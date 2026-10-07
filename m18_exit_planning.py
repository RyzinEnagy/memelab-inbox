"""m18: exit planning, built BEFORE entry.

Ladder at supply zones, principal reclaim point, runner retention, trailing thesis invalidation,
blow-off handling, and REALIZABLE proceeds at hypothetical 2x/5x/10x using the SELL quote curve
(interpolated; conservatively extrapolated and flagged beyond the largest tested size).
"""
from __future__ import annotations

import math

from . import m13_price_structure as m13
from ._common import (
    base_result,
    fmt_price,
    interp_impact,
    parse_quote_side,
    quote_unit_note,
    safe_get,
    to_float,
)


def _pick_entry(entries, prefer: str | None) -> dict | None:
    if isinstance(entries, dict) and "entries" in entries:
        entries = entries["entries"]
    entries = [e for e in (entries or []) if isinstance(e, dict) and e.get("zone_low") and e.get("zone_high")]
    if not entries:
        return None
    if prefer:
        for e in entries:
            if e.get("style") == prefer:
                return e
    order = {"BREAKOUT_RETEST": 0, "PULLBACK": 1, "CONFIRMATION": 2, "ANTICIPATION": 3}
    actionable = [e for e in entries if not e.get("pending")]
    pool = actionable or entries
    return sorted(pool, key=lambda e: order.get(e.get("style"), 9))[0]


