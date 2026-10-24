"""Phase 03 R4 smoke for NannyML at the pin (run offline, NML_DISABLE_USAGE_LOGGING=1).

Role: drift monitoring plus label-free performance estimation (CBPE) for PENDING labels (P05).
"""
import os
import pickle
import sys
import tempfile
import time
import warnings

sys.path.insert(0, os.environ.get("R4_HARNESS", os.path.dirname(os.path.abspath(__file__))))
import common as C  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

warnings.filterwarnings("ignore")
import nannyml as nml  # noqa: E402

F = C.FEATURES
df = C.load()
df["ts"] = pd.to_datetime(df.decision_time, unit="s")
tr, va, ho = (df[df.split == s].copy() for s in ("train", "val", "holdout"))
trm = C.matured(tr)
prev = float(trm.label.mean())


def alerts_by_period(res_df, cols, method):
    out = {}
    period = res_df[("chunk", "chunk", "period")]
    start = res_df[("chunk", "chunk", "start_date")]
    for c in cols:
        a = res_df[(c, method, "alert")].astype(bool)
        out[c] = {
            "reference_chunks_alerting": int(a[period == "reference"].sum()),
            "analysis_alerts_by_chunk_start": [str(s)[:16] for s in start[(period == "analysis") & a]],
        }
    return out


# ---- Role: univariate drift, reference = train; val and holdout each chunked separately (150 rows, time-ordered) ----
role = {}
for cont, cat in (("kolmogorov_smirnov", "chi2"), ("jensen_shannon", "jensen_shannon"), ("wasserstein", "jensen_shannon")):
    t0 = time.perf_counter()
    calc = nml.UnivariateDriftCalculator(column_names=F, treat_as_categorical=["fatal_flag"], timestamp_column_name="ts",
                                         chunk_size=150, continuous_methods=[cont], categorical_methods=[cat])
    calc.fit(tr)
    rv = calc.calculate(va).to_df()
    rh = calc.calculate(ho).to_df()
    dt = time.perf_counter() - t0
    pv, ph = rv[("chunk", "chunk", "period")], rh[("chunk", "chunk", "period")]
    summ = {"seconds": round(dt, 3), "chunks_reference": int((pv == "reference").sum()),
            "chunks_val": int((pv == "analysis").sum()), "chunks_holdout": int((ph == "analysis").sum()),
            "val_chunk_rows": rv[pv == "analysis"][("chunk", "chunk", "end_index")].sub(rv[pv == "analysis"][("chunk", "chunk", "start_index")]).add(1).tolist(),
            "holdout_chunk_rows": rh[ph == "analysis"][("chunk", "chunk", "end_index")].sub(rh[ph == "analysis"][("chunk", "chunk", "start_index")]).add(1).tolist()}
    fa, det = 0, {}
    for c in F:
        meth = cat if c == "fatal_flag" else cont
        av = rv[(c, meth, "alert")].astype(bool)
        ah = rh[(c, meth, "alert")].astype(bool)
        fa += int(av[pv == "analysis"].sum())
        det[c] = {"val_alerts": int(av[pv == "analysis"].sum()), "holdout_alerts": int(ah[ph == "analysis"].sum()),
                  "reference_alerts": int(av[pv == "reference"].sum())}
    summ["false_alarm_column_chunks_in_val"] = f"{fa} of {int((pv == 'analysis').sum()) * len(F)}"
    summ["per_column"] = det
    role[cont] = summ
    C.emit(f"ROLE_univariate_{cont}", summ)

# ---- Role: multivariate (PCA reconstruction error) ----
t0 = time.perf_counter()
from sklearn.impute import SimpleImputer  # noqa: E402

mv = nml.DataReconstructionDriftCalculator(column_names=F, timestamp_column_name="ts", chunk_size=150,
                                            imputer_continuous=SimpleImputer(strategy="median"))
mv.fit(tr)
mres = {"seconds": None}
for name, part in (("val", va), ("holdout", ho)):
    rm = mv.calculate(part).to_df()
    per = rm[("chunk", "period")] if ("chunk", "period") in rm.columns else rm[("chunk", "chunk", "period")]
    alert_col = [c for c in rm.columns if c[-1] == "alert"][0]
    a = rm[alert_col].astype(bool)
    mres[f"{name}_chunk_alerts"] = int(a[per == "analysis"].sum())
    mres[f"{name}_chunks"] = int((per == "analysis").sum())
    mres["reference_chunk_alerts"] = int(a[per == "reference"].sum())
