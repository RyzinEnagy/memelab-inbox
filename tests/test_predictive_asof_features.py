"""Predictive intelligence Phase 05: point-in-time features (memelab/predictive/features.py).

The strict invariant available_at <= decision_time is enforced by the view (replay_core.Audit, LeakageError) and checked by
truncation invariance; a feature input 1 s after the decision is absent and one exactly at it is present (P36); missingness
is explicit with a basis; snapshots are deterministic, versioned (P46) and immutable (P03, P07); the universe at a decision
holds only decisions at or before it (P43); outages and dead pools are visible statuses (P47, P09); capture mode never
counts a backfill before its read (P04); same-symbol mints and other pools never join (P01, P02). No network, temp files.
"""
import types
import json
import math
import socket
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from memelab.predictive import features as F
from memelab.predictive import sources as SRC
from memelab.predictive import store as S
from memelab.social import replay_core as RC

FIX = Path(__file__).resolve().parent / "fixtures" / "predictive"
H = types.ModuleType("asof_helpers")          # loaded without writing bytecode next to the fixtures
exec(compile((FIX / "asof_helpers.py").read_text(), str(FIX / "asof_helpers.py"), "exec"), H.__dict__)
V = F.FEATURE_VERSION
CANDLE = [f["name"] for f in F.FEATURES if f["group"] in ("candle", "cross")]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network use in a Phase 05 test")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(SRC, "curl_get", refuse)


@pytest.fixture
def world(tmp_path):
    c = S.connect(tmp_path / "store.sqlite")
    times = H.small_world(c)
    yield c, times
    c.close()


def val(snap, name):
    return next(v for v in snap["values"] if v["feature_name"] == name)


def plant(con, *, start, c, retrieved_at, pool=H.POOL_A, mint=H.MINT_A, boundary=None):
    """Ingest one more read of the pool holding a single candle (no series status: only the candle rows matter here)."""
    b = boundary if boundary is not None else start + 300
    return S.ingest_gt_response(con, H.resp(pool, b, [H.candle(start, c=c, h=c * 1.01, l=c * 0.99)], retrieved_at, mint=mint),
                                chain="solana", mint=mint, pool=pool, now=retrieved_at)


# ---------------------------------------------------------------- the strict invariant (A9, P36)
M3 = "Tm2iqbxYjKpW8xCMe6q1xUraNMNzcG5xMztAir3pump"


def live_world(path, *, read_at, decision=H.T0 + 86400 + 60):
    """One decision of M3 at `decision` (60 s past a 5-minute mark) and one read of its pool returning three candles, the
    newest ending 60 s before the decision, received at `read_at`."""
    con = S.connect(path)
    T = decision
    S.ingest_exports(con, [H.export("c1", T, [H.thesis(M3, T - 100)], [H.token(M3, pool=H.POOL_A2)])], now=T)
    rows = [H.candle(T - 360 - 300 * i, c=1.0 + 0.1 * i) for i in range(3)]
    r = S.ingest_gt_response(con, H.resp(H.POOL_A2, T - 1 if read_at < T else T, rows, read_at, mint=M3), chain="solana", mint=M3,
                             pool=H.POOL_A2, now=read_at)
    H.series(con, mint=M3, pool=H.POOL_A2, boundary=T - 1 if read_at < T else T, need_from=H.T0, keys=[r["response_key"]],
             checked_at=read_at, kept=3, last_end=T - 60)
    con.commit()
    return con, T


def test_an_input_available_one_second_after_the_decision_is_absent_and_one_at_it_is_present(tmp_path):
    ages = {}
    for read_at in ("at", "after"):
        T = H.T0 + 86400 + 60
        con, T = live_world(tmp_path / f"{read_at}.sqlite", read_at=T if read_at == "at" else T + 1)
        newest = S.iter_rows(con, "SELECT * FROM predictive_candles ORDER BY end_at DESC")[0]
        assert newest["available_basis"] == "CAPTURE" and newest["available_at"] == (T if read_at == "at" else T + 1)
        snap = F.features_as_of(con, "solana", M3, T, V)
        ages[read_at] = val(snap, "cdl_last_close_age_s")["value"]
        con.close()
    assert ages == {"at": 60.0, "after": 360.0}


