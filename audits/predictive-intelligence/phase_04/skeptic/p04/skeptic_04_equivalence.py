"""Skeptic 04: numpy core (core_numpy.py) against scikit-learn and ip200/venn-abers on inputs the phase's probes did not use.
    <p04_bundle python> -I -B skeptic_04_equivalence.py PROTO_DIR logistic
    <ip200 venv python> -I -B skeptic_04_equivalence.py PROTO_DIR venn
"""
import json, sys, warnings
import numpy as np
sys.path.insert(0, sys.argv[1])
import core_numpy as K
warnings.filterwarnings("ignore")
rng = np.random.default_rng(424242)
res = {}

def cases_lr():
    n, d = 300, 5
    X = rng.normal(size=(n, d)); w = rng.normal(size=d)
    y = (rng.random(n) < 1 / (1 + np.exp(-(X @ w - 0.8)))).astype(float)
    yield "random_300x5", X, y, 1.0
    Xs = X * np.array([1e4, 1e-4, 1, 1, 1]); yield "unscaled_1e4_1e-4", Xs, y, 1.0
    Xsep = rng.normal(size=(200, 3)); ysep = (Xsep[:, 0] > 0).astype(float); yield "separable_C1", Xsep, ysep, 1.0
    yield "separable_C1e4", Xsep, ysep, 1e4
    Xd = np.hstack([X, X[:, :2]]); yield "duplicated_columns", Xd, y, 1.0
    Xw = rng.normal(size=(12, 20)); yw = np.r_[np.ones(4), np.zeros(8)]; yield "n_lt_d", Xw, yw, 1.0
    Xi = rng.normal(size=(500, 4)); yi = np.zeros(500); yi[[3, 77]] = 1; yield "two_positives_in_500", Xi, yi, 1.0
    Xt = np.repeat(rng.normal(size=(20, 3)), 15, axis=0); yt = (rng.random(300) < 0.4).astype(float); yield "tied_rows", Xt, yt, 1.0

if sys.argv[2] == "logistic":
    from sklearn.linear_model import LogisticRegression
    from sklearn.calibration import _sigmoid_calibration
    import sklearn
    res["sklearn"] = sklearn.__version__
    lr_out = {}
    for name, X, y, C in cases_lr():
        mine = K.Logistic(C=C).fit(X, y)
        sk = LogisticRegression(C=C, tol=1e-12, max_iter=100000).fit(X, y)
        skd = LogisticRegression(C=C).fit(X, y)
        Xq = rng.normal(size=(200, X.shape[1])) * X.std(axis=0) + X.mean(axis=0)
        pm, ps, pd_ = mine.predict_proba1(Xq), sk.predict_proba(Xq)[:, 1], skd.predict_proba(Xq)[:, 1]
        # objective values: lower is better
        def obj(b0, b):
            z = X @ b + b0; return float(np.sum(np.logaddexp(0, z) - y * z) + b @ b / (2 * C))
        lr_out[name] = {"max_prob_diff_vs_sklearn_tight": float(np.max(np.abs(pm - ps))),
                        "max_prob_diff_vs_sklearn_default": float(np.max(np.abs(pm - pd_))),
                        "newton_iters": mine.n_iter_, "obj_numpy": obj(mine.intercept_, mine.coef_),
                        "obj_sklearn_tight": obj(float(sk.intercept_[0]), sk.coef_[0]), "finite": bool(np.all(np.isfinite(pm)))}
    res["logistic"] = lr_out
    pl_out = {}
    s = rng.normal(size=200); ys = (rng.random(200) < 1 / (1 + np.exp(-2 * s))).astype(float)
    pcases = {"random": (s, ys), "ties": (np.round(s, 0), ys), "extreme_scale": (s * 1e3, ys),
              "separable": (s, (s > 0).astype(float)), "tiny_n5": (s[:5], np.r_[1., 0, 1, 0, 0]),
              "constant_scores": (np.zeros(50), (rng.random(50) < 0.3).astype(float))}
    for name, (sc, yy) in pcases.items():
        try:
            a, b = _sigmoid_calibration(sc, yy)
            p = K.Platt().fit(sc, yy)
            q = np.linspace(sc.min() - 1, sc.max() + 1, 101)
            pl_out[name] = {"a_np": p.a_, "b_np": p.b_, "a_sk": float(a), "b_sk": float(b),
                            "max_prob_diff": float(np.max(np.abs(p.predict(q) - 1 / (1 + np.exp(a * q + b)))))}
        except Exception as e:
            pl_out[name] = {"error": f"{type(e).__name__}: {e}"}
    res["platt"] = pl_out
    # degenerate inputs
    deg = {}
    for name, fn in {
        "logistic_nan": lambda: K.Logistic().fit(np.array([[np.nan], [1.0], [2.0]]), np.array([0., 1, 0])),
        "logistic_inf": lambda: K.Logistic().fit(np.array([[np.inf], [1.0], [2.0]]), np.array([0., 1, 0])),
        "logistic_one_class": lambda: K.Logistic().fit(np.array([[0.], [1.0], [2.0]]), np.array([1., 1, 1])),
        "logistic_labels_0_2": lambda: K.Logistic().fit(np.array([[0.], [1.0], [2.0]]), np.array([0., 2, 0])),
        "prep_all_constant_then_fit": lambda: K.Logistic().fit(K.Prep().fit(np.ones((5, 2))).transform(np.ones((5, 2))), np.array([0., 1, 0, 1, 0])),
        "prep_inf_at_predict": lambda: K.Prep().fit(np.array([[0.], [1.], [2.]])).transform(np.array([[np.inf]])).tolist(),
        "predict_nan_without_prep": lambda: K.Logistic().fit(np.array([[0.], [1.], [2.], [3.]]), np.array([0., 1, 0, 1])).predict_proba1(np.array([[np.nan]])).tolist(),
        "brier_nan": lambda: K.brier(np.array([0., 1]), np.array([np.nan, 0.5])),
        "platt_one_class": lambda: K.Platt().fit(np.array([0., 1, 2]), np.array([1., 1, 1])),
        "venn_one_class": lambda: K.venn_abers(np.array([0., 1, 2]), np.array([1., 1, 1]), np.array([0.5])),
        "venn_nan_test": lambda: K.venn_abers(np.array([0., 1, 2, 3]), np.array([1., 0, 1, 0]), np.array([np.nan])),
        "pagehinkley_nan": lambda: K.PageHinkley().update(float("nan")),
        "wilson_n0": lambda: K.wilson(0, 0),
        "holm_empty": lambda: K.holm([]),
    }.items():
        try:
            deg[name] = {"returned": str(fn())[:80]}
        except Exception as e:
            deg[name] = {"raised": f"{type(e).__name__}: {str(e)[:80]}"}
    res["degenerate"] = deg
    # determinism
    X, y = next(cases_lr())[1:3]
    a = K.Logistic().fit(X, y).predict_proba1(X).tobytes(); b = K.Logistic().fit(X, y).predict_proba1(X).tobytes()
    res["deterministic_same_process"] = a == b
