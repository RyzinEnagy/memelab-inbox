"""Phase 11: analog cohorts and as-of regime labels for low-history opportunities (analog-1). Research only, flag OFF, imported by
no existing module. numpy and the standard library only, plus the reused `memelab.social.replay_core.LeakageError`. No network,
no clock, no language model.

Pre-registration: audits/predictive-intelligence/phase_11/ACCEPTANCE_CHECKLIST.md, experiments/EXPERIMENT_REGISTRY.csv and
PI-D-061 (committed before any cohort on a labelled decision). Rules enforced here:
  - the analog pool at `as_of` is a set of Phase 07 examples from `labels.training_labels` (decided before and matured by
    `as_of`), checked again row by row: a row decided at or after `as_of`, a label maturing after it or a token first seen after
    it is refused (FutureUniverseError, P43, NC2-AC). Nothing in this module reads a current token list or a later export (P09);
  - a pool row of the same chain and exact mint is token history, never an analog (P01: similarity is never identity); the same
    creator wallet is excluded (P14); one analog per group, where a group is a connected component over mints and every
    creator wallet recorded for them in the pool (repair pass 2, CX-S11: a mint whose rows carry different creator values is one
    group, never two), so duplicate windows of one token or one deployer count once;
  - G is the number of distinct groups among the analogs (not an effective sample size); the day-ICC design-effect N
    (`n_eff_icc`) and its Wilson interval are reported beside it; a number needs G >= 20 and 5 analog days (ACCEPTANCE min_bin_events and
    min_effective_days) and a pool that passes the training gate; else ANALOGS_TOO_FEW or INSUFFICIENT_HISTORY. A target outside
    the pool's support is OUT_OF_DISTRIBUTION with a sub-reason;
  - the regime label at T uses only decisions at or before T and compares with earlier export instants only (no full-sample
    statistic, no smoothing; counterexample CX-11); WARMUP below 5 earlier instants;
  - a cohort number is a research number (`publishable: False`) labelled COHORT_ESTIMATE_NOT_TOKEN_HISTORY; it is never a
    probability in a forecast document (Phase 13 calibration and a Phase 16 champion first); every answer carries
    NO_HISTORICAL_EXECUTABLE_DEPTH, and a position size gives EXECUTION_DATA_MISSING (P44);
  - every fitted object is a JSON card (no pickle); a card trained after a decision cannot score it (P13).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

import numpy as np

from ..social import replay_core as RC
from . import baselines as B
from . import contract as C
from . import features as F
from . import labels as L
from . import stats as K
from . import store as S

PHASE = "11"
ANALOG_VERSION = "analog-1"
STATUS = "DEVELOPMENT_RETROSPECTIVE_REVISION_CHECK_PASSED"     # PI-D-059: the frozen 48 h re-read changed no label
MIN_G = int(C.ACCEPTANCE["min_bin_events"])                   # 20 independent clusters
MIN_DAYS = int(C.ACCEPTANCE["min_effective_days"])            # 5 analog decision days
MIN_TOKEN_HISTORY = int(C.ACCEPTANCE["min_bin_events"])       # 20 matured rows of the exact mint
K_NEIGHBOURS = 30
OOD_Q = 0.95
M_SHRINK = B.M_SHRINK                                         # 20, the lab's shrinkage convention
REGIME_WINDOW_S = 86400.0
REGIME_WARMUP = 5
LAUNCH = "ac_launchpad_class"
T22 = "oc_token2022"
NUMERIC = (B.LIQ, B.MCAP, B.VOL, B.AGE)
CATEGORICAL = (LAUNCH, T22)
DIST_COLUMNS = NUMERIC + CATEGORICAL
ALLOWED = frozenset(B.ALLOWED_COLUMNS | {LAUNCH, T22})        # every column analog-1 may read (NC2 allowlist)
LAUNCH_CODES = {"PUMP_FUN": 0.0, "OTHER_LAUNCHPAD": 1.0, "NONE_RECORDED": 2.0}
MODEL_IDS = ("AC1_STRATA", "AC2_KNN", "AC3_KNN_REGIME")
PRIMARY = "AC3_KNN_REGIME"
LOCO = "AC3_LOCO"
COHORT_LABEL = "COHORT_ESTIMATE_NOT_TOKEN_HISTORY"
CHAIN_WIDE_STATE = "CHAIN_WIDE_DATA_NOT_AVAILABLE"
CATALYST_CATEGORY = "CATALYST_TABLES_NOT_EXPORTED"
DEPTH_FLAGS = ("NO_HISTORICAL_EXECUTABLE_DEPTH", "PRICE_PATH_NOT_PROCEEDS")
WARMUP, UNKNOWN = "WARMUP", "UNKNOWN"
CONSTRUCTIVE = "CONSTRUCTIVE"
AUTHORITY_ATTRS = ("oc_mint_authority_active", "oc_freeze_authority_active", "oc_transfer_fee_present", "oc_token2022")
DEPTH_ATTRS = ("oc_exit_cap_share", "oc_round_trip_friction_pct")
STATES = ("ANALOGS_TOO_FEW", "OUT_OF_DISTRIBUTION", "REGIME_UNKNOWN", "INSUFFICIENT_HISTORY", "TOKEN_HISTORY_TOO_SHORT")


class AnalogError(ValueError):
    pass


class FutureUniverseError(AnalogError):
    """A pool row decided at or after the cohort time, labelled after it, or of a token first seen after it (P43, NC2-AC)."""


class ModelTrainedAfterDecision(AnalogError):
    pass


def definitions() -> dict:
    return {"name": "memelab.predictive.analog", "version": ANALOG_VERSION, "min_g": MIN_G, "min_days": MIN_DAYS,
            "min_token_history": MIN_TOKEN_HISTORY, "k": K_NEIGHBOURS, "ood_q": OOD_Q, "m_shrink": M_SHRINK,
            "regime_window_s": REGIME_WINDOW_S, "regime_warmup": REGIME_WARMUP, "numeric": list(NUMERIC),
            "categorical": list(CATEGORICAL), "launch_codes": LAUNCH_CODES, "models": list(MODEL_IDS),
            "regime": "activity = median thesis_log1p_vol_24h_usd, tone = constructive share, of Solana decisions in (T-24h, T]; "
                      "each against the median over export instants strictly before T; ACTIVE/QUIET, RISK_ON/RISK_OFF; WARMUP < 5"}


def feature_set_sha() -> str:
    return S.sha(definitions())


def launchpad_class(token: dict | None) -> str:
    lp = (token or {}).get("launchpad")
    if not isinstance(lp, str) or not lp.strip():
        return "NONE_RECORDED"
    return "PUMP_FUN" if lp.strip().lower() == "pump.fun" else "OTHER_LAUNCHPAD"


def cluster_of(chain: str, mint: str, creator: str | None) -> str:
    """The row-level key (first pass). Cohorts use `groups` instead, which merges every row of one mint and every creator ever
    recorded for it in the pool (CX-S11)."""
    return f"creator:{creator}" if isinstance(creator, str) and creator else f"mint:{chain}:{mint}"


def groups(pool: Sequence[B.Example]) -> tuple[dict[str, str], dict]:
    """Connected components over the nodes (chain, mint) and creator wallet: each pool row joins its mint and its own creator,
    so one mint with rows under no creator and under one or more wallets is one group, and two mints of one wallet are one group
    (union-find; P14, CX-S11). Returns decision_key -> group id ("group:" + the smallest member mint) and the node -> root map."""
    parent: dict[tuple, tuple] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    for r in pool:
        m = ("m", r.chain, r.mint)
        find(m)
        if isinstance(r.creator, str) and r.creator:
            union(m, ("c", r.creator))
    label: dict[tuple, str] = {}
    for node in sorted(parent):
        if node[0] == "m":
            label.setdefault(find(node), f"group:{node[1]}:{node[2]}")
    return {r.decision_key: label[find(("m", r.chain, r.mint))] for r in pool}, {n: find(n) for n in parent}


def regroup(pool: Sequence[AExample]) -> list:
    """The pool with every row's cluster set to its group (repair pass 2, CX-S11)."""
    g, _ = groups(pool)
    return [r if r.cluster == g[r.decision_key] else AExample(**{**r.__dict__, "cluster": g[r.decision_key]}) for r in pool]


