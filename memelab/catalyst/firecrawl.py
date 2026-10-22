"""Firecrawl adapter for Catalyst Intelligence: read the article behind a catalyst event, a fallback route for
navigate-mode sources, and a news search that finds other publishers of the same story.

Contract read 2026-10-22 from the Firecrawl source (github.com/firecrawl/firecrawl at 5442955, apps/api/src) and
docs.firecrawl.dev/billing (docs/catalyst/FIRECRAWL.md has the details and the gaps):

  POST {base}/v2/scrape   {url, formats, onlyMainContent, maxAge, timeout, proxy, parsers, storeInCache, ...}
                          -> {success, data: {markdown, links, rawHtml, metadata: {statusCode, url, sourceURL, title,
                              language, publishedTime, modifiedTime, cacheState, proxyUsed, creditsUsed, ...}}}
                          1 credit per returned document, also when the page itself answered 403 or 404; 0 when no
                          document comes back; +1 per extra PDF page unless parsers=[]; +1 with zeroDataRetention;
                          x.com / twitter.com pages cost 30 (refused here anyway).
  POST {base}/v2/search   {query, limit, sources, tbs, lang, timeout}
                          -> {success, data: {web: [...], news: [{title, url, snippet, date, position}]}, creditsUsed}
                          2 credits per 10 results, rounded up per 10. No scrapeOptions are sent, so no page is scraped.
  GET  {base}/v2/team/credit-usage   -> {success, data: {remainingCredits, planCredits, billingPeriodStart, ...}}
  Errors: 401 bad key, 402 credits used up (free plan: no pay-as-you-go, 402 until the next cycle), 429 rate limit
  (free plan: 10 scrape or search requests per minute), 403 blocked URL or option, 408 timeout, 5xx.
  Firecrawl does not check robots.txt on a single scrape unless the team has that flag, so the lab checks it itself
  (RFC 9309: 4xx = no rules, 5xx / unreachable = disallow everything) for the FirecrawlAgent user agent.

Rules (FIRECRAWL.md "Decisions"):
  - The page text never reaches the public database, the inbox or state/. What is kept: a hash of the text, a word
    count, the page's own times, the HTTP statuses, and identifiers found on the page (contract addresses, tickers,
    the domains it links to). A private copy can be kept in the gitignored private store for a few days.
  - Platforms the lab reads only through their official APIs or not at all are refused before any call
    (X, Reddit, Discord, YouTube, Telegram, Farcaster clients, TikTok, Instagram, Facebook, Threads, LinkedIn).
  - Proxies: "basic" by default. "auto" lets Firecrawl escalate to its anti-bot proxies and is Elving's decision.
    Geo-blocked sources (four.meme, Bybit) are not routed around.
  - Credits are capped per run and per month before every call; a call whose worst case does not fit is not made.
    A cost per credit above zero needs allow_billable (same rule as the X API and the LLM, D-023, D-036).
  - Page text is evidence. It is never executed, never sent to a model, and only regular expressions read it.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .. import db
from ..social.api_common import HttpResponse, billing_day
from ..social.identity import extract_mentions
from ..social.ingest import TransientError, redact
from .ingest import OFFICIAL_DOMAINS, canonical_url, domain_of, strip_publisher, to_epoch

PROVIDER = "firecrawl"
KEY_ENV = "FIRECRAWL_API_KEY"
CONFIG_ENV = "MEMELAB_FIRECRAWL_CONFIG"
CONFIG_SCHEMA = "memelab.catalyst.firecrawl.config/1"
FIXTURE_SCHEMA = "memelab.catalyst.firecrawl.fixture/1"
CONTRACT_VERIFIED = "2026-10-22"
CLOUD_BASE = "https://api.firecrawl.dev"
ENDPOINTS = {"scrape": "/v2/scrape", "search": "/v2/search", "credit_usage": "/v2/team/credit-usage"}
ROBOTS_AGENT = "FirecrawlAgent"           # the token Firecrawl's own robots checker matches (lib/robots-txt.ts)
SEARCH_SOURCE_ID = "web:firecrawl:search"
KEY_RX = re.compile(r"\bfc-[0-9a-fA-F]{32}\b")
LOOPBACK = {"localhost", "127.0.0.1", "::1"}
FORBIDDEN_CONFIG_KEYS = {"key", "api_key", "apikey", "firecrawl_api_key", "token", "secret", "password", "authorization",
                         "bearer", "headers", "cookie", "cookies", "actions", "location", "profile"}
MAX_FACTS = {"CONTRACT": 20, "ADDRESS_LINK": 20, "TICKER": 30, "CITED_DOMAIN": 60}
STOP_STATUSES = {"UNAUTHORIZED", "PAYMENT_REQUIRED", "RATE_LIMITED", "BAD_REQUEST"}

_SAME = "official API route only, decided per platform"
REFUSED_HOSTS = {
    "x.com": "X: non-API automation is prohibited by X's Developer Guidelines (D-025); Firecrawl also bills 30 credits per X page",
    "twitter.com": "X: non-API automation is prohibited by X's Developer Guidelines (D-025)",
    "reddit.com": "Reddit: only through the approved Data API (D-127)",
    "redd.it": "Reddit: only through the approved Data API (D-127)",
    "discord.com": "Discord: only through a bot a consenting server installed (D-133)",
    "discord.gg": "Discord: an invite grants no collection rights (D-133)",
    "youtube.com": "YouTube: Data API only; scraping is prohibited by its Developer Policies (D-142)",
    "youtu.be": "YouTube: Data API only (D-142)",
    "t.me": "Telegram: channel scraping is restricted by Telegram's terms (D-028, open)",
    "telegram.me": "Telegram: channel scraping is restricted (D-028, open)",
    "telegram.org": "Telegram: channel scraping is restricted (D-028, open)",
    "warpcast.com": "Farcaster: read through a node, not a client website (D-129)",
    "farcaster.xyz": "Farcaster: read through a node, not a client website (D-129)",
    "tiktok.com": "TikTok: no public read route; not collected",
    "instagram.com": "Instagram: login wall; not collected",
    "facebook.com": "Facebook: login wall; not collected",
    "threads.net": "Threads: login wall; not collected",
    "threads.com": "Threads: login wall; not collected",
    "linkedin.com": "LinkedIn: login wall; not collected",
}

DEFAULTS: dict[str, Any] = {
    "schema": CONFIG_SCHEMA,
    "enabled": False,
    "billing": "cloud",                                  # cloud | self_hosted
    "base_url": CLOUD_BASE,
    "budget": {"max_credits_per_run": 0, "max_credits_per_month": 0, "max_requests_per_run": 40,
               "usd_per_credit": 0.0, "allow_billable": False, "min_interval_seconds": 6.5,
               "check_remote_balance": True, "min_remaining_credits": 0},
    "scrape": {"proxy": "basic", "max_age_ms": 3_600_000, "timeout_ms": 45_000, "only_main_content": True,
               "store_in_cache": True, "zero_data_retention": False},
    "enrich": {"tiers": ["official", "reputable", "aggregator"], "source_groups": ["news"],
               "roles": ["ORIGINAL", "INDEPENDENT"], "max_pages_per_run": 15, "event_window_hours": 72,
               "retry_failed_after_hours": 24, "relevance": "memecoin"},
    "search": {"enabled": False, "max_queries_per_run": 3, "limit": 10, "tbs_query": "qdr:d", "tbs_events": "qdr:w",
               "lang": "en", "max_event_sources": 2},
    "pull_fallback": {"sources": []},
    "private_copy_days": 7,
}


class ConfigError(ValueError):
    pass


class FixtureMiss(Exception):
    """A request the recorded fixture does not contain: the contract changed or the test is wrong. Not transient."""


def config_path() -> Path:
    env = os.environ.get(CONFIG_ENV)
    return Path(env) if env else db.DATA_DIR / "private" / "firecrawl.json"


def _forbidden(obj: Any, where: str = "") -> list[str]:
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            loc = f"{where}.{k}" if where else str(k)
            if str(k).lower() in FORBIDDEN_CONFIG_KEYS:
                out.append(loc)
            out += _forbidden(v, loc)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += _forbidden(v, f"{where}[{i}]")
    return out


def _merge(defaults: dict, given: dict, where: str = "") -> dict:
    out = {}
    for k in given:
        if k not in defaults:
            raise ConfigError(f"unknown config key {where + k}")
    for k, dv in defaults.items():
        gv = given.get(k, dv)
        if isinstance(dv, dict):
            if not isinstance(gv, dict):
                raise ConfigError(f"{where + k} must be an object")
            out[k] = _merge(dv, gv, f"{where}{k}.")
        else:
            out[k] = gv
    return out


def _int(v: Any, name: str, lo: int, hi: int) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
        raise ConfigError(f"{name} must be an integer from {lo} to {hi}")
    return v


def validate_config(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raise ConfigError("config must be a JSON object")
    bad = _forbidden(raw)
    if bad:
        raise ConfigError(f"config holds a refused key ({', '.join(bad)}): the API key comes only from {KEY_ENV}; "
                          "custom headers, cookies, browser actions, profiles and location overrides are not used")
    if raw.get("schema") != CONFIG_SCHEMA:
        raise ConfigError(f"schema must be {CONFIG_SCHEMA}")
    cfg = _merge(DEFAULTS, raw)
    if not isinstance(cfg["enabled"], bool):
        raise ConfigError("enabled must be true or false")
    if cfg["billing"] not in ("cloud", "self_hosted"):
        raise ConfigError("billing must be cloud or self_hosted")
    u = urllib.parse.urlparse(str(cfg["base_url"]).rstrip("/"))
    if u.username or u.password or u.query or u.fragment or u.path not in ("", "/"):
        raise ConfigError("base_url must be scheme://host[:port] with nothing else")
    if cfg["billing"] == "cloud":
        if f"{u.scheme}://{u.netloc}" != CLOUD_BASE:
            raise ConfigError(f"billing cloud uses {CLOUD_BASE}; a self-hosted server needs billing self_hosted")
    elif not (u.scheme == "https" or (u.scheme == "http" and (u.hostname or "") in LOOPBACK)):
        raise ConfigError("a self-hosted server must use https, or http on this machine only (localhost)")
    cfg["base_url"] = f"{u.scheme}://{u.netloc}"
    b = cfg["budget"]
    _int(b["max_credits_per_run"], "budget.max_credits_per_run", 0, 10_000)
    _int(b["max_credits_per_month"], "budget.max_credits_per_month", 0, 1_000_000)
    _int(b["max_requests_per_run"], "budget.max_requests_per_run", 0, 500)
    if isinstance(b["usd_per_credit"], bool) or not isinstance(b["usd_per_credit"], (int, float)) or b["usd_per_credit"] < 0:
        raise ConfigError("budget.usd_per_credit must be a number >= 0")
    if not isinstance(b["allow_billable"], bool):
        raise ConfigError("budget.allow_billable must be true or false")
    if isinstance(b["min_interval_seconds"], bool) or not isinstance(b["min_interval_seconds"], (int, float)) or not 0 <= b["min_interval_seconds"] <= 120:
        raise ConfigError("budget.min_interval_seconds must be from 0 to 120")
    if not isinstance(b["check_remote_balance"], bool):
        raise ConfigError("budget.check_remote_balance must be true or false")
    _int(b["min_remaining_credits"], "budget.min_remaining_credits", 0, 1_000_000)
    s = cfg["scrape"]
    if s["proxy"] not in ("basic", "auto"):
        raise ConfigError("scrape.proxy must be basic or auto (stealth and enhanced proxies are not configured here; "
                          "auto already lets Firecrawl escalate and needs Elving's decision)")
    _int(s["max_age_ms"], "scrape.max_age_ms", 0, 7 * 86_400_000)
    _int(s["timeout_ms"], "scrape.timeout_ms", 5_000, 120_000)
    for k in ("only_main_content", "store_in_cache", "zero_data_retention"):
        if not isinstance(s[k], bool):
            raise ConfigError(f"scrape.{k} must be true or false")
    e = cfg["enrich"]
    if not set(e["tiers"]) <= {"official", "reputable", "aggregator"} or not e["tiers"]:
        raise ConfigError("enrich.tiers must be a non-empty subset of official, reputable, aggregator")
    if not set(e["source_groups"]) <= {"news", "scheduled", "market"} or not e["source_groups"]:
        raise ConfigError("enrich.source_groups must be a non-empty subset of news, scheduled, market")
    if not set(e["roles"]) <= {"ORIGINAL", "INDEPENDENT", "SYNDICATED", "CIRCULAR", "COMMENTARY"} or not e["roles"]:
        raise ConfigError("enrich.roles must be a non-empty subset of the catalyst_event_sources roles")
    _int(e["max_pages_per_run"], "enrich.max_pages_per_run", 0, 200)
    _int(e["event_window_hours"], "enrich.event_window_hours", 1, 24 * 30)
    _int(e["retry_failed_after_hours"], "enrich.retry_failed_after_hours", 1, 24 * 30)
    if e["relevance"] not in ("memecoin", "all"):
        raise ConfigError("enrich.relevance must be memecoin or all")
    q = cfg["search"]
    if not isinstance(q["enabled"], bool):
        raise ConfigError("search.enabled must be true or false")
    _int(q["max_queries_per_run"], "search.max_queries_per_run", 0, 20)
    _int(q["limit"], "search.limit", 1, 20)
    _int(q["max_event_sources"], "search.max_event_sources", 1, 20)
    for k in ("tbs_query", "tbs_events"):
        if q[k] not in ("qdr:h", "qdr:d", "qdr:w", "qdr:m"):
            raise ConfigError(f"search.{k} must be qdr:h, qdr:d, qdr:w or qdr:m")
    if not isinstance(q["lang"], str) or not re.fullmatch(r"[a-z]{2}", q["lang"]):
        raise ConfigError("search.lang must be a two-letter language code")
    pf = cfg["pull_fallback"]["sources"]
    if not isinstance(pf, list) or not all(isinstance(x, str) and x for x in pf):
        raise ConfigError("pull_fallback.sources must be a list of catalyst source ids")
    _int(cfg["private_copy_days"], "private_copy_days", 0, 30)
    return cfg


def load_config(path: Path | str | None = None) -> tuple[dict | None, Path, str | None]:
    """(config, path, error). A missing file is (None, path, None): Firecrawl is simply not set up."""
    p = Path(path) if path else config_path()
    if not p.exists():
        return None, p, None
    try:
        return validate_config(json.loads(p.read_text())), p, None
    except (ConfigError, ValueError) as e:
        return None, p, str(e)


def api_key() -> str | None:
    v = os.environ.get(KEY_ENV, "").strip()
    return v or None


def readiness(cfg: dict | None, key: str | None, error: str | None = None) -> tuple[str, str]:
    """Why a live run can or cannot happen. Only 'ready' allows a live request."""
    if error:
        return "config_invalid", error
    if cfg is None:
        return "config_missing", f"no config file; copy docs/catalyst/firecrawl.example.json to {config_path()}"
    if not cfg["enabled"]:
        return "disabled", "config has enabled: false"
    b = cfg["budget"]
    if cfg["billing"] == "cloud":
        if not key:
            return "credentials_missing", f"set {KEY_ENV} in the environment (never in a file that is committed)"
        if b["max_credits_per_run"] <= 0 or b["max_credits_per_month"] <= 0:
            return "caps_zero", "budget.max_credits_per_run and budget.max_credits_per_month must both be above 0"
        if b["usd_per_credit"] > 0 and not b["allow_billable"]:
            return "billing_not_consented", "usd_per_credit is above 0 but budget.allow_billable is false"
    if b["max_requests_per_run"] <= 0:
        return "caps_zero", "budget.max_requests_per_run must be above 0"
    return "ready", "live requests allowed within the caps"


def refused_reason(url: str | None) -> str | None:
    try:
        u = urllib.parse.urlparse(url or "")
    except ValueError:
        return "unparseable URL"
    if u.scheme not in ("http", "https") or not u.hostname:
        return "not an http(s) URL"
    if u.username or u.password:
        return "URL carries credentials"
    host = u.hostname.lower().rstrip(".")
    for h, why in REFUSED_HOSTS.items():
        if host == h or host.endswith("." + h):
            return why
    return None


def safe_page_url(url: str | None) -> str | None:
    """scheme://host/path only: no credentials, query or fragment (a final URL can carry session or tracking tokens)."""
    try:
        u = urllib.parse.urlparse(url or "")
    except ValueError:
        return None
    if u.scheme not in ("http", "https") or not u.hostname:
        return None
    port = f":{u.port}" if u.port and u.port not in (80, 443) else ""
    return f"{u.scheme}://{u.hostname.lower()}{port}{u.path or '/'}"[:500]


