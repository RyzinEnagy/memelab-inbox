"""m26: portfolio-level risk for a book of memecoin positions.

Public interface:
    analyze(positions, token_data, account_size=None) -> dict

positions: [{"mint","symbol","size_usd","entry_price","current_price","invalidation_price"}]
token_data: {mint: {"narrative_tags": [...], "pools": [{"dex","quote",...}], "quotes": {"SELL": {usd: {...}}},
                    "chain": "solana", "launchpad": "pump.fun"}}

Key output fields:
    total_exposure_usd, exposure_pct_of_account, chain_concentration, memecoin_concentration,
    narrative_correlation, liquidity_exposure, ecosystem_correlation,
    aggregate_max_loss_usd, aggregate_exit_capacity_usd, liquidity_shortfall_usd,
    liquidity_adjusted_risk_usd, correlated_drawdown, effective_independent_bets, positions (per-position rows),
    facts / inferences / heuristics / unknowns
"""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from typing import Any

IMPACT_FOR_EXIT = 3.0  # percent

SCENARIO = {"sol_pct": -20.0, "memecoin_pct": -50.0, "liquidity_pct": -40.0}


def _num(x: Any) -> float | None:
    try:
        if x is None or isinstance(x, bool):
            return None
        v = float(x)
        return None if v != v else v
    except (TypeError, ValueError):
        return None


def _d(x: Any) -> dict:
    return x if isinstance(x, dict) else {}


def _hhi(weights: dict[str, float]) -> float:
    tot = sum(weights.values())
    if tot <= 0:
        return 1.0
    return sum((w / tot) ** 2 for w in weights.values())


def _exit_capacity(quotes: dict, impact_limit: float = IMPACT_FOR_EXIT) -> tuple[float | None, str | None]:
    """Largest SELL quote size whose price impact is <= impact_limit (%)."""
    sell = _d(_d(quotes).get("SELL"))
    best: float | None = None
    worst_status = None
    for k, q in sell.items():
        usd = _num(k)
        q = _d(q)
        if usd is None:
            usd = _num(q.get("usd")) or _num(q.get("size_usd"))
        if usd is None:
            continue
        status = str(q.get("status") or "OK").upper()
        imp = _num(q.get("impact"))
        if imp is not None and imp > 1.0 and imp <= 100 and impact_limit <= 1.0:
            imp /= 100.0
        if status != "OK":
            worst_status = status
            continue
        if imp is None:
            continue
        if imp <= impact_limit:
            best = usd if best is None else max(best, usd)
    return best, worst_status


def _current_value(p: dict) -> float | None:
    size = _num(p.get("size_usd"))
    ep, cp = _num(p.get("entry_price")), _num(p.get("current_price"))
    if _num(p.get("current_value_usd")) is not None:
        return _num(p.get("current_value_usd"))
    if size is None:
        return None
    if ep and cp:
        return size * cp / ep
    return size


