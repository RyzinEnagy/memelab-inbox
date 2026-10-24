"""Predictive intelligence Phase 01: forecast contract, pre-registered target registry and format validator.

Format only: these tests prove the contract refuses malformed or overclaiming documents (P05, P08, P34, P46, P38 and others).
They say nothing about predictive accuracy. No network, no clock, no writes outside tmp_path.
"""
import copy
import json
import math
import re
import zipfile
from pathlib import Path

import pytest

from memelab.predictive import contract as C

ROOT = Path(__file__).resolve().parent.parent
FIX = json.loads((ROOT / "tests/fixtures/predictive/forecast_examples_format_only.json").read_text())
NA = C.BACKTEST_NOT_AVAILABLE
# Pre-registration fingerprint of TARGETS + ACCEPTANCE (DECISIONS PI-D-014). Changing the registry must change this line
# and be recorded as change control; a silent edit fails here.
FROZEN_REGISTRY_SHA = "dd3b4576aa1e408052dd227e361aa2cbf4b38450994c3b5e6a2be5dc199fbccd"


def abstain():
    return copy.deepcopy(FIX["abstain_example"])


def forecast():
    return copy.deepcopy(FIX["forecast_example"])


def card():
    return copy.deepcopy(FIX["model_card_example"])


def reid(d):
    d["forecast_id"] = C.forecast_id(d["chain"], d["mint_address"], d["snapshot_hash"], d["target"], d["target_version"],
                                     d["horizon_seconds"], d["model_sha"])
    return d


def errs(d, **kw):
    kw.setdefault("backtest", NA)
    return " | ".join(C.validate(d, **kw))


# ---------- registry ----------

def test_registry_is_frozen_and_has_two_to_four_primary_targets():
    assert C.registry_sha256() == FROZEN_REGISTRY_SHA
    assert 2 <= len(C.PRIMARY) <= 4
    need = ("horizon_s", "scope_chain", "decision_time_historical", "decision_time_prospective", "decision_time_never", "execution_lag_s",
            "price_source", "pool_route", "reference_price", "path", "thinning", "statuses_included", "positive", "negative", "tie_rule",
            "censored", "label_observed_at", "fetch_margin_s", "caveats")
    for name in C.PRIMARY:
        t = C.TARGETS[name]
        missing = [k for k in need if k not in t]
        assert not missing, (name, missing)
        assert "position_usd" in t and t["position_usd"] is None      # price path: no size claim (P08)
        assert C.PRICE_PATH_CAVEAT in t["caveats"]
        assert not set(t["positive"]) & set(t["negative"])
    assert C.TARGETS["exit_adjusted_target_before_invalidation_24h"]["status"] == "BLOCKED_NO_HISTORICAL_DEPTH"


def test_format_examples_are_marked_and_well_formed():
    assert FIX["_note"].startswith("FORMAT ONLY")
    assert FIX["abstain_example"]["is_fixture"] and FIX["forecast_example"]["is_fixture"]
    assert errs(abstain()) == ""
    assert errs(forecast(), model_card=card()) == ""


# ---------- P38 and abstention ----------

@pytest.mark.parametrize("p", [1.2, -0.01, math.nan, math.inf, True, "0.3", None])
def test_p38_probability_must_be_finite_in_unit_interval(p):
    d = forecast()
    d["probability"] = p
    assert "probability" in errs(d, model_card=card())


def test_abstain_carries_reasons_and_no_number():
    d = abstain()
    d["probability"] = 0.4
    assert "ABSTAIN carries probability" in errs(d)
    d = abstain()
    d["abstain_reasons"] = []
    assert "named reasons" in errs(d)
    d = abstain()
    d["abstain_reasons"] = ["LOOKS_BAD"]
    assert "named reasons" in errs(d)
    d = abstain()
    d["score"] = 72
    assert "forbidden field score" in errs(d)


def test_probability_outside_its_interval_and_missing_calibration_are_refused():
    d = forecast()
    d["probability"] = 0.5
    assert "outside its uncertainty_interval" in errs(d, model_card=card())
    d = forecast()
    d["calibration_reference"] = {"holdout_n": 12, "passed": True}
    assert "holdout_n >= 50" in errs(d, model_card=card())
    d = forecast()
    d["calibration_reference"]["passed"] = False
    assert "UNCALIBRATED" in errs(d, model_card=card())


# ---------- P05 pending label ----------

def test_p05_pending_label_is_never_scored_or_counted_negative():
    tgt = "price_path_severe_drawdown_or_halt_24h"
    t0 = 1_790_000_000.0
    m = C.label_matures_at(tgt, t0)
    assert m == t0 + 300 + 86400 + 86400 + 900          # entry lag, horizon, halt confirmation, fetch margin
    assert C.label_state(tgt, t0, t0 + 30 * 3600) == "PENDING"   # 24 h horizon, read after 30 h: still pending
    pending = {"forecast_id": "x", "target": tgt, "decision_time": t0, "label": 0, "label_status": "PENDING", "label_observed_at": t0 + 30 * 3600}
    with pytest.raises(C.ContractError, match="P05"):
        C.assert_scorable(pending, as_of=t0 + 30 * 3600)
    unlabeled = dict(pending, label=None)
    with pytest.raises(C.ContractError, match="no binary label"):
        C.assert_scorable(unlabeled, as_of=m + 1)
    early_read = dict(pending, label_status="MATURED")
    with pytest.raises(C.ContractError, match="before its label matured"):
        C.assert_scorable(early_read, as_of=m + 1)          # label value was read at 30 h, before maturity
    ok = dict(pending, label_status="MATURED", label_observed_at=m + 60)
    C.assert_scorable(ok, as_of=m + 60)
    assert C.label_state("price_path_target_before_invalidation_6h", t0, t0 + 6 * 3600) == "PENDING"


