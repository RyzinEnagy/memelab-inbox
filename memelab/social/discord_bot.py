"""Discord community monitoring through an installed bot (Phase 20, optional Prompt 20).

Contract read 2026-10-12 on docs.discord.com (DISCORD_20.md in docs/social-intelligence has the sources and gaps):

  REST  https://discord.com/api/v10, header "Authorization: Bot <token>", User-Agent "DiscordBot (<url>, <version>)"
    GET /applications/@me                 application flags: GATEWAY_MESSAGE_CONTENT (1<<18, verified apps in 100+
                                          servers) and GATEWAY_MESSAGE_CONTENT_LIMITED (1<<19, under 100 servers)
    GET /users/@me                        the bot's own user id
    GET /guilds/{guild}                   owner_id, roles (permissions are strings), features
    GET /guilds/{guild}/members/{bot}     the bot's roles in that server
    GET /channels/{channel}               type, guild_id, permission_overwrites
    GET /channels/{channel}/messages      after|before|around (one at a time), limit 1-100; needs VIEW_CHANNEL, and
                                          returns no messages without READ_MESSAGE_HISTORY
    GET /channels/{channel}/messages/{id} recheck of a stored message; 404 with code 10008 = Unknown Message
  Rate limits: X-RateLimit-Limit/-Remaining/-Reset/-Reset-After/-Bucket; on 429 also -Global and -Scope (user,
    global, shared) and a body {message, retry_after, global, code}; 50 requests per second per bot; 10,000 invalid
    requests (401, 403, 429 except scope shared) per 10 minutes lead to a temporary IP restriction.
  Gateway: op 10 Hello, 1 Heartbeat, 11 Heartbeat ACK, 2 Identify (token, intents), 0 Dispatch (t, s, d), 6 Resume
    (session_id, seq), 7 Reconnect, 9 Invalid Session (d = resumable). Close codes 4004 authentication failed,
    4013 invalid intents and 4014 disallowed intents do not allow a reconnect. MESSAGE_CONTENT (1<<15) is a privileged
    intent: without it content, embeds, attachments, components and poll come back empty (except messages that
    mention the app, DMs with it and its own messages). GUILD_MESSAGES (1<<9) carries MESSAGE_CREATE, MESSAGE_UPDATE,
    MESSAGE_DELETE and MESSAGE_DELETE_BULK. GUILD_DELETE without "unavailable" means the bot was removed.
  Messages: id, channel_id, author (user; webhook messages carry webhook_id), content, timestamp, edited_timestamp,
    type (19 REPLY), message_reference (type 0 DEFAULT = reply, 1 FORWARD = message_snapshots), referenced_message.
  Policy: bots only. "Automating normal user accounts (generally called "self-bots") outside of the OAuth2/bot API is
    forbidden" (Discord support article 115002192352). The Developer Policy forbids mining or scraping, profiling users,
    selling API data and training models on message content; the Developer Terms 5(b) require deleting API data that
    is no longer necessary and giving users a way to ask for deletion.

What this adapter refuses, before any request (D-133, D-134):
  - no bot token (env DISCORD_BOT_TOKEN), a token or invite in the config, a user token or self-bot setting;
  - a server without a recorded consent (own_server or server_admin_installed_bot). A public invite is never consent;
  - private messages: no DM endpoint is called and the gateway never asks for DIRECT_MESSAGES intents;
  - channels the server does not show to @everyone (role-gated), channels the bot cannot view or read history in,
    channels whose guild_id differs from the configured server, and channel types other than text and announcement;
  - message content when the application has no message-content flag (require_message_content true, the default);
    with require_message_content false the run keeps ids, times and references only and says so on every unit.

What is stored per message (D-010, D-013, D-016): channel id and message id (provider id "<channel>_<message>"), link
https://discord.com/channels/<guild>/<channel>/<message>, author user id and username (never the display name, avatar
or roles; no author for bots and webhooks), send and edit time, sha256 of the content (or of the forwarded snapshot),
reply, forward and message-link references as ids, attachment, embed and reaction counts. Never: the words, embeds,
attachments, mentions, member lists, presences or anything from a DM.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

from . import store
from .api_common import (FixtureMiss, FixtureTransport as _FT, HttpResponse, RequestGuard, TextSink, connect, erase_accounts,
                         get_cursor, iso, purge_gone_items, save_cursor, scrub, units_committed)
from .ingest import INBOUND_SCHEMA_V3, Budget, SourceUnit, TransientError, canonical_sha, log_event, redact, with_retries

PLATFORM = "discord"
TOKEN_ENV = "DISCORD_BOT_TOKEN"
CONFIG_SCHEMA = "memelab.discord_bot.config/1"
FIXTURE_SCHEMA = "memelab.discord_bot.fixture/1"
GATEWAY_FIXTURE_SCHEMA = "memelab.discord_gateway.fixture/1"
CONTRACT_VERIFIED = "2026-10-12"
API_BASE = "https://discord.com/api/v10"
USER_AGENT = "DiscordBot (https://github.com/RyzinEnagy/memelab-inbox, 0.20)"
DISCORD_EPOCH_MS = 1420070400000

# application flags, intents and permission bits (docs.discord.com, read 2026-10-12)
APP_MESSAGE_CONTENT, APP_MESSAGE_CONTENT_LIMITED = 1 << 18, 1 << 19
INTENT_GUILDS, INTENT_GUILD_MESSAGES, INTENT_MESSAGE_CONTENT = 1 << 0, 1 << 9, 1 << 15
INTENT_DIRECT_MESSAGES = (1 << 12) | (1 << 13) | (1 << 14)          # never requested
PERM_ADMINISTRATOR, PERM_VIEW_CHANNEL, PERM_READ_HISTORY = 1 << 3, 1 << 10, 1 << 16
ALL_PERMISSIONS = (1 << 64) - 1
TEXT_CHANNEL_TYPES = {0: "GUILD_TEXT", 5: "GUILD_ANNOUNCEMENT"}
MSG_DEFAULT, MSG_REPLY = 0, 19
CONSENT_BASES = ("own_server", "server_admin_installed_bot")
SERVER_VISIBILITY = ("discoverable", "open_invite")
FATAL_CLOSE = {4004: "credentials_rejected", 4010: "invalid_shard", 4011: "sharding_required", 4012: "invalid_api_version",
               4013: "invalid_intents", 4014: "privileged_intent_missing"}

SNOWFLAKE = re.compile(r"^[0-9]{15,21}$")
USERNAME = re.compile(r"^[a-z0-9_.]{2,32}$")
LABEL = re.compile(r"^[A-Za-z0-9_.\-]{1,40}$")
MESSAGE_LINK = re.compile(r"https://(?:ptb\.|canary\.)?discord(?:app)?\.com/channels/([0-9]{15,21}|@me)/([0-9]{15,21})/([0-9]{15,21})")
INVITE = re.compile(r"(?i)(discord\.gg/|discord(?:app)?\.com/invite/)")
FORBIDDEN_CONFIG_KEYS = {"token", "bot_token", "secret", "client_secret", "password", "api_key", "user_token",
                         "authorization", "session_id", "invite", "invite_url", "invite_code"}
SELF_BOT_KEYS = {"user_token", "self_bot", "selfbot", "user_account"}
TERMS_NOTE = ("Discord bot API: only channels of servers that installed the bot with recorded consent and that @everyone "
              "can view; no DMs; content needs the message-content intent; text hashed and dropped; forwards and "
              "link-only shares never counted as independent originals; deleted messages purged")


def snowflake_time(sf: str) -> float:
    return ((int(sf) >> 22) + DISCORD_EPOCH_MS) / 1000.0


def pid(channel_id: str, message_id: str) -> str:
    return f"{channel_id}_{message_id}"


# ---------- config ----------

@dataclass
class Channel:
    channel_id: str
    label: str
    guild_id: str

    @property
    def connector(self) -> str:
        return f"discord_bot:channel:{self.channel_id}"


@dataclass
class Guild:
    guild_id: str
    label: str
    consent_basis: str | None
    consent_reference: str | None
    server_visibility: str | None
    channels: list[Channel]

    @property
    def consented(self) -> bool:
        return self.consent_basis in CONSENT_BASES and bool(self.consent_reference)


@dataclass
class DiscordConfig:
    bot_label: str
    guilds: list[Guild]
    require_message_content: bool = True
    page_size: int = 100
    backfill_max_pages: int = 1
    max_pages_per_channel: int = 3
    max_requests_per_run: int = 40
    max_invalid_requests_per_run: int = 10
    max_wait_seconds: float = 5.0
    recheck: bool = True
    recheck_max_items: int = 25
    gateway_max_events: int = 500
    timeout_seconds: float = 20.0
    by_channel: dict = field(default_factory=dict)

    def __post_init__(self):
        self.by_channel = {c.channel_id: c for g in self.guilds for c in g.channels}

    def guild(self, gid: str) -> Guild | None:
        return next((g for g in self.guilds if g.guild_id == gid), None)


def load_config(obj: dict | str | Path) -> DiscordConfig:
    if not isinstance(obj, dict):
        obj = json.loads(Path(obj).read_text())
    if obj.get("schema") != CONFIG_SCHEMA:
        raise ValueError(f"config schema must be {CONFIG_SCHEMA}")

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                kl = str(k).lower()
                if kl in SELF_BOT_KEYS:
                    raise ValueError(f"config key '{k}': user tokens and self-bots are forbidden by Discord; only a bot installed by the server")
                if kl in FORBIDDEN_CONFIG_KEYS:
                    raise ValueError(f"config must not hold credentials or invites (key '{k}'); the bot token goes in {TOKEN_ENV}")
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str) and INVITE.search(o):
            raise ValueError("config holds an invite link: an invite never grants collection rights; record the server's consent instead")
    walk(obj)
    label = obj.get("bot_label")
    if not isinstance(label, str) or not LABEL.match(label):
        raise ValueError("bot_label: 1-40 letters, digits, '_', '.' or '-'")
    guilds, seen_g, seen_c = [], set(), set()
    for i, g in enumerate(obj.get("guilds") or []):
        gid = g.get("guild_id") if isinstance(g, dict) else None
        if not isinstance(gid, str) or not SNOWFLAKE.match(gid):
            raise ValueError(f"guilds[{i}].guild_id: a Discord id (snowflake) as a string")
        if gid in seen_g:
            raise ValueError(f"guilds[{i}]: duplicate server")
        seen_g.add(gid)
        glabel = g.get("label") or gid
        if not isinstance(glabel, str) or not LABEL.match(glabel):
            raise ValueError(f"guilds[{i}].label: 1-40 letters, digits, '_', '.' or '-'")
        consent = g.get("consent") or {}
        basis = consent.get("basis")
        if basis is not None and basis not in CONSENT_BASES:
            raise ValueError(f"guilds[{i}].consent.basis: one of {', '.join(CONSENT_BASES)} (a public invite is not consent)")
        vis = g.get("server_visibility")
        if vis is not None and vis not in SERVER_VISIBILITY:
            raise ValueError(f"guilds[{i}].server_visibility: one of {', '.join(SERVER_VISIBILITY)}")
        chans = []
        for j, c in enumerate(g.get("channels") or []):
            cid = c.get("channel_id") if isinstance(c, dict) else None
            if not isinstance(cid, str) or not SNOWFLAKE.match(cid):
                raise ValueError(f"guilds[{i}].channels[{j}].channel_id: a Discord id (snowflake) as a string")
            if cid in seen_c:
                raise ValueError(f"guilds[{i}].channels[{j}]: duplicate channel")
            seen_c.add(cid)
            cl = c.get("label") or cid
            if not isinstance(cl, str) or not LABEL.match(cl):
                raise ValueError(f"guilds[{i}].channels[{j}].label: 1-40 letters, digits, '_', '.' or '-'")
            chans.append(Channel(cid, cl, gid))
        ref = consent.get("reference")
        guilds.append(Guild(gid, glabel, basis, ref if isinstance(ref, str) and ref.strip() else None, vis, chans))
    rc = obj.get("recheck") or {}
    if obj.get("require_message_content", True) not in (True, False):
        raise ValueError("require_message_content: true or false")
    return DiscordConfig(bot_label=label, guilds=guilds, require_message_content=obj.get("require_message_content", True) is True,
                         page_size=max(1, min(int(obj.get("page_size", 100)), 100)),
                         backfill_max_pages=max(1, int(obj.get("backfill_max_pages", 1))),
                         max_pages_per_channel=max(1, int(obj.get("max_pages_per_channel", 3))),
                         max_requests_per_run=max(1, int(obj.get("max_requests_per_run", 40))),
                         max_invalid_requests_per_run=max(1, int(obj.get("max_invalid_requests_per_run", 10))),
                         max_wait_seconds=max(0.0, float(obj.get("max_wait_seconds", 5))),
                         recheck=rc.get("enabled", True) is True, recheck_max_items=max(1, min(int(rc.get("max_items", 25)), 200)),
                         gateway_max_events=max(1, int(obj.get("gateway_max_events", 500))))


def get_token(env: dict | None = None) -> str | None:
    import os
    e = env if env is not None else os.environ
    return e.get(TOKEN_ENV, "").strip() or None


# ---------- permissions (docs.discord.com/developers/topics/permissions) ----------

def _bits(v: Any) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def compute_permissions(*, guild_id: str, owner_id: str | None, roles: list[dict], member_id: str, member_roles: list[str],
                        overwrites: list[dict]) -> int:
    """The documented algorithm: owner has everything; @everyone role OR member roles; ADMINISTRATOR has everything;
    then overwrites in order @everyone, member roles (deny aggregated then allow aggregated), member."""
    if owner_id and owner_id == member_id:
        return ALL_PERMISSIONS
    by_id = {str(r.get("id")): _bits(r.get("permissions")) for r in roles if isinstance(r, dict)}
    perms = by_id.get(guild_id, 0)
    for rid in member_roles:
        perms |= by_id.get(str(rid), 0)
    if perms & PERM_ADMINISTRATOR:
        return ALL_PERMISSIONS
    ow = {str(o.get("id")): o for o in overwrites if isinstance(o, dict)}
    ev = ow.get(guild_id)
    if ev:
        perms = (perms & ~_bits(ev.get("deny"))) | _bits(ev.get("allow"))
    allow = deny = 0
    for rid in member_roles:
        o = ow.get(str(rid))
        if o and o.get("type", 0) == 0:
            allow |= _bits(o.get("allow"))
            deny |= _bits(o.get("deny"))
    perms = (perms & ~deny) | allow
    mo = ow.get(member_id)
    if mo and mo.get("type", 1) == 1:
        perms = (perms & ~_bits(mo.get("deny"))) | _bits(mo.get("allow"))
    return perms


def everyone_can_view(*, guild_id: str, roles: list[dict], overwrites: list[dict]) -> bool:
    """A channel is public inside the server when a member with no role can view it (no role gate)."""
    perms = compute_permissions(guild_id=guild_id, owner_id=None, roles=roles, member_id="0", member_roles=[], overwrites=overwrites)
    return bool(perms & PERM_VIEW_CHANNEL)


@dataclass
class ChannelAccess:
    readable: bool
    public: bool
    reason: str | None


def channel_access(ch: Channel, channel_obj: dict, guild_obj: dict, bot_id: str, bot_roles: list[str]) -> ChannelAccess:
    if str(channel_obj.get("guild_id")) != ch.guild_id:
        return ChannelAccess(False, False, "config_mismatch: channel belongs to another server")
    t = channel_obj.get("type")
    if t not in TEXT_CHANNEL_TYPES:
        return ChannelAccess(False, False, f"unsupported_channel_type: {str(t)[:8]} (only text and announcement channels)")
    roles, ow = guild_obj.get("roles") or [], channel_obj.get("permission_overwrites") or []
    public = everyone_can_view(guild_id=ch.guild_id, roles=roles, overwrites=ow)
    if not public:
        return ChannelAccess(False, False, "not_public: the channel is hidden from @everyone (role-gated); not read")
    p = compute_permissions(guild_id=ch.guild_id, owner_id=str(guild_obj.get("owner_id") or ""), roles=roles, member_id=bot_id,
                            member_roles=[str(r) for r in bot_roles], overwrites=ow)
    if not p & PERM_VIEW_CHANNEL:
        return ChannelAccess(False, True, "access_denied: the bot lacks VIEW_CHANNEL in this channel")
    if not p & PERM_READ_HISTORY:
        return ChannelAccess(False, True, "access_denied: the bot lacks READ_MESSAGE_HISTORY in this channel")
    return ChannelAccess(True, True, None)


# ---------- transport ----------

class UrllibTransport:
    """The only code that talks to discord.com. The token goes into the Authorization header only."""

    def __init__(self, timeout: float = 20.0, clock: Callable[[], float] = time.time):
        self.timeout, self.clock = timeout, clock

    def request(self, method: str, path: str, params: dict | None, secret: str | None) -> HttpResponse:
        url = API_BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
        req = urllib.request.Request(url, method=method, headers={"Authorization": f"Bot {secret}", "User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                status, headers, raw = r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
        except urllib.error.HTTPError as e:
            status, headers, raw = e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, e.read() or b""
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise TransientError(f"network: {type(e).__name__}") from None
        try:
            body = json.loads(raw.decode("utf-8")) if raw else None
        except ValueError:
            body = None
        return HttpResponse(status, headers, body, self.clock())


class FixtureTransport(_FT):
    def __init__(self, fixture):
        super().__init__(fixture, FIXTURE_SCHEMA)


# ---------- message -> inbound item ----------

def _int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _ts(v) -> float | None:
    try:
        return store.to_utc(v)
    except (TypeError, ValueError):
        return None


def message_item(msg: dict, ch: Channel, fetched_at: float, sink: TextSink | None, *, content_available: bool
                 ) -> tuple[dict | None, str | None]:
    """One message object -> (inbound/3 item, drop reason). The words are hashed here and go no further, except into
    the in-memory sink when the caller asked for extraction."""
    mid = str(msg.get("id") or "")
    if not SNOWFLAKE.match(mid):
        return None, "missing_ids"
    if str(msg.get("channel_id") or ch.channel_id) != ch.channel_id:
        return None, "other_channel"
    mtype = msg.get("type", MSG_DEFAULT)
    if mtype not in (MSG_DEFAULT, MSG_REPLY):
        return None, "system_message"          # joins, pins, boosts, thread starters ...: not posts
    created = _ts(msg.get("timestamp")) or snowflake_time(mid)
    edited = _ts(msg.get("edited_timestamp"))
    version_at = edited if edited and edited > created else created
    ref = msg.get("message_reference") if isinstance(msg.get("message_reference"), dict) else {}
    snaps = msg.get("message_snapshots") if isinstance(msg.get("message_snapshots"), list) else []
    forward = None
    refs: list[dict] = []
    if ref.get("type") == 1:      # FORWARD: the words are the snapshot's, not the forwarder's
        oc, om = str(ref.get("channel_id") or ""), str(ref.get("message_id") or "")
        ok = SNOWFLAKE.match(oc) and SNOWFLAKE.match(om)
        snap = (snaps[0].get("message") if snaps and isinstance(snaps[0], dict) else None) or {}
        forward = {"origin_type": "channel", "origin_chat_id": oc if ok else None, "origin_message_id": om if ok else None,
                   "origin_provider_item_id": pid(oc, om) if ok else None,
                   "origin_published_at": iso(_ts(snap.get("timestamp"))) if _ts(snap.get("timestamp")) else None,
                   "is_automatic_forward": False}
        text = snap.get("content") if isinstance(snap.get("content"), str) else None
    else:
        text = msg.get("content") if isinstance(msg.get("content"), str) else None
        if mtype == MSG_REPLY or (ref and ref.get("type", 0) == 0 and ref.get("message_id")):
            rc, rm = str(ref.get("channel_id") or ch.channel_id), str(ref.get("message_id") or "")
            if SNOWFLAKE.match(rc) and SNOWFLAKE.match(rm):
                rmsg = msg.get("referenced_message") if isinstance(msg.get("referenced_message"), dict) else {}
                ra = str((rmsg.get("author") or {}).get("id") or "")
                refs.append({"type": "replied_to", "provider_item_id": pid(rc, rm), "author_id": ra if SNOWFLAKE.match(ra) else None})
    text = text if text and text.strip() else None
    link_only = False
    if text and forward is None:
        links = [(g, c, m) for g, c, m in MESSAGE_LINK.findall(text) if g != "@me"]      # @me = a DM link: never followed
        rest = MESSAGE_LINK.sub("", text).strip()
        link_only = bool(links) and not rest
        for g, c, m in links[:5]:
            refs.append({"type": "retweeted" if link_only else "quoted", "provider_item_id": pid(c, m), "author_id": None})
    chash = store.text_hash(text) if text else None
    if sink is not None and text and chash:
        sink.put(PLATFORM, pid(ch.channel_id, mid), chash, text)
    rtype = ("REPOST" if forward or link_only else "REPLY" if any(r["type"] == "replied_to" for r in refs)
             else "QUOTE" if refs else "ORIGINAL")
    metrics = {}
    for k, key in (("attachment_count", "attachments"), ("embed_count", "embeds")):
        if isinstance(msg.get(key), list) and content_available:
            metrics[k] = len(msg[key])
    if isinstance(msg.get("reactions"), list):
        metrics["reaction_count"] = sum(r.get("count", 0) for r in msg["reactions"] if isinstance(r, dict) and _int(r.get("count")))
    author = msg.get("author") if isinstance(msg.get("author"), dict) else {}
    aid, uname = str(author.get("id") or ""), author.get("username")
    is_bot = author.get("bot") is True or msg.get("webhook_id") is not None
    item = {
        # same message in the same version = same event, whether it came from REST, the gateway or a replay; metrics
        # (embed unfurls, reactions) do not make a new event, an edit does
        "event_id": f"dc.{pid(ch.channel_id, mid)}.v{int(version_at * 1000)}." + canonical_sha([chash, forward, [(r["type"], r["provider_item_id"]) for r in refs]])[:12],
        "provider_item_id": pid(ch.channel_id, mid),
        "url": f"https://discord.com/channels/{ch.guild_id}/{ch.channel_id}/{mid}",
        "published_at": iso(created),
        "published_at_basis": "PROVIDER",
        "fetched_at": iso(fetched_at),
        "retrieval_status": "OK",
        "content_hash": chash,
        "metrics": metrics or None,
        "visibility": "PUBLIC",
        "context": {"reference_type": rtype, "conversation_id": None, "in_reply_to_user_id": None, "edit_history_ids": None,
                    "referenced": refs[:10], "basis": "PROVIDER"},
        "forward": forward,
        "version": {"kind": "EDIT" if version_at != created else "ORIGINAL", "provider_version_at": iso(version_at)},
    }
    if not is_bot and SNOWFLAKE.match(aid):    # bots and webhooks get no author: never an independent source (D-042)
        item["account"] = {"provider_user_id": aid, "profile_url": f"https://discord.com/users/{aid}",
                           **({"handle": uname} if isinstance(uname, str) and USERNAME.match(uname) else {})}
    return {k: v for k, v in item.items() if v is not None}, None


def deleted_item(ch: Channel, mid: str, at: float, status: str = "DELETED") -> dict:
    return {"event_id": f"dc.{pid(ch.channel_id, mid)}.{status.lower()}", "provider_item_id": pid(ch.channel_id, mid),
            "url": f"https://discord.com/channels/{ch.guild_id}/{ch.channel_id}/{mid}", "fetched_at": iso(at),
            "retrieval_status": status, "visibility": "PUBLIC"}


def classify_error(status: int, body: Any) -> tuple[str, str]:
    code = body.get("code") if isinstance(body, dict) else None
    msg = redact(str(body.get("message") or ""))[:60] if isinstance(body, dict) else ""
    if status == 401:
        return "BLOCKED", f"credentials_rejected: 401 {msg}"
    if status == 403 or code in (50001, 50013):
        return "BLOCKED", f"access_denied: 403 code {code}; the bot lost access or permissions"
    if status == 404 and code == 10003:
        return "BLOCKED", "access_denied: 404 unknown channel (deleted, or not visible to the bot)"
    if status == 404 and code == 10004:
        return "BLOCKED", "access_denied: 404 unknown server (the bot is not a member)"
    if status == 404:
        return "DOWN", f"404 code {code}"
    if status == 429:
        return "RATE_LIMITED", "429 rate limited"
    return "DOWN", f"HTTP {status} code {code}"


# ---------- REST adapter ----------

class DiscordBotAdapter:
    """SourceAdapter for configured channels over the REST API. One SourceUnit per page or stop condition, inbound /3."""

    name = "discord_bot"

    def __init__(self, cfg: DiscordConfig, transport, token: str | None, db_path: Path | str, *, run_id: str | None = None,
                 mode: str = "live", clock: Callable[[], float] = time.time, sleep: Callable[[float], None] = time.sleep,
                 retries: int = 3, base_delay: float = 1.0, text_sink: TextSink | None = None):
        if mode not in ("live", "fixture"):
            raise ValueError("mode must be live or fixture")
        self.cfg, self.transport, self._token = cfg, transport, token
        self.db_path, self.run_id, self.mode = Path(db_path), run_id, mode
        self.clock, self.sleep, self.retries, self.base_delay = clock, sleep, retries, base_delay
        self.sink = text_sink
        self.requests = 0
        self.invalid = 0
        self.stopped: str | None = None
        self.content_available = False
        self.intent_status: str | None = None
        self.dropped: dict[str, int] = {}

    def __repr__(self) -> str:
        return (f"DiscordBotAdapter(mode={self.mode!r}, channels={len(self.cfg.by_channel)}, "
                f"token={'set' if self._token else 'missing'})")

    def _scrub(self, s: str) -> str:
        return scrub(s, self._token)

    def _source(self, ch: Channel | None, g: Guild | None = None) -> dict:
        live = self.mode == "live"
        basis = (g.consent_basis if g else None) or "consent"
        return {"platform": PLATFORM, "source_id": f"bot:{self.cfg.bot_label}:" + (f"channel:{ch.channel_id}" if ch else "app"),
                "access_mode": "fetch" if live else "fixture", "collector": "discord-bot-rest" if live else "discord-bot-rest/fixture",
                "rights_basis": f"discord_bot_{basis}" if live else "synthetic_fixture", "visibility": "PUBLIC",
                "terms_note": TERMS_NOTE[:400]}

    def _unit(self, connector: str, status: str, ref: str, error: str | None = None, body: Any = None) -> SourceUnit:
        error = self._scrub(error)[:300] if error else None
        return SourceUnit(connector=connector, platform=PLATFORM, source_ref=ref, status=status,
                          unit_sha=canonical_sha(body if body is not None else [status, ref, error]), body=body, error=error,
                          plan_id=self.run_id)

    def _drop(self, why: str) -> None:
        self.dropped[why] = self.dropped.get(why, 0) + 1

    def _call(self, con, guard: RequestGuard, connector: str, endpoint: str, path: str,
              params: dict | None = None) -> tuple[HttpResponse | None, str | None, str | None]:
        """(response, stop status, stop message). Handles 5xx retries, 429, bucket exhaustion and the invalid-request cap."""
        if self.stopped:
            return None, "DEGRADED", f"not run: {self.stopped}"
        why = guard.check()
        if why:
            self.stopped = f"run budget: {why}"
            return None, "DEGRADED", self.stopped

        def once():
            self.requests += 1
            try:
                r = self.transport.request("GET", path, params, self._token)
            except (TransientError, FixtureMiss) as e:
                raise type(e)(self._scrub(str(e))) from None
            except Exception as e:
                raise RuntimeError(f"transport {type(e).__name__}: {self._scrub(str(e))[:160]}") from None
            if r.status >= 500:
                raise TransientError(f"HTTP {r.status}")
            return r
        try:
            r = with_retries(once, attempts=self.retries, base_delay=self.base_delay, sleep=self.sleep,
                             transient=(TransientError,), what=f"discord {endpoint}")
        except TransientError as e:
            guard.record(connector=connector, run_id=self.run_id, endpoint=endpoint, status=0, resources={}, now=self.clock())
            return None, "DOWN", f"{self._scrub(str(e))[:120]} after {self.retries} attempts"
        except FixtureMiss as e:
            return None, "DOWN", f"fixture: {e}"
        n = len(r.body) if isinstance(r.body, list) else 0
        guard.record(connector=connector, run_id=self.run_id, endpoint=endpoint, status=r.status, resources={"objects": n},
                     now=r.received_at)
        log_event("discord_request", connector=connector, endpoint=endpoint, status=r.status,
                  remaining=r.headers.get("x-ratelimit-remaining"), mode=self.mode)
        shared = r.headers.get("x-ratelimit-scope") == "shared"
        if r.status in (401, 403) or (r.status == 429 and not shared):
            self.invalid += 1
            if self.invalid >= self.cfg.max_invalid_requests_per_run:
                self.stopped = (f"invalid-request cap {self.cfg.max_invalid_requests_per_run} reached (401/403/429); "
                                "stopping to stay far below Discord's limit")
        if r.status == 401:
            self.stopped = "credentials_rejected: 401"
        if r.status == 429:
            body = r.body if isinstance(r.body, dict) else {}
            if body.get("global") is True or r.headers.get("x-ratelimit-global") or r.headers.get("x-ratelimit-scope") == "global":
                self.stopped = f"global rate limit; retry after {self._retry_after(r):.1f} s"
        elif r.status == 200 and r.headers.get("x-ratelimit-remaining") == "0":
            wait = self._reset_after(r)
            if wait <= self.cfg.max_wait_seconds:
                self.sleep(wait)                 # bucket exhausted: wait for the documented reset, then continue
        return r, None, None

    @staticmethod
    def _retry_after(r: HttpResponse) -> float:
        for v in ((r.body or {}).get("retry_after") if isinstance(r.body, dict) else None, r.headers.get("retry-after")):
            try:
                return max(0.0, float(v))
            except (TypeError, ValueError):
                continue
        return 60.0

    @staticmethod
    def _reset_after(r: HttpResponse) -> float:
        try:
            return max(0.0, float(r.headers.get("x-ratelimit-reset-after")))
        except (TypeError, ValueError):
            return 1.0

    def _stop_channel(self, con, ch: Channel, status: str, msg: str, ref: str, r: HttpResponse | None = None) -> SourceUnit:
        kw: dict = {"last_status": msg.split(":", 1)[0] if status == "BLOCKED" else status}
        if status == "RATE_LIMITED" and r is not None:
            kw["rate_limit_reset_at"] = r.received_at + self._retry_after(r)
            msg += f"; retry after {self._retry_after(r):.1f} s"
        save_cursor(con, ch.connector, "messages", self.clock(), provider_scope_id=ch.guild_id, **kw)
        log_event("discord_channel_stopped", connector=ch.connector, status=status, error=self._scrub(msg))
        return self._unit(ch.connector, status, ref, msg)

    # -- SourceAdapter --
    def units(self, budget: Budget) -> Iterator[SourceUnit]:
        app = f"discord_bot:app:{self.cfg.bot_label}"
        chans = [(g, c) for g in self.cfg.guilds for c in g.channels]
        if not self._token:
            for g, c in chans or [(None, None)]:
                conn = c.connector if c else app
                yield self._unit(conn, "BLOCKED", f"{conn}#credentials", f"credentials_missing: set {TOKEN_ENV}")
            return
        con = connect(self.db_path)
        self.started_at = self.clock()
        try:
            guard = RequestGuard(con, connector_prefix="discord_bot:", mode=self.mode, max_requests=self.cfg.max_requests_per_run)
            todo = []
            for g, c in chans:
                if not g.consented:
                    yield self._unit(c.connector, "BLOCKED", f"{c.connector}#consent",
                                     "consent_missing: record the server's consent (own_server or server_admin_installed_bot "
                                     "with a reference); an invite is not consent")
                elif g.server_visibility not in SERVER_VISIBILITY:
                    yield self._unit(c.connector, "BLOCKED", f"{c.connector}#visibility",
                                     "not_public: server_visibility must be discoverable or open_invite")
                else:
                    todo.append((g, c))
            if not todo:
                return
            stop = yield from self._preflight(con, guard, app, todo)
            if stop:
                return
            guild_cache: dict[str, tuple[dict | None, list[str] | None]] = {}
            for g, c in todo:
                if self.stopped:
                    yield self._unit(c.connector, "DEGRADED", f"{c.connector}#not-run", f"not run: {self.stopped}")
                    continue
                try:
                    yield from self._channel(con, guard, g, c, guild_cache)
                except Exception as e:
                    yield self._unit(c.connector, "DOWN", f"{c.connector}#error",
                                     f"adapter error {type(e).__name__}: {self._scrub(str(e))[:160]}")
            if self.cfg.recheck and not self.stopped:
                try:
                    yield from self._recheck(con, guard)
                except Exception as e:
                    yield self._unit("discord_bot:recheck:stored", "DOWN", "discord_bot:recheck:stored#error",
                                     f"adapter error {type(e).__name__}: {self._scrub(str(e))[:160]}")
            if self.dropped:
                log_event("discord_dropped", counts=dict(self.dropped))
        finally:
            con.close()

    def _preflight(self, con, guard, app: str, todo):
        """Application flags (message content intent) and the bot's user id. Returns True to stop the run."""
        r, st, msg = self._call(con, guard, app, "/applications/@me", "/applications/@me")
        if r is None or r.status != 200 or not isinstance(r.body, dict):
            st, msg = (st, msg) if r is None else classify_error(r.status, r.body)
            yield self._unit(app, st, f"{app}#application", msg)
            self.stopped = self.stopped or msg
            return True
        flags = _bits(r.body.get("flags"))
        self.content_available = bool(flags & (APP_MESSAGE_CONTENT | APP_MESSAGE_CONTENT_LIMITED))
        self.intent_status = "message_content_enabled" if self.content_available else "message_content_intent_missing"
        save_cursor(con, app, "application", self.clock(), last_status=self.intent_status,
                    **({"last_success_at": self.clock()} if self.content_available else {}))
        if not self.content_available and self.cfg.require_message_content:
            msg = ("message_content_intent_missing: the application has neither GATEWAY_MESSAGE_CONTENT nor "
                   "GATEWAY_MESSAGE_CONTENT_LIMITED; enable Message Content Intent on the Bot page (or get it approved "
                   "for 100+ servers); no channel was read")
            yield self._unit(app, "BLOCKED", f"{app}#intent", msg)
            for g, c in todo:
                yield self._unit(c.connector, "BLOCKED", f"{c.connector}#intent", msg)
            return True
        r, st, msg = self._call(con, guard, app, "/users/@me", "/users/@me")
        if r is None or r.status != 200 or not isinstance(r.body, dict) or not SNOWFLAKE.match(str(r.body.get("id") or "")):
            st, msg = (st, msg) if r is None else classify_error(r.status if r.status != 200 else 401, r.body)
            yield self._unit(app, st, f"{app}#user", msg)
            self.stopped = self.stopped or msg
            return True
        if r.body.get("bot") is not True:
            msg = "not_a_bot: the token belongs to a user account; self-bots are forbidden by Discord; nothing was read"
            self.stopped = msg
            yield self._unit(app, "BLOCKED", f"{app}#user", msg)
            return True
        self.bot_id = str(r.body["id"])
        yield self._unit(app, "OK", f"{app}#preflight@{int(r.received_at)}",
                         body={"schema": INBOUND_SCHEMA_V3, "source": self._source(None), "fetched_at": iso(r.received_at), "items": []})
        return False

    def _guild(self, con, guard, g: Guild, cache) -> tuple[dict | None, list[str] | None, str | None, str | None]:
        if g.guild_id in cache:
            return (*cache[g.guild_id], None, None)
        conn = f"discord_bot:guild:{g.guild_id}"
        r, st, msg = self._call(con, guard, conn, "/guilds/{guild}", f"/guilds/{g.guild_id}")
        if r is None or r.status != 200 or not isinstance(r.body, dict):
            st, msg = (st, msg) if r is None else classify_error(r.status, r.body)
            cache[g.guild_id] = (None, None)
            return None, None, st, msg
        gobj = r.body
        r, st, msg = self._call(con, guard, conn, "/guilds/{guild}/members/{user}", f"/guilds/{g.guild_id}/members/{self.bot_id}")
        if r is None or r.status != 200 or not isinstance(r.body, dict):
            st, msg = (st, msg) if r is None else classify_error(r.status, r.body)
            cache[g.guild_id] = (None, None)
            return None, None, st, msg
        roles = [str(x) for x in r.body.get("roles") or []]
        cache[g.guild_id] = (gobj, roles)
        return gobj, roles, None, None

    def _channel(self, con, guard, g: Guild, c: Channel, cache) -> Iterator[SourceUnit]:
        cur = get_cursor(con, c.connector, "messages")
        if cur and cur["rate_limit_reset_at"] and cur["rate_limit_reset_at"] > self.clock():
            yield self._unit(c.connector, "RATE_LIMITED", f"{c.connector}#waiting",
                             f"rate limited until {iso(cur['rate_limit_reset_at'])}; not called")
            return
        gobj, roles, st, msg = self._guild(con, guard, g, cache)
        if gobj is None:
            yield self._stop_channel(con, c, st or "BLOCKED", msg or "server not readable", f"{c.connector}#guild")
            return
        r, st, msg = self._call(con, guard, c.connector, "/channels/{channel}", f"/channels/{c.channel_id}")
        if r is None or r.status != 200 or not isinstance(r.body, dict):
            st, msg = (st, msg) if r is None else classify_error(r.status, r.body)
            yield self._stop_channel(con, c, st, msg, f"{c.connector}#channel", r)
            return
        acc = channel_access(c, r.body, gobj, self.bot_id, roles)
        if not acc.readable:
            yield self._stop_channel(con, c, "BLOCKED", acc.reason, f"{c.connector}#access")
            return
        yield from self._messages(con, guard, c, cur["newest_id"] if cur else None)

    def _messages(self, con, guard, c: Channel, since: str | None) -> Iterator[SourceUnit]:
        path = f"/channels/{c.channel_id}/messages"
        newest, yielded, page = since, [], 0
        before = None
        cap = self.cfg.max_pages_per_channel if since else self.cfg.backfill_max_pages
        note = None if self.content_available else ("message_content_intent_missing: ids, times and references only; "
                                                    "no text, attachments or embeds")
        while True:
            page += 1
            p: dict = {"limit": self.cfg.page_size}
            if since:
                p["after"] = newest
            elif before:
                p["before"] = before
            ref = f"{c.connector}#{'after=' + newest if since else 'backfill'}&page={page}" + (f"&before={before}" if before else "")
            r, st, msg = self._call(con, guard, c.connector, "/channels/{channel}/messages", path, p)
            if r is None:
                yield self._stop_channel(con, c, st, msg, ref)
                return
            if r.status != 200 or not isinstance(r.body, list):
                st, msg = classify_error(r.status, r.body)
                yield self._stop_channel(con, c, st, msg, ref, r)
                return
            msgs = sorted((m for m in r.body if isinstance(m, dict) and SNOWFLAKE.match(str(m.get("id") or ""))),
                          key=lambda m: int(m["id"]))
            items = []
            for m in msgs:
                it, why = message_item(m, c, r.received_at, self.sink, content_available=self.content_available)
                if it is None:
                    self._drop(why)
                    continue
                items.append(it)
            env = {"schema": INBOUND_SCHEMA_V3, "source": self._source(c, self.cfg.guild(c.guild_id)), "fetched_at": iso(r.received_at),
                   "items": items}
            u = self._unit(c.connector, "OK", ref, body=env)
            yielded.append(u)
            yield u
            if note and items:
                yield self._unit(c.connector, "DEGRADED", f"{ref}&intent", note)
            if msgs:
                top = msgs[-1]["id"]
                if newest is None or int(top) > int(newest):
                    newest = top
            if len(r.body) < self.cfg.page_size:
                break
            if page >= cap:
                yield self._unit(c.connector, "DEGRADED", f"{c.connector}#gap@{newest}",
                                 f"page cap {cap} reached; " + ("newer messages are read from the cursor on the next run"
                                                                 if since else "older history before this window was not read"))
                break
            if not since:
                before = msgs[0]["id"] if msgs else None
                if before is None:
                    break
        if units_committed(con, yielded):
            save_cursor(con, c.connector, "messages", self.clock(), provider_scope_id=c.guild_id, newest_id=newest,
                        last_status="OK", last_success_at=self.clock(), rate_limit_reset_at=None)
        else:
            save_cursor(con, c.connector, "messages", self.clock(), provider_scope_id=c.guild_id, last_status="PARTIAL")

    def _recheck(self, con, guard) -> Iterator[SourceUnit]:
        conn = "discord_bot:recheck:stored"
        rows = con.execute(
            "SELECT i.provider_item_id FROM social_items i WHERE i.platform='discord' AND i.provider_item_id IS NOT NULL"
            " AND i.first_ingested_at < ? AND NOT EXISTS (SELECT 1 FROM social_observations o WHERE o.item_key=i.item_key"
            " AND o.retrieval_status IN ('NOT_FOUND','DELETED')) ORDER BY COALESCE(i.first_observed_at, i.first_ingested_at) DESC,"
            " i.provider_item_id LIMIT ?", (self.started_at, self.cfg.recheck_max_items)).fetchall()
        blocked: set[str] = set()
        for (prov,) in rows:
            cid, _, mid = prov.partition("_")
            ch = self.cfg.by_channel.get(cid)
            if ch is None or cid in blocked or not SNOWFLAKE.match(mid):
                continue
            cur = get_cursor(con, ch.connector, "messages")
            if cur and cur["last_status"] not in ("OK", "PARTIAL"):
                continue                    # the channel is not readable right now: never read absence as deletion
            ref = f"{conn}#{prov}"
            r, st, msg = self._call(con, guard, conn, "/channels/{channel}/messages/{message}", f"/channels/{cid}/messages/{mid}")
            if r is None:
                yield self._unit(conn, st, ref, msg)
                return
            src = self._source(ch, self.cfg.guild(ch.guild_id))
            if r.status == 200 and isinstance(r.body, dict):
                it, why = message_item(r.body, ch, r.received_at, self.sink, content_available=self.content_available)
                items = [it] if it else []
            elif r.status == 404 and isinstance(r.body, dict) and r.body.get("code") == 10008:
                items = [deleted_item(ch, mid, r.received_at)]
            else:
                st, msg = classify_error(r.status, r.body)
                blocked.add(cid)
                if st == "BLOCKED":
                    yield self._stop_channel(con, ch, st, msg, ref, r)
                else:
                    yield self._unit(conn, st, ref, msg)
                continue
            yield self._unit(conn, "OK", ref, body={"schema": INBOUND_SCHEMA_V3, "source": src, "fetched_at": iso(r.received_at),
                                                    "items": items})


