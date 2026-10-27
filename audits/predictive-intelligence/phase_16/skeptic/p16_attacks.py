"""Phase 16 skeptic attacks on registry-1 (fixtures and temp copies only; never writes into the repo).
Usage: python -B p16_attacks.py <repo clone> <out.json>"""
import copy, json, math, sys, tempfile
from pathlib import Path
REPO = Path(sys.argv[1]); OUT = Path(sys.argv[2])
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tests"))
import numpy as np
from memelab.predictive import registry as R, contract as C, abstention as AB, calibration as CAL
import test_predictive_registry as TR
res = {}
def attempt(name, fn):
    try:
        out = fn(); res[name] = {"accepted": True, "detail": out}
    except Exception as e:
        res[name] = {"accepted": False, "refused_by": type(e).__name__, "detail": str(e)[:200]}
AUD = REPO / "audits/predictive-intelligence/phase_16/registry"
real = R.read_entries(AUD / "entries")
log_text = (AUD / "REGISTRY_LOG.jsonl").read_text(); events = R.read_log(log_text)
T1 = "price_path_target_before_invalidation_24h"
byc = {(e["target"], e["family"]["candidate"]): e for e in real.values()}
b0, b2, b1 = byc[(T1, "P07_B0")], byc[(T1, "P07_B2")], byc[(T1, "P07_B1")]
refs = {"base_rate": b0["entry_id"], "simple_model": b2["entry_id"]}
AS = "2026-10-28T00:00:00Z"
def rehash(e):
    e["promotion"] = R.promotion_decision(e["facts"]); e["registry_status"] = R.registry_status(e["promotion"]["level"], e["role"])
    e["publishable"] = R.publishable(e); e["entry_id"] = R.sha({k: v for k, v in e.items() if k != "entry_id"}); return e
def forge_b2(e):
    f = copy.deepcopy(e)
    f["facts"]["retrospective"].update({"bss": 0.05, "calibration_in_the_large_ok": True, "calibration_every_bin_ok": True})
    f["facts"]["calibration"] = {"status": "CALIBRATED", "evidence_n": 60, "evidence_k": 12, "evidence_source": "PROSPECTIVE_HOLDOUT", "evidence_status": "ADMISSIBLE"}
    f["calibration"] = {**f["calibration"], "status": "CALIBRATED", "level": "SHADOW"}
    return rehash(f)
fb2 = forge_b2(b2)
res["forged_b2_level"] = fb2["promotion"]["level"]
attempt("A0_forged_b2_passes_verify_entry", lambda: bool(R.verify_entry(fb2)))
ents = {**real, fb2["entry_id"]: fb2}
# A1: pin a NO_GO real entry, a reference as champion
attempt("A1_pin_NO_GO_B1_as_champion", lambda: R.pin_event(real, T1, mode="CHAMPION", champion=b1["entry_id"], references=refs, reasons=[], as_of_utc=AS, verify=lambda e: None))
attempt("A1b_pin_real_B2_ABSTAIN_as_champion", lambda: R.pin_event(real, T1, mode="CHAMPION", champion=b2["entry_id"], references=refs, reasons=[], as_of_utc=AS, verify=lambda e: None))
# A2: swap a NO_GO card in as a reference
attempt("A2_NO_GO_B1_as_reference", lambda: R.pin_event(real, T1, mode="NO_VIABLE_CHAMPION", champion=None, references={"base_rate": b1["entry_id"], "simple_model": b2["entry_id"]}, reasons=[], as_of_utc=AS))
attempt("A2b_T1b_B2_as_T1_reference", lambda: R.pin_event(real, T1, mode="NO_VIABLE_CHAMPION", champion=None, references={"base_rate": b0["entry_id"], "simple_model": byc[("price_path_target_before_invalidation_6h", "P07_B2")]["entry_id"]}, reasons=[], as_of_utc=AS))
# A3: forged facts, pinned with no verify / real verify / the registry's own verify_entry as verifier (plausible integrator mistake)
attempt("A3a_forged_pin_no_verify", lambda: R.pin_event(ents, T1, mode="CHAMPION", champion=fb2["entry_id"], references=refs, reasons=[], as_of_utc=AS))
attempt("A3b_forged_pin_verify_is_verify_entry", lambda: R.pin_event(ents, T1, mode="CHAMPION", champion=fb2["entry_id"], references={"base_rate": b0["entry_id"], "simple_model": b2["entry_id"]}, reasons=[], as_of_utc=AS, verify=R.verify_entry)["mode"])
def served_forged():
    pin = R.pin_event(ents, T1, mode="CHAMPION", champion=fb2["entry_id"], references=refs, reasons=["forged"], as_of_utc=AS, verify=R.verify_entry)
    ev = R.read_log(log_text) ; ev = ev + R.chain_events([pin], prev=R.line_sha(R.canon(ev[-1])), start_seq=len(ev))
    sv = R.serve(ev, ents, T1, C.parse_utc("2026-10-29T00:00:00Z"), runtime=TR.runtime(), verify=R.verify_entry)
    return {"use_champion": sv["use_champion"], "forecast_inputs": sv["forecast_inputs"], "blocking": sv["blocking"]}
