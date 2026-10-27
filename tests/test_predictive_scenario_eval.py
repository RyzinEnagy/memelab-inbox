"""Phase 15 scenario-eval-1: blind coding, warning metrics, A_WARN, the frozen decision rule and isolation. No network, no
label store, fixed times, nothing written into tracked paths."""
from __future__ import annotations

import ast
import copy
import hashlib
import math
import sys
from pathlib import Path

import numpy as np
import pytest

from memelab.predictive import behavioral as BH
from memelab.predictive import contract as C
from memelab.predictive import evaluation as E
from memelab.predictive import scenario_eval as S

ROOT = Path(__file__).resolve().parents[1]
MINT = "So11111111111111111111111111111111111111112"
T = "2026-10-12T05:00:00Z"
TT = C.parse_utc(T)
CREATED = "2026-10-27T00:00:00Z"
T1, T1B, T2 = S.PRIMARY
STDLIB = set(sys.stdlib_module_names)


def obs_att(name, value, at="2026-10-12T04:00:00Z"):
    return BH.observation(BH.LAB_ATTENTION_PROXY, name, value, at, f"lab-proxy:{'ab' * 32}:{name}")


def seed_of(*obs, t=T):
    return BH.build_seed("solana", MINT, "a" * 64, t, list(obs))


def doc_of(seed):
    d = BH.rule_scenarios(seed, created_at_utc=CREATED)
    return d, BH.validate_scenario(d)


def cat(state):
    return BH.observation(BH.CATALYST_EVENT, "bogus_control_catalyst", "BOGUS_CONTROL_NOT_A_REAL_EVENT", T,
                          "fictional-bogus-control:0123456789abcdef", state=state)


def resign(d):
    body = {k: v for k, v in d.items() if k != "doc_sha256"}
    d["doc_sha256"] = BH.sha(body)
    return d


# ---------------------------------------------------------------- isolation
def _imports(p):
    out = set()
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n, ast.ImportFrom):
            out.add(("." * n.level) + (n.module or ""))
            out.update(("." * n.level) + a.name for a in n.names if n.level and not n.module)
        elif isinstance(n, ast.Import):
            out.update(a.name for a in n.names)
    return out


def test_scenario_eval_imports_numpy_stdlib_and_lab_predictive_modules_only():
    got = _imports(ROOT / "memelab/predictive/scenario_eval.py")
    allowed = {"numpy", ".", "__future__"}
    for i in got:
        assert i in allowed or i.split(".")[0] in STDLIB or (i.startswith(".") and i != ".behavioral"), i
    txt = (ROOT / "memelab/predictive/scenario_eval.py").read_text()
    assert "import behavioral" not in txt and "from .behavioral" not in txt and "socialcat" not in txt
    for banned in ("socket", "urllib", "requests", "subprocess", "http.client"):
        assert f"import {banned}" not in txt


def test_no_other_memelab_module_imports_scenario_eval():
    for p in (ROOT / "memelab").rglob("*.py"):
        if p.name == "scenario_eval.py":
            continue
        assert not any(i.endswith("scenario_eval") for i in _imports(p)), p


# ---------------------------------------------------------------- blindness
def test_coder_refuses_outcome_like_keys_at_any_depth_and_allows_hypothesis_labels():
    d, errs = doc_of(seed_of(obs_att("sc_organic_acceleration", 1.0)))
    assert errs == []
    S.code_document(d, errs)                      # the hypothesis key "label" is not an outcome
    for key in ("y", "outcome", "label_class", "first_touch_start", "label_matures_at", "realized_return", "hit", "event_observed"):
        bad = copy.deepcopy(d)
        bad["hypotheses"][0]["monitor"][key] = 1
        with pytest.raises(S.BlindingError):
            S.code_document(bad, [])
    with pytest.raises(S.BlindingError):
        S.code_document([{"x": {"outcome_24h": 0}}], [])


