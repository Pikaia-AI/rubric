"""追问配合 (Follow-up Cooperation) — PKBench v5 single-dim plugin.

One Claude call with criteria-injected prompt. Algorithm + dim text live
in rubric.internal.pkbench_v5 (snapshot cbd08bb, 2026-05-07).
"""
from rubric.internal import pkbench_v5 as _pk

DIM_KEY = "followup_cooperation"

META = {
    "id": f"pkbench-{DIM_KEY}",
    "name": _pk.dim_zh(DIM_KEY),
    "version": "5.0.0",
    "description": _pk.dim_description(DIM_KEY),
    "level": "transcript",
    "group": "Pikaia-Bench",
    "homepage": "https://github.com/Pikaia-AI/rubric/tree/main/rubric/builtin_metrics/pkbench_followup_cooperation",
    "paper": f"pikaia_benchmarking 维度集{_pk.DIMENSION_SET_VERSION} @ {_pk.SOURCE_COMMIT} (snapshot {_pk.SNAPSHOT_DATE})",
    "deterministic": False,
    "needs_api_key": "ANTHROPIC_API_KEY",
    "dims": [
        {
            "key": DIM_KEY,
            "label": {"zh": _pk.dim_zh(DIM_KEY), "en": _pk.dim_en(DIM_KEY)},
            "score_range": (0, 2),
            "higher_is_better": True,
            "description": _pk.dim_description(DIM_KEY),
            "category": _pk.dim_category(DIM_KEY),
        }
    ],
}


def score(turns):
    return {DIM_KEY: _pk.score_dim(DIM_KEY, turns)}
