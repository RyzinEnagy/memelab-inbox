"""Phase 08: persistent source and trader registry (migration 8, tables social_registry_*).

The registry holds identities and the evidence that links them. It does not rank anyone, it does not assume that a
profitable wallet belongs to a good commentator, and it never merges two identities because their names match.

Identities (entity kinds and edge types), see docs/social-intelligence/REGISTRY_08.md for the full table:
  SOCIAL_ACCOUNT          a platform account, keyed by the Phase 01 social account id (provider id when known)
  OBSERVED_WALLET         an address seen in data; seeing it says nothing about who owns it
  LEADERBOARD_CANDIDATE   one line of a third-party list, keyed by list and identifier; a claim by that list
  SOURCE_ORGANIZATION     who publishes a list or runs accounts
  SOCIAL_NETWORK          a named community or cluster of accounts
  self-disclosed public wallet      = link WALLET_SELF_DISCLOSED (an account says the wallet is its own)
  verified attribution assertion    = link WALLET_ON_CHAIN_PROOF or an independent WALLET_THIRD_PARTY_LABEL, reviewed

Rules enforced here (each has a test in tests/test_social_registry.py):
  - no merge by name: SAME_OPERATOR needs a reviewed link with a direct reference, and name similarity is not a basis;
  - a self-claimed wallet stays SELF_CLAIMED until a reviewed, independent label or a reviewed on-chain proof exists;
  - categories are separate: being a wallet candidate says nothing about being an information source, and the
    categories that need evidence refuse to be confirmed without it;
  - no field accepts a "best trader" style assertion, and no query orders or scores by rank;
  - fixtures carry a label, cannot be set to WATCH, and cannot be linked to real entities;
  - evidence from a stale or undated capture cannot approve a follow unless a reason is recorded;
  - everything a person decides is written to social_registry_reviews.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import re
import sqlite3
import time
from typing import Any

from ..chains import registry as chain_registry
from . import store

VERSION = "registry-v1"
KINDS = ("SOCIAL_ACCOUNT", "OBSERVED_WALLET", "LEADERBOARD_CANDIDATE", "SOURCE_ORGANIZATION", "SOCIAL_NETWORK")
CATEGORIES = ("PROFITABLE_TRADING_CLAIMANT", "VERIFIED_WALLET_CANDIDATE", "INFORMATION_ORIGINATOR", "ANALYTICAL_SOURCE",
              "AMPLIFIER", "PROMOTER_HIGH_CONFLICT")
WATCH = ("NONE", "WATCH", "PAUSED", "DROPPED")
PLATFORMS = ("x", "telegram", "youtube", "discord", "farcaster", "other")
LEVELS = ("NONE", "THIRD_PARTY_LABELED", "SELF_CLAIMED", "CORROBORATED", "DISPUTED")
WALLET_LINKS = ("WALLET_SELF_DISCLOSED", "WALLET_THIRD_PARTY_LABEL", "WALLET_ON_CHAIN_PROOF", "WALLET_DISPUTED")
DEFAULT_MAX_AGE = 7 * 86400
EVIDENCE_MAX_AGE = 30 * 86400
CONFIDENCES = ("HIGH", "MODERATE", "LOW", "UNKNOWN")

# what each link type may connect, and which bases it accepts
LINK_RULES: dict[str, dict] = {
    "WALLET_SELF_DISCLOSED": {"from": ("SOCIAL_ACCOUNT",), "to": ("OBSERVED_WALLET",), "basis": ("SELF_STATEMENT",), "ref": True},
    "WALLET_THIRD_PARTY_LABEL": {"from": ("SOCIAL_ACCOUNT",), "to": ("OBSERVED_WALLET",),
                                 "basis": ("THIRD_PARTY_STATEMENT", "LEADERBOARD_LISTING"), "ref": True},
    "WALLET_ON_CHAIN_PROOF": {"from": ("SOCIAL_ACCOUNT",), "to": ("OBSERVED_WALLET",), "basis": ("ON_CHAIN_PROOF",), "ref": True},
    "WALLET_DISPUTED": {"from": ("SOCIAL_ACCOUNT",), "to": ("OBSERVED_WALLET",),
                        "basis": ("THIRD_PARTY_STATEMENT", "REVIEWER_JUDGMENT", "ON_CHAIN_PROOF"), "ref": True},
    "SAME_OPERATOR": {"from": ("SOCIAL_ACCOUNT",), "to": ("SOCIAL_ACCOUNT",),
                      "basis": ("PLATFORM_LINK", "SELF_STATEMENT", "ON_CHAIN_PROOF", "REVIEWER_JUDGMENT"), "ref": True},
    "OPERATED_BY_ORG": {"from": ("SOCIAL_ACCOUNT",), "to": ("SOURCE_ORGANIZATION",),
                        "basis": ("PLATFORM_LINK", "SELF_STATEMENT", "THIRD_PARTY_STATEMENT", "REVIEWER_JUDGMENT"), "ref": True},
    "MEMBER_OF_NETWORK": {"from": ("SOCIAL_ACCOUNT", "SOURCE_ORGANIZATION"), "to": ("SOCIAL_NETWORK",),
                          "basis": ("PLATFORM_LINK", "SELF_STATEMENT", "THIRD_PARTY_STATEMENT", "REVIEWER_JUDGMENT"), "ref": True},
    "LISTED_BY": {"from": ("LEADERBOARD_CANDIDATE",), "to": ("SOURCE_ORGANIZATION",), "basis": ("LEADERBOARD_LISTING",), "ref": False},
    "OBSERVED_AS": {"from": ("LEADERBOARD_CANDIDATE",), "to": ("OBSERVED_WALLET", "SOCIAL_ACCOUNT"),
                    "basis": ("LEADERBOARD_LISTING",), "ref": False},
}
NAME_BASES = {"NAME_SIMILARITY", "SAME_NAME", "NAME_MATCH", "DISPLAY_NAME", "SCREEN_NAME"}

_SUPERLATIVE = re.compile(
    r"(?:\b(?:best|top|greatest|number one|no\.\s?1)\b|#\s?1\b).{0,24}\b(?:trader|caller|wallet|investor|analyst)s?\b"
    r"|\bmost profitable\b|\bproven (winner|profit\w*)\b|\bguaranteed\b|\bnever loses\b|\bverified profitable\b"
    r"|\b(trader|caller)s? to follow\b", re.I)
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_REF = re.compile(r"^(https://\S{4,290}|listing:\d{1,12}|observation:\d{1,12}|tx:[A-Za-z0-9]{20,120}|repo:\S{3,200}"
                  r"|narrative:\d+:\S{3,120}:\d+)$")


@contextlib.contextmanager
def savepoint(con, name: str = "reg_sp"):
    """All-or-nothing block that also works inside a caller's transaction."""
    con.execute(f"SAVEPOINT {name}")
    try:
        yield
    except BaseException:
        con.execute(f"ROLLBACK TO {name}")
        con.execute(f"RELEASE {name}")
        raise
    con.execute(f"RELEASE {name}")


def _now(now: float | None) -> float:
    return time.time() if now is None else float(now)


def _sha(*parts: Any) -> str:
    return hashlib.sha256("|".join("" if p is None else str(p) for p in parts).encode()).hexdigest()


def clean_text(value: str | None, field: str, maxlen: int) -> str | None:
    """Short own-words text. Refuses control characters, length overruns and unsupported 'best trader' assertions."""
    if value is None:
        return None
    s = re.sub(r"\s+", " ", str(value)).strip()
    if not s:
        return None
    if len(s) > maxlen:
        raise ValueError(f"{field}: longer than {maxlen} characters")
    if _CONTROL.search(s):
        raise ValueError(f"{field}: control characters are not allowed")
    if _SUPERLATIVE.search(s):
        raise ValueError(f"{field}: unsupported 'best trader' style assertion; say who claimed what and where")
    return s


