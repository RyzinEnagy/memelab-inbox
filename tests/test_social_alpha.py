"""Phase 11: Information Alpha Score.

Invented data only. Hand-worked numbers are in test_hand_checked_single_call and docs/social-intelligence/ALPHA_11.md. No network, no clock.
"""
import copy
import importlib.util
import json
import math
import random
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from memelab import db
from memelab.social import alpha_core as A, alpha_store as S, schema, store

ROOT = Path(__file__).resolve().parent.parent
FX = ROOT / "tests" / "fixtures" / "social" / "alpha"
_spec = importlib.util.spec_from_file_location("make_alpha", FX / "make_alpha.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
T0, H, HOURS = M.T0, M.H, M.HOURS
POL = {"horizons_s": [3600, 86400], "primary_horizon_s": 86400}
MAIN = json.loads((FX / "alpha_main.json").read_text())


def pool(mults=(0.8, 0.9, 1.0, 1.0, 1.1, 1.2), **kw):
    return [M.series(f"BK{i + 1:02d}", M.flat_then(12, m), **kw) for i, m in enumerate(mults)]


def doc(calls, series, sources=None, as_of=None, **extra):
    d = {"schema": A.SCHEMA, "label": "FIXTURE: test", "is_fixture": True, "as_of": as_of or T0 + HOURS * H, "calls": calls, "series": series,
         "sources": sources or {}}
    d.update(extra)
    return d


def one(sid="s1", token="X1", mult=1.5, pub_h=12, **kw):
    return M.call(f"{sid}-{token}", sid, token, pub_h, **kw), M.series(token, M.flat_then(pub_h, mult))


def run(d, **pol):
    return A.analyze(d, dict(POL, **pol))


def by_id(res, cid):
    return next(c for c in res["calls"] if c["call_id"] == cid)


def prim(c):
    return c["horizons"]["86400"]


# ---------- the numbers ----------

def test_hand_checked_single_call():
    """Entry 1.00, exit 1.50, 500 USD into a 100000 pool. Cost per side = 1.00% fee + 0.50% slippage + 2 * 500 / 100000 impact = 2.5%.
    Net = 1.5 * 0.975 / (1.0 * 1.025) - 1 = 0.4268292683. Six matched tokens exit at 0.8 0.9 1.0 1.0 1.1 1.2: median 1.0,
    net 1.0 * 0.975 / 1.025 - 1 = -0.0487804878. Relative = 0.4756097561."""
    c, s = one(mult=1.5)
    r = run(doc([c], [s] + pool()))
    x = by_id(r, c["call_id"])
    en = x["entry"]
    assert en["price"] == 1.0 and en["cost"] == 0.025 and en["participation"] == 0.005 and en["wait_s"] == 0
    assert x["decision_t"] == c["first_observed_at"] + 300
    h = prim(x)
    assert h["exit"]["price"] == 1.5 and h["exit"]["cost"] == 0.025
    assert h["net"] == round(1.5 * 0.975 / 1.025 - 1, 10) == 0.4268292683
    assert h["baseline"]["n"] == 6 and h["baseline"]["median"] == round(0.975 / 1.025 - 1, 10)
    assert h["relative"] == round(1.5 * 0.975 / 1.025 - 0.975 / 1.025, 10) == 0.4756097561
    assert [m["net"] for m in h["baseline"]["members"]][:2] == [round(0.8 * 0.975 / 1.025 - 1, 10), round(0.9 * 0.975 / 1.025 - 1, 10)]


def _independent_net(ser, t_entry, t_exit, direction=1, size=500.0):
    """Second implementation of the arithmetic, straight from raw candles; shares no code with the engine."""
    def row(t):
        return next(r for r in ser["rows"] if r["t"] <= t < r["t"] + ser["candle_seconds"])
    en = row(t_entry)
    try:
        ex = row(t_exit)
    except StopIteration:                  # delisted before the exit: a long is a total loss
        return -1.0
    cin, cout = 0.015 + 2 * size / en["liq"], 0.015 + 2 * size / ex["liq"]
    if direction > 0:
        return ex["o"] * (1 - cout) / (en["o"] * (1 + cin)) - 1
    return -(ex["o"] / en["o"] - 1) - cin - cout


def test_fixture_calls_recompute_independently_from_raw_candles():
    r = A.analyze(MAIN, {"horizons_s": [3600, 21600, 86400], "primary_horizon_s": 86400})
    ser = {s["contract"]: s for s in MAIN["series"]}
    checked = 0
    for cid in ("a02", "a05", "a09", "a10", "b01", "b03"):
        x = by_id(r, cid)
        call = next(c for c in MAIN["calls"] if c["call_id"] == cid)
        t0 = max(call["published_at"], call["first_observed_at"]) + 300
        h = prim(x)
        assert h["net"] == pytest.approx(_independent_net(ser[call["token"]["contract"]], t0, t0 + 86400), abs=1e-9)
        bl = [_independent_net(ser[m], t0, t0 + 86400) for m in x["baseline_tokens"]]
        assert h["baseline"]["median"] == pytest.approx(sorted(bl)[len(bl) // 2 - 1] / 2 + sorted(bl)[len(bl) // 2] / 2, abs=1e-9)
        assert h["relative"] == pytest.approx(h["net"] - h["baseline"]["median"], abs=1e-9)
        checked += 1
    assert checked == 6


def test_short_signed_return_and_mfe_mae():
    c, s = one(mult=0.7, direction="SHORT")
    r = run(doc([c], [s] + pool()))
    h = prim(by_id(r, c["call_id"]))
    assert h["net"] == pytest.approx(-(0.7 / 1.0 - 1) - 0.05, abs=1e-9)
    assert "SHORT_NOT_EXECUTABLE_ON_SPOT" in by_id(r, c["call_id"])["flags"]
    p = h["path"]
    assert p["status"] == "OK" and p["coverage"] == 1.0 and p["mfe"] > 0 and p["mae"] < p["mfe"]


def test_mfe_mae_need_path_coverage():
    c, s = one(mult=1.5)
    s["rows"] = [r for r in s["rows"] if not (T0 + 20 * H <= r["t"] < T0 + 30 * H)]
    r = run(doc([c], [s] + pool()))
    p = prim(by_id(r, c["call_id"]))["path"]
    assert p["status"] == "INSUFFICIENT_PATH_COVERAGE" and p["coverage"] < 0.8 and "mfe" not in p


def test_adverse_entry_rule_lowers_return():
    c, s = one(mult=1.5)
    base = prim(by_id(run(doc([c], [s] + pool())), c["call_id"]))["net"]
    adv = prim(by_id(run(doc([c], [s] + pool()), entry_price_rule="CANDLE_ADVERSE"), c["call_id"]))["net"]
    assert adv < base


def test_delay_and_horizons_are_configurable():
    c, s = one(mult=1.5)
    r = run(doc([c], [s] + pool()), delay_s=3000)
    assert by_id(r, c["call_id"])["decision_t"] == c["first_observed_at"] + 3000
    with pytest.raises(ValueError):
        A.evaluate(doc([c], [s]), {"primary_horizon_s": 12345})
    with pytest.raises(ValueError):
        A.evaluate(doc([c], [s]), {"nonsense": 1})


# ---------- required cases ----------

def test_late_promotion_after_pump_is_kept_flagged_and_negative():
    r = A.analyze(MAIN, {"horizons_s": [3600, 21600, 86400], "primary_horizon_s": 86400})
    x = by_id(r, "a20")
    assert "LATE_PROMOTION" in x["flags"] and x["pre_move"] >= 1.0
    assert x["lead_time_status"] == "POSTED_AFTER_ONSET" and x["lead_time_s"] < 0
    assert x["status"] == "EVALUATED" and prim(x)["net"] < 0 and prim(x)["relative"] < 0     # counted, not hidden
    assert r["sources"]["src_a"]["flags"]["late_promotion_calls"] == 1
    assert r["sources"]["src_a"]["lead_time"]["n_posted_after_onset"] >= 1


def test_hindsight_selected_calls_are_ineligible_and_the_source_is_declined():
    r = A.analyze(MAIN, {"horizons_s": [3600, 21600, 86400], "primary_horizon_s": 86400})
    c = r["sources"]["src_c"]
    assert c["counts"]["ineligible_by_reason"] == {"HINDSIGHT_CAPTURE_RISK": 6} and c["counts"]["eligible_independent"] == 0
    assert c["score"]["status"] == "DECLINED" and c["score"]["score"] is None
    assert any("picked" in x for x in c["score"]["reasons"])                     # 6 of 40 enumerated posts supplied
    assert "src_c" not in [x["source_id"] for x in r["ranking"]["ranked"]]
    assert r["sources"]["src_c"]["context_not_in_formula"]["followers"] == 5000000


def test_an_unknown_observation_time_is_also_hindsight_risk():
    c, s = one()
    c["first_observed_at"] = None
    assert by_id(run(doc([c], [s] + pool())), c["call_id"])["reasons"] == ["HINDSIGHT_CAPTURE_RISK"]
    c2, s2 = one(token="X2")
    c2["first_observed_at"] = c2["published_at"] - 3600
    assert by_id(run(doc([c2], [s2] + pool())), c2["call_id"])["reasons"] == ["OBSERVED_BEFORE_PUBLISHED"]


def test_repeated_reposts_and_repeat_posts_do_not_inflate_the_sample():
    cs, ss = [], []
    for i in range(12):
        c, s = one(token=f"W{i:02d}", mult=1.5, pub_h=12 + i % 5)
        cs.append(c)
        ss.append(s)
    clean = run(doc(cs, ss + pool(), sources={"s1": {"label": "x"}}))
    spam = copy.deepcopy(cs)
    for k in range(10):                                                          # ten reposts of the first call
        rp = copy.deepcopy(cs[0]); rp.update(call_id=f"rp{k}", original=False, item_key=f"fixture:x:rp{k}")
        spam.append(rp)
    for k in range(5):                                                           # five repeats by the same source, same token, later
        rp = copy.deepcopy(cs[1]); rp.update(call_id=f"rep{k}", item_key=f"fixture:x:rep{k}")
        rp["published_at"] += 600 * (k + 1); rp["first_observed_at"] += 600 * (k + 1)
        spam.append(rp)
    noisy = run(doc(spam, ss + pool(), sources={"s1": {"label": "x"}}))
    a, b = clean["sources"]["s1"], noisy["sources"]["s1"]
    assert a["horizons"]["86400"]["n_with_baseline"] == b["horizons"]["86400"]["n_with_baseline"] == 12
    assert b["counts"]["ineligible_by_reason"] == {"NOT_ORIGINAL": 10, "REPEAT_POST": 5}
    assert a["score"]["score"] == b["score"]["score"] and a["score"]["n_independent_with_baseline"] == 12
    # the same token again after the dedupe window is a new independent call
    later = copy.deepcopy(cs[0]); later.update(call_id="later", published_at=cs[0]["published_at"] + 8 * 86400, first_observed_at=cs[0]["first_observed_at"] + 8 * 86400)
    r = run(doc([cs[0], later], ss[:1] + pool(), as_of=T0 + 20 * 86400))
    assert by_id(r, "later")["reasons"] != ["REPEAT_POST"]


def test_delisted_tokens_are_total_losses_for_longs_and_get_no_extra_credit_for_shorts():
    r = A.analyze(MAIN, {"horizons_s": [3600, 21600, 86400], "primary_horizon_s": 86400})
    x = by_id(r, "a21")
    assert prim(x)["exit"]["kind"] == "DELISTED_TOTAL_LOSS" and prim(x)["net"] == -1.0
    rugged = [m for m in prim(by_id(r, "a02"))["baseline"]["members"] if m["contract"] == "BK09"]
    assert rugged and rugged[0]["net"] == -1.0 and rugged[0]["exit_kind"] == "DELISTED_TOTAL_LOSS"      # the rug is in the control group too
    s = M.series("D1", M.flat_then(12, 0.5), delisted_hour=30)
    c = M.call("d1", "s1", "D1", 12, direction="SHORT")
    h = prim(by_id(run(doc([c], [s] + pool())), "d1"))
    last = s["rows"][-1]
    assert h["exit"]["kind"] == "DELISTED_LAST_PRICE_NO_EXTRA_CREDIT" and h["exit"]["price"] == last["c"]
    s2 = M.series("D2", M.flat_then(12, 0.5), delisted_hour=10)
    c2 = M.call("d2", "s1", "D2", 12)
    assert by_id(run(doc([c2], [s2] + pool())), "d2")["reasons"] == ["TOKEN_DELISTED_BEFORE_ENTRY"]


def test_price_gaps_are_not_filled():
    c, s = one(mult=1.5)
    g = copy.deepcopy(s)
    g["rows"] = [r for r in g["rows"] if not (T0 + 12 * H <= r["t"] < T0 + 15 * H)]
    assert by_id(run(doc([c], [g] + pool())), c["call_id"])["reasons"] == ["NO_ENTRY_PRICE_PRICE_GAP"]
    e = copy.deepcopy(s)
    e["rows"] = [r for r in e["rows"] if not (T0 + 36 * H <= r["t"] < T0 + 40 * H)]
    x = by_id(run(doc([c], [e] + pool())), c["call_id"])
    assert x["horizons"]["3600"]["status"] == "OK" and prim(x) == {"horizon_s": 86400, "status": "NOT_EVALUABLE", "reason": "NO_EXIT_PRICE_PRICE_GAP"}
    # a gap shorter than the allowed wait: the order fills at the next candle open, later and at that price
    c2 = M.call("w", "s1", "W", 12, offset=3000)
    s2 = M.series("W", M.flat_then(12, 1.5))
    s2["rows"] = [r for r in s2["rows"] if r["t"] != T0 + 12 * H]
    en = by_id(run(doc([c2], [s2] + pool())), "w")["entry"]
    assert en["wait_s"] == 180 and en["fill_t"] == T0 + 13 * H and en["price"] == next(r["o"] for r in s2["rows"] if r["t"] == T0 + 13 * H)
    # a series that simply ends is not a loss and not interpolated
    h = copy.deepcopy(s)
    h["rows"] = [r for r in h["rows"] if r["t"] < T0 + 20 * H]
    assert prim(by_id(run(doc([c], [h] + pool())), c["call_id"]))["reason"] == "NO_EXIT_PRICE_HISTORY_ENDS"


def test_illiquid_execution_is_refused_or_charged():
    c, s = one(mult=1.5)
    thin = M.series("X1", M.flat_then(12, 1.5), liq=5000.0)
    assert by_id(run(doc([c], [thin] + pool())), c["call_id"])["reasons"] == ["ILLIQUID_ENTRY"]
    mid = M.series("X1", M.flat_then(12, 1.5), liq=20000.0)
    x = by_id(run(doc([c], [mid] + pool(liq=20000.0))), c["call_id"])
    assert x["entry"]["cost"] == 0.065                       # 1.5% + 2 * 500 / 20000
    assert prim(x)["net"] < prim(by_id(run(doc([c], [s] + pool())), c["call_id"]))["net"]
    # the pool dries up after the call: exit costs 1.5% + 2 * 500 / 2000 = 51.5%
    dry = copy.deepcopy(s)
    for r in dry["rows"]:
        if r["t"] >= T0 + 30 * H:
            r["liq"] = 2000.0
    h = prim(by_id(run(doc([c], [dry] + pool())), c["call_id"]))
    assert h["exit"]["cost"] == 0.515 and h["net"] == pytest.approx(1.5 * (1 - 0.515) / 1.025 - 1, abs=1e-9)
    unk = copy.deepcopy(s)
    for r in unk["rows"]:
        if r["t"] >= T0 + 30 * H:
            del r["liq"]
    h = prim(by_id(run(doc([c], [unk] + pool())), c["call_id"]))
    assert h["exit"]["kind"] == "EXIT_LIQUIDITY_UNKNOWN" and h["exit"]["cost"] == 0.5
    nol = copy.deepcopy(s)
    for r in nol["rows"]:
        del r["liq"]
    assert by_id(run(doc([c], [nol] + pool())), c["call_id"])["reasons"] == ["LIQUIDITY_UNKNOWN"]
    # a long can lose at most everything
    ruin = copy.deepcopy(s)
    for r in ruin["rows"]:
        if r["t"] >= T0 + 30 * H:
            r["liq"] = 100.0
    assert prim(by_id(run(doc([c], [ruin] + pool())), c["call_id"]))["net"] == -1.0


def test_null_baseline_gives_no_edge_and_no_validation():
    cs, ss = [], []
    for i in range(40):
        c, s = one(token=f"N{i:02d}", mult=1.0, pub_h=12 + i % 5)
        cs.append(c); ss.append(s)
    r = run(doc(cs, ss + pool((1.0,) * 8), sources={"s1": {"universe_count": 40, "universe_basis": "fixture"}}))
    sc = r["sources"]["s1"]["score"]
    assert r["sources"]["s1"]["horizons"]["86400"]["median_relative_return"] == 0.0
    assert sc["status"] == "SCORED" and sc["score"] == 50 and sc["tier"] == "PRELIMINARY"
    assert any("includes zero" in m for m in sc["not_validated_because"])


def test_noisy_sample_stays_preliminary_with_an_interval_that_spans_zero():
    """Calls and controls drawn from one wide distribution: some seeds show a lucky edge, many do not. When the interval spans zero the result
    must stay preliminary and score exactly 50 (no demonstrated edge), whatever the point estimate says."""
    spans, lucky = 0, 0
    for seed in range(12):
        rng = random.Random(seed)
        cs, ss = [], []
        for i in range(40):
            c, s = one(token=f"R{i:02d}", mult=round(rng.uniform(0.4, 2.2), 3), pub_h=12 + i % 5)
            cs.append(c); ss.append(s)
        base = [M.series(f"BK{i:02d}", M.flat_then(12, round(rng.uniform(0.4, 2.2), 3))) for i in range(40)]
        r = run(doc(cs, ss + base, sources={"s1": {"universe_count": 40, "universe_basis": "fixture"}}))
        sc, hz = r["sources"]["s1"]["score"], r["sources"]["s1"]["horizons"]["86400"]
        lo, hi = hz["median_relative_ci95"]
        if lo <= 0 <= hi:
            spans += 1
            assert sc["tier"] == "PRELIMINARY" and sc["score"] == 50
            assert any("cannot be told apart from no edge" in m for m in sc["not_validated_because"])
        else:
            lucky += 1
    assert spans >= 3 and spans + lucky == 12                                   # noise is common, and the engine does not call it skill


def test_zero_eligible_calls_decline_and_rank_nothing():
    r = A.analyze(doc([], [], sources={"s1": {"label": "empty"}}), POL)
    sc = r["sources"]["s1"]["score"]
    assert sc["status"] == "DECLINED" and sc["score"] is None and sc["tier"] == "UNVERIFIED" and "no eligible calls" in sc["reasons"]
    assert r["ranking"]["ranked"] == [] and "Declining is the correct output" in r["ranking"]["statement"]
    assert A.analyze(doc([], []), POL)["sources"] == {}
    n = M.call("n1", "s1", "X1", 12, direction="NEUTRAL")
    r = run(doc([n], [M.series("X1", M.flat_then(12, 2.0))] + pool()))
    assert r["sources"]["s1"]["score"]["status"] == "DECLINED" and r["sources"]["s1"]["counts"]["ineligible_by_reason"] == {"NO_DIRECTION": 1}
    assert "no eligible calls" in A.report(r) or "NO SCORE" in A.report(r)


def test_conflicting_bullish_and_bearish_statements_exclude_both():
    r = A.analyze(MAIN, {"horizons_s": [3600, 21600, 86400], "primary_horizon_s": 86400})
    assert by_id(r, "a16")["reasons"] == ["CONFLICTING_STATEMENTS"] and by_id(r, "a17")["reasons"] == ["CONFLICTING_STATEMENTS"]
    # the later statement does not rescue either one, and the order of arrival does not matter
    a, s = one(token="Z1", mult=1.6)
    b = M.call("z-short", "s1", "Z1", 12, direction="EXIT", offset=7200)
    for calls in ([a, b], [b, a]):
        rr = run(doc(calls, [s] + pool()))
        assert by_id(rr, a["call_id"])["reasons"] == ["CONFLICTING_STATEMENTS"] and by_id(rr, "z-short")["reasons"] == ["CONFLICTING_STATEMENTS"]
    late = M.call("z-late", "s1", "Z1", 12, direction="EXIT", offset=3 * 86400)
    rr = run(doc([a, late], [s] + pool(), as_of=T0 + 10 * 86400))
    assert all(not by_id(rr, i)["reasons"] or "CONFLICTING_STATEMENTS" not in by_id(rr, i)["reasons"] for i in (a["call_id"], "z-late"))
    other = M.call("z-other", "s2", "Z1", 12, direction="SHORT", offset=600)          # a different source does not conflict
    assert "CONFLICTING_STATEMENTS" not in by_id(run(doc([a, other], [s] + pool())), a["call_id"])["reasons"]


def test_other_ineligible_kinds_are_listed_with_reasons():
    r = A.analyze(MAIN, {"horizons_s": [3600, 21600, 86400], "primary_horizon_s": 86400})
    sa = r["sources"]["src_a"]["counts"]
    assert sa["ineligible_by_reason"] == {"CONDITIONAL_CLAIM": 1, "CONFLICTING_STATEMENTS": 2, "HINDSIGHT_CAPTURE_RISK": 1, "NOT_ORIGINAL": 1, "NO_DIRECTION": 1, "REPEAT_POST": 1}
    assert sa["unevaluable_by_reason"] == {"ILLIQUID_ENTRY": 1, "NO_PRICE_HISTORY": 1}
    assert sa["eligible_independent"] == 16 and sa["calls_supplied"] == 23
    c = M.call("u", "s1", "X1", 12, uncertainty="high")
    assert by_id(run(doc([c], [M.series("X1", M.flat_then(12, 2))] + pool())), "u")["reasons"] == ["HIGH_UNCERTAINTY_EXTRACTION"]
    c = M.call("sar", "s1", "X1", 12, sarcasm_suspected=True)
    assert by_id(run(doc([c], [M.series("X1", M.flat_then(12, 2))] + pool())), "sar")["reasons"] == ["SARCASM_SUSPECTED"]
    c = M.call("ns", "s1", "X1", 12); del c["item_key"]
    assert by_id(run(doc([c], [M.series("X1", M.flat_then(12, 2))] + pool())), "ns")["reasons"] == ["NO_SOURCE"]
    c = M.call("tu", "s1", "X1", 12); c["token"] = {}
    assert by_id(run(doc([c], [])), "tu")["reasons"] == ["TOKEN_UNRESOLVED"]
    c = M.call("fut", "s1", "X1", 12)
    assert by_id(run(doc([c], [M.series("X1", M.flat_then(12, 2))] + pool(), as_of=T0 + 11 * H)), "fut")["reasons"] == ["AFTER_AS_OF"]


def test_losing_and_flat_calls_are_in_the_sample():
    r = A.analyze(MAIN, {"horizons_s": [3600, 21600, 86400], "primary_horizon_s": 86400})
    nets = [prim(by_id(r, f"a{i:02d}"))["net"] for i in range(1, 13)]
    assert sum(1 for n in nets if n < 0) >= 4 and sum(1 for n in nets if n > 0) >= 4
    hz = r["sources"]["src_a"]["horizons"]["86400"]
    assert hz["n_evaluated"] == 14                                              # 12 ordinary + late promotion + delisted
    assert hz["false_positives"] == sum(1 for c in r["calls"] if c["source_id"] == "src_a" and c["status"] == "EVALUATED" and prim(c)["net"] <= 0)
    assert hz["fail_to_beat_baseline"] == hz["n_with_baseline"] - round(hz["beat_baseline_rate"] * hz["n_with_baseline"])


# ---------- temporal leakage ----------

def test_nothing_after_as_of_is_used():
    cut = T0 + 24 * H
    full = doc([M.call("L1", "s1", "X1", 12, direction="LONG")], [M.series("X1", M.flat_then(12, 1.5))] + pool(), as_of=cut)
    trunc = copy.deepcopy(full)
    for s in trunc["series"]:
        s["rows"] = [r for r in s["rows"] if r["t"] < cut]
    pol = {"horizons_s": [3600, 21600, 86400], "primary_horizon_s": 86400}
    a, b = A.analyze(full, pol), A.analyze(trunc, pol)
    assert A.sha(a["calls"]) == A.sha(b["calls"]) and a["sources"] == b["sources"]
    x = by_id(a, "L1")
    assert x["horizons"]["3600"]["status"] == "OK" and x["horizons"]["21600"]["status"] == "OK"
    assert prim(x) == {"horizon_s": 86400, "status": "NOT_EVALUABLE", "reason": "HORIZON_NOT_ELAPSED"}


def test_entry_and_matching_do_not_depend_on_later_candles():
    c, s = one(mult=1.5)
    base = run(doc([c], [s] + pool()))
    fut = copy.deepcopy([s] + pool())
    for ser in fut:
        for r in ser["rows"]:
            if r["t"] >= T0 + 14 * H:                                    # everything after the entry candles
                r["v"] = r["v"] * 1000
                r["h"], r["l"] = r["o"] * 2, r["o"] * 0.5
    after = run(doc([c], fut))
    assert by_id(base, c["call_id"])["entry"] == by_id(after, c["call_id"])["entry"]
    assert by_id(base, c["call_id"])["baseline_tokens"] == by_id(after, c["call_id"])["baseline_tokens"]
    # comparison tokens that only started trading after the call are not eligible controls, however well they match
    late = M.series("LATE", M.flat_then(12, 3.0))
    late["rows"] = [r for r in late["rows"] if r["t"] >= T0 + 20 * H]
    x = by_id(run(doc([c], [s] + pool() + [late])), c["call_id"])
    assert "LATE" not in x["baseline_tokens"]


def test_a_live_quote_replayed_as_history_is_rejected():
    c, s = one()
    s["as_of_kind"] = "OBSERVED_AT_FETCH"
    r = run(doc([c], [s] + pool()))
    assert r["series_rejected"] == [{"chain": "solana", "contract": "X1", "reason": "LIVE_QUOTE_REPLAY", "as_of_kind": "OBSERVED_AT_FETCH"}]
    x = by_id(r, c["call_id"])
    assert x["status"] == "UNEVALUABLE" and x["reasons"] == ["NO_PRICE_HISTORY"]
    for mutate, why in ((lambda q: q.pop("source"), "NO_SOURCE"), (lambda q: q["rows"][3].update(h=0.0001), "BAD_CANDLES"),
                        (lambda q: q["rows"][4].update(t=q["rows"][2]["t"]), "BAD_CANDLES"), (lambda q: q.update(delisted_at=T0 + 5 * H), "CANDLE_AFTER_DELISTING")):
        s2 = M.series("X2", M.flat_then(12, 2)); mutate(s2)
        assert run(doc([], [s2]))["series_rejected"][0]["reason"] == why
    dup = run(doc([], [M.series("X3", [(0, 1), (57, 1)]), M.series("X3", [(0, 2), (57, 2)])]))
    assert dup["series_rejected"][0]["reason"] == "DUPLICATE_SERIES" and not dup["series_used"]


# ---------- the score itself ----------

def test_three_great_calls_never_make_a_great_score():
    cs, ss = [], []
    for i in range(3):
        c, s = one(token=f"G{i}", mult=2.0, pub_h=12 + i)
        cs.append(c); ss.append(s)
    r = run(doc(cs, ss + pool()))
    sc = r["sources"]["s1"]["score"]
    assert sc["status"] == "DECLINED" and sc["score"] is None and "at least 10" in sc["reasons"][0]
    forced = run(doc(cs, ss + pool()), min_calls_preliminary=1)["sources"]["s1"]["score"]       # even if someone lowers the floor
    assert forced["shrinkage"]["weight"] == pytest.approx(3 / 23, abs=1e-9) and forced["score"] < 70


def test_score_grows_with_evidence_and_validated_needs_every_gate():
    def src(n, mult=1.4):
        cs, ss = [], []
        for i in range(n):
            c, s = one(token=f"V{i:02d}", mult=mult, pub_h=12 + i % 5)
            cs.append(c); ss.append(s)
        return run(doc(cs, ss + pool(), sources={"s1": {"universe_count": n, "universe_basis": "fixture"}}))["sources"]["s1"]["score"]
    s12, s40 = src(12), src(40)
    assert s12["tier"] == "PRELIMINARY" and s40["tier"] == "VALIDATED" and s40["score"] > s12["score"] and s40["score"] < 95
    assert "not_validated_because" not in s40 and s40["split_sample"]["n"] == [20, 20]
    assert any("30" in m for m in s12["not_validated_because"])
    # a bad split-sample: strong first half, weak second half
    cs, ss = [], []
    for i in range(40):
        c, s = one(token=f"S{i:02d}", mult=1.6 if i < 20 else 0.7, pub_h=12 + i % 5)
        c["published_at"] += (i // 5) * 600; c["first_observed_at"] += (i // 5) * 600
        cs.append(c); ss.append(s)
    r = run(doc(cs, ss + pool(), sources={"s1": {"universe_count": 40, "universe_basis": "fixture"}}))["sources"]["s1"]["score"]
    assert r["tier"] == "PRELIMINARY" and any("disagree" in m or "includes zero" in m for m in r["not_validated_because"])
    # unknown universe: cannot validate
    cs, ss = [], []
    for i in range(40):
        c, s = one(token=f"U{i:02d}", mult=1.4, pub_h=12 + i % 5)
        cs.append(c); ss.append(s)
    u = run(doc(cs, ss + pool()))["sources"]["s1"]["score"]
    assert u["tier"] == "PRELIMINARY" and any("enumerated" in m for m in u["not_validated_because"])
    # a single token repeated by many sources' worth of calls cannot validate either
    one_tok = [M.call(f"o{i}", "s1", "ONE", 12, offset=i * 8 * 86400) for i in range(40)]
    assert A.analyze(doc(one_tok, [M.series("ONE", M.flat_then(12, 1.4))] + pool(), as_of=T0 + 400 * 86400), POL)["sources"]["s1"]["score"]["status"] == "DECLINED"


def test_ranking_orders_validated_above_preliminary_and_lists_declines():
    cs, ss = [], []
    for sid, n in (("big", 40), ("mid", 12), ("few", 3)):
        for i in range(n):
            c, s = one(sid=sid, token=f"{sid}{i:02d}", mult=1.4, pub_h=12 + i % 5)
            cs.append(c); ss.append(s)
    r = run(doc(cs, ss + pool(), sources={"big": {"universe_count": 40, "universe_basis": "fixture"}}))
    assert [x["source_id"] for x in r["ranking"]["ranked"]] == ["big", "mid"]
    assert [x["tier"] for x in r["ranking"]["ranked"]] == ["VALIDATED", "PRELIMINARY"]
    assert [x["source_id"] for x in r["ranking"]["declined"]] == ["few"]


def test_confidence_interval_and_helpers():
    assert A.median_ci([1, 2, 3, 4, 5]) is None                       # n too small for 95%
    assert A.median_ci(list(range(1, 9))) == (1, 8)
    lo, hi = A.median_ci(list(range(1, 31)))
    assert lo < 15.5 < hi and lo > 1
    w = A.wilson(8, 10)
    assert 0.49 < w[0] < 0.50 and 0.94 < w[1] < 0.95 and A.wilson(0, 0) is None
    assert A.quantile([1, 2, 3, 4], 0.5) == 2.5 and A.quantile([], 0.5) is None
    hz = by_id(A.analyze(MAIN, POL), "a01")
    assert hz is not None


def test_horizons_reported_separately_and_primary_alone_scores():
    r = A.analyze(MAIN, {"horizons_s": [3600, 21600, 86400], "primary_horizon_s": 86400})
    hs = r["sources"]["src_a"]["horizons"]
    assert hs["86400"]["primary"] and not hs["3600"]["primary"] and not hs["21600"]["primary"]
    assert hs["3600"]["median_relative_return"] != hs["86400"]["median_relative_return"]
    r6 = A.analyze(MAIN, {"horizons_s": [3600, 21600, 86400], "primary_horizon_s": 21600})
    assert r6["sources"]["src_a"]["score"]["primary_horizon_s"] == 21600
    assert r["policy_sha256"] != r6["policy_sha256"] and r["input_sha256"] != r6["input_sha256"]
    full = A.analyze(MAIN)                                              # default horizons include 72 h and 7 d, which the fixture cannot reach
    assert full["sources"]["src_a"]["horizons"]["604800"]["n_evaluated"] == 0
    assert full["sources"]["src_a"]["horizons"]["604800"]["not_evaluable_by_reason"]


def test_lead_time_and_move_lag_are_reported():
    r = A.analyze(MAIN, {"horizons_s": [3600, 21600, 86400], "primary_horizon_s": 86400})
    lt = r["sources"]["src_a"]["lead_time"]
    assert lt["n_with_onset"] > 0 and lt["quantiles_s"]["p25"] <= lt["quantiles_s"]["median"] <= lt["quantiles_s"]["p75"]
    x = by_id(r, "a02")
    assert x["lead_time_s"] == 36000 and x["lead_time_status"] == "POSTED_BEFORE_ONSET"
    assert x["move_lag_s"] > 0 and x["liquidity"]["entry"] == 100000.0 and x["liquidity"]["exit_vs_entry"] == 1.0


def test_author_trades_are_context_only():
    r = A.analyze(MAIN, {"horizons_s": [3600, 21600, 86400], "primary_horizon_s": 86400})
    x = by_id(r, "a01")
    assert x["author_trades"]["flags"] == ["UNDISCLOSED_PRIOR_BUY"] and x["author_trades"]["used_in_score"] is False
    assert x["author_trades"]["assertions"] == ["CHAIN_EVIDENCE"] and x["author_trades"]["sources"] == ["fixture:wallet-event-1"]
    assert r["sources"]["src_a"]["flags"]["undisclosed_prior_buy"] == 1
    d2 = copy.deepcopy(MAIN)
    d2["author_trades"][0].update(usd=9e9, side="BUY")
    d3 = copy.deepcopy(MAIN); d3["author_trades"] = []
    pol = {"horizons_s": [3600, 21600, 86400], "primary_horizon_s": 86400}
    assert A.analyze(d2, pol)["sources"]["src_a"]["score"] == A.analyze(d3, pol)["sources"]["src_a"]["score"] == r["sources"]["src_a"]["score"]
    d4 = copy.deepcopy(MAIN)
    d4["author_trades"] = [{"source_id": "src_a", "chain": "solana", "contract": "TA02", "t": T0 + 14 * H, "side": "SELL", "usd": 10, "assertion": "SELF_CLAIMED", "source": "fixture:w2"}]
    assert "SOLD_AFTER_PROMOTING" in by_id(A.analyze(d4, pol), "a02")["flags"]


def test_popularity_and_wallet_profit_stay_out_of_the_formula():
    pol = {"horizons_s": [3600, 21600, 86400], "primary_horizon_s": 86400}
    a = A.analyze(MAIN, pol)
    d = copy.deepcopy(MAIN)
    d["sources"]["src_a"]["context"] = {"followers": 1, "engagement": 0}
    d["sources"]["src_c"]["context"] = {"followers": 10 ** 9, "views": 10 ** 12, "wallet_profit_usd": 10 ** 9}
    b = A.analyze(d, pol)
    for sid in ("src_a", "src_b", "src_c"):
        assert a["sources"][sid]["score"] == b["sources"][sid]["score"] and a["sources"][sid]["horizons"] == b["sources"][sid]["horizons"]
    assert a["separation"]["wallet_profits_in_formula"] is False and a["separation"]["source_popularity_in_formula"] is False
    src = (ROOT / "memelab" / "social" / "alpha_core.py").read_text()
    assert "followers\"" not in src and "engagement\"" not in src and "views\"" not in src


def test_deterministic_and_input_hash_changes_with_policy():
    a, b = A.analyze(MAIN, POL), A.analyze(MAIN, POL)
    assert a["result_sha256"] == b["result_sha256"] and a["input_sha256"] == b["input_sha256"]
    assert A.analyze(MAIN, dict(POL, delay_s=600))["input_sha256"] != a["input_sha256"]
    assert A.analyze(MAIN, dict(POL, delay_s=600))["calls"] != a["calls"]
    bad = copy.deepcopy(MAIN); bad["schema"] = "x"
    with pytest.raises(ValueError):
        A.evaluate(bad)
    bad = copy.deepcopy(MAIN); bad["calls"].append(copy.deepcopy(bad["calls"][0]))
    with pytest.raises(ValueError):
        A.evaluate(bad)
    nd = copy.deepcopy(MAIN); del nd["as_of"]
    with pytest.raises(ValueError):
        A.evaluate(nd)


def test_rules_are_written_down_and_versioned():
    r = A.analyze(MAIN, POL)
    assert r["engine_version"] == "information-alpha-v1" and r["rules_version"] == "alpha-rules-v1" and len(r["selection_rules"]) >= 8
    assert r["usable_as_evidence"] is False and r["is_fixture"] is True
    assert "INVENTED FIXTURE DATA" in A.report(r)
    for c in r["calls"]:
        assert c["reference"]                                           # every observation traces to a source reference
    assert all(s["source"] for s in r["series_used"])


# ---------- fixture file and the end-to-end demonstration ----------

def test_fixture_file_matches_its_generator():
    assert json.loads(json.dumps(M.build(), sort_keys=True)) == json.loads(json.dumps(MAIN, sort_keys=True))


def test_end_to_end_fixture_evaluation():
    r = A.analyze(MAIN, {"horizons_s": [3600, 21600, 86400], "primary_horizon_s": 86400})
    a, b, c = (r["sources"][k]["score"] for k in ("src_a", "src_b", "src_c"))
    assert a["status"] == "SCORED" and a["tier"] == "PRELIMINARY" and 40 <= a["score"] <= 65 and a["score"] == 50 and a["score_point"] == 53
    assert b["status"] == "DECLINED" and "3 independent" in b["reasons"][0]
    assert c["status"] == "DECLINED"
    assert [x["source_id"] for x in r["ranking"]["ranked"]] == ["src_a"] and {x["source_id"] for x in r["ranking"]["declined"]} == {"src_b", "src_c"}
    rep = A.report(r)
    assert "SCORE" in rep and "NO SCORE (declined)" in rep and "Source src_c" in rep


# ---------- storage, migration and CLI ----------

def _con(tmp_path, name="a.sqlite"):
    p = tmp_path / name
    db.init_db(p)
    con = sqlite3.connect(p)
    con.row_factory = sqlite3.Row
    return con, p


def test_migration_11_rolls_back_cleanly_and_leaves_phase_10_alone(tmp_path):
    con, _ = _con(tmp_path)
    assert schema.current_version(con) == schema.LATEST == 11
    before = {r[0]: r[1] for r in con.execute("SELECT name, sql FROM sqlite_master WHERE name LIKE 'social_perf_%'")}
    assert len(before) >= 5
    assert schema.rollback(con, 10) == [11]
    assert not con.execute("SELECT 1 FROM sqlite_master WHERE name LIKE 'social_alpha_%'").fetchall()
    assert {r[0]: r[1] for r in con.execute("SELECT name, sql FROM sqlite_master WHERE name LIKE 'social_perf_%'")} == before
    assert schema.migrate(con) == [11]
    cols = {r[1] for t in ("social_alpha_series", "social_alpha_candles", "social_alpha_runs", "social_alpha_scores")
            for r in con.execute(f"PRAGMA table_info({t})")}
    assert not any(w in c for c in cols for w in ("follower", "engagement", "profit", "pnl", "views"))
    perf_cols = {r[1] for r in con.execute("PRAGMA table_info(social_perf_runs)")}
    assert not any("alpha" in c for c in perf_cols)


def test_schema_refuses_live_quotes_and_scored_without_a_score(tmp_path):
    con, _ = _con(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO social_alpha_series(chain,contract,source,candle_seconds,as_of_kind,recorded_at) VALUES ('solana','X','s',60,'OBSERVED_AT_FETCH',1)")
    con.execute("INSERT INTO social_alpha_runs(engine_version,rules_version,as_of,policy_sha256,input_sha256,result_sha256,n_calls,n_sources_scored,input_json,result_json,created_at) VALUES ('e','r',1,'p','i','r',0,0,'{}','{}',1)")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO social_alpha_scores VALUES (1,'s','SCORED','UNVERIFIED',NULL,NULL,0,'[]')")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO social_alpha_scores VALUES (1,'s','DECLINED','UNVERIFIED',55,NULL,0,'[]')")
    con.execute("INSERT INTO social_alpha_scores VALUES (1,'s','DECLINED','UNVERIFIED',NULL,NULL,0,'[]')")


def test_series_round_trip_run_store_verify_and_tamper(tmp_path):
    con, _ = _con(tmp_path)
    assert S.put_series(con, MAIN["series"], fixture=True, now=5)["added"] == len(MAIN["series"])
    assert S.put_series(con, MAIN["series"][:3], fixture=True, now=6) == {"added": 0, "skipped_repeats": 3}
    live = copy.deepcopy(MAIN["series"][0]); live["as_of_kind"] = "OBSERVED_AT_FETCH"; live["source"] = "other"
    with pytest.raises(ValueError, match="LIVE_QUOTE_REPLAY"):
        S.put_series(con, [live])
    back = {s["contract"]: s for s in S.load_series(con)}
    orig = {s["contract"]: s for s in MAIN["series"]}
    assert back.keys() == orig.keys() and back["TA02"]["rows"] == orig["TA02"]["rows"]
    d = copy.deepcopy(MAIN)
    res = A.analyze(d, POL)
    saved = S.save_run(con, d, res, res["policy"], now=9)
    assert saved["created"] and S.save_run(con, d, res, res["policy"], now=10) == {"run_id": saved["run_id"], "created": False, "result_sha256": res["result_sha256"]}
    v = S.verify_run(con, saved["run_id"])
    assert v["verified"] and v["recomputation_matches"] and v["stored_result_matches_its_hash"]
    rows = {r["source_id"]: dict(r) for r in con.execute("SELECT * FROM social_alpha_scores WHERE run_id=?", (saved["run_id"],))}
    assert rows["src_a"]["status"] == "SCORED" and rows["src_c"]["status"] == "DECLINED" and rows["src_c"]["score"] is None
    # edit the stored result: verification must notice
    stored = json.loads(con.execute("SELECT result_json FROM social_alpha_runs").fetchone()[0])
    stored["sources"]["src_c"]["score"]["score"] = 99
    con.execute("UPDATE social_alpha_runs SET result_json=?", (A.canon(stored),))
    assert not S.verify_run(con, saved["run_id"])["verified"]
    assert S.status(con)["series"] == len(MAIN["series"])


def _claim_rows(con, *, item, account, token_ref, direction="LONG", published=1000.0, observed=1100.0, tokens=None, conditional=0, attribution="author", status="ok"):
    """Insert one item, one observation, one current extraction and one claim with attributes, the way Phase 06 leaves them."""
    store.register_analysis_version(con, "extract-v1", "claims", "fixture")
    ob = store.record_observation(con, platform="x", access_mode="fixture", collector="fixture", provider_item_id=item, account_id=account,
                                  published_at=published, observed_at=observed, content_hash="a" * 64, now=2000)
    cid = store.add_claim(con, claim_type="CALL", analysis_version="extract-v1", item_key=ob["item_key"], account_id=account, token_ref_id=token_ref,
                          direction=direction, observation_id=ob["id"], now=2000)["id"]
    con.execute("INSERT INTO social_claim_extractions(extraction_key,observation_id,item_key,content_hash,context_sha,extractor,extractor_version,analysis_version,status,mode,extracted_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)", (f"k{item}", ob["id"], ob["item_key"], "a" * 64, "c", "deterministic", "v1", "extract-v1", status, "none", 2000))
    eid = con.execute("SELECT MAX(extraction_id) FROM social_claim_extractions").fetchone()[0]
    con.execute("INSERT INTO social_claim_attributes(claim_id,extraction_id,claim_index,category,assertion_type,stance,negated,conditional,sarcasm_suspected,time_horizon,"
                "author_position,attribution,uncertainty,uncertainty_reasons_json,verification,narrative_tags_json,tokens_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, eid, 0, "bullish", "prediction", "positive", 0, conditional, 0, "days", "holds", attribution, "low", "[]", "unverified_text_claim", "[]",
                 json.dumps(tokens if tokens is not None else [])))
    return ob["item_key"], cid


def test_build_input_reads_current_claims_and_only_resolved_tokens(tmp_path):
    con, _ = _con(tmp_path)
    acct = store.upsert_account(con, "x", handle="invented_a", now=1)
    store.upsert_trader(con, "trader_a", "Invented A", now=1)
    store.link_trader_account(con, "trader_a", acct, "LAB_ASSERTED", evidence_status="INFERENCE", now=1)
    ref = store.upsert_token_ref(con, chain="solana", contract="MintAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", now=1)
    ref_id = ref["ref_id"] if isinstance(ref, dict) else ref
    cA = MAIN["calls"][0]
    good = [{"status": "resolved", "chain": "solana", "contract": "MintAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"}]
    _claim_rows(con, item="1", account=acct, token_ref=ref_id, tokens=good)
    _claim_rows(con, item="2", account=acct, token_ref=ref_id, tokens=[{"status": "ambiguous", "contract": "MintAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"}], direction="SHORT")
    _claim_rows(con, item="3", account=acct, token_ref=ref_id, tokens=good, attribution="reposted")
    con.commit()
    d = S.build_input(con, as_of=99999, annotations={"universe": {"trader_a": {"count": 7, "basis": "invented"}}})
    by = {c["item_key"]: c for c in d["calls"]}
    assert set(c["source_id"] for c in d["calls"]) == {"trader_a"} and d["sources"]["trader_a"]["universe_count"] == 7
    c1, c2, c3 = by["x:1"], by["x:2"], by["x:3"]
    assert c1["token"]["contract"].startswith("MintA") and c1["original"] is True and c1["published_at"] == 1000.0 and c1["first_observed_at"] == 1100.0
    assert c2["token"] == {} and c3["original"] is False
    r = A.analyze(d, None)
    assert {c["reasons"][0] for c in r["calls"] if c["reference"] in ("x:2", "x:3")} == {"TOKEN_UNRESOLVED", "NOT_ORIGINAL"}
    assert r["sources"]["trader_a"]["score"]["status"] == "DECLINED"
    # a superseded extraction is not read
    con.execute("UPDATE social_claim_extractions SET superseded_by=1 WHERE item_key='x:1'")
    assert "x:1" not in {c["item_key"] for c in S.build_input(con, as_of=99999)["calls"]}


def _cli(args, tmp_path, env_db=None):
    import os
    env = {k: v for k, v in os.environ.items() if k != "MEMELAB_DB"}
    return subprocess.run([sys.executable, "-m", "memelab", "social", "alpha"] + args, cwd=ROOT, capture_output=True, text=True, env=env)


def test_cli_demo_declines_and_never_writes_fixtures_to_the_tracked_database(tmp_path):
    inp = str(FX / "alpha_main.json")
    p = _cli(["run", "--input", inp, "--policy", json.dumps({"horizons_s": [3600, 21600, 86400]})], tmp_path)
    assert p.returncode == 0, p.stderr
    assert "INVENTED FIXTURE DATA" in p.stdout and "NO SCORE (declined)" in p.stdout and "SCORE 50 (PRELIMINARY)" in p.stdout
    dbp = str(tmp_path / "cli.sqlite")
    p = _cli(["run", "--input", inp, "--save", "--db", dbp, "--policy", json.dumps({"horizons_s": [3600, 21600, 86400]})], tmp_path)
    assert p.returncode == 0 and "Stored as run 1 (new)" in p.stdout, p.stderr
    p = _cli(["verify", "1", "--db", dbp], tmp_path)
    assert p.returncode == 0 and json.loads(p.stdout)["verified"] is True
    p = _cli(["rank", "--db", dbp], tmp_path)
    assert json.loads(p.stdout)["ranked"][0]["source_id"] == "src_a"
    p = _cli(["status", "--db", dbp], tmp_path)
    assert json.loads(p.stdout)["runs"][0]["is_fixture"] == 1
    p = _cli(["run", "--input", inp, "--save"], tmp_path)                                    # default database is the tracked one
    assert p.returncode == 1 and "never written to the tracked database" in p.stderr
    p = _cli(["series", "import", inp, "--fixture"], tmp_path)
    assert p.returncode == 1
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps(doc([], [], is_fixture=False)))
    p = _cli(["run", "--input", str(empty)], tmp_path)
    assert p.returncode == 0 and "Declining is the correct output" in p.stdout
    p = _cli(["rank", "--input", str(empty)], tmp_path)
    assert p.returncode == 0 and json.loads(p.stdout)["ranked"] == []
    bad = tmp_path / "bad.json"; bad.write_text("{}")
    assert _cli(["run", "--input", str(bad)], tmp_path).returncode == 1
