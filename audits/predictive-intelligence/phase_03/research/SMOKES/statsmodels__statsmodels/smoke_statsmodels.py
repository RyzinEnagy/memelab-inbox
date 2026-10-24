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

# ---- statsmodels body ----
import pandas as pd
import statsmodels
import statsmodels.api as sm
from statsmodels.discrete.discrete_model import Logit
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

RESULTS["library"] = {"statsmodels": statsmodels.__version__, "path": statsmodels.__file__}
RESULTS["network_attempts_after_import"] = list(NET_ATTEMPTS)
tr, va, ho = SP["train"], SP["val"], SP["holdout"]
Xtr_raw, names = matrix(D, tr)
Xho_raw, _ = matrix(D, ho)
XtrL_raw, _ = matrix(D, tr, with_leak=True)
XhoL_raw, _ = matrix(D, ho, with_leak=True)


def prep(train, *others):
    med = np.nanmedian(train, axis=0)
    mu = np.nanmean(np.where(np.isnan(train), med, train), axis=0)
    sd = np.nanstd(np.where(np.isnan(train), med, train), axis=0)
    sd[sd == 0] = 1.0
    out = []
    for a in (train,) + others:
        a = np.where(np.isnan(a), med, a)
        out.append(sm.add_constant((a - mu) / sd, has_constant="add"))
    return out


def capture(fn):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            r = fn()
            err = None
        except Exception as e:  # noqa: BLE001
            r, err = None, "%s: %s" % (type(e).__name__, (str(e).splitlines() or [""])[0][:160])
    return r, err, sorted({"%s: %s" % (x.category.__name__, str(x.message)[:120]) for x in w})


# S3 missing covariates
r_none, e_none, w_none = capture(lambda: Logit(YTR, sm.add_constant(Xtr_raw)).fit(disp=0))
r_drop, e_drop, w_drop = capture(lambda: Logit(YTR, sm.add_constant(Xtr_raw), missing="drop").fit(disp=0))
p_drop = r_drop.predict(sm.add_constant(Xho_raw, has_constant="add"))
RESULTS["S3_missing"] = {"default_missing_none": {"error": e_none, "warnings": w_none},
                         "missing_drop": {"error": e_drop, "nobs_used": int(r_drop.nobs), "train_rows": len(tr),
                                          "holdout_predictions_nan": int(np.isnan(p_drop).sum()),
                                          "holdout_rows_with_nan_feature": int(np.isnan(Xho_raw).any(axis=1).sum())},
                         "note": "missing='drop' drops rows at fit; predict on a row with NaN returns NaN probability"}

# S2 Logit and GLM Binomial on train-imputed standardized features
Xtr, Xho = prep(Xtr_raw, Xho_raw)
res, t_fit = timed(lambda: Logit(YTR, Xtr).fit(disp=0))
p_logit = res.predict(Xho)
glm, t_glm = timed(lambda: sm.GLM(YTR, Xtr, family=sm.families.Binomial()).fit())
p_glm = glm.predict(Xho)
RESULTS["S2_probability"] = {"logit_holdout": score_block(YHO, p_logit, BASE), "glm_binomial_holdout": score_block(YHO, p_glm, BASE),
                             "logit_vs_glm_max_abs_diff": float(np.max(np.abs(p_logit - p_glm))),
                             "logit_converged": bool(res.mle_retvals.get("converged")),
                             "coef_names": ["const"] + names, "coef": [round(float(c), 4) for c in res.params],
                             "coef_se": [round(float(c), 4) for c in res.bse],
                             "censored_rows_excluded": SP["holdout_censored"]}

# S1 leak trap and separation
XtrL, XhoL = prep(XtrL_raw, XhoL_raw)
rL, eL, wL = capture(lambda: Logit(YTR, XtrL).fit(disp=0, maxiter=200))
s1 = {"without_leak": score_block(YHO, p_logit, BASE), "with_leak_fit_error": eL, "with_leak_warnings": wL,
      "library_has_availability_time_concept": False, "library_refused_leak_column": False}
if rL is not None:
    s1["with_leak"] = score_block(YHO, rL.predict(XhoL), BASE)
    s1["with_leak_leak_coef"] = round(float(rL.params[-1]), 3)
RESULTS["S1_leak_trap"] = s1
# small-N separation: first 120 training rows
n_small = 120
Xs, Xhs = prep(Xtr_raw[:n_small], Xho_raw)
rs, es, ws = capture(lambda: Logit(YTR[:n_small], Xs).fit(disp=0, maxiter=100))
RESULTS["small_n_120"] = {"positives": int(YTR[:n_small].sum()), "error": es, "warnings": ws,
                          "holdout": score_block(YHO, rs.predict(Xhs), BASE) if rs is not None else None}

# S4 uncertainty: parameter-based CI for the mean probability (GLM get_prediction), Wilson, Holm
sf = glm.get_prediction(Xho).summary_frame(alpha=0.05)
width = (sf["mean_ci_upper"] - sf["mean_ci_lower"]).to_numpy()
order = np.argsort(p_glm, kind="stable")
bins = np.array_split(order, 3)
band = []
for b in bins:
    obs = float(YHO[b].mean())
    band.append({"n": int(len(b)), "mean_p": round(float(p_glm[b].mean()), 4), "obs": round(obs, 4),
                 "mean_ci": [round(float(sf["mean_ci_lower"].to_numpy()[b].mean()), 4),
                             round(float(sf["mean_ci_upper"].to_numpy()[b].mean()), 4)]})


def lab_wilson(k, n, z=1.96):  # verbatim copy of memelab/social/alpha_core.py:125 for comparison
    if n == 0:
        return None
    p = k / n
    dd = 1 + z * z / n
    c = (p + z * z / (2 * n)) / dd
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / dd
    return max(0.0, c - h), min(1.0, c + h)


