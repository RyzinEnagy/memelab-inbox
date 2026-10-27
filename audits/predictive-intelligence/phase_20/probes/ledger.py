"""Phase 20 search ledger: the Phase 19 cumulative ledger plus one row per Phase 20 audit run (debug runs before the frozen audit
code and the recorded runs). No row is a candidate configuration: N_search stays 130 (169 with the rule configurations).

    python -B ledger.py PHASE20_DIR
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
CLAIM = "AUDIT_RUN_NOT_A_CONFIGURATION"
DEBUG = [
    ("P20:DEBUG:1", "DEBUG_RUN_FIXTURE", "X02 prototype before the pre-registration: cross-wired token row in the export replay (fixture champion)"),
    ("P20:DEBUG:2", "DEBUG_RUN_FIXTURE", "X03 prototype before the pre-registration: millisecond capture and observed times (fixture champion)"),
    ("P20:DEBUG:3", "DEBUG_RUN_FIXTURE", "X06 prototype while writing the scenario checks: a card fitted on labels maturing after its cutoff served "
                                         "as a fixture champion (published a FORECAST)"),
    ("P20:DEBUG:4", "DEBUG_RUN_FIXTURE", "scenario checks P01 to P48 developed at uncommitted audit code (fixtures and committed files only)"),
    ("P20:DEBUG:5", "DEBUG_RUN_REAL_DATA", "independent recalculation at uncommitted audit code (committed raw archives, exports, cards; "
                                           "a 61 of 61, b 40 of 40, c 168 of 168, two traces)"),
    ("P20:DEBUG:6", "DEBUG_RUN_REAL_DATA", "out-of-sample sensitivity at uncommitted audit code (committed scored rows of the spent holdout and "
                                           "the prospective window)"),
    ("P20:DEBUG:7", "DEBUG_RUN_REAL_DATA", "flag-off identity at uncommitted audit code (two exports; first form compared a malformed config "
                                           "only with the no-config base; the script was changed to compare each config with the same base)"),
    ("P20:DEBUG:8", "DEBUG_RUN_REAL_DATA", "reproduction entry points at uncommitted audit code in a sandbox at 9e1f29d"),
    ("P20:DEBUG:9", "DEBUG_RUN_REAL_DATA", "threat scan and counterexample rerun at uncommitted audit code"),
]
RECORDED = ["P20:SCENARIOS", "P20:MAPPED_TESTS", "P20:CX_RERUN", "P20:CROSS", "P20:REPRO", "P20:E2E", "P20:SMOKE", "P20:FLAG_OFF",
            "P20:FRESH_ENV", "P20:RELEASE_AUDIT", "P20:RECALC", "P20:OOS_SENSITIVITY", "P20:THREATS", "P20:OPERATIONS"]


def main(out: Path, frozen: str) -> int:
    base = list(csv.DictReader(open(AUD / "phase_19/experiments/SEARCH_LEDGER.csv")))
    cols = list(base[0].keys())
    new = []
    for eid, kind, what in DEBUG:
        new.append({c: "" for c in cols} | {"phase": "20", "experiment_id": eid, "candidate": "P20_DEBUG", "kind": kind, "view": "ALL",
                                            "verdict": what, "claim": CLAIM})
    for eid in RECORDED:
        kind = "POST_OPENING_DESCRIPTIVE" if eid == "P20:OOS_SENSITIVITY" else "TRAP_OR_CHECK"
        new.append({c: "" for c in cols} | {"phase": "20", "experiment_id": eid, "candidate": "P20_AUDIT", "kind": kind, "view": "ALL",
                                            "verdict": f"recorded audit run at the frozen audit code {frozen}", "claim": CLAIM})
    rows = base + new
    (out / "experiments").mkdir(parents=True, exist_ok=True)
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
    return 0 if tot["after"]["n_search"] == 130 and tot["after"]["n_search_sensitivity"] == 169 else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), sys.argv[2]))
