"""Phase 13: calibration-1, the calibration and uncertainty layer every forecast passes through (research only, flag OFF,
imported by no existing module). numpy and the standard library only; no network, no clock, no store.

Pre-registration: audits/predictive-intelligence/phase_13/ACCEPTANCE_CHECKLIST.md (rules 1 to 11) and PI-D-067. Rules enforced
here:
  - a calibration set holds only chronologically valid out-of-sample rows: decided before the cutoff, label matured by it,
    scored by a card trained at or before the row's decision (never in-sample), development split only (never the spent
    retrospective holdout, never the prospective holdout); a violating row raises, it is never silently dropped;
  - a calibrator is fitted only above the frozen gate (100 events, 20 per class, 5 decision days); the method follows a fixed
    rule (Venn-Abers from 200 events with 40 per class, else Platt), never a choice made on outcomes;
  - the calibration check is the frozen ACCEPTANCE tolerance (`stats.calibration_bins`) on admissible evidence of at least 50
    events and 10 per class that is not the fit set;
  - an interval is the hull of the calibrator's own interval and the Wilson interval of the score's support bin, so it widens
    as support falls (P23, P24); it describes calibration sampling under exchangeability, never unmodelled risk;
  - non-finite or out-of-range numbers raise (P38); flat predictions are detected (P11); Brier and log loss are always reported
    together with counts and intervals, and their disagreement is flagged (P10, P23);
  - a calibration card is JSON with a sha over its content (no pickle); a card whose content differs from its sha is refused.

Nothing here publishes a probability: `abstention.py` decides publication, and today every card is ABSTAIN.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Sequence

import numpy as np

from . import contract as C
from . import stats as K

PHASE = "13"
CALIBRATION_VERSION = "calibration-1"
_A = C.ACCEPTANCE
FIT_GATE = {"min_events": _A["min_train_events"], "min_per_class": _A["min_train_per_class"], "min_days": _A["min_effective_days"]}
VENN_ABERS_GATE = {"min_events": 200, "min_per_class": 40}
EVIDENCE_GATE = {"min_events": _A["min_holdout_events"], "min_per_class": _A["min_holdout_per_class"]}
CAL_RULE = _A["calibration"]
SUPPORT_MIN = CAL_RULE["min_bin_events"]
DISPLAY_RANGE = (float(_A["display_probability_range"][0]), float(_A["display_probability_range"][1]))
OOD_Z = 4.0
FLAT_PTP = 1e-9
NEAR_FLAT_SD = 0.005
SCORE_REPS = 2000
BASE_REPS = 20000
SEED = 20261025
LOG_LOSS_CLIP = _A["secondary_scores"]["log_loss_clip"]
AUC_MIN_PER_CLASS = _A["secondary_scores"]["auc_and_average_precision_min_per_class"]
DRIFT = {"delta": 0.005, "threshold": 2.0, "min_obs": 30, "two_sided": False}

CALIBRATED, UNCALIBRATED = "CALIBRATED", "UNCALIBRATED"
LEVELS = ("ABSTAIN", "SHADOW", "VALIDATED_EXPERIMENTAL", "NO_GO")
PUBLISHABLE_LEVELS = ("SHADOW", "VALIDATED_EXPERIMENTAL")
METHODS = ("VENN_ABERS", "PLATT")
SOURCES = ("STATISTICAL_MODEL",)                  # a behavioral simulation is never a calibration source (P27)
SPLITS_ALLOWED = ("DEVELOPMENT",)
EVIDENCE_STATUSES = ("ADMISSIBLE", "NOT_YET_MATURED", "NONE")
REFERENCE_KEYS = ("calibration_card_sha", "calibration_version", "method", "level", "status", "holdout_n", "holdout_k",
                  "passed", "calibration_n", "calibration_k", "support_n", "support_k")
ROW_KEYS = ("decision_key", "mint", "decision_time", "label_matures_at", "y", "score", "scored_by_cutoff", "split")
HOLDOUT_START = C.parse_utc(_A["holdout_window_utc"][0])
PROSPECTIVE_START = C.parse_utc(_A["prospective_from_utc"])


class CalibrationError(ValueError):
    pass


class CardHashMismatch(CalibrationError):
    pass


def canon(o: Any) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(o: Any) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


def _iso(t: float) -> str:
    import datetime as _dt
    return _dt.datetime.fromtimestamp(float(t), _dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _day(t: float) -> str:
    return _iso(t)[:10]


def _fin01(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and 0.0 <= x <= 1.0


# ---------------------------------------------------------------- calibration set (rule 1)
def check_rows(rows: Sequence[dict], cutoff: float) -> None:
    """Raise unless every row may calibrate a forecast made at `cutoff`: development split, decided before the cutoff, label
    matured by it, a binary label, a finite score in [0, 1], scored by a card trained at or before the row's own decision (an
    in-sample score is refused), no duplicate decision."""
    seen = set()
    for r in rows:
        miss = [k for k in ROW_KEYS if k not in r]
        if miss:
            raise CalibrationError(f"calibration row lacks {miss}")
        k = r["decision_key"]
        if k in seen:
            raise CalibrationError(f"calibration row {str(k)[:12]} appears twice")
        seen.add(k)
        if r["split"] not in SPLITS_ALLOWED:
            raise CalibrationError(f"calibration row {str(k)[:12]} is {r['split']}: only development out-of-sample rows calibrate "
                                   "(the retrospective holdout is spent, the prospective one is Phase 19's)")
        if not (float(r["decision_time"]) < HOLDOUT_START and float(r["label_matures_at"]) <= HOLDOUT_START):
            raise CalibrationError(f"calibration row {str(k)[:12]} is not a development row (decided before and matured by "
                                   f"{_A['holdout_window_utc'][0]}): a holdout row relabelled as development is refused")
        if not float(r["decision_time"]) < cutoff:
            raise CalibrationError(f"calibration row {str(k)[:12]} is decided at or after the cutoff (P43)")
        if not float(r["label_matures_at"]) <= cutoff:
            raise CalibrationError(f"calibration row {str(k)[:12]} matures after the cutoff: its label is not known yet (P05)")
        if r["y"] not in (0, 1) or isinstance(r["y"], bool):
            raise CalibrationError(f"calibration row {str(k)[:12]} has no binary label")
        if not _fin01(r["score"]):
            raise CalibrationError(f"calibration row {str(k)[:12]} has a score that is not finite in [0, 1] (P38)")
        if not float(r["scored_by_cutoff"]) <= float(r["decision_time"]):
            raise CalibrationError(f"calibration row {str(k)[:12]} was scored by a card trained after its decision: an in-sample "
                                   "or later-trained score is never a calibration row (P13)")


EVIDENCE_SPLITS = ("PROSPECTIVE",)               # from Phase 13 on; the retrospective holdout is spent (PI-D-065)


def check_evidence_rows(rows: Sequence[dict], *, fit_cutoff: float, as_of: float) -> None:
    """Raise unless every row is admissible calibration evidence: prospective split (never the spent retrospective holdout,
    never development rows, which belong to the fit set), decided at or after the calibrator's own cutoff, matured by `as_of`,
    binary label, finite score in [0, 1], scored by a card trained at or before its decision."""
    seen = set()
    for r in rows:
        miss = [k for k in ROW_KEYS if k not in r]
        if miss:
            raise CalibrationError(f"evidence row lacks {miss}")
        k = r["decision_key"]
        if k in seen:
            raise CalibrationError(f"evidence row {str(k)[:12]} appears twice")
        seen.add(k)
        if r["split"] not in EVIDENCE_SPLITS:
            raise CalibrationError(f"evidence row {str(k)[:12]} is {r['split']}: only prospective rows are admissible evidence "
                                   "(the retrospective holdout is spent, PI-D-065)")
        if float(r["decision_time"]) < max(fit_cutoff, PROSPECTIVE_START):
            raise CalibrationError(f"evidence row {str(k)[:12]} is decided before the calibrator's cutoff or the prospective start: "
                                   "not admissible out-of-sample evidence")
        if not float(r["label_matures_at"]) <= as_of:
            raise CalibrationError(f"evidence row {str(k)[:12]} is not matured at {as_of} (P05)")
        if r["y"] not in (0, 1) or isinstance(r["y"], bool):
            raise CalibrationError(f"evidence row {str(k)[:12]} has no binary label")
        if not _fin01(r["score"]):
            raise CalibrationError(f"evidence row {str(k)[:12]} has a score that is not finite in [0, 1] (P38)")
        if not float(r["scored_by_cutoff"]) <= float(r["decision_time"]):
            raise CalibrationError(f"evidence row {str(k)[:12]} was scored by a card trained after its decision (P13)")


def rows_at(rows: Sequence[dict], cutoff: float) -> list[dict]:
    """The rows usable at `cutoff`: decided before it and matured by it (the rest are simply not known yet), then checked."""
    use = [r for r in rows if float(r["decision_time"]) < cutoff and float(r["label_matures_at"]) <= cutoff]
    check_rows(use, cutoff)
    return sorted(use, key=lambda r: (float(r["decision_time"]), str(r["mint"]), str(r["decision_key"])))


def counts(rows: Sequence[dict]) -> dict:
    n = len(rows)
    k = int(sum(int(r["y"]) for r in rows))
    days = len({_day(float(r["decision_time"])) for r in rows})
    return {"n": n, "k": k, "negatives": n - k, "days": days}


# ---------------------------------------------------------------- gates and the method rule (rules 2, 3)
def fit_gate(n: int, k: int, days: int) -> list[str]:
    """Empty when a calibrator may be fitted; else the named shortfalls."""
    out = []
    if n < FIT_GATE["min_events"]:
        out.append(f"events {n} < {FIT_GATE['min_events']}")
    if k < FIT_GATE["min_per_class"] or n - k < FIT_GATE["min_per_class"]:
        out.append(f"per class {min(k, n - k)} < {FIT_GATE['min_per_class']}")
    if days < FIT_GATE["min_days"]:
        out.append(f"decision days {days} < {FIT_GATE['min_days']}")
    return out


def method_for(n: int, k: int, days: int) -> str | None:
    if fit_gate(n, k, days):
        return None
    if n >= VENN_ABERS_GATE["min_events"] and min(k, n - k) >= VENN_ABERS_GATE["min_per_class"]:
        return "VENN_ABERS"
    return "PLATT"


def evidence_gate(n: int, k: int) -> list[str]:
    out = []
    if n < EVIDENCE_GATE["min_events"]:
        out.append(f"evidence events {n} < {EVIDENCE_GATE['min_events']}")
    if k < EVIDENCE_GATE["min_per_class"] or n - k < EVIDENCE_GATE["min_per_class"]:
        out.append(f"evidence per class {min(k, n - k)} < {EVIDENCE_GATE['min_per_class']}")
    return out


# ---------------------------------------------------------------- calibrators
def fit_calibrator(scores: Any, y: Any, method: str) -> dict:
    """Fit one calibrator (no gate here: the caller applies `fit_gate`, and descriptive below-gate fits say so)."""
    s, yy = np.asarray(scores, float), np.asarray(y, float)
    K.check_probs(s)
    K.check_fit_inputs(s, yy, f"calibrator {method}")
    if method == "PLATT":
        return {"method": "PLATT", "params": K.Platt().fit(s, yy).to_dict()}
    if method == "VENN_ABERS":
        pairs = sorted([float(a), int(b)] for a, b in zip(s, yy))
        return {"method": "VENN_ABERS", "params": {"calibration": pairs}}
    raise CalibrationError(f"unknown calibration method {method!r}")


def apply_calibrator(cal: dict, scores: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(point, low, high) per score. Venn-Abers gives p0, p1 and the merged p1 / (1 - p0 + p1); Platt gives a point only."""
    s = np.asarray(scores, float)
    if s.size == 0 or not np.all(np.isfinite(s)):
        raise CalibrationError("calibrator input must be finite (P38)")
    if cal["method"] == "PLATT":
        p = K.Platt.from_dict(cal["params"]).predict(s)
        out = (p, p.copy(), p.copy())
    elif cal["method"] == "VENN_ABERS":
        pairs = np.asarray(cal["params"]["calibration"], float)
        p0, p1, p = K.venn_abers(pairs[:, 0], pairs[:, 1], s)
        out = (p, p0, p1)
    else:
        raise CalibrationError(f"unknown calibration method {cal['method']!r}")
    for a in out:
        if not np.all(np.isfinite(a)) or np.any(a < 0) or np.any(a > 1):
            raise CalibrationError("calibrator produced a number outside [0, 1] or not finite (P38)")
    return out


