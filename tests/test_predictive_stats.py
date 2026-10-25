"""Phase 07: the numpy statistical engine (memelab/predictive/stats.py), ported from the Phase 04 prototype with its tests.

The prototype tests ran on the Phase 04 BAKEOFF_ONLY sample; here every case runs on a seeded synthetic sample of the same
shape (24 h labels, UTC days, mints shared across days), so no bake-off label is read (PI-D-035). Hand-computed values for the
scores. No network, no clock, no third-party oracle (scikit-learn agreement is measured in
audits/predictive-intelligence/phase_07/probes/sklearn_crosscheck.py).
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from memelab.predictive import contract as C
from memelab.predictive import stats as K

T1 = "price_path_target_before_invalidation_24h"
LAG_24H = C.label_matures_at(T1, 0.0)                 # entry lag + horizon + fetch margin of T1
FIRST = C.parse_utc("2026-10-11T00:00:00Z")            # the frozen first_last_train_day


@pytest.fixture(scope="module")
def dev24():
    rng = np.random.default_rng(11)
    t = np.sort(C.parse_utc("2026-10-07T00:00:00Z") + rng.uniform(0, 9 * 86400, 150))
    m = t + LAG_24H
    mints = [f"m{int(i) % 60}" for i in rng.integers(0, 60, 150)]
    return {"t": t, "m": m, "mints": mints}


def folds_of(d, mat=None, min_train=30):
    return K.day_walk_forward(d["t"], d["m"] if mat is None else mat, first_last_train_day=FIRST, min_train=min_train)


# ---------------------------------------------------------------- ported from phase_04/adoption/prototypes/test_core_numpy.py
def test_lab_rule_is_valid_and_the_purge_mutation_is_refused(dev24):
    d = dev24
    a = K.fold_audit(d["t"], d["m"], folds_of(d), len(d["t"]), min_maturity_lag_s=LAG_24H, groups=d["mints"])
    assert a["valid_walk_forward"] and not a["reasons"] and len(a["folds"]) >= 3
    leaky = folds_of(d, mat=np.minimum(d["m"], d["t"]))
    b = K.fold_audit(d["t"], d["m"], leaky, len(d["t"]))
    assert not b["valid_walk_forward"]
    assert sum(r["train_labels_maturing_after_cutoff"] for r in b["folds"]) > 0


def test_a_nan_test_decision_time_makes_the_audit_invalid(dev24):
    d = dev24
    leaky = folds_of(d, mat=np.minimum(d["m"], d["t"]))
    t = d["t"].copy()
    for f in leaky:
        t[f["test"][0]] = np.nan
    a = K.fold_audit(t, d["m"], leaky, len(t))
    assert not a["valid_walk_forward"] and any("non_finite_times" in r for r in a["reasons"])
    clean = folds_of(d)
    t2 = d["t"].copy()
    t2[clean[0]["test"][0]] = np.nan
    assert not K.fold_audit(t2, d["m"], clean, len(t2))["valid_walk_forward"]


def test_nan_maturity_on_leaking_rows_makes_the_audit_invalid(dev24):
    d = dev24
    leaky = folds_of(d, mat=np.minimum(d["m"], d["t"]))
    m = d["m"].copy()
    for f in leaky:
        tr = f["train"]
        m[tr[m[tr] > f["cutoff"]]] = np.nan
    assert not K.fold_audit(d["t"], m, leaky, len(m))["valid_walk_forward"]


def test_a_cutoff_after_the_test_start_is_invalid(dev24):
    d = dev24
    folds = [dict(f, cutoff=f["cutoff"] + 2 * 86400) for f in folds_of(d)]
    a = K.fold_audit(d["t"], d["m"], folds, len(d["t"]))
    assert not a["valid_walk_forward"] and all(r["cutoff_after_test_start"] for r in a["folds"])
    nan_cut = [dict(f, cutoff=float("nan")) for f in folds_of(d)]
    assert not K.fold_audit(d["t"], d["m"], nan_cut, len(d["t"]))["valid_walk_forward"]


def test_p20_a_maturity_column_of_a_shorter_horizon_is_refused(dev24):
    d = dev24
    m6 = d["t"] + C.label_matures_at("price_path_target_before_invalidation_6h", 0.0)
    folds = folds_of(d, mat=m6)
    assert K.fold_audit(d["t"], m6, folds, len(d["t"]))["valid_walk_forward"]          # without the target's lag it passes
    a = K.fold_audit(d["t"], m6, folds, len(d["t"]), min_maturity_lag_s=LAG_24H)
    assert not a["valid_walk_forward"]
    assert all(r["maturity_shorter_than_target"] == r["train"] + r["test"] for r in a["folds"])


def test_p14_shared_groups_are_reported_not_hidden(dev24):
    d = dev24
    a = K.fold_audit(d["t"], d["m"], folds_of(d), len(d["t"]), groups=d["mints"])
    assert a["valid_walk_forward"] and any(r["test_rows_sharing_group_with_training"] for r in a["folds"])


def test_splitter_refuses_non_finite_times(dev24):
    d = dev24
    t = d["t"].copy()
    t[5] = np.nan
    with pytest.raises(ValueError):
        K.day_walk_forward(t, d["m"], first_last_train_day=FIRST, min_train=30)


def test_platt_on_constant_scores_predicts_the_mean_smoothed_target():
    y = np.array([1.0] * 30 + [0.0] * 70)
    p = K.Platt().fit(np.full(100, 0.3), y).predict(np.array([0.3, 5.0]))
    tbar = (30 * (31 / 32) + 70 * (1 / 72)) / 100
    assert np.allclose(p, tbar, atol=1e-15)
    with pytest.raises(ValueError):
        K.Platt().fit(np.full(10, 0.3), np.zeros(10))


def test_fail_closed_inputs():
    X = np.random.default_rng(1).normal(size=(50, 2))
    with pytest.raises(ValueError):
        K.Logistic().fit(X, np.zeros(50))
    X[3, 1] = np.nan
    with pytest.raises(ValueError):
        K.Logistic().fit(X, (np.arange(50) % 3 == 0).astype(float))
    with pytest.raises(ValueError):
        K.venn_abers(np.array([0.1, 0.2, math.nan]), np.array([0.0, 1.0, 1.0]), np.array([0.5]))


# ---------------------------------------------------------------- the frozen walk-forward rule itself
def test_first_fold_is_extended_by_whole_days_until_the_minimum(dev24):
    d = dev24
    f100 = folds_of(d, min_train=100)
    assert f100 and all(len(f["train"]) >= 100 for f in f100)
    assert f100[0]["cutoff"] % 86400 == 0 and f100[0]["cutoff"] >= FIRST + 86400
    first_ok = min(c for c in np.arange(FIRST + 86400, FIRST + 20 * 86400, 86400)
                   if np.sum((d["t"] < c) & (d["m"] <= c)) >= 100)
    assert f100[0]["cutoff"] == first_ok
    for f in f100:
        assert np.all(d["t"][f["train"]] < f["cutoff"]) and np.all(d["m"][f["train"]] <= f["cutoff"])
        assert np.all((d["t"][f["test"]] >= f["cutoff"]) & (d["t"][f["test"]] < f["cutoff"] + 86400))


# ---------------------------------------------------------------- scores, hand values
def test_brier_log_loss_and_skill_hand_values():
    y, p = np.array([0, 1, 1, 0.0]), np.array([0.1, 0.8, 0.6, 0.3])
    assert K.brier(y, p) == pytest.approx((0.01 + 0.04 + 0.16 + 0.09) / 4, abs=1e-15)
    assert K.log_loss(y, p) == pytest.approx(-np.mean(np.log([0.9, 0.8, 0.6, 0.7])), abs=1e-15)
    assert K.brier_skill(y, p, np.full(4, 0.5)) == pytest.approx(1 - 0.075 / 0.25, abs=1e-15)
    assert math.isnan(K.brier_skill(np.array([1.0, 1.0]), np.array([0.9, 0.9]), np.array([1.0, 1.0])))


def test_p38_probabilities_outside_0_1_or_nan_are_refused():
    for bad in ([0.5, 1.2], [0.5, -0.1], [0.5, np.nan], [np.inf, 0.2], []):
        with pytest.raises(ValueError):
            K.brier(np.array([0, 1][: len(bad)], float), np.array(bad, float))
    with pytest.raises(ValueError):
        K.brier(np.array([0, 2.0]), np.array([0.1, 0.2]))


def test_roc_auc_and_average_precision_hand_values_with_ties():
    y, s = np.array([0, 0, 1, 1.0]), np.array([0.1, 0.4, 0.35, 0.8])
    assert K.roc_auc(y, s) == pytest.approx(0.75, abs=1e-15)
    assert K.average_precision(y, s) == pytest.approx(0.5 + 0.5 * 2 / 3, abs=1e-15)
    y2, s2 = np.array([1, 0, 1, 0.0]), np.array([0.5, 0.5, 0.5, 0.1])
    assert K.roc_auc(y2, s2) == pytest.approx(0.75, abs=1e-15)
    assert K.average_precision(y2, s2) == pytest.approx(2 / 3, abs=1e-15)
    y3, s3 = np.array([0, 1, 1, 0.0]), np.array([0.5, 0.5, 0.9, 0.1])   # a positive tied with a negative counts one half
    assert K.roc_auc(y3, s3) == pytest.approx(0.875, abs=1e-15)
    with pytest.raises(ValueError):
        K.roc_auc(np.zeros(4), s)


def test_wilson_and_holm_hand_values():
    lo, hi = K.wilson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(0.27753, abs=1e-5)
    lo, hi = K.wilson(5, 10)
    assert lo == pytest.approx(0.23659, abs=1e-5) and hi == pytest.approx(0.76341, abs=1e-5)
    assert K.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    adj = K.holm([0.01, float("nan"), 0.03])                  # an undefined test still counts in the family of three
    assert adj[0] == pytest.approx(0.03) and math.isnan(adj[1]) and adj[2] == pytest.approx(0.06)


def test_p11_p24_calibration_bins_rules():
    rng = np.random.default_rng(5)
    p = rng.uniform(0.05, 0.6, 100)
    y = (rng.uniform(size=100) < p).astype(float)
    cal = K.calibration_bins(y, p)
    assert len(cal["bins"]) == 5 and all(b["n"] == 20 for b in cal["bins"]) and cal["ece"] is not None
    small = K.calibration_bins(y[:39], p[:39])
    assert small["bins"] == [] and small["every_bin_ok"] is None and "in the large only" in small["note"]
    flat = K.calibration_bins(y, np.full(100, 0.99))                   # P11: flat all-positive predictions
    assert not flat["in_the_large_ok"] and not flat["every_bin_ok"]
    assert len(K.calibration_bins(y[:60], p[:60])["bins"]) == 3          # 60 // 20


def test_group_bootstrap_resamples_whole_groups_and_ess():
    groups = [f"d{i // 10}" for i in range(50)]                           # 5 groups of 10 identical values
    v = np.repeat(np.arange(5, dtype=float), 10)
    bs = K.group_bootstrap(groups, lambda idx: float(np.mean(v[idx])), reps=500, seed=1)
    assert bs["groups"] == 5 and bs["finite"] == 500
    assert set(np.round(bs["values"] * 5, 9)) <= set(range(0, 21))     # a mean of 5 whole groups
    assert K.design_effect_ess(groups, v, reps=2000, seed=1) == pytest.approx(50 * 5 / 49, rel=0.15)   # n var_iid / var_groups
    one = K.group_bootstrap(["a"] * 7, lambda idx: float(len(idx)), reps=10)
    assert one["ci"] == (7.0, 7.0)
    a1 = K.group_bootstrap(groups, lambda idx: float(np.mean(v[idx])), reps=200, seed=9)
    a2 = K.group_bootstrap(groups, lambda idx: float(np.mean(v[idx])), reps=200, seed=9)
    assert np.array_equal(a1["values"], a2["values"])


def test_logistic_reaches_the_penalised_optimum_and_round_trips():
    rng = np.random.default_rng(2)
    X = rng.normal(size=(200, 3))
    y = (rng.uniform(size=200) < K.sigmoid(X @ np.array([1.0, -0.5, 0.0]) - 0.3)).astype(float)
    lr = K.Logistic(C=1.0).fit(X, y)
    A = np.hstack([np.ones((200, 1)), X])
    g = A.T @ (lr.predict_proba1(X) - y) + np.r_[0.0, lr.coef_]
    assert np.max(np.abs(g)) < 1e-9
    back = K.Logistic.from_dict(lr.to_dict())
    assert np.array_equal(back.predict_proba1(X), lr.predict_proba1(X))


def test_prep_is_fitted_on_training_rows_only_and_round_trips():
    tr = np.array([[1.0, 5.0, 2.0], [3.0, np.nan, 2.0], [5.0, 7.0, 2.0]])
    te = np.array([[100.0, np.nan, 9.0]])
    prep = K.Prep().fit(tr)
    assert list(prep.keep) == [0, 1] and list(prep.ind) == [1]           # constant column dropped, indicator for column 1
    assert prep.med.tolist() == [3.0, 6.0]
    z = prep.transform(te)
    assert z.shape == (1, 3) and np.all(np.isfinite(z))
    back = K.Prep.from_dict(prep.to_dict())
    assert np.array_equal(back.transform(te), z)
    with pytest.raises(ValueError):
        prep.transform(np.ones((1, 2)))


def test_venn_abers_bounds_and_pooled_ties():
    rng = np.random.default_rng(4)
    s = np.round(rng.uniform(size=40), 1)
    y = (rng.uniform(size=40) < s).astype(float)
    p0, p1, p = K.venn_abers(s, y, np.array([0.05, 0.5, 0.95, 2.0]))
    assert np.all(p0 <= p1 + 1e-15) and np.all((p >= 0) & (p <= 1))


def test_page_hinkley_detects_a_shift_and_refuses_nan():
    ph = K.PageHinkley(threshold=5.0, min_obs=10)
    hits = [ph.update(0.0) for _ in range(50)] + [ph.update(1.0) for _ in range(50)]
    assert not any(hits[:50]) and any(hits[50:])
    with pytest.raises(ValueError):
        K.PageHinkley().update(float("nan"))
