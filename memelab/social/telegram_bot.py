"""Telegram channel monitoring through the official Telegram Bot API (Phase 04).

Contract read on core.telegram.org on 2026-10-11 (docs/social-intelligence/TELEGRAM_04.md has the quotes):

  getUpdates(offset, limit 1-100, timeout, allowed_updates)  long or short polling; "An update is considered
      confirmed as soon as getUpdates is called with an offset higher than its update_id"; unconfirmed updates are
      kept "not longer than 24 hours"; does not work while a webhook is set (the two ways are mutually exclusive)
  setWebhook(secret_token)  Telegram sends the secret in header X-Telegram-Bot-Api-Secret-Token on every request
  Update.channel_post / edited_channel_post / my_chat_member
  Message: message_id (unique inside the chat), chat, sender_chat, date, edit_date, author_signature,
      forward_origin (MessageOriginUser / HiddenUser / Chat / Channel), is_automatic_forward, reply_to_message,
      external_reply, text, caption.  InaccessibleMessage has date 0.
  Responses: {"ok": true, "result": ...} or {"ok": false, "error_code", "description", "parameters"}.

What a bot can see (FACT from the docs, plus what the docs do not offer):
  - Bots receive "All messages from channels where they are a member". In a channel that means the channel's
    admins added the bot (Telegram adds bots to channels as administrators). A newly created bot cannot read an
    arbitrary public channel, and nothing here pretends it can.
  - No history: the Bot API has no method that returns a channel's earlier messages. Coverage starts when the bot
    was added and when the first poll ran; unconfirmed updates older than 24 hours are gone.
  - No deletion signal: no Update field reports a deleted channel post (deleted_business_messages is for business
    accounts only), and there is no method to fetch a message by id. A deleted post simply stops being edited.
  - Telegram's Bot Platform Developer Terms 4.3 forbid using a bot to collect data "beyond what is essential" and
    "any form of data collection aimed at creating large datasets ... such as scraping public group or channel
    contents". The adapter therefore reads only channels listed in the config with a recorded approval basis, keeps
    ids, hashes and times, and drops message text in memory (D-013, D-016, D-026).

What is stored per channel post: channel id and public username, message id, link https://t.me/<username>/<id>,
send time, edit time, sha256 of the text or caption, sha256 of the author signature (never the name), reply
target ids, forward origin ids (never a user's id or name), the update that carried it, fetch time.

Safety:
  - No token (env TELEGRAM_BOT_TOKEN) -> no request; the CLI says credentials_missing.
  - The token is part of the request URL path; transport errors are rebuilt without it and every message is scrubbed.
  - Only approved channels are converted; anything else (other chats, DMs to the bot, unapproved channels, service
    messages, inaccessible messages) is counted by reason and dropped without being written anywhere.
  - The update offset (social_source_cursors) advances only after ingest() committed every unit of the batch, so an
    interrupted run gets the same updates again on the next poll and event-id dedupe absorbs the repeats.
  - Webhook route: webhook_receive() checks the secret header in constant time, converts the update in memory
    and spools only the hashed record to the gitignored private folder; WebhookSpoolAdapter ingests the spool.
"""
from __future__ import annotations

import hmac
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from . import private, store
from .ingest import (INBOUND_SCHEMA_V3, Budget, BudgetExceeded, SourceUnit, TransientError, canonical_sha, log_event,
                     redact, with_retries)

API_BASE = "https://api.telegram.org"
TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
SECRET_ENV = "TELEGRAM_WEBHOOK_SECRET"
CONFIG_SCHEMA = "memelab.telegram_bot.config/1"
FIXTURE_SCHEMA = "memelab.telegram_bot.fixture/1"
SPOOL_SCHEMA = "memelab.telegram_bot.spool/1"
CONTRACT_VERIFIED = "2026-10-11"
BOT_API_VERSION_SEEN = "10.3"          # top of the Bot API changelog on 2026-10-11
ALLOWED_UPDATES = ["channel_post", "edited_channel_post", "my_chat_member"]
UPDATE_RETENTION_S = 24 * 3600         # unconfirmed updates are dropped by Telegram after 24 h
WEBHOOK_MAX_BYTES = 1_000_000
CHANNEL_ID = re.compile(r"^-100\d{5,16}$")
USERNAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")
SECRET_CHARS = re.compile(r"^[A-Za-z0-9_\-]{1,256}$")
APPROVALS = ("own_channel", "admin_invited_bot")
ADMIN_STATUSES = ("administrator", "creator")
FORBIDDEN_CONFIG_KEYS = {"token", "bot_token", "secret", "secret_token", "webhook_secret", "api_key", "api_hash",
                         "password", "session", "phone"}
TERMS_NOTE = ("Telegram Bot API: only posts sent while the bot is an administrator of this channel; no history before "
              "that; no deletion events; unconfirmed updates are dropped by Telegram after 24 h; text hashed and dropped; "
              "forward origins kept as ids and never counted as independent originals")


# ---------- config ----------

@dataclass
class Channel:
    chat_id: str
    username: str | None
    approval: str                   # own_channel | admin_invited_bot (how the bot got admin access)

    @property
    def connector(self) -> str:
        return f"telegram_bot:channel:{self.chat_id}"


