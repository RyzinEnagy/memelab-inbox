"""Phase 12: the out-of-sample evaluation discipline (memelab/predictive/evaluation.py). Synthetic fixtures only; no network, no
clock, no store, and never the sealed holdout (the opener is tested on a temporary folder standing in for it). The real run is
audits/predictive-intelligence/phase_12/probes/run_holdout.py."""
from __future__ import annotations

import ast
import csv
import gzip
import json
import math
from pathlib import Path

import numpy as np
import pytest

from memelab.predictive import baselines as B
from memelab.predictive import contract as C
from memelab.predictive import evaluation as E
from memelab.predictive import labels as L
from memelab.predictive import stats as K

ROOT = Path(__file__).resolve().parents[1]
H = L.holdout_start()
DAY = 86400.0
DEC = (ROOT / "docs/predictive-intelligence/DECISIONS.md").read_text()
GOOD_REPORT = {"holdout_labels_sha256": E.SEAL_PINS["holdout_labels_sha256"], "seal_sha256": E.SEAL_PINS["seal_sha256"],
               "seal_json_sha256": E.SEAL_PINS["seal_json_sha256"], "problems": []}
RECORD = {"time_utc": "2026-10-26T17:00:00Z", "head": "abc", "prediction_manifest_sha256": "def", "purpose": "test"}
CONTACTED = C.ACCEPTANCE["holdout_contacted"]["decisions"]


# ---------------------------------------------------------------- the seal check and the opener
def test_the_pins_are_the_values_recorded_outside_the_seal():
    for v in E.SEAL_PINS.values():
        assert v in DEC
    res = (ROOT / "audits/predictive-intelligence/phase_06/PHASE_06_RESULTS.json").read_text()
    assert E.SEAL_PINS["holdout_labels_sha256"] in res


@pytest.mark.parametrize("change", [
    {"problems": ["x: sha256 or size differs from the seal"]},
    {"holdout_labels_sha256": "0" * 64},
    {"seal_sha256": "1" * 64},
    {"seal_json_sha256": "2" * 64},
])
def test_a_seal_report_with_a_problem_or_another_hash_is_refused(change):
    with pytest.raises(E.SealError):
        E.check_seal_report({**GOOD_REPORT, **change}, 0, DEC)


def test_a_failed_seal_check_exit_or_an_unrecorded_pin_is_refused():
    with pytest.raises(E.SealError, match="exited"):
        E.check_seal_report(GOOD_REPORT, 1, DEC)
    with pytest.raises(E.SealError, match="DECISIONS"):
        E.check_seal_report(GOOD_REPORT, 0, DEC.replace(E.SEAL_PINS["seal_json_sha256"], "removed"))
    E.check_seal_report(GOOD_REPORT, 0, DEC)


@pytest.fixture
def fake_seal(tmp_path, monkeypatch):
    """A temporary folder standing in for the sealed one, with its own pins; the real folder is never touched."""
    d = tmp_path / "x" / "fake_sealed_dir"
    d.mkdir(parents=True)
    rows = [{"target": L.T1, "decision_key": "k1", "label": 1}, {"target": L.T1, "decision_key": "k2", "label": 0}]
    raw = gzip.compress("\n".join(json.dumps(r) for r in rows).encode() + b"\n", mtime=0)
    (d / E.LABEL_FILE).write_bytes(raw)
    monkeypatch.setattr(L, "SEALED_DIR", "x/fake_sealed_dir")
    pins = dict(E.SEAL_PINS, holdout_labels_sha256=E.sha256_bytes(raw))
    monkeypatch.setattr(E, "SEAL_PINS", pins)
    report = {**GOOD_REPORT, "holdout_labels_sha256": pins["holdout_labels_sha256"]}
    dec = DEC + "\n" + pins["holdout_labels_sha256"]
    return d, report, dec, rows


