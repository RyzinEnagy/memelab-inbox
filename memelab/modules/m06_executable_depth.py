"""06_EXECUTABLE_DEPTH: build the executable depth curve from Jupiter quotes (BUY and SELL separately).

Quotes dict: bundle["quotes"][side][usd] = {"in","out","impact" (fraction, Jupiter priceImpactPct),"usd","route":[[amm,label,pct,inMint,outMint,inAmt,outAmt],...],"status"}
Effective price for BUY = usd_in / tokens_out; for SELL = usd_out / tokens_in.
"""
from __future__ import annotations

import math
from typing import Any

SOL = "So11111111111111111111111111111111111111112"


def _interp_capacity(curve: list[tuple[float, float]], max_impact_pct: float) -> float | None:
    """Largest size whose impact <= max_impact_pct, log-linear interpolation between tested points; never extrapolate above max tested."""
    pts = sorted((s, i) for s, i in curve if i is not None)
    if not pts:
        return None
    if pts[0][1] > max_impact_pct:
        return 0.0
    cap = pts[0][0]
    for (s0, i0), (s1, i1) in zip(pts, pts[1:]):
        if i1 <= max_impact_pct:
            cap = s1
            continue
        if i1 > i0:
            t = (max_impact_pct - i0) / (i1 - i0)
            cap = math.exp(math.log(s0) + t * (math.log(s1) - math.log(s0)))
        break
    return cap


