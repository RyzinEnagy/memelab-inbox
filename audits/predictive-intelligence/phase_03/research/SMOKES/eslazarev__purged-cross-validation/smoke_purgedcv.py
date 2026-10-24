"""Phase 03 R2 smoke for eslazarev/purged-cross-validation (purgedcv) at 07692dd8 (installed from the pinned source, 0.1.11).
Checks purge and embargo against the challenge's decision_time and label_matures_at with an independent brute-force checker.
Run: python -I smoke_purgedcv.py   (the runner adds unshare -n so no network is available)
"""
import os
import pickle
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import common as C  # noqa: E402
import leakcheck as L  # noqa: E402
import purgedcv  # noqa: E402
from purgedcv import (  # noqa: E402
    CombinatorialPurgedCV,
    PurgedGroupKFold,
    PurgedKFold,
    WalkForwardSplit,
    apply_embargo,
    audit_splitter,
    probability_of_backtest_overfitting,
    purge,
)

C.header(f"purgedcv {purgedcv.__version__} from {purgedcv.__file__}")
H = 3600
print("\n--- hand case: six 24 h labels, one test row ---")
dec_h = np.array([0, 6, 12, 30, 36, 60]) * H
mat_h = dec_h + 24 * H
pred = pd.Series(pd.to_datetime(dec_h, unit="s"))
evl = pd.Series(pd.to_datetime(mat_h, unit="s"))
train = np.array([0, 1, 2, 4, 5])
test = np.array([3])
kept = purge(train, test, pred, evl)
print(f"windows (h): {[(int(a/H), int(b/H)) for a, b in zip(dec_h, mat_h)]}; test row 3 = [30, 54)")
print(f"purge kept {kept.tolist()} (expected [0, 1, 5]: row 1 matures exactly at the test decision, rows 2 and 4 overlap)")
emb = apply_embargo(kept, test, pred, evl, pd.Timedelta(hours=24))
print(f"embargo 24 h kept {emb.tolist()} (expected [0, 1]: row 5 decided at 60 h, inside [54 h, 78 h])")
mat_b = mat_h.copy()
mat_b[1] += 1
kept_b = purge(train, test, pred, pd.Series(pd.to_datetime(mat_b, unit="s")))
print(f"row 1 maturing one second after the test decision: purge kept {kept_b.tolist()} (expected [0, 5])")
brute = L.overlap_leaks(train, test, dec_h, mat_h)
print(f"independent checker on the unpurged candidates flags {brute.tolist()} (expected [2, 4])")
hand_ok = kept.tolist() == [0, 1, 5] and emb.tolist() == [0, 1] and kept_b.tolist() == [0, 5]
print(f"HAND CASE PASS: {hand_ok}")

df, sha = C.load()
print("\nchallenge sha256", sha)
lab = df.label.notna().to_numpy()
d = df[lab].sort_values("decision_time", kind="mergesort").reset_index(drop=True)
dec = d.decision_time.to_numpy().astype(np.int64)
mat = d.label_matures_at.to_numpy().astype(np.int64)
P = pd.Series(pd.to_datetime(dec, unit="s"))
E = pd.Series(pd.to_datetime(mat, unit="s"))
print(f"labeled rows {len(d)}; irregular gaps between decisions: min {np.diff(dec).min()} s, median {int(np.median(np.diff(dec)))} s, max {np.diff(dec).max()} s; "
      f"duplicate decision times {int((np.diff(dec) == 0).sum())}")

print("\n--- the challenge's own split: is the 'embargo' split enough for 24 h labels? ---")
iv = np.where(d.split == "val")[0]
ih = np.where(d.split == "holdout")[0]
itr = np.where(d.split == "train")[0]
kept_v = purge(iv, ih, P, E)
print(f"embargo split spans {(df.loc[df.split=='embargo','decision_time'].max()-df.loc[df.split=='embargo','decision_time'].min())/H:.1f} h; label horizon 24 h")
print(f"val rows whose label window overlaps holdout windows (purgedcv): {len(iv) - len(kept_v)}; independent checker: {len(L.overlap_leaks(iv, ih, dec, mat))}; "
      f"rows with label_matures_at > first holdout decision: {int((mat[iv] > dec[ih].min()).sum())}")
kept_t = purge(itr, iv, P, E)
print(f"train rows overlapping val windows: purgedcv {len(itr) - len(kept_t)}; independent checker {len(L.overlap_leaks(itr, iv, dec, mat))}")

print("\n--- splitters on the challenge (independent overlap and embargo check per fold) ---")
X = C.design(d, C.FEATURES)


def check(name, cv, embargo_s=0):
    t0 = time.perf_counter()
    folds = list(cv.split(X))
    dt = time.perf_counter() - t0
    leaks = [len(L.overlap_leaks(a, b, dec, mat)) for a, b in folds]
    embv = [len(L.embargo_violations(a, b, dec, mat, embargo_s)) for a, b in folds]
    sizes = [(len(a), len(b)) for a, b in folds]
    print(f"  {name}: {len(folds)} folds in {dt*1000:.1f} ms; (train, test) sizes {sizes[:6]}{' ...' if len(sizes) > 6 else ''}; "
          f"overlap leaks per fold {leaks[:15]}; embargo violations per fold {embv[:15]}")
    return folds, leaks, embv


