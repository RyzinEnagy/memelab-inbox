"""CRUD for the social intelligence tables (schema in memelab/social/schema.py).

Every write is idempotent: calling the same function twice with the same inputs adds nothing the second time.
Known values are never overwritten with None; a NULL column means UNKNOWN.

Safe defaults for the public database:
  - record_observation() takes the source text only to hash it. The text itself is not written to the main
    database. If keep_exact_reason is given, the exact wording goes to the gitignored private store.
  - Summaries must be the lab's own words: a summary that repeats 8 or more consecutive words of the source text
    is refused.
  - metrics are numeric counts only.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
import unicodedata
from datetime import datetime, timezone
from typing import Any

from ..chains import registry
from . import private

EVIDENCE = ("FACT", "INFERENCE", "HEURISTIC", "UNKNOWN")
SOLANA_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
EVM_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
MOVE_RE = re.compile(r"^0x[0-9a-fA-F]{1,64}(::[A-Za-z_][A-Za-z0-9_]*){2}$")
VERBATIM_WORDS = 8
SUMMARY_MAX = 400


# ---------- helpers ----------

def _now(now: float | None) -> float:
    return time.time() if now is None else float(now)


def _sha(*parts: Any) -> str:
    return hashlib.sha256("|".join("" if p is None else str(p) for p in parts).encode()).hexdigest()


def to_utc(value: Any) -> float | None:
    """UTC epoch seconds, or None for UNKNOWN. Accepts epoch seconds or milliseconds, an aware datetime, or an
    ISO-8601 string with an offset or Z. Naive datetimes are refused: their zone is unknown."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("boolean is not a timestamp")
    if isinstance(value, (int, float)):
        v = float(value)
        return v / 1000.0 if v > 1e12 else v
    if isinstance(value, str):
        s = value.strip()
        if re.fullmatch(r"\d+(\.\d+)?", s):
            return to_utc(float(s))
        value = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"naive datetime {value!r}: time zone unknown")
        return value.astimezone(timezone.utc).timestamp()
    raise ValueError(f"unsupported timestamp {value!r}")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def text_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode()).hexdigest()


def normalize_contract(chain: str, contract: str) -> str:
    """Validate an address for its chain family and return the canonical form. Raises ValueError otherwise."""
    if not chain or not contract:
        raise ValueError("contract identity needs both chain and contract")
    c = contract.strip()
    fam = registry.family(chain)
    if fam == "solana" and SOLANA_RE.match(c):
        return c
    if fam == "evm" and EVM_RE.match(c):
        return c.lower()
    if fam == "move" and (MOVE_RE.match(c) or EVM_RE.match(c)):
        return c.lower()
    raise ValueError(f"{contract!r} is not a valid {chain} ({fam}) address")


def _handle(h: str | None) -> str | None:
    if h is None:
        return None
    h = h.strip().lstrip("@")
    return h or None


def _require_version(con: sqlite3.Connection, version: str | None) -> None:
    # db.connect() does not turn on PRAGMA foreign_keys, so references that matter are checked here
    if version is not None and con.execute("SELECT 1 FROM social_analysis_versions WHERE version=?", (version,)).fetchone() is None:
        raise ValueError(f"analysis version {version!r} is not registered")


def _check_evidence(v: str) -> None:
    if v not in EVIDENCE:
        raise ValueError(f"evidence status must be one of {EVIDENCE}")


def check_summary(summary: str | None, source_text: str | None) -> None:
    if summary is None:
        return
    if len(summary) > SUMMARY_MAX:
        raise ValueError(f"summary longer than {SUMMARY_MAX} characters")
    if not source_text:
        return
    words = re.findall(r"\w+", normalize_text(source_text).lower())
    swords = re.findall(r"\w+", normalize_text(summary).lower())
    grams = {tuple(words[i:i + VERBATIM_WORDS]) for i in range(len(words) - VERBATIM_WORDS + 1)}
    for i in range(len(swords) - VERBATIM_WORDS + 1):
        if tuple(swords[i:i + VERBATIM_WORDS]) in grams:
            raise ValueError(f"summary repeats {VERBATIM_WORDS}+ consecutive words of the source text; use own words")


