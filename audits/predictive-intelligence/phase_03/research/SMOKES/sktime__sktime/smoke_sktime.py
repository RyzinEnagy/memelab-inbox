"""R3 Phase 03 smoke for sktime/sktime at pin 2cc1253 (installed from the pinned source; version string 1.2.0; core
dependencies only, pandas 3.0.5). Shared synthetic challenge (sha256 checked) for splitters on irregular decision times,
and seeded synthetic paths (r3_common.seeded_paths, seed 20261026; label seed 20261028) for a short unequal-length
panel. Format and behaviour only."""
import os, sys, time, warnings, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import r3_common as C
tm = C.Timer()
with tm("import_s"):
    import pandas as pd
    import sktime
    from sktime.split import ExpandingWindowSplitter, ExpandingCutoffSplitter, InstanceSplitter, temporal_train_test_split
    from sktime.datatypes import check_is_mtype
    from sktime.registry import all_estimators
warnings.filterwarnings("ignore")
res = {"env": C.env_info(), "sktime_version": sktime.__version__, "sktime_file": sktime.__file__, "pandas": pd.__version__}
d = C.load(); M = C.masks(d)
t = pd.to_datetime(d["decision_time"], unit="s", utc=True)
idx = pd.DatetimeIndex(t)
mat = pd.to_datetime(d["label_matures_at"], unit="s", utc=True)
res["decision_index"] = {"n": len(idx), "monotonic": bool(idx.is_monotonic_increasing), "duplicates": int(idx.duplicated().sum()),
                         "inferred_freq": str(pd.infer_freq(idx[:50])) if len(idx) > 3 else None}
y = pd.Series(np.nan_to_num(d["label"], nan=-1), index=idx)

def fold_report(splitter, yy):
    out = []
    try:
        for tr, te in splitter.split(yy):
            if len(te) == 0 or len(tr) == 0:
                out.append({"train": len(tr), "test": len(te)}); continue
            test_start = yy.index[te].min()
            unmat = int((mat[tr] > test_start).sum())
            out.append({"train": int(len(tr)), "test": int(len(te)),
                        "gap_s": float((test_start - yy.index[tr].max()).total_seconds()),
                        "train_labels_not_matured_at_test_start": unmat})
        return {"folds": len(out), "detail": out[:6], "raised": None}
    except Exception as e:
        return {"folds": len(out), "detail": out[:3], "raised": type(e).__name__ + ": " + str(e)[:160]}

# A1: row-count expanding window
res["A1_expanding_rows"] = fold_report(ExpandingWindowSplitter(fh=list(range(1, 101)), initial_window=1000, step_length=400), y)
# A2: time-based windows on an irregular DatetimeIndex
res["A2_expanding_timedelta"] = fold_report(ExpandingWindowSplitter(fh=[pd.Timedelta("1D")], initial_window=pd.Timedelta("12D"),
                                                                    step_length=pd.Timedelta("3D")), y)
# A3: row-count gap emulated through fh offset (100-row gap)
res["A3_fh_offset_gap_100_rows"] = fold_report(ExpandingWindowSplitter(fh=list(range(101, 201)), initial_window=1000, step_length=400), y)
# A4: expanding cutoff on a timestamp
res["A4_expanding_cutoff_timestamp"] = fold_report(ExpandingCutoffSplitter(cutoff=idx[1500], fh=list(range(1, 101)), step_length=400), y)
# A5: group split by mint (instance) on a (mint, time) MultiIndex
mi = pd.MultiIndex.from_arrays([d["mint"], idx], names=["mint", "time"])
ym = pd.DataFrame({"label": y.to_numpy()}, index=mi).sort_index()  # a Series with this MultiIndex was refused (first run)
try:
    from sklearn.model_selection import KFold
    sp = InstanceSplitter(cv=KFold(n_splits=3))
    folds = list(sp.split(ym))
    mints = ym.index.get_level_values(0)
    overlap = [len(set(mints[tr]) & set(mints[te])) for tr, te in folds]
    res["A5_instance_splitter"] = {"folds": len(folds), "mint_overlap_train_test": overlap, "raised": None,
        "time_order_inside_fold": "not enforced (instances split, timestamps ignored)"}
