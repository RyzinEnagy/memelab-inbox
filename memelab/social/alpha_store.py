"""Phase 11: database side of Information Alpha. Reads Phase 06 claims and Phase 01 items, stores supplied historical candles (migration 11),
builds an input document for the pure engine (alpha_core), stores runs with their exact input so a run can be recomputed and compared by hash.

Nothing is fetched. Candles are rows somebody supplied, each with its source. Wallet performance tables (Phase 10) are not read: the score is
a measurement of public commentary, separate from wallet profit (D-073).
"""
from __future__ import annotations

import json
import sqlite3
import time

from . import alpha_core as A, store


def _now(now):
    return time.time() if now is None else float(now)


def put_series(con, series: list[dict], *, fixture: bool = False, now: float | None = None) -> dict:
    """Store supplied candle series. A series the engine would reject (live quote, bad candles, no source) is refused whole, with the reason."""
    t, added, skipped = _now(now), 0, 0
    for s in series:
        ok, rejected = A.prep_series({"series": [s]})
        if rejected:
            raise ValueError(f"{rejected[0]['contract'] or '?'}: {rejected[0]['reason']}")
        chain, contract = str(s["chain"]).lower(), str(s["contract"])
        try:
            cur = con.execute("INSERT INTO social_alpha_series(chain,contract,source,candle_seconds,as_of_kind,delisted_at,recorded_at,is_fixture) VALUES (?,?,?,?,?,?,?,?)",
                              (chain, contract, str(s["source"])[:200], s["candle_seconds"], s["as_of_kind"], s.get("delisted_at"), t, int(fixture)))
        except sqlite3.IntegrityError:
            skipped += 1
            continue
        con.executemany("INSERT INTO social_alpha_candles(series_id,t,o,h,l,c,v,liq) VALUES (?,?,?,?,?,?,?,?)",
                        [(cur.lastrowid, r["t"], r["o"], r["h"], r["l"], r["c"], r.get("v"), r.get("liq")) for r in s["rows"]])
        added += 1
    return {"added": added, "skipped_repeats": skipped}


def load_series(con) -> list[dict]:
    out = []
    for s in con.execute("SELECT * FROM social_alpha_series ORDER BY chain, contract, source"):
        rows = [dict(r) for r in con.execute("SELECT t,o,h,l,c,v,liq FROM social_alpha_candles WHERE series_id=? ORDER BY t", (s["series_id"],))]
        for r in rows:
            for k in ("v", "liq"):
                if r[k] is None:
                    del r[k]
        d = {"chain": s["chain"], "contract": s["contract"], "source": s["source"], "candle_seconds": s["candle_seconds"], "as_of_kind": s["as_of_kind"], "rows": rows}
        if s["delisted_at"] is not None:
            d["delisted_at"] = s["delisted_at"]
        out.append(d)
    return out


def build_input(con, *, as_of: float, annotations: dict | None = None, label: str = "stored claims and supplied candles") -> dict:
    """Input document from current Phase 06 claims. Only the newest extraction of each post counts (superseded_by IS NULL). A claim whose token
    is not resolved by Phase 05 keeps an empty token and is reported as TOKEN_UNRESOLVED. The number of posts the collector enumerated for a
    source is not stored anywhere yet, so it is unknown unless the annotations supply it, and an unknown universe caps the tier at PRELIMINARY."""
    ann = annotations or {}
    rows = con.execute(
        "SELECT c.id AS claim_id, c.item_key, c.account_id, c.direction, a.conditional, a.sarcasm_suspected, a.author_position, a.attribution, a.uncertainty, a.tokens_json, "
        "i.published_at, i.published_at_basis, i.first_observed_at, i.original_url, r.chain, r.contract, r.ref_kind "
        "FROM social_claims c JOIN social_claim_attributes a ON a.claim_id=c.id JOIN social_claim_extractions e ON e.extraction_id=a.extraction_id "
        "JOIN social_items i ON i.item_key=c.item_key LEFT JOIN social_token_refs r ON r.ref_id=c.token_ref_id "
        "WHERE e.superseded_by IS NULL AND c.claim_type <> 'WALLET_CLAIM' AND a.category <> 'wallet' ORDER BY c.id").fetchall()
    link = {}
    for r in con.execute("SELECT trader_id, account_id FROM social_trader_accounts ORDER BY linked_at, trader_id"):
        link.setdefault(r["account_id"], r["trader_id"])
    calls, sources = [], {}
    skipped = 0
    for r in rows:
        if not r["account_id"]:
            skipped += 1
            continue
        sid = link.get(r["account_id"], r["account_id"])
        sources.setdefault(sid, {"label": sid})
        resolved = False
        for t in json.loads(r["tokens_json"] or "[]"):
            if t.get("status") == "resolved" and r["contract"] and str(t.get("contract")) == str(r["contract"]):
                resolved = True
        first = r["first_observed_at"]
        if first is None:
            o = con.execute("SELECT MIN(observed_at) FROM social_observations WHERE item_key=? AND observed_at IS NOT NULL", (r["item_key"],)).fetchone()
            first = o[0]
        calls.append({"call_id": f"claim{r['claim_id']}", "source_id": sid, "item_key": r["item_key"],
                      "token": {"chain": r["chain"], "contract": r["contract"]} if resolved and r["ref_kind"] in ("CONTRACT_ADDRESS", "OFFICIAL_LINK") else {},
                      "direction": r["direction"], "published_at": r["published_at"] if r["published_at_basis"] != "UNKNOWN" else None, "first_observed_at": first,
                      "original": bool(store.is_independent_original(con, r["item_key"])) and r["attribution"] == "author",
                      "conditional": bool(r["conditional"]), "sarcasm_suspected": bool(r["sarcasm_suspected"]), "author_position": r["author_position"],
                      "uncertainty": r["uncertainty"]})
    for sid, u in (ann.get("universe") or {}).items():
        sources.setdefault(sid, {"label": sid})
        sources[sid]["universe_count"], sources[sid]["universe_basis"] = int(u["count"]), str(u.get("basis") or "supplied")
    return {"schema": A.SCHEMA, "label": label, "is_fixture": False, "as_of": as_of, "sources": sources, "calls": calls, "series": load_series(con),
            "author_trades": ann.get("author_trades") or [], "claims_without_account_skipped": skipped}


