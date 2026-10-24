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

# ---- interpret (EBM) body ----
import io
import pickle

import interpret
from interpret.glassbox import ExplainableBoostingClassifier

RESULTS["library"] = {"interpret": interpret.__version__, "path": interpret.__file__}
RESULTS["network_attempts_after_import"] = list(NET_ATTEMPTS)
tr, va, ho = SP["train"], SP["val"], SP["holdout"]
Xtr, names = matrix(D, tr)
Xho, _ = matrix(D, ho)
XtrL, namesL = matrix(D, tr, with_leak=True)
XhoL, _ = matrix(D, ho, with_leak=True)


def ebm(**kw):
    p = dict(random_state=7, n_jobs=1, feature_names=names)
    p.update(kw)
    return ExplainableBoostingClassifier(**p)


# S3 + S2 with defaults
m, t_fit = timed(lambda: ebm().fit(Xtr, YTR))
P = m.predict_proba(Xho)
RESULTS["defaults"] = {k: getattr(m, k) for k in ("outer_bags", "inner_bags", "validation_size", "interactions",
                                                  "max_rounds", "early_stopping_rounds", "learning_rate")}
RESULTS["S3_missing"] = {"fit_with_nan_ok": True, "train_rows_with_nan": int(np.isnan(Xtr).any(axis=1).sum()),
                         "proba_finite": bool(np.all(np.isfinite(P)))}
RESULTS["S2_probability"] = {"proba_shape": list(P.shape), "rows_sum_to_1": bool(np.allclose(P.sum(axis=1), 1)),
                             "holdout": score_block(YHO, P[:, 1], BASE), "censored_rows_excluded": SP["holdout_censored"],
                             "term_names": list(m.term_names_)}

# S1 leak trap
mL = ebm(feature_names=namesL).fit(XtrL, YTR)
imp = dict(zip(mL.term_names_, [round(float(v), 4) for v in mL.term_importances()]))
RESULTS["S1_leak_trap"] = {"without_leak": score_block(YHO, P[:, 1], BASE),
                           "with_leak": score_block(YHO, mL.predict_proba(XhoL)[:, 1], BASE),
                           "term_importance_with_leak_top": sorted(imp.items(), key=lambda kv: -kv[1])[:3],
                           "library_has_availability_time_concept": False, "library_refused_leak_column": False}

# S1 internal validation: default is a random split per outer bag; the bags argument can make it time ordered
ob = 8
n = len(tr)
bags = np.ones((n, ob), dtype=np.int8)
cut = int(n * 0.85)
bags[cut:, :] = -1  # last 15% of training (by decision time) is validation in every bag
mt = ebm(outer_bags=ob).fit(Xtr, YTR, bags=bags)
RESULTS["S1_internal_validation"] = {
    "default_validation": "random validation_size=%s per outer bag (rows from any time)" % m.validation_size,
    "time_ordered_bags_fit_ok": True,
    "time_ordered_bags_holdout": score_block(YHO, mt.predict_proba(Xho)[:, 1], BASE),
}

# S4 calibration / uncertainty
RESULTS["S4_calibration"] = {
    "built_in_calibration": False,
    "raw_reliability_3bins": reliability(YHO, P[:, 1], 3),
    "has_term_standard_deviations": hasattr(m, "term_standard_deviations_"),
    "has_bagged_scores": hasattr(m, "bagged_scores_"),
    "note": "term standard deviations describe spread of shape functions across outer bags, not a predictive interval",
}

# small N: first 300 training rows
mS = ebm().fit(Xtr[:300], YTR[:300])
RESULTS["small_n_300"] = {"positives": int(YTR[:300].sum()), "holdout": score_block(YHO, mS.predict_proba(Xho)[:, 1], BASE)}

# S5 persistence: pickle and JSON export (from_json is a private, UNTESTED_ path)
pk = os.path.join(SCRATCH, "ebm.pkl")
with open(pk, "wb") as fh:
    pickle.dump(m, fh)
with open(pk, "rb") as fh:
    m2 = pickle.load(fh)
js = os.path.join(SCRATCH, "ebm.json")
m.to_json(js)
s5 = {"pickle": {"bytes": os.path.getsize(pk), "identical": bool(np.array_equal(m2.predict_proba(Xho), P))},
      "json_export": {"bytes": os.path.getsize(js), "sha256": sha256_file(js)}}
try:
    m3 = ExplainableBoostingClassifier()
    m3._from_json(js)
    pj = m3.predict_proba(Xho)
    s5["json_reload_private"] = {"identical": bool(np.array_equal(pj, P)), "max_abs_diff": float(np.max(np.abs(pj - P)))}
except Exception as e:  # noqa: BLE001
    s5["json_reload_private"] = "%s: %s" % (type(e).__name__, str(e)[:160])
RESULTS["S5_persistence"] = s5

# determinism
m4 = ebm().fit(Xtr, YTR)
RESULTS["determinism"] = {"same_seed_identical_proba": bool(np.array_equal(m4.predict_proba(Xho), P))}

# S6 cost
_, t_pred = timed(lambda: m.predict_proba(Xho))
mf, t_fast = timed(lambda: ebm(outer_bags=4, interactions=0).fit(Xtr, YTR))
RESULTS["S6_cost"] = {"fit_s_defaults_1_job": round(t_fit, 3), "fit_s_outer_bags4_no_interactions": round(t_fast, 3),
                      "batch_predict_per_row_ms": round(1000 * t_pred / len(ho), 5),
                      "single_row_latency": single_row_latency(m.predict_proba, Xho)}
finish()