@dataclass
class TgConfig:
    bot_label: str
    channels: list[Channel]
    poll_limit: int = 100
    max_polls_per_run: int = 5
    long_poll_timeout: int = 0
    timeout_seconds: float = 30.0
    by_id: dict = field(default_factory=dict)

    def __post_init__(self):
        self.by_id = {c.chat_id: c for c in self.channels}

    @property
    def bot_connector(self) -> str:
        return f"telegram_bot:{self.bot_label}"


def load_config(obj: dict | str | Path) -> TgConfig:
    """Parse and check a config. Credentials never live in the config (env TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET)."""
    if not isinstance(obj, dict):
        obj = json.loads(Path(obj).read_text())
    if obj.get("schema") != CONFIG_SCHEMA:
        raise ValueError(f"config schema must be {CONFIG_SCHEMA}")

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if str(k).lower() in FORBIDDEN_CONFIG_KEYS:
                    raise ValueError(f"config must not hold credentials (key '{k}'); use the {TOKEN_ENV} / {SECRET_ENV} environment variables")
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    label = obj.get("bot_label")
    if not isinstance(label, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,40}", label):
        raise ValueError("bot_label: 1-40 letters, digits or underscore")
    chans, seen = [], set()
    for i, c in enumerate(obj.get("channels") or []):
        cid = str(c.get("chat_id", "")).strip()
        if not CHANNEL_ID.match(cid):
            raise ValueError(f"channels[{i}].chat_id: a channel id looks like -100 followed by digits")
        un = c.get("username")
        if un is not None:
            un = str(un).lstrip("@")
            if not USERNAME.match(un):
                raise ValueError(f"channels[{i}].username: 5-32 letters, digits or underscore, starting with a letter")
        if c.get("approval") not in APPROVALS:
            raise ValueError(f"channels[{i}].approval: one of {', '.join(APPROVALS)} (record how the bot became an admin)")
        if cid in seen:
            raise ValueError(f"channels[{i}]: duplicate chat_id")
        seen.add(cid)
        chans.append(Channel(cid, un, c["approval"]))
    return TgConfig(bot_label=label, channels=chans, poll_limit=max(1, min(int(obj.get("poll_limit", 100)), 100)),
                    max_polls_per_run=max(1, int(obj.get("max_polls_per_run", 5))),
                    long_poll_timeout=max(0, min(int(obj.get("long_poll_timeout", 0)), 50)),
                    timeout_seconds=float(obj.get("timeout_seconds", 30)))


def get_token(env: dict | None = None) -> str | None:
    v = (env if env is not None else os.environ).get(TOKEN_ENV, "")
    return v.strip() or None


def get_secret(env: dict | None = None) -> str | None:
    v = (env if env is not None else os.environ).get(SECRET_ENV, "").strip()
    return v if v and SECRET_CHARS.match(v) else None


# ---------- transport ----------

@dataclass
class TgResponse:
    status: int
    body: Any
    received_at: float


