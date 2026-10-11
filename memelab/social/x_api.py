"""X API v2 adapter (Phase 03): explicitly configured public accounts, lists and recent-search scopes.

Contract verified against the official docs on 2026-10-10 (docs/social-intelligence/X_API_03.md has the sources):

  GET /2/users/{id}/tweets       user timeline; max_results 5-100; pagination_token; since_id; exclude=replies,retweets
  GET /2/lists/{id}/tweets       list timeline; max_results 1-100; pagination_token; no since_id
  GET /2/tweets/search/recent    last 7 days only; max_results 10-100; next_token; since_id
  GET /2/users/by/username/{u}   resolve a configured handle to a user id (once, cached in social_source_cursors)
  GET /2/tweets?ids=             lookup, used by the 'recheck' scope to see whether stored posts still exist
  Auth: app-only Bearer token (env X_BEARER_TOKEN). Rate-limit headers x-rate-limit-limit/-remaining/-reset;
  429 until the reset time. Errors are problem objects {type, title, detail}; a 200 can carry partial errors.
  Billing: pay-per-use, prepaid credits, charged per resource returned (posts $0.005, users $0.010 at
  verification), deduplicated per UTC day; failed requests are not billed.

What this adapter stores (D-010, D-013, D-016): post id, author user id and handle, provider time, a hash of the
post text, public metric counts and reference/thread/edit ids. The text is hashed in memory and dropped; it is
never logged, returned or written anywhere. X's Developer Guidelines allow storing API content subject to its
deletion rules, but this repo's database is public, so the lab's stricter rule applies.

Safety:
  - No credentials -> no request. Every scope reports BLOCKED with 'credentials_missing'.
  - Billing guard: a request is made only when budget.allow_billable is true and the worst-case cost of the
    request fits both the per-run and the per-month cap (live spend from social_api_spend). Defaults are 0.
  - Fixture mode (recorded synthetic HTTP exchanges) is labelled access_mode='fixture' and
    rights_basis='synthetic_fixture'; its spend rows have mode='fixture' and never count as live evidence.
  - 429 stops the scope and records the reset time; the next run skips the scope until then. 401/403/404 stop the
    scope with a precise status. 5xx and network errors get bounded retries.
  - The cursor (newest fully ingested id) advances only after every page of the scope was committed by ingest().
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from . import store
from .ingest import (INBOUND_SCHEMA_V2, Budget, BudgetExceeded, SourceUnit, TransientError, canonical_sha, log_event,
                     redact, with_retries)

API_BASE = "https://api.x.com"
TOKEN_ENV = "X_BEARER_TOKEN"
CONFIG_SCHEMA = "memelab.x_api.config/1"
FIXTURE_SCHEMA = "memelab.x_api.fixture/1"
CONTRACT_VERIFIED = "2026-10-10"
# Per-resource read prices on docs.x.com/x-api/getting-started/pricing, read 2026-10-10. Estimates only:
# the Developer Console is the bill. Override in the config if X changes them.
DEFAULT_PRICES = {"post": 0.005, "user": 0.010}
ENDPOINTS = {
    "user": "/2/users/{id}/tweets",
    "list": "/2/lists/{id}/tweets",
    "search": "/2/tweets/search/recent",
    "resolve_user": "/2/users/by/username/{username}",
    "lookup": "/2/tweets",
}
PAGE_PARAM = {"user": "pagination_token", "list": "pagination_token", "search": "next_token"}
MAX_RESULTS = {"user": (5, 100), "list": (1, 100), "search": (10, 100)}
TWEET_FIELDS = "id,text,note_tweet,author_id,created_at,conversation_id,in_reply_to_user_id,referenced_tweets,edit_history_tweet_ids,public_metrics"
EXPANSIONS = "author_id,referenced_tweets.id,referenced_tweets.id.author_id"
USER_FIELDS = "id,username,protected"
FORBIDDEN_CONFIG_KEYS = {"token", "bearer", "bearer_token", "secret", "api_key", "api_secret", "access_token", "password"}

# What each scope kind cannot see. Written into every envelope (source.terms_note -> provenance) and the docs.
VISIBILITY = {
    "user": "X API v2 user timeline: only the configured account's own posts; protected accounts and their posts "
            "are not visible; quotes and replies by other accounts are not read; replies/reposts dropped when excluded in config",
    "list": "X API v2 list timeline: posts by list members only; private lists need user-context auth (not used); "
            "no since_id, so the cursor is applied client-side",
    "search": "X API v2 recent search: last 7 days only; protected posts never match; full-archive search not used",
    "recheck": "X API v2 post lookup: a missing post is NOT_FOUND (deleted, never existed or suspended author are "
               "indistinguishable); a protected one is PROTECTED; edits appear as new post ids, not as changes",
}


# ---------- config ----------

@dataclass
class Scope:
    kind: str                       # user | list | search | recheck
    key: str                        # stable text for the cursor: handle, user id, list id or search name
    username: str | None = None
    user_id: str | None = None
    list_id: str | None = None
    query: str | None = None
    exclude: list[str] = field(default_factory=list)
    max_items: int = 100            # recheck only

    @property
    def connector(self) -> str:
        return f"x_api:{self.kind}:{self.key}"


@dataclass
class XConfig:
    scopes: list[Scope]
    max_results: int = 100
    max_pages_per_scope: int = 3
    allow_billable: bool = False
    max_usd_per_run: float = 0.0
    max_usd_per_month: float = 0.0
    prices: dict = field(default_factory=lambda: dict(DEFAULT_PRICES))
    max_rate_wait_seconds: float = 0.0
    fields_param: str = "tweet.fields"
    expansions: str = EXPANSIONS
    timeout_seconds: float = 20.0


def _id(v: Any, what: str) -> str:
    s = str(v).strip() if v is not None else ""
    if not s.isdigit() or len(s) > 19:
        raise ValueError(f"{what}: must be 1-19 digits")
    return s


def load_config(obj: dict | str | Path) -> XConfig:
    """Parse and check a config. Credentials never live in the config (env X_BEARER_TOKEN only)."""
    if not isinstance(obj, dict):
        obj = json.loads(Path(obj).read_text())
    if obj.get("schema") != CONFIG_SCHEMA:
        raise ValueError(f"config schema must be {CONFIG_SCHEMA}")

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if str(k).lower() in FORBIDDEN_CONFIG_KEYS:
                    raise ValueError(f"config must not hold credentials (key '{k}'); use the {TOKEN_ENV} environment variable")
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    scopes, seen = [], set()
    for i, s in enumerate(obj.get("scopes") or []):
        kind = s.get("kind")
        if kind == "user":
            if s.get("user_id"):
                sc = Scope("user", key=_id(s["user_id"], f"scopes[{i}].user_id"), user_id=_id(s["user_id"], "user_id"))
            else:
                u = store._handle(s.get("username"))
                if not u or not all(c.isalnum() or c == "_" for c in u) or len(u) > 15:
                    raise ValueError(f"scopes[{i}].username: 1-15 letters, digits or underscore")
                sc = Scope("user", key=u.lower(), username=u)
            ex = s.get("exclude") or []
            if not isinstance(ex, list) or not set(ex) <= {"replies", "retweets"}:
                raise ValueError(f"scopes[{i}].exclude: only 'replies' and 'retweets'")
            sc.exclude = sorted(set(ex))
        elif kind == "list":
            lid = _id(s.get("list_id"), f"scopes[{i}].list_id")
            sc = Scope("list", key=lid, list_id=lid)
        elif kind == "search":
            name, q = s.get("name"), s.get("query")
            if not isinstance(name, str) or not name or not all(c.isalnum() or c in "_-" for c in name) or len(name) > 40:
                raise ValueError(f"scopes[{i}].name: 1-40 letters, digits, '_' or '-'")
            if not isinstance(q, str) or not (1 <= len(q) <= 4096):
                raise ValueError(f"scopes[{i}].query: 1-4096 characters")
            sc = Scope("search", key=name, query=q)
        elif kind == "recheck":
            sc = Scope("recheck", key="stored_posts", max_items=max(1, min(int(s.get("max_items", 100)), 1000)))
        else:
            raise ValueError(f"scopes[{i}].kind: user, list, search or recheck")
        if sc.connector in seen:
            raise ValueError(f"scopes[{i}]: duplicate scope {sc.connector}")
        seen.add(sc.connector)
        scopes.append(sc)
    b = obj.get("budget") or {}
    prices = dict(DEFAULT_PRICES)
    prices.update({k: float(v) for k, v in (obj.get("prices_usd") or {}).items() if k in DEFAULT_PRICES})
    return XConfig(scopes=scopes, max_results=max(1, min(int(obj.get("max_results", 100)), 100)),
                   max_pages_per_scope=max(1, int(obj.get("max_pages_per_scope", 3))),
                   allow_billable=b.get("allow_billable") is True,
                   max_usd_per_run=max(0.0, float(b.get("max_usd_per_run", 0))),
                   max_usd_per_month=max(0.0, float(b.get("max_usd_per_month", 0))), prices=prices,
                   max_rate_wait_seconds=max(0.0, float(obj.get("max_rate_wait_seconds", 0))),
                   fields_param=obj.get("fields_param", "tweet.fields"), expansions=obj.get("expansions", EXPANSIONS))


def get_token(env: dict | None = None) -> str | None:
    import os
    v = (env if env is not None else os.environ).get(TOKEN_ENV, "")
    return v.strip() or None


# ---------- transport ----------

@dataclass
class HttpResponse:
    status: int
    headers: dict
    body: Any
    received_at: float


class UrllibTransport:
    """The only code that talks to api.x.com. The token goes into one header and nowhere else."""

    def __init__(self, timeout: float = 20.0, clock: Callable[[], float] = time.time):
        self.timeout = timeout
        self.clock = clock

    def get(self, path: str, params: dict, token: str) -> HttpResponse:
        url = API_BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "User-Agent": "memelab-x-api/1"})
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


class FixtureMiss(Exception):
    """A request the recorded fixture does not contain. Not transient: the contract changed or the test is wrong."""


class FixtureTransport:
    """Replays recorded synthetic exchanges. Matching is on path plus exact query parameters; an exchange listed
    twice for the same request is served in order (e.g. a 503 then a 200). 'raise' simulates a transport error
    whose message may even contain the token (to prove redaction)."""

    def __init__(self, fixture: dict | str | Path):
        if not isinstance(fixture, dict):
            fixture = json.loads(Path(fixture).read_text())
        if fixture.get("schema") != FIXTURE_SCHEMA:
            raise ValueError(f"fixture schema must be {FIXTURE_SCHEMA}")
        self.exchanges = fixture["exchanges"]
        self.used: set[int] = set()
        self.calls: list[dict] = []

    @staticmethod
    def _norm(params: dict) -> dict:
        return {str(k): str(v) for k, v in (params or {}).items()}

    def get(self, path: str, params: dict, token: str) -> HttpResponse:
        p = self._norm(params)
        self.calls.append({"path": path, "params": p, "auth_header_sent": bool(token)})
        for i, ex in enumerate(self.exchanges):
            rq = ex["request"]
            if i in self.used or rq["path"] != path or self._norm(rq.get("params")) != p:
                continue
            self.used.add(i)
            if "raise" in ex:
                raise TransientError(ex["raise"].replace("{token}", token))
            rs = ex["response"]
            return HttpResponse(int(rs["status"]), {k.lower(): str(v) for k, v in (rs.get("headers") or {}).items()},
                                rs.get("body"), store.to_utc(ex["recorded_at"]))
        raise FixtureMiss(f"no recorded exchange for {path} with parameters {sorted(p)}")


# ---------- billing guard ----------

def billing_day(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")


class BillingGuard:
    """Refuses a request unless billable reads are consented and its worst-case cost fits the run and month caps.
    Spend is estimated from what each response returned, after the per-UTC-day dedupe."""

    def __init__(self, cfg: XConfig, con, mode: str, connector_prefix: str = "x_api:"):
        self.cfg, self.con, self.mode = cfg, con, mode
        self.prefix = connector_prefix
        self.run_spent = 0.0

    def month_spent(self, now: float) -> float:
        month = billing_day(now)[:7]
        r = self.con.execute("SELECT COALESCE(SUM(est_cost_usd),0) FROM social_api_spend WHERE mode=? AND substr(billing_day,1,7)=?"
                             " AND connector LIKE ?", (self.mode, month, self.prefix + "%")).fetchone()
        return float(r[0])

    def check(self, worst: float, now: float) -> str | None:
        """None = allowed; otherwise the reason, which goes into health and coverage."""
        if not self.cfg.allow_billable:
            return "billing_guard: billable reads not consented (budget.allow_billable is false)"
        if self.run_spent + worst > self.cfg.max_usd_per_run + 1e-12:
            return f"billing_guard: run cap ${self.cfg.max_usd_per_run:.3f} would be exceeded (worst case ${worst:.3f})"
        if self.month_spent(now) + worst > self.cfg.max_usd_per_month + 1e-12:
            return f"billing_guard: monthly cap ${self.cfg.max_usd_per_month:.3f} would be exceeded (worst case ${worst:.3f})"
        return None

    def record(self, *, connector: str, run_id: str | None, endpoint: str, status: int, resources: dict[str, list[str]],
               now: float) -> float:
        """Write the spend row. Only successful responses that returned data are billed (pricing docs)."""
        day = billing_day(now)
        counts, cost = {}, 0.0
        if status == 200:
            for rtype, ids in resources.items():
                new = 0
                for rid in dict.fromkeys(ids):
                    cur = self.con.execute("INSERT OR IGNORE INTO social_api_billed_resources(connector,billing_day,resource_type,"
                                           "resource_id,mode) VALUES (?,?,?,?,?)", (connector, day, rtype, rid, self.mode))
                    new += cur.rowcount
                counts[rtype] = {"returned": len(ids), "billable_new": new}
                cost += new * self.cfg.prices.get(rtype, 0.0)
        self.con.execute("INSERT INTO social_api_spend(connector,run_id,endpoint,http_status,billing_day,resources_json,est_cost_usd,"
                         "mode,requested_at) VALUES (?,?,?,?,?,?,?,?,?)",
                         (connector, run_id, endpoint, status, day, json.dumps(counts, sort_keys=True), cost, self.mode, now))
        self.con.commit()
        self.run_spent += cost
        return cost


# ---------- response -> inbound items ----------

def _iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _refs(p: dict) -> list[dict]:
    return p.get("referenced_tweets") or p.get("referenced_posts") or []


def reference_type(p: dict, requested: bool = True) -> str:
    if not requested:
        return "UNKNOWN"
    types = {r.get("type") for r in _refs(p)}
    if "retweeted" in types:
        return "REPOST"
    if "replied_to" in types:
        return "REPLY"        # a reply that also quotes stays a REPLY; the quote is kept in social_item_refs
    if "quoted" in types:
        return "QUOTE"
    return "ORIGINAL"


def post_item(p: dict, users: dict, ref_posts: dict, fetched_at: float, refs_requested: bool) -> dict:
    """One API post -> one inbound/2 item. The text is hashed here and goes no further."""
    pid = str(p["id"])
    author = str(p["author_id"]) if p.get("author_id") else None
    u = users.get(author) or {}
    username = u.get("username")
    text = (p.get("note_tweet") or {}).get("text") or p.get("text")
    chash = store.text_hash(text) if text else None
    metrics = {k: v for k, v in (p.get("public_metrics") or {}).items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    hist = [str(x) for x in (p.get("edit_history_tweet_ids") or p.get("edit_history_post_ids") or [])] or None
    refs = []
    for r in _refs(p)[:10]:
        rid = str(r.get("id"))
        rp = ref_posts.get(rid) or {}
        refs.append({"type": r.get("type"), "provider_item_id": rid,
                     "author_id": str(rp["author_id"]) if rp.get("author_id") else None})
    item = {
        # same post in the same state = same event, from any scope or rerun; a change (metrics, edit, handle) is new
        "event_id": "api." + pid + "." + canonical_sha([chash, metrics, author, username, hist])[:16],
        "provider_item_id": pid,
        "url": f"https://x.com/{username}/status/{pid}" if username else f"https://x.com/i/web/status/{pid}",
        "published_at": p.get("created_at"),
        "published_at_basis": "PROVIDER" if p.get("created_at") else None,
        "fetched_at": _iso(fetched_at),
        "retrieval_status": "OK",
        "content_hash": chash,
        "metrics": metrics or None,
        "visibility": "PROTECTED" if u.get("protected") is True else "PUBLIC",
        "context": {"reference_type": reference_type(p, refs_requested),
                    "conversation_id": str(p["conversation_id"]) if p.get("conversation_id") else None,
                    "in_reply_to_user_id": str(p["in_reply_to_user_id"]) if p.get("in_reply_to_user_id") else None,
                    "edit_history_ids": hist, "referenced": refs,
                    "basis": "PROVIDER" if refs_requested else "NOT_REQUESTED"},
    }
    if author:
        item["account"] = {"provider_user_id": author, **({"handle": username, "profile_url": f"https://x.com/{username}"} if username else {})}
    return {k: v for k, v in item.items() if v is not None}


def _problem(body: Any) -> str:
    """'<type-suffix>: <title>' from a problem object, never the detail (it can echo ids or query text)."""
    if isinstance(body, dict):
        e = body
        if not e.get("type") and isinstance(body.get("errors"), list) and body["errors"]:
            e = body["errors"][0] if isinstance(body["errors"][0], dict) else {}
        t = str(e.get("type") or "").rstrip("/").rsplit("/", 1)[-1] or "about:blank"
        title = str(e.get("title") or e.get("message") or "")[:80]
        return redact(f"{t}: {title}" if title else t)
    return "no problem body"


STATUS_FOR = {401: ("BLOCKED", "credentials rejected (401)"), 402: ("BLOCKED", "payment required / credits depleted (402)")}


def classify_error(status: int, body: Any) -> tuple[str, str]:
    """HTTP error -> (connector status, message). 403 is split by problem type (docs: response codes and errors)."""
    prob = _problem(body)
    if status in STATUS_FOR:
        s, m = STATUS_FOR[status]
        return s, f"{m}; {prob}"
    if status == 403:
        if "not-authorized-for-resource" in prob:
            return "BLOCKED", f"403 protected or private resource; {prob}"
        if "client-forbidden" in prob:
            return "BLOCKED", f"403 app not enrolled or lacks the access level for this endpoint; {prob}"
        return "BLOCKED", f"403 forbidden; {prob}"
    if status == 429:
        return "RATE_LIMITED", f"429; {prob}"
    if status == 404:
        return "DOWN", f"404 not found; {prob}"
    if status == 400:
        return "DOWN", f"400 invalid request; {prob}"
    return "DOWN", f"HTTP {status}; {prob}"


# ---------- the adapter ----------

class XApiAdapter:
    """SourceAdapter for X API v2. One SourceUnit per page read (or per stop condition), inbound schema /2."""

    name = "x_api"

    def __init__(self, cfg: XConfig, transport, token: str | None, db_path: Path | str, *, run_id: str | None = None,
                 mode: str = "live", clock: Callable[[], float] = time.time, sleep: Callable[[float], None] = time.sleep,
                 retries: int = 3, base_delay: float = 1.0):
        if mode not in ("live", "fixture"):
            raise ValueError("mode must be live or fixture")
        self.cfg, self.transport, self._token = cfg, transport, token
        self.db_path, self.run_id, self.mode = Path(db_path), run_id, mode
        self.clock, self.sleep, self.retries, self.base_delay = clock, sleep, retries, base_delay
        self.stopped: str | None = None
        self.requests = 0

    def __repr__(self) -> str:   # never show the token
        return f"XApiAdapter(mode={self.mode!r}, scopes={len(self.cfg.scopes)}, token={'set' if self._token else 'missing'})"

    # -- source fields --
    def _source(self, scope: Scope) -> dict:
        live = self.mode == "live"
        note = VISIBILITY[scope.kind]
        if scope.exclude:
            note += f"; excluded by config: {','.join(scope.exclude)}"
        return {"platform": "x", "source_id": scope.connector.split(":", 1)[1], "access_mode": "fetch" if live else "fixture",
                "collector": "x-api-v2" if live else "x-api-v2/fixture",
                "rights_basis": "x_api_v2_developer_agreement" if live else "synthetic_fixture",
                "visibility": "PUBLIC", "terms_note": note[:400]}

    def _scrub(self, s: str) -> str:
        """Remove the exact token wherever it hides, then the generic secret patterns."""
        if self._token:
            s = s.replace(self._token, "[REDACTED]")
        return redact(s)

    def _unit(self, scope: Scope, status: str, ref: str, error: str | None = None, body: Any = None) -> SourceUnit:
        error = self._scrub(error)[:300] if error else None
        return SourceUnit(connector=scope.connector, platform="x", source_ref=ref, status=status,
                          unit_sha=canonical_sha(body if body is not None else [status, ref, error]),
                          body=body, error=error, plan_id=self.run_id)

    # -- cursor --
    def _cursor(self, con, scope: Scope):
        return con.execute("SELECT * FROM social_source_cursors WHERE connector=? AND scope=?", (scope.connector, scope.key)).fetchone()

    def _save_cursor(self, con, scope: Scope, **kw) -> None:
        now = self.clock()
        row = self._cursor(con, scope)
        cur = dict(row) if row else {"provider_scope_id": None, "newest_id": None, "last_success_at": None, "rate_limit_reset_at": None}
        cur.update(kw)
        con.execute("INSERT INTO social_source_cursors(connector,scope,provider_scope_id,newest_id,last_success_at,last_attempt_at,"
                    "last_status,rate_limit_reset_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(connector,scope) DO UPDATE SET"
                    " provider_scope_id=excluded.provider_scope_id, newest_id=excluded.newest_id, last_success_at=excluded.last_success_at,"
                    " last_attempt_at=excluded.last_attempt_at, last_status=excluded.last_status,"
                    " rate_limit_reset_at=excluded.rate_limit_reset_at, updated_at=excluded.updated_at",
                    (scope.connector, scope.key, cur["provider_scope_id"], cur["newest_id"], cur["last_success_at"], now,
                     cur.get("last_status", "UNKNOWN"), cur["rate_limit_reset_at"], now))
        con.commit()

    def _committed(self, con, units: list[SourceUnit]) -> bool:
        for u in units:
            r = con.execute("SELECT status FROM social_ingest_checkpoints WHERE connector=? AND source_ref=? AND unit_sha=?",
                            (u.connector, u.source_ref, u.unit_sha)).fetchone()
            if r is None or r[0] != "COMPLETE":
                return False
        return True

    # -- one request with guard, retries, spend --
    def _call(self, con, guard: BillingGuard, budget: Budget, scope: Scope, endpoint: str, path: str, params: dict,
              worst: float) -> tuple[HttpResponse | None, str | None, str | None]:
        """Returns (response, stop_status, stop_message). Never raises for HTTP or network trouble."""
        why = guard.check(worst, self.clock())
        if why:
            return None, "BLOCKED", why
        try:
            budget.charge("requests", cost=0.0)
            if budget.max_cost is not None and budget.used["cost"] + worst > budget.max_cost + 1e-12:
                raise BudgetExceeded(f"cost budget {budget.max_cost} reached")
        except BudgetExceeded as e:
            return None, "DEGRADED", f"run budget: {e}"

        def once():
            self.requests += 1
            try:
                r = self.transport.get(path, params, self._token)
            except (TransientError, FixtureMiss) as e:
                # re-raise without the original: an HTTP library message can carry the Authorization header
                raise type(e)(self._scrub(str(e))) from None
            except Exception as e:
                raise RuntimeError(f"transport {type(e).__name__}: {self._scrub(str(e))[:160]}") from None
            if r.status >= 500:
                raise TransientError(f"HTTP {r.status}")
            return r
        try:
            r = with_retries(once, attempts=self.retries, base_delay=self.base_delay, sleep=self.sleep,
                             transient=(TransientError,), what=f"x_api {endpoint}")
        except TransientError as e:
            return None, "DOWN", f"{self._scrub(str(e))[:120]} after {self.retries} attempts"
        except FixtureMiss as e:
            return None, "DOWN", f"fixture: {e}"
        if r.status == 429 and self.cfg.max_rate_wait_seconds > 0:
            wait = self._reset_at(r) - self.clock()
            if 0 < wait <= self.cfg.max_rate_wait_seconds:
                log_event("x_rate_wait", connector=scope.connector, wait_s=round(wait, 1))
                self.sleep(wait)
                try:
                    r = with_retries(once, attempts=self.retries, base_delay=self.base_delay, sleep=self.sleep,
                                     transient=(TransientError,), what=f"x_api {endpoint}")
                except (TransientError, FixtureMiss) as e:
                    return None, "DOWN", self._scrub(str(e))[:160]
        resources: dict[str, list[str]] = {}
        if r.status == 200 and isinstance(r.body, dict):
            data = r.body.get("data")
            rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
            inc = r.body.get("includes") or {}
            if endpoint == "resolve_user":
                resources["user"] = [str(x.get("id")) for x in rows]
            else:
                resources["post"] = [str(x.get("id")) for x in rows] + [str(x.get("id")) for x in inc.get("tweets") or []]
                resources["user"] = [str(x.get("id")) for x in inc.get("users") or []]
        cost = guard.record(connector=scope.connector, run_id=self.run_id, endpoint=ENDPOINTS[endpoint], status=r.status,
                            resources=resources, now=r.received_at)
        if cost:
            budget.used["cost"] += cost
        log_event("x_request", connector=scope.connector, endpoint=ENDPOINTS[endpoint], status=r.status,
                  remaining=r.headers.get("x-rate-limit-remaining"), est_cost_usd=round(cost, 4), mode=self.mode)
        return r, None, None

    @staticmethod
    def _reset_at(r: HttpResponse) -> float:
        try:
            return float(r.headers.get("x-rate-limit-reset"))
        except (TypeError, ValueError):
            return r.received_at + 900.0   # documented window is 15 minutes

    def _worst(self, n_posts: int) -> float:
        # every post may bring an author and a referenced post (with its author) in includes: upper bound
        exp = self.cfg.expansions or ""
        users = n_posts * (("author_id" in exp) + ("referenced_tweets.id.author_id" in exp))
        refs = n_posts * ("referenced_tweets.id" in exp)
        return n_posts * self.cfg.prices["post"] + refs * self.cfg.prices["post"] + users * self.cfg.prices["user"]

    # -- SourceAdapter --
    def units(self, budget: Budget) -> Iterator[SourceUnit]:
        con = store_connect(self.db_path)
        try:
            guard = BillingGuard(self.cfg, con, self.mode)
            for scope in self.cfg.scopes:
                if self.stopped:
                    yield self._unit(scope, "DEGRADED", f"{scope.connector}#not-run", f"not run: {self.stopped}")
                    continue
                if not self._token:
                    yield self._unit(scope, "BLOCKED", f"{scope.connector}#credentials", f"credentials_missing: set {TOKEN_ENV}")
                    continue
                try:
                    yield from (self._recheck(con, guard, budget, scope) if scope.kind == "recheck"
                                else self._timeline(con, guard, budget, scope))
                except Exception as e:   # one scope's bug or surprise never ends the run
                    msg = f"adapter error {type(e).__name__}: {self._scrub(str(e))[:160]}"
                    log_event("x_scope_error", connector=scope.connector, error=msg)
                    yield self._unit(scope, "DOWN", f"{scope.connector}#error", msg)
        finally:
            con.close()

    def _stop(self, con, scope: Scope, status: str, msg: str, ref: str, r: HttpResponse | None = None) -> SourceUnit:
        kw = {"last_status": status}
        if status == "RATE_LIMITED" and r is not None:
            kw["rate_limit_reset_at"] = self._reset_at(r)
        self._save_cursor(con, scope, **kw)
        if msg.startswith("billing_guard") or msg.startswith("run budget"):
            self.stopped = msg
        msg = self._scrub(msg)
        log_event("x_scope_stopped", connector=scope.connector, status=status, error=msg)
        return self._unit(scope, status, ref, msg)

    def _resolve_user(self, con, guard, budget, scope: Scope) -> tuple[str | None, SourceUnit | None]:
        if scope.user_id:
            return scope.user_id, None
        row = self._cursor(con, scope)
        if row and row["provider_scope_id"]:
            return row["provider_scope_id"], None
        ref = f"{scope.connector}#resolve"
        r, st, msg = self._call(con, guard, budget, scope, "resolve_user", ENDPOINTS["resolve_user"].format(username=scope.username),
                                {"user.fields": USER_FIELDS}, self.cfg.prices["user"])
        if r is None:
            return None, self._stop(con, scope, st, msg, ref)
        if r.status != 200:
            st, msg = classify_error(r.status, r.body)
            return None, self._stop(con, scope, st, msg, ref, r)
        d = (r.body or {}).get("data") or {}
        if not d.get("id"):
            st, msg = "DOWN", "user not found; " + _problem((r.body or {}).get("errors", [{}])[0] if (r.body or {}).get("errors") else r.body)
            return None, self._stop(con, scope, st, msg, ref, r)
        if d.get("protected") is True:
            return None, self._stop(con, scope, "BLOCKED", "protected account: posts are not visible to app-only access", ref, r)
        self._save_cursor(con, scope, provider_scope_id=str(d["id"]))
        return str(d["id"]), None

    def _timeline(self, con, guard, budget, scope: Scope) -> Iterator[SourceUnit]:
        now = self.clock()
        cur = self._cursor(con, scope)
        if cur and cur["rate_limit_reset_at"] and cur["rate_limit_reset_at"] > now:
            yield self._unit(scope, "RATE_LIMITED", f"{scope.connector}#waiting",
                             f"rate limit window until {_iso(cur['rate_limit_reset_at'])}; not called")
            return
        since = cur["newest_id"] if cur else None
        lo, hi = MAX_RESULTS[scope.kind]
        n = max(lo, min(self.cfg.max_results, hi))
        params = {self.cfg.fields_param: TWEET_FIELDS, "user.fields": USER_FIELDS, "max_results": n}
        if self.cfg.expansions:
            params["expansions"] = self.cfg.expansions
        if scope.kind == "user":
            uid, stop = self._resolve_user(con, guard, budget, scope)
            if stop:
                yield stop
                return
            path = ENDPOINTS["user"].format(id=uid)
            if scope.exclude:
                params["exclude"] = ",".join(scope.exclude)
        elif scope.kind == "list":
            path = ENDPOINTS["list"].format(id=scope.list_id)
        else:
            path = ENDPOINTS["search"]
            params["query"] = scope.query
        if since and scope.kind in ("user", "search"):
            params["since_id"] = since
        refs_requested = "referenced_tweets" in TWEET_FIELDS
        token, newest, yielded, page, reached_cursor = None, None, [], 0, False
        while True:
            page += 1
            p = dict(params)
            if token:
                p[PAGE_PARAM[scope.kind]] = token
            ref = f"{scope.connector}#since={since or 'none'}&page={page}"
            r, st, msg = self._call(con, guard, budget, scope, scope.kind, path, p, self._worst(n))
            if r is None:
                yield self._stop(con, scope, st, msg, ref)
                return
            if r.status != 200:
                st, msg = classify_error(r.status, r.body)
                if st == "RATE_LIMITED":
                    msg += f"; resets {_iso(self._reset_at(r))}"
                yield self._stop(con, scope, st, msg, ref, r)
                return
            body = r.body if isinstance(r.body, dict) else {}
            data = body.get("data") or []
            inc = body.get("includes") or {}
            users = {str(u.get("id")): u for u in inc.get("users") or []}
            ref_posts = {str(t.get("id")): t for t in inc.get("tweets") or []}
            if scope.kind == "list" and since:   # list timelines have no since_id: stop at the cursor client-side
                kept = [d for d in data if int(d["id"]) > int(since)]
                reached_cursor = len(kept) < len(data)
                data = kept
            items = [post_item(d, users, ref_posts, r.received_at, refs_requested) for d in data]
            for d in data:
                newest = d["id"] if newest is None or int(d["id"]) > int(newest) else newest
            env = {"schema": INBOUND_SCHEMA_V2, "source": self._source(scope), "fetched_at": _iso(r.received_at), "items": items}
            unit = self._unit(scope, "OK", ref, body=env)
            if body.get("errors"):
                log_event("x_partial_errors", connector=scope.connector, count=len(body["errors"]),
                          types=sorted({_problem(e) for e in body["errors"] if isinstance(e, dict)})[:5])
            yielded.append(unit)
            yield unit
            token = (body.get("meta") or {}).get("next_token")
            remaining = r.headers.get("x-rate-limit-remaining")
            if not token or reached_cursor:
                break
            if page >= self.cfg.max_pages_per_scope:
                gap = (f"page cap {self.cfg.max_pages_per_scope} reached; older posts "
                       f"{'down to the cursor' if since else 'before this window'} were not read")
                yield self._unit(scope, "DEGRADED", f"{scope.connector}#since={since or 'none'}&gap", gap)
                break
            if remaining is not None and str(remaining).isdigit() and int(remaining) == 0:
                yield self._stop(con, scope, "RATE_LIMITED", f"rate limit exhausted mid-scope; resets {_iso(self._reset_at(r))}",
                                 f"{scope.connector}#since={since or 'none'}&page={page + 1}", r)
                return
        # advance the cursor only when ingest() committed every page of this scope
        if self._committed(con, yielded):
            kw = {"last_status": "OK", "last_success_at": self.clock(), "rate_limit_reset_at": None}
            if newest and (since is None or int(newest) > int(since)):
                kw["newest_id"] = str(newest)
            self._save_cursor(con, scope, **kw)
        else:
            self._save_cursor(con, scope, last_status="PARTIAL")
            log_event("x_cursor_held", connector=scope.connector, reason="not every page was committed")

    def _recheck(self, con, guard, budget, scope: Scope) -> Iterator[SourceUnit]:
        """Look stored X posts up again: present -> new OK sighting, missing -> NOT_FOUND, protected -> PROTECTED."""
        ids = [r[0] for r in con.execute(
            "SELECT i.provider_item_id FROM social_items i WHERE i.platform='x' AND i.provider_item_id GLOB '[0-9]*'"
            " AND NOT EXISTS (SELECT 1 FROM social_observations o WHERE o.item_key=i.item_key AND o.retrieval_status IN ('NOT_FOUND','DELETED'))"
            " ORDER BY COALESCE(i.first_observed_at, i.first_ingested_at) DESC LIMIT ?", (scope.max_items,))]
        if not ids:
            yield self._unit(scope, "OK", f"{scope.connector}#empty", body={"schema": INBOUND_SCHEMA_V2, "source": self._source(scope),
                                                                               "fetched_at": _iso(self.clock()), "items": []})
            return
        for b in range(0, len(ids), 100):
            chunk = ids[b:b + 100]
            ref = f"{scope.connector}#batch={b // 100 + 1}&ids={canonical_sha(chunk)[:12]}"
            p = {"ids": ",".join(chunk), self.cfg.fields_param: TWEET_FIELDS, "user.fields": USER_FIELDS}
            if self.cfg.expansions:
                p["expansions"] = self.cfg.expansions
            r, st, msg = self._call(con, guard, budget, scope, "lookup", ENDPOINTS["lookup"], p, self._worst(len(chunk)))
            if r is None:
                yield self._stop(con, scope, st, msg, ref)
                return
            if r.status != 200:
                st, msg = classify_error(r.status, r.body)
                yield self._stop(con, scope, st, msg, ref, r)
                return
            body = r.body if isinstance(r.body, dict) else {}
            inc = body.get("includes") or {}
            users = {str(u.get("id")): u for u in inc.get("users") or []}
            ref_posts = {str(t.get("id")): t for t in inc.get("tweets") or []}
            items = [post_item(d, users, ref_posts, r.received_at, True) for d in body.get("data") or []]
            seen = {i["provider_item_id"] for i in items}
            for e in body.get("errors") or []:
                rid = str(e.get("resource_id") or e.get("value") or "")
                if not rid.isdigit() or rid in seen:
                    continue
                prob = _problem(e)
                status = "PROTECTED" if "not-authorized" in prob else "NOT_FOUND"
                items.append({"event_id": f"api.{rid}.{status.lower()}.{billing_day(r.received_at)}", "provider_item_id": rid,
                              "url": f"https://x.com/i/web/status/{rid}", "fetched_at": _iso(r.received_at),
                              "retrieval_status": status, "visibility": "PUBLIC"})
                seen.add(rid)
            env = {"schema": INBOUND_SCHEMA_V2, "source": self._source(scope), "fetched_at": _iso(r.received_at), "items": items}
            yield self._unit(scope, "OK", ref, body=env)
        self._save_cursor(con, scope, last_status="OK", last_success_at=self.clock())


def store_connect(db_path: Path | str):
    import sqlite3
    from .schema import migrate
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    migrate(con)
    return con


# ---------- health ----------

def health(config_path: Path | str | None, db_path: Path | str, env: dict | None = None, now: float | None = None) -> dict:
    """Connection health without any network call. Status: credentials_missing | not_configured |
    billing_not_consented | ready (ready = configured, not yet proved by a live call unless live_evidence says so)."""
    t = time.time() if now is None else now
    token = get_token(env)
    out: dict = {"adapter": "x_api", "contract_verified": CONTRACT_VERIFIED, "token_env": TOKEN_ENV,
                 "credentials": "present" if token else "missing", "network_calls_made": 0}
    cfg = None
    if config_path and Path(config_path).exists():
        try:
            cfg = load_config(config_path)
        except Exception as e:
            out["config_error"] = redact(str(e))[:200]
    out["config"] = None if cfg is None else {
        "scopes": [s.connector for s in cfg.scopes], "allow_billable": cfg.allow_billable,
        "max_usd_per_run": cfg.max_usd_per_run, "max_usd_per_month": cfg.max_usd_per_month,
        "max_pages_per_scope": cfg.max_pages_per_scope, "prices_usd": cfg.prices}
    con = store_connect(db_path)
    try:
        month = billing_day(t)[:7]
        live = con.execute("SELECT COUNT(*), COALESCE(SUM(est_cost_usd),0), MAX(requested_at) FROM social_api_spend "
                           "WHERE mode='live' AND connector LIKE 'x_api:%'").fetchone()
        ok_live = con.execute("SELECT COUNT(*) FROM social_api_spend WHERE mode='live' AND connector LIKE 'x_api:%' AND http_status=200").fetchone()[0]
        out["live_evidence"] = {"requests": live[0], "successful": ok_live, "last_request_at": live[2],
                                "verdict": "live authorized ingest proved" if ok_live else "none: no live X API read has been made"}
        out["spend_this_month_usd"] = {"live": round(con.execute(
            "SELECT COALESCE(SUM(est_cost_usd),0) FROM social_api_spend WHERE mode='live' AND substr(billing_day,1,7)=?",
            (month,)).fetchone()[0], 4)}
        out["cursors"] = [{k: r[k] for k in ("connector", "scope", "newest_id", "last_status", "last_success_at", "rate_limit_reset_at")}
                          for r in con.execute("SELECT * FROM social_source_cursors WHERE connector LIKE 'x_api:%' ORDER BY connector")]
        for c in out["cursors"]:
            c["age_hours"] = round((t - c["last_success_at"]) / 3600, 1) if c["last_success_at"] else None
        out["connector_health"] = [dict(r) for r in con.execute(
            "SELECT h.connector, h.status, h.checked_at, h.error FROM social_connector_health h WHERE h.connector LIKE 'x_api:%'"
            " AND h.checked_at=(SELECT MAX(checked_at) FROM social_connector_health WHERE connector=h.connector) ORDER BY h.connector")]
    finally:
        con.close()
    if not token:
        out["status"] = "credentials_missing"
    elif cfg is None or not cfg.scopes:
        out["status"] = "not_configured"
    elif not cfg.allow_billable or cfg.max_usd_per_run <= 0 or cfg.max_usd_per_month <= 0:
        out["status"] = "billing_not_consented"
    else:
        out["status"] = "ready"
    out["next_step"] = {
        "credentials_missing": f"authorize: see docs/social-intelligence/X_API_03.md, then export {TOKEN_ENV} in the shell that runs memelab",
        "not_configured": "write the scope config (docs/social-intelligence/x_api.example.json) to data/private/x_api.json",
        "billing_not_consented": "set budget.allow_billable true with non-zero max_usd_per_run and max_usd_per_month (Elving's decision)",
        "ready": "run one small live ingest (one scope, max_pages_per_scope 1) and check `social x-health` live_evidence",
    }[out["status"]]
    return out
