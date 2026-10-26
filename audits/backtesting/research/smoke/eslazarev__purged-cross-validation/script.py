"""Smoke test for purgedcv 0.1.11 (eslazarev/purged-cross-validation @ 07692dd862d3).

Deterministic, synthetic, no network. purgedcv is a CV splitter, not a fill
engine, so instead of fill timing this checks the split chronology the lab
needs: 30 hourly bars, one decision per bar close, each label/trade lives
3 bars ([decision_time, decision_time + 3h)). An independent checker (not the
library's own asserts) verifies that no training row's label interval overlaps
any test interval, that the embargo is respected, and that walk-forward train
rows end before the test fold. Also probes unsorted times, tz-aware input,
PurgedGroupKFold for token cohorts, and DSR determinism.
"""

import sys

import numpy as np
import pandas as pd

import purgedcv
from purgedcv import (
    PurgedGroupKFold,
    PurgedKFold,
    WalkForwardSplit,
    deflated_sharpe_ratio,
)
from purgedcv.diagnostics import (
    assert_embargo_respected,
    assert_no_temporal_leakage,
    audit_splitter,
)

N = 30
HORIZON = pd.Timedelta(hours=3)
EMBARGO = pd.Timedelta(hours=2)
T0 = pd.Timestamp("2026-01-01 00:00")
bar_open = pd.Series(pd.date_range(T0, periods=N, freq="h"))
decision = bar_open + pd.Timedelta(hours=1)  # decided at bar close
label_end = decision + HORIZON  # trade/label resolves 3 bars later
X = np.arange(N, dtype=float).reshape(-1, 1)

failures = []
warnings_ = []


def overlaps(a0, a1, b0, b1):
    return (a0 < b1) and (b0 < a1)


def independent_check(name, train, test, embargo=None, walk_forward=False):
    t0 = decision.iloc[test]
    t1 = label_end.iloc[test]
    bad = []
    for i in train:
        for s, e in zip(t0, t1):
            if overlaps(decision.iloc[i], label_end.iloc[i], s, e):
                bad.append(int(i))
                break
    if bad:
        failures.append(f"{name}: train rows overlap test horizon: {bad}")
    if embargo is not None:
        hi = t1.max()
        emb = [int(i) for i in train if hi <= decision.iloc[i] <= hi + embargo]
        if emb:
            failures.append(f"{name}: embargo violated by rows {emb}")
    if walk_forward and len(train):
        if label_end.iloc[train].max() > t0.min():
            failures.append(f"{name}: walk-forward train label ends after test start")
    return bad


print(f"purgedcv {purgedcv.__version__}, numpy {np.__version__}, pandas {pd.__version__}")

print("\n[1] PurgedKFold(n_splits=5, embargo=2h), label horizon 3h")
cv = PurgedKFold(5, prediction_times=decision, evaluation_times=label_end, embargo=EMBARGO)
plain = PurgedKFold(5, prediction_times=decision, evaluation_times=decision)  # zero-length labels
for k, ((tr, te), (tr0, _)) in enumerate(zip(cv.split(X), plain.split(X))):
    dropped = sorted(int(i) for i in set(tr0) - set(tr))
    print(f"fold {k}: test={te.min()}..{te.max()} train_n={len(tr)} dropped_by_purge_embargo={dropped}")
    independent_check(f"pkf fold {k}", tr, te, embargo=EMBARGO)
    assert_no_temporal_leakage(tr, te, decision, label_end)
    assert_embargo_respected(tr, te, decision, label_end, EMBARGO)

print("\n[2] WalkForwardSplit(n_splits=3, test_size=5, expanding)")
wf = WalkForwardSplit(3, 5, prediction_times=decision, evaluation_times=label_end)
for k, (tr, te) in enumerate(wf.split(X)):
    print(f"fold {k}: train=0..{tr.max()} (n={len(tr)}) test={te.min()}..{te.max()}")
    independent_check(f"wf fold {k}", tr, te, walk_forward=True)

print("\n[3] WalkForwardSplit sliding train_size=8")
wfs = WalkForwardSplit(3, 5, train_size=8, window="sliding", prediction_times=decision, evaluation_times=label_end)
for k, (tr, te) in enumerate(wfs.split(X)):
    print(f"fold {k}: train={tr.min()}..{tr.max()} (n={len(tr)}) test={te.min()}..{te.max()}")
    independent_check(f"wfs fold {k}", tr, te, walk_forward=True)

print("\n[4] audit_splitter report (PurgedKFold)")
rep = audit_splitter(cv, X)
print("columns:", list(rep.columns))
with pd.option_context("display.width", 200, "display.max_columns", 30):
    print(rep.to_string(index=False))

print("\n[5] unsorted prediction times (async event rows out of order)")
shuffled = decision.sample(frac=1.0, random_state=7).reset_index(drop=True)
try:
    PurgedKFold(5, prediction_times=shuffled, evaluation_times=shuffled + HORIZON)
    print("accepted unsorted times (no error)")
    failures.append("unsorted times accepted silently")
except ValueError as e:
    print(f"rejected: {e}")

print("\n[6] tz-aware UTC input")
dz = decision.dt.tz_localize("UTC")
cvz = PurgedKFold(5, prediction_times=dz, evaluation_times=dz + HORIZON, embargo=EMBARGO)
same = all(np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1]) for a, b in zip(cvz.split(X), cv.split(X)))
print(f"tz-aware splits identical to naive: {same}")
if not same:
    failures.append("tz-aware splits differ")

print("\n[7] PurgedGroupKFold by token (3 tokens x 10 bars, interleaved times)")
print("(token cohort CV: does leave-token-out keep any training rows when tokens trade concurrently?)")
tok = pd.Series(np.tile(["A", "B", "C"], 10))
gcv = PurgedGroupKFold(3, prediction_times=decision, evaluation_times=label_end, groups=tok)
for k, (tr, te) in enumerate(gcv.split(X)):
    tr_tok, te_tok = set(tok.iloc[tr]), set(tok.iloc[te])
    print(f"fold {k}: test tokens={sorted(te_tok)} train tokens={sorted(tr_tok)} train_n={len(tr)}")
    if tr_tok & te_tok:
        failures.append(f"group fold {k}: token in both train and test")
    if len(tr) == 0:
        warnings_.append(f"group fold {k}: EMPTY training set, no error raised (concurrent tokens are all purged by time overlap)")
    independent_check(f"gkf fold {k}", tr, te)

print("\n[8] deflated_sharpe_ratio determinism")
rng = np.random.default_rng(42)
r = rng.normal(0.001, 0.01, 500)
d1 = deflated_sharpe_ratio(r, n_trials=20, var_sharpe=0.01)
d2 = deflated_sharpe_ratio(r, n_trials=20, var_sharpe=0.01)
d_one = deflated_sharpe_ratio(r, n_trials=1, var_sharpe=0.01)
print(f"DSR(n=20)={d1:.6f} repeat={d2:.6f} DSR(n=1)={d_one:.6f}")
if d1 != d2 or not (d1 <= d_one):
    failures.append("DSR not deterministic or not decreasing in n_trials")

for w in warnings_:
    print("WARNING:", w)
print("\nRESULT:", "PASS" if not failures else "FAIL")
for f in failures:
    print(" -", f)
sys.exit(0 if not failures else 1)
