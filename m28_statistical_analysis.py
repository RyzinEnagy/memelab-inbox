"""m28: statistical analysis of the paper/live trade history.

Public interface:
    load_trades(con) -> list[dict]        one row per closed position with realized metrics
    stats(con) -> dict                    grouped statistics by setup_type, lifecycle_at_entry, regime, score bucket
    compare_signal(con, signal_fn_name, n_boot=2000, seed=0) -> dict
                                          two-group comparison with bootstrap CI on expectancy difference

Sample-size discipline: every grouping carries a "sample_flag" (INSUFFICIENT SAMPLE for n < 20,
LOW CONFIDENCE for n < 50, OK otherwise), and groups are not ranked when any group has n < 10.

Signal functions (name -> (label_a, label_b, fn(trade) -> True/False/None)) live in SIGNALS and can be
extended by callers: register_signal(name, label_true, label_false, fn).
"""
from __future__ import annotations

import sqlite3
from typing import Any, Callable

import numpy as np

SCORE_BUCKETS = [(0, 39, "0-39"), (40, 59, "40-59"), (60, 74, "60-74"), (75, 100, "75-100")]
MIN_N_RANK = 10
N_INSUFFICIENT = 20
N_LOW_CONF = 50


def _num(x: Any) -> float | None:
    try:
        if x is None or isinstance(x, bool):
            return None
        v = float(x)
        return None if v != v else v
    except (TypeError, ValueError):
        return None


def sample_flag(n: int) -> str:
    if n < N_INSUFFICIENT:
        return "INSUFFICIENT SAMPLE"
    if n < N_LOW_CONF:
        return "LOW CONFIDENCE"
    return "OK"


def score_bucket(score: float | None) -> str:
    if score is None:
        return "UNKNOWN"
    for lo, hi, label in SCORE_BUCKETS:
        if lo <= score <= hi:
            return label
    return "UNKNOWN"


# ----------------------------------------------------------------------------
# loading
# ----------------------------------------------------------------------------
def load_trades(con: sqlite3.Connection) -> list[dict]:
    """One row per position that has at least one exit. Returns [] on any schema problem."""
    try:
        con.row_factory = sqlite3.Row
        positions = con.execute("SELECT * FROM positions").fetchall()
    except sqlite3.Error:
        return []
    out: list[dict] = []
    for p in positions:
        p = dict(p)
        try:
            exits = [dict(r) for r in con.execute("SELECT * FROM exits WHERE position_id=? ORDER BY exited_at", (p["id"],))]
            rv = con.execute("SELECT * FROM trade_reviews WHERE position_id=? ORDER BY reviewed_at DESC LIMIT 1", (p["id"],)).fetchone()
        except sqlite3.Error:
            exits, rv = [], None
        if not exits:
            continue
        rv = dict(rv) if rv else {}
        entry, size, inv = _num(p.get("entry_price")), _num(p.get("size_usd")), _num(p.get("invalidation_price"))
        tokens = _num(p.get("tokens")) or (size / entry if size and entry else None)
        realized = sum((_num(e.get("usd_realized")) or 0.0) for e in exits)
        displayed = sum((_num(e.get("displayed_value_usd")) or (_num(e.get("usd_realized")) or 0.0)) for e in exits)
        sold = sum((_num(e.get("tokens")) or 0.0) for e in exits)
        cost = sold * entry if entry and sold else size
        if not cost:
            continue
        pnl = realized - cost
        ret_pct = pnl / cost * 100
        disp_pct = displayed / cost * 100 - 100
        risk = _num(p.get("max_risk_usd"))
        if risk is None and entry and inv is not None and size:
            risk = size * max(0.0, (entry - inv) / entry)
        r = pnl / risk if risk else None
        slips = [_num(e.get("slippage_pct")) for e in exits]
        slips = [s for s in slips if s is not None]
        opened, closed = _num(p.get("opened_at")), _num(p.get("closed_at"))
        if closed is None:
            closed = max((_num(e.get("exited_at")) or 0.0) for e in exits) or None
        hold_h = (closed - opened) / 3600 if opened is not None and closed is not None else None
        out.append({
            "position_id": p["id"], "mint": p.get("mint"), "paper": p.get("paper"),
            "setup_type": p.get("setup_type") or "UNKNOWN",
            "lifecycle_at_entry": p.get("lifecycle_at_entry") or "UNKNOWN",
            "regime": p.get("regime") or "UNKNOWN",
            "score_at_entry": _num(p.get("score_at_entry")),
            "score_bucket": score_bucket(_num(p.get("score_at_entry"))),
            "ret_pct": ret_pct, "displayed_pct": disp_pct, "r": r, "pnl_usd": pnl, "cost_usd": cost,
            "win": pnl > 0,
            "mae_pct": _num(rv.get("mae_pct")), "mfe_pct": _num(rv.get("mfe_pct")),
            "review_realized_pct": _num(rv.get("realized_pct")), "review_displayed_pct": _num(rv.get("displayed_pct")),
            "quadrant": rv.get("quadrant"),
            "avg_slippage_pct": sum(slips) / len(slips) if slips else None,
            "holding_hours": hold_h, "n_exits": len(exits),
        })
    return out


