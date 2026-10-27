"""Phase 17 committed outputs: the real-path smoke, the export replay, the trace examples, the fixture path and the ledger say
exactly what the evidence allows (every real request abstains; nothing published; the flag-off body unchanged). Reads committed
files only; no network, no store."""
from __future__ import annotations

import csv
import json
import subprocess
from collections import Counter
from pathlib import Path

from memelab.predictive import contract as C
from memelab.predictive import evaluation as E

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / "audits/predictive-intelligence"
P17 = AUD / "phase_17"
SMOKE = P17 / "smoke"


def _j(name):
    return json.loads((SMOKE / name).read_text())


def test_the_real_scout_runs_exit_0_the_flag_off_body_is_unchanged_and_the_on_body_only_gains_a_section():
    d = _j("REAL_PATH_SMOKE.json")
    assert set(d["exit_codes"].values()) == {0} and len(d["exit_codes"]) == 16
    assert d["base_vs_frozen_off_all_reports_byte_equal"] is True and d["reports_compared"] == 9
    assert d["frozen_on_token_reports_byte_equal_to_base"] is True and d["frozen_on_scout_is_base_plus_appended_section"] is True
    assert d["lab_tables_equal_base_off_frozen_off_frozen_on"] is True
    assert d["section_abstain_lines"] == 24 and d["section_forecast_lines"] == 0
    assert d["checkout_status"] == [] and d["sandbox_final_tracked_changes"] == []
    assert all(v == [] for v in d["sandbox_tracked_changes_after_scout_runs"].values())


def test_the_real_states_show_exactly_once_idempotent_bounded_and_internal_references():
    st = _j("REAL_PATH_SMOKE.json")["states"]
    assert st["state"]["event_counts"] == {"DISCOVERY": 8, "DUPLICATE": 16} and st["state"]["documents"] == 24      # rerun and retry
    assert st["state_storm"]["event_counts"] == {"DISCOVERY": 8, "SUPERSEDED_IN_PASS": 4}                         # PAID x5: one attempt
    assert st["state_research"]["reference_records"] == 48 and st["state_research"]["documents"] == 24
    assert st["state_analyze"]["event_counts"] == {"DISCOVERY": 1}
    for s in st.values():
        assert s["completed_forecasts"] == 0 and s["models_in_use"] == ["not_selected"] and s["errors"] == 0
        assert s["documents"] == s["records"] == 3 * s["attempted"]
        assert {"MODEL_NOT_SELECTED", "UNCALIBRATED", "SOURCE_STALE", "INSUFFICIENT_HISTORY"} <= set(s["reason_counts"])
    assert all(c["problems"] == [] for c in _j("REAL_PATH_SMOKE.json")["checks"].values())


def test_the_section_names_the_registry_calibration_backtest_staleness_and_carries_no_number_or_trading_word():
    sec = (SMOKE / "REAL_SCOUT_SECTION.md").read_text()
    assert sec.startswith("\n## Predictive research section (flag on, research only)")
    assert sec.count("NO_VIABLE_CHAMPION") == 3 and sec.count("calibration UNCALIBRATED") == 3
    assert "Backtesting: BACKTEST_NOT_AVAILABLE" in sec and "Depth collector: COLLECTOR_NOT_AVAILABLE" in sec
    assert sec.count("Inputs: INPUT_STALE") == 8 and sec.count("Fatal-flag veto: ") == 8
    assert "FORECAST;" not in sec and "%" not in sec.replace("+25%", "").replace("-15%", "")
    import re
    from memelab.predictive import abstention as AB
    body = re.sub(r"`[^`]*`", "", sec)
    assert not any(re.search(r"\b" + re.escape(w) + r"\b", body.lower()) for w in AB.TRADING_WORDS)
    assert "/tmp/" not in sec and "OUTDIR" not in sec and "state directory" in sec                         # CP17-1 (skeptic m8)


def test_the_export_replay_abstains_everywhere_and_is_idempotent():
    d = _j("REAL_EXPORT_REPLAY.json")
    assert d["ref"] == "71fc50e1eb86d916034bb0285a466cf2ec1cc4d0" and d["window_from_utc"] == C.ACCEPTANCE["prospective_from_utc"]
    assert d["window_decision_events"] == 52 and d["window_commits"] == 3
    assert d["round_1_events"] == {"DISCOVERY": 47, "MATERIAL_CHANGE": 5} and d["round_2_events"] == {"DUPLICATE": 52}
    assert d["round_1_documents"] == 156 and d["round_2_documents"] == 0 and d["documents"] == d["records"] == 156
    assert d["probabilities_published"] == 0 and d["forecast_documents"] == 0 and d["model_ids"] == ["not_selected"]
    assert d["backtest_status"] == ["BACKTEST_NOT_AVAILABLE"] and d["registry_modes"] == ["NO_VIABLE_CHAMPION"]
    assert d["pin_reasons_seen"] == ["NO_PIN"]          # the registry was pinned on 2026-10-27, after these decisions
    assert d["every_document_has_its_record"] and d["unique_forecast_ids"] and d["documents_equal_three_per_attempt"]
    assert d["socket_events"] == 0 and d["reference_records"] == 0