def day_icc(rows: Sequence[B.Example]) -> float:
    """One-way ANOVA intraclass correlation of the labels by decision day, clipped to [0, 1]; 0 when undefined."""
    by: dict[str, list[int]] = {}
    for r in rows:
        by.setdefault(r.day, []).append(int(r.y))
    k, N = len(by), sum(len(v) for v in by.values())
    if k < 2 or N - k < 1:
        return 0.0
    ybar = sum(sum(v) for v in by.values()) / N
    msb = sum(len(v) * (sum(v) / len(v) - ybar) ** 2 for v in by.values()) / (k - 1)
    msw = sum(sum((y - sum(v) / len(v)) ** 2 for y in v) for v in by.values()) / (N - k)
    n0 = (N - sum(len(v) ** 2 for v in by.values()) / N) / (k - 1)
    den = msb + (n0 - 1) * msw
    return float(min(1.0, max(0.0, (msb - msw) / den))) if den > 0 else 0.0


# ---------------------------------------------------------------- examples
@dataclass
class AExample(B.Example):
    cluster: str = ""
    regime: str | None = None
    launchpad: str | None = None
    first_seen_at: float | None = None
    hist_prior: float | None = None
    oc: dict = field(default_factory=dict)          # divergence attributes (onchain-1 values at the decision)
    pool_address: str | None = None


def attach(examples: Sequence[B.Example], extras: dict[str, dict]) -> list[AExample]:
    """Phase 07 examples with analog-1 inputs: launchpad class of the decision's own token row, token program, regime label at
    the decision, prior decisions and the divergence attributes, joined by decision key with chain, mint and time checked (P01)."""
    out = []
    for e in examples:
        s = extras.get(e.decision_key)
        if s is None:
            raise AnalogError(f"no analog inputs for decision {e.decision_key[:12]}")
        if s["chain"] != e.chain or s["mint"] != e.mint or float(s["decision_time"]) != e.decision_time:
            raise B.IdentityJoinError("analog inputs of another decision (P01)")
        x, av = dict(e.x), dict(e.avail)
        x[LAUNCH] = LAUNCH_CODES[s["launchpad_class"]]
        av[LAUNCH] = e.decision_time                      # the decision's own token row, inside the export that is the decision
        t22 = s.get("token2022")
        x[T22] = float(t22) if isinstance(t22, (int, float)) and math.isfinite(t22) else float("nan")
        if math.isfinite(x[T22]):
            a = s.get("token2022_available_at")
            if a is None:
                raise AnalogError(f"{T22}: a value without an availability time")
            av[T22] = float(a)
        else:
            av[T22] = e.decision_time
        out.append(AExample(**{**e.__dict__, "x": x, "avail": av}, cluster=cluster_of(e.chain, e.mint, e.creator),
                            regime=s.get("regime"), launchpad=s["launchpad_class"], first_seen_at=s.get("first_seen_at"),
                            hist_prior=s.get("hist_prior"), oc=dict(s.get("oc") or {}), pool_address=s.get("pool_address")))
    return out


def check_asof(examples: Sequence[B.Example], columns: Sequence[str], *, as_of: float | None, with_labels: bool) -> None:
    bad = [c for c in columns if c not in ALLOWED]
    if bad:
        raise F.AsOfError(f"columns {bad} are not in the analog-1 allowlist (NC2-AC: only declared as-of inputs reach a cohort)")
    rows = []
    for e in examples:
        r = {"decision_time": e.decision_time}
        for c in columns:
            r[c] = e.x.get(c)
            r[c + "__available_at"] = e.avail.get(c)
        if with_labels:
            r["y"], r["label_matures_at"] = e.y, e.label_matures_at
        rows.append(r)
    cols = ["decision_time"] + list(columns) + [c + "__available_at" for c in columns] + (["y", "label_matures_at"] if with_labels else [])
    F.validate_rows(rows, columns=cols, availability=[c + "__available_at" for c in columns], as_of=as_of)