def analyze(bundle: dict, entries: list | None = None, structure: dict | None = None, quotes: dict | None = None,
            position_usd: float | None = None, entry_style: str | None = None,
            multiples: tuple = (2, 5, 10), principal_reclaim_multiple: float = 2.0,
            runner_pct: float = 20.0, blowoff_atr_mult: float = 4.0, **kwargs) -> dict:
    out = base_result()
    out.update({"entry_style": None, "entry_price": None, "ladder": [], "principal_reclaim": None,
                "trailing_invalidation": None, "blowoff": None, "runner": None, "realizable": {}, "notes": []})
    bundle = bundle if isinstance(bundle, dict) else {}
    if not isinstance(structure, dict):
        structure = m13.analyze(bundle) if bundle.get("ohlcv") else {}
        if structure:
            out["heuristics"].append("structure= not supplied; ran m13 internally")
    if quotes is None:
        quotes = bundle.get("quotes") if isinstance(bundle.get("quotes"), dict) else {}
    price = to_float(safe_get(bundle, "market", "price_usd")) or to_float(structure.get("price"))
    entry = _pick_entry(entries, entry_style)
    if entry is None:
        out["unknowns"].append("no entry with a zone; exit plan built from current price only" if price else "no entry and no price; exit plan cannot be built")
        entry_px = price
    else:
        entry_px = (to_float(entry["zone_low"]) + to_float(entry["zone_high"])) / 2.0
        out["entry_style"] = entry.get("style")
    out["entry_price"] = entry_px
    position_usd = to_float(position_usd)

    zones = [z for z in (structure.get("zones") or []) if isinstance(z, dict) and z.get("low") and z.get("high")]
    ath = to_float(structure.get("ath"))
    atr_pct = safe_get(structure, "volatility", "headline", "atr_pct")
    atr_tf = safe_get(structure, "volatility", "headline", "tf") or "hour1"

    # ------------------------------------------------------------------ ladder
    ladder = []
    if entry_px:
        supply = sorted([z for z in zones if z["low"] > entry_px * 1.01], key=lambda z: z["low"])
        merged = []
        for z in supply:
            if merged and abs(z["low"] - merged[-1]["low"]) / merged[-1]["low"] < 0.03:
                merged[-1] = dict(merged[-1], high=max(merged[-1]["high"], z["high"]), touches=merged[-1].get("touches", 0) + z.get("touches", 0), tf=f"{merged[-1].get('tf')}+{z.get('tf')}")
            else:
                merged.append(dict(z))
        supply = merged[:4]
        if not supply and ath and ath > entry_px * 1.02:
            supply = [{"low": ath, "high": ath, "tf": "ath", "touches": 1, "why": "in-data ATH: no swing-based supply between entry and the prior high; this is where earlier buyers break even"}]
            out["heuristics"].append("no supply zones above entry: ladder uses the in-data ATH as its only structural level")
        # fractions of the position (0..1); `proceeds` is cumulative proceeds as a fraction of principal
        sellable = (100.0 - runner_pct) / 100.0
        m_r = float(principal_reclaim_multiple)
        sold = 0.0
        proceeds = 0.0
        reclaim_rung = None

        def add_reclaim():
            nonlocal sold, proceeds, reclaim_rung
            if reclaim_rung is not None:
                return
            need = max(0.0, 1.0 - proceeds)  # principal still to recover, as fraction of principal
            frac = min(need / m_r, max(0.0, sellable - sold))
            reclaim_rung = {"multiple": m_r, "price": entry_px * m_r, "pct_of_position": round(frac * 100, 1),
                            "already_recovered_pct": round(proceeds * 100, 1)}
            if frac > 0.005:
                ladder.append({
                    "trigger": f"price reaches {m_r:g}x entry ({fmt_price(entry_px * m_r)}); limit sell resting there in advance",
                    "zone": {"low": entry_px * m_r, "high": entry_px * m_r, "tf": "multiple"},
                    "multiple": round(m_r, 2), "pct_of_position": round(frac * 100, 1),
                    "rationale": f"principal reclaim: earlier rungs recovered {proceeds*100:.0f}% of principal; selling {frac*100:.0f}% of tokens here recovers the rest before impact and fees, the remainder is a free position",
                    "kind": "principal_reclaim",
                })
                sold += frac
                proceeds += frac * m_r

        for idx, z in enumerate(supply):
            mult = z["low"] / entry_px
            if mult >= m_r:
                add_reclaim()
            later = len(supply) - idx - 1
            # trim into near supply, larger clips into far supply; always keep something for later rungs
            cap = 0.20 if mult < 1.5 else (0.25 if mult < 3 else 0.30)
            reserve = 0.10 * later + (0.0 if reclaim_rung is not None or mult >= m_r else 0.25)
            frac = min(cap, max(0.0, sellable - sold - reserve))
            if frac < 0.02:
                continue
            ladder.append({
                "trigger": f"price trades into {fmt_price(z['low'])}-{fmt_price(z['high'])} ({z.get('tf')}); place the sell at the zone LOW {fmt_price(z['low'])}, not the high, so it fills before the crowd's",
                "zone": {"low": z["low"], "high": z["high"], "tf": z.get("tf"), "touches": z.get("touches")},
                "multiple": round(mult, 2), "pct_of_position": round(frac * 100, 1),
                "rationale": f"{z.get('why', 'prior swing cluster')}; holders trapped here sell into the first touch, so partial exit into that supply rather than through it"
                             + ("; near-term supply: trim only, the position's job is not done at +{:.0f}%".format((mult - 1) * 100) if mult < 1.5 else ""),
                "kind": "supply_zone",
            })
            sold += frac
            proceeds += frac * mult
        add_reclaim()
        leftover = sellable - sold
        if leftover > 0.02:
            ladder.append({
                "trigger": f"above the last structural level ({fmt_price(supply[-1]['high']) if supply else fmt_price(entry_px * m_r)}): price discovery. Sell in clips on vertical candles per the blow-off rule, or on the trailing invalidation",
                "zone": None, "multiple": None, "pct_of_position": round(leftover * 100, 1),
                "rationale": "no structural level to place a sell at; the remaining non-runner tokens are distributed into strength rather than at a level",
                "kind": "discovery",
            })
        if not supply:
            out["notes"].append("price discovery with no supply above: the ladder has no structural levels; principal reclaim at a multiple, blow-off rule and trailing invalidation carry the plan")
            out["unknowns"].append("no resistance zones above entry; ladder is multiple-based only")
        out["_reclaim_rung"] = reclaim_rung
    out["ladder"] = ladder

    # ------------------------------------------------------------------ principal reclaim
    if entry_px:
        m = float(principal_reclaim_multiple)
        rung = out.pop("_reclaim_rung", None) or {"multiple": m, "price": entry_px * m, "pct_of_position": round(100.0 / m, 1), "already_recovered_pct": 0.0}
        standalone = round(100.0 / m, 1)
        out["principal_reclaim"] = {
            "multiple": m, "price": entry_px * m,
            "pct_of_position_to_sell": rung["pct_of_position"],
            "pct_if_nothing_sold_before": standalone,
            "recovered_by_earlier_rungs_pct": rung["already_recovered_pct"],
            "text": (f"at {m:g}x ({fmt_price(entry_px * m)}) sell {rung['pct_of_position']:.0f}% of the tokens"
                     + (f" (earlier ladder rungs already recovered {rung['already_recovered_pct']:.0f}% of principal; selling {standalone:.0f}% would be needed with no prior sales)" if rung["already_recovered_pct"] > 0 else f" ({standalone:.0f}% = 1/{m:g})")
                     + ": cumulative proceeds then equal the principal before impact and fees; the remainder is a free position"),
            "caveat": "principal is reclaimed only on REALIZABLE proceeds; see `realizable` for the impact at that displayed size",
        }

    # ------------------------------------------------------------------ runner
    out["runner"] = {"pct_of_position": runner_pct,
                     "text": f"retain {runner_pct:g}% as a runner managed only by the trailing invalidation and the blow-off rule; no price target"}

    # ------------------------------------------------------------------ trailing invalidation
    tr = None
    for tf in ("hour1", "day1", "minute15"):
        ptf = safe_get(structure, "per_timeframe", tf)
        if not isinstance(ptf, dict):
            continue
        lvl = ptf.get("last_higher_low") or ptf.get("last_swing_low")
        if lvl:
            tf_label = {"hour1": "hourly", "day1": "daily", "minute15": "15-minute"}.get(tf, tf)
            tr = {"tf": tf, "level": lvl, "type": "last_higher_low" if ptf.get("last_higher_low") else "last_swing_low",
                  "text": f"exit the remaining position on {"an" if tf_label == "hourly" else "a"} {tf_label} close below the last higher low ({fmt_price(lvl)} now); re-anchor to each new higher low as the trend advances. A close, not a wick.",
                  "initial": f"until the trade is in profit the entry invalidation applies: {entry.get('invalidation_text') if entry else 'close below entry zone low'}"}
            break
    if tr is None:
        out["unknowns"].append("no swing lows available to trail; trailing invalidation falls back to the entry invalidation")
        if entry:
            tr = {"tf": entry.get("tf"), "level": entry.get("invalidation_level"), "type": "entry_invalidation",
                  "text": entry.get("invalidation_text")}
    out["trailing_invalidation"] = tr

    # ------------------------------------------------------------------ blow-off
    if atr_pct and price:
        out["blowoff"] = {
            "rule": f"if a single {atr_tf} candle extends more than {blowoff_atr_mult:g} ATR ({blowoff_atr_mult*atr_pct:.1f}% of price at current ATR {atr_pct:.2f}%) above the prior close, or the move goes parabolic (three consecutive candles each larger than the last with volume climbing), sell into strength: 25-50% of what remains at market, do not wait for the close",
            "atr_pct": atr_pct, "atr_mult": blowoff_atr_mult,
            "why": "parabolic extensions in memecoins mark distribution; the bid that exists during the spike is gone within hours, and realizable proceeds collapse with it",
        }
    else:
        out["unknowns"].append("ATR unavailable; blow-off rule cannot be quantified (qualitative: sell into vertical candles)")

    # ------------------------------------------------------------------ realizable proceeds
    sell_pts = parse_quote_side(quotes.get("SELL") if isinstance(quotes, dict) else None)
    note = quote_unit_note(quotes.get("SELL") if isinstance(quotes, dict) else None)
    if note:
        out["heuristics"].append("SELL " + note)
    realizable = {}
    if position_usd is None:
        out["unknowns"].append("position_usd not supplied; realizable proceeds computed per $1,000 of position (scale linearly only for the displayed value, impact does not scale linearly)")
        base_pos = 1000.0
        out["realizable_basis_usd"] = base_pos
    else:
        base_pos = position_usd
        out["realizable_basis_usd"] = base_pos
    for m in multiples:
        m = float(m)
        key = int(m) if m.is_integer() else m
        displayed = base_pos * m
        if not sell_pts:
            realizable[key] = {"displayed": displayed, "realizable": None, "impact_pct": None, "flag": "no_sell_quotes"}
            continue
        imp, flag = interp_impact(sell_pts, displayed)
        if imp is None or not math.isfinite(imp):
            realizable[key] = {"displayed": displayed, "realizable": None, "impact_pct": None, "flag": "route_failed_or_unknown"}
            out["unknowns"].append(f"{key}x: SELL of ${displayed:,.0f} failed to route or exceeds quotable depth")
            continue
        imp_capped = min(imp, 99.0)
        real = displayed * (1 - imp_capped / 100.0)
        realizable[key] = {"displayed": displayed, "realizable": round(real, 2), "impact_pct": round(imp_capped, 2), "flag": flag,
                           "haircut_pct": round(imp_capped, 2), "all_at_once": True,
                           "note": "single-shot sale; laddering across the plan above reduces impact per clip" + (", beyond tested depth: extrapolated conservatively" if flag == "beyond_tested_depth" else "")}
        if flag == "beyond_tested_depth":
            out["unknowns"].append(f"{key}x: displayed ${displayed:,.0f} is beyond the largest tested SELL size (${sell_pts[-1][0]:,.0f}); impact extrapolated")
    out["realizable"] = realizable
    if not sell_pts:
        out["unknowns"].append("no SELL quotes in bundle; realizable proceeds unknown")
    else:
        out["facts"].append(f"SELL curve tested at {len(sell_pts)} sizes (${sell_pts[0][0]:,.0f} to ${sell_pts[-1][0]:,.0f})")
        worst = max((v for v in realizable.values() if v.get("impact_pct") is not None), key=lambda v: v["impact_pct"], default=None)
        if worst:
            out["inferences"].append(f"at {max(realizable, key=float)}x a one-shot exit of ${worst['displayed']:,.0f} costs {worst['impact_pct']:.1f}% impact (flag: {worst['flag']}); plan the ladder so no single clip exceeds the tested depth")

    out["notes"].extend([
        "the exit plan is fixed before entry; it changes only when structure changes (new zone, new higher low), never because of P&L",
        "ladder sells are placed at zone lows (front-running the obvious level); principal reclaim is the first priority, runner the last",
        "realizable proceeds use the SELL quote curve at the displayed size; depth at the time of exit will differ from depth now, usually for the worse in a blow-off",
    ])
    if structure and not zones:
        out["unknowns"].append("m13 produced no zones; ladder has no structural levels")
    out["heuristics"].append(f"ladder weights 45/30/15/10% of the sellable {100-runner_pct:g}% across up to four supply zones; principal reclaim at {principal_reclaim_multiple:g}x sells 1/{principal_reclaim_multiple:g} of tokens")
    return out