def test_verify_file_refuses_a_file_that_is_not_the_committed_one(tmp_path):
    p = tmp_path / "c.csv"
    p.write_bytes(b"a,b\n1,2\n")
    good = hashlib.sha256(b"a,b\n1,2\n").hexdigest()
    assert S.verify_file(p, good) == b"a,b\n1,2\n"
    p.write_bytes(b"a,b\n1,3\n")
    with pytest.raises(S.BlindingError):
        S.verify_file(p, good)


# ---------------------------------------------------------------- coding rules (protocol 4)
def test_rule_documents_code_into_statements_on_the_primary_targets():
    d, errs = doc_of(seed_of(obs_att("sc_organic_acceleration", 1.0), obs_att("sc_attention_suspect", 1.0)))
    c = S.code_document(d, errs)
    assert c["status"] == S.CODED and c["unscorable"] == [] and c["refused"] == []
    assert {(s["target"], s["expect"], s["label"]) for s in c["statements"]} == {
        (T1B, "EVENT", "ORGANIC_ATTENTION_CONTINUATION"), (T2, "EVENT", "MANUFACTURED_ATTENTION_DUMP")}
    assert S.warnings_of(c) == {T1: S.WARN_NONE, T1B: S.WARN_EVENT, T2: S.WARN_EVENT}
    assert S.labels_by_target(c)[T2] == ["MANUFACTURED_ATTENTION_DUMP"]


def test_no_grounded_scenario_is_no_statement():
    d, errs = doc_of(seed_of(obs_att("sc_organic_acceleration", 0.0)))
    c = S.code_document(d, errs)
    assert c["status"] == S.CODED and c["statements"] == [] and c["no_statement"] == 1
    assert set(S.warnings_of(c).values()) == {S.WARN_NONE}


def test_catalyst_monitors_without_an_outcome_source_are_unscorable_and_verified_bogus_gives_a_t1_statement():
    d, errs = doc_of(seed_of(obs_att("sc_organic_acceleration", 0.0), cat("UNVERIFIED_EVENT")))
    c = S.code_document(d, errs)
    assert errs == [] and c["statements"] == []
    assert [u["reason"] for u in c["unscorable"]] == [S.UNSCORABLE] and c["unscorable"][0]["label"] == "RUMOR_FADE"
    d2, e2 = doc_of(seed_of(obs_att("sc_organic_acceleration", 0.0), cat("VERIFIED")))
    c2 = S.code_document(d2, e2)
    assert [(s["target"], s["label"]) for s in c2["statements"]] == [(T1, "CATALYST_FOLLOW_THROUGH")]


def test_a_window_that_is_not_decision_to_horizon_is_refused():
    d, errs = doc_of(seed_of(obs_att("sc_organic_acceleration", 1.0)))
    for field, val in (("window_start_utc", "2026-10-12T05:00:01Z"), ("window_end_utc", "2026-10-13T05:00:00Z"),
                       ("window_end_utc", "not a time")):
        bad = copy.deepcopy(d)
        bad["hypotheses"][0]["monitor"][field] = val
        c = S.code_document(bad, [])
        assert c["statements"] == [] and [r["reason"] for r in c["refused"]] == [S.REFUSED_WINDOW]
        assert S.warnings_of(c)[T1B] == S.WARN_NONE


def test_an_expectation_outside_the_vocabulary_is_refused():
    d, _ = doc_of(seed_of(obs_att("sc_organic_acceleration", 1.0)))
    d["hypotheses"][0]["monitor"]["expect"] = "PUMP"
    c = S.code_document(d, [])
    assert [r["reason"] for r in c["refused"]] == [S.REFUSED_EXPECTATION] and c["statements"] == []


