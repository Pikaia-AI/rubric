"""parrot-single_question_rate — single-dim plugin.

% of agent turns asking ≤ 1 question. Char-level question-mark counter
across the full agent reply (both `?` and `？`). No LLM.
"""
from rubric.internal.parrot import iter_agent_turns, question_count

DIM_KEY = "single_question_rate"

META = {
    "id": f"parrot-{DIM_KEY}",
    "name": "一题一问率",
    "version": "0.1.0",
    "description": (
        "% agent turns asking ≤ 1 question. Counts ? + ？ across the "
        "whole reply (not just first sentence). No LLM."
    ),
    "level": "transcript",
    "group": "Parrot Check",
    "homepage": "https://github.com/Pikaia-AI/rubric",
    "deterministic": True,
    "dims": [
        {
            "key": DIM_KEY,
            "label": {"zh": "一题一问率", "en": "Single-Q Rate"},
            "score_range": (0, 100),
            "higher_is_better": True,
            "description": "% agent turns asking ≤ 1 question.",
            "category": "提问质量",
        }
    ],
}


def score(turns):
    flags = [1.0 if question_count(t["text"]) <= 1 else 0.0
             for _, t, _ in iter_agent_turns(turns)]
    if not flags:
        return {DIM_KEY: 0.0}
    return {DIM_KEY: round(100.0 * sum(flags) / len(flags), 2)}
