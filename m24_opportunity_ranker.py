"""m24: opportunity scoring, fatal flags, status assignment and ranking.

Public interface:
    derive_components(**modules) -> (components: dict[bucket -> 0..1], rationales: dict[bucket -> [str]])
    score(components, **modules) -> {"total", "breakdown", "fatal_flags", "untradeable", "unknown_buckets", ...}
    fatal_flags(**modules) -> [{"flag", "evidence", "severity", "category"}]
    assign_status(score_result, breakout=None, entries=None, lifecycle=None, early=None, monitor_diff=None)
        -> {"status", "reasoning"}
    rank(candidates) -> {"rows": [...], "best_token", "best_trade", "best_token_vs_best_trade", ...}
    evaluate(**modules) -> convenience: derive_components + score + assign_status

Bucket helpers (each returns (score_0_to_1, rationale_lines)):
    sub_market_execution(depth=, lp=)
    sub_supply_ownership(holders=, clusters=, early=)
    sub_token_lp_safety(mechanics=, lp=)
    sub_demand_order_flow(orderflow=, manipulation=)
    sub_price_structure_entry(structure=, breakout=, entries=)
    sub_attention_narrative(attention=)
    sub_lifecycle_relative_strength(lifecycle=, rs=)
    sub_risk_reward_exitability(rr=, sizing=, depth=)

Module output dicts are read defensively: missing inputs give partial credit no
higher than MISSING_CAP (0.4) and add an "UNKNOWN:" rationale line.
"""
from __future__ import annotations

from typing import Any, Callable

MAX_POINTS: dict[str, int] = {
    "market_execution": 15,
    "supply_ownership": 15,
    "token_lp_safety": 10,
    "demand_order_flow": 10,
    "price_structure_entry": 15,
    "attention_narrative": 10,
    "lifecycle_relative_strength": 10,
    "risk_reward_exitability": 15,
}
assert sum(MAX_POINTS.values()) == 100

MISSING_CAP = 0.4
UNKNOWN_PREFIX = "UNKNOWN:"

STATUSES = [
    "REJECTED", "RESEARCH REQUIRED", "WATCH", "SETUP DEVELOPING", "NEAR ENTRY",
    "ENTRY CONDITIONS MET", "OVEREXTENDED", "DISTRIBUTION RISK", "THESIS DETERIORATING",
    "THESIS INVALIDATED",
]
WATCHED_STATUSES = {"WATCH", "SETUP DEVELOPING", "NEAR ENTRY", "ENTRY CONDITIONS MET",
                    "OVEREXTENDED", "THESIS DETERIORATING"}


# ----------------------------------------------------------------------------
# generic helpers
# ----------------------------------------------------------------------------
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


def _first(d: dict, *keys: str) -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _lin(v: float, bad: float, good: float) -> float:
    """Linear map v from [bad, good] to [0, 1] (works for either direction)."""
    if good == bad:
        return 1.0 if v >= good else 0.0
    return _clamp((v - bad) / (good - bad))


def _truthy(x: Any) -> bool:
    if isinstance(x, str):
        return x.strip().lower() not in ("", "none", "null", "false", "0", "no", "revoked", "disabled")
    return bool(x)


def _chase(breakout: dict) -> bool:
    """m14 returns chase_risk as a dict with an 'overextended' bool; accept bool too."""
    cr = breakout.get("chase_risk")
    if isinstance(cr, dict):
        return bool(cr.get("overextended")) or bool(breakout.get("overextended"))
    return _truthy(cr) or _truthy(breakout.get("overextended"))


class _Acc:
    """Accumulates weighted sub-criteria for one bucket."""

    def __init__(self) -> None:
        self.pts: list[tuple[float, float]] = []  # (score, weight)
        self.lines: list[str] = []
        self.unknown_weight = 0.0
        self.total_weight = 0.0

    def add(self, score: float, weight: float, line: str) -> None:
        self.pts.append((_clamp(score), weight))
        self.total_weight += weight
        self.lines.append(line)

    def unknown(self, weight: float, line: str) -> None:
        # missing criteria earn partial credit, capped
        self.pts.append((MISSING_CAP, weight))
        self.total_weight += weight
        self.unknown_weight += weight
        self.lines.append(f"{UNKNOWN_PREFIX} {line}")

    def result(self) -> tuple[float, list[str]]:
        if self.total_weight <= 0:
            return MISSING_CAP, [f"{UNKNOWN_PREFIX} no inputs supplied"]
        s = sum(p * w for p, w in self.pts) / self.total_weight
        if self.unknown_weight >= self.total_weight:  # fully missing
            s = min(s, MISSING_CAP)
        elif self.unknown_weight > 0:
            # cap proportional to how much is known: known part can earn full credit,
            # unknown part capped at MISSING_CAP
            known_frac = 1.0 - self.unknown_weight / self.total_weight
            s = min(s, known_frac * 1.0 + (1.0 - known_frac) * MISSING_CAP)
        return round(_clamp(s), 4), self.lines


