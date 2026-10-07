"""Eight separate assessments for an event-token pair, each with exposed components and explicit missing data.

Grades: STRONG / MODERATE / WEAK / UNKNOWN. UNKNOWN never earns triage points. Fatal checks from the core
pipeline (identity, mechanics, execution) override everything: verdict REJECTED regardless of other grades.

The triage score (0-100) is a sorting aid for the operator. It is not a probability of profit.
"""
from __future__ import annotations

import json
import time
from typing import Any

from .. import db

WEIGHTS = {"event_credibility": 15, "token_connection": 20, "attention_quality": 10, "timing": 15, "demand_evidence": 15, "ownership_risk": 10, "execution_feasibility": 10, "entry_quality": 5}
GRADE_PTS = {"STRONG": 1.0, "MODERATE": 0.6, "WEAK": 0.25, "UNKNOWN": 0.0}


def _g(v, strong, moderate, higher_is_better=True):
    if v is None:
        return "UNKNOWN"
    if higher_is_better:
        return "STRONG" if v >= strong else "MODERATE" if v >= moderate else "WEAK"
    return "STRONG" if v <= strong else "MODERATE" if v <= moderate else "WEAK"


def assess(event: dict, link: dict | None, attention: dict | None, core: dict | None, t: float | None = None) -> dict[str, Any]:
    """core: result of pipeline.analyze_token for the linked mint (may be None when no deep data was fetched)."""
    t = t or time.time()
    comp: dict[str, dict] = {}
    missing: list[str] = []
    fatal: list[str] = []
    mods = (core or {}).get("modules") or {}
    bundle = (core or {}).get("bundle") or {}
    mk = bundle.get("market") or {}

    # 1. event credibility
    ev_status = event.get("evidence_status")
    cred = {"CONFIRMED": "STRONG", "REPORTED": "MODERATE", "RUMOR": "WEAK"}.get(ev_status, "UNKNOWN")
    if event.get("independent_sources", 1) >= 3 and cred == "MODERATE":
        cred = "STRONG"
    if event.get("status") in ("DENIED", "CANCELLED"):
        cred = "WEAK"
    if event.get("future_dated"):
        cred = "WEAK" if cred == "STRONG" else cred
    comp["event_credibility"] = {"grade": cred, "evidence_status": ev_status, "independent_sources": event.get("independent_sources"), "repetitions": event.get("repetitions"), "status": event.get("status"), "resurfaced": event.get("resurfaced")}

    # 2. token connection
    if not link:
        comp["token_connection"] = {"grade": "UNKNOWN", "note": "no verified token linked; event record only"}
        missing.append("token link")
    else:
        strength = link.get("link_strength")
        tc = {"STRONG": "STRONG", "MODERATE": "MODERATE", "WEAK": "WEAK", "AMBIGUOUS": "WEAK"}.get(strength, "UNKNOWN")
        comp["token_connection"] = {"grade": tc, "link_type": link.get("link_type"), "link_strength": strength, "verified_mint": link.get("verified_mint"), "competing": len(json.loads(link.get("competing_json") or "[]")),
                                    "note": "unofficial name match; subject has not endorsed any token" if link.get("link_type") in ("NAME_MATCH", "TICKER_MATCH") else None}

    # 3. attention quality
    am = (attention or {}).get("metrics") or {}
    flags = (attention or {}).get("flags") or []
    if not am:
        comp["attention_quality"] = {"grade": "UNKNOWN"}; missing.append("attention sample")
    else:
        pts = 0
        pts += 1 if (am.get("independent_sources") or 0) >= 2 else 0
        pts += 1 if len(am.get("platform_groups") or []) >= 2 else 0
        pts += 1 if (am.get("mention_acceleration_x") or 0) >= 2 else 0
        pts -= 1 if any(f.startswith(("MORE COPIES", "ATTENTION CONCENTRATED", "PAID PLACEMENT")) for f in flags) else 0
        grade = "STRONG" if pts >= 3 else "MODERATE" if pts == 2 else "WEAK"
        comp["attention_quality"] = {"grade": grade, **{k: am.get(k) for k in ("unique_publishers", "independent_sources", "platform_groups", "mention_acceleration_x", "persistence_days", "top_publisher_share")}, "flags": flags, "coverage": "publisher-level only; social platforms unknown"}

    # 4. timing / how widely known
    pub = event.get("published_at"); disc = event.get("discovered_at"); ev_at = event.get("event_at")
    hours_since_pub = ((t - pub) / 3600) if pub else None
    pre_move = None
    if core and pub and bundle.get("ohlcv"):
        pre_move = _price_move_before(bundle, pub)
    timing = "UNKNOWN"
    if hours_since_pub is not None:
        timing = "STRONG" if hours_since_pub <= 6 else "MODERATE" if hours_since_pub <= 48 else "WEAK"
        if event.get("resurfaced"):
            timing = "WEAK"
        if pre_move is not None and pre_move > 50:
            timing = "WEAK"  # the move already happened before publication: information was known
    else:
        missing.append("publication time")
    comp["timing"] = {"grade": timing, "hours_since_publication": None if hours_since_pub is None else round(hours_since_pub, 1), "hours_to_event": None if not ev_at else round((ev_at - t) / 3600, 1),
                      "price_move_before_publication_pct": pre_move, "already_known": event.get("already_known") or ("resurfaced story" if event.get("resurfaced") else None)}

    # 5. demand evidence (token side)
    of = mods.get("orderflow") or {}; att = mods.get("attention") or {}; early = mods.get("early") or {}
    if not core:
        comp["demand_evidence"] = {"grade": "UNKNOWN"}; missing.append("token market data")
    else:
        nb = of.get("net_buyers_h24"); ratio = of.get("buy_sell_vol_ratio"); hc24 = ((att.get("holder_change") or {}).get("24h"))
        if nb is None and ratio is None and hc24 is None:
            comp["demand_evidence"] = {"grade": "UNKNOWN", "note": "no order-flow or holder-change observations in the bundle (trades/holder feeds failed or not fetched)"}; missing.append("order flow")
            pts = None
        else:
          pts = (1 if (nb or 0) > 0 else 0) + (1 if (ratio or 0) > 1.05 else 0) + (1 if (hc24 or 0) > 1 else 0) - (1 if str(early.get("large_holder_net_direction", "")).upper() in ("DISTRIBUTING", "EXITING") else 0)
        if pts is not None:
          comp["demand_evidence"] = {"grade": "STRONG" if pts >= 3 else "MODERATE" if pts == 2 else "WEAK", "net_buyers_24h": nb, "buy_sell_vol_ratio": ratio, "holder_change_24h_pct": hc24, "large_holder_direction": early.get("large_holder_net_direction"), "organic_share": of.get("organic_share")}

    # 6. ownership / selling risk
    hold = mods.get("holders") or {}; cl = mods.get("clusters") or {}
    if not core:
        comp["ownership_risk"] = {"grade": "UNKNOWN"}; missing.append("holder data")
    else:
        top10 = hold.get("adjusted_top10_pct"); largest = hold.get("largest_unexplained_pct"); clus = cl.get("cluster_adjusted_ownership_pct")
        vals = [x for x in (top10, (largest * 2) if largest else None, clus) if x]
        worst = max(vals) if vals else None
        if worst is None:
            missing.append("holder distribution")
        comp["ownership_risk"] = {"grade": _g(worst, 20, 35, higher_is_better=False), "adjusted_top10_pct": top10, "largest_unexplained_pct": largest, "cluster_adjusted_pct": clus, "dev_direction": early.get("large_holder_net_direction")}

    # 7. execution feasibility
    dp = mods.get("depth") or {}
    if not core:
        comp["execution_feasibility"] = {"grade": "UNKNOWN"}; missing.append("router quotes")
    else:
        exit3 = dp.get("exit_capacity_usd_3pct"); fr = dp.get("friction_pct")
        comp["execution_feasibility"] = {"grade": _g(exit3, 25_000, 5_000), "exit_capacity_usd_3pct": exit3, "exit_capacity_usd_10pct": dp.get("exit_capacity_usd_10pct"), "round_trip_friction_pct": fr, "no_route": dp.get("no_route")}

    # 8. entry quality
    en = mods.get("entries") or {}; bo = mods.get("breakout") or {}
    if not core:
        comp["entry_quality"] = {"grade": "UNKNOWN"}; missing.append("price structure")
    else:
        ents = en.get("entries") or []
        chase = bo.get("chase_risk"); chase_bad = bool(chase.get("overextended")) if isinstance(chase, dict) else bool(chase)
        comp["entry_quality"] = {"grade": "WEAK" if chase_bad else ("MODERATE" if ents else "WEAK"), "entries": [e.get("style") for e in ents], "chase_risk": chase_bad, "structure": (mods.get("structure") or {}).get("structure")}

    # fatal overrides from the core pipeline
    sc = (core or {}).get("score") or {}
    for f in sc.get("fatal_flags") or []:
        fatal.append(f"{f.get('flag')}: {f.get('evidence')}")
    if (mods.get("identity") or {}).get("status") == "IDENTITY NOT VERIFIED":
        fatal.append("IDENTITY NOT VERIFIED")

    # triage score: UNKNOWN earns 0; fatal -> 0 and REJECTED
    score = round(sum(WEIGHTS[k] * GRADE_PTS[comp[k]["grade"]] for k in WEIGHTS))
    if fatal:
        verdict, reason = "REJECTED", "fatal: " + "; ".join(fatal)[:300]; score = 0
    elif not link:
        verdict, reason = "EVENT_ONLY", "no verified token connection; keep as an event record"
    elif comp["token_connection"]["grade"] == "WEAK" and comp["event_credibility"]["grade"] != "STRONG":
        verdict, reason = "RESEARCH", "weak or ambiguous token link on an unconfirmed event"
    elif event.get("category") == "NEGATIVE":
        verdict, reason = "TRACKED", "negative catalyst: monitored for thesis deterioration, never an entry"
    elif comp["demand_evidence"]["grade"] == "UNKNOWN" or comp["execution_feasibility"]["grade"] == "UNKNOWN":
        verdict, reason = "RESEARCH", "needs deep market/on-chain research before any setup is considered"
    elif comp["execution_feasibility"]["grade"] == "WEAK":
        verdict, reason = "TRACKED", "exit capacity too thin for a realistic position; tracked only"
    elif comp["event_credibility"]["grade"] == "WEAK":
        verdict, reason = "TRACKED", "event is a RUMOR-tier or denied story; tracked for corroboration, not an entry candidate"
    elif comp["demand_evidence"]["grade"] in ("WEAK", "UNKNOWN") or comp["ownership_risk"]["grade"] == "UNKNOWN":
        verdict, reason = "TRACKED", "no demand evidence yet (attention has not shown up as buying) or ownership unknown; tracked"
    elif comp["ownership_risk"]["grade"] == "WEAK":
        verdict, reason = "TRACKED", "ownership concentration makes the selling side too strong; tracked only"
    elif comp["entry_quality"]["grade"] != "WEAK" and comp["timing"]["grade"] != "WEAK":
        verdict, reason = "WATCH_FOR_ENTRY", "credible event, verified token, demand visible, exit feasible; entry per the core entry module"
    else:
        verdict, reason = "TRACKED", "credible but either extended (chase) or late (widely known); wait for structure"
    reassess = ev_at if ev_at and ev_at > t else t + 6 * 3600
    exp = event.get("expires_at")
    return {"components": comp, "missing": missing, "fatal": fatal, "triage_score": score, "verdict": verdict, "verdict_reason": reason,
            "grades": {k: comp[k]["grade"] for k in WEIGHTS}, "reassess_at": reassess, "expires_at": exp,
            "entry_conditions": "; ".join(e.get("condition", "") for e in (en.get("entries") or [])) if core else None,
            "invalidation": "; ".join(f"{e.get('style')}: {e.get('invalidation_text')}" for e in (en.get("entries") or [])) if core else None,
            "price_now": mk.get("price_usd") if core else None, "price_before_pub_move_pct": pre_move}


