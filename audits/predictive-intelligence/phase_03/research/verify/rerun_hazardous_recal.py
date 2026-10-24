"""Phase 03 repair pass (lead): definition probe for hazardous recalibrate_survival_function (skeptic m4).

The docstring promises S(t | x) - Delta(t) with Delta(t) = mean predicted S(t) on the calibration set minus the
Kaplan-Meier S(t) of the calibration outcomes; the pinned code subtracts difference_at_t, which returns the ABSOLUTE
difference (hazardous/metrics/_km_calibration.py, difference_at_t and recalibrate_survival_function), with no
clipping. A survival probability must stay in [0, 1] and a recalibration must move toward the observed curve.
Probe 1: a model that under-states survival on the calibration window (mean predicted S below KM); the lead's own
product-limit KM gives the signed Delta. Probe 2 (mirror): a model that over-states survival and a low test row.
The function recalibrates the any-event survival function only, not the probability of one competing event.
Usage: <hazardous venv python> -I rerun_hazardous_recal.py
"""
import json
import numpy as np
import pandas as pd
from hazardous.metrics._km_calibration import recalibrate_survival_function_predictions

rng = np.random.default_rng(20261024)
n = 400
duration = rng.uniform(1, 48, n)
event = (rng.uniform(size=n) < 0.10).astype(int)          # few events: KM survival stays near 0.9 at 24 h
y_cal = pd.DataFrame({"event": event, "duration": duration})
times = np.array([6.0, 12.0, 24.0])
pred_cal = np.full((n, len(times)), 0.60)                  # model under-states survival on the calibration window
pred_test = np.array([[0.97, 0.95, 0.93], [0.50, 0.45, 0.40]])
out = recalibrate_survival_function_predictions(pred_test, pred_cal, y_cal, times)
res = {"times": times.tolist(), "pred_test": pred_test.tolist(), "recalibrated": np.round(out, 6).tolist(),
       "outside_0_1": int(((out < 0) | (out > 1)).sum()), "max": float(out.max()), "min": float(out.min())}
# mirror case: model over-states survival, low test survival goes below 0
pred_cal2 = np.full((n, len(times)), 0.999)
event2 = (rng.uniform(size=n) < 0.6).astype(int)
y_cal2 = pd.DataFrame({"event": event2, "duration": duration})
out2 = recalibrate_survival_function_predictions(np.array([[0.05, 0.03, 0.02]]), pred_cal2, y_cal2, times)
res["mirror_recalibrated"] = np.round(out2, 6).tolist()
res["mirror_outside_0_1"] = int(((out2 < 0) | (out2 > 1)).sum())


def km(dur, ev, t):
    # product-limit estimate written by the lead (no library), events at a time counted before censorings
    s = 1.0
    for u in np.unique(dur[(ev == 1) & (dur <= t)]):
        at_risk = int((dur >= u).sum())
        d = int(((dur == u) & (ev == 1)).sum())
        s *= 1 - d / at_risk
    return s


km_t = np.array([km(duration, event, t) for t in times])
signed = pred_cal.mean(axis=0) - km_t                     # Delta(t) as the docstring defines it (signed)
res["lead_km_at_times"] = np.round(km_t, 6).tolist()
res["docstring_signed_delta"] = np.round(signed, 6).tolist()
res["docstring_formula_first_test_row"] = np.round(pred_test[0] - signed, 6).tolist()
res["library_shift_equals_abs_delta"] = bool(np.allclose(pred_test[0] - out[0], np.abs(signed)))
res["library_moves_against_the_error"] = bool(np.all(np.sign(pred_test[0] - out[0]) != np.sign(signed)))
print("RESULTS_JSON " + json.dumps(res, sort_keys=True))
