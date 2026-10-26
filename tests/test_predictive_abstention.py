"""Phase 13: abstention-1 (memelab/predictive/abstention.py), the publication rule and the ForecastResult schema. Synthetic
fixtures only (every FORECAST here is a fixture: no real card is calibrated); no network, no clock, no store, no holdout."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
import pytest

from memelab.predictive import abstention as AB
from memelab.predictive import baselines as B
from memelab.predictive import calibration as CAL
from memelab.predictive import contract as C
from memelab.predictive import evaluation as E
from memelab.predictive import labels as L

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "audits/predictive-intelligence/phase_13/models/FORECAST_RESULT_SCHEMA.json").read_text())
H = L.holdout_start()
P0 = CAL.PROSPECTIVE_START
DAY = 86400.0
T1 = L.T1
BT = C.BACKTEST_NOT_AVAILABLE
_ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def mint(i: int) -> str:
    n = int.from_bytes(hashlib.sha256(f"m{i}".encode()).digest(), "big")
    s = ""
    while n:
        n, r = divmod(n, 58)
        s = _ALPH[r] + s
    return s


def _example(i, t, rng, *, y=None):
    x = {c: float(rng.normal()) for c in sorted(B.ALLOWED_COLUMNS)}
    x[B.FATAL] = float(rng.integers(0, 2))
    if y is None:
        y = int(rng.random() < 1 / (1 + math.exp(-(1.2 * x[B.LIQ] - 0.8))))
    return B.Example(decision_key=f"k{i}", chain="solana", mint=mint(i), decision_time=t, label_matures_at=t + DAY, y=y, x=x,
                     avail={c: t for c in x})


def world(seed: int = 1, *, level: str = "SHADOW", fit_n: int = 300, ev_n: int = 120, flat: bool = False,
          evidence: str = "ADMISSIBLE"):
    """A B2 card trained at H, a calibration card on its out-of-sample development scores and prospective evidence, and a
    request at P0 + 6 days whose every condition holds (a FIXTURE: nothing real is calibrated)."""
    rng = np.random.default_rng(seed)
    train = [_example(i, H - 40 * DAY + i * 3000.0, rng) for i in range(260)]
    card = B.fit_b2(T1, train, H)
    dev = [_example(1000 + i, H - 12 * DAY + i * 2400.0, rng) for i in range(fit_n)]
    p = B.predict(card, dev)[0] if not flat else np.full(fit_n, 0.4)
    rows = [{"decision_key": e.decision_key, "mint": e.mint, "decision_time": e.decision_time, "label_matures_at": e.label_matures_at,
             "y": e.y, "score": float(s), "scored_by_cutoff": e.decision_time - 60.0, "split": "DEVELOPMENT"} for e, s in zip(dev, p)]
    ev_ex = [_example(5000 + i, P0 + i * 1800.0, rng) for i in range(ev_n)]
    pe = B.predict(card, ev_ex)[0]
    ev_rows = [{"decision_key": e.decision_key, "mint": e.mint, "decision_time": e.decision_time, "label_matures_at": e.label_matures_at,
                "y": e.y, "score": float(s), "scored_by_cutoff": H, "split": "PROSPECTIVE"} for e, s in zip(ev_ex, pe)]
    ev = ({"status": "ADMISSIBLE", "rows": ev_rows, "fit_cutoff": H, "cutoff": P0 + 5 * DAY, "source": "PROSPECTIVE_HOLDOUT"}
          if evidence == "ADMISSIBLE" else {"status": "NOT_YET_MATURED", "source": "PROSPECTIVE_HOLDOUT"})
    cal = CAL.build_card(T1, card, rows, H, level=level, evidence=ev, is_fixture=True)
    q = _example(9000, P0 + 6 * DAY, rng)
    q.x = {c: 0.05 for c in B.ALLOWED_COLUMNS}
    q.x[B.FATAL] = 0.0
    q.avail = {c: q.decision_time - 600.0 for c in q.x}
    req = {"chain": "solana", "mint": q.mint, "target": T1, "decision_time": q.decision_time, "decision_time_basis": "CAPTURE_TIME",
           "snapshot_hash": "b" * 64, "flag_on": True, "pool_point_in_time": True, "route": "CAPTURE", "eligibility": "ELIGIBLE",
           "position_usd": None, "backtest_required": False, "x": q.x, "avail": q.avail, "feature_set_sha": card["feature_set_sha"],
           "new_mint": False, "token_history_rows": 0}
    raw, why = B.predict(card, [q])
    return {"req": req, "card": card, "level": level, "cal": cal, "raw": float(raw[0]), "raw_why": why[0], "drift": [],
            "rows": rows}


def run(w, **kw):
    a = dict(card=w["card"], level=w["level"], cal_card=w["cal"], raw=w["raw"], raw_why=w["raw_why"], drift_alarms=w["drift"],
             generated_at_utc="2026-11-01T00:00:00Z", backtest_status=BT, is_fixture=True)
    a.update(kw)
    return AB.forecast_result(w["req"], **a)


@pytest.fixture(scope="module")
def good():
    return world()


# ---------------------------------------------------------------- the vocabulary
def test_every_condition_maps_to_one_frozen_contract_reason_and_matches_the_preregistration():
    assert len(AB.CONDITIONS) == 28
    assert all(r in C.ABSTAIN_REASONS for r, _ in AB.CONDITIONS.values())
    chk = (ROOT / "audits/predictive-intelligence/phase_13/ACCEPTANCE_CHECKLIST.md").read_text()
    rule12 = chk.split("12. Abstention conditions")[1].split("13. Persistence")[0]
    listed = re.findall(r"^    - ([A-Z_]+): .*\(([A-Z_]+)(?:[,;)])", rule12, re.M)
    assert {c for c, _ in listed} == set(AB.CONDITIONS)
    for code, reason in listed:
        assert AB.CONDITIONS[code][0] == reason, code
    assert C.CONTRACT_VERSION == "memelab.predictive.forecast/1" and C.registry_sha256().startswith("4b4aabce")


# ---------------------------------------------------------------- the publication path (fixture only)
def test_a_request_meeting_every_condition_publishes_a_valid_forecast(good):
    doc, rec = run(good)
    assert doc["prediction_status"] == "FORECAST" and rec["conditions"] == [] and rec["reasons"] == []
    assert C.validate(doc, model_card=good["card"], backtest=BT) == []
    assert AB.validate_publication(doc, model_card=good["card"], calibration_card=good["cal"], record=rec, backtest=BT) == []
    lo, hi = doc["uncertainty_interval"]
    assert lo <= doc["probability"] <= hi and CAL.DISPLAY_RANGE[0] <= doc["probability"] <= CAL.DISPLAY_RANGE[1]
    assert AB.SHADOW_CAVEAT in doc["caveats"] and AB.INTERVAL_CAVEAT in doc["caveats"] and doc["is_fixture"] is True
    assert schema_errors({"document": doc, "record": rec}) == []
    assert "Research estimate (SHADOW)" in AB.describe(doc, rec)


def _set(path, value):
    def f(w):
        obj = w
        for k in path[:-1]:
            obj = obj[k]
        obj[path[-1]] = value
    return f


def _cal(**kw):
    def f(w):
        ww = world(**kw)
        w["cal"] = ww["cal"]
    return f


def _card_flag(w):
    w["card"] = dict(w["card"], needs_token_history=True)


SINGLE = {
    "FLAG_OFF": _set(("req", "flag_on"), False),
    "CHAIN_OUT_OF_SCOPE": lambda w: w["req"].update(chain="base", mint="0x" + "ab" * 20),
    "MINT_NOT_VERIFIED": _set(("req", "mint"), "MukLDtJ8Cx9DxLbeyLRWPSposTMWuwHANbuaudpump"),
    "TARGET_NOT_PRIMARY": _set(("req", "target"), "exit_adjusted_target_before_invalidation_24h"),
    "POOL_NOT_POINT_IN_TIME": lambda w: w["req"].update(pool_point_in_time=False, route="CURRENT_VENDOR_LIST"),
    "MARKET_INACTIVE": _set(("req", "eligibility"), "MARKET_INACTIVE"),
    "SOURCE_GAP": _set(("req", "eligibility"), "VENDOR_OR_ROUTE_GAP"),
    "DISALLOWED_INPUT": _set(("req", "input_paths"), [str(ROOT / "audits/predictive-intelligence/phase_06/sealed/holdout_labels.jsonl.gz")]),
    "SIZE_REQUESTED": _set(("req", "position_usd"), 500),
    "BACKTEST_REQUIRED_NOT_AVAILABLE": _set(("req", "backtest_required"), True),
    "MISSING_REQUIRED_INPUT": lambda w: w["req"]["x"].update({B.LIQ: float("nan")}),
    "FEATURE_OUT_OF_RANGE": lambda w: w["req"]["x"].update({B.LIQ: 60.0}),
    "SCORE_OUTSIDE_CALIBRATION_RANGE": lambda w: w.update(raw=min(1.0, max(r["score"] for r in w["rows"]) + 1e-4)),
    "NO_TOKEN_HISTORY": _card_flag,
    "MODEL_NOT_PROMOTED": _set(("level",), "ABSTAIN"),
    "NO_CHAMPION": _set(("card",), None),
    "MODEL_TRAINED_AFTER_DECISION": _set(("req", "decision_time"), H - 3 * DAY),
    "MODEL_TOO_OLD": _set(("req", "decision_time"), H + 15 * DAY),
    "FEATURE_SET_MISMATCH": _set(("req", "feature_set_sha"), "0" * 64),
    "INVALID_PROBABILITY": _set(("raw",), float("nan")),
    "NO_CALIBRATOR": _set(("cal",), None),
    "DEGENERATE_FLAT_PREDICTIONS": _cal(flat=True),
    "CALIBRATION_SET_TOO_SMALL": _cal(fit_n=60),
    "CALIBRATION_EVIDENCE_TOO_SMALL": _cal(ev_n=40),
    "CALIBRATION_EVIDENCE_PENDING": _cal(evidence="NOT_YET_MATURED"),
    "DRIFT": lambda w: w.update(drift=[w["req"]["decision_time"] - 3600.0]),
}


@pytest.mark.parametrize("code", sorted(SINGLE))
def test_each_condition_alone_turns_the_forecast_into_an_abstention_with_its_reason(good, code):
    w = copy.deepcopy(good)
    SINGLE[code](w)
    doc, rec = run(w)
    codes = [c["code"] for c in rec["conditions"]]
    assert doc["prediction_status"] == "ABSTAIN" and code in codes, codes
    assert AB.CONDITIONS[code][0] in doc["abstain_reasons"]
    assert doc["probability"] is None and doc["uncertainty_interval"] is None
    assert C.validate(doc, backtest=BT) == []
    assert AB.validate_publication(doc, model_card=w["card"], calibration_card=w["cal"], record=rec, backtest=BT) == []
    assert schema_errors({"document": doc, "record": rec}) == []
    assert rec["target"] == w["req"]["target"] and rec["horizon_seconds"] == C.TARGETS[w["req"]["target"]]["horizon_s"]


@pytest.mark.parametrize("code, patch", [("POINT_OUTSIDE_DISPLAY_RANGE", ("DISPLAY_RANGE", (0.995, 1.0))),
                                         ("LOW_SUPPORT", ("SUPPORT_MIN", 10_000))])
def test_display_range_and_support_conditions(good, monkeypatch, code, patch):
    monkeypatch.setattr(CAL, patch[0], patch[1])
    doc, rec = run(copy.deepcopy(good))
    assert doc["prediction_status"] == "ABSTAIN" and code in [c["code"] for c in rec["conditions"]]
    assert "every condition" not in AB.describe(doc, rec)


def test_every_condition_is_evaluated_none_hides_another(good):
    w = copy.deepcopy(good)
    for code in ("FLAG_OFF", "SIZE_REQUESTED", "DRIFT", "MODEL_NOT_PROMOTED", "SOURCE_GAP", "FEATURE_OUT_OF_RANGE"):
        SINGLE[code](w)
    doc, rec = run(w)
    codes = {c["code"] for c in rec["conditions"]}
    assert {"FLAG_OFF", "SIZE_REQUESTED", "DRIFT", "MODEL_NOT_PROMOTED", "SOURCE_GAP", "FEATURE_OUT_OF_RANGE"} <= codes
    assert set(doc["abstain_reasons"]) == {c["reason"] for c in rec["conditions"]}
    assert doc["abstain_reasons"] == [r for r in C.ABSTAIN_REASONS if r in doc["abstain_reasons"]]


def test_today_every_target_abstains_with_the_preregistered_reasons():
    """Rule 15: flag OFF, level ABSTAIN, a calibration set of 24 rows (T1's size), prospective evidence not matured."""
    w = world(fit_n=24, level="ABSTAIN", evidence="NOT_YET_MATURED")
    w["req"]["flag_on"] = False
    w["raw"] = float(np.median([r["score"] for r in w["rows"]]))
    doc, rec = run(w)
    assert doc["prediction_status"] == "ABSTAIN"
    assert set(doc["abstain_reasons"]) == {"FLAG_OFF", "MODEL_NOT_SELECTED", "UNCALIBRATED", "INSUFFICIENT_HISTORY", "NOT_YET_MATURED"}
    text = AB.describe(doc, rec)
    assert "%" not in text and text.startswith("No probability")


# ---------------------------------------------------------------- P38: invalid numbers and inputs
@pytest.mark.parametrize("raw", [float("nan"), float("inf"), -float("inf"), -0.1, 1.1])
def test_p38_an_invalid_raw_number_never_publishes(good, raw):
    w = copy.deepcopy(good)
    w["raw"] = raw
    doc, rec = run(w)
    assert doc["prediction_status"] == "ABSTAIN" and "INVALID_PROBABILITY" in [c["code"] for c in rec["conditions"]]
    assert "MODEL_NOT_SELECTED" in doc["abstain_reasons"]


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), 1.5, -0.2, "0.4", None])
def test_p38_the_validator_refuses_an_injected_invalid_probability(good, bad):
    doc, rec = run(good)
    d = dict(doc, probability=bad)
    assert AB.validate_publication(d, model_card=good["card"], calibration_card=good["cal"], record=rec, backtest=BT)