# ----------------------------------------------------------------------------
# bucket helpers
# ----------------------------------------------------------------------------
def sub_market_execution(depth: dict | None = None, lp: dict | None = None, **_: Any) -> tuple[float, list[str]]:
    depth, lp = _d(depth), _d(lp)
    a = _Acc()
    if not depth and not lp:
        a.unknown(1.0, "no depth or LP module output")
        return a.result()

    liq = _num(_first(depth, "liquidity_usd", "liquidity_usd_total")) or _num(_first(lp, "liquidity_usd", "total_liquidity_usd"))
    if liq is None:
        a.unknown(1.0, "liquidity_usd missing")
    else:
        a.add(_lin(liq, 10_000, 300_000), 1.0, f"liquidity ${liq:,.0f}")

    cap3 = _num(_first(depth, "exit_capacity_usd_3pct", "sell_capacity_3pct_usd", "exit_capacity_3pct"))
    cap5 = _num(_first(depth, "exit_capacity_usd_5pct", "sell_capacity_5pct_usd", "exit_capacity_5pct"))
    if cap3 is None and cap5 is None:
        a.unknown(1.5, "executable sell depth (3%/5% impact capacity) missing")
    else:
        cap = cap3 if cap3 is not None else cap5
        a.add(_lin(cap, 1_000, 50_000), 1.5, f"executable sell depth ${cap:,.0f} at {'3' if cap3 is not None else '5'}% impact")

    status = str(_first(depth, "route_status", "status") or "").upper()
    no_route = depth.get("no_route") is True or status in ("NO_ROUTE", "ERROR")
    hops = _num(_first(depth, "n_hops", "hops"))
    if not status and hops is None and "no_route" not in depth:
        a.unknown(1.0, "route quality missing")
    elif no_route:
        a.add(0.0, 1.0, f"no sell route ({status or 'no_route'})")
    else:
        h = hops if hops is not None else 1
        a.add(1.0 if h <= 1 else 0.7 if h == 2 else 0.4, 1.0, f"route OK, {int(h)} hop(s)")

    fric = _num(_first(depth, "friction_pct", "round_trip_cost_pct", "spread_pct"))
    if fric is None:
        a.unknown(0.5, "friction (round-trip cost) missing")
    else:
        a.add(_lin(fric, 8.0, 1.0), 0.5, f"round-trip friction {fric:.2f}%")
    return a.result()


def sub_supply_ownership(holders: dict | None = None, clusters: dict | None = None,
                         early: dict | None = None, **_: Any) -> tuple[float, list[str]]:
    holders, clusters, early = _d(holders), _d(clusters), _d(early)
    a = _Acc()
    if not holders and not clusters and not early:
        a.unknown(1.0, "no holder, cluster or early-wallet module output")
        return a.result()

    top10 = _num(_first(holders, "adjusted_top10_pct", "top10_adjusted_pct", "top_10_pct"))
    if top10 is None:
        a.unknown(1.5, "adjusted top-10 ownership missing")
    else:
        a.add(_lin(top10, 50.0, 15.0), 1.5, f"adjusted top-10 holds {top10:.1f}%")

    largest = _num(_first(holders, "largest_unexplained_pct", "largest_unexplained_economic_pct", "largest_economic_holder_pct"))
    if largest is None:
        a.unknown(1.0, "largest unexplained economic holder missing")
    else:
        a.add(_lin(largest, 15.0, 2.0), 1.0, f"largest unexplained holder {largest:.1f}%")

    cl = _num(_first(clusters, "cluster_adjusted_ownership_pct", "cluster_adjusted_pct", "combined_pct"))
    if cl is None:
        a.unknown(1.0, "cluster-adjusted ownership missing")
    else:
        conf = str(clusters.get("confidence") or "").upper()
        a.add(_lin(cl, 25.0, 5.0), 1.0, f"cluster-adjusted ownership {cl:.1f}% (confidence {conf or 'n/a'})")

    dev = _num(_first(holders, "dev_holding_pct", "dev_pct"))
    if dev is None:
        dev = _num(_first(early, "dev_holding_pct", "insider_holding_pct"))
    if dev is None:
        a.unknown(0.5, "dev/insider holding missing")
    else:
        a.add(_lin(dev, 10.0, 0.0), 0.5, f"dev/insider holding {dev:.1f}%")

    direction = str(_first(early, "large_holder_net_direction", "direction") or "").upper()
    if not direction:
        a.unknown(1.0, "early-wallet net direction missing")
    else:
        m = {"ACCUMULATING": 1.0, "HOLDING": 0.85, "SCALING_OUT": 0.4, "DISTRIBUTING": 0.1, "EXITING": 0.0}
        a.add(m.get(direction, 0.5), 1.0, f"early wallets {direction}")
    return a.result()


