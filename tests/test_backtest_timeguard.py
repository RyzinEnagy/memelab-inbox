"""Phase 05: point-in-time schema, clocks and as-of joins. Golden scenarios G01-G08 plus migration safety.

All data here is synthetic and labeled as such; these tests prove engine behavior, not market fidelity.
"""
import ast
import shutil
import sqlite3
from pathlib import Path

import pytest

from memelab.backtest import schema, store
from memelab.backtest.timeguard import (AsOf, Audit, Bar, ClockError, LeakageError, Series, asof, closed_bars, earliest_execution,
                                        latest_versions, utc_ts, visible_events, MISSING, OBSERVED, STALE, UNAVAILABLE, ZERO)

ROOT = Path(__file__).resolve().parent.parent
T = 1_800_000_000.0  # aligned hour, synthetic clock
H = 3600


@pytest.fixture
def con(tmp_path):
    c = sqlite3.connect(tmp_path / "bt.sqlite")
    c.row_factory = sqlite3.Row
    schema.migrate(c)
    yield c
    c.close()


# ---------------- clock hygiene ----------------

def test_utc_refuses_ambiguous_times():
    assert utc_ts("2027-01-15T08:00:00Z") == utc_ts("2027-01-15T03:00:00-05:00")
    for bad in ("2027-01-15T08:00:00", 1_800_000_000_000, float("nan"), "", None, True, 12):
        with pytest.raises(ClockError):
            utc_ts(bad)


# ---------------- G01 same ticker, two mints ----------------

def test_g01_same_ticker_two_mints_never_merge(con):
    a, b = "MintAAAA1111", "MintBBBB2222"
    for mint, px in ((a, 1.0), (b, 50.0)):
        store.record_asset_version(con, chain="solana", mint=mint, symbol="DOGE2", decimals=6, observed_at=T, source="fixture")
        store.record_bar(con, chain="solana", mint=mint, pool_address=f"pool_{mint}", tf=H, start=T, o=px, h=px, l=px, c=px,
                         volume_usd=1.0, observed_at=T + 2 * H, provider="fixture", provider_lag_s=0)
    ra = store.bars_asof(con, chain="solana", mint=a, pool_address=f"pool_{a}", tf=H, cutoff=T + 2 * H)
    rb = store.bars_asof(con, chain="solana", mint=b, pool_address=f"pool_{b}", tf=H, cutoff=T + 2 * H)
    assert [r["c"] for r in ra] == [1.0] and [r["c"] for r in rb] == [50.0]
    with pytest.raises(ValueError):
        store.record_observation(con, kind="POST", provider="fixture", payload={"x": 1}, observed_at=T, available_at=T, mint=a)  # mint without chain
    # symbol is not a key: there is no lookup by symbol in the store API
    assert not any("symbol" in n for n in dir(store) if n.startswith(("bars_", "pools_", "universe_")))


# ---------------- G02 same mint, two pools ----------------

def test_g02_pools_are_separate_and_time_valid(con):
    m = "MintPOOL3333"
    store.record_pool_version(con, chain="solana", pool_address="P_old", mint=m, pool_type="CPMM", pool_created_at=T, observed_at=T + 10, source="fixture")
    store.record_pool_version(con, chain="solana", pool_address="P_new", mint=m, pool_type="CLMM", pool_created_at=T + 5 * H, observed_at=T + 5 * H + 10, source="fixture")
    at3 = store.pools_valid_at(con, chain="solana", mint=m, cutoff=T + 3 * H)
    at6 = store.pools_valid_at(con, chain="solana", mint=m, cutoff=T + 6 * H)
    assert [p["pool_address"] for p in at3] == ["P_old"]
    assert sorted(p["pool_address"] for p in at6) == ["P_new", "P_old"]
    assert {p["pool_type"] for p in at6} == {"CPMM", "CLMM"}
    # a pool address announced before the pool exists (e.g. a launchpad's precomputed migration pool) is known
    # but not tradeable until it is created
    store.record_pool_version(con, chain="solana", pool_address="P_future", mint=m, pool_type="CPMM", pool_created_at=T + 8 * H,
                              observed_at=T + H, source="fixture")
    assert "P_future" not in [p["pool_address"] for p in store.pools_valid_at(con, chain="solana", mint=m, cutoff=T + 6 * H)]
    assert "P_future" in [p["pool_address"] for p in store.pools_valid_at(con, chain="solana", mint=m, cutoff=T + 8 * H)]


