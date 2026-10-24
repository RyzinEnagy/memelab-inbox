"""Smoke test: backtesting.py fill timing and SL/TP intrabar behaviour (synthetic, no network).

30 hourly bars; Open[i] = 100 + i, Close[i] = Open[i] + 0.5. Signal on bar k = 10.
"""
import warnings
import numpy as np
import pandas as pd
import backtesting
from backtesting import Backtest, Strategy

warnings.simplefilter("ignore")
n, k = 30, 10


def make(crash=None):
    idx = pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC")
    o = 100.0 + np.arange(n)
    df = pd.DataFrame({"Open": o, "High": o + 0.75, "Low": o - 0.25, "Close": o + 0.5,
                       "Volume": 1e6}, index=idx)
    if crash:
        df.iloc[15] = list(crash) + [1e6]
    return df


def strat(sl=None, tp=None, size=10):
    class S(Strategy):
        def init(self):
            pass

        def next(self):
            if len(self.data) - 1 == k:
                self.buy(size=size, sl=sl, tp=tp)
    return S


print("backtesting", backtesting.__version__)
df = make()
print(f"bar k={k}: Open={df.Open.iloc[k]} Close={df.Close.iloc[k]}; bar k+1 Open={df.Open.iloc[k+1]}")

for toc in (False, True):
    st = Backtest(df, strat(), cash=100_000, trade_on_close=toc, finalize_trades=True).run()
    t = st._trades.iloc[0]
    print(f"[1] trade_on_close={toc}: EntryBar={t.EntryBar} EntryPrice={t.EntryPrice}")

# both SL (105) and TP (118) inside crash bar 15 (O=114 H=125 L=90 C=95)
st = Backtest(make((114.0, 125.0, 90.0, 95.0)), strat(sl=105, tp=118), cash=100_000).run()
t = st._trades.iloc[0]
print(f"[2] SL+TP both inside bar 15: ExitBar={t.ExitBar} ExitPrice={t.ExitPrice} (SL=105, TP=118)")

# gap through SL: bar 15 opens at 90 below SL 105
st = Backtest(make((90.0, 92.0, 88.0, 91.0)), strat(sl=105), cash=100_000).run()
t = st._trades.iloc[0]
print(f"[3] gap below SL: ExitBar={t.ExitBar} ExitPrice={t.ExitPrice} (SL=105, bar15 Open=90)")

# size independence: spread is a flat fraction
for size in (1, 900):
    st = Backtest(df, strat(size=size), cash=1e7, spread=0.01, finalize_trades=True).run()
    print(f"[4] size={size} spread=1%: EntryPrice={st._trades.iloc[0].EntryPrice:.4f}")