attempt("A3c_forged_served_with_verify_entry", served_forged)
# A3d: forged champion entering the publication path, flag ON (temp config), real UNCALIBRATED calibration card
def publish_forged():
    sv = served_forged(); fi = sv["forecast_inputs"]
    cal = CAL.loads((REPO / "audits/predictive-intelligence/phase_13/artifacts/T1_24h/CALIBRATION_CARD.json").read_text())
    card = json.loads((REPO / fb2["card_path"]).read_text())
    with tempfile.TemporaryDirectory() as d:
        cfg = Path(d) / "config.json"; cfg.write_text(json.dumps({"predictive": {"enabled": True}}))
        req = {"chain": "solana", "mint": "4kjruqGHDsSqkMdFfCjV7Vb62HPFhtXyWc2t6JpQzDnz", "target": T1, "decision_time": C.parse_utc("2026-10-29T00:00:00Z"),
               "decision_time_basis": "EXPORT_COMMIT", "snapshot_hash": "a" * 64, "flag_on": True, "pool_point_in_time": True, "route": "PIT_RECORDED",
               "eligibility": "ELIGIBLE", "position_usd": None, "backtest_required": False,
               "x": {"thesis_log1p_liquidity_usd": 11.0, "thesis_log1p_mcap_usd": 15.0, "thesis_log1p_vol_24h_usd": 13.0, "thesis_fatal_present": 0.0, "log1p_token_age_days": 2.0},
               "avail": {}, "feature_set_sha": card["feature_set_sha"], "new_mint": False, "token_history_rows": 50}
        doc, rec = AB.forecast_result(req, card=card, level=fi["level"], cal_card=cal, raw=0.3, generated_at_utc="2026-10-29T00:00:01Z", config_path=cfg)
        return {"status": doc["prediction_status"], "probability": doc["probability"], "reasons": doc.get("abstain_reasons")}
attempt("A3d_forged_champion_to_document_flag_on", publish_forged)
# A4: edit pins: append a CHAMPION pin for NO_GO B1 to a copy of the real log with a valid chain
def edited_log():
    pin = {"kind": "PIN", "as_of_utc": AS, "target": T1, "mode": "CHAMPION", "champion": b1["entry_id"], "champion_inference_sha": b1["inference"]["outputs_sha"], "references": refs, "reasons": ["edited"]}
    ev = events + R.chain_events([pin], prev=R.line_sha(R.canon(events[-1])), start_seq=len(events))
    return R.resolve(ev, real, T1, C.parse_utc("2026-10-29T00:00:00Z"))
attempt("A4_edited_log_champion_NO_GO", edited_log)
def rewritten_line():
    lines = log_text.splitlines(); j = json.loads(lines[-1]); j["mode"] = "CHAMPION"; lines[-1] = R.canon(j)
    return len(R.read_log("\n".join(lines) + "\n"))
attempt("A4b_rewritten_last_pin_line", rewritten_line)
# A5: recompute ids after changing a level directly (no facts change)
def direct_level():
    e = copy.deepcopy(b2); e["promotion"]["level"] = "SHADOW"; e["registry_status"] = "PROMOTED_SHADOW"; e["entry_id"] = R.sha({k: v for k, v in e.items() if k != "entry_id"})
    return R.verify_entry(e)["promotion"]["level"]
attempt("A5_direct_level_edit_rehashed", direct_level)
# A6: stale replay past 2026-10-31 with a fixture champion
fx, steps = TR.fixture_registry(); fev = R.chain_events(steps["initial"])
for tt in ("2026-10-31T00:00:00Z", "2026-10-31T00:00:01Z", "2026-12-01T00:00:00Z"):
    s = R.serve(fev, fx, TR.FX_TARGET, C.parse_utc(tt), runtime=TR.runtime(), verify=TR.FX_VERIFY)
    res[f"A6_fixture_champion_served_at_{tt}"] = {"use_champion": s["use_champion"], "blocking": [b["state"] for b in s["blocking"]]}