def sub_token_lp_safety(mechanics: dict | None = None, lp: dict | None = None, **_: Any) -> tuple[float, list[str]]:
    mechanics, lp = _d(mechanics), _d(lp)
    a = _Acc()
    if not mechanics and not lp:
        a.unknown(1.0, "no mechanics or LP module output")
        return a.result()

    if not mechanics:
        a.unknown(2.0, "token mechanics missing")
    else:
        mint_active = _truthy(_first(mechanics, "mint_authority_active", "mint_authority"))
        freeze_active = _truthy(_first(mechanics, "freeze_authority_active", "freeze_authority"))
        perm = _truthy(_first(mechanics, "permanent_delegate_active", "permanent_delegate"))
        fee_bps = _num(_first(mechanics, "transfer_fee_bps")) or 0.0
        hook_unknown = _truthy(mechanics.get("transfer_hook_unknown")) or (
            _truthy(mechanics.get("transfer_hook_program")) and not _truthy(mechanics.get("transfer_hook_known")))
        non_transferable = _truthy(mechanics.get("non_transferable"))
        meta_mut = mechanics.get("metadata_mutable")
        bad = sum([mint_active, freeze_active, perm, fee_bps > 500, hook_unknown, non_transferable])
        a.add(0.0 if bad else 1.0, 1.5, "token mechanics " + ("clean (no mint/freeze/delegate/fee/hook issues)" if not bad else f"{bad} critical issue(s)"))
        if 0 < fee_bps <= 500:
            a.add(_lin(fee_bps, 500, 0), 0.5, f"transfer fee {fee_bps/100:.2f}%")
        else:
            a.add(1.0 if fee_bps == 0 else 0.0, 0.5, f"transfer fee {fee_bps/100:.2f}%")
        if meta_mut is None:
            a.unknown(0.3, "metadata mutability unknown")
        else:
            a.add(0.6 if _truthy(meta_mut) else 1.0, 0.3, f"metadata {'mutable' if _truthy(meta_mut) else 'immutable'}")

    if not lp:
        a.unknown(2.0, "LP analysis missing")
    else:
        risk = str(_first(lp, "lp_risk", "risk") or "").upper()
        if not risk:
            a.unknown(1.0, "lp_risk label missing")
        else:
            a.add({"LOW": 1.0, "MODERATE": 0.6, "HIGH": 0.2, "CRITICAL": 0.0}.get(risk, 0.4), 1.0, f"LP risk {risk}")
        locked = _num(_first(lp, "locked_pct", "lp_locked_pct", "burned_pct"))
        if locked is None:
            a.unknown(1.0, "LP locked/burned % missing")
        else:
            a.add(_lin(locked, 30.0, 95.0), 1.0, f"LP locked/burned {locked:.0f}%")
    return a.result()


def sub_demand_order_flow(orderflow: dict | None = None, manipulation: dict | None = None, **_: Any) -> tuple[float, list[str]]:
    orderflow, manipulation = _d(orderflow), _d(manipulation)
    a = _Acc()
    if not orderflow and not manipulation:
        a.unknown(1.0, "no order-flow or manipulation module output")
        return a.result()

    nb = _num(_first(orderflow, "net_buyers_h24", "net_buyers_24h", "net_buyers"))
    if nb is None:
        a.unknown(1.0, "net buyers missing")
    else:
        a.add(_lin(nb, -100.0, 200.0), 1.0, f"net buyers 24h {nb:+.0f}")

    ratio = _num(_first(orderflow, "buy_sell_vol_ratio", "buy_sell_ratio"))
    if ratio is None:
        a.unknown(1.0, "buy/sell volume ratio missing")
    else:
        a.add(_lin(ratio, 0.6, 1.5), 1.0, f"buy/sell volume ratio {ratio:.2f}")

    org = _num(_first(orderflow, "organic_share", "organic_volume_share", "organic_pct"))
    if org is None:
        a.unknown(1.0, "organic volume share missing")
    else:
        if org > 1.0:
            org /= 100.0
        a.add(_lin(org, 0.2, 0.8), 1.0, f"organic share {org:.0%}")

    bq = _num(_first(orderflow, "buyer_quality", "buyer_quality_score"))
    if bq is not None:
        a.add(_clamp(bq), 0.5, f"buyer quality {bq:.2f}")

    if not manipulation:
        a.unknown(1.0, "manipulation screen missing")
    else:
        label = str(_first(manipulation, "label", "verdict", "classification") or "").upper()
        wash = str(_first(manipulation, "wash_trading", "wash_trading_flag", "wash") or "").upper()
        s = 1.0
        if "SEVERELY" in label or wash == "HIGH":
            s = 0.0
        elif "MANIPULAT" in label or wash in ("MODERATE", "MEDIUM"):
            s = 0.4
        a.add(s, 1.0, f"manipulation screen {label or 'n/a'} / wash {wash or 'n/a'}")
    return a.result()


def sub_price_structure_entry(structure: dict | None = None, breakout: dict | None = None,
                              entries: dict | None = None, **_: Any) -> tuple[float, list[str]]:
    structure, breakout, entries = _d(structure), _d(breakout), _d(entries)
    a = _Acc()
    if not structure and not breakout and not entries:
        a.unknown(1.0, "no structure, breakout or entry module output")
        return a.result()

    st = str(_first(structure, "structure", "label", "trend") or "").upper()
    if not st:
        a.unknown(1.0, "structure label missing")
    else:
        m = {"UPTREND": 0.9, "RANGE": 0.7, "BASE": 0.75, "CONSOLIDATION": 0.7, "DOWNTREND": 0.2, "CAPITULATION": 0.3}
        a.add(m.get(st, 0.5), 1.0, f"structure {st}")

    levels_ok = _first(structure, "support_defined", "levels_defined", "has_levels")
    if levels_ok is None:
        n_levels = len(structure.get("levels") or []) if isinstance(structure.get("levels"), list) else None
        levels_ok = None if n_levels is None else n_levels > 0
    if levels_ok is None:
        a.unknown(0.5, "support/resistance levels unknown")
    else:
        a.add(1.0 if levels_ok else 0.2, 0.5, "levels " + ("defined" if levels_ok else "undefined"))

    bc = str(_first(breakout, "classification", "label", "state") or "").upper()
    if not bc:
        a.unknown(1.0, "breakout classification missing")
    else:
        m = {"BREAKOUT_RETEST": 1.0, "RETEST": 1.0, "BREAKOUT_CONFIRMED": 0.9, "CONFIRMED_BREAKOUT": 0.9, "CONFIRMED": 0.9,
             "BREAKOUT": 0.8, "RECLAIM": 0.75, "EARLY_BREAKOUT_ATTEMPT": 0.55, "COILING": 0.7, "SETUP": 0.65,
             "NO_BREAKOUT": 0.45, "NO_SETUP": 0.2, "FAILED_BREAKOUT": 0.1, "CHASE": 0.3, "EXTENDED": 0.3}
        a.add(m.get(bc, 0.4), 1.0, f"breakout state {bc}")
    if _chase(breakout):
        a.add(0.0, 0.5, "chase risk flagged (extended from base)")

    in_zone = _first(entries, "in_zone", "price_in_zone")
    zones = entries.get("zones") if isinstance(entries.get("zones"), list) else []
    if in_zone is None and zones:
        in_zone = any(_truthy(z.get("in_zone")) for z in zones if isinstance(z, dict))
    if in_zone is None:
        a.unknown(0.75, "entry zone / price-in-zone unknown")
    else:
        a.add(1.0 if in_zone else 0.5, 0.75, "price " + ("inside" if in_zone else "outside") + " an entry zone")

    inv = _first(entries, "invalidation_defined", "invalidation_level", "invalidation_price")
    if inv is None and zones:
        inv = any(z.get("invalidation") is not None or z.get("invalidation_level") is not None for z in zones if isinstance(z, dict))
    if inv is None:
        a.unknown(0.75, "invalidation level unknown")
    else:
        a.add(1.0 if _truthy(inv) else 0.0, 0.75, "invalidation " + ("defined" if _truthy(inv) else "undefined"))
    return a.result()