# ---------- analysis versions ----------

def register_analysis_version(con: sqlite3.Connection, version: str, component: str, description: str | None = None,
                              params: dict | None = None, now: float | None = None) -> str:
    con.execute("INSERT OR IGNORE INTO social_analysis_versions(version,component,description,params_json,created_at)"
                " VALUES (?,?,?,?,?)", (version, component, description, json.dumps(params) if params else None, _now(now)))
    return version


# ---------- accounts and traders ----------

def upsert_account(con: sqlite3.Connection, platform: str, handle: str | None = None,
                   provider_user_id: str | None = None, display_name: str | None = None,
                   profile_url: str | None = None, account_kind: str | None = None,
                   identity_status: str | None = None, identity_checked_at: Any = None,
                   catalyst_source_id: str | None = None, seen_at: Any = None, now: float | None = None) -> str:
    platform = platform.strip().lower()
    handle = _handle(handle)
    hn = handle.lower() if handle else None
    pid = str(provider_user_id) if provider_user_id not in (None, "") else None
    if pid is None and hn is None:
        raise ValueError("an account needs a provider user id or a handle")
    t = to_utc(seen_at) or _now(now)
    row = None
    if pid is not None:
        row = con.execute("SELECT * FROM social_accounts WHERE platform=? AND provider_user_id=?", (platform, pid)).fetchone()
    if row is None and hn is not None:
        # a handle-keyed row with no provider id yet is the same account once the id becomes known
        row = con.execute("SELECT * FROM social_accounts WHERE account_id=?", (f"{platform}:handle:{hn}",)).fetchone()
        if row is not None and pid is not None and row["provider_user_id"] not in (None, pid):
            row = None  # same handle, different provider id: the handle was reused by another account
    fields = {"provider_user_id": pid, "handle": handle, "handle_normalized": hn, "display_name": display_name,
              "profile_url": profile_url, "account_kind": account_kind, "identity_status": identity_status,
              "identity_checked_at": to_utc(identity_checked_at), "catalyst_source_id": catalyst_source_id}
    known = {k: v for k, v in fields.items() if v is not None}
    if row is None:
        account_id = f"{platform}:id:{pid}" if pid is not None else f"{platform}:handle:{hn}"
        cols = ["account_id", "platform", "first_seen_at", "last_seen_at"] + list(known)
        con.execute(f"INSERT INTO social_accounts({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                    [account_id, platform, t, t] + list(known.values()))
    else:
        account_id = row["account_id"]
        known["last_seen_at"] = max(t, row["last_seen_at"])
        known["first_seen_at"] = min(t, row["first_seen_at"])
        con.execute(f"UPDATE social_accounts SET {','.join(k + '=?' for k in known)} WHERE account_id=?",
                    list(known.values()) + [account_id])
    if hn is not None:
        con.execute("INSERT INTO social_account_handles(account_id,handle_normalized,first_seen_at,last_seen_at) VALUES (?,?,?,?)"
                    " ON CONFLICT(account_id,handle_normalized) DO UPDATE SET"
                    " first_seen_at=MIN(first_seen_at,excluded.first_seen_at), last_seen_at=MAX(last_seen_at,excluded.last_seen_at)",
                    (account_id, hn, t, t))
    return account_id


def get_account(con: sqlite3.Connection, account_id: str) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM social_accounts WHERE account_id=?", (account_id,)).fetchone()


def upsert_trader(con: sqlite3.Connection, trader_id: str, label: str, status: str | None = None,
                  added_reason: str | None = None, notes: str | None = None, now: float | None = None) -> str:
    t = _now(now)
    con.execute("INSERT INTO social_traders(trader_id,label,status,added_at,added_reason,updated_at,notes)"
                " VALUES (?,?,COALESCE(?,'RESEARCH_SOURCE'),?,?,?,?)"
                " ON CONFLICT(trader_id) DO UPDATE SET label=excluded.label,"
                " status=COALESCE(?,status), added_reason=COALESCE(added_reason,excluded.added_reason),"
                " notes=COALESCE(excluded.notes,notes), updated_at=excluded.updated_at",
                (trader_id, label, status, t, added_reason, t, notes, status))
    return trader_id


def link_trader_account(con: sqlite3.Connection, trader_id: str, account_id: str, link_basis: str,
                        evidence_status: str, confidence: str = "UNKNOWN", observation_id: int | None = None,
                        now: float | None = None) -> None:
    _check_evidence(evidence_status)
    t = _now(now)
    con.execute("INSERT INTO social_trader_accounts(trader_id,account_id,link_basis,evidence_status,confidence,linked_at)"
                " VALUES (?,?,?,?,?,?) ON CONFLICT(trader_id,account_id) DO UPDATE SET"
                " link_basis=excluded.link_basis, evidence_status=excluded.evidence_status, confidence=excluded.confidence",
                (trader_id, account_id, link_basis, evidence_status, confidence, t))
    if observation_id is not None:
        link_evidence(con, "TRADER_ACCOUNT", f"{trader_id}|{account_id}", observation_id, "SOURCE", now=t)


# ---------- items and observations ----------

def item_key_for(platform: str, provider_item_id: str | None, original_url: str | None) -> str:
    platform = platform.strip().lower()
    if provider_item_id not in (None, ""):
        return f"{platform}:{provider_item_id}"
    if original_url:
        return f"{platform}:url:{_sha(original_url.strip())[:24]}"
    raise ValueError("an item needs a provider item id or an original URL")


def upsert_item(con: sqlite3.Connection, platform: str, provider_item_id: str | None = None,
                original_url: str | None = None, account_id: str | None = None, published_at: Any = None,
                published_at_basis: str | None = None, observed_at: float | None = None,
                now: float | None = None) -> tuple[str, list[str]]:
    """Create or fill the item row. Returns (item_key, conflicts). A later, different published_at is not written
    over the first one; it is returned as a conflict for the caller to record."""
    platform = platform.strip().lower()
    key = item_key_for(platform, provider_item_id, original_url)
    pub = to_utc(published_at)
    basis = published_at_basis or ("PROVIDER" if pub is not None else "UNKNOWN")
    if pub is None:
        basis = "UNKNOWN"
    row = con.execute("SELECT * FROM social_items WHERE item_key=?", (key,)).fetchone()
    conflicts: list[str] = []
    if row is None:
        con.execute("INSERT INTO social_items(item_key,platform,provider_item_id,account_id,original_url,published_at,"
                    "published_at_basis,first_observed_at,first_ingested_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (key, platform, provider_item_id or None, account_id, original_url, pub, basis, observed_at, _now(now)))
        return key, conflicts
    if row["account_id"] and account_id and row["account_id"] != account_id:
        conflicts.append(f"account_id {row['account_id']} vs {account_id}")
    if row["published_at"] is not None and pub is not None and abs(row["published_at"] - pub) > 1:
        conflicts.append(f"published_at {row['published_at']} vs {pub}")
    first_obs = row["first_observed_at"]
    if observed_at is not None and (first_obs is None or observed_at < first_obs):
        first_obs = observed_at
    con.execute("UPDATE social_items SET account_id=COALESCE(account_id,?), original_url=COALESCE(original_url,?),"
                " published_at=COALESCE(published_at,?),"
                " published_at_basis=CASE WHEN published_at IS NULL THEN ? ELSE published_at_basis END,"
                " first_observed_at=? WHERE item_key=?",
                (account_id, original_url, pub, basis, first_obs, key))
    return key, conflicts


def record_observation(con: sqlite3.Connection, *, platform: str, access_mode: str, collector: str,
                       provider_item_id: str | None = None, original_url: str | None = None,
                       account_id: str | None = None, published_at: Any = None, observed_at: Any = None,
                       retrieval_status: str = "OK", text: str | None = None, summary: str | None = None,
                       metrics: dict | None = None, analysis_version: str | None = None,
                       keep_exact_reason: str | None = None, error: str | None = None,
                       now: float | None = None, private_path=None) -> dict:
    """Append one sighting. Returns {"id", "item_key", "created", "conflicts"}. Same inputs twice -> created False."""
    obs = to_utc(observed_at)
    if metrics is not None:
        bad = [k for k, v in metrics.items() if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)))]
        if bad:
            raise ValueError(f"metrics must be numeric counts; non-numeric keys: {bad}")
    check_summary(summary, text)
    _require_version(con, analysis_version)
    chash = text_hash(text) if text else None
    key, conflicts = upsert_item(con, platform, provider_item_id, original_url, account_id, published_at,
                                 observed_at=obs, now=now)
    private_ref = None
    if keep_exact_reason:
        if not text:
            raise ValueError("keep_exact_reason given without text")
        private_ref = private.put(chash, normalize_text(text), keep_exact_reason, platform=platform,
                                  original_url=original_url, now=now, path=private_path)
    retained = ("SUMMARY_AND_PRIVATE" if summary and private_ref else "PRIVATE" if private_ref
                else "SUMMARY" if summary else "NONE")
    okey = _sha(key, "UNKNOWN" if obs is None else repr(obs), chash, retrieval_status)
    cur = con.execute(
        "INSERT OR IGNORE INTO social_observations(observation_key,item_key,account_id,observed_at,observed_at_basis,"
        "ingested_at,access_mode,collector,retrieval_status,content_hash,retained_content,summary,private_ref,"
        "metrics_json,analysis_version,error) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (okey, key, account_id, obs, "COLLECTOR" if obs is not None else "UNKNOWN", _now(now), access_mode, collector,
         retrieval_status, chash, retained, summary, private_ref,
         json.dumps(metrics, sort_keys=True) if metrics else None, analysis_version, error))
    created = cur.rowcount == 1
    oid = cur.lastrowid if created else con.execute(
        "SELECT id FROM social_observations WHERE observation_key=?", (okey,)).fetchone()[0]
    return {"id": oid, "item_key": key, "created": created, "conflicts": conflicts}


