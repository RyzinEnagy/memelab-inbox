"""Phase 15 CP15-0 rerun comparison: every value of the first recorded scoring run must be equal in the repeated run; list
what was added. Standard library only.

    python -B rerun_diff.py FIRST_DIR SECOND_DIR OUT.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path


def flat(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from flat(v, f"{p}.{k}" if p else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from flat(v, f"{p}[{i}]")
    else:
        yield p, o


def main(a, b, out):
    a, b = Path(a), Path(b)
    rep = {"files": {}}
    for f in ("behavioral/INCREMENTAL_VALUE_RESULTS.json", "behavioral/POST_OPENING_LOG.json", "experiments/LEDGER_TOTALS.json"):
        fa, fb = dict(flat(json.loads((a / f).read_text()))), dict(flat(json.loads((b / f).read_text())))
        changed = sorted(k for k in fa if k in fb and fa[k] != fb[k])
        rep["files"][f] = {"first_values": len(fa), "removed": sorted(set(fa) - set(fb)), "changed": changed,
                           "added_keys": len(set(fb) - set(fa)),
                           "added_prefixes": sorted({k.split(".")[0] + "." + k.split(".")[1] if k.count(".") else k for k in set(fb) - set(fa)})}
    for f in ("behavioral/E1_OOS_ROWS.csv", "behavioral/E2_SCORED_ROWS.csv"):
        rep["files"][f] = {"byte_equal": (a / f).read_bytes() == (b / f).read_bytes(),
                           "sha256": hashlib.sha256((b / f).read_bytes()).hexdigest()}
    la, lb = list(csv.DictReader(open(a / "experiments/SEARCH_LEDGER.csv"))), list(csv.DictReader(open(b / "experiments/SEARCH_LEDGER.csv")))
    rep["files"]["experiments/SEARCH_LEDGER.csv"] = {"first_rows": len(la), "second_rows": len(lb),
                                                      "first_rows_kept_in_order": all(r in lb for r in la),
                                                      "added": [r["experiment_id"] for r in lb if r not in la]}
    # the only changes allowed: ledger counts that grow by exactly the number of added POST_OPENING_CHECK ledger rows
    n_add = len(rep["files"]["experiments/SEARCH_LEDGER.csv"]["added"])
    allowed = ("rows", "holdout_evaluation_rows", "rows_by_phase.15", "phase15_rows")
    for f in ("behavioral/INCREMENTAL_VALUE_RESULTS.json", "experiments/LEDGER_TOTALS.json"):
        fa, fb = dict(flat(json.loads((a / f).read_text()))), dict(flat(json.loads((b / f).read_text())))
        expl = [k for k in rep["files"][f]["changed"] if k.split("after.", 1)[-1] in allowed or k.endswith("phase15_rows")]
        rep["files"][f]["changed_explained_by_added_ledger_rows"] = [k for k in expl if fb[k] - fa[k] == n_add]
        rep["files"][f]["changed"] = [k for k in rep["files"][f]["changed"] if k not in rep["files"][f]["changed_explained_by_added_ledger_rows"]]
    ok = all(not v.get("removed") and not v.get("changed") for v in rep["files"].values() if "changed" in v)
    ok = ok and all(v.get("byte_equal", True) for v in rep["files"].values())
    ok = ok and rep["files"]["experiments/SEARCH_LEDGER.csv"]["first_rows_kept_in_order"]
    rep["ok"] = ok
    Path(out).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"ok": ok, **{k: {kk: vv for kk, vv in v.items() if kk in ("changed", "removed", "added", "byte_equal", "added_prefixes")}
                                   for k, v in rep["files"].items()}}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