def test_a_revision_counts_from_its_read_onward_and_never_before(tmp_path):
    con, T = live_world(tmp_path / "rev.sqlite", read_at=H.T0 + 86400 + 59)
    rows = [H.candle(T - 360 - 300 * i, c=1.0 + 0.1 * i) for i in range(3)]
    rows[0] = H.candle(T - 360, c=2.0)                           # the vendor later revises the newest close
    R2 = T + 50
    r = S.ingest_gt_response(con, H.resp(H.POOL_A2, R2, rows, R2, mint=M3), chain="solana", mint=M3, pool=H.POOL_A2, now=R2)
    H.series(con, mint=M3, pool=H.POOL_A2, boundary=R2, need_from=H.T0, keys=[r["response_key"]], checked_at=R2, sid="rev")
    before = F.features_as_of(con, "solana", M3, T, V)
    after = F.features_as_of(con, "solana", M3, R2 + 10, V)
    assert r["revisions"] == 1 and r["reads"] == 2
    assert val(after, "xsrc_log_close_over_thesis_price")["value"] == pytest.approx(math.log(2.0 / 1.0))
    assert val(before, "xsrc_log_close_over_thesis_price")["value"] == pytest.approx(0.0)


def test_a_window_the_fetched_history_does_not_cover_is_missing_not_zero(tmp_path):
    con = S.connect(tmp_path / "w.sqlite")
    T = H.T0 + 86400 + 60
    S.ingest_exports(con, [H.export("c1", T, [H.thesis(M3, T - 100)], [H.token(M3, pool=H.POOL_A2)])], now=T)
    rows = [H.candle(T - 360 - 300 * i) for i in range(20)]      # 100 minutes of history in a read that hit its limit
    r = S.ingest_gt_response(con, H.resp(H.POOL_A2, T, rows, H.T0 + 30 * 86400, mint=M3), chain="solana", mint=M3, pool=H.POOL_A2,
                             now=1, limit=20)
    assert r["cover_complete"] == 0
    H.series(con, mint=M3, pool=H.POOL_A2, boundary=T, need_from=H.T0, keys=[r["response_key"]], checked_at=H.T0 + 30 * 86400)
    snap = F.features_as_of(con, "solana", M3, T, V)
    assert val(snap, "cdl_vol_usd_1h")["value"] == 1100.0 and val(snap, "cdl_log_ret_1h")["value"] is not None
    for n in ("cdl_vol_usd_24h", "cdl_candles_24h", "cdl_log_ret_6h", "cdl_rv_6h", "cdl_log_range_24h"):
        assert val(snap, n)["missing_reason"] == "OUTSIDE_FETCHED_WINDOW" and val(snap, n)["missing_basis"] == "RETRIEVAL", n


def test_the_view_audits_every_row_and_raises_on_a_later_one(world):
    con, (d1, d2, d3) = world
    view = F.AsOfView(con, d2)
    rows = view.candles("solana", H.MINT_A, H.POOL_A)
    assert rows and all(r["_avail"] <= d2 for r in rows) and view.audit.records == len(rows)
    with pytest.raises(RC.LeakageError):
        view._check("candle", [{"_avail": d2 + 1}])


def test_a_view_whose_filters_are_bypassed_is_caught_by_the_audit(world, monkeypatch):
    con, (d1, d2, d3) = world
    real = S.iter_rows

    def leaky(c, sql, params=()):
        if "FROM predictive_candles" in sql:
            sql = sql.replace("<= ?", ">= ? - 1e12")       # a broken SQL filter that returns everything
        return real(c, sql, params)

    def no_time_visible(obs, chain, contract, as_of):
        return F.OC.__dict__["visible"].__wrapped__(obs, chain, contract, 1e18) if hasattr(F.OC.visible, "__wrapped__") else \
            _visible_all(obs)
    monkeypatch.setattr(S, "iter_rows", leaky)
    monkeypatch.setattr(F.OC, "visible", lambda obs, chain, contract, as_of: _visible_all(obs))
    with pytest.raises(RC.LeakageError):
        F.features_as_of(con, "solana", H.MINT_A, d1, V)


def _visible_all(obs):
    best = {}
    for o in obs:
        if o["series_key"] not in best or o["seq"] > best[o["series_key"]]["seq"]:
            best[o["series_key"]] = o
    return list(best.values())