except Exception as e:
    res["A5_instance_splitter"] = {"raised": type(e).__name__ + ": " + str(e)[:160]}

# S1: trap column through an sktime split, model is scikit-learn logistic regression (sktime has no tabular classifier)
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
lab = ~np.isnan(d["label"])
def s1(with_trap):
    X, cols = C.design(d, np.ones(len(idx), bool), with_trap=with_trap)
    briers = []; bases = []
    for tr, te in ExpandingWindowSplitter(fh=list(range(1, 101)), initial_window=1000, step_length=400).split(y):
        tr = tr[lab[tr]]; te = te[lab[te]]
        m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=1000)).fit(X[tr], d["label"][tr])
        p = m.predict_proba(X[te])[:, 1]
        briers.append(C.brier(d["label"][te], p)); bases.append(C.brier(d["label"][te], np.full(len(te), d["label"][tr].mean())))
    return {"mean_fold_brier": float(np.mean(briers)), "mean_fold_brier_base": float(np.mean(bases)), "folds": len(briers)}
res["S1_trap_through_splitter"] = {"clean": s1(False), "with_trap": s1(True), "library_stopped_it": False,
    "evaluate_note": "forecasting evaluate() passes X_test (future exogenous rows) to predict (_functions.py:289)"}

# D: forecasting on one short irregular series
from sktime.forecasting.naive import NaiveForecaster
paths = C.seeded_paths()
p0 = max(paths, key=lambda q: q["n_dense"] - len(q["t"]))
ser = pd.Series(np.log(p0["close"]), index=pd.to_datetime(p0["t"], unit="s"))
try:
    f = NaiveForecaster(strategy="last").fit(ser)
    pr = f.predict(fh=[1])
    res["D_forecast_irregular"] = {"raised": None, "predicted_index": str(pr.index[0]), "last_obs": str(ser.index[-1])}
except Exception as e:
    res["D_forecast_irregular"] = {"raised": type(e).__name__ + ": " + str(e)[:200]}

# C: short unequal-length panel classification
rng = np.random.default_rng(20261028)
inst = []; ys = []; tdec = []
for k, p in enumerate(paths):
    n = len(p["t"])
    if n < 30:
        continue
    dd = int(rng.integers(8, n - 12))
    L = min(dd + 1, 24)
    w = p["close"][dd - L + 1:dd + 1]; ts = p["t"][dd - L + 1:dd + 1]
    r = np.r_[0.0, np.diff(np.log(w))]
    for j in range(L):
        inst.append((p["mint"], pd.Timestamp(int(ts[j]), unit="s"), r[j]))
    ys.append(int(np.max(p["close"][dd + 1:dd + 13]) / p["close"][dd] - 1 > 0.05)); tdec.append(int(p["t"][dd]))
Xp = pd.DataFrame(inst, columns=["mint", "time", "ret"]).set_index(["mint", "time"])
ids = Xp.index.get_level_values(0).unique()
yv = np.array(ys)
ok, msg, meta = check_is_mtype(Xp, "pd-multiindex", return_metadata=True, msg_return_dict="dict")
res["C_panel_meta"] = {"valid_pd_multiindex": bool(ok), "n_instances": int(meta.get("n_instances", -1)),
    "is_equal_length": meta.get("is_equal_length"), "is_equally_spaced": meta.get("is_equally_spaced"), "has_nans": meta.get("has_nans"),
    "positives": int(yv.sum())}
with tm("registry_s"):
    allc = all_estimators("classifier", return_names=True)
    unequal = all_estimators("classifier", filter_tags={"capability:unequal_length": True}, return_names=True)
    missing = all_estimators("classifier", filter_tags={"capability:missing_values": True}, return_names=True)
def nodeps(cls):
    deps = cls.get_class_tag("python_dependencies", None)
    return not deps
