"""Phase 16: registry-1, the model registry and the champion policy (research only, flag OFF, imported by no existing module).
numpy, the standard library, `contract` and `stats` only; no network and no clock (callers pass every time).

Pre-registration: audits/predictive-intelligence/phase_16/ACCEPTANCE_CHECKLIST.md (rules 1 to 14) and PI-D-085.
  - every frozen card becomes one immutable, hash-addressed entry (`make_entry`, `verify_entry`): its id is the sha256 of the
    canonical entry, so a changed byte refuses it; the entry holds the card's model sha and file sha256, the feature set,
    the training cutoff, the label and target versions, the dataset sha, the calibration card, the evidence, the minimum
    support, the risk flags, the identical-inference hash and its level;
  - a level is never given, it is recomputed from the entry's facts (`promotion_decision`): the frozen ACCEPTANCE promotion
    table, plus admissible prospective calibration for anything above ABSTAIN because the opened retrospective holdout can
    no longer support a promotion on its own (PI-D-065, PI-D-069); reference baselines that reach no level are ABSTAIN,
    every other candidate NO_GO (NO_INCREMENTAL_PREDICTIVE_EDGE);
  - a target is served by a pinned champion only at SHADOW or VALIDATED_EXPERIMENTAL; otherwise it is NO_VIABLE_CHAMPION
    (abstain, model `not_selected`) with B0 and B2 pinned beside it as references that are never published;
  - pins live in an append-only, sha-chained event log (`chain_events`, `append_events`, `read_log`) and resolve as of a
    decision time (`resolve`); compatibility (P46), staleness and drift (P39), the identical-inference hash (P38) and
    rollback (`rollback_event`) decide whether a pinned champion may be used (`serve`);
  - ensembles only from chronologically out-of-fold member rows, never in-sample, never with two members reading the same
    evidence source (`check_members`, `out_of_fold_rows`, `check_stack_rows`, `stack_gate`, `ensemble_decision`).
The isolation tests of Phases 09 to 15 forbid any other lab module to import the evaluation, calibration, abstention and
family modules; card loading, inference and calibration-card checks therefore come from the caller, and this module
re-hashes what it is given. Nothing here publishes a probability: `abstention.forecast_result` stays the only document path.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import numpy as np

from . import contract as C
from . import stats as K

PHASE = "16"
REGISTRY_VERSION = "registry-1"
ACC = C.ACCEPTANCE
LEVELS = ("ABSTAIN", "SHADOW", "VALIDATED_EXPERIMENTAL", "NO_GO")
PUBLISHABLE_LEVELS = ("SHADOW", "VALIDATED_EXPERIMENTAL")
ROLES = ("REFERENCE_BASELINE", "CANDIDATE")
REFERENCE_KINDS = ("B0", "B2")                       # ACCEPTANCE: the baselines a later model must not lose to / must beat
REFERENCE_NAMES = {"B0": "base_rate", "B2": "simple_model"}
MODES = ("CHAMPION", "NO_VIABLE_CHAMPION")
EVENT_KINDS = ("REGISTER", "PIN", "ROLLBACK", "ENSEMBLE_DECISION")
GENESIS = "0" * 64
NOT_SELECTED = "not_selected"
SOURCE = "STATISTICAL_MODEL"
SIMULATION_MARKERS = ("mirofish", "oasis", "simulation", "simulated", "agent", "behavioral", "persona", "swarm")
FAMILY_PHASES = ("07", "08", "09", "10", "11")      # the frozen card families; the caller reads each card's module version
PHASE07_FAMILY_VERSION = "baselines-phase07"
CALIBRATED = "CALIBRATED"
SELECTION_SURVIVES = "SURVIVES_SELECTION_CORRECTION"
FIRST_OPENING = "FIRST_OPENING"
ALPHA = round(1 - ACC["bootstrap"]["conf"], 12)          # 0.05 exactly; p = 0.05 is not below it

# model-level states and their thresholds (rule 8); request-level OOD conditions stay in abstention-1
MODEL_STALE = "MODEL_STALE"
DRIFT_ALERT = "DRIFT_ALERT"
MODEL_NOT_PROMOTED = "MODEL_NOT_PROMOTED"
OUT_OF_DISTRIBUTION = "OUT_OF_DISTRIBUTION"
NOT_AVAILABLE_AS_OF = "RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF"
FEATURE_SCHEMA_MISMATCH = "FEATURE_SCHEMA_MISMATCH"
INCOMPATIBLE = "MODEL_INCOMPATIBLE_RETRAIN_REQUIRED"
INFERENCE_MISMATCH = "INFERENCE_MISMATCH"
ENTRY_REFUSED = "ENTRY_REFUSED"
FACTS_MISMATCH = "FACTS_MISMATCH"
FACTS_NOT_VERIFIED = "FACTS_NOT_VERIFIED"
INFERENCE_NOT_CHECKED = "INFERENCE_NOT_CHECKED"
FIXTURE_IN_REAL_REGISTRY = "FIXTURE_IN_REAL_REGISTRY"
FACTS_CHECKED = "REBUILT_FROM_COMMITTED_FILES"
FIXTURE_FACTS_NOT_CHECKED = "FIXTURE_FACTS_NOT_CHECKED"
TRAINING_AFTER_CUTOFF = "TRAINING_ROWS_AFTER_CUTOFF"   # CP20-1 (F20-06): the replay guard's rule, on the serving path too
THRESHOLDS = {
    MODEL_STALE: {"max_model_age_s": ACC["max_model_age_s"], "rule": "decision time minus training cutoff above max_model_age_s",
                  "contract_reason": "MODEL_STALE"},
    NOT_AVAILABLE_AS_OF: {"rule": "decision time before the training cutoff", "contract_reason": "MODEL_NOT_SELECTED"},
    DRIFT_ALERT: {"detector": "Page-Hinkley on matured champion Brier loss minus B0 loss, in maturity order", "delta": 0.005,
                  "threshold": 2.0, "min_obs": 30, "two_sided": False, "rule": "an alarm at or before the decision",
                  "contract_reason": "DRIFT_ALERT"},
    MODEL_NOT_PROMOTED: {"rule": "registry level not SHADOW or VALIDATED_EXPERIMENTAL", "contract_reason": "MODEL_NOT_SELECTED"},
    OUT_OF_DISTRIBUTION: {"conditions": ["MISSING_REQUIRED_INPUT", "FEATURE_OUT_OF_RANGE", "SCORE_OUTSIDE_CALIBRATION_RANGE"],
                          "feature_z_max": 4.0, "rule": "per request, through abstention-1", "contract_reason": "OOD"},
    FEATURE_SCHEMA_MISMATCH: {"rule": "the request's feature set sha or version differs from the entry's",
                              "contract_reason": "FEATURE_SCHEMA_MISMATCH"},
    INCOMPATIBLE: {"rule": "the running code's feature set, family version, target registry or labels version differs from the "
                           "entry's (a change without retrain, P46)", "contract_reason": "FEATURE_SCHEMA_MISMATCH"},
    INFERENCE_MISMATCH: {"rule": "the recomputed identical-inference hash differs from the pinned one", "contract_reason": "MODEL_NOT_SELECTED"},
    INFERENCE_NOT_CHECKED: {"rule": "serve was not given the champion's recomputed inference rows", "contract_reason": "MODEL_NOT_SELECTED"},
    FACTS_NOT_VERIFIED: {"rule": "serve was not given the repository root, so the champion's facts could not be rebuilt",
                         "contract_reason": "MODEL_NOT_SELECTED"},
    FACTS_MISMATCH: {"rule": "the champion's facts differ from what the committed files give", "contract_reason": "MODEL_NOT_SELECTED"},
    FIXTURE_IN_REAL_REGISTRY: {"rule": "a fixture champion outside a fixture run", "contract_reason": "MODEL_NOT_SELECTED"},
}
RETRAIN = {
    MODEL_STALE: "RETRAIN_PLAN_REQUIRED: a new frozen card from a plan committed before its evaluation data are read",
    DRIFT_ALERT: "RETRAIN_AND_HUMAN_REVIEW: the model is not used until a reviewed retrain is registered",
    INCOMPATIBLE: "RETRAIN_REQUIRED_BEFORE_ANY_USE: the code changed under the model",
    FEATURE_SCHEMA_MISMATCH: "REQUEST_REFUSED: recompute the inputs with the model's feature set, or retrain",
    INFERENCE_MISMATCH: "ROLLBACK_AND_INVESTIGATE: the model no longer gives its recorded outputs",
    FACTS_MISMATCH: "ROLLBACK_AND_INVESTIGATE: the entry's facts are not what its committed sources say",
    INFERENCE_NOT_CHECKED: "REQUEST_REFUSED: recompute the champion's probe outputs and pass them",
    FACTS_NOT_VERIFIED: "REQUEST_REFUSED: pass the repository root so the registry can rebuild the facts",
    FIXTURE_IN_REAL_REGISTRY: "ROLLBACK_AND_INVESTIGATE: a fixture entry was pinned outside a fixture run",
    "TARGET_OR_LABEL_VERSION_CHANGE": "RETRAIN_AND_REEVALUATE: a new target or label version is a new model",
}
RETRAIN_POLICY = {"automatic": False, "reason": "no scheduled job is approved (PI-D-005); a retrain is a phase step with a plan",
                  "new_entry_level": "ABSTAIN", "inherits_level": False, "max_model_age_s": ACC["max_model_age_s"],
                  "triggers": RETRAIN, "rollback": "previous pinned champion whose checks hold, else NO_VIABLE_CHAMPION"}

# evidence sources of the columns an ensemble member may read (rule 12); a column outside this map refuses the member
EVIDENCE_SOURCES = {
    "thesis_log1p_liquidity_usd": ("LAB_THESIS_MARKET_ROW",),
    "thesis_log1p_mcap_usd": ("LAB_THESIS_MARKET_ROW",),
    "thesis_log1p_vol_24h_usd": ("LAB_THESIS_MARKET_ROW",),
    "log1p_token_age_days": ("LAB_TOKEN_AGE",),
    "thesis_fatal_present": ("LAB_FATAL_FLAGS",),
    "thesis_score": ("LAB_100_POINT_SCORE",),
    "oc_structural_fatal": ("LAB_FATAL_FLAGS",),
    "oc_distribution_fatal": ("LAB_FATAL_FLAGS",),
    "oc_lp_risk_ord": ("LAB_LP_READING",),
    "oc_lp_locked_pct": ("LAB_LP_READING",),
    "oc_exit_cap_share": ("LAB_EXIT_CAPACITY_READING", "LAB_THESIS_MARKET_ROW"),
    "oc_largest_unexplained_pct": ("LAB_HOLDER_DISTRIBUTION",),
    "thesis_adj_top10_pct": ("LAB_HOLDER_DISTRIBUTION",),
    "oc_wash_ord": ("LAB_FLOW_SCREEN", "LAB_MANIPULATION_SCREEN"),
    "sc_attention_trend_ord": ("LAB_ATTENTION_PROXIES",),
    "sc_attention_suspect": ("LAB_ATTENTION_PROXIES", "LAB_MANIPULATION_SCREEN"),
    "sc_narrative_strength": ("LAB_ATTENTION_PROXIES",),
    "sc_manipulation_ord": ("LAB_ATTENTION_PROXIES", "LAB_MANIPULATION_SCREEN"),
    "sc_lifecycle_late": ("LAB_LIFECYCLE_CLASSIFIER",),
    "sc_channels_n": ("LAB_CHANNEL_LINKS",),
}
LOGIT_CLIP = ACC["secondary_scores"]["log_loss_clip"]
STACK_GATE = {"min_events": ACC["min_train_events"], "min_per_class": ACC["min_train_per_class"], "min_days": ACC["min_effective_days"]}

ENTRY_KEYS = ("registry_version", "entry_kind", "is_fixture", "target", "target_version", "target_registry_sha", "family",
              "model_id", "model_sha", "card_path", "card_file_sha256", "feature_set_sha", "feature_version", "family_version",
              "training_cutoff", "training_cutoff_utc", "max_train_decision_time", "max_train_label_matures_at", "n_train",
              "k_train", "labels_version", "label_set_sha", "data_snapshot_sha", "fitted", "abstain_reason", "source",
              "calibration", "facts", "evidence", "min_support", "risk_flags", "role", "promotion", "registry_status",
              "publishable", "inference", "code", "retrain_policy", "thresholds", "registered_as_of_utc", "entry_id")


class RegistryError(ValueError):
    status = ENTRY_REFUSED


class EntryHashMismatch(RegistryError):
    status = "ENTRY_HASH_MISMATCH"


class LevelMismatch(RegistryError):
    status = "LEVEL_MISMATCH"


class BehavioralNotAModel(RegistryError):
    status = "BEHAVIORAL_NOT_A_MODEL"


class MalformedScore(RegistryError):
    status = "MALFORMED_SCORE"


class InferenceMismatchError(RegistryError):
    status = INFERENCE_MISMATCH


class FactsMismatchError(RegistryError):
    status = FACTS_MISMATCH


class LogError(RegistryError):
    status = "LOG_REFUSED"


class PinRefused(RegistryError):
    status = "PIN_REFUSED"


class HoldoutInputRefused(RegistryError):
    status = "HOLDOUT_INPUT_REFUSED"


class DoubleCountedEvidence(RegistryError):
    status = "DOUBLE_COUNTED_EVIDENCE"


class UndeclaredColumn(RegistryError):
    status = "UNDECLARED_EVIDENCE_SOURCE"


class NotOutOfFold(RegistryError):
    status = "NOT_OUT_OF_FOLD"


class InSampleStacking(RegistryError):
    status = "IN_SAMPLE_STACKING"


def canon(o: Any) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(o: Any) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _iso(t: float) -> str:
    import datetime as _dt
    return _dt.datetime.fromtimestamp(float(t), _dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fin(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _int(x: Any) -> int:
    return int(x) if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else 0


def _behavioral(*texts: Any) -> bool:
    low = " ".join(str(t or "").lower() for t in texts)
    return any(m in low for m in SIMULATION_MARKERS)


# ---------------------------------------------------------------- promotion (rule 3)
def _counts_ok(n: int, k: int, min_n: int, min_k: int) -> bool:
    return n >= min_n and k >= min_k and n - k >= min_k


def promotion_decision(facts: dict) -> dict:
    """The level an entry's facts allow. Never a given level: SHADOW and VALIDATED_EXPERIMENTAL follow the frozen ACCEPTANCE
    table, read on a FIRST_OPENING retrospective evaluation (a POST_OPENING fact can only block), plus a CALIBRATED card on
    admissible prospective evidence (PI-D-065, PI-D-069). Reference baselines that reach no level are ABSTAIN; every other
    candidate NO_GO."""
    reasons: list[str] = []
    role = facts.get("role")
    if role not in ROLES:
        raise RegistryError(f"role {role!r} is not one of {ROLES}")
    if facts.get("source") != SOURCE or _behavioral(facts.get("kind"), facts.get("model_id")):
        raise BehavioralNotAModel("a behavioral simulation is never a registry model (P27, MIROFISH_NO_GO)")
    tests = facts.get("tests") or {}
    if not all(tests.get(k) is True for k in ("leakage", "provenance", "contract")):
        reasons.append("TESTS_NOT_PASSED")
    if not facts.get("fitted"):
        reasons.append("NOT_FITTED")
    tr = facts.get("training") or {}
    if not _counts_ok(_int(tr.get("n")), _int(tr.get("k")), ACC["min_train_events"], ACC["min_train_per_class"]):
        reasons.append("TRAINING_BELOW_MINIMUM")
    ret = facts.get("retrospective") or {}
    if ret.get("evaluation") != FIRST_OPENING:
        reasons.append("NO_FIRST_OPENING_RETROSPECTIVE_EVALUATION" if not ret.get("evaluation") else
                       f"RETROSPECTIVE_EVALUATION_{ret.get('evaluation')}_CANNOT_PROMOTE")
    else:
        if not _counts_ok(_int(ret.get("n")), _int(ret.get("k")), ACC["min_holdout_events"], ACC["min_holdout_per_class"]):
            reasons.append("RETROSPECTIVE_BELOW_MINIMUM")
        # every-bin result may be absent only below 40 events, where the frozen check is in the large only (CP16-2, m3)
        bins_ok = ret.get("calibration_every_bin_ok") is True or (
            ret.get("calibration_every_bin_ok") is None and _int(ret.get("n")) < ACC["calibration"]["in_the_large_only_below_events"])
        if not (ret.get("calibration_in_the_large_ok") is True and bins_ok):
            reasons.append("RETROSPECTIVE_CALIBRATION_FAILED")
        if not (_fin(ret.get("bss")) and float(ret["bss"]) >= ACC["promotion"]["SHADOW"]["bss_point_min"]):
            reasons.append("RETROSPECTIVE_BSS_BELOW_0")
    if any(s == "FAILS_SELECTION_CORRECTION" for s in facts.get("post_opening_states") or []):
        reasons.append("POST_OPENING_FAILS")
    cal = facts.get("calibration") or {}
    if not (cal.get("status") == CALIBRATED and _counts_ok(_int(cal.get("evidence_n")), _int(cal.get("evidence_k")),
                                                          ACC["min_holdout_events"], ACC["min_holdout_per_class"])
            and cal.get("evidence_source") == "PROSPECTIVE_HOLDOUT"):
        reasons.append("NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION")
    shadow = not reasons
    ve_reasons: list[str] = []
    if shadow:
        ve = ACC["promotion"]["VALIDATED_EXPERIMENTAL"]
        if not (_fin(ret.get("bss_lo")) and float(ret["bss_lo"]) > ve["bss_lower_bound_gt"] and _fin(ret.get("p_holm"))
                and float(ret["p_holm"]) < ALPHA):
            ve_reasons.append("RETROSPECTIVE_LOWER_BOUND_NOT_ABOVE_0")
        pro = facts.get("prospective") or {}
        if pro.get("status") != "ADMISSIBLE" or not _counts_ok(_int(pro.get("n")), _int(pro.get("k")), ve["prospective_min_events"],
                                                                ACC["min_holdout_per_class"]):
            ve_reasons.append("PROSPECTIVE_BELOW_MINIMUM")
        elif not (_fin(pro.get("bss_lo")) and float(pro["bss_lo"]) > ve["bss_lower_bound_gt"] and _fin(pro.get("p_holm"))
                  and float(pro["p_holm"]) < ALPHA):
            ve_reasons.append("PROSPECTIVE_LOWER_BOUND_NOT_ABOVE_0")
        b2 = facts.get("vs_b2") or {}
        if facts.get("kind") != "B2":
            if not (_fin(b2.get("brier_minus_b2")) and float(b2["brier_minus_b2"]) <= 0.0):
                ve_reasons.append("WORSE_THAN_B2")
            if not (_fin(b2.get("lower_bound_b2_minus_brier")) and float(b2["lower_bound_b2_minus_brier"]) > 0.0):
                ve_reasons.append("NOT_BETTER_THAN_B2")
        if facts.get("selection_status") != SELECTION_SURVIVES:
            ve_reasons.append("SELECTION_CORRECTION_NOT_SURVIVED")
    if shadow and not ve_reasons:
        level = "VALIDATED_EXPERIMENTAL"
    elif shadow:
        level = "SHADOW"
    elif role == "REFERENCE_BASELINE":
        level = "ABSTAIN"
    else:
        level = "NO_GO"
    out = list(reasons) + [r for r in ve_reasons]
    if level == "NO_GO":
        out.append("NO_INCREMENTAL_PREDICTIVE_EDGE")
    if level == "ABSTAIN":
        out.append("REFERENCE_BASELINE_NEVER_PUBLISHED")
    return {"level": level, "reasons": out, "shadow_reached": shadow, "rule": "ACCEPTANCE promotion + PI-D-065 + PI-D-069 (registry-1)"}


def registry_status(level: str, role: str) -> str:
    if level in PUBLISHABLE_LEVELS:
        return f"PROMOTED_{level}"
    if role == "REFERENCE_BASELINE":
        return "REFERENCE_ONLY_NEVER_PUBLISHED"
    return "NO_GO"


def role_of(phase: str, kind: str) -> str:
    return "REFERENCE_BASELINE" if phase == "07" and kind in REFERENCE_KINDS else "CANDIDATE"


# ---------------------------------------------------------------- facts from their committed sources (CP16-0)
FACTS_VERSION = "facts-1"


def _f(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _n(x: Any) -> int:
    v = _f(x)
    return int(v) if v is not None else 0


def derive_facts(*, candidate: str, phase: str, card: dict, tests: dict, m_b0: dict | None, m_b2: dict | None,
                 post_states: dict[str, str], cal_card: dict | None) -> dict:
    """An entry's facts from the committed records: `m_b0` and `m_b2` are the card's rows of the Phase 12 HOLDOUT_METRICS.csv
    against B0 and B2 (as read from the CSV, strings), `post_states` its POST_OPENING_CORRECTIONS.csv selection states by
    reference, `cal_card` the Phase 13 calibration card of B2 (None for every other card), `tests` the pre-opening checks."""
    kind = card["kind"]
    role = role_of(phase, kind)
    f = {"role": role, "kind": kind, "model_id": card["model_id"], "source": SOURCE, "fitted": "abstain" not in card["body"],
         "tests": tests, "training": {"n": card.get("n_train"), "k": card.get("k_train")}}
    if candidate == "P07_B0":
        f["retrospective"] = {"evaluation": None, "note": "B0 is the reference of the skill score"}
    elif m_b0 is None or not _n(m_b0.get("n_with_number")):
        f["retrospective"] = {"evaluation": None, "note": "no holdout number (no inputs under the Phase 05 seal, or not fitted)",
                              "verdict": m_b0["verdict"] if m_b0 else None}
    else:
        gov = m_b0["governing"]
        f["retrospective"] = {"evaluation": FIRST_OPENING, "kind": m_b0["kind"], "n": _n(m_b0["n_with_number"]),
                              "k": _n(m_b0["positives"]), "days": _n(m_b0["days"]),
                              "calibration_in_the_large_ok": m_b0["cal_in_the_large_ok"] == "1",
                              "calibration_every_bin_ok": None if m_b0["cal_every_bin_ok"] == "" else m_b0["cal_every_bin_ok"] == "1",
                              "bss": _f(m_b0["bss"]), "bss_lo": _f(m_b0[f"bss_ci_{gov}_lo"]) if gov in ("day", "mint") else None,
                              "governing": gov, "p_holm": _f(m_b0["p_holm"]) if m_b0["p_holm"] else None, "verdict": m_b0["verdict"]}
    f["post_opening_states"] = sorted(post_states.values())
    f["selection_status"] = post_states.get("P07_B0") or ("NO_UNCORRECTED_SKILL" if candidate != "P07_B0" else None)
    if m_b2 is not None and _n(m_b2.get("n_with_number")):
        gov = m_b2["governing"]
        b, br = _f(m_b2["brier"]), _f(m_b2["brier_ref"])
        f["vs_b2"] = {"brier_minus_b2": (b - br) if b is not None and br is not None else None,
                      "lower_bound_b2_minus_brier": _f(m_b2[f"bss_ci_{gov}_lo"]) if gov in ("day", "mint") else None,
                      "note": "sign of the lower bound of the BSS against B2 (B2 Brier minus model Brier, over B2 Brier)"}
    else:
        f["vs_b2"] = None
    if candidate == "P07_B2":
        if cal_card is None:
            raise RegistryError("B2 needs its calibration card")
        f["calibration"] = {"status": cal_card["status"], "evidence_n": cal_card["evidence"]["n"], "evidence_k": cal_card["evidence"]["k"],
                            "evidence_source": cal_card["evidence"]["source"], "evidence_status": cal_card["evidence"]["status"]}
    else:
        if cal_card is not None:
            raise RegistryError("only B2 carries a calibration card")
        f["calibration"] = {"status": None, "note": "no calibration card (Phase 13 calibrated the champion only)"}
    f["prospective"] = {"status": "NOT_YET_MATURED", "note": "Phase 19 evaluates the prospective holdout"}
    return f


def verify_facts(entry: dict, **sources: Any) -> dict:
    """Recompute an entry's facts from the committed records (`derive_facts` arguments other than the candidate, phase and
    card, which come from the entry and `card`) and refuse any difference: a level can only be as true as its facts."""
    card = sources.pop("card")
    if card.get("model_sha") != entry["model_sha"] or card_sha_of(card) != entry["model_sha"]:
        raise EntryHashMismatch("card is not the one the entry names (model sha)")
    want = derive_facts(candidate=entry["family"]["candidate"], phase=entry["family"]["phase"], card=card, **sources)
    if canon(want) != canon(entry["facts"]):
        diff = sorted(k for k in set(want) | set(entry["facts"]) if canon(want.get(k)) != canon(entry["facts"].get(k)))
        raise FactsMismatchError(f"entry {entry['model_id']}: facts differ from their committed sources in {diff}")
    return entry


def verify_sources(entry: dict, read: Callable[[str], bytes]) -> list[str]:
    """Check the sha256 of every committed file the entry names (card, calibration card, evidence files); returns the paths."""
    checked = []

    def one(path: str | None, want: str | None) -> None:
        if not path or not want:
            return
        if sha_bytes(read(path)) != want:
            raise EntryHashMismatch(f"{path}: bytes differ from the sha256 the entry records")
        checked.append(path)
    one(entry["card_path"], entry["card_file_sha256"])
    cal = entry.get("calibration") or {}
    one(cal.get("path"), cal.get("file_sha256"))
    for v in (entry.get("evidence") or {}).values():
        if isinstance(v, dict):
            one(v.get("file"), v.get("sha256"))
    return checked


# ---------------------------------------------------------------- the registry's own rebuild of an entry's facts (CP16-2, CX-S16)
P12V = "audits/predictive-intelligence/phase_12/validation/"
FACT_SOURCES = {"metrics": P12V + "HOLDOUT_METRICS.csv", "post_opening": P12V + "POST_OPENING_CORRECTIONS.csv",
                "candidates": P12V + "CANDIDATES.json", "traps": P12V + "PREOPEN_TRAPS.json", "replay": P12V + "REPLAY_AUDIT.json"}
CALIBRATION_CARD_PATH = "audits/predictive-intelligence/phase_13/artifacts/{short}/CALIBRATION_CARD.json"
TESTS_BASIS = "phase_12 PREOPEN_TRAPS.json failures [] and REPLAY_AUDIT ok; cards load with their hashes; registry fingerprint"
ROW_KIND_ORDER = ("PRIMARY_HOLDOUT", "SECONDARY_HOLDOUT")


def metric_rows(text: str) -> dict[tuple[str, str, str], dict]:
    """HOLDOUT_METRICS.csv rows by (target_short, model, reference). A card that has a PRIMARY_HOLDOUT and a SECONDARY_HOLDOUT
    row against the same reference (B2 against B0) is represented by its PRIMARY row; two rows of the same kind refuse
    (CP16-2, skeptic m2: a last-wins dictionary had kept the secondary row)."""
    out: dict[tuple[str, str, str], dict] = {}
    for r in csv.DictReader(io.StringIO(text)):
        k = (r["target_short"], r["model"], r["reference"])
        if r["kind"] not in ROW_KIND_ORDER:
            raise RegistryError(f"metric row kind {r['kind']!r} is not one of {ROW_KIND_ORDER}")
        old = out.get(k)
        if old is None:
            out[k] = r
        elif old["kind"] == r["kind"]:
            raise RegistryError(f"two {r['kind']} rows for {k}")
        elif ROW_KIND_ORDER.index(r["kind"]) < ROW_KIND_ORDER.index(old["kind"]):
            out[k] = r
    return out


def post_states_of(text: str) -> dict[tuple[str, str], dict[str, str]]:
    out: dict[tuple[str, str], dict[str, str]] = {}
    for r in csv.DictReader(io.StringIO(text)):
        d = out.setdefault((r["target_short"], r["model"]), {})
        if r["reference"] in d:
            raise RegistryError(f"two post-opening rows for {(r['target_short'], r['model'], r['reference'])}")
        d[r["reference"]] = r["selection_status_final"]
    return out


def tests_of(card: dict, card_bytes: bytes, cand_row: dict, traps: dict, replay: dict) -> dict:
    """The pre-opening checks of one card: leakage from Phase 12's committed trap results and replay audit, provenance from the
    card's own file and model hashes against CANDIDATES.json, contract from its registry fingerprint."""
    return {"leakage": traps.get("failures") == [] and bool(replay.get("ok")),
            "provenance": sha_bytes(card_bytes) == cand_row["file_sha256"] and card_sha_of(card) == card.get("model_sha") == cand_row["model_sha"],
            "contract": card.get("registry_sha") == C.registry_sha256(), "basis": TESTS_BASIS}


