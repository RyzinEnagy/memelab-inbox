# Second reviewer rerun: MAPIE at pin f1cc3d07. Checks of review claims, own construction.
import sys, warnings, numpy as np, pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from mapie._venn_abers import VennAbers
from mapie.calibration import VennAbersCalibrator
from mapie.classification import SplitConformalClassifier
from mapie.risk_control import BinaryClassificationController
from mapie.metrics.calibration import spiegelhalter_p_value
rng = np.random.default_rng(7)
# (1) Venn-Abers p1 for a test score above every calibration score
s_cal = rng.uniform(0, 0.5, 200); y_cal = (rng.uniform(size=200) < s_cal).astype(int)
va = VennAbers(); va.fit(np.c_[1 - s_cal, s_cal], y_cal)
probe = np.array([0.25, 0.9])
p_prime, p0p1 = va.predict_proba(np.c_[1 - probe, probe])
def defn(score, lab):
    x = np.r_[s_cal, score]; y = np.r_[y_cal, lab]
    return IsotonicRegression(out_of_bounds="clip").fit(x, y).predict([score])[0]
for i, sc in enumerate(probe):
    print(f"VA probe {sc}: mapie p0 {p0p1[i,0]:.4f} p1 {p0p1[i,1]:.4f} | definition p0 {defn(sc,0):.4f} p1 {defn(sc,1):.4f}")
# NaN score
try:
    out = va.predict_proba(np.array([[np.nan, np.nan]]))[0]
    print("VA NaN score ->", np.round(out, 4).tolist())
except Exception as e:
    print("VA NaN score raises", type(e).__name__)
# challenge data
df = pd.read_csv(sys.argv[1]).sort_values("decision_time", kind="stable").reset_index(drop=True)
feats = ["liq_usd", "vol_24h", "age_h", "score100", "fatal_flag", "ret_1h"]
X = df[feats].copy(); X["liq_usd"] = np.log1p(X["liq_usd"]); X["vol_24h"] = np.log1p(X["vol_24h"])
lab = df.label.notna()
tr = (df.split == "train") & lab & (df.label_matures_at <= df.loc[df.split == "val", "decision_time"].min())
va_ = (df.split == "val") & lab & (df.label_matures_at <= df.loc[df.split == "holdout", "decision_time"].min())
ho = (df.split == "holdout") & lab
print("rows train/cal/holdout", tr.sum(), va_.sum(), ho.sum(), "positives", int(df.label[tr].sum()), int(df.label[va_].sum()), int(df.label[ho].sum()))
base = Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler()), ("lr", LogisticRegression(max_iter=1000))])
base.fit(X[tr], df.label[tr].astype(int))
before = base.predict_proba(X[ho])[:, 1].copy()
# (2) Pipeline + prefit changes the caller's base model?
vac = VennAbersCalibrator(estimator=base, cv="prefit")
with warnings.catch_warnings():
    warnings.simplefilter("ignore"); vac.fit(X[va_], df.label[va_].astype(int))
after = base.predict_proba(X[ho])[:, 1]
print("pipeline prefit: max abs change of caller base predictions", float(np.max(np.abs(after - before))))
# (3) split conformal LAC on purged calibration rows
base2 = Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler()), ("lr", LogisticRegression(max_iter=1000))]).fit(X[tr], df.label[tr].astype(int))
scc = SplitConformalClassifier(estimator=base2, confidence_level=0.9, prefit=True)
scc.conformalize(X[va_], df.label[va_].astype(int))
_, sets = scc.predict_set(X[ho]); sets = sets[:, :, 0]
yh = df.label[ho].astype(int).values
cov = sets[np.arange(len(yh)), yh]
print("LAC 0.90: coverage", round(cov.mean(), 4), "positives covered", int(cov[yh == 1].sum()), "of", int((yh == 1).sum()), "set sizes", np.bincount(sets.sum(1), minlength=3).tolist())
# (4) risk controller on 16 positives
p_cal = base2.predict_proba(X[va_])[:, 1]
ctrl = BinaryClassificationController(predict_function=base2.predict_proba, risk="precision", target_level=0.2, confidence_level=0.9)
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always"); ctrl.calibrate(X[va_], df.label[va_].astype(int))
print("risk controller best_predict_param:", ctrl.best_predict_param, "| warnings:", [str(x.message)[:70] for x in w][:2])
print("spiegelhalter p (holdout, base):", round(spiegelhalter_p_value(yh, base2.predict_proba(X[ho])[:, 1]), 4))
