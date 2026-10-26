"""Phase 13: calibration-1 (memelab/predictive/calibration.py). Synthetic fixtures only; no network, no clock, no store, no
holdout. The real run is audits/predictive-intelligence/phase_13/probes/run_calibration.py."""
from __future__ import annotations

import ast
import json
import math
from pathlib import Path

import numpy as np
import pytest

from memelab.predictive import baselines as B
from memelab.predictive import calibration as CAL
from memelab.predictive import contract as C
from memelab.predictive import labels as L
from memelab.predictive import stats as K

ROOT = Path(__file__).resolve().parents[1]
H = L.holdout_start()
P0 = CAL.PROSPECTIVE_START
DAY = 86400.0
T1 = L.T1


def rows(n, k, *, days=10, start=None, scores=None, split="DEVELOPMENT", seed=0, prefix="r"):
    """n development rows with k positives over `days` decision days, all decided and matured before H."""
    rng = np.random.default_rng(seed)
    start = H - 30 * DAY if start is None else start
    y = np.zeros(n, int)
    y[rng.choice(n, k, replace=False)] = 1
    s = scores if scores is not None else np.clip(0.15 + 0.5 * y + rng.normal(0, 0.15, n), 0.01, 0.99)
    out = []
    for i in range(n):
        t = start + (i % days) * DAY + i
        out.append({"decision_key": f"{prefix}{i}", "mint": f"m{i}", "decision_time": t, "label_matures_at": t + DAY, "y": int(y[i]),
                    "score": float(s[i]), "scored_by_cutoff": t - 1.0, "split": split})
    return out


def champion():
    return {"model_id": "B2:" + T1, "model_sha": "a" * 64, "kind": "B2", "training_cutoff_utc": "2026-10-17T00:00:00Z"}


def evidence(n, k, *, seed=5, scores=None):
    ev = rows(n, k, days=5, start=P0 + DAY, seed=seed, split="PROSPECTIVE", prefix="e", scores=scores)
    return {"status": "ADMISSIBLE", "rows": ev, "fit_cutoff": H, "cutoff": P0 + 20 * DAY, "source": "PROSPECTIVE_HOLDOUT"}


# ---------------------------------------------------------------- frozen constants
def test_frozen_constants_are_the_preregistered_ones():
    a = C.ACCEPTANCE
    assert CAL.FIT_GATE == {"min_events": 100, "min_per_class": 20, "min_days": 5}
    assert CAL.VENN_ABERS_GATE == {"min_events": 200, "min_per_class": 40}
    assert CAL.EVIDENCE_GATE == {"min_events": 50, "min_per_class": 10}
    assert CAL.SUPPORT_MIN == 20 and CAL.DISPLAY_RANGE == (0.01, 0.99) and CAL.OOD_Z == 4.0
    assert CAL.FLAT_PTP == 1e-9 and CAL.NEAR_FLAT_SD == 0.005 and CAL.SEED == 20261025
    assert CAL.SCORE_REPS == 2000 and CAL.BASE_REPS == 20000
    assert CAL.DRIFT == {"delta": 0.005, "threshold": 2.0, "min_obs": 30, "two_sided": False}
    assert CAL.CAL_RULE == a["calibration"] and CAL.CAL_RULE["conf"] == 0.95 and CAL.CAL_RULE["max_bins"] == 5
    assert CAL.LOG_LOSS_CLIP == 1e-6 and CAL.AUC_MIN_PER_CLASS == 10
    assert CAL.HOLDOUT_START == H and CAL.PROSPECTIVE_START == L.prospective_start()
    assert C.registry_sha256().startswith("4b4aabce")


def test_the_frozen_tolerance_is_the_wilson_check_of_acceptance():
    y = np.zeros(100)
    y[::10] = 1
    ok = CAL.reliability(y, np.full(100, 0.1))
    bad = CAL.reliability(y, np.full(100, 0.2))
    assert ok["in_the_large_ok"] and CAL.check_passed(ok)
    assert not bad["in_the_large_ok"] and not CAL.check_passed(bad)
    lo, hi = K.wilson(10, 100)
    assert ok["wilson"] == [lo, hi] and len(ok["bins"]) == 5 and all(b["n"] == 20 for b in ok["bins"])
    assert "note" in CAL.reliability(y[:39], np.full(39, 0.1))         # under 40: in the large only