# ----------------------------------------------------------------------------
# group statistics
# ----------------------------------------------------------------------------
def _mean(vals: list[float | None]) -> float | None:
    v = [x for x in vals if x is not None]
    return float(np.mean(v)) if v else None


def group_stats(trades: list[dict]) -> dict:
    n = len(trades)
    wins = [t for t in trades if t["win"]]
    losses = [t for t in trades if not t["win"]]
    win_rate = len(wins) / n if n else None
    avg_win_pct = _mean([t["ret_pct"] for t in wins])
    avg_loss_pct = _mean([t["ret_pct"] for t in losses])
    rs = [t["r"] for t in trades if t["r"] is not None]
    avg_win_r = _mean([t["r"] for t in wins if t["r"] is not None])
    avg_loss_r = _mean([t["r"] for t in losses if t["r"] is not None])
    exp_pct = _mean([t["ret_pct"] for t in trades])
    exp_r = float(np.mean(rs)) if rs else None
    real = _mean([t["ret_pct"] for t in trades])
    disp = _mean([t["displayed_pct"] for t in trades])
    return {
        "n": n,
        "sample_flag": sample_flag(n),
        "win_rate": round(win_rate, 4) if win_rate is not None else None,
        "avg_win_pct": _r(avg_win_pct), "avg_loss_pct": _r(avg_loss_pct),
        "avg_win_r": _r(avg_win_r), "avg_loss_r": _r(avg_loss_r),
        "expectancy_pct": _r(exp_pct),
        "expectancy_r": _r(exp_r),
        "n_with_r": len(rs),
        "avg_mae_pct": _r(_mean([t["mae_pct"] for t in trades])),
        "avg_mfe_pct": _r(_mean([t["mfe_pct"] for t in trades])),
        "avg_realized_pct": _r(real),
        "avg_displayed_pct": _r(disp),
        "realized_vs_displayed_pp": _r(real - disp) if real is not None and disp is not None else None,
        "avg_slippage_pct": _r(_mean([t["avg_slippage_pct"] for t in trades])),
        "avg_holding_hours": _r(_mean([t["holding_hours"] for t in trades])),
    }


def _r(x: float | None, nd: int = 3) -> float | None:
    return None if x is None else round(float(x), nd)


def _grouped(trades: list[dict], key: str) -> dict:
    groups: dict[str, list[dict]] = {}
    for t in trades:
        groups.setdefault(str(t.get(key) or "UNKNOWN"), []).append(t)
    out = {g: group_stats(ts) for g, ts in sorted(groups.items())}
    small = [g for g, s in out.items() if s["n"] < MIN_N_RANK]
    if not out:
        ranking: dict[str, Any] = {"ranked": False, "reason": "no groups"}
    elif small:
        ranking = {"ranked": False,
                   "reason": f"refusing to rank: group(s) with n < {MIN_N_RANK}: {', '.join(small)}"}
    else:
        order = sorted(out.items(), key=lambda kv: (kv[1]["expectancy_r"] if kv[1]["expectancy_r"] is not None else kv[1]["expectancy_pct"] or -1e9), reverse=True)
        ranking = {"ranked": True, "by": "expectancy_r (fallback expectancy_pct)", "order": [g for g, _ in order],
                   "warning": "all groups below n=50: ranking is LOW CONFIDENCE" if any(s["n"] < N_LOW_CONF for s in out.values()) else None}
    return {"groups": out, "ranking": ranking}