# ---------------------------------------------------------------- support and intervals (rule 7)
def support_bins(scores: Any, y: Any) -> list[dict]:
    """The frozen quantile bins of the calibration set (the ACCEPTANCE calibration layout); a set under 40 events is one bin."""
    s, yy = K.check_probs(scores), K.check_labels(y)
    res = K.calibration_bins(yy, s, min_bin=CAL_RULE["min_bin_events"], max_bins=CAL_RULE["max_bins"],
                             in_the_large_only_below=CAL_RULE["in_the_large_only_below_events"])
    if res["bins"]:
        return [{"n": b["n"], "k": b["positives"], "p_min": b["p_min"], "p_max": b["p_max"]} for b in res["bins"]]
    return [{"n": res["n"], "k": int(yy.sum()), "p_min": float(s.min()), "p_max": float(s.max())}]


def support_of(bins: Sequence[dict], score: float) -> dict | None:
    """The bin holding `score` (between two bins: the nearer edge, ties to the lower bin); None outside the calibration range."""
    if not (isinstance(score, (int, float)) and math.isfinite(score)) or not bins:
        return None
    lo, hi = min(b["p_min"] for b in bins), max(b["p_max"] for b in bins)
    if score < lo or score > hi:
        return None
    best, gap = None, math.inf
    for b in bins:
        g = 0.0 if b["p_min"] <= score <= b["p_max"] else min(abs(score - b["p_min"]), abs(score - b["p_max"]))
        if g < gap:
            best, gap = b, g
    return dict(best)


