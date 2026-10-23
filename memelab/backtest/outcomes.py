"""Post-discovery outcomes, calibration and drift checks (Phase 15). Shadow evaluation only: nothing here trades.

Opportunities are frozen decision states the lab recorded at the time (the append-only discovery universe, one per
{mint, lab status} first appearance, and every stored FAST assessment). Their outcomes are measured afterwards at
prespecified windows (protocol outcomes-v1: 1 h, 6 h, 24 h, 72 h) from bars that were available at the outcome's own
`observed_asof`. Rules:
- the decision state is read from the record as it was stored; an outcome never writes back into it, into stored
  assessments or into stored runs (all append-only);
- an outcome row is identified by (opportunity, horizon, content hash): recomputing with the same available bars adds
  nothing, a provider revision adds a new row that supersedes the old one, and the old row stays;
- a token that stopped trading, never had stored bars or has no pool basis is recorded as CENSORED or NOT_OBSERVABLE
  with its reason, never dropped;
- calibration reports sample counts and censoring per segment and says when a segment is too small; segments are
  correlations, not causes;
- observed deviations open a versioned re-evaluation proposal; no strategy parameter is ever retuned in place.
"""
from __future__ import annotations

import bisect
import json
import math
import sqlite3
import statistics
import time
from collections import defaultdict
from datetime import datetime, timezone

from . import store
from .sources import gecko

PROTOCOL = "outcomes-v1"
HORIZONS_S = (3600, 6 * 3600, 24 * 3600, 72 * 3600)
SIZES_USD = (250.0, 1000.0, 5000.0)
TF = 3600
LAG_S = gecko.PROVIDER_LAG_S
MIN_SEGMENT = 30
BASIS_TRIES_H = (0, 6, 12, 24, 48)
TERMINAL = ("COMPLETE", "CENSORED", "NOT_OBSERVABLE")
SOL = "So11111111111111111111111111111111111111112"