def test_p38_nan_features_are_missing_inputs_not_zeros(good):
    w = copy.deepcopy(good)
    for c in B.B2_REQUIRED:
        w["req"]["x"][c] = float("nan")
    ex = B.Example(decision_key="q", chain="solana", mint=w["req"]["mint"], decision_time=w["req"]["decision_time"], label_matures_at=0,
                   y=-1, x=w["req"]["x"], avail=w["req"]["avail"])
    p, why = B.predict(w["card"], [ex])
    w["raw"], w["raw_why"] = float(p[0]), why[0]
    doc, rec = run(w)
    assert why[0] == "OOD" and doc["prediction_status"] == "ABSTAIN"
    assert "MISSING_REQUIRED_INPUT" in [c["code"] for c in rec["conditions"]]


# ---------------------------------------------------------------- the validator's Phase 13 checks
def _tamper(doc, **kw):
    d = copy.deepcopy(doc)
    for k, v in kw.items():
        d[k] = v
    return d


def test_the_validator_refuses_each_unsupported_forecast(good):
    doc, rec = run(good)
    card, cal = good["card"], good["cal"]

    def bad(d, c=cal, mc=card):
        return AB.validate_publication(d, model_card=mc, calibration_card=c, backtest=BT)

    ref = dict(doc["calibration_reference"])
    assert bad(_tamper(doc, calibration_reference={**ref, "holdout_n": ref["holdout_n"] + 1}))
    assert bad(_tamper(doc, calibration_reference={**ref, "agent_share": 0.9}))
    assert bad(_tamper(doc, calibration_reference={k: v for k, v in ref.items() if k != "support_n"}))
    assert bad(_tamper(doc, caveats=[c for c in doc["caveats"] if c != AB.SHADOW_CAVEAT]))
    assert bad(_tamper(doc, caveats=[c for c in doc["caveats"] if c != AB.INTERVAL_CAVEAT]))
    p = doc["probability"]
    assert bad(_tamper(doc, uncertainty_interval=[max(0.0, p - 1e-3), min(1.0, p + 1e-3)]))
    assert bad(_tamper(doc, calibration_reference={**ref, "support_n": 10, "support_k": 3}))
    assert bad(_tamper(doc, cohort={"new_mint": True, "route": "CAPTURE"}))
    assert bad(doc, c=None)
    abst = CAL.build_card(T1, card, good["rows"], H, level="ABSTAIN", evidence=None)
    assert bad(_tamper(doc, calibration_reference=CAL.reference(abst, support_n=ref["support_n"], support_k=ref["support_k"])), c=abst)
    t = copy.deepcopy(cal)
    t["evidence"]["n"] += 1
    assert any("refused" in e for e in bad(doc, c=t))