mres["seconds"] = round(time.perf_counter() - t0, 3)
C.emit("ROLE_multivariate_reconstruction", mres)

# ---- S3: NaN handling in univariate drift ----
calc = nml.UnivariateDriftCalculator(column_names=["liq_usd"], timestamp_column_name="ts", chunk_number=1,
                                     continuous_methods=["kolmogorov_smirnov"])
calc.fit(tr)
v_nan = float(calc.calculate(ho).to_df()[("liq_usd", "kolmogorov_smirnov", "value")].iloc[-1])
calc2 = nml.UnivariateDriftCalculator(column_names=["liq_usd"], timestamp_column_name="ts", chunk_number=1,
                                      continuous_methods=["kolmogorov_smirnov"])
calc2.fit(tr.dropna(subset=["liq_usd"]))
v_drop = float(calc2.calculate(ho.dropna(subset=["liq_usd"])).to_df()[("liq_usd", "kolmogorov_smirnov", "value")].iloc[-1])
C.emit("S3_nan", {"ks_stat_with_nan": round(v_nan, 6), "ks_stat_after_dropna": round(v_drop, 6), "same": abs(v_nan - v_drop) < 1e-12})

# ---- CBPE (P05): estimate performance on rows whose labels are not available ----
model = C.fit_baseline(trm, F)
for part in (va, ho):
    part["proba"] = model.predict_proba(C.log_feats(part, F))[:, 1]
thr = float(np.quantile(C.matured(va).proba, 0.9))  # flag the top decile, so y_pred is not all zeros
for part in (va, ho):
    part["pred"] = (part.proba >= thr).astype(int)
ref_c = C.matured(va)
ref_c["label"] = ref_c.label.astype(int)
metrics = ["roc_auc", "average_precision", "accuracy"]
t0 = time.perf_counter()
est = nml.CBPE(y_pred_proba="proba", y_pred="pred", y_true="label", timestamp_column_name="ts", metrics=metrics,
               chunk_size=150, problem_type="classification_binary")
est.fit(ref_c)
fit_s = time.perf_counter() - t0
blind = ho.drop(columns=["label"])  # every holdout label hidden, as if PENDING
t0 = time.perf_counter()
er = est.estimate(blind).to_df()
est_s = time.perf_counter() - t0
hom = C.matured(ho)
hom["label"] = hom.label.astype(int)
pc = nml.PerformanceCalculator(y_pred_proba="proba", y_pred="pred", y_true="label", timestamp_column_name="ts",
                               metrics=metrics, chunk_size=150, problem_type="classification_binary")
pc.fit(ref_c)
rr = pc.calculate(hom).to_df()
from sklearn.metrics import accuracy_score, average_precision_score, roc_auc_score  # noqa: E402

an = er[er[("chunk", "period")] == "analysis"] if ("chunk", "period") in er.columns else er[er[("chunk", "chunk", "period")] == "analysis"]
cb = {"needs_calibration_decided": bool(est.needs_calibration), "fit_s": round(fit_s, 3), "estimate_s": round(est_s, 3),
      "threshold_top_decile": round(thr, 5), "reference_rows": len(ref_c), "reference_positives": int(ref_c.label.sum())}
chunks = []
for _, row in an.iterrows():
    s, e = int(row[("chunk", "start_index")]), int(row[("chunk", "end_index")])
    sub = blind.sort_values("ts").iloc[s:e + 1]
    lab = ho.set_index("decision_id").loc[sub.decision_id, "label"]
    mat = lab.notna()
    y = lab[mat].astype(int).values
    p = sub.proba.values[mat.values]
    yp = sub.pred.values[mat.values]
    ch = {"rows": len(sub), "matured": int(mat.sum()), "censored_pending": int((~mat).sum()), "positives": int(y.sum())}
    for mname in metrics:
        v = float(row[(mname, "value")])
        se = float(row[(mname, "sampling_error")])
        if mname == "roc_auc":
            real = roc_auc_score(y, p) if 0 < y.sum() < len(y) else None
        elif mname == "average_precision":
            real = average_precision_score(y, p) if y.sum() > 0 else None
        else:
            real = accuracy_score(y, yp) if len(y) else None
        ch[mname] = {"estimated": round(v, 4), "sampling_error": round(se, 4),
                     "realized_on_matured": None if real is None else round(float(real), 4),
                     "inside_3se": None if real is None else bool(abs(real - v) <= 3 * se),
                     "alert": bool(row[(mname, "alert")])}
    chunks.append(ch)
