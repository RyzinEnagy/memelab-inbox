"""Emerging Chain Detector + launchpad monitoring + benchmark baskets + cross-chain relative strength.

Emerging: a chain outside the registry's active set that shows up in GeckoTerminal cross-network trending, or whose DefiLlama TVL
is material and growing. Levels: MONITOR (seen), BUILD PARTIAL (repeated presence or TVL growth), BUILD FULL (sustained over 3 runs).
Nothing here adds a chain to the research set automatically; it writes an alert and a MONITOR record a human (or the next run) acts on.
"""
from __future__ import annotations

import json
import time
from typing import Any

from .. import db
from . import registry as R
from ._util import clear_at, median, pct_change

LAUNCHPAD_DEX_RX = {"pump.fun": ("pump-fun", "pumpswap"), "letsbonk": ("launchlab", "raydium-launchlab", "bonk"), "moonshot": ("moonshot",), "believe": ("meteora-dbc", "dbc"),
                    "boop": ("boop",), "four.meme": ("four-meme", "fourmeme"), "zora": ("zora",), "clanker": ("clanker",), "virtuals": ("virtuals",), "flaunch": ("flaunch",), "arena": ("arena",)}
KNOWN_LLAMA = {v["llama"].lower() for v in R.CHAINS.values()}
KNOWN_GT = {v["gt_network"] for v in R.CHAINS.values()}


