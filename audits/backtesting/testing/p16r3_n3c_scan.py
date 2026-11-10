"""Phase 16 re-run 3: real-corpus size of N3c. For every frozen opportunity in a COPY of the corpus, at 1/6/24/72 h, and
every other pool of the mint, count the shared hours whose closes are more than 30% apart. Lists the windows the pass-3
guard measures although at least two shared hours are apart (apart hours never clock-adjacent), and how many of those
would be refused by a rule that counts consecutive shared observations instead of clock-adjacent hours, or that
refuses when more than a third of the shared hours are apart.
Usage: python3 audits/backtesting/testing/p16r3_n3c_scan.py <copy of bt.sqlite>"""
import json, math, sys, time
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from memelab.backtest import outcomes as O, store  # noqa: E402

db = Path(sys.argv[1]); assert db.resolve() != (ROOT / "data/backtest/bt.sqlite").resolve()
con = store.connect(db)
asof = con.execute("SELECT MAX(available_at) FROM bt_market_bars").fetchone()[0]
iso = lambda t: time.strftime("%Y-%m-%d %H:%M", time.gmtime(t))
TOL = math.log(1.30)
opps = O.opportunities(con)
out = {"opportunities": len(opps), "by_horizon": {}, "windows": []}
for h in O.HORIZONS_S:
    tally = {"measured": 0, "multi_pool_measured": 0, "two_plus_apart_not_refused": 0, "would_refuse_by_shared_observation_run": 0, "would_refuse_by_third_rule": 0}
    for o in opps:
        r = O.outcome_for(con, o, h, asof)
        if r["state"] not in ("OBSERVED", "COMPLETE", "PARTIAL") and not (r.get("realized") and r["realized"].get("exit_close") is not None):
            continue
        tally["measured"] += 1
        t, end = o["decision_time"], o["decision_time"] + h
        basis = r["realized"]["pool"]
        rows = con.execute("SELECT pool_address, start, c FROM bt_market_bars WHERE chain=? AND mint=? AND timeframe_s=3600 AND start>=? AND start<? "
                           "AND available_at<=? ORDER BY start, available_at, id", (o["chain"], o["mint"], t, end, asof)).fetchall()
        by = defaultdict(dict)
        for row in rows:
            by[row["pool_address"]].setdefault(row["start"], row["c"])
        if len(by) < 2:
            continue
        tally["multi_pool_measured"] += 1
        base = by.get(basis) or {}
        for pool, series in by.items():
            if pool == basis:
                continue
            shared = sorted(x for x in series if x in base)
            flags = [bool(base[s] > 0 and series[s] > 0 and abs(math.log(series[s] / base[s])) > TOL) for s in shared]
            apart = sum(flags)
            if apart < 2:
                continue
            obs_run = best = 0
            for f in flags:
                obs_run = obs_run + 1 if f else 0
                best = max(best, obs_run)
            third = apart / len(shared) > 1 / 3
            tally["two_plus_apart_not_refused"] += 1
            tally["would_refuse_by_shared_observation_run"] += best >= 2
            tally["would_refuse_by_third_rule"] += third
            out["windows"].append({"horizon_h": h // 3600, "mint": o["mint"], "status": o["status"], "decision": iso(t), "other_pool": pool,
                                   "shared_hours": len(shared), "apart_hours": apart, "best_run_shared_observations": best, "third_rule": third,
                                   "measured_ret": (r["realized"]["exit_close"] / r["realized"]["entry_open"] - 1) if r["realized"].get("entry_open") else None})
    out["by_horizon"][f"{h // 3600}h"] = tally
print(json.dumps(out, indent=1, default=str))