def observations_for(con: sqlite3.Connection, item_key: str) -> list[sqlite3.Row]:
    return con.execute("SELECT * FROM social_observations WHERE item_key=? ORDER BY COALESCE(observed_at, ingested_at), id",
                       (item_key,)).fetchall()


# ---------- token references ----------

def upsert_token_ref(con: sqlite3.Connection, chain: str | None = None, contract: str | None = None,
                     symbol: str | None = None, name: str | None = None, official_link: bool = False,
                     now: float | None = None) -> int:
    """A contract address is identity; a ticker or name alone is a separate, unresolved reference."""
    if contract:
        c = normalize_contract(chain, contract)
        ch = chain.strip().lower()
        kind = "OFFICIAL_LINK" if official_link else "CONTRACT_ADDRESS"
        key = f"ca:{ch}:{c}"
        con.execute("INSERT OR IGNORE INTO social_token_refs(ref_key,ref_kind,chain,contract,symbol_seen,first_seen_at)"
                    " VALUES (?,?,?,?,?,?)", (key, kind, ch, c, symbol, _now(now)))
        if official_link:
            con.execute("UPDATE social_token_refs SET ref_kind='OFFICIAL_LINK' WHERE ref_key=?", (key,))
    elif symbol:
        key = f"ticker:{symbol.strip().lstrip('$').upper()}"
        con.execute("INSERT OR IGNORE INTO social_token_refs(ref_key,ref_kind,chain,contract,symbol_seen,first_seen_at)"
                    " VALUES (?,'TICKER_ONLY',NULL,NULL,?,?)", (key, symbol, _now(now)))
    elif name:
        key = f"name:{normalize_text(name).lower()}"
        con.execute("INSERT OR IGNORE INTO social_token_refs(ref_key,ref_kind,chain,contract,symbol_seen,first_seen_at)"
                    " VALUES (?,'NAME_ONLY',NULL,NULL,NULL,?)", (key, _now(now)))
    else:
        raise ValueError("a token reference needs a contract, a ticker or a name")
    return con.execute("SELECT ref_id FROM social_token_refs WHERE ref_key=?", (key,)).fetchone()[0]


