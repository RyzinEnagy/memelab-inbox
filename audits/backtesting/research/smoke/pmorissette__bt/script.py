"""Smoke test: bt fill timing and cost model on synthetic data (no network).

30 hourly bars; open[i] = 100 + i, close[i] = open[i] + 0.5. Signal on bar k = 10.
bt takes ONE price series per security; we pass closes.
"""
import warnings
import numpy as np
import pandas as pd
import bt

warnings.simplefilter("ignore")
n, k = 30, 10
idx = pd.date_range("2026-01-01", periods=n, freq="h")
o = 100.0 + np.arange(n)
close = pd.DataFrame({"TOK": o + 0.5}, index=idx)
opens = pd.DataFrame({"TOK": o}, index=idx)
sig = pd.DataFrame({"TOK": np.arange(n) >= k}, index=idx)
print("bt", bt.__version__)
print(f"bar k={k}: open={o[k]} close={o[k]+0.5}; bar k+1 open={o[k+1]}")


def run(prices, signal, name, **kw):
    s = bt.Strategy(name, [bt.algos.SelectWhere(signal), bt.algos.WeighEqually(), bt.algos.Rebalance()])
    b = bt.Backtest(s, prices, initial_capital=1_000_000, progress_bar=False, integer_positions=False, **kw)
    r = bt.run(b, progress_bar=False)
    return b, r.get_transactions()


b, tx = run(close, sig, "close_prices")
first = tx.iloc[0]
print("[1] close series, signal at k ->", tx.index[0][0], "price", first["price"],
      "SAME_BAR_CLOSE_FILL =", tx.index[0][0] == idx[k] and first["price"] == o[k] + 0.5)

b2, tx2 = run(opens, sig.shift(1, fill_value=False), "open_prices_lagged")
print("[2] open series + signal shifted 1 ->", tx2.index[0][0], "price", tx2.iloc[0]["price"],
      "NEXT_BAR_OPEN =", tx2.index[0][0] == idx[k + 1] and tx2.iloc[0]["price"] == o[k + 1])

# size-aware cost model: zero volume on the entry bar
vol_sigma = pd.DataFrame({"TOK": 0.02}, index=idx)
for v in (1e3, 0.0):
    volume = pd.DataFrame({"TOK": 1e3}, index=idx)
    volume.iloc[k] = v
    b3, tx3 = run(close, sig, f"sqrt_v{v}", commissions=bt.SqrtCostModel(Y=0.6),
                  volume=volume, volatility=vol_sigma)
    fees = b3.strategy.fees
    print(f"[3] SqrtCostModel, entry-bar volume={v}: qty={tx3.iloc[0]['quantity']:.2f} "
          f"fill price={tx3.iloc[0]['price']} fee at bar k={fees.loc[idx[k]]:.2f}")
