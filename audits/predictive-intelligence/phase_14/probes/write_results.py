"""Phase 14: write PHASE_14_RESULTS.json from the committed outputs (artifact sha256 computed here; numbers read from the outputs).

    python -B write_results.py HEAD_AFTER [POSTCOMMIT_JSON]
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
P14 = REPO / "audits/predictive-intelligence/phase_14"
ARTIFACTS = ["memelab/predictive/behavioral.py", "tests/test_predictive_behavioral.py", "tests/test_predictive_phase14_outputs.py",
             "tests/fixtures/predictive/behavioral_mock.py", "tools/release_audit.py"] + sorted(
    p.relative_to(REPO).as_posix() for p in P14.rglob("*") if p.is_file() and p.name != "PHASE_14_RESULTS.json" and "postcommit" not in p.parts)


def j(rel):
    return json.loads((P14 / rel).read_text())


def main(head_after: str, post: str | None = None) -> int:
    run, rules, cost, mf, core = j("evidence/run_log.json"), j("behavioral/RULE_COUNTS.json"), j("behavioral/COST_CAP.json"), \
        j("behavioral/MIROFISH_PROBE.json"), j("behavioral/CORE_UNAFFECTED.json")
    mut, orc, seeds = j("evidence/mutation_behavioral.json"), j("evidence/oracle_jsonschema.json"), j("behavioral/SEEDS_DEV_LOG.json")
    grid = j("behavioral/MOCK_GRID_RUNS.json")
    rr, netns, diff = j("skeptic/rp2_recheck.json"), j("behavioral/NETNS_EGRESS.json"), j("evidence/rerun_rp2_diff.json")
    checks = [
        {"name": "G1 package checksums", "command": "sha256sum -c SHA256SUMS.txt", "result": "41 OK, 0 failed", "exit_code": 0, "pass": True},
        {"name": "G2 entry suite at 2fd0aae", "command": "python -m pytest tests -q -p no:cacheprovider",
         "result": "1 failed, 1596 passed in 190.45s (known test_dedup_corroboration_resurface_denial only)", "exit_code": 1, "pass": True},
        {"name": "G2 entry seal check", "command": "python -B audits/predictive-intelligence/phase_06/probes/check_seal.py", "result": "problems []",
         "exit_code": 0, "pass": True},
        {"name": "G2 Phase 13 key tests", "command": "pytest test_predictive_calibration, _abstention, _phase13_outputs, _runtime", "result": "276 passed",
         "exit_code": 0, "pass": True},
        {"name": "G2 Phase 13 runner rerun", "command": "python -B audits/predictive-intelligence/phase_13/probes/run_calibration.py <scratch>",
         "result": "22 of 24 files byte-equal; the 2 run logs differ in head and time", "exit_code": 0, "pass": True},
        {"name": "G3 MiroFish pin recheck", "command": "git rev-parse HEAD; sha256sum LICENSE; git ls-remote .../MiroFish HEAD",
         "result": "7657031a clean; LICENSE 8486a10c...; upstream HEAD equal; Python <3.13; LLM and Zep keys required", "exit_code": 0, "pass": True},
        {"name": "G4 to G15, G19 unit tests (repair pass 2)", "command": "python -m pytest tests/test_predictive_behavioral.py -q",
         "result": "204 passed, 1 skipped (no IPv6 loopback in the sandbox); the two netns tests ran (unshare -n usable)", "exit_code": 0, "pass": True},
        {"name": "G16 seeds", "command": "python -B probes/build_seeds.py <scratch>", "result":
         f"{seeds['development_decisions']} seeds, {seeds['seeds_refused']} refused, label calls {len(seeds['label_calls'])}, socket events {len(seeds['socket_events'])}",
         "exit_code": 0, "pass": seeds["seeds_refused"] == 0 and not seeds["label_calls"]},
        {"name": "G16 rules on real seeds", "command": "python -B probes/run_behavioral.py <scratch> (part A)", "result":
         f"labels {rules['labels']}; catalyst hypotheses {rules['catalyst_hypotheses']}; twin byte-equal {rules['twin_byte_equal']}; "
         f"validation errors {rules['documents_with_validation_errors']}; unscored", "exit_code": 0,
         "pass": rules["catalyst_hypotheses"] == 0 and rules["twin_byte_equal"] and rules["documents_with_validation_errors"] == 0},
        {"name": "G10 stability grids", "command": "run_behavioral.py part B", "result": {k: v["stability"]["status"] for k, v in grid.items()},
         "exit_code": 0, "pass": all((v["stability"]["status"] == "STABLE") == k.endswith(":STABLE") for k, v in grid.items())},
        {"name": "G12 failure matrix", "command": "run_behavioral.py part C", "result": "45 cases; simulation_state agrees on every case (AVAILABLE exactly when SIMULATION_RAN)",
         "exit_code": 0, "pass": run["summary"]["p30_all_not_available_except_stable"]},
        {"name": "G13 cost caps", "command": "run_behavioral.py part D", "result":
         f"worst-case requests {cost['worst_case_refusal']['service_requests']}; meter charged {cost['meter_cap']['meter']['charged_microusd']} of "
         f"{cost['meter_cap']['meter']['cap_microusd']} micro-USD; breaker {cost['upstream_breaker']['codes']}", "exit_code": 0,
         "pass": cost["worst_case_refusal"]["service_requests"] == 0 and cost["meter_cap"]["charged_not_above_cap"]},
        {"name": "G17 MiroFish through the boundary", "command": "run_behavioral.py part E", "result":
         {k: [v["status"], v["reasons"]] for k, v in mf["runs"].items()} | {"same_seed_trace_identical": mf["same_seed_trace_identical"]},
         "exit_code": 0, "pass": mf["runs"]["meter_cap_low"]["reasons"] == ["COST_CAP_REACHED"] and mf["runs"]["llm_down"]["reasons"] == ["NO_LLM_ACTIONS"]},
        {"name": "G18 core unaffected", "command": core["command"], "result": f"blocker {core['blocker']}; {core['byte_equal']} byte-equal; differ {core['differ']}",
         "exit_code": core["exit_code"], "pass": core["pass"]},
        {"name": "G6 loopback only in the recorded run", "command": "audit hook in run_behavioral.py", "result":
         f"{run['socket_connects']} connects, hosts {run['socket_hosts']}", "exit_code": 0, "pass": run["socket_hosts"] == ["127.0.0.1"]},
        {"name": "G19 mutation probe", "command": "python -B probes/mutation_behavioral.py OUT", "result": f"{mut['caught']} of {mut['mutations']} caught",
         "exit_code": 0, "pass": mut["survivors"] == []},
        {"name": "G8 schema oracle", "command": "python -B probes/oracle_schema.py OUT", "result":
         f"jsonschema {orc['jsonschema_version']}: {orc['schema_errors']} errors on {orc['documents']} documents", "exit_code": 0, "pass": orc["schema_errors"] == 0},
        {"name": "Skeptic findings rechecked (repair pass 2)", "command": "python -B skeptic/rp2_recheck.py skeptic/rp2_recheck.json",
         "result": "first-pass code c59c494: CX-S14 NOT CAUGHT, A1 to A4 NOT CAUGHT, meter bill up to 55 times the cap, egress E3 and E4 received the "
                   "request; repaired code: all CAUGHT, 0 multiplied calls forwarded, E3 and E4 nothing received", "exit_code": 0,
         "pass": rr["repaired_working_tree"]["cx14_monitor_reversal"]["exit"] == 0 and rr["first_pass_c59c494"]["cx14_monitor_reversal"]["exit"] == 1},
        {"name": "G6 netns child egress (repair M4)", "command": "run_behavioral.py part G", "result":
         f"received from children {netns['received_from_children']}; positive control {netns['positive_control_from_parent_received']}",
         "exit_code": 0, "pass": netns["received_from_children"] == 0 and netns["positive_control_from_parent_received"]},
        {"name": "Repeated recorded run against the first pass", "command": "python -B probes/rerun_diff.py OUT evidence/rerun_rp2_diff.json",
         "result": f"rule documents equal after removing the added field, time and digest: {diff['rule_documents']['equal_after_removing_doc_sha_created_at_and_llm_actions_observed']} of 830; seeds byte-equal {diff['seeds_byte_equal']}",
         "exit_code": 0, "pass": diff["rule_documents"]["hypotheses_equal"] == 830 and diff["seeds_byte_equal"]},
        {"name": "PI-D-074 release audit entries", "command": "python -B probes/release_exempt_compare.py 2fd0aae", "result":
         "findings outside the Phase 14 files equal (63 reviewed, 0 unexplained)", "exit_code": 0, "pass": True},
    ]
    if post:
        checks += json.loads(Path(post).read_text())
    res = {"phase": "14", "status": "TEST_ONLY",
           "status_statement": ("TEST_ONLY: the simulator path is proved only on fixtures, the lab's mocks and MiroFish's script against a canned "
                                "mock LLM; live use is BLOCKED pending Elving's approval of LLM spend. The statistical-engine-unaffected item and "
                                "the safety items (egress, no probability, seeds, stability, failure states, cost) PASS after repair pass 2."),
           "gate": {"MIROFISH_GATE": "BLOCKED", "simulator_path": "TEST_ONLY", "rule_based_generator": "REAL_SEEDS_UNSCORED",
                    "statistical_engine_unaffected": "PASS", "safety_items": "PASS"},
           "head_before": "2fd0aae", "head_after": head_after,
           "commits": {"pre_registration": "9ed8377", "frozen_code_first_pass": "c59c494", "recorded_run_first_pass": "872578d",
                       "records_first_pass": "bf06b87", "frozen_code_repair_pass_2": "69a3584", "skeptic_reviewed_at": "58bee5d"},
           "repair_pass_2": {"skeptic": "skeptic/PHASE_14_SKEPTIC.md", "material": 5, "minor": 6, "counterexample": "CX-S14 monitor reversal",
                             "caught_by": "tests/test_predictive_behavioral.py::test_cx_s14_a_seed_reversed_monitor_is_unstable",
                             "decision": "PI-D-076", "disagreements": [
                                 "A5 'future unix time as a number value' uses 1790000000 (2026-09-21T14:13:20Z), which is before the decision "
                                 "2026-10-12T05:00:00Z, so accepting it is correct; a value after the decision is refused (test with 1791800000).",
                                 "X3 (IP check removed) is an equivalent mutation: the netloc comparison already admits only the two literals."]},
           "result": {"development_seeds": seeds["development_decisions"], "rule_labels": rules["labels"], "catalyst_hypotheses": rules["catalyst_hypotheses"],
                      "mirofish": {k: v["status"] for k, v in mf["runs"].items()}, "spend_usd": 0, "language_model_calls": 0, "labels_read_by_phase_14_code": 0},
           "checks": checks,
           "artifacts": [{"path": p, "sha256": hashlib.sha256((REPO / p).read_bytes()).hexdigest()} for p in ARTIFACTS],
           "limitations": [
               "Simulator path is TEST_ONLY: proved on the lab's mocks, fictional seeds and MiroFish's script against a canned mock LLM; no live LLM exists on the path.",
               "MiroFish output on the script path is free text and NOT_CODABLE; coding it needs the paid ReportAgent or blind coders (Phase 15 protocol).",
               "MiroFish is not reproducible for a fixed seed (traces differ), so its scenarios are UNSTABLE under the frozen grid without many repetitions.",
               "Grounding is checked by observation kind and state, not by value; stability compares label sets only; injection patterns are a heuristic.",
               "unshare -n isolates the network, not the filesystem; a live run would need a separate container or user with only the request mounted.",
               "The meter's cap holds for one meter lifetime; a live route also needs a persistent spend ledger across runs.",
               "The rule-based generator is unscored; its label counts say how often each rule fires, not whether any scenario happened.",
               "No catalyst or social rows are exported, so no real seed holds a catalyst event and catalyst rules never fired on real data.",
               "The core-unaffected check re-executes Phase 13's runner, which reads what Phase 13 read; Phase 14's own code reads no label.",
               "IPv6 loopback could not be tested in this sandbox (one test skipped).",
               "The netns suite tests skip, with a recorded reason, where unshare -n is unusable; they ran here."],
           "blockers": ["Live MiroFish or any LLM simulation: no approved LLM, Zep or other paid spend and no API key (PI-D-005)."],
           "approvals_needed": ["Elving: an LLM budget (max_cost_usd) and a named upstream, plus change control, before any live behavioral simulation; "
                                "an LLM with a declared training cutoff before the evaluated events; filesystem isolation for the engine."],
           "next_eligible_phase": "15, if the orchestrator or Elving accepts a TEST_ONLY Phase 14 as its entry (the package's entry gate asks for PASS)"}
    (P14 / "PHASE_14_RESULTS.json").write_text(json.dumps(res, indent=1) + "\n")
    print(res["status"], len(res["artifacts"]), all(c["pass"] for c in res["checks"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
