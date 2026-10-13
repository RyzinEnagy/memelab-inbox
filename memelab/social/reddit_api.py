"""Reddit Data API adapter (Phase 19, optional source): selected, approved communities only.

Contract read 2026-10-12 (docs/social-intelligence/SOURCES_19.md has the sources and the gaps):

  POST https://www.reddit.com/api/v1/access_token   grant_type=client_credentials, HTTP Basic client id:secret
                                                    -> {access_token, token_type 'bearer', expires_in, scope}
  GET  https://oauth.reddit.com/r/{sub}/about       subreddit_type (public, restricted, private, ...), name (t5_ id)
  GET  https://oauth.reddit.com/r/{sub}/new         submissions newest first; limit <= 100; after=<fullname>
  GET  https://oauth.reddit.com/r/{sub}/comments    newest comments in the community; limit <= 100; after=<fullname>
  GET  https://oauth.reddit.com/api/info            id=<fullname,...> (<= 100): current state of stored items
  Every call: OAuth token, a unique User-Agent '<platform>:<app id>:<version> (by /u/<username>)', raw_json=1.
  Rate limit: 100 queries per minute per OAuth client id, averaged over 10 minutes; headers X-Ratelimit-Used,
  -Remaining, -Reset (seconds). 429 when exceeded.
  Access: the Responsible Builder Policy requires explicit approval before any Reddit data is accessed; commercial
  use, selling or sharing data and training models need separate written approval. Deleted posts, comments and
  accounts must be removed from stored data (Reddit recommends within 48 hours), even if de-identified.

What this adapter stores (D-010, D-013, D-016): fullnames (t3_, t1_, t2_, t5_ ids), the author's username and
t2_ id, provider times, a hash of the title/body (the words are hashed in memory and dropped), score-type counts,
the parent, thread and cross-post parent ids, and edit times. Never stored: titles, bodies, link targets, flair,
media, display names, private messages, anything from private communities. Canonical URLs carry ids only
(no title slug), because the slug is the title.

Deleted and removed items: a sighting with [deleted] / [removed] content becomes retrieval_status DELETED, and
purge_deleted() then erases what the lab derived from that item's words (content hashes, metrics, claim spans,
private copies). An author shown as [deleted] while the content stays means the account was deleted: the account
row, its handle history and its links from items and observations are erased. The CLI runs the purge after every
ingest, so erasure happens at the next run after detection.

Safety: no approval flag in the config -> no request; no credentials -> no request; commercial_use must be false;
request cap per run; 429 and a low X-Ratelimit-Remaining stop the scope until the reset time; secrets never logged.
"""
from __future__ import annotations

import base64
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
from .api_common import (FixtureMiss, FixtureTransport as _FT, HttpResponse, RequestGuard, TextSink, connect, erase_accounts,
                         get_cursor, iso, purge_gone_items, save_cursor, scrub, units_committed)
from .ingest import INBOUND_SCHEMA_V3, Budget, SourceUnit, TransientError, canonical_sha, log_event, redact, with_retries

PLATFORM = "reddit"
ID_ENV, SECRET_ENV = "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"
CONFIG_SCHEMA = "memelab.reddit_api.config/1"
FIXTURE_SCHEMA = "memelab.reddit_api.fixture/1"
CONTRACT_VERIFIED = "2026-10-12"
TOKEN_HOST, API_HOST = "https://www.reddit.com", "https://oauth.reddit.com"
TOKEN_PATH = "/api/v1/access_token"
ENDPOINTS = {"about": "/r/{sub}/about", "submissions": "/r/{sub}/new", "comments": "/r/{sub}/comments", "info": "/api/info"}
READABLE_TYPES = ("public", "restricted", "archived")      # 'restricted' = anyone can read, only approved users post
FORBIDDEN_CONFIG_KEYS = {"secret", "client_secret", "password", "token", "access_token", "refresh_token", "api_key"}
SUB_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_]{1,20}$")
USER_RE = re.compile(r"^[A-Za-z0-9_\-]{3,20}$")
B36 = re.compile(r"^[0-9a-z]{1,13}$")
GONE = {"[deleted]", "[removed]"}
VISIBILITY = {
    "submissions": "Reddit Data API /new listing of one approved community: posts in other communities are not read; "
                   "a listing shows at most about 1000 items; scores are fuzzed by Reddit",
    "comments": "Reddit Data API /comments listing of one approved community: newest comments only, older comments are "
                "not backfilled; scores are fuzzed by Reddit",
    "recheck": "Reddit Data API /api/info lookup of stored items: [deleted] and [removed] are DELETED, a missing id is "
               "NOT_FOUND; a deleted account shows as [deleted]",
}


