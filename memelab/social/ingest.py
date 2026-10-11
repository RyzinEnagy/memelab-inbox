"""Provider-neutral ingestion of inbound social observations (Phase 02).

An adapter turns some transport (today: the browser-bridge inbox, memelab/social/bridge_adapter.py) into
SourceUnits. Everything after that is shared and lives here:

  validate  -> versioned inbound schema (INBOUND_SCHEMA); field names and rule names in errors, never values
  dedupe    -> event_id (collector id, or derived) is unique; observations are also unique by observation_key
  persist   -> memelab/social/store.py (accounts, items, append-only observations) + provenance row per event
  quarantine-> a bad item is set aside (hash + reasons in the DB, payload in the gitignored private folder)
               and the rest of the unit carries on
  checkpoint-> per unit (connector, source_ref, unit_sha): items are committed in batches and the next index is
               saved in the same transaction, so a crash or a budget stop resumes without duplicates
  health    -> one connector_health row per connector per run (worst status wins); a connector that is down
               is recorded as down and the other connectors carry on
  coverage  -> one social_coverage row per unit per run, with the gap reason when it was not fully covered

Content policy (DECISIONS D-010, D-013): the inbound schema carries a content hash computed by the collector,
never the text. Items that carry text, bios, media, DMs, member lists or anything not PUBLIC are quarantined.
Logs are JSON lines with counts, ids, hashes and reasons only; secret-looking values are redacted.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Protocol

from . import private, store
from .schema import migrate

INBOUND_SCHEMA = "memelab.social.inbound/1"
ANALYSIS_VERSION = "social-ingest-v1"
PLATFORMS = ("x", "telegram", "youtube", "discord", "farcaster", "other")
ACCESS_MODES = ("fetch", "navigate", "signed_in_browser", "manual", "fixture")
RETRIEVAL = ("OK", "PARTIAL", "NOT_FOUND", "DELETED", "PROTECTED", "BLOCKED", "RATE_LIMITED", "LOGIN_REQUIRED", "CAPTCHA", "ERROR")
# content classes that never travel through the public inbox (D-010): quarantined on sight
BLOCKED_KEYS = {"text", "raw_text", "full_text", "html", "raw_html", "bio", "description", "media", "image", "images",
                "video", "videos", "dm", "dms", "members", "member_list", "quote", "quotes", "screenshot", "transcript"}
ITEM_KEYS = {"event_id", "platform", "provider_item_id", "url", "account", "published_at", "published_at_basis",
             "fetched_at", "retrieval_status", "content_hash", "summary", "metrics", "visibility"}
ACCOUNT_KEYS = {"handle", "provider_user_id", "profile_url", "display_name"}
FUTURE_SKEW = 300.0           # seconds a timestamp may sit in the future (clock drift)
HEALTH_RANK = {"OK": 0, "DEGRADED": 1, "RATE_LIMITED": 2, "LOGIN_REQUIRED": 3, "CAPTCHA": 3, "BLOCKED": 3, "DOWN": 4}
HEX64 = re.compile(r"^[0-9a-f]{64}$")

log = logging.getLogger("memelab.social.ingest")


# ---------- safe structured logging ----------

_CONTENT_FIELDS = {"text", "summary", "body", "payload", "raw", "html", "bio", "item", "entry"}
_SECRET_RE = re.compile(r"(?i)((?:api[-_]?key|apikey|token|secret|password|passwd|authorization|auth|key)\s*[=:]\s*)([^&\s\"',;]+)")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]+")
_TOKEN_RE = re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,})\b")


def redact(s: str) -> str:
    s = _SECRET_RE.sub(lambda m: m.group(1) + "[REDACTED]", s)
    s = _BEARER_RE.sub("Bearer [REDACTED]", s)
    return _TOKEN_RE.sub("[REDACTED]", s)


def _safe(v: Any) -> Any:
    if isinstance(v, str):
        return redact(v)[:300]
    if isinstance(v, dict):
        return {k: _safe(x) for k, x in v.items() if k not in _CONTENT_FIELDS}
    if isinstance(v, (list, tuple)):
        return [_safe(x) for x in v][:50]
    return v


def log_event(event: str, level: int = logging.INFO, **fields: Any) -> None:
    """One JSON line. Content-bearing field names are dropped and secret-looking values redacted."""
    rec = {"event": event, **{k: _safe(v) for k, v in fields.items() if k not in _CONTENT_FIELDS}}
    log.log(level, json.dumps(rec, sort_keys=True, default=str))


# ---------- retries and budget ----------

class TransientError(Exception):
    """Raised by an adapter for a failure worth retrying (timeouts, 5xx, a file still being written)."""


def with_retries(fn: Callable[[], Any], attempts: int = 3, base_delay: float = 0.5, max_delay: float = 8.0,
                 sleep: Callable[[float], None] = time.sleep, transient=(TransientError, OSError, TimeoutError),
                 what: str = "call") -> Any:
    """Bounded retries with exponential backoff. Non-transient errors are raised at once."""
    attempts = max(1, int(attempts))
    for i in range(attempts):
        try:
            return fn()
        except transient as e:
            if i == attempts - 1:
                raise
            delay = min(max_delay, base_delay * (2 ** i))
            log_event("retry", logging.WARNING, what=what, attempt=i + 1, of=attempts, delay_s=delay, error=type(e).__name__)
            sleep(delay)


class BudgetExceeded(Exception):
    pass


@dataclass
class Budget:
    """Rate-limit and cost hook. Adapters and the pipeline call charge(); a collector that reads pages (X, Telegram)
    sets pace_seconds for human pacing and max_cost for paid calls. None = no limit."""
    max_items: int | None = None
    max_units: int | None = None
    max_cost: float | None = None
    pace_seconds: float = 0.0
    sleep: Callable[[float], None] = time.sleep
    used: dict = field(default_factory=lambda: {"items": 0, "units": 0, "cost": 0.0})

    def charge(self, kind: str, n: int = 1, cost: float = 0.0) -> None:
        limit = {"items": self.max_items, "units": self.max_units}.get(kind)
        if limit is not None and self.used[kind] + n > limit:
            raise BudgetExceeded(f"{kind} budget {limit} reached")
        if self.max_cost is not None and self.used["cost"] + cost > self.max_cost:
            raise BudgetExceeded(f"cost budget {self.max_cost} reached")
        self.used[kind] = self.used.get(kind, 0) + n
        self.used["cost"] += cost
        if self.pace_seconds:
            self.sleep(self.pace_seconds)

    def to_dict(self) -> dict:
        return {"max_items": self.max_items, "max_units": self.max_units, "max_cost": self.max_cost,
                "pace_seconds": self.pace_seconds, "used": dict(self.used)}


# ---------- adapter contract ----------

@dataclass
class SourceUnit:
    """One batch of inbound items from one connector, as the adapter found it.

    status is the connector's state for this unit: OK when body holds an inbound envelope, otherwise DOWN,
    RATE_LIMITED, LOGIN_REQUIRED, CAPTCHA or BLOCKED with error set."""
    connector: str
    platform: str
    source_ref: str
    status: str
    unit_sha: str
    body: Any = None
    error: str | None = None
    plan_id: str | None = None


class SourceAdapter(Protocol):
    """What a transport must provide. Only these two members are used by ingest()."""
    name: str

    def units(self, budget: Budget) -> Iterable[SourceUnit]: ...


def canonical_sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


# ---------- validation ----------

def _ts(v: Any, name: str, errors: list[str], required: bool = False) -> float | None:
    if v is None or v == "":
        if required:
            errors.append(f"{name}: missing")
        return None
    try:
        return store.to_utc(v)
    except Exception:
        errors.append(f"{name}: unparseable or naive timestamp")
        return None


def validate_envelope(body: Any, unit: SourceUnit, now: float) -> tuple[dict | None, list[str]]:
    errors: list[str] = []
    if not isinstance(body, dict):
        return None, ["body: not an object"]
    if body.get("schema") != INBOUND_SCHEMA:
        errors.append(f"schema: expected {INBOUND_SCHEMA}")
    src = body.get("source")
    if not isinstance(src, dict):
        errors.append("source: not an object")
        src = {}
    plat = src.get("platform")
    if plat not in PLATFORMS:
        errors.append("source.platform: not an allowed platform")
    elif plat != unit.platform:
        errors.append("source.platform: does not match the inbox key")
    if src.get("access_mode") not in ACCESS_MODES:
        errors.append("source.access_mode: not an allowed access mode")
    for k in ("collector", "rights_basis"):
        if not isinstance(src.get(k), str) or not src.get(k):
            errors.append(f"source.{k}: missing")
    fetched = _ts(body.get("fetched_at"), "fetched_at", errors, required=True)
    if fetched is not None and fetched > now + FUTURE_SKEW:
        errors.append("fetched_at: in the future")
    if not isinstance(body.get("items"), list):
        errors.append("items: not a list")
    if errors:
        return None, errors
    return {"source": src, "fetched_at": fetched, "items": body["items"]}, []


def validate_item(item: Any, env: dict, now: float) -> tuple[dict | None, str | None, list[str], list[str]]:
    """Returns (clean, reason_code, errors, ignored_fields). clean is None when the item must be quarantined."""
    if not isinstance(item, dict):
        return None, "INVALID", ["item: not an object"], []
    blocked = sorted(BLOCKED_KEYS & set(item)) + sorted("account." + k for k in BLOCKED_KEYS & set(item.get("account") or {}) if isinstance(item.get("account"), dict))
    if blocked:
        return None, "BLOCKED_CONTENT", [f"{k}: content class not allowed in the inbox (D-010)" for k in blocked], []
    src = env["source"]
    vis = item.get("visibility", src.get("visibility"))
    if vis != "PUBLIC":
        return None, "NOT_PUBLIC", ["visibility: only PUBLIC content is ingested (D-009)"], []
    errors: list[str] = []
    ignored = sorted(set(item) - ITEM_KEYS)
    plat = item.get("platform", src["platform"])
    if plat != src["platform"]:
        errors.append("platform: differs from source.platform")
    pid = item.get("provider_item_id")
    if pid is not None and not isinstance(pid, (str, int)) or isinstance(pid, bool):
        errors.append("provider_item_id: not a string or integer")
    pid = str(pid) if isinstance(pid, (str, int)) and not isinstance(pid, bool) and str(pid).strip() else None
    url = item.get("url")
    if url is not None and (not isinstance(url, str) or not url.startswith("https://") or len(url) > 500):
        errors.append("url: not an https URL")
        url = None
    if pid is None and url is None:
        errors.append("provider_item_id/url: one is required")
    acct = item.get("account")
    if acct is not None:
        if not isinstance(acct, dict):
            errors.append("account: not an object")
            acct = None
        else:
            ignored += sorted("account." + k for k in set(acct) - ACCOUNT_KEYS)
            if not (acct.get("handle") or acct.get("provider_user_id")):
                errors.append("account: needs handle or provider_user_id")
            pu = acct.get("profile_url")
            if pu is not None and (not isinstance(pu, str) or not pu.startswith("https://")):
                errors.append("account.profile_url: not an https URL")
    fetched = _ts(item.get("fetched_at"), "fetched_at", errors) if "fetched_at" in item else env["fetched_at"]
    if fetched is not None and fetched > now + FUTURE_SKEW:
        errors.append("fetched_at: in the future")
    published = _ts(item.get("published_at"), "published_at", errors)
    if published is not None and fetched is not None and published > fetched + FUTURE_SKEW:
        errors.append("published_at: after fetched_at")
    basis = item.get("published_at_basis")
    if basis is not None and basis not in ("PROVIDER", "PARSED_RELATIVE"):
        errors.append("published_at_basis: not PROVIDER or PARSED_RELATIVE")
    status = item.get("retrieval_status", "OK")
    if status not in RETRIEVAL:
        errors.append("retrieval_status: not an allowed status")
    ch = item.get("content_hash")
    if ch is not None and (not isinstance(ch, str) or not HEX64.match(ch)):
        errors.append("content_hash: not a lower-case sha256 hex digest")
    summ = item.get("summary")
    if summ is not None and (not isinstance(summ, str) or len(summ) > store.SUMMARY_MAX):
        errors.append(f"summary: not a string of at most {store.SUMMARY_MAX} characters")
    metrics = item.get("metrics")
    if metrics is not None:
        if not isinstance(metrics, dict):
            errors.append("metrics: not an object")
        else:
            bad = sorted(k for k, v in metrics.items() if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))))
            if bad:
                errors.append("metrics: non-numeric values for " + ",".join(str(b)[:40] for b in bad))
    eid = item.get("event_id")
    if eid is not None and (not isinstance(eid, str) or not re.fullmatch(r"[A-Za-z0-9:_\-.]{1,128}", eid)):
        errors.append("event_id: must be 1-128 characters of [A-Za-z0-9:_-.]")
    if errors:
        return None, "INVALID", errors, ignored
    return {"platform": plat, "provider_item_id": pid, "url": url, "account": acct, "published_at": published,
            "published_at_basis": basis, "fetched_at": fetched, "retrieval_status": status, "content_hash": ch,
            "summary": summ, "metrics": metrics or None, "event_id": eid}, None, [], ignored


# ---------- pipeline ----------

def _connect(db_path: Path | str) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path), isolation_level=None)   # explicit BEGIN/COMMIT/SAVEPOINT below
    con.row_factory = sqlite3.Row
    return con


def quarantine_dir() -> Path:
    return private.private_path().parent / "quarantine"


def _quarantine(con, *, run_id, unit: SourceUnit, item_index, reason, errors, payload, now, qdir: Path | None) -> bool:
    psha = canonical_sha(payload)
    ref = None
    if qdir is not None:
        qdir.mkdir(parents=True, exist_ok=True)
        f = qdir / f"{psha}.json"
        if not f.exists():
            f.write_text(json.dumps({"connector": unit.connector, "source_ref": unit.source_ref, "item_index": item_index,
                                     "payload": payload}, default=str))
        ref = f"quarantine/{f.name}"
    key = store._sha(unit.connector, unit.source_ref, unit.unit_sha, item_index)
    cur = con.execute("INSERT OR IGNORE INTO social_ingest_quarantine(quarantine_key,run_id,connector,source_ref,item_index,"
                      "reason_code,errors_json,payload_sha256,private_payload_ref,quarantined_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (key, run_id, unit.connector, unit.source_ref, item_index, reason, json.dumps(errors), psha, ref, now))
    log_event("quarantined", logging.WARNING, run_id=run_id, connector=unit.connector, source_ref=unit.source_ref,
              item_index=item_index, reason=reason, errors=errors, payload_sha256=psha)
    return cur.rowcount == 1


def _persist_item(con, *, clean: dict, env: dict, unit: SourceUnit, run_id: str, index: int, ignored: list[str],
                  stale_before: float, now: float) -> str:
    """Write one valid item. Returns 'created' or 'duplicate'."""
    plat = clean["platform"]
    item_key = store.item_key_for(plat, clean["provider_item_id"], clean["url"])
    event_id = (f"{plat}:{clean['event_id']}" if clean["event_id"] else
                "derived:" + store._sha(plat, item_key, repr(clean["fetched_at"]), clean["content_hash"], clean["retrieval_status"]))
    if con.execute("SELECT 1 FROM social_observation_provenance WHERE event_id=?", (event_id,)).fetchone():
        return "duplicate"
    src = env["source"]
    acct_id = None
    if clean["account"]:
        a = clean["account"]
        acct_id = store.upsert_account(con, plat, handle=a.get("handle"), provider_user_id=a.get("provider_user_id"),
                                       display_name=a.get("display_name"), profile_url=a.get("profile_url"),
                                       seen_at=clean["fetched_at"], now=now)
    res = store.record_observation(
        con, platform=plat, access_mode=src["access_mode"], collector=src["collector"],
        provider_item_id=clean["provider_item_id"], original_url=clean["url"], account_id=acct_id,
        published_at=clean["published_at"], observed_at=clean["fetched_at"], retrieval_status=clean["retrieval_status"],
        summary=clean["summary"], metrics=clean["metrics"], analysis_version=ANALYSIS_VERSION,
        content_hash=clean["content_hash"], now=now)
    if clean["published_at"] is not None and clean["published_at_basis"] == "PARSED_RELATIVE":
        con.execute("UPDATE social_items SET published_at_basis='PARSED_RELATIVE' WHERE item_key=? AND published_at=?",
                    (res["item_key"], clean["published_at"]))
    con.execute("INSERT INTO social_observation_provenance(event_id,observation_id,run_id,connector,source_ref,unit_sha,item_index,"
                "inbound_schema,plan_id,fetched_at,provider_published_at,freshness,visibility,rights_basis,terms_note,"
                "ignored_fields,recorded_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (event_id, res["id"], run_id, unit.connector, unit.source_ref, unit.unit_sha, index, INBOUND_SCHEMA,
                 unit.plan_id, clean["fetched_at"], clean["published_at"],
                 "STALE" if clean["fetched_at"] < stale_before else "FRESH", "PUBLIC", src["rights_basis"],
                 src.get("terms_note"), json.dumps(ignored) if ignored else None, now))
    return "created" if res["created"] else "duplicate"


def _worse(a: str | None, b: str) -> str:
    return b if a is None or HEALTH_RANK.get(b, 4) > HEALTH_RANK.get(a, 4) else a


def ingest(adapter: SourceAdapter, db_path: Path | str, *, now: float | None = None, run_id: str | None = None,
           batch_size: int = 50, budget: Budget | None = None, max_age_hours: float = 12.0,
           qdir: Path | None | bool = True, hooks: dict | None = None) -> dict:
    """Run one ingestion pass. Never raises for a connector or item failure; returns the run summary.

    hooks (tests only): {"after_batch": fn(unit, next_index)} lets a test simulate a crash between batches."""
    t = time.time() if now is None else float(now)
    run_id = run_id or f"ingest_{time.strftime('%Y%m%d_%H%M%S', time.gmtime(t))}_{uuid.uuid4().hex[:6]}"
    budget = budget or Budget()
    hooks = hooks or {}
    qd = quarantine_dir() if qdir is True else (qdir or None)
    batch_size = max(1, int(batch_size))
    stale_before = t - max_age_hours * 3600
    counts = {"units": 0, "units_ok": 0, "units_replayed": 0, "units_unavailable": 0, "units_rejected": 0, "units_failed": 0,
              "items_seen": 0, "created": 0, "duplicates": 0, "quarantined": 0, "stale_items": 0, "budget_stopped": 0}
    health: dict[str, dict] = {}

    con = _connect(db_path)
    try:
        migrate(con)
        con.execute("BEGIN")
        store.register_analysis_version(con, ANALYSIS_VERSION, "collector", "inbound schema " + INBOUND_SCHEMA, now=t)
        con.execute("INSERT INTO social_ingest_runs(run_id,adapter,started_at,status,params_json) VALUES (?,?,?,?,?)",
                    (run_id, adapter.name, t, "RUNNING", json.dumps({"batch_size": batch_size, "max_age_hours": max_age_hours,
                                                                       "budget": budget.to_dict()})))
        con.execute("COMMIT")
        log_event("run_start", run_id=run_id, adapter=adapter.name, batch_size=batch_size)

        def note(conn: str, status: str, msg: str | None = None, items: int = 0):
            h = health.setdefault(conn, {"status": None, "errors": [], "items": 0})
            h["status"] = _worse(h["status"], status)
            h["items"] += items
            if msg and msg not in h["errors"]:
                h["errors"].append(msg)

        stop_all = False
        for unit in adapter.units(budget):
            counts["units"] += 1
            try:
                if stop_all:
                    raise BudgetExceeded("budget reached earlier in this run")
                budget.charge("units")
                outcome = _process_unit(con, unit, run_id=run_id, now=t, batch_size=batch_size, budget=budget,
                                        stale_before=stale_before, qd=qd, counts=counts, hooks=hooks)
            except BudgetExceeded as e:
                stop_all = True
                counts["budget_stopped"] += 1
                note(unit.connector, "DEGRADED", f"not processed: {e}")
                _coverage(con, run_id, unit, "SKIPPED", t, None, f"budget: {e}")
                continue
            except Exception as e:  # one connector's failure never ends the run
                if con.in_transaction:
                    con.execute("ROLLBACK")
                counts["units_failed"] += 1
                msg = f"{type(e).__name__}: {redact(str(e))[:160]}"
                note(unit.connector, "DOWN", "ingest error " + msg)
                log_event("unit_failed", logging.ERROR, run_id=run_id, connector=unit.connector, source_ref=unit.source_ref, error=msg)
                _coverage(con, run_id, unit, "GAP", t, None, "ingest error " + msg)
                continue
            if outcome is None:
                continue  # replayed unit: nothing new learned about the connector
            note(unit.connector, outcome["health"], outcome.get("error"), outcome.get("items", 0))
            if outcome.get("budget_stopped"):
                stop_all = True

        for conn, h in sorted(health.items()):
            store.record_connector_health(con, conn, h["status"], checked_at=t, items_seen=h["items"],
                                          error="; ".join(h["errors"])[:500] or None, now=t)
        bad = counts["units_unavailable"] + counts["units_failed"] + counts["units_rejected"] + counts["budget_stopped"]
        processed = counts["units"] - counts["units_replayed"]
        if processed and bad >= processed and counts["units_ok"] == 0:
            status = "FAILED"
        elif bad or counts["quarantined"] or counts["stale_items"]:
            status = "PARTIAL"
        else:
            status = "OK"
        con.execute("UPDATE social_ingest_runs SET finished_at=?, status=?, counts_json=? WHERE run_id=?",
                    (t, status, json.dumps(counts, sort_keys=True), run_id))
        log_event("run_end", run_id=run_id, status=status, **counts)
        return {"run_id": run_id, "status": status, "counts": counts,
                "health": {k: {"status": v["status"], "items": v["items"], "errors": v["errors"]} for k, v in sorted(health.items())},
                "budget": budget.to_dict()}
    finally:
        con.close()


def _coverage(con, run_id, unit: SourceUnit, status: str, now: float, items: int | None, gap: str | None) -> None:
    store.record_coverage(con, run_id=run_id, connector=unit.connector, platform=unit.platform, scope=unit.source_ref,
                          status=status, checked_at=now, items_seen=items, gap_reason=gap,
                          sampling_note="items as shipped by the collector for this unit; no sampling by the ingester")


_UNIT_COVERAGE = {"RATE_LIMITED": "BLOCKED", "LOGIN_REQUIRED": "BLOCKED", "CAPTCHA": "BLOCKED", "BLOCKED": "BLOCKED"}


def _process_unit(con, unit: SourceUnit, *, run_id, now, batch_size, budget: Budget, stale_before, qd, counts, hooks) -> dict | None:
    if unit.status != "OK":
        counts["units_unavailable"] += 1
        log_event("unit_unavailable", logging.WARNING, run_id=run_id, connector=unit.connector, source_ref=unit.source_ref,
                  status=unit.status, error=unit.error)
        _coverage(con, run_id, unit, _UNIT_COVERAGE.get(unit.status, "GAP"), now, 0, f"{unit.status}: {unit.error or 'no detail'}")
        return {"health": unit.status, "error": unit.error or unit.status}

    cp = con.execute("SELECT * FROM social_ingest_checkpoints WHERE connector=? AND source_ref=? AND unit_sha=?",
                     (unit.connector, unit.source_ref, unit.unit_sha)).fetchone()
    if cp is not None and cp["status"] in ("COMPLETE", "REJECTED"):
        counts["units_replayed"] += 1
        log_event("unit_replayed", run_id=run_id, connector=unit.connector, source_ref=unit.source_ref, checkpoint=cp["status"])
        return None

    env, errs = validate_envelope(unit.body, unit, now)
    if env is None:
        con.execute("BEGIN")
        _quarantine(con, run_id=run_id, unit=unit, item_index=None, reason="SCHEMA", errors=errs, payload=unit.body, now=now, qdir=qd)
        con.execute("INSERT OR REPLACE INTO social_ingest_checkpoints(connector,source_ref,unit_sha,status,next_index,item_count,"
                    "first_run_id,last_run_id,updated_at) VALUES (?,?,?,'REJECTED',0,NULL,COALESCE(?,?),?,?)",
                    (unit.connector, unit.source_ref, unit.unit_sha, cp["first_run_id"] if cp else None, run_id, run_id, now))
        con.execute("COMMIT")
        counts["units_rejected"] += 1
        counts["quarantined"] += 1
        _coverage(con, run_id, unit, "GAP", now, 0, "unit rejected: inbound schema invalid")
        return {"health": "DEGRADED", "error": "unit rejected: inbound schema invalid"}

    items = env["items"]
    start = cp["next_index"] if cp else 0
    if cp is None:
        con.execute("INSERT INTO social_ingest_checkpoints(connector,source_ref,unit_sha,status,next_index,item_count,first_run_id,"
                    "last_run_id,updated_at) VALUES (?,?,?,'IN_PROGRESS',0,?,?,?,?)",
                    (unit.connector, unit.source_ref, unit.unit_sha, len(items), run_id, run_id, now))
    local = {"created": 0, "duplicates": 0, "quarantined": 0, "stale": 0}
    budget_msg = None
    i = start
    while i < len(items):
        batch_end = min(len(items), i + batch_size)
        con.execute("BEGIN")
        try:
            while i < batch_end:
                try:
                    budget.charge("items")
                except BudgetExceeded as e:
                    budget_msg = str(e)
                    break
                counts["items_seen"] += 1
                raw = items[i]
                clean, reason, ierrs, ignored = validate_item(raw, env, now)
                if clean is None:
                    _quarantine(con, run_id=run_id, unit=unit, item_index=i, reason=reason, errors=ierrs, payload=raw, now=now, qdir=qd)
                    local["quarantined"] += 1
                else:
                    con.execute("SAVEPOINT item")
                    try:
                        r = _persist_item(con, clean=clean, env=env, unit=unit, run_id=run_id, index=i, ignored=ignored,
                                          stale_before=stale_before, now=now)
                        con.execute("RELEASE item")
                    except (ValueError, sqlite3.IntegrityError) as e:
                        con.execute("ROLLBACK TO item")
                        con.execute("RELEASE item")
                        _quarantine(con, run_id=run_id, unit=unit, item_index=i, reason="STORE_ERROR",
                                    errors=[f"{type(e).__name__}: {redact(str(e))[:160]}"], payload=raw, now=now, qdir=qd)
                        local["quarantined"] += 1
                    else:
                        local["created" if r == "created" else "duplicates"] += 1
                        if r == "created" and clean["fetched_at"] < stale_before:
                            local["stale"] += 1
                i += 1
            con.execute("UPDATE social_ingest_checkpoints SET next_index=?, last_run_id=?, updated_at=? "
                        "WHERE connector=? AND source_ref=? AND unit_sha=?",
                        (i, run_id, now, unit.connector, unit.source_ref, unit.unit_sha))
            con.execute("COMMIT")
        except Exception:
            if con.in_transaction:
                con.execute("ROLLBACK")
            raise
        if "after_batch" in hooks:
            hooks["after_batch"](unit, i)
        if budget_msg:
            break

    complete = i >= len(items) and budget_msg is None
    if complete:
        con.execute("UPDATE social_ingest_checkpoints SET status='COMPLETE', updated_at=? WHERE connector=? AND source_ref=? AND unit_sha=?",
                    (now, unit.connector, unit.source_ref, unit.unit_sha))
    counts["created"] += local["created"]
    counts["duplicates"] += local["duplicates"]
    counts["quarantined"] += local["quarantined"]
    counts["stale_items"] += local["stale"]
    counts["units_ok"] += 1
    if budget_msg:
        counts["budget_stopped"] += 1
    stale_unit = env["fetched_at"] < stale_before
    problems = []
    if local["quarantined"]:
        problems.append(f"{local['quarantined']} item(s) quarantined")
    if stale_unit or local["stale"]:
        problems.append(f"stale data: fetched {round((now - env['fetched_at']) / 3600, 1)} h before the run")
    if budget_msg:
        problems.append(f"stopped at item {i} of {len(items)}: {budget_msg}")
    log_event("unit_done", run_id=run_id, connector=unit.connector, source_ref=unit.source_ref, next_index=i,
              item_count=len(items), complete=complete, **local)
    _coverage(con, run_id, unit, "PARTIAL" if problems else "COVERED", now, len(items), "; ".join(problems) or None)
    return {"health": "DEGRADED" if problems else "OK", "error": "; ".join(problems) or None,
            "items": local["created"] + local["duplicates"], "budget_stopped": bool(budget_msg)}


# ---------- read-back ----------

def event_record(con: sqlite3.Connection, event_id: str) -> dict | None:
    """Everything stored about one inbound event: provenance, observation, item and account. For verification."""
    p = con.execute("SELECT * FROM social_observation_provenance WHERE event_id=?", (event_id,)).fetchone()
    if p is None:
        return None
    o = con.execute("SELECT * FROM social_observations WHERE id=?", (p["observation_id"],)).fetchone()
    it = con.execute("SELECT * FROM social_items WHERE item_key=?", (o["item_key"],)).fetchone()
    acc = con.execute("SELECT * FROM social_accounts WHERE account_id=?", (o["account_id"],)).fetchone() if o["account_id"] else None
    return {"provenance": dict(p), "observation": dict(o), "item": dict(it), "account": dict(acc) if acc else None}
