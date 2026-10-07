"""Tests for m13-m18 on synthetic OHLCV and quotes."""
from __future__ import annotations

import math

import numpy as np
import pytest

from memelab.modules import (
    m13_price_structure as m13,
    m14_breakout_classifier as m14,
    m15_entry_invalidation as m15,
    m16_risk_reward as m16,
    m17_position_sizing as m17,
    m18_exit_planning as m18,
)

T0 = 1_759_000_000  # epoch seconds, arbitrary
BUCKETS = ("facts", "inferences", "heuristics", "unknowns")


def _candles_from_path(path, vols, step=3600, noise=0.004, seed=1):
    """Build hourly candles from a close path; returned NEWEST FIRST like GeckoTerminal."""
    rng = np.random.default_rng(seed)
    rows = []
    prev = path[0]
    for i, (c, v) in enumerate(zip(path, vols)):
        o = prev
        wick = abs(c) * noise * (1 + rng.random())
        h = max(o, c) + wick
        l = min(o, c) - wick
        rows.append([T0 + i * step, o, h, l, c, v])
        prev = c
    return rows[::-1]


def _zigzag(start, end, n, legs, amp):
    """Trend from start to end over n candles with `legs` zigzag legs of relative amplitude amp."""
    base = np.linspace(start, end, n)
    osc = amp * np.sin(np.linspace(0, legs * np.pi, n))
    return base * (1 + osc)


def make_uptrend_breakout():
    """Uptrend 1.00 -> 1.42, consolidation 1.44-1.54 with 4 touches each side, breakout to ~1.66 on
    3x volume with 6 accepting closes, a retest dipping to the zone high, then holding ~1.62."""
    rng = np.random.default_rng(7)
    p1 = _zigzag(1.00, 1.42, 80, legs=5, amp=0.03)
    # consolidation: oscillate between 1.44 and 1.54, 8 half-cycles
    t = np.linspace(0, 4 * np.pi, 80)
    p2 = 1.49 + 0.05 * np.sin(t)
    # breakout: strong closes above 1.54
    p3 = np.array([1.555, 1.58, 1.60, 1.63, 1.65, 1.66, 1.64, 1.60, 1.57, 1.56, 1.59, 1.61, 1.62, 1.63, 1.62, 1.625, 1.61, 1.62, 1.615, 1.62])
    path = np.concatenate([p1, p2, p3])
    vols = np.concatenate([
        rng.uniform(8_000, 12_000, len(p1)),
        rng.uniform(6_000, 9_000, len(p2)),
        np.array([30_000, 28_000, 22_000, 18_000, 15_000, 12_000, 9_000, 8_000, 7_000, 7_500, 9_000, 8_000, 7_000, 7_000, 6_500, 7_000, 6_500, 7_000, 6_500, 7_000]),
    ])
    hour1 = _candles_from_path(path, vols)
    # daily: 30 candles, rising, newest first
    dpath = _zigzag(0.6, 1.60, 30, legs=2, amp=0.04)
    day1 = _candles_from_path(dpath, rng.uniform(150_000, 250_000, 30), step=86400)
    return {"hour1": hour1, "day1": day1}, float(path[-1])


def make_range():
    rng = np.random.default_rng(3)
    t = np.linspace(0, 8 * np.pi, 200)
    path = 1.10 + 0.10 * np.sin(t) + rng.normal(0, 0.003, 200)
    path[-1] = 1.10
    vols = rng.uniform(5_000, 9_000, 200)
    return {"hour1": _candles_from_path(path, vols)}, 1.10


def make_quotes():
    buy = {500: {"in": 500, "out": 1, "impact": 0.3, "status": "ok"},
           1000: {"in": 1000, "out": 1, "impact": 0.6, "status": "ok"},
           2500: {"in": 2500, "out": 1, "impact": 1.5, "status": "ok"},
           5000: {"in": 5000, "out": 1, "impact": 3.2, "status": "ok"},
           10000: {"in": 10000, "out": 1, "impact": 7.0, "status": "ok"}}
    sell = {500: {"in": 1, "out": 498, "impact": 0.35, "status": "ok"},
            1000: {"in": 1, "out": 993, "impact": 0.7, "status": "ok"},
            2500: {"in": 1, "out": 2455, "impact": 1.8, "status": "ok"},
            5000: {"in": 1, "out": 4800, "impact": 4.0, "status": "ok"},
            10000: {"in": 1, "out": 9100, "impact": 9.0, "status": "ok"}}
    return {"BUY": buy, "SELL": sell}