def test_truncation_invariance_in_both_modes(world):
    con, (d1, d2, d3) = world
    targets = [("solana", H.MINT_A, d1), ("solana", H.MINT_A, d2), ("solana", H.MINT_B, d2), ("solana", H.MINT_A, d3),
               ("solana", H.MINT_A, d2 + 3600.5)]
    for mode in F.MODES:
        r = F.truncation_check(con, targets, mode)
        assert r["ok"] and r["checked"] == 5, r


def test_truncation_check_is_sensitive_to_a_read_past_the_cutoff(world, monkeypatch):
    con, (d1, d2, d3) = world
    real = F.AsOfView.candles

    def peek(self, chain, mint, pool):
        saved = self.cutoff
        self.cutoff = saved + 86400                 # a feature that quietly looks one day ahead
        try:
            rows = real(self, chain, mint, pool)
        finally:
            self.cutoff = saved
        for r in rows:
            r["_avail"] = min(r["_avail"], saved)    # and hides it from the audit
        return rows
    monkeypatch.setattr(F.AsOfView, "candles", peek)
    r = F.truncation_check(con, [("solana", H.MINT_A, d1)], "provider")
    assert not r["ok"] and r["differences"][0]["features"]


# ---------------------------------------------------------------- the API (A10)
def test_features_as_of_is_deterministic_and_complete(world):
    con, (d1, d2, d3) = world
    a = F.features_as_of(con, "solana", H.MINT_A, d3, V)
    b = F.features_as_of(con, "solana", H.MINT_A, d3, V)
    assert a["snapshot_sha256"] == b["snapshot_sha256"] and [v["feature_name"] for v in a["values"]] == F.NAMES
    assert a["cutoff_at"] == a["decision_time"] == d3 and a["max_input_available_at"] <= d3
    for v in a["values"]:
        assert (v["value"] is None) != (v["missing_reason"] is None)
        assert (v["missing_reason"] is None) == (v["missing_basis"] is None)
        for k in ("source_ids", "raw_hashes", "source_fingerprint", "evidence", "feature_version"):
            assert v[k] is not None, (v["feature_name"], k)
        if v["value"] is not None:
            assert v["feature_available_at"] is not None and v["feature_available_at"] <= d3 and v["available_basis"]
            assert v["raw_hashes"] and v["retrieved_at"] is not None or v["feature_name"].startswith("universe")
    assert val(a, "hist_prior_decisions")["value"] == 2.0
    assert val(a, "thesis_status_rejected")["value"] == 0.0 and val(a, "cdl_candles_24h")["value"] > 200
    assert val(a, "cdl_log_ret_1h")["evidence"] == "HEURISTIC" and val(a, "thesis_score")["evidence"] == "FACT"


def test_determinism_across_fresh_processes(world, tmp_path):
    con, (d1, d2, d3) = world
    con.commit()
    path = next(r[2] for r in con.execute("PRAGMA database_list") if r[1] == "main")
    code = ("import sys,json; from memelab.predictive import store as S, features as F; c=S.connect(sys.argv[1]); "
            "print(F.features_as_of(c,'solana',sys.argv[2],float(sys.argv[3]),F.FEATURE_VERSION)['snapshot_sha256'])")
    root = Path(__file__).resolve().parents[1]
    outs = {subprocess.run([sys.executable, "-c", code, path, H.MINT_A, repr(d3)], capture_output=True, text=True, cwd=root,
                           check=True).stdout.strip() for _ in range(2)}
    assert outs == {F.features_as_of(con, "solana", H.MINT_A, d3, V)["snapshot_sha256"]}


def test_another_feature_version_or_definitions_hash_is_refused(world):
    con, (d1, d2, d3) = world
    for other in ("1", "3"):                      # version 1 (before repair m2) and any later one are refused
        with pytest.raises(F.FeatureVersionError):
            F.features_as_of(con, "solana", H.MINT_A, d3, other)
    with pytest.raises(F.FeatureVersionError):
        F.require_compatible(V, "0" * 64)
    F.require_compatible(V, F.feature_set_sha())


def test_a_changed_definition_changes_the_definitions_hash(monkeypatch):
    before = F.feature_set_sha()
    monkeypatch.setitem(F.FEATURES[0], "transform", "ln(snapshot.price) + 1")
    assert F.feature_set_sha() != before