def check_ref(ref: str | None, field: str = "evidence_ref", required: bool = False) -> str | None:
    if ref is None or ref == "":
        if required:
            raise ValueError(f"{field}: a direct URL, listing id, observation id or transaction id is required")
        return None
    if not _REF.match(ref):
        raise ValueError(f"{field}: must be an https URL, listing:<id>, observation:<id>, tx:<hash>, repo:<path> or narrative:<run>:<cluster>:<claim>")
    return ref


def _log(con, target_type: str, target_id: Any, action: str, reviewer: str, reason: str | None, now: float,
         from_state: str | None = None, to_state: str | None = None) -> None:
    con.execute("INSERT INTO social_registry_reviews(target_type,target_id,action,from_state,to_state,reviewer,reason,reviewed_at)"
                " VALUES (?,?,?,?,?,?,?,?)", (target_type, str(target_id), action, from_state, to_state, reviewer, reason, now))


def _reviewer(name: str | None) -> str:
    n = clean_text(name, "reviewer", 60)
    if not n:
        raise ValueError("reviewer: a name is required for every manual decision")
    return n


# ---------- sources and captures ----------

def register_source(con, *, source_key: str, source_kind: str, access_mode: str, permitted_basis: str, url: str | None = None,
                    organization_entity_id: str | None = None, max_age_seconds: int | None = None,
                    is_fixture: bool = False, now: float | None = None) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9:_.\-]{2,60}", source_key or ""):
        raise ValueError("source_key: 3 to 61 characters of a-z 0-9 : _ . -")
    basis = clean_text(permitted_basis, "permitted_basis", 300)
    if not basis:
        raise ValueError("permitted_basis: say why the lab may read this source")
    row = con.execute("SELECT * FROM social_registry_sources WHERE source_key=?", (source_key,)).fetchone()
    if row is not None:
        if bool(row["is_fixture"]) != bool(is_fixture):
            raise ValueError(f"source {source_key} exists with a different fixture flag; fixture and real sources never share a key")
        return source_key
    con.execute("INSERT INTO social_registry_sources(source_key,source_kind,organization_entity_id,access_mode,permitted_basis,url,"
                "max_age_seconds,is_fixture,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (source_key, source_kind, organization_entity_id, access_mode, basis, url,
                 int(max_age_seconds or DEFAULT_MAX_AGE), int(bool(is_fixture)), _now(now)))
    return source_key


def capture_freshness(capture: sqlite3.Row | dict | None, max_age: int | None, now: float) -> str:
    """FRESH, STALE or UNKNOWN. An undated capture is never FRESH; a list whose own period ended long ago is STALE."""
    if capture is None or capture["captured_at"] is None:
        return "UNKNOWN"
    limit = max_age or DEFAULT_MAX_AGE
    if now - capture["captured_at"] > limit:
        return "STALE"
    if capture["period_end"] is not None and now - capture["period_end"] > limit:
        return "STALE"
    return "FRESH"


# ---------- entities ----------

def get_entity(con, entity_id: str) -> sqlite3.Row:
    row = con.execute("SELECT * FROM social_registry_entities WHERE entity_id=?", (entity_id,)).fetchone()
    if row is None:
        raise ValueError(f"unknown registry entity {entity_id!r}")
    return row


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def _insert_entity(con, entity_id: str, kind: str, label: str, now: float, *, platform=None, account_id=None, chain=None,
                   wallet=None, source_key=None, fixture_label: str | None = None) -> str:
    label = clean_text(label, "label", 120)
    if not label:
        raise ValueError("label: required")
    fx = clean_text(fixture_label, "fixture_label", 120) if fixture_label else None
    row = con.execute("SELECT is_fixture FROM social_registry_entities WHERE entity_id=?", (entity_id,)).fetchone()
    if row is not None:
        if bool(row["is_fixture"]) != bool(fx):
            raise ValueError(f"{entity_id} exists with a different fixture flag; fixture and real data never share an entity")
        return entity_id
    con.execute("INSERT INTO social_registry_entities(entity_id,entity_kind,label,platform,account_id,chain,wallet_address,source_key,"
                "first_seen_at,is_fixture,fixture_label) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (entity_id, kind, label, platform, account_id, chain, wallet, source_key, now, int(bool(fx)), fx))
    con.execute("INSERT OR IGNORE INTO social_registry_records(entity_id,created_at,updated_at) VALUES (?,?,?)", (entity_id, now, now))
    return entity_id


def ensure_account(con, platform: str, handle: str | None = None, provider_user_id: str | None = None, *,
                   display_name: str | None = None, profile_url: str | None = None, fixture_label: str | None = None,
                   now: float | None = None) -> str:
    """Entity for a social account. The key is the Phase 01 account id, so the same provider id after a handle rename is the
    same entity, while two accounts with the same screen name but different provider ids (or platforms) are two entities."""
    platform = platform.strip().lower()
    if platform not in PLATFORMS:
        raise ValueError(f"platform {platform!r} is not one of {PLATFORMS}")
    if display_name is not None:
        display_name = clean_text(display_name, "display_name", 80)
    t = _now(now)
    account_id = store.upsert_account(con, platform, handle=handle, provider_user_id=provider_user_id, display_name=display_name,
                                      profile_url=profile_url, now=t)
    acc = store.get_account(con, account_id)
    label = acc["display_name"] or (f"@{acc['handle']}" if acc["handle"] else account_id)
    eid = _insert_entity(con, f"acct:{account_id}", "SOCIAL_ACCOUNT", label, t, platform=platform, account_id=account_id,
                         fixture_label=fixture_label)
    if fixture_label:
        con.execute("UPDATE social_accounts SET notes=? WHERE account_id=? AND notes IS NULL", (f"FIXTURE: {fixture_label}", account_id))
    return eid


def ensure_wallet(con, chain: str, address: str, *, fixture_label: str | None = None, now: float | None = None) -> str:
    ch = chain.strip().lower()
    if ch not in chain_registry.CHAINS:
        raise ValueError(f"unknown chain {chain!r}")
    w = store.normalize_contract(ch, address)
    return _insert_entity(con, f"wallet:{ch}:{w}", "OBSERVED_WALLET", f"{ch} {w[:6]}...{w[-4:]}", _now(now), chain=ch, wallet=w,
                          fixture_label=fixture_label)


def ensure_org(con, key: str, label: str, *, fixture_label: str | None = None, now: float | None = None) -> str:
    """Organizations are keyed by an explicit key chosen by the importer or reviewer, never by matching names."""
    k = _slug(key)
    if not k:
        raise ValueError("an organization needs a key")
    return _insert_entity(con, f"org:{k}", "SOURCE_ORGANIZATION", label, _now(now), fixture_label=fixture_label)


def ensure_network(con, key: str, label: str, *, fixture_label: str | None = None, now: float | None = None) -> str:
    k = _slug(key)
    if not k:
        raise ValueError("a network needs a key")
    return _insert_entity(con, f"net:{k}", "SOCIAL_NETWORK", label, _now(now), fixture_label=fixture_label)


def ensure_candidate(con, source_key: str, ident: str, label: str, *, fixture_label: str | None = None, now: float | None = None) -> str:
    return _insert_entity(con, f"cand:{source_key}:{ident}", "LEADERBOARD_CANDIDATE", label, _now(now), source_key=source_key,
                          fixture_label=fixture_label)


def add_evidence(con, entity_id: str, kind: str, ref: str, *, url: str | None = None, source_key: str | None = None,
                 capture_id: int | None = None, captured_at: float | None = None, note: str | None = None,
                 now: float | None = None) -> bool:
    get_entity(con, entity_id)
    if kind == "MANUAL_NOTE":
        check_ref(ref, "ref", required=True)
    note = clean_text(note, "note", 300)
    cur = con.execute("INSERT OR IGNORE INTO social_registry_evidence(entity_id,evidence_kind,ref,url,source_key,capture_id,captured_at,note,"
                      "recorded_at) VALUES (?,?,?,?,?,?,?,?,?)", (entity_id, kind, ref, url, source_key, capture_id, captured_at, note, _now(now)))
    return cur.rowcount == 1


# ---------- links ----------

def _active_clause(alias: str = "l") -> str:
    return (f"{alias}.state='ASSERTED' AND {alias}.review_state<>'REJECTED' AND NOT EXISTS "
            f"(SELECT 1 FROM social_registry_links r WHERE r.retracts_link_id={alias}.link_id AND r.state='RETRACTED')")


def _fixture_pair(*rows) -> bool:
    flags = {bool(r["is_fixture"]) for r in rows if r is not None}
    if len(flags) > 1:
        raise ValueError("a fixture entity can only be linked to other fixture entities")
    return flags == {True}


def add_link(con, *, link_type: str, from_entity: str, to_entity: str, basis: str, recorded_by: str,
             asserted_by: str | None = None, evidence_status: str | None = None, confidence: str = "UNKNOWN",
             evidence_ref: str | None = None, source_key: str | None = None, capture_id: int | None = None,
             observation_id: int | None = None, valid_from: Any = None, valid_to: Any = None, asserted_at: Any = None,
             note: str | None = None, now: float | None = None, mirror: bool = True) -> dict:
    """Record one assertion between two entities. Nothing here merges entities: a link is a claim with a basis, a source and a
    time, and it counts toward an attribution only after a person reviews it (see wallet_attribution)."""
    rules = LINK_RULES.get(link_type)
    if rules is None:
        raise ValueError(f"link type {link_type!r} is not one of {tuple(LINK_RULES)}")
    if str(basis).upper() in NAME_BASES:
        raise ValueError("basis: matching names or screen names is not evidence of the same identity")
    if basis not in rules["basis"]:
        raise ValueError(f"{link_type} accepts bases {rules['basis']}, not {basis!r}")
    if confidence not in CONFIDENCES:
        raise ValueError(f"confidence must be one of {CONFIDENCES}")
    t = _now(now)
    who = _reviewer(recorded_by)
    a, b = get_entity(con, from_entity), get_entity(con, to_entity)
    if a["entity_kind"] not in rules["from"] or b["entity_kind"] not in rules["to"]:
        raise ValueError(f"{link_type} connects {rules['from']} to {rules['to']}, not {a['entity_kind']} to {b['entity_kind']}")
    if link_type == "SAME_OPERATOR":
        from_entity, to_entity = sorted((from_entity, to_entity))
    ab = get_entity(con, asserted_by) if asserted_by else None
    fixture = _fixture_pair(a, b, ab)
    ref = check_ref(evidence_ref, required=rules["ref"] and capture_id is None)
    if link_type in WALLET_LINKS:
        if evidence_status == "FACT":
            raise ValueError("evidence_status FACT is set by reviewing an on-chain proof, not when a wallet link is recorded")
        evidence_status = evidence_status or "INFERENCE"
    else:
        evidence_status = evidence_status or ("FACT" if link_type in ("LISTED_BY", "OBSERVED_AS") else "INFERENCE")
    if evidence_status not in store.EVIDENCE:
        raise ValueError(f"evidence status must be one of {store.EVIDENCE}")
    if link_type == "WALLET_THIRD_PARTY_LABEL" and (ab is None or asserted_by == from_entity):
        raise ValueError("a third-party label needs asserted_by: the entity that published it, other than the account itself")
    if link_type == "WALLET_SELF_DISCLOSED" and asserted_by not in (None, from_entity):
        asserted_by = from_entity
    if link_type == "WALLET_SELF_DISCLOSED":
        asserted_by = from_entity
    vf, vt, at = store.to_utc(valid_from), store.to_utc(valid_to), store.to_utc(asserted_at) or t
    if vf is not None and vt is not None and vt < vf:
        raise ValueError("valid_to is before valid_from")
    note = clean_text(note, "note", 300)
    key = _sha(link_type, from_entity, to_entity, asserted_by, basis, ref, capture_id, vf, vt, "ASSERTED")
    cur = con.execute(
        "INSERT OR IGNORE INTO social_registry_links(link_key,link_type,from_entity,to_entity,asserted_by_entity,state,basis,"
        "evidence_status,confidence,evidence_ref,source_key,capture_id,observation_id,valid_from,valid_to,asserted_at,recorded_at,"
        "recorded_by,note,is_fixture) VALUES (?,?,?,?,?,'ASSERTED',?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (key, link_type, from_entity, to_entity, asserted_by, basis, evidence_status, confidence, ref, source_key, capture_id,
         observation_id, vf, vt, at, t, who, note, int(fixture)))
    created = cur.rowcount == 1
    lid = cur.lastrowid if created else con.execute("SELECT link_id FROM social_registry_links WHERE link_key=?", (key,)).fetchone()[0]
    if created:
        _log(con, "LINK", lid, f"RECORD_{link_type}", who, note, t, None, "UNREVIEWED")
        if mirror:
            _sync_links(con, get_link(con, lid), t)
    return {"link_id": lid, "created": created}


