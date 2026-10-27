"""Phase 16: registry-1 and the champion policy (memelab/predictive/registry.py). No network, no clock, fixtures only; the real
cards are read from the committed artifacts and never changed. Pre-registration:
audits/predictive-intelligence/phase_16/ACCEPTANCE_CHECKLIST.md."""
from __future__ import annotations

import ast
import copy
import json
import math
from pathlib import Path

import numpy as np
import pytest

from memelab.predictive import abstention as AB
from memelab.predictive import baselines as B
from memelab.predictive import calibration as CAL
from memelab.predictive import contract as C
from memelab.predictive import evaluation as E
from memelab.predictive import features as F
from memelab.predictive import registry as R

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "audits/predictive-intelligence"
FX_TARGET = "price_path_target_before_invalidation_24h"
FX_SHORT = "T1_24h"
AS_OF = "2026-10-27T00:00:00Z"
CUT = C.parse_utc("2026-10-17T00:00:00Z")


BASE_CODE = ["memelab/predictive/features.py", "memelab/predictive/baselines.py", "memelab/predictive/stats.py",
             "memelab/predictive/contract.py", "memelab/predictive/labels.py"]


def code_for(phase: str) -> dict:
    extra = {"07": [], "08": ["memelab/predictive/technical.py"], "09": ["memelab/predictive/onchain.py"]}[phase]
    return R.code_of(BASE_CODE + extra, ROOT)


# ---------------------------------------------------------------- fixture builders (also used by the recorded run's rollback test)
def real_card(phase: str, kind: str, short: str = FX_SHORT) -> dict:
    return json.loads((ART / f"phase_{phase}/artifacts/{short}/{kind}.json").read_text())


def fixture_card(phase: str, kind: str, short: str = FX_SHORT) -> dict:
    c = copy.deepcopy(real_card(phase, kind, short))
    c["evidence_class"] = "FIXTURE_REGISTRY_1"
    c["model_sha"] = R.card_sha_of(c)
    return c


def facts(kind: str, *, role: str | None = None, level: str = "NONE", fitted: bool = True, **over) -> dict:
    role = role or R.role_of("07" if kind in ("B0", "B1", "B2", "B3", "B3F", "B4") else "09", kind)
    f = {"role": role, "kind": kind, "model_id": f"{kind}:{FX_TARGET}", "source": R.SOURCE, "fitted": fitted,
         "tests": {"leakage": True, "provenance": True, "contract": True}, "training": {"n": 136, "k": 34},
         "retrospective": {"evaluation": None}, "post_opening_states": [], "selection_status": "NO_UNCORRECTED_SKILL",
         "vs_b2": None, "calibration": {"status": None}, "prospective": {"status": "NOT_YET_MATURED"}}
    if level in ("SHADOW", "VALIDATED_EXPERIMENTAL"):
        f["retrospective"] = {"evaluation": R.FIRST_OPENING, "n": 66, "k": 15, "calibration_in_the_large_ok": True,
                              "calibration_every_bin_ok": True, "bss": 0.05, "bss_lo": -0.02, "p_holm": 0.3}
        f["calibration"] = {"status": "CALIBRATED", "evidence_n": 60, "evidence_k": 12, "evidence_source": "PROSPECTIVE_HOLDOUT"}
    if level == "VALIDATED_EXPERIMENTAL":
        f["retrospective"].update({"bss_lo": 0.01, "p_holm": 0.01})
        f["prospective"] = {"status": "ADMISSIBLE", "n": 60, "k": 12, "bss_lo": 0.02, "p_holm": 0.01}
        f["selection_status"] = R.SELECTION_SURVIVES
        if kind != "B2":
            f["vs_b2"] = {"brier_minus_b2": -0.01, "lower_bound_b2_minus_brier": 0.004}
    f.update(over)
    return f


def inf_for(card: dict, phase: str) -> dict:
    rows = [(f"fx-{i}", 0.2 + 0.01 * i, "") for i in range(5)]
    return {"probe_set": "fixture", "probe_set_sha": "0" * 64, "rows": 5, "numbers": 5, "abstentions": {},
            "outputs_sha": R.inference_hash(rows), "recorded_predictions_file": None, "recorded_predictions_sha256": None,
            "equal_to_recorded": True, "differences": 0}


def make(phase: str, kind: str, f: dict, *, fixture: bool = True, calibration: dict | None = None, card: dict | None = None,
         target: str = FX_TARGET) -> dict:
    card = card or (fixture_card(phase, kind) if fixture else real_card(phase, kind))
    lvl = R.promotion_decision(f)["level"]
    if calibration is None and lvl in R.PUBLISHABLE_LEVELS:
        calibration = {"path": "fixture", "card_sha": "a" * 64, "file_sha256": "b" * 64, "status": "CALIBRATED", "level": lvl,
                       "details": []}
    mv = R.PHASE07_FAMILY_VERSION if phase == "07" else card[{"08": "tech_version", "09": "onchain_version"}[phase]]
    return R.make_entry(target=target, family={"phase": phase, "kind": kind, "candidate": f"P{phase}_{kind}", "module_version": mv},
                        card=card,
                        card_path=f"fixture/{kind}.json", card_file_sha256="c" * 64, calibration=calibration, facts=f,
                        evidence={"fixture": True}, risk_flags=["FIXTURE"], inference=inf_for(card, phase),
                        registered_as_of_utc=AS_OF, is_fixture=fixture, code=code_for(phase))


def fixture_registry() -> tuple[dict, dict]:
    """A fixture B0 reference, a fixture B2 at SHADOW (the baseline champion) and a fixture model at VALIDATED_EXPERIMENTAL.
    Initial events: register all three, pin the B2 baseline at t1, pin the model at t2. Used by the rollback test here and by
    the recorded run (evidence/ROLLBACK_TEST.json)."""
    b0 = make("07", "B0", facts("B0"))
    b2 = make("07", "B2", facts("B2", level="SHADOW"))
    m = make("09", "M2_OC_LOGIT_B2", facts("M2_OC_LOGIT_B2", level="VALIDATED_EXPERIMENTAL"))
    ents = {e["entry_id"]: e for e in (b0, b2, m)}
    refs = {"base_rate": b0["entry_id"], "simple_model": b2["entry_id"]}
    t1, t2 = "2026-10-20T00:00:00Z", "2026-10-22T00:00:00Z"
    initial = [R.register_event(e, as_of_utc=t1) for e in (b0, b2, m)]
    initial.append(R.pin_event(ents, FX_TARGET, mode="CHAMPION", champion=b2["entry_id"], references=refs,
                               reasons=["FIXTURE_BASELINE_CHAMPION"], as_of_utc=t1, allow_fixture=True))
    initial.append(R.pin_event(ents, FX_TARGET, mode="CHAMPION", champion=m["entry_id"], references=refs,
                               reasons=["FIXTURE_MODEL_CHAMPION"], as_of_utc=t2, allow_fixture=True))
    return ents, {"initial": initial, "t_baseline_pin": t1, "t_model_pin": t2, "t_drift": "2026-10-24T00:00:00Z",
                  "t_mismatch": "2026-10-25T00:00:00Z", "b0": b0["entry_id"], "b2": b2["entry_id"], "model": m["entry_id"]}


def runtime() -> dict:
    from memelab.predictive import analog as A
    from memelab.predictive import labels as L
    from memelab.predictive import onchain as O
    from memelab.predictive import socialcat as SC
    from memelab.predictive import technical as T8
    return {"feature_set_sha": {"07": F.feature_set_sha(), "08": T8.feature_set_sha(), "09": O.feature_set_sha(),
                                "10": SC.feature_set_sha(), "11": A.feature_set_sha()}, "feature_version": F.FEATURE_VERSION,
            "family_version": {"07": R.PHASE07_FAMILY_VERSION, "08": T8.TECH_VERSION, "09": O.ONCHAIN_VERSION,
                               "10": SC.SOCIALCAT_VERSION, "11": A.ANALOG_VERSION},
            "registry_sha": C.registry_sha256(), "labels_version": L.LABELS_VERSION}


def _imports(p: Path) -> set[str]:
    out = set()
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n, ast.Import):
            out.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            out.add(("." * n.level) + (n.module or ""))
    return out


# ---------------------------------------------------------------- isolation (G26)
def test_registry_imports_numpy_stdlib_contract_and_stats_only():
    p = ROOT / "memelab/predictive/registry.py"
    std = {"__future__", "csv", "hashlib", "io", "json", "math", "pathlib", "re", "typing", "datetime"}
    got = _imports(p)
    assert got <= std | {"numpy", "."}, got
    txt = p.read_text()
    for banned in ("socialcat", "depth_adapter", "predictive.analog", "predictive.evaluation", "predictive.calibration",
                   "predictive.abstention", "holdout_labels.jsonl", "phase_06/sealed", "phase_04/adoption/data", "sklearn",
                   "import pickle"):
        assert banned not in txt, banned
    tree = ast.parse(txt)
    rel = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level == 1 for a in n.names}
    assert rel <= {"contract", "stats"}, rel


def test_no_other_module_imports_the_registry():
    for p in (ROOT / "memelab").rglob("*.py"):
        if p.name == "registry.py" and p.parent.name == "predictive":
            continue
        if p.name == "integration.py" and p.parent.name == "predictive":       # Phase 17 seam (PI-D-093 item 7): the one allowed importer
            assert "from . import registry as R" in p.read_text()
            continue
        imps = _imports(p)
        assert not any(i.endswith("predictive.registry") or i == "..predictive.registry" for i in imps), p
        if p.parent.name == "predictive":                    # memelab/social has a registry of its own; only this package matters
            assert ".registry" not in imps and "from . import registry" not in p.read_text(), p
            assert "predictive.registry" not in p.read_text(), p


