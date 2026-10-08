"""PRE_LAUNCH_RANKER.

PRE-LAUNCH OPPORTUNITY SCORE (100): launch structure 20, ownership/team/deployer 15, attention quality 15, narrative/chain momentum 15,
liquidity plan 10, comparable launches 10, catalyst/uniqueness 5, risk/asymmetry 10. Unknown inputs earn zero and are never redistributed.
DATA COMPLETENESS (0-100) = share of the score's weight whose inputs were known. CONFIDENCE follows completeness.
Not comparable with the post-launch opportunity score: different information environment.
Statuses: IGNORE / WATCH / HIGH-INTEREST WATCH / LAUNCH MONITOR / RESEARCH INCOMPLETE / AVOID / SEVERE RISK. There is no BUY.
"""
from __future__ import annotations

import json
from typing import Any

from .. import db
from ..chains._util import Component, lin, loglin

HIGH_QUALITY_SCORE, HIGH_QUALITY_COMPLETENESS = 70, 60


def _chain_ctx(con, chain: str | None) -> dict:
    if not chain:
        return {}
    r = con.execute("SELECT soi, trend, research_allocation FROM chain_scores WHERE chain_id=? ORDER BY observed_at DESC LIMIT 1", (chain,)).fetchone()
    g = con.execute("SELECT regime, confidence FROM regime_snapshots ORDER BY observed_at DESC LIMIT 1").fetchone()
    return {"soi": r["soi"] if r else None, "trend": r["trend"] if r else None, "allocation": r["research_allocation"] if r else None, "regime": g["regime"] if g else None}


def _narrative(con, c: dict) -> tuple[str | None, str | None]:
    try:
        from ..chains.narrative import narrative_for_token
        nid = narrative_for_token(con, c.get("contract") or c["launch_id"], c.get("project"), c.get("symbol"))
    except Exception:
        nid = None
    if not nid:
        return None, None
    r = con.execute("SELECT lifecycle FROM narratives WHERE narrative_id=?", (nid,)).fetchone()
    return nid, r["lifecycle"] if r else None


