"""Phase 13 oracle check: the numpy calibration engine against reference implementations, in a research venv only.

    /home/claude/pi_research/venvs/p04_bundle/bin/python -B oracle_calibration.py PHASE13_DIR OUT.json      (scikit-learn, statsmodels)
    /home/claude/pi_research/venvs/ip200__venn-abers/bin/python -B oracle_calibration.py PHASE13_DIR OUT.json (ip200/venn-abers)

Runs every check whose package imports in the interpreter that runs it. Inputs: the recorded calibration sets
(calibration/CALIBRATION_SETS.csv), the descriptive fits (calibration/BELOW_GATE_DESCRIPTIVE.json), the reliability table and
synthetic fixtures. Oracles only: nothing here is imported by the lab.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from memelab.predictive import calibration as CAL  # noqa: E402
from memelab.predictive import stats as K  # noqa: E402


def sets(d: Path) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    out: dict[str, list] = {}
    with open(d / "calibration/CALIBRATION_SETS.csv") as f:
        for r in csv.DictReader(f):
            out.setdefault(r["target_short"], []).append((float(r["raw_b2"]), int(r["y"]), float(r["b0_fold"])))
    return {k: (np.array([a for a, _, _ in v]), np.array([b for _, b, _ in v], float), np.array([c for _, _, c in v])) for k, v in out.items()}


def fixtures():
    rng = np.random.default_rng(20261026)
    out = {}
    for name, n, rate in (("f300", 300, 0.3), ("f120", 120, 0.1), ("ties", 200, 0.25)):
        y = (rng.random(n) < rate).astype(float)
        s = np.clip(0.2 + 0.4 * y + rng.normal(0, 0.15, n), 0.01, 0.99)
        if name == "ties":
            s = np.round(s, 1).clip(0.01, 0.99)
        out[name] = (s, y, np.full(n, y.mean()))
    return out


def sklearn_checks(d: Path) -> dict:
    from sklearn.calibration import _sigmoid_calibration
    from sklearn.isotonic import IsotonicRegression
    from sklearn.metrics import brier_score_loss, log_loss
    import sklearn
    res = {"sklearn_version": sklearn.__version__, "platt": {}, "isotonic_in_venn_abers": {}, "scores": {}}
    data = {**sets(d), **fixtures()}
    from sklearn.linear_model import LogisticRegression

    def grad(a_, b_, s_, y_):
        n1, n0 = float(np.sum(y_ > 0)), float(np.sum(y_ <= 0))
        t_ = np.where(y_ > 0, (n1 + 1) / (n1 + 2), 1 / (n0 + 2))
        p_ = 1 / (1 + np.exp(a_ * s_ + b_))
        return float(max(abs(np.sum((t_ - p_) * s_)), abs(np.sum(t_ - p_)))), t_

    for name, (s, y, ref) in data.items():
        if 0 < y.sum() < y.size:
            ours = K.Platt().fit(s, y)
            a, b = _sigmoid_calibration(s, y)
            g_ours, t = grad(ours.a_, ours.b_, s, y)
            g_sk, _ = grad(float(a), float(b), s, y)
            # PI-D-053 reference for any numpy logistic fit: newton-cholesky; Platt is an unpenalised logistic fit on the smoothed
            # targets, written as two weighted rows per score (label 1 with weight t, label 0 with weight 1 - t)
            nc = LogisticRegression(C=np.inf, solver="newton-cholesky", tol=1e-14, max_iter=1000).fit(
                np.r_[s, s].reshape(-1, 1), np.r_[np.ones_like(s), np.zeros_like(s)], sample_weight=np.r_[t, 1 - t])
            a_nc, b_nc = -float(nc.coef_[0][0]), -float(nc.intercept_[0])
            res["platt"][name] = {"n": int(y.size), "a_ours": ours.a_, "b_ours": ours.b_, "a_sklearn": float(a), "b_sklearn": float(b),
                                  "max_abs_param_diff": max(abs(ours.a_ - a), abs(ours.b_ - b)),
                                  "max_abs_prob_diff": float(np.max(np.abs(ours.predict(s) - 1 / (1 + np.exp(a * s + b))))),
                                  "gradient_ours": g_ours, "gradient_sklearn_sigmoid": g_sk,
                                  "a_newton_cholesky": a_nc, "b_newton_cholesky": b_nc,
                                  "max_abs_param_diff_newton_cholesky": max(abs(ours.a_ - a_nc), abs(ours.b_ - b_nc))}
            grid = np.quantile(s, [0.05, 0.25, 0.5, 0.75, 0.95])
            p0, p1, _ = K.venn_abers(s, y, grid)
            diffs = []
            for i, g in enumerate(grid):
                for lab, mine in ((0.0, p0[i]), (1.0, p1[i])):
                    iso = IsotonicRegression(increasing=True).fit(np.r_[s, g], np.r_[y, lab])
                    diffs.append(abs(float(iso.predict([g])[0]) - float(mine)))
            res["isotonic_in_venn_abers"][name] = {"points": len(diffs), "max_abs_diff": max(diffs)}
        p = np.clip(s, 1e-6, 1 - 1e-6)
        res["scores"][name] = {"brier_diff": abs(K.brier(y, s) - brier_score_loss(y, s)),
                               "log_loss_diff": abs(K.log_loss(y, s) - log_loss(y, p, labels=[0, 1])),
                               "ref_brier_diff": abs(K.brier(y, ref) - brier_score_loss(y, ref))}
    rep = json.loads((d / "calibration/SCORE_REPORT_DEV.json").read_text())
    for name, (s, y, ref) in sets(d).items():
        r = rep[name]
        res["scores"][name]["report_brier_diff"] = abs(r["brier"] - brier_score_loss(y, s))
        res["scores"][name]["report_ref_brier_diff"] = abs(r["brier_ref"] - brier_score_loss(y, ref))
    worst = {"platt_param": max(v["max_abs_param_diff"] for v in res["platt"].values()),
             "platt_param_newton_cholesky": max(v["max_abs_param_diff_newton_cholesky"] for v in res["platt"].values()),
             "isotonic": max(v["max_abs_diff"] for v in res["isotonic_in_venn_abers"].values()),
             "scores": max(max(v.values()) for v in res["scores"].values())}
    res["worst"] = worst
    # G7 as registered compares with _sigmoid_calibration within 1e-6; the PI-D-053 reference (newton-cholesky, 1e-9) is reported
    # beside it and never replaces the registered check
    res["g7_as_registered_pass"] = bool(worst["platt_param"] <= 1e-6)
    res["g7_cases_over_1e-6"] = sorted(k for k, v in res["platt"].items() if v["max_abs_param_diff"] > 1e-6)
    res["pi_d_053_reference_pass"] = bool(worst["platt_param_newton_cholesky"] <= 1e-9)
    res["pass"] = bool(res["g7_as_registered_pass"] and worst["isotonic"] <= 1e-12 and worst["scores"] <= 1e-9)
    try:
        from statsmodels.stats.proportion import proportion_confint
        wd = 0.0
        with open(d / "calibration/RELIABILITY_COVERAGE.csv") as f:
            for r in csv.DictReader(f):
                if r["wilson_lo"] and r["n"] and r["positives"] != "":
                    lo, hi = proportion_confint(int(r["positives"]), int(r["n"]), alpha=0.05, method="wilson")
                    wd = max(wd, abs(lo - float(r["wilson_lo"])), abs(hi - float(r["wilson_hi"])))
        res["wilson_statsmodels_max_abs_diff_vs_table_12_decimals"] = wd
        res["pass"] = bool(res["pass"] and wd <= 1e-11)
    except ImportError:
        res["wilson"] = "statsmodels not importable here"
    return res


def venn_abers_checks(d: Path) -> dict:
    import venn_abers
    from venn_abers import VennAbers
    res = {"venn_abers": "ip200/venn-abers 1.5.4", "cases": {}}
    data = {**sets(d), **fixtures()}
    bel = json.loads((d / "calibration/BELOW_GATE_DESCRIPTIVE.json").read_text())
    for name, (s, y, _) in data.items():
        if not 0 < y.sum() < y.size:
            continue
        grid = np.r_[np.quantile(s, [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]), s.min() - 0.005, s.max() + 0.005].clip(0, 1)
        p0, p1, p = K.venn_abers(s, y, grid)
        va = VennAbers().fit(np.column_stack([1 - s, s]), y.astype(int))
        pp, p01 = va.predict_proba(np.column_stack([1 - grid, grid]))
        case = {"n": int(y.size), "max_abs_diff_p0": float(np.max(np.abs(p0 - p01[:, 0]))),
                "max_abs_diff_p1": float(np.max(np.abs(p1 - p01[:, 1]))), "max_abs_diff_p": float(np.max(np.abs(p - pp[:, 1])))}
        if name in bel and "venn_abers_grid" in bel[name]:
            g = np.array([r["raw_b2"] for r in bel[name]["venn_abers_grid"]])
            _, q01 = va.predict_proba(np.column_stack([1 - g, g]))
            case["recorded_grid_max_abs_diff"] = float(max(np.max(np.abs(np.array([r["va_p0"] for r in bel[name]["venn_abers_grid"]]) - q01[:, 0])),
                                                          np.max(np.abs(np.array([r["va_p1"] for r in bel[name]["venn_abers_grid"]]) - q01[:, 1]))))
        res["cases"][name] = case
    worst = max(max(v for k, v in c.items() if k.startswith("max_abs") or k.startswith("recorded")) for c in res["cases"].values())
    res["worst"] = worst
    res["pass"] = bool(worst <= 1e-12)
    return res


def main() -> int:
    d, outp = Path(sys.argv[1]), Path(sys.argv[2])
    out = {"python": sys.executable}
    try:
        out["sklearn"] = sklearn_checks(d)
    except ImportError as e:
        out["sklearn"] = f"not importable: {e}"
    try:
        out["venn_abers"] = venn_abers_checks(d)
    except ImportError as e:
        out["venn_abers"] = f"not importable: {e}"
    ok = all(v.get("pass") for v in out.values() if isinstance(v, dict))
    out["pass"] = ok
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, indent=1, sort_keys=True, default=float) + "\n")
    print(json.dumps({k: (v.get("worst") if isinstance(v, dict) else v) for k, v in out.items()}, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