def test_the_registry_seam_names_only_the_integration_module():
    allowed = [p for p in (ROOT / "memelab").rglob("*.py") if p.parent.name == "predictive" and p.name not in ("registry.py",)
               and ("from . import registry" in p.read_text() or ".registry import" in p.read_text())]
    assert [p.name for p in allowed] == ["integration.py"]
    # CP17-1 (skeptic m4): relative imports read from the AST, so `from . import stats, registry` is seen too
    users = []
    for p in (ROOT / "memelab/predictive").glob("*.py"):
        tree = ast.parse(p.read_text())
        if any(isinstance(n, ast.ImportFrom) and n.level == 1 and ((n.module or "") == "registry" or any(a.name == "registry" for a in n.names))
               for n in ast.walk(tree)):
            users.append(p.name)
    assert users == ["integration.py"]


# ---------------------------------------------------------------- promotion (G7, CX-16, P22, P24)
def test_a_reference_baseline_without_evidence_is_abstain_and_a_candidate_is_no_go():
    assert R.promotion_decision(facts("B2"))["level"] == "ABSTAIN"
    assert R.promotion_decision(facts("B0"))["level"] == "ABSTAIN"
    got = R.promotion_decision(facts("M2_OC_LOGIT_B2"))
    assert got["level"] == "NO_GO" and "NO_INCREMENTAL_PREDICTIVE_EDGE" in got["reasons"]


def test_cx16_a_positive_t2_point_on_seven_positives_and_no_calibration_stays_abstain():
    f = facts("B2", retrospective={"evaluation": R.FIRST_OPENING, "n": 59, "k": 7, "calibration_in_the_large_ok": True,
                                   "calibration_every_bin_ok": True, "bss": 0.2925, "bss_lo": -0.0258, "p_holm": 0.1003})
    got = R.promotion_decision(f)
    assert got["level"] == "ABSTAIN"
    assert "RETROSPECTIVE_BELOW_MINIMUM" in got["reasons"] and "NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION" in got["reasons"]


def test_cx16_a_forged_champion_level_is_refused_everywhere():
    e = make("07", "B2", facts("B2"), fixture=False)
    assert e["promotion"]["level"] == "ABSTAIN"
    forged = copy.deepcopy(e)
    forged["promotion"] = {**forged["promotion"], "level": "SHADOW", "reasons": [], "shadow_reached": True}
    forged["registry_status"] = "PROMOTED_SHADOW"
    forged["entry_id"] = R.sha({k: v for k, v in forged.items() if k != "entry_id"})
    with pytest.raises(R.LevelMismatch):
        R.verify_entry(forged)
    b0 = make("07", "B0", facts("B0"), fixture=False)
    ents = {x["entry_id"]: x for x in (e, b0)}
    refs = {"base_rate": b0["entry_id"], "simple_model": e["entry_id"]}
    with pytest.raises(R.PinRefused, match="SHADOW or VALIDATED_EXPERIMENTAL"):
        R.pin_event(ents, FX_TARGET, mode="CHAMPION", champion=e["entry_id"], references=refs, reasons=[], as_of_utc=AS_OF)
    # a hand-written CHAMPION pin of an ABSTAIN entry in a log is refused when resolved
    bad = {"kind": "PIN", "as_of_utc": AS_OF, "target": FX_TARGET, "mode": "CHAMPION", "champion": e["entry_id"],
           "champion_inference_sha": e["inference"]["outputs_sha"], "references": refs, "reasons": ["forged"]}
    events = R.chain_events([bad])
    with pytest.raises(R.PinRefused):
        R.resolve(events, ents, FX_TARGET, C.parse_utc(AS_OF) + 1)


def test_shadow_needs_every_criterion_and_prospective_calibration():
    assert R.promotion_decision(facts("B2", level="SHADOW"))["level"] == "SHADOW"
    for path, val, reason in ((("calibration",), {"status": "UNCALIBRATED"}, "NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION"),
                              (("tests",), {"leakage": True, "provenance": False, "contract": True}, "TESTS_NOT_PASSED"),
                              (("training",), {"n": 99, "k": 34}, "TRAINING_BELOW_MINIMUM"),
                              (("training",), {"n": 136, "k": 19}, "TRAINING_BELOW_MINIMUM")):
        f = facts("B2", level="SHADOW", **{path[0]: val})
        got = R.promotion_decision(f)
        assert got["level"] == "ABSTAIN" and reason in got["reasons"], (path, got)
    f = facts("B2", level="SHADOW")
    f["retrospective"]["bss"] = -0.0001
    assert "RETROSPECTIVE_BSS_BELOW_0" in R.promotion_decision(f)["reasons"]
    f["retrospective"]["bss"] = 0.0
    assert R.promotion_decision(f)["level"] == "SHADOW"                 # the frozen bound is "at least 0"
    f = facts("B2", level="SHADOW")
    f["retrospective"]["calibration_in_the_large_ok"] = False
    assert "RETROSPECTIVE_CALIBRATION_FAILED" in R.promotion_decision(f)["reasons"]
    f = facts("B2", level="SHADOW")
    f["retrospective"]["calibration_every_bin_ok"] = False
    assert "RETROSPECTIVE_CALIBRATION_FAILED" in R.promotion_decision(f)["reasons"]


def test_holdout_and_calibration_count_boundaries():
    for n, k, ok in ((50, 10, True), (49, 10, False), (50, 9, False), (50, 41, False), (50, 40, True)):
        f = facts("B2", level="SHADOW")
        f["retrospective"].update({"n": n, "k": k})
        assert (R.promotion_decision(f)["level"] == "SHADOW") is ok, (n, k)
    for n, k, ok in ((50, 10, True), (49, 10, False), (50, 9, False), (30, 10, False)):
        f = facts("B2", level="SHADOW")
        f["calibration"].update({"evidence_n": n, "evidence_k": k})
        assert (R.promotion_decision(f)["level"] == "SHADOW") is ok, (n, k)
    f = facts("B2", level="SHADOW")
    f["calibration"]["evidence_source"] = "RETROSPECTIVE_HOLDOUT"          # the spent holdout is never evidence
    assert R.promotion_decision(f)["level"] == "ABSTAIN"


def test_p24_a_small_calibration_set_cannot_reach_shadow_and_the_document_abstains():
    f = facts("B2", level="SHADOW")
    f["calibration"].update({"evidence_n": 30, "evidence_k": 2})
    got = R.promotion_decision(f)
    assert got["level"] == "ABSTAIN" and "NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION" in got["reasons"]
    e = make("07", "B2", f)
    assert not e["publishable"]
    ev = AB.evaluate(_req(), card=None, level=e["promotion"]["level"], cal_card=None, raw=0.95)
    assert ev["point"] is None and {c["code"] for c in ev["conditions"]} >= {"MODEL_NOT_PROMOTED", "NO_CHAMPION", "NO_CALIBRATOR"}


def test_post_opening_evaluations_cannot_promote_and_a_post_opening_failure_blocks():
    f = facts("B2", level="SHADOW")
    f["retrospective"]["evaluation"] = "POST_OPENING"
    got = R.promotion_decision(f)
    assert got["level"] == "ABSTAIN" and "RETROSPECTIVE_EVALUATION_POST_OPENING_CANNOT_PROMOTE" in got["reasons"]
    f = facts("B2", level="SHADOW", post_opening_states=["FAILS_SELECTION_CORRECTION"])
    assert "POST_OPENING_FAILS" in R.promotion_decision(f)["reasons"]


def test_validated_experimental_needs_both_holdouts_b2_and_the_selection_correction():
    assert R.promotion_decision(facts("M2_OC_LOGIT_B2", level="VALIDATED_EXPERIMENTAL"))["level"] == "VALIDATED_EXPERIMENTAL"
    assert R.promotion_decision(facts("B2", level="VALIDATED_EXPERIMENTAL"))["level"] == "VALIDATED_EXPERIMENTAL"
    cases = [("prospective", {"status": "NOT_YET_MATURED"}, "PROSPECTIVE_BELOW_MINIMUM"),
             ("prospective", {"status": "ADMISSIBLE", "n": 49, "k": 12, "bss_lo": 0.02, "p_holm": 0.01}, "PROSPECTIVE_BELOW_MINIMUM"),
             ("prospective", {"status": "ADMISSIBLE", "n": 60, "k": 12, "bss_lo": 0.0, "p_holm": 0.01}, "PROSPECTIVE_LOWER_BOUND_NOT_ABOVE_0"),
             ("prospective", {"status": "ADMISSIBLE", "n": 60, "k": 12, "bss_lo": 0.02, "p_holm": 0.05}, "PROSPECTIVE_LOWER_BOUND_NOT_ABOVE_0"),
             ("selection_status", "FAILS_SELECTION_CORRECTION", "SELECTION_CORRECTION_NOT_SURVIVED"),
             ("selection_status", "CORRECTION_NOT_COMPUTED", "SELECTION_CORRECTION_NOT_SURVIVED"),
             ("vs_b2", {"brier_minus_b2": 0.001, "lower_bound_b2_minus_brier": 0.004}, "WORSE_THAN_B2"),
             ("vs_b2", {"brier_minus_b2": -0.01, "lower_bound_b2_minus_brier": 0.0}, "NOT_BETTER_THAN_B2"),
             ("vs_b2", None, "NOT_BETTER_THAN_B2")]
    for key, val, reason in cases:
        f = facts("M2_OC_LOGIT_B2", level="VALIDATED_EXPERIMENTAL", **{key: val})
        got = R.promotion_decision(f)
        assert got["level"] == "SHADOW" and reason in got["reasons"], (key, val, got)
    f = facts("M2_OC_LOGIT_B2", level="VALIDATED_EXPERIMENTAL")
    f["retrospective"]["bss_lo"] = -0.001
    assert "RETROSPECTIVE_LOWER_BOUND_NOT_ABOVE_0" in R.promotion_decision(f)["reasons"]