def test_the_first_opening_logs_before_it_reads_and_a_second_first_opening_is_refused(fake_seal, tmp_path):
    d, report, dec, rows = fake_seal
    log = tmp_path / "OPENING_LOG.json"
    got, entry = E.open_holdout(d, seal_report=report, seal_exit=0, decisions_text=dec, log_path=log, record=RECORD)
    assert got == rows and entry["mode"] == "FIRST_OPENING" and entry["label_file_sha256_read"] == E.SEAL_PINS["holdout_labels_sha256"]
    assert json.loads(log.read_text())["entries"][0]["head"] == "abc"
    with pytest.raises(E.HoldoutAlreadyOpened):
        E.open_holdout(d, seal_report=report, seal_exit=0, decisions_text=dec, log_path=log, record=RECORD)
    again, e2 = E.open_holdout(d, seal_report=report, seal_exit=0, decisions_text=dec, log_path=log, record=RECORD, mode="REPRODUCTION")
    assert again == rows and e2["mode"] == "REPRODUCTION"
    assert len(json.loads(log.read_text())["entries"]) == 1        # the caller keeps a reproduction's entry elsewhere


def test_the_log_exists_even_when_the_label_bytes_cannot_be_decompressed(fake_seal, tmp_path, monkeypatch):
    d, report, dec, _ = fake_seal
    bad = b"not gzip at all"
    (d / E.LABEL_FILE).write_bytes(bad)
    monkeypatch.setattr(E, "SEAL_PINS", dict(E.SEAL_PINS, holdout_labels_sha256=E.sha256_bytes(bad)))
    rep = {**report, "holdout_labels_sha256": E.sha256_bytes(bad)}
    log = tmp_path / "OPENING_LOG.json"
    with pytest.raises(Exception):
        E.open_holdout(d, seal_report=rep, seal_exit=0, decisions_text=dec + E.sha256_bytes(bad), log_path=log, record=RECORD)
    assert log.exists(), "the opening is logged before the label bytes are decompressed"


def test_bytes_that_are_not_the_sealed_file_are_refused(fake_seal, tmp_path):
    d, report, dec, _ = fake_seal
    (d / E.LABEL_FILE).write_bytes(gzip.compress(b'{"label": 1}\n'))
    log = tmp_path / "OPENING_LOG.json"
    with pytest.raises(E.SealError, match="bytes read"):
        E.open_holdout(d, seal_report=report, seal_exit=0, decisions_text=dec, log_path=log, record=RECORD)
    assert not log.exists()


def test_the_opener_refuses_another_folder_a_missing_record_field_a_reproduction_without_log_and_an_unknown_mode(fake_seal, tmp_path):
    d, report, dec, _ = fake_seal
    other = tmp_path / "elsewhere"
    other.mkdir()
    with pytest.raises(E.SealError, match="not the sealed"):
        E.open_holdout(other, seal_report=report, seal_exit=0, decisions_text=dec, log_path=tmp_path / "l.json", record=RECORD)
    with pytest.raises(E.EvaluationError, match="head"):
        E.open_holdout(d, seal_report=report, seal_exit=0, decisions_text=dec, log_path=tmp_path / "l.json",
                       record={**RECORD, "head": ""})
    with pytest.raises(E.EvaluationError, match="first opening"):
        E.open_holdout(d, seal_report=report, seal_exit=0, decisions_text=dec, log_path=tmp_path / "none.json", record=RECORD,
                       mode="REPRODUCTION")
    with pytest.raises(E.EvaluationError, match="mode"):
        E.open_holdout(d, seal_report=report, seal_exit=0, decisions_text=dec, log_path=tmp_path / "l.json", record=RECORD, mode="LOOK")
    with pytest.raises(E.SealError):
        E.open_holdout(d, seal_report={**report, "problems": ["p"]}, seal_exit=1, decisions_text=dec, log_path=tmp_path / "l.json",
                       record=RECORD)


# ---------------------------------------------------------------- the holdout rows that may be scored
def hrow(key, t, *, target=L.T1, label=1, state="LABELED", censored=0, mint=None, contacted=None, flags=(), **kw):
    m = C.label_matures_at(target, t)
    mint = mint or ("M" + key)
    r = {"target": target, "decision_key": key, "chain": "solana", "mint": mint, "decision_time": t, "split": "HOLDOUT",
         "label_matures_at": m, "target_version": C.TARGETS[target]["version"], "labels_version": L.LABELS_VERSION,
         "registry_sha": C.registry_sha256(), "holdout_contacted": E.contacted(mint, t) if contacted is None else contacted,
         "state": state, "censored": censored, "label": label if state == "LABELED" else None,
         "label_observed_at": m + 60.0 if state == "LABELED" else None, "label_key": "L" + key, "flags_json": json.dumps(list(flags))}
    r.update(kw)
    return r


AS_OF = H + 10 * DAY