def interval(low: float, high: float, support_n: int, support_k: int) -> list[float]:
    """Hull of the calibrator's interval [low, high] and the Wilson 95% interval of the support bin's observed rate."""
    if not (_fin01(low) and _fin01(high)) or low > high:
        raise CalibrationError("calibrator interval must be finite inside [0, 1] (P38)")
    wl, wh = K.wilson(int(support_k), int(support_n))
    return [float(min(low, wl)), float(max(high, wh))]


# ---------------------------------------------------------------- degeneracy and scores (rules 8, 9)
def degeneracy(p: Any) -> dict:
    p = K.check_probs(p)
    ptp, sd = float(np.ptp(p)), float(np.std(p))
    return {"flat": ptp <= FLAT_PTP, "near_flat": sd < NEAR_FLAT_SD, "ptp": ptp, "sd": sd, "n": int(p.size)}


def score_report(y: Any, p: Any, ref: Any, *, days: Sequence[str], mints: Sequence[str], reps: int = SCORE_REPS,
                 seed: int = SEED) -> dict:
    """Brier and log loss of p and of the reference on the same rows, both skills, counts, day and mint bootstrap intervals of
    the Brier skill (wider governs), AUC and AP only with enough of each class, degeneracy flags and the Brier and log-loss
    conflict flag. Nothing is dropped when the two scores disagree (P23)."""
    yy, pp, rr = K.check_labels(y), K.check_probs(p), K.check_probs(ref)
    n, k = int(yy.size), int(yy.sum())
    b, br = K.brier(yy, pp), K.brier(yy, rr)
    ll, llr = K.log_loss(yy, pp, LOG_LOSS_CLIP), K.log_loss(yy, rr, LOG_LOSS_CLIP)
    bss = K.brier_skill(yy, pp, rr)
    lls = float("nan") if llr == 0 else 1.0 - ll / llr
    out = {"n": n, "positives": k, "days": len(set(days)), "mints": len(set(mints)), "prevalence": k / n,
           "brier": b, "brier_ref": br, "log_loss": ll, "log_loss_ref": llr, "bss": bss, "log_loss_skill": lls,
           "auc": None, "average_precision": None, "auc_note": None, "degeneracy": degeneracy(pp)}
    if min(k, n - k) >= AUC_MIN_PER_CLASS:
        out["auc"], out["average_precision"] = K.roc_auc(yy, pp), K.average_precision(yy, pp)
    else:
        out["auc_note"] = f"fewer than {AUC_MIN_PER_CLASS} per class: no AUC or AP"
    if (b - br) * (ll - llr) < 0:
        out["conflict"] = "BRIER_LOGLOSS_CONFLICT"
    else:
        out["conflict"] = None

    def bss_of(idx: np.ndarray) -> float:
        yi, ri = yy[idx], rr[idx]
        den = float(np.sum((ri - yi) ** 2))
        return float("nan") if den == 0 else 1.0 - float(np.sum((pp[idx] - yi) ** 2)) / den

    ivs = {}
    for name, g in (("day", days), ("mint", mints)):
        bs = K.group_bootstrap(g, bss_of, reps=reps, seed=seed)
        ivs[name] = {"ci": list(bs["ci"]), "groups": bs["groups"], "finite": bs["finite"]}
    out["bss_intervals"] = ivs
    w = {nm: (v["ci"][1] - v["ci"][0]) if all(math.isfinite(x) for x in v["ci"]) else math.inf for nm, v in ivs.items()}
    out["bss_governing"] = max(w, key=lambda nm: (w[nm], nm))
    return out