def facts_from_repo(card_path: str, root: str | Path) -> tuple[dict, dict]:
    """Rebuild a card's facts from the committed files under `root` (fixed paths, FACT_SOURCES); returns the facts and the
    context (candidate row, card, card bytes, calibration card or None)."""
    root = Path(root)
    read = lambda p: (root / p).read_bytes()
    cand = json.loads(read(FACT_SOURCES["candidates"]))["candidates"]
    rows = [c for c in cand if c["path"] == card_path]
    if len(rows) != 1:
        raise FactsMismatchError(f"{card_path} is not exactly one frozen candidate of CANDIDATES.json")
    c = rows[0]
    b = read(card_path)
    card = json.loads(b)
    m = metric_rows(read(FACT_SOURCES["metrics"]).decode())
    post = post_states_of(read(FACT_SOURCES["post_opening"]).decode())
    traps, replay = json.loads(read(FACT_SOURCES["traps"])), json.loads(read(FACT_SOURCES["replay"]))
    s, cid = c["target_short"], c["candidate"]
    cal_card = json.loads(read(CALIBRATION_CARD_PATH.format(short=s))) if cid == "P07_B2" else None
    facts = derive_facts(candidate=cid, phase=c["phase"], card=card, tests=tests_of(card, b, c, traps, replay),
                         m_b0=m.get((s, cid, "P07_B0")), m_b2=m.get((s, cid, "P07_B2")), post_states=post.get((s, cid), {}),
                         cal_card=cal_card)
    return facts, {"candidate": c, "card": card, "card_bytes": b, "cal_card": cal_card,
                   "cal_path": CALIBRATION_CARD_PATH.format(short=s) if cal_card is not None else None}