def sync_attribution(con, account_entity: str, wallet_entity: str, now: float | None = None) -> dict | None:
    """Keep social_wallet_attributions (Phase 01), the table later attribution and performance stages read, equal to what the registry
    computes now. A new assertion row is appended only when the computed state changes, so the latest row per subject is the current level.
    NONE writes RETRACTED; CORROBORATED by a reviewed on-chain proof writes CHAIN_EVIDENCE (FACT); corroboration by a self claim plus a
    reviewed independent label has no enum of its own and is written as THIRD_PARTY_LABEL at MODERATE."""
    t = _now(now)
    a, w = get_entity(con, account_entity), get_entity(con, wallet_entity)
    if a["entity_kind"] != "SOCIAL_ACCOUNT" or w["entity_kind"] != "OBSERVED_WALLET":
        return None
    att = wallet_attribution(con, account_entity, wallet_entity)
    level = att["level"]
    proof = "reviewed_on_chain_proof" in att["reasons"]
    assertion, evidence, conf = {"NONE": ("RETRACTED", "UNKNOWN", "UNKNOWN"), "THIRD_PARTY_LABELED": ("THIRD_PARTY_LABEL", "INFERENCE", "LOW"),
                                 "SELF_CLAIMED": ("SELF_CLAIMED", "INFERENCE", "LOW"),
                                 "CORROBORATED": ("CHAIN_EVIDENCE", "FACT", "HIGH") if proof else ("THIRD_PARTY_LABEL", "INFERENCE", "MODERATE"),
                                 "DISPUTED": ("DISPUTED", "INFERENCE", "UNKNOWN")}[level]
    rows = con.execute("SELECT assertion, evidence_status, confidence FROM social_wallet_attributions WHERE subject_type='ACCOUNT' AND subject_id=? "
                       "AND chain=? AND wallet_address=? ORDER BY asserted_at, id", (a["account_id"], w["chain"], w["wallet_address"])).fetchall()
    if not rows and level == "NONE":
        return None
    if rows and tuple(rows[-1]) == (assertion, evidence, conf):
        return None
    store.register_analysis_version(con, VERSION, "registry", "source and trader registry (Phase 08)", now=t)
    fx = a["is_fixture"] or w["is_fixture"]
    basis = (f"{'FIXTURE ' if fx else ''}registry state {level.lower()} ({'; '.join(att['reasons'])[:200]}) links {att['supporting_links']} [sync {len(rows) + 1}]")
    return store.assert_wallet(con, subject_type="ACCOUNT", subject_id=a["account_id"], chain=w["chain"], wallet_address=w["wallet_address"],
                               assertion=assertion, evidence_status=evidence, confidence=conf, basis=basis, asserted_at=t,
                               analysis_version=VERSION, now=t)


def _sync_links(con, l, now: float) -> None:
    """Re-sync the mirror after a link was added, reviewed or retracted."""
    if l["link_type"] in WALLET_LINKS:
        for acc in identity_cluster(con, l["from_entity"]):
            sync_attribution(con, acc, l["to_entity"], now)
    elif l["link_type"] == "SAME_OPERATOR":
        for acc in set(identity_cluster(con, l["from_entity"])) | set(identity_cluster(con, l["to_entity"])):
            for w in wallets_of(con, acc):
                sync_attribution(con, acc, w["wallet_entity"], now)


