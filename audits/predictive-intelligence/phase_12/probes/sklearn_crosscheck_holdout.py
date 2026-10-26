"""Phase 12 oracle cross-check (research venv only; the lab never imports scikit-learn, PI-D-031, PI-D-032).

Recomputes, for every holdout metric row with a number (primary, secondary, sensitivities that use the primary rows), the Brier
score of the model and of its reference, the log loss (probabilities clipped to [1e-6, 1 - 1e-6] first, as the module does),
ROC AUC and average precision with scikit-learn from `validation/HOLDOUT_SCORED.csv`, on the rows where the model and its
reference both have a number, and compares them with `validation/HOLDOUT_METRICS.csv` (tolerance 1e-12). Reads no sealed file.

    /home/claude/pi_research/venvs/p04_bundle/bin/python -B sklearn_crosscheck_holdout.py VALIDATION_DIR OUT.json
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import sklearn
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

TOL = 1e-12
CLIP = 1e-6


def f(x):
    return float(x) if x not in ("", None) else float("nan")


def main() -> int:
    val, out = Path(sys.argv[1]), Path(sys.argv[2])
    with open(val / "HOLDOUT_SCORED.csv") as fh:
        scored = list(csv.DictReader(fh))
    with open(val / "HOLDOUT_METRICS.csv") as fh:
        metrics = list(csv.DictReader(fh))
    checked, worst, bad = 0, 0.0, []
    for m in metrics:
        if m["view"] != "PRIMARY" or not m["n_with_number"] or int(m["n_with_number"]) == 0:
            continue
        rows = [r for r in scored if r["target_short"] == m["target_short"] and math.isfinite(f(r.get(m["model"])))
                and math.isfinite(f(r.get(m["reference"])))]
        if len(rows) != int(m["n_with_number"]):
            bad.append({"row": m["model"] + " vs " + m["reference"], "target": m["target_short"], "issue": "row count"})
            continue
        y = np.array([int(r["y"]) for r in rows])
        p = np.array([f(r[m["model"]]) for r in rows])
        b = np.array([f(r[m["reference"]]) for r in rows])
        got = {"brier": brier_score_loss(y, p), "brier_ref": brier_score_loss(y, b),
               "log_loss": log_loss(y, np.clip(p, CLIP, 1 - CLIP), labels=[0, 1]),
               "log_loss_ref": log_loss(y, np.clip(b, CLIP, 1 - CLIP), labels=[0, 1])}
        if m["roc_auc"]:
            got["roc_auc"] = roc_auc_score(y, p)
            got["average_precision"] = average_precision_score(y, p)
        for k, v in got.items():
            d = abs(float(v) - f(m[k]))
            worst = max(worst, d)
            checked += 1
            if not d <= TOL:
                bad.append({"row": m["model"] + " vs " + m["reference"], "target": m["target_short"], "metric": k, "diff": d})
    rep = {"sklearn": sklearn.__version__, "values_checked": checked, "max_abs_difference": worst, "tolerance": TOL,
           "problems": bad}
    out.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rep[k] for k in ("sklearn", "values_checked", "max_abs_difference")} | {"problems": len(bad)}))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