# ---------------------------------------------------------------- rule 1: the calibration set
def test_rows_at_keeps_only_rows_known_at_the_cutoff_and_checks_them():
    rs = rows(30, 10)
    cut = rs[15]["decision_time"] + 0.5
    got = CAL.rows_at(rs, cut)
    assert all(r["decision_time"] < cut and r["label_matures_at"] <= cut for r in got)
    assert len(got) == sum(1 for r in rs if r["decision_time"] < cut and r["label_matures_at"] <= cut)


@pytest.mark.parametrize("bad, match", [
    ({"decision_time_shift": 0.0}, "at or after the cutoff"),
    ({"mature_after": True}, "matures after"),
    ({"split": "RETROSPECTIVE_HOLDOUT"}, "only development"),
    ({"relabel_holdout": True}, "not a development row"),
    ({"in_sample": True}, "in-sample"),
    ({"score": float("nan")}, "P38"),
    ({"score": 1.2}, "P38"),
    ({"y": 2}, "binary"),
    ({"y": True}, "binary"),
])
def test_a_row_that_cannot_calibrate_is_refused_never_dropped(bad, match):
    rs = rows(20, 5)
    cut = H - 2 * DAY
    r = rs[3]
    if "decision_time_shift" in bad:
        r["decision_time"] = cut
    if bad.get("mature_after"):
        r["label_matures_at"] = cut + 1
    if "split" in bad:
        r["split"] = bad["split"]
    if bad.get("relabel_holdout"):
        r["decision_time"], r["label_matures_at"], r["scored_by_cutoff"] = H + 3600, H + DAY, H
    if bad.get("in_sample"):
        r["scored_by_cutoff"] = r["decision_time"] + 1
    for k in ("score", "y"):
        if k in bad:
            r[k] = bad[k]
    with pytest.raises(CAL.CalibrationError, match=match):
        CAL.check_rows(rs, cut if not bad.get("relabel_holdout") else H + 30 * DAY)


def test_a_duplicate_decision_or_a_missing_field_is_refused():
    rs = rows(5, 2)
    with pytest.raises(CAL.CalibrationError, match="twice"):
        CAL.check_rows(rs + [dict(rs[0])], H)
    r = dict(rs[0])
    del r["scored_by_cutoff"]
    with pytest.raises(CAL.CalibrationError, match="lacks"):
        CAL.check_rows([r], H)


# ---------------------------------------------------------------- rules 2 and 3: gate and method
@pytest.mark.parametrize("n, k, days, ok", [
    (99, 30, 5, False), (100, 20, 5, True), (100, 19, 5, False), (100, 81, 5, False), (100, 80, 5, True), (150, 40, 4, False),
])
def test_the_fit_gate_boundaries(n, k, days, ok):
    assert (CAL.fit_gate(n, k, days) == []) is ok
    assert (CAL.method_for(n, k, days) is not None) is ok


@pytest.mark.parametrize("n, k, method", [(199, 60, "PLATT"), (200, 40, "VENN_ABERS"), (200, 39, "PLATT"), (200, 161, "PLATT"),
                                          (99, 40, None)])
def test_the_method_rule_is_fixed_by_counts_only(n, k, method):
    assert CAL.method_for(n, k, 5) == method


@pytest.mark.parametrize("n, k, ok", [(49, 20, False), (50, 10, True), (50, 9, False), (50, 41, False)])
def test_the_evidence_gate(n, k, ok):
    assert (CAL.evidence_gate(n, k) == []) is ok


def test_the_development_sizes_of_the_real_targets_can_never_pass_the_gate():
    """The recorded Phase 07 out-of-sample counts (PI-D-049, PI-D-055): T1 24/8/3 days, T1b 44/3/5, T2 8/1/1."""
    for n, k, d in ((24, 8, 3), (44, 3, 5), (8, 1, 1)):
        assert CAL.fit_gate(n, k, d) and CAL.method_for(n, k, d) is None


