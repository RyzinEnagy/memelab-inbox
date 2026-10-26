"""Phase 13: abstention-1, the abstention conditions and the publication rule of every forecast (research only, flag OFF,
imported by no existing module). numpy and the standard library only; no network, no clock.

Pre-registration: audits/predictive-intelligence/phase_13/ACCEPTANCE_CHECKLIST.md (rules 6, 12 to 15) and PI-D-067.
  - 28 named conditions, each mapped to exactly one reason of the frozen contract (`contract.ABSTAIN_REASONS`, unchanged); every
    condition is evaluated (none short-circuits another), so a document lists every reason that applies;
  - a probability is issued only when no condition holds: flag ON, card level SHADOW or VALIDATED_EXPERIMENTAL, a CALIBRATED
    calibration card of the same model, enough support, a score inside the calibration range, a finite point inside the display
    range and inside its interval (P24, P38);
  - every result is a document of the frozen contract `memelab.predictive.forecast/1` plus an `abstention-1` record (attempted
    target and horizon, each condition with detail, contract reason and a plain explanation), persisted append-only (P39);
  - `validate_publication` adds the Phase 13 checks to `contract.validate`: `calibration_reference` keys allowlisted and equal to
    the stored calibration card (PI-D-022), the support interval inside the published one, the caveats, no probability-like
    entry in scenarios or cohort and no behavioral simulation as a source (P27).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from . import baselines as B
from . import calibration as CAL
from . import contract as C
from . import labels as L
from . import runtime as R
from . import stats as K
from . import store as S

PHASE = "13"
ABSTENTION_VERSION = "abstention-1"
SHADOW_CAVEAT = "SHADOW_RESEARCH_ONLY"
INTERVAL_CAVEAT = "INTERVAL_EXCLUDES_UNMODELED_RISK"
NEW_MINT_CAVEAT = "COHORT_ESTIMATE_NOT_TOKEN_HISTORY"
TOKEN_HISTORY_MIN_ROWS = 20
SIMULATION_MARKERS = ("mirofish", "oasis", "simulation", "simulated", "agent", "behavioral", "persona")
PROB_LIKE = re.compile(r"prob|likel|confid|share|vote|agree|pct|percent|odds|chance|consensus|certain", re.I)

# code -> (contract reason, plain explanation). Order is the order of evaluation and of the record.
CONDITIONS: dict[str, tuple[str, str]] = {
    "FLAG_OFF": ("FLAG_OFF", "the predictive flag is off, so nothing is published"),
    "CHAIN_OUT_OF_SCOPE": ("OUT_OF_SCOPE_CHAIN", "the target is defined for Solana decisions only"),
    "MINT_NOT_VERIFIED": ("UNVERIFIED_EVENT", "the token is not an exact verified address"),
    "TARGET_NOT_PRIMARY": ("TARGET_NOT_FEASIBLE", "the target is not one of the three pre-registered primary targets"),
    "POOL_NOT_POINT_IN_TIME": ("TARGET_NOT_FEASIBLE", "no point-in-time pool on the registered price route at the decision"),
    "MARKET_INACTIVE": ("NO_RECENT_PRICE", "no recent trade gives a reference price at the decision"),
    "SOURCE_GAP": ("SOURCE_STALE", "the price source or route failed or is unknown at the decision"),
    "DISALLOWED_INPUT": ("RESTRICTED_SOURCE", "an input is not allowed (sealed data, bake-off labels, a column outside the card, "
                                              "data available after the decision, or a simulation number)"),
    "SIZE_REQUESTED": ("EXECUTION_DATA_MISSING", "a position size needs executable depth, which has no history"),
    "BACKTEST_REQUIRED_NOT_AVAILABLE": ("EXECUTION_DATA_MISSING", "a stress assessment was required and backtesting is not available"),
    "MISSING_REQUIRED_INPUT": ("OOD", "a required model input is missing"),
    "FEATURE_OUT_OF_RANGE": ("OOD", "an input lies far outside the model's training range"),
    "SCORE_OUTSIDE_CALIBRATION_RANGE": ("OOD", "the model's raw number lies outside the range seen in calibration"),
    "NO_TOKEN_HISTORY": ("INSUFFICIENT_HISTORY", "the model needs this token's own history and there is not enough"),
    "MODEL_NOT_PROMOTED": ("MODEL_NOT_SELECTED", "the model has not reached SHADOW or VALIDATED_EXPERIMENTAL"),
    "NO_CHAMPION": ("MODEL_NOT_SELECTED", "no champion model exists for this target"),
    "MODEL_TRAINED_AFTER_DECISION": ("MODEL_NOT_SELECTED", "the model was trained after the decision, so it was not available then"),
    "MODEL_TOO_OLD": ("MODEL_STALE", "the model is more than 14 days older than the decision"),
    "FEATURE_SET_MISMATCH": ("FEATURE_SCHEMA_MISMATCH", "the inputs come from another feature set than the model's"),
    "INVALID_PROBABILITY": ("MODEL_NOT_SELECTED", "the model or calibrator produced a number that is not a finite probability"),
    "NO_CALIBRATOR": ("UNCALIBRATED", "no calibration of this model has passed the frozen check"),
    "DEGENERATE_FLAT_PREDICTIONS": ("UNCALIBRATED", "the model gives the same number for everything"),
    "POINT_OUTSIDE_DISPLAY_RANGE": ("UNCALIBRATED", "the calibrated number is more extreme than the evidence can support"),
    "CALIBRATION_SET_TOO_SMALL": ("INSUFFICIENT_HISTORY", "too few out-of-sample outcomes to fit a calibration"),
    "CALIBRATION_EVIDENCE_TOO_SMALL": ("INSUFFICIENT_HISTORY", "too few independent outcomes to check a calibration"),
    "LOW_SUPPORT": ("INSUFFICIENT_HISTORY", "too few calibration outcomes near this model number"),
    "CALIBRATION_EVIDENCE_PENDING": ("NOT_YET_MATURED", "the outcomes that would check the calibration have not matured"),
    "DRIFT": ("DRIFT_ALERT", "the model's recent errors drifted upward"),
}
assert all(r in C.ABSTAIN_REASONS for r, _ in CONDITIONS.values())
TRADING_WORDS = ("buy", "sell", "long", "short", "entry", "exit now", "moon", "pump", "guaranteed", "signal", "target hit")


class PublicationError(ValueError):
    pass


def canon(o: Any) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(o: Any) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


def _iso(t: float) -> str:
    import datetime as _dt
    return _dt.datetime.fromtimestamp(float(t), _dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fin(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _cond(code: str, detail: str = "") -> dict:
    reason, text = CONDITIONS[code]
    return {"code": code, "reason": reason, "detail": detail, "explanation": text}


# ---------------------------------------------------------------- input checks
def mint_verified(chain: Any, mint: Any) -> bool:
    try:
        S.check_address(chain, mint)
        return True
    except Exception:
        return False


def disallowed_inputs(req: dict, allowed_columns: Iterable[str]) -> list[str]:
    out = []
    for p in req.get("input_paths") or []:
        try:
            L.refuse_sealed(p)
            R.refuse_bakeoff_labels(path=p)
        except Exception as e:
            out.append(f"path refused: {type(e).__name__}")
    try:
        R.refuse_bakeoff_labels(list(req.get("input_rows") or []))
    except Exception as e:
        out.append(f"row refused: {type(e).__name__}")
    allowed = set(allowed_columns)
    extra = sorted(set((req.get("x") or {}).keys()) - allowed)
    if extra:
        out.append(f"columns outside the card's allowlist: {extra}")
    T = float(req["decision_time"])
    xs, av = req.get("x") or {}, req.get("avail") or {}
    late = sorted(c for c, v in xs.items() if _fin(v) and (not _fin(av.get(c)) or float(av[c]) > T))
    if late:
        out.append(f"inputs without availability at or before the decision: {late}")
    if req.get("behavioral_inputs"):
        out.append("a behavioral-simulation number was passed as an input (P27)")
    if req.get("decision_time_basis") not in C.DECISION_TIME_BASES:
        out.append(f"decision time basis {req.get('decision_time_basis')!r} (PI-D-011)")
    return out


def out_of_range(card: dict, x: dict) -> list[str]:
    """Required inputs whose value, standardised by the card's own training preprocessing, has |z| above the frozen bound."""
    body = card.get("body") or {}
    if "prep" not in body or "columns" not in body:
        return []
    cols, req_cols = list(body["columns"]), set(body.get("required") or body["columns"])
    vals = [x.get(c, float("nan")) for c in cols]
    vals = [float(v) if _fin(v) else float("nan") for v in vals]
    prep = K.Prep.from_dict(body["prep"])
    z = prep.transform(np.asarray([vals], float))[0]
    out = []
    for i, j in enumerate(prep.keep):
        c = cols[int(j)]
        if c in req_cols and math.isfinite(vals[int(j)]) and abs(float(z[i])) > CAL.OOD_Z:
            out.append(f"{c} z={float(z[i]):.2f}")
    return out