def b36(fullname: str) -> int:
    return int(fullname.split("_", 1)[1], 36)


# ---------- config ----------

@dataclass
class Community:
    name: str
    submissions: bool = True
    comments: bool = True


@dataclass
class RedditConfig:
    communities: list[Community]
    app_id: str
    version: str
    reddit_username: str | None
    approved: bool = False
    approval_reference: str | None = None
    commercial_use: bool = False
    recheck: bool = True
    recheck_max_items: int = 100
    page_size: int = 100
    max_pages_per_listing: int = 3
    max_requests_per_run: int = 30
    min_remaining: float = 5.0
    timeout_seconds: float = 20.0

    @property
    def user_agent(self) -> str:
        who = f" (by /u/{self.reddit_username})" if self.reddit_username else ""
        return f"python:{self.app_id}:{self.version}{who}"


def load_config(obj: dict | str | Path) -> RedditConfig:
    if not isinstance(obj, dict):
        obj = json.loads(Path(obj).read_text())
    if obj.get("schema") != CONFIG_SCHEMA:
        raise ValueError(f"config schema must be {CONFIG_SCHEMA}")

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if str(k).lower() in FORBIDDEN_CONFIG_KEYS:
                    raise ValueError(f"config must not hold credentials (key '{k}'); use {ID_ENV} and {SECRET_ENV}")
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    if obj.get("commercial_use") is not False:
        raise ValueError("commercial_use must be false: commercial use of Reddit data needs Reddit's written approval")
    ua = obj.get("user_agent") or {}
    app_id, version = ua.get("app_id"), ua.get("version")
    if not isinstance(app_id, str) or not re.fullmatch(r"[A-Za-z0-9_.\-]{3,40}", app_id):
        raise ValueError("user_agent.app_id: 3-40 letters, digits, '_', '.' or '-'")
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9_.\-]{1,20}", version):
        raise ValueError("user_agent.version: 1-20 letters, digits, '_', '.' or '-'")
    user = ua.get("reddit_username")
    if user is not None and (not isinstance(user, str) or not USER_RE.match(user)):
        raise ValueError("user_agent.reddit_username: 3-20 letters, digits, '_' or '-'")
    comms, seen = [], set()
    for i, c in enumerate(obj.get("communities") or []):
        name = c.get("name") if isinstance(c, dict) else None
        if not isinstance(name, str) or not SUB_RE.match(name):
            raise ValueError(f"communities[{i}].name: a community name without 'r/'")
        if name.lower() in seen:
            raise ValueError(f"communities[{i}]: duplicate community")
        seen.add(name.lower())
        comms.append(Community(name.lower(), submissions=c.get("submissions", True) is True, comments=c.get("comments", True) is True))
    ap = obj.get("access_approval") or {}
    rc = obj.get("recheck") or {}
    return RedditConfig(communities=comms, app_id=app_id, version=version, reddit_username=user,
                        approved=ap.get("approved") is True, approval_reference=ap.get("reference"),
                        commercial_use=False, recheck=rc.get("enabled", True) is True,
                        recheck_max_items=max(1, min(int(rc.get("max_items", 100)), 1000)),
                        page_size=max(1, min(int(obj.get("page_size", 100)), 100)),
                        max_pages_per_listing=max(1, int(obj.get("max_pages_per_listing", 3))),
                        max_requests_per_run=max(1, int(obj.get("max_requests_per_run", 30))),
                        min_remaining=max(0.0, float(obj.get("min_remaining", 5))))


def get_credentials(env: dict | None = None) -> tuple[str | None, str | None]:
    import os
    e = env if env is not None else os.environ
    return (e.get(ID_ENV, "").strip() or None), (e.get(SECRET_ENV, "").strip() or None)


# ---------- transport ----------

class UrllibTransport:
    """The only code that talks to reddit.com. The client secret goes into the token request's Basic header only,
    and the access token into the Authorization header only."""

    def __init__(self, user_agent: str, timeout: float = 20.0, clock: Callable[[], float] = time.time):
        self.ua, self.timeout, self.clock = user_agent, timeout, clock

    def request(self, method: str, path: str, params: dict | None, secret: str | None, *, client_id: str | None = None) -> HttpResponse:
        if method == "POST":
            data = urllib.parse.urlencode(params or {}).encode()
            basic = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
            req = urllib.request.Request(TOKEN_HOST + path, data=data, method="POST",
                                         headers={"Authorization": f"Basic {basic}", "User-Agent": self.ua})
        else:
            url = API_HOST + path + ("?" + urllib.parse.urlencode(params) if params else "")
            req = urllib.request.Request(url, headers={"Authorization": f"bearer {secret}", "User-Agent": self.ua})
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

    def request(self, method, path, params, secret, *, client_id=None):
        return super().request(method, path, params, secret)


