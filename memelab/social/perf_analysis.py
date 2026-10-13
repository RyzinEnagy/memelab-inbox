"""Phase 10: from an engine run to a result: positions, realized P&L, costs, open inventory (mark-to-market vs executable proceeds), coverage,
reconciliation checks, statistics, drawdown, sensitivities and the score gate. Pure; see perf_core.py for the accounting rules.

Everything that leaves this module is JSON-safe: decimals are strings rounded to 12 places, so a result hashes the same on every machine.
"""
from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Any

from . import perf_core as C
from .perf_core import DEFAULT_POLICY, OFFBOOK_KINDS, SALE_KINDS, ZERO, _q, canonical_json, dec, merge_policy, run_engine, sha

LIMITS = [
    "Wallet-level only. A wallet is not a person; other wallets, exchange flows and off-chain activity are not in the data.",
    "Amounts are the provider's legs. Decimals cannot be re-verified from stored events; a ledger with raw amounts and decimals is checked.",
    "Liquidity positions are capital moves. Fees earned and impermanent loss are not computed, and LP tokens are not valued.",
    "Prices and quotes are supplied observations (estimates). They are labelled with their source and never fetched by the accounting.",
    "Drawdown uses event-time points only, so it is a lower bound of the true drawdown.",
    "A provider's P&L or leaderboard figure is never an input. It can be compared (compare_provider_estimates) and is labelled an estimate.",
]


# ---------- positions ----------

def _sum(xs, default=ZERO):
    t = default
    for x in xs:
        t += x
    return t


def position_rows(R: C.Run, as_of: float) -> list[dict]:
    rows = []
    for p in R.positions:
        pid, asset = p["id"], p["asset"]
        slices = [s for s in R.slices if s["position"] == pid and s["bucket"] == "TRADING"]
        lots = [l for l in R.lots if l.position == pid and l.bucket == "TRADING"]
        open_qty = _sum(l.qty for l in lots)
        offbook_qty = _sum(pe["qty_rem"] for pe in R.pool_out if pe["position"] == pid)
        real = [s for s in slices if s["kind"] in SALE_KINDS]
        sold = [s for s in real if s["kind"] in ("SALE", "TOKEN_SWAP")]
        status = "OPEN" if open_qty > 0 else ("OFF_BOOK" if offbook_qty > 0 else ("CLOSED" if sold else "EMPTY"))
        end = p.get("closed_at") if status == "CLOSED" else as_of
        reasons: dict[str, list[str]] = {"USD": [], "NATIVE": []}
        both = []
        if status != "CLOSED":
            both.append(f"STATUS_{status}")
        for c in R.contam.get(asset, []):
            if p["opened_at"] <= c["time"] <= (end if end is not None else as_of):
                both.append("CONTAMINATED_" + c["reason"])
        for l in lots:      # an unpriced USD basis does not stop the native-unit view, which needs no price; every other unknown basis stops both
            if l.basis_status != "KNOWN":
                (reasons["USD"] if l.basis_status == "UNKNOWN_UNPRICED" else both).append("LOT_BASIS_" + l.basis_status)
        fees = [f for f in R.fees if f["position"] == pid]
        row = {"position": pid, "asset": asset, "status": status, "opened_at": p["opened_at"], "closed_at": p.get("closed_at") if status == "CLOSED" else None, "entries": sorted(set(p["entries"])),
               "open_qty": open_qty, "offbook_qty": offbook_qty, "units": {}}
        for u in ("USD", "NATIVE"):
            bk = "basis" if u == "USD" else "basis_native"
            pk = "proceeds" if u == "USD" else "proceeds_native"
            basis_known = all(s[bk] is not None for s in real) and bool(real)
            proceeds_known = all(s[pk] is not None for s in sold) and bool(sold)
            cost = _sum(s[bk] for s in real if s[bk] is not None)
            proceeds = _sum(s[pk] for s in real if s[pk] is not None)
            if u == "USD":
                fee_known = all(f["usd"] is not None for f in fees)
                fee_val = _sum(f["usd"] for f in fees if f["usd"] is not None)
            else:
                fee_known = all(f["native"] is not None for f in fees)
                fee_val = _sum(f["native"] for f in fees if f["native"] is not None)
            rs = list(both) + reasons[u]
            if not basis_known:
                rs.append("BASIS_UNKNOWN")
            if not proceeds_known:
                rs.append("PROCEEDS_UNKNOWN")
            if not fee_known:
                rs.append("FEE_UNKNOWN")
            realized = proceeds - cost
            row["units"][u] = {"cost": cost if basis_known else None, "proceeds": proceeds if proceeds_known else None,
                               "realized_gross": realized if (basis_known and proceeds_known) else None, "fees_known": fee_val, "fees_complete": fee_known,
                               "net": (realized - fee_val) if (basis_known and proceeds_known and fee_known) else None,
                               "return": ((realized - fee_val) / cost) if (basis_known and proceeds_known and fee_known and cost > 0) else None,
                               "in_sample": status == "CLOSED" and not rs and cost > 0, "exclusion_reasons": sorted(set(rs))}
        row["hold_s"] = (p["closed_at"] - p["opened_at"]) if status == "CLOSED" and p.get("closed_at") is not None else None
        rows.append(row)
    return rows


