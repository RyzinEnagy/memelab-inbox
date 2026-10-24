"""Phase 08: point-in-time TA strategy library (G05, G18, G19, G31 plus malformed data). Synthetic bars."""
import pytest

from memelab.backtest.strategies import features as F, registry
from memelab.backtest.strategies.base import Abstain, Signal
from memelab.backtest.strategies.features import B
from memelab.backtest.timeguard import LeakageError, closed_bars, Bar

T = 1_800_000_000.0
H = 3600


def bars_from(ohlcv, lag=60.0, t0=T):
    return [B(t0 + i * H, t0 + (i + 1) * H, o, h, l, c, v, t0 + (i + 1) * H + lag) for i, (o, h, l, c, v) in enumerate(ohlcv)]


def flat(n, px=1.0, v=100.0):
    return [(px, px * 1.01, px * 0.99, px, v)] * n


# G18: wick vs confirmed close vs failed retest
def test_g18_wick_is_not_a_breakout_close_is():
    s = registry.make("BREAKOUT_CLOSE", lookback=10, vol_mult=1.5)
    wick = bars_from(flat(10) + [(1.0, 1.30, 0.99, 1.005, 500)])
    assert s.evaluate("solana", "M", wick, wick[-1].avail) is None
    close = bars_from(flat(10) + [(1.0, 1.30, 0.99, 1.20, 500)])
    sig = s.evaluate("solana", "M", close, close[-1].avail)
    assert isinstance(sig, Signal) and sig.features["level"] == pytest.approx(1.01) and sig.exits.stop_price == pytest.approx(1.01 * 0.97)
    low_vol = bars_from(flat(10) + [(1.0, 1.30, 0.99, 1.20, 120)])
    assert s.evaluate("solana", "M", low_vol, low_vol[-1].avail) is None


def test_g18_retest_hold_vs_failed_retest():
    s = registry.make("BREAKOUT_RETEST", lookback=10, within_bars=6, tol=0.02)
    base = flat(10)
    held = bars_from(base + [(1.0, 1.25, 0.99, 1.20, 500), (1.2, 1.21, 1.02, 1.05, 100), (1.04, 1.12, 1.025, 1.10, 100)])
    sig = s.evaluate("solana", "M", held, held[-1].avail)
    assert isinstance(sig, Signal) and sig.strategy_id == "BREAKOUT_RETEST"
    failed = bars_from(base + [(1.0, 1.25, 0.99, 1.20, 500), (1.2, 1.21, 0.95, 0.96, 100), (0.97, 1.12, 0.96, 1.10, 100)])
    assert s.evaluate("solana", "M", failed, failed[-1].avail) is None


def test_g18_pivots_do_not_repaint_truncation_invariance():
    """Signals computed incrementally (only bars available at each decision) equal signals computed by replaying the
    full history with the same cutoffs, and no signal uses a pivot before its confirming bar closed."""
    import math
    px = [1 + 0.2 * math.sin(i / 3.0) + 0.01 * i for i in range(120)]
    rows = [(p, p * 1.03, p * 0.97, p * (1.01 if i % 4 else 0.99), 100 + (i % 7) * 30) for i, p in enumerate(px)]
    allb = bars_from(rows)
    for sid in ("TREND_HHHL", "BREAKOUT_CLOSE", "RECLAIM", "ABSORPTION_BREAK", "MA_CROSS"):
        s = registry.make(sid)
        inc, full = [], []
        for i in range(1, len(allb) + 1):
            d = allb[i - 1].avail
            r = s.evaluate("solana", "M", allb[:i], d)
            inc.append(r.as_dict() if isinstance(r, Signal) else None)
            vis = [b for b in allb if b.avail <= d]
            r2 = s.evaluate("solana", "M", vis, d)
            full.append(r2.as_dict() if isinstance(r2, Signal) else None)
        assert inc == full, sid
    hs, ls = F.confirmed_pivots(allb[:50], 3, 3)
    assert all(p["known_at"] == allb[p["i"] + 3].avail for p in hs + ls)
    # repaint check: pivots found on the full history and filtered to what was confirmed by time d are exactly the
    # pivots found using only the bars available at d
    fh, fl = F.confirmed_pivots(allb, 3, 3)
    for i in range(10, len(allb)):
        d = allb[i - 1].avail
        th, tl = F.confirmed_pivots(allb[:i], 3, 3)
        assert [p["i"] for p in th] == [p["i"] for p in fh if p["known_at"] <= d]
        assert [p["i"] for p in tl] == [p["i"] for p in fl if p["known_at"] <= d]


