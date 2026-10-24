"""Phase 15: post-discovery outcomes, calibration, drift (G06, G08, G32 and missing-outcome regressions).

Synthetic tokens are written through the real store functions; G06 uses the committed real GeckoTerminal responses
for a token that collapsed (3GVSN8)."""
import json
import sqlite3
from pathlib import Path

import pytest

from memelab.backtest import outcomes as O, store
from memelab.backtest.sources import captures, gecko

T0 = 1_792_000_800.0          # 2026-10-14 12:00 UTC, on the hour
H = 3600.0
M1 = "Fq1aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaapump"
M2 = "Fq2aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaapump"
M3 = "Fq3aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaapump"
M4 = "Fq4aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaapump"
FIX = Path(__file__).parent / "fixtures" / "backtest" / "real"


@pytest.fixture
def con(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RAW_DIR", tmp_path / "raw")
    c = store.connect(tmp_path / "bt.sqlite")
    yield c
    c.close()


def pool(con, mint, created=T0 - 10 * 86400):
    p = "P" + mint[1:]
    store.record_pool_version(con, chain="solana", pool_address=p, mint=mint, pool_type="CPMM", observed_at=created + 60, source="test",
                              dex="pumpswap", pool_created_at=created, available_at=created + 60)
    return p


def bars(con, mint, p, start, n, price=1.0, step=0.0, observed_late=False, lows=None):
    for i in range(n):
        s = start + i * H
        o = price * (1 + step) ** i
        c = price * (1 + step) ** (i + 1)
        lo = (lows or {}).get(i, min(o, c) * 0.99)
        store.record_bar(con, chain="solana", mint=mint, pool_address=p, tf=3600, start=s, o=o, h=max(o, c) * 1.01, l=lo, c=c, volume_usd=1000.0,
                         observed_at=(T0 + 30 * 86400) if observed_late else s + H + 600, provider="test")
    con.commit()


def thesis(con, mint, t=T0, status="WATCH", score=70, liq=300_000.0, price=1.0, basis="THESIS"):
    store.record_universe_member(con, universe_id="lab_state_history", chain="solana", mint=mint, symbol=mint[:3], basis=basis, entered_at=t,
                                 status_at_entry=status if basis == "THESIS" else None, score_at_entry=score,
                                 snapshot={"liquidity": liq, "price": price} if liq else None, stage="deep")
    con.commit()


def opp(con, mint):
    return next(o for o in O.opportunities(con) if o["mint"] == mint)


# ---------------------------------------------------------------- windows, point in time, determinism

def test_outcome_window_is_point_in_time(con):
    p = pool(con, M1)
    bars(con, M1, p, T0 - 48 * H, 48, price=1.0)
    bars(con, M1, p, T0, 24, price=1.0, step=0.01)
    store.record_bar(con, chain="solana", mint=M1, pool_address=p, tf=3600, start=T0 + 24 * H, o=1.27, h=50.0, l=0.01, c=40.0, volume_usd=1.0,
                     observed_at=T0 + 26 * H, provider="test")                        # after the 24 h window: never part of it
    thesis(con, M1)
    o = opp(con, M1)
    assert O.outcome_for(con, o, 24 * 3600, T0 + 24 * H)["state"] == "PENDING"       # closed but not yet published
    out = O.outcome_for(con, o, 24 * 3600, T0 + 30 * H)
    assert out["state"] == "COMPLETE" and out["realized"]["bars"] == 24
    assert abs(out["realized"]["ret_close"] - (1.01 ** 24 - 1)) < 1e-9 and out["realized"]["max_runup"] < 0.3 and not out["realized"]["down_50"]


def test_delayed_backfill_is_deterministic_and_supersedes(con, tmp_path):
    p = pool(con, M1)
    bars(con, M1, p, T0 - 24 * H, 24)
    thesis(con, M1)
    o = opp(con, M1)
    asof = T0 + 30 * H
    first = O.outcome_for(con, o, 24 * 3600, asof)
    assert first["state"] == "CENSORED" and first["missing_reason"].startswith("NO_BARS_IN_WINDOW")
    id1, _ = O.record(con, o, 24 * 3600, first, asof)
    bars(con, M1, p, T0, 24, step=-0.01, observed_late=True)                          # the window's bars arrive late (backfill)
    again = O.outcome_for(con, o, 24 * 3600, asof)
    assert again["state"] == "COMPLETE"                                                # public at the time, so observable at that asof
    id2, ins = O.record(con, o, 24 * 3600, again, asof)
    assert ins and con.execute("SELECT supersedes_id FROM bt_outcomes WHERE id=?", (id2,)).fetchone()[0] == id1
    assert O.record(con, o, 24 * 3600, O.outcome_for(con, o, 24 * 3600, asof), asof)[1] is False            # rerun adds nothing
    assert con.execute("SELECT COUNT(*) FROM bt_outcomes").fetchone()[0] == 2                                # the old row stays
    c2 = store.connect(tmp_path / "fresh.sqlite")                                       # same data loaded in one go
    p2 = pool(c2, M1); bars(c2, M1, p2, T0 - 24 * H, 24); bars(c2, M1, p2, T0, 24, step=-0.01); thesis(c2, M1)
    fresh = O.outcome_for(c2, opp(c2, M1), 24 * 3600, asof)
    assert O._body_hash(fresh["state"], fresh["realized"], fresh["missing_reason"]) == O._body_hash(again["state"], again["realized"], again["missing_reason"])
    c2.close()


def test_provider_revision_is_a_new_row_and_never_reaches_an_earlier_asof(con):
    p = pool(con, M1)
    bars(con, M1, p, T0 - 24 * H, 24)
    bars(con, M1, p, T0, 24, step=0.01)
    thesis(con, M1)
    o = opp(con, M1)
    a1 = T0 + 30 * H
    id1, _ = O.record(con, o, 24 * 3600, O.outcome_for(con, o, 24 * 3600, a1), a1)
    store.record_bar(con, chain="solana", mint=M1, pool_address=p, tf=3600, start=T0 + 23 * H, o=1.25, h=1.26, l=0.2, c=0.3, volume_usd=1.0,
                     observed_at=T0 + 40 * H, provider="test")                         # revised last bar, published later
    con.commit()
    assert O.outcome_for(con, o, 24 * 3600, a1)["realized"]["ret_close"] > 0          # an asof before the revision never sees it
    a2 = T0 + 41 * H
    rev = O.outcome_for(con, o, 24 * 3600, a2)
    assert rev["realized"]["revisions_used"] == 1 and rev["realized"]["down_50"]
    id2, ins = O.record(con, o, 24 * 3600, rev, a2)
    assert ins and con.execute("SELECT supersedes_id FROM bt_outcomes WHERE id=?", (id2,)).fetchone()[0] == id1
    assert O.latest(con, a1)[(o["opportunity_id"], 24 * 3600)]["id"] == id1 and O.latest(con)[(o["opportunity_id"], 24 * 3600)]["id"] == id2


# ---------------------------------------------------------------- missing outcomes are recorded, never dropped

def test_missing_outcomes_are_recorded_with_reasons(con):
    pa = pool(con, M1); bars(con, M1, pa, T0 - 24 * H, 24); bars(con, M1, pa, T0, 3, step=-0.3)   # stops trading 3 h in
    pb = pool(con, M2); bars(con, M2, pb, T0 - 24 * H, 24)                                         # no bars after the decision
    thesis(con, M1); thesis(con, M2); thesis(con, M3)                                              # M3: never fetched
    pd = pool(con, M4, created=T0 + 5 * 86400); bars(con, M4, pd, T0 + 5 * 86400, 5)               # pool appears days later
    thesis(con, M4)
    thesis(con, M2, t=T0 - 2 * H, liq=None, basis="REJECTION")                                   # screened out earlier: still in the study
    res = O.track(con, now=T0 + 8 * 86400)
    assert res["status"] == "RAN" and res["opportunities"] == 5
    assert {o["source"] for o in O.opportunities(con)} == {"LAB_THESIS", "LAB_REJECTION"}
    lat = O.latest(con)
    st = {o["mint"]: lat[(o["opportunity_id"], 24 * 3600)] for o in O.opportunities(con) if o["source"] == "LAB_THESIS"}
    assert st[M1]["state"] == "CENSORED" and st[M1]["missing_reason"].startswith("BARS_END_EARLY") and st[M1]["realized"]["down_50"]
    assert st[M2]["state"] == "CENSORED" and st[M2]["missing_reason"].startswith("NO_BARS_IN_WINDOW")
    assert st[M3]["state"] == "NOT_OBSERVABLE" and st[M3]["missing_reason"].startswith("NO_BARS_STORED")
    assert st[M4]["state"] == "NOT_OBSERVABLE" and st[M4]["missing_reason"].startswith("NO_POOL_BASIS")
    cal = O.calibrate(con, horizon_s=24 * 3600)
    o = cal["overall"]
    assert o["n"] == 5 and o["censored"] == 3 and o["not_observable"] == 2 and o["complete"] == 0
    assert o["share_down_50_observed"] == 0.5 and o["n_observed"] == 2                 # only windows with price bars count; censored ones as lower bounds
    assert cal["selection_bias_risk"] and o["verdict"] == "INSUFFICIENT_SAMPLE"


def test_g06_collapsed_token_stays_in_the_study_real_fixture(con):
    man = json.loads((FIX / "MANIFEST.json").read_text())
    mint = man["mint"]

    def replay(url, timeout=30.0):
        for f, m in man["files"].items():
            if m["url"] == url:
                return 200, (FIX / f).read_bytes()
        return 404, b""
    b = gecko.Budget(max_calls=10, min_spacing_s=0.0)
    gecko.fetch_pools(con, mint, b, replay, observed_at=man["files"]["gt_pools_3GVSN8.json"]["observed_at"])
    gecko.fetch_ohlcv(con, mint, "7AvDaHLbHW6qaMGuHQGpebbbGaV7fRTdFq5T5Vd4vdoH", b, replay, observed_at=man["files"]["gt_ohlcv_3GVSN8.json"]["observed_at"])
    con.commit()
    t = 1791446400.0 + 2 * H + 1                                           # 2026-10-08 09:00 UTC, while it was still rising
    thesis(con, mint, t=t, status="SETUP DEVELOPING", liq=50_000.0, price=0.027)
    O.track(con, now=man["files"]["gt_ohlcv_3GVSN8.json"]["observed_at"])
    lat = O.latest(con)
    o = opp(con, mint)
    day, three = lat[(o["opportunity_id"], 24 * 3600)], lat[(o["opportunity_id"], 72 * 3600)]
    assert day["state"] in ("COMPLETE", "CENSORED") and day["realized"]["down_50"]
    assert three["state"] in ("COMPLETE", "CENSORED") and three["realized"]["max_drawdown"] < -0.99
    cal = O.calibrate(con)
    assert cal["segments"]["cohort"]["LAB_THESIS:SETUP DEVELOPING"]["n"] == 1        # the dead token counts; nothing filters survivors


# ---------------------------------------------------------------- G08: as-known-at segments

def test_g08_late_edits_never_reach_earlier_decisions(con):
    p = pool(con, M1); bars(con, M1, p, T0 - 24 * H, 24); bars(con, M1, p, T0, 30)
    thesis(con, M1)
    o = opp(con, M1)
    captures.record_capture(con, collector="FIRECRAWL", source_url="https://solana.com/news/late", text="late claim", captured_at=T0 + 2 * H,
                            source_published_at=T0 - 6 * H, published_confidence="META", chain="solana", mint=M1, mint_verified=True, record_type="ARTICLE")
    con.commit()
    assert O.catalyst_known_at(con, o) == ("NONE", "NO_CATALYST")          # published "earlier", captured later: unknown at the decision
    before = O.outcome_for(con, o, 24 * 3600, T0 + 30 * H)
    captures.record_capture(con, collector="FIRECRAWL", source_url="https://solana.com/news/early", text="early claim", captured_at=T0 - 3 * H,
                            source_published_at=T0 - 4 * H, published_confidence="META", chain="solana", mint=M1, mint_verified=True, record_type="ARTICLE")
    captures.record_capture(con, collector="FIRECRAWL", source_url="https://solana.com/news/early", text="post removed", captured_at=T0 + 5 * H,
                            chain="solana", mint=M1, mint_verified=True, record_type="ARTICLE", claim_state="DELETED")
    con.commit()
    assert O.catalyst_known_at(con, o) == ("ARTICLE", "VERIFIED_LATE_CAPTURE")   # known then; a later deletion does not erase it
    late_cat = [{"mint": M1, "chain": "solana", "available_at": T0 + 3600, "published_at": T0 - 9 * H, "claim_type": "GRADUATION", "mint_verified": True}]
    assert O.catalyst_known_at(con, o, late_cat)[0] == "ARTICLE"
    thesis(con, M2)
    late2 = [dict(late_cat[0], mint=M2)]                                       # the lab saw it an hour after the decision
    assert O.catalyst_known_at(con, opp(con, M2), late2) == ("NONE", "NO_CATALYST")
    assert O.catalyst_known_at(con, opp(con, M2), [dict(late2[0], available_at=T0 - 60)])[0] == "GRADUATION"
    assert O.outcome_for(con, o, 24 * 3600, T0 + 30 * H) == before            # catalysts never change an outcome


# ---------------------------------------------------------------- G32: replay and byte-identical daily report

def test_g32_daily_report_replays_byte_identical(con):
    for m, sc, step in ((M1, 80, 0.01), (M2, 60, -0.02), (M3, 70, 0.0)):
        p = pool(con, m); bars(con, m, p, T0 - 24 * H, 24); bars(con, m, p, T0, 26, step=step)
        thesis(con, m, t=T0 + 5, score=sc)
    day = "2026-10-14"
    a = T0 + 30 * H
    O.track(con, now=a, observed_asof=a)
    r1 = O.daily_report(con, day, a)
    assert r1.index("Fq1") < r1.index("Fq3") < r1.index("Fq2")               # ranked by the lab score at decision
    p1 = "P" + M1[1:]
    store.record_bar(con, chain="solana", mint=M1, pool_address=p1, tf=3600, start=T0 + 20 * H, o=1.2, h=1.2, l=0.1, c=0.1, volume_usd=1.0,
                     observed_at=T0 + 50 * H, provider="test")                 # a revision published after the first report
    O.track(con, now=T0 + 52 * H, observed_asof=T0 + 52 * H)
    assert O.daily_report(con, day, a) == r1                                   # same asof: byte for byte
    r2 = O.daily_report(con, day, T0 + 52 * H)
    assert r2 != r1
    dec = lambda txt: [ln.split(" | ")[:3] for ln in txt.splitlines() if ln[:2] in ("1.", "2.", "3.")]
    assert dec(r1) == dec(r2)                                                  # decision columns never change, only outcomes


# ---------------------------------------------------------------- prior signed runs and assessments are immutable

def test_future_outcomes_cannot_change_prior_signed_runs(con):
    p = pool(con, M1); bars(con, M1, p, T0 - 24 * H, 24); bars(con, M1, p, T0, 30)
    thesis(con, M1)
    rid = store.register_run(con, {"strategy_id": "X", "params": {}}, dataset_hash="d")
    store.record_result(con, rid, "COMPLETE", {"n_trades": 1, "mean_ret": 0.1})
    store._insert(con, "bt_assessments", dict(request_key="k", chain="solana", mint=M1, snapshot_hash="s", engine_version="e", as_of=T0, stage="FAST",
                  tier="SCENARIO_ONLY", state="PARTIAL_WITH_LIMITATIONS", result_json={"lab": {"status": "WATCH"}}, result_hash="h", created_at=T0))
    con.commit()
    snap = lambda: [tuple(r) for r in con.execute("SELECT run_id, result_hash, result_json FROM bt_run_results")] + \
        [tuple(r) for r in con.execute("SELECT request_key, result_hash, result_json FROM bt_assessments")] + \
        [tuple(r) for r in con.execute("SELECT id, content_hash, status_at_entry, snapshot_json FROM bt_universe_members")]
    before = snap()
    O.track(con, now=T0 + 80 * H)
    bars(con, M1, p, T0 + 30 * H, 60, step=0.05)                                # much later, very different data
    O.track(con, now=T0 + 200 * H)
    O.calibrate(con); O.drift(con, now=T0 + 200 * H)
    assert snap() == before
    for sql in ("UPDATE bt_run_results SET result_hash='x'", "UPDATE bt_assessments SET state='COMPLETE'", "UPDATE bt_outcomes SET state='COMPLETE'",
                "DELETE FROM bt_outcomes"):
        with pytest.raises(sqlite3.DatabaseError):
            con.execute(sql)
    assert any(o["source"] == "ASSESSMENT" for o in O.opportunities(con))     # stored assessments are tracked too


# ---------------------------------------------------------------- scheduling: rate limit, dedup, exponential retry

def test_tracker_rate_limit_dedup_and_exponential_retry(con):
    p = pool(con, M2); bars(con, M2, p, T0 - 24 * H, 24)
    thesis(con, M2)
    calls = []

    def failing_fetch(chain, mint, pool_address):
        calls.append(mint)
        raise TimeoutError("provider down")
    now = T0 + 80 * H
    r1 = O.track(con, now=now, fetch=failing_fetch, retry_base_s=600)
    assert r1["status"] == "RAN" and r1["fetched"] == 1 and calls == [M2]
    assert O.track(con, now=now + 60, fetch=failing_fetch)["status"] == "SKIPPED_MIN_INTERVAL"
    n_rows = con.execute("SELECT COUNT(*) FROM bt_outcomes").fetchone()[0]
    r2 = O.track(con, now=now + 3700, fetch=failing_fetch, retry_base_s=6000)   # 1 failure: wait 6000 s
    assert r2["fetched"] == 0 and r2["deferred_fetches"] == 1 and r2["new_rows"] == 0
    assert con.execute("SELECT COUNT(*) FROM bt_outcomes").fetchone()[0] == n_rows
    r3 = O.track(con, now=now + 7400, fetch=failing_fetch, retry_base_s=6000)
    assert r3["fetched"] == 1 and len(calls) == 2
    r4 = O.track(con, now=now + 7400 + 8000, fetch=failing_fetch, retry_base_s=6000)   # 2 failures: wait 12000 s, not 6000
    assert r4["fetched"] == 0 and r4["deferred_fetches"] == 1
    r5 = O.track(con, now=now + 7400 + 12100, fetch=failing_fetch, retry_base_s=6000)
    assert r5["fetched"] == 1 and len(calls) == 3


# ---------------------------------------------------------------- calibration, reconciliation, drift, re-evaluation

def test_calibration_segments_and_sample_disclosure(con):
    p = pool(con, M1, created=T0 - 3 * H); bars(con, M1, p, T0 - 3 * H, 3); bars(con, M1, p, T0, 30, step=-0.03)
    thesis(con, M1, liq=40_000.0)
    p2 = pool(con, M2); bars(con, M2, p2, T0 - 24 * H, 24); bars(con, M2, p2, T0, 30)
    thesis(con, M2, status="REJECTED", liq=2_000_000.0)
    O.track(con, now=T0 + 80 * H)
    cal = O.calibrate(con)
    seg = cal["segments"]
    assert set(seg) == {"cohort", "token_age", "liquidity_band", "market_regime", "catalyst_type", "source_credibility"}
    assert seg["token_age"]["<6h"]["n"] == 1 and seg["token_age"][">=7d"]["n"] == 1
    assert seg["liquidity_band"]["<50k"]["n"] == 1 and seg["liquidity_band"][">=1M"]["n"] == 1
    assert all(v["verdict"] == "INSUFFICIENT_SAMPLE" for d in seg.values() for v in d.values())
    assert "not causes" in cal["note"]
    md = O.render_calibration(cal)
    assert "INSUFFICIENT_SAMPLE" in md and "censored" in md


def test_exit_reconciliation_uses_the_labs_later_snapshot(con):
    p = pool(con, M1); bars(con, M1, p, T0 - 24 * H, 24); bars(con, M1, p, T0, 30)
    thesis(con, M1, liq=100_000.0, price=1.0)
    thesis(con, M1, t=T0 + 24 * H + 600, status="SETUP DEVELOPING", liq=50_000.0, price=1.21)   # the lab's own later observation
    thesis(con, M2, liq=100_000.0)
    O.track(con, now=T0 + 80 * H)
    rec = O.exit_reconciliation(con)
    row = next(r for r in rec["rows"] if r["mint"] == M1 and r["liq_predicted"] == pytest.approx(110_000.0))
    assert row["liq_observed"] == 50_000.0 and row["liq_error"] == pytest.approx(50_000 / 110_000 - 1)
    assert row["by_size"]["5000"]["impact_observed"] > row["by_size"]["5000"]["impact_predicted"]
    assert rec["not_observable"] >= 1 and rec["basis"].startswith("LAB_SNAPSHOT") and rec["verdict"] == "INSUFFICIENT_SAMPLE"


def test_drift_warnings_and_deferred_reevaluation(con, monkeypatch):
    monkeypatch.setattr(O, "MIN_SEGMENT", 2)
    for i in range(8):                                                       # 8 decision days; the last 3 lose their bars
        m = f"Fd{i}aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaapump"
        t = T0 + i * 86400
        p = pool(con, m)
        bars(con, m, p, t - 24 * H, 24)
        if i < 5:
            bars(con, m, p, t, 30, step=(-0.05 if i >= 3 else 0.01))
        thesis(con, m, t=t)
        for j in range(2):
            mm = f"Fe{i}{j}aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaapump"
            pp = pool(con, mm); bars(con, mm, pp, t - 24 * H, 24)
            if i < 5:
                bars(con, mm, pp, t, 30, step=(-0.05 if i >= 3 else 0.01))
            thesis(con, mm, t=t)
    O.track(con, now=T0 + 12 * 86400)
    d = O.drift(con, now=T0 + 12 * 86400)
    kinds = {w["kind"] for w in d["warnings"]}
    assert "PROVIDER_COVERAGE_DRIFT" in kinds and "CALIBRATION_DRIFT" in kinds
    stale_con_pending = O.drift(con, now=T0 + 12 * 86400)["warnings"]
    assert all(w["kind"] != "STALE_PENDING" for w in stale_con_pending)
    from memelab.backtest.strategies import registry
    before = registry.make("LAB_STATUS").params
    prop = O.propose_reevaluation(con, "LAB_STATUS", O.deviations(d), now=T0 + 12 * 86400)
    assert prop["status"] == "PROPOSED" and any("pre-registration" in x for x in prop["requires"]) and prop["findings"]
    assert registry.make("LAB_STATUS").params == before
    with pytest.raises(PermissionError):
        O.retune_in_place("LAB_STATUS", {"min_score": 50})
    assert con.execute("SELECT COUNT(*) FROM bt_assessment_events WHERE event='REEVALUATION_PROPOSED'").fetchone()[0] == 1


def test_stale_pending_warning(con):
    p = pool(con, M1); bars(con, M1, p, T0 - 24 * H, 24)
    thesis(con, M1)
    o = opp(con, M1)
    O.record(con, o, 24 * 3600, O.outcome_for(con, o, 24 * 3600, T0 + H), T0 + H)        # pending when last tracked
    w = O.drift(con, now=T0 + 72 * H)["warnings"]
    assert any(x["kind"] == "STALE_PENDING" for x in w)


def test_shadow_saves_nothing_and_collector_health(con):
    n = con.execute("SELECT COUNT(*) FROM bt_experiment_runs").fetchone()[0]
    s = O.shadow(con, "NO_TRADE", since=T0)
    assert s["mode"].startswith("SHADOW") and con.execute("SELECT COUNT(*) FROM bt_experiment_runs").fetchone()[0] == n
    h = O.collector_health(con)
    assert h["maxun"].startswith("NOT_ADOPTED") and "NO_DATA" in h["note"]
    for i, (pub, cap) in enumerate(((T0 - 30 * H, T0), (T0 - H, T0 + H), (T0 - H, T0 + 2 * H))):
        captures.record_capture(con, collector="FIRECRAWL", source_url=f"https://solana.com/news/x{min(i, 1)}", text=f"claim {min(i, 1)}", captured_at=cap,
                                source_published_at=pub, chain="solana", mint=M1, mint_verified=True, record_type="ARTICLE", run_status="OK")
    con.commit()
    h = O.collector_health(con)["collectors"]["FIRECRAWL"]
    assert h["captures"] >= 2 and h["late_arrival_share"] > 0 and "MAXUN" not in O.collector_health(con)["collectors"]


# ---------------------------------------------------------------- G02: pools that disagree (Phase 16, N3)

def _two_pools(con, mint, side_vol, side_step, main_step=0.0, main_vol=2000.0):
    pm, ps = "M" + mint[1:], "S" + mint[1:]
    for p_ in (pm, ps):
        store.record_pool_version(con, chain="solana", pool_address=p_, mint=mint, pool_type="CPMM", observed_at=T0 - 3 * 86400, source="test",
                                  dex="pumpswap", pool_created_at=T0 - 3 * 86400 - 60, available_at=T0 - 3 * 86400)
    for i in range(-24, 30):
        k = max(0, i)
        for p_, v, step in ((pm, main_vol, main_step), (ps, side_vol, side_step)):
            o, c = (1 + step) ** k, (1 + step) ** (k + 1) if i >= 0 else 1.0
            store.record_bar(con, chain="solana", mint=mint, pool_address=p_, tf=3600, start=T0 + i * H, o=o, h=max(o, c), l=min(o, c), c=c, volume_usd=v,
                             observed_at=T0 + (i + 1) * H + 600, provider="test")
    con.commit()
    thesis(con, mint)
    return pm, ps


def test_pools_that_disagree_are_not_measured_and_thin_prints_are_ignored(con):
    _two_pools(con, M1, side_vol=1500.0, side_step=-0.08)                 # a second pool drifting 90% away hour after hour: ambiguous
    _two_pools(con, M2, side_vol=20.0, side_step=-0.08)                   # same with 1% of the volume: volume does not settle it (wash can be either side)
    _two_pools(con, M3, side_vol=20.0, side_step=0.0, main_step=-0.15)    # main pool falls hour after hour while a side pool keeps printing flat
    asof = T0 + 40 * H
    st = {m: O.outcome_for(con, opp(con, m), 24 * 3600, asof) for m in (M1, M2, M3)}
    assert all(st[m]["state"] == "NOT_OBSERVABLE" and st[m]["missing_reason"].startswith("POOL_DISAGREEMENT") for m in (M1, M2, M3))
    # a lone print off the market (one hour) and a side pool that last traded before a crash inside the crash hour (N7): measured
    pm, ps = "M" + M4[1:], "S" + M4[1:]
    for p_ in (pm, ps):
        store.record_pool_version(con, chain="solana", pool_address=p_, mint=M4, pool_type="CPMM", observed_at=T0 - 3 * 86400, source="test",
                                  dex="pumpswap", pool_created_at=T0 - 3 * 86400 - 60, available_at=T0 - 3 * 86400)
    for i in range(-24, 30):
        o, c = (1.0, 1.0) if i < 3 else ((1.0, 0.01) if i == 3 else (0.01, 0.01))
        store.record_bar(con, chain="solana", mint=M4, pool_address=pm, tf=3600, start=T0 + i * H, o=o, h=max(o, c), l=min(o, c), c=c,
                         volume_usd=(20000.0 if i == 3 else 1000.0), observed_at=T0 + (i + 1) * H + 600, provider="test")
        if i <= 3:
            sc = 0.98 if i == 3 else 1.0                                   # crash-hour close from a trade before the crash
            store.record_bar(con, chain="solana", mint=M4, pool_address=ps, tf=3600, start=T0 + i * H, o=1.0, h=1.0, l=sc, c=sc, volume_usd=50.0,
                             observed_at=T0 + (i + 1) * H + 600, provider="test")
    con.commit()
    thesis(con, M4)
    rug = O.outcome_for(con, opp(con, M4), 24 * 3600, asof)
    assert rug["state"] == "COMPLETE" and rug["realized"]["down_50"] and rug["realized"]["pool"] == pm
    from memelab.backtest import stress as S
    c = S.empirical_cohort(con, "WATCH", min_n=1, asof=asof)
    assert c["pool_disagreement_removed"] == 3 and c["n"] == 1 and c["selection_bias_risk"] is True
    # one lone off-market print among 24 shared hours does not void a window
    m5 = "Fq5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaapump"
    pm5, ps5 = "M" + m5[1:], "S" + m5[1:]
    for p_ in (pm5, ps5):
        store.record_pool_version(con, chain="solana", pool_address=p_, mint=m5, pool_type="CPMM", observed_at=T0 - 3 * 86400, source="test",
                                  dex="pumpswap", pool_created_at=T0 - 3 * 86400 - 60, available_at=T0 - 3 * 86400)
    for i in range(-24, 30):
        for p_, v, c_ in ((pm5, 2000.0, 1.0), (ps5, 100.0, 0.4 if i == 10 else 1.0)):
            store.record_bar(con, chain="solana", mint=m5, pool_address=p_, tf=3600, start=T0 + i * H, o=1.0, h=1.0, l=c_, c=c_, volume_usd=v,
                             observed_at=T0 + (i + 1) * H + 600, provider="test")
    con.commit()
    thesis(con, m5)
    assert O.outcome_for(con, opp(con, m5), 24 * 3600, asof)["state"] == "COMPLETE"


def test_cohort_keeps_feeds_that_died_and_flags_unmeasured_tokens(con):
    from memelab.backtest import stress as S
    for k in range(4):
        m = f"Fk{k}aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaapump"
        p = pool(con, m); bars(con, m, p, T0 - 24 * H, 24)
        bars(con, m, p, T0, 24 if k < 2 else 3, step=(0.0 if k < 2 else -0.8))   # two survive, two rug and stop trading
        thesis(con, m)
    for k in range(3):
        thesis(con, f"Fn{k}aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaapump")         # never fetched
    c = S.empirical_cohort(con, "WATCH", min_n=4, asof=T0 + 40 * H)
    assert c["n"] == 4 and c["n_complete"] == 2 and c["ret_p10_p50_p90"][0] < -0.9          # rugs stay in the return percentiles
    assert c["selection_bias_risk"] is True and c["unmeasured_share"] == pytest.approx(3 / 7, abs=1e-4)
    assert c["ret_complete_only_p10_p50_p90"][0] > -0.1 and c["point_in_time"] is True


def test_a_few_guard_removals_raise_the_bias_flag_even_under_twenty_percent(con):
    from memelab.backtest import stress as S
    for k in range(9):
        m = f"Fg{k}aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaapump"
        p = pool(con, m); bars(con, m, p, T0 - 24 * H, 24); bars(con, m, p, T0, 30)
        thesis(con, m)
    _two_pools(con, M1, side_vol=1500.0, side_step=-0.08)                 # 1 of 10 refused by the guard
    c = S.empirical_cohort(con, "WATCH", min_n=1, asof=T0 + 40 * H)
    assert c["pool_disagreement_removed"] == 1 and c["unmeasured_share"] == pytest.approx(0.1) and c["selection_bias_risk"] is True


def test_in_memory_cohorts_are_never_cached():
    """Phase 16 C3: an in-memory database has no stable identity (a reused id() could alias another one)."""
    from memelab.backtest import stress as S
    S._COHORT_CACHE.clear()
    c = store.connect(":memory:")
    thesis(c, M1)
    S.empirical_cohort(c, "WATCH", asof=T0 + 40 * H)
    assert S._COHORT_CACHE == {}
    c.close()


def test_one_off_market_hour_out_of_two_shared_is_not_enough_to_refuse(con):
    """A side pool sharing only two hours, one of them the crash hour it closed before the crash: measured (N7 edge)."""
    pm, ps = "M" + M1[1:], "S" + M1[1:]
    for p_ in (pm, ps):
        store.record_pool_version(con, chain="solana", pool_address=p_, mint=M1, pool_type="CPMM", observed_at=T0 - 3 * 86400, source="test",
                                  dex="pumpswap", pool_created_at=T0 - 3 * 86400 - 60, available_at=T0 - 3 * 86400)
    for i in range(-24, 30):
        o, c = (1.0, 1.0) if i < 3 else ((1.0, 0.01) if i == 3 else (0.01, 0.01))
        store.record_bar(con, chain="solana", mint=M1, pool_address=pm, tf=3600, start=T0 + i * H, o=o, h=max(o, c), l=min(o, c), c=c, volume_usd=1000.0,
                         observed_at=T0 + (i + 1) * H + 600, provider="test")
        if i in (2, 3):
            store.record_bar(con, chain="solana", mint=M1, pool_address=ps, tf=3600, start=T0 + i * H, o=1.0, h=1.0, l=0.98, c=0.98 if i == 3 else 1.0,
                             volume_usd=50.0, observed_at=T0 + (i + 1) * H + 600, provider="test")
    con.commit()
    thesis(con, M1)
    out = O.outcome_for(con, opp(con, M1), 24 * 3600, T0 + 40 * H)
    assert out["state"] == "COMPLETE" and out["realized"]["down_50"]


def test_report_cohort_line_states_the_bias_flag_and_the_split():
    from memelab.backtest import report
    coh = {"tier": "HISTORICAL_COHORT", "status": "WATCH", "n": 45, "n_complete": 30, "min_n": 30, "known_tokens": 60, "horizon_h": 24,
           "ret_p10_p50_p90": [-0.8, 0.0, 0.0], "worst_drop_p10_p50": [-0.8, -0.01], "ret_complete_only_p10_p50_p90": [0.0, 0.0, 0.0],
           "selection_bias_risk": True, "unmeasured_share": 0.25, "pool_disagreement_removed": 0, "point_in_time": True}
    a = {"chain": "solana", "mint": "X", "as_of": T0, "state": "PARTIAL_WITH_LIMITATIONS", "tier": "HISTORICAL_COHORT",
         "stress": {"historical_evidence": coh, "decision": "INCONCLUSIVE"}}
    md = report.render_md(report.build(a, lab={"score": 60, "status": "WATCH", "fatal_flags": []}, shared={}))
    line = next(x for x in md.splitlines() if x.startswith("Cohort of past tokens"))
    assert "45 measured windows (30 complete, 15 cut short" in line and "Selection-bias risk: YES (25% of measurable tokens could not be measured" in line
    md2 = report.render_md(report.build(dict(a, stress={"historical_evidence": dict(coh, point_in_time=False), "decision": "INCONCLUSIVE"}),
                                        lab={"score": 60, "status": "WATCH", "fatal_flags": []}, shared={}))
    assert "NOT point-in-time" in md2 and "NOT point-in-time" not in md
    assert "Complete windows only" in line


def test_cohort_cache_follows_a_replaced_database_file(tmp_path):
    """Phase 16 C4: a different file at the same path (same row ids, different prices) is never served the old cohort."""
    import os
    from memelab.backtest import stress as S

    def build(path, step):
        c = store.connect(path)
        for k in range(3):
            m = f"Fr{k}aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaapump"
            p = pool(c, m); bars(c, m, p, T0 - 24 * H, 24); bars(c, m, p, T0, 24, step=step)
            thesis(c, m)
        c.commit(); c.close()
    S._COHORT_CACHE.clear()
    a, b = tmp_path / "a.sqlite", tmp_path / "b.sqlite"
    build(a, 0.0)
    c1 = store.connect(a)
    first = S.empirical_cohort(c1, "WATCH", min_n=1, asof=T0 + 40 * H)
    c1.close()
    build(b, -0.05)
    os.replace(b, a)
    c2 = store.connect(a)
    second = S.empirical_cohort(c2, "WATCH", min_n=1, asof=T0 + 40 * H)
    c2.close()
    assert first["ret_p10_p50_p90"][1] != second["ret_p10_p50_p90"][1]