def test_three_traceable_real_examples_and_the_fixture_forecast_path():
    t = _j("TRACE_EXAMPLES.json")["examples"]
    assert [e["example"].split(",")[0] for e in t] == ["scout ON", "scout ON", "export replay"]
    for e in t[:2]:
        assert e["snapshot_hash_recomputed_without_report_path"] and e["row_sha256_recomputed"]          # CP17-1 (skeptic m7)
        assert e["token_report_named_in_section"] and e["record_ids_in_section"]
        assert all(x["prediction_status"] == "ABSTAIN" and x["probability"] is None and x["document_checks"] == [] for x in e["targets"])
    assert t[1]["veto"]["veto"] is True and t[1]["veto"]["flags"] == ["CANNOT_EXIT_5K"]
    rep = t[2]["requests"]
    assert [r["event"] for r in rep] == ["DISCOVERY", "MATERIAL_CHANGE", "MATERIAL_CHANGE"]
    assert all(r["snapshot_row_found_in_that_export"] and r["decision_time_basis"] == "EXPORT_COMMIT" for r in rep)
    assert all("OUT_OF_SCOPE_CHAIN" in x["reasons"] for r in rep for x in r["targets"])
    fx = _j("FIXTURE_E2E.json")
    assert fx["evidence_class"] == "TEST_ONLY" and len(fx["forecast_documents"]) == 2 and fx["abstentions"] == 4
    assert all(d["is_fixture"] and "SHADOW_RESEARCH_ONLY" in d["caveats"] for d in fx["forecast_documents"])
    assert fx["section_has_veto"] and fx["section_has_record_ids"] and fx["check_state"]["problems"] == []


def test_the_search_ledger_extends_phase_16_with_runs_that_are_not_configurations():
    base = list(csv.DictReader(open(AUD / "phase_16/experiments/SEARCH_LEDGER.csv")))
    led = list(csv.DictReader(open(P17 / "experiments/SEARCH_LEDGER.csv")))
    assert led[:len(base)] == base
    new = led[len(base):]
    assert Counter(r["kind"] for r in new) == Counter({"DEBUG_RUN_REAL_DATA": 4, "TRAP_OR_CHECK": 30})         # CP17-1: two repeats
    assert all(r["claim"] == "INTEGRATION_RUN_NOT_A_CONFIGURATION" and r["phase"] == "17" for r in new)
    tot = E.ledger_totals(led)
    assert tot["n_search"] == 130 and tot["n_search"] + E.rule_configurations(led) == 169


def test_the_mutation_probe_at_the_frozen_code_caught_every_mutation():
    d = json.loads((P17 / "evidence/mutation_integration.json").read_text())
    assert d["mutations"] == 73 and d["caught"] == 73 and d["survivors"] == []                              # CP17-1: 14 more
    iso = json.loads((P17 / "evidence/rp2_isolation_mutations.json").read_text())
    assert iso["survivors"] == [] and iso["known_limit_survivors"] == ["pipeline_concat_string"]
    old = json.loads((P17 / "evidence/rp2_old_code_check.json").read_text())
    assert old["old_code"] == "ea73cfb" and old["all_fail_on_old_code"] is True and len(old["tests"]) == 10
    assert all(old["pinning_tests_pass_on_old_code"].values()) and len(old["pinning_tests_pass_on_old_code"]) == 4


def test_pre_registration_was_committed_before_the_integration_code():
    def first(path):
        out = subprocess.run(["git", "-C", str(ROOT), "log", "--reverse", "--format=%H", "--", path], capture_output=True, text=True)
        lines = out.stdout.split()
        assert out.returncode == 0 and lines, f"no history for {path} (a shallow or exported tree cannot prove the order)"
        return lines[0]
    pre = first("audits/predictive-intelligence/phase_17/ACCEPTANCE_CHECKLIST.md")
    code = first("memelab/predictive/integration.py")
    assert pre != code
    assert subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", pre, code]).returncode == 0


def test_every_phase_17_json_passes_the_content_guard_tracked_or_not():
    from memelab.social import content_guard as G
    paths = sorted(p.relative_to(ROOT).as_posix() for p in P17.rglob("*.json"))
    assert len(paths) >= 6
    out = G.scan(ROOT, paths)
    assert out["violations"] == [], out["violations"][:3]