# ---------------- G03 news posted 09:00, ingested 09:08, processed 09:12 ----------------

def test_g03_known_at_is_processing_time(con):
    posted, ingested, processed = T + 9 * H, T + 9 * H + 480, T + 9 * H + 720
    store.record_observation(con, kind="CATALYST_CLAIM", provider="fixture", payload={"title": "listing"}, chain="solana", mint="M3",
                             event_time=posted, observed_at=ingested, available_at=processed)
    s = store.observation_series(con, chain="solana", mint="M3", kind="CATALYST_CLAIM")
    assert asof(s, posted, field_name="value_json").state == MISSING
    assert asof(s, ingested + 60, field_name="value_json").state == MISSING
    assert asof(s, processed, field_name="value_json").state == OBSERVED
    bars = [Bar(T + i * H, H, 1, 1, 1, 1) for i in range(24)]
    ex = earliest_execution(processed, bars)
    assert ex.start == T + 10 * H  # next bar open after 09:12, never 09:00
    with pytest.raises(LeakageError):
        Audit().check("catalyst", [{"available_at": processed}], posted)


# ---------------- G04 transfer at 10:00 is not a sale until the 11:00 swap ----------------

def test_g04_transfer_is_not_a_sale(con):
    store.record_observation(con, kind="WALLET_TRANSFER", provider="fixture", payload={"tx": "a"}, chain="solana", mint="M4", wallet="W1",
                             event_time=T + 10 * H, observed_at=T + 10 * H + 30, available_at=T + 10 * H + 30, value_num=1e6)
    store.record_observation(con, kind="SWAP_SELL", provider="fixture", payload={"tx": "b"}, chain="solana", mint="M4", wallet="W1",
                             event_time=T + 11 * H, observed_at=T + 11 * H + 30, available_at=T + 11 * H + 30, value_num=1e6)
    sells = store.observation_series(con, chain="solana", mint="M4", kind="SWAP_SELL")
    assert asof(sells, T + 10 * H + 600).state == MISSING          # at 10:10 there is a transfer, not a sale
    assert asof(sells, T + 11 * H + 60).state == OBSERVED
    # an append-only log cannot be rewritten to relabel the transfer as a sale
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE bt_observations SET kind='SWAP_SELL' WHERE kind='WALLET_TRANSFER'")


# ---------------- G05 bar high before close; execute after close + delay ----------------

def test_g05_forming_bar_invisible_and_next_open_execution():
    bars = [Bar(T + i * H, H, 1.0, 1.01, 0.99, 1.0) for i in range(12)] + [Bar(T + 12 * H, H, 1.0, 9.99, 1.0, 1.5)]
    decision = T + 12 * H + 600                                    # 12:10, inside the forming 12:00 bar
    vis = closed_bars(bars, decision)
    assert max(b.h for b in vis) == 1.01                            # the 9.99 wick of the forming bar is not visible
    sig_bar = bars[12]
    from memelab.backtest.timeguard import bar_decision_time
    d = bar_decision_time(sig_bar, provider_lag=60)                 # 13:01
    more = bars + [Bar(T + 13 * H, H, 1.4, 1.5, 1.3, 1.45), Bar(T + 14 * H, H, 1.45, 1.5, 1.4, 1.42)]
    ex = earliest_execution(d, more, latency_s=5)
    assert ex.start == T + 14 * H                                   # 13:00 bar already open at 13:01:05: next open is 14:00
    assert earliest_execution(T + 100 * H, more) is None            # end of data: no fill


# ---------------- G06 delisted token stays in the universe ----------------

