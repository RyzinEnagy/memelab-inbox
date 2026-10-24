"""Phase 03 R2 smoke for henrikbostrom/crepes at 88a0dfac (installed from the pinned source, version 0.9.1).
Run: python -I smoke_crepes.py   (the runner adds unshare -n so no network is available)
"""
import os
import pickle
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import common as C  # noqa: E402
import crepes  # noqa: E402
from crepes import WrapClassifier  # noqa: E402
from crepes.extras import hinge  # noqa: E402
from crepes.martingales import CompositeMartingale, SimpleJumper, SleeperStayer, semi_online_p_values  # noqa: E402

C.header(f"crepes {crepes.__version__} from {crepes.__file__}")
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

t0 = time.perf_counter()
base = C.base_pipeline().fit(Xtr, ytr)
fit_s = time.perf_counter() - t0
p_ho = base.predict_proba(Xh)[:, 1]
print(f"base fit {fit_s*1000:.1f} ms; base cal pred_hash={C.pred_hash(base.predict_proba(Xc)[:, 1])} holdout pred_hash={C.pred_hash(p_ho)}")


def set_report(tag, sets, yt):
    sets = np.asarray(sets, dtype=bool)
    covered = sets[np.arange(len(yt)), yt]
    size = sets.sum(1)
    print(f"  {tag}: coverage={covered.mean():.4f} positives_cov={covered[yt==1].mean():.4f} (n_pos={int(yt.sum())}) "
          f"negatives_cov={covered[yt==0].mean():.4f} sizes: empty={int((size==0).sum())} {{0}}={int(((size==1)&sets[:,0]).sum())} "
          f"{{1}}={int(((size==1)&sets[:,1]).sum())} {{0,1}}={int((size==2).sum())}")
    return covered


print("\n--- S1 leak trap ---")
viol, n = C.asof_violations(df, "leak_available_at")
print(f"rows where leak_available_at > decision_time: {viol}/{n}")
Xl = C.design(df, C.FEATURES + [C.TRAP])
leaky = C.base_pipeline().fit(Xl[tr], ytr)
wl = WrapClassifier(leaky)
wl.calibrate(Xl[cal], yc, seed=1)
C.score_block("S1 base (legit features)", yh, p_ho, base_rate)
C.score_block("S1 leaky (+leak_future_ret) via crepes predict_proba", yh, wl.predict_proba(Xl[ho])[:, 1], base_rate)
set_report("S1 leaky crepes 90% sets", wl.predict_set(Xl[ho], confidence=0.9, labels=False), yh)
print("crepes has no feature-availability or time-split mechanism: the trap column was accepted.")

print("\n--- S2 probability shape (crepes passes the learner's predict_proba through unchanged) ---")
w = WrapClassifier(base)
pp = w.predict_proba(Xh)
print(f"predict_proba shape {pp.shape}; identical to base: {np.array_equal(pp[:, 1], p_ho)}")
C.score_block("S2 base via crepes", yh, pp[:, 1], base_rate)
print("crepes offers no probability recalibration for classifiers (no Platt, isotonic or Venn-Abers in src/crepes); "
      "it outputs conformal p-values and prediction sets")

print("\n--- S3 missing covariates ---")
try:
    from sklearn.linear_model import LogisticRegression
    bare = LogisticRegression(max_iter=2000).fit(np.nan_to_num(Xtr), ytr)
    WrapClassifier(bare).calibrate(Xc, yc)
    print("bare LogisticRegression + NaN: accepted (unexpected)")
except Exception as e:
    print(f"bare LogisticRegression + NaN: {type(e).__name__}: {str(e)[:120]}")
w.calibrate(Xc, yc, seed=1)
print(f"Pipeline(SimpleImputer median): crepes passes NaN rows to the learner; sets for {len(w.predict_set(Xh, labels=False))} rows")

print("\n--- S4 conformal sets and p-values ---")
t0 = time.perf_counter()
w = WrapClassifier(base)
w.calibrate(Xc, yc, seed=1)
cal_s = time.perf_counter() - t0
for cl in (0.9, 0.95):
    t0 = time.perf_counter()
    sets = w.predict_set(Xh, confidence=cl, labels=False)
    ps = time.perf_counter() - t0
    set_report(f"standard (hinge) conf={cl}", sets, yh)