def check_pool(pool: Sequence[AExample], as_of: float) -> None:
    """Every pool row decided before, matured by and of a token first seen by `as_of` (P43, NC2-AC); inputs available at their
    decisions (P36)."""
    for r in pool:
        if not r.decision_time < as_of:
            raise FutureUniverseError(f"pool row {r.decision_key[:12]} decided at or after the cohort time (P43)")
        if not r.label_matures_at <= as_of:
            raise FutureUniverseError(f"pool row {r.decision_key[:12]} has a label maturing after the cohort time (P05, NC2-AC)")
        if r.first_seen_at is not None and r.first_seen_at > as_of:
            raise FutureUniverseError(f"pool row {r.decision_key[:12]}: token first seen after the cohort time (future-issued, P43)")
    if pool:
        check_asof(pool, list(DIST_COLUMNS), as_of=as_of, with_labels=True)


def check_target(e: AExample, as_of: float) -> None:
    if as_of > e.decision_time:
        raise F.AsOfError("a cohort as of a time after the decision would use outcomes the decision could not know (P43)")
    check_asof([e], list(DIST_COLUMNS), as_of=None, with_labels=False)


def complete(e: B.Example, cols: Sequence[str] = DIST_COLUMNS) -> bool:
    return all(math.isfinite(B._num(e.x.get(c))) for c in cols)


def cell_of(e: B.Example) -> tuple[str | None, str | None]:
    return (e.cohort.get("launch_age_bucket"), e.cohort.get("liquidity_bucket"))


# ---------------------------------------------------------------- regime label at T (as of T, past only)
@dataclass
class RegimeRow:
    decision_time: float
    status: str | None
    log_vol: float                                   # thesis_log1p_vol_24h_usd at the decision, NaN when missing
    available_at: float | None = None
    chain: str = "solana"


def _inputs(rows: Sequence[RegimeRow], T: float) -> tuple[float, float, int]:
    w = [r for r in rows if T - REGIME_WINDOW_S < r.decision_time <= T]
    v = [r.log_vol for r in w if math.isfinite(r.log_vol)]
    act = float(np.median(v)) if v else float("nan")
    tone = (sum(1 for r in w if B.status_group(r.status) == CONSTRUCTIVE) / len(w)) if w else float("nan")
    return act, tone, len(w)


def _label(a: float, t: float, past_a: Sequence[float], past_t: Sequence[float], n_prior: int) -> tuple[str, float, float]:
    if n_prior < REGIME_WARMUP:
        return WARMUP, float("nan"), float("nan")
    pa = [x for x in past_a if math.isfinite(x)]
    pt = [x for x in past_t if math.isfinite(x)]
    if not (pa and pt and math.isfinite(a) and math.isfinite(t)):
        return UNKNOWN, float("nan"), float("nan")
    ma, mt = float(np.median(pa)), float(np.median(pt))
    return ("ACTIVE" if a > ma else "QUIET") + "/" + ("RISK_ON" if t > mt else "RISK_OFF"), ma, mt


def _fin(v: float) -> float | None:
    return float(v) if math.isfinite(v) else None


def _record(T, a, t, n, lab, ma, mt, n_prior) -> dict:
    return {"T": float(T), "activity_median_log1p_vol": _fin(a), "tone_constructive_share": _fin(t), "window_decisions": n,
            "past_activity_median": _fin(ma), "past_tone_median": _fin(mt), "prior_instants": n_prior, "label": lab,
            "chain_wide_state": CHAIN_WIDE_STATE, "catalyst_category": CATALYST_CATEGORY}


def _assert_visible(rows: Sequence[RegimeRow], T: float) -> None:
    for r in rows:
        if r.decision_time > T:
            raise RC.LeakageError(f"regime input decided at {r.decision_time} after T {T} (P36, CX-11)")
        if r.available_at is not None and r.available_at > T:
            raise RC.LeakageError("regime input available after T (P36)")


def visible_at(rows: Sequence[RegimeRow], T: float) -> list[RegimeRow]:
    return [r for r in rows if r.decision_time <= T and (r.available_at is None or r.available_at <= T)]


def regime_as_of(rows: Sequence[RegimeRow], T: float) -> dict:
    """The regime record at T from decisions visible at T only; refuses any later row. Thresholds are the medians over the
    export instants strictly before T (no full-sample statistic, CX-11)."""
    _assert_visible(rows, T)
    instants = sorted({r.decision_time for r in rows if r.decision_time < T})
    past = [_inputs(rows, s) for s in instants]
    a, t, n = _inputs(rows, T)
    lab, ma, mt = _label(a, t, [p[0] for p in past], [p[1] for p in past], len(instants))
    return _record(T, a, t, n, lab, ma, mt, len(instants))


def regime_series(rows: Sequence[RegimeRow]) -> dict[float, dict]:
    """regime_as_of at every export instant of `rows`, computed once (each label uses only earlier instants)."""
    instants = sorted({r.decision_time for r in rows})
    vals = {s: _inputs([r for r in rows if r.decision_time <= s], s) for s in instants}
    out = {}
    for i, s in enumerate(instants):
        prior = instants[:i]
        a, t, n = vals[s]
        lab, ma, mt = _label(a, t, [vals[p][0] for p in prior], [vals[p][1] for p in prior], len(prior))
        out[s] = _record(s, a, t, n, lab, ma, mt, len(prior))
    return out


def regime_full_sample(rows: Sequence[RegimeRow], T: float) -> dict:
    """TRAP ONLY (CX-11): the label with full-sample medians over every export instant, including those after T. Kept to show
    that the truncation check catches it; never used for a cohort."""
    instants = sorted({r.decision_time for r in rows})
    vals = [_inputs(rows, s) for s in instants]
    a, t, n = _inputs([r for r in rows if r.decision_time <= T], T)
    lab, ma, mt = _label(a, t, [v[0] for v in vals], [v[1] for v in vals], len(instants))
    return _record(T, a, t, n, lab, ma, mt, len(instants))


def truncation_invariant(fn: Callable[[Sequence[RegimeRow], float], dict], rows: Sequence[RegimeRow], T: float) -> bool:
    """True when `fn` gives the same label at T on every row and on the rows visible at T. A function that refuses later rows
    (regime_as_of) is invariant by construction; a function that reads them (the CX-11 trap) can differ."""
    try:
        full = fn(rows, T)["label"]
    except RC.LeakageError:
        return True
    return full == fn(visible_at(rows, T), T)["label"]


