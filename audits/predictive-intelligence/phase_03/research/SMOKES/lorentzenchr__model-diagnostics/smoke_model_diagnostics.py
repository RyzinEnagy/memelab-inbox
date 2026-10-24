"""Phase 03 R2 smoke for lorentzenchr/model-diagnostics at d0d8eec5 (installed from the pinned source, version 1.5.0).
Run: python -I smoke_model_diagnostics.py   (the runner adds unshare -n so no network is available)
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

import common as C  # noqa: E402
import model_diagnostics  # noqa: E402
from model_diagnostics.calibration import compute_bias, plot_reliability_diagram  # noqa: E402
from model_diagnostics.scoring import LogLoss, SquaredError, decompose  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
C.header(f"model_diagnostics from {model_diagnostics.__file__} | polars {pl.__version__} | matplotlib {matplotlib.__version__}")
df, sha = C.load()
print("challenge sha256", sha)
tr, cal, ho, info = C.splits(df)
print("splits", info)
X = C.design(df, C.FEATURES)
y = df.label.to_numpy()
Xtr, ytr = X[tr], y[tr].astype(int)
Xh, yh = X[ho], y[ho].astype(int)
base_rate = float(ytr.mean())
base = C.base_pipeline().fit(Xtr, ytr)
p_ho = base.predict_proba(Xh)[:, 1]
print(f"train prevalence {base_rate:.5f}; base holdout pred_hash={C.pred_hash(p_ho)}")
Xl = C.design(df, C.FEATURES + [C.TRAP])
leaky = C.base_pipeline().fit(Xl[tr], ytr)
pl_ho = leaky.predict_proba(Xl[ho])[:, 1]
const = np.full(len(yh), base_rate)

print("\n--- S2/S4 score decomposition: score = miscalibration - discrimination + uncertainty ---")
preds = np.column_stack([const, p_ho, pl_ho])
t0 = time.perf_counter()
dec_se = decompose(yh, preds, scoring_function=SquaredError())
t_dec = time.perf_counter() - t0
print("SquaredError (Brier) decomposition, columns const_B0 / base / leaky:")
print(dec_se)
dec_ll = decompose(yh, preds, scoring_function=LogLoss())
print("LogLoss decomposition:")
print(dec_ll)
own = [C.brier(yh, preds[:, i]) for i in range(3)]
lib = dec_se["score"].to_list()
print(f"own Brier {np.round(own, 6).tolist()} vs library score {np.round(lib, 6).tolist()}; max diff {np.max(np.abs(np.array(own) - np.array(lib))):.2e}")
own_ll = [C.logloss(yh, preds[:, i], eps=1e-15) for i in range(3)]
print(f"own log loss {np.round(own_ll, 6).tolist()} vs library {np.round(dec_ll['score'].to_list(), 6).tolist()}")
print(f"decompose wall {t_dec*1000:.1f} ms for 3 models x {len(yh)} rows")

print("\nS4b reliability as used by the library (isotonic / PAV recalibration, no fixed bins); PAV blocks with counts for the base model:")
from sklearn.isotonic import IsotonicRegression  # noqa: E402

iso = IsotonicRegression(y_min=None, y_max=None).fit(p_ho, yh)
rec = iso.predict(p_ho)
blocks = {}
for v, p in zip(rec, p_ho):
    b = blocks.setdefault(round(float(v), 10), [0, 0.0, float("inf"), 0.0])
    b[0] += 1
    b[1] += p
    b[2] = min(b[2], p)
    b[3] = max(b[3], p)
for v, (n, s, lo, hi) in sorted(blocks.items()):
    print(f"   p in [{lo:.4f},{hi:.4f}] n={n:4d} mean_p={s/n:.4f} recalibrated(obs)={v:.4f}")
C.print_reliability("own bins, base", yh, p_ho)

fig, ax = plt.subplots(1, 2, figsize=(10, 4))
t0 = time.perf_counter()
plot_reliability_diagram(yh, np.column_stack([p_ho, pl_ho]), n_bootstrap=200, confidence_level=0.9, ax=ax[0])
plot_reliability_diagram(yh, p_ho, n_bootstrap=200, diagram_type="bias", ax=ax[1])
fig.savefig(os.path.join(HERE, "reliability_base_vs_leaky.png"), dpi=80)
print(f"reliability diagrams with 200 bootstrap resamples written to reliability_base_vs_leaky.png ({time.perf_counter()-t0:.2f} s)")

print("\nS4c conditional calibration: generalised bias by feature bins (std error and p-value per bin)")
b_all = compute_bias(yh, p_ho)
print(b_all)
liq_h = df.liq_usd.to_numpy()[ho]
b_liq = compute_bias(yh, p_ho, feature=np.log1p(liq_h), n_bins=4, bin_method="quantile")
print(b_liq)
m_null = np.isnan(liq_h)
print("rows with NaN liq_usd are reported as their own bin (null feature value):", int(m_null.sum()),
      f"| positives in that bin: {int(yh[m_null].sum())}; mean p there {p_ho[m_null].mean():.4f}; "
      f"chance of 0 positives in {int(m_null.sum())} rows at p={p_ho[m_null].mean():.3f}: {np.prod(1 - p_ho[m_null]):.3f}")
print("the bin p-value uses the spread of (p - y) only; with no positives in the bin it treats a likely-by-chance 0/30 as decisive")

print("\n--- S1 leak trap ---")
print(f"leaky model discrimination {dec_se['discrimination'][2]:.5f} vs base {dec_se['discrimination'][1]:.5f}; "
      "model-diagnostics scores whatever it is given; it has no time or availability notion")

print("\n--- S3 missing values ---")
for tag, yp in (("NaN prediction", np.r_[np.nan, p_ho[1:]]), ("NaN outcome", None)):
    try:
        if yp is None:
            out = decompose(np.r_[np.nan, yh[1:]].astype(float), p_ho, scoring_function=SquaredError())
        else:
            out = decompose(yh, yp, scoring_function=SquaredError())
        print(f"  {tag}: no error; result {out.row(0)}")
    except Exception as e:
        print(f"  {tag}: {type(e).__name__}: {str(e)[:150]}")
try:
    print(f"  SquaredError()(y, p with NaN) = {SquaredError()(yh, np.r_[np.nan, p_ho[1:]])}")
except Exception as e:
    print(f"  SquaredError with NaN: {type(e).__name__}: {str(e)[:150]}")

print("\n--- S5 persistence ---")
d2 = decompose(yh, preds, scoring_function=SquaredError())
print(f"SKIPPED (stateless functions, nothing to persist); repeated call identical: {d2.equals(dec_se)}")

print("\n--- S6 cost ---")
t0 = time.perf_counter()
for _ in range(20):
    decompose(yh, p_ho, scoring_function=SquaredError())
print(f"decompose single model {(time.perf_counter()-t0)/20*1000:.2f} ms; peak RSS {C.peak_rss_mb():.1f} MB")
