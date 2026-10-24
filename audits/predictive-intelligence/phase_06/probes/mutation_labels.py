"""Phase 06 mutation check: every mutation of labels.py must make the Phase 06 label tests fail.

Each mutation is one exact text replacement in memelab/predictive/labels.py, applied to a copy of memelab/ and tests/ in a
temporary folder; `pytest tests/test_predictive_labels.py -x -q` runs there. A mutation whose text is not found is an error (the
check would be vacuous). Nothing in the repository is changed.

    python -B mutation_labels.py OUT.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TEST = "tests/test_predictive_labels.py"
F = "memelab/predictive/labels.py"

MUTATIONS = [
    ("tie resolved positive", 'cls = "AMBIGUOUS_BAR" if (up and lo) else', 'cls = "TARGET_FIRST" if (up and lo) else'),
    ("upper barrier strict", "up, lo = c[2] >= U, c[3] <= L", "up, lo = c[2] > U, c[3] <= L"),
    ("pending ignored", 'elif rd.retrieved_at < rec["label_matures_at"]:', "elif False:"),
    ("path includes the candle holding t_entry", "    path = C.path_candles(list(read.candles), decision_time, H)",
     "    path = sorted((c for c in read.candles if c[0] + 300 > decision_time + 300 and c[0] + 300 <= decision_time + 300 + H), key=lambda c: c[0])"),
    ("empty page read as no trade", "    return (read is not None and read.ok and read.boundary >= ceil_grid(e) and read.cover_from is not None\n            and read.cover_from < s)",
     "    return read is not None and read.ok and read.boundary >= ceil_grid(e)"),
    ("absence ignores the boundary", "read.boundary >= ceil_grid(e) and read.cover_from is not None",
     "read.cover_from is not None"),
    ("other pool not evidenced counts as quiet", '    if any(x["state"] != "QUIET_EVIDENCED" for x in seen):',
     '    if any(x["state"] == "READ_FAILED" for x in seen):'),
    ("halt without other pools", "    if other_reads is None:\n        return out | {\"state\": NEEDS_OTHER_POOLS",
     "    if other_reads is None:\n        other_reads = []\n    if False:\n        return out | {\"state\": NEEDS_OTHER_POOLS"),
    ("list failure means halt", '    if other_reads == LIST_FAILED:\n        return out | {"state": "UNVERIFIABLE_NO_VENDOR_HISTORY"',
     '    if other_reads == LIST_FAILED:\n        other_reads = []\n    if False:\n        return out | {"state": "UNVERIFIABLE_NO_VENDOR_HISTORY"'),
    ("drawdown threshold from the T1 lower barrier", '    Dd = p0 * tg["drawdown"]', "    Dd = p0 * 0.85"),
    ("no thinning", '        kept = {d["decision_key"] for d in D.thin(eligible, C.TARGETS[target]["horizon_s"])}',
     '        kept = {d["decision_key"] for d in eligible}'),
    ("purge ignored", '    return "DEVELOPMENT" if C.label_matures_at(target, decision_time) <= h0 else "PURGED"', '    return "DEVELOPMENT"'),
    ("identity not checked on reads", '    if not ident.startswith("OK"):\n        return Read(identity=ident, raw_count=len(rows), **base)',
     '    if False:\n        return Read(identity=ident, raw_count=len(rows), **base)'),
    ("boundary candle kept", "        if start + period > float(boundary) or start in kept:", "        if start in kept:"),
    ("read of another mint accepted", '            if rd is not None and (rd.mint != d["mint"] or (d.get("pool") and rd.pool != d["pool"])):',
     "            if False:"),
    ("training gate ignores maturity", '        if avail > as_of or r["label_matures_at"] > as_of:', "        if False:"),
    ("training gate skips the bake-off guard", "    R.refuse_bakeoff_labels(rows)\n", ""),
    ("capture mode ignored", '        if mode == "capture":\n            avail = max(avail, r["label_observed_at"])', '        if False:\n            pass'),
    ("revision used before its read", '        avail = r["label_matures_at"] if r["revision_of"] is None else max(r["label_observed_at"], r["label_matures_at"])',
     '        avail = r["label_matures_at"]'),
    ("holdout rows allowed in the table", '    if rec["split"] == "HOLDOUT":\n        raise LabelError("holdout labels never enter',
     '    if False:\n        raise LabelError("holdout labels never enter'),
    ("revision check ignores the 48 h gap", '    return {"gap_s": gap, "frozen_check": gap >= gap_req,', '    return {"gap_s": gap, "frozen_check": True,'),
    ("cross-target first-touch invariant off", '            if (r1["label_class"], r1.get("first_touch_start")) != (r["label_class"], r.get("first_touch_start")):',
     "            if False:"),
    ("seal ignores content", '        elif p.stat().st_size != meta["bytes"] or file_sha256(p) != meta["sha256"]:', "        elif False:"),
    ("wick flag off", "                if c[5] < wick:\n                    flags.append(\"WICK_TOUCH\")\n                break",
     "                break"),
    ("forbidden field names allowed", "        if any(w in str(k).lower() for w in FORBIDDEN_NAME_WORDS):", "        if False:"),
]


def apply(root: Path, old: str, new: str) -> None:
    p = root / F
    s = p.read_text()
    if s.count(old) != 1:
        raise SystemExit(f"mutation text found {s.count(old)} times: {old[:70]!r}")
    p.write_text(s.replace(old, new))


def run(root: Path) -> int:
    return subprocess.run([sys.executable, "-m", "pytest", TEST, "-x", "-q", "-p", "no:cacheprovider"], cwd=root,
                          capture_output=True, text=True).returncode


def main(out: str) -> None:
    res = []
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "base"
        base.mkdir()
        for d in ("memelab", "tests"):
            shutil.copytree(REPO / d, base / d, ignore=shutil.ignore_patterns("__pycache__"))
        ctl = run(base)
        for name, old, new in MUTATIONS:
            work = Path(tmp) / "w"
            if work.exists():
                shutil.rmtree(work)
            shutil.copytree(base, work)
            apply(work, old, new)
            t0 = time.time()
            rc = run(work)
            res.append({"mutation": name, "caught": rc != 0, "exit": rc, "seconds": round(time.time() - t0, 1)})
            print(json.dumps(res[-1]), flush=True)
    summary = {"control_exit": ctl, "mutations": len(res), "caught": sum(r["caught"] for r in res), "results": res}
    Path(out).write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}))


if __name__ == "__main__":
    main(sys.argv[1])