def _day(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------- opportunities (frozen decision states)

def opportunities(con, universe_id: str = "lab_state_history", include_assessments: bool = True) -> list[dict]:
    rows = con.execute("SELECT * FROM bt_universe_members WHERE universe_id=? ORDER BY available_at, id", (universe_id,)).fetchall()
    seen, out = set(), []
    for r in rows:
        status = r["status_at_entry"] if r["basis"] == "THESIS" else "REJECTED_AT_SCREEN"
        k = (r["chain"], r["mint"], r["basis"], status)
        if k in seen:
            continue
        seen.add(k)
        snap = json.loads(r["snapshot_json"]) if r["snapshot_json"] else {}
        d = {"source": "LAB_" + r["basis"], "chain": r["chain"], "mint": r["mint"], "symbol": r["symbol"], "decision_time": r["available_at"],
             "status": status, "score": r["score_at_entry"], "stage": r["stage"], "liquidity": snap.get("liquidity"), "price": snap.get("price"),
             "fatal": json.loads(r["fatal_flags_json"] or "[]"), "record_id": r["id"], "record_hash": r["content_hash"]}
        d["opportunity_id"] = store.sha256([d["source"], d["chain"], d["mint"], d["decision_time"], d["status"]])
        out.append(d)
    if include_assessments:
        for a in con.execute("SELECT request_key, chain, mint, as_of, state, result_json FROM bt_assessments WHERE stage='FAST' ORDER BY as_of, id"):
            res = json.loads(a["result_json"])
            snap = res.get("snapshot") or {}
            d = {"source": "ASSESSMENT", "chain": a["chain"], "mint": a["mint"], "symbol": res.get("symbol"), "decision_time": a["as_of"],
                 "status": (res.get("lab") or {}).get("status"), "score": (res.get("lab") or {}).get("score"), "stage": a["state"],
                 "liquidity": snap.get("liquidity_usd"), "price": snap.get("price_usd"), "fatal": (res.get("lab") or {}).get("fatal_flags") or [],
                 "record_id": a["request_key"], "record_hash": a["request_key"], "assessment_state": a["state"]}
            d["opportunity_id"] = "asmt:" + a["request_key"]
            out.append(d)
    return out


# ---------------------------------------------------------------- one outcome

def _bars_basis(con, chain: str, mint: str, cutoff: float, lookback_s: float = 86400.0) -> dict | None:
    """Fallback when no pool record exists: the pool with the most volume in bars closed and available at cutoff."""
    r = con.execute("SELECT pool_address, SUM(COALESCE(volume_usd, 0)) v, COUNT(*) n FROM bt_market_bars WHERE chain=? AND mint=? AND timeframe_s=? "
                    "AND available_at<=? AND end>? GROUP BY pool_address ORDER BY v DESC, pool_address LIMIT 1", (chain, mint, TF, cutoff, cutoff - lookback_s)).fetchone()
    return {"pool_address": r["pool_address"], "pool_type": "UNKNOWN", "dex": None, "trailing_volume_usd": r["v"], "n_bars": r["n"], "from_bars_only": True} if r else None


def _basis(con, opp: dict) -> tuple[dict | None, float | None]:
    """One pool per token, chosen with information available at the decision (or the first try that has any):
    pool records first, bars alone when the corpus holds no pool record for the mint."""
    has_records = con.execute("SELECT 1 FROM bt_pool_versions WHERE chain=? AND mint=? LIMIT 1", (opp["chain"], opp["mint"])).fetchone() is not None
    for h in BASIS_TRIES_H:
        t = opp["decision_time"] + h * 3600
        b = gecko.pool_basis_at(con, opp["chain"], opp["mint"], t) if has_records else _bars_basis(con, opp["chain"], opp["mint"], t)
        if b:
            return b, h
    return None, None


def outcome_for(con, opp: dict, horizon_s: int, observed_asof: float) -> dict:
    """State and realized values for one window, from bars available at observed_asof only."""
    t, end = opp["decision_time"], opp["decision_time"] + horizon_s
    if observed_asof < end + LAG_S:
        return {"state": "PENDING", "missing_reason": "window not closed and published yet", "censored": 0, "realized": None}
    if not con.execute("SELECT 1 FROM bt_market_bars WHERE chain=? AND mint=? AND available_at<=? LIMIT 1", (opp["chain"], opp["mint"], observed_asof)).fetchone():
        return {"state": "NOT_OBSERVABLE", "missing_reason": "NO_BARS_STORED: no bars for this mint were available at this asof", "censored": 1, "realized": None}
    basis, delay_h = _basis(con, opp)
    if not basis:
        return {"state": "NOT_OBSERVABLE", "missing_reason": "NO_POOL_BASIS: no pool had bars within 48 h of the decision", "censored": 1, "realized": None}
    bars = [b for b in store.bars_asof(con, chain=opp["chain"], mint=opp["mint"], pool_address=basis["pool_address"], tf=TF, cutoff=observed_asof)
            if b["start"] >= t and b["start"] < end]
    flags = ([f"POOL_BASIS_DELAYED_{delay_h}H"] if delay_h else []) + (["POOL_BASIS_FROM_BARS_ONLY"] if basis.get("from_bars_only") else [])
    if not bars:
        last = con.execute("SELECT MAX(end) FROM bt_market_bars WHERE mint=? AND pool_address=? AND available_at<=?",
                           (opp["mint"], basis["pool_address"], observed_asof)).fetchone()[0]
        return {"state": "CENSORED", "missing_reason": "NO_BARS_IN_WINDOW: no trade bars after the decision (stopped trading or provider gap)",
                "censored": 1, "realized": {"pool": basis["pool_address"], "last_bar_end": last, "flags": flags}}
    e = bars[0]
    entry = e["o"]
    if e["start"] - t >= TF:
        flags.append("ENTRY_BAR_DELAYED")
    lo, hi = min(b["l"] for b in bars), max(b["h"] for b in bars)
    real = {"pool": basis["pool_address"], "entry_bar_start": e["start"], "entry_open": entry, "exit_close": bars[-1]["c"], "last_bar_end": bars[-1]["end"],
            "ret_close": bars[-1]["c"] / entry - 1, "max_drawdown": lo / entry - 1, "max_runup": hi / entry - 1, "down_50": lo / entry - 1 <= -0.5,
            "bars": len(bars), "revisions_used": sum(1 for b in bars if "REVISION" in (b["quality_flags"] or "")), "flags": flags}
    if bars[-1]["end"] < end - TF:
        real["flags"] = flags + ["PARTIAL_WINDOW"]
        return {"state": "CENSORED", "missing_reason": f"BARS_END_EARLY: last bar ends {(end - bars[-1]['end']) / 3600:.1f} h before the window; drawdown is a lower bound",
                "censored": 1, "realized": real}
    return {"state": "COMPLETE", "missing_reason": None, "censored": 0, "realized": real}


def _body_hash(state, realized, missing_reason, protocol=PROTOCOL) -> str:
    return store.sha256({"state": state, "realized": realized, "missing_reason": missing_reason, "protocol": protocol})


def record(con, opp: dict, horizon_s: int, out: dict, observed_asof: float, now: float | None = None) -> tuple[int | None, bool]:
    """Append when the result differs from the newest row for this window (a revert to an older value is a new row too)."""
    bh = _body_hash(out["state"], out["realized"], out["missing_reason"])
    prev = con.execute("SELECT id, state, realized_json, missing_reason, protocol_version FROM bt_outcomes WHERE opportunity_id=? AND horizon_s=? ORDER BY id DESC LIMIT 1",
                       (opp["opportunity_id"], horizon_s)).fetchone()
    if prev and _body_hash(prev["state"], json.loads(prev["realized_json"]) if prev["realized_json"] else None, prev["missing_reason"], prev["protocol_version"]) == bh:
        return prev["id"], False
    h = store.sha256([bh, prev["id"] if prev else None])
    return store._insert(con, "bt_outcomes", dict(opportunity_id=opp["opportunity_id"], chain=opp["chain"], mint=opp["mint"], decision_time=opp["decision_time"],
                         horizon_s=horizon_s, observed_asof=max(observed_asof, opp["decision_time"]), state=out["state"], realized_json=out["realized"],
                         protocol_version=PROTOCOL, censored=out["censored"], missing_reason=out["missing_reason"],
                         supersedes_id=prev["id"] if prev else None, content_hash=h, created_at=now if now is not None else time.time()))


def latest(con, asof: float | None = None) -> dict[tuple[str, int], dict]:
    """Newest outcome row per (opportunity, horizon) that was observable at `asof` (all rows when None)."""
    q = "SELECT * FROM bt_outcomes" + (" WHERE observed_asof<=?" if asof is not None else "") + " ORDER BY id"
    out = {}
    for r in con.execute(q, (asof,) if asof is not None else ()):
        out[(r["opportunity_id"], r["horizon_s"])] = dict(r) | {"realized": json.loads(r["realized_json"]) if r["realized_json"] else None}
    return out


# ---------------------------------------------------------------- scheduled tracker

def track(con, now: float, observed_asof: float | None = None, horizons=HORIZONS_S, min_interval_s: float = 3600.0, fetch=None,
          max_fetches: int = 20, retry_base_s: float = 600.0, retry_cap_s: float = 86400.0, opps: list[dict] | None = None,
          claim_wait_s: float = 2.0) -> dict:
    """One scheduled pass. Rate limited (one pass per min_interval_s), idempotent (unchanged results add no rows),
    optional bounded fetch for windows still missing bars with exponential retry per mint."""
    if con.in_transaction:
        con.commit()
    con.execute(f"PRAGMA busy_timeout = {int(claim_wait_s * 1000)}")
    try:
        con.execute("BEGIN IMMEDIATE")                              # claim the pass; another tracker writing now means skip, not crash
    except sqlite3.OperationalError as e:
        con.execute(f"PRAGMA busy_timeout = {int(store.BUSY_TIMEOUT_S * 1000)}")
        if "locked" in str(e) or "busy" in str(e):
            return {"status": "SKIPPED_BUSY", "reason": "another writer holds the research database; retry at the next scheduled pass"}
        raise
    con.execute(f"PRAGMA busy_timeout = {int(store.BUSY_TIMEOUT_S * 1000)}")
    last = con.execute("SELECT MAX(created_at) FROM bt_assessment_events WHERE event IN ('OUTCOME_TRACK_RUN','OUTCOME_TRACK_STARTED')").fetchone()[0]
    if last is not None and now - last < min_interval_s:
        con.rollback()
        return {"status": "SKIPPED_MIN_INTERVAL", "last_run_min_ago": round((now - last) / 60, 1)}
    store._insert(con, "bt_assessment_events", dict(request_key="outcomes", event="OUTCOME_TRACK_STARTED", detail=None, wall_ms=0.0, created_at=now))
    con.commit()
    asof = observed_asof if observed_asof is not None else now
    opps = opps if opps is not None else opportunities(con)
    counts, new_rows, fetched, deferred = defaultdict(int), 0, 0, 0
    want_fetch = set()
    for o in opps:
        for h in horizons:
            out = outcome_for(con, o, h, asof)
            _, ins = record(con, o, h, out, asof, now)
            new_rows += int(ins)
            counts[out["state"]] += 1
            if out["state"] == "CENSORED" and str(out["missing_reason"]).startswith("NO_BARS_IN_WINDOW") and (out["realized"] or {}).get("pool"):
                want_fetch.add((o["chain"], o["mint"], out["realized"]["pool"]))
        con.commit()                                                # short write transactions: other writers wait milliseconds
    if fetch:
        for chain, mint, pool in sorted(want_fetch):
            if fetched >= max_fetches:
                deferred += 1
                continue
            fails = con.execute("SELECT COUNT(*), MAX(created_at) FROM bt_assessment_events WHERE event='OUTCOME_FETCH_FAIL' AND detail=?", (mint,)).fetchone()
            n_fail, last_fail = fails[0] or 0, fails[1]
            if n_fail and now < last_fail + min(retry_cap_s, retry_base_s * 2 ** (n_fail - 1)):
                deferred += 1
                continue
            fetched += 1
            ok = False
            try:
                ok = bool(fetch(chain, mint, pool))
            except Exception:
                ok = False
            if not ok:
                store._insert(con, "bt_assessment_events", dict(request_key="outcomes", event="OUTCOME_FETCH_FAIL", detail=mint, wall_ms=0.0, created_at=now))
    store._insert(con, "bt_assessment_events", dict(request_key="outcomes", event="OUTCOME_TRACK_RUN",
                  detail=json.dumps({"asof": asof, "states": dict(counts), "new_rows": new_rows, "fetched": fetched, "deferred": deferred}), wall_ms=0.0, created_at=now))
    con.commit()
    return {"status": "RAN", "asof": asof, "opportunities": len(opps), "states": dict(counts), "new_rows": new_rows, "fetched": fetched, "deferred_fetches": deferred}


# ---------------------------------------------------------------- segments (all known at decision time)

def _sol_regime(con):
    from .runner import _first_versions
    from .sources import corpus
    bars = _first_versions(con, SOL, corpus.SOL_USDC_POOL)
    av = [b.avail for b in bars]

    def f(t: float) -> str:
        i = bisect.bisect_right(av, t) - 1
        if i < 24:
            return "UNKNOWN"
        r = bars[i].c / bars[i - 24].c - 1
        return "SOL_UP" if r > 0.03 else ("SOL_DOWN" if r < -0.03 else "SOL_FLAT")
    return f


def _liq_band(x) -> str:
    if x is None:
        return "UNKNOWN"
    x = float(x)
    return "<50k" if x < 5e4 else ("50k-250k" if x < 2.5e5 else ("250k-1M" if x < 1e6 else ">=1M"))


def _age_band(con, opp: dict) -> str:
    r = con.execute("SELECT MIN(pool_created_at) FROM bt_pool_versions WHERE chain=? AND mint=? AND available_at<=? AND pool_created_at IS NOT NULL",
                    (opp["chain"], opp["mint"], opp["decision_time"])).fetchone()[0]
    if r is None:
        return "UNKNOWN"
    age_h = (opp["decision_time"] - r) / 3600
    return "<6h" if age_h < 6 else ("6-24h" if age_h < 24 else ("1-7d" if age_h < 168 else ">=7d"))


def catalyst_known_at(con, opp: dict, catalysts: list[dict] | None = None) -> tuple[str, str]:
    """(catalyst type, source credibility) from records AVAILABLE at the decision time only. A later capture, a
    corrected publication time or a later deletion never changes what an earlier decision knew (G08)."""
    t = opp["decision_time"]
    recs = [c for c in (catalysts or []) if c.get("mint") == opp["mint"] and c.get("chain", "solana") == opp["chain"] and c["available_at"] <= t]
    for x in con.execute("SELECT record_type, mint_verified, historical_asof_proof, available_at, claim_state FROM bt_capture_provenance "
                         "WHERE chain=? AND mint=? AND available_at<=? ORDER BY available_at, id", (opp["chain"], opp["mint"], t)):
        recs.append({"claim_type": x["record_type"] or "CAPTURE", "mint_verified": bool(x["mint_verified"]), "historical_asof_proof": x["historical_asof_proof"],
                     "available_at": x["available_at"]})
    if not recs:
        return "NONE", "NO_CATALYST"
    first = min(recs, key=lambda c: c["available_at"])
    cred = ("VERIFIED_CONTEMPORANEOUS" if first.get("mint_verified") and first.get("historical_asof_proof") not in (None, "NONE")
            else ("VERIFIED_LATE_CAPTURE" if first.get("mint_verified") else "UNVERIFIED_MINT"))
    return str(first.get("claim_type") or "OTHER"), cred


def segments_for(con, opp: dict, regime, catalysts=None) -> dict:
    ctype, cred = catalyst_known_at(con, opp, catalysts)
    return {"cohort": f"{opp['source']}:{opp['status']}", "token_age": _age_band(con, opp), "liquidity_band": _liq_band(opp.get("liquidity")),
            "market_regime": regime(opp["decision_time"]), "catalyst_type": ctype, "source_credibility": cred}


# ---------------------------------------------------------------- calibration

def _wilson(k: int, n: int, z: float = 1.96):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - m), 4), round(min(1.0, c + m), 4)]


