"""parrot-paraphrase_rate — single-dim plugin.

Per-agent-turn Echo Ratio (char-bigram precision of reply's first sentence
vs the user's prior turn), aggregated as 100 − avg(ER). Higher = less
literal echo of user's words.

See rubric.internal.parrot for the shared echo_ratio + role normalization.
"""
from rubric.internal.parrot import echo_ratio, iter_agent_turns

DIM_KEY = "paraphrase_rate"

META = {
    "id": f"parrot-{DIM_KEY}",
    "name": "改述率",
    "version": "0.1.0",
    "description": (
        "100 − avg Echo Ratio over agent turns. ER = char-bigram set "
        "precision of agent's first sentence vs the user's prior turn. "
        "Higher = less literal echo. Char-level Chinese, no LLM."
    ),
    "level": "transcript",
    "group": "Parrot Check",
    "homepage": "https://github.com/Pikaia-AI/rubric",
    "deterministic": True,
    "dims": [
        {
            "key": DIM_KEY,
            "label": {"zh": "改述率", "en": "Paraphrase Rate"},
            "score_range": (0, 100),
            "higher_is_better": True,
            "description": "100 − avg Echo Ratio over agent turns. Higher = less literal echo of user's words.",
            "category": "提问质量",
        }
    ],
}


def score(turns):
    er_values = [echo_ratio(t["text"], lu) for _, t, lu in iter_agent_turns(turns)]
    if not er_values:
        return {DIM_KEY: 0.0}
    avg_er = sum(er_values) / len(er_values)
    return {DIM_KEY: round(100.0 - avg_er, 2)}
