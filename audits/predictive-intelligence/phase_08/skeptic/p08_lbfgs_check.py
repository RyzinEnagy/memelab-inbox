"""Phase 08 skeptic: is the 1.13e-6 lbfgs difference lbfgs's stopping point? Rebuilds the T1b fold-4 M1 design independently
(p08_independent.tech and prep_fit), compares the committed fold card's coefficients with scikit-learn lbfgs, newton-cholesky and
an own Newton iteration, and reports the penalised objective and gradient at each."""
import json, math, sys
import numpy as np
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, "/home/claude/pi_orchestration/skeptic")
import p08_independent as I

dev, fs = I.ro(sys.argv[1]), I.ro(sys.argv[2])
card = json.load(open(sys.argv[3]))["folds"][4]["cards"]["M1_T_LOGIT"]
rows = I.load(dev, fs, I.TARGETS["T1b_6h"])
cut = I.FIRST_CUT + 4 * I.DAY
tr = [r for r in rows if r["decision_time"] < cut and r["label_matures_at"] <= cut]
X = np.array([[v if v is not None else np.nan for v in (I.tech(fs, r["decision_key"])[0][n] for n in I.TECH)] for r in tr])
y = np.array([r["label"] for r in tr], float)
u = np.all(np.isfinite(X), 1)
X, y = X[u], y[u]
st = I.prep_fit(X)
Z = I.prep_tr(st, X)
def obj(b):
    z = Z @ b[1:] + b[0]
    return float(np.sum(np.logaddexp(0, z) - y * z) + 0.5 * b[1:] @ b[1:])
def grad(b):
    p = 1 / (1 + np.exp(-(Z @ b[1:] + b[0])))
    return np.r_[np.sum(p - y), Z.T @ (p - y) + b[1:]]
b = np.zeros(Z.shape[1] + 1)
for _ in range(50):                      # own Newton
    p = 1 / (1 + np.exp(-(Z @ b[1:] + b[0]))); A = np.c_[np.ones(len(y)), Z]
    Hs = A.T @ (A * (p * (1 - p))[:, None]) + np.diag(np.r_[0, np.ones(Z.shape[1])])
    b = b - np.linalg.solve(Hs, grad(b))
bc = np.r_[card["body"]["logistic"]["intercept"], card["body"]["logistic"]["coef"]]
out = {"rows": int(len(y)), "positives": int(y.sum()),
       "prep_mu_maxdiff_vs_card": float(np.max(np.abs(st["mu"] - np.array(card["body"]["prep"]["mu"])))),
       "prep_sd_maxdiff_vs_card": float(np.max(np.abs(st["sd"] - np.array(card["body"]["prep"]["sd"])))),
       "card": {"obj": obj(bc), "maxgrad": float(np.max(np.abs(grad(bc))))},
       "own_newton": {"obj": obj(b), "maxgrad": float(np.max(np.abs(grad(b)))), "coef_diff_vs_card": float(np.max(np.abs(b - bc)))}}
for solver, tol in (("lbfgs", 1e-4), ("lbfgs", 1e-12), ("newton-cholesky", 1e-12)):
    m = LogisticRegression(C=1.0, solver=solver, tol=tol, max_iter=100000).fit(Z, y)
    bs = np.r_[m.intercept_, m.coef_.ravel()]
    out[f"{solver}_tol{tol:g}"] = {"obj": obj(bs), "maxgrad": float(np.max(np.abs(grad(bs)))), "n_iter": int(m.n_iter_[0]),
                                   "coef_diff_vs_card": float(np.max(np.abs(bs - bc))), "coef_diff_vs_own_newton": float(np.max(np.abs(bs - b)))}
print(json.dumps(out, indent=1))
