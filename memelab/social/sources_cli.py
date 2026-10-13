"""CLI for the optional Reddit and Farcaster adapters (Phase 19) and the Discord bot adapter (Phase 20), wired into `python -m memelab social ...`.

  social reddit-health [--config <path>]                     Reddit Data API status; no network call
  social reddit-ingest [--config <path>] [--fixture <file>] [--extract [--bodies <json>]]
                                                             approved communities; live needs approval and credentials
  social reddit-purge                                        erase what was derived from deleted Reddit items and accounts
  social fc-health [--config <path>]                         Farcaster hub status; no network call
  social fc-ingest [--config <path>] [--fixture <file>] [--extract [--bodies <json>]]
                                                             configured fids and channels through a Snapchain node
  social discord-health [--config <path>]                    Discord bot status (consent, token, message-content intent); no network
  social discord-ingest [--config <path>] [--fixture <file>] [--extract [--bodies <json>]]
                                                             consented channels over the bot REST API, then purge deleted messages
  social discord-gateway --fixture <file> [--config <path>] [--extract]
                                                             one gateway pass from recorded frames (live websocket not shipped)
  social discord-purge [--user <id>]                         erase what was derived from deleted messages, and named users
  social discord-reset --channel <id>                        forget one channel's message cursor (dedupe absorbs re-reads)
  social youtube-health [--config <path>]                    YouTube Data API status (terms review, key, quota, transcripts); no network
  social youtube-ingest [--config <path>] [--fixture <file>] [--extract [--bodies <json>]]
                                                             configured channels and videos; transcript snippets only on an
                                                             authorized route; then purge gone and expired (30-day) items
  social youtube-purge [--retention-days N]                  erase what was derived from gone videos and videos past retention
  social sources                                             one table: every social connector, its status, cost and next step

--extract hands the post text to claim extraction in memory (api_common.TextSink); the text is never written.
Live runs refuse before any network call unless the health status is ready. Exit 0 for OK or PARTIAL, 1 for
FAILED or not ready, 2 for usage errors.
"""
from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

from .. import db

REDDIT_CONFIG = db.DATA_DIR / "private" / "reddit_api.json"
FC_CONFIG = db.DATA_DIR / "private" / "farcaster_hub.json"
DISCORD_CONFIG = db.DATA_DIR / "private" / "discord_bot.json"
YOUTUBE_CONFIG = db.DATA_DIR / "private" / "youtube_data.json"


def _dbp(a) -> Path:
    p = Path(a.db) if a.db else db.DB_PATH
    db.init_db(p)
    return p


def _print(obj) -> None:
    print(json.dumps(obj, indent=1, sort_keys=True, default=str))


def _bodies(path):
    if not path:
        return None
    from .cli import _load_bodies
    return _load_bodies(path)[0]


def _run(adapter, dbp, t, run_id, a, sink, mode, platform):
    from . import ingest as I
    from .api_common import extract_after_ingest
    out = I.ingest(adapter, dbp, now=t, run_id=run_id, batch_size=a.batch_size, budget=I.Budget(max_items=a.max_items),
                   max_age_hours=a.max_age_hours)
    out["mode"] = mode
    out["requests_made"] = adapter.requests
    if sink is not None:
        out["extraction"] = extract_after_ingest(dbp, sink, now=t, bodies=_bodies(a.bodies),
                                                 provider_reason="model_not_configured")
    return out


def cmd_reddit_health(a):
    from . import reddit_api as R
    out = R.health(Path(a.config) if a.config else REDDIT_CONFIG, _dbp(a))
    _print(out)
    raise SystemExit(0 if out["status"] == "ready" else 1)


