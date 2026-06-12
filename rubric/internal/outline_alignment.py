"""Outline alignment helper with per-call cache.

Both outline-* plugins (research_question_coverage + outline_adherence) feed
on the SAME alignment list produced by a single Haiku call. We cache by
(turns identity, outline string) so that scoring both dims sequentially
inside one rubric.run_all() doesn't pay the LLM cost twice.

Cache is process-local + bounded — a dict with manual eviction.
"""
from __future__ import annotations

import json
import os
import re
import sys

from rubric.helpers import ask_claude

_BAI_BASE_URL = os.environ.get("BAI_BASE_URL", "https://api.b.ai/v1")
_BAI_API_KEY = os.environ.get("BAI_API_KEY", "")
_MODEL = os.environ.get("OUTLINE_ADAPTER_MODEL", "claude-haiku-4-5")

_bai_client = None
_ALIGN_CACHE: dict = {}
_CACHE_MAX = 64  # plenty for one server-side eval run


def _get_bai():
    global _bai_client
    if _bai_client is None:
        import openai  # type: ignore[import-not-found]
        _bai_client = openai.OpenAI(base_url=_BAI_BASE_URL, api_key=_BAI_API_KEY)
    return _bai_client


def _ask_haiku(system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
    if not _BAI_API_KEY:
        return ask_claude(system_prompt, user_prompt, max_tokens=max_tokens)
    try:
        resp = _get_bai().chat.completions.create(
            model=_MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(
            f"[outline_alignment] b.ai/{_MODEL} failed ({type(e).__name__}: {e}); "
            f"falling back to ask_claude",
            file=sys.stderr,
        )
        return ask_claude(system_prompt, user_prompt, max_tokens=max_tokens)


SYSTEM_PROMPT = """你是一位访谈对齐分析师。我会给你一份「计划大纲」(planned outline) 和一份实际的访谈 transcript。

请为每一条访谈员 (interviewer / assistant) 的发言, 判断它对应到大纲里的哪条 planned question (用 q_id 引用), 或标记为即兴提问 (q_id 设为 null)。

判定规则:
- 一条 turn 覆盖一条 question 的条件: turn 用任何措辞 询问 该 question, 或在追问中明显围绕该 question 的内容展开
- 寒暄、确认、过渡语 ("好的"、"嗯"、"明白") 不覆盖任何 question
- 完全不在大纲范围内的提问 = improv (q_id: null)
- 多条 turn 可以覆盖同一条 planned question (典型的追问链), 这是合法的
- 大纲不是严格顺序——agent 可以任意跳 section

输出: 严格一个 JSON 数组, 每条 interviewer turn 一个对象, 按 transcript 顺序:
[
  {"turn_idx": <int>, "q_id": "<node_id 字符串 或 null>", "confidence": <0.0-1.0 浮点>},
  ...
]

只输出这个 JSON 数组, 不要解释, 不要 markdown 代码块。"""


def _flatten_outline(outline_str):
    if not outline_str:
        return []
    try:
        tree = json.loads(outline_str) if isinstance(outline_str, str) else outline_str
    except Exception:
        return []
    root = tree.get("root_node") or {}
    out = []
    for sec in root.get("children", []) or []:
        if not sec.get("is_section"):
            continue
        for q in sec.get("children", []) or []:
            out.append({
                "q_id": q.get("node_id"),
                "q_text": q.get("name", ""),
                "sec_id": sec.get("node_id"),
                "sec_name": sec.get("name", ""),
            })
    return out


def _build_user_content(turns, questions):
    outline_block = []
    cur_sec = None
    for q in questions:
        if q["sec_id"] != cur_sec:
            cur_sec = q["sec_id"]
            outline_block.append(f"\n## Section: {q['sec_name']}  [sec_id: {q['sec_id']}]")
        outline_block.append(f"- q_id: {q['q_id']}\n  question: {q['q_text']}")

    iq_indices = []
    transcript_block = []
    for i, t in enumerate(turns):
        role_lbl = "INTERVIEWER" if t.get("role") == "assistant" else "respondent"
        if t.get("role") == "assistant":
            iq_indices.append(i)
        transcript_block.append(f"[turn {i}, {role_lbl}] {t.get('text','')}")

    return (
        "# Planned outline\n"
        + "\n".join(outline_block)
        + "\n\n# Transcript\n"
        + "\n".join(transcript_block)
        + f"\n\n请为以下 {len(iq_indices)} 个 INTERVIEWER turn 各输出一个对齐对象。"
        + f"INTERVIEWER turn indices: {iq_indices}"
    )


def _parse_alignment_json(raw_text: str):
    txt = re.sub(r"```(?:json)?", "", raw_text).strip("` \n")
    m = re.search(r"\[\s*\{.*\}\s*\]", txt, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group())
        if isinstance(data, list):
            return data
    except Exception:
        return None
    return None


def _cache_key(turns, outline):
    """Identity-based for turns (callers reuse the same list) + outline hash."""
    return (id(turns), outline if isinstance(outline, str) else json.dumps(outline))


def get_alignment(turns, outline=""):
    """Return (questions: list, aligns: list[dict] | None).

    Cached by (turns id, outline). Both outline-* plugins call this; the
    second call hits cache and pays zero LLM cost.
    """
    key = _cache_key(turns, outline)
    if key in _ALIGN_CACHE:
        return _ALIGN_CACHE[key]

    questions = _flatten_outline(outline)
    iq_turns = [t for t in turns if t.get("role") == "assistant"]
    if not questions or not iq_turns:
        result = (questions, None)
        _ALIGN_CACHE[key] = result
        return result

    user_content = _build_user_content(turns, questions)
    response = _ask_haiku(SYSTEM_PROMPT, user_content, max_tokens=4096)
    aligns = _parse_alignment_json(response)
    if not aligns:
        print(
            f"[outline_alignment] alignment JSON unparseable; response head: {response[:200]!r}",
            file=sys.stderr,
        )
        aligns = None

    # Manual LRU-ish eviction
    if len(_ALIGN_CACHE) >= _CACHE_MAX:
        _ALIGN_CACHE.pop(next(iter(_ALIGN_CACHE)))

    result = (questions, aligns)
    _ALIGN_CACHE[key] = result
    return result
