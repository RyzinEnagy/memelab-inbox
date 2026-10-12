"""Phase 11: Information Alpha Score. Pure engine, no I/O, no network, no clock.

Question answered: after a public post about a token, did the token do better than comparable tokens, net of a realistic delay and trading
frictions, and is the sample large and clean enough to say so? It does not measure wallet profits (Phase 10 does, separately), and it never
reads follower counts or engagement (those are echoed as context only).

Input document `memelab.alpha.input/1`: sources, calls, price series (historical candles only), optional attributed author trades.
Every observation carries a source reference. Rules are fixed before any outcome is looked at (SELECTION_RULES below) and are part of the
policy hash. Calls that fail a rule stay in the output with a reason; nothing is dropped silently.

Time discipline: the entry time is max(published_at, first_observed_at) + delay. Only candles that start at or before a decision time are used
to decide anything at that time (entry price, liquidity, matching features). Exit prices come from the candle at entry + horizon, never from
a later quote. A horizon that has not elapsed at `as_of` is not evaluable.
"""
from __future__ import annotations

import hashlib
import json
import math
from bisect import bisect_left, bisect_right
from statistics import median

ENGINE_VERSION = "information-alpha-v1"
RULES_VERSION = "alpha-rules-v1"
SCHEMA = "memelab.alpha.input/1"

DEFAULT_POLICY = {
    "horizons_s": [3600, 21600, 86400, 259200, 604800],      # 1h, 6h, 24h, 72h, 7d
    "primary_horizon_s": 86400,                              # the one horizon the score uses; the others are reported, never blended
    "delay_s": 300,                                          # time from knowing about the post to a filled order
    "max_capture_lag_s": 3600,                               # first observed more than this after publication: possible hindsight capture
    "max_entry_wait_s": 900,                                 # an order may wait this long for the next candle when none covers the entry time
    "max_exit_wait_s": 900,
    "entry_price_rule": "OPEN",                              # OPEN | CANDLE_ADVERSE (high to buy, low to sell/cover)
    "trade_size_usd": 500.0,
    "fee_bps_per_side": 100.0,                               # venue and platform fees
    "slippage_bps_per_side": 50.0,                           # base execution slippage on top of fees and impact
    "max_participation": 0.05,                               # size / pool liquidity above this at entry: not tradable at this size
    "unknown_exit_cost": 0.5,                                # exit cost when exit liquidity is unknown (conservative)
    "dedupe_window_s": 604800,                               # same source, same token, same direction inside this window counts once
    "conflict_window_s": 86400,                              # opposite statements inside this window exclude both
    "min_path_coverage": 0.8,                                # share of expected candles needed for MFE / MAE
    "onset_threshold": 0.2,                                  # a signed move of this size from the reference marks the move onset
    "pre_window_s": 21600,                                   # lookback for the pre-post move and the lead time
    "late_promotion_threshold": 1.0,                         # signed pre-post move at or above this flags LATE_PROMOTION
    "trade_window_s": 86400,                                 # attributed author trades this long before / after the post are shown
    "baseline_k": 8,                                         # matched comparison tokens per call
    "min_baseline": 5,                                       # fewer than this at a horizon: no relative return there
    "baseline_max_liq_ratio": 4.0,                           # comparison pool liquidity within this factor of the call token's
    "ci_min_n": 8,                                           # no confidence interval below this many values
    "min_calls_preliminary": 10,
    "min_calls_validated": 30,
    "min_distinct_tokens_validated": 20,
    "min_coverage_preliminary": 0.5,                         # evaluated / eligible at the primary horizon
    "min_coverage_validated": 0.7,
    "min_completeness_validated": 0.9,                       # supplied calls / calls the collector enumerated for the source
    "min_completeness_preliminary": 0.8,
    "max_top_token_share_validated": 0.2,
    "min_half_n": 10,                                        # each chronological half needs this many for the split-sample check
    "shrink_k": 20.0,                                        # evidence weight w = n / (n + k)
    "edge_scale": 0.5,                                       # shrunk median relative return that maps to a score of about 88
    "max_uncertainty": "medium",                             # extraction uncertainty above this: call is not evaluated
}

SELECTION_RULES = [
    "A call is evaluated if it has a source reference, a resolved token (chain and contract), a known publication time, is an original (not a repost, forward or quote of another item), and states LONG, SHORT or EXIT.",
    "A call published or first observed after the run's as_of time is ineligible (AFTER_AS_OF). No candle that starts after as_of is ever read.",
    "NEUTRAL or UNKNOWN direction, conditional claims, suspected sarcasm and extractions with uncertainty above the policy limit are listed as ineligible, not scored.",
    "A call first observed later than max_capture_lag_s after publication, or with an unknown observation time, is ineligible (HINDSIGHT_CAPTURE_RISK): it may have been picked after the outcome was known.",
    "Opposite statements on one token by one source inside conflict_window_s exclude all of them (CONFLICTING_STATEMENTS). The later statement never overrides the earlier one.",
    "Repeat posts (same source, token, direction) inside dedupe_window_s after an evaluated call are not independent (REPEAT_POST).",
    "Eligibility never depends on the outcome. Every eligible call is evaluated whether it won, lost or did nothing. Calls without usable price data stay in the coverage count with a reason.",
    "One primary horizon is fixed by policy. Other horizons are reported as secondary and are never mixed into the score.",
    "Prices are historical candles only. A series marked as observed-at-fetch (a live quote) is rejected, never used as a past price.",
    "Comparison tokens are matched on liquidity and trailing volume known before entry, from tokens with candles that exist at entry time, delisted ones included. Every token that any source in the run called is excluded from the comparison pool, because promoted tokens are not a neutral control.",
]

