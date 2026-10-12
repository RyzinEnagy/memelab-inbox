"""Phase 09: monitor selected public wallets and store what they did as classified, provenance-linked events (migration 9).

What this is: an observation log. A transfer, a swap and an LP operation are different events and are never folded together. Every event
carries the transaction signature, chain, block time, fee, counterparties, the provider and a hash chain back to the response it came from.

What this is not: profit and loss. No prices, no cost basis, no realised or unrealised figures exist in these tables, and a token sent to
another address is never a sale. The next phase decides how, and whether, activity becomes performance.

Wallet-level monitoring does not need an owner. A wallet can be tracked with no attribution at all, and a tracked wallet is never described
as belonging to a person here. Who might control it is the job of wallet_assertions.py.

Provider abstraction: every provider is converted to one normalized transaction (memelab.wallet.tx/1, see normalize_* below) before
classification. The Helius adapter is the only one built; an EVM wallet can be tracked and attributed, but without a transaction provider its
coverage is recorded as a GAP, never as "no activity".
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from ..chains import registry as chain_registry
from ..wallet import STABLES as _SOL_STABLES
from . import registry as R, sigverify, store
from .wallet_assertions import NON_CONTROL_KINDS, audit, canon, effective_label

VERSION = "wallet-activity-v1"
CLASSIFIER_VERSION = "wallet-classifier-v1"
SCHEMA_FETCH = "memelab.wallet.fetch/1"     # bridge result wrapper around helius_wallet_tx:<wallet> bodies
SCHEMA_TX = "memelab.wallet.tx/1"           # provider-neutral transactions
MAX_ACTIVE = 25
DEFAULT_MAX_AGE = 12 * 3600
SKEW = 300
DUST = 1e-9

SWAP_TYPES = {"SWAP", "SWAP_EXACT_OUT", "SWAP_WITH_PRICE_IMPACT"}
TRANSFER_TYPES = {"TRANSFER", "TRANSFER_PAYMENT"}
LP_ADD_TYPES = {"ADD_LIQUIDITY", "ADD_LIQUIDITY_ONE_SIDE", "ADD_LIQUIDITY_BY_STRATEGY", "ADD_LIQUIDITY_BY_WEIGHT", "ADD_BALANCE_LIQUIDITY", "ADD_IMBALANCE_LIQUIDITY"}
LP_REMOVE_TYPES = {"REMOVE_LIQUIDITY", "REMOVE_ALL_LIQUIDITY", "REMOVE_LIQUIDITY_BY_RANGE", "REMOVE_LIQUIDITY_SINGLE_SIDE", "REMOVE_BALANCE_LIQUIDITY", "WITHDRAW_LIQUIDITY"}
EVENT_TYPES = ("SWAP", "LP_ADD", "LP_REMOVE", "TOKEN_TRANSFER_IN", "TOKEN_TRANSFER_OUT", "NATIVE_TRANSFER_IN", "NATIVE_TRANSFER_OUT", "FAILED", "UNCLASSIFIED")
_EVM_HASH = re.compile(r"^0x[0-9a-fA-F]{64}$")


def _now(now): return time.time() if now is None else float(now)
def _sha(*p): return hashlib.sha256("|".join("" if x is None else str(x) for x in p).encode()).hexdigest()
def canonical_json(o: Any) -> str: return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
def row_sha(o: Any) -> str: return hashlib.sha256(canonical_json(o).encode()).hexdigest()


# ---------- tracked wallets ----------

def _tracked_row(con, chain: str, wallet: str):
    return con.execute("SELECT * FROM social_tracked_wallets WHERE chain=? AND wallet_address=?", (chain, wallet)).fetchone()


def add_wallet(con, chain: str, wallet: str, *, reason: str, added_by: str, selection_basis: str = "MANUAL", max_tx: int = 50,
               allow_custody: bool = False, fixture: bool = False, max_active: int = MAX_ACTIVE, now: float | None = None) -> dict:
    """Start monitoring one public wallet. Safe defaults: a reason and a name are required, at most 25 wallets are active, a wallet labelled
    exchange custody, protocol or pool is refused unless allowed on purpose, 50 transactions per fetch, and fetches begin at the time of adding."""
    t = _now(now)
    who = R._reviewer(added_by)
    why = R.clean_text(reason, "reason", 300)
    if not why:
        raise ValueError("reason: say why this wallet is worth watching (no claim about its owner)")
    if selection_basis not in ("MANUAL", "REGISTRY_ENTITY", "DISCOVERED"):
        raise ValueError("selection_basis must be MANUAL, REGISTRY_ENTITY or DISCOVERED")
    if not 1 <= int(max_tx) <= 100:
        raise ValueError("max_tx must be between 1 and 100")
    ch, w = canon(chain, wallet)
    lab = effective_label(con, ch, w)
    if lab["non_control"] and not allow_custody:
        raise ValueError(f"custody_wallet_not_monitored_by_default: this address is labelled {lab['kind']} ({lab['text'] or lab['source']}); "
                         "its activity is many people's, not one trader's. Pass allow_custody to watch it anyway.")
    row = _tracked_row(con, ch, w)
    if row is not None:
        if bool(row["is_fixture"]) != bool(fixture):
            raise ValueError("this wallet exists with a different fixture flag; fixture and real data never share a wallet")
        if row["status"] == "ACTIVE":
            return {"tracked_id": row["tracked_id"], "created": False, "status": "ACTIVE"}
    active = con.execute("SELECT COUNT(*) FROM social_tracked_wallets WHERE status='ACTIVE'").fetchone()[0]
    if active >= max_active:
        raise ValueError(f"too_many_active_wallets: {active} are active (limit {max_active}); pause or remove one first")
    if row is not None:
        con.execute("UPDATE social_tracked_wallets SET status='ACTIVE', status_by=?, status_at=?, status_reason=?, max_tx_per_fetch=?, custody_override=? WHERE tracked_id=?",
                    (who, t, why, int(max_tx), int(allow_custody), row["tracked_id"]))
        audit(con, "TRACKED_WALLET", row["tracked_id"], "REACTIVATE", who, why, t, row["status"], "ACTIVE")
        return {"tracked_id": row["tracked_id"], "created": False, "status": "ACTIVE"}
    cur = con.execute("INSERT INTO social_tracked_wallets(chain,wallet_address,status,reason,selection_basis,added_by,added_at,watch_since,max_tx_per_fetch,"
                      "custody_override,is_fixture) VALUES (?,?,'ACTIVE',?,?,?,?,?,?,?,?)", (ch, w, why, selection_basis, who, t, t, int(max_tx), int(allow_custody), int(fixture)))
    audit(con, "TRACKED_WALLET", cur.lastrowid, "ADD", who, why, t, None, "ACTIVE")
    return {"tracked_id": cur.lastrowid, "created": True, "status": "ACTIVE"}


def set_status(con, chain: str, wallet: str, status: str, *, by: str, reason: str, now: float | None = None) -> dict:
    """pause: keep the wallet and its history, stop ingesting. remove: stop and mark REMOVED. Nothing is deleted; history stays readable."""
    if status not in ("ACTIVE", "PAUSED", "REMOVED"):
        raise ValueError("status must be ACTIVE, PAUSED or REMOVED")
    t = _now(now)
    who = R._reviewer(by)
    why = R.clean_text(reason, "reason", 300)
    if not why:
        raise ValueError("reason: required")
    ch, w = canon(chain, wallet)
    row = _tracked_row(con, ch, w)
    if row is None:
        raise ValueError("this wallet is not tracked")
    if status == "ACTIVE" and row["status"] != "ACTIVE":
        return add_wallet(con, ch, w, reason=why, added_by=who, max_tx=row["max_tx_per_fetch"], allow_custody=bool(row["custody_override"]),
                          fixture=bool(row["is_fixture"]), now=t)
    con.execute("UPDATE social_tracked_wallets SET status=?, status_by=?, status_at=?, status_reason=? WHERE tracked_id=?", (status, who, t, why, row["tracked_id"]))
    audit(con, "TRACKED_WALLET", row["tracked_id"], f"SET_{status}", who, why, t, row["status"], status)
    return {"tracked_id": row["tracked_id"], "status": status}


def list_wallets(con, status: str | None = None) -> list[dict]:
    q, a = "SELECT * FROM social_tracked_wallets", []
    if status:
        q += " WHERE status=?"
        a.append(status)
    out = []
    for r in con.execute(q + " ORDER BY chain, wallet_address", a):
        d = dict(r)
        d["label"] = effective_label(con, r["chain"], r["wallet_address"])["kind"]
        d["owner_claimed"] = None   # wallet-level monitoring claims no owner; see wallet_assertions.explain for attribution
        out.append(d)
    return out


# ---------- normalizing providers ----------

def valid_signature(chain: str, sig: Any) -> bool:
    if not isinstance(sig, str) or not sig:
        return False
    fam = chain_registry.family(chain)
    if fam == "solana":
        try:
            return len(sigverify.b58decode(sig)) == 64
        except ValueError:
            return False
    return bool(_EVM_HASH.match(sig))


def normalize_helius(row: dict) -> dict:
    """One row of the helius_wallet_tx projection (bridge/collector.js) as a normalized transaction. The older helius_tx projection cut the
    signature to 12 characters, which is not a transaction signature; it is rejected as INVALID_SIGNATURE rather than stored."""
    typ = row.get("type")
    kind = ("SWAP" if typ in SWAP_TYPES else "TRANSFER" if typ in TRANSFER_TYPES else "ADD_LIQUIDITY" if typ in LP_ADD_TYPES
            else "REMOVE_LIQUIDITY" if typ in LP_REMOVE_TYPES else "OTHER")
    nt, tt = row.get("nt") or [], row.get("tt") or []
    trunc = bool((row.get("nn") is not None and row["nn"] > len(nt)) or (row.get("nk") is not None and row["nk"] > len(tt)))
    fee = row.get("fee")
    return {"signature": row.get("sig"), "slot": row.get("slot"), "block_time": row.get("ts"), "failed": bool(row.get("err")), "kind": kind,
            "provider_type": typ, "source": row.get("src"), "fee": (fee / 1e9) if isinstance(fee, (int, float)) else None, "fee_unit": "SOL",
            "fee_payer": row.get("payer"), "native": [list(x) for x in nt], "tokens": [list(x) for x in tt], "truncated": trunc}


def normalize_generic(row: dict) -> dict:
    kind = row.get("kind") if row.get("kind") in ("SWAP", "TRANSFER", "ADD_LIQUIDITY", "REMOVE_LIQUIDITY") else "OTHER"
    return {"signature": row.get("signature"), "slot": row.get("slot"), "block_time": row.get("block_time"), "failed": row.get("status") == "failed",
            "kind": kind, "provider_type": row.get("kind"), "source": row.get("source"), "fee": row.get("fee"), "fee_unit": row.get("fee_unit"),
            "fee_payer": row.get("fee_payer"), "native": row.get("native") or [], "tokens": row.get("tokens") or [], "truncated": bool(row.get("truncated"))}


# ---------- classification ----------

def _quote_assets(chain: str) -> set[str]:
    c = chain_registry.CHAINS.get(chain, {})
    out = {str(c.get("wrapped_native", "")).lower()} | {str(k).lower() for k in (c.get("stables") or {})}
    if chain == "solana":
        out |= {chain_registry.CHAINS["solana"]["wrapped_native"]} | set(_SOL_STABLES) | {"NATIVE"}
    else:
        out |= {"NATIVE"}
    return {x for x in out if x}


def _legs(chain: str, wallet: str, tx: dict) -> list[dict]:
    legs = []
    for f, t, amt in tx["native"]:
        if not isinstance(amt, (int, float)) or amt <= DUST or f == t:
            continue
        if t == wallet or f == wallet:
            legs.append({"asset_kind": "NATIVE", "contract": None, "direction": "IN" if t == wallet else "OUT", "amount": float(amt),
                         "counterparty": f if t == wallet else t})
    for f, t, mint, amt in tx["tokens"]:
        if not isinstance(amt, (int, float)) or amt <= DUST or f == t:
            continue
        if t == wallet or f == wallet:
            legs.append({"asset_kind": "TOKEN", "contract": store.normalize_contract(chain, mint), "direction": "IN" if t == wallet else "OUT", "amount": float(amt),
                         "counterparty": f if t == wallet else t})
    return legs


def classify(chain: str, wallet: str, tx: dict, con=None) -> dict:
    """Event type from the provider's type AND the shape of what moved. Disagreement is UNCLASSIFIED with the reason, never a guess.
    A transfer is never a sale: token out with native in under a TRANSFER type stays UNCLASSIFIED."""
    legs = _legs(chain, wallet, tx)
    for i, lg in enumerate(legs):
        lg["leg_index"] = i
        lab = effective_label(con, chain, lg["counterparty"]) if con is not None and lg["counterparty"] else {"kind": "NO_SPECIAL_LABEL"}
        lg["counterparty_label"] = None if lab["kind"] == "NO_SPECIAL_LABEL" else lab["kind"]
    ins = [g for g in legs if g["direction"] == "IN"]
    outs = [g for g in legs if g["direction"] == "OUT"]
    basis = {"provider_type": tx["provider_type"], "kind": tx["kind"], "legs_in": len(ins), "legs_out": len(outs), "truncated": tx["truncated"],
             "token_in": sum(g["asset_kind"] == "TOKEN" for g in ins), "token_out": sum(g["asset_kind"] == "TOKEN" for g in outs),
             "native_in": sum(g["asset_kind"] == "NATIVE" for g in ins), "native_out": sum(g["asset_kind"] == "NATIVE" for g in outs)}
    conf = "MODERATE" if tx["truncated"] else "HIGH"
    side = None
    if tx["failed"]:
        etype, rule, conf = "FAILED", "failed.provider_error.v1", "HIGH"
        legs = []
    elif not legs:
        etype, rule, conf = "UNCLASSIFIED", "none.no_wallet_legs.v1", "LOW"
    elif tx["kind"] == "SWAP":
        if ins and outs:
            etype, rule = "SWAP", "swap.two_sides.v1"
            q = _quote_assets(chain)
            asset = lambda g: "NATIVE" if g["asset_kind"] == "NATIVE" else g["contract"]
            in_nq = {asset(g) for g in ins} - q
            out_nq = {asset(g) for g in outs} - q
            if in_nq and not out_nq:
                side = "BUY"
            elif out_nq and not in_nq:
                side = "SELL"
            elif in_nq and out_nq:
                side = "TOKEN_TO_TOKEN"
        else:
            etype, rule, conf = "UNCLASSIFIED", "swap.one_sided.v1", "LOW"
    elif tx["kind"] == "ADD_LIQUIDITY":
        etype, rule = ("LP_ADD", "lp.add.v1") if outs else ("UNCLASSIFIED", "lp.add_without_outflow.v1")
        conf = conf if outs else "LOW"
    elif tx["kind"] == "REMOVE_LIQUIDITY":
        etype, rule = ("LP_REMOVE", "lp.remove.v1") if ins else ("UNCLASSIFIED", "lp.remove_without_inflow.v1")
        conf = conf if ins else "LOW"
    elif tx["kind"] == "TRANSFER":
        ti, to = basis["token_in"], basis["token_out"]
        ni, no = basis["native_in"], basis["native_out"]
        if ti and to:
            etype, rule, conf = "UNCLASSIFIED", "transfer.mixed_token_directions.v1", "LOW"
        elif ti:
            etype, rule = ("UNCLASSIFIED", "transfer.token_in_with_native_out.v1") if no else ("TOKEN_TRANSFER_IN", "transfer.token_in.v1")
            conf = "LOW" if no else conf
        elif to:
            etype, rule = ("UNCLASSIFIED", "transfer.token_out_with_native_in.v1") if ni else ("TOKEN_TRANSFER_OUT", "transfer.token_out.v1")
            conf = "LOW" if ni else conf
        elif ni and no:
            etype, rule, conf = "UNCLASSIFIED", "transfer.mixed_native_directions.v1", "LOW"
        elif ni:
            etype, rule = "NATIVE_TRANSFER_IN", "transfer.native_in.v1"
        else:
            etype, rule = "NATIVE_TRANSFER_OUT", "transfer.native_out.v1"
    else:
        etype, rule, conf = "UNCLASSIFIED", "provider_type_unmapped.v1", "LOW"
    cps, seen = [], set()
    for g in legs:
        if g["counterparty"] and g["counterparty"] not in seen:
            seen.add(g["counterparty"])
            cps.append({"address": g["counterparty"], "label": g["counterparty_label"]})
    custody = next((c["label"] for c in cps if c["label"] in ("CUSTODY_EXCHANGE", "CUSTODY_OTHER")), None)
    return {"event_type": etype, "swap_side": side, "rule": rule, "confidence": conf, "basis": basis, "legs": legs, "counterparties": cps, "custody_touch": custody}


# ---------- ingestion ----------

def _units(doc: dict) -> tuple[str, str, float | None, list[dict]]:
    """(provider, chain, fetched_at, units). A unit is one wallet's response: wallet, http_status, retry_after, rows (normalized) and raw rows."""
    sch = doc.get("schema")
    if sch == SCHEMA_FETCH:
        provider, chain = doc.get("provider", "helius"), doc.get("chain", "solana")
        units = []
        for key, res in (doc.get("results") or {}).items():
            if not key.startswith("helius_wallet_tx:"):
                continue
            body = res.get("body") if isinstance(res, dict) else res
            units.append({"wallet": key.split(":", 1)[1], "status": res.get("s", 200) if isinstance(res, dict) else 200, "retry_after": res.get("retry_after") if isinstance(res, dict) else None,
                          "raw": body if isinstance(body, list) else None, "norm": normalize_helius})
        return provider, chain, store.to_utc(doc.get("fetched_at")), units
    if sch == SCHEMA_TX:
        provider, chain = doc.get("provider", "unknown"), doc.get("chain")
        units = [{"wallet": w, "status": v.get("http_status", 200), "retry_after": v.get("retry_after"), "raw": v.get("txs") if isinstance(v.get("txs"), list) else None,
                  "norm": normalize_generic} for w, v in (doc.get("wallets") or {}).items()]
        return provider, chain, store.to_utc(doc.get("fetched_at")), units
    raise ValueError(f"document schema must be {SCHEMA_FETCH} or {SCHEMA_TX}")


