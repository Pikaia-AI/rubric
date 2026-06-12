"""outline-outline_adherence — single-dim plugin.

Interviewer turns aligned to outline / total interviewer turns, scaled 0-5.
Shares the same cached alignment as outline-research_question_coverage.
"""
from rubric.internal.outline_alignment import get_alignment

DIM_KEY = "outline_adherence"

META = {
    "id": f"outline-{DIM_KEY}",
    "name": "大纲贴合度",
    "version": "0.1.0",
    "description": (
        "Same alignment as outline-research_question_coverage, but the "
        "rate is n_aligned / n_interviewer_turns × 5 — reflects how "
        "much the agent stayed on outline vs improvised."
    ),
    "level": "transcript",
    "io": {
        "input": "turns: list[{role, text}]\noutline: str (JSON of interview_state.outline tree)",
        "output": "{outline_adherence: float ∈ [0, 5]}",
    },

    "group": "Outline Coverage",
    "homepage": "https://github.com/Pikaia-AI/rubric/tree/main/rubric/builtin_metrics/outline_outline_adherence",
    "deterministic": False,
    "needs_api_key": "BAI_API_KEY",
    "dims": [
        {
            "key": DIM_KEY,
            "label": {"zh": "大纲贴合度", "en": "Outline Adherence"},
            "score_range": (0, 5),
            "higher_is_better": True,
            "description": "主持人发言中实际对齐到大纲的占比 × 5。反映即兴跑题率。",
            "formula": """
A, planned       = same as outline-research_question_coverage (shared cache hit)
n_aligned        = |{ a ∈ A : a.q_id ∈ planned }|
n_judged         = |A|

outline_adherence = 5 · n_aligned / max(1, n_judged)

Range: [0, 5], higher = better.""",
            "category": "主持人质量",
        }
    ],
}


def score(turns, outline: str = ""):
    questions, aligns = get_alignment(turns, outline)
    if not questions or not aligns:
        return {DIM_KEY: 0.0}
    planned_q_ids = {q["q_id"] for q in questions}
    n_judged = sum(1 for a in aligns)
    n_aligned = sum(1 for a in aligns if a.get("q_id") in planned_q_ids and a.get("q_id"))
    rate = n_aligned / max(1, n_judged)
    return {DIM_KEY: round(rate * 5.0, 3)}