def _bundle(ohlcv, price, quotes=None):
    return {"mint": "TEST", "ohlcv": ohlcv, "quotes": quotes or make_quotes(),
            "market": {"price_usd": price, "vol": {"h1": 50_000, "h24": 600_000},
                       "txns": {"h1": [120, 80, 90, 60]}, "net_buyers": {"h1": 30}},
            "authorities": {"transfer_fee_bps": None}, "pools": [{"pool": "p1"}]}


@pytest.fixture(scope="module")
def up():
    ohlcv, price = make_uptrend_breakout()
    b = _bundle(ohlcv, price)
    s = m13.analyze(b)
    br = m14.analyze(b, structure=s)
    en = m15.analyze(b, structure=s, breakout=br)
    return b, s, br, en


@pytest.fixture(scope="module")
def rng_case():
    ohlcv, price = make_range()
    b = _bundle(ohlcv, price)
    s = m13.analyze(b)
    br = m14.analyze(b, structure=s)
    en = m15.analyze(b, structure=s, breakout=br)
    return b, s, br, en


def _check_buckets(res):
    assert isinstance(res, dict)
    for k in BUCKETS:
        assert isinstance(res[k], list), k


# ----------------------------------------------------------------------------- m13

def test_m13_uptrend_structure(up):
    b, s, _, _ = up
    _check_buckets(s)
    assert s["structure"] in ("UPTREND", "PRICE_DISCOVERY")
    assert s["per_timeframe"]["hour1"]["structure"] in ("UPTREND", "PRICE_DISCOVERY")
    assert s["per_timeframe"]["day1"]["structure"] in ("UPTREND", "PRICE_DISCOVERY")
    assert s["ath"] >= 1.66 and s["atl"] < 1.0
    assert s["pct_from_ath"] < 0
    # the consolidation 1.44-1.54 must appear as a support zone below price with several touches
    sup = [z for z in s["zones"] if z["kind"] == "SUPPORT" and z["tf"] == "hour1" and 1.40 <= z["low"] and z["high"] <= 1.58]
    assert sup, s["zones"]
    assert max(z["touches"] for z in sup) >= 3
    assert s["nearest_support"] is not None and s["nearest_support"]["high"] < b["market"]["price_usd"]
    for z in s["zones"]:
        assert set(("tf", "kind", "low", "high", "mid", "touches", "strength", "distance_pct", "why")) <= set(z)
        assert z["low"] <= z["mid"] <= z["high"]
        assert z["why"]
    v = s["volatility"]["hour1"]
    assert v["per_candle_pct"] is not None and v["per_24h_pct"] > v["per_candle_pct"]
    assert v["atr_pct"] is not None and v["atr_pct"] > 0


def test_m13_candle_order_independent(up):
    b, s, _, _ = up
    b2 = dict(b, ohlcv={k: list(reversed(v)) for k, v in b["ohlcv"].items()})
    s2 = m13.analyze(b2)
    assert s2["structure"] == s["structure"]
    assert s2["ath"] == s["ath"]
    assert len(s2["zones"]) == len(s["zones"])


def test_m13_range_structure(rng_case):
    b, s, _, _ = rng_case
    assert s["per_timeframe"]["hour1"]["structure"] == "RANGE", s["per_timeframe"]["hour1"]["reason"]
    assert s["structure"] == "RANGE"
    assert s["nearest_support"] is not None and s["nearest_resistance"] is not None
    assert 0.95 <= s["nearest_support"]["mid"] <= 1.06
    assert 1.14 <= s["nearest_resistance"]["mid"] <= 1.25
    assert s["current_range"] is not None and s["current_range"]["low"] < 1.1 < s["current_range"]["high"]


def test_m13_price_discovery():
    rng = np.random.default_rng(11)
    path = _zigzag(1.0, 2.0, 120, legs=6, amp=0.02)
    path[-1] = path.max() * 1.001
    b = _bundle({"hour1": _candles_from_path(path, rng.uniform(5000, 8000, 120))}, float(path[-1]))
    s = m13.analyze(b)
    assert s["per_timeframe"]["hour1"]["structure"] == "PRICE_DISCOVERY"
    assert s["nearest_resistance"] is None