rr = R.reference_record(b2, decision_key="k", decision_time=C.parse_utc("2026-12-01T00:00:00Z"), number=0.2, why="", as_of_utc="2026-12-01T00:00:00Z")
res["A6b_stale_reference_record"] = {"states": rr["states"], "published": rr["published"], "is_document": R.is_document(rr)}
# A7: P46 runtime change in transform code only (definitions unchanged): compare runtime facts before/after monkeypatch of features internals
from memelab.predictive import features as F
rt0 = TR.runtime()
orig = F._num_field
def patched(snap, key, *, log1p=False, log=False, allow_negative=False):
    v, why = orig(snap, key, log1p=log1p, log=log, allow_negative=allow_negative)
    return ((v * 1.5) if (v is not None and log1p) else v, why)
F._num_field = patched
rt1 = TR.runtime()
res["A7_transform_code_change_runtime_equal"] = rt0 == rt1
res["A7_compatibility_states_after_code_change"] = {k: R.compatibility(e, runtime=rt1) for k, e in list(real.items())[:3]}
s = R.serve(fev, fx, TR.FX_TARGET, C.parse_utc("2026-10-23T00:00:00Z"), runtime=rt1, verify=TR.FX_VERIFY)
res["A7_fixture_champion_served_after_transform_change_without_inference"] = {"use_champion": s["use_champion"], "blocking": s["blocking"]}
F._num_field = orig
# A8: P38 malformed outputs
for name, num, why in [("nan_no_reason", float("nan"), ""), ("inf", float("inf"), ""), ("neg", -0.1, ""), ("over", 1.1, ""),
                       ("np32_nan", np.float32("nan"), ""), ("string", "0.5", ""), ("bool", True, ""), ("np_int", np.int64(1), ""),
                       ("nan_with_reason", float("nan"), "OOD"), ("neg_zero", -0.0, ""), ("np_float_over", np.float64(1.0000001), ""),
                       ("none_with_number_reason", None, "x")]:
    attempt(f"A8_inference_{name}", lambda n=num, w=why: R.inference_rows([("k", n, w)]))
attempt("A8b_reference_record_1.5", lambda: R.reference_record(b2, decision_key="k", decision_time=C.parse_utc("2026-10-28T00:00:00Z"), number=1.5, why="", as_of_utc=AS))
def nan_fact():
    e = copy.deepcopy(b2); e["facts"]["retrospective"]["bss"] = float("nan"); return rehash(e)
attempt("A8c_nan_in_facts", nan_fact)
# A9: P27 agent-agreement fields
def agent_field(where):
    e = copy.deepcopy(b2)
    if where == "facts": e["facts"]["agent_agreement_share"] = 0.9
    elif where == "evidence": e["evidence"]["mirofish"] = {"agent_vote_share": 0.9}
    elif where == "risk": e["risk_flags"] = sorted(e["risk_flags"] + ["AGENTS_AGREE_90PCT"])
    elif where == "model_id_alias": e["facts"]["source"] = R.SOURCE; e["family"]["candidate"] = "P07_B2"; e["facts"]["swarm"] = {"p": 0.9}
    e = rehash(e); R.verify_entry(e); return {"level": e["promotion"]["level"], "publishable": e["publishable"]}
for w in ("facts", "evidence", "risk", "model_id_alias"):
    attempt(f"A9_agent_field_in_{w}", lambda w=w: agent_field(w))
attempt("A9b_member_column_agent_share", lambda: R.check_members({"B2": ["thesis_log1p_liquidity_usd"], "S9": ["agent_vote_share"]}))
attempt("A9c_member_named_mirofish", lambda: R.check_members({"B2": ["thesis_log1p_liquidity_usd"], "MiroFish_S": ["sc_channels_n"]}))
# A10: every-bin calibration not computed on a large holdout passes the SHADOW bin check
f = TR.facts("B2", level="SHADOW"); f["retrospective"]["calibration_every_bin_ok"] = None; f["retrospective"]["n"] = 66
res["A10_every_bin_None_at_66_events_level"] = R.promotion_decision(f)["level"]
OUT.write_text(json.dumps(res, indent=1, sort_keys=True, default=str))
for k, v in sorted(res.items()):
    print(k, "->", json.dumps(v, default=str)[:230])
