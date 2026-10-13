"""CLI for Information Alpha: `python -m memelab social alpha <action> ...` (Phase 11).

  alpha run --input FILE [--policy JSON|FILE] [--save] [--json]          evaluate an input document (pure; nothing is fetched)
  alpha run --as-of T [--annotations FILE] [--policy ..] [--no-save]     evaluate stored claims against stored candles
  alpha series import FILE [--fixture]                                   store supplied historical candle series
  alpha show RUN [--json]                                                a stored run
  alpha verify RUN                                                       recompute a stored run and compare hashes
  alpha rank [--input FILE ...]                                          rank scored sources; decline the rest with reasons
  alpha status                                                           counts

Declining to score or rank is an answer, so those commands exit 0. Exit codes: 0 done, 1 refused (message on stderr), 2 usage.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from .. import db
from . import alpha_core as A, alpha_store as S


def _out(o) -> None:
    print(json.dumps(o, indent=1, sort_keys=True, default=str))


def _policy(txt):
    if not txt:
        return None
    p = Path(txt)
    return json.loads(p.read_text() if p.exists() else txt)


def _tracked(dbp: Path) -> bool:
    return dbp.resolve() == (db.DATA_DIR / "memelab.sqlite").resolve()


def _is_fixture_file(f) -> bool:
    try:
        return bool(json.loads(Path(f).read_text()).get("is_fixture"))
    except (OSError, ValueError, AttributeError):
        return False


def cmd_alpha(a):
    c = a.a_cmd
    file_run = c in ("run", "rank") and getattr(a, "input", None)
    needs_db = not (file_run and not getattr(a, "save", False))
    write = c == "series" or (c == "run" and (getattr(a, "save", False) or (not getattr(a, "input", None) and not a.no_save)))
    dbp = Path(a.db) if a.db else db.DB_PATH
    fixture = getattr(a, "fixture", False) or (c == "run" and getattr(a, "input", None) and _is_fixture_file(a.input))
    if write and _tracked(dbp) and fixture:
        print(json.dumps({"error": "fixtures are never written to the tracked database; use --db"}), file=sys.stderr)
        raise SystemExit(1)
    con = None
    try:
        if needs_db:
            if write:
                db.init_db(dbp)
            elif not dbp.exists():
                raise ValueError("no database")
            con = sqlite3.connect(str(dbp))
            con.row_factory = sqlite3.Row
            if not con.execute("SELECT 1 FROM sqlite_master WHERE name='social_alpha_runs'").fetchone():
                raise ValueError("alpha tables not found; run social schema migrate")
        res = _dispatch(a, con)
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


def _dispatch(a, con):
    c = a.a_cmd
    if c == "run":
        pol = _policy(a.policy)
        if a.input:
            doc = json.loads(Path(a.input).read_text())
        else:
            if a.as_of is None:
                raise ValueError("--as-of is required when running from stored claims")
            doc = S.build_input(con, as_of=a.as_of, annotations=json.loads(Path(a.annotations).read_text()) if a.annotations else None)
        res = A.analyze(doc, pol)
        saved = S.save_run(con, doc, res, res["policy"], now=a.now) if (con is not None and (a.save or not a.input) and not a.no_save) else None
        if a.json:
            return {"saved": saved, "result": res}
        return A.report(res) + (f"\nStored as run {saved['run_id']} ({'new' if saved['created'] else 'already stored'}), " if saved else "\n") + f"result sha256 {res['result_sha256'][:16]}.."
    if c == "series":
        data = json.loads(Path(a.file).read_text())
        data = data.get("series", data) if isinstance(data, dict) else data
        return S.put_series(con, data, fixture=a.fixture, now=a.now)
    if c == "show":
        r = S.load_run(con, a.run)
        return r["result"] if a.json else A.report(r["result"])
    if c == "verify":
        return S.verify_run(con, a.run)
    if c == "rank":
        if a.input:
            return A.rank(A.analyze(json.loads(Path(a.input[0]).read_text()), None))
        r = S.latest_result(con)
        if r is None:
            return {"ranked": [], "declined": [], "statement": "No stored run. Nothing to rank."}
        return r["ranking"]
    if c == "status":
        return S.status(con)
    raise ValueError(f"unknown action {c}")


def add_parser(ssp) -> None:
    p = ssp.add_parser("alpha", help="Information Alpha: predictive value of public posts against matched tokens (Phase 11)")
    sub = p.add_subparsers(dest="a_cmd", required=True)

    def common(q):
        q.add_argument("--db"); q.add_argument("--now", type=float, help="fixed clock (epoch seconds)")
        q.set_defaults(fn=cmd_alpha)
        return q

    q = common(sub.add_parser("run", help="evaluate an input file or stored claims"))
    q.add_argument("--input"); q.add_argument("--as-of", type=float); q.add_argument("--annotations"); q.add_argument("--policy")
    q.add_argument("--save", action="store_true"); q.add_argument("--no-save", action="store_true"); q.add_argument("--json", action="store_true")
    sr = sub.add_parser("series", help="supplied historical candles")
    ss = sr.add_subparsers(dest="s_cmd", required=True)
    q = common(ss.add_parser("import")); q.set_defaults(a_cmd="series")
    q.add_argument("file"); q.add_argument("--fixture", action="store_true")
    q = common(sub.add_parser("show", help="a stored run")); q.add_argument("run", type=int); q.add_argument("--json", action="store_true")
    q = common(sub.add_parser("verify", help="recompute a stored run and compare hashes")); q.add_argument("run", type=int)
    q = common(sub.add_parser("rank", help="rank scored sources, decline the rest")); q.add_argument("--input", action="append")
    common(sub.add_parser("status", help="counts"))
