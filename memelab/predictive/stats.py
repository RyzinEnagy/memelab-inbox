"""Phase 07: the essential statistical engine in numpy (research only, flag OFF, imported by no existing module).

Ported from the Phase 04 prototype `audits/predictive-intelligence/phase_04/adoption/prototypes/core_numpy.py` (PI-D-031,
INSPIRED_NEW_CODE written for the lab from the definitions; scikit-learn, ip200/venn-abers and river were oracles only), with
the pieces Phase 07 adds: ROC AUC, average precision, quantile calibration bins, expected calibration error, Brier skill score,
block bootstrap by group and the design-effect sample size. numpy and the standard library only; no network, no clock.

Fail closed: non-finite probabilities or inputs, labels other than 0 and 1, and one-class training windows raise instead of
returning a silent, degenerate number (P38); `runtime.guarded` turns such an error into a visible abstention.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Iterable, Sequence

import numpy as np

DAY = 86400.0
Z95 = 1.959963984540054


# ---------------------------------------------------------------- scores and intervals
def check_probs(p: Any) -> np.ndarray:
    p = np.asarray(p, float)
    if p.size == 0 or not np.all(np.isfinite(p)) or np.any(p < 0) or np.any(p > 1):
        raise ValueError("probabilities must be finite and inside [0, 1] (P38)")
    return p


def check_labels(y: Any) -> np.ndarray:
    y = np.asarray(y, float)
    if y.size == 0 or not set(np.unique(y).tolist()) <= {0.0, 1.0}:
        raise ValueError("labels must be 0 or 1")
    return y


def brier(y: Any, p: Any) -> float:
    y, p = check_labels(y), check_probs(p)
    return float(np.mean((p - y) ** 2))


def log_loss(y: Any, p: Any, clip: float = 1e-6) -> float:
    y, p = check_labels(y), check_probs(p)
    q = np.clip(p, clip, 1 - clip)
    return float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q)))


def brier_skill(y: Any, p: Any, ref: Any) -> float:
    """1 - Brier(p) / Brier(ref) on the same rows. NaN when the reference has zero error (undefined, never a fake 1)."""
    y, p, r = check_labels(y), check_probs(p), check_probs(ref)
    den = float(np.sum((r - y) ** 2))
    return float("nan") if den == 0 else 1.0 - float(np.sum((p - y) ** 2)) / den


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 1.0)
    ph = k / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def holm(pvalues: Sequence[float]) -> list[float]:
    """Holm step-down adjusted p-values over the whole family. An undefined test (None or NaN) counts in the family as p = 1
    (conservative: the frozen family is the three primary targets even when a target has no test) and its own adjusted value
    stays NaN."""
    m = len(pvalues)
    vals = [p if p is not None and math.isfinite(p) else 1.0 for p in pvalues]
    adj = [float("nan")] * m
    run = 0.0
    for rank, i in enumerate(sorted(range(m), key=lambda i: vals[i])):
        run = max(run, min(1.0, (m - rank) * vals[i]))
        if pvalues[i] is not None and math.isfinite(pvalues[i]):
            adj[i] = run
    return adj


def roc_auc(y: Any, s: Any) -> float:
    """Area under the ROC curve by the rank (Mann-Whitney) formula with average ranks for ties."""
    y, s = check_labels(y), np.asarray(s, float)
    if not np.all(np.isfinite(s)):
        raise ValueError("roc_auc: scores must be finite")
    n1, n0 = int(np.sum(y == 1)), int(np.sum(y == 0))
    if n1 == 0 or n0 == 0:
        raise ValueError("roc_auc needs both classes")
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s))
    ss = s[order]
    i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return float((np.sum(ranks[y == 1]) - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def average_precision(y: Any, s: Any) -> float:
    """Average precision: sum over distinct score thresholds (descending) of (recall step) x precision, the step-wise
    definition scikit-learn uses (no interpolation)."""
    y, s = check_labels(y), np.asarray(s, float)
    if not np.all(np.isfinite(s)):
        raise ValueError("average_precision: scores must be finite")
    if np.sum(y) == 0:
        raise ValueError("average_precision needs a positive")
    order = np.argsort(-s, kind="mergesort")
    ys, ss = y[order], s[order]
    last = np.r_[np.where(np.diff(ss) != 0)[0], len(ss) - 1]
    tps = np.cumsum(ys)[last]
    fps = (last + 1) - tps
    prec = tps / (tps + fps)
    rec = tps / tps[-1]
    return float(np.sum(np.diff(np.r_[0.0, rec]) * prec))


def calibration_bins(y: Any, p: Any, *, min_bin: int = 20, max_bins: int = 5, conf_z: float = Z95,
                     in_the_large_only_below: int = 40) -> dict:
    """Frozen calibration check (ACCEPTANCE calibration): in the large, and quantile bins of at least min_bin events (at most
    max_bins) when there are at least in_the_large_only_below events. A bin or the whole passes when its mean prediction lies
    inside the Wilson interval of its observed rate. ECE is descriptive only."""
    y, p = check_labels(y), check_probs(p)
    n = len(y)
    lo, hi = wilson(int(y.sum()), n, conf_z)
    mp = float(p.mean())
    out = {"n": n, "mean_pred": mp, "observed": float(y.mean()), "wilson": [lo, hi], "in_the_large_ok": lo <= mp <= hi,
           "bins": [], "every_bin_ok": None, "ece": None}
    if n < in_the_large_only_below:
        out["note"] = f"fewer than {in_the_large_only_below} events: calibration in the large only"
        return out
    nb = min(max_bins, n // min_bin)
    order = np.lexsort((np.arange(n), p))
    ece = 0.0
    for part in np.array_split(order, nb):
        k, m = int(y[part].sum()), len(part)
        bl, bh = wilson(k, m, conf_z)
        bp = float(p[part].mean())
        out["bins"].append({"n": m, "positives": k, "mean_pred": bp, "observed": k / m, "wilson": [bl, bh],
                            "p_min": float(p[part].min()), "p_max": float(p[part].max()), "ok": bl <= bp <= bh})
        ece += m / n * abs(bp - k / m)
    out["every_bin_ok"] = all(b["ok"] for b in out["bins"])
    out["ece"] = ece
    return out


# ---------------------------------------------------------------- uncertainty by groups
def group_bootstrap(groups: Sequence, stat: Callable[[np.ndarray], float], *, reps: int = 2000, seed: int = 20261025,
                    conf: float = 0.95) -> dict:
    """Bootstrap that resamples whole groups (decision days, mints) with replacement. `stat` gets the row indices of a
    replicate. Returns the percentile interval, the replicates' finite count and the replicate values."""
    g = np.asarray([str(x) for x in groups], dtype=object)
    uniq = sorted(set(g.tolist()))
    rows_of = [np.where(g == u)[0] for u in uniq]
    rng = np.random.default_rng(seed)
    vals = np.empty(reps)
    for r in range(reps):
        pick = rng.integers(0, len(uniq), size=len(uniq))
        idx = np.concatenate([rows_of[i] for i in pick])
        vals[r] = stat(idx)
    fin = vals[np.isfinite(vals)]
    a = (1 - conf) / 2
    ci = (float(np.quantile(fin, a)), float(np.quantile(fin, 1 - a))) if fin.size else (float("nan"), float("nan"))
    return {"groups": len(uniq), "reps": reps, "finite": int(fin.size), "ci": ci, "values": vals}