def analyze(positions: list[dict] | None, token_data: dict | None, account_size: float | None = None) -> dict:
    positions = [p for p in positions if isinstance(p, dict)] if isinstance(positions, (list, tuple)) else []
    token_data = _d(token_data)
    account_size = _num(account_size)

    facts: list[str] = []
    inferences: list[str] = []
    heuristics: list[str] = [
        f"Exit capacity = largest SELL quote with impact <= {IMPACT_FOR_EXIT:.0f}%",
        "Liquidity-adjusted risk = max loss to invalidation + shortfall between position value and exit capacity",
        "Effective independent bets = 1 / HHI of value weights over narrative/ecosystem groups",
        f"Correlated drawdown scenario: SOL {SCENARIO['sol_pct']:.0f}%, memecoins {SCENARIO['memecoin_pct']:.0f}%, liquidity {SCENARIO['liquidity_pct']:.0f}%",
    ]
    unknowns: list[str] = []

    if not positions:
        unknowns.append("no positions supplied")
        return {
            "n_positions": 0, "total_exposure_usd": 0.0, "exposure_pct_of_account": None,
            "chain_concentration": {}, "memecoin_concentration": None, "narrative_correlation": {},
            "liquidity_exposure": {}, "ecosystem_correlation": {}, "aggregate_max_loss_usd": 0.0,
            "aggregate_exit_capacity_usd": 0.0, "liquidity_shortfall_usd": 0.0, "liquidity_adjusted_risk_usd": 0.0,
            "correlated_drawdown": None, "effective_independent_bets": 0.0, "positions": [],
            "facts": facts, "inferences": inferences, "heuristics": heuristics, "unknowns": unknowns,
        }

    rows: list[dict] = []
    total_value = 0.0
    total_max_loss = 0.0
    total_exit = 0.0
    total_shortfall = 0.0
    chain_w: dict[str, float] = defaultdict(float)
    quote_w: dict[str, float] = defaultdict(float)
    venue_w: dict[str, float] = defaultdict(float)
    launchpad_w: dict[str, float] = defaultdict(float)
    tag_w: dict[str, float] = defaultdict(float)
    tags_by_pos: dict[str, set[str]] = {}
    group_w: dict[str, float] = defaultdict(float)  # for effective bets

    for p in positions:
        mint = str(p.get("mint") or p.get("symbol") or f"pos{len(rows)}")
        sym = p.get("symbol") or mint[:6]
        td = _d(token_data.get(mint))
        value = _current_value(p)
        if value is None:
            unknowns.append(f"{sym}: size_usd missing, position excluded from exposure totals")
            value = 0.0
        cp, inv = _num(p.get("current_price")), _num(p.get("invalidation_price"))
        if cp and inv is not None and cp > 0:
            dist = max(0.0, (cp - inv) / cp)
            max_loss = value * dist
            if inv >= cp:
                inferences.append(f"{sym}: invalidation at/above current price; position already invalidated, max loss counted as 0 (exit now)")
        else:
            dist = 1.0
            max_loss = value
            unknowns.append(f"{sym}: invalidation or current price missing, max loss assumed = full position value")

        cap, bad_status = _exit_capacity(td.get("quotes"))
        if cap is None:
            if td.get("quotes"):
                unknowns.append(f"{sym}: no SELL quote within {IMPACT_FOR_EXIT:.0f}% impact ({bad_status or 'all quotes exceed limit'}), exit capacity assumed 0")
            else:
                unknowns.append(f"{sym}: no SELL quotes supplied, exit capacity assumed 0")
            cap = 0.0
        shortfall = max(0.0, value - cap)

        chain = str(td.get("chain") or p.get("chain") or "solana").lower()
        pools = [q for q in (td.get("pools") or []) if isinstance(q, dict)]
        quotes_used = {str(q.get("quote") or "SOL").upper() for q in pools} or {"SOL"}
        venues = {str(q.get("dex") or "unknown").lower() for q in pools} or {"unknown"}
        if not pools:
            unknowns.append(f"{sym}: no pools supplied, quote asset assumed SOL, venue unknown")
        launchpad = str(td.get("launchpad") or p.get("launchpad") or "unknown").lower()
        tags = {str(t).lower() for t in (td.get("narrative_tags") or []) if t}
        if not tags:
            unknowns.append(f"{sym}: no narrative tags, treated as its own narrative group")
        tags_by_pos[mint] = tags

        chain_w[chain] += value
        for q in quotes_used:
            quote_w[q] += value / len(quotes_used)
        for v in venues:
            venue_w[v] += value / len(venues)
        launchpad_w[launchpad] += value
        for t in tags:
            tag_w[t] += value / len(tags)
        # group for effective-bets: primary narrative tag + chain; untagged -> own group
        group = f"{chain}:{sorted(tags)[0] if tags else 'untagged-' + mint}"
        group_w[group] += value

        total_value += value
        total_max_loss += max_loss
        total_exit += min(cap, value)
        total_shortfall += shortfall
        rows.append({
            "mint": mint, "symbol": sym, "value_usd": round(value, 2),
            "entry_price": _num(p.get("entry_price")), "current_price": cp, "invalidation_price": inv,
            "distance_to_invalidation_pct": round(dist * 100, 2), "max_loss_usd": round(max_loss, 2),
            "exit_capacity_3pct_usd": round(cap, 2), "liquidity_shortfall_usd": round(shortfall, 2),
            "chain": chain, "quote_assets": sorted(quotes_used), "venues": sorted(venues),
            "launchpad": launchpad, "narrative_tags": sorted(tags), "group": group,
        })

    facts.append(f"{len(rows)} positions, total speculative exposure ${total_value:,.0f}")
    exposure_pct = None
    if account_size and account_size > 0:
        exposure_pct = total_value / account_size * 100
        facts.append(f"Exposure is {exposure_pct:.1f}% of account ${account_size:,.0f}")
        if exposure_pct > 20:
            inferences.append("Speculative exposure above 20% of account: a correlated drawdown is an account-level event")
    else:
        unknowns.append("account_size not supplied: exposure as % of account unknown")

    def _shares(w: dict[str, float]) -> dict[str, float]:
        return {k: round(v / total_value * 100, 1) for k, v in sorted(w.items(), key=lambda kv: -kv[1])} if total_value else {}

    chain_conc = _shares(chain_w)
    top_chain = max(chain_w.items(), key=lambda kv: kv[1])[0] if chain_w else None
    facts.append("Chain concentration: " + ", ".join(f"{k} {v}%" for k, v in chain_conc.items()))
    memecoin_conc = 100.0  # every position in this book is a memecoin by construction
    facts.append("Memecoin concentration: 100% of this book")

    # narrative correlation: pairwise shared tags
    pair_rows = []
    n_corr_pairs = 0
    for a, b in combinations(rows, 2):
        shared = set(a["narrative_tags"]) & set(b["narrative_tags"])
        same_launchpad = a["launchpad"] == b["launchpad"] and a["launchpad"] != "unknown"
        same_quote = bool(set(a["quote_assets"]) & set(b["quote_assets"]))
        same_chain = a["chain"] == b["chain"]
        corr_points = len(shared) * 2 + same_launchpad + same_quote + same_chain
        if shared or (same_chain and same_quote):
            n_corr_pairs += 1
        pair_rows.append({"a": a["symbol"], "b": b["symbol"], "shared_tags": sorted(shared),
                          "same_chain": same_chain, "same_quote": same_quote, "same_launchpad": same_launchpad,
                          "correlation_points": corr_points})
    n_pairs = len(pair_rows)
    narrative_corr = {
        "tag_exposure_pct": _shares(tag_w),
        "pairs": pair_rows,
        "pairs_sharing_a_tag": sum(1 for r in pair_rows if r["shared_tags"]),
        "n_pairs": n_pairs,
    }
    if n_pairs:
        facts.append(f"{narrative_corr['pairs_sharing_a_tag']} of {n_pairs} position pairs share a narrative tag")

    liq_exposure = {
        "quote_asset_pct": _shares(quote_w),
        "venue_pct": _shares(venue_w),
        "shared_quote_asset": max(quote_w.items(), key=lambda kv: kv[1])[0] if quote_w else None,
    }
    sol_share = quote_w.get("SOL", 0.0) / total_value * 100 if total_value else 0.0
    facts.append(f"{sol_share:.0f}% of exposure is quoted against SOL")
    if sol_share > 60:
        inferences.append("Common liquidity exposure: most positions exit into SOL, so SOL weakness hits every position's exit price and liquidity simultaneously")

    eco_corr = {"launchpad_pct": _shares(launchpad_w), "chain_pct": chain_conc}

    # effective independent bets
    hhi_group = _hhi(group_w)
    eff_bets = round(1.0 / hhi_group, 2) if hhi_group > 0 else 0.0
    hhi_pos = _hhi({r["mint"]: r["value_usd"] for r in rows})
    eff_pos = round(1.0 / hhi_pos, 2) if hhi_pos > 0 else 0.0
    facts.append(f"Effective independent bets: {eff_bets} (by narrative/ecosystem group) vs {eff_pos} by position weight")
    if top_chain and chain_conc.get(top_chain, 0) >= 80:
        inferences.append(
            f"{len(rows)} highly correlated {top_chain} memecoins are NOT {len(rows)} independent risks. "
            f"Grouping by narrative and ecosystem, this book behaves like roughly {eff_bets} independent bet(s)."
        )

    # correlated drawdown scenario
    scen_value_loss = 0.0
    scen_loss_capped = 0.0
    scen_shortfall = 0.0
    for r in rows:
        v = r["value_usd"]
        # memecoin shock is applied in quote-asset terms; a SOL-quoted token that falls 50% in SOL
        # falls further in USD when SOL itself falls 20% (0.5 * 0.8 = 0.4 of starting USD value)
        sol_quoted = "SOL" in r["quote_assets"]
        drop = 1 + SCENARIO["memecoin_pct"] / 100
        if sol_quoted:
            drop *= 1 + SCENARIO["sol_pct"] / 100
        loss = v * (1 - drop)
        # invalidation should cap the loss if honored, but gaps and illiquidity mean the scenario assumes slippage past it
        capped = min(loss, r["max_loss_usd"]) if r["max_loss_usd"] > 0 else loss
        scen_value_loss += loss
        scen_loss_capped += capped
        cap_after = r["exit_capacity_3pct_usd"] * (1 + SCENARIO["liquidity_pct"] / 100)
        value_after = v * drop
        scen_shortfall += max(0.0, value_after - cap_after)
    correlated_drawdown = {
        "scenario": SCENARIO,
        "unhedged_mark_to_market_loss_usd": round(scen_value_loss, 2),
        "loss_if_invalidations_honored_usd": round(scen_loss_capped, 2),
        "post_shock_liquidity_shortfall_usd": round(scen_shortfall, 2),
        "worst_case_usd": round(scen_value_loss + scen_shortfall, 2),
        "worst_case_pct_of_account": round((scen_value_loss + scen_shortfall) / account_size * 100, 2) if account_size else None,
    }
    inferences.append(
        f"Correlated drawdown: mark-to-market loss ${scen_value_loss:,.0f} if all positions fall together; "
        f"${scen_loss_capped:,.0f} only if every invalidation is honored, which is unlikely when liquidity is also down 40% "
        f"(post-shock exit shortfall ${scen_shortfall:,.0f})"
    )

    liquidity_adjusted = total_max_loss + total_shortfall
    facts.append(f"Aggregate max loss to invalidation ${total_max_loss:,.0f}; aggregate exit capacity ${total_exit:,.0f}; "
                 f"shortfall ${total_shortfall:,.0f}; liquidity-adjusted portfolio risk ${liquidity_adjusted:,.0f}")
    if total_shortfall > 0:
        inferences.append("Displayed position values exceed what the SELL quotes can absorb at 3% impact: part of the book cannot be exited at displayed prices")
    if account_size and liquidity_adjusted / account_size > 0.05:
        inferences.append(f"Liquidity-adjusted risk is {liquidity_adjusted/account_size*100:.1f}% of account, above a 5% book-level risk budget")

    return {
        "n_positions": len(rows),
        "total_exposure_usd": round(total_value, 2),
        "exposure_pct_of_account": round(exposure_pct, 2) if exposure_pct is not None else None,
        "chain_concentration": chain_conc,
        "memecoin_concentration": memecoin_conc,
        "narrative_correlation": narrative_corr,
        "liquidity_exposure": liq_exposure,
        "ecosystem_correlation": eco_corr,
        "aggregate_max_loss_usd": round(total_max_loss, 2),
        "aggregate_exit_capacity_usd": round(total_exit, 2),
        "liquidity_shortfall_usd": round(total_shortfall, 2),
        "liquidity_adjusted_risk_usd": round(liquidity_adjusted, 2),
        "liquidity_adjusted_risk_pct_of_account": round(liquidity_adjusted / account_size * 100, 2) if account_size else None,
        "correlated_drawdown": correlated_drawdown,
        "effective_independent_bets": eff_bets,
        "effective_bets_by_position_weight": eff_pos,
        "hhi_group": round(hhi_group, 4),
        "positions": rows,
        "facts": facts,
        "inferences": inferences,
        "heuristics": heuristics,
        "unknowns": unknowns,
    }