def test_p22_a_lucky_winner_of_a_thousand_null_candidates_never_reaches_validated_experimental():
    rng = np.random.default_rng(7)
    n, k = 400, 80
    y = (rng.random(n) < k / n).astype(float)
    best_p, best = 1.0, None
    for c in range(1000):
        p = np.clip(0.2 + rng.normal(0, 0.05, n), 0.01, 0.99)
        bss = K_bss(y, p)
        z = rng.normal()
        pv = 0.5 * math.erfc(z / math.sqrt(2))
        if pv < best_p:
            best_p, best = pv, (c, bss)
    p_bonf = E.bonferroni(best_p, 1000)
    status = E.selection_status(E.HOLDOUT_SKILL, best_p, None, p_bonf)
    assert best_p < 0.05 and status in (E.FAILS, E.NOT_COMPUTED)
    f = facts("M2_OC_LOGIT_B2", level="VALIDATED_EXPERIMENTAL", selection_status=status)
    got = R.promotion_decision(f)
    assert got["level"] != "VALIDATED_EXPERIMENTAL" and "SELECTION_CORRECTION_NOT_SURVIVED" in got["reasons"]


def K_bss(y, p):
    from memelab.predictive import stats as K
    return K.brier_skill(y, p, np.full_like(p, y.mean()))


def test_p27_behavioral_sources_and_simulation_models_are_refused():
    with pytest.raises(R.BehavioralNotAModel):
        R.promotion_decision(facts("B2", source="BEHAVIORAL_SIMULATION"))
    with pytest.raises(R.BehavioralNotAModel):
        R.promotion_decision({**facts("M2_OC_LOGIT_B2"), "kind": "MIROFISH_SWARM", "model_id": "mirofish:x"})
    e = make("07", "B2", facts("B2"))
    bad = copy.deepcopy(e)
    bad["family"]["candidate"] = "P15_agent_vote_share"
    bad["entry_id"] = R.sha({k: v for k, v in bad.items() if k != "entry_id"})
    with pytest.raises(R.BehavioralNotAModel):
        R.verify_entry(bad)
    with pytest.raises(R.BehavioralNotAModel):
        R.check_members({"B2": list(B.B2_COLUMNS), "mirofish_scenarios": []})


# ---------------------------------------------------------------- entries (G9)
def test_entry_id_is_the_content_hash_and_one_changed_byte_refuses_it(tmp_path):
    e = make("07", "B2", facts("B2"), fixture=False)
    assert e["entry_id"] == R.sha({k: v for k, v in e.items() if k != "entry_id"})
    assert not e["publishable"] and e["registry_status"] == "REFERENCE_ONLY_NEVER_PUBLISHED" and e["role"] == "REFERENCE_BASELINE"
    p = R.write_entry(tmp_path, e)
    assert p.name == e["entry_id"] + ".json"
    R.write_entry(tmp_path, e)                                       # same bytes again: fine
    text = p.read_text()
    p.write_text(text.replace('"k_train": 34', '"k_train": 35'))
    with pytest.raises(R.EntryHashMismatch):
        R.read_entries(tmp_path)
    p.write_text(text)
    other = tmp_path / ("f" * 64 + ".json")
    other.write_text(text)
    with pytest.raises(R.EntryHashMismatch, match="file name"):
        R.read_entries(tmp_path)


def test_write_entry_refuses_to_overwrite_an_entry_with_other_content(tmp_path):
    e = make("07", "B2", facts("B2"), fixture=False)
    p = R.write_entry(tmp_path, e)
    p.write_text(p.read_text() + " ")
    with pytest.raises(R.EntryHashMismatch, match="immutable"):
        R.write_entry(tmp_path, e)


def test_verify_entry_checks_the_card_its_bytes_and_its_calibration_card():
    card = real_card("07", "B2")
    bytes_ = (ART / "phase_07/artifacts/T1_24h/B2.json").read_bytes()
    cal = json.loads((ART / "phase_13/artifacts/T1_24h/CALIBRATION_CARD.json").read_text())
    calref = {"path": "x", "card_sha": cal["card_sha"], "file_sha256": "x", "status": cal["status"], "level": cal["level"],
              "details": cal["details"]}
    e = R.make_entry(target=FX_TARGET, family={"phase": "07", "kind": "B2", "candidate": "P07_B2",
                                               "module_version": R.PHASE07_FAMILY_VERSION}, card=card,
                     card_path="audits/predictive-intelligence/phase_07/artifacts/T1_24h/B2.json",
                     card_file_sha256=R.sha_bytes(bytes_), calibration=calref, facts=facts("B2"), evidence={}, risk_flags=[],
                     inference=inf_for(card, "07"), registered_as_of_utc=AS_OF, code=code_for("07"))
    R.verify_entry(e, card=card, card_bytes=bytes_, cal_card=cal)
    bad = copy.deepcopy(card)
    bad["body"]["logistic"]["coef"][0] += 1e-9
    with pytest.raises(R.EntryHashMismatch):
        R.verify_entry(e, card=bad)
    with pytest.raises(R.EntryHashMismatch):
        R.verify_entry(e, card_bytes=bytes_ + b" ")
    other = json.loads((ART / "phase_13/artifacts/T2_24h/CALIBRATION_CARD.json").read_text())
    with pytest.raises(R.RegistryError):
        R.verify_entry(e, cal_card=other)
    tampered = copy.deepcopy(cal)
    tampered["status"] = "CALIBRATED"
    with pytest.raises(R.EntryHashMismatch):
        R.verify_entry(e, cal_card=tampered)


def test_p38_non_finite_facts_and_malformed_inference_outputs_are_refused():
    f = facts("B2")
    f["training"]["n"] = float("nan")
    with pytest.raises(ValueError):
        make("07", "B2", f)
    for rows in ([("a", float("nan"), "")], [("a", None, "")], [("a", float("inf"), "")], [("a", -0.1, "")], [("a", 1.1, "")],
                 [("a", 0.2, ""), ("a", 0.3, "")], [("a", True, "")]):
        with pytest.raises(R.MalformedScore):
            R.inference_rows(rows)
    assert R.inference_rows([("b", 0.5, ""), ("a", None, "OOD")]) == [["a", None, "OOD"], ["b", 0.5, ""]]


# ---------------------------------------------------------------- identical inference (G11)
def test_identical_inference_hash_detects_any_change_of_output():
    e = make("07", "B2", facts("B2"))
    rows = [(f"fx-{i}", 0.2 + 0.01 * i, "") for i in range(5)]
    R.check_inference(e, rows)
    changed = list(rows)
    changed[2] = ("fx-2", 0.2 + 0.01 * 2 + 1e-15, "")
    with pytest.raises(R.InferenceMismatchError):
        R.check_inference(e, changed)
    with pytest.raises(R.InferenceMismatchError):
        R.check_inference(e, rows[:4])
    with pytest.raises(R.InferenceMismatchError):
        R.check_inference(e, rows[:4] + [("fx-4", None, "OOD")])


def test_the_synthetic_probe_hash_is_reproducible_and_moves_with_the_card():
    d = json.loads((ROOT / "tests/fixtures/predictive/registry_probe_examples.json").read_text())
    assert d["is_fixture"] is True and len(d["rows"]) == 16
    ex = [B.Example(decision_key=r["decision_key"], chain=r["chain"], mint=r["mint"], decision_time=r["decision_time"],
                    label_matures_at=r["decision_time"] + 86400.0, y=-1,
                    x={k: (float("nan") if v is None else float(v)) for k, v in r["x"].items()}, avail=r["avail"], status=r["status"])
          for r in d["rows"]]
    card = real_card("07", "B2")

    def h(c):
        p, w = B.predict(c, ex)
        return R.inference_hash([(e.decision_key, float(v) if math.isfinite(v) else None, x or "") for e, v, x in zip(ex, p, w)])
    a = h(card)
    assert a == h(copy.deepcopy(card))
    c2 = copy.deepcopy(card)
    c2["body"]["logistic"]["intercept"] += 1e-6
    assert h(c2) != a


# ---------------------------------------------------------------- the log (G10)
def _log_with(tmp_path, payloads):
    p = tmp_path / "LOG.jsonl"
    sha_, evs = R.append_events(p, payloads, expect_sha=None)
    return p, sha_, evs


def test_the_log_is_chained_and_refuses_changed_dropped_reordered_or_partial_lines(tmp_path):
    ents, steps = fixture_registry()
    p, sha_, evs = _log_with(tmp_path, steps["initial"])
    text = p.read_text()
    assert len(R.read_log(text)) == 5
    lines = text.splitlines(keepends=True)
    changed = text.replace('"FIXTURE_MODEL_CHAMPION"', '"FIXTURE_MODEL_CHAMPION_EDITED"')
    last_spaced = "".join(lines[:-1]) + lines[-1].replace('{"', '{ "', 1)          # only the canonical-form check sees this
    for bad in (changed, "".join(lines[:2] + lines[3:]), "".join([lines[1], lines[0]] + lines[2:]), text[:-1],
                text.replace('{"', '{ "', 1), last_spaced):
        with pytest.raises(R.LogError):
            R.read_log(bad)
    late = R.chain_events([{"kind": "PIN", "as_of_utc": "2026-10-01T00:00:00Z", "target": FX_TARGET, "mode": "NO_VIABLE_CHAMPION",
                            "champion": None, "references": {}, "reasons": []}], prev=R.line_sha(lines[-1].rstrip("\n")), start_seq=5)
    with pytest.raises(R.LogError, match="earlier"):
        R.read_log(text + R.canon(late[0]) + "\n")
    with pytest.raises(R.LogError):
        R.chain_events([{"kind": "EDIT", "as_of_utc": AS_OF}])


