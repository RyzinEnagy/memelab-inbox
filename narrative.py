"""Layer 2: NARRATIVE_ROTATION_ENGINE.

Narratives come from three places and are never hard-coded as a fixed list:
  1. CoinGecko categories whose name matches a speculative-theme pattern (dynamic membership, market cap and volume).
  2. Keyword clusters: a word that appears in the names of >= 3 distinct tokens across the trending pools and meme markets of all chains.
  3. Catalyst events: counted per narrative by keyword match (last 7 days).
Lifecycle labels (EMERGING / ACCELERATING / MATURE / MANIA / EXHAUSTING / DEAD) need history; without it the label is UNKNOWN with a reason.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from .. import db
from . import registry as R
from ._util import clear_at, median, pct_change, ratio

THEME_RX = re.compile(r"meme|pump|bonk|launchlab|clanker|zora|virtuals|believe|moonshot|ai-agent|ai agent|politifi|celebrit|animal|\bdog\b|\bcat\b|frog|pepe|culture|parody|tiktok|sports|elon|trump|country|mascot|cult\b|degen|fan token", re.I)
EXCLUDE_RX = re.compile(r"stock|securit|rwa|treasur|fund\b|bond|etf|real world|yield|lending|bridged|wrapped|liquid staking|restak|perpetual|exchange-based|centralized", re.I)
STOP = {"the", "coin", "token", "inu", "of", "on", "and", "by", "to", "in", "a", "an", "is", "for", "with", "weth", "usdc", "usdt", "sol", "eth", "bnb", "wbnb", "base", "bsc", "v2", "v3", "v4", "dao", "finance", "protocol", "network", "chain", "wrapped", "official", "cto", "2", "20", "69", "420", "x", "ai"}
GENERIC_CATS = {"meme-token", "solana-meme-coins", "base-meme-coins", "bnb-chain-meme-coins", "ethereum-meme-coins", "sui-meme", "avalanche-meme"}


def _words(name: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z0-9]{2,}", (name or "").lower()) if w not in STOP}


def compute(bodies: dict[str, Any], t: float | None = None, persist: bool = True, max_keywords: int = 12) -> dict[str, Any]:
    t = t or time.time()
    out: dict[str, Any] = {"observed_at": t, "narratives": [], "keywords": []}
    cats = bodies.get("cg_cat") if isinstance(bodies.get("cg_cat"), list) else []
    themed = [c for c in cats if (THEME_RX.search(c.get("name") or "") or THEME_RX.search(c.get("id") or "")) and not EXCLUDE_RX.search(c.get("name") or "") and (c.get("market_cap") or 0) >= 2e7]
    # token name universe across chains (trending pools + meme markets)
    names: list[tuple[str, str, str, str]] = []  # (word-source name, chain, mint, symbol)
    for k, v in bodies.items():
        if k.startswith("gt_pools:") and isinstance(v, dict):
            net = k.split(":")[1]; chain = R.by_gt_network(net) or net
            for p in v.get("pools") or []:
                nm = (p.get("name") or "").split("/")[0].strip()
                names.append((nm, chain, p.get("base"), nm.upper()))
        if k.startswith("gt_xnet") and isinstance(v, dict):
            for p in v.get("pools") or []:
                nm = (p.get("name") or "").split("/")[0].strip()
                names.append((nm, R.by_gt_network(p.get("net") or "") or p.get("net"), p.get("base"), nm.upper()))
        if k.startswith("cg_mkts:") and isinstance(v, list):
            for m in v:
                names.append((m.get("name") or "", "cg-top100", m.get("id"), (m.get("symbol") or "").upper()))
    seen_tokens = set(); word_hits: dict[str, list[tuple]] = {}
    for nm, chain, mint, sym in names:
        key = (chain, mint)
        if key in seen_tokens or not mint:
            continue
        seen_tokens.add(key)
        for w in _words(nm):
            word_hits.setdefault(w, []).append((chain, mint, sym))
    keywords = sorted(((w, hs) for w, hs in word_hits.items() if len({h[1] for h in hs}) >= 3), key=lambda x: -len(x[1]))[:max_keywords]
    with db.connect() as con:
        ev_titles = [r["title"] or "" for r in con.execute("SELECT title FROM catalyst_events WHERE discovered_at > ?", (t - 7 * 86400,))]

        GENERIC = {"meme", "memes", "coin", "coins", "token", "tokens", "ecosystem", "themed", "inspired", "affiliated", "protocol", "launchpad", "agent", "agents"}

        def catalyst_hits(words: list[str]) -> int | None:
            specific = [w for w in words if len(w) >= 3 and w not in GENERIC]
            if not specific:
                return None  # a generic word like "meme" would match most of the feed; that is not evidence for this narrative
            rx = re.compile(r"\b(" + "|".join(re.escape(w) for w in specific) + r")\b", re.I)
            return sum(1 for s in ev_titles if rx.search(s))

        def lifecycle(nid: str, mcap: float | None, chg24: float | None, vol: float | None) -> tuple[str, str]:
            hist = [dict(r) for r in con.execute("SELECT observed_at, mcap, vol_24h, mcap_chg_24h_pct FROM narrative_snapshots WHERE narrative_id=? AND observed_at < ? ORDER BY observed_at DESC LIMIT 40", (nid, t - 1800))]
            vm = ratio(vol, mcap)
            if mcap is None:
                return "UNKNOWN", "no market cap for this narrative (keyword cluster without CoinGecko category)"
            max14 = max([h["mcap"] for h in hist if h["mcap"] and t - h["observed_at"] <= 14 * 86400] + [mcap])
            max30 = max([h["mcap"] for h in hist if h["mcap"] and t - h["observed_at"] <= 30 * 86400] + [mcap])
            old7 = next((h["mcap"] for h in hist if h["mcap"] and t - h["observed_at"] >= 6 * 86400), None)
            chg7 = pct_change(mcap, old7)
            if mcap < 0.5 * max30 and len(hist) >= 3:
                return "DEAD", f"market cap {pct_change(mcap, max30):+.0f}% from its 30-day high"
            if mcap < 0.8 * max14 and len(hist) >= 3 and (chg24 or 0) < 5:
                return "EXHAUSTING", f"market cap {pct_change(mcap, max14):+.0f}% from its 14-day high; 24h {chg24:+.1f}%"
            if (chg24 or 0) >= 25 or (vm or 0) >= 1.0:
                return "MANIA", f"24h {chg24:+.1f}%; volume/mcap {vm:.2f}" if vm is not None else f"24h {chg24:+.1f}%"
            if (chg24 or 0) >= 8 and (chg7 is None or chg7 > 0):
                return "ACCELERATING", f"24h {chg24:+.1f}%" + (f", 7d {chg7:+.0f}%" if chg7 is not None else " (7d UNKNOWN)")
            if len(hist) < 3 and (chg24 or 0) > 3:
                return "EMERGING", f"first {len(hist) + 1} observation(s); 24h {chg24:+.1f}%"
            if mcap >= 5e9 and abs(chg24 or 0) < 5:
                return "MATURE", f"large (${mcap / 1e9:,.1f}B) and quiet (24h {chg24:+.1f}%)"
            if len(hist) < 3:
                return "UNKNOWN", f"only {len(hist) + 1} observation(s); lifecycle needs history"
            return "MATURE", f"no acceleration (24h {chg24:+.1f}%" + (f", 7d {chg7:+.0f}%" if chg7 is not None else "") + ")"

        rows = []
        for c in themed:
            nid = f"cg:{c['id']}"
            words = [w for w in _words(c.get("name") or "")]
            hits = catalyst_hits(words)
            lc, why = lifecycle(nid, c.get("market_cap"), c.get("market_cap_change_24h"), c.get("volume_24h"))
            rows.append({"narrative_id": nid, "name": c["name"], "source": "coingecko_category", "cg_category_id": c["id"], "keywords": words, "mcap": c.get("market_cap"), "mcap_chg_24h_pct": c.get("market_cap_change_24h"),
                         "vol_24h": c.get("volume_24h"), "top3": c.get("top_3_coins_id") or [], "catalyst_events_7d": hits, "lifecycle": lc, "lifecycle_reason": why, "generic": c["id"] in GENERIC_CATS})
        for w, hs in keywords:
            nid = f"kw:{w}"
            chains = sorted({h[0] for h in hs if h[0]})
            hits = catalyst_hits([w])
            lc, why = lifecycle(nid, None, None, None)
            rows.append({"narrative_id": nid, "name": f'"{w}" tokens', "source": "keyword", "cg_category_id": None, "keywords": [w], "mcap": None, "mcap_chg_24h_pct": None, "vol_24h": None,
                         "top3": [h[2] for h in hs[:3]], "catalyst_events_7d": hits, "lifecycle": lc, "lifecycle_reason": why, "token_count": len({h[1] for h in hs}), "chains": chains, "tokens": hs[:30]})
        rows.sort(key=lambda r: (-(r.get("mcap_chg_24h_pct") or -999) if r["source"] == "coingecko_category" else -(r.get("token_count") or 0)))
        out["narratives"] = rows
        if persist:
            clear_at(con, t, {"narrative_snapshots": "observed_at"})
            for r in rows:
                ex = con.execute("SELECT narrative_id FROM narratives WHERE narrative_id=?", (r["narrative_id"],)).fetchone()
                if ex:
                    con.execute("UPDATE narratives SET last_seen_at=?, lifecycle=?, lifecycle_reason=?, keywords_json=? WHERE narrative_id=?", (t, r["lifecycle"], r["lifecycle_reason"], json.dumps(r["keywords"]), r["narrative_id"]))
                else:
                    db.insert(con, "narratives", {"narrative_id": r["narrative_id"], "name": r["name"], "source": r["source"], "keywords_json": json.dumps(r["keywords"]), "cg_category_id": r.get("cg_category_id"),
                              "first_seen_at": t, "last_seen_at": t, "lifecycle": r["lifecycle"], "lifecycle_reason": r["lifecycle_reason"]})
                db.insert(con, "narrative_snapshots", {"narrative_id": r["narrative_id"], "observed_at": t, "source": r["source"], "mcap": r.get("mcap"), "mcap_chg_24h_pct": r.get("mcap_chg_24h_pct"), "vol_24h": r.get("vol_24h"),
                          "token_count": r.get("token_count"), "top3_json": json.dumps(r.get("top3")), "catalyst_events_7d": r["catalyst_events_7d"], "chains_json": json.dumps(r.get("chains") or []), "lifecycle": r["lifecycle"]})
                for h in r.get("tokens") or []:
                    chain, mint, sym = h
                    if not mint:
                        continue
                    con.execute("INSERT INTO narrative_tokens (narrative_id, chain_id, mint, symbol, basis, first_seen_at, last_seen_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT(narrative_id, mint) DO UPDATE SET last_seen_at=excluded.last_seen_at",
                                (r["narrative_id"], chain, mint, sym, "name keyword", t, t))
    out["keywords"] = [(w, len({h[1] for h in hs})) for w, hs in keywords]
    return out


def narrative_for_token(con, mint: str, name: str | None, symbol: str | None) -> str | None:
    """Best narrative id for a token: explicit narrative_tokens row, else a keyword narrative whose word is in the name."""
    r = con.execute("SELECT narrative_id FROM narrative_tokens WHERE mint=? ORDER BY last_seen_at DESC LIMIT 1", (mint,)).fetchone()
    if r:
        return r["narrative_id"]
    words = _words(f"{name or ''} {symbol or ''}")
    for w in words:
        r = con.execute("SELECT narrative_id FROM narratives WHERE narrative_id=?", (f"kw:{w}",)).fetchone()
        if r:
            return r["narrative_id"]
    return None
