"""Phase 04 calibration-layer checks (offline; run inside `unshare -n` through measure.py).

    python calibration_check.py oracle   # in the ip200/venn-abers venv: numpy Venn-Abers prototype versus the reference package
    python calibration_check.py bundle   # in the bundle venv: numpy logistic and Platt versus scikit-learn; MAPIE offline only

The challenge file is synthetic: these are definition and equivalence checks, not calibration evidence for memecoins.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bakeoff as B  # noqa: E402
import core_numpy as K  # noqa: E402


def challenge_scores():
    d = B.load("challenge")
    t, m = d["t"], d["m"]
    q1, q2 = np.quantile(t, [0.6, 0.8])
    tr = np.where((t < q1) & (m <= q1))[0]
    cal = np.where((t >= q1) & (t < q2) & (m <= q2))[0]
    te = np.where(t >= q2)[0]
    prep = K.Prep().fit(d["X"][tr])
    lr = K.Logistic().fit(prep.transform(d["X"][tr]), d["y"][tr])
    s = lambda idx: lr.decision_function(prep.transform(d["X"][idx]))  # noqa: E731
    return d, tr, cal, te, prep, lr, s


def oracle() -> dict:
    from venn_abers import VennAbers
    import venn_abers
    d, tr, cal, te, prep, lr, s = challenge_scores()
    sig = lambda z: 1 / (1 + np.exp(-z))  # noqa: E731
    probes = {}
    rng = np.random.default_rng(20261024)
    cases = {
        "challenge_holdout": (s(cal), d["y"][cal], s(te)),
        "ties_in_calibration": (np.round(s(cal), 1), d["y"][cal], np.round(s(te), 1)),
        "outside_calibration_range": (s(cal), d["y"][cal], np.r_[s(cal).min() - 3, s(cal).min() - 0.5, s(cal).max() + 0.5, s(cal).max() + 3]),
        "random_small": (rng.normal(size=40), (rng.random(40) < 0.3).astype(float), rng.normal(size=200)),
        # skeptic m7: raw scores above about 37 saturate the sigmoid, so the oracle sees ties the raw scores do not have
        "large_scores": (rng.uniform(20, 60, size=60), (rng.random(60) < 0.4).astype(float), rng.uniform(15, 65, size=100)),
    }
    for name, (cs, cy, ts) in cases.items():
        # both implementations get the same inputs (the probabilities the oracle needs); Venn-Abers depends only on the order
        p0, p1, p = K.venn_abers(sig(cs), cy, sig(ts))
        va = VennAbers().fit(np.column_stack([1 - sig(cs), sig(cs)]), cy.astype(int))
        pp, p01 = va.predict_proba(np.column_stack([1 - sig(ts), sig(ts)]))
        probes[name] = {"n_cal": int(len(cs)), "n_test": int(len(ts)), "max_abs_diff_p0": float(np.max(np.abs(p0 - p01[:, 0]))),
                        "max_abs_diff_p1": float(np.max(np.abs(p1 - p01[:, 1]))), "max_abs_diff_p": float(np.max(np.abs(p - pp[:, 1]))),
                        "p0_le_p1_all": bool(np.all(p0 <= p1 + 1e-15)), "p_inside_0_1": bool(np.all((p >= 0) & (p <= 1)))}
    worst = max(max(v["max_abs_diff_p0"], v["max_abs_diff_p1"], v["max_abs_diff_p"]) for v in probes.values())
    return {"mode": "oracle", "venn_abers_version": getattr(venn_abers, "__version__", "1.5.4 (no __version__)"),
            "probes": probes, "max_abs_diff_any": worst, "pass_1e-9": worst <= 1e-9}


def bundle() -> dict:
    import sklearn
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.frozen import FrozenEstimator
    from sklearn.linear_model import LogisticRegression
    d, tr, cal, te, prep, lr, s = challenge_scores()
    Ztr, Zcal, Zte = (prep.transform(d["X"][i]) for i in (tr, cal, te))
    sk = LogisticRegression(C=1.0, tol=1e-10, max_iter=10000).fit(Ztr, d["y"][tr])
    coef_diff = float(np.max(np.abs(np.r_[sk.intercept_, sk.coef_[0]] - np.r_[lr.intercept_, lr.coef_])))
    prob_diff = float(np.max(np.abs(sk.predict_proba(Zte)[:, 1] - lr.predict_proba1(Zte))))
    pl = K.Platt().fit(s(cal), d["y"][cal])
    cc = CalibratedClassifierCV(FrozenEstimator(sk), method="sigmoid").fit(Zcal, d["y"][cal])
    platt_diff = float(np.max(np.abs(cc.predict_proba(Zte)[:, 1] - pl.predict(s(te)))))
    # MAPIE offline only: risk controller for an alert threshold and calibration tests; never its Venn-Abers port and never
    # a fitted Pipeline in prefit mode (Phase 03 MA-1, MA-4). banned_scan.py refuses those calls in every prototype.
    import mapie
    from mapie.metrics.calibration import spiegelhalter_p_value
    from mapie.risk_control import BinaryClassificationController
    p_cal = pl.predict(s(cal))
    pf = lambda X: np.column_stack([1 - pl.predict(lr.decision_function(X)), pl.predict(lr.decision_function(X))])  # noqa: E731
    ctl = {}
    for tgt in (0.10, 0.20):
        bcc = BinaryClassificationController(predict_function=pf, risk="precision", target_level=tgt, confidence_level=0.9)
        bcc.calibrate(Zcal, d["y"][cal].astype(int))
        nvalid = 0 if bcc.valid_predict_params is None else int(len(np.atleast_1d(bcc.valid_predict_params)))
        ctl[f"precision_ge_{tgt}"] = {"valid_thresholds": nvalid,
                                      "best": None if bcc.best_predict_param is None or nvalid == 0 else round(float(np.atleast_1d(bcc.best_predict_param)[0]), 4)}
    sp = float(spiegelhalter_p_value(d["y"][te].astype(int), pl.predict(s(te))))
    # skeptic m7: constant scores; only a s + b is identified. numpy returns the exact optimum (the mean smoothed target)
    yc = d["y"][cal]
    const = np.full(len(cal), 0.25)
    from sklearn.calibration import _sigmoid_calibration
    a_sk, b_sk = _sigmoid_calibration(const, yc)
    n1, n0 = float(yc.sum()), float(len(yc) - yc.sum())
    tbar = (n1 * (n1 + 1) / (n1 + 2) + n0 / (n0 + 2)) / len(yc)
    p_np = float(K.Platt().fit(const, yc).predict(np.array([0.25]))[0])
    p_sk = float(1 / (1 + np.exp(a_sk * 0.25 + b_sk)))
    return {"mode": "bundle", "sklearn": sklearn.__version__, "mapie": mapie.__version__,
            "logistic_numpy_vs_sklearn": {"max_abs_coef_diff": coef_diff, "max_abs_prob_diff": prob_diff},
            "platt_numpy_vs_frozen_sigmoid": {"max_abs_prob_diff": platt_diff},
            "platt_constant_scores": {"numpy": round(p_np, 10), "sklearn": round(p_sk, 10), "exact_optimum_mean_smoothed_target": round(tbar, 10),
                                      "numpy_minus_optimum": p_np - tbar, "sklearn_minus_optimum": p_sk - tbar},
            "mapie_controller": ctl, "mapie_spiegelhalter_p_holdout": round(sp, 6), "calibration_rows": int(len(cal)),
            "calibration_positives": int(d["y"][cal].sum()), "mean_p_cal": round(float(p_cal.mean()), 6)}


if __name__ == "__main__":
    out = oracle() if sys.argv[1] == "oracle" else bundle()
    print(json.dumps(out, sort_keys=True, indent=1))
