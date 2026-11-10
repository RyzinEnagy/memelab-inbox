"""vectorbt 1.2.0 (Apache-2.0 + Commons Clause, isolated venv) on the canonical dataset, flat-fee mode. Two configurations:
default (signals at bar close, fills at close, stops at stop price) and adjusted (signals shifted one bar, price=open)."""
import json, time, warnings
import numpy as np, pandas as pd
import vectorbt as vbt
warnings.filterwarnings("ignore")
d = json.load(open("dataset.json"))
df = pd.DataFrame(d["bars"]); df.index = pd.to_datetime(df["t"], unit="s")
LB = d["strategy_breakout"]["lookback"]
prior_high = df["h"].rolling(LB).max().shift(1)
sig = df["c"] > prior_high
out = {}
for name, kw in (("default_close_fill", dict(close=df["c"], entries=sig, exits=pd.Series(False, index=df.index))),
                 ("adjusted_next_open", dict(close=df["c"], open=df["o"], high=df["h"], low=df["l"], price=df["o"], entries=sig.shift(1, fill_value=False), exits=pd.Series(False, index=df.index)))):
    t0 = time.perf_counter()
    pf = vbt.Portfolio.from_signals(init_cash=1000, size=np.inf, fees=d["pool"]["swap_fee"], sl_stop=0.10, accumulate=False, **kw)
    tr = pf.trades.records_readable
    out[name] = [{"entry_bar": int(df.index.get_loc(r["Entry Timestamp"])), "entry_px": float(r["Avg Entry Price"]), "exit_bar": int(df.index.get_loc(r["Exit Timestamp"])),
                  "exit_px": float(r["Avg Exit Price"]), "size": float(r["Size"]), "pnl": float(r["PnL"]), "ret": float(r["Return"])} for _, r in tr.iterrows()]
    out[name + "_secs"] = time.perf_counter() - t0
json.dump(out, open("result_vectorbt.json", "w"), indent=1)
print(json.dumps(out, indent=1))
