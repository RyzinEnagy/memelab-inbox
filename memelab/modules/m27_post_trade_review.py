"""m27: post-trade review.

Public interface:
    review(position, exits, decision_log, price_path) -> dict
    store_review(con, position_id, review) -> int (trade_reviews.id)

position: {"id"?, "mint", "entry_price", "size_usd", "tokens"?, "invalidation_price", "max_risk_usd"?,
           "opened_at", "closed_at"?, "setup_type"?, ...}
exits: [{"exited_at","price","tokens","usd_realized","reason","displayed_value_usd","slippage_pct"}]
decision_log: [{"ts","info_available":{...},"action","reasoning"}]
    action in ENTER / ADD / TRIM / EXIT / HOLD (case-insensitive, substring match)
    info_available may carry: invalidation_price, size_usd, max_risk_usd, risk_budget_usd, exit_capacity_usd,
    exit_plan (bool or text), thesis_state ("IMPROVING"/"INTACT"/"DETERIORATING"/"INVALIDATED"),
    price, score, lifecycle, structure
price_path: [[ts, price], ...]

Decision quality is judged ONLY from decision_log entries and the information
recorded as available at that time. Outcome quality is judged from realized P&L in R.

Output keys match trade_reviews columns (quadrant, thesis_quality, entry_quality, sizing, execution,
risk_mgmt, profit_taking, exit_quality, process_errors, missed_evidence, unexpected, mae_pct, mfe_pct,
realized_pct, displayed_pct) plus: decision_grade, outcome_grade, realized_r, holding_hours,
avg_slippage_pct, lessons, facts, inferences, heuristics, unknowns.
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

TRADE_REVIEW_COLUMNS = [
    "quadrant", "thesis_quality", "entry_quality", "sizing", "execution", "risk_mgmt", "profit_taking",
    "exit_quality", "process_errors", "missed_evidence", "unexpected", "mae_pct", "mfe_pct", "realized_pct",
    "displayed_pct",
]


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


def _act(e: dict) -> str:
    return str(e.get("action") or "").upper()


def _is(e: dict, *kinds: str) -> bool:
    a = _act(e)
    return any(k in a for k in kinds)


def _mae_mfe(price_path: list, entry: float | None, t_open: float | None, t_close: float | None) -> tuple[float | None, float | None, int]:
    if entry is None or entry <= 0:
        return None, None, 0
    pts = []
    for row in price_path or []:
        if isinstance(row, (list, tuple)) and len(row) >= 2:
            ts, px = _num(row[0]), _num(row[1])
            if px is None or px <= 0:
                continue
            if t_open is not None and ts is not None and ts < t_open:
                continue
            if t_close is not None and ts is not None and ts > t_close:
                continue
            pts.append(px)
    if not pts:
        return None, None, 0
    lo, hi = min(pts), max(pts)
    mae = min(0.0, (lo / entry - 1) * 100)
    mfe = max(0.0, (hi / entry - 1) * 100)
    return round(mae, 2), round(mfe, 2), len(pts)


def review(position: dict | None, exits: list[dict] | None, decision_log: list[dict] | None,
           price_path: list | None) -> dict:
    p = _d(position)
    exits = [e for e in exits if isinstance(e, dict)] if isinstance(exits, (list, tuple)) else []
    log = [e for e in decision_log if isinstance(e, dict)] if isinstance(decision_log, (list, tuple)) else []
    log = sorted(log, key=lambda e: _num(e.get("ts")) or 0)
    price_path = price_path if isinstance(price_path, (list, tuple)) else []
    facts: list[str] = []
    inferences: list[str] = []
    heuristics: list[str] = [
        "Decision quality is judged only from decision_log entries and the information recorded at that time",
        "Outcome quality is judged from realized R (realized P&L / planned risk)",
        "GOOD outcome: realized R >= +0.5; BAD outcome: realized R <= -0.5; otherwise FLAT",
    ]
    unknowns: list[str] = []
    lessons: list[str] = []
    process_errors: list[str] = []
    missed: list[str] = []
    unexpected: list[str] = []

    entry = _num(p.get("entry_price"))
    size = _num(p.get("size_usd"))
    inv = _num(p.get("invalidation_price"))
    tokens = _num(p.get("tokens"))
    if tokens is None and entry and size:
        tokens = size / entry
    t_open = _num(p.get("opened_at"))
    t_close = _num(p.get("closed_at"))
    if t_close is None and exits:
        t_close = max((_num(e.get("exited_at")) or 0) for e in exits) or None
    if entry is None:
        unknowns.append("entry_price missing: returns and MAE/MFE cannot be computed")
    if size is None:
        unknowns.append("size_usd missing")

    # ---- realized vs displayed ----
    realized_usd = sum((_num(e.get("usd_realized")) or 0.0) for e in exits)
    displayed_usd = sum((_num(e.get("displayed_value_usd")) or (_num(e.get("usd_realized")) or 0.0)) for e in exits)
    tokens_sold = sum((_num(e.get("tokens")) or 0.0) for e in exits)
    cost_sold = None
    if entry and tokens_sold:
        cost_sold = tokens_sold * entry
    elif size and exits:
        cost_sold = size
    realized_pct = displayed_pct = None
    if cost_sold:
        realized_pct = round((realized_usd / cost_sold - 1) * 100, 2)
        displayed_pct = round((displayed_usd / cost_sold - 1) * 100, 2)
        facts.append(f"Realized {realized_pct:+.2f}% vs displayed {displayed_pct:+.2f}% on ${cost_sold:,.0f} cost sold")
        if displayed_pct - realized_pct > 2:
            inferences.append(f"Execution gap {displayed_pct - realized_pct:.2f}pp between displayed and realized return")
    elif not exits:
        unknowns.append("no exits: position still open or exits not recorded; realized return unknown")
    remaining = None
    if tokens is not None:
        remaining = max(0.0, tokens - tokens_sold)
        if remaining > 1e-9 and tokens:
            facts.append(f"{remaining/tokens*100:.1f}% of tokens still held (open remainder)")

    slips = [_num(e.get("slippage_pct")) for e in exits]
    slips = [s for s in slips if s is not None]
    avg_slip = round(sum(slips) / len(slips), 3) if slips else None
    if avg_slip is not None:
        facts.append(f"Average exit slippage {avg_slip:.2f}% over {len(slips)} exit(s)")
    elif exits:
        unknowns.append("slippage_pct missing on exits")

    holding_hours = None
    if t_open is not None and t_close is not None:
        holding_hours = round((t_close - t_open) / 3600, 2)
        facts.append(f"Holding period {holding_hours:.1f}h")
    else:
        unknowns.append("opened_at/closed_at missing: holding period unknown")

    mae, mfe, n_pts = _mae_mfe(price_path or [], entry, t_open, t_close)
    if n_pts:
        facts.append(f"MAE {mae:.2f}% / MFE {mfe:+.2f}% over {n_pts} price points")
    else:
        unknowns.append("price_path empty or outside holding window: MAE/MFE unknown")

    # ---- R multiple ----
    risk_usd = _num(p.get("max_risk_usd"))
    if risk_usd is None and entry and inv is not None and size and entry > 0:
        risk_usd = size * max(0.0, (entry - inv) / entry)
    realized_r = None
    if risk_usd and cost_sold:
        realized_r = round((realized_usd - cost_sold) / risk_usd, 2)
        facts.append(f"Realized {realized_r:+.2f}R on planned risk ${risk_usd:,.0f}")
    elif cost_sold:
        unknowns.append("planned risk undefined (no invalidation / max_risk_usd): R multiple unavailable")

    # ---- decision quality from the log ----
    entries_ = [e for e in log if _is(e, "ENTER", "OPEN", "BUY") and not _is(e, "ADD")]
    adds = [e for e in log if _is(e, "ADD", "SCALE_IN", "SCALE IN")]
    trims = [e for e in log if _is(e, "TRIM", "TAKE_PROFIT", "TAKE PROFIT", "PARTIAL")]
    exit_decisions = [e for e in log if _is(e, "EXIT", "CLOSE", "SELL") and not _is(e, "PARTIAL", "TRIM")]
    holds = [e for e in log if _is(e, "HOLD")]

    good_points = 0
    total_points = 0

    def mark(ok: bool | None, weight: int, good_msg: str, bad_msg: str, unknown_msg: str) -> str:
        nonlocal good_points, total_points
        if ok is None:
            unknowns.append(unknown_msg)
            return "UNKNOWN"
        total_points += weight
        if ok:
            good_points += weight
            return good_msg
        process_errors.append(bad_msg)
        return bad_msg

    if not log:
        unknowns.append("decision_log empty: decision quality cannot be judged")

    e0 = entries_[0] if entries_ else None
    info0 = _d(e0.get("info_available")) if e0 else {}

    # thesis quality: was there a stated reasoning and a thesis state at entry
    if e0 is None:
        thesis_quality = mark(None, 0, "", "", "no ENTER decision in log")
    else:
        has_reason = bool(str(e0.get("reasoning") or "").strip())
        has_inval_text = bool(info0.get("invalidation_text") or info0.get("thesis") or info0.get("thesis_state"))
        ok = has_reason and (has_inval_text or len(str(e0.get("reasoning") or "")) > 40)
        thesis_quality = mark(ok, 2, "GOOD: entry reasoning and thesis recorded",
                              "WEAK: entry reasoning thin or no thesis state recorded", "")

    # entry quality: defined invalidation at entry and entry in a setup
    if e0 is None:
        entry_quality = "UNKNOWN"
    else:
        inv0 = _num(info0.get("invalidation_price"))
        if inv0 is None and "invalidation_defined" in info0:
            inv0 = 1.0 if info0.get("invalidation_defined") else None
        has_inv = inv0 is not None
        setup = str(info0.get("setup") or info0.get("structure") or info0.get("breakout") or "").upper()
        chased = bool(info0.get("chase_risk")) or "CHASE" in setup or "EXTENDED" in setup
        ok = has_inv and not chased
        entry_quality = mark(ok, 3,
                             "GOOD: invalidation defined at entry" + (f", setup {setup}" if setup else ""),
                             ("BAD: " + ("no invalidation defined at entry" if not has_inv else "entered into chase/extended conditions")),
                             "")
        if not has_inv:
            lessons.append("Never enter without a price level that proves the thesis wrong")
        if chased:
            lessons.append("Entering extended from the base converts a good token into a bad trade")

    # sizing: within risk budget and liquidity constraint
    if e0 is None:
        sizing = "UNKNOWN"
    else:
        s0 = _num(info0.get("size_usd")) or size
        risk_budget = _num(info0.get("risk_budget_usd")) or _num(info0.get("max_risk_usd"))
        inv0 = _num(info0.get("invalidation_price"))
        px0 = _num(info0.get("price")) or entry
        exit_cap = _num(info0.get("exit_capacity_usd")) or _num(info0.get("exit_capacity_3pct_usd"))
        risk_ok = None
        if s0 and risk_budget and inv0 is not None and px0:
            risk_ok = s0 * max(0.0, (px0 - inv0) / px0) <= risk_budget * 1.001
        liq_ok = None
        if s0 and exit_cap is not None:
            liq_ok = s0 <= exit_cap
        if risk_ok is None and liq_ok is None:
            sizing = mark(None, 0, "", "", "sizing constraints (risk budget / exit capacity) not recorded at entry")
        else:
            checks = [c for c in (risk_ok, liq_ok) if c is not None]
            ok = all(checks)
            parts = []
            if risk_ok is not None:
                parts.append("risk " + ("within" if risk_ok else "EXCEEDS") + " budget")
            if liq_ok is not None:
                parts.append("size " + ("within" if liq_ok else "EXCEEDS") + " exit capacity")
            sizing = mark(ok, 3, "GOOD: " + ", ".join(parts), "BAD: " + ", ".join(parts), "")
            if len(checks) == 1:
                unknowns.append("only one of the two sizing constraints was recorded at entry")
            if not ok:
                lessons.append("Size to the smaller of the risk budget and the exit capacity, never to conviction")

    # exit plan pre-defined
    plan = info0.get("exit_plan") if e0 else None
    if e0 is None:
        profit_taking = "UNKNOWN"
    else:
        has_plan = bool(plan) if plan is not None else None
        if has_plan is None:
            profit_taking = mark(None, 0, "", "", "exit plan presence not recorded at entry")
        else:
            followed = None
            if has_plan and trims:
                followed = True
            elif has_plan and exits and not trims and not exit_decisions:
                followed = False
            msg_good = "GOOD: exit plan pre-defined" + (" and partial profits taken" if trims else "")
            msg_bad = "BAD: no pre-defined exit plan" if not has_plan else "BAD: exit plan defined but exits were not logged as decisions"
            profit_taking = mark(has_plan and followed is not False, 2, msg_good, msg_bad, "")
            if not has_plan:
                lessons.append("Decide where and how to take profit before entering, while unemotional")

    # adds: on thesis improvement vs averaging down into failure
    if adds:
        bad_adds = 0
        for a in adds:
            ia = _d(a.get("info_available"))
            state = str(ia.get("thesis_state") or "").upper()
            px = _num(ia.get("price"))
            below_entry = px is not None and entry is not None and px < entry
            if state in ("DETERIORATING", "INVALIDATED") or (below_entry and state not in ("IMPROVING",)):
                bad_adds += 1
        risk_mgmt = mark(bad_adds == 0, 3,
                         f"GOOD: {len(adds)} add(s) made on thesis improvement",
                         f"BAD: {bad_adds} of {len(adds)} add(s) averaged down into a deteriorating thesis", "")
        if bad_adds:
            lessons.append("Adds are earned by thesis improvement, not by a lower price")
    else:
        # honoring invalidation
        breached = None
        if inv is not None and price_path:
            lows = [_num(r[1]) for r in price_path if isinstance(r, (list, tuple)) and len(r) >= 2]
            lows = [l for l in lows if l is not None]
            breached = bool(lows) and min(lows) < inv
        if breached is None:
            risk_mgmt = mark(None, 0, "", "", "invalidation or price path missing: cannot judge whether the stop was honored")
        elif not breached:
            risk_mgmt = mark(True, 2, "GOOD: invalidation never breached, no adds", "", "")
        else:
            # breached: was there an exit decision at or after breach, before further loss?
            exit_after = bool(exit_decisions) or bool(exits)
            worst_exit = min((_num(e.get("price")) or inv for e in exits), default=None)
            honored = exit_after and (worst_exit is None or worst_exit >= inv * 0.85)
            risk_mgmt = mark(honored, 3, "GOOD: invalidation breached and position exited near the level",
                             "BAD: invalidation breached but exit was late or absent (held through the stop)", "")
            if not honored:
                lessons.append("An invalidation that is not acted on is a hope, not a plan")

    # execution: slippage relative to what was expected
    exp_slip = _num(info0.get("expected_slippage_pct")) if e0 else None
    if avg_slip is None:
        execution = "UNKNOWN"
        unknowns.append("slippage not recorded: execution quality unknown")
    else:
        if exp_slip is not None:
            ok = avg_slip <= exp_slip * 1.5 + 0.5
            execution = mark(ok, 1, f"GOOD: slippage {avg_slip:.2f}% within expectation {exp_slip:.2f}%",
                             f"BAD: slippage {avg_slip:.2f}% vs expected {exp_slip:.2f}%", "")
        else:
            ok = avg_slip <= 3.0
            execution = mark(ok, 1, f"ACCEPTABLE: slippage {avg_slip:.2f}%", f"POOR: slippage {avg_slip:.2f}% > 3%", "")
            unknowns.append("expected slippage not recorded at entry; 3% used as threshold")
        if not ok:
            lessons.append("Check SELL-side depth before entry; the exit decides the realized return")

    # exit quality: captured share of MFE and reason recorded
    if not exits:
        exit_quality = "OPEN"
    else:
        reasons = [str(e.get("reason") or "").strip() for e in exits]
        # an imported/manual placeholder is not a recorded exit reason
        has_reasons = all(r and not any(w in r.lower() for w in ("imported", "manual sell", "unknown")) for r in reasons)
        capture = None
        if mfe and realized_pct is not None and mfe > 0 and realized_pct > 0:
            capture = realized_pct / mfe
        elif mfe and realized_pct is not None and mfe > 20 and realized_pct <= 0:
            missed.append(f"MFE reached {mfe:+.1f}% but the trade closed at {realized_pct:+.1f}%: an open gain of that size was given back entirely")
        parts = []
        if capture is not None:
            parts.append(f"captured {capture*100:.0f}% of MFE")
            if capture < 0.25 and mfe > 20:
                missed.append(f"MFE reached {mfe:+.1f}% but realized {realized_pct:+.1f}%: profit-taking rule did not capture the move")
        parts.append("reasons recorded" if has_reasons else "exit reasons missing")
        ok = has_reasons and (capture is None or capture >= 0.25 or (mfe or 0) <= 20)
        exit_quality = mark(ok, 2, "GOOD: " + ", ".join(parts), "WEAK: " + ", ".join(parts), "")

    # missed evidence / unexpected from the log
    for e in log:
        ia = _d(e.get("info_available"))
        if _is(e, "ENTER", "ADD") and str(ia.get("large_holder_net_direction") or "").upper() in ("DISTRIBUTING", "EXITING"):
            missed.append(f"{_act(e)} while large holders were {ia.get('large_holder_net_direction')}")
        if _is(e, "ENTER", "ADD") and str(ia.get("lifecycle") or "").upper() in ("DISTRIBUTION", "MANIA"):
            missed.append(f"{_act(e)} during lifecycle {ia.get('lifecycle')}")
        if ia.get("unexpected"):
            unexpected.append(str(ia.get("unexpected")))
    if mae is not None and risk_usd and size and entry and inv is not None:
        inv_dist_pct = (inv / entry - 1) * 100
        if mae < inv_dist_pct - 10:
            unexpected.append(f"Price gapped {mae - inv_dist_pct:.1f}pp beyond the invalidation ({inv_dist_pct:.1f}%)")

    # ---- grades ----
    if total_points == 0 or not log:
        decision_grade = "UNKNOWN"
        if not log:
            unknowns.append("decision quality is judged only from the decision log; none was recorded for this trade")
    else:
        frac = good_points / total_points
        decision_grade = "GOOD" if frac >= 0.7 else "BAD"
        inferences.append(f"Decision score {good_points}/{total_points} weighted checks -> {decision_grade}")
    if realized_r is not None:
        outcome_grade = "GOOD" if realized_r >= 0.5 else "BAD" if realized_r <= -0.5 else "FLAT"
    elif realized_pct is not None:
        outcome_grade = "GOOD" if realized_pct >= 10 else "BAD" if realized_pct <= -10 else "FLAT"
        unknowns.append("outcome graded on % return because R is unavailable")
    else:
        outcome_grade = "UNKNOWN"
    if decision_grade == "UNKNOWN" or outcome_grade == "UNKNOWN":
        quadrant = "UNCLASSIFIED"
    else:
        og = "GOOD" if outcome_grade == "GOOD" else "BAD" if outcome_grade == "BAD" else "FLAT"
        quadrant = f"{decision_grade}_DECISION_{og}_OUTCOME"
    if quadrant == "BAD_DECISION_GOOD_OUTCOME":
        lessons.append("Profitable but undisciplined: this outcome does not validate the process")
    if quadrant == "GOOD_DECISION_BAD_OUTCOME":
        lessons.append("Process was sound; losses within plan are the cost of doing business, do not change rules on one sample")

    out = {
        "quadrant": quadrant,
        "decision_grade": decision_grade,
        "outcome_grade": outcome_grade,
        "thesis_quality": thesis_quality,
        "entry_quality": entry_quality,
        "sizing": sizing,
        "execution": execution,
        "risk_mgmt": risk_mgmt,
        "profit_taking": profit_taking,
        "exit_quality": exit_quality,
        "process_errors": "; ".join(process_errors) if process_errors else None,
        "missed_evidence": "; ".join(dict.fromkeys(missed)) if missed else None,
        "unexpected": "; ".join(dict.fromkeys(unexpected)) if unexpected else None,
        "mae_pct": mae,
        "mfe_pct": mfe,
        "realized_pct": realized_pct,
        "displayed_pct": displayed_pct,
        "realized_r": realized_r,
        "realized_usd": round(realized_usd, 2) if exits else None,
        "holding_hours": holding_hours,
        "avg_slippage_pct": avg_slip,
        "n_exits": len(exits),
        "n_decisions": len(log),
        "lessons": list(dict.fromkeys(lessons)),
        "facts": facts,
        "inferences": inferences,
        "heuristics": heuristics,
        "unknowns": unknowns,
    }
    return out


def store_review(con: sqlite3.Connection, position_id: int, review_: dict) -> int:
    row = {"position_id": position_id, "reviewed_at": time.time()}
    for c in TRADE_REVIEW_COLUMNS:
        v = review_.get(c)
        if isinstance(v, (list, dict)):
            v = json.dumps(v)
        row[c] = v
    cols = list(row)
    cur = con.execute(
        f"INSERT INTO trade_reviews ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
        list(row.values()),
    )
    return int(cur.lastrowid)