cb["chunks"] = chunks
whole_est = nml.CBPE(y_pred_proba="proba", y_pred="pred", y_true="label", metrics=metrics, chunk_number=1,
                     problem_type="classification_binary").fit(ref_c).estimate(blind).to_df()
wa = whole_est.iloc[-1]
cb["whole_holdout"] = {m: {"estimated": round(float(wa[(m, "value")]), 4)} for m in metrics}
cb["whole_holdout"]["realized_on_matured"] = {
    "roc_auc": round(float(roc_auc_score(hom.label, hom.proba)), 4),
    "average_precision": round(float(average_precision_score(hom.label, hom.proba)), 4),
    "accuracy": round(float(accuracy_score(hom.label, hom.pred)), 4), "n": len(hom), "positives": int(hom.label.sum())}
cens = ho[ho.label.isna()]
ce = nml.CBPE(y_pred_proba="proba", y_pred="pred", y_true="label", metrics=metrics, chunk_number=1,
              problem_type="classification_binary").fit(ref_c).estimate(cens.drop(columns=["label"])).to_df().iloc[-1]
cb["censored_107_rows_estimate"] = {m: round(float(ce[(m, "value")]), 4) for m in metrics}
C.emit("ROLE_cbpe", cb)

# ---- S1: leak trap: realized and CBPE-estimated performance with the trap feature ----
leak_model = C.fit_baseline(trm, F + [C.TRAP])
s1 = {}
for name, mdl, cols in (("legit", model, F), ("with_trap", leak_model, F + [C.TRAP])):
    rv = C.matured(va).copy()
    rv["label"] = rv.label.astype(int)
    rv["proba"] = mdl.predict_proba(C.log_feats(rv, cols))[:, 1]
    rv["pred"] = (rv.proba >= 0.5).astype(int)
    hh = ho.copy()
    hh["proba"] = mdl.predict_proba(C.log_feats(hh, cols))[:, 1]
    hh["pred"] = (hh.proba >= 0.5).astype(int)
    e1 = nml.CBPE(y_pred_proba="proba", y_pred="pred", y_true="label", metrics=["roc_auc"], chunk_number=1,
                  problem_type="classification_binary").fit(rv).estimate(hh.drop(columns=["label"])).to_df().iloc[-1]
    s1[name] = {"cbpe_estimated_roc_auc": round(float(e1[("roc_auc", "value")]), 4),
                "realized": C.scores(C.matured(hh).label, C.matured(hh).proba, prev)}
s1["note"] = "no availability-time or cutoff mechanism in NannyML; the trap column passed through and CBPE reports the inflated score"
C.emit("S1_leak", s1)

# ---- S2: probability validation (P38) ----
s2 = {}
for label, val in (("proba_1_5", 1.5), ("proba_nan", np.nan), ("proba_neg", -0.2)):
    bad = blind.copy().reset_index(drop=True)
    bad.loc[0, "proba"] = val
    try:
        out = est.estimate(bad).to_df()
        an2 = out[out[("chunk", "period")] == "analysis"] if ("chunk", "period") in out.columns else out
        s2[label] = {"raised": False, "roc_auc_first_chunk": float(an2.iloc[0][("roc_auc", "value")])}
    except Exception as ex:  # noqa: BLE001
        s2[label] = {"raised": True, "error": f"{type(ex).__name__}: {str(ex)[:160]}"}
s2["sklearn_scores_holdout_matured"] = C.scores(hom.label, hom.proba, prev)
C.emit("S2_probs", s2)

# ---- S5: persistence (pickle store) ----
from nannyml.io.store import FilesystemStore  # noqa: E402

work = tempfile.mkdtemp(prefix="nml_store_")
store = FilesystemStore(root_path=work)
store.store(est, filename="cbpe.pkl")
loaded = store.load(filename="cbpe.pkl", as_type=nml.CBPE)
a1 = est.estimate(blind).to_df()
a2 = loaded.estimate(blind).to_df()
same = a1.equals(a2)
raw = open(os.path.join(work, "cbpe.pkl"), "rb").read()
C.emit("S5_persist", {"format": "pickle (nannyml.io.store.serializers.PickleSerializer)", "bytes": len(raw),
                      "reloaded_estimates_identical": bool(same), "pickle_opcodes_start": raw[:2].hex()})

# ---- S6: cost ----
C.emit("S6_cost", {"cbpe_fit_s": round(fit_s, 3), "cbpe_estimate_634_rows_s": round(est_s, 3),
                   "per_row_estimate_ms": round(1000 * est_s / len(blind), 3)})
print("DONE")
