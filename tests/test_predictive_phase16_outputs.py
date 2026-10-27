"""Phase 16 committed outputs: the registry, the pins, the ensemble decision and today's documents say exactly what the evidence
allows (no champion, references never published). Reads committed files only; no network, no store."""
from __future__ import annotations

import csv
import json
import math
import subprocess
from collections import Counter
from pathlib import Path

import pytest

from memelab.predictive import abstention as AB
from memelab.predictive import baselines as B
from memelab.predictive import calibration as CAL
from memelab.predictive import contract as C
from memelab.predictive import evaluation as E
from memelab.predictive import registry as R

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / "audits/predictive-intelligence"
P16 = AUD / "phase_16"
REG = P16 / "registry"
SHORT = {"price_path_target_before_invalidation_24h": "T1_24h", "price_path_target_before_invalidation_6h": "T1b_6h",
         "price_path_severe_drawdown_or_halt_24h": "T2_24h"}


@pytest.fixture(scope="module")
def entries():
    return R.read_entries(REG / "entries")


@pytest.fixture(scope="module")
def events():
    return R.read_log((REG / "REGISTRY_LOG.jsonl").read_text())


def test_sixty_nine_immutable_entries_one_per_frozen_card_with_their_cards_and_calibration(entries):
    cand = json.loads((AUD / "phase_12/validation/CANDIDATES.json").read_text())
    assert len(entries) == 69
    by = {(SHORT[e["target"]], e["family"]["candidate"]): e for e in entries.values()}
    for c in cand["candidates"]:
        e = by[(c["target_short"], c["candidate"])]
        b = (ROOT / c["path"]).read_bytes()
        cal = None
        if c["candidate"] == "P07_B2":
            cal = json.loads((ROOT / e["calibration"]["path"]).read_text())
            CAL.verify_card(cal)
        R.verify_entry(e, card=json.loads(b), card_bytes=b, cal_card=cal)
        assert e["model_sha"] == c["model_sha"] and e["card_file_sha256"] == c["file_sha256"]
        assert e["target_registry_sha"] == C.registry_sha256() and not e["is_fixture"]


def test_levels_are_abstain_for_the_references_and_no_go_for_everything_else_and_nothing_is_publishable(entries):
    lv = Counter((e["family"]["candidate"] in ("P07_B0", "P07_B2"), e["promotion"]["level"]) for e in entries.values())
    assert lv == Counter({(True, "ABSTAIN"): 6, (False, "NO_GO"): 63})
    assert not any(e["publishable"] for e in entries.values())
    assert all(R.promotion_decision(e["facts"]) == e["promotion"] for e in entries.values())
    assert all("NO_INCREMENTAL_PREDICTIVE_EDGE" in e["promotion"]["reasons"] for e in entries.values() if e["promotion"]["level"] == "NO_GO")


def test_cx16_t2_b2_has_a_positive_point_but_stays_an_abstain_reference(entries):
    b2 = [e for e in entries.values() if e["target"] == "price_path_severe_drawdown_or_halt_24h" and e["family"]["kind"] == "B2"
          and e["family"]["phase"] == "07"][0]
    ret = b2["facts"]["retrospective"]
    assert ret["evaluation"] == R.FIRST_OPENING and ret["bss"] > 0.25 and ret["k"] == 7
    assert b2["promotion"]["level"] == "ABSTAIN" and "RETROSPECTIVE_BELOW_MINIMUM" in b2["promotion"]["reasons"]
    assert b2["calibration"]["status"] == "UNCALIBRATED" and b2["registry_status"] == "REFERENCE_ONLY_NEVER_PUBLISHED"


def test_every_target_is_pinned_no_viable_champion_with_its_own_references(entries, events):
    pins = [e for e in events if e["kind"] == "PIN"]
    assert len(pins) == 3 and not any(e["kind"] == "ROLLBACK" for e in events)
    assert {p["target"] for p in pins} == set(SHORT)
    for p in pins:
        assert p["mode"] == "NO_VIABLE_CHAMPION" and p["champion"] is None and p["champion_inference_sha"] is None
        for name, eid in p["references"].items():
            e = entries[eid]
            assert e["target"] == p["target"] and e["role"] == "REFERENCE_BASELINE" and R.REFERENCE_NAMES[e["family"]["kind"]] == name
        assert "PHASE_12_CHAMPION_B2_BY_DEFAULT_NOT_BY_EVIDENCE" in p["reasons"] and "NO_ENTRY_AT_SHADOW_OR_ABOVE" in p["reasons"]
    reg = {e["entry_id"] for e in events if e["kind"] == "REGISTER"}
    assert reg == set(entries)
    dec = [e for e in events if e["kind"] == "ENSEMBLE_DECISION"]
    assert len(dec) == 3 and all(d["decision"] == "NO_ENSEMBLE" and d["configuration"] is None for d in dec)
    idx = json.loads((REG / "REGISTRY_INDEX.json").read_text())
    assert idx["publishable"] == 0 and idx["log_sha256"] == R.file_sha(REG / "REGISTRY_LOG.jsonl")
    assert all(v["mode"] == "NO_VIABLE_CHAMPION" and v["champion"] is None for v in idx["targets"].values())
    assert "No champion" in idx["statement"] and "not forecasts" in idx["statement"]


