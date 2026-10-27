"""Repair pass 2 (PI-D-082): compare the coding and scoring outputs repeated at the repair commit, and the twin of the mint-null
addition, with the committed files. Run logs may differ only in times and head.

    python -B rerun_rp2_diff.py CODING_DIR SCORING_DIR TWIN_DIR OUT.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

P15 = Path(__file__).resolve().parents[1]
CODING = ["behavioral/SCENARIO_CODING.csv", "behavioral/CONTROL_CODING.csv", "behavioral/EVENT_SET.csv", "behavioral/HOLDOUT_RULE_SCENARIOS.jsonl"]
SCORING = ["behavioral/INCREMENTAL_VALUE_RESULTS.json", "behavioral/E1_OOS_ROWS.csv", "behavioral/E2_SCORED_ROWS.csv",
           "behavioral/POST_OPENING_LOG.json", "experiments/SEARCH_LEDGER.csv", "experiments/LEDGER_TOTALS.json"]
ADDITION = ["behavioral/MINT_CLUSTERED_NULL.json", "experiments/SEARCH_LEDGER_RP2_ADDITION.csv", "experiments/REGISTRY_LEDGER_MAP.csv"]
LOGS = {"behavioral/CODING_LOG.json": 0, "evidence/score_run_log.json": 1, "evidence/mint_null_run_log.json": 2}


def h(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(c: str, s: str, t: str, out: str) -> int:
    dirs = [Path(c), Path(s), Path(t)]
    res = {"files": {}, "logs": {}}
    for i, group in enumerate((CODING, SCORING, ADDITION)):
        for f in group:
            res["files"][f] = {"byte_equal": h(dirs[i] / f) == h(P15 / f), "sha256": h(P15 / f)}
    for f, i in LOGS.items():
        a, b = json.loads((P15 / f).read_text()), json.loads((dirs[i] / f).read_text())
        res["logs"][f] = {"differing_keys": sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))}
    allowed = {"start_utc", "end_utc", "head"}
    res["ok"] = all(v["byte_equal"] for v in res["files"].values()) and all(set(v["differing_keys"]) <= allowed for v in res["logs"].values())
    Path(out).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"ok": res["ok"], "logs": res["logs"]}))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:5]))