# ---------- claims and evidence ----------

def add_claim(con: sqlite3.Connection, *, claim_type: str, analysis_version: str, item_key: str | None = None,
              account_id: str | None = None, token_ref_id: int | None = None, narrative_id: str | None = None,
              direction: str = "UNKNOWN", claimed_at: Any = None, summary: str | None = None,
              evidence_status: str = "INFERENCE", observation_id: int | None = None,
              now: float | None = None) -> dict:
    """Record what a post asserts. The claim's existence is evidence of what was said, not of its truth.
    Re-running a newer analysis_version adds a new claim row; old versions are kept for reprocessing audits."""
    _check_evidence(evidence_status)
    check_summary(summary, None)
    _require_version(con, analysis_version)
    t = _now(now)
    key = _sha(item_key, account_id, claim_type, token_ref_id, narrative_id, direction, analysis_version)
    cur = con.execute(
        "INSERT OR IGNORE INTO social_claims(claim_key,item_key,account_id,claim_type,token_ref_id,narrative_id,direction,"
        "claimed_at,extracted_at,analysis_version,summary,evidence_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (key, item_key, account_id, claim_type, token_ref_id, narrative_id, direction, to_utc(claimed_at), t,
         analysis_version, summary, evidence_status))
    created = cur.rowcount == 1
    cid = cur.lastrowid if created else con.execute("SELECT id FROM social_claims WHERE claim_key=?", (key,)).fetchone()[0]
    if observation_id is not None:
        link_evidence(con, "CLAIM", str(cid), observation_id, "SOURCE", now=t)
    return {"id": cid, "created": created}


