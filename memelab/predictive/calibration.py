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
REGISTRY_LEVELS = ("VALIDATED_EXPERIMENTAL",)    # a level a card cannot give itself: refused until the Phase 16 registry exists
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
def decide(cn: dict, *, champion_present: bool, flat: bool, calibrator_method: str | None, ev: dict, level: str) -> dict:
    """The gate decisions of a card from its own recorded facts (repair pass 2, PI-D-070, skeptic M2 and M4). `build_card`
    writes exactly this and `verify_card` recomputes it, so a card cannot claim more than its counts allow."""
    gate = fit_gate(int(cn["n"]), int(cn["k"]), int(cn["days"]))
    chosen = method_for(int(cn["n"]), int(cn["k"]), int(cn["days"])) if not gate else None
    details: list[str] = []
    if not champion_present:
        details.append("NO_CHAMPION")
    if gate:
        details.append("CALIBRATION_SET_TOO_SMALL")
    elif flat:
        details.append("DEGENERATE_FLAT_PREDICTIONS")
    has_cal = calibrator_method is not None
    ev_flat = bool((ev.get("degeneracy") or {}).get("flat"))
    ev_small = bool(evidence_gate(int(ev.get("n") or 0), int(ev.get("k") or 0)))
    if has_cal:
        if ev["status"] == "NOT_YET_MATURED":
            details.append("CALIBRATION_EVIDENCE_PENDING")
        elif ev["status"] == "NONE" or ev_small:
            details.append("CALIBRATION_EVIDENCE_TOO_SMALL")
        elif ev_flat:
            details.append("DEGENERATE_FLAT_PREDICTIONS")
        elif not ev["passed"]:
            details.append("CALIBRATION_CHECK_FAILED")
    ok = (has_cal and champion_present and ev["status"] == "ADMISSIBLE" and bool(ev["passed"]) and not ev_small and not ev_flat
          and ev.get("source") in EVIDENCE_SOURCES)
    status = CALIBRATED if ok else UNCALIBRATED
    if status == UNCALIBRATED:
        details.insert(0, "NO_CALIBRATOR")
    return {"fit_gate": {"rule": FIT_GATE, "shortfalls": gate, "passed": not gate},
            "method_rule": {"venn_abers": VENN_ABERS_GATE, "else": "PLATT", "chosen": chosen},
            "status": status, "details": details, "publishable": status == CALIBRATED and level in PUBLISHABLE_LEVELS}


def build_card(target: str, champion: dict | None, rows: Sequence[dict], cutoff: float, *, level: str = "ABSTAIN",
               source: str = "STATISTICAL_MODEL", evidence: dict | None = None, is_fixture: bool = False) -> dict:
    """The calibration artifact of one champion card at `cutoff`. Rows go through `rows_at` (refused if invalid); the fit gate
    and the method rule decide whether a calibrator exists; the evidence (rule 4) decides whether it passed. Status CALIBRATED
    only with a calibrator and a passed, non-flat check on admissible prospective evidence (`decide`)."""
    if target not in C.PRIMARY:
        raise CalibrationError(f"{target} is not a primary target")
    if level not in LEVELS:
        raise CalibrationError(f"level {level!r} is not one of {LEVELS}")
    if level in REGISTRY_LEVELS:
        raise CalibrationError(f"level {level} needs the Phase 16 promotion registry, which does not exist yet (PI-D-070)")
    if source not in SOURCES:
        raise CalibrationError(f"calibration source {source!r} refused: a behavioral simulation is never calibrated into a "
                               "probability (P27)")
    use = rows_at(rows, cutoff)
    cn = counts(use)
    gate = fit_gate(cn["n"], cn["k"], cn["days"])
    method = method_for(cn["n"], cn["k"], cn["days"])
    cal = None
    deg = degeneracy([r["score"] for r in use]) if use else None
    if not gate and not (deg and deg["flat"]):
        cal = fit_calibrator([r["score"] for r in use], [r["y"] for r in use], method)
    bins = support_bins([r["score"] for r in use], [r["y"] for r in use]) if use else []
    ev = {"status": "NONE", "n": 0, "k": 0, "check": None, "passed": False, "source": None, "as_of": None, "as_of_utc": None,
          "degeneracy": None, "score_range": None}
    if evidence is not None:
        ev = _evidence(evidence, cal, use, cutoff)
    dec = decide(cn, champion_present=champion is not None, flat=bool(deg and deg["flat"]),
                 calibrator_method=(cal or {}).get("method"), ev=ev, level=level)
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
                                "last_decision_time": float(use[-1]["decision_time"]) if use else None,
                                "last_label_matures_at": max(float(r["label_matures_at"]) for r in use) if use else None,
                                "rule": "champion out-of-sample rows of the development walk-forward, decided before and matured by the cutoff"},
            "fit_gate": dec["fit_gate"], "method_rule": dec["method_rule"],
            "calibrator": cal, "support_bins": bins, "degeneracy": deg, "evidence": ev, "evidence_rule": EVIDENCE_GATE,
            "status": dec["status"], "details": dec["details"], "level": level, "publishable": dec["publishable"],
            "available_at": max(float(cutoff), float(ev["as_of"])) if ev.get("as_of") is not None else float(cutoff),
            "interval_rule": "hull of the calibrator interval and the Wilson 95% interval of the support bin; excludes unmodelled risk",
            "is_fixture": bool(is_fixture)}
    card["card_sha"] = sha({k: v for k, v in card.items() if k != "card_sha"})
    return card