# ---------- P08 historical depth ----------

def test_p08_exit_adjusted_target_cannot_be_forecast_and_price_path_is_not_proceeds():
    d = forecast()
    d["target"] = "exit_adjusted_target_before_invalidation_24h"
    d["target_version"] = "0"
    d["position_usd"] = 500
    reid(d)
    c = card()
    c["targets"] = [d["target"]]
    c["target_version"] = {d["target"]: "0"}
    assert "BLOCKED_NO_HISTORICAL_DEPTH: it cannot be forecast" in errs(d, model_card=c)
    d = forecast()
    d["position_usd"] = 500
    assert "a price path is not proceeds" in errs(d, model_card=card())
    d = forecast()
    d["caveats"] = []
    assert "PRICE_PATH_NOT_PROCEEDS" in errs(d, model_card=card())
    d = abstain()       # abstaining on a blocked target with a named reason is allowed and visible
    d["target"], d["target_version"] = "exit_adjusted_target_before_invalidation_24h", "0"
    d["abstain_reasons"] = ["TARGET_NOT_FEASIBLE", "EXECUTION_DATA_MISSING"]
    assert errs(reid(d)) == ""


# ---------- P34 ZIP-only backtesting ----------

def test_p34_prompt_package_zip_is_not_an_installed_backtest(tmp_path, monkeypatch):
    z = tmp_path / "Memecoin_Backtesting_Stress_Testing_Prompt_Package_v1.2.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("Memecoin_Backtesting_Stress_Testing_Prompt_Package_v1.2/START_HERE.md", "prompts only")
    monkeypatch.syspath_prepend(str(z))
    monkeypatch.syspath_prepend(str(tmp_path))
    assert C.backtest_status() == NA
    assert C.backtest_status({"memelab.backtest": False}) == NA
    assert C.backtest_status({"memelab.backtest": True}) == "UNVERIFIED"   # importable is not verified
    d = abstain()
    d["backtest_assessment_ref"] = "audits/backtesting/phase_12/stress.json"
    assert "no combined stress claim" in errs(d)
    d = abstain()
    d["backtest_status"] = "VERIFIED"
    assert "disagrees with the installed state" in errs(d)
    d = abstain()
    d["backtest_assessment_ref"] = "x"
    assert "no combined stress claim" in errs(d, backtest="UNVERIFIED")


# ---------- P46 feature/model mismatch, P13 future-trained model ----------

def test_p46_feature_set_or_target_mismatch_with_the_model_card_is_refused():
    c = card()
    c["feature_set_sha"] = "sha256:" + "0" * 64
    assert "FEATURE_SCHEMA_MISMATCH" in errs(forecast(), model_card=c)
    c = card()
    c["target_version"] = {FIX["forecast_example"]["target"]: "2"}
    assert "does not cover this target and version" in errs(forecast(), model_card=c)
    assert "P46 cannot be checked" in errs(forecast())


def test_p13_model_trained_after_the_decision_is_refused():
    d = forecast()
    d["training_cutoff_utc"] = "2026-10-21T00:00:00Z"
    assert "P13" in errs(d, model_card=card())


# ---------- identity, clocks, idempotency, scenarios ----------

def test_identity_decision_clock_idempotency_and_scenarios():
    d = forecast()
    d["mint_address"] = "BONK"
    assert "never a ticker" in errs(reid(d), model_card=card())
    d = forecast()
    d["decision_time_basis"] = "THESIS_CREATED_AT"
    assert "PI-D-011" in errs(d, model_card=card())
    d = forecast()
    d["horizon_seconds"] = 21600
    assert "registered 86400" in errs(d, model_card=card())
    d = forecast()
    d["forecast_id"] = "fc_" + "1" * 32
    assert "P35" in errs(d, model_card=card())
    assert reid(forecast())["forecast_id"] == FIX["forecast_example"]["forecast_id"]
    d = forecast()
    d["behavioral_scenarios"] = [{"name": "agents agree", "probability": 0.9}]
    assert "P27" in errs(d, model_card=card())
    d = forecast()
    d["chain"] = "base"
    assert "outside the target's scope" in errs(reid(d), model_card=card())


# ---------- flag and isolation ----------

def test_flag_defaults_off_and_needs_an_explicit_true(tmp_path):
    assert C.enabled(tmp_path / "absent.json") is False
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"predictive": {"enabled": "true"}}))
    assert C.enabled(cfg) is False
    cfg.write_text(json.dumps({"predictive": {"enabled": True}}))
    assert C.enabled(cfg) is True
    cfg.write_text("{not json")
    assert C.enabled(cfg) is False


def test_no_existing_module_imports_the_predictive_package():
    pat = re.compile(r"^\s*(from\s+[.\w]*predictive\b|import\s+[.\w]*predictive\b)", re.M)
    hits = [str(p.relative_to(ROOT)) for p in (ROOT / "memelab").rglob("*.py")
            if "predictive" not in p.relative_to(ROOT / "memelab").parts and pat.search(p.read_text())]
    assert hits == []
