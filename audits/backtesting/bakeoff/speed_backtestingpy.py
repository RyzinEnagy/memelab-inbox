import json, time, warnings
import pandas as pd
from backtesting import Backtest, Strategy
warnings.filterwarnings("ignore")
U = json.load(open("/tmp/claude-0/speed_universe.json"))
class S(Strategy):
    def init(self): pass
    def next(self):
        i = len(self.data) - 1
        for tr in self.trades:
            if tr.sl is None: tr.sl = tr.entry_price * 0.9
        if not self.position and i >= 20 and self.data.Close[i] > max(self.data.High[i - 20:i]): self.buy(size=0.9999)
t0 = time.perf_counter(); n = 0
for bars in U:
    df = pd.DataFrame(bars); df.index = pd.to_datetime(df["t"], unit="s")
    df = df.rename(columns={"o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume"})[["Open", "High", "Low", "Close", "Volume"]]
    n += len(Backtest(df, S, cash=1e6, commission=0.0025, trade_on_close=False, finalize_trades=True).run()["_trades"])
print(json.dumps({"engine": "backtesting.py 0.6.6 (flat fee)", "tokens": len(U), "bars": len(U) * 1000, "trades": n, "secs": round(time.perf_counter() - t0, 3)}))