def test_only_labelled_uncensored_holdout_rows_are_scored_and_everything_else_is_counted():
    t = H + 3600.0
    rows = [hrow("a", t), hrow("b", t + 1, label=0), hrow("c", t + 2, state="PENDING"), hrow("d", t + 3, state="VENDOR_OR_ROUTE_GAP", censored=1),
            hrow("e", t + 4, state="THINNED"), hrow("z", t, target=L.T2, label=1)]
    got, cnt = E.holdout_rows(rows, L.T1, as_of=AS_OF)
    assert [r["decision_key"] for r in got] == ["a", "b"]
    assert cnt["rows"] == 5 and cnt["censored"] == 1 and cnt["states"] == {"LABELED": 2, "PENDING": 1, "VENDOR_OR_ROUTE_GAP": 1, "THINNED": 1}


def test_the_two_contacted_decisions_are_excluded_and_kept_only_as_a_sensitivity():
    mint, iso = CONTACTED[0]
    t = C.parse_utc(iso)
    rows = [hrow("c1", t, mint=mint), hrow("ok", t + 5)]
    got, cnt = E.holdout_rows(rows, L.T1, as_of=AS_OF)
    assert [r["decision_key"] for r in got] == ["ok"] and cnt["contacted_excluded"] == 1
    got2, cnt2 = E.holdout_rows(rows, L.T1, as_of=AS_OF, exclude_contacted=False)
    assert len(got2) == 2 and cnt2["contacted_excluded"] == 0 and cnt2["contacted_labelled"] == 1


def test_a_contacted_flag_that_disagrees_with_acceptance_stops_the_evaluation():
    mint, iso = CONTACTED[1]
    with pytest.raises(E.EvaluationError, match="contacted"):
        E.holdout_rows([hrow("c", C.parse_utc(iso), mint=mint, contacted=False)], L.T1, as_of=AS_OF)
    with pytest.raises(E.EvaluationError, match="contacted"):
        E.holdout_rows([hrow("c", H + 99.0, contacted=True)], L.T1, as_of=AS_OF)


@pytest.mark.parametrize("change,match", [
    ({"decision_time": H - 3600.0}, "split"),
    ({"split": "DEVELOPMENT"}, "split"),
    ({"decision_time": L.prospective_start() + 60.0}, "split"),
    ({"label_matures_at": 0.0}, "maturity"),
    ({"target_version": "2"}, "version"),
    ({"labels_version": "labels-0"}, "version"),
    ({"registry_sha": "0" * 64}, "registry"),
])
def test_a_row_that_disagrees_with_the_registry_stops_the_evaluation(change, match):
    r = hrow("a", H + 7200.0)
    r.update(change)
    if "decision_time" in change and "label_matures_at" not in change:
        r["label_matures_at"] = C.label_matures_at(L.T1, change["decision_time"])
        r["label_observed_at"] = r["label_matures_at"] + 60
    with pytest.raises(E.EvaluationError, match=match):
        E.holdout_rows([r], L.T1, as_of=AS_OF)


def test_p05_a_labelled_row_read_before_its_maturity_or_not_matured_at_as_of_is_refused():
    r = hrow("a", H + 7200.0)
    r["label_observed_at"] = r["label_matures_at"] - 1.0
    with pytest.raises(E.EvaluationError, match="P05"):
        E.holdout_rows([r], L.T1, as_of=AS_OF)
    with pytest.raises(C.ContractError):
        E.holdout_rows([hrow("b", H + 7200.0)], L.T1, as_of=H + 7200.0)


def test_key_conflict_rows_leave_only_in_that_sensitivity_and_a_duplicate_decision_stops():
    rows = [hrow("a", H + 7200.0, flags=["KEY_CONFLICT"]), hrow("b", H + 7300.0)]
    assert len(E.holdout_rows(rows, L.T1, as_of=AS_OF)[0]) == 2
    got, cnt = E.holdout_rows(rows, L.T1, as_of=AS_OF, include_key_conflict=False)
    assert [r["decision_key"] for r in got] == ["b"] and cnt["key_conflict_excluded"] == 1
    with pytest.raises(E.EvaluationError, match="twice"):
        E.holdout_rows([hrow("a", H + 7200.0), hrow("a", H + 7200.0)], L.T1, as_of=AS_OF)