def check_facts(entry: dict, root: str | Path) -> dict:
    """The registry's own source check (no caller-supplied verifier): rebuild the facts from the committed files, refuse any
    difference, then check the card, the calibration card and every sha256 the entry names."""
    facts, ctx = facts_from_repo(entry["card_path"], root)
    if ctx["candidate"]["candidate"] != entry["family"]["candidate"] or ctx["candidate"]["phase"] != entry["family"]["phase"]:
        raise FactsMismatchError("the card path belongs to another candidate")
    if canon(facts) != canon(entry["facts"]):
        diff = sorted(k for k in set(facts) | set(entry["facts"]) if canon(facts.get(k)) != canon(entry["facts"].get(k)))
        raise FactsMismatchError(f"entry {entry['model_id']}: facts differ from the committed files in {diff}")
    if ctx["cal_card"] is not None and (entry["calibration"] or {}).get("path") != ctx["cal_path"]:
        raise FactsMismatchError("the entry names another calibration card than the committed one")
    verify_entry(entry, card=ctx["card"], card_bytes=ctx["card_bytes"], cal_card=ctx["cal_card"])
    verify_sources(entry, lambda p: (Path(root) / p).read_bytes())
    return entry


def code_of(paths: Sequence[str], root: str | Path) -> dict:
    """The sha256 of the code files an entry's numbers depend on (CP16-2, m5: P46 without a version bump)."""
    if not paths or "memelab/predictive/features.py" not in paths:
        raise RegistryError("code files must include memelab/predictive/features.py")
    return {"files": {p: sha_bytes((Path(root) / p).read_bytes()) for p in sorted(set(paths))}}


