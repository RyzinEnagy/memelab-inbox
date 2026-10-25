"""Phase 08: why scikit-learn's lbfgs differs from the numpy Newton logistic by 1.1e-6 on the real T1b fold 4 designs (added after
the oracle cross-check, disclosed as such). Measures the gradient of the penalised objective (sum of log loss + ||w||^2 / 2 with
C = 1, intercept unpenalised) at each solution, and compares scikit-learn's exact Newton solvers. Research venv only.

    /home/claude/pi_research/venvs/p04_bundle/bin/python -B logit_solver_diagnosis.py ARRAYS.npz OUT.json
"""
import json
import sys

import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression


def main(npz, out):
    d = np.load(npz)
    rep = {"sklearn": sklearn.__version__, "folds": {}}
    for key in sorted(k for k in d.files if k.endswith("_Z")):
        base = key[:-2]
        Z, y, coef = d[key], d[base + "_y"], d[base + "_coef"]

        def grad(b):
            p = 1 / (1 + np.exp(-(Z @ b[1:] + b[0])))
            return float(np.max(np.abs(np.r_[np.sum(p - y), Z.T @ (p - y) + b[1:]])))
        r = {"rows": int(len(y)), "columns": int(Z.shape[1]), "numpy_newton_max_abs_gradient": grad(coef)}
        for solver in ("lbfgs", "newton-cholesky", "newton-cg"):
            lr = LogisticRegression(C=1.0, solver=solver, tol=1e-12, max_iter=100000).fit(Z, y)
            b = np.r_[lr.intercept_, lr.coef_.ravel()]
            r[solver] = {"max_abs_gradient": grad(b), "max_abs_coef_diff_to_numpy": float(np.max(np.abs(b - coef))),
                         "n_iter": int(lr.n_iter_[0])}
        rep["folds"][base] = r
    rep["reading"] = ("the numpy fit is at the optimum (gradient near 1e-15); lbfgs stops with a gradient near 1e-6 to 1e-5, "
                      "so its 1.1e-6 coefficient difference is lbfgs's own stopping point; the exact Newton solvers agree with numpy")
    open(out, "w").write(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({b: {s: r[s]["max_abs_coef_diff_to_numpy"] for s in ("lbfgs", "newton-cholesky", "newton-cg")} for b, r in rep["folds"].items()}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
