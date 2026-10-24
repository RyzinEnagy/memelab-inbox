"""Phase 04 repair (skeptic m1, m7): tests for the numpy prototype's fold audit, splitter and Platt edge case. They live with the
prototype (not in tests/, which the lab suite collects) and must be ported with the code in Phase 07 (ROADMAP).

    python -m pytest audits/predictive-intelligence/phase_04/adoption/prototypes/test_core_numpy.py -q
"""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bakeoff as B  # noqa: E402
import core_numpy as K  # noqa: E402

LAG_24H = 300 + 86400 + 900           # entry lag + horizon + fetch margin of T1 (contract.label_matures_at)


@pytest.fixture(scope="module")
def dev24():
    d = B.load("dev24")
    first = 1791763200.0 - 86400       # 2026-10-11T00:00Z, the frozen first_last_train_day
    return d, first


def lab_folds(d, first, mat=None):
    return K.day_walk_forward(d["t"], d["m"] if mat is None else mat, first_last_train_day=first, min_train=30)


def test_lab_rule_is_valid_and_the_purge_mutation_is_refused(dev24):
    d, first = dev24
    a = K.fold_audit(d["t"], d["m"], lab_folds(d, first), len(d["t"]), min_maturity_lag_s=LAG_24H, groups=d["ids"])
    assert a["valid_walk_forward"] and not a["reasons"] and len(a["folds"]) == 4
    leaky = lab_folds(d, first, mat=np.minimum(d["m"], d["t"]))
    b = K.fold_audit(d["t"], d["m"], leaky, len(d["t"]))
    assert not b["valid_walk_forward"]
    assert sum(r["train_labels_maturing_after_cutoff"] for r in b["folds"]) == 31


def test_a_nan_test_decision_time_makes_the_audit_invalid(dev24):
    d, first = dev24
    leaky = lab_folds(d, first, mat=np.minimum(d["m"], d["t"]))
    t = d["t"].copy()
    for f in leaky:
        t[f["test"][0]] = np.nan                 # the skeptic's case A: one NaN test time per fold hid every leak
    a = K.fold_audit(t, d["m"], leaky, len(t))
    assert not a["valid_walk_forward"] and any("non_finite_times" in r for r in a["reasons"])
    clean = lab_folds(d, first)
    t2 = d["t"].copy()
    t2[clean[0]["test"][0]] = np.nan
    assert not K.fold_audit(t2, d["m"], clean, len(t2))["valid_walk_forward"]


def test_nan_maturity_on_leaking_rows_makes_the_audit_invalid(dev24):
    d, first = dev24
    leaky = lab_folds(d, first, mat=np.minimum(d["m"], d["t"]))
    m = d["m"].copy()
    for f in leaky:
        tr = f["train"]
        m[tr[m[tr] > f["cutoff"]]] = np.nan      # case A2: NaN on exactly the leaking rows
    a = K.fold_audit(d["t"], m, leaky, len(m))
    assert not a["valid_walk_forward"]


def test_a_cutoff_after_the_test_start_is_invalid(dev24):
    d, first = dev24
    folds = [dict(f, cutoff=f["cutoff"] + 2 * 86400) for f in lab_folds(d, first)]     # case B
    a = K.fold_audit(d["t"], d["m"], folds, len(d["t"]))
    assert not a["valid_walk_forward"] and all(r["cutoff_after_test_start"] for r in a["folds"])
    nan_cut = [dict(f, cutoff=float("nan")) for f in lab_folds(d, first)]
    assert not K.fold_audit(d["t"], d["m"], nan_cut, len(d["t"]))["valid_walk_forward"]


def test_a_maturity_column_of_a_shorter_horizon_is_refused(dev24):
    d, first = dev24
    m6 = d["t"] + 300 + 21600 + 900                       # case C: 6 h maturities supplied for 24 h labels
    folds = lab_folds(d, first, mat=m6)
    assert K.fold_audit(d["t"], m6, folds, len(d["t"]))["valid_walk_forward"]          # without the target's lag it passes
    a = K.fold_audit(d["t"], m6, folds, len(d["t"]), min_maturity_lag_s=LAG_24H)
    assert not a["valid_walk_forward"]
    assert all(r["maturity_shorter_than_target"] == r["train"] + r["test"] for r in a["folds"])     # every row of every fold


def test_shared_groups_are_reported_not_hidden(dev24):
    d, first = dev24
    import csv
    mints = [r["mint"] for r in csv.DictReader(open(B.DATA / "dev_t1_24h.csv"))]
    a = K.fold_audit(d["t"], d["m"], lab_folds(d, first), len(d["t"]), groups=mints)
    assert [r["test_rows_sharing_group_with_training"] for r in a["folds"]] == [1, 4, 4, 1]     # case D, reproduced
    assert a["valid_walk_forward"]


def test_splitter_refuses_non_finite_times(dev24):
    d, first = dev24
    t = d["t"].copy()
    t[5] = np.nan
    with pytest.raises(ValueError):
        K.day_walk_forward(t, d["m"], first_last_train_day=first, min_train=30)


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
