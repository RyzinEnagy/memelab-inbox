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

# ---- LightGBM body ----
import pickle

import lightgbm as lgb

RESULTS["library"] = {"lightgbm": lgb.__version__, "path": lgb.__file__}
RESULTS["network_attempts_after_import"] = list(NET_ATTEMPTS)
tr, va, ho = SP["train"], SP["val"], SP["holdout"]
Xtr, names = matrix(D, tr, log=False)
Xva, _ = matrix(D, va, log=False)
Xho, _ = matrix(D, ho, log=False)
XtrL, _ = matrix(D, tr, with_leak=True, log=False)
XhoL, _ = matrix(D, ho, with_leak=True, log=False)
PARAMS = dict(n_estimators=200, learning_rate=0.03, num_leaves=15, min_child_samples=20, subsample=1.0,
              colsample_bytree=1.0, random_state=7, deterministic=True, force_row_wise=True, n_jobs=1, verbose=-1)


def model(**kw):
    p = dict(PARAMS)
    p.update(kw)
    return lgb.LGBMClassifier(**p)


# S3 + S2: native NaN handling, probability shape
(m, t_fit) = timed(lambda: model().fit(Xtr, YTR))
P = m.predict_proba(Xho)
RESULTS["S3_missing"] = {"fit_with_nan_ok": True, "train_rows_with_nan": int(np.isnan(Xtr).any(axis=1).sum()),
                         "holdout_rows_with_nan": int(np.isnan(Xho).any(axis=1).sum()),
                         "proba_finite": bool(np.all(np.isfinite(P))), "params_default": {"use_missing": True,
                                                                                         "zero_as_missing": False}}
RESULTS["S2_probability"] = {"proba_shape": list(P.shape), "rows_sum_to_1": bool(np.allclose(P.sum(axis=1), 1)),
                             "holdout": score_block(YHO, P[:, 1], BASE),
                             "censored_rows_excluded": SP["holdout_censored"]}

# imbalance switches distort probabilities (they reweight the loss)
pu = model(is_unbalance=True).fit(Xtr, YTR).predict_proba(Xho)[:, 1]
ps = model(scale_pos_weight=10.0).fit(Xtr, YTR).predict_proba(Xho)[:, 1]
RESULTS["S2_imbalance_options"] = {"is_unbalance_true": score_block(YHO, pu, BASE),
                                   "scale_pos_weight_10": score_block(YHO, ps, BASE),
                                   "holdout_prevalence": round(float(YHO.mean()), 5)}

# small-N behaviour: first 300 training rows only (about the lab's event counts)
small = slice(0, 300)
psm = model().fit(Xtr[small], YTR[small]).predict_proba(Xho)[:, 1]
psm_reg = model(n_estimators=100, num_leaves=4, min_child_samples=40, reg_lambda=5.0).fit(
    Xtr[small], YTR[small]).predict_proba(Xho)[:, 1]
RESULTS["small_n_300"] = {"positives_in_300": int(YTR[small].sum()), "default_params": score_block(YHO, psm, BASE),
                          "shrunk_params": score_block(YHO, psm_reg, BASE)}

# S1 leak trap
mL = model().fit(XtrL, YTR)
RESULTS["S1_leak_trap"] = {"without_leak": score_block(YHO, P[:, 1], BASE),
                           "with_leak": score_block(YHO, mL.predict_proba(XhoL)[:, 1], BASE),
                           "library_has_availability_time_concept": False, "library_refused_leak_column": False}

# S1 cv: lgb.cv defaults (stratified=True, shuffle=True) versus a custom day walk-forward folds iterable
dev = np.sort(np.concatenate([tr, va]))
Xdev, _ = matrix(D, dev, log=False)
ydev = D["label"][dev].astype(int)
ds = lgb.Dataset(Xdev, ydev, free_raw_data=False)
cvp = {"objective": "binary", "learning_rate": 0.03, "num_leaves": 15, "verbose": -1, "seed": 7,
       "deterministic": True, "force_row_wise": True, "num_threads": 1, "metric": "binary_logloss"}