class UrllibTransport:
    """The only code that talks to api.telegram.org. The token is in the URL path, so no exception text that could
    carry the URL ever leaves this method."""

    def __init__(self, timeout: float = 30.0, clock: Callable[[], float] = time.time):
        self.timeout, self.clock = timeout, clock

    def call(self, method: str, params: dict, token: str) -> TgResponse:
        req = urllib.request.Request(f"{API_BASE}/bot{token}/{method}", data=json.dumps(params or {}).encode(),
                                     headers={"Content-Type": "application/json", "User-Agent": "memelab-telegram-bot/1"},
                                     method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                status, raw = r.status, r.read()
        except urllib.error.HTTPError as e:
            status, raw = e.code, (e.read() or b"")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise TransientError(f"network: {type(e).__name__}") from None
        try:
            body = json.loads(raw.decode("utf-8")) if raw else None
        except ValueError:
            body = None
        return TgResponse(status, body, self.clock())


class FixtureMiss(Exception):
    """A request the recorded fixture does not contain."""


class FixtureTransport:
    """Replays recorded synthetic exchanges, matched on method plus exact parameters; an exchange listed twice for the
    same request is served in order. 'raise' simulates a transport error (its text may contain the token)."""

    def __init__(self, fixture: dict | str | Path):
        if not isinstance(fixture, dict):
            fixture = json.loads(Path(fixture).read_text())
        if fixture.get("schema") != FIXTURE_SCHEMA:
            raise ValueError(f"fixture schema must be {FIXTURE_SCHEMA}")
        self.exchanges = fixture["exchanges"]
        self.used: set[int] = set()
        self.calls: list[dict] = []

    def call(self, method: str, params: dict, token: str) -> TgResponse:
        p = json.loads(json.dumps(params or {}, sort_keys=True))
        self.calls.append({"method": method, "params": p, "token_sent": bool(token)})
        for i, ex in enumerate(self.exchanges):
            rq = ex["request"]
            if i in self.used or rq["method"] != method or json.loads(json.dumps(rq.get("params") or {}, sort_keys=True)) != p:
                continue
            self.used.add(i)
            if "raise" in ex:
                raise TransientError(ex["raise"].replace("{token}", token))
            rs = ex["response"]
            return TgResponse(int(rs["status"]), rs.get("body"), store.to_utc(ex["recorded_at"]))
        raise FixtureMiss(f"no recorded exchange for {method} with parameters {sorted(p)}")


# ---------- errors ----------

def _description(body: Any) -> str:
    if isinstance(body, dict) and isinstance(body.get("description"), str):
        return redact(body["description"])[:100]
    return "no description"


def classify_error(status: int, body: Any) -> tuple[str, str, str]:
    """HTTP error -> (connector status, access state, message). Access states: credentials_rejected, access_denied,
    webhook_conflict, rate_limited, error."""
    d = _description(body)
    if status == 401 or status == 404:
        return "BLOCKED", "credentials_rejected", f"{status} token rejected or unknown method; {d}"
    if status == 403:
        return "BLOCKED", "access_denied", f"403 forbidden; {d}"
    if status == 400 and ("chat not found" in d.lower() or "not a member" in d.lower()):
        return "BLOCKED", "access_denied", f"400; {d}"
    if status == 409:
        return "BLOCKED", "webhook_conflict", f"409 getUpdates conflicts with an active webhook; {d}"
    if status == 429:
        return "RATE_LIMITED", "rate_limited", f"429; {d}"
    return "DOWN", "error", f"HTTP {status}; {d}"


def retry_after(body: Any) -> float:
    try:
        return float(((body or {}).get("parameters") or {}).get("retry_after"))
    except (TypeError, ValueError):
        return 30.0


# ---------- update -> inbound item ----------

def _iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _pid(chat_id: Any, message_id: Any) -> str:
    return f"{chat_id}_{message_id}"


def _int(v: Any) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def message_item(msg: dict, kind: str, fetched_at: float, cfg: TgConfig, update_id: int | None = None
                 ) -> tuple[str | None, dict | None, str | None]:
    """One channel message -> (chat_id, inbound/3 item, drop reason). The text and caption are hashed here and go no
    further; author signatures and forward sender names likewise."""
    chat = msg.get("chat") if isinstance(msg.get("chat"), dict) else {}
    cid = str(chat.get("id")) if chat.get("id") is not None else None
    if chat.get("type") != "channel":
        return cid, None, "not_a_channel"
    ch = cfg.by_id.get(cid)
    if ch is None:
        return cid, None, "unapproved_channel"
    if msg.get("date") == 0:
        return cid, None, "inaccessible_message"
    if any(k in msg for k in ("pinned_message", "new_chat_title", "new_chat_photo", "delete_chat_photo",
                              "message_auto_delete_timer_changed", "migrate_to_chat_id")):
        return cid, None, "service_message"
    mid, date = _int(msg.get("message_id")), _int(msg.get("date"))
    if not mid or mid <= 0 or not date:
        return cid, None, "missing_ids"
    username = chat.get("username") or ch.username
    pid = _pid(cid, mid)
    text = msg.get("text") if isinstance(msg.get("text"), str) else msg.get("caption") if isinstance(msg.get("caption"), str) else None
    chash = store.text_hash(text) if text else None
    sig = msg.get("author_signature")
    poster = store.text_hash(sig) if isinstance(sig, str) and sig.strip() else None
    edit = _int(msg.get("edit_date"))
    version_at = edit if edit else date

    forward = None
    fo = msg.get("forward_origin")
    if isinstance(fo, dict):
        ot = fo.get("type") if fo.get("type") in ("channel", "chat", "user", "hidden_user") else "unknown"
        oc = om = None
        if ot == "channel" and isinstance(fo.get("chat"), dict):
            oc = str(fo["chat"].get("id")) if fo["chat"].get("id") is not None else None
            om = str(fo["message_id"]) if _int(fo.get("message_id")) else None
        elif ot == "chat" and isinstance(fo.get("sender_chat"), dict):
            oc = str(fo["sender_chat"].get("id")) if fo["sender_chat"].get("id") is not None else None
        forward = {"origin_type": ot, "origin_chat_id": oc, "origin_message_id": om,
                   "origin_provider_item_id": _pid(oc, om) if oc and om else None,
                   "origin_published_at": _iso(fo["date"]) if _int(fo.get("date")) else None,
                   "is_automatic_forward": msg.get("is_automatic_forward") is True}

    refs = []
    rt = msg.get("reply_to_message")
    if isinstance(rt, dict) and _int(rt.get("message_id")):
        refs.append({"type": "replied_to", "provider_item_id": _pid(cid, rt["message_id"]), "author_id": cid})
    ext = msg.get("external_reply")
    if isinstance(ext, dict) and isinstance(ext.get("chat"), dict) and _int(ext.get("message_id")):
        ec = str(ext["chat"].get("id"))
        refs.append({"type": "replied_to", "provider_item_id": _pid(ec, ext["message_id"]), "author_id": ec})
    rtype = "REPOST" if forward else "REPLY" if refs else "ORIGINAL"

    item = {
        # same message in the same version = same event, however often Telegram delivers it; an edit is a new event
        "event_id": f"bot.{pid}.v{version_at}." + canonical_sha([chash, poster, forward, refs])[:12],
        "provider_item_id": pid,
        "url": f"https://t.me/{username}/{mid}" if username else None,
        "published_at": _iso(date),
        "published_at_basis": "PROVIDER",
        "fetched_at": _iso(fetched_at),
        "retrieval_status": "OK",
        "content_hash": chash,
        "visibility": "PUBLIC" if username else "PRIVATE",   # no public username = not a public channel (D-009)
        "account": {"provider_user_id": cid, **({"handle": username, "profile_url": f"https://t.me/{username}"} if username else {})},
        "context": {"reference_type": rtype, "referenced": refs[:10], "basis": "PROVIDER"},
        "forward": forward,
        "version": {"kind": "EDIT" if edit else "ORIGINAL", "provider_version_at": _iso(version_at), "poster_hash": poster},
    }
    return cid, {k: v for k, v in item.items() if v is not None}, None


def normalize_update(upd: dict, cfg: TgConfig, fetched_at: float) -> dict:
    """One Update -> {"update_id", "kind", "chat_id", "item" | None, "membership" | None, "dropped" | None}. No text."""
    uid = _int(upd.get("update_id"))
    out = {"update_id": uid, "kind": None, "chat_id": None, "item": None, "membership": None, "dropped": None}
    for kind in ("channel_post", "edited_channel_post"):
        if isinstance(upd.get(kind), dict):
            out["kind"] = kind
            out["chat_id"], out["item"], out["dropped"] = message_item(upd[kind], kind, fetched_at, cfg, uid)
            return out
    cmu = upd.get("my_chat_member")
    if isinstance(cmu, dict):
        out["kind"] = "my_chat_member"
        chat = cmu.get("chat") if isinstance(cmu.get("chat"), dict) else {}
        cid = str(chat.get("id")) if chat.get("id") is not None else None
        out["chat_id"] = cid
        if cid not in cfg.by_id:
            out["dropped"] = "unapproved_channel"
            return out
        st = ((cmu.get("new_chat_member") or {}).get("status")) or "unknown"
        out["membership"] = {"status": str(st)[:20], "date": _int(cmu.get("date"))}
        return out
    out["kind"] = next((k for k in upd if k != "update_id"), "empty")
    out["dropped"] = "update_type_not_used"     # e.g. a DM to the bot ('message'): never read, never stored
    return out


# ---------- shared unit building ----------

def _cursor(con, connector: str, scope: str):
    return con.execute("SELECT * FROM social_source_cursors WHERE connector=? AND scope=?", (connector, scope)).fetchone()


def _save_cursor(con, connector: str, scope: str, now: float, **kw) -> None:
    row = _cursor(con, connector, scope)
    cur = dict(row) if row else {"provider_scope_id": None, "newest_id": None, "last_success_at": None,
                                  "rate_limit_reset_at": None, "last_status": "UNKNOWN"}
    cur.update(kw)
    con.execute("INSERT INTO social_source_cursors(connector,scope,provider_scope_id,newest_id,last_success_at,last_attempt_at,"
                "last_status,rate_limit_reset_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(connector,scope) DO UPDATE SET"
                " provider_scope_id=excluded.provider_scope_id, newest_id=excluded.newest_id, last_success_at=excluded.last_success_at,"
                " last_attempt_at=excluded.last_attempt_at, last_status=excluded.last_status,"
                " rate_limit_reset_at=excluded.rate_limit_reset_at, updated_at=excluded.updated_at",
                (connector, scope, cur["provider_scope_id"], cur["newest_id"], cur["last_success_at"], now,
                 cur["last_status"], cur["rate_limit_reset_at"], now))
    con.commit()


def membership_state(status: str) -> str:
    return "OK" if status in ADMIN_STATUSES else "access_denied"


class _UnitBuilder:
    """Turns normalized update records into SourceUnits, one per channel per batch, and records membership changes."""

    def __init__(self, cfg: TgConfig, mode: str, collector: str, run_id: str | None, scrub: Callable[[str], str]):
        self.cfg, self.mode, self.collector, self.run_id, self.scrub = cfg, mode, collector, run_id, scrub
        self.dropped: dict[str, int] = {}

    def source(self, ch: Channel) -> dict:
        live = self.mode == "live"
        return {"platform": "telegram", "source_id": f"bot:{self.cfg.bot_label}:channel:{ch.chat_id}",
                "access_mode": "fetch" if live else "fixture", "collector": self.collector if live else self.collector + "/fixture",
                "rights_basis": f"telegram_bot_api_{ch.approval}" if live else "synthetic_fixture",
                "visibility": "PUBLIC", "terms_note": TERMS_NOTE[:400]}

    def bot_source(self) -> dict:
        live = self.mode == "live"
        return {"platform": "telegram", "source_id": f"bot:{self.cfg.bot_label}:updates",
                "access_mode": "fetch" if live else "fixture", "collector": self.collector if live else self.collector + "/fixture",
                "rights_basis": "telegram_bot_api" if live else "synthetic_fixture", "visibility": "PUBLIC",
                "terms_note": TERMS_NOTE[:400]}

    def unit(self, connector: str, status: str, ref: str, error: str | None = None, body: Any = None) -> SourceUnit:
        error = self.scrub(error)[:300] if error else None
        return SourceUnit(connector=connector, platform="telegram", source_ref=ref, status=status,
                          unit_sha=canonical_sha(body if body is not None else [status, ref, error]),
                          body=body, error=error, plan_id=self.run_id)

    def build(self, con, records: list[dict], ref_prefix: str, fetched_at: float, now: float) -> list[SourceUnit]:
        per_chat: dict[str, list[tuple[int, dict]]] = {}
        units: list[SourceUnit] = []
        for r in records:
            if r.get("dropped"):
                self.dropped[r["dropped"]] = self.dropped.get(r["dropped"], 0) + 1
                continue
            if r.get("item"):
                per_chat.setdefault(r["chat_id"], []).append((r["update_id"] or 0, r["item"]))
        for cid, rows in per_chat.items():
            ch = self.cfg.by_id[cid]
            ids = [u for u, _ in rows]
            env = {"schema": INBOUND_SCHEMA_V3, "source": self.source(ch), "fetched_at": _iso(fetched_at),
                   "items": [it for _, it in rows]}
            units.append(self.unit(ch.connector, "OK", f"{ref_prefix}&updates={min(ids)}-{max(ids)}&chat={cid}", body=env))
        for r in records:     # membership after posts, so a removal in the same batch ends with the channel BLOCKED
            m = r.get("membership")
            if not m:
                continue
            ch = self.cfg.by_id[r["chat_id"]]
            state = membership_state(m["status"])
            _save_cursor(con, ch.connector, "membership", now, provider_scope_id=ch.chat_id, last_status=state,
                         newest_id=str(r["update_id"]), **({"last_success_at": now} if state == "OK" else {}))
            log_event("tg_membership", connector=ch.connector, status=m["status"], state=state)
            if state != "OK":
                units.append(self.unit(ch.connector, "BLOCKED", f"{ref_prefix}&membership={r['update_id']}",
                                       f"access_denied: bot is now '{m['status']}' in this channel (needs administrator)"))
        if self.dropped:
            log_event("tg_dropped", counts=dict(self.dropped))
        return units


def _committed(con, units: list[SourceUnit]) -> bool:
    for u in units:
        if u.status != "OK":
            continue
        r = con.execute("SELECT status FROM social_ingest_checkpoints WHERE connector=? AND source_ref=? AND unit_sha=?",
                        (u.connector, u.source_ref, u.unit_sha)).fetchone()
        if r is None or r[0] != "COMPLETE":
            return False
    return True


def store_connect(db_path: Path | str):
    import sqlite3
    from .schema import migrate
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    migrate(con)
    return con


def _log_request(con, connector: str, run_id: str | None, method: str, status: int, mode: str, now: float) -> None:
    """Request ledger (free API: cost 0). Live rows are the only live evidence health() accepts."""
    con.execute("INSERT INTO social_api_spend(connector,run_id,endpoint,http_status,billing_day,resources_json,est_cost_usd,"
                "mode,requested_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (connector, run_id, method, status, datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d"), None, 0.0,
                 mode, now))
    con.commit()