def relate_claims(con: sqlite3.Connection, claim_id: int, other_claim_id: int, relation: str,
                  note: str | None = None, now: float | None = None) -> None:
    con.execute("INSERT OR IGNORE INTO social_claim_relations(claim_id,other_claim_id,relation,noted_at,note) VALUES (?,?,?,?,?)",
                (claim_id, other_claim_id, relation, _now(now), note))


def set_claim_status(con: sqlite3.Connection, claim_id: int, status: str, now: float | None = None) -> None:
    con.execute("UPDATE social_claims SET claim_status=?, status_updated_at=? WHERE id=?", (status, _now(now), claim_id))


def link_evidence(con: sqlite3.Connection, target_type: str, target_id: str, observation_id: int, role: str,
                  now: float | None = None) -> None:
    con.execute("INSERT OR IGNORE INTO social_evidence_links(target_type,target_id,observation_id,role,linked_at) VALUES (?,?,?,?,?)",
                (target_type, str(target_id), observation_id, role, _now(now)))


def conflicting_claims(con: sqlite3.Connection, token_ref_id: int) -> list[tuple[int, int]]:
    """Pairs of claims about one token whose directions disagree (LONG vs SHORT/EXIT) or that are marked CONTRADICTS."""
    rows = con.execute("SELECT id, direction FROM social_claims WHERE token_ref_id=? AND claim_type='CALL' ORDER BY id",
                       (token_ref_id,)).fetchall()
    out = set()
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if {a["direction"], b["direction"]} in ({"LONG", "SHORT"}, {"LONG", "EXIT"}):
                out.add((a["id"], b["id"]))
    for r in con.execute("SELECT r.claim_id, r.other_claim_id FROM social_claim_relations r JOIN social_claims c ON c.id=r.claim_id"
                         " WHERE r.relation='CONTRADICTS' AND c.token_ref_id=?", (token_ref_id,)):
        out.add(tuple(sorted((r[0], r[1]))))
    return sorted(out)


# ---------- wallet attribution ----------