def sub_attention_narrative(attention: dict | None = None, **_: Any) -> tuple[float, list[str]]:
    attention = _d(attention)
    a = _Acc()
    if not attention:
        a.unknown(1.0, "no attention module output")
        return a.result()
    trend = str(attention.get("trend") or "").upper()
    if not trend:
        a.unknown(1.0, "attention trend missing")
    else:
        a.add({"ACCELERATION": 1.0, "STABILITY": 0.6, "EXHAUSTION": 0.1}.get(trend, 0.4), 1.0, f"attention trend {trend}")
    ns = _num(_first(attention, "narrative_strength", "narrative_score"))
    if ns is None:
        a.unknown(1.0, "narrative strength missing")
    else:
        if ns > 1.0:
            ns /= 100.0
        a.add(_clamp(ns), 1.0, f"narrative strength {ns:.2f}")
    org = _first(attention, "organic", "organic_social")
    if org is None:
        a.unknown(0.5, "organic vs paid attention unknown")
    else:
        a.add(1.0 if _truthy(org) else 0.2, 0.5, "attention " + ("organic" if _truthy(org) else "paid/boosted"))
    return a.result()


def sub_lifecycle_relative_strength(lifecycle: dict | None = None, rs: dict | None = None, **_: Any) -> tuple[float, list[str]]:
    lifecycle, rs = _d(lifecycle), _d(rs)
    a = _Acc()
    if not lifecycle and not rs:
        a.unknown(1.0, "no lifecycle or relative-strength module output")
        return a.result()
    stage = str(lifecycle.get("stage") or "").upper()
    sub = str(lifecycle.get("sub_stage") or "").upper()
    if not stage or stage == "UNKNOWN":
        a.unknown(1.0, "lifecycle stage unknown")
    else:
        m = {"LAUNCH": 0.3, "DISCOVERY": 0.8, "EARLY_EXPANSION": 1.0, "BROAD_ATTENTION": 0.7, "MANIA": 0.2,
             "DISTRIBUTION": 0.1, "BREAKDOWN": 0.05, "POST_BREAKDOWN": 0.3}
        s = m.get(stage, 0.4)
        if stage == "POST_BREAKDOWN":
            s = {"REACCUMULATION": 0.6, "DEAD_CAT_BOUNCE": 0.15, "EXTINCTION": 0.0}.get(sub, 0.2)
        conf = str(lifecycle.get("confidence") or "").upper()
        if conf == "LOW":
            s = s * 0.7 + 0.4 * 0.3  # shrink toward partial credit
        a.add(s, 1.0, f"lifecycle {stage}{('/' + sub) if sub else ''} (confidence {conf or 'n/a'})")
    labels = rs.get("label") if isinstance(rs.get("label"), dict) else {}
    vals = [str(v).upper() for v in labels.values() if v]
    if not vals:
        a.unknown(1.0, "relative strength labels missing")
    else:
        s = sum({"STRONG": 1.0, "NEUTRAL": 0.55, "WEAK": 0.1}.get(v, 0.5) for v in vals) / len(vals)
        a.add(s, 1.0, "relative strength " + "/".join(vals))
    ll = str(rs.get("leader_laggard") or "").upper()
    if ll:
        a.add(1.0 if "LEADER" in ll else 0.1 if "LAGGARD" in ll else 0.5, 0.5, f"peer position {ll}")
    return a.result()


