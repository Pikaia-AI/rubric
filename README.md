# rubric

Pluggable interview metric framework. Drop a folder under `metrics/` with a `metric.py` exposing `META` + `score()`, and the loader picks it up. Consumers (`pikaia_eval`, standalone CLI, future Node bridge, etc.) all see the same registry.

## Why

Pikaia had two divergent code paths for the same metric: `pikaia_eval/adapters/parrot_check_adapter.py` and the standalone `parrot-check` skill. Bugs in one wouldn't reach the other. This repo is the single source of truth — both consumers vendor or `pip install` from here.

Future metrics (semantic-echo, outline-tightness, time-pacing, etc.) follow the same plugin shape so they auto-show on any consumer that has rubric installed.

## Quick start

```bash
git clone https://github.com/Pikaia-AI/rubric && cd rubric
python -m rubric list                                           # see all metrics
python -m rubric run parrot-check metrics/parrot_check/examples/x03_q6.json
python -m rubric run-all metrics/parrot_check/examples/x03_q6.json    # everything transcript-level
```

As a library:

```python
from rubric import load_all, load, run

registry = load_all()                           # {metric_id: Metric}
m = load("parrot-check")
result = run(m, turns)                          # validates output against META
print(result["paraphrase_rate"])                # 0-100
```

Install editable for dev:

```bash
pip install -e .
rubric list                                     # the CLI is also a console_script
```

## Plugin contract

```
metrics/<your-metric>/
├── metric.py        # required: exposes META (dict) + score (callable)
├── README.md        # recommended: algorithm + worked example
└── examples/        # recommended: sample input files
    └── *.json
```

`metric.py`:

```python
META = {
    "id": "your-metric",              # kebab-case, unique
    "name": "Your Metric",
    "version": "0.1.0",
    "description": "one line",
    "level": "transcript",            # or "utterance"
    "dims": [
        {
            "key": "your_dim",        # snake_case, unique within this metric
            "label": {"zh": "维度", "en": "Your Dim"},
            "score_range": (0, 100),
            "higher_is_better": True,
            "description": "what it measures",
            # Optional: "category": "提问质量",
        },
    ],
    # Optional fields:
    # "homepage":  "https://...",
    # "paper":     "Smith et al., NeurIPS 2025",
    # "deterministic": True,           # no LLM/network call
    # "needs_api_key": "OPENAI_API_KEY",
}

def score(sample):
    # sample = turns list[{"role", "text"}] if level='transcript'
    # sample = example dict {"context": [...], "probe_text": ...} if 'utterance'
    return {
        "your_dim": 42.0,             # must lie in score_range
        # Extra diagnostic keys allowed; consumers filter them.
    }
```

The loader validates META + score() output. Malformed plugins raise `PluginError` and fail discovery (unless `strict=False` is passed to `load_all`).

### Role aliases (transcript level)

Plugins should treat these as the same when iterating `turns`:

| canonical | aliases |
|---|---|
| `assistant` | `面试官`, `interviewer`, `agent`, `ai` |
| `user` | `受访者`, `respondent`, `human` |

The bundled `parrot_check` does this — copy its `_norm_role` if you need it.

## Currently bundled

| id | level | dims | LLM | description |
|---|---|---|---|---|
| `parrot-check` | transcript | 改述率 / 一题一问率 | no | char-bigram echo + question count |

## Integrating with pikaia_eval

Eval has its own adapter framework (`adapters/<x>_adapter.py`). The thin adapter pattern:

```python
# pikaia_eval/adapters/parrot_check_adapter.py
import rubric

_metric = rubric.load("parrot-check")

BENCH_META = {
    "id": "parrot",
    "name": _metric.meta["name"],
    "group_prefix": "内部",
    "paper": _metric.meta.get("homepage", ""),
    "level": _metric.level,
    "score_range": _metric.meta["dims"][0]["score_range"],
    "api_key_env": "",
    "priority": 15,
    "dims": [
        {"key": d["key"], "label_zh": d["label"]["zh"], "label_en": d["label"]["en"],
         "category": d.get("category", "")}
        for d in _metric.meta["dims"]
    ],
}

def score(turns):
    out = _metric.score(turns)
    return {k: out[k] for k in (d["key"] for d in _metric.meta["dims"])}
```

Then eval's Dockerfile gets `pip install rubric` and the algorithm has one home.

## Roadmap

- [x] `parrot-check` (char-bigram echo + multi-question)
- [ ] `semantic-echo` (sentence-embedding cosine — catches the ASR-typo blind spot)
- [ ] `outline-tightness` (visited-section coverage and detours)
- [ ] `time-pacing` (turn rate / pause distribution)
- [ ] Node bridge (so bench.trooly.ai's Next.js can call the same metrics)