# ----------------------------------------------------------------------------- m14

def test_m14_breakout_confirmed(up):
    b, s, br, _ = up
    _check_buckets(br)
    assert br["classification"] in ("CONFIRMED_BREAKOUT", "BREAKOUT_RETEST"), br
    assert br["volume_expansion_ratio"] is not None and br["volume_expansion_ratio"] >= 1.5
    assert br["breakout_zone"] is not None and br["breakout_zone"]["low"] < b["market"]["price_usd"]
    assert br["evidence"]
    assert br["wick_vs_body"] is not None and br["wick_vs_body"]["body_frac"] is not None
    cr = br["chase_risk"]
    assert cr is not None and cr["distance_pct"] > 0 and cr["distance_atr"] > 0


def test_m14_no_breakout_in_range(rng_case):
    b, s, br, _ = rng_case
    assert br["classification"] in ("NO_BREAKOUT", "EARLY_BREAKOUT_ATTEMPT"), br
    assert br["chase_risk"] is not None


def test_m14_failed_breakout():
    rng = np.random.default_rng(5)
    t = np.linspace(0, 4 * np.pi, 80)
    cons = 1.0 + 0.04 * np.sin(t)
    # break above 1.04 on closes for 4 candles then collapse below 0.96
    tail = np.array([1.06, 1.08, 1.09, 1.07, 1.02, 0.98, 0.95, 0.94, 0.95, 0.945])
    path = np.concatenate([cons, tail])
    vols = np.concatenate([rng.uniform(5000, 7000, 80), [20000, 15000, 9000, 8000, 9000, 14000, 16000, 9000, 8000, 8000]])
    b = _bundle({"hour1": _candles_from_path(path, vols)}, float(path[-1]))
    s = m13.analyze(b)
    br = m14.analyze(b, structure=s)
    assert br["classification"] == "FAILED_BREAKOUT", br


def test_m14_wick_only_is_early_attempt():
    rng = np.random.default_rng(9)
    t = np.linspace(0, 4 * np.pi, 100)
    path = 1.0 + 0.04 * np.sin(t)
    candles = _candles_from_path(path, rng.uniform(5000, 7000, 100))
    # newest first: poke a wick above the range high on the latest candle without closing above
    candles[0][2] = 1.09
    candles[0][4] = 1.02
    b = _bundle({"hour1": candles}, 1.02)
    s = m13.analyze(b)
    br = m14.analyze(b, structure=s)
    assert br["classification"] in ("EARLY_BREAKOUT_ATTEMPT", "NO_BREAKOUT")
    if br["classification"] == "EARLY_BREAKOUT_ATTEMPT":
        assert any("wick" in e.lower() for e in br["evidence"])


# ----------------------------------------------------------------------------- m15

def test_m15_entries_uptrend(up):
    b, s, br, en = up
    _check_buckets(en)
    styles = {e["style"] for e in en["entries"]}
    assert styles, en["omitted"]
    assert styles & {"PULLBACK", "BREAKOUT_RETEST", "ANTICIPATION", "CONFIRMATION"}
    assert set(styles) | set(en["omitted"]) == set(m15.STYLES)
    price = b["market"]["price_usd"]
    for e in en["entries"]:
        for k in ("style", "condition", "zone_low", "zone_high", "thesis", "why_exists", "evidence", "invalidation_level",
                  "invalidation_text", "stop_location", "expected_execution", "advantages", "disadvantages"):
            assert k in e, k
        assert e["zone_low"] <= e["zone_high"]
        assert e["invalidation_level"] < (e["zone_low"] + e["zone_high"]) / 2
        assert e["stop_location"] < e["invalidation_level"]  # stop is beyond the structural level
        assert "close" in e["invalidation_text"].lower()
        # never a fixed 10% stop
        mid = (e["zone_low"] + e["zone_high"]) / 2
        assert not math.isclose((mid - e["stop_location"]) / mid, 0.10, abs_tol=1e-4)
        assert e["evidence"] and e["advantages"] and e["disadvantages"]


def test_m15_range_entries(rng_case):
    b, s, br, en = rng_case
    styles = {e["style"] for e in en["entries"]}
    assert "ANTICIPATION" in styles, en["omitted"]
    assert "CONFIRMATION" in en["omitted"]
    assert "PULLBACK" in en["omitted"]
    ant = next(e for e in en["entries"] if e["style"] == "ANTICIPATION")
    assert ant["zone_high"] < b["market"]["price_usd"]