def get_link(con, link_id: int) -> sqlite3.Row:
    row = con.execute("SELECT * FROM social_registry_links WHERE link_id=?", (link_id,)).fetchone()
    if row is None:
        raise ValueError(f"unknown link {link_id}")
    return row


def retract_link(con, link_id: int, *, reviewer: str, reason: str, now: float | None = None) -> dict:
    """A retraction is a new row that points at the old one; the old row and its history stay."""
    t = _now(now)
    who = _reviewer(reviewer)
    why = clean_text(reason, "reason", 300)
    if not why:
        raise ValueError("reason: required to retract a link")
    l = get_link(con, link_id)
    if l["state"] != "ASSERTED":
        raise ValueError("only an asserted link can be retracted")
    key = _sha(l["link_type"], l["from_entity"], l["to_entity"], l["asserted_by_entity"], l["basis"], l["evidence_ref"], l["capture_id"],
               l["valid_from"], l["valid_to"], "RETRACTED", link_id)
    cur = con.execute(
        "INSERT OR IGNORE INTO social_registry_links(link_key,link_type,from_entity,to_entity,asserted_by_entity,state,retracts_link_id,basis,"
        "evidence_status,confidence,evidence_ref,source_key,capture_id,observation_id,valid_from,valid_to,asserted_at,recorded_at,recorded_by,"
        "note,is_fixture) VALUES (?,?,?,?,?,'RETRACTED',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (key, l["link_type"], l["from_entity"], l["to_entity"], l["asserted_by_entity"], link_id, l["basis"], "UNKNOWN", "UNKNOWN",
         l["evidence_ref"], l["source_key"], l["capture_id"], l["observation_id"], l["valid_from"], l["valid_to"], t, t, who, why,
         l["is_fixture"]))
    created = cur.rowcount == 1
    if created:
        _log(con, "LINK", link_id, "RETRACT", who, why, t, "ASSERTED", "RETRACTED")
        _sync_links(con, l, t)
    return {"retraction_link_id": cur.lastrowid if created else None, "created": created}


def review_link(con, link_id: int, decision: str, *, reviewer: str, reason: str, now: float | None = None) -> dict:
    """APPROVED makes a link count (same-operator merges, independent labels, on-chain proofs); REJECTED removes it from every view."""
    if decision not in ("APPROVED", "REJECTED"):
        raise ValueError("decision must be APPROVED or REJECTED")
    t = _now(now)
    who = _reviewer(reviewer)
    why = clean_text(reason, "reason", 300)
    if not why:
        raise ValueError("reason: required to review a link")
    l = get_link(con, link_id)
    if l["state"] != "ASSERTED":
        raise ValueError("a retraction row is not reviewed")
    if decision == "APPROVED" and l["link_type"] in ("WALLET_ON_CHAIN_PROOF", "SAME_OPERATOR") and not l["evidence_ref"]:
        raise ValueError(f"{l['link_type']} cannot be approved without a direct evidence reference")
    con.execute("UPDATE social_registry_links SET review_state=?, reviewed_by=?, reviewed_at=?, review_reason=? WHERE link_id=?",
                (decision, who, t, why, link_id))
    _log(con, "LINK", link_id, f"REVIEW_{decision}", who, why, t, l["review_state"], decision)
    _sync_links(con, l, t)
    return {"link_id": link_id, "review_state": decision}


def active_links(con, entity_id: str | None = None, link_types: tuple[str, ...] | None = None, *, direction: str = "any") -> list[sqlite3.Row]:
    q = f"SELECT l.* FROM social_registry_links l WHERE {_active_clause()}"
    args: list = []
    if entity_id is not None:
        cond = {"from": "l.from_entity=?", "to": "l.to_entity=?", "any": "(l.from_entity=? OR l.to_entity=?)"}[direction]
        q += f" AND {cond}"
        args += [entity_id] * (2 if direction == "any" else 1)
    if link_types:
        q += f" AND l.link_type IN ({','.join('?' * len(link_types))})"
        args += list(link_types)
    return con.execute(q + " ORDER BY l.link_id", args).fetchall()


def identity_cluster(con, entity_id: str) -> list[str]:
    """Accounts joined to this one by an APPROVED SAME_OPERATOR link. An unreviewed proposal never joins anything."""
    seen, todo = {entity_id}, [entity_id]
    while todo:
        cur = todo.pop()
        for l in active_links(con, cur, ("SAME_OPERATOR",)):
            if l["review_state"] != "APPROVED":
                continue
            other = l["to_entity"] if l["from_entity"] == cur else l["from_entity"]
            if other not in seen:
                seen.add(other)
                todo.append(other)
    return sorted(seen)


def _in_window(l, as_of: float | None) -> bool:
    if as_of is None:
        return True
    return (l["valid_from"] is None or l["valid_from"] <= as_of) and (l["valid_to"] is None or as_of <= l["valid_to"])


def _independent(con, claimant_cluster: list[str], asserter: str | None) -> tuple[bool, str]:
    if asserter is None:
        return False, "label_asserter_unknown"
    if asserter in claimant_cluster:
        return False, "label_asserter_is_the_claimant_or_a_linked_account"
    if asserter.startswith("org:"):
        for acc in claimant_cluster:
            for l in active_links(con, acc, ("OPERATED_BY_ORG",), direction="from"):
                if l["to_entity"] == asserter and l["review_state"] == "APPROVED":
                    return False, "label_asserter_operates_the_claimant"
    return True, "independent"


def wallet_attribution(con, account_entity: str, wallet_entity: str, *, as_of: Any = None) -> dict:
    """What the registry can honestly say about whether this account controls this wallet.
    Levels: NONE, THIRD_PARTY_LABELED (someone else says so), SELF_CLAIMED (the account or a linked account says so),
    CORROBORATED (reviewed on-chain proof, or a self claim plus a reviewed label from an independent party), DISPUTED.
    Links that are unreviewed, rejected, retracted or outside as_of never count toward CORROBORATED; they are listed."""
    at = store.to_utc(as_of)
    cluster = identity_cluster(con, account_entity)
    links = [l for l in active_links(con, wallet_entity, WALLET_LINKS, direction="to") if l["from_entity"] in cluster and _in_window(l, at)]
    self_claims = [l for l in links if l["link_type"] == "WALLET_SELF_DISCLOSED"]
    labels = [l for l in links if l["link_type"] == "WALLET_THIRD_PARTY_LABEL"]
    proofs = [l for l in links if l["link_type"] == "WALLET_ON_CHAIN_PROOF" and l["review_state"] == "APPROVED" and l["evidence_ref"]]
    disputes = [l for l in links if l["link_type"] == "WALLET_DISPUTED"]
    reasons: list[str] = []
    good_labels = []
    for l in labels:
        ok, why = _independent(con, cluster, l["asserted_by_entity"])
        if not ok:
            reasons.append(f"{why}:link{l['link_id']}")
        elif l["review_state"] != "APPROVED":
            reasons.append(f"label_unreviewed:link{l['link_id']}")
        else:
            good_labels.append(l)
    for l in links:
        if l["link_type"] == "WALLET_ON_CHAIN_PROOF" and l not in proofs:
            reasons.append(f"proof_unreviewed:link{l['link_id']}")
    if disputes:
        level, conf = "DISPUTED", "UNKNOWN"
        reasons += [f"disputed_by:link{l['link_id']}" for l in disputes]
    elif proofs:
        level, conf = "CORROBORATED", "HIGH"
        reasons.append("reviewed_on_chain_proof")
    elif self_claims and good_labels:
        level, conf = "CORROBORATED", "MODERATE"
        reasons.append("self_claim_plus_reviewed_independent_label")
    elif self_claims:
        level, conf = "SELF_CLAIMED", "LOW"
        reasons.append("self_claim_only")
    elif labels:
        level, conf = "THIRD_PARTY_LABELED", "LOW"
        reasons.append("third_party_label_only")
    else:
        level, conf = "NONE", "UNKNOWN"
    return {"account_entity": account_entity, "wallet_entity": wallet_entity, "level": level, "confidence": conf,
            "verified": level == "CORROBORATED", "reasons": reasons, "via_accounts": [c for c in cluster if c != account_entity],
            "supporting_links": [l["link_id"] for l in links],
            "windows": [{"link_id": l["link_id"], "valid_from": l["valid_from"], "valid_to": l["valid_to"], "asserted_at": l["asserted_at"]}
                        for l in links],
            "as_of": at}


