"""Predictive intelligence Phase 01: forecast contract, pre-registered target registry and format validator.

Format only: these tests prove the contract refuses malformed or overclaiming documents (P05, P08, P34, P46, P38 and others).
They say nothing about predictive accuracy. No network, no clock, no writes outside tmp_path.
"""
import ast
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
# Fingerprint of TARGETS + ACCEPTANCE. Pre-registered dd3b4576... (b6f2621, PI-D-014); changed by CC-01 (9f8c9deb..., PI-D-019) and
# by CC-02 (repair pass 2, PI-D-021), both before any label existed; changed by CC-03 (Phase 06, PI-D-040: absence evidence, halt span
# and other pools, one read per decision), also before any label was computed. A further change must update this line and be recorded
# as change control; a silent edit fails here.
FROZEN_REGISTRY_SHA = "4b4aabce77a5a6f9214c4cfdddf5223f410ed6126410cf4b213b3c80b035f896"
ACCEPTANCE_DOC = ROOT / "audits/predictive-intelligence/phase_01/architecture/ACCEPTANCE_METRICS.md"


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
    return C.validate(d, **kw)


def joined(d, **kw):
    return " | ".join(errs(d, **kw))


# ---------- registry and frozen acceptance plan ----------

def test_registry_is_frozen_and_has_two_to_four_primary_targets():
    assert C.registry_sha256() == FROZEN_REGISTRY_SHA
    assert 2 <= len(C.PRIMARY) <= 4
    need = ("horizon_s", "scope_chain", "unit", "decision_time_historical", "decision_time_prospective", "decision_time_never",
            "same_time_rule", "execution_lag_s", "price_source", "pool_route", "reference_price", "eligibility_classes", "gap_rule",
            "path", "thinning", "statuses_included", "positive", "negative", "tie_rule", "censored", "unverifiable_rule",
            "label_observed_at", "fetch_margin_s", "caveats")
    for name in C.PRIMARY:
        t = C.TARGETS[name]
        missing = [k for k in need if k not in t]
        assert not missing, (name, missing)
        assert "position_usd" in t and t["position_usd"] is None      # price path: no size claim (P08)
        assert C.PRICE_PATH_CAVEAT in t["caveats"]
        assert not set(t["positive"]) & set(t["negative"])
        assert set(t["eligibility_classes"]) == set(C.ELIGIBILITY_CLASSES)
        assert "VENDOR_OR_ROUTE_GAP" in t["censored"]
    assert C.TARGETS["exit_adjusted_target_before_invalidation_24h"]["status"] == "BLOCKED_NO_HISTORICAL_DEPTH"
    assert C.ACCEPTANCE["multiple_testing"]["family"] == list(C.PRIMARY)


LOOSENINGS = [
    ("calibration interval 95% to 99.9%", ("calibration", "conf"), 0.999),
    ("one calibration bin", ("calibration", "max_bins"), 1),
    ("smaller calibration bins", ("calibration", "min_bin_events"), 5),
    ("Holm dropped", ("multiple_testing", "method"), "none"),
    ("BSS lower bound allowed below 0", ("promotion", "VALIDATED_EXPERIMENTAL", "bss_lower_bound_gt"), -0.05),
    ("prospective holdout dropped", ("promotion", "VALIDATED_EXPERIMENTAL", "holdouts"), ["retrospective"]),
    ("B2 comparison dropped", ("promotion", "VALIDATED_EXPERIMENTAL", "brier_point_not_worse_than"), "B0"),
    ("SHADOW below base rate", ("promotion", "SHADOW", "bss_point_min"), -0.1),
    ("one effective day", ("min_effective_days",), 1),
    ("first fold moved", ("walk_forward", "first_fold_last_train_day_utc"), "2026-10-15"),
    ("holdout start moved", ("holdout_window_utc",), ["2026-10-19T00:00:00Z", "2026-10-24T00:00:00Z"]),
    ("fewer holdout events", ("min_holdout_events",), 30),
    ("fewer training events", ("min_train_events",), 50),
    ("primary score changed", ("primary_score",), "log_loss"),
    ("bootstrap without day blocks", ("bootstrap", "resample_units"), ["mint"]),
    ("contacted holdout decisions readmitted", ("holdout_contacted", "decisions"), []),
    ("market-inactive threshold raised", ("eligibility", "market_inactive_vol_24h_usd"), 50000),
    ("API pace raised", ("api_limits", "geckoterminal_calls_per_min"), 30),
    ("model age stretched", ("max_model_age_s",), 90 * 86400),
]


