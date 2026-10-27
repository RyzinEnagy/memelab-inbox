"""Phase 15 committed outputs (added with them): blind coding hashes and order, the event count, the decision, the cumulative
ledger and the absence of any outcome in the coding files. Reads only committed files; no network, no label store."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

from memelab.predictive import evaluation as E
from memelab.predictive import scenario_eval as S

ROOT = Path(__file__).resolve().parents[1]
P15 = ROOT / "audits/predictive-intelligence/phase_15"


def _load(p):
    return json.loads((P15 / p).read_text())


def test_coding_files_are_the_logged_ones_and_the_coding_run_was_blind():
    log = _load("behavioral/CODING_LOG.json")
    for k, v in log["outputs_sha256"].items():
        assert hashlib.sha256((P15 / k).read_bytes()).hexdigest() == v, k
    assert log["label_calls"] == [] and log["forbidden_opens"] == [] and log["socket_events"] == []
    assert log["development_recompute_differences"] == 0 and log["documents_with_validation_errors"] == 0
    res = _load("behavioral/INCREMENTAL_VALUE_RESULTS.json")
    assert res["coding_outputs_sha256"] == log["outputs_sha256"]


def test_coding_was_committed_before_the_scoring_code_and_outputs():
    def first(path):
        out = subprocess.run(["git", "-C", str(ROOT), "log", "--diff-filter=A", "--format=%H", "--", path], capture_output=True, text=True)
        return out.stdout.split()[-1] if out.returncode == 0 and out.stdout.split() else None
    # repair pass 2 (skeptic m5): a shallow or exported tree cannot show the order, so the test fails instead of passing
    shallow = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--is-shallow-repository"], capture_output=True, text=True)
    assert shallow.returncode == 0 and shallow.stdout.strip() == "false", "the order check needs the full git history"
    coding = first("audits/predictive-intelligence/phase_15/behavioral/SCENARIO_CODING.csv")
    scorer = first("audits/predictive-intelligence/phase_15/probes/score_scenarios.py")
    assert coding and scorer, "the order check needs the commits that added the coding outputs and the scorer"
    assert coding.startswith("7b787bf") and scorer.startswith("0abffd5"), (coding, scorer)
    anc = subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", coding, scorer])
    assert anc.returncode == 0 and coding != scorer


def test_coding_files_hold_no_outcome_column():
    for name in ("SCENARIO_CODING.csv", "CONTROL_CODING.csv", "EVENT_SET.csv"):
        cols = next(csv.reader(open(P15 / "behavioral" / name)))
        for c in cols:
            assert not S.OUTCOME_KEY.match(c), (name, c)
        assert "label" not in cols and "brier" not in " ".join(cols)


def test_event_count_and_decision():
    ev = list(csv.DictReader(open(P15 / "behavioral/EVENT_SET.csv")))
    assert sum(r["eligible_catalyst_event"] == "True" for r in ev) == 0
    assert sum(r["row_kind"] == "DECISION_SNAPSHOT" for r in ev) == 925
    res = _load("behavioral/INCREMENTAL_VALUE_RESULTS.json")
    d = res["decision"]
    assert d["eligible_events"] == 0 and d["validation"] == S.INSUFFICIENT_VALIDATION
    assert d["mirofish"] == S.MIROFISH_NO_GO and d["rules_1"] == S.RULES_NOT_PROMOTED
    assert d["probability_created"] is False and d["live_capability_created"] is False
    for t in ("T1_24h", "T1b_6h", "T2_24h"):
        a = res["E1"][t]["A_WARN_vs_B0"]
        assert a["verdict_with_holm"] in ("INSUFFICIENT_DAYS", "INSUFFICIENT_EVENTS") and a["selection_status"] == E.NO_UNCORRECTED_SKILL
    assert not res["controls"]["NCB_VERIFIED_T1"]["ncb_failed"]
    assert all(v["equal"] for v in res["E1_restated_equal_to_phase10"].values())


def test_cumulative_ledger_keeps_phase_13_rows_and_every_registered_configuration():
    prior = list(csv.DictReader(open(ROOT / "audits/predictive-intelligence/phase_13/experiments/SEARCH_LEDGER.csv")))
    led = list(csv.DictReader(open(P15 / "experiments/SEARCH_LEDGER.csv")))
    assert led[:len(prior)] == prior
    new = led[len(prior):]
    assert {r["phase"] for r in new} == {"15"}
    ids = {r["experiment_id"] for r in new}
    reg = list(csv.DictReader(open(P15 / "experiments/EXPERIMENT_REGISTRY.csv")))
    kinds = {"SIMPLE_ATTENTION_RULE", "DESCRIPTION_ONLY", "NEGATIVE_CONTROL", "POST_OPENING_CHECK", "TRAP_OR_CHECK"}
    assert [r["experiment_id"] for r in reg if r["kind"] in kinds and r["experiment_id"] not in ids] == []
    tot = E.ledger_totals(led)
    assert tot["n_search"] == 121 and tot == _load("experiments/LEDGER_TOTALS.json")["after"]
    assert sum(r["kind"] == "DEBUG_RUN_REAL_DATA" for r in new) == 5