@pytest.mark.parametrize("mutate,reason", [
    (lambda d: "free text from the engine", "NOT_A_DOCUMENT"),
    (lambda d: {**d, "kind": "FORECAST"}, "NOT_A_BEHAVIORAL_DOCUMENT"),
    (lambda d: {**d, "status": "SIMULATION_NOT_AVAILABLE"}, "STATUS_SIMULATION_NOT_AVAILABLE"),
    (lambda d: {**d, "status": "SIMULATION_RAN", "hypotheses": []}, "FREE_TEXT_OR_NO_HYPOTHESIS"),
    (lambda d: {**d, "subject": {}}, "NO_DECISION_TIME"),
])
def test_documents_that_cannot_be_coded_are_not_codable(mutate, reason):
    d, _ = doc_of(seed_of(obs_att("sc_organic_acceleration", 1.0)))
    c = S.code_document(mutate(d), [])
    assert c["status"] == S.NOT_CODABLE and c["reason"] == reason and c["statements"] == []
    assert set(S.warnings_of(c).values()) == {S.WARN_NOT_CODABLE}


def test_validation_errors_make_a_document_not_codable():
    d, _ = doc_of(seed_of(obs_att("sc_organic_acceleration", 1.0)))
    c = S.code_document(d, ["SOME_ERROR"])
    assert c["status"] == S.NOT_CODABLE and c["reason"] == "DOCUMENT_INVALID"


def test_conflict_and_no_event_warnings():
    d, _ = doc_of(seed_of(obs_att("sc_organic_acceleration", 1.0)))
    h = copy.deepcopy(d["hypotheses"][0])
    h["monitor"]["expect"] = "NO_EVENT"
    h["hypothesis_id"] = "h-other"
    both = {**d, "hypotheses": d["hypotheses"] + [h]}
    assert S.warnings_of(S.code_document(both, []))[T1B] == S.WARN_CONFLICT
    only_no = {**d, "hypotheses": [h]}
    assert S.warnings_of(S.code_document(only_no, []))[T1B] == S.WARN_NO_EVENT


def test_the_mirofish_probe_outputs_of_phase_14_are_not_codable():
    import json
    probe = json.loads((ROOT / "audits/predictive-intelligence/phase_14/behavioral/MIROFISH_PROBE.json").read_text())
    for name, run in probe["runs"].items():
        c = S.code_document(run, BH.validate_scenario(run))
        assert c["status"] == S.NOT_CODABLE and c["statements"] == [], name


# ---------------------------------------------------------------- warning metrics (E2, E3)
def rows_of(w, y, days, leads=None):
    return [{"warning": a, "y": b, "day": c, "lead_s": (leads[i] if leads else None)} for i, (a, b, c) in enumerate(zip(w, y, days))]


def test_warning_metrics_by_hand():
    w = ["EVENT", "EVENT", "NONE", "NONE", "CONFLICT", "NOT_CODABLE", "EVENT"]
    y = [1, 0, 1, 0, 1, 1, 1]
    r = S.warning_metrics(rows_of(w, y, ["d1"] * 7, [3600.0, None, None, None, None, None, 7200.0]), reps=50, seed=1)
    assert r["excluded"] == {"CONFLICT": 1, "NOT_CODABLE": 1} and r["n_scored"] == 5 and r["positives"] == 3
    assert r["warned"] == 3 and r["hits"] == 2 and r["precision"] == pytest.approx(2 / 3)
    assert r["prevalence"] == pytest.approx(3 / 5) and r["lift"] == pytest.approx(2 / 3 - 3 / 5)
    assert r["recall"] == pytest.approx(2 / 3) and r["coverage"] == pytest.approx(3 / 5)
    assert r["lead_time_h"] == {"n": 2, "median": 1.5, "min": 1.0, "max": 2.0}
    assert r["gate"] == S.INSUFFICIENT_DAYS


