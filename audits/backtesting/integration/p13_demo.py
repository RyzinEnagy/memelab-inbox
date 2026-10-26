"""Phase 13 evidence: the FAST assessment on a real lab analysis (PAID, from the committed inbox captures) against a
COPY of the real research corpus, cache behaviour, DEEP stage, a manually supplied catalyst observation (Maxun
schedules are not approved, so no robot runs), and a FAST-stage wall-time benchmark. Writes p13_demo.json.
Run: python audits/backtesting/integration/p13_demo.py   (needs data/backtest/bt.sqlite; never writes it)"""
import copy, json, shutil, statistics, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from memelab import pipeline                       # noqa: E402
from memelab.backtest import assess, hook, store   # noqa: E402
from memelab.bridge import ingest                  # noqa: E402

PAID = "98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump"
IDS = ["disc01", "s2_01", "deep01a"]
res = [ingest.load_result(ROOT / "data" / "inbox" / f"{i}.result.json") for i in IDS]
bodies = {k: v[0] for k, v in ingest.merged_bodies(res).items()}
t_obs = max(r.observed_at for r in res)
r = pipeline.analyze_token(PAID, bodies, observed_at=t_obs, sol_price=120.8, persist=False)
lab_before = json.dumps({k: r[k] for k in ("score", "status", "report_md")}, sort_keys=True, default=str)
pol = dict(assess.DEFAULT_POLICY, enabled=True)
out = {"mint": PAID, "observed_at": t_obs, "lab": {"score": r["score"]["total"], "status": r["status"]["status"]}}
with tempfile.TemporaryDirectory() as td:
    db = Path(td) / "bt.sqlite"
    shutil.copy(ROOT / "data" / "backtest" / "bt.sqlite", db)
    con = store.connect(db)
    now = t_obs + 60
    a = assess.attach(r, pol, con=con, now=now)
    b = assess.attach(r, pol, con=con, now=now)
    out["fast"] = {k: a.get(k) for k in ("state", "tier", "cache", "request_key", "deep_stage", "flags", "reason")}
    out["fast"]["stress_decision"] = a.get("stress", {}).get("decision")
    out["fast"]["max_size"] = a.get("stress", {}).get("max_size")
    out["fast"]["historical_evidence"] = {k: v for k, v in (a.get("stress", {}).get("historical_evidence") or {}).items() if k != "returns"}
    out["fast"]["token_signals"] = a.get("token_signals")
    out["fast"]["one_line"] = hook.one_line(a)
    out["second_call_cache"] = b["cache"]
    out["lab_result_unchanged"] = json.dumps({k: r[k] for k in ("score", "status", "report_md")}, sort_keys=True, default=str) == lab_before
    out["stale_rerun"] = assess.attach(r, pol, con=con, now=t_obs + 3 * 3600)["state"]
    d = assess.run_deep(con, a["request_key"])
    out["deep"] = {k: d.get(k) for k in ("state", "tier", "reason", "per_strategy", "wall_s")}
    obs = {"chain": "solana", "mint": PAID, "origin_group": "manual:p13-demo", "content_hash": "manual-1", "available_at": a["as_of"] + 900,
           "mint_verified": True, "claim_type": "MANUAL_OBSERVATION", "source_status": "OK"}
    out["catalyst"] = {"manual_observation": assess.on_catalyst(con, obs, a)["action"],
                       "same_again": assess.on_catalyst(con, obs, a)["action"],
                       "ticker_only": assess.on_catalyst(con, dict(obs, content_hash="manual-2", mint_verified=False), a)["action"],
                       "robot_outage": assess.on_catalyst(con, dict(obs, content_hash="manual-3", source_status="SOURCE_BLOCKED"), a)["action"],
                       "stale": assess.on_catalyst(con, dict(obs, content_hash="manual-4", available_at=a["as_of"] - 60), a)["action"]}
    walls = []
    for i in range(20):                                   # distinct snapshots force cache misses
        v = copy.deepcopy(r)
        v["bundle"]["market"]["price_usd"] = v["bundle"]["market"]["price_usd"] * (1 + (i + 1) / 1000)
        t0 = time.time()
        x = assess.attach(v, pol, con=con, now=now)
        walls.append((time.time() - t0) * 1000)
        assert x["cache"] == "MISS"
    out["benchmark_fast_ms"] = {"n": len(walls), "median": round(statistics.median(walls), 1), "max": round(max(walls), 1)}
    out["stats"] = assess.stats(con)
    con.close()
p = Path(__file__).with_name("p13_demo.json")
p.write_text(json.dumps(out, indent=1, default=str))
print(json.dumps({k: out[k] for k in ("fast", "second_call_cache", "lab_result_unchanged", "stale_rerun", "deep", "catalyst", "benchmark_fast_ms")}, indent=1, default=str)[:4000])
