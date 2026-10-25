"""Phase 08: technical market-state features tech-1 and the technical predictors (memelab/predictive/technical.py).

Synthetic, seeded fixtures and temp stores only; every fixture result carries NO_REAL_HISTORICAL_EVIDENCE. The real run is
audits/predictive-intelligence/phase_08/probes/run_technical.py. No network, temp files, fixed times. Scenario ids from the
package's ADVERSARIAL_SCENARIOS.md; CX-08 is this phase's new counterexample (window-dependent opens, highs and lows).
"""
from __future__ import annotations

import ast
import json
import math
import socket
import types
from pathlib import Path

import numpy as np
import pytest

from memelab.predictive import baselines as B
from memelab.predictive import contract as C
from memelab.predictive import features as F
from memelab.predictive import labels as L
from memelab.predictive import sources as SRC
from memelab.predictive import stats as K
from memelab.predictive import store as S
from memelab.predictive import technical as T

FIX = Path(__file__).resolve().parent / "fixtures" / "predictive"
H = types.ModuleType("asof_helpers")          # loaded without writing bytecode next to the fixtures
exec(compile((FIX / "asof_helpers.py").read_text(), str(FIX / "asof_helpers.py"), "exec"), H.__dict__)
T1, T1B, T2 = L.T1, L.T1B, L.T2
H0 = L.holdout_start()
D0 = C.parse_utc("2026-10-01T00:00:00Z")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network use in a Phase 08 test")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(SRC, "curl_get", refuse)


