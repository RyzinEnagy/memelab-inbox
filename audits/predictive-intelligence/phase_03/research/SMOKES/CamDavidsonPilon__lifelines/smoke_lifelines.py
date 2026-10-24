"""R3 Phase 03 smoke for CamDavidsonPilon/lifelines at pin 7a8fc34 (installed from the pinned source, version string 0.30.3).
Shared synthetic challenge (challenge.csv, sha256 checked) and the R3 competing-risk variant (r3_survival, seed 20261025).
Format and behaviour only."""
import os, sys, time, pickle, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import r3_common as C
import r3_survival as R
tm = C.Timer()
with tm("import_s"):
    import matplotlib
    matplotlib.use("Agg")
    import pandas as pd
    import lifelines
    from lifelines import CoxPHFitter, WeibullAFTFitter, AalenJohansenFitter, KaplanMeierFitter
    from lifelines.utils import concordance_index
    from lifelines.calibration import survival_probability_calibration
warnings.filterwarnings("ignore")
res = {"env": C.env_info(), "lifelines_version": lifelines.__version__, "lifelines_file": lifelines.__file__}
d = C.load(); M = C.masks(d)
T_H = 23.99  # just inside the 24 h horizon; challenge negatives are censored at exactly 24.0
base = float(np.mean(d["label"][M["train"]]))
res["counts"] = {k: int(v.sum()) for k, v in M.items()}
res["train_prevalence"] = base

def frame(mask, with_trap=False, impute=None):
    X, cols = C.design(d, mask, with_trap=with_trap)
    if impute is not None:
        X = np.where(np.isnan(X), impute, X)
    df = pd.DataFrame(X, columns=cols)
    df["T"] = d["time_to_event_h"][mask]; df["E"] = d["event_observed"][mask].astype(int)
    return df

# S3: NaN covariates
try:
    CoxPHFitter().fit(frame(M["train"]), "T", "E"); s3 = "no error"
except Exception as e:
    s3 = type(e).__name__ + ": " + str(e)[:140]
res["S3_nan"] = {"coxph_fit_with_nan": s3, "handling": "required imputation; R3 wrapper imputes train medians"}

def run(with_trap):
    Xtr, cols = C.design(d, M["train"], with_trap=with_trap)
    med = np.nanmedian(Xtr, axis=0)
    dtr = frame(M["train"], with_trap, med)
    dho = frame(M["holdout_all"], with_trap, med)
    out = {"features": cols}
    cph = CoxPHFitter(penalizer=0.01)
    s = time.perf_counter(); cph.fit(dtr, "T", "E"); out["fit_s"] = round(time.perf_counter() - s, 4)
    s = time.perf_counter(); sf = cph.predict_survival_function(dho, times=[T_H]).T.squeeze().to_numpy()
    out["predict_ms_per_row"] = round(1000 * (time.perf_counter() - s) / len(dho), 4)
    p24 = 1 - sf
    lab_in_ho = ~np.isnan(d["label"][M["holdout_all"]])
    y = d["label"][M["holdout_all"]][lab_in_ho]
    out["binary_24h_on_labeled_holdout"] = C.prob_report(y, p24[lab_in_ho], base)
    Tho = dho["T"].to_numpy(); Eho = dho["E"].to_numpy()
    out["concordance_holdout_all_incl_censored"] = float(concordance_index(Tho, sf, Eho))
    grid = np.arange(1.0, 23.0 + 1e-9, 1.0)
    S_grid = cph.predict_survival_function(dho, times=grid).T.to_numpy()
    bs = [C.ipcw_brier_at(t, Tho, Eho, S_grid[:, j], Tho, Eho) for j, t in enumerate(grid)]
    out["ipcw_ibs_1_23h"] = float(np.trapezoid(bs, grid) / (grid[-1] - grid[0]))
    km = KaplanMeierFitter().fit(dtr["T"], dtr["E"])
    S_km = km.survival_function_at_times(grid).to_numpy()
    bs_km = [C.ipcw_brier_at(t, Tho, Eho, np.full(len(Tho), S_km[j]), Tho, Eho) for j, t in enumerate(grid)]
    out["ipcw_ibs_km_baseline"] = float(np.trapezoid(bs_km, grid) / (grid[-1] - grid[0]))
    return cph, dho, out