def test_gate_order():
    assert S.gate(0, 0, 0, 0) == S.INSUFFICIENT_HISTORY
    assert S.gate(100, 30, 4, 50) == S.INSUFFICIENT_DAYS
    assert S.gate(49, 20, 5, 30) == S.INSUFFICIENT_EVENTS
    assert S.gate(100, 9, 5, 30) == S.INSUFFICIENT_EVENTS
    assert S.gate(100, 91, 5, 30) == S.INSUFFICIENT_EVENTS
    assert S.gate(100, 30, 5, 0) == S.NO_WARNINGS
    assert S.gate(100, 30, 5, 19) == S.INSUFFICIENT_WARNINGS
    assert S.gate(50, 10, 5, 20) is None


def _bigset(aligned: bool, n=400, days=8):
    rng = np.random.default_rng(7)
    y = (rng.random(n) < 0.25).astype(int)
    if aligned:
        w = [("EVENT" if (yy == 1 or i % 7 == 0) else "NONE") for i, yy in enumerate(y)]
    else:
        w = [("EVENT" if int(hashlib.sha256(f"k{i}:bogus-control".encode()).hexdigest()[0], 16) % 2 == 0 else "NONE") for i in range(n)]
    d = [f"2026-10-{6 + i % days:02d}" for i in range(n)]
    return rows_of(w, list(y), d)


def test_permutation_flags_a_real_signal_and_not_an_outcome_independent_planted_half():
    sig = S.warning_metrics(_bigset(True), reps=400, seed=3)
    hb = S.holm_by_target({T1: sig})
    assert sig["gate"] is None and hb[T1]["verdict"] == S.LIFT_SUGGESTED
    cx = S.warning_metrics(_bigset(False), reps=400, seed=3)
    # CX-15: about half of all positives are "warned", which reads like accuracy, yet the lift is noise
    assert 0.35 < cx["recall"] < 0.65 and abs(cx["lift"]) < 0.08
    assert S.holm_by_target({T1: cx})[T1]["verdict"] == S.NOT_DISTINGUISHABLE


def test_permutation_is_within_day_and_reproducible():
    # every decision of a day carries the same warning: a within-day shuffle cannot move anything
    w = ["EVENT"] * 30 + ["NONE"] * 30
    y = [1] * 25 + [0] * 5 + [1] * 5 + [0] * 25
    d = ["a"] * 30 + ["b"] * 30
    p = S.day_permutation(np.array([x == "EVENT" for x in w]), np.array(y), d, reps=99, seed=5)
    assert p["p_up"] == 1.0 and p["p_down"] == 1.0 and p["null_min"] == p["null_max"] == 25
    a = S.warning_metrics(_bigset(False), reps=100, seed=11)["permutation"]
    b = S.warning_metrics(_bigset(False), reps=100, seed=11)["permutation"]
    assert a == b


def test_worse_than_prevalence_and_holm_counts_missing_targets_as_one():
    rows = _bigset(True)
    flipped = [{**r, "warning": ("NONE" if r["warning"] == "EVENT" else "EVENT")} for r in rows]
    res = S.warning_metrics(flipped, reps=400, seed=3)
    hb = S.holm_by_target({T2: res})
    assert res["lift"] < 0 and hb[T2]["verdict"] == S.WORSE
    assert set(hb) == {T2}


def test_bad_rows_are_refused():
    with pytest.raises(S.ScenarioEvalError):
        S.warning_metrics([{"warning": "MAYBE", "y": 1, "day": "d"}])
    with pytest.raises(S.ScenarioEvalError):
        S.warning_metrics([{"warning": "EVENT", "y": None, "day": "d"}])


# ---------------------------------------------------------------- A_WARN (E1)
def train_rows(n=120, k=30, warned_k=20, warned_n=40, cutoff=TT + 10 * 86400):
    rows = []
    for i in range(n):
        warned = i < warned_n
        yy = 1 if (i < warned_k) or (warned_n <= i < warned_n + (k - warned_k)) else 0
        rows.append({"decision_key": f"k{i:03d}", "decision_time": TT + i * 60, "label_matures_at": TT + i * 60 + 90000,
                     "y": yy, "warning": "EVENT" if warned else "NONE"})
    return rows, cutoff