def test_malformed_identity_and_time_are_refused(world):
    con, (d1, d2, d3) = world
    for chain, mint in (("solana", H.MINT_A + "11"), ("solana", "PAID"), ("bsc", H.MINT_A), ("solana", H.MINT_A + " ")):
        with pytest.raises(S.StoreError):
            F.features_as_of(con, chain, mint, d3, V)
    with pytest.raises(F.AsOfError):
        F.features_as_of(con, "solana", H.MINT_A, float("nan"), V)


def test_missing_is_a_reason_never_a_favorable_zero(world):
    con, (d1, d2, d3) = world
    snap = F.features_as_of(con, "solana", H.MINT_A, d1, V)
    assert val(snap, "thesis_cluster_pct")["missing_reason"] == "ABSENT_IN_SNAPSHOT"
    assert val(snap, "thesis_cluster_pct")["value"] is None
    assert val(snap, "hist_seconds_since_prior_decision")["missing_reason"] == "NO_PRIOR_DECISION"
    with pytest.raises(F.AsOfError):
        F._val("cdl_vol_usd_1h")                       # neither a value nor a reason
    with pytest.raises(F.AsOfError):
        F._val("cdl_vol_usd_1h", 0.0, "NO_CANDLE_AVAILABLE")
    with pytest.raises(sqlite3.IntegrityError):         # the table refuses a value row with neither
        con.execute("INSERT INTO predictive_feature_values(value_key, snapshot_key, chain, mint, decision_time, cutoff_at, "
                    "feature_name, feature_version, value, missing_reason, evidence, source_ids_json, raw_hashes_json, "
                    "source_record_count, source_fingerprint, recorded_at) VALUES ('v','s','solana',?,1,1,'f','1',NULL,NULL,"
                    "'FACT','[]','[]',0,'x',1)", (H.MINT_A,))


def test_a_zero_is_a_value_only_where_covered_history_shows_no_trade(world):
    con, (d1, d2, d3) = world
    snap = F.features_as_of(con, "solana", H.MINT_B, d2, V)     # B's pool: two candles a day before, complete coverage
    assert val(snap, "cdl_vol_usd_1h")["value"] == 0.0
    assert val(snap, "cdl_rv_6h")["value"] == pytest.approx(abs(math.log(0.4 / 0.45)), rel=1e-9)
    assert val(snap, "cdl_candles_24h")["value"] == 1.0
    assert val(snap, "cdl_last_close_age_s")["value"] == d2 - (H.T0 + 86400 - 2700)
    assert val(snap, "cdl_log_ret_24h")["value"] == pytest.approx(math.log(0.4 / 0.45), rel=1e-9)


# ---------------------------------------------------------------- immutability (A11, P03, P07)
def test_stored_snapshots_do_not_move_when_later_data_arrive(world):
    con, (d1, d2, d3) = world
    r = F.build_snapshots(con, feature_version=V, now=H.T0 + 40 * 86400)
    assert r["snapshots_added"] == 4 and not r["skipped"]
    keys = [x[0] for x in con.execute("SELECT snapshot_key FROM predictive_snapshots")]
    before = {k: F.stored_snapshot(con, k)["snapshot_sha256"] for k in keys}
    # a later vendor revision of a candle inside every window, and a later export editing a row of the same key
    S.ingest_gt_response(con, H.resp(H.POOL_A, int(d1), [H.candle(H.T0 + 86400, c=99.0, h=120.0, l=90.0)], H.T0 + 50 * 86400),
                         chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=H.T0 + 50 * 86400)
    e4 = H.export("c4", H.T0 + 50 * 86400, [H.thesis(H.MINT_A, d1 - 900, price=7.0, status="REJECTED")],
                  [H.token(H.MINT_A, pool=H.POOL_A, first_seen_at=d1 - 400)])
    with pytest.raises(S.StoreError, match="full history"):
        S.ingest_exports(con, [e4], now=H.T0 + 50 * 86400)
    S.ingest_exports(con, H.world_exports() + [e4], now=H.T0 + 50 * 86400)
    assert F.build_snapshots(con, feature_version=V, now=H.T0 + 51 * 86400)["snapshots_added"] == 0
    for k in keys:
        assert F.stored_snapshot(con, k)["snapshot_sha256"] == before[k] and F.recompute_matches(con, k)
    later = F.features_as_of(con, "solana", H.MINT_A, H.T0 + 50 * 86400 + 1, V)
    assert later["snapshot_sha256"] not in before.values()
    assert S.verify(con) == []


