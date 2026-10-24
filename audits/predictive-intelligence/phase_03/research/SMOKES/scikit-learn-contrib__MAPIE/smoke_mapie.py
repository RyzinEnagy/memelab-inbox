"""Phase 03 R2 smoke for scikit-learn-contrib/MAPIE at f1cc3d07 (installed from the pinned source).
Run: python -I smoke_mapie.py   (the runner adds unshare -n so no network is available)
"""
import os
import pickle
import sys
import time
import warnings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import common as C  # noqa: E402

warnings.simplefilter("ignore", FutureWarning)
import mapie  # noqa: E402
from mapie.calibration import VennAbersCalibrator  # noqa: E402
from mapie.classification import SplitConformalClassifier  # noqa: E402
from mapie.metrics.calibration import (  # noqa: E402
    expected_calibration_error,
    kolmogorov_smirnov_p_value,
    spiegelhalter_p_value,
)
from mapie.metrics.classification import classification_coverage_score  # noqa: E402

C.header(f"MAPIE {mapie.__version__} from {mapie.__file__}")
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
print(f"train prevalence (baseline B0) = {base_rate:.5f}")

# ---- base model (shared across calibration reviews) ----
t0 = time.perf_counter()
base = C.base_pipeline().fit(Xtr, ytr)
fit_s = time.perf_counter() - t0
p_cal = base.predict_proba(Xc)[:, 1]
p_ho = base.predict_proba(Xh)[:, 1]
print(f"base fit {fit_s*1000:.1f} ms; base cal pred_hash={C.pred_hash(p_cal)} holdout pred_hash={C.pred_hash(p_ho)}")

print("\n--- S1 leak trap ---")
viol, n = C.asof_violations(df, "leak_available_at")
print(f"rows where leak_available_at > decision_time: {viol}/{n} (an as-of filter would drop {C.TRAP})")
Xl = C.design(df, C.FEATURES + [C.TRAP])
leaky = C.base_pipeline().fit(Xl[tr], ytr)
pl_ho = leaky.predict_proba(Xl[ho])[:, 1]
C.score_block("S1 base (legit features)", yh, p_ho, base_rate)
C.score_block("S1 leaky (+leak_future_ret)", yh, pl_ho, base_rate)
scc_leak = SplitConformalClassifier(estimator=leaky, confidence_level=0.9, prefit=True)
scc_leak.conformalize(Xl[cal], yc)
_, sets_leak = scc_leak.predict_set(Xl[ho])
print(f"MAPIE SplitConformalClassifier accepted the trap column without any check; leaky 90% sets: "
      f"singletons={int((sets_leak[:, :, 0].sum(1) == 1).sum())}/{len(yh)}")
va_leak = VennAbersCalibrator(estimator=leaky[-1], cv="prefit").fit(leaky[:-1].transform(Xl[cal]), yc)
pv_leak = va_leak.predict_proba(leaky[:-1].transform(Xl[ho]))[:, 1]
C.score_block("S1 leaky + MAPIE Venn-Abers", yh, pv_leak, base_rate)
print("MAPIE has no feature-availability or time-split mechanism in these classes: nothing refused the trap column.")

print("\n--- S2 probability shape and imbalance (base model, holdout, censored excluded) ---")
C.score_block("S2 base", yh, p_ho, base_rate)
C.print_reliability("S2 base", yh, p_ho)

print("\n--- S3 missing covariates ---")
nan_rows = int(np.isnan(Xh).any(1).sum())
print(f"holdout rows with NaN features: {nan_rows}")
from sklearn.linear_model import LogisticRegression  # noqa: E402

try:
    bare = LogisticRegression(max_iter=2000).fit(np.nan_to_num(Xtr), ytr)
    SplitConformalClassifier(estimator=bare, prefit=True).conformalize(Xc, yc)
    print("bare LogisticRegression + NaN conformalize: accepted (unexpected)")