else:
    from venn_abers import VennAbers
    out = {}
    def comp(name, cs, cy, ts):
        # both sides get probabilities (a monotone transform of a score is VA-invariant), so no sigmoid saturation artifact
        p0, p1, p = K.venn_abers(cs, cy, ts)
        va = VennAbers().fit(np.column_stack([1 - cs, cs]), cy.astype(int))
        pp, p01 = va.predict_proba(np.column_stack([1 - ts, ts]))
        out[name] = {"max_abs_diff": float(max(np.max(np.abs(p0 - p01[:, 0])), np.max(np.abs(p1 - p01[:, 1])), np.max(np.abs(p - pp[:, 1])))),
                     "p0_le_p1": bool(np.all(p0 <= p1 + 1e-15)), "in_0_1": bool(np.all((p >= 0) & (p <= 1)))}
    u = rng.random(300); y = (rng.random(300) < u).astype(float)
    comp("random_300", u, y, rng.random(500))
    comp("heavy_ties_10_levels", np.round(u, 1), y, np.round(rng.random(200), 1))
    comp("test_equals_calibration_points", u, y, u[:100].copy())
    comp("extreme_test_0_and_1", u, y, np.array([0.0, 1e-300, 1 - 1e-16, 1.0]))
    comp("all_calibration_scores_equal", np.full(40, 0.3), (rng.random(40) < 0.3).astype(float), np.array([0.1, 0.3, 0.9]))
    comp("two_points", np.array([0.2, 0.8]), np.array([0., 1.]), np.array([0.1, 0.5, 0.9]))
    comp("antimonotone_calibration", u, (u < 0.3).astype(float), rng.random(100))
    big = rng.random(2000); comp("n2000", big, (rng.random(2000) < big ** 2).astype(float), rng.random(300))
    # saturation artifact of the phase's probe design: raw scores > 37 are distinct for numpy, equal after sigmoid for the oracle
    sc = np.r_[rng.normal(size=60), 38.0, 40.0, 45.0, 50.0]; sy = np.r_[(rng.random(60) < 0.3).astype(float), 0., 1., 0., 1.]
    ts = np.array([39.0, 42.0, 47.0, 55.0])
    p0, p1, p = K.venn_abers(sc, sy, ts)
    sig = 1 / (1 + np.exp(-sc)); sigt = 1 / (1 + np.exp(-ts))
    pp, p01 = VennAbers().fit(np.column_stack([1 - sig, sig]), sy.astype(int)).predict_proba(np.column_stack([1 - sigt, sigt]))
    out["phase_probe_design_with_saturated_sigmoid"] = {"max_abs_diff": float(np.max(np.abs(p - pp[:, 1]))), "numpy_p": p.round(4).tolist(), "oracle_p": pp[:, 1].round(4).tolist()}
    res["venn_abers"] = out
print(json.dumps(res, indent=1))