def assert_wallet(con: sqlite3.Connection, *, subject_type: str, subject_id: str, chain: str, wallet_address: str,
                  assertion: str, evidence_status: str, basis: str, confidence: str = "UNKNOWN",
                  asserted_at: Any = None, analysis_version: str | None = None,
                  observation_id: int | None = None, now: float | None = None) -> dict:
    """Append a wallet-attribution assertion. The subject (trader or social account) must already exist and the
    wallet must be a valid address on that chain: a social id or handle can never be stored as a wallet."""
    _check_evidence(evidence_status)
    if not basis:
        raise ValueError("a wallet attribution needs a basis")
    _require_version(con, analysis_version)
    table, col = {"TRADER": ("social_traders", "trader_id"), "ACCOUNT": ("social_accounts", "account_id")}[subject_type]
    if con.execute(f"SELECT 1 FROM {table} WHERE {col}=?", (subject_id,)).fetchone() is None:
        raise ValueError(f"unknown {subject_type.lower()} {subject_id!r}")
    w = normalize_contract(chain, wallet_address)
    ch = chain.strip().lower()
    at = to_utc(asserted_at) or _now(now)
    key = _sha(subject_type, subject_id, ch, w, assertion, evidence_status, confidence, basis, observation_id)
    cur = con.execute(
        "INSERT OR IGNORE INTO social_wallet_attributions(assertion_key,subject_type,subject_id,chain,wallet_address,assertion,"
        "evidence_status,confidence,basis,asserted_at,analysis_version) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (key, subject_type, subject_id, ch, w, assertion, evidence_status, confidence, basis, at, analysis_version))
    created = cur.rowcount == 1
    aid = cur.lastrowid if created else con.execute(
        "SELECT id FROM social_wallet_attributions WHERE assertion_key=?", (key,)).fetchone()[0]
    if observation_id is not None:
        link_evidence(con, "WALLET_ATTRIBUTION", str(aid), observation_id, "SOURCE", now=now)
    return {"id": aid, "created": created}


def current_wallet_view(con: sqlite3.Connection, chain: str, wallet_address: str) -> list[dict]:
    """Latest assertion per subject for one wallet. History stays in the table; this is the derived view."""
    w = normalize_contract(chain, wallet_address)
    rows = con.execute("SELECT * FROM social_wallet_attributions WHERE chain=? AND wallet_address=? ORDER BY asserted_at, id",
                       (chain.strip().lower(), w)).fetchall()
    latest: dict[tuple, dict] = {}
    for r in rows:
        latest[(r["subject_type"], r["subject_id"])] = dict(r)
    return list(latest.values())


# ---------- connector health and coverage ----------

def record_connector_health(con: sqlite3.Connection, connector: str, status: str, checked_at: Any = None,
                            items_seen: int | None = None, latency_ms: float | None = None,
                            error: str | None = None, now: float | None = None) -> bool:
    t = to_utc(checked_at) or _now(now)
    cur = con.execute("INSERT OR IGNORE INTO social_connector_health(connector,checked_at,status,items_seen,latency_ms,error)"
                      " VALUES (?,?,?,?,?,?)", (connector, t, status, items_seen, latency_ms, error))
    return cur.rowcount == 1


def latest_connector_health(con: sqlite3.Connection, connector: str) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM social_connector_health WHERE connector=? ORDER BY checked_at DESC LIMIT 1",
                       (connector,)).fetchone()


def record_coverage(con: sqlite3.Connection, *, run_id: str, connector: str, platform: str, scope: str, status: str,
                    window_start: Any = None, window_end: Any = None, checked_at: Any = None,
                    items_seen: int | None = None, gap_reason: str | None = None,
                    sampling_note: str | None = None, now: float | None = None) -> bool:
    if status in ("GAP", "BLOCKED", "PARTIAL") and not gap_reason:
        raise ValueError("a gap, block or partial coverage record needs a gap_reason")
    key = _sha(run_id, connector, scope)
    cur = con.execute(
        "INSERT OR IGNORE INTO social_coverage(coverage_key,run_id,connector,platform,scope,window_start,window_end,checked_at,"
        "status,items_seen,gap_reason,sampling_note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (key, run_id, connector, platform, scope, to_utc(window_start), to_utc(window_end),
         to_utc(checked_at) or _now(now), status, items_seen, gap_reason, sampling_note))
    return cur.rowcount == 1