def _seg_stats(rows: list[dict]) -> dict:
    by = defaultdict(int)
    for r in rows:
        by[r["state"]] += 1
    comp = [r for r in rows if r["state"] == "COMPLETE"]
    obs = [r for r in rows if r["state"] in ("COMPLETE", "CENSORED") and r["realized"] and r["realized"].get("max_drawdown") is not None]
    rets = [r["realized"]["ret_close"] for r in comp]
    k50 = sum(1 for r in obs if r["realized"]["down_50"])
    out = {"n": len(rows), "complete": by["COMPLETE"], "censored": by["CENSORED"], "not_observable": by["NOT_OBSERVABLE"], "pending": by["PENDING"],
           "median_ret_close_complete": statistics.median(rets) if rets else None,
           "share_down_50_observed": (k50 / len(obs)) if obs else None, "share_down_50_ci95": _wilson(k50, len(obs)),
           "n_observed": len(obs)}
    out["verdict"] = "INSUFFICIENT_SAMPLE" if len(comp) < MIN_SEGMENT else "REPORTABLE"
    return out


def calibrate(con, asof: float | None = None, horizon_s: int = 24 * 3600, catalysts: list[dict] | None = None, opps: list[dict] | None = None) -> dict:
    opps = opps if opps is not None else opportunities(con)
    lat = latest(con, asof)
    regime = _sol_regime(con)
    dims = ("cohort", "token_age", "liquidity_band", "market_regime", "catalyst_type", "source_credibility")
    groups = {d: defaultdict(list) for d in dims}
    allrows = []
    for o in opps:
        row = lat.get((o["opportunity_id"], horizon_s))
        row = row if row else {"state": "NOT_TRACKED", "realized": None}
        seg = segments_for(con, o, regime, catalysts)
        allrows.append(row)
        for d in dims:
            groups[d][seg[d]].append(row)
    total = _seg_stats(allrows)
    total["not_tracked"] = sum(1 for r in allrows if r["state"] == "NOT_TRACKED")
    sel_bias = (total["not_observable"] + total["not_tracked"]) / max(1, total["n"])
    return {"protocol": PROTOCOL, "horizon_h": horizon_s / 3600, "asof": asof, "overall": total,
            "segments": {d: {k: _seg_stats(v) for k, v in sorted(groups[d].items())} for d in dims},
            "selection_bias_risk": sel_bias > 0.2, "not_observable_share": round(sel_bias, 4),
            "note": ("segments are historical correlations among the lab's own records, not causes; a segment with fewer than "
                     f"{MIN_SEGMENT} complete outcomes is INSUFFICIENT_SAMPLE; censored outcomes count in drawdown shares as observed lower bounds")}