def reliability(y: Any, p: Any) -> dict:
    """The frozen calibration check (ACCEPTANCE calibration) with counts and Wilson bands; a format wrapper of stats."""
    return K.calibration_bins(K.check_labels(y), K.check_probs(p), min_bin=CAL_RULE["min_bin_events"],
                              max_bins=CAL_RULE["max_bins"], in_the_large_only_below=CAL_RULE["in_the_large_only_below_events"])


def check_passed(rel: dict) -> bool:
    return bool(rel["in_the_large_ok"]) and rel["every_bin_ok"] in (True, None)


# ---------------------------------------------------------------- event-rate uncertainty and exchangeability (rules 10, 11)
def base_rate_uncertainty(y: Any, *, days: Sequence[str], mints: Sequence[str], reps: int = BASE_REPS, seed: int = SEED) -> dict:
    yy = K.check_labels(y)
    n, k = int(yy.size), int(yy.sum())
    wl, wh = K.wilson(k, n)
    out = {"n": n, "positives": k, "prevalence": k / n, "wilson": [wl, wh], "days": len(set(days)), "mints": len(set(mints))}
    for name, g in (("day", days), ("mint", mints)):
        bs = K.group_bootstrap(g, lambda idx: float(np.mean(yy[idx])), reps=reps, seed=seed)
        out[f"{name}_block"] = list(bs["ci"])
    wd = out["day_block"][1] - out["day_block"][0]
    wm = out["mint_block"][1] - out["mint_block"][0]
    out["governing"] = "day_block" if wd >= wm else "mint_block"
    gov = out[out["governing"]]
    out["governing_interval"] = gov
    out["width_ratio_to_wilson"] = (gov[1] - gov[0]) / (wh - wl) if wh > wl else None
    return out


