"""Phase 13 skeptic: G7 convergence check of the numpy Platt fit (independent of the phase's oracle probe).

    python -B p13_g7_platt_convergence.py CLONE OUT.json

For each recorded calibration set (calibration/CALIBRATION_SETS.csv) and two synthetic sets:
  1. the lab's numpy Platt (code under test);
  2. scikit-learn's exact Platt objective (smoothed targets, same start) through scipy L-BFGS-B with scikit-learn's own options
     (gtol 1e-6, ftol 64 eps), which reproduces `_sigmoid_calibration`, and again with gtol 1e-13 / ftol 0 / maxiter 10000;
  3. scipy trust-exact with the analytic Hessian, gtol 1e-14;
  4. an independent Newton solve in 60-digit decimal arithmetic (damped, my own code), taken as ground truth.
Reports parameter differences and gradient norms. No network.
"""
from __future__ import annotations

import csv
import json
import sys
from decimal import Decimal, getcontext
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

getcontext().prec = 60


def targets(y):
    n1, n0 = float(np.sum(y > 0)), float(np.sum(y <= 0))
    return np.where(y > 0, (n1 + 1) / (n1 + 2), 1 / (n0 + 2)), n0, n1


def loss_grad(ab, s, t):
    f = ab[0] * s + ab[1]
    # p = 1/(1+exp(f)); loss = sum -t log p - (1-t) log(1-p)
    lp = -np.logaddexp(0, f)
    l1p = -np.logaddexp(0, -f)
    loss = -np.sum(t * lp + (1 - t) * l1p)
    p = np.exp(lp)
    r = t - p                       # d loss / d f = t - p ... sign: dL/df = p_neg... computed below
    g = np.array([np.sum(r * s), np.sum(r)])
    return loss, g


def hess(ab, s, t):
    f = ab[0] * s + ab[1]
    p = 1 / (1 + np.exp(f))
    w = p * (1 - p)
    return np.array([[np.sum(w * s * s), np.sum(w * s)], [np.sum(w * s), np.sum(w)]])


def dec_newton(s, t, a0, b0):
    S = [Decimal(repr(float(x))) for x in s]
    T = [Decimal(repr(float(x))) for x in t]
    a, b = Decimal(repr(a0)), Decimal(repr(b0))
    one = Decimal(1)

    def L(a, b):
        tot = Decimal(0)
        for si, ti in zip(S, T):
            f = a * si + b
            # log(1+e^f)
            lpos = (one + f.exp()).ln() if f < 0 else f + (one + (-f).exp()).ln()
            lneg = lpos - f                      # log(1+e^-f)
            tot += ti * lpos + (one - ti) * lneg
        return tot

    for it in range(200):
        ga = gb = haa = hab = hbb = Decimal(0)
        for si, ti in zip(S, T):
            f = a * si + b
            p = one / (one + f.exp())
            r = ti - p
            w = p * (one - p)
            ga += r * si; gb += r
            haa += w * si * si; hab += w * si; hbb += w
        det = haa * hbb - hab * hab
        da = (hbb * ga - hab * gb) / det
        db = (-hab * ga + haa * gb) / det
        step = one
        L0 = L(a, b)
        while L(a - step * da, b - step * db) > L0 and step > Decimal("1e-30"):
            step /= 2
        a, b = a - step * da, b - step * db
        if max(abs(ga), abs(gb)) < Decimal("1e-40"):
            break
    return float(a), float(b), float(max(abs(ga), abs(gb))), it