def _price_move_before(bundle: dict, pub_ts: float) -> float | None:
    """Price change over the 24h before publication, from hourly candles (close at pub vs close 24h earlier)."""
    rows = (bundle.get("ohlcv") or {}).get("hour1") or []
    if not rows:
        return None
    closes = sorted(((r[0], r[4]) for r in rows if len(r) > 4 and r[4]), key=lambda x: x[0])
    at = next((c for ts, c in reversed(closes) if ts <= pub_ts), None)
    before = next((c for ts, c in reversed(closes) if ts <= pub_ts - 86400), None)
    if at and before:
        return round((at / before - 1) * 100, 1)
    return None


def store(event_id: int, mint: str | None, a: dict, quotes: dict | None = None, price_at_discovery: float | None = None, t: float | None = None) -> int:
    t = t or time.time()
    with db.connect() as con:
        rid = db.insert(con, "catalyst_assessments", {"event_id": event_id, "mint": mint, "assessed_at": t, **{k: a["grades"][k] for k in WEIGHTS},
                                                       "components_json": json.dumps(a["components"], default=str), "missing_json": json.dumps(a["missing"]), "fatal_json": json.dumps(a["fatal"]),
                                                       "triage_score": a["triage_score"], "verdict": a["verdict"], "verdict_reason": a["verdict_reason"], "entry_conditions": a.get("entry_conditions"), "invalidation": a.get("invalidation"),
                                                       "expires_at": a.get("expires_at"), "reassess_at": a.get("reassess_at"), "price_before_pub": a.get("price_before_pub_move_pct"), "price_at_discovery": price_at_discovery, "price_now": a.get("price_now"),
                                                       "quotes_json": json.dumps(quotes, default=str) if quotes else None})
        rank = {"REJECTED": 0, "EVENT_ONLY": 1, "RESEARCH": 2, "TRACKED": 3, "WATCH_FOR_ENTRY": 3}
        latest = con.execute("SELECT mint, verdict, MAX(assessed_at) FROM catalyst_assessments WHERE event_id=? GROUP BY mint", (event_id,)).fetchall()
        best = max((r["verdict"] for r in latest), key=lambda v: rank.get(v, 0), default=a["verdict"])
        new_status = {"REJECTED": "REJECTED", "EVENT_ONLY": "EVENT_ONLY", "RESEARCH": "RESEARCH", "TRACKED": "TRACKED", "WATCH_FOR_ENTRY": "TRACKED"}[best]
        old = con.execute("SELECT status FROM catalyst_events WHERE id=?", (event_id,)).fetchone()
        if old and old["status"] not in ("DENIED", "CANCELLED") and old["status"] != new_status:
            con.execute("UPDATE catalyst_events SET status=?, status_reason=?, updated_at=? WHERE id=?", (new_status, a["verdict_reason"][:300], t, event_id))
            db.insert(con, "catalyst_event_revisions", {"event_id": event_id, "revised_at": t, "kind": "STATUS", "field": "status", "old_value": old["status"], "new_value": new_status, "note": a["verdict_reason"][:300], "source_id": "assess"})
        else:
            con.execute("UPDATE catalyst_events SET updated_at=? WHERE id=?", (t, event_id))
    return rid
