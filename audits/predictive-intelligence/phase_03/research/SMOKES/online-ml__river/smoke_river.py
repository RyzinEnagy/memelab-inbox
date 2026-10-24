"""R3 Phase 03 smoke for online-ml/river at pin b674b75 (built from the pinned source with maturin; version string 0.26.1).
Shared synthetic challenge (sha256 checked), processed in decision-time order. Format and behaviour only."""
import os, sys, time, pickle, math, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import r3_common as C
tm = C.Timer()
with tm("import_s"):
    import river
    from river import compose, preprocessing, linear_model, optim, drift, stream, metrics
res = {"env": C.env_info(), "river_version": river.__version__, "river_file": river.__file__}
d = C.load(); M = C.masks(d)
N = len(d["label"])
order = np.argsort(d["decision_time"], kind="stable")
assert np.all(np.diff(d["decision_time"][order]) >= 0)
base = float(np.mean(d["label"][M["train"]]))
split = d["split"]

def xrow(i, with_trap=False, nan_mode="omit"):
    x = {}
    for c in C.FEATURES + (["leak_future_ret"] if with_trap else []):
        v = float(d[c][i])
        if c in ("liq_usd", "vol_24h") and not math.isnan(v):
            v = math.log(v)
        if math.isnan(v):
            if nan_mode == "omit":
                continue
        x[c] = v
    return x

def make_model():
    # compose.Select is not used: it raises KeyError when a selected key is absent (first run of this smoke).
    # Missing values are passed as omitted keys (S3 shows why: NaN values and StatImputer do not work as hoped).
    return preprocessing.StandardScaler() | linear_model.LogisticRegression(optimizer=optim.SGD(0.02))

def run_online(with_trap=False, delayed=True):
    """Question at decision_time; answer at label_matures_at (delayed) or immediately (no delay)."""
    model = make_model()
    def gen():
        for i in order:
            x = xrow(i, with_trap); x["__i"] = int(i)
            yield x, d["label"][i]
    moment = lambda x: d["decision_time"][x["__i"]]
    delay = (lambda x, y: d["label_matures_at"][x["__i"]] - d["decision_time"][x["__i"]]) if delayed else None
    preds = {}; learned = 0; learned_unmatured = 0; skipped_unlabeled = 0
    last_t = d["decision_time"][order[-1]]
    t_learn = 0.0; t_pred = 0.0
    for i, x, y in stream.simulate_qa(gen(), moment if delayed else None, delay):
        idx = x.pop("__i")
        if y is None:
            s = time.perf_counter(); preds[idx] = model.predict_proba_one(x).get(True, 0.0); t_pred += time.perf_counter() - s
        else:
            if isinstance(y, float) and math.isnan(y):
                skipped_unlabeled += 1
                continue
            if delayed and d["label_matures_at"][idx] > last_t:
                learned_unmatured += 1
            s = time.perf_counter(); model.learn_one(x, bool(y)); t_learn += time.perf_counter() - s
            learned += 1
    ho = np.where(M["holdout"])[0]
    p = np.array([preds[i] for i in ho]); y = d["label"][ho]
    rep = C.prob_report(y, p, base)
    rep.update({"learned": learned, "learned_after_data_end_but_unmatured": learned_unmatured,
                "nan_labels_skipped": skipped_unlabeled, "learn_us_per_row": round(1e6 * t_learn / max(learned, 1), 1),
                "predict_us_per_row": round(1e6 * t_pred / len(preds), 1)})
    return model, rep, preds

model, clean, preds = run_online(False, True)
res["S2_S6_online_delayed"] = clean
_, nodelay, _ = run_online(False, False)
res["label_maturity_no_delay"] = {k: nodelay[k] for k in ("brier", "logloss", "auc", "bss_vs_base", "learned")}
_, trap, _ = run_online(True, True)
res["S1_trap"] = {"with_trap": {k: trap[k] for k in ("brier", "logloss", "auc", "bss_vs_base")},
                  "clean": {k: clean[k] for k in ("brier", "logloss", "auc", "bss_vs_base")}, "library_stopped_it": False,
                  "mechanism": "simulate_qa delays labels (moment + delay) but yields every feature at question time; no feature availability"}

# end-of-stream flush: simulate_qa reveals all pending labels after the last question
cnt = 0; total = 0
def g2():
    for i in order:
        yield {"__i": int(i)}, d["label"][i]
last_t = d["decision_time"][order[-1]]
seen_q = 0
for i, x, y in stream.simulate_qa(g2(), lambda x: d["decision_time"][x["__i"]], lambda x, y: 86400):
    if y is None:
        seen_q += 1
    elif seen_q == N:
        total += 1
        if d["label_matures_at"][x["__i"]] > last_t:
            cnt += 1
res["simulate_qa_end_flush"] = {"answers_after_last_question": total, "of_which_not_matured_by_last_moment": cnt,
    "note": "stream/qa.py final loop yields every pending memento; a model trained to the end of the data would learn unmatured labels unless the caller filters them"}

# S3: missing values. River pipelines take dicts; test NaN values, None values with StatImputer, omitted keys.
from river import stats as rstats
tr = np.where(M["train"])[0][:300]
xi = int(np.where(np.isnan(d["liq_usd"]) & M["holdout"])[0][0])
def as_none(x):
    return {k: (None if (isinstance(v, float) and math.isnan(v)) else v) for k, v in x.items()}
def full_keys(x):
    y = dict(x)
    for c in C.FEATURES:
        y.setdefault(c, None)
    return y
out = {}
bare = linear_model.LogisticRegression()
for i in tr:
    bare.learn_one(xrow(i, nan_mode="keep"), bool(d["label"][i]))
