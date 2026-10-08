"""Orchestration: discovery -> shortlist -> deep research -> scoring -> launch monitor -> hand-over.

The engine runs before the normal pipeline. Tokens younger than NEW_LAUNCH_HOURS, or without trading, are judged here; older tokens
with enough market history are handed to the full framework (watchlist status RESEARCH REQUIRED).
"""
from __future__ import annotations

import json
from typing import Any

from .. import db
from . import cohort, deployer, discover as D, monitor as MON, ranker, social, tokenomics, wallets

MAX_SHORTLIST = 14
TRACK_STATUSES = ("LAUNCH MONITOR", "HIGH-INTEREST WATCH", "WATCH", "RESEARCH INCOMPLETE")


def prices(bodies: dict) -> tuple[float | None, float | None]:
    cg = bodies.get("cg_price") or bodies.get("raw:cg_sol") or {}
    g = lambda k: (cg.get(k) or {}).get("usd") if isinstance(cg.get(k), dict) else None
    return g("solana"), g("ethereum")


def run_discovery(con, bodies: dict, t: float) -> dict[str, dict]:
    sol, eth = prices(bodies)
    cands = D.from_bodies(bodies, t, sol, eth)
    for c in D.from_catalyst(con, t):
        cands.setdefault(c["launch_id"], c)
    D.impersonation_check(con, cands)
    res = D.persist(con, cands, t)
    return {"cands": cands, "alerts": res["alerts"], "sol_price": sol, "eth_price": eth}


def prescore(c: dict, t: float) -> float:
    """Cheap ordering for the deep-research shortlist. Not a quality score: it only decides what gets the expensive reads first."""
    o, s = c.get("obs") or {}, c.get("signals") or {}
    if "NSFW" in (c.get("flags") or []) or (s.get("creator_launches_in_sample") or 0) >= 3:
        return -1
    age_h = (t - (c.get("created_at") or t)) / 3600
    trade_h = (t - (c.get("first_trade_at") or c.get("created_at") or t)) / 3600
    if c["state"] in "BCD" and age_h > D.NEW_LAUNCH_HOURS:
        return -1   # a curve or undeployed token older than the launch window is a stale launch, not an upcoming one
    if c["state"] == "E" and min(age_h, trade_h) > D.NEW_LAUNCH_HOURS:
        return -1
    p = 0.0
    p += min((o.get("curve_progress_pct") or 0) / 100, 1) * 3
    p += min((o.get("replies") or 0) / 200, 1) * 2
    p += min((o.get("holders") or 0) / 1000, 1) * 2
    p += min((o.get("vol_usd") or 0) / 500_000, 1) * 2
    p += (o.get("organic_score") or 0) / 100 * 2
    p += 1 if o.get("is_live") else 0
    p += 1 if c["state"] == "A" and (s.get("independent_sources") or 0) >= 2 else 0
    mc = o.get("mcap_usd") or 0
    if c["state"] == "E" and mc < 30_000:
        p -= 2
    return p


def shortlist(con, cands: dict[str, dict], t: float, n: int = MAX_SHORTLIST) -> list[dict]:
    fresh = sorted((c for c in cands.values() if c.get("contract")), key=lambda c: -prescore(c, t))
    fresh = [c for c in fresh if prescore(c, t) > 0][:n]
    # plus every launch already tracked in an active status (re-checked each run until hand-over)
    ids = {c["launch_id"] for c in fresh}
    for r in con.execute(f"SELECT * FROM upcoming_launches WHERE phase IN ('PRE_LAUNCH','NEW_LAUNCH_MONITOR') AND status IN ({','.join('?' * len(TRACK_STATUSES))}) AND contract IS NOT NULL",
                         TRACK_STATUSES):
        if r["launch_id"] not in ids:
            fresh.append(cands.get(r["launch_id"]) or from_row(con, r)); ids.add(r["launch_id"])
    return fresh


