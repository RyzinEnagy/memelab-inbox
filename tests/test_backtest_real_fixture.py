"""Phase 06: re-ingestion of real, unmodified GeckoTerminal responses (one collapsed token). Not a backtest result."""
import json
from pathlib import Path

import pytest

from memelab.backtest import quality, store
from memelab.backtest.sources import gecko

FIX = Path(__file__).parent / "fixtures" / "backtest" / "real"
MAN = json.loads((FIX / "MANIFEST.json").read_text())
MINT = MAN["mint"]
POOL = "7AvDaHLbHW6qaMGuHQGpebbbGaV7fRTdFq5T5Vd4vdoH"


def replay(url, timeout=30.0):
    for f, m in MAN["files"].items():
        if m["url"] == url:
            return 200, (FIX / f).read_bytes()
    return 404, b""


@pytest.fixture
def con(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RAW_DIR", tmp_path / "raw")
    c = store.connect(tmp_path / "bt.sqlite")
    yield c
    c.close()


def ingest(con, later_s=0.0):
    b = gecko.Budget(max_calls=10, min_spacing_s=0.0)
    p = gecko.fetch_pools(con, MINT, b, replay, observed_at=MAN["files"]["gt_pools_3GVSN8.json"]["observed_at"] + later_s)
    o = gecko.fetch_ohlcv(con, MINT, POOL, b, replay, observed_at=MAN["files"]["gt_ohlcv_3GVSN8.json"]["observed_at"] + later_s)
    con.commit()
    return p, o


def test_fixture_bytes_are_the_recorded_raw_responses():
    import hashlib
    for f, m in MAN["files"].items():
        assert hashlib.sha256((FIX / f).read_bytes()).hexdigest() == m["sha256"]


def test_real_reingestion_is_idempotent_and_point_in_time(con):
    p, o = ingest(con)
    assert {x["pool_type"] for x in p["pools"]} == {"CPMM", "BONDING_CURVE"}           # pumpswap pool + the pump.fun curve
    n1 = con.execute("SELECT COUNT(*) FROM bt_market_bars WHERE mint=?", (MINT,)).fetchone()[0]
    assert n1 == 38
    h1 = quality.dataset_hash(con, [MINT])
    ingest(con)                                                                          # same bytes again
    ingest(con, later_s=86400.0)                                                         # same bytes seen a day later: not a revision
    assert con.execute("SELECT COUNT(*) FROM bt_market_bars WHERE mint=?", (MINT,)).fetchone()[0] == n1
    assert quality.dataset_hash(con, [MINT]) == h1
    rows = con.execute("SELECT start, end, available_at, quality_flags FROM bt_market_bars WHERE mint=? ORDER BY start", (MINT,)).fetchall()
    assert all(r["available_at"] >= r["end"] + gecko.PROVIDER_LAG_S for r in rows)        # never knowable before close + provider lag
    assert all("BACKFILLED" in r["quality_flags"] for r in rows)                          # fetched long after the fact, disclosed
    cut = rows[10]["available_at"]
    assert quality.dataset_hash(con, [MINT], cutoff=cut) != h1                           # a study at that cutoff sees fewer bars
    vis = store.bars_asof(con, chain="solana", mint=MINT, pool_address=POOL, tf=3600, cutoff=cut)
    assert len(vis) == 11 and all(b["available_at"] <= cut for b in vis)


def test_collapse_is_kept_not_dropped(con):
    ingest(con)
    hi = con.execute("SELECT MAX(h) FROM bt_market_bars WHERE mint=?", (MINT,)).fetchone()[0]
    last = con.execute("SELECT c FROM bt_market_bars WHERE mint=? ORDER BY start DESC LIMIT 1", (MINT,)).fetchone()[0]
    assert last / hi < 0.001                                                              # a 99.9%+ collapse stays in the corpus


def test_pool_not_valid_before_it_existed(con):
    ingest(con)
    created = con.execute("SELECT MIN(pool_created_at) FROM bt_pool_versions WHERE mint=?", (MINT,)).fetchone()[0]
    assert store.pools_valid_at(con, chain="solana", mint=MINT, cutoff=created - 1) == []
    assert {p["pool_address"] for p in store.pools_valid_at(con, chain="solana", mint=MINT, cutoff=created + 3600)} >= {POOL}
