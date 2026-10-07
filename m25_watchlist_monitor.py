"""25_WATCHLIST_MONITOR: compare a new compact snapshot with the previous thesis snapshot and narrate WHAT CHANGED."""
from __future__ import annotations

import json
from typing import Any


def compact_snapshot(bundle: dict[str, Any], mods: dict[str, dict], score_result: dict | None, status: str | None) -> dict[str, Any]:
    mk = bundle.get("market") or {}
    hold, depth, early, cl, lc, st, att = (mods.get(k) or {} for k in ("holders", "depth", "early", "clusters", "lifecycle", "structure", "attention"))
    return {
        "t": bundle.get("observed_at"), "price": mk.get("price_usd"), "mcap": mk.get("market_cap"), "fdv": mk.get("fdv"),
        "liquidity": mk.get("liquidity_usd_total"), "exit_cap_3pct": depth.get("exit_capacity_usd_3pct"), "holders": mk.get("holder_count") or hold.get("holder_count"),
        "adj_top10": hold.get("adjusted_top10_pct"), "cluster_pct": cl.get("cluster_adjusted_ownership_pct"), "dev_pct": hold.get("dev_holding_pct"),
        "insider_pct": hold.get("insider_pct"), "direction": early.get("large_holder_net_direction"), "vol_24h": (mk.get("vol") or {}).get("24h"),
        "net_buyers_24h": (mk.get("net_buyers") or {}).get("24h"), "structure": st.get("structure"), "nearest_support": (st.get("nearest_support") or {}).get("mid") if isinstance(st.get("nearest_support"), dict) else None,
        "nearest_resistance": (st.get("nearest_resistance") or {}).get("mid") if isinstance(st.get("nearest_resistance"), dict) else None,
        "lifecycle": lc.get("stage"), "attention": att.get("trend"), "score": (score_result or {}).get("total"), "status": status,
        "fatal": [f.get("flag") for f in (score_result or {}).get("fatal_flags") or []],
    }


def _fmt(v, kind):
    if v is None:
        return "n/a"
    if kind == "usd":
        return f"${v:,.0f}"
    if kind == "pct":
        return f"{v:.1f}%"
    if kind == "price":
        return f"${v:.6g}"
    if kind == "int":
        return f"{int(v):,}"
    return str(v)


FIELDS = [("price", "Price", "price"), ("mcap", "Market cap", "usd"), ("liquidity", "Liquidity", "usd"), ("exit_cap_3pct", "Exit capacity (3%)", "usd"),
          ("holders", "Holders", "int"), ("adj_top10", "Adjusted top-10", "pct"), ("cluster_pct", "Cluster-adjusted ownership", "pct"), ("dev_pct", "Dev holding", "pct"),
          ("insider_pct", "Insider-flagged holding", "pct"), ("vol_24h", "24h volume", "usd"), ("net_buyers_24h", "Net buyers 24h", "int"), ("direction", "Material-wallet direction", "str"),
          ("structure", "Structure", "str"), ("lifecycle", "Lifecycle", "str"), ("attention", "Attention", "str"), ("score", "Score", "int"), ("status", "Status", "str")]


def diff(prev: dict | None, cur: dict, prev_invalidation_level: float | None = None, prev_interpretation: str | None = None) -> dict[str, Any]:
    if not prev:
        return {"first_snapshot": True, "lines": ["first snapshot; nothing to compare"], "invalidated": False, "deteriorating": False, "score_delta": None, "previous_status": None}
    lines, changes = [], {}
    for key, label, kind in FIELDS:
        a, b = prev.get(key), cur.get(key)
        if a == b or (a is None and b is None):
            continue
        changes[key] = (a, b)
        delta = ""
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a:
            delta = f" ({(b - a) / abs(a):+.1%})"
        lines.append(f"{label}: {_fmt(a, kind)} -> {_fmt(b, kind)}{delta}")
    invalidated = False; reason = None
    if prev_invalidation_level and cur.get("price") is not None and cur["price"] < prev_invalidation_level:
        invalidated = True; reason = f"price {cur['price']:.6g} is below the previously stated invalidation {prev_invalidation_level:.6g}"
    score_delta = (cur.get("score") - prev.get("score")) if cur.get("score") is not None and prev.get("score") is not None else None
    deteriorating = (score_delta is not None and score_delta <= -10) or (cur.get("direction") in ("DISTRIBUTING", "EXITING") and prev.get("direction") not in ("DISTRIBUTING", "EXITING")) or bool(set(cur.get("fatal") or []) - set(prev.get("fatal") or []))
    # interpretation
    interp = []
    if "liquidity" in changes and changes["liquidity"][0] and changes["liquidity"][1]:
        d = changes["liquidity"][1] / changes["liquidity"][0] - 1
        interp.append("liquidity " + ("grew" if d > 0 else "shrank") + f" {abs(d):.0%}")
    if "insider_pct" in changes or "adj_top10" in changes:
        key = "insider_pct" if "insider_pct" in changes else "adj_top10"
        a, b = changes[key]
        if a is not None and b is not None:
            if b < a and (changes.get("price", (0, 0))[1] or 0) >= (changes.get("price", (0, 0))[0] or 0):
                interp.append("concentrated holders reduced inventory while price held: consistent with absorption")
            elif b < a:
                interp.append("concentrated holders reduced inventory into a falling price: distribution, not absorption")
    if "vol_24h" in changes and changes["vol_24h"][0] and changes["vol_24h"][1]:
        d = changes["vol_24h"][1] / changes["vol_24h"][0] - 1
        interp.append(f"24h volume {'up' if d > 0 else 'down'} {abs(d):.0%}" + ("; activity declining does not yet establish renewed demand" if d < -0.3 else ""))
    return {"first_snapshot": False, "lines": lines or ["no material change in tracked fields"], "changes": changes, "invalidated": invalidated, "reason": reason,
            "deteriorating": deteriorating, "score_delta": score_delta, "previous_status": prev.get("status"), "previous_interpretation": prev_interpretation,
            "revised_interpretation": "; ".join(interp) or "no change in interpretation warranted by tracked fields"}
