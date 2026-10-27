"""Phase 20 (G12): does the out-of-sample picture survive a changed seed, token grouping, start and end selection, route, regime
and the static baselines? Descriptive, own numpy code, on committed scored rows only:

  - the spent retrospective holdout: phase_12/validation/HOLDOUT_SCORED.csv (opened once in Phase 12, PI-D-065; any use here is
    POST_OPENING and can only make statements more conservative);
  - the prospective window: phase_19/monitoring/PROSPECTIVE_SCORED.csv (PROVISIONAL_PENDING_REVISION_REREAD, PI-D-106).

    python -B oos_sensitivity.py OUTJSON

For each target: the Brier skill of B2 (and of B1, B3, B3F, B4) against B0 on the rows where both have a number, with day and mint
bootstrap intervals (2,000 replicates, seeds 1 to 5, the wider interval governs, as ACCEPTANCE bootstrap), and the same after one
decision per mint, without the first or the last decision day, PIT_RECORDED rows only, and by route. Nothing here is a verdict,
a claim or a selection; it says whether any reading would turn "not distinguishable" into a lower bound above 0.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

AUD = Path(__file__).resolve().parents[2]
REPS = 2000
SEEDS = (1, 2, 3, 4, 5)
MODELS = ("P07_B2", "P07_B1", "P07_B3", "P07_B3F", "P07_B4")


def fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def bss(y, p, r) -> float:
    d = float(np.sum((r - y) ** 2))
    return float("nan") if d == 0 else 1.0 - float(np.sum((p - y) ** 2)) / d


def boot(y, p, r, groups, seed) -> list:
    rng = np.random.default_rng(seed)
    g = np.array(groups)
    u = np.unique(g)
    idx = {k: np.where(g == k)[0] for k in u}
    vals = []
    for _ in range(REPS):
        pick = rng.choice(u, size=len(u), replace=True)
        ii = np.concatenate([idx[k] for k in pick])
        v = bss(y[ii], p[ii], r[ii])
        if math.isfinite(v):
            vals.append(v)
    if len(vals) < 100:
        return [None, None]
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]


def describe(rows, model) -> dict:
    rs = [r for r in rows if fnum(r[model]) is not None and fnum(r["P07_B0"]) is not None and r["y"] in ("0", "1")]
    if not rs:
        return {"n": 0}
    y = np.array([int(r["y"]) for r in rs], float)
    p = np.array([fnum(r[model]) for r in rs])
    b0 = np.array([fnum(r["P07_B0"]) for r in rs])
    out = {"n": len(rs), "positives": int(y.sum()), "days": len({r["day"] for r in rs}), "mints": len({r["mint"] for r in rs}),
           "bss": bss(y, p, b0)}
    ivs = {}
    for s in SEEDS:
        d = boot(y, p, b0, [r["day"] for r in rs], s) if out["days"] >= 2 else [None, None]
        m = boot(y, p, b0, [r["mint"] for r in rs], s)
        wd = (d[1] - d[0]) if None not in d else math.inf
        wm = (m[1] - m[0]) if None not in m else math.inf
        ivs[s] = {"day": d, "mint": m, "governing": "day" if wd >= wm else "mint"}
    out["intervals"] = ivs
    gov = [ivs[s][ivs[s]["governing"]] for s in SEEDS]
    out["governing_lower_bounds"] = [g[0] for g in gov]
    out["any_lower_bound_above_0"] = any(g[0] is not None and g[0] > 0 for g in gov)
    out["below_frozen_minimum"] = out["n"] < 50 or min(out["positives"], out["n"] - out["positives"]) < 10 or out["days"] < 5
    return out


def variants(rows) -> dict:
    by_t = {}
    for r in rows:
        by_t.setdefault(r["day"], []).append(r)
    days = sorted(by_t)
    first_per_mint, seen = [], set()
    for r in sorted(rows, key=lambda r: (r["decision_time_utc"], r["decision_key"])):
        if r["mint"] not in seen:
            seen.add(r["mint"])
            first_per_mint.append(r)
    v = {"all": rows, "one_decision_per_mint": first_per_mint,
         "without_first_day": [r for r in rows if r["day"] != days[0]] if len(days) > 1 else [],
         "without_last_day": [r for r in rows if r["day"] != days[-1]] if len(days) > 1 else [],
         "pit_recorded_only": [r for r in rows if r["route"] == "PIT_RECORDED"]}
    for route in sorted({r["route"] for r in rows}):
        v[f"route={route}"] = [r for r in rows if r["route"] == route]
    return v


def main(outjson: Path) -> int:
    res = {"note": "POST_OPENING_DESCRIPTIVE (holdout) and PROVISIONAL_PENDING_REVISION_REREAD (prospective); not a verdict or a claim",
           "datasets": {}}
    claims = []
    for name, path in (("retrospective_holdout_spent", AUD / "phase_12/validation/HOLDOUT_SCORED.csv"),
                       ("prospective_phase19", AUD / "phase_19/monitoring/PROSPECTIVE_SCORED.csv")):
        rows = list(csv.DictReader(open(path)))
        ds = {}
        for t in sorted({r["target_short"] for r in rows}):
            tr = [r for r in rows if r["target_short"] == t]
            ds[t] = {}
            for vn, vr in variants(tr).items():
                ds[t][vn] = {m: describe(vr, m) for m in (MODELS if vn == "all" else ("P07_B2",))}
                for m, d in ds[t][vn].items():
                    if d.get("any_lower_bound_above_0"):
                        claims.append({"dataset": name, "target": t, "variant": vn, "model": m, "n": d["n"], "positives": d["positives"],
                                       "days": d["days"], "below_frozen_minimum": d["below_frozen_minimum"]})
        res["datasets"][name] = ds
    res["readings_with_a_lower_bound_above_0"] = claims
    res["any_reading_meets_the_frozen_minimums_and_a_positive_lower_bound"] = any(not c["below_frozen_minimum"] for c in claims)
    outjson.parent.mkdir(parents=True, exist_ok=True)
    outjson.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"readings_with_positive_lower_bound": len(claims),
                      "of_which_meet_frozen_minimums": sum(not c["below_frozen_minimum"] for c in claims),
                      "headline_bss_B2": {n: {t: round(v["all"]["P07_B2"].get("bss", float("nan")), 3) for t, v in d.items()}
                                          for n, d in res["datasets"].items()}}))
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
