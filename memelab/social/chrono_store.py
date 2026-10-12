"""Phase 12: database side of the chronology. Builds one input document for chrono_core from what earlier phases stored, keeps every run
with its exact input (migration 12) so it can be recomputed and compared by hash, and keeps the corroboration and risk flags in a normalized
table that a later discovery pipeline can query by token.

Read, never written: Phase 01 items and observations, Phase 04 forwards, Phase 03 item context and refs, Phase 06 claims (current extractions
only), Phase 05 resolutions through the claim's token list, Phase 09 assertions (through wallet_assertions.explain), tracked wallets, fetches
and events, Phase 11 candles. Nothing is fetched.
"""
from __future__ import annotations

import json
import time

from . import chrono_core as C, store, wallet_activity as WA, wallet_assertions as WAS


def _now(now):
    return time.time() if now is None else float(now)


def source_accounts(con, source_id: str) -> list[str]:
    """A source is a Phase 01 account id or a Phase 01 trader id (all its linked accounts)."""
    accts = [r[0] for r in con.execute("SELECT account_id FROM social_trader_accounts WHERE trader_id=? ORDER BY account_id", (source_id,))]
    if con.execute("SELECT 1 FROM social_accounts WHERE account_id=?", (source_id,)).fetchone():
        accts.append(source_id)
    return sorted(set(accts))


def _posts(con, accounts: list[str], tok: tuple[str, str]) -> list[dict]:
    if not accounts:
        return []
    q = ("SELECT c.id AS claim_id, c.item_key, c.direction, a.author_position, a.attribution, a.referenced_item_key, a.tokens_json, "
         "i.published_at, i.published_at_basis, i.original_url, i.platform, r.chain AS ref_chain, r.contract AS ref_contract, r.symbol_seen "
         "FROM social_claims c JOIN social_claim_attributes a ON a.claim_id=c.id JOIN social_claim_extractions e ON e.extraction_id=a.extraction_id "
         "JOIN social_items i ON i.item_key=c.item_key LEFT JOIN social_token_refs r ON r.ref_id=c.token_ref_id "
         f"WHERE e.superseded_by IS NULL AND c.claim_type <> 'WALLET_CLAIM' AND a.category <> 'wallet' AND c.account_id IN ({','.join('?' * len(accounts))}) "
         "ORDER BY c.item_key, c.id")
    by: dict[str, dict] = {}
    for r in con.execute(q, accounts):
        token = None
        resolved = [t for t in json.loads(r["tokens_json"] or "[]") if t.get("status") == "resolved" and t.get("chain") and t.get("contract")]
        for t in resolved:
            if C.ident(t["chain"], t["contract"]) == tok:
                token = {"chain": t["chain"], "contract": t["contract"], "status": "resolved", "symbol": r["symbol_seen"]}
        if token is None and resolved:
            t = resolved[0]
            token = {"chain": t["chain"], "contract": t["contract"], "status": "resolved", "symbol": r["symbol_seen"]}
        if token is None:
            token = {"chain": r["ref_chain"], "contract": r["ref_contract"], "status": "unresolved", "symbol": r["symbol_seen"]}
        prev = by.get(r["item_key"])
        if prev is not None and C.ident(prev["token"].get("chain"), prev["token"].get("contract")) == tok and prev["token"]["status"] == "resolved":
            continue
        kind = "ORIGINAL"
        ctx = con.execute("SELECT reference_type FROM social_item_context WHERE item_key=?", (r["item_key"],)).fetchone()
        if not store.is_independent_original(con, r["item_key"]) or r["attribution"] == "reposted":
            kind = "REPOST"
        elif (ctx and ctx[0] == "QUOTE") or r["attribution"] == "quoted":
            kind = "QUOTE"
        elif ctx and ctx[0] == "REPLY":
            kind = "REPLY"
        ref = r["referenced_item_key"]
        if kind == "REPOST" and not ref:
            f = con.execute("SELECT origin_item_key FROM social_item_forwards WHERE item_key=?", (r["item_key"],)).fetchone()
            g = con.execute("SELECT referenced_item_key FROM social_item_refs WHERE item_key=? AND ref_type='retweeted'", (r["item_key"],)).fetchone()
            ref = (f and f[0]) or (g and g[0])
        obs = [{"observation_id": o["id"], "observed_at": o["observed_at"], "status": o["retrieval_status"]}
               for o in con.execute("SELECT id, observed_at, retrieval_status FROM social_observations WHERE item_key=? ORDER BY observed_at, id", (r["item_key"],))]
        by[r["item_key"]] = {"item_key": r["item_key"], "platform": r["platform"], "url": r["original_url"], "published_at": r["published_at"],
                             "published_basis": r["published_at_basis"], "observations": obs, "talk_kind": kind, "repost_of": ref,
                             "direction": r["direction"], "author_position": r["author_position"], "claim_id": r["claim_id"], "token": token}
    return [by[k] for k in sorted(by)]


