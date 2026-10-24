"""Phase 03 R2 smoke for ip200/venn-abers at 60767e41 (installed from the pinned source, version 1.5.4, Python 3.13).
Run: python -I smoke_venn_abers.py   (the runner adds unshare -n so no network is available)
"""
import os
import pickle
import sys
import time
import warnings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import common as C  # noqa: E402
import venn_abers  # noqa: E402
from venn_abers import VennAbers, VennAbersCalibrator  # noqa: E402

warnings.simplefilter("ignore", RuntimeWarning)
C.header(f"venn_abers from {venn_abers.__file__}")
df, sha = C.load()
print("challenge sha256", sha)
tr, cal, ho, info = C.splits(df)
print("splits", info)
X = C.design(df, C.FEATURES)
y = df.label.to_numpy()
Xtr, ytr = X[tr], y[tr].astype(int)
Xc, yc = X[cal], y[cal].astype(int)
Xh, yh = X[ho], y[ho].astype(int)
base_rate = float(ytr.mean())
print(f"train prevalence (baseline B0) = {base_rate:.5f}; calibration positives = {int(yc.sum())}/{len(yc)}")

base = C.base_pipeline().fit(Xtr, ytr)
s_cal = base.predict_proba(Xc)
s_ho = base.predict_proba(Xh)
p_ho = s_ho[:, 1]
print(f"base cal pred_hash={C.pred_hash(s_cal[:, 1])} holdout pred_hash={C.pred_hash(p_ho)}")

print("\n--- S1 leak trap ---")
Xl = C.design(df, C.FEATURES + [C.TRAP])
leaky = C.base_pipeline().fit(Xl[tr], ytr)
va_l = VennAbers().fit(leaky.predict_proba(Xl[cal]), yc)
pl, _ = va_l.predict_proba(leaky.predict_proba(Xl[ho]))
C.score_block("S1 base (legit features)", yh, p_ho, base_rate)
C.score_block("S1 leaky (+leak_future_ret) + Venn-Abers", yh, pl[:, 1], base_rate)
print("venn-abers has no feature-availability or time mechanism: the calibrated leaky model keeps its inflated score.")

print("\n--- S2/S4 Venn-Abers on the shared base scores (manual prefit path) ---")
t0 = time.perf_counter()
va = VennAbers().fit(s_cal, yc)
fit_s = time.perf_counter() - t0
t0 = time.perf_counter()
pp, p0p1 = va.predict_proba(s_ho)
pred_s = time.perf_counter() - t0
pv = pp[:, 1]
w = p0p1[:, 1] - p0p1[:, 0]
print(f"fit {fit_s*1000:.2f} ms; predict {pred_s/len(yh)*1e6:.2f} us/row; output shape {pp.shape}; rows sum to 1: {np.allclose(pp.sum(1), 1)}")
print(f"interval p1-p0: median={np.median(w):.4f} p90={np.quantile(w, 0.9):.4f} max={w.max():.4f}; p0<=p1 all: {bool(np.all(p0p1[:,0] <= p0p1[:,1] + 1e-12))}")
C.score_block("S2 base", yh, p_ho, base_rate)
C.print_reliability("S2 base", yh, p_ho)
C.score_block("S4 venn-abers merged p", yh, pv, base_rate)
C.print_reliability("S4 venn-abers merged p", yh, pv)
cover_int = (yh >= p0p1[:, 0]) & (yh <= p0p1[:, 1])
print(f"interval [p0,p1] is a probability interval, not a set: mean p0={p0p1[:,0].mean():.4f} mean p1={p0p1[:,1].mean():.4f} "
      f"observed prevalence={yh.mean():.4f} inside [mean p0, mean p1]: {p0p1[:,0].mean() <= yh.mean() <= p0p1[:,1].mean()}")
manual = VennAbersCalibrator().predict_proba(p_cal=s_cal, y_cal=yc, p_test=s_ho)
print(f"VennAbersCalibrator manual mode equals VennAbers class: {np.array_equal(manual, pp)}")

print("\nS4b correctness against the definition (isotonic fit with the test score appended)")
probe = np.concatenate([p_ho, [s_cal[:, 1].max() + 1e-3, min(s_cal[:, 1].max() + 0.2, 0.999), s_cal[:, 1].min() / 2]])
_, q = va.predict_proba(np.column_stack([1 - probe, probe]))
bp0, bp1 = C.venn_abers_bruteforce(s_cal[:, 1], yc, probe)
print(f"{len(probe)} probe scores; max |p0 - definition| = {np.abs(q[:,0]-bp0).max():.3g}; max |p1 - definition| = {np.abs(q[:,1]-bp1).max():.3g}")
for lab, k in (("above max cal score", -3), ("far above max cal score", -2), ("below min cal score", -1)):
    print(f"  {lab}: p0={q[k,0]:.4f} p1={q[k,1]:.4f} | definition p0={bp0[k]:.4f} p1={bp1[k]:.4f}")

print("\nS4c inductive mode with an unfitted estimator on time-ordered rows (train then val)")
from sklearn.model_selection import train_test_split  # noqa: E402

trval = np.where(tr | cal)[0]
trval = trval[np.argsort(df.decision_time.to_numpy()[trval], kind="mergesort")]
Xa, ya, ta = X[trval], y[trval].astype(int), df.decision_time.to_numpy()[trval]
for shuffle in (True, False):
    vac = VennAbersCalibrator(estimator=C.base_pipeline(), inductive=True, cal_size=0.2, random_state=5, shuffle=shuffle)
    vac.fit(Xa, ya)
    _, _, t_prop, t_cal = train_test_split(Xa, ta, test_size=0.2, random_state=5, shuffle=shuffle)
    later = float(np.mean(t_cal < t_prop.max()))
    overlap = int(np.sum(t_cal < (t_prop.max())))
    pr = vac.predict_proba(Xh)[:, 1]
    print(f"  shuffle={shuffle}{' (library default)' if shuffle else ' (must be set explicitly)'}: calibration rows with a later proper-training row (future data trains the scorer): {overlap}/{len(t_cal)} ({later:.2%}); "
          f"holdout brier={C.brier(yh, pr):.5f}")
print("  with shuffle=False the calibration block is the newest 20% but no purge gap separates it from proper-training labels")

print("\n--- S3 missing covariates ---")
try:
    VennAbers().fit(np.column_stack([1 - np.r_[np.nan, s_cal[1:, 1]], np.r_[np.nan, s_cal[1:, 1]]]), yc)
    out, _ = VennAbers().fit(s_cal, yc).predict_proba(np.array([[np.nan, np.nan]]))
    print(f"NaN calibration score accepted silently; NaN test score -> {out}")
except Exception as e:
    print(f"NaN score: {type(e).__name__}: {e}")
vnan = VennAbersCalibrator(estimator=C.base_pipeline(), inductive=True, cal_size=0.2, random_state=5, shuffle=False).fit(Xa, ya)
print(f"estimator mode with NaN features and an imputing pipeline: ok, holdout outputs finite: {bool(np.all(np.isfinite(vnan.predict_proba(Xh))))}")

print("\n--- S5 persistence ---")
blob = pickle.dumps(va)
va2 = pickle.loads(blob)
print(f"pickle size {len(blob)} bytes; reload identical: {np.array_equal(va2.predict_proba(s_ho)[0], pp)}; no native format")

print("\n--- S6 cost ---")
t0 = time.perf_counter()
for _ in range(20):
    VennAbers().fit(s_cal, yc)
print(f"fit on {len(yc)} calibration scores: {(time.perf_counter()-t0)/20*1000:.2f} ms; peak RSS {C.peak_rss_mb():.1f} MB")