# ---------- gateway ----------

class GatewayClosed(Exception):
    def __init__(self, code: int, reason: str, fatal: bool):
        super().__init__(f"{code} {reason}")
        self.code, self.reason, self.fatal = code, reason, fatal


class GatewaySession:
    """The gateway protocol as a pure state machine over frames (dicts). It holds session_id, resume_gateway_url and
    the token in memory only. on_frame() returns the frames to send; dispatches are collected in self.events with
    the connection index and sequence number so a resume, a duplicate delivery or an out-of-order batch can be
    reconciled by the adapter."""

    def __init__(self, token: str, *, intents: int):
        if intents & INTENT_DIRECT_MESSAGES:
            raise ValueError("direct-message intents are never requested")
        self._token, self.intents = token, intents
        self.seq: int | None = None
        self._session: str | None = None
        self.resume_url: str | None = None
        self.connection = 0
        self.events: list[dict] = []
        self.seen: set[tuple[str | None, int]] = set()
        self.duplicates = 0
        self.heartbeat_ms: int | None = None
        self.resumed = 0

    def __repr__(self) -> str:
        return f"GatewaySession(connection={self.connection}, seq={self.seq}, session={'set' if self._session else 'none'})"

    def connect(self) -> None:
        self.connection += 1

    def on_frame(self, f: dict) -> list[dict]:
        op = f.get("op")
        if op == 10:
            self.heartbeat_ms = (f.get("d") or {}).get("heartbeat_interval")
            if self._session and self.seq is not None:
                return [{"op": 6, "d": {"token": self._token, "session_id": self._session, "seq": self.seq}}]
            return [{"op": 2, "d": {"token": self._token, "intents": self.intents,
                                    "properties": {"os": "linux", "browser": "memelab", "device": "memelab"}}}]
        if op == 1:
            return [{"op": 1, "d": self.seq}]
        if op == 7:
            raise GatewayClosed(4900, "reconnect requested", fatal=False)
        if op == 9:
            if not f.get("d"):
                self._session, self.seq = None, None
            raise GatewayClosed(4901, "invalid session" + (" (resumable)" if f.get("d") else ""), fatal=False)
        if op == 0:
            s = f.get("s")
            t = f.get("t")
            d = f.get("d") if isinstance(f.get("d"), dict) else {}
            if _int(s):
                key = (self._session, s)
                if key in self.seen:
                    self.duplicates += 1
                    return []
                self.seen.add(key)
                self.seq = max(self.seq or 0, s)
            if t == "READY":
                self._session = d.get("session_id") if isinstance(d.get("session_id"), str) else None
                self.resume_url = d.get("resume_gateway_url") if isinstance(d.get("resume_gateway_url"), str) else None
                self.seen = {(self._session, x) for (_, x) in self.seen}
            elif t == "RESUMED":
                self.resumed += 1
            self.events.append({"connection": self.connection, "seq": s if _int(s) else -1, "t": t, "d": d})
        return []

    @staticmethod
    def close_action(code: int) -> tuple[str, bool]:
        if code in FATAL_CLOSE:
            return FATAL_CLOSE[code], True
        return f"close {code}", False


