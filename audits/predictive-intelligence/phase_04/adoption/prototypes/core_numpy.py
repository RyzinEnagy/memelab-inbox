"""Phase 04 prototype of the essential statistical engine (INSPIRED_NEW_CODE): numpy and the standard library only.

Not part of memelab; Phase 07 and later port these pieces with their own tests. Every function here was written for the lab
from the definitions, not copied: scikit-learn, statsmodels, ip200/venn-abers, purgedcv and river are used only as oracles in
the bake-off (bakeoff.py, calibration_check.py, splitter_check.py, drift_check.py).

Pieces: training prevalence (B0); a preprocessing step fitted on training rows only (median fill, missing indicators,
standardisation); L2 logistic regression by Newton steps with an unpenalised intercept (the objective of scikit-learn's
LogisticRegression with lbfgs); Platt sigmoid on a later window with Platt's smoothed targets (the objective of scikit-learn's
_sigmoid_calibration); inductive Venn-Abers by pool-adjacent-violators; Brier, log loss, Wilson interval, Holm; the frozen day
walk-forward of ACCEPTANCE["walk_forward"] and a fold audit; Page-Hinkley drift detection that refuses NaN; an as-of row
validator.
"""
from __future__ import annotations

import math
from typing import Iterable, Sequence

import numpy as np

DAY = 86400.0


# ---------------------------------------------------------------- scores and intervals
def brier(y: np.ndarray, p: np.ndarray) -> float:
    y, p = np.asarray(y, float), np.asarray(p, float)
    _check_probs(p)
    return float(np.mean((p - y) ** 2))


def log_loss(y: np.ndarray, p: np.ndarray, clip: float = 1e-6) -> float:
    y, p = np.asarray(y, float), np.asarray(p, float)
    _check_probs(p)
    q = np.clip(p, clip, 1 - clip)
    return float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q)))


def _check_probs(p: np.ndarray) -> None:
    if p.size == 0 or not np.all(np.isfinite(p)) or np.any(p < 0) or np.any(p > 1):
        raise ValueError("probabilities must be finite and inside [0, 1] (P38)")


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 1.0)
    ph = k / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def holm(pvalues: Sequence[float]) -> list[float]:
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adj, run = [0.0] * m, 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * pvalues[i]))
        adj[i] = run
    return adj


# ---------------------------------------------------------------- preprocessing and models
def informative_columns(X: np.ndarray) -> np.ndarray:
    """Columns with at least two distinct finite values in the training rows. Found on the first real-data run: an all-missing
    or constant training column makes HistGradientBoosting raise an opaque ValueError and lifelines' Cox fail to converge."""
    X = np.asarray(X, float)
    return np.array([j for j in range(X.shape[1]) if np.unique(X[np.isfinite(X[:, j]), j]).size >= 2], dtype=int)


class Prep:
    """Fitted on training rows only: drop columns that are constant or all missing in training, median fill, a missing
    indicator for every kept column with a training NaN, standardisation."""

    def fit(self, X: np.ndarray) -> "Prep":
        X = np.asarray(X, float)
        self.keep = informative_columns(X)
        Xk = X[:, self.keep]
        self.med = np.array([np.nanmedian(c) if np.any(np.isfinite(c)) else 0.0 for c in Xk.T])
        self.ind = np.where(np.any(~np.isfinite(Xk), axis=0))[0]
        Z = self._fill(X)
        self.mu = Z.mean(axis=0)
        sd = Z.std(axis=0)
        self.sd = np.where(sd > 0, sd, 1.0)
        return self

    def _fill(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, float)[:, self.keep]
        miss = ~np.isfinite(X)
        F = np.where(miss, self.med, X)
        return np.hstack([F, miss[:, self.ind].astype(float)]) if self.ind.size else F

    def transform(self, X: np.ndarray) -> np.ndarray:
        return (self._fill(X) - self.mu) / self.sd


def _check_fit_inputs(X: np.ndarray, y: np.ndarray, what: str) -> None:
    """Fail closed (found by error_semantics.py): non-finite inputs or a window with one class raise instead of returning a
    silent, degenerate probability; runtime.guarded turns the error into a visible abstention."""
    if X.size == 0 or not np.all(np.isfinite(X)):
        raise ValueError(f"{what}: inputs must be finite (run Prep first; P38)")
    vals = set(np.unique(y).tolist())
    if not vals <= {0.0, 1.0}:
        raise ValueError(f"{what}: labels must be 0 or 1")
    if vals != {0.0, 1.0}:
        raise ValueError(f"{what}: the window has one class only (INSUFFICIENT_HISTORY)")


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return np.where(z >= 0, 1 / (1 + np.exp(-np.abs(z))), np.exp(-np.abs(z)) / (1 + np.exp(-np.abs(z))))


