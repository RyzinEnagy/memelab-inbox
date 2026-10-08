"""LAUNCHPAD_ANALYTICS + COMPARABLE_LAUNCH_ANALYSIS from the launch cohort.

The cohort is every launch the system has seen (sample_basis 'newest' = drawn from newest-launch lists, close to unbiased) plus
graduated samples (sample_basis 'graduated' = survivorship-biased, reported separately and never mixed into rates).
Outcomes come from re-reading cohort tokens later (24h / 7d / 30d market cap, peak, graduation). Distributions report n, median and
quartiles; with too few observations the result is INSUFFICIENT HISTORY rather than a number.
"""
from __future__ import annotations

import json
import statistics
from typing import Any

from .. import db

MIN_N = 20
ALIVE_USD = 20_000       # a launch counts as surviving at a horizon if its market cap is at least this
RUG_FRACTION = 0.1       # cap below 10% of peak with peak >= $100k counts toward the collapse rate


def _q(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    if len(xs) < 4:
        return {"n": len(xs), "median": statistics.median(xs)}
    q = statistics.quantiles(xs, n=4)
    return {"n": len(xs), "p25": q[0], "median": q[1], "p75": q[2]}


def launchpad_stats(con, t: float, persist: bool = True) -> dict[str, dict]:
    out = {}
    for pr in con.execute("SELECT platform, chain FROM launch_cohort WHERE sample_basis='newest' GROUP BY platform, chain"):
        rows = [dict(r) for r in con.execute("SELECT * FROM launch_cohort WHERE platform=? AND sample_basis='newest' AND created_at < ?", (pr["platform"], t - 24 * 3600))]
        n = len(rows)
        if n == 0:
            continue
        ath = [r["ath_usd"] or r["mcap_usd"] for r in rows]
        grad = sum(1 for r in rows if r["graduated"]) / n
        r100k = sum(1 for a in ath if (a or 0) >= 100_000) / n
        r1m = sum(1 for a in ath if (a or 0) >= 1_000_000) / n
        s24 = [r for r in rows if r["mcap_24h"] is not None]
        s7 = [r for r in rows if r["mcap_7d"] is not None]
        surv24 = (sum(1 for r in s24 if r["mcap_24h"] >= ALIVE_USD) / len(s24)) if s24 else None
        surv7 = (sum(1 for r in s7 if r["mcap_7d"] >= ALIVE_USD) / len(s7)) if s7 else None
        dd = [((r["mcap_usd"] or 0) / r["ath_usd"] - 1) * 100 for r in rows if r["ath_usd"]]
        big = [r for r in rows if (r["ath_usd"] or 0) >= 100_000]
        collapse = (sum(1 for r in big if (r["mcap_usd"] or 0) < RUG_FRACTION * r["ath_usd"]) / len(big)) if big else None
        parts = [(0.25, min(grad / 0.05, 1.0)), (0.25, min(r100k / 0.05, 1.0)), (0.2, surv24), (0.15, surv7), (0.15, (1 - collapse) if collapse is not None else None)]
        known = [(w, v) for w, v in parts if v is not None]
        score = round(100 * sum(w * v for w, v in known) / sum(w for w, _ in parts), 1) if known else None
        rec = {"platform": pr["platform"], "chain": pr["chain"], "n": n, "graduation_rate": grad, "median_ath_usd": statistics.median([a for a in ath if a is not None]) if any(a is not None for a in ath) else None,
               "reach_100k_rate": r100k, "reach_1m_rate": r1m, "survival_24h": surv24, "survival_7d": surv7, "median_drawdown_pct": statistics.median(dd) if dd else None,
               "rug_flag_rate": collapse, "quality_score": score if n >= MIN_N else None,
               "basis": f"newest-launch cohort, launches older than 24h, n={n}" + ("" if n >= MIN_N else f" (below {MIN_N}: INSUFFICIENT HISTORY, no score)")}
        out[pr["platform"]] = rec
        if persist:
            db.insert(con, "launchpad_stats", {"observed_at": t, **rec})
    return out


def comparables(con, c: dict, t: float) -> dict[str, Any]:
    """Launches like this one: same chain and launchpad, similar starting/current valuation bucket, older than 24h."""
    pad, chain = c.get("launchpad"), c.get("chain")
    mc = (c.get("obs") or {}).get("mcap_usd")
    if not pad:
        return {"verdict": "NO COMPARABLE BASE", "n": 0, "facts": [], "unknowns": ["launchpad unknown: no comparable cohort"]}
    rows = [dict(r) for r in con.execute("SELECT * FROM launch_cohort WHERE platform=? AND chain=? AND sample_basis='newest' AND created_at < ? AND mint != ?",
                                         (pad, chain, t - 24 * 3600, c.get("contract") or ""))]
    # valuation bucket: within 0.3x..3x of this token's current cap at a similar point in life, approximated by the cohort's peak band
    if mc:
        sim = [r for r in rows if r["ath_usd"] and 0.3 * mc <= r["ath_usd"] <= 30 * mc]
    else:
        sim = rows
    n = len(sim)
    facts, unknowns = [], []
    res: dict[str, Any] = {"n": n, "cohort_n": len(rows)}
    if n < 10:
        res["verdict"] = "INSUFFICIENT HISTORY"
        unknowns.append(f"only {n} comparable launch(es) with 24h+ history on {pad} (need 10); the cohort grows with every run")
        res.update({"facts": facts, "unknowns": unknowns})
        return res
    peak_mult = [r["ath_usd"] / r["start_mcap_usd"] for r in sim if r["ath_usd"] and r["start_mcap_usd"]]
    d24 = [r["mcap_24h"] for r in sim if r["mcap_24h"] is not None]
    d7 = [r["mcap_7d"] for r in sim if r["mcap_7d"] is not None]
    dd = [((r["mcap_usd"] or 0) / r["ath_usd"] - 1) * 100 for r in sim if r["ath_usd"]]
    res.update({"peak_multiple": _q(peak_mult), "mcap_24h": _q(d24), "mcap_7d": _q(d7), "drawdown_from_peak_pct": _q(dd),
                "graduation_rate": sum(1 for r in sim if r["graduated"]) / n, "survival_24h": (sum(1 for x in d24 if x >= ALIVE_USD) / len(d24)) if d24 else None,
                "survival_7d": (sum(1 for x in d7 if x >= ALIVE_USD) / len(d7)) if d7 else None})
    facts.append(f"{n} comparable {pad} launches (peak within 0.3x..30x of this cap, older than 24h): graduation {res['graduation_rate']:.0%}"
                 + (f", alive at 24h {res['survival_24h']:.0%}" if res["survival_24h"] is not None else "") + (f", alive at 7d {res['survival_7d']:.0%}" if res["survival_7d"] is not None else ""))
    if res["drawdown_from_peak_pct"]:
        facts.append(f"median drawdown from peak {res['drawdown_from_peak_pct']['median']:.0f}%")
    if not peak_mult:
        unknowns.append("opening valuation for comparables (start cap is recorded only for launches first seen within 30 minutes of creation)")
    if not d7:
        unknowns.append("7-day outcomes (cohort not yet old enough)")
    surv = res["survival_7d"] if res["survival_7d"] is not None else res["survival_24h"]
    res["verdict"] = "FAVORABLE" if (surv or 0) >= 0.4 and res["graduation_rate"] >= 0.2 else "POOR" if (surv is not None and surv < 0.1) else "NEUTRAL"
    res.update({"facts": facts, "unknowns": unknowns})
    return res


def followup_mints(con, t: float, limit: int = 150) -> list[str]:
    """Cohort tokens due for an outcome reading (24h, 7d, 30d marks), oldest due first."""
    due = []
    for r in con.execute("SELECT mint, created_at, last_checked, mcap_24h, mcap_7d, mcap_30d, platform FROM launch_cohort WHERE platform='pump.fun' ORDER BY created_at"):
        age = t - (r["created_at"] or t)
        if (r["mcap_24h"] is None and 20 * 3600 <= age <= 48 * 3600) or (r["mcap_7d"] is None and 6 * 86400 <= age <= 10 * 86400) or (r["mcap_30d"] is None and 27 * 86400 <= age <= 40 * 86400):
            due.append(r["mint"])
    return due[:limit]
