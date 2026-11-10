import json, time, warnings
import numpy as np, pandas as pd, vectorbt as vbt
warnings.filterwarnings("ignore")
U = json.load(open("/tmp/claude-0/speed_universe.json"))
idx = pd.to_datetime([b["t"] for b in U[0]], unit="s")
f = lambda k: pd.DataFrame({i: [b[k] for b in bars] for i, bars in enumerate(U)}, index=idx)
o, h, l, c = f("o"), f("h"), f("l"), f("c")
t0 = time.perf_counter()
sig = (c > h.rolling(20).max().shift(1)).shift(1, fill_value=False)
pf = vbt.Portfolio.from_signals(close=c, open=o, high=h, low=l, price=o, entries=sig, exits=pd.DataFrame(False, index=idx, columns=c.columns), init_cash=1000, size=np.inf, fees=0.0025, sl_stop=0.1)
n = int(pf.trades.count().sum())
print(json.dumps({"engine": "vectorbt 1.2.0 (flat fee, no size impact)", "tokens": len(U), "bars": len(U) * 1000, "trades": n, "secs": round(time.perf_counter() - t0, 3)}))