print(f"  calibrate {cal_s*1000:.1f} ms, predict_set {ps/len(yh)*1e6:.1f} us/row")
ev = w.evaluate(Xh, yh, confidence=0.9)
print(f"  crepes evaluate(conf=0.9): {ev}")

wc = WrapClassifier(base)
wc.calibrate(Xc, yc, class_cond=True, seed=1)
for cl in (0.9, 0.95):
    set_report(f"class-conditional (Mondrian by label) conf={cl}", wc.predict_set(Xh, confidence=cl, labels=False), yh)
pv = wc.predict_p(Xh, smoothing=False)
print(f"  class-conditional non-smoothed p-values for label 1: min={pv[:,1].min():.4f} (floor 1/(n_pos_cal+1) = {1/(yc.sum()+1):.4f})")
print(f"  ks_test (uniformity of p-values) from evaluate: {wc.evaluate(Xh, yh, confidence=0.9)}")

fatal_col = C.FEATURES.index("fatal_flag")
wm = WrapClassifier(base)
wm.calibrate(Xc, yc, mc=lambda Z: Z[:, fatal_col].astype(int), seed=1)
cats, counts = np.unique(Xc[:, fatal_col].astype(int), return_counts=True)
print(f"  Mondrian by fatal_flag: calibration rows per category {dict(zip(cats.tolist(), counts.tolist()))}")
cov = set_report("Mondrian by fatal_flag conf=0.9", wm.predict_set(Xh, confidence=0.9, labels=False), yh)
for c in cats:
    m = Xh[:, fatal_col].astype(int) == c
    print(f"    category {c}: holdout n={int(m.sum())} coverage={cov[m].mean():.4f}")

print("\n  determinism: two predict_p calls with the same seed equal:",
      np.array_equal(w.predict_p(Xh, seed=7), w.predict_p(Xh, seed=7)),
      "| without seed equal:", np.array_equal(w.predict_p(Xh, seed=None), w.predict_p(Xh, seed=None)))

print("\n--- role-specific: conformal test martingales over time-ordered scores (exchangeability / drift) ---")
order = np.argsort(df.decision_time.to_numpy(), kind="mergesort")
lab = df.label.notna().to_numpy()
p_all = base.predict_proba(X)[:, 1]
seg = {
    "train then val (no shift, false-alarm check)": (df.split.isin(["train", "val"]).to_numpy()),
    "val only (no shift, false-alarm check)": (df.split == "val").to_numpy(),
    "val then holdout (shift in liq_usd and ret_1h)": df.split.isin(["val", "holdout"]).to_numpy(),
}
for name, mask in seg.items():
    idx = order[mask[order]]
    for score_name, alphas in (("p(positive), label-free", p_all[idx]),
                               ("log1p(liq_usd) raw feature", np.nan_to_num(X[idx, 0], nan=np.nanmedian(X[:, 0])))):
        t0 = time.perf_counter()
        pvals = semi_online_p_values(alphas, seed=11, optimized=True)
        res = {}
        for mname, m in (("SimpleJumper", SimpleJumper()), ("SleeperStayer", SleeperStayer()),
                         ("Composite", CompositeMartingale([SimpleJumper(), SleeperStayer()]))):
            i = m.apply(pvals, c=100)
            res[mname] = int(i)
        first_hold = int(np.argmax(df.split.to_numpy()[idx] == "holdout")) if "holdout" in name else None
        print(f"  {name} | {score_name}: n={len(idx)} alarm index (c=100, n means no alarm) {res}"
              f"{'' if first_hold is None else f'; first holdout row at index {first_hold}'} ({time.perf_counter()-t0:.2f} s)")

print("\n--- S5 persistence ---")
blob = pickle.dumps(w)
w2 = pickle.loads(blob)
print(f"pickle size {len(blob)} bytes; identical p-values after reload (seed 3): "
      f"{np.array_equal(w2.predict_p(Xh, seed=3), w.predict_p(Xh, seed=3))}; no native save format")

print("\n--- S6 cost ---")
print(f"peak RSS {C.peak_rss_mb():.1f} MB; ran with no network namespace (see runner header)")
