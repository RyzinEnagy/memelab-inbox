import json, sys
from pathlib import Path
sys.path.insert(0, "/home/claude/pi_orchestration/skeptic_collector/tests")
sys.path.insert(0, "/home/claude/pi_orchestration/skeptic_collector")
import test_backtest_depth as T
from test_backtest_depth import *  # fixtures
from memelab.backtest import depth, store
from memelab.backtest.sources import gecko

def test_jup_429_on_last_budgeted_call(con, exports):
    clk = T.Clock(T.NOW); base = T.fake(clk); n = {"j": 0}
    def get(url):
        if "jup.ag" in url:
            n["j"] += 1
            if n["j"] == 4: return 429, b'{"message":"rate limited"}'
        return base(url)
    out = depth.collect(con, exports=exports, now=T.NOW, http_get=get, clock=clk, sleep=clk.sleep, jup_max_calls=4)
    print(out)

def test_gt_200_then_failures(con, exports):
    clk = T.Clock(T.NOW); base = T.fake(clk); n = {"g": 0}
    def get(url):
        if "geckoterminal" in url:
            n["g"] += 1
            if n["g"] > 1: return 0, b""
        return base(url)
    out = depth.collect(con, exports=exports, now=T.NOW, http_get=get, clock=clk, sleep=clk.sleep)
    print(out)

def test_slow_network_wall(con, exports):
    clk = T.Clock(T.NOW); base = T.fake(clk)
    def get(url):
        clk.t += 10.0   # every call times out at HTTP_TIMEOUT_S
        return 0, b""
    out = depth.collect(con, exports=exports, now=T.NOW, http_get=get, clock=clk, sleep=clk.sleep)
    print("WALL", out["wall_s"], out["calls"], out["deadline_hit"])
