"""Phase 13 skeptic: attempts to get a probability through the publication path (`abstention.forecast_result` and
`abstention.validate_publication`) that the frozen rules say must not be published. Fixtures only (the phase's own `world()`
fixture from tests/test_predictive_abstention.py is reused to build a legitimate SHADOW card, then attacked).

    python -B p13_publication_attacks.py CLONE OUT.json

Each attack reports: did `forecast_result` produce a FORECAST, did `validate_publication` return no error. "PUBLISHED" means
both happened (the probability would be shown); "VALIDATOR_ONLY" means a hand-built document passes the validator.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np


def main():
    clone, outp = Path(sys.argv[1]), Path(sys.argv[2])
    sys.path.insert(0, str(clone))
    sys.path.insert(0, str(clone / "tests"))
    import test_predictive_abstention as T
    from memelab.predictive import abstention as AB
    from memelab.predictive import baselines as B
    from memelab.predictive import calibration as CAL
    from memelab.predictive import contract as C
    BT = C.BACKTEST_NOT_AVAILABLE
    out = {"flag_enabled_in_this_checkout": C.enabled()}

    def publish(w, req=None, cal=None, card=None, raw=None, level=None):
        doc, rec = AB.forecast_result(req or w["req"], card=card or w["card"], level=level or w["level"], cal_card=cal or w["cal"],
                                      raw=w["raw"] if raw is None else raw, raw_why=w["raw_why"], drift_alarms=w["drift"],
                                      generated_at_utc="2026-11-01T00:00:00Z", backtest_status=BT, is_fixture=True)
        errs = AB.validate_publication(doc, model_card=card or w["card"], calibration_card=cal or w["cal"], record=rec, backtest=BT)
        return {"status": doc["prediction_status"], "probability": doc["probability"], "interval": doc["uncertainty_interval"],
                "validator_errors": errs, "reasons": doc["abstain_reasons"],
                "PUBLISHED": doc["prediction_status"] == "FORECAST" and not errs}, doc, rec

    def reseal(card):
        card = copy.deepcopy(card)
        card["card_sha"] = CAL.sha({k: v for k, v in card.items() if k != "card_sha"})
        return card

    good = T.world()
    r, gdoc, grec = publish(good)
    out["baseline_legit_fixture"] = r

    # A1 flag OFF in the real config, request says flag_on True
    out["A1_flag_off_in_config_request_says_on"] = {**r, "note": "C.enabled() is %s; neither evaluate nor validate_publication reads it" % C.enabled()}

    # A2 forged card: a below-gate world (24 calibration rows) turned CALIBRATED by editing fields and recomputing card_sha
    small = T.world(seed=3, fit_n=24)
    c = copy.deepcopy(small["cal"])
    out["A2_original_small_card"] = {"status": c["status"], "details": list(c["details"]), "fit_gate": copy.deepcopy(c["fit_gate"]),
                                     "calibration_set_n": c["calibration_set"]["n"]}
    use = CAL.rows_at(small["rows"], CAL.HOLDOUT_START)
    c["calibrator"] = CAL.fit_calibrator([q["score"] for q in use], [q["y"] for q in use], "PLATT")
    c["fit_gate"]["passed"] = True                  # shortfalls left in place: an internally inconsistent card
    c["status"], c["details"], c["level"], c["publishable"] = "CALIBRATED", [], "SHADOW", True
    c["evidence"] = {"status": "ADMISSIBLE", "n": 66, "k": 15, "check": None, "passed": True, "source": "RETROSPECTIVE_HOLDOUT"}
    forged = reseal(c)
    try:
        CAL.verify_card(forged)
        out["A2_verify_card_accepts_forged"] = True
    except Exception as e:
        out["A2_verify_card_accepts_forged"] = f"refused {e}"
    r2, d2, rec2 = publish(small, cal=forged)
    out["A2_forged_card_24_rows_spent_holdout_evidence"] = r2

    # A2b forged card from the legit one: evidence per class below 10 (n 60, k 2), status still CALIBRATED
    c = copy.deepcopy(good["cal"])
    c["evidence"] = dict(c["evidence"], n=60, k=2, check=None)
    f2 = reseal(c)
    r, doc, rec = publish(good, cal=f2)
    out["A2b_evidence_k2_via_forecast_result"] = r
    # hand-built doc on the same forged card (as a later phase that builds its own document would)
    hd = copy.deepcopy(gdoc)
    hd["calibration_reference"] = CAL.reference(f2, support_n=gdoc["calibration_reference"]["support_n"], support_k=gdoc["calibration_reference"]["support_k"])
    hd["evidence_refs"] = [x for x in hd["evidence_refs"] if not x.startswith("calibration-1")] + [f"calibration-1:{f2['card_sha']}"]
    out["A2b_evidence_k2_hand_built_doc_validator_errors"] = AB.validate_publication(hd, model_card=good["card"], calibration_card=f2, backtest=BT)

    # A2c forged card claiming its calibration set lies in the retrospective holdout window
    c = copy.deepcopy(good["cal"])
    c["calibration_set"]["first_decision_utc"] = "2026-10-18T00:00:00Z"
    c["calibration_set"]["last_decision_utc"] = "2026-10-20T00:00:00Z"
    c["calibration_set"]["rule"] = "retrospective holdout rows"
    f3 = reseal(c)
    r, _, _ = publish(good, cal=f3)
    out["A2c_card_claims_holdout_window_rows"] = r

    # A3 calibration card from the future relative to the decision (replay): request decided before the evidence matured
    w = T.world(seed=1)
    ev_cut = w["ev"]["cutoff"]
    req = dict(w["req"])
    req["decision_time"] = CAL.PROSPECTIVE_START + 0.5 * 86400       # evidence matured 4.5 days later (cutoff P0 + 5 d)
    req["avail"] = {k: req["decision_time"] - 600.0 for k in req["x"]}
    raw, why = B.predict(w["card"], [B.Example(decision_key="q", chain="solana", mint=req["mint"], decision_time=req["decision_time"],
                                                label_matures_at=req["decision_time"] + 86400, y=0, x=req["x"], avail=req["avail"])])
    w["raw"], w["raw_why"] = float(raw[0]), why[0]
    r, doc, _ = publish(w, req=req)
    out["A3_card_whose_evidence_matured_after_the_decision"] = {**r, "decision_utc": doc["decision_time_utc"],
                                                               "evidence_cutoff_utc": CAL._iso(ev_cut),
                                                               "card_stores_evidence_cutoff": "cutoff" in w["cal"]["evidence"]}

    # A4 stale model: hand-built doc with a 20-day-old training cutoff
    hd = copy.deepcopy(gdoc)
    mc = dict(good["card"], training_cutoff_utc="2026-09-01T00:00:00Z")
    hd["training_cutoff_utc"] = "2026-09-01T00:00:00Z"
    out["A4_stale_model_validator_errors"] = [e for e in AB.validate_publication(hd, model_card=mc, calibration_card=good["cal"], backtest=BT) if "STALE" in e or "trained" in e]

    # A5 non-finite and out-of-range numbers in a hand-built FORECAST
    a5 = {}
    for name, val in (("nan", float("nan")), ("np_nan", np.float64("nan")), ("inf", float("inf")), ("neg", -0.1), ("big", 1.1),
                      ("bool", True), ("str", "0.5"), ("tiny", 0.001)):
        hd = copy.deepcopy(gdoc)
        hd["probability"] = val
        try:
            e = AB.validate_publication(hd, model_card=good["card"], calibration_card=good["cal"], backtest=BT)
        except Exception as ex:
            e = [f"raised {type(ex).__name__}"]
        a5[name] = bool(e)
    hd = copy.deepcopy(gdoc)
    hd["uncertainty_interval"] = [float("nan"), 0.9]
    a5["interval_nan"] = bool(AB.validate_publication(hd, model_card=good["card"], calibration_card=good["cal"], backtest=BT))
    hd = copy.deepcopy(gdoc)
    hd["base_rate"] = float("nan")
    a5["base_rate_nan"] = bool(AB.validate_publication(hd, model_card=good["card"], calibration_card=good["cal"], backtest=BT))
    out["A5_refused"] = a5

    # A5b forged probability inside an interval that covers the support Wilson (calibrated point not recomputed, PI-D-068)
    hd = copy.deepcopy(gdoc)
    lo, hi = hd["uncertainty_interval"]
    hd["probability"] = min(0.99, hi)
    out["A5b_point_moved_to_interval_edge_validator_errors"] = AB.validate_publication(hd, model_card=good["card"], calibration_card=good["cal"], backtest=BT)
    out["A5b_point_true_vs_forged"] = [gdoc["probability"], hd["probability"]]

    # A6 flat predictions on the evidence (rule 8 names evidence too): calibration set not flat, evidence scores constant
    w = T.world(seed=1)
    ev = copy.deepcopy(w["ev"])
    med = float(np.median([q["score"] for q in w["rows"]]))
    for q in ev["rows"]:
        q["score"] = med
    try:
        cflat = CAL.build_card(T.T1, w["card"], w["rows"], T.H, level="SHADOW", evidence=ev, is_fixture=True)
        out["A6_flat_evidence_card"] = {"status": cflat["status"], "details": cflat["details"],
                                        "evidence_passed": cflat["evidence"]["passed"],
                                        "calibration_set_flat": cflat["degeneracy"]["flat"]}
        r, _, _ = publish(w, cal=cflat, raw=med)
        out["A6_flat_evidence_publish"] = r
    except Exception as e:
        out["A6_flat_evidence_card"] = f"raised {type(e).__name__}: {e}"

    # A7 SHADOW label removed from a legit doc
    hd = copy.deepcopy(gdoc)
    hd["caveats"] = [x for x in hd["caveats"] if x != AB.SHADOW_CAVEAT]
    out["A7_shadow_label_missing_refused"] = bool(AB.validate_publication(hd, model_card=good["card"], calibration_card=good["cal"], record=grec, backtest=BT))
    # A7b level relabelled VALIDATED_EXPERIMENTAL on a resealed card: no caveat needed any more
    c = copy.deepcopy(good["cal"])
    c["level"] = "VALIDATED_EXPERIMENTAL"
    f4 = reseal(c)
    r, doc, _ = publish(good, cal=f4, level="VALIDATED_EXPERIMENTAL")
    out["A7b_card_level_relabelled_validated"] = {**r, "shadow_caveat_present": AB.SHADOW_CAVEAT in doc["caveats"]}

    # A8 abstention reasons dropped: an ABSTAIN doc whose reason list is cut, without and with its record
    w = T.world(seed=1, level="ABSTAIN")
    w["req"] = dict(w["req"], flag_on=False, position_usd=100.0)
    doc, rec = AB.forecast_result(w["req"], card=w["card"], level="ABSTAIN", cal_card=w["cal"], raw=w["raw"], raw_why=w["raw_why"],
                                  generated_at_utc="2026-11-01T00:00:00Z", backtest_status=BT, is_fixture=True)
    hd = copy.deepcopy(doc)
    hd["abstain_reasons"] = hd["abstain_reasons"][:1]
    out["A8_reasons_cut_no_record_errors"] = AB.validate_publication(hd, model_card=w["card"], calibration_card=w["cal"], backtest=BT)
    out["A8_reasons_cut_with_record_errors"] = AB.validate_publication(hd, model_card=w["card"], calibration_card=w["cal"], record=rec, backtest=BT)
    rr = copy.deepcopy(rec)
    rr["conditions"] = rr["conditions"][:0] + [c for c in rec["conditions"] if c["reason"] in hd["abstain_reasons"]]
    rr["reasons"] = AB.reasons_of(rr["conditions"])
    rr["record_id"] = AB.sha({k: v for k, v in rr.items() if k != "record_id"})
    hd["evidence_refs"] = [f"abstention-1:{rr['record_id']}"] + [x for x in hd["evidence_refs"] if not x.startswith("abstention-1")]
    out["A8_reasons_cut_with_resealed_record_errors"] = AB.validate_publication(hd, model_card=w["card"], calibration_card=w["cal"], record=rr, backtest=BT)
    out["A8_original_reasons"] = doc["abstain_reasons"]

    # A9 P23/P24: interval width against support at a fixed observed rate, and the hull with a confident Platt point
    widths = []
    for n in (20, 40, 80, 160, 320, 640):
        lo, hi = CAL.interval(0.30, 0.30, n, int(round(0.25 * n)))
        widths.append([n, hi - lo])
    out["A9_interval_width_by_support"] = widths
    out["A9_non_increasing"] = all(widths[i][1] >= widths[i + 1][1] for i in range(len(widths) - 1))
    out["A9_point_far_from_bin_rate"] = CAL.interval(0.95, 0.95, 25, 10)

    outp.write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n")
    for k, v in out.items():
        print(k, ":", json.dumps(v, default=str)[:400])


if __name__ == "__main__":
    main()