# ---------------------------------------------------------------- slippage model reconciliation

def cpmm_sell_impact(size_usd: float, liquidity_usd: float) -> float:
    """Average-price shortfall of selling `size_usd` (at mid) into a constant-product pool with liquidity_usd split
    evenly: dx/(X+dx) = s/(L/2 + s). Fees are separate."""
    return size_usd / (liquidity_usd / 2 + size_usd)


def exit_reconciliation(con, opps: list[dict] | None = None, horizon_s: int = 24 * 3600, tol_s: float = 2 * 3600) -> dict:
    """Intended exit at the window end vs the stress model's liquidity (decision liquidity scaled by sqrt(price ratio))
    vs the liquidity the lab itself observed near the window end. Exact historical pool state is SOURCE_BLOCKED; the
    lab's later snapshot is the only observed basis."""
    opps = [o for o in (opps if opps is not None else opportunities(con, include_assessments=False)) if o.get("liquidity") and o.get("price")]
    lat = latest(con)
    rows, unobservable = [], 0
    for o in opps:
        out = lat.get((o["opportunity_id"], horizon_s))
        if not out or out["state"] != "COMPLETE":
            unobservable += 1
            continue
        tgt = o["decision_time"] + horizon_s
        later = con.execute("SELECT snapshot_json, available_at FROM bt_universe_members WHERE chain=? AND mint=? AND basis='THESIS' AND available_at BETWEEN ? AND ? "
                            "ORDER BY ABS(available_at - ?) LIMIT 1", (o["chain"], o["mint"], tgt - tol_s, tgt + tol_s, tgt)).fetchone()
        snap = json.loads(later["snapshot_json"]) if later and later["snapshot_json"] else {}
        if not snap.get("liquidity") or not snap.get("price"):
            unobservable += 1
            continue
        pred = float(o["liquidity"]) * math.sqrt(float(snap["price"]) / float(o["price"]))
        obs = float(snap["liquidity"])
        r = {"opportunity_id": o["opportunity_id"], "mint": o["mint"], "liquidity_band": _liq_band(o["liquidity"]), "liq_predicted": pred, "liq_observed": obs,
             "liq_error": obs / pred - 1, "by_size": {}}
        for s in SIZES_USD:
            ip, io = cpmm_sell_impact(s, pred), cpmm_sell_impact(s, obs)
            r["by_size"][str(int(s))] = {"impact_predicted": ip, "impact_observed": io, "impact_error": io - ip}
        rows.append(r)
    errs = [r["liq_error"] for r in rows]
    by_band = defaultdict(list)
    for r in rows:
        by_band[r["liquidity_band"]].append(r["liq_error"])
    size_err = {str(int(s)): [r["by_size"][str(int(s))]["impact_error"] for r in rows] for s in SIZES_USD}
    return {"horizon_h": horizon_s / 3600, "pairs": len(rows), "not_observable": unobservable,
            "liq_error_median": statistics.median(errs) if errs else None, "liq_error_p10_p90": ([sorted(errs)[int(0.1 * len(errs))], sorted(errs)[min(len(errs) - 1, int(0.9 * len(errs)))]] if errs else None),
            "by_liquidity_band": {k: {"n": len(v), "median_error": statistics.median(v)} for k, v in sorted(by_band.items())},
            "impact_error_median_by_size": {k: (statistics.median(v) if v else None) for k, v in size_err.items()},
            "basis": "LAB_SNAPSHOT_NEAR_WINDOW_END (exact historical pool state SOURCE_BLOCKED)", "rows": rows,
            "verdict": "INSUFFICIENT_SAMPLE" if len(rows) < MIN_SEGMENT else "REPORTABLE"}


