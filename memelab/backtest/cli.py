"""`python -m memelab backtest ...`: research commands for the backtesting package. Nothing here can trade."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timezone

from . import ENGINE_VERSION, store


def _ts(s: str | None) -> float | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()


def _con(a):
    return store.connect(a.db) if getattr(a, "db", None) else store.connect()


def cmd_status(a):
    con = _con(a)
    q = lambda sql: con.execute(sql).fetchone()[0]
    out = {"engine_version": ENGINE_VERSION, "db": str(a.db or store.BT_DB_PATH),
           "bars": q("SELECT COUNT(*) FROM bt_market_bars"), "mints_with_bars": q("SELECT COUNT(DISTINCT mint) FROM bt_market_bars"),
           "pools": q("SELECT COUNT(DISTINCT pool_address) FROM bt_pool_versions"), "universe_rows": q("SELECT COUNT(*) FROM bt_universe_members"),
           "captures": q("SELECT COUNT(*) FROM bt_capture_provenance"), "runs": q("SELECT COUNT(*) FROM bt_experiment_runs"),
           "results": q("SELECT COUNT(*) FROM bt_run_results"), "assessments": q("SELECT COUNT(*) FROM bt_assessments")}
    print(json.dumps(out, indent=1))


def _runs_dir(a):
    from pathlib import Path
    return (Path(a.db).parent / "runs") if getattr(a, "db", None) else (Path(store.BT_DB_PATH).parent / "runs")   # MEMELAB_BT_DB too (R3)


def cmd_run(a):
    from .engine import EngineConfig
    from . import runner
    runner.RUNS_DIR = _runs_dir(a)                       # run files live next to the database they belong to
    cfg = EngineConfig(account_usd=a.account_usd, size_usd=a.size_usd, max_positions=a.max_positions, max_exposure_frac=a.max_exposure,
                       entry_impact_cap=a.entry_impact_cap, max_drawdown_frac=a.max_drawdown)
    con = _con(a)
    if a.as_of and a.until and _ts(a.as_of) != _ts(a.until):
        sys.exit("--as-of and --until disagree; give one")
    res = runner.run(con, a.strategy, params=json.loads(a.params) if a.params else None, cfg=cfg, universe_id=a.universe,
                     until=_ts(a.as_of or a.until), decide_from=_ts(a.decide_from), decide_until=_ts(a.decide_until), thesis_known_at=a.thesis_known_at,
                     mints=a.mints, label=a.label)
    summary = {k: res.get(k) for k in ("run_id", "cache", "dataset_hash", "tokens", "n_trades", "pnl_usd", "mean_ret", "mean_paper_ret_mid", "ledger_hash")}
    summary["counts"] = res.get("counts")
    summary["disclosure"] = "research backtest on historical data; not a forecast and not an instruction to trade"
    print(json.dumps(summary, indent=1, default=str))


def cmd_deep(a):
    from . import assess
    con = _con(a)
    keys = assess.pending_deep(con)[: a.limit]
    out = [assess.run_deep(con, k) for k in keys]
    print(json.dumps({"processed": len(out), "results": [{k: r.get(k) for k in ("mint", "state", "tier", "wall_s", "cache")} for r in out]}, indent=1))


def cmd_assess_stats(a):
    from . import assess
    print(json.dumps(assess.stats(_con(a)), indent=1))


def _emit(doc: dict, as_json: bool):
    from . import report
    print(json.dumps(doc, indent=1, default=str) if as_json else report.render_md(doc))


def cmd_stress(a):
    """Explicit request: analyze the mint from saved results (no lab persistence), assess it now and print the report.
    Runs even when the scout policy is off, because the user asked for it by name."""
    from .. import cli as lab_cli, db, pipeline
    from . import assess, report
    bodies, t = lab_cli._bodies(a.results)
    s1 = json.loads((lab_cli.INBOX / f"{a.stage1}.stage1.json").read_text()) if a.stage1 else {}
    sol = s1.get("sol_price") or lab_cli._sol_price(bodies)
    r = pipeline.analyze_token(a.mint, bodies, observed_at=t, sol_price=sol, persist=False)
    pol = dict(assess.load_policy(), enabled=True)
    if a.position_usd:
        pol["sizes_usd"] = sorted(set(a.position_usd))
    if a.max_loss_usd is not None:
        pol["max_loss_usd"] = a.max_loss_usd
    con = _con(a)
    asmt = assess.attach(r, pol, con=con, now=_ts(a.now) if a.now else None)
    doc = report.build(asmt, con=con, lab_db=db.DB_PATH)
    _emit(doc, a.json)


def cmd_assess(a):
    from .. import db
    from . import hook, report
    con = _con(a)
    asmt = hook.latest_assessment(a.chain, a.mint, con)
    deep = None
    if asmt:
        row = con.execute("SELECT result_json FROM bt_assessments WHERE request_key=? AND stage='DEEP'", (asmt["request_key"],)).fetchone()
        deep = json.loads(row[0]) if row else None
    doc = report.build(asmt, con=con, deep=deep, lab={"chain": a.chain, "mint": a.mint}, lab_db=db.DB_PATH)
    _emit(doc, a.json)


def cmd_inspect(a):
    con = _con(a)
    rows = con.execute("SELECT e.*, r.result_json, r.result_hash, r.status FROM bt_experiment_runs e JOIN bt_run_results r ON r.run_id=e.run_id "
                       "WHERE e.run_id LIKE ? ORDER BY r.created_at", (a.run_id + "%",)).fetchall()
    ids = sorted({x["run_id"] for x in rows})
    if len(ids) != 1:
        sys.exit(f"{len(ids)} runs match {a.run_id!r}; give more of the id")
    x = rows[0]
    cfg, res = json.loads(x["config_json"]), json.loads(x["result_json"])
    args = ["python -m memelab backtest run", f"--strategy {cfg['strategy_id']}"]
    if cfg.get("params"):
        args.append("--params '" + json.dumps(cfg["params"], sort_keys=True) + "'")
    if cfg.get("until"):
        args.append("--as-of " + datetime.fromtimestamp(cfg["until"], timezone.utc).isoformat().replace("+00:00", "Z"))
    for k, flag in (("decide_from", "--decide-from"), ("decide_until", "--decide-until")):
        if cfg.get(k):
            args.append(f"{flag} " + datetime.fromtimestamp(cfg[k], timezone.utc).isoformat().replace("+00:00", "Z"))
    if cfg.get("mints"):
        args.append("--mints " + " ".join(cfg["mints"]))
    if cfg.get("thesis_known_at") and cfg["thesis_known_at"] != "created":
        args.append(f"--thesis-known-at {cfg['thesis_known_at']}")
    if cfg.get("label"):
        args.append(f"--label {cfg['label']}")
    out = {"run_id": x["run_id"], "status": x["status"], "strategy": cfg["strategy_id"], "strategy_version": x["strategy_version"],
           "engine_version": x["engine_version"], "cost_model_version": x["cost_model_version"], "code_sha": x["code_sha"], "dataset_hash": x["dataset_hash"],
           "result_hash": x["result_hash"], "ledger_hash": res.get("ledger_hash"), "config": cfg,
           "summary": {k: res.get(k) for k in ("tokens", "n_trades", "pnl_usd", "mean_ret", "mean_paper_ret_mid", "counts", "wall_s")},
           "files": [str(p) for p in sorted((_runs_dir(a) / x["run_id"]).glob("*"))],
           "reproduce": " ".join(args) + "  (same code and data give the same run id and a cache HIT; changed code or data give a new id)",
           "disclosure": "research backtest on historical data; not a forecast and not an instruction to trade"}
    if a.json:
        print(json.dumps(out, indent=1, default=str))
    else:
        s = out["summary"]
        print(f"run {out['run_id']} ({out['status']}): {out['strategy']} v{out['strategy_version']}, engine {out['engine_version']}, cost model {out['cost_model_version']}")
        print(f"code {out['code_sha']}, dataset {out['dataset_hash']}, result {out['result_hash']}, ledger {out['ledger_hash']}")
        print(f"{s['tokens']} tokens, {s['n_trades']} trades, mean net {s['mean_ret']}, mean paper {s['mean_paper_ret_mid']}, counts {s['counts']}")
        print("files: " + (", ".join(out["files"]) or "none on this machine"))
        print("reproduce: " + out["reproduce"])
        print(out["disclosure"])


def cmd_data(a):
    from . import report
    print(json.dumps(report.coverage(_con(a)), indent=1))


def cmd_outcomes(a):
    """Shadow outcome tracking and calibration. Nothing here can trade or change a stored run, assessment or strategy."""
    import time as _t
    from . import outcomes as O
    con = _con(a)
    now = _ts(a.now) if a.now else _t.time()
    asof = _ts(a.asof) if a.asof else None
    if a.action == "track":
        out = O.track(con, now=now, observed_asof=asof, min_interval_s=a.min_interval)
    elif a.action == "calibrate":
        cats = None
        if a.with_launches:
            from .sources import lab_events
            cats = lab_events.launch_catalysts(store.ROOT)
        out = O.calibrate(con, asof=asof, horizon_s=int(a.horizon_h * 3600), catalysts=cats)
        if not a.json:
            print(O.render_calibration(out))
            return
    elif a.action == "drift":
        out = O.drift(con, now=now)
    elif a.action == "reconcile":
        out = O.exit_reconciliation(con, horizon_s=int(a.horizon_h * 3600))
        out.pop("rows", None)
    elif a.action == "daily":
        if not a.day:
            sys.exit("--day YYYY-MM-DD is required")
        print(O.daily_report(con, a.day, asof if asof is not None else now, horizon_s=int(a.horizon_h * 3600)), end="")
        return
    elif a.action == "shadow":
        if not (a.strategy and a.since):
            sys.exit("--strategy and --since are required")
        out = O.shadow(con, a.strategy, since=_ts(a.since), until=asof)
    print(json.dumps(out, indent=1, default=str))


def cmd_refresh(a):
    """Network, read-only: fetch new hourly bars from GeckoTerminal for windows waiting on a refresh (or --mints)."""
    from . import outcomes as O
    from .sources import gecko
    con = _con(a)
    store.RAW_DIR = (Path(a.db).parent / "raw") if a.db else store.RAW_DIR
    out = O.refresh(con, gecko.Budget(max_calls=a.max_calls, min_spacing_s=a.spacing), mints=a.mints)
    print(json.dumps(out, indent=1, default=str))


def cmd_depth(a):
    """Forward depth collector (D-BT-034). `collect` is NETWORK (read-only, budgeted): GeckoTerminal pool reads and, on
    Solana, keyless Jupiter sell quotes for the lab's decisions of the last 24 h. `status` reads the database only."""
    import time as _t
    from . import depth
    con = _con(a)
    now = _ts(a.now) if a.now else _t.time()
    if a.action == "status":
        out = depth.status(con, now=now, hours=a.hours)
        print(json.dumps(out, indent=1, default=str))
        return
    store.RAW_DIR = (Path(a.db).parent / "raw") if a.db else store.RAW_DIR
    exports = None
    if a.repo:
        try:
            exports = depth.export_decisions(a.repo, a.ref, now=now)
        except Exception as e:                       # lab exports not readable: collect for stored decisions only
            exports = {"status": f"EXPORTS_UNREADABLE: {type(e).__name__}", "decisions": []}
    out = depth.collect(con, exports=exports, now=None if not a.now else now, gt_max_calls=a.max_gt_calls, jup_max_calls=a.max_quote_calls,
                        gt_spacing_s=a.gt_spacing, jup_spacing_s=a.quote_spacing, deadline_s=a.deadline,
                        gt_prior_calls=a.gt_prior_calls, gt_prior_end=a.gt_prior_end)
    print(json.dumps(out, indent=1, default=str))


