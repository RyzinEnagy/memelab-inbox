"""Phase 16 re-run 3 (pass-3 guard fields): every frozen opportunity in a COPY of the corpus, at 1/6/24/72 h, with the pool-disagreement
guard (outcomes.pool_disagreement). For each window the guard removes, it also measures what the basis pool alone
showed, so a removed crash is visible. Usage: python3 audits/backtesting/testing/p16r2_guard_scan.py <copy of bt.sqlite>"""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from memelab.backtest import outcomes as O, store  # noqa: E402

db = Path(sys.argv[1]); assert db.resolve() != (ROOT / "data/backtest/bt.sqlite").resolve()
con = store.connect(db)
asof = con.execute("SELECT MAX(available_at) FROM bt_market_bars").fetchone()[0]
iso = lambda t: time.strftime("%Y-%m-%d %H:%M", time.gmtime(t))
opps = O.opportunities(con)
out = {"opportunities": len(opps), "by_horizon": {}, "removed": []}
for h in O.HORIZONS_S:
    states = {}
    for o in opps:
        r = O.outcome_for(con, o, h, asof)
        states[r["state"]] = states.get(r["state"], 0) + 1
        if str(r.get("missing_reason") or "").startswith("POOL_DISAGREEMENT"):
            basis = r["realized"]["pool"]
            bars = [b for b in store.bars_asof(con, chain=o["chain"], mint=o["mint"], pool_address=basis, tf=3600, cutoff=asof)
                    if o["decision_time"] <= b["start"] < o["decision_time"] + h]
            d = r["realized"]["disagreement"]
            out["removed"].append({"horizon_h": h // 3600, "mint": o["mint"], "source": o["source"], "status": o["status"], "decision": iso(o["decision_time"]),
                                   "basis_pool_ret": (bars[-1]["c"] / bars[0]["o"] - 1) if bars else None,
                                   "basis_pool_min_drop": (min(b["l"] for b in bars) / bars[0]["o"] - 1) if bars else None,
                                   "gap_pct": round(2.718281828 ** d["log_gap"] - 1, 3), "consecutive_hours_apart": d.get("consecutive_hours_apart")})
    out["by_horizon"][f"{h // 3600}h"] = states
print(json.dumps(out, indent=1, default=str))