def test_identical_inference_reproduced_every_recorded_prediction_and_the_synthetic_hashes_recompute(entries):
    inf = json.loads((P16 / "evidence/INFERENCE_CHECK.json").read_text())
    assert inf["cards"] == 69 and inf["equal_to_recorded"] == 69 and inf["differences"] == {}
    assert all(e["inference"]["equal_to_recorded"] and e["inference"]["recorded_predictions_sha256"] ==
               R.sha_bytes((AUD / "phase_12/validation/HOLDOUT_PREDICTIONS.csv").read_bytes()) for e in entries.values())
    d = json.loads((ROOT / "tests/fixtures/predictive/registry_probe_examples.json").read_text())
    ex = [B.Example(decision_key=r["decision_key"], chain=r["chain"], mint=r["mint"], decision_time=r["decision_time"],
                    label_matures_at=r["decision_time"] + 86400.0, y=-1,
                    x={k: (float("nan") if v is None else float(v)) for k, v in r["x"].items()}, avail=r["avail"], status=r["status"])
          for r in d["rows"]]
    n = 0
    for e in entries.values():
        if e["family"]["phase"] != "07":
            assert "synthetic_outputs_sha" not in e["inference"]
            continue
        card = B.loads((ROOT / e["card_path"]).read_text())
        p, w = B.predict(card, ex)
        R.check_inference(e, [(x.decision_key, float(v) if math.isfinite(v) else None, ww or "") for x, v, ww in zip(ex, p, w)],
                          which="synthetic_outputs_sha")
        n += 1
    assert n == 18


def test_today_every_document_abstains_with_model_not_selected_and_validates_with_its_record():
    docs = [json.loads(x) for x in (REG / "TODAY_RESULTS.jsonl").read_text().splitlines()]
    recs = [json.loads(x) for x in (REG / "TODAY_RECORDS.jsonl").read_text().splitlines()]
    assert len(docs) == len(recs) == 30
    for d, r in zip(docs, recs):
        assert d["prediction_status"] == "ABSTAIN" and d["probability"] is None and d["model_id"] == R.NOT_SELECTED
        assert d["base_rate"] is None and "MODEL_NOT_SELECTED" in d["abstain_reasons"] and d["behavioral_scenarios"] == []
        assert AB.validate_publication(d, model_card=None, calibration_card=None, record=r, backtest=d["backtest_status"]) == []
    st = json.loads((REG / "TODAY_STATUS.json").read_text())
    assert st["failures"] == [] and "No probability is published" in st["statement"]
    for s, v in st["targets"].items():
        assert v["mode"] == "NO_VIABLE_CHAMPION" and v["champion"] is None
        for ref in v["references"].values():
            assert ref["published"] is False and R.MODEL_STALE not in ref["states_today"]
            assert R.MODEL_STALE not in ref["states_at_2026-10-31T00:00:00Z"]
            assert R.MODEL_STALE in ref["states_at_2026-10-31T00:00:01Z"] and ref["stale_after_utc"] == "2026-10-31T00:00:00Z"
    plan = {p["target"]: p for p in st["target_plan_example"]["plan"]}
    assert all(p["reasons"] == ["TARGET_NOT_FEASIBLE"] for t, p in plan.items() if C.TARGETS[t]["status"] != "PRIMARY")
    assert all(p["forecast_inputs"]["card_entry"] is None for t, p in plan.items() if C.TARGETS[t]["status"] == "PRIMARY")


def test_the_ensemble_ablation_refused_the_traps_gave_no_verdict_and_decided_no_ensemble():
    ab = json.loads((P16 / "ensemble/ENSEMBLE_ABLATION.json").read_text())
    assert ab["ensemble_decision"] == {"T1_24h": "NO_ENSEMBLE", "T1b_6h": "NO_ENSEMBLE", "T2_24h": "NO_ENSEMBLE"}
    for s, v in ab["targets"].items():
        assert all(t["refused"] for t in v["traps"].values()) and len(v["traps"]) == 3
        assert v["development"]["STACK_CHRONO_B2_S1"]["fitted_folds"] == 0
        for cfg in ("ENS_MEAN_B0_B2", "ENS_MEAN_B2_S1"):
            for ref in ("vs_B0", "vs_B2"):
                assert v["development"][cfg][ref]["verdict"] in ("INSUFFICIENT_DAYS", "INSUFFICIENT_EVENTS", "INSUFFICIENT_HISTORY")
                assert v["post_opening"][cfg][ref]["claim"] == "NOT_A_CLAIM_POST_OPENING"
    rows = list(csv.DictReader(open(P16 / "ensemble/ENSEMBLE_ABLATION.csv")))
    assert all(r["claim"] in ("NO_CLAIM", "NOT_A_CLAIM_POST_OPENING") for r in rows)
    log = json.loads((P16 / "ensemble/POST_OPENING_LOG.json").read_text())
    assert log and all(x["label"] == "POST_OPENING" and x["sealed_folder_read"] is False for x in log)