@pytest.mark.parametrize("name,path,value", LOOSENINGS, ids=[x[0] for x in LOOSENINGS])
def test_loosening_any_frozen_acceptance_rule_changes_the_fingerprint(name, path, value):
    acc = copy.deepcopy(C.ACCEPTANCE)
    node = acc
    for k in path[:-1]:
        node = node[k]
    assert path[-1] in node, name
    node[path[-1]] = value
    assert C.fingerprint(C.TARGETS, acc) != FROZEN_REGISTRY_SHA


def test_acceptance_document_carries_the_frozen_block_verbatim():
    text = ACCEPTANCE_DOC.read_text()
    m = re.search(r"<!-- frozen-acceptance:start -->\s*```json\n(.*?)\n```\s*<!-- frozen-acceptance:end -->", text, re.S)
    assert m, "ACCEPTANCE_METRICS.md lost its frozen block"
    assert json.loads(m.group(1)) == C.ACCEPTANCE


def test_format_examples_are_marked_and_well_formed():
    assert FIX["_note"].startswith("FORMAT ONLY")
    assert FIX["abstain_example"]["is_fixture"] and FIX["forecast_example"]["is_fixture"]
    assert errs(abstain()) == []
    assert errs(forecast(), model_card=card()) == []


# ---------- P38, numbers and abstention (one assertion per rule) ----------

@pytest.mark.parametrize("p", [1.2, -0.01, math.nan, math.inf, True, "0.3", None])
def test_p38_probability_must_be_finite_in_unit_interval(p):
    d = forecast()
    d["probability"] = p
    d["uncertainty_interval"] = [0.0, 1.0]
    assert f"probability {p!r} must be a finite number in [0, 1] (P38)" in errs(d, model_card=card())


def test_out_of_range_probability_inside_a_wide_interval_is_still_refused():
    d = forecast()
    d["probability"], d["uncertainty_interval"] = 1.2, [1.0, 1.4]
    e = errs(d, model_card=card())
    assert "probability 1.2 must be a finite number in [0, 1] (P38)" in e
    assert "uncertainty_interval must be [low, high] inside [0, 1]" in e


def test_bool_is_not_a_probability_or_a_base_rate():
    d = forecast()
    d["probability"], d["uncertainty_interval"], d["base_rate"] = True, [0.0, 1.0], True
    e = errs(d, model_card=card())
    assert "probability True must be a finite number in [0, 1] (P38)" in e
    assert "base_rate must be a finite number in [0, 1]" in e


@pytest.mark.parametrize("v", [1.5, -0.1, math.nan])
def test_base_rate_range_on_forecast_and_abstain(v):
    d = forecast()
    d["base_rate"] = v
    assert "base_rate must be a finite number in [0, 1]" in errs(d, model_card=card())
    a = abstain()
    a["base_rate"] = v
    assert "base_rate must be a finite number in [0, 1]" in errs(a)


@pytest.mark.parametrize("field", ["model_sha", "feature_set_sha", "data_snapshot_sha", "training_cutoff_utc", "model_id"])
def test_forecast_needs_every_fingerprint(field):
    d = forecast()
    d[field] = None
    reid(d)
    assert f"FORECAST needs {field}" in errs(d, model_card=card())


@pytest.mark.parametrize("field,value", [("probability", 0.4), ("probability", math.nan), ("probability", 0),
                                         ("uncertainty_interval", [0.1, 0.2])])
def test_abstain_carries_no_number(field, value):
    d = abstain()
    d[field] = value
    assert f"ABSTAIN carries {field}: no number when abstaining (P38)" in errs(d)


def test_abstain_needs_named_reasons_and_no_extra_fields():
    d = abstain()
    d["abstain_reasons"] = []
    assert "named reasons" in joined(d)
    d = abstain()
    d["abstain_reasons"] = ["LOOKS_BAD"]
    assert "named reasons" in joined(d)
    for k, v in (("score", 72), ("opportunity_score", 72), ("confidence", 0.93), ("Signal", "x")):
        d = abstain()
        d[k] = v
        assert f"forbidden field {k}: a forecast is not a score, rank, signal, confidence or order" in errs(d)
    d = abstain()
    d["note_for_reader"] = "x"
    assert "unknown field note_for_reader: the contract has exactly its listed fields" in errs(d)


