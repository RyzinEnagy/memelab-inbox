"""Phase 11 checks on the recorded outputs (no new configuration, no new number in any metric table):

1. every fold card header in artifacts/folds/<target>.json, with its fold's pool put back, passes `analog.verify_card` (model sha,
   registry, analog-1 and version 2 definitions), and its pool sha matches;
2. the reproducible cohort query (`cohort_query.query`) gives the trace's answers for every model at the trace's cutoff;
3. day dependence of every out-of-sample answer with a cohort number: the analog days and the day Kish ESS, recomputed through
   `cohort_query.query` at the row's fold cutoff (the frozen rule counts days, not the Kish ESS; this shows how far apart they are).

    python -B postrun_checks.py OUTDIR OUT.json
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("p11_cohort_query", HERE / "cohort_query.py")
CQ = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CQ)
A, B, C = CQ.A, CQ.B, CQ.C


def main() -> int:
    out = Path(sys.argv[1])
    res: dict = {"fold_cards": {"checked": 0, "verified": 0, "pool_sha_equal": 0}}
    for p in sorted((out / "artifacts/folds").glob("*.json")):
        doc = json.loads(p.read_text())
        for f in doc["folds"]:
            for m, head in f["cards"].items():
                if m not in A.MODEL_IDS:
                    continue
                res["fold_cards"]["checked"] += 1
                card = {k: v for k, v in head.items() if k != "pool_sha"}
                card["body"] = dict(head["body"], pool=f["pool"])
                res["fold_cards"]["pool_sha_equal"] += int(B.sha(f["pool"]) == head["pool_sha"])
                try:
                    A.verify_card(card)
                    res["fold_cards"]["verified"] += 1
                except Exception as e:      # noqa: BLE001 - recorded, then the check fails
                    res["fold_cards"].setdefault("errors", []).append(f"{p.name} {f['fold']} {m}: {e}")
    ctx = CQ.build()
    trace = json.loads((out / "evidence/trace/trace.json").read_text())
    q_rows = []
    for t in trace:
        q = CQ.query(ctx, t["target_short"], t["decision_key"], t["cutoff"])
        eq = {m: (q["answers"][m]["number"] == t["answers"][m]["number"]
                  and [x["decision_key"] for x in q["answers"][m]["analogs"]] == [x["decision_key"] for x in t["answers"][m]["analogs"]]
                  and q["answers"][m]["reasons"] == t["answers"][m]["reasons"]) for m in A.MODEL_IDS}
        q_rows.append({"target_short": t["target_short"], "decision_key": t["decision_key"][:12], "as_of_utc": B._iso(t["cutoff"]),
                       "equal": eq, "router_path": q["router"]["path"], "router_reasons": q["router"].get("reasons")})
    res["cohort_query"] = {"queries": q_rows, "pass": all(all(r["equal"].values()) for r in q_rows)}
    dd = []
    for r in csv.DictReader(open(out / "experiments/OOS_PREDICTIONS.csv")):
        for m in ("AC2_KNN", "AC3_KNN_REGIME"):
            if r[m] in ("", None):
                continue
            q = CQ.query(ctx, r["target_short"], r["decision_key"], C.parse_utc(r["cutoff_utc"]), models=(m,))
            a = q["answers"][m]
            if abs(a["number"] - float(r[m])) > 5e-7:
                raise SystemExit(f"cohort query disagrees with OOS_PREDICTIONS for {r['decision_key'][:12]} {m}")
            days = {}
            for x in a["analogs"]:
                days[x["day"]] = days.get(x["day"], 0) + 1
            dd.append({"target_short": r["target_short"], "decision_key": r["decision_key"][:12], "model": m, "G": a["G"],
                       "analog_days": a["analog_days"], "day_kish_ess": round(a["day_kish_ess"], 4),
                       "largest_day_share": round(max(days.values()) / a["G"], 4)})
    res["day_dependence"] = {"answers_with_number": len(dd),
                             "kish_below_5": sum(1 for x in dd if x["day_kish_ess"] < 5),
                             "kish_below_3": sum(1 for x in dd if x["day_kish_ess"] < 3),
                             "max_largest_day_share": max((x["largest_day_share"] for x in dd), default=None),
                             "min_day_kish_ess": min((x["day_kish_ess"] for x in dd), default=None), "rows": dd}
    res["pass"] = (res["fold_cards"]["verified"] == res["fold_cards"]["checked"] == res["fold_cards"]["pool_sha_equal"]
                   and res["cohort_query"]["pass"])
    Path(sys.argv[2]).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: (v if k != "day_dependence" else {kk: vv for kk, vv in v.items() if kk != "rows"}) for k, v in res.items()
                      if k != "cohort_query"} | {"cohort_query_pass": res["cohort_query"]["pass"]}))
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
