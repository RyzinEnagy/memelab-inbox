"""Phase 10: database side of wallet performance. Reads Phase 09 activity (events, legs, fetches), supplied prices and token metadata (migration 10),
builds a ledger, runs the pure engine (perf_core / perf_analysis) and stores the run with its exact input, so it can be recomputed and compared by hash.

The accounting never fetches anything. Prices and quotes are rows somebody supplied (`social_perf_prices`), each with its source and an estimate flag.
Phase 09 tables are read only: this phase adds no column to them.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ..chains import registry as chain_registry
from ..wallet import STABLES as SOL_STABLES
from . import perf_analysis as PA, perf_core as C, store
from .wallet_assertions import canon

LEDGER_BUILD_VERSION = "perf-ledger-build-v1"
EVENT_TO_ENTRY = {"SWAP": "SWAP", "LP_ADD": "LP_ADD", "LP_REMOVE": "LP_REMOVE", "TOKEN_TRANSFER_IN": "TRANSFER_IN", "NATIVE_TRANSFER_IN": "TRANSFER_IN",
                  "TOKEN_TRANSFER_OUT": "TRANSFER_OUT", "NATIVE_TRANSFER_OUT": "TRANSFER_OUT", "FAILED": "FAILED", "UNCLASSIFIED": "UNCLASSIFIED"}


def _now(now): 
    import time
    return time.time() if now is None else float(now)


# ---------- supplied prices and token metadata ----------

def put_token_meta(con, chain: str, asset: str, *, kind: str, source: str, alias_of: str | None = None, symbol: str | None = None, decimals: int | None = None,
                   transfer_fee_bps: int | None = None, fixture: bool = False, now: float | None = None) -> dict:
    if kind not in ("NATIVE", "STABLE", "TOKEN", "LP_RECEIPT"):
        raise ValueError("kind must be NATIVE, STABLE, TOKEN or LP_RECEIPT")
    if not str(source or "").strip():
        raise ValueError("source: say where this was learned")
    ch = chain.strip().lower()
    a = "NATIVE" if asset == "NATIVE" else canon(ch, asset)[1]
    al = None if alias_of is None else ("NATIVE" if alias_of == "NATIVE" else canon(ch, alias_of)[1])
    t = _now(now)
    cur = con.execute("INSERT INTO social_perf_token_meta(chain,asset,kind,alias_of,symbol,decimals,transfer_fee_bps,source,recorded_at,is_fixture) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (ch, a, kind, al, symbol, decimals, transfer_fee_bps, str(source)[:200], t, int(fixture)))
    return {"meta_id": cur.lastrowid, "chain": ch, "asset": a, "kind": kind}


def put_prices(con, chain: str, rows: list[dict], *, fixture: bool = False, now: float | None = None) -> dict:
    """Store supplied price observations. MID needs usd; EXEC_QUOTE needs amount_in and usd_out; NO_ROUTE needs a reason; IMPACT_CURVE needs a `sell` dict.
    Repeats (same chain, asset, time, kind, source) are skipped."""
    ch, t, added, skipped = chain.strip().lower(), _now(now), 0, 0
    for r in rows:
        kind = r.get("kind", "MID")
        if kind not in C.PRICE_KINDS or not r.get("source"):
            raise ValueError("each price needs a source and a kind of MID, EXEC_QUOTE, NO_ROUTE or IMPACT_CURVE")
        asset = "NATIVE" if r["asset"] == "NATIVE" else canon(ch, r["asset"])[1]
        obs = float(C.dec(r.get("t"), "t"))
        usd = amount_in = usd_out = None
        detail = None
        if kind == "MID":
            usd = float(C.dec(r.get("usd"), "usd"))
        elif kind == "EXEC_QUOTE":
            amount_in, usd_out = float(C.dec(r.get("amount_in"), "amount_in")), float(C.dec(r.get("usd_out"), "usd_out"))
        elif kind == "IMPACT_CURVE":
            if not isinstance(r.get("sell"), dict):
                raise ValueError("IMPACT_CURVE needs a sell quotes dict")
            detail = json.dumps(r["sell"], sort_keys=True)
        else:
            detail = str(r.get("detail") or "no route observed")[:200]
        try:
            con.execute("INSERT INTO social_perf_prices(chain,asset,observed_at,kind,usd,amount_in,usd_out,detail_json,source,is_estimate,recorded_at,is_fixture) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (ch, asset, obs, kind, usd, amount_in, usd_out, detail, str(r["source"])[:80], int(bool(r.get("is_estimate", True))), t, int(fixture)))
            added += 1
        except sqlite3.IntegrityError:
            skipped += 1
    return {"added": added, "skipped_repeats": skipped}


# ---------- building a ledger from Phase 09 events ----------

def _chain_assets(chain: str) -> dict:
    c = chain_registry.CHAINS.get(chain, {})
    assets: dict[str, dict] = {"NATIVE": {"kind": "NATIVE", "symbol": c.get("native_symbol")}}
    wn = c.get("wrapped_native")
    if wn:
        w = store.normalize_contract(chain, wn)
        assets[w] = {"kind": "NATIVE", "alias_of": "NATIVE", "symbol": "W" + str(c.get("native_symbol") or "")}
    stables = dict(c.get("stables") or {})
    if chain == "solana":
        stables.update(SOL_STABLES)
    for k, sym in stables.items():
        try:
            assets[store.normalize_contract(chain, k)] = {"kind": "STABLE", "symbol": sym}
        except ValueError:
            continue
    return assets


def ledger_from_events(con, chain: str, wallets: list[str], *, as_of: float | None = None, group_reason: str | None = None, annotations: list[dict] | None = None,
                       label: str | None = None, include_prices: bool = True) -> dict:
    """A ledger document from stored Phase 09 events. Deterministic: the same stored rows give the same document (and so the same run hash)."""
    ch = chain.strip().lower()
    ws = sorted({canon(ch, w)[1] for w in wallets})
    if not ws:
        raise ValueError("at least one wallet is required")
    tracked = [con.execute("SELECT * FROM social_tracked_wallets WHERE chain=? AND wallet_address=?", (ch, w)).fetchone() for w in ws]
    fixtures = {bool(r["is_fixture"]) for r in tracked if r is not None}
    if len(fixtures) > 1:
        raise ValueError("fixture and real wallets never share a run")
    is_fixture = bool(fixtures and True in fixtures)
    ph = ",".join("?" * len(ws))
    evs = con.execute(f"SELECT * FROM social_wallet_events WHERE chain=? AND wallet_address IN ({ph}) ORDER BY block_time, event_id", [ch] + ws).fetchall()
    fetches = con.execute(f"SELECT * FROM social_wallet_fetches WHERE chain=? AND wallet_address IN ({ph}) ORDER BY fetched_at, fetch_id", [ch] + ws).fetchall()
    usable = [f for f in fetches if f["status"] in ("OK", "PARTIAL", "STALE")]
    if as_of is None:
        as_of = max([f["fetched_at"] for f in usable] + [e["block_time"] for e in evs] or [0.0])
    assets = _chain_assets(ch)
    for r in con.execute("SELECT * FROM social_perf_token_meta WHERE chain=? ORDER BY recorded_at, meta_id", (ch,)):
        assets[r["asset"]] = {k: v for k, v in {"kind": r["kind"], "alias_of": r["alias_of"], "symbol": r["symbol"], "decimals": r["decimals"], "transfer_fee_bps": r["transfer_fee_bps"]}.items() if v is not None}
    entries = []
    for e in evs:
        legs = []
        for g in con.execute("SELECT * FROM social_wallet_event_legs WHERE event_id=? ORDER BY leg_index", (e["event_id"],)):
            a = "NATIVE" if g["asset_kind"] == "NATIVE" else g["contract"]
            if a not in assets:
                assets[a] = {"kind": "TOKEN"}
            legs.append({"asset": a, "dir": g["direction"], "amount": repr(g["amount"]), "counterparty": g["counterparty"]})
        fee = None if e["fee_native"] is None else {"amount": repr(e["fee_native"]), "unit": e["fee_unit"]}
        entries.append({"id": f"ev{e['event_id']}", "wallet": e["wallet_address"], "time": e["block_time"], "type": EVENT_TO_ENTRY[e["event_type"]], "legs": legs, "fee": fee,
                        "fee_paid_by_wallet": None if e["fee_paid_by_wallet"] is None else bool(e["fee_paid_by_wallet"]), "signature": e["signature"], "side": e["swap_side"],
                        "confidence": e["classification_confidence"]})
    limit_hit = [f for f in usable if f["rows_seen"] >= (next((t["max_tx_per_fetch"] for t in tracked if t is not None and t["wallet_address"] == f["wallet_address"]), 50))]
    if not usable:
        hist, evidence = "UNKNOWN", "no usable provider response is stored for these wallets"
    elif limit_hit:
        hist, evidence = "TRUNCATED", f"{len(limit_hit)} fetch(es) returned as many rows as the per-fetch limit; older transactions were probably not read"
    else:
        hist, evidence = "PLAUSIBLY_COMPLETE", "every usable fetch returned fewer rows than the per-fetch limit; the limit actually requested from the provider is not recorded"
    gaps = [{"from": None, "to": None, "reason": f"fetch {f['fetch_id']} at {f['fetched_at']:.0f} was {f['status']} ({f['detail'] or 'no detail'}); that wallet was not read", "source": "fetch"}
            for f in fetches if f["status"] in ("RATE_LIMITED", "ERROR")]
    notes = [f"fetch {f['fetch_id']} {f['status']} rows_seen {f['rows_seen']} stored {f['rows_stored']} rejected {f['rows_rejected']}" for f in fetches]
    if ch != "solana" and not evs:
        gaps.append({"from": None, "to": None, "reason": "no transaction provider is configured for this chain", "source": "provider"})
    doc: dict[str, Any] = {"schema": C.SCHEMA_LEDGER, "label": ("FIXTURE: " if is_fixture else "") + (label or "ledger built from stored Phase 09 events"), "chain": ch, "wallets": ws,
                           "as_of": as_of, "assets": assets, "entries": entries, "prices": [], "annotations": annotations or [],
                           "coverage": {"history": hist, "evidence": evidence, "gaps": gaps, "fetch_notes": notes}, "builder": LEDGER_BUILD_VERSION}
    if len(ws) > 1:
        if not str(group_reason or "").strip():
            raise ValueError("a group of wallets needs a reason; the group is the analyst's choice and never an ownership claim")
        doc["linked_wallets"] = {"declared": ws, "reason": group_reason}
    if include_prices:
        for r in con.execute("SELECT * FROM social_perf_prices WHERE chain=? ORDER BY observed_at, price_id", (ch,)):
            p = {"asset": r["asset"], "t": r["observed_at"], "kind": r["kind"], "source": r["source"]}
            if r["kind"] == "MID":
                p["usd"] = repr(r["usd"])
            elif r["kind"] == "EXEC_QUOTE":
                p["amount_in"], p["usd_out"] = repr(r["amount_in"]), repr(r["usd_out"])
            elif r["kind"] == "IMPACT_CURVE":
                p["sell"] = json.loads(r["detail_json"])
            else:
                p["detail"] = r["detail_json"]
            doc["prices"].append(p)
    doc["_fixture"] = is_fixture
    return doc


# ---------- runs ----------

def save_run(con, doc: dict, result: dict, policy: dict, *, now: float | None = None) -> dict:
    fixture = bool(doc.get("_fixture") or str(doc.get("label") or "").startswith("FIXTURE"))
    scope = result["chain"] + ":" + ",".join(result["wallets"])
    inp = C.canonical_json({"ledger": doc, "policy": policy})
    row = con.execute("SELECT run_id FROM social_perf_runs WHERE scope=? AND convention=? AND as_of=? AND input_sha256=?", (scope, result["convention"], result["as_of"], result["input_sha256"])).fetchone()
    if row:
        return {"run_id": row[0], "created": False, "result_sha256": result["result_sha256"]}
    cur = con.execute("INSERT INTO social_perf_runs(scope,chain,engine_version,convention,as_of,input_sha256,result_sha256,reconstruction_status,reconciled,score_status,n_entries,input_json,result_json,created_at,is_fixture)"
                      " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (scope, result["chain"], result["engine_version"], result["convention"], result["as_of"], result["input_sha256"], result["result_sha256"], result["reconstruction"]["status"],
                       int(result["reconciliation"]["reconciled"]), result["score"]["status"], len(doc.get("entries") or []), inp, C.canonical_json(result), _now(now), int(fixture)))
    rid = cur.lastrowid
    for p in result["positions"]:
        u = p["units"]["USD"]
        con.execute("INSERT INTO social_perf_positions(run_id,position_no,asset,status,in_sample,exclusion_reasons_json,opened_at,closed_at,cost_usd,proceeds_usd,net_usd) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (rid, p["position"], p["asset"], p["status"], int(u["in_sample"]), json.dumps(u["exclusion_reasons"]), p["opened_at"], p["closed_at"], u["cost"], u["proceeds"], u["net"]))
    for c in result["reconciliation"]["checks"]:
        con.execute("INSERT INTO social_perf_checks(run_id,check_name,status,detail_json) VALUES (?,?,?,?)", (rid, c["check"], c["status"], C.canonical_json(c["detail"])))
    return {"run_id": rid, "created": True, "result_sha256": result["result_sha256"]}


def run_wallet(con, chain: str, wallets: list[str], *, policy: dict | None = None, as_of: float | None = None, group_reason: str | None = None,
               annotations: list[dict] | None = None, save: bool = True, now: float | None = None) -> dict:
    doc = ledger_from_events(con, chain, wallets, as_of=as_of, group_reason=group_reason, annotations=annotations)
    fixture = doc.pop("_fixture")
    pol = C.merge_policy(policy)
    res = PA.analyze(doc, pol)
    out = {"result": res}
    if save:
        out["saved"] = save_run(con, dict(doc, _fixture=True) if fixture else doc, res, pol, now=now)
    return out


def load_run(con, run_id: int) -> dict:
    r = con.execute("SELECT * FROM social_perf_runs WHERE run_id=?", (run_id,)).fetchone()
    if r is None:
        raise ValueError(f"unknown run {run_id}")
    return {**dict(r), "input": json.loads(r["input_json"]), "result": json.loads(r["result_json"])}


def verify_run(con, run_id: int) -> dict:
    """Recompute a stored run from its stored input and compare hashes. Also detects a stored result that was edited after it was written."""
    r = load_run(con, run_id)
    stored_ok = C.sha({k: v for k, v in r["result"].items() if k != "result_sha256"}) == r["result_sha256"]
    inp = r["input"]
    doc = {k: v for k, v in inp["ledger"].items() if k != "_fixture"}
    again = PA.analyze(doc, inp["policy"])
    input_ok = C.sha({"ledger": doc, "policy": inp["policy"]}) == r["input_sha256"] or C.sha(inp) == r["input_sha256"]
    return {"run_id": run_id, "stored_result_matches_its_hash": stored_ok, "recomputed_result_sha256": again["result_sha256"], "stored_result_sha256": r["result_sha256"],
            "recomputation_matches": again["result_sha256"] == r["result_sha256"], "input_matches_hash": input_ok,
            "verified": stored_ok and again["result_sha256"] == r["result_sha256"] and input_ok}


def list_runs(con) -> list[dict]:
    return [dict(r) for r in con.execute("SELECT run_id, scope, convention, as_of, reconstruction_status, reconciled, score_status, n_entries, result_sha256, is_fixture FROM social_perf_runs ORDER BY run_id")]


def latest_results(con) -> list[dict]:
    """The newest run for each scope and convention."""
    out = []
    for r in con.execute("SELECT MAX(run_id) FROM social_perf_runs GROUP BY scope, convention"):
        out.append(load_run(con, r[0])["result"])
    return out