def test_p27_an_agent_agreement_never_becomes_a_probability(good):
    doc, rec = run(good)
    card, cal = good["card"], good["cal"]
    scen = _tamper(doc, behavioral_scenarios=[{"name": "fast follow-through", "agent_agreement": 0.9}])
    assert C.validate(scen, model_card=card, backtest=BT) == []          # the frozen contract alone lets this key through
    assert AB.validate_publication(scen, model_card=card, calibration_card=cal, backtest=BT)
    assert AB.validate_publication(_tamper(doc, behavioral_scenarios=[{"name": "x", "agents": "90"}, {"name": "y", "n": 9}]),
                                   model_card=card, calibration_card=cal, backtest=BT)
    assert AB.validate_publication(_tamper(doc, cohort={"vote_share": 0.9}), model_card=card, calibration_card=cal, backtest=BT)
    assert AB.validate_publication(_tamper(doc, cohort={"route": "CAPTURE", "rate": 0.9}), model_card=card, calibration_card=cal, backtest=BT)
    sim = dict(card, kind="MIROFISH_SIMULATION")
    assert any("simulation" in e for e in AB.validate_publication(doc, model_card=sim, calibration_card=cal, backtest=BT))
    ok = _tamper(doc, behavioral_scenarios=[{"name": "fast follow-through", "assumptions": ["listing confirmed"], "monitor": "volume"}])
    assert AB.validate_publication(ok, model_card=card, calibration_card=cal, backtest=BT) == []
    w = copy.deepcopy(good)
    w["req"]["behavioral_inputs"] = [{"agent_agreement": 0.9}]
    d2, r2 = run(w)
    assert d2["prediction_status"] == "ABSTAIN" and "RESTRICTED_SOURCE" in d2["abstain_reasons"]


