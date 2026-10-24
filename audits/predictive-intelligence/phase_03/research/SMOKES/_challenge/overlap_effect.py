"""Phase 03 lead: quantify the challenge's short 'embargo' split and test whether it can move any smoke metric.

Usage: <python with numpy, pandas, scikit-learn> -I overlap_effect.py challenge.csv
Prints counts and holdout Brier/log loss for fits on purged versus unpurged rows. Offline, deterministic.
"""
import json, sys
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator

d = pd.read_csv(sys.argv[1])
first = {s: int(d.loc[d.split == s, "decision_time"].min()) for s in ("train", "val", "embargo", "holdout")}
last = {s: int(d.loc[d.split == s, "decision_time"].max()) for s in ("train", "val", "embargo", "holdout")}
out = {
    "embargo_gap_h_val_end_to_holdout_start": round((first["holdout"] - last["val"]) / 3600, 2),
    "label_horizon_h": float(((d.label_matures_at - d.decision_time) / 3600).max()),
    "val_rows_label_matures_after_first_holdout_decision": int(((d.split == "val") & (d.label_matures_at > first["holdout"])).sum()),
    "train_rows_label_matures_after_first_val_decision": int(((d.split == "train") & (d.label_matures_at > first["val"])).sum()),
    "train_rows_label_matures_after_first_holdout_decision": int(((d.split == "train") & (d.label_matures_at > first["holdout"])).sum()),
    "censored_rows_by_split": {k: int(v) for k, v in d[d.censored == 1].split.value_counts().items()},
}
feats = ["liq_usd", "vol_24h", "age_h", "score100", "fatal_flag", "ret_1h"]
X = d[feats].copy()
X["liq_usd"] = np.log1p(X["liq_usd"]); X["vol_24h"] = np.log1p(X["vol_24h"])
y = d["label"]
tr = d.split == "train"; va = d.split == "val"; ho = (d.split == "holdout") & d.label.notna()
tr_p = tr & (d.label_matures_at <= first["val"])
va_p = va & (d.label_matures_at <= first["holdout"])
def model():
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=1000))
def score(p):
    yy = y[ho].to_numpy(); p = np.clip(p, 1e-15, 1 - 1e-15)
    return {"brier": round(float(np.mean((p - yy) ** 2)), 6), "logloss": round(float(-np.mean(yy * np.log(p) + (1 - yy) * np.log(1 - p))), 6)}
res = {}
for name, m_tr in (("train_all", tr), ("train_purged", tr_p)):
    m = model().fit(X[m_tr], y[m_tr].astype(int))
    res[name] = score(m.predict_proba(X[ho])[:, 1])
    for cname, m_va in (("cal_val_all", va), ("cal_val_purged", va_p)):
        c = CalibratedClassifierCV(FrozenEstimator(m), method="sigmoid").fit(X[m_va], y[m_va].astype(int))
        res[name + "+" + cname] = score(c.predict_proba(X[ho])[:, 1])
out["holdout_scores"] = res
out["rows"] = {"train_all": int(tr.sum()), "train_purged": int(tr_p.sum()), "val_all": int(va.sum()), "val_purged": int(va_p.sum()), "holdout_scored": int(ho.sum())}
out["max_abs_brier_difference_purged_vs_not"] = round(max(abs(res["train_all"]["brier"] - res["train_purged"]["brier"]),
    abs(res["train_all+cal_val_all"]["brier"] - res["train_all+cal_val_purged"]["brier"])), 6)
print("RESULTS_JSON " + json.dumps(out, sort_keys=True))
