"""rubric CLI — list metrics, run one over a transcript file.

Usage:
    python -m rubric list
    python -m rubric run parrot-check examples/x03_q6.json
    python -m rubric run-all transcripts.jsonl       # all transcript-level metrics
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

from . import load, load_all, run

_ROLE_ALIASES_A = {"assistant", "面试官", "interviewer", "agent", "ai"}
_ROLE_ALIASES_U = {"user", "受访者", "respondent", "human"}


def _parse_txt(text: str) -> list[dict]:
    """Parse Pikaia-style [面试官]/[受访者] alternating lines into turns."""
    turns = []
    cur_role, cur_buf = None, []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^\[?([\w一-鿿]+)\]?\s*[:：]?\s*(.*)", line)
        if m and (line.startswith("[") or m.group(1).lower() in _ROLE_ALIASES_A | _ROLE_ALIASES_U):
            if cur_role:
                turns.append({"role": cur_role, "text": " ".join(cur_buf).strip()})
            cur_role = m.group(1)
            cur_buf = [m.group(2)] if m.group(2) else []
        elif cur_role is not None:
            cur_buf.append(line)
    if cur_role:
        turns.append({"role": cur_role, "text": " ".join(cur_buf).strip()})
    return turns


def _load_sample(path: pathlib.Path):
    """Load a transcript / utterance file. JSON / JSONL / TXT supported."""
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in (".json", ".jsonl"):
        obj = json.loads(text.splitlines()[0]) if suffix == ".jsonl" else json.loads(text)
        if isinstance(obj, list):
            return obj
        for key in ("turns", "transcript", "messages"):
            if isinstance(obj, dict) and isinstance(obj.get(key), list):
                return obj[key]
        return obj
    return _parse_txt(text)


def _cmd_list(args):
    reg = load_all(args.metrics_dir)
    if args.json:
        print(json.dumps(
            [{"id": m.id, "name": m.meta["name"], "version": m.meta["version"],
              "level": m.level, "dims": m.dim_keys, "description": m.meta["description"]}
             for m in reg.values()],
            ensure_ascii=False, indent=2,
        ))
        return 0
    print(f"{len(reg)} metric(s) loaded\n")
    for m in reg.values():
        print(f"  {m.id:<20} {m.meta['version']:<8} {m.level:<10}  {m.meta['name']}")
        print(f"  {'':<20} {'':<8} {'':<10}  {m.meta['description']}")
        for d in m.meta["dims"]:
            arrow = "↑" if d["higher_is_better"] else "↓"
            print(f"  {'':<22}{arrow} {d['key']:<28} {d['label']['zh']} / {d['label']['en']}")
        print()
    return 0


def _cmd_run(args):
    metric = load(args.metric_id, args.metrics_dir)
    sample = _load_sample(args.sample)
    result = run(metric, sample)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(f"metric:  {metric.id} v{metric.meta['version']}")
    print(f"sample:  {args.sample.name}")
    print()
    dim_map = {d["key"]: d for d in metric.meta["dims"]}
    for k, v in result.items():
        if k in dim_map:
            d = dim_map[k]
            lo, hi = d["score_range"]
            arrow = "↑" if d["higher_is_better"] else "↓"
            print(f"  {arrow} {d['label']['zh']} ({d['label']['en']}): "
                  f"{v:>8.2f} / {hi:<6}  {d['description']}")
        else:
            print(f"    {k}: {v!r}  (diagnostic)")
    return 0


def _cmd_run_all(args):
    reg = load_all(args.metrics_dir)
    sample = _load_sample(args.sample)
    out = {}
    for mid, m in reg.items():
        if m.level != "transcript":
            continue
        try:
            out[mid] = run(m, sample)
        except Exception as e:
            out[mid] = {"_error": str(e)}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rubric", description="Pluggable interview metric framework.")
    ap.add_argument("--metrics-dir", type=pathlib.Path, default=None,
                    help="Override the metrics/ folder (default: bundled).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="List discovered metric plugins.")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_cmd_list)

    p = sub.add_parser("run", help="Run one metric on a sample file.")
    p.add_argument("metric_id")
    p.add_argument("sample", type=pathlib.Path)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_cmd_run)

    p = sub.add_parser("run-all", help="Run every transcript-level metric on the sample.")
    p.add_argument("sample", type=pathlib.Path)
    p.set_defaults(func=_cmd_run_all)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