def ingest(con, doc: dict, *, now: float | None = None, max_age: int = DEFAULT_MAX_AGE, source_ref: str | None = None,
           payload_sha: str | None = None, fixture: bool = False) -> dict:
    """Store the events of every tracked wallet in one provider document. One wallet failing (429, bad rows, paused) never stops the others.
    Returns per-wallet results and an overall status: OK, PARTIAL (something degraded or rejected) or FAILED (nothing usable)."""
    t = _now(now)
    provider, chain, fetched_at, units = _units(doc)
    if chain not in chain_registry.CHAINS:
        raise ValueError(f"unknown chain {chain!r}")
    if fetched_at is None:
        raise ValueError("fetched_at is required: an observation without a fetch time cannot be judged fresh or stale")
    if fetched_at > t + SKEW:
        raise ValueError("fetched_at is in the future")
    psha = payload_sha or row_sha(doc)
    stale = (t - fetched_at) > max_age
    results, worst = [], "OK"
    rank = {"OK": 0, "DEGRADED": 1, "RATE_LIMITED": 2, "DOWN": 3}
    connector = f"wallet:{provider}:{chain}"
    gaps = []
    for u in units:
        try:
            w = canon(chain, u["wallet"])[1]
        except ValueError:
            results.append({"wallet": u["wallet"], "status": "REJECTED", "detail": "invalid address for chain"})
            worst = max(worst, "DEGRADED", key=rank.get)
            continue
        tr = _tracked_row(con, chain, w)
        if tr is None:
            results.append({"wallet": w, "status": "UNTRACKED", "detail": "not a tracked wallet; ignored"})
            continue
        if bool(tr["is_fixture"]) != bool(fixture):
            raise ValueError("fixture documents go to fixture wallets only, and real documents to real wallets only")
        fkey = _sha(provider, chain, w, fetched_at, psha)
        if con.execute("SELECT 1 FROM social_wallet_fetches WHERE fetch_key=?", (fkey,)).fetchone():
            results.append({"wallet": w, "status": "ALREADY_INGESTED"})
            continue

        def put_fetch(status, **kw):
            cur = con.execute("INSERT INTO social_wallet_fetches(fetch_key,provider,chain,wallet_address,fetched_at,http_status,status,rows_seen,rows_stored,rows_rejected,"
                              "payload_sha256,source_ref,retry_after_s,detail,rejects_json,is_fixture) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (fkey, provider, chain, w, fetched_at, u["status"], status, kw.get("seen", 0), kw.get("stored", 0), kw.get("rejected", 0), psha, source_ref,
                               u["retry_after"], kw.get("detail"), json.dumps(kw.get("rejects", [])), int(fixture)))
            return cur.lastrowid
        if tr["status"] != "ACTIVE":
            put_fetch("SKIPPED", detail=f"wallet_{tr['status'].lower()}")
            results.append({"wallet": w, "status": "SKIPPED", "detail": f"wallet is {tr['status']}"})
            continue
        st = u["status"]
        if st == 429:
            put_fetch("RATE_LIMITED", detail="provider answered 429; no events taken, retry later")
            results.append({"wallet": w, "status": "RATE_LIMITED", "retry_after_s": u["retry_after"]})
            worst = max(worst, "RATE_LIMITED", key=rank.get)
            gaps.append((w, "GAP", "provider rate limit (429); this wallet was not read"))
            continue
        if st != 200 or u["raw"] is None:
            put_fetch("ERROR", detail=f"http {st}" if st != 200 else "response body is not a list")
            results.append({"wallet": w, "status": "ERROR", "detail": f"http {st}" if st != 200 else "body not a list"})
            worst = max(worst, "DOWN", key=rank.get)
            gaps.append((w, "GAP", f"provider error (http {st})"))
            continue
        raw_rows = u["raw"][: tr["max_tx_per_fetch"]]
        beyond = len(u["raw"]) - len(raw_rows)
        fid = put_fetch("STALE" if stale else "OK", seen=len(raw_rows))
        stored = dup = rejected = 0
        rejects, sigs = [], set()
        for raw in raw_rows:
            try:
                if not isinstance(raw, dict):
                    raise _Reject("MALFORMED_ROW")
                tx = u["norm"](raw)
                if not tx["signature"]:
                    raise _Reject("MISSING_SIGNATURE")
                if not valid_signature(chain, tx["signature"]):
                    raise _Reject("INVALID_SIGNATURE")
                bt = store.to_utc(tx["block_time"]) if tx["block_time"] is not None else None
                if bt is None:
                    raise _Reject("MISSING_BLOCK_TIME")
                if bt > fetched_at + SKEW:
                    raise _Reject("FUTURE_BLOCK_TIME")
                if tx["signature"] in sigs:
                    dup += 1
                    continue
                sigs.add(tx["signature"])
                try:
                    c = classify(chain, w, tx, con)
                except ValueError:
                    raise _Reject("INVALID_CONTRACT")
            except _Reject as e:
                rejected += 1
                rejects.append({"code": str(e), "row_sha256": row_sha(raw) if isinstance(raw, dict) else None})
                continue
            ekey = _sha(chain, tx["signature"], w)
            if con.execute("SELECT 1 FROM social_wallet_events WHERE event_key=?", (ekey,)).fetchone():
                dup += 1
                continue
            payer = tx["fee_payer"]
            cur = con.execute(
                "INSERT INTO social_wallet_events(event_key,chain,wallet_address,signature,slot,block_time,event_type,swap_side,classification_rule,classification_version,"
                "classification_confidence,classification_basis_json,provider_type,protocol_source,fee_native,fee_unit,fee_payer,fee_paid_by_wallet,counterparties_json,"
                "custody_touch,legs_truncated,observed_scope,freshness,provider,fetch_id,row_sha256,ingested_at,is_fixture) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (ekey, chain, w, tx["signature"], tx["slot"], bt, c["event_type"], c["swap_side"], c["rule"], CLASSIFIER_VERSION, c["confidence"],
                 canonical_json(c["basis"]), tx["provider_type"], tx["source"], tx["fee"], tx["fee_unit"], payer, None if payer is None else int(payer == w),
                 canonical_json(c["counterparties"]), c["custody_touch"], int(tx["truncated"]), "LIVE" if bt >= tr["watch_since"] else "BACKFILL",
                 "STALE" if stale else "FRESH", provider, fid, row_sha(raw), t, int(fixture)))
            for g in c["legs"]:
                con.execute("INSERT INTO social_wallet_event_legs(event_id,leg_index,asset_kind,contract,direction,amount,counterparty,counterparty_label) VALUES (?,?,?,?,?,?,?,?)",
                            (cur.lastrowid, g["leg_index"], g["asset_kind"], g["contract"], g["direction"], g["amount"], g["counterparty"], g["counterparty_label"]))
            stored += 1
        status = "STALE" if stale else ("PARTIAL" if rejected or beyond else "OK")
        con.execute("UPDATE social_wallet_fetches SET status=?, rows_stored=?, rows_rejected=?, rejects_json=?, detail=? WHERE fetch_id=?",
                    (status, stored, rejected, json.dumps(rejects), f"{dup} already stored or repeated; {beyond} beyond the per-fetch limit" if (dup or beyond) else None, fid))
        results.append({"wallet": w, "status": status, "seen": len(raw_rows), "stored": stored, "already_stored": dup, "rejected": rejected,
                        "reject_codes": sorted({r['code'] for r in rejects}), "beyond_limit": beyond})
        if stale:
            worst = max(worst, "DEGRADED", key=rank.get)
            gaps.append((w, "PARTIAL", f"data fetched {int((t - fetched_at) / 3600)} hours before this run; events stored as STALE"))
        elif rejected or beyond:
            worst = max(worst, "DEGRADED", key=rank.get)
            gaps.append((w, "PARTIAL", f"{rejected} rows rejected, {beyond} beyond the per-fetch limit"))
        else:
            gaps.append((w, "COVERED", None))
    usable = [r for r in results if r["status"] in ("OK", "PARTIAL", "STALE", "ALREADY_INGESTED")]
    store.record_connector_health(con, connector, worst, checked_at=fetched_at, items_seen=sum(r.get("stored", 0) for r in results), now=t,
                                  error=None if worst == "OK" else worst.lower())
    run = psha[:16]
    for w, cov, reason in gaps:
        store.record_coverage(con, run_id=run, connector=connector, platform="onchain", scope=f"{chain}:{w}", status=cov, checked_at=fetched_at, gap_reason=reason,
                              sampling_note="latest transactions only, up to the per-fetch limit", now=t)
    overall = "FAILED" if (results and not usable and any(r["status"] in ("RATE_LIMITED", "ERROR") for r in results)) else \
              ("OK" if worst == "OK" and all(r["status"] in ("OK", "ALREADY_INGESTED", "UNTRACKED") for r in results) else "PARTIAL")
    return {"status": overall, "provider": provider, "chain": chain, "payload_sha256": psha, "fetched_at": fetched_at, "stale": stale, "results": results}