def _chi2(groups: np.ndarray, y: np.ndarray, codes: np.ndarray, n_g: np.ndarray) -> float:
    k_g = np.bincount(codes, weights=y, minlength=n_g.size)
    p = y.mean()
    e1, e0 = n_g * p, n_g * (1 - p)
    return float(np.sum((k_g - e1) ** 2 / e1 + ((n_g - k_g) - e0) ** 2 / e0))


def heterogeneity(groups: Sequence[str], y: Any, *, perms: int = BASE_REPS, seed: int = SEED, alpha: float = 0.05) -> dict:
    """Chi-square statistic of the group by outcome table with a label-permutation p (group sizes fixed). A small p rejects
    exchangeability of the event rate across groups; a large p never proves it."""
    yy = K.check_labels(y)
    g = np.asarray([str(x) for x in groups], dtype=object)
    uniq, codes = np.unique(g, return_inverse=True)
    n_g = np.bincount(codes).astype(float)
    out = {"groups": int(uniq.size), "n": int(yy.size), "positives": int(yy.sum()), "permutations": perms, "seed": seed}
    if uniq.size < 2 or yy.sum() in (0, yy.size):
        return {**out, "stat": None, "p": None, "status": "UNDEFINED_ONE_GROUP_OR_ONE_CLASS"}
    obs = _chi2(g, yy, codes, n_g)
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(perms):
        if _chi2(g, rng.permutation(yy), codes, n_g) >= obs - 1e-12:
            hits += 1
    p = (1 + hits) / (perms + 1)
    return {**out, "stat": obs, "p": p,
            "status": "EXCHANGEABILITY_REJECTED" if p < alpha else "EXCHANGEABILITY_NOT_REJECTED_NOT_PROVED"}