def test_append_refuses_a_log_changed_since_the_last_append_and_keeps_earlier_lines(tmp_path):
    ents, steps = fixture_registry()
    p, sha_, _ = _log_with(tmp_path, steps["initial"][:3])
    old = p.read_text()
    sha2, _ = R.append_events(p, steps["initial"][3:], expect_sha=sha_)
    assert R.is_append_only(old, p.read_text())
    with pytest.raises(R.LogError, match="changed"):
        R.append_events(p, steps["initial"][3:4], expect_sha=sha_)
    p.write_text(p.read_text() + "")
    with pytest.raises(R.LogError, match="earlier"):
        R.append_events(p, [{**steps["initial"][3], "as_of_utc": "2026-10-01T00:00:00Z"}], expect_sha=sha2)


def test_resolve_uses_the_pin_in_force_at_the_decision_time():
    ents, steps = fixture_registry()
    events = R.chain_events(steps["initial"])
    assert R.resolve(events, ents, FX_TARGET, C.parse_utc("2026-10-19T00:00:00Z"))["reasons"] == ["NO_PIN"]
    assert R.resolve(events, ents, FX_TARGET, C.parse_utc("2026-10-21T00:00:00Z"))["champion"] == steps["b2"]
    assert R.resolve(events, ents, FX_TARGET, C.parse_utc(steps["t_model_pin"]))["champion"] == steps["model"]
    assert R.resolve(events, ents, "price_path_target_before_invalidation_6h", C.parse_utc("2026-10-23T00:00:00Z"))["reasons"] == ["NO_PIN"]
    with pytest.raises(R.LogError, match="unknown entry"):
        R.resolve(events, {k: v for k, v in ents.items() if k != steps["model"]}, FX_TARGET, C.parse_utc("2026-10-23T00:00:00Z"))


def test_pins_refuse_fixtures_in_a_real_registry_and_references_of_another_kind_or_target():
    ents, steps = fixture_registry()
    refs = {"base_rate": steps["b0"], "simple_model": steps["b2"]}
    with pytest.raises(R.PinRefused, match="fixture"):
        R.pin_event(ents, FX_TARGET, mode="CHAMPION", champion=steps["model"], references=refs, reasons=[], as_of_utc=AS_OF)
    with pytest.raises(R.PinRefused, match="fixture"):
        R.pin_event(ents, FX_TARGET, mode="NO_VIABLE_CHAMPION", champion=None, references=refs, reasons=[], as_of_utc=AS_OF)
    with pytest.raises(R.PinRefused):
        R.pin_event(ents, FX_TARGET, mode="NO_VIABLE_CHAMPION", champion=None, references={"base_rate": steps["b2"],
                    "simple_model": steps["b0"]}, reasons=[], as_of_utc=AS_OF, allow_fixture=True)
    with pytest.raises(R.PinRefused):
        R.pin_event(ents, "price_path_target_before_invalidation_6h", mode="NO_VIABLE_CHAMPION", champion=None, references=refs,
                    reasons=[], as_of_utc=AS_OF, allow_fixture=True)
    with pytest.raises(R.PinRefused):
        R.pin_event(ents, FX_TARGET, mode="NO_VIABLE_CHAMPION", champion=steps["model"], references=refs, reasons=[],
                    as_of_utc=AS_OF, allow_fixture=True)


# ---------------------------------------------------------------- rollback (G14)
def test_rollback_goes_to_the_baseline_then_to_abstention_and_keeps_history(tmp_path):
    ents, steps = fixture_registry()
    p, sha_, _ = _log_with(tmp_path, steps["initial"])
    old = p.read_text()
    events = R.read_log(old)
    rb = R.rollback_event(events, ents, FX_TARGET, reason="DRIFT_ALERT", as_of_utc=steps["t_drift"], usable=lambda e: True,
                          allow_fixture=True)
    assert rb["kind"] == "ROLLBACK" and rb["mode"] == "CHAMPION" and rb["champion"] == steps["b2"] and rb["from"] == steps["model"]
    sha_, _ = R.append_events(p, [rb], expect_sha=sha_)
    events = R.read_log(p.read_text())
    assert R.resolve(events, ents, FX_TARGET, C.parse_utc(steps["t_drift"]))["champion"] == steps["b2"]
    rb2 = R.rollback_event(events, ents, FX_TARGET, reason=R.INFERENCE_MISMATCH, as_of_utc=steps["t_mismatch"],
                           usable=lambda e: True, allow_fixture=True)
    assert rb2["mode"] == "NO_VIABLE_CHAMPION" and rb2["champion"] is None
    R.append_events(p, [rb2], expect_sha=sha_)
    events = R.read_log(p.read_text())
    assert R.resolve(events, ents, FX_TARGET, C.parse_utc(steps["t_mismatch"]))["mode"] == "NO_VIABLE_CHAMPION"
    assert R.resolve(events, ents, FX_TARGET, C.parse_utc(steps["t_model_pin"]) + 60)["champion"] == steps["model"]
    assert R.is_append_only(old, p.read_text())


def test_rollback_skips_an_earlier_champion_that_is_no_longer_usable():
    ents, steps = fixture_registry()
    events = R.chain_events(steps["initial"])
    rb = R.rollback_event(events, ents, FX_TARGET, reason="DRIFT_ALERT", as_of_utc=steps["t_drift"],
                          usable=lambda e: e["entry_id"] != steps["b2"], allow_fixture=True)
    assert rb["mode"] == "NO_VIABLE_CHAMPION"


def test_rollback_of_the_real_mode_stays_no_viable_champion():
    b0 = make("07", "B0", facts("B0"), fixture=False)
    b2 = make("07", "B2", facts("B2"), fixture=False)
    ents = {e["entry_id"]: e for e in (b0, b2)}
    pin = R.pin_event(ents, FX_TARGET, mode="NO_VIABLE_CHAMPION", champion=None,
                      references={"base_rate": b0["entry_id"], "simple_model": b2["entry_id"]}, reasons=["x"], as_of_utc=AS_OF)
    events = R.chain_events([pin])
    rb = R.rollback_event(events, ents, FX_TARGET, reason="DRIFT_ALERT", as_of_utc="2026-10-27T01:00:00Z", usable=lambda e: True)
    assert rb["mode"] == "NO_VIABLE_CHAMPION" and rb["champion"] is None


# ---------------------------------------------------------------- serving, compatibility, staleness (G12, G13)
def test_serve_uses_a_pinned_champion_only_while_every_check_holds():
    ents, steps = fixture_registry()
    events = R.chain_events(steps["initial"])
    rt = runtime()
    T = C.parse_utc("2026-10-23T00:00:00Z")
    rows = [(f"fx-{i}", 0.2 + 0.01 * i, "") for i in range(5)]
    kw = {"root": ROOT, "allow_fixture": True}
    ok = R.serve(events, ents, FX_TARGET, T, runtime=rt, inference=rows, **kw)
    assert ok["use_champion"] and ok["forecast_inputs"]["card_entry"] == steps["model"]
    assert ok["forecast_inputs"]["level"] == "VALIDATED_EXPERIMENTAL"
    stale = R.serve(events, ents, FX_TARGET, CUT + C.ACCEPTANCE["max_model_age_s"] + 1, runtime=rt, inference=rows, **kw)
    assert not stale["use_champion"] and stale["rollback_required"] and stale["blocking"][0]["state"] == R.MODEL_STALE
    assert stale["forecast_inputs"]["model_id"] == R.NOT_SELECTED and stale["forecast_inputs"]["level"] == "ABSTAIN"
    drift = R.serve(events, ents, FX_TARGET, T, runtime=rt, drift_alarms=[T - 10], inference=rows, **kw)
    assert any(b["state"] == R.DRIFT_ALERT for b in drift["blocking"]) and drift["retrain"]
    mism = R.serve(events, ents, FX_TARGET, T, runtime=rt, inference=rows[:4], **kw)
    assert any(b["state"] == R.INFERENCE_MISMATCH for b in mism["blocking"])
    rt2 = copy.deepcopy(rt)
    rt2["feature_set_sha"]["09"] = "f" * 64
    inc = R.serve(events, ents, FX_TARGET, T, runtime=rt2, inference=rows, **kw)
    assert any(b["state"] == R.INCOMPATIBLE for b in inc["blocking"]) and not inc["use_champion"]
    req = R.serve(events, ents, FX_TARGET, T, runtime=rt, request={"feature_set_sha": "d" * 64}, inference=rows, **kw)
    assert any(b["state"] == R.FEATURE_SCHEMA_MISMATCH for b in req["blocking"])