out["bare_LR_nan_values"] = {"pred": bare.predict_proba_one(xrow(xi, nan_mode="keep")).get(True),
    "weights_finite_after_learning": bool(all(math.isfinite(w) for w in bare.weights.values()))}
imp = lambda: preprocessing.StatImputer(("liq_usd", rstats.Mean()), ("vol_24h", rstats.Mean()))
for name, conv in {"none_values": lambda x: as_none(full_keys(x)), "nan_values": lambda x: x, "omitted_keys": None}.items():
    m = imp() | preprocessing.StandardScaler() | linear_model.LogisticRegression()
    try:
        for i in tr:
            x = xrow(i, nan_mode="keep") if name != "omitted_keys" else xrow(i, nan_mode="omit")
            m.learn_one(conv(x) if conv else x, bool(d["label"][i]))
        x = xrow(xi, nan_mode="keep") if name != "omitted_keys" else xrow(xi, nan_mode="omit")
        out["StatImputer_" + name] = {"pred": m.predict_proba_one(conv(x) if conv else x).get(True), "raised": None}
    except Exception as e:
        out["StatImputer_" + name] = {"pred": None, "raised": type(e).__name__ + ": " + str(e)[:80]}
m = make_model()
for i in tr:
    m.learn_one(xrow(i, nan_mode="omit"), bool(d["label"][i]))
out["no_imputer_omitted_keys"] = {"pred": m.predict_proba_one(xrow(xi, nan_mode="omit")).get(True)}
try:
    sel = compose.Select(*C.FEATURES); sel.transform_one(xrow(xi, nan_mode="omit")); out["compose_Select_omitted_key"] = "no error"
except Exception as e:
    out["compose_Select_omitted_key"] = type(e).__name__ + ": " + str(e)[:80]
res["S3_nan"] = out

# S4: calibration in the large and bins (no calibrator offered for classifiers)
ho = np.where(M["holdout"])[0]; p = np.array([preds[i] for i in ho]); y = d["label"][ho]
n = len(y); k = y.sum(); z = 1.96; ph = k / n
den = 1 + z * z / n; ctr = (ph + z * z / (2 * n)) / den; half = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
res["S4_calibration"] = {"mean_pred": float(p.mean()), "observed": float(ph), "wilson95": [float(ctr - half), float(ctr + half)],
    "inside": bool(ctr - half <= p.mean() <= ctr + half),
    "library_tools": "no classifier calibrator; conf.RegressionJackknife gives regression intervals only; metrics include LogLoss, ROCAUC"}

# Drift detectors on feature streams in time order: false alarms in train and val, detection in holdout
def run_detector(det_factory, values, idx_split):
    det = det_factory(); out = {"train": 0, "val": 0, "embargo": 0, "holdout": 0}; first_ho = None; pos_ho = 0
    for v, sp in zip(values, idx_split):
        if sp == "holdout":
            pos_ho += 1
        det.update(v)
        if det.drift_detected:
            out[sp] += 1
            if sp == "holdout" and first_ho is None:
                first_ho = pos_ho
    out["rows_into_holdout_before_first_detection"] = first_ho
    return out
streams = {}
for c in ("liq_usd", "ret_1h"):
    vals = d[c][order]; sps = split[order]
    keep = ~np.isnan(vals)
    v = np.log(vals[keep]) if c == "liq_usd" else vals[keep]
    streams[c] = (v.tolist(), sps[keep].tolist())
dets = {"ADWIN": lambda: drift.ADWIN(), "PageHinkley": lambda: drift.PageHinkley(), "KSWIN": lambda: drift.KSWIN(seed=42)}
res["drift_feature_streams"] = {}
s = time.perf_counter(); nupd = 0
for c, (v, sp) in streams.items():
    res["drift_feature_streams"][c] = {"n": len(v), "holdout_n": sp.count("holdout")}
    for name, f in dets.items():
        res["drift_feature_streams"][c][name] = run_detector(f, v, sp); nupd += len(v)
res["drift_update_us"] = round(1e6 * (time.perf_counter() - s) / nupd, 2)
# Control: same detectors on a stream with the holdout shift removed (holdout rows replaced by a shuffled train sample)
rng = np.random.default_rng(7)
ctrl = {}
for c, (v, sp) in streams.items():
    v = np.array(v); spa = np.array(sp)
    tr_vals = v[spa == "train"]
    v2 = v.copy(); v2[spa == "holdout"] = rng.choice(tr_vals, size=(spa == "holdout").sum(), replace=True)
    ctrl[c] = {name: run_detector(f, v2.tolist(), sp) for name, f in dets.items()}
res["drift_control_no_shift"] = ctrl
# Error stream monitor: ADWIN on the per-row squared error of the online model, in time order
err = [(preds[i] - d["label"][i]) ** 2 for i in order if not math.isnan(d["label"][i])]
sp_err = [split[i] for i in order if not math.isnan(d["label"][i])]
res["drift_error_stream_ADWIN"] = run_detector(lambda: drift.ADWIN(), err, sp_err)

# S5: persistence
blob = pickle.dumps(model); m2 = pickle.loads(blob)
xs = [xrow(i) for i in ho[:50]]
same = all(model.predict_proba_one(x) == m2.predict_proba_one(x) for x in xs)
a = drift.ADWIN()
for v in streams["liq_usd"][0][:500]:
    a.update(v)
a2 = pickle.loads(pickle.dumps(a)); a.update(12.0); a2.update(12.0)
res["S5_persistence"] = {"format": "pickle (Rust-backed objects implement __getstate__)", "pipeline_bytes": len(blob),
    "pipeline_identical": bool(same), "adwin_roundtrip_same_state": bool(a.width == a2.width and a.estimation == a2.estimation)}
res["S6_timings"] = dict(tm.t)
C.dump(res, os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoke_river.result.json"))