def test_probability_outside_its_interval_and_missing_calibration_are_refused():
    d = forecast()
    d["probability"] = 0.5
    assert "probability lies outside its uncertainty_interval" in errs(d, model_card=card())
    d = forecast()
    d["calibration_reference"] = {"holdout_n": 12, "passed": True}
    assert "holdout_n >= 50" in joined(d, model_card=card())
    d = forecast()
    d["calibration_reference"]["passed"] = False
    assert "UNCALIBRATED" in joined(d, model_card=card())


def test_generated_before_decision_is_refused():
    d = forecast()
    d["generated_at_utc"] = "2026-10-20T10:24:01Z"
    assert "generated_at_utc is before decision_time_utc" in errs(d, model_card=card())


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
    assert "BLOCKED_NO_HISTORICAL_DEPTH: it cannot be forecast" in joined(d, model_card=c)
    d = forecast()
    d["position_usd"] = 500
    assert "a price path is not proceeds" in joined(d, model_card=card())
    d = forecast()
    d["caveats"] = []
    assert "PRICE_PATH_NOT_PROCEEDS" in joined(d, model_card=card())
    d = abstain()       # abstaining on a blocked target with a named reason is allowed and visible
    d["target"], d["target_version"] = "exit_adjusted_target_before_invalidation_24h", "0"
    d["abstain_reasons"] = ["TARGET_NOT_FEASIBLE", "EXECUTION_DATA_MISSING"]
    assert errs(reid(d)) == []


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
    assert "no combined stress claim" in joined(d)
    d = abstain()
    d["backtest_status"] = "VERIFIED"
    assert "disagrees with the installed state" in joined(d)
    d = abstain()
    d["backtest_assessment_ref"] = "x"
    assert "no combined stress claim" in joined(d, backtest="UNVERIFIED")


# ---------- P46 feature/model mismatch, P13 model chronology, MODEL_STALE ----------

def test_p46_feature_set_or_target_mismatch_with_the_model_card_is_refused():
    c = card()
    c["feature_set_sha"] = "sha256:" + "0" * 64
    assert "FEATURE_SCHEMA_MISMATCH" in joined(forecast(), model_card=c)
    c = card()
    c["target_version"] = {FIX["forecast_example"]["target"]: "2"}
    assert "does not cover this target and version" in joined(forecast(), model_card=c)
    assert "P46 cannot be checked" in joined(forecast())


def test_p13_model_trained_after_the_decision_is_refused():
    d = forecast()
    d["training_cutoff_utc"] = "2026-10-21T00:00:00Z"
    assert "P13" in joined(d, model_card=dict(card(), training_cutoff_utc="2026-10-21T00:00:00Z"))


def test_p13_cutoff_is_the_model_cards_not_the_forecasts_claim():
    c = card()
    c["training_cutoff_utc"] = "2026-10-22T00:00:00Z"          # the model really saw data after the decision
    assert "training_cutoff_utc differs from the model card" in joined(forecast(), model_card=c)


def test_model_stale_is_enforced():
    d = forecast()
    d["training_cutoff_utc"] = "2026-07-01T00:00:00Z"
    assert "MODEL_STALE" in joined(d, model_card=dict(card(), training_cutoff_utc="2026-07-01T00:00:00Z"))


# ---------- identity, clocks, idempotency, scenarios ----------

def test_identity_decision_clock_idempotency_and_scenarios():
    d = forecast()
    d["mint_address"] = "BONK"
    assert "never a ticker" in joined(reid(d), model_card=card())
    d = forecast()
    d["mint_address"] = d["mint_address"] + "\n"                 # would make a second forecast_id for the same mint (P35)
    assert "never a ticker" in joined(reid(d), model_card=card())
    a = abstain()
    a["mint_address"] = "BONK"
    assert "never a ticker" in joined(reid(a))
    a = abstain()
    a["chain"], a["mint_address"] = "base", "0x" + "ab" * 20
    a["abstain_reasons"] = ["OUT_OF_SCOPE_CHAIN"]
    assert errs(reid(a)) == []
    d = forecast()
    d["decision_time_basis"] = "THESIS_CREATED_AT"
    assert "PI-D-011" in joined(d, model_card=card())
    d = forecast()
    d["horizon_seconds"] = 21600
    assert "registered 86400" in joined(d, model_card=card())
    d = forecast()
    d["forecast_id"] = "fc_" + "1" * 32
    assert "P35" in joined(d, model_card=card())
    assert reid(forecast())["forecast_id"] == FIX["forecast_example"]["forecast_id"]
    d = forecast()
    d["behavioral_scenarios"] = [{"name": "agents agree", "probability": 0.9}]
    assert "P27" in joined(d, model_card=card())
    d = forecast()
    d["chain"], d["mint_address"] = "base", "0x" + "ab" * 20
    assert "outside the target's scope" in joined(reid(d), model_card=card())


