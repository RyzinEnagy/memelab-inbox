"""Smoke test: vectorbt fill timing on synthetic data (no network).

30 hourly bars; open[i] = 100 + i, close[i] = open[i] + 0.5, so every bar's
close differs from the next bar's open. Entry signal fires on bar k = 10.
"""
import numpy as np
import pandas as pd
import vectorbt as vbt

n, k = 30, 10
idx = pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC")
o = pd.Series(100.0 + np.arange(n), index=idx)
c = o + 0.5
h = c + 0.25
l = o - 0.25
# crash bar 15: opens above the stop level, trades far below it
o.iloc[15], h.iloc[15], l.iloc[15], c.iloc[15] = 114.0, 114.2, 90.0, 95.0

entries = pd.Series(False, index=idx); entries.iloc[k] = True
exits = pd.Series(False, index=idx)

print("vectorbt", vbt.__version__)
print(f"bar k={k}: open={o.iloc[k]} close={c.iloc[k]}; bar k+1 open={o.iloc[k+1]}")

# 1) defaults: price=None -> np.inf -> same-bar close
pf = vbt.Portfolio.from_signals(c, entries, exits, open=o, high=h, low=l, init_cash=1000, freq="1h")
r = pf.orders.records_readable
print("\n[1] default from_signals: entry row/price ->", r[["Timestamp", "Price"]].iloc[0].tolist())
same_bar = r["Price"].iloc[0] == c.iloc[k]
print("    SAME_BAR_CLOSE_FILL =", same_bar)

# 2) explicit next-bar open: user must shift signals and pass price=open
pf2 = vbt.Portfolio.from_signals(c, entries.shift(1, fill_value=False), exits, price=o, init_cash=1000, freq="1h")
r2 = pf2.orders.records_readable
print("[2] shifted signals + price=open: entry ->", r2[["Timestamp", "Price"]].iloc[0].tolist(),
      "NEXT_BAR_OPEN =", r2["Price"].iloc[0] == o.iloc[k + 1])

# 3) size-dependence: same fill price for 1e3 and 1e12 cash (flat % slippage only)
for cash in (1e3, 1e12):
    p = vbt.Portfolio.from_signals(c, entries, exits, init_cash=cash, slippage=0.01, freq="1h")
    print(f"[3] init_cash={cash:.0e} slippage=1% -> entry price {p.orders.records_readable['Price'].iloc[0]:.6f}")

# 4) stop-loss 5% on a crash bar with default stop_exit_price='stoplimit' and slippage=1%
pf4 = vbt.Portfolio.from_signals(c, entries, exits, open=o, high=h, low=l, sl_stop=0.05,
                                  slippage=0.01, init_cash=1000, freq="1h")
r4 = pf4.orders.records_readable
print("[4] SL 5% (stop level", round(c.iloc[k] * 0.95, 6), "), bar15 low=90 close=95 ->")
print(r4[["Timestamp", "Side", "Price"]].to_string(index=False))
