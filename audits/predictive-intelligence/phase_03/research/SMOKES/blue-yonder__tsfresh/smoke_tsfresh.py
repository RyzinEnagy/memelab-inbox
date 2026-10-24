"""R3 Phase 03 smoke for blue-yonder/tsfresh at pin 6af3c00 (tested with PyPI wheel 0.21.2, whose package code equals the
pin except one docstring typo fix). Synthetic seeded paths (r3_common.seeded_paths, seed 20261026) with an R3 synthetic
label: does close rise 5% above the decision close within the next 12 kept candles. Format and behaviour only."""
import os, sys, time, pickle, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import r3_common as C
tm = C.Timer()
with tm("import_s"):
    import pandas as pd
    import tsfresh
    from tsfresh import extract_features, select_features
    from tsfresh.utilities.dataframe_functions import roll_time_series, impute
    from tsfresh.feature_extraction import ComprehensiveFCParameters, EfficientFCParameters, MinimalFCParameters
    from tsfresh.feature_extraction.settings import from_columns
    from sklearn.metrics import roc_auc_score
warnings.filterwarnings("ignore")
res = {"env": C.env_info(), "tsfresh_version": tsfresh.__version__, "pandas": pd.__version__,
       "settings_sizes": {"comprehensive": len(ComprehensiveFCParameters()), "efficient": len(EfficientFCParameters()),
                          "minimal": len(MinimalFCParameters())}}
paths = C.seeded_paths()
rng = np.random.default_rng(20261028)
W = 12
rows = []; dec = []
for p in paths[:150]:
    n = len(p["t"])
    lr = np.r_[0.0, np.diff(np.log(p["close"]))]
    for j in range(n):
        rows.append((p["mint"], int(p["t"][j]), float(lr[j]), float(np.log(p["volume"][j]))))
    if n >= W + 13:
        d = int(rng.integers(W, n - 12))
        fut = p["close"][d + 1:d + 13]
        dec.append((p["mint"], int(p["t"][d]), int(np.max(fut) / p["close"][d] - 1 > 0.05)))
df = pd.DataFrame(rows, columns=["id", "time", "ret", "logvol"])
decs = pd.DataFrame(dec, columns=["id", "time", "y"])
res["data"] = {"paths": 150, "rows": len(df), "decisions": len(decs), "positives": int(decs["y"].sum())}

# S1a: rolling direction. Positive direction: window id (mint, t) = rows up to and including t. Negative: rows from t on.
roll = {}
for direction in (1, -1):
    with tm(f"roll_dir{direction}_s"):
        r = roll_time_series(df, column_id="id", column_sort="time", max_timeshift=W - 1, min_timeshift=W - 1,
                             rolling_direction=direction, n_jobs=0, disable_progressbar=True)
    r["win_t"] = r["id"].map(lambda v: v[1])
    keep = set(zip(decs["id"], decs["time"]))
    r = r[[(a[0], a[1]) in keep for a in r["id"]]]
    roll[direction] = r
    res[f"rolled_dir{direction}"] = {"windows_for_decisions": int(r["id"].nunique()),
        "rows_after_window_time": int((r["time"] > r["win_t"]).sum()), "rows_total": len(r)}

feat = {}
for direction, r in roll.items():
    with tm(f"extract_minimal_dir{direction}_s"):
        f = extract_features(r.drop(columns=["win_t"]), column_id="id", column_sort="time",
                             default_fc_parameters=MinimalFCParameters(), n_jobs=0, disable_progressbar=True)
    feat[direction] = f
y_map = {(a, b): c for a, b, c in dec}
def auc_of(f, col):
    ids = [i for i in f.index]
    y = np.array([y_map[(i[0], i[1])] for i in ids]); x = f[col].to_numpy()
    ok = np.isfinite(x)
    return float(roc_auc_score(y[ok], x[ok])) if len(set(y[ok])) == 2 else None
res["S1_direction_leak"] = {"window": "12 rows",
    "auc_ret_maximum_backward": auc_of(feat[1], "ret__maximum"), "auc_ret_maximum_forward": auc_of(feat[-1], "ret__maximum"),
    "auc_ret_sum_values_backward": auc_of(feat[1], "ret__sum_values"), "auc_ret_sum_values_forward": auc_of(feat[-1], "ret__sum_values"),
    "library_stopped_it": False,
    "note": "with rolling_direction=-1 the window named (mint, t) holds rows at or after t; the library allows it"}