EVIDENCE_SOURCES = ("PROSPECTIVE_HOLDOUT",)       # the opened retrospective holdout is spent (PI-D-065): never evidence


def _evidence(evidence: dict, cal: dict | None, fit_rows: Sequence[dict], fit_cutoff: float) -> dict:
    """Admissible evidence: prospective out-of-sample rows (own maturity time `cutoff`) not in the fit set, from the
    prospective holdout only; or a pending status. Records its as-of time, its own degeneracy and score range (PI-D-070)."""
    st = evidence.get("status")
    src = evidence.get("source")
    if st == "NOT_YET_MATURED":
        return {"status": "NOT_YET_MATURED", "n": 0, "k": 0, "check": None, "passed": False, "source": src, "as_of": None,
                "as_of_utc": None, "degeneracy": None, "score_range": None}
    if st != "ADMISSIBLE":
        raise CalibrationError(f"evidence status {st!r} is not one of {EVIDENCE_STATUSES}")
    if src not in EVIDENCE_SOURCES:
        raise CalibrationError(f"evidence source {src!r} refused: only {EVIDENCE_SOURCES} (the retrospective holdout is spent, PI-D-065)")
    if float(evidence["fit_cutoff"]) != float(fit_cutoff):
        raise CalibrationError("evidence fit_cutoff differs from the card's cutoff")
    rows = list(evidence["rows"])
    as_of = float(evidence["cutoff"])
    check_evidence_rows(rows, fit_cutoff=float(fit_cutoff), as_of=as_of)
    fit_keys = {r["decision_key"] for r in fit_rows}
    if any(r["decision_key"] in fit_keys for r in rows):
        raise CalibrationError("calibration evidence overlaps the fit set: a check on the fit rows passes by construction")
    n, k = len(rows), int(sum(int(r["y"]) for r in rows))
    base = {"status": "ADMISSIBLE", "n": n, "k": k, "check": None, "passed": False, "source": src, "as_of": as_of,
            "as_of_utc": _iso(as_of), "degeneracy": None, "score_range": None}
    if not rows:
        return base
    sc = [float(r["score"]) for r in rows]
    base["degeneracy"] = degeneracy(sc)
    base["score_range"] = [min(sc), max(sc)]
    if cal is None:
        return base
    p, _, _ = apply_calibrator(cal, sc)
    rel = reliability([r["y"] for r in rows], p)
    rel = {kk: vv for kk, vv in rel.items() if kk != "note"}
    base["check"] = rel
    base["passed"] = check_passed(rel) and not base["degeneracy"]["flat"]
    return base


