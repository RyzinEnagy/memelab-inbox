"""Phase 13 skeptic: independent recomputation of the reliability / coverage table, base-rate intervals, exchangeability tests
and the chronology of the calibration sets, with my own code (numpy only; Phase 07's loader used only to read rows).

    python -B p13_independent.py CLONE OUT.json

The retrospective-holdout rows read here come from committed Phase 12 files (HOLDOUT_SCORED.csv): POST_OPENING description
only, never a fit or a claim.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

Z = 1.959963984540054


def wilson(k, n):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def my_bins(y, p, min_bin=20, max_bins=5, large_only_below=40):
    n = len(y)
    out = {"n": n, "k": int(sum(y)), "mean_pred": float(np.mean(p)), "obs": float(np.mean(y)), "wilson": wilson(int(sum(y)), n)}
    out["ok"] = out["wilson"][0] <= out["mean_pred"] <= out["wilson"][1]
    out["bins"] = []
    if n < large_only_below:
        return out
    nb = min(max_bins, n // min_bin)
    idx = sorted(range(n), key=lambda i: (p[i], i))
    base, extra = divmod(n, nb)
    start = 0
    for b in range(nb):
        m = base + (1 if b < extra else 0)
        part = idx[start:start + m]
        start += m
        k = int(sum(y[i] for i in part))
        mp = float(np.mean([p[i] for i in part]))
        lo, hi = wilson(k, m)
        out["bins"].append({"n": m, "k": k, "mean_pred": mp, "lo": lo, "hi": hi, "ok": lo <= mp <= hi})
    return out


def utc(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def chi2(codes, y, ng):
    kg = np.bincount(codes, weights=y, minlength=ng.size)
    p = y.mean()
    e1, e0 = ng * p, ng * (1 - p)
    return float(np.sum((kg - e1) ** 2 / e1 + ((ng - kg) - e0) ** 2 / e0))


def perm_test(groups, y, reps=100000, seed=99):
    g = np.asarray(groups, dtype=object)
    uniq, codes = np.unique(g, return_inverse=True)
    ng = np.bincount(codes).astype(float)
    y = np.asarray(y, float)
    obs = chi2(codes, y, ng)
    rng = np.random.default_rng(seed)
    hits = sum(chi2(codes, rng.permutation(y), ng) >= obs - 1e-12 for _ in range(reps))
    return {"stat": obs, "p": (1 + hits) / (reps + 1), "groups": int(uniq.size)}


def cluster_perm_test(groups, clusters, y, reps=20000, seed=5):
    """Permutation that moves whole mints (clusters) between days only as units: each mint keeps its rows' outcomes together
    and is assigned to a day slot with the same row count. Implemented as: permute the outcome vectors among mints with equal
    row counts (a restricted, cluster-respecting null)."""
    g = np.asarray(groups, dtype=object)
    uniq, codes = np.unique(g, return_inverse=True)
    ng = np.bincount(codes).astype(float)
    y = np.asarray(y, float)
    obs = chi2(codes, y, ng)
    rows_of = defaultdict(list)
    for i, c in enumerate(clusters):
        rows_of[c].append(i)
    by_size = defaultdict(list)
    for c, rr in rows_of.items():
        by_size[len(rr)].append(c)
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(reps):
        yy = y.copy()
        for size, cs in by_size.items():
            perm = rng.permutation(len(cs))
            for a, b in zip(cs, [cs[j] for j in perm]):
                yy[rows_of[a]] = y[rows_of[b]]
        if chi2(codes, yy, ng) >= obs - 1e-12:
            hits += 1
    return {"stat": obs, "p": (1 + hits) / (reps + 1), "mints": len(rows_of),
            "mints_with_more_than_one_row": sum(1 for r in rows_of.values() if len(r) > 1)}


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj = [0.0] * len(ps)
    run = 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


def main():
    clone, outp = Path(sys.argv[1]), Path(sys.argv[2])
    sys.path.insert(0, str(clone))
    aud = clone / "audits/predictive-intelligence"
    d13 = aud / "phase_13"
    res = {"findings": []}
    # ------------------------------------------------ 1. reliability of the dev OOS raw B2 numbers
    cs = defaultdict(list)
    with open(d13 / "calibration/CALIBRATION_SETS.csv") as f:
        for r in csv.DictReader(f):
            cs[r["target_short"]].append(r)
    table = defaultdict(dict)
    with open(d13 / "calibration/RELIABILITY_COVERAGE.csv") as f:
        for r in csv.DictReader(f):
            table[(r["target_short"], r["view"])][r["part"]] = r
    H = utc("2026-10-17T00:00:00Z") if False else None
    rel = {}
    worst = 0.0
    for s, rows in cs.items():
        y = [int(r["y"]) for r in rows]
        p = [float(r["raw_b2"]) for r in rows]
        mb = my_bins(y, p)
        t = table[(s, "DEV_OOS_RAW_B2")]
        d = [abs(mb["mean_pred"] - float(t["IN_THE_LARGE"]["mean_pred"])), abs(mb["wilson"][0] - float(t["IN_THE_LARGE"]["wilson_lo"])),
             abs(mb["wilson"][1] - float(t["IN_THE_LARGE"]["wilson_hi"]))]
        same_counts = mb["n"] == int(t["IN_THE_LARGE"]["n"]) and mb["k"] == int(t["IN_THE_LARGE"]["positives"]) and int(mb["ok"]) == int(t["IN_THE_LARGE"]["ok"])
        for i, b in enumerate(mb["bins"]):
            tb = t[f"BIN_{i}"]
            same_counts &= b["n"] == int(tb["n"]) and b["k"] == int(tb["positives"]) and int(b["ok"]) == int(tb["ok"])
            d += [abs(b["mean_pred"] - float(tb["mean_pred"])), abs(b["lo"] - float(tb["wilson_lo"])), abs(b["hi"] - float(tb["wilson_hi"]))]
        n_bins_table = sum(1 for k in t if k.startswith("BIN_"))
        same_counts &= n_bins_table == len(mb["bins"])
        worst = max(worst, max(d))
        rel[s] = {"n": mb["n"], "k": mb["k"], "mean_pred": mb["mean_pred"], "wilson": mb["wilson"], "ok": mb["ok"],
                  "bins": mb["bins"], "counts_and_flags_equal_table": bool(same_counts), "max_abs_diff_vs_table": max(d)}
    res["dev_reliability"] = rel
    # ------------------------------------------------ 2. POST_OPENING: holdout raw B2 reliability from Phase 12 committed file
    ho = defaultdict(list)
    with open(aud / "phase_12/validation/HOLDOUT_SCORED.csv") as f:
        for r in csv.DictReader(f):
            v = r.get("P07_B2", "")
            try:
                fv = float(v)
            except ValueError:
                continue
            if math.isfinite(fv):
                ho[r["target_short"]].append((int(r["y"]), fv))
    hrel = {}
    for s, pr in ho.items():
        mb = my_bins([a for a, _ in pr], [b for _, b in pr])
        t = table[(s, "HOLDOUT_RAW_B2_POST_OPENING")]
        d = [abs(mb["mean_pred"] - float(t["IN_THE_LARGE"]["mean_pred"]))] + \
            [abs(b["mean_pred"] - float(t[f"BIN_{i}"]["mean_pred"])) for i, b in enumerate(mb["bins"])]
        same = all(b["n"] == int(t[f"BIN_{i}"]["n"]) and b["k"] == int(t[f"BIN_{i}"]["positives"]) and int(b["ok"]) == int(t[f"BIN_{i}"]["ok"])
                   for i, b in enumerate(mb["bins"])) and mb["n"] == int(t["IN_THE_LARGE"]["n"]) and int(mb["ok"]) == int(t["IN_THE_LARGE"]["ok"])
        hrel[s] = {"label": "POST_OPENING_DESCRIPTION", "n": mb["n"], "k": mb["k"], "ok": mb["ok"],
                   "bins_ok": [b["ok"] for b in mb["bins"]], "equal_counts_flags": bool(same), "max_abs_diff": max(d)}
    res["holdout_reliability_post_opening"] = hrel
    # ------------------------------------------------ 3. chronology of the calibration sets and fold cards
    hstart = utc("2026-10-17T00:00:00Z")
    from memelab.predictive import contract as C
    hstart = C.parse_utc(C.ACCEPTANCE["holdout_window_utc"][0])
    chron = {}
    folds = json.loads((d13 / "calibration/FOLD_CALIBRATION_CARDS.json").read_text())
    for s, rows in cs.items():
        bad = []
        for r in rows:
            dt, mt, sc = utc(r["decision_time_utc"]), utc(r["label_matures_at_utc"]), utc(r["scored_by_cutoff_utc"])
            if not (dt < hstart and mt <= hstart and sc <= dt and r["split"] == "DEVELOPMENT"):
                bad.append(r["decision_key"][:12])
        fold_ok = {}
        for k, v in folds[s].items():
            cut = utc(v["cutoff_utc"])
            n = sum(1 for r in rows if utc(r["decision_time_utc"]) < cut and utc(r["label_matures_at_utc"]) <= cut)
            kk = sum(int(r["y"]) for r in rows if utc(r["decision_time_utc"]) < cut and utc(r["label_matures_at_utc"]) <= cut)
            fold_ok[k] = {"mine": [n, kk], "card": [v["calibration_set"]["n"], v["calibration_set"]["k"]]}
        chron[s] = {"rows": len(rows), "violations": bad, "folds": fold_ok,
                    "days": len({r["decision_time_utc"][:10] for r in rows}), "positives": sum(int(r["y"]) for r in rows)}
    res["chronology"] = chron
    # ------------------------------------------------ 4. base rates and exchangeability on all development labels at H
    spec = importlib.util.spec_from_file_location("p07", aud / "phase_07/probes/run_baselines.py")
    P7 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(P7)
    from memelab.predictive import labels as L
    dev, fs = P7.ro(P7.DEV_STORE), P7.ro(P7.FEATURE_STORE)
    frows, snaps, info = P7.load_inputs(dev, fs)
    exch_json = json.loads((d13 / "calibration/EXCHANGEABILITY.json").read_text())
    base_tab = {r["target_short"]: r for r in csv.DictReader(open(d13 / "calibration/BASE_RATE_UNCERTAINTY.csv"))}
    ex, ps = {}, []
    rng = np.random.default_rng(123)
    for t in (L.T1, L.T1B, L.T2):
        s = P7.SHORT[t]
        dev_ex, _ = P7.examples_at(dev, t, L.holdout_start(), frows, snaps, info)
        y = np.array([e.y for e in dev_ex], float)
        days = [e.day for e in dev_ex]
        routes = [e.route or "UNKNOWN" for e in dev_ex]
        mints = [e.mint for e in dev_ex]
        k, n = int(y.sum()), y.size
        wl, wh = wilson(k, n)
        # day-block bootstrap, my own RNG and loop
        ud = sorted(set(days))
        rows_of = {d: np.array([i for i, x in enumerate(days) if x == d]) for d in ud}
        bs = []
        for _ in range(20000):
            pick = rng.integers(0, len(ud), len(ud))
            idx = np.concatenate([rows_of[ud[j]] for j in pick])
            bs.append(y[idx].mean())
        dbl = (float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975)))
        pt_days = perm_test(days, y)
        pt_route = perm_test(routes, y)
        cl_days = cluster_perm_test(days, mints, y)
        # route by day crosstab: is route confounded with time?
        rd = Counter((d, r) for d, r in zip(days, routes))
        route_days = {r: sorted({d for d, rr in rd if rr == r}) for r in set(routes)}
        # day test without the first day
        first = ud[0]
        keep = [i for i, d in enumerate(days) if d != first]
        pt_days_wo_first = perm_test([days[i] for i in keep], y[keep])
        rows_first = [i for i, d in enumerate(days) if d == first]
        ex[s] = {"n": n, "k": k, "wilson": [wl, wh], "wilson_table": [float(base_tab[s]["wilson_lo"]), float(base_tab[s]["wilson_hi"])],
                 "day_block_mine": dbl, "day_block_table": [float(base_tab[s]["day_block_lo"]), float(base_tab[s]["day_block_hi"])],
                 "perm_days_mine_100k": pt_days, "perm_days_table": exch_json[s]["days"]["p"],
                 "perm_route_mine_100k": pt_route, "perm_route_table": exch_json[s]["route"]["p"],
                 "cluster_respecting_days": cl_days,
                 "days_without_first_day": pt_days_wo_first,
                 "first_day": {"day": first, "rows": len(rows_first), "positives": int(y[rows_first].sum()),
                               "distinct_mints": len({mints[i] for i in rows_first})},
                 "route_days": {r: [v[0], v[-1], len(v)] for r, v in route_days.items()},
                 "route_counts": {r: [int(sum(1 for x in routes if x == r)), int(sum(y[i] for i, x in enumerate(routes) if x == r))] for r in set(routes)}}
        ps += [pt_days["p"], pt_route["p"]]
    hp = holm(ps)
    res["exchangeability"] = ex
    res["holm_over_six_tests"] = {"raw": ps, "holm": hp, "any_survives_0_05": any(x < 0.05 for x in hp)}
    outp.write_text(json.dumps(res, indent=1, sort_keys=True, default=float) + "\n")
    print(json.dumps({"dev_rel": {s: (v["counts_and_flags_equal_table"], v["max_abs_diff_vs_table"]) for s, v in rel.items()},
                      "hold_rel": {s: (v["equal_counts_flags"], v["max_abs_diff"]) for s, v in hrel.items()},
                      "chron": {s: (v["rows"], v["positives"], v["days"], len(v["violations"]), v["folds"]) for s, v in chron.items()},
                      "holm": res["holm_over_six_tests"]}, default=float, indent=1))
    for s, v in ex.items():
        print(s, "wilson", np.round(v["wilson"], 9), np.round(v["wilson_table"], 9), "dayblock", np.round(v["day_block_mine"], 4), v["day_block_table"])
        print("   days p mine", round(v["perm_days_mine_100k"]["p"], 4), "table", round(v["perm_days_table"], 4),
              "| route p mine", round(v["perm_route_mine_100k"]["p"], 4), "table", round(v["perm_route_table"], 4),
              "| cluster-respecting days p", round(v["cluster_respecting_days"]["p"], 4), v["cluster_respecting_days"]["mints"],
              v["cluster_respecting_days"]["mints_with_more_than_one_row"],
              "| days w/o first", round(v["days_without_first_day"]["p"], 4), "| first", v["first_day"])
        print("   route_days", v["route_days"], v["route_counts"])


if __name__ == "__main__":
    main()
