"""Skeptic Phase 15: independent A_WARN recompute from the raw label table (not labels.training_labels) and the committed
coding file. Standard library only. Usage: python -I p15_awarn_recompute.py REPO DEV_STORE"""
import csv, sqlite3, sys, json
from datetime import datetime, timezone
repo, store = sys.argv[1], sys.argv[2]
P15 = f"{repo}/audits/predictive-intelligence/phase_15/behavioral"
LONG = {"T1_24h": "price_path_target_before_invalidation_24h", "T1b_6h": "price_path_target_before_invalidation_6h",
        "T2_24h": "price_path_severe_drawdown_or_halt_24h"}
def ts(s): return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
con = sqlite3.connect(f"file:{store}?mode=ro", uri=True)
warn = {}
for r in csv.DictReader(open(f"{P15}/SCENARIO_CODING.csv")):
    if r["set"] == "DEVELOPMENT":
        warn[(r["decision_key"], r["target"])] = r["warning"]
oos = list(csv.DictReader(open(f"{P15}/E1_OOS_ROWS.csv")))
out = {}
for short, target in LONG.items():
    labs = [dict(zip(("k", "t", "m", "y"), row)) for row in con.execute(
        "SELECT decision_key, decision_time, label_matures_at, label FROM predictive_labels WHERE target=? AND split='DEVELOPMENT' "
        "AND state='LABELED' AND eligibility='ELIGIBLE' AND censored=0 AND thinned_by IS NULL", (target,))]
    rows = [r for r in oos if r["target_short"] == short]
    se_a = se_b0 = 0.0; maxdiff = 0.0; n = 0
    for r in rows:
        cut = ts(r["cutoff_utc"])
        train = [l for l in labs if float(l["t"]) < cut and float(l["m"]) <= cut]
        N = len(train); K = sum(int(l["y"]) for l in train)
        if N < 100 or K < 20 or N - K < 20:
            continue                                       # frozen training gate: abstain
        b0 = K / N
        cells = {}
        for l in train:
            w = warn[(l["k"], target)]
            c = cells.setdefault(w, [0, 0]); c[0] += 1; c[1] += int(l["y"])
        w = warn[(r["decision_key"], target)]
        p = (cells[w][1] + 20 * b0) / (cells[w][0] + 20) if w in cells else b0
        y = int(r["y"])
        maxdiff = max(maxdiff, abs(p - float(r["A_WARN"])), abs(b0 - float(r["B0"])))
        se_a += (p - y) ** 2; se_b0 += (b0 - y) ** 2; n += 1
    out[short] = {"rows": len(rows), "scored": n, "brier_A_WARN": se_a / n, "brier_B0": se_b0 / n,
                  "bss_vs_B0": 1 - se_a / se_b0, "max_abs_diff_vs_committed_columns": maxdiff}
print(json.dumps(out, indent=1))
