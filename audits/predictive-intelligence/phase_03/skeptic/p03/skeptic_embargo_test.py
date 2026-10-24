"""Skeptic P03: test the lead's claim that the challenge's 14.6 h embargo band (24 h labels) cannot move any smoke
metric beyond 0.0001 Brier. (1) Reproduce the lead's logistic numbers. (2) Placebo: drop the same NUMBER of random
non-overlapping rows instead of the overlapping ones, 200 times; if the purge difference sits inside the placebo
spread, the change is sample-size noise, not leakage. (3) Repeat with a flexible model (HistGradientBoosting, native
NaN), as used by several smokes, to see whether 0.0001 is a general bound.
Usage: <python with numpy, pandas, scikit-learn> -I skeptic_embargo_test.py challenge.csv"""
import json, sys
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator

d = pd.read_csv(sys.argv[1])
first = {s: int(d.loc[d.split == s, "decision_time"].min()) for s in ("train", "val", "holdout")}
feats = ["liq_usd", "vol_24h", "age_h", "score100", "fatal_flag", "ret_1h"]
X = d[feats].copy(); X["liq_usd"] = np.log1p(X["liq_usd"]); X["vol_24h"] = np.log1p(X["vol_24h"])
y = d["label"]
tr = (d.split == "train").to_numpy(); va = (d.split == "val").to_numpy(); ho = ((d.split == "holdout") & d.label.notna()).to_numpy()
ovl_tr = tr & (d.label_matures_at > first["val"]).to_numpy()
ovl_va = va & (d.label_matures_at > first["holdout"]).to_numpy()
yh = y[ho].to_numpy()
def brier(p): return float(np.mean((p - yh) ** 2))
def lr(): return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=1000))
def hgb(): return HistGradientBoostingClassifier(max_iter=100, learning_rate=0.1, random_state=0)
out = {"overlap_train": int(ovl_tr.sum()), "overlap_val": int(ovl_va.sum())}
rng = np.random.default_rng(7)
for name, mk in (("logistic", lr), ("hgb", hgb)):
    full = mk().fit(X[tr], y[tr].astype(int)); b_full = brier(full.predict_proba(X[ho])[:, 1])
    m_p = tr & ~ovl_tr
    purged = mk().fit(X[m_p], y[m_p].astype(int)); b_p = brier(purged.predict_proba(X[ho])[:, 1])
    # calibration on val: all versus purged (model fitted on all train)
    c_all = CalibratedClassifierCV(FrozenEstimator(full), method="sigmoid").fit(X[va], y[va].astype(int))
    c_pur = CalibratedClassifierCV(FrozenEstimator(full), method="sigmoid").fit(X[va & ~ovl_va], y[va & ~ovl_va].astype(int))
    b_ca, b_cp = brier(c_all.predict_proba(X[ho])[:, 1]), brier(c_pur.predict_proba(X[ho])[:, 1])
    # placebo: drop the same number of random NON-overlapping train rows
    idx_ok = np.where(tr & ~ovl_tr)[0]; diffs = []
    for _ in range(60 if name == "hgb" else 200):
        drop = rng.choice(idx_ok, size=int(ovl_tr.sum()), replace=False)
        m = tr.copy(); m[drop] = False
        diffs.append(brier(mk().fit(X[m], y[m].astype(int)).predict_proba(X[ho])[:, 1]) - b_full)
    diffs = np.abs(np.array(diffs))
    out[name] = {"brier_train_all": round(b_full, 6), "brier_train_purged": round(b_p, 6),
                 "abs_diff_purge": round(abs(b_full - b_p), 6),
                 "abs_diff_cal_val_all_vs_purged": round(abs(b_ca - b_cp), 6),
                 "placebo_abs_diff_median": round(float(np.median(diffs)), 6),
                 "placebo_abs_diff_p95": round(float(np.quantile(diffs, 0.95)), 6),
                 "placebo_abs_diff_max": round(float(diffs.max()), 6),
                 "purge_diff_percentile_in_placebo": round(float((diffs < abs(b_full - b_p)).mean()), 3),
                 "placebo_runs": int(len(diffs))}
print("RESULTS_JSON " + json.dumps(out, sort_keys=True))