class GatewayFixtureTransport:
    """Recorded gateway connections: each is {"frames": [...], "close": code}. Records what the client sent."""

    def __init__(self, fixture: dict | str | Path):
        if not isinstance(fixture, dict):
            fixture = json.loads(Path(fixture).read_text())
        if fixture.get("schema") != GATEWAY_FIXTURE_SCHEMA:
            raise ValueError(f"fixture schema must be {GATEWAY_FIXTURE_SCHEMA}")
        self.connections = fixture["connections"]
        self.recorded_at = store.to_utc(fixture["recorded_at"])
        self.sent: list[dict] = []

    def sessions(self) -> Iterator[tuple[list[dict], int | None]]:
        for c in self.connections:
            yield c.get("frames") or [], c.get("close")

    def send(self, frame: dict) -> None:
        self.sent.append(frame)


class GuildState:
    """What the gateway told us about one server: roles, the bot's roles, channel overwrites, removal."""

    def __init__(self):
        self.owner_id: str | None = None
        self.roles: dict[str, dict] = {}
        self.bot_roles: list[str] = []
        self.channels: dict[str, dict] = {}
        self.removed = False
        self.unavailable = False


class DiscordGatewayAdapter:
    """SourceAdapter over one gateway pass (fixture frames, or a websocket transport with the same interface).
    Message events of configured, readable, public channels become inbound /3 items, sorted per channel by
    (connection, sequence); deletions become DELETED sightings; a removal or a permission change blocks the channel
    for the rest of the pass. A close code that forbids reconnecting ends the pass with its reason."""

    name = "discord_gateway"

    def __init__(self, cfg: DiscordConfig, transport, token: str | None, db_path: Path | str, *, run_id: str | None = None,
                 mode: str = "live", clock: Callable[[], float] = time.time, text_sink: TextSink | None = None):
        if mode not in ("live", "fixture"):
            raise ValueError("mode must be live or fixture")
        self.cfg, self.transport, self._token = cfg, transport, token
        self.db_path, self.run_id, self.mode, self.clock = Path(db_path), run_id, mode, clock
        self.sink = text_sink
        self.requests = 0
        self.session: GatewaySession | None = None
        self.close_reason: str | None = None
        self.dropped: dict[str, int] = {}
        self.bot_id: str | None = None

    def __repr__(self) -> str:
        return f"DiscordGatewayAdapter(mode={self.mode!r}, token={'set' if self._token else 'missing'})"

    def _scrub(self, s: str) -> str:
        return scrub(s, self._token)

    def _drop(self, why: str) -> None:
        self.dropped[why] = self.dropped.get(why, 0) + 1

    def _unit(self, connector: str, status: str, ref: str, error: str | None = None, body: Any = None) -> SourceUnit:
        error = self._scrub(error)[:300] if error else None
        return SourceUnit(connector=connector, platform=PLATFORM, source_ref=ref, status=status,
                          unit_sha=canonical_sha(body if body is not None else [status, ref, error]), body=body, error=error,
                          plan_id=self.run_id)

    def _source(self, ch: Channel) -> dict:
        live = self.mode == "live"
        g = self.cfg.guild(ch.guild_id)
        return {"platform": PLATFORM, "source_id": f"bot:{self.cfg.bot_label}:channel:{ch.channel_id}",
                "access_mode": "fetch" if live else "fixture",
                "collector": "discord-bot-gateway" if live else "discord-bot-gateway/fixture",
                "rights_basis": f"discord_bot_{g.consent_basis}" if live and g else "synthetic_fixture",
                "visibility": "PUBLIC", "terms_note": TERMS_NOTE[:400]}

    def _run_session(self) -> None:
        intents = INTENT_GUILDS | INTENT_GUILD_MESSAGES | (INTENT_MESSAGE_CONTENT if self.cfg.require_message_content else 0)
        self.session = s = GatewaySession(self._token, intents=intents)
        for frames, close in self.transport.sessions():
            s.connect()
            closed = None
            for f in frames:
                try:
                    for out in s.on_frame(f):
                        self.transport.send(out)
                except GatewayClosed as e:
                    closed = e
                    break
                if len(s.events) >= self.cfg.gateway_max_events:
                    self.close_reason = f"event cap {self.cfg.gateway_max_events} per pass reached"
                    return
            if closed is None and close is not None:
                reason, fatal = GatewaySession.close_action(int(close))
                if fatal:
                    self.close_reason = reason
                    log_event("discord_gateway_closed", code=close, reason=reason, fatal=True)
                    return
                log_event("discord_gateway_closed", code=close, reason=reason, fatal=False)

    def units(self, budget: Budget) -> Iterator[SourceUnit]:
        gw = f"discord_bot:gateway:{self.cfg.bot_label}"
        if not self._token:
            yield self._unit(gw, "BLOCKED", f"{gw}#credentials", f"credentials_missing: set {TOKEN_ENV}")
            return
        con = connect(self.db_path)
        try:
            self._run_session()
            s = self.session
            fetched = getattr(self.transport, "recorded_at", None) or self.clock()
            if self.close_reason in FATAL_CLOSE.values():
                msg = {"privileged_intent_missing": "privileged_intent_missing: gateway closed 4014 (disallowed intents); enable "
                                                    "Message Content Intent on the Bot page or run with require_message_content false",
                       "credentials_rejected": "credentials_rejected: gateway closed 4004 (authentication failed)"}.get(
                    self.close_reason, f"{self.close_reason}: gateway closed and may not reconnect")
                save_cursor(con, gw, "gateway", self.clock(), last_status=self.close_reason)
                if self.close_reason == "privileged_intent_missing":
                    save_cursor(con, f"discord_bot:app:{self.cfg.bot_label}", "application", self.clock(),
                                last_status="message_content_intent_missing")
                yield self._unit(gw, "BLOCKED", f"{gw}#close@{int(fetched)}", msg)
                if not s.events:
                    return
            yield from self._convert(con, s, fetched, gw)
        finally:
            con.close()

    def _convert(self, con, s: GatewaySession, fetched: float, gw: str) -> Iterator[SourceUnit]:
        guilds: dict[str, GuildState] = {}
        blocked: dict[str, str] = {}
        per_channel: dict[str, list[dict]] = {}
        content_ok = self.cfg.require_message_content
        events = sorted(s.events, key=lambda e: (e["connection"], e["seq"]))

        def check(cid: str) -> str | None:
            ch = self.cfg.by_channel[cid]
            gs = guilds.get(ch.guild_id)
            g = self.cfg.guild(ch.guild_id)
            if g is None or not g.consented or g.server_visibility not in SERVER_VISIBILITY:
                return "consent_missing: server not consented in the config"
            if gs is None or self.bot_id is None:
                return "server_state_unknown: no READY and GUILD_CREATE seen for this server in this pass; not read"
            if gs.removed:
                return "access_denied: the bot was removed from this server (GUILD_DELETE)"
            cobj = gs.channels.get(cid)
            if cobj is None:
                return "channel_state_unknown: the channel was not in GUILD_CREATE; not read"
            acc = channel_access(ch, cobj, {"owner_id": gs.owner_id, "roles": list(gs.roles.values())}, self.bot_id, gs.bot_roles)
            return None if acc.readable else acc.reason

        for e in events:
            t, d = e["t"], e["d"]
            if t == "READY":
                u = d.get("user") if isinstance(d.get("user"), dict) else {}
                self.bot_id = str(u.get("id")) if SNOWFLAKE.match(str(u.get("id") or "")) else None
                continue
            if t == "GUILD_CREATE":
                gid = str(d.get("id") or "")
                if self.cfg.guild(gid) is None:
                    self._drop("unconfigured_server")
                    continue
                gs = guilds.setdefault(gid, GuildState())
                gs.owner_id = str(d.get("owner_id") or "") or None
                gs.roles = {str(r.get("id")): r for r in d.get("roles") or [] if isinstance(r, dict)}
                for m in d.get("members") or []:
                    if isinstance(m, dict) and str((m.get("user") or {}).get("id")) == self.bot_id:
                        gs.bot_roles = [str(x) for x in m.get("roles") or []]
                gs.channels = {str(c.get("id")): {**c, "guild_id": gid} for c in d.get("channels") or [] if isinstance(c, dict)}
                gs.removed = False
                for cid in [c for c, why in blocked.items() if self.cfg.by_channel[c].guild_id == gid]:
                    if check(cid) is None:
                        blocked.pop(cid)
                continue
            if t == "GUILD_DELETE":
                gid = str(d.get("id") or "")
                g = self.cfg.guild(gid)
                if g is None:
                    continue
                gs = guilds.setdefault(gid, GuildState())
                if d.get("unavailable") is True:
                    gs.unavailable = True          # outage: events stop, nothing is blocked
                    continue
                gs.removed = True
                for ch in g.channels:
                    blocked[ch.channel_id] = "access_denied: the bot was removed from this server (GUILD_DELETE)"
                continue
            if t in ("CHANNEL_UPDATE", "CHANNEL_CREATE"):
                cid, gid = str(d.get("id") or ""), str(d.get("guild_id") or "")
                if cid in self.cfg.by_channel and gid in guilds:
                    guilds[gid].channels[cid] = d
                    why = check(cid)
                    if why:
                        blocked[cid] = why
                    else:
                        blocked.pop(cid, None)
                continue
            if t in ("GUILD_ROLE_UPDATE", "GUILD_ROLE_CREATE"):
                gid = str(d.get("guild_id") or "")
                r = d.get("role") if isinstance(d.get("role"), dict) else None
                if gid in guilds and r:
                    guilds[gid].roles[str(r.get("id"))] = r
                    for ch in self.cfg.guild(gid).channels:
                        why = check(ch.channel_id)
                        if why:
                            blocked[ch.channel_id] = why
                        else:
                            blocked.pop(ch.channel_id, None)
                continue
            if t in ("MESSAGE_CREATE", "MESSAGE_UPDATE", "MESSAGE_DELETE", "MESSAGE_DELETE_BULK"):
                cid = str(d.get("channel_id") or "")
                if "guild_id" not in d:
                    self._drop("direct_message")       # never read, never stored
                    continue
                if cid not in self.cfg.by_channel:
                    self._drop("unconfigured_channel")
                    continue
                why = blocked.get(cid) or check(cid)
                if why:
                    blocked[cid] = why
                    self._drop("channel_blocked")
                    continue
                ch = self.cfg.by_channel[cid]
                if t == "MESSAGE_DELETE":
                    if SNOWFLAKE.match(str(d.get("id") or "")):
                        per_channel.setdefault(cid, []).append(deleted_item(ch, str(d["id"]), fetched))
                    continue
                if t == "MESSAGE_DELETE_BULK":
                    for mid in d.get("ids") or []:
                        if SNOWFLAKE.match(str(mid)):
                            per_channel.setdefault(cid, []).append(deleted_item(ch, str(mid), fetched))
                    continue
                if t == "MESSAGE_UPDATE" and not d.get("edited_timestamp") and "content" not in d:
                    self._drop("partial_update")       # embed unfurl or flags only: not a new version
                    continue
                it, why = message_item(d, ch, fetched, self.sink, content_available=content_ok)
                if it is None:
                    self._drop(why)
                    continue
                per_channel.setdefault(cid, []).append(it)
                continue
            self._drop("event_not_used")
        for cid, why in sorted(blocked.items()):
            ch = self.cfg.by_channel[cid]
            save_cursor(con, ch.connector, "messages", self.clock(), provider_scope_id=ch.guild_id, last_status=why.split(":", 1)[0])
            yield self._unit(ch.connector, "BLOCKED", f"{ch.connector}#gateway-blocked@{int(fetched)}", why)
        for cid, items in sorted(per_channel.items()):
            ch = self.cfg.by_channel[cid]
            env = {"schema": INBOUND_SCHEMA_V3, "source": self._source(ch), "fetched_at": iso(fetched), "items": items}
            yield self._unit(ch.connector, "OK", f"{ch.connector}#gateway@{int(fetched)}&n={len(items)}", body=env)
        save_cursor(con, gw, "gateway", self.clock(), last_status=self.close_reason or "OK",
                    **({} if self.close_reason in FATAL_CLOSE.values() else {"last_success_at": self.clock()}))
        if not per_channel and not blocked:
            src = {"platform": PLATFORM, "source_id": f"bot:{self.cfg.bot_label}:gateway",
                   "access_mode": "fetch" if self.mode == "live" else "fixture",
                   "collector": "discord-bot-gateway" if self.mode == "live" else "discord-bot-gateway/fixture",
                   "rights_basis": "discord_bot_gateway" if self.mode == "live" else "synthetic_fixture", "visibility": "PUBLIC",
                   "terms_note": TERMS_NOTE[:400]}
            yield self._unit(gw, "OK", f"{gw}#empty@{int(fetched)}",
                             body={"schema": INBOUND_SCHEMA_V3, "source": src, "fetched_at": iso(fetched), "items": []})
        if self.dropped:
            log_event("discord_gateway_dropped", counts=dict(self.dropped), duplicates=s.duplicates)