def score(con, c: dict, tk: dict, dep: dict, hold: dict, snip: dict, clus: dict, soc: dict, comp: dict, pads: dict, contract: dict, t: float) -> dict[str, Any]:
    comps: dict[str, Component] = {}
    o = c.get("obs") or {}
    state = c["state"]
    # ---- launch structure (20) ----
    x = comps["launch_structure"] = Component("launch_structure", 20)
    fl = tk.get("initial_float_pct")
    x.add(4, (lin(fl, 10, 60) if fl is not None and fl < 60 else (1.0 if fl is not None else None)), "initial float (10%..60%+)")
    ov = tk.get("overhang_pct")
    x.add(3, lin(ov, 40, 0) if ov is not None else (1.0 if tk.get("basis", "").startswith("MECHANISM") and tk.get("locked_pct") in (None, 0, 0.0) else None), "future supply overhang (40%..0%)")
    val = tk.get("expected_valuation_usd") or o.get("mcap_usd")
    med = (pads.get(c.get("launchpad")) or {}).get("median_ath_usd")
    x.add(2, (lin(val / med, 50, 1) if med and val else None), "valuation vs launchpad median peak (50x..1x)")
    clean = contract.get("clean")
    x.add(5, 1.0 if clean is True else 0.0 if clean is False else None, "token mechanics clean (authorities, fees, hooks, taxes)")
    # ---- ownership / team / deployer (15) ----
    x = comps["ownership_deployer"] = Component("ownership_deployer", 15)
    dmap = {"STRONG POSITIVE HISTORY": 1.0, "MIXED HISTORY": 0.6, "NO HISTORY": 0.5, "CONCERNING HISTORY": 0.1, "SEVERE RISK": 0.0}
    x.add(4, dmap.get(dep.get("classification")), "deployer track record")
    ins = tk.get("initial_insider_pct")
    ins_v = lin(ins, 30, 2) if ins is not None else None
    if ins_v is not None and tk.get("insider_basis") in ("MECHANISM", "CLAIMED"):
        ins_v *= 0.5   # a launch rule or a claim says nothing about what the creator bought on the curve
    x.add(3, ins_v, f"insider share (30%..2%; {tk.get('insider_basis') or 'UNKNOWN'})")
    t10 = hold.get("top10_ex_pool_pct")
    x.add(3, lin(t10, 60, 15) if t10 is not None else None, "top-10 excl. pools (60%..15%)")
    sh = snip.get("sniper_still_holding_pct") if snip.get("sniper_wallets") is not None else None
    x.add(2, lin(sh, 25, 2) if sh is not None else (None if state in ("A", "B") else None), "sniper inventory still held (25%..2%)")
    x.add(2, (0.0 if clus.get("clusters") else 1.0) if clus.get("wallets_checked") else None, "no funding clusters among top/early wallets")
    # ---- attention quality (15) ----
    x = comps["attention"] = Component("attention", 15)
    x.add(4, lin(soc.get("organic_points"), 0, 5), "organic signals (comments, livestream, organic score, news)")
    x.add(2, 1.0 if soc.get("paid_points") == 0 else 0.4 if soc.get("paid_points") == 1 else 0.0, "no paid-promotion dominance")
    b = o.get("buyers") or o.get("holders")
    x.add(3, loglin(b, 30, 3000) if b else None, "unique buyers / holders (log 30..3000)")
    x.add(6, None, "X / Telegram / Discord / Farcaster growth (not readable)")
    # ---- narrative / chain momentum (15) ----
    x = comps["narrative_chain"] = Component("narrative_chain", 15)
    ctx = _chain_ctx(con, c.get("chain"))
    x.add(5, lin(ctx.get("soi"), 25, 75), "chain SOI (25..75)")
    nid, life = _narrative(con, c)
    lmap = {"EMERGING": 1.0, "ACCELERATING": 1.0, "MANIA": 0.6, "MATURE": 0.4, "EXHAUSTING": 0.15, "DEAD": 0.0}
    x.add(6, lmap.get(life), f"narrative lifecycle ({nid or 'no narrative matched'}: {life or 'UNKNOWN'})")
    rmap = {"RISK-ON": 1.0, "HIGH-VOLATILITY SPECULATION": 0.7, "NEUTRAL": 0.6, "RISK-OFF": 0.2, "CAPITAL FLIGHT": 0.0}
    x.add(4, rmap.get(ctx.get("regime")), f"market regime ({ctx.get('regime') or 'UNKNOWN'})")
    # ---- liquidity plan (10) ----
    x = comps["liquidity_plan"] = Component("liquidity_plan", 10)
    lr = tk.get("liquidity_ratio")
    x.add(4, lin(lr, 0.03, 0.3) if lr is not None else None, f"liquidity / market cap ({tk.get('liquidity_basis') or 'UNKNOWN'}; 0.03..0.30)")
    lpc = contract.get("lp_control")
    x.add(4, {"BURNED_OR_PROTOCOL": 1.0, "LOCKED": 0.8, "REMOVABLE": 0.0}.get(lpc), f"LP control ({lpc or 'UNKNOWN'})")
    x.add(2, 1.0 if c.get("launchpad") in ("pump.fun", "clanker") or (c.get("launchpad") or "").startswith("raydium-launchlab") else None, "migration venue is a standard AMM path")
    # ---- comparables (10) ----
    x = comps["comparables"] = Component("comparables", 10)
    x.add(6, {"FAVORABLE": 1.0, "NEUTRAL": 0.5, "POOR": 0.1}.get(comp.get("verdict")), f"comparable launches ({comp.get('verdict') or 'UNKNOWN'}, n={comp.get('n', 0)})")
    qs = (pads.get(c.get("launchpad")) or {}).get("quality_score")
    x.add(4, qs / 100 if qs is not None else None, "launchpad quality score")
    # ---- catalyst / uniqueness (5) ----
    x = comps["catalyst_uniqueness"] = Component("catalyst_uniqueness", 5)
    col = next((f for f in c.get("flags") or [] if f.startswith("TICKER_COLLISION")), None)
    x.add(2, 0.0 if col else 1.0 if c.get("symbol") else None, "ticker unique among tracked tokens")
    x.add(3, 1.0 if soc.get("mentions_7d") else None, "independent catalyst/news mention")
    # ---- risk / asymmetry (10) ----
    x = comps["risk_asymmetry"] = Component("risk_asymmetry", 10)
    mc = o.get("mcap_usd")
    if state in ("C", "D") and val and mc:
        x.add(5, lin(mc / val, 1.0, 0.2), "distance to graduation valuation (closer = less upside left)")
    elif state == "E" and med and mc:
        x.add(5, lin(mc / med, 5, 0.5), "current cap vs launchpad median peak")
    else:
        x.add(5, None, "valuation room (no observed cap)")
    age_h = (t - (c.get("first_trade_at") or c.get("created_at") or t)) / 3600
    x.add(5, 0.0 if contract.get("fatal") else (1.0 if not tk.get("flags") else 0.5), "no fatal or structural red flags")
    total = round(sum(v.points for v in comps.values()), 1)
    completeness = round(100 * sum(v.coverage * v.max for v in comps.values()) / 100, 1)
    confidence = "HIGH" if completeness >= 75 else "MODERATE" if completeness >= 50 else "LOW"
    # ---- status ----
    fatal = list(contract.get("fatal") or [])
    if dep.get("classification") == "SEVERE RISK":
        fatal.append("deployer SEVERE RISK: " + "; ".join(dep.get("evidence") or [])[:160])
    if hold.get("rugged"):
        fatal.append("RugCheck marks the token rugged")
    if (hold.get("insider_network_pct") or 0) > 40:
        fatal.append(f"insider networks hold {hold['insider_network_pct']:.0f}%")
    avoid = []
    if ins is not None and ins >= 30:
        avoid.append(f"insider share {ins:.0f}%")
    if t10 is not None and t10 >= 50:
        avoid.append(f"top-10 excl. pools {t10:.0f}%")
    if sh is not None and sh >= 20:
        avoid.append(f"snipers still hold {sh:.0f}%")
    if dep.get("classification") == "CONCERNING HISTORY":
        avoid.append("deployer has a concerning launch record")
    if soc.get("classification") == "PAID / COORDINATED-LEANING":
        avoid.append("promotion is paid while organic interest is thin")
    if clus.get("clusters"):
        avoid.append("funding clusters among top/early wallets")
    if fatal:
        status, reason = "SEVERE RISK", "; ".join(fatal)
    elif avoid:
        status, reason = "AVOID", "; ".join(avoid)
    elif completeness < 40:
        status, reason = "RESEARCH INCOMPLETE", f"data completeness {completeness:.0f}%"
    elif total >= 68 and completeness >= 55 and (state in "ABCD" or age_h <= 24):
        status, reason = "LAUNCH MONITOR", "strong structure with enough data: observe price discovery intensively"
    elif total >= 60:
        status, reason = "HIGH-INTEREST WATCH", "above-average launch on the evidence available"
    elif total >= 48:
        status, reason = "WATCH", "ordinary launch; nothing disqualifying"
    else:
        status, reason = "IGNORE", "weak structure or attention relative to other launches"
    if state == "A":
        reason = "CONTRACT NOT YET VERIFIED. " + reason
    verify = verify_at_launch(c, tk, dep, hold, snip, contract)
    entry = entry_view(c, status, verify)
    return {"score": total, "completeness": completeness, "confidence": confidence, "status": status, "status_reason": reason, "entry_view": entry,
            "components": {k: v.to_dict() for k, v in comps.items()}, "fatal": fatal, "avoid": avoid, "verify_at_launch": verify, "chain_ctx": ctx, "narrative": nid, "narrative_lifecycle": life}