def _wallets(con, accounts: list[str], chain: str, as_of: float) -> list[dict]:
    out = []
    for acct in accounts:
        ent = f"acct:{acct}"
        if not con.execute("SELECT 1 FROM social_registry_entities WHERE entity_id=?", (ent,)).fetchone():
            continue
        for (w,) in con.execute("SELECT DISTINCT wallet_address FROM social_wallet_assertions WHERE account_entity=? AND chain=? ORDER BY wallet_address", (ent, chain)):
            v = WAS.explain(con, ent, chain, w, as_of=as_of)
            others = sorted({a["account_entity"] for a in v["other_accounts_assertions"] if a["counts_as"] in ("SELF_CLAIM", "CONTROL_PROOF", "INDEPENDENT", "THIRD_PARTY")})
            out.append({"chain": chain, "wallet": w, "level": v["level"], "confidence": v["confidence"], "account_entity": ent, "other_claimants": others,
                        "label_kind": v["wallet_label"].get("kind"), "assertion_ids": [a["assertion_id"] for a in v["assertions"]],
                        "evidence_refs": sorted({a["evidence_ref"] for a in v["assertions"]})})
    return out


def _events(con, chain: str, wallets: list[str], lo: float | None, hi: float) -> list[dict]:
    out = []
    for w in wallets:
        for e in WA.events(con, chain=chain, wallet=w, since=lo, limit=5000):
            if e["block_time"] is not None and e["block_time"] > hi:
                continue
            out.append({"chain": e["chain"], "wallet": e["wallet_address"], "signature": e["signature"], "slot": e["slot"], "block_time": e["block_time"],
                        "event_type": e["event_type"], "swap_side": e["swap_side"], "legs": e["legs"], "url": e["tx_url"], "provider": e["provider"],
                        "custody_touch": e["custody_touch"], "event_id": e["event_id"]})
    return out


def _monitoring(con, chain: str, wallets: list[str]) -> list[dict]:
    out = []
    for w in wallets:
        t = con.execute("SELECT watch_since, status FROM social_tracked_wallets WHERE chain=? AND wallet_address=?", (chain, w)).fetchone()
        ok = con.execute("SELECT MAX(fetched_at) FROM social_wallet_fetches WHERE chain=? AND wallet_address=? AND status IN ('OK','PARTIAL')", (chain, w)).fetchone()[0]
        if t is None or ok is None:
            continue
        out.append({"chain": chain, "wallet": w, "from": t["watch_since"], "to": ok, "last_ok_fetch": ok,
                    "basis": "watch_since to last good fetch; transactions beyond a capped fetch may be missing"})
    return out


def _market(con, tok: tuple[str, str]) -> list[dict]:
    out = []
    for s in con.execute("SELECT * FROM social_alpha_series WHERE chain=? AND contract=? ORDER BY source", tok):
        rows = [dict(r) for r in con.execute("SELECT t,o,h,l,c,liq FROM social_alpha_candles WHERE series_id=? ORDER BY t", (s["series_id"],))]
        for r in rows:
            if r["liq"] is None:
                del r["liq"]
        out.append({"chain": s["chain"], "contract": s["contract"], "source": s["source"], "candle_seconds": s["candle_seconds"],
                    "as_of_kind": s["as_of_kind"], "rows": rows})
    return out


def _pool(con, tok: tuple[str, str], as_of: float) -> list[dict]:
    """Liquidity values observed at fetch time are facts about the fetch time and are placed there (never back-dated)."""
    out = []
    for f in con.execute("SELECT fact_id, value_num, pair_id, provider, source_url, fetched_at FROM social_market_facts WHERE chain=? AND contract=? "
                         "AND field='liquidity_reported' AND as_of_kind='OBSERVED_AT_FETCH' AND fetched_at<=? ORDER BY fetched_at, fact_id", (*tok, as_of)):
        out.append({"chain": tok[0], "contract": tok[1], "pool": f["pair_id"], "kind": "LIQUIDITY_SNAPSHOT", "time": f["fetched_at"], "time_basis": "FETCH",
                    "liquidity_usd": f["value_num"], "source": f["provider"], "ref": f"market_fact:{f['fact_id']}"})
    return out


def build_input(con, *, chain: str, contract: str, source_id: str, as_of: float, window: dict | None = None, annotations: dict | None = None) -> dict:
    tok = C.ident(chain, contract)
    if tok is None:
        raise ValueError("token needs chain and contract")
    tok = (tok[0], store.normalize_contract(tok[0], tok[1]))
    ann = annotations or {}
    accounts = source_accounts(con, source_id)
    if not accounts:
        raise ValueError(f"unknown source {source_id!r}: neither an account id nor a trader with linked accounts")
    posts = _posts(con, accounts, tok)
    wallets = _wallets(con, accounts, tok[0], as_of)
    addrs = [w["wallet"] for w in wallets]
    pol = C.DEFAULT_POLICY
    pubs = [p["published_at"] or min([o["observed_at"] for o in p["observations"] if o["observed_at"] is not None] or [None]) for p in posts]
    pubs = [x for x in pubs if x is not None]
    lo = (window or {}).get("from") if window else (min(pubs) - pol["window_before_s"] if pubs else None)
    hi = (window or {}).get("to") if window else as_of
    sym = con.execute("SELECT symbol_seen FROM social_token_refs WHERE chain=? AND contract=?", tok).fetchone()
    doc = {"schema": C.SCHEMA, "label": "stored posts, wallet associations, wallet events and candles", "is_fixture": False, "as_of": as_of,
           "token": {"chain": tok[0], "contract": tok[1], "symbol": sym[0] if sym else None},
           "source": {"source_id": source_id, "label": source_id, "accounts": accounts}, "posts": posts, "wallets": wallets,
           "wallet_events": _events(con, tok[0], addrs, lo, hi if hi is not None else as_of), "pool_events": _pool(con, tok, as_of), "market": _market(con, tok),
           "coverage": {"posts_enumerated": bool(ann.get("posts_enumerated")), "providers": ann.get("providers") or {},
                        "wallet_monitoring": _monitoring(con, tok[0], addrs)}}
    if window:
        doc["window"] = window
    return doc


