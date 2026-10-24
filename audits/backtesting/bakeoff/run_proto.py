import json, time
from proto_engine import Exec, run_breakout, run_event
d = json.load(open("dataset.json")); pool = d["pool"]
t0 = time.perf_counter()
r = {
 "A_noimpact_1000": run_breakout(d, 1000.0, Exec("flat", pool["swap_fee"])),
 "A_cpmm_1000": run_breakout(d, 1000.0, Exec("cpmm", pool["swap_fee"], pool["quote_reserve_usd"], pool["network_fee_usd"])),
 "A_cpmm_50000": run_breakout(d, 50000.0, Exec("cpmm", pool["swap_fee"], pool["quote_reserve_usd"], pool["network_fee_usd"])),
 "B_noimpact_1000": run_event(d, 1000.0, Exec("flat", pool["swap_fee"])),
 "B_naive_published_1000": run_event(d, 1000.0, Exec("flat", pool["swap_fee"]), use_field="published_at"),
}
r["_secs"] = time.perf_counter() - t0
json.dump(r, open("result_proto.json", "w"), indent=1)
for k, v in r.items():
    if k.startswith("_"): continue
    for t in v: print(k, {kk: (round(vv, 6) if isinstance(vv, float) else vv) for kk, vv in t.items() if kk in ("entry_bar","entry_px","exit_bar","exit_px","reason","tokens","proceeds","pnl","ret")})