# ---------- deletion compliance and user requests ----------

def purge_deleted(db_path: Path | str, *, now: float, users: list[str] | tuple = (), private_path=None) -> dict:
    """Erase what the lab derived from deleted Discord messages (Developer Terms 5(b): data no longer necessary), and
    erase the users named (a user's request to delete their data). Ids and the DELETED sighting stay. Idempotent."""
    con = connect(db_path)
    try:
        out = purge_gone_items(con, PLATFORM, private_path=private_path)
        targets = {}
        for uid in set(users):
            row = con.execute("SELECT account_id FROM social_accounts WHERE platform='discord' AND provider_user_id=?", (uid,)).fetchone()
            if row is not None:
                targets[row[0]] = uid
        out["accounts_erased"] = erase_accounts(con, targets)
        con.commit()
    finally:
        con.close()
    log_event("discord_purge", **out)
    return out


def reset_checkpoint(db_path: Path | str, channel_id: str, now: float) -> dict:
    """Forget the message cursor and any rate-limit wait of one channel; the next run reads the newest page again
    and event-id dedupe absorbs what was already stored."""
    con = connect(db_path)
    try:
        conn = f"discord_bot:channel:{channel_id}"
        before = get_cursor(con, conn, "messages")
        con.execute("DELETE FROM social_source_cursors WHERE connector=? AND scope='messages'", (conn,))
        con.commit()
    finally:
        con.close()
    return {"connector": conn, "had_cursor": before is not None, "previous_newest_id": before["newest_id"] if before else None}


