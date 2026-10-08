"""DEPLOYER_HISTORY: what has this creator launched before, and how did it go?

Classes: STRONG POSITIVE HISTORY / MIXED HISTORY / NO HISTORY / CONCERNING HISTORY / SEVERE RISK.
Anonymous is not fraud and a known name is not safety: the class comes only from the launch record, prior rug evidence, and
launch frequency. Heuristic thresholds are stated in the evidence so they can be argued with.
"""
from __future__ import annotations

import json
import statistics
import time
from typing import Any

from .. import db


def from_launches(rows: list[dict], current: str | None, t: float) -> dict[str, Any]:
    """rows: the creator's launches as {mint, created_at, ath_usd, mcap_usd, graduated, rug_flag, last_trade_at}."""
    prior = [r for r in rows if r.get("mint") != current]
    n = len(prior)
    ev: list[str] = []
    if n == 0:
        return {"classification": "NO HISTORY", "launches": 0, "launches_7d": 0, "graduated": 0, "best_ath_usd": None, "median_ath_usd": None, "abandoned": 0, "flagged_rugs": 0,
                "evidence": ["no earlier launches by this creator in the launchpad index (first launch, or a fresh wallet)"]}
    athv = [r["ath_usd"] for r in prior if r.get("ath_usd") is not None]
    grad = sum(1 for r in prior if r.get("graduated"))
    l7 = sum(1 for r in prior if r.get("created_at") and t - r["created_at"] < 7 * 86400)
    rugs = sum(1 for r in prior if r.get("rug_flag"))
    abandoned = sum(1 for r in prior if not r.get("graduated") and (r.get("ath_usd") or 0) < 15_000 and r.get("created_at") and t - r["created_at"] > 86400)
    best = max(athv) if athv else None
    med = statistics.median(athv) if athv else None
    ev.append(f"{n} earlier launch(es), {grad} graduated, {l7} in the last 7 days; best peak ${best or 0:,.0f}, median peak ${med or 0:,.0f}; {abandoned} abandoned under $15k peak")
    if rugs:
        ev.append(f"{rugs} earlier launch(es) carry a rug flag (RugCheck 'rugged' or LP removal)")
    if rugs >= 1:
        cls = "SEVERE RISK"
    elif l7 >= 10 or (n >= 5 and grad == 0 and (best or 0) < 50_000):
        cls = "CONCERNING HISTORY"
        ev.append("rule: >=10 launches in 7 days, or >=5 launches with none graduating and no peak above $50k, reads as serial low-effort launching")
    elif grad >= 1 and (best or 0) >= 1_000_000 and grad / n >= 0.3:
        cls = "STRONG POSITIVE HISTORY"
        ev.append("rule: at least one earlier launch peaked above $1M and >=30% graduated")
    else:
        cls = "MIXED HISTORY"
    return {"classification": cls, "launches": n, "launches_7d": l7, "graduated": grad, "best_ath_usd": best, "median_ath_usd": med, "abandoned": abandoned, "flagged_rugs": rugs, "evidence": ev}


def rows_from_bodies(bodies: dict, creator: str, chain: str) -> list[dict]:
    out = []
    for k, v in bodies.items():
        if k in (f"pump:creator:{creator}",) and isinstance(v, list):
            for r in v:
                rtok = r.get("real_token_reserves")
                out.append({"mint": r.get("mint"), "created_at": (r.get("created_timestamp") or 0) / 1000 or None, "ath_usd": r.get("ath_market_cap"), "mcap_usd": r.get("usd_market_cap"),
                            "graduated": bool(r.get("complete")) or rtok == 0, "rug_flag": False, "last_trade_at": (r.get("last_trade_timestamp") or 0) / 1000 or None})
        if k == f"ray:user:{creator}" and isinstance(v, list):
            for r in v:
                out.append({"mint": r.get("mint"), "created_at": (r.get("createAt") or 0) / 1000 or None, "ath_usd": r.get("marketCap"), "mcap_usd": r.get("marketCap"),
                            "graduated": (r.get("finishingRate") or 0) >= 100, "rug_flag": False})
        if k == f"clanker:deployer:{creator}" and isinstance(v, list):
            from .discover import _iso
            for r in v:
                out.append({"mint": (r.get("contract_address") or "").lower(), "created_at": _iso(r.get("deployed_at") or r.get("created_at")), "ath_usd": (r.get("mkt") or {}).get("marketCap"),
                            "mcap_usd": (r.get("mkt") or {}).get("marketCap"), "graduated": True, "rug_flag": False})
    # mark rugs we already know about from RugCheck reports in the same result set
    for r in out:
        rg = bodies.get(f"rug:{r['mint']}")
        if isinstance(rg, dict) and rg.get("rugged"):
            r["rug_flag"] = True
    return out


def assess(con, c: dict, bodies: dict, t: float, persist: bool = True) -> dict[str, Any]:
    creator = c.get("creator")
    if not creator:
        return {"classification": "UNKNOWN", "evidence": ["creator not identified by any source"], "launches": None}
    rows = rows_from_bodies(bodies, creator, c.get("chain"))
    # include launches by this creator that the system already saw (any platform)
    for r in con.execute("SELECT mint, created_at, ath_usd, mcap_usd, graduated, rug_flag, last_trade_at FROM launch_cohort WHERE creator=?", (creator,)):
        if not any(x["mint"] == r["mint"] for x in rows):
            rows.append(dict(r))
    queried = any(k in bodies for k in (f"pump:creator:{creator}", f"ray:user:{creator}", f"clanker:deployer:{creator}"))
    res = from_launches(rows, c.get("contract"), t)
    if not queried:
        res["evidence"].append("creator history not queried this run (only launches the system had already seen are counted)")
        if res["classification"] == "NO HISTORY":
            res["classification"] = "UNKNOWN"
    # EVM: GoPlus links the creator to earlier honeypots
    gp = bodies.get(f"goplus:{c.get('chain')}:{c.get('contract')}")
    rec = (gp or {}).get((c.get("contract") or "").lower()) if isinstance(gp, dict) else None
    if rec and rec.get("honeypot_with_same_creator") == "1":
        res["classification"] = "SEVERE RISK"; res["evidence"].append("GoPlus: this creator deployed honeypots before")
    sib = (c.get("signals") or {}).get("creator_launches_in_sample") or 0
    if sib >= 3:
        res["evidence"].append(f"{sib} launches by this creator appear in this run's newest-launch sample alone")
        if res["classification"] in ("NO HISTORY", "MIXED HISTORY", "UNKNOWN"):
            res["classification"] = "CONCERNING HISTORY"
    if persist:
        db.insert(con, "deployer_history", {"deployer": creator, "chain": c.get("chain"), "platform": c.get("launchpad"), "observed_at": t, "launches": res.get("launches"),
                  "launches_7d": res.get("launches_7d"), "graduated": res.get("graduated"), "best_ath_usd": res.get("best_ath_usd"), "median_ath_usd": res.get("median_ath_usd"),
                  "abandoned": res.get("abandoned"), "flagged_rugs": res.get("flagged_rugs"), "classification": res["classification"], "evidence_json": json.dumps(res["evidence"])})
    return res