# ---------------------------------------------------------------- drift and quality

def collector_health(con) -> dict:
    """Monitoring of the chosen collectors (existing catalyst layer, Firecrawl, Crawl4AI captures). Maxun was not
    adopted (Phase 06A), so no Maxun metrics are reported."""
    rows = [dict(r) for r in con.execute("SELECT collector, run_status, extraction_status, extractor_version, content_hash, canonical_origin, "
                                         "first_seen_at, source_published_at, mint, mint_verified, captured_at FROM bt_capture_provenance ORDER BY captured_at")]
    out = {"maxun": "NOT_ADOPTED (Phase 06A): no Maxun robot runs, no Maxun metrics", "collectors": {}}
    by = defaultdict(list)
    for r in rows:
        by[r["collector"]].append(r)
    for c, rs in sorted(by.items()):
        late = [r for r in rs if r["source_published_at"] and r["first_seen_at"] - r["source_published_at"] > 6 * 3600]
        hashes = defaultdict(int)
        for r in rs:
            hashes[(r["canonical_origin"], r["content_hash"])] += 1
        caps = sorted(r["captured_at"] for r in rs)
        gaps = [b - a for a, b in zip(caps, caps[1:])]
        out["collectors"][c] = {"captures": len(rs), "late_arrival_share": len(late) / len(rs), "duplicate_share": sum(v - 1 for v in hashes.values()) / len(rs),
                                "misattribution_risk_share": sum(1 for r in rs if r["mint"] and not r["mint_verified"]) / len(rs),
                                "extractor_versions": sorted({r["extractor_version"] or "none" for r in rs}),
                                "incomplete_extraction_share": sum(1 for r in rs if r["extraction_status"] not in ("OK", "REFINED_DATE")) / len(rs),
                                "failed_run_share": sum(1 for r in rs if r["run_status"] not in (None, "OK")) / len(rs),
                                "longest_gap_h": (max(gaps) / 3600) if gaps else None}
    if not rows:
        out["note"] = "NO_DATA: no captures stored in this database; nothing to monitor yet"
    return out


