"""Counterexample: the export's pool carries a stale price 2x the market; Jupiter routes elsewhere at the market."""
import json, sys
sys.path.insert(0, "/home/claude/pi_orchestration/skeptic_collector/tests")
import test_backtest_depth as T
from test_backtest_depth import con, exports  # fixtures
from memelab.backtest import depth

def test_stale_pool_price_reads_as_exit_haircut(con, exports):
    clk = T.Clock(T.NOW); base = T.fake(clk)
    pools = json.loads((T.FX / "gt_pools_multi_solana.json").read_bytes())
    for it in pools["data"]:
        if it["attributes"]["address"] == T.A_POOL:
            it["attributes"]["base_token_price_usd"] = str(float(it["attributes"]["base_token_price_usd"]) * 2)   # stale: last trade at 2x
    def get(url):
        if "/solana/pools/multi/" in url:
            clk.t += 0.3; return 200, json.dumps(pools).encode()
        if "jup.ag" in url and f"inputMint={T.A}" in url:
            amt = int(url.split("amount=")[1].split("&")[0])
            fx = next(v for (m, a), v in T.JUP.items() if m == T.A and int(a) > 0 and abs(int(a) / 2 - amt) / amt < 0.01)  # same USD size at the market
            j = json.loads(fx); scale = amt / int(j["inAmount"])
            j["inAmount"] = str(amt); j["outAmount"] = str(int(int(j["outAmount"]) * scale)); j["swapUsdValue"] = str(float(j.get("swapUsdValue") or 0) * scale)
            clk.t += 0.3; return 200, json.dumps(j).encode()
        return base(url)
    depth.collect(con, exports=exports, now=T.NOW, http_get=get, clock=clk, sleep=clk.sleep)
    rows = [dict(r) for r in con.execute("SELECT size_usd, state, out_usd, price_impact, value_json FROM bt_depth_snapshots WHERE kind='QUOTE' AND mint=?", (T.A,))]
    for r in rows:
        v = json.loads(r["value_json"]); print(r["size_usd"], r["state"], round(r["out_usd"], 2), "ratio", round(v["proceeds_ratio"], 3), "impact", r["price_impact"], "swapUsd", round(v["swap_usd_value"], 2))
    assert all(r["state"] == "OK" for r in rows)