# ---------- reference price, path and eligibility (CC-01, P06, CC-02 F3) ----------

def test_reference_price_uses_only_candles_available_at_the_decision():
    d = 1_790_000_000.0
    row = lambda start, close: [start, close, close, close, close, 100.0]   # noqa: E731
    candles = [row(d - 3900, 1.0),        # ends d - 3600: oldest allowed end
               row(d - 1000, 2.0),        # ends d - 700: available at d - 400
               row(d - 500, 3.0),         # ends d - 200: closed before the decision but not served until d + 100
               row(d - 200, 4.0),         # ends d + 100: closes after the decision, before t_entry
               row(d + 300, 5.0)]         # the candle holding t_entry
    assert C.reference_candle(candles, d)[4] == 2.0
    assert C.reference_candle(candles[:1], d)[4] == 1.0
    assert C.reference_candle([row(d - 4000, 1.0)], d) is None          # last trade more than an hour before
    assert C.reference_candle(candles[2:], d) is None                   # only not-yet-available candles
    assert C.reference_candle(candles, d, provider_lag_s=0)[4] == 3.0  # the lag is what excludes the d - 200 candle


def test_path_starts_after_entry_and_never_uses_the_entry_candle():
    d = 1_790_000_000.0
    starts = [d - 300, d, d + 200, d + 300, d + 600, d + 21600, d + 21600 + 300]
    got = [c[0] for c in C.path_candles([[s, 1, 1, 1, 1, 1] for s in starts], d, 21600)]
    assert got == [d + 300, d + 600, d + 21600]                         # t_entry = d + 300; last candle ends at t_entry + 6 h


def test_eligibility_never_turns_a_vendor_or_route_gap_into_a_quiet_market():
    d = 1_790_000_000.0
    recent = [[d - 1000, 1, 1, 1, 1, 10]]
    earlier_today = [[d - 30000, 1, 1, 1, 1, 10]]
    E = C.eligibility
    assert E(recent, d, read_ok=True, pool="P", route="PIT_RECORDED", snapshot_vol_24h=94115.0) == "ELIGIBLE"
    # the BAT case of the coverage sample: vendor-list pool, no candle that day, lab saw $94k of 24 h volume
    assert E([], d, read_ok=True, pool="P", route="CURRENT_VENDOR_LIST", snapshot_vol_24h=94115.0) == "VENDOR_OR_ROUTE_GAP"
    assert E(earlier_today, d, read_ok=True, pool="P", route="CURRENT_VENDOR_LIST", snapshot_vol_24h=94115.0) == "VENDOR_OR_ROUTE_GAP"
    assert E([], d, read_ok=True, pool="P", route="CURRENT_VENDOR_LIST", snapshot_vol_24h=650.0) == "MARKET_INACTIVE"
    assert E(earlier_today, d, read_ok=True, pool="P", route="PIT_RECORDED", snapshot_vol_24h=94115.0) == "MARKET_INACTIVE"
    assert E([], d, read_ok=True, pool="P", route="PIT_RECORDED", snapshot_vol_24h=None) == "VENDOR_OR_ROUTE_GAP"
    assert E(recent, d, read_ok=False, pool="P", route="PIT_RECORDED", snapshot_vol_24h=10.0) == "VENDOR_OR_ROUTE_GAP"
    assert E(None, d, read_ok=True, pool="P", route="PIT_RECORDED", snapshot_vol_24h=10.0) == "VENDOR_OR_ROUTE_GAP"
    assert E(recent, d, read_ok=True, pool=None, route="PIT_RECORDED", snapshot_vol_24h=10.0) == "VENDOR_OR_ROUTE_GAP"
    for bad in (True, math.nan, -1.0, "500"):
        assert E([], d, read_ok=True, pool="P", route="CURRENT_VENDOR_LIST", snapshot_vol_24h=bad) == "VENDOR_OR_ROUTE_GAP"


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


_DOTTED = re.compile(r"(^|\.)predictive(\.|$)")


def _imports_predictive(src: str) -> list[str]:
    hits = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            hits += [a.name for a in node.names if _DOTTED.search(a.name)]
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if _DOTTED.search(mod) or any(a.name == "predictive" for a in node.names):
                hits.append(("." * node.level) + mod)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and " " not in node.value and _DOTTED.search(node.value):
            hits.append(node.value)                              # import_module("memelab.predictive...") or __import__ strings
    return hits


