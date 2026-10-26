"""Phase 13 committed outputs (added with them): the recorded run of probes/run_calibration.py says what the gate needs and
nothing more. Reads committed files only; no store, no network."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from memelab.predictive import abstention as AB
from memelab.predictive import calibration as CAL
from memelab.predictive import contract as C
from memelab.predictive import evaluation as E

ROOT = Path(__file__).resolve().parents[1]
P13 = ROOT / "audits/predictive-intelligence/phase_13"
CALD = P13 / "calibration"
SHORTS = ("T1_24h", "T1b_6h", "T2_24h")
EXPECTED_SETS = {"T1_24h": (24, 8, 3), "T1b_6h": (44, 3, 5), "T2_24h": (8, 1, 1)}
TODAY_REASONS = {"FLAG_OFF", "MODEL_NOT_SELECTED", "UNCALIBRATED", "INSUFFICIENT_HISTORY", "NOT_YET_MATURED"}

pytestmark = pytest.mark.skipif(not (P13 / "evidence/run_log.json").exists(), reason="Phase 13 outputs not committed yet")


def _schema_checker():
    spec = importlib.util.spec_from_file_location("p13_abst_tests", ROOT / "tests/test_predictive_abstention.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.schema_errors


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def _csv(p: Path) -> list[dict]:
    with open(p) as f:
        return list(csv.DictReader(f))


def test_the_calibration_artifacts_are_uncalibrated_and_unpublishable():
    for s in SHORTS:
        card = CAL.loads((P13 / f"artifacts/{s}/CALIBRATION_CARD.json").read_text())
        n, k, d = EXPECTED_SETS[s]
        cs = card["calibration_set"]
        assert (cs["n"], cs["k"], cs["days"]) == (n, k, d)
        assert card["status"] == CAL.UNCALIBRATED and card["calibrator"] is None and card["publishable"] is False
        assert card["level"] == "ABSTAIN" and card["evidence"]["status"] == "NOT_YET_MATURED"
        assert "CALIBRATION_SET_TOO_SMALL" in card["details"] and card["fit_gate"]["passed"] is False
        assert card["is_fixture"] is False and card["source"] == "STATISTICAL_MODEL"


def test_every_written_result_is_a_valid_abstention_with_its_record():
    check = _schema_checker()
    for name in ("FORECAST_RESULTS_DEV.jsonl", "FORECAST_RESULTS_HOLDOUT_POST_OPENING.jsonl", "FORECAST_RESULTS_TODAY.jsonl"):
        pairs = _jsonl(CALD / name)
        assert pairs, name
        for pr in pairs:
            doc, rec = pr["document"], pr["record"]
            assert check(pr) == [], (name, check(pr)[:3])
            assert doc["prediction_status"] == "ABSTAIN" and doc["probability"] is None and doc["uncertainty_interval"] is None
            assert C.validate(doc, backtest=C.BACKTEST_NOT_AVAILABLE) == []
            assert set(doc["abstain_reasons"]) == set(rec["reasons"]) and rec["conditions"]
            assert rec["record_id"] == AB.sha({k: v for k, v in rec.items() if k != "record_id"})
            assert f"abstention-1:{rec['record_id']}" in doc["evidence_refs"]
            assert "FLAG_OFF" in doc["abstain_reasons"] and "UNCALIBRATED" in doc["abstain_reasons"]
    for name, src in (("ABSTENTION_RECORDS_DEV.jsonl", "FORECAST_RESULTS_DEV.jsonl"),
                      ("ABSTENTION_RECORDS_HOLDOUT_POST_OPENING.jsonl", "FORECAST_RESULTS_HOLDOUT_POST_OPENING.jsonl")):
        assert _jsonl(CALD / name) == [p["record"] for p in _jsonl(CALD / src)]


def test_coverage_is_zero_and_every_request_is_counted():
    rows = {(r["condition"], r["explanation"]): r for r in _csv(CALD / "ABSTENTION_MATRIX.csv")}
    for s in SHORTS:
        req = int(rows[("COVERAGE_REQUESTS", "dev: requests")][f"dev_{s}"])
        assert int(rows[("COVERAGE_FORECAST", "dev: forecast")][f"dev_{s}"]) == 0
        assert int(rows[("COVERAGE_CALIBRATED_NUMBER", "dev: calibrated_number")][f"dev_{s}"]) == 0
        assert req == EXPECTED_SETS[s][0]
        flag = next(r for (c, _), r in rows.items() if c == "FLAG_OFF")
        assert int(flag[f"dev_{s}"]) == req
        hreq = int(rows[("COVERAGE_REQUESTS", "holdout_post_opening: requests")][f"holdout_post_opening_{s}"])
        assert hreq == {"T1_24h": 66, "T1b_6h": 68, "T2_24h": 59}[s]
        assert int(rows[("COVERAGE_FORECAST", "holdout_post_opening: forecast")][f"holdout_post_opening_{s}"]) == 0
    assert {r["condition"] for r in _csv(CALD / "ABSTENTION_MATRIX.csv") if not r["condition"].startswith("COVERAGE_")} == set(AB.CONDITIONS)


def test_today_every_target_abstains_with_the_standing_reasons():
    t = json.loads((CALD / "TODAY_STATUS.json").read_text())
    assert t["as_of_utc"] == "2026-10-26T20:00:00Z"
    for s in SHORTS:
        v = t["targets"][s]
        assert v["prediction_status"] == "ABSTAIN" and set(v["standing_reasons"]) == TODAY_REASONS
        assert v["calibration_status"] == CAL.UNCALIBRATED


def test_post_opening_results_never_become_claims_and_the_sealed_folder_was_not_read():
    h = json.loads((CALD / "HOLDOUT_POST_OPENING.json").read_text())
    for s in SHORTS:
        assert h[s]["combined_is_a_claim"] is False and h[s]["combined_state"] != E.SURVIVES
        assert h[s]["publication"].startswith("ABSTAIN")
        assert h[s]["max_abs_b2_diff_vs_holdout_scored"] <= 1e-12
    log = json.loads((CALD / "POST_OPENING_LOG.json").read_text())
    assert log["label"] == "POST_OPENING" and log["sealed_folder_read"] is False
    for f, sha in log["inputs_sha256"].items():
        assert hashlib.sha256((ROOT / "audits/predictive-intelligence/phase_12/validation" / f).read_bytes()).hexdigest() == sha


def test_the_replay_was_rederived_exactly_and_the_cx13_traps_refused_real_holdout_rows():
    r = json.loads((CALD / "REPLAY_CHECKS.json").read_text())
    assert r["flag_on"] is False and r["backtest_status"] == C.BACKTEST_NOT_AVAILABLE
    for s in SHORTS:
        v = r["targets"][s]
        assert v["fold_card_sha_equal"] and v["fold_cutoffs_equal"] and v["equal_within_rounding"] and v["card_time_cross_check_equal"]
        assert all(x.startswith("REFUSED") for x in r["traps_cx13_on_real_holdout_rows"][s].values())


def test_the_run_log_matches_the_files_and_the_ledger_adds_no_candidate():
    log = json.loads((P13 / "evidence/run_log.json").read_text())
    assert log["failures"] == [] and log["socket_events"] == [] and log["vendor_calls"] == 0 and log["dirty_code"] == ""
    for rel, sha in log["outputs_sha256"].items():
        assert hashlib.sha256((P13 / rel).read_bytes()).hexdigest() == sha, rel
    tot = E.ledger_totals(_csv(P13 / "experiments/SEARCH_LEDGER.csv"))
    assert tot["candidate_configurations"] == 87 and tot["n_search"] == 118
    claims = {r["claim"] for r in _csv(CALD / "RELIABILITY_COVERAGE.csv")}
    assert all(c.startswith(("DESCRIPTIVE", "POST_OPENING")) for c in claims)
