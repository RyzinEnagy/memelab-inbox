"""Phase 16 re-run: independent check of the point-in-time cohort (stress.empirical_cohort with asof) on a corpus COPY.
For each decision time it recomputes, with plain SQL written here, which cohort tokens were known, which 24 h windows
had closed and been published, and the complete-window returns on the package's chosen pool, then compares.
Usage: python3 audits/backtesting/testing/p16r1_cohort_check.py <copy of bt.sqlite>"""
import json, statistics, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from memelab.backtest import outcomes as O, store, stress as S  # noqa: E402

db = Path(sys.argv[1]); assert db.resolve() != (ROOT / "data/backtest/bt.sqlite").resolve()
con = store.connect(db)
iso = lambda t: time.strftime("%Y-%m-%d %H:%M", time.gmtime(t))
CASES = {"PAID_demo (SETUP DEVELOPING)": (1791330503.698, "SETUP DEVELOPING"), "RUG thesis (REJECTED)": (1791548299.772, "REJECTED"),
         "puter/PQC thesis (REJECTED)": (1791487808.0, "REJECTED"), "QTC thesis (RESEARCH REQUIRED)": (1792491564.0, "RESEARCH REQUIRED"),
         "corpus end (REJECTED)": (1792776856.8, "REJECTED")}
out = {}
for name, (asof, status) in CASES.items():
    pkg = S.empirical_cohort(con, status, asof=asof)
    known = con.execute("SELECT chain, mint, MIN(available_at) t FROM bt_universe_members WHERE universe_id='lab_state_history' AND basis='THESIS' "
                        "AND status_at_entry=? AND available_at<=? GROUP BY chain, mint", (status, asof)).fetchall()
    rets, violations, censored_dead = [], [], 0
    for r in known:
        t, end = r["t"], r["t"] + 86400
        if asof < end + O.LAG_S:
            continue                                            # window not closed and published at asof
        basis, _ = O._basis(con, {"chain": r["chain"], "mint": r["mint"], "decision_time": t})
        if not basis:
            continue
        rows = con.execute("SELECT start, end, o, c, available_at FROM bt_market_bars WHERE chain=? AND mint=? AND pool_address=? AND timeframe_s=3600 "
                           "AND start>=? AND start<? AND available_at<=? ORDER BY start, available_at, id", (r["chain"], r["mint"], basis["pool_address"], t, end, asof)).fetchall()
        first = {}
        for b in rows:
            first.setdefault(b["start"], b)
        bs = [first[k] for k in sorted(first)]
        if not bs:
            continue
        if any(b["available_at"] > asof for b in bs):
            violations.append(r["mint"])
        if bs[-1]["end"] < end - 3600:
            censored_dead += 1
            continue
        rets.append(bs[-1]["c"] / bs[0]["o"] - 1)
    out[name] = {"asof": iso(asof), "package_n": pkg["n"], "package_tier": pkg["tier"], "package_known_tokens": pkg.get("known_tokens"),
                 "package_window_states": pkg.get("window_states"), "independent_known": len(known), "independent_complete_n": len(rets),
                 "independent_censored_early": censored_dead, "package_median": (pkg.get("ret_p10_p50_p90") or [None, None])[1],
                 "independent_median": statistics.median(rets) if rets else None, "bars_after_asof_used": len(violations)}
    out[name]["match"] = (pkg["n"] == len(rets) and pkg.get("known_tokens") == len(known)
                          and (pkg.get("ret_p10_p50_p90") is None or abs(pkg["ret_p10_p50_p90"][1] - statistics.median(rets)) < 1e-12))
print(json.dumps(out, indent=1))