# ---------------------------------------------------------------- calibrators
def test_platt_and_venn_abers_are_the_stats_engine_and_stay_inside_0_1():
    rs = rows(300, 90, seed=2)
    s, y = [r["score"] for r in rs], [r["y"] for r in rs]
    pl = CAL.fit_calibrator(s, y, "PLATT")
    assert pl["params"] == K.Platt().fit(np.asarray(s), np.asarray(y, float)).to_dict()
    va = CAL.fit_calibrator(s, y, "VENN_ABERS")
    test = np.linspace(0.02, 0.98, 17)
    p, p0, p1 = CAL.apply_calibrator(va, test)
    q0, q1, q = K.venn_abers(np.asarray(s), np.asarray(y, float), test)
    assert np.array_equal(p, q) and np.array_equal(p0, q0) and np.array_equal(p1, q1)
    assert np.all(p0 <= p + 1e-15) and np.all(p <= p1 + 1e-15)
    pp, lo, hi = CAL.apply_calibrator(pl, test)
    assert np.array_equal(pp, lo) and np.array_equal(pp, hi) and np.all((pp > 0) & (pp < 1))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_a_non_finite_score_never_reaches_a_calibrator_p38(bad):
    rs = rows(120, 40)
    for m in ("PLATT", "VENN_ABERS"):
        cal = CAL.fit_calibrator([r["score"] for r in rs], [r["y"] for r in rs], m)
        with pytest.raises(CAL.CalibrationError, match="P38"):
            CAL.apply_calibrator(cal, [0.3, bad])
    with pytest.raises(ValueError):
        CAL.fit_calibrator([0.1, bad, 0.3], [0, 1, 0], "PLATT")
    with pytest.raises(CAL.CalibrationError):
        CAL.fit_calibrator([0.1, 0.2], [0, 1], "ISOTONIC_ALONE")


# ---------------------------------------------------------------- rule 7: support and intervals (P23, P24)
def test_the_interval_never_narrows_as_support_falls():
    widths = []
    for n in (20, 40, 80, 160, 320, 640, 1280):
        lo, hi = CAL.interval(0.3, 0.3, n, int(round(0.3 * n)))
        widths.append(hi - lo)
        assert lo <= 0.3 <= hi
    assert all(a >= b for a, b in zip(widths, widths[1:])) and widths[0] > 2 * widths[-1]


def test_the_interval_is_the_hull_of_the_calibrator_interval_and_the_support_wilson():
    lo, hi = CAL.interval(0.20, 0.45, 25, 5)
    wl, wh = K.wilson(5, 25)
    assert lo == min(0.20, wl) and hi == max(0.45, wh)
    with pytest.raises(CAL.CalibrationError):
        CAL.interval(float("nan"), 0.4, 25, 5)
    with pytest.raises(CAL.CalibrationError):
        CAL.interval(0.5, 0.4, 25, 5)


def test_support_bins_follow_the_frozen_quantile_layout_and_refuse_extrapolation():
    rs = rows(100, 30, seed=4)
    s, y = [r["score"] for r in rs], [r["y"] for r in rs]
    bins = CAL.support_bins(s, y)
    assert len(bins) == 5 and sum(b["n"] for b in bins) == 100 and all(b["n"] == 20 for b in bins)
    assert CAL.support_of(bins, min(s) - 1e-6) is None and CAL.support_of(bins, max(s) + 1e-6) is None
    mid = CAL.support_of(bins, float(np.median(s)))
    assert mid is not None and mid["p_min"] <= float(np.median(s)) <= mid["p_max"]
    assert CAL.support_of(bins, float("nan")) is None
    small = CAL.support_bins(s[:30], y[:30])
    assert len(small) == 1 and small[0]["n"] == 30


def test_p24_a_small_calibration_set_with_a_confident_number_gives_no_calibrated_card():
    rs = rows(30, 29, days=6, scores=np.full(30, 0.95) + np.linspace(-0.01, 0.01, 30))
    card = CAL.build_card(T1, champion(), rs, H, level="SHADOW", evidence=evidence(60, 15))
    assert card["status"] == CAL.UNCALIBRATED and card["calibrator"] is None and not card["publishable"]
    assert "CALIBRATION_SET_TOO_SMALL" in card["details"]
    lo, hi = K.wilson(29, 30)
    assert hi - lo > 0.15


# ---------------------------------------------------------------- rules 8 and 9: degeneracy and scores (P10, P11, P23)
def test_p11_flat_all_positive_predictions_are_flagged_and_fail_calibration():
    y = np.r_[np.ones(30), np.zeros(70)]
    d = CAL.degeneracy(np.full(100, 0.9))
    assert d["flat"] and d["near_flat"]
    assert not CAL.reliability(y, np.full(100, 0.9))["in_the_large_ok"]
    rs = rows(200, 60, scores=np.full(200, 0.9))
    card = CAL.build_card(T1, champion(), rs, H)
    assert "DEGENERATE_FLAT_PREDICTIONS" in card["details"] and card["calibrator"] is None and card["status"] == CAL.UNCALIBRATED
    assert not CAL.degeneracy(np.linspace(0.1, 0.9, 50))["flat"]
    assert CAL.degeneracy(0.5 + np.linspace(0, 0.004, 50))["near_flat"]
    with pytest.raises(ValueError):
        CAL.degeneracy([0.2, float("nan")])


