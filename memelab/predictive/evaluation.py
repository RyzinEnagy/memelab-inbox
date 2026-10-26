"""Phase 12: out-of-sample evaluation discipline and the single opening of the retrospective holdout (research only, flag OFF,
imported by no existing module). numpy and the standard library only; no network and no clock (callers pass every time).

Plan: audits/predictive-intelligence/phase_12/validation/WALK_FORWARD_PROTOCOL.md (frozen before this code, PI-D-064). Rules
enforced here:
  - the sealed holdout is opened only by `open_holdout`, after the seal check reported no problem and the three hashes pinned
    in DECISIONS (PI-D-041, PI-D-045) and in `SEAL_PINS`; the opening is logged before the label bytes are decompressed; a
    second opening is refused unless it is declared a REPRODUCTION of the same program (logged by the caller);
  - a holdout row is scored only when its split and maturity recomputed from the registry say HOLDOUT, it is LABELED,
    uncensored, labelled 0 or 1, observed after maturity, and not one of the contacted decisions of ACCEPTANCE (PI-D-021 item 4),
    whose own flag must agree with that list (`holdout_rows`);
  - no card scores a decision made before its training cutoff (RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF, P13), a card whose
    training rows were decided at or after its cutoff or matured after it is refused, and a decision more than the ACCEPTANCE
    model age after the cutoff gets MODEL_STALE instead of a number (`check_card_time`, `score`);
  - the champion is chosen from committed development verdicts only (`champion`), never from a holdout outcome;
  - selection over many candidates is corrected (`holm`, `max_t`, `bonferroni`), and the search size comes from the ledger
    (`ledger_totals`, P22).
No number here is a published probability: calibration (Phase 13) and a champion registry (Phase 16) come first.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import numpy as np

from . import baselines as B
from . import contract as C
from . import labels as L
from . import stats as K

PHASE = "12"
EVAL_VERSION = "evaluation-1"
LABEL_FILE = "holdout_labels.jsonl.gz"
# Recorded outside the seal in DECISIONS PI-D-041 and PI-D-045 (and in PHASE_06_RESULTS.json for the label file).
SEAL_PINS = {"holdout_labels_sha256": "e695500d01014936cf4a4a46f9975dcf9a9ca1351fe067f28ec36117cb82682b",
             "seal_sha256": "d5059baeb07099d5d73d74249d4487e362cb38b2e1dafe974139d2d4d0d25390",
             "seal_json_sha256": "f362ca127baf20e8c3036eca3e11e6d6df4f69b0e0741a4f1b914ada7b2706c2"}
REPLAY_STATUS = "RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF"
STALE = "MODEL_STALE"
HOLDOUT_SKILL = "SKILL_INDICATED_RETROSPECTIVE_HOLDOUT"
DEV_SKILL = "SKILL_INDICATED_DEVELOPMENT_ONLY"
MODES = ("FIRST_OPENING", "REPRODUCTION")
REPS = 20000
SEED = 20261025
ALPHA = 0.05
T2_NOTE = ("possible partial contact with the T2 holdout through first-pass public call counts (PI-D-045 item 6); nobody "
           "computed the bound")
# kinds of the cumulative search ledger (Phases 04 and 07 to 11); an unknown kind stops the count (P22: nothing silently dropped)
CANDIDATE_KINDS = frozenset({"BASELINE", "REFERENCE_PHASE07", "TECHNICAL_MODEL", "TECHNICAL_MODEL_PRIMARY", "ABLATION",
                             "SIMPLE_ONCHAIN_RULE", "ONCHAIN_MODEL", "ONCHAIN_MODEL_PRIMARY", "SIMPLE_ATTENTION_RULE", "SOCIAL_MODEL",
                             "SOCIAL_MODEL_PRIMARY", "SOCIAL_MODEL_BOOSTED", "ANALOG_COHORT", "ANALOG_COHORT_PRIMARY",
                             "SENSITIVITY_LEAVE_ONE_CAMPAIGN_OUT"})
BAKEOFF_KINDS = frozenset({"BAKEOFF_ONLY", "BAKEOFF_PRE_FIX_RUN"})
CONTROL_KINDS = frozenset({"NEGATIVE_CONTROL"})
DEBUG_KINDS = frozenset({"DEBUG_RUN_REAL_DATA"})
OTHER_KINDS = frozenset({"DESCRIPTION_ONLY", "VETO_ALARM_COUNTS_ONLY", "AMPLIFICATION_ALARM_COUNTS_ONLY"})
# Phase 12 rows: evaluations of existing frozen configurations, never new candidates
HOLDOUT_KINDS = frozenset({"PRIMARY_HOLDOUT", "SECONDARY_HOLDOUT", "SENSITIVITY", "DATASET_SHIFT_DESCRIPTIVE", "TRAP_OR_CHECK"})


class EvaluationError(ValueError):
    pass


class SealError(EvaluationError):
    """The seal check failed, a pinned hash differs, or the bytes read are not the sealed label file."""


class HoldoutAlreadyOpened(EvaluationError):
    pass


class RetrospectiveModelNotAvailable(EvaluationError):
    """A model trained after a decision was about to score it (P13, DATA_TIME_CONTRACT)."""
    status = REPLAY_STATUS


class TrainingAfterCutoff(EvaluationError):
    """A card whose training rows were decided at or after its cutoff, or matured after it (P05, P43)."""


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canon(o: Any) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), allow_nan=False)


# ---------------------------------------------------------------- the seal and the single opening
def check_seal_report(report: dict, exit_code: int, decisions_text: str) -> None:
    """`check_seal.py`'s printed report must show no problem and exactly the pinned hashes, each also recorded in DECISIONS."""
    if exit_code != 0:
        raise SealError(f"check_seal.py exited {exit_code}")
    if not isinstance(report, dict) or report.get("problems") != []:
        raise SealError(f"seal problems: {report.get('problems') if isinstance(report, dict) else report!r}")
    for key in ("holdout_labels_sha256", "seal_sha256", "seal_json_sha256"):
        if report.get(key) != SEAL_PINS[key]:
            raise SealError(f"{key} {report.get(key)!r} differs from the pin {SEAL_PINS[key]}")
        if SEAL_PINS[key] not in decisions_text:
            raise SealError(f"{key} pin is not recorded in DECISIONS.md")


