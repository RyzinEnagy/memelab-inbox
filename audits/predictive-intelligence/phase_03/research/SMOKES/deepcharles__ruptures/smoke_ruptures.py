"""R3 Phase 03 smoke for deepcharles/ruptures at pin ee1c8ff (built from the pinned source).
Synthetic seeded OHLCV-like paths (r3_common.seeded_paths, seed 20261026). Format and behaviour only."""
import os, sys, pickle, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import r3_common as C
import ruptures as rpt
from ruptures.metrics import precision_recall

res = {"env": C.env_info(), "ruptures_version": rpt.__version__, "ruptures_file": rpt.__file__}
paths = C.seeded_paths()
res["paths"] = {"n": len(paths), "len_min": int(min(len(p["t"]) for p in paths)),
                "len_max": int(max(len(p["t"]) for p in paths)),
                "with_true_change": int(sum(1 for p in paths if p["cps"]))}

def logret(p):
    return np.diff(np.log(p["close"]))

def pelt_bkps(sig, pen):
    algo = rpt.Pelt(model="normal", min_size=4, jump=1).fit(sig)
    return algo.predict(pen=pen)

# R1 role: change-point recovery on returns (index space of returns = candle index - 1)
t0 = time.perf_counter()
P = R = 0.0; npos = 0; fp_paths = 0; nochange = 0; fit_times = []
for p in paths:
    sig = logret(p)
    n = len(sig)
    pen = 3 * np.log(n)
    s = time.perf_counter(); bk = pelt_bkps(sig, pen); fit_times.append(time.perf_counter() - s)
    true = [c - 1 for c in p["cps"] if 1 <= c - 1 < n] + [n]
    if len(true) > 1:
        pr, rc = precision_recall(true, bk, margin=3)
        P += pr; R += rc; npos += 1
    else:
        nochange += 1
        if len(bk) > 1:
            fp_paths += 1
res["R1_change_points"] = {"detector": "Pelt(model=normal, min_size=4, jump=1), pen=3*log(n), log returns",
    "paths_with_true_change": npos, "mean_precision_margin3": round(P / npos, 3), "mean_recall_margin3": round(R / npos, 3),
    "paths_without_change": nochange, "false_alarm_paths": fp_paths,
    "fit_predict_s_median": round(float(np.median(fit_times)), 5), "fit_predict_s_p95": round(float(np.percentile(fit_times, 95)), 5),
    "fit_predict_s_max": round(float(np.max(fit_times)), 5), "total_s": round(time.perf_counter() - t0, 3)}

# S1: truncation invariance. Decision index d = 60% of the path. Causal = fit on sig[:d]; full = fit on full sig, keep bkps < d.
diff_sets = 0; diff_feature = 0; tested = 0
examples = []
for p in paths:
    sig = logret(p); n = len(sig)
    if n < 60:
        continue
    d = int(0.6 * n)
    pen = 3 * np.log(n)
    causal = [b for b in pelt_bkps(sig[:d], pen) if b < d]
    full = [b for b in pelt_bkps(sig, pen) if b < d]
    tested += 1
    if causal != full:
        diff_sets += 1
        if len(examples) < 3:
            examples.append({"mint": p["mint"], "n": n, "d": d, "causal_bkps_before_d": causal, "full_series_bkps_before_d": full})
    since_c = d - (causal[-1] if causal else 0)
    since_f = d - (full[-1] if full else 0)
    if since_c != since_f:
        diff_feature += 1
res["S1_truncation"] = {"paths_tested": tested, "bkps_before_decision_differ": diff_sets,
    "feature_candles_since_last_break_differs": diff_feature, "examples": examples,
    "library_as_of_mechanism": "none: fit() takes the whole array; Window score at k reads signal[k-width//2:k+width//2] (future half-window)"}

# Window detector look-ahead in practice: score at k uses future samples; changing only samples after k changes score[k].
sig = logret(paths[0]); w = 20
a = rpt.Window(width=w, model="l2").fit(sig)
k_idx = len(a.inds) // 2; k = int(a.inds[k_idx])
sig2 = sig.copy(); sig2[k + 1:] += 0.5
b = rpt.Window(width=w, model="l2").fit(sig2)
res["S1_window_future_dependence"] = {"k": k, "score_k_original": float(a.score[k_idx]), "score_k_after_editing_only_future": float(b.score[k_idx]),
    "changed": bool(abs(a.score[k_idx] - b.score[k_idx]) > 1e-12)}

# Irregular timestamps: ruptures sees only the index; omitted intervals vanish
p = max(paths, key=lambda q: q["n_dense"] - len(q["t"]))
gaps = np.diff(p["t"]) // 300
res["irregular_time"] = {"mint": p["mint"], "dense_len": p["n_dense"], "kept_len": len(p["t"]), "max_gap_candles": int(gaps.max()),
    "note": "fit(signal) has no time argument; a gap of k missing candles is one step to the detector"}

# S3: NaN handling
sig = logret(paths[1]).copy(); sig[10] = np.nan
out = {}
for name, fn in {"Pelt_l2": lambda s: rpt.Pelt(model="l2").fit(s).predict(pen=5),
                 "Pelt_normal": lambda s: rpt.Pelt(model="normal").fit(s).predict(pen=5),
                 "KernelCPD_rbf": lambda s: rpt.KernelCPD(kernel="rbf").fit(s).predict(pen=5),
                 "L1Potts": lambda s: rpt.L1Potts().fit(s).predict(pen=5)}.items():
    try:
        out[name] = {"result": fn(sig), "raised": None}
    except Exception as e:
        out[name] = {"result": None, "raised": type(e).__name__ + ": " + str(e)[:160]}
res["S3_nan"] = out

# S5: persistence (pickle of fitted estimator)
sig = logret(paths[2])
algo = rpt.Pelt(model="normal", min_size=4, jump=1).fit(sig)
bk1 = algo.predict(pen=3 * np.log(len(sig)))
blob = pickle.dumps(algo)
algo2 = pickle.loads(blob)
bk2 = algo2.predict(pen=3 * np.log(len(sig)))
res["S5_persistence"] = {"format": "pickle (no native format; results are plain int lists)", "bytes": len(blob), "identical": bk1 == bk2}

# S6: cost of causal use = refit at every decision. Expanding refits over one 288-candle path, and KernelCPD (C) comparison.
long = max(paths, key=lambda q: len(q["t"]))
sig = logret(long)
s = time.perf_counter(); n_fits = 0
for d in range(24, len(sig) + 1, 12):
    pelt_bkps(sig[:d], 3 * np.log(d)); n_fits += 1
pelt_exp = time.perf_counter() - s
s = time.perf_counter()
for d in range(24, len(sig) + 1, 12):
    rpt.KernelCPD(kernel="rbf", min_size=4).fit(sig[:d].reshape(-1, 1)).predict(pen=3 * np.log(d))
kcpd_exp = time.perf_counter() - s
res["S6_cost"] = {"path_len": len(sig), "expanding_refits": n_fits, "pelt_normal_total_s": round(pelt_exp, 4),
    "pelt_normal_per_refit_ms": round(1000 * pelt_exp / n_fits, 2), "kernelcpd_rbf_total_s": round(kcpd_exp, 4),
    "kernelcpd_per_refit_ms": round(1000 * kcpd_exp / n_fits, 2)}
res["S2"] = "SKIPPED: no probability output (segmentation only)"
res["S4"] = "SKIPPED: no calibration or uncertainty API (penalty is a hard threshold)"
C.dump(res, os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoke_ruptures.result.json"))
