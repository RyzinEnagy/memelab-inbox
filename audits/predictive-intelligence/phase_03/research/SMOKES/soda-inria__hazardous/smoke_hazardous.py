"""R3 Phase 03 smoke for soda-inria/hazardous at pin 1504934 (installed from the pinned source, version 0.2.0).
Shared synthetic challenge (sha256 checked) and the R3 competing-risk variant (r3_survival, seed 20261025):
event 1 = target first, event 2 = invalidation first, 0 = censored. Format and behaviour only."""
import os, sys, time, pickle, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import r3_common as C
import r3_survival as R
tm = C.Timer()
with tm("import_s"):
    import hazardous
    from hazardous import SurvivalBoost
    from hazardous.metrics import (integrated_brier_score_incidence, concordance_index_incidence,
                                   aj_calibration_per_event, brier_score_incidence)
    from hazardous.metrics._km_calibration import recalibrate_survival_function
    from lifelines import AalenJohansenFitter
warnings.filterwarnings("ignore")
res = {"env": C.env_info(), "hazardous_version": hazardous.__version__, "hazardous_file": hazardous.__file__}
d = C.load(); M = C.masks(d)
ev, dur = R.competing_variant(d)
T_H = 23.99
base = float(np.mean(d["label"][M["train"]]))
grid = np.arange(1.0, 23.0 + 1e-9, 1.0)

import pandas as pd
def Y(mask):
    # DataFrame: concordance_index_incidence rejects the dict form that SurvivalBoost.fit accepts
    return pd.DataFrame({"event": ev[mask], "duration": dur[mask]})

def aj_baseline(mask, k):
    aj = AalenJohansenFitter(seed=0, calculate_variance=False).fit(dur[mask], ev[mask], event_of_interest=k)
    cd = aj.cumulative_density_
    return np.array([float(cd[cd.index <= t].iloc[-1, 0]) if (cd.index <= t).any() else 0.0 for t in grid])

def fit_eval(with_trap, random_state=0, n_iter=100):
    Xtr, cols = C.design(d, M["train"], with_trap=with_trap)
    Xho, _ = C.design(d, M["holdout_all"], with_trap=with_trap)
    model = SurvivalBoost(n_iter=n_iter, show_progressbar=False, random_state=random_state)
    s = time.perf_counter(); model.fit(Xtr, Y(M["train"])); fit_s = time.perf_counter() - s
    s = time.perf_counter(); cif = model.predict_cumulative_incidence(Xho, times=grid); pred_grid_s = time.perf_counter() - s
    s = time.perf_counter(); p = model.predict_proba(Xho, time_horizon=T_H); pred_one_s = time.perf_counter() - s
    out = {"features": cols, "fit_s": round(fit_s, 3), "predict_grid_ms_per_row": round(1000 * pred_grid_s / len(Xho), 4),
           "predict_one_horizon_ms_per_row": round(1000 * pred_one_s / len(Xho), 4), "proba_shape": list(p.shape),
           "rows_sum_to_1": bool(np.allclose(p.sum(axis=1), 1.0))}
    lab = ~np.isnan(d["label"][M["holdout_all"]])
    y = d["label"][M["holdout_all"]][lab]
    out["binary_target_first_24h"] = C.prob_report(y, p[lab, 1], base)
    for k in (1, 2):
        out[f"ibs_event{k}"] = float(integrated_brier_score_incidence(Y(M["train"]), Y(M["holdout_all"]), cif[:, k, :], grid, event_of_interest=k))
    out["cindex_event1"] = [float(x) for x in np.atleast_1d(concordance_index_incidence(Y(M["holdout_all"]), cif[:, 1, :], y_train=Y(M["train"]), time_grid=grid, taus=[12.0, 23.0], event_of_interest=1))]
    dec = np.diff(cif[:, 1, :], axis=1) < -1e-9
    out["cif1_non_monotone_rows"] = int(np.any(dec, axis=1).sum())
    out["cif1_largest_decrease"] = float(-np.min(np.diff(cif[:, 1, :], axis=1)))
    return model, cif, p, out