def metrics(rows: list[dict], unit: str, pol: dict) -> dict:
    """Trade statistics for one unit. A trade is a closed position; only in-sample positions count. Definitions are in the result."""
    s = [r for r in rows if r["units"][unit]["in_sample"]]
    n = len(s)
    out: dict[str, Any] = {"unit": unit, "sample_size": n, "positions_total": len(rows),
                           "definitions": {"trade": "one closed position: first swap-buy to flat, every disposal a sale at known proceeds from lots of known basis, fees known",
                                           "win": "net P&L after known fees strictly greater than zero (break-even is not a win)",
                                           "return": "net P&L / cost basis of the position",
                                           "profit_share_from_biggest_winner": "largest position net P&L / sum of positive position net P&Ls",
                                           "return_excluding_biggest_winner": "(sum of net P&L - biggest winner) / (sum of cost - its cost), capital weighted"}}
    if n == 0:
        out.update({"wins": 0, "losses": 0, "breakeven": 0, "win_rate": None, "win_rate_interval_95": None, "median_return": None, "aggregate_return": None,
                    "total_net": None, "total_cost": None, "profit_share_from_biggest_winner": None, "return_excluding_biggest_winner": None, "biggest_winner": None})
        return out
    nets = [r["units"][unit]["net"] for r in s]
    rets = [r["units"][unit]["return"] for r in s]
    costs = [r["units"][unit]["cost"] for r in s]
    wins = sum(1 for x in nets if x > 0)
    losses = sum(1 for x in nets if x < 0)
    best = max(range(n), key=lambda i: (nets[i], -s[i]["position"]))
    pos_sum = _sum(x for x in nets if x > 0)
    total_net, total_cost = _sum(nets), _sum(costs)
    iv = C.wilson(wins, n)
    rest_cost = total_cost - costs[best]
    out.update({"wins": wins, "losses": losses, "breakeven": n - wins - losses, "win_rate": Decimal(wins) / n, "win_rate_interval_95": [iv[0], iv[1]] if iv else None,
                "median_return": C._median(rets), "aggregate_return": total_net / total_cost if total_cost > 0 else None, "total_net": total_net, "total_cost": total_cost,
                "profit_share_from_biggest_winner": (nets[best] / pos_sum) if pos_sum > 0 and nets[best] > 0 else None,
                "return_excluding_biggest_winner": ((total_net - nets[best]) / rest_cost) if n >= 2 and rest_cost > 0 else None,
                "biggest_winner": {"position": s[best]["position"], "asset": s[best]["asset"], "net": nets[best], "return": rets[best]}})
    return out


def trade_counts(R: C.Run, rows: list[dict], L: C.Ledger) -> dict:
    cnt = R.counts
    return {"entries_input": len(L.entries) + len(L.rejects), "entries_accounted": cnt.get("entries", 0), "rejected": len(L.rejects), "buys": cnt.get("buys", 0), "sells": cnt.get("sells", 0),
            "token_to_token_swaps": cnt.get("token_swaps", 0), "quote_conversions": cnt.get("quote_conversions", 0), "transfers_in": cnt.get("transfers_in", 0),
            "transfers_out": cnt.get("transfers_out", 0), "airdrops": cnt.get("airdrops", 0), "lp_deployed_legs": cnt.get("lp_deployed_legs", 0), "failed": cnt.get("failed", 0),
            "unclassified": cnt.get("unclassified", 0), "unsupported_swaps": cnt.get("unsupported_swaps", 0), "internal_transfer_pairs": R.internal_pairs,
            "returns_matched": cnt.get("returns_matched", 0), "positions": {k: sum(1 for r in rows if r["status"] == k) for k in ("CLOSED", "OPEN", "OFF_BOOK", "EMPTY")},
            "note": "transfers, liquidity moves and failed transactions are never counted as trades"}


# ---------- realized, costs ----------

def realized_block(R: C.Run) -> dict:
    t = {"known_pnl": ZERO, "cost": ZERO, "proceeds": ZERO, "known_slices": 0, "unknown_slices": 0, "unknown_qty_by_asset": {}}
    nat = {"pnl": ZERO, "cost": ZERO, "proceeds": ZERO, "slices": 0}
    unk = {"proceeds": ZERO, "slices": 0, "unpriced_slices": 0}
    air = {"proceeds": ZERO, "slices": 0, "unpriced_slices": 0}
    for s in R.slices:
        if s["kind"] not in SALE_KINDS:
            continue
        if s["bucket"] == "TRADING":
            if s["basis"] is not None and s["proceeds"] is not None:
                t["known_pnl"] += s["proceeds"] - s["basis"]
                t["cost"] += s["basis"]
                t["proceeds"] += s["proceeds"]
                t["known_slices"] += 1
            else:
                t["unknown_slices"] += 1
            if s["basis_native"] is not None and s["proceeds_native"] is not None:
                nat["pnl"] += s["proceeds_native"] - s["basis_native"]
                nat["cost"] += s["basis_native"]
                nat["proceeds"] += s["proceeds_native"]
                nat["slices"] += 1
        elif s["bucket"] == "AIRDROP":
            air["slices"] += 1
            if s["proceeds"] is None:
                air["unpriced_slices"] += 1
            else:
                air["proceeds"] += s["proceeds"]
        else:
            unk["slices"] += 1
            if s["proceeds"] is None:
                unk["unpriced_slices"] += 1
            else:
                unk["proceeds"] += s["proceeds"]
    off = {}
    for kind in OFFBOOK_KINDS:
        pes = [pe for pe in R.pool_out if pe["kind"] == kind]
        off[kind] = {"qty_out": _sum(pe["qty"] for pe in pes), "qty_not_returned": _sum(pe["qty_rem"] for pe in pes),
                     "basis_not_returned_usd": _sum(pe["basis"] for pe in pes if pe["basis"] is not None), "unknown_basis_entries": sum(1 for pe in pes if pe["basis"] is None and pe["qty_rem"] > 0)}
    return {"trading_known": {"realized_pnl_usd": t["known_pnl"], "cost_basis_usd": t["cost"], "proceeds_usd": t["proceeds"], "slices": t["known_slices"],
                              "slices_with_unknown_basis_or_proceeds": t["unknown_slices"], "scope": "lots bought by swap, basis and proceeds both known, before fees"},
            "trading_native_units": {"realized_pnl_native": nat["pnl"], "cost_native": nat["cost"], "proceeds_native": nat["proceeds"], "slices": nat["slices"],
                                     "scope": "slices whose cost and proceeds were both paid in the native coin: needs no price"},
            "unknown_basis_proceeds": {"proceeds_usd": unk["proceeds"], "slices": unk["slices"], "unpriced_slices": unk["unpriced_slices"],
                                       "note": "tokens that arrived by transfer or from before the visible history: proceeds are real, but no gain or loss is computed"},
            "airdrop_proceeds": {"proceeds_usd": air["proceeds"], "slices": air["slices"], "unpriced_slices": air["unpriced_slices"],
                                 "note": "lots an analyst marked AIRDROP; basis zero by convention; kept out of trading performance"},
            "off_book": off}