def cmd_reddit_ingest(a):
    from . import reddit_api as R
    from .api_common import TextSink
    from .cli import _setup_logging
    _setup_logging(a.verbose)
    dbp = _dbp(a)
    cfg_path = Path(a.config) if a.config else REDDIT_CONFIG
    if a.fixture:
        cfg, tr, cid, sec, mode = R.load_config(cfg_path), R.FixtureTransport(a.fixture), "fixture-client", "fixture-secret-not-real", "fixture"
    else:
        h = R.health(cfg_path, dbp)
        if h["status"] != "ready":
            _print({"status": "NOT_RUN", "reason": h["status"], "next_step": h["next_step"], "network_calls_made": 0})
            raise SystemExit(1)
        cfg = R.load_config(cfg_path)
        cid, sec = R.get_credentials()
        tr, mode = R.UrllibTransport(cfg.user_agent, timeout=cfg.timeout_seconds), "live"
    t = a.now if a.now is not None else time.time()
    run_id = a.run_id or f"reddit_{mode}_{time.strftime('%Y%m%d_%H%M%S', time.gmtime(t))}_{uuid.uuid4().hex[:6]}"
    sink = TextSink() if a.extract else None
    ad = R.RedditApiAdapter(cfg, tr, cid, sec, dbp, run_id=run_id, mode=mode, clock=(lambda: t) if a.now is not None else time.time,
                            text_sink=sink, **({"sleep": lambda s: None} if mode == "fixture" else {}))
    out = _run(ad, dbp, t, run_id, a, sink, mode, "reddit")
    out["deletion_purge"] = R.purge_deleted(dbp, now=t, deleted_account_items=ad.account_deletion_items)
    _print(out)
    raise SystemExit(1 if out["status"] == "FAILED" else 0)


def cmd_reddit_purge(a):
    from . import reddit_api as R
    _print(R.purge_deleted(_dbp(a), now=a.now if a.now is not None else time.time(), deleted_accounts=a.account or []))


def cmd_fc_health(a):
    from . import farcaster_hub as F
    out = F.health(Path(a.config) if a.config else FC_CONFIG, _dbp(a))
    _print(out)
    raise SystemExit(0 if out["status"] == "ready" else 1)


def cmd_fc_ingest(a):
    from . import farcaster_hub as F
    from .api_common import TextSink
    from .cli import _setup_logging
    _setup_logging(a.verbose)
    dbp = _dbp(a)
    cfg_path = Path(a.config) if a.config else FC_CONFIG
    if a.fixture:
        cfg, tr, key, mode = F.load_config(cfg_path), F.FixtureTransport(a.fixture), None, "fixture"
    else:
        h = F.health(cfg_path, dbp)
        if h["status"] != "ready":
            _print({"status": "NOT_RUN", "reason": h["status"], "next_step": h["next_step"], "network_calls_made": 0})
            raise SystemExit(1)
        cfg = F.load_config(cfg_path)
        key = F.get_api_key(cfg)
        tr, mode = F.UrllibTransport(cfg.base_url, cfg.api_key_header, timeout=cfg.timeout_seconds), "live"
    t = a.now if a.now is not None else time.time()
    run_id = a.run_id or f"farcaster_{mode}_{time.strftime('%Y%m%d_%H%M%S', time.gmtime(t))}_{uuid.uuid4().hex[:6]}"
    sink = TextSink() if a.extract else None
    ad = F.FarcasterHubAdapter(cfg, tr, key, dbp, run_id=run_id, mode=mode, clock=(lambda: t) if a.now is not None else time.time,
                               text_sink=sink, **({"sleep": lambda s: None} if mode == "fixture" else {}))
    out = _run(ad, dbp, t, run_id, a, sink, mode, "farcaster")
    _print(out)
    raise SystemExit(1 if out["status"] == "FAILED" else 0)


def cmd_discord_health(a):
    from . import discord_bot as D
    out = D.health(Path(a.config) if a.config else DISCORD_CONFIG, _dbp(a))
    _print(out)
    raise SystemExit(0 if out["status"] == "ready" else 1)


def _discord_finish(ad, dbp, t, run_id, a, sink, mode):
    from . import discord_bot as D
    out = _run(ad, dbp, t, run_id, a, sink, mode, "discord")
    out["dropped"] = dict(ad.dropped)
    out["deletion_purge"] = D.purge_deleted(dbp, now=t)
    _print(out)
    raise SystemExit(1 if out["status"] == "FAILED" else 0)


