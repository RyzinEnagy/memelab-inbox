"""Phase 17: build a replay input (memelab.social.replay.input/1) from history the lab actually holds. Read-only.

Sources:
  - a lab database (read-only): legacy market_snapshots as dated prices; and, when the social schema exists, CALL claims with
    resolved contracts as posts (available when first observed), repost references, wallet events with their linkage, Phase 11
    candle series (available when recorded) and social_market_facts prices and liquidity (available when fetched);
  - a folder of collector result files (inbox/*.json): GeckoTerminal OHLCV, GeckoTerminal trending pool lists and DexScreener
    boost lists, each available at the file's collection time.

Availability is the lab's capture time unless `candle_availability="provider"` is asked for, in which case a candle is
available at its close plus the documented provider lag (a reconstruction, labelled as such). Nothing here fetches.
No post text is read or kept: posts are ids, times, direction and contract only.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sqlite3
from datetime import datetime
from typing import Any

from .replay_core import SCHEMA, iso, tkey

GT_NET = {"eth": "ethereum", "polygon_pos": "polygon", "sui-network": "sui", "avax": "avalanche"}
TF = {"minute1": 60, "minute5": 300, "minute15": 900, "hour1": 3600, "hour4": 14400, "day1": 86400}
PROVIDER_LAG = {"geckoterminal-ohlcv": 300}   # HEURISTIC: assumed delay before a closed GeckoTerminal candle is served


def _ts(v) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str) and v:
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def _tables(con) -> set[str]:
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def empty_doc(label: str) -> dict:
    return {"schema": SCHEMA, "label": label, "is_fixture": False, "as_of": None,
            "coverage": {"version": None, "providers": {}, "universe": {}}, "sources": [], "tokens": [], "posts": [],
            "wallet_events": [], "trending": [], "candles": [], "points": [], "notes": []}


def from_db(path: str) -> dict:
    doc = empty_doc(f"lab database {os.path.basename(path)}")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    tabs = _tables(con)
    chain_of = {}
    if "tokens" in tabs:
        for r in con.execute("SELECT mint, chain FROM tokens"):
            chain_of[r["mint"]] = (r["chain"] or "solana")
    if "market_snapshots" in tabs:
        for r in con.execute("SELECT mint, observed_at, source, price_usd, liquidity_usd, market_cap FROM market_snapshots ORDER BY id"):
            if r["observed_at"] is None:
                continue
            doc["points"].append({"chain": chain_of.get(r["mint"], "solana"), "contract": r["mint"], "t": r["observed_at"],
                                  "available_at": r["observed_at"], "provider": f"lab-snapshot:{r['source']}", "price": r["price_usd"],
                                  "liq": r["liquidity_usd"], "mcap": r["market_cap"]})
    if {"social_claims", "social_items", "social_token_refs"} <= tabs:
        reposts = {}
        if "social_item_refs" in tabs:
            for r in con.execute("SELECT item_key, referenced_item_key FROM social_item_refs WHERE ref_type IN ('retweeted','quoted')"):
                reposts[r["item_key"]] = r["referenced_item_key"]
        if "social_item_forwards" in tabs:
            cols = {c[1] for c in con.execute("PRAGMA table_info(social_item_forwards)")}
            if "item_key" in cols:
                for r in con.execute("SELECT item_key FROM social_item_forwards"):
                    reposts.setdefault(r["item_key"], "forward")
        q = """SELECT c.id, c.direction, i.item_key, i.account_id, i.published_at, i.first_observed_at, r.chain, r.contract
               FROM social_claims c JOIN social_items i ON c.item_key = i.item_key
               LEFT JOIN social_token_refs r ON c.token_ref_id = r.ref_id AND r.ref_kind IN ('CONTRACT_ADDRESS','OFFICIAL_LINK')
               WHERE c.claim_type = 'CALL' ORDER BY c.id"""
        for r in con.execute(q):
            doc["posts"].append({"post_id": f"claim{r['id']}", "source_id": r["account_id"] or "unknown", "chain": r["chain"],
                                 "contract": r["contract"], "direction": r["direction"], "published_at": r["published_at"],
                                 "available_at": r["first_observed_at"], "captured_at": r["first_observed_at"],
                                 "repost_of": reposts.get(r["item_key"]), "provider": "lab-social"})
        seen = {p["source_id"] for p in doc["posts"]}
        doc["sources"] = [{"source_id": s, "independence_group": s} for s in sorted(seen)]
    if {"social_wallet_events", "social_wallet_event_legs"} <= tabs:
        link = {}
        if "social_wallet_assertions" in tabs:
            for a in con.execute("SELECT account_entity, chain, wallet_address, evidence_type, signature_check, review_state, status "
                                 "FROM social_wallet_assertions ORDER BY assertion_id"):
                if a["status"] != "ACTIVE" or a["review_state"] == "REJECTED":
                    continue
                kind = {"OFFICIAL_SELF_DISCLOSURE": "SELF_CLAIMED", "SIGNED_MESSAGE": "SIGNED_MESSAGE" if a["signature_check"] == "VALID_BOUND" else "UNKNOWN",
                        "TRANSACTION_PATTERN": "CHAIN_EVIDENCE" if a["review_state"] == "APPROVED" else "UNKNOWN",
                        "THIRD_PARTY_CLAIM": "THIRD_PARTY_CLAIM", "INDEPENDENT_LINKED_SOURCE": "THIRD_PARTY_CLAIM"}.get(a["evidence_type"], "UNKNOWN")
                link[(a["chain"], a["wallet_address"])] = (a["account_entity"], kind)
        q = """SELECT e.event_id, e.chain, e.wallet_address, e.block_time, e.swap_side, e.ingested_at, l.contract
               FROM social_wallet_events e JOIN social_wallet_event_legs l ON l.event_id = e.event_id
               WHERE e.event_type = 'SWAP' AND e.swap_side IN ('BUY','SELL') AND l.asset_kind = 'TOKEN'
                 AND ((e.swap_side = 'BUY' AND l.direction = 'IN') OR (e.swap_side = 'SELL' AND l.direction = 'OUT'))
               ORDER BY e.event_id, l.leg_index"""
        for r in con.execute(q):
            src, kind = link.get((r["chain"], r["wallet_address"]), ("", "UNKNOWN"))
            doc["wallet_events"].append({"event_id": f"we{r['event_id']}:{r['contract']}", "source_id": src, "linkage": kind,
                                         "chain": r["chain"], "contract": r["contract"], "side": r["swap_side"], "block_time": r["block_time"],
                                         "available_at": r["ingested_at"], "captured_at": r["ingested_at"]})
    if {"social_alpha_series", "social_alpha_candles"} <= tabs:
        for s in con.execute("SELECT * FROM social_alpha_series ORDER BY series_id"):
            if s["is_fixture"]:
                continue
            for c in con.execute("SELECT * FROM social_alpha_candles WHERE series_id = ? ORDER BY t", (s["series_id"],)):
                doc["candles"].append({"chain": s["chain"], "contract": s["contract"], "provider": f"alpha:{s['source']}", "period_s": s["candle_seconds"],
                                       "t": c["t"], "o": c["o"], "h": c["h"], "l": c["l"], "c": c["c"], "liq": c["liq"], "available_at": s["recorded_at"]})
            if s["delisted_at"]:
                doc["tokens"].append({"chain": s["chain"], "contract": s["contract"], "delisted_at": s["delisted_at"], "delisted_available_at": s["recorded_at"]})
    if "social_market_facts" in tabs:
        for f in con.execute("SELECT chain, contract, field, value_num, provider, as_of, fetched_at FROM social_market_facts "
                             "WHERE field IN ('price','liquidity_reported') AND value_num IS NOT NULL AND as_of IS NOT NULL ORDER BY fact_id"):
            pt = {"chain": f["chain"], "contract": f["contract"], "t": f["as_of"], "available_at": f["fetched_at"], "provider": f"facts:{f['provider']}"}
            pt.update(price=f["value_num"]) if f["field"] == "price" else pt.update(liq=f["value_num"])
            doc["points"].append(pt)
    con.close()
    doc["notes"].append("social tables present" if "social_claims" in tabs else "no social schema in this database: no posts, wallet events or facts")
    return doc


def from_inbox(folder: str, *, candle_availability: str = "capture") -> dict:
    doc = empty_doc(f"collector files {folder}")
    files = sorted(glob.glob(os.path.join(folder, "**", "*.json"), recursive=True))
    bodies = []
    for p in files:
        try:
            d = json.load(open(p))
        except (OSError, ValueError):
            continue
        if isinstance(d, dict):
            bodies.append((os.path.relpath(p, folder), d))
    # chain evidence per base address: GeckoTerminal pool lists and Solana-only collectors (jup_tok, rug)
    net_of_pool, solana = {}, set()
    for _p, d in bodies:
        for k, v in d.items():
            if not isinstance(v, dict):
                continue
            b = v.get("body")
            if k.startswith("gt_pools:") and isinstance(b, dict):
                for pl in b.get("pools") or []:
                    if pl.get("pool") and pl.get("net"):
                        net_of_pool[pl["pool"]] = GT_NET.get(pl["net"], pl["net"])
            if k.startswith(("jup_tok:", "rug:")):
                solana.add(k.split(":", 1)[1])
    unresolved = 0
    for path, d in bodies:
        at = _ts(d.get("_at"))
        if at is None:
            continue
        for k, v in d.items():
            if not isinstance(v, dict) or v.get("s") not in (200, None):
                continue
            b = v.get("body")
            if k.startswith("gt_ohlcv:") and isinstance(b, dict):
                parts = k.split(":")
                pool, tf = parts[1], parts[-1]
                base = (((b.get("meta") or {}).get("base")) or {}).get("address")
                chain = net_of_pool.get(pool) or ("solana" if base in solana else None)
                if not base or not chain or tf not in TF:
                    unresolved += 1
                    continue
                for row in b.get("ohlcv") or []:
                    if not isinstance(row, list) or len(row) < 5:
                        continue
                    c = {"chain": chain, "contract": base, "provider": "geckoterminal-ohlcv", "period_s": TF[tf], "t": float(row[0]),
                         "o": row[1], "h": row[2], "l": row[3], "c": row[4], "captured_at": at}
                    if candle_availability == "capture":
                        c["available_at"] = at
                    doc["candles"].append(c)
            elif k.startswith("gt_pools:") and "trending" in k and isinstance(b, dict):
                page = k.split(":")[-1]
                off = (int(page) - 1) * 20 if page.isdigit() else 0
                for i, pl in enumerate(b.get("pools") or []):
                    net = GT_NET.get(pl.get("net"), pl.get("net"))
                    if not (net and pl.get("base")):
                        continue
                    doc["trending"].append({"snapshot_id": f"{path}:{k}", "provider": f"geckoterminal-{k.split(':')[2]}", "chain": net,
                                            "contract": pl["base"], "rank": off + i + 1, "t": at, "available_at": at, "captured_at": at})
                    doc["points"].append({"chain": net, "contract": pl["base"], "t": at, "available_at": at, "provider": "geckoterminal-pools",
                                          "price": pl.get("price"), "liq": pl.get("reserve"), "mcap": pl.get("mcap") or pl.get("fdv")})
            elif k.startswith("ds_boosts") and isinstance(b, list):
                for i, x in enumerate(b):
                    if isinstance(x, dict) and x.get("chainId") and x.get("tokenAddress"):
                        doc["trending"].append({"snapshot_id": f"{path}:{k}", "provider": "dexscreener-boosts", "chain": x["chainId"],
                                                "contract": x["tokenAddress"], "rank": i + 1, "t": at, "available_at": at, "captured_at": at})
    if unresolved:
        doc["notes"].append(f"{unresolved} OHLCV series skipped: chain or base token could not be established from the files")
    doc["notes"].append(f"{len(bodies)} collector files read; candle availability: "
                        + ("lab capture time (demonstrable)" if candle_availability == "capture" else "close + assumed provider lag (reconstruction)"))
    return doc


def merge(*docs: dict, candle_availability: str = "capture") -> dict:
    out = empty_doc(" + ".join(d["label"] for d in docs))
    for d in docs:
        for k in ("sources", "tokens", "posts", "wallet_events", "trending", "candles", "points", "notes"):
            out[k] += d[k]
    times = [p.get("available_at") for k in ("posts", "wallet_events", "trending", "points") for p in out[k]]
    times += [c.get("available_at") or c["t"] + c["period_s"] + PROVIDER_LAG.get(c["provider"], 0) for c in out["candles"]]
    times = [t for t in times if isinstance(t, (int, float))]
    out["as_of"] = max(times) if times else None
    provs: dict[str, dict] = {}

    def note(name, kind, t):
        p = provs.setdefault(name, {"kind": kind, "publication_lag_s": PROVIDER_LAG.get(name) if candle_availability == "provider" else None,
                                    "window": [t, t], "records": 0})
        p["window"] = [min(p["window"][0], t), max(p["window"][1], t)]
        p["records"] += 1

    for c in out["candles"]:
        note(c["provider"], "PRICE", c["t"])
    for p in out["points"]:
        note(p["provider"], "PRICE", p["t"])
    for t in out["trending"]:
        note(t["provider"], "TRENDING", t["t"])
    for p in out["posts"]:
        if isinstance(p.get("published_at"), (int, float)):
            note(p.get("provider") or "lab-social", "SOCIAL", p["published_at"])
    for w in out["wallet_events"]:
        note("lab-wallet-events", "WALLET", w["block_time"])
    out["coverage"] = {"version": "real-" + hashlib.sha256(json.dumps(sorted((k, v["records"], v["window"]) for k, v in provs.items()),
                                                                       default=str).encode()).hexdigest()[:12],
                       "providers": provs,
                       "universe": {"basis": "only tokens the lab's runs happened to fetch; delisted tokens are not tracked", "includes_delisted": False,
                                    "token_count": len({tkey(x["chain"], x["contract"]) for k in ("candles", "points", "trending") for x in out[k] if x.get("chain")})}}
    return out


def inventory(doc: dict) -> dict:
    """What history exists, per kind, and how much forward price coverage follows each trending observation."""
    per_tok: dict[tuple, list[float]] = {}
    for c in doc["candles"]:
        per_tok.setdefault(tkey(c["chain"], c["contract"]), []).append(c["t"])
    for p in doc["points"]:
        if p.get("price"):
            per_tok.setdefault(tkey(p["chain"], p["contract"]), []).append(p["t"])
    spans = {k: (min(v), max(v)) for k, v in per_tok.items()}
    fwd = []
    for t in doc["trending"]:
        k = tkey(t["chain"], t["contract"])
        after = [x for x in per_tok.get(k, []) if x > t["t"]]
        fwd.append(max(after) - t["t"] if after else 0.0)
    resolved_posts = [p for p in doc["posts"] if p.get("chain") and p.get("contract")]
    return {
        "label": doc["label"], "as_of": doc["as_of"], "as_of_iso": iso(doc["as_of"]),
        "posts": len(doc["posts"]), "posts_resolved": len(resolved_posts), "sources": len({p["source_id"] for p in doc["posts"]}),
        "wallet_events": len(doc["wallet_events"]), "trending_entries": len(doc["trending"]),
        "trending_snapshots": len({t["snapshot_id"] for t in doc["trending"]}),
        "candles": len(doc["candles"]), "points": len(doc["points"]), "tokens_with_prices": len(spans),
        "tokens_price_span_ge_1d": sum(1 for a, b in spans.values() if b - a >= 86400),
        "tokens_price_span_ge_7d": sum(1 for a, b in spans.values() if b - a >= 7 * 86400),
        "earliest_price": iso(min((a for a, _ in spans.values()), default=None)), "latest_price": iso(max((b for _, b in spans.values()), default=None)),
        "trending_with_24h_forward_prices": sum(1 for x in fwd if x >= 86400 + 1200),
        "trending_with_1h_forward_prices": sum(1 for x in fwd if x >= 3600 + 1200),
        "notes": doc["notes"], "coverage_version": doc["coverage"].get("version"),
    }


def render_inventory(inv: dict) -> str:
    L = [f"History inventory: {inv['label']}", f"data clock ends {inv['as_of_iso']}; coverage version {inv['coverage_version']}", "",
         f"posts {inv['posts']} (resolved to a contract {inv['posts_resolved']}) from {inv['sources']} sources",
         f"wallet events {inv['wallet_events']}",
         f"trending entries {inv['trending_entries']} in {inv['trending_snapshots']} lists; with >=1h of later prices {inv['trending_with_1h_forward_prices']}, "
         f">=24h {inv['trending_with_24h_forward_prices']}",
         f"candles {inv['candles']}, price points {inv['points']}, tokens with prices {inv['tokens_with_prices']} "
         f"(span >=1 day {inv['tokens_price_span_ge_1d']}, >=7 days {inv['tokens_price_span_ge_7d']}); prices from {inv['earliest_price']} to {inv['latest_price']}", ""]
    L += [f"note: {n}" for n in inv["notes"]]
    return "\n".join(L) + "\n"