def test_p46_a_feature_or_schema_change_without_retrain_fails_compatibility(monkeypatch):
    e = make("07", "B2", facts("B2"), fixture=False)
    assert R.compatibility(e, runtime=runtime()) == []
    monkeypatch.setattr(F, "FEATURE_VERSION", "3")
    st = {s["state"] for s in R.compatibility(e, runtime=runtime())}
    assert st == {R.INCOMPATIBLE}
    monkeypatch.undo()
    monkeypatch.setattr(F, "TRANSFORM_REVISION", "asof-3")
    assert any(s["state"] == R.INCOMPATIBLE and "feature definitions" in s["detail"] for s in R.compatibility(e, runtime=runtime()))
    monkeypatch.undo()
    rt = runtime()
    rt["registry_sha"] = "0" * 64
    assert any("target registry" in s["detail"] for s in R.compatibility(e, runtime=rt))
    rt = runtime()
    rt["labels_version"] = "labels-2"
    assert any("labels" in s["detail"] for s in R.compatibility(e, runtime=rt))
    got = R.compatibility(e, runtime=runtime(), request={"feature_set_sha": "0" * 64, "feature_version": "2"})
    assert [s["state"] for s in got] == [R.FEATURE_SCHEMA_MISMATCH]


def test_staleness_and_availability_thresholds_are_exact():
    e = make("07", "B2", facts("B2"), fixture=False)
    edge = CUT + C.ACCEPTANCE["max_model_age_s"]
    assert R._iso(edge) == "2026-10-31T00:00:00Z"
    assert [s["state"] for s in R.status_at(e, edge)] == [R.MODEL_NOT_PROMOTED]
    assert [s["state"] for s in R.status_at(e, edge + 1)] == [R.MODEL_STALE, R.MODEL_NOT_PROMOTED]
    assert R.status_at(e, CUT - 1)[0]["state"] == R.NOT_AVAILABLE_AS_OF
    assert [s["state"] for s in R.status_at(e, CUT)] == [R.MODEL_NOT_PROMOTED]
    got = R.status_at(e, CUT + 100, drift_alarms=[CUT + 100])
    assert R.DRIFT_ALERT in [s["state"] for s in got]
    assert R.DRIFT_ALERT not in [s["state"] for s in R.status_at(e, CUT + 99, drift_alarms=[CUT + 100])]


def test_thresholds_name_the_frozen_constants_of_the_earlier_layers():
    th = R.THRESHOLDS
    assert th[R.MODEL_STALE]["max_model_age_s"] == C.ACCEPTANCE["max_model_age_s"] == 1209600
    assert {k: th[R.DRIFT_ALERT][k] for k in CAL.DRIFT} == CAL.DRIFT
    assert th[R.OUT_OF_DISTRIBUTION]["feature_z_max"] == CAL.OOD_Z
    assert set(th[R.OUT_OF_DISTRIBUTION]["conditions"]) <= set(AB.CONDITIONS)
    assert all(AB.CONDITIONS[c][0] == "OOD" for c in th[R.OUT_OF_DISTRIBUTION]["conditions"])
    assert all(v["contract_reason"] in C.ABSTAIN_REASONS for v in th.values())
    assert R.RETRAIN_POLICY["automatic"] is False and R.RETRAIN_POLICY["inherits_level"] is False
    assert R.retrain_requirements([{"state": R.MODEL_STALE}, {"state": R.MODEL_STALE}]) == [R.RETRAIN[R.MODEL_STALE]]


# ---------------------------------------------------------------- champion restatement (G6)
def test_select_champion_refuses_holdout_or_post_opening_rows_and_delegates_the_rule():
    dev = [{"target": FX_TARGET, "view": "ALL", "reference": "B2", "verdict": "NOT_DISTINGUISHABLE_FROM_BASE_RATE", "brier": "0.2",
            "candidate_id": "P09_M2_OC_LOGIT_B2"}]
    got = R.select_champion(FX_TARGET, dev, {"P07_B2": True, "P09_M2_OC_LOGIT_B2": True}, rule=E.champion)
    assert got["champion"] == "P07_B2" and got["basis"].startswith("default")
    for bad in ({**dev[0], "kind": "SECONDARY_HOLDOUT"}, {**dev[0], "verdict": "SKILL_INDICATED_RETROSPECTIVE_HOLDOUT"},
                {**dev[0], "label": "POST_OPENING"}, {**dev[0], "view": "HOLDOUT_POST_OPENING"}):
        with pytest.raises(R.HoldoutInputRefused):
            R.select_champion(FX_TARGET, [bad], {"P07_B2": True}, rule=E.champion)


# ---------------------------------------------------------------- ensembles (G19)
def _oof(name, rows):
    return [{"fold": f, "decision_key": k, "cutoff": c, "decision_time": t, "mint": "M" + k, "label_matures_at": t + 86400,
             "y": y, "number": n} for f, k, c, t, y, n in rows]


def test_members_may_not_share_an_evidence_source_and_every_column_is_declared():
    b2 = list(real_card("07", "B2")["body"]["columns"])
    m1 = list(real_card("09", "M1_OC_LOGIT")["body"]["spec"]["columns"])
    s1 = list(real_card("10", "S1_SC_LOGIT")["body"]["spec"]["columns"])
    m2 = list(real_card("09", "M2_OC_LOGIT_B2")["body"]["spec"]["columns"])
    s2 = list(real_card("10", "S2_SC_LOGIT_B2")["body"]["spec"]["columns"])
    assert R.check_members({"B0": [], "B2": b2})["members"] == ["B0", "B2"]
    assert R.check_members({"B2": b2, "S1": s1})
    with pytest.raises(R.DoubleCountedEvidence, match="LAB_FATAL_FLAGS"):
        R.check_members({"B2": b2, "M1": m1, "S1": s1})
    with pytest.raises(R.DoubleCountedEvidence):
        R.check_members({"B2": b2, "M2": m2, "S2": s2})
    with pytest.raises(R.UndeclaredColumn):
        R.check_members({"B2": b2, "X": ["tech_log_return_1h"]})
    with pytest.raises(R.RegistryError):
        R.check_members({"B2": b2})


def test_out_of_fold_rows_refuse_in_sample_rows_and_members_from_other_folds():
    a = _oof("a", [("1", "k1", 100.0, 150.0, 1, 0.3), ("1", "k2", 100.0, 160.0, 0, 0.2)])
    b = _oof("b", [("1", "k1", 100.0, 150.0, 1, 0.4), ("1", "k2", 100.0, 160.0, 0, float("nan"))])
    rows = R.out_of_fold_rows({"a": a, "b": b})
    assert [r["decision_key"] for r in rows] == ["k1", "k2"]
    assert R.mean_ensemble(rows[0]["members"]) == pytest.approx(0.35) and math.isnan(R.mean_ensemble(rows[1]["members"]))
    with pytest.raises(R.NotOutOfFold, match="before its fold cutoff"):
        R.out_of_fold_rows({"a": _oof("a", [("1", "k1", 200.0, 150.0, 1, 0.3)]), "b": _oof("b", [("1", "k1", 200.0, 150.0, 1, 0.3)])})
    with pytest.raises(R.NotOutOfFold, match="disagree"):
        R.out_of_fold_rows({"a": _oof("a", [("1", "k1", 100.0, 150.0, 1, 0.3)]), "b": _oof("b", [("1", "k1", 120.0, 150.0, 1, 0.3)])})
    with pytest.raises(R.NotOutOfFold, match="disagree"):
        R.out_of_fold_rows({"a": _oof("a", [("1", "k1", 100.0, 150.0, 1, 0.3)]), "b": _oof("b", [("1", "k1", 100.0, 150.0, 0, 0.3)])})


def test_stacking_is_chronological_gated_and_never_in_sample():
    mk = lambda k, t, y, cut: {"decision_key": k, "decision_time": t, "label_matures_at": t + 10, "cutoff": cut, "y": y,
                               "members": {"B2": 0.3, "S1": 0.2}}
    ev = [mk("e1", 1000.0, 1, 900.0)]
    R.check_stack_rows([mk("f1", 100.0, 0, 0.0)], ev)
    with pytest.raises(R.InSampleStacking):
        R.check_stack_rows(ev, ev)
    with pytest.raises(R.InSampleStacking):
        R.check_stack_rows([mk("f2", 895.0, 0, 0.0)], ev)          # matures after the evaluation cutoff
    with pytest.raises(R.InSampleStacking):
        R.check_stack_rows([mk("f3", 950.0, 0, 0.0)], ev)          # decided after it
    rng = np.random.default_rng(1)
    day = 86400.0
    fit = [{"decision_key": f"r{i}", "decision_time": i * day / 20, "label_matures_at": i * day / 20 + 1, "cutoff": 0.0,
            "y": int(i % 4 == 0), "members": {"B2": float(rng.uniform(0.1, 0.5)), "S1": float(rng.uniform(0.1, 0.5))}} for i in range(100)]
    assert R.stack_gate(fit) == []
    assert R.stack_gate(fit[:99]) and R.stack_gate(fit[:80])
    one_day = [dict(r, decision_time=10.0 + i) for i, r in enumerate(fit)]
    assert any("decision days" in g for g in R.stack_gate(one_day))
    few_pos = [dict(r, y=int(i < 19)) for i, r in enumerate(fit)]
    assert any("per class" in g for g in R.stack_gate(few_pos))
    st = R.fit_stack(fit, ["B2", "S1"])
    p = R.predict_stack(st, fit[:3])
    assert np.all((p > 0) & (p < 1))
    with pytest.raises(R.RegistryError, match="gate"):
        R.fit_stack(fit[:50], ["B2", "S1"])


def test_ensemble_decision_needs_skill_over_b2_the_correction_and_a_reachable_level():
    base = {"configuration": "ENS_X", "status": "EVALUATED_DEVELOPMENT", "verdict_vs_b0": "SKILL_INDICATED_DEVELOPMENT_ONLY",
            "verdict_vs_b2": "SKILL_INDICATED_DEVELOPMENT_ONLY", "selection_status": R.SELECTION_SURVIVES, "level_possible": "SHADOW"}
    assert R.ensemble_decision(FX_TARGET, [base])["decision"] == "ENSEMBLE"
    for k, v in (("verdict_vs_b2", "NOT_DISTINGUISHABLE_FROM_BASE_RATE"), ("selection_status", "FAILS_SELECTION_CORRECTION"),
                 ("level_possible", "NO_GO"), ("verdict_vs_b2", "INSUFFICIENT_DAYS")):
        got = R.ensemble_decision(FX_TARGET, [{**base, k: v}])
        assert got["decision"] == "NO_ENSEMBLE" and got["configuration"] is None


