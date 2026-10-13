"""CLI for wallet performance accounting: `python -m memelab social perf <action> ...` (Phase 10).

  perf run --ledger FILE [--policy JSON|FILE] [--save] [--json]                      run a ledger document (pure; nothing is fetched)
  perf run --chain C --wallet A [--wallet B --group-reason R] [--as-of T]             run from stored Phase 09 events
           [--annotations FILE] [--policy JSON|FILE] [--no-save] [--json]
  perf prices import FILE --chain C [--fixture]                                       store supplied price observations and sell quotes
  perf meta set CHAIN ASSET --kind K --source S [--decimals N] [--alias-of A]         asset role and decimals
  perf show RUN [--json]                                                              a stored run
  perf verify RUN                                                                     recompute from the stored input and compare hashes
  perf rank [--ledger FILE ...]                                                       rank scored wallets; refuse the rest with reasons
  perf compare (--run N | --ledger FILE) --provider FILE                              compare a provider's figures (an estimate, never an input)
  perf status                                                                         counts

A refused score is an answer, so `perf run` exits 0 when it refuses. Exit codes: 0 done, 1 refused (message on stderr, nothing written), 2 usage.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from .. import db
from . import perf_analysis as PA, perf_core as C, perf_store as S


def _out(o) -> None:
    print(json.dumps(o, indent=1, sort_keys=True, default=str))


def _tracked(dbp: Path) -> bool:
    return dbp.resolve() == (db.DATA_DIR / "memelab.sqlite").resolve()


def _policy(txt):
    if not txt:
        return None
    p = Path(txt)
    return json.loads(p.read_text() if p.exists() else txt)


def _con(a, write: bool):
    dbp = Path(a.db) if a.db else db.DB_PATH
    if write:
        db.init_db(dbp)
    elif not dbp.exists():
        print(json.dumps({"error": "no database", "path": str(dbp)}), file=sys.stderr)
        raise SystemExit(1)
    con = sqlite3.connect(str(dbp))
    con.row_factory = sqlite3.Row
    if not con.execute("SELECT 1 FROM sqlite_master WHERE name='social_perf_runs'").fetchone():
        con.close()
        print(json.dumps({"error": "performance tables not found; run a perf write command or social schema migrate"}), file=sys.stderr)
        raise SystemExit(1)
    return con, dbp


def cmd_perf(a):
    c = a.p_cmd
    needs_db = not (c in ("run", "rank", "compare") and getattr(a, "ledger", None) and not getattr(a, "save", False)) and c != "meta-none"
    write = c in ("prices", "meta") or (c == "run" and (getattr(a, "save", False) or (not getattr(a, "ledger", None) and not a.no_save)))
    dbp = Path(a.db) if a.db else db.DB_PATH
    if write and _tracked(dbp) and (getattr(a, "fixture", False) or _is_fixture_input(a)):
        print(json.dumps({"error": "fixtures are never written to the tracked database; use --db"}), file=sys.stderr)
        raise SystemExit(1)
    con = None
    try:
        if needs_db:
            con, dbp = _con(a, write)
        res = _dispatch(a, con, dbp)
        if write and con is not None:
            con.commit()
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        if con is not None:
            con.rollback()
        print(json.dumps({"error": str(e).strip("'\"")}), file=sys.stderr)
        raise SystemExit(1)
    finally:
        if con is not None:
            con.close()
    if isinstance(res, str):
        print(res)
    elif res is not None:
        _out(res)
    raise SystemExit(0)


def _is_fixture_input(a) -> bool:
    f = getattr(a, "ledger", None)
    if not f:
        return False
    try:
        d = json.loads(Path(f).read_text())
        return str(d.get("label") or "").startswith("FIXTURE")
    except (OSError, ValueError, AttributeError):
        return False


def _dispatch(a, con, dbp):
    c = a.p_cmd
    if c == "run":
        pol = C.merge_policy(_policy(a.policy))
        if a.ledger:
            doc = json.loads(Path(a.ledger).read_text())
            res = PA.analyze(doc, pol)
            saved = S.save_run(con, doc, res, pol, now=a.now) if a.save else None
        else:
            r = S.run_wallet(con, a.chain, a.wallet, policy=pol, as_of=a.as_of, group_reason=a.group_reason,
                             annotations=json.loads(Path(a.annotations).read_text()) if a.annotations else None, save=not a.no_save, now=a.now)
            res, saved = r["result"], r.get("saved")
        if a.json:
            return {"saved": saved, "result": res}
        return PA.render_report(res) + (f"\nStored as run {saved['run_id']} ({'new' if saved['created'] else 'already stored'}), result sha256 {res['result_sha256'][:16]}.." if saved else f"\nresult sha256 {res['result_sha256'][:16]}..")
    if c == "prices":
        rows = json.loads(Path(a.file).read_text())
        rows = rows.get("prices", rows) if isinstance(rows, dict) else rows
        return S.put_prices(con, a.chain, rows, fixture=a.fixture, now=a.now)
    if c == "meta":
        return S.put_token_meta(con, a.chain, a.asset, kind=a.kind, source=a.source, alias_of=a.alias_of, symbol=a.symbol, decimals=a.decimals, fixture=a.fixture, now=a.now)
    if c == "show":
        r = S.load_run(con, a.run)
        return r["result"] if a.json else PA.render_report(r["result"])
    if c == "verify":
        return S.verify_run(con, a.run)
    if c == "rank":
        if a.ledger:
            results = [PA.analyze(json.loads(Path(f).read_text()), C.merge_policy(_policy(a.policy))) for f in a.ledger]
        else:
            results = S.latest_results(con)
        return PA.rank_wallets(results)
    if c == "compare":
        prov = json.loads(Path(a.provider).read_text())
        if a.ledger:
            res = PA.analyze(json.loads(Path(a.ledger).read_text()), C.merge_policy(_policy(a.policy)))
        else:
            res = S.load_run(con, a.run)["result"]
        return PA.compare_provider_estimates(res, prov)
    if c == "status":
        return {"runs": S.list_runs(con), "prices": con.execute("SELECT COUNT(*) FROM social_perf_prices").fetchone()[0],
                "token_meta": con.execute("SELECT COUNT(*) FROM social_perf_token_meta").fetchone()[0], "engine_version": C.VERSION}
    raise ValueError(f"unknown action {c}")


def add_parser(ssp) -> None:
    p = ssp.add_parser("perf", help="wallet-level performance accounting with reconciliation checks (Phase 10)")
    sub = p.add_subparsers(dest="p_cmd", required=True)

    def common(q):
        q.add_argument("--db"); q.add_argument("--now", type=float, help="fixed clock (epoch seconds)")
        q.set_defaults(fn=cmd_perf)
        return q

    q = common(sub.add_parser("run", help="compute performance from a ledger file or from stored wallet events"))
    q.add_argument("--ledger"); q.add_argument("--chain"); q.add_argument("--wallet", action="append"); q.add_argument("--group-reason")
    q.add_argument("--as-of", type=float); q.add_argument("--annotations"); q.add_argument("--policy", help="JSON or a file of policy overrides")
    q.add_argument("--save", action="store_true", help="with --ledger: also store the run"); q.add_argument("--no-save", action="store_true", help="with --wallet: do not store the run")
    q.add_argument("--json", action="store_true")
    pr = sub.add_parser("prices", help="supplied prices and sell quotes")
    ps = pr.add_subparsers(dest="pr_cmd", required=True)
    q = common(ps.add_parser("import")); q.set_defaults(p_cmd="prices")
    q.add_argument("file"); q.add_argument("--chain", required=True); q.add_argument("--fixture", action="store_true")
    mt = sub.add_parser("meta", help="asset role and decimals")
    ms = mt.add_subparsers(dest="m_cmd", required=True)
    q = common(ms.add_parser("set")); q.set_defaults(p_cmd="meta")
    q.add_argument("chain"); q.add_argument("asset"); q.add_argument("--kind", required=True, choices=["NATIVE", "STABLE", "TOKEN", "LP_RECEIPT"]); q.add_argument("--source", required=True)
    q.add_argument("--decimals", type=int); q.add_argument("--alias-of"); q.add_argument("--symbol"); q.add_argument("--fixture", action="store_true")
    q = common(sub.add_parser("show", help="a stored run")); q.add_argument("run", type=int); q.add_argument("--json", action="store_true")
    q = common(sub.add_parser("verify", help="recompute a stored run and compare hashes")); q.add_argument("run", type=int)
    q = common(sub.add_parser("rank", help="rank scored wallets, refuse the rest")); q.add_argument("--ledger", action="append"); q.add_argument("--policy")
    q = common(sub.add_parser("compare", help="compare a provider's figures with the ledger (estimate only)"))
    q.add_argument("--run", type=int); q.add_argument("--ledger"); q.add_argument("--provider", required=True); q.add_argument("--policy")
    common(sub.add_parser("status", help="counts"))