def wallets_of(con, account_entity: str, *, as_of: Any = None) -> list[dict]:
    """Every wallet linked to this account or its approved same-operator accounts, each with its own attribution level."""
    cluster = identity_cluster(con, account_entity)
    wallets = sorted({l["to_entity"] for a in cluster for l in active_links(con, a, WALLET_LINKS, direction="from")})
    return [wallet_attribution(con, account_entity, w, as_of=as_of) for w in wallets]


def owners_of(con, wallet_entity: str, *, as_of: Any = None) -> list[dict]:
    """Accounts that anyone has linked to this wallet, each with the attribution level. Several owners is normal data, not an error."""
    accts = sorted({l["from_entity"] for l in active_links(con, wallet_entity, WALLET_LINKS, direction="to")})
    seen, out = set(), []
    for a in accts:
        cl = tuple(identity_cluster(con, a))
        if cl in seen:
            continue
        seen.add(cl)
        out.append(wallet_attribution(con, a, wallet_entity, as_of=as_of))
    return out


# ---------- records, review and watch ----------

def get_record(con, entity_id: str) -> sqlite3.Row:
    get_entity(con, entity_id)
    con.execute("INSERT OR IGNORE INTO social_registry_records(entity_id,created_at,updated_at) VALUES (?,0,0)", (entity_id,))
    return con.execute("SELECT * FROM social_registry_records WHERE entity_id=?", (entity_id,)).fetchone()


def _account_row(con, ent) -> sqlite3.Row | None:
    return store.get_account(con, ent["account_id"]) if ent["entity_kind"] == "SOCIAL_ACCOUNT" else None


def evidence_summary(con, entity_id: str, now: float) -> dict:
    """Counts of usable evidence. Usable means dated and not older than the source's limit (30 days when it has no source)."""
    fresh = stale = unknown = 0
    for e in con.execute("SELECT * FROM social_registry_evidence WHERE entity_id=?", (entity_id,)):
        if e["captured_at"] is None:
            unknown += 1
            continue
        lim = EVIDENCE_MAX_AGE
        if e["source_key"]:
            s = con.execute("SELECT max_age_seconds FROM social_registry_sources WHERE source_key=?", (e["source_key"],)).fetchone()
            lim = s["max_age_seconds"] if s else lim
        if e["capture_id"]:
            c = con.execute("SELECT * FROM social_registry_captures WHERE capture_id=?", (e["capture_id"],)).fetchone()
            if capture_freshness(c, lim, now) != "FRESH":
                stale += 1
                continue
        if now - e["captured_at"] > lim:
            stale += 1
        else:
            fresh += 1
    return {"fresh": fresh, "stale": stale, "undated": unknown, "total": fresh + stale + unknown}


def approve(con, entity_id: str, *, reviewer: str, reason: str, specialty: str | None = None, topical_focus: str | None = None,
            watch: bool = False, accept_stale_reason: str | None = None, now: float | None = None) -> dict:
    """Approve a candidate as a research source worth watching. This does not say the source is profitable, right, or honest."""
    t = _now(now)
    who = _reviewer(reviewer)
    ent = get_entity(con, entity_id)
    rec = get_record(con, entity_id)
    why = clean_text(reason, "reason (why follow)", 300)
    if not why:
        raise ValueError("reason: say why this source is worth following")
    spec = clean_text(specialty, "specialty", 120) if specialty is not None else rec["specialty"]
    focus = clean_text(topical_focus, "topical_focus", 200) if topical_focus is not None else rec["topical_focus"]
    ev = evidence_summary(con, entity_id, t)
    if ev["total"] == 0:
        raise ValueError("no_evidence: a registry record needs at least one evidence row (direct URL, listing, observation or note)")
    override = None
    if ev["fresh"] == 0:
        override = clean_text(accept_stale_reason, "accept_stale_reason", 300)
        if not override:
            raise ValueError(f"stale_evidence_only: all {ev['total']} evidence rows are stale or undated; add current evidence or give accept_stale_reason")
    acc = _account_row(con, ent)
    if watch:
        _check_watchable(ent, acc, "WATCH")
    con.execute("UPDATE social_registry_records SET review_state='APPROVED', watch_status=?, specialty=?, topical_focus=?, follow_reason=?, "
                "reject_reason=NULL, stale_override_reason=?, updated_at=?, last_reviewed_at=?, reviewed_by=? WHERE entity_id=?",
                ("WATCH" if watch else rec["watch_status"], spec, focus, why, override, t, t, who, entity_id))
    _log(con, "ENTITY", entity_id, "APPROVE", who, why + (f" | stale override: {override}" if override else ""), t, rec["review_state"], "APPROVED")
    return {"entity_id": entity_id, "review_state": "APPROVED", "watch_status": "WATCH" if watch else rec["watch_status"], "evidence": ev}


def reject(con, entity_id: str, *, reviewer: str, reason: str, now: float | None = None) -> dict:
    t = _now(now)
    who = _reviewer(reviewer)
    why = clean_text(reason, "reason", 300)
    if not why:
        raise ValueError("reason: required to reject")
    rec = get_record(con, entity_id)
    con.execute("UPDATE social_registry_records SET review_state='REJECTED', watch_status='NONE', reject_reason=?, updated_at=?, last_reviewed_at=?, "
                "reviewed_by=? WHERE entity_id=?", (why, t, t, who, entity_id))
    _log(con, "ENTITY", entity_id, "REJECT", who, why, t, rec["review_state"], "REJECTED")
    return {"entity_id": entity_id, "review_state": "REJECTED"}


def _check_watchable(ent, acc, status: str) -> None:
    if status != "WATCH":
        return
    if ent["is_fixture"]:
        raise ValueError("fixture_cannot_be_watched: fixture entities are demonstration data and are never followed")
    if acc is not None and acc["identity_status"] in ("SUSPENDED", "NOT_FOUND"):
        raise ValueError(f"account_{acc['identity_status'].lower()}: cannot watch an account that is {acc['identity_status']}")


def update_record(con, entity_id: str, *, reviewer: str, specialty: str | None = None, topical_focus: str | None = None,
                  follow_reason: str | None = None, watch_status: str | None = None, now: float | None = None) -> dict:
    t = _now(now)
    who = _reviewer(reviewer)
    ent = get_entity(con, entity_id)
    rec = get_record(con, entity_id)
    sets: dict[str, Any] = {}
    if specialty is not None:
        sets["specialty"] = clean_text(specialty, "specialty", 120)
    if topical_focus is not None:
        sets["topical_focus"] = clean_text(topical_focus, "topical_focus", 200)
    if follow_reason is not None:
        sets["follow_reason"] = clean_text(follow_reason, "follow_reason", 300)
    if watch_status is not None:
        if watch_status not in WATCH:
            raise ValueError(f"watch_status must be one of {WATCH}")
        if watch_status == "WATCH" and rec["review_state"] != "APPROVED":
            raise ValueError("not_approved: only an approved record can be watched")
        _check_watchable(ent, _account_row(con, ent), watch_status)
        sets["watch_status"] = watch_status
    if not sets:
        raise ValueError("nothing to update")
    sets.update(updated_at=t, last_reviewed_at=t, reviewed_by=who)
    con.execute(f"UPDATE social_registry_records SET {','.join(k + '=?' for k in sets)} WHERE entity_id=?", list(sets.values()) + [entity_id])
    _log(con, "ENTITY", entity_id, "UPDATE", who, json.dumps({k: v for k, v in sets.items() if k not in ("updated_at", "last_reviewed_at", "reviewed_by")},
                                                              sort_keys=True), t, rec["watch_status"], sets.get("watch_status", rec["watch_status"]))
    return {"entity_id": entity_id, **{k: v for k, v in sets.items() if k in ("specialty", "topical_focus", "follow_reason", "watch_status")}}