def code_changes(entry: dict, root: str | Path) -> list[dict]:
    out = []
    for p, want in sorted(((entry.get("code") or {}).get("files") or {}).items()):
        f = Path(root) / p
        got = sha_bytes(f.read_bytes()) if f.is_file() else None
        if got != want:
            out.append({"state": INCOMPATIBLE, "detail": f"{p} changed since registration (transform or model code, P46)"})
    if not (entry.get("code") or {}).get("files"):
        out.append({"state": INCOMPATIBLE, "detail": "the entry records no code files"})
    return out


AGENT_RE = re.compile(r"(?<![a-z])(agents?|votes?|voting|agreements?|agree|consensus|personas?|swarm|mirofish|oasis|simulat[a-z]*)",
                      re.I)


def agent_fields(o: Any, path: str = "") -> list[str]:
    """Paths of keys or strings that name an agent, vote, agreement, consensus, persona, swarm or simulation (P27, m6)."""
    out = []
    if isinstance(o, dict):
        for k, v in o.items():
            here = f"{path}.{k}" if path else str(k)
            if AGENT_RE.search(str(k)):
                out.append(here)
            out += agent_fields(v, here)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out += agent_fields(v, f"{path}[{i}]")
    elif isinstance(o, str) and AGENT_RE.search(o):
        out.append(path)
    return out


def _no_agent_fields(entry_like: dict) -> None:
    bad = []
    for k in ("facts", "evidence", "risk_flags", "inference", "calibration", "family", "model_id"):
        bad += agent_fields(entry_like.get(k), k)
    if bad:
        raise BehavioralNotAModel(f"agent or simulation fields in the entry (P27): {bad[:5]}")


# ---------------------------------------------------------------- entries (rule 4)
def make_entry(*, target: str, family: dict, card: dict, card_path: str, card_file_sha256: str, calibration: dict | None,
               facts: dict, evidence: dict, risk_flags: Sequence[str], inference: dict, registered_as_of_utc: str,
               code: dict, is_fixture: bool = False) -> dict:
    """One immutable entry for one frozen card. The level, status and publishable flag come from the facts."""
    if target not in C.TARGETS:
        raise RegistryError(f"unknown target {target!r}")
    ph, kind = str(family.get("phase")), str(family.get("kind"))
    if ph not in FAMILY_PHASES:
        raise RegistryError(f"unknown family phase {ph!r}")
    mv = family.get("module_version")
    if not isinstance(mv, str) or not mv:
        raise RegistryError("the family module version is missing (the caller reads it from the card)")
    if card.get("targets") != [target]:
        raise RegistryError("card target differs from the entry target")
    if _behavioral(kind, card.get("model_id"), card.get("kind"), family.get("candidate")):
        raise BehavioralNotAModel("a behavioral simulation is never a registry model (P27, MIROFISH_NO_GO)")
    role = role_of(ph, kind)
    if facts.get("role") != role or facts.get("kind") != kind:
        raise RegistryError("facts name another role or kind than the card")
    promo = promotion_decision(facts)
    entry = {"registry_version": REGISTRY_VERSION, "entry_kind": "MODEL", "is_fixture": bool(is_fixture), "target": target,
             "target_version": C.TARGETS[target]["version"], "target_registry_sha": card.get("registry_sha"),
             "family": {"phase": ph, "kind": kind, "candidate": family.get("candidate"), "module_version": mv},
             "model_id": card["model_id"], "model_sha": card["model_sha"], "card_path": card_path,
             "card_file_sha256": card_file_sha256, "feature_set_sha": card.get("feature_set_sha"),
             "feature_version": card.get("feature_version"),
             "family_version": mv,
             "training_cutoff": float(card["training_cutoff"]), "training_cutoff_utc": card["training_cutoff_utc"],
             "max_train_decision_time": card.get("max_train_decision_time"),
             "max_train_label_matures_at": card.get("max_train_label_matures_at"), "n_train": card.get("n_train"),
             "k_train": card.get("k_train"), "labels_version": card.get("labels_version"), "label_set_sha": card.get("label_set_sha"),
             "data_snapshot_sha": card.get("data_snapshot_sha"), "fitted": "abstain" not in (card.get("body") or {}),
             "abstain_reason": (card.get("body") or {}).get("abstain"), "source": facts.get("source"),
             "calibration": calibration, "facts": facts, "evidence": evidence,
             "min_support": {"train_events": ACC["min_train_events"], "train_per_class": ACC["min_train_per_class"],
                             "holdout_events": ACC["min_holdout_events"], "holdout_per_class": ACC["min_holdout_per_class"],
                             "bin_events": ACC["min_bin_events"], "effective_days": ACC["min_effective_days"],
                             "prospective_events": ACC["promotion"]["VALIDATED_EXPERIMENTAL"]["prospective_min_events"]},
             "risk_flags": sorted(set(risk_flags)), "role": role, "promotion": promo,
             "registry_status": registry_status(promo["level"], role), "publishable": False, "inference": inference,
             "code": code, "retrain_policy": RETRAIN_POLICY, "thresholds": THRESHOLDS, "registered_as_of_utc": registered_as_of_utc}
    entry["publishable"] = publishable(entry)
    _no_agent_fields(entry)
    if not isinstance((code or {}).get("files"), dict) or "memelab/predictive/features.py" not in code["files"]:
        raise RegistryError("the entry must record the sha256 of its code files (code_of)")
    if bool(facts.get("fitted")) != entry["fitted"]:
        raise RegistryError("facts say fitted differently from the card")
    entry["entry_id"] = sha({k: v for k, v in entry.items() if k != "entry_id"})
    return entry