# ---------------------------------------------------------------- target plan and the publication path (G20, G8)
def _req(**over):
    r = {"chain": "solana", "mint": "So11111111111111111111111111111111111111112", "target": FX_TARGET,
         "decision_time": C.parse_utc("2026-10-26T10:00:00Z"), "decision_time_basis": "EXPORT_COMMIT", "snapshot_hash": "1" * 64,
         "flag_on": False, "pool_point_in_time": True, "route": "PIT_RECORDED", "eligibility": "ELIGIBLE", "position_usd": None,
         "backtest_required": False, "x": {}, "avail": {}, "feature_set_sha": F.feature_set_sha(), "new_mint": None,
         "token_history_rows": 0}
    r.update(over)
    return r


def test_no_viable_champion_gives_abstain_documents_with_model_not_selected_that_validate(tmp_path):
    b0 = make("07", "B0", facts("B0"), fixture=False)
    b2 = make("07", "B2", facts("B2"), fixture=False)
    ents = {e["entry_id"]: e for e in (b0, b2)}
    pins = [R.pin_event(ents, FX_TARGET, mode="NO_VIABLE_CHAMPION", champion=None,
                        references={"base_rate": b0["entry_id"], "simple_model": b2["entry_id"]}, reasons=["NO_ENTRY_AT_SHADOW_OR_ABOVE"],
                        as_of_utc=AS_OF)]
    events = R.chain_events(pins)
    rt = runtime()
    s = R.serve(events, ents, FX_TARGET, C.parse_utc("2026-10-27T01:00:00Z"), runtime=rt)
    assert not s["use_champion"] and s["forecast_inputs"] == {"card_entry": None, "model_id": R.NOT_SELECTED, "level": "ABSTAIN",
                                                              "calibration_card_sha": None}
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"predictive": {"enabled": True}}))           # even with the flag ON nothing publishes
    doc, rec = AB.forecast_result(_req(flag_on=True), card=None, level=s["forecast_inputs"]["level"], cal_card=None, raw=0.4,
                                  generated_at_utc=AS_OF, config_path=cfg)
    assert doc["prediction_status"] == "ABSTAIN" and doc["probability"] is None and doc["model_id"] == R.NOT_SELECTED
    assert "MODEL_NOT_SELECTED" in doc["abstain_reasons"] and doc["base_rate"] is None
    assert AB.validate_publication(doc, model_card=None, calibration_card=None, record=rec, config_path=cfg) == []
    plan = R.target_plan({"chain": "solana"}, {t: {**s, "target": t} for t in C.PRIMARY})
    by = {p["target"]: p for p in plan}
    assert len(plan) == len(C.TARGETS)
    for t, reg in C.TARGETS.items():
        if reg["status"] == "PRIMARY":
            assert by[t]["attempted"] and "MODEL_NOT_SELECTED" in by[t]["reasons"] and by[t]["behavioral_scenarios"] == []
            assert by[t]["backtest_assessment_ref"] is None and by[t]["forecast_inputs"]["card_entry"] is None
        else:
            assert not by[t]["attempted"] and by[t]["reasons"] == ["TARGET_NOT_FEASIBLE"]
    evm = R.target_plan({"chain": "base"}, {t: {**s, "target": t} for t in C.PRIMARY})
    assert all(p["reasons"] == ["OUT_OF_SCOPE_CHAIN"] for p in evm if p["status"] == "PRIMARY")


def test_shadow_baseline_mode_records_are_internal_and_never_documents():
    b2 = make("07", "B2", facts("B2"), fixture=False)
    rec = R.reference_record(b2, decision_key="k", decision_time=CUT + C.ACCEPTANCE["max_model_age_s"] + 5, number=0.31, why="",
                             as_of_utc=AS_OF)
    assert rec["published"] is False and not R.is_document(rec) and rec["states"] == [R.MODEL_STALE]
    assert rec["record_id"] == R.sha({k: v for k, v in rec.items() if k != "record_id"})
    assert AB.validate_publication(rec, model_card=None, calibration_card=None)        # not a valid document
    m = make("09", "M2_OC_LOGIT_B2", facts("M2_OC_LOGIT_B2"), fixture=False)
    with pytest.raises(R.RegistryError):
        R.reference_record(m, decision_key="k", decision_time=CUT + 5, number=0.3, why="", as_of_utc=AS_OF)
    with pytest.raises(R.MalformedScore):
        R.reference_record(b2, decision_key="k", decision_time=CUT + 5, number=1.3, why="", as_of_utc=AS_OF)


def test_publishable_needs_the_level_and_a_calibrated_card_of_that_level():
    f = facts("B2", level="SHADOW")
    ok = make("07", "B2", f)
    assert ok["publishable"] and ok["registry_status"] == "PROMOTED_SHADOW"
    for cal in ({"path": "x", "card_sha": "a" * 64, "file_sha256": "b" * 64, "status": "UNCALIBRATED", "level": "SHADOW", "details": []},
                {"path": "x", "card_sha": "a" * 64, "file_sha256": "b" * 64, "status": "CALIBRATED", "level": "ABSTAIN", "details": []}):
        e = make("07", "B2", f, calibration=cal)
        assert e["promotion"]["level"] == "SHADOW" and not e["publishable"]
    forged = copy.deepcopy(make("07", "B2", f, calibration={"path": "x", "card_sha": "a" * 64, "file_sha256": "b" * 64,
                                                           "status": "UNCALIBRATED", "level": "SHADOW", "details": []}))
    forged["publishable"] = True
    forged["entry_id"] = R.sha({k: v for k, v in forged.items() if k != "entry_id"})
    with pytest.raises(R.LevelMismatch):
        R.verify_entry(forged)


def test_make_entry_refuses_facts_of_another_kind_a_target_mismatch_and_a_missing_module_version():
    card = fixture_card("07", "B2")
    base = dict(target=FX_TARGET, card=card, card_path="x", card_file_sha256="c" * 64, calibration=None, evidence={}, risk_flags=[],
                inference=inf_for(card, "07"), registered_as_of_utc=AS_OF, is_fixture=True, code=code_for("07"))
    fam = {"phase": "07", "kind": "B2", "candidate": "P07_B2", "module_version": R.PHASE07_FAMILY_VERSION}
    with pytest.raises(R.RegistryError):
        R.make_entry(family=fam, facts=facts("B0"), **base)
    with pytest.raises(R.RegistryError):
        R.make_entry(family={**fam, "module_version": ""}, facts=facts("B2"), **base)
    with pytest.raises(R.RegistryError):
        R.make_entry(family={**fam, "phase": "15"}, facts=facts("B2"), **base)
    with pytest.raises(R.RegistryError):
        R.make_entry(family=fam, facts=facts("B2"), **{**base, "target": "price_path_target_before_invalidation_6h"})
    with pytest.raises(R.RegistryError):
        R.make_entry(family=fam, facts=facts("B2", fitted=False), **base)


# ---------------------------------------------------------------- added after the first mutation probe (4 survivors)
def test_any_change_to_the_stored_promotion_is_refused_even_at_the_same_level():
    e = make("07", "B2", facts("B2"), fixture=False)
    forged = copy.deepcopy(e)
    forged["promotion"]["reasons"] = ["REFERENCE_BASELINE_NEVER_PUBLISHED"]          # same level, reasons hidden
    forged["entry_id"] = R.sha({k: v for k, v in forged.items() if k != "entry_id"})
    with pytest.raises(R.LevelMismatch):
        R.verify_entry(forged)


def test_a_feature_version_change_alone_is_incompatible():
    e = make("07", "B2", facts("B2"), fixture=False)
    rt = runtime()
    rt["feature_version"] = "3"                                                   # definitions hash left as it is
    got = R.compatibility(e, runtime=rt)
    assert [s["state"] for s in got] == [R.INCOMPATIBLE] and "feature version" in got[0]["detail"]


def test_a_fixture_champion_is_refused_beside_real_references():
    b0 = make("07", "B0", facts("B0"), fixture=False)
    b2 = make("07", "B2", facts("B2"), fixture=False)
    m = make("09", "M2_OC_LOGIT_B2", facts("M2_OC_LOGIT_B2", level="VALIDATED_EXPERIMENTAL"))
    ents = {x["entry_id"]: x for x in (b0, b2, m)}
    with pytest.raises(R.PinRefused, match="fixture entry"):
        R.pin_event(ents, FX_TARGET, mode="CHAMPION", champion=m["entry_id"],
                    references={"base_rate": b0["entry_id"], "simple_model": b2["entry_id"]}, reasons=[], as_of_utc=AS_OF)


def test_a_stacking_fit_row_that_is_also_an_evaluation_row_is_refused_even_when_it_looks_earlier():
    ev = [{"decision_key": "k1", "decision_time": 1000.0, "label_matures_at": 1010.0, "cutoff": 900.0, "y": 1, "members": {}}]
    fit = [{"decision_key": "k1", "decision_time": 100.0, "label_matures_at": 110.0, "cutoff": 0.0, "y": 1, "members": {}}]
    with pytest.raises(R.InSampleStacking, match="also an evaluation row"):
        R.check_stack_rows(fit, ev)