def cmd_discord_ingest(a):
    from . import discord_bot as D
    from .api_common import TextSink
    from .cli import _setup_logging
    _setup_logging(a.verbose)
    dbp = _dbp(a)
    cfg_path = Path(a.config) if a.config else DISCORD_CONFIG
    if a.fixture:
        cfg, tr, tok, mode = D.load_config(cfg_path), D.FixtureTransport(a.fixture), "fixture-bot-token-not-real", "fixture"
    else:
        h = D.health(cfg_path, dbp)
        if h["status"] != "ready":
            _print({"status": "NOT_RUN", "reason": h["status"], "next_step": h["next_step"], "network_calls_made": 0})
            raise SystemExit(1)
        cfg, tok = D.load_config(cfg_path), D.get_token()
        tr, mode = D.UrllibTransport(timeout=cfg.timeout_seconds), "live"
    t = a.now if a.now is not None else time.time()
    run_id = a.run_id or f"discord_{mode}_{time.strftime('%Y%m%d_%H%M%S', time.gmtime(t))}_{uuid.uuid4().hex[:6]}"
    sink = TextSink() if a.extract else None
    ad = D.DiscordBotAdapter(cfg, tr, tok, dbp, run_id=run_id, mode=mode, clock=(lambda: t) if a.now is not None else time.time,
                             text_sink=sink, **({"sleep": lambda s: None} if mode == "fixture" else {}))
    _discord_finish(ad, dbp, t, run_id, a, sink, mode)


def cmd_discord_gateway(a):
    from . import discord_bot as D
    from .api_common import TextSink
    from .cli import _setup_logging
    _setup_logging(a.verbose)
    dbp = _dbp(a)
    if not a.fixture:
        _print({"status": "NOT_RUN", "reason": "gateway_transport_not_shipped",
                "next_step": "the live gateway needs a websocket client that this repo does not ship; use `social discord-ingest` "
                             "(REST) for live reads", "network_calls_made": 0})
        raise SystemExit(1)
    cfg = D.load_config(Path(a.config) if a.config else DISCORD_CONFIG)
    tr = D.GatewayFixtureTransport(a.fixture)
    t = a.now if a.now is not None else time.time()
    run_id = a.run_id or f"discord_gw_fixture_{time.strftime('%Y%m%d_%H%M%S', time.gmtime(t))}_{uuid.uuid4().hex[:6]}"
    sink = TextSink() if a.extract else None
    ad = D.DiscordGatewayAdapter(cfg, tr, "fixture-bot-token-not-real", dbp, run_id=run_id, mode="fixture",
                                 clock=(lambda: t) if a.now is not None else time.time, text_sink=sink)
    _discord_finish(ad, dbp, t, run_id, a, sink, "fixture")


def cmd_discord_purge(a):
    from . import discord_bot as D
    _print(D.purge_deleted(_dbp(a), now=a.now if a.now is not None else time.time(), users=a.user or []))


def cmd_discord_reset(a):
    from . import discord_bot as D
    _print(D.reset_checkpoint(_dbp(a), a.channel, now=a.now if a.now is not None else time.time()))


def cmd_youtube_health(a):
    from . import youtube_data as Y
    out = Y.health(Path(a.config) if a.config else YOUTUBE_CONFIG, _dbp(a), now=a.now)
    _print(out)
    raise SystemExit(0 if out["status"] == "ready" else 1)