def test_g05_signal_decision_after_bar_available_and_leak_refused():
    s = registry.make("BREAKOUT_CLOSE", lookback=10)
    b = bars_from(flat(10) + [(1.0, 1.30, 0.99, 1.20, 500)])
    with pytest.raises(LeakageError):
        s.evaluate("solana", "M", b, b[-1].end)               # bar closed but not yet published (lag 60 s)
    sig = s.evaluate("solana", "M", b, b[-1].avail)
    assert sig.decision_time >= b[-1].avail
    forming = [Bar(x.start, H, x.o, x.h, x.l, x.c, x.v, x.avail) for x in b]
    assert len(closed_bars(forming, b[-1].start + 600)) == len(b) - 1


# G19: absorption is an observed feature plus a labeled interpretation, never a forecast
def test_g19_absorption_observed_vs_interpreted():
    rows = []
    for i in range(12):
        down = i % 2 == 0
        rows.append((1.0, 1.04, 0.98 + 0.001 * i, 0.99 if down else 1.02, (300 - 20 * i) if down else 80))
    rows.append((1.02, 1.10, 1.01, 1.08, 200))
    b = bars_from(rows)
    sig = registry.make("ABSORPTION_BREAK", k=12).evaluate("solana", "M", b, b[-1].avail)
    assert isinstance(sig, Signal) and sig.claim == "SETUP"
    assert sig.features["down_volume_slope"] < 0 and "inference" in sig.features["interpretation"]
    rising = [(o, h, l, c, (v + 40 * i) if c < o else v) for i, (o, h, l, c, v) in enumerate(rows[:-1])] + [rows[-1]]
    b2 = bars_from(rising)
    assert registry.make("ABSORPTION_BREAK", k=12).evaluate("solana", "M", b2, b2[-1].avail) is None


# G31: a brand-new token never gets a token-specific claim
def test_g31_new_token_insufficient_history():
    b = bars_from(flat(3))
    for sid in ("BREAKOUT_CLOSE", "BREAKOUT_RETEST", "RECLAIM", "TREND_HHHL", "ABSORPTION_BREAK", "MA_CROSS"):
        r = registry.make(sid).evaluate("solana", "NEW", b, b[-1].avail)
        assert isinstance(r, Abstain) and r.reason == "INSUFFICIENT_HISTORY", sid
    assert isinstance(registry.make("BREAKOUT_CLOSE").evaluate("solana", "NEW", [], T), Abstain)


def test_stale_last_bar_abstains_and_gaps_not_filled():
    b = bars_from(flat(30))
    r = registry.make("BREAKOUT_CLOSE", lookback=10).evaluate("solana", "M", b, b[-1].avail + 10 * H)
    assert isinstance(r, Abstain) and r.reason == "STALE_DATA"


def test_unknown_params_refused_and_params_hash_stable():
    with pytest.raises(ValueError):
        registry.make("BREAKOUT_CLOSE", lookbak=5)
    a, b = registry.make("BREAKOUT_CLOSE", lookback=10), registry.make("BREAKOUT_CLOSE", lookback=10)
    assert a.phash == b.phash != registry.make("BREAKOUT_CLOSE", lookback=11).phash


def test_lab_status_never_overrides_fatal_flag_and_respects_known_at():
    s = registry.make("LAB_STATUS")
    b = bars_from(flat(5))
    t = b[-1].avail + 100
    ok = {"available_at": t, "status": "NEAR ENTRY", "score": 70, "fatal_flags": [], "snapshot": {"nearest_support": 0.9}}
    sig = s.evaluate("solana", "M", b, t, {"thesis": ok})
    assert isinstance(sig, Signal) and sig.exits.stop_price == 0.9
    bad = {**ok, "fatal_flags": ["LP_RISK_CRITICAL"]}
    r = s.evaluate("solana", "M", b, t, {"thesis": bad})
    assert isinstance(r, Abstain) and r.reason == "RISK_FATAL_FLAW"
    with pytest.raises(LeakageError):
        s.evaluate("solana", "M", b, t - 50, {"thesis": ok})
    assert s.evaluate("solana", "M", b, t, {"thesis": {**ok, "status": "DISTRIBUTION RISK"}}) is None


def test_random_baseline_is_deterministic_and_price_blind():
    s = registry.make("RANDOM_ENTRY", p=0.5, seed=3)
    b1 = bars_from(flat(5, px=1.0)); b2 = bars_from(flat(5, px=7.0))
    r1 = s.evaluate("solana", "M", b1, b1[-1].avail); r2 = s.evaluate("solana", "M", b2, b2[-1].avail)
    assert (r1 is None) == (r2 is None)
    assert registry.make("NO_TRADE").evaluate("solana", "M", b1, b1[-1].avail) is None