def set_account_status(con, entity_id: str, status: str, *, reviewer: str, reason: str, evidence_ref: str | None = None,
                       checked_at: Any = None, now: float | None = None) -> dict:
    """Record that a platform account is suspended, missing, or back to unverified. Links, wallets and history stay; watching pauses."""
    if status not in ("SUSPENDED", "NOT_FOUND", "UNVERIFIED"):
        raise ValueError("status must be SUSPENDED, NOT_FOUND or UNVERIFIED")
    t = _now(now)
    who = _reviewer(reviewer)
    why = clean_text(reason, "reason", 300)
    if not why:
        raise ValueError("reason: required")
    ref = check_ref(evidence_ref)
    ent = get_entity(con, entity_id)
    if ent["entity_kind"] != "SOCIAL_ACCOUNT":
        raise ValueError("account status applies to social accounts only")
    acc = store.get_account(con, ent["account_id"])
    at = store.to_utc(checked_at) or t
    con.execute("UPDATE social_accounts SET identity_status=?, identity_checked_at=? WHERE account_id=?", (status, at, ent["account_id"]))
    rec = get_record(con, entity_id)
    paused = False
    if status in ("SUSPENDED", "NOT_FOUND") and rec["watch_status"] == "WATCH":
        con.execute("UPDATE social_registry_records SET watch_status='PAUSED', updated_at=? WHERE entity_id=?", (t, entity_id))
        paused = True
    _log(con, "ACCOUNT_STATUS", entity_id, f"SET_{status}", who, why + (f" | ref {ref}" if ref else ""), t, acc["identity_status"], status)
    return {"entity_id": entity_id, "identity_status": status, "watch_paused": paused}


# ---------- categories ----------

def category_state(con, entity_id: str) -> dict[str, dict]:
    """Latest non-retracted row per category."""
    out: dict[str, dict] = {}
    for r in con.execute("SELECT * FROM social_registry_categories WHERE entity_id=? ORDER BY id", (entity_id,)):
        if r["status"] == "RETRACTED":
            out.pop(r["category"], None)
        else:
            out[r["category"]] = dict(r)
    return out


def set_category(con, entity_id: str, category: str, status: str, *, basis: str, set_by: str, evidence_ref: str | None = None,
                 now: float | None = None) -> dict:
    """PROPOSED may come from discovery; CONFIRMED needs a person and the evidence its category requires; RETRACTED removes it."""
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {CATEGORIES}")
    if status not in ("PROPOSED", "CONFIRMED", "RETRACTED"):
        raise ValueError("status must be PROPOSED, CONFIRMED or RETRACTED")
    t = _now(now)
    who = _reviewer(set_by)
    b = clean_text(basis, "basis", 300)
    if not b:
        raise ValueError("basis: say what supports this category")
    ref = check_ref(evidence_ref)
    ent = get_entity(con, entity_id)
    if status == "CONFIRMED":
        _check_category(con, ent, category, ref, t)
    cur = con.execute("INSERT INTO social_registry_categories(entity_id,category,status,basis,evidence_ref,set_by,set_at) VALUES (?,?,?,?,?,?,?)",
                      (entity_id, category, status, b, ref, who, t))
    _log(con, "CATEGORY", f"{entity_id}|{category}", status, who, b, t, None, status)
    return {"id": cur.lastrowid, "entity_id": entity_id, "category": category, "status": status}


def _kinds_of_evidence(con, entity_id: str) -> set[str]:
    return {r[0] for r in con.execute("SELECT evidence_kind FROM social_registry_evidence WHERE entity_id=?", (entity_id,))}


def _check_category(con, ent, category: str, ref: str | None, now: float) -> None:
    eid = ent["entity_id"]
    kinds = _kinds_of_evidence(con, eid)
    if category == "VERIFIED_WALLET_CANDIDATE":
        if ent["entity_kind"] != "SOCIAL_ACCOUNT":
            raise ValueError("VERIFIED_WALLET_CANDIDATE applies to a social account with a linked wallet")
        ws = wallets_of(con, eid)
        if not any(w["level"] in ("SELF_CLAIMED", "CORROBORATED", "THIRD_PARTY_LABELED") for w in ws):
            raise ValueError("no_wallet_attribution: link a wallet with evidence first; the level stays visible and is not 'verified' until CORROBORATED")
    elif category == "PROFITABLE_TRADING_CLAIMANT":
        if not (kinds & {"LEADERBOARD_LISTING", "OBSERVATION", "MANUAL_NOTE"}) and not ref:
            raise ValueError("no_claim_source: record where the profit claim was made (a listing, an observation or a URL); the claim itself stays unverified")
    elif category in ("INFORMATION_ORIGINATOR", "AMPLIFIER"):
        if not (kinds & {"NARRATIVE_MEMBER", "OBSERVATION"}):
            raise ValueError(f"no_observed_behaviour: {category} needs narrative or observation evidence, not a reputation")
    elif category == "ANALYTICAL_SOURCE":
        if not (kinds & {"OBSERVATION", "NARRATIVE_MEMBER", "MANUAL_NOTE"}) and not ref:
            raise ValueError("no_analysis_evidence: cite an observation or a URL to the analysis")
    elif category == "PROMOTER_HIGH_CONFLICT":
        if not ref and "MANUAL_NOTE" not in kinds:
            raise ValueError("no_conflict_evidence: cite the disclosure, paid placement or relationship that creates the conflict")


# ---------- listings ----------

def review_listing_claim(con, listing_id: int, result: str, *, reviewer: str, evidence_ref: str | None, now: float | None = None) -> dict:
    """Evaluate what a list claimed (a rank or a figure) on its own. This never changes who owns the wallet."""
    if result not in ("CORROBORATED", "CONTRADICTED", "NOT_CHECKABLE"):
        raise ValueError("result must be CORROBORATED, CONTRADICTED or NOT_CHECKABLE")
    t = _now(now)
    who = _reviewer(reviewer)
    ref = check_ref(evidence_ref, required=result != "NOT_CHECKABLE")
    row = con.execute("SELECT * FROM social_registry_listings WHERE listing_id=?", (listing_id,)).fetchone()
    if row is None:
        raise ValueError(f"unknown listing {listing_id}")
    con.execute("UPDATE social_registry_listings SET claim_review=?, claim_review_ref=?, claim_reviewed_by=?, claim_reviewed_at=? WHERE listing_id=?",
                (result, ref, who, t, listing_id))
    _log(con, "LISTING", listing_id, "CLAIM_REVIEW", who, ref, t, row["claim_review"], result)
    return {"listing_id": listing_id, "claim_review": result}


# ---------- search and show ----------

def _handles(con, ent) -> list[str]:
    if ent["entity_kind"] != "SOCIAL_ACCOUNT":
        return []
    return [r[0] for r in con.execute("SELECT handle_normalized FROM social_account_handles WHERE account_id=? ORDER BY first_seen_at, handle_normalized",
                                      (ent["account_id"],))]


def _display_label(con, ent) -> str:
    acc = _account_row(con, ent)
    if acc is not None:
        return acc["display_name"] or (f"@{acc['handle']}" if acc["handle"] else ent["label"])
    return ent["label"]


def shared_handle_entities(con, ent) -> list[str]:
    """Other accounts that use or used the same screen name. Same name is a reason to look, never a reason to merge."""
    if ent["entity_kind"] != "SOCIAL_ACCOUNT":
        return []
    hs = _handles(con, ent)
    if not hs:
        return []
    rows = con.execute(f"SELECT DISTINCT e.entity_id FROM social_account_handles h JOIN social_registry_entities e ON e.account_id=h.account_id "
                       f"WHERE h.handle_normalized IN ({','.join('?' * len(hs))}) AND e.entity_id<>? ORDER BY e.entity_id", hs + [ent["entity_id"]]).fetchall()
    return [r[0] for r in rows]