# ---------- polling adapter ----------

class TelegramBotAdapter:
    """SourceAdapter for getUpdates polling. One SourceUnit per channel per poll batch (inbound schema /3)."""

    name = "telegram_bot"

    def __init__(self, cfg: TgConfig, transport, token: str | None, db_path: Path | str, *, run_id: str | None = None,
                 mode: str = "live", clock: Callable[[], float] = time.time, sleep: Callable[[float], None] = time.sleep,
                 retries: int = 3, base_delay: float = 1.0):
        if mode not in ("live", "fixture"):
            raise ValueError("mode must be live or fixture")
        self.cfg, self.transport, self._token = cfg, transport, token
        self.db_path, self.run_id, self.mode = Path(db_path), run_id, mode
        self.clock, self.sleep, self.retries, self.base_delay = clock, sleep, retries, base_delay
        self.requests = 0
        self.builder = _UnitBuilder(cfg, mode, "telegram-bot-api", run_id, self._scrub)

    def __repr__(self) -> str:
        return f"TelegramBotAdapter(mode={self.mode!r}, channels={len(self.cfg.channels)}, token={'set' if self._token else 'missing'})"

    @property
    def dropped(self) -> dict:
        return dict(self.builder.dropped)

    def _scrub(self, s: str) -> str:
        if self._token:
            s = s.replace(self._token, "[REDACTED]")
        return redact(s)

    def call(self, con, method: str, params: dict, connector: str) -> tuple[TgResponse | None, str | None]:
        """(response, transport failure message). HTTP errors come back as responses."""
        def once():
            self.requests += 1
            try:
                r = self.transport.call(method, params, self._token)
            except (TransientError, FixtureMiss) as e:
                raise type(e)(self._scrub(str(e))) from None
            except Exception as e:
                raise RuntimeError(f"transport {type(e).__name__}: {self._scrub(str(e))[:160]}") from None
            if r.status >= 500:
                raise TransientError(f"HTTP {r.status}")
            return r
        try:
            r = with_retries(once, attempts=self.retries, base_delay=self.base_delay, sleep=self.sleep,
                             transient=(TransientError,), what=f"telegram {method}")
        except TransientError as e:
            _log_request(con, connector, self.run_id, method, 0, self.mode, self.clock())
            return None, f"{self._scrub(str(e))[:120]} after {self.retries} attempts"
        except FixtureMiss as e:
            return None, f"fixture: {e}"
        _log_request(con, connector, self.run_id, method, r.status, self.mode, r.received_at)
        log_event("tg_request", connector=connector, method=method, status=r.status, mode=self.mode)
        return r, None

    def units(self, budget: Budget) -> Iterator[SourceUnit]:
        bot = self.cfg.bot_connector
        b = self.builder
        if not self._token:
            yield b.unit(bot, "BLOCKED", f"{bot}#credentials", f"credentials_missing: set {TOKEN_ENV}")
            return
        con = store_connect(self.db_path)
        try:
            now = self.clock()
            cur = _cursor(con, bot, "updates")
            if cur and cur["rate_limit_reset_at"] and cur["rate_limit_reset_at"] > now:
                yield b.unit(bot, "RATE_LIMITED", f"{bot}#waiting", f"rate limited until {_iso(cur['rate_limit_reset_at'])}; not called")
                return
            if cur and cur["last_success_at"] and now - cur["last_success_at"] > UPDATE_RETENTION_S:
                hours = round((now - cur["last_success_at"]) / 3600, 1)
                yield b.unit(bot, "DEGRADED", f"{bot}#gap@{int(now)}",
                             f"gap: last successful poll {hours} h ago; Telegram keeps unconfirmed updates at most 24 h, "
                             "so channel posts in between may be lost")
            offset = int(cur["newest_id"]) + 1 if cur and cur["newest_id"] else None
            for poll in range(self.cfg.max_polls_per_run):
                try:
                    budget.charge("requests")
                except BudgetExceeded as e:
                    yield b.unit(bot, "DEGRADED", f"{bot}#offset={offset}&budget", f"run budget: {e}")
                    return
                params = {"limit": self.cfg.poll_limit, "timeout": self.cfg.long_poll_timeout, "allowed_updates": ALLOWED_UPDATES}
                if offset is not None:
                    params["offset"] = offset
                ref = f"{bot}#offset={offset if offset is not None else 'none'}"
                r, fail = self.call(con, "getUpdates", params, bot)
                if r is None:
                    _save_cursor(con, bot, "updates", self.clock(), last_status="DOWN")
                    yield b.unit(bot, "DOWN", ref, fail)
                    return
                body = r.body if isinstance(r.body, dict) else {}
                if r.status != 200 or body.get("ok") is not True:
                    st, access, msg = classify_error(r.status, body)
                    kw = {"last_status": access if access != "error" else st}
                    if st == "RATE_LIMITED":
                        kw["rate_limit_reset_at"] = r.received_at + retry_after(body)
                        msg += f"; retry after {retry_after(body):.0f} s"
                    _save_cursor(con, bot, "updates", self.clock(), **kw)
                    yield b.unit(bot, st, ref, f"{access}: {msg}")
                    return
                updates = [u for u in (body.get("result") or []) if isinstance(u, dict) and _int(u.get("update_id")) is not None]
                if not updates:
                    _save_cursor(con, bot, "updates", self.clock(), last_status="OK", last_success_at=self.clock(),
                                 rate_limit_reset_at=None)
                    if poll == 0:   # one OK row so the bot connector's health is current
                        yield b.unit(bot, "OK", f"{ref}&empty@{int(r.received_at)}",
                                     body={"schema": INBOUND_SCHEMA_V3, "source": b.bot_source(),
                                           "fetched_at": _iso(r.received_at), "items": []})
                    return
                records = [normalize_update(u, self.cfg, r.received_at) for u in updates]
                units = b.build(con, records, ref, r.received_at, self.clock())
                for u in units:
                    yield u
                newest = max(_int(u["update_id"]) for u in updates)
                if not _committed(con, units):
                    _save_cursor(con, bot, "updates", self.clock(), last_status="PARTIAL")
                    log_event("tg_cursor_held", connector=bot, reason="not every unit of the batch was committed")
                    return
                old = int(cur["newest_id"]) if cur and cur["newest_id"] else None
                keep = str(max(newest, old)) if old is not None else str(newest)    # never move backwards
                _save_cursor(con, bot, "updates", self.clock(), newest_id=keep, last_status="OK",
                             last_success_at=self.clock(), rate_limit_reset_at=None)
                cur = _cursor(con, bot, "updates")
                offset = int(keep) + 1
                if len(updates) < self.cfg.poll_limit:
                    return
        finally:
            con.close()