# ---------------- momentum / exhaustion / liquidity filter ----------------

def ramp(n, start=1.0, step=0.02, v0=5_000.0, vstep=150.0, wick=0.03):
    out, p = [], start
    for i in range(n):
        o, c = p, p * (1 + step)
        out.append((o, c * (1 + wick), o * (1 - wick), c, v0 + i * vstep))
        p = c
    return out


def test_momentum_signals_on_a_clean_uptrend_with_rising_volume():
    b = bars_from(ramp(40))
    r = registry.make("MOMENTUM").evaluate("solana", "M1", b, b[-1].avail)
    assert isinstance(r, Signal) and r.exits.stop_price < b[-1].c
    assert r.latest_input_available_at == b[-1].avail <= r.decision_time
    smooth = bars_from(ramp(40, wick=0.005))                                          # same climb, tiny ranges: far above EMA in ATRs
    r = registry.make("MOMENTUM").evaluate("solana", "M1", smooth, smooth[-1].avail)
    assert isinstance(r, Abstain) and r.reason == "EXHAUSTION"


def test_momentum_abstains_on_blowoff_bar_and_illiquid_tape():
    rows = ramp(39, wick=0.005)
    last_c = rows[-1][3]
    rows.append((last_c, last_c * 1.6, last_c * 0.98, last_c * 1.05, 20_000.0))   # huge range, closes in its lower half
    b = bars_from(rows)
    r = registry.make("MOMENTUM").evaluate("solana", "M1", b, b[-1].avail)
    assert isinstance(r, Abstain) and r.reason == "EXHAUSTION"
    thin = bars_from(ramp(40, v0=100.0, vstep=5.0))
    r = registry.make("MOMENTUM").evaluate("solana", "M1", thin, thin[-1].avail)
    assert isinstance(r, Abstain) and r.reason == "ILLIQUID"


# ---------------- malformed periods, alternate routes, same symbol ----------------

def test_malformed_series_is_refused_not_guessed():
    from memelab.backtest.strategies.base import MalformedBars
    b = bars_from(flat(30))
    mixed = b[:10] + [B(b[10].start, b[10].start + 300, 1, 1, 1, 1, 1, b[10].start + 360)] + b[11:]   # one 5-minute bar
    with pytest.raises(MalformedBars):
        registry.make("BREAKOUT_CLOSE").evaluate("solana", "X", mixed, mixed[-1].avail)
    shuffled = b[:5] + [b[6], b[5]] + b[7:]
    with pytest.raises(MalformedBars):
        registry.make("BREAKOUT_CLOSE").evaluate("solana", "X", shuffled, shuffled[-1].avail)
    gapped = b[:10] + b[13:]                                                          # missing hours are allowed (no trades)
    assert registry.make("BREAKOUT_CLOSE").evaluate("solana", "X", gapped, gapped[-1].avail) is None


def test_alternate_pool_basis_is_explicit_and_recorded():
    rows = flat(24) + [(1.0, 1.3, 1.0, 1.25, 1000.0)]
    pool_a, pool_b = bars_from(rows), bars_from(flat(25))                             # same token, two pools, different tape
    s = registry.make("BREAKOUT_CLOSE", lookback=24)
    a, b = s.evaluate("solana", "TOK", pool_a, pool_a[-1].avail), s.evaluate("solana", "TOK", pool_b, pool_b[-1].avail)
    assert isinstance(a, Signal) and b is None
    assert a.based_on == (pool_a[0].start, pool_a[-1].start)                         # the bars actually used are recorded


def test_two_tokens_with_the_same_symbol_never_share_a_signal():
    rows = flat(24) + [(1.0, 1.3, 1.0, 1.25, 1000.0)]
    b = bars_from(rows)
    s = registry.make("BREAKOUT_CLOSE", lookback=24)
    x = s.evaluate("solana", "MintAAAA1111pump", b, b[-1].avail)
    y = s.evaluate("solana", "MintBBBB2222pump", b, b[-1].avail)                        # same ticker in the wild, different mint
    assert x.mint != y.mint and x.signal_id != y.signal_id
    z = s.evaluate("base", "MintAAAA1111pump", b, b[-1].avail)                          # identity is {chain, mint}
    assert z.signal_id != x.signal_id


def test_future_bar_refused_even_when_no_signal_would_result():
    """Deciding NOT to trade from a future bar is lookahead too (it changes which trades exist)."""
    b = bars_from(flat(30))
    for sid in ("BREAKOUT_CLOSE", "TREND_HHHL", "MOMENTUM", "ABSORPTION_BREAK"):
        with pytest.raises(LeakageError):
            registry.make(sid).evaluate("solana", "X", b, b[-1].avail - 1)
