"""11_EARLY_WALLET_ANALYSIS: dev / creator / top-holder / large-trader behavior from recent trades and holder data.

Classifies the aggregate behavior of material wallets as ACCUMULATING / HOLDING / SCALING_OUT / DISTRIBUTING / EXITING
and distinguishes absorption from distribution by pairing flows with price and volume (Phase 8).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def analyze(bundle: dict[str, Any], holders_out: dict | None = None, big_trade_usd: float = 2000) -> dict[str, Any]:
    trades = bundle.get("trades") or []
    mk = bundle.get("market") or {}
    ident = bundle.get("identity") or {}
    h = bundle.get("holders") or {}
    facts, inferences, unknowns, heur = [], [], [], []
    top = (holders_out or {}).get("classified") or []
    econ_owner = {c["owner"]: c for c in top if c.get("owner") and c.get("classification") not in ("POOL", "BURN", "LOCKER", "CEX")}
    dev_set = {x for x in (ident.get("creator"), ident.get("dev")) if x}
    # per wallet flow in the trade window
    flow = defaultdict(lambda: {"buy_usd": 0.0, "sell_usd": 0.0, "buy_tok": 0.0, "sell_tok": 0.0, "n": 0, "first": None, "last": None})
    window_start, window_end = None, None
    for t in trades:
        ts, w, kind, amt, usd = t[0], t[1], t[2], t[3] or 0, t[4] or 0
        f = flow[w]; f["n"] += 1
        f["first"] = f["first"] or ts; f["last"] = ts
        window_start = min(window_start or ts, ts); window_end = max(window_end or ts, ts)
        if kind == "buy":
            f["buy_usd"] += usd; f["buy_tok"] += amt
        else:
            f["sell_usd"] += usd; f["sell_tok"] += amt
    # dev behaviour
    dev_rows = []
    for d in dev_set:
        f = flow.get(d)
        bal = h.get("creator_balance")
        dev_rows.append({"wallet": d, "buy_usd": f["buy_usd"] if f else 0, "sell_usd": f["sell_usd"] if f else 0, "balance_tokens": bal})
        if f:
            facts.append(f"creator/dev {d[:8]}.. traded in window: bought ${f['buy_usd']:,.0f}, sold ${f['sell_usd']:,.0f}")
    if h.get("creator_balance") is not None:
        facts.append(f"creator wallet balance {h['creator_balance']:,} base units (rugcheck)" if h["creator_balance"] else "creator wallet holds zero tokens (rugcheck)")
    dev_pct = (holders_out or {}).get("dev_holding_pct")
    if dev_pct is not None:
        facts.append(f"developer holding {dev_pct:.2f}%")
    # top holders activity in window
    th_buy = sum(flow[w]["buy_usd"] for w in econ_owner if w in flow)
    th_sell = sum(flow[w]["sell_usd"] for w in econ_owner if w in flow)
    active_top = [w for w in econ_owner if w in flow]
    if active_top:
        facts.append(f"{len(active_top)} of {len(econ_owner)} top economic holders traded in the window: bought ${th_buy:,.0f}, sold ${th_sell:,.0f}")
    # large traders (not necessarily top holders)
    big = {w: f for w, f in flow.items() if (f["buy_usd"] + f["sell_usd"]) >= big_trade_usd}
    big_buy = sum(f["buy_usd"] for f in big.values()); big_sell = sum(f["sell_usd"] for f in big.values())
    net_big = big_buy - big_sell
    if big:
        facts.append(f"{len(big)} wallets with >= ${big_trade_usd:,.0f} activity: bought ${big_buy:,.0f}, sold ${big_sell:,.0f}, net ${net_big:+,.0f}")
        sellers = sorted(((f["sell_usd"] - f["buy_usd"], w) for w, f in big.items()), reverse=True)[:3]
        buyers = sorted(((f["buy_usd"] - f["sell_usd"], w) for w, f in big.items()), reverse=True)[:3]
        facts.append("largest net sellers: " + ", ".join(f"{w[:6]}.. ${v:,.0f}" for v, w in sellers if v > 0))
        facts.append("largest net buyers: " + ", ".join(f"{w[:6]}.. ${v:,.0f}" for v, w in buyers if v > 0))
    # direction classification
    total_vol = sum(f["buy_usd"] + f["sell_usd"] for f in flow.values())
    direction = "UNKNOWN"
    if big or active_top:
        ref_buy = th_buy + big_buy; ref_sell = th_sell + big_sell
        tot = ref_buy + ref_sell
        if tot:
            r = (ref_buy - ref_sell) / tot
            if r > 0.3: direction = "ACCUMULATING"
            elif r > 0.1: direction = "HOLDING"
            elif r > -0.15: direction = "SCALING_OUT" if ref_sell > 0 else "HOLDING"
            elif r > -0.5: direction = "DISTRIBUTING"
            else: direction = "EXITING"
            inferences.append(f"material-wallet net flow ratio {r:+.2f} in the observed trade window -> {direction}")
    else:
        unknowns.append("no material wallet activity in the recent trade window (window covers the last ~300 trades)")
    # pair with price and volume (Phase 8)
    chg = mk.get("chg") or {}
    c24, c6, c1 = chg.get("24h"), chg.get("6h"), chg.get("1h")
    vol = mk.get("vol") or {}
    pace6 = (vol.get("6h") * 4 / vol.get("24h")) if vol.get("6h") is not None and vol.get("24h") else None
    hc24 = (mk.get("holder_change") or {}).get("24h")
    absorption = None
    if direction in ("DISTRIBUTING", "EXITING", "SCALING_OUT"):
        if c6 is not None and c6 > -5:
            absorption = "ABSORPTION_POSSIBLE"; inferences.append("price holding while material holders sell: possible absorption by new buyers")
        elif c6 is not None and c6 <= -5 and pace6 is not None and pace6 < 0.7:
            absorption = "DISTRIBUTION_WITH_FADING_DEMAND"; inferences.append("price falling, volume fading while material holders sell: buyer interest may be gone")
        elif c24 is not None and c24 > 0:
            absorption = "STRENGTH_CONCEALS_DISTRIBUTION"; inferences.append("price up while early/large wallets distribute: strength may conceal distribution")
    elif direction in ("ACCUMULATING", "HOLDING"):
        if c6 is not None and c6 > -5 and pace6 is not None and pace6 >= 1.0:
            absorption = "CONSTRUCTIVE"; inferences.append("selling not dominant, demand/volume present while price holds: constructive")
        elif pace6 is not None and pace6 < 0.6:
            absorption = "QUIET"; inferences.append("material wallets not selling but activity is drying up; supply may be scarce but demand is not yet evident")
    if hc24 is not None:
        facts.append(f"holder count change 24h {hc24:+.2f}%")
    heur.append("a profitable early wallet is not 'smart money' on one trade; historical performance across tokens is needed and survivorship bias applies")
    heur.append("PRICE HOLDS + LARGE HOLDERS SELL -> possible absorption; PRICE FALLS + VOLUME DISAPPEARS -> loss of interest; PRICE RISES WHILE EARLY WALLETS DISTRIBUTE -> strength may conceal distribution")
    return {"large_holder_net_direction": direction, "absorption": absorption, "dev": dev_rows, "dev_holding_pct": dev_pct,
            "top_holder_buy_usd": th_buy, "top_holder_sell_usd": th_sell, "big_wallets": {w: f for w, f in list(big.items())[:25]},
            "big_net_usd": net_big, "window": [window_start, window_end], "n_trades": len(trades), "trade_window_volume_usd": total_vol,
            "price_chg_24h": c24, "price_down": (c24 or 0) < 0, "vol_ratio": pace6, "volume_collapsing": pace6 is not None and pace6 < 0.5,
            "facts": facts, "inferences": inferences, "heuristics": heur, "unknowns": unknowns}