def test_p12_a_new_mint_abstains_with_a_history_card_and_is_labelled_with_a_cross_sectional_one(good):
    w = copy.deepcopy(good)
    _card_flag(w)
    w["req"]["new_mint"] = True
    d, r = run(w)
    assert d["prediction_status"] == "ABSTAIN" and "INSUFFICIENT_HISTORY" in d["abstain_reasons"]
    w2 = copy.deepcopy(good)
    w2["req"]["new_mint"] = True
    d2, r2 = run(w2)
    assert d2["prediction_status"] == "FORECAST" and AB.NEW_MINT_CAVEAT in d2["caveats"] and d2["cohort"]["new_mint"] is True
    assert AB.validate_publication(d2, model_card=w2["card"], calibration_card=w2["cal"], record=r2, backtest=BT) == []
    stripped = _tamper(d2, caveats=[c for c in d2["caveats"] if c != AB.NEW_MINT_CAVEAT])
    assert any("P12" in e for e in AB.validate_publication(stripped, model_card=w2["card"], calibration_card=w2["cal"], backtest=BT))


def test_an_abstention_record_must_match_its_document(good):
    w = copy.deepcopy(good)
    w["level"] = "ABSTAIN"
    doc, rec = run(w)
    v = lambda d, r: AB.validate_publication(d, model_card=w["card"], calibration_card=w["cal"], record=r, backtest=BT)
    assert v(doc, rec) == []
    assert v(_tamper(doc, abstain_reasons=["MODEL_NOT_SELECTED", "OOD"]), rec)          # an invented reason
    hidden = copy.deepcopy(rec)
    hidden["conditions"].append(AB._cond("DRIFT"))
    hidden["record_id"] = AB.sha({k: x for k, x in hidden.items() if k != "record_id"})
    assert v(doc, hidden)                                                                # a hidden reason
    assert v(doc, dict(rec, record_id="0" * 64))
    assert v(doc, dict(rec, forecast_id="fc_" + "0" * 32))
    assert v(_tamper(doc, evidence_refs=[]), rec)


