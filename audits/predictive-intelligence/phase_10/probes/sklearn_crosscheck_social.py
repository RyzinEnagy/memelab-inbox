"""Phase 10 oracle cross-check (research venv only; the lab never imports scikit-learn, PI-D-031, PI-D-032).

The frozen oracle of PI-D-053: scikit-learn LogisticRegression(solver="newton-cholesky", C = 1, intercept unpenalised) against
the numpy Newton logistic, coefficient tolerance 1e-9, on every fitted logistic design `run_social.py --npz` wrote (fold cards
and the holdout-start cards), plus `stats.Prep` against SimpleImputer(median, add_indicator) and StandardScaler. Seeded synthetic
designs of the same shape are added, so the comparison exists even if no real design passes the training gate. lbfgs is shown
beside it with its gradient norm, for information only.

    /home/claude/pi_research/venvs/p04_bundle/bin/python -B sklearn_crosscheck_social.py ARRAYS.npz OUT.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import sklearn  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from memelab.predictive import stats as K  # noqa: E402

TOL = 1e-9


def prep_compare(X, Z):
    keep = [j for j in range(X.shape[1]) if np.unique(X[np.isfinite(X[:, j]), j]).size >= 2]
    pipe = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler()).fit(X[:, keep])
    Zs = pipe.transform(X[:, keep])
    return {"shape_equal": list(Zs.shape) == list(Z.shape),
            "max_abs_design_diff": float(np.max(np.abs(Zs - Z))) if Zs.shape == Z.shape else None}


def logit_compare(Z, y, coef=None):
    nc = LogisticRegression(C=1.0, solver="newton-cholesky", tol=1e-12, max_iter=100000).fit(Z, y)
    skn = np.r_[nc.intercept_, nc.coef_.ravel()]
    lb = LogisticRegression(C=1.0, solver="lbfgs", tol=1e-12, max_iter=100000).fit(Z, y)
    skl = np.r_[lb.intercept_, lb.coef_.ravel()]
    if coef is None:
        m = K.Logistic(C=1.0).fit(Z, y)
        coef = np.r_[m.intercept_, m.coef_]
    A = np.hstack([np.ones((len(y), 1)), Z])
    grad = A.T @ (K.sigmoid(A @ skl) - y) + np.r_[0.0, skl[1:]]
    d = float(np.max(np.abs(skn - coef)))
    return {"rows": int(len(y)), "columns": int(Z.shape[1]), "positives": int(y.sum()),
            "max_abs_coef_diff_newton_cholesky": d, "within_1e-9": d <= TOL,
            "max_abs_coef_diff_lbfgs_info_only": float(np.max(np.abs(skl - coef))), "lbfgs_gradient_max_abs": float(np.max(np.abs(grad)))}


def main(npz_path: str, out: str) -> int:
    real = []
    if npz_path != "-" and Path(npz_path).exists():
        d = np.load(npz_path)
        tags = sorted({k.rsplit("_", 1)[0] for k in d.files})
        for t in tags:
            X, y, Z, coef = d[t + "_X"], d[t + "_y"], d[t + "_Z"], d[t + "_coef"]
            real.append({"design": t, **logit_compare(Z, y, coef), "prep": prep_compare(X, Z)})
    syn = []
    rng = np.random.default_rng(20261025)
    for n, p in ((120, 12), (200, 16), (400, 18)):
        X = rng.normal(size=(n, p))
        X[rng.random(size=X.shape) < 0.05] = np.nan
        prep = K.Prep().fit(X)
        Z = prep.transform(X)
        y = (rng.random(n) < K.sigmoid(Z[:, 0] - 1.0)).astype(float)
        syn.append({"design": f"synthetic_{n}x{p}", **logit_compare(Z, y), "prep": prep_compare(X, Z)})
    allr = real + syn
    rep = {"sklearn_version": sklearn.__version__, "tolerance": TOL, "oracle": "newton-cholesky (PI-D-053)",
           "real_designs": real, "synthetic_designs": syn,
           "max_coef_diff_real": max((r["max_abs_coef_diff_newton_cholesky"] for r in real), default=None),
           "max_coef_diff_all": max(r["max_abs_coef_diff_newton_cholesky"] for r in allr),
           "max_prep_diff_all": max(r["prep"]["max_abs_design_diff"] for r in allr if r["prep"]["max_abs_design_diff"] is not None),
           "all_within_tolerance": all(r["within_1e-9"] for r in allr) and all(r["prep"]["shape_equal"] for r in allr)}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rep[k] for k in ("max_coef_diff_real", "max_coef_diff_all", "max_prep_diff_all", "all_within_tolerance")}
                     | {"real_designs": len(real)}))
    return 0 if rep["all_within_tolerance"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