wf = WalkForwardSplit(n_splits=5, test_size=280, prediction_times=P, evaluation_times=E)
f_wf, lk_wf, _ = check("WalkForwardSplit(expanding, 5 x 280 rows)", wf)
pk = PurgedKFold(n_splits=5, prediction_times=P, evaluation_times=E, embargo=pd.Timedelta(hours=24))
f_pk, lk_pk, em_pk = check("PurgedKFold(5, embargo 24 h)", pk, embargo_s=24 * H)
cp = CombinatorialPurgedCV(n_splits=6, n_test_groups=2, prediction_times=P, evaluation_times=E, embargo=pd.Timedelta(hours=24))
f_cp, lk_cp, em_cp = check("CombinatorialPurgedCV(6, 2 test groups, embargo 24 h)", cp, embargo_s=24 * H)
print("  audit_splitter(PurgedKFold) per fold:")
aud = audit_splitter(pk, X)
cols = [c for c in aud.columns if c in ("fold", "candidate_train_size", "rows_removed_by_purge", "rows_removed_by_embargo",
                                        "final_train_size", "test_size", "final_overlap_fraction", "temporal_leakage_free")]
print(aud[cols].to_string(index=False))

print("\n  without purge information (plain sklearn KFold on the same rows), for contrast:")
from sklearn.model_selection import KFold, TimeSeriesSplit  # noqa: E402

lk_kf = [len(L.overlap_leaks(a, b, dec, mat)) for a, b in KFold(5).split(X)]
lk_ts = [len(L.overlap_leaks(a, b, dec, mat)) for a, b in TimeSeriesSplit(5, test_size=280).split(X)]
print(f"  sklearn KFold(5) overlap leaks per fold {lk_kf}; TimeSeriesSplit(5, test_size=280) {lk_ts}")

print("\n--- groups: exact mint versus symbol (P01, P14) ---")
gk = PurgedGroupKFold(n_splits=5, prediction_times=P, evaluation_times=E, groups=d.mint.to_numpy())
f_g = list(gk.split(X))
shared = [len(set(d.mint.to_numpy()[a]) & set(d.mint.to_numpy()[b])) for a, b in f_g]
leak_g = [len(L.overlap_leaks(a, b, dec, mat)) for a, b in f_g]
print(f"  PurgedGroupKFold by mint: mints shared train/test per fold {shared}; overlap leaks {leak_g}")
try:
    wf_g = WalkForwardSplit(n_splits=5, test_size=280, prediction_times=P, evaluation_times=E, groups=d.mint.to_numpy())
    list(wf_g.split(X))
    print("  WalkForwardSplit with mint groups: no error")
except Exception as e:
    print(f"  WalkForwardSplit with mint groups bound: {type(e).__name__}: {str(e)[:140]}")
print(f"  symbols {d.symbol.nunique()} vs mints {d.mint.nunique()}: grouping by symbol would merge different mints; the library cannot know which key is identity")

print("\n--- S1 leak trap through the splitter ---")
from sklearn.metrics import roc_auc_score  # noqa: E402

y = d.label.to_numpy().astype(int)
Xl = C.design(d, C.FEATURES + [C.TRAP])
for tag, XX in (("legit", X), ("legit + leak_future_ret", Xl)):
    briers, aucs = [], []
    for a, b in f_wf:
        m = C.base_pipeline().fit(XX[a], y[a])
        p = m.predict_proba(XX[b])[:, 1]
        briers.append(C.brier(y[b], p))
        aucs.append(roc_auc_score(y[b], p) if 0 < y[b].sum() < len(b) else np.nan)
    print(f"  walk-forward {tag}: mean Brier {np.mean(briers):.5f}, mean AUC {np.nanmean(aucs):.4f}")
print("  purgedcv purges by label windows only; it has no feature-availability notion, so the trap column passes")

print("\n--- input validation ---")
perm = np.random.default_rng(1).permutation(len(P))
for tag, pp, ee in (("rows not in time order (prediction and evaluation shuffled together)", P.iloc[perm].reset_index(drop=True), E.iloc[perm].reset_index(drop=True)),
                    ("NaT in evaluation times", P, E.where(E.index != 5)),
                    ("evaluation before prediction", P, E - pd.Timedelta(days=2))):
    try:
        PurgedKFold(n_splits=3, prediction_times=pp, evaluation_times=ee)
        print(f"  {tag}: accepted")
    except Exception as e:
        print(f"  {tag}: {type(e).__name__}: {str(e)[:110]}")

print("\n--- P22: probability of backtest overfitting (CSCV) ---")
rng = np.random.default_rng(20261024)
noise = rng.normal(0, 0.01, size=(20, 1600))
r1 = probability_of_backtest_overfitting(noise, n_splits=16)
sig = noise.copy()
sig[0] += 0.003
r2 = probability_of_backtest_overfitting(sig, n_splits=16)
print(f"  20 pure-noise configurations: PBO={r1.pbo:.3f} slope={r1.slope:.3f} combos={r1.n_combos}")
print(f"  same with one configuration given a real drift: PBO={r2.pbo:.3f} slope={r2.slope:.3f}")

print("\n--- S5 persistence ---")
blob = pickle.dumps(pk)
pk2 = pickle.loads(blob)
same = all(np.array_equal(a1, a2) and np.array_equal(b1, b2) for (a1, b1), (a2, b2) in zip(pk.split(X), pk2.split(X)))
print(f"  pickled splitter ({len(blob)} bytes) yields identical folds after reload: {same}; folds are deterministic (no randomness)")

print("\n--- summary ---")
ok = hand_ok and sum(lk_wf) == 0 and sum(lk_pk) == 0 and sum(em_pk) == 0 and sum(lk_cp) == 0 and sum(em_cp) == 0 and sum(leak_g) == 0
print(f"ALL PURGE/EMBARGO CHECKS PASS: {ok}; peak RSS {C.peak_rss_mb():.1f} MB")
