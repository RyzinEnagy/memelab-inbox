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


def test_pool_basis_is_chosen_with_bars_known_at_the_decision(con):
    """Phase 16 M16-5: a pool that only traded later (and was listed earlier) must not become the basis in hindsight."""
    late = "LATEPooLaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    store.record_pool_version(con, chain="solana", pool_address=late, mint=MINT, pool_type="CPMM", observed_at=1791400060.0, source="test",
                              dex="pumpswap", pool_created_at=1791400000.0, available_at=1791400060.0)
    t_lab = 1791547052.132
    for i in range(5):
        s = (int(t_lab // 3600) + 72 + i) * 3600.0
        store.record_bar(con, chain="solana", mint=MINT, pool_address=late, tf=3600, start=s, o=99.0, h=99.0, l=99.0, c=99.0, volume_usd=1e9,
                         observed_at=s + 4000, provider="test")
    con.commit()
    toks, _ = runner.build_tokens(con, "u")
    assert toks and all(b.o != 99.0 for b in toks[0].bars)


def _run_in_child(db, runs_dir, raw_dir, start_at, q):
    import time as _t
    store.RAW_DIR = raw_dir
    runner.RUNS_DIR = runs_dir
    while _t.time() < start_at:
        _t.sleep(0.001)
    try:
        c = store.connect(db)
        r = runner.run(c, "LAB_STATUS", universe_id="u", cfg=EngineConfig(sol_usd_default=None))
        c.close()
        q.put(r["cache"])
    except Exception as e:  # noqa: BLE001
        q.put(f"{type(e).__name__}: {e}")


def test_concurrent_identical_runs_store_one_result(con, tmp_path):
    """Phase 16 N6: three identical runs at once store one result row; the others return it."""
    import multiprocessing as mp
    import sys
    import time as _t
    if sys.platform == "win32":
        pytest.skip("fork start method")
    db = con.execute("PRAGMA database_list").fetchone()[2]
    con.commit()
    ctx = mp.get_context("fork")
    q = ctx.Queue()
    start_at = _t.time() + 1.5
    ps = [ctx.Process(target=_run_in_child, args=(db, tmp_path / "runs", tmp_path / "raw", start_at, q)) for _ in range(3)]
    for p in ps:
        p.start()
    got = [q.get(timeout=120) for _ in ps]
    for p in ps:
        p.join(timeout=30)
    assert all(g in ("MISS", "HIT", "HIT_AFTER_CONCURRENT_RUN") for g in got), got
    rows = con.execute("SELECT run_id, COUNT(*) n FROM bt_run_results GROUP BY run_id").fetchall()
    assert rows and all(r["n"] == 1 for r in rows)


def test_a_run_finished_meanwhile_by_another_process_is_not_stored_twice(con, monkeypatch):
    """Deterministic form of N6: another writer stores the same run while this one is computing."""
    import sqlite3
    from memelab.backtest import engine as E
    db = con.execute("PRAGMA database_list").fetchone()[2]
    real_run = E.Engine.run

    def slow_run(self, *a, **k):
        res = real_run(self, *a, **k)
        rid = con.execute("SELECT run_id FROM bt_experiment_runs ORDER BY id DESC LIMIT 1").fetchone()[0]
        other = sqlite3.connect(db)
        other.execute("INSERT INTO bt_run_results(run_id, status, result_json, result_hash, created_at) VALUES (?,?,?,?,?)",
                      (rid, "COMPLETE", json.dumps({"n_trades": -1, "from": "other process"}), "h", 1.0))
        other.commit(); other.close()
        return res
    monkeypatch.setattr(runner.Engine, "run", slow_run)
    out = runner.run(con, "LAB_STATUS", universe_id="u", cfg=EngineConfig(sol_usd_default=None))
    assert out["cache"] == "HIT_AFTER_CONCURRENT_RUN" and out["from"] == "other process"
    assert con.execute("SELECT COUNT(*) FROM bt_run_results").fetchone()[0] == 1