def costs_block(R: C.Run) -> dict:
    fees = R.fees
    attributed = [f for f in fees if f["position"] is not None]
    return {"fee_entries": len(fees), "native_known": _sum(f["native"] for f in fees if f["native"] is not None), "usd_known": _sum(f["usd"] for f in fees if f["usd"] is not None),
            "usd_known_attributed_to_positions": _sum(f["usd"] for f in attributed if f["usd"] is not None), "usd_known_unattributed": _sum(f["usd"] for f in fees if f["position"] is None and f["usd"] is not None),
            "amount_unknown": sum(1 for f in fees if f["status"].startswith("UNKNOWN")), "usd_unpriced": sum(1 for f in fees if f["native"] is not None and f["usd"] is None),
            "payer_unknown": R.counts.get("fee_payer_unknown", 0),
            "transfer_tax_basis_usd": _sum(s["basis"] for s in R.slices if s["kind"] == "TRANSFER_TAX" and s["basis"] is not None),
            "dust_written_off_basis_usd": _sum(s["basis"] for s in R.slices if s["kind"] == "DUST_WRITE_OFF" and s["basis"] is not None),
            "note": "network fees are not added to lot cost; they are listed here and subtracted in position net P&L. Slippage and price impact are inside the swap legs."}


# ---------- open inventory ----------

def liquidation(asset: str, qty: Decimal, mark: Decimal | None, obs: dict | None, as_of: float, pol: dict) -> dict:
    """Estimated proceeds of selling `qty` now, from a supplied sell quote. Never extrapolates depth it was not shown; a missing quote is UNKNOWN, not zero."""
    if obs is None:
        return {"status": "NO_QUOTE", "value": None, "age_s": None, "detail": "no sell quote was supplied"}
    age = as_of - obs["t"]
    if age > float(pol["quote_max_age_s"]):
        return {"status": "STALE_QUOTE", "value": None, "age_s": age, "detail": f"latest quote is {int(age)} s old"}
    if obs["kind"] == "NO_ROUTE":
        return {"status": "UNEXITABLE", "value": ZERO, "age_s": age, "detail": str(obs.get("detail") or "no route to sell was observed"), "source": obs["source"]}
    if obs["kind"] == "EXEC_QUOTE":
        if qty <= obs["amount_in"]:
            return {"status": "QUOTED_PRORATA", "value": obs["usd_out"] * qty / obs["amount_in"], "age_s": age, "source": obs["source"],
                    "detail": "scaled down from a larger quoted sale; a smaller sale usually does at least as well, so this is a lower bound"}
        return {"status": "QUOTED_PARTIAL", "value": obs["usd_out"], "age_s": age, "source": obs["source"],
                "detail": f"the quote covers {_q(obs['amount_in'])} of {_q(qty)} units; the rest is not valued (lower bound)"}
    from ..modules import _common as M     # the lab's own reading of Jupiter-style SELL quotes: sizes in dollars, impact as a fraction or percent
    if mark is None:
        return {"status": "NO_MARK_TO_SIZE", "value": None, "age_s": age, "detail": "an impact curve needs a mark to size the sale"}
    size = qty * mark
    pts = M.parse_quote_side(obs["sell"])
    imp, flag = M.interp_impact(pts, float(size))
    if imp is None:
        return {"status": "NO_QUOTE", "value": None, "age_s": age, "detail": "the quotes could not be read"}
    if imp == float("inf"):
        return {"status": "UNEXECUTABLE_AT_SIZE", "value": ZERO, "age_s": age, "source": obs["source"], "detail": "a quote at this size failed; valued at zero (lower bound)"}
    val = max(ZERO, size * (1 - dec(repr(imp)) / 100))
    return {"status": "IMPACT_CURVE_" + flag.upper(), "value": val, "age_s": age, "source": obs["source"], "detail": f"price impact {imp:.4g}% at {_q(size, 2)} USD ({flag})"}


def inventory_block(R: C.Run, as_of: float, pol: dict) -> dict:
    book, rows = R.book, []
    for asset in sorted({l.asset for l in R.lots if l.qty > 0}):
        ls = [l for l in R.lots if l.asset == asset and l.qty > 0]
        qty = _sum(l.qty for l in ls)
        known = [l for l in ls if l.bucket == "TRADING" and l.cost is not None]
        kq, kb = _sum(l.qty for l in known), _sum(l.cost for l in known)
        other = [l for l in ls if l not in known]
        m = book.latest_mid(asset, as_of)
        age = (as_of - m["t"]) if m else None
        mark_status = "NO_PRICE" if m is None else ("STALE" if age > float(pol["mtm_max_age_s"]) else "FRESH")
        mark = m["usd"] if m else None
        mtm = qty * mark if mark_status == "FRESH" else None
        liq = liquidation(asset, qty, mark if mark_status == "FRESH" else None, book.latest_exec(asset, as_of), as_of, pol)
        kmtm = kq * mark if mark_status == "FRESH" else None
        kliq = (liq["value"] * kq / qty) if liq["value"] is not None and qty > 0 else None
        rows.append({"asset": asset, "qty_open": qty, "qty_known_basis": kq, "basis_known_usd": kb, "qty_other": qty - kq,
                     "other_buckets": sorted({l.bucket + ":" + l.basis_status for l in other}),
                     "mark": {"status": mark_status, "price_usd": mark, "age_s": age, "source": m["source"] if m else None}, "mtm_value_usd": mtm,
                     "liquidation": {**liq, "value": liq["value"]}, "known_basis_mtm_value_usd": kmtm, "known_basis_liquidation_value_usd": kliq,
                     "unrealized_mtm_usd": (kmtm - kb) if (kmtm is not None and kq > 0) else None, "unrealized_executable_usd": (kliq - kb) if (kliq is not None and kq > 0) else None,
                     "mtm_minus_executable_usd": (kmtm - kliq) if (kmtm is not None and kliq is not None) else None})
    with_basis = [r for r in rows if r["qty_known_basis"] > 0]
    return {"as_of": as_of, "assets": rows,
            "unrealized_mtm_usd": _sum(r["unrealized_mtm_usd"] for r in with_basis if r["unrealized_mtm_usd"] is not None),
            "unrealized_executable_usd": _sum(r["unrealized_executable_usd"] for r in with_basis if r["unrealized_executable_usd"] is not None),
            "mtm_minus_executable_usd": _sum(r["mtm_minus_executable_usd"] for r in with_basis if r["mtm_minus_executable_usd"] is not None),
            "assets_with_known_basis": len(with_basis),
            "assets_without_mark": sum(1 for r in with_basis if r["unrealized_mtm_usd"] is None),
            "assets_without_executable_estimate": sum(1 for r in with_basis if r["unrealized_executable_usd"] is None),
            "basis_without_mark_usd": _sum(r["basis_known_usd"] for r in with_basis if r["unrealized_mtm_usd"] is None),
            "basis_without_executable_estimate_usd": _sum(r["basis_known_usd"] for r in with_basis if r["unrealized_executable_usd"] is None),
            "open_qty_of_unknown_basis_assets": sum(1 for r in rows if r["qty_other"] > 0),
            "off_book_not_valued": [{"asset": pe["asset"], "kind": pe["kind"], "qty": pe["qty_rem"], "counterparty_or_pool": pe["key"]} for pe in R.pool_out if pe["qty_rem"] > 0],
            "notes": ["unrealized P&L covers only open lots of known basis; open inventory of unknown basis is shown but has no gain or loss",
                      "mark-to-market uses the last supplied price; executable value uses a supplied sell quote and is a lower bound; the gap between them is shown, never hidden",
                      "a missing quote is UNKNOWN. Only an observed no-route or failed quote is valued at zero"]}


