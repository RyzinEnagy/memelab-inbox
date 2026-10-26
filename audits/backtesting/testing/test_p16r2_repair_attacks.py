"""Phase 16 re-run after repair pass 2 (0e63563): attacks on pass 2, written by the reviewer.
Run from the repo root: python3 -m pytest audits/backtesting/testing/test_p16r2_repair_attacks.py -v -p no:cacheprovider
Tests named in RESIDUAL_TESTS fail on purpose on 0e63563 (E2E_RESULTS.md, "Re-run after repair pass 2"); the rest pass."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from memelab.backtest import assess, store, stress as S  # noqa: E402
from memelab.backtest.sources import webcapture  # noqa: E402

RESIDUAL_TESTS = {
    "test_r2_guard_is_evaded_when_wash_volume_exceeds_twenty_times_the_real_pool": "N3b: the disagreement guard ignores any pool under 5% of the basis volume, so 20x wash volume evades it",
    "test_r2_guard_does_not_hide_a_rug_below_the_bias_flag": "N7: a side pool's pre-crash close in the crash hour marks a real rug NOT_OBSERVABLE; under 20% unmeasured, no flag",
    "test_r2_redaction_catches_bare_short_keys": "N4b: bare 32-39 character keys and a Telegram token secret are not redacted",
    "test_r2_redaction_keeps_useful_public_text": "N4c: hashes, tx signatures and words after 'Basic' are removed from error text (false positives)",
    "test_r2_cached_cohort_cannot_be_poisoned_by_a_caller": "C1: the cohort cache returns a shallow copy, so a caller's edit of a nested list changes later answers",
    "test_r2_assessment_cache_never_serves_a_stale_cohort_after_new_pool_records": "C2: the FAST request key's data revision omits bt_pool_versions, which the cohort now reads",
}
T0 = 1_800_000_000.0
H = 3600.0
POL = {"collectors_enabled": True, "schedules_approved": False, "maxun_adopted": False}
INBOX = ROOT / "data" / "inbox"
IDS = ["disc01", "s2_01", "deep01a"]
PAID = "98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump"


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


def bar(con, mint, addr, start, o, c, v, lo=None, hi=None):
    store.record_bar(con, chain="solana", mint=mint, pool_address=addr, tf=3600, start=start, o=o, h=hi or max(o, c), l=lo or min(o, c), c=c, volume_usd=v,
                     observed_at=start + H + 60, provider="test")


# ---------------------------------------------------------------- N3b: guard thresholds (G02)

def test_r2_guard_is_evaded_when_wash_volume_exceeds_twenty_times_the_real_pool(con):
    """Same world as the pass-1 wash test, with wash volume 25x the real pool's (the real pool is 4% of it, under the
    guard's 5% floor). The guard then ignores the real market and the cohort is measured on the wash pool."""
    for k in range(30):
        m = f"WASH{k:02d}"
        member(con, m, "WATCH", T0)
        pool(con, m, f"M{m}", T0 - 3 * 86400)
        pool(con, m, f"W{m}", T0 - 3 * 86400)
        for i in range(-24, 24):
            bar(con, m, f"M{m}", T0 + i * H, 1.0, 1.0, 2000.0)
            px = 1.0 if i < 0 else max(0.05, 1.0 - 0.04 * (i + 1))
            bar(con, m, f"W{m}", T0 + i * H, 1.0 if i <= 0 else max(0.05, 1.0 - 0.04 * i), px, 50000.0)
    con.commit()
    c = S.empirical_cohort(con, "WATCH", min_n=30, asof=T0 + 10 * 86400)
    assert c["tier"] != "HISTORICAL_COHORT" or c["ret_p10_p50_p90"][1] > -0.5, c


def test_r2_guard_refuses_the_pass1_wash_world(con):
    """The builder's fail-closed rule on the pass-1 world (real pool 10% of the wash volume): not measured, flagged."""
    for k in range(30):
        m = f"WSH{k:02d}"
        member(con, m, "WATCH", T0)
        pool(con, m, f"M{m}", T0 - 3 * 86400)
        pool(con, m, f"W{m}", T0 - 3 * 86400)
        for i in range(-24, 24):
            bar(con, m, f"M{m}", T0 + i * H, 1.0, 1.0, 2000.0)
            px = 1.0 if i < 0 else max(0.05, 1.0 - 0.04 * (i + 1))
            bar(con, m, f"W{m}", T0 + i * H, 1.0 if i <= 0 else max(0.05, 1.0 - 0.04 * i), px, 20000.0)
    con.commit()
    c = S.empirical_cohort(con, "WATCH", min_n=30, asof=T0 + 10 * 86400)
    assert c["tier"] == "INSUFFICIENT_HISTORY" and c["selection_bias_risk"] and c["missing_reasons"].get("POOL_DISAGREEMENT") == 30