def sub_risk_reward_exitability(rr: dict | None = None, sizing: dict | None = None,
                                depth: dict | None = None, **_: Any) -> tuple[float, list[str]]:
    rr, sizing, depth = _d(rr), _d(sizing), _d(depth)
    a = _Acc()
    if not rr and not sizing and not depth:
        a.unknown(1.0, "no R:R, sizing or depth module output")
        return a.result()
    ratio = _num(_first(rr, "rr_ratio", "reward_risk", "rr"))
    if ratio is None:
        a.unknown(1.5, "reward:risk ratio missing")
    else:
        a.add(_lin(ratio, 1.0, 4.0), 1.5, f"reward:risk {ratio:.2f}")
    ev = _num(_first(rr, "ev_r", "expected_value_r", "ev"))
    if ev is None:
        a.unknown(1.0, "expected value missing")
    else:
        a.add(_lin(ev, -0.2, 1.0), 1.0, f"EV {ev:+.2f}R")
    inv = _first(rr, "invalidation_defined", "invalidation_price", "invalidation_level")
    if inv is None:
        a.unknown(1.0, "invalidation definition missing")
    else:
        a.add(1.0 if _truthy(inv) else 0.0, 1.0, "invalidation " + ("defined" if _truthy(inv) else "undefined"))
    fits = _first(sizing, "fits_constraints", "within_constraints", "ok")
    if fits is None:
        a.unknown(0.75, "sizing constraint check missing")
    else:
        a.add(1.0 if _truthy(fits) else 0.3, 0.75, "size " + ("within" if _truthy(fits) else "exceeds") + " risk and liquidity constraints")
    cap3 = _num(_first(depth, "exit_capacity_usd_3pct", "sell_capacity_3pct_usd", "exit_capacity_3pct"))
    size = _num(_first(sizing, "size_usd", "recommended_size_usd", "position_size_usd"))
    if cap3 is None:
        a.unknown(1.0, "exit capacity missing")
    elif size is not None and size > 0:
        cov = cap3 / size
        a.add(_lin(cov, 0.5, 3.0), 1.0, f"exit capacity covers {cov:.1f}x intended size")
    else:
        a.add(_lin(cap3, 1_000, 50_000), 1.0, f"exit capacity ${cap3:,.0f} at 3% impact")
    return a.result()


HELPERS: dict[str, Callable[..., tuple[float, list[str]]]] = {
    "market_execution": sub_market_execution,
    "supply_ownership": sub_supply_ownership,
    "token_lp_safety": sub_token_lp_safety,
    "demand_order_flow": sub_demand_order_flow,
    "price_structure_entry": sub_price_structure_entry,
    "attention_narrative": sub_attention_narrative,
    "lifecycle_relative_strength": sub_lifecycle_relative_strength,
    "risk_reward_exitability": sub_risk_reward_exitability,
}


def derive_components(**modules: Any) -> tuple[dict[str, float], dict[str, list[str]]]:
    comps: dict[str, float] = {}
    rats: dict[str, list[str]] = {}
    for b, fn in HELPERS.items():
        try:
            s, lines = fn(**modules)
        except Exception as e:  # never raise
            s, lines = MISSING_CAP, [f"{UNKNOWN_PREFIX} helper error {type(e).__name__}: {e}"]
        comps[b] = s
        rats[b] = lines
    return comps, rats


