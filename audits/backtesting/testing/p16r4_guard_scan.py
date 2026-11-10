"""Phase 16 re-run 4: the pass-4 pool-disagreement guard on every frozen opportunity in a COPY of the corpus, at
1/6/24/72 h. Lists the windows it removes, and counts the measured multi-pool windows that show each shape the pass-4
attacks use, recomputed here from raw bars (first version of each bar available at the as-of):
- N3e: two or more consecutive shared hours apart (median of the other pools against the basis, more than 30%) that
  the share rule lets through;
- exit: the basis pool's last shared hour apart (the limitation: the window's return then rests on that close);
- N3d: other pools traded in the window but never in an hour the basis traded; flagged when the basis close is more
  than 30% from the nearest other-pool close (within 1 hour) in two or more hours;
- N3f: one other pool alone apart in at least 2 and a third of its shared hours while the median hides it;
- pass3_rule: windows the pass-3 rule (one pool, two clock-adjacent shared hours apart) would have refused.
Usage: python3 audits/backtesting/testing/p16r4_guard_scan.py <copy of bt.sqlite>"""
import json, math, statistics, sys, time
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from memelab.backtest import outcomes as O, store  # noqa: E402

db = Path(sys.argv[1]); assert db.resolve() != (ROOT / "data/backtest/bt.sqlite").resolve()
con = store.connect(db)
asof = con.execute("SELECT MAX(available_at) FROM bt_market_bars").fetchone()[0]
iso = lambda t: time.strftime("%Y-%m-%d %H:%M", time.gmtime(t))
TOL = math.log(1.3)
apart_ = lambda a, b: a > 0 and b > 0 and abs(math.log(a / b)) > TOL
opps = O.opportunities(con)
out = {"opportunities": len(opps), "asof": iso(asof), "by_horizon": {}, "removed": [], "examples": []}
for h in O.HORIZONS_S:
    tally = defaultdict(int)
    for o in opps:
        r = O.outcome_for(con, o, h, asof)
        tally["state_" + r["state"]] += 1
        rz = r.get("realized") or {}
        if str(r.get("missing_reason") or "").startswith("POOL_DISAGREEMENT"):
            d = rz["disagreement"]
            out["removed"].append({"horizon_h": h // 3600, "mint": o["mint"], "status": o["status"], "decision": iso(o["decision_time"]),
                                   "hours_apart": d.get("hours_apart"), "shared_hours": d.get("shared_hours"), "gap_pct": round(math.exp(d["log_gap"]) - 1, 3)})
            continue
        if rz.get("ret_close") is None:
            continue
        tally["measured"] += 1
        t, end, basis = o["decision_time"], o["decision_time"] + h, rz["pool"]
        by = defaultdict(dict)
        for row in con.execute("SELECT pool_address p, start, c FROM bt_market_bars WHERE chain=? AND mint=? AND timeframe_s=3600 AND start>=? AND start<? "
                               "AND available_at<=? ORDER BY start, available_at, id", (o["chain"], o["mint"], t, end, asof)):
            by[row["p"]].setdefault(row["start"], row["c"])
        others = {p: s for p, s in by.items() if p != basis}
        if not others:
            continue
        tally["multi_pool_measured"] += 1
        base = by.get(basis, {})
        med = defaultdict(list)
        for s in others.values():
            for st, c in s.items():
                if c and c > 0:
                    med[st].append(c)
        shared = sorted(st for st in base if st in med and base[st] > 0)
        flags = [apart_(statistics.median(med[st]), base[st]) for st in shared]
        run = best = 0
        for f in flags:
            run = run + 1 if f else 0
            best = max(best, run)
        shapes = []
        if best >= 2:
            shapes.append("N3e")
        if shared and flags[-1] and shared[-1] == max(base):
            shapes.append("exit")
        if not shared:
            near = 0
            for st, bc in base.items():
                cand = [c for s in others.values() for st2, c in s.items() if abs(st2 - st) <= 3600 and c > 0]
                if cand and bc > 0 and apart_(statistics.median(cand), bc):
                    near += 1
            if near >= 2:
                shapes.append("N3d")
        for p, s in others.items():
            sh = [st for st in s if st in base and base[st] > 0 and s[st] and s[st] > 0]
            ap = [st for st in sh if apart_(s[st], base[st])]
            if len(ap) >= 2 and len(ap) * 3 >= len(sh):
                shapes.append("N3f")
                break
        for p, s in others.items():
            sh = sorted(st for st in s if st in base)
            ap = {st for st in sh if apart_(s[st] or 0, base[st] or 0)}
            if any(st + 3600 in ap for st in ap):
                shapes.append("pass3_rule")
                break
        for sh_ in shapes:
            tally[sh_] += 1
        if shapes:
            out["examples"].append({"horizon_h": h // 3600, "mint": o["mint"], "status": o["status"], "decision": iso(t), "shapes": shapes,
                                    "shared_hours": len(shared), "hours_apart": sum(flags), "measured_ret": round(rz["ret_close"], 4)})
    out["by_horizon"][f"{h // 3600}h"] = dict(tally)
print(json.dumps(out, indent=1, default=str))
