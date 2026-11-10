"""Phase 00 negative review: wrong-but-plausible claims about the current lab, each checked against the code.

Run: python audits/backtesting/testing/p00_counterexamples.py
Exit 0 when every counterexample is reproduced (that is, the finding is real), 1 otherwise.
Nothing here changes the lab; it only calls existing pure functions on invented bundles.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from memelab.normalize import build_bundle, empty_bundle  # noqa: E402
from memelab.modules import m06_executable_depth as m06, m13_price_structure as m13  # noqa: E402
from memelab.modules import _common  # noqa: E402

MINT = "FAKE1111111111111111111111111111111111111pump"
results = []


def check(name, cond, detail):
    results.append((name, bool(cond), detail))
    print(("REPRODUCED " if cond else "NOT REPRODUCED ") + name + " :: " + detail)


# C1. Claim: "round-trip friction includes the Token-2022 transfer fee reported by RugCheck."
# normalize stores RugCheck's dict under authorities.transfer_fee; m06 reads authorities.transfer_fee_bps.
bodies = {f"rug:{MINT}": {"mint": MINT, "token": {"supply": "1000000000", "decimals": 6, "mintAuthority": None, "freezeAuthority": None},
                         "tokenProgram": "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb", "transferFee": {"pct": 5.0, "maxAmount": 0, "authority": "x"}}}
b = build_bundle(MINT, bodies, observed_at=1_800_000_000.0, sol_price=150.0)
b["quotes"] = {"BUY": {1000.0: {"in": 6_666_666_667, "out": 1_000_000_000, "impact": 0.01, "route": [["p", "Raydium", 100, "SOL", "TOK", 1, 1]], "status": "OK"}},
               "SELL": {1000.0: {"in": 1_000_000_000, "out": 6_400_000_000, "impact": 0.02, "route": [["p", "Raydium", 100, "TOK", "SOL", 1, 1]], "status": "OK"}}}
b["market"]["sol_price"] = 150.0
b["identity"]["decimals"] = 6
out = m06.analyze(b)
fric_fact = next((f for f in out["facts"] if f.startswith("round-trip friction")), "")
check("C1 transfer fee silently dropped from m06 friction",
      "transfer fee" not in fric_fact and (b.get("authorities") or {}).get("transfer_fee", {}).get("pct") == 5.0
      and (b.get("authorities") or {}).get("transfer_fee_bps") is None,
      f"bundle authorities.transfer_fee={b['authorities'].get('transfer_fee')}, transfer_fee_bps={b['authorities'].get('transfer_fee_bps')}, m06 says: {fric_fact!r}")

# C2. Claim: "price structure only uses closed candles, so a signal at time t cannot see the unfinished bar."
# Build hourly candles where the newest bar (start = observed_at - 10 min) is still forming and spikes.
t_obs = 1_800_000_000
rows = []
for i in range(60, 0, -1):
    start = t_obs - 600 - i * 3600  # closed bars; the last one ends exactly at t_obs - 600
    p = 1.0 + 0.001 * (60 - i)
    rows.append([start, p, p * 1.01, p * 0.99, p, 1000.0])
rows.append([t_obs - 600, 1.06, 9.99, 1.05, 9.5, 50_000.0])  # unfinished bar: a wick that a closed-bar rule must not see yet
eb = empty_bundle(MINT, float(t_obs))
eb["ohlcv"] = {"hour1": list(reversed(rows))}  # GeckoTerminal order: newest first
eb["market"]["price_usd"] = 9.5
st = m13.analyze(eb)
c = _common.normalize_candles(eb["ohlcv"]["hour1"])
last_start = int(c[-1][0]) if len(c) else None
check("C2 unfinished candle used by m13 (no observed_at / bar-close guard)",
      last_start == t_obs - 600 and (st.get("ath") or 0) >= 9.99 - 1e-9,
      f"last candle start={last_start} (obs-600s, bar not closed until obs+3000s); m13 ath={st.get('ath')}")

# C3. Claim: "the observation clock of a merged result is never earlier than the data inside it."
# Evidence lives in data/inbox/deep01a.result.json: result _at precedes a contained trade timestamp.
import json  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
p = Path(__file__).resolve().parents[3] / "data" / "inbox" / "deep01a.result.json"
if p.exists():
    d = json.loads(p.read_text())
    at = d.get("_at")
    at_s = datetime.fromisoformat(at.replace("Z", "+00:00")).timestamp() if isinstance(at, str) else float(at) / (1000 if float(at) > 1e12 else 1)
    later = []
    for k, v in (d.get("bodies") or d).items():
        if isinstance(v, dict) and "body" in v:
            v = v["body"]
        if isinstance(v, dict) and "trades" in v:
            v = v["trades"]
        if isinstance(k, str) and k.startswith("gt_trades:") and isinstance(v, list):
            for row in v:
                try:
                    ts = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00")).timestamp()
                except Exception:
                    continue
                if ts > at_s:
                    later.append(row[0])
    check("C3 result _at earlier than trades it contains", len(later) > 0,
          f"_at={at}; {len(later)} trade rows stamped after it, e.g. {later[:2]}")
else:
    check("C3 result _at earlier than trades it contains", False, "fixture file missing")

ok = all(r[1] for r in results)
print(f"\n{sum(r[1] for r in results)}/{len(results)} counterexamples reproduced")
sys.exit(0 if ok else 1)