# ---------- webhook route ----------

def spool_dir() -> Path:
    return private.private_path().parent / "telegram_spool"


def webhook_receive(headers: dict, raw: bytes, *, cfg: TgConfig, secret: str | None, spool: Path, now: float,
                    mode: str = "live") -> tuple[int, dict]:
    """Handle one webhook POST. Returns (HTTP status for Telegram, small JSON result). The update is converted in
    memory; only the hashed record is written, under the update id, so a redelivered update is a no-op."""
    if not secret:
        return 503, {"error": "webhook secret not configured"}
    got = next((v for k, v in (headers or {}).items() if str(k).lower() == "x-telegram-bot-api-secret-token"), None)
    if not isinstance(got, str) or not hmac.compare_digest(got.encode(), secret.encode()):
        log_event("tg_webhook_rejected", reason="secret token mismatch")
        return 401, {"error": "secret token mismatch"}
    if raw is None or len(raw) > WEBHOOK_MAX_BYTES:
        return 413, {"error": "body too large"}
    try:
        upd = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return 400, {"error": "body is not JSON"}
    if not isinstance(upd, dict) or _int(upd.get("update_id")) is None:
        return 400, {"error": "no update_id"}
    rec = normalize_update(upd, cfg, now)
    rec.update({"schema": SPOOL_SCHEMA, "received_at": now, "mode": mode})
    if rec["dropped"]:
        log_event("tg_webhook_dropped", reason=rec["dropped"], update_id=rec["update_id"])
        return 200, {"stored": False, "dropped": rec["dropped"]}
    spool.mkdir(parents=True, exist_ok=True)
    f = spool / f"{rec['update_id']:015d}.json"
    if f.exists() or (spool / "done" / f.name).exists():
        return 200, {"stored": False, "duplicate": True}
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(rec, sort_keys=True))
    tmp.replace(f)
    return 200, {"stored": True}