def test_fit_warn_shrinks_each_stratum_toward_the_training_prevalence():
    rows, cut = train_rows()
    card = S.fit_warn(T2, rows, cut)
    b0 = 30 / 120
    assert card["b0"] == pytest.approx(b0)
    assert card["cells"]["EVENT"]["p"] == pytest.approx((20 + 20 * b0) / (40 + 20))
    assert card["cells"]["NONE"]["p"] == pytest.approx((10 + 20 * b0) / (80 + 20))
    test = [{"decision_key": "t1", "decision_time": cut + 1, "warning": "EVENT"}, {"decision_key": "t2", "decision_time": cut + 2, "warning": "NONE"},
            {"decision_key": "t3", "decision_time": cut + 3, "warning": "CONFLICT"}, {"decision_key": "t4", "decision_time": cut + 4, "warning": "NO_EVENT"}]
    p, why = S.predict_warn(card, test)
    assert p[0] == pytest.approx(card["cells"]["EVENT"]["p"]) and p[1] == pytest.approx(card["cells"]["NONE"]["p"])
    assert math.isnan(p[2]) and why[2] == "AMBIGUOUS_OR_NOT_CODABLE" and p[3] == pytest.approx(b0)


def test_fit_warn_refuses_rows_not_decided_before_and_matured_by_the_cutoff():
    rows, cut = train_rows()
    late = copy.deepcopy(rows)
    late[5]["label_matures_at"] = cut + 1
    with pytest.raises(S.ScenarioEvalError):
        S.fit_warn(T2, late, cut)
    after = copy.deepcopy(rows)
    after[5]["decision_time"] = cut
    with pytest.raises(S.ScenarioEvalError):
        S.fit_warn(T2, after, cut)
    with pytest.raises(S.ScenarioEvalError):
        S.fit_warn("liquidity_degradation_24h", rows, cut)


def test_fit_warn_abstains_below_the_training_gate_and_predict_refuses_earlier_decisions():
    rows, cut = train_rows(n=99, k=30, warned_k=10, warned_n=20)
    card = S.fit_warn(T2, rows, cut)
    assert card["abstain"] == "INSUFFICIENT_HISTORY" and "cells" not in card
    p, why = S.predict_warn(card, [{"decision_key": "x", "decision_time": cut, "warning": "EVENT"}])
    assert math.isnan(p[0]) and why == ["INSUFFICIENT_HISTORY"]
    rows, cut = train_rows()
    card = S.fit_warn(T2, rows, cut)
    with pytest.raises(S.ScenarioEvalError):
        S.predict_warn(card, [{"decision_key": "x", "decision_time": cut - 1, "warning": "EVENT"}])
    bad = copy.deepcopy(card)
    bad["cells"]["EVENT"]["p"] = 0.99
    with pytest.raises(S.ScenarioEvalError):
        S.predict_warn(bad, [{"decision_key": "x", "decision_time": cut, "warning": "EVENT"}])


def test_selection_status_on_development_verdicts():
    assert S.selection_status_dev("INSUFFICIENT_DAYS", 0.01, 0.01, 0.01) == E.NO_UNCORRECTED_SKILL
    assert S.selection_status_dev(S.DEV_SKILL, 0.01, 0.2) == E.FAILS
    assert S.selection_status_dev(S.DEV_SKILL, 0.01, 0.01) == E.NOT_COMPUTED
    assert S.selection_status_dev(S.DEV_SKILL, 0.01, 0.01, 0.01) == E.SURVIVES
    assert S.selection_status_dev(S.DEV_SKILL, 0.05, 0.01, 0.01) == E.FAILS


# ---------------------------------------------------------------- the decision rule (protocol 10)
GOOD_D = {"selection_status": E.SURVIVES, "not_worse_than_all": True, "stability": "STABLE", "cutoff_verified_before_events": True,
          "within_approved_budget": True}
ALL_RAN = {"A": "RAN", "B": "RAN", "C": "RAN", "D": "RAN"}