def detect(bodies: dict[str, Any], t: float | None = None, persist: bool = True) -> dict[str, Any]:
    t = t or time.time()
    out: dict[str, Any] = {"observed_at": t, "candidates": [], "alerts": []}
    xnet = []
    for k, v in bodies.items():
        if k.startswith("gt_xnet") and isinstance(v, dict):
            xnet += v.get("pools") or []
    net_names = {}
    for k, v in bodies.items():
        if k.startswith("gt_xnet") and isinstance(v, dict):
            for nid, nm in v.get("networks") or []:
                net_names[nid] = nm
    for nid, nm in (bodies.get("gt_nets") or []):
        net_names.setdefault(nid, nm)
    counts: dict[str, int] = {}
    for p in xnet:
        counts[p.get("net")] = counts.get(p.get("net"), 0) + 1
    tvls = {x[0]: x[1] for x in (bodies.get("llama_chains") or []) if isinstance(x, list) and len(x) >= 2}
    stables = {x[0]: x[1] for x in (bodies.get("llama_stables") or []) if isinstance(x, list) and len(x) == 2}
    with db.connect() as con:
        if persist:
            con.execute("DELETE FROM ecosystem_alerts WHERE alerted_at=? AND kind='EMERGING_CHAIN'", (t,))
            con.execute("DELETE FROM chain_snapshots WHERE observed_at=? AND chain_id NOT IN (SELECT chain_id FROM chains WHERE tier IN (1,2))", (t,))
        cand: dict[str, dict] = {}
        for net, n in counts.items():
            if not net or net in KNOWN_GT:
                continue
            cand[net] = {"id": net, "name": net_names.get(net, net), "trending_pools": n, "trending_share": n / len(xnet) if xnet else None, "tvl": None, "signals": [f"{n} of {len(xnet)} cross-network trending pools"]}
        for name, tvl in tvls.items():
            if (tvl or 0) < 2e7 or name.lower() in KNOWN_LLAMA:
                continue
            nl = name.lower()
            key = next((k for k, c in cand.items() if c["name"].lower() == nl or nl.startswith(c["name"].lower()) or c["name"].lower().startswith(nl)), None) or nl.replace(" ", "-")
            c = cand.setdefault(key, {"id": key, "name": name, "trending_pools": 0, "trending_share": 0.0, "tvl": None, "signals": []})
            c["tvl"] = tvl; c["stables"] = stables.get(name)
            prev = con.execute("SELECT tvl_usd FROM chain_snapshots WHERE chain_id=? AND observed_at <= ? ORDER BY observed_at DESC LIMIT 1", (key, t - 6 * 86400)).fetchone()
            c["tvl_chg_7d"] = pct_change(tvl, prev["tvl_usd"]) if prev else None
            c["signals"].append(f"TVL ${tvl / 1e6:,.0f}M" + (f" ({c['tvl_chg_7d']:+.1f}% vs ~7d)" if c["tvl_chg_7d"] is not None else " (7d change UNKNOWN until a 6-day-old snapshot exists)"))
        for key, c in cand.items():
            hist = [dict(r) for r in con.execute("SELECT level FROM ecosystem_alerts WHERE kind='EMERGING_CHAIN' AND subject=? AND alerted_at < ? ORDER BY alerted_at DESC LIMIT 3", (key, t - 3600))]
            strong = (c["trending_pools"] >= 6) or ((c.get("tvl_chg_7d") or 0) >= 25 and c["trending_pools"] >= 2)
            weak = c["trending_pools"] >= 2 or (c.get("tvl") or 0) >= 2e8
            if not weak and not strong:
                continue
            level = "BUILD FULL" if strong and len(hist) >= 2 and all(h["level"] in ("BUILD PARTIAL", "BUILD FULL") for h in hist[:2]) else "BUILD PARTIAL" if strong else "MONITOR"
            c["level"] = level
            text = f"Emerging chain {c['name']}: {'; '.join(c['signals'])}. Level {level}." + (" Only market-level data is readable for it (no contract-risk or router adapter); tokens there stay RESEARCH REQUIRED." if level != "MONITOR" else "")
            out["candidates"].append(c)
            out["alerts"].append({"kind": "EMERGING_CHAIN", "subject": key, "level": level, "text": text, "evidence_json": json.dumps({k: v for k, v in c.items() if k != "signals"})})
            if persist:
                if not con.execute("SELECT 1 FROM chains WHERE chain_id=?", (key,)).fetchone():
                    con.execute("INSERT INTO chains (chain_id, name, tier, family, gt_network, llama_slug, status, status_reason, research_allocation, first_seen_at, updated_at, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                (key, c["name"], 3, "other", key if key in counts else None, c["name"], "EMERGING", text[:200], "NONE", t, t, "partial record from the emerging-chain detector"))
                db.insert(con, "chain_snapshots", {"chain_id": key, "observed_at": t, "source": "defillama+geckoterminal", "tvl_usd": c.get("tvl"), "tvl_chg_7d_pct": c.get("tvl_chg_7d"), "stablecoin_mcap": c.get("stables"), "raw_json": json.dumps(c["signals"])})
        if persist:
            for a in out["alerts"]:
                db.insert(con, "ecosystem_alerts", {"alerted_at": t, **a})
    out["candidates"].sort(key=lambda c: (-c["trending_pools"], -(c.get("tvl") or 0)))
    return out


def launchpads(bodies: dict[str, Any], t: float | None = None, persist: bool = True) -> dict[str, Any]:
    """Launchpad activity read from pool dex ids on each network's new/trending pools (coverage is partial: Clanker and four.meme
    pools trade on Uniswap/Pancake and are not distinguishable by dex id, so their rows stay UNKNOWN rather than zero)."""
    t = t or time.time()
    out: dict[str, Any] = {"observed_at": t, "rows": []}
    with db.connect() as con:
        if persist:
            clear_at(con, t, {"launchpad_snapshots": "observed_at"})
        for cid, cfg in R.CHAINS.items():
            net = cfg["gt_network"]
            pools = []
            for k, v in bodies.items():
                if k.startswith(f"gt_pools:{net}:") and isinstance(v, dict):
                    pools += [(k.split(":")[2], p) for p in v.get("pools") or []]
            for lp in cfg.get("launchpads") or []:
                pats = LAUNCHPAD_DEX_RX.get(lp, (lp.replace(".", "-"),))
                mine = [(kind, p) for kind, p in pools if any(pt in (p.get("dex") or "").lower() for pt in pats)]
                detectable = lp not in ("clanker", "four.meme", "virtuals", "flaunch", "arena", "flap")
                row = {"launchpad_id": f"{cid}:{lp}", "chain_id": cid, "name": lp, "detectable": detectable,
                       "new_pools_sample": sum(1 for kind, _ in mine if kind.startswith("new")) if detectable else None,
                       "pools_in_trending": sum(1 for kind, _ in mine if kind.startswith("trending") or kind.startswith("top")) if detectable else None,
                       "sample_vol_24h": sum((p.get("vol") or {}).get("h24") or 0 for _, p in mine) if detectable and mine else None,
                       "sample_liq": sum(p.get("reserve") or 0 for _, p in mine) if detectable and mine else None}
                out["rows"].append(row)
                if persist:
                    if not con.execute("SELECT 1 FROM launchpads WHERE launchpad_id=?", (row["launchpad_id"],)).fetchone():
                        db.insert(con, "launchpads", {"launchpad_id": row["launchpad_id"], "chain_id": cid, "name": lp, "dex_ids_json": json.dumps(list(pats)), "first_seen_at": t,
                                  "notes": None if detectable else "pools trade on a general DEX; not identifiable from pool data alone"})
                    db.insert(con, "launchpad_snapshots", {"launchpad_id": row["launchpad_id"], "observed_at": t, "source": "geckoterminal", "new_pools_sample": row["new_pools_sample"],
                              "pools_in_trending": row["pools_in_trending"], "sample_vol_24h": row["sample_vol_24h"], "sample_liq": row["sample_liq"]})
    return out


BUCKETS = (("MICRO", 0, 5e7), ("SMALL", 5e7, 3e8), ("MID", 3e8, 2e9), ("LARGE", 2e9, 1e15))


def benchmark_baskets(bodies: dict[str, Any], t: float | None = None, persist: bool = True) -> dict[str, Any]:
    """Dynamic meme benchmark basket per cap bucket from the CoinGecko meme-token category (top 100 by market cap)."""
    t = t or time.time()
    memes = bodies.get("cg_mkts:meme-token:1") if isinstance(bodies.get("cg_mkts:meme-token:1"), list) else []
    out: dict[str, Any] = {"observed_at": t, "buckets": {}, "all": memes}
    with db.connect() as con:
        if persist:
            clear_at(con, t, {"benchmark_baskets": "observed_at"})
        for name, lo, hi in BUCKETS:
            mem = [m for m in memes if lo <= (m.get("market_cap") or 0) < hi]
            row = {"members": [(m.get("symbol") or "").upper() for m in mem], "n": len(mem), "median_chg_24h": median(m.get("price_change_percentage_24h") for m in mem), "median_chg_7d": median(m.get("p7d") for m in mem)}
            out["buckets"][name] = row
            if persist and mem:
                db.insert(con, "benchmark_baskets", {"observed_at": t, "bucket": name, "members_json": json.dumps(row["members"]), "median_chg_24h": row["median_chg_24h"], "median_chg_7d": row["median_chg_7d"], "n": row["n"]})
    return out


def bucket_for(mcap: float | None) -> str | None:
    if mcap is None:
        return None
    return next((n for n, lo, hi in BUCKETS if lo <= mcap < hi), None)


def cross_chain_rs(con, t: float, tokens: list[dict], bodies: dict[str, Any], persist: bool = True) -> list[dict]:
    """tokens: [{chain, mint, symbol, chg_24h, mcap}]. RS vs the chain's meme median, the global basket median (same cap bucket) and the native coin."""
    memes = bodies.get("cg_mkts:meme-token:1") if isinstance(bodies.get("cg_mkts:meme-token:1"), list) else []
    price = bodies.get("cg_price") if isinstance(bodies.get("cg_price"), dict) else {}
    rows = []
    for tk in tokens:
        cfg = R.CHAINS.get(tk["chain"], {})
        cat = cfg.get("cg_meme_category")
        chain_memes = bodies.get(f"cg_mkts:{cat}:1") if cat and isinstance(bodies.get(f"cg_mkts:{cat}:1"), list) else []
        chain_med = median(m.get("price_change_percentage_24h") for m in chain_memes)
        bucket = bucket_for(tk.get("mcap"))
        glob = [m for m in memes if bucket_for(m.get("market_cap")) == bucket] if bucket else memes
        glob_med = median(m.get("price_change_percentage_24h") for m in glob)
        nat = ((price.get(cfg.get("cg_native")) or {}).get("usd_24h_change")) if cfg else None
        c = tk.get("chg_24h")
        row = {"observed_at": t, "chain_id": tk["chain"], "mint": tk["mint"], "symbol": tk.get("symbol"), "chg_24h": c, "chain_meme_median_24h": chain_med, "global_meme_median_24h": glob_med, "native_chg_24h": nat,
               "rs_vs_chain": (c - chain_med) if c is not None and chain_med is not None else None, "rs_vs_global": (c - glob_med) if c is not None and glob_med is not None else None,
               "rs_vs_native": (c - nat) if c is not None and nat is not None else None, "note": f"global basket = {bucket or 'all'} cap bucket (n={len(glob)})" + ("; chain meme median UNKNOWN (no category)" if chain_med is None else "")}
        rows.append(row)
    rows.sort(key=lambda r: -(r["rs_vs_global"] if r["rs_vs_global"] is not None else -999))
    for i, r in enumerate(rows):
        r["rank_global"] = i + 1
        if persist:
            db.insert(con, "cross_chain_relative_strength", r)
    return rows
