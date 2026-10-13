"""Farcaster adapter on the Snapchain node HTTP API (Phase 19, optional source).

Contract read 2026-10-12 (docs/social-intelligence/SOURCES_19.md has the sources and the gaps):

  GET {base}/v1/castsByFid        fid, pageSize, pageToken, reverse     casts by one account (fid)
  GET {base}/v1/castsByParent     url (channel parent URL) or fid+hash  casts in a channel, or replies to a cast
  GET {base}/v1/castById          fid, hash                             one cast (used by recheck)
  GET {base}/v1/reactionsByCast   target_fid, target_hash, reaction_type=Recast, pageSize, pageToken
  GET {base}/v1/userDataByFid     fid, user_data_type=6 (USER_DATA_TYPE_USERNAME only; bio, pfp and display name
                                  are never requested)
  List responses: {"messages": [...], "nextPageToken": "<empty when done>"}. A message has data.type, data.fid,
  data.timestamp (seconds since the Farcaster epoch 2021-01-01T00:00:00Z), data.castAddBody {text, embeds, mentions,
  parentCastId {fid, hash}, parentUrl} or data.reactionBody {type, targetCastId}, and hash (0x + 40 hex, blake3).
  A node serves HTTP on port 3381 by default; no authentication is documented for a self-hosted node. Neynar's
  hosted hub endpoint (the company that now operates Farcaster) needs an API key and is metered in compute units.

Farcaster data is public protocol data; there are no private casts. Casts cannot be edited: a change is a remove
plus a new cast. A removed cast disappears from the node, so recheck reports it as NOT_FOUND.

What this adapter stores (D-010, D-013, D-016): cast and reaction hashes, fids, the username (preferred name)
of authors, provider times, a hash of the cast text plus its embedded URLs, parent and quoted cast ids. The text
is hashed in memory and dropped (it reaches claim extraction only through the in-memory TextSink when asked).

Safety: not configured -> no request; a metered endpoint needs its API key in the environment and an explicit
billing consent with a non-zero cap; request cap per run; 429 stops the run until retry-after; plain http is
accepted only for a loopback node; secrets never logged.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

from . import store
from .api_common import (FixtureMiss, FixtureTransport as _FT, HttpResponse, RequestGuard, TextSink, connect, get_cursor, iso,
                         save_cursor, scrub, units_committed)
from .ingest import INBOUND_SCHEMA_V3, Budget, SourceUnit, TransientError, canonical_sha, log_event, redact, with_retries

PLATFORM = "farcaster"
CONFIG_SCHEMA = "memelab.farcaster_hub.config/1"
FIXTURE_SCHEMA = "memelab.farcaster_hub.fixture/1"
CONTRACT_VERIFIED = "2026-10-12"
FC_EPOCH = 1609459200          # 2021-01-01T00:00:00Z
DEFAULT_KEY_ENV = "FARCASTER_HUB_API_KEY"
ENDPOINTS = {"fid": "/v1/castsByFid", "channel": "/v1/castsByParent", "cast": "/v1/castById",
             "recasts": "/v1/reactionsByCast", "username": "/v1/userDataByFid"}
HASH_RE = re.compile(r"^0x[0-9a-f]{40}$")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9.\-]{0,31}$")
CHANNEL_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,31}$")
FORBIDDEN_CONFIG_KEYS = {"api_key", "key", "secret", "token", "password", "signer"}
LOOPBACK = ("127.0.0.1", "localhost", "::1")
VISIBILITY = {
    "fid": "Snapchain castsByFid: casts by one configured account; replies and recasts by others are not read here",
    "channel": "Snapchain castsByParent with a channel URL: top-level casts in one configured channel; replies under "
               "those casts are not read",
    "recasts": "Snapchain reactionsByCast (Recast) for casts ingested in this run, capped per run; likes are not read",
    "recheck": "Snapchain castById for stored casts: a removed cast is NOT_FOUND (remove and never-existed look the same)",
}


def fc_time(ts: Any) -> float | None:
    return FC_EPOCH + float(ts) if isinstance(ts, (int, float)) and not isinstance(ts, bool) and ts >= 0 else None


# ---------- config ----------

@dataclass
class Scope:
    kind: str                 # fid | channel
    key: str
    fid: int | None = None
    parent_url: str | None = None

    @property
    def connector(self) -> str:
        return f"farcaster_hub:{self.kind}:{self.key}"


@dataclass
class FarcasterConfig:
    base_url: str | None
    scopes: list[Scope]
    billing: str = "self_hosted"           # self_hosted | metered
    api_key_env: str = DEFAULT_KEY_ENV
    api_key_header: str = "x-api-key"
    usd_per_request: float = 0.0
    allow_billable: bool = False
    max_usd_per_run: float = 0.0
    recasts: bool = True
    max_recast_lookups: int = 20
    recheck: bool = True
    recheck_max_items: int = 50
    page_size: int = 100
    max_pages_per_scope: int = 3
    max_requests_per_run: int = 60
    timeout_seconds: float = 20.0


def _check_base(url: str) -> str:
    p = urllib.parse.urlparse(url)
    if p.scheme == "https" and p.hostname:
        pass
    elif p.scheme == "http" and p.hostname in LOOPBACK:
        pass
    else:
        raise ValueError("hub.base_url: https, or http only for a node on this machine (127.0.0.1, localhost)")
    if p.username or p.password or p.query or p.fragment:
        raise ValueError("hub.base_url: no credentials, query or fragment in the URL")
    return url.rstrip("/")


def load_config(obj: dict | str | Path) -> FarcasterConfig:
    if not isinstance(obj, dict):
        obj = json.loads(Path(obj).read_text())
    if obj.get("schema") != CONFIG_SCHEMA:
        raise ValueError(f"config schema must be {CONFIG_SCHEMA}")

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if str(k).lower() in FORBIDDEN_CONFIG_KEYS:
                    raise ValueError(f"config must not hold credentials (key '{k}'); name an environment variable in hub.api_key_env")
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    hub = obj.get("hub") or {}
    base = _check_base(hub["base_url"]) if hub.get("base_url") else None
    billing = hub.get("billing", "self_hosted")
    if billing not in ("self_hosted", "metered"):
        raise ValueError("hub.billing: self_hosted or metered")
    env = hub.get("api_key_env", DEFAULT_KEY_ENV)
    if not isinstance(env, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", env):
        raise ValueError("hub.api_key_env: an environment variable name")
    header = hub.get("api_key_header", "x-api-key")
    if header.lower() in ("cookie", "host") or not re.fullmatch(r"[A-Za-z0-9\-]{1,40}", header):
        raise ValueError("hub.api_key_header: a header name")
    scopes, seen = [], set()
    for i, s in enumerate(obj.get("scopes") or []):
        kind = s.get("kind")
        if kind == "fid":
            fid = s.get("fid")
            if not isinstance(fid, int) or isinstance(fid, bool) or not (0 < fid < 2 ** 63):
                raise ValueError(f"scopes[{i}].fid: a positive integer")
            sc = Scope("fid", key=str(fid), fid=fid)
        elif kind == "channel":
            name, purl = s.get("name"), s.get("parent_url")
            if not isinstance(name, str) or not CHANNEL_RE.match(name):
                raise ValueError(f"scopes[{i}].name: channel id, lower-case letters, digits and '-'")
            if not isinstance(purl, str) or not (purl.startswith("https://") or purl.startswith("chain://")) or len(purl) > 300:
                raise ValueError(f"scopes[{i}].parent_url: the channel's parent URL (https:// or chain://)")
            sc = Scope("channel", key=name, parent_url=purl)
        else:
            raise ValueError(f"scopes[{i}].kind: fid or channel")
        if sc.connector in seen:
            raise ValueError(f"scopes[{i}]: duplicate scope")
        seen.add(sc.connector)
        scopes.append(sc)
    b = obj.get("budget") or {}
    rc, rv = obj.get("recasts") or {}, obj.get("recheck") or {}
    return FarcasterConfig(base_url=base, scopes=scopes, billing=billing, api_key_env=env, api_key_header=header,
                           usd_per_request=max(0.0, float(hub.get("usd_per_request", 0))),
                           allow_billable=b.get("allow_billable") is True, max_usd_per_run=max(0.0, float(b.get("max_usd_per_run", 0))),
                           recasts=rc.get("enabled", True) is True, max_recast_lookups=max(0, int(rc.get("max_casts_per_run", 20))),
                           recheck=rv.get("enabled", True) is True, recheck_max_items=max(1, min(int(rv.get("max_items", 50)), 500)),
                           page_size=max(1, min(int(obj.get("page_size", 100)), 1000)),
                           max_pages_per_scope=max(1, int(obj.get("max_pages_per_scope", 3))),
                           max_requests_per_run=max(1, int(obj.get("max_requests_per_run", 60))))


def get_api_key(cfg: FarcasterConfig, env: dict | None = None) -> str | None:
    import os
    e = env if env is not None else os.environ
    return e.get(cfg.api_key_env, "").strip() or None


# ---------- transport ----------

class UrllibTransport:
    def __init__(self, base_url: str, header: str = "x-api-key", timeout: float = 20.0, clock: Callable[[], float] = time.time):
        self.base, self.header, self.timeout, self.clock = base_url, header, timeout, clock

    def request(self, method: str, path: str, params: dict | None, secret: str | None) -> HttpResponse:
        url = self.base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        headers = {"User-Agent": "memelab-farcaster/1", "Accept": "application/json"}
        if secret:
            headers[self.header] = secret
        req = urllib.request.Request(url, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                status, hdrs, raw = r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
        except urllib.error.HTTPError as e:
            status, hdrs, raw = e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, e.read() or b""
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise TransientError(f"network: {type(e).__name__}") from None
        try:
            body = json.loads(raw.decode("utf-8")) if raw else None
        except ValueError:
            body = None
        return HttpResponse(status, hdrs, body, self.clock())


class FixtureTransport(_FT):
    def __init__(self, fixture):
        super().__init__(fixture, FIXTURE_SCHEMA)


# ---------- messages -> inbound items ----------

def _hash(v: Any) -> str | None:
    s = str(v or "").lower()
    return s if HASH_RE.match(s) else None


def cast_text(body: dict) -> str | None:
    """Words plus embedded URLs, in order: what the cast shows and where contract links usually sit."""
    parts = [body.get("text") or ""]
    for e in body.get("embeds") or []:
        if isinstance(e, dict) and isinstance(e.get("url"), str):
            parts.append(e["url"])
    t = "\n".join(p for p in parts if p)
    return t or None


def cast_url(username: str | None, h: str) -> str | None:
    return f"https://farcaster.xyz/{username}/{h[:10]}" if username else None


def cast_item(m: dict, fetched_at: float, usernames: dict, sink: TextSink | None) -> dict | None:
    d = m.get("data") or {}
    h = _hash(m.get("hash"))
    fid = d.get("fid")
    if d.get("type") != "MESSAGE_TYPE_CAST_ADD" or not h or not isinstance(fid, int):
        return None
    body = d.get("castAddBody") or {}
    text = cast_text(body)
    chash = store.text_hash(text) if text else None
    if sink is not None and text and chash:
        sink.put(PLATFORM, h, chash, text)
    refs, rtype = [], "ORIGINAL"
    parent = body.get("parentCastId") or {}
    if _hash(parent.get("hash")):
        rtype = "REPLY"
        refs.append({"type": "replied_to", "provider_item_id": _hash(parent["hash"]),
                     "author_id": str(parent["fid"]) if isinstance(parent.get("fid"), int) else None})
    for e in body.get("embeds") or []:
        cid = e.get("castId") if isinstance(e, dict) else None
        if isinstance(cid, dict) and _hash(cid.get("hash")) and len(refs) < 10:
            if rtype == "ORIGINAL":
                rtype = "QUOTE"
            refs.append({"type": "quoted", "provider_item_id": _hash(cid["hash"]),
                         "author_id": str(cid["fid"]) if isinstance(cid.get("fid"), int) else None})
    pub = fc_time(d.get("timestamp"))
    uname = usernames.get(fid)
    item = {"event_id": f"fc.{h}.{canonical_sha([chash, fid, uname])[:16]}", "provider_item_id": h, "url": cast_url(uname, h),
            "published_at": iso(pub) if pub else None, "published_at_basis": "PROVIDER" if pub else None,
            "fetched_at": iso(fetched_at), "retrieval_status": "OK", "content_hash": chash, "visibility": "PUBLIC",
            "account": {"provider_user_id": str(fid), **({"handle": uname, "profile_url": f"https://farcaster.xyz/{uname}"} if uname else {})},
            "context": {"reference_type": rtype, "conversation_id": None, "in_reply_to_user_id": refs[0]["author_id"] if rtype == "REPLY" else None,
                        "edit_history_ids": None, "referenced": refs, "basis": "PROVIDER"}}
    if pub:
        item["version"] = {"kind": "ORIGINAL", "provider_version_at": iso(pub)}
    return {k: v for k, v in item.items() if v is not None}


def recast_item(m: dict, fetched_at: float, usernames: dict) -> dict | None:
    d = m.get("data") or {}
    h = _hash(m.get("hash"))
    rb = d.get("reactionBody") or {}
    tgt = rb.get("targetCastId") or {}
    fid = d.get("fid")
    if (d.get("type") != "MESSAGE_TYPE_REACTION_ADD" or rb.get("type") != "REACTION_TYPE_RECAST" or not h
            or not isinstance(fid, int) or not _hash(tgt.get("hash"))):
        return None
    pub = fc_time(d.get("timestamp"))
    uname = usernames.get(fid)
    return {k: v for k, v in {
        "event_id": f"fc.{h}.recast", "provider_item_id": h, "published_at": iso(pub) if pub else None,
        "published_at_basis": "PROVIDER" if pub else None, "fetched_at": iso(fetched_at), "retrieval_status": "OK",
        "visibility": "PUBLIC",
        "account": {"provider_user_id": str(fid), **({"handle": uname, "profile_url": f"https://farcaster.xyz/{uname}"} if uname else {})},
        "context": {"reference_type": "REPOST", "conversation_id": None, "in_reply_to_user_id": None, "edit_history_ids": None,
                    "referenced": [{"type": "retweeted", "provider_item_id": _hash(tgt["hash"]),
                                    "author_id": str(tgt["fid"]) if isinstance(tgt.get("fid"), int) else None}],
                    "basis": "PROVIDER"}}.items() if v is not None}


def classify_error(status: int, body: Any) -> tuple[str, str]:
    code = ""
    if isinstance(body, dict):
        code = str(body.get("errCode") or body.get("code") or body.get("error") or "")[:40]
    code = redact(code)
    if status in (401, 403):
        return "BLOCKED", f"{status} API key missing or rejected; {code}"
    if status == 402:
        return "BLOCKED", f"402 credits exhausted; {code}"
    if status == 429:
        return "RATE_LIMITED", f"429 rate limited; {code}"
    if status == 404 or "not_found" in code:
        return "DOWN", f"{status} not found; {code}"
    return "DOWN", f"HTTP {status}; {code}"


def _not_found(r: HttpResponse) -> bool:
    code = str((r.body or {}).get("errCode") or "") if isinstance(r.body, dict) else ""
    return r.status == 404 or (r.status in (400, 404) and "not_found" in code)


# ---------- the adapter ----------

class FarcasterHubAdapter:
    name = "farcaster_hub"

    def __init__(self, cfg: FarcasterConfig, transport, api_key: str | None, db_path: Path | str, *, run_id: str | None = None,
                 mode: str = "live", clock: Callable[[], float] = time.time, sleep: Callable[[float], None] = time.sleep,
                 retries: int = 3, base_delay: float = 1.0, text_sink: TextSink | None = None):
        if mode not in ("live", "fixture"):
            raise ValueError("mode must be live or fixture")
        self.cfg, self.transport, self._key = cfg, transport, api_key
        self.db_path, self.run_id, self.mode = Path(db_path), run_id, mode
        self.clock, self.sleep, self.retries, self.base_delay = clock, sleep, retries, base_delay
        self.sink = text_sink
        self.requests = 0
        self.stopped: str | None = None
        self.usernames: dict[int, str | None] = {}
        self.new_casts: list[tuple[int, str]] = []

    def __repr__(self) -> str:
        return f"FarcasterHubAdapter(mode={self.mode!r}, scopes={len(self.cfg.scopes)}, key={'set' if self._key else 'none'})"

    def _scrub(self, s: str) -> str:
        return scrub(s, self._key)

    def _source(self, connector: str, kind: str) -> dict:
        live = self.mode == "live"
        basis = ("farcaster_public_protocol_data_self_hosted_node" if self.cfg.billing == "self_hosted"
                 else "farcaster_public_protocol_data_hosted_hub_terms")
        return {"platform": PLATFORM, "source_id": connector.split(":", 1)[1], "access_mode": "fetch" if live else "fixture",
                "collector": "snapchain-http" if live else "snapchain-http/fixture",
                "rights_basis": basis if live else "synthetic_fixture", "visibility": "PUBLIC", "terms_note": VISIBILITY[kind][:400]}

    def _unit(self, connector: str, status: str, ref: str, error: str | None = None, body: Any = None) -> SourceUnit:
        error = self._scrub(error)[:300] if error else None
        return SourceUnit(connector=connector, platform=PLATFORM, source_ref=ref, status=status,
                          unit_sha=canonical_sha(body if body is not None else [status, ref, error]), body=body, error=error,
                          plan_id=self.run_id)

    def _call(self, con, guard: RequestGuard, connector: str, endpoint: str, params: dict):
        why = guard.check()
        if why:
            return None, "DEGRADED", f"run budget: {why}"

        def once():
            self.requests += 1
            try:
                r = self.transport.request("GET", ENDPOINTS[endpoint], params, self._key)
            except (TransientError, FixtureMiss) as e:
                raise type(e)(self._scrub(str(e))) from None
            except Exception as e:
                raise RuntimeError(f"transport {type(e).__name__}: {self._scrub(str(e))[:160]}") from None
            if r.status >= 500:
                raise TransientError(f"HTTP {r.status}")
            return r
        try:
            r = with_retries(once, attempts=self.retries, base_delay=self.base_delay, sleep=self.sleep,
                             transient=(TransientError,), what=f"farcaster {endpoint}")
        except TransientError as e:
            guard.record(connector=connector, run_id=self.run_id, endpoint=ENDPOINTS[endpoint], status=0, resources={}, now=self.clock())
            return None, "DOWN", f"{self._scrub(str(e))[:120]} after {self.retries} attempts"
        except FixtureMiss as e:
            return None, "DOWN", f"fixture: {e}"
        n = len((r.body or {}).get("messages") or []) if isinstance(r.body, dict) else 0
        guard.record(connector=connector, run_id=self.run_id, endpoint=ENDPOINTS[endpoint], status=r.status,
                     resources={"messages": n}, now=r.received_at)
        log_event("farcaster_request", connector=connector, endpoint=ENDPOINTS[endpoint], status=r.status, mode=self.mode)
        return r, None, None

    def _stop(self, con, scope_conn: str, scope_key: str, status: str, msg: str, ref: str, r: HttpResponse | None = None) -> SourceUnit:
        kw = {"last_status": status}
        if status == "RATE_LIMITED" and r is not None:
            try:
                kw["rate_limit_reset_at"] = r.received_at + float(r.headers.get("retry-after"))
            except (TypeError, ValueError):
                kw["rate_limit_reset_at"] = r.received_at + 60.0
            self.stopped = msg
        if msg.startswith("run budget") or (status == "BLOCKED" and msg[:3] in ("401", "402", "403")):
            self.stopped = msg
        save_cursor(con, scope_conn, scope_key, self.clock(), **kw)
        log_event("farcaster_scope_stopped", connector=scope_conn, status=status, error=self._scrub(msg))
        return self._unit(scope_conn, status, ref, msg)

    def _username(self, con, guard, conn: str, fid: int) -> None:
        """Preferred name (USER_DATA_TYPE_USERNAME) once per fid per run; nothing else about the profile is asked."""
        if fid in self.usernames or len(self.usernames) >= 200:
            return
        r, st, msg = self._call(con, guard, conn, "username", {"fid": fid, "user_data_type": 6})
        name = None
        if r is not None and r.status == 200 and isinstance(r.body, dict):
            for m in r.body.get("messages") or []:
                ub = ((m or {}).get("data") or {}).get("userDataBody") or {}
                if ub.get("type") == "USER_DATA_TYPE_USERNAME" and isinstance(ub.get("value"), str) and NAME_RE.match(ub["value"]):
                    name = ub["value"]
        self.usernames[fid] = name

    def units(self, budget: Budget) -> Iterator[SourceUnit]:
        con = connect(self.db_path)
        try:
            limit = self.cfg.max_usd_per_run if self.cfg.billing == "metered" else None
            guard = RequestGuard(con, connector_prefix="farcaster_hub:", mode=self.mode, max_requests=self.cfg.max_requests_per_run,
                                 usd_per_request=self.cfg.usd_per_request, max_usd_per_run=limit)
            block = None
            if not self.cfg.base_url and self.mode == "live":
                block = "not_configured: no hub.base_url"
            elif self.cfg.billing == "metered" and not self._key:
                block = f"credentials_missing: set {self.cfg.api_key_env}"
            elif self.cfg.billing == "metered" and (not self.cfg.allow_billable or self.cfg.max_usd_per_run <= 0):
                block = "billing_not_consented: budget.allow_billable is false or the run cap is 0"
            if block:
                for s in self.cfg.scopes:
                    yield self._unit(s.connector, "BLOCKED", f"{s.connector}#preflight", block)
                return
            for s in self.cfg.scopes:
                if self.stopped:
                    yield self._unit(s.connector, "DEGRADED", f"{s.connector}#not-run", f"not run: {self.stopped}")
                    continue
                try:
                    yield from self._scope(con, guard, s)
                except Exception as e:
                    yield self._unit(s.connector, "DOWN", f"{s.connector}#error", f"adapter error {type(e).__name__}: {self._scrub(str(e))[:160]}")
            if self.cfg.recasts and not self.stopped:
                yield from self._recasts(con, guard)
            if self.cfg.recheck and not self.stopped:
                yield from self._recheck(con, guard)
        finally:
            con.close()

    def _scope(self, con, guard, s: Scope) -> Iterator[SourceUnit]:
        now = self.clock()
        cur = get_cursor(con, s.connector, s.key)
        if cur and cur["rate_limit_reset_at"] and cur["rate_limit_reset_at"] > now:
            yield self._unit(s.connector, "RATE_LIMITED", f"{s.connector}#waiting", f"rate limit until {iso(cur['rate_limit_reset_at'])}; not called")
            return
        since = float(cur["newest_id"]) if cur and cur["newest_id"] else None
        base = {"pageSize": self.cfg.page_size, "reverse": 1}
        base.update({"fid": s.fid} if s.kind == "fid" else {"url": s.parent_url})
        token, newest, yielded, page, reached = None, None, [], 0, False
        while True:
            page += 1
            p = dict(base)
            if token:
                p["pageToken"] = token
            ref = f"{s.connector}#since={int(since) if since else 'none'}&page={page}"
            r, st, msg = self._call(con, guard, s.connector, s.kind, p)
            if r is None:
                yield self._stop(con, s.connector, s.key, st, msg, ref)
                return
            if r.status != 200:
                st, msg = classify_error(r.status, r.body)
                yield self._stop(con, s.connector, s.key, st, msg, ref, r)
                return
            msgs = [m for m in (r.body or {}).get("messages") or [] if isinstance(m, dict)]
            kept = []
            for m in msgs:
                t = fc_time((m.get("data") or {}).get("timestamp"))
                if since is not None and t is not None and t < since:
                    reached = True
                    continue
                kept.append(m)
            for m in kept:
                f = (m.get("data") or {}).get("fid")
                if isinstance(f, int):
                    self._username(con, guard, s.connector, f)
            items = []
            for m in kept:
                it = cast_item(m, r.received_at, self.usernames, self.sink)
                if it is None:
                    continue
                items.append(it)
                self.new_casts.append((int(it["account"]["provider_user_id"]), it["provider_item_id"]))
                t = fc_time((m.get("data") or {}).get("timestamp"))
                newest = t if t is not None and (newest is None or t > newest) else newest
            env = {"schema": INBOUND_SCHEMA_V3, "source": self._source(s.connector, s.kind), "fetched_at": iso(r.received_at), "items": items}
            unit = self._unit(s.connector, "OK", ref, body=env)
            yielded.append(unit)
            yield unit
            token = (r.body or {}).get("nextPageToken") or None
            if not token or reached:
                break
            if page >= self.cfg.max_pages_per_scope:
                yield self._unit(s.connector, "DEGRADED", f"{s.connector}#gap",
                                 f"page cap {self.cfg.max_pages_per_scope} reached; older casts were not read")
                break
        if units_committed(con, yielded):
            kw = {"last_status": "OK", "last_success_at": self.clock(), "rate_limit_reset_at": None}
            if newest is not None and (since is None or newest > since):
                kw["newest_id"] = str(int(newest))
            save_cursor(con, s.connector, s.key, self.clock(), **kw)
        else:
            save_cursor(con, s.connector, s.key, self.clock(), last_status="PARTIAL")

    def _recasts(self, con, guard) -> Iterator[SourceUnit]:
        conn = "farcaster_hub:recasts:run"
        targets = list(dict.fromkeys(self.new_casts))[: self.cfg.max_recast_lookups]
        skipped = max(0, len(dict.fromkeys(self.new_casts)) - len(targets))
        for fid, h in targets:
            if self.stopped:
                yield self._unit(conn, "DEGRADED", f"{conn}#not-run&cast={h}", f"not run: {self.stopped}")
                break
            ref = f"{conn}#cast={h}"
            r, st, msg = self._call(con, guard, conn, "recasts", {"target_fid": fid, "target_hash": h, "reaction_type": "Recast",
                                                                  "pageSize": self.cfg.page_size})
            if r is None:
                yield self._stop(con, conn, "run", st, msg, ref)
                return
            if r.status != 200:
                st, msg = classify_error(r.status, r.body)
                yield self._stop(con, conn, "run", st, msg, ref, r)
                return
            msgs = [m for m in (r.body or {}).get("messages") or [] if isinstance(m, dict)]
            for m in msgs:
                f = (m.get("data") or {}).get("fid")
                if isinstance(f, int):
                    self._username(con, guard, conn, f)
            items = [it for it in (recast_item(m, r.received_at, self.usernames) for m in msgs) if it]
            env = {"schema": INBOUND_SCHEMA_V3, "source": self._source(conn, "recasts"), "fetched_at": iso(r.received_at), "items": items}
            yield self._unit(conn, "OK", ref, body=env)
            if (r.body or {}).get("nextPageToken"):
                yield self._unit(conn, "DEGRADED", f"{conn}#gap&cast={h}", "more recasts than one page; later pages not read")
        if skipped:
            yield self._unit(conn, "DEGRADED", f"{conn}#cap", f"recast lookups capped at {self.cfg.max_recast_lookups}; {skipped} casts not looked up")

    def _recheck(self, con, guard) -> Iterator[SourceUnit]:
        conn = "farcaster_hub:recheck:stored"
        rows = con.execute(
            "SELECT i.provider_item_id, a.provider_user_id FROM social_items i JOIN social_accounts a ON a.account_id=i.account_id "
            "LEFT JOIN social_item_context c ON c.item_key=i.item_key WHERE i.platform='farcaster' AND COALESCE(c.reference_type,'')<>'REPOST'"
            " AND NOT EXISTS (SELECT 1 FROM social_observations o WHERE o.item_key=i.item_key AND o.retrieval_status IN ('NOT_FOUND','DELETED'))"
            " ORDER BY COALESCE(i.first_observed_at, i.first_ingested_at) DESC, i.provider_item_id LIMIT ?", (self.cfg.recheck_max_items,)).fetchall()
        fresh = {h for _, h in self.new_casts}
        rows = [r for r in rows if r[0] not in fresh and r[1] and str(r[1]).isdigit()]
        items, fetched = [], self.clock()
        for h, fid in rows:
            r, st, msg = self._call(con, guard, conn, "cast", {"fid": int(fid), "hash": h})
            if r is None:
                yield self._stop(con, conn, "stored", st, msg, f"{conn}#cast={h}")
                break
            fetched = r.received_at
            if _not_found(r):
                items.append({"event_id": f"fc.{h}.not_found.{time.strftime('%Y-%m-%d', time.gmtime(r.received_at))}",
                              "provider_item_id": h, "fetched_at": iso(r.received_at), "retrieval_status": "NOT_FOUND", "visibility": "PUBLIC"})
            elif r.status == 200 and isinstance(r.body, dict):
                it = cast_item(r.body, r.received_at, self.usernames, self.sink)
                if it:
                    items.append(it)
            else:
                st, msg = classify_error(r.status, r.body)
                yield self._stop(con, conn, "stored", st, msg, f"{conn}#cast={h}", r)
                break
        env = {"schema": INBOUND_SCHEMA_V3, "source": self._source(conn, "recheck"), "fetched_at": iso(fetched), "items": items}
        yield self._unit(conn, "OK", f"{conn}#n={len(rows)}&ids={canonical_sha([r[0] for r in rows])[:12]}", body=env)
        save_cursor(con, conn, "stored", self.clock(), last_status="OK", last_success_at=self.clock())


# ---------- health ----------

def health(config_path: Path | str | None, db_path: Path | str, env: dict | None = None, now: float | None = None) -> dict:
    """No network call. Status: not_configured | credentials_missing | billing_not_consented | ready."""
    t = time.time() if now is None else now
    out: dict = {"adapter": "farcaster_hub", "contract_verified": CONTRACT_VERIFIED, "network_calls_made": 0}
    cfg = None
    if config_path and Path(config_path).exists():
        try:
            cfg = load_config(config_path)
        except Exception as e:
            out["config_error"] = redact(str(e))[:200]
    key = get_api_key(cfg, env) if cfg else None
    out["config"] = None if cfg is None else {
        "base_url_set": bool(cfg.base_url), "billing": cfg.billing, "api_key_env": cfg.api_key_env,
        "scopes": [s.connector for s in cfg.scopes], "allow_billable": cfg.allow_billable, "max_usd_per_run": cfg.max_usd_per_run,
        "usd_per_request": cfg.usd_per_request, "max_requests_per_run": cfg.max_requests_per_run}
    out["credentials"] = "not_needed" if cfg is None or cfg.billing == "self_hosted" else ("present" if key else "missing")
    out["cost"] = ("self-hosted node: no per-request charge (your own server and bandwidth)" if cfg is None or cfg.billing == "self_hosted"
                   else f"metered hub: estimated ${cfg.usd_per_request:.5f} per request, capped at ${cfg.max_usd_per_run:.2f} per run")
    con = connect(db_path)
    try:
        live = con.execute("SELECT COUNT(*), MAX(requested_at), SUM(http_status=200), COALESCE(SUM(est_cost_usd),0) FROM social_api_spend "
                           "WHERE mode='live' AND connector LIKE 'farcaster_hub:%'").fetchone()
        out["live_evidence"] = {"requests": live[0], "successful": live[2] or 0, "last_request_at": live[1],
                                "est_cost_usd_total": round(live[3], 4),
                                "verdict": "live read proved" if live[2] else "none: no live Farcaster read has been made"}
        out["cursors"] = [{k: r[k] for k in ("connector", "scope", "newest_id", "last_status", "last_success_at", "rate_limit_reset_at")}
                          for r in con.execute("SELECT * FROM social_source_cursors WHERE connector LIKE 'farcaster_hub:%' ORDER BY connector")]
        for c in out["cursors"]:
            c["age_hours"] = round((t - c["last_success_at"]) / 3600, 1) if c["last_success_at"] else None
        out["connector_health"] = [dict(r) for r in con.execute(
            "SELECT h.connector, h.status, h.checked_at, h.error FROM social_connector_health h WHERE h.connector LIKE 'farcaster_hub:%'"
            " AND h.checked_at=(SELECT MAX(checked_at) FROM social_connector_health WHERE connector=h.connector) ORDER BY h.connector")]
    finally:
        con.close()
    if cfg is None or not cfg.base_url or not cfg.scopes:
        out["status"] = "not_configured"
    elif cfg.billing == "metered" and not key:
        out["status"] = "credentials_missing"
    elif cfg.billing == "metered" and (not cfg.allow_billable or cfg.max_usd_per_run <= 0):
        out["status"] = "billing_not_consented"
    else:
        out["status"] = "ready"
    out["next_step"] = {
        "not_configured": "run a Snapchain node (free, self-hosted) or choose a hosted hub, then write data/private/farcaster_hub.json "
                          "from docs/social-intelligence/farcaster_hub.example.json with hub.base_url and scopes",
        "credentials_missing": "export the hosted hub's API key in the variable named by hub.api_key_env",
        "billing_not_consented": "set budget.allow_billable true and a non-zero max_usd_per_run (Elving's cost decision)",
        "ready": "run one small live ingest (one scope, max_pages_per_scope 1) and check `social fc-health` live_evidence",
    }[out["status"]]
    return out
