"""Outline-Coverage — engineering replacement for the PKBench v5
"研究问题覆盖" dim that was removed 2026-05-20 as a "工程打点" dim.

Given a planned outline (JSON-string snapshot of
`t_project_interviews.interview_state.outline` tree) and a transcript,
a single LLM call aligns every interviewer turn to either a planned
(section, question) or `improv`. Then two 0-5 dims:

  • research_question_coverage — planned questions actually asked / total planned
  • outline_adherence          — interviewer turns aligned to outline / total interviewer turns

Routes through b.ai/Haiku primarily (this task is structured + cheap),
falls back to ask_claude on transport failure.

Outline schema (from interview_state.outline):
  {"title": ..., "root_node": {"children": [section_node, ...]}}
  section_node = {"node_id", "name", "is_section": True, "children": [question_node]}
  question_node = {"node_id", "name"}

If outline is empty/unparseable, both dims return 0 — caller knows to supply.

Signature note: this metric needs an outline AND turns. The rubric loader
calls `score(turns, outline=...)` if the metric exposes that param via
inspect — same convention pikaia_eval already uses for the legacy adapter.
"""
from __future__ import annotations

import json
import os
import re
import sys

from rubric.helpers import ask_claude

# ── Model routing (b.ai/Haiku primary, ask_claude fallback) ──────────────────
_BAI_BASE_URL = os.environ.get("BAI_BASE_URL", "https://api.b.ai/v1")
_BAI_API_KEY = os.environ.get("BAI_API_KEY", "")
_MODEL = os.environ.get("OUTLINE_ADAPTER_MODEL", "claude-haiku-4-5")

_bai_client = None


def _get_bai():
    global _bai_client
    if _bai_client is None:
        import openai  # type: ignore[import-not-found]
        _bai_client = openai.OpenAI(base_url=_BAI_BASE_URL, api_key=_BAI_API_KEY)
    return _bai_client


def _ask_haiku(system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
    """Call b.ai gateway with Haiku. Falls back to ask_claude on transport error."""
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
        print(f"[outline-coverage] b.ai/{_MODEL} failed ({type(e).__name__}: {e}); "
              f"falling back to ask_claude", file=sys.stderr)
        return ask_claude(system_prompt, user_prompt, max_tokens=max_tokens)


# ── rubric META ──────────────────────────────────────────────────────────────
META = {
    "id": "outline-coverage",
    "name": "Outline-Coverage",
    "version": "0.1.0",
    "description": (
        "Engineering replacement for the PKBench v5 '研究问题覆盖' dim "
        "(removed 2026-05-20). Aligns every interviewer turn to a planned "
        "(section, question) via a single LLM call, then derives coverage "
        "and adherence rates from the alignment."
    ),
    "level": "transcript",
    "homepage": "https://github.com/Pikaia-AI/rubric",
    "paper": "Pikaia engineering-dim (replaces PKBench v5 'research_question_coverage' removed 2026-05-20)",
    "deterministic": False,
    "needs_api_key": "BAI_API_KEY",
    "dims": [
        {
            "key": "research_question_coverage",
            "label": {"zh": "研究问题覆盖", "en": "Research Question Coverage"},
            "score_range": (0, 5),
            "higher_is_better": True,
            "description": (
                "实际访谈对大纲中预设问题的覆盖比例。"
                "covered_q_ids / total_planned_q_ids × 5."
            ),
            "category": "结果质量",
        },
        {
            "key": "outline_adherence",
            "label": {"zh": "大纲贴合度", "en": "Outline Adherence"},
            "score_range": (0, 5),
            "higher_is_better": True,
            "description": (
                "主持人发言中实际对齐到大纲的占比，反映即兴跑题率。"
                "n_aligned / n_interviewer_turns × 5."
            ),
            "category": "主持人质量",
        },
    ],
}


# ── Alignment prompt + parser ────────────────────────────────────────────────
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
    """Parse interview_state.outline JSON → ordered list of {q_id, q_text, sec_id, sec_name}."""
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
    """Combine outline + indexed interviewer turns into the LLM prompt."""
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
    """Extract a JSON array of {turn_idx, q_id, confidence} from the LLM response."""
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


def score(turns, outline: str = ""):
    """Score (research_question_coverage, outline_adherence) for one sample.

    Args:
        turns: list[{"role": "assistant"|"user", "text": str}]
        outline: JSON string of interview_state.outline tree.

    Returns: {dim_key: 0..5 float}. Returns zeros if outline is empty/unparseable
    or no interviewer turns exist.
    """
    questions = _flatten_outline(outline)
    iq_turns = [t for t in turns if t.get("role") == "assistant"]
    if not questions or not iq_turns:
        return {"research_question_coverage": 0.0, "outline_adherence": 0.0}

    user_content = _build_user_content(turns, questions)
    response = _ask_haiku(SYSTEM_PROMPT, user_content, max_tokens=4096)
    aligns = _parse_alignment_json(response)
    if not aligns:
        print(f"[outline-coverage] alignment JSON unparseable; response head: {response[:200]!r}",
              file=sys.stderr)
        return {"research_question_coverage": 0.0, "outline_adherence": 0.0}

    planned_q_ids = {q["q_id"] for q in questions}
    covered_q_ids = {
        a.get("q_id") for a in aligns
        if a.get("q_id") and a.get("q_id") in planned_q_ids
    }
    n_iq_judged = sum(1 for a in aligns)
    n_aligned = sum(1 for a in aligns if a.get("q_id") in planned_q_ids and a.get("q_id"))

    coverage_rate = len(covered_q_ids) / max(1, len(planned_q_ids))
    adherence_rate = n_aligned / max(1, n_iq_judged)

    return {
        "research_question_coverage": round(coverage_rate * 5.0, 3),
        "outline_adherence": round(adherence_rate * 5.0, 3),
    }