# ---------------------------------------------------------------- evaluation of one request
def evaluate(req: dict, *, card: dict | None, level: str, cal_card: dict | None, raw: float | None, raw_why: str | None = None,
             drift_alarms: Sequence[float] = (), backtest_status: str | None = None,
             allowed_columns: Iterable[str] = B.ALLOWED_COLUMNS) -> dict:
    """Every condition of rule 12 for one (decision, target) request, plus the calibrated point, interval and support when they
    exist. `raw` is the champion card's own number for the request (from the card's predict), `raw_why` its reason when it has
    none. Nothing here short-circuits: all conditions are evaluated and returned."""
    tgt = req["target"]
    reg = C.TARGETS.get(tgt, {})
    T = float(req["decision_time"])
    conds: list[dict] = []
    refused = None
    if cal_card is not None:
        try:
            CAL.verify_card(cal_card)
        except Exception as e:                    # a tampered or foreign calibration card counts as none (self-review pass 2)
            refused, cal_card = f"calibration card refused: {type(e).__name__}", None
    if req.get("flag_on") is not True:
        conds.append(_cond("FLAG_OFF"))
    if req.get("chain") != reg.get("scope_chain", "solana"):
        conds.append(_cond("CHAIN_OUT_OF_SCOPE", f"chain {req.get('chain')!r}"))
    if not mint_verified(req.get("chain"), req.get("mint")):
        conds.append(_cond("MINT_NOT_VERIFIED"))
    if tgt not in C.PRIMARY:
        conds.append(_cond("TARGET_NOT_PRIMARY", f"{tgt} is {reg.get('status', 'UNKNOWN')}"))
    if req.get("pool_point_in_time") is not True:
        conds.append(_cond("POOL_NOT_POINT_IN_TIME", f"route {req.get('route')!r}"))
    el = req.get("eligibility")
    if el == "MARKET_INACTIVE":
        conds.append(_cond("MARKET_INACTIVE"))
    elif el != "ELIGIBLE":
        conds.append(_cond("SOURCE_GAP", f"eligibility {el!r}"))
    bad = disallowed_inputs(req, allowed_columns)
    if bad:
        conds.append(_cond("DISALLOWED_INPUT", "; ".join(bad)))
    if req.get("position_usd") is not None:
        conds.append(_cond("SIZE_REQUESTED", "NO_HISTORICAL_EXECUTABLE_DEPTH"))
    bt = backtest_status if backtest_status is not None else C.backtest_status()
    if req.get("backtest_required") and bt != "VERIFIED":
        conds.append(_cond("BACKTEST_REQUIRED_NOT_AVAILABLE", bt))
    x = req.get("x") or {}
    if card is not None:
        body = card.get("body") or {}
        need = list(body.get("required") or [])
        miss = sorted(c for c in need if not _fin(x.get(c)))
        if miss or raw_why == "OOD":
            conds.append(_cond("MISSING_REQUIRED_INPUT", f"{miss}" if miss else "the card's predict gave OOD"))
        far = out_of_range(card, x) if not miss else []
        if far:
            conds.append(_cond("FEATURE_OUT_OF_RANGE", "; ".join(far)))
    support = None
    if cal_card is not None and _fin(raw) and 0.0 <= float(raw) <= 1.0 and cal_card.get("support_bins"):
        support = CAL.support_of(cal_card["support_bins"], float(raw))
        if support is None:
            conds.append(_cond("SCORE_OUTSIDE_CALIBRATION_RANGE", f"raw {float(raw):.4f}"))
    if card is not None and card.get("needs_token_history") is True and int(req.get("token_history_rows") or 0) < TOKEN_HISTORY_MIN_ROWS:
        conds.append(_cond("NO_TOKEN_HISTORY", f"{int(req.get('token_history_rows') or 0)} matured rows of this mint"))
    if level not in CAL.PUBLISHABLE_LEVELS:
        conds.append(_cond("MODEL_NOT_PROMOTED", f"level {level}"))
    elif cal_card is not None and cal_card.get("level") != level:
        conds.append(_cond("MODEL_NOT_PROMOTED", f"level {level} differs from the calibration card's {cal_card.get('level')}"))
    if card is None:
        conds.append(_cond("NO_CHAMPION"))
    elif "abstain" in (card.get("body") or {}):
        conds.append(_cond("NO_CHAMPION", f"the champion card is not fitted ({card['body']['abstain']})"))
    if card is not None:
        cut = float(card["training_cutoff"]) if "training_cutoff" in card else C.parse_utc(card["training_cutoff_utc"])
        if cut > T:
            conds.append(_cond("MODEL_TRAINED_AFTER_DECISION", f"cutoff {_iso(cut)}"))
        elif T - cut > C.ACCEPTANCE["max_model_age_s"]:
            conds.append(_cond("MODEL_TOO_OLD", f"cutoff {_iso(cut)}"))
        if req.get("feature_set_sha") != card.get("feature_set_sha"):
            conds.append(_cond("FEATURE_SET_MISMATCH"))
    if raw is not None and not (_fin(raw) and 0.0 <= float(raw) <= 1.0):
        conds.append(_cond("INVALID_PROBABILITY", f"raw {raw!r}"))
    cal_ok = (cal_card is not None and cal_card.get("status") == CAL.CALIBRATED and card is not None
              and cal_card.get("champion_model_sha") == card.get("model_sha") and cal_card.get("target") == tgt)
    if not cal_ok:
        why = (refused or "no calibration card") if cal_card is None else (
            "calibration card of another model or target" if card is not None and (cal_card.get("champion_model_sha") != card.get("model_sha")
                                                                                   or cal_card.get("target") != tgt)
            else f"status {cal_card.get('status')}")
        conds.append(_cond("NO_CALIBRATOR", why))
    details = set((cal_card or {}).get("details") or [])
    if cal_card is not None and ((cal_card.get("degeneracy") or {}).get("flat") or "DEGENERATE_FLAT_PREDICTIONS" in details):
        conds.append(_cond("DEGENERATE_FLAT_PREDICTIONS"))
    if cal_card is None or not (cal_card.get("fit_gate") or {}).get("passed"):
        sh = (cal_card or {}).get("fit_gate", {}).get("shortfalls") if cal_card else ["no calibration set"]
        conds.append(_cond("CALIBRATION_SET_TOO_SMALL", "; ".join(sh or [])))
    ev = (cal_card or {}).get("evidence") or {"status": "NONE", "n": 0, "k": 0}
    if ev.get("status") == "NOT_YET_MATURED":
        conds.append(_cond("CALIBRATION_EVIDENCE_PENDING", "prospective holdout labels not matured (Phase 19)"))
        conds.append(_cond("CALIBRATION_EVIDENCE_TOO_SMALL", "0 matured evidence events"))
    elif CAL.evidence_gate(int(ev.get("n") or 0), int(ev.get("k") or 0)):
        conds.append(_cond("CALIBRATION_EVIDENCE_TOO_SMALL", "; ".join(CAL.evidence_gate(int(ev.get("n") or 0), int(ev.get("k") or 0)))))
    point = iv = None
    if cal_ok and _fin(raw) and 0.0 <= float(raw) <= 1.0:
        try:
            p, lo, hi = CAL.apply_calibrator(cal_card["calibrator"], [float(raw)])
            point = float(p[0])
            if support is not None:
                iv = CAL.interval(float(lo[0]), float(hi[0]), int(support["n"]), int(support["k"]))
        except Exception as e:
            conds.append(_cond("INVALID_PROBABILITY", f"calibrator: {type(e).__name__}"))
            point = iv = None
        if point is not None and not (CAL.DISPLAY_RANGE[0] <= point <= CAL.DISPLAY_RANGE[1]):
            conds.append(_cond("POINT_OUTSIDE_DISPLAY_RANGE", f"{point:.4f}"))
    if support is None or int(support["n"]) < CAL.SUPPORT_MIN:
        conds.append(_cond("LOW_SUPPORT", "no calibration bin holds this number" if support is None
                           else f"{int(support['n'])} calibration events in the bin"))
    if drift_at(drift_alarms, T):
        conds.append(_cond("DRIFT", f"alarm at {_iso(min(a for a in drift_alarms if a <= T))}"))
    order = list(CONDITIONS)
    conds.sort(key=lambda c: order.index(c["code"]))
    return {"conditions": conds, "point": point, "interval": iv, "support": support}


