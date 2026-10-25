"""Phase 06: outcome labels, censoring and the mature-only training gate (memelab/predictive/labels.py).

Synthetic candles only (the real labels are built by audits/predictive-intelligence/phase_06/probes/build_labels.py). No network,
temp stores, fixed times. Scenario ids from the package's ADVERSARIAL_SCENARIOS.md.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

from memelab.predictive import contract as C
from memelab.predictive import labels as L
from memelab.predictive import runtime as R
from memelab.predictive import store as S

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests" / "fixtures" / "predictive"))
import asof_helpers as H  # noqa: E402

MINT, POOL = H.MINT_A, H.POOL_A
MINT_B, POOL_B = H.MINT_B, H.POOL_B
POOL_A2 = H.POOL_A2
DT = H.T0 + 86400 + 1234           # unaligned decision time (2026-10-08T00:20:34Z)
TE = DT + 300                      # t_entry
LATE = DT + 30 * 86400             # a read long after every maturity


def mkread(rows, boundary, retrieved=LATE, *, mint=MINT, pool=POOL, status=200, base=None, quote=None, token=True):
    url = H.GT.format(pool=pool, b=int(boundary)) + (f"&token={mint}" if token else "")
    body = (H.gt_body(rows, base=base or mint, **({"quote": quote} if quote else {})) if status == 200 else b'{"errors":[]}')
    return L.read_from_body(body, mint=mint, pool=pool, url=url, boundary=boundary, retrieved_at=retrieved, http_status=status,
                            response_key=L.sha([url, retrieved, len(rows)]))


def grid(t0, t1, c=1.0, v=1000.0):
    """Flat 5-minute candles with starts in [t0, t1)."""
    s0 = int(L.ceil_grid(t0))
    return [H.candle(s, c=c, v=v) for s in range(s0, int(t1), 300)]


def ref_rows(c=1.0):
    """A reference candle available at DT (end + 300 <= DT) plus an hour of trading before it."""
    last_ok = int((DT - 600) // 300 * 300)
    return [H.candle(s, c=c) for s in range(last_ok - 3600, last_ok + 1, 300)]


def T2B():
    return L.needed_boundary(L.T2, DT)


def dec(mint=MINT, pool=POOL, t=DT, key=None, vol=2e5, price=1.0, route="PIT_RECORDED", chain="solana", creator=None, flags=()):
    return {"decision_key": key or f"k-{mint[:4]}-{int(t)}", "chain": chain, "mint": mint, "pool": pool, "route": route,
            "decision_time": float(t), "decision_time_basis": "EXPORT_COMMIT", "export_commit": "c1", "created_at": float(t) - 600,
            "status": "WATCH", "flags": list(flags), "snapshot": {"price": price, "vol_24h": vol, "liquidity": 5e4},
            "token": {"creator": creator, "first_pool_at": "2026-10-01T00:00:00Z"}, "row_sha256": "0" * 64}


def build_one(rows, *, boundary=None, retrieved=LATE, others=None, **kw):
    d = dec(**kw)
    rd = mkread(rows, boundary or T2B(), retrieved, mint=d["mint"], pool=d["pool"])
    recs, elig = L.build(L.Universe([d], as_of=retrieved, read_of={d["decision_key"]: rd},
                                    other_reads={d["decision_key"]: others} if others is not None else {}))
    return {r["target"]: r for r in recs}, elig[d["decision_key"]]


@pytest.fixture
def con(tmp_path):
    c = L.connect(tmp_path / "labels.sqlite")
    yield c
    c.close()


# ---------------------------------------------------------------- registry
def test_labels_cover_exactly_the_registry_primary_targets_and_their_frozen_values():
    assert set(L.TARGETS) == set(C.PRIMARY)
    assert (C.TARGETS[L.T1]["upper"], C.TARGETS[L.T1]["lower"], C.TARGETS[L.T1]["horizon_s"]) == (1.25, 0.85, 86400)
    assert (C.TARGETS[L.T1B]["horizon_s"], C.TARGETS[L.T2]["drawdown"], C.TARGETS[L.T2]["confirm_s"]) == (21600, 0.5, 86400)
    assert L.needed_boundary(L.T2, DT) == L.ceil_grid(TE + 2 * 86400)
    assert C.label_matures_at(L.T2, DT) == TE + 2 * 86400 + 900


def test_barriers_are_inclusive_and_relative_to_the_reference_close():
    rows = ref_rows(1.0) + [H.candle(int(L.ceil_grid(TE)) + 600, c=1.0, h=1.25, l=0.99)]
    recs, _ = build_one(rows + grid(TE + 3600, TE + 2 * 86400))
    assert recs[L.T1]["label_class"] == "TARGET_FIRST" and recs[L.T1]["label"] == 1
    rows = ref_rows(1.0) + [H.candle(int(L.ceil_grid(TE)) + 600, c=1.0, h=1.01, l=0.85)]
    recs, _ = build_one(rows + grid(TE + 3600, TE + 2 * 86400))
    assert recs[L.T1]["label_class"] == "INVALIDATION_FIRST" and recs[L.T1]["label"] == 0
    rows = ref_rows(1.0) + [H.candle(int(L.ceil_grid(TE)) + 600, c=1.0, h=1.2499, l=0.8501)]
    recs, _ = build_one(rows + grid(TE + 3600, TE + 2 * 86400))
    assert recs[L.T1]["label_class"] == "NEITHER"


# ---------------------------------------------------------------- P06: no same-candle entry, nothing after the horizon
def test_p06_the_candle_holding_the_entry_and_candles_after_the_horizon_never_count():
    hold = int(TE // 300 * 300)                      # starts before t_entry, ends after it
    assert hold < TE < hold + 300
    after = int(L.ceil_grid(TE + 21600))             # first candle that ends after the 6 h horizon
    rows = ref_rows(1.0) + [H.candle(hold, c=1.0, h=5.0, l=0.99)] + grid(hold + 300, after, c=1.0) + \
        [H.candle(after, c=1.0, h=9.0, l=0.99)] + grid(after + 300, TE + 2 * 86400, c=1.0)
    recs, _ = build_one(rows)
    assert recs[L.T1B]["label_class"] == "NEITHER"           # the 5x candle held t_entry, the 9x one ended after 6 h
    assert recs[L.T1]["label_class"] == "TARGET_FIRST"       # inside 24 h the later spike counts
    assert recs[L.T1]["first_touch_start"] == after


def test_p06_reference_candle_must_be_available_at_the_decision():
    # the newest closed candle is not yet served at the decision (end + 300 s > decision), so the one before it is P0
    late = int(DT // 300 * 300) - 300                    # closed by the decision, served only after it
    rows = [H.candle(late - 300, c=1.0), H.candle(late, c=2.0)] + grid(TE, TE + 2 * 86400, c=1.0)
    assert late + 300 <= DT < late + 300 + 300
    recs, _ = build_one(rows)
    assert recs[L.T1]["p0"] == 1.0 and recs[L.T1]["p0_start"] == late - 300


def test_tie_rule_ambiguous_bar_is_negative_and_its_opposite_is_kept_for_sensitivity_only():
    rows = ref_rows(1.0) + [H.candle(int(L.ceil_grid(TE)) + 300, c=1.0, h=1.3, l=0.8)] + grid(TE + 3600, TE + 2 * 86400)
    recs, _ = build_one(rows)
    for t in (L.T1, L.T1B):
        assert recs[t]["label_class"] == "AMBIGUOUS_BAR" and recs[t]["label"] == 0 and recs[t]["label_tie_positive"] == 1


# ---------------------------------------------------------------- P05: pending is not negative
def test_p05_a_read_before_maturity_leaves_the_label_pending_and_untrainable(con):
    rows = ref_rows(1.0) + grid(TE, TE + 2 * 86400, c=1.0)
    early = C.label_matures_at(L.T1, DT) - 1          # T1b matured, T1 and T2 not yet
    recs, _ = build_one(rows, boundary=L.needed_boundary(L.T1B, DT), retrieved=early)
    assert recs[L.T1]["state"] == "PENDING" and recs[L.T1]["label"] is None
    assert recs[L.T2]["state"] == "PENDING"
    assert recs[L.T1B]["state"] == "LABELED"
    L.store_labels(con, list(recs.values()), export_ref="x", params={}, now=LATE)
    assert L.training_labels(con, LATE, L.T1) == []
    assert len(L.training_labels(con, LATE, L.T1B)) == 1
    with pytest.raises(C.ContractError):
        C.assert_scorable({"label": None, "target": L.T1, "decision_time": DT, "label_status": "PENDING"}, LATE)


def test_p05_a_decision_not_read_because_every_label_is_pending_is_pending_not_negative():
    d = dec()
    recs, elig = L.build(L.Universe([d], as_of=DT + 3600))
    assert elig[d["decision_key"]] == "NOT_READ"
    assert {r["state"] for r in recs} == {"PENDING"} and all(r["label"] is None for r in recs)


# ---------------------------------------------------------------- P09, P37: dead, rugged, unquoted
def test_p37_trading_stops_after_entry_is_no_trades_and_halt_only_with_evidence():
    rows = ref_rows(1.0)                                           # reference present, then nothing until the boundary
    recs, _ = build_one(rows, others=[])                           # the vendor lists no other pool
    assert recs[L.T1]["label_class"] == "NO_TRADES_AFTER_ENTRY" and recs[L.T1]["label"] == 0
    assert recs[L.T2]["label_class"] == "TRADING_HALT" and recs[L.T2]["label"] == 1


def test_p09_an_empty_page_is_never_evidence_of_no_trade():
    for vol, want in ((2e5, "VENDOR_OR_ROUTE_GAP"), (500.0, "MARKET_INACTIVE")):
        recs, elig = build_one([], vol=vol)
        assert elig == want
        assert all(r["state"] == want and r["label"] is None for r in recs.values())
        assert all(r["censored"] == (1 if want == "VENDOR_OR_ROUTE_GAP" else 0) for r in recs.values())


def test_p37_a_pool_the_vendor_no_longer_serves_is_censored_not_a_fill():
    d = dec()
    rd = mkread([], T2B(), status=404)
    recs, elig = L.build(L.Universe([d], as_of=LATE, read_of={d["decision_key"]: rd}))
    assert elig[d["decision_key"]] == "VENDOR_OR_ROUTE_GAP" and all(r["censored"] == 1 for r in recs)


def test_absence_needs_a_candle_before_the_span_and_a_boundary_after_it():
    s, e = L.halt_span(DT)
    inside_only = mkread([H.candle(int(L.ceil_grid(s)) + 600, c=1.0)], T2B())
    assert not L.absence_evidenced(inside_only, s, e)
    short = mkread(ref_rows(), L.ceil_grid(e) - 300)
    assert not L.absence_evidenced(short, s, e)
    assert L.absence_evidenced(mkread(ref_rows(), L.ceil_grid(e)), s, e)
    assert not L.absence_evidenced(mkread([], L.ceil_grid(e)), s, e)


def test_t2_other_pools_decide_halt_trade_or_censoring():
    rows = ref_rows(1.0) + grid(TE, TE + 3 * 3600, c=1.0)          # trades 3 h, then the reference pool goes quiet
    s, e = L.halt_span(DT)
    quiet = mkread(grid(TE - 7200, TE, c=1.0), L.ceil_grid(e), pool=POOL_A2)
    traded = mkread(grid(TE - 7200, TE, c=1.0) + [H.candle(int(L.ceil_grid(s)) + 3000, c=1.0)], L.ceil_grid(e), pool=POOL_A2)
    empty = mkread([], L.ceil_grid(e), pool=POOL_A2)
    assert build_one(rows)[0][L.T2]["state"] == L.NEEDS_OTHER_POOLS
    assert build_one(rows, others=[quiet])[0][L.T2]["label_class"] == "TRADING_HALT"
    r = build_one(rows, others=[quiet, traded])[0][L.T2]
    assert r["label_class"] == "NO_SEVERE_EVENT" and "HALT_ON_REFERENCE_POOL_ONLY" in r["flags"]
    r = build_one(rows, others=[empty])[0][L.T2]
    assert r["state"] == "UNVERIFIABLE_NO_VENDOR_HISTORY" and r["censored"] == 1 and r["detail"] == "OTHER_POOL_NOT_EVIDENCED"
    r = build_one(rows, others=L.LIST_FAILED)[0][L.T2]
    assert r["state"] == "UNVERIFIABLE_NO_VENDOR_HISTORY" and r["detail"] == "VENDOR_POOL_LIST_FAILED"


def test_t2_drawdown_wins_over_halt_and_keeps_the_halt_as_a_flag():
    rows = ref_rows(1.0) + [H.candle(int(L.ceil_grid(TE)) + 900, c=0.2, o=1.0, h=1.0, l=0.1)]
    r = build_one(rows)[0]
    assert r[L.T2]["label_class"] == "DRAWDOWN_50" and "HALT_ON_REFERENCE_POOL" in r[L.T2]["flags"]
    assert r[L.T1]["label_class"] == "INVALIDATION_FIRST"


def test_a_read_that_stops_before_the_window_end_is_a_plan_error_not_a_label():
    rows = ref_rows(1.0) + grid(TE, TE + 86400, c=1.0)
    with pytest.raises(L.LabelError):
        build_one(rows, boundary=L.needed_boundary(L.T1, DT))     # T2 needs t_entry + 48 h


# ---------------------------------------------------------------- P01, P02: identity
def test_p01_a_read_of_another_mint_is_refused_even_with_the_same_symbol():
    d = dec()
    other = mkread(ref_rows(), T2B(), mint=MINT_B, pool=POOL_B)
    with pytest.raises(L.LabelError, match="another mint"):
        L.build(L.Universe([d], as_of=LATE, read_of={d["decision_key"]: other}))


def test_p01_a_default_side_read_of_a_quote_side_pool_gives_no_candle():
    rd = mkread(ref_rows() + grid(TE, TE + 86400), T2B(), base="So11111111111111111111111111111111111111112", quote=MINT, token=False)
    assert rd.identity == "MINT_IS_QUOTE" and not rd.ok and rd.candles == ()
    d = dec()
    _, elig = L.build(L.Universe([d], as_of=LATE, read_of={d["decision_key"]: rd}))
    assert elig[d["decision_key"]] == "VENDOR_OR_ROUTE_GAP"


def test_p02_one_mint_on_several_pools_keeps_one_event_and_per_pool_evidence():
    rows = ref_rows(1.0) + grid(TE, TE + 3 * 3600, c=1.0)
    s, e = L.halt_span(DT)
    quiet = mkread(grid(TE - 7200, TE, c=1.0), L.ceil_grid(e), pool=POOL_A2)
    recs, _ = build_one(rows, others=[quiet])
    assert len(recs) == 3 and len({r["decision_key"] for r in recs.values()}) == 1
    assert recs[L.T2]["other_pools"] == [{"pool": POOL_A2, "state": "QUIET_EVIDENCED"}]


def test_read_from_body_keeps_exactly_the_candles_the_store_keeps(tmp_path):
    c = S.connect(tmp_path / "s.sqlite")
    S.ingest_exports(c, H.world_exports(), now=LATE - 10)
    b = int(T2B()) + 150                                            # unaligned: the vendor returns the candle holding it
    rows = ref_rows() + grid(TE, b + 300, c=1.0) + [[int(TE) // 300 * 300 + 7200, 1.0, 0.5, 1.0, 1.0, 1.0]]   # high < open: invalid
    resp = H.resp(POOL, b, list(reversed(rows)), LATE)
    out = S.ingest_gt_response(c, resp, chain="solana", mint=MINT, pool=POOL, now=LATE)
    rd = L.read_from_store(c, out["response_key"])
    stored = [tuple(r) for r in c.execute("SELECT start_at, o, h, l, c, v FROM predictive_candles WHERE response_key=? ORDER BY start_at",
                                          (out["response_key"],))]
    assert rd.candles == tuple(stored) and len(stored) > 300 and out["dropped"] == 2 and out["refused"] == 1


# ---------------------------------------------------------------- P20 overlap, thinning and purge; P14 groups
def test_p20_thinning_per_target_keeps_label_windows_apart():
    d1, d2, d3 = dec(t=DT, key="a"), dec(t=DT + 3 * 3600, key="b"), dec(t=DT + 7 * 3600, key="c")
    rows = [H.candle(s, c=1.0) for s in range(int(DT - 86400) // 300 * 300, int(DT + 7 * 3600 + 3 * 86400), 300)]
    rd = mkread(rows, L.needed_boundary(L.T2, d3["decision_time"]))
    recs, _ = L.build(L.Universe([d1, d2, d3], as_of=LATE, read_of={k: rd for k in "abc"}))
    st = {(r["decision_key"], r["target"]): r["state"] for r in recs}
    assert st[("b", L.T1B)] == "THINNED" and st[("c", L.T1B)] == "LABELED"
    assert st[("b", L.T1)] == "THINNED" and st[("c", L.T1)] == "THINNED"
    thinned_by = {r["decision_key"]: r["thinned_by"] for r in recs if r["target"] == L.T1}
    assert thinned_by["b"] == "a" and thinned_by["c"] == "a"


def test_p20_a_development_label_maturing_after_the_holdout_start_is_purged():
    t = L.holdout_start() - 10 * 3600
    assert L.split_of(L.T1B, t) == "DEVELOPMENT"
    assert L.split_of(L.T1, t) == "PURGED" and L.split_of(L.T2, t) == "PURGED"
    assert L.split_of(L.T1, L.holdout_start()) == "HOLDOUT" and L.split_of(L.T1, L.prospective_start()) == "PROSPECTIVE"
    d = dec(t=t)
    rows = [H.candle(s, c=1.0) for s in range(int(t - 86400) // 300 * 300, int(t + 7 * 3600), 300)]
    recs, _ = L.build(L.Universe([d], as_of=LATE, read_of={d["decision_key"]: mkread(rows, L.needed_boundary(L.T1B, t))}))
    st = {r["target"]: r["state"] for r in recs}
    assert st == {L.T1B: "LABELED", L.T1: "PURGED", L.T2: "PURGED"}


def test_p14_group_keys_are_the_exact_mint_and_the_creator_wallet():
    a, b = dec(mint=MINT, creator="CreatorWa11et"), dec(mint=MINT_B, pool=POOL_B, creator="CreatorWa11et")
    assert L.groups_of(a)["creator"] == L.groups_of(b)["creator"] and L.groups_of(a)["mint"] != L.groups_of(b)["mint"]
    assert L.groups_of(dec(creator=None))["creator"] is None


# ---------------------------------------------------------------- store, seal and the training gate
def test_label_migration_is_additive_append_only_and_reversible(tmp_path):
    c = L.connect(tmp_path / "x.sqlite")
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert set(L.LABEL_TABLES) <= names and set(S.DATA_TABLES) <= names
    recs, _ = build_one(ref_rows() + grid(TE, TE + 2 * 86400))
    L.store_labels(c, list(recs.values()), export_ref="x", params={}, now=LATE)
    c.commit()
    for t in L.LABEL_TABLES:
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            c.execute(f"UPDATE {t} SET recorded_at = 0")
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            c.execute(f"DELETE FROM {t}")
    assert L.rollback_labels(c) == [2]
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not set(L.LABEL_TABLES) & names and set(S.DATA_TABLES) <= names


def test_holdout_rows_never_enter_the_label_table(con):
    t = L.holdout_start() + 3600
    d = dec(t=t)
    rows = [H.candle(s, c=1.0) for s in range(int(t - 86400) // 300 * 300, int(t + 3 * 86400), 300)]
    recs, _ = L.build(L.Universe([d], as_of=t + 5 * 86400, read_of={d["decision_key"]: mkread(rows, L.needed_boundary(L.T2, t),
                                                                                                   t + 5 * 86400)}))
    assert {r["split"] for r in recs} == {"HOLDOUT"}
    with pytest.raises(L.LabelError):
        L.record_row(recs[0], run_key="r", registry_sha="x", now=0)
    assert L.store_labels(con, recs, export_ref="x", params={}, now=LATE)["added"] == 0
    row = L.record_row(dict(recs[0], split="PURGED"), run_key="r", registry_sha="x", now=0)
    S._insert(con, "predictive_label_runs", {"run_key": "r", "labels_version": "x", "registry_sha": "x", "export_ref": "x",
                                             "params_json": "{}", "recorded_at": 0})
    with pytest.raises(sqlite3.IntegrityError):
        L._insert_strict(con, "predictive_labels", dict(row, split="HOLDOUT"))
    sealed = L.sealed_row(recs[0])
    assert sealed["split"] == "HOLDOUT" and sealed["holdout_contacted"] is False


def test_the_training_gate_returns_only_matured_development_labels(con, monkeypatch):
    ds = [dec(t=DT, key="a"), dec(mint=MINT_B, pool=POOL_B, t=DT, key="b", vol=2e5)]
    rd_a = mkread(ref_rows() + grid(TE, TE + 2 * 86400), T2B())
    rd_b = mkread([], T2B(), mint=MINT_B, pool=POOL_B)               # censored
    recs, _ = L.build(L.Universe(ds, as_of=LATE, read_of={"a": rd_a, "b": rd_b}))
    L.store_labels(con, recs, export_ref="x", params={}, now=LATE)
    m = C.label_matures_at(L.T1, DT)
    assert L.training_labels(con, m - 1, L.T1) == []                  # not matured by the training cutoff
    got = L.training_labels(con, m, L.T1)
    assert [r["decision_key"] for r in got] == ["a"] and got[0]["censored"] == 0
    assert L.training_labels(con, m, L.T1, mode="capture") == []      # the lab first held it at the read (LATE)
    assert len(L.training_labels(con, LATE, L.T1, mode="capture")) == 1
    real = S.iter_rows
    monkeypatch.setattr(S, "iter_rows", lambda *a, **k: [dict(r, use=R.BAKEOFF_ONLY) for r in real(*a, **k)])
    with pytest.raises(ValueError, match="BAKEOFF_ONLY"):
        L.training_labels(con, LATE, L.T1)


def test_sealed_and_bakeoff_folders_are_refused_as_label_sources():
    with pytest.raises(L.LabelError):
        L.refuse_sealed(ROOT / L.SEALED_DIR / "holdout_labels.jsonl.gz")
    with pytest.raises(ValueError):
        R.refuse_bakeoff_labels(path=ROOT / R.BAKEOFF_DATA_DIR / "labels.json")
    L.refuse_sealed(ROOT / "audits/predictive-intelligence/phase_06/labels/x.json")


def test_only_the_label_module_names_the_sealed_folder():
    hits = [p for p in (ROOT / "memelab").rglob("*.py") if "phase_06/sealed" in p.read_text() and p.name != "labels.py"]
    assert hits == []


# ---------------------------------------------------------------- P44: price path, not proceeds
def test_p44_rows_carry_the_caveats_and_no_profit_or_exit_field(con):
    recs, _ = build_one(ref_rows() + grid(TE, TE + 2 * 86400))
    L.store_labels(con, list(recs.values()), export_ref="x", params={}, now=LATE)
    cols = [r[1] for r in con.execute("PRAGMA table_info(predictive_labels)")]
    assert not [c for c in cols if any(w in c.lower() for w in L.FORBIDDEN_NAME_WORDS)]
    for r in S.iter_rows(con, "SELECT * FROM predictive_labels"):
        assert json.loads(r["caveats_json"]) == ["PRICE_PATH_NOT_PROCEEDS", "NO_HISTORICAL_EXECUTABLE_DEPTH"]
    with pytest.raises(L.LabelError):
        L._check_names({"return_24h": 0.3})
    for t in L.TARGETS:
        assert t.startswith("price_path_") and not any(w in t for w in ("profit", "return", "exit", "executable"))


def test_p25_a_touch_by_a_tiny_candle_is_flagged_as_a_wick():
    rows = ref_rows(1.0) + [H.candle(int(L.ceil_grid(TE)) + 600, c=1.0, h=1.3, l=0.99, v=12.0)] + grid(TE + 3600, TE + 2 * 86400)
    r = build_one(rows)[0][L.T1]
    assert r["label_class"] == "TARGET_FIRST" and "WICK_TOUCH" in r["flags"] and r["touch_volume_usd"] == 12.0


def test_sparse_paths_are_flagged():
    rows = ref_rows(1.0) + [H.candle(int(L.ceil_grid(TE)) + 300, c=1.0), H.candle(int(L.ceil_grid(TE)) + 4 * 3600, c=1.0)] + \
        grid(TE + 86400, TE + 2 * 86400)
    assert "SPARSE_PATH" in build_one(rows)[0][L.T1B]["flags"]


# ---------------------------------------------------------------- P07: revisions
def test_p07_revision_check_counts_only_reads_48h_apart_and_candles_older_than_48h():
    rows = ref_rows(1.0) + grid(TE, TE + 2 * 86400, c=1.0)
    first = mkread(rows, T2B(), LATE)
    changed = [list(r) for r in rows]
    i = next(i for i, r in enumerate(changed) if r[0] >= TE + 3600)
    changed[i][2] = 1.4                                                # a revised high inside the 24 h path
    soon = mkread(changed, T2B(), LATE + 3600)
    later = mkread(changed, T2B(), LATE + 2 * 86400)
    a, b = L.revision_changes(first, soon), L.revision_changes(first, later)
    assert a["frozen_check"] is False and b["frozen_check"] is True
    assert [x["fields"] for x in b["changed"]] == ["h"] and b["changed"][0]["start"] == changed[i][0]
    with pytest.raises(L.LabelError):
        L.revision_changes(first, mkread(rows, T2B(), LATE, mint=MINT_B, pool=POOL_B))


def test_p07_a_revision_changes_the_label_only_from_its_own_read_and_keeps_both(con):
    rows = ref_rows(1.0) + grid(TE, TE + 2 * 86400, c=1.0)
    recs, _ = build_one(rows)
    L.store_labels(con, list(recs.values()), export_ref="x", params={}, now=LATE)
    stored = {r["target"]: r for r in S.iter_rows(con, "SELECT * FROM predictive_labels")}
    changed = [list(r) for r in rows]
    i = next(i for i, r in enumerate(changed) if r[0] >= TE + 3600)
    changed[i][2] = 1.4
    reread_at = LATE + 3 * 86400
    rev = L.revise(dict(recs[L.T1], label_key=stored[L.T1]["label_key"]), mkread(changed, T2B(), reread_at), reason="REREAD_48H")
    assert rev["label_class"] == "TARGET_FIRST" and "REVISED" in rev["flags"] and rev["revision_of"] == stored[L.T1]["label_key"]
    assert L.revise(recs[L.T1], mkread(rows, T2B(), reread_at), reason="same") is None
    L.store_labels(con, [rev], export_ref="x", params={"revision": 1}, now=reread_at)
    assert con.execute("SELECT COUNT(*) FROM predictive_labels WHERE target=?", (L.T1,)).fetchone()[0] == 2
    before = L.training_labels(con, reread_at - 1, L.T1)
    after = L.training_labels(con, reread_at, L.T1)
    assert before[0]["label_class"] == "NEITHER" and after[0]["label_class"] == "TARGET_FIRST"


# ---------------------------------------------------------------- CX-06: targets of one decision never mix reads
def test_cx06_targets_from_one_read_satisfy_the_cross_target_invariants():
    rows = ref_rows(1.0) + [H.candle(int(L.ceil_grid(TE)) + 1800, c=1.0, h=1.0, l=0.82)] + grid(TE + 7200, TE + 2 * 86400, c=0.4)
    recs, _ = build_one(rows)
    assert recs[L.T1B]["label_class"] == "INVALIDATION_FIRST" and recs[L.T2]["label_class"] == "DRAWDOWN_50"
    assert L.cross_target_violations(recs.values()) == []


def test_cx06_a_label_built_from_another_read_breaks_an_invariant():
    """Counterexample CX-06 (this phase's own, not independent): the vendor computes a response's highs and lows partly from the
    request window (PI-D-037), so a T1b label from one read and a T1 label from another can disagree on the same first candle.
    A builder that labels each target from whichever read covers it (plausible: the shortest read for 6 h, a later one for 24 h)
    gives T1b TARGET_FIRST and T1 INVALIDATION_FIRST for one decision. The invariant check catches it."""
    base = ref_rows(1.0) + grid(TE, TE + 2 * 86400, c=1.0)
    k = next(i for i, r in enumerate(base) if r[0] >= TE + 1800)
    read6 = [list(r) for r in base]
    read6[k][2] = 1.3                                   # in the 6 h read the candle's high touches +25%
    read24 = [list(r) for r in base]
    read24[k][3] = 0.8                                  # in the later read the same candle's low touches -15%
    r6, _ = build_one(read6)
    r24, _ = build_one(read24)
    mixed = [r6[L.T1B], r24[L.T1], r24[L.T2]]
    assert r6[L.T1B]["label_class"] == "TARGET_FIRST" and r24[L.T1]["label_class"] == "INVALIDATION_FIRST"
    v = L.cross_target_violations(mixed)
    assert v and v[0]["rule"] == "T1b first touch is T1's first touch"
    assert L.cross_target_violations(r6.values()) == [] and L.cross_target_violations(r24.values()) == []


# ---------------------------------------------------------------- hand-checked trace (fixture)
HAND = json.loads((ROOT / "tests/fixtures/predictive/labels_hand_trace.json").read_text())


@pytest.mark.parametrize("case", HAND["cases"], ids=[c["name"] for c in HAND["cases"]])
def test_hand_checked_trace_cases(case):
    d = dec(t=case["decision_time"], vol=case.get("snapshot_vol_24h", 2e5))
    rows = case["candles"]
    rd = mkread(rows, case["boundary"], case["retrieved_at"])
    others = None
    if "other_pools" in case:
        others = [mkread(o["candles"], o["boundary"], case["retrieved_at"], pool=o["pool"]) for o in case["other_pools"]]
    recs, elig = L.build(L.Universe([d], as_of=case["retrieved_at"], read_of={d["decision_key"]: rd},
                                    other_reads={d["decision_key"]: others} if others is not None else {}))
    assert elig[d["decision_key"]] == case["expected"]["eligibility"]
    got = {r["target"]: [r["state"], r["label_class"], r["label"]] for r in recs}
    want = {L.T1: case["expected"]["t1_24h"], L.T1B: case["expected"]["t1b_6h"], L.T2: case["expected"]["t2_24h"]}
    assert got == want
    for r in recs:
        if r["state"] == "LABELED":
            assert r["p0"] == case["expected"]["p0"]
            if r["target"] in case["expected"].get("first_touch_start", {}):
                assert r["first_touch_start"] == case["expected"]["first_touch_start"][r["target"]]


def test_the_seal_detects_any_change_to_a_sealed_file(tmp_path):
    a, b = tmp_path / "holdout_labels.jsonl.gz", tmp_path / "raw" / "x.json.gz"
    b.parent.mkdir()
    a.write_bytes(b"sealed-a")
    b.write_bytes(b"sealed-b")
    man = L.seal_manifest([a, b], tmp_path)
    assert set(man) == {"holdout_labels.jsonl.gz", "raw/x.json.gz"} and L.verify_seal(man, tmp_path) == []
    a.write_bytes(b"sealed-A")
    assert L.verify_seal(man, tmp_path) == ["holdout_labels.jsonl.gz: sha256 or size differs from the seal"]
    b.unlink()
    assert "raw/x.json.gz: missing" in L.verify_seal(man, tmp_path)


def test_p09_a_decision_whose_route_resolves_no_pool_is_a_censored_gap_not_unread():
    d = dec(pool=None, route="CURRENT_VENDOR_LIST")                    # no point-in-time pool and an empty vendor list
    recs, elig = L.build(L.Universe([d], as_of=LATE))
    assert elig[d["decision_key"]] == "VENDOR_OR_ROUTE_GAP" and all(r["censored"] == 1 for r in recs)
    p = dec(pool=None, route="CURRENT_VENDOR_LIST", t=L.prospective_start() + 60)
    recs, elig = L.build(L.Universe([p], as_of=LATE))
    assert elig[p["decision_key"]] == "NOT_READ" and {r["state"] for r in recs} == {"PROSPECTIVE"}


# ---------------------------------------------------------------- repair pass 2: the independent skeptic's surviving mutations (M1)
def test_m1_p0_is_the_reference_candle_close_not_its_open():
    rows = ref_rows(1.0)
    rows[-1] = H.candle(rows[-1][0], c=1.0, o=0.8, h=1.0, l=0.8)            # reference candle opens at 0.8, closes at 1.0
    rows += [H.candle(int(L.ceil_grid(TE)) + 600, c=1.0, h=1.10, l=0.99)] + grid(TE + 3600, TE + 2 * 86400)
    r = build_one(rows)[0]
    assert r[L.T1]["p0"] == 1.0 and r[L.T1]["label_class"] == "NEITHER"   # from the open (0.8) the 1.10 high would be +37%


def test_m1_thinning_runs_after_eligibility():
    gap = dec(t=DT, key="gap")                                              # its own read is empty: VENDOR_OR_ROUTE_GAP
    later = dec(t=DT + 3 * 3600, key="later")
    rows = [H.candle(s, c=1.0) for s in range(int(DT + 2 * 3600) // 300 * 300, int(DT + 3 * 3600 + 3 * 86400), 300)]
    recs, elig = L.build(L.Universe([gap, later], as_of=LATE, read_of={
        "gap": mkread([], L.needed_boundary(L.T2, DT)), "later": mkread(rows, L.needed_boundary(L.T2, DT + 3 * 3600))}))
    assert elig == {"gap": "VENDOR_OR_ROUTE_GAP", "later": "ELIGIBLE"}
    assert {r["target"]: r["state"] for r in recs if r["decision_key"] == "later"} == {t: "LABELED" for t in L.TARGETS}


def test_m1_a_trade_from_18_h_in_the_halt_span_is_no_halt():
    assert L.halt_span(DT)[0] == TE + 18 * 3600                              # the registry's span start, from absolute times
    rows = ref_rows(1.0) + grid(TE, TE + 3600) + [H.candle(int(L.ceil_grid(TE + 19 * 3600)), c=1.0)]   # one trade at about 19 h
    r = build_one(rows, others=[])[0][L.T2]
    assert r["label_class"] == "NO_SEVERE_EVENT"


def test_m1_a_candle_overlapping_the_halt_span_start_is_in_the_span():
    s, e = L.halt_span(DT)
    edge = int(s // 300 * 300)                                              # starts before the span, ends inside it
    assert edge < s < edge + 300
    rows = ref_rows(1.0) + grid(TE, TE + 3600) + [H.candle(edge, c=1.0)]
    assert L.in_span(rows[-1], s, e) and not L.in_span(H.candle(edge - 300), s, e)
    assert build_one(rows, others=[])[0][L.T2]["label_class"] == "NO_SEVERE_EVENT"


def test_m1_exactly_three_other_pools_count():
    rows = ref_rows(1.0) + grid(TE, TE + 3 * 3600)
    s, e = L.halt_span(DT)
    quiet = [mkread(grid(TE - 7200, TE), L.ceil_grid(e), pool=p) for p in (POOL_A2, POOL_B, H.POOL_A2)]
    traded = mkread(grid(TE - 7200, TE) + [H.candle(int(L.ceil_grid(s)) + 600, c=1.0)], L.ceil_grid(e), pool=POOL_B)
    assert build_one(rows, others=[quiet[0], quiet[1], traded])[0][L.T2]["label_class"] == "NO_SEVERE_EVENT"   # third counts
    assert build_one(rows, others=quiet + [traded])[0][L.T2]["label_class"] == "TRADING_HALT"                 # fourth does not


def test_m1_a_low_exactly_at_half_is_a_drawdown():
    rows = ref_rows(1.0) + [H.candle(int(L.ceil_grid(TE)) + 900, c=0.6, o=1.0, h=1.0, l=0.5)] + grid(TE + 3600, TE + 2 * 86400, c=0.6)
    assert build_one(rows)[0][L.T2]["label_class"] == "DRAWDOWN_50"


def test_m1_span_ends_are_rounded_up_to_the_candle_grid():
    assert L.ceil_grid(H.T0 + 1) == H.T0 + 300 and L.ceil_grid(H.T0) == H.T0
    s, e = L.halt_span(DT)
    assert e % 300 and L.needed_boundary(L.T2, DT) == L.ceil_grid(e) > e
    assert not L.absence_evidenced(mkread(ref_rows(), e // 300 * 300), s, e)       # floor of the span end is short


def test_m1_absence_needs_a_candle_strictly_before_the_span():
    s, e = L.halt_span(DT)
    rd = L.Read(pool=POOL, mint=MINT, url="u", boundary=L.ceil_grid(e), retrieved_at=LATE, http_status=200, identity="OK_TOKEN_PARAM",
                candles=((s, 1, 1, 1, 1, 1),), cover_from=s)
    assert not L.absence_evidenced(rd, s, e)


def test_m1_pending_and_purge_boundaries_are_inclusive():
    rows = ref_rows(1.0) + grid(TE, TE + 2 * 86400)
    at = C.label_matures_at(L.T1B, DT)
    assert build_one(rows, boundary=L.needed_boundary(L.T1B, DT), retrieved=at)[0][L.T1B]["state"] == "LABELED"
    t = L.holdout_start() - (C.label_matures_at(L.T1B, 0.0) - 0.0)          # matures exactly at the holdout start
    assert C.label_matures_at(L.T1B, t) == L.holdout_start() and L.split_of(L.T1B, t) == "DEVELOPMENT"


def test_m1_conservative_lens_values():
    recs, _ = build_one([])                                                  # empty page: censored gap
    lens = {t: json.loads(L.record_row(r, run_key="r", registry_sha="x", now=0)["sensitivity_json"])["conservative_lens"]
            for t, r in recs.items()}
    assert lens == {L.T1: 0, L.T1B: 0, L.T2: 1}


def test_m1_t2_drawdown_without_a_t1_touch_violates_the_invariant():
    t1 = {"decision_key": "k", "target": L.T1, "state": "LABELED", "label_class": "NEITHER", "first_touch_start": None, "p0": 1.0, "p0_start": 0}
    t2 = {"decision_key": "k", "target": L.T2, "state": "LABELED", "label_class": "DRAWDOWN_50", "first_touch_start": 600, "p0": 1.0, "p0_start": 0}
    assert [v["rule"] for v in L.cross_target_violations([t1, t2])] == ["a 50% drawdown touches the T1 lower barrier no later"]


# ---------------------------------------------------------------- repair pass 2: the training gate (m1 to m3)
def _store_one(con, rows=None):
    recs, _ = build_one(rows or (ref_rows() + grid(TE, TE + 2 * 86400)))
    L.store_labels(con, list(recs.values()), export_ref="x", params={}, now=LATE)
    return recs, {r["target"]: r for r in S.iter_rows(con, "SELECT * FROM predictive_labels")}


def test_m1_gate_recomputes_split_and_maturity_from_the_registry(con):
    _, stored = _store_one(con)
    row = dict(stored[L.T1])
    del row["id"]
    forged = dict(row, label_key="forged", decision_key="forged", decision_time=L.holdout_start() + 3600,
                  label_matures_at=C.label_matures_at(L.T1, L.holdout_start() + 3600) - 4 * 86400)
    L._insert_strict(con, "predictive_labels", forged)                       # claims DEVELOPMENT for a holdout-time decision
    with pytest.raises(L.LabelError, match="disagrees with the registry"):
        L.training_labels(con, LATE, L.T1)


def test_m1_gate_never_returns_a_purged_labeled_row(tmp_path):
    c = L.connect(tmp_path / "p.sqlite")
    t = L.holdout_start() - 10 * 3600                                         # T1 purged by the registry
    _, stored = _store_one(c)
    row = dict(stored[L.T1])
    del row["id"]
    L._insert_strict(c, "predictive_labels", dict(row, label_key="purged", decision_key="purged", decision_time=t, split="PURGED",
                                                  label_matures_at=C.label_matures_at(L.T1, t)))
    assert [r["decision_key"] for r in L.training_labels(c, LATE, L.T1)] == [row["decision_key"]]


def test_m3_a_revision_that_leaves_labeled_removes_the_label(con):
    recs, stored = _store_one(con)
    rev = dict(recs[L.T1], state="UNVERIFIABLE_NO_VENDOR_HISTORY", label_class=None, label=None, revision_of=stored[L.T1]["label_key"],
               revision_reason="TEST", read=mkread(ref_rows() + grid(TE, TE + 2 * 86400), T2B(), LATE + 3 * 86400))
    rev["censored"] = 1
    L.store_labels(con, [rev], export_ref="x", params={"r": 1}, now=LATE + 3 * 86400)
    assert len(L.training_labels(con, LATE, L.T1)) == 1                     # before the revising read
    assert L.training_labels(con, LATE + 3 * 86400, L.T1) == []              # after it: censored, not trained on


def test_m2_gate_refuses_a_sealed_or_bakeoff_store_file(tmp_path, monkeypatch):
    for bad in (L.SEALED_DIR, R.BAKEOFF_DATA_DIR):
        p = tmp_path / bad / "store.sqlite"
        p.parent.mkdir(parents=True)
        c = L.connect(p)
        with pytest.raises(ValueError):
            L.training_labels(c, LATE, L.T1)
        c.close()


# ---------------------------------------------------------------- repair pass 2: CX-S06, a token=<mint> read that kept the other base
ZCAT, ZEC, ZPOOL = "HcRLc9VDgjLeK154xDawfb1dmVJ98DoSqcwTHGqiDeJR", "A7bdiYdS5GjqGFtxf17ppRHtDKPkkRqbKtR27dxvQXaS", "BTccxxTFi7a9xJTE1exKn38Jgie35s6gNeRxd8DM61Rc"


def test_cx_s06_a_token_read_whose_body_keeps_the_other_token_as_base_gives_no_candle():
    """The real ZEC/ZCAT pool (ZCAT quote in the vendor list). Real token=<mint> reads show ZCAT as meta.base at about 0.046 USD;
    a body that kept ZEC as base (about 1,161 USD) would label ZCAT from ZEC's path. Accepted as OK_TOKEN_PARAM before the repair."""
    rows = ref_rows(1161.0) + [H.candle(int(L.ceil_grid(TE)) + 600, c=1161.0, h=1161.0 * 1.3, l=1160.0)] + grid(TE + 3600, TE + 2 * 86400, c=1161.0)
    url = H.GT.format(pool=ZPOOL, b=int(T2B())) + f"&token={ZCAT}"
    wrong = H.gt_body(rows, base=ZEC, quote=ZCAT)
    rd = L.read_from_body(wrong, mint=ZCAT, pool=ZPOOL, url=url, boundary=T2B(), retrieved_at=LATE, http_status=200, response_key="cx")
    assert rd.identity == "TOKEN_PARAM_NOT_BASE" and not rd.ok and rd.candles == ()
    d = dec(mint=ZCAT, pool=ZPOOL, price=0.0456, vol=2e6, route="CURRENT_VENDOR_LIST")
    recs, elig = L.build(L.Universe([d], as_of=LATE, read_of={d["decision_key"]: rd}))
    assert elig[d["decision_key"]] == "VENDOR_OR_ROUTE_GAP" and all(r["label"] is None for r in recs)
    right = L.read_from_body(H.gt_body(rows, base=ZCAT, quote=ZEC), mint=ZCAT, pool=ZPOOL, url=url, boundary=T2B(), retrieved_at=LATE,
                             http_status=200, response_key="ok")
    assert right.identity == "OK_TOKEN_PARAM" and right.ok


def test_p0_far_from_the_snapshot_price_is_flagged():
    rows = ref_rows(1161.0) + grid(TE, TE + 2 * 86400, c=1161.0)
    far = build_one(rows, price=0.0456)[0]
    near = build_one(rows, price=1100.0)[0]
    assert all("P0_FAR_FROM_SNAPSHOT_PRICE" in r["flags"] for r in far.values())
    assert not any("P0_FAR_FROM_SNAPSHOT_PRICE" in r["flags"] for r in near.values())