def from_row(con, r) -> dict[str, Any]:
    r = dict(r)
    c = D._cand(r["chain"], r["contract"], launch_id=r["launch_id"]) if r["contract"] else D._cand(r["chain"], None, launch_id=r["launch_id"])
    c["launch_id"] = r["launch_id"]
    for k in ("project", "symbol", "launchpad", "state", "creator", "created_at", "first_trade_at", "scheduled_at", "pool", "curve_pool", "contract_verified", "contract_source"):
        c[k] = r.get(k)
    c["sources"] = json.loads(r["sources_json"] or "[]")
    c["links"] = json.loads(r["official_links_json"] or "{}")
    c["tokenomics"] = json.loads(r["tokenomics_json"] or "{}")
    c["signals"] = json.loads(r["social_json"] or "{}")
    c["flags"] = json.loads(r["risk_flags_json"] or "[]")
    if r["expected_valuation_usd"] or r["expected_liquidity_usd"]:
        c["expected"] = {"grad_mcap_usd": r["expected_valuation_usd"], "grad_liquidity_usd": r["expected_liquidity_usd"], "basis": r["valuation_basis"]}
    o = con.execute("SELECT * FROM launch_observations WHERE launch_id=? ORDER BY observed_at DESC LIMIT 1", (r["launch_id"],)).fetchone()
    if o:
        c["obs"] = {k: o[k] for k in ("price_usd", "mcap_usd", "fdv_usd", "liquidity_usd", "curve_progress_pct", "holders", "buyers", "sellers", "vol_usd", "replies", "is_live") if o[k] is not None}
    return c


def refresh(c: dict, bodies: dict, t: float, sol: float | None, eth: float | None) -> dict:
    """Merge fresh deep-research bodies (coins-v2, Jupiter search, token pools) into a candidate."""
    mint = c.get("contract")
    sub = {k: v for k, v in bodies.items() if mint and (k.endswith(mint) or k == f"pump:coin:{mint}")}
    jt = bodies.get(f"jup_tok:{mint}")
    if isinstance(jt, list):
        sub["jup:recent"] = [x for x in jt if isinstance(x, dict) and x.get("id") == mint]
    gp = bodies.get(f"gt_pools:token:{mint}")
    if isinstance(gp, dict):
        sub[f"gt_pools:x:new:{mint}"] = {"pools": [p for p in gp.get("pools") or [] if p.get("base") == mint]}
    new = D.from_bodies(sub, t, sol, eth).get(c["launch_id"])
    if new:
        D._merge(new, c)   # fresh values win; old fill gaps
        new["obs"] = {**(c.get("obs") or {}), **{k: v for k, v in new["obs"].items() if v is not None}}
        if c.get("pool") and not new.get("pool"):
            new["pool"] = c["pool"]
        # the deepest pool by liquidity is the token's main market
        if isinstance(gp, dict):
            best = max((p for p in gp.get("pools") or [] if p.get("base") == mint and p.get("reserve")), key=lambda p: p["reserve"], default=None)
            if best and not any(x in (best.get("dex") or "") for x in ("pump-fun", "launchlab", "meteora-dbc")):
                new["pool"] = best["pool"]; new["obs"]["liquidity_usd"] = best["reserve"]
                if new["state"] in "BCD":
                    new["state"] = "E"
                new["first_trade_at"] = new.get("first_trade_at") or D._iso(best.get("created"))
            elif best:
                new["curve_pool"] = new.get("curve_pool") or best["pool"]
        return new
    return c