# ---------------------------------------------------------------- N7: guard hides real rugs (G06)

def test_r2_guard_does_not_hide_a_rug_below_the_bias_flag(con):
    """30 flat tokens and 6 rugs. In each rug's crash hour the main pool closes at 0.01; a side pool (10% of the
    volume) last traded early in that hour at 0.98 and never again: an hourly close is the last trade, so the two
    closes legitimately differ. The guard marks the rug NOT_OBSERVABLE; 6 of 36 unmeasured stays under the 20% flag,
    so the cohort's returns and worst drops silently lose every rug."""
    for k in range(36):
        m = f"RUG{k:02d}"
        member(con, m, "WATCH", T0)
        pool(con, m, f"M{m}", T0 - 3 * 86400)
        pool(con, m, f"S{m}", T0 - 3 * 86400)
        for i in range(-3, 24):
            if k < 30:
                bar(con, m, f"M{m}", T0 + i * H, 1.0, 1.0, 1000.0)
            else:
                o = 1.0 if i <= 3 else 0.01
                c = 1.0 if i < 3 else 0.01
                bar(con, m, f"M{m}", T0 + i * H, o, c, 1000.0 if i != 3 else 20000.0)
                if i <= 3:
                    bar(con, m, f"S{m}", T0 + i * H, 1.0, 0.98 if i == 3 else 1.0, 100.0 if i < 3 else 2000.0)
    con.commit()
    c = S.empirical_cohort(con, "WATCH", min_n=30, asof=T0 + 10 * 86400)
    rugs_seen = c.get("ret_p10_p50_p90") is not None and c["ret_p10_p50_p90"][0] < -0.5
    assert rugs_seen or c["selection_bias_risk"], c


# ---------------------------------------------------------------- N4b / N4c: redaction (G39)

def test_r2_redaction_catches_bare_short_keys(con):
    hex32 = "a0b1" * 8                                       # 32-hex API key shape (Birdeye, Infura and others)
    tg = "123456789:AA" + "ab" * 16 + "a"                    # Telegram bot token shape (placeholder characters)
    alnum34 = "Q7" * 17                                      # 34-character alphanumeric key shape (Etherscan and others)
    texts = [f"401 Unauthorized for key {hex32}", f"bot token {tg} rejected", f"provider refused credential {alnum34}"]
    leaked = [t for t in texts if any(s in (webcapture.redact_text(t) or "") for s in (hex32, tg.split(":")[1], alnum34))]
    assert not leaked, leaked


def test_r2_redaction_keeps_useful_public_text():
    sha = "5f4ce7239eb4f0b03dfccf01205c59aee855b224653d42fbeae52da0e8dc39b1"
    txsig = "4RzJen" + "3x" * 41                               # 88-character base58 transaction-signature shape (public)
    mint = "98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump"
    t = f"content hash {sha} did not match; tx {txsig} for mint {mint}; HTTP 401 Basic authentication required"
    r = webcapture.redact_text(t) or ""
    kept = {"hash": sha in r, "tx": txsig in r, "mint": mint in r, "basic_word": "authentication" in r}
    assert all(kept.values()), (kept, r)


def test_r2_redaction_pass2_claims_hold(con):
    """The pass-2 claims that do hold: Bearer/Basic values, name=value, JSON pairs, user:password, prefixes, UUIDs,
    long runs, path tokens, and public base58 addresses kept."""
    key = "fc-" + "ab" * 16
    uuid = "a0a0a0a0-b1b1-c2c2-d3d3-e4e4e4e4e4e4"
    long = "Zz9" * 15
    cases = [f"Authorization: Bearer {key}", f"Basic {long}", f"api_key={key}&x=1", f'{{"client_secret": "{long}"}}',
             f"https://u:{long}@solana.com/news/x", f"key {key}", f"helius {uuid}", f"run {long}", f"https://solana.com/news/{long}/x"]
    for t in cases:
        r = webcapture.redact_text(t) or ""
        assert key not in r and uuid not in r and long not in r, (t, r)
    mint = "98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump"
    assert mint in (webcapture.redact_text(f"mint {mint} not found") or "")
    with pytest.raises(webcapture.OffAllowlist):
        webcapture.allowed("project_catalyst_watch", f"https://solana.com/news/{long}")