def drift_at(alarms: Sequence[float], decision_time: float) -> bool:
    return CAL.drift_at(alarms, decision_time)


def reasons_of(conds: Sequence[dict]) -> list[str]:
    got = {c["reason"] for c in conds}
    return [r for r in C.ABSTAIN_REASONS if r in got]


# ---------------------------------------------------------------- documents and records
def build(req: dict, ev: dict, *, card: dict | None, level: str, cal_card: dict | None, generated_at_utc: str,
          is_fixture: bool = False) -> tuple[dict, dict]:
    """The contract document and the abstention-1 record of one evaluated request. FORECAST only when no condition holds."""
    tgt = req["target"]
    reg = C.TARGETS.get(tgt)
    if reg is None:
        raise PublicationError(f"unknown target {tgt!r}")
    conds = ev["conditions"]
    T = float(req["decision_time"])
    base = (float(card["k_train"]) / float(card["n_train"])) if card and card.get("n_train") else None
    if conds:
        doc = {"contract_version": C.CONTRACT_VERSION, "chain": req["chain"], "mint_address": req["mint"],
               "snapshot_hash": req["snapshot_hash"], "decision_time_utc": _iso(T), "decision_time_basis": req.get("decision_time_basis"),
               "target": tgt, "target_version": reg["version"], "horizon_seconds": reg["horizon_s"], "position_usd": None,
               "probability": None, "prediction_status": "ABSTAIN", "abstain_reasons": reasons_of(conds),
               "uncertainty_interval": None, "base_rate": base, "calibration_reference": None,
               "training_cutoff_utc": card["training_cutoff_utc"] if card else None,
               "model_id": card["model_id"] if card else "not_selected", "model_sha": card["model_sha"] if card else None,
               "feature_set_sha": card["feature_set_sha"] if card else None,
               "data_snapshot_sha": card["data_snapshot_sha"] if card else None, "cohort": None, "evidence_refs": [],
               "backtest_status": C.backtest_status(), "backtest_assessment_ref": None, "execution_stress_assessment_ref": None,
               "behavioral_scenarios": [], "caveats": list(reg.get("caveats") or [reg["status"]]), "is_fixture": bool(is_fixture),
               "generated_at_utc": generated_at_utc}
        doc["forecast_id"] = C.forecast_id(req["chain"], req["mint"], req["snapshot_hash"], tgt, reg["version"],
                                           reg["horizon_s"], doc["model_sha"])
    else:
        caveats = list(reg["caveats"]) + [INTERVAL_CAVEAT]
        if level == "SHADOW":
            caveats.append(SHADOW_CAVEAT)
        if req.get("new_mint"):
            caveats.append(NEW_MINT_CAVEAT)
        sup = ev["support"]
        doc = {"contract_version": C.CONTRACT_VERSION, "chain": req["chain"], "mint_address": req["mint"],
               "snapshot_hash": req["snapshot_hash"], "decision_time_utc": _iso(T), "decision_time_basis": req["decision_time_basis"],
               "target": tgt, "target_version": reg["version"], "horizon_seconds": reg["horizon_s"], "position_usd": None,
               "probability": float(ev["point"]), "prediction_status": "FORECAST", "abstain_reasons": [],
               "uncertainty_interval": [float(v) for v in ev["interval"]], "base_rate": base,
               "calibration_reference": CAL.reference(cal_card, support_n=int(sup["n"]), support_k=int(sup["k"])),
               "training_cutoff_utc": card["training_cutoff_utc"], "model_id": card["model_id"], "model_sha": card["model_sha"],
               "feature_set_sha": card["feature_set_sha"], "data_snapshot_sha": card["data_snapshot_sha"],
               "cohort": {"new_mint": bool(req.get("new_mint")), "route": req.get("route")}, "evidence_refs": [],
               "backtest_status": C.backtest_status(), "backtest_assessment_ref": None, "execution_stress_assessment_ref": None,
               "behavioral_scenarios": [], "caveats": caveats, "is_fixture": bool(is_fixture), "generated_at_utc": generated_at_utc}
        doc["forecast_id"] = C.forecast_id(req["chain"], req["mint"], req["snapshot_hash"], tgt, reg["version"], reg["horizon_s"],
                                           card["model_sha"])
    rec = {"record_version": ABSTENTION_VERSION, "forecast_id": doc["forecast_id"], "chain": req["chain"], "mint": req["mint"],
           "target": tgt, "target_version": reg["version"], "horizon_seconds": reg["horizon_s"], "decision_time_utc": _iso(T),
           "decision_time_basis": req.get("decision_time_basis"), "prediction_status": doc["prediction_status"],
           "conditions": [dict(c) for c in conds], "reasons": reasons_of(conds),
           "model_id": doc["model_id"], "model_sha": doc["model_sha"], "level": level,
           "calibration_card_sha": (cal_card or {}).get("card_sha"), "calibration_status": (cal_card or {}).get("status"),
           "is_fixture": bool(is_fixture), "generated_at_utc": generated_at_utc}
    rec["record_id"] = sha({k: v for k, v in rec.items() if k != "record_id"})
    refs = [f"{ABSTENTION_VERSION}:{rec['record_id']}"]
    if cal_card is not None:
        refs.append(f"{CAL.CALIBRATION_VERSION}:{cal_card['card_sha']}")
    doc["evidence_refs"] = refs
    return doc, rec