def publishable(entry: dict) -> bool:
    cal = entry.get("calibration") or {}
    return entry["promotion"]["level"] in PUBLISHABLE_LEVELS and cal.get("status") == CALIBRATED and \
        cal.get("level") == entry["promotion"]["level"]


def card_sha_of(card: dict) -> str:
    return sha({k: v for k, v in card.items() if k != "model_sha"})


def verify_entry(entry: dict, *, card: dict | None = None, card_bytes: bytes | None = None, cal_card: dict | None = None) -> dict:
    """Refuse an entry whose content differs from its id, whose level, status or flags are not what its facts give, or whose
    card or calibration card (when given) is not the one it names."""
    if not isinstance(entry, dict) or tuple(sorted(entry)) != tuple(sorted(ENTRY_KEYS)):
        raise RegistryError("entry keys differ from the schema")
    try:
        want = sha({k: v for k, v in entry.items() if k != "entry_id"})
    except ValueError as e:                                     # NaN or infinity anywhere (P38)
        raise MalformedScore(f"entry holds a non-finite number: {e}")
    if entry["entry_id"] != want:
        raise EntryHashMismatch(f"entry {entry.get('model_id')}: content does not match its entry_id")
    if entry["registry_version"] != REGISTRY_VERSION or entry["entry_kind"] != "MODEL":
        raise RegistryError("entry of another registry version or kind")
    if entry["source"] != SOURCE or _behavioral(entry["family"].get("kind"), entry["model_id"], entry["family"].get("candidate")):
        raise BehavioralNotAModel("a behavioral simulation is never a registry model (P27, MIROFISH_NO_GO)")
    _no_agent_fields(entry)
    for k in ("model_id", "model_sha", "feature_set_sha", "training_cutoff_utc", "target"):
        if not isinstance(entry[k], str) or not entry[k]:
            raise RegistryError(f"entry field {k} is missing")
    if not isinstance((entry["code"] or {}).get("files"), dict) or "memelab/predictive/features.py" not in entry["code"]["files"]:
        raise RegistryError("entry records no code files")
    if entry["role"] != role_of(entry["family"]["phase"], entry["family"]["kind"]):
        raise RegistryError("entry role is not the one its family and kind give")
    promo = promotion_decision(entry["facts"])
    if promo != entry["promotion"]:
        raise LevelMismatch(f"entry {entry['model_id']}: stored level {entry['promotion'].get('level')} is not what its facts "
                            f"give ({promo['level']})")
    if entry["registry_status"] != registry_status(promo["level"], entry["role"]) or entry["publishable"] != publishable(entry):
        raise LevelMismatch("registry status or publishable flag differ from the level")
    if entry["facts"].get("role") != entry["role"] or entry["facts"].get("kind") != entry["family"]["kind"]:
        raise RegistryError("facts name another role or kind than the entry")
    if bool(entry["facts"].get("fitted")) != bool(entry["fitted"]):
        raise RegistryError("facts say fitted differently from the entry")
    inf = entry["inference"] or {}
    if not isinstance(inf.get("outputs_sha"), str) or len(inf["outputs_sha"]) != 64:
        raise RegistryError("entry carries no identical-inference hash")
    if card is not None:
        if card.get("model_sha") != entry["model_sha"] or card_sha_of(card) != entry["model_sha"]:
            raise EntryHashMismatch("card is not the one the entry names (model sha)")
        for ck, ek in (("feature_set_sha", "feature_set_sha"), ("training_cutoff_utc", "training_cutoff_utc"),
                       ("data_snapshot_sha", "data_snapshot_sha"), ("label_set_sha", "label_set_sha"),
                       ("labels_version", "labels_version"), ("n_train", "n_train"), ("k_train", "k_train"),
                       ("registry_sha", "target_registry_sha")):
            if card.get(ck) != entry[ek]:
                raise EntryHashMismatch(f"card {ck} differs from the entry")
    if card_bytes is not None and sha_bytes(card_bytes) != entry["card_file_sha256"]:
        raise EntryHashMismatch("card file bytes differ from the entry's card_file_sha256")
    cal = entry["calibration"]
    if cal_card is not None:
        if cal is None:
            raise RegistryError("a calibration card was given for an entry that names none")
        if cal_card.get("card_sha") != sha({k: v for k, v in cal_card.items() if k != "card_sha"}) or \
                cal_card["card_sha"] != cal.get("card_sha"):
            raise EntryHashMismatch("calibration card is not the one the entry names")
        if cal_card.get("champion_model_sha") != entry["model_sha"] or cal_card.get("target") != entry["target"]:
            raise RegistryError("calibration card of another model or target")
        if cal_card.get("status") != cal.get("status") or cal_card.get("level") != cal.get("level"):
            raise RegistryError("calibration card status or level differ from the entry")
    return entry


def dumps(entry: dict) -> str:
    return json.dumps(entry, sort_keys=True, indent=1, allow_nan=False) + "\n"


def loads(text: str, **kw: Any) -> dict:
    return verify_entry(json.loads(text), **kw)


def write_entry(directory: str | Path, entry: dict) -> Path:
    """Write once: the file is named by the entry id; an existing file must hold the same bytes (immutable)."""
    verify_entry(entry)
    p = Path(directory) / f"{entry['entry_id']}.json"
    text = dumps(entry)
    if p.exists() and p.read_text() != text:
        raise EntryHashMismatch(f"{p.name} exists with other content: entries are immutable")
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(text)
    return p


def read_entries(directory: str | Path) -> dict[str, dict]:
    out = {}
    for p in sorted(Path(directory).glob("*.json")):
        e = loads(p.read_text())
        if p.stem != e["entry_id"]:
            raise EntryHashMismatch(f"{p.name}: file name differs from the entry id")
        out[e["entry_id"]] = e
    return out


# ---------------------------------------------------------------- identical inference (rule 7, P38)
def inference_rows(rows: Iterable[Sequence[Any]]) -> list[list]:
    """Canonical (decision key, number or None, reason) rows. A number that is not finite needs a reason; a finite number
    must lie in [0, 1] (P38)."""
    out = []
    for key, num, why in rows:
        why = why or ""
        if num is None or (isinstance(num, float) and math.isnan(num)):
            if not why:
                raise MalformedScore(f"{str(key)[:12]}: no number and no reason")
            out.append([str(key), None, str(why)])
            continue
        if isinstance(num, bool) or not isinstance(num, (int, float, np.floating)) or not math.isfinite(float(num)):
            raise MalformedScore(f"{str(key)[:12]}: number {num!r} is not finite (P38)")
        if not 0.0 <= float(num) <= 1.0:
            raise MalformedScore(f"{str(key)[:12]}: number {float(num)!r} outside [0, 1] (P38)")
        out.append([str(key), float(num), str(why)])
    keys = [r[0] for r in out]
    if len(set(keys)) != len(keys):
        raise MalformedScore("a decision appears twice in the inference rows")
    return sorted(out, key=lambda r: r[0])


def inference_hash(rows: Iterable[Sequence[Any]]) -> str:
    return sha(inference_rows(rows))


def check_inference(entry: dict, rows: Iterable[Sequence[Any]], *, which: str = "outputs_sha") -> str:
    got = inference_hash(rows)
    want = (entry.get("inference") or {}).get(which)
    if got != want:
        raise InferenceMismatchError(f"{entry.get('model_id')}: recomputed {which} {got[:12]} differs from the pinned {str(want)[:12]}")
    return got