def analyze(bundle: dict[str, Any], decimals: int | None = None, max_entry_impact_pct: float = 1.5, max_exit_impact_pct: float = 3.0) -> dict[str, Any]:
    q = bundle.get("quotes") or {}
    mk = bundle.get("market") or {}
    sol_px = mk.get("sol_price")
    dec = decimals if decimals is not None else (bundle.get("identity") or {}).get("decimals") or (bundle.get("authorities") or {}).get("decimals") or 6
    mid = mk.get("price_usd")
    facts, inferences, unknowns = [], [], []
    table = []
    curves = {"BUY": [], "SELL": []}
    route_pools = set(); max_hops = 0
    no_route_sizes = {"BUY": [], "SELL": []}
    for side in ("BUY", "SELL"):
        for usd in sorted(q.get(side) or {}, key=float):
            r = q[side][usd]
            if r.get("status") != "OK":
                table.append({"side": side, "usd": usd, "status": r.get("status"), "error": str(r.get("error"))[:120]})
                no_route_sizes[side].append(usd)
                continue
            inn, out = r.get("in"), r.get("out")
            eff = None; usd_val = None
            if side == "BUY" and out and sol_px and inn:
                usd_in = inn / 1e9 * sol_px
                tokens = out / (10 ** dec)
                eff = usd_in / tokens if tokens else None
                usd_val = usd_in
            elif side == "SELL" and inn and out and sol_px:
                tokens = inn / (10 ** dec)
                usd_out = out / 1e9 * sol_px
                eff = usd_out / tokens if tokens else None
                usd_val = usd_out
            imp_pct = (r.get("impact") or 0) * 100
            vs_mid = ((eff / mid - 1) * 100) if eff and mid else None
            route = r.get("route") or []
            labels = [x[1] for x in route]
            for x in route:
                route_pools.add(x[0])
            hops = len({(x[3], x[4]) for x in route})
            max_hops = max(max_hops, len(route))
            table.append({"side": side, "usd": usd, "status": "OK", "effective_price": eff, "impact_pct": imp_pct, "vs_mid_pct": vs_mid,
                          "usd_value": usd_val, "n_route_legs": len(route), "pools": labels, "proceeds_usd": usd_val if side == "SELL" else None})
            curves[side].append((usd, imp_pct))
    caps = {
        "entry_capacity_usd_1_5pct": _interp_capacity(curves["BUY"], max_entry_impact_pct),
        "exit_capacity_usd_3pct": _interp_capacity(curves["SELL"], max_exit_impact_pct),
        "exit_capacity_usd_5pct": _interp_capacity(curves["SELL"], 5.0),
        "exit_capacity_usd_10pct": _interp_capacity(curves["SELL"], 10.0),
    }
    tested_max_sell = max((s for s, _ in curves["SELL"]), default=None)
    for k, v in list(caps.items()):
        if v is not None and tested_max_sell and v >= tested_max_sell - 1e-6 and "exit" in k:
            caps[k + "_note"] = f"at least ${tested_max_sell:,.0f} (largest size tested; true capacity may be higher)"
    if not table:
        unknowns.append("no router quotes collected")
    else:
        ok_sell = [t for t in table if t["side"] == "SELL" and t["status"] == "OK"]
        ok_buy = [t for t in table if t["side"] == "BUY" and t["status"] == "OK"]
        if ok_sell:
            worst = ok_sell[-1]
            facts.append(f"SELL ${worst['usd']:,.0f}: impact {worst['impact_pct']:.2f}%, proceeds ${worst['proceeds_usd']:,.0f}" if worst.get("proceeds_usd") else f"SELL ${worst['usd']:,.0f}: impact {worst['impact_pct']:.2f}%")
            best = ok_sell[0]
            facts.append(f"SELL ${best['usd']:,.0f}: impact {best['impact_pct']:.2f}%")
        if ok_buy:
            facts.append(f"BUY ${ok_buy[0]['usd']:,.0f}: impact {ok_buy[0]['impact_pct']:.2f}%; BUY ${ok_buy[-1]['usd']:,.0f}: impact {ok_buy[-1]['impact_pct']:.2f}%")
        if caps["exit_capacity_usd_3pct"] is not None:
            facts.append(f"exit capacity at <=3% impact about ${caps['exit_capacity_usd_3pct']:,.0f}; at <=5% about ${caps['exit_capacity_usd_5pct']:,.0f}; at <=10% about ${caps['exit_capacity_usd_10pct']:,.0f}")
        if no_route_sizes["SELL"]:
            facts.append("no sell route at sizes: " + ", ".join(f"${s:,.0f}" for s in no_route_sizes["SELL"]))
        facts.append(f"routes touch {len(route_pools)} distinct pool(s); max legs in one route {max_hops}")
        # asymmetry
        if ok_buy and ok_sell:
            common = sorted(set(t["usd"] for t in ok_buy) & set(t["usd"] for t in ok_sell))
            asym = []
            for s in common:
                b = next(t for t in ok_buy if t["usd"] == s); se = next(t for t in ok_sell if t["usd"] == s)
                asym.append((s, se["impact_pct"] - b["impact_pct"]))
            bad = [a for a in asym if a[1] > 1.0]
            if bad:
                inferences.append("sell-side impact exceeds buy-side by >1 pt at " + ", ".join(f"${s:,.0f} (+{d:.1f} pts)" for s, d in bad) + ": exits are harder than entries")
    # round-trip friction at $1k (buy impact + sell impact + est fees)
    fric = None
    b1 = next((t for t in table if t["side"] == "BUY" and t["status"] == "OK" and t["usd"] <= 1000), None)
    s1 = next((t for t in table if t["side"] == "SELL" and t["status"] == "OK" and t["usd"] <= 1000), None)
    tf = (bundle.get("authorities") or {}).get("transfer_fee_bps") or 0
    if b1 and s1:
        fee_pct = 0.5  # assumed DEX fee each way for memecoin pools (0.25%) x2; most launchpad pools charge more, flagged in mechanics
        fric = b1["impact_pct"] + s1["impact_pct"] + fee_pct + 2 * tf / 100
        facts.append(f"round-trip friction at ~$1k about {fric:.2f}% (buy impact {b1['impact_pct']:.2f} + sell impact {s1['impact_pct']:.2f} + est. DEX fees {fee_pct:.2f}" + (f" + transfer fee {2*tf/100:.2f}" if tf else "") + ")")
    status = "OK" if any(t["status"] == "OK" for t in table if t["side"] == "SELL") else ("NO_ROUTE" if table else "UNKNOWN")
    return {"table": table, "curves": curves, **caps, "route_status": status, "no_route": status == "NO_ROUTE",
            "n_hops": max_hops, "n_route_pools": len(route_pools), "friction_pct": fric, "liquidity_usd": mk.get("liquidity_usd_total"),
            "tested_max_sell_usd": tested_max_sell,
            "facts": facts, "inferences": inferences,
            "heuristics": ["the most important liquidity question is how much can actually be realized; displayed liquidity is not an exit quote",
                           "price impact (what the pool charges you) is distinct from slippage tolerance (what you allow the tx to accept)"],
            "unknowns": unknowns}