# ----------------------------------------------------------------------------- m16

def test_m16_scenarios(up, rng_case):
    for b, s, br, en in (up, rng_case):
        rr = m16.analyze(b, entries=en["entries"], structure=s)
        _check_buckets(rr)
        assert len(rr["per_entry"]) == len(en["entries"])
        for pe in rr["per_entry"]:
            sc = pe["scenarios"]
            assert set(sc) == {"BEAR", "BASE", "BULL", "EXTREME"}
            assert sc["BEAR"]["r"] == -1.0
            assert sc["BASE"]["target"] > pe["entry_price"]
            assert sc["BULL"]["target"] >= sc["BASE"]["target"]
            assert sc["EXTREME"]["target"] >= sc["BULL"]["target"]
            for k in sc:
                assert sc[k]["what_must_happen"]
                assert sc[k]["r"] == round(sc[k]["r"], 1)
            assert pe["ev_r_low"] <= pe["ev_r_high"]
            assert pe["distance_to_invalidation_pct"] > 0
            assert "RANGE" in pe["uncertainty"]


# ----------------------------------------------------------------------------- m17

def test_m17_liquidity_only_without_account(up):
    b, s, br, en = up
    ps = m17.analyze(b, entries=en["entries"], structure=s)
    _check_buckets(ps)
    assert ps["needs_account_inputs"] is True
    lc = ps["liquidity_constraint"]
    assert lc["entry_max"] is not None and 1000 < lc["entry_max"] <= 2500  # 1.5% impact lies at the 2500 tested point
    assert lc["exit_max_now"] is not None and 2500 < lc["exit_max_now"] < 5000
    assert set(lc["exit_max_by_multiple"]) == {2, 5, 10}
    assert lc["exit_max_by_multiple"][2] > lc["exit_max_by_multiple"][5] > lc["exit_max_by_multiple"][10]
    assert math.isclose(lc["exit_max_by_multiple"][10] * 10, lc["exit_max_now"])
    assert ps["allowed_size_usd"] is not None and ps["allowed_size_usd"] > 0
    assert "liquidity" in ps["binding_constraint"]
    assert ps["risk_constraint"]["size_usd"] is None


def test_m17_with_account(up):
    b, s, br, en = up
    ps = m17.analyze(b, entries=en["entries"], structure=s, account_size=10_000, max_loss_pct=2.0)
    assert ps["needs_account_inputs"] is False
    assert ps["risk_constraint"]["max_loss_usd"] == 200.0
    assert ps["risk_constraint"]["size_usd"] > 0
    assert ps["allowed_size_usd"] <= ps["risk_constraint"]["size_usd"] + 0.01
    assert ps["allowed_size_usd"] <= ps["liquidity_constraint"]["liquidity_max_usd"] + 0.01
    assert ps["binding_constraint"]
    for pe in ps["per_entry"]:
        if pe.get("loss_at_stop_usd") is not None:
            assert pe["loss_at_stop_usd"] <= 200.0 + 1e-6


def test_m17_haircuts():
    ohlcv, price = make_uptrend_breakout()
    b = _bundle(ohlcv, price)
    b["authorities"] = {"transfer_fee_bps": 100}
    for side in ("BUY", "SELL"):
        for v in b["quotes"][side].values():
            v["route"] = ["p1", "p2", "p3"]
    s = m13.analyze(b)
    en = m15.analyze(b, structure=s)
    ps = m17.analyze(b, entries=en["entries"], structure=s, account_size=10_000, max_loss_usd=300)
    names = {h["name"] for h in ps["haircuts"]}
    assert {"transfer_fee", "route_fragmentation"} <= names
    plain = m17.analyze(_bundle(ohlcv, price), entries=en["entries"], structure=s, account_size=10_000, max_loss_usd=300)
    assert ps["allowed_size_usd"] < plain["allowed_size_usd"]


def test_m17_fraction_impacts_detected():
    ohlcv, price = make_uptrend_breakout()
    q = make_quotes()
    for side in q.values():
        for v in side.values():
            v["impact"] = v["impact"] / 100.0
    b = _bundle(ohlcv, price, quotes=q)
    ps = m17.analyze(b, entries=[])
    assert any("fraction" in h for h in ps["heuristics"])
    assert 1000 < ps["liquidity_constraint"]["entry_max"] <= 2500