def verify_at_launch(c, tk, dep, hold, snip, contract) -> list[str]:
    v = []
    if c["state"] == "A":
        v.append("the contract address, from the project's own official channel, matching the chain index; ignore any earlier token using the name")
    if c["state"] in "ABCD":
        v.append("observed pool liquidity against the projected figure" + (f" (${tk['expected_liquidity_usd']:,.0f} projected)" if tk.get("expected_liquidity_usd") else ""))
        v.append("a real sell quote at your size (e.g. $50 and $500) with impact under 3%")
    v.append("first-minute buyers: share of supply and whether they sell into the first rally")
    v.append("creator wallet: no sales and no transfers to fresh wallets")
    if hold.get("top10_ex_pool_pct") is None or hold.get("top10_ex_pool_pct", 0) > 25:
        v.append("top-10 holders excluding pools falling toward 25% while price holds")
    if not contract.get("lp_control") or contract.get("lp_control") == "REMOVABLE":
        v.append("LP tokens burned, protocol-held, or locked with a verifiable unlock date")
    if c.get("chain") != "solana":
        v.append("buy/sell tax 0% in a live simulation (honeypot.is) and owner renounced or powerless")
    else:
        v.append("mint and freeze authority revoked; no transfer fee or transfer hook")
    v.append("price structure after the first hour: a base or orderly trend, not a parabolic open")
    return v