# ---------------------------------------------------------------- cohort selection
def _excluded(target: AExample, pool: Sequence[AExample], *, loco: bool) -> tuple[list[AExample], dict]:
    """Rows of the target's mint (token history), then every row in a group that holds the target's mint or the target's own
    creator wallet (P14 over every creator ever recorded for the mint in the pool, CX-S11), then the LOCO campaign."""
    _, root = groups(pool)
    banned = {root[n] for n in (("m", target.chain, target.mint), ("c", target.creator)) if n in root}
    out, ex = [], {"same_mint": 0, "same_creator": 0, "same_campaign": 0}
    for r in pool:
        if r.chain == target.chain and r.mint == target.mint:
            ex["same_mint"] += 1
            continue
        if root[("m", r.chain, r.mint)] in banned:
            ex["same_creator"] += 1
            continue
        if loco and target.narrative and r.narrative == target.narrative:
            ex["same_campaign"] += 1
            continue
        out.append(r)
    return out, ex


class KnnIndex:
    """The reference rows of one neighbour query (complete pool rows, regime-restricted for AC3): z-scores from their mean and
    population sd (sd 0 counts 1), categorical codes, cluster ids, and the out-of-distribution threshold, which depends on the
    reference rows only (not on the target or the labels)."""

    def __init__(self, ref: Sequence[AExample]):
        self.rows = list(ref)
        X = np.array([[e.x[c] for c in NUMERIC] for e in self.rows], float).reshape(len(self.rows), len(NUMERIC))
        self.mu = X.mean(axis=0) if len(self.rows) else np.zeros(len(NUMERIC))
        sd = X.std(axis=0) if len(self.rows) else np.ones(len(NUMERIC))
        self.sd = np.where(sd > 0, sd, 1.0)
        self.Z = (X - self.mu) / self.sd
        self.cat = np.array([[e.x[c] for c in CATEGORICAL] for e in self.rows], float).reshape(len(self.rows), len(CATEGORICAL))
        self.keys = [e.decision_key for e in self.rows]
        names = sorted({e.cluster for e in self.rows})
        self.cid = np.array([names.index(e.cluster) for e in self.rows], int)
        self.n_clusters = len(names)
        self._thr: float | None = None

    def query(self, e: AExample) -> np.ndarray:
        z = (np.array([e.x[c] for c in NUMERIC], float) - self.mu) / self.sd
        c = np.array([e.x[c] for c in CATEGORICAL], float)
        d2 = np.sum((self.Z - z) ** 2, axis=1) + np.sum(self.cat != c, axis=1)
        return np.sqrt(d2)

    def nearest_clusters(self, d: np.ndarray, allowed: np.ndarray | None = None, *, skip: int | None = None) -> list[int]:
        """Row index of each cluster's nearest row (ties by decision key), clusters ordered by (distance, decision key)."""
        best: dict[int, int] = {}
        for i in range(len(self.rows)):
            if (allowed is not None and not allowed[i]) or (skip is not None and self.cid[i] == skip):
                continue
            j = best.get(int(self.cid[i]))
            if j is None or (d[i], self.keys[i]) < (d[j], self.keys[j]):
                best[int(self.cid[i])] = i
        return sorted(best.values(), key=lambda i: (d[i], self.keys[i]))

    def threshold(self, k: int = K_NEIGHBOURS) -> float:
        """The 95th percentile (numpy linear) of each reference row's distance to its k-th nearest other cluster."""
        if self._thr is None:
            n = len(self.rows)
            if n == 0 or self.n_clusters < 2:
                self._thr = float("nan")
            else:
                G2 = np.sum((self.Z[:, None, :] - self.Z[None, :, :]) ** 2, axis=2)
                M = np.sum(self.cat[:, None, :] != self.cat[None, :, :], axis=2)
                D = np.sqrt(G2 + M)
                kth = []
                for i in range(n):
                    cm = np.full(self.n_clusters, np.inf)
                    np.minimum.at(cm, self.cid, D[i])
                    cm[self.cid[i]] = np.inf
                    v = np.sort(cm[np.isfinite(cm)])
                    kth.append(v[min(k, len(v)) - 1])
                self._thr = float(np.quantile(np.array(kth, float), OOD_Q))
        return self._thr


def ood_threshold(ref: Sequence[AExample], k: int = K_NEIGHBOURS) -> float:
    return KnnIndex(ref).threshold(k)


def _days(rows: Sequence[B.Example]) -> list[str]:
    return [r.day for r in rows]


def _kish(labels: Sequence[str]) -> float:
    if not labels:
        return 0.0
    c = np.array(list({d: labels.count(d) for d in set(labels)}.values()), float)
    return float(c.sum() ** 2 / np.sum(c ** 2))


def n_eff_icc(G: int, kish: float, icc: float) -> float | None:
    """Design-effect effective N of G analogs grouped by day: G / (1 + (G / day Kish ESS - 1) x day ICC)."""
    if not G or not kish:
        return None
    return float(G / (1.0 + (G / kish - 1.0) * icc))


def _summary(analogs: Sequence[AExample], b0: float, icc: float = 0.0) -> dict:
    G = len(analogs)
    k = int(sum(r.y for r in analogs))
    days = _days(analogs)
    kish = _kish(days)
    ne = n_eff_icc(G, kish, icc)
    out = {"G": G, "G_meaning": "distinct groups (mint and creator components), not an effective sample size",
           "positives": k, "analog_mints": len({r.mint for r in analogs}), "analog_days": len(set(days)),
           "day_kish_ess": kish, "pool_day_icc": icc, "n_eff_icc": ne, "raw_rate": (k / G) if G else None,
           "wilson": list(K.wilson(k, G)) if G else None, "wilson_assumes_independent_analogs": True,
           "wilson_icc": list(K.wilson(k / G * ne, ne)) if G and ne else None,
           "shrunk_number": (k + M_SHRINK * b0) / (G + M_SHRINK) if G else None}
    srt = sorted(analogs, key=lambda r: (r.decision_time, r.decision_key))
    h = G // 2
    old, new = srt[:h], srt[h:]
    if old and new:
        ko, kn = sum(r.y for r in old), sum(r.y for r in new)
        wo, wn = K.wilson(ko, len(old)), K.wilson(kn, len(new))
        out["time_sensitivity"] = {"older_n": len(old), "older_rate": ko / len(old), "older_wilson": list(wo),
                                   "newer_n": len(new), "newer_rate": kn / len(new), "newer_wilson": list(wn),
                                   "split_time": srt[h].decision_time,
                                   "time_unstable": bool(wo[1] < wn[0] or wn[1] < wo[0])}
    else:
        out["time_sensitivity"] = None
    return out