def save_run(con, doc: dict, result: dict, *, now: float | None = None) -> dict:
    row = con.execute("SELECT run_id FROM social_chrono_runs WHERE input_sha256=?", (result["input_sha256"],)).fetchone()
    if row:
        return {"run_id": row[0], "created": False, "result_sha256": result["result_sha256"]}
    t = result["token"]
    cur = con.execute("INSERT INTO social_chrono_runs(engine_version,rules_version,chain,contract,source_id,as_of,order_status,policy_sha256,input_sha256,"
                      "result_sha256,n_timeline,n_patterns,input_json,result_json,created_at,is_fixture) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (result["engine_version"], result["rules_version"], t["chain"], t["contract"], result["source"]["source_id"], result["as_of"],
                       result["order_status"], result["policy_sha256"], result["input_sha256"], result["result_sha256"], len(result["timeline"]),
                       len(result["patterns"]), C.canon({"doc": doc, "policy": result["policy"]}), C.canon(result), _now(now), int(result["is_fixture"])))
    rid = cur.lastrowid
    for f in result["flags"]:
        con.execute("INSERT INTO social_chrono_flags(run_id,flag_key,chain,contract,source_id,flag,category,bucket,rule,order_status,attribution,at,evidence_json,note,is_fixture)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (rid, f["flag_key"], f["chain"], f["contract"], f["source_id"], f["flag"], f["category"], f["bucket"], f["rule"], f["order_status"],
                     f["attribution"], f["at"], json.dumps(f["evidence"]), f["note"], int(result["is_fixture"])))
    return {"run_id": rid, "created": True, "result_sha256": result["result_sha256"]}


def load_run(con, run_id: int) -> dict:
    r = con.execute("SELECT * FROM social_chrono_runs WHERE run_id=?", (run_id,)).fetchone()
    if r is None:
        raise ValueError(f"unknown run {run_id}")
    return {**dict(r), "input": json.loads(r["input_json"]), "result": json.loads(r["result_json"])}


def verify_run(con, run_id: int) -> dict:
    r = load_run(con, run_id)
    stored_ok = C.sha({k: v for k, v in r["result"].items() if k != "result_sha256"}) == r["result_sha256"]
    again = C.analyze(r["input"]["doc"], r["input"]["policy"])
    return {"run_id": run_id, "stored_result_matches_its_hash": stored_ok, "recomputed_result_sha256": again["result_sha256"],
            "stored_result_sha256": r["result_sha256"], "recomputation_matches": again["result_sha256"] == r["result_sha256"],
            "verified": stored_ok and again["result_sha256"] == r["result_sha256"]}


def current_flags(con, *, chain: str | None = None, contract: str | None = None, category: str | None = None, include_fixtures: bool = False) -> list[dict]:
    """Flags from the newest run of each (token, source). This is what a discovery pipeline should read; older runs stay for audit."""
    q = ("SELECT f.* FROM social_chrono_flags f JOIN (SELECT chain, contract, source_id, MAX(run_id) AS run_id FROM social_chrono_runs GROUP BY chain, contract, source_id) n "
         "ON n.run_id=f.run_id WHERE 1=1")
    a: list = []
    if chain:
        q += " AND f.chain=?"; a.append(chain.lower())
    if contract:
        q += " AND f.contract=?"; a.append(C.ident(chain or "solana", contract)[1])
    if category:
        q += " AND f.category=?"; a.append(category.upper())
    if not include_fixtures:
        q += " AND f.is_fixture=0"
    out = []
    for r in con.execute(q + " ORDER BY f.chain, f.contract, f.source_id, f.category, f.flag, f.flag_key", a):
        d = dict(r)
        d["evidence"] = json.loads(d.pop("evidence_json"))
        out.append(d)
    return out


def status(con) -> dict:
    return {"runs": [dict(r) for r in con.execute("SELECT run_id, chain, contract, source_id, as_of, order_status, n_timeline, n_patterns, result_sha256, is_fixture "
                                                    "FROM social_chrono_runs ORDER BY run_id")],
            "flags": con.execute("SELECT COUNT(*) FROM social_chrono_flags").fetchone()[0],
            "engine_version": C.ENGINE_VERSION, "rules_version": C.RULES_VERSION}