# S1b: truncation invariance of the backward window (features at t from data cut at t)
p0 = paths[0]; n0 = len(p0["t"]); dcut = int(0.6 * n0)
dfa = df[df["id"] == p0["mint"]]
dfb = dfa.iloc[:dcut]
ra = roll_time_series(dfa, "id", "time", max_timeshift=W - 1, min_timeshift=W - 1, n_jobs=0, disable_progressbar=True)
rb = roll_time_series(dfb, "id", "time", max_timeshift=W - 1, min_timeshift=W - 1, n_jobs=0, disable_progressbar=True)
fa = extract_features(ra, column_id="id", column_sort="time", default_fc_parameters=EfficientFCParameters(), n_jobs=0, disable_progressbar=True)
fb = extract_features(rb, column_id="id", column_sort="time", default_fc_parameters=EfficientFCParameters(), n_jobs=0, disable_progressbar=True)
common = fb.index.intersection(fa.index)
A = fa.loc[common, fb.columns].to_numpy(dtype=float); B = fb.loc[common].to_numpy(dtype=float)
same = np.isclose(A, B, equal_nan=True)
res["S1_truncation_backward"] = {"windows_compared": len(common), "features": fb.shape[1],
    "cells_equal": int(same.sum()), "cells_total": int(same.size)}

# S1c: impute() uses column statistics of the whole frame it is given (train and holdout together)
Fe = feat[1].copy()
order = sorted(Fe.index, key=lambda i: i[1]); Fe = Fe.loc[order]
cut = int(0.7 * len(Fe))
Fe.iloc[0, 0] = np.nan
all_imp = impute(Fe.copy())
tr_imp = impute(Fe.iloc[:cut].copy())
res["S1_impute_scope"] = {"feature": Fe.columns[0], "value_imputed_with_all_rows": float(all_imp.iloc[0, 0]),
    "value_imputed_with_train_rows_only": float(tr_imp.iloc[0, 0]),
    "differs": bool(all_imp.iloc[0, 0] != tr_imp.iloc[0, 0])}

# P22: feature explosion and selection under null labels at small N
with tm("extract_comprehensive_decisions_s"):
    Fc = extract_features(roll[1].drop(columns=["win_t"]), column_id="id", column_sort="time",
                          default_fc_parameters=ComprehensiveFCParameters(), n_jobs=0, disable_progressbar=True)
Fc_imp = impute(Fc.copy())
yv = pd.Series([y_map[(i[0], i[1])] for i in Fc_imp.index], index=Fc_imp.index)
sel_true = select_features(Fc_imp, yv, n_jobs=0)
null_counts = []
for s in range(5):
    yn = pd.Series(np.random.default_rng(100 + s).permutation(yv.to_numpy()), index=yv.index)
    null_counts.append(int(select_features(Fc_imp, yn, n_jobs=0).shape[1]))
res["P22_selection"] = {"decisions": len(Fc_imp), "features_extracted": Fc.shape[1], "selected_true_label": int(sel_true.shape[1]),
    "selected_under_5_permuted_labels": null_counts, "fdr_level": 0.05, "hypotheses_independent": False,
    "extract_ms_per_decision_window": round(1000 * tm.t["extract_comprehensive_decisions_s"] / len(Fc), 2)}

# S3: NaN in the series
dn = dfa.copy(); dn.iloc[5, 2] = np.nan
try:
    extract_features(dn, column_id="id", column_sort="time", default_fc_parameters=MinimalFCParameters(), n_jobs=0, disable_progressbar=True)
    s3 = "no error"
except Exception as e:
    s3 = type(e).__name__ + ": " + str(e)[:150]
res["S3_nan_in_series"] = s3

# S5: reproducible feature set via from_columns, and pickle of the settings
kind_params = from_columns(sel_true.columns) if sel_true.shape[1] else from_columns(Fc.columns[:20])
blob = pickle.dumps(kind_params)
again = extract_features(roll[1].drop(columns=["win_t"]), column_id="id", column_sort="time",
                         kind_to_fc_parameters=pickle.loads(blob), n_jobs=0, disable_progressbar=True)
cols = [c for c in again.columns if c in Fc.columns]
res["S5_persistence"] = {"settings_pickle_bytes": len(blob), "columns_reproduced": len(cols), "columns_requested": int(sel_true.shape[1]) if sel_true.shape[1] else 20,
    "values_identical": bool(np.allclose(again[cols].to_numpy(dtype=float), Fc.loc[again.index, cols].to_numpy(dtype=float), equal_nan=True))}

# S6: one decision-time window, comprehensive vs efficient vs minimal (warm)
one = roll[1][roll[1]["id"] == roll[1]["id"].iloc[0]].drop(columns=["win_t"])
for name, st in (("comprehensive", ComprehensiveFCParameters()), ("efficient", EfficientFCParameters()), ("minimal", MinimalFCParameters())):
    s = time.perf_counter()
    extract_features(one, column_id="id", column_sort="time", default_fc_parameters=st, n_jobs=0, disable_progressbar=True)
    res.setdefault("S6_one_window_ms", {})[name] = round(1000 * (time.perf_counter() - s), 1)
res["S2"] = "SKIPPED: feature extraction only, no probability output"
res["S4"] = "SKIPPED: no calibration or uncertainty API"
res["S6_timings"] = dict(tm.t)
C.dump(res, os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoke_tsfresh.result.json"))