# ---------------------------------------------------------------- P39: drift and the append-only record file
def test_p39_drift_degrades_later_forecasts_and_never_rewrites_earlier_records(good, tmp_path):
    path = tmp_path / "records.jsonl"
    earlier = []
    for i in range(3):
        w = copy.deepcopy(good)
        w["req"]["snapshot_hash"] = f"{i:064x}"
        w["req"]["decision_time"] -= (3 - i) * 3600.0
        earlier.append(run(w)[1])
    s1 = AB.append(path, earlier, expect_sha=None)
    before = path.read_text()
    alarm = good["req"]["decision_time"] - 1800.0
    w = copy.deepcopy(good)
    w["drift"] = [alarm]
    doc, rec = run(w)
    assert doc["prediction_status"] == "ABSTAIN" and "DRIFT_ALERT" in doc["abstain_reasons"]
    old = copy.deepcopy(good)
    old["drift"] = [alarm]
    old["req"]["decision_time"] = alarm - 60.0
    old["req"]["avail"] = {c: alarm - 600.0 for c in old["req"]["avail"]}
    assert run(old)[0]["prediction_status"] == "FORECAST"                 # an earlier decision is not touched by a later alarm
    s2 = AB.append(path, [rec], expect_sha=s1)
    assert AB.is_append_only(before, path.read_text()) and path.read_text().startswith(before)
    lines = path.read_text().splitlines()
    path.write_text("\n".join([lines[1], lines[0]] + lines[2:]) + "\n")    # someone rewrites the trail
    with pytest.raises(AB.PublicationError, match="changed"):
        AB.append(path, [rec], expect_sha=s2)
    with pytest.raises(AB.PublicationError, match="record_id"):
        AB.append(tmp_path / "new.jsonl", [dict(rec, level="NO_GO")], expect_sha=None)
    assert not AB.is_append_only("a\nb\n", "a\nc\n")


