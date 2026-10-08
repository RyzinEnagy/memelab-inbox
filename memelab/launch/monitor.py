"""LAUNCH_MONITOR + POST_LAUNCH_THESIS_CONVERTER.

For tracked launches that are trading: window snapshots at 1m / 5m / 15m / 1h / 6h / 24h after the first trade (reconstructed from the
pool's minute candles and trades when they cover the start, otherwise taken from the nearest observation and labeled so),
price-discovery classification, expected-vs-actual comparison, and the hand-over into the normal framework.
Forecasts are replaced by observations as soon as trading begins.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .. import db

WINDOWS = [("1m", 1), ("5m", 5), ("15m", 15), ("1h", 60), ("6h", 360), ("24h", 1440)]
HANDOVER_HOURS = 72
MIN_HOURS_FOR_FULL = 24


def _ts(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def candles(bodies: dict, pool: str | None, tf: str = "minute1") -> list[list[float]]:
    v = bodies.get(f"gt_ohlcv:{pool}:{tf}") if pool else None
    rows = (v or {}).get("ohlcv") or []
    return sorted([r for r in rows if len(r) >= 6], key=lambda r: r[0])   # [ts, o, h, l, c, vol_usd]


def windows(c: dict, bodies: dict, hold: dict, snip: dict, t: float) -> dict[str, dict]:
    pool = c.get("pool") or c.get("curve_pool")
    cs = candles(bodies, pool)
    start = c.get("first_trade_at") or (cs[0][0] if cs else None) or c.get("created_at")
    if not start:
        return {}
    trades = (bodies.get(f"gt_trades:{pool}:all") or {}).get("trades") or [] if pool else []
    tt = [(_ts(x[0]), x) for x in trades if _ts(x[0])]
    covered = bool(cs) and cs[0][0] - start <= 120
    out = {}
    age_min = (t - start) / 60
    for name, m in WINDOWS:
        if age_min < m:
            break
        end = start + m * 60
        seg = [r for r in cs if r[0] < end]
        met: dict[str, Any] = {}
        basis = "candles-reconstructed" if covered and seg else "snapshot"
        if seg:
            met.update({"open": seg[0][1], "high": max(r[2] for r in seg), "low": min(r[3] for r in seg), "close": seg[-1][4], "volume_usd": sum(r[5] for r in seg)})
        tw = [x for ts, x in tt if ts < end]
        if tw and (min(ts for ts, _ in tt) - start) <= 120:
            met["unique_buyers"] = len({x[1] for x in tw if x[2] == "buy"})
            met["unique_sellers"] = len({x[1] for x in tw if x[2] == "sell"})
        if abs(age_min - m) <= max(10, 0.25 * m):   # the observation taken now belongs to the window it is closest to
            o = c.get("obs") or {}
            met.update({"mcap_usd": o.get("mcap_usd"), "fdv_usd": o.get("fdv_usd"), "liquidity_usd": o.get("liquidity_usd"), "holders": o.get("holders"),
                        "top10_ex_pool_pct": hold.get("top10_ex_pool_pct"), "dev_pct": hold.get("dev_pct"), "sniper_still_holding_pct": snip.get("sniper_still_holding_pct")})
        if met:
            out[name] = {"basis": basis, "metrics": met}
    return out


def price_discovery(c: dict, bodies: dict, t: float) -> dict[str, Any]:
    pool = c.get("pool") or c.get("curve_pool")
    cs = candles(bodies, pool)
    start = c.get("first_trade_at") or c.get("created_at")
    if cs and start and cs[0][0] - start > 1800:
        c5 = candles(bodies, pool, "minute5")
        if c5 and c5[0][0] < cs[0][0]:
            cs = c5
    if len(cs) < 10:
        return {"pattern": "UNKNOWN", "why": "fewer than 10 candles for the token's pool"}
    covered = bool(start) and cs[0][0] - start <= 1800
    o = cs[0][1]
    hi_i = max(range(len(cs)), key=lambda i: cs[i][2]); hi = cs[hi_i][2]
    last = cs[-1][4]
    lo_after = min(r[3] for r in cs[hi_i:])
    mins_to_high = (cs[hi_i][0] - cs[0][0]) / 60
    span = (cs[-1][0] - cs[0][0]) / 60 or 1
    tail = cs[int(len(cs) * 0.6):]
    tail_range = max(r[2] for r in tail) / max(min(r[3] for r in tail), 1e-30)
    last_hour = [r for r in cs if r[0] >= cs[-1][0] - 3600]
    lh_range = max(r[2] for r in last_hour) / max(min(r[3] for r in last_hour), 1e-30)
    dd = (lo_after / hi - 1) * 100
    d = {"open": o, "high": hi, "low_after_high": lo_after, "last": last, "minutes_to_high": round(mins_to_high, 1), "drawdown_from_high_pct": round(dd, 1),
         "last_vs_open": round(last / o, 2) if o else None, "span_minutes": round(span)}
    if o and last < 0.3 * o and covered:
        p = "FAILED LAUNCH"
    elif o and ((hi >= 3 * o and last <= 1.2 * o) or (not covered and dd <= -85)):
        p = "PUMP AND DUMP"
    elif o and hi >= 3 * o and mins_to_high <= 15 and last >= 0.6 * hi:
        p = "PARABOLIC OPEN"
    elif dd <= -50 and last >= lo_after + 0.6 * (hi - lo_after):
        p = "SELL-OFF AND RECOVERY"
    elif last >= 0.8 * hi and mins_to_high >= 0.5 * span and dd > -35:
        p = "ORDERLY TREND"
    elif lh_range < 1.3 and len(last_hour) >= 20:
        p = "BASE"
    elif tail_range < 1.6:
        p = "RANGE"
    else:
        p = "UNRESOLVED"
    d["pattern"] = p
    d["covers_open"] = covered
    d["why"] = "heuristic from candles of the token's own pool (rules in launch/monitor.py)" + ("" if covered else f"; PARTIAL: candles start {(cs[0][0] - start) / 3600:.1f}h after launch, the open is not observed" if start else "; launch time unknown")
    d["why_short"] = f"{dd:.0f}% from the high" + ("" if covered else " (partial history)")
    return d


def convert(con, c: dict, tk: dict, hold: dict, snip: dict, clus: dict) -> dict[str, Any]:
    """Expected (pre-launch record) vs actual (observed now)."""
    lid = c["launch_id"]
    pre = con.execute("SELECT * FROM upcoming_launches WHERE launch_id=?", (lid,)).fetchone()
    pre_obs = con.execute("SELECT * FROM launch_observations WHERE launch_id=? AND state IN ('A','B','C','D') ORDER BY observed_at DESC LIMIT 1", (lid,)).fetchone()
    o = c.get("obs") or {}
    lines, worse, better = [], 0, 0

    def cmp(label, exp, act, good_if_higher, tol=0.25):
        nonlocal worse, better
        if exp is None or act is None:
            lines.append(f"{label}: expected {('%s' % _fmt(exp)) if exp is not None else 'UNKNOWN'}, actual {('%s' % _fmt(act)) if act is not None else 'UNKNOWN'}")
            return
        rel = (act - exp) / abs(exp) if exp else 0
        verdict = "as expected"
        if (rel > tol and good_if_higher) or (rel < -tol and not good_if_higher):
            verdict = "better"; better += 1
        elif (rel < -tol and good_if_higher) or (rel > tol and not good_if_higher):
            verdict = "worse"; worse += 1
        lines.append(f"{label}: expected {_fmt(exp)}, actual {_fmt(act)} ({verdict})")

    cmp("initial liquidity", pre["expected_liquidity_usd"] if pre else None, o.get("liquidity_usd"), True)
    cmp("top-10 concentration %", pre_obs["top10_pct"] if pre_obs else None, hold.get("top10_ex_pool_pct"), False)
    exp_ins = tk.get("initial_insider_pct") if tk.get("insider_basis") in ("MECHANISM", "CLAIMED") else (pre["team_alloc_pct"] if pre else None)
    obs_ins = max([x for x in (hold.get("dev_pct"), hold.get("insider_network_pct"), sum(cl["pct"] for cl in clus.get("clusters") or []) or None) if x is not None], default=None)
    cmp("insider / related-cluster %", exp_ins, obs_ins, False)
    if snip.get("sniper_still_holding_pct") is not None:
        lines.append(f"sniper inventory still held: {snip['sniper_still_holding_pct']:.1f}% ({snip.get('snipers_selling', 0)} sniper wallet(s) selling)")
        if snip["sniper_still_holding_pct"] > 15:
            worse += 1
    if worse >= 2 and worse > better:
        interp = "The pre-launch thesis materially deteriorated."
    elif better >= 2 and better > worse:
        interp = "The live market structure is stronger than the pre-launch thesis expected."
    elif worse or better:
        interp = "Mixed: some expectations missed, some beaten."
    else:
        interp = "Not enough expected-vs-actual pairs to judge; most pre-launch expectations were UNKNOWN."
    return {"lines": lines, "worse": worse, "better": better, "interpretation": interp}


def _fmt(x):
    return f"${x:,.0f}" if isinstance(x, (int, float)) and abs(x) >= 1000 else (f"{x:.1f}" if isinstance(x, float) else str(x))


def handover(con, c: dict, pd: dict, conv: dict, status: str, t: float) -> dict | None:
    """Move a trading launch to NORMAL_WATCHLIST (full framework) or REJECTED; returns the transition or None."""
    row = con.execute("SELECT phase FROM upcoming_launches WHERE launch_id=?", (c["launch_id"],)).fetchone()
    if not row or row["phase"] in ("NORMAL_WATCHLIST", "REJECTED") or c["state"] != "E":
        return None
    start = c.get("first_trade_at") or c.get("created_at") or t
    age_h = (t - start) / 3600
    to, reason = None, None
    if pd.get("pattern") in ("FAILED LAUNCH",) or (pd.get("pattern") == "PUMP AND DUMP" and age_h >= 6):
        to, reason = "REJECTED", f"price discovery: {pd['pattern']}"
    elif status in ("AVOID", "SEVERE RISK"):
        to, reason = "REJECTED", f"status {status}"
    elif age_h >= HANDOVER_HOURS or (age_h >= MIN_HOURS_FOR_FULL and pd.get("span_minutes", 0) >= 24 * 60 * 0.9):
        to, reason = "NORMAL_WATCHLIST", f"{age_h:.0f}h of market history: the pre-launch framework ends; the full Memecoin Investing Lab analysis takes over"
    if not to:
        return None
    tr = {"launch_id": c["launch_id"], "at": t, "from_phase": row["phase"], "to_phase": to, "reason": reason, "interpretation": conv.get("interpretation"), "actual_json": json.dumps(conv.get("lines"))}
    db.insert(con, "launch_transitions", tr)
    con.execute("UPDATE upcoming_launches SET phase=?, transitioned_at=? WHERE launch_id=?", (to, t, c["launch_id"]))
    if to == "NORMAL_WATCHLIST" and c.get("contract"):
        db.upsert_token(con, c["contract"], chain=c.get("chain") or "solana", name=c.get("project"), symbol=c.get("symbol"), launchpad=c.get("launchpad"), creator=c.get("creator"))
        if not con.execute("SELECT 1 FROM watchlist WHERE mint=?", (c["contract"],)).fetchone():
            db.insert(con, "watchlist", {"mint": c["contract"], "added_at": t, "status": "RESEARCH REQUIRED", "last_status_change": t,
                      "notes": f"from launch monitor ({c.get('launchpad')}); pre-launch status {status}; {conv.get('interpretation')}"})
    db.insert(con, "launch_alerts", {"launch_id": c["launch_id"], "alerted_at": t, "kind": "PHASE_" + to, "text": f"{c.get('symbol')}: {reason}"})
    return tr


def persist_windows(con, lid: str, wins: dict, t: float, start: float | None) -> None:
    for name, w in wins.items():
        m = dict(WINDOWS)[name]
        row = con.execute("SELECT id, basis, metrics_json FROM launch_monitor WHERE launch_id=? AND window=?", (lid, name)).fetchone()
        if row and row["basis"] == "candles-reconstructed" and w["basis"] != "candles-reconstructed":
            merged = {**json.loads(row["metrics_json"]), **{k: v for k, v in w["metrics"].items() if v is not None}}
            con.execute("UPDATE launch_monitor SET metrics_json=? WHERE id=?", (json.dumps(merged), row["id"]))
            continue
        if row:
            merged = {**json.loads(row["metrics_json"]), **{k: v for k, v in w["metrics"].items() if v is not None}}
            con.execute("UPDATE launch_monitor SET metrics_json=?, basis=?, observed_at=? WHERE id=?", (json.dumps(merged), w["basis"], t, row["id"]))
        else:
            db.insert(con, "launch_monitor", {"launch_id": lid, "window": name, "observed_at": t, "age_minutes": m, "basis": w["basis"], "metrics_json": json.dumps(w["metrics"])})
