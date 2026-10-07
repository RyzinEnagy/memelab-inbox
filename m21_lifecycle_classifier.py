"""m21: lifecycle stage classifier.

Classifies a token into one of eight lifecycle stages using several independent
evidence families (age, drawdown from ATH, volume trend, holder dynamics, order
flow, early-wallet/insider behavior, attention, liquidity trend). A stage is
only asserted with MODERATE or HIGH confidence when at least two independent
families agree; otherwise the module returns LOW confidence and lists what is
missing. Chart shape alone never drives the classification.

Public interface:
    analyze(bundle, structure=None, flows=None, attention=None) -> dict
"""
from __future__ import annotations

from typing import Any

STAGES = [
    "LAUNCH",
    "DISCOVERY",
    "EARLY_EXPANSION",
    "BROAD_ATTENTION",
    "MANIA",
    "DISTRIBUTION",
    "BREAKDOWN",
    "POST_BREAKDOWN",  # stage 8, carries a sub_stage
]
STAGE8_SUBSTAGES = ["DEAD_CAT_BOUNCE", "REACCUMULATION", "EXTINCTION"]

# Evidence families. "chart" (price vs ATH) is deliberately NOT sufficient alone.
FAMILIES = ["age", "chart", "volume", "holders", "orderflow", "insiders", "attention", "liquidity"]


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def _num(x: Any) -> float | None:
    try:
        if x is None or isinstance(x, bool):
            return None
        v = float(x)
        if v != v:  # NaN
            return None
        return v
    except (TypeError, ValueError):
        return None


def _get(d: Any, *path: str, default: Any = None) -> Any:
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
        if cur is None:
            return default
    return cur


