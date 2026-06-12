"""Smoke tests for the plugin contract + the bundled parrot-check metric."""
import json
import pathlib

import pytest

from rubric import load, load_all, run, validate_meta, PluginError


REPO = pathlib.Path(__file__).parent.parent


def test_discovery():
    reg = load_all()
    assert "parrot-check" in reg
    assert reg["parrot-check"].level == "transcript"


def test_meta_shape():
    m = load("parrot-check")
    validate_meta(m.meta, source="parrot-check")
    assert {d["key"] for d in m.meta["dims"]} == {"paraphrase_rate", "single_question_rate"}


def test_parrot_score_on_example():
    m = load("parrot-check")
    sample_path = REPO / "rubric/builtin_metrics/parrot_check/examples/x03_q6.json"
    sample = json.loads(sample_path.read_text(encoding="utf-8"))["turns"]
    result = run(m, sample)
    # Known X03 Q6 numbers — must stay byte-identical to pikaia_eval + standalone
    assert result["paraphrase_rate"] == pytest.approx(46.07, abs=0.01)
    assert result["single_question_rate"] == pytest.approx(50.0, abs=0.01)
    # Diagnostics present
    assert result["n_agent_turns"] == 6
    assert isinstance(result["per_turn"], list)


def test_unknown_metric_raises():
    with pytest.raises(PluginError, match="not found"):
        load("does-not-exist")


def test_score_validation_catches_bad_dim():
    """A malformed score() output should be caught by validate_score_output."""
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
    # Missing dim
    with pytest.raises(PluginError, match="missing dim keys"):
        validate_score_output(meta, {})
    # Out of range
    with pytest.raises(PluginError, match="outside score_range"):
        validate_score_output(meta, {"foo": 200})