# ---------- provider object -> inbound item ----------

def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _gone(d: dict, kind: str) -> str | None:
    """'deleted' or 'removed' when the provider shows the content as gone, else None."""
    words = [d.get("body")] if kind == "t1" else [d.get("selftext"), d.get("title")]
    for w in words:
        if isinstance(w, str) and w.strip() in GONE:
            return "removed" if w.strip() == "[removed]" else "deleted"
    cat = d.get("removed_by_category")
    if isinstance(cat, str) and cat:
        return "deleted" if cat == "deleted" else "removed"
    return None


def _text(d: dict, kind: str) -> str | None:
    if kind == "t1":
        return d.get("body") if isinstance(d.get("body"), str) else None
    parts = [d.get("title") or "", d.get("selftext") or ""]
    if d.get("is_self") is False and isinstance(d.get("url"), str):
        parts.append(d["url"])          # a link post's target is part of what was posted; hashed with the title
    t = "\n\n".join(p for p in parts if p)
    return t or None


def item_url(kind: str, d: dict) -> str | None:
    rid = str(d.get("id") or "")
    if not B36.match(rid):
        return None
    if kind == "t3":
        return f"https://www.reddit.com/comments/{rid}/"
    link = str(d.get("link_id") or "")
    if link.startswith("t3_") and B36.match(link[3:]):
        return f"https://www.reddit.com/comments/{link[3:]}/_/{rid}/"
    return None


def to_item(kind: str, d: dict, fetched_at: float, sink: TextSink | None, community_type: str | None = None) -> dict | None:
    """One Reddit thing (t3 submission or t1 comment) -> one inbound/3 item. Text is hashed and goes no further,
    except into the in-memory sink when the caller asked for extraction."""
    name = d.get("name") or (f"{kind}_{d['id']}" if d.get("id") else None)
    if not isinstance(name, str) or not name.startswith(kind + "_") or not B36.match(name[3:]):
        return None
    gone = _gone(d, kind)
    author, author_id = d.get("author"), d.get("author_fullname")
    account_deleted = author == "[deleted]" and not gone
    text = None if gone else _text(d, kind)
    chash = store.text_hash(text) if text else None
    if sink is not None and text and chash:
        sink.put(PLATFORM, name, chash, text)
    if kind == "t3":
        keys = ("score", "num_comments", "upvote_ratio", "num_crossposts")
    else:
        keys = ("score",)
    metrics = None if gone else ({k: d[k] for k in keys if _num(d.get(k))} or None)
    edited = d.get("edited") if _num(d.get("edited")) and d.get("edited") > 0 else None
    types = {t for t in (community_type, d.get("subreddit_type")) if t is not None}   # either one saying not public wins
    refs, rtype, conv = [], "ORIGINAL", None
    if kind == "t3":
        conv = name
        cp = d.get("crosspost_parent")
        if isinstance(cp, str) and cp.startswith("t3_") and B36.match(cp[3:]):
            rtype = "REPOST"
            plist = d.get("crosspost_parent_list") or [{}]
            pa = plist[0].get("author_fullname") if isinstance(plist[0], dict) else None
            refs.append({"type": "retweeted", "provider_item_id": cp,
                         "author_id": pa if isinstance(pa, str) and pa.startswith("t2_") else None})
    else:
        rtype = "REPLY"
        link, parent = d.get("link_id"), d.get("parent_id")
        conv = link if isinstance(link, str) and link.startswith("t3_") else None
        if isinstance(parent, str) and parent[:3] in ("t1_", "t3_") and B36.match(parent[3:]):
            refs.append({"type": "replied_to", "provider_item_id": parent, "author_id": None})
    created = d.get("created_utc") if _num(d.get("created_utc")) else None
    status = "DELETED" if gone else "OK"
    state = [chash, metrics, author_id, author, edited, status, gone]
    item = {
        "event_id": f"rd.{name}.{canonical_sha(state)[:16]}",
        "provider_item_id": name,
        "url": item_url(kind, d),
        "published_at": iso(float(created)) if created else None,
        "published_at_basis": "PROVIDER" if created else None,
        "fetched_at": iso(fetched_at),
        "retrieval_status": status,
        "content_hash": chash,
        "metrics": metrics,
        "visibility": "PUBLIC" if types <= set(READABLE_TYPES) else "NOT_PUBLIC",
        "context": {"reference_type": rtype, "conversation_id": conv, "in_reply_to_user_id": None,
                    "edit_history_ids": None, "referenced": refs, "basis": "PROVIDER"},
    }
    if created and not gone:
        item["version"] = {"kind": "EDIT" if edited else "ORIGINAL", "provider_version_at": iso(float(edited or created))}
    if (not gone and not account_deleted and isinstance(author, str) and USER_RE.match(author)
            and isinstance(author_id, str) and author_id.startswith("t2_")):
        item["account"] = {"provider_user_id": author_id, "handle": author,
                           "profile_url": f"https://www.reddit.com/user/{author}/"}
    return {k: v for k, v in item.items() if v is not None}, ("account_deleted" if account_deleted else None)


