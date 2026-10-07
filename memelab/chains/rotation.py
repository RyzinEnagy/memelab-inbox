"""Layer 1: CHAIN_ROTATION_ENGINE with the Speculative Opportunity Index (SOI, 0-100).

Components (max points): DEX activity 20, meme activity 20, participation 15, capital flows 15, attention 15, opportunity quality 15.
Every component lists its parts, the value each part took, and what was UNKNOWN (unknown parts earn zero and are never redistributed).
Rotation statements separate FACT (measured), INFERENCE (what the numbers suggest) and CONFIDENCE (data coverage + history depth).
Research allocation follows SOI but never drops a Tier-1 chain below WATCHLIST: rotations reverse.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Any

from .. import db
from . import registry as R
from ._util import Component, clear_at, confidence_from_coverage, lin, loglin, median, pct_change, ratio

MAJORS = {"WETH", "ETH", "USDC", "USDT", "USDbC", "WBTC", "CBBTC", "SOL", "WSOL", "BNB", "WBNB", "DAI", "STETH", "WSTETH", "USDE", "USD1", "FDUSD", "BUSD", "POL", "WMATIC", "AVAX", "WAVAX", "ARB", "SUI", "HYPE", "WHYPE", "USDS", "USDH", "USDT0", "BTCB", "WETH.E", "USDC.E", "USDT.E", "ETHB", "JITOSOL", "MSOL", "BSOL",
          # DeFi / infrastructure / commodity tokens that trend on DEXes but are not memes
          "AERO", "ZRO", "UNI", "AAVE", "LINK", "CAKE", "XAUT", "PAXG", "ZEN", "ARK", "VIRTUAL", "VVV", "WELL", "MORPHO", "COMP", "CRV", "CVX", "PENDLE", "LDO", "RPL", "EIGEN", "ENA", "ONDO", "RAY", "JUP", "ORCA", "PYTH", "JTO", "W", "TNSR", "DRIFT", "KMNO", "RENDER", "HNT", "MOBILE", "IO", "GRASS", "ZK", "STRK", "OP", "MNT", "TIA", "SEI", "APT", "NEAR", "DOT", "ADA", "XRP", "TRX", "TON", "LTC", "BCH", "ETC", "FIL", "ATOM", "INJ", "FET", "TAO", "WLD", "GALA", "SAND", "MANA", "AXS", "IMX", "APE", "GMT", "DYDX", "GMX", "SNX", "MKR", "SKY", "FRAX", "FXS", "LQTY", "BAL", "SUSHI", "1INCH", "YFI", "ALPHA", "BEL", "TWT", "XVS", "ALPACA", "BSW", "BAKE", "BURGER", "AUTO", "BIFI", "LISTA", "SLISBNB", "ASBNB", "ANKRBNB", "STKBNB", "BNBX", "WBETH", "RETH", "CBETH", "WEETH", "EZETH", "RSETH", "PUFETH", "METH", "SWETH", "FRXETH", "SFRXETH", "OSETH", "ETHX", "ANKRETH", "LSETH", "WSTETH", "STETH", "AEUR", "EURC", "EURS", "AGEUR", "PYUSD", "GHO", "LUSD", "SUSD", "DOLA", "MIM", "CRVUSD", "USDD", "USDP", "TUSD", "GUSD", "USD0", "USDA", "DEUSD", "SUSDE", "SDAI", "SUSDS"}
STOCK_RX = re.compile(r"stock|xstock|bstock|tokenized|backed|equity|share|etf|treasur|t-bill|bond", re.I)
LST_RX = re.compile(r"^(w|wst|st|cb|we|ez|rs|puf|m|sw|frx|sfrx|os|ankr|ls|b|bnb|sl|as|stk)?(eth|btc|sol|bnb|avax|pol|matic|hype|sui)(b|x)?$", re.I)


def _is_meme_pool(p: dict) -> bool:
    """Heuristic meme filter for DEX pool rows. Excludes majors, stablecoins, liquid-staking derivatives, tokenized stocks, known DeFi
    governance/infra tokens and anything above a $2B FDV. Everything else is treated as a speculative (meme-like) token."""
    name = (p.get("name") or "")
    base_sym = name.split("/")[0].strip()
    up = base_sym.upper()
    fdv = p.get("fdv") or p.get("mcap") or 0
    if (p.get("base") or "").lower().startswith("0xb2000000000000"):  # Backed bStocks vanity prefix on Base (tokenized equities)
        return False
    if up in MAJORS or (fdv or 0) >= 2e9 or up.startswith("USD") or up.endswith("USD") or LST_RX.match(base_sym) or STOCK_RX.search(name):
        return False
    # tokenized-equity convention on Base/BNB: ticker root + lowercase 'c' or 'b' (MSTRc, AAPLb) or ending in 'on'/'x' stock wrappers
    if re.match(r"^[A-Z]{2,5}[cb]$", base_sym) or re.match(r"^[A-Z]{2,5}(on|x)$", base_sym):
        return False
    return True


def _pools(bodies: dict, net: str, kind: str) -> list[dict]:
    """Pools for one network and plan kind (trending matches trending/trending24/trending1h), deduplicated by pool address."""
    seen: dict[str, dict] = {}
    for k, v in bodies.items():
        if k.startswith(f"gt_pools:{net}:{kind}") and isinstance(v, dict):
            for p in v.get("pools") or []:
                if p.get("pool") and p["pool"] not in seen:
                    seen[p["pool"]] = p
    return list(seen.values())


def _hours_ago(iso: str | None, t: float) -> float | None:
    if not iso:
        return None
    try:
        return (t - datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()) / 3600
    except ValueError:
        return None


def score_chain(chain: str, bodies: dict[str, Any], t: float, con, prev_rows: dict[str, Any], catalyst_hits: int, xnet_share: float | None, profile_counts: dict[str, int], boost_counts: dict[str, int]) -> dict[str, Any]:
    cfg = R.CHAINS[chain]; net = cfg["gt_network"]
    comps: dict[str, Component] = {}
    # ---- DEX activity (20) ----
    c = comps["dex_activity"] = Component("dex_activity", 20)
    ld = bodies.get(f"llama_dex:{chain}") if isinstance(bodies.get(f"llama_dex:{chain}"), dict) else None
    vol24 = avg7 = avg30 = None
    if ld:
        chart = [v for _, v in (ld.get("chart") or []) if v is not None]
        vol24 = ld.get("total24h") or (chart[-1] if chart else None)
        hist = chart[:-1] if chart and ld.get("total24h") is None else chart[:-1]  # last point is the partial current day
        avg7 = sum(hist[-7:]) / len(hist[-7:]) if len(hist) >= 3 else None
        avg30 = sum(hist[-30:]) / len(hist[-30:]) if len(hist) >= 10 else None
        c.add(8, loglin(vol24, 5e6, 3e9), "absolute 24h DEX volume (log $5M..$3B)")
        c.add(6, lin(ratio(vol24, avg7), 0.5, 1.6), "24h volume vs 7d average (0.5x..1.6x)")
        c.add(6, lin(ratio(avg7, avg30), 0.6, 1.5), "7d average vs 30d average (0.6x..1.5x)")
        c.fact(f"DEX volume 24h ${(vol24 or 0) / 1e6:,.0f}M; 7d avg ${(avg7 or 0) / 1e6:,.0f}M; 30d avg ${(avg30 or 0) / 1e6:,.0f}M" + (f"; top venues {', '.join(p[0] for p in (ld.get('protocols') or [])[:3])}" if ld.get("protocols") else ""))
    else:
        c.add(20, None, "DefiLlama DEX overview missing")
    # ---- meme activity (20) ----
    c = comps["meme_activity"] = Component("meme_activity", 20)
    cat = cfg.get("cg_meme_category")
    mk = bodies.get(f"cg_mkts:{cat}:1") if cat and isinstance(bodies.get(f"cg_mkts:{cat}:1"), list) else None
    meme_mcap = meme_vol = meme_chg = None; gainers = losers = None
    if mk:
        meme_mcap = sum(m.get("market_cap") or 0 for m in mk); meme_vol = sum(m.get("total_volume") or 0 for m in mk)
        ch = [m.get("price_change_percentage_24h") for m in mk if m.get("price_change_percentage_24h") is not None]
        meme_chg = median(ch); gainers = sum(1 for x in ch if x > 0); losers = sum(1 for x in ch if x <= 0)
        c.add(5, loglin(meme_vol, 2e6, 3e9), f"meme category 24h volume (log $2M..$3B), n={len(mk)}")
        c.add(4, lin(ratio(meme_vol, meme_mcap), 0.03, 0.4), "meme volume / market cap (0.03..0.4)")
        c.add(4, lin(meme_chg, -10, 15), "median 24h change of the chain's memes (-10%..+15%)")
        c.fact(f"CoinGecko {cat}: {len(mk)} tokens, mcap ${meme_mcap / 1e9:,.2f}B, vol ${meme_vol / 1e6:,.0f}M, median 24h {meme_chg:+.1f}%, {gainers} up / {losers} down")
    else:
        c.add(13, None, f"no CoinGecko meme category for {chain}" if not cat else f"CoinGecko {cat} not fetched")
    tr = _pools(bodies, net, "trending")
    if tr:
        memes = [p for p in tr if _is_meme_pool(p)]
        share = len(memes) / len(tr)
        tvol = sum((p.get("vol") or {}).get("h24") or 0 for p in memes)
        c.add(4, lin(share, 0.2, 0.9), "meme share of trending pools (20%..90%)")
        c.add(3, loglin(tvol, 1e6, 5e8), "24h volume of trending meme pools (log $1M..$500M)")
        c.fact(f"GeckoTerminal trending: {len(memes)}/{len(tr)} pools are memes, their 24h volume ${tvol / 1e6:,.1f}M")
    else:
        c.add(7, None, "GeckoTerminal trending pools missing")
    # ---- participation (15) ----
    c = comps["participation"] = Component("participation", 15)
    if tr:
        buyers = sum(((p.get("tx") or {}).get("h24") or [0, 0, 0, 0])[2] or 0 for p in tr)
        sellers = sum(((p.get("tx") or {}).get("h24") or [0, 0, 0, 0])[3] or 0 for p in tr)
        txs = sum(sum(x or 0 for x in ((p.get("tx") or {}).get("h24") or [0, 0])[:2]) for p in tr)
        c.add(6, loglin(buyers, 2000, 300000), "unique 24h buyers across trending pools (log 2k..300k)")
        c.add(3, lin(ratio(buyers, sellers), 0.8, 1.4), "buyers / sellers across trending pools (0.8..1.4)")
        c.fact(f"trending pools: {buyers:,} unique buyers, {sellers:,} unique sellers, {txs:,} trades in 24h")
    else:
        c.add(9, None, "trending pools missing")
    new = _pools(bodies, net, "new")
    if new:
        fresh = [p for p in new if (_hours_ago(p.get("created"), t) or 99) <= 24]
        funded = [p for p in fresh if (p.get("reserve") or 0) >= 10_000]
        c.add(6, loglin(len(funded) + 1, 1, 15), "new pools in the last 24h with >= $10k liquidity (sample of 20 newest; log 1..15)")
        c.fact(f"newest pools sample: {len(fresh)}/{len(new)} created in the last 24h, {len(funded)} with >= $10k liquidity")
    else:
        c.add(6, None, "new pools missing")
    # ---- capital flows (15) ----
    c = comps["capital_flows"] = Component("capital_flows", 15)
    st = {x[0]: x[1] for x in (bodies.get("llama_stables") or []) if isinstance(x, list) and len(x) == 2}
    tvls = {x[0]: x[1] for x in (bodies.get("llama_chains") or []) if isinstance(x, list) and len(x) >= 2}
    stable = st.get(cfg["llama"]); tvl = tvls.get(cfg["llama"])
    prev = prev_rows.get(chain) or {}
    stable_chg = pct_change(stable, prev.get("stablecoin_mcap")); tvl_chg = pct_change(tvl, prev.get("tvl_usd"))
    c.add(4, loglin(stable, 1e8, 1.5e11), "stablecoin supply on chain (log $100M..$150B)")
    c.add(5, lin(stable_chg, -3, 5), "stablecoin supply change vs previous snapshot >= 6 days old (-3%..+5%)")
    c.add(3, loglin(tvl, 1e8, 1e11), "TVL (log $100M..$100B)")
    c.add(3, lin(tvl_chg, -10, 15), "TVL change vs previous snapshot (-10%..+15%)")
    if stable is not None or tvl is not None:
        c.fact(f"stablecoins ${(stable or 0) / 1e9:,.2f}B" + (f" ({stable_chg:+.2f}% vs ~7d)" if stable_chg is not None else " (change UNKNOWN until a 6-day-old snapshot exists)") + f"; TVL ${(tvl or 0) / 1e9:,.2f}B" + (f" ({tvl_chg:+.1f}%)" if tvl_chg is not None else ""))
    # ---- attention (15) ----
    c = comps["attention"] = Component("attention", 15)
    c.add(6, lin(catalyst_hits, 0, 12), "catalyst events naming the chain in the last 7d (0..12)")
    c.add(5, lin(xnet_share, 0.0, 0.4), "share of GeckoTerminal cross-network trending pools (0..40%)")
    pc = profile_counts.get(cfg["ds_chain"], 0); bc = boost_counts.get(cfg["ds_chain"], 0)
    c.add(4, lin(pc + bc, 0, 25), "DEX Screener new profiles + boosted tokens on chain (0..25)")
    c.fact(f"attention: {catalyst_hits} catalyst event(s) name the chain (7d); {(xnet_share or 0) * 100:.0f}% of cross-network trending pools; {pc} new DS profiles, {bc} boosts. Catalyst feeds skew toward Solana coverage until the multi-chain news queries have run for a week; read the catalyst part as biased.")
    # ---- opportunity quality (15) ----
    c = comps["opportunity_quality"] = Component("opportunity_quality", 15)
    quality = [p for p in tr if _is_meme_pool(p) and (p.get("reserve") or 0) >= 100_000 and 0.3 <= (ratio((p.get("vol") or {}).get("h24"), p.get("reserve")) or 0) <= 10 and (((p.get("tx") or {}).get("h24") or [0, 0, 0])[2] or 0) >= 200] if tr else None
    c.add(10, lin(len(quality), 0, 10) if quality is not None else None, "trending meme pools with >= $100k liquidity, sane vol/liq (0.3..10x) and >= 200 buyers (0..10)")
    rows = con.execute("SELECT COUNT(*) n FROM theses th JOIN tokens tk ON tk.mint=th.mint WHERE tk.chain=? AND th.created_at > ? AND th.score >= 60", (chain, t - 48 * 3600)).fetchone() if _has_col(con, "theses", "score") else None
    wl = con.execute("SELECT COUNT(*) n FROM watchlist w JOIN tokens tk ON tk.mint=w.mint WHERE tk.chain=?", (chain,)).fetchone()
    scored = rows["n"] if rows else None
    c.add(3, lin(scored, 0, 5) if scored is not None else None, "tokens on chain scoring >= 60 in the last 48h (0..5; reflects research history, not just the market)")
    c.add(2, lin(wl["n"], 0, 5), "watchlist entries on chain (0..5; reflects research history)")
    c.fact(f"opportunity quality: {len(quality) if quality is not None else 'UNKNOWN'} quality trending pools; {scored if scored is not None else 'UNKNOWN'} tokens scored >= 60 (48h); {wl['n']} watchlist entries")

    soi = round(sum(x.points for x in comps.values()), 1)
    coverage = sum(x.coverage * x.max for x in comps.values()) / 100
    return {"chain": chain, "soi": soi, "components": {k: v.to_dict() for k, v in comps.items()}, "coverage": round(coverage, 2),
            "snapshot": {"tvl_usd": tvl, "tvl_chg_7d_pct": tvl_chg, "dex_vol_24h": vol24, "dex_vol_7d_avg": avg7, "dex_vol_30d_avg": avg30, "dex_vol_chg_7d_pct": pct_change(vol24, avg7),
                         "stablecoin_mcap": stable, "stablecoin_chg_7d_pct": stable_chg},
            "meme": {"meme_mcap": meme_mcap, "meme_mcap_chg_24h_pct": meme_chg, "meme_vol_24h": meme_vol, "meme_count": len(mk) if mk else None, "meme_gainers_24h": gainers, "meme_losers_24h": losers,
                     "meme_share_of_trending": (len([p for p in tr if _is_meme_pool(p)]) / len(tr)) if tr else None, "boosted_tokens": bc, "new_profiles": pc},
            "dex": {"trending_pools": len(tr) if tr else None, "quality_pools": len(quality) if quality is not None else None}}


def _has_col(con, table: str, col: str) -> bool:
    return col in {r[1] for r in con.execute(f"PRAGMA table_info({table})")}


def compute(bodies: dict[str, Any], t: float | None = None, persist: bool = True) -> dict[str, Any]:
    t = t or time.time()
    out: dict[str, Any] = {"observed_at": t, "chains": {}, "statements": [], "alerts": []}
    with db.connect() as con:
        R.sync(con)
        # previous snapshots >= 6 days old for change computations; most recent score for trend
        prev_rows = {}
        for cid in R.CHAINS:
            r = con.execute("SELECT * FROM chain_snapshots WHERE chain_id=? AND observed_at <= ? ORDER BY observed_at DESC LIMIT 1", (cid, t - 6 * 86400)).fetchone()
            prev_rows[cid] = dict(r) if r else {}
        last_scores = {cid: [dict(r) for r in con.execute("SELECT * FROM chain_scores WHERE chain_id=? AND observed_at < ? ORDER BY observed_at DESC LIMIT 6", (cid, t - 3600))] for cid in R.CHAINS}
        # attention inputs
        xnet = []
        for k, v in bodies.items():
            if k.startswith("gt_xnet") and isinstance(v, dict):
                xnet += v.get("pools") or []
        xnet_counts: dict[str, int] = {}
        for p in xnet:
            xnet_counts[p.get("net")] = xnet_counts.get(p.get("net"), 0) + 1
        profiles = bodies.get("ds_profiles:latest") if isinstance(bodies.get("ds_profiles:latest"), list) else []
        pcounts: dict[str, int] = {}
        for p in profiles:
            pcounts[p.get("chainId")] = pcounts.get(p.get("chainId"), 0) + 1
        bcounts: dict[str, int] = {}
        for k, v in bodies.items():
            if k.startswith("ds_boosts") and isinstance(v, list):
                for p in v:
                    bcounts[p.get("chainId")] = bcounts.get(p.get("chainId"), 0) + 1
        for cid, cfg in R.CHAINS.items():
            rx = re.compile(r"\b(" + "|".join(re.escape(x) for x in {cfg["name"].lower(), cid, cfg["native_symbol"].lower()} if len(x) >= 3) + r")\b", re.I)
            hits = sum(1 for r in con.execute("SELECT title FROM catalyst_events WHERE discovered_at > ?", (t - 7 * 86400,)) if rx.search(r["title"] or ""))
            share = (xnet_counts.get(cfg["gt_network"], 0) / len(xnet)) if xnet else None
            sc = score_chain(cid, bodies, t, con, prev_rows, hits, share, pcounts, bcounts)
            hist = last_scores[cid]
            prev_soi = hist[0]["soi"] if hist else None
            delta = (sc["soi"] - prev_soi) if prev_soi is not None else None
            sc["prev_soi"] = prev_soi; sc["delta"] = delta
            sc["trend"] = "UNKNOWN" if delta is None else "RISING" if delta >= 5 else "FALLING" if delta <= -5 else "FLAT"
            sc["history"] = [h["soi"] for h in hist]
            out["chains"][cid] = sc
        # ---- allocation and statements ----
        ranked = sorted(out["chains"].values(), key=lambda s: -s["soi"])
        for i, s in enumerate(ranked):
            cid = s["chain"]; cfg = R.CHAINS[cid]
            row = con.execute("SELECT status, research_allocation FROM chains WHERE chain_id=?", (cid,)).fetchone()
            cur_alloc = row["research_allocation"] if row else None
            low_streak = sum(1 for h in s["history"][:2] if h < 30) + (1 if s["soi"] < 30 else 0)
            if s["soi"] >= 55 and s["coverage"] >= 0.6:
                alloc = "FULL"
            elif s["soi"] >= 40:
                alloc = "PARTIAL"
            else:
                alloc = "WATCHLIST"
            if cfg["tier"] == 1 and alloc == "WATCHLIST":
                alloc = "WATCHLIST"  # never NONE for Tier 1: existing watchlists keep refreshing
            status = row["status"] if row else cfg["status"]
            reason = None
            if low_streak >= 3 and cfg["tier"] == 1:
                status = "LOW-PRIORITY MONITORING"; reason = f"SOI below 30 for {low_streak} consecutive runs"
                out["alerts"].append({"kind": "DE_EMPHASIS", "subject": cid, "level": "INFO", "text": f"{cfg['name']} moved to LOW-PRIORITY MONITORING: {reason}. Watchlist tokens keep refreshing; discovery pauses."})
            elif cfg["tier"] == 1 and s["soi"] >= 40 and status == "LOW-PRIORITY MONITORING":
                status = "ACTIVE"; reason = f"SOI recovered to {s['soi']}"
                out["alerts"].append({"kind": "ROTATION", "subject": cid, "level": "INFO", "text": f"{cfg['name']} back to ACTIVE: {reason}"})
            if cfg["tier"] == 2 and s["soi"] >= 60 and s["coverage"] >= 0.6:
                lvl = "BUILD FULL" if s["soi"] >= 70 and len([h for h in s["history"][:2] if h >= 60]) >= 2 else "BUILD PARTIAL"
                out["alerts"].append({"kind": "ROTATION", "subject": cid, "level": lvl, "text": f"Tier-2 chain {cfg['name']} SOI {s['soi']} (coverage {s['coverage']:.0%}): consider {lvl} research allocation"})
            s["research_allocation"] = alloc; s["status"] = status; s["rank"] = i + 1
            if persist:
                con.execute("UPDATE chains SET research_allocation=?, status=?, status_reason=COALESCE(?, status_reason), updated_at=? WHERE chain_id=?", (alloc, status, reason, t, cid))
            # statement
            conf = confidence_from_coverage(s["coverage"]) if len(s["history"]) >= 1 else ("MODERATE" if s["coverage"] >= 0.75 else "LOW")
            comp_txt = ", ".join(f"{k.replace('_', ' ')} {v['points']}/{v['max']}" for k, v in s["components"].items())
            unk = [u for v in s["components"].values() for u in v["unknowns"]]
            fact = f"FACT: {cfg['name']} SOI {s['soi']} (rank {i + 1}; {comp_txt})" + (f"; previous {s['prev_soi']} ({s['delta']:+.1f})" if s["prev_soi"] is not None else "; first measurement")
            inf = {"RISING": "speculative activity is increasing on this chain", "FALLING": "speculative activity is cooling here", "FLAT": "no meaningful change in speculative activity", "UNKNOWN": "no previous score; direction cannot be inferred yet"}[s["trend"]]
            s["statement"] = f"{fact}. INFERENCE: {inf}; research allocation {alloc}. CONFIDENCE: {conf}" + (f" (unknown: {'; '.join(unk[:3])}{'...' if len(unk) > 3 else ''})" if unk else "") + "."
            out["statements"].append(s["statement"])
        # cross-chain rotation inference: needs divergence over >= 2 runs
        movers = [s for s in ranked if s["delta"] is not None]
        if len(movers) >= 2:
            up = max(movers, key=lambda s: s["delta"]); dn = min(movers, key=lambda s: s["delta"])
            if up["delta"] >= 5 and dn["delta"] <= -5:
                sustained = len(up["history"]) >= 2 and up["history"][0] > up["history"][1] and len(dn["history"]) >= 2 and dn["history"][0] < dn["history"][1]
                out["statements"].append(f"FACT: {R.CHAINS[up['chain']]['name']} SOI {up['delta']:+.1f} while {R.CHAINS[dn['chain']]['name']} {dn['delta']:+.1f}. INFERENCE: {'rotation from ' + R.CHAINS[dn['chain']]['name'] + ' toward ' + R.CHAINS[up['chain']]['name'] + ' is underway' if sustained else 'possible early rotation; one run of divergence is not a trend'}. CONFIDENCE: {'MODERATE' if sustained else 'LOW'}.")
                out["alerts"].append({"kind": "ROTATION", "subject": f"{dn['chain']}->{up['chain']}", "level": "INFO", "text": out["statements"][-1]})
        if persist:
            clear_at(con, t, {"chain_snapshots": "observed_at", "chain_dex_activity": "observed_at", "chain_meme_activity": "observed_at", "chain_flows": "observed_at", "chain_scores": "observed_at", "ecosystem_alerts": "alerted_at"})
            for cid, s in out["chains"].items():
                snap = s["snapshot"]
                db.insert(con, "chain_snapshots", {"chain_id": cid, "observed_at": t, "source": "defillama", **snap, "raw_json": json.dumps(s["dex"])})
                db.insert(con, "chain_dex_activity", {"chain_id": cid, "observed_at": t, "source": "geckoterminal", "trending_pools": s["dex"]["trending_pools"], "pools_over_100k_liq": s["dex"]["quality_pools"]})
                db.insert(con, "chain_meme_activity", {"chain_id": cid, "observed_at": t, "source": "coingecko+geckoterminal+dexscreener", **s["meme"]})
                db.insert(con, "chain_flows", {"chain_id": cid, "observed_at": t, "source": "defillama", "stablecoin_net_7d": snap.get("stablecoin_chg_7d_pct"), "tvl_net_7d": snap.get("tvl_chg_7d_pct"), "note": "percent changes vs the most recent snapshot at least 6 days old; bridge flows UNKNOWN (no source)"})
                comps = s["components"]
                db.insert(con, "chain_scores", {"chain_id": cid, "observed_at": t, "soi": s["soi"], **{k: comps[k]["points"] for k in comps}, "components_json": json.dumps(comps),
                          "unknown_json": json.dumps([u for v in comps.values() for u in v["unknowns"]]), "trend": s["trend"], "rotation_statement": s["statement"],
                          "confidence": confidence_from_coverage(s["coverage"]), "research_allocation": s["research_allocation"]})
            for a in out["alerts"]:
                db.insert(con, "ecosystem_alerts", {"alerted_at": t, **a})
    out["ranked"] = [s["chain"] for s in ranked]
    return out