r_def = lgb.cv(cvp, ds, num_boost_round=50, nfold=5, return_cvbooster=False)
wf = day_walk_forward(D, dev, min_train=300)
wf_local = [(np.searchsorted(dev, a), np.searchsorted(dev, b)) for a, b in wf]
r_wf = lgb.cv(cvp, lgb.Dataset(Xdev, ydev, free_raw_data=False), num_boost_round=50, folds=wf_local)
RESULTS["S1_cv"] = {"lgb_cv_default": {"stratified": True, "shuffle": True, "nfold": 5, "raised": False,
                                       "final_valid_logloss_mean": round(float(r_def["valid binary_logloss-mean"][-1]), 5)},
                    "lgb_cv_custom_walk_forward": {"folds": len(wf_local), "accepted": True,
                                                   "final_valid_logloss_mean": round(float(r_wf["valid binary_logloss-mean"][-1]), 5)}}
# fold look-ahead of the default: engine.py _make_n_folds uses _LGBMStratifiedKFold (= sklearn StratifiedKFold)
# with shuffle=True and random_state=seed, so the same indices are rebuilt here
from sklearn.model_selection import StratifiedKFold  # noqa: E402

la = []
for a, b in StratifiedKFold(n_splits=5, shuffle=True, random_state=7).split(Xdev, ydev):
    la.append(int((D["decision_time"][dev[a]] > D["decision_time"][dev[b]].min()).sum()))
RESULTS["S1_cv"]["default_fold_train_rows_later_than_test_start"] = la

# determinism: two fits with the same seed give identical model text
def trees_only(s):
    # drop the trailing parameters block, which records num_threads itself
    return s.split("\nparameters:")[0]


m1, m2, m3 = model().fit(Xtr, YTR), model().fit(Xtr, YTR), model(n_jobs=2).fit(Xtr, YTR)
s1, s2, s3 = (trees_only(x.booster_.model_to_string()) for x in (m1, m2, m3))
RESULTS["determinism"] = {"same_seed_same_threads_trees_identical": s1 == s2,
                          "threads_1_vs_2_trees_identical": s1 == s3,
                          "threads_1_vs_2_max_abs_proba_diff": float(np.max(np.abs(
                              m1.predict_proba(Xho)[:, 1] - m3.predict_proba(Xho)[:, 1])))}

# S4 calibration: none built in; report reliability of raw probabilities
RESULTS["S4_calibration"] = {"built_in_calibration": False, "raw_reliability_3bins": reliability(YHO, P[:, 1], 3),
                             "intervals_or_quantiles": "objective='quantile' exists for regression only; no class-probability interval"}

# S5 persistence: native text model, JSON dump, pickle
txt = os.path.join(SCRATCH, "lgb_model.txt")
m.booster_.save_model(txt)
b2 = lgb.Booster(model_file=txt)
p_txt = b2.predict(Xho)
pk = os.path.join(SCRATCH, "lgb_model.pkl")
with open(pk, "wb") as fh:
    pickle.dump(m, fh)
with open(pk, "rb") as fh:
    m_pk = pickle.load(fh)
dump = m.booster_.dump_model()
RESULTS["S5_persistence"] = {
    "native_text": {"bytes": os.path.getsize(txt), "sha256": sha256_file(txt),
                    "identical": bool(np.array_equal(p_txt, P[:, 1])),
                    "max_abs_diff": float(np.max(np.abs(p_txt - P[:, 1])))},
    "pickle": {"identical": bool(np.array_equal(m_pk.predict_proba(Xho)[:, 1], P[:, 1]))},
    "json_dump_keys": sorted(dump.keys())[:12],
    "text_header_version": open(txt).readline().strip(),
}

# S6 cost
_, t_pred = timed(lambda: m.predict_proba(Xho))
RESULTS["S6_cost"] = {"fit_s_200_trees_1_thread": round(t_fit, 4),
                      "batch_predict_per_row_ms": round(1000 * t_pred / len(ho), 5),
                      "single_row_latency": single_row_latency(m.predict_proba, Xho),
                      "single_row_latency_booster": single_row_latency(b2.predict, Xho)}
finish()