def classify_error(status: int, body: Any) -> tuple[str, str]:
    msg = ""
    if isinstance(body, dict):
        msg = str(body.get("reason") or body.get("message") or body.get("error") or "")[:60]
    msg = redact(msg)
    if status == 401:
        return "BLOCKED", f"401 credentials rejected; {msg}"
    if status == 403:
        if "private" in msg.lower() or "quarantin" in msg.lower():
            return "BLOCKED", f"403 private or quarantined community; {msg}"
        return "BLOCKED", f"403 forbidden; {msg}"
    if status == 404:
        return "DOWN", f"404 not found (banned or missing community); {msg}"
    if status == 429:
        return "RATE_LIMITED", f"429 rate limited; {msg}"
    return "DOWN", f"HTTP {status}; {msg}"


# ---------- the adapter ----------

class RedditApiAdapter:
    """SourceAdapter for the Reddit Data API. One SourceUnit per page (or per stop condition), inbound schema /3."""

    name = "reddit_api"

    def __init__(self, cfg: RedditConfig, transport, client_id: str | None, client_secret: str | None, db_path: Path | str, *,
                 run_id: str | None = None, mode: str = "live", clock: Callable[[], float] = time.time,
                 sleep: Callable[[float], None] = time.sleep, retries: int = 3, base_delay: float = 1.0,
                 text_sink: TextSink | None = None):
        if mode not in ("live", "fixture"):
            raise ValueError("mode must be live or fixture")
        self.cfg, self.transport = cfg, transport
        self._id, self._secret, self._token = client_id, client_secret, None
        self.db_path, self.run_id, self.mode = Path(db_path), run_id, mode
        self.clock, self.sleep, self.retries, self.base_delay = clock, sleep, retries, base_delay
        self.sink = text_sink
        self.requests = 0
        self.account_deletion_items: list[str] = []  # items whose author now shows as [deleted] (account deleted)
        self.stopped: str | None = None

    def __repr__(self) -> str:
        return (f"RedditApiAdapter(mode={self.mode!r}, communities={len(self.cfg.communities)}, "
                f"credentials={'set' if self._id and self._secret else 'missing'})")

    def _scrub(self, s: str) -> str:
        return scrub(s, self._secret, self._token, self._id)

    def _source(self, connector: str, kind: str) -> dict:
        live = self.mode == "live"
        return {"platform": PLATFORM, "source_id": connector.split(":", 1)[1], "access_mode": "fetch" if live else "fixture",
                "collector": "reddit-data-api" if live else "reddit-data-api/fixture",
                "rights_basis": "reddit_data_api_terms_approved_noncommercial" if live else "synthetic_fixture",
                "visibility": "PUBLIC", "terms_note": VISIBILITY[kind][:400]}

    def _unit(self, connector: str, status: str, ref: str, error: str | None = None, body: Any = None) -> SourceUnit:
        error = self._scrub(error)[:300] if error else None
        return SourceUnit(connector=connector, platform=PLATFORM, source_ref=ref, status=status,
                          unit_sha=canonical_sha(body if body is not None else [status, ref, error]), body=body, error=error,
                          plan_id=self.run_id)

    def _call(self, con, guard: RequestGuard, connector: str, endpoint: str, method: str, path: str,
              params: dict) -> tuple[HttpResponse | None, str | None, str | None]:
        why = guard.check()
        if why:
            return None, "DEGRADED", f"run budget: {why}"
        secret = self._secret if method == "POST" else self._token

        def once():
            self.requests += 1
            try:
                r = self.transport.request(method, path, params, secret, client_id=self._id)
            except (TransientError, FixtureMiss) as e:
                raise type(e)(self._scrub(str(e))) from None
            except Exception as e:
                raise RuntimeError(f"transport {type(e).__name__}: {self._scrub(str(e))[:160]}") from None
            if r.status >= 500:
                raise TransientError(f"HTTP {r.status}")
            return r
        try:
            r = with_retries(once, attempts=self.retries, base_delay=self.base_delay, sleep=self.sleep,
                             transient=(TransientError,), what=f"reddit {endpoint}")
        except TransientError as e:
            guard.record(connector=connector, run_id=self.run_id, endpoint=path if method == "POST" else ENDPOINTS.get(endpoint, path),
                         status=0, resources={}, now=self.clock())
            return None, "DOWN", f"{self._scrub(str(e))[:120]} after {self.retries} attempts"
        except FixtureMiss as e:
            return None, "DOWN", f"fixture: {e}"
        children = ((r.body or {}).get("data") or {}).get("children") if isinstance(r.body, dict) else None
        guard.record(connector=connector, run_id=self.run_id, endpoint=TOKEN_PATH if method == "POST" else ENDPOINTS[endpoint],
                     status=r.status, resources={"things": len(children) if isinstance(children, list) else 0}, now=r.received_at)
        log_event("reddit_request", connector=connector, endpoint=ENDPOINTS.get(endpoint, TOKEN_PATH), status=r.status,
                  remaining=r.headers.get("x-ratelimit-remaining"), mode=self.mode)
        return r, None, None

    @staticmethod
    def _reset_at(r: HttpResponse) -> float:
        try:
            return r.received_at + float(r.headers.get("x-ratelimit-reset"))
        except (TypeError, ValueError):
            return r.received_at + 600.0          # documented averaging window is 10 minutes

    def _low(self, r: HttpResponse) -> bool:
        try:
            return float(r.headers.get("x-ratelimit-remaining")) < self.cfg.min_remaining
        except (TypeError, ValueError):
            return False

    def _stop(self, con, connector: str, scope: str, status: str, msg: str, ref: str, r: HttpResponse | None = None) -> SourceUnit:
        kw = {"last_status": status}
        if status == "RATE_LIMITED" and r is not None:
            kw["rate_limit_reset_at"] = self._reset_at(r)
            self.stopped = msg          # one client id shares one limit: stop every scope
        if msg.startswith("run budget") or status == "BLOCKED" and msg.startswith("401"):
            self.stopped = msg
        save_cursor(con, connector, scope, self.clock(), **kw)
        log_event("reddit_scope_stopped", connector=connector, status=status, error=self._scrub(msg))
        return self._unit(connector, status, ref, msg)

    def _authorize(self, con, guard) -> SourceUnit | None:
        conn = "reddit_api:auth"
        r, st, msg = self._call(con, guard, conn, "token", "POST", TOKEN_PATH, {"grant_type": "client_credentials"})
        if r is None:
            self.stopped = msg
            return self._unit(conn, st, f"{conn}#token", msg)
        if r.status != 200 or not isinstance(r.body, dict) or not r.body.get("access_token"):
            st, msg = classify_error(r.status if r.status != 200 else 401, r.body)
            self.stopped = msg
            return self._unit(conn, st, f"{conn}#token", msg)
        self._token = str(r.body["access_token"])
        return None

    # -- SourceAdapter --
    def units(self, budget: Budget) -> Iterator[SourceUnit]:
        con = connect(self.db_path)
        self.started_at = self.clock()
        try:
            guard = RequestGuard(con, connector_prefix="reddit_api:", mode=self.mode, max_requests=self.cfg.max_requests_per_run)
            scopes = []
            for c in self.cfg.communities:
                if c.submissions:
                    scopes.append((c, "submissions"))
                if c.comments:
                    scopes.append((c, "comments"))
            if not self.cfg.approved or self.cfg.commercial_use:
                for c, kind in scopes:
                    yield self._unit(f"reddit_api:sub:{c.name}:{kind}", "BLOCKED", f"reddit_api:sub:{c.name}:{kind}#approval",
                                     "approval_missing: Reddit requires explicit approval before Data API access")
                return
            if not (self._id and self._secret):
                for c, kind in scopes:
                    yield self._unit(f"reddit_api:sub:{c.name}:{kind}", "BLOCKED", f"reddit_api:sub:{c.name}:{kind}#credentials",
                                     f"credentials_missing: set {ID_ENV} and {SECRET_ENV}")
                return
            stop = self._authorize(con, guard)
            if stop:
                yield stop
                return
            about: dict[str, str | None] = {}
            for c, kind in scopes:
                conn = f"reddit_api:sub:{c.name}:{kind}"
                if self.stopped:
                    yield self._unit(conn, "DEGRADED", f"{conn}#not-run", f"not run: {self.stopped}")
                    continue
                try:
                    if c.name not in about:
                        about[c.name], u = self._about(con, guard, c, conn)
                        if u is not None:
                            yield u
                    if about[c.name] is None:
                        if not self.stopped:
                            yield self._unit(conn, "BLOCKED", f"{conn}#community", "community not readable; see the about unit")
                        continue
                    yield from self._listing(con, guard, c, kind, conn, about[c.name])
                except Exception as e:
                    msg = f"adapter error {type(e).__name__}: {self._scrub(str(e))[:160]}"
                    yield self._unit(conn, "DOWN", f"{conn}#error", msg)
            if self.cfg.recheck and not self.stopped:
                try:
                    yield from self._recheck(con, guard)
                except Exception as e:
                    yield self._unit("reddit_api:recheck:stored", "DOWN", "reddit_api:recheck:stored#error",
                                     f"adapter error {type(e).__name__}: {self._scrub(str(e))[:160]}")
        finally:
            con.close()

    def _about(self, con, guard, c: Community, conn: str) -> tuple[str | None, SourceUnit | None]:
        """The community must be readable without membership. Returns (subreddit_type or None, stop unit)."""
        ref = f"{conn}#about"
        cur = get_cursor(con, conn, c.name)
        if cur and cur["rate_limit_reset_at"] and cur["rate_limit_reset_at"] > self.clock():
            self.stopped = f"rate limit window until {iso(cur['rate_limit_reset_at'])}"
            return None, self._unit(conn, "RATE_LIMITED", f"{conn}#waiting", f"{self.stopped}; not called")
        r, st, msg = self._call(con, guard, conn, "about", "GET", ENDPOINTS["about"].format(sub=c.name), {"raw_json": 1})
        if r is None:
            return None, self._stop(con, conn, c.name, st, msg, ref)
        if r.status != 200:
            st, msg = classify_error(r.status, r.body)
            return None, self._stop(con, conn, c.name, st, msg, ref, r)
        d = (r.body or {}).get("data") or {}
        stype = d.get("subreddit_type")
        if stype not in READABLE_TYPES:
            return None, self._stop(con, conn, c.name, "BLOCKED", f"not_public: community type is {str(stype)[:20]}", ref)
        if d.get("quarantine") is True:
            return None, self._stop(con, conn, c.name, "BLOCKED", "quarantined community: not read", ref)
        if isinstance(d.get("name"), str) and d["name"].startswith("t5_"):
            save_cursor(con, conn, c.name, self.clock(), provider_scope_id=d["name"])
        return stype, None

    def _listing(self, con, guard, c: Community, kind: str, conn: str, stype: str) -> Iterator[SourceUnit]:
        cur = get_cursor(con, conn, c.name)
        since = cur["newest_id"] if cur else None
        thing = "t3" if kind == "submissions" else "t1"
        path = ENDPOINTS[kind].format(sub=c.name)
        after, newest, yielded, page, reached = None, None, [], 0, False
        while True:
            page += 1
            p = {"limit": self.cfg.page_size, "raw_json": 1}
            if after:
                p["after"] = after
            ref = f"{conn}#since={since or 'none'}&page={page}"
            r, st, msg = self._call(con, guard, conn, kind, "GET", path, p)
            if r is None:
                yield self._stop(con, conn, c.name, st, msg, ref)
                return
            if r.status != 200:
                st, msg = classify_error(r.status, r.body)
                if st == "RATE_LIMITED":
                    msg += f"; resets {iso(self._reset_at(r))}"
                yield self._stop(con, conn, c.name, st, msg, ref, r)
                return
            data = (r.body or {}).get("data") or {}
            children = [ch for ch in data.get("children") or [] if isinstance(ch, dict) and ch.get("kind") == thing]
            items = []
            for ch in children:
                d = ch.get("data") or {}
                nm = d.get("name")
                if since and isinstance(nm, str) and b36(nm) <= b36(since):
                    reached = True
                    continue
                if isinstance(d.get("subreddit"), str) and d["subreddit"].lower() != c.name:
                    continue                    # never keep items from a community that was not approved
                res = to_item(thing, d, r.received_at, self.sink, stype)
                if res is None:
                    continue
                it, flag = res
                if flag == "account_deleted":
                    self.account_deletion_items.append(it["provider_item_id"])
                items.append(it)
                if isinstance(nm, str) and (newest is None or b36(nm) > b36(newest)):
                    newest = nm
            env = {"schema": INBOUND_SCHEMA_V3, "source": self._source(conn, kind), "fetched_at": iso(r.received_at), "items": items}
            unit = self._unit(conn, "OK", ref, body=env)
            yielded.append(unit)
            yield unit
            after = data.get("after")
            if not after or reached:
                break
            if page >= self.cfg.max_pages_per_listing:
                yield self._unit(conn, "DEGRADED", f"{conn}#since={since or 'none'}&gap",
                                 f"page cap {self.cfg.max_pages_per_listing} reached; older items "
                                 f"{'down to the cursor' if since else 'before this window'} were not read")
                break
            if self._low(r):
                yield self._stop(con, conn, c.name, "RATE_LIMITED",
                                 f"X-Ratelimit-Remaining below {self.cfg.min_remaining:g}; resets {iso(self._reset_at(r))}",
                                 f"{conn}#since={since or 'none'}&page={page + 1}", r)
                return
        if units_committed(con, yielded):
            kw = {"last_status": "OK", "last_success_at": self.clock(), "rate_limit_reset_at": None}
            if newest and (since is None or b36(newest) > b36(since)):
                kw["newest_id"] = newest
            save_cursor(con, conn, c.name, self.clock(), **kw)
        else:
            save_cursor(con, conn, c.name, self.clock(), last_status="PARTIAL")

    def _recheck(self, con, guard) -> Iterator[SourceUnit]:
        conn = "reddit_api:recheck:stored"
        ids = [r[0] for r in con.execute(
            "SELECT i.provider_item_id FROM social_items i WHERE i.platform='reddit' AND i.provider_item_id IS NOT NULL"
            " AND i.first_ingested_at < ? AND NOT EXISTS (SELECT 1 FROM social_observations o WHERE o.item_key=i.item_key AND o.retrieval_status IN ('NOT_FOUND','DELETED'))"
            " ORDER BY COALESCE(i.first_observed_at, i.first_ingested_at) DESC, i.provider_item_id LIMIT ?", (self.started_at, self.cfg.recheck_max_items))]
        ids = [i for i in ids if i[:3] in ("t1_", "t3_")]
        if not ids:
            yield self._unit(conn, "OK", f"{conn}#empty", body={"schema": INBOUND_SCHEMA_V3, "source": self._source(conn, "recheck"),
                                                               "fetched_at": iso(self.clock()), "items": []})
            return
        for b in range(0, len(ids), 100):
            chunk = ids[b:b + 100]
            ref = f"{conn}#batch={b // 100 + 1}&ids={canonical_sha(chunk)[:12]}"
            r, st, msg = self._call(con, guard, conn, "info", "GET", ENDPOINTS["info"], {"id": ",".join(chunk), "raw_json": 1})
            if r is None:
                yield self._stop(con, conn, "stored", st, msg, ref)
                return
            if r.status != 200:
                st, msg = classify_error(r.status, r.body)
                yield self._stop(con, conn, "stored", st, msg, ref, r)
                return
            items, seen = [], set()
            for ch in ((r.body or {}).get("data") or {}).get("children") or []:
                if not isinstance(ch, dict) or ch.get("kind") not in ("t1", "t3"):
                    continue
                d = ch.get("data") or {}
                res = to_item(ch["kind"], d, r.received_at, self.sink)
                if res is None:
                    continue
                it, flag = res
                if flag == "account_deleted":
                    self.account_deletion_items.append(it["provider_item_id"])
                items.append(it)
                seen.add(it["provider_item_id"])
            day = time.strftime("%Y-%m-%d", time.gmtime(r.received_at))
            for rid in chunk:
                if rid not in seen:
                    items.append({"event_id": f"rd.{rid}.not_found.{day}", "provider_item_id": rid, "fetched_at": iso(r.received_at),
                                  "retrieval_status": "NOT_FOUND", "visibility": "PUBLIC"})
            env = {"schema": INBOUND_SCHEMA_V3, "source": self._source(conn, "recheck"), "fetched_at": iso(r.received_at), "items": items}
            yield self._unit(conn, "OK", ref, body=env)
        save_cursor(con, conn, "stored", self.clock(), last_status="OK", last_success_at=self.clock())


