"""CX-S16: a forged-facts B2 entry pinned and served through a plausible but wrong `verify` callback (verify_sources only).
Usage: python -B p16_cx_s16.py <repo clone> <out.json> [--commit-copy <throwaway repo copy>]"""
import copy, json, subprocess, sys, tempfile
from pathlib import Path
REPO = Path(sys.argv[1]); OUT = Path(sys.argv[2])
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tests"))
from memelab.predictive import registry as R, contract as C, abstention as AB, calibration as CAL
import test_predictive_registry as TR
REG = REPO / "audits/predictive-intelligence/phase_16/registry"
real = R.read_entries(REG / "entries"); events = R.read_log((REG / "REGISTRY_LOG.jsonl").read_text())
T1 = "price_path_target_before_invalidation_24h"
by = {(e["target"], e["family"]["candidate"]): e for e in real.values()}
b0, b2 = by[(T1, "P07_B0")], by[(T1, "P07_B2")]
f = copy.deepcopy(b2)
f["facts"]["retrospective"].update({"bss": 0.05, "calibration_in_the_large_ok": True, "calibration_every_bin_ok": True})
f["facts"]["calibration"] = {"status": "CALIBRATED", "evidence_n": 60, "evidence_k": 12, "evidence_source": "PROSPECTIVE_HOLDOUT", "evidence_status": "ADMISSIBLE"}
f["calibration"] = {**f["calibration"], "status": "CALIBRATED", "level": "SHADOW"}
f["promotion"] = R.promotion_decision(f["facts"]); f["registry_status"] = R.registry_status(f["promotion"]["level"], f["role"])
f["publishable"] = R.publishable(f); f["entry_id"] = R.sha({k: v for k, v in f.items() if k != "entry_id"})
ents = {**real, f["entry_id"]: f}
refs = {"base_rate": b0["entry_id"], "simple_model": b2["entry_id"]}
read = lambda p: (REPO / p).read_bytes()
src_check = lambda e: R.verify_sources(e, read)          # the plausible wrong verifier: file hashes only
out = {"forged_level": f["promotion"]["level"], "forged_publishable_flag": f["publishable"]}
out["verify_entry_passes"] = bool(R.verify_entry(f))
out["verify_sources_passes"] = R.verify_sources(f, read)
pin = R.pin_event(ents, T1, mode="CHAMPION", champion=f["entry_id"], references=refs, reasons=["CX-S16"], as_of_utc="2026-10-28T00:00:00Z", verify=src_check)
ev = events + R.chain_events([pin], prev=R.line_sha(R.canon(events[-1])), start_seq=len(events))
sv = R.serve(ev, ents, T1, C.parse_utc("2026-10-29T00:00:00Z"), runtime=TR.runtime(), verify=src_check)
out["pinned_mode"] = pin["mode"]; out["served"] = {"use_champion": sv["use_champion"], "level": sv["forecast_inputs"]["level"], "blocking": sv["blocking"]}
cal = CAL.loads((REPO / "audits/predictive-intelligence/phase_13/artifacts/T1_24h/CALIBRATION_CARD.json").read_text())
card = json.loads((REPO / f["card_path"]).read_text())
with tempfile.TemporaryDirectory() as d:
    cfg = Path(d) / "config.json"; cfg.write_text(json.dumps({"predictive": {"enabled": True}}))
    req = {"chain": "solana", "mint": "4kjruqGHDsSqkMdFfCjV7Vb62HPFhtXyWc2t6JpQzDnz", "target": T1, "decision_time": C.parse_utc("2026-10-29T00:00:00Z"),
           "decision_time_basis": "EXPORT_COMMIT", "snapshot_hash": "a" * 64, "flag_on": True, "pool_point_in_time": True, "route": "PIT_RECORDED",
           "eligibility": "ELIGIBLE", "position_usd": None, "backtest_required": False,
           "x": {"thesis_log1p_liquidity_usd": 11.0, "thesis_log1p_mcap_usd": 15.0, "thesis_log1p_vol_24h_usd": 13.0, "thesis_fatal_present": 0.0, "log1p_token_age_days": 2.0},
           "avail": {}, "feature_set_sha": card["feature_set_sha"], "new_mint": False, "token_history_rows": 50}
    doc, rec = AB.forecast_result(req, card=card, level=sv["forecast_inputs"]["level"], cal_card=cal, raw=0.3, generated_at_utc="2026-10-29T00:00:01Z", config_path=cfg)
    out["document"] = {"status": doc["prediction_status"], "probability": doc["probability"], "reasons": doc["abstain_reasons"],
                       "model_not_promoted_condition": [c for c in rec["conditions"] if c.get("code") in ("MODEL_NOT_PROMOTED", "UNCALIBRATED") and c.get("holds")] if isinstance(rec.get("conditions"), list) else None}
if len(sys.argv) > 4 and sys.argv[3] == "--commit-copy":
    cp = Path(sys.argv[4]); R.write_entry(cp / "audits/predictive-intelligence/phase_16/registry/entries", f)
    r = subprocess.run([sys.executable, "-B", "-m", "pytest", "tests/test_predictive_phase16_outputs.py", "-q", "-p", "no:cacheprovider"], cwd=cp, capture_output=True, text=True)
    out["committed_copy_output_tests"] = [l for l in r.stdout.splitlines() if l.startswith("FAILED") or "passed" in l or "failed" in l][-6:]
    (cp / "audits/predictive-intelligence/phase_16/registry/entries" / f"{f['entry_id']}.json").unlink()
OUT.write_text(json.dumps(out, indent=1, default=str)); print(json.dumps(out, indent=1, default=str)[:2500])
