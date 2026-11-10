import json, time
from proto_engine import Exec, run_breakout
U = json.load(open("/tmp/claude-0/speed_universe.json"))
t0 = time.perf_counter(); n = 0
for bars in U:
    d = {"bars": bars, "bar_seconds": 3600, "strategy_breakout": {"lookback": 20, "stop_frac": 0.1, "max_hold_bars": 10**9}}
    n += len(run_breakout(d, 1000.0, Exec("cpmm", 0.0025, 60000.0, 0.01)))
print(json.dumps({"engine": "proto (pure Python, CPMM fills)", "tokens": len(U), "bars": len(U) * 1000, "trades": n, "secs": round(time.perf_counter() - t0, 3)}))