def _sealed_label_path(sealed_dir: str | Path) -> Path:
    d = Path(sealed_dir).resolve()
    if not d.as_posix().endswith(L.SEALED_DIR):
        raise SealError(f"{sealed_dir} is not the sealed holdout folder")
    return d / LABEL_FILE


def open_holdout(sealed_dir: str | Path, *, seal_report: dict, seal_exit: int, decisions_text: str, log_path: str | Path,
                 record: dict, mode: str = "FIRST_OPENING") -> tuple[list[dict], dict]:
    """Read the sealed holdout labels once. `record` carries the caller's facts (UTC time, HEAD commit, prediction manifest
    sha256, purpose). FIRST_OPENING writes `log_path` before the bytes are decompressed and refuses when it already exists;
    REPRODUCTION requires the first opening's log and returns its own entry for the caller to keep elsewhere."""
    if mode not in MODES:
        raise EvaluationError(f"mode must be one of {MODES}")
    for k in ("time_utc", "head", "prediction_manifest_sha256", "purpose"):
        if not record.get(k):
            raise EvaluationError(f"opening record needs {k}")
    check_seal_report(seal_report, seal_exit, decisions_text)
    log_path = Path(log_path)
    if mode == "FIRST_OPENING" and log_path.exists():
        raise HoldoutAlreadyOpened(f"{log_path} exists: the holdout was opened before; a rerun is a REPRODUCTION")
    if mode == "REPRODUCTION":
        if not log_path.exists():
            raise EvaluationError("a REPRODUCTION needs the first opening's log")
        first = json.loads(log_path.read_text())
        if not any(e.get("mode") == "FIRST_OPENING" for e in first.get("entries", [])):
            raise EvaluationError("the opening log holds no FIRST_OPENING entry")
    p = _sealed_label_path(Path(sealed_dir))
    raw = p.read_bytes()
    got = sha256_bytes(raw)
    if got != SEAL_PINS["holdout_labels_sha256"]:
        raise SealError(f"the bytes read hash to {got}, not the sealed label file")
    entry = dict(record, mode=mode, label_file=f"{L.SEALED_DIR}/{LABEL_FILE}", label_file_sha256_read=got,
                 seal_report={k: seal_report[k] for k in ("holdout_labels_sha256", "seal_sha256", "seal_json_sha256")},
                 seal_problems=[], eval_version=EVAL_VERSION)
    if mode == "FIRST_OPENING":
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps({"entries": [entry]}, sort_keys=True, indent=1) + "\n")
    rows = [json.loads(line) for line in gzip.decompress(raw).decode().splitlines() if line.strip()]
    return rows, entry