def entry_view(c, status, verify) -> dict[str, str]:
    st = c["state"]
    project = {"LAUNCH MONITOR": "INTERESTING LAUNCH: WATCH IT", "HIGH-INTEREST WATCH": "ABOVE-AVERAGE LAUNCH", "WATCH": "ORDINARY LAUNCH",
               "AVOID": "STRUCTURALLY WEAK LAUNCH", "SEVERE RISK": "DANGEROUS LAUNCH", "RESEARCH INCOMPLETE": "NOT ENOUGH INFORMATION", "IGNORE": "NOT WORTH ATTENTION"}.get(status, status)
    if st in ("A", "B", "D"):
        pre = "NO PRE-LAUNCH ENTRY: there is no executable depth before trading; planned liquidity is not liquidity"
    elif st == "C":
        pre = "CURVE ENTRY NOT FAVORED: the curve price is executable, but the risks the first DEX minutes reveal (snipers, dev selling, migration liquidity) are still unresolved"
    else:
        pre = "n/a (already trading)"
    post = "WAIT FOR PRICE DISCOVERY: let the first hour show structure, then hand over to the full analysis" if status not in ("AVOID", "SEVERE RISK", "IGNORE") else "NO ENTRY"
    return {"project": project, "pre_launch_entry": pre, "post_launch_entry": post}


def persist(con, c: dict, res: dict, t: float) -> list[dict]:
    alerts = []
    prev = con.execute("SELECT status FROM upcoming_launches WHERE launch_id=?", (c["launch_id"],)).fetchone()
    db.insert(con, "launch_scores", {"launch_id": c["launch_id"], "scored_at": t, "score": res["score"], "completeness": res["completeness"], "confidence": res["confidence"],
              "status": res["status"], "status_reason": res["status_reason"][:500], "entry_view": json.dumps(res["entry_view"]), "components_json": json.dumps(res["components"]),
              "fatal_json": json.dumps(res["fatal"]), "verify_at_launch_json": json.dumps(res["verify_at_launch"])})
    upd = {"prelaunch_score": res["score"], "completeness": res["completeness"], "confidence": res["confidence"], "status": res["status"], "status_reason": res["status_reason"][:500],
           "entry_view": json.dumps(res["entry_view"]), "narrative_id": res.get("narrative"), "updated_at": t}
    if res["status"] in ("SEVERE RISK", "AVOID"):
        upd["phase"] = "REJECTED"
        db.insert(con, "launch_rejections", {"launch_id": c["launch_id"], "rejected_at": t, "symbol": c.get("symbol"), "chain": c.get("chain"), "contract": c.get("contract"), "creator": c.get("creator"),
                  "reasons_json": json.dumps(res["fatal"] + res["avoid"]), "evidence_json": json.dumps({"score": res["score"], "completeness": res["completeness"], "flags": c.get("flags")})})
    con.execute(f"UPDATE upcoming_launches SET {','.join(k + '=?' for k in upd)} WHERE launch_id=?", list(upd.values()) + [c["launch_id"]])
    if res["score"] >= HIGH_QUALITY_SCORE and res["completeness"] >= HIGH_QUALITY_COMPLETENESS and not res["fatal"] and (not prev or prev["status"] != "LAUNCH MONITOR"):
        alerts.append({"launch_id": c["launch_id"], "kind": "HIGH_QUALITY_LAUNCH_DETECTED", "text": f"{c.get('symbol')} ({c.get('chain')}, {c.get('launchpad')}): score {res['score']}, completeness {res['completeness']:.0f}%"})
    for a in alerts:
        db.insert(con, "launch_alerts", {"alerted_at": t, **a})
    return alerts
