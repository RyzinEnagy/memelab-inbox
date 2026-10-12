"""Builds tests/fixtures/social/alpha/alpha_main.json. Everything here is invented: sources, tokens, posts and prices.

Run: python tests/fixtures/social/alpha/make_alpha.py   (rewrites alpha_main.json; the test suite checks the file matches this script)
Hourly candles from T0 for 57 hours. Price paths are piecewise linear through knots (hour, price); volume and liquidity are constants unless given.
"""
import json
from pathlib import Path

T0 = 1789999200          # hour-aligned
H = 3600
HOURS = 57
SRC = "fixture:invented-candles"


def path(knots, hours=HOURS):
    ks = sorted(knots)
    out = []
    for k in range(hours + 1):
        for (h0, p0), (h1, p1) in zip(ks, ks[1:]):
            if h0 <= k <= h1:
                out.append(p0 + (p1 - p0) * (k - h0) / (h1 - h0))
                break
        else:
            out.append(ks[-1][1] if k > ks[-1][0] else ks[0][1])
    return out


def series(contract, knots, liq=100000.0, vol=2000.0, delisted_hour=None, chain="solana", hours=HOURS):
    px = path(knots, hours)
    last = hours if delisted_hour is None else delisted_hour
    rows = []
    for k in range(last):
        o, c = px[k], px[k + 1]
        rows.append({"t": T0 + k * H, "o": round(o, 6), "h": round(max(o, c) * 1.01, 6), "l": round(min(o, c) * 0.99, 6), "c": round(c, 6), "v": vol, "liq": liq})
    s = {"chain": chain, "contract": contract, "as_of_kind": "HISTORICAL_CANDLE", "candle_seconds": H, "source": SRC, "rows": rows}
    if delisted_hour is not None:
        s["delisted_at"] = T0 + delisted_hour * H
    return s


def flat_then(pub_h, mult24, pre=1.0):
    """Price 1.0 until the post, then straight to mult24 at +24h and flat after."""
    return [(0, pre), (pub_h, pre), (pub_h + 24, mult24), (HOURS, mult24)]


def call(cid, sid, contract, pub_h, direction="LONG", obs_lag=120, offset=0, **kw):
    pub = T0 + pub_h * H + offset
    c = {"call_id": cid, "source_id": sid, "item_key": f"fixture:x:{cid}", "token": {"chain": "solana", "contract": contract}, "direction": direction,
         "published_at": pub, "first_observed_at": pub + obs_lag, "original": True, "author_position": "not_disclosed", "uncertainty": "low"}
    c.update(kw)
    return c


def build():
    calls, ser = [], []
    # source A: twelve ordinary calls, then the awkward ones
    mults = [1.8, 1.5, 1.3, 1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 1.4, 0.6, 1.25]
    for i, m in enumerate(mults):
        tok, ph = f"TA{i + 1:02d}", 12 + i % 6
        calls.append(call(f"a{i + 1:02d}", "src_a", tok, ph))
        ser.append(series(tok, flat_then(ph, m)))
    calls.append(call("a13", "src_a", "TA01", 14, original=False))                               # a repost: not independent
    calls.append(call("a14", "src_a", "TA01", 12, offset=7200))                                  # same source, same token, two hours later
    calls.append(call("a15", "src_a", "TA02", 13, direction="NEUTRAL"))                          # commentary with no direction
    calls.append(call("a16", "src_a", "TA13", 15)); ser.append(series("TA13", flat_then(15, 1.6)))   # bullish...
    calls.append(call("a17", "src_a", "TA13", 15, direction="SHORT", offset=3600))               # ...then bearish within a day
    calls.append(call("a18", "src_a", "TA14", 15, obs_lag=5 * H)); ser.append(series("TA14", flat_then(15, 3.0)))  # captured 5 h late
    calls.append(call("a19", "src_a", "TA14", 16, conditional=True))
    calls.append(call("a20", "src_a", "TA15", 18)); ser.append(series("TA15", [(0, 1.0), (12, 1.0), (18, 3.0), (42, 1.5), (HOURS, 1.5)]))  # late promotion after a pump
    calls.append(call("a21", "src_a", "TA16", 14)); ser.append(series("TA16", flat_then(14, 1.2), delisted_hour=30))  # delisted before the 24 h exit
    calls.append(call("a22", "src_a", "TA17", 14)); ser.append(series("TA17", flat_then(14, 2.0), liq=5000.0))          # pool too thin for the size
    calls.append(call("a23", "src_a", "TA18", 14))                                               # no price history supplied
    # source B: three calls only
    for i, m in enumerate([2.0, 1.9, 1.7]):
        tok = f"TB{i + 1:02d}"
        calls.append(call(f"b{i + 1:02d}", "src_b", tok, 13 + i)); ser.append(series(tok, flat_then(13 + i, m)))
    # source C: posts found after the fact, only the winners
    for i, m in enumerate([4.0, 3.5, 3.0, 2.5, 2.2, 2.0]):
        tok = f"TC{i + 1:02d}"
        calls.append(call(f"c{i + 1:02d}", "src_c", tok, 13, obs_lag=6 * H)); ser.append(series(tok, flat_then(13, m)))
    # matched comparison pool, all flat-ish, one of them rugged
    for i, m in enumerate([0.8, 0.9, 0.95, 1.0, 1.0, 1.05, 1.1, 1.2]):
        ser.append(series(f"BK{i + 1:02d}", [(0, 1.0), (HOURS, 1.0)] if False else flat_then(12, m), liq=100000.0 * (1 + 0.05 * i)))
    ser.append(series("BK09", flat_then(12, 0.5), delisted_hour=33))
    return {"schema": "memelab.alpha.input/1", "label": "FIXTURE: invented sources, tokens, posts and prices", "is_fixture": True, "as_of": T0 + HOURS * H,
            "sources": {"src_a": {"label": "invented source A", "universe_count": 23, "universe_basis": "fixture: every post the invented collector saw",
                                  "context": {"followers": 120000}},
                        "src_b": {"label": "invented source B", "universe_count": 3, "universe_basis": "fixture", "context": {"followers": 900}},
                        "src_c": {"label": "invented source C (huge following, late-found winners)", "universe_count": 40, "universe_basis": "fixture: 40 posts seen, 6 supplied",
                                  "context": {"followers": 5000000}}},
            "calls": calls, "series": ser,
            "author_trades": [{"source_id": "src_a", "chain": "solana", "contract": "TA01", "t": T0 + 12 * H - 1800, "side": "BUY", "usd": 800.0,
                               "assertion": "CHAIN_EVIDENCE", "source": "fixture:wallet-event-1"}]}


if __name__ == "__main__":
    out = Path(__file__).with_name("alpha_main.json")
    out.write_text(json.dumps(build(), sort_keys=True, separators=(",", ":")) + "\n")
    print("wrote", out, out.stat().st_size, "bytes")
