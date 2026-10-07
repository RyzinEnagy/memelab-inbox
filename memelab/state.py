"""Portable state for fresh-session runs.

The sandbox is rebuilt from the public repo on every scheduled run, so the SQLite database that ships with the repo
is stale by the time a run starts. This module exports the continuity tables (tokens, watchlist, theses, rejections,
latest market snapshot per token) to data/state/latest.json, and imports such a file back into the database.
Only public market data and the lab's own status fields are included. No keys, no wallets.

  python -m memelab.state export [path]        -> data/state/latest.json
  python -m memelab.state import <path-or-url>  -> merges into data/memelab.sqlite (idempotent)
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from . import db

STATE_DIR = db.DATA_DIR / "state"
DEFAULT_PATH = STATE_DIR / "latest.json"
THESES_PER_MINT = 6
VERSION = 1


def _rows(con, sql, args=()):
    return [dict(r) for r in con.execute(sql, args).fetchall()]


def export(path: Path | None = None) -> Path:
    path = Path(path) if path else DEFAULT_PATH
    db.init_db()
    with db.connect() as con:
        tokens = _rows(con, "SELECT * FROM tokens")
        watchlist = _rows(con, "SELECT * FROM watchlist")
        rejections = _rows(con, "SELECT * FROM rejections")
        theses = []
        for t in tokens:
            theses += _rows(con, "SELECT * FROM theses WHERE mint=? ORDER BY created_at DESC LIMIT ?", (t["mint"], THESES_PER_MINT))
        market = []
        for t in tokens:
            r = db.latest(con, "market_snapshots", t["mint"])
            if r:
                market.append(dict(r))
        pools = _rows(con, "SELECT * FROM pools")
    for th in theses:
        th.pop("id", None)
    for r in rejections:
        r.pop("id", None)
    for m in market:
        m.pop("id", None)
    out = {"_version": VERSION, "_exported_at": time.time(), "tokens": tokens, "pools": pools, "watchlist": watchlist,
           "theses": theses, "rejections": rejections, "market_snapshots": market}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, separators=(",", ":"), default=str))
    print(f"exported {len(tokens)} tokens, {len(watchlist)} watchlist, {len(theses)} theses, {len(rejections)} rejections -> {path}")
    return path


def _load(src: str) -> dict:
    if src.startswith("http://") or src.startswith("https://"):
        r = subprocess.run(["curl", "-sS", "-L", "--max-time", "30", "-w", "\n%{http_code}", src], capture_output=True, text=True)
        body, _, code = r.stdout.rpartition("\n")
        if code != "200":
            sys.exit(f"fetch failed ({code}) for {src}")
        return json.loads(body)
    return json.loads(Path(src).read_text())


def _insert_if_absent(con, table: str, row: dict, key_cols: tuple[str, ...]) -> bool:
    where = " AND ".join(f"{k}=?" for k in key_cols)
    if con.execute(f"SELECT 1 FROM {table} WHERE {where}", [row[k] for k in key_cols]).fetchone():
        return False
    db.insert(con, table, row)
    return True


def import_state(src: str) -> None:
    data = _load(src)
    db.init_db()
    n = {"tokens": 0, "pools": 0, "theses": 0, "rejections": 0, "market": 0}
    with db.connect() as con:
        for t in data.get("tokens", []):
            mint = t.pop("mint")
            t.pop("first_seen_at", None); t.pop("last_seen_at", None)
            db.upsert_token(con, mint, **t); n["tokens"] += 1
        for p in data.get("pools", []):
            n["pools"] += _insert_if_absent(con, "pools", p, ("pool_address",))
        for th in data.get("theses", []):
            n["theses"] += _insert_if_absent(con, "theses", th, ("mint", "created_at"))
        for r in data.get("rejections", []):
            n["rejections"] += _insert_if_absent(con, "rejections", r, ("mint", "rejected_at"))
        for m in data.get("market_snapshots", []):
            n["market"] += _insert_if_absent(con, "market_snapshots", m, ("mint", "observed_at", "source"))
        for w in data.get("watchlist", []):
            con.execute("INSERT INTO watchlist (mint, added_at, status, last_status_change, notes) VALUES (?,?,?,?,?) "
                        "ON CONFLICT(mint) DO UPDATE SET status=excluded.status, last_status_change=excluded.last_status_change, notes=excluded.notes "
                        "WHERE excluded.last_status_change >= watchlist.last_status_change",
                        (w["mint"], w.get("added_at"), w["status"], w.get("last_status_change"), w.get("notes")))
    exported = data.get("_exported_at")
    when = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(exported)) if exported else "unknown time"
    print(f"imported state from {when}: {n['tokens']} tokens, {n['pools']} new pools, {n['theses']} new theses, {n['rejections']} new rejections, {n['market']} new market snapshots, {len(data.get('watchlist', []))} watchlist rows")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ("export", "import"):
        sys.exit("usage: python -m memelab.state export [path] | import <path-or-url>")
    if argv[0] == "export":
        export(argv[1] if len(argv) > 1 else None)
    else:
        if len(argv) < 2:
            sys.exit("import needs a path or URL")
        import_state(argv[1])


if __name__ == "__main__":
    main()
