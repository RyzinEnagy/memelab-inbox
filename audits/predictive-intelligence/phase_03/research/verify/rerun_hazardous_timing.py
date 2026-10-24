"""Phase 03 lead re-execution: SurvivalBoost fit time at reduced n_iter on the 1,746 challenge train rows (K2),
and per-row inference time for one horizon. Usage: <hazardous venv python> -I rerun_hazardous_timing.py challenge.csv
"""
import json, sys, time
import numpy as np, pandas as pd
import hazardous
from hazardous import SurvivalBoost
d = pd.read_csv(sys.argv[1])
tr = d[d.split == "train"]; ho = d[d.split == "holdout"]
F = ["liq_usd", "vol_24h", "age_h", "score100", "fatal_flag", "ret_1h"]
y = pd.DataFrame({"event": tr.event_observed.astype(int), "duration": tr.time_to_event_h.astype(float)})
out = {"hazardous_version": hazardous.__version__, "train_rows": int(len(tr))}
for n in (10, 20):
    t0 = time.perf_counter(); m = SurvivalBoost(n_iter=n, show_progressbar=False, random_state=0).fit(tr[F], y); out["fit_s_n_iter_%d" % n] = round(time.perf_counter() - t0, 2)
t0 = time.perf_counter(); p = m.predict_proba(ho[F], time_horizon=23.99); dt = time.perf_counter() - t0
out["predict_ms_per_row_one_horizon"] = round(1000 * dt / len(ho), 4); out["proba_shape"] = list(p.shape)
print("RESULTS_JSON " + json.dumps(out, sort_keys=True))
