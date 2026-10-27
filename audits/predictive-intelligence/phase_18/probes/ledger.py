"""Phase 18 search ledger: the Phase 17 cumulative ledger plus one row per Phase 18 run on real data (debug runs before the frozen
code and the recorded runs). No row is a candidate configuration: N_search stays 130 (169 with the rule configurations).

    python -B ledger.py PHASE18_DIR
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from memelab.predictive import evaluation as E  # noqa: E402

AUD = REPO / "audits/predictive-intelligence"
CLAIM = "REPORT_RUN_NOT_A_CONFIGURATION"
DEBUG = [   # every Phase 18 run on real data before the frozen code (P22), all on the entry-gate smoke state in the scratchpad
    ("P18:DEBUG:1", "report on the entry-gate smoke state between 2026-10-27T09:49Z and 09:56Z at uncommitted code: refused by its own text check "
                    "(the report's own wording carried a word of the Phase 18 list); wording changed"),
    ("P18:DEBUG:2", "report on the entry-gate smoke state between 2026-10-27T09:49Z and 09:56Z after the wording fix: complete, 8 opportunities, 24 abstentions, 0 numbers"),
    ("P18:DEBUG:3", "report on the entry-gate smoke state 2026-10-27T09:56:50Z after the section layout change: complete, same counts"),
    ("P18:DEBUG:4", "alerts dry run, alerts-state and a refused --send on the entry-gate smoke state 2026-10-27T09:56:58Z: 0 alerts, "
                    "3 risk_override candidates suppressed SOURCE_STALE"),
]
RECORDED = ["P18:REAL_SCOUT_SMOKE", "P18:REAL_SCOUT_REPORT", "P18:REAL_SCOUT_ALERTS", "P18:REAL_REPLAY", "P18:REAL_REPLAY_REPORT",
            "P18:REAL_REPLAY_ALERTS"]
REPEATS = [("CP18_0", "0127d2e", "PI-D-099, evidence/rerun_cp18_0_diff.json")]


def main(out: Path) -> int:
    base = list(csv.DictReader(open(AUD / "phase_17/experiments/SEARCH_LEDGER.csv")))
    cols = list(base[0].keys())
    new = []
    for eid, what in DEBUG:
        new.append({c: "" for c in cols} | {"phase": "18", "experiment_id": eid, "candidate": "P18_DEBUG", "kind": "DEBUG_RUN_REAL_DATA",
                                            "view": "ALL", "verdict": what, "claim": CLAIM})
    for eid in RECORDED:
        new.append({c: "" for c in cols} | {"phase": "18", "experiment_id": eid, "candidate": "P18_REPORTS", "kind": "TRAP_OR_CHECK",
                                            "view": "ALL", "verdict": "recorded run at the frozen code 96c4445 (real/ at 3601881)", "claim": CLAIM})
    for cp, code, why in REPEATS:   # the recorded runs repeated at each change-control commit are runs on real data too (P22)
        for eid in RECORDED:
            new.append({c: "" for c in cols} | {"phase": "18", "experiment_id": eid.replace("P18:", f"P18:{cp}:"), "candidate": "P18_REPORTS",
                                                "kind": "TRAP_OR_CHECK", "view": "ALL", "verdict": f"recorded run repeated at {code} ({why})",
                                                "claim": CLAIM})
    rows = base + new
    with open(out / "experiments/SEARCH_LEDGER.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    tot = {"before": E.ledger_totals(base) | {"n_search_sensitivity": E.ledger_totals(base)["n_search"] + E.rule_configurations(base)},
           "after": E.ledger_totals(rows) | {"n_search_sensitivity": E.ledger_totals(rows)["n_search"] + E.rule_configurations(rows)},
           "added_rows": len(new), "claim": CLAIM}
    (out / "experiments/LEDGER_TOTALS.json").write_text(json.dumps(tot, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"rows": len(rows), "added": len(new), "n_search": tot["after"]["n_search"],
                      "sensitivity": tot["after"]["n_search_sensitivity"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