# ---------------------------------------------------------------- compatibility (rule 6, P46)
def compatibility(entry: dict, *, runtime: dict, request: dict | None = None) -> list[dict]:
    """States that refuse the entry for this code and this request. `runtime` names, for the running code: `feature_set_sha`
    per family phase, `feature_version`, `family_version` per phase, `registry_sha` and `labels_version`."""
    out = []
    ph = entry["family"]["phase"]
    fs = (runtime.get("feature_set_sha") or {}).get(ph)
    if fs != entry["feature_set_sha"]:
        out.append({"state": INCOMPATIBLE, "detail": f"feature definitions of family {ph} changed since training (P46)"})
    if runtime.get("feature_version") != entry["feature_version"]:
        out.append({"state": INCOMPATIBLE, "detail": f"feature version {runtime.get('feature_version')!r} is not the entry's "
                                                     f"{entry['feature_version']!r}"})
    if (runtime.get("family_version") or {}).get(ph) != entry["family_version"]:
        out.append({"state": INCOMPATIBLE, "detail": f"family module version changed ({entry['family_version']})"})
    if runtime.get("registry_sha") != entry["target_registry_sha"]:
        out.append({"state": INCOMPATIBLE, "detail": "target registry fingerprint changed (target or acceptance plan)"})
    if runtime.get("labels_version") != entry["labels_version"]:
        out.append({"state": INCOMPATIBLE, "detail": "labels version changed"})
    if request is not None:
        if request.get("feature_set_sha") != entry["feature_set_sha"]:
            out.append({"state": FEATURE_SCHEMA_MISMATCH, "detail": "the request's feature set sha differs from the model's"})
        if request.get("feature_version") is not None and request.get("feature_version") != entry["feature_version"]:
            out.append({"state": FEATURE_SCHEMA_MISMATCH, "detail": "the request's feature version differs from the model's"})
    return out


# ---------------------------------------------------------------- staleness, drift, promotion state (rule 8, P39)
def stale_after(entry: dict) -> float:
    return float(entry["training_cutoff"]) + float(ACC["max_model_age_s"])


def training_after_cutoff(entry: dict) -> str | None:
    """The rule of `evaluation.check_card_time` on an entry's own record (P05, P43): a training decision at or after the
    training cutoff, or a training label maturing after it. None when the record keeps its cutoff (CP20-1, F20-06)."""
    cut = float(entry["training_cutoff"])
    mt, mm = entry.get("max_train_decision_time"), entry.get("max_train_label_matures_at")
    if mt is not None and float(mt) >= cut:
        return f"a training decision at or after the cutoff {entry['training_cutoff_utc']} (P43)"
    if mm is not None and float(mm) > cut:
        return f"a training label maturing after the cutoff {entry['training_cutoff_utc']} (P05)"
    return None


def status_at(entry: dict, decision_time: float, *, drift_alarms: Sequence[float] = ()) -> list[dict]:
    T = float(decision_time)
    cut = float(entry["training_cutoff"])
    out = []
    leak = training_after_cutoff(entry)
    if leak:
        out.append({"state": TRAINING_AFTER_CUTOFF, "detail": leak})
    if T < cut:
        out.append({"state": NOT_AVAILABLE_AS_OF, "detail": f"trained to {entry['training_cutoff_utc']}"})
    elif T - cut > float(ACC["max_model_age_s"]):
        out.append({"state": MODEL_STALE, "detail": f"stale after {_iso(stale_after(entry))}"})
    hits = [float(a) for a in drift_alarms if float(a) <= T]
    if hits:
        out.append({"state": DRIFT_ALERT, "detail": f"alarm at {_iso(min(hits))}"})
    if entry["promotion"]["level"] not in PUBLISHABLE_LEVELS:
        out.append({"state": MODEL_NOT_PROMOTED, "detail": f"level {entry['promotion']['level']}"})
    return out


def retrain_requirements(states: Iterable[dict]) -> list[str]:
    got = []
    for s in states:
        r = RETRAIN.get(s.get("state"))
        if r and r not in got:
            got.append(r)
    return got


# ---------------------------------------------------------------- the event log (rule 5)
def line_sha(line: str) -> str:
    return sha_bytes(line.encode())


def _event_id(ev: dict) -> str:
    return sha({k: v for k, v in ev.items() if k != "event_id"})


def chain_events(payloads: Sequence[dict], *, prev: str = GENESIS, start_seq: int = 0) -> list[dict]:
    """Events with their sequence number, the sha256 of the previous line and their own id."""
    out = []
    for i, p in enumerate(payloads):
        if p.get("kind") not in EVENT_KINDS:
            raise LogError(f"event kind {p.get('kind')!r} is not one of {EVENT_KINDS}")
        if not isinstance(p.get("as_of_utc"), str):
            raise LogError("an event needs as_of_utc")
        ev = {**{k: v for k, v in p.items() if k not in ("seq", "prev", "event_id")}, "seq": start_seq + i, "prev": prev}
        ev["event_id"] = _event_id(ev)
        out.append(ev)
        prev = line_sha(canon(ev))
    return out


def read_log(text: str) -> list[dict]:
    """Every event of a log, refused when a line was changed, dropped, reordered or appended out of time order."""
    if text and not text.endswith("\n"):
        raise LogError("log does not end with a newline (a partial write)")
    events, prev, last_t = [], GENESIS, -math.inf
    for i, line in enumerate(text.splitlines()):
        try:
            ev = json.loads(line)
        except ValueError:
            raise LogError(f"line {i}: not JSON")
        if canon(ev) != line:
            raise LogError(f"line {i}: not in canonical form")
        if ev.get("seq") != i or ev.get("prev") != prev or ev.get("event_id") != _event_id(ev):
            raise LogError(f"line {i}: chain broken (changed, dropped or reordered event)")
        if ev.get("kind") not in EVENT_KINDS:
            raise LogError(f"line {i}: unknown event kind")
        t = C.parse_utc(ev["as_of_utc"])
        if t < last_t:
            raise LogError(f"line {i}: event earlier than the one before it")
        last_t = t
        events.append(ev)
        prev = line_sha(line)
    return events


def file_sha(path: str | Path) -> str | None:
    p = Path(path)
    return sha_bytes(p.read_bytes()) if p.exists() else None


def append_events(path: str | Path, payloads: Sequence[dict], *, expect_sha: str | None) -> tuple[str, list[dict]]:
    """Append chained events. `expect_sha` is the sha256 the file had after the last append (None for a new file); a file
    that changed in between is refused, so the log is never rewritten (P39)."""
    p = Path(path)
    if file_sha(p) != expect_sha:
        raise LogError(f"{p.name}: the log changed since its last append")
    old = p.read_text() if p.exists() else ""
    events = read_log(old)
    prev = line_sha(canon(events[-1])) if events else GENESIS
    new = chain_events(payloads, prev=prev, start_seq=len(events))
    if events and new and C.parse_utc(new[0]["as_of_utc"]) < C.parse_utc(events[-1]["as_of_utc"]):
        raise LogError("an appended event is earlier than the last event")
    with open(p, "a") as f:
        for ev in new:
            f.write(canon(ev) + "\n")
    read_log(p.read_text())
    return file_sha(p), new


def is_append_only(old_text: str, new_text: str) -> bool:
    return new_text.startswith(old_text) and (old_text == "" or old_text.endswith("\n"))


def register_event(entry: dict, *, as_of_utc: str) -> dict:
    verify_entry(entry)
    return {"kind": "REGISTER", "as_of_utc": as_of_utc, "target": entry["target"], "entry_id": entry["entry_id"],
            "model_id": entry["model_id"], "level": entry["promotion"]["level"], "registry_status": entry["registry_status"]}


def _references_ok(entries: dict[str, dict], target: str, references: dict) -> None:
    if sorted(references) != sorted(REFERENCE_NAMES.values()):
        raise PinRefused(f"references must be {sorted(REFERENCE_NAMES.values())}")
    for name, eid in references.items():
        e = entries.get(eid)
        if e is None:
            raise PinRefused(f"reference {name} names an unknown entry")
        if e["target"] != target or e["role"] != "REFERENCE_BASELINE" or REFERENCE_NAMES.get(e["family"]["kind"]) != name:
            raise PinRefused(f"reference {name} is not the {name} baseline of {target}")


def pin_event(entries: dict[str, dict], target: str, *, mode: str, champion: str | None, references: dict, reasons: Sequence[str],
              as_of_utc: str, root: str | Path | None = None, allow_fixture: bool = False) -> dict:
    """A pin of the deployed mode of one target. CHAMPION only for an entry whose recomputed level is SHADOW or
    VALIDATED_EXPERIMENTAL (no champion that implies skill it does not have) and whose facts the registry itself rebuilt from
    the committed files under `root` and found equal (`check_facts`; CP16-2: no caller-supplied verifier, CX-S16). A fixture
    champion needs `allow_fixture` and is recorded FIXTURE_FACTS_NOT_CHECKED. NO_VIABLE_CHAMPION names no champion."""
    if mode not in MODES:
        raise PinRefused(f"mode {mode!r} is not one of {MODES}")
    _references_ok(entries, target, references)
    inf_sha = None
    if mode == "CHAMPION":
        e = entries.get(champion or "")
        if e is None:
            raise PinRefused("champion names an unknown entry")
        verify_entry(e)
        if e["target"] != target:
            raise PinRefused("champion of another target")
        if e["promotion"]["level"] not in PUBLISHABLE_LEVELS:
            raise PinRefused(f"champion level {e['promotion']['level']}: a champion needs SHADOW or VALIDATED_EXPERIMENTAL")
        leak = training_after_cutoff(e)
        if leak:
            raise PinRefused(f"champion card: {leak} ({TRAINING_AFTER_CUTOFF})")
        if e["is_fixture"] and not allow_fixture:
            raise PinRefused("a fixture entry is never pinned in a real registry")
        if e["is_fixture"]:
            check = FIXTURE_FACTS_NOT_CHECKED
        else:
            if root is None:
                raise PinRefused("a champion is pinned only after the registry rebuilds its facts from the committed files (root)")
            try:
                check_facts(e, root)
            except (RegistryError, OSError, ValueError, KeyError) as err:
                raise PinRefused(f"champion facts refused: {type(err).__name__}: {err}")
            check = FACTS_CHECKED
        inf_sha = e["inference"]["outputs_sha"]
    elif champion is not None:
        raise PinRefused("NO_VIABLE_CHAMPION names no champion")
    else:
        check = None
    for eid in references.values():
        if entries[eid]["is_fixture"] and not allow_fixture:
            raise PinRefused("a fixture reference is never pinned in a real registry")
    return {"kind": "PIN", "as_of_utc": as_of_utc, "target": target, "mode": mode, "champion": champion,
            "champion_inference_sha": inf_sha, "facts_check": check, "references": dict(sorted(references.items())),
            "reasons": list(reasons)}