def same_label_entities(con, ent) -> list[str]:
    """Other entities of the same kind showing the same name. Names collide all the time; this is a prompt to look, not a link."""
    lab = _display_label(con, ent).lower()
    rows = con.execute("SELECT entity_id, label FROM social_registry_entities WHERE entity_kind=? AND entity_id<>?", (ent["entity_kind"], ent["entity_id"])).fetchall()
    out = []
    for r in rows:
        other = con.execute("SELECT * FROM social_registry_entities WHERE entity_id=?", (r["entity_id"],)).fetchone()
        if _display_label(con, other).lower() == lab:
            out.append(r["entity_id"])
    return sorted(out)


def search(con, *, q: str | None = None, kind: str | None = None, review_state: str | None = None, watch: str | None = None,
           category: str | None = None, platform: str | None = None, fixture: bool | None = None, stale: bool | None = None,
           attribution: str | None = None, suspended: bool | None = None, limit: int = 200, now: float | None = None) -> list[dict]:
    """Searchable list. Ordered by label, never by rank or score: the registry makes no ranking claim."""
    t = _now(now)
    sql = "SELECT e.*, r.review_state, r.watch_status, r.specialty, r.topical_focus, r.follow_reason FROM social_registry_entities e " \
          "JOIN social_registry_records r ON r.entity_id=e.entity_id WHERE 1=1"
    args: list = []
    for col, val in (("e.entity_kind", kind), ("r.review_state", review_state), ("r.watch_status", watch), ("e.platform", platform)):
        if val:
            sql += f" AND {col}=?"
            args.append(val)
    if fixture is not None:
        sql += " AND e.is_fixture=?"
        args.append(int(fixture))
    needle = (q or "").strip().lstrip("@").lower()
    out = []
    for e in con.execute(sql, args).fetchall():
        matched: list[str] = []
        if needle:
            hay = {"id": e["entity_id"].lower(), "label": e["label"].lower(), "label_now": _display_label(con, e).lower(),
                   "specialty": (e["specialty"] or "").lower(), "focus": (e["topical_focus"] or "").lower(),
                   "reason": (e["follow_reason"] or "").lower()}
            for k, v in hay.items():
                if needle in v:
                    matched.append(k)
            if any(needle in h for h in _handles(con, e)):
                matched.append("handle_history")
            if e["wallet_address"] and len(needle) >= 6 and needle in e["wallet_address"].lower():
                matched.append("wallet_address")
            if con.execute("SELECT 1 FROM social_registry_listings WHERE candidate_entity_id=? AND (lower(display_name_seen) LIKE ? OR lower(handle_seen) LIKE ? "
                           "OR lower(wallet_address) LIKE ?) LIMIT 1", (e["entity_id"], f"%{needle}%", f"%{needle}%", f"%{needle}%" if len(needle) >= 6 else "\0")).fetchone():
                matched.append("listing")
            if not matched:
                continue
        cats = category_state(con, e["entity_id"])
        if category and category not in cats:
            continue
        acc = _account_row(con, e)
        is_susp = bool(acc is not None and acc["identity_status"] in ("SUSPENDED", "NOT_FOUND"))
        if suspended is not None and suspended != is_susp:
            continue
        ev = evidence_summary(con, e["entity_id"], t)
        is_stale = ev["total"] > 0 and ev["fresh"] == 0
        if stale is not None and stale != is_stale:
            continue
        wlev = None
        if e["entity_kind"] == "SOCIAL_ACCOUNT":
            ws = wallets_of(con, e["entity_id"])
            wlev = max((w["level"] for w in ws), key=LEVELS.index, default="NONE") if ws else "NONE"
            if attribution and wlev != attribution:
                continue
        elif attribution:
            continue
        flags = []
        if e["is_fixture"]:
            flags.append("FIXTURE")
        if is_susp:
            flags.append(acc["identity_status"])
        if is_stale:
            flags.append("STALE_EVIDENCE")
        if ev["total"] == 0:
            flags.append("NO_EVIDENCE")
        if shared_handle_entities(con, e):
            flags.append("SAME_SCREEN_NAME_AS_OTHER_ENTITY")
        if same_label_entities(con, e):
            flags.append("SAME_NAME_AS_OTHER_ENTITY")
        out.append({"entity_id": e["entity_id"], "kind": e["entity_kind"], "label": _display_label(con, e), "platform": e["platform"],
                    "review_state": e["review_state"], "watch_status": e["watch_status"], "specialty": e["specialty"],
                    "topical_focus": e["topical_focus"], "categories": {k: v["status"] for k, v in cats.items()},
                    "wallet_attribution": wlev, "evidence": ev, "flags": flags, "matched_on": matched})
    out.sort(key=lambda d: (d["label"].lower(), d["entity_id"]))
    return out[:limit]


def show(con, entity_id: str, *, now: float | None = None) -> dict:
    """Candidate -> evidence -> reviewed record, with every link, listing, wallet and warning that bears on it."""
    t = _now(now)
    e = get_entity(con, entity_id)
    rec = get_record(con, entity_id)
    acc = _account_row(con, e)
    warns = []
    if e["is_fixture"]:
        warns.append(f"FIXTURE: {e['fixture_label']}")
    if acc is not None and acc["identity_status"] in ("SUSPENDED", "NOT_FOUND"):
        warns.append(f"account is {acc['identity_status']} (checked {acc['identity_checked_at']})")
    shared = shared_handle_entities(con, e)
    if shared:
        warns.append("another registry entity uses or used the same screen name: " + ", ".join(shared) + " (not merged)")
    same = same_label_entities(con, e)
    if same:
        warns.append(f"{len(same)} other {e['entity_kind']} entities show the same name: " + ", ".join(same) + " (not merged)")
    evidence = [dict(r) for r in con.execute("SELECT * FROM social_registry_evidence WHERE entity_id=? ORDER BY evidence_id", (entity_id,))]
    ev = evidence_summary(con, entity_id, t)
    if ev["total"] == 0:
        warns.append("no evidence recorded")
    elif ev["fresh"] == 0:
        warns.append("all evidence is stale or undated")
    listings = []
    for r in con.execute("SELECT l.*, c.captured_at, c.period_start, c.period_end, c.stated_period, c.url AS capture_url, c.source_key, c.is_fixture AS cap_fx "
                         "FROM social_registry_listings l JOIN social_registry_captures c ON c.capture_id=l.capture_id "
                         "WHERE l.candidate_entity_id=? OR l.wallet_address=? ORDER BY c.captured_at, l.listing_id",
                         (entity_id, e["wallet_address"] or "\0")):
        d = dict(r)
        src = con.execute("SELECT max_age_seconds FROM social_registry_sources WHERE source_key=?", (d["source_key"],)).fetchone()
        d["freshness"] = capture_freshness(d, src["max_age_seconds"] if src else None, t)
        d["flags"] = json.loads(d.pop("flags_json"))
        d["metrics"] = json.loads(d.pop("metrics_json") or "{}")
        d["rank_claimed_by_list"] = d.pop("rank_claimed")
        listings.append(d)
    links = [dict(l) for l in con.execute(f"SELECT l.* FROM social_registry_links l WHERE (l.from_entity=? OR l.to_entity=? OR l.asserted_by_entity=?) "
                                         f"AND {_active_clause()} ORDER BY l.link_id", (entity_id, entity_id, entity_id))]
    wallets = wallets_of(con, entity_id) if e["entity_kind"] == "SOCIAL_ACCOUNT" else []
    owners = owners_of(con, entity_id) if e["entity_kind"] == "OBSERVED_WALLET" else []
    for w in wallets:
        if w["level"] == "SELF_CLAIMED":
            warns.append(f"wallet {w['wallet_entity']}: self-claimed only, not verified")
        if w["level"] == "DISPUTED":
            warns.append(f"wallet {w['wallet_entity']}: attribution is disputed")
    reviews = [dict(r) for r in con.execute("SELECT * FROM social_registry_reviews WHERE (target_type='ENTITY' AND target_id=?) OR "
                                            "(target_type IN ('CATEGORY','ACCOUNT_STATUS') AND target_id LIKE ?) ORDER BY review_id",
                                            (entity_id, entity_id + "%"))]
    return {"entity": {**dict(e), "current_label": _display_label(con, e), "handles": _handles(con, e),
                       "identity_status": acc["identity_status"] if acc is not None else None},
            "record": dict(rec), "categories": category_state(con, entity_id), "evidence": evidence, "evidence_summary": ev,
            "listings": listings, "links": links, "wallets": wallets, "owners": owners,
            "same_operator_cluster": identity_cluster(con, entity_id) if e["entity_kind"] == "SOCIAL_ACCOUNT" else [],
            "reviews": reviews, "warnings": warns}


