"""Phase 16: immutable signal ledger and forward evaluation. Fixed clock, temp ledgers, invented prices, no network."""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from memelab.social import outcomes_cli as OCLI
from memelab.social import outcomes_core as OC
from memelab.social import outcomes_ledger as OL

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "social" / "outcomes"
SPEC_PATH = "tests/fixtures/social/outcomes/outcomes_fixture.json"
G = 1791892800.0          # 2026-10-13T12:00:00Z, signal generation time
H = 3600.0
E = G + 300               # hypothetical entry (default execution lag)
CA = "B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY"
CB = "bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ"
POL = OC.make_policy({})


def sig(ref="s1", *, contract=CA, gen=G, event=G - H, disposition="EMITTED", market=None, **kw):
    return {"emitter": "test", "emitter_ref": ref, "disposition": disposition, "chain": "solana" if contract else None, "contract": contract,
            "symbol": "FXCAT", "event_time": event, "generated_at": gen, "classifier_version": "c1", "scoring_version": "s1",
            "references": {"claims": [1]}, "market": market if market is not None else
            [{"field": "price", "value_num": 1.0, "as_of": gen - 30, "provider": "jupiter"},
             {"field": "liquidity_reported", "value_num": 1e6, "as_of": gen - 30, "provider": "dexscreener"}], **kw}


def pt(t, price, *, contract=CA, liq=1e6, avail=None, sell=None, provider="fx", kind="POINT", **kw):
    o = {"kind": kind, "chain": "solana", "contract": contract, "t": t, "available_at": t + 30 if avail is None else avail, "provider": provider}
    if kind == "POINT":
        o["price"] = price
    if liq is not None:
        o["liquidity_usd"] = liq
    if sell is not None:
        o["sell_quote"] = sell
    o.update(kw)
    return o


def series(start, end, step, f, **kw):
    out, t = [], start
    while t <= end:
        out.append(pt(t, f(t), **kw))
        t += step
    return out


def ledger(tmp_path, name="l.sqlite"):
    return OL.connect(tmp_path / name)


def ctx_of(con, ref="s1"):
    return next(c for c in OL.signals(con) if c["emitter_ref"] == ref)


def latest(con, sid, h):
    return OL.latest_outcomes(con)[(sid, int(h))]


def snapshot(con):
    return [(r["seq"], r["kind"], r["entry_key"], r["body_json"], r["entry_sha256"]) for r in con.execute("SELECT * FROM ledger_entries ORDER BY seq")]


# ---------- look-ahead ----------

def test_lookahead_context_drops_later_facts_and_entry_is_never_before_the_signal(tmp_path):
    con = ledger(tmp_path)
    mk = [{"field": "price", "value_num": 1.0, "as_of": G - 30, "provider": "jupiter"},
          {"field": "price", "value_num": 9.0, "as_of": G + 60, "provider": "jupiter"},         # fetched after emission
          {"field": "liquidity_reported", "value_num": 1e6, "as_of": G - 30, "provider": "dexscreener"}]
    OL.record_signals(con, [sig(market=mk)], POL, now=G + 10)
    c = ctx_of(con)
    assert c["market_at_generation"]["observed_price"]["value"] == 1.0
    assert c["market_at_generation"]["facts_after_generation_excluded"] == 1
    # a big candle-like jump just before the entry must not become the entry; neither can a price later than the evaluation clock
    obs = [pt(G - 60, 0.5), pt(G + 200, 0.6)] + series(E, E + 2 * H, 300, lambda t: 1.0 + (t - E) / H * 0.1)
    obs.append(pt(E + H, 50.0, avail=E + 30 * H))      # a snapshot the lab only had much later
    OL.add_observations(con, obs, POL, now=G + 10)
    OL.evaluate_all(con, as_of=E + H + 1000, pol=POL, now=E + H + 1000)
    o = latest(con, c["signal_id"], H)
    assert o["status"] == "MEASURED"
    assert o["entry"]["t"] >= E and o["entry"]["price"] == 1.0
    assert o["exit"]["price"] == pytest.approx(1.1)
    assert all(s is not None for s in o["inputs"])
    # the same outcome replayed at the same time stays the same; a later clock sees the late snapshot as a revision
    again = [x for x in OL.compute(con, as_of=E + H + 1000, pol=POL) if x["signal_id"] == c["signal_id"] and x["horizon_s"] == H][0]
    assert OC.content_sha(again) == OC.content_sha({k: v for k, v in o.items() if k != "_seq"})


