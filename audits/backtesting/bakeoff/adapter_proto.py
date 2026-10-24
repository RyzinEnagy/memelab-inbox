"""Thin adapter prototype: real lab analyze result -> opportunity snapshot used by the execution/stress model.

Runs the unchanged lab pipeline on the committed inbox fixture with persist=False and a fixed observed_at,
then extracts only what the engine needs. Proves the seam, raw-unit quote handling and the C1 fix
(transfer fee taken from the mechanics output, not the unwritten authorities key)."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from memelab import pipeline
from memelab.bridge import ingest

INBOX = ROOT / "data" / "inbox"
IDS = ["disc01", "s2_01", "deep01a"]
PAID = "98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump"
res = [ingest.load_result(INBOX / f"{i}.result.json") for i in IDS]
mb = ingest.merged_bodies(res)
bodies = {k: v[0] for k, v in mb.items()}
obs = max(v[1] for v in mb.values())          # latest capture time among merged bodies (not wall clock)
r = pipeline.analyze_token(PAID, bodies, observed_at=obs, sol_price=120.8, persist=False)


def snapshot(r):
    b, m = r["bundle"], r["modules"]
    mech = m.get("mechanics") or {}
    dec = (b.get("identity") or {}).get("decimals")
    sol = (b.get("market") or {}).get("sol_price") or 120.8
    sells = []
    for usd, q in sorted(((b.get("quotes") or {}).get("SELL") or {}).items()):
        if q.get("status") != "OK":
            sells.append({"usd": usd, "status": q.get("status")}); continue
        tokens_in = q["in"] / 10 ** dec
        sol_out = q["out"] / 1e9
        sells.append({"usd": usd, "status": "OK", "tokens_in": tokens_in, "proceeds_usd": sol_out * sol, "impact_frac": q.get("impact"), "hops": len(q.get("route") or [])})
    return {"chain": b.get("chain"), "mint": r["mint"], "as_of": b["observed_at"], "quote_basis": "PRESENT_TENSE_ROUTER_QUOTE (not a historical fill)",
            "transfer_fee_bps": mech.get("transfer_fee_bps"), "transfer_fee_bps_in_authorities": (b.get("authorities") or {}).get("transfer_fee_bps"),
            "pools": [{"pool": p.get("pool"), "dex": p.get("dex"), "reserve_usd": p.get("reserve_usd"), "created": p.get("created")} for p in b.get("pools") or []][:5],
            "fatal_flags": [f["flag"] for f in r["score"].get("fatal_flags") or []], "score": r["score"]["total"], "status": r["status"]["status"], "sell_curve": sells}


s = snapshot(r)
json.dump(s, open("result_adapter.json", "w"), indent=1, default=str)
print(json.dumps({k: s[k] for k in ("chain", "mint", "as_of", "transfer_fee_bps", "transfer_fee_bps_in_authorities", "fatal_flags", "score", "status")}, default=str))
for x in s["sell_curve"]:
    print(x)
assert s["chain"] == "solana" and s["mint"] == PAID and s["as_of"] == obs
assert any(x["status"] == "OK" for x in s["sell_curve"])
ok = [x for x in s["sell_curve"] if x["status"] == "OK"]
eff = [x["proceeds_usd"] / x["usd"] for x in ok]
print("proceeds per $ of quoted size:", [round(e, 4) for e in eff])
