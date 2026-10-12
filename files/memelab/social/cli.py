"""CLI for social ingestion (wired into `python -m memelab social ...`).

  social ingest --results <id> [<id> ...]     bridge result files data/inbox/<id>.result.json
  social ingest --file <path> [<path> ...]    any bridge result file (e.g. a fixture)
  social ingest --pull inbox/<id>.json        pull from the hand-off repo first (github_inbox.pull), then ingest
  social status [--event <event_id>]          last runs, connector health, checkpoints, quarantine; or one event
  social guard [--root <repo>]                fail if a tracked file holds raw social content (content_guard.py)
  social x-health [--config <path>]           X API connection health; no network call (x_api.py)
  social x-ingest [--config <path>] [--fixture <file>]   X API v2 ingest; live needs X_BEARER_TOKEN and a consented budget
  social tg-health [--config <path>] [--check-access [--fixture <file>]]   Telegram Bot API health (telegram_bot.py)
  social tg-ingest [--config <path>] [--fixture <file>]   poll approved channels through getUpdates; live needs TELEGRAM_BOT_TOKEN
  social tg-webhook-ingest [--config <path>] [--spool <dir>]   ingest updates spooled by telegram_bot.webhook_receive()
  social resolve --post <json> --bodies <json> [--context]   token identity for one post (identity.py), optional market context
  social identity [--item <item_key>] [--resolution <id>]    what is stored: status, identity, candidates, evidence, context

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


X_CONFIG = db.DATA_DIR / "private" / "x_api.json"


def cmd_x_health(a):
    from .x_api import health
    out = health(Path(a.config) if a.config else X_CONFIG, Path(a.db) if a.db else db.DB_PATH)
    print(json.dumps(out, indent=1, sort_keys=True, default=str))
    raise SystemExit(0 if out["status"] == "ready" else 1)


def cmd_x_ingest(a):
    """Live: refuses before any network call unless the token is set and the config consents to a budget.
    --fixture: replays recorded synthetic HTTP exchanges; rows are labelled fixture, never live."""
    import time
    import uuid
    from . import ingest as I
    from . import x_api as X
    _setup_logging(a.verbose)
    dbp = Path(a.db) if a.db else db.DB_PATH
    cfg_path = Path(a.config) if a.config else X_CONFIG
    db.init_db(dbp)
    if a.fixture:
        cfg, transport, token, mode = X.load_config(cfg_path), X.FixtureTransport(a.fixture), "fixture-token-not-a-secret", "fixture"
    else:
        h = X.health(cfg_path, dbp)
        if h["status"] != "ready":
            print(json.dumps({"status": "NOT_RUN", "reason": h["status"], "next_step": h["next_step"],
                              "network_calls_made": 0}, indent=1, sort_keys=True))
            raise SystemExit(1)
        cfg = X.load_config(cfg_path)
        transport, token, mode = X.UrllibTransport(timeout=cfg.timeout_seconds), X.get_token(), "live"
    t = a.now if a.now is not None else time.time()
    run_id = a.run_id or f"x_{mode}_{time.strftime('%Y%m%d_%H%M%S', time.gmtime(t))}_{uuid.uuid4().hex[:6]}"
    clock = (lambda: t) if a.now is not None else time.time
    # fixture replays do not wait out backoff delays; live runs do
    adapter = X.XApiAdapter(cfg, transport, token, dbp, run_id=run_id, mode=mode, clock=clock,
                            **({"sleep": lambda s: None} if mode == "fixture" else {}))
    out = I.ingest(adapter, dbp, now=t, run_id=run_id, batch_size=a.batch_size,
                   budget=I.Budget(max_items=a.max_items), max_age_hours=a.max_age_hours)
    out["mode"] = mode
    out["requests_made"] = adapter.requests
    print(json.dumps(out, indent=1, sort_keys=True))
    raise SystemExit(1 if out["status"] == "FAILED" else 0)


TG_CONFIG = db.DATA_DIR / "private" / "telegram_bot.json"
FIXTURE_TOKEN = "000000:fixture-token-not-a-secret"


def cmd_tg_health(a):
    """No network call unless --check-access (read-only getMe/getChat/getChatMember; free)."""
    from . import telegram_bot as T
    dbp = Path(a.db) if a.db else db.DB_PATH
    cfg_path = Path(a.config) if a.config else TG_CONFIG
    db.init_db(dbp)
    access = None
    if a.check_access:
        if a.fixture:
            access = T.check_access(T.load_config(cfg_path), T.FixtureTransport(a.fixture), FIXTURE_TOKEN, dbp, mode="fixture",
                                    sleep=lambda s: None)
        elif T.get_token() and cfg_path.exists():
            cfg = T.load_config(cfg_path)
            access = T.check_access(cfg, T.UrllibTransport(timeout=cfg.timeout_seconds), T.get_token(), dbp)
    out = T.health(cfg_path, dbp, access=access)
    if a.fixture:
        out["mode"] = "fixture: access states come from recorded synthetic exchanges, not from Telegram"
    print(json.dumps(out, indent=1, sort_keys=True, default=str))
    raise SystemExit(0 if out["status"] == "ready" else 1)


def cmd_tg_ingest(a):
    """Live: refuses before any network call without TELEGRAM_BOT_TOKEN and a channel config.
    --fixture: replays recorded synthetic getUpdates exchanges; rows are labelled fixture, never live."""
    import time
    import uuid
    from . import ingest as I
    from . import telegram_bot as T
    _setup_logging(a.verbose)
    dbp = Path(a.db) if a.db else db.DB_PATH
    cfg_path = Path(a.config) if a.config else TG_CONFIG
    db.init_db(dbp)
    if a.fixture:
        cfg, transport, token, mode = T.load_config(cfg_path), T.FixtureTransport(a.fixture), FIXTURE_TOKEN, "fixture"
    else:
        h = T.health(cfg_path, dbp)
        if h["status"] in ("credentials_missing", "not_configured"):
            print(json.dumps({"status": "NOT_RUN", "reason": h["status"], "next_step": h["next_step"],
                              "network_calls_made": 0}, indent=1, sort_keys=True))
            raise SystemExit(1)
        cfg = T.load_config(cfg_path)
        transport, token, mode = T.UrllibTransport(timeout=cfg.timeout_seconds + cfg.long_poll_timeout), T.get_token(), "live"
    t = a.now if a.now is not None else time.time()
    run_id = a.run_id or f"tg_{mode}_{time.strftime('%Y%m%d_%H%M%S', time.gmtime(t))}_{uuid.uuid4().hex[:6]}"
    clock = (lambda: t) if a.now is not None else time.time
    adapter = T.TelegramBotAdapter(cfg, transport, token, dbp, run_id=run_id, mode=mode, clock=clock,
                                   **({"sleep": lambda s: None} if mode == "fixture" else {}))
    out = I.ingest(adapter, dbp, now=t, run_id=run_id, batch_size=a.batch_size,
                   budget=I.Budget(max_items=a.max_items), max_age_hours=a.max_age_hours)
    out.update({"mode": mode, "requests_made": adapter.requests, "dropped_updates": adapter.dropped})
    print(json.dumps(out, indent=1, sort_keys=True))
    raise SystemExit(1 if out["status"] == "FAILED" else 0)


def cmd_tg_webhook_ingest(a):
    import time
    from . import ingest as I
    from . import telegram_bot as T
    _setup_logging(a.verbose)
    dbp = Path(a.db) if a.db else db.DB_PATH
    db.init_db(dbp)
    cfg = T.load_config(Path(a.config) if a.config else TG_CONFIG)
    spool = Path(a.spool) if a.spool else T.spool_dir()
    t = a.now if a.now is not None else time.time()
    adapter = T.WebhookSpoolAdapter(cfg, spool, dbp, run_id=a.run_id, clock=(lambda: t) if a.now is not None else time.time)
    out = I.ingest(adapter, dbp, now=t, run_id=a.run_id, max_age_hours=a.max_age_hours)
    out["spool_files_done"] = adapter.files_done
    print(json.dumps(out, indent=1, sort_keys=True))
    raise SystemExit(1 if out["status"] == "FAILED" else 0)


def _load_bodies(path: str) -> tuple[dict, float | None]:
    """A resolver fixture ({bodies, fetched_at}) or a bridge result file ({key: {s, body}}, _at)."""
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict) and isinstance(data.get("bodies"), dict):
        return data["bodies"], data.get("fetched_at")
    from .store import to_utc
    at = to_utc(data.get("_at")) if isinstance(data, dict) and data.get("_at") else None
    return {k: v for k, v in data.items() if not k.startswith("_")}, at


def cmd_resolve(a):
    from . import identity as ID, market_context as MC
    from .store import to_utc
    post = json.loads(Path(a.post).read_text())
    bodies, fetched = _load_bodies(a.bodies)
    fetched = a.fetched_at if a.fetched_at is not None else fetched
    dbp = Path(a.db) if a.db else db.DB_PATH
    db.init_db(dbp)
    import sqlite3
    con = sqlite3.connect(str(dbp)); con.row_factory = sqlite3.Row
    try:
        res = ID.resolve_post(bodies, text=post.get("text"), urls=post.get("urls") or [], cashtags=post.get("cashtags") or [],
                              chain_hint=post.get("chain_hint"), con=con)
        ids = ID.persist(con, res, item_key=post.get("item_key"), now=a.now)
        if a.context:
            if fetched is None:
                print("--context needs fetched_at (in the bodies file or --fetched-at)", file=sys.stderr)
                raise SystemExit(2)
            for rid, m in zip(ids, res["mentions"]):
                if m["status"] == "resolved":
                    MC.attach(con, rid, bodies, fetched_at=fetched, published_at=to_utc(post.get("published_at")),
                              native_price=post.get("native_price"), now=a.now)
        con.commit()
        out = {"status": res["status"], "resolutions": [ID.token_identity(con, resolution_id=i)[0] for i in ids]}
    finally:
        con.close()
    print(json.dumps(out, indent=1, sort_keys=True, default=str))
    raise SystemExit(0)


def cmd_identity(a):
    from . import identity as ID
    import sqlite3
    dbp = Path(a.db) if a.db else db.DB_PATH
    con = sqlite3.connect(str(dbp)); con.row_factory = sqlite3.Row
    try:
        out = ID.token_identity(con, item_key=a.item, resolution_id=a.resolution)
    finally:
        con.close()
    print(json.dumps(out, indent=1, sort_keys=True, default=str))
    raise SystemExit(0 if out else 1)


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
    q = ssp.add_parser("x-health", help="X API adapter health (credentials, consent, cursors, live evidence); no network")
    q.add_argument("--config", help=f"scope config (default {X_CONFIG})")
    q.add_argument("--db")
    q.set_defaults(fn=cmd_x_health)
    q = ssp.add_parser("x-ingest", help="ingest configured X scopes through the official X API v2")
    q.add_argument("--config", help=f"scope config (default {X_CONFIG})")
    q.add_argument("--fixture", help="recorded synthetic HTTP exchanges (no network, rows labelled fixture)")
    q.add_argument("--db")
    q.add_argument("--batch-size", type=int, default=50)
    q.add_argument("--max-items", type=int)
    q.add_argument("--max-age-hours", type=float, default=12.0)
    q.add_argument("--run-id")
    q.add_argument("--now", type=float, help="fixed clock (epoch seconds), for replays and tests")
    q.add_argument("-v", "--verbose", action="store_true")
    q.set_defaults(fn=cmd_x_ingest)
    q = ssp.add_parser("tg-health", help="Telegram Bot API health (credentials, channel access, update cursor, live evidence)")
    q.add_argument("--config", help=f"channel config (default {TG_CONFIG})")
    q.add_argument("--db")
    q.add_argument("--check-access", action="store_true", help="read-only getMe/getChat/getChatMember calls (live needs the token)")
    q.add_argument("--fixture", help="recorded synthetic exchanges for --check-access (no network)")
    q.set_defaults(fn=cmd_tg_health)
    q = ssp.add_parser("tg-ingest", help="poll approved Telegram channels through the Bot API (getUpdates)")
    q.add_argument("--config", help=f"channel config (default {TG_CONFIG})")
    q.add_argument("--fixture", help="recorded synthetic exchanges (no network, rows labelled fixture)")
    q.add_argument("--db")
    q.add_argument("--batch-size", type=int, default=50)
    q.add_argument("--max-items", type=int)
    q.add_argument("--max-age-hours", type=float, default=12.0)
    q.add_argument("--run-id")
    q.add_argument("--now", type=float, help="fixed clock (epoch seconds), for replays and tests")
    q.add_argument("-v", "--verbose", action="store_true")
    q.set_defaults(fn=cmd_tg_ingest)
    q = ssp.add_parser("tg-webhook-ingest", help="ingest Telegram webhook updates spooled in the private folder")
    q.add_argument("--config", help=f"channel config (default {TG_CONFIG})")
    q.add_argument("--spool", help="spool folder (default <private folder>/telegram_spool)")
    q.add_argument("--db")
    q.add_argument("--max-age-hours", type=float, default=12.0)
    q.add_argument("--run-id")
    q.add_argument("--now", type=float)
    q.add_argument("-v", "--verbose", action="store_true")
    q.set_defaults(fn=cmd_tg_webhook_ingest)
    q = ssp.add_parser("resolve", help="resolve a post's token references to (chain, contract); store candidates and evidence")
    q.add_argument("--post", required=True, help="JSON: {item_key?, published_at?, text?, urls?, cashtags?, chain_hint?, native_price?}; text is read, never stored")
    q.add_argument("--bodies", required=True, help="collector bodies: resolver fixture or bridge result file")
    q.add_argument("--context", action="store_true", help="also store timestamped market context for resolved mentions")
    q.add_argument("--fetched-at", type=float, help="when the bodies were fetched (epoch seconds), if the file does not say")
    q.add_argument("--db")
    q.add_argument("--now", type=float, help="fixed clock (epoch seconds), for replays and tests")
    q.set_defaults(fn=cmd_resolve)
    q = ssp.add_parser("identity", help="stored token identity, candidates, evidence and market context for an item")
    q.add_argument("--item", help="item_key")
    q.add_argument("--resolution", type=int, help="resolution id")
    q.add_argument("--db")
    q.set_defaults(fn=cmd_identity)
