"""01_TOKEN_DISCOVERY: Stage 1 broad universe from several discovery feeds, with cheap pre-scoring.

Input: the discovery result bodies (gt_pools:*, jup_tok:*, ds_profiles:*, raw:rug_trending).
Output: ranked candidate list with "why_surfaced" reasons, before any structural checks.
Trending / top gainers / most mentions are INPUTS only. The pre-score favors combinations of
volume acceleration, rising unique buyers, holder growth, liquidity growth and organic share.
"""
from __future__ import annotations

from typing import Any

SOL = "So11111111111111111111111111111111111111112"
MAJOR_IGNORE = {SOL, "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "Es9vMGANM1E2EjMA4c6kQX8m3KdMMw2sCkChfR4ZF9",
                "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So", "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn", "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",
                "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm", "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
                "rndrizKT3MK1iimdxRdWabcF7Zg7AR5T4nud4EkHBof", "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3", "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
                "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL", "27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4", "cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij",
                "3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh", "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E", "2b1kV6DkPAnxd5ixfnxCpjxmKwqjjaYmCZfHsFu24GXo",
                "USD1ttGY1N17NEEHLmELoaybftRBUSErhqYiQzvEmuB", "Fw6HfsiMK7Qdt9JBGxtn4QmZzW8gKeNg7uZc6wVYSDFF"}


def _f(x):
    try:
        return float(x) if x is not None and x != "" else None
    except (TypeError, ValueError):
        return None


# Not memecoins: tokenized equities (xStocks issuer wallet), stablecoins / yield tokens, wrapped or liquid-staked assets.
EXCLUDED_DEVS = {"S7vYFFWH6BjJyEsdrPQpqpYTqLTrPRK6KW3VwsJuRaS": "xStocks tokenized equity issuer"}
EXCLUDED_SYMBOLS = {"JUPUSD": "stablecoin", "CASH": "stablecoin", "SUSDAI": "yield-bearing stable", "USDC": "stablecoin", "USDT": "stablecoin", "USD1": "stablecoin",
                    "WNEAR": "wrapped asset", "XSOL": "liquid-staked SOL", "XORCA": "staked ORCA", "ZEC": "wrapped/bridged asset", "XMR": "wrapped/bridged asset",
                    "TOPENAI": "tokenized pre-IPO claim", "MET": "protocol governance token", "KMNO": "protocol governance token", "BP": "exchange/project token"}


def category_exclusion(symbol: str | None, dev: str | None, signals: dict | None = None) -> str | None:
    if dev in EXCLUDED_DEVS:
        return EXCLUDED_DEVS[dev]
    if symbol and symbol.upper() in EXCLUDED_SYMBOLS:
        return EXCLUDED_SYMBOLS[symbol.upper()]
    s = signals or {}
    chg = [abs(x) for x in (s.get("j_chg_24h"), s.get("j_chg_6h")) if isinstance(x, (int, float))]
    if chg and max(chg) < 0.05 and (s.get("j_vol_24h") or 0) > 1e6:
        return "price pinned near zero change on heavy volume (stable/wrapped behaviour)"
    return None


def _ratio(a, b):
    a, b = _f(a), _f(b)
    if a is None or not b:
        return None
    return a / b


