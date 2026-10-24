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

# ---- TabPFN body (network guard active: only cached v2 weights can be used) ----
import pickle

import torch

torch.set_num_threads(2)
t_imp0 = time.perf_counter()
import tabpfn  # noqa: E402
from tabpfn import TabPFNClassifier  # noqa: E402
from tabpfn.constants import ModelVersion  # noqa: E402

RESULTS["library"] = {"tabpfn": getattr(tabpfn, "__version__", "n/a"), "path": tabpfn.__file__, "torch": torch.__version__,
                      "import_s": round(time.perf_counter() - t_imp0, 3),
                      "env": {k: os.environ.get(k) for k in ("TABPFN_MODEL_CACHE_DIR", "TABPFN_NO_BROWSER")}}
RESULTS["network_attempts_after_import"] = list(NET_ATTEMPTS)
tr, va, ho = SP["train"], SP["val"], SP["holdout"]
Xtr, names = matrix(D, tr)
Xho, _ = matrix(D, ho)
XtrL, _ = matrix(D, tr, with_leak=True)
XhoL, _ = matrix(D, ho, with_leak=True)


def progress(msg):
    print("PROGRESS %s %s" % (time.strftime("%H:%M:%S", time.gmtime()), msg), flush=True)


SUB = slice(0, 100)  # holdout subset for determinism and persistence checks (CPU cost)


def err(e):
    return "%s: %s" % (type(e).__name__, " | ".join(str(e).splitlines()[:3])[:300])


# default constructor (TabPFN-3.5, gated by a client-side license check) with network blocked
n0 = len(NET_ATTEMPTS)
try:
    TabPFNClassifier(device="cpu").fit(Xtr[:200], YTR[:200])
    RESULTS["default_v3_5_offline"] = "fit succeeded"
except Exception as e:  # noqa: BLE001
    RESULTS["default_v3_5_offline"] = err(e)
RESULTS["default_v3_5_network_attempts"] = NET_ATTEMPTS[n0:]


def v2(**kw):
    p = dict(device="cpu", random_state=7)
    p.update(kw)
    return TabPFNClassifier.create_default_for_version(ModelVersion.V2, **p)


# CPU size guard: more than 1000 training rows raises unless ignore_pretraining_limits
try:
    v2().fit(Xtr, YTR)
    RESULTS["cpu_size_guard_1746_rows"] = "no error"
except Exception as e:  # noqa: BLE001
    RESULTS["cpu_size_guard_1746_rows"] = err(e)

progress("S2")
# S2 + S3 with v2 weights (cached), full training window
m, t_fit = timed(lambda: v2(ignore_pretraining_limits=True).fit(Xtr, YTR))
P, t_pred = timed(lambda: m.predict_proba(Xho))
RESULTS["S3_missing"] = {"fit_with_nan_ok": True, "train_rows_with_nan": int(np.isnan(Xtr).any(axis=1).sum()),
                         "proba_finite": bool(np.all(np.isfinite(P)))}
RESULTS["S2_probability"] = {"proba_shape": list(P.shape), "rows_sum_to_1": bool(np.allclose(P.sum(axis=1), 1, atol=1e-5)),
                             "holdout": score_block(YHO, P[:, 1], BASE), "censored_rows_excluded": SP["holdout_censored"],
                             "n_estimators_resolved": getattr(m, "n_estimators_", None),
                             "softmax_temperature_resolved": getattr(m, "softmax_temperature_", None)}
RESULTS["network_attempts_after_v2_fit_predict"] = list(NET_ATTEMPTS)

progress("small N")
# small N (inside the CPU guard, about the lab's event counts)
mS = v2().fit(Xtr[:300], YTR[:300])
RESULTS["small_n_300"] = {"positives": int(YTR[:300].sum()), "holdout": score_block(YHO, mS.predict_proba(Xho)[:, 1], BASE)}

progress("S1")
# S1 leak trap
mL = v2(ignore_pretraining_limits=True).fit(XtrL, YTR)
RESULTS["S1_leak_trap"] = {"without_leak": score_block(YHO, P[:, 1], BASE),
                           "with_leak": score_block(YHO, mL.predict_proba(XhoL)[:, 1], BASE),
                           "library_has_availability_time_concept": False, "library_refused_leak_column": False}

# S4 calibration options
progress("S4")
mB = v2(ignore_pretraining_limits=True, balance_probabilities=True).fit(Xtr, YTR)
RESULTS["S4_calibration"] = {"built_in_post_hoc_calibration": False,
                             "raw_reliability_3bins": reliability(YHO, P[:, 1], 3),
                             "balance_probabilities_true": score_block(YHO, mB.predict_proba(Xho)[:, 1], BASE),
                             "softmax_temperature_option": "exists (default resolved from checkpoint); not re-run for CPU cost"}

# determinism
progress("determinism")
m2 = v2(ignore_pretraining_limits=True).fit(Xtr, YTR)
p2 = m2.predict_proba(Xho[SUB])
RESULTS["determinism"] = {"holdout_rows_checked": 100, "same_seed_identical_proba": bool(np.array_equal(p2, P[SUB])),
                          "max_abs_diff": float(np.max(np.abs(p2 - P[SUB])))}

progress("S5")
# S5 persistence
fsp = os.path.join(SCRATCH, "tabpfn_fit_state.tabpfn_fit")
s5 = {}
try:
    m.save_fit_state(fsp)
    m3 = TabPFNClassifier.load_from_fit_state(fsp, device="cpu")
    p3 = m3.predict_proba(Xho[SUB])
    s5["save_fit_state"] = {"bytes": os.path.getsize(fsp), "holdout_rows_checked": 100,
                            "identical": bool(np.array_equal(p3, P[SUB])), "max_abs_diff": float(np.max(np.abs(p3 - P[SUB])))}
except Exception as e:  # noqa: BLE001
    s5["save_fit_state"] = err(e)
pk = os.path.join(SCRATCH, "tabpfn.pkl")
try:
    with open(pk, "wb") as fh:
        pickle.dump(m, fh)
    with open(pk, "rb") as fh:
        m4 = pickle.load(fh)
    s5["pickle"] = {"bytes": os.path.getsize(pk), "identical": bool(np.array_equal(m4.predict_proba(Xho[SUB]), P[SUB]))}
except Exception as e:  # noqa: BLE001
    s5["pickle"] = err(e)
RESULTS["S5_persistence"] = s5

# S6 cost (single-row latency re-runs the network over the training context)
progress("S6")
lat = single_row_latency(m.predict_proba, Xho, reps=5)
mc = v2(ignore_pretraining_limits=True, fit_mode="fit_with_cache").fit(Xtr, YTR)
lat_c = single_row_latency(mc.predict_proba, Xho, reps=5)
RESULTS["S6_cost"] = {"fit_s_1746_rows": round(t_fit, 3), "predict_s_527_rows": round(t_pred, 3),
                      "batch_predict_per_row_ms": round(1000 * t_pred / len(ho), 3),
                      "single_row_latency_fit_preprocessors": lat, "single_row_latency_fit_with_cache": lat_c,
                      "torch_threads": torch.get_num_threads()}
finish()