# ---------------------------------------------------------------- CP16-0 and CP16-2: the registry rebuilds the facts itself
import csv as _csv
import inspect as _inspect
import shutil as _shutil

B2_T1_PATH = "audits/predictive-intelligence/phase_07/artifacts/T1_24h/B2.json"


def _p12_rows(model: str, short: str = FX_SHORT) -> tuple[dict | None, dict | None, dict]:
    """The card's committed rows, read the way the registry reads them (PRIMARY row first; skeptic m2)."""
    m = R.metric_rows((ART / "phase_12/validation/HOLDOUT_METRICS.csv").read_text())
    post = R.post_states_of((ART / "phase_12/validation/POST_OPENING_CORRECTIONS.csv").read_text())
    return m.get((short, model, "P07_B0")), m.get((short, model, "P07_B2")), post.get((short, model), {})


def _real_b2_entry(short: str = FX_SHORT):
    path = f"audits/predictive-intelligence/phase_07/artifacts/{short}/B2.json"
    f, ctx = R.facts_from_repo(path, ROOT)
    card, cal = ctx["card"], ctx["cal_card"]
    calref = {"path": ctx["cal_path"], "card_sha": cal["card_sha"], "file_sha256": R.sha_bytes((ROOT / ctx["cal_path"]).read_bytes()),
              "status": cal["status"], "level": cal["level"], "details": cal["details"]}
    target = card["targets"][0]
    e = R.make_entry(target=target, family={"phase": "07", "kind": "B2", "candidate": "P07_B2",
                                            "module_version": R.PHASE07_FAMILY_VERSION}, card=card, card_path=path,
                     card_file_sha256=R.sha_bytes(ctx["card_bytes"]), calibration=calref, facts=f,
                     evidence={"x": {"file": "audits/predictive-intelligence/phase_12/validation/HOLDOUT_METRICS.csv",
                                     "sha256": R.sha_bytes((ART / "phase_12/validation/HOLDOUT_METRICS.csv").read_bytes())}},
                     risk_flags=[], inference=inf_for(card, "07"), registered_as_of_utc=AS_OF, code=code_for("07"))
    m0, m2, post = _p12_rows("P07_B2", short)
    src = dict(card=card, tests=f["tests"], m_b0=m0, m_b2=m2, post_states=post, cal_card=cal)
    return e, src


def _forge(e: dict) -> dict:
    forged = copy.deepcopy(e)
    forged["facts"]["retrospective"].update({"bss": 0.05, "calibration_in_the_large_ok": True, "calibration_every_bin_ok": True})
    forged["facts"]["calibration"] = {"status": "CALIBRATED", "evidence_n": 60, "evidence_k": 12, "evidence_source": "PROSPECTIVE_HOLDOUT",
                                      "evidence_status": "ADMISSIBLE"}
    forged["calibration"] = {**forged["calibration"], "status": "CALIBRATED", "level": "SHADOW"}
    forged["promotion"] = R.promotion_decision(forged["facts"])
    forged["registry_status"] = R.registry_status(forged["promotion"]["level"], forged["role"])
    forged["publishable"] = R.publishable(forged)
    forged["entry_id"] = R.sha({k: v for k, v in forged.items() if k != "entry_id"})
    return forged


def test_derive_facts_rebuilds_the_t1_b2_facts_from_the_committed_files():
    e, src = _real_b2_entry()
    ret = e["facts"]["retrospective"]
    assert ret["evaluation"] == R.FIRST_OPENING and ret["n"] == 66 and ret["kind"] == "PRIMARY_HOLDOUT"
    assert e["facts"]["calibration"]["status"] == "UNCALIBRATED" and e["promotion"]["level"] == "ABSTAIN"
    assert e["facts"]["tests"] == {"leakage": True, "provenance": True, "contract": True, "basis": R.TESTS_BASIS}
    R.verify_facts(e, **dict(src))
    R.check_facts(e, ROOT)
    assert set(R.verify_sources(e, lambda p: (ROOT / p).read_bytes())) == {
        e["card_path"], e["calibration"]["path"], "audits/predictive-intelligence/phase_12/validation/HOLDOUT_METRICS.csv"}
    with pytest.raises(R.EntryHashMismatch):
        R.verify_sources(e, lambda p: (ROOT / p).read_bytes() + b" ")
    with pytest.raises(R.RegistryError):
        R.derive_facts(candidate="P07_B2", phase="07", card=src["card"], tests=src["tests"], m_b0=src["m_b0"], m_b2=src["m_b2"],
                       post_states=src["post_states"], cal_card=None)
    with pytest.raises(R.RegistryError):
        R.derive_facts(candidate="P07_B1", phase="07", card=real_card("07", "B1"), tests=src["tests"], m_b0=None, m_b2=None,
                       post_states={}, cal_card=src["cal_card"])


def test_m2_b2_facts_come_from_the_primary_holdout_row_and_t2_holm_p_is_0_100():
    for short, holm in (("T1_24h", 1.0), ("T1b_6h", 1.0), ("T2_24h", 0.10034498275086245)):
        e, _ = _real_b2_entry(short)
        assert e["facts"]["retrospective"]["kind"] == "PRIMARY_HOLDOUT" and e["facts"]["retrospective"]["p_holm"] == pytest.approx(holm)
    rows = (ART / "phase_12/validation/HOLDOUT_METRICS.csv").read_text()
    m = R.metric_rows(rows)
    assert m[("T2_24h", "P07_B2", "P07_B0")]["kind"] == "PRIMARY_HOLDOUT"
    lines = rows.splitlines(keepends=True)
    dup = lines[0] + lines[1] + lines[1]
    with pytest.raises(R.RegistryError, match="two PRIMARY_HOLDOUT"):
        R.metric_rows(dup)
    # the order of the rows does not decide (a last-wins dictionary did)
    m2 = R.metric_rows(lines[0] + "".join(reversed(lines[1:])))
    assert m2[("T2_24h", "P07_B2", "P07_B0")]["kind"] == "PRIMARY_HOLDOUT"


def _pin_kwargs():
    """CX-S16 on either code: the first pass took a caller verifier (the plausible wrong one checks file hashes only); the
    repaired registry takes the repository root and rebuilds the facts itself."""
    sig = _inspect.signature(R.pin_event).parameters
    if "verify" in sig:
        return {"verify": lambda e: R.verify_sources(e, lambda p: (ROOT / p).read_bytes())}
    return {"root": ROOT}


def _serve_kwargs():
    sig = _inspect.signature(R.serve).parameters
    if "verify" in sig:
        return {"verify": lambda e: R.verify_sources(e, lambda p: (ROOT / p).read_bytes())}
    return {"root": ROOT}


def test_cx_s16_a_forged_facts_entry_is_never_pinned_or_served_whatever_the_caller_checks():
    e, src = _real_b2_entry()
    forged = _forge(e)
    assert forged["promotion"]["level"] == "SHADOW" and forged["publishable"]
    R.verify_entry(forged)                                         # self-consistent
    assert R.verify_sources(forged, lambda p: (ROOT / p).read_bytes())   # every file it names is genuine
    b0 = make("07", "B0", facts("B0"), fixture=False)
    ents = {x["entry_id"]: x for x in (forged, b0, e)}
    refs = {"base_rate": b0["entry_id"], "simple_model": e["entry_id"]}
    with pytest.raises(R.PinRefused):
        R.pin_event(ents, FX_TARGET, mode="CHAMPION", champion=forged["entry_id"], references=refs, reasons=["CX-S16"],
                    as_of_utc=AS_OF, **_pin_kwargs())
    # a hand-written CHAMPION pin of the forged entry in the log is not served either
    bad = {"kind": "PIN", "as_of_utc": AS_OF, "target": FX_TARGET, "mode": "CHAMPION", "champion": forged["entry_id"],
           "champion_inference_sha": forged["inference"]["outputs_sha"], "references": refs, "reasons": ["CX-S16"]}
    events = R.chain_events([bad])
    rows = [(f"fx-{i}", 0.2 + 0.01 * i, "") for i in range(5)]
    got = R.serve(events, ents, FX_TARGET, C.parse_utc(AS_OF) + 60, runtime=runtime(), inference=rows, **_serve_kwargs())
    assert not got["use_champion"] and got["forecast_inputs"]["level"] == "ABSTAIN"


def test_cp16_2_pin_and_serve_need_the_registry_s_own_rebuild():
    e, _ = _real_b2_entry()
    forged = _forge(e)
    b0 = make("07", "B0", facts("B0"), fixture=False)
    ents = {x["entry_id"]: x for x in (forged, b0, e)}
    refs = {"base_rate": b0["entry_id"], "simple_model": e["entry_id"]}
    assert "verify" not in _inspect.signature(R.pin_event).parameters and "verify" not in _inspect.signature(R.serve).parameters
    with pytest.raises(R.PinRefused, match="root"):
        R.pin_event(ents, FX_TARGET, mode="CHAMPION", champion=forged["entry_id"], references=refs, reasons=[], as_of_utc=AS_OF)
    with pytest.raises(R.PinRefused, match="facts refused"):
        R.pin_event(ents, FX_TARGET, mode="CHAMPION", champion=forged["entry_id"], references=refs, reasons=[], as_of_utc=AS_OF,
                    root=ROOT)
    with pytest.raises(R.FactsMismatchError, match="calibration|retrospective"):
        R.check_facts(forged, ROOT)
    bad = {"kind": "PIN", "as_of_utc": AS_OF, "target": FX_TARGET, "mode": "CHAMPION", "champion": forged["entry_id"],
           "champion_inference_sha": forged["inference"]["outputs_sha"], "references": refs, "reasons": ["forged"]}
    events = R.chain_events([bad])
    rows = [(f"fx-{i}", 0.2 + 0.01 * i, "") for i in range(5)]
    T = C.parse_utc(AS_OF) + 60
    none = R.serve(events, ents, FX_TARGET, T, runtime=runtime(), inference=rows)
    assert R.FACTS_NOT_VERIFIED in [b["state"] for b in none["blocking"]] and not none["use_champion"]
    got = R.serve(events, ents, FX_TARGET, T, runtime=runtime(), inference=rows, root=ROOT)
    assert R.FACTS_MISMATCH in [b["state"] for b in got["blocking"]] and got["rollback_required"]