# ---------- deletion compliance ----------

def purge_deleted(db_path: Path | str, *, now: float, deleted_accounts: list[str] | tuple = (),
                  deleted_account_items: list[str] | tuple = (), private_path=None) -> dict:
    """Erase what the lab derived from Reddit items that are now deleted or removed, and erase accounts seen as
    deleted. Ids and the DELETED/NOT_FOUND sightings stay (they say that something existed and is gone, nothing more).

    Per gone item: content hashes, summaries, metrics and private refs on every observation; versions; claim spans,
    claim summaries, extraction outputs and their hashes; private copies of the text. Narrative snapshots keep their
    counts (they are dated statistics with no wording); the item no longer votes in later runs (NOT_PRESENT).
    Per gone item also the link to its author (the post was the author's; the account itself stays unless deleted).
    Per deleted account: the account row, handle history, and account links on items, observations and claims. A deleted
    account is named by its t2_ id, or by an item whose author now shows as [deleted] while the content stays (Reddit
    drops author_fullname then, so the account is the one the lab stored for that item). Idempotent."""
    con = connect(db_path)
    try:
        out = purge_gone_items(con, PLATFORM, private_path=private_path)
        targets = {}
        for t2 in set(deleted_accounts):
            acct = con.execute("SELECT account_id FROM social_accounts WHERE platform='reddit' AND provider_user_id=?", (t2,)).fetchone()
            if acct is not None:
                targets[acct[0]] = t2
        for name in set(deleted_account_items):
            row = con.execute("SELECT a.account_id, a.provider_user_id FROM social_items i JOIN social_accounts a ON a.account_id=i.account_id "
                              "WHERE i.item_key=?", (store.item_key_for(PLATFORM, name, None),)).fetchone()
            if row is not None:
                targets[row[0]] = row[1]
        out["accounts_erased"] = erase_accounts(con, targets)
        con.commit()
    finally:
        con.close()
    log_event("reddit_purge", **out)
    return out