# ----------------------------------------------------------------------------
# fatal flags
# ----------------------------------------------------------------------------
def fatal_flags(**modules: Any) -> list[dict]:
    flags: list[dict] = []

    def add(flag: str, evidence: str, category: str, severity: str = "FATAL") -> None:
        flags.append({"flag": flag, "evidence": evidence, "severity": severity, "category": category})

    mech = _d(modules.get("mechanics"))
    if mech:
        if _truthy(_first(mech, "mint_authority_active", "mint_authority")):
            add("MINT_AUTHORITY_ACTIVE", f"mint authority {mech.get('mint_authority') or 'active'}", "mechanics")
        if _truthy(_first(mech, "freeze_authority_active", "freeze_authority")):
            add("FREEZE_AUTHORITY_ACTIVE", f"freeze authority {mech.get('freeze_authority') or 'active'}", "mechanics")
        if _truthy(_first(mech, "permanent_delegate_active", "permanent_delegate")):
            add("PERMANENT_DELEGATE", f"permanent delegate {mech.get('permanent_delegate') or 'set'}", "mechanics")
        fee = _num(mech.get("transfer_fee_bps"))
        if fee is not None and fee > 500:
            add("TRANSFER_FEE_GT_5PCT", f"transfer fee {fee/100:.2f}%", "mechanics")
        hook_unknown = _truthy(mech.get("transfer_hook_unknown")) or (
            _truthy(mech.get("transfer_hook_program")) and not _truthy(mech.get("transfer_hook_known")))
        if hook_unknown:
            add("TRANSFER_HOOK_UNKNOWN", f"transfer hook program {mech.get('transfer_hook_program') or 'unknown'}", "mechanics")
        if _truthy(mech.get("non_transferable")):
            add("NON_TRANSFERABLE", "non-transferable extension present", "mechanics")
        # EVM contract-risk flags (chains/evm.py). Fatal: honeypot, cannot buy, hidden owner, extreme tax, failed sell simulation, proxy with live owner.
        evm_flags = set(mech.get("flags") or []) if mech.get("contract_risk") else set()
        for f, ev in (("HONEYPOT", "honeypot flagged by GoPlus or honeypot.is simulation"), ("CANNOT_BUY", "buying disabled"), ("HIDDEN_OWNER", "hidden owner: renounce is not real"),
                      ("EXTREME_TAX", f"round-trip tax {mech.get('transfer_fee_pct')}%"), ("SIMULATION_FAILED", "a sell could not be simulated"), ("AIRDROP_SCAM", "GoPlus airdrop-scam flag"),
                      ("SELFDESTRUCT", "selfdestruct present"), ("CREATOR_PRIOR_HONEYPOT", "creator deployed honeypots before")):
            if f in evm_flags:
                add(f, ev, "mechanics")
        if "UPGRADEABLE_PROXY" in evm_flags and mech.get("owner_state") == "ACTIVE":
            add("PROXY_WITH_LIVE_OWNER", "upgradeable proxy and a live owner: the contract can be replaced", "mechanics")
        if "TAX_MODIFIABLE" in evm_flags and mech.get("owner_state") == "ACTIVE":
            add("TAX_MODIFIABLE_BY_OWNER", "owner can change the tax at any time (sell tax can become 100%)", "mechanics")

    lp = _d(modules.get("lp"))
    if str(_first(lp, "lp_risk", "risk") or "").upper() == "CRITICAL":
        add("LP_RISK_CRITICAL", str(lp.get("reason") or lp.get("why") or "lp_risk CRITICAL"), "liquidity")

    holders = _d(modules.get("holders"))
    largest = _num(_first(holders, "largest_unexplained_pct", "largest_unexplained_economic_pct", "largest_economic_holder_pct"))
    if largest is not None and largest > 15:
        add("LARGEST_HOLDER_GT_15PCT", f"largest unexplained economic holder {largest:.1f}%", "ownership")
    top10 = _num(_first(holders, "adjusted_top10_pct", "top10_adjusted_pct", "top_10_pct"))
    if top10 is not None and top10 > 50:
        add("TOP10_GT_50PCT", f"adjusted top-10 {top10:.1f}%", "ownership")

    clusters = _d(modules.get("clusters"))
    cl = _num(_first(clusters, "cluster_adjusted_ownership_pct", "cluster_adjusted_pct", "combined_pct"))
    if cl is not None and cl > 25 and str(clusters.get("confidence") or "").upper() == "HIGH":
        add("CLUSTER_OWNERSHIP_GT_25PCT", f"cluster-adjusted ownership {cl:.1f}% (HIGH confidence)", "ownership")

    depth = _d(modules.get("depth"))
    if depth:
        status = str(_first(depth, "route_status", "status") or "").upper()
        if depth.get("no_route") is True or status in ("NO_ROUTE", "ERROR"):
            add("NO_SELL_ROUTE", f"sell route status {status or 'no_route'}", "exitability")
        imp5k = _num(_first(depth, "sell_impact_5k_pct", "impact_sell_5000_pct"))
        cap5 = _num(_first(depth, "exit_capacity_usd_5pct", "sell_capacity_5pct_usd", "exit_capacity_5pct"))
        if imp5k is not None and imp5k > 5:
            add("CANNOT_EXIT_5K", f"$5k sell impact {imp5k:.1f}% > 5%", "exitability")
        elif imp5k is None and cap5 is not None and cap5 < 5_000:
            add("CANNOT_EXIT_5K", f"exit capacity at 5% impact only ${cap5:,.0f}", "exitability")

    manip = _d(modules.get("manipulation"))
    label = str(_first(manip, "label", "verdict", "classification") or "").upper()
    wash = str(_first(manip, "wash_trading", "wash_trading_flag", "wash") or "").upper()
    if "SEVERELY MANIPULATED" in label or label == "SEVERELY_MANIPULATED":
        add("SEVERELY_MANIPULATED", f"manipulation verdict {label}", "manipulation")
    if wash == "HIGH":
        add("WASH_TRADING_HIGH", "wash-trading flag HIGH", "manipulation")

    early = _d(modules.get("early"))
    direction = str(_first(early, "large_holder_net_direction", "direction") or "").upper()
    if direction in ("DISTRIBUTING", "EXITING"):
        price_down = _truthy(early.get("price_down")) or (_num(early.get("price_chg_24h")) or 0) < 0
        vol_collapse = _truthy(early.get("volume_collapsing")) or (_num(early.get("vol_ratio")) is not None and _num(early.get("vol_ratio")) < 0.5)
        if price_down and vol_collapse:
            add("INSIDER_DISTRIBUTION", f"large holders {direction} with price down and volume collapsing", "distribution")
    return flags


# ----------------------------------------------------------------------------
# score
# ----------------------------------------------------------------------------
def _component_value(v: Any) -> tuple[float | None, list[str]]:
    if isinstance(v, dict):
        return _num(_first(v, "score", "value")), list(v.get("rationale") or [])
    if isinstance(v, (list, tuple)) and len(v) == 2:
        return _num(v[0]), list(v[1] or [])
    return _num(v), []


def score(components: dict | None, **modules: Any) -> dict:
    components = _d(components)
    breakdown: dict[str, dict] = {}
    total = 0.0
    unknown_buckets: list[str] = []
    for b, mx in MAX_POINTS.items():
        s, rat = _component_value(components.get(b))
        if s is None:
            s = MISSING_CAP
            rat = rat + [f"{UNKNOWN_PREFIX} component {b} not supplied; partial credit {MISSING_CAP}"]
        s = _clamp(s)
        if any(str(l).startswith(UNKNOWN_PREFIX) for l in rat):
            unknown_buckets.append(b)
        pts = round(s * mx, 2)
        total += pts
        breakdown[b] = {"points": pts, "max": mx, "score": round(s, 4), "rationale": rat}
    flags = fatal_flags(**modules) if modules else []
    extra = components.get("fatal_flags")
    if isinstance(extra, list):
        flags = flags + [f for f in extra if isinstance(f, dict)]
    return {
        "total": int(round(total)),
        "breakdown": breakdown,
        "fatal_flags": flags,
        "untradeable": bool(flags),
        "unknown_buckets": unknown_buckets,
        "unknown_count": sum(1 for b in breakdown.values() for l in b["rationale"] if str(l).startswith(UNKNOWN_PREFIX)),
    }