# ---------- coverage, reconstruction status ----------

def coverage_block(R: C.Run, L: C.Ledger, rows: list[dict], realized: dict, pol: dict) -> dict:
    cin = L.coverage_in or {}
    hs = cin.get("history", "UNKNOWN")
    if hs not in ("DECLARED_COMPLETE", "PLAUSIBLY_COMPLETE", "TRUNCATED", "UNKNOWN"):
        raise ValueError("coverage.history must be DECLARED_COMPLETE, PLAUSIBLY_COMPLETE, TRUNCATED or UNKNOWN")
    times = [e["time"] for e in L.entries]
    gaps = [dict(g, source="input") for g in (cin.get("gaps") or [])]
    if hs != "DECLARED_COMPLETE":
        gaps.append({"from": None, "to": min(times) if times else None, "reason": "earlier history is not shown to be covered", "source": "derived"})
    cnt = R.counts
    needing = cnt.get("buys", 0) + cnt.get("sells", 0) + cnt.get("token_swaps", 0)
    unpriced = cnt.get("unpriced_buys", 0) + cnt.get("unpriced_sells", 0) + cnt.get("unpriced_token_swaps", 0)
    sold = [s for s in R.slices if s["kind"] in ("SALE", "TOKEN_SWAP")]
    val_all = _sum(s["proceeds"] for s in sold if s["proceeds"] is not None)
    val_known = _sum(s["proceeds"] for s in sold if s["proceeds"] is not None and s["bucket"] == "TRADING" and s["basis"] is not None)
    by_slices = (Decimal(sum(1 for s in sold if s["bucket"] == "TRADING" and s["basis"] is not None)) / len(sold)) if sold else None
    fee_unknown = sum(1 for f in R.fees if f["status"].startswith("UNKNOWN") or f["usd"] is None)
    total_in = len(L.entries) + len(L.rejects)
    bad = cnt.get("unclassified", 0) + cnt.get("unsupported_swaps", 0) + len(L.rejects)
    return {"history": {"status": hs, "evidence": cin.get("evidence"), "first_entry_time": min(times) if times else None, "last_entry_time": max(times) if times else None,
                        "span_days": ((max(times) - min(times)) / 86400) if times else None, "gaps": gaps, "opening_lots_from_missing_history": cnt.get("shortfall_lots", 0),
                        "assets_with_missing_history": sorted({l.asset for l in R.synthetic_lots}), "fetch_notes": cin.get("fetch_notes") or [],
                        "note": "a transaction list read newest-first up to a limit starts at the limit, not at the wallet's first transaction, unless the provider shows it was exhausted"},
            "prices": {"entries_needing_a_price": needing, "unpriced": unpriced, "fraction_priced": (Decimal(needing - unpriced) / needing) if needing else None,
                       "entries_using_assumed_stable_peg": cnt.get("peg_assumed_entries", 0)},
            "fees": {"fee_entries": len(R.fees), "unknown_or_unpriced": fee_unknown, "unknown_share": (Decimal(fee_unknown) / len(R.fees)) if R.fees else None},
            "basis": {"share_of_disposed_value_with_known_basis": (val_known / val_all) if val_all > 0 else None, "share_of_disposals_with_known_basis": by_slices,
                      "disposed_value_usd": val_all},
            "classification": {"entries_excluded_or_unclassified": bad, "share": (Decimal(bad) / total_in) if total_in else None},
            "wallets": L.wallets, "group": L.group}


def reconstruction(R: C.Run, L: C.Ledger, rows: list[dict], cov: dict, checks: list[dict], inv: dict, realized: dict) -> dict:
    reasons, cnt = [], R.counts
    trading = cnt.get("buys", 0) + cnt.get("sells", 0) + cnt.get("token_swaps", 0)
    blocking = []
    if trading == 0:
        blocking.append("no swap could be accounted for")
    if any(c["status"] == "FAIL" for c in checks):
        blocking.append("a reconciliation check failed: " + ", ".join(c["check"] for c in checks if c["status"] == "FAIL"))
    if cov["history"]["status"] != "DECLARED_COMPLETE":
        reasons.append(f"history coverage is {cov['history']['status']}: earlier transactions may exist that are not in the ledger")
    if cnt.get("shortfall_lots"):
        reasons.append(f"{cnt['shortfall_lots']} disposal(s) exceeded the inventory the ledger can explain; an opening lot of unknown basis was added (missing earlier history or a unit error)")
    unk = [l for l in R.lots if l.basis_status.startswith("UNKNOWN") and l.origin != "PRIOR_HISTORY"]
    if unk:
        reasons.append(f"{len(unk)} lot(s) of unknown basis (transfers in, unpriced buys or liquidity excess): sales from them show proceeds but no gain or loss")
    if cnt.get("unpriced_buys", 0) + cnt.get("unpriced_sells", 0) + cnt.get("unpriced_token_swaps", 0):
        reasons.append("some swaps could not be priced in dollars (no price observation near the swap time)")
    if cnt.get("peg_assumed_entries"):
        reasons.append(f"{cnt['peg_assumed_entries']} swap(s) used an assumed 1.00 stablecoin price")
    if cov["fees"]["unknown_or_unpriced"]:
        reasons.append(f"{cov['fees']['unknown_or_unpriced']} fee(s) are unknown or could not be priced")
    if cov["classification"]["entries_excluded_or_unclassified"]:
        reasons.append(f"{cov['classification']['entries_excluded_or_unclassified']} entry(ies) were unclassified, unsupported or rejected and are not in the P&L")
    if R.contam:
        reasons.append("tokens touched by unclassified, unsupported or suspect entries: " + ", ".join(sorted(R.contam)))
    off = [pe for pe in R.pool_out if pe["qty_rem"] > 0]
    if off:
        reasons.append(f"{len(off)} off-book holding(s) (sent away or deployed to liquidity) have not come back; they are not valued")
    if inv["assets_without_mark"] or inv["assets_without_executable_estimate"]:
        reasons.append("open positions lack a fresh mark or an executable estimate: unrealized and liquidation figures are partial")
    if cov["history"]["gaps"] and any(g["source"] == "input" for g in cov["history"]["gaps"]):
        reasons.append("declared coverage gaps exist")
    if L.chain not in ("solana",):
        reasons.append("no transaction provider is wired for this chain in the lab; the ledger came from the caller")
    status = "NOT_POSSIBLE" if blocking else ("PARTIAL" if reasons else "COMPLETE")
    statement = ("Comprehensive reconstruction cannot be achieved: " + "; ".join(blocking or reasons)) if status != "COMPLETE" else \
                "Reconstruction is complete for the observed window; it still describes wallets, not people."
    return {"status": status, "blocking": blocking, "reasons": reasons, "statement": statement}


