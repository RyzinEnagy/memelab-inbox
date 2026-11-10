"""backtesting.py (AGPL-3.0, unmodified, isolated venv, never imported by the lab) on the canonical dataset, flat-fee mode."""
import json, time, warnings
import pandas as pd
from backtesting import Backtest, Strategy
warnings.filterwarnings("ignore")
d = json.load(open("dataset.json"))
df = pd.DataFrame(d["bars"]); df.index = pd.to_datetime(df["t"], unit="s", utc=True).dt.tz_localize(None)
df = df.rename(columns={"o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume"})[["Open", "High", "Low", "Close", "Volume"]]
LB = d["strategy_breakout"]["lookback"]


class Breakout(Strategy):
    def init(self):
        pass

    def next(self):
        i = len(self.data) - 1
        for tr in self.trades:
            if tr.sl is None:
                tr.sl = tr.entry_price * 0.9
        if not self.position and i >= LB:
            prior_high = max(self.data.High[i - LB:i])
            if self.data.Close[i] > prior_high:
                self.buy(size=0.9999)


ev_t = d["event"]["first_seen_at"]; H = d["bar_seconds"]
ev_bar = (ev_t - d["bars"][0]["t"]) // H        # bar whose interval contains the known-at time


class Event(Strategy):
    def init(self):
        self.k = None

    def next(self):
        i = len(self.data) - 1
        if i == ev_bar and not self.position:
            self.buy(size=0.9999); self.k = i
        elif self.position and self.k is not None and i == self.k + d["strategy_event"]["hold_bars"]:
            self.position.close()


out = {}
for name, S in (("A_noimpact_1000", Breakout), ("B_noimpact_1000", Event)):
    t0 = time.perf_counter()
    bt = Backtest(df, S, cash=1000, commission=d["pool"]["swap_fee"], trade_on_close=False, exclusive_orders=False, finalize_trades=True)
    st = bt.run()
    tr = st["_trades"]
    out[name] = [{"entry_bar": int(r.EntryBar), "entry_px": float(r.EntryPrice), "exit_bar": int(r.ExitBar), "exit_px": float(r.ExitPrice),
                  "size": float(r.Size), "pnl": float(r.PnL), "ret": float(r.ReturnPct)} for r in tr.itertuples()]
    out[name + "_equity_final"] = float(st["Equity Final [$]"])
    out[name + "_secs"] = time.perf_counter() - t0
json.dump(out, open("result_backtestingpy.json", "w"), indent=1)
print(json.dumps(out, indent=1))