class Logistic:
    """Minimises sum(log loss) + ||w||^2 / (2 C) with the intercept unpenalised, by Newton steps (deterministic)."""

    def __init__(self, C: float = 1.0, tol: float = 1e-12, max_iter: int = 200):
        self.C, self.tol, self.max_iter = C, tol, max_iter

    def fit(self, X: np.ndarray, y: np.ndarray) -> "Logistic":
        X, y = np.asarray(X, float), np.asarray(y, float)
        _check_fit_inputs(X, y, "Logistic.fit")
        n, d = X.shape
        A = np.hstack([np.ones((n, 1)), X])
        beta = np.zeros(d + 1)
        lam = np.r_[0.0, np.full(d, 1.0 / self.C)]
        for it in range(self.max_iter):
            p = _sigmoid(A @ beta)
            g = A.T @ (p - y) + lam * beta
            H = (A * (p * (1 - p))[:, None]).T @ A + np.diag(lam) + 1e-12 * np.eye(d + 1)
            step = np.linalg.solve(H, g)
            beta = beta - step
            if np.max(np.abs(step)) < self.tol:
                break
        self.n_iter_ = it + 1
        self.intercept_, self.coef_ = float(beta[0]), beta[1:].copy()
        return self

    def decision_function(self, X: np.ndarray) -> np.ndarray:
        return np.asarray(X, float) @ self.coef_ + self.intercept_

    def predict_proba1(self, X: np.ndarray) -> np.ndarray:
        return _sigmoid(self.decision_function(X))


class Platt:
    """Platt scaling on a later window: fit p = 1 / (1 + exp(a s + b)) to Platt's smoothed targets by Newton steps."""

    def fit(self, s: np.ndarray, y: np.ndarray, max_iter: int = 200, tol: float = 1e-12) -> "Platt":
        s, y = np.asarray(s, float), np.asarray(y, float)
        _check_fit_inputs(s, y, "Platt.fit")
        n1, n0 = float(np.sum(y > 0)), float(np.sum(y <= 0))
        t = np.where(y > 0, (n1 + 1) / (n1 + 2), 1 / (n0 + 2))
        if np.ptp(s) == 0:
            # constant scores (skeptic m7): only a s + b is identified; the optimum predicts the mean smoothed target exactly.
            # The 2 x 2 Newton system is singular here and scikit-learn's L-BFGS stops near its start, so the two differ.
            tbar = float(np.mean(t))
            self.a_, self.b_ = 0.0, math.log((1 - tbar) / tbar)
            return self
        a, b = 0.0, math.log((n0 + 1) / (n1 + 1))
        for _ in range(max_iter):
            f = a * s + b
            p = _sigmoid(-f)
            # derivative of the loss -sum(t log p + (1-t) log(1-p)) with p = sigmoid(-f): d/df = (t - p)
            r = t - p
            ga, gb = float(np.sum(r * s)), float(np.sum(r))
            w = p * (1 - p)
            haa, hab, hbb = float(np.sum(w * s * s)), float(np.sum(w * s)), float(np.sum(w))
            det = haa * hbb - hab * hab
            if det <= 1e-300:
                break
            da = (hbb * ga - hab * gb) / det
            db = (-hab * ga + haa * gb) / det
            a, b = a - da, b - db
            if max(abs(da), abs(db)) < tol:
                break
        self.a_, self.b_ = a, b
        return self

    def predict(self, s: np.ndarray) -> np.ndarray:
        return _sigmoid(-(self.a_ * np.asarray(s, float) + self.b_))