def scrub(s: Any, *secrets: str | None) -> str:
    s = str(s)
    for x in secrets:
        if x:
            s = s.replace(x, "[REDACTED]")
    return KEY_RX.sub("[REDACTED]", redact(s))[:200]


# ---------- transports ----------

class RestTransport:
    """JSON over HTTPS with urllib (the sandbox proxy is honoured through the environment). The key is sent as a Bearer
    header and is never put in a URL."""

    def __init__(self, base_url: str, key: str | None, timeout_s: float):
        self.base, self.key, self.timeout = base_url.rstrip("/"), key, timeout_s

    def request(self, method: str, path: str, body: dict | None = None) -> HttpResponse:
        headers = {"Accept": "application/json", "User-Agent": "memelab-catalyst/1"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                status, raw, hdrs = r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            status, raw, hdrs = e.code, e.read() or b"", dict(e.headers or {})
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise TransientError(scrub(e, self.key)) from None
        try:
            parsed = json.loads(raw.decode("utf-8", "replace")) if raw else {}
        except ValueError:
            parsed = {"_non_json": True}
        return HttpResponse(status, {k.lower(): str(v) for k, v in hdrs.items()}, parsed, time.time())


class FixtureTransport:
    """Recorded synthetic exchanges. A request matches when method and path are equal and every key in the exchange's
    'match' equals the request body's value; each exchange is served once, in order. 'raise' simulates a transport
    error ('{secret}' is replaced with the key the caller holds, to prove redaction). Robots answers come from
    'robots': {host: text | {"status": n}}; a host not listed is unreachable."""

    def __init__(self, fixture: dict | str | Path, secret: str | None = None):
        if not isinstance(fixture, dict):
            fixture = json.loads(Path(fixture).read_text())
        if fixture.get("schema") != FIXTURE_SCHEMA:
            raise ValueError(f"fixture schema must be {FIXTURE_SCHEMA}")
        self.exchanges = fixture.get("exchanges") or []
        self.robots_map = fixture.get("robots") or {}
        self.secret = secret
        self.used: set[int] = set()
        self.calls: list[dict] = []
        self.robots_calls: list[str] = []

    def request(self, method: str, path: str, body: dict | None = None) -> HttpResponse:
        body = body or {}
        self.calls.append({"method": method, "path": path, "url": body.get("url"), "query": body.get("query"),
                           "body": json.loads(json.dumps(body))})
        for i, ex in enumerate(self.exchanges):
            rq = ex["request"]
            if i in self.used or rq.get("method", "POST") != method or rq["path"] != path:
                continue
            if any(body.get(k) != v for k, v in (rq.get("match") or {}).items()):
                continue
            self.used.add(i)
            if "raise" in ex:
                raise TransientError(ex["raise"].replace("{secret}", self.secret or ""))
            rs = ex["response"]
            return HttpResponse(int(rs["status"]), {k.lower(): str(v) for k, v in (rs.get("headers") or {}).items()},
                                rs.get("body"), to_epoch(ex.get("recorded_at")) or 0.0)
        raise FixtureMiss(f"no recorded exchange for {method} {path} url={body.get('url')!r} query={body.get('query')!r}")

    def robots(self, robots_url: str) -> tuple[int | None, str]:
        self.robots_calls.append(robots_url)
        host = (urllib.parse.urlparse(robots_url).hostname or "").lower()
        v = self.robots_map.get(host)
        if v is None:
            return None, ""
        if isinstance(v, dict):
            return int(v.get("status", 200)), v.get("text", "")
        return 200, str(v)


def live_robots_fetch(robots_url: str, timeout_s: float = 10.0) -> tuple[int | None, str]:
    """(HTTP status, text) of a robots.txt, read directly from this machine; (None, '') when unreachable."""
    req = urllib.request.Request(robots_url, headers={"User-Agent": "Mozilla/5.0 (compatible; memelab-catalyst robots check)",
                                                      "Accept": "text/plain,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as r:
            return r.status, r.read(512_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None, ""


class Robots:
    """robots.txt per origin, cached for the run, read with RFC 9309 semantics: 2xx parse the rules; 4xx (other than
    429) means no rules apply; 429, 5xx or no answer means disallow everything until it can be read."""

    def __init__(self, fetch: Callable[[str], tuple[int | None, str]]):
        self.fetch = fetch
        self.cache: dict[str, tuple[str, urllib.robotparser.RobotFileParser | None]] = {}

    def check(self, url: str) -> tuple[bool, str]:
        u = urllib.parse.urlparse(url)
        origin = f"{u.scheme}://{u.netloc}"
        if origin not in self.cache:
            status, text = self.fetch(origin + "/robots.txt")
            if status is None or status == 429 or status >= 500:
                self.cache[origin] = ("UNREACHABLE", None)
            elif 400 <= status < 500:
                self.cache[origin] = ("UNAVAILABLE", None)
            elif 200 <= status < 300:
                rp = urllib.robotparser.RobotFileParser()
                rp.parse(text.splitlines())
                self.cache[origin] = ("RULES", rp)
            else:
                self.cache[origin] = ("UNREACHABLE", None)
        kind, rp = self.cache[origin]
        if kind == "UNREACHABLE":
            return False, "ROBOTS_UNREACHABLE"
        if kind == "UNAVAILABLE":
            return True, "ROBOTS_NONE"
        ok = rp.can_fetch(ROBOTS_AGENT, url)
        return ok, ("ROBOTS_ALLOWED" if ok else "ROBOTS_DISALLOWED")


# ---------- credits and the spend ledger ----------

def scrape_credit_estimate(cfg: dict) -> int:
    if cfg["billing"] == "self_hosted":
        return 0
    return 1 + (1 if cfg["scrape"]["zero_data_retention"] else 0)


def search_credit_estimate(cfg: dict, limit: int) -> int:
    return 0 if cfg["billing"] == "self_hosted" else 2 * math.ceil(limit / 10)


def month_credits(con, mode: str, now: float) -> int:
    """Credits recorded in social_api_spend for connector firecrawl in the UTC calendar month of `now`. Firecrawl's own
    cycle starts on the renewal date, so this is a conservative stand-in, not the bill."""
    prefix = billing_day(now)[:8]
    total = 0
    for (rj,) in con.execute("SELECT resources_json FROM social_api_spend WHERE connector=? AND mode=? AND billing_day LIKE ?",
                             (PROVIDER, mode, prefix + "%")):
        try:
            total += int((json.loads(rj or "{}") or {}).get("credits") or 0)
        except (ValueError, TypeError):
            continue
    return total


@dataclass
class Session:
    """One run: transport, caps, ledger rows, pacing. Every request is checked against the caps first and recorded
    after, success or not."""
    con: Any
    cfg: dict
    transport: Any
    mode: str
    run_id: str
    clock: Callable[[], float]
    sleep: Callable[[float], None] = time.sleep
    secret: str | None = None
    requests: int = 0
    run_credits: int = 0
    stopped: str | None = None
    remote_remaining: int | None = None      # plan credits left as Firecrawl reports them, minus the configured reserve
    _month: int | None = None
    _last_call: float | None = None
    _preflighted: bool = False
    log: list = field(default_factory=list)

    def month_used(self) -> int:
        if self._month is None:
            self._month = month_credits(self.con, self.mode, self.clock())
        return self._month

    def cap_reason(self, estimate: int) -> str | None:
        b = self.cfg["budget"]
        if self.requests >= b["max_requests_per_run"]:
            return f"REQUEST_CAP: {b['max_requests_per_run']} requests per run"
        if self.cfg["billing"] == "cloud":
            if self.run_credits + estimate > b["max_credits_per_run"]:
                return f"RUN_CREDIT_CAP: {self.run_credits} of {b['max_credits_per_run']} credits used this run"
            if self.month_used() + self.run_credits + estimate > b["max_credits_per_month"]:
                return f"MONTH_CREDIT_CAP: {self.month_used() + self.run_credits} of {b['max_credits_per_month']} credits used this month"
            if self.remote_remaining is not None and self.run_credits + estimate > self.remote_remaining:
                return f"REMOTE_BALANCE: Firecrawl reports too few plan credits left (reserve {b['min_remaining_credits']})"
        return None

    def preflight(self) -> None:
        """Once per run, before the first billable call: ask Firecrawl how many plan credits are left (free call). The
        local ledger only knows what this lab recorded; the account may be used elsewhere, and a scheduled session that
        lost its ledger would otherwise trust a reset month. If the answer is unusable the local caps still apply."""
        self._preflighted = True
        b = self.cfg["budget"]
        if self.cfg["billing"] != "cloud" or not b["check_remote_balance"]:
            return
        resp, outcome, _ = self.call("credit_usage", None, 0, method="GET", credits_of=lambda r: 0)
        if outcome == "OK":
            left = ((resp.body or {}).get("data") or {}).get("remainingCredits")
            if isinstance(left, (int, float)) and not isinstance(left, bool):
                self.remote_remaining = max(0, int(left) - int(b["min_remaining_credits"]))

    def _pace(self) -> None:
        gap = float(self.cfg["budget"]["min_interval_seconds"])
        if self._last_call is not None and gap > 0 and self.mode == "live":
            wait = self._last_call + gap - time.time()
            if wait > 0:
                self.sleep(wait)

    def record(self, endpoint: str, status: int | None, credits: int, resources: dict) -> None:
        now = self.clock()
        cost = round(credits * float(self.cfg["budget"]["usd_per_credit"]), 6)
        self.con.execute("INSERT INTO social_api_spend(connector,run_id,endpoint,http_status,billing_day,resources_json,est_cost_usd,"
                         "mode,requested_at) VALUES (?,?,?,?,?,?,?,?,?)",
                         (PROVIDER, self.run_id, endpoint, status, billing_day(now),
                          json.dumps({"credits": credits, "seq": self.requests, **resources}, sort_keys=True),   # seq keeps rows distinct in the state export
                          cost, self.mode, now))
        self.con.commit()
        self.requests += 1
        self.run_credits += credits

    def call(self, name: str, body: dict | None, estimate: int, *, method: str = "POST",
             credits_of: Callable[[HttpResponse], int] | None = None) -> tuple[HttpResponse | None, str, str | None]:
        """Returns (response or None, outcome, error). Outcome is OK or a provider status; a status in STOP_STATUSES
        also sets self.stopped so the caller ends the run. 5xx and transport errors are retried once."""
        path = ENDPOINTS[name]
        if not self._preflighted and name != "credit_usage":
            self.preflight()
            if self.stopped:
                return None, "BUDGET", self.stopped
        last_err = None
        for attempt in range(2):
            reason = self.cap_reason(estimate)
            if reason:
                self.stopped = reason
                return None, "BUDGET", reason
            self._pace()
            try:
                resp = self.transport.request(method, path, body)
            except TransientError as e:
                self._last_call = time.time()
                last_err = scrub(e, self.secret)
                self.record(path, None, 0, {"outcome": "TRANSPORT_ERROR"})
                if attempt == 0:
                    self.sleep(1.0 if self.mode == "live" else 0)
                    continue
                return None, "TRANSPORT_ERROR", last_err
            self._last_call = time.time()
            st = resp.status
            ok_body = isinstance(resp.body, dict) and resp.body.get("success") is True
            credits = 0
            if st == 200 and ok_body:
                credits = credits_of(resp) if credits_of else 0
            outcome = classify(st, ok_body)
            self.record(path, st, credits, {"outcome": outcome})
            if outcome == "PROVIDER_ERROR" and st >= 500 and attempt == 0:
                self.sleep(2.0 if self.mode == "live" else 0)
                continue
            err = None
            if outcome != "OK":
                b = resp.body if isinstance(resp.body, dict) else {}
                err = scrub(f"HTTP {st}: {b.get('code') or ''} {b.get('error') or ''}".strip(), self.secret)
            if outcome in STOP_STATUSES:
                self.stopped = f"{outcome}: {err}"
            return resp, outcome, err
        return None, "TRANSPORT_ERROR", last_err


def classify(status: int, ok_body: bool) -> str:
    if status == 200 and ok_body:
        return "OK"
    return {401: "UNAUTHORIZED", 402: "PAYMENT_REQUIRED", 429: "RATE_LIMITED", 400: "BAD_REQUEST",
            403: "PROVIDER_REFUSED", 408: "PROVIDER_TIMEOUT"}.get(status, "PROVIDER_ERROR")


# ---------- page facts ----------

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def is_solana_pubkey(s: str) -> bool:
    """True when s decodes from base58 to exactly 32 bytes (a public key or mint); rejects look-alike words."""
    if not 32 <= len(s) <= 44 or any(c not in _B58 for c in s):
        return False
    n = 0
    for c in s:
        n = n * 58 + _B58.index(c)
    lead = len(s) - len(s.lstrip("1"))
    return lead + (n.bit_length() + 7) // 8 == 32


def page_facts(markdown: str, links: list[str], own_domain: str | None) -> list[tuple[str, str, str | None]]:
    """Identifiers on a page: contract addresses, address-bearing explorer or DEX links, cashtags, linked domains.
    Regular expressions only; the wording is never kept."""
    out: list[tuple[str, str, str | None]] = []
    counts: dict[str, int] = {}

    def add(kind: str, value: str, hint: str | None) -> None:
        if counts.get(kind, 0) < MAX_FACTS[kind] and (kind, value) not in {(k, v) for k, v, _ in out}:
            out.append((kind, value, hint))
            counts[kind] = counts.get(kind, 0) + 1

    for m in extract_mentions(markdown or "", urls=links or []):
        if m["kind"] == "CONTRACT":
            a = m["address"]
            if a.startswith("0x"):
                if re.fullmatch(r"0x[0-9a-fA-F]{40}", a):
                    add("CONTRACT", a.lower(), "evm")
            elif is_solana_pubkey(a):
                add("CONTRACT", a, "solana")
        elif m["kind"] == "LINK":
            a = m.get("address") or ""
            if a.startswith("0x") and re.fullmatch(r"0x[0-9a-fA-F]{40}", a):
                add("ADDRESS_LINK", a.lower(), m.get("link_chain") or "evm")
            elif is_solana_pubkey(a):
                add("ADDRESS_LINK", a, m.get("link_chain") or "solana")
        elif m["kind"] == "TICKER" and re.fullmatch(r"[A-Z][A-Z0-9]{0,9}", m["value"]):
            add("TICKER", m["value"], None)
    own = (own_domain or "").lower()
    for link in links or []:
        d = domain_of(link) if isinstance(link, str) else None
        if not d or d == own or d.endswith("." + own) or (own and own.endswith("." + d)):
            continue
        if re.fullmatch(r"[a-z0-9.\-]{1,253}", d):
            add("CITED_DOMAIN", d, None)
    return out


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _page_time(v: Any, now: float) -> float | None:
    """A page's own published or modified time. A date-time without a zone (Decrypt publishes "2026-10-22T16:31:07",
    first live run) is ambiguous and stays UNKNOWN rather than being read in this machine's zone (same rule as D-019)."""
    if isinstance(v, str):
        s = v.strip().replace("Z", "+00:00")
        try:
            if datetime.fromisoformat(s).tzinfo is None:
                return None
        except ValueError:
            pass                                   # not ISO 8601: an RFC 2822 date carries its own offset
    t = to_epoch(v) if v else None
    if t is None or t < 1_230_768_000 or t > now + 86_400:     # before 2009 or more than a day ahead: not believable
        return None
    return t


# ---------- enrichment ----------

def url_key(url: str | None) -> str:
    return (canonical_url(url) or url or "")[:500]


def _origin(url: str | None) -> str:
    u = urllib.parse.urlparse(url or "")
    return f"{u.scheme}://{(u.netloc or '').lower()}"


# Which events are worth credits. On the first live run (2026-10-22) about 9 of 109 readable publisher articles were
# about memecoins, listings or launches; the rest were macro, AI and regulation stories that cannot produce a token link.
# HEURISTIC: it only decides which pages are read (and searched), never a grade or a score. enrich.relevance "all" turns it off.
RELEVANCE_RX = re.compile(
    r"\$[A-Za-z][A-Za-z0-9]{1,9}\b|\([A-Z][A-Z0-9]{1,9}\)|\b(meme ?coins?|memes?|pump\.?fun|launchpads?|letsbonk|bonk|pepe|doge\w*|"
    r"shib\w*|dogwifhat|wif|airdrops?|lists|listing|listed|delist\w*|token launch|new token|solana|four\.meme|zora|clanker|"
    r"virtuals|raydium|jupiter|dex ?screener|presale|rug ?pull|honeypot)\b", re.I)


def relevant(category: str | None, title: str | None, description: str | None) -> bool:
    """Category alone is not enough: the catalyst classifier files spot ETF flow stories as ACCESS. A real listing names
    the asset "(TICKER)" or says list/listing, which the pattern catches."""
    return bool(RELEVANCE_RX.search(f"{title or ''} {description or ''}"))


def _prior_fetches(con, mode: str, purpose: str) -> tuple[dict[str, dict], dict[str, float]]:
    """Latest read per URL (an OK read wins over a later failure: a page read once stays read), and the latest robots
    refusal per origin, so one refusal covers every other article on that site until the retry wait has passed."""
    out: dict[str, dict] = {}
    robots: dict[str, float] = {}
    for r in con.execute("SELECT url_key, requested_url, status, fetched_at FROM catalyst_page_fetches WHERE access_mode=? AND purpose=? "
                         "ORDER BY fetched_at", (mode, purpose)):
        prev = out.get(r["url_key"])
        if prev is None or prev["status"] != "OK":
            out[r["url_key"]] = dict(r)
        if r["status"] in ("ROBOTS_DISALLOWED", "ROBOTS_UNREACHABLE"):
            robots[_origin(r["requested_url"])] = r["fetched_at"]
    return out, robots


def select_targets(con, cfg: dict, now: float, *, mode: str, limit: int | None = None,
                   event_ids: list[int] | None = None) -> tuple[list[dict], dict]:
    """Items of live events worth reading, newest events first, official and reputable before aggregators, the original
    before independent coverage. Copies (SYNDICATED, CIRCULAR) are skipped by default: they repeat what is read."""
    e = cfg["enrich"]
    q = ("SELECT i.id AS item_id, i.url, i.source_id, s.tier, es.role, ev.id AS event_id, ev.category, ev.title, ev.description, "
         "COALESCE(ev.published_at, ev.discovered_at) AS ref FROM catalyst_events ev "
         "JOIN catalyst_event_sources es ON es.event_id=ev.id JOIN catalyst_items i ON i.id=es.item_id "
         "JOIN catalyst_sources s ON s.source_id=i.source_id "
         "WHERE ev.status IN ('NEW','RESEARCH','TRACKED','EVENT_ONLY') AND (ev.expires_at IS NULL OR ev.expires_at > ?) "
         f"AND es.role IN ({','.join('?' * len(e['roles']))}) AND s.tier IN ({','.join('?' * len(e['tiers']))}) "
         f"AND s.source_group IN ({','.join('?' * len(e['source_groups']))}) AND i.url LIKE 'http%'")
    args: list[Any] = [now, *e["roles"], *e["tiers"], *e["source_groups"]]
    if event_ids:
        q += f" AND ev.id IN ({','.join('?' * len(event_ids))})"
        args += list(event_ids)
    else:
        q += " AND ev.discovered_at >= ?"
        args.append(now - e["event_window_hours"] * 3600)
    rows = [dict(r) for r in con.execute(q, args)]
    tier_rank = {"official": 0, "reputable": 1, "aggregator": 2}
    rows.sort(key=lambda r: (-(r["ref"] or 0), r["event_id"], tier_rank.get(r["tier"], 3), r["role"] != "ORIGINAL", r["item_id"]))
    prior, robots_refused = _prior_fetches(con, mode, "ENRICH")
    wait = e["retry_failed_after_hours"] * 3600
    skip = {"already_read": 0, "recent_failure": 0, "duplicate_url": 0, "site_refused_robots": 0, "not_relevant": 0}
    seen: set[str] = set()
    out = []
    cap = e["max_pages_per_run"] if limit is None else min(limit, e["max_pages_per_run"])
    for r in rows:
        if e["relevance"] == "memecoin" and not event_ids and not relevant(r["category"], r["title"], r["description"]):
            skip["not_relevant"] += 1
            continue
        cu = url_key(r["url"])
        if cu in seen:
            skip["duplicate_url"] += 1
            continue
        seen.add(cu)
        p = prior.get(cu)
        if p and p["status"] == "OK":
            skip["already_read"] += 1
            continue
        if p and now - p["fetched_at"] < wait:
            skip["recent_failure"] += 1
            continue
        if now - robots_refused.get(_origin(r["url"]), -1e18) < wait:
            skip["site_refused_robots"] += 1
            continue
        out.append(r)
        if len(out) >= cap:
            break
    return out, skip


def _insert_fetch(con, row: dict) -> int:
    return db.insert(con, "catalyst_page_fetches", {**row, "url_key": url_key(row["requested_url"])})


def scrape_body(cfg: dict, url: str, purpose: str) -> dict:
    s = cfg["scrape"]
    body = {"url": url, "formats": ["markdown", "links"] if purpose == "ENRICH" else ["rawHtml"],
            "onlyMainContent": bool(s["only_main_content"]) if purpose == "ENRICH" else False,
            "maxAge": s["max_age_ms"], "timeout": s["timeout_ms"], "proxy": s["proxy"], "parsers": [],
            "blockAds": True, "removeBase64Images": True, "storeInCache": bool(s["store_in_cache"])}
    if s["zero_data_retention"]:
        body["zeroDataRetention"] = True
    return body


def _scrape_credits(resp: HttpResponse, estimate: int) -> int:
    data = (resp.body or {}).get("data") if isinstance(resp.body, dict) else None
    meta = (data or {}).get("metadata") or {}
    cu = meta.get("creditsUsed")
    if isinstance(cu, int) and not isinstance(cu, bool) and cu >= 0:
        return cu
    return estimate if data else 0


def enrich(con, cfg: dict, transport, *, mode: str, run_id: str, now: float | None = None, limit: int | None = None,
           event_ids: list[int] | None = None, robots: Robots | None = None, sleep: Callable[[float], None] = time.sleep,
           secret: str | None = None, private_path: Path | str | None = None) -> dict:
    """Read the pages behind catalyst events and store what they say in derived form. Returns run statistics."""
    clock = (lambda: now) if now is not None else time.time
    t0 = clock()
    sess = Session(con, cfg, transport, mode, run_id, clock, sleep=sleep, secret=secret)
    rob = robots or Robots(getattr(transport, "robots", live_robots_fetch))
    targets, skipped = select_targets(con, cfg, t0, mode=mode, limit=limit, event_ids=event_ids)
    st = {"run_id": run_id, "mode": mode, "targets": len(targets), **skipped, "ok": 0, "empty": 0, "target_http_error": 0,
          "refused_host": 0, "robots_disallowed": 0, "robots_unreachable": 0, "provider_failed": 0, "facts": 0,
          "credits": 0, "requests": 0, "private_copies": 0, "stopped": None}
    est = scrape_credit_estimate(cfg)
    refused_origins: set[str] = set()
    for tg in targets:
        url = tg["url"]
        base = {"run_id": run_id, "purpose": "ENRICH", "provider": PROVIDER, "access_mode": mode, "item_id": tg["item_id"],
                "event_id": tg["event_id"], "source_id": tg["source_id"], "requested_url": url[:500], "credits_used": 0}
        why = refused_reason(url)
        if why:
            st["refused_host"] += 1
            continue
        allowed, rcode = rob.check(url)
        if not allowed:
            origin = _origin(url)
            if origin in refused_origins:           # one row per site per run is enough to remember the refusal
                st["site_refused_robots"] += 1
                continue
            refused_origins.add(origin)
            st["robots_disallowed" if rcode == "ROBOTS_DISALLOWED" else "robots_unreachable"] += 1
            _insert_fetch(con, {**base, "status": rcode, "fetched_at": clock(),
                                "error": "robots.txt disallows FirecrawlAgent" if rcode == "ROBOTS_DISALLOWED" else
                                "robots.txt could not be read (RFC 9309: treated as disallow)"})
            con.commit()
            continue
        resp, outcome, err = sess.call("scrape", scrape_body(cfg, url, "ENRICH"), est,
                                       credits_of=lambda r: _scrape_credits(r, est))
        if outcome == "BUDGET":
            st["stopped"] = err
            break
        if outcome != "OK":
            st["provider_failed"] += 1
            _insert_fetch(con, {**base, "status": f"PROVIDER_{outcome}" if not outcome.startswith("PROVIDER") else outcome,
                                "api_status": resp.status if resp else None, "error": err, "fetched_at": clock()})
            con.commit()
            if sess.stopped:
                st["stopped"] = sess.stopped
                break
            continue
        row, facts, md = _document_row(resp, base, clock(), est)
        if row["status"] == "OK" and cfg["private_copy_days"] > 0:
            from ..social import private
            row["private_ref"] = private.put(row["content_sha256"], md, "catalyst enrichment: page text kept briefly for "
                                             "re-extraction and manual review; never published", platform="web",
                                             original_url=row.get("final_url"), retention_days=cfg["private_copy_days"],
                                             now=clock(), path=private_path)
            st["private_copies"] += 1
        fid = _insert_fetch(con, row)
        for kind, value, hint in facts:
            con.execute("INSERT OR IGNORE INTO catalyst_page_facts(fetch_id,kind,value,chain_hint) VALUES (?,?,?,?)",
                        (fid, kind, value, hint))
        con.commit()
        st[{"OK": "ok", "EMPTY": "empty", "TARGET_HTTP_ERROR": "target_http_error"}[row["status"]]] += 1
        st["facts"] += len(facts)
    st["credits"], st["requests"] = sess.run_credits, sess.requests
    st["stopped"] = st["stopped"] or sess.stopped
    return st


def _document_row(resp: HttpResponse, base: dict, now: float, est: int) -> tuple[dict, list, str]:
    data = (resp.body or {}).get("data") or {}
    meta = data.get("metadata") or {}
    md = data.get("markdown") if isinstance(data.get("markdown"), str) else ""
    links = [x for x in (data.get("links") or []) if isinstance(x, str)][:1000]
    ts = meta.get("statusCode")
    ts = ts if isinstance(ts, int) and not isinstance(ts, bool) else None
    final = safe_page_url(meta.get("url") or meta.get("sourceURL") or base["requested_url"])
    fdom = domain_of(final)
    norm = _norm_text(md)
    status = "TARGET_HTTP_ERROR" if ts is not None and ts >= 400 else ("OK" if norm else "EMPTY")
    lang = meta.get("language") if isinstance(meta.get("language"), str) and re.fullmatch(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})?", meta.get("language")) else None
    cache = meta.get("cacheState") if meta.get("cacheState") in ("hit", "miss") else None
    proxy = meta.get("proxyUsed") if meta.get("proxyUsed") in ("basic", "stealth", "enhanced") else None
    row = {**base, "final_url": final, "final_domain": fdom, "status": status, "target_status": ts, "api_status": resp.status,
           "content_sha256": hashlib.sha256(norm.encode()).hexdigest() if norm and status == "OK" else None,
           "word_count": len(re.findall(r"\w+", md)) if status == "OK" else None, "language": lang,
           "page_published_at": _page_time(meta.get("publishedTime"), now), "page_modified_at": _page_time(meta.get("modifiedTime"), now),
           "cache_state": cache, "proxy_used": proxy, "credits_used": _scrape_credits(resp, est), "fetched_at": now}
    facts = page_facts(md, links, fdom) if status == "OK" else []
    return row, facts, md


# ---------- what the rest of the catalyst code reads ----------

# Pages are looked up by the URL of each event item, not by event id: event and item ids are local to one database,
# while the read history travels between scheduled sessions through the state export (memelab/state.py).

def _event_item_urls(con, event_id: int, roles: tuple[str, ...] | None = None) -> list[tuple[int, str, str | None]]:
    q = ("SELECT i.id, i.url, i.platform FROM catalyst_items i JOIN catalyst_event_sources es ON es.item_id=i.id "
         "WHERE es.event_id=? AND i.url IS NOT NULL")
    args: list[Any] = [event_id]
    if roles:
        q += f" AND es.role IN ({','.join('?' * len(roles))})"
        args += list(roles)
    return [(r[0], r[1], r[2]) for r in con.execute(q, args)]


def _latest_ok(con, key: str) -> dict | None:
    r = con.execute("SELECT * FROM catalyst_page_fetches WHERE url_key=? AND status='OK' ORDER BY fetched_at DESC LIMIT 1", (key,)).fetchone()
    return dict(r) if r else None


def event_contracts(con, event_id: int, chain: str = "solana") -> list[str]:
    """Contracts named on pages read for an event's items (CONTRACT facts and address-bearing links), first seen first."""
    out: list[str] = []
    for _, url, _ in _event_item_urls(con, event_id):
        f = _latest_ok(con, url_key(url))
        if not f:
            continue
        for (v,) in con.execute("SELECT value FROM catalyst_page_facts WHERE fetch_id=? AND kind IN ('CONTRACT','ADDRESS_LINK') "
                                "AND chain_hint=? ORDER BY id", (f["id"], chain)):
            if v not in out:
                out.append(v)
    return out


def event_page_summary(con, event_id: int) -> dict:
    attempts, ok, facts = [], [], []
    for _, url, _ in _event_item_urls(con, event_id):
        rows = [dict(r) for r in con.execute("SELECT * FROM catalyst_page_fetches WHERE url_key=? AND purpose='ENRICH' ORDER BY fetched_at",
                                             (url_key(url),))]
        if not rows:
            continue
        good = [r for r in rows if r["status"] == "OK"]
        attempts.append(good[-1] if good else rows[-1])
        if good:
            ok.append(good[-1])
            facts += [dict(r) for r in con.execute("SELECT kind, value, chain_hint FROM catalyst_page_facts WHERE fetch_id=?", (good[-1]["id"],))]
    return {"attempts": len(attempts), "read": len(ok), "statuses": sorted({r["status"] for r in attempts}),
            "contracts": sorted({(f["chain_hint"] or "?", f["value"]) for f in facts if f["kind"] in ("CONTRACT", "ADDRESS_LINK")}),
            "tickers": sorted({f["value"] for f in facts if f["kind"] == "TICKER"}),
            "page_times": [(r["final_domain"], r["page_published_at"]) for r in ok if r["page_published_at"]]}


def citation_check(con, event_id: int) -> dict:
    """Of the event's ORIGINAL and INDEPENDENT items, how many link to another non-official publisher in the same event
    (derivative coverage). Complete only when every such item was read."""
    items = [{"id": i, "url": u, "platform": p} for i, u, p in _event_item_urls(con, event_id, ("ORIGINAL", "INDEPENDENT"))]
    doms = {i["id"]: (i["platform"] or domain_of(i["url"]) or "").lower() for i in items}
    official = lambda d: any(d == o or d.endswith("." + o) for o in OFFICIAL_DOMAINS)
    read = 0
    citing = []
    for i in items:
        r = _latest_ok(con, url_key(i["url"]))
        if not r:
            continue
        read += 1
        cited = {x[0] for x in con.execute("SELECT value FROM catalyst_page_facts WHERE fetch_id=? AND kind='CITED_DOMAIN'", (r["id"],))}
        others = {d for k, d in doms.items() if k != i["id"] and d and d != doms[i["id"]] and not official(d)}
        if any(c == o or c.endswith("." + o) for c in cited for o in others):
            citing.append(doms[i["id"]])
    complete = bool(items) and read == len(items)
    pubs = {d for d in doms.values() if d}
    uncited = len(pubs - set(citing)) if complete else None
    return {"sources": len(items), "read": read, "complete": complete, "citing": sorted(set(citing)), "uncited_publishers": uncited}


# ---------- navigate-mode fallback ----------

def page_text_from_raw(raw: str) -> str:
    """A browser-rendered JSON or XML document comes back as HTML with the text in <pre>; plain JSON/XML passes."""
    import html as _html
    s = (raw or "").strip()
    if s.startswith(("{", "[", "<?xml", "<rss", "<feed")):
        return s
    m = re.search(r"<pre[^>]*>(.*?)</pre>", s, re.S | re.I)
    if m:
        return _html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
    for tag in ("<rss", "<feed"):
        i = s.find(tag)
        if i >= 0:
            return s[i:]
    return s


def pull_fallback(con, cfg: dict, transport, sources: list[dict], *, mode: str, run_id: str, parse: Callable[[str, str], Any],
                  now: float | None = None, robots: Robots | None = None, sleep: Callable[[float], None] = time.sleep,
                  secret: str | None = None) -> tuple[dict, dict]:
    """For navigate-mode sources that failed a direct pull and are listed in pull_fallback.sources: read the URL through
    Firecrawl (rawHtml) and parse it with the same parser. Returns ({'cat:<sid>': entry}, stats)."""
    clock = (lambda: now) if now is not None else time.time
    allow = set(cfg["pull_fallback"]["sources"])
    sess = Session(con, cfg, transport, mode, run_id, clock, sleep=sleep, secret=secret)
    rob = robots or Robots(getattr(transport, "robots", live_robots_fetch))
    est = scrape_credit_estimate(cfg)
    out: dict[str, dict] = {}
    st = {"listed": 0, "not_listed": 0, "ok": 0, "failed": 0, "credits": 0, "stopped": None}
    for s in sources:
        sid, url, kind = s["source_id"], s["url"], s.get("parser") or "rss"
        if sid not in allow:
            st["not_listed"] += 1
            continue
        st["listed"] += 1
        base = {"run_id": run_id, "purpose": "PULL_FALLBACK", "provider": PROVIDER, "access_mode": mode, "source_id": sid,
                "requested_url": url[:500], "credits_used": 0}
        why = refused_reason(url)
        allowed, rcode = (False, "REFUSED_HOST") if why else rob.check(url)
        if not allowed:
            st["failed"] += 1
            _insert_fetch(con, {**base, "status": rcode, "error": why, "fetched_at": clock()})
            con.commit()
            continue
        resp, outcome, err = sess.call("scrape", scrape_body(cfg, url, "PULL_FALLBACK"), est,
                                       credits_of=lambda r: _scrape_credits(r, est))
        if outcome == "BUDGET":
            st["stopped"] = err
            break
        data = ((resp.body or {}).get("data") or {}) if resp is not None and outcome == "OK" else {}
        meta = data.get("metadata") or {}
        ts = meta.get("statusCode") if isinstance(meta.get("statusCode"), int) else None
        body, perr = None, err
        if outcome != "OK":
            status = outcome if outcome.startswith("PROVIDER") else f"PROVIDER_{outcome}"
        elif ts is not None and ts >= 400:
            status, perr = "TARGET_HTTP_ERROR", f"page answered HTTP {ts}"
        else:
            status = "OK"
            try:
                body = parse(kind, page_text_from_raw(data.get("rawHtml") or ""))
            except Exception as e:          # the page was not the document the parser expects
                status, perr = "PARSE_FAILED", scrub(f"{type(e).__name__}: {e}", secret)
        if status == "OK":
            st["ok"] += 1
            out[f"cat:{sid}"] = {"s": 200, "len": len(data.get("rawHtml") or ""), "ms": 0, "body": body, "err": None, "_cat": sid,
                                 "via": "firecrawl"}
        else:
            st["failed"] += 1
        final = meta.get("url") or meta.get("sourceURL")
        _insert_fetch(con, {**base, "status": status, "final_url": safe_page_url(final) if final else None,
                            "final_domain": domain_of(final) if final else None, "target_status": ts,
                            "api_status": resp.status if resp is not None else None,
                            "credits_used": _scrape_credits(resp, est) if resp is not None and outcome == "OK" else 0,
                            "error": perr, "fetched_at": clock()})
        con.commit()
        if sess.stopped:
            st["stopped"] = sess.stopped
            break
    st["credits"] = sess.run_credits
    return out, st


# ---------- news search ----------

_REL = re.compile(r"^\s*(\d{1,3})\s+(minute|min|hour|hr)s?\s+ago\s*$", re.I)


def search_time(v: Any, now: float) -> float | None:
    """Absolute dates, and 'N minutes/hours ago' (hour precision). 'N days ago' and coarser are left unknown: a
    day-level guess would make an old story look fresh."""
    if not isinstance(v, str) or not v.strip():
        return None
    m = _REL.match(v)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        return now - n * (60 if unit.startswith("min") else 3600)
    t = to_epoch(v)
    return t if t is not None and 1_230_768_000 <= t <= now + 3600 else None


def search_queries(con, cfg: dict, now: float, *, query: str | None = None, events: int = 0) -> list[tuple[str, str, int | None]]:
    q = cfg["search"]
    if query:
        return [(query.strip()[:200], q["tbs_query"], None)]
    rows = con.execute("SELECT id, title, description, category FROM catalyst_events WHERE status IN ('NEW','RESEARCH','TRACKED') AND "
                       "(expires_at IS NULL OR expires_at > ?) AND discovered_at >= ? AND independent_sources <= ? "
                       "ORDER BY COALESCE(published_at, discovered_at) DESC",
                       (now, now - cfg["enrich"]["event_window_hours"] * 3600, q["max_event_sources"])).fetchall()
    if cfg["enrich"]["relevance"] == "memecoin":
        rows = [r for r in rows if relevant(r["category"], r["title"], r["description"])]
    out = []
    for r in rows[: max(0, events)]:
        t = re.sub(r"\s+", " ", strip_publisher(r["title"]) or "").strip()
        if len(t) >= 12:
            out.append((t[:200], q["tbs_events"], r["id"]))
    return out


def search(con, cfg: dict, transport, *, mode: str, run_id: str, now: float | None = None, query: str | None = None,
           events: int = 0, sleep: Callable[[float], None] = time.sleep, secret: str | None = None) -> tuple[dict, dict]:
    """News search; returns ({'cat:web:firecrawl:search': entry} or {}, stats). Results whose URL the lab already
    stored, refused hosts, and repeats within the run are dropped before ingest."""
    clock = (lambda: now) if now is not None else time.time
    t0 = clock()
    qc = cfg["search"]
    sess = Session(con, cfg, transport, mode, run_id, clock, sleep=sleep, secret=secret)
    known = {canonical_url(r[0]) for r in con.execute("SELECT url FROM catalyst_items WHERE url IS NOT NULL")}
    results: list[dict] = []
    st = {"queries": 0, "results": 0, "kept": 0, "already_stored": 0, "refused_host": 0, "credits": 0, "stopped": None}
    for text, tbs, ev_id in search_queries(con, cfg, t0, query=query, events=events)[: qc["max_queries_per_run"]]:
        body = {"query": text, "limit": qc["limit"], "sources": ["news"], "tbs": tbs, "lang": qc["lang"], "timeout": 30000}
        est = search_credit_estimate(cfg, qc["limit"])

        def credits_of(r: HttpResponse) -> int:
            cu = (r.body or {}).get("creditsUsed")
            return cu if isinstance(cu, int) and not isinstance(cu, bool) and cu >= 0 else est
        resp, outcome, err = sess.call("search", body, est, credits_of=credits_of)
        if outcome == "BUDGET":
            st["stopped"] = err
            break
        st["queries"] += 1
        if outcome != "OK":
            if sess.stopped:
                st["stopped"] = sess.stopped
                break
            continue
        data = (resp.body or {}).get("data")
        groups = [("news", (data or {}).get("news") or []), ("web", (data or {}).get("web") or [])] if isinstance(data, dict) else [("web", data or [])]
        qsha = hashlib.sha256(text.encode()).hexdigest()[:16]
        for kind, rows in groups:
            for r in rows if isinstance(rows, list) else []:
                if not isinstance(r, dict) or not isinstance(r.get("url"), str):
                    continue
                st["results"] += 1
                if refused_reason(r["url"]):
                    st["refused_host"] += 1
                    continue
                cu = canonical_url(r["url"])
                if cu in known:
                    st["already_stored"] += 1
                    continue
                known.add(cu)
                title = re.sub(r"\s+", " ", str(r.get("title") or "")).strip()[:300]
                if not title:
                    continue
                snippet = re.sub(r"\s+", " ", str(r.get("snippet") or r.get("description") or "")).strip()[:400]
                results.append({"url": r["url"][:500], "title": title, "snippet": snippet, "kind": kind,
                                "published_at": search_time(r.get("date"), t0), "position": r.get("position"),
                                "query_sha": qsha, "for_event": ev_id})
                st["kept"] += 1
    st["credits"] = sess.run_credits
    st["stopped"] = st["stopped"] or sess.stopped
    out = {f"cat:{SEARCH_SOURCE_ID}": {"_cat": SEARCH_SOURCE_ID, "s": 200, "body": results}} if results else {}
    return out, st


# ---------- health ----------

def health(con, cfg: dict | None, *, key: str | None, error: str | None = None, path: Path | None = None,
           transport=None, remote: bool = False, now: float | None = None) -> dict:
    t = time.time() if now is None else now
    status, why = readiness(cfg, key, error)
    out = {"provider": PROVIDER, "contract_verified": CONTRACT_VERIFIED, "config": str(path) if path else None,
           "status": status, "detail": why, "key": ("set" if key else "missing") if (cfg or {}).get("billing", "cloud") == "cloud" else "not needed"}
    if cfg:
        b = cfg["budget"]
        out.update({"enabled": cfg["enabled"], "billing": cfg["billing"], "base_url": cfg["base_url"], "proxy": cfg["scrape"]["proxy"],
                    "caps": {"credits_per_run": b["max_credits_per_run"], "credits_per_month": b["max_credits_per_month"],
                             "requests_per_run": b["max_requests_per_run"]},
                    "search_enabled": cfg["search"]["enabled"], "pull_fallback_sources": cfg["pull_fallback"]["sources"]})
    out["credits_this_month_live"] = month_credits(con, "live", t)
    last = con.execute("SELECT MAX(requested_at) FROM social_api_spend WHERE connector=? AND mode='live' AND http_status=200",
                       (PROVIDER,)).fetchone()[0]
    out["last_live_ok_at"] = last
    if status == "ready" and last:
        out["status"] = "live_ok"
    elif status == "ready":
        out["status"] = "configured_unverified"
    if remote and status == "ready" and cfg["billing"] == "cloud" and transport is not None:
        sess = Session(con, cfg, transport, "live" if isinstance(transport, RestTransport) else "fixture", f"fchealth_{int(t)}",
                       lambda: t, secret=key)
        resp, outcome, err = sess.call("credit_usage", None, 0, method="GET", credits_of=lambda r: 0)
        if outcome == "OK":
            d = (resp.body or {}).get("data") or {}
            out["remote"] = {k: d.get(k) for k in ("remainingCredits", "planCredits", "billingPeriodStart", "billingPeriodEnd")}
            if out["status"] == "configured_unverified" and sess.mode == "live":
                out["status"] = "live_ok"
        else:
            out["remote"] = {"outcome": outcome, "error": err}
            if outcome == "UNAUTHORIZED":
                out["status"] = "credentials_rejected"
    return out


def new_run_id(prefix: str = "fc") -> str:
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{os.getpid() % 10000:04d}"
