"""Phase 16 re-run after repair pass 3 (c42045b): attacks on pass 3, written by the reviewer.
Run from the repo root: python3 -m pytest audits/backtesting/testing/test_p16r3_repair_attacks.py -v -p no:cacheprovider
Tests named in RESIDUAL_TESTS fail on purpose on c42045b (E2E_RESULTS.md, "Re-run after repair pass 3"); the rest pass."""
from __future__ import annotations

import gc
import multiprocessing as mp
import sqlite3
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from memelab.backtest import report, store, stress as S  # noqa: E402
from memelab.backtest.sources import webcapture  # noqa: E402

RESIDUAL_TESTS = {
    "test_r3_guard_alternating_divergence": "N3c: a basis pool that leaves the market only every other hour is never refused (no two consecutive hours apart)",
    "test_r3_guard_sparse_real_market": "N3c: a real market that trades every other hour never shares two consecutive hours with the basis, so a persistent gap is never refused",
    "test_r3_guard_three_pools_real_market_split_across_two_pools": "N3c: two real pools that trade in alternate hours are each compared with the basis alone, so neither has two adjacent hours apart",
    "test_r3_redaction_hex_and_secret_key_shaped_values": "N4d: 40/64-hex values and 64-byte base58 values are exempt as digests or signatures even right after Bearer, secret, token or private key",
    "test_r3_redaction_context_word_without_separator": "N4e: a 32-hex key after 'X-API-KEY header value' (credential word not directly before the value) is echoed",
    "test_r3_redaction_false_positives_after_credential_words": "N4f: ordinary 16+ character words or timestamps after key, token or auth are removed",
    "test_r3_cohort_cache_in_memory_id_reuse": "C3: the in-memory cache key is id(con); a later in-memory connection can reuse the id and get another database's cohort",
    "test_r3_report_markdown_discloses_cohort_bias_and_censored_windows": "N8: the Markdown report calls every measured cohort window a complete case and never shows selection_bias_risk",
}
T0 = 1_800_000_000.0
H = 3600.0
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58encode(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    s = ""
    while n:
        n, r = divmod(n, 58)
        s = B58[r] + s
    return "1" * (len(b) - len(b.lstrip(b"\0"))) + s


@pytest.fixture
def con(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RAW_DIR", tmp_path / "raw")
    S._COHORT_CACHE.clear()
    c = store.connect(tmp_path / "bt.sqlite")
    yield c
    c.close()
    S._COHORT_CACHE.clear()


def member(con, mint, status, t):
    store.record_universe_member(con, universe_id="lab_state_history", chain="solana", mint=mint, basis="THESIS", entered_at=t, status_at_entry=status,
                                 snapshot={"liquidity": 100_000.0, "price": 1.0})


def pool(con, mint, addr, created):
    store.record_pool_version(con, chain="solana", pool_address=addr, mint=mint, pool_type="CPMM", observed_at=created + 60, source="test", dex="pumpswap",
                              pool_created_at=created, available_at=created + 60)


def bar(con, mint, addr, start, o, c, v):
    store.record_bar(con, chain="solana", mint=mint, pool_address=addr, tf=3600, start=start, o=o, h=max(o, c), l=min(o, c), c=c, volume_usd=v,
                     observed_at=start + H + 60, provider="test")


def wash_world(con, real_hours, wash_close, n=30):
    """Basis = wash pool (more volume before the decision). The real pool is flat at 1.00 in `real_hours`."""
    for k in range(n):
        m = f"W{k:02d}"
        member(con, m, "WATCH", T0)
        pool(con, m, f"R{m}", T0 - 3 * 86400)
        pool(con, m, f"X{m}", T0 - 3 * 86400)
        for i in range(-24, 24):
            if i < 0 or i in real_hours:
                bar(con, m, f"R{m}", T0 + i * H, 1.0, 1.0, 2000.0)
            c = 1.0 if i < 0 else wash_close(i)
            bar(con, m, f"X{m}", T0 + i * H, 1.0 if i <= 0 else wash_close(i - 1), c, 50000.0)
    con.commit()
    return S.empirical_cohort(con, "WATCH", min_n=30, asof=T0 + 10 * 86400)


# ---------------------------------------------------------------- persistence-rule edge cases (G02)

def test_r3_guard_steady_divergence_is_refused(con):
    c = wash_world(con, set(range(24)), lambda i: max(0.05, 1.0 - 0.04 * (i + 1)))
    assert c["tier"] == "INSUFFICIENT_HISTORY" and c["pool_disagreement_removed"] == 30 and c["selection_bias_risk"]


def test_r3_guard_alternating_divergence(con):
    """The wash pool prints at the market (1.00) in even hours and drifts down in odd hours, so the last hour (23) is
    off the market: never two consecutive hours apart, and the window's last close is the wash price."""
    c = wash_world(con, set(range(24)), lambda i: 1.0 if i % 2 == 0 else max(0.05, 1.0 - 0.04 * (i + 1)))
    assert c["tier"] != "HISTORICAL_COHORT" or c["ret_p10_p50_p90"][1] > -0.5, c


def test_r3_guard_sparse_real_market(con):
    """The real market trades every other hour (flat); the wash basis collapses every hour."""
    c = wash_world(con, set(range(0, 24, 2)), lambda i: max(0.05, 1.0 - 0.04 * (i + 1)))
    assert c["tier"] != "HISTORICAL_COHORT" or c["ret_p10_p50_p90"][1] > -0.5, c


def _three_pool_world(con, basis_close, side_pools, n=30):
    """Basis pool B (largest volume before the decision, closes basis_close(i) after it); `side_pools` maps a pool name
    to (hours it trades after the decision, close(i)). Every pool trades at 1.00 in the 24 hours before the decision."""
    for k in range(n):
        m = f"Q{k:02d}"
        member(con, m, "WATCH", T0)
        for name in ("B", *side_pools):
            pool(con, m, f"{name}{m}", T0 - 3 * 86400)
        for i in range(-24, 24):
            bar(con, m, f"B{m}", T0 + i * H, 1.0, 1.0 if i < 0 else basis_close(i), 50000.0)
            for name, (hours, close) in side_pools.items():
                if i < 0 or i in hours:
                    bar(con, m, f"{name}{m}", T0 + i * H, 1.0, 1.0 if i < 0 else close(i), 2000.0)
    con.commit()
    return S.empirical_cohort(con, "WATCH", min_n=30, asof=T0 + 10 * 86400)


def test_r3_guard_three_pools_real_market_split_across_two_pools(con):
    """Wash basis collapses every hour; the real market is flat at 1.00 but split: R1 trades in even hours, R2 in odd hours."""
    c = _three_pool_world(con, lambda i: max(0.05, 1.0 - 0.04 * (i + 1)),
                          {"R1": (set(range(0, 24, 2)), lambda i: 1.0), "R2": (set(range(1, 24, 2)), lambda i: 1.0)})
    assert c["tier"] != "HISTORICAL_COHORT" or c["ret_p10_p50_p90"][1] > -0.5, c


def test_r3_guard_three_pools_one_off_market_side_pool_is_refused_and_disclosed(con):
    """Real basis and a real side pool agree at 1.00; a third pool prints 0.40 all day. Fail-closed: every window is
    refused, and the count and the flag say so (no wrong number, no silent loss)."""
    c = _three_pool_world(con, lambda i: 1.0, {"R1": (set(range(24)), lambda i: 1.0), "Z": (set(range(24)), lambda i: 0.4)})
    assert c["tier"] == "INSUFFICIENT_HISTORY" and c["pool_disagreement_removed"] == 30 and c["selection_bias_risk"], c


def test_r3_guard_gap_across_a_missing_hour_still_refused(con):
    """Real pool missing every third hour: runs of two consecutive shared hours remain, so the gap is caught."""
    c = wash_world(con, {i for i in range(24) if i % 3 != 2}, lambda i: max(0.05, 1.0 - 0.04 * (i + 1)))
    assert c["tier"] == "INSUFFICIENT_HISTORY" and c["pool_disagreement_removed"] == 30


def test_r3_rug_with_a_two_hour_stale_side_pool_is_disclosed(con):
    """30 flat tokens and 1 rug whose side pool keeps printing the pre-crash price for two hours: refused (persistent
    gap), and the removal is disclosed in pool_disagreement_removed even below the 5% flag."""
    for k in range(31):
        m = f"T{k:02d}"
        member(con, m, "WATCH", T0)
        pool(con, m, f"M{m}", T0 - 3 * 86400)
        pool(con, m, f"S{m}", T0 - 3 * 86400)
        for i in range(-3, 24):
            if k < 30:
                bar(con, m, f"M{m}", T0 + i * H, 1.0, 1.0, 1000.0)
            else:
                bar(con, m, f"M{m}", T0 + i * H, 1.0 if i <= 3 else 0.01, 1.0 if i < 3 else 0.01, 1000.0)
                if i <= 4:
                    bar(con, m, f"S{m}", T0 + i * H, 1.0, 0.98 if i >= 3 else 1.0, 100.0)
    con.commit()
    c = S.empirical_cohort(con, "WATCH", min_n=30, asof=T0 + 10 * 86400)
    assert c["pool_disagreement_removed"] == 1 and c["n"] == 30


# ---------------------------------------------------------------- report disclosure of the cohort (G06)

def test_r3_report_markdown_discloses_cohort_bias_and_censored_windows(con):
    """30 tokens trade flat for the whole window, 15 stop trading after 4 hours (CENSORED, counted at the last price)
    and 15 never traded (not measurable). The cohort is flagged selection-biased (25% unmeasured) with 45 measured, 30
    complete. The per-token Markdown report must not call 45 windows complete and must show the bias flag."""
    for k in range(60):
        m = f"C{k:02d}"
        member(con, m, "WATCH", T0)
        if k >= 45:
            continue
        pool(con, m, f"P{m}", T0 - 86400)
        for i in (range(-2, 24) if k < 30 else range(-2, 4)):
            bar(con, m, f"P{m}", T0 + i * H, 1.0, 1.0 if k < 30 else 0.2, 1000.0)
    con.commit()
    coh = S.empirical_cohort(con, "WATCH", min_n=30, asof=T0 + 10 * 86400)
    assert coh["tier"] == "HISTORICAL_COHORT" and coh["n"] == 45 and coh["n_complete"] == 30 and coh["selection_bias_risk"], coh
    a = {"chain": "solana", "mint": "C00", "as_of": T0 + 10 * 86400, "state": "PARTIAL_WITH_LIMITATIONS", "tier": "HISTORICAL_COHORT",
         "stress": {"historical_evidence": coh, "decision": "INCONCLUSIVE"}}
    doc = report.build(a, lab={"score": 60, "status": "WATCH", "fatal_flags": []}, shared={})
    assert doc["historical_evidence"]["cohort"]["selection_bias_risk"] is True          # the JSON document carries the flag
    md = report.render_md(doc)
    line = next(x for x in md.splitlines() if x.startswith("Cohort of past tokens"))
    assert "45 complete cases" not in line and "bias" in md.lower(), line


# ---------------------------------------------------------------- redaction (G39)

def test_r3_redaction_hex_and_secret_key_shaped_values():
    hex64 = "9f86d081" * 8                                   # 64-hex secret shape (HMAC secrets, many API keys)
    hex40 = "e4c1a0b2" * 5                                   # 40-hex token shape (legacy personal access tokens)
    fake_secret_key = b58encode(bytes([7]) * 64)                # FAKE: base58 of 64 bytes of 0x07, the shape of a Solana secret key
    texts = [f"Authorization: Bearer {hex64}", f"HMAC secret {hex64} rejected", f"token {hex40} expired", f"private key {fake_secret_key} refused"]
    leaked = [t[:40] for t, s in zip(texts, (hex64, hex64, hex40, fake_secret_key)) if s in (webcapture.redact_text(t) or "")]
    assert not leaked, leaked


def test_r3_redaction_context_word_without_separator():
    hex32 = "a0b1" * 8
    t = f"provider rejected the X-API-KEY header value {hex32}"
    assert hex32 not in (webcapture.redact_text(t) or "")


def test_r3_redaction_false_positives_after_credential_words():
    t = "missing key published_time_field_value; token expired_at_2026-10-23T12:00:00Z; auth required_for_this_endpoint"
    r = webcapture.redact_text(t) or ""
    assert all(w in r for w in ("published_time_field_value", "expired_at_2026-10-23T12:00:00Z", "required_for_this_endpoint")), r


def test_r3_redaction_keeps_public_identifiers_and_removes_prefixed_keys():
    mint = "98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump"
    sha = "5f4ce7239eb4f0b03dfccf01205c59aee855b224653d42fbeae52da0e8dc39b1"
    key = "fc-" + "ab" * 16
    r = webcapture.redact_text(f"token {mint} hash {sha} used key {key}") or ""
    assert mint in r and sha in r and key not in r, r


# ---------------------------------------------------------------- cohort cache key (C3)

def _mem_cohort(close):
    c = store.connect(":memory:")
    for k in range(30):
        m = f"MEM{k:02d}"
        member(c, m, "WATCH", T0)
        pool(c, m, f"P{m}", T0 - 86400)
        for i in range(-2, 24):
            bar(c, m, f"P{m}", T0 + i * H, 1.0, close, 1000.0)
    c.commit()
    return c


def test_r3_cohort_cache_in_memory_id_reuse():
    S._COHORT_CACHE.clear()
    seen = []
    for attempt in range(20):
        a = _mem_cohort(1.0)
        ra = S.empirical_cohort(a, "WATCH", asof=T0 + 5 * 86400)
        ida = id(a)
        a.close(); del a; gc.collect()
        b = _mem_cohort(0.5)                                     # a different database with the same row ids
        rb = S.empirical_cohort(b, "WATCH", asof=T0 + 5 * 86400)
        same_id = id(b) == ida
        seen.append(same_id)
        b.close(); del b; gc.collect()
        if same_id:
            assert rb["ret_p10_p50_p90"][1] != ra["ret_p10_p50_p90"][1], f"attempt {attempt}: reused id served the other database's cohort"
            return
    pytest.skip(f"id() was not reused in 20 attempts ({sum(seen)})")


# ---------------------------------------------------------------- connect retry (D6 follow-up)

def _connect_at(path, start_at, q):
    while time.time() < start_at:
        time.sleep(0.001)
    t0 = time.time()
    try:
        store.connect(path).close()
        q.put(("OK", time.time() - t0))
    except Exception as e:  # noqa: BLE001
        q.put((f"{type(e).__name__}: {e}", time.time() - t0))


@pytest.mark.parametrize("round_", range(5))
def test_r3_fresh_database_burst_repeated(tmp_path, round_):
    ctx = mp.get_context("fork")
    q = ctx.Queue()
    db = tmp_path / f"fresh{round_}" / "bt.sqlite"
    start_at = time.time() + 1.5
    ps = [ctx.Process(target=_connect_at, args=(str(db), start_at, q)) for _ in range(16)]
    for p in ps:
        p.start()
    got = [q.get(timeout=120) for _ in ps]
    for p in ps:
        p.join(timeout=30)
    assert all(g[0] == "OK" for g in got), got
    assert max(g[1] for g in got) < 15, got
    assert sqlite3.connect(db).execute("SELECT COUNT(*) FROM bt_schema_migrations").fetchone()[0] == 1


def test_r3_connect_to_an_existing_database_is_not_blocked_by_a_writer(tmp_path):
    db = tmp_path / "bt.sqlite"
    store.connect(db).close()
    holder = sqlite3.connect(db)
    holder.execute("BEGIN IMMEDIATE")
    try:
        t0 = time.time()
        store.connect(db).close()
        assert time.time() - t0 < 2.0
    finally:
        holder.rollback()
        holder.close()


def test_r3_connect_gives_up_on_a_non_lock_error(tmp_path):
    p = tmp_path / "not_a_db.sqlite"
    p.write_bytes(b"this is not a sqlite database" * 100)
    t0 = time.time()
    with pytest.raises(sqlite3.DatabaseError):
        store.connect(p)
    assert time.time() - t0 < 2.0
