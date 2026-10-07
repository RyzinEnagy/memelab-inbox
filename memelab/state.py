"""Portable state for scheduled runs: export the rows that carry memory across sessions
(theses with their snapshots, entries, watchlist, rejections, tokens) to one JSON text file,
and import them into a fresh database without duplicating what is already there.

    python -m memelab.state export [path]      -> data/state/latest.json (default)
    python -m memelab.state import [path|url]  -> merges into data/memelab.sqlite

The file holds public market research only (no keys, no wallet data). It is small enough to
commit as text through the GitHub web editor, which is how the inbox repo receives it.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

from . import db

TABLES = ["tokens", "theses", "entries", "watchlist", "rejections", "chains", "chain_snapshots", "chain_scores", "regime_snapshots", "narratives", "narrative_snapshots", "benchmark_baskets", "ecosystem_alerts"]
KEYS = {"tokens": ("mint",), "theses": ("mint", "created_at"), "entries": ("thesis_id", "style", "zone_low"),
        "watchlist": ("mint",), "rejections": ("mint", "rejected_at", "stage"),
        "chains": ("chain_id",), "chain_snapshots": ("chain_id", "observed_at"), "chain_scores": ("chain_id", "observed_at"), "regime_snapshots": ("observed_at",),
        "narratives": ("narrative_id",), "narrative_snapshots": ("narrative_id", "observed_at"), "benchmark_baskets": ("observed_at", "bucket"), "ecosystem_alerts": ("alerted_at", "kind", "subject")}
DEFAULT = db.DATA_DIR / "state" / "latest.json"


def export(path: Path | str | None = None, keep_theses_per_mint: int = 12) -> Path:
    out = Path(path) if path else DEFAULT
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {"_exported_at": time.time(), "_tables": {}}
    with db.connect() as con:
        for t in TABLES:
            rows = [dict(r) for r in con.execute(f"SELECT * FROM {t}")]
            if t == "theses":
                by: dict[str, list] = {}
                for r in sorted(rows, key=lambda r: -(r["created_at"] or 0)):
                    by.setdefault(r["mint"], []).append(r)
                rows = [r for lst in by.values() for r in lst[:keep_theses_per_mint]]
            data["_tables"][t] = rows
    out.write_text(json.dumps(data, separators=(",", ":"), default=str))
    return out


def _load(src: str) -> dict:
    if src.startswith("http"):
        with urllib.request.urlopen(src, timeout=60) as r:
            return json.loads(r.read().decode())
    return json.loads(Path(src).read_text())


def import_(src: str | None = None) -> dict[str, int]:
    data = _load(str(src or DEFAULT))
    tables = data.get("_tables") or {}
    added = {}
    with db.connect() as con:
        thesis_id_map: dict[int, int] = {}
        for t in TABLES:
            n = 0
            for row in tables.get(t) or []:
                row = dict(row)
                old_id = row.pop("id", None)
                if t == "entries" and row.get("thesis_id") in thesis_id_map:
                    row["thesis_id"] = thesis_id_map[row["thesis_id"]]
                keys = KEYS[t]
                where = " AND ".join(f"{k} IS ?" for k in keys)
                hit = con.execute(f"SELECT rowid, * FROM {t} WHERE {where}", [row.get(k) for k in keys]).fetchone()
                if hit:
                    if t == "theses" and old_id is not None:
                        thesis_id_map[old_id] = hit["id"]
                    if t == "chains" and row.get("research_allocation"):  # the export is the continuity record; a fresh init only knows registry defaults
                        con.execute("UPDATE chains SET status=?, status_reason=?, research_allocation=?, updated_at=? WHERE chain_id=?",
                                    (row.get("status"), row.get("status_reason"), row.get("research_allocation"), row.get("updated_at"), row["chain_id"]))
                    if t == "watchlist" and (row.get("last_status_change") or 0) > (hit["last_status_change"] or 0):
                        con.execute("UPDATE watchlist SET status=?, last_status_change=?, notes=? WHERE mint=?",
                                    (row.get("status"), row.get("last_status_change"), row.get("notes"), row["mint"]))
                    continue
                cols = list(row)
                cur = con.execute(f"INSERT INTO {t} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", [row[c] for c in cols])
                if t == "theses" and old_id is not None:
                    thesis_id_map[old_id] = cur.lastrowid
                n += 1
            added[t] = n
    return added


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "export"
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    if cmd == "export":
        p = export(arg)
        print(p, p.stat().st_size, "bytes")
    elif cmd == "import":
        print(import_(arg))
    else:
        raise SystemExit("usage: python -m memelab.state export|import [path|url]")