class _Reject(Exception):
    pass


def ingest_file(con, path: str | Path, *, now: float | None = None, max_age: int = DEFAULT_MAX_AGE, fixture: bool = False) -> dict:
    p = Path(path)
    raw = p.read_bytes()
    try:
        doc = json.loads(raw)
    except ValueError:
        raise ValueError("file is not JSON")
    if not isinstance(doc, dict):
        raise ValueError("file must hold one JSON object")
    return ingest(con, doc, now=now, max_age=max_age, source_ref=p.name, payload_sha=hashlib.sha256(raw).hexdigest(), fixture=fixture)


# ---------- reading, provenance, reports ----------

def tx_url(chain: str, signature: str) -> str | None:
    ex = chain_registry.CHAINS.get(chain, {}).get("explorer")
    return ex.replace("/token/", "/tx/") + signature if ex else None


def events(con, *, chain: str | None = None, wallet: str | None = None, types: tuple[str, ...] | None = None, since: Any = None, limit: int = 200) -> list[dict]:
    q, a = "SELECT * FROM social_wallet_events WHERE 1=1", []
    if chain:
        q += " AND chain=?"; a.append(chain.lower())
    if wallet:
        q += " AND wallet_address=?"; a.append(canon(chain or "solana", wallet)[1])
    if types:
        q += f" AND event_type IN ({','.join('?' * len(types))})"; a += list(types)
    if since is not None:
        q += " AND block_time>=?"; a.append(store.to_utc(since))
    out = []
    for r in con.execute(q + " ORDER BY block_time, event_id LIMIT ?", a + [int(limit)]):
        d = dict(r)
        d["classification_basis"] = json.loads(d.pop("classification_basis_json"))
        d["counterparties"] = json.loads(d.pop("counterparties_json"))
        d["legs"] = [dict(x) for x in con.execute("SELECT leg_index,asset_kind,contract,direction,amount,counterparty,counterparty_label FROM social_wallet_event_legs WHERE event_id=? ORDER BY leg_index", (r["event_id"],))]
        d["tx_url"] = tx_url(r["chain"], r["signature"])
        out.append(d)
    return out