def forecast_result(req: dict, *, card: dict | None, level: str, cal_card: dict | None, raw: float | None,
                    raw_why: str | None = None, drift_alarms: Sequence[float] = (), generated_at_utc: str,
                    backtest_status: str | None = None, is_fixture: bool = False) -> tuple[dict, dict]:
    ev = evaluate(req, card=card, level=level, cal_card=cal_card, raw=raw, raw_why=raw_why, drift_alarms=drift_alarms,
                  backtest_status=backtest_status)
    return build(req, ev, card=card, level=level, cal_card=cal_card, generated_at_utc=generated_at_utc, is_fixture=is_fixture)


# ---------------------------------------------------------------- the publication validator
def _plain(v: Any) -> bool:
    return isinstance(v, str) or (isinstance(v, list) and all(isinstance(x, str) for x in v))


def validate_publication(doc: dict, *, model_card: dict | None, calibration_card: dict | None, record: dict | None = None,
                         backtest: str | None = None) -> list[str]:
    """`contract.validate` plus the Phase 13 rules. Empty list: the document may be shown."""
    if not isinstance(doc, dict):
        return ["document is not an object"]
    st = doc.get("prediction_status")
    errs = C.validate(doc, model_card=model_card if st == "FORECAST" else None, backtest=backtest)
    for s in doc.get("behavioral_scenarios") or []:
        if not isinstance(s, dict) or any(PROB_LIKE.search(str(k)) for k in s) or not all(_plain(v) for v in s.values()):
            errs.append("a behavioral scenario carries a number or a probability-like field: scenario labels only (P27)")
    coh = doc.get("cohort")
    if coh is not None:
        if not isinstance(coh, dict) or any(PROB_LIKE.search(str(k)) for k in coh) or any(isinstance(v, float) for v in coh.values()):
            errs.append("cohort carries a probability-like field or a fraction (P27)")
    mid = str(doc.get("model_id") or "").lower() + " " + str((model_card or {}).get("kind") or "").lower()
    if st == "FORECAST" and any(m in mid for m in SIMULATION_MARKERS):
        errs.append("a behavioral simulation is never a forecast source (P27)")
    ref = doc.get("calibration_reference")
    if ref is not None:
        if not isinstance(ref, dict):
            errs.append("calibration_reference is not an object")
        else:
            extra = sorted(set(ref) - set(CAL.REFERENCE_KEYS))
            if extra:
                errs.append(f"calibration_reference has keys outside the allowlist: {extra} (PI-D-022)")
    if st == "FORECAST":
        errs += _forecast_checks(doc, model_card, calibration_card, ref)
        if record is not None and record.get("conditions"):
            errs.append("a FORECAST whose record lists abstention conditions")
    elif st == "ABSTAIN" and record is not None:
        if record.get("forecast_id") != doc.get("forecast_id"):
            errs.append("abstention record of another forecast")
        if record.get("target") != doc.get("target") or record.get("horizon_seconds") != doc.get("horizon_seconds"):
            errs.append("abstention record does not name the attempted target and horizon")
        if not record.get("conditions"):
            errs.append("ABSTAIN without a persisted condition")
        if sorted(set(record.get("reasons") or [])) != sorted(set(doc.get("abstain_reasons") or [])) or \
                sorted({c.get("reason") for c in record.get("conditions") or []}) != sorted(set(doc.get("abstain_reasons") or [])):
            errs.append("the document's reasons differ from the persisted conditions (hidden or invented reason)")
        if record.get("record_id") != sha({k: v for k, v in record.items() if k != "record_id"}):
            errs.append("abstention record content does not match its record_id")
        if f"{ABSTENTION_VERSION}:{record.get('record_id')}" not in (doc.get("evidence_refs") or []):
            errs.append("the document does not reference its abstention record")
    return errs


