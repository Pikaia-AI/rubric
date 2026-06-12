"""Auto-discover metric plugins under <repo>/metrics/."""
from __future__ import annotations

import importlib.util
import pathlib
import sys
from typing import Iterable

from ._contract import Metric, PluginError, validate_meta


def default_metrics_dir() -> pathlib.Path:
    """Return <repo>/metrics/ for an in-tree run (sibling of the rubric package)."""
    return pathlib.Path(__file__).parent.parent / "metrics"


def find_metric_dirs(metrics_dir: str | pathlib.Path | None = None) -> list[pathlib.Path]:
    """Return all immediate sub-dirs of `metrics/` that contain a `metric.py`."""
    root = pathlib.Path(metrics_dir) if metrics_dir else default_metrics_dir()
    if not root.is_dir():
        return []
    return sorted(
        p for p in root.iterdir()
        if p.is_dir()
        and not p.name.startswith((".", "_"))
        and (p / "metric.py").is_file()
    )


def _load_module(metric_dir: pathlib.Path):
    """Import `metric.py` from `metric_dir` as a uniquely-named module."""
    init = metric_dir / "metric.py"
    mod_name = f"rubric_metric_{metric_dir.name.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(mod_name, init)
    if spec is None or spec.loader is None:
        raise PluginError(f"could not build import spec for {init}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    # Make sibling files importable (e.g. helpers next to metric.py)
    sys.path.insert(0, str(metric_dir))
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    finally:
        try:
            sys.path.remove(str(metric_dir))
        except ValueError:
            pass
    return module


def _build_metric(metric_dir: pathlib.Path) -> Metric:
    mod = _load_module(metric_dir)
    if not hasattr(mod, "META"):
        raise PluginError(f"{metric_dir.name}/metric.py missing META")
    if not hasattr(mod, "score"):
        raise PluginError(f"{metric_dir.name}/metric.py missing score()")
    meta = mod.META
    validate_meta(meta, source=f"{metric_dir.name}/metric.py")
    return Metric(meta=meta, score=mod.score, source_dir=str(metric_dir))


def load_all(
    metrics_dir: str | pathlib.Path | None = None,
    *,
    ids: Iterable[str] | None = None,
    strict: bool = True,
) -> dict[str, Metric]:
    """Load every metric plugin and return a registry { metric_id: Metric }.

    Args:
        metrics_dir: path containing one sub-folder per metric. Defaults to
            the repo's bundled `metrics/` next to this package.
        ids: if given, only load these metric ids.
        strict: if True, any malformed plugin raises. If False, skip with a
            warning and continue.

    Raises:
        PluginError: when a plugin is malformed and strict=True, or when an
            id in `ids` isn't found.
    """
    registry: dict[str, Metric] = {}
    wanted = set(ids) if ids else None
    for metric_dir in find_metric_dirs(metrics_dir):
        try:
            m = _build_metric(metric_dir)
        except PluginError:
            if strict:
                raise
            continue
        if wanted is not None and m.id not in wanted:
            continue
        if m.id in registry:
            raise PluginError(f"duplicate metric id {m.id!r} (from {metric_dir})")
        registry[m.id] = m
    if wanted:
        missing = wanted - set(registry)
        if missing:
            raise PluginError(f"requested metric id(s) not found: {sorted(missing)}")
    return registry


def load(metric_id: str, metrics_dir: str | pathlib.Path | None = None) -> Metric:
    """Load one metric by id, raising PluginError if not found."""
    reg = load_all(metrics_dir, ids=[metric_id])
    return reg[metric_id]
