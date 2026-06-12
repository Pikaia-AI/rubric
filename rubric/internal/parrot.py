"""Shared parrot-check primitives — char-bigram set logic + role normalization.

Used by both parrot single-dim plugins:
  • parrot_paraphrase_rate
  • parrot_single_question_rate
"""
from __future__ import annotations

import re

_PUNCT = re.compile(r'[，。！？、：；""‘’…—,!?.:; \t\n\r-]')
_SENT_END = re.compile(r'[。！？!?]')

_ASSISTANT_ROLES = {"assistant", "面试官", "interviewer", "agent", "ai"}
_USER_ROLES = {"user", "受访者", "respondent", "human"}


def norm_role(role) -> str:
    r = (role or "").strip()
    if r in _ASSISTANT_ROLES or r.lower() in _ASSISTANT_ROLES:
        return "assistant"
    if r in _USER_ROLES or r.lower() in _USER_ROLES:
        return "user"
    return r.lower()


def echo_ratio(reply: str, last_user: str) -> float:
    """0-100, char-bigram precision of reply's first sentence vs last_user."""
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


def question_count(text: str) -> int:
    return text.count("?") + text.count("？")


def iter_agent_turns(turns):
    """Yield (i, agent_turn_dict, last_user_text) for every scorable agent turn.

    Skips agent turns with no preceding user turn or with empty text.
    """
    for i, t in enumerate(turns):
        if norm_role(t.get("role", "")) != "assistant":
            continue
        last_user = ""
        for j in range(i - 1, -1, -1):
            if norm_role(turns[j].get("role", "")) == "user":
                last_user = turns[j].get("text", "") or ""
                break
        if not last_user:
            continue
        reply = t.get("text", "") or ""
        if not reply:
            continue
        yield i, t, last_user
