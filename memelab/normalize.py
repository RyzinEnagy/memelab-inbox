"""Build the normalized Bundle for one mint from collector bodies.

bodies: dict key -> body (already projected by collector.js). Keys follow the plan conventions.
Every field records its source in bundle["sources"]; nothing is invented.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

SOL = "So11111111111111111111111111111111111111112"
STABLES = {"EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC", "Es9vMGANM1E2EjMA4c6kQX8m3KdMMw2sCkChfR4ZF9": "USDT"}


def _f(x) -> float | None:
    try:
        if x is None or x == "":
            return None
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def _iso_epoch(s: str | None) -> float | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _orient_trade(t: list, ref_price: float | None) -> list:
    """Normalize a projected GeckoTerminal trade to [ts, wallet, kind, base_amount, usd, base_price_usd, tx8].
    New collector format: [ts, wallet, kind, from_amt, to_amt, usd, price_from, price_to, tx8]; the base side is whichever
    price is closer to the reference price (handles pools where the token is the quote asset)."""
    if len(t) >= 9:
        ts, wallet, kind, fa, ta, usd, pf, pt, tx = t[:9]
        if ref_price and pf and pt:
            use_from = abs(pf - ref_price) <= abs(pt - ref_price)
        else:
            use_from = (kind == "sell")
        return [ts, wallet, kind, fa if use_from else ta, usd, pf if use_from else pt, tx]
    return list(t)


def empty_bundle(mint: str, observed_at: float | None = None) -> dict[str, Any]:
    return {
        "mint": mint, "observed_at": observed_at or time.time(), "sources": {},
        "identity": {}, "market": {"vol": {}, "chg": {}, "net_buyers": {}, "txns": {}, "holder_change": {}},
        "pools": [], "authorities": {}, "holders": {"top": [], "distribution": {}, "insider_networks": []},
        "quotes": {"BUY": {}, "SELL": {}}, "ohlcv": {}, "trades": [], "rpc_mint": None, "social": {}, "risks": [],
        "discrepancies": [],
    }


def build_bundle(mint: str, bodies: dict[str, Any], observed_at: float | None = None, sol_price: float | None = None) -> dict[str, Any]:
    b = empty_bundle(mint, observed_at)
    src = b["sources"]
    ident, mk = b["identity"], b["market"]
    if sol_price:
        mk["sol_price"] = sol_price
        src["sol_price"] = "coingecko"

    # ---------------- Jupiter token search ----------------
    jt = None
    for k, v in bodies.items():
        if k.startswith("jup_tok") and isinstance(v, list):
            for t in v:
                if isinstance(t, dict) and t.get("id") == mint:
                    jt = t
                    break
        if jt:
            break
    if jt:
        ident.update({
            "name": jt.get("name"), "symbol": jt.get("symbol"), "decimals": jt.get("decimals"),
            "token_program": jt.get("tokenProgram"), "dev": jt.get("dev"), "launchpad": jt.get("launchpad"),
            "graduated_pool": jt.get("graduatedPool"), "graduated_at": jt.get("graduatedAt"),
            "first_pool_at": (jt.get("firstPool") or {}).get("createdAt"),
            "website": jt.get("website"), "twitter": jt.get("twitter"), "telegram": jt.get("telegram"),
        })
        for kk in ("name", "symbol", "decimals", "token_program", "dev", "launchpad", "graduated_pool", "first_pool_at"):
            src[kk] = "jupiter.tokens_v2"
        mk.update({
            "price_usd": _f(jt.get("usdPrice")), "circ_supply": _f(jt.get("circSupply")), "total_supply": _f(jt.get("totalSupply")),
            "market_cap": _f(jt.get("mcap")), "fdv": _f(jt.get("fdv")), "liquidity_usd_total": _f(jt.get("liquidity")),
            "holder_count": jt.get("holderCount"), "organic_score": _f(jt.get("organicScore")),
            "organic_score_label": jt.get("organicScoreLabel"),
        })
        for kk in ("price_usd", "circ_supply", "total_supply", "market_cap", "fdv", "liquidity_usd_total", "holder_count", "organic_score"):
            src[kk] = "jupiter.tokens_v2"
        for w, key in (("5m", "stats5m"), ("1h", "stats1h"), ("6h", "stats6h"), ("24h", "stats24h")):
            s = jt.get(key) or {}
            mk["vol"].setdefault(w, (_f(s.get("buyVolume")) or 0) + (_f(s.get("sellVolume")) or 0) if s else None)
            mk["chg"][w] = _f(s.get("priceChange"))
            mk["net_buyers"][w] = s.get("numNetBuyers")
            mk["holder_change"][w] = _f(s.get("holderChange"))
            mk["txns"][w] = [s.get("numBuys"), s.get("numSells"), s.get("numTraders"), None]
            if w == "24h":
                mk["buy_vol_24h"], mk["sell_vol_24h"] = _f(s.get("buyVolume")), _f(s.get("sellVolume"))
                mk["organic_buy_vol_24h"], mk["organic_sell_vol_24h"] = _f(s.get("buyOrganicVolume")), _f(s.get("sellOrganicVolume"))
                mk["num_traders_24h"] = s.get("numTraders")
                mk["num_organic_buyers_24h"] = s.get("numOrganicBuyers")
            if w == "1h":
                mk["buy_vol_1h"], mk["sell_vol_1h"] = _f(s.get("buyVolume")), _f(s.get("sellVolume"))
                mk["liquidity_change_1h"] = _f(s.get("liquidityChange"))
            if w == "6h":
                mk["liquidity_change_6h"] = _f(s.get("liquidityChange"))
            if w == "24h":
                mk["liquidity_change_24h"] = _f(s.get("liquidityChange"))
        audit = jt.get("audit") or {}
        b["authorities"].update({
            "mint_authority_disabled_jup": audit.get("mintAuthorityDisabled"),
            "freeze_authority_disabled_jup": audit.get("freezeAuthorityDisabled"),
            "top_holders_pct_jup": _f(audit.get("topHoldersPercentage")),
            "dev_balance_pct_jup": _f(audit.get("devBalancePercentage")),
            "dev_migrations_jup": audit.get("devMigrations"),
        })
        b["social"].update({"website": jt.get("website"), "twitter": jt.get("twitter"), "telegram": jt.get("telegram")})

    # ---------------- DEX Screener pairs ----------------
    pairs = []
    for k, v in bodies.items():
        if k.startswith("ds") and isinstance(v, list):
            pairs += [p for p in v if isinstance(p, dict) and (p.get("baseToken") or {}).get("address") == mint]
    if pairs:
        main = max(pairs, key=lambda p: _f((p.get("liquidity") or {}).get("usd")) or 0)
        bt = main.get("baseToken") or {}
        ident.setdefault("name", bt.get("name")); ident.setdefault("symbol", bt.get("symbol"))
        ident["ds_name"], ident["ds_symbol"] = bt.get("name"), bt.get("symbol")
        if mk.get("price_usd") is None:
            mk["price_usd"] = _f(main.get("priceUsd")); src["price_usd"] = "dexscreener"
        mk["ds_price_usd"] = _f(main.get("priceUsd"))
        mk["ds_fdv"], mk["ds_market_cap"] = _f(main.get("fdv")), _f(main.get("marketCap"))
        mk["ds_liquidity_total"] = sum(_f((p.get("liquidity") or {}).get("usd")) or 0 for p in pairs)
        mk["ds_vol_24h"] = sum(_f((p.get("volume") or {}).get("h24")) or 0 for p in pairs)
        if mk["vol"].get("24h") is None:
            mk["vol"]["24h"] = mk["ds_vol_24h"]; src["vol_24h"] = "dexscreener"
        if mk.get("fdv") is None:
            mk["fdv"], mk["market_cap"] = mk["ds_fdv"], mk["ds_market_cap"]; src["fdv"] = "dexscreener"
        if mk.get("liquidity_usd_total") is None:
            mk["liquidity_usd_total"] = mk["ds_liquidity_total"]; src["liquidity_usd_total"] = "dexscreener"
        txb = {"h1": [0, 0], "h24": [0, 0]}
        for p in pairs:
            for w in ("h1", "h24"):
                t = (p.get("txns") or {}).get(w) or {}
                txb[w][0] += t.get("buys") or 0; txb[w][1] += t.get("sells") or 0
        mk["ds_txns"] = txb
        ages = [p.get("pairCreatedAt") for p in pairs if p.get("pairCreatedAt")]
        if ages:
            mk["ds_first_pair_at"] = min(ages) / 1000.0
        info = main.get("info") or {}
        if info.get("websites"):
            w0 = info["websites"][0]
            b["social"].setdefault("website", w0.get("url") if isinstance(w0, dict) else w0)
        for s in info.get("socials") or []:
            b["social"].setdefault(s.get("type"), s.get("url"))
        for p in pairs:
            liq = p.get("liquidity") or {}
            b["pools"].append({
                "pool": p.get("pairAddress"), "dex": p.get("dexId"), "labels": p.get("labels"),
                "quote": (p.get("quoteToken") or {}).get("address"), "quote_symbol": (p.get("quoteToken") or {}).get("symbol"),
                "created": datetime.fromtimestamp(p["pairCreatedAt"] / 1000, tz=timezone.utc).isoformat() if p.get("pairCreatedAt") else None,
                "reserve_usd": _f(liq.get("usd")), "base_reserve": _f(liq.get("base")), "quote_reserve": _f(liq.get("quote")),
                "vol_24h": _f((p.get("volume") or {}).get("h24")), "vol_1h": _f((p.get("volume") or {}).get("h1")),
                "txns_h24": [((p.get("txns") or {}).get("h24") or {}).get("buys"), ((p.get("txns") or {}).get("h24") or {}).get("sells"), None, None],
                "price": _f(p.get("priceUsd")), "source": "dexscreener", "lp": None, "market_type": None,
            })
        src["pools"] = "dexscreener"

    # ---------------- GeckoTerminal pools for token ----------------
    gtp = None
    for k, v in bodies.items():
        if k.startswith("gt_pools:token") and isinstance(v, dict):
            gtp = v.get("pools") or []
    if gtp:
        known = {p["pool"]: p for p in b["pools"]}
        for p in gtp:
            if p.get("base") != mint:
                continue
            row = known.get(p["pool"])
            if row is None:
                row = {"pool": p["pool"], "dex": p.get("dex"), "quote": p.get("quote"), "quote_symbol": None, "created": p.get("created"),
                       "reserve_usd": p.get("reserve"), "base_reserve": None, "quote_reserve": None, "vol_24h": (p.get("vol") or {}).get("h24"),
                       "vol_1h": (p.get("vol") or {}).get("h1"), "txns_h24": (p.get("tx") or {}).get("h24"), "price": p.get("price"),
                       "source": "geckoterminal", "lp": None, "market_type": None}
                b["pools"].append(row); known[p["pool"]] = row
            else:
                row["gt_reserve_usd"] = p.get("reserve"); row["txns_h24_gt"] = (p.get("tx") or {}).get("h24")
                row["txns_h1_gt"] = (p.get("tx") or {}).get("h1"); row["created"] = row.get("created") or p.get("created")
            row["gt_txns"] = p.get("tx"); row["gt_vol"] = p.get("vol"); row["gt_chg"] = p.get("chg")

    # ---------------- GeckoTerminal token info ----------------
    gi = next((v for k, v in bodies.items() if k.startswith("gt_info") and isinstance(v, dict) and v.get("address") == mint), None)
    if gi:
        h = gi.get("holders") or {}
        b["holders"]["total_gt"] = h.get("count")
        b["holders"]["distribution"] = h.get("distribution_percentage") or {}
        b["holders"]["distribution_updated"] = h.get("last_updated")
        b["holders"]["dev_holding_pct"] = _f(gi.get("developer_holding_percentage"))
        b["holders"]["developer_address_gt"] = gi.get("developer_address")
        b["authorities"]["mint_authority_gt"] = gi.get("mint_authority"); b["authorities"]["freeze_authority_gt"] = gi.get("freeze_authority")
        b["social"].update({k2: gi.get(k2) for k2 in ("description", "discord_url", "telegram_handle", "twitter_handle") if gi.get(k2)})
        b["social"]["gt_score"] = _f(gi.get("gt_score")); b["social"]["gt_score_details"] = gi.get("gt_score_details")
        b["social"]["gt_verified"] = gi.get("gt_verified"); b["social"]["is_honeypot_gt"] = gi.get("is_honeypot")
        if gi.get("websites"):
            b["social"].setdefault("website", gi["websites"][0])
        ident.setdefault("name", gi.get("name")); ident.setdefault("symbol", gi.get("symbol")); ident.setdefault("decimals", gi.get("decimals"))
        ident["gt_name"], ident["gt_symbol"] = gi.get("name"), gi.get("symbol")
        ld = gi.get("launchpad_details") or {}
        if ld:
            ident.setdefault("graduated_pool", ld.get("migrated_destination_pool_address"))
            ident.setdefault("graduated_at", ld.get("completed_at"))

    # ---------------- RugCheck ----------------
    rg = next((v for k, v in bodies.items() if k.startswith("rug") and isinstance(v, dict) and v.get("mint") == mint), None)
    if rg:
        tok = rg.get("token") or {}
        a = b["authorities"]
        a.update({
            "mint_authority": tok.get("mintAuthority"), "freeze_authority": tok.get("freezeAuthority"),
            "token_program": rg.get("tokenProgram"), "supply_raw": tok.get("supply"), "decimals": tok.get("decimals"),
            "extensions": rg.get("token_extensions"), "metadata_mutable": (rg.get("tokenMeta") or {}).get("mutable"),
            "update_authority": (rg.get("tokenMeta") or {}).get("updateAuthority"), "transfer_fee": rg.get("transferFee"),
        })
        for kk in ("mint_authority", "freeze_authority", "extensions", "metadata_mutable", "update_authority", "supply_raw"):
            src[kk] = "rugcheck.report"
        ident.setdefault("creator", rg.get("creator")); ident["creator"] = rg.get("creator"); src["creator"] = "rugcheck.report"
        ident.setdefault("token_program", rg.get("tokenProgram"))
        tm = rg.get("tokenMeta") or {}
        ident["rug_name"], ident["rug_symbol"] = tm.get("name"), tm.get("symbol")
        ident.setdefault("name", tm.get("name")); ident.setdefault("symbol", tm.get("symbol"))
        b["holders"]["total"] = rg.get("totalHolders")
        b["holders"]["creator_balance"] = rg.get("creatorBalance")
        b["holders"]["top"] = [{"account": h.get("address"), "owner": h.get("owner"), "pct": _f(h.get("pct")), "amount": _f(h.get("uiAmount")), "insider": bool(h.get("insider"))} for h in rg.get("topHolders") or []]
        b["holders"]["insider_networks"] = rg.get("insiderNetworks") or []
        b["holders"]["graph_insiders_detected"] = rg.get("graphInsidersDetected")
        b["holders"]["total_lp_providers"] = rg.get("totalLPProviders")
        b["risks"] = rg.get("risks") or []
        b["rug_score"] = rg.get("score_normalised") if rg.get("score_normalised") is not None else rg.get("score")
        b["rug_total_market_liquidity"] = _f(rg.get("totalMarketLiquidity"))
        b["lockers"] = rg.get("lockers"); b["locker_owners"] = rg.get("lockerOwners")
        known = {p["pool"]: p for p in b["pools"]}
        for m in rg.get("markets") or []:
            row = known.get(m.get("pubkey"))
            lp = m.get("lp") or {}
            lpinfo = {
                "locked_pct": _f(lp.get("lpLockedPct")), "locked_usd": _f(lp.get("lpLockedUSD")), "lp_total_supply": _f(lp.get("lpTotalSupply")),
                "lp_current_supply": _f(lp.get("lpCurrentSupply")), "lp_unlocked": _f(lp.get("lpUnlocked")), "lp_locked": _f(lp.get("lpLocked")),
                "base_usd": _f(lp.get("baseUSD")), "quote_usd": _f(lp.get("quoteUSD")), "mint_lp": m.get("mintLP"),
                "holders": [{"owner": h.get("owner"), "account": h.get("address"), "pct": _f(h.get("pct")), "insider": bool(h.get("insider"))} for h in lp.get("holders") or []],
            }
            if row is None:
                row = {"pool": m.get("pubkey"), "dex": None, "quote": m.get("mintB") if m.get("mintA") == mint else m.get("mintA"), "quote_symbol": None,
                       "created": None, "reserve_usd": (lpinfo["base_usd"] or 0) + (lpinfo["quote_usd"] or 0) or None, "base_reserve": None,
                       "quote_reserve": None, "vol_24h": None, "vol_1h": None, "txns_h24": None, "price": None, "source": "rugcheck", "lp": None, "market_type": None}
                b["pools"].append(row); known[row["pool"]] = row
            row["lp"] = lpinfo; row["market_type"] = m.get("marketType")
        src["lp"] = "rugcheck.report"

    # ---------------- RPC mint account ----------------
    rpc = next((v for k, v in bodies.items() if k.startswith("rpc:mint") and isinstance(v, dict)), None)
    if rpc and isinstance(rpc.get("result"), dict):
        val = (rpc["result"] or {}).get("value") or {}
        parsed = ((val.get("data") or {}).get("parsed") or {})
        info = parsed.get("info") or {}
        b["rpc_mint"] = {"owner_program": val.get("owner"), "info": info, "type": parsed.get("type"), "slot": (rpc["result"].get("context") or {}).get("slot")}
        a = b["authorities"]
        a["mint_authority_rpc"] = info.get("mintAuthority"); a["freeze_authority_rpc"] = info.get("freezeAuthority")
        a["supply_raw_rpc"] = info.get("supply"); a["decimals_rpc"] = info.get("decimals"); a["extensions_rpc"] = info.get("extensions")
        a["token_program_rpc"] = val.get("owner")
        src["mint_authority_rpc"] = "solana_rpc.getAccountInfo"

    # ---------------- OHLCV / trades (only for THIS token's pools) ----------------
    my_pools = {p.get("pool") for p in b["pools"] if p.get("pool")}
    ref_price = mk.get("price_usd")
    for k, v in bodies.items():
        parts = k.split(":")
        if k.startswith("gt_ohlcv") and isinstance(v, dict) and len(parts) >= 3 and parts[1] in my_pools:
            tf = parts[-1]  # e.g. day1 / hour1 / minute15
            rows = v.get("ohlcv") or []
            meta = v.get("meta") or {}
            meta_base = (meta.get("base") or {}).get("address"); meta_quote = (meta.get("quote") or {}).get("address")
            if meta_base and meta_base != mint:
                # candles describe the base token unless the request pinned token=<mint>; sanity-check against the reference price
                closes = [r[4] for r in rows if len(r) > 4 and r[4]]
                last_close = closes[0] if closes else None
                if not (ref_price and last_close and 0.3 * ref_price <= last_close <= 3 * ref_price):
                    b["discrepancies"].append(f"ohlcv for pool {parts[1][:8]}.. priced in base {meta_base[:8]}.. (this mint is the quote side); candles skipped, re-fetch with token={mint[:6]}..")
                    continue
            if rows and (tf not in b["ohlcv"] or len(rows) > len(b["ohlcv"][tf])):
                b["ohlcv"][tf] = rows
        if k.startswith("gt_trades") and isinstance(v, dict) and len(parts) >= 3 and parts[1] in my_pools:
            for t in v.get("trades") or []:
                b["trades"].append(_orient_trade(t, ref_price))
    if b["trades"]:
        # sanity filter BEFORE dedup so a mis-oriented legacy row never shadows a correctly priced copy of the same tx
        if ref_price:
            sane = [t for t in b["trades"] if t[5] and 0.2 * ref_price <= t[5] <= 5 * ref_price]
            dropped = len(b["trades"]) - len(sane)
            if dropped:
                b["discrepancies"].append(f"{dropped} trade rows dropped before dedup: price more than 5x away from current price (quote-side pricing in legacy rows, or stale)")
            b["trades"] = sane
        seen = set(); dedup = []
        for t in b["trades"]:
            key = (t[6], t[1], t[2]) if len(t) > 6 and t[6] else tuple(t[:5])
            if key in seen:
                continue
            seen.add(key); dedup.append(t)
        b["trades"] = sorted(dedup, key=lambda t: t[0] or "")

    # ---------------- Jupiter quotes ----------------
    for k, v in bodies.items():
        if k.startswith("jq:") and isinstance(v, dict):
            _, side, usd, m = k.split(":")
            if m != mint:
                continue
            usd = float(usd)
            if v.get("error") or v.get("errorCode"):
                b["quotes"][side][usd] = {"status": "NO_ROUTE" if "route" in str(v.get("error", "")).lower() or v.get("errorCode") in ("COULD_NOT_FIND_ANY_ROUTE",) else "ERROR", "error": v.get("error")}
            else:
                b["quotes"][side][usd] = {"in": _f(v.get("inAmount")), "out": _f(v.get("outAmount")), "impact": _f(v.get("impact")), "usd": _f(v.get("usd")),
                                          "route": v.get("route") or [], "status": "OK", "slot": v.get("slot")}
    if b["quotes"]["BUY"] or b["quotes"]["SELL"]:
        src["quotes"] = "jupiter.quote_v1"

    # ---------------- derived ----------------
    first = _iso_epoch(ident.get("first_pool_at")) or mk.get("ds_first_pair_at")
    pool_times = [_iso_epoch(p.get("created")) for p in b["pools"] if p.get("created")]
    if pool_times:
        first = min([t for t in [first] + pool_times if t])
    mk["age_hours"] = (b["observed_at"] - first) / 3600 if first else None
    mk["first_seen_epoch"] = first
    if mk.get("price_usd") and mk.get("sol_price"):
        mk["price_sol"] = mk["price_usd"] / mk["sol_price"]

    # name/symbol agreement across sources
    names = {s: ident.get(f"{s}_name") for s in ("ds", "gt", "rug")}
    names["jup"] = jt.get("name") if jt else None
    present = {s: n for s, n in names.items() if n}
    ident["sources_agreeing"] = len(present)
    ident["name_matches"] = (len({n.strip().lower() for n in present.values()}) == 1) if len(present) >= 2 else None
    syms = {s: ident.get(f"{s}_symbol") for s in ("ds", "gt", "rug")}
    syms["jup"] = jt.get("symbol") if jt else None
    ps = {s: n for s, n in syms.items() if n}
    ident["symbol_matches"] = (len({n.strip().upper() for n in ps.values()}) == 1) if len(ps) >= 2 else None

    # discrepancies worth recording
    if mk.get("ds_price_usd") and mk.get("price_usd"):
        d = abs(mk["ds_price_usd"] - mk["price_usd"]) / mk["price_usd"]
        if d > 0.03:
            b["discrepancies"].append(f"price: jupiter {mk['price_usd']:.6g} vs dexscreener {mk['ds_price_usd']:.6g} ({d:.1%} apart)")
    if mk.get("ds_liquidity_total") and mk.get("liquidity_usd_total"):
        d = abs(mk["ds_liquidity_total"] - mk["liquidity_usd_total"]) / max(mk["liquidity_usd_total"], 1)
        if d > 0.25:
            b["discrepancies"].append(f"liquidity: jupiter ${mk['liquidity_usd_total']:,.0f} vs dexscreener ${mk['ds_liquidity_total']:,.0f} (methodology differs; jupiter counts both sides across routes)")
    if b["holders"].get("total") and b["holders"].get("total_gt") and mk.get("holder_count"):
        vals = {"rugcheck": b["holders"]["total"], "geckoterminal": b["holders"]["total_gt"], "jupiter": mk["holder_count"]}
        lo, hi = min(vals.values()), max(vals.values())
        if hi and (hi - lo) / hi > 0.1:
            b["discrepancies"].append("holder count: " + ", ".join(f"{k} {v:,}" for k, v in vals.items()))
    return b