def drift(con, now: float, calibration_horizon_s: int = 24 * 3600, opps: list[dict] | None = None, coverage_drop: float = 0.2,
          shift: float = 0.25, stale_pending_s: float = 24 * 3600) -> dict:
    opps = opps if opps is not None else opportunities(con)
    lat = latest(con)
    warnings = []
    # provider coverage drift: share of opportunities whose window has price bars, by decision day
    by_day = defaultdict(lambda: [0, 0])
    for o in opps:
        r = lat.get((o["opportunity_id"], calibration_horizon_s))
        if not r or r["state"] == "PENDING":
            continue
        by_day[_day(o["decision_time"])][0] += 1
        has_bars = r["state"] == "COMPLETE" or (r["state"] == "CENSORED" and (r["realized"] or {}).get("max_drawdown") is not None)
        by_day[_day(o["decision_time"])][1] += int(has_bars)            # windows with price bars; a gap or a dead feed counts as uncovered
    days = sorted(by_day)
    cov = {d: {"n": by_day[d][0], "observable_share": by_day[d][1] / by_day[d][0]} for d in days}
    if len(days) >= 6:
        early = [cov[d]["observable_share"] for d in days[:-3]]
        recent = [cov[d]["observable_share"] for d in days[-3:]]
        if statistics.mean(early) - statistics.mean(recent) > coverage_drop:
            warnings.append({"kind": "PROVIDER_COVERAGE_DRIFT", "detail": f"observable share fell from {statistics.mean(early):.0%} to {statistics.mean(recent):.0%} over the last 3 decision days"})
    # stale pending outcomes
    stale = [k for k, r in lat.items() if r["state"] == "PENDING" and now - (r["decision_time"] + r["horizon_s"]) > stale_pending_s]
    if stale:
        warnings.append({"kind": "STALE_PENDING", "detail": f"{len(stale)} outcome windows closed more than {stale_pending_s / 3600:.0f} h ago and still pending (tracker not run or data not fetched)"})
    # outcome calibration drift: share down 50% per cohort, first half vs second half of decision time
    halves = defaultdict(lambda: ([], []))
    if opps:
        mid = statistics.median(o["decision_time"] for o in opps)
        for o in opps:
            r = lat.get((o["opportunity_id"], calibration_horizon_s))
            if r and r["state"] in ("COMPLETE", "CENSORED") and r["realized"] and "down_50" in r["realized"]:
                halves[f"{o['source']}:{o['status']}"][0 if o["decision_time"] < mid else 1].append(bool(r["realized"]["down_50"]))
    cal = {}
    for k, (a, b) in sorted(halves.items()):
        cal[k] = {"n_first": len(a), "n_second": len(b), "share_first": (sum(a) / len(a)) if a else None, "share_second": (sum(b) / len(b)) if b else None}
        if len(a) >= MIN_SEGMENT and len(b) >= MIN_SEGMENT and abs(cal[k]["share_first"] - cal[k]["share_second"]) > shift:
            warnings.append({"kind": "CALIBRATION_DRIFT", "detail": f"{k}: share down 50% moved from {cal[k]['share_first']:.0%} to {cal[k]['share_second']:.0%}"})
    # bar revisions observed (provider rewrote history)
    rev = con.execute("SELECT COUNT(*) FROM bt_market_bars WHERE quality_flags LIKE '%REVISION%'").fetchone()[0]
    tot = con.execute("SELECT COUNT(*) FROM bt_market_bars").fetchone()[0]
    if tot and rev / tot > 0.01:
        warnings.append({"kind": "PROVIDER_REVISIONS", "detail": f"{rev} of {tot} bars were revised by the provider after first fetch"})
    return {"now": now, "coverage_by_decision_day": cov, "calibration_halves": cal, "bar_revisions": {"revised": rev, "total": tot},
            "collector_health": collector_health(con), "warnings": warnings}