# ---------- reconciliation ----------

def run_checks(R: C.Run, L: C.Ledger, rows: list[dict], realized: dict, costs: dict) -> list[dict]:
    out = []

    def add(name, ok, detail, warn=False):
        out.append({"check": name, "status": "PASS" if ok else ("WARN" if warn else "FAIL"), "detail": detail})
    # 1 each lot: slices + remainder = what came in
    bad = []
    for l in R.lots:
        used = _sum(s["qty"] for s in R.slices if s["lot"] == l.id)
        if used + l.qty != l.qty0 or l.qty < 0:
            bad.append(l.id)
    add("lot_quantity_conservation", not bad, {"lots": len(R.lots), "violations": bad[:10]})
    # 2 per asset: everything that came in is accounted for
    viol = {}
    for a in sorted({l.asset for l in R.lots}):
        came = _sum(l.qty0 for l in R.lots if l.asset == a)
        went = _sum(s["qty"] for s in R.slices if s["asset"] == a)
        left = _sum(l.qty for l in R.lots if l.asset == a)
        if came != went + left:
            viol[a] = _q(came - went - left)
    add("asset_quantity_conservation", not viol, {"assets": len({l.asset for l in R.lots}), "violations": viol})
    # 3 off-book pool: out = back + still out
    out_q = _sum(s["qty"] for s in R.slices if s["kind"] in OFFBOOK_KINDS)
    back_q = _sum(l.qty0 for l in R.lots if l.restored)
    rem_q = _sum(pe["qty_rem"] for pe in R.pool_out)
    add("off_book_conservation", out_q == back_q + rem_q, {"qty_out": _q(out_q), "qty_returned": _q(back_q), "qty_not_returned": _q(rem_q)})
    # 4 value: basis created = basis realized + off-book remainder + open basis
    created = _sum(l.cost0 for l in R.lots if not l.restored and l.cost0 is not None)
    realized_b = _sum(s["basis"] for s in R.slices if s["kind"] in SALE_KINDS and s["basis"] is not None)
    pool_b = _sum(pe["basis"] for pe in R.pool_out if pe["basis"] is not None)
    open_b = _sum(l.cost for l in R.lots if l.cost is not None and l.qty > 0)
    add("basis_conservation", created == realized_b + pool_b + open_b, {"basis_created": _q(created), "basis_realized": _q(realized_b), "off_book_basis": _q(pool_b), "open_basis": _q(open_b)})
    # 5 proceeds recorded on each sale = proceeds spread over slices
    logged = _sum(x["proceeds"] for x in R.entry_log if x.get("proceeds") is not None)
    spread = _sum(s["proceeds"] for s in R.slices if s["kind"] in ("SALE", "TOKEN_SWAP") and s["proceeds"] is not None)
    add("proceeds_conservation", logged == spread, {"entry_proceeds": _q(logged), "slice_proceeds": _q(spread)})
    # 6 two routes to the same realized number
    from_pos = _sum(r["units"]["USD"]["realized_gross"] for r in rows if r["units"]["USD"]["realized_gross"] is not None)
    from_slices = realized["trading_known"]["realized_pnl_usd"]
    in_pos = [r for r in rows if r["units"]["USD"]["realized_gross"] is not None]
    # positions that are fully known must agree with slice totals for the same positions
    same = _sum(s["proceeds"] - s["basis"] for s in R.slices if s["kind"] in SALE_KINDS and s["bucket"] == "TRADING" and s["basis"] is not None and s["proceeds"] is not None
                and s["position"] in {r["position"] for r in in_pos})
    add("position_total_equals_slice_total", from_pos == same, {"positions_total": _q(from_pos), "slices_same_positions": _q(same), "all_known_slices": _q(from_slices)})
    # 7 fees partition
    tot = _sum(f["usd"] for f in R.fees if f["usd"] is not None)
    parts = costs["usd_known_attributed_to_positions"] + costs["usd_known_unattributed"]
    add("fee_partition", tot == parts == R.fees_usd_cum, {"fees_usd": _q(tot), "attributed_plus_unattributed": _q(parts)})
    # 8 every input entry has an outcome
    handled = set()
    for x in R.entry_log:
        handled.update(x["id"].split("+"))
    add("entries_accounted", len(handled) == len(L.entries) and R.counts.get("entries", 0) == len(L.entries),
        {"input": len(L.entries) + len(L.rejects), "accounted": len(handled), "rejected_with_reason": len(L.rejects)})
    # 9 data-quality warnings
    dc = [r for r in L.rejects if r["reason"] in ("DECIMALS_CONFLICT", "AMOUNT_RAW_MISMATCH")]
    add("decimals_consistent", not dc, {"rejected_for_decimals": [r["id"] for r in dc]}, warn=True)
    add("inventory_explained_by_ledger", R.counts.get("shortfall_lots", 0) == 0, {"opening_lots_added": R.counts.get("shortfall_lots", 0), "assets": sorted({l.asset for l in R.synthetic_lots})}, warn=True)
    add("no_rejected_entries", not L.rejects, {"rejected": [{"id": r["id"], "reason": r["reason"]} for r in L.rejects][:20]}, warn=True)
    add("no_suspect_units", not any(f["code"] in ("UNIT_ERROR_SUSPECTED", "IMPLIED_PRICE_MISMATCH") for f in R.flags),
        {"flags": [f for f in R.flags if f["code"] in ("UNIT_ERROR_SUSPECTED", "IMPLIED_PRICE_MISMATCH")][:10]}, warn=True)
    return out


# ---------- equity and drawdown ----------