def design_effect_ess(groups: Sequence, values: Any, *, reps: int = 2000, seed: int = 20261025) -> float:
    """Effective sample size of a mean under group dependence: n x Var_iid(mean) / Var_group_bootstrap(mean)."""
    v = np.asarray(values, float)
    n = len(v)
    if n < 2:
        return float(n)
    var_iid = float(np.var(v, ddof=1)) / n
    bs = group_bootstrap(groups, lambda idx: float(np.mean(v[idx])), reps=reps, seed=seed)
    var_g = float(np.var(bs["values"][np.isfinite(bs["values"])], ddof=1))
    if var_g <= 0:
        return float("nan")
    return float(n * var_iid / var_g)


# ---------------------------------------------------------------- preprocessing and models
def informative_columns(X: np.ndarray) -> np.ndarray:
    """Columns with at least two distinct finite values in the training rows (an all-missing or constant column is dropped)."""
    X = np.asarray(X, float)
    return np.array([j for j in range(X.shape[1]) if np.unique(X[np.isfinite(X[:, j]), j]).size >= 2], dtype=int)


class Prep:
    """Fitted on training rows only: drop columns that are constant or all missing in training, median fill, a missing
    indicator for every kept column with a training NaN, standardisation."""

    def fit(self, X: np.ndarray) -> "Prep":
        X = np.asarray(X, float)
        self.n_in = X.shape[1]
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
        X = np.asarray(X, float)
        if X.ndim != 2 or X.shape[1] != self.n_in:
            raise ValueError(f"Prep: expected {self.n_in} columns")
        X = X[:, self.keep]
        miss = ~np.isfinite(X)
        F = np.where(miss, self.med, X)
        return np.hstack([F, miss[:, self.ind].astype(float)]) if self.ind.size else F

    def transform(self, X: np.ndarray) -> np.ndarray:
        return (self._fill(X) - self.mu) / self.sd

    def to_dict(self) -> dict:
        return {"n_in": int(self.n_in), "keep": [int(x) for x in self.keep], "med": [float(x) for x in self.med],
                "ind": [int(x) for x in self.ind], "mu": [float(x) for x in self.mu], "sd": [float(x) for x in self.sd]}

    @classmethod
    def from_dict(cls, d: dict) -> "Prep":
        o = cls()
        o.n_in = int(d["n_in"])
        o.keep = np.asarray(d["keep"], dtype=int)
        o.med = np.asarray(d["med"], float)
        o.ind = np.asarray(d["ind"], dtype=int)
        o.mu = np.asarray(d["mu"], float)
        o.sd = np.asarray(d["sd"], float)
        return o