# ----------------------------------------------------------------------------
# status
# ----------------------------------------------------------------------------
def assign_status(score_result: dict | None, breakout: dict | None = None, entries: dict | None = None,
                  lifecycle: dict | None = None, early: dict | None = None,
                  monitor_diff: dict | None = None) -> dict:
    sr, breakout, entries = _d(score_result), _d(breakout), _d(entries)
    lifecycle, early, monitor_diff = _d(lifecycle), _d(early), _d(monitor_diff)
    flags = [f for f in (sr.get("fatal_flags") or []) if isinstance(f, dict)]
    prev_status = str(monitor_diff.get("previous_status") or "").upper()
    was_watched = prev_status in WATCHED_STATUSES

    if flags:
        cats = {str(f.get("category") or "").lower() for f in flags}
        names = ", ".join(str(f.get("flag")) for f in flags)
        if was_watched:
            return {"status": "THESIS INVALIDATED",
                    "reasoning": f"Previously {prev_status}; fatal flag(s) appeared: {names}"}
        if "distribution" in cats and cats <= {"distribution", "ownership"}:
            return {"status": "DISTRIBUTION RISK",
                    "reasoning": f"Fatal distribution evidence: {names}"}
        return {"status": "REJECTED", "reasoning": f"Fatal flag(s): {names}"}

    # non-fatal but unmistakable distribution signal
    direction = str(_first(early, "large_holder_net_direction", "direction") or "").upper()
    stage = str(lifecycle.get("stage") or "").upper()
    lc_conf = str(lifecycle.get("confidence") or "").upper()
    if direction in ("DISTRIBUTING", "EXITING") or (stage == "DISTRIBUTION" and lc_conf != "LOW"):
        return {"status": "DISTRIBUTION RISK",
                "reasoning": f"Large holders {direction or 'n/a'}; lifecycle {stage or 'n/a'}"}

    if monitor_diff:
        if _truthy(monitor_diff.get("invalidated")):
            return {"status": "THESIS INVALIDATED", "reasoning": str(monitor_diff.get("reason") or "invalidation level breached")}
        if _truthy(monitor_diff.get("deteriorating")) or (_num(monitor_diff.get("score_delta")) or 0) <= -10:
            return {"status": "THESIS DETERIORATING",
                    "reasoning": str(monitor_diff.get("reason") or f"score delta {monitor_diff.get('score_delta')}")}

    unknown_buckets = sr.get("unknown_buckets") or []
    unknown_count = int(sr.get("unknown_count") or 0)
    if len(unknown_buckets) >= 4 or unknown_count >= 8:
        return {"status": "RESEARCH REQUIRED",
                "reasoning": f"{len(unknown_buckets)} of 8 buckets rely on missing inputs ({unknown_count} unknown lines): "
                             + ", ".join(unknown_buckets)}

    if _chase(breakout):
        return {"status": "OVEREXTENDED", "reasoning": "breakout module flags chase risk (price extended from base)"}

    bc = str(_first(breakout, "classification", "label", "state") or "").upper()
    in_zone = _first(entries, "in_zone", "price_in_zone")
    zones = entries.get("zones") if isinstance(entries.get("zones"), list) else []
    if in_zone is None and zones:
        in_zone = any(_truthy(z.get("in_zone")) for z in zones if isinstance(z, dict))
    near_zone = _truthy(_first(entries, "near_zone", "approaching_zone"))
    dist = _num(_first(entries, "distance_to_zone_pct", "pct_to_zone"))
    if dist is not None and abs(dist) <= 5:
        near_zone = True
    inv_defined = _truthy(_first(entries, "invalidation_defined", "invalidation_level", "invalidation_price"))
    total = int(sr.get("total") or 0)

    confirmed = bc in ("BREAKOUT_RETEST", "RETEST", "BREAKOUT_CONFIRMED", "CONFIRMED", "BREAKOUT")
    if confirmed and _truthy(in_zone) and inv_defined and total >= 60:
        return {"status": "ENTRY CONDITIONS MET",
                "reasoning": f"{bc} with price inside entry zone, invalidation defined, score {total}"}
    if (confirmed and (_truthy(in_zone) or near_zone)) or (_truthy(in_zone) and inv_defined):
        why = "inside zone" if _truthy(in_zone) else "approaching zone"
        return {"status": "NEAR ENTRY", "reasoning": f"{bc or 'setup'} {why}" + ("" if inv_defined else ", invalidation not yet defined")}
    if bc in ("COILING", "SETUP", "BASE", "COMPRESSION") or near_zone or zones:
        return {"status": "SETUP DEVELOPING", "reasoning": f"breakout state {bc or 'n/a'}; zones defined {bool(zones)}"}
    if total < 40:
        return {"status": "WATCH", "reasoning": f"score {total} below actionable threshold; no setup"}
    return {"status": "WATCH", "reasoning": f"no actionable setup (breakout state {bc or 'n/a'})"}


# ----------------------------------------------------------------------------
# rank
# ----------------------------------------------------------------------------
def _cand_score(c: dict) -> dict:
    sr = c.get("score_result") or c.get("score")
    if isinstance(sr, dict) and "total" in sr:
        return sr
    if isinstance(c.get("components"), dict):
        return score(c["components"], **_d(c.get("modules")))
    mods = _d(c.get("modules")) or {k: c[k] for k in HELPERS_INPUT_KEYS if isinstance(c.get(k), dict)}
    comps, rats = derive_components(**mods)
    return score({b: (comps[b], rats[b]) for b in comps}, **mods)


HELPERS_INPUT_KEYS = ["depth", "lp", "mechanics", "holders", "clusters", "early", "orderflow", "structure",
                      "breakout", "entries", "rr", "attention", "manipulation", "lifecycle", "rs", "sizing"]


