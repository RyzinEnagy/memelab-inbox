"""`python -m memelab backtest ...`: research commands for the backtesting package. Nothing here can trade."""
from __future__ import annotations

import argparse
import json
import sys
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


def cmd_run(a):
    from .engine import EngineConfig
    from . import runner
    cfg = EngineConfig(account_usd=a.account_usd, size_usd=a.size_usd, max_positions=a.max_positions, max_exposure_frac=a.max_exposure,
                       entry_impact_cap=a.entry_impact_cap, max_drawdown_frac=a.max_drawdown)
    con = _con(a)
    res = runner.run(con, a.strategy, params=json.loads(a.params) if a.params else None, cfg=cfg, universe_id=a.universe,
                     until=_ts(a.until), decide_from=_ts(a.decide_from), decide_until=_ts(a.decide_until), thesis_known_at=a.thesis_known_at,
                     mints=a.mints, label=a.label)
    summary = {k: res.get(k) for k in ("run_id", "cache", "dataset_hash", "tokens", "n_trades", "pnl_usd", "mean_ret", "mean_paper_ret_mid", "ledger_hash")}
    summary["counts"] = res.get("counts")
    summary["disclosure"] = "research backtest on historical data; not a forecast and not an instruction to trade"
    print(json.dumps(summary, indent=1, default=str))


def add_subparser(sp):
    p = sp.add_parser("backtest", help="research backtests and stress tests (no trading; separate data/backtest/bt.sqlite)")
    ssp = p.add_subparsers(dest="bcmd", required=True)
    q = ssp.add_parser("status", help="what the backtest database holds")
    q.add_argument("--db"); q.set_defaults(fn=cmd_status)
    q = ssp.add_parser("run", help="replay one strategy over the frozen discovery universe and save the run")
    q.add_argument("--strategy", required=True); q.add_argument("--params", help="JSON object of strategy parameters")
    q.add_argument("--universe", default="lab_state_history"); q.add_argument("--mints", nargs="*")
    q.add_argument("--until"); q.add_argument("--decide-from"); q.add_argument("--decide-until")
    q.add_argument("--thesis-known-at", choices=["created", "committed"], default="created")
    q.add_argument("--account-usd", type=float, default=10_000.0); q.add_argument("--size-usd", type=float, default=500.0)
    q.add_argument("--max-positions", type=int, default=5); q.add_argument("--max-exposure", type=float, default=0.5)
    q.add_argument("--entry-impact-cap", type=float, default=0.03); q.add_argument("--max-drawdown", type=float)
    q.add_argument("--label"); q.add_argument("--db"); q.set_defaults(fn=cmd_run)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="memelab-backtest")
    sp = ap.add_subparsers(dest="cmd", required=True)
    add_subparser(sp)
    a = ap.parse_args(["backtest", *(argv if argv is not None else sys.argv[1:])])
    a.fn(a)
