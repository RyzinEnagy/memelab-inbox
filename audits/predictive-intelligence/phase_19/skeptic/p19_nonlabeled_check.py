"""Phase 19 skeptic: check the non-LABELED Solana outcome states against the archive and the decision list (no memelab import)."""
import csv, gzip, json, sys
from pathlib import Path
from collections import defaultdict
PH = Path(sys.argv[1]) / "audits/predictive-intelligence/phase_19"
rmap = json.load(open(PH / "data/read_map.json"))
man = {r["response_key"]: r for r in csv.DictReader(open(PH / "raw/MANIFEST.csv")) if r["response_key"]}
dec = {r["decision_key"]: r for r in csv.DictReader(open(PH / "monitoring/PROSPECTIVE_DECISIONS.csv"))}
outs = {}
for l in open(PH / "monitoring/OUTCOME_LEDGER.jsonl"):
    p = json.loads(l)["payload"]
    if p["kind"] == "OUTCOME":
        outs[(p["decision_key"], p["target"])] = p
H = {"price_path_target_before_invalidation_24h": 86400, "price_path_target_before_invalidation_6h": 21600,
     "price_path_severe_drawdown_or_halt_24h": 172800}
for (k, t), p in sorted(outs.items(), key=lambda x: (x[1]["state"], x[1]["decision_time"])):
    if p["chain"] != "solana" or p["state"] in ("LABELED",):
        continue
    rk = rmap.get(k)
    info = {"state": p["state"], "t": t.split("_")[-1] + ("b" if "6h" in t else ""), "mint6": p["mint"][:6], "D": p["decision_time"],
            "read": bool(rk), "detail": p["detail"]}
    if rk and rk in man:
        m = man[rk]
        info["http"] = m["http_status"]; info["identity"] = m["identity_check"]
        if m["http_status"] == "200":
            d = json.loads(gzip.open(PH / "raw" / m["file"]).read())
            cs = d["data"]["attributes"]["ohlcv_list"]
            D = p["decision_time"]
            ref = [c for c in cs if c[0] + 600 <= D and c[0] + 300 >= D - 3600]
            info["ref_candles"] = len(ref)
            info["candles_24h_before"] = sum(1 for c in cs if D - 86400 <= c[0] < D)
    if p["state"] == "THINNED":
        prev = [o for (k2, t2), o in outs.items() if t2 == t and o["mint"] == p["mint"] and o["decision_time"] < p["decision_time"]]
        info["earlier_same_mint"] = [(o["decision_time"], o["state"], round((p["decision_time"] - o["decision_time"]) / 3600, 1)) for o in prev]
    print(json.dumps(info))
