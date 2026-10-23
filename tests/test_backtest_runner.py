"""Phase 10: research runner on a small real corpus (the collapsed-token fixture) with restart recovery."""
import json
from pathlib import Path

import pytest

from memelab.backtest import store
from memelab.backtest.engine import EngineConfig
from memelab.backtest import runner
from memelab.backtest.sources import corpus, gecko

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
    monkeypatch.setattr(runner, "RUNS_DIR", tmp_path / "runs")
    c = store.connect(tmp_path / "bt.sqlite")
    b = gecko.Budget(max_calls=10, min_spacing_s=0.0)
    gecko.fetch_pools(c, MINT, b, replay, observed_at=MAN["files"]["gt_pools_3GVSN8.json"]["observed_at"])
    gecko.fetch_ohlcv(c, MINT, POOL, b, replay, observed_at=MAN["files"]["gt_ohlcv_3GVSN8.json"]["observed_at"])
    bars = c.execute("SELECT start FROM bt_market_bars WHERE mint=? ORDER BY start", (MINT,)).fetchall()
    for r in bars:                                                  # a flat SOL/USD reference series covering the token's life
        store.record_bar(c, chain="solana", mint=corpus.SOL_MINT, pool_address=corpus.SOL_USDC_POOL, tf=3600, start=r["start"], o=150, h=150, l=150,
                         c=150, volume_usd=1e6, observed_at=MAN["files"]["gt_ohlcv_3GVSN8.json"]["observed_at"], provider="test")
    t_lab = 1791547052.132                                          # the lab's real record time for this token (2026-10-09 11:57Z)
    store.record_universe_member(c, universe_id="u", chain="solana", mint=MINT, basis="THESIS", entered_at=t_lab, status_at_entry="ENTRY CONDITIONS MET",
                                 score_at_entry=70, fatal_flags=[], snapshot={"liquidity": 150000.0, "price": 0.0114}, committed_by=t_lab + 900)
    c.commit()
    yield c
    c.close()


def test_runner_replays_real_bars_and_recovers_on_restart(con):
    cfg = EngineConfig(sol_usd_default=None)
    a = runner.run(con, "LAB_STATUS", cfg=cfg, universe_id="u")
    assert a["cache"] == "MISS" and a["tokens"] == 1 and a["n_trades"] == 1
    t = a["trades"][0]
    assert t["entry_time"] >= 1791547052.132                        # never before the lab knew the token
    assert t["ret"] < -0.9                                          # the real collapse is in the ledger, not dropped
    b = runner.run(con, "LAB_STATUS", cfg=cfg, universe_id="u")     # restart: same inputs
    assert b["cache"] == "HIT" and b["ledger_hash"] == a["ledger_hash"]
    assert con.execute("SELECT COUNT(*) FROM bt_run_results").fetchone()[0] == 1
    c = runner.run(con, "LAB_STATUS", cfg=cfg, universe_id="u", thesis_known_at="committed")
    assert c["run_id"] != a["run_id"]                               # a different known-at rule is a different experiment
    assert c["trades"][0]["entry_time"] >= 1791547052.132 + 900


def test_runner_refuses_fees_without_a_sol_price(con):
    con.execute("PRAGMA foreign_keys=OFF")
    res = runner.run(con, "LAB_STATUS", cfg=EngineConfig(), universe_id="u", until=1791547052.132 + 86400, save=False)
    assert res["n_trades"] == 1                                     # SOL bars present: fee priced from the series
    fresh = runner.sol_usd_series(con, max_age_s=1.0)
    assert fresh(1791547052.132 + 1800) is None                     # stale reference price is refused, not reused


def test_runner_uses_first_bar_versions_never_later_revisions(con):
    first = con.execute("SELECT start, c, observed_at FROM bt_market_bars WHERE mint=? ORDER BY start LIMIT 1 OFFSET 5", (MINT,)).fetchone()
    store.record_bar(con, chain="solana", mint=MINT, pool_address=POOL, tf=3600, start=first["start"], o=1, h=9, l=1, c=9, volume_usd=1,
                     observed_at=first["observed_at"] + 86400, provider="geckoterminal")      # a provider revision seen a day later
    con.commit()
    bars = runner._first_versions(con, MINT, POOL)
    assert next(b for b in bars if b.start == first["start"]).c == first["c"]


def test_package_hash_changes_with_any_source_change(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    h1 = store.package_hash(tmp_path)
    (tmp_path / "a.py").write_text("x = 2\n")
    assert store.package_hash(tmp_path) != h1