except Exception as e:
    print(f"bare LogisticRegression + NaN conformalize: {type(e).__name__}: {str(e)[:160]}")
scc_nan = SplitConformalClassifier(estimator=base, prefit=True).conformalize(Xc, yc)
_, s_nan = scc_nan.predict_set(Xh)
print(f"Pipeline(SimpleImputer median) inside the estimator: NaN rows pass through MAPIE, sets returned for {s_nan.shape[0]} rows")
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402

hgb = HistGradientBoostingClassifier(max_iter=100, random_state=0).fit(Xtr, ytr)
_, s_hgb = SplitConformalClassifier(estimator=hgb, prefit=True).conformalize(Xc, yc).predict_set(Xh)
print(f"HistGradientBoosting (native NaN) inside MAPIE: sets returned for {s_hgb.shape[0]} rows; MAPIE itself does not impute, it defers to the estimator")
from mapie._venn_abers import VennAbers as _VA  # noqa: E402

_v = _VA()
_v.fit(base.predict_proba(Xc), yc)
print(f"MAPIE Venn-Abers core given a NaN test score returns {np.round(_v.predict_proba(np.array([[np.nan, np.nan]]))[0], 4).tolist()} without an error")

print("\n--- S4 calibration and uncertainty ---")
print("S4a split conformal prediction sets (prefit base, conformalized on purged val, evaluated on holdout)")
cov_rows = {}
try:
    SplitConformalClassifier(estimator=base, conformity_score="aps", prefit=True).conformalize(Xc, yc)
    print("  aps on a binary target: accepted")
except ValueError as e:
    print(f"  aps on a binary target: refused by MAPIE: {e}")
for score in ("lac",):
    t0 = time.perf_counter()
    scc = SplitConformalClassifier(estimator=base, confidence_level=[0.9, 0.95], conformity_score=score, prefit=True)
    scc.conformalize(Xc, yc)
    conf_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    yp, sets = scc.predict_set(Xh)
    pred_s = time.perf_counter() - t0
    for j, cl in enumerate((0.9, 0.95)):
        s = sets[:, :, j]
        covered = s[np.arange(len(yh)), yh]
        size = s.sum(1)
        lib_cov = float(classification_coverage_score(yh, sets)[j])
        cov_pos = float(covered[yh == 1].mean())
        cov_neg = float(covered[yh == 0].mean())
        cov_rows[(score, cl)] = (float(covered.mean()), cov_pos, cov_neg)
        print(f"  {score} conf={cl}: coverage={covered.mean():.4f} (lib={lib_cov:.4f}) positives_cov={cov_pos:.4f} "
              f"(n_pos={int(yh.sum())}) negatives_cov={cov_neg:.4f} sizes: empty={int((size==0).sum())} "
              f"{{0}}={int(((size==1)&s[:,0]).sum())} {{1}}={int(((size==1)&s[:,1]).sum())} {{0,1}}={int((size==2).sum())}")
    print(f"  {score}: conformalize {conf_s*1000:.1f} ms, predict_set {pred_s/len(yh)*1e6:.1f} us/row")
cal_cov = scc.predict_set(Xc)[1][np.arange(len(yc)), yc, 0].mean()
print(f"  (lac 0.9 coverage on its own calibration rows = {cal_cov:.4f}; positives in cal = {int(yc.sum())})")

print("\nS4b Venn-Abers (MAPIE port), prefit on the same base scores")
before = base.predict_proba(Xh)[:, 1].copy()
va_pipe = VennAbersCalibrator(estimator=base, cv="prefit").fit(Xc, yc)
after = base.predict_proba(Xh)[:, 1]
print(f"  Pipeline passed as estimator with cv='prefit': base pipeline predictions changed after VennAbersCalibrator.fit: "
      f"{not np.array_equal(before, after)} (max abs change {np.max(np.abs(before - after)):.3g})")