def test_a_recomputation_that_differs_is_refused_not_written(world):
    con, (d1, d2, d3) = world
    snap = F.features_as_of(con, "solana", H.MINT_A, d3, V, persist=True, now=1.0)
    bad = dict(snap, snapshot_sha256="0" * 64)
    with pytest.raises(F.SnapshotDriftError):
        F.save_snapshot(con, bad, now=2.0)
    assert F.stored_snapshot(con, snap["snapshot_key"])["snapshot_sha256"] == snap["snapshot_sha256"]


def test_an_edited_row_first_exported_later_never_reaches_an_earlier_decision(world):
    con, (d1, d2, d3) = world
    before = F.features_as_of(con, "solana", H.MINT_A, d1, V)
    e = H.export("c9", d3 + 100, [H.thesis(H.MINT_A, d1 - 900, price=3.0, status="REJECTED")], [H.token(H.MINT_A, pool=H.POOL_A)])
    S.ingest_exports(con, H.world_exports() + [e], now=d3 + 200)
    assert F.features_as_of(con, "solana", H.MINT_A, d1, V)["snapshot_sha256"] == before["snapshot_sha256"]


# ---------------------------------------------------------------- universe and training view (A13, P43, P13, P46)
def test_a_later_mint_never_enters_an_earlier_universe(tmp_path):
    new_mint = "Tm2iqbxYjKpW8xCMe6q1xUraNMNzcG5xMztAir3pump"
    worlds = {}
    for name in ("base", "later", "at"):
        ex = H.world_exports(extra_in_e2=[H.thesis(new_mint, H.D2 - 50)] if name == "at" else (),
                             extra_tokens_e2=[H.token(new_mint)] if name == "at" else ())
        if name == "later":                       # the new mint's first export one second after D2
            ex = ex[:2] + [H.export("c5", H.D2 + 1, [H.thesis(new_mint, H.D2 - 100)], [H.token(new_mint)])] + ex[2:]
        con = S.connect(tmp_path / f"{name}.sqlite")
        H.small_world(con, exports=ex)
        worlds[name] = F.features_as_of(con, "solana", H.MINT_A, H.D2, V)
        con.close()
    assert worlds["later"]["snapshot_sha256"] == worlds["base"]["snapshot_sha256"]
    assert val(worlds["at"], "universe_new_mints_24h")["value"] == val(worlds["base"], "universe_new_mints_24h")["value"] + 1


def test_training_view_takes_decisions_up_to_its_as_of_only_and_never_mixes_versions(world):
    con, (d1, d2, d3) = world
    F.build_snapshots(con, feature_version=V, now=1.0)
    rows = F.training_view(con, as_of=d2, feature_version=V)
    assert sorted(r["decision_time"] for r in rows) == [d1, d2, d2]
    assert all(r[n + "__available_at"] <= r["decision_time"] for r in rows for n in F.NAMES)
    con.execute("DROP TRIGGER predictive_snapshots_no_update")
    con.execute("UPDATE predictive_snapshots SET feature_version='0' WHERE decision_time=?", (d1,))
    with pytest.raises(F.FeatureVersionError):
        F.training_view(con, as_of=d2, feature_version=V)


def test_the_row_validator_refuses_future_unknown_and_undeclared_inputs():
    cols = ["decision_time", "a", "a__available_at"]
    ok = {"decision_time": 10.0, "a": 1.0, "a__available_at": 10.0}
    F.validate_rows([ok], columns=cols, availability=["a__available_at"], as_of=10.0)
    for bad in (dict(ok, a__available_at=11.0), dict(ok, a__available_at=None), dict(ok, a__available_at=float("nan")),
                dict(ok, extra=1)):
        with pytest.raises(F.AsOfError):
            F.validate_rows([bad], columns=cols, availability=["a__available_at"])
    with pytest.raises(F.AsOfError):
        F.validate_rows([ok], columns=cols, availability=["a__available_at"], as_of=9.0)
    with pytest.raises(F.AsOfError):
        F.validate_rows([dict(ok, y=1, label_matures_at=20.0)], columns=cols + ["y", "label_matures_at"],
                        availability=["a__available_at"], as_of=15.0)