def _pava(y: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Weighted isotonic (non-decreasing) fit of y in the given order."""
    vals, wts, cnt = [], [], []
    for yi, wi in zip(y, w):
        vals.append(float(yi)); wts.append(float(wi)); cnt.append(1)
        while len(vals) > 1 and vals[-2] > vals[-1]:
            v2, w2, c2 = vals.pop(), wts.pop(), cnt.pop()
            v1, w1, c1 = vals.pop(), wts.pop(), cnt.pop()
            vals.append((v1 * w1 + v2 * w2) / (w1 + w2)); wts.append(w1 + w2); cnt.append(c1 + c2)
    return np.repeat(vals, cnt)


def venn_abers(cal_s: np.ndarray, cal_y: np.ndarray, test_s: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Inductive Venn-Abers: for each test score, isotonic fits with the test point labelled 0 and 1 give p0 and p1;
    the merged probability is p1 / (1 - p0 + p1). Ties in the score are pooled (one isotonic value per distinct score)."""
    cal_s, cal_y = np.asarray(cal_s, float), np.asarray(cal_y, float)
    _check_fit_inputs(cal_s, cal_y, "venn_abers")
    if not np.all(np.isfinite(np.asarray(test_s, float))):
        raise ValueError("venn_abers: test scores must be finite (P38)")
    p0s, p1s = [], []
    for s in np.asarray(test_s, float):
        out = []
        for lab in (0.0, 1.0):
            xs = np.r_[cal_s, s]
            ys = np.r_[cal_y, lab]
            ux, inv = np.unique(xs, return_inverse=True)
            sums = np.bincount(inv, weights=ys)
            cnts = np.bincount(inv).astype(float)
            fit = _pava(sums / cnts, cnts)
            out.append(float(fit[np.searchsorted(ux, s)]))
        p0s.append(out[0]); p1s.append(out[1])
    p0, p1 = np.array(p0s), np.array(p1s)
    return p0, p1, p1 / (1 - p0 + p1)


# ---------------------------------------------------------------- time-ordered splits
def day_walk_forward(decision_time: np.ndarray, label_matures_at: np.ndarray, *, first_last_train_day: float,
                     min_train: int) -> list[dict]:
    """Frozen rule of ACCEPTANCE["walk_forward"]: expanding by UTC decision day. Fold k has a training cutoff T at a UTC
    midnight; training rows are decided before T AND have labels matured by T; the validation rows are those decided on the
    day starting at T. The first cutoff is the midnight after first_last_train_day, extended by whole days until min_train
    training rows exist. A training label can never mature after its validation rows start (the embargo is the maturity)."""
    dt_, mat = np.asarray(decision_time, float), np.asarray(label_matures_at, float)
    if not (np.all(np.isfinite(dt_)) and np.all(np.isfinite(mat))):
        raise ValueError("day_walk_forward: decision and maturity times must be finite (a NaN would leave rows out silently)")
    days = np.floor(dt_ / DAY) * DAY
    cut = math.floor(first_last_train_day / DAY) * DAY + DAY
    last_day = float(days.max())
    folds = []
    while cut <= last_day:
        tr = np.where((dt_ < cut) & (mat <= cut))[0]
        te = np.where((dt_ >= cut) & (dt_ < cut + DAY))[0]
        if len(tr) >= min_train and len(te) > 0:
            folds.append({"cutoff": cut, "train": tr, "test": te})
        cut += DAY
    return folds


def fold_audit(decision_time: np.ndarray, label_matures_at: np.ndarray, folds: Iterable[dict], n_labelled: int, *,
               min_maturity_lag_s: float | None = None, groups: Sequence | None = None) -> dict:
    """Independent check of any splitter's folds (PI-D-029 rule 4), fail closed: training size, rows decided after the test
    start, training labels maturing after the test start, and, when the splitter declares a training cutoff (the time the model
    claims to be trained as of, P13), training rows decided or labels maturing after that cutoff. The cutoff check came from
    this phase's own adversarial pass; the rest from the Phase 04 skeptic (m1):
      - a non-finite decision or maturity time in any fold row makes the audit invalid (a NaN compares false and hid leaks);
      - a declared cutoff after the fold's test start is invalid (a model card would claim training after its own decisions);
      - with min_maturity_lag_s (entry lag + horizon + confirmation + fetch margin of the target), a maturity earlier than
        decision + that lag is invalid, so a maturity column of a shorter horizon cannot pass for the real one;
      - with groups (for example the mint), test rows whose group also appears in training are counted and reported; the frozen
        plan treats them as a sensitivity, so they do not make the audit invalid."""
    dt_, mat = np.asarray(decision_time, float), np.asarray(label_matures_at, float)
    grp = np.asarray(groups, dtype=object) if groups is not None else None
    rows, reasons = [], []
    for k, f in enumerate(folds):
        tr, te = np.asarray(f["train"], dtype=int), np.asarray(f["test"], dtype=int)
        used = np.concatenate([tr, te])
        nonfinite = int(np.sum(~np.isfinite(dt_[used])) + np.sum(~np.isfinite(mat[used])))
        t0 = float(np.min(dt_[te])) if len(te) and np.all(np.isfinite(dt_[te])) else float("nan")
        cut = f.get("cutoff")
        cut_ok = cut is None or (isinstance(cut, (int, float)) and math.isfinite(cut) and math.isfinite(t0) and cut <= t0)
        short = int(np.sum(mat[used] < dt_[used] + min_maturity_lag_s)) if min_maturity_lag_s is not None else 0
        shared = (int(np.sum(np.isin(grp[te], grp[tr]))) if grp is not None and len(tr) else None)
        r = {"fold": k, "train": int(len(tr)), "test": int(len(te)),
             "train_share": round(len(tr) / n_labelled, 4) if n_labelled else 0.0,
             "non_finite_times": nonfinite,
             "train_decided_after_test_start": int(np.sum(~(dt_[tr] < t0))),
             "train_labels_maturing_after_test_start": int(np.sum(~(mat[tr] <= t0))),
             "declared_cutoff": cut, "cutoff_after_test_start": not cut_ok,
             "train_decided_after_cutoff": int(np.sum(~(dt_[tr] < cut))) if cut is not None else 0,
             "train_labels_maturing_after_cutoff": int(np.sum(~(mat[tr] <= cut))) if cut is not None else 0,
             "maturity_shorter_than_target": short, "test_rows_sharing_group_with_training": shared,
             "overlap_rows": int(len(np.intersect1d(tr, te)))}
        rows.append(r)
        for key in ("non_finite_times", "train_decided_after_test_start", "train_labels_maturing_after_test_start",
                    "train_decided_after_cutoff", "train_labels_maturing_after_cutoff", "maturity_shorter_than_target",
                    "overlap_rows"):
            if r[key]:
                reasons.append(f"fold {k}: {key} {r[key]}")
        if r["cutoff_after_test_start"]:
            reasons.append(f"fold {k}: declared cutoff {cut} is after the test start {t0}")
        if not len(te):
            reasons.append(f"fold {k}: empty test set")
    return {"folds": rows, "valid_walk_forward": bool(rows) and not reasons, "reasons": reasons,
            "min_train_share": min((r["train_share"] for r in rows), default=0.0)}


# ---------------------------------------------------------------- monitoring
class PageHinkley:
    """Page-Hinkley test for a change of the mean (increase, and with two_sided a decrease), with a forgetting factor alpha.
    Written from the published test; the start values (minimum +inf, maximum -1) and alpha follow river 0.26.1's documented
    behaviour so that river can serve as an oracle in drift_check.py. Refuses NaN instead of absorbing it."""

    def __init__(self, delta: float = 0.005, threshold: float = 50.0, min_obs: int = 30, two_sided: bool = True,
                 alpha: float = 1 - 0.0001):
        self.delta, self.threshold, self.min_obs, self.two_sided, self.alpha = delta, threshold, min_obs, two_sided, alpha
        self.reset()

    def reset(self) -> None:
        self.n, self.mean, self.up, self.up_min, self.dn, self.dn_max = 0, 0.0, 0.0, math.inf, 0.0, -1.0

    def update(self, x: float) -> bool:
        if not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x):
            raise ValueError("drift input must be a finite number (P38): NaN is refused, never absorbed")
        self.n += 1
        self.mean += (x - self.mean) / self.n
        dev = x - self.mean
        self.up = self.alpha * self.up + dev - self.delta
        self.dn = self.alpha * self.dn + dev + self.delta
        self.up_min = min(self.up_min, self.up)
        self.dn_max = max(self.dn_max, self.dn)
        if self.n < self.min_obs:
            return False
        hit = self.up - self.up_min > self.threshold or (self.two_sided and self.dn_max - self.dn > self.threshold)
        if hit:
            self.reset()
        return hit