def test_p10_an_always_negative_model_on_a_rare_event_shows_its_weakness():
    n = 500
    y = np.zeros(n)
    y[::100] = 1                                                       # 1% event, 5 positives
    p = np.full(n, 0.001)
    ref = np.full(n, y.mean())
    rep = CAL.score_report(y, p, ref, days=[str(i % 7) for i in range(n)], mints=[str(i) for i in range(n)], reps=200)
    assert rep["brier"] < 0.011                                       # a small Brier that looks good alone
    assert rep["bss"] <= 0 and rep["log_loss"] > rep["log_loss_ref"] and rep["log_loss_skill"] < 0
    assert rep["auc"] is None and "per class" in rep["auc_note"] and rep["degeneracy"]["flat"]


def test_p23_a_brier_and_log_loss_conflict_is_flagged_with_both_scores_and_counts():
    y = np.r_[np.ones(10), np.zeros(10)]
    p = np.r_[np.full(9, 0.95), [0.0], np.full(10, 0.05)]
    ref = np.full(20, 0.5)
    rep = CAL.score_report(y, p, ref, days=[str(i % 4) for i in range(20)], mints=[str(i) for i in range(20)], reps=300)
    assert rep["brier"] < rep["brier_ref"] and rep["log_loss"] > rep["log_loss_ref"]
    assert rep["conflict"] == "BRIER_LOGLOSS_CONFLICT"
    for k in ("n", "positives", "days", "brier", "log_loss", "bss", "log_loss_skill", "bss_intervals", "bss_governing"):
        assert rep[k] is not None
    assert set(rep["bss_intervals"]) == {"day", "mint"}
    agree = CAL.score_report(y, np.r_[np.full(10, 0.8), np.full(10, 0.2)], ref, days=["a"] * 20, mints=list("abcdefghijklmnopqrst"), reps=50)
    assert agree["conflict"] is None


