"""Smoke test: quantstats on synthetic hourly returns (no network, no benchmark ticker).

quantstats is an analytics library: it has no order or fill model, so there is no
fill timing to observe. We feed it a returns series built by OUR assumption
(entry at bar k+1 open) and check (a) it does not re-time anything, (b) default
annualisation, (c) the Monte Carlo CAGR spread.
"""
import warnings
import numpy as np
import pandas as pd
import quantstats as qs

warnings.simplefilter("ignore")
n, k = 30, 10
idx = pd.date_range("2026-01-01", periods=n, freq="h")
o = 100.0 + np.arange(n)
c = o + 0.5
# strategy equity: flat until bar k+1, long from k+1 open to the end
eq = pd.Series(1.0, index=idx)
eq.iloc[k + 1:] = c[k + 1:] / o[k + 1]
rets = eq.pct_change().fillna(0.0)
print("quantstats", qs.__version__)
print("[1] first non-zero return at", rets[rets != 0].index[0], "(we set entry at bar k+1; library does not re-time)")

print("[2] sharpe default periods=252:", round(qs.stats.sharpe(rets), 4),
      "| periods=8760 (hourly 24/7):", round(qs.stats.sharpe(rets, periods=8760), 4))
print("    probabilistic_sharpe_ratio:", round(qs.stats.probabilistic_sharpe_ratio(rets), 4))

rng = np.random.default_rng(7)
noisy = pd.Series(rng.normal(0.0005, 0.03, 2000), index=pd.date_range("2026-01-01", periods=2000, freq="h"))
mc = qs.stats.montecarlo_cagr(noisy, sims=200, seed=1)
print("[3] montecarlo_cagr on 2000 hourly returns (permutation MC):",
      {k2: round(v, 10) for k2, v in mc.items() if k2 in ("min", "max", "std")})
print("    std ~0 => shuffling returns cannot change terminal wealth; 'years' uses 252 bars/yr")
dd = qs.stats.montecarlo_drawdown(noisy, sims=200, seed=1)
print("[4] montecarlo_drawdown percentile_5/95:", round(dd["percentile_5"], 4), round(dd["percentile_95"], 4))