def provenance(con, event_id: int, *, source_file: str | Path | None = None) -> dict:
    """The chain from an event back to its source, with each link checkable: event -> row hash -> provider response (file hash, fetch time,
    status) -> transaction signature on a public explorer. With the source file, the hashes are recomputed and compared."""
    e = con.execute("SELECT * FROM social_wallet_events WHERE event_id=?", (event_id,)).fetchone()
    if e is None:
        raise ValueError(f"unknown event {event_id}")
    f = con.execute("SELECT * FROM social_wallet_fetches WHERE fetch_id=?", (e["fetch_id"],)).fetchone()
    out = {"event_id": event_id, "signature": e["signature"], "chain": e["chain"], "wallet": e["wallet_address"], "block_time": e["block_time"], "tx_url": tx_url(e["chain"], e["signature"]),
           "row_sha256": e["row_sha256"], "provider": e["provider"], "fetch": {"fetch_id": f["fetch_id"], "fetched_at": f["fetched_at"], "http_status": f["http_status"],
           "status": f["status"], "payload_sha256": f["payload_sha256"], "source_ref": f["source_ref"], "is_fixture": bool(f["is_fixture"])},
           "classification": {"rule": e["classification_rule"], "version": e["classification_version"], "confidence": e["classification_confidence"]},
           "signature_well_formed": valid_signature(e["chain"], e["signature"]), "checks": []}
    if source_file is not None:
        raw = Path(source_file).read_bytes()
        out["checks"].append({"check": "file_sha256_equals_fetch_payload_sha256", "ok": hashlib.sha256(raw).hexdigest() == f["payload_sha256"]})
        found = False
        try:
            doc = json.loads(raw)
            _, chain, _, units = _units(doc)
            for u in units:
                if u["raw"] and u["wallet"].lower() == e["wallet_address"].lower():
                    for r in u["raw"]:
                        if isinstance(r, dict) and u["norm"](r)["signature"] == e["signature"]:
                            found = row_sha(r) == e["row_sha256"]
        except (ValueError, KeyError):
            found = False
        out["checks"].append({"check": "row_in_file_hashes_to_row_sha256", "ok": found})
    out["verified"] = bool(out["checks"]) and all(c["ok"] for c in out["checks"]) and out["signature_well_formed"]
    return out