def cmd_youtube_ingest(a):
    from . import youtube_data as Y
    from .api_common import TextSink
    from .cli import _setup_logging
    _setup_logging(a.verbose)
    dbp = _dbp(a)
    cfg_path = Path(a.config) if a.config else YOUTUBE_CONFIG
    if a.fixture:
        cfg, tr, key, oauth, mode = (Y.load_config(cfg_path), Y.FixtureTransport(a.fixture), "fixture-api-key-not-real",
                                     "fixture-oauth-not-real", "fixture")
    else:
        h = Y.health(cfg_path, dbp)
        if h["status"] != "ready":
            _print({"status": "NOT_RUN", "reason": h["status"], "next_step": h["next_step"], "network_calls_made": 0})
            raise SystemExit(1)
        cfg = Y.load_config(cfg_path)
        key, oauth = Y.get_credentials()
        tr, mode = Y.UrllibTransport(timeout=cfg.timeout_seconds), "live"
    t = a.now if a.now is not None else time.time()
    run_id = a.run_id or f"youtube_{mode}_{time.strftime('%Y%m%d_%H%M%S', time.gmtime(t))}_{uuid.uuid4().hex[:6]}"
    sink = TextSink() if a.extract else None
    ad = Y.YouTubeDataAdapter(cfg, tr, key, dbp, oauth_token=oauth, run_id=run_id, mode=mode,
                              clock=(lambda: t) if a.now is not None else time.time, text_sink=sink,
                              **({"sleep": lambda s: None} if mode == "fixture" else {}))
    out = _run(ad, dbp, t, run_id, a, sink, mode, "youtube")
    out["quota_units"] = ad.quota_units
    out["transcripts"] = dict(sorted(ad.transcripts.items()))
    out["dropped"] = dict(ad.dropped)
    out["purge"] = Y.purge(dbp, now=t, retention_days=cfg.retention_days)
    _print(out)
    raise SystemExit(1 if out["status"] == "FAILED" else 0)


def cmd_youtube_purge(a):
    from . import youtube_data as Y
    _print(Y.purge(_dbp(a), now=a.now if a.now is not None else time.time(), retention_days=a.retention_days))


def sources_table(dbp, env=None) -> list[dict]:
    """One row per social connector: status, credentials, cost, live evidence. No network call."""
    from . import discord_bot as D, farcaster_hub as F, reddit_api as R, telegram_bot as T, x_api as X, youtube_data as Y
    from .cli import TG_CONFIG, X_CONFIG
    rows = []
    for name, fn, cfg in (("x_api", X.health, X_CONFIG), ("telegram_bot", T.health, TG_CONFIG),
                          ("reddit_api", R.health, REDDIT_CONFIG), ("farcaster_hub", F.health, FC_CONFIG),
                          ("discord_bot", D.health, DISCORD_CONFIG), ("youtube_data", Y.health, YOUTUBE_CONFIG)):
        h = fn(cfg, dbp, env=env)
        le = h.get("live_evidence") or {}
        rows.append({"connector": name, "status": h.get("status"), "credentials": h.get("credentials"),
                     "cost": h.get("cost") or h.get("spend_this_month_usd"), "live_requests": le.get("requests"),
                     "live_verdict": le.get("verdict"), "next_step": h.get("next_step")})
    return rows


def cmd_sources(a):
    _print({"network_calls_made": 0, "connectors": sources_table(_dbp(a))})


def _ingest_args(q):
    q.add_argument("--fixture", help="recorded synthetic HTTP exchanges (no network, rows labelled fixture)")
    q.add_argument("--extract", action="store_true", help="run claim extraction on this run's items; text held in memory only")
    q.add_argument("--bodies", help="collector bodies for token identity during --extract (Phase 05 resolver fixture or result file)")
    q.add_argument("--db")
    q.add_argument("--batch-size", type=int, default=50)
    q.add_argument("--max-items", type=int)
    q.add_argument("--max-age-hours", type=float, default=12.0)
    q.add_argument("--run-id")
    q.add_argument("--now", type=float, help="fixed clock (epoch seconds), for replays and tests")
    q.add_argument("-v", "--verbose", action="store_true")