def contract_checks(c: dict, bodies: dict, hold: dict) -> dict[str, Any]:
    """Token mechanics and LP control from chain-derived data. clean=None when nothing was read."""
    chain, mint, pad = c.get("chain"), c.get("contract"), c.get("launchpad") or ""
    facts, fatal, warn = [], [], []
    lp = None
    clean = None
    if chain == "solana":
        rg = bodies.get(f"rug:{mint}")
        sig = c.get("signals") or {}
        tk = c.get("tokenomics") or {}
        mint_auth = hold.get("mint_authority") if hold.get("source") else sig.get("mint_authority")
        frz = hold.get("freeze_authority") if hold.get("source") else sig.get("freeze_authority")
        known = bool(hold.get("source")) or sig.get("mint_disabled") is not None
        if sig.get("mint_disabled") is False or mint_auth:
            fatal.append("mint authority active (supply can be inflated)")
        if sig.get("freeze_disabled") is False or frz:
            fatal.append("freeze authority active (holders can be frozen)")
        if tk.get("transfer_hook"):
            fatal.append("transfer hook program set (transfers can be blocked or taxed by another program)")
        fee = tk.get("transfer_fee_bps")
        if fee:
            (fatal if fee >= 1000 else warn).append(f"transfer fee {fee / 100:.1f}%")
        if isinstance(rg, dict):
            for r in rg.get("risks") or []:
                if (r.get("level") == "danger") and any(x in (r.get("name") or "").lower() for x in ("freeze", "mint authority", "rugged", "copycat", "permanent delegate")):
                    fatal.append("RugCheck: " + r["name"])
            known = True
        if known:
            clean = not fatal and not warn
            facts.append("authorities and token-2022 extensions read from " + ("RugCheck" if hold.get("source") else "Jupiter audit"))
        # LP control
        if pad == "pump.fun":
            lp = "BURNED_OR_PROTOCOL"; facts.append("pump.fun: curve is protocol-held; PumpSwap migration LP is burned by the protocol (mechanism)")
        elif pad.startswith("raydium-launchlab"):
            lp = "BURNED_OR_PROTOCOL" if c["state"] in "BCD" else None
            facts.append("LaunchLab curve is protocol-held" + ("; post-migration LP handling depends on the pool's migrate type (not verified)" if c["state"] == "E" else ""))
        if lp is None and isinstance(rg, dict):
            lks = [m.get("lp", {}).get("lpLockedPct") for m in rg.get("markets") or [] if isinstance(m.get("lp"), dict) and m["lp"].get("lpLockedPct") is not None]
            if lks:
                lp = "BURNED_OR_PROTOCOL" if max(lks) >= 95 else "LOCKED" if max(lks) >= 50 else "REMOVABLE"
                facts.append(f"RugCheck: LP locked/burned {max(lks):.0f}% on the main market")
    else:
        try:
            from ..chains import evm
            b = evm.build_bundle(chain, mint, bodies, None, None)
            m = evm.mechanics(b)
            if m.get("contract_risk") != "UNKNOWN":
                clean = m["contract_risk"] in ("LOW", "MODERATE") and not m.get("flags")
                facts += m.get("facts", [])[:4]
                if m["contract_risk"] == "FATAL":
                    fatal += [f for f in m["flags"] if f in ("HONEYPOT", "CANNOT_BUY", "EXTREME_TAX", "HIDDEN_OWNER")]
                elif m["contract_risk"] == "HIGH":
                    warn += m["flags"]
        except Exception as e:  # pragma: no cover - partial data
            facts.append(f"EVM contract check failed: {e}")
        if pad == "clanker":
            lp = "BURNED_OR_PROTOCOL"; facts.append("Clanker: LP position held by the Clanker locker contract (mechanism)")
        elif pad.startswith("zora"):
            lp = "BURNED_OR_PROTOCOL"; facts.append("Zora: liquidity is protocol-owned in the coin's Uniswap v4 position (mechanism)")
    return {"clean": clean, "fatal": fatal, "warnings": warn, "lp_control": lp, "facts": facts}