def equity_block(R: C.Run, pol: dict) -> dict:
    pts, complete = [], 0
    for sn in R.snapshots:
        unreal, ok = ZERO, True
        for a, o in sn["open"].items():
            m = R.book.latest_mid(a, sn["time"])
            if o["unknown"] or m is None or sn["time"] - m["t"] > float(pol["mtm_max_age_s"]):
                ok = False
                break
            unreal += m["usd"] * o["qty"] - o["basis"]
        if ok:
            complete += 1
            pts.append({"time": sn["time"], "equity": sn["realized"] - sn["fees"] + unreal, "capital": _sum(o["basis"] for o in sn["open"].values())})
    total = len(R.snapshots)
    share = Decimal(complete) / total if total else None
    need_pts, need_share = int(pol["min_equity_points"]), dec(pol["min_equity_completeness"])
    out = {"points_total": total, "points_fully_valued": complete, "completeness": share, "min_points": need_pts, "min_completeness": need_share,
           "method": "equity = cumulative realized P&L - fees to date + unrealized P&L of open trading lots at the latest supplied price; deposits and withdrawals never enter it",
           "caveat": "sampled at transaction times only, so the drawdown is a lower bound"}
    if complete < need_pts or share is None or share < need_share:
        out.update({"status": "INSUFFICIENT_DATA", "max_drawdown_usd": None, "max_drawdown_share_of_peak_capital": None,
                    "reason": f"{complete} fully valued points of {total} (need at least {need_pts} and {_q(need_share, 2)} of all points)"})
        return out
    peak, dd, peak_cap = pts[0]["equity"], ZERO, max(p["capital"] for p in pts)
    for p in pts:
        peak = max(peak, p["equity"])
        dd = max(dd, peak - p["equity"])
    out.update({"status": "COMPUTED", "max_drawdown_usd": dd, "peak_capital_usd": peak_cap, "max_drawdown_share_of_peak_capital": (dd / peak_cap) if peak_cap > 0 else None,
                "final_equity_usd": pts[-1]["equity"]})
    return out


# ---------- one analysis pass ----------

def _headline(R: C.Run, as_of: float) -> dict:
    realized = realized_block(R)
    rows = position_rows(R, as_of)
    m = metrics(rows, "USD", R.pol)
    return {"realized_usd": realized["trading_known"]["realized_pnl_usd"], "cost_usd": realized["trading_known"]["cost_basis_usd"], "sample": m["sample_size"], "win_rate": m["win_rate"],
            "unknown_basis_proceeds_usd": realized["unknown_basis_proceeds"]["proceeds_usd"], "rows": rows}


def sensitivity_block(L: C.Ledger, pol: dict, primary: C.Run, primary_head: dict, as_of: float) -> list[dict]:
    share = dec(pol["material_sensitivity_share"])
    scale = abs(primary_head["realized_usd"])
    out = []

    def entry(name, R2, note, applies=True):
        h = _headline(R2, as_of)
        d = h["realized_usd"] - primary_head["realized_usd"]
        changed = sum(1 for a, b in zip(primary_head["rows"], h["rows"]) if a["units"]["USD"]["net"] != b["units"]["USD"]["net"] and a["position"] == b["position"])
        sign_flip = (h["realized_usd"] > 0) != (primary_head["realized_usd"] > 0) and h["realized_usd"] != 0 and primary_head["realized_usd"] != 0
        material = abs(d) > share * scale if scale > 0 else d != 0     # moves the realized figure by more than the declared share of itself
        out.append({"name": name, "realized_usd": h["realized_usd"], "delta_vs_primary_usd": d, "material": bool(material or sign_flip), "sign_flip": bool(sign_flip),
                    "positions_with_different_net": changed, "sample_size": h["sample"], "unknown_basis_proceeds_usd": h["unknown_basis_proceeds_usd"], "note": note})
    alt = "AVCO" if primary.conv == "FIFO" else "FIFO"
    entry(f"convention_{alt}", run_engine(L, pol, alt), f"{alt} instead of {primary.conv}. For a position that closes with only trading lots in it, the total is the same under every convention; "
                                                       "the convention moves realized P&L only between partly closed positions and (with mixed inventory) between lots.")
    stables = [a for a, m in L.assets.items() if m["kind"] == "STABLE"]
    if any(p["asset"] in stables and p["kind"] == "MID" for p in L.prices):
        entry("stablecoins_at_1.00", run_engine(L, dict(pol, force_stable_par=True), primary.conv), "every stablecoin valued at exactly 1.00, ignoring observed prices")
    if primary.counts.get("returns_matched"):
        entry("no_return_matching", run_engine(L, dict(pol, return_matching=False), primary.conv),
              "tokens sent away and received back are treated as unrelated: the returned units have unknown basis")
    return out


def _analyze_once(doc: dict, pol: dict) -> dict:
    L = C.parse_ledger(doc)
    R = run_engine(L, pol, pol["convention"])
    as_of = L.as_of
    rows = position_rows(R, as_of)
    realized = realized_block(R)
    costs = costs_block(R)
    inv = inventory_block(R, as_of, pol)
    cov = coverage_block(R, L, rows, realized, pol)
    checks = run_checks(R, L, rows, realized, costs)
    checks.append({"check": "no_entries_after_as_of", "status": "PASS" if not any(r["reason"] == "AFTER_AS_OF" for r in L.rejects) else "WARN",
                   "detail": {"rejected_after_as_of": [r["id"] for r in L.rejects if r["reason"] == "AFTER_AS_OF"]}})
    rec = reconstruction(R, L, rows, cov, checks, inv, realized)
    mets = {u: metrics(rows, u, pol) for u in ("USD", "NATIVE")}
    head = {"realized_usd": realized["trading_known"]["realized_pnl_usd"], "cost_usd": realized["trading_known"]["cost_basis_usd"], "rows": rows}
    sens = sensitivity_block(L, pol, R, head, as_of)
    eq = equity_block(R, pol)
    reconciled = not any(c["status"] == "FAIL" for c in checks)
    net_realized = realized["trading_known"]["realized_pnl_usd"] - costs["usd_known_unattributed"] - costs["usd_known_attributed_to_positions"]
    result = {
        "schema": C.SCHEMA_RESULT, "engine_version": C.VERSION, "label": L.label, "chain": L.chain, "as_of": as_of, "wallets": L.wallets, "group": L.group,
        "convention": R.conv, "policy": pol, "person_level_claim": False, "statement": C.STATEMENT, "limits": LIMITS,
        "reconstruction": rec, "coverage": cov, "counts": trade_counts(R, rows, L),
        "realized": realized,
        "costs": costs,
        "headline": {"realized_trading_known_usd_before_fees": realized["trading_known"]["realized_pnl_usd"], "known_fees_usd": costs["usd_known"],
                     "realized_trading_known_usd_after_known_fees": net_realized,
                     "unrealized_mark_to_market_usd": inv["unrealized_mtm_usd"], "unrealized_if_sold_now_usd_lower_bound": inv["unrealized_executable_usd"],
                     "mark_minus_executable_gap_usd": inv["mtm_minus_executable_usd"],
                     "note": "realized, mark-to-market and executable lines are separate and are not added together here; each states what it leaves out"},
        "open_inventory": inv, "positions": rows, "metrics": mets, "equity": eq, "sensitivity": sens,
        "flags": R.flags, "round_trip_transfers": [{**x, "sent": x["sent"], "returned": x["returned"]} for x in R.round_trips],
        "rejects": L.rejects, "native_unit_view": realized["trading_native_units"],
        "reconciliation": {"reconciled": reconciled, "checks": checks},
    }
    result["score"] = score(result, pol)
    return result