# ---------------------------------------------------------------- as-of validation
class AsOfError(ValueError):
    pass


def validate_rows(rows: list[dict], *, columns: Sequence[str], availability: Sequence[str], decision: str = "decision_time",
                  label: str = "y", matures: str = "label_matures_at", as_of: float | None = None) -> None:
    """The lab's as-of rule, fail closed: exactly the declared columns; every availability column present, finite and at or
    before the decision; a label only when it has matured by as_of (training-time rule, P05, P36)."""
    want = set(columns)
    for i, r in enumerate(rows):
        if set(r) != want:
            raise AsOfError(f"row {i}: columns {sorted(set(r) ^ want)} differ from the declared set (strict)")
        d = r[decision]
        if not isinstance(d, (int, float)) or not math.isfinite(d):
            raise AsOfError(f"row {i}: decision time missing")
        for a in availability:
            v = r[a]
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
                raise AsOfError(f"row {i}: {a} missing: an unknown availability time is not available")
            if v > d:
                raise AsOfError(f"row {i}: {a} {v} is after the decision {d} (future feature, P36)")
        if as_of is not None and r.get(label) is not None:
            m = r[matures]
            if not isinstance(m, (int, float)) or not math.isfinite(m) or m > as_of:
                raise AsOfError(f"row {i}: label not matured by {as_of} (P05)")
