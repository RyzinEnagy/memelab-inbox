"""Phase 16 re-run after repair pass 1 (47a7845): attacks on the repairs themselves, written by the reviewer.
Run from the repo root: python3 -m pytest audits/backtesting/testing/test_p16r1_repair_attacks.py -v -p no:cacheprovider
Tests named in RESIDUAL_TESTS fail on purpose on 47a7845: they reproduce residual or new defects (E2E_RESULTS.md,
section "Re-run after repair pass 1"). The rest must pass."""
from __future__ import annotations

import json
import multiprocessing as mp
import sqlite3
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from memelab.backtest import outcomes as O, store, stress as S  # noqa: E402
from memelab.backtest.sources import webcapture  # noqa: E402

RESIDUAL_TESTS = {
    "test_r1_cohort_returns_keep_dead_tokens_or_flag_the_bias": "N1: complete-window-only returns drop tokens whose feed died (rugs) from the return percentiles, with no selection-bias flag",
    "test_r1_cohort_pool_choice_never_reads_after_the_assessment_time": "N2: the pool-basis search tries up to 48 h after each cohort decision, past the assessment time",
    "test_r1_cohort_basis_not_steered_by_wash_volume_on_a_thin_pool": "N3: the pool basis is the pool with most traded volume, which wash volume on a thin pool can steer",
    "test_r1_redaction_covers_bare_keys_headers_and_path_tokens": "N4: redaction covers key=value and user:password only; bare keys, Authorization headers and path tokens are echoed",
}
T0 = 1_800_000_000.0
H = 3600.0
POL = {"collectors_enabled": True, "schedules_approved": False, "maxun_adopted": False}
SECRET = "fc-" + "ab" * 16          # key-shaped placeholder (fewer than 8 distinct characters)


