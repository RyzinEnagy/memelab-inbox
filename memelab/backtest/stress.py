"""Adversarial position and opportunity stress engine.

Given a present opportunity snapshot (from the lab's analyze result), a range of position sizes and the planned
invalidation, it recomputes what each size would actually return under a set of adverse but plausible shocks.
Every shock is HYPOTHETICAL and labeled as such; no probability is attached unless historical evidence exists
(it is passed in separately and reported side by side, never blended). Fatal flags are respected: a token with a
fatal flag can never get a positive decision status here.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import execution as X

DECISIONS = ("RESEARCHABLE", "INCONCLUSIVE", "NO_TRADE", "STRUCTURALLY_UNTRADEABLE", "RISK_FATAL_FLAW", "INSUFFICIENT_EXECUTION_DATA")


@dataclass
class Snapshot:
    chain: str
    mint: str
    as_of: float
    price_usd: float
    liquidity_usd: float | None
    pool_type: str = "CPMM"                     # of the main pool
    quote_asset: str = "SOL"
    sol_usd: float | None = None
    transfer_fee_bps: float = 0.0
    fee_authority_active: bool = False          # Token-2022 transfer-fee config authority present (can raise the fee)
    freeze_authority_active: bool = False
    mint_authority_active: bool = False
    concentrated_pct: float | None = None       # cluster-adjusted / insider share of supply (percent)
    circulating_tokens: float | None = None
    invalidation_price: float | None = None
    sell_quotes: list = field(default_factory=list)   # [(usd_size, proceeds_usd, impact_frac, status)] present-tense
    quote_at: float | None = None
    fatal_flags: list = field(default_factory=list)
    has_sell_route: bool | None = True
    score: float | None = None
    status: str | None = None
    swap_fee: float = 0.0125                    # main pool's fee; default is the conservative PumpSwap tier (execution.DEX_FEE_DEFAULTS)
    fee_basis: str = "ASSUMED_UPPER_OBSERVED_TIER"


@dataclass(frozen=True)
class Shock:
    id: str
    label: str
    liquidity_scale: float = 1.0       # 0.25 = 75% of liquidity withdrawn before our exit
    price_move: float = 0.0            # move of the mid before our exit (negative = drop)
    insider_sell_frac: float = 0.0     # share of the concentrated holders' tokens sold into the pool ahead of us
    transfer_fee_bps_at_exit: float | None = None
    sol_move: float = 0.0
    stable_rate: float = 1.0
    network_fee_mult: float = 1.0
    tx_fail_attempts: int = 0          # failed exit transactions before one lands (each costs a network fee)
    sell_route_fails: bool = False
    exit_at_invalidation: bool = False
    freeze: bool = False


def default_shocks(snap: Snapshot) -> list[Shock]:
    s = [
        Shock("BASE", "no shock: exit right away at present liquidity"),
        Shock("LIQ_25", "25% of liquidity withdrawn", liquidity_scale=0.75),
        Shock("LIQ_50", "50% of liquidity withdrawn", liquidity_scale=0.50),
        Shock("LIQ_75", "75% of liquidity withdrawn", liquidity_scale=0.25),
        Shock("INSIDER_DUMP", "concentrated holders sell half their tokens ahead of us", insider_sell_frac=0.5),
        Shock("STOP_GAP", "price gaps 40% down through the stop; exit at the gap", price_move=-0.40),
        Shock("DELAYED_EXIT", "exit lands 30 minutes late: price -20% and liquidity -30% meanwhile", price_move=-0.20, liquidity_scale=0.70),
        Shock("FAILED_BREAKOUT", "setup fails: exit at the invalidation level", exit_at_invalidation=True),
        Shock("ATTENTION_COLLAPSE", "viral post collapses: price -50%, liquidity -60%", price_move=-0.50, liquidity_scale=0.40),
        Shock("VOLUME_GONE", "volume and depth disappear: liquidity -90%", liquidity_scale=0.10),
        Shock("SOL_DOWN_30", "SOL falls 30% vs USD while the position is open", sol_move=-0.30),
        Shock("CONGESTION", "network congestion: fees x200 and 3 failed exit transactions", network_fee_mult=200, tx_fail_attempts=3),
        Shock("HONEYPOT", "sell route fails: tokens cannot be sold", sell_route_fails=True),
        Shock("COMBINED_WORST", "75% liquidity withdrawn + insiders sell + fee raised + 30% gap + 2 failed transactions",
              liquidity_scale=0.25, insider_sell_frac=0.5, price_move=-0.30, transfer_fee_bps_at_exit=max(snap.transfer_fee_bps, 1000.0), tx_fail_attempts=2),
    ]
    if snap.fee_authority_active or snap.transfer_fee_bps > 0:
        s.append(Shock("FEE_HIKE", "transfer-fee authority raises the fee to 10% before our exit", transfer_fee_bps_at_exit=1000.0))
    if snap.freeze_authority_active:
        s.append(Shock("FREEZE", "freeze authority freezes our token account", freeze=True))
    if snap.mint_authority_active:
        s.append(Shock("MINT_DILUTION", "mint authority doubles the supply and sells into the pool", insider_sell_frac=1.0, price_move=-0.5))
    if snap.quote_asset in ("USDC", "USDT"):
        s.append(Shock("STABLE_DEPEG", "quote stablecoin depegs to 0.95", stable_rate=0.95))
    if _largest_ok_quote(snap) is not None:
        s.append(Shock("QUOTE_DEPLETION", "routes fail above the largest size that had a working sell quote", sell_route_fails=False))
    return s


def _largest_ok_quote(snap: Snapshot) -> float | None:
    ok = [q[0] for q in snap.sell_quotes if q[3] == "OK" and q[1] is not None]
    return max(ok) if ok else None


def observed_sell_proceeds(snap: Snapshot, size_usd: float) -> float | None:
    """Proceeds (USD) of selling `size_usd` worth now, from present router quotes, interpolated on the effective rate;
    None above the largest working quote (no extrapolation) or without quotes."""
    pts = sorted((q[0], q[1]) for q in snap.sell_quotes if q[3] == "OK" and q[1] is not None and q[0] > 0)
    if not pts or size_usd > pts[-1][0] * (1 + 1e-9):
        return None
    lo = max([p for p in pts if p[0] <= size_usd], default=pts[0])
    hi = min([p for p in pts if p[0] >= size_usd], default=pts[-1])
    r_lo, r_hi = lo[1] / lo[0], hi[1] / hi[0]
    rate = r_lo if hi[0] == lo[0] else r_lo + (size_usd - lo[0]) / (hi[0] - lo[0]) * (r_hi - r_lo)
    return size_usd * rate


def _pool_for(snap: Snapshot, liquidity_scale: float, price: float, fee_bps: float) -> X.CpmmPool | None:
    if snap.liquidity_usd is None or snap.liquidity_usd <= 0 or snap.pool_type != "CPMM":
        return None
    fees = X.Fees(snap.swap_fee, fee_bps, None, 0.0)
    return X.pool_from_liquidity_snapshot(snap.liquidity_usd * liquidity_scale, price, 1.0, fees, haircut=1.0)


def run_scenario(snap: Snapshot, size_usd: float, shock: Shock, network_fee_sol: float = 0.000105) -> dict:
    """USD-denominated: pool quote side expressed in USD at the as-of SOL price; SOL moves applied to proceeds."""
    out = {"scenario": shock.id, "label": shock.label, "size_usd": size_usd, "hypothetical": shock.id != "BASE"}
    sol = snap.sol_usd
    if sol is None:
        out.update(status="INSUFFICIENT_EXECUTION_DATA", reason="no as-of SOL/USD price")
        return out
    nfee = network_fee_sol * sol * shock.network_fee_mult
    entry_pool = _pool_for(snap, 1.0, snap.price_usd, snap.transfer_fee_bps)
    if entry_pool is None:
        out.update(status="INSUFFICIENT_EXECUTION_DATA" if snap.pool_type == "CPMM" else "UNSUPPORTED_POOL",
                   reason="no constant-product liquidity basis for a sized fill" if snap.pool_type == "CPMM" else f"{snap.pool_type} pool: present quotes only")
        return out
    buy, _ = entry_pool.buy(size_usd)
    tokens = buy.out
    cost = size_usd + nfee
    if shock.id == "QUOTE_DEPLETION" and size_usd > (_largest_ok_quote(snap) or 0):
        out.update(status="FAILED", entry_impact=buy.impact_frac, tokens=tokens, cost_usd=cost, proceeds_usd=0.0, ret=-1.0,
                   reason=f"no working sell route above ${_largest_ok_quote(snap):,.0f} (present quotes)")
        return out
    if shock.freeze or shock.sell_route_fails or snap.has_sell_route is False:
        out.update(status="FAILED", entry_impact=buy.impact_frac, tokens=tokens, cost_usd=cost, proceeds_usd=0.0, ret=-1.0,
                   reason="tokens frozen" if shock.freeze else "no sell route")
        return out
    px = snap.price_usd * (1 + shock.price_move)
    if shock.exit_at_invalidation:
        if snap.invalidation_price is None:
            out.update(status="INCONCLUSIVE", reason="no invalidation level defined")
            return out
        px = min(px, snap.invalidation_price)
    if px <= 0:
        out.update(status="FAILED", ret=-1.0, proceeds_usd=0.0, cost_usd=cost, reason="price to zero")
        return out
    exit_fee = shock.transfer_fee_bps_at_exit if shock.transfer_fee_bps_at_exit is not None else snap.transfer_fee_bps
    # in a constant-product pool the USD depth falls with the square root of the price when nobody adds liquidity
    depth_scale = shock.liquidity_scale * (px / snap.price_usd) ** 0.5
    pool = _pool_for(snap, depth_scale, px, exit_fee)
    if shock.insider_sell_frac and snap.concentrated_pct and snap.circulating_tokens:
        dump = snap.circulating_tokens * snap.concentrated_pct / 100.0 * shock.insider_sell_frac
        _, pool = pool.sell(dump)                     # they sell ahead of us: reserves shift before our exit
    elif shock.insider_sell_frac:
        out.setdefault("notes", []).append("insider share unknown: insider-dump effect not modeled (not assumed zero)")
    sell, _ = pool.sell(tokens)
    gross = sell.out
    # present quotes are the better evidence of today's depth: when the model is more generous than the observed quote
    # for this size, scale every scenario down by that ratio (never up)
    obs = observed_sell_proceeds(snap, size_usd)
    base_sell, _ = entry_pool.sell(tokens) if obs is not None else (None, None)
    ratio = min(1.0, obs / base_sell.out) if (obs is not None and base_sell and base_sell.out > 0) else 1.0
    if ratio < 1.0:
        gross *= ratio
        out["capped_by_observed_quote"] = round(ratio, 6)
    proceeds = gross * (1 + shock.sol_move) * shock.stable_rate - nfee * (1 + shock.tx_fail_attempts)
    out.update(status="FILLED", entry_impact=buy.impact_frac, exit_impact=sell.impact_frac, tokens=tokens, cost_usd=cost,
               exit_mid=pool.mid, proceeds_usd=max(proceeds, 0.0), ret=max(proceeds, 0.0) / cost - 1,
               marked_value_usd=tokens * px, realizable_vs_marked=(max(proceeds, 0.0) / (tokens * px)) if tokens * px > 0 else None,
               basis=X.LIQ_SNAPSHOT_APPROX if ratio == 1.0 else "LIQ_SNAPSHOT_APPROX_CAPPED_BY_QUOTE", swap_fee=snap.swap_fee, fee_basis=snap.fee_basis)
    return out


def max_size(snap: Snapshot, max_loss_usd: float, max_exit_impact: float, shock_ids=("BASE", "LIQ_50", "STOP_GAP")) -> dict:
    """Largest size whose loss stays within max_loss_usd under each listed shock and whose BASE exit impact stays
    within max_exit_impact. Binary search on size (loss and impact are monotone in size for a constant-product pool)."""
    if snap.liquidity_usd is None or snap.pool_type != "CPMM" or snap.sol_usd is None:
        return {"max_size_usd": None, "reason": "INSUFFICIENT_EXECUTION_DATA"}
    shocks = {s.id: s for s in default_shocks(snap)}

    def ok(x):
        for sid in shock_ids:
            r = run_scenario(snap, x, shocks[sid])
            if r.get("status") not in ("FILLED",):
                return False
            if r["cost_usd"] - r["proceeds_usd"] > max_loss_usd:
                return False
            if sid == "BASE" and r["exit_impact"] > max_exit_impact:
                return False
        return True

    lo, hi = 0.0, snap.liquidity_usd * 2
    if not ok(1.0):
        return {"max_size_usd": 0.0, "binding": "even $1 breaks a constraint"}
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    return {"max_size_usd": lo, "constraints": {"max_loss_usd": max_loss_usd, "max_exit_impact": max_exit_impact, "shocks": list(shock_ids)}}


def stress(snap: Snapshot, sizes_usd: list[float], max_loss_usd: float | None = None, max_exit_impact: float = 0.05,
           historical: dict | None = None) -> dict:
    shocks = default_shocks(snap)
    table = [run_scenario(snap, s, sh) for s in sizes_usd for sh in shocks]
    curve = [{"size_usd": r["size_usd"], "ret": r.get("ret"), "entry_impact": r.get("entry_impact"), "exit_impact": r.get("exit_impact")}
             for r in table if r["scenario"] == "BASE"]
    ms = max_size(snap, max_loss_usd if max_loss_usd is not None else min(sizes_usd) * 0.5, max_exit_impact)
    decision, why = _decide(snap, table, ms)
    return {"chain": snap.chain, "mint": snap.mint, "as_of": snap.as_of, "sizes_usd": sizes_usd, "scenarios": table, "size_curve": curve,
            "max_size": ms, "decision": decision, "decision_reasons": why, "fatal_flags": list(snap.fatal_flags),
            "historical_evidence": historical or {"tier": "UNAVAILABLE", "note": "no historical calibration attached; scenario results are hypothetical"},
            "probabilities": "NOT_ASSIGNED (shocks are hypothetical; see historical_evidence for empirical frequencies when available)",
            "improves": _improves(snap), "deteriorates": _deteriorates(snap)}


def _decide(snap: Snapshot, table: list[dict], ms: dict) -> tuple[str, list[str]]:
    why = []
    if snap.fatal_flags:
        return "RISK_FATAL_FLAW", [f"fatal flag(s): {', '.join(snap.fatal_flags)}; stress results cannot override them"]
    base = [r for r in table if r["scenario"] == "BASE"]
    if all(r.get("status") in ("INSUFFICIENT_EXECUTION_DATA", "UNSUPPORTED_POOL") for r in base):
        return "INSUFFICIENT_EXECUTION_DATA", [base[0].get("reason", "no execution basis")] if base else ["no sizes"]
    if snap.has_sell_route is False:
        return "STRUCTURALLY_UNTRADEABLE", ["no sell route"]
    smallest = min(base, key=lambda r: r["size_usd"])
    if smallest.get("status") == "FILLED" and smallest.get("exit_impact", 0) > 0.10:
        return "STRUCTURALLY_UNTRADEABLE", [f"even the smallest size exits with {smallest['exit_impact']:.1%} impact"]
    if ms.get("max_size_usd") is not None and ms["max_size_usd"] < smallest["size_usd"]:
        why.append(f"max size under the loss/impact caps is ${ms['max_size_usd']:,.0f}, below the smallest requested size")
        return "NO_TRADE", why
    worst = [r for r in table if r["scenario"] == "COMBINED_WORST" and r.get("status") == "FILLED"]
    if worst and min(r["ret"] for r in worst) <= -0.95:
        why.append("combined adverse scenario loses almost everything at every size")
    if snap.invalidation_price is None:
        why.append("no structural invalidation defined")
        return "INCONCLUSIVE", why
    return "RESEARCHABLE", why + ["execution is feasible at the smaller sizes under base conditions; scenarios show the downside, not a forecast"]


def _improves(s: Snapshot) -> list[str]:
    out = ["deeper liquidity observed at decision time", "a fresh sell quote at the intended size"]
    if s.fee_authority_active:
        out.append("transfer-fee authority revoked")
    if s.freeze_authority_active:
        out.append("freeze authority revoked")
    if s.concentrated_pct and s.concentrated_pct > 20:
        out.append("concentrated holders distribute without breaking the price")
    return out


def _deteriorates(s: Snapshot) -> list[str]:
    return ["liquidity withdrawn or LP unlocked", "large holders selling into thin depth", "quote staleness beyond its TTL",
            "price closes below the invalidation level"]


def empirical_cohort(con, status: str | None, horizon_h: int = 24, min_n: int = 30, universe_id: str = "lab_state_history",
                     asof: float | None = None) -> dict:
    """HISTORICAL percentiles for tokens the lab gave the same status, measured exactly like the outcome tracker
    (outcomes.outcome_for): one pool per token chosen at its decision time, first open after the decision, only bars
    available at `asof`. Only tokens the lab had recorded by `asof` and whose window had closed and been published by
    then count (Phase 16, D1/D2/D11). Returns come from complete windows only; worst drops also include windows cut
    short by a dead feed, as lower bounds. Reported beside the hypothetical shocks, never blended into them.
    Below `min_n` complete cases: INSUFFICIENT_HISTORY, no percentiles."""
    import statistics
    from . import outcomes as O
    cut = asof if asof is not None else 1e12
    rows = con.execute("SELECT chain, mint, MIN(available_at) t FROM bt_universe_members WHERE universe_id=? AND basis='THESIS' AND status_at_entry IS ? "
                       "AND available_at<=? GROUP BY chain, mint", (universe_id, status, cut)).fetchall()
    rets, worst, states = [], [], {}
    for r in rows:
        out = O.outcome_for(con, {"chain": r["chain"], "mint": r["mint"], "decision_time": r["t"]}, int(horizon_h * 3600), cut)
        states[out["state"]] = states.get(out["state"], 0) + 1
        rz = out["realized"] or {}
        if out["state"] == "COMPLETE":
            rets.append(rz["ret_close"])
        if rz.get("max_drawdown") is not None:
            worst.append(rz["max_drawdown"])
    base = {"status": status, "n": len(rets), "min_n": min_n, "asof": asof, "known_tokens": len(rows), "window_states": states}
    if len(rets) < min_n:
        return {"tier": "INSUFFICIENT_HISTORY", **base}
    q = lambda v, p: sorted(v)[max(0, min(len(v) - 1, int(p * len(v))))]
    return {"tier": "HISTORICAL_COHORT", **base, "horizon_h": horizon_h,
            "ret_p10_p50_p90": [q(rets, 0.1), statistics.median(rets), q(rets, 0.9)], "worst_drop_p10_p50": [q(worst, 0.1), statistics.median(worst)],
            "note": ("empirical frequencies for past tokens with the same lab status, known and measurable at the assessment time; not this token's "
                     "probabilities; mid prices before costs; worst drops include windows cut short by a dead feed as lower bounds")}