# ----------------------------------------------------------------------------- m18

def test_m18_exit_plan(up):
    b, s, br, en = up
    ex = m18.analyze(b, entries=en["entries"], structure=s, quotes=b["quotes"], position_usd=1000)
    _check_buckets(ex)
    assert ex["entry_price"] is not None
    pr = ex["principal_reclaim"]
    assert pr["pct_if_nothing_sold_before"] == 50.0
    assert 0 < pr["pct_of_position_to_sell"] <= 50.0
    # cumulative proceeds through the principal-reclaim rung must cover the principal
    proceeds = 0.0
    for l in ex["ladder"]:
        if l["multiple"] is None:
            continue
        proceeds += l["pct_of_position"] / 100.0 * l["multiple"]
        if l.get("kind") == "principal_reclaim":
            break
    assert proceeds >= 0.99, ex["ladder"]
    # near supply (< 1.5x) only gets a trim, never the bulk of the position
    for l in ex["ladder"]:
        if l["multiple"] is not None and l["multiple"] < 1.5:
            assert l["pct_of_position"] <= 25.0
    assert ex["trailing_invalidation"] is not None and "close" in ex["trailing_invalidation"]["text"].lower()
    assert ex["blowoff"] is not None
    r = ex["realizable"]
    assert set(r) == {2, 5, 10}
    assert r[2]["displayed"] == 2000 and r[10]["displayed"] == 10000
    for m in (2, 5, 10):
        assert r[m]["realizable"] < r[m]["displayed"]
    assert r[10]["impact_pct"] > r[2]["impact_pct"]
    assert r[10]["flag"] in ("exact", "interpolated")
    for l in ex["ladder"]:
        assert set(("trigger", "zone", "pct_of_position", "rationale")) <= set(l)
    total = sum(l["pct_of_position"] for l in ex["ladder"]) + ex["runner"]["pct_of_position"]
    assert total <= 100.0 + 1e-6


def test_m18_beyond_tested_depth(up):
    b, s, br, en = up
    ex = m18.analyze(b, entries=en["entries"], structure=s, position_usd=5000)
    assert ex["realizable"][10]["displayed"] == 50_000
    assert ex["realizable"][10]["flag"] == "beyond_tested_depth"
    assert ex["realizable"][10]["impact_pct"] >= 9.0 * 5  # at least linear scaling from the largest tested point
    assert any("beyond" in u for u in ex["unknowns"])


# ----------------------------------------------------------------------------- empty bundle

EMPTY = {"ohlcv": {}, "market": {}, "quotes": {}}


def test_all_modules_on_empty_bundle():
    s = m13.analyze(EMPTY)
    _check_buckets(s)
    assert s["structure"] in m13.STRUCTURES and s["zones"] == [] and s["ath"] is None and s["unknowns"]
    br = m14.analyze(EMPTY, structure=s)
    _check_buckets(br)
    assert br["classification"] == "NO_BREAKOUT" and br["unknowns"]
    en = m15.analyze(EMPTY, structure=s, breakout=br)
    _check_buckets(en)
    assert en["entries"] == [] and set(en["omitted"]) == set(m15.STYLES)
    rr = m16.analyze(EMPTY, entries=en["entries"], structure=s)
    _check_buckets(rr)
    assert rr["per_entry"] == []
    ps = m17.analyze(EMPTY, entries=en["entries"], structure=s)
    _check_buckets(ps)
    assert ps["needs_account_inputs"] is True and ps["allowed_size_usd"] is None
    ex = m18.analyze(EMPTY, entries=en["entries"], structure=s, quotes={})
    _check_buckets(ex)
    assert ex["ladder"] == [] and ex["unknowns"]
    # also without kwargs at all, and with None / garbage inputs
    for mod in (m13, m14, m15, m16, m17, m18):
        _check_buckets(mod.analyze(EMPTY))
        _check_buckets(mod.analyze({}))
        _check_buckets(mod.analyze(None))
        _check_buckets(mod.analyze({"ohlcv": {"hour1": None, "day1": [[1, None, 2], "x"]}, "market": None, "quotes": None}))