def score(res: dict, pol: dict) -> dict:
    """The score gate. A wallet is scored only on enough closed, fully known positions with enough coverage. Otherwise the refusal says why."""
    m = res["metrics"]["USD"]
    cov = res["coverage"]
    reasons = []
    floor, low = int(pol["min_closed_positions"]), int(pol["low_confidence_below"])
    if res["reconstruction"]["status"] == "NOT_POSSIBLE":
        reasons.append("reconstruction is not possible: " + "; ".join(res["reconstruction"]["blocking"]))
    if not res["reconciliation"]["reconciled"]:
        reasons.append("reconciliation failed")
    if m["sample_size"] < floor:
        reasons.append(f"sample of {m['sample_size']} closed, fully known position(s) is below the minimum of {floor}")
    sample = [r for r in res["positions"] if r["units"]["USD"]["in_sample"]]
    if sample:
        span = (max(r["closed_at"] for r in sample) - min(r["opened_at"] for r in sample)) / 86400
        if span < float(pol["min_span_days"]):
            reasons.append(f"the sample spans {span:.1f} days, below the minimum of {pol['min_span_days']}")
    bc = cov["basis"]["share_of_disposed_value_with_known_basis"]
    if bc is None:
        reasons.append("no disposal with a known value to judge basis coverage")
    elif bc < dec(pol["min_basis_coverage"]):
        reasons.append(f"only {_q(bc, 3)} of disposed value came from lots of known basis (minimum {pol['min_basis_coverage']})")
    pc = cov["prices"]["fraction_priced"]
    if pc is not None and pc < dec(pol["min_price_coverage"]):
        reasons.append(f"only {_q(pc, 3)} of swaps could be priced (minimum {pol['min_price_coverage']})")
    fu = cov["fees"]["unknown_share"]
    if fu is not None and fu > dec(pol["max_unknown_fee_share"]):
        reasons.append(f"{_q(fu, 3)} of fees are unknown or unpriced (maximum {pol['max_unknown_fee_share']})")
    cs = cov["classification"]["share"]
    if cs is not None and cs > dec(pol["max_unclassified_share"]):
        reasons.append(f"{_q(cs, 3)} of entries were unclassified, unsupported or rejected (maximum {pol['max_unclassified_share']})")
    window = {"from": min((r["opened_at"] for r in sample), default=None), "to": max((r["closed_at"] for r in sample), default=None)}
    if reasons:
        return {"status": "INSUFFICIENT_DATA", "reasons": reasons, "sample_size": m["sample_size"], "minimum_sample": floor, "value": None, "rankable": False,
                "note": "no score and no ranking: the data is too sparse or too incomplete to say anything about this wallet's skill"}
    notes, conf = [], "OK"
    if m["sample_size"] < low:
        conf = "LOW_CONFIDENCE"
        notes.append(f"sample below {low}: treat as an indication only")
    if cov["history"]["status"] in ("UNKNOWN", "TRUNCATED"):
        conf = "LOW_CONFIDENCE"
        notes.append("history coverage not established: the score applies only to the observed window")
    share = m["profit_share_from_biggest_winner"]
    if share is not None and share > Decimal("0.5"):
        conf = "LOW_CONFIDENCE"
        notes.append(f"one position produced {_q(share, 3)} of all profit; the score is the return excluding it")
    val = m["return_excluding_biggest_winner"]
    if val is None:
        return {"status": "INSUFFICIENT_DATA", "reasons": ["return excluding the biggest winner is undefined for this sample"], "sample_size": m["sample_size"], "minimum_sample": floor, "value": None, "rankable": False}
    return {"status": "SCORED", "metric": "return_excluding_biggest_winner (capital weighted, USD, after known fees)", "value": val, "confidence": conf,
            "win_rate": m["win_rate"], "win_rate_interval_95": m["win_rate_interval_95"], "sample_size": m["sample_size"], "window": window,
            "reasons": [], "notes": notes, "rankable": True,
            "note": "describes this wallet over the window above, not a person and not future results"}


def analyze(doc: dict, policy: dict | None = None, *, verify_determinism: bool = True) -> dict:
    """Ledger in, result out. Pure and repeatable: the same ledger and policy give the same result hash, checked by running twice."""
    pol = merge_policy(policy)
    with localcontext() as ctx:
        ctx.prec = C.PREC
        res = _analyze_once(doc, pol)
        res = _jsonable(res)
        if verify_determinism:
            res2 = _jsonable(_analyze_once(doc, pol))
            same = sha(res2) == sha(res)
            res["reconciliation"]["checks"].append({"check": "deterministic_recomputation", "status": "PASS" if same else "FAIL", "detail": {"second_run_hash_equal": same}})
            res["reconciliation"]["reconciled"] = res["reconciliation"]["reconciled"] and same
            if not same:
                res["score"] = {"status": "INSUFFICIENT_DATA", "reasons": ["recomputation gave a different result"], "rankable": False, "value": None}
    res["input_sha256"] = sha({"ledger": doc, "policy": pol})
    res["result_sha256"] = sha({k: v for k, v in res.items() if k != "result_sha256"})
    return res


def _jsonable(o: Any) -> Any:
    if isinstance(o, Decimal):
        return _q(o)
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(x) for x in o]
    if isinstance(o, float):
        return o if o == o and o not in (float("inf"), float("-inf")) else None
    return o