def assess_one(con, c: dict, bodies: dict, t: float, pads: dict, sol: float | None, persist: bool = True) -> dict[str, Any]:
    hold = wallets.holders(c, bodies)
    tk = tokenomics.analyze(c, hold, None, sol)
    dep = deployer.assess(con, c, bodies, t, persist=persist)
    total_supply = (c.get("tokenomics") or {}).get("total_supply")
    snip = wallets.snipers(c, bodies, hold, total_supply)
    clus = wallets.funding_clusters(c, bodies, hold, snip)
    soc = social.analyze(con, c, t)
    comp = cohort.comparables(con, c, t)
    contract = contract_checks(c, bodies, hold)
    res = ranker.score(con, c, tk, dep, hold, snip, clus, soc, comp, pads, contract, t)
    out = {"c": c, "tk": tk, "dep": dep, "hold": hold, "snip": snip, "clus": clus, "soc": soc, "comp": comp, "contract": contract, "res": res, "alerts": []}
    if c["state"] == "E":
        wins = MON.windows(c, bodies, hold, snip, t)
        pd = MON.price_discovery(c, bodies, t)
        conv = MON.convert(con, c, tk, hold, snip, clus)
        out.update({"windows": wins, "price_discovery": pd, "conversion": conv})
        bad = pd.get("pattern") in ("FAILED LAUNCH", "PUMP AND DUMP")
        if bad and res["status"] not in ("SEVERE RISK", "AVOID"):
            res["avoid"].append(f"price discovery {pd['pattern']}: {pd.get('why_short') or ''}".strip(": "))
            res["status"], res["status_reason"] = "AVOID", "; ".join(res["avoid"])
            res["entry_view"] = ranker.entry_view(c, "AVOID", res["verify_at_launch"])
    if not persist:
        return out
    con.execute("UPDATE upcoming_launches SET pool=COALESCE(?, pool), curve_pool=COALESCE(?, curve_pool), state=CASE WHEN phase IN ('PRE_LAUNCH','NEW_LAUNCH_MONITOR') THEN ? ELSE state END, "
                "first_trade_at=COALESCE(first_trade_at, ?), team_alloc_pct=COALESCE(?, team_alloc_pct), tokenomics_json=? WHERE launch_id=?",
                (c.get("pool"), c.get("curve_pool"), c["state"], c.get("first_trade_at"), tk.get("initial_insider_pct"), json.dumps({**(c.get("tokenomics") or {}), "analysis": {k: tk.get(k) for k in ("initial_float_pct", "initial_insider_pct", "insider_basis", "locked_pct", "overhang_pct", "liquidity_ratio", "liquidity_basis")}}), c["launch_id"]))
    o = c.get("obs") or {}
    db.insert(con, "launch_observations", {"launch_id": c["launch_id"], "observed_at": t, "source": "deep", "state": c["state"], "mcap_usd": o.get("mcap_usd"), "fdv_usd": o.get("fdv_usd"),
              "liquidity_usd": o.get("liquidity_usd"), "curve_progress_pct": o.get("curve_progress_pct"), "holders": o.get("holders"), "top10_pct": hold.get("top10_ex_pool_pct"),
              "dev_pct": hold.get("dev_pct"), "sniper_pct": snip.get("sniper_still_holding_pct"), "replies": o.get("replies"), "vol_usd": o.get("vol_usd")})
    flags = wallets.persist(con, c["launch_id"], t, hold, snip, clus)
    out["alerts"] += ranker.persist(con, c, res, t)
    out["alerts"] += suspicious(con, c, hold, clus, t)
    if c["state"] == "E":
        MON.persist_windows(con, c["launch_id"], out["windows"], t, c.get("first_trade_at"))
        tr = MON.handover(con, c, out["price_discovery"], out["conversion"], res["status"], t)
        out["transition"] = tr
    out["wallet_flags"] = flags
    return out


def suspicious(con, c: dict, hold: dict, clus: dict, t: float) -> list[dict]:
    """SUSPICIOUS WALLET ACTIVITY: dev wallet share falling between observations, or a new funding cluster."""
    al = []
    prev = con.execute("SELECT dev_pct FROM launch_observations WHERE launch_id=? AND dev_pct IS NOT NULL AND observed_at < ? ORDER BY observed_at DESC LIMIT 1", (c["launch_id"], t)).fetchone()
    if prev and hold.get("dev_pct") is not None and prev["dev_pct"] - hold["dev_pct"] >= 1.0:
        al.append({"launch_id": c["launch_id"], "kind": "SUSPICIOUS_WALLET_ACTIVITY", "text": f"{c.get('symbol')}: creator balance fell {prev['dev_pct']:.1f}% -> {hold['dev_pct']:.1f}% of supply"})
    if clus.get("clusters"):
        al.append({"launch_id": c["launch_id"], "kind": "SUSPICIOUS_WALLET_ACTIVITY", "text": f"{c.get('symbol')}: " + "; ".join(clus["facts"])[:300]})
    for a in al:
        db.insert(con, "launch_alerts", {"alerted_at": t, **a})
    return al


def run_assess(con, bodies: dict, short: list[dict], t: float, persist: bool = True) -> list[dict]:
    sol, eth = prices(bodies)
    pads = cohort.launchpad_stats(con, t, persist=persist)
    out = []
    for c in short:
        c = refresh(c, bodies, t, sol, eth)
        out.append(assess_one(con, c, bodies, t, pads, sol, persist))
    out.sort(key=lambda r: (r["res"]["status"] in ("SEVERE RISK", "AVOID", "IGNORE"), -(r["res"]["score"] or 0)))
    return out


def cohort_ingest(con, bodies: dict, t: float, sol: float | None) -> int:
    """Outcome readings for cohort tokens (coins-v2 re-reads)."""
    n = 0
    for k, v in bodies.items():
        if k.startswith("pump:coin:") and isinstance(v, dict) and v.get("mint"):
            mc = D._f(v.get("usd_market_cap"))
            rtok = D._f(v.get("real_token_reserves"))
            grad = bool(v.get("complete")) or rtok == 0
            D.update_cohort(con, v["mint"], {"mcap_usd": mc, "ath_usd": D._f(v.get("ath_market_cap")), "last_trade_at": D._iso(v.get("last_trade_timestamp"))}, grad, t)
            n += 1
    return n