maxdiff = 0.0
for n in (5, 20, 50, 58, 100, 300):
    for k in range(0, n + 1):
        lo, hi = proportion_confint(k, n, alpha=0.05, method="wilson")
        lo2, hi2 = lab_wilson(k, n)
        maxdiff = max(maxdiff, abs(lo - lo2), abs(hi - hi2))
pv = [0.012, 0.030, 0.041]
rej, padj, _, _ = multipletests(pv, alpha=0.05, method="holm")
manual = []
srt = np.argsort(pv)
running = 0.0
tmp = [0.0] * 3
for rank, i in enumerate(srt):
    running = max(running, min(1.0, (3 - rank) * pv[i]))
    tmp[i] = running
_, holm_err, _ = capture(lambda: multipletests([0.2, 1.3], method="holm"))
RESULTS["S4_uncertainty"] = {
    "glm_mean_ci_width_holdout": {"median": round(float(np.median(width)), 5), "max": round(float(width.max()), 5)},
    "glm_mean_ci_by_tercile": band,
    "note": "mean CI is parameter uncertainty of the fitted probability, not outcome coverage; no calibration or conformal method in the library",
    "wilson_vs_lab_alpha_core_max_abs_diff": maxdiff,
    "holm": {"pvals": pv, "adjusted": [round(float(x), 6) for x in padj], "manual": [round(x, 6) for x in tmp],
             "reject": [bool(x) for x in rej]},
    "holm_out_of_range_pvalue": holm_err,
}

# S5 persistence
pk = os.path.join(SCRATCH, "sm_logit.pickle")
res.save(pk)
r2 = sm.load(pk)
pk2 = os.path.join(SCRATCH, "sm_logit_nodata.pickle")
res.save(pk2, remove_data=True)
r3 = sm.load(pk2)
RESULTS["S5_persistence"] = {"pickle_bytes": os.path.getsize(pk), "pickle_remove_data_bytes": os.path.getsize(pk2),
                             "identical": bool(np.array_equal(p_logit, r2.predict(Xho))),
                             "identical_remove_data": bool(np.array_equal(p_logit, r3.predict(Xho))),
                             "format": "pickle (statsmodels.iolib.smpickle); load executes code"}

# Role-specific: MarkovRegression regime states (N07) on the ret_1h series ordered by decision time
y = D["ret_1h"].astype(float)
n_tr = int(np.searchsorted(D["decision_time"], D["decision_time"][SP["val"]].min()))  # rows before validation
idx_irreg = pd.to_datetime(D["decision_time"].astype("int64"), unit="s")
mr_warn = capture(lambda: MarkovRegression(pd.Series(y, index=idx_irreg), k_regimes=2, switching_variance=True))
full, t_mr = timed(lambda: MarkovRegression(y, k_regimes=2, switching_variance=True).fit(disp=False))
trn = MarkovRegression(y[:n_tr], k_regimes=2, switching_variance=True).fit(disp=False)
mod_full_fixed = MarkovRegression(y, k_regimes=2, switching_variance=True)
filt_fixed = mod_full_fixed.filter(trn.params).filtered_marginal_probabilities
filt_fixed = np.asarray(filt_fixed)
filt_trn = np.asarray(trn.filtered_marginal_probabilities)
filt_full = np.asarray(full.filtered_marginal_probabilities)
smooth_full = np.asarray(full.smoothed_marginal_probabilities)


def col(a, k):
    a = np.asarray(a)
    return a[:, k] if a.ndim == 2 and a.shape[1] in (2,) else a[k]


hi_full = int(np.argmax(full.params[2:4]))  # regime with the larger mean (trend const per regime)
hi_trn = int(np.argmax(trn.params[2:4]))
_, oos_err, _ = capture(lambda: full.predict(start=len(y), end=len(y) + 5))
split = D["split"]
RESULTS["markov_regression"] = {
    "n_obs": len(y), "fit_s": round(t_mr, 3), "param_names": list(full.model.param_names),
    "params_full": [round(float(v), 5) for v in full.params],
    "params_train_only": [round(float(v), 5) for v in trn.params],
    "expected_durations_full": [round(float(v), 2) for v in np.ravel(full.expected_durations)],
    "share_high_mean_regime_filtered_full": {s: round(float((col(filt_full, hi_full)[split == s] > 0.5).mean()), 4)
                                             for s in ("train", "val", "holdout")},
    "truncation_test": {
        "filtered_trainonly_params_vs_same_params_full_series_max_abs_diff_on_train_rows":
            float(np.max(np.abs(col(filt_fixed, hi_trn)[:n_tr] - col(filt_trn, hi_trn)))),
        "filtered_full_sample_params_vs_train_only_fit_max_abs_diff_on_train_rows":
            float(np.max(np.abs(col(filt_full, hi_full)[:n_tr] - col(filt_trn, hi_trn)))),
        "smoothed_full_vs_filtered_full_max_abs_diff":
            float(np.max(np.abs(col(smooth_full, hi_full) - col(filt_full, hi_full)))),
    },
    "out_of_sample_predict": oos_err,
    "irregular_datetime_index_warnings": mr_warn[2],
    "panel_or_many_short_series": "not supported: one endog series per model",
}

# S6 cost
_, t_pred = timed(lambda: res.predict(Xho))
RESULTS["S6_cost"] = {"fit_s": {"logit": round(t_fit, 4), "glm_binomial": round(t_glm, 4), "markov_regression_3000": round(t_mr, 3)},
                      "batch_predict_per_row_ms": round(1000 * t_pred / len(ho), 5),
                      "single_row_latency": single_row_latency(res.predict, Xho)}
finish()