def _ratio(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b <= 0:
        return None
    return a / b


def _confidence_label(n_families: int, margin: float) -> str:
    """Two independent families are the floor for anything above LOW.

    margin = top_votes / (top_votes + runner_up_votes); 0.5 means a tie.
    """
    if n_families < 2:
        return "LOW"
    if n_families >= 4 and margin >= 0.6:
        return "HIGH"
    if n_families >= 2 and margin >= 0.52:
        return "MODERATE"
    return "LOW"


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def analyze(bundle: dict | None, structure: dict | None = None, flows: dict | None = None,
            attention: dict | None = None) -> dict:
    bundle = bundle if isinstance(bundle, dict) else {}
    structure = structure if isinstance(structure, dict) else {}
    flows = flows if isinstance(flows, dict) else {}
    attention = attention if isinstance(attention, dict) else {}

    facts: list[str] = []
    inferences: list[str] = []
    heuristics: list[str] = []
    unknowns: list[str] = []
    evidence: list[str] = []
    missing: list[str] = []

    # votes[stage] = weight; family_used[stage] = set of families that voted for it
    votes: dict[str, float] = {s: 0.0 for s in STAGES}
    family_votes: dict[str, set[str]] = {s: set() for s in STAGES}
    sub_votes: dict[str, float] = {s: 0.0 for s in STAGE8_SUBSTAGES}
    families_present: set[str] = set()

    def vote(stage: str, family: str, weight: float, why: str) -> None:
        votes[stage] += weight
        family_votes[stage].add(family)
        families_present.add(family)
        evidence.append(f"[{family}] {why} -> {stage}")

    market = bundle.get("market") if isinstance(bundle.get("market"), dict) else {}

    # ---------------- age ----------------
    age_h = _num(market.get("age_hours"))
    if age_h is None:
        unknowns.append("market.age_hours missing: cannot anchor stage on age")
        missing.append("age")
    else:
        facts.append(f"Token age {age_h:.1f}h")
        families_present.add("age")
        if age_h < 6:
            vote("LAUNCH", "age", 1.0, f"age {age_h:.1f}h < 6h")
        elif age_h < 48:
            vote("DISCOVERY", "age", 0.6, f"age {age_h:.1f}h in 6-48h window")
            vote("EARLY_EXPANSION", "age", 0.4, f"age {age_h:.1f}h compatible with early expansion")
        elif age_h < 24 * 7:
            vote("EARLY_EXPANSION", "age", 0.4, f"age {age_h:.1f}h (2-7d)")
            vote("BROAD_ATTENTION", "age", 0.3, f"age {age_h:.1f}h (2-7d)")
        else:
            # old tokens: age alone says nothing about later stages, small spread vote
            for s in ("BROAD_ATTENTION", "MANIA", "DISTRIBUTION", "BREAKDOWN", "POST_BREAKDOWN"):
                votes[s] += 0.1
            evidence.append(f"[age] age {age_h:.1f}h >= 7d: late-stage candidates only")

    # ---------------- chart: price vs ATH ----------------
    pct_from_ath = _num(structure.get("pct_from_ath"))
    if pct_from_ath is None:
        # try to derive from ohlcv if available
        ohlcv = bundle.get("ohlcv") if isinstance(bundle.get("ohlcv"), dict) else {}
        px = _num(market.get("price_usd"))
        highs = []
        for tf in ("day1", "hour1", "minute15"):
            rows = ohlcv.get(tf) or []
            for r in rows:
                if isinstance(r, (list, tuple)) and len(r) >= 3:
                    h = _num(r[2])
                    if h is not None:
                        highs.append(h)
        if highs and px is not None and max(highs) > 0:
            pct_from_ath = (px / max(highs) - 1.0) * 100.0
            inferences.append(f"pct_from_ath derived from bundle OHLCV highs: {pct_from_ath:.1f}%")
    if pct_from_ath is None:
        unknowns.append("structure.pct_from_ath missing and not derivable from OHLCV")
        missing.append("chart")
    else:
        if pct_from_ath > 0:
            pct_from_ath = 0.0
        facts.append(f"Price is {pct_from_ath:.1f}% from ATH")
        families_present.add("chart")
        if pct_from_ath >= -10:
            vote("MANIA", "chart", 0.5, f"at/near ATH ({pct_from_ath:.1f}%)")
            vote("BROAD_ATTENTION", "chart", 0.4, f"at/near ATH ({pct_from_ath:.1f}%)")
            vote("EARLY_EXPANSION", "chart", 0.3, f"at/near ATH ({pct_from_ath:.1f}%)")
        elif pct_from_ath >= -35:
            vote("DISTRIBUTION", "chart", 0.6, f"{pct_from_ath:.1f}% off ATH (10-35% drawdown)")
            vote("BROAD_ATTENTION", "chart", 0.3, f"{pct_from_ath:.1f}% off ATH could be a pullback")
        elif pct_from_ath >= -70:
            vote("BREAKDOWN", "chart", 0.7, f"{pct_from_ath:.1f}% off ATH (35-70% drawdown)")
            vote("DISTRIBUTION", "chart", 0.3, f"{pct_from_ath:.1f}% off ATH")
        else:
            vote("POST_BREAKDOWN", "chart", 1.2, f"{pct_from_ath:.1f}% off ATH (>70% drawdown)")
            vote("BREAKDOWN", "chart", 0.2, f"{pct_from_ath:.1f}% off ATH")
    heuristics.append("Chart drawdown alone never sets the stage; it must be corroborated by a second family.")

    # ---------------- volume trend ----------------
    vol = market.get("vol") if isinstance(market.get("vol"), dict) else {}
    v1, v6, v24 = _num(vol.get("h1")), _num(vol.get("h6")), _num(vol.get("h24"))
    r1 = _ratio(None if v1 is None else v1 * 24, v24)
    r6 = _ratio(None if v6 is None else v6 * 4, v24)
    if r1 is None and r6 is None:
        unknowns.append("volume windows (h1/h6/h24) missing: volume trend unknown")
        missing.append("volume")
    else:
        families_present.add("volume")
        parts = []
        if r1 is not None:
            parts.append(f"h1*24/h24={r1:.2f}")
        if r6 is not None:
            parts.append(f"h6*4/h24={r6:.2f}")
        facts.append("Volume trend " + ", ".join(parts))
        r = r1 if r1 is not None else r6
        r_alt = r6 if r6 is not None else r1
        if r >= 2.0 and (r_alt is None or r_alt >= 1.3):
            vote("MANIA", "volume", 0.6, f"volume accelerating hard ({', '.join(parts)})")
            vote("BROAD_ATTENTION", "volume", 0.4, "volume accelerating")
            vote("EARLY_EXPANSION", "volume", 0.3, "volume accelerating")
            sub_votes["DEAD_CAT_BOUNCE"] += 0.5
        elif r >= 1.2:
            vote("EARLY_EXPANSION", "volume", 0.5, f"volume rising ({', '.join(parts)})")
            vote("BROAD_ATTENTION", "volume", 0.4, "volume rising")
            vote("DISCOVERY", "volume", 0.3, "volume rising")
            sub_votes["REACCUMULATION"] += 0.3
        elif r >= 0.7:
            vote("DISTRIBUTION", "volume", 0.3, f"volume flat ({', '.join(parts)})")
            vote("BROAD_ATTENTION", "volume", 0.3, "volume flat")
            sub_votes["REACCUMULATION"] += 0.4
        elif r >= 0.35:
            vote("DISTRIBUTION", "volume", 0.5, f"volume fading ({', '.join(parts)})")
            vote("BREAKDOWN", "volume", 0.4, "volume fading")
            sub_votes["REACCUMULATION"] += 0.2
        else:
            vote("BREAKDOWN", "volume", 0.3, f"volume collapsing ({', '.join(parts)})")
            vote("POST_BREAKDOWN", "volume", 0.5, "volume collapsing")
            sub_votes["EXTINCTION"] += 0.7

    # organic share of volume
    org_b, org_s = _num(market.get("organic_buy_vol_24h")), _num(market.get("organic_sell_vol_24h"))
    if org_b is not None and org_s is not None and v24:
        org_share = (org_b + org_s) / v24
        facts.append(f"Organic share of 24h volume {org_share*100:.0f}%")
        if org_share < 0.3:
            inferences.append("Low organic share: volume may be wash/bot driven, weakens volume evidence")
            heuristics.append("Volume evidence discounted when organic share < 30%")
            votes["MANIA"] *= 0.8
        elif org_share > 0.7:
            inferences.append("High organic share: volume evidence is credible")
    else:
        unknowns.append("organic volume split missing")

    # ---------------- holders ----------------
    hc = _num(market.get("holder_count"))
    if hc is None:
        hc = _num(_get(bundle, "holders", "total"))
    hchg = market.get("holder_change") if isinstance(market.get("holder_change"), dict) else None
    if hc is None and not hchg:
        unknowns.append("holder_count / holder_change missing")
        missing.append("holders")
    else:
        families_present.add("holders")
        if hc is not None:
            facts.append(f"Holder count {int(hc)}")
            if hc < 300:
                vote("LAUNCH", "holders", 0.4, f"{int(hc)} holders")
                vote("DISCOVERY", "holders", 0.4, f"{int(hc)} holders")
            elif hc < 2000:
                vote("DISCOVERY", "holders", 0.3, f"{int(hc)} holders")
                vote("EARLY_EXPANSION", "holders", 0.4, f"{int(hc)} holders")
            elif hc < 10000:
                vote("EARLY_EXPANSION", "holders", 0.2, f"{int(hc)} holders")
                vote("BROAD_ATTENTION", "holders", 0.4, f"{int(hc)} holders")
            else:
                vote("BROAD_ATTENTION", "holders", 0.3, f"{int(hc)} holders")
                vote("MANIA", "holders", 0.2, f"{int(hc)} holders")
        if hchg:
            # accept pct or absolute changes keyed by window, e.g. {"h24_pct": 12.0} or {"h24": 150}
            chg_pct = None
            for k in ("h24_pct", "pct_24h", "h6_pct", "pct_6h", "h1_pct", "pct_1h"):
                if _num(hchg.get(k)) is not None:
                    chg_pct = _num(hchg.get(k))
                    break
            if chg_pct is None and hc:
                for k in ("h24", "h6", "h1"):
                    if _num(hchg.get(k)) is not None:
                        chg_pct = _num(hchg.get(k)) / hc * 100.0
                        break
            if chg_pct is not None:
                facts.append(f"Holder change {chg_pct:+.1f}%")
                if chg_pct > 15:
                    vote("MANIA", "holders", 0.5, f"holders +{chg_pct:.0f}% (surge)")
                    vote("BROAD_ATTENTION", "holders", 0.4, "holder surge")
                    vote("EARLY_EXPANSION", "holders", 0.3, "holder surge")
                elif chg_pct > 3:
                    vote("EARLY_EXPANSION", "holders", 0.5, f"holders +{chg_pct:.1f}%")
                    vote("BROAD_ATTENTION", "holders", 0.3, "holders growing")
                    vote("DISCOVERY", "holders", 0.3, "holders growing")
                    sub_votes["REACCUMULATION"] += 0.4
                elif chg_pct > -2:
                    vote("DISTRIBUTION", "holders", 0.3, f"holders flat ({chg_pct:+.1f}%)")
                    sub_votes["REACCUMULATION"] += 0.3
                else:
                    vote("BREAKDOWN", "holders", 0.4, f"holders shrinking ({chg_pct:+.1f}%)")
                    vote("POST_BREAKDOWN", "holders", 0.3, "holders shrinking")
                    sub_votes["EXTINCTION"] += 0.5
            else:
                unknowns.append("holder_change present but no parseable window")

    # ---------------- order flow (net buyers) ----------------
    nb = market.get("net_buyers") if isinstance(market.get("net_buyers"), dict) else {}
    nb1, nb24 = _num(nb.get("h1")), _num(nb.get("h24"))
    if nb1 is None and nb24 is None:
        txns = market.get("txns") if isinstance(market.get("txns"), dict) else {}
        for w in ("h1", "h24"):
            row = txns.get(w)
            if isinstance(row, (list, tuple)) and len(row) >= 4:
                b, s = _num(row[2]), _num(row[3])
                if b is not None and s is not None:
                    if w == "h1":
                        nb1 = b - s
                    else:
                        nb24 = b - s
    if nb1 is None and nb24 is None:
        unknowns.append("net_buyers / txns missing: order flow unknown")
        missing.append("orderflow")
    else:
        families_present.add("orderflow")
        facts.append(f"Net buyers h1={nb1} h24={nb24}")
        ref = nb1 if nb1 is not None else nb24
        if ref > 0 and (nb24 is None or nb24 > 0):
            vote("EARLY_EXPANSION", "orderflow", 0.4, "net buyers positive")
            vote("BROAD_ATTENTION", "orderflow", 0.3, "net buyers positive")
            vote("DISCOVERY", "orderflow", 0.2, "net buyers positive")
            sub_votes["REACCUMULATION"] += 0.4
            sub_votes["DEAD_CAT_BOUNCE"] += 0.2
        elif ref > 0:
            vote("DISTRIBUTION", "orderflow", 0.3, "short-term net buyers positive but 24h negative")
            sub_votes["DEAD_CAT_BOUNCE"] += 0.5
        elif ref < 0 and (nb24 is None or nb24 < 0):
            vote("DISTRIBUTION", "orderflow", 0.4, "net buyers negative")
            vote("BREAKDOWN", "orderflow", 0.4, "net buyers negative")
            vote("POST_BREAKDOWN", "orderflow", 0.2, "net buyers negative")
            sub_votes["EXTINCTION"] += 0.3
        else:
            vote("DISTRIBUTION", "orderflow", 0.3, "net buyers mixed")

    # ---------------- insiders / early wallets ----------------
    direction = str(flows.get("large_holder_net_direction") or "").upper() or None
    inv_chg = _num(flows.get("insider_inventory_change_pct"))
    if direction is None and inv_chg is None:
        unknowns.append("flows (insider inventory / large holder direction) not provided")
        missing.append("insiders")
    else:
        families_present.add("insiders")
        if direction:
            facts.append(f"Large holder net direction {direction}")
        if inv_chg is not None:
            facts.append(f"Insider inventory change {inv_chg:+.1f}%")
        if direction == "ACCUMULATING" or (inv_chg is not None and inv_chg > 3):
            vote("DISCOVERY", "insiders", 0.4, "large holders accumulating")
            vote("EARLY_EXPANSION", "insiders", 0.4, "large holders accumulating")
            sub_votes["REACCUMULATION"] += 0.8
        elif direction == "HOLDING" or (inv_chg is not None and abs(inv_chg) <= 3):
            vote("EARLY_EXPANSION", "insiders", 0.2, "large holders holding")
            vote("BROAD_ATTENTION", "insiders", 0.3, "large holders holding")
            sub_votes["REACCUMULATION"] += 0.3
        elif direction == "SCALING_OUT" or (inv_chg is not None and inv_chg > -15):
            vote("DISTRIBUTION", "insiders", 0.6, "large holders scaling out")
            vote("MANIA", "insiders", 0.2, "early holders selling into strength")
        elif direction in ("DISTRIBUTING", "EXITING") or (inv_chg is not None and inv_chg <= -15):
            vote("DISTRIBUTION", "insiders", 0.8, f"large holders {direction or 'exiting'}")
            vote("BREAKDOWN", "insiders", 0.4, f"large holders {direction or 'exiting'}")
            vote("POST_BREAKDOWN", "insiders", 0.3, f"large holders {direction or 'exiting'}")
            sub_votes["EXTINCTION"] += 0.4
            sub_votes["DEAD_CAT_BOUNCE"] += 0.3
        else:
            unknowns.append(f"unrecognized large_holder_net_direction {direction!r}")

    # ---------------- attention ----------------
    trend = str(attention.get("trend") or "").upper() or None
    if trend is None:
        unknowns.append("attention trend not provided")
        missing.append("attention")
    else:
        families_present.add("attention")
        facts.append(f"Attention trend {trend}")
        if trend == "ACCELERATION":
            vote("BROAD_ATTENTION", "attention", 0.5, "attention accelerating")
            vote("MANIA", "attention", 0.5, "attention accelerating")
            vote("EARLY_EXPANSION", "attention", 0.3, "attention accelerating")
            sub_votes["DEAD_CAT_BOUNCE"] += 0.3
        elif trend == "STABILITY":
            vote("BROAD_ATTENTION", "attention", 0.3, "attention stable")
            vote("DISTRIBUTION", "attention", 0.3, "attention stable (plateau)")
            sub_votes["REACCUMULATION"] += 0.3
        elif trend == "EXHAUSTION":
            vote("DISTRIBUTION", "attention", 0.5, "attention exhausting")
            vote("BREAKDOWN", "attention", 0.4, "attention exhausting")
            vote("POST_BREAKDOWN", "attention", 0.2, "attention exhausting")
            sub_votes["EXTINCTION"] += 0.5
        else:
            unknowns.append(f"unrecognized attention trend {trend!r}")

    # ---------------- liquidity trend ----------------
    liq_trend = None
    liq_chg = _num(structure.get("liquidity_change_pct"))
    if liq_chg is None:
        liq_chg = _num(market.get("liquidity_change_pct"))
    if liq_chg is None and isinstance(flows.get("liquidity_trend"), str):
        liq_trend = flows["liquidity_trend"].upper()
    if liq_chg is not None:
        liq_trend = "RISING" if liq_chg > 5 else "FALLING" if liq_chg < -5 else "FLAT"
    if liq_trend is None:
        unknowns.append("liquidity trend not available (no liquidity_change_pct)")
        missing.append("liquidity")
    else:
        families_present.add("liquidity")
        facts.append(f"Liquidity trend {liq_trend}" + (f" ({liq_chg:+.1f}%)" if liq_chg is not None else ""))
        if liq_trend == "RISING":
            vote("EARLY_EXPANSION", "liquidity", 0.3, "liquidity rising")
            vote("BROAD_ATTENTION", "liquidity", 0.3, "liquidity rising")
            sub_votes["REACCUMULATION"] += 0.3
        elif liq_trend == "FALLING":
            vote("DISTRIBUTION", "liquidity", 0.3, "liquidity falling")
            vote("BREAKDOWN", "liquidity", 0.4, "liquidity falling")
            vote("POST_BREAKDOWN", "liquidity", 0.2, "liquidity falling")
            sub_votes["EXTINCTION"] += 0.4

    # ---------------- aggregate ----------------
    ranked = sorted(votes.items(), key=lambda kv: kv[1], reverse=True)
    top_stage, top_score = ranked[0]
    alt_stage, alt_score = ranked[1] if len(ranked) > 1 else (None, 0.0)
    total = sum(votes.values()) or 1.0
    agreement = top_score / total
    margin = top_score / (top_score + alt_score) if (top_score + alt_score) > 0 else 0.0

    # independent families supporting top stage, excluding chart-only support
    supporting = family_votes[top_stage]
    n_indep = len(supporting)
    chart_only = supporting == {"chart"} or (n_indep == 0)

    if top_score <= 0:
        stage = "UNKNOWN"
        confidence = "LOW"
        inferences.append("No evidence families available; stage cannot be classified")
    else:
        stage = top_stage
        confidence = _confidence_label(n_indep, margin)
        if chart_only:
            confidence = "LOW"
            inferences.append("Only chart-shape evidence supports this stage; confidence capped at LOW")

    sub_stage = None
    if stage == "POST_BREAKDOWN":
        sub_ranked = sorted(sub_votes.items(), key=lambda kv: kv[1], reverse=True)
        sub_stage = sub_ranked[0][0] if sub_ranked[0][1] > 0 else "EXTINCTION"
        inferences.append(f"Stage 8 sub-label {sub_stage} (sub-votes: " +
                          ", ".join(f"{k}={v:.1f}" for k, v in sub_ranked) + ")")

    if stage != "UNKNOWN":
        inferences.append(
            f"Stage {stage} supported by {n_indep} evidence famil{'y' if n_indep == 1 else 'ies'} "
            f"({', '.join(sorted(supporting)) or 'none'}), vote share {agreement:.0%}, margin over runner-up {margin:.0%}"
        )
    if missing:
        unknowns.append("Missing evidence families: " + ", ".join(missing))

    alternative_reason = None
    if alt_stage and alt_score > 0:
        alt_fams = ", ".join(sorted(family_votes[alt_stage])) or "spread"
        alternative_reason = f"{alt_stage} holds {alt_score/total:.0%} of votes from {alt_fams}"

    confirm_if, reject_if = _confirm_reject(stage, sub_stage, alt_stage)

    return {
        "stage": stage,
        "sub_stage": sub_stage,
        "evidence": evidence,
        "alternative_stage": alt_stage if alt_score > 0 else None,
        "alternative_reason": alternative_reason,
        "confirm_if": confirm_if,
        "reject_if": reject_if,
        "confidence": confidence,
        "families_present": sorted(families_present),
        "families_missing": missing,
        "votes": {k: round(v, 2) for k, v in votes.items()},
        "facts": facts,
        "inferences": inferences,
        "heuristics": heuristics,
        "unknowns": unknowns,
    }


def _confirm_reject(stage: str, sub_stage: str | None, alt: str | None) -> tuple[str, str]:
    table = {
        "LAUNCH": ("holders and organic volume grow over the next 6-24h without insider selling",
                   "dev/insiders sell > 10% of supply or liquidity is pulled"),
        "DISCOVERY": ("holder growth > 3%/day, net buyers positive, large holders accumulating/holding",
                      "volume fades below 0.5x of 24h run-rate and net buyers turn negative"),
        "EARLY_EXPANSION": ("new highs with rising volume, liquidity, and holder count",
                            "price fails to make new highs while insiders scale out"),
        "BROAD_ATTENTION": ("attention accelerates further with holder surge and sustained organic volume",
                            "attention plateaus and net buyers turn negative"),
        "MANIA": ("parabolic volume with holder surge and attention acceleration persists",
                  "volume collapses >50% from peak with large holders distributing"),
        "DISTRIBUTION": ("lower highs, large holders scaling out, net buyers negative",
                         "large holders accumulate and price reclaims prior high on rising volume"),
        "BREAKDOWN": ("volume and liquidity keep falling, holders shrinking",
                      "price stabilizes with holder growth and accumulation (reaccumulation)"),
        "POST_BREAKDOWN": ("", ""),
        "UNKNOWN": ("at least two independent evidence families become available",
                    "n/a"),
    }
    if stage == "POST_BREAKDOWN":
        sub = {
            "DEAD_CAT_BOUNCE": ("bounce fails below prior breakdown level on falling volume",
                                "bounce reclaims breakdown level with holder growth and accumulation"),
            "REACCUMULATION": ("range holds with holder growth, accumulation and rising organic volume",
                               "range breaks down on rising volume with holders shrinking"),
            "EXTINCTION": ("volume, holders and liquidity keep decaying",
                           "fresh accumulation and attention appear"),
        }
        c, r = sub.get(sub_stage or "EXTINCTION", sub["EXTINCTION"])
    else:
        c, r = table.get(stage, table["UNKNOWN"])
    if alt and alt != stage:
        r = f"{r}; evidence shifts toward {alt}"
    return c, r