# ---------------------------------------------------------------- disallowed inputs and card time
def test_disallowed_inputs_are_named(good):
    req = copy.deepcopy(good["req"])
    assert AB.disallowed_inputs(req, B.ALLOWED_COLUMNS) == []
    req["input_paths"] = [str(ROOT / "audits/predictive-intelligence/phase_04/adoption/data/x.csv")]
    req["input_rows"] = [{"use": "BAKEOFF_ONLY"}]
    req["x"] = dict(req["x"], future_price=1.0)
    req["avail"] = dict(req["avail"], **{B.LIQ: req["decision_time"] + 1})
    req["decision_time_basis"] = "THESES_CREATED_AT"
    out = AB.disallowed_inputs(req, B.ALLOWED_COLUMNS)
    assert len(out) == 5 and any("allowlist" in o for o in out) and any("availability" in o for o in out)


def test_card_time_conditions_agree_with_the_phase_12_replay_guard(good):
    card = good["card"]
    cut = float(card["training_cutoff"])
    for dt in (-DAY, -1.0, 0.0, 1.0, 13 * DAY, 14 * DAY, 14 * DAY + 1, 30 * DAY):
        w = copy.deepcopy(good)
        w["req"]["decision_time"] = cut + dt
        codes = {c["code"] for c in AB.evaluate(w["req"], card=card, level="SHADOW", cal_card=w["cal"], raw=w["raw"],
                                                backtest_status=BT)["conditions"]}
        try:
            stale = E.check_card_time(card, [cut + dt])[0]
            assert ("MODEL_TOO_OLD" in codes) == (stale == E.STALE) and "MODEL_TRAINED_AFTER_DECISION" not in codes
        except E.RetrospectiveModelNotAvailable:
            assert "MODEL_TRAINED_AFTER_DECISION" in codes


def test_plain_language_has_no_trading_words_and_no_number_when_abstaining(good):
    w = copy.deepcopy(good)
    w["level"] = "ABSTAIN"
    doc, rec = run(w)
    text = AB.describe(doc, rec)
    assert "%" not in text and not any(re.search(r"\b" + t + r"\b", text.lower()) for t in AB.TRADING_WORDS)
    for code in AB.CONDITIONS:
        assert not any(re.search(r"\b" + re.escape(t) + r"\b", AB.CONDITIONS[code][1].lower()) for t in AB.TRADING_WORDS), code


