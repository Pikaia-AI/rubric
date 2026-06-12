"""Smoke tests for the plugin contract + the 25 bundled single-dim plugins."""
import json
import pathlib

import pytest

from rubric import load, load_all, run, validate_meta, PluginError


REPO = pathlib.Path(__file__).parent.parent


def test_discovery_25():
    reg = load_all()
    assert len(reg) == 25, f"expected 25 single-dim plugins, got {len(reg)}: {sorted(reg)}"
    # Group counts
    by_group = {}
    for m in reg.values():
        by_group.setdefault(m.meta.get("group", "(none)"), []).append(m.id)
    assert len(by_group.get("Parrot Check", [])) == 2
    assert len(by_group.get("Outline Coverage", [])) == 2
    assert len(by_group.get("Pikaia-Bench", [])) == 21


def test_one_dim_per_plugin():
    """Every plugin owns exactly one dim — the new shape after 0.3.0."""
    for m in load_all().values():
        assert len(m.meta["dims"]) == 1, f"{m.id} has {len(m.meta['dims'])} dims, expected 1"


def test_meta_shape():
    for m in load_all().values():
        validate_meta(m.meta, source=m.id)
        # Dim key matches plugin id suffix
        dim_key = m.meta["dims"][0]["key"]
        assert m.id.endswith(dim_key), f"{m.id} dim key {dim_key} should match id suffix"


def test_parrot_paraphrase_score_on_example():
    m = load("parrot-paraphrase_rate")
    sample_path = REPO / "rubric/builtin_metrics/parrot_paraphrase_rate/examples/x03_q6.json"
    sample = json.loads(sample_path.read_text(encoding="utf-8"))["turns"]
    result = run(m, sample)
    assert result["paraphrase_rate"] == pytest.approx(46.07, abs=0.1)


def test_parrot_single_q_score_on_example():
    m = load("parrot-single_question_rate")
    sample_path = REPO / "rubric/builtin_metrics/parrot_paraphrase_rate/examples/x03_q6.json"
    sample = json.loads(sample_path.read_text(encoding="utf-8"))["turns"]
    result = run(m, sample)
    assert result["single_question_rate"] == pytest.approx(50.0, abs=0.1)


def test_unknown_metric_raises():
    with pytest.raises(PluginError, match="not found"):
        load("does-not-exist")


def test_score_validation_catches_bad_dim():
    from rubric import validate_score_output
    meta = {
        "id": "x", "name": "X", "version": "0", "description": "",
        "level": "transcript",
        "dims": [{
            "key": "foo", "label": {"zh": "F", "en": "F"},
            "score_range": (0, 100), "higher_is_better": True,
            "description": "",
        }],
    }
    with pytest.raises(PluginError, match="missing dim keys"):
        validate_score_output(meta, {})
    with pytest.raises(PluginError, match="outside score_range"):
        validate_score_output(meta, {"foo": 200})
