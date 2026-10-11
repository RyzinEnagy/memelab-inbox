"""CLI for social ingestion (wired into `python -m memelab social ...`).

  social ingest --results <id> [<id> ...]     bridge result files data/inbox/<id>.result.json
  social ingest --file <path> [<path> ...]    any bridge result file (e.g. a fixture)
  social ingest --pull inbox/<id>.json        pull from the hand-off repo first (github_inbox.pull), then ingest
  social status [--event <event_id>]          last runs, connector health, checkpoints, quarantine; or one event
  social guard [--root <repo>]                fail if a tracked file holds raw social content (content_guard.py)

Exit code 0 for OK or PARTIAL runs (a down connector is recorded, not fatal), 1 for FAILED, 2 for usage errors.
Output is a JSON summary on stdout; structured logs go to stderr as JSON lines.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from .. import db

INBOX = db.DATA_DIR / "inbox"


def _setup_logging(verbose: bool) -> None:
    lg = logging.getLogger("memelab.social.ingest")
    if not lg.handlers:
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(logging.Formatter("%(message)s"))
        lg.addHandler(h)
    lg.setLevel(logging.INFO if verbose else logging.WARNING)
    lg.propagate = False


def cmd_ingest(a):
    from . import ingest as I
    from .bridge_adapter import BridgeInboxAdapter
    _setup_logging(a.verbose)
    paths: list[Path] = [Path(f) for f in a.file or []] + [INBOX / f"{r}.result.json" for r in a.results or []]
    if a.pull:
        from ..bridge import github_inbox
        for rp in a.pull:
            paths.append(github_inbox.pull(rp, result_name=a.as_name if len(a.pull) == 1 else None, ref=a.ref))
    if not paths:
        print("give --results, --file or --pull", file=sys.stderr)
        raise SystemExit(2)
    dbp = Path(a.db) if a.db else db.DB_PATH
    db.init_db(dbp)
    budget = I.Budget(max_items=a.max_items, max_units=a.max_units)
    out = I.ingest(BridgeInboxAdapter(paths), dbp, now=a.now, run_id=a.run_id, batch_size=a.batch_size,
                   budget=budget, max_age_hours=a.max_age_hours)
    print(json.dumps(out, indent=1, sort_keys=True))
    raise SystemExit(1 if out["status"] == "FAILED" else 0)


def cmd_status(a):
    from .ingest import event_record
    dbp = Path(a.db) if a.db else db.DB_PATH
    with db.connect(dbp) as con:
        if a.event:
            rec = event_record(con, a.event)
            if rec is None:
                print(f"no event {a.event}", file=sys.stderr)
                raise SystemExit(1)
            print(json.dumps(rec, indent=1, sort_keys=True, default=str))
            return
        out = {
            "runs": [dict(r) for r in con.execute("SELECT run_id, adapter, started_at, status, counts_json FROM social_ingest_runs "
                                                  "ORDER BY started_at DESC, run_id DESC LIMIT ?", (a.limit,))],
            "connector_health": [dict(r) for r in con.execute(
                "SELECT h.connector, h.status, h.checked_at, h.items_seen, h.error FROM social_connector_health h "
                "WHERE h.checked_at = (SELECT MAX(checked_at) FROM social_connector_health WHERE connector=h.connector) ORDER BY h.connector")],
            "checkpoints": [dict(r) for r in con.execute("SELECT connector, source_ref, status, next_index, item_count, last_run_id "
                                                         "FROM social_ingest_checkpoints ORDER BY updated_at DESC LIMIT ?", (a.limit * 5,))],
            "quarantine_by_reason": {r[0]: r[1] for r in con.execute("SELECT reason_code, COUNT(*) FROM social_ingest_quarantine GROUP BY reason_code")},
            "events": con.execute("SELECT COUNT(*) FROM social_observation_provenance").fetchone()[0],
        }
    print(json.dumps(out, indent=1, sort_keys=True, default=str))


def cmd_guard(a):
    from .content_guard import scan
    root = Path(a.root) if a.root else db.ROOT
    out = scan(root)
    print(json.dumps(out, indent=1, sort_keys=True))
    raise SystemExit(1 if out["violations"] else 0)


def add_subparser(sp) -> None:
    p = sp.add_parser("social", help="Social intelligence: ingest bridge inbox observations, status")
    ssp = p.add_subparsers(dest="social_cmd", required=True)
    q = ssp.add_parser("ingest", help="ingest social units from bridge result files")
    q.add_argument("--results", nargs="+", help="result ids in data/inbox (<id>.result.json)")
    q.add_argument("--file", nargs="+", help="paths to bridge result files")
    q.add_argument("--pull", nargs="+", help="hand-off repo paths, e.g. inbox/soc_20261010.json (pulled first)")
    q.add_argument("--as", dest="as_name", help="result name for a single --pull")
    q.add_argument("--ref", help="git ref or commit SHA for --pull (avoids the raw.githubusercontent cache)")
    q.add_argument("--db", help="database path (default: MEMELAB_DB or data/memelab.sqlite)")
    q.add_argument("--batch-size", type=int, default=50)
    q.add_argument("--max-items", type=int, help="item budget for this run; the rest resumes next run")
    q.add_argument("--max-units", type=int, help="unit budget for this run")
    q.add_argument("--max-age-hours", type=float, default=12.0, help="older fetched_at is flagged STALE")
    q.add_argument("--run-id")
    q.add_argument("--now", type=float, help="fixed clock (epoch seconds), for replays and tests")
    q.add_argument("-v", "--verbose", action="store_true", help="info-level JSON logs on stderr")
    q.set_defaults(fn=cmd_ingest)
    q = ssp.add_parser("status", help="runs, connector health, checkpoints, quarantine counts")
    q.add_argument("--db")
    q.add_argument("--event", help="show everything stored for one event id")
    q.add_argument("--limit", type=int, default=10)
    q.set_defaults(fn=cmd_status)
    q = ssp.add_parser("guard", help="fail if a tracked file holds raw third-party social content")
    q.add_argument("--root", help="repo root (default: this checkout)")
    q.set_defaults(fn=cmd_guard)