def select(model: str, target: AExample, pool: Sequence[AExample], *, as_of: float, loco: bool = False,
           check: bool = True, cache: dict | None = None) -> dict:
    """One cohort answer for one target: the analogs, effective N, the research number or the states. `as_of` <= T."""
    if model not in MODEL_IDS:
        raise AnalogError(f"unknown analog model {model}")
    if check:
        check_target(target, as_of)
        check_pool(pool, as_of)
    gk = ("groups", id(pool))
    gp = cache.get(gk) if cache is not None else None
    if gp is None:
        gp = (regroup(pool), day_icc(pool))
        if cache is not None:
            cache[gk] = gp
    pool, icc = gp
    y = B.labels_of(pool)
    b0 = float(y.mean()) if len(pool) else float("nan")
    ans: dict[str, Any] = {"model": model + ("_LOCO" if loco else ""), "decision_key": target.decision_key, "mint": target.mint,
                           "decision_time": target.decision_time, "as_of": float(as_of), "regime": target.regime,
                           "pool_n": len(pool), "pool_positives": int(y.sum()) if len(pool) else 0, "b0": b0,
                           "no_matured_token_rows": not any(r.chain == target.chain and r.mint == target.mint for r in pool),
                           "no_prior_decision": (None if target.hist_prior is None or not math.isfinite(B._num(target.hist_prior))
                                                 else bool(target.hist_prior == 0)),
                           "label": COHORT_LABEL, "publishable": False, "flags": list(DEPTH_FLAGS), "reasons": [],
                           "analogs": [], "number": None}
    g = B.gate(len(pool), int(y.sum()) if len(pool) else 0)
    if g:
        ans["reasons"].append(g)
        return ans
    cands, ex = _excluded(target, pool, loco=loco)
    ans["excluded"] = ex
    reasons: list[str] = []
    analogs: list[AExample] = []
    if model == "AC1_STRATA":
        cell = cell_of(target)
        ans["cell"] = list(cell)
        if None in cell or "UNKNOWN" in cell:
            reasons.append("OUT_OF_DISTRIBUTION:MISSING_INPUT")
        else:
            rows = [r for r in cands if cell_of(r) == cell]
            if not rows:
                reasons.append("OUT_OF_DISTRIBUTION:CELL_UNSEEN")
            newest: dict[str, AExample] = {}
            for r in rows:
                cur = newest.get(r.cluster)
                if cur is None or (r.decision_time, r.decision_key) > (cur.decision_time, cur.decision_key):
                    newest[r.cluster] = r
            analogs = sorted(newest.values(), key=lambda r: (r.decision_time, r.decision_key))
            ans["analogs"] = [{"decision_key": r.decision_key, "mint": r.mint, "cluster": r.cluster, "day": r.day, "y": r.y,
                               "distance": None} for r in analogs]
    else:
        if not complete(target):
            reasons.append("OUT_OF_DISTRIBUTION:MISSING_INPUT")
        ref = [r for r in pool if complete(r)]
        if model == "AC3_KNN_REGIME":
            if target.regime in (None, WARMUP, UNKNOWN):
                reasons.append("REGIME_UNKNOWN")
                ref = []
            else:
                ref = [r for r in ref if r.regime == target.regime]
                if not ref:
                    reasons.append("OUT_OF_DISTRIBUTION:REGIME_UNSEEN")
        cset = {r.decision_key for r in cands}
        if not reasons:
            ck = (model, target.regime if model == "AC3_KNN_REGIME" else None, id(pool))
            idx = cache.get(ck) if cache is not None else None
            if idx is None:
                idx = KnnIndex(ref)
                if cache is not None:
                    cache[ck] = idx
            d = idx.query(target)
            allowed = np.array([k in cset for k in idx.keys], bool)
            nn = idx.nearest_clusters(d, allowed)[:K_NEIGHBOURS]
            analogs = [idx.rows[i] for i in nn]
            thr = idx.threshold()
            kth = float(d[nn[-1]]) if nn else float("inf")
            ans["kth_distance"], ans["ood_threshold"] = kth, thr
            ans["scale"] = {"mean": idx.mu.tolist(), "sd": idx.sd.tolist()}
            ans["analogs"] = [{"decision_key": idx.keys[i], "mint": idx.rows[i].mint, "cluster": idx.rows[i].cluster,
                               "day": idx.rows[i].day, "y": idx.rows[i].y, "distance": float(d[i])} for i in nn]
            if not nn:
                reasons.append("OUT_OF_DISTRIBUTION:NO_CANDIDATE")
            elif not (math.isfinite(thr) and kth <= thr):
                reasons.append("OUT_OF_DISTRIBUTION:FAR_FROM_ANALOGS")
        ans["ref_n"] = len(ref)
    ans["new_mint"] = ans["no_prior_decision"] if ans["no_prior_decision"] is not None else ans["no_matured_token_rows"]
    ans.update(_summary(analogs, b0, icc))
    if analogs or not reasons:
        if ans["G"] < MIN_G:
            reasons.append("ANALOGS_TOO_FEW:G_BELOW_MIN")
        if ans["analog_days"] < MIN_DAYS:
            reasons.append("ANALOGS_TOO_FEW:DAYS_BELOW_MIN")
    ans["reasons"] = reasons
    if not reasons:
        ans["number"] = ans["shrunk_number"]
        if ans["time_sensitivity"] and ans["time_sensitivity"]["time_unstable"]:
            ans["flags"].append("TIME_UNSTABLE")
    return ans