def stats(con: sqlite3.Connection) -> dict:
    trades = load_trades(con)
    facts: list[str] = []
    inferences: list[str] = []
    heuristics: list[str] = [
        f"n < {N_INSUFFICIENT}: INSUFFICIENT SAMPLE; n < {N_LOW_CONF}: LOW CONFIDENCE",
        f"Groups are not ranked when any group has n < {MIN_N_RANK}",
        "Expectancy in R = mean(pnl / planned risk); trades without planned risk are excluded from R metrics",
    ]
    unknowns: list[str] = []
    if not trades:
        unknowns.append("no closed positions with exits in the database")
    overall = group_stats(trades)
    facts.append(f"{overall['n']} closed trades; sample flag {overall['sample_flag']}")
    if overall["n"] and overall["n_with_r"] < overall["n"]:
        unknowns.append(f"{overall['n'] - overall['n_with_r']} trade(s) lack planned risk; excluded from R-based metrics")
    if overall["expectancy_r"] is not None:
        inferences.append(f"Overall expectancy {overall['expectancy_r']:+.2f}R ({overall['expectancy_pct']:+.1f}%), "
                          f"win rate {overall['win_rate']:.0%}; {overall['sample_flag']}")
    if overall["realized_vs_displayed_pp"] is not None and overall["realized_vs_displayed_pp"] < -1:
        inferences.append(f"Realized returns trail displayed by {abs(overall['realized_vs_displayed_pp']):.1f}pp on average: execution costs are material")
    by = {
        "setup_type": _grouped(trades, "setup_type"),
        "lifecycle_at_entry": _grouped(trades, "lifecycle_at_entry"),
        "regime": _grouped(trades, "regime"),
        "score_bucket": _grouped(trades, "score_bucket"),
    }
    for k, g in by.items():
        if not g["ranking"]["ranked"]:
            inferences.append(f"{k}: {g['ranking']['reason']}")
    quadrants: dict[str, int] = {}
    for t in trades:
        if t.get("quadrant"):
            quadrants[t["quadrant"]] = quadrants.get(t["quadrant"], 0) + 1
    if overall["n"] < N_INSUFFICIENT:
        inferences.append("Sample is too small for any grouping to be actionable; treat every figure as descriptive only")
    return {
        "n_trades": overall["n"],
        "sample_flag": overall["sample_flag"],
        "overall": overall,
        "by": by,
        "quadrants": quadrants,
        "facts": facts,
        "inferences": inferences,
        "heuristics": heuristics,
        "unknowns": unknowns,
    }


# ----------------------------------------------------------------------------
# signal comparison
# ----------------------------------------------------------------------------
SignalFn = Callable[[dict], bool | None]
SIGNALS: dict[str, tuple[str, str, SignalFn]] = {}


def register_signal(name: str, label_true: str, label_false: str, fn: SignalFn) -> None:
    SIGNALS[name] = (label_true, label_false, fn)


def _sig_breakout_retest_vs_anticipation(t: dict) -> bool | None:
    s = str(t.get("setup_type") or "").upper()
    if "RETEST" in s:
        return True
    if "ANTICIP" in s:
        return False
    return None


def _sig_high_score(t: dict) -> bool | None:
    s = t.get("score_at_entry")
    return None if s is None else s >= 75


def _sig_early_lifecycle(t: dict) -> bool | None:
    lc = str(t.get("lifecycle_at_entry") or "").upper()
    if lc in ("DISCOVERY", "EARLY_EXPANSION"):
        return True
    if lc in ("UNKNOWN", ""):
        return None
    return False


def _sig_good_decision(t: dict) -> bool | None:
    q = str(t.get("quadrant") or "")
    if q.startswith("GOOD_DECISION"):
        return True
    if q.startswith("BAD_DECISION"):
        return False
    return None