BULL, BEAR = "BULL", "BEAR"
_DIR = {"LONG": (BULL, 1), "SHORT": (BEAR, -1), "EXIT": (BEAR, -1)}
_UNC = {"low": 0, "medium": 1, "high": 2}


# ---------- small numeric helpers ----------

def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def r10(x):
    return None if x is None else round(float(x), 10)


def canon(o) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)


def sha(o) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


def quantile(xs, q):
    s = sorted(xs)
    if not s:
        return None
    pos = (len(s) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def median_ci(xs, conf=0.95):
    """Distribution-free interval for the median from order statistics (binomial, conservative). None when n is too small to reach `conf`."""
    n, s, alpha = len(xs), sorted(xs), 1 - conf
    k, cum = 0, 0.0
    for j in range(0, n // 2 + 1):
        cum += math.comb(n, j) / 2 ** n
        if cum <= alpha / 2:
            k = j + 1
        else:
            break
    if k == 0:
        return None
    return s[k - 1], s[n - k]


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


# ---------- price series ----------

def prep_series(doc: dict) -> tuple[dict, list]:
    """Validate supplied candle series. A bad series is rejected whole with a reason; it is never repaired."""
    out, rejected = {}, []
    for s in doc.get("series") or []:
        chain, contract = str(s.get("chain") or "").lower(), str(s.get("contract") or "")
        key = (chain, contract)
        ref = {"chain": chain, "contract": contract}

        def rej(reason, **extra):
            rejected.append(dict(ref, reason=reason, **extra))

        if not chain or not contract:
            rej("NO_TOKEN")
        elif key in out or any(r["chain"] == chain and r["contract"] == contract for r in rejected):
            rejected.append(dict(ref, reason="DUPLICATE_SERIES"))
            out.pop(key, None)
        elif s.get("as_of_kind") != "HISTORICAL_CANDLE":
            rej("LIVE_QUOTE_REPLAY", as_of_kind=s.get("as_of_kind"))
        elif not s.get("source"):
            rej("NO_SOURCE")
        elif not (isinstance(s.get("candle_seconds"), int) and s["candle_seconds"] > 0):
            rej("BAD_CANDLE_SECONDS")
        else:
            rows, ok, last = [], True, None
            for r in s.get("rows") or []:
                if not all(_num(r.get(k)) for k in ("t", "o", "h", "l", "c")) or min(r["o"], r["h"], r["l"], r["c"]) <= 0 \
                        or r["h"] < max(r["o"], r["c"]) or r["l"] > min(r["o"], r["c"]) or (last is not None and r["t"] <= last):
                    ok = False
                    break
                if r.get("liq") is not None and not (_num(r["liq"]) and r["liq"] >= 0):
                    ok = False
                    break
                last = r["t"]
                rows.append(r)
            dl = s.get("delisted_at")
            if not ok or not rows:
                rej("BAD_CANDLES")
            elif dl is not None and (not _num(dl) or rows[-1]["t"] >= dl):
                rej("CANDLE_AFTER_DELISTING")
            else:
                out[key] = {"rows": rows, "starts": [r["t"] for r in rows], "period": s["candle_seconds"], "delisted_at": dl,
                            "source": s["source"], "chain": chain, "contract": contract}
    return out, rejected


def _candle_at(ser, t, max_wait):
    """(row, wait_s) for the candle that covers t, else the first candle starting within max_wait after t, else (None, reason)."""
    i = bisect_right(ser["starts"], t) - 1
    if i >= 0 and t < ser["starts"][i] + ser["period"]:
        return ser["rows"][i], 0
    j = bisect_left(ser["starts"], t)
    if j >= len(ser["rows"]):
        return None, "HISTORY_ENDS"
    wait = ser["rows"][j]["t"] - t
    if wait > max_wait:
        return None, "PRICE_GAP"
    return ser["rows"][j], wait


def _cost(size, liq, pol):
    """Per-side cost as a fraction: fees + slippage + constant-product price impact 2 * size / liquidity."""
    base = (pol["fee_bps_per_side"] + pol["slippage_bps_per_side"]) / 1e4
    if liq is None or liq <= 0:
        return None, None, base
    part = size / liq
    return base + 2 * part, part, base


def entry_for(ser, t, d, pol, as_of):
    """Decide an entry at decision time t using only candles that start at or before the fill. Returns (entry dict, None) or (None, reason)."""
    dl = ser["delisted_at"]
    if dl is not None and dl <= t:
        return None, "TOKEN_DELISTED_BEFORE_ENTRY"
    if t > as_of:
        return None, "ENTRY_AFTER_AS_OF"
    row, wait = _candle_at(ser, t, pol["max_entry_wait_s"])
    if row is None:
        return None, "NO_ENTRY_PRICE_" + wait
    if row["t"] > as_of:
        return None, "ENTRY_AFTER_AS_OF"
    if dl is not None and row["t"] >= dl:
        return None, "TOKEN_DELISTED_BEFORE_ENTRY"
    liq = row.get("liq")
    cost, part, base = _cost(pol["trade_size_usd"], liq, pol)
    if cost is None:
        return None, "LIQUIDITY_UNKNOWN"
    if part > pol["max_participation"]:
        return None, "ILLIQUID_ENTRY"
    price = row["o"] if pol["entry_price_rule"] == "OPEN" else (row["h"] if d > 0 else row["l"])
    return {"decision_t": t, "fill_t": max(t, row["t"]), "candle_t": row["t"], "wait_s": wait, "price": price, "liq": liq, "participation": r10(part),
            "cost": r10(cost), "fee_slip": r10(base), "rule": pol["entry_price_rule"], "source": ser["source"]}, None


def exit_for(ser, t_exit, d, pol, as_of):
    """Exit at t_exit. Returns (exit dict, None) or (None, reason). A delisting before t_exit is a total loss for a long, last-seen price for a short."""
    if t_exit > as_of:
        return None, "HORIZON_NOT_ELAPSED"
    dl = ser["delisted_at"]
    if dl is not None and dl <= t_exit:
        last = ser["rows"][-1]
        if d > 0:
            return {"t": dl, "price": 0.0, "cost": 0.0, "liq": None, "kind": "DELISTED_TOTAL_LOSS", "source": ser["source"]}, None
        c, _, base = _cost(pol["trade_size_usd"], last.get("liq"), pol)
        return {"t": last["t"], "price": last["c"], "cost": r10(min(1.0, c if c is not None else pol["unknown_exit_cost"])),
                "liq": last.get("liq"), "kind": "DELISTED_LAST_PRICE_NO_EXTRA_CREDIT", "source": ser["source"]}, None
    row, wait = _candle_at(ser, t_exit, pol["max_exit_wait_s"])
    if row is None:
        return None, "NO_EXIT_PRICE_" + wait
    if row["t"] > as_of:
        return None, "HORIZON_NOT_ELAPSED"
    c, part, base = _cost(pol["trade_size_usd"], row.get("liq"), pol)
    kind = "CANDLE"
    if c is None:
        c, kind = pol["unknown_exit_cost"], "EXIT_LIQUIDITY_UNKNOWN"
    price = row["o"] if pol["entry_price_rule"] == "OPEN" else (row["l"] if d > 0 else row["h"])
    return {"t": max(t_exit, row["t"]), "candle_t": row["t"], "wait_s": wait, "price": price, "cost": r10(min(1.0, c)), "liq": row.get("liq"),
            "participation": r10(part), "kind": kind, "source": ser["source"]}, None


def net_return(en, ex, d):
    """Signed net return. Long: proceeds after exit cost over outlay after entry cost, floor -1. Short/exit (information return, not
    executable on spot): minus the price move, minus both costs."""
    if d > 0:
        return (ex["price"] * (1 - ex["cost"])) / (en["price"] * (1 + en["cost"])) - 1
    return -(ex["price"] / en["price"] - 1) - en["cost"] - ex["cost"]


def path_stats(ser, en, ex, d, pol):
    """Maximum favourable / adverse excursion from the fill, gross of exit costs, only when enough candles cover the path."""
    start, end = en["fill_t"], ex["t"]
    rows = [r for r in ser["rows"] if start <= r["t"] <= end]
    expected = max(1, int((end - start) / ser["period"]))
    cov = min(1.0, len(rows) / expected)
    if ex.get("kind", "").startswith("DELISTED"):
        return {"status": "NOT_COMPUTED_DELISTED", "coverage": r10(cov)}
    if cov < pol["min_path_coverage"] or not rows:
        return {"status": "INSUFFICIENT_PATH_COVERAGE", "coverage": r10(cov)}
    hi, lo = max(r["h"] for r in rows), min(r["l"] for r in rows)
    p = en["price"]
    mfe = (hi / p - 1) if d > 0 else (1 - lo / p)
    mae = (lo / p - 1) if d > 0 else (1 - hi / p)
    return {"status": "OK", "coverage": r10(cov), "mfe": r10(mfe), "mae": r10(mae), "candles": len(rows)}


def trailing_volume(ser, t):
    return sum(r.get("v") or 0.0 for r in ser["rows"] if r["t"] + ser["period"] <= t and r["t"] > t - 86400)


# ---------- the evaluation of one call ----------

def _eligibility(doc, pol, series):
    """Apply the fixed selection rules. Returns {call_id: reasons} and the cleaned call list in time order."""
    calls = []
    for i, c in enumerate(doc.get("calls") or []):
        c = dict(c)
        c["_i"] = i
        c["call_id"] = str(c.get("call_id") or f"call{i}")
        calls.append(c)
    ids = [c["call_id"] for c in calls]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate call_id")
    reasons = {c["call_id"]: [] for c in calls}
    live = []
    for c in calls:
        r = reasons[c["call_id"]]
        tok = c.get("token") or {}
        if not (c.get("item_key") or c.get("observation_ref") or c.get("source_url")):
            r.append("NO_SOURCE")
        elif not (tok.get("chain") and tok.get("contract")):
            r.append("TOKEN_UNRESOLVED")
        elif not c.get("original", False):
            r.append("NOT_ORIGINAL")
        elif not _num(c.get("published_at")):
            r.append("PUBLISHED_AT_UNKNOWN")
        elif c["published_at"] > doc["as_of"] or (_num(c.get("first_observed_at")) and c["first_observed_at"] > doc["as_of"]):
            r.append("AFTER_AS_OF")
        elif str(c.get("direction")) not in _DIR:
            r.append("NO_DIRECTION")
        elif c.get("conditional"):
            r.append("CONDITIONAL_CLAIM")
        elif c.get("sarcasm_suspected"):
            r.append("SARCASM_SUSPECTED")
        elif _UNC.get(str(c.get("uncertainty") or "low"), 2) > _UNC[pol["max_uncertainty"]]:
            r.append("HIGH_UNCERTAINTY_EXTRACTION")
        elif not _num(c.get("first_observed_at")) or c["first_observed_at"] - c["published_at"] > pol["max_capture_lag_s"]:
            r.append("HINDSIGHT_CAPTURE_RISK")
        elif c["first_observed_at"] < c["published_at"] - 60:
            r.append("OBSERVED_BEFORE_PUBLISHED")      # a clock or data error: the sighting cannot predate the post
        else:
            live.append(c)
    # conflicting statements
    groups = {}
    for c in live:
        groups.setdefault((c["source_id"], c["token"]["chain"], c["token"]["contract"].lower() if c["token"]["chain"] != "solana" else c["token"]["contract"]), []).append(c)
    for g in groups.values():
        g.sort(key=lambda c: (c["published_at"], c["call_id"]))
        for a in range(len(g)):
            for b in range(a + 1, len(g)):
                if _DIR[g[a]["direction"]][0] != _DIR[g[b]["direction"]][0] and abs(g[b]["published_at"] - g[a]["published_at"]) <= pol["conflict_window_s"]:
                    for c in (g[a], g[b]):
                        if "CONFLICTING_STATEMENTS" not in reasons[c["call_id"]]:
                            reasons[c["call_id"]].append("CONFLICTING_STATEMENTS")
    # repeats
    for g in groups.values():
        last = {}
        for c in g:
            if reasons[c["call_id"]]:
                continue
            cls = _DIR[c["direction"]][0]
            if cls in last and c["published_at"] - last[cls] <= pol["dedupe_window_s"]:
                reasons[c["call_id"]].append("REPEAT_POST")
            else:
                last[cls] = c["published_at"]
    calls.sort(key=lambda c: (c["published_at"] if _num(c.get("published_at")) else float("inf"), c["call_id"]))
    return calls, reasons


def _tkey(tok):
    return tok["chain"], tok["contract"]


def _baseline(call, d, t0, series, pol, as_of, banned):
    """Matched comparison tokens for one call: features from candles completed before the entry, same entry/exit/frictions rules."""
    main = series[_tkey(call["token"])]
    en, _ = entry_for(main, t0, d, pol, as_of)
    f_liq, f_vol = en["liq"], trailing_volume(main, t0)
    cands = []
    for key, ser in series.items():
        if key[0] != call["token"]["chain"] or key == _tkey(call["token"]) or key in banned:
            continue
        e, why = entry_for(ser, t0, d, pol, as_of)
        if e is None:
            continue
        ratio = e["liq"] / f_liq
        if ratio > pol["baseline_max_liq_ratio"] or ratio < 1 / pol["baseline_max_liq_ratio"]:
            continue
        dist = abs(math.log(ratio)) + 0.5 * abs(math.log((trailing_volume(ser, t0) + 1) / (f_vol + 1)))
        cands.append((dist, key[1], key, e))
    cands.sort(key=lambda x: (x[0], x[1]))
    return cands[: pol["baseline_k"]]


def _author_context(call, trades, pol):
    pub = call["published_at"]
    mine = [t for t in trades if t.get("source_id") == call["source_id"] and t.get("chain") == call["token"]["chain"]
            and t.get("contract") == call["token"]["contract"] and t.get("t") is not None]
    pre = [t for t in mine if pub - pol["trade_window_s"] <= t["t"] <= pub]
    post = [t for t in mine if pub < t["t"] <= pub + pol["trade_window_s"]]
    bought_pre = any(t["side"] == "BUY" for t in pre)
    sold_post = any(t["side"] == "SELL" for t in post)
    declared = call.get("author_position") in ("holds", "sold")
    flags = []
    if bought_pre and not declared:
        flags.append("UNDISCLOSED_PRIOR_BUY")
    if sold_post and call["direction"] == "LONG":
        flags.append("SOLD_AFTER_PROMOTING")
    return {"attributed_trades_pre": len(pre), "attributed_trades_post": len(post), "flags": flags,
            "assertions": sorted({t.get("assertion", "UNKNOWN") for t in pre + post}), "sources": sorted({str(t.get("source")) for t in pre + post}),
            "used_in_score": False}


def _evaluate_call(call, reasons, series, pol, as_of, doc, banned):
    d_cls, d = _DIR.get(str(call.get("direction")), (None, 0))
    tok = call.get("token") or {}
    out = {"call_id": call["call_id"], "source_id": call.get("source_id"), "token": {"chain": tok.get("chain"), "contract": tok.get("contract")},
           "direction": call.get("direction"), "published_at": call.get("published_at"), "first_observed_at": call.get("first_observed_at"),
           "reference": call.get("item_key") or call.get("observation_ref") or call.get("source_url"),
           "reasons": list(reasons), "eligible": not reasons, "horizons": {}, "flags": []}
    if reasons:
        out["status"] = "INELIGIBLE"
        return out
    ser = series.get(_tkey(tok))
    if ser is None:
        out["status"], out["reasons"] = "UNEVALUABLE", ["NO_PRICE_HISTORY"]
        return out
    t0 = max(call["published_at"], call["first_observed_at"]) + pol["delay_s"]
    out["decision_t"] = t0
    en, why = entry_for(ser, t0, d, pol, as_of)
    if en is None:
        out["status"], out["reasons"] = "UNEVALUABLE", [why]
        return out
    out["entry"] = en
    members = _baseline(call, d, t0, series, pol, as_of, banned)
    out["baseline_tokens"] = [m[1] for m in members]
    for h in pol["horizons_s"]:
        row = {"horizon_s": h}
        ex, why = exit_for(ser, t0 + h, d, pol, as_of)
        if ex is None:
            row.update(status="NOT_EVALUABLE", reason=why)
            out["horizons"][str(h)] = row
            continue
        net = net_return(en, ex, d)
        gross = (ex["price"] / en["price"] - 1) * (1 if d > 0 else -1)
        row.update(status="OK", exit=ex, gross=r10(gross), net=r10(net), execution_cost_in=en["cost"], execution_cost_out=ex["cost"])
        if h == pol["primary_horizon_s"]:
            row["path"] = path_stats(ser, en, ex, d, pol)
        # matched baseline, same rules, same horizon
        bl = []
        for _dist, contract, key, e in members:
            bser = series[key]
            bex, bwhy = exit_for(bser, t0 + h, d, pol, as_of)
            if bex is None:
                continue
            bl.append({"contract": contract, "net": r10(net_return(e, bex, d)), "exit_kind": bex["kind"]})
        row["baseline"] = {"n": len(bl), "members": bl}
        if len(bl) >= pol["min_baseline"]:
            bm = median([b["net"] for b in bl])
            row["baseline"]["median"] = r10(bm)
            row["relative"] = r10(net - bm)
        else:
            row["baseline"]["median"] = None
            row["relative"] = None
            row["baseline"]["reason"] = "FEWER_THAN_MIN_BASELINE"
        out["horizons"][str(h)] = row
    # lead time, pre-post move, move lag, liquidity change
    pub = call["published_at"]
    pre_rows = [r for r in ser["rows"] if pub - pol["pre_window_s"] <= r["t"] <= pub]
    if pre_rows:
        ref = pre_rows[0]["o"]
        at_pub = _candle_at(ser, pub, 0)[0] or pre_rows[-1]
        pre_move = d * (at_pub["o"] / ref - 1)
        out["pre_move"] = r10(pre_move)
        if pre_move >= pol["late_promotion_threshold"]:
            out["flags"].append("LATE_PROMOTION")
        onset = None
        end_t = pub + max(pol["horizons_s"])
        for r in ser["rows"]:
            if r["t"] < pre_rows[0]["t"] or r["t"] > end_t or r["t"] + ser["period"] > as_of:
                continue
            if d * (r["c"] / ref - 1) >= pol["onset_threshold"]:
                onset = r["t"] + ser["period"]
                break
        out["lead_time_s"] = None if onset is None else onset - pub
        out["lead_time_status"] = "NO_ONSET" if onset is None else ("POSTED_AFTER_ONSET" if onset <= pub else "POSTED_BEFORE_ONSET")
        liq_pre = pre_rows[0].get("liq")
        out["liquidity"] = {"pre": liq_pre, "entry": en["liq"]}
    else:
        out["pre_move"], out["lead_time_s"], out["lead_time_status"] = None, None, "NO_PRE_WINDOW_DATA"
        out["liquidity"] = {"pre": None, "entry": en["liq"]}
    lag = None
    for r in ser["rows"]:
        if r["t"] < en["candle_t"] or r["t"] > t0 + max(pol["horizons_s"]) or r["t"] + ser["period"] > as_of:
            continue
        if d * (r["c"] / en["price"] - 1) >= pol["onset_threshold"]:
            lag = r["t"] + ser["period"] - pub
            break
    out["move_lag_s"] = lag
    prim = out["horizons"].get(str(pol["primary_horizon_s"]), {})
    if prim.get("status") == "OK":
        ex = prim["exit"]
        out["liquidity"]["exit"] = ex.get("liq")
        if out["liquidity"]["pre"]:
            out["liquidity"]["entry_vs_pre"] = r10(en["liq"] / out["liquidity"]["pre"]) if en["liq"] else None
        if ex.get("liq") and en["liq"]:
            out["liquidity"]["exit_vs_entry"] = r10(ex["liq"] / en["liq"])
    out["author_trades"] = _author_context(call, doc.get("author_trades") or [], pol)
    out["flags"] += out["author_trades"]["flags"]
    if d < 0:
        out["flags"].append("SHORT_NOT_EXECUTABLE_ON_SPOT")
    out["status"] = "EVALUATED" if any(h["status"] == "OK" for h in out["horizons"].values()) else "UNEVALUABLE"
    if out["status"] == "UNEVALUABLE":
        out["reasons"] = sorted({h["reason"] for h in out["horizons"].values()})
    return out


# ---------- aggregation ----------

def _count(items):
    d = {}
    for i in items:
        d[i] = d.get(i, 0) + 1
    return dict(sorted(d.items()))


def _summarise(sid, src, calls, pol):
    mine = [c for c in calls if c["source_id"] == sid]
    eligible = [c for c in mine if c["eligible"]]
    ph = str(pol["primary_horizon_s"])
    res = {"source_id": sid, "label": src.get("label"), "context_not_in_formula": src.get("context"),
           "counts": {"calls_supplied": len(mine), "ineligible_by_reason": _count(r for c in mine if not c["eligible"] for r in c["reasons"][:1]),
                      "eligible_independent": len(eligible), "evaluated_any_horizon": sum(1 for c in eligible if c["status"] == "EVALUATED"),
                      "unevaluable_by_reason": _count(r for c in eligible if c["status"] == "UNEVALUABLE" for r in c["reasons"][:1])}}
    horizons = {}
    for h in pol["horizons_s"]:
        k = str(h)
        rows = [(c, c["horizons"].get(k)) for c in eligible if c["status"] == "EVALUATED"]
        ok = [(c, r) for c, r in rows if r and r["status"] == "OK"]
        rel = [(c, r) for c, r in ok if r.get("relative") is not None]
        nets = [r["net"] for _c, r in ok]
        rels = [r["relative"] for _c, r in rel]
        hz = {"horizon_s": h, "primary": h == pol["primary_horizon_s"], "n_eligible": len(eligible), "n_evaluated": len(ok), "n_with_baseline": len(rel),
              "coverage": r10(len(ok) / len(eligible)) if eligible else None,
              "not_evaluable_by_reason": _count((r or {}).get("reason", "NO_DATA") for _c, r in rows if not r or r["status"] != "OK"),
              "median_net_return": r10(median(nets)) if nets else None, "median_relative_return": r10(median(rels)) if rels else None,
              "median_baseline_return": r10(median([r["baseline"]["median"] for _c, r in rel])) if rel else None}
        ci = median_ci(rels) if len(rels) >= pol["ci_min_n"] else None
        hz["median_relative_ci95"] = None if ci is None else [r10(ci[0]), r10(ci[1])]
        hz["ci_note"] = None if ci is not None else (f"no interval: {len(rels)} values, needs {pol['ci_min_n']}" if len(rels) < pol["ci_min_n"] else "too few values for 95%")
        beats = sum(1 for x in rels if x > 0)
        hz["beat_baseline_rate"] = r10(beats / len(rels)) if rels else None
        w = wilson(beats, len(rels))
        hz["beat_baseline_ci95"] = None if w is None else [r10(w[0]), r10(w[1])]
        hz["fail_to_beat_baseline"] = len(rels) - beats
        fp = sum(1 for x in nets if x <= 0)
        hz["false_positives"] = fp                                   # evaluated calls with a net signed return of zero or less
        hz["false_positive_rate"] = r10(fp / len(nets)) if nets else None
        horizons[k] = hz
    res["horizons"] = horizons
    leads = [c["lead_time_s"] for c in eligible if c["status"] == "EVALUATED" and c.get("lead_time_s") is not None]
    res["lead_time"] = {"n_with_onset": len(leads), "n_no_onset": sum(1 for c in eligible if c.get("lead_time_status") == "NO_ONSET"),
                        "n_no_pre_window": sum(1 for c in eligible if c.get("lead_time_status") == "NO_PRE_WINDOW_DATA"),
                        "n_posted_after_onset": sum(1 for x in leads if x <= 0),
                        "quantiles_s": None if not leads else {"p25": r10(quantile(leads, .25)), "median": r10(quantile(leads, .5)), "p75": r10(quantile(leads, .75))},
                        "note": "lead time = end of the first candle that moved the call's way by the onset threshold from the pre-window start, minus publication; negative means the move had already happened"}
    paths = [c["horizons"][ph]["path"] for c in eligible if c["status"] == "EVALUATED" and c["horizons"].get(ph, {}).get("path", {}).get("status") == "OK"]
    res["excursion"] = {"n": len(paths), "median_mfe": r10(median([p["mfe"] for p in paths])) if paths else None,
                        "median_mae": r10(median([p["mae"] for p in paths])) if paths else None}
    res["flags"] = {"late_promotion_calls": sum(1 for c in eligible if "LATE_PROMOTION" in c["flags"]),
                    "undisclosed_prior_buy": sum(1 for c in eligible if "UNDISCLOSED_PRIOR_BUY" in c["flags"]),
                    "sold_after_promoting": sum(1 for c in eligible if "SOLD_AFTER_PROMOTING" in c["flags"])}
    # selection completeness: what the collector enumerated for this source vs what was supplied
    uni = src.get("universe_count")
    res["selection"] = {"universe_count": uni, "universe_basis": src.get("universe_basis"),
                        "completeness": r10(min(1.0, len(mine) / uni)) if isinstance(uni, int) and uni > 0 else None}
    res["score"] = _score(res, [c for c in eligible if c["status"] == "EVALUATED" and c["horizons"].get(ph, {}).get("relative") is not None], pol)
    return res


def _score(res, rel_calls, pol):
    ph = str(pol["primary_horizon_s"])
    hz = res["horizons"][ph]
    n = hz["n_with_baseline"]
    toks = _count(c["token"]["contract"] for c in rel_calls)
    top_share = max(toks.values()) / n if n else None
    cov = hz["coverage"]
    comp = res["selection"]["completeness"]
    reasons = []
    out = {"primary_horizon_s": pol["primary_horizon_s"], "n_independent_with_baseline": n, "distinct_tokens": len(toks), "top_token_share": r10(top_share),
           "rules_version": RULES_VERSION, "score": None, "score_point": None, "status": "DECLINED", "tier": "UNVERIFIED"}
    if res["counts"]["eligible_independent"] == 0:
        reasons.append("no eligible calls")
    if n < pol["min_calls_preliminary"]:
        reasons.append(f"{n} independent calls with a matched baseline at the primary horizon; at least {pol['min_calls_preliminary']} are needed to publish a score")
    if cov is not None and cov < pol["min_coverage_preliminary"] and n >= pol["min_calls_preliminary"]:
        reasons.append(f"price coverage {cov:.2f} of eligible calls at the primary horizon is below {pol['min_coverage_preliminary']}")
    if comp is not None and comp < pol["min_completeness_preliminary"]:
        reasons.append(f"only {comp:.2f} of the posts enumerated for this source were supplied, below {pol['min_completeness_preliminary']}; the sample may be picked")
    if reasons:
        out["reasons"] = reasons
        return out
    rels = [c["horizons"][ph]["relative"] for c in rel_calls]
    m = median(rels)
    w = n / (n + pol["shrink_k"])
    edge = w * m
    ci = hz["median_relative_ci95"]
    # headline score is conservative: the end of the 95% interval nearest zero (zero when the interval spans it), with the same shrinkage.
    # The point estimate is kept beside it. n >= min_calls_preliminary >= ci_min_n in every default policy, so the interval normally exists.
    near = m if ci is None else (0.0 if ci[0] <= 0 <= ci[1] else (ci[0] if ci[0] > 0 else ci[1]))
    f = lambda e: int(round(50 + 50 * math.tanh(e / pol["edge_scale"])))
    out.update(median_relative_return=r10(m), shrinkage={"n": n, "k": pol["shrink_k"], "weight": r10(w)}, edge_point=r10(edge), edge_conservative=r10(w * near),
               edge_scale=pol["edge_scale"], score=f(w * near), score_point=f(edge), status="SCORED", tier="PRELIMINARY")
    out["scale"] = ("50 means no demonstrated edge over matched tokens. Above 50: the low end of the 95% interval of the median relative return beat them, after shrinkage "
                    "for sample size. Below 50: it did worse. The point estimate is shown as score_point. Not a probability and not a ranking of skill.")
    # validated checks
    miss = []
    if n < pol["min_calls_validated"]:
        miss.append(f"{n} independent calls, validation needs {pol['min_calls_validated']}")
    if len(toks) < pol["min_distinct_tokens_validated"]:
        miss.append(f"{len(toks)} distinct tokens, validation needs {pol['min_distinct_tokens_validated']}")
    if cov is None or cov < pol["min_coverage_validated"]:
        miss.append(f"coverage {cov} below {pol['min_coverage_validated']}")
    if comp is None:
        miss.append("the number of posts the collector enumerated for this source is unknown, so selection cannot be ruled out")
    elif comp < pol["min_completeness_validated"]:
        miss.append(f"selection completeness {comp:.2f} below {pol['min_completeness_validated']}")
    if top_share is not None and top_share > pol["max_top_token_share_validated"]:
        miss.append(f"one token makes {top_share:.2f} of the calls")
    if ci is None:
        miss.append("no confidence interval at this sample size")
    elif ci[0] <= 0 <= ci[1]:
        miss.append("the 95% interval of the median relative return includes zero: the result cannot be told apart from no edge")
    ordered = sorted(rel_calls, key=lambda c: (c["published_at"], c["call_id"]))
    half = len(ordered) // 2
    h1, h2 = [c["horizons"][ph]["relative"] for c in ordered[:half]], [c["horizons"][ph]["relative"] for c in ordered[half:]]
    if min(len(h1), len(h2)) < pol["min_half_n"]:
        miss.append(f"chronological halves have {len(h1)} and {len(h2)} calls, the split-sample check needs {pol['min_half_n']} each")
    else:
        s = lambda x: (x > 0) - (x < 0)
        if not (s(median(h1)) == s(median(h2)) == s(m) and s(m) != 0):
            miss.append("the first and second half of the calls disagree in sign")
    out["split_sample"] = {"first_half_median": r10(median(h1)) if h1 else None, "second_half_median": r10(median(h2)) if h2 else None, "n": [len(h1), len(h2)]}
    if miss:
        out["not_validated_because"] = miss
    else:
        out["tier"] = "VALIDATED"
    return out


def rank(result):
    """Rank only scored sources. Declined sources are listed with reasons; with nobody scored the ranking is empty and says so."""
    scored = [s for s in result["sources"].values() if s["score"]["status"] == "SCORED"]
    order = {"VALIDATED": 0, "PRELIMINARY": 1}
    scored.sort(key=lambda s: (order[s["score"]["tier"]], -s["score"]["score"], -s["score"]["score_point"], s["source_id"]))
    declined = [{"source_id": s["source_id"], "reasons": s["score"].get("reasons", [])} for s in result["sources"].values() if s["score"]["status"] != "SCORED"]
    return {"ranked": [{"source_id": s["source_id"], "tier": s["score"]["tier"], "score": s["score"]["score"], "score_point": s["score"]["score_point"],
                        "n": s["score"]["n_independent_with_baseline"]} for s in scored],
            "declined": sorted(declined, key=lambda x: x["source_id"]),
            "statement": ("No source has enough clean evidence to rank. Declining is the correct output." if not scored else
                          "Ranked by tier first (validated above preliminary), then score. A preliminary score is a lead to check, not a finding.")}


# ---------- entry point ----------

def evaluate(doc: dict, policy: dict | None = None) -> dict:
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise ValueError(f"document schema must be {SCHEMA}")
    pol = dict(DEFAULT_POLICY)
    for k, v in (policy or {}).items():
        if k not in DEFAULT_POLICY:
            raise ValueError(f"unknown policy key {k!r}")
        pol[k] = v
    if pol["primary_horizon_s"] not in pol["horizons_s"]:
        raise ValueError("primary horizon must be one of the horizons")
    if pol["entry_price_rule"] not in ("OPEN", "CANDLE_ADVERSE"):
        raise ValueError("entry_price_rule must be OPEN or CANDLE_ADVERSE")
    as_of = doc.get("as_of")
    if not _num(as_of):
        raise ValueError("as_of is required: it is the last moment of data the run may use")
    series, rejected = prep_series(doc)
    calls, reasons = _eligibility(doc, pol, series)
    banned = {_tkey(c["token"]) for c in calls if (c.get("token") or {}).get("chain") and c["token"].get("contract")}
    results = [_evaluate_call(c, reasons[c["call_id"]], series, pol, as_of, doc, banned) for c in calls]
    srcs = dict(doc.get("sources") or {})
    for c in calls:
        srcs.setdefault(c.get("source_id"), {})
    sources = {sid: _summarise(sid, srcs[sid], results, pol) for sid in sorted(srcs, key=str)}
    res = {"engine_version": ENGINE_VERSION, "rules_version": RULES_VERSION, "label": doc.get("label"), "is_fixture": bool(doc.get("is_fixture")),
           "usable_as_evidence": not doc.get("is_fixture"), "as_of": as_of, "policy": pol, "policy_sha256": sha(pol), "selection_rules": SELECTION_RULES,
           "series_rejected": rejected, "series_used": sorted([{"chain": k[0], "contract": k[1], "source": v["source"], "candles": len(v["rows"]),
                                                              "delisted_at": v["delisted_at"]} for k, v in series.items()], key=lambda x: (x["chain"], x["contract"])),
           "calls": results, "sources": sources,
           "separation": {"wallet_profits_in_formula": False, "source_popularity_in_formula": False, "claims_from_model_text_only_set_direction": True,
                          "note": "Phase 10 wallet performance is a separate measurement. Attributed author trades appear only as context flags."}}
    res["ranking"] = rank(res)
    res["input_sha256"] = sha({"doc": doc, "policy": pol, "engine": ENGINE_VERSION, "rules": RULES_VERSION})
    return res


def analyze(doc: dict, policy: dict | None = None) -> dict:
    """Evaluate twice and compare hashes; a mismatch means the engine is not deterministic and the result is refused."""
    a, b = evaluate(doc, policy), evaluate(doc, policy)
    ha, hb = sha(a), sha(b)
    if ha != hb:
        raise RuntimeError("alpha evaluation is not deterministic; result refused")
    a["result_sha256"] = ha
    return a


# ---------- plain-English report ----------

def _pct(x):
    return "n/a" if x is None else f"{x * 100:.1f}%"


def report(res: dict) -> str:
    L = [f"Information Alpha ({res['engine_version']}, {res['rules_version']})  label: {res['label']}"]
    if res["is_fixture"]:
        L.append("INVENTED FIXTURE DATA: this is a demonstration of the calculation, not evidence about any real source.")
    L.append(f"as of {res['as_of']}; delay {res['policy']['delay_s']}s; size ${res['policy']['trade_size_usd']:.0f}; primary horizon {res['policy']['primary_horizon_s'] // 3600}h; "
             f"policy {res['policy_sha256'][:12]}")
    if res["series_rejected"]:
        L.append("rejected price series: " + "; ".join(f"{r['contract']} {r['reason']}" for r in res["series_rejected"]))
    for sid, s in res["sources"].items():
        sc, ph = s["score"], s["horizons"][str(res["policy"]["primary_horizon_s"])]
        L += ["", f"Source {sid}: {s['counts']['calls_supplied']} calls supplied, {s['counts']['eligible_independent']} eligible and independent, "
              f"{ph['n_evaluated']} evaluated, {ph['n_with_baseline']} with a matched baseline at the primary horizon."]
        if s["counts"]["ineligible_by_reason"]:
            L.append("  ineligible: " + ", ".join(f"{k} {v}" for k, v in s["counts"]["ineligible_by_reason"].items()))
        if s["counts"]["unevaluable_by_reason"]:
            L.append("  no usable price data: " + ", ".join(f"{k} {v}" for k, v in s["counts"]["unevaluable_by_reason"].items()))
        for k, h in s["horizons"].items():
            L.append(f"  {int(k) // 3600:>3}h  n={h['n_evaluated']:<3} median net {_pct(h['median_net_return']):>8}  baseline {_pct(h['median_baseline_return']):>8}  "
                     f"relative {_pct(h['median_relative_return']):>8}  ci95 {h['median_relative_ci95'] and [_pct(x) for x in h['median_relative_ci95']] or 'none'}  "
                     f"beat {h['beat_baseline_rate'] if h['beat_baseline_rate'] is None else round(h['beat_baseline_rate'], 2)}  false positives {h['false_positives']}")
        lt = s["lead_time"]
        L.append(f"  lead time: {lt['n_with_onset']} with an onset, {lt['n_no_onset']} none, {lt['n_posted_after_onset']} posted after the move; "
                 f"quantiles {lt['quantiles_s']}")
        if sc["status"] == "SCORED":
            L.append(f"  SCORE {sc['score']} ({sc['tier']}), point estimate {sc['score_point']}, shrinkage weight {sc['shrinkage']['weight']:.2f}. {sc['scale']}")
            for m in sc.get("not_validated_because", []):
                L.append(f"    not validated: {m}")
        else:
            L.append("  NO SCORE (declined): " + " | ".join(sc["reasons"]))
    L += ["", res["ranking"]["statement"]]
    return "\n".join(L)