# ---------- health ----------

def health(config_path: Path | str | None, db_path: Path | str, env: dict | None = None, now: float | None = None) -> dict:
    """No network call. Status: not_configured | approval_missing | credentials_missing | ready."""
    t = time.time() if now is None else now
    cid, sec = get_credentials(env)
    out: dict = {"adapter": "reddit_api", "contract_verified": CONTRACT_VERIFIED, "credential_env": [ID_ENV, SECRET_ENV],
                 "credentials": "present" if cid and sec else "missing", "network_calls_made": 0,
                 "cost": "free tier: 100 queries per minute per OAuth client, non-commercial use only; estimated $0 per request"}
    cfg = None
    if config_path and Path(config_path).exists():
        try:
            cfg = load_config(config_path)
        except Exception as e:
            out["config_error"] = redact(str(e))[:200]
    out["config"] = None if cfg is None else {
        "communities": [c.name for c in cfg.communities], "approved": cfg.approved, "commercial_use": cfg.commercial_use,
        "max_requests_per_run": cfg.max_requests_per_run, "max_pages_per_listing": cfg.max_pages_per_listing,
        "user_agent": cfg.user_agent}
    con = connect(db_path)
    try:
        live = con.execute("SELECT COUNT(*), MAX(requested_at), SUM(http_status=200) FROM social_api_spend "
                           "WHERE mode='live' AND connector LIKE 'reddit_api:%'").fetchone()
        out["live_evidence"] = {"requests": live[0], "successful": live[2] or 0, "last_request_at": live[1],
                                "verdict": "live authorized ingest proved" if live[2] else "none: no live Reddit read has been made"}
        out["requests_this_month"] = con.execute(
            "SELECT COUNT(*) FROM social_api_spend WHERE mode='live' AND connector LIKE 'reddit_api:%' AND substr(billing_day,1,7)=?",
            (time.strftime("%Y-%m", time.gmtime(t)),)).fetchone()[0]
        out["cursors"] = [{k: r[k] for k in ("connector", "scope", "newest_id", "last_status", "last_success_at", "rate_limit_reset_at")}
                          for r in con.execute("SELECT * FROM social_source_cursors WHERE connector LIKE 'reddit_api:%' ORDER BY connector")]
        for c in out["cursors"]:
            c["age_hours"] = round((t - c["last_success_at"]) / 3600, 1) if c["last_success_at"] else None
        out["connector_health"] = [dict(r) for r in con.execute(
            "SELECT h.connector, h.status, h.checked_at, h.error FROM social_connector_health h WHERE h.connector LIKE 'reddit_api:%'"
            " AND h.checked_at=(SELECT MAX(checked_at) FROM social_connector_health WHERE connector=h.connector) ORDER BY h.connector")]
        pend = con.execute("SELECT COUNT(DISTINCT o.item_key) FROM social_observations o JOIN social_items i ON i.item_key=o.item_key "
                           "WHERE i.platform='reddit' AND o.retrieval_status IN ('DELETED','NOT_FOUND') AND EXISTS (SELECT 1 FROM "
                           "social_observations o2 WHERE o2.item_key=o.item_key AND o2.content_hash IS NOT NULL)").fetchone()[0]
        out["deletion_purge_pending_items"] = pend
    finally:
        con.close()
    if cfg is None or not cfg.communities:
        out["status"] = "not_configured"
    elif not cfg.approved:
        out["status"] = "approval_missing"
    elif not (cid and sec):
        out["status"] = "credentials_missing"
    else:
        out["status"] = "ready"
    out["next_step"] = {
        "not_configured": "write the community config (docs/social-intelligence/reddit_api.example.json) to data/private/reddit_api.json",
        "approval_missing": "request Data API access from Reddit (Responsible Builder Policy) for non-commercial research; "
                            "after written approval set access_approval.approved true with the reference",
        "credentials_missing": f"create the approved app's credentials and export {ID_ENV} and {SECRET_ENV} in the shell that runs memelab",
        "ready": "run one small live ingest (one community, max_pages_per_listing 1) and check `social reddit-health` live_evidence",
    }[out["status"]]
    return out