def derive_funding_hypotheses(con, *, chain: str | None = None, now: float | None = None) -> dict:
    """For each tracked wallet, take its earliest plain native transfer in (never a swap payout) among the stored events as its first funder, and
    record the funder and everything it first funded as a HYPOTHESIS. Only the stored window is seen, so "first" means first seen. Shared funding is a reason to look. It never attributes a wallet to an account and never counts toward a level."""
    t = _now(now)
    first: dict[tuple, dict] = {}
    q = "SELECT e.*, l.amount, l.counterparty FROM social_wallet_events e JOIN social_wallet_event_legs l ON l.event_id=e.event_id WHERE l.asset_kind='NATIVE' AND l.direction='IN' AND e.event_type='NATIVE_TRANSFER_IN'"
    a: list = []
    if chain:
        q += " AND e.chain=?"; a.append(chain.lower())
    for r in con.execute(q + " ORDER BY e.block_time, e.event_id", a):
        k = (r["chain"], r["wallet_address"])
        if k not in first and r["counterparty"]:
            first[k] = {"funder": r["counterparty"], "signature": r["signature"], "block_time": r["block_time"], "amount": r["amount"], "fixture": r["is_fixture"]}
    by: dict[tuple, list] = {}
    for (ch, w), f in first.items():
        by.setdefault((ch, f["funder"]), []).append((w, f))
    made = 0
    for (ch, funder), members in sorted(by.items()):
        lab = effective_label(con, ch, funder)
        key = _sha(ch, funder)
        ws = sorted(w for w, _ in members)
        ev = [{"wallet": w, "signature": f["signature"], "block_time": f["block_time"], "amount": f["amount"]} for w, f in sorted(members)]
        row = con.execute("SELECT hypothesis_id, members_json FROM social_wallet_funding_hypotheses WHERE hypothesis_key=?", (key,)).fetchone()
        informative = int(not lab["non_control"])
        if row is None:
            con.execute("INSERT INTO social_wallet_funding_hypotheses(hypothesis_key,chain,funder_address,members_json,evidence_json,funder_label,informative,status,derived_version,derived_at,is_fixture)"
                        " VALUES (?,?,?,?,?,?,?,'HYPOTHESIS',?,?,?)", (key, ch, funder, json.dumps(ws), json.dumps(ev), lab["kind"], informative, VERSION, t, int(all(f["fixture"] for _, f in members))))
            made += 1
        elif json.loads(row["members_json"]) != ws:
            con.execute("UPDATE social_wallet_funding_hypotheses SET members_json=?, evidence_json=?, funder_label=?, informative=?, derived_at=? WHERE hypothesis_id=?",
                        (json.dumps(ws), json.dumps(ev), lab["kind"], informative, t, row["hypothesis_id"]))
            made += 1
    return {"hypotheses_written": made, "wallets_with_a_funder": len(first)}