# ---------------------------------------------------------------- store fixtures
def build(tmp_path, closes, *, name="s.sqlite", ohl=(1.0, 1.01, 0.99), first=None, last_end=None, exports=None,
          retrieved_at=None, vol=lambda s: 100.0):
    """A store with world_exports' decisions and one read of POOL_A's 5-minute candles from `first` to `last_end` with close
    closes(start); opens, highs and lows are close times the factors in `ohl`."""
    con = S.connect(tmp_path / name)
    ra = retrieved_at if retrieved_at is not None else H.T0 + 30 * 86400
    S.ingest_exports(con, exports if exports is not None else H.world_exports(), now=ra - 10)
    lo = int(first if first is not None else H.T0)
    hi = int(last_end if last_end is not None else H.D3)
    rows = [H.candle(s, c=closes(s), o=closes(s) * ohl[0], h=closes(s) * ohl[1], l=closes(s) * ohl[2], v=vol(s))
            for s in range(lo, hi, 300) if s + 300 <= hi]
    rows.reverse()
    keys = []
    for i in range(0, len(rows), 1000):
        page = rows[i:i + 1000]
        b = hi if i == 0 else rows[i - 1][0]
        r = S.ingest_gt_response(con, H.resp(H.POOL_A, b, page, ra + i, page=i // 1000), chain="solana", mint=H.MINT_A,
                                 pool=H.POOL_A, now=ra + i)
        keys.append(r["response_key"])
    H.series(con, mint=H.MINT_A, pool=H.POOL_A, boundary=hi, need_from=lo, keys=keys, checked_at=ra + 5000, kept=len(rows),
             last_end=hi)
    con.commit()
    return con


def wave(s):
    return 1.0 + 0.001 * ((s - H.T0) // 300 % 37)


def vals(snap):
    return {k: v["value"] for k, v in snap["values"].items()}


def tech(con, t, mint=H.MINT_A, **kw):
    return T.technical_as_of(con, "solana", mint, t, **kw)


# ---------------------------------------------------------------- tech-1 definitions
def test_values_match_an_independent_hand_computation(tmp_path):
    con = build(tmp_path, wave)
    t = H.D3
    snap = tech(con, t)
    lag = 300
    cs = [(s, s + 300, wave(s), 100.0) for s in range(int(H.T0), int(t), 300) if s + 300 + lag <= t]
    last = cs[-1]

    def px(x):
        return [c for c in cs if c[1] <= x][-1]

    def win(w):
        return [c for c in cs if t - w < c[1] <= t]
    want = {"tech_log_ret_1h": math.log(last[2] / px(t - 3600)[2]), "tech_log_ret_24h": math.log(last[2] / px(t - 86400)[2])}
    seq = [px(t - 3600)] + win(3600)
    want["tech_rv_1h"] = math.sqrt(sum(math.log(b[2] / a[2]) ** 2 for a, b in zip(seq, seq[1:])))
    cl6 = [px(t - 21600)[2]] + [c[2] for c in win(21600)]
    want["tech_log_range_6h"] = math.log(max(cl6) / min(cl6))
    want["tech_log_pullback_6h"] = math.log(last[2] / max(cl6))
    want["tech_log_rel_vol_1h"] = math.log((len(win(3600)) * 100.0 + 1) / (len(win(86400)) * 100.0 / 24 + 1))
    want["tech_log1p_candles_24h"] = math.log1p(len(win(86400)))
    want["tech_log1p_last_close_age_min"] = math.log1p((t - last[1]) / 60)
    ph = max([px(t - 86400)[2]] + [c[2] for c in cs if t - 86400 < c[1] <= t - 3600])
    rh = max([px(t - 3600)[2]] + [c[2] for c in win(3600)])
    want["tech_log_breakout_1h"] = math.log(rh / ph)
    got = vals(snap)
    for k, v in want.items():
        assert got[k] == pytest.approx(v, rel=1e-9, abs=1e-12), k
    assert T.row_status(snap) is None


def test_tech_restates_version_2_exactly_where_they_overlap(tmp_path):
    con = build(tmp_path, wave)
    for t in (H.D1, H.D2, H.D3):
        f = F.features_as_of(con, "solana", H.MINT_A, t, F.FEATURE_VERSION)
        row = {v["feature_name"]: v["value"] for v in f["values"]}
        row["__reasons"] = {v["feature_name"]: v["missing_reason"] for v in f["values"]}
        assert T.v2_consistency(tech(con, t), row) == []
        row["cdl_log_ret_6h"] = row["cdl_log_ret_6h"] + 1e-6
        assert T.v2_consistency(tech(con, t), row)


def test_breakout_failed_breakout_retest_and_exhaustion_on_shaped_paths(tmp_path):
    t = H.D3                                  # aligned: the newest usable candle ends at t - 300

    def spike_fail(s):                         # flat 1.0, a new high 1.2 inside the last hour, last close back to 0.98
        if s + 300 == t - 300:
            return 0.98
        if t - 3600 < s + 300 <= t - 900:
            return 1.2
        return 1.0
    v = vals(tech(build(tmp_path, spike_fail, name="a.sqlite"), t))
    assert v["tech_log_breakout_1h"] == pytest.approx(math.log(1.2))
    assert v["tech_failed_breakout_1h"] == 1.0
    assert v["tech_log_pullback_6h"] == pytest.approx(math.log(0.98 / 1.2))

    def retest(s):                             # flat 1.0 for 18 h, 1.2 four hours ago, last close 1.01 (within 3% of 1.0)
        if t - 4 * 3600 < s + 300 <= t - 3 * 3600:
            return 1.2
        if s + 300 > t - 3 * 3600:
            return 1.01
        return 1.0
    w = vals(tech(build(tmp_path, retest, name="b.sqlite"), t))
    assert w["tech_retest_6h"] == 1.0
    assert w["tech_failed_breakout_1h"] == 0.0
    assert w["tech_log_breakout_1h"] == pytest.approx(math.log(1.01 / 1.2))

    def no_retest(s):
        return 1.2 if t - 4 * 3600 < s + 300 <= t - 3 * 3600 else (1.10 if s + 300 > t - 3 * 3600 else 1.0)
    assert vals(tech(build(tmp_path, no_retest, name="c.sqlite"), t))["tech_retest_6h"] == 0.0

    def clean_breakout(s):
        return 1.3 if s + 300 > t - 1800 else 1.0
    z = vals(tech(build(tmp_path, clean_breakout, name="d.sqlite"), t))
    assert z["tech_log_breakout_1h"] == pytest.approx(math.log(1.3))
    assert z["tech_failed_breakout_1h"] == 0.0
    assert z["tech_log_dist_24h_high"] == 0.0


def test_spike_fail_retest_value(tmp_path):
    """The failed spike of the test above, read for the retest rule: PH6 = 1.0, a 1.2 close inside 6 h, last close 0.98 is
    within 3% of 1.0, so it is a retest as defined (the rule does not ask for the breakout to be older than an hour)."""
    t = H.D3

    def spike_fail(s):
        if s + 300 == t - 300:
            return 0.98
        if t - 3600 < s + 300 <= t - 900:
            return 1.2
        return 1.0
    assert vals(tech(build(tmp_path, spike_fail), t))["tech_retest_6h"] == 1.0


# ---------------------------------------------------------------- P06, P36: closed and available candles only
def test_p06_the_candle_holding_the_decision_and_one_closing_at_it_are_not_used(tmp_path):
    con = build(tmp_path, wave, last_end=H.D3 + 3000)
    t = H.D3 + 450                            # the candle [D3, D3 + 300) holds nothing; [D3 + 300, D3 + 600) holds t
    snap = tech(con, t)
    newest_end = max(float(r["end_at"]) for r in con.execute("SELECT end_at FROM predictive_candles WHERE available_at <= ?", (t,)))
    assert newest_end == H.D3                  # the candle ending at D3 is available at D3 + 300 <= t; the one ending at D3 + 300 is not
    assert snap["values"]["tech_log1p_last_close_age_min"]["value"] == pytest.approx(math.log1p(450 / 60))


def test_p36_a_candle_available_one_second_after_the_decision_is_absent_and_one_at_it_is_present(tmp_path):
    con = build(tmp_path, wave, last_end=H.D3 + 3000)
    t = H.D3 + 300                            # the candle ending at D3 becomes available exactly now
    a = tech(con, t)
    b = tech(con, t - 1)
    assert a["values"]["tech_log1p_last_close_age_min"]["value"] == pytest.approx(math.log1p(300 / 60))
    assert b["values"]["tech_log1p_last_close_age_min"]["value"] == pytest.approx(math.log1p((300 - 1 + 300) / 60))
    for s in (a, b):
        assert all(v["available_at"] is None or v["available_at"] <= s["decision_time"] for v in s["values"].values())


def test_p06_an_in_progress_candle_is_refused_at_ingest_and_ignored_by_tech_if_a_view_ever_served_one(tmp_path, monkeypatch):
    con = build(tmp_path, wave, retrieved_at=H.D3 + 1)
    # a live read at D3 + 10 that served the candle [D3, D3 + 300) while still in progress: the store refuses it
    r = S.ingest_gt_response(con, H.resp(H.POOL_A, H.D3 + 300, [H.candle(H.D3, c=9.0)], H.D3 + 10), chain="solana",
                             mint=H.MINT_A, pool=H.POOL_A, now=H.D3 + 10)
    con.commit()
    assert r["refused"] == 1 and con.execute("SELECT COUNT(*) FROM predictive_candles WHERE response_key=?",
                                             (r["response_key"],)).fetchone()[0] == 0
    t = H.D3 + 20
    before = vals(tech(con, t))
    real = F.AsOfView.candles

    def with_in_progress(self, chain, mint, pool):
        rows = real(self, chain, mint, pool)
        fake = dict(rows[-1], obs_key="fake-in-progress", start_at=H.D3, end_at=H.D3 + 300, c=9.0, v=5.0, _avail=H.D3 + 10)
        return rows + [fake]
    monkeypatch.setattr(F.AsOfView, "candles", with_in_progress)
    assert vals(tech(con, t)) == before       # a close exists only once its candle has ended


# ---------------------------------------------------------------- CX-08: opens, highs and lows depend on the request window
def test_cx08_opens_highs_and_lows_never_change_a_feature(tmp_path):
    a = build(tmp_path, wave, name="a.sqlite", ohl=(1.0, 1.01, 0.99))
    b = build(tmp_path, wave, name="b.sqlite", ohl=(0.7, 1.9, 0.4))
    for t in (H.D1, H.D2, H.D3):
        assert vals(tech(a, t)) == vals(tech(b, t))


def test_cx08_a_later_read_that_only_moves_opens_highs_and_lows_changes_nothing(tmp_path):
    con = build(tmp_path, wave, retrieved_at=H.D3 + 1)
    t = H.D3 + 200
    before = vals(tech(con, t))
    rows = [H.candle(s, c=wave(s), o=wave(s) * 0.5, h=wave(s) * 3, l=wave(s) * 0.2) for s in range(int(H.D3) - 6000, int(H.D3), 300)]
    rows.reverse()
    S.ingest_gt_response(con, H.resp(H.POOL_A, H.D3, rows, H.D3 + 100), chain="solana", mint=H.MINT_A, pool=H.POOL_A,
                         now=H.D3 + 100)
    con.commit()
    n_rev = con.execute("SELECT COUNT(*) FROM predictive_candles WHERE revision_kind='OPEN_WINDOW' AND available_at <= ?",
                        (t,)).fetchone()[0]
    assert n_rev == 20                          # visible at t: the revised versions are what the view hands over
    assert vals(tech(con, t)) == before


# ---------------------------------------------------------------- missingness: never imputed, retrieval is censoring
def test_no_point_in_time_pool_is_ood_and_never_filled_from_another_pool(tmp_path):
    ex = H.world_exports()
    for e in ex:
        e["tokens"] = [H.token(H.MINT_B, pool=None) if tk["mint"] == H.MINT_B else tk for tk in e["tokens"]]
    con = build(tmp_path, wave, exports=ex)
    snap = tech(con, H.D2, mint=H.MINT_B)
    assert {v["missing_reason"] for v in snap["values"].values()} == {"NO_POOL_AT_DECISION"}
    assert T.row_status(snap) == "OOD"


def test_a_window_before_the_fetched_history_is_censored_retrieval(tmp_path):
    con = build(tmp_path, wave, first=H.T0 + 12 * 3600)
    snap = tech(con, H.D1)
    v = snap["values"]
    assert v["tech_log_ret_1h"]["value"] is not None
    assert v["tech_log_ret_24h"]["missing_reason"] == "OUTSIDE_FETCHED_WINDOW"
    assert v["tech_log_ret_24h"]["missing_basis"] == F.RETRIEVAL
    assert T.row_status(snap) == "CENSORED_RETRIEVAL"


def test_capture_mode_never_counts_a_backfill_read_after_the_decision(tmp_path):
    con = build(tmp_path, wave)
    snap = tech(con, H.D3, mode="capture")
    assert all(v["value"] is None for v in snap["values"].values())
    assert {v["missing_basis"] for v in snap["values"].values()} == {F.RETRIEVAL}


def test_identity_a_decision_key_of_another_decision_is_refused(tmp_path):
    con = build(tmp_path, wave)
    k3 = tech(con, H.D3)["decision_key"]
    with pytest.raises(B.IdentityJoinError):
        tech(con, H.D2, decision_key=k3)
    with pytest.raises(S.StoreError):
        T.technical_as_of(con, "solana", "NOT-A-MINT", H.D3)


def test_snapshots_are_deterministic(tmp_path):
    con = build(tmp_path, wave)
    assert tech(con, H.D3)["tech_snapshot_sha"] == tech(con, H.D3)["tech_snapshot_sha"]
    assert T.feature_set_sha() == T.feature_set_sha()


# ---------------------------------------------------------------- models on synthetic examples
def tex(n=700, *, seed=11, signal=1.0, days=16, target=T1, missing_share=0.1, censored_share=0.05):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        t = D0 + rng.uniform(0, days * 86400)
        z = {c: rng.normal(0, 1) for c in T.TECH}
        y = int(rng.uniform() < 1 / (1 + math.exp(-(-1.0 + signal * z["tech_log_ret_1h"]))))
        liq = rng.normal(11, 1.5)
        x = {B.LIQ: liq, B.MCAP: liq + rng.normal(1, 0.3), B.VOL: rng.normal(12, 1), B.FATAL: float(rng.uniform() < 0.2),
             B.AGE: math.log1p(rng.uniform(0, 30)), B.SCORE: float(rng.integers(20, 80))}
        u = rng.uniform()
        status, reasons = None, {}
        if u < missing_share:
            status, reasons = "OOD", {c: "NO_POOL_AT_DECISION" for c in T.TECH}
            z = {c: float("nan") for c in T.TECH}
        elif u < missing_share + censored_share:
            status, reasons = "CENSORED_RETRIEVAL", {"tech_log_ret_24h": "OUTSIDE_FETCHED_WINDOW"}
            z["tech_log_ret_24h"] = float("nan")
        x.update(z)
        out.append(T.TExample(f"k{i:04d}", "solana", f"{H.MINT_A[:-3]}{i % 150:03d}", t, C.label_matures_at(target, t), y, x,
                              {c: t for c in x}, status="WATCH", creator=f"c{i % 40}", route="PIT_RECORDED", label_key=f"l{i}",
                              snapshot_sha256="0" * 64, tech_status=status, tech_reasons=reasons, tech_sha="1" * 64))
    return [e for e in out if e.label_matures_at <= H0]


def gate_like(dev):
    return lambda c: [e for e in dev if e.decision_time < c and e.label_matures_at <= c]


@pytest.fixture(scope="module")
def fixture_run():
    dev = tex()
    return dev, T.walk_forward(T1, dev, gate_like(dev), nc1_seeds=range(5), is_fixture=True)


def test_g18_fixture_with_a_technical_signal_m1_m2_beat_b0_nc1_does_not_and_says_no_real_evidence(fixture_run):
    dev, res = fixture_run
    rows = res["oos"]
    for m in ("M1_T_LOGIT", "M2_T_LOGIT_B2", "M3_T_STUMPS"):
        ev = B.evaluate(rows, m, reps=200)
        assert ev["bss"] > 0.05, m
    nc = [B.evaluate(rows, f"NC1T_{s}", reps=200, boot=False)["bss"] for s in range(5)]
    assert np.mean(nc) < 0.02
    assert res["evidence_class"] == T.FIXTURE_FLAG
    for f in res["folds"]:
        for c in f["cards"].values():
            assert c["evidence_class"] == T.FIXTURE_FLAG


def test_every_card_is_provisional_not_promoted_and_claims_no_revision_check(fixture_run):
    _, res = fixture_run
    for f in res["folds"]:
        for m in T.ALL_IDS:
            c = f["cards"][m]
            assert c["status"] == T.PROVISIONAL and c["revision_check_claimed"] is False and c["publishable"] is False
            assert c["promotion"] == "MODEL_NOT_PROMOTED" and c["feature_set_sha"] == T.feature_set_sha()


def test_ood_and_censored_rows_never_train_and_abstain_with_their_reason(fixture_run):
    dev, res = fixture_run
    for r in res["oos"]:
        e = r["example"]
        if e.tech_status == "OOD":
            assert not math.isfinite(r["M1_T_LOGIT"]) and r["M1_T_LOGIT_why"] == "OOD"
        elif e.tech_status == "CENSORED_RETRIEVAL":
            assert not math.isfinite(r["M2_T_LOGIT_B2"]) and r["M2_T_LOGIT_B2_why"] == "CENSORED_RETRIEVAL"
        else:
            assert math.isfinite(r["M3_T_STUMPS"])
    f = res["folds"][0]
    train = gate_like(dev)(f["cutoff"])
    assert f["cards"]["M1_T_LOGIT"]["n_used"] == sum(1 for e in train if e.tech_status is None)


def test_count_gate_on_the_rows_with_every_technical_input():
    dev = tex(n=300, days=12, missing_share=0.75, censored_share=0.0)
    cut = H0
    train = gate_like(dev)(cut)
    assert len(train) >= 100
    c = T.fit("M1_T_LOGIT", T1, train, cut, is_fixture=True)
    assert c["n_used"] < 100 and c["body"]["abstain"] == "INSUFFICIENT_HISTORY"
    p, why = T.predict(c, [e for e in dev if e.decision_time >= cut][:3] or [])
    assert all(w == "INSUFFICIENT_HISTORY" for w in why)


def test_ablations_drop_exactly_one_family_and_use_m2_rows():
    m2 = T.SPECS["M2_T_LOGIT_B2"]
    for i, fam in enumerate(T.FAMILIES, 1):
        a = T.SPECS[f"A{i}_M2_minus_{fam}"]
        assert set(m2["columns"]) - set(a["columns"]) == set(T.FAMILIES[fam])
        assert a["rows"] == m2["rows"]
    assert set(T.SPECS["A5_T_B2_TC"]["columns"]) == set(B.B2_COLUMNS) and T.SPECS["A5_T_B2_TC"]["rows"] == m2["rows"]


def test_p13_a_card_trained_after_a_decision_cannot_score_it(fixture_run):
    dev, res = fixture_run
    card = T.fit("M1_T_LOGIT", T1, gate_like(dev)(H0), H0, is_fixture=True)
    early = [e for e in dev if e.decision_time < H0][:2]
    with pytest.raises(T.ModelTrainedAfterDecision):
        T.predict(card, early)


def test_p43_p05_fit_refuses_a_row_decided_after_or_maturing_after_the_cutoff(fixture_run):
    dev, _ = fixture_run
    cut = D0 + 12 * 86400
    train = gate_like(dev)(cut)
    late = [e for e in dev if e.decision_time >= cut][0]
    with pytest.raises((B.BaselineError, F.AsOfError)):
        T.fit("M1_T_LOGIT", T1, train + [late], cut)


def test_p20_a_maturity_shorter_than_the_target_fails_the_fold_audit():
    dev = tex(n=500)
    for e in dev:
        e.label_matures_at = e.decision_time + 6 * 3600
    with pytest.raises(B.BaselineError):
        T.walk_forward(T1, dev, gate_like(dev), nc1_seeds=())


def test_walk_forward_refuses_a_gate_that_disagrees_with_the_frozen_index():
    dev = tex(n=500)
    with pytest.raises(B.WalkForwardMismatch):
        T.walk_forward(T1, dev, lambda c: gate_like(dev)(c)[1:], nc1_seeds=())


def test_nc2t_a_future_return_is_refused_by_the_allowlist_and_by_validate_rows(fixture_run):
    dev, _ = fixture_run
    e = dev[0]
    e2 = T.TExample(**{**e.__dict__, "x": {**e.x, "trap_next_hour_return": 0.1}, "avail": {**e.avail, "trap_next_hour_return": e.decision_time + 3900}})
    with pytest.raises(F.AsOfError):
        T.check_asof([e2], ["trap_next_hour_return"], as_of=None, with_labels=False)
    e3 = T.TExample(**{**e.__dict__, "avail": {**e.avail, "tech_log_ret_1h": e.decision_time + 3900}})
    with pytest.raises(F.AsOfError):
        T.check_asof([e3], ["tech_log_ret_1h"], as_of=None, with_labels=False)
    card = T.fit("M1_T_LOGIT", T1, gate_like(dev)(D0 + 12 * 86400), D0 + 12 * 86400, is_fixture=True)
    newest = max(dev, key=lambda x: x.decision_time)
    late = T.TExample(**{**newest.__dict__, "avail": {**newest.avail, "tech_rv_1h": newest.decision_time + 1}})
    with pytest.raises(F.AsOfError):
        T.predict(card, [late])


def test_p10_p11_p38_degenerate_and_invalid_numbers(fixture_run):
    assert T.degenerate([0.2, 0.2, 0.2]) and not T.degenerate([0.2, 0.3]) and not T.degenerate([0.2])
    with pytest.raises(ValueError):
        K.check_probs([0.2, float("nan")])
    dev, _ = fixture_run
    card = T.fit("M3_T_STUMPS", T1, gate_like(dev)(H0), H0, is_fixture=True)
    bad = json.loads(T.dumps(card))
    bad["body"]["stumps"]["init"] = float("inf")
    with pytest.raises(ValueError):
        T.dumps(bad)
    e = [x for x in dev if x.tech_status is None][0]
    e_nan = T.TExample(**{**e.__dict__, "x": {**e.x, "tech_rv_1h": float("inf")}})
    with pytest.raises(ValueError):
        T.Stumps.from_dict(card["body"]["stumps"]).decision_function(T.matrix([e_nan], T.TECH))
    # P10: an always-negative model on a rare event loses to the base rate under the frozen score
    y = np.array([1] * 3 + [0] * 97, float)
    assert K.brier_skill(y, np.full(100, 1e-6), np.full(100, 0.03)) < 0


def test_cards_round_trip_exactly_and_tampering_or_another_feature_set_is_refused(fixture_run, tmp_path):
    dev, _ = fixture_run
    train = gate_like(dev)(H0)
    for m in T.MODEL_IDS:
        card = T.fit(m, T1, train, H0, is_fixture=True)
        p = tmp_path / f"{m}.json"
        p.write_text(T.dumps(card))
        back = T.loads(p.read_text())
        a = T.predict_numbers(card, train)[0]
        b = T.predict_numbers(back, train)[0]
        assert np.array_equal(np.nan_to_num(a, nan=-1), np.nan_to_num(b, nan=-1))
        t = json.loads(p.read_text())
        key = "logistic" if "logistic" in t["body"] else "stumps"
        if key == "logistic":
            t["body"]["logistic"]["coef"][0] += 1e-9
        else:
            t["body"]["stumps"]["trees"][0][2] += 1e-9
        with pytest.raises(B.ModelHashMismatch):
            T.verify_card(t)
        other = json.loads(p.read_text())
        other["feature_set_sha"] = "0" * 64
        other["model_sha"] = B.sha({k: v for k, v in other.items() if k != "model_sha"})
        with pytest.raises(F.FeatureVersionError):
            T.verify_card(other)


def test_an_abstain_document_from_an_m2_card_is_valid_and_a_forecast_is_refused(fixture_run):
    dev, _ = fixture_run
    card = T.fit("M2_T_LOGIT_B2", T1, gate_like(dev)(H0), H0, is_fixture=True)
    doc = B.abstain_document(T1, mint=H.MINT_A, snapshot_hash="a" * 64, decision_time_utc="2026-10-18T10:00:00Z",
                             generated_at_utc="2026-10-18T10:00:01Z", reasons=["INSUFFICIENT_HISTORY", "MODEL_NOT_SELECTED"],
                             base_rate=0.25, card=card)
    assert C.validate(doc, backtest=C.BACKTEST_NOT_AVAILABLE) == []
    fc = dict(doc, prediction_status="FORECAST", abstain_reasons=[], probability=0.3, uncertainty_interval=[0.2, 0.4])
    mc = {k: card[k] for k in ("model_sha", "feature_set_sha", "targets", "target_version", "training_cutoff_utc")}
    assert C.validate(fc, model_card=mc, backtest=C.BACKTEST_NOT_AVAILABLE)


def test_p21_hit_miss_by_week_claims_no_rate_below_20(fixture_run):
    _, res = fixture_run
    tab = T.hit_miss(res["oos"], "M2_T_LOGIT_B2", lambda e: e.day)
    assert tab and all(r["hits"] + r["misses"] + r["false_alarms"] + r["correct_rejections"] == r["n_scored"] for r in tab)
    assert all(r["support_note"].startswith("n < 20") for r in tab if r["n_scored"] < 20)


# ---------------------------------------------------------------- stumps
def test_stumps_learn_a_step_respect_the_leaf_minimum_and_are_deterministic():
    rng = np.random.default_rng(3)
    X = rng.normal(size=(300, 3))
    y = (rng.uniform(size=300) < np.where(X[:, 1] > 0.3, 0.8, 0.1)).astype(float)
    a = T.Stumps().fit(X, y)
    b = T.Stumps().fit(X, y)
    assert a.to_dict() == b.to_dict()
    assert {t[0] for t in a.trees[:5]} == {1}
    assert abs(a.trees[0][1] - 0.3) < 0.2
    for j, thr, _, _ in a.trees:
        left = int(np.sum(X[:, j] <= thr))
        assert T.STUMP_MIN_LEAF <= left <= 300 - T.STUMP_MIN_LEAF
    assert len(a.trees) == T.STUMP_ROUNDS
    p = a.predict_proba1(X)
    assert K.brier(y, p) < K.brier(y, np.full(300, y.mean()))
    assert a.init == pytest.approx(math.log(y.mean() / (1 - y.mean())))


def test_stumps_refuse_one_class_and_non_finite_inputs():
    with pytest.raises(ValueError):
        T.Stumps().fit(np.ones((50, 2)) * np.arange(50)[:, None], np.zeros(50))
    X = np.random.default_rng(1).normal(size=(50, 2))
    X[3, 1] = np.nan
    with pytest.raises(ValueError):
        T.Stumps().fit(X, (np.arange(50) % 2).astype(float))


def test_stumps_leaf_value_is_the_newton_step():
    X = np.array([[0.0], [0.0], [1.0], [1.0]] * 10)
    y = np.array([0, 1, 1, 1] * 10, float)
    m = T.Stumps(rounds=1, lr=1.0, min_leaf=10).fit(X, y)
    p0 = y.mean()
    j, thr, vl, vr = m.trees[0]
    assert thr == 0.5
    assert vl == pytest.approx(np.sum(y[X[:, 0] <= 0.5] - p0) / (20 * p0 * (1 - p0)))
    assert vr == pytest.approx(np.sum(y[X[:, 0] > 0.5] - p0) / (20 * p0 * (1 - p0)))


# ---------------------------------------------------------------- code rules
def test_the_new_module_uses_only_numpy_and_the_standard_library():
    tree = ast.parse(Path(T.__file__).read_text())
    names = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    names |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module and n.level == 0}
    assert names <= {"__future__", "math", "sqlite3", "dataclasses", "typing", "numpy", "json"}, names


def test_tech_reads_closes_and_volumes_only():
    src = Path(T.__file__).read_text()
    for k in ('["o"]', '["h"]', '["l"]', "['o']", "['h']", "['l']"):
        assert k not in src


def test_feature_set_sha_names_the_version_2_definitions():
    d = T.feature_set_definitions()
    assert d["base_feature_set_sha"] == F.feature_set_sha() and d["version"] == "tech-1"
    assert [f["name"] for f in d["features"]] == list(T.TECH) and len(T.TECH) == 15


def test_coverage_boundary_a_window_needs_one_candle_before_it(tmp_path):
    t = H.D3
    ok = tech(build(tmp_path, wave, name="a.sqlite", first=t - 86400 - 300), t)
    assert ok["values"]["tech_log_ret_24h"]["value"] is not None
    short = tech(build(tmp_path, wave, name="b.sqlite", first=t - 86400), t)
    assert short["values"]["tech_log_ret_24h"]["missing_reason"] == "OUTSIDE_FETCHED_WINDOW"
    for c in ("tech_log1p_candles_24h", "tech_log_rel_vol_1h", "tech_log_range_24h"):
        assert short["values"][c]["missing_reason"] == "OUTSIDE_FETCHED_WINDOW", c
    assert short["values"]["tech_log_ret_6h"]["value"] is not None


def test_nc2t_the_allowlist_refuses_an_undeclared_column_even_with_a_plausible_availability(fixture_run):
    dev, _ = fixture_run
    e = dev[0]
    e4 = T.TExample(**{**e.__dict__, "x": {**e.x, "trap_next_hour_return": 0.1}, "avail": {**e.avail, "trap_next_hour_return": e.decision_time}})
    with pytest.raises(F.AsOfError, match="allowlist"):
        T.check_asof([e4], ["trap_next_hour_return"], as_of=None, with_labels=False)
    with pytest.raises(F.AsOfError, match="allowlist"):
        T.matrix([e4], ["trap_next_hour_return"])


def test_hit_miss_counts_an_alert_only_strictly_above_the_training_prevalence():
    ex = [B.Example(f"k{i}", "solana", H.MINT_A, D0 + 600, D0, y) for i, y in enumerate([1, 0, 1, 0])]
    rows = [{"example": e, "y": e.y, "B0": 0.3, "M": p} for e, p in zip(ex, [0.3, 0.3, 0.5, 0.1])]
    r = T.hit_miss(rows, "M", lambda e: "all")[0]
    assert (r["hits"], r["misses"], r["false_alarms"], r["correct_rejections"]) == (1, 1, 0, 2)


def test_windows_of_6_and_24_hours_are_distinct(tmp_path):
    t = H.D3

    def path(s):
        e = s + 300
        if t - 12 * 3600 - 300 < e <= t - 12 * 3600:
            return 0.5
        return 1.1 if e > t - 2 * 3600 else 1.0
    v = vals(tech(build(tmp_path, path), t))
    assert v["tech_log_range_6h"] == pytest.approx(math.log(1.1))
    assert v["tech_log_range_24h"] == pytest.approx(math.log(1.1 / 0.5))
    assert v["tech_log_pullback_6h"] == 0.0 and v["tech_log_ret_6h"] == pytest.approx(math.log(1.1))


def test_attach_keeps_a_missing_technical_input_missing_and_the_row_abstains(tmp_path):
    ex = H.world_exports()
    for e in ex:
        e["tokens"] = [H.token(H.MINT_B, pool=None) if tk["mint"] == H.MINT_B else tk for tk in e["tokens"]]
    con = build(tmp_path, wave, exports=ex)
    sb, sa = tech(con, H.D2, mint=H.MINT_B), tech(con, H.D3)
    base = [B.Example(sb["decision_key"], "solana", H.MINT_B, H.D2, H.D2 + 86400, 1, {c: 1.0 for c in B.ALLOWED_COLUMNS},
                      {c: H.D2 for c in B.ALLOWED_COLUMNS}),
            B.Example(sa["decision_key"], "solana", H.MINT_A, H.D3, H.D3 + 86400, 0, {c: 1.0 for c in B.ALLOWED_COLUMNS},
                      {c: H.D3 for c in B.ALLOWED_COLUMNS})]
    a, b = T.attach(base, {sb["decision_key"]: sb, sa["decision_key"]: sa})
    assert all(math.isnan(a.x[c]) for c in T.TECH) and a.tech_status == "OOD" and not T.complete(a, T.TECH)
    assert T.complete(b, T.TECH) and b.tech_status is None
    assert all(b.avail[c] <= H.D3 for c in T.TECH)
    with pytest.raises(B.IdentityJoinError):
        T.attach([base[0]], {sb["decision_key"]: dict(sb, mint=H.MINT_A)})