def prevalence_shift(y_a: Any, y_b: Any, *, perms: int = BASE_REPS, seed: int = SEED) -> dict:
    """Two-sided label-permutation test of a difference in prevalence between two sets (descriptive)."""
    a, b = K.check_labels(y_a), K.check_labels(y_b)
    allv = np.r_[a, b]
    obs = abs(a.mean() - b.mean())
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(perms):
        z = rng.permutation(allv)
        if abs(z[:a.size].mean() - z[a.size:].mean()) >= obs - 1e-12:
            hits += 1
    return {"n_a": int(a.size), "k_a": int(a.sum()), "p_a": float(a.mean()), "n_b": int(b.size), "k_b": int(b.sum()),
            "p_b": float(b.mean()), "difference": float(b.mean() - a.mean()), "p": (1 + hits) / (perms + 1), "permutations": perms}


# ---------------------------------------------------------------- drift (P39)
def drift_alarm_times(stream: Sequence[tuple[float, float]]) -> list[float]:
    """Page-Hinkley (frozen DRIFT settings) over (time the value became known, champion loss minus reference loss) in time
    order; returns the times at which it alarmed. A NaN raises (P38)."""
    ph = K.PageHinkley(delta=DRIFT["delta"], threshold=DRIFT["threshold"], min_obs=DRIFT["min_obs"], two_sided=DRIFT["two_sided"])
    out = []
    for t, v in sorted(stream, key=lambda tv: tv[0]):
        if ph.update(float(v)):
            out.append(float(t))
    return out


def drift_at(alarms: Sequence[float], decision_time: float) -> bool:
    return any(a <= decision_time for a in alarms)