# ---------------------------------------------------------------- the ForecastResult schema (in-house checker; jsonschema oracle)
def _resolve(ref: str) -> dict:
    node = SCHEMA
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _is(v, t):
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
    return isinstance(v, _TYPES[t])


def schema_errors(inst, sch=None, path="$") -> list[str]:
    """A small checker for the keywords the schema uses: $ref, type, const, enum, required, properties, additionalProperties,
    items, minItems, maxItems, contains, minimum, maximum, pattern, minLength, allOf, if/then."""
    sch = SCHEMA if sch is None else sch
    if "$ref" in sch:
        return schema_errors(inst, _resolve(sch["$ref"]), path)
    errs = []
    if "type" in sch:
        ts = sch["type"] if isinstance(sch["type"], list) else [sch["type"]]
        if not any(_is(inst, t) for t in ts):
            return [f"{path}: type {type(inst).__name__} not in {ts}"]
    if "const" in sch and inst != sch["const"]:
        errs.append(f"{path}: not {sch['const']!r}")
    if "enum" in sch and inst not in sch["enum"]:
        errs.append(f"{path}: {inst!r} not in enum")
    if isinstance(inst, (int, float)) and not isinstance(inst, bool):
        if "minimum" in sch and not inst >= sch["minimum"]:
            errs.append(f"{path}: below minimum")
        if "maximum" in sch and not inst <= sch["maximum"]:
            errs.append(f"{path}: above maximum")
    if isinstance(inst, str):
        if "pattern" in sch and not re.search(sch["pattern"], inst):
            errs.append(f"{path}: pattern")
        if "minLength" in sch and len(inst) < sch["minLength"]:
            errs.append(f"{path}: too short")
    if isinstance(inst, dict):
        for k in sch.get("required", []):
            if k not in inst:
                errs.append(f"{path}: missing {k}")
        props = sch.get("properties", {})
        for k, v in inst.items():
            if k in props:
                errs += schema_errors(v, props[k], f"{path}.{k}")
            elif sch.get("additionalProperties") is False:
                errs.append(f"{path}: extra {k}")
            elif isinstance(sch.get("additionalProperties"), dict):
                errs += schema_errors(v, sch["additionalProperties"], f"{path}.{k}")
    if isinstance(inst, list):
        if "items" in sch:
            for i, v in enumerate(inst):
                errs += schema_errors(v, sch["items"], f"{path}[{i}]")
        if "minItems" in sch and len(inst) < sch["minItems"]:
            errs.append(f"{path}: too few items")
        if "maxItems" in sch and len(inst) > sch["maxItems"]:
            errs.append(f"{path}: too many items")
        if "contains" in sch and not any(not schema_errors(v, sch["contains"]) for v in inst):
            errs.append(f"{path}: contains")
    for sub in sch.get("allOf", []):
        if "if" in sub:
            if not schema_errors(inst, sub["if"], path):
                errs += schema_errors(inst, sub.get("then", {}), path)
        else:
            errs += schema_errors(inst, sub, path)
    return errs


def test_the_schema_accepts_both_kinds_of_result_and_refuses_mutations(good):
    fdoc, frec = run(good)
    w = copy.deepcopy(good)
    w["level"] = "ABSTAIN"
    adoc, arec = run(w)
    assert schema_errors({"document": fdoc, "record": frec}) == [] and schema_errors({"document": adoc, "record": arec}) == []
    muts = [
        ({"document": dict(adoc, probability=0.3), "record": arec}, "probability on ABSTAIN"),
        ({"document": dict(adoc, confidence=0.9), "record": arec}, "extra field"),
        ({"document": dict(adoc, abstain_reasons=["NOT_A_REASON"]), "record": arec}, "unknown reason"),
        ({"document": dict(adoc, abstain_reasons=[]), "record": arec}, "abstain without reason"),
        ({"document": dict(fdoc, caveats=["PRICE_PATH_NOT_PROCEEDS"]), "record": frec}, "forecast without interval caveat"),
        ({"document": dict(fdoc, probability=0.999), "record": frec}, "outside display"),
        ({"document": dict(fdoc, calibration_reference=dict(fdoc["calibration_reference"], level="ABSTAIN")), "record": frec}, "level"),
        ({"document": fdoc, "record": dict(frec, conditions=[AB._cond("DRIFT")])}, "forecast with a condition"),
        ({"document": adoc, "record": dict(arec, conditions=[dict(AB._cond("DRIFT"), code="SOMETHING")])}, "unknown code"),
        ({"document": adoc, "record": dict(arec, raw_number=0.3)}, "record carries a number"),
        ({"document": dict(fdoc, behavioral_scenarios=[{"name": "x", "agreement": 0.9}]), "record": frec}, "scenario number"),
        ({"document": adoc}, "record missing"),
    ]
    for inst, why in muts:
        assert schema_errors(inst), why
    try:
        import jsonschema  # noqa: F401  (research venv oracle only; skipped in the lab runtime)
    except ImportError:
        return
    jsonschema.Draft202012Validator(SCHEMA).validate({"document": fdoc, "record": frec})
    for inst, why in muts:
        assert list(jsonschema.Draft202012Validator(SCHEMA).iter_errors(inst)), why


