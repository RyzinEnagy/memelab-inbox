"""Writes the two scored-wallet fixture ledgers next to this file. Invented data: no chain, provider or person is behind them.
Run: python make_scored.py   (output is committed; the test file checks the committed files against hand arithmetic)

outlier: 24 positions of 1 SOL each at SOL = 100 USD. Position 1 returns 21 SOL, positions 2-12 return 1.2 SOL, positions 13-24 return 0.7 SOL.
clean:   50 positions of 1 SOL each. Positions 1-30 return 1.1 SOL, positions 31-50 return 0.9 SOL. Token prices are supplied at each buy, so equity can be valued.
Fees are declared as exactly zero so the hand arithmetic has no fee terms.
"""
import json
from pathlib import Path

T0, DAY = 1790000000, 86400


def build(name, returns, with_token_marks):
    entries, prices = [], []
    for i, r in enumerate(returns):
        tb, ts, tok = T0 + i * DAY, T0 + i * DAY + 3600, f"TOK{i + 1:02d}"
        entries.append({"id": f"b{i + 1:02d}", "wallet": "WS", "time": tb, "type": "SWAP", "signature": f"sb{i + 1:02d}", "fee": {"amount": "0", "unit": "SOL"},
                        "legs": [{"asset": "NATIVE", "dir": "OUT", "amount": "1"}, {"asset": tok, "dir": "IN", "amount": "1000"}]})
        entries.append({"id": f"s{i + 1:02d}", "wallet": "WS", "time": ts, "type": "SWAP", "signature": f"ss{i + 1:02d}", "fee": {"amount": "0", "unit": "SOL"},
                        "legs": [{"asset": tok, "dir": "OUT", "amount": "1000"}, {"asset": "NATIVE", "dir": "IN", "amount": str(r)}]})
        prices += [{"asset": "NATIVE", "t": tb, "kind": "MID", "usd": "100", "source": "fixture:invented"}, {"asset": "NATIVE", "t": ts, "kind": "MID", "usd": "100", "source": "fixture:invented"}]
        if with_token_marks:
            prices.append({"asset": tok, "t": tb, "kind": "MID", "usd": "0.1", "source": "fixture:invented"})
    n = len(returns)
    return {"schema": "memelab.perf.ledger/1", "label": f"FIXTURE: {name} invented wallet, invented prices", "chain": "solana", "wallets": ["WS"], "as_of": T0 + (n + 2) * DAY,
            "assets": {"NATIVE": {"kind": "NATIVE", "symbol": "SOL"}}, "coverage": {"history": "DECLARED_COMPLETE", "evidence": "fixture: declared complete by the fixture author"},
            "entries": entries, "prices": sorted(prices, key=lambda p: (p["t"], p["asset"]))}


here = Path(__file__).parent
(here / "ledger_scored_outlier.json").write_text(json.dumps(build("outlier", [21] + [1.2] * 11 + [0.7] * 12, False), indent=1))
(here / "ledger_scored_clean.json").write_text(json.dumps(build("clean", [1.1] * 30 + [0.9] * 20, True), indent=1))
