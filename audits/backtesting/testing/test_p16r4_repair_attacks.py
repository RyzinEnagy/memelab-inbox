"""Phase 16 re-run after repair pass 4 (7c7b582): attacks on pass 4, written by the reviewer.
Run from the repo root: python3 -m pytest audits/backtesting/testing/test_p16r4_repair_attacks.py -v -p no:cacheprovider
Tests named in RESIDUAL_TESTS fail on purpose on 7c7b582 (E2E_RESULTS.md, "Re-run after repair pass 4 (final)"); tests named in
LIMITATION_TESTS fail on purpose too and record a limitation of hourly bars that I accept when disclosed; the rest pass."""
from __future__ import annotations

import gc
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from memelab.backtest import report, store, stress as S  # noqa: E402
from memelab.backtest.sources import webcapture  # noqa: E402

RESIDUAL_TESTS = {
    "test_r4_guard_late_persistent_divergence": "N3e: a basis pool off the market for the last 7 of 24 shared hours (29%, under a third) is measured at its off-market close",
    "test_r4_guard_late_persistent_divergence_72h": "N3e: on a 72 h window, 23 consecutive off-market hours at the end (32%) are measured",
    "test_r4_guard_pools_that_never_share_an_hour": "N3d: a basis and a real pool that trade in disjoint hours are never compared",
    "test_r4_guard_decoy_pools_outvote_the_real_market": "N3f: two decoy pools that copy the basis move the median of the other pools, so the real pool's gap is ignored",
    "test_r4_redaction_32_byte_base58_secret_after_strong_words": "N4g: a 32-byte base58 value is exempt as a public address even after private key, secret, password or Bearer",
    "test_r4_redaction_underscored_or_letters_only_secret_after_strong_words": "N4h: after a space, a secret with two underscores or a letters-only password of 16+ characters is kept",
    "test_r4_redaction_url_encoded_bearer_and_short_basic": "N4i: '%' is outside the value pattern, so a URL-encoded bearer token's tail after the first %2B or %3D is kept; a short Basic value without digits is kept",
    "test_r4_cohort_cache_file_replaced_at_the_same_path":"C4: a replaced database file usually gets the same inode on ext4, so the (path, inode) key serves the old file's cohort",
}
LIMITATION_TESTS = {
    "test_r4_guard_exit_hour_print_on_the_basis": "a single off-market close in the basis pool's last hour sets the window's return; hourly bars cannot tell it from a crash in that hour (see the rug test that passes)",
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


def world(con, basis_close, basis_hours, others, hours=24, n=30, horizon_h=24):
    """Basis pool B has the most volume before the decision and trades in `basis_hours` after it, closing basis_close(i).
    `others` maps a pool name to (hours it trades after the decision, close(i)). Every pool trades at 1.00 for 24 h
    before the decision. Returns the cohort at T0 + 10 days."""
    for k in range(n):
        m = f"V{k:02d}"
        member(con, m, "WATCH", T0)
        for name in ("B", *others):
            pool(con, m, f"{name}{m}", T0 - 3 * 86400)
        for i in range(-24, hours):
            if i < 0 or i in basis_hours:
                bar(con, m, f"B{m}", T0 + i * H, 1.0, 1.0 if i < 0 else basis_close(i), 50000.0)
            for name, (hrs, close) in others.items():
                if i < 0 or i in hrs:
                    bar(con, m, f"{name}{m}", T0 + i * H, 1.0, 1.0 if i < 0 else close(i), 2000.0)
    con.commit()
    return S.empirical_cohort(con, "WATCH", horizon_h=horizon_h, min_n=30, asof=T0 + 10 * 86400)


def not_fooled(c):
    return c["tier"] != "HISTORICAL_COHORT" or c["ret_p10_p50_p90"][1] > -0.5


ALL24 = set(range(24))
FLAT = lambda i: 1.0  # noqa: E731


# ---------------------------------------------------------------- guard (G02)

def test_r4_guard_late_persistent_divergence(con):
    """Pass 3's run rule refused this window (7 consecutive hours apart); pass 4's share rule needs 8 of 24."""
    c = world(con, lambda i: 1.0 if i < 17 else 0.05, ALL24, {"R": (ALL24, FLAT)})
    assert not_fooled(c), c


def test_r4_guard_late_persistent_divergence_72h(con):
    """A 72 h window: the basis leaves the market for the last 23 hours (23 of 72 shared hours, 32%)."""
    c = world(con, lambda i: 1.0 if i < 49 else 0.05, set(range(72)), {"R": (set(range(72)), FLAT)}, hours=72, horizon_h=72)
    assert not_fooled(c), c


def test_r4_guard_pools_that_never_share_an_hour(con):
    """After the decision the basis trades in odd hours (collapsing), the real pool in even hours (flat): no shared hour."""
    c = world(con, lambda i: max(0.05, 1.0 - 0.04 * (i + 1)), set(range(1, 24, 2)), {"R": (set(range(0, 24, 2)), FLAT)})
    assert not_fooled(c), c


def test_r4_guard_decoy_pools_outvote_the_real_market(con):
    """The real pool R stays at 1.00; two thin decoy pools print the basis pool's collapsing price, so the median of the
    other pools agrees with the basis. Pass 3 compared each pool with the basis and refused the window."""
    wash = lambda i: max(0.05, 1.0 - 0.04 * (i + 1))  # noqa: E731
    c = world(con, wash, ALL24, {"R": (ALL24, FLAT), "D1": (ALL24, wash), "D2": (ALL24, wash)})
    assert not_fooled(c), c


def test_r4_guard_exit_hour_print_on_the_basis(con):
    """Limitation: the basis is at the market for 23 hours and closes at 0.05 in the last hour; the real pool stays at 1.00."""
    c = world(con, lambda i: 1.0 if i < 23 else 0.05, ALL24, {"R": (ALL24, FLAT)})
    assert not_fooled(c), c


def test_r4_rug_in_the_final_hour_is_measured(con):
    """The other side of that limitation: a real crash in the last hour, the side pool's last trade before it. Measured."""
    c = world(con, lambda i: 1.0 if i < 23 else 0.01, ALL24, {"R": (ALL24, lambda i: 1.0 if i < 23 else 0.97)})
    assert c["tier"] == "HISTORICAL_COHORT" and c["ret_p10_p50_p90"][1] < -0.9 and c["pool_disagreement_removed"] == 0, c


def test_r4_guard_pass3_shapes_still_refused(con):
    """Alternating divergence (10 of 24 apart): refused by the share rule."""
    c = world(con, lambda i: 1.0 if i % 2 == 0 else max(0.05, 1.0 - 0.04 * (i + 1)), ALL24, {"R": (ALL24, FLAT)})
    assert c["tier"] == "INSUFFICIENT_HISTORY" and c["pool_disagreement_removed"] == 30 and c["selection_bias_risk"], c


def test_r4_guard_one_junk_pool_among_two_real_side_pools_is_outvoted(con):
    """Real basis, two real side pools and one junk pool at 0.40: the median of the others is real, so the window is
    measured correctly. (One real side pool next to one junk pool is refused, fail-closed: the pass-3 file covers it.)"""
    c = world(con, FLAT, ALL24, {"R1": (ALL24, FLAT), "R2": (ALL24, FLAT), "Z": (ALL24, lambda i: 0.4)})
    assert c["tier"] == "HISTORICAL_COHORT" and abs(c["ret_p10_p50_p90"][1]) < 1e-9 and c["pool_disagreement_removed"] == 0, c


# ---------------------------------------------------------------- report (G06)

def test_r4_report_line_states_counts_flag_and_split(con):
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
    a = {"chain": "solana", "mint": "C00", "as_of": T0 + 10 * 86400, "state": "PARTIAL_WITH_LIMITATIONS", "tier": "HISTORICAL_COHORT",
         "stress": {"historical_evidence": coh, "decision": "INCONCLUSIVE"}}
    md = report.render_md(report.build(a, lab={"score": 60, "status": "WATCH", "fatal_flags": []}, shared={}))
    line = next(x for x in md.splitlines() if x.startswith("Cohort of past tokens"))
    assert "45 measured windows (30 complete, 15 cut short" in line and "of 60 tokens" in line, line
    assert "Selection-bias risk: YES (25% of measurable tokens could not be measured, 0 removed for pool disagreement)" in line, line
    assert "Complete windows only: +0.0% / +0.0% / +0.0%" in line and "NOT point-in-time" not in line, line
    assert "may be selection-biased: 25%" in md, md


def test_r4_report_survives_sparse_or_old_cohort_records():
    """Old stored cohort records (before pass 4) and empty cohorts must render without an exception."""
    base = {"evidence_class": "FACT", "state": "NONE"}
    for coh in ({"tier": "INSUFFICIENT_HISTORY", "status": "WATCH", "n": 0, "min_n": 30},
                {"tier": "INSUFFICIENT_HISTORY", "status": "WATCH", "n": 0, "n_complete": 0, "min_n": 30, "known_tokens": 0,
                 "selection_bias_risk": False, "unmeasured_share": None, "pool_disagreement_removed": 0, "point_in_time": False},
                {"tier": "HISTORICAL_COHORT", "status": "WATCH", "n": 31, "min_n": 30, "horizon_h": 24, "ret_p10_p50_p90": [-0.5, 0.0, 0.2],
                 "worst_drop_p10_p50": [-0.6, -0.1]}):
        a = {"chain": "solana", "mint": "X", "as_of": T0, "state": "PARTIAL_WITH_LIMITATIONS", "stress": {"historical_evidence": coh, "decision": "INCONCLUSIVE"}}
        md = report.render_md(report.build(a, lab={"score": 60, "status": "WATCH", "fatal_flags": []}, shared={}))
        assert "Cohort of past tokens" in md and base


# ---------------------------------------------------------------- redaction (G39)

def test_r4_redaction_32_byte_base58_secret_after_strong_words():
    seed = b58encode(bytes([9]) * 32)                       # FAKE: base58 of 32 bytes of 0x09, the shape of an ed25519 seed
    texts = [f"private key {seed} refused", f"secret {seed} rejected", f"password {seed} wrong", f"Authorization: Bearer {seed}"]
    leaked = [t.split(" ")[0] for t in texts if seed in (webcapture.redact_text(t) or "")]
    assert not leaked, leaked


def test_r4_redaction_underscored_or_letters_only_secret_after_strong_words():
    underscored = "_".join(["Q7x2" * 2, "m9K4" * 2, "z3P8" * 2, "w5" * 2])   # FAKE: 30 characters, three underscores, letters and digits
    phrase = "correct" + "horse" + "battery" + "staple"                      # FAKE: a letters-only passphrase, 28 characters
    texts = [f"secret {underscored} rejected", f"api key {underscored} rejected", f"password {phrase} rejected"]
    leaked = [t for t, s in zip(texts, (underscored, underscored, phrase)) if s in (webcapture.redact_text(t) or "")]
    assert not leaked, leaked


def test_r4_redaction_url_encoded_bearer_and_short_basic():
    tail = "Qw3Ke8Rt5Yu1Io0Pa2Sd"                                                      # FAKE token fragments, built at runtime
    encoded = "A" * 21 + "Mx7Q2" + "A" * 8 + "k9" + "%2B" + tail + "%3D" + "Lk4Jh7Gf6DsZx" + "%3D"
    basic = "dXNlcjpwYXNz"                                                             # base64 of the placeholder "user:pass"
    leaked = [label for label, t, s in (("encoded bearer tail", "Authorization: Bearer " + encoded, tail),
                                        ("short basic value", "Authorization: Basic " + basic, basic)) if s in (webcapture.redact_text(t) or "")]
    assert not leaked, leaked


def test_r4_redaction_pass3_cases_now_removed():
    hex64, hex40, hex32 = "9f86d081" * 8, "e4c1a0b2" * 5, "a0b1" * 8
    kp = b58encode(bytes([7]) * 64)                         # FAKE: base58 of 64 bytes of 0x07
    for t, s in ((f"Authorization: Bearer {hex64}", hex64), (f"HMAC secret {hex64} rejected", hex64), (f"token {hex40} expired", hex40),
                 (f"private key {kp} refused", kp), (f"provider rejected the X-API-KEY header value {hex32}", hex32), (f"password {hex40}", hex40)):
        assert s not in (webcapture.redact_text(t) or ""), t[:30]


def test_r4_redaction_keeps_public_identifiers_outside_credential_context():
    mint = "98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump"
    sha = "5f4ce7239eb4f0b03dfccf01205c59aee855b224653d42fbeae52da0e8dc39b1"
    sig = b58encode(bytes([5]) * 64)
    r = webcapture.redact_text(f"token {mint} not found; content hash {sha}; signature {sig} confirmed; missing key published_time_field_value") or ""
    assert mint in r and sha in r and "published_time_field_value" in r, r


def test_r4_redaction_over_redacts_evm_addresses_and_mints_after_a_colon():
    """Observation (diagnostics only, the allowlists hold no EVM paths): EVM addresses are removed anywhere, and a mint
    after 'token:' is removed. Recorded, not counted as a defect."""
    evm = "0x" + "4ed4e862" * 5
    mint = "98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump"
    r = webcapture.redact_text(f"token {evm} not found; token: {mint}") or ""
    assert evm not in r and mint not in r, r                 # documents current behavior


# ---------------------------------------------------------------- cohort cache (C3, C4)

def _file_cohort(path, close):
    c = store.connect(path)
    for k in range(30):
        m = f"F{k:02d}"
        member(c, m, "WATCH", T0)
        pool(c, m, f"P{m}", T0 - 86400)
        for i in range(-2, 24):
            bar(c, m, f"P{m}", T0 + i * H, 1.0, close, 1000.0)
    c.commit()
    r = S.empirical_cohort(c, "WATCH", asof=T0 + 5 * 86400)["ret_p10_p50_p90"][1]
    c.close()
    return r


def _remove(path):
    for suf in ("", "-wal", "-shm"):
        try:
            os.remove(str(path) + suf)
        except FileNotFoundError:
            pass


def test_r4_cohort_cache_in_memory_never_cached():
    S._COHORT_CACHE.clear()
    for close in (1.0, 0.5, 1.0, 0.5):
        c = store.connect(":memory:")
        for k in range(30):
            m = f"M{k:02d}"
            member(c, m, "WATCH", T0)
            pool(c, m, f"P{m}", T0 - 86400)
            for i in range(-2, 24):
                bar(c, m, f"P{m}", T0 + i * H, 1.0, close, 1000.0)
        c.commit()
        assert abs(S.empirical_cohort(c, "WATCH", asof=T0 + 5 * 86400)["ret_p10_p50_p90"][1] - (close - 1)) < 1e-9
        c.close(); del c; gc.collect()
    assert S._COHORT_CACHE == {}


def test_r4_cohort_cache_file_replaced_at_the_same_path(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RAW_DIR", tmp_path / "raw")
    S._COHORT_CACHE.clear()
    p = tmp_path / "bt.sqlite"
    first = _file_cohort(p, 1.0)
    ino = os.stat(p).st_ino
    _remove(p)
    second = _file_cohort(p, 0.5)                               # a different database written at the same path, same row ids
    same_inode = os.stat(p).st_ino == ino
    S._COHORT_CACHE.clear()
    if not same_inode:
        pytest.skip("the filesystem gave the new file another inode")
    assert abs(first) < 1e-9 and abs(second - (-0.5)) < 1e-9, f"replaced file at the same inode served {second} (true -0.5)"
