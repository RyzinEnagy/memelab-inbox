"""Phase 03 repair pass (lead): reproduce the blind rescorer's MAPIE finding (MA-4) with the lead's own code.

Claim: VennAbersCalibrator(estimator=<fitted Pipeline>, cv="prefit").fit(X_cal, y_cal) refits the caller's fitted
transformers on the calibration rows (mapie/calibration.py: transformers.fit_transform before the prefit branch), so the
caller's frozen base model changes. Also re-checks the Venn-Abers p1 value above the calibration range (MA-1).
Usage: <MAPIE venv python> -I rerun_mapie_prefit.py challenge.csv
"""
import json, sys
import numpy as np, pandas as pd
import mapie
from mapie.calibration import VennAbersCalibrator
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

df = pd.read_csv(sys.argv[1])
df = df[df.label.notna()]
cols = ["liq_usd", "vol_24h", "age_h", "score100", "ret_1h"]
tr = df[df.split == "train"]; va = df[df.split == "val"]; ho = df[df.split == "holdout"]
X = lambda d: np.log1p(np.abs(d[cols].to_numpy(float))) * np.sign(d[cols].to_numpy(float))
base = Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler()),
                 ("lr", LogisticRegression(max_iter=2000))]).fit(X(tr), tr.label.astype(int))
before = base.predict_proba(X(ho))[:, 1]
scaler_mean_before = base.named_steps["sc"].mean_.copy()
vac = VennAbersCalibrator(estimator=base, cv="prefit").fit(X(va), va.label.astype(int))
after = base.predict_proba(X(ho))[:, 1]
res = {"mapie": mapie.__version__, "rows_train": int(len(tr)), "rows_cal": int(len(va)), "rows_holdout": int(len(ho)),
       "caller_base_max_abs_change": float(np.max(np.abs(after - before))),
       "caller_scaler_mean_changed": bool(not np.allclose(scaler_mean_before, base.named_steps["sc"].mean_)),
       "same_scaler_object": vac.transformers_.named_steps["sc"] is base.named_steps["sc"]}
# MA-1 recheck: a score above every calibration score must get p1 = 1 under IVAP
from mapie._venn_abers import VennAbers
cal_p = np.clip(base.predict_proba(X(va)), 1e-6, 1 - 1e-6)
va_obj = VennAbers()
va_obj.fit(cal_p, va.label.astype(int).to_numpy())
probe = np.array([[1 - 0.999, 0.999]])
p_prime, p0p1 = va_obj.predict_proba(probe)
res["venn_abers_probe_above_cal_max"] = {"cal_max_score": float(cal_p[:, 1].max()), "p0": float(p0p1[0, 0]),
                                         "p1": float(p0p1[0, 1]), "ivap_definition_p1": 1.0}
print("RESULTS_JSON " + json.dumps(res, sort_keys=True))
