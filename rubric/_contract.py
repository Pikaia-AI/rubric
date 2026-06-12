"""Plugin contract.

Each metric folder under `metrics/<id>/` must contain a `metric.py` that
exposes two module-level objects:

    META  — dict matching MetricMeta schema below.
    score — callable taking either `turns` (level='transcript') or
            `example` (level='utterance') and returning {dim_key: raw_value}
            where each dim_key is one of META["dims"][i]["key"] and
            raw_value falls inside that dim's `score_range`.

`turns` shape: list[{"role": "assistant"|"user"|..., "text": str}]
`example` shape: {"context": [str], "probe_text": str, ...}  (FED-style)

Roles accepted (any case):
    assistant aliases: "assistant", "面试官", "interviewer", "agent", "ai"
    user      aliases: "user", "受访者", "respondent", "human"
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal, TypedDict


class PluginError(ValueError):
    """Raised when a metric plugin's META or score output is malformed."""


class DimSpec(TypedDict):
    key: str                            # short snake_case id, unique inside the metric
    label: dict                         # {"zh": "...", "en": "..."}
    score_range: tuple                  # (lo, hi); raw_value must lie in this
    higher_is_better: bool
    description: str                    # one-line: what does this measure
    # Optional:
    # category: str                    # free-text group inside the metric


class MetricMeta(TypedDict):
    id: str                             # kebab-case, unique. e.g. "parrot-check"
    name: str                           # display name
    version: str                        # semver, e.g. "0.1.0"
    description: str                    # one-line
    level: Literal["transcript", "utterance"]
    dims: list[DimSpec]
    # Optional:
    # homepage: str
    # paper: str                       # citation
    # needs_api_key: str               # env var that must be set
    # deterministic: bool              # True if no LLM/network call (default False)


REQUIRED_META_KEYS = {"id", "name", "version", "description", "level", "dims"}
REQUIRED_DIM_KEYS = {"key", "label", "score_range", "higher_is_better", "description"}


def validate_meta(meta: dict, source: str = "<unknown>") -> None:
    """Raise PluginError if META is malformed."""
    missing = REQUIRED_META_KEYS - set(meta.keys())
    if missing:
        raise PluginError(f"{source}: META missing required keys: {sorted(missing)}")
    if meta["level"] not in ("transcript", "utterance"):
        raise PluginError(
            f"{source}: META['level'] must be 'transcript' or 'utterance', got {meta['level']!r}"
        )
    if not isinstance(meta["dims"], list) or not meta["dims"]:
        raise PluginError(f"{source}: META['dims'] must be a non-empty list")
    seen = set()
    for i, d in enumerate(meta["dims"]):
        miss = REQUIRED_DIM_KEYS - set(d.keys())
        if miss:
            raise PluginError(f"{source}: dim[{i}] missing keys {sorted(miss)}")
        if d["key"] in seen:
            raise PluginError(f"{source}: duplicate dim key {d['key']!r}")
        seen.add(d["key"])
        lo, hi = d["score_range"]
        if not (isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and lo < hi):
            raise PluginError(
                f"{source}: dim[{i}]['score_range'] must be (lo, hi) with lo<hi"
            )
        if not isinstance(d["label"], dict) or "zh" not in d["label"] or "en" not in d["label"]:
            raise PluginError(
                f"{source}: dim[{i}]['label'] must be a dict with 'zh' and 'en' keys"
            )


def validate_score_output(meta: dict, output: Any, source: str = "<unknown>") -> None:
    """Raise PluginError if score() output doesn't match META's dims."""
    if not isinstance(output, dict):
        raise PluginError(f"{source}: score() must return a dict, got {type(output).__name__}")
    declared = {d["key"]: d["score_range"] for d in meta["dims"]}
    missing = set(declared) - set(output)
    if missing:
        raise PluginError(f"{source}: score() missing dim keys: {sorted(missing)}")
    for key, val in output.items():
        if key not in declared:
            continue  # extra diagnostics keys allowed (will be filtered by consumer)
        lo, hi = declared[key]
        if not isinstance(val, (int, float)) or not (lo <= val <= hi):
            raise PluginError(
                f"{source}: dim {key!r} value {val!r} outside score_range [{lo}, {hi}]"
            )


@dataclass
class Metric:
    """A loaded metric plugin."""
    meta: dict
    score: Callable
    source_dir: str = ""
    module: Any = None  # the imported metric.py module — adapters can reach
                       # for optional extras like score_partial / per-dim helpers

    @property
    def id(self) -> str:
        return self.meta["id"]

    @property
    def level(self) -> str:
        return self.meta["level"]

    @property
    def dim_keys(self) -> list[str]:
        return [d["key"] for d in self.meta["dims"]]