def check_fit_inputs(X: Any, y: Any, what: str) -> None:
    X = np.asarray(X, float)
    if X.size == 0 or not np.all(np.isfinite(X)):
        raise ValueError(f"{what}: inputs must be finite (run Prep first; P38)")
    vals = set(np.unique(np.asarray(y, float)).tolist())
    if not vals <= {0.0, 1.0}:
        raise ValueError(f"{what}: labels must be 0 or 1")
    if vals != {0.0, 1.0}:
        raise ValueError(f"{what}: the window has one class only (INSUFFICIENT_HISTORY)")


def sigmoid(z: Any) -> np.ndarray:
    z = np.asarray(z, float)
    e = np.exp(-np.abs(z))
    return np.where(z >= 0, 1 / (1 + e), e / (1 + e))


class Logistic:
    """Minimises sum(log loss) + ||w||^2 / (2 C) with the intercept unpenalised, by Newton steps (deterministic)."""

    def __init__(self, C: float = 1.0, tol: float = 1e-12, max_iter: int = 200):
        self.C, self.tol, self.max_iter = C, tol, max_iter

    def fit(self, X: np.ndarray, y: np.ndarray) -> "Logistic":
        X, y = np.asarray(X, float), np.asarray(y, float)
        check_fit_inputs(X, y, "Logistic.fit")
        n, d = X.shape
        A = np.hstack([np.ones((n, 1)), X])
        beta = np.zeros(d + 1)
        lam = np.r_[0.0, np.full(d, 1.0 / self.C)]
        it = 0
        for it in range(self.max_iter):
            p = sigmoid(A @ beta)
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
        return sigmoid(self.decision_function(X))

    def to_dict(self) -> dict:
        return {"C": float(self.C), "intercept": float(self.intercept_), "coef": [float(x) for x in self.coef_],
                "n_iter": int(self.n_iter_)}

    @classmethod
    def from_dict(cls, d: dict) -> "Logistic":
        o = cls(C=float(d["C"]))
        o.intercept_, o.coef_, o.n_iter_ = float(d["intercept"]), np.asarray(d["coef"], float), int(d.get("n_iter", 0))
        return o