def test_compatibility_rollback_and_the_run_log():
    comp = json.loads((P16 / "evidence/COMPATIBILITY_P46.json").read_text())
    assert comp["real_runtime_incompatible_entries"] == 0
    assert comp["phase07_feature_definitions_changed"] == {"affected": 18, "phase07_entries": 18}
    assert comp["feature_version_bumped"] == {"affected": 69, "entries": 69}
    assert comp["request_with_another_feature_set"]["affected"] == 69 and comp["target_registry_changed"]["affected"] == 69
    rb = json.loads((P16 / "evidence/ROLLBACK_TEST.json").read_text())
    assert rb["fixture"]["status"] == "TEST_ONLY" and rb["fixture"]["history_preserved"]
    assert rb["fixture"]["after_drift_rollback"]["champion_model"].startswith("B2:")
    assert rb["fixture"]["after_inference_mismatch_rollback"]["mode"] == "NO_VIABLE_CHAMPION"
    assert all(rb["real_log_copy"][s]["mode_after"] == "NO_VIABLE_CHAMPION" for s in SHORT.values())
    run = json.loads((P16 / "evidence/run_log.json").read_text())
    assert run["failures"] == [] and run["stores_unchanged"] and run["sealed_folder_unchanged"] and run["network_calls"] == 0
    assert run["llm_calls"] == 0 and run["firecrawl_credits"] == 0


def test_the_search_ledger_extends_phase_15_and_counts_the_ensembles():
    base = list(csv.DictReader(open(AUD / "phase_15/experiments/SEARCH_LEDGER.csv"))) + \
        list(csv.DictReader(open(AUD / "phase_15/experiments/SEARCH_LEDGER_RP2_ADDITION.csv")))
    led = list(csv.DictReader(open(P16 / "experiments/SEARCH_LEDGER.csv")))
    assert led[:len(base)] == base
    tot = E.ledger_totals(led)
    assert tot["n_search"] == 130 and tot["n_search"] + E.rule_configurations(led) == 169
    new = led[len(base):]
    assert Counter(r["kind"] for r in new) == Counter({"ABLATION": 9, "TRAP_OR_CHECK": 9, "POST_OPENING_CHECK": 6, "DEBUG_RUN_REAL_DATA": 4})
    reg = [r["experiment_id"] for r in csv.DictReader(open(P16 / "experiments/EXPERIMENT_REGISTRY.csv"))]
    ids = {r["experiment_id"] for r in new}
    for x in reg:
        if any(k in x for k in ("ENS_MEAN", "STACK_", "TRAP_")):
            assert x in ids or x.replace("POST_OPENING_ENS_MEANS", "POST_OPENING_ENS_MEAN_B0_B2") in ids, x


def test_pre_registration_was_committed_before_the_registry_code():
    def first(path):
        out = subprocess.run(["git", "-C", str(ROOT), "log", "--reverse", "--format=%H", "--", path], capture_output=True, text=True)
        lines = out.stdout.split()
        assert out.returncode == 0 and lines, f"no history for {path} (a shallow or exported tree cannot prove the order)"
        return lines[0]
    pre = first("audits/predictive-intelligence/phase_16/ACCEPTANCE_CHECKLIST.md")
    code = first("memelab/predictive/registry.py")
    assert pre != code
    r = subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", pre, code])
    assert r.returncode == 0


def test_cp16_0_every_entry_s_facts_rebuild_from_the_committed_files_and_every_source_hash_holds(entries):
    import csv as _csv
    m = {(r["target_short"], r["model"], r["reference"]): r for r in _csv.DictReader(open(AUD / "phase_12/validation/HOLDOUT_METRICS.csv"))}
    post = {}
    for r in _csv.DictReader(open(AUD / "phase_12/validation/POST_OPENING_CORRECTIONS.csv")):
        post.setdefault((r["target_short"], r["model"]), {})[r["reference"]] = r["selection_status_final"]
    for e in entries.values():
        s = SHORT[e["target"]]
        cid = e["family"]["candidate"]
        card = json.loads((ROOT / e["card_path"]).read_text())
        cal = json.loads((ROOT / e["calibration"]["path"]).read_text()) if e["calibration"] else None
        R.verify_facts(e, card=card, tests=e["facts"]["tests"], m_b0=m.get((s, cid, "P07_B0")), m_b2=m.get((s, cid, "P07_B2")),
                       post_states=post.get((s, cid), {}), cal_card=cal)
        assert e["facts"]["tests"]["leakage"] and e["facts"]["tests"]["provenance"] and e["facts"]["tests"]["contract"]
        assert len(R.verify_sources(e, lambda p: (ROOT / p).read_bytes())) >= 4