def verify_card(card: dict) -> dict:
    """Refuse a card whose content differs from its sha, or whose recorded decisions are not what its own recorded facts allow:
    the fit gate, the method, the evidence source, maturity and gate, the check, the status, the details and the publishable
    flag are recomputed (repair pass 2, PI-D-070, skeptic M2). Full authenticity of the facts needs the Phase 16 registry."""
    want = sha({k: v for k, v in card.items() if k != "card_sha"})
    if card.get("card_sha") != want:
        raise CardHashMismatch(f"calibration card {card.get('target')}: content does not match its card_sha")
    if card.get("calibration_version") != CALIBRATION_VERSION:
        raise CalibrationError("calibration card of another version")
    if card.get("registry_sha") != C.registry_sha256():
        raise CalibrationError("calibration card made under another registry fingerprint")
    if card.get("source") not in SOURCES:
        raise CalibrationError("calibration card source is not a statistical model (P27)")
    if card.get("level") not in LEVELS:
        raise CalibrationError("calibration card level is not one of the frozen levels")
    if card.get("level") in REGISTRY_LEVELS:
        raise CalibrationError(f"level {card['level']} needs the Phase 16 promotion registry, which does not exist yet (PI-D-070)")
    cn = card["calibration_set"]
    n, k, days = int(cn["n"]), int(cn["k"]), int(cn["days"])
    if not (0 <= k <= n and int(cn["negatives"]) == n - k and 0 <= days <= n and (days > 0) == (n > 0)):
        raise CalibrationError("calibration set counts are inconsistent")
    cut = float(card["cutoff"])
    if n:
        if cn.get("last_decision_time") is None or not float(cn["last_decision_time"]) < min(cut, HOLDOUT_START):
            raise CalibrationError("calibration rows are not all development rows decided before the cutoff (spent or later rows)")
        try:
            first, last = C.parse_utc(cn["first_decision_utc"]), C.parse_utc(cn["last_decision_utc"])
        except (C.ContractError, KeyError) as e:
            raise CalibrationError(f"calibration set times unreadable: {e}")
        if _iso(float(cn["last_decision_time"])) != cn["last_decision_utc"] or not first <= last < min(cut, HOLDOUT_START):
            raise CalibrationError("calibration set times disagree or lie outside the development window (spent or later rows)")
        if cn.get("last_label_matures_at") is None or not float(cn["last_label_matures_at"]) <= min(cut, HOLDOUT_START):
            raise CalibrationError("a calibration label matures after the cutoff or the holdout start")
        if sum(int(b["n"]) for b in card["support_bins"]) != n or sum(int(b["k"]) for b in card["support_bins"]) != k:
            raise CalibrationError("support bins do not add up to the calibration set")
    ev = card["evidence"]
    if ev.get("status") not in EVIDENCE_STATUSES:
        raise CalibrationError("evidence status unknown")
    if ev["status"] == "ADMISSIBLE":
        if ev.get("source") not in EVIDENCE_SOURCES:
            raise CalibrationError(f"evidence source {ev.get('source')!r} refused: spent or unknown evidence (PI-D-065)")
        if ev.get("as_of") is None or float(ev["as_of"]) < max(cut, PROSPECTIVE_START):
            raise CalibrationError("evidence has no maturity time after the calibrator's cutoff and the prospective start")
        chk = ev.get("check")
        if ev.get("passed") and (chk is None or int(chk.get("n", -1)) != int(ev["n"]) or not check_passed(chk)):
            raise CalibrationError("evidence marked passed without a passing check on its own rows")
        deg = ev.get("degeneracy")
        if ev.get("passed") and (deg is None or deg.get("flat") or not (float(deg["ptp"]) > FLAT_PTP)):
            raise CalibrationError("flat or unchecked evidence marked passed (rule 8)")
    elif ev.get("passed") or ev.get("n") or ev.get("k"):
        raise CalibrationError("pending or missing evidence carries counts or a pass")
    calm = (card.get("calibrator") or {}).get("method")
    deg = card.get("degeneracy") or {}
    dec = decide(cn, champion_present=card.get("champion_model_sha") is not None, flat=bool(deg.get("flat")),
                 calibrator_method=calm, ev=ev, level=card["level"])
    if card["fit_gate"] != dec["fit_gate"] or card["method_rule"] != dec["method_rule"]:
        raise CalibrationError("the fit gate or method recorded on the card is not what its counts give")
    if calm is not None and (calm != dec["method_rule"]["chosen"] or deg.get("flat")):
        raise CalibrationError("a calibrator exists where the gate, the method rule or rule 8 allows none or another")
    if calm == "VENN_ABERS":
        pairs = card["calibrator"]["params"]["calibration"]
        if len(pairs) != n or int(sum(int(q[1]) for q in pairs)) != k:
            raise CalibrationError("Venn-Abers calibration pairs do not match the calibration set counts")
    if card.get("status") != dec["status"] or card.get("details") != dec["details"] or card.get("publishable") != dec["publishable"]:
        raise CalibrationError(f"status, details or publishable flag differ from what the card's facts allow ({dec['status']})")
    want_av = max(cut, float(ev["as_of"])) if ev.get("as_of") is not None else cut
    if float(card.get("available_at", -1)) != want_av:
        raise CalibrationError("available_at is not the later of the cutoff and the evidence maturity")
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
