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
    "homepage": "https://github.com/Pikaia-AI/rubric/tree/main/rubric/builtin_metrics/parrot_paraphrase_rate",
    "deterministic": True,
    "dims": [
        {
            "key": DIM_KEY,
            "label": {"zh": "改述率", "en": "Paraphrase Rate"},
            "score_range": (0, 100),
            "higher_is_better": True,
            "description": "100 − avg Echo Ratio over agent turns. Higher = less literal echo of user's words.",
            "formula": """
For each agent turn t with non-empty preceding user turn u_t, let
  H_t      = first sentence of t.reply, truncated at first .?！?! within
             first 30 chars, else first 30 chars
  clean(x) = x with punct + whitespace removed
  G(x)     = { clean(x)[i:i+2] : 0 ≤ i < |clean(x)| − 1 }      (char 2-gram set)
  ER(t)    = 100 · |G(H_t) ∩ G(u_t)| / |G(H_t)|                (single-turn echo ratio)

paraphrase_rate = 100 − (1/|T|) · Σ_{t ∈ T} ER(t)

where T = { t : t is an assistant turn with valid u_t and |clean(H_t)| ≥ 2 }

Range: [0, 100], higher = better. No LLM.""",
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
