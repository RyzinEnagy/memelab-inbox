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

# ---- interpret at the pin: EBM Cox survival objective (time to barrier with censoring) ----
import interpret
from interpret.glassbox import ExplainableBoostingRegressor
from interpret.utils._native import Native

RESULTS["library"] = {"interpret": interpret.__version__, "path": interpret.__file__,
                      "libebm": Native.get_native_singleton()._unsafe.__dict__.get("_name", "unknown")
                      if hasattr(Native.get_native_singleton(), "_unsafe") else "unknown"}
RESULTS["network_attempts_after_import"] = list(NET_ATTEMPTS)
s = D["split"]
tte = D["time_to_event_h"].astype(float)
ev = D["event_observed"].astype(int)
tr_all = np.where(s == "train")[0]
ho_all = np.where(s == "holdout")[0]  # includes the 107 censored-at-cutoff rows: survival keeps them
Xtr, names = matrix(D, tr_all)
Xho, _ = matrix(D, ho_all)
y_tr = tte[tr_all] * (2 * ev[tr_all] - 1)  # encoding documented at _ebm.py:4141: negative = censored time


def harrell_c(time_, event, risk):
    # concordance: among comparable pairs (earlier time had an event), higher risk should fail first
    num = 0.0
    den = 0
    for i in range(len(time_)):
        if not event[i]:
            continue
        later = time_ > time_[i]
        den += int(later.sum())
        num += float((risk[i] > risk[later]).sum()) + 0.5 * float((risk[i] == risk[later]).sum())
    return num / den if den else float("nan"), den


m, t_fit = timed(lambda: ExplainableBoostingRegressor(objective="survival_cox", random_state=7, n_jobs=1,
                                                      feature_names=names).fit(Xtr, y_tr))
risk = m.predict(Xho)
c, pairs = harrell_c(tte[ho_all], ev[ho_all], risk)
rng = np.random.default_rng(0)
null_c = np.array([harrell_c(tte[ho_all], ev[ho_all], rng.permutation(risk))[0] for _ in range(200)])
lab = D["label"][ho_all]
RESULTS["cox_survival"] = {
    "objective": "survival_cox", "fit_s": round(t_fit, 3), "train_rows": len(tr_all), "train_events": int(ev[tr_all].sum()),
    "holdout_rows_incl_censored": len(ho_all), "holdout_events": int(ev[ho_all].sum()),
    "holdout_censored_before_24h": int(((ev[ho_all] == 0) & (tte[ho_all] < 24)).sum()),
    "harrell_c_holdout": round(c, 4), "comparable_pairs": pairs, "harrell_c_permuted_risk_200": {"mean": round(float(null_c.mean()), 4), "p2.5": round(float(np.percentile(null_c, 2.5)), 4), "p97.5": round(float(np.percentile(null_c, 97.5)), 4), "share_ge_observed": round(float((null_c >= c).mean()), 4)},
    "risk_finite": bool(np.all(np.isfinite(risk))),
    "predict_output": "log relative hazard per row (no baseline hazard, so no P(event by 24h) without extra code)",
    "auc_of_risk_vs_label_uncensored_holdout": round(auc(lab[~np.isnan(lab)].astype(int), risk[~np.isnan(lab)]), 4),
}
finish()