def test_decision_with_no_events_and_blocked_comparators_is_insufficient_and_no_go():
    d = S.decide(eligible_events=0, comparators={"A": "RAN", "B": "BLOCKED_NO_APPROVED_SPEND", "C": "UNCALIBRATED",
                                                 "D": "BLOCKED_NO_APPROVED_SPEND"},
                 a_warn={T2: {"verdict": "INSUFFICIENT_DAYS", "selection_status": E.NO_UNCORRECTED_SKILL, "brier": 0.2, "brier_b2": 0.21}})
    assert d["validation"] == S.INSUFFICIENT_VALIDATION and d["mirofish"] == S.MIROFISH_NO_GO and d["rules_1"] == S.RULES_NOT_PROMOTED
    assert d["validation_reasons"] == ["ELIGIBLE_EVENTS_BELOW_100", "D_NOT_RUN", "B_NOT_RUN"]
    assert d["probability_created"] is False and d["live_capability_created"] is False


def test_go_candidate_needs_every_condition():
    assert S.decide(eligible_events=100, comparators=ALL_RAN, d_result=GOOD_D)["mirofish"] == S.MIROFISH_GO_CANDIDATE
    assert S.decide(eligible_events=99, comparators=ALL_RAN, d_result=GOOD_D)["mirofish"] == S.MIROFISH_NO_GO
    for key, bad, reason in (("selection_status", E.NOT_COMPUTED, "D_NO_SKILL_SURVIVING_SELECTION_CORRECTION"),
                             ("not_worse_than_all", False, "D_NOT_SHOWN_NOT_WORSE_THAN_EVERY_COMPARATOR"),
                             ("stability", "UNSTABLE", "D_NOT_STABLE"),
                             ("cutoff_verified_before_events", None, "P26_TRAINING_CUTOFF_NOT_VERIFIED"),
                             ("within_approved_budget", False, "NO_APPROVED_BUDGET")):
        r = S.decide(eligible_events=500, comparators=ALL_RAN, d_result={**GOOD_D, key: bad})
        assert r["validation"] == S.EVALUABLE and r["mirofish"] == S.MIROFISH_NO_GO and r["mirofish_reasons"] == [reason]
    r = S.decide(eligible_events=500, comparators={**ALL_RAN, "B": "BLOCKED"}, d_result=GOOD_D)
    assert r["validation"] == S.INSUFFICIENT_VALIDATION and r["mirofish"] == S.MIROFISH_NO_GO
    with pytest.raises(S.ScenarioEvalError):
        S.decide(eligible_events=-1, comparators=ALL_RAN)


def test_rules_candidate_needs_a_surviving_skill_not_worse_than_b2():
    ok = {"verdict": S.DEV_SKILL, "selection_status": E.SURVIVES, "brier": 0.18, "brier_b2": 0.19}
    assert S.decide(eligible_events=0, comparators={}, a_warn={T2: ok})["rules_1"] == S.RULES_CANDIDATE
    for bad in ({**ok, "selection_status": E.NOT_COMPUTED}, {**ok, "verdict": "NOT_DISTINGUISHABLE_FROM_BASE_RATE"},
                {**ok, "brier": 0.2}, {**ok, "brier_b2": None}, {**ok, "brier": float("nan")}):
        assert S.decide(eligible_events=0, comparators={}, a_warn={T2: bad})["rules_1"] == S.RULES_NOT_PROMOTED


def test_summarize_rows_counts_independence_units():
    rows = [{"mint": "a", "decision_time_utc": "2026-10-06T01:00:00Z", "export_commit": "c1"},
            {"mint": "a", "decision_time_utc": "2026-10-06T05:00:00Z", "export_commit": "c1"},
            {"mint": "b", "decision_time_utc": "2026-10-07T01:00:00Z", "export_commit": "c2"}]
    assert S.summarize_rows(rows) == {"rows": 3, "mints": 2, "days": 2, "export_commits": 2}
