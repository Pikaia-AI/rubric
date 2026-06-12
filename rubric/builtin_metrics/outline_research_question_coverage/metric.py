"""outline-research_question_coverage — single-dim plugin.

Planned questions actually asked / total planned, scaled 0-5.
Shares one Haiku alignment call with outline-outline_adherence (cached
in rubric.internal.outline_alignment).
"""
from rubric.internal.outline_alignment import get_alignment

DIM_KEY = "research_question_coverage"

META = {
    "id": f"outline-{DIM_KEY}",
    "name": "研究问题覆盖",
    "version": "0.1.0",
    "description": (
        "Engineering replacement for the v5-removed '研究问题覆盖' dim. "
        "Single Haiku call aligns interviewer turns → outline q_ids; "
        "coverage = covered_q / total_planned_q × 5."
    ),
    "level": "transcript",
    "group": "Outline Coverage",
    "homepage": "https://github.com/Pikaia-AI/rubric/tree/main/rubric/builtin_metrics/outline_research_question_coverage",
    "deterministic": False,
    "needs_api_key": "BAI_API_KEY",
    "dims": [
        {
            "key": DIM_KEY,
            "label": {"zh": "研究问题覆盖", "en": "Research Question Coverage"},
            "score_range": (0, 5),
            "higher_is_better": True,
            "description": "实际访谈对大纲中预设问题的覆盖比例 × 5.",
            "category": "结果质量",
        }
    ],
}


def score(turns, outline: str = ""):
    questions, aligns = get_alignment(turns, outline)
    if not questions or not aligns:
        return {DIM_KEY: 0.0}
    planned_q_ids = {q["q_id"] for q in questions}
    covered = {
        a.get("q_id") for a in aligns
        if a.get("q_id") and a.get("q_id") in planned_q_ids
    }
    rate = len(covered) / max(1, len(planned_q_ids))
    return {DIM_KEY: round(rate * 5.0, 3)}
