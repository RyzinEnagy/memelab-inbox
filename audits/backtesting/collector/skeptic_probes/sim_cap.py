import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, "tests"); sys.path.insert(0, ".")
import test_backtest_depth as T
from memelab.backtest import depth, store
d = json.load(open("tests/fixtures/backtest/depth/gt_pools_multi_solana.json"))
NOW = T.NOW; ET = NOW - 50*60       # export 50 min before the run
decs = []
for i, it in enumerate(d["data"]):
    decs.append({"chain": "solana", "mint": it["relationships"]["base_token"]["data"]["id"].split("_",1)[1], "pool_address": it["attributes"]["address"],
                 "pool_source": "EXPORT_GRADUATED_POOL", "export_commit": "c", "export_time": ET, "export_path": "data/state/latest.json",
                 "created_at": ET-60, "row_sha256": f"r{i}", "status": "x"})
decs += [{"chain":"bsc","mint":T.C,"pool_address":T.C_POOL,"pool_source":"EXPORT_PRIMARY_POOL","export_commit":"c","export_time":ET,"export_path":"p","created_at":ET,"row_sha256":"rc","status":"x"},
         {"chain":"base","mint":T.E,"pool_address":T.E_POOL,"pool_source":"EXPORT_PRIMARY_POOL","export_commit":"c","export_time":ET,"export_path":"p","created_at":ET,"row_sha256":"re","status":"x"}]
td = Path(tempfile.mkdtemp()); store.RAW_DIR = td/"raw"; con = store.connect(td/"bt.sqlite")
for hour in range(3):
    clk = T.Clock(NOW + hour*3600); get = T.fake(clk)
    out = depth.collect(con, exports={"status":"OK","decisions":decs}, now=NOW+hour*3600, http_get=get, clock=clk, sleep=clk.sleep)
    quoted = {r[0] for r in con.execute("SELECT DISTINCT mint FROM bt_depth_snapshots WHERE kind='QUOTE' AND provider='jupiter' AND captured_at>=?", (NOW+hour*3600,))}
    print(f"hour {hour}: jup calls {out['calls']['jupiter']}, gt {out['calls']['geckoterminal']}, pools quoted {len(quoted)}/16, wall {out['wall_s']}, deadline_hit {out['deadline_hit']}, not_attempted {out['not_attempted']}")
    if hour == 0:
        order = [r[0] for r in con.execute("SELECT mint FROM bt_depth_decisions WHERE chain='solana' ORDER BY id")]
        print("  never quoted in hour 0, by export position:", [order.index(m) for m in order if m not in quoted])