def state_of(reasons: Sequence[str]) -> str | None:
    """The abstention vocabulary of a reason list: the first state in STATES order."""
    if not reasons:
        return None
    heads = {r.split(":")[0] for r in reasons}
    for s in STATES:
        if s in heads:
            return s
    return sorted(heads)[0]


# ---------------------------------------------------------------- divergence (phase prompt step 5)
def divergence_flags(target: AExample, analogs: Sequence[AExample]) -> list[str]:
    """Authority, fee, token program, exit-capacity share and friction of the target against its analogs. A flag is part of the
    answer; segmentation never removes it."""
    flags = []
    for a in AUTHORITY_ATTRS:
        tv = target.oc.get(a)
        if tv is None or not math.isfinite(B._num(tv)):
            flags.append(f"{a.upper()}_UNKNOWN")
            continue
        known = [B._num(r.oc.get(a)) for r in analogs if r.oc.get(a) is not None and math.isfinite(B._num(r.oc.get(a)))]
        if known and sum(1 for v in known if v == float(tv)) < 0.5 * len(known):
            flags.append(f"{a.upper()}_DIFFERS_FROM_ANALOGS")
    for a, name in zip(DEPTH_ATTRS, ("EXIT_CAP_SHARE_DIFFERS", "FRICTION_DIFFERS")):
        tv = B._num(target.oc.get(a))
        known = [B._num(r.oc.get(a)) for r in analogs if math.isfinite(B._num(r.oc.get(a)))]
        if not math.isfinite(tv):
            flags.append(f"{a.upper()}_UNKNOWN")
        elif known:
            lo, hi = np.quantile(np.array(known, float), [0.1, 0.9])
            if tv < lo or tv > hi:
                flags.append(name)
    return flags


# ---------------------------------------------------------------- router (policy)
def token_history(target: AExample, pool: Sequence[AExample]) -> list[AExample]:
    """Matured rows of the exact chain and mint (P01: never a symbol or name match; never an analog)."""
    return [r for r in pool if r.chain == target.chain and r.mint == target.mint]


def cohort_forecast(target: AExample, pool: Sequence[AExample], *, as_of: float, position_usd: float | None = None,
                    quotes: Sequence[dict] = (), max_loss: float = 0.1, max_age_s: float = 3600.0) -> dict:
    """Token history when valid, the regime-matched analog cohort when valid, else ABSTAIN with every reason. Research only."""
    check_target(target, as_of)
    check_pool(pool, as_of)
    th = token_history(target, pool)
    out: dict[str, Any] = {"decision_key": target.decision_key, "chain": target.chain, "mint": target.mint,
                           "decision_time": target.decision_time, "as_of": float(as_of), "token_history_n": len(th),
                           "publishable": False, "probability": None, "flags": list(DEPTH_FLAGS)}
    if len(th) >= MIN_TOKEN_HISTORY:
        k = int(sum(r.y for r in th))
        b0 = float(B.labels_of(pool).mean())
        out.update({"path": "TOKEN_HISTORY", "label": "TOKEN_HISTORY_ESTIMATE", "number": (k + M_SHRINK * b0) / (len(th) + M_SHRINK),
                    "wilson": list(K.wilson(k, len(th))), "reasons": [], "cohort": None})
    else:
        a = select(PRIMARY, target, pool, as_of=as_of, check=False)
        out["cohort"] = a
        if a["number"] is not None:
            out.update({"path": "ANALOG_COHORT", "label": COHORT_LABEL, "number": a["number"], "wilson": a["wilson"],
                        "reasons": [], "new_mint": a["new_mint"]})
            sel = {d["decision_key"] for d in a["analogs"]}
            out["flags"] += divergence_flags(target, [r for r in pool if r.decision_key in sel])
        else:
            out.update({"path": "ABSTAIN", "label": None, "number": None, "wilson": None,
                        "reasons": ["TOKEN_HISTORY_TOO_SHORT"] + list(a["reasons"]), "new_mint": a["new_mint"],
                        "state": state_of(a["reasons"]) or "ABSTAIN"})
    if position_usd is not None:
        from . import onchain as O
        cap = (O.size_cap_usd(quotes, decision_time=target.decision_time, pool_address=target.pool_address, max_loss=max_loss,
                              max_age_s=max_age_s) if target.pool_address else {"size_cap_usd": None, "basis": "EXECUTION_DATA_MISSING"})
        out["size_cap"] = cap
        if cap.get("basis") == "EXECUTION_DATA_MISSING":
            out["flags"].append("EXECUTION_DATA_MISSING")
    return out


# ---------------------------------------------------------------- cards (the pool is the model)
POOL_FIELDS = ("decision_key", "chain", "mint", "decision_time", "label_matures_at", "y", "creator", "narrative", "route",
               "key_conflict", "label_key", "snapshot_sha256", "cluster", "regime", "launchpad", "first_seen_at", "hist_prior",
               "pool_address", "status")


def _pool_rows(pool: Sequence[AExample]) -> list[dict]:
    out = []
    for e in sorted(pool, key=lambda r: (r.decision_time, r.decision_key)):
        d = {f: getattr(e, f) for f in POOL_FIELDS}
        d["x"] = {c: (None if not math.isfinite(B._num(e.x.get(c))) else float(e.x[c])) for c in sorted(ALLOWED) if c in e.x}
        d["avail"] = {c: e.avail.get(c) for c in sorted(ALLOWED) if c in e.avail}
        d["cohort"] = {k: e.cohort.get(k) for k in ("launch_age_bucket", "liquidity_bucket")}
        d["oc"] = {k: (None if not math.isfinite(B._num(v)) else float(v)) for k, v in sorted(e.oc.items())}
        out.append(d)
    return out


def pool_from_rows(rows: Sequence[dict]) -> list[AExample]:
    out = []
    for d in rows:
        x = {c: (float("nan") if v is None else float(v)) for c, v in d["x"].items()}
        out.append(AExample(decision_key=d["decision_key"], chain=d["chain"], mint=d["mint"], decision_time=float(d["decision_time"]),
                            label_matures_at=float(d["label_matures_at"]), y=int(d["y"]), x=x, avail=dict(d["avail"]),
                            status=d.get("status"), creator=d.get("creator"), narrative=d.get("narrative"), route=d.get("route"),
                            key_conflict=bool(d.get("key_conflict")), label_key=d.get("label_key"),
                            snapshot_sha256=d.get("snapshot_sha256"), cohort=dict(d["cohort"]), cluster=d["cluster"],
                            regime=d.get("regime"), launchpad=d.get("launchpad"), first_seen_at=d.get("first_seen_at"),
                            hist_prior=d.get("hist_prior"), oc={k: (float("nan") if v is None else v) for k, v in d["oc"].items()},
                            pool_address=d.get("pool_address")))
    return out