@pytest.fixture
def con(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RAW_DIR", tmp_path / "raw")
    c = store.connect(tmp_path / "bt.sqlite")
    yield c
    c.close()


def member(con, mint, status, t, liq=100_000.0):
    store.record_universe_member(con, universe_id="lab_state_history", chain="solana", mint=mint, basis="THESIS", entered_at=t, status_at_entry=status,
                                 snapshot={"liquidity": liq, "price": 1.0})


def pool(con, mint, addr, created):
    store.record_pool_version(con, chain="solana", pool_address=addr, mint=mint, pool_type="CPMM", observed_at=created + 60, source="test", dex="pumpswap",
                              pool_created_at=created, available_at=created + 60)


def bar(con, mint, addr, start, o, c, v, lo=None, hi=None):
    store.record_bar(con, chain="solana", mint=mint, pool_address=addr, tf=3600, start=start, o=o, h=hi or max(o, c), l=lo or min(o, c), c=c, volume_usd=v,
                     observed_at=start + H + 60, provider="test")


# ---------------------------------------------------------------- N1: survivorship in cohort returns (G06)

def test_r1_cohort_returns_keep_dead_tokens_or_flag_the_bias(con):
    """30 tokens stay flat for 24 h; 30 tokens rug to -99% in their 3rd hour and their feed stops (the usual end of a rug).
    A return distribution that silently keeps only the survivors says 'median 0%' for a cohort where half went to zero."""
    for k in range(60):
        m = f"SURV{k:02d}"
        member(con, m, "WATCH", T0)
        pool(con, m, f"P{m}", T0 - 86400)
        bar(con, m, f"P{m}", T0 - H, 1.0, 1.0, 1000.0)
        n = 24 if k < 30 else 3
        for i in range(n):
            px = 1.0 if (k < 30 or i < 2) else 0.01
            bar(con, m, f"P{m}", T0 + i * H, 1.0 if i < 3 else px, px, 1000.0)
    con.commit()
    c = S.empirical_cohort(con, "WATCH", min_n=30, asof=T0 + 10 * 86400)
    flagged = any("SELECTION" in str(k).upper() or "SURVIVOR" in str(v).upper() for k, v in c.items())
    included = c.get("ret_p10_p50_p90") is not None and c["ret_p10_p50_p90"][0] < -0.5
    assert flagged or included, c


# ---------------------------------------------------------------- N2: pool choice past the assessment time (G32)

def test_r1_cohort_pool_choice_never_reads_after_the_assessment_time(con):
    """Each cohort token has two pools that both print once at hour 23 of the window (published just after hour 24).
    At the assessment time the main pool has more volume. Pool B only becomes 'the volume pool' with bars printed
    after the assessment time. Point-in-time, the cohort must be measured on pool A (flat)."""
    t = T0
    asof = t + 24 * H + 600                                      # window closed and published; nothing later known
    for k in range(30):
        m = f"LATE{k:02d}"
        member(con, m, "WATCH", t)
        pool(con, m, f"A{m}", t - 86400)
        pool(con, m, f"B{m}", t - 86400)
        store.record_bar(con, chain="solana", mint=m, pool_address=f"A{m}", tf=3600, start=t + 23 * H, o=1.0, h=1.0, l=1.0, c=1.0, volume_usd=5000.0,
                         observed_at=t + 24 * H + 300, provider="test")
        store.record_bar(con, chain="solana", mint=m, pool_address=f"B{m}", tf=3600, start=t + 23 * H, o=1.0, h=1.0, l=0.01, c=0.01, volume_usd=100.0,
                         observed_at=t + 24 * H + 300, provider="test")
        for i in range(30, 46):                                  # pool B volume only AFTER the assessment time
            store.record_bar(con, chain="solana", mint=m, pool_address=f"B{m}", tf=3600, start=t + i * H, o=0.01, h=0.01, l=0.01, c=0.01, volume_usd=1e6,
                             observed_at=t + (i + 1) * H + 300, provider="test")
    con.commit()
    c = S.empirical_cohort(con, "WATCH", min_n=30, asof=asof)
    assert c["tier"] == "HISTORICAL_COHORT", c
    assert c["ret_p10_p50_p90"][1] > -0.05, c


# ---------------------------------------------------------------- N3: basis steered by wash volume (G02)

def test_r1_cohort_basis_not_steered_by_wash_volume_on_a_thin_pool(con):
    """Main pool: deep, flat at 1.00, $2k volume an hour. Thin pool of the same mint: $20k of wash volume an hour at a
    price that drifts to 0.05. Both pools are valid. A cohort measured on the thin pool reports a -95% median for
    tokens whose main market never moved."""
    for k in range(30):
        m = f"WASH{k:02d}"
        member(con, m, "WATCH", T0)
        pool(con, m, f"M{m}", T0 - 3 * 86400)
        pool(con, m, f"W{m}", T0 - 3 * 86400)
        for i in range(-24, 24):
            bar(con, m, f"M{m}", T0 + i * H, 1.0, 1.0, 2000.0)
            px = 1.0 if i < 0 else max(0.05, 1.0 - 0.04 * (i + 1))
            bar(con, m, f"W{m}", T0 + i * H, 1.0 if i <= 0 else max(0.05, 1.0 - 0.04 * i), px, 20000.0)
    con.commit()
    c = S.empirical_cohort(con, "WATCH", min_n=30, asof=T0 + 10 * 86400)
    assert c["ret_p10_p50_p90"][1] > -0.5, c


# ---------------------------------------------------------------- D6 under a larger burst

def _connect_at(path, start_at, q):
    while time.time() < start_at:
        time.sleep(0.001)
    try:
        store.connect(path).close()
        q.put("OK")
    except Exception as e:  # noqa: BLE001
        q.put(f"{type(e).__name__}: {e}")


def test_r1_sixteen_processes_open_a_new_database_at_once(tmp_path):
    ctx = mp.get_context("fork")
    q = ctx.Queue()
    db = tmp_path / "fresh" / "bt.sqlite"
    start_at = time.time() + 2.0
    ps = [ctx.Process(target=_connect_at, args=(str(db), start_at, q)) for _ in range(16)]
    for p in ps:
        p.start()
    got = [q.get(timeout=90) for _ in ps]
    for p in ps:
        p.join(timeout=30)
    assert got == ["OK"] * 16, got
    c = sqlite3.connect(db)
    assert c.execute("SELECT COUNT(*) FROM bt_schema_migrations").fetchone()[0] == 1


# ---------------------------------------------------------------- D7: interval check under concurrent passes

def _track_at(path, start_at, now, q):
    while time.time() < start_at:
        time.sleep(0.001)
    try:
        c = store.connect(path)
        r = O.track(c, now=now)
        c.close()
        q.put(r["status"])
    except Exception as e:  # noqa: BLE001
        q.put(f"{type(e).__name__}: {e}")


def _tracker_db(tmp_path, n=150):
    db = tmp_path / "trk.sqlite"
    c = store.connect(db)
    for k in range(n):
        m = f"TRK{k:03d}"
        member(c, m, "WATCH", T0)
        pool(c, m, f"P{m}", T0 - 86400)
        for i in range(-2, 80):
            bar(c, m, f"P{m}", T0 + i * H, 1.0, 1.0 + 0.001 * i, 100.0)
    c.commit()
    c.close()
    return db


def test_r1_concurrent_trackers_with_the_same_now_run_once(tmp_path):
    db = _tracker_db(tmp_path)
    ctx = mp.get_context("fork")
    q = ctx.Queue()
    start_at = time.time() + 2.0
    now = T0 + 10 * 86400
    ps = [ctx.Process(target=_track_at, args=(str(db), start_at, now, q)) for _ in range(4)]
    for p in ps:
        p.start()
    got = sorted(q.get(timeout=300) for _ in ps)
    for p in ps:
        p.join(timeout=30)
    assert got.count("RAN") == 1 and all(g in ("RAN", "SKIPPED_MIN_INTERVAL", "SKIPPED_BUSY") for g in got), got
    c = sqlite3.connect(db)
    assert c.execute("SELECT COUNT(*) FROM (SELECT opportunity_id, horizon_s FROM bt_outcomes GROUP BY 1, 2 HAVING COUNT(*) > 1)").fetchone()[0] == 0


def test_r1_concurrent_trackers_with_different_now_never_fork_a_window(tmp_path):
    """Two passes whose `now` differ by more than the interval both run (the interval is judged on `now`). Whatever
    interleaving happens, each (opportunity, horizon) must keep one supersede chain: no two rows naming the same prior
    row, and at most one row without a prior row."""
    db = _tracker_db(tmp_path)
    ctx = mp.get_context("fork")
    q = ctx.Queue()
    start_at = time.time() + 2.0
    ps = [ctx.Process(target=_track_at, args=(str(db), start_at, now, q)) for now in (T0 + 1.5 * 86400, T0 + 10 * 86400)]
    for p in ps:
        p.start()
    got = sorted(q.get(timeout=300) for _ in ps)
    for p in ps:
        p.join(timeout=30)
    assert all(not g.startswith(("OperationalError", "IntegrityError")) for g in got), got
    c = sqlite3.connect(db)
    forks = c.execute("SELECT COUNT(*) FROM (SELECT opportunity_id, horizon_s, supersedes_id FROM bt_outcomes GROUP BY 1, 2, 3 HAVING COUNT(*) > 1)").fetchone()[0]
    assert forks == 0, (got, forks)


# ---------------------------------------------------------------- N4: redaction gaps (G39)

def test_r1_redaction_covers_bare_keys_headers_and_path_tokens(con):
    res = [{"url": "https://solana.com/news/a", "status": 401, "view": None, "error": f"401 Unauthorized: invalid key {SECRET}"},
           {"url": "https://solana.com/news/b", "status": 401, "view": None, "error": f"request failed with headers {{'Authorization': 'Bearer {SECRET}'}}"},
           {"url": f"https://solana.com/news/c/{SECRET}/x", "status": 500, "view": None, "error": "upstream error"},
           {"url": "https://solana.com/news/d", "status": 403, "view": None, "error": f'{{"error": "forbidden", "api_key": "{SECRET}"}}'}]
    out = webcapture.ingest_batch(con, "project_catalyst_watch", "FIRECRAWL", res, captured_at=T0, policy=POL)
    dump = json.dumps(out)
    leaks = [i for i, r in enumerate(out["rows"]) if SECRET in json.dumps(r)]
    assert SECRET not in dump, f"rows still carrying the credential: {leaks}"


def test_r1_redaction_covers_query_userinfo_and_common_names(con):
    names = ("api_key", "apikey", "api-key", "token", "access_token", "key", "secret", "client_secret", "password", "auth")
    res = [{"url": f"https://solana.com/news/q{i}?{n}={SECRET}", "status": 200, "view": {"meta": {"og:title": "t"}}} for i, n in enumerate(names)]
    res.append({"url": f"https://user:{SECRET}@solana.com/news/u", "status": 401, "view": None, "error": f"failed https://user:{SECRET}@solana.com/news/u"})
    out = webcapture.ingest_batch(con, "project_catalyst_watch", "FIRECRAWL", res, captured_at=T0, policy=POL)
    assert SECRET not in json.dumps(out)
    assert SECRET not in json.dumps([dict(r) for r in con.execute("SELECT * FROM bt_capture_provenance")])