def _forecast_checks(doc: dict, model_card: dict | None, cal: dict | None, ref: Any) -> list[str]:
    errs = []
    if cal is None:
        return ["FORECAST without its calibration card"]
    try:
        CAL.verify_card(cal)
    except Exception as e:
        return [f"calibration card refused: {e}"]
    if cal["status"] != CAL.CALIBRATED:
        errs.append(f"calibration card is {cal['status']}: no probability (UNCALIBRATED)")
    if cal["level"] not in CAL.PUBLISHABLE_LEVELS:
        errs.append(f"card level {cal['level']}: a probability needs SHADOW or VALIDATED_EXPERIMENTAL")
    if cal["target"] != doc.get("target") or cal["champion_model_sha"] != doc.get("model_sha"):
        errs.append("calibration card of another target or model")
    if not isinstance(ref, dict):
        return errs + ["FORECAST without calibration_reference"]
    if sorted(ref) != sorted(CAL.REFERENCE_KEYS):
        errs.append("calibration_reference keys differ from the allowlist")
    want = CAL.reference(cal, support_n=int(ref.get("support_n") or 0), support_k=int(ref.get("support_k") or 0))
    for k in CAL.REFERENCE_KEYS:
        if k in ("support_n", "support_k"):
            continue
        if ref.get(k) != want.get(k):
            errs.append(f"calibration_reference {k} {ref.get(k)!r} differs from the stored card {want.get(k)!r} (PI-D-022)")
    sn, sk = ref.get("support_n"), ref.get("support_k")
    if not (isinstance(sn, int) and isinstance(sk, int) and 0 <= sk <= sn) or sn < CAL.SUPPORT_MIN:
        errs.append(f"support below {CAL.SUPPORT_MIN} calibration events (P24)")
    elif not any(int(b["n"]) == sn and int(b["k"]) == sk for b in cal.get("support_bins") or []):
        errs.append("support_n and support_k are not a support bin of the stored card (PI-D-022, self-review pass 2)")
    else:
        wl, wh = K.wilson(sk, sn)
        iv = doc.get("uncertainty_interval")
        if not (isinstance(iv, list) and len(iv) == 2 and all(_fin(v) for v in iv) and iv[0] <= wl + 1e-12 and iv[1] >= wh - 1e-12):
            errs.append("the interval is narrower than the Wilson interval of its support (P23, P24)")
    if model_card is not None and model_card.get("n_train"):
        want_base = float(model_card["k_train"]) / float(model_card["n_train"])
        if not (_fin(doc.get("base_rate")) and abs(float(doc["base_rate"]) - want_base) <= 1e-12):
            errs.append("base_rate is not the model card's training prevalence (self-review pass 2)")
    p = doc.get("probability")
    if not (_fin(p) and CAL.DISPLAY_RANGE[0] <= p <= CAL.DISPLAY_RANGE[1]):
        errs.append(f"probability outside the display range {CAL.DISPLAY_RANGE}")
    cav = doc.get("caveats") or []
    if INTERVAL_CAVEAT not in cav:
        errs.append(f"FORECAST without {INTERVAL_CAVEAT}")
    if cal["level"] == "SHADOW" and SHADOW_CAVEAT not in cav:
        errs.append(f"SHADOW forecast without its label {SHADOW_CAVEAT}")
    if (doc.get("cohort") or {}).get("new_mint") and NEW_MINT_CAVEAT not in cav:
        errs.append(f"new-mint forecast without {NEW_MINT_CAVEAT} (P12)")
    return errs