def fit(model_id: str, target: str, pool: Sequence[AExample], cutoff: float, *, y_override: np.ndarray | None = None,
        is_fixture: bool = False, meta: dict | None = None, card_kind: str | None = None) -> dict:
    """A card holding the analog pool at the cutoff (checked: decided before, matured by, first seen by the cutoff)."""
    if model_id not in MODEL_IDS:
        raise AnalogError(f"unknown analog model {model_id}")
    pool = list(pool)
    if y_override is not None:
        yy = np.asarray(y_override, float)
        pool = [AExample(**{**e.__dict__, "y": int(v)}) for e, v in zip(pool, yy)]
    check_pool(pool, cutoff)
    pool = regroup(pool)
    y = B.labels_of(pool)
    g = B.gate(len(pool), int(y.sum()) if len(pool) else 0)
    body = {"spec": {"model": model_id, "definitions_sha": feature_set_sha()}, "pool": _pool_rows(pool)}
    if g:
        body["abstain"] = g
    card = {"phase": PHASE, "kind": card_kind or model_id, "model_id": f"{card_kind or model_id}:{target}", "targets": [target],
            "target_version": {target: C.TARGETS[target]["version"]}, "training_cutoff": float(cutoff),
            "training_cutoff_utc": B._iso(cutoff), "registry_sha": C.registry_sha256(), "feature_set_sha": feature_set_sha(),
            "analog_version": ANALOG_VERSION, "base_feature_set_sha": F.feature_set_sha(), "feature_version": F.FEATURE_VERSION,
            "labels_version": L.LABELS_VERSION, "store_schema": S.SCHEMA_VERSION, "label_mode": "provider",
            "n_train": len(pool), "k_train": int(y.sum()) if len(pool) else 0,
            "label_set_sha": B.sha(sorted([e.label_key or e.decision_key, int(e.y)] for e in pool)),
            "data_snapshot_sha": B.sha(sorted([e.decision_key, e.snapshot_sha256] for e in pool)),
            "status": STATUS, "revision_check_claimed": True, "revision_check_ref": "PI-D-059", "publishable": False,
            "promotion": "MODEL_NOT_PROMOTED", "evidence_class": B.evidence_class(is_fixture),
            "max_train_decision_time": max((e.decision_time for e in pool), default=None),
            "max_train_label_matures_at": max((e.label_matures_at for e in pool), default=None)}
    card.update(meta or {})
    card["body"] = body
    card["model_sha"] = B.sha({k: v for k, v in card.items() if k != "model_sha"})
    return card


def verify_card(card: dict) -> dict:
    want = B.sha({k: v for k, v in card.items() if k != "model_sha"})
    if card.get("model_sha") != want:
        raise B.ModelHashMismatch(f"card {card.get('model_id')}: content does not match its model_sha (MODEL_HASH_MISMATCH)")
    if card.get("registry_sha") != C.registry_sha256():
        raise AnalogError("card trained under another registry fingerprint")
    if card.get("feature_set_sha") != feature_set_sha() or card.get("analog_version") != ANALOG_VERSION:
        raise F.FeatureVersionError("FEATURE_SCHEMA_MISMATCH: analog-1 definitions differ from the card's (P46)")
    F.require_compatible(card["feature_version"], card["base_feature_set_sha"])
    return card