def resolve(events: Sequence[dict], entries: dict[str, dict], target: str, decision_time: float) -> dict:
    """The pin in force for a target at a decision time: the last PIN or ROLLBACK at or before it."""
    T = float(decision_time)
    cur = None
    for ev in events:
        if ev["kind"] in ("PIN", "ROLLBACK") and ev["target"] == target and C.parse_utc(ev["as_of_utc"]) <= T:
            cur = ev
    if cur is None:
        return {"target": target, "mode": "NO_VIABLE_CHAMPION", "champion": None, "champion_inference_sha": None,
                "references": {}, "reasons": ["NO_PIN"], "event_id": None, "as_of_utc": None}
    for eid in [cur.get("champion")] + list((cur.get("references") or {}).values()):
        if eid is not None and eid not in entries:
            raise LogError(f"pin names an unknown entry {str(eid)[:12]}")
    if cur["mode"] == "CHAMPION" and entries[cur["champion"]]["promotion"]["level"] not in PUBLISHABLE_LEVELS:
        raise PinRefused("pinned champion is below SHADOW")
    return {"target": target, "mode": cur["mode"], "champion": cur.get("champion"),
            "champion_inference_sha": cur.get("champion_inference_sha"), "references": dict(cur.get("references") or {}),
            "reasons": list(cur.get("reasons") or []), "event_id": cur["event_id"], "as_of_utc": cur["as_of_utc"]}


def rollback_event(events: Sequence[dict], entries: dict[str, dict], target: str, *, reason: str, as_of_utc: str,
                   usable: Callable[[dict], bool], root: str | Path | None = None, allow_fixture: bool = False) -> dict:
    """Fall back from the pin in force: to the most recent earlier CHAMPION pin of another entry that is still usable, else to
    NO_VIABLE_CHAMPION with the current references. Earlier events are never touched (P39)."""
    T = C.parse_utc(as_of_utc)
    now = resolve(events, entries, target, T)
    if now["event_id"] is None:
        raise PinRefused("nothing is pinned for this target")
    bad = {now["champion"]} if now["champion"] else set()
    earlier = [ev for ev in events if ev["kind"] in ("PIN", "ROLLBACK") and ev["target"] == target
               and C.parse_utc(ev["as_of_utc"]) <= T]
    for ev in reversed(earlier):
        if ev["kind"] == "ROLLBACK" and ev.get("from"):
            bad.add(ev["from"])
    pick = None
    for ev in reversed(earlier):
        c = ev.get("champion")
        if ev["mode"] == "CHAMPION" and c and c not in bad and usable(entries[c]):
            pick = ev
            break
    refs = now["references"]
    if pick is not None:
        pin = pin_event(entries, target, mode="CHAMPION", champion=pick["champion"], references=refs,
                        reasons=[reason, f"rolled back to the champion pinned at {pick['as_of_utc']}"], as_of_utc=as_of_utc,
                        root=root, allow_fixture=allow_fixture)
    else:
        pin = pin_event(entries, target, mode="NO_VIABLE_CHAMPION", champion=None, references=refs,
                        reasons=[reason, "no earlier usable champion: abstain with the references"], as_of_utc=as_of_utc,
                        allow_fixture=allow_fixture)
    return {**pin, "kind": "ROLLBACK", "from": now["champion"], "from_event": now["event_id"]}


def serve(events: Sequence[dict], entries: dict[str, dict], target: str, decision_time: float, *, runtime: dict,
          request: dict | None = None, drift_alarms: Sequence[float] = (), inference: Sequence[Sequence[Any]] | None = None,
          root: str | Path | None = None, allow_fixture: bool = False) -> dict:
    """What the publication path may use for one request: the pinned champion only when its entry verifies, the registry
    itself rebuilt its facts from the committed files under `root` and found them equal (FACTS_NOT_VERIFIED without a root,
    FACTS_MISMATCH on a difference; CP16-2, CX-S16), its code files are unchanged (P46), it is compatible, current, not
    drifting, and the caller's recomputed inference rows give its pinned hash (INFERENCE_NOT_CHECKED without rows). A fixture
    champion is served only with `allow_fixture` (its facts have no committed sources). Otherwise NO_VIABLE_CHAMPION with the
    blocking states, and `rollback_required` when a pinned champion failed. `forecast_inputs` is what abstention-1 gets."""
    res = resolve(events, entries, target, decision_time)
    blocking: list[dict] = []
    if res["mode"] == "CHAMPION":
        e = entries[res["champion"]]
        try:
            verify_entry(e)
        except RegistryError as err:
            blocking.append({"state": ENTRY_REFUSED, "detail": f"{type(err).__name__}"})
        if e["is_fixture"]:
            if not allow_fixture:
                blocking.append({"state": FIXTURE_IN_REAL_REGISTRY, "detail": "a fixture champion outside a fixture run"})
        elif root is None:
            blocking.append({"state": FACTS_NOT_VERIFIED, "detail": "no repository root: the facts were not rebuilt"})
        else:
            try:
                check_facts(e, root)
            except (RegistryError, OSError, ValueError, KeyError) as err:
                blocking.append({"state": FACTS_MISMATCH, "detail": f"{type(err).__name__}: {err}"})
        if root is not None:
            blocking += code_changes(e, root)
        else:
            blocking.append({"state": INCOMPATIBLE, "detail": "no repository root: the code files were not checked"})
        blocking += compatibility(e, runtime=runtime, request=request)
        blocking += [s for s in status_at(e, decision_time, drift_alarms=drift_alarms) if s["state"] != MODEL_NOT_PROMOTED]
        if inference is None:
            blocking.append({"state": INFERENCE_NOT_CHECKED, "detail": "no recomputed inference rows were given"})
        else:
            try:
                got = inference_hash(inference)
                if got != res["champion_inference_sha"]:
                    blocking.append({"state": INFERENCE_MISMATCH, "detail": "recomputed outputs differ from the pinned hash"})
            except MalformedScore as err:
                blocking.append({"state": "MALFORMED_SCORE", "detail": str(err)})
    use = res["mode"] == "CHAMPION" and not blocking
    ch = entries[res["champion"]] if use else None
    return {"target": target, "resolved": res, "use_champion": use, "blocking": blocking,
            "rollback_required": res["mode"] == "CHAMPION" and bool(blocking), "retrain": retrain_requirements(blocking),
            "forecast_inputs": {"card_entry": ch["entry_id"] if ch else None, "model_id": ch["model_id"] if ch else NOT_SELECTED,
                                "level": ch["promotion"]["level"] if ch else "ABSTAIN",
                                "calibration_card_sha": (ch["calibration"] or {}).get("card_sha") if ch else None},
            "references": res["references"]}


# ---------------------------------------------------------------- champion restatement (rule 2): no holdout input
HOLDOUT_MARKERS = ("HOLDOUT", "POST_OPENING")


def select_champion(target: str, dev_rows: Sequence[dict], fitted: dict[str, bool], *,
                    rule: Callable[[str, Sequence[dict], dict[str, bool]], dict]) -> dict:
    """The Phase 12 development rule (`rule`, the caller passes `evaluation.champion`), after refusing any row that carries a
    holdout or post-opening marker: the opened holdout never chooses (PI-D-065)."""
    for r in dev_rows:
        txt = " ".join(str(r.get(k) or "") for k in ("kind", "view", "split", "label", "verdict", "source")).upper()
        if any(m in txt for m in HOLDOUT_MARKERS):
            raise HoldoutInputRefused(f"a holdout or post-opening row was passed to the champion rule ({txt.strip()[:60]})")
    return rule(target, dev_rows, fitted)


# ---------------------------------------------------------------- ensembles (rule 12)
def sources_of(columns: Iterable[str]) -> set[str]:
    got = set()
    for c in columns:
        if c not in EVIDENCE_SOURCES:
            raise UndeclaredColumn(f"column {c!r} has no declared evidence source")
        got.update(EVIDENCE_SOURCES[c])
    return got


