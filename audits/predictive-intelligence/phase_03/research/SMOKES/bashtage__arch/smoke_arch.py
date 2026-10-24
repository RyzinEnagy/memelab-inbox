"""Phase 03 R2 smoke for bashtage/arch at 5db69b01 (built from the pinned source with Cython, Python 3.13).
Run: python -I smoke_arch.py   (the runner adds unshare -n so no network is available)
"""
import os
import pickle
import sys
import time
import warnings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import common as C  # noqa: E402
import arch  # noqa: E402
from arch.bootstrap import (  # noqa: E402
    MCS,
    SPA,
    CircularBlockBootstrap,
    IIDBootstrap,
    MovingBlockBootstrap,
    StationaryBootstrap,
    optimal_block_length,
)

C.header(f"arch {arch.__version__} from {arch.__file__}")
df, sha = C.load()
print("challenge sha256", sha)
tr, cal, ho, info = C.splits(df)
print("splits", info)
X = C.design(df, C.FEATURES)
y = df.label.to_numpy()
ytr = y[tr].astype(int)
base_rate = float(ytr.mean())
base = C.base_pipeline().fit(X[tr], ytr)
hidx = np.where(ho)[0]
hidx = hidx[np.argsort(df.decision_time.to_numpy()[hidx], kind="mergesort")]
yh = y[hidx].astype(int)
p_ho = base.predict_proba(X[hidx])[:, 1]
print(f"train prevalence {base_rate:.5f}; holdout rows (time-ordered, censored excluded) {len(yh)}, positives {int(yh.sum())}; "
      f"base holdout pred_hash={C.pred_hash(base.predict_proba(X[ho])[:, 1])}")