def dumps(card: dict) -> str:
    """Compact canonical JSON (a card holds its whole pool)."""
    return json.dumps(card, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"


def loads(text: str) -> dict:
    return verify_card(json.loads(text))


def predict(card: dict, examples: Sequence[AExample], *, loco: bool = False) -> tuple[np.ndarray, list[str | None], list[dict]]:
    """Numbers, the first abstain reason and the full answers for decisions at or after the card's cutoff only (P13)."""
    early = [e for e in examples if e.decision_time < float(card["training_cutoff"])]
    if early:
        raise ModelTrainedAfterDecision(f"card {card['model_id']} built at {card['training_cutoff_utc']} cannot score "
                                        f"{len(early)} earlier decision(s) (P13, RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF)")
    n = len(examples)
    p, why, answers = np.full(n, np.nan), [None] * n, []
    if "abstain" in card["body"]:
        return p, [card["body"]["abstain"]] * n, [{"reasons": [card["body"]["abstain"]], "number": None}] * n
    pool = pool_from_rows(card["body"]["pool"])
    cut = float(card["training_cutoff"])
    check_pool(pool, cut)
    cache: dict = {}
    for i, e in enumerate(examples):
        check_target(e, cut)
        a = select(card["body"]["spec"]["model"], e, pool, as_of=cut, loco=loco, check=False, cache=cache)
        answers.append(a)
        if a["number"] is None:
            why[i] = a["reasons"][0] if a["reasons"] else "NO_NUMBER"
        else:
            p[i] = a["number"]
    fin = p[np.isfinite(p)]
    if fin.size:
        K.check_probs(fin)
    return p, why, answers


def degenerate(p: Any) -> bool:
    q = np.asarray(p, float)
    q = q[np.isfinite(q)]
    return bool(q.size > 1 and np.ptp(q) == 0)


# ---------------------------------------------------------------- the frozen walk-forward, same folds as Phase 07
def walk_forward(target: str, development: Sequence[AExample], train_at: Callable[[float], Sequence[AExample]], *,
                 nc1_seeds: Iterable[int] = range(20), is_fixture: bool = False, models: Sequence[str] = MODEL_IDS) -> dict:
    dev = sorted(development, key=lambda e: (e.decision_time, e.mint))
    if not dev:
        return {"target": target, "folds": [], "oos": [], "audit": None, "status": "INSUFFICIENT_HISTORY",
                "evidence_class": B.evidence_class(is_fixture)}
    dt_ = np.array([e.decision_time for e in dev])
    mat = np.array([e.label_matures_at for e in dev])
    folds = K.day_walk_forward(dt_, mat, first_last_train_day=B.first_last_train_day(),
                               min_train=C.ACCEPTANCE["walk_forward"]["first_fold_min_events"])
    audit = K.fold_audit(dt_, mat, folds, len(dev), min_maturity_lag_s=B.maturity_lag(target), groups=[e.mint for e in dev])
    if folds and not audit["valid_walk_forward"]:
        raise B.BaselineError(f"{target}: fold audit failed: {audit['reasons']}")
    seeds = list(nc1_seeds)
    out_folds, oos = [], []
    for k, f in enumerate(folds):
        cut = float(f["cutoff"])
        train = list(train_at(cut))
        want = sorted(dev[i].decision_key for i in f["train"])
        got = sorted(e.decision_key for e in train)
        if want != got:
            raise B.WalkForwardMismatch(f"{target} fold {k}: walk-forward index ({len(want)}) and training gate ({len(got)}) differ")
        test = [dev[i] for i in f["test"]]
        B.check_asof(train, sorted(B.ALLOWED_COLUMNS), as_of=cut, with_labels=True)
        cards = {"B0": B.fit_b0(target, train, cut), "B2": B.fit_b2(target, train, cut)}
        for c in cards.values():
            c["evidence_class"] = B.evidence_class(is_fixture)
            c["model_sha"] = B.sha({kk: v for kk, v in c.items() if kk != "model_sha"})
        preds = {b: B.predict(cards[b], test) for b in ("B0", "B2")}
        answers = {}
        for m in models:
            cards[m] = fit(m, target, train, cut, is_fixture=is_fixture)
            p, w, a = predict(cards[m], test)
            preds[m], answers[m] = (p, w), a
        if PRIMARY in models:
            p, w, a = predict(cards[PRIMARY], test, loco=True)
            preds[LOCO], answers[LOCO] = (p, w), a
        nc1 = {s: np.full(len(test), np.nan) for s in seeds}
        if "AC2_KNN" in cards and "abstain" not in cards["AC2_KNN"]["body"]:
            for s in seeds:
                yy = np.random.default_rng(s).permutation(B.labels_of(train))
                cnc = fit("AC2_KNN", target, train, cut, y_override=yy, is_fixture=is_fixture, meta={"nc1_seed": s}, card_kind="NC1AC")
                nc1[s] = predict(cnc, test)[0]
        mints_tr = {e.mint for e in train}
        for j, e in enumerate(test):
            row = {"fold": k, "cutoff": cut, "example": e, "y": e.y, "new_mint": e.mint not in mints_tr,
                   "no_prior_decision": e.hist_prior == 0, "regime": e.regime, "answers": {m: answers[m][j] for m in answers}}
            for m in preds:
                row[m] = float(preds[m][0][j])
                row[m + "_why"] = preds[m][1][j]
            for s, v in nc1.items():
                row[f"NC1AC_{s}"] = float(v[j])
            oos.append(row)
        out_folds.append({"fold": k, "cutoff": cut, "cutoff_utc": B._iso(cut), "n_train": len(train),
                          "k_train": int(B.labels_of(train).sum()), "n_test": len(test), "k_test": int(sum(e.y for e in test)),
                          "pool_regimes": {r: sum(1 for e in train if (e.regime or "NONE") == r) for r in sorted({e.regime or "NONE" for e in train})},
                          "test_day": B._iso(cut)[:10], "cards": cards,
                          "split_fingerprint": B.sha([target, cut, want, sorted(e.decision_key for e in test)])})
    return {"target": target, "folds": out_folds, "oos": oos, "audit": audit, "nc1_seeds": seeds,
            "evidence_class": B.evidence_class(is_fixture), "split_fingerprint": B.sha([f["split_fingerprint"] for f in out_folds]),
            "status": "OK" if out_folds else "INSUFFICIENT_HISTORY"}


CONTRACT_REASON = {"ANALOGS_TOO_FEW": "INSUFFICIENT_HISTORY", "INSUFFICIENT_HISTORY": "INSUFFICIENT_HISTORY",
                   "TOKEN_HISTORY_TOO_SHORT": "INSUFFICIENT_HISTORY", "REGIME_UNKNOWN": "INSUFFICIENT_HISTORY",
                   "OUT_OF_DISTRIBUTION": "OOD", "EXECUTION_DATA_MISSING": "EXECUTION_DATA_MISSING"}


def contract_reasons(reasons: Sequence[str]) -> list[str]:
    """The frozen contract vocabulary for an analog answer (contract.ABSTAIN_REASONS is unchanged): every analog state maps to
    INSUFFICIENT_HISTORY or OOD, and a cohort number always adds UNCALIBRATED and MODEL_NOT_SELECTED (never published)."""
    out = []
    for r in reasons:
        c = CONTRACT_REASON.get(r.split(":")[0])
        if c is None:
            raise AnalogError(f"analog reason {r} has no contract mapping")
        if c not in out:
            out.append(c)
    return out + [r for r in ("UNCALIBRATED", "MODEL_NOT_SELECTED") if r not in out]


def abstain_document(target: str, answer: dict, *, snapshot_hash: str, generated_at_utc: str, base_rate: float | None,
                     card: dict | None) -> dict:
    """An ABSTAIN forecast document of the frozen contract for one cohort answer (format only: a cohort number is never a
    published probability). The analog states and effective N go in the `cohort` field, without the number."""
    doc = B.abstain_document(target, mint=answer["mint"], snapshot_hash=snapshot_hash, decision_time_utc=B._iso(answer["decision_time"]),
                             generated_at_utc=generated_at_utc, reasons=contract_reasons(answer.get("reasons") or []),
                             base_rate=base_rate, card=card)
    doc["cohort"] = {"analog_version": ANALOG_VERSION, "model": answer.get("model"), "states": list(answer.get("reasons") or []),
                     "label": answer.get("label"), "G": answer.get("G"), "analog_days": answer.get("analog_days"),
                     "regime": answer.get("regime"), "new_mint": answer.get("new_mint")}
    return doc
