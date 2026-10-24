"""Phase 06: write tests/fixtures/predictive/labels_hand_trace.json, the hand-checked label cases.

Candles and expected labels are written here by hand (worked in labels/HAND_CHECKED_TRACE.md); the label code is not called.
Times: decision 2026-10-08T00:20:34Z (unaligned), t_entry 00:25:34Z, reference candle 00:10Z (end 00:15Z, served by 00:20Z),
the candle 00:25Z holds t_entry and is never in the path, first path candle 00:30Z. Rows are [start, open, high, low, close, volume].
"""
import json
from pathlib import Path

DAY = 1791417600            # 2026-10-08T00:00:00Z
DT = DAY + 1234             # decision 00:20:34Z
B = 1791592200              # request boundary: t_entry + 48 h on the 5-minute grid (2026-10-10T00:30:00Z)
RET = DT + 30 * 86400       # read long after every maturity


def t(h, m=0):
    return DAY + h * 3600 + m * 60


def c(start, o, h, l, cl, v=2000.0):
    return [start, o, h, l, cl, v]


def pre(p):
    """A candle the evening before (it brackets every later span) and the reference candle at 00:10Z closing at p."""
    return [c(t(-1), p, p, p, p), c(t(0, 10), p, p, p, p)]


def later(p, from_h, to_h=48, step=2):
    """Trading every two hours from from_h to to_h (keeps the T2 halt span traded)."""
    return [c(t(h, 30), p, p * 1.01, p * 0.99, p) for h in range(from_h, to_h, step)]


cases = []
# 1 false breakout: +20% high above the range at 01:00, then a -17% low at 02:00; never -50%, trading continues
cases.append({"name": "false_breakout", "candles":
    pre(1.0) + [c(t(0, 25), 1.0, 1.4, 1.0, 1.0),                       # holds t_entry: its +40% high must not count (P06)
                c(t(0, 30), 1.0, 1.06, 1.0, 1.05), c(t(1), 1.05, 1.20, 1.05, 1.15), c(t(1, 30), 1.15, 1.15, 0.98, 1.0),
                c(t(2), 1.0, 1.0, 0.83, 0.84)] + later(0.8, 4),
    "expected": {"eligibility": "ELIGIBLE", "p0": 1.0,
                 "t1_24h": ["LABELED", "INVALIDATION_FIRST", 0], "t1b_6h": ["LABELED", "INVALIDATION_FIRST", 0],
                 "t2_24h": ["LABELED", "NO_SEVERE_EVENT", 0],
                 "first_touch_start": {"price_path_target_before_invalidation_24h": t(2),
                                       "price_path_target_before_invalidation_6h": t(2)}}})
# 2 true confirmation with a delayed catalyst: flat for ten hours, +30% high at 10:30 (after the 6 h horizon)
cases.append({"name": "delayed_confirmation", "candles":
    pre(2.0) + [c(t(h, 30), 2.0, 2.1, 1.95, 2.05) for h in range(0, 10)] + [c(t(10, 30), 2.05, 2.6, 2.05, 2.5)] + later(2.5, 12),
    "expected": {"eligibility": "ELIGIBLE", "p0": 2.0,
                 "t1_24h": ["LABELED", "TARGET_FIRST", 1], "t1b_6h": ["LABELED", "NEITHER", 0],
                 "t2_24h": ["LABELED", "NO_SEVERE_EVENT", 0],
                 "first_touch_start": {"price_path_target_before_invalidation_24h": t(10, 30)}}})
# 3 rug with a crash: -90% low at 01:00, two dust trades, then nothing to the boundary
cases.append({"name": "rug_crash_then_halt", "candles":
    pre(0.5) + [c(t(0, 30), 0.5, 0.5, 0.5, 0.5), c(t(1), 0.5, 0.5, 0.05, 0.06), c(t(1, 30), 0.06, 0.06, 0.04, 0.04, 30.0),
                c(t(2), 0.04, 0.04, 0.04, 0.04, 20.0)],
    "expected": {"eligibility": "ELIGIBLE", "p0": 0.5,
                 "t1_24h": ["LABELED", "INVALIDATION_FIRST", 0], "t1b_6h": ["LABELED", "INVALIDATION_FIRST", 0],
                 "t2_24h": ["LABELED", "DRAWDOWN_50", 1],
                 "first_touch_start": {"price_path_target_before_invalidation_24h": t(1),
                                       "price_path_severe_drawdown_or_halt_24h": t(1)}}})
# 4 rug by pulled liquidity: flat to 03:00, then no trade on the reference pool or on the one other listed pool
cases.append({"name": "rug_halt_without_drawdown", "candles":
    pre(1.0) + [c(t(0, 30), 1.0, 1.02, 0.98, 1.0), c(t(1, 30), 1.0, 1.02, 0.98, 1.0), c(t(3), 1.0, 1.0, 0.97, 0.97)],
    "other_pools": [{"pool": "8BRDx1ky8xuRBYq1kmVJ4TrSNaDybSiLU2mxmLVB4WaW", "boundary": B,
                     "candles": [c(t(-2), 1.0, 1.0, 1.0, 1.0, 50.0), c(t(2), 1.0, 1.0, 1.0, 1.0, 50.0)]}],
    "expected": {"eligibility": "ELIGIBLE", "p0": 1.0,
                 "t1_24h": ["LABELED", "NEITHER", 0], "t1b_6h": ["LABELED", "NEITHER", 0],
                 "t2_24h": ["LABELED", "TRADING_HALT", 1]}})
# 5 ambiguous OHLC bar: the first path candle has high +30% and low -20%; order inside the candle unknown
cases.append({"name": "ambiguous_bar", "candles":
    pre(1.0) + [c(t(0, 30), 1.0, 1.30, 0.80, 1.0)] + later(1.0, 2),
    "expected": {"eligibility": "ELIGIBLE", "p0": 1.0,
                 "t1_24h": ["LABELED", "AMBIGUOUS_BAR", 0], "t1b_6h": ["LABELED", "AMBIGUOUS_BAR", 0],
                 "t2_24h": ["LABELED", "NO_SEVERE_EVENT", 0],
                 "first_touch_start": {"price_path_target_before_invalidation_24h": t(0, 30),
                                       "price_path_target_before_invalidation_6h": t(0, 30)}}})
# 6 vendor serves nothing although the thesis saw $200,000 of 24 h volume: a gap, censored, never a halt or no-trade label
cases.append({"name": "empty_page_is_a_gap", "candles": [],
    "expected": {"eligibility": "VENDOR_OR_ROUTE_GAP", "p0": None,
                 "t1_24h": ["VENDOR_OR_ROUTE_GAP", None, None], "t1b_6h": ["VENDOR_OR_ROUTE_GAP", None, None],
                 "t2_24h": ["VENDOR_OR_ROUTE_GAP", None, None]}})
for x in cases:
    x.update(decision_time=DT, boundary=B, retrieved_at=RET, snapshot_vol_24h=200000.0)
    x["candles"] = sorted(x["candles"], reverse=True)          # vendor order, newest first
out = Path(__file__).resolve().parents[4] / "tests/fixtures/predictive/labels_hand_trace.json"
out.write_text(json.dumps({"note": "hand-checked Phase 06 label cases; expected values worked by hand in "
                                   "audits/predictive-intelligence/phase_06/labels/HAND_CHECKED_TRACE.md", "cases": cases}, indent=1) + "\n")
print(out, len(cases))