print(f"  imputer medians now: {np.round(base.named_steps['impute'].statistics_, 4).tolist()}")
base = C.base_pipeline().fit(Xtr, ytr)  # refit clean base for the rest
print(f"  base refit; holdout pred_hash={C.pred_hash(base.predict_proba(Xh)[:, 1])} (must equal the first hash)")
pre, lr = base[:-1], base[-1]
t0 = time.perf_counter()
va = VennAbersCalibrator(estimator=lr, cv="prefit").fit(pre.transform(Xc), yc)
va_fit_s = time.perf_counter() - t0
t0 = time.perf_counter()
pv, p0p1 = va.predict_proba(pre.transform(Xh), p0_p1_output=True)
va_pred_s = time.perf_counter() - t0
pv1 = pv[:, 1]
width = p0p1[:, 1] - p0p1[:, 0]
print(f"  fit {va_fit_s*1000:.1f} ms, predict {va_pred_s/len(yh)*1e6:.1f} us/row; p0p1 shape {p0p1.shape}; "
      f"interval width p1-p0: median={np.median(width):.4f} p90={np.quantile(width, 0.9):.4f} max={width.max():.4f}; "
      f"p0<=p1 for all rows: {bool(np.all(p0p1[:, 0] <= p0p1[:, 1] + 1e-12))}")
C.score_block("S4b MAPIE Venn-Abers", yh, pv1, base_rate)
C.print_reliability("S4b MAPIE Venn-Abers", yh, pv1)
print("\nS4c MAPIE ECE and calibration tests versus this smoke's own computation")
for tag, p in (("base", p_ho), ("venn-abers", pv1)):
    e_u = expected_calibration_error(yh, p, num_bins=10, split_strategy="uniform")
    e_q = expected_calibration_error(yh, p, num_bins=5, split_strategy="quantile")
    own_u = C.reliability_uniform(yh, p, 10)[1]
    print(f"  {tag}: MAPIE ECE uniform(num_bins=10)={e_u:.5f} own ECE uniform10={own_u:.5f}; MAPIE ECE quantile(5)={e_q:.5f}; "
          f"spiegelhalter_p={spiegelhalter_p_value(yh, p):.4f} ks_p={kolmogorov_smirnov_p_value(yh, p):.4f}")
from mapie.metrics.calibration import _calc_bins  # noqa: E402

edges, _, _, sizes = _calc_bins(yh, p_ho, 10, "uniform")
print(f"  MAPIE uniform num_bins=10: edges={np.round(edges, 3).tolist()} sizes={sizes.astype(int).tolist()} "
      "(bin 0 holds only scores <= 0, so 9 usable intervals of width 1/9)")
print("  when every bin has the same sign of (observed - mean_p), any binned ECE equals |mean_p - prevalence|, "
      "which is why MAPIE and own ECE agree here although the bins differ")

print("\nS4d Venn-Abers correctness against the definition (isotonic fit with the test score appended)")
from mapie._venn_abers import VennAbers  # noqa: E402

s_cal = lr.predict_proba(pre.transform(Xc))
s_ho = lr.predict_proba(pre.transform(Xh))
probe = np.concatenate([s_ho[:, 1], [s_cal[:, 1].max() + 1e-3, min(s_cal[:, 1].max() + 0.2, 0.999), s_cal[:, 1].min() / 2]])
vam = VennAbers()
vam.fit(s_cal, yc)  # MAPIE private class: fit returns None
_, mp0p1 = vam.predict_proba(np.column_stack([1 - probe, probe]))
bp0, bp1 = C.venn_abers_bruteforce(s_cal[:, 1], yc, probe)
d0 = np.abs(mp0p1[:, 0] - bp0)
d1 = np.abs(mp0p1[:, 1] - bp1)
print(f"  {len(probe)} probe scores (holdout plus 2 above and 1 below every calibration score)")
print(f"  max |p0 MAPIE - p0 definition| = {d0.max():.3g}; max |p1 MAPIE - p1 definition| = {d1.max():.3g}")
for lab, k in (("above max cal score", -3), ("far above max cal score", -2), ("below min cal score", -1)):
    print(f"  {lab}: MAPIE p0={mp0p1[k,0]:.4f} p1={mp0p1[k,1]:.4f} | definition p0={bp0[k]:.4f} p1={bp1[k]:.4f}")