# ---------------------------------------------------------------- added after the first mutation probe (8 survivors)
def test_a_calibration_card_of_another_model_or_target_is_no_calibrator(good):
    w = copy.deepcopy(good)
    other = dict(w["card"], model_sha="c" * 64)
    w["cal"] = CAL.build_card(T1, other, w["rows"], H, level="SHADOW",
                              evidence={**world()["cal"]["evidence"], "status": "NOT_YET_MATURED"})
    doc, rec = run(w)
    no = [c for c in rec["conditions"] if c["code"] == "NO_CALIBRATOR"]
    assert doc["prediction_status"] == "ABSTAIN" and no and "another model" in no[0]["detail"]
    w2 = copy.deepcopy(good)
    w2["cal"] = dict(w2["cal"], target=L.T1B)
    d2, r2 = run(w2)
    assert d2["prediction_status"] == "ABSTAIN" and any(c["code"] == "NO_CALIBRATOR" for c in r2["conditions"])


def test_an_abstention_document_cannot_carry_a_reference_outside_the_allowlist(good):
    w = copy.deepcopy(good)
    w["level"] = "ABSTAIN"
    doc, rec = run(w)
    bad = _tamper(doc, calibration_reference={"agent_share": 0.9})
    errs = AB.validate_publication(bad, model_card=w["card"], calibration_card=w["cal"], record=rec, backtest=BT)
    assert any("allowlist" in e for e in errs)


def test_a_calibrated_card_kept_at_level_abstain_never_publishes(good):
    doc, rec = run(good)
    ev = good["cal"]["evidence"]
    assert good["cal"]["status"] == CAL.CALIBRATED
    w = world(level="ABSTAIN")
    assert w["cal"]["status"] == CAL.CALIBRATED and w["cal"]["publishable"] is False and ev["passed"]
    ref = CAL.reference(w["cal"], support_n=doc["calibration_reference"]["support_n"], support_k=doc["calibration_reference"]["support_k"])
    d = _tamper(doc, calibration_reference=ref, caveats=[c for c in doc["caveats"] if c != AB.SHADOW_CAVEAT])
    errs = AB.validate_publication(d, model_card=good["card"], calibration_card=w["cal"], backtest=BT)
    assert any("SHADOW or VALIDATED_EXPERIMENTAL" in e for e in errs)


def test_an_edited_record_that_keeps_its_id_is_refused(good):
    w = copy.deepcopy(good)
    w["level"] = "ABSTAIN"
    doc, rec = run(w)
    edited = dict(rec, model_id="B9:edited")
    errs = AB.validate_publication(doc, model_card=w["card"], calibration_card=w["cal"], record=edited, backtest=BT)
    assert errs == ["abstention record content does not match its record_id"]


def test_plain_language_refuses_a_trading_word_even_from_an_explanation(good, monkeypatch):
    w = copy.deepcopy(good)
    w["level"] = "ABSTAIN"
    doc, rec = run(w)
    rec2 = copy.deepcopy(rec)
    rec2["conditions"][0]["explanation"] = "buy before the move"
    with pytest.raises(AB.PublicationError, match="trading word"):
        AB.describe(doc, rec2)