# ---------------------------------------------------------------- calibration cards
def build_card(target: str, champion: dict | None, rows: Sequence[dict], cutoff: float, *, level: str = "ABSTAIN",
               source: str = "STATISTICAL_MODEL", evidence: dict | None = None, is_fixture: bool = False) -> dict:
    """The calibration artifact of one champion card at `cutoff`. Rows go through `rows_at` (refused if invalid); the fit gate
    and the method rule decide whether a calibrator exists; the evidence (rule 4) decides whether it passed. Status CALIBRATED
    only with a calibrator and a passed check on admissible evidence."""
    if target not in C.PRIMARY:
        raise CalibrationError(f"{target} is not a primary target")
    if level not in LEVELS:
        raise CalibrationError(f"level {level!r} is not one of {LEVELS}")
    if source not in SOURCES:
        raise CalibrationError(f"calibration source {source!r} refused: a behavioral simulation is never calibrated into a "
                               "probability (P27)")
    use = rows_at(rows, cutoff)
    cn = counts(use)
    details: list[str] = []
    if champion is None:
        details.append("NO_CHAMPION")
    gate = fit_gate(cn["n"], cn["k"], cn["days"])
    method = method_for(cn["n"], cn["k"], cn["days"])
    cal = None
    deg = degeneracy([r["score"] for r in use]) if use else None
    if gate:
        details.append("CALIBRATION_SET_TOO_SMALL")
    elif deg and deg["flat"]:
        details.append("DEGENERATE_FLAT_PREDICTIONS")
    else:
        cal = fit_calibrator([r["score"] for r in use], [r["y"] for r in use], method)
    bins = support_bins([r["score"] for r in use], [r["y"] for r in use]) if use else []
    ev = {"status": "NONE", "n": 0, "k": 0, "check": None, "passed": False, "source": None}
    if evidence is not None:
        ev = _evidence(evidence, cal, use)
    if cal is not None:
        if ev["status"] == "NOT_YET_MATURED":
            details.append("CALIBRATION_EVIDENCE_PENDING")
        elif ev["status"] == "ADMISSIBLE" and evidence_gate(ev["n"], ev["k"]):
            details.append("CALIBRATION_EVIDENCE_TOO_SMALL")
        elif ev["status"] == "ADMISSIBLE" and not ev["passed"]:
            details.append("CALIBRATION_CHECK_FAILED")
        elif ev["status"] == "NONE":
            details.append("CALIBRATION_EVIDENCE_TOO_SMALL")
    status = CALIBRATED if (cal is not None and champion is not None and ev["status"] == "ADMISSIBLE" and ev["passed"]
                            and not evidence_gate(ev["n"], ev["k"])) else UNCALIBRATED
    if status == UNCALIBRATED and "NO_CALIBRATOR" not in details:
        details.insert(0, "NO_CALIBRATOR")
    card = {"phase": PHASE, "calibration_version": CALIBRATION_VERSION, "target": target,
            "target_version": C.TARGETS[target]["version"], "registry_sha": C.registry_sha256(), "source": source,
            "champion_model_id": champion.get("model_id") if champion else None,
            "champion_model_sha": champion.get("model_sha") if champion else None,
            "champion_kind": champion.get("kind") if champion else None,
            "champion_training_cutoff_utc": champion.get("training_cutoff_utc") if champion else None,
            "cutoff": float(cutoff), "cutoff_utc": _iso(cutoff),
            "calibration_set": {**cn, "rows_sha": sha([[r["decision_key"], round(float(r["score"]), 12), int(r["y"])] for r in use]),
                                "first_decision_utc": _iso(use[0]["decision_time"]) if use else None,
                                "last_decision_utc": _iso(use[-1]["decision_time"]) if use else None,
                                "rule": "champion out-of-sample rows of the development walk-forward, decided before and matured by the cutoff"},
            "fit_gate": {"rule": FIT_GATE, "shortfalls": gate, "passed": not gate},
            "method_rule": {"venn_abers": VENN_ABERS_GATE, "else": "PLATT", "chosen": method if not gate else None},
            "calibrator": cal, "support_bins": bins, "degeneracy": deg, "evidence": ev, "evidence_rule": EVIDENCE_GATE,
            "status": status, "details": details, "level": level,
            "publishable": status == CALIBRATED and level in PUBLISHABLE_LEVELS,
            "interval_rule": "hull of the calibrator interval and the Wilson 95% interval of the support bin; excludes unmodelled risk",
            "is_fixture": bool(is_fixture)}
    card["card_sha"] = sha({k: v for k, v in card.items() if k != "card_sha"})
    return card