class WebhookSpoolAdapter:
    """Ingests spooled webhook records. Units are grouped per channel and mode; a file moves to spool/done/ once every
    unit that used it is committed."""

    name = "telegram_bot_webhook"

    def __init__(self, cfg: TgConfig, spool: Path, db_path: Path | str, *, run_id: str | None = None,
                 clock: Callable[[], float] = time.time, batch: int = 100):
        self.cfg, self.spool, self.db_path, self.run_id, self.clock, self.batch = cfg, Path(spool), Path(db_path), run_id, clock, batch
        self.files_done = 0

    def units(self, budget: Budget) -> Iterator[SourceUnit]:
        files = sorted(self.spool.glob("*.json")) if self.spool.exists() else []
        recs = []
        for f in files:
            try:
                r = json.loads(f.read_text())
                if r.get("schema") != SPOOL_SCHEMA or r.get("mode") not in ("live", "fixture"):
                    raise ValueError("not a spool record")
                recs.append((f, r))
            except (ValueError, OSError):
                log_event("tg_spool_unreadable", file=f.name)
        con = store_connect(self.db_path)
        try:
            for mode in ("live", "fixture"):
                group = [(f, r) for f, r in recs if r["mode"] == mode]
                b = _UnitBuilder(self.cfg, mode, "telegram-bot-api/webhook", self.run_id, redact)
                for i in range(0, len(group), self.batch):
                    chunk = group[i:i + self.batch]
                    fetched = max(r["received_at"] for _, r in chunk)
                    units = b.build(con, [r for _, r in chunk], f"{self.cfg.bot_connector}#webhook", fetched, self.clock())
                    for u in units:
                        yield u
                    if _committed(con, units):
                        done = self.spool / "done"
                        done.mkdir(exist_ok=True)
                        for f, _ in chunk:
                            f.replace(done / f.name)
                            self.files_done += 1
        finally:
            con.close()


