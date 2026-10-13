"""Shared pieces for the optional Reddit and Farcaster adapters (Phase 19).

  HttpResponse / FixtureTransport   recorded synthetic exchanges, matched on method, path and exact parameters
  RequestGuard                      per-run request cap and per-request cost estimate, one social_api_spend row per call
  cursor helpers                    social_source_cursors, same table and columns the X adapter uses
  TextSink + extract_after_ingest   optional in-memory hand-off of post text to claim extraction; text is never written

The text sink exists so a run can go source -> storage -> claim -> narrative without keeping wording anywhere:
the adapter hashes the text for the inbound item (D-016) and, only when the caller asked for extraction, keeps
{(platform, provider id, content hash): text} in memory until ingest() has stored the observation. Extraction then
checks the text against the stored hash (Phase 06) and the sink is cleared. Nothing in this module writes text.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import store
from .ingest import TransientError, redact


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def billing_day(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")


@dataclass
class HttpResponse:
    status: int
    headers: dict
    body: Any
    received_at: float


class FixtureMiss(Exception):
    """A request the recorded fixture does not contain: the contract changed or the test is wrong. Not transient."""


class FixtureTransport:
    """Replays recorded synthetic exchanges for one adapter. An exchange listed twice for the same request is served
    in order (a 503 then a 200). 'raise' simulates a transport error; '{secret}' in its text is replaced with the
    secret the adapter sent, to prove redaction."""

    def __init__(self, fixture: dict | str | Path, schema: str):
        if not isinstance(fixture, dict):
            fixture = json.loads(Path(fixture).read_text())
        if fixture.get("schema") != schema:
            raise ValueError(f"fixture schema must be {schema}")
        self.exchanges = fixture["exchanges"]
        self.used: set[int] = set()
        self.calls: list[dict] = []

    @staticmethod
    def _norm(params: dict | None) -> dict:
        return {str(k): str(v) for k, v in (params or {}).items()}

    def request(self, method: str, path: str, params: dict | None, secret: str | None) -> HttpResponse:
        p = self._norm(params)
        self.calls.append({"method": method, "path": path, "params": p, "auth_sent": bool(secret)})
        for i, ex in enumerate(self.exchanges):
            rq = ex["request"]
            if i in self.used or rq.get("method", "GET") != method or rq["path"] != path or self._norm(rq.get("params")) != p:
                continue
            self.used.add(i)
            if "raise" in ex:
                raise TransientError(ex["raise"].replace("{secret}", secret or ""))
            rs = ex["response"]
            return HttpResponse(int(rs["status"]), {k.lower(): str(v) for k, v in (rs.get("headers") or {}).items()},
                                rs.get("body"), store.to_utc(ex["recorded_at"]))
        raise FixtureMiss(f"no recorded exchange for {method} {path} with parameters {sorted(p)}")


class RequestGuard:
    """Caps requests per run and writes one social_api_spend row per call (estimate; the provider is the bill).
    Reddit's free tier and a self-hosted Farcaster node cost nothing per request, so the estimate is usually 0;
    the row still proves when, where and how often the lab called a provider, and only mode='live' rows count."""

    def __init__(self, con, *, connector_prefix: str, mode: str, max_requests: int, usd_per_request: float = 0.0,
                 max_usd_per_run: float | None = None):
        self.con, self.prefix, self.mode = con, connector_prefix, mode
        self.max_requests, self.usd = max(0, int(max_requests)), max(0.0, float(usd_per_request))
        self.max_usd = max_usd_per_run
        self.count, self.spent = 0, 0.0

    def check(self) -> str | None:
        if self.count >= self.max_requests:
            return f"request cap {self.max_requests} per run reached"
        if self.max_usd is not None and self.spent + self.usd > self.max_usd + 1e-12:
            return f"cost cap ${self.max_usd:.3f} per run would be exceeded"
        return None

    def record(self, *, connector: str, run_id: str | None, endpoint: str, status: int, resources: dict, now: float) -> float:
        self.count += 1
        cost = self.usd if status and status < 500 else 0.0
        self.con.execute("INSERT INTO social_api_spend(connector,run_id,endpoint,http_status,billing_day,resources_json,est_cost_usd,"
                         "mode,requested_at) VALUES (?,?,?,?,?,?,?,?,?)",
                         (connector, run_id, endpoint, status, billing_day(now), json.dumps(resources, sort_keys=True), cost,
                          self.mode, now))
        self.con.commit()
        self.spent += cost
        return cost


# ---------- cursors (social_source_cursors) ----------

def get_cursor(con, connector: str, scope: str):
    return con.execute("SELECT * FROM social_source_cursors WHERE connector=? AND scope=?", (connector, scope)).fetchone()


def save_cursor(con, connector: str, scope: str, now: float, **kw) -> None:
    row = get_cursor(con, connector, scope)
    cur = dict(row) if row else {"provider_scope_id": None, "newest_id": None, "last_success_at": None,
                                 "rate_limit_reset_at": None, "last_status": "UNKNOWN"}
    cur.update(kw)
    con.execute("INSERT INTO social_source_cursors(connector,scope,provider_scope_id,newest_id,last_success_at,last_attempt_at,"
                "last_status,rate_limit_reset_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(connector,scope) DO UPDATE SET"
                " provider_scope_id=excluded.provider_scope_id, newest_id=excluded.newest_id, last_success_at=excluded.last_success_at,"
                " last_attempt_at=excluded.last_attempt_at, last_status=excluded.last_status,"
                " rate_limit_reset_at=excluded.rate_limit_reset_at, updated_at=excluded.updated_at",
                (connector, scope, cur["provider_scope_id"], cur["newest_id"], cur["last_success_at"], now,
                 cur.get("last_status") or "UNKNOWN", cur["rate_limit_reset_at"], now))
    con.commit()


def units_committed(con, units) -> bool:
    for u in units:
        r = con.execute("SELECT status FROM social_ingest_checkpoints WHERE connector=? AND source_ref=? AND unit_sha=?",
                        (u.connector, u.source_ref, u.unit_sha)).fetchone()
        if r is None or r[0] != "COMPLETE":
            return False
    return True


def connect(db_path: Path | str):
    import sqlite3
    from .schema import migrate
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    migrate(con)
    return con


def scrub(s: str, *secrets: str | None) -> str:
    for x in secrets:
        if x:
            s = s.replace(x, "[REDACTED]")
    return redact(s)


# ---------- optional in-memory text hand-off to claim extraction ----------

@dataclass
class TextSink:
    """Holds post text in memory for one run, keyed by (platform, provider_item_id, content_hash). Never persisted;
    repr() shows only the count. Capped so a large run cannot hold unbounded text."""
    max_items: int = 500
    _texts: dict = field(default_factory=dict, repr=False)

    def put(self, platform: str, provider_item_id: str, content_hash: str, text: str) -> None:
        if len(self._texts) < self.max_items:
            self._texts[(platform, provider_item_id, content_hash)] = text

    def __len__(self) -> int:
        return len(self._texts)

    def __repr__(self) -> str:
        return f"TextSink(items={len(self._texts)})"

    def items(self):
        return list(self._texts.items())

    def clear(self) -> None:
        self._texts.clear()


def extract_after_ingest(db_path: Path | str, sink: TextSink, *, now: float, bodies: dict | None = None,
                         provider=None, provider_reason: str | None = None) -> dict:
    """Run Phase 06 extraction on the observations this run stored, with the text held in the sink. Without a model
    only deterministic token-reference claims are made and the model part is analysis_unavailable (D-036, D-037).
    The sink is cleared afterwards, also on error."""
    import sqlite3
    from . import extraction as EX
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    out = {"texts_held": len(sink), "extracted": 0, "claims": 0, "skipped_no_observation": 0, "skipped_already_extracted": 0,
           "item_keys": []}
    try:
        for (platform, pid, chash), text in sink.items():
            ikey = store.item_key_for(platform, pid, None)
            obs = con.execute("SELECT id FROM social_observations WHERE item_key=? AND content_hash=? ORDER BY id DESC LIMIT 1",
                              (ikey, chash)).fetchone()
            if obs is None:
                out["skipped_no_observation"] += 1
                continue
            # a re-sighting of the same words (cursor overlap, recheck) was already analysed: do not make a second claim set
            if con.execute("SELECT 1 FROM social_claim_extractions WHERE item_key=? AND content_hash=? AND extractor='deterministic'"
                           " AND status='ok' AND observation_id<>?", (ikey, chash, obs["id"])).fetchone():
                out["skipped_already_extracted"] += 1
                continue
            res = EX.extract_observation(con, obs["id"], text, provider=provider, provider_reason=provider_reason,
                                         bodies=bodies, now=now)
            con.commit()
            out["extracted"] += 1
            out["claims"] += sum(len((res.get(k) or {}).get("claim_ids") or []) for k in ("deterministic", "model"))
            out["item_keys"].append(ikey)
    finally:
        sink.clear()
        con.close()
    out["item_keys"] = sorted(set(out["item_keys"]))
    return out


# ---------- deletion compliance shared by the Reddit and Discord adapters ----------

def purge_gone_items(con, platform: str, *, private_path=None) -> dict:
    """Erase what the lab derived from items of one platform that have a DELETED or NOT_FOUND sighting. Ids and the
    gone sighting stay (they say that something existed and is gone, nothing more). Per gone item: content hashes,
    summaries, metrics and private refs on every observation; versions; claim spans, claim summaries, extraction outputs
    and their hashes; private copies of the text; the link to its author. Narrative snapshots keep their dated counts.
    Idempotent. The caller commits. Moved here from reddit_api.purge_deleted in Phase 20 (behaviour unchanged)."""
    gone = [r[0] for r in con.execute(
        "SELECT DISTINCT i.item_key FROM social_items i JOIN social_observations o ON o.item_key=i.item_key "
        "WHERE i.platform=? AND o.retrieval_status IN ('DELETED','NOT_FOUND')", (platform,))]
    return clear_item_keys(con, gone, private_path=private_path)


def clear_item_keys(con, keys, *, private_path=None) -> dict:
    """The erasure step of purge_gone_items for an explicit list of item keys (Phase 21: the YouTube 30-day expiry
    uses it too). Same per-item erasure and counting. The caller commits."""
    from . import private
    out = {"items_purged": 0, "observations_cleared": 0, "claims_cleared": 0, "private_rows_deleted": 0}
    hashes = set()
    for key in keys:
        rows = con.execute("SELECT id, content_hash FROM social_observations WHERE item_key=? AND (content_hash IS NOT NULL "
                           "OR summary IS NOT NULL OR metrics_json IS NOT NULL OR private_ref IS NOT NULL)", (key,)).fetchall()
        hashes.update(r[1] for r in rows if r[1])
        for ext in con.execute("SELECT content_hash FROM social_claim_extractions WHERE item_key=?", (key,)):
            if ext[0] and len(ext[0]) == 64 and ext[0] != "0" * 64:
                hashes.add(ext[0])
        if rows:
            out["observations_cleared"] += con.execute(
                "UPDATE social_observations SET content_hash=NULL, summary=NULL, metrics_json=NULL, private_ref=NULL, "
                "retained_content='NONE' WHERE item_key=?", (key,)).rowcount
        con.execute("DELETE FROM social_item_versions WHERE item_key=?", (key,))
        claim_ids = [r[0] for r in con.execute("SELECT id FROM social_claims WHERE item_key=?", (key,))]
        spans = 0
        for cid in claim_ids:
            spans += con.execute("DELETE FROM social_claim_spans WHERE claim_id=?", (cid,)).rowcount
        n = con.execute("UPDATE social_claims SET summary=NULL WHERE item_key=? AND summary IS NOT NULL", (key,)).rowcount
        e = con.execute("UPDATE social_claim_extractions SET content_hash=?, output_json=NULL, output_sha=NULL, cache_key=NULL "
                        "WHERE item_key=? AND (content_hash<>? OR output_json IS NOT NULL)", ("0" * 64, key, "0" * 64)).rowcount
        out["claims_cleared"] += n + e
        for tbl in ("social_items", "social_observations", "social_claims"):
            con.execute(f"UPDATE {tbl} SET account_id=NULL WHERE item_key=? AND account_id IS NOT NULL", (key,))
        if rows or e or n or spans:          # counted only when something was erased, so a repeat run reports 0
            out["items_purged"] += 1
    if hashes:
        with private.connect(private_path) as pcon:
            for h in hashes:
                out["private_rows_deleted"] += pcon.execute("DELETE FROM private_content WHERE content_hash=?", (h,)).rowcount
    return out


def erase_accounts(con, targets: dict) -> int:
    """targets: {account_id: provider_user_id}. Deletes each account row and its handle history and unlinks it from
    items, observations, claims and reference author ids. The caller commits."""
    n = 0
    for aid, puid in sorted(targets.items()):
        for tbl in ("social_items", "social_observations", "social_claims"):
            con.execute(f"UPDATE {tbl} SET account_id=NULL WHERE account_id=?", (aid,))
        con.execute("DELETE FROM social_account_handles WHERE account_id=?", (aid,))
        con.execute("DELETE FROM social_accounts WHERE account_id=?", (aid,))
        if puid:
            con.execute("UPDATE social_item_refs SET referenced_author_id=NULL WHERE referenced_author_id=?", (puid,))
        n += 1
    return n


def now_clock(now: float | None) -> Callable[[], float]:
    return (lambda: now) if now is not None else time.time