def test_a_label_joins_a_prediction_of_the_same_decision_only_p01():
    lab = {"decision_key": "k", "chain": "solana", "mint": "MintA", "decision_time": H + 60}
    E.check_identity(lab, dict(lab))
    for k, v in (("mint", "minta"), ("chain", "base"), ("decision_key", "k2"), ("decision_time", H + 61)):
        with pytest.raises(B.IdentityJoinError):
            E.check_identity(lab, {**lab, k: v})


# ---------------------------------------------------------------- model time (P13)
def card(cut=H, **kw):
    c = {"model_id": "B2:x", "training_cutoff": cut, "training_cutoff_utc": "t", "max_train_decision_time": cut - DAY,
         "max_train_label_matures_at": cut - 60.0}
    c.update(kw)
    return c


def ex(t, key="k"):
    return B.Example(decision_key=key, chain="solana", mint="M" + key, decision_time=t, label_matures_at=t + DAY, y=-1)


def const_predict(card_, examples):
    return np.full(len(examples), 0.3), [None] * len(examples)


def test_p13_a_card_trained_after_a_decision_raises_with_the_explicit_status():
    with pytest.raises(E.RetrospectiveModelNotAvailable) as err:
        E.score(card(), [ex(H + 60), ex(H - 1.0, "b")], const_predict)
    assert err.value.status == "RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF"
    p, why = E.score(card(), [ex(H), ex(H + 60, "b")], const_predict)
    assert np.allclose(p, 0.3) and why == [None, None]


def test_a_card_whose_training_rows_break_its_cutoff_is_refused():
    with pytest.raises(E.TrainingAfterCutoff, match="decision"):
        E.check_card_time(card(max_train_decision_time=H), [H + 60])
    with pytest.raises(E.TrainingAfterCutoff, match="maturing"):
        E.check_card_time(card(max_train_label_matures_at=H + 1), [H + 60])


def test_a_decision_past_the_model_age_gets_model_stale_and_no_number():
    age = C.ACCEPTANCE["max_model_age_s"]
    p, why = E.score(card(), [ex(H + age), ex(H + age + 1, "b")], const_predict)
    assert why == [None, "MODEL_STALE"] and math.isfinite(p[0]) and math.isnan(p[1])


def test_score_refuses_a_wrong_row_count_or_a_probability_outside_0_1():
    with pytest.raises(E.EvaluationError):
        E.score(card(), [ex(H + 60)], lambda c, e: (np.array([0.1, 0.2]), [None, None]))
    with pytest.raises(ValueError):
        E.score(card(), [ex(H + 60)], lambda c, e: (np.array([1.2]), [None]))


# ---------------------------------------------------------------- champion from development verdicts only
def dev(target, cid, verdict, *, ref="B2", view="ALL", brier="0.2"):
    return {"target": target, "candidate_id": cid, "verdict": verdict, "reference": ref, "view": view, "brier": brier}


def test_the_champion_is_b2_by_default_and_never_from_a_holdout_number():
    fitted = {"P07_B2": True, "P09_M2_OC_LOGIT_B2": True}
    rows = [dev(L.T1, "P09_M2_OC_LOGIT_B2", "INSUFFICIENT_DAYS"), dev(L.T1, "P09_M2_OC_LOGIT_B2", E.DEV_SKILL, ref="B0"),
            dev(L.T1, "P09_M2_OC_LOGIT_B2", E.DEV_SKILL, view="NEW_MINTS"), dev(L.T1B, "P09_M2_OC_LOGIT_B2", E.DEV_SKILL)]
    c = E.champion(L.T1, rows, fitted)
    assert c["champion"] == "P07_B2" and c["development_skill_vs_b2"] == []


def test_a_candidate_with_development_skill_over_b2_replaces_it_lowest_brier_first_and_only_if_fitted():
    fitted = {"P07_B2": True, "P09_X": True, "P10_Y": True, "P08_Z": False}
    rows = [dev(L.T1, "P09_X", E.DEV_SKILL, brier="0.19"), dev(L.T1, "P10_Y", E.DEV_SKILL, brier="0.17"),
            dev(L.T1, "P08_Z", E.DEV_SKILL, brier="0.01")]
    c = E.champion(L.T1, rows, fitted)
    assert c["champion"] == "P10_Y" and c["development_skill_vs_b2"] == ["P10_Y", "P09_X"]


