"""Phase 14 committed outputs (added with them, after the recorded run at the frozen code c59c494): the recorded run's log, the
rule-based scenarios on the 830 development seeds (re-derived here, byte-equal), the mock grids, the failure matrix, the cost
caps, the MiroFish boundary probe, the core-unaffected check and the mutation probe. No network, no store, no label."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from memelab.predictive import behavioral as B

ROOT = Path(__file__).resolve().parents[1]
P14 = ROOT / "audits/predictive-intelligence/phase_14"
FROZEN = "c59c494ae5b6c91ddca89916a799aed03a6a7960"


def j(rel):
    return json.loads((P14 / rel).read_text())


def test_run_log_is_the_frozen_code_with_loopback_only_and_no_label():
    log = j("evidence/run_log.json")
    assert log["head"] == FROZEN and log["dirty_code"] == ""
    assert log["socket_hosts"] == ["127.0.0.1"] and log["socket_connects"] > 0
    assert log["label_calls"] == [] and log["sealed_opens"] == [] and log["vendor_calls"] == 0 and log["paid_calls"] == 0
    for rel, h in log["files"].items():
        if rel.startswith("behavioral/"):
            assert hashlib.sha256((P14 / rel).read_bytes()).hexdigest() == h, rel
    seeds_log = j("behavioral/SEEDS_DEV_LOG.json")
    assert seeds_log["head"] == FROZEN and seeds_log["label_calls"] == [] and seeds_log["socket_events"] == []
    assert seeds_log["feature_store_sha256_before"] == seeds_log["feature_store_sha256_after"]


def test_seeds_pass_and_rule_documents_rederive_byte_equal():
    lines = (P14 / "behavioral/SEEDS_DEV.jsonl").read_text()
    assert hashlib.sha256(lines.encode()).hexdigest() == j("behavioral/SEEDS_DEV_LOG.json")["seeds_sha256"]
    rows = [json.loads(x) for x in lines.splitlines()]
    counts = j("behavioral/RULE_COUNTS.json")
    assert len(rows) == counts["seeds"] == 830
    assert all(B.check_seed(r["seed"]) == [] == r["check_seed"] for r in rows)
    assert all(B.C.parse_utc(r["seed"]["decision_time_utc"]) < B.C.parse_utc("2026-10-17T00:00:00Z") for r in rows)
    body = "\n".join(B.canon({"decision_key": r["decision_key"], "document": B.rule_scenarios(r["seed"], created_at_utc=counts["created_at_utc"])})
                     for r in rows) + "\n"
    assert body == (P14 / "behavioral/RULE_SCENARIOS_DEV.jsonl").read_text()
    assert counts["catalyst_hypotheses"] == 0 and counts["documents_with_validation_errors"] == 0 and counts["twin_byte_equal"]
    assert counts["labels"] == {"ATTENTION_EXHAUSTION": 309, "MANUFACTURED_ATTENTION_DUMP": 313, "NO_GROUNDED_SCENARIO": 227,
                                "ORGANIC_ATTENTION_CONTINUATION": 66}
    assert counts["scored"] is False and counts["outcomes_read"] is False
    assert not any(o["kind"] == B.CATALYST_EVENT for r in rows for o in r["seed"]["observations"])
    m = counts["real_seed_mutations"]
    assert "OBSERVATION_AFTER_DECISION" in m["observation_one_second_after_decision"]["check_seed"]
    assert "POST_DECISION_DATE" in m["quoted_text_with_post_decision_date"]["check_seed"]
    assert "BEHAVIORAL_FEEDBACK" in m["behavioral_derived_observation"]["check_seed"]
    assert all(v["rule_status"] == B.SEED_REFUSED and v["hypotheses"] == 0 for v in m.values())


def test_mock_grids_and_failure_matrix():
    g = j("behavioral/MOCK_GRID_RUNS.json")
    for seed in ("fictional", "real_development_seed"):
        assert g[f"{seed}:STABLE"]["stability"]["status"] == B.STABLE
        for mode, flag in (("SEED_SENSITIVE", "SEED_SENSITIVE"), ("PERSONA_SENSITIVE", "PERSONA_SENSITIVE"),
                           ("NONREPRODUCIBLE", "NOT_REPRODUCIBLE"), ("EVIDENCE_BLIND", "NOT_SOURCE_GROUNDED")):
            r = g[f"{seed}:{mode}"]
            assert r["stability"]["status"] == B.UNSTABLE and flag in r["stability"]["flags"] and "UNSTABLE_EXPLORATORY" in r["reasons"]
        assert all(v["valid"] for k, v in g.items())
    rows = list(csv.DictReader(open(P14 / "behavioral/P30_MATRIX.csv")))
    assert len(rows) == 39
    for r in rows:
        ran = r["case"] in ("service:STABLE", "service:WALLET_CLAIM", "subprocess:STABLE")
        assert r["simulation_state"] == ("AVAILABLE" if ran else "SIMULATION_NOT_AVAILABLE"), r
        assert r["abstain_reason"] == "" and r["valid_document"] == "True"
        if r["case"].startswith(("gate:", "egress:")):
            assert r["service_requests"] == "0"


def test_cost_caps_and_breakers():
    c = j("behavioral/COST_CAP.json")
    assert c["worst_case_refusal"]["service_requests"] == 0 and c["worst_case_refusal"]["reasons"] == ["COST_CAP_REACHED"]
    m = c["meter_cap"]
    assert m["charged_not_above_cap"] and m["meter"]["charged_microusd"] <= m["meter"]["cap_microusd"]
    assert m["first_run"]["reasons"] == m["second_run"]["reasons"] == ["COST_CAP_REACHED"]
    assert m["upstream_calls"] == m["upstream_calls_after_first_run"] and m["max_tokens_seen_upstream"] == [512]
    assert c["upstream_breaker"]["codes"] == [500] * 5 + [503, 503] and c["upstream_breaker"]["upstream_calls"] == 5
    assert c["prompt_call_kill"]["prompt_over_cap"] == 413 and c["prompt_call_kill"]["four_calls_cap_three"] == [200, 200, 200, 429]
    assert c["prompt_call_kill"]["after_kill"] == 503


def test_mirofish_probe_through_the_boundary():
    m = j("behavioral/MIROFISH_PROBE.json")
    assert m["clone_head"] == "7657031ac01184afe2cb220f5ee3545573b5e843"
    r = m["runs"]
    for k in ("meter_cap_high", "meter_cap_high_repeat"):
        assert r[k]["status"] == B.SIMULATION_RAN and r[k]["reasons"] == ["NOT_CODABLE"] and r[k]["llm_actions"] > 0 and r[k]["labels"] == []
    assert r["meter_cap_low"]["reasons"] == ["COST_CAP_REACHED"] and r["meter_cap_low"]["cost"]["est_cost_usd"] <= 0.03
    assert r["meter_cap_low"]["cost"]["calls_refused"] > 0
    assert r["llm_down"]["reasons"] == ["NO_LLM_ACTIONS"] and r["llm_down"]["runner_side"]["script_exit_code"] == 0
    assert r["llm_down"]["runner_side"]["meter_breaker_open"] is True
    assert r["config_cap_below_worst_case"]["reasons"] == ["COST_CAP_REACHED"] and r["config_cap_below_worst_case"]["runner_side"] is None
    assert m["same_seed_trace_identical"] is False
    assert all(v["contamination_flags"] == list(B.P26_FLAGS) and v["valid"] for v in r.values())


def test_core_unaffected_and_mutation_probe():
    c = j("behavioral/CORE_UNAFFECTED.json")
    assert c["pass"] and c["blocker"] == "BLOCKER_OK" and c["byte_equal"] == 22 and c["new"] == []
    mut = j("evidence/mutation_behavioral.json")
    assert mut["mutations"] == mut["caught"] >= 60 and mut["survivors"] == []
    o = j("evidence/oracle_jsonschema.json")
    assert o["documents"] == 830 and o["schema_errors"] == 0 and o["lab_validator_errors"] == 0