# ---------- ranking and provider comparison ----------

def rank_wallets(results: list[dict]) -> dict:
    """Rank only wallets whose score gate passed. Everything else is listed with the reasons and gets no rank."""
    ok = [r for r in results if r["score"]["status"] == "SCORED" and r["reconciliation"]["reconciled"]]
    ok.sort(key=lambda r: (-Decimal(r["score"]["value"]), -r["score"]["sample_size"], ",".join(r["wallets"])))
    return {"ranked": [{"rank": i + 1, "wallets": r["wallets"], "score": r["score"]["value"], "n": r["score"]["sample_size"], "confidence": r["score"]["confidence"], "window": r["score"]["window"]}
                       for i, r in enumerate(ok)],
            "refused": [{"wallets": r["wallets"], "reasons": r["score"].get("reasons", [])} for r in results if r not in ok],
            "note": "a refusal is not a bad score. It means the data cannot support a number."}


def compare_provider_estimates(result: dict, provider: dict) -> dict:
    """Compare a provider's stated figures with the ledger's. The comparison is labelled an estimate and never changes the ledger or its hash."""
    mine = {"realized_pnl_usd": result["headline"]["realized_trading_known_usd_before_fees"], "trade_count": str(result["counts"]["positions"]["CLOSED"]),
            "swap_count": str(result["counts"]["buys"] + result["counts"]["sells"] + result["counts"]["token_to_token_swaps"]), "win_rate": result["metrics"]["USD"]["win_rate"]}
    defs = {"realized_pnl_usd": "ledger: realized P&L of trading lots with known basis and proceeds, before fees. Providers often include airdrops, transfers or mark-to-market",
            "trade_count": "ledger: closed positions. Providers often count every swap", "swap_count": "ledger: swaps accounted for", "win_rate": "ledger: share of in-sample closed positions with net P&L above zero"}
    rows = []
    for k, v in (provider.get("claims") or {}).items():
        row = {"metric": k, "provider_value": v, "ledger_value": mine.get(k), "definition_note": defs.get(k, "no ledger equivalent")}
        try:
            row["difference"] = _q(dec(v) - dec(mine[k])) if mine.get(k) is not None else None
        except (ValueError, KeyError):
            row["difference"] = None
        rows.append(row)
    return {"label": "PROVIDER ESTIMATE, NOT VALIDATED, NOT USED IN THE LEDGER", "provider": str(provider.get("source") or "unspecified"), "ledger_result_sha256": result["result_sha256"],
            "rows": rows, "note": "a match does not validate the ledger and a mismatch does not invalidate it; accounting is validated by the reconciliation checks, not by a provider"}


# ---------- plain-English report ----------

def render_report(res: dict) -> str:
    h, rec, cov, sc = res["headline"], res["reconstruction"], res["coverage"], res["score"]
    m = res["metrics"]["USD"]
    L = [f"Wallet performance (wallet-level, not person-level)   scope: {', '.join(res['wallets'])}   chain: {res['chain']}   as of {res['as_of']:.0f}   convention: {res['convention']}",
         f"Label: {res['label']}" if res.get("label") else "",
         f"Reconstruction: {rec['status']}. {rec['statement']}",
         f"Reconciled: {res['reconciliation']['reconciled']} ({sum(1 for c in res['reconciliation']['checks'] if c['status'] == 'PASS')} pass, "
         f"{sum(1 for c in res['reconciliation']['checks'] if c['status'] == 'WARN')} warn, {sum(1 for c in res['reconciliation']['checks'] if c['status'] == 'FAIL')} fail)",
         f"History coverage: {cov['history']['status']}; first entry {cov['history']['first_entry_time']}, last {cov['history']['last_entry_time']}; "
         f"{cov['history']['opening_lots_from_missing_history']} disposal(s) needed an opening lot from missing history",
         "",
         f"Realized (trading lots, known basis and proceeds, before fees): {h['realized_trading_known_usd_before_fees']} USD",
         f"Known fees: {h['known_fees_usd']} USD ({res['costs']['amount_unknown']} fee(s) unknown, {res['costs']['usd_unpriced']} unpriced)",
         f"Realized after known fees: {h['realized_trading_known_usd_after_known_fees']} USD",
         f"Proceeds from lots of unknown basis (no gain or loss computed): {res['realized']['unknown_basis_proceeds']['proceeds_usd']} USD",
         f"Unrealized, marked at last supplied price: {h['unrealized_mark_to_market_usd']} USD on {res['open_inventory']['assets_with_known_basis'] - res['open_inventory']['assets_without_mark']} of "
         f"{res['open_inventory']['assets_with_known_basis']} open positions of known basis",
         f"If sold now per supplied quotes (lower bound): {h['unrealized_if_sold_now_usd_lower_bound']} USD on "
         f"{res['open_inventory']['assets_with_known_basis'] - res['open_inventory']['assets_without_executable_estimate']} of {res['open_inventory']['assets_with_known_basis']}; "
         f"the mark overstates the executable value by {h['mark_minus_executable_gap_usd']} USD where both are known",
         "",
         f"Trades (closed, fully known positions): {m['sample_size']} of {m['positions_total']} positions; swaps accounted for: "
         f"{res['counts']['buys'] + res['counts']['sells'] + res['counts']['token_to_token_swaps']}",
         f"Win rate: {m['win_rate']} (95% interval {m['win_rate_interval_95']}); median return {m['median_return']}; aggregate return {m['aggregate_return']}",
         f"Profit share from biggest winner: {m['profit_share_from_biggest_winner']}; return excluding biggest winner: {m['return_excluding_biggest_winner']}",
         f"Drawdown: {res['equity']['status']}" + (f" ({res['equity']['reason']})" if res['equity'].get('reason') else f", max {res['equity']['max_drawdown_usd']} USD (lower bound)"),
         "Sensitivity: " + ("; ".join(f"{s['name']} {s['delta_vs_primary_usd']} USD{' (MATERIAL)' if s['material'] else ''}" for s in res["sensitivity"]) or "none applicable"),
         "",
         f"Score: {sc['status']}" + (f" {sc['value']} ({sc['confidence']})" if sc["status"] == "SCORED" else ""),
         *[f"  refused because: {r}" for r in sc.get("reasons", [])],
         *[f"  note: {n}" for n in sc.get("notes", [])],
         "Limits: " + " ".join(res["limits"][:2])]
    return "\n".join(x for x in L if x is not None)