def test_no_champion_when_b2_abstains():
    assert E.champion(L.T2, [], {"P07_B2": False})["champion"] is None


def test_the_holdout_skill_verdict_carries_the_holdout_name_and_the_gates_are_phase_07s():
    base = {"n_with_number": 60, "positives": 15, "days": 7, "gov_ci": [0.05, 0.3]}
    assert E.holdout_verdict(base, 0.01) == E.HOLDOUT_SKILL
    assert E.holdout_verdict(base, 0.2) == "NOT_DISTINGUISHABLE_FROM_BASE_RATE"
    assert E.holdout_verdict({**base, "positives": 9}, 0.01) == "INSUFFICIENT_EVENTS"
    assert E.holdout_verdict({**base, "n_with_number": 49}, 0.01) == "INSUFFICIENT_EVENTS"
    assert E.holdout_verdict({**base, "days": 4}, 0.01) == "INSUFFICIENT_DAYS"
    assert E.holdout_verdict({**base, "gov_ci": [-0.3, -0.01]}, 0.01) == "WORSE_THAN_BASE_RATE"


# ---------------------------------------------------------------- selection correction (P22) and CX-12
def _fixture(n_days=7, per_day=10, seed=0, prev=0.25):
    rng = np.random.default_rng(seed)
    days = [f"d{d}" for d in range(n_days) for _ in range(per_day)]
    y = (rng.random(len(days)) < prev).astype(float)
    return days, y


def test_cx12_the_best_of_63_no_skill_candidates_looks_good_uncorrected_but_not_after_max_t():
    days, y = _fixture(per_day=9, seed=3)
    ref = np.full(len(y), y.mean())
    rng = np.random.default_rng(11)
    preds = {("T", f"c{j}"): np.clip(y.mean() + rng.normal(0, 0.08, len(y)), 0.01, 0.99) for j in range(63)}
    res = E.max_t({"T": days}, {"T": y}, {"T": ref}, preds, reps=400, seed=5)
    best = max(res, key=lambda k: res[k]["bss"])
    bs = K.group_bootstrap(days, lambda i: K.brier_skill(y[i], preds[best][i], ref[i]), reps=400, seed=5)
    raw_p = (1 + int(np.sum(~(bs["values"] > 0)))) / 401
    assert res[best]["p_max_t"] > 0.05
    assert res[best]["p_max_t"] > raw_p


def test_max_t_keeps_a_strong_candidate_and_is_deterministic():
    days, y = _fixture(seed=1)
    ref = np.full(len(y), y.mean())
    good = np.where(y == 1, 0.8, 0.1)
    noise = np.clip(y.mean() + np.random.default_rng(2).normal(0, 0.1, len(y)), 0.01, 0.99)
    preds = {("T", "good"): good, ("T", "noise"): noise}
    a = E.max_t({"T": days}, {"T": y}, {"T": ref}, preds, reps=300, seed=9)
    b = E.max_t({"T": days}, {"T": y}, {"T": ref}, preds, reps=300, seed=9)
    assert a == b and a[("T", "good")]["p_max_t"] < 0.05 and a[("T", "good")]["bss"] > 0.5


def test_max_t_leaves_rows_without_a_number_out_and_an_all_missing_candidate_undefined():
    days, y = _fixture(seed=4)
    ref = np.full(len(y), y.mean())
    p = np.where(y == 1, 0.7, 0.2)
    p[:5] = np.nan
    res = E.max_t({"T": days}, {"T": y}, {"T": ref}, {("T", "a"): p, ("T", "none"): np.full(len(y), np.nan)}, reps=100, seed=1)
    m = np.isfinite(p)
    assert res[("T", "a")]["bss"] == pytest.approx(K.brier_skill(y[m], p[m], ref[m]))
    assert res[("T", "none")]["p_max_t"] is None


def test_bonferroni_over_the_search_and_holm_count_undefined_tests():
    assert E.bonferroni(0.0004, 118) == pytest.approx(0.0472) and E.bonferroni(0.01, 118) == 1.0 and E.bonferroni(None, 118) is None
    with pytest.raises(E.EvaluationError):
        E.bonferroni(0.1, 0)
    adj = E.holm([0.01, None, 0.02])
    assert adj[0] == pytest.approx(0.03) and math.isnan(adj[1]) and adj[2] == pytest.approx(0.04)