lm = (p_ho - yh) ** 2
lb = (base_rate - yh) ** 2
day = (df.decision_time.to_numpy()[hidx] // 86400)
mint = df.mint.to_numpy()[hidx]
sym = df.symbol.to_numpy()[hidx]
rows_per_day = np.bincount(day - day.min())
print(f"holdout UTC days {len(np.unique(day))}, rows per day {rows_per_day.tolist()}; distinct mints {len(np.unique(mint))}, distinct symbols {len(np.unique(sym))}")


def stat(a, b):
    return np.array([a.mean(), 1 - a.mean() / b.mean()])


point = stat(lm, lb)
print(f"\npoint: Brier={point[0]:.5f} BSS vs B0={point[1]:.4f}")

print("\n--- block bootstrap of Brier and Brier skill score (reps=2000, 95% percentile intervals) ---")
obl = optimal_block_length(lm)
print("optimal_block_length on the per-row Brier loss:")
print(obl.round(3).to_string())
b_sb = max(1.0, float(obl["stationary"].iloc[0]))
b_cb = max(1, int(round(float(obl["circular"].iloc[0]))))
b_day = int(np.median(rows_per_day))
rows = []
for name, mk in (
    ("IID", lambda: IIDBootstrap(lm, lb, seed=20261024)),
    (f"Stationary(mean block {b_sb:.2f}, optimal)", lambda: StationaryBootstrap(b_sb, lm, lb, seed=20261024)),
    (f"Stationary(mean block {b_day}, about one day of rows)", lambda: StationaryBootstrap(b_day, lm, lb, seed=20261024)),
    (f"MovingBlock(block {b_day})", lambda: MovingBlockBootstrap(b_day, lm, lb, seed=20261024)),
    (f"CircularBlock(block {b_cb}, optimal)", lambda: CircularBlockBootstrap(b_cb, lm, lb, seed=20261024)),
):
    bs = mk()
    t0 = time.perf_counter()
    ci = bs.conf_int(stat, reps=2000, method="percentile", size=0.95)
    dt = time.perf_counter() - t0
    rows.append((name, ci))
    print(f"  {name:48s} Brier [{ci[0,0]:.5f}, {ci[1,0]:.5f}] width {ci[1,0]-ci[0,0]:.5f} | BSS [{ci[0,1]:.4f}, {ci[1,1]:.4f}] "
          f"includes 0: {ci[0,1] <= 0 <= ci[1,1]} | {dt:.2f} s")
bca = IIDBootstrap(lm, lb, seed=20261024).conf_int(stat, reps=2000, method="bca")
print(f"  IID BCa: Brier [{bca[0,0]:.5f}, {bca[1,0]:.5f}] BSS [{bca[0,1]:.4f}, {bca[1,1]:.4f}]")


def cluster_ci(keys, label, reps=2000):
    uk, inv = np.unique(keys, return_inverse=True)
    sm = np.bincount(inv, weights=lm)
    sb = np.bincount(inv, weights=lb)
    n = np.bincount(inv)

    def f(sm_, sb_, n_):
        return np.array([sm_.sum() / n_.sum(), 1 - sm_.sum() / sb_.sum()])

    ci = IIDBootstrap(sm, sb, n.astype(float), seed=20261024).conf_int(f, reps=reps, method="percentile")
    print(f"  cluster bootstrap over {label} ({len(uk)} clusters, IIDBootstrap on per-cluster sums): Brier [{ci[0,0]:.5f}, {ci[1,0]:.5f}] "
          f"BSS [{ci[0,1]:.4f}, {ci[1,1]:.4f}]")
    return ci


print("\n  group (cluster) bootstraps are not built in; done here by resampling per-cluster sums with IIDBootstrap:")
cluster_ci(day, "UTC decision days")
cluster_ci(mint, "exact mints")
cluster_ci(sym, "symbols (identity trap: merges different mints)")

print("\n  reproducibility: same seed twice identical:",
      np.array_equal(StationaryBootstrap(b_day, lm, lb, seed=7).conf_int(stat, reps=300, method="percentile"),
                     StationaryBootstrap(b_day, lm, lb, seed=7).conf_int(stat, reps=300, method="percentile")),
      "| different seed differs:",
      not np.array_equal(StationaryBootstrap(b_day, lm, lb, seed=7).conf_int(stat, reps=300, method="percentile"),
                         StationaryBootstrap(b_day, lm, lb, seed=8).conf_int(stat, reps=300, method="percentile")))

print("\n--- S4 interval coverage check (Monte Carlo, clustered binary events, known mean) ---")
rng = np.random.default_rng(20261024)
p11, p01 = 0.5, 0.02
pi = p01 / (p01 + 1 - p11)
n, sims, reps = 500, 200, 399
hit = {"IID": 0, "Stationary(optimal)": 0, "Stationary(block 25)": 0}
t0 = time.perf_counter()
for s in range(sims):
    z = np.empty(n)
    z[0] = rng.random() < pi
    u = rng.random(n)
    for t in range(1, n):
        z[t] = u[t] < (p11 if z[t - 1] else p01)
    bopt = max(1.0, float(optimal_block_length(z)["stationary"].iloc[0])) if z.std() > 0 else 1.0
    for name, bs in (("IID", IIDBootstrap(z, seed=s)), ("Stationary(optimal)", StationaryBootstrap(bopt, z, seed=s)),
                     ("Stationary(block 25)", StationaryBootstrap(25, z, seed=s))):
        ci = bs.conf_int(np.mean, reps=reps, method="percentile", size=0.9)
        hit[name] += int(ci[0, 0] <= pi <= ci[1, 0])
print(f"  Markov binary series n={n}, P(1|1)={p11}, P(1|0)={p01}, true mean {pi:.4f}; {sims} simulations x {reps} reps; nominal 0.90")
for k, v in hit.items():
    print(f"  {k:22s} empirical coverage {v/sims:.3f}")
print(f"  ({time.perf_counter()-t0:.1f} s)")

print("\n--- S1 leak trap ---")
Xl = C.design(df, C.FEATURES + [C.TRAP])
leaky = C.base_pipeline().fit(Xl[tr], ytr)
pl_ho = leaky.predict_proba(Xl[hidx])[:, 1]
ll = (pl_ho - yh) ** 2
ci = StationaryBootstrap(b_day, ll, lb, seed=1).conf_int(stat, reps=2000, method="percentile")
print(f"  leaky model BSS {stat(ll, lb)[1]:.4f}, stationary 95% [{ci[0,1]:.4f}, {ci[1,1]:.4f}]: a bootstrap quantifies sampling noise, it cannot detect look-ahead")

print("\n--- S3 missing values ---")
lnan = lm.copy()
lnan[0] = np.nan
try:
    ci = IIDBootstrap(lnan, seed=1).conf_int(np.mean, reps=200, method="percentile")
    print(f"  NaN in the loss series: no error, interval {ci.ravel().tolist()}")
except Exception as e:
    print(f"  NaN in the loss series: {type(e).__name__}: {str(e)[:150]}")
try:
    print("  optimal_block_length with NaN:", optimal_block_length(lnan).to_dict("records"))
except Exception as e:
    print(f"  optimal_block_length with NaN: {type(e).__name__}: {str(e)[:150]}")

print("\n--- role-specific: multiple-comparison tests on holdout losses (P22) ---")
X_s = X[hidx][:, [C.FEATURES.index("score100")]]
m_score = C.base_pipeline().fit(X[tr][:, [C.FEATURES.index("score100")]], ytr)
p_score = m_score.predict_proba(X_s)[:, 1]
noise = np.clip(base_rate + np.random.default_rng(3).normal(0, 0.02, len(yh)), 0.001, 0.999)
losses = np.column_stack([lb, lm, (p_score - yh) ** 2, (noise - yh) ** 2])
names = ["B0_prevalence", "base_LR", "score100_only_LR", "noise_around_prevalence"]
spa = SPA(lb, losses[:, 1:], block_size=b_day, reps=1000, seed=11)
spa.compute()
print(f"  SPA (benchmark B0 vs 3 models): pvalues {spa.pvalues.round(4).to_dict()} (small p means some model beats B0)")
mcs = MCS(losses, size=0.10, block_size=b_day, reps=1000, seed=11)
mcs.compute()
print(f"  MCS 90% set: included {[names[i] for i in mcs.included]} excluded {[names[i] for i in mcs.excluded]}")

print("\n--- role-specific: volatility models (what arch offers beyond the bootstrap) ---")
from arch import arch_model  # noqa: E402

rng = np.random.default_rng(5)
omega, alpha, beta, nobs = 0.02, 0.10, 0.85, 2016
r = np.empty(nobs)
s2 = omega / (1 - alpha - beta)
for t in range(nobs):
    r[t] = np.sqrt(s2) * rng.standard_normal()
    s2 = omega + alpha * r[t] ** 2 + beta * s2
for nn in (2016, 60):
    with warnings.catch_warnings(record=True) as wlist:
        warnings.simplefilter("always")
        t0 = time.perf_counter()
        res = arch_model(r[:nn], mean="Zero", vol="GARCH", p=1, q=1).fit(disp="off")
        dt = time.perf_counter() - t0
    f = res.forecast(horizon=12, reindex=False).variance.values[-1]
    print(f"  GARCH(1,1) on {nn} simulated 5-minute returns (true omega={omega}, alpha={alpha}, beta={beta}): "
          f"est {np.round(res.params.values, 3).tolist()} se {np.round(res.std_err.values, 3).tolist()} conv_flag={res.convergence_flag} "
          f"warnings={len(wlist)} fit {dt*1000:.0f} ms; 12-step variance forecast last={f[-1]:.4f}")

print("\n--- S5 persistence ---")
bs = StationaryBootstrap(b_day, lm, lb, seed=99)
blob = pickle.dumps(bs)
bs2 = pickle.loads(blob)
a = bs.conf_int(stat, reps=300, method="percentile")
b = bs2.conf_int(stat, reps=300, method="percentile")
print(f"  pickled bootstrap ({len(blob)} bytes) reproduces the same interval after reload: {np.array_equal(a, b)}; "
      "state is the seed plus the data, no model file")

print("\n--- S6 cost ---")
t0 = time.perf_counter()
StationaryBootstrap(b_day, lm, lb, seed=1).conf_int(stat, reps=2000, method="percentile")
print(f"  2000-rep stationary bootstrap on {len(lm)} rows: {time.perf_counter()-t0:.2f} s; peak RSS {C.peak_rss_mb():.1f} MB")