def purge_spool(spool: Path, older_than_days: float, now: float) -> int:
    """Delete processed spool records older than the retention period (Bot Platform terms 4.2: keep no longer than needed)."""
    n = 0
    for f in (Path(spool) / "done").glob("*.json") if (Path(spool) / "done").exists() else []:
        if now - f.stat().st_mtime > older_than_days * 86400:
            f.unlink()
            n += 1
    return n


# ---------- health and access check ----------

def check_access(cfg: TgConfig, transport, token: str, db_path: Path | str, *, mode: str = "live", run_id: str | None = None,
                 clock: Callable[[], float] = time.time, sleep: Callable[[float], None] = time.sleep) -> dict:
    """getMe, then getChat and getChatMember(bot) per approved channel. Writes each channel's membership cursor.
    Free calls; read-only."""
    ad = TelegramBotAdapter(cfg, transport, token, db_path, run_id=run_id, mode=mode, clock=clock, sleep=sleep)
    out: dict = {"bot": None, "channels": {}}
    con = store_connect(db_path)
    try:
        r, fail = ad.call(con, "getMe", {}, cfg.bot_connector)
        if r is None or r.status != 200 or not (r.body or {}).get("ok"):
            st, access, msg = classify_error(r.status, r.body) if r is not None else ("DOWN", "error", fail)
            out["bot"] = {"state": access, "detail": ad._scrub(msg)}
            return out
        me = r.body["result"]
        bot_id = me.get("id")
        out["bot"] = {"state": "OK", "is_bot": me.get("is_bot") is True}
        for ch in cfg.channels:
            r, fail = ad.call(con, "getChat", {"chat_id": ch.chat_id}, ch.connector)
            if r is None or r.status != 200 or not (r.body or {}).get("ok"):
                st, access, msg = classify_error(r.status, r.body) if r is not None else ("DOWN", "error", fail)
                res = {"state": access, "detail": ad._scrub(msg)}
            else:
                c = r.body["result"]
                if c.get("type") != "channel":
                    res = {"state": "not_a_channel"}
                elif not c.get("username"):
                    res = {"state": "not_public", "detail": "channel has no public username; D-009 allows public content only"}
                else:
                    r2, fail2 = ad.call(con, "getChatMember", {"chat_id": ch.chat_id, "user_id": bot_id}, ch.connector)
                    if r2 is None or r2.status != 200 or not (r2.body or {}).get("ok"):
                        st, access, msg = classify_error(r2.status, r2.body) if r2 is not None else ("DOWN", "error", fail2)
                        res = {"state": access, "detail": ad._scrub(msg)}
                    else:
                        status = (r2.body["result"] or {}).get("status")
                        res = {"state": membership_state(status), "member_status": status, "username": c.get("username")}
            out["channels"][ch.chat_id] = res
            _save_cursor(con, ch.connector, "membership", clock(), provider_scope_id=ch.chat_id, last_status=res["state"],
                         **({"last_success_at": clock()} if res["state"] == "OK" else {}))
    finally:
        con.close()
    out["requests_made"] = ad.requests
    return out


