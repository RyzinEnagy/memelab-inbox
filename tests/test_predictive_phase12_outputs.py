"""Phase 12: the committed outputs of the single opening are the ones the run wrote, the predictions were fixed before it, and the
reported result is the frozen plan's. Reads committed files only (no store, no sealed folder, no network)."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from memelab.predictive import evaluation as E

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / "audits/predictive-intelligence/phase_12/validation"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_the_holdout_was_opened_once_after_the_seal_check_with_the_pinned_bytes():
    log = json.loads((VAL / "OPENING_LOG.json").read_text())
    assert [e["mode"] for e in log["entries"]] == ["FIRST_OPENING"]
    e = log["entries"][0]
    assert e["label_file_sha256_read"] == E.SEAL_PINS["holdout_labels_sha256"] and e["seal_problems"] == []
    assert e["seal_report"] == {k: E.SEAL_PINS[k] for k in ("holdout_labels_sha256", "seal_sha256", "seal_json_sha256")}
    assert e["prediction_manifest_sha256"] == sha(VAL / "PREOPEN_MANIFEST.json")
    for name, h in e["outputs_sha256"].items():
        assert sha(VAL / name) == h, name


def test_every_prediction_file_is_the_one_fixed_before_the_opening():
    man = json.loads((VAL / "PREOPEN_MANIFEST.json").read_text())
    assert man["labels_read"] == 0
    for name, h in man["files"].items():
        assert sha(VAL / name) == h, name


def test_the_champions_were_the_development_rule_and_no_primary_result_is_a_skill_claim():
    cands = json.loads((VAL / "CANDIDATES.json").read_text())
    assert {s: c["champion"] for s, c in cands["champions"].items()} == {"T1_24h": "P07_B2", "T1b_6h": "P07_B2", "T2_24h": "P07_B2"}
    prim = json.loads((VAL / "PRIMARY_RESULTS.json").read_text())["primary"]
    assert {s: v["metric"]["verdict"] for s, v in prim.items()} == {
        "T1_24h": "NOT_DISTINGUISHABLE_FROM_BASE_RATE", "T1b_6h": "NOT_DISTINGUISHABLE_FROM_BASE_RATE", "T2_24h": "INSUFFICIENT_EVENTS"}
    assert all(v["shadow_criteria"]["promotion"] == "NONE_IN_PHASE_12" for v in prim.values())


def test_no_secondary_candidate_survives_the_frozen_selection_correction():
    with open(VAL / "HOLDOUT_METRICS.csv") as f:
        sec = [r for r in csv.DictReader(f) if r["kind"] == "SECONDARY_HOLDOUT"]
    assert len(sec) == 129 and all(r["skill_after_selection_correction"] == "0" for r in sec)
    assert all(r["n_search"] == "118" for r in sec)


def test_the_full_ledger_keeps_the_search_size_and_adds_only_evaluations_controls_and_runs():
    tot = json.loads((VAL / "FULL_LEDGER_TOTALS.json").read_text())
    assert tot["candidate_configurations"] == 87 and tot["n_search"] == 118 and tot["bakeoff_configurations"] == 31
    with open(VAL / "FULL_EXPERIMENT_LEDGER.csv") as f:
        rows = list(csv.DictReader(f))
    assert E.ledger_totals(rows) == tot


def test_post_opening_corrections_are_logged_left_the_recorded_outputs_alone_and_only_made_results_more_conservative():
    log = json.loads((VAL / "POST_OPENING_LOG.json").read_text())
    assert log["label"] == "POST_OPENING" and log["recorded_outputs_unchanged"] and not log["sealed_folder_read"]
    for name, h in log["outputs_sha256"].items():
        assert sha(VAL / name) == h, name
    assert log["n_search_post_opening"] == 127 and log["max_t_vs_b2_family"] == 51
    with open(VAL / "POST_OPENING_CORRECTIONS.csv") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 129
    assert not any(r["selection_status_final"] in (E.SURVIVES, E.NOT_COMPUTED, E.POST_OPENING_NOT_A_CLAIM) for r in rows)
    assert all(r["p_max_t_vs_b2_post_opening"] for r in rows if r["reference"] == "P07_B2" and r["bss"])


def test_the_corrected_ledger_keeps_every_recorded_row_and_no_holm_only_verdict_reads_as_a_claim():
    with open(VAL / "FULL_EXPERIMENT_LEDGER.csv") as f:
        rec = list(csv.DictReader(f))
    with open(VAL / "FULL_EXPERIMENT_LEDGER_CORRECTED.csv") as f:
        cor = list(csv.DictReader(f))
    assert [{k: r[k] for k in rec[0]} for r in cor[:len(rec)]] == rec
    for r in cor:
        if r["verdict"] == E.HOLDOUT_SKILL:
            assert r["claim"] == "NOT_A_CLAIM_VERDICT_IS_HOLM_ONLY" and r["selection_status"] == E.FAILS
        assert r["claim"] != "CLAIM_SKILL_AFTER_SELECTION_CORRECTION"
    assert all(r["kind"] == "POST_OPENING_CHECK" for r in cor[len(rec):]) and len(cor) == len(rec) + 3