# ---------------------------------------------------------------- outages, dead pools, capture mode (A14, A15, A8)
def test_a_vendor_outage_is_a_visible_status_and_decision_features_stay(world):
    con, (d1, d2, d3) = world
    pool = H.POOL_A2
    t = d3 + 10                                     # the new export's commit time is the decision time
    S.ingest_exports(con, H.world_exports() + [H.export("c7", t, [H.thesis(M3, t - 100)], [H.token(M3, pool=pool)])], now=t + 10)
    r = S.ingest_gt_response(con, H.resp(pool, int(t), [], H.T0 + 30 * 86400, status=503, mint=M3), chain="solana", mint=M3, pool=pool,
                             now=1)
    H.series(con, mint=M3, pool=pool, boundary=int(t), need_from=H.T0, keys=[r["response_key"]], status="READ_FAILED",
             checked_at=H.T0 + 30 * 86400)
    snap = F.features_as_of(con, "solana", M3, t, V)
    assert {val(snap, n)["missing_reason"] for n in CANDLE} == {"VENDOR_READ_FAILED"}
    assert {val(snap, n)["missing_basis"] for n in CANDLE} == {"RETRIEVAL"}
    assert snap["source_status"] == {"geckoterminal-ohlcv": ["VENDOR_READ_FAILED"], "state-export": "OK"}
    assert val(snap, "thesis_log_price_usd")["value"] == 0.0 and val(snap, "thesis_score")["value"] == 55.0


def test_a_dead_pool_stays_in_the_universe_with_a_status(world):
    con, (d1, d2, d3) = world
    m = M3
    t = d3 + 10
    S.ingest_exports(con, H.world_exports() + [H.export("c8", t, [H.thesis(m, t - 100)], [H.token(m, pool=H.POOL_A2)])],
                     now=t + 10)
    r = S.ingest_gt_response(con, H.resp(H.POOL_A2, int(t), [], H.T0 + 30 * 86400, mint=m), chain="solana", mint=m, pool=H.POOL_A2,
                             now=1)
    H.series(con, mint=m, pool=H.POOL_A2, boundary=int(t), need_from=H.T0, keys=[r["response_key"]], status="NO_DATA",
             checked_at=H.T0 + 30 * 86400)
    F.build_snapshots(con, feature_version=V, now=2.0)
    s = con.execute("SELECT snapshot_key FROM predictive_snapshots WHERE mint=?", (m,)).fetchone()
    assert s is not None
    snap = F.stored_snapshot(con, s[0])
    assert {v["missing_reason"] for v in snap["values"] if v["feature_name"] in CANDLE} == {"VENDOR_NO_DATA"}
    assert json.loads(snap["source_status_json"])["geckoterminal-ohlcv"] == ["VENDOR_NO_DATA"]


def test_capture_mode_never_counts_a_backfill_before_its_read(world, tmp_path):
    con, (d1, d2, d3) = world
    prov = F.features_as_of(con, "solana", H.MINT_A, d3, V, mode="provider")
    cap = F.features_as_of(con, "solana", H.MINT_A, d3, V, mode="capture")
    assert val(prov, "cdl_log_ret_1h")["value"] is not None
    assert {val(cap, n)["missing_reason"] for n in CANDLE} == {"NOT_RETRIEVED_BY_DECISION"}
    late = F.features_as_of(con, "solana", H.MINT_A, H.T0 + 31 * 86400, V, mode="capture")
    assert {val(late, n)["missing_reason"] for n in CANDLE} == {"NOT_FETCHED"}   # read, but not up to that time
    live, T = live_world(tmp_path / "live.sqlite", read_at=H.T0 + 86400 + 59)     # a read 1 s before a live decision
    a = F.features_as_of(live, "solana", M3, T, V, mode="capture")
    b = F.features_as_of(live, "solana", M3, T, V, mode="provider")
    assert val(a, "cdl_last_close_age_s")["value"] == 60.0 and a["snapshot_sha256"] == b["snapshot_sha256"]


