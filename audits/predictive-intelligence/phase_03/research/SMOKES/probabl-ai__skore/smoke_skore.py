"""Phase 03 R4 smoke for skore at the pin (run offline): evaluation reports, methodological checks, local project lineage."""
import json
import os
import sys
import tempfile
import time
import warnings

sys.path.insert(0, os.environ.get("R4_HARNESS", os.path.dirname(os.path.abspath(__file__))))
import common as C  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

warnings.filterwarnings("ignore")
t0 = time.perf_counter()
import skore  # noqa: E402
from skore import CrossValidationReport, EstimatorReport, Project  # noqa: E402

IMPORT_S = time.perf_counter() - t0
from sklearn.compose import ColumnTransformer  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.model_selection import KFold, TimeSeriesSplit  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

F = C.FEATURES
df = C.load()
df["decision_ts"] = pd.to_datetime(df.decision_time, unit="s")
tr, va, ho = (df[df.split == s].copy() for s in ("train", "val", "holdout"))
trm, hom = C.matured(tr), C.matured(ho)
prev = float(trm.label.mean())
C.emit("env", {"import_s": round(IMPORT_S, 3), "skore_metadata_version": __import__("importlib.metadata").metadata.version("skore")})


def pipe(cols):
    num = make_pipeline(SimpleImputer(strategy="median"), StandardScaler())
    ct = ColumnTransformer([("num", num, cols)], remainder="drop")  # drops decision_ts
    return make_pipeline(ct, LogisticRegression(max_iter=1000))


def X_of(frame, cols, with_ts=True):
    X = C.log_feats(frame, cols)
    if with_ts:
        X["decision_ts"] = frame["decision_ts"].values
    return X


def metric_dict(display):
    fr = display.frame()
    if isinstance(fr, pd.Series):
        fr = fr.to_frame()
    out = {}
    for k, v in fr.iloc[:, 0].items():
        try:
            out[str(k)] = round(float(v), 5)
        except (TypeError, ValueError):
            out[str(k)] = str(v)
    return out


def checks_frame(rep):
    fr = rep.checks.summarize().frame().reset_index()
    return fr.astype(object).where(fr.notna(), "").map(str).to_dict(orient="records")


# ---- S1: leak trap, with skore's checks (SKD011 golden feature, SKD013 time overlap) ----
s1 = {}
for name, cols in (("legit", F), ("with_trap", F + [C.TRAP])):
    t0 = time.perf_counter()
    rep = EstimatorReport(pipe(cols), X_train=X_of(trm, cols), y_train=trm.label.astype(int),
                          X_test=X_of(hom, cols), y_test=hom.label.astype(int), pos_label=1)
    s1[name] = {"metrics": metric_dict(rep.metrics.summarize()),
                "checks": checks_frame(rep), "seconds": round(time.perf_counter() - t0, 3)}
C.emit("S1_leak_and_checks", s1)

# ---- Role: SKD013 with a shuffled split vs a time split ----
mat = C.matured(df[df.split.isin(["train", "val"])]).sort_values("decision_time")
Xall = X_of(mat, F)
yall = mat.label.astype(int)
role = {}
for name, splitter in (("kfold_shuffled", KFold(n_splits=4, shuffle=True, random_state=0)),
                       ("time_series_split_gap", TimeSeriesSplit(n_splits=4, gap=50))):
    t0 = time.perf_counter()
    cv = CrossValidationReport(pipe(F), X=Xall, y=yall, splitter=splitter, pos_label=1)
    ch0 = cv.checks.summarize().frame().reset_index()
    ch = ch0.astype(object).where(ch0.notna(), "").map(str)
    skd013 = ch[ch.apply(lambda r: "SKD013" in " ".join(r.values), axis=1)]
    role[name] = {"skd013_rows": skd013.to_dict(orient="records"),
                  "cv_metrics_first_column": metric_dict(cv.metrics.summarize()),
                  "seconds": round(time.perf_counter() - t0, 3)}
C.emit("ROLE_time_overlap_check", role)