res["C_registry"] = {"classifiers": len(allc), "unequal_length": len(unequal), "missing_values": len(missing),
    "unequal_and_missing": len(set(n for n, _ in unequal) & set(n for n, _ in missing)),
    "unequal_core_deps_only": sorted(n for n, c in unequal if nodeps(c))[:40]}
order = np.argsort(np.array(tdec)); ntr = int(0.7 * len(order))
tr_ids = ids[order[:ntr]]; te_ids = ids[order[ntr:]]
Xtr = Xp.loc[list(tr_ids)]; Xte = Xp.loc[list(te_ids)]
ytr = yv[order[:ntr]]; yte = yv[order[ntr:]]
base = float(ytr.mean())
results = {}
from sktime.classification.feature_based import SummaryClassifier
from sktime.classification.dummy import DummyClassifier
from sktime.classification.distance_based import KNeighborsTimeSeriesClassifier
from sktime.classification.compose import SklearnClassifierPipeline
from sktime.transformations.series.summarize import SummaryTransformer
def summary_lr():
    return SklearnClassifierPipeline(LogisticRegression(max_iter=1000), [SummaryTransformer()])
cands = {"SummaryClassifier": lambda: SummaryClassifier(random_state=0), "DummyClassifier(prior)": lambda: DummyClassifier(strategy="prior"),
         "KNeighborsTimeSeriesClassifier(dtw)": lambda: KNeighborsTimeSeriesClassifier(n_neighbors=15),
         "SklearnClassifierPipeline(SummaryTransformer, LogisticRegression)": summary_lr}
for name, mk in cands.items():
    try:
        est = mk()
        s = time.perf_counter(); est.fit(Xtr, ytr); fs = time.perf_counter() - s
        s = time.perf_counter(); P = est.predict_proba(Xte); ps = time.perf_counter() - s
        rep = C.prob_report(yte, np.asarray(P)[:, 1], base)
        rep.update({"fit_s": round(fs, 3), "predict_ms_per_instance": round(1000 * ps / len(te_ids), 3), "proba_shape": list(np.asarray(P).shape),
                    "tags_unequal": est.get_tag("capability:unequal_length"), "tags_missing": est.get_tag("capability:missing_values")})
        results[name] = rep
    except Exception as e:
        results[name] = {"raised": type(e).__name__ + ": " + str(e)[:200]}
res["C_classification_S2_S6"] = results
# S3: NaN inside the panel
Xn = Xtr.copy(); Xn.iloc[3, 0] = np.nan
s3 = {}
for name, mk in (("SummaryClassifier", lambda: SummaryClassifier(random_state=0)), ("SummaryTransformer_LR_pipeline", summary_lr)):
    try:
        e = mk().fit(Xn, ytr); P = np.asarray(e.predict_proba(Xte))
        s3[name] = {"raised": None, "proba_finite": bool(np.all(np.isfinite(P)))}
    except Exception as ex:
        s3[name] = {"raised": type(ex).__name__ + ": " + str(ex)[:160]}
res["S3_nan_panel"] = s3
# S5: persistence via BaseObject.save / load
try:
    est = summary_lr().fit(Xtr, ytr)
    ser_obj = est.save()
    from sktime.base import load
    est2 = load(ser_obj)
    same = np.array_equal(np.asarray(est.predict_proba(Xte)), np.asarray(est2.predict_proba(Xte)))
    res["S5_persistence"] = {"estimator": "SklearnClassifierPipeline(SummaryTransformer, LogisticRegression)",
        "format": "BaseObject.save() returns an in-memory pickle; with a path it writes a zip holding pickles", "identical": bool(same), "raised": None}
except Exception as e:
    res["S5_persistence"] = {"raised": type(e).__name__ + ": " + str(e)[:200]}
res["S4"] = "SKIPPED for sktime core: no classifier calibration in core; probabilistic forecasting intervals need soft dependencies (skpro) not installed"
res["S6_timings"] = dict(tm.t)
C.dump(res, os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoke_sktime.result.json"))
