"""Model providers for Phase 06 claim extraction: configuration, budget and a truthful health status.

No model was configured in this repo before Phase 06. Configuration lives in a gitignored file:

    data/private/llm.json   (override with MEMELAB_LLM_CONFIG; example in docs/social-intelligence/llm.example.json)

    {"provider": "anthropic", "model": "<model id>", "allow_billable": false,
     "price_usd_per_mtok": {"input": 0, "output": 0},
     "max_calls_per_run": 20, "max_calls_per_month": 500, "max_usd_per_month": 0,
     "max_input_chars": 4000, "max_output_tokens": 1500, "timeout_s": 60}

The API key is read from the environment only (ANTHROPIC_API_KEY); a config file holding a key is refused.
A live call happens only when a provider and model are configured, the key is present, allow_billable is true,
prices are set, and the call fits the run, monthly-call and monthly-dollar caps. Otherwise the extractor gets an
`analysis_unavailable` reason and makes no call (the X billing guard pattern, D-023).

Status values (llm_status): model_not_configured, credentials_missing, billing_not_consented, configured_unverified
(everything set, no successful live call recorded yet), live_ok (a live call returned 200, from social_api_spend).
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .. import db
from .ingest import redact

FORBIDDEN_CONFIG_KEYS = {"api_key", "key", "token", "secret", "anthropic_api_key", "authorization", "password"}
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULTS = {"allow_billable": False, "max_calls_per_run": 20, "max_calls_per_month": 500, "max_usd_per_month": 0.0,
            "max_input_chars": 4000, "max_output_tokens": 1500, "timeout_s": 60, "price_usd_per_mtok": None}


def config_path() -> Path:
    env = os.environ.get("MEMELAB_LLM_CONFIG")
    return Path(env) if env else db.DATA_DIR / "private" / "llm.json"


def load_config(path: Path | str | None = None) -> dict | None:
    """None when no config file exists (model_not_configured). Raises on a config that holds a secret."""
    p = Path(path) if path else config_path()
    if not p.is_file():
        return None
    cfg = json.loads(p.read_text())
    bad = sorted(k for k in cfg if k.lower() in FORBIDDEN_CONFIG_KEYS)
    if bad:
        raise ValueError(f"llm config must not hold secrets; remove keys {bad} and use the environment")
    return {**DEFAULTS, **cfg}


@dataclass
class Completion:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    http_status: int | None = None


class ProviderError(Exception):
    def __init__(self, code: str, http_status: int | None = None):
        super().__init__(code)
        self.code, self.http_status = code, http_status


class MockProvider:
    """Offline provider for tests and demos. Responses are keyed by the content hash that the prompt carries;
    each call for a hash returns the next response in its list (the last one repeats). Mode 'fixture'."""
    name = "mock"
    mode = "fixture"

    def __init__(self, responses: dict[str, list[str]], model: str = "mock-claims-1"):
        self.responses = {k: list(v) for k, v in responses.items()}
        self.model = model
        self.calls: list[dict] = []

    @classmethod
    def from_file(cls, path: Path | str) -> "MockProvider":
        body = json.loads(Path(path).read_text())
        return cls({r["content_sha256"]: [o if isinstance(o, str) else json.dumps(o) for o in r["outputs"]] for r in body["responses"]},
                   model=body.get("model", "mock-claims-1"))

    def complete(self, system: str, user: str, max_tokens: int) -> Completion:
        m = re.search(r"content_sha256: ([0-9a-f]{64})", user)
        key = m.group(1) if m else ""
        self.calls.append({"content_sha256": key, "user_chars": len(user)})
        seq = self.responses.get(key)
        if not seq:
            raise ProviderError("mock_no_response")
        out = seq.pop(0) if len(seq) > 1 else seq[0]
        return Completion(out, input_tokens=len(system + user) // 4, output_tokens=len(out) // 4, http_status=200)


class AnthropicProvider:
    """Anthropic Messages API (POST /v1/messages). Not exercised live in Phase 06: no key or consent exists.
    `transport` is injectable so the request shape is tested offline."""
    name = "anthropic"
    mode = "live"

    def __init__(self, model: str, api_key: str, timeout_s: float = 60, transport: Callable | None = None):
        if not model:
            raise ValueError("anthropic provider needs a model id in the config")
        self.model, self._key, self.timeout_s = model, api_key, timeout_s
        self._transport = transport or self._urllib

    def _urllib(self, url: str, headers: dict, body: bytes, timeout: float) -> tuple[int, bytes]:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def complete(self, system: str, user: str, max_tokens: int) -> Completion:
        body = json.dumps({"model": self.model, "max_tokens": int(max_tokens), "temperature": 0, "system": system,
                           "messages": [{"role": "user", "content": user}]}).encode()
        headers = {"x-api-key": self._key, "anthropic-version": ANTHROPIC_VERSION, "content-type": "application/json"}
        try:
            status, raw = self._transport(ANTHROPIC_URL, headers, body, self.timeout_s)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise ProviderError("network_error:" + redact(type(e).__name__))
        if status == 429 or status == 529:
            raise ProviderError("rate_limited", status)
        if status in (401, 403):
            raise ProviderError("auth_failed", status)
        if status != 200:
            raise ProviderError(f"http_{status}", status)
        try:
            j = json.loads(raw)
            text = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
            u = j.get("usage") or {}
        except (ValueError, AttributeError):
            raise ProviderError("unparseable_provider_response", status)
        return Completion(text, u.get("input_tokens"), u.get("output_tokens"), status)


@dataclass
class Budget:
    """Per-run call budget plus monthly caps read from social_api_spend (live rows only count as live spend)."""
    max_calls_per_run: int = 20
    max_calls_per_month: int = 500
    max_usd_per_month: float = 0.0
    max_input_chars: int = 4000
    max_output_tokens: int = 1500
    price_in: float | None = None          # USD per million input tokens
    price_out: float | None = None
    calls: int = 0
    spent_usd: float = 0.0
    refusals: list[str] = field(default_factory=list)

    @classmethod
    def from_config(cls, cfg: dict | None) -> "Budget":
        cfg = cfg or DEFAULTS
        price = cfg.get("price_usd_per_mtok") or {}
        return cls(max_calls_per_run=int(cfg["max_calls_per_run"]), max_calls_per_month=int(cfg["max_calls_per_month"]),
                   max_usd_per_month=float(cfg["max_usd_per_month"]), max_input_chars=int(cfg["max_input_chars"]),
                   max_output_tokens=int(cfg["max_output_tokens"]), price_in=price.get("input"), price_out=price.get("output"))

    def worst_case_usd(self, input_chars: int) -> float:
        if self.price_in is None or self.price_out is None:
            return 0.0
        return (input_chars / 3.0) * self.price_in / 1e6 + self.max_output_tokens * self.price_out / 1e6

    def cost(self, input_tokens: int | None, output_tokens: int | None) -> float:
        if self.price_in is None or self.price_out is None:
            return 0.0
        return (input_tokens or 0) * self.price_in / 1e6 + (output_tokens or 0) * self.price_out / 1e6

    def allow(self, con: sqlite3.Connection, connector: str, mode: str, input_chars: int, now: float) -> str | None:
        """None when the call may go ahead, else the refusal reason."""
        if self.calls >= self.max_calls_per_run:
            return "budget_exhausted"
        if mode == "live":
            month = time.strftime("%Y-%m", time.gmtime(now))
            n, usd = con.execute("SELECT COUNT(*), COALESCE(SUM(est_cost_usd),0) FROM social_api_spend WHERE mode='live' AND connector=?"
                                 " AND substr(billing_day,1,7)=?", (connector, month)).fetchone()
            if n >= self.max_calls_per_month:
                return "budget_exhausted"
            if self.price_in is None or self.price_out is None:
                return "billing_not_consented"
            if usd + self.worst_case_usd(input_chars) > self.max_usd_per_month:
                return "budget_exhausted"
        return None

    def record(self, con: sqlite3.Connection, connector: str, mode: str, http_status: int | None, comp: Completion | None,
               run_id: str | None, now: float) -> float:
        self.calls += 1
        c = self.cost(comp.input_tokens, comp.output_tokens) if comp else 0.0
        if mode == "fixture":
            c = 0.0
        self.spent_usd += c
        con.execute("INSERT INTO social_api_spend(connector,run_id,endpoint,http_status,billing_day,resources_json,est_cost_usd,mode,requested_at)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (connector, run_id, "/v1/messages", http_status, time.strftime("%Y-%m-%d", time.gmtime(now)),
                     json.dumps({"input_tokens": comp.input_tokens if comp else None, "output_tokens": comp.output_tokens if comp else None}),
                     c, mode, now))
        return c


def provider_from_config(cfg: dict | None, env: dict | None = None, transport: Callable | None = None):
    """(provider or None, reason). Reason is None when a provider is ready to be asked (budget still applies)."""
    env = os.environ if env is None else env
    if not cfg or not cfg.get("provider") or not cfg.get("model"):
        return None, "model_not_configured"
    if cfg["provider"] != "anthropic":
        return None, "model_not_configured"
    key = env.get("ANTHROPIC_API_KEY")
    if not key:
        return None, "credentials_missing"
    if not cfg.get("allow_billable"):
        return None, "billing_not_consented"
    return AnthropicProvider(cfg["model"], key, float(cfg.get("timeout_s", 60)), transport=transport), None


def llm_status(con: sqlite3.Connection | None = None, cfg_path: Path | str | None = None, env: dict | None = None) -> dict:
    """Truthful model status. Never makes a network call."""
    try:
        cfg = load_config(cfg_path)
    except ValueError as e:
        return {"status": "config_invalid", "detail": str(e)}
    _, reason = provider_from_config(cfg, env)
    out: dict[str, Any] = {"config_file": str(Path(cfg_path) if cfg_path else config_path()), "provider": (cfg or {}).get("provider"),
                           "model": (cfg or {}).get("model"), "live_calls_ok": 0}
    if con is not None:
        try:
            out["live_calls_ok"] = con.execute("SELECT COUNT(*) FROM social_api_spend WHERE mode='live' AND connector LIKE 'llm:%'"
                                               " AND http_status=200").fetchone()[0]
            out["fixture_calls"] = con.execute("SELECT COUNT(*) FROM social_api_spend WHERE mode='fixture' AND connector LIKE 'llm:%'").fetchone()[0]
        except sqlite3.OperationalError:
            pass
    if reason:
        out["status"] = reason
    elif (cfg.get("price_usd_per_mtok") or {}).get("input") is None or (cfg.get("price_usd_per_mtok") or {}).get("output") is None:
        out["status"] = "billing_not_consented"
    else:
        out["status"] = "live_ok" if out["live_calls_ok"] else "configured_unverified"
    return out