class Platt:
    """Platt scaling: fit p = 1 / (1 + exp(a s + b)) to Platt's smoothed targets by Newton steps."""

    def fit(self, s: np.ndarray, y: np.ndarray, max_iter: int = 200, tol: float = 1e-12) -> "Platt":
        s, y = np.asarray(s, float), np.asarray(y, float)
        check_fit_inputs(s, y, "Platt.fit")
        n1, n0 = float(np.sum(y > 0)), float(np.sum(y <= 0))
        t = np.where(y > 0, (n1 + 1) / (n1 + 2), 1 / (n0 + 2))
        if np.ptp(s) == 0:
            # constant scores: only a s + b is identified; the optimum predicts the mean smoothed target exactly
            tbar = float(np.mean(t))
            self.a_, self.b_ = 0.0, math.log((1 - tbar) / tbar)
            return self
        a, b = 0.0, math.log((n0 + 1) / (n1 + 1))
        for _ in range(max_iter):
            f = a * s + b
            p = sigmoid(-f)
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
        return sigmoid(-(self.a_ * np.asarray(s, float) + self.b_))

    def to_dict(self) -> dict:
        return {"a": float(self.a_), "b": float(self.b_)}

    @classmethod
    def from_dict(cls, d: dict) -> "Platt":
        o = cls()
        o.a_, o.b_ = float(d["a"]), float(d["b"])
        return o


def _pava(y: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Weighted isotonic (non-decreasing) fit of y in the given order."""
    vals: list[float] = []
    wts: list[float] = []
    cnt: list[int] = []
    for yi, wi in zip(y, w):
        vals.append(float(yi)); wts.append(float(wi)); cnt.append(1)
        while len(vals) > 1 and vals[-2] > vals[-1]:
            v2, w2, c2 = vals.pop(), wts.pop(), cnt.pop()
            v1, w1, c1 = vals.pop(), wts.pop(), cnt.pop()
            vals.append((v1 * w1 + v2 * w2) / (w1 + w2)); wts.append(w1 + w2); cnt.append(c1 + c2)
    return np.repeat(vals, cnt)


def venn_abers(cal_s: Any, cal_y: Any, test_s: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Inductive Venn-Abers: for each test score, isotonic fits with the test point labelled 0 and 1 give p0 and p1; the merged
    probability is p1 / (1 - p0 + p1). Ties in the score are pooled. A Phase 13 candidate, not used by Phase 07's baselines."""
    cal_s, cal_y = np.asarray(cal_s, float), np.asarray(cal_y, float)
    check_fit_inputs(cal_s, cal_y, "venn_abers")
    ts = np.asarray(test_s, float)
    if not np.all(np.isfinite(ts)):
        raise ValueError("venn_abers: test scores must be finite (P38)")
    p0s, p1s = [], []
    for s in ts:
        out = []
        for lab in (0.0, 1.0):
            xs, ys = np.r_[cal_s, s], np.r_[cal_y, lab]
            ux, inv = np.unique(xs, return_inverse=True)
            sums = np.bincount(inv, weights=ys)
            cnts = np.bincount(inv).astype(float)
            fit = _pava(sums / cnts, cnts)
            out.append(float(fit[np.searchsorted(ux, s)]))
        p0s.append(out[0]); p1s.append(out[1])
    p0, p1 = np.array(p0s), np.array(p1s)
    return p0, p1, p1 / (1 - p0 + p1)


# ---------------------------------------------------------------- time-ordered splits
def day_walk_forward(decision_time: Any, label_matures_at: Any, *, first_last_train_day: float, min_train: int) -> list[dict]:
    """Frozen rule of ACCEPTANCE["walk_forward"]: expanding by UTC decision day. Fold k has a training cutoff T at a UTC
    midnight; training rows are decided before T and have labels matured by T; the validation rows are those decided on the
    day starting at T. The first cutoff is the midnight after first_last_train_day, extended by whole days until min_train
    training rows exist. A training label can never mature after its validation rows start (the embargo is the maturity)."""
    dt_, mat = np.asarray(decision_time, float), np.asarray(label_matures_at, float)
    if dt_.size == 0:
        return []
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


def fold_audit(decision_time: Any, label_matures_at: Any, folds: Iterable[dict], n_labelled: int, *,
               min_maturity_lag_s: float | None = None, groups: Sequence | None = None) -> dict:
    """Independent check of any splitter's folds, fail closed: training size, rows decided after the test start, training
    labels maturing after the test start, a declared cutoff after the test start, training rows decided or labels maturing
    after the declared cutoff, non-finite times, maturities shorter than the target's lag (a maturity column of a shorter
    horizon), overlap; test rows sharing a group with training are reported (a sensitivity, not invalid)."""
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
        shared = int(np.sum(np.isin(grp[te], grp[tr]))) if grp is not None and len(tr) else None
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
    Start values follow river 0.26.1's documented behaviour (oracle in Phase 04). Refuses NaN instead of absorbing it."""

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