def rank(candidates: list[dict] | None) -> dict:
    rows: list[dict] = []
    for c in (candidates if isinstance(candidates, (list, tuple)) else []):
        if not isinstance(c, dict):
            continue
        mods = _d(c.get("modules")) or {k: c[k] for k in HELPERS_INPUT_KEYS if isinstance(c.get(k), dict)}
        sr = _cand_score(c)
        bd = sr.get("breakdown") or {}

        def pts(b: str) -> float:
            return float(_d(bd.get(b)).get("score") or 0.0)

        rr = _d(mods.get("rr"))
        depth = _d(mods.get("depth"))
        entries = _d(mods.get("entries"))
        lifecycle = _d(mods.get("lifecycle"))
        ev = _num(_first(rr, "ev_r", "expected_value_r", "ev"))
        inv_defined = _truthy(_first(rr, "invalidation_defined", "invalidation_price", "invalidation_level")) or \
            _truthy(_first(entries, "invalidation_defined", "invalidation_level", "invalidation_price"))
        cap3 = _num(_first(depth, "exit_capacity_usd_3pct", "sell_capacity_3pct_usd", "exit_capacity_3pct"))
        has_exit = (cap3 is not None and cap3 >= 5_000) or (not depth and pts("market_execution") >= 0.6)
        status = c.get("status")
        if not isinstance(status, dict):
            status = assign_status(sr, breakout=mods.get("breakout"), entries=entries, lifecycle=lifecycle,
                                   early=mods.get("early"), monitor_diff=c.get("monitor_diff"))
        rows.append({
            "symbol": c.get("symbol"),
            "mint": c.get("mint"),
            "total": sr.get("total"),
            "untradeable": bool(sr.get("untradeable")),
            "fatal_flags": [f.get("flag") for f in sr.get("fatal_flags") or []],
            "status": status.get("status"),
            "structure": round(pts("price_structure_entry"), 2),
            "exitability": round((pts("market_execution") + pts("risk_reward_exitability")) / 2, 2),
            "ownership": round(pts("supply_ownership"), 2),
            "lifecycle": lifecycle.get("stage"),
            "lifecycle_score": round(pts("lifecycle_relative_strength"), 2),
            "entry_quality": round(pts("price_structure_entry"), 2),
            "invalidation_clarity": "DEFINED" if inv_defined else "UNDEFINED",
            "ev_r": ev,
            "exit_capacity_3pct_usd": cap3,
            "has_exit_capacity": has_exit,
            "unknown_buckets": len(sr.get("unknown_buckets") or []),
        })

    rows.sort(key=lambda r: ((r["total"] or 0) if not r["untradeable"] else -1), reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    tradeable = [r for r in rows if not r["untradeable"]]
    best_token = tradeable[0] if tradeable else None
    # best trade: highest EV with defined invalidation among those with exit capacity
    pool = [r for r in tradeable if r["invalidation_clarity"] == "DEFINED" and r["has_exit_capacity"] and r["ev_r"] is not None]
    best_trade = max(pool, key=lambda r: (r["ev_r"], r["total"] or 0)) if pool else None

    note = None
    if best_token and best_trade and best_token["mint"] != best_trade["mint"]:
        note = (f"Best token by score is {best_token['symbol']} ({best_token['total']}), but the best trade is "
                f"{best_trade['symbol']} ({best_trade['total']}): EV {best_trade['ev_r']:+.2f}R with a defined invalidation "
                f"and exit capacity ${(best_trade['exit_capacity_3pct_usd'] or 0):,.0f} at 3% impact. "
                f"{best_token['symbol']} " +
                ("lacks a defined invalidation" if best_token["invalidation_clarity"] != "DEFINED" else
                 "lacks exit capacity" if not best_token["has_exit_capacity"] else
                 "has no EV estimate" if best_token["ev_r"] is None else
                 f"has lower EV ({best_token['ev_r']:+.2f}R)") + ".")
    elif best_token and not best_trade:
        note = (f"Best token by score is {best_token['symbol']} ({best_token['total']}), but no candidate qualifies as a "
                "trade: none combine a defined invalidation, exit capacity and an EV estimate.")
    elif best_token and best_trade:
        note = f"{best_token['symbol']} is both the best token and the best trade."
    elif not tradeable and rows:
        note = "All candidates carry fatal flags; nothing is tradeable."

    return {
        "rows": rows,
        "best_token": best_token["mint"] if best_token else None,
        "best_trade": best_trade["mint"] if best_trade else None,
        "best_token_vs_best_trade": note,
        "n": len(rows),
        "n_tradeable": len(tradeable),
    }


def evaluate(**modules: Any) -> dict:
    comps, rats = derive_components(**modules)
    sr = score({b: (comps[b], rats[b]) for b in comps}, **modules)
    st = assign_status(sr, breakout=modules.get("breakout"), entries=modules.get("entries"),
                       lifecycle=modules.get("lifecycle"), early=modules.get("early"),
                       monitor_diff=modules.get("monitor_diff"))
    sr["status"] = st["status"]
    sr["status_reasoning"] = st["reasoning"]
    sr["facts"] = []
    sr["inferences"] = [f"{b}: {sr['breakdown'][b]['points']}/{MAX_POINTS[b]}" for b in MAX_POINTS]
    sr["heuristics"] = [f"Missing inputs earn at most {MISSING_CAP} of a bucket", "Any fatal flag overrides the numeric score"]
    sr["unknowns"] = [l for b in sr["breakdown"].values() for l in b["rationale"] if str(l).startswith(UNKNOWN_PREFIX)]
    return sr
