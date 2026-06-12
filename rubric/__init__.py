"""rubric — pluggable interview metric framework.

Each metric lives in its own folder under `<repo>/metrics/<id>/`. Each
exposes `META` + `score()`. Loader auto-discovers, validates, returns a
registry { metric_id: Metric }.

Public API:
    from rubric import load_all, load, run, Metric, MetricMeta, DimSpec

    registry = load_all()                # all metrics under metrics/
    m = load("parrot-check")             # single metric by id
    result = run(m, turns)               # score one transcript

See README.md for the plugin contract.
"""
from __future__ import annotations

from ._contract import (
    DimSpec,
    Metric,
    MetricMeta,
    PluginError,
    validate_meta,
    validate_score_output,
)
from ._loader import load_all, load, default_metrics_dir, find_metric_dirs
from ._runner import run, run_all

__version__ = "0.1.1"

__all__ = [
    "__version__",
    "DimSpec",
    "Metric",
    "MetricMeta",
    "PluginError",
    "validate_meta",
    "validate_score_output",
    "load_all",
    "load",
    "default_metrics_dir",
    "find_metric_dirs",
    "run",
    "run_all",
]