# ---------------------------------------------------------------- shadow evaluation and deferred re-evaluation

def shadow(con, strategy_id: str, since: float, params: dict | None = None, until: float | None = None) -> dict:
    """Run a frozen strategy forward on decisions after `since` without saving a run and without any order path.
    Labeled SHADOW; it informs re-evaluation, it never changes the strategy."""
    from . import runner
    res = runner.run(con, strategy_id, params=params, decide_from=since, until=until, save=False)
    return {"mode": "SHADOW (no orders, not saved as a run)", "strategy": strategy_id, "since": since, "until": until, "n_trades": res.get("n_trades"),
            "mean_ret": res.get("mean_ret"), "mean_paper_ret_mid": res.get("mean_paper_ret_mid"), "ledger_hash": res.get("ledger_hash")}


def propose_reevaluation(con, strategy_id: str, findings: list[dict], now: float) -> dict:
    """Record that observed deviations call for a re-evaluation. The proposal names what a new evaluation needs; it
    changes no parameter, no frozen strategy version and no prior run."""
    body = {"strategy": strategy_id, "findings": findings}
    key = store.sha256(body)
    store._insert(con, "bt_assessment_events", dict(request_key="reeval:" + key, event="REEVALUATION_PROPOSED", detail=json.dumps(body, sort_keys=True, default=str),
                  wall_ms=0.0, created_at=now))
    con.commit()
    return {"proposal": key, "strategy": strategy_id, "status": "PROPOSED",
            "requires": ["a new pre-registration (hash recorded before any new data is looked at)",
                         "a new sealed train/validation/test split that starts after the current sealed test",
                         "a new strategy version id; the current version and its runs stay as they are",
                         "a logged change entry in docs/backtesting/DECISIONS.md"],
            "findings": findings}