def test_g06_dead_token_stays_in_frozen_universe(con):
    u = "fixture_universe"
    store.record_universe_member(con, universe_id=u, chain="solana", mint="ALIVE", basis="THESIS", entered_at=T, status_at_entry="WATCH", score_at_entry=60)
    store.record_universe_member(con, universe_id=u, chain="solana", mint="RUGGED", basis="REJECTION", entered_at=T + 60, status_at_entry="REJECTED")
    store.record_lifecycle(con, chain="solana", mint="RUGGED", event="RUGGED", event_time=T + 5 * H, available_at=T + 5 * H + 60, source="fixture")
    members = {m["mint"] for m in store.universe_asof(con, u, T + 10 * H)}
    assert members == {"ALIVE", "RUGGED"}                           # today's API forgetting a token cannot remove it
    assert {m["mint"] for m in store.universe_asof(con, u, T + 30)} == {"ALIVE"}


# ---------------- G07 zero vs missing vs stale vs unavailable ----------------

def test_g07_zero_missing_stale_unavailable():
    s = Series([{"available_at": T, "event_time": T, "value": 0.0},
                {"available_at": T + 10 * H, "event_time": T + 10 * H, "value": None, "value_state": UNAVAILABLE}])
    assert asof(s, T - 1).state == MISSING
    assert asof(s, T + 60, max_age_s=3600).state == ZERO
    assert asof(s, T + 2 * H, max_age_s=3600).state == STALE
    r = asof(s, T + 10 * H + 1)
    assert r.state == UNAVAILABLE and r.value is None and not r.usable
    assert asof(None, T).state == MISSING


# ---------------- G08 corrected and deleted posts ----------------

def test_g08_corrections_and_deletions_never_reach_earlier_cutoffs(con):
    i1, _ = store.record_observation(con, kind="POST", provider="fixture", payload={"text": "launch at 18:00", "v": 1}, chain="solana", mint="M8",
                                     origin_group="post-1", event_time=T + 9 * H, observed_at=T + 9 * H + 60, available_at=T + 9 * H + 60)
    i2, _ = store.record_observation(con, kind="POST_EDIT", provider="fixture", payload={"text": "launch at 08:00 (backdated edit)", "v": 2}, chain="solana",
                                     mint="M8", origin_group="post-1", event_time=T + 8 * H, observed_at=T + 20 * H, available_at=T + 20 * H, supersedes_id=i1)
    i3, _ = store.record_observation(con, kind="POST_DELETED", provider="fixture", payload={"deleted": True, "v": 3}, chain="solana", mint="M8",
                                     origin_group="post-1", observed_at=T + 30 * H, available_at=T + 30 * H, supersedes_id=i2)
    rows = [dict(r) | {"origin_key": r["origin_group"]} for r in con.execute("SELECT * FROM bt_observations WHERE mint='M8'")]
    at10 = latest_versions(rows, T + 10 * H)
    at25 = latest_versions(rows, T + 25 * H)
    at31 = latest_versions(rows, T + 30 * H + 1)
    assert [r["id"] for r in at10] == [i1] and '"v":1' in at10[0]["value_json"]
    assert [r["id"] for r in at25] == [i2]
    assert at31 == []
    # the backdated event_time of the edit does not make it visible before it was observed
    assert all(r["id"] != i2 for r in visible_events(rows, T + 10 * H))
    # the original row is intact
    assert con.execute("SELECT value_json FROM bt_observations WHERE id=?", (i1,)).fetchone()[0].count('"v":1') == 1
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("DELETE FROM bt_observations WHERE id=?", (i1,))


# ---------------- bar revisions and partial bars ----------------