def save_run(con, doc: dict, result: dict, policy: dict, *, now: float | None = None) -> dict:
    row = con.execute("SELECT run_id FROM social_alpha_runs WHERE input_sha256=?", (result["input_sha256"],)).fetchone()
    if row:
        return {"run_id": row[0], "created": False, "result_sha256": result["result_sha256"]}
    scored = sum(1 for s in result["sources"].values() if s["score"]["status"] == "SCORED")
    cur = con.execute("INSERT INTO social_alpha_runs(engine_version,rules_version,as_of,policy_sha256,input_sha256,result_sha256,n_calls,n_sources_scored,input_json,result_json,created_at,is_fixture)"
                      " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                      (result["engine_version"], result["rules_version"], result["as_of"], result["policy_sha256"], result["input_sha256"], result["result_sha256"],
                       len(result["calls"]), scored, A.canon({"doc": doc, "policy": policy}), A.canon(result), _now(now), int(result["is_fixture"])))
    rid = cur.lastrowid
    for sid, s in result["sources"].items():
        sc = s["score"]
        con.execute("INSERT INTO social_alpha_scores(run_id,source_id,status,tier,score,score_point,n_independent,reasons_json) VALUES (?,?,?,?,?,?,?,?)",
                    (rid, str(sid), sc["status"], sc["tier"], sc["score"], sc["score_point"], sc["n_independent_with_baseline"],
                     json.dumps(sc.get("reasons") or sc.get("not_validated_because") or [])))
    return {"run_id": rid, "created": True, "result_sha256": result["result_sha256"]}


def load_run(con, run_id: int) -> dict:
    r = con.execute("SELECT * FROM social_alpha_runs WHERE run_id=?", (run_id,)).fetchone()
    if r is None:
        raise ValueError(f"unknown run {run_id}")
    return {**dict(r), "input": json.loads(r["input_json"]), "result": json.loads(r["result_json"])}


def verify_run(con, run_id: int) -> dict:
    r = load_run(con, run_id)
    stored_ok = A.sha({k: v for k, v in r["result"].items() if k != "result_sha256"}) == r["result_sha256"]
    again = A.analyze(r["input"]["doc"], r["input"]["policy"])
    return {"run_id": run_id, "stored_result_matches_its_hash": stored_ok, "recomputed_result_sha256": again["result_sha256"], "stored_result_sha256": r["result_sha256"],
            "recomputation_matches": again["result_sha256"] == r["result_sha256"], "verified": stored_ok and again["result_sha256"] == r["result_sha256"]}


def latest_result(con) -> dict | None:
    r = con.execute("SELECT MAX(run_id) FROM social_alpha_runs").fetchone()[0]
    return None if r is None else load_run(con, r)["result"]


def status(con) -> dict:
    return {"series": con.execute("SELECT COUNT(*) FROM social_alpha_series").fetchone()[0],
            "runs": [dict(r) for r in con.execute("SELECT run_id, as_of, n_calls, n_sources_scored, result_sha256, is_fixture FROM social_alpha_runs ORDER BY run_id")],
            "engine_version": A.ENGINE_VERSION, "rules_version": A.RULES_VERSION}
