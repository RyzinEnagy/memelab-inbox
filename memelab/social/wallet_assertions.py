"""Phase 09: wallet-attribution assertions as independently auditable records (migration 9).

An assertion says: this social account is said to control this exact wallet, on this evidence, seen at this time, valid for this period.
Every field a reviewer needs to judge it is on the row; the row's claim never changes after it is written. Only its review and
status change, and each change is in social_wallet_audit with who and why.

Two questions are kept apart on purpose:
  real-world identity   who the person is. Always UNKNOWN here. Nothing in this module stores or infers a name.
  on-chain control      whether the key behind the wallet is operated by whoever runs the social account. This is a hypothesis with
                        evidence of different strength, and the level says which kind of evidence supports it.

Evidence types and what each can do (full table in WALLETS_09.md):
  OFFICIAL_SELF_DISCLOSURE   the account says the wallet is its own. SELF_CLAIMED. A claim, not proof.
  SIGNED_MESSAGE             a signature by the wallet over a message that names the account. Verified here (sigverify.py). With a
                             reviewer's approval it is SIGNATURE_VERIFIED. A valid signature over a message that does not name the
                             account proves nothing about the account and never counts.
  INDEPENDENT_LINKED_SOURCE  a source that neither is nor operates the account links them. Corroborates a self claim once reviewed.
  THIRD_PARTY_CLAIM          someone else says so. THIRD_PARTY_CLAIMED, never more.
  TRANSACTION_PATTERN        funding or timing similarity. HYPOTHESIS_ONLY, never counts toward a level.

Rules enforced here, each with a test in tests/test_social_wallets.py:
  - a self-disclosure must come from the account itself; a claim by any other entity is a third-party claim;
  - a signature must verify and name the account to count; approval of one that did not is refused;
  - nothing becomes SIGNATURE_VERIFIED or CORROBORATED without a named reviewer;
  - a wallet labelled as exchange custody, protocol or pool cannot be approved as controlled; relabel it with a source first;
  - another account holding verified control of the same wallet makes later claims DISPUTED;
  - confidence cannot be set higher than the evidence type supports;
  - revoked, superseded, rejected, unreviewed and out-of-window rows stay visible with the reason they are not counted.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from typing import Any

from ..modules.m09_holder_classification import KNOWN_LABELS
from . import registry as R, sigverify, store

VERSION = "wallet-assertions-v1"
EVIDENCE_TYPES = ("OFFICIAL_SELF_DISCLOSURE", "SIGNED_MESSAGE", "INDEPENDENT_LINKED_SOURCE", "THIRD_PARTY_CLAIM", "TRANSACTION_PATTERN")
LABEL_KINDS = ("CUSTODY_EXCHANGE", "CUSTODY_OTHER", "PROTOCOL", "POOL", "NO_SPECIAL_LABEL")
NON_CONTROL_KINDS = ("CUSTODY_EXCHANGE", "CUSTODY_OTHER", "PROTOCOL", "POOL")
CONF_RANK = {"UNKNOWN": 0, "LOW": 1, "MODERATE": 2, "HIGH": 3}
MAX_CONFIDENCE = {"OFFICIAL_SELF_DISCLOSURE": "LOW", "SIGNED_MESSAGE": "HIGH", "INDEPENDENT_LINKED_SOURCE": "MODERATE",
                  "THIRD_PARTY_CLAIM": "LOW", "TRANSACTION_PATTERN": "LOW"}
LEVELS = ("NONE", "HYPOTHESIS_ONLY", "THIRD_PARTY_CLAIMED", "SELF_CLAIMED", "CORROBORATED", "SIGNATURE_VERIFIED", "DISPUTED", "UNSUPPORTED_CUSTODY")
LINKED_STATUS = {"SIGNATURE_VERIFIED": "LINKED", "CORROBORATED": "LINKED", "SELF_CLAIMED": "CLAIMED", "THIRD_PARTY_CLAIMED": "NOT_LINKED",
                 "HYPOTHESIS_ONLY": "NOT_LINKED", "NONE": "NOT_LINKED", "DISPUTED": "DISPUTED", "UNSUPPORTED_CUSTODY": "NOT_LINKED"}
_BUILTIN_KIND = {"CEX": "CUSTODY_EXCHANGE", "POOL": "POOL", "LOCKER": "PROTOCOL"}
SKEW = 300


def _now(now): return time.time() if now is None else float(now)
def _sha(*p): return hashlib.sha256("|".join("" if x is None else str(x) for x in p).encode()).hexdigest()


def audit(con, target_type: str, target_id: Any, action: str, actor: str, reason: str | None, now: float,
          from_state: str | None = None, to_state: str | None = None) -> None:
    con.execute("INSERT INTO social_wallet_audit(target_type,target_id,action,from_state,to_state,actor,reason,at) VALUES (?,?,?,?,?,?,?,?)",
                (target_type, str(target_id), action, from_state, to_state, actor, reason, now))


def canon(chain: str, address: str) -> tuple[str, str]:
    ch = chain.strip().lower()
    return ch, store.normalize_contract(ch, address)


# ---------- labels ----------

def effective_label(con, chain: str, wallet: str) -> dict:
    """The newest active label row, else the built-in list the lab already uses to classify holders (m09), else no label.
    A NO_SPECIAL_LABEL row beats the built-in list: that is how a reviewer corrects a wrong built-in label, with a source."""
    ch, w = canon(chain, wallet)
    row = con.execute("SELECT * FROM social_wallet_labels WHERE chain=? AND wallet_address=? AND status='ACTIVE' ORDER BY label_id DESC LIMIT 1", (ch, w)).fetchone()
    if row is not None:
        return {"kind": row["label_kind"], "text": row["label_text"], "source": f"label:{row['label_id']}", "source_ref": row["source_ref"], "set_by": row["set_by"],
                "set_at": row["set_at"], "non_control": row["label_kind"] in NON_CONTROL_KINDS}
    if ch == "solana" and w in KNOWN_LABELS:
        cls, name = KNOWN_LABELS[w]
        kind = _BUILTIN_KIND.get(cls)
        if kind:
            return {"kind": kind, "text": name, "source": "builtin:m09", "source_ref": "repo:memelab/modules/m09_holder_classification.py", "set_by": None,
                    "set_at": None, "non_control": True}
    return {"kind": "NO_SPECIAL_LABEL", "text": None, "source": None, "source_ref": None, "set_by": None, "set_at": None, "non_control": False}


def set_label(con, chain: str, wallet: str, kind: str, *, source_ref: str, set_by: str, text: str | None = None,
              fixture: bool = False, now: float | None = None) -> dict:
    """Relabel a wallet. The old row stays, marked SUPERSEDED. A label needs a source a reviewer can open."""
    if kind not in LABEL_KINDS:
        raise ValueError(f"label kind must be one of {LABEL_KINDS}")
    t = _now(now)
    who = R._reviewer(set_by)
    ref = R.check_ref(source_ref, "source_ref", required=True)
    txt = R.clean_text(text, "label_text", 120)
    ch, w = canon(chain, wallet)
    prev = con.execute("SELECT label_id, label_kind FROM social_wallet_labels WHERE chain=? AND wallet_address=? AND status='ACTIVE' ORDER BY label_id DESC LIMIT 1",
                       (ch, w)).fetchone()
    cur = con.execute("INSERT INTO social_wallet_labels(chain,wallet_address,label_kind,label_text,source_ref,set_by,set_at,status,supersedes_label_id,is_fixture)"
                      " VALUES (?,?,?,?,?,?,?,'ACTIVE',?,?)", (ch, w, kind, txt, ref, who, t, prev["label_id"] if prev else None, int(fixture)))
    if prev:
        con.execute("UPDATE social_wallet_labels SET status='SUPERSEDED' WHERE label_id=?", (prev["label_id"],))
    audit(con, "LABEL", cur.lastrowid, "SET_LABEL", who, txt or ref, t, prev["label_kind"] if prev else None, kind)
    return {"label_id": cur.lastrowid, "supersedes": prev["label_id"] if prev else None, "kind": kind}


# ---------- recording ----------

def bound(message: str, handles: list[str]) -> bool:
    """A message names the account when one of its handles (3 characters or more) appears as a whole word, with or without @."""
    m = message.lower()
    for h in handles:
        h = (h or "").lower().lstrip("@")
        if len(h) >= 3 and re.search(rf"(?<![a-z0-9_]){re.escape(h)}(?![a-z0-9_])", m):
            return True
    return False


def record(con, *, account_entity: str, chain: str, wallet_address: str, evidence_type: str, evidence_ref: str, recorded_by: str,
           asserter_entity: str | None = None, message: str | None = None, signature: str | None = None, observed_at: Any = None,
           valid_from: Any = None, valid_to: Any = None, confidence: str | None = None, note: str | None = None,
           supersedes: int | None = None, registry_link_id: int | None = None, now: float | None = None) -> dict:
    if evidence_type not in EVIDENCE_TYPES:
        raise ValueError(f"evidence type must be one of {EVIDENCE_TYPES}")
    t = _now(now)
    who = R._reviewer(recorded_by)
    acct = R.get_entity(con, account_entity)
    if acct["entity_kind"] != "SOCIAL_ACCOUNT":
        raise ValueError("an attribution is asserted for a social account; use the account entity (a trader is reached through its accounts)")
    ch, w = canon(chain, wallet_address)
    ref = R.check_ref(evidence_ref, "evidence_ref", required=True)
    if evidence_type == "TRANSACTION_PATTERN" and not ref.startswith("tx:"):
        raise ValueError("a transaction pattern cites the transactions it rests on (evidence_ref tx:<signature>)")
    asserter = asserter_entity
    if evidence_type == "OFFICIAL_SELF_DISCLOSURE":
        if asserter not in (None, account_entity):
            raise ValueError("self_disclosure_must_come_from_the_account: a statement by any other entity is a THIRD_PARTY_CLAIM")
        asserter = account_entity
    elif evidence_type in ("INDEPENDENT_LINKED_SOURCE", "THIRD_PARTY_CLAIM"):
        if not asserter:
            raise ValueError(f"{evidence_type} needs asserter_entity: who published the statement")
        R.get_entity(con, asserter)
        if asserter == account_entity:
            raise ValueError("an account vouching for itself is OFFICIAL_SELF_DISCLOSURE, not a third-party statement")
    elif evidence_type == "SIGNED_MESSAGE":
        asserter = asserter or account_entity
        R.get_entity(con, asserter)
    else:
        asserter = None
    obs = store.to_utc(observed_at) or t
    if obs > t + SKEW:
        raise ValueError("observed_at is in the future")
    vf, vt = store.to_utc(valid_from), store.to_utc(valid_to)
    if vf is not None and vt is not None and vt < vf:
        raise ValueError("valid_to is before valid_from")
    note = R.clean_text(note, "note", 300)
    sig_check, sig_detail, verifier, msg_sha = "NOT_APPLICABLE", None, None, None
    if evidence_type == "SIGNED_MESSAGE":
        if not message or not signature:
            raise ValueError("SIGNED_MESSAGE needs the signed message text and the signature (public values; no key is ever involved)")
        raw = message.encode("utf-8")
        msg_sha = hashlib.sha256(raw).hexdigest()
        status, sig_detail = sigverify.verify(ch, w, raw, signature)
        verifier = sigverify.VERSION
        if status == "VALID":
            sig_check = "VALID_BOUND" if bound(message, R._handles(con, acct)) else "VALID_UNBOUND"
            if sig_check == "VALID_UNBOUND":
                sig_detail += "; the message does not name the account, so it says nothing about the account"
        else:
            sig_check = status
    else:
        if message or signature:
            raise ValueError("a message and signature belong to SIGNED_MESSAGE evidence only")
    cap = MAX_CONFIDENCE[evidence_type]
    if evidence_type == "SIGNED_MESSAGE" and sig_check != "VALID_BOUND":
        cap = "LOW"
    conf = confidence or cap
    if conf not in CONF_RANK:
        raise ValueError(f"confidence must be one of {tuple(CONF_RANK)}")
    if CONF_RANK[conf] > CONF_RANK[cap]:
        raise ValueError(f"confidence {conf} is higher than {evidence_type} supports here (maximum {cap})")
    hyp = ("RELATED_BY_ACTIVITY" if evidence_type == "TRANSACTION_PATTERN" else
           "ACCOUNT_CONTROLS_KEY" if sig_check == "VALID_BOUND" else "ACCOUNT_CLAIMS_WALLET")
    fixture = int(acct["is_fixture"])
    if asserter and asserter != account_entity and int(R.get_entity(con, asserter)["is_fixture"]) != fixture:
        raise ValueError("a fixture entity can only be linked to other fixture entities")
    key = _sha(account_entity, ch, w, evidence_type, asserter, ref, msg_sha, vf, vt)
    cur = con.execute(
        "INSERT OR IGNORE INTO social_wallet_assertions(assertion_key,account_entity,chain,wallet_address,evidence_type,asserter_entity,evidence_ref,"
        "evidence_sha256,signature_check,signature_detail,signature_verifier,observed_at,valid_from,valid_to,confidence,control_hypothesis,"
        "registry_link_id,recorded_by,recorded_at,note,is_fixture) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (key, account_entity, ch, w, evidence_type, asserter, ref, msg_sha, sig_check, sig_detail, verifier, obs, vf, vt, conf, hyp,
         registry_link_id, who, t, note, fixture))
    created = cur.rowcount == 1
    aid = cur.lastrowid if created else con.execute("SELECT assertion_id FROM social_wallet_assertions WHERE assertion_key=?", (key,)).fetchone()[0]
    if created:
        audit(con, "ASSERTION", aid, f"RECORD_{evidence_type}", who, note, t, None, "UNREVIEWED")
        if supersedes is not None:
            old = get(con, supersedes)
            if (old["account_entity"], old["chain"], old["wallet_address"]) != (account_entity, ch, w):
                raise ValueError("a replacement must be about the same account and the same wallet")
            if old["status"] != "ACTIVE":
                raise ValueError("only an active assertion can be superseded")
            con.execute("UPDATE social_wallet_assertions SET status='SUPERSEDED', superseded_by=?, status_at=?, status_by=?, status_reason=? WHERE assertion_id=?",
                        (aid, t, who, f"replaced by assertion {aid}", supersedes))
            audit(con, "ASSERTION", supersedes, "SUPERSEDE", who, f"replaced by {aid}", t, "ACTIVE", "SUPERSEDED")
    return {"assertion_id": aid, "created": created, "signature_check": sig_check, "confidence": conf, "control_hypothesis": hyp}


def get(con, assertion_id: int) -> sqlite3.Row:
    row = con.execute("SELECT * FROM social_wallet_assertions WHERE assertion_id=?", (assertion_id,)).fetchone()
    if row is None:
        raise ValueError(f"unknown assertion {assertion_id}")
    return row


def review(con, assertion_id: int, decision: str, *, reviewer: str, reason: str, now: float | None = None) -> dict:
    if decision not in ("APPROVED", "REJECTED"):
        raise ValueError("decision must be APPROVED or REJECTED")
    t = _now(now)
    who = R._reviewer(reviewer)
    why = R.clean_text(reason, "reason", 300)
    if not why:
        raise ValueError("reason: required to review an assertion")
    a = get(con, assertion_id)
    if a["status"] != "ACTIVE":
        raise ValueError(f"assertion is {a['status']}; only an active assertion is reviewed")
    if decision == "APPROVED":
        if a["evidence_type"] == "SIGNED_MESSAGE" and a["signature_check"] != "VALID_BOUND":
            raise ValueError(f"cannot approve: the signature check is {a['signature_check']}; only a valid signature over a message that names the account can be approved")
        lab = effective_label(con, a["chain"], a["wallet_address"])
        if lab["non_control"] and a["evidence_type"] != "TRANSACTION_PATTERN":
            raise ValueError(f"custody_or_protocol_wallet: the wallet is labelled {lab['kind']} ({lab['text'] or lab['source']}); a person does not control "
                             "an exchange, protocol or pool address. Correct the label with a source first if it is wrong.")
    con.execute("UPDATE social_wallet_assertions SET review_state=?, reviewed_by=?, reviewed_at=?, review_reason=? WHERE assertion_id=?", (decision, who, t, why, assertion_id))
    audit(con, "ASSERTION", assertion_id, f"REVIEW_{decision}", who, why, t, a["review_state"], decision)
    return {"assertion_id": assertion_id, "review_state": decision}


def revoke(con, assertion_id: int, *, reviewer: str, reason: str, now: float | None = None) -> dict:
    t = _now(now)
    who = R._reviewer(reviewer)
    why = R.clean_text(reason, "reason", 300)
    if not why:
        raise ValueError("reason: required to revoke")
    a = get(con, assertion_id)
    if a["status"] != "ACTIVE":
        raise ValueError(f"assertion is already {a['status']}")
    con.execute("UPDATE social_wallet_assertions SET status='REVOKED', status_at=?, status_by=?, status_reason=? WHERE assertion_id=?", (t, who, why, assertion_id))
    audit(con, "ASSERTION", assertion_id, "REVOKE", who, why, t, "ACTIVE", "REVOKED")
    return {"assertion_id": assertion_id, "status": "REVOKED"}


# ---------- explaining ----------

_SIG_WHY = {"VALID_UNBOUND": "signature_valid_but_message_does_not_name_the_account", "INVALID": "signature_does_not_verify",
            "MALFORMED": "signature_malformed", "UNSUPPORTED": "signature_check_not_supported_for_this_chain"}


def _in_window(a, at: float | None) -> bool:
    if at is None:
        return True
    return (a["valid_from"] is None or a["valid_from"] <= at) and (a["valid_to"] is None or at <= a["valid_to"])


def _view(con, a, account_cluster: list[str], at: float | None, label: dict) -> dict:
    """One assertion, with what it contributes and, when it contributes nothing, why."""
    v = {k: a[k] for k in ("assertion_id", "account_entity", "chain", "wallet_address", "evidence_type", "asserter_entity", "evidence_ref", "evidence_sha256",
                           "signature_check", "signature_detail", "observed_at", "valid_from", "valid_to", "confidence", "control_hypothesis",
                           "real_world_identity", "review_state", "reviewed_by", "reviewed_at", "review_reason", "status", "status_reason", "superseded_by",
                           "recorded_by", "recorded_at", "note", "is_fixture")}
    why: list[str] = []
    counts = "NONE"
    if a["status"] != "ACTIVE":
        why.append(a["status"].lower() + (f"_by_{a['superseded_by']}" if a["superseded_by"] else ""))
    elif a["review_state"] == "REJECTED":
        why.append("rejected_by_reviewer")
    elif not _in_window(a, at):
        why.append("outside_validity_window")
    else:
        et = a["evidence_type"]
        approved = a["review_state"] == "APPROVED"
        if et == "TRANSACTION_PATTERN":
            counts = "HYPOTHESIS"
            why.append("pattern_evidence_never_counts_toward_control")
        elif et == "OFFICIAL_SELF_DISCLOSURE":
            counts = "SELF_CLAIM"
        elif et == "SIGNED_MESSAGE":
            if a["signature_check"] != "VALID_BOUND":
                why.append(_SIG_WHY.get(a["signature_check"], "signature_not_usable"))
            elif approved:
                counts = "CONTROL_PROOF"
            else:
                counts = "SELF_CLAIM"
                why.append("signature_verified_awaiting_review")
        else:
            ok, reason = R._independent(con, account_cluster, a["asserter_entity"])
            if not ok:
                why.append(f"asserter_not_independent:{reason}")
            elif et == "INDEPENDENT_LINKED_SOURCE" and approved:
                counts = "INDEPENDENT"
            else:
                counts = "THIRD_PARTY"
                if et == "INDEPENDENT_LINKED_SOURCE":
                    why.append("independent_source_awaiting_review")
    if counts != "NONE" and counts != "HYPOTHESIS" and label["non_control"]:
        why.append(f"wallet_labelled_{label['kind'].lower()}")
    v["counts_as"] = counts
    v["why_not_counted"] = why
    return v


def adopt_registry_links(con, *, actor: str = "registry-adopt", now: float | None = None) -> dict:
    """Bring Phase 08 registry wallet links in as assertions so there is one place to inspect. Self-disclosures and third-party labels only:
    an ON_CHAIN_PROOF link has no signature the lab can re-check, so it is listed as not adopted and a SIGNED_MESSAGE assertion should be recorded."""
    t = _now(now)
    adopted, skipped = [], []
    for l in R.active_links(con, None, ("WALLET_SELF_DISCLOSED", "WALLET_THIRD_PARTY_LABEL", "WALLET_ON_CHAIN_PROOF")):
        if con.execute("SELECT 1 FROM social_wallet_assertions WHERE registry_link_id=?", (l["link_id"],)).fetchone():
            continue
        if l["link_type"] == "WALLET_ON_CHAIN_PROOF":
            skipped.append({"link_id": l["link_id"], "reason": "no re-checkable signature; record a SIGNED_MESSAGE assertion"})
            continue
        w = R.get_entity(con, l["to_entity"])
        et = "OFFICIAL_SELF_DISCLOSURE" if l["link_type"] == "WALLET_SELF_DISCLOSED" else "THIRD_PARTY_CLAIM"
        ref = l["evidence_ref"]
        if not ref:
            skipped.append({"link_id": l["link_id"], "reason": "no direct evidence reference"})
            continue
        try:
            r = record(con, account_entity=l["from_entity"], chain=w["chain"], wallet_address=w["wallet_address"], evidence_type=et, evidence_ref=ref,
                       recorded_by=actor, asserter_entity=None if et == "OFFICIAL_SELF_DISCLOSURE" else l["asserted_by_entity"],
                       observed_at=l["asserted_at"], valid_from=l["valid_from"], valid_to=l["valid_to"], registry_link_id=l["link_id"],
                       note=f"adopted from registry link {l['link_id']}", now=t)
        except ValueError as e:
            skipped.append({"link_id": l["link_id"], "reason": str(e)[:120]})
            continue
        if l["review_state"] == "APPROVED":
            con.execute("UPDATE social_wallet_assertions SET review_state='APPROVED', reviewed_by=?, reviewed_at=?, review_reason=? WHERE assertion_id=?",
                        (l["reviewed_by"] or actor, l["reviewed_at"] or t, f"approved on registry link {l['link_id']}", r["assertion_id"]))
            audit(con, "ASSERTION", r["assertion_id"], "REVIEW_APPROVED", l["reviewed_by"] or actor, f"carried over from registry link {l['link_id']}", t, "UNREVIEWED", "APPROVED")
        adopted.append({"link_id": l["link_id"], "assertion_id": r["assertion_id"]})
    return {"adopted": adopted, "skipped": skipped}


def explain(con, account_entity: str, chain: str, wallet_address: str, *, as_of: Any = None, now: float | None = None) -> dict:
    """The reviewer's view: why this account is, or is not, linked to this wallet. Every assertion about the wallet is listed with what it
    contributes or why it does not, then the level, the control basis, the wallet's label, funding hypotheses and the real-world identity (UNKNOWN)."""
    R.get_entity(con, account_entity)
    ch, w = canon(chain, wallet_address)
    at = store.to_utc(as_of)
    cluster = R.identity_cluster(con, account_entity)
    label = effective_label(con, ch, w)
    rows = con.execute("SELECT * FROM social_wallet_assertions WHERE chain=? AND wallet_address=? ORDER BY assertion_id", (ch, w)).fetchall()
    mine, others = [], []
    for a in rows:
        a_cluster = R.identity_cluster(con, a["account_entity"])
        (mine if a["account_entity"] in cluster else others).append(_view(con, a, a_cluster if a["account_entity"] not in cluster else cluster, at, label))
    kinds = {v["counts_as"] for v in mine}
    other_proof = [v for v in others if v["counts_as"] == "CONTROL_PROOF"]
    other_claim = [v for v in others if v["counts_as"] in ("SELF_CLAIM", "CONTROL_PROOF")]
    reasons: list[str] = []
    if label["non_control"]:
        level = "UNSUPPORTED_CUSTODY"
        reasons.append(f"wallet_labelled_{label['kind'].lower()}: {label['text'] or label['source']} ({label['source']})")
    elif (kinds & {"SELF_CLAIM", "CONTROL_PROOF", "INDEPENDENT", "THIRD_PARTY"}) and other_proof:
        level = "DISPUTED"
        reasons.append("another account holds verified control of this wallet: " + ", ".join(sorted({v["account_entity"] for v in other_proof})))
    elif "CONTROL_PROOF" in kinds:
        level = "SIGNATURE_VERIFIED"
        reasons.append("a reviewed signature by the wallet over a message naming the account")
    elif "SELF_CLAIM" in kinds and "INDEPENDENT" in kinds:
        level = "CORROBORATED"
        reasons.append("the account's own claim plus a reviewed statement from an independent source")
    elif "SELF_CLAIM" in kinds:
        level = "SELF_CLAIMED"
        reasons.append("the account says so; nothing independent confirms it")
        if other_claim:
            reasons.append("also claimed by: " + ", ".join(sorted({v["account_entity"] for v in other_claim})))
    elif kinds & {"INDEPENDENT", "THIRD_PARTY"}:
        level = "THIRD_PARTY_CLAIMED"
        reasons.append("only someone else says so")
    elif "HYPOTHESIS" in kinds:
        level = "HYPOTHESIS_ONLY"
        reasons.append("only transaction-pattern evidence, which never establishes control")
    else:
        level = "NONE"
        reasons.append("no counted assertion links this account to this wallet" + (" (assertions exist but none count, see why_not_counted)" if mine else ""))
    awaiting = [v["assertion_id"] for v in mine if v["counts_as"] != "NONE" and v["counts_as"] != "HYPOTHESIS" and v["review_state"] == "UNREVIEWED"]
    hyps = funding_for(con, ch, w)
    related = []
    for h in hyps:
        for other in [h["funder_address"]] + h["members"]:
            if other == w:
                continue
            for a in con.execute("SELECT DISTINCT account_entity FROM social_wallet_assertions WHERE chain=? AND wallet_address=? AND status='ACTIVE'", (ch, other)):
                related.append({"wallet": other, "account_entity": a[0], "via_hypothesis": h["hypothesis_id"], "counts_toward_level": False,
                                "note": "related by funding only; this does not attribute this wallet to that account"})
    return {"account_entity": account_entity, "chain": ch, "wallet_address": w, "as_of": at, "level": level, "linked": LINKED_STATUS[level],
            "linked_status": LINKED_STATUS[level], "confidence": _level_conf(level), "reasons": reasons, "awaiting_review": awaiting,
            "real_world_identity": "UNKNOWN", "identity_note": "No name or real-world identity is recorded or implied; this concerns control of a key only.",
            "wallet_label": label, "assertions": mine, "other_accounts_assertions": others, "funding_hypotheses": hyps, "related_by_funding": related,
            "version": VERSION}