print(f"  rows where MAPIE p1 differs from the definition by >1e-9: {int((d1 > 1e-9).sum())}; p0: {int((d0 > 1e-9).sum())}")

print("\n--- S5 persistence ---")
blob = pickle.dumps((scc, va))
scc2, va2 = pickle.loads(blob)
same_sets = np.array_equal(scc2.predict_set(Xh)[1], scc.predict_set(Xh)[1])
same_va = np.array_equal(va2.predict_proba(pre.transform(Xh)), va.predict_proba(pre.transform(Xh)))
print(f"pickle size {len(blob)} bytes; reload identical sets: {same_sets}; identical Venn-Abers probabilities: {same_va}")
print("MAPIE has no native save format; pickle/joblib only (executes code on load, trusted files only)")

print("\n--- role-specific: MAPIE exchangeability test on time-ordered conformity scores ---")
from mapie.exchangeability_testing.permutations import PValuePermutationTest  # noqa: E402

order_c = np.argsort(df.decision_time.to_numpy()[cal], kind="mergesort")
order_h = np.argsort(df.decision_time.to_numpy()[ho], kind="mergesort")
for tag, Xs, ys in (("val only (no shift expected)", Xc[order_c], yc[order_c]),
                    ("val then holdout (covariate shift at the boundary)", np.vstack([Xc[order_c], Xh[order_h]]), np.concatenate([yc[order_c], yh[order_h]]))):
    t0 = time.perf_counter()
    est = SplitConformalClassifier(estimator=base, confidence_level=0.9, prefit=True)
    test = PValuePermutationTest(mapie_estimator=est, random_state=0, num_permutations=200, warn=False).run(Xs, ys)
    print(f"  {tag}: n={len(ys)} p_value={test.p_values[-1]:.4f} is_exchangeable={test.is_exchangeable} ({time.perf_counter()-t0:.1f} s)")
nc_c = 1 - s_cal[np.arange(len(yc)), yc]
nc_h = 1 - s_ho[np.arange(len(yh)), yh]
print(f"  mean LAC score val={nc_c.mean():.4f} holdout={nc_h.mean():.4f}; holdout mean liq log1p {np.nanmean(Xh[:,0]):.3f} vs val {np.nanmean(Xc[:,0]):.3f}")

print("\n--- role-specific: MAPIE risk control (alert threshold with a precision guarantee, Learn-then-Test) ---")
from mapie.risk_control import BinaryClassificationController  # noqa: E402

for tgt in (0.10, 0.20):
    bcc = BinaryClassificationController(predict_function=base.predict_proba, risk="precision", target_level=tgt,
                                         confidence_level=0.9)
    bcc.calibrate(Xc, yc)
    nvalid = 0 if bcc.valid_predict_params is None else len(np.atleast_1d(bcc.valid_predict_params))
    if bcc.best_predict_param is None or nvalid == 0:
        print(f"  precision >= {tgt} at 90% confidence: no valid threshold on {int(yc.sum())} calibration positives (controller abstains)")
    else:
        thr = float(np.atleast_1d(bcc.best_predict_param)[0])
        alert = p_ho >= thr
        prec = float(yh[alert].mean()) if alert.any() else float("nan")
        print(f"  precision >= {tgt} at 90% confidence: {nvalid} valid thresholds, best {thr:.2f}; holdout alerts {int(alert.sum())}, precision {prec:.3f}")

print("\n--- S6 cost ---")
print(f"base fit {fit_s*1000:.1f} ms; peak RSS {C.peak_rss_mb():.1f} MB; ran with no network namespace (see runner header)")
