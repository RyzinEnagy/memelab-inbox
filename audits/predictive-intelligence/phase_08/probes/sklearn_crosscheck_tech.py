"""Phase 08 oracle cross-check (research venv only; the lab never imports scikit-learn, PI-D-031, PI-D-032).

1. Real fold designs written by `run_technical.py --npz` (only folds where a technical model passed the training gate): the
   numpy Newton logistic against scikit-learn LogisticRegression (lbfgs, C = 1, intercept unpenalised) on the preprocessed
   design; the numpy stumps against GradientBoostingClassifier(max_depth=1, n_estimators=100, learning_rate=0.1,
   min_samples_leaf=10, subsample=1.0) on the raw design (its trees cast X to float32; thresholds are compared at float32).
2. Seeded synthetic designs of the same shape (15 technical columns, 120 to 400 rows), so the oracle comparison exists even when
   no real fold passes the gate.

    /home/claude/pi_research/venvs/p04_bundle/bin/python -B sklearn_crosscheck_tech.py ARRAYS.npz OUT.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import sklearn  # noqa: E402
from sklearn.ensemble import GradientBoostingClassifier  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

from memelab.predictive import stats as K  # noqa: E402
from memelab.predictive import technical as T  # noqa: E402


def gbc(X, y):
    return GradientBoostingClassifier(loss="log_loss", n_estimators=T.STUMP_ROUNDS, learning_rate=T.STUMP_LR, max_depth=1,
                                      min_samples_leaf=T.STUMP_MIN_LEAF, subsample=1.0, random_state=0).fit(X, y)


def stump_compare(X, y, p_np=None):
    m = T.Stumps().fit(X, y)
    p_mine = m.predict_proba1(X)
    sk = gbc(X, y)
    p_sk = sk.predict_proba(X)[:, 1]
    feats_sk = [int(e[0].tree_.feature[0]) for e in sk.estimators_]
    thr_sk = [float(e[0].tree_.threshold[0]) for e in sk.estimators_]
    # scikit-learn trees cast X to float32 and take the midpoint there: thresholds agree to float32 precision (1e-6 relative)
    same_split = sum(1 for (j, t, *_), fj, ft in zip(m.trees, feats_sk, thr_sk) if j == fj and abs(t - ft) <= 1e-6 * max(1.0, abs(t)))
    out = {"rows": int(len(y)), "positives": int(y.sum()), "rounds_numpy": len(m.trees), "rounds_sklearn": len(sk.estimators_),
           "same_split_rounds": same_split, "max_abs_prob_diff": float(np.max(np.abs(p_mine - p_sk)))}
    if p_np is not None:
        out["max_abs_diff_to_stored_card"] = float(np.max(np.abs(p_mine - p_np)))
    return out


def logit_compare(Z, y, coef=None):
    lr = LogisticRegression(C=1.0, solver="lbfgs", tol=1e-12, max_iter=100000).fit(Z, y)
    sk = np.r_[lr.intercept_, lr.coef_.ravel()]
    if coef is None:
        m = K.Logistic(C=1.0).fit(Z, y)
        coef = np.r_[m.intercept_, m.coef_]
    return {"rows": int(len(y)), "max_abs_coef_diff": float(np.max(np.abs(sk - coef))),
            "max_abs_prob_diff": float(np.max(np.abs(K.sigmoid(Z @ coef[1:] + coef[0]) - lr.predict_proba(Z)[:, 1])))}


def main(npz_path: str, out: str) -> int:
    real = {"logistic": [], "stumps": []}
    if npz_path != "-" and Path(npz_path).exists():
        d = np.load(npz_path)
        for key in sorted(k for k in d.files if k.endswith("_X")):
            base = key[:-2]
            y = d[base + "_y"]
            if base + "_Z" in d.files:
                real["logistic"].append({"fold": base, **logit_compare(d[base + "_Z"], y, d[base + "_coef"])})
            if base + "_p" in d.files:
                real["stumps"].append({"fold": base, **stump_compare(d[key], y, d[base + "_p"])})
    synth = {"logistic": [], "stumps": []}
    for seed in range(10):
        rng = np.random.default_rng(1000 + seed)
        n = int(rng.integers(120, 401))
        X = rng.normal(size=(n, len(T.TECH)))
        X[:, 11] = (rng.uniform(size=n) < 0.1).astype(float)            # 0/1 columns like the failed-breakout and retest flags
        X[:, 12] = (rng.uniform(size=n) < 0.2).astype(float)
        z = -1.5 + 0.8 * X[:, 0] - 0.5 * X[:, 4] + 0.6 * X[:, 11]
        y = (rng.uniform(size=n) < 1 / (1 + np.exp(-z))).astype(float)
        synth["stumps"].append({"seed": 1000 + seed, **stump_compare(X, y)})
        prep = K.Prep().fit(X)
        synth["logistic"].append({"seed": 1000 + seed, **logit_compare(prep.transform(X), y)})
    allr = real["stumps"] + synth["stumps"]
    alll = real["logistic"] + synth["logistic"]
    rep = {"sklearn": sklearn.__version__, "numpy": np.__version__, "real_fold_designs": real, "synthetic_designs": synth,
           "max_stump_prob_diff": max((r["max_abs_prob_diff"] for r in allr), default=None),
           "max_logit_coef_diff": max((r["max_abs_coef_diff"] for r in alll), default=None),
           "stump_rounds_with_a_different_split": sum(r["rounds_numpy"] - r["same_split_rounds"] for r in allr),
           "thresholds": {"logistic_coef": 1e-6, "stump_prob": 1e-9}}
    rep["pass"] = (rep["max_logit_coef_diff"] is not None and rep["max_logit_coef_diff"] <= 1e-6
                   and rep["max_stump_prob_diff"] is not None and rep["max_stump_prob_diff"] <= 1e-9)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rep[k] for k in ("max_stump_prob_diff", "max_logit_coef_diff", "stump_rounds_with_a_different_split", "pass")}))
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