def _level_conf(level: str) -> str:
    return {"SIGNATURE_VERIFIED": "HIGH", "CORROBORATED": "MODERATE", "SELF_CLAIMED": "LOW", "THIRD_PARTY_CLAIMED": "LOW", "HYPOTHESIS_ONLY": "LOW"}.get(level, "UNKNOWN")


def funding_for(con, chain: str, wallet: str) -> list[dict]:
    out = []
    for h in con.execute("SELECT * FROM social_wallet_funding_hypotheses WHERE chain=? ORDER BY hypothesis_id", (chain,)):
        members = json.loads(h["members_json"])
        if wallet == h["funder_address"] or wallet in members:
            out.append({"hypothesis_id": h["hypothesis_id"], "funder_address": h["funder_address"], "members": members, "funder_label": h["funder_label"],
                        "informative": bool(h["informative"]), "status": h["status"], "evidence": json.loads(h["evidence_json"]),
                        "meaning": ("shared funding by an exchange, custody, protocol or pool address says nothing about common control" if not h["informative"]
                                    else "the first funding we saw for these wallets came from this address: a reason to look, not evidence of common control")})
    return out


def report(view: dict) -> str:
    L = [f"Account {view['account_entity']}  wallet {view['chain']}:{view['wallet_address']}",
         f"Level: {view['level']} ({view['linked_status']}), confidence {view['confidence']}",
         "Real-world identity: UNKNOWN. This says nothing about who the person is."]
    L += ["Why: " + r for r in view["reasons"]]
    lab = view["wallet_label"]
    if lab["kind"] != "NO_SPECIAL_LABEL":
        L.append(f"Wallet label: {lab['kind']} ({lab['text'] or ''}) from {lab['source']}")
    if view["awaiting_review"]:
        L.append("Awaiting review: assertions " + ", ".join(map(str, view["awaiting_review"])))
    for v in view["assertions"]:
        L.append(f"  #{v['assertion_id']} {v['evidence_type']} by {v['asserter_entity'] or '-'} ref {v['evidence_ref']} seen {v['observed_at']} "
                 f"[{v['review_state']}/{v['status']}] counts as {v['counts_as']}" + (f"; not counted: {', '.join(v['why_not_counted'])}" if v["why_not_counted"] else ""))
    for v in view["other_accounts_assertions"]:
        L.append(f"  (other account {v['account_entity']}) #{v['assertion_id']} {v['evidence_type']} [{v['review_state']}/{v['status']}] counts as {v['counts_as']}")
    for h in view["funding_hypotheses"]:
        L.append(f"  funding hypothesis {h['hypothesis_id']}: funder {h['funder_address'][:8]}.. members {len(h['members'])}, {h['meaning']}")
    for r in view["related_by_funding"]:
        L.append(f"  related by funding only: {r['wallet'][:8]}.. has an assertion from {r['account_entity']}; not counted here")
    return "\n".join(L)