def test_ledger_totals_reproduce_the_frozen_plan_on_the_committed_ledger():
    with open(ROOT / "audits/predictive-intelligence/phase_11/experiments/SEARCH_LEDGER.csv") as f:
        rows = list(csv.DictReader(f))
    tot = E.ledger_totals(rows)
    assert (tot["rows"], tot["candidate_configurations"], tot["bakeoff_configurations"], tot["negative_control_fits"],
            tot["debug_runs"], tot["n_search"]) == (2896, 87, 31, 306, 15, 118)
    assert tot["rows_by_phase"] == {"04": 31, "07": 488, "08": 616, "09": 670, "10": 703, "11": 388}


def test_ledger_totals_refuse_an_unclassified_kind_and_keep_holdout_rows_apart():
    base = {"phase": "12", "experiment_id": "x", "target": "t", "candidate": "c", "seed": "1"}
    with pytest.raises(E.EvaluationError, match="not classified"):
        E.ledger_totals([{**base, "kind": "NEW_MODEL"}])
    tot = E.ledger_totals([{**base, "kind": "SECONDARY_HOLDOUT"}, {**base, "kind": "BASELINE", "candidate": "B2"},
                           {**base, "kind": "REFERENCE_PHASE07", "candidate": "B2"}, {**base, "kind": "NEGATIVE_CONTROL"},
                           {**base, "kind": "NEGATIVE_CONTROL", "seed": "2"}])
    assert tot["holdout_evaluation_rows"] == 1 and tot["candidate_configurations"] == 1 and tot["negative_control_fits"] == 2


def test_shadow_criteria_need_counts_calibration_and_a_non_negative_skill():
    ok = {"n_with_number": 60, "positives": 12, "bss": 0.01, "calibration": {"in_the_large_ok": True, "every_bin_ok": True}}
    assert E.shadow_criteria(ok)["all"] and E.shadow_criteria(ok)["promotion"] == "NONE_IN_PHASE_12"
    assert not E.shadow_criteria({**ok, "positives": 9})["all"]
    assert not E.shadow_criteria({**ok, "bss": -0.01})["all"]
    assert not E.shadow_criteria({**ok, "calibration": {"in_the_large_ok": True, "every_bin_ok": False}})["all"]
    assert E.shadow_criteria({**ok, "calibration": {"in_the_large_ok": True, "every_bin_ok": None}})["calibration"]


def test_prevalence_reports_a_wilson_interval():
    p = E.prevalence([1, 0, 0, 0])
    assert p["prevalence"] == 0.25 and p["wilson"] == list(K.wilson(1, 4))


# ---------------------------------------------------------------- isolation
def _imports(p: Path) -> set[str]:
    out = set()
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            out.add(("." * n.level) + (n.module or ""))
    return out


def test_evaluation_imports_numpy_and_the_standard_library_only():
    std = {"__future__", "datetime", "gzip", "hashlib", "json", "math", "pathlib", "typing"}
    assert _imports(ROOT / "memelab/predictive/evaluation.py") <= std | {"numpy", "."}
    txt = (ROOT / "memelab/predictive/evaluation.py").read_text()
    assert "sklearn" not in txt and "phase_06/sealed" not in txt


def test_no_other_module_imports_the_phase_12_code_and_only_it_names_the_holdout_label_file():
    for p in (ROOT / "memelab").rglob("*.py"):
        if p.name == "evaluation.py":
            continue
        assert not any(i.endswith("evaluation") for i in _imports(p)), p
        assert "predictive.evaluation" not in p.read_text(), p
        assert "holdout_labels.jsonl" not in p.read_text(), p


def test_a_censored_or_pending_row_that_carries_a_label_value_is_still_never_scored():
    t = H + 3600.0
    cen = hrow("c", t, state="LABELED", censored=1)            # a LABELED state with the censored bit: refused on the bit
    pen = hrow("p", t + 1)
    pen["state"] = "PENDING"                                   # a PENDING row that carries a label value (P05)
    gap = hrow("g", t + 2, state="VENDOR_OR_ROUTE_GAP", censored=1)
    gap["label"] = 0                                           # the conservative lens value written into the label column
    got, cnt = E.holdout_rows([cen, pen, gap, hrow("ok", t + 3)], L.T1, as_of=AS_OF)
    assert [r["decision_key"] for r in got] == ["ok"] and cnt["censored"] == 2