def test_evaluation_clock_cannot_run_ahead_or_backwards(tmp_path):
    con = ledger(tmp_path)
    OL.record_signals(con, [sig()], POL, now=G)
    OL.evaluate_all(con, as_of=G + 10 * H, pol=POL, now=G + 10 * H)
    with pytest.raises(OC.OutcomeError, match="before the latest evaluation"):
        OL.evaluate_all(con, as_of=G + 5 * H, pol=POL, now=G + 10 * H)
    r = subprocess.run([sys.executable, "-m", "memelab", "social", "evaluate", "run", "--ledger", str(tmp_path / "c.sqlite"),
                        "--as-of", "2026-10-14T00:00:00+00:00", "--now", "2026-10-13T00:00:00+00:00"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 2 and "future" in r.stderr


# ---------- provider revisions ----------

def test_revised_provider_snapshot_appends_a_revision_and_keeps_the_original(tmp_path):
    con = ledger(tmp_path)
    OL.record_signals(con, [sig()], POL, now=G)
    sid = ctx_of(con)["signal_id"]
    OL.add_observations(con, series(E, E + 2 * H, 300, lambda t: 1.0), POL, now=G + 3 * H)
    OL.evaluate_all(con, as_of=G + 3 * H, pol=POL, now=G + 3 * H)
    v1 = latest(con, sid, H)
    assert v1["returns"]["return_mid_gross"] == 0.0
    OL.add_observations(con, [pt(E + H, 1.2, avail=G + 5 * H)], POL, now=G + 5 * H)   # same series, revised later
    OL.evaluate_all(con, as_of=G + 6 * H, pol=POL, now=G + 6 * H)
    v2 = latest(con, sid, H)
    assert v2["returns"]["return_mid_gross"] == pytest.approx(0.2)
    assert v2["supersedes_seq"] == v1["_seq"] and v2["revision_reason"] == "INPUTS_REVISED"
    hist = [o for o in OL.outcome_history(con, sid) if o["horizon_s"] == H]
    assert [o["returns"]["return_mid_gross"] for o in hist] == [0.0, pytest.approx(0.2)]
    # replay before the revision was available still gives the original number
    old = [x for x in OL.compute(con, as_of=G + 3 * H, pol=POL) if x["horizon_s"] == H][0]
    assert old["returns"]["return_mid_gross"] == 0.0


# ---------- delayed publication ----------

def test_delayed_publication_is_measured_from_the_signal_not_the_event(tmp_path):
    con = ledger(tmp_path)
    OL.record_signals(con, [sig(event=G - 10 * H)], POL, now=G)
    c = ctx_of(con)
    assert c["times"]["publication_delay_s"] == 10 * H
    # the token ran from 1.0 to 3.0 between the post and the signal; that move is not credited to the signal
    obs = series(G - 10 * H, G, 1800, lambda t: 1.0 + 2.0 * (t - (G - 10 * H)) / (10 * H)) + series(E, E + 2 * H, 300, lambda t: 3.0)
    OL.add_observations(con, obs, POL, now=G + 3 * H)
    OL.evaluate_all(con, as_of=G + 3 * H, pol=POL, now=G + 3 * H)
    o = latest(con, c["signal_id"], H)
    assert o["entry"]["price"] == 3.0 and o["returns"]["return_mid_gross"] == 0.0


def test_late_capture_is_flagged_and_capture_before_generation_is_refused(tmp_path):
    con = ledger(tmp_path)
    r = OL.record_signals(con, [sig("late")], POL, now=G + 5 * H)
    assert r["appended"] and any(f["flag"] == "LATE_CAPTURE" for f in ctx_of(con, "late")["flags"])
    r = OL.record_signals(con, [sig("early", gen=G + 10 * H)], POL, now=G)
    assert r["refused"] and "generated after it was recorded" in r["refused"][0]["reason"]


def test_event_after_generation_invalidates_outcomes(tmp_path):
    con = ledger(tmp_path)
    OL.record_signals(con, [sig(event=G + H)], POL, now=G + 2 * H)
    OL.evaluate_all(con, as_of=G + 2 * H, pol=POL, now=G + 2 * H)
    o = latest(con, ctx_of(con)["signal_id"], H)
    assert o["status"] == "INVALIDATED" and o["reasons"][0]["code"] == "EVENT_AFTER_GENERATION"


# ---------- delisting, liquidity, route ----------

def test_delisted_token_is_non_executable_and_no_exit_is_invented(tmp_path):
    con = ledger(tmp_path)
    OL.record_signals(con, [sig()], POL, now=G)
    sid = ctx_of(con)["signal_id"]
    obs = series(E, E + 3 * H, 300, lambda t: 1.0 + (t - E) / H)
    obs.append({"kind": "STATUS", "chain": "solana", "contract": CA, "t": E + 3 * H + 60, "available_at": E + 3 * H + 120, "provider": "fx", "status": "DELISTED"})
    obs.append(pt(E + 6 * H, 99.0))          # a stray price after delisting is never used
    OL.add_observations(con, obs, POL, now=G + 8 * H)
    OL.evaluate_all(con, as_of=G + 8 * H, pol=POL, now=G + 8 * H)
    assert latest(con, sid, H)["status"] == "MEASURED"
    o = latest(con, sid, 6 * H)
    assert o["status"] == "NON_EXECUTABLE" and o["reasons"][0]["code"] == "TOKEN_DELISTED_BEFORE_EXIT"
    assert o["returns"] is None and o["exit"]["last_seen_price"] == pytest.approx(4.0)


def test_lost_liquidity_and_missing_sell_route_are_non_executable(tmp_path):
    con = ledger(tmp_path)
    OL.record_signals(con, [sig("a"), sig("b", contract=CB)], POL, now=G)
    obs = series(E, E + 2 * H, 300, lambda t: 1.0, liq=1e6)
    obs[-1]["liquidity_usd"] = 0.0                                                   # pool emptied by E+2h
    obs[12]["liquidity_usd"] = 2000.0                                                # at the 1h exit: 25% participation
    obs_b = series(E, E + 2 * H, 300, lambda t: 1.0, contract=CB, liq=1e6)
    obs_b[12]["sell_quote"] = {"status": "NO_ROUTE", "size_usd": 500}
    OL.add_observations(con, obs + obs_b, POL, now=G + 3 * H)
    OL.evaluate_all(con, as_of=G + 3 * H, pol=POL, now=G + 3 * H)
    oa = latest(con, ctx_of(con, "a")["signal_id"], H)
    ob = latest(con, ctx_of(con, "b")["signal_id"], H)
    assert oa["status"] == "NON_EXECUTABLE" and [r["code"] for r in oa["reasons"]] == ["EXIT_LIQUIDITY_LOST"]
    assert ob["status"] == "NON_EXECUTABLE" and [r["code"] for r in ob["reasons"]] == ["NO_SELL_ROUTE"]
    # the displayed move is still shown, labeled as display, never as proceeds
    assert oa["returns"]["return_mid_gross"] == 0.0 and "not proceeds" in oa["returns"]["notes"][0]


# ---------- midpoints and quotes ----------

def test_missing_midpoint_is_missing_and_a_route_quote_never_stands_in(tmp_path):
    con = ledger(tmp_path)
    OL.record_signals(con, [sig()], POL, now=G)
    sid = ctx_of(con)["signal_id"]
    obs = series(E, E + 50 * 60, 300, lambda t: 1.0)
    obs += [{"kind": "QUOTE", "chain": "solana", "contract": CA, "t": E + H + k * 300, "available_at": E + H + k * 300 + 10, "provider": "q",
             "sell_quote": {"status": "OK", "size_usd": 500, "out_usd": 700}} for k in range(3)]
    obs.append(pt(E + H + 60, None))       # a point with no midpoint
    OL.add_observations(con, obs, POL, now=G + 3 * H)
    OL.evaluate_all(con, as_of=G + 3 * H, pol=POL, now=G + 3 * H)
    o = latest(con, sid, H)
    assert o["status"] == "MISSING" and o["reasons"][0]["code"] == "MISSING_MIDPOINT_AT_EXIT" and o["returns"] is None


def test_price_quote_mismatch(tmp_path):
    con = ledger(tmp_path)
    OL.record_signals(con, [sig("low"), sig("high", contract=CB)], POL, now=G)
    a = series(E, E + 2 * H, 300, lambda t: 1.0)
    a[12]["sell_quote"] = {"status": "OK", "size_usd": 500, "out_usd": 250}          # route returns half the displayed value
    b = series(E, E + 2 * H, 300, lambda t: 1.0, contract=CB)
    b[12]["sell_quote"] = {"status": "OK", "size_usd": 500, "out_usd": 600}          # pays more than the displayed price: inconsistent
    OL.add_observations(con, a + b, POL, now=G + 3 * H)
    OL.evaluate_all(con, as_of=G + 3 * H, pol=POL, now=G + 3 * H)
    lo = latest(con, ctx_of(con, "low")["signal_id"], H)
    hi = latest(con, ctx_of(con, "high")["signal_id"], H)
    assert lo["status"] == "NON_EXECUTABLE" and lo["reasons"][0]["code"] == "PRICE_QUOTE_MISMATCH"
    assert lo["returns"]["return_net_quoted"] < -0.5 < lo["returns"]["return_net_modeled"]
    assert hi["status"] == "MEASURED" and hi["returns"]["return_net_quoted"] is None
    assert any(f["flag"] == "PRICE_QUOTE_MISMATCH" for f in hi["flags"])


def test_route_quote_and_modeled_impact_are_kept_apart(tmp_path):
    con = ledger(tmp_path)
    OL.record_signals(con, [sig()], POL, now=G)
    a = series(E, E + 2 * H, 300, lambda t: 1.0 + (t - E) / H * 0.1, liq=1e5)
    a[12]["sell_quote"] = {"status": "OK", "size_usd": 550, "out_usd": 539}
    OL.add_observations(con, a, POL, now=G + 3 * H)
    OL.evaluate_all(con, as_of=G + 3 * H, pol=POL, now=G + 3 * H)
    r = latest(con, ctx_of(con)["signal_id"], H)["returns"]
    assert r["entry_cost_basis"] == "MODELED_IMPACT"
    assert r["exit_cost_quoted"] == pytest.approx(0.02 + 0.01) and r["exit_cost_modeled"] == pytest.approx(0.015 + 2 * 550 / 1e5)
    assert r["return_mid_gross"] > r["return_net_quoted"] and r["return_net_quoted"] != r["return_net_modeled"]


def test_max_excursion_needs_a_granular_path(tmp_path):
    con = ledger(tmp_path)
    OL.record_signals(con, [sig("fine"), sig("sparse", contract=CB)], POL, now=G)
    fine = series(E, E + 2 * H, 300, lambda t: 1.0 + (0.5 if t == E + 1800 else 0.0))
    sparse = [pt(E, 1.0, contract=CB), pt(E + 1800, 1.5, contract=CB), pt(E + H, 1.0, contract=CB)]
    OL.add_observations(con, fine + sparse, POL, now=G + 3 * H)
    OL.evaluate_all(con, as_of=G + 3 * H, pol=POL, now=G + 3 * H)
    f = latest(con, ctx_of(con, "fine")["signal_id"], H)["excursion"]
    s = latest(con, ctx_of(con, "sparse")["signal_id"], H)["excursion"]
    assert f["status"] == "OK" and f["mfe_mid"] == pytest.approx(0.5)
    assert s["status"] == "INSUFFICIENT_PATH" and "mfe_mid" not in s


# ---------- repetition, resumption, deletion, windows ----------

def test_duplicate_evaluation_appends_nothing(tmp_path):
    con = ledger(tmp_path)
    OL.record_signals(con, [sig()], POL, now=G)
    OL.add_observations(con, series(E, E + 2 * H, 300, lambda t: 1.0), POL, now=G + 3 * H)
    s1 = OL.evaluate_all(con, as_of=G + 3 * H, pol=POL, now=G + 3 * H)
    snap = snapshot(con)
    s2 = OL.evaluate_all(con, as_of=G + 3 * H, pol=POL, now=G + 3 * H)
    s3 = OL.evaluate_all(con, as_of=G + 4 * H, pol=POL, now=G + 4 * H)      # later clock, nothing new
    assert s1["appended"] == 5 and s2["appended"] == 0 and s3["appended"] == 0 and snapshot(con) == snap
    assert OL.add_observations(con, series(E, E + 2 * H, 300, lambda t: 1.0), POL, now=G + 5 * H)["duplicate"] == 25
    assert OL.record_signals(con, [sig()], POL, now=G + 9 * H)["already_recorded"]
    assert snapshot(con) == snap


def test_deterministic_resumption_after_a_crash(tmp_path):
    def build(name):
        con = ledger(tmp_path, name)
        OL.record_signals(con, [sig("a"), sig("b", contract=CB, disposition="REJECTED")], POL, now=G)
        OL.add_observations(con, series(E, E + 26 * H, 1800, lambda t: 1.0) + series(E, E + 26 * H, 1800, lambda t: 2.0, contract=CB), POL, now=G + 30 * H)
        return con
    ref = build("ref.sqlite")
    OL.evaluate_all(ref, as_of=G + 30 * H, pol=POL, now=G + 30 * H)
    con = build("crash.sqlite")
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 7:
            raise RuntimeError("simulated crash")
        return OC.evaluate(*a, **k)
    with pytest.raises(RuntimeError):
        OL.evaluate_all(con, as_of=G + 30 * H, pol=POL, now=G + 30 * H, evaluator=flaky)
    assert con.execute("SELECT COUNT(*) FROM ledger_entries WHERE kind='OUTCOME'").fetchone()[0] == 6
    OL.evaluate_all(con, as_of=G + 30 * H, pol=POL, now=G + 30 * H)
    assert snapshot(con) == snapshot(ref)
    assert OL.verify(con)["ok"]


def test_source_deletion_keeps_the_signal_and_its_outcomes(tmp_path):
    con = ledger(tmp_path)
    OL.record_signals(con, [sig()], POL, now=G)
    sid = ctx_of(con)["signal_id"]
    before = con.execute("SELECT body_json FROM ledger_entries WHERE kind='SIGNAL'").fetchone()[0]
    OL.add_observations(con, series(E, E + 2 * H, 300, lambda t: 1.0), POL, now=G + 3 * H)
    OL.annotate(con, sid, "SOURCE_DELETED", reason="post removed by its author", at=G + 2 * H, available_at=G + 2 * H, now=G + 2 * H)
    OL.evaluate_all(con, as_of=G + 3 * H, pol=POL, now=G + 3 * H)
    o = latest(con, sid, H)
    assert o["status"] == "MEASURED" and any(f["flag"] == "SOURCE_DELETED" for f in o["flags"])
    assert con.execute("SELECT body_json FROM ledger_entries WHERE kind='SIGNAL'").fetchone()[0] == before
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        con.execute("DELETE FROM ledger_entries WHERE kind='SIGNAL'")
    # invalidation is also an annotation, appended later; the earlier measured entry stays
    OL.annotate(con, sid, "IDENTITY_REVISED", reason="contract was a lookalike", at=G + 4 * H, available_at=G + 4 * H, now=G + 4 * H)
    OL.evaluate_all(con, as_of=G + 4 * H, pol=POL, now=G + 4 * H)
    hist = [x["status"] for x in OL.outcome_history(con, sid) if x["horizon_s"] == H]
    assert hist == ["MEASURED", "INVALIDATED"]


def test_postponed_windows_pending_then_missing_and_a_late_run_uses_the_target_time_price(tmp_path):
    con = ledger(tmp_path)
    OL.record_signals(con, [sig("gap"), sig("late", contract=CB)], POL, now=G)
    gap = series(E, E + 50 * 60, 300, lambda t: 1.0)                               # nothing at or after the 1h exit yet
    late = series(E, E + 30 * H, 300, lambda t: 1.0 + (t - E) / H, contract=CB)    # keeps rising long after the 1h exit
    OL.add_observations(con, gap + late, POL, now=G + 31 * H)
    OL.evaluate_all(con, as_of=E + H + 100, pol=POL, now=E + H + 100)
    sg = ctx_of(con, "gap")["signal_id"]
    assert latest(con, sg, H)["status"] == "PENDING" and latest(con, sg, H)["reasons"][0]["code"] == "EXIT_WINDOW_OPEN"
    OL.evaluate_all(con, as_of=G + 31 * H, pol=POL, now=G + 31 * H)              # run postponed by more than a day
    assert latest(con, sg, H)["status"] == "MISSING" and latest(con, sg, H)["reasons"][0]["code"] == "NO_EXIT_PRICE"
    lo = latest(con, ctx_of(con, "late")["signal_id"], H)
    assert lo["exit"]["t"] == E + H and lo["returns"]["return_mid_gross"] == pytest.approx(1.0)


def test_no_outcomes_matured(tmp_path):
    con = ledger(tmp_path)
    OL.record_signals(con, [sig("a"), sig("b", contract=CB, disposition="SUPPRESSED")], POL, now=G)
    s = OL.evaluate_all(con, as_of=G + 1800, pol=POL, now=G + 1800)
    assert s["by_status"]["PENDING"] == 10 and s["appended"] == 10
    cov = OL.report(con, POL)
    assert all(v["coverage_rate"] is None and v["matured"] == 0 for v in cov["horizons"].values())
    assert "n/a (none matured)" in OC.render_report(cov)


# ---------- no cherry-picking, immutability ----------

def test_rejected_and_suppressed_signals_are_kept_and_a_changed_context_is_refused(tmp_path):
    con = ledger(tmp_path)
    r = OL.record_signals(con, [sig("a"), sig("b", contract=CB, disposition="REJECTED"), sig("c", contract=None, disposition="SUPPRESSED")],
                          POL, now=G)
    assert len(r["appended"]) == 3
    with pytest.raises(OC.OutcomeError, match="immutable"):
        ctx = OC.make_signal(sig("a", market=[{"field": "price", "value_num": 7.0, "as_of": G - 1, "provider": "jupiter"}]), POL, captured_at=G)
        OL.record_signal(con, ctx, now=G)
    OL.evaluate_all(con, as_of=G + 8 * 24 * H, pol=POL, now=G + 8 * 24 * H)
    cov = OL.report(con, POL)
    assert cov["dispositions"] == {"EMITTED": 1, "REJECTED": 1, "SUPPRESSED": 1, "NEEDS_REVIEW": 0}
    assert cov["horizons"]["1h"]["exclusions"]["MISSING"] == {"NO_ENTRY_PRICE": 2, "UNRESOLVED_IDENTITY": 1}
    assert sum(cov["horizons"]["7d"]["counts"].values()) == 3


def test_ledger_is_append_only_and_verify_detects_tampering(tmp_path):
    con = ledger(tmp_path)
    OL.record_signals(con, [sig()], POL, now=G)
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        con.execute("UPDATE ledger_entries SET body_json='{}'")
    assert OL.verify(con)["ok"]
    con.execute("DROP TRIGGER ledger_no_update")                  # someone bypasses the guard
    con.execute("UPDATE ledger_entries SET body_json=replace(body_json, '\"EMITTED\"', '\"REJECTED\"')")
    v = OL.verify(con)
    assert not v["ok"] and any("hash" in p["problem"] for p in v["problems"])


def test_ledger_never_uses_the_tracked_database():
    from memelab import db
    with pytest.raises(OC.OutcomeError, match="tracked"):
        OL.connect(db.DB_PATH)


def test_observation_validation(tmp_path):
    with pytest.raises(OC.OutcomeError, match="future-dated"):
        OC.normalize_observation(pt(G + H, 1.0, avail=G), POL)
    with pytest.raises(OC.OutcomeError, match="not a finished candle"):
        OC.normalize_observation({"kind": "CANDLE", "chain": "solana", "contract": CA, "t": G, "available_at": G + 60, "period_s": 3600,
                                  "provider": "gt", "o": 1, "h": 1, "l": 1, "c": 1}, POL)
    with pytest.raises(OC.OutcomeError, match="refused"):
        OC.make_policy({"execute_orders": True})


def test_candles_give_open_at_start_and_close_at_end(tmp_path):
    con = ledger(tmp_path)
    OL.record_signals(con, [sig()], POL, now=G)
    candles = [{"kind": "CANDLE", "chain": "solana", "contract": CA, "t": G + k * 300, "period_s": 300, "available_at": G + (k + 1) * 300 + 5,
                "provider": "gt", "o": 1.0 + k * 0.01, "h": 1.0 + k * 0.01 + 0.015, "l": 1.0 + k * 0.01 - 0.005, "c": 1.0 + (k + 1) * 0.01,
                "liquidity_usd": 1e6} for k in range(30)]
    OL.add_observations(con, candles, POL, now=G + 3 * H)
    OL.evaluate_all(con, as_of=G + 3 * H, pol=POL, now=G + 3 * H)
    o = latest(con, ctx_of(con)["signal_id"], H)
    assert o["entry"]["basis"] == "CANDLE_CLOSE" or o["entry"]["basis"] == "CANDLE_OPEN"
    assert o["entry"]["t"] >= E and o["entry"]["price"] == pytest.approx(1.01)
    assert o["excursion"]["status"] == "OK"


# ---------- adapters ----------

def test_signals_from_the_phase_15_feed_fixture(tmp_path):
    from memelab.social import alerts_cli as ACLI, feed_core as FC
    feed = ACLI._feed_from_fixture("tests/fixtures/social/alerts/alerts_day.json", None, "UTC")
    raws = OC.signals_from_feed(feed)
    assert len(raws) == len(feed["items"]) and all(r["generated_at"] == feed["as_of"] for r in raws)
    con = ledger(tmp_path)
    r = OL.record_signals(con, raws, POL, now=feed["as_of"] + 60, is_fixture=True)
    assert len(r["appended"]) == len(raws) and not r["refused"]
    themes = [c for c in OL.signals(con) if c["token"]["contract"] is None]
    assert all(any(m["field"] == "identity" for m in c["missing"]) for c in themes)
    assert all(c["is_fixture"] for c in OL.signals(con))


def test_research_adapter_keeps_rejections():
    sec = {"as_of": G, "engine_version": "research-v1", "policy": {"policy_version": "default-1"}, "result_sha256": "x",
           "candidates": [{"chain": "solana", "contract": CA, "symbol": "A", "research_state": "REJECTED_STRUCTURE", "timeline_evidence": []},
                          {"chain": "solana", "contract": CB, "symbol": "B", "research_state": "RESEARCH_CANDIDATE",
                           "timeline_evidence": [{"at": G - 50}]}]}
    raws = OC.signals_from_research(sec)
    assert [r["disposition"] for r in raws] == ["REJECTED", "EMITTED"] and raws[1]["event_time"] == G - 50


def test_market_facts_import(tmp_path):
    p = tmp_path / "lab.sqlite"
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE social_market_facts (fact_id INTEGER PRIMARY KEY, chain TEXT, contract TEXT, field TEXT, value_num REAL, value_str TEXT,"
              " pair_id TEXT, size_usd REAL, provider TEXT, as_of REAL, as_of_kind TEXT, fetched_at REAL, valid_from REAL, valid_until REAL)")
    rows = [("price", 1.0, None, None, None, "jupiter", G, "OBSERVED_AT_FETCH", G, G, G + 120),
            ("liquidity_reported", 5e5, None, "P1", None, "dexscreener", G, "OBSERVED_AT_FETCH", G, G, G + 300),
            ("sell_quote_out", None, "NO_ROUTE", None, 500, "jupiter.quote_v1", G, "OBSERVED_AT_FETCH", G, G, G + 120)]
    rows += [(f"price_candle_{n}", v, None, "P1", None, "geckoterminal", G - 3600, "HISTORICAL_CANDLE", G, G - 3600, G)
             for n, v in (("open", 0.9), ("high", 1.1), ("low", 0.8), ("close", 1.0))]
    c.executemany("INSERT INTO social_market_facts(field,value_num,value_str,pair_id,size_usd,provider,as_of,as_of_kind,fetched_at,valid_from,valid_until,chain,contract)"
                  " VALUES (?,?,?,?,?,?,?,?,?,?,?,'solana',?)", [r + (CA,) for r in rows])
    c.commit(); c.close()
    obs = OCLI.facts_to_observations(str(p))
    kinds = sorted(o["kind"] for o in obs)
    assert kinds == ["CANDLE", "POINT", "QUOTE", "QUOTE"]
    cd = next(o for o in obs if o["kind"] == "CANDLE")
    assert (cd["o"], cd["h"], cd["l"], cd["c"], cd["period_s"]) == (0.9, 1.1, 0.8, 1.0, 3600)
    out = OL.add_observations(ledger(tmp_path), obs, POL, now=G)
    assert out["appended"] == 4 and not out["refused"]


# ---------- fixture demo: before / after with zero mutation ----------

def test_fixture_signal_snapshot_before_and_after_two_evaluations(tmp_path):
    spec = json.loads((FIX / "outcomes_fixture.json").read_text())
    con = ledger(tmp_path)
    OL.record_signals(con, spec["signals"]["signals"], POL, now=spec["recorded_at"], is_fixture=True)
    before = [(r[0], r[1], r[2]) for r in con.execute("SELECT seq, body_json, entry_sha256 FROM ledger_entries WHERE kind='SIGNAL' ORDER BY seq")]
    statuses = []
    for ev in spec["evaluations"]:
        OL.add_observations(con, ev["observations"], POL, now=ev["now"])
        OL.evaluate_all(con, as_of=ev["as_of"], pol=POL, now=ev["now"])
        statuses.append({(k[0], k[1]): v["status"] for k, v in OL.latest_outcomes(con).items()})
    after = [(r[0], r[1], r[2]) for r in con.execute("SELECT seq, body_json, entry_sha256 FROM ledger_entries WHERE kind='SIGNAL' ORDER BY seq")]
    assert before == after and len(after) == 5
    assert OL.verify(con)["ok"]
    good = ctx_of(con, "contract:solana:" + CA)["signal_id"]
    assert statuses[0][(good, 86400)] == "PENDING" and statuses[1][(good, 86400)] == "MEASURED"
    assert [o["revision_reason"] for o in OL.outcome_history(con, good) if o["horizon_s"] == 3600] == [None, "INPUTS_REVISED"]


def test_fixture_is_reproducible_and_sample_matches_byte_for_byte():
    import importlib.util
    spec = importlib.util.spec_from_file_location("make_outcomes", FIX / "make_outcomes.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert json.dumps(m.build(), indent=1, sort_keys=True) + "\n" == (FIX / "outcomes_fixture.json").read_text()
    r = subprocess.run([sys.executable, "-m", "memelab", "social", "evaluate", "demo", "--fixture", SPEC_PATH], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout == (FIX / "sample_run.md").read_text()
    assert "Original context unchanged, byte for byte, for all 5 signals: yes." in r.stdout
    assert "UPDATE refused by the ledger" in r.stdout and "hash chain and body hashes OK" in r.stdout


def test_cli_end_to_end_on_an_empty_and_a_filled_ledger(tmp_path):
    led = str(tmp_path / "cli.sqlite")
    env = {**os.environ, "MEMELAB_SIGNAL_LEDGER": led}

    def run(*args):
        return subprocess.run([sys.executable, "-m", "memelab", "social", "evaluate", *args], cwd=ROOT, env=env, capture_output=True, text=True)
    r = run("run", "--as-of", "2026-10-13T12:00:00+00:00", "--now", "2026-10-13T12:00:00+00:00")
    assert r.returncode == 0 and "no signals recorded" in r.stdout
    r = run("report")
    assert r.returncode == 0 and "No signals recorded" in r.stdout
    spec = json.loads((FIX / "outcomes_fixture.json").read_text())
    (tmp_path / "sig.json").write_text(json.dumps(spec["signals"]))
    (tmp_path / "p1.json").write_text(json.dumps({"schema": OC.PRICES_SCHEMA, "observations": spec["evaluations"][0]["observations"]}))
    assert run("record", "--signals", str(tmp_path / "sig.json"), "--now", str(spec["recorded_at"])).returncode == 0
    assert run("observe", "--prices", str(tmp_path / "p1.json"), "--now", str(spec["evaluations"][0]["now"])).returncode == 0
    r = run("run", "--as-of", str(spec["evaluations"][0]["as_of"]), "--now", str(spec["evaluations"][0]["now"]))
    assert r.returncode == 0 and "appended: 25" in r.stdout
    sid = json.loads(run("record", "--signals", str(tmp_path / "sig.json"), "--now", str(spec["recorded_at"] + 99)).stdout)["already_recorded"][0]
    r = run("annotate", "--signal", sid, "--kind", "SOURCE_DELETED", "--reason", "removed", "--now", str(spec["evaluations"][0]["now"] + 1))
    assert r.returncode == 0
    r = run("show", "--signal", sid)
    assert r.returncode == 0 and "Original context (immutable)" in r.stdout
    r = run("show", "--signal", sid, "--as-of", str(spec["evaluations"][0]["as_of"]))
    assert r.returncode == 0 and "Replay" in r.stdout
    r = run("report")
    assert r.returncode == 0 and "Reasons for exclusion" in r.stdout
    assert run("verify").returncode == 0