def health(config_path: Path | str | None, db_path: Path | str, env: dict | None = None, now: float | None = None,
           access: dict | None = None) -> dict:
    """Health without a network call (unless the caller ran check_access and passes its result).
    Status: credentials_missing | not_configured | access_denied | access_unverified | ready."""
    t = time.time() if now is None else now
    token = get_token(env)
    out: dict = {"adapter": "telegram_bot", "contract_verified": CONTRACT_VERIFIED, "bot_api_version_seen": BOT_API_VERSION_SEEN,
                 "token_env": TOKEN_ENV, "credentials": "present" if token else "missing",
                 "webhook_secret": "present" if get_secret(env) else "missing",
                 "network_calls_made": (access or {}).get("requests_made", 0)}
    cfg = None
    if config_path and Path(config_path).exists():
        try:
            cfg = load_config(config_path)
        except Exception as e:
            out["config_error"] = redact(str(e))[:200]
    con = store_connect(db_path)
    try:
        chans = []
        for ch in (cfg.channels if cfg else []):
            m = _cursor(con, ch.connector, "membership")
            chans.append({"connector": ch.connector, "chat_id": ch.chat_id, "username": ch.username, "approval": ch.approval,
                          "access": m["last_status"] if m else "unverified",
                          "access_checked_at": m["last_attempt_at"] if m else None})
        out["channels"] = chans
        live = con.execute("SELECT COUNT(*), MAX(requested_at) FROM social_api_spend WHERE mode='live' AND connector LIKE 'telegram_bot:%'").fetchone()
        ok_live = con.execute("SELECT COUNT(*) FROM social_api_spend WHERE mode='live' AND connector LIKE 'telegram_bot:%'"
                              " AND http_status=200 AND endpoint='getUpdates'").fetchone()[0]
        out["live_evidence"] = {"requests": live[0], "successful_polls": ok_live, "last_request_at": live[1],
                                "verdict": "live authorized ingest proved" if ok_live else "none: no live Telegram Bot API read has been made"}
        cur = _cursor(con, cfg.bot_connector, "updates") if cfg else None
        out["update_cursor"] = None if cur is None else {
            "last_update_id": cur["newest_id"], "last_status": cur["last_status"], "last_success_at": cur["last_success_at"],
            "age_hours": round((t - cur["last_success_at"]) / 3600, 1) if cur["last_success_at"] else None,
            "gap_risk": bool(cur["last_success_at"] and t - cur["last_success_at"] > UPDATE_RETENTION_S),
            "rate_limit_reset_at": cur["rate_limit_reset_at"]}
        out["connector_health"] = [dict(r) for r in con.execute(
            "SELECT h.connector, h.status, h.checked_at, h.error FROM social_connector_health h WHERE h.connector LIKE 'telegram_bot:%'"
            " AND h.checked_at=(SELECT MAX(checked_at) FROM social_connector_health WHERE connector=h.connector) ORDER BY h.connector")]
    finally:
        con.close()
    if access:
        out["access_check"] = access
    states = [c["access"] for c in out["channels"]]
    if not token:
        out["status"] = "credentials_missing"
    elif cfg is None or not cfg.channels:
        out["status"] = "not_configured"
    elif access and (access.get("bot") or {}).get("state") not in (None, "OK"):
        out["status"] = "access_denied" if access["bot"]["state"] != "error" else "access_unverified"
    elif any(s not in ("OK", "unverified") for s in states):
        out["status"] = "access_denied"
    elif any(s == "unverified" for s in states):
        out["status"] = "access_unverified"
    else:
        out["status"] = "ready"
    out["next_step"] = {
        "credentials_missing": f"create a bot with @BotFather and export {TOKEN_ENV} in the shell that runs memelab "
                               "(docs/social-intelligence/TELEGRAM_04.md, 'How to authorize it')",
        "not_configured": "write the channel list (docs/social-intelligence/telegram_bot.example.json) to data/private/telegram_bot.json",
        "access_denied": "a channel admin must add the bot as an administrator; private channels (no username) are not read",
        "access_unverified": "run `social tg-health --check-access` (read-only getMe/getChat/getChatMember calls)",
        "ready": "run `social tg-ingest` and check `social tg-health` live_evidence",
    }[out["status"]]
    return out