# ---------- health ----------

def health(config_path: Path | str | None, db_path: Path | str, env: dict | None = None, now: float | None = None) -> dict:
    """No network call. Status: not_configured | consent_missing | credentials_missing | intent_missing | ready."""
    t = time.time() if now is None else now
    tok = get_token(env)
    out: dict = {"adapter": "discord_bot", "contract_verified": CONTRACT_VERIFIED, "credential_env": [TOKEN_ENV],
                 "credentials": "present" if tok else "missing", "network_calls_made": 0,
                 "cost": "free: Discord's bot API has no per-request charge; 50 requests per second per bot; estimated $0 per request"}
    cfg = None
    if config_path and Path(config_path).exists():
        try:
            cfg = load_config(config_path)
        except Exception as e:
            out["config_error"] = redact(str(e))[:200]
    out["config"] = None if cfg is None else {
        "bot_label": cfg.bot_label, "require_message_content": cfg.require_message_content,
        "servers": [{"guild_id": g.guild_id, "label": g.label, "consent": g.consent_basis if g.consented else "missing",
                     "server_visibility": g.server_visibility, "channels": [c.channel_id for c in g.channels]} for g in cfg.guilds],
        "max_requests_per_run": cfg.max_requests_per_run}
    con = connect(db_path)
    try:
        live = con.execute("SELECT COUNT(*), MAX(requested_at), SUM(http_status=200) FROM social_api_spend "
                           "WHERE mode='live' AND connector LIKE 'discord_bot:%'").fetchone()
        out["live_evidence"] = {"requests": live[0], "successful": live[2] or 0, "last_request_at": live[1],
                                "verdict": "live authorized ingest proved" if live[2] else "none: no live Discord read has been made"}
        intent = con.execute("SELECT last_status, updated_at FROM social_source_cursors WHERE connector LIKE 'discord_bot:app:%' "
                             "AND scope='application' ORDER BY updated_at DESC LIMIT 1").fetchone()
        out["message_content_intent"] = intent[0] if intent else "unknown: no run has checked the application flags"
        gwc = con.execute("SELECT last_status FROM social_source_cursors WHERE connector LIKE 'discord_bot:gateway:%' "
                          "ORDER BY updated_at DESC LIMIT 1").fetchone()
        out["gateway_last_status"] = gwc[0] if gwc else None
        out["cursors"] = [{k: r[k] for k in ("connector", "scope", "newest_id", "last_status", "last_success_at", "rate_limit_reset_at")}
                          for r in con.execute("SELECT * FROM social_source_cursors WHERE connector LIKE 'discord_bot:channel:%' ORDER BY connector")]
        for c in out["cursors"]:
            c["age_hours"] = round((t - c["last_success_at"]) / 3600, 1) if c["last_success_at"] else None
        out["blocked_channels"] = [c["connector"] for c in out["cursors"] if c["last_status"] not in ("OK", "PARTIAL", "RATE_LIMITED")]
        out["connector_health"] = [dict(r) for r in con.execute(
            "SELECT h.connector, h.status, h.checked_at, h.error FROM social_connector_health h WHERE h.connector LIKE 'discord_bot:%'"
            " AND h.checked_at=(SELECT MAX(checked_at) FROM social_connector_health WHERE connector=h.connector) ORDER BY h.connector")]
        out["deletion_purge_pending_items"] = con.execute(
            "SELECT COUNT(DISTINCT o.item_key) FROM social_observations o JOIN social_items i ON i.item_key=o.item_key "
            "WHERE i.platform='discord' AND o.retrieval_status IN ('DELETED','NOT_FOUND') AND EXISTS (SELECT 1 FROM "
            "social_observations o2 WHERE o2.item_key=o.item_key AND o2.content_hash IS NOT NULL)").fetchone()[0]
    finally:
        con.close()
    if cfg is None or not cfg.by_channel:
        out["status"] = "not_configured"
    elif not any(g.consented and g.server_visibility in SERVER_VISIBILITY and g.channels for g in cfg.guilds):
        out["status"] = "consent_missing"
    elif not tok:
        out["status"] = "credentials_missing"
    elif out["message_content_intent"] == "message_content_intent_missing" and cfg.require_message_content:
        out["status"] = "intent_missing"
    else:
        out["status"] = "ready"
    out["next_step"] = {
        "not_configured": "write the server and channel config (docs/social-intelligence/discord_bot.example.json) to data/private/discord_bot.json",
        "consent_missing": "a server admin installs your bot and agrees in writing; record consent.basis, consent.reference "
                           "and server_visibility for that server (an invite link is not consent)",
        "credentials_missing": f"create a bot in the Discord Developer Portal and export {TOKEN_ENV} in the shell that runs memelab",
        "intent_missing": "enable Message Content Intent on the Bot page of the Developer Portal (under 100 servers), then run again",
        "ready": "run one small live ingest (one channel, backfill_max_pages 1) and check `social discord-health` live_evidence",
    }[out["status"]]
    return out