def test_sealed_and_out_of_scope_decisions_keep_their_rows_with_reasons(tmp_path):
    con = S.connect(tmp_path / "s.sqlite")
    h0 = SRC.holdout_start()
    evm = "0x" + "ab" * 20
    e = H.export("c1", h0 + 600, [H.thesis(H.MINT_A, h0 + 100), H.thesis(evm, h0 + 100), H.thesis(H.MINT_B, h0 + 100)],
                 [H.token(H.MINT_A, pool=H.POOL_A), H.token(evm, chain="base", pool="0x" + "cd" * 32), H.token(H.MINT_B)])
    S.ingest_exports(con, [e], now=h0 + 700)
    a = F.features_as_of(con, "solana", H.MINT_A, h0 + 600, V)
    b = F.features_as_of(con, "base", evm, h0 + 600, V)
    c = F.features_as_of(con, "solana", H.MINT_B, h0 + 600, V)
    assert {val(a, n)["missing_reason"] for n in CANDLE} == {"NOT_FETCHED_SEALED"}
    assert {val(b, n)["missing_reason"] for n in CANDLE} == {"OUT_OF_SCOPE_CHAIN"}
    assert {val(c, n)["missing_reason"] for n in CANDLE} == {"NO_POOL_AT_DECISION"}
    assert all(val(x, "thesis_score")["value"] == 55.0 for x in (a, b, c))


# ---------------------------------------------------------------- identity in joins (A5, P01, P02)
def test_same_symbol_mints_and_other_pools_never_join(world):
    con, (d1, d2, d3) = world
    a = F.features_as_of(con, "solana", H.MINT_A, d2, V)
    b = F.features_as_of(con, "solana", H.MINT_B, d2, V)
    cnames = [f["name"] for f in F.FEATURES if f["group"] == "candle"]
    ha = set().union(*(set(v["raw_hashes"]) for v in a["values"] if v["feature_name"] in cnames))
    hb = set().union(*(set(v["raw_hashes"]) for v in b["values"] if v["feature_name"] in cnames))
    assert ha and hb and not (ha & hb)
    assert val(b, "hist_prior_decisions")["value"] == 0.0 and val(a, "hist_prior_decisions")["value"] == 1.0
    # a second pool of mint A with wild prices: the decision's point-in-time pool is POOL_A, so nothing changes
    S.ingest_gt_response(con, H.resp(H.POOL_A2, int(d2), [H.candle(int(d2) - 900, c=500.0)], H.T0 + 60 * 86400, mint=H.MINT_A),
                         chain="solana",
                         mint=H.MINT_A, pool=H.POOL_A2, now=1)
    assert F.features_as_of(con, "solana", H.MINT_A, d2, V)["snapshot_sha256"] == a["snapshot_sha256"]
    upper = H.MINT_A[:5] + H.MINT_A[5].swapcase() + H.MINT_A[6:]
    u = F.features_as_of(con, "solana", upper, d2, V)
    assert {v["missing_reason"] for v in u["values"] if not v["feature_name"].startswith("universe")} == {"NOT_IN_UNIVERSE"}

def test_fifteen_minute_candles_of_the_same_pool_never_enter_five_minute_features(world):
    con, (d1, d2, d3) = world
    before = F.features_as_of(con, "solana", H.MINT_A, d3, V)
    rr = H.resp(H.POOL_A, int(d3), [H.candle(int(d3) // 900 * 900 - 900, c=77.0)], H.T0 + 31 * 86400)
    rr.update(timeframe="minute", aggregate=15, url=rr["url"].replace("aggregate=5", "aggregate=15"))
    assert S.url_period(rr["url"]) == 900 and S.url_period(H.resp(H.POOL_A, 1, [], 1)["url"]) == 300
    r = S.ingest_gt_response(con, rr, chain="solana", mint=H.MINT_A, pool=H.POOL_A, now=1)
    row = S.iter_rows(con, "SELECT * FROM predictive_candles WHERE period_s = 900")[0]
    assert r["added"] == 1 and row["available_basis"] == "PROVIDER_LAG_RECONSTRUCTION"   # a 5-minute read never covers it
    S.record_series_status(con, chain="solana", mint=H.MINT_A, pool=H.POOL_A, series_id="m15", boundary_at=int(d3), need_from=H.T0,
                           status="OK", detail=None, response_keys=[r["response_key"]], calls=1, candles_kept=1, last_end_at=None,
                           checked_at=H.T0 + 31 * 86400, now=1, period_s=900)
    assert F.features_as_of(con, "solana", H.MINT_A, d3, V)["snapshot_sha256"] == before["snapshot_sha256"]

