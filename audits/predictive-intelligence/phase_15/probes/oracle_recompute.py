"""Phase 15 independent recomputation: standard library only, no lab code, no label store. From the committed coding and scored
files it recomputes the E2 and E3 warning counts, precision, prevalence, lift, recall, coverage and Wilson intervals, the
permutation p values with its own shuffle (Python's random, 20,000 replicates, so they agree only within Monte Carlo error), the
E1 Brier numbers of A_WARN, B0 and B2, and checks that every scored row's warning equals the blind coding file.

    python -B oracle_recompute.py OUT.json
"""
from __future__ import annotations

import csv
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

P = Path(__file__).resolve().parents[1]
REPO = P.parents[2]
Z = 1.959963984540054


def wilson(k, n):
    if n == 0:
        return [0.0, 1.0]
    ph = k / n
    den = 1 + Z * Z / n
    c = (ph + Z * Z / (2 * n)) / den
    h = Z * math.sqrt(ph * (1 - ph) / n + Z * Z / (4 * n * n)) / den
    return [max(0.0, c - h), min(1.0, c + h)]


def perm(rows, reps=20000, seed=7):
    rnd = random.Random(seed)
    obs = sum(1 for r in rows if r["w"] and r["y"])
    by = defaultdict(list)
    for i, r in enumerate(rows):
        by[r["day"]].append(i)
    up = down = 0
    for _ in range(reps):
        h = 0
        for idx in by.values():
            ws = [rows[i]["w"] for i in idx]
            rnd.shuffle(ws)
            h += sum(1 for i, w in zip(idx, ws) if w and rows[i]["y"])
        up += h >= obs
        down += h <= obs
    return (1 + up) / (reps + 1), (1 + down) / (reps + 1)


def metrics(rows):
    n = len(rows)
    k = sum(r["y"] for r in rows)
    nw = sum(r["w"] for r in rows)
    hits = sum(1 for r in rows if r["w"] and r["y"])
    out = {"n": n, "positives": k, "warned": nw, "hits": hits, "prevalence": k / n if n else None,
           "precision": hits / nw if nw else None, "recall": hits / k if k else None, "coverage": nw / n if n else None,
           "precision_wilson": wilson(hits, nw) if nw else None, "prevalence_wilson": wilson(k, n)}
    out["lift"] = out["precision"] - out["prevalence"] if nw else None
    if 0 < nw < n:
        out["p_up"], out["p_down"] = perm(rows)
    return out


def main(dst):
    res = json.loads((P / "behavioral/INCREMENTAL_VALUE_RESULTS.json").read_text())
    coding = {(r["set"], r["decision_key"], r["target_short"]): r["warning"] for r in csv.DictReader(open(P / "behavioral/SCENARIO_CODING.csv"))}
    rep = {"E2": {}, "E3": {}, "E1": {}, "warning_mismatches": 0, "differences": []}
    by = defaultdict(list)
    for r in csv.DictReader(open(P / "behavioral/E2_SCORED_ROWS.csv")):
        if coding[("DEVELOPMENT", r["decision_key"], r["target_short"])] != r["warning"]:
            rep["warning_mismatches"] += 1
        by[r["target_short"]].append({"w": r["warning"] == "EVENT", "y": int(r["y"]), "day": r["day"]})
    hs = defaultdict(list)
    for r in csv.DictReader(open(REPO / "audits/predictive-intelligence/phase_12/validation/HOLDOUT_SCORED.csv")):
        w = coding[("HOLDOUT_WINDOW", r["decision_key"], r["target_short"])]
        hs[r["target_short"]].append({"w": w == "EVENT", "y": int(r["y"]), "day": r["day"]})

    def cmp(tag, ours, theirs):
        for key in ("n", "positives", "warned", "hits", "prevalence", "precision", "recall", "coverage", "lift"):
            tk = {"n": "n_scored"}.get(key, key)
            a, b = ours.get(key), theirs.get(tk)
            if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-12):
                rep["differences"].append([tag, key, a, b])
        for key in ("precision_wilson", "prevalence_wilson"):
            a, b = ours.get(key), theirs.get(key)
            if (a is None) != (b is None) or (a is not None and max(abs(x - y) for x, y in zip(a, b)) > 1e-12):
                rep["differences"].append([tag, key, a, b])
        if "p_up" in ours:
            pm = theirs.get("permutation") or {}
            for key in ("p_up", "p_down"):
                if abs(ours[key] - pm[key]) > 0.02:
                    rep["differences"].append([tag, key, ours[key], pm[key]])
    for t, rows in sorted(by.items()):
        m = metrics(rows)
        rep["E2"][t] = m
        cmp(f"E2:{t}", m, res["E2"][t])
    for t, rows in sorted(hs.items()):
        m = metrics(rows)
        rep["E3"][t] = m
        cmp(f"E3:{t}", m, res["E3_POST_OPENING"][t]["warning_metrics"])
    e1 = defaultdict(list)
    for r in csv.DictReader(open(P / "behavioral/E1_OOS_ROWS.csv")):
        e1[r["target_short"]].append(r)
    for t, rows in sorted(e1.items()):
        use = [r for r in rows if r["A_WARN"] and r["B0"]]
        br = {m: sum((float(r[m]) - int(r["y"])) ** 2 for r in use) / len(use) for m in ("A_WARN", "B0")}
        bss = 1 - br["A_WARN"] / br["B0"]
        u2 = [r for r in rows if r["A_WARN"] and r["B2"]]
        b2 = sum((float(r["B2"]) - int(r["y"])) ** 2 for r in u2) / len(u2)
        a2 = sum((float(r["A_WARN"]) - int(r["y"])) ** 2 for r in u2) / len(u2)
        rep["E1"][t] = {"n": len(use), "brier_A_WARN": br["A_WARN"], "brier_B0": br["B0"], "bss_vs_B0": bss, "brier_B2": b2}
        ours = res["E1"][t]["A_WARN_vs_B0"]
        # the CSV holds 6 decimals, so agreement is to about 1e-6
        for a, b, key in ((br["A_WARN"], ours["brier"], "brier"), (br["B0"], ours["brier_ref"], "brier_ref"), (bss, ours["bss"], "bss"),
                          (a2, res["E1"][t]["A_WARN_vs_B2"]["brier"], "brier_vs_B2_rows"), (b2, res["E1"][t]["A_WARN_vs_B2"]["brier_ref"], "brier_B2")):
            if abs(a - b) > 2e-5:
                rep["differences"].append([f"E1:{t}", key, a, b])
    rep["ok"] = not rep["differences"] and rep["warning_mismatches"] == 0
    Path(dst).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"ok": rep["ok"], "differences": rep["differences"], "warning_mismatches": rep["warning_mismatches"]}))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
