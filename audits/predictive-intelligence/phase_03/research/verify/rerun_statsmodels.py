"""Phase 03 lead re-execution: MarkovRegression filtered state is past-only once parameters are fixed (T5),
smoothed state is not (control). Different cut and series length from reviewer R1 (first 1,000 rows).
Usage: <statsmodels venv python> -I rerun_statsmodels.py challenge.csv
"""
import csv, json, sys
import numpy as np
import statsmodels
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
rows = sorted(csv.DictReader(open(sys.argv[1])), key=lambda r: int(r["decision_time"]))
y = np.array([float(r["ret_1h"]) for r in rows])
n = 1000
fit = MarkovRegression(y[:n], k_regimes=2, switching_variance=True).fit(disp=False)
f_short = np.asarray(MarkovRegression(y[:n], k_regimes=2, switching_variance=True).filter(fit.params).filtered_marginal_probabilities)
long_mod = MarkovRegression(y[: n + 800], k_regimes=2, switching_variance=True)
f_long = np.asarray(long_mod.filter(fit.params).filtered_marginal_probabilities)[:n]
s_short = np.asarray(MarkovRegression(y[:n], k_regimes=2, switching_variance=True).smooth(fit.params).smoothed_marginal_probabilities)
s_long = np.asarray(long_mod.smooth(fit.params).smoothed_marginal_probabilities)[:n]
oos = None
try:
    fit.predict(start=n, end=n + 3)
except Exception as e:
    oos = type(e).__name__
print("RESULTS_JSON " + json.dumps({
    "statsmodels_version": statsmodels.__version__,
    "filtered_first_1000_with_800_later_rows_appended_max_abs_diff": float(np.max(np.abs(f_short - f_long))),
    "smoothed_first_1000_with_800_later_rows_appended_max_abs_diff": float(np.max(np.abs(s_short - s_long))),
    "out_of_sample_predict": oos,
}, sort_keys=True))
