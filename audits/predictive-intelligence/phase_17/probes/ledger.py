"""Phase 17 search ledger: the Phase 16 cumulative ledger plus one row per Phase 17 run on real data (debug runs before the frozen
code and the recorded runs). No row is a candidate configuration: N_search stays 130 (169 with the rule configurations).

    python -B ledger.py PHASE17_DIR
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
CLAIM = "INTEGRATION_RUN_NOT_A_CONFIGURATION"
DEBUG = [   # every run of a Phase 17 probe on real data before the frozen code (P22), all into the scratchpad
    ("P17:DEBUG:1", "replay dbg1 2026-10-27T06:04:08Z at uncommitted code: stopped after round 2 reading the absent "
                    "REFERENCE_RECORDS.jsonl (no pin existed before 2026-10-27, so no reference was scored); the probe now reads it "
                    "only when present"),
    ("P17:DEBUG:2", "replay dbg2 2026-10-27T06:04:41Z: complete, 52 window events, round 1 DISCOVERY 47 MATERIAL_CHANGE 5, "
                    "round 2 DUPLICATE 52, 0 probabilities"),
    ("P17:DEBUG:3", "real_path_smoke dbg1 2026-10-27T06:05:46Z (WORKTREE): complete, all exits 0, base and frozen OFF equal; "
                    "the compare step did not exist yet"),
    ("P17:DEBUG:4", "real_path_smoke dbg2 2026-10-27T06:07:10Z (WORKTREE) with the compare step: complete; then tests were "
                    "added for 3 mutation survivors (code unchanged by them)"),
]
RECORDED = ["P17:REAL_SCOUT_OFF_BASE", "P17:REAL_SCOUT_OFF_FROZEN", "P17:REAL_SCOUT_ON", "P17:REAL_SCOUT_RERUN", "P17:REAL_SCOUT_RETRY",
            "P17:REAL_SCOUT_STORM", "P17:REAL_SCOUT_RESEARCH", "P17:REAL_ANALYZE_ON", "P17:REAL_EXPORT_REPLAY:ROUND_1",
            "P17:REAL_EXPORT_REPLAY:ROUND_2"]

REPEATS = [("CP17_0", "6172b49", "PI-D-094, evidence/rerun_cp17_0_diff.json; rows added late, in the CP17-1 repair"),
           ("CP17_1", "148e3da", "PI-D-096, evidence/rerun_rp2_diff.json")]


def main(out: Path) -> int:
    base = list(csv.DictReader(open(AUD / "phase_16/experiments/SEARCH_LEDGER.csv")))
    cols = list(base[0].keys())
    new = []
    for eid, what in DEBUG:
        new.append({c: "" for c in cols} | {"phase": "17", "experiment_id": eid, "candidate": "P17_DEBUG", "kind": "DEBUG_RUN_REAL_DATA",
                                            "view": "ALL", "verdict": what, "claim": CLAIM})
    for eid in RECORDED:
        new.append({c: "" for c in cols} | {"phase": "17", "experiment_id": eid, "candidate": "P17_INTEGRATION", "kind": "TRAP_OR_CHECK",
                                            "view": "ALL", "verdict": "recorded run at the frozen code (smoke/)", "claim": CLAIM})
    for cp, code, why in REPEATS:   # CP17-1: the recorded runs repeated at each change-control commit are runs on real data too (P22)
        for eid in RECORDED:
            new.append({c: "" for c in cols} | {"phase": "17", "experiment_id": eid.replace("P17:", f"P17:{cp}:"), "candidate": "P17_INTEGRATION",
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
