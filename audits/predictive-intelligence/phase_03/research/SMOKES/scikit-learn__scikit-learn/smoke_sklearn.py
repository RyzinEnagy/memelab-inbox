# Phase 03 smoke harness (shared header, reviewer R1). Synthetic challenge data only:
# results show format and behaviour, never memecoin predictive value.
# Usage: python -I <script> <challenge.csv> <scratch_out_dir>
import csv
import hashlib
import json
import math
import os
import platform
import resource
import socket
import sys
import time
import warnings

import numpy as np

CHALLENGE = sys.argv[1]
SCRATCH = sys.argv[2]
os.makedirs(SCRATCH, exist_ok=True)
RESULTS = {"script": os.path.basename(__file__), "python": sys.version.split()[0],
           "platform": platform.platform(), "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

# Network guard: every AF_INET/AF_INET6 connect is recorded and refused, so any phone-home
# at import, fit or predict shows up as an attempt (and usually an exception).
NET_ATTEMPTS = []
_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex


def _guard_connect(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        NET_ATTEMPTS.append(repr(address))
        raise OSError("network blocked by phase03 smoke guard: %r" % (address,))
    return _orig_connect(self, address)


def _guard_connect_ex(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        NET_ATTEMPTS.append(repr(address))
        return 111
    return _orig_connect_ex(self, address)


socket.socket.connect = _guard_connect
socket.socket.connect_ex = _guard_connect_ex

FEATURES = ["liq_usd", "vol_24h", "age_h", "score100", "fatal_flag", "ret_1h"]
LOG_FEATURES = {"liq_usd", "vol_24h"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fnum(v):
    return float("nan") if v == "" else float(v)


def load():
    with open(CHALLENGE, newline="") as fh:
        rows = list(csv.DictReader(fh))
    d = {}
    for col in rows[0].keys():
        vals = [r[col] for r in rows]
        if col in ("decision_id", "mint", "symbol", "split"):
            d[col] = np.array(vals)
        else:
            d[col] = np.array([fnum(v) for v in vals])
    order = np.argsort(d["decision_time"], kind="stable")
    for k in d:
        d[k] = d[k][order]
    return d


def matrix(d, idx, with_leak=False, log=True):
    cols = []
    names = []
    for f in FEATURES:
        x = d[f][idx].astype(float)
        if log and f in LOG_FEATURES:
            x = np.log(x)
        cols.append(x)
        names.append(("log_" + f) if (log and f in LOG_FEATURES) else f)
    if with_leak:
        cols.append(d["leak_future_ret"][idx])
        names.append("leak_future_ret")
    return np.column_stack(cols), names


def splits(d):
    s = d["split"]
    lab = ~np.isnan(d["label"])
    out = {k: np.where((s == k) & lab)[0] for k in ("train", "val", "holdout")}
    out["holdout_censored"] = int(((s == "holdout") & ~lab).sum())
    out["embargo"] = int((s == "embargo").sum())
    return out


def brier(y, p):
    return float(np.mean((p - y) ** 2))


def logloss(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def auc(y, p):
    # Mann-Whitney AUC with ties averaged, no library dependency
    y = np.asarray(y)
    p = np.asarray(p)
    order = np.argsort(p, kind="mergesort")
    ranks = np.empty(len(p))
    sp = p[order]
    i = 0
    while i < len(sp):
        j = i
        while j + 1 < len(sp) and sp[j + 1] == sp[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1
        i = j + 1
    n1 = y.sum()
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def wilson(k, n, z=1.959964):
    if n == 0:
        return (float("nan"), float("nan"))
    ph = k / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def score_block(y, p, base):
    p = np.asarray(p, dtype=float)
    b = brier(y, p)
    b0 = brier(y, np.full_like(p, base))
    return {"n": int(len(y)), "positives": int(y.sum()), "brier": round(b, 6), "brier_b0": round(b0, 6),
            "bss_vs_b0": round(1 - b / b0, 4) if b0 > 0 else None, "logloss": round(logloss(y, p), 6),
            "logloss_b0": round(logloss(y, np.full_like(p, base)), 6), "auc": round(auc(y, p), 4),
            "mean_p": round(float(p.mean()), 5), "min_p": float(p.min()), "max_p": float(p.max()),
            "finite": bool(np.all(np.isfinite(p))), "in_0_1": bool(np.all((p >= 0) & (p <= 1)))}


def reliability(y, p, n_bins=3):
    # quantile bins (the lab's rule: >= 20 events per bin, at most 5 bins), Wilson check per bin
    order = np.argsort(p, kind="stable")
    bins = np.array_split(order, n_bins)
    out = []
    for b in bins:
        k = int(y[b].sum())
        lo, hi = wilson(k, len(b))
        mp = float(p[b].mean())
        out.append({"n": int(len(b)), "mean_p": round(mp, 4), "obs": round(k / len(b), 4),
                    "wilson95": [round(lo, 4), round(hi, 4)], "inside": bool(lo <= mp <= hi)})
    return out


def maturity_violations(d, train_idx, test_idx):
    # training rows whose label matures after the first test decision: a look-ahead in labels
    t0 = d["decision_time"][test_idx].min()
    return int((d["label_matures_at"][train_idx] > t0).sum())


def day_walk_forward(d, idx, min_train=200):
    # the lab's rule (ACCEPTANCE_METRICS): expanding window by UTC decision day; each fold trains only on
    # labels matured by the first decision of the test day. Custom code, not a library feature.
    t = d["decision_time"][idx]
    mat = d["label_matures_at"][idx]
    days = np.floor(t / 86400).astype(int)
    out = []
    for day in np.unique(days):
        te = idx[days == day]
        start = t[days == day].min()
        tr = idx[mat <= start]
        if len(tr) >= min_train:
            out.append((tr, te))
    return out


def peak_rss_mb():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)


def timed(fn, *a, **k):
    t = time.perf_counter()
    r = fn(*a, **k)
    return r, time.perf_counter() - t


def single_row_latency(fn, X, reps=200):
    ts = []
    for i in range(reps):
        row = X[i % len(X):i % len(X) + 1]
        t = time.perf_counter()
        fn(row)
        ts.append(time.perf_counter() - t)
    return {"median_ms": round(1000 * float(np.median(ts)), 4), "p90_ms": round(1000 * float(np.percentile(ts, 90)), 4)}


def finish():
    RESULTS["network_attempts"] = NET_ATTEMPTS
    RESULTS["peak_rss_mb"] = peak_rss_mb()
    RESULTS["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print("RESULTS_JSON " + json.dumps(RESULTS, sort_keys=True, default=str))


D = load()
SP = splits(D)
RESULTS["challenge_sha256"] = sha256_file(CHALLENGE)
RESULTS["counts"] = {"train": len(SP["train"]), "val": len(SP["val"]), "holdout_scored": len(SP["holdout"]),
                     "holdout_censored_excluded": SP["holdout_censored"], "embargo_rows_unused": SP["embargo"]}
YTR = D["label"][SP["train"]].astype(int)
YVA = D["label"][SP["val"]].astype(int)
YHO = D["label"][SP["holdout"]].astype(int)
BASE = float(YTR.mean())
RESULTS["train_prevalence_b0"] = round(BASE, 5)
# ---- end of shared header ----

# ---- scikit-learn body ----
import pickle

import joblib
import sklearn
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, TimeSeriesSplit, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

RESULTS["library"] = {"sklearn": sklearn.__version__, "path": sklearn.__file__}
RESULTS["network_attempts_after_import"] = list(NET_ATTEMPTS)
tr, va, ho = SP["train"], SP["val"], SP["holdout"]
Xtr, names = matrix(D, tr)
Xva, _ = matrix(D, va)
Xho, _ = matrix(D, ho)
XtrL, namesL = matrix(D, tr, with_leak=True)
XhoL, _ = matrix(D, ho, with_leak=True)


def lr():
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=2000))


def hgb():
    return HistGradientBoostingClassifier(random_state=0, max_iter=150, learning_rate=0.05, max_leaf_nodes=15,
                                          early_stopping=False)


# S3 missing covariates
s3 = {}
try:
    LogisticRegression(max_iter=2000).fit(Xtr, YTR)
    s3["LogisticRegression_raw_nan"] = "accepted"
except ValueError as e:
    s3["LogisticRegression_raw_nan"] = "ValueError: " + str(e).splitlines()[0][:160]
m_h = hgb()
m_h.fit(Xtr, YTR)
p_h_nan = m_h.predict_proba(Xho)[:, 1]
s3["HistGradientBoosting_native_nan"] = {"fit_ok": True, "holdout_rows_with_nan": int(np.isnan(Xho).any(axis=1).sum()),
                                         "proba_finite": bool(np.all(np.isfinite(p_h_nan)))}
s3["pipeline_with_SimpleImputer"] = "ok"
RESULTS["S3_missing"] = s3

# S2 probability shape and imbalance (censored rows never scored)
(m_lr, t_fit_lr) = timed(lambda: lr().fit(Xtr, YTR))
P_lr = m_lr.predict_proba(Xho)
RESULTS["S2_probability"] = {
    "logistic": {"proba_shape": list(P_lr.shape), "rows_sum_to_1": bool(np.allclose(P_lr.sum(axis=1), 1)),
                 "holdout": score_block(YHO, P_lr[:, 1], BASE)},
    "hist_gradient_boosting": {"holdout": score_block(YHO, p_h_nan, BASE)},
    "censored_rows_excluded": SP["holdout_censored"],
}

# S1 leak trap
avail_after = int((D["leak_available_at"] > D["decision_time"]).sum())
m_lr_leak = lr().fit(XtrL, YTR)
m_h_leak = hgb().fit(XtrL, YTR)
RESULTS["S1_leak_trap"] = {
    "rows_where_leak_available_after_decision": avail_after,
    "library_has_availability_time_concept": False,
    "logistic_without_leak": score_block(YHO, P_lr[:, 1], BASE),
    "logistic_with_leak": score_block(YHO, m_lr_leak.predict_proba(XhoL)[:, 1], BASE),
    "hgb_without_leak": score_block(YHO, p_h_nan, BASE),
    "hgb_with_leak": score_block(YHO, m_h_leak.predict_proba(XhoL)[:, 1], BASE),
    "library_refused_leak_column": False,
}

# S1 splitters: TimeSeriesSplit counts rows, not seconds; label maturity is not modelled
dev = np.sort(np.concatenate([tr, va]))
Xdev, _ = matrix(D, dev)
ydev = D["label"][dev].astype(int)
tss_rows = {}
for gap in (0, 50, 100, 150):
    viol = []
    for a, b in TimeSeriesSplit(n_splits=5, gap=gap).split(Xdev):
        viol.append(maturity_violations(D, dev[a], dev[b]))
    tss_rows["gap_%d_rows" % gap] = {"train_rows_with_label_maturing_after_test_start_per_fold": viol}
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    list(TimeSeriesSplit(n_splits=3).split(Xdev, ydev, groups=D["mint"][dev]))
    groups_warning = [str(x.message) for x in w]
wf = day_walk_forward(D, dev, min_train=300)
wf_local = [(np.searchsorted(dev, a), np.searchsorted(dev, b)) for a, b in wf]
wf_viol = [maturity_violations(D, dev[a], dev[b]) for a, b in wf_local]
cv_scores = cross_val_score(lr(), Xdev, ydev, cv=wf_local, scoring="neg_brier_score")
gkf = GroupKFold(n_splits=5)
gkf_future = []
for a, b in gkf.split(Xdev, ydev, groups=D["mint"][dev]):
    gkf_future.append(int((D["decision_time"][dev[a]] > D["decision_time"][dev[b]].min()).sum()))
RESULTS["S1_splitters"] = {
    "TimeSeriesSplit": tss_rows,
    "TimeSeriesSplit_groups_argument": groups_warning,
    "custom_day_walk_forward": {"folds": len(wf_local), "maturity_violations_per_fold": wf_viol,
                                "accepted_as_cv_iterable_by_cross_val_score": True,
                                "neg_brier_per_fold": [round(float(s), 5) for s in cv_scores]},
    "GroupKFold_by_mint_train_rows_later_than_test_start_per_fold": gkf_future,
}

# S4 calibration: fit on train, calibrate on later val with FrozenEstimator (time respecting), score holdout
s4 = {"uncalibrated_hgb_holdout": score_block(YHO, p_h_nan, BASE),
      "uncalibrated_hgb_reliability_3bins": reliability(YHO, p_h_nan, 3)}
for method in ("sigmoid", "isotonic", "temperature"):
    cal = CalibratedClassifierCV(FrozenEstimator(m_h), method=method).fit(Xva, YVA)
    pc = cal.predict_proba(Xho)[:, 1]
    s4["frozen_" + method] = {"holdout": score_block(YHO, pc, BASE), "reliability_3bins": reliability(YHO, pc, 3)}
    if method == "sigmoid":
        cal_sig = cal
prob_true, prob_pred = calibration_curve(YHO, cal_sig.predict_proba(Xho)[:, 1], n_bins=3, strategy="quantile")
s4["calibration_curve_quantile_3"] = {"prob_true": [round(float(v), 4) for v in prob_true],
                                      "prob_pred": [round(float(v), 4) for v in prob_pred],
                                      "returns_bin_counts": False}
# default cv ignores time order: StratifiedKFold folds put later rows in training
cal_default = CalibratedClassifierCV(hgb(), method="sigmoid").fit(Xdev, ydev)
s4["default_cv"] = {"cv_used": "5-fold StratifiedKFold (check_cv default)", "raised": False,
                    "holdout": score_block(YHO, cal_default.predict_proba(Xho)[:, 1], BASE)}
try:
    CalibratedClassifierCV(hgb(), method="sigmoid", cv=TimeSeriesSplit(5), ensemble=False).fit(Xdev, ydev)
    s4["ensemble_false_timeseriessplit"] = "accepted"
except ValueError as e:
    s4["ensemble_false_timeseriessplit"] = "ValueError: " + str(e).splitlines()[0][:160]
cal_wf = CalibratedClassifierCV(hgb(), method="sigmoid", cv=wf_local, ensemble=True).fit(Xdev, ydev)
s4["walk_forward_cv_ensemble"] = {"n_calibrated_pairs": len(cal_wf.calibrated_classifiers_),
                                  "holdout": score_block(YHO, cal_wf.predict_proba(Xho)[:, 1], BASE)}
s4["conformal_or_interval_methods_in_library"] = False
RESULTS["S4_calibration"] = s4

# S5 persistence
p_ref = cal_sig.predict_proba(Xho)[:, 1]
pk = os.path.join(SCRATCH, "sk_cal.pkl")
with open(pk, "wb") as fh:
    pickle.dump(cal_sig, fh, protocol=5)
with open(pk, "rb") as fh:
    re_pk = pickle.load(fh)
jb = os.path.join(SCRATCH, "sk_cal.joblib")
joblib.dump(cal_sig, jb)
re_jb = joblib.load(jb)
state = m_h.__getstate__()
RESULTS["S5_persistence"] = {
    "pickle": {"bytes": os.path.getsize(pk), "sha256": sha256_file(pk),
               "identical": bool(np.array_equal(p_ref, re_pk.predict_proba(Xho)[:, 1]))},
    "joblib": {"bytes": os.path.getsize(jb), "identical": bool(np.array_equal(p_ref, re_jb.predict_proba(Xho)[:, 1]))},
    "version_stamp_in_state": state.get("_sklearn_version"),
    "format_note": "pickle/joblib execute code on load; skops and ONNX are separate packages, not tested here",
}

# S6 cost
m_h2, t_fit_h = timed(lambda: hgb().fit(Xtr, YTR))
_, t_pred_h = timed(lambda: m_h2.predict_proba(Xho))
_, t_pred_lr = timed(lambda: m_lr.predict_proba(Xho))
RESULTS["S6_cost"] = {
    "fit_s": {"logistic_pipeline": round(t_fit_lr, 4), "hgb": round(t_fit_h, 4)},
    "batch_predict_per_row_ms": {"logistic_pipeline": round(1000 * t_pred_lr / len(ho), 5),
                                 "hgb": round(1000 * t_pred_h / len(ho), 5)},
    "single_row_latency": {"logistic_pipeline": single_row_latency(m_lr.predict_proba, Xho),
                           "hgb": single_row_latency(m_h2.predict_proba, Xho),
                           "calibrated_sigmoid": single_row_latency(cal_sig.predict_proba, Xho)},
}
finish()
