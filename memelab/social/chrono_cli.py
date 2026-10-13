"""CLI for the chronology: `python -m memelab social chrono <action> ...` (Phase 12).

  chrono run --input FILE [--policy JSON|FILE] [--save] [--json]                       order one input document (pure; nothing is fetched)
  chrono run --token CHAIN:CONTRACT --source ID --as-of T [--window-from T --window-to T]
             [--annotations FILE] [--policy ..] [--no-save] [--json]                     build the input from stored data, order it, store it
  chrono show RUN [--json]                                                             a stored run
  chrono verify RUN                                                                    recompute a stored run and compare hashes
  chrono flags [--token CHAIN:CONTRACT] [--category C] [--include-fixtures]             current flags (newest run per token and source)
  chrono status                                                                        counts

An indeterminate order or an empty timeline is an answer, so those exit 0. Exit codes: 0 done, 1 refused (message on stderr), 2 usage.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from .. import db
from . import chrono_core as C, chrono_store as S


def _out(o) -> None:
    print(json.dumps(o, indent=1, sort_keys=True, default=str))


def _load(txt):
    if not txt:
        return None
    p = Path(txt)
    return json.loads(p.read_text() if p.exists() else txt)


def _tracked(dbp: Path) -> bool:
    return dbp.resolve() == (db.DATA_DIR / "memelab.sqlite").resolve()


def _token(t: str) -> tuple[str, str]:
    if not t or ":" not in t:
        raise ValueError("--token must be CHAIN:CONTRACT (a symbol is never an identity)")
    ch, c = t.split(":", 1)
    return ch, c


def cmd_chrono(a):
    c = a.c_cmd
    file_run = c == "run" and getattr(a, "input", None)
    needs_db = not (file_run and not getattr(a, "save", False))
    write = c == "run" and (getattr(a, "save", False) or (not getattr(a, "input", None) and not a.no_save))
    dbp = Path(a.db) if a.db else db.DB_PATH
    fixture = False
    if file_run:
        try:
            fixture = bool(json.loads(Path(a.input).read_text()).get("is_fixture"))
        except (OSError, ValueError, AttributeError):
            fixture = False
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
            if not con.execute("SELECT 1 FROM sqlite_master WHERE name='social_chrono_runs'").fetchone():
                raise ValueError("chronology tables not found; run social schema migrate")
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
    c = a.c_cmd
    if c == "run":
        pol = _load(a.policy)
        if a.input:
            doc = json.loads(Path(a.input).read_text())
        else:
            if a.as_of is None or not a.token or not a.source:
                raise ValueError("--token, --source and --as-of are required when running from stored data")
            ch, ct = _token(a.token)
            win = {"from": a.window_from, "to": a.window_to} if a.window_from is not None and a.window_to is not None else None
            doc = S.build_input(con, chain=ch, contract=ct, source_id=a.source, as_of=a.as_of, window=win, annotations=_load(a.annotations))
        res = C.analyze(doc, pol)
        saved = S.save_run(con, doc, res, now=a.now) if (con is not None and (a.save or not a.input) and not a.no_save) else None
        if a.json:
            return {"saved": saved, "result": res}
        return C.report(res) + (f"\nStored as run {saved['run_id']} ({'new' if saved['created'] else 'already stored'}), " if saved else "\n") + \
            f"result sha256 {res['result_sha256'][:16]}.."
    if c == "show":
        r = S.load_run(con, a.run)
        return r["result"] if a.json else C.report(r["result"])
    if c == "verify":
        return S.verify_run(con, a.run)
    if c == "flags":
        ch, ct = _token(a.token) if a.token else (None, None)
        return S.current_flags(con, chain=ch, contract=ct, category=a.category, include_fixtures=a.include_fixtures)
    if c == "status":
        return S.status(con)
    raise ValueError(f"unknown action {c}")


def add_parser(ssp) -> None:
    p = ssp.add_parser("chrono", help="order a source's posts against associated-wallet activity and market moves (Phase 12)")
    sub = p.add_subparsers(dest="c_cmd", required=True)

    def common(q):
        q.add_argument("--db"); q.add_argument("--now", type=float, help="fixed clock (epoch seconds)")
        q.set_defaults(fn=cmd_chrono)
        return q

    q = common(sub.add_parser("run", help="order an input file or stored data"))
    q.add_argument("--input"); q.add_argument("--token"); q.add_argument("--source"); q.add_argument("--as-of", type=float)
    q.add_argument("--window-from", type=float); q.add_argument("--window-to", type=float)
    q.add_argument("--annotations"); q.add_argument("--policy")
    q.add_argument("--save", action="store_true"); q.add_argument("--no-save", action="store_true"); q.add_argument("--json", action="store_true")
    q = common(sub.add_parser("show", help="a stored run")); q.add_argument("run", type=int); q.add_argument("--json", action="store_true")
    q = common(sub.add_parser("verify", help="recompute a stored run and compare hashes")); q.add_argument("run", type=int)
    q = common(sub.add_parser("flags", help="current flags, newest run per token and source"))
    q.add_argument("--token"); q.add_argument("--category"); q.add_argument("--include-fixtures", action="store_true")
    common(sub.add_parser("status", help="counts"))