def discover(bodies: dict[str, Any], min_liquidity: float = 20_000, min_vol_24h: float = 50_000,
             min_age_hours: float = 2.0, max_candidates: int = 60) -> dict[str, Any]:
    cands: dict[str, dict[str, Any]] = {}
    # pre-merged rows from the in-browser screen (memelab/bridge/screen.js)
    rest_rows = []
    if isinstance(bodies.get("merged"), list):
        for row in bodies["merged"]:
            cands[row["mint"]] = {"mint": row["mint"], "symbol": row.get("symbol"), "name": row.get("name"), "why": row.get("why") or [], "feeds": set(row.get("feeds") or []),
                                  "signals": row.get("signals") or {}, "pre_score": row.get("pre_score") or 0.0, "reject": [], "age_hours": row.get("age_hours"),
                                  "liquidity_est": row.get("liquidity_est"), "vol_24h_est": row.get("vol_24h_est")}
        for r in bodies.get("rest") or []:  # [mint, symbol, pre_score, liq, vol, age_hours]
            rest_rows.append({"mint": r[0], "symbol": r[1], "reject": [f"below browser pre-score cut (pre_score {r[2]})"], "why": [], "feeds": [], "signals": {}, "pre_score": r[2], "liquidity_est": r[3], "vol_24h_est": r[4], "age_hours": r[5]})
        bodies = {k: v for k, v in bodies.items() if k not in ("merged", "rest")}

    def cand(mint: str) -> dict[str, Any]:
        if mint not in cands:
            cands[mint] = {"mint": mint, "symbol": None, "name": None, "why": [], "feeds": set(), "signals": {}, "pre_score": 0.0, "reject": []}
        return cands[mint]

    # GeckoTerminal pool feeds
    for key, body in bodies.items():
        if not key.startswith("gt_pools") or not isinstance(body, dict):
            continue
        feed = key.split(":")[1]
        for p in body.get("pools") or []:
            base, quote = p.get("base"), p.get("quote")
            if not base or base in MAJOR_IGNORE:
                # pools where the memecoin is the quote side are rare; skip majors
                continue
            if quote not in MAJOR_IGNORE:
                continue  # need a SOL/stable quote for executable analysis
            c = cand(base)
            c["feeds"].add(f"gt:{feed}")
            s = c["signals"]
            s.setdefault("gt_reserve", p.get("reserve"))
            s["gt_reserve"] = max(s.get("gt_reserve") or 0, p.get("reserve") or 0)
            vol, tx, chg = p.get("vol") or {}, p.get("tx") or {}, p.get("chg") or {}
            s["vol_24h"] = (s.get("vol_24h") or 0) + (vol.get("h24") or 0)
            s["vol_1h"] = (s.get("vol_1h") or 0) + (vol.get("h1") or 0)
            s["vol_6h"] = (s.get("vol_6h") or 0) + (vol.get("h6") or 0)
            if tx.get("h24"):
                s["buyers_24h"] = (s.get("buyers_24h") or 0) + (tx["h24"][2] or 0)
                s["sellers_24h"] = (s.get("sellers_24h") or 0) + (tx["h24"][3] or 0)
            if tx.get("h1"):
                s["buyers_1h"] = (s.get("buyers_1h") or 0) + (tx["h1"][2] or 0)
                s["sellers_1h"] = (s.get("sellers_1h") or 0) + (tx["h1"][3] or 0)
            s.setdefault("chg", chg); s.setdefault("fdv", p.get("fdv")); s.setdefault("mcap", p.get("mcap"))
            s.setdefault("created", p.get("created")); s.setdefault("name", p.get("name"))
            c["name"] = c["name"] or (p.get("name") or "").split(" / ")[0]
            c["symbol"] = c["symbol"] or c["name"]

    # Jupiter token feeds (compact jup_disc rows from the collector, or full jup_tok rows)
    def setv(s, k, v):
        if v is not None:
            s[k] = v
    for key, body in bodies.items():
        if not key.startswith(("jup_disc", "jup_tok")) or not isinstance(body, list):
            continue
        feed = key.split(":", 1)[1]
        for t in body:
            m = t.get("id")
            if not m or m in MAJOR_IGNORE:
                continue
            c = cand(m)
            c["feeds"].add(f"jup:{feed}")
            c["symbol"] = t.get("symbol") or c["symbol"]; c["name"] = t.get("name") or c["name"]
            if t.get("_dup"):
                continue
            s = c["signals"]
            compact = "liq" in t or "s24h" in t
            if compact:
                setv(s, "jup_liq", _f(t.get("liq"))); setv(s, "mcap", _f(t.get("mcap"))); setv(s, "fdv", _f(t.get("fdv")))
                setv(s, "holders", t.get("holders")); setv(s, "organic_score", _f(t.get("org"))); setv(s, "organic_label", t.get("orgL"))
                setv(s, "launchpad", t.get("lp")); setv(s, "first_pool_at", t.get("fp")); setv(s, "dev", t.get("dev"))
                au = t.get("audit") or {}
                setv(s, "mint_disabled", au.get("m")); setv(s, "freeze_disabled", au.get("f")); setv(s, "top_holders_pct", _f(au.get("th"))); setv(s, "dev_pct", _f(au.get("dv")))
                for w in ("1h", "6h", "24h"):
                    st = t.get(f"s{w}") or {}
                    if st:
                        setv(s, f"j_vol_{w}", _f(st.get("v"))); setv(s, f"j_org_{w}", _f(st.get("o"))); setv(s, f"j_netbuyers_{w}", st.get("nb")); setv(s, f"j_traders_{w}", st.get("tr"))
                        setv(s, f"j_holderchg_{w}", _f(st.get("hc"))); setv(s, f"j_liqchg_{w}", _f(st.get("lc"))); setv(s, f"j_chg_{w}", _f(st.get("pc")))
            else:
                setv(s, "jup_liq", _f(t.get("liquidity"))); setv(s, "mcap", _f(t.get("mcap"))); setv(s, "fdv", _f(t.get("fdv")))
                setv(s, "holders", t.get("holderCount")); setv(s, "organic_score", _f(t.get("organicScore"))); setv(s, "organic_label", t.get("organicScoreLabel"))
                setv(s, "launchpad", t.get("launchpad")); setv(s, "first_pool_at", (t.get("firstPool") or {}).get("createdAt")); setv(s, "dev", t.get("dev"))
                au = t.get("audit") or {}
                setv(s, "mint_disabled", au.get("mintAuthorityDisabled")); setv(s, "freeze_disabled", au.get("freezeAuthorityDisabled"))
                setv(s, "top_holders_pct", _f(au.get("topHoldersPercentage"))); setv(s, "dev_pct", _f(au.get("devBalancePercentage")))
                for w in ("5m", "1h", "6h", "24h"):
                    st = t.get(f"stats{w}") or {}
                    if st:
                        s[f"j_vol_{w}"] = (_f(st.get("buyVolume")) or 0) + (_f(st.get("sellVolume")) or 0)
                        s[f"j_org_{w}"] = (_f(st.get("buyOrganicVolume")) or 0) + (_f(st.get("sellOrganicVolume")) or 0)
                        setv(s, f"j_netbuyers_{w}", st.get("numNetBuyers")); setv(s, f"j_traders_{w}", st.get("numTraders"))
                        setv(s, f"j_holderchg_{w}", _f(st.get("holderChange"))); setv(s, f"j_liqchg_{w}", _f(st.get("liquidityChange"))); setv(s, f"j_chg_{w}", _f(st.get("priceChange")))

    # DexScreener profiles/boosts: attention inputs (paid), only as a flag
    for key, body in bodies.items():
        if key.startswith("ds_profiles") and isinstance(body, list):
            for p in body:
                if p.get("chainId") != "solana" or not p.get("tokenAddress"):
                    continue
                c = cand(p["tokenAddress"])
                c["feeds"].add("ds:boost" if "boosts" in key else "ds:profile")
                c["signals"]["ds_boost_amount"] = _f(p.get("totalAmount") or p.get("amount"))
    rt = bodies.get("raw:rug_trending")
    if isinstance(rt, list):
        for t in rt:
            m = t.get("mint") if isinstance(t, dict) else None
            if m and m not in MAJOR_IGNORE:
                cand(m)["feeds"].add("rug:trending")

    # ---- cheap pre-screen and pre-score ----
    out = []
    for m, c in cands.items():
        s = c["signals"]
        excl = category_exclusion(c.get("symbol"), s.get("dev"), s)
        if excl:
            c["reject"].append(f"not a memecoin: {excl}")
        if c.get("pre_score") and c.get("why"):
            # already pre-scored in the browser (screen.js); keep its score and reasons
            c["liquidity_est"] = c.get("liquidity_est") or max(_f(s.get("jup_liq")) or 0, _f(s.get("gt_reserve")) or 0)
            c["vol_24h_est"] = c.get("vol_24h_est") or max(_f(s.get("vol_24h")) or 0, _f(s.get("j_vol_24h")) or 0)
            c["feeds"] = sorted(c["feeds"]) if isinstance(c["feeds"], set) else c["feeds"]
            out.append(c)
            continue
        liq = max(_f(s.get("jup_liq")) or 0, _f(s.get("gt_reserve")) or 0)
        vol24 = max(_f(s.get("vol_24h")) or 0, _f(s.get("j_vol_24h")) or 0)
        if liq and liq < min_liquidity:
            c["reject"].append(f"liquidity ${liq:,.0f} < ${min_liquidity:,.0f}")
        if vol24 and vol24 < min_vol_24h:
            c["reject"].append(f"24h volume ${vol24:,.0f} < ${min_vol_24h:,.0f}")
        if not liq and not vol24:
            c["reject"].append("no liquidity or volume data in discovery feeds")
        if s.get("mint_disabled") is False:
            c["reject"].append("mint authority active (jupiter audit)")
        if s.get("freeze_disabled") is False:
            c["reject"].append("freeze authority active (jupiter audit)")
        # pre-score components (each 0..1)
        comps = {}
        v1, v6, v24 = _f(s.get("j_vol_1h")) or _f(s.get("vol_1h")), _f(s.get("j_vol_6h")) or _f(s.get("vol_6h")), vol24
        acc = None
        if v24 and v6 is not None:
            acc = (v6 * 4) / v24  # >1 means last 6h running hotter than the 24h average
        if acc is not None:
            comps["volume_acceleration"] = min(max((acc - 0.6) / 1.4, 0), 1)
            c["why"].append(f"6h volume pace {acc:.2f}x the 24h average")
        nb = s.get("j_netbuyers_24h")
        tr = s.get("j_traders_24h")
        if nb is not None and tr:
            comps["net_buyers"] = min(max(nb / max(tr, 1) + 0.2, 0) / 0.6, 1)
            c["why"].append(f"net buyers 24h {nb:+d} of {tr} traders")
        hc = s.get("j_holderchg_24h")
        if hc is not None:
            comps["holder_growth"] = min(max((hc + 2) / 12, 0), 1)
            c["why"].append(f"holder change 24h {hc:+.1f}%")
        lc = s.get("j_liqchg_24h")
        if lc is not None:
            comps["liquidity_growth"] = min(max((lc + 10) / 40, 0), 1)
            if abs(lc) > 5:
                c["why"].append(f"liquidity change 24h {lc:+.1f}%")
        if s.get("j_vol_24h") and s.get("j_org_24h") is not None:
            org = s["j_org_24h"] / max(s["j_vol_24h"], 1)
            comps["organic_share"] = min(org / 0.3, 1)
            c["why"].append(f"organic volume share {org:.0%}")
        if s.get("organic_score") is not None:
            comps["organic_score"] = min(s["organic_score"] / 80, 1)
        if liq and vol24:
            turnover = vol24 / liq
            comps["turnover_sane"] = 1.0 if 0.5 <= turnover <= 15 else 0.3
            if turnover > 15:
                c["why"].append(f"24h volume is {turnover:.0f}x liquidity (possible wash/circular volume)")
        chg24 = _f(s.get("j_chg_24h")) or _f((s.get("chg") or {}).get("h24"))
        if chg24 is not None:
            comps["not_parabolic"] = 1.0 if chg24 < 150 else 0.4 if chg24 < 400 else 0.1
            if chg24 > 150:
                c["why"].append(f"up {chg24:.0f}% in 24h (chase risk)")
        feeds = len(c["feeds"])
        comps["multi_feed"] = min(feeds / 3, 1)
        c["why"].insert(0, "surfaced on " + ", ".join(sorted(c["feeds"])))
        c["pre_score"] = round(100 * sum(comps.values()) / max(len(comps), 1), 1) if comps else 0.0
        c["pre_components"] = comps
        c["liquidity_est"] = liq; c["vol_24h_est"] = vol24
        c["feeds"] = sorted(c["feeds"])
        out.append(c)
    out.sort(key=lambda c: (len(c["reject"]) == 0, c["pre_score"]), reverse=True)
    survivors = [c for c in out if not c["reject"]][:max_candidates]
    pre_rej = bodies.get("stage1_rejected") or []
    universe = (bodies.get("_screen") or {}).get("universe") or len(out)
    return {"universe_size": universe, "survivors": survivors, "rejected_stage1": [c for c in out if c["reject"]] + rest_rows + [{"mint": r[0], "symbol": r[1], "reject": [r[2]], "why": [], "feeds": [], "signals": {}} for r in pre_rej],
            "facts": [f"{len(out)} distinct Solana mints surfaced across discovery feeds", f"{len(survivors)} passed stage-1 cheap screen"],
            "inferences": [], "heuristics": ["pre_score is a screening aid only; it averages volume acceleration, net buyers, holder growth, liquidity growth, organic share, turnover sanity and multi-feed presence"],
            "unknowns": []}
