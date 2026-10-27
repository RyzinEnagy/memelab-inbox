"""Phase 18 committed outputs: the real reports and dry-run alerts say exactly what the evidence allows (every real target
abstains; no number, no trade word, no local path; nothing sent), the flag-off lab output repeated byte-identical at the frozen
commit, the mutation probe and the ledger. Reads committed files only; no network, no store."""
from __future__ import annotations

import json
import re
from pathlib import Path

from memelab.predictive import reports as RP
from memelab.social import content_guard as CG

ROOT = Path(__file__).resolve().parents[1]
P18 = ROOT / "audits/predictive-intelligence/phase_18"
REAL = P18 / "real"


def _j(p):
    return json.loads(p.read_text())


def test_the_flag_off_scout_is_byte_identical_at_the_frozen_commit_and_the_on_body_only_gains_the_phase17_section():
    d = _j(REAL / "REAL_PATH_SMOKE.json")
    assert set(d["exit_codes"].values()) == {0} and len(d["exit_codes"]) == 16
    assert d["base_vs_frozen_off_all_reports_byte_equal"] is True and d["reports_compared"] == 9
    assert d["frozen_on_scout_is_base_plus_appended_section"] is True and d["lab_tables_equal_base_off_frozen_off_frozen_on"] is True
    assert d["section_abstain_lines"] == 24 and d["section_forecast_lines"] == 0
    # the checkout during the recorded run: no tracked change; the one untracked file is this test, written while the runs went on
    assert all(x.startswith("?? ") for x in d["checkout_status"]) and d["sandbox_final_tracked_changes"] == []


def test_the_real_scout_report_shows_every_target_abstaining_with_its_reasons_and_no_number():
    c = _j(REAL / "REAL_RUN_CHECKS.json")["scout_report"]
    assert c["state"] == "OK" and c["format_only"] is False
    assert c["counts"]["opportunities"] == 8 and c["counts"]["targets"] == 24 and c["counts"]["probabilities_shown"] == 0
    assert c["statuses"] == {"ABSTAIN": 24} and c["counts"]["refused"] == 0 and c["counts"]["overridden"] == 0
    assert c["counts"]["with_risk"] == c["counts"]["vetoes"] == 3
    assert c["reason_counts"]["MODEL_NOT_SELECTED"] == 24 and c["reason_counts"]["UNCALIBRATED"] == 24
    assert c["input_states"] == {"INPUT_STALE": 8} and c["lab_states"] == {"SNAPSHOT_VERIFIED": 8}
    assert c["backtest_results"] == ["BACKTEST_NOT_AVAILABLE"] and c["simulation_lines"] >= 10
    assert c["percent_or_fraction_outside_definitions"] == 0 and c["local_path"] is False and c["trading_word"] is False
    text = (REAL / "REAL_SCOUT_REPORT.md").read_text()
    import hashlib
    assert hashlib.sha256(text.encode()).hexdigest() == c["sha256"]
    mints = re.findall(r"`solana:([1-9A-HJ-NP-Za-km-z]{32,44})`", text)
    RP.check_text(text, mints)
    assert not re.search(r"FORECAST \d", text) and "FORMAT-ONLY" not in text and "ABSTAIN (no number)" in text


def test_the_real_replay_report_has_no_number():
    c = _j(REAL / "REAL_RUN_CHECKS.json")["replay_report"]
    assert c["state"] == "OK" and c["counts"]["probabilities_shown"] == 0 and set(c["statuses"]) == {"ABSTAIN"}
    assert c["measured_change_percents"] == 1             # the labelled event line of one MATERIAL_CHANGE (CP18-1, PI-D-100)
    assert c["percent_or_fraction_outside_definitions"] == 0 and c["local_path"] is False and c["trading_word"] is False


def test_the_real_alerts_are_dry_run_only_and_never_for_an_abstention():
    d = _j(REAL / "REAL_RUN_CHECKS.json")
    for k in ("scout_alerts", "replay_alerts"):
        a = d[k]
        assert a["remote_deliveries_succeeded"] == 0 and a["sent_folder_exists"] is False
        assert set(a["alert_policies"]) <= {"risk_override", "pipeline_health"} and a["new"] <= 8
        assert set(a["ledger"]) <= {"file:dry_run_preview"} and a["previews"] == a["new"]
    assert d["scout_alerts"]["new"] == 0 and d["socket_events"] == 0


def test_the_mutation_probe_caught_every_mutation():
    m = _j(P18 / "evidence/mutation_reports.json")
    assert m["mutations"] >= 45 and m["survivors"] == [] and m["caught"] == m["mutations"]


def test_the_ledger_adds_rows_but_no_configuration():
    t = _j(P18 / "experiments/LEDGER_TOTALS.json")
    assert t["after"]["n_search"] == t["before"]["n_search"] == 130
    assert t["after"]["n_search_sensitivity"] == 169 and t["added_rows"] == 28 and t["claim"] == "REPORT_RUN_NOT_A_CONFIGURATION"


def test_every_phase18_json_passes_the_content_guard():
    paths = [str(p.relative_to(ROOT)) for p in P18.rglob("*.json")]
    assert paths
    rep = CG.scan(ROOT, paths)
    assert rep.get("violations") in ([], None) and not rep.get("violation_count"), rep