def add_parser(ssp) -> None:
    q = ssp.add_parser("reddit-health", help="Reddit Data API adapter status (approval, credentials, cursors, live evidence); no network")
    q.add_argument("--config", help=f"community config (default {REDDIT_CONFIG})")
    q.add_argument("--db")
    q.set_defaults(fn=cmd_reddit_health)
    q = ssp.add_parser("reddit-ingest", help="ingest approved Reddit communities through the Reddit Data API, then purge deleted items")
    q.add_argument("--config", help=f"community config (default {REDDIT_CONFIG})")
    _ingest_args(q)
    q.set_defaults(fn=cmd_reddit_ingest)
    q = ssp.add_parser("reddit-purge", help="erase what the lab derived from deleted or removed Reddit items and deleted accounts")
    q.add_argument("--account", action="append", help="a t2_ id of an account known to be deleted (repeatable)")
    q.add_argument("--db")
    q.add_argument("--now", type=float)
    q.set_defaults(fn=cmd_reddit_purge)
    q = ssp.add_parser("fc-health", help="Farcaster hub adapter status (endpoint, billing consent, cursors, live evidence); no network")
    q.add_argument("--config", help=f"hub config (default {FC_CONFIG})")
    q.add_argument("--db")
    q.set_defaults(fn=cmd_fc_health)
    q = ssp.add_parser("fc-ingest", help="ingest configured Farcaster fids and channels through a Snapchain node HTTP API")
    q.add_argument("--config", help=f"hub config (default {FC_CONFIG})")
    _ingest_args(q)
    q.set_defaults(fn=cmd_fc_ingest)
    q = ssp.add_parser("discord-health", help="Discord bot adapter status (consent, token, message-content intent, cursors); no network")
    q.add_argument("--config", help=f"server and channel config (default {DISCORD_CONFIG})")
    q.add_argument("--db")
    q.set_defaults(fn=cmd_discord_health)
    q = ssp.add_parser("discord-ingest", help="ingest consented Discord channels through the bot REST API, then purge deleted messages")
    q.add_argument("--config", help=f"server and channel config (default {DISCORD_CONFIG})")
    _ingest_args(q)
    q.set_defaults(fn=cmd_discord_ingest)
    q = ssp.add_parser("discord-gateway", help="one Discord gateway pass from recorded frames (fixture only)")
    q.add_argument("--config", help=f"server and channel config (default {DISCORD_CONFIG})")
    _ingest_args(q)
    q.set_defaults(fn=cmd_discord_gateway)
    q = ssp.add_parser("discord-purge", help="erase what the lab derived from deleted Discord messages, and named users on request")
    q.add_argument("--user", action="append", help="a Discord user id whose data must be erased (repeatable)")
    q.add_argument("--db")
    q.add_argument("--now", type=float)
    q.set_defaults(fn=cmd_discord_purge)
    q = ssp.add_parser("discord-reset", help="forget one Discord channel's message cursor")
    q.add_argument("--channel", required=True, help="channel id")
    q.add_argument("--db")
    q.add_argument("--now", type=float)
    q.set_defaults(fn=cmd_discord_reset)
    q = ssp.add_parser("youtube-health", help="YouTube Data API adapter status (terms review, key, quota, transcripts); no network")
    q.add_argument("--config", help=f"channel config (default {YOUTUBE_CONFIG})")
    q.add_argument("--db")
    q.add_argument("--now", type=float)
    q.set_defaults(fn=cmd_youtube_health)
    q = ssp.add_parser("youtube-ingest", help="ingest configured YouTube channels and videos (metadata; transcript snippets only "
                                              "on an authorized route), then purge gone and expired items")
    q.add_argument("--config", help=f"channel config (default {YOUTUBE_CONFIG})")
    _ingest_args(q)
    q.set_defaults(fn=cmd_youtube_ingest)
    q = ssp.add_parser("youtube-purge", help="erase what the lab derived from removed YouTube videos and videos past retention")
    q.add_argument("--retention-days", type=float, default=30.0)
    q.add_argument("--db")
    q.add_argument("--now", type=float)
    q.set_defaults(fn=cmd_youtube_purge)
    q = ssp.add_parser("sources", help="every social connector with status, cost and next step; no network")
    q.add_argument("--db")
    q.set_defaults(fn=cmd_sources)


if __name__ == "__main__":     # pragma: no cover
    sys.exit("use: python -m memelab social <command>")