def _evidence(evidence: dict, cal: dict | None, fit_rows: Sequence[dict]) -> dict:
    """Admissible evidence: out-of-sample rows (same row rules, its own cutoff) not in the fit set; or a pending status."""
    st = evidence.get("status")
    if st == "NOT_YET_MATURED":
        return {"status": "NOT_YET_MATURED", "n": 0, "k": 0, "check": None, "passed": False, "source": evidence.get("source")}
    if st != "ADMISSIBLE":
        raise CalibrationError(f"evidence status {st!r} is not one of {EVIDENCE_STATUSES}")
    rows = list(evidence["rows"])
    check_evidence_rows(rows, fit_cutoff=float(evidence["fit_cutoff"]), as_of=float(evidence["cutoff"]))
    fit_keys = {r["decision_key"] for r in fit_rows}
    if any(r["decision_key"] in fit_keys for r in rows):
        raise CalibrationError("calibration evidence overlaps the fit set: a check on the fit rows passes by construction")
    n, k = len(rows), int(sum(int(r["y"]) for r in rows))
    if cal is None or not rows:
        return {"status": "ADMISSIBLE", "n": n, "k": k, "check": None, "passed": False, "source": evidence.get("source")}
    p, _, _ = apply_calibrator(cal, [r["score"] for r in rows])
    rel = reliability([r["y"] for r in rows], p)
    rel = {kk: vv for kk, vv in rel.items() if kk != "note"}
    return {"status": "ADMISSIBLE", "n": n, "k": k, "check": rel, "passed": check_passed(rel), "source": evidence.get("source")}


def verify_card(card: dict) -> dict:
    want = sha({k: v for k, v in card.items() if k != "card_sha"})
    if card.get("card_sha") != want:
        raise CardHashMismatch(f"calibration card {card.get('target')}: content does not match its card_sha")
    if card.get("calibration_version") != CALIBRATION_VERSION:
        raise CalibrationError("calibration card of another version")
    if card.get("registry_sha") != C.registry_sha256():
        raise CalibrationError("calibration card made under another registry fingerprint")
    if card.get("source") not in SOURCES:
        raise CalibrationError("calibration card source is not a statistical model (P27)")
    if card.get("status") == CALIBRATED and (card.get("calibrator") is None or not card["evidence"].get("passed")):
        raise CalibrationError("a CALIBRATED card needs a calibrator and a passed check on admissible evidence")
    if card.get("publishable") != (card.get("status") == CALIBRATED and card.get("level") in PUBLISHABLE_LEVELS):
        raise CalibrationError("publishable flag disagrees with status and level")
    return card


def dumps(card: dict) -> str:
    return json.dumps(card, sort_keys=True, indent=1, allow_nan=False) + "\n"


def loads(text: str) -> dict:
    return verify_card(json.loads(text))


def reference(card: dict, *, support_n: int, support_k: int) -> dict:
    """The `calibration_reference` of a forecast document: allowlisted keys whose numbers are the stored card's (PI-D-022)."""
    ev = card["evidence"]
    return {"calibration_card_sha": card["card_sha"], "calibration_version": card["calibration_version"],
            "method": (card["calibrator"] or {}).get("method"), "level": card["level"], "status": card["status"],
            "holdout_n": int(ev["n"]), "holdout_k": int(ev["k"]), "passed": bool(ev["passed"]),
            "calibration_n": int(card["calibration_set"]["n"]), "calibration_k": int(card["calibration_set"]["k"]),
            "support_n": int(support_n), "support_k": int(support_k)}
