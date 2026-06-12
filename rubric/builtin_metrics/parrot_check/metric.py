"""parrot-check — deterministic 复读 / 多问 detector.

See README.md in this folder for the full algorithm + worked example +
relation to BLEU.

Two dims, both 0-100, higher = better:
  • paraphrase_rate     = 100 − avg Echo Ratio over agent turns
  • single_question_rate = % agent turns asking ≤ 1 question

No LLM call, no network. Pure char-bigram Jaccard.
"""
from __future__ import annotations

import re

# ── rubric plugin contract ───────────────────────────────────────────────────

META = {
    "id": "parrot-check",
    "name": "Parrot Check",
    "version": "0.1.0",
    "description": "Deterministic 复读 / 多问 detector for Chinese interview transcripts (char-bigram, no LLM).",
    "level": "transcript",
    "homepage": "https://github.com/Pikaia-AI/rubric",
    "deterministic": True,
    "dims": [
        {
            "key": "paraphrase_rate",
            "label": {"zh": "改述率", "en": "Paraphrase Rate"},
            "score_range": (0, 100),
            "higher_is_better": True,
            "description": "100 − avg Echo Ratio over agent turns. Higher = less literal echo of user's words.",
            "category": "提问质量",
        },
        {
            "key": "single_question_rate",
            "label": {"zh": "一题一问率", "en": "Single-Q Rate"},
            "score_range": (0, 100),
            "higher_is_better": True,
            "description": "% agent turns asking ≤ 1 question.",
            "category": "提问质量",
        },
    ],
}


# ── implementation ───────────────────────────────────────────────────────────

_PUNCT = re.compile(r'[，。！？、：；""‘’…—,!?.:; \t\n\r-]')
_SENT_END = re.compile(r'[。！？!?]')

_ASSISTANT_ROLES = {"assistant", "面试官", "interviewer", "agent", "ai"}
_USER_ROLES = {"user", "受访者", "respondent", "human"}


def _norm_role(role) -> str:
    r = (role or "").strip()
    if r in _ASSISTANT_ROLES or r.lower() in _ASSISTANT_ROLES:
        return "assistant"
    if r in _USER_ROLES or r.lower() in _USER_ROLES:
        return "user"
    return r.lower()


def echo_ratio(reply: str, last_user: str) -> float:
    """0-100. Char-bigram set precision of reply's first sentence vs last_user."""
    if not reply or not last_user:
        return 0.0
    head = reply
    m = _SENT_END.search(head[:30])
    if m and m.start() > 0:
        head = head[:m.start()]
    head = head[:30]
    head_clean = _PUNCT.sub("", head)
    user_clean = _PUNCT.sub("", last_user)
    if len(head_clean) < 2 or len(user_clean) < 2:
        return 0.0
    agent_grams = {head_clean[i : i + 2] for i in range(len(head_clean) - 1)}
    user_grams = {user_clean[i : i + 2] for i in range(len(user_clean) - 1)}
    if not agent_grams:
        return 0.0
    return 100.0 * len(agent_grams & user_grams) / len(agent_grams)


def _question_count(text: str) -> int:
    return text.count("?") + text.count("？")


def score(turns: list[dict]) -> dict:
    """Per rubric contract: returns {paraphrase_rate, single_question_rate, ...diagnostics}."""
    er_values = []
    single_flags = []
    per_turn = []
    for i, t in enumerate(turns):
        if _norm_role(t.get("role", "")) != "assistant":
            continue
        last_user = ""
        for j in range(i - 1, -1, -1):
            if _norm_role(turns[j].get("role", "")) == "user":
                last_user = turns[j].get("text", "") or ""
                break
        if not last_user:
            continue
        reply = t.get("text", "") or ""
        if not reply:
            continue
        er = echo_ratio(reply, last_user)
        qc = _question_count(reply)
        er_values.append(er)
        single_flags.append(1.0 if qc <= 1 else 0.0)
        per_turn.append({
            "turn_index": i,
            "echo_ratio": round(er, 2),
            "q_count": qc,
        })

    if not er_values:
        return {
            "paraphrase_rate": 0.0,
            "single_question_rate": 0.0,
            "avg_echo_ratio": 0.0,
            "n_agent_turns": 0,
            "per_turn": [],
        }

    avg_er = sum(er_values) / len(er_values)
    return {
        "paraphrase_rate": round(100.0 - avg_er, 2),
        "single_question_rate": round(100.0 * sum(single_flags) / len(single_flags), 2),
        "avg_echo_ratio": round(avg_er, 2),
        "n_agent_turns": len(er_values),
        "per_turn": per_turn,
    }