# Phase 17 (PI-D-093 item 7): the only seam is memelab/cli.py, whose two helpers import memelab.predictive.integration lazily
SEAMS = {"memelab/cli.py": [".predictive", ".predictive", "predictive"]}    # CP17-1: the config key, read by _predictive_enabled
SEAM_FUNCTIONS = ("_predictive_section", "_predictive_line")
FLAG_READER = "_predictive_enabled"


def _seam_violations(src: str) -> list[str]:
    """Every predictive import in a seam module must be `from .predictive import integration` inside one of the two helpers."""
    tree = ast.parse(src)
    ok_nodes = set()
    for f in tree.body:
        if isinstance(f, ast.FunctionDef) and f.name == FLAG_READER:      # only the bare config key, as a string, in the flag reader
            for n in ast.walk(f):
                if isinstance(n, ast.Constant) and n.value == "predictive":
                    ok_nodes.add(id(n))
                if isinstance(n, (ast.Import, ast.ImportFrom)):
                    ok_nodes.discard(id(n))
        if isinstance(f, ast.FunctionDef) and f.name in SEAM_FUNCTIONS:
            for n in ast.walk(f):
                if isinstance(n, ast.ImportFrom) and n.level == 1 and n.module == "predictive" and [a.name for a in n.names] == ["integration"]:
                    ok_nodes.add(id(n))
    bad = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)) and _imports_predictive(ast.unparse(n)) and id(n) not in ok_nodes:
            bad.append(ast.unparse(n))
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and " " not in n.value and _DOTTED.search(n.value) \
                and id(n) not in ok_nodes:
            bad.append(repr(n.value))
    return bad


def test_no_existing_module_imports_the_predictive_package():
    hits = {}
    for p in (ROOT / "memelab").rglob("*.py"):
        if "predictive" in p.relative_to(ROOT / "memelab").parts:
            continue
        h = _imports_predictive(p.read_text())
        if h:
            hits[str(p.relative_to(ROOT))] = h
    assert hits == SEAMS
    assert _seam_violations((ROOT / "memelab/cli.py").read_text()) == []


def _relative_users(src: str, target: str) -> bool:
    """CP17-1 (skeptic m4): a relative import of a sibling module, read from the AST, in every form: `from . import a, target`,
    `from . import target as T`, `from .target import name`."""
    return any(isinstance(n, ast.ImportFrom) and n.level == 1 and ((n.module or "") == target or (n.module is None and any(a.name == target for a in n.names)))
               for n in ast.walk(ast.parse(src)))


def test_no_predictive_module_imports_the_integration_module():
    users = [p.name for p in (ROOT / "memelab/predictive").glob("*.py") if _relative_users(p.read_text(), "integration")]
    assert users == []                                   # the integration is a leaf: it is imported only by the cli helpers


@pytest.mark.parametrize("src", ["from . import stats, integration", "from . import integration as II", "from .integration import run_pass"])
def test_the_relative_import_scan_sees_every_form(src):
    assert _relative_users(src, "integration") and not _relative_users("from . import stats", "integration")


@pytest.mark.parametrize("src", ["from .predictive import integration",                      # at module level
                                 "def _predictive_section():\n    from .predictive import contract",
                                 "def _predictive_line():\n    from .predictive import integration, registry",
                                 "def other():\n    from .predictive import integration",
                                 "def _predictive_line():\n    import importlib\n    importlib.import_module('memelab.predictive.integration')",
                                 "def _predictive_enabled():\n    return 'memelab.predictive'",
                                 "def _predictive_enabled():\n    from .predictive import contract",
                                 "def other():\n    return {}.get('predictive')"])
def test_the_seam_allows_nothing_but_the_lazy_integration_import(src):
    assert _seam_violations(src)
    assert not _seam_violations("def _predictive_section():\n    from .predictive import integration")


@pytest.mark.parametrize("src", ["from memelab import predictive", "from . import predictive", "from .predictive import contract",
                                 "import memelab.predictive.contract", "from ..predictive.contract import validate",
                                 "import importlib\nimportlib.import_module('memelab.predictive.contract')",
                                 "__import__('memelab.predictive')"])
def test_the_isolation_check_sees_every_import_form(src):
    assert _imports_predictive(src)
    assert not _imports_predictive("help = 'predictive value of public posts'")