def check_members(members: dict[str, Sequence[str]]) -> dict:
    """Refuse an ensemble whose members read the same evidence source (social or on-chain evidence counted twice)."""
    if len(members) < 2:
        raise RegistryError("an ensemble needs at least two members")
    seen: dict[str, str] = {}
    for name, cols in members.items():
        if _behavioral(name):
            raise BehavioralNotAModel("a behavioral output never enters an ensemble (P27)")
        for s in sorted(sources_of(cols)):
            if s in seen:
                raise DoubleCountedEvidence(f"{name} and {seen[s]} both read {s}")
            seen[s] = name
    return {"members": sorted(members), "sources": dict(sorted(seen.items()))}


def out_of_fold_rows(member_rows: dict[str, Sequence[dict]]) -> list[dict]:
    """Join members on (fold, decision key). Every row must be a committed out-of-fold row: decided at or after its fold cutoff,
    every member at the same fold cutoff, the same label."""
    names = sorted(member_rows)
    idx = {n: {(str(r["fold"]), r["decision_key"]): r for r in member_rows[n]} for n in names}
    keys = sorted(set.intersection(*[set(v) for v in idx.values()]) if idx else set())
    out = []
    for k in keys:
        rs = [idx[n][k] for n in names]
        cuts = {float(r["cutoff"]) for r in rs}
        ys = {int(r["y"]) for r in rs}
        if len(cuts) != 1 or len(ys) != 1:
            raise NotOutOfFold(f"{k[1][:12]}: members disagree on the fold cutoff or the label")
        cut = cuts.pop()
        T = float(rs[0]["decision_time"])
        if T < cut:
            raise NotOutOfFold(f"{k[1][:12]}: decided before its fold cutoff (an in-sample row)")
        out.append({"fold": k[0], "decision_key": k[1], "cutoff": cut, "decision_time": T, "mint": rs[0]["mint"],
                    "label_matures_at": float(rs[0]["label_matures_at"]), "y": ys.pop(),
                    "members": {n: idx[n][k]["number"] for n in names}})
    return out


def mean_ensemble(numbers: dict[str, float]) -> float:
    vals = list(numbers.values())
    if not vals or not all(_fin(v) for v in vals):
        return float("nan")
    return float(sum(float(v) for v in vals) / len(vals))


def check_stack_rows(fit_rows: Sequence[dict], eval_rows: Sequence[dict]) -> None:
    """A stack is fitted only on rows decided before, and matured by, the first evaluation fold's cutoff, and never on a row it
    is scored on (in-sample stacking refused)."""
    if not eval_rows:
        return
    cut = min(float(r["cutoff"]) for r in eval_rows)
    ek = {r["decision_key"] for r in eval_rows}
    for r in fit_rows:
        if r["decision_key"] in ek:
            raise InSampleStacking("a stacking fit row is also an evaluation row")
        if not (float(r["decision_time"]) < cut and float(r["label_matures_at"]) <= cut):
            raise InSampleStacking("a stacking fit row is not decided before and matured by the evaluation cutoff")


def stack_gate(fit_rows: Sequence[dict]) -> list[str]:
    n = len(fit_rows)
    k = sum(int(r["y"]) for r in fit_rows)
    days = len({_iso(float(r["decision_time"]))[:10] for r in fit_rows})
    out = []
    if n < STACK_GATE["min_events"]:
        out.append(f"events {n} < {STACK_GATE['min_events']}")
    if min(k, n - k) < STACK_GATE["min_per_class"]:
        out.append(f"per class {min(k, n - k)} < {STACK_GATE['min_per_class']}")
    if days < STACK_GATE["min_days"]:
        out.append(f"decision days {days} < {STACK_GATE['min_days']}")
    return out


def _logit(p: np.ndarray) -> np.ndarray:
    q = np.clip(np.asarray(p, float), LOGIT_CLIP, 1 - LOGIT_CLIP)
    return np.log(q / (1 - q))


def fit_stack(fit_rows: Sequence[dict], members: Sequence[str]) -> dict:
    """Logistic stack on the members' clipped logits; only after `stack_gate` passes (a fitted stack below it is refused)."""
    g = stack_gate(fit_rows)
    if g:
        raise RegistryError(f"stack below its training gate: {g}")
    X = np.column_stack([_logit(np.array([r["members"][m] for r in fit_rows], float)) for m in members])
    y = np.array([int(r["y"]) for r in fit_rows], float)
    lr = K.Logistic().fit(X, y)
    return {"members": list(members), "logistic": lr.to_dict()}


def predict_stack(stack: dict, rows: Sequence[dict]) -> np.ndarray:
    X = np.column_stack([_logit(np.array([r["members"][m] for r in rows], float)) for m in stack["members"]])
    return K.Logistic.from_dict(stack["logistic"]).predict_proba1(X)


def ensemble_decision(target: str, results: Sequence[dict]) -> dict:
    """ENSEMBLE only when an ensemble earned SKILL_INDICATED_DEVELOPMENT_ONLY against B2, survives the selection correction and
    its level could leave ABSTAIN; else NO_ENSEMBLE with the evidence per configuration."""
    ok = [r for r in results if r.get("verdict_vs_b2") == "SKILL_INDICATED_DEVELOPMENT_ONLY"
          and r.get("selection_status") == SELECTION_SURVIVES and r.get("level_possible") in PUBLISHABLE_LEVELS]
    ev = [{k: r.get(k) for k in ("configuration", "status", "verdict_vs_b0", "verdict_vs_b2", "selection_status", "reason")}
          for r in results]
    if ok:
        return {"kind": "ENSEMBLE_DECISION", "target": target, "decision": "ENSEMBLE", "configuration": ok[0]["configuration"],
                "evidence": ev}
    return {"kind": "ENSEMBLE_DECISION", "target": target, "decision": "NO_ENSEMBLE", "configuration": None,
            "reasons": ["NO_ENSEMBLE_EARNED_SKILL_OVER_B2", "NOTHING_BEATS_THE_BASE_RATE"], "evidence": ev}


# ---------------------------------------------------------------- target selection per opportunity (rule 11)
def target_plan(opportunity: dict, served: dict[str, dict]) -> list[dict]:
    """Which outcomes an opportunity is attempted for and what the publication path gets for each. Every registry target is
    listed; only PRIMARY targets are attempted; the forecast inputs are what `serve` allowed."""
    out = []
    for t, reg in C.TARGETS.items():
        row = {"target": t, "target_version": reg["version"], "horizon_seconds": reg.get("horizon_s"), "status": reg["status"]}
        if reg["status"] != "PRIMARY":
            row.update({"attempted": False, "reasons": ["TARGET_NOT_FEASIBLE"], "forecast_inputs": None})
        elif opportunity.get("chain") != reg.get("scope_chain", "solana"):
            row.update({"attempted": True, "reasons": ["OUT_OF_SCOPE_CHAIN"], "forecast_inputs": served[t]["forecast_inputs"]})
        else:
            s = served[t]
            rs = [] if s["use_champion"] else ["MODEL_NOT_SELECTED"]
            rs += sorted({THRESHOLDS[b["state"]]["contract_reason"] for b in s["blocking"] if b["state"] in THRESHOLDS})
            row.update({"attempted": True, "reasons": rs, "forecast_inputs": s["forecast_inputs"], "references_scored_internally":
                        sorted(s["references"]), "backtest_assessment_ref": None, "behavioral_scenarios": []})
        out.append(row)
    return out


# ---------------------------------------------------------------- shadow baseline mode: internal reference scores (rule 2)
REFERENCE_RECORD_VERSION = "reference-score-1"
DOCUMENT_KEYS = ("probability", "prediction_status", "forecast_id", "uncertainty_interval", "calibration_reference")


def reference_record(entry: dict, *, decision_key: str, decision_time: float, number: float | None, why: str | None,
                     as_of_utc: str) -> dict:
    """An internal record of a reference baseline's raw number for one decision, kept only for the prospective comparison
    (Phase 19). It is not a forecast document: it has none of the document keys, says `published` false, and carries the
    reference's states (a stale reference is recorded as stale, never refreshed)."""
    if entry["role"] != "REFERENCE_BASELINE":
        raise RegistryError("only a reference baseline is scored in shadow baseline mode")
    rows = inference_rows([(decision_key, number, why or "")])
    rec = {"record_version": REFERENCE_RECORD_VERSION, "kind": "REFERENCE_SCORE_INTERNAL", "published": False,
           "purpose": "PROSPECTIVE_COMPARISON_ONLY_NEVER_A_FORECAST", "target": entry["target"], "entry_id": entry["entry_id"],
           "reference": REFERENCE_NAMES[entry["family"]["kind"]], "model_id": entry["model_id"], "decision_key": decision_key,
           "decision_time_utc": _iso(decision_time), "raw_number": rows[0][1], "why": rows[0][2],
           "states": [s["state"] for s in status_at(entry, decision_time) if s["state"] != MODEL_NOT_PROMOTED],
           "as_of_utc": as_of_utc}
    rec["record_id"] = sha({k: v for k, v in rec.items() if k != "record_id"})
    return rec


def is_document(obj: dict) -> bool:
    """True when an object carries a forecast document key; a reference record never does."""
    return any(k in obj for k in DOCUMENT_KEYS)
