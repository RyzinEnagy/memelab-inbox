# Second reviewer rerun: hazardous at pin 1504934e (installed from pinned tree), small n_iter for CPU.
import sys, time, pickle, numpy as np, pandas as pd, warnings
warnings.simplefilter("ignore")
import hazardous
from hazardous import SurvivalBoost
from hazardous.metrics import integrated_brier_score_incidence
df = pd.read_csv(sys.argv[1]).sort_values("decision_time", kind="stable").reset_index(drop=True)
X = df[["liq_usd", "vol_24h", "age_h", "score100", "fatal_flag", "ret_1h"]].copy()
X["liq_usd"] = np.log1p(X["liq_usd"]); X["vol_24h"] = np.log1p(X["vol_24h"])
y = pd.DataFrame({"event": df["event_observed"].astype(int), "duration": df["time_to_event_h"].astype(float)})
tr = (df.split == "train").values; ho = (df.split == "holdout").values
print("hazardous", open(hazardous.__file__.replace("__init__.py", "VERSION.txt")).read().strip(), "events train", int(y.event[tr].sum()), "holdout rows", int(ho.sum()), "nan in X train", int(X[tr].isna().any(axis=1).sum()))
t0 = time.time(); m = SurvivalBoost(n_iter=10, random_state=0, show_progressbar=False).fit(X[tr], y[tr]); fit_s = time.time() - t0
grid = np.linspace(1, 23, 12)
cif = m.predict_cumulative_incidence(X[ho], times=grid)
d = np.diff(cif[:, 1, :], axis=1)
print(f"fit n_iter=10: {fit_s:.1f} s; CIF event1 decreases somewhere for {int((d < -1e-12).any(axis=1).sum())} of {cif.shape[0]} holdout rows, largest drop {float(-d.min()):.4f}")
p = m.predict_proba(X[ho], time_horizon=23.0)
print("predict_proba shape", p.shape, "rows sum to 1:", bool(np.allclose(p.sum(1), 1)), "range event1", round(float(p[:, 1].min()), 4), round(float(p[:, 1].max()), 4))
m2 = pickle.loads(pickle.dumps(m)); print("pickle identical:", bool(np.array_equal(m2.predict_proba(X[ho], time_horizon=23.0), p)))
ibs = integrated_brier_score_incidence(y_train=y[tr], y_test=y[ho], y_pred=cif[:, 1, :], times=grid, event_of_interest=1)
print("IBS event1 holdout", round(float(ibs), 5))