# ---------------------------------------------------------------- persistence (append-only) and plain language
def file_sha(path: str | Path) -> str | None:
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def append(path: str | Path, records: Sequence[dict], *, expect_sha: str | None) -> str:
    """Append records as JSON lines. `expect_sha` is the sha256 the file had after the last append (None for a new file); a
    file that changed in between (an earlier record rewritten or dropped) is refused, so the audit trail is never rewritten."""
    p = Path(path)
    now = file_sha(p)
    if now != expect_sha:
        raise PublicationError(f"{p.name}: the record file changed since its last append (expected {expect_sha}, found {now})")
    for r in records:
        if r.get("record_id") != sha({k: v for k, v in r.items() if k != "record_id"}):
            raise PublicationError("record content does not match its record_id")
    with open(p, "a") as f:
        for r in records:
            f.write(canon(r) + "\n")
    return file_sha(p)


def is_append_only(old_text: str, new_text: str) -> bool:
    return new_text.startswith(old_text) and (old_text == "" or old_text.endswith("\n"))


HORIZON_WORDS = {86400: "24 hours", 21600: "6 hours"}
EVENT_WORDS = {"price_path_target_before_invalidation_24h": "the price rises 25 percent before it falls 15 percent",
               "price_path_target_before_invalidation_6h": "the price rises 25 percent before it falls 15 percent",
               "price_path_severe_drawdown_or_halt_24h": "the price halves or trading halts"}


def describe(doc: dict, record: dict | None = None) -> str:
    """Plain language for one document. ABSTAIN shows no number; FORECAST shows the number with its interval and level.
    Never a trading word."""
    ev = EVENT_WORDS.get(doc.get("target"), str(doc.get("target")))
    hz = HORIZON_WORDS.get(doc.get("horizon_seconds"), f"{doc.get('horizon_seconds')} s")
    if doc.get("prediction_status") != "FORECAST":
        texts = [c["explanation"] for c in (record or {}).get("conditions") or []] or list(doc.get("abstain_reasons") or [])
        out = f"No probability for whether {ev} within {hz}: " + "; ".join(texts) + "."
    else:
        lo, hi = doc["uncertainty_interval"]
        lvl = (doc.get("calibration_reference") or {}).get("level")
        out = (f"Research estimate ({lvl}), not advice: chance that {ev} within {hz} is {doc['probability']:.0%} "
               f"(interval {lo:.0%} to {hi:.0%}; the interval leaves out risks the model does not see).")
    low = out.lower()
    if any(re.search(r"\b" + re.escape(w) + r"\b", low) for w in TRADING_WORDS):
        raise PublicationError("plain-language text would carry a trading word")
    return out