def test_the_wider_bootstrap_interval_governs_the_score_report():
    rng = np.random.default_rng(9)
    y = (rng.random(200) < 0.3).astype(float)
    p = np.clip(0.3 + 0.3 * (y - 0.3) + rng.normal(0, 0.1, 200), 0.01, 0.99)
    rep = CAL.score_report(y, p, np.full(200, 0.3), days=[str(i // 40) for i in range(200)], mints=[str(i) for i in range(200)], reps=300)
    w = {k: v["ci"][1] - v["ci"][0] for k, v in rep["bss_intervals"].items()}
    assert rep["bss_governing"] == max(w, key=w.get)


# ---------------------------------------------------------------- rules 10 and 11: event-rate uncertainty and exchangeability
def test_block_intervals_of_the_event_rate_widen_with_clustered_days():
    y = np.r_[np.ones(40), np.zeros(10), np.zeros(45), np.ones(5), np.ones(20), np.zeros(30)]
    days = ["d1"] * 50 + ["d2"] * 50 + ["d3"] * 50
    out = CAL.base_rate_uncertainty(y, days=days, mints=[str(i) for i in range(150)], reps=2000)
    wl, wh = out["wilson"]
    gov = out["governing_interval"]
    assert out["governing"] == "day_block" and (gov[1] - gov[0]) > (wh - wl) and out["width_ratio_to_wilson"] > 1


def test_heterogeneity_rejects_different_day_rates_and_never_proves_exchangeability():
    y = np.r_[np.ones(40), np.zeros(10), np.zeros(45), np.ones(5)]
    het = CAL.heterogeneity(["a"] * 50 + ["b"] * 50, y, perms=2000)
    assert het["status"] == "EXCHANGEABILITY_REJECTED" and het["p"] < 0.05
    rng = np.random.default_rng(3)
    yy = (rng.random(200) < 0.3).astype(float)
    same = CAL.heterogeneity([str(i % 4) for i in range(200)], yy, perms=2000)
    assert same["status"] == "EXCHANGEABILITY_NOT_REJECTED_NOT_PROVED"
    assert CAL.heterogeneity(["a"] * 10, yy[:10], perms=10)["status"] == "UNDEFINED_ONE_GROUP_OR_ONE_CLASS"
    assert CAL.heterogeneity(["a", "b"] * 5, np.zeros(10), perms=10)["p"] is None


def test_prevalence_shift_is_a_two_sided_permutation_test():
    a, b = np.r_[np.ones(20), np.zeros(80)], np.r_[np.ones(50), np.zeros(50)]
    out = CAL.prevalence_shift(a, b, perms=2000)
    assert out["difference"] == pytest.approx(0.3) and out["p"] < 0.01
    assert CAL.prevalence_shift(a, a, perms=500)["p"] > 0.5


# ---------------------------------------------------------------- P39: drift
def test_p39_drift_alarms_after_a_step_and_never_before_it():
    stream = [(float(i), 0.0) for i in range(100)] + [(100.0 + i, 0.3) for i in range(60)]
    alarms = CAL.drift_alarm_times(stream)
    assert alarms and min(alarms) > 100.0
    assert not CAL.drift_at(alarms, 99.0) and CAL.drift_at(alarms, max(alarms))
    assert CAL.drift_alarm_times([(float(i), 0.0) for i in range(200)]) == []
    with pytest.raises(ValueError, match="P38"):
        CAL.drift_alarm_times([(0.0, 0.1), (1.0, float("nan"))])


# ---------------------------------------------------------------- cards
def test_a_card_is_calibrated_only_with_a_calibrator_and_passed_admissible_evidence():
    fit = rows(300, 90, seed=11)
    good_ev = evidence(120, 36, seed=12)
    card = CAL.build_card(T1, champion(), fit, H, level="SHADOW", evidence=good_ev, is_fixture=True)
    assert card["status"] == CAL.CALIBRATED and card["calibrator"]["method"] == "VENN_ABERS" and card["publishable"]
    CAL.verify_card(card)
    assert CAL.build_card(T1, champion(), fit, H, level="ABSTAIN", evidence=good_ev)["publishable"] is False
    pend = CAL.build_card(T1, champion(), fit, H, level="SHADOW", evidence={"status": "NOT_YET_MATURED"})
    assert pend["status"] == CAL.UNCALIBRATED and "CALIBRATION_EVIDENCE_PENDING" in pend["details"]
    none = CAL.build_card(T1, champion(), fit, H, level="SHADOW")
    assert none["status"] == CAL.UNCALIBRATED and "CALIBRATION_EVIDENCE_TOO_SMALL" in none["details"]
    small = CAL.build_card(T1, champion(), fit, H, level="SHADOW", evidence=evidence(40, 12))
    assert small["status"] == CAL.UNCALIBRATED and "CALIBRATION_EVIDENCE_TOO_SMALL" in small["details"]
    mid = CAL.build_card(T1, champion(), rows(150, 45, seed=13), H, level="SHADOW", evidence=good_ev)
    assert mid["calibrator"]["method"] == "PLATT"
    assert CAL.build_card(T1, None, fit, H, evidence=good_ev)["status"] == CAL.UNCALIBRATED


def test_an_overconfident_model_on_a_rare_class_is_never_calibrated():
    rng = np.random.default_rng(21)
    n = 300
    y = np.zeros(n, int)
    y[rng.choice(n, 6, replace=False)] = 1                             # 2% event
    s = np.clip(0.9 + rng.normal(0, 0.03, n), 0.01, 0.99)              # the model says about 90%
    assert not CAL.reliability(y, s)["in_the_large_ok"]
    card = CAL.build_card(T1, champion(), rows(n, 6, scores=s), H, level="SHADOW", evidence=evidence(60, 10))
    assert card["status"] == CAL.UNCALIBRATED and card["calibrator"] is None
    ev_bad = evidence(120, 3, scores=np.clip(0.9 + rng.normal(0, 0.03, 120), 0.01, 0.99))
    card2 = CAL.build_card(T1, champion(), rows(300, 90, seed=11), H, level="SHADOW", evidence=ev_bad)
    assert card2["status"] == CAL.UNCALIBRATED


def test_evidence_must_be_prospective_out_of_sample_and_not_the_fit_set():
    fit = rows(300, 90, seed=11)
    ev = evidence(60, 20)
    with pytest.raises(CAL.CalibrationError, match="only prospective"):
        CAL.build_card(T1, champion(), fit, H, evidence={**ev, "rows": [{**r, "split": "RETROSPECTIVE_HOLDOUT"} for r in ev["rows"]]})
    with pytest.raises(CAL.CalibrationError, match="only prospective"):
        CAL.build_card(T1, champion(), fit, H, evidence={**ev, "rows": [{**r, "split": "DEVELOPMENT"} for r in ev["rows"]]})
    early = [{**r, "decision_time": H + 3600, "label_matures_at": H + DAY} for r in ev["rows"][:1]] + ev["rows"][1:]
    with pytest.raises(CAL.CalibrationError, match="prospective start"):
        CAL.build_card(T1, champion(), fit, H, evidence={**ev, "rows": early})
    clash = [{**ev["rows"][0], "decision_key": fit[0]["decision_key"]}] + ev["rows"][1:]
    with pytest.raises(CAL.CalibrationError, match="overlaps the fit set"):
        CAL.build_card(T1, champion(), fit, H, evidence={**ev, "rows": clash})
    late = [{**ev["rows"][0], "label_matures_at": ev["cutoff"] + 1}] + ev["rows"][1:]
    with pytest.raises(CAL.CalibrationError, match="not matured"):
        CAL.build_card(T1, champion(), fit, H, evidence={**ev, "rows": late})
    with pytest.raises(CAL.CalibrationError, match="status"):
        CAL.build_card(T1, champion(), fit, H, evidence={"status": "OPENED_HOLDOUT"})


def test_cx13_platt_fitted_and_checked_on_the_spent_holdout_is_refused_at_every_step():
    """CX-13 (named before building): 66 opened holdout rows, Platt fitted and checked on the same rows, published."""
    hold = [{**r, "decision_time": H + 3600 * (i + 1), "label_matures_at": H + 3600 * (i + 1) + DAY, "scored_by_cutoff": H,
             "split": "RETROSPECTIVE_HOLDOUT"} for i, r in enumerate(rows(66, 15, seed=8))]
    after_opening = C.parse_utc("2026-10-26T18:00:00Z")
    with pytest.raises(CAL.CalibrationError, match="only development"):
        CAL.build_card(T1, champion(), hold, after_opening, level="SHADOW")
    relabelled = [{**r, "split": "DEVELOPMENT"} for r in hold]
    with pytest.raises(CAL.CalibrationError, match="not a development row"):
        CAL.build_card(T1, champion(), relabelled, after_opening, level="SHADOW")
    ev = {"status": "ADMISSIBLE", "rows": hold, "fit_cutoff": H, "cutoff": after_opening, "source": "RETROSPECTIVE_HOLDOUT"}
    with pytest.raises(CAL.CalibrationError):
        CAL.build_card(T1, champion(), rows(300, 90, seed=11), H, level="SHADOW", evidence=ev)
    assert CAL.fit_gate(66, 15, 7)                                     # and the fit gate refuses the size anyway


def test_card_sha_level_source_and_status_are_checked_on_load():
    card = CAL.build_card(T1, champion(), rows(300, 90, seed=11), H, level="SHADOW", evidence=evidence(120, 36, seed=12))
    back = CAL.loads(CAL.dumps(card))
    assert back == card
    t = json.loads(CAL.dumps(card))
    t["level"] = "VALIDATED_EXPERIMENTAL"
    with pytest.raises(CAL.CardHashMismatch):
        CAL.verify_card(t)
    t = dict(card, calibrator=None)
    t["card_sha"] = CAL.sha({k: v for k, v in t.items() if k != "card_sha"})
    with pytest.raises(CAL.CalibrationError, match="calibrator exists|status, details or publishable"):
        CAL.verify_card(t)
    t = dict(card, publishable=False)
    t["card_sha"] = CAL.sha({k: v for k, v in t.items() if k != "card_sha"})
    with pytest.raises(CAL.CalibrationError, match="publishable"):
        CAL.verify_card(t)
    with pytest.raises(CAL.CalibrationError, match="P27"):
        CAL.build_card(T1, champion(), rows(300, 90), H, source="BEHAVIORAL_SIMULATION")
    t = dict(card, source="BEHAVIORAL_SIMULATION")
    t["card_sha"] = CAL.sha({k: v for k, v in t.items() if k != "card_sha"})
    with pytest.raises(CAL.CalibrationError, match="P27"):
        CAL.verify_card(t)
    with pytest.raises(CAL.CalibrationError):
        CAL.build_card("exit_adjusted_target_before_invalidation_24h", champion(), rows(300, 90), H)
    with pytest.raises(CAL.CalibrationError):
        CAL.build_card(T1, champion(), rows(300, 90), H, level="PROMOTED")


def test_the_reference_holds_exactly_the_allowlisted_keys_with_the_card_numbers():
    card = CAL.build_card(T1, champion(), rows(300, 90, seed=11), H, level="SHADOW", evidence=evidence(120, 36, seed=12))
    ref = CAL.reference(card, support_n=40, support_k=12)
    assert tuple(sorted(ref)) == tuple(sorted(CAL.REFERENCE_KEYS))
    assert ref["holdout_n"] == 120 and ref["calibration_n"] == 300 and ref["calibration_card_sha"] == card["card_sha"]
    assert not any(k in C.FORBIDDEN_KEYS for k in ref)


# ---------------------------------------------------------------- isolation
def _imports(p: Path) -> set[str]:
    out = set()
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            out.add(("." * n.level) + (n.module or ""))
    return out


def test_the_phase_13_modules_use_numpy_and_the_standard_library_only_and_nothing_imports_them():
    std = {"__future__", "hashlib", "json", "math", "re", "pathlib", "typing", "datetime"}
    for name in ("calibration.py", "abstention.py"):
        p = ROOT / "memelab/predictive" / name
        got = {i for i in _imports(p) if not i.startswith(".")}
        assert got <= std | {"numpy"}, (name, got)
        txt = p.read_text()
        assert "sklearn" not in txt and "phase_06/sealed" not in txt and "predictive.evaluation" not in txt
        assert "import pickle" not in txt and "pickle.load" not in txt
    for p in (ROOT / "memelab").rglob("*.py"):
        if p.name in ("calibration.py", "abstention.py"):
            continue
        imps = _imports(p)
        assert not any(i.endswith("calibration") or i.endswith("abstention") for i in imps), p
        assert "predictive.calibration" not in p.read_text() and "predictive.abstention" not in p.read_text(), p


# ---------------------------------------------------------------- added after the first mutation probe (8 survivors)
def test_a_failed_check_on_enough_evidence_leaves_the_card_uncalibrated():
    fit = rows(300, 90, seed=11)
    ev = evidence(120, 36, seed=12)
    ev["rows"] = [dict(r, score=min(0.99, r["score"] + 0.45)) for r in ev["rows"]]     # the model says far more than happens
    card = CAL.build_card(T1, champion(), fit, H, level="SHADOW", evidence=ev)
    assert card["calibrator"] is not None and card["evidence"]["n"] == 120 and card["evidence"]["passed"] is False
    assert card["status"] == CAL.UNCALIBRATED and "CALIBRATION_CHECK_FAILED" in card["details"] and not card["publishable"]


def test_a_calibrator_that_returns_a_non_finite_number_is_refused():
    with pytest.raises(CAL.CalibrationError, match="P38"):
        CAL.apply_calibrator({"method": "PLATT", "params": {"a": float("nan"), "b": 0.0}}, [0.3])
    with pytest.raises(CAL.CalibrationError, match="P38"):
        CAL.apply_calibrator({"method": "PLATT", "params": {"a": float("inf"), "b": -float("inf")}}, [0.0])


def test_a_permutation_p_value_is_never_zero():
    y = np.r_[np.ones(50), np.zeros(50)]
    het = CAL.heterogeneity(["a"] * 50 + ["b"] * 50, y, perms=50)
    assert het["p"] == pytest.approx(1 / 51)
    sh = CAL.prevalence_shift(np.zeros(50), np.ones(50), perms=40)
    assert sh["p"] == pytest.approx(1 / 41)


# ---------------------------------------------------------------- repair pass 2 after the independent skeptic (PI-D-070, PI-D-071)
def _platt_reference(s, y, digits=60):
    """Independent Platt solution: Newton steps on the smoothed-target log loss in decimal arithmetic (no numpy)."""
    from decimal import Decimal, getcontext
    getcontext().prec = digits
    n1, n0 = sum(1 for v in y if v > 0), sum(1 for v in y if v <= 0)
    one = Decimal(1)
    t = [Decimal(n1 + 1) / Decimal(n1 + 2) if v > 0 else one / Decimal(n0 + 2) for v in y]
    S = [Decimal(repr(float(v))) for v in s]
    a, b = Decimal(0), (Decimal(n0 + 1) / Decimal(n1 + 1)).ln()
    for _ in range(100):
        ga = gb = haa = hab = hbb = Decimal(0)
        for si, ti in zip(S, t):
            f = a * si + b
            p = one / (one + f.exp())
            r, w = ti - p, p * (one - p)
            ga += r * si
            gb += r
            haa += w * si * si
            hab += w * si
            hbb += w
        det = haa * hbb - hab * hab
        da, db = (hbb * ga - hab * gb) / det, (-hab * ga + haa * gb) / det
        a, b = a - da, b - db
        if max(abs(da), abs(db)) < Decimal(10) ** -40:
            break
    return float(a), float(b), float(max(abs(ga), abs(gb)))


PLATT_SETS = {
    # the recorded T2 calibration set (8 development out-of-sample rows, public in phase_13/calibration/CALIBRATION_SETS.csv)
    "t2_like": ([0.212651593748, 0.72456567455, 0.027283286595, 0.244477767214, 0.089198227979, 0.08182020118, 0.001420123565, 0.027401468616], [1, 0, 0, 0, 0, 0, 0, 0]),
}


@pytest.mark.parametrize("name", ["t2_like", "synthetic_30", "synthetic_300"])
def test_rp2_numpy_platt_equals_a_60_digit_newton_solution(name):
    """G7 decision (PI-D-071): the numpy Platt is pinned to an independent exact solution within 1e-9 and its gradient."""
    if name in PLATT_SETS:
        s, y = PLATT_SETS[name]
    else:
        n = int(name.split("_")[1])
        rng = np.random.default_rng(n)
        y = (rng.random(n) < 0.3).astype(int).tolist()
        s = np.clip(0.2 + 0.3 * np.array(y) + rng.normal(0, 0.12, n), 0.01, 0.99).tolist()
    a_ref, b_ref, g_ref = _platt_reference(s, y)
    assert g_ref < 1e-30
    pl = K.Platt().fit(np.asarray(s, float), np.asarray(y, float))
    assert abs(pl.a_ - a_ref) <= 1e-9 and abs(pl.b_ - b_ref) <= 1e-9
    yy = np.asarray(y, float)
    n1, n0 = yy.sum(), (1 - yy).sum()
    t = np.where(yy > 0, (n1 + 1) / (n1 + 2), 1 / (n0 + 2))
    p = pl.predict(np.asarray(s, float))
    assert max(abs(np.sum((t - p) * np.asarray(s))), abs(np.sum(t - p))) < 1e-10


def test_rp2_support_ties_go_to_the_lower_bin_and_alpha_is_frozen():
    import inspect
    bins = [{"n": 20, "k": 2, "p_min": 0.1, "p_max": 0.2}, {"n": 20, "k": 8, "p_min": 0.3, "p_max": 0.4}]
    assert CAL.support_of(bins, 0.25)["k"] == 2
    assert inspect.signature(CAL.heterogeneity).parameters["alpha"].default == 0.05


def test_rp2_a_card_of_another_registry_is_refused():
    card = CAL.build_card(T1, champion(), rows(300, 90, seed=11), H, level="SHADOW", evidence=evidence(120, 36, seed=12))
    c = dict(card, registry_sha="0" * 64)
    c["card_sha"] = CAL.sha({k: v for k, v in c.items() if k != "card_sha"})
    with pytest.raises(CAL.CalibrationError, match="registry"):
        CAL.verify_card(c)


def test_rp2_evidence_from_another_source_is_refused_at_build():
    ev = evidence(60, 20)
    with pytest.raises(CAL.CalibrationError, match="spent"):
        CAL.build_card(T1, champion(), rows(300, 90, seed=11), H, evidence={**ev, "source": "RETROSPECTIVE_HOLDOUT"})


def test_rp2_cards_record_their_availability():
    card = CAL.build_card(T1, champion(), rows(300, 90, seed=11), H, level="SHADOW", evidence=evidence(120, 36, seed=12))
    assert card["available_at"] == card["evidence"]["as_of"] > H and card["evidence"]["score_range"][0] <= card["evidence"]["score_range"][1]
    pend = CAL.build_card(T1, champion(), rows(30, 9), H, evidence={"status": "NOT_YET_MATURED", "source": "PROSPECTIVE_HOLDOUT"})
    assert pend["available_at"] == H and pend["evidence"]["as_of"] is None