# ---- S2: probabilities and censored labels ----
rep = EstimatorReport(pipe(F), X_train=X_of(trm, F), y_train=trm.label.astype(int),
                      X_test=X_of(hom, F), y_test=hom.label.astype(int), pos_label=1)
model = rep.estimator_
p = model.predict_proba(X_of(hom, F))[:, 1]
s2 = {"harness_scores": C.scores(hom.label, p, prev),
      "skore_summary": metric_dict(rep.metrics.summarize())}
try:
    EstimatorReport(model, X_test=X_of(ho, F), y_test=ho.label, pos_label=1).metrics.summarize()
    s2["censored_rows_label_nan"] = "accepted"
except Exception as e:  # noqa: BLE001
    s2["censored_rows_label_nan"] = f"raised {type(e).__name__}: {str(e)[:200]}"
C.emit("S2_probs", s2)

# ---- S3: NaN without an imputer ----
try:
    EstimatorReport(make_pipeline(ColumnTransformer([("n", "passthrough", F)]), LogisticRegression()),
                    X_train=X_of(trm, F), y_train=trm.label.astype(int), X_test=X_of(hom, F), y_test=hom.label.astype(int))
    s3 = {"no_imputer": "accepted"}
except Exception as e:  # noqa: BLE001
    s3 = {"no_imputer": f"raised {type(e).__name__}: {str(e)[:160]}"}
C.emit("S3_nan", s3)

# ---- S4: calibration display ----
s4 = {}
try:
    disp = rep.inspection.calibration_curve()
    fr = disp.frame() if hasattr(disp, "frame") else None
    s4["calibration_curve_rows"] = None if fr is None else int(len(fr))
    s4["calibration_curve_head"] = None if fr is None else fr.head(3).astype(str).to_dict(orient="records")
except Exception as e:  # noqa: BLE001
    s4["error"] = f"{type(e).__name__}: {str(e)[:200]}"
C.emit("S4_calibration", s4)

# ---- Role: local project lineage, S5 persistence ----
work = tempfile.mkdtemp(prefix="skore_ws_")
proj = Project("pi_r4", mode="local", workspace=os.path.join(work, "skore"))
t0 = time.perf_counter()
proj.put("baseline_legit", rep)
put_s = time.perf_counter() - t0
summ = proj.summarize()
sdf = summ if isinstance(summ, pd.DataFrame) else getattr(summ, "frame", lambda: pd.DataFrame(summ))()
rid = str(sdf.reset_index()["id"].iloc[0]) if "id" in sdf.reset_index().columns else None
back = proj.get(rid)
p2 = back.estimator_.predict_proba(X_of(hom, F))[:, 1]
files = []
for root, _, fs in os.walk(work):
    files += [os.path.relpath(os.path.join(root, f), work) for f in fs]
meta_file = [f for f in files if f.endswith("metadata.json")][0]
meta = json.load(open(os.path.join(work, meta_file)))
data_refs = {f: json.load(open(os.path.join(work, f))) for f in files if "/data/" in f and f.endswith(".json")}
C.emit("LINEAGE", {"summary_columns": [str(c) for c in sdf.reset_index().columns], "report_id": rid,
                   "metadata_json": meta, "data_refs": data_refs,
                   "pickle_files": sorted(f for f in files if f.endswith(".pickle")),
                   "file_count": len(files), "put_s": round(put_s, 3)})
C.emit("S5_persist", {"reloaded_predictions_identical": bool(np.array_equal(p, p2)), "format": "pickle and joblib files in the workspace"})

# ---- S6: cost ----
t0 = time.perf_counter()
EstimatorReport(pipe(F), X_train=X_of(trm, F), y_train=trm.label.astype(int), X_test=X_of(hom, F), y_test=hom.label.astype(int), pos_label=1).metrics.summarize()
rep_s = time.perf_counter() - t0
t0 = time.perf_counter()
rep.checks.summarize()
chk_s = time.perf_counter() - t0
C.emit("S6_cost", {"import_s": round(IMPORT_S, 3), "report_fit_and_summarize_s": round(rep_s, 3), "checks_summarize_cached_s": round(chk_s, 3)})
print("DONE")