def test_bar_revision_visible_only_from_its_observation(con):
    kw = dict(chain="solana", mint="MR", pool_address="PR", tf=H, start=T, volume_usd=1.0, provider="fixture", provider_lag_s=300)
    store.record_bar(con, o=1, h=1.2, l=0.9, c=1.1, observed_at=T + H + 400, **kw)
    _, again = store.record_bar(con, o=1, h=1.2, l=0.9, c=1.1, observed_at=T + 5 * H, **kw)
    assert again is False                                           # idempotent re-ingest
    store.record_bar(con, o=1, h=1.9, l=0.9, c=1.8, observed_at=T + 50 * H, **kw)  # provider revised the bar later
    early = store.bars_asof(con, chain="solana", mint="MR", pool_address="PR", tf=H, cutoff=T + 2 * H)
    late = store.bars_asof(con, chain="solana", mint="MR", pool_address="PR", tf=H, cutoff=T + 60 * H)
    assert early[0]["c"] == 1.1 and "AVAIL_MODELED" in early[0]["quality_flags"]
    assert late[0]["c"] == 1.8 and "REVISION" in late[0]["quality_flags"]
    with pytest.raises(ClockError):
        store.record_bar(con, o=1, h=1, l=1, c=1, observed_at=T + 30 * 60, **{**kw, "start": T + 100 * H})  # partial bar refused


# ---------------- migrations: additive, idempotent, reversible, legacy untouched ----------------

def _legacy_fingerprint(c):
    tabs = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'bt_%' ORDER BY name")]
    fp = {}
    for t in tabs:
        rows = c.execute(f"SELECT * FROM {t}").fetchall()
        fp[t] = store.sha256([list(r) for r in rows])
    return fp


def test_migration_on_copy_of_tracked_db_leaves_legacy_unchanged(tmp_path):
    src = ROOT / "data" / "memelab.sqlite"
    if not src.exists():
        pytest.skip("tracked database not present")
    dst = tmp_path / "copy.sqlite"
    schema.backup_db(src, dst)
    c = sqlite3.connect(dst)
    before = _legacy_fingerprint(c)
    assert schema.migrate(c) == [1]
    assert schema.migrate(c) == []                                  # idempotent
    c.close()
    c = sqlite3.connect(dst)                                        # reopen
    assert schema.current_version(c) == 1
    assert _legacy_fingerprint(c) == before
    assert schema.rollback(c) == [1]
    assert not [r for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'bt_%' AND name != 'bt_schema_migrations'")]
    assert _legacy_fingerprint(c) == before
    c.close()


def test_changed_migration_refused(con):
    bad = [(1, "backtesting core v1", schema.V1_UP + "\n-- edited", schema.V1_DOWN)]
    with pytest.raises(RuntimeError):
        schema.migrate(con, migrations=bad)


def test_every_bt_table_is_append_only(con):
    for t in schema.BT_TABLES:
        trg = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (t,))}
        assert {f"{t}_no_update", f"{t}_no_delete"} <= trg, t


def test_experiment_run_id_is_reproducible(con):
    cfg = {"strategy_id": "S", "strategy_version": "1", "splits": [0.5, 0.25, 0.25], "code_sha": "abc"}
    a = store.register_run(con, cfg, dataset_hash="d1", seed=7)
    b = store.register_run(con, cfg, dataset_hash="d1", seed=7)
    c = store.register_run(con, cfg, dataset_hash="d2", seed=7)
    assert a == b and a != c
    assert con.execute("SELECT COUNT(*) FROM bt_experiment_runs").fetchone()[0] == 2


# ---------------- research-only guard (G33 part) ----------------

FORBIDDEN_IMPORTS = {"solders", "solana", "nacl", "ed25519", "web3", "eth_account", "ccxt", "jupiter_python_sdk"}
FORBIDDEN_TEXT = ("/swap/v1/swap", "/execute", "sendTransaction", "signTransaction", "Keypair", "secretKey", "private_key", "mnemonic", "seed_phrase")


def test_backtest_package_has_no_order_or_key_path():
    pkg = ROOT / "memelab" / "backtest"
    for f in pkg.rglob("*.py"):
        src = f.read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                for n in names:
                    assert n.split(".")[0] not in FORBIDDEN_IMPORTS, f"{f}: imports {n}"
        for s in FORBIDDEN_TEXT:
            assert s not in src, f"{f}: contains {s!r}"