def cmd_backup(a):
    """Consistent copy of the live research database (sqlite backup API; includes what is still in the WAL file)."""
    from . import schema
    src = a.db or store.BT_DB_PATH
    dest = schema.backup_db(src, a.to)
    con = sqlite3.connect(f"file:{dest}?mode=ro", uri=True)
    n = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("bt_market_bars", "bt_universe_members", "bt_assessments", "bt_outcomes")}
    con.close()
    print(json.dumps({"backup": str(dest), "rows": n}, indent=1))


def cmd_schema(a):
    from . import report
    print(json.dumps(report.json_schema(), indent=1))


def add_subparser(sp):
    p = sp.add_parser("backtest", help="research backtests and stress tests (no trading; separate data/backtest/bt.sqlite)")
    ssp = p.add_subparsers(dest="bcmd", required=True)
    q = ssp.add_parser("status", help="what the backtest database holds")
    q.add_argument("--db"); q.set_defaults(fn=cmd_status)
    q = ssp.add_parser("run", help="replay one strategy over the frozen discovery universe and save the run")
    q.add_argument("--strategy", required=True); q.add_argument("--params", help="JSON object of strategy parameters")
    q.add_argument("--universe", default="lab_state_history"); q.add_argument("--mints", nargs="*")
    q.add_argument("--until"); q.add_argument("--as-of", help="same as --until: nothing after this UTC time is read"); q.add_argument("--decide-from"); q.add_argument("--decide-until")
    q.add_argument("--thesis-known-at", choices=["created", "committed"], default="created")
    q.add_argument("--account-usd", type=float, default=10_000.0); q.add_argument("--size-usd", type=float, default=500.0)
    q.add_argument("--max-positions", type=int, default=5); q.add_argument("--max-exposure", type=float, default=0.5)
    q.add_argument("--entry-impact-cap", type=float, default=0.03); q.add_argument("--max-drawdown", type=float)
    q.add_argument("--label"); q.add_argument("--db"); q.set_defaults(fn=cmd_run)
    q = ssp.add_parser("deep", help="run queued DEEP assessments (offline, bounded)")
    q.add_argument("--limit", type=int, default=20); q.add_argument("--db"); q.set_defaults(fn=cmd_deep)
    q = ssp.add_parser("assess-stats", help="assessment counts, states and average wall time")
    q.add_argument("--db"); q.set_defaults(fn=cmd_assess_stats)
    q = ssp.add_parser("stress", help="analyze one mint from saved results, assess it now and print the report (no lab persistence)")
    q.add_argument("mint"); q.add_argument("--results", nargs="+", required=True); q.add_argument("--stage1")
    q.add_argument("--position-usd", type=float, nargs="+", help="sizes to stress (default: policy sizes)"); q.add_argument("--max-loss-usd", type=float)
    q.add_argument("--now", help="UTC time to judge freshness against (default: now)"); q.add_argument("--json", action="store_true"); q.add_argument("--db")
    q.set_defaults(fn=cmd_stress)
    q = ssp.add_parser("assess", help="report for the newest stored assessment of a mint")
    q.add_argument("mint"); q.add_argument("--chain", default="solana"); q.add_argument("--json", action="store_true"); q.add_argument("--db"); q.set_defaults(fn=cmd_assess)
    q = ssp.add_parser("inspect", help="one stored run: config, hashes, summary, files and the command that reproduces it")
    q.add_argument("run_id", help="run id or a unique prefix"); q.add_argument("--json", action="store_true"); q.add_argument("--db"); q.set_defaults(fn=cmd_inspect)
    q = ssp.add_parser("data", help="coverage of the research database (bars, universe, blocked sources)")
    q.add_argument("--db"); q.set_defaults(fn=cmd_data)
    q = ssp.add_parser("outcomes", help="shadow outcome tracking: track, calibrate, drift, reconcile, daily, shadow (no trading)")
    q.add_argument("action", choices=["track", "calibrate", "drift", "reconcile", "daily", "shadow"])
    q.add_argument("--now", help="UTC time of this run (default: now)"); q.add_argument("--asof", help="only data available at this UTC time")
    q.add_argument("--horizon-h", type=float, default=24.0); q.add_argument("--min-interval", type=float, default=3600.0)
    q.add_argument("--day", help="YYYY-MM-DD for the daily report"); q.add_argument("--strategy"); q.add_argument("--since")
    q.add_argument("--with-launches", action="store_true", help="segment by the lab's launch-monitor records (reads git history)")
    q.add_argument("--json", action="store_true"); q.add_argument("--db"); q.set_defaults(fn=cmd_outcomes)
    q = ssp.add_parser("refresh", help="NETWORK (read-only): fetch new hourly bars for windows waiting on a refresh, within a call budget")
    q.add_argument("--mints", nargs="*"); q.add_argument("--max-calls", type=int, default=20); q.add_argument("--spacing", type=float, default=3.0)
    q.add_argument("--db"); q.set_defaults(fn=cmd_refresh)
    q = ssp.add_parser("depth", help="forward depth collector: collect (NETWORK, read-only, budgeted) or status")
    q.add_argument("action", choices=["collect", "status"])
    q.add_argument("--repo", help="git repository holding the lab's state exports (a shallow fetch of main is enough)")
    q.add_argument("--ref", default="refs/remotes/origin/main"); q.add_argument("--now", help="UTC time of this run (default: now)")
    q.add_argument("--max-gt-calls", type=int, default=6); q.add_argument("--max-quote-calls", type=int, default=48)
    q.add_argument("--gt-spacing", type=float, default=10.0); q.add_argument("--quote-spacing", type=float, default=2.2)
    q.add_argument("--deadline", type=float, default=115.0, help="no call or retry starts after this many seconds")
    q.add_argument("--gt-prior-calls", type=int, default=0, help="GeckoTerminal calls the refresh step just made (count against 6 in 60 s)")
    q.add_argument("--gt-prior-end", type=float, help="UTC epoch seconds when that refresh step ended")
    q.add_argument("--hours", type=float, default=48.0, help="status: decisions exported in the last N hours")
    q.add_argument("--db"); q.set_defaults(fn=cmd_depth)
    q = ssp.add_parser("backup", help="consistent copy of the research database while it may be in use")
    q.add_argument("--to", required=True); q.add_argument("--db"); q.set_defaults(fn=cmd_backup)
    q = ssp.add_parser("schema", help="JSON Schema of the report document")
    q.set_defaults(fn=cmd_schema)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="memelab-backtest")
    sp = ap.add_subparsers(dest="cmd", required=True)
    add_subparser(sp)
    a = ap.parse_args(["backtest", *(argv if argv is not None else sys.argv[1:])])
    a.fn(a)