model, cif, p, clean = fit_eval(False)
res["S2_S3_S6_clean"] = clean
res["S3_nan"] = {"fit_with_nan": "no error: check_array(ensure_all_finite='allow-nan') at _survival_boost.py fit, HistGradientBoosting handles NaN",
                 "nan_in_train_X": int(np.isnan(C.design(d, M["train"])[0]).sum())}
for k in (1, 2):
    bl = aj_baseline(M["train"], k)
    nho = int(M["holdout_all"].sum())
    res[f"aj_baseline_ibs_event{k}"] = float(integrated_brier_score_incidence(Y(M["train"]), Y(M["holdout_all"]), np.tile(bl, (nho, 1)), grid, event_of_interest=k))
_, _, _, trap = fit_eval(True)
res["S1_trap"] = {"with_trap": {k: trap[k] for k in ("ibs_event1", "ibs_event2", "cindex_event1")},
                  "with_trap_binary_brier": trap["binary_target_first_24h"]["brier"], "with_trap_auc": trap["binary_target_first_24h"]["auc"],
                  "clean": {k: clean[k] for k in ("ibs_event1", "ibs_event2", "cindex_event1")},
                  "clean_binary_brier": clean["binary_target_first_24h"]["brier"], "library_stopped_it": False,
                  "library_mechanism": "none: no time-aware splitter or availability field; scikit-learn API so any sklearn splitter can be used"}

# S4: calibration
lab = ~np.isnan(d["label"][M["holdout_all"]]); y = d["label"][M["holdout_all"]][lab]
n = len(y); kk = y.sum(); z = 1.96; ph = kk / n
den = 1 + z * z / n; ctr = (ph + z * z / (2 * n)) / den; half = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
ajc = aj_calibration_per_event(Y(M["holdout_all"]), grid, cif)
Xva, _ = C.design(d, M["val"]); Xho, _ = C.design(d, M["holdout_all"])
try:
    S_rec = recalibrate_survival_function(Xva, Y(M["val"]), grid, estimator=model, X=Xho)
    rec = {"min": float(np.min(S_rec)), "max": float(np.max(S_rec)), "outside_0_1": int(np.sum((S_rec < 0) | (S_rec > 1)))}
except Exception as e:
    rec = {"raised": type(e).__name__ + ": " + str(e)[:160]}
res["S4_calibration"] = {"aj_calibration_per_event_holdout": np.asarray(ajc).tolist() if not isinstance(ajc, dict) else {str(k): float(v) for k, v in ajc.items()},
    "in_the_large_mean_pred_24h": float(np.mean(p[lab, 1])), "observed": float(ph), "wilson95": [float(ctr - half), float(ctr + half)],
    "inside_wilson": bool(ctr - half <= np.mean(p[lab, 1]) <= ctr + half),
    "recalibrate_survival_function_val_to_holdout": rec,
    "notes": "recalibration is a marginal shift of the any-event survival function (km_calibration.py), not clipped; no conformal or CIF recalibration"}

# S5: persistence and seed reproducibility
blob = pickle.dumps(model); m2 = pickle.loads(blob)
p2 = m2.predict_proba(Xho, time_horizon=T_H)
# reproducibility refits use n_iter=20 to bound CPU on the shared host
model_a, _, p_a, _ = fit_eval(False, random_state=0, n_iter=20)
model_b, _, p_b, _ = fit_eval(False, random_state=0, n_iter=20)
model_c, _, p_c, _ = fit_eval(False, random_state=1, n_iter=20)
res["S5_persistence"] = {"format": "pickle (sklearn estimator)", "bytes": len(blob), "identical_after_reload": bool(np.array_equal(p, p2)),
    "refit_same_seed_identical_n_iter20": bool(np.array_equal(p_a, p_b)),
    "refit_other_seed_max_abs_diff_p1_n_iter20": float(np.max(np.abs(p_a[:, 1] - p_c[:, 1])))}
res["S6_timings"] = dict(tm.t)
C.dump(res, os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoke_hazardous.result.json"))