def main():
    clone, outp = Path(sys.argv[1]), Path(sys.argv[2])
    sys.path.insert(0, str(clone))
    from memelab.predictive import stats as K
    sets = {}
    with open(clone / "audits/predictive-intelligence/phase_13/calibration/CALIBRATION_SETS.csv") as f:
        for r in csv.DictReader(f):
            sets.setdefault(r["target_short"], []).append((float(r["raw_b2"]), int(r["y"])))
    data = {k: (np.array([a for a, _ in v]), np.array([b for _, b in v], float)) for k, v in sets.items()}
    rng = np.random.default_rng(7)
    for name, n, rate in (("syn_n30_rare", 30, 0.1), ("syn_n500", 500, 0.25)):
        y = (rng.random(n) < rate).astype(float)
        y[0] = 1.0
        s = np.clip(0.2 + 0.3 * y + rng.normal(0, 0.12, n), 0.001, 0.999)
        data[name] = (s, y)
    out = {}
    for name, (s, y) in data.items():
        if not 0 < y.sum() < y.size:
            continue
        t, n0, n1 = targets(y)
        x0 = np.array([0.0, np.log((n0 + 1) / (n1 + 1))])
        ours = K.Platt().fit(s, y)
        sk_like = minimize(lambda ab: loss_grad(ab, s, t), x0, method="L-BFGS-B", jac=True,
                           options={"gtol": 1e-6, "ftol": 64 * np.finfo(float).eps})
        sk_tight = minimize(lambda ab: loss_grad(ab, s, t), x0, method="L-BFGS-B", jac=True,
                            options={"gtol": 1e-13, "ftol": 0.0, "maxiter": 10000, "maxcor": 20})
        tex = minimize(lambda ab: loss_grad(ab, s, t), x0, method="trust-exact", jac=True, hess=lambda ab: hess(ab, s, t),
                       options={"gtol": 1e-14})
        da, db, dg, dit = dec_newton(s, t, float(x0[0]), float(x0[1]))
        truth = np.array([da, db])

        def rec(ab):
            ab = np.asarray(ab, float)
            return {"a": float(ab[0]), "b": float(ab[1]), "max_abs_diff_to_decimal_truth": float(np.max(np.abs(ab - truth))),
                    "grad_inf": float(np.max(np.abs(loss_grad(ab, s, t)[1])))}
        row = {"n": int(y.size), "k": int(y.sum()), "decimal_truth": {"a": da, "b": db, "grad_inf": dg, "iterations": dit},
               "numpy_platt_lab": rec([ours.a_, ours.b_]),
               "lbfgs_sklearn_options": {**rec(sk_like.x), "nit": int(sk_like.nit), "message": str(sk_like.message)},
               "lbfgs_tight": {**rec(sk_tight.x), "nit": int(sk_tight.nit), "message": str(sk_tight.message)},
               "trust_exact": {**rec(tex.x), "nit": int(tex.nit)}}
        row["lab_vs_sklearn_options_max_abs_diff"] = float(np.max(np.abs(np.array([ours.a_, ours.b_]) - sk_like.x)))
        row["lab_vs_lbfgs_tight_max_abs_diff"] = float(np.max(np.abs(np.array([ours.a_, ours.b_]) - sk_tight.x)))
        out[name] = row
    try:
        from sklearn.calibration import _sigmoid_calibration
        import sklearn
        for name, (s, y) in data.items():
            if name in out:
                a, b = _sigmoid_calibration(s, y)
                out[name]["sklearn_sigmoid_calibration"] = {"version": sklearn.__version__, "a": float(a), "b": float(b),
                                                           "equals_lbfgs_sklearn_options_within": float(max(abs(a - out[name]["lbfgs_sklearn_options"]["a"]), abs(b - out[name]["lbfgs_sklearn_options"]["b"])))}
    except ImportError:
        pass
    outp.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    for k, v in out.items():
        print(k, "n", v["n"], "lab-truth", f"{v['numpy_platt_lab']['max_abs_diff_to_decimal_truth']:.2e}",
              "skopts-truth", f"{v['lbfgs_sklearn_options']['max_abs_diff_to_decimal_truth']:.2e}",
              "tight-truth", f"{v['lbfgs_tight']['max_abs_diff_to_decimal_truth']:.2e}",
              "trustexact-truth", f"{v['trust_exact']['max_abs_diff_to_decimal_truth']:.2e}",
              "lab-vs-tight", f"{v['lab_vs_lbfgs_tight_max_abs_diff']:.2e}",
              "sk-grad", f"{v['lbfgs_sklearn_options']['grad_inf']:.1e}", "lab-grad", f"{v['numpy_platt_lab']['grad_inf']:.1e}",
              "sklearn_fn_eq", v.get("sklearn_sigmoid_calibration", {}).get("equals_lbfgs_sklearn_options_within"))


if __name__ == "__main__":
    main()
