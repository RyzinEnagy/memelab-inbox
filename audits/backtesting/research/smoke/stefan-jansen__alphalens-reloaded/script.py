"""Smoke test: alphalens-reloaded forward-return timing on synthetic hourly data (no network).

alphalens has no order/fill model. Its "fill" is implicit: forward return for a factor
stamped at t is prices[t+N] / prices[t] - 1, using whatever price series you pass.
"""
import warnings
import numpy as np
import pandas as pd
import alphalens as al

warnings.simplefilter("ignore")
n, k = 600, 10
rng = np.random.default_rng(3)
idx = pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC")
assets = [f"T{i}" for i in range(5)]
rets = rng.normal(0.0, 0.01, (n, 5))
rets[300, 1] = 59.0                    # T1: one +5900% hour (memecoin pump)
close = pd.DataFrame(100 * np.cumprod(1 + rets, axis=0), index=idx, columns=assets)
close.iloc[401:, 2] = np.nan           # T2: pool drained after bar 400, no more prices
factor = pd.DataFrame(rng.normal(size=(n, 5)), index=idx, columns=assets).stack()
factor.index.names = ["date", "asset"]
print("alphalens", al.__version__)

fd = al.utils.get_clean_factor_and_forward_returns(factor, close, periods=(1,), quantiles=5, max_loss=1.0)
col = fd.columns[0]
t0 = fd.loc[(idx[k], "T0"), col]
exp_close = close["T0"].iloc[k + 1] / close["T0"].iloc[k] - 1
print(f"[1] fwd '{col}' return for T0 at bar k equals close[k+1]/close[k]-1: {np.isclose(t0, exp_close)} "
      "=> entry assumed at the factor bar's own price (same-bar), unless the caller shifts prices")

pump_default = fd.loc[(idx[299], "T1"), col] if (idx[299], "T1") in fd.index else "ROW DROPPED"
fd2 = al.utils.get_clean_factor_and_forward_returns(factor, close, periods=(1,), quantiles=5,
                                                     max_loss=1.0, filter_zscore=None)
print(f"[2] T1 +5900% hour, default filter_zscore=20: {pump_default} | filter_zscore=None: "
      f"{fd2.loc[(idx[299], 'T1'), col]:.2f}")

rug = fd2.loc[(idx[400], "T2"), col]
print(f"[3] T2 after pool drained (price NaN from bar 401): fwd return at bar 400 = {rug} (prices are ffilled)")
