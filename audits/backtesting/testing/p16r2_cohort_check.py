"""Phase 16 re-run 2: independent recomputation of stress.empirical_cohort (pass-2 definition) on a corpus COPY.
Known tokens, window closure, bars available at the as-of, the pool-disagreement guard (written here), returns
including windows cut short (last close), complete-only returns, worst drops and the selection-bias flag are all
computed with plain SQL in this file. Only the pool choice reuses the package (outcomes._basis with latest=asof).
Usage: python3 audits/backtesting/testing/p16r2_cohort_check.py <copy of bt.sqlite>"""
import json, math, statistics, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from memelab.backtest import outcomes as O, store, stress as S  # noqa: E402

db = Path(sys.argv[1]); assert db.resolve() != (ROOT / "data/backtest/bt.sqlite").resolve()
con = store.connect(db)
iso = lambda t: time.strftime("%Y-%m-%d %H:%M", time.gmtime(t))
q = lambda v, p: sorted(v)[max(0, min(len(v) - 1, int(p * len(v))))]
CASES = {"PAID demo (SETUP DEVELOPING)": (1791330503.698, "SETUP DEVELOPING"), "RUG thesis (REJECTED)": (1791548299.772, "REJECTED"),
         "puter/PQC thesis (REJECTED)": (1791487808.0, "REJECTED"), "QTC thesis (RESEARCH REQUIRED)": (1792491564.0, "RESEARCH REQUIRED"),
         "corpus end (REJECTED)": (1792776856.8, "REJECTED"), "corpus end (RESEARCH REQUIRED)": (1792776856.8, "RESEARCH REQUIRED")}


def first_versions(chain, mint, pool, a, b, asof):
    rows = con.execute("SELECT start, end, o, l, c, volume_usd v FROM bt_market_bars WHERE chain=? AND mint=? AND pool_address=? AND timeframe_s=3600 "
                       "AND start>=? AND start<? AND available_at<=? ORDER BY start, available_at, id", (chain, mint, pool, a, b, asof)).fetchall()
    best = {}
    for r in rows:
        best.setdefault(r["start"], r)
    return [best[k] for k in sorted(best)]


def disagree(chain, mint, basis, a, b, asof):
    pools = [r[0] for r in con.execute("SELECT DISTINCT pool_address FROM bt_market_bars WHERE chain=? AND mint=? AND timeframe_s=3600 AND start>=? AND start<? "
                                        "AND available_at<=?", (chain, mint, a, b, asof))]
    base = {r["start"]: r for r in first_versions(chain, mint, basis, a, b, asof)}
    for p in pools:
        if p == basis:
            continue
        other = {r["start"]: r for r in first_versions(chain, mint, p, a, b, asof)}
        common = [s for s in other if s in base]
        vo, vb = sum(other[s]["v"] or 0 for s in common), sum(base[s]["v"] or 0 for s in common)
        if not common or vb <= 0 or vo < 0.05 * vb:
            continue
        if any(other[s]["c"] > 0 and base[s]["c"] > 0 and abs(math.log(other[s]["c"] / base[s]["c"])) > math.log(1.3) for s in common):
            return True
    return False


out = {}
for name, (asof_raw, status) in CASES.items():
    asof = float(int(asof_raw // 3600) * 3600)                 # assess floors the as-of to the hour
    S._COHORT_CACHE.clear()
    pkg = S.empirical_cohort(con, status, asof=asof)
    known = con.execute("SELECT chain, mint, MIN(available_at) t FROM bt_universe_members WHERE universe_id='lab_state_history' AND basis='THESIS' "
                        "AND status_at_entry=? AND available_at<=? GROUP BY chain, mint", (status, asof)).fetchall()
    rets, comp, worst, pending, guard = [], [], [], 0, 0
    for r in known:
        t, end = r["t"], r["t"] + 86400
        if asof < end + O.LAG_S:
            pending += 1
            continue
        if not con.execute("SELECT 1 FROM bt_market_bars WHERE chain=? AND mint=? AND available_at<=? LIMIT 1", (r["chain"], r["mint"], asof)).fetchone():
            continue
        basis, _ = O._basis(con, {"chain": r["chain"], "mint": r["mint"], "decision_time": t}, latest=asof)
        if not basis:
            continue
        if disagree(r["chain"], r["mint"], basis["pool_address"], t, end, asof):
            guard += 1
            continue
        bs = first_versions(r["chain"], r["mint"], basis["pool_address"], t, end, asof)
        if not bs:
            continue
        ret = bs[-1]["c"] / bs[0]["o"] - 1
        rets.append(ret)
        worst.append(min(b["l"] for b in bs) / bs[0]["o"] - 1)
        if bs[-1]["end"] >= end - 3600:
            comp.append(ret)
    measurable = len(known) - pending
    flag = bool(measurable) and (measurable - len(rets)) / measurable > 0.2
    ind = {"known": len(known), "n": len(rets), "n_complete": len(comp), "guard_removed": guard, "selection_bias_risk": flag,
           "p10_p50": [q(rets, .1), statistics.median(rets)] if rets else None, "worst_p10_p50": [q(worst, .1), statistics.median(worst)] if worst else None}
    pk = {"known": pkg["known_tokens"], "n": pkg["n"], "n_complete": pkg["n_complete"], "tier": pkg["tier"], "selection_bias_risk": pkg["selection_bias_risk"],
          "unmeasured_share": pkg["unmeasured_share"], "p10_p50": (pkg.get("ret_p10_p50_p90") or [None, None])[:2],
          "complete_only_p10_p50": (pkg.get("ret_complete_only_p10_p50_p90") or [None, None])[:2], "worst_p10_p50": pkg.get("worst_drop_p10_p50"),
          "missing_reasons": pkg["missing_reasons"]}
    match = (pk["known"] == ind["known"] and pk["n"] == ind["n"] and pk["n_complete"] == ind["n_complete"] and pk["selection_bias_risk"] == ind["selection_bias_risk"]
             and (pkg["tier"] != "HISTORICAL_COHORT" or (abs(pk["p10_p50"][0] - ind["p10_p50"][0]) < 1e-12 and abs(pk["p10_p50"][1] - ind["p10_p50"][1]) < 1e-12)))
    out[name] = {"asof": iso(asof), "package": pk, "independent": ind, "match": match}
print(json.dumps(out, indent=1, default=str))
