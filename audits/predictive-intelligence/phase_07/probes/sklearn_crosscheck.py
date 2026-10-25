"""Phase 07 oracle cross-check (research venv only; the lab never imports scikit-learn, PI-D-031, PI-D-032).

Reads the arrays `run_baselines.py --npz` wrote (B2 fold designs after the training-only preprocessing, the numpy coefficients,
and the pooled out-of-sample labels and numbers) and compares: scikit-learn 1.9.1 LogisticRegression (lbfgs, C = 1, intercept
unpenalised) with the numpy Newton fit on every real fold, and roc_auc_score, average_precision_score, brier_score_loss and
log_loss with memelab.predictive.stats on the pooled numbers.

    /home/claude/pi_research/venvs/p04_bundle/bin/python -B sklearn_crosscheck.py ARRAYS.npz OUT.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import sklearn  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score  # noqa: E402

from memelab.predictive import stats as K  # noqa: E402


def main(npz_path: str, out: str) -> int:
    d = np.load(npz_path)
    folds, metrics = [], []
    for key in sorted(k for k in d.files if k.endswith("_Z")):
        base = key[:-2]
        Z, y, coef = d[key], d[base + "_y"], d[base + "_coef"]
        lr = LogisticRegression(C=1.0, solver="lbfgs", tol=1e-12, max_iter=100000).fit(Z, y)
        sk = np.r_[lr.intercept_, lr.coef_.ravel()]
        p_np = K.sigmoid(Z @ coef[1:] + coef[0])
        p_sk = lr.predict_proba(Z)[:, 1]
        folds.append({"fold": base, "rows": int(len(y)), "max_abs_coef_diff": float(np.max(np.abs(sk - coef))),
                      "max_abs_prob_diff": float(np.max(np.abs(p_np - p_sk)))})
    for key in sorted(k for k in d.files if k.endswith("_p")):
        base = key[:-2]
        y, p = d[base + "_y"], d[key]
        row = {"set": base, "rows": int(len(y)), "positives": int(y.sum()),
               "brier_diff": abs(K.brier(y, p) - brier_score_loss(y, p)),
               "log_loss_diff": abs(K.log_loss(y, p, 1e-6) - log_loss(y, np.clip(p, 1e-6, 1 - 1e-6), labels=[0, 1]))}
        if 0 < y.sum() < len(y):
            row["auc_diff"] = abs(K.roc_auc(y, p) - roc_auc_score(y, p))
            row["ap_diff"] = abs(K.average_precision(y, p) - average_precision_score(y, p))
        metrics.append(row)
    # tie handling: rounded numbers create ties
    rng = np.random.default_rng(3)
    ties = []
    for _ in range(50):
        y = (rng.uniform(size=60) < 0.3).astype(float)
        if y.sum() in (0, 60):
            continue
        p = np.round(rng.uniform(size=60), 1)
        ties.append(max(abs(K.roc_auc(y, p) - roc_auc_score(y, p)), abs(K.average_precision(y, p) - average_precision_score(y, p))))
    res = {"sklearn": sklearn.__version__, "numpy": np.__version__, "folds": folds, "metrics": metrics,
           "max_coef_diff": max((f["max_abs_coef_diff"] for f in folds), default=None),
           "max_prob_diff": max((f["max_abs_prob_diff"] for f in folds), default=None),
           "max_metric_diff": max((max(v for k, v in m.items() if k.endswith("_diff")) for m in metrics), default=None),
           "tie_cases": len(ties), "max_tie_diff": max(ties) if ties else None}
    res["pass"] = (res["max_coef_diff"] is not None and res["max_coef_diff"] < 1e-6 and res["max_metric_diff"] < 1e-12
                   and res["max_tie_diff"] < 1e-12)
    Path(out).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: res[k] for k in ("max_coef_diff", "max_prob_diff", "max_metric_diff", "max_tie_diff", "pass")}))
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
