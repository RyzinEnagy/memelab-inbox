"""Phase 16 concurrency burst and blocked-provider checks, on COPIES of the research corpus only.
Usage: python3 audits/backtesting/testing/p16_concurrency.py <scratch dir holding a copy named bt.sqlite>
Bursts (each worker is a separate process released at the same instant):
  A  fresh database: 8 processes open a brand-new bt.sqlite at once (schema migration race)
  B  assessment burst: 8 processes assess the same real PAID analysis + 4 with distinct snapshots, one corpus copy
  C  tracker burst: 3 processes run outcomes.track over the whole universe at once, one corpus copy
  D  runner burst: 3 processes run the same strategy run at once, one corpus copy
Blocked provider (real PAID inbox captures with the quote / bar / price bodies removed): assessment + report."""
from __future__ import annotations

import copy
import json
import multiprocessing as mp
import shutil
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

PAID = "98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump"
IDS = ["disc01", "s2_01", "deep01a"]


def paid_result(drop_prefixes=()):
    from memelab import pipeline
    from memelab.bridge import ingest
    res = [ingest.load_result(ROOT / "data" / "inbox" / f"{i}.result.json") for i in IDS]
    bodies = {k: v[0] for k, v in ingest.merged_bodies(res).items()}
    bodies = {k: v for k, v in bodies.items() if not any(k.startswith(p) for p in drop_prefixes)}
    t_obs = max(r.observed_at for r in res)
    return pipeline.analyze_token(PAID, bodies, observed_at=t_obs, sol_price=120.8, persist=False), t_obs


def _wait(start_at):
    while time.time() < start_at:
        time.sleep(0.001)


def w_fresh(db, start_at, q):
    from memelab.backtest import store
    _wait(start_at)
    try:
        con = store.connect(db)
        n = con.execute("SELECT COUNT(*) FROM bt_schema_migrations").fetchone()[0]
        con.close()
        q.put(("A", "OK", n))
    except Exception as e:
        q.put(("A", "ERROR", f"{type(e).__name__}: {e}"))


def w_assess(db, start_at, q, k):
    from memelab.backtest import assess, store
    r, t_obs = paid_result()
    if k >= 8:
        r = copy.deepcopy(r)
        r["bundle"]["market"]["price_usd"] *= 1 + k / 1000
    pol = dict(assess.DEFAULT_POLICY, enabled=True)
    _wait(start_at)
    t0 = time.time()
    try:
        con = store.connect(db)
        a = assess.attach(r, pol, con=con, now=t_obs + 60)
        con.close()
        q.put(("B", "OK", {"k": k, "state": a.get("state"), "cache": a.get("cache"), "key": a.get("request_key"), "error": a.get("error"), "wall_s": round(time.time() - t0, 2)}))
    except Exception as e:
        q.put(("B", "ERROR", {"k": k, "error": f"{type(e).__name__}: {e}", "wall_s": round(time.time() - t0, 2)}))


def w_track(db, start_at, q, k, now):
    from memelab.backtest import outcomes as O, store
    _wait(start_at)
    t0 = time.time()
    try:
        con = store.connect(db)
        r = O.track(con, now=now, observed_asof=now)
        con.close()
        q.put(("C", "OK", {"k": k, "status": r.get("status"), "new_rows": r.get("new_rows"), "wall_s": round(time.time() - t0, 1)}))
    except Exception as e:
        q.put(("C", "ERROR", {"k": k, "error": f"{type(e).__name__}: {e}", "wall_s": round(time.time() - t0, 1)}))


def w_run(db, start_at, q, k, runs_dir):
    from memelab.backtest import runner, store
    runner.RUNS_DIR = Path(runs_dir)          # keep run files out of data/backtest/runs
    _wait(start_at)
    t0 = time.time()
    try:
        con = store.connect(db)
        r = runner.run(con, "BREAKOUT_CLOSE")
        con.close()
        q.put(("D", "OK", {"k": k, "run_id": r.get("run_id"), "cache": r.get("cache"), "ledger_hash": r.get("ledger_hash"), "wall_s": round(time.time() - t0, 1)}))
    except Exception as e:
        q.put(("D", "ERROR", {"k": k, "error": f"{type(e).__name__}: {e}", "wall_s": round(time.time() - t0, 1)}))


def burst(target, args_list, lead=3.0):
    q = mp.Queue()
    start_at = time.time() + lead
    ps = [mp.Process(target=target, args=(*a[:1], start_at, q, *a[1:])) for a in args_list]
    for p in ps:
        p.start()
    out = [q.get(timeout=900) for _ in ps]
    for p in ps:
        p.join(timeout=60)
    return out