def summary(con, chain: str, wallet: str) -> dict:
    ch, w = canon(chain, wallet)
    tr = _tracked_row(con, ch, w)
    counts = {r[0]: r[1] for r in con.execute("SELECT event_type, COUNT(*) FROM social_wallet_events WHERE chain=? AND wallet_address=? GROUP BY event_type", (ch, w))}
    last = con.execute("SELECT * FROM social_wallet_fetches WHERE chain=? AND wallet_address=? ORDER BY fetched_at DESC, fetch_id DESC LIMIT 1", (ch, w)).fetchone()
    cov = None
    if last is None:
        cov = ("GAP: no provider response has been ingested for this wallet" if chain_registry.family(ch) == "solana" else
               "GAP: no transaction provider is configured for this chain; no activity is not the same as no data")
    return {"chain": ch, "wallet": w, "tracked": dict(tr) if tr else None, "label": effective_label(con, ch, w), "event_counts": counts,
            "last_fetch": dict(last) if last else None, "coverage": cov or ("last fetch " + last["status"]),
            "owner_claimed": None, "pnl": "not computed in this phase"}


def report(con, chain: str, wallet: str, limit: int = 15) -> str:
    s = summary(con, chain, wallet)
    L = [f"Wallet {s['chain']}:{s['wallet']}  tracked: {s['tracked']['status'] if s['tracked'] else 'no'}  label: {s['label']['kind']}",
         "Owner: not claimed by monitoring. See `social wallet why` for attribution evidence.",
         f"Coverage: {s['coverage']}", "Events: " + (", ".join(f"{k} {v}" for k, v in sorted(s['event_counts'].items())) or "none stored"),
         "No profit or loss, price or cost basis is computed here."]
    for e in events(con, chain=s["chain"], wallet=s["wallet"], limit=10000)[-limit:]:
        legs = "; ".join(f"{g['direction']} {g['amount']:g} {'native' if g['asset_kind'] == 'NATIVE' else g['contract'][:6] + '..'}" for g in e["legs"]) or "no legs"
        L.append(f"  {e['block_time']:.0f} {e['event_type']}{'/' + e['swap_side'] if e['swap_side'] else ''} [{e['classification_rule']}, {e['classification_confidence']}] "
                 f"{e['signature'][:12]}.. fee {e['fee_native']} {e['fee_unit'] or ''} {e['observed_scope']}/{e['freshness']}: {legs}")
    return "\n".join(L)