def test_serve_refuses_a_fixture_champion_outside_a_fixture_run_and_needs_inference_rows():
    ents, steps = fixture_registry()
    events = R.chain_events(steps["initial"])
    T = C.parse_utc("2026-10-23T00:00:00Z")
    rows = [(f"fx-{i}", 0.2 + 0.01 * i, "") for i in range(5)]
    real = R.serve(events, ents, FX_TARGET, T, runtime=runtime(), inference=rows, root=ROOT)
    assert [b["state"] for b in real["blocking"]] == [R.FIXTURE_IN_REAL_REGISTRY]
    noinf = R.serve(events, ents, FX_TARGET, T, runtime=runtime(), root=ROOT, allow_fixture=True)
    assert [b["state"] for b in noinf["blocking"]] == [R.INFERENCE_NOT_CHECKED] and not noinf["use_champion"]
    noroot = R.serve(events, ents, FX_TARGET, T, runtime=runtime(), inference=rows, allow_fixture=True)
    assert [b["state"] for b in noroot["blocking"]] == [R.INCOMPATIBLE]
    assert R.pin_event(ents, FX_TARGET, mode="CHAMPION", champion=steps["model"], references={"base_rate": steps["b0"],
                       "simple_model": steps["b2"]}, reasons=[], as_of_utc=AS_OF, allow_fixture=True)["facts_check"] == \
        R.FIXTURE_FACTS_NOT_CHECKED


def test_m5_a_transform_code_change_without_a_version_bump_is_incompatible(tmp_path):
    ents, steps = fixture_registry()
    events = R.chain_events(steps["initial"])
    T = C.parse_utc("2026-10-23T00:00:00Z")
    rows = [(f"fx-{i}", 0.2 + 0.01 * i, "") for i in range(5)]
    for f in ents[steps["model"]]["code"]["files"]:
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
        _shutil.copy2(ROOT / f, tmp_path / f)
    ok = R.serve(events, ents, FX_TARGET, T, runtime=runtime(), inference=rows, root=tmp_path, allow_fixture=True)
    assert ok["use_champion"]
    p = tmp_path / "memelab/predictive/features.py"
    p.write_text(p.read_text().replace("return float(f\"{x:.{SIG}g}\")", "return float(f\"{x:.{SIG}g}\") * 1.0001"))
    assert R.sha_bytes(p.read_bytes()) != R.sha_bytes((ROOT / "memelab/predictive/features.py").read_bytes())
    got = R.serve(events, ents, FX_TARGET, T, runtime=runtime(), inference=rows, root=tmp_path, allow_fixture=True)
    assert not got["use_champion"] and [b["state"] for b in got["blocking"]] == [R.INCOMPATIBLE]
    assert "features.py changed" in got["blocking"][0]["detail"]
    assert R.compatibility(ents[steps["model"]], runtime=runtime()) == []          # the declarations alone did not see it
    (tmp_path / "memelab/predictive/stats.py").unlink()
    assert any("stats.py" in c["detail"] for c in R.code_changes(ents[steps["model"]], tmp_path))
    with pytest.raises(R.RegistryError):
        R.code_of(["memelab/predictive/stats.py"], ROOT)


def test_verify_facts_refuses_another_card():
    e, src = _real_b2_entry()
    other = dict(src)
    other["card"] = real_card("07", "B2", "T1b_6h")
    with pytest.raises(R.EntryHashMismatch):
        R.verify_facts(e, **other)
    bad = copy.deepcopy(e)
    bad["card_path"] = "audits/predictive-intelligence/phase_07/artifacts/T1_24h/B1.json"
    bad["entry_id"] = R.sha({k: v for k, v in bad.items() if k != "entry_id"})
    with pytest.raises(R.FactsMismatchError):
        R.check_facts(bad, ROOT)


# ---------------------------------------------------------------- repair pass 2: skeptic m3, m4, m6
def test_m3_a_missing_every_bin_result_fails_from_40_events():
    for n, ok in ((39, True), (40, False), (66, False)):
        f = facts("B2", level="SHADOW")
        f["retrospective"].update({"n": n, "k": 12, "calibration_every_bin_ok": None})
        got = R.promotion_decision(f)
        assert ("RETROSPECTIVE_CALIBRATION_FAILED" not in got["reasons"]) is ok, (n, got)


def test_m4_family_version_request_feature_version_card_feature_set_and_the_ve_holm_condition():
    e = make("07", "B2", facts("B2"), fixture=False)
    rt = runtime()
    rt["family_version"]["07"] = "baselines-phase07-changed"
    got = R.compatibility(e, runtime=rt)
    assert [s["state"] for s in got] == [R.INCOMPATIBLE] and "family module version" in got[0]["detail"]
    got = R.compatibility(e, runtime=runtime(), request={"feature_set_sha": e["feature_set_sha"], "feature_version": "3"})
    assert [s["state"] for s in got] == [R.FEATURE_SCHEMA_MISMATCH] and "feature version" in got[0]["detail"]
    card = real_card("07", "B2")
    other = copy.deepcopy(card)
    other["feature_set_sha"] = "0" * 64
    other["model_sha"] = R.card_sha_of(other)
    e2 = R.make_entry(target=FX_TARGET, family={"phase": "07", "kind": "B2", "candidate": "P07_B2",
                                                "module_version": R.PHASE07_FAMILY_VERSION}, card=card, card_path="x",
                      card_file_sha256="c" * 64, calibration=None, facts=facts("B2"), evidence={}, risk_flags=[],
                      inference=inf_for(card, "07"), registered_as_of_utc=AS_OF, code=code_for("07"))
    e2b = copy.deepcopy(e2)
    e2b["model_sha"] = other["model_sha"]
    e2b["entry_id"] = R.sha({k: v for k, v in e2b.items() if k != "entry_id"})
    with pytest.raises(R.EntryHashMismatch, match="feature_set_sha"):
        R.verify_entry(e2b, card=other)
    f = facts("M2_OC_LOGIT_B2", level="VALIDATED_EXPERIMENTAL")
    f["retrospective"]["p_holm"] = 0.2                          # lower bound above 0 but Holm not below 0.05
    got = R.promotion_decision(f)
    assert got["level"] == "SHADOW" and "RETROSPECTIVE_LOWER_BOUND_NOT_ABOVE_0" in got["reasons"]


def test_m6_nested_agent_agreement_fields_are_refused_anywhere_in_an_entry():
    for where in ("facts", "evidence", "risk_flags", "inference"):
        f = facts("B2")
        kw = {}
        if where == "facts":
            f["retrospective"] = {"evaluation": None, "agent_agreement_share": 0.9}
        card = fixture_card("07", "B2")
        base = dict(target=FX_TARGET, family={"phase": "07", "kind": "B2", "candidate": "P07_B2",
                                              "module_version": R.PHASE07_FAMILY_VERSION}, card=card, card_path="x",
                    card_file_sha256="c" * 64, calibration=None, facts=f, evidence={}, risk_flags=[],
                    inference=inf_for(card, "07"), registered_as_of_utc=AS_OF, code=code_for("07"), is_fixture=True)
        if where == "evidence":
            base["evidence"] = {"x": {"agent_vote_share": 0.8}}
        if where == "risk_flags":
            base["risk_flags"] = ["MIROFISH_CONSENSUS_HIGH"]
        if where == "inference":
            base["inference"] = {**base["inference"], "note": "swarm agreement 90 percent"}
        with pytest.raises(R.BehavioralNotAModel):
            R.make_entry(**base)
    e = make("07", "B2", facts("B2"))
    bad = copy.deepcopy(e)
    bad["evidence"]["nested"] = [{"persona_votes": 3}]
    bad["entry_id"] = R.sha({k: v for k, v in bad.items() if k != "entry_id"})
    with pytest.raises(R.BehavioralNotAModel):
        R.verify_entry(bad)


def test_check_facts_also_checks_every_evidence_file_hash():
    e, _ = _real_b2_entry()
    bad = copy.deepcopy(e)
    bad["evidence"]["x"]["sha256"] = "0" * 64
    bad["entry_id"] = R.sha({k: v for k, v in bad.items() if k != "entry_id"})
    with pytest.raises(R.EntryHashMismatch):
        R.check_facts(bad, ROOT)


# ---------------------------------------------------------------- added after the repair-pass-2 mutation probe (2 survivors)
def test_verify_facts_refuses_forged_facts_given_the_committed_records():
    e, src = _real_b2_entry()
    with pytest.raises(R.FactsMismatchError, match="calibration|retrospective"):
        R.verify_facts(_forge(e), **dict(src))


def test_an_entry_whose_own_source_is_not_a_statistical_model_is_refused():
    e = make("07", "B2", facts("B2"))
    bad = copy.deepcopy(e)
    bad["source"] = "SCENARIO_ENGINE"                    # facts unchanged, only the entry's own source field differs
    bad["entry_id"] = R.sha({k: v for k, v in bad.items() if k != "entry_id"})
    with pytest.raises(R.BehavioralNotAModel):
        R.verify_entry(bad)