# ---------------------------------------------------------------- C1 / C2: cohort cache

def _flat_cohort(con, n=30, status="WATCH", t=T0, pool_records=True):
    for k in range(n):
        m = f"COH{k:02d}"
        member(con, m, status, t)
        if pool_records:
            pool(con, m, f"P{m}", t - 86400)
        for i in range(-2, 24):
            bar(con, m, f"P{m}", t + i * H, 1.0, 1.0, 1000.0)
    con.commit()


def test_r2_cached_cohort_cannot_be_poisoned_by_a_caller(con):
    _flat_cohort(con)
    a = S.empirical_cohort(con, "WATCH", asof=T0 + 5 * 86400)
    true_median = a["ret_p10_p50_p90"][1]
    a["ret_p10_p50_p90"][1] = 9.99                            # a caller edits its copy
    a["window_states"]["COMPLETE"] = -1
    b = S.empirical_cohort(con, "WATCH", asof=T0 + 5 * 86400)
    assert b["ret_p10_p50_p90"][1] == true_median and b["window_states"]["COMPLETE"] == 30, b


def test_r2_cohort_cache_follows_new_bars_universe_rows_and_pool_records(con):
    _flat_cohort(con)
    asof = T0 + 5 * 86400
    a = S.empirical_cohort(con, "WATCH", asof=asof)
    assert a["n"] == 30
    member(con, "NEWTOKEN", "WATCH", T0)                         # a new universe row
    pool(con, "NEWTOKEN", "PNEW", T0 - 86400)
    for i in range(-2, 24):
        bar(con, "NEWTOKEN", "PNEW", T0 + i * H, 1.0, 0.5, 1000.0)
    con.commit()
    b = S.empirical_cohort(con, "WATCH", asof=asof)
    assert b["n"] == 31 and b["known_tokens"] == 31
    # a backfilled bar that was public before the as-of but stored only now
    bar(con, "COH00", "PCOH00", T0 + 24 * H, 1.0, 1.0, 1.0)
    con.commit()
    c = S.empirical_cohort(con, "WATCH", asof=asof)
    assert c is not b and c["n"] == 31


@pytest.mark.skipif(not all((INBOX / f"{i}.result.json").exists() for i in IDS), reason="inbox captures not present")
def test_r2_assessment_cache_never_serves_a_stale_cohort_after_new_pool_records(con):
    """Cohort tokens whose bars have no pool record are measured from bars alone. A later pool-list refresh records
    a pool for each of them (with no bars yet): the cohort is recomputed and can no longer measure them, but the FAST
    assessment's request key only follows bars and universe rows, so asking again returns the old cohort."""
    from memelab import pipeline
    from memelab.bridge import ingest
    res = [ingest.load_result(INBOX / f"{i}.result.json") for i in IDS]
    bodies = {k: v[0] for k, v in ingest.merged_bodies(res).items()}
    t_obs = max(r.observed_at for r in res)
    r = pipeline.analyze_token(PAID, bodies, observed_at=t_obs, sol_price=120.8, persist=False)
    status = r["status"]["status"]
    early = t_obs - 10 * 86400
    for k in range(30):
        m = f"BAR{k:02d}"
        member(con, m, status, early)
        for i in range(-2, 24):
            bar(con, m, f"PB{m}", early + i * H, 1.0, 1.0, 1000.0)
    con.commit()
    pol = dict(assess.DEFAULT_POLICY, enabled=True)
    a1 = assess.attach(copy.deepcopy(r), pol, con=con, now=t_obs + 60)
    assert a1["stress"]["historical_evidence"]["n"] == 30
    for k in range(30):
        pool(con, f"BAR{k:02d}", f"PNEW{k:02d}", early - 86400)    # pool records only (the bars fetch has not run yet)
    con.commit()
    fresh = S.empirical_cohort(con, status, min_n=30, asof=float(int(r["bundle"]["observed_at"] // 3600) * 3600))
    a2 = assess.attach(copy.deepcopy(r), pol, con=con, now=t_obs + 120)
    assert a2["stress"]["historical_evidence"]["n"] == fresh["n"], (a2.get("cache"), a2["stress"]["historical_evidence"]["n"], fresh["n"])
