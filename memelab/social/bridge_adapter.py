"""Bridge/inbox adapter: social units from browser-bridge result files.

This is the lab's established route (memelab/bridge): the collector runs in Elving's Chrome, the page result is
shipped to the hand-off repo as inbox/<id>.json (__ML.ship), and the cloud side pulls it with
memelab.bridge.github_inbox.pull() into data/inbox/<id>.result.json. A result file has the shape the collector
writes for every source:

    {"_plan": "<id>", "_at": "<ISO time>", "_n": <count>,
     "<key>": {"s": <http-like status>, "len": <bytes>, "ms": <latency>, "err": <text or null>, "body": <projection>}}

Social units use keys "soc:<platform>:<source_id>" and their body is an inbound envelope (INBOUND_SCHEMA in
memelab/social/ingest.py). Every other key (market data, catalyst sources) belongs to other modules and is
ignored here. An entry may also carry "challenge": "login" | "captcha" | "blocked" when the page asked for one;
the collector stops and records it (D-009) and the connector is marked accordingly.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, Iterable, Iterator

from .ingest import PLATFORMS, Budget, SourceUnit, TransientError, canonical_sha, log_event, redact, with_retries

PREFIX = "soc:"
CHALLENGE = {"login": "LOGIN_REQUIRED", "captcha": "CAPTCHA", "blocked": "BLOCKED"}


def _status(entry: dict) -> tuple[str, str | None]:
    ch = entry.get("challenge")
    if ch in CHALLENGE:
        return CHALLENGE[ch], f"page asked for {ch}"
    s = entry.get("s")
    err = entry.get("err")
    err = redact(str(err))[:200] if err else None
    if s == 200:
        if not isinstance(entry.get("body"), dict):
            return "DOWN", "status 200 without an envelope body"
        return "OK", None
    if s == 429:
        return "RATE_LIMITED", err or "status 429"
    if s in (401, 403):
        return "BLOCKED", err or f"status {s}"
    return "DOWN", err or f"status {s}"


class BridgeInboxAdapter:
    """Reads one or more bridge result files. Unreadable files become a DOWN unit for that file only."""

    name = "bridge_inbox"

    def __init__(self, paths: Iterable[Path | str], retries: int = 3, base_delay: float = 0.5,
                 sleep: Callable[[float], None] = time.sleep):
        self.paths = [Path(p) for p in paths]
        self.retries = retries
        self.base_delay = base_delay
        self.sleep = sleep

    def _read(self, p: Path) -> str:
        def once():
            if not p.exists():
                raise FileNotFoundError(str(p))
            txt = p.read_text()
            if not txt.strip():
                raise TransientError("empty file (still being written?)")
            return txt
        return with_retries(once, attempts=self.retries, base_delay=self.base_delay, sleep=self.sleep,
                            transient=(TransientError, TimeoutError, BlockingIOError, InterruptedError), what=f"read {p.name}")

    def units(self, budget: Budget) -> Iterator[SourceUnit]:
        for p in self.paths:
            file_conn = f"{self.name}:file:{p.name}"
            try:
                data = json.loads(self._read(p))
                if not isinstance(data, dict):
                    raise ValueError("result file is not a JSON object")
            except Exception as e:
                why = "result file is not valid JSON" if isinstance(e, json.JSONDecodeError) else f"{type(e).__name__}: {redact(str(e))[:160]}"
                log_event("file_unreadable", connector=file_conn, file=p.name, error=why)
                yield SourceUnit(connector=file_conn, platform="other", source_ref=p.name, status="DOWN",
                                 unit_sha=canonical_sha(["unreadable", p.name]), error=why)
                continue
            plan_id = data.get("_plan") if isinstance(data.get("_plan"), str) else None
            keys = sorted(k for k in data if isinstance(k, str) and k.startswith(PREFIX))
            if not keys:
                log_event("file_without_social_units", file=p.name, plan_id=plan_id)
            for key in keys:
                entry = data[key]
                parts = key.split(":", 2)
                platform = parts[1] if len(parts) == 3 and parts[1] in PLATFORMS else "other"
                connector = f"{self.name}:{key[len(PREFIX):]}"
                ref = f"{p.name}#{key}"
                if not isinstance(entry, dict) or len(parts) != 3 or not parts[2]:
                    yield SourceUnit(connector=connector, platform=platform, source_ref=ref, status="DOWN",
                                     unit_sha=canonical_sha(entry), error="malformed inbox entry or key", plan_id=plan_id)
                    continue
                status, err = _status(entry)
                yield SourceUnit(connector=connector, platform=platform, source_ref=ref, status=status,
                                 unit_sha=canonical_sha(entry), body=entry.get("body"), error=err, plan_id=plan_id)
