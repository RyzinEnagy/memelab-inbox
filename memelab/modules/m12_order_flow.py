"""12_ORDER_FLOW: buy/sell volume, imbalance, unique participants, trade-size distribution, aggression, absorption."""
from __future__ import annotations

import statistics
from collections import Counter
from typing import Any


def analyze(bundle: dict[str, Any]) -> dict[str, Any]:
    mk = bundle.get("market") or {}
    trades = bundle.get("trades") or []
    facts, inferences, unknowns, heur = [], [], [], []
    out: dict[str, Any] = {}
    bv, sv = mk.get("buy_vol_24h"), mk.get("sell_vol_24h")
    if bv is not None and sv is not None and (bv + sv):
        out["buy_sell_vol_ratio"] = bv / sv if sv else None
        facts.append(f"24h buy volume ${bv:,.0f} vs sell volume ${sv:,.0f} (ratio {bv/sv:.2f})" if sv else f"24h buy ${bv:,.0f}, no sells")
    obv, osv = mk.get("organic_buy_vol_24h"), mk.get("organic_sell_vol_24h")
    if obv is not None and osv is not None and bv is not None and sv is not None and (bv + sv):
        share = (obv + osv) / (bv + sv)
        out["organic_share"] = share
        facts.append(f"jupiter 'organic' volume share {share:.1%} of 24h volume (provider methodology: filters bot/wash-like flow)")
        if share < 0.05:
            inferences.append("very low organic share: most volume is likely bot/arbitrage/wash-like under the provider's method")
    nb = mk.get("net_buyers") or {}
    for w in ("1h", "24h"):
        if nb.get(w) is not None:
            out[f"net_buyers_{'h'+w[:-1] if w.endswith('h') else w}"] = nb[w]
    if nb.get("24h") is not None:
        facts.append(f"net buyers 24h {nb['24h']:+d}; 1h {nb.get('1h')}; traders 24h {mk.get('num_traders_24h')}" if nb.get("1h") is not None else f"net buyers 24h {nb['24h']:+d}")
    if mk.get("num_organic_buyers_24h") is not None and mk.get("num_traders_24h"):
        out["buyer_quality"] = min(mk["num_organic_buyers_24h"] / max(mk["num_traders_24h"], 1) * 5, 1.0)
        facts.append(f"organic buyers 24h {mk['num_organic_buyers_24h']} of {mk['num_traders_24h']} traders")
    tx = mk.get("txns") or {}
    for w in ("1h", "24h"):
        t = tx.get(w)
        if t and t[0] is not None and t[1] is not None:
            tot = t[0] + t[1]
            if tot:
                out[f"tx_imbalance_{w}"] = (t[0] - t[1]) / tot
                facts.append(f"{w}: {t[0]} buys / {t[1]} sells (imbalance {(t[0]-t[1])/tot:+.2f})")
    # trade-size distribution and aggression from recent trades
    if trades:
        usd = [t[4] or 0 for t in trades]
        buys = [t for t in trades if t[2] == "buy"]; sells = [t for t in trades if t[2] == "sell"]
        out["recent_trades"] = len(trades); out["recent_buy_usd"] = sum(t[4] or 0 for t in buys); out["recent_sell_usd"] = sum(t[4] or 0 for t in sells)
        out["recent_unique_buyers"] = len({t[1] for t in buys}); out["recent_unique_sellers"] = len({t[1] for t in sells})
        med = statistics.median(usd) if usd else 0
        p90 = sorted(usd)[int(0.9 * (len(usd) - 1))] if usd else 0
        out["trade_size_median_usd"] = med; out["trade_size_p90_usd"] = p90; out["trade_size_max_usd"] = max(usd) if usd else 0
        facts.append(f"recent window: {len(buys)} buys (${out['recent_buy_usd']:,.0f}, {out['recent_unique_buyers']} wallets) vs {len(sells)} sells (${out['recent_sell_usd']:,.0f}, {out['recent_unique_sellers']} wallets); median trade ${med:,.0f}, p90 ${p90:,.0f}, max ${max(usd):,.0f}")
        # repeated aggressive participants
        cb = Counter(t[1] for t in buys); cs = Counter(t[1] for t in sells)
        rep_b = [(w, n) for w, n in cb.most_common(3) if n >= 5]; rep_s = [(w, n) for w, n in cs.most_common(3) if n >= 5]
        if rep_b:
            facts.append("repeated buyers: " + ", ".join(f"{w[:6]}.. x{n}" for w, n in rep_b))
        if rep_s:
            facts.append("repeated sellers: " + ", ".join(f"{w[:6]}.. x{n}" for w, n in rep_s))
        # cascade / absorption in sequence: large sells followed by price recovery?
        from datetime import datetime, timezone
        cutoff = (bundle.get("observed_at") or 0) - 6 * 3600
        def _ts(t):
            try:
                return datetime.fromisoformat(str(t[0]).replace("Z", "+00:00")).timestamp()
            except Exception:
                return 0
        recent = [t for t in trades if _ts(t) >= cutoff] or trades
        big_sells = [t for t in recent if t[2] == "sell" and (t[4] or 0) >= max(p90, 1000)]
        if big_sells and len(recent) > 20:
            prices = [t[5] for t in recent if t[5]]
            if prices:
                first_p, last_p = prices[0], prices[-1]
                drift = (last_p / first_p - 1) * 100 if first_p else None
                if drift is not None:
                    out["window_price_drift_pct"] = drift
                    if drift > -2 and sum(t[4] or 0 for t in big_sells) > 0.3 * out["recent_sell_usd"]:
                        inferences.append(f"{len(big_sells)} large sells were absorbed with price drift {drift:+.1f}% across the window: absorption")
                    elif drift < -8:
                        inferences.append(f"large sells with price drift {drift:+.1f}%: cascade / supply overwhelming demand in the window")
        # same-wallet buy and sell (possible wash / bot) share
        both = set(cb) & set(cs)
        if both:
            wash_usd = sum((t[4] or 0) for t in trades if t[1] in both)
            out["two_sided_wallet_share"] = wash_usd / max(sum(usd), 1)
            facts.append(f"{len(both)} wallets both bought and sold in the window, {out['two_sided_wallet_share']:.0%} of window volume (bots/arb/wash candidates)")
    else:
        unknowns.append("no recent trade list")
    heur.append("every trade has a counterparty; 'buy volume' is the provider's taker-side label, so look for changes in aggression, not the label itself")
    return {**out, "facts": facts, "inferences": inferences, "heuristics": heur, "unknowns": unknowns}