cph, dho, clean = run(False)
cph_t, dho_t, trap = run(True)
res["S2_S6_clean"] = clean
res["S1_trap"] = {"with_trap": {k: trap[k] for k in ("concordance_holdout_all_incl_censored", "ipcw_ibs_1_23h")},
                   "with_trap_binary_brier": trap["binary_24h_on_labeled_holdout"]["brier"],
                   "with_trap_binary_auc": trap["binary_24h_on_labeled_holdout"]["auc"],
                   "clean_concordance": clean["concordance_holdout_all_incl_censored"], "clean_ibs": clean["ipcw_ibs_1_23h"],
                   "clean_binary_brier": clean["binary_24h_on_labeled_holdout"]["brier"],
                   "library_stopped_it": False,
                   "library_mechanism": "none; k_fold_cross_validation permutes rows at random (utils/__init__.py:764), not by time"}

# S4: calibration tools
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
s = time.perf_counter()
ax, ici, e50 = survival_probability_calibration(cph, dho, t0=T_H, ax=ax)
plt.close(fig)
lab_in_ho = ~np.isnan(d["label"][M["holdout_all"]])
p24 = 1 - cph.predict_survival_function(dho, times=[T_H]).T.squeeze().to_numpy()
yv = d["label"][M["holdout_all"]][lab_in_ho]
n = len(yv); k = yv.sum(); z = 1.96; ph = k / n
den = 1 + z * z / n; ctr = (ph + z * z / (2 * n)) / den; half = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
res["S4_calibration"] = {"survival_probability_calibration_ICI": float(ici), "E50": float(e50), "seconds": round(time.perf_counter() - s, 3),
    "calibration_in_the_large_mean_pred": float(np.mean(p24[lab_in_ho])), "observed_rate": float(ph),
    "wilson95": [float(ctr - half), float(ctr + half)],
    "mean_pred_inside_wilson": bool(ctr - half <= np.mean(p24[lab_in_ho]) <= ctr + half),
    "recalibration_api": "none (no isotonic/Platt/conformal); confidence intervals on coefficients and on univariate curves only"}

# Role: competing risks with Aalen-Johansen (marginal, no covariates)
ev, dur = R.competing_variant(d)
s = time.perf_counter()
aj = AalenJohansenFitter(seed=0, calculate_variance=True).fit(dur[M["train"]], ev[M["train"]], event_of_interest=1)
aj_fit_s = time.perf_counter() - s
cif = aj.cumulative_density_
cif_24 = float(cif[cif.index <= T_H].iloc[-1, 0])
aj2 = AalenJohansenFitter(seed=0).fit(dur[M["train"]], ev[M["train"]], event_of_interest=2)
cif2 = aj2.cumulative_density_; cif2_24 = float(cif2[cif2.index <= T_H].iloc[-1, 0])
yv_lab = d["label"][M["holdout"]]
res["role_competing_AJ"] = {"train_events": np.bincount(ev[M["train"]]).tolist(), "fit_s": round(aj_fit_s, 4),
    "cif_target_first_24h_train": cif_24, "cif_invalidation_first_24h_train": cif2_24, "train_prevalence_binary": base,
    "brier_holdout_if_used_as_constant": C.brier(yv_lab, np.full(len(yv_lab), cif_24)),
    "covariate_competing_risk_model": "none at pin (no Fine-Gray or cause-specific CIF regression found by grep)",
    "jitter_note": "ties are jittered with np.random.seed(seed) on the global RNG (aalen_johansen_fitter.py:171-182)"}

# S5: persistence
blob = pickle.dumps(cph)
cph2 = pickle.loads(blob)
a = cph.predict_survival_function(dho, times=[T_H]).to_numpy(); b = cph2.predict_survival_function(dho, times=[T_H]).to_numpy()
res["S5_persistence"] = {"format": "pickle (no native text/ONNX format)", "bytes": len(blob), "identical": bool(np.array_equal(a, b))}

# WeibullAFT for comparison (parametric)
Xtr, cols = C.design(d, M["train"]); med = np.nanmedian(Xtr, axis=0)
dtr = frame(M["train"], False, med)
s = time.perf_counter(); waft = WeibullAFTFitter(penalizer=0.01).fit(dtr, "T", "E"); waft_s = time.perf_counter() - s
sfw = waft.predict_survival_function(dho, times=[T_H]).T.squeeze().to_numpy()
res["weibull_aft"] = {"fit_s": round(waft_s, 4), "binary_24h": C.prob_report(d["label"][M["holdout_all"]][lab_in_ho], (1 - sfw)[lab_in_ho], base),
    "concordance": float(concordance_index(dho["T"], sfw, dho["E"]))}
res["S6_timings"] = dict(tm.t)
C.dump(res, os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoke_lifelines.result.json"))
