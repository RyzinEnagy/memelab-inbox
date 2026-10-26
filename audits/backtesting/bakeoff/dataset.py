"""Canonical bake-off dataset (synthetic, deterministic). Writes dataset.json and prints its sha256.

Synthetic fixture: proves engine behavior only, never fidelity to a live market.
"""
import hashlib, json, sys

T0 = 1_800_000_000  # aligned to the hour (1_800_000_000 / 3600 = 500_000)
H = 3600


def bars():
    rows = []
    for i in range(48):
        t = T0 + i * H
        if i < 20:
            trend = 0.002 * i
            o = 1.00 + trend + (0.01 if i % 2 else -0.01)
            c = 1.00 + trend + (-0.005 if i % 2 else 0.005)
            hi, lo = max(o, c) + 0.005, min(o, c) - 0.005
        elif i == 20:
            o, hi, lo, c = 1.01, 1.12, 1.00, 1.10          # breakout bar: closes above the prior 20-bar high
        elif 21 <= i <= 34:
            o = 1.11 + 0.01 * (i - 21)
            c = o + 0.008
            hi, lo = c + 0.01, o - 0.01
        elif i == 35:
            o, hi, lo, c = 0.95, 0.96, 0.90, 0.93          # gap down through any stop between 0.96 and 1.24
        else:
            o = 0.93 - 0.002 * (i - 36)
            c = o - 0.001
            hi, lo = o + 0.004, c - 0.004
        rows.append({"t": t, "o": round(o, 6), "h": round(hi, 6), "l": round(lo, 6), "c": round(c, 6), "v": 10_000.0 + 100 * i})
    return rows


def main():
    d = {
        "_fixture": "SYNTHETIC_BAKEOFF_V1 - not market data",
        "mint": "BAKEOFFsynth1111111111111111111111111111111",
        "bar_seconds": H,
        "bars": bars(),
        # CPMM pool: quote reserve held constant in USD at each bar open; base reserve = quote / open price
        "pool": {"type": "CPMM", "quote_reserve_usd": 60_000.0, "swap_fee": 0.0025, "transfer_fee_bps": 0, "network_fee_usd": 0.01},
        "event": {"id": "EV1", "published_at": T0 + 5 * H + 1800, "first_seen_at": T0 + 7 * H + 600, "claim": "listing announcement (synthetic)"},
        "strategy_breakout": {"lookback": 20, "stop_frac": 0.10, "max_hold_bars": 20},
        "strategy_event": {"hold_bars": 6},
        "sizes_usd": [1000.0, 50000.0],
        "latency_seconds": 0,
    }
    s = json.dumps(d, sort_keys=True, indent=1)
    open("dataset.json", "w").write(s)
    print(hashlib.sha256(s.encode()).hexdigest())


if __name__ == "__main__":
    sys.exit(main())
