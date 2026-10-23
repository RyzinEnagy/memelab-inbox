"""Phase 09 event study on the lab's own launch-monitor records (real, contemporaneous) with a placebo control.

For each launch event with corpus bars: the pool is the one the lab recorded at discovery (known then); entry is the
open of the first bar that starts at or after the event became available to the lab; outcomes at +6h, +24h and +72h
(close of the last bar that ended by then), plus the worst low in 72h. Placebo: the same tokens with the event time
moved by a seeded random shift of 12 to 72 hours later (never before the token existed). Research only.
    python audits/backtesting/catalyst/p09_event_study.py > audits/backtesting/catalyst/p09_event_study.json
"""
from __future__ import annotations

import json
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from memelab.backtest import store  # noqa: E402
from memelab.backtest.sources import lab_events  # noqa: E402

H = 3600


def bars_of(con, mint, pool):
    return [dict(r) for r in con.execute("SELECT start, end, o, h, l, c, available_at FROM bt_market_bars WHERE mint=? AND pool_address=? AND timeframe_s=3600 "
                                         "ORDER BY start, available_at", (mint, pool))]


def outcome(bars, t):
    nxt = [b for b in bars if b["start"] >= t]
    if not nxt:
        return None
    e = nxt[0]
    entry = e["o"]
    res = {"entry_bar": e["start"], "entry": entry, "wait_h": round((e["start"] - t) / H, 2)}
    for hz in (6, 24, 72):
        done = [b for b in bars if b["end"] <= e["start"] + hz * H and b["start"] >= e["start"]]
        res[f"ret_{hz}h"] = (done[-1]["c"] / entry - 1) if done else None
    w = [b for b in bars if e["start"] <= b["start"] < e["start"] + 72 * H]
    res["worst_72h"] = min(b["l"] for b in w) / entry - 1 if w else None
    res["last_bar_age_h"] = round((time.time() - bars[-1]["end"]) / H, 1)
    return res


def main():
    con = store.connect()
    recs = lab_events.launch_catalysts(Path(__file__).resolve().parents[3])
    rows, placebo = [], []
    rng = random.Random(20261023)
    for r in recs:
        pool = r.get("pool_at_discovery")
        if not pool:
            continue
        bars = bars_of(con, r["mint"], pool)
        if not bars:
            continue
        o = outcome(bars, r["available_at"])
        if o is None:
            continue
        failed = o["worst_72h"] is not None and o["worst_72h"] <= -0.5
        rows.append({"symbol": r["symbol"], "mint": r["mint"], "kind": r["claim_type"], "pool": pool, "available_at": r["available_at"],
                     "event_time_claim": r["event_time"], "committed_by": r["committed_by"], "lab_status_then": r["lab_status"],
                     "outcome": o, "failed_72h": failed})
        t2 = r["available_at"] + rng.uniform(12, 72) * H
        o2 = outcome(bars, t2)
        if o2:
            placebo.append({"mint": r["mint"], "t": t2, "outcome": o2})

    def summ(xs, k):
        v = [x["outcome"][k] for x in xs if x["outcome"][k] is not None]
        return {"n": len(v), "median": statistics.median(v) if v else None, "mean": statistics.mean(v) if v else None,
                "share_positive": sum(1 for a in v if a > 0) / len(v) if v else None}
    return {"events": len(rows), "failed_72h": sum(1 for x in rows if x["failed_72h"]),
            "event": {k: summ(rows, k) for k in ("ret_6h", "ret_24h", "ret_72h", "worst_72h")},
            "placebo": {k: summ(placebo, k) for k in ("ret_6h", "ret_24h", "ret_72h", "worst_72h")},
            "rows": rows, "note": "small sample (one week of lab launch records); descriptive only, not a validated edge"}


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