def report(view: dict) -> str:
    """Plain-English record. States who said what; never says 'best' or ranks."""
    e, r = view["entity"], view["record"]
    L = []
    L.append(f"{e['current_label']} ({e['entity_kind']}, {e['entity_id']})")
    if e["is_fixture"]:
        L.append(f"  FIXTURE, demonstration data only: {e['fixture_label']}")
    L.append(f"  record: {r['review_state']}, watch {r['watch_status']}")
    if r["follow_reason"]:
        L.append(f"  reason to follow: {r['follow_reason']}")
    if r["specialty"] or r["topical_focus"]:
        L.append(f"  specialty: {r['specialty'] or 'not set'}; topics: {r['topical_focus'] or 'not set'}")
    if r["reject_reason"]:
        L.append(f"  rejected because: {r['reject_reason']}")
    if r["stale_override_reason"]:
        L.append(f"  approved on stale evidence, reason given: {r['stale_override_reason']}")
    if e["handles"]:
        L.append(f"  handles seen: {', '.join('@' + h for h in e['handles'])}; platform identity status {e['identity_status']}")
    for cat, c in sorted(view["categories"].items()):
        L.append(f"  category {cat}: {c['status']} ({c['basis']})")
    for w in view["wallets"]:
        L.append(f"  wallet {w['wallet_entity']}: {w['level']}, confidence {w['confidence']} ({'; '.join(w['reasons'])})")
    for o in view["owners"]:
        L.append(f"  owner claim by {o['account_entity']}: {o['level']} ({'; '.join(o['reasons'])})")
    ev = view["evidence_summary"]
    L.append(f"  evidence: {ev['total']} rows ({ev['fresh']} current, {ev['stale']} stale, {ev['undated']} undated)")
    for x in view["evidence"]:
        L.append(f"    {x['evidence_kind']} {x['ref']} captured {x['captured_at']}" + (f" note: {x['note']}" if x["note"] else ""))
    for l in view["listings"]:
        L.append(f"  listed by {l['source_key']} capture {l['capture_id']} ({l['freshness']}): the list states rank {l['rank_claimed_by_list']}, "
                 f"figures {l['metrics']}, period {l['stated_period']}; flags {l['flags']}; claim review {l['claim_review']}")
    for w in view["warnings"]:
        L.append(f"  warning: {w}")
    return "\n".join(L)


def counts(con) -> dict:
    out: dict[str, Any] = {"entities": {}, "records": {}, "fixture_entities": 0, "captures": 0, "live_captures": 0, "links": 0}
    for k, n in con.execute("SELECT entity_kind, COUNT(*) FROM social_registry_entities GROUP BY entity_kind"):
        out["entities"][k] = n
    for k, n in con.execute("SELECT review_state, COUNT(*) FROM social_registry_records GROUP BY review_state"):
        out["records"][k] = n
    out["fixture_entities"] = con.execute("SELECT COUNT(*) FROM social_registry_entities WHERE is_fixture=1").fetchone()[0]
    out["captures"] = con.execute("SELECT COUNT(*) FROM social_registry_captures").fetchone()[0]
    out["live_captures"] = con.execute("SELECT COUNT(*) FROM social_registry_captures WHERE is_fixture=0").fetchone()[0]
    out["links"] = con.execute("SELECT COUNT(*) FROM social_registry_links WHERE state='ASSERTED'").fetchone()[0]
    return out


# ---------- discovery from data the lab already has ----------

def import_catalyst_list(con, *, now: float | None = None, dry_run: bool = False) -> dict:
    """Bring the existing research list (memelab/catalyst/sources.py TRADER_RESEARCH_LIST) in as unverified candidates.
    These are research sources the lab already tracks, not rankings. Capture time is unknown, so the evidence is undated."""
    from ..catalyst import sources as cs
    t = _now(now)
    made = 0
    con.execute("SAVEPOINT cat_import")
    register_source(con, source_key="repo:catalyst-trader-list", source_kind="REPO_LIST", access_mode="repo", now=t,
                    permitted_basis="research list already in this repository (memelab/catalyst/sources.py); handles are research sources, not certified profitable traders (D-003)")
    for handle, display, reason in cs.TRADER_RESEARCH_LIST:
        eid = ensure_account(con, "x", handle=handle, display_name=display, now=t)
        if add_evidence(con, eid, "REPO_LIST", f"repo:memelab/catalyst/sources.py#{handle}", source_key="repo:catalyst-trader-list",
                        captured_at=None, note=f"listed in the repo research list because: {reason}"[:300], now=t):
            made += 1
    if dry_run:
        con.execute("ROLLBACK TO cat_import")
    con.execute("RELEASE cat_import")
    return {"source": "repo:catalyst-trader-list", "candidates_added": made, "note": "undated repo list: evidence is UNKNOWN age; approval needs a reason or newer evidence", "dry_run": dry_run}


def discover_from_narratives(con, run_id: int | None = None, *, min_amplified: int = 3, now: float | None = None) -> dict:
    """Propose accounts from a stored narrative snapshot (Phase 07): INDEPENDENT_ORIGINAL members become INFORMATION_ORIGINATOR proposals,
    accounts with at least min_amplified AMPLIFIER items become AMPLIFIER proposals. Proposals only: a person confirms them."""
    t = _now(now)
    if run_id is None:
        row = con.execute("SELECT run_id FROM social_narrative_runs ORDER BY window_end DESC, run_id DESC LIMIT 1").fetchone()
        if row is None:
            return {"run_id": None, "proposed": [], "note": "no narrative snapshot stored"}
        run_id = row[0]
    rows = con.execute("SELECT m.*, o.access_mode, o.observed_at FROM social_narrative_members m LEFT JOIN social_observations o ON o.id=m.observation_id "
                       "WHERE m.run_id=? AND m.account_id IS NOT NULL AND m.role IN ('INDEPENDENT_ORIGINAL','AMPLIFIER') ORDER BY m.account_id, m.claim_id",
                       (run_id,)).fetchall()
    by: dict[tuple[str, str], list] = {}
    for m in rows:
        by.setdefault((m["account_id"], m["role"]), []).append(m)
    proposed = []
    for (aid, role), ms in sorted(by.items()):
        cat = "INFORMATION_ORIGINATOR" if role == "INDEPENDENT_ORIGINAL" else "AMPLIFIER"
        if cat == "AMPLIFIER" and len(ms) < min_amplified:
            continue
        acc = store.get_account(con, aid)
        if acc is None:
            continue
        fx = all(m["access_mode"] == "fixture" for m in ms)
        eid = ensure_account(con, acc["platform"], handle=acc["handle"], provider_user_id=acc["provider_user_id"],
                             fixture_label=f"derived from fixture observations in narrative run {run_id}" if fx else None, now=t)
        for m in ms:
            add_evidence(con, eid, "NARRATIVE_MEMBER", f"narrative:{run_id}:{m['cluster_key']}:{m['claim_id']}", captured_at=m["observed_at"],
                         note=f"{m['role']} ({m['why']}) in {m['cluster_key']}", now=t)
        cur = category_state(con, eid).get(cat)
        if cur is None:
            clusters = len({m["cluster_key"] for m in ms})
            set_category(con, eid, cat, "PROPOSED", basis=f"narrative run {run_id}: {len(ms)} {role.lower().replace('_', ' ')} item(s) across {clusters} cluster(s)",
                         set_by="discovery:narratives-v1", now=t)
            proposed.append({"entity_id": eid, "category": cat, "items": len(ms)})
    return {"run_id": run_id, "proposed": proposed, "note": "proposals only; confirm with a reviewer and the category's evidence"}
