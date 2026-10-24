"""Does skore score rows whose label is NaN (censored, P05)?"""
import os, sys, warnings
sys.path.insert(0, os.environ["R4_HARNESS"])
import common as C
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
warnings.filterwarnings("ignore")
from skore import EstimatorReport
df = C.load(); trm = C.matured(df[df.split == "train"]); ho = df[df.split == "holdout"]
m = make_pipeline(SimpleImputer(), LogisticRegression(max_iter=1000)).fit(C.log_feats(trm, C.FEATURES), trm.label.astype(int))
out = {"holdout_rows": len(ho), "nan_labels": int(ho.label.isna().sum())}
try:
    r = EstimatorReport(m, X_test=C.log_feats(ho, C.FEATURES), y_test=ho.label, pos_label=1)
    s = r.metrics.summarize().frame()
    out["metrics_with_nan_labels"] = {str(k): str(v) for k, v in s.items()}
except Exception as e:
    out["error"] = f"{type(e).__name__}: {str(e)[:300]}"
try:
    r2 = EstimatorReport(m, X_test=C.log_feats(ho, C.FEATURES), y_test=ho.label.fillna(0).astype(int), pos_label=1)
    out["metrics_if_censored_scored_as_negative"] = {str(k): str(v) for k, v in r2.metrics.summarize().frame().items()}
except Exception as e:
    out["error2"] = f"{type(e).__name__}: {str(e)[:300]}"
C.emit("S2_censored", out)
