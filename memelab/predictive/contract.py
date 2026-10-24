"""Phase 01: forecast output contract, pre-registered target registry and format validator. Pure: no I/O except reading the
optional config file for the flag, no network, no clock.

FORMAT ONLY. A document that passes `validate` is well formed; that says nothing about predictive accuracy. Phase 01 fitted
no model and computed no outcome. Human-readable registry: audits/predictive-intelligence/phase_01/architecture/TARGET_REGISTRY.md.

Rules enforced here (package FORECAST_OUTPUT_SCHEMA.md, ADVERSARIAL_SCENARIOS.md, DECISIONS PI-D-006, PI-D-011, PI-D-014 to PI-D-019):
  - one result per (chain, mint, snapshot_hash, target, target_version, horizon, model_sha); the forecast_id is derived from them;
  - a probability only with prediction_status FORECAST, finite in [0, 1], inside its interval, with base rate, calibration
    reference and model, feature-set and data fingerprints; ABSTAIN carries named reasons and no number (P38);
  - only PRIMARY targets can be forecast; the exit-adjusted target is BLOCKED (no historical executable depth, P08);
    price-path targets carry no position size and the PRICE_PATH_NOT_PROCEEDS caveat;
  - the model's feature set and target must match the forecast (P46); a model trained after the decision is refused (P13);
  - a label is PENDING until it matures and can never be scored before that (P05);
  - backtesting is BACKTEST_NOT_AVAILABLE unless a verified engine exists; a prompt-package ZIP is not one (P34);
  - decision time never comes from theses.created_at (PI-D-011);
  - behavioral scenarios never carry a probability (P27);
  - the reference price uses only candles available at the decision, and the path never uses the candle holding the entry (CC-01, P06).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "memelab.predictive.forecast/1"
REGISTRY_VERSION = "memelab.predictive.targets/1"
FLAG_SECTION = "predictive"

PREDICTION_STATUSES = ("FORECAST", "ABSTAIN")
ABSTAIN_REASONS = (
    "INSUFFICIENT_HISTORY", "NOT_YET_MATURED", "UNCALIBRATED", "MODEL_STALE", "DRIFT_ALERT", "OOD",
    "FEATURE_SCHEMA_MISMATCH", "EXECUTION_DATA_MISSING", "NO_RECENT_PRICE", "OUT_OF_SCOPE_CHAIN",
    "OUT_OF_SCOPE_OPPORTUNITY_TYPE", "TARGET_NOT_FEASIBLE", "UNVERIFIED_EVENT", "RESTRICTED_SOURCE", "SOURCE_STALE",
    "MODEL_NOT_SELECTED", "FLAG_OFF",
)
DECISION_TIME_BASES = ("EXPORT_COMMIT", "CAPTURE_TIME")     # never theses.created_at (PI-D-011)
BACKTEST_NOT_AVAILABLE = "BACKTEST_NOT_AVAILABLE"
BACKTEST_STATUSES = (BACKTEST_NOT_AVAILABLE, "UNVERIFIED", "VERIFIED")
BACKTEST_MODULES = ("memelab.backtest", "memelab.backtesting", "memelab.stress")
FORBIDDEN_KEYS = ("score", "rank", "signal", "bullish", "bearish", "buy", "sell", "order", "wallet", "private_key")
PRICE_PATH_CAVEAT = "PRICE_PATH_NOT_PROCEEDS"

# Acceptance constants frozen in Phase 01 (ACCEPTANCE_METRICS.md). Changing one is a recorded change-control decision.
ACCEPTANCE = {
    "min_train_events": 100, "min_train_per_class": 20,
    "min_holdout_events": 50, "min_holdout_per_class": 10,
    "min_bin_events": 20, "display_probability_range": [0.01, 0.99],
    "holdout_window_utc": ["2026-10-17T00:00:00Z", "2026-10-24T00:00:00Z"],
    "prospective_from_utc": "2026-10-24T00:00:00Z",
    "max_model_age_s": 14 * 86400,
}

_COMMON = {
    "scope_chain": "solana",
    "unit": "decision event: one deep-analysis thesis of an exact Solana mint, thinned per mint to non-overlapping label windows",
    "decision_time_historical": "commit time of the first data/state/latest.json commit on main that contains the thesis row (mint, created_at)",
    "decision_time_prospective": "capture time recorded when the forecast request is created",
    "decision_time_never": "theses.created_at or any t-stamped column (PI-D-011)",
    "execution_lag_s": 300,
    "price_source": "GeckoTerminal public OHLCV of the reference pool, minute timeframe aggregate 5, currency usd, empty intervals omitted",
    "pool_route": "primary_pool or graduated_pool of the token row in the first export holding the thesis (PIT_RECORDED); otherwise the "
                  "vendor's current top pool for the mint at label time (CURRENT_VENDOR_LIST, flagged and stratified)",
    "reference_price": "close of the newest 5-minute candle available at the decision: candle end + provider lag (300 s, "
                       "replay_sources.PROVIDER_LAG, HEURISTIC) <= decision time and candle end >= decision time - 3600 s; none: "
                       "INELIGIBLE_NO_RECENT_TRADE. Only data available at the decision decide eligibility (CC-01, PI-D-019)",
    "gap_rule": "candles between the reference candle and t_entry are neither reference nor path",
    "path": "5-minute candles that start at or after t_entry and end at or before t_entry + horizon; the candle holding t_entry is never used",
    "thinning": "eligibility first, then per mint the first eligible decision and each next eligible decision at least one horizon "
                "after the previous kept one; theses of one mint that share a decision time count once, as the newest created_at",
    "statuses_included": "all thesis statuses, REJECTED and fatal-flagged included",
    "label_observed_at": "retrieval time of the candles; a backfill read is never a historical availability claim",
    "fetch_margin_s": 900,
    "censored": ["UNVERIFIABLE_NO_VENDOR_HISTORY"],
    "position_usd": None,
    "caveats": [PRICE_PATH_CAVEAT, "NO_HISTORICAL_EXECUTABLE_DEPTH"],
}

TARGETS: dict[str, dict[str, Any]] = {
    "price_path_target_before_invalidation_24h": dict(_COMMON, status="PRIMARY", version="1", horizon_s=86400,
        upper=1.25, lower=0.85, confirm_s=0,
        positive=["TARGET_FIRST"], negative=["INVALIDATION_FIRST", "AMBIGUOUS_BAR", "NEITHER", "NO_TRADES_AFTER_ENTRY"],
        tie_rule="a candle touching both barriers resolves to AMBIGUOUS_BAR, counted negative (conservative); no 1-minute refinement in v1"),
    "price_path_target_before_invalidation_6h": dict(_COMMON, status="PRIMARY", version="1", horizon_s=21600,
        upper=1.25, lower=0.85, confirm_s=0,
        positive=["TARGET_FIRST"], negative=["INVALIDATION_FIRST", "AMBIGUOUS_BAR", "NEITHER", "NO_TRADES_AFTER_ENTRY"],
        tie_rule="a candle touching both barriers resolves to AMBIGUOUS_BAR, counted negative (conservative); no 1-minute refinement in v1"),
    "price_path_severe_drawdown_or_halt_24h": dict(_COMMON, status="PRIMARY", version="1", horizon_s=86400,
        drawdown=0.5, halt_quiet_from_s=64800, confirm_s=86400,
        positive=["DRAWDOWN_50", "TRADING_HALT"], negative=["NO_SEVERE_EVENT"],
        tie_rule="none needed: one barrier; TRADING_HALT = no candle on the reference pool or up to 3 other vendor-listed pools of the mint "
                 "from t_entry + 18 h to t_entry + 48 h"),
    "exit_adjusted_target_before_invalidation_24h": {"status": "BLOCKED_NO_HISTORICAL_DEPTH", "version": "0", "horizon_s": 86400,
        "why": "needs sell quotes at a stated size at entry and at the barrier times; none kept after 2026-10-08, theses hold exit_cap_3pct at decision only (P08)"},
    "liquidity_degradation_24h": {"status": "DEFERRED_FORWARD_COLLECTION", "version": "0", "horizon_s": 86400,
        "why": "needs pool reserves or quotes at decision and decision + 24 h for every decision; snapshots give 53 of 351, a watchlist-selected subset; "
               "a scheduled collector needs Elving's approval"},
    "failed_breakout_6h": {"status": "DEFERRED_PHASE_08", "version": "0", "horizon_s": 21600,
        "why": "eligibility needs the m14 breakout class as of the decision; it is not exported and must be recomputed from backfilled candles"},
    "catalyst_followthrough_24h_7d": {"status": "BLOCKED_NO_DATA", "version": "0", "horizon_s": 86400,
        "why": "catalyst tables are not exported; every scheduled session starts empty"},
    "distribution_event_24h": {"status": "BLOCKED_NO_DATA", "version": "0", "horizon_s": 86400,
        "why": "holders and wallet transactions are not exported after 2026-10-07"},
    "price_path_target_before_invalidation_7d": {"status": "EXPLORATORY", "version": "0", "horizon_s": 604800,
        "why": "136 matured events over 9 decision days; reported, never a primary claim"},
    "launch_cohort_collapse_24h": {"status": "EXPLORATORY", "version": "0", "horizon_s": 86400,
        "why": "1,422 launches first seen inside one 22 h window (2026-10-08T13:45Z to 2026-10-09T11:57Z): no temporal out-of-sample split"},
}
PRIMARY = tuple(k for k, v in TARGETS.items() if v["status"] == "PRIMARY")

_B58 = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
_HEX64 = re.compile(r"^(sha256:)?[0-9a-f]{64}$")
REQUIRED = ("forecast_id", "contract_version", "chain", "mint_address", "snapshot_hash", "decision_time_utc", "decision_time_basis",
            "target", "target_version", "horizon_seconds", "position_usd", "probability", "prediction_status", "abstain_reasons",
            "uncertainty_interval", "base_rate", "calibration_reference", "training_cutoff_utc", "model_id", "model_sha",
            "feature_set_sha", "data_snapshot_sha", "cohort", "evidence_refs", "backtest_status", "backtest_assessment_ref",
            "execution_stress_assessment_ref", "behavioral_scenarios", "caveats", "is_fixture", "generated_at_utc")


class ContractError(ValueError):
    pass


def canon(o: Any) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)


def sha(o: Any) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


def registry_sha256() -> str:
    """Fingerprint of the frozen registry and acceptance constants (recorded in DECISIONS.md at pre-registration)."""
    return sha({"registry_version": REGISTRY_VERSION, "targets": TARGETS, "acceptance": ACCEPTANCE})


def enabled(config_path: str | Path | None = None) -> bool:
    """Feature flag. OFF unless data/config.json (gitignored, per machine) says {"predictive": {"enabled": true}}."""
    if config_path is None:
        from ..db import DATA_DIR
        config_path = DATA_DIR / "config.json"
    p = Path(config_path)
    if not p.exists():
        return False
    try:
        cfg = json.loads(p.read_text())
    except (OSError, ValueError):
        return False
    return (cfg.get(FLAG_SECTION) or {}).get("enabled") is True


def backtest_status(installed: dict[str, bool] | None = None) -> str:
    """BACKTEST_NOT_AVAILABLE unless an importable engine exists; even then UNVERIFIED until a phase verifies it (PI-D-006).
    A prompt-package ZIP is documentation, not an engine, and is not looked for."""
    if installed is None:
        import importlib.util
        installed = {}
        for m in BACKTEST_MODULES:
            try:
                installed[m] = importlib.util.find_spec(m) is not None
            except (ImportError, ValueError):
                installed[m] = False
    return "UNVERIFIED" if any(installed.values()) else BACKTEST_NOT_AVAILABLE


def parse_utc(s: Any) -> float:
    if not isinstance(s, str) or not s.endswith("Z"):
        raise ContractError(f"time {s!r} must be an ISO 8601 UTC string ending in Z")
    try:
        return datetime.fromisoformat(s[:-1] + "+00:00").astimezone(timezone.utc).timestamp()
    except ValueError as e:
        raise ContractError(f"time {s!r} is not ISO 8601: {e}")


def forecast_id(chain: str, mint: str, snapshot_hash: str, target: str, target_version: str, horizon_s: int, model_sha: str | None) -> str:
    return "fc_" + sha([chain, mint, snapshot_hash, target, target_version, int(horizon_s), model_sha or "none"])[:32]


def reference_candle(candles: list, decision_time: float, *, period_s: int = 300, max_age_s: int = 3600,
                     provider_lag_s: float | None = None) -> list | None:
    """Registry reference price P0 (CC-01): the newest candle whose end plus the provider lag is at or before the decision time
    and whose end is within max_age_s of it. A candle that closed after the decision, or too recently to have been served,
    never decides eligibility. Rows are GeckoTerminal ohlcv_list rows [start, open, high, low, close, volume]."""
    if provider_lag_s is None:
        from ..social.replay_sources import PROVIDER_LAG
        provider_lag_s = PROVIDER_LAG["geckoterminal-ohlcv"]
    best = None
    for c in candles:
        end = float(c[0]) + period_s
        if end + provider_lag_s <= decision_time and end >= decision_time - max_age_s and (best is None or c[0] > best[0]):
            best = c
    return best


def path_candles(candles: list, decision_time: float, horizon_s: int, *, period_s: int = 300, lag_s: int = 300) -> list:
    """Registry path: candles that start at or after t_entry and end at or before t_entry + horizon. The candle holding t_entry is
    never part of the path (no same-candle entry, P06)."""
    t_entry = decision_time + lag_s
    return sorted((c for c in candles if float(c[0]) >= t_entry and float(c[0]) + period_s <= t_entry + horizon_s), key=lambda c: c[0])


def label_matures_at(target: str, decision_time: float) -> float:
    """Earliest time a label of this target can be read: entry lag, horizon, the confirmation window and the fetch margin."""
    t = TARGETS[target]
    return decision_time + t.get("execution_lag_s", 300) + t["horizon_s"] + t.get("confirm_s", 0) + t.get("fetch_margin_s", 900)


def label_state(target: str, decision_time: float, as_of: float) -> str:
    return "PENDING" if as_of < label_matures_at(target, decision_time) else "MATURED"


def assert_scorable(outcome: dict, as_of: float) -> None:
    """A pending label is never scored, and never as a negative (P05)."""
    if outcome.get("label") not in (0, 1):
        raise ContractError(f"outcome {outcome.get('forecast_id')} has no binary label ({outcome.get('label_status')}): not scorable")
    if label_state(outcome["target"], outcome["decision_time"], as_of) == "PENDING" or outcome.get("label_status") == "PENDING":
        raise ContractError(f"outcome {outcome.get('forecast_id')} is PENDING at {as_of}: P05, a pending label cannot be scored")
    if outcome.get("label_observed_at") is None or outcome["label_observed_at"] < label_matures_at(outcome["target"], outcome["decision_time"]):
        raise ContractError(f"outcome {outcome.get('forecast_id')} was read before its label matured")


def _num01(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and 0.0 <= x <= 1.0


def validate(doc: dict, *, model_card: dict | None = None, backtest: str | None = None) -> list[str]:
    """Return the list of contract violations (empty: well formed). Format only; accuracy is never checked here."""
    errs: list[str] = []
    if not isinstance(doc, dict):
        return ["document is not an object"]
    for k in REQUIRED:
        if k not in doc:
            errs.append(f"missing field {k}")
    for k in doc:
        if k.lower() in FORBIDDEN_KEYS:
            errs.append(f"forbidden field {k}: a forecast is not a score, rank, signal or order")
    if errs:
        return errs
    if doc["contract_version"] != CONTRACT_VERSION:
        errs.append(f"contract_version {doc['contract_version']!r} is not {CONTRACT_VERSION}")
    tgt = TARGETS.get(doc["target"])
    if tgt is None:
        return errs + [f"unknown target {doc['target']!r}"]
    if doc["target_version"] != tgt["version"]:
        errs.append(f"target_version {doc['target_version']!r} is not the registered {tgt['version']!r}")
    if doc["horizon_seconds"] != tgt["horizon_s"]:
        errs.append(f"horizon_seconds {doc['horizon_seconds']} is not the registered {tgt['horizon_s']}")
    if doc["decision_time_basis"] not in DECISION_TIME_BASES:
        errs.append(f"decision_time_basis {doc['decision_time_basis']!r}: decision time must be an export commit or a capture time (PI-D-011)")
    try:
        dt_ = parse_utc(doc["decision_time_utc"])
        gen = parse_utc(doc["generated_at_utc"])
        if gen < dt_:
            errs.append("generated_at_utc is before decision_time_utc")
    except ContractError as e:
        errs.append(str(e))
        dt_ = None
    if not _HEX64.match(str(doc["snapshot_hash"])):
        errs.append("snapshot_hash must be a sha256 hex digest")
    expect = forecast_id(doc["chain"], doc["mint_address"], doc["snapshot_hash"], doc["target"], doc["target_version"],
                         doc["horizon_seconds"], doc["model_sha"])
    if doc["forecast_id"] != expect:
        errs.append(f"forecast_id is not derived from its inputs (expected {expect}); idempotency key broken (P35)")
    bt = backtest if backtest is not None else backtest_status()
    if doc["backtest_status"] not in BACKTEST_STATUSES:
        errs.append(f"backtest_status {doc['backtest_status']!r} is not one of {BACKTEST_STATUSES}")
    elif doc["backtest_status"] != bt:
        errs.append(f"backtest_status {doc['backtest_status']!r} disagrees with the installed state {bt!r} (P34)")
    if doc["backtest_assessment_ref"] is not None and bt != "VERIFIED":
        errs.append(f"backtest_assessment_ref given while backtesting is {bt}: no combined stress claim without a verified engine (P34)")
    if doc["execution_stress_assessment_ref"] is not None and bt != "VERIFIED":
        errs.append(f"execution_stress_assessment_ref given while backtesting is {bt} (P34)")
    for s in doc["behavioral_scenarios"] or []:
        if not isinstance(s, dict) or any(k in s for k in ("probability", "likelihood", "confidence_pct")):
            errs.append("a behavioral scenario carries a probability: simulated agreement is not a likelihood (P27)")
    st = doc["prediction_status"]
    if st not in PREDICTION_STATUSES:
        return errs + [f"prediction_status {st!r} is not one of {PREDICTION_STATUSES}"]
    if st == "ABSTAIN":
        rs = doc["abstain_reasons"]
        if not rs or not isinstance(rs, list) or any(r not in ABSTAIN_REASONS for r in rs):
            errs.append(f"ABSTAIN needs one or more named reasons from {ABSTAIN_REASONS}")
        for k in ("probability", "uncertainty_interval"):
            if doc[k] is not None:
                errs.append(f"ABSTAIN carries {k}: no number when abstaining (P38)")
        return errs
    # FORECAST
    if tgt["status"] != "PRIMARY":
        errs.append(f"target {doc['target']} is {tgt['status']}: it cannot be forecast (P08 when blocked by missing historical depth)")
    if doc["abstain_reasons"]:
        errs.append("FORECAST with abstain_reasons")
    if doc["chain"] != tgt.get("scope_chain"):
        errs.append(f"chain {doc['chain']!r} is outside the target's scope {tgt.get('scope_chain')!r}")
    if doc["chain"] == "solana" and not _B58.match(str(doc["mint_address"])):
        errs.append("mint_address is not a Solana address: identity is the exact mint, never a ticker (P01)")
    p = doc["probability"]
    if not _num01(p):
        errs.append(f"probability {p!r} must be a finite number in [0, 1] (P38)")
    iv = doc["uncertainty_interval"]
    if not (isinstance(iv, list) and len(iv) == 2 and all(_num01(x) for x in iv) and iv[0] <= iv[1]):
        errs.append("uncertainty_interval must be [low, high] inside [0, 1]")
    elif _num01(p) and not (iv[0] <= p <= iv[1]):
        errs.append("probability lies outside its uncertainty_interval")
    if not _num01(doc["base_rate"]):
        errs.append("base_rate must be a finite number in [0, 1]")
    cal = doc["calibration_reference"]
    if not isinstance(cal, dict) or not isinstance(cal.get("holdout_n"), int) or cal["holdout_n"] < ACCEPTANCE["min_holdout_events"]:
        errs.append(f"calibration_reference needs holdout_n >= {ACCEPTANCE['min_holdout_events']} out-of-sample events (else INSUFFICIENT_HISTORY)")
    elif cal.get("passed") is not True:
        errs.append("calibration_reference does not record a passed calibration check (else UNCALIBRATED)")
    for k in ("model_id", "model_sha", "feature_set_sha", "data_snapshot_sha", "training_cutoff_utc"):
        if not doc[k]:
            errs.append(f"FORECAST needs {k}")
    if doc["training_cutoff_utc"] and dt_ is not None:
        try:
            if parse_utc(doc["training_cutoff_utc"]) > dt_:
                errs.append("model trained after the decision time: not an as-of forecast (P13)")
        except ContractError as e:
            errs.append(str(e))
    if tgt.get("position_usd", "x") is None:
        if doc["position_usd"] is not None:
            errs.append("price-path target with a position size: a price path is not proceeds at any size (P08)")
        if PRICE_PATH_CAVEAT not in (doc["caveats"] or []):
            errs.append(f"price-path target without the {PRICE_PATH_CAVEAT} caveat (P08)")
    if model_card is None:
        errs.append("FORECAST validated without the model card it claims (P46 cannot be checked)")
    else:
        if model_card.get("model_sha") != doc["model_sha"]:
            errs.append("model_sha differs from the model card")
        if model_card.get("feature_set_sha") != doc["feature_set_sha"]:
            errs.append("FEATURE_SCHEMA_MISMATCH: feature_set_sha differs from the one the model was trained on (P46)")
        if doc["target"] not in (model_card.get("targets") or []) or model_card.get("target_version", {}).get(doc["target"]) != doc["target_version"]:
            errs.append("model card does not cover this target and version (P46)")
    return errs