# ---------------------------------------------------------------- the holdout rows that may be scored
def _iso(t: float) -> str:
    import datetime as _dt
    return _dt.datetime.fromtimestamp(float(t), _dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def contacted(mint: str, decision_time: float) -> bool:
    return [mint, _iso(decision_time)] in C.ACCEPTANCE["holdout_contacted"]["decisions"]


def holdout_rows(sealed: Iterable[dict], target: str, *, as_of: float, exclude_contacted: bool = True,
                 include_key_conflict: bool = True) -> tuple[list[dict], dict]:
    """Holdout rows of one target that may be scored, and the counts of everything else (states, censored, contacted, key
    conflicts). Split and maturity are recomputed from the decision time and the registry; a stored row that disagrees, a
    version mismatch or a contacted flag that disagrees with ACCEPTANCE stops the evaluation."""
    if target not in L.TARGETS:
        raise EvaluationError(f"{target} is not a primary target")
    out, counts = [], {"rows": 0, "states": {}, "censored": 0, "contacted_excluded": 0, "contacted_labelled": 0,
                       "key_conflict_excluded": 0, "scorable": 0}
    seen = set()
    for r in sealed:
        if r.get("target") != target:
            continue
        counts["rows"] += 1
        k = r["decision_key"]
        if k in seen:
            raise EvaluationError(f"decision {k[:12]} appears twice for {target}")
        seen.add(k)
        dt = float(r["decision_time"])
        if r.get("split") != "HOLDOUT" or L.split_of(target, dt) != "HOLDOUT":
            raise EvaluationError(f"row {k[:12]}: split {r.get('split')} vs registry {L.split_of(target, dt)}")
        if abs(float(r["label_matures_at"]) - C.label_matures_at(target, dt)) > 1e-6:
            raise EvaluationError(f"row {k[:12]}: stored maturity disagrees with the registry")
        if r.get("target_version") != C.TARGETS[target]["version"] or r.get("labels_version") != L.LABELS_VERSION:
            raise EvaluationError(f"row {k[:12]}: target or label version differs")
        if r.get("registry_sha") != C.registry_sha256():
            raise EvaluationError(f"row {k[:12]}: labelled under another registry fingerprint")
        listed = contacted(r["mint"], dt)
        if bool(r.get("holdout_contacted")) != listed:
            raise EvaluationError(f"row {k[:12]}: contacted flag disagrees with ACCEPTANCE holdout_contacted")
        st = r.get("state")
        counts["states"][st] = counts["states"].get(st, 0) + 1
        if r.get("censored"):
            counts["censored"] += 1
        if st != "LABELED" or r.get("censored") or r.get("label") not in (0, 1):
            continue
        obs = r.get("label_observed_at")
        if obs is None or float(obs) < float(r["label_matures_at"]):
            raise EvaluationError(f"row {k[:12]}: a LABELED row observed before its maturity (P05)")
        C.assert_scorable({"label": r["label"], "target": target, "decision_time": dt, "label_status": st,
                           "label_observed_at": float(obs), "forecast_id": r.get("label_key") or k}, as_of)
        if listed:
            counts["contacted_labelled"] += 1
            if exclude_contacted:
                counts["contacted_excluded"] += 1
                continue
        flags = json.loads(r["flags_json"]) if isinstance(r.get("flags_json"), str) else list(r.get("flags") or [])
        if not include_key_conflict and "KEY_CONFLICT" in flags:
            counts["key_conflict_excluded"] += 1
            continue
        out.append(r)
    counts["scorable"] = len(out)
    return sorted(out, key=lambda r: (float(r["decision_time"]), r["mint"])), counts


def check_identity(label_row: dict, pred_row: dict) -> None:
    """A holdout label joins a prediction only for the same decision: key, chain, mint (byte for byte) and time (P01)."""
    for a in ("decision_key", "chain", "mint"):
        if not isinstance(label_row.get(a), str) or label_row.get(a) != pred_row.get(a):
            raise B.IdentityJoinError(f"{a} differs between the holdout label and the prediction (P01)")
    if float(label_row["decision_time"]) != float(pred_row["decision_time"]):
        raise B.IdentityJoinError("decision time differs between the holdout label and the prediction")


# ---------------------------------------------------------------- model time: no future-trained replay (P13)
def check_card_time(card: dict, decision_times: Sequence[float], *, max_age_s: float | None = None) -> list[str | None]:
    """Refuse a card trained after any decision it would score, or one whose training rows break its own cutoff; return
    MODEL_STALE for decisions more than the ACCEPTANCE model age after the cutoff (None otherwise)."""
    cut = float(card["training_cutoff"])
    early = [t for t in decision_times if float(t) < cut]
    if early:
        raise RetrospectiveModelNotAvailable(f"card {card.get('model_id')} trained to {card.get('training_cutoff_utc')} cannot "
                                             f"score {len(early)} earlier decision(s) ({REPLAY_STATUS}, P13)")
    mt, mm = card.get("max_train_decision_time"), card.get("max_train_label_matures_at")
    if mt is not None and float(mt) >= cut:
        raise TrainingAfterCutoff(f"card {card.get('model_id')}: a training decision at or after its cutoff (P43)")
    if mm is not None and float(mm) > cut:
        raise TrainingAfterCutoff(f"card {card.get('model_id')}: a training label maturing after its cutoff (P05)")
    age = C.ACCEPTANCE["max_model_age_s"] if max_age_s is None else max_age_s
    return [STALE if float(t) - cut > age else None for t in decision_times]


def score(card: dict, examples: Sequence[B.Example], predict: Callable[..., tuple]) -> tuple[np.ndarray, list[str | None]]:
    """Numbers and abstain reasons of one card on examples, through the family's own `predict`, after the time checks."""
    stale = check_card_time(card, [e.decision_time for e in examples])
    out = predict(card, examples)
    p, why = np.array(out[0], float).copy(), list(out[1])
    if len(p) != len(examples):
        raise EvaluationError("predict returned a different number of rows")
    for i, s in enumerate(stale):
        if s:
            p[i], why[i] = float("nan"), s
    fin = p[np.isfinite(p)]
    if fin.size:
        K.check_probs(fin)
    return p, why


# ---------------------------------------------------------------- champion from development verdicts only
def champion(target: str, dev_rows: Sequence[dict], fitted: dict[str, bool]) -> dict:
    """The frozen rule (protocol 4): B2 unless a frozen candidate earned SKILL_INDICATED_DEVELOPMENT_ONLY against B2 in view ALL
    on development data (lowest development Brier among several); no champion when B2 abstains. `fitted` maps candidate ids
    (as in the metric files' model column, prefixed by phase, e.g. P09_M2_OC_LOGIT_B2) to whether the frozen card is fitted."""
    won = []
    for r in dev_rows:
        if r.get("target") != target or r.get("view") != "ALL" or r.get("reference") != "B2" or r.get("verdict") != DEV_SKILL:
            continue
        cid = r["candidate_id"]
        if fitted.get(cid):
            won.append((float(r["brier"]), cid))
    if won:
        won.sort()
        return {"target": target, "champion": won[0][1], "basis": "champion_over_B2 on development data",
                "development_skill_vs_b2": [c for _, c in won]}
    if fitted.get("P07_B2"):
        return {"target": target, "champion": "P07_B2", "basis": "default: no candidate earned champion_over_B2 on development data",
                "development_skill_vs_b2": []}
    return {"target": target, "champion": None, "basis": "B2 abstains at the holdout start: INSUFFICIENT_HISTORY",
            "development_skill_vs_b2": []}


def holdout_verdict(res: dict, p_holm: float | None) -> str:
    """Phase 07's frozen verdict on a holdout evaluation; the skill verdict carries the holdout name."""
    v = B.verdict(res, p_holm)
    return HOLDOUT_SKILL if v == DEV_SKILL else v


# ---------------------------------------------------------------- selection-bias correction
def holm(pvalues: Sequence[float | None]) -> list[float]:
    return K.holm(list(pvalues))


def bonferroni(p: float | None, n: int) -> float | None:
    if p is None or not math.isfinite(p):
        return None
    if n < 1:
        raise EvaluationError("Bonferroni needs at least one configuration")
    return min(1.0, p * n)


def max_t(days: dict[str, Sequence[str]], y: dict[str, Any], ref: dict[str, Any], preds: dict[tuple[str, str], Any], *,
          reps: int = REPS, seed: int = SEED) -> dict[tuple[str, str], dict]:
    """Single-step max-T over every (target, candidate) of `preds` against the per-target reference: the same resampled decision
    days for all targets; statistic BSS* - BSS (centred); adjusted p_j = (1 + #{max_k (BSS*_k - BSS_k) >= BSS_j}) / (reps + 1).
    A replicate where no statistic is defined counts as an exceedance (conservative). Rows without a number are left out of
    that candidate's BSS only."""
    allday = sorted({d for t in days for d in days[t]})
    idx = {t: {d: np.where(np.asarray(days[t], dtype=object) == d)[0] for d in allday} for t in days}
    yy = {t: np.asarray(y[t], float) for t in y}
    rr = {t: np.asarray(ref[t], float) for t in ref}
    keys = sorted(preds)
    obs, masks, pp = {}, {}, {}
    for key in keys:
        t = key[0]
        p = np.asarray(preds[key], float)
        m = np.isfinite(p) & np.isfinite(rr[t])
        masks[key], pp[key] = m, p
        obs[key] = K.brier_skill(yy[t][m], p[m], rr[t][m]) if m.any() else float("nan")
    rng = np.random.default_rng(seed)
    exceed = {key: 0 for key in keys}
    defined = [key for key in keys if math.isfinite(obs[key])]
    for _ in range(reps):
        pick = rng.integers(0, len(allday), size=len(allday))
        rows = {t: np.concatenate([idx[t][allday[i]] for i in pick]) for t in days}
        mx = -math.inf
        for key in defined:
            t = key[0]
            i = rows[t][masks[key][rows[t]]]
            if i.size == 0:
                continue
            den = float(np.sum((rr[t][i] - yy[t][i]) ** 2))
            if den == 0:
                continue
            s = 1.0 - float(np.sum((pp[key][i] - yy[t][i]) ** 2)) / den - obs[key]
            mx = max(mx, s)
        for key in defined:
            if mx == -math.inf or mx >= obs[key]:
                exceed[key] += 1
    return {key: {"bss": obs[key], "p_max_t": ((1 + exceed[key]) / (reps + 1)) if key in defined else None} for key in keys}


# ---------------------------------------------------------------- the search ledger (P22)
def ledger_totals(rows: Sequence[dict]) -> dict:
    """Totals of the cumulative search ledger as fixed in the protocol (7): candidate model configurations are distinct
    (target, candidate) pairs of the model kinds; bake-off configurations are rows; controls are distinct (phase, target,
    candidate, seed); N_search = candidates + bake-off. An unknown kind raises."""
    by_phase: dict[str, int] = {}
    cand, ctrl = set(), set()
    bake = debug = other = holdout = 0
    for r in rows:
        by_phase[r["phase"]] = by_phase.get(r["phase"], 0) + 1
        k = r["kind"]
        if k in HOLDOUT_KINDS:
            holdout += 1
        elif k in CANDIDATE_KINDS:
            cand.add((r["target"], r["candidate"]))
        elif k in BAKEOFF_KINDS:
            bake += 1
        elif k in CONTROL_KINDS:
            ctrl.add((r["phase"], r["target"], r["candidate"], r["seed"]))
        elif k in DEBUG_KINDS:
            debug += 1
        elif k in OTHER_KINDS:
            other += 1
        else:
            raise EvaluationError(f"ledger kind {k!r} is not classified (P22: nothing is dropped silently)")
    return {"rows": len(rows), "rows_by_phase": dict(sorted(by_phase.items())), "candidate_configurations": len(cand),
            "bakeoff_configurations": bake, "negative_control_fits": len(ctrl), "debug_runs": debug, "other_rows": other,
            "holdout_evaluation_rows": holdout, "n_search": len(cand) + bake}


# ---------------------------------------------------------------- small helpers for the report
def prevalence(y: Sequence[int]) -> dict:
    n, k = len(y), int(sum(y))
    lo, hi = K.wilson(k, n)
    return {"n": n, "positives": k, "prevalence": (k / n) if n else None, "wilson": [lo, hi]}


def shadow_criteria(res: dict) -> dict:
    """Which SHADOW criteria of ACCEPTANCE hold on this holdout evaluation (information for Phases 13 and 16, never a promotion
    here): count gates, calibration in the large and in every bin, BSS point at least 0."""
    a = C.ACCEPTANCE
    n, k = int(res.get("n_with_number") or 0), int(res.get("positives") or 0)
    counts = n >= a["min_holdout_events"] and k >= a["min_holdout_per_class"] and n - k >= a["min_holdout_per_class"]
    cal = res.get("calibration") or {}
    cal_ok = bool(cal.get("in_the_large_ok")) and cal.get("every_bin_ok") in (True, None)
    bss = res.get("bss")
    bss_ok = bss is not None and math.isfinite(bss) and bss >= a["promotion"]["SHADOW"]["bss_point_min"]
    return {"count_gates": counts, "calibration": cal_ok, "bss_point_at_least_0": bss_ok, "all": counts and cal_ok and bss_ok,
            "promotion": "NONE_IN_PHASE_12"}