def retune_in_place(*_a, **_k):
    raise PermissionError("in-place retuning is not allowed: register a new strategy version through a new pre-registration and sealed test (Phase 15 policy)")


def deviations(drift_out: dict, recon: dict | None = None) -> list[dict]:
    """Findings worth a re-evaluation proposal: calibration drift (lab status cohorts) and slippage-model error."""
    f = [w for w in drift_out.get("warnings") or [] if w["kind"] in ("CALIBRATION_DRIFT", "PROVIDER_COVERAGE_DRIFT")]
    if recon and recon.get("liq_error_median") is not None and abs(recon["liq_error_median"]) > 0.25 and recon.get("pairs", 0) >= MIN_SEGMENT:
        f.append({"kind": "SLIPPAGE_MODEL_ERROR", "detail": f"median liquidity forecast error {recon['liq_error_median']:+.0%} over {recon['pairs']} pairs"})
    return f


# ---------------------------------------------------------------- daily report (replayable)

def daily_report(con, day: str, asof: float, horizon_s: int = 24 * 3600, opps: list[dict] | None = None) -> str:
    """Opportunities first recorded on `day` (UTC), ranked by the lab's score at decision, with outcomes as observable at
    `asof`. Decision columns come from the frozen records; only the outcome columns can change with a later asof."""
    opps = [o for o in (opps if opps is not None else opportunities(con)) if _day(o["decision_time"]) == day]
    opps.sort(key=lambda o: (-(o["score"] if o["score"] is not None else -1), o["mint"], o["source"], o["status"]))
    lat = latest(con, asof)
    L = [f"# Outcomes for opportunities first recorded on {day} (UTC)", "",
         f"Outcomes as observable at {datetime.fromtimestamp(asof, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}, window {horizon_s // 3600} h, protocol {PROTOCOL}. "
         "Research only; decision columns are the lab's frozen records.", ""]
    if not opps:
        L.append("No opportunity was recorded that day.")
    for i, o in enumerate(opps, 1):
        r = lat.get((o["opportunity_id"], horizon_s))
        st = r["state"] if r else "NOT_TRACKED"
        rz = (r or {}).get("realized") or {}
        res = (f"close {rz['ret_close']:+.1%}, worst {rz['max_drawdown']:+.1%}, best {rz['max_runup']:+.1%}" if st == "COMPLETE" else
               (f"{r['missing_reason']}" + (f"; worst seen {rz['max_drawdown']:+.1%}" if rz.get("max_drawdown") is not None else "") if r else "not tracked yet"))
        L.append(f"{i}. {o['symbol'] or '?'} `{o['chain']}:{o['mint']}` | decided {datetime.fromtimestamp(o['decision_time'], timezone.utc).strftime('%H:%M:%S')} | "
                 f"{o['source']} {o['status']} score {o['score']} liq {_liq_band(o.get('liquidity'))} | {st}: {res}")
    return "\n".join(L) + "\n"


def render_calibration(cal: dict) -> str:
    L = [f"# Outcome calibration, {cal['horizon_h']:g} h window ({cal['protocol']})", "", cal["note"] + ".", ""]
    o = cal["overall"]
    L.append(f"Overall: {o['n']} opportunities, {o['complete']} complete, {o['censored']} censored, {o['not_observable']} not observable, {o['pending']} pending. "
             f"Selection-bias risk: {'yes' if cal['selection_bias_risk'] else 'no'} ({cal['not_observable_share']:.0%} not observable or not tracked).")
    for d, segs in cal["segments"].items():
        L += ["", f"## {d}", ""]
        for k, s in segs.items():
            med = "n/a" if s["median_ret_close_complete"] is None else f"{s['median_ret_close_complete']:+.1%}"
            sh = "n/a" if s["share_down_50_observed"] is None else f"{s['share_down_50_observed']:.0%} (95% {s['share_down_50_ci95'][0]:.0%} to {s['share_down_50_ci95'][1]:.0%}, n {s['n_observed']})"
            L.append(f"- {k}: n {s['n']}, complete {s['complete']}, censored {s['censored']}, not observable {s['not_observable']}; median close {med}; "
                     f"down 50% or more {sh}; {s['verdict']}")
    return "\n".join(L) + "\n"
