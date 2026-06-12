"""Run a loaded metric over a transcript / utterance and validate output."""
from __future__ import annotations

from typing import Any

from ._contract import Metric, validate_score_output


def run(metric: Metric, sample: Any, *, validate: bool = True) -> dict[str, float]:
    """Run one metric on one sample. Returns {dim_key: raw_value}.

    Args:
        metric: result of rubric.load() or one entry from load_all().
        sample: turns list if level='transcript', example dict if 'utterance'.
        validate: if True, validate the score() output against META.

    Diagnostic extras from the score() output (keys not in META["dims"]) are
    preserved in the returned dict — consumers may use them but the framework
    won't carry them in summary tables.
    """
    output = metric.score(sample)
    if validate:
        validate_score_output(metric.meta, output, source=metric.id)
    return output


def run_all(
    registry: dict[str, Metric],
    sample: Any,
    *,
    levels: tuple = ("transcript", "utterance"),
    validate: bool = True,
) -> dict[str, dict[str, float]]:
    """Run every metric in `registry` whose level is in `levels` on `sample`.

    Returns: { metric_id: {dim_key: raw_value} }.
    """
    out = {}
    for mid, m in registry.items():
        if m.level not in levels:
            continue
        out[mid] = run(m, sample, validate=validate)
    return out
