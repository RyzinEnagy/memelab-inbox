"""Phase 08 chronological case proofs on real bars: every strategy evaluated at every hour a decision could be made,
seeing only bars available at that moment. Prints the first signals and the abstain counts per strategy.
    python audits/backtesting/strategies/p08_cases.py MINT [MINT ...]  (needs data/backtest/bt.sqlite)
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from memelab.backtest import store  # noqa: E402
from memelab.backtest.sources import gecko  # noqa: E402
from memelab.backtest.strategies import registry  # noqa: E402
from memelab.backtest.strategies.base import Abstain, Signal  # noqa: E402
from memelab.backtest.strategies.features import B  # noqa: E402

TA = ("BREAKOUT_CLOSE", "BREAKOUT_RETEST", "RECLAIM", "TREND_HHHL", "ABSORPTION_BREAK", "MOMENTUM")


def case(con, mint: str) -> dict:
    pool = gecko.pool_basis_at(con, "solana", mint, time.time())
    if not pool:
        return {"mint": mint, "error": "no pool basis"}
    rows = store.bars_asof(con, chain="solana", mint=mint, pool_address=pool["pool_address"], tf=3600, cutoff=time.time())
    bars = [B(r["start"], r["end"], r["o"], r["h"], r["l"], r["c"], r["volume_usd"] or 0.0, r["available_at"]) for r in rows]
    out = {"mint": mint, "pool": pool["pool_address"], "bars": len(bars), "strategies": {}}
    for sid in TA:
        s = registry.make(sid)
        sig, ab = [], Counter()
        for i in range(1, len(bars) + 1):
            vis = bars[:i]
            t = vis[-1].avail                                    # decide the moment the bar becomes available
            r = s.evaluate("solana", mint, vis, t)
            if isinstance(r, Signal):
                sig.append({"decision": time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(t)), "close": vis[-1].c, "stop": r.exits.stop_price,
                            "next_open": bars[i].o if i < len(bars) else None, "invalidation": r.invalidation})
            elif isinstance(r, Abstain):
                ab[r.reason] += 1
        out["strategies"][sid] = {"signals": len(sig), "first": sig[:3], "abstain": dict(ab)}
    return out


if __name__ == "__main__":
    con = store.connect()
    print(json.dumps([case(con, m) for m in sys.argv[1:]], indent=1))