register_signal("breakout_retest_vs_anticipation", "BREAKOUT_RETEST", "ANTICIPATION", _sig_breakout_retest_vs_anticipation)
register_signal("high_score_vs_rest", "score>=75", "score<75", _sig_high_score)
register_signal("early_lifecycle_vs_late", "DISCOVERY/EARLY_EXPANSION", "later stages", _sig_early_lifecycle)
register_signal("good_decision_vs_bad", "GOOD_DECISION", "BAD_DECISION", _sig_good_decision)


def bootstrap_diff_ci(a: list[float], b: list[float], n_boot: int = 2000, seed: int = 0, alpha: float = 0.05) -> dict:
    a_arr, b_arr = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a_arr.size == 0 or b_arr.size == 0:
        return {"diff": None, "ci_low": None, "ci_high": None, "n_boot": 0}
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        diffs[i] = rng.choice(a_arr, a_arr.size, replace=True).mean() - rng.choice(b_arr, b_arr.size, replace=True).mean()
    lo, hi = np.percentile(diffs, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {"diff": float(a_arr.mean() - b_arr.mean()), "ci_low": float(lo), "ci_high": float(hi), "n_boot": n_boot,
            "ci_excludes_zero": bool(lo > 0 or hi < 0)}


def compare_signal(con: sqlite3.Connection, signal_fn_name: str, n_boot: int = 2000, seed: int = 0,
                   metric: str = "r") -> dict:
    trades = load_trades(con)
    unknowns: list[str] = []
    if signal_fn_name not in SIGNALS:
        return {"signal": signal_fn_name, "error": f"unknown signal; available: {sorted(SIGNALS)}",
                "facts": [], "inferences": [], "heuristics": [], "unknowns": [f"signal {signal_fn_name!r} not registered"]}
    label_a, label_b, fn = SIGNALS[signal_fn_name]
    ga, gb, skipped = [], [], 0
    for t in trades:
        try:
            v = fn(t)
        except Exception:
            v = None
        if v is True:
            ga.append(t)
        elif v is False:
            gb.append(t)
        else:
            skipped += 1
    if skipped:
        unknowns.append(f"{skipped} trade(s) could not be assigned to either group")

    def metric_vals(ts: list[dict]) -> list[float]:
        key = "r" if metric == "r" else "ret_pct"
        return [t[key] for t in ts if t.get(key) is not None]

    va, vb = metric_vals(ga), metric_vals(gb)
    if metric == "r" and (len(va) < len(ga) or len(vb) < len(gb)):
        unknowns.append("some trades lack planned risk and are excluded from the R comparison")
    ci = bootstrap_diff_ci(va, vb, n_boot=n_boot, seed=seed)
    n_min = min(len(ga), len(gb))
    warning = sample_flag(n_min)
    heuristics = ["Plain percentile bootstrap on the difference of group means (expectancy)",
                  f"Sample warning uses the smaller group: n < {N_INSUFFICIENT} INSUFFICIENT, n < {N_LOW_CONF} LOW CONFIDENCE"]
    inferences: list[str] = []
    if ci["diff"] is None:
        inferences.append("One group is empty: no comparison possible")
    else:
        unit = "R" if metric == "r" else "pp"
        verdict = ("CI excludes zero" if ci.get("ci_excludes_zero") else "CI includes zero: no evidence of a difference")
        inferences.append(f"{label_a} minus {label_b} expectancy = {ci['diff']:+.2f}{unit} "
                          f"(95% CI {ci['ci_low']:+.2f} to {ci['ci_high']:+.2f}); {verdict}; sample {warning}")
        if warning != "OK":
            inferences.append("Sample size warning: do not act on this comparison yet")
    return {
        "signal": signal_fn_name,
        "metric": metric,
        "group_a": {"label": label_a, **group_stats(ga)},
        "group_b": {"label": label_b, **group_stats(gb)},
        "expectancy_diff": ci,
        "sample_warning": warning,
        "facts": [f"{label_a}: n={len(ga)}; {label_b}: n={len(gb)}; unassigned {skipped}"],
        "inferences": inferences,
        "heuristics": heuristics,
        "unknowns": unknowns,
    }