def main(scratch: Path):
    import sqlite3
    from memelab.backtest import assess, report, store
    src = scratch / "bt.sqlite"
    assert src.resolve() != (ROOT / "data" / "backtest" / "bt.sqlite").resolve()
    out = {}
    # A: fresh database migration race
    fresh = scratch / "fresh" / "bt.sqlite"
    fresh.parent.mkdir(exist_ok=True)
    if fresh.exists():
        fresh.unlink()
    out["A_fresh_db_race"] = burst(w_fresh, [(str(fresh),) for _ in range(8)], lead=4.0)
    c = sqlite3.connect(fresh)
    out["A_migration_rows"] = c.execute("SELECT COUNT(*) FROM bt_schema_migrations").fetchone()[0]
    c.close()
    # B: assessment burst on one corpus copy
    dbB = scratch / "B" / "bt.sqlite"
    dbB.parent.mkdir(exist_ok=True)
    shutil.copy(src, dbB)
    out["B_assess_burst"] = burst(w_assess, [(str(dbB), k) for k in range(12)], lead=25.0)
    c = sqlite3.connect(dbB)
    out["B_fast_rows"] = c.execute("SELECT COUNT(*), COUNT(DISTINCT request_key) FROM bt_assessments WHERE stage='FAST'").fetchone()
    out["B_dup_keys"] = c.execute("SELECT COUNT(*) FROM (SELECT request_key FROM bt_assessments GROUP BY request_key, stage HAVING COUNT(*)>1)").fetchone()[0]
    out["B_events"] = dict(c.execute("SELECT event, COUNT(*) FROM bt_assessment_events GROUP BY event").fetchall())
    c.close()
    # C: tracker burst
    dbC = scratch / "C" / "bt.sqlite"
    dbC.parent.mkdir(exist_ok=True)
    shutil.copy(src, dbC)
    c = sqlite3.connect(dbC)
    now = c.execute("SELECT MAX(available_at) FROM bt_market_bars").fetchone()[0]
    c.close()
    out["C_track_burst"] = burst(w_track, [(str(dbC), k, now) for k in range(3)], lead=5.0)
    c = sqlite3.connect(dbC)
    out["C_outcome_rows"] = c.execute("SELECT COUNT(*), COUNT(DISTINCT opportunity_id || ':' || horizon_s) FROM bt_outcomes").fetchone()
    out["C_dup_windows"] = c.execute("SELECT COUNT(*) FROM (SELECT opportunity_id, horizon_s FROM bt_outcomes GROUP BY 1, 2 HAVING COUNT(*)>1)").fetchone()[0]
    out["C_track_run_events"] = c.execute("SELECT COUNT(*) FROM bt_assessment_events WHERE event='OUTCOME_TRACK_RUN'").fetchone()[0]
    c.close()
    # D: runner burst
    dbD = scratch / "D" / "bt.sqlite"
    dbD.parent.mkdir(exist_ok=True)
    shutil.copy(src, dbD)
    out["D_run_burst"] = burst(w_run, [(str(dbD), k, str(scratch / "D" / "runs")) for k in range(3)], lead=5.0)
    c = sqlite3.connect(dbD)
    rid = next((x[2]["run_id"] for x in out["D_run_burst"] if x[1] == "OK"), None)
    out["D_result_rows_for_run"] = c.execute("SELECT COUNT(*), COUNT(DISTINCT result_hash) FROM bt_run_results WHERE run_id=?", (rid,)).fetchone() if rid else None
    out["D_ledger_hashes"] = sorted({x[2].get("ledger_hash") for x in out["D_run_burst"] if x[1] == "OK"})
    c.close()
    # blocked providers on the real PAID capture
    dbE = scratch / "E" / "bt.sqlite"
    dbE.parent.mkdir(exist_ok=True)
    shutil.copy(src, dbE)
    con = store.connect(dbE)
    pol = dict(assess.DEFAULT_POLICY, enabled=True)
    blocked = {}
    for name, drop in (("no_router_quotes", ("jq:",)), ("no_ohlcv", ("gt_ohlcv:",)), ("no_quotes_no_ohlcv_no_pools", ("jq:", "gt_ohlcv:", "gt_pools:", "gt_info:"))):
        try:
            r, t_obs = paid_result(drop)
            a = assess.attach(r, pol, con=con, now=t_obs + 60)
            doc = report.build(a, con=con)
            blocked[name] = {"lab_score": r["score"]["total"], "lab_status": r["status"]["status"], "state": a.get("state"), "tier": a.get("tier"),
                             "stress_decision": (a.get("stress") or {}).get("decision"), "label": doc["headline"]["label"],
                             "sell_quotes": a.get("sell_quotes"), "report_errors": report.validate(doc),
                             "token_kept": bool(doc["token"]["mint"]), "max_size": ((a.get("stress") or {}).get("max_size") or {}).get("max_size_usd"),
                             "base_proceeds": [(s["size_usd"], s.get("status"), s.get("proceeds_usd")) for s in (a.get("stress") or {}).get("scenarios", []) if s["scenario"] == "BASE"]}
        except Exception as e:
            blocked[name] = {"error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-600:]}
    out["E_blocked_provider"] = blocked
    con.close()
    return out


if __name__ == "__main__":
    mp.set_start_method("fork")
    print(json.dumps(main(Path(sys.argv[1])), indent=1, default=str))
