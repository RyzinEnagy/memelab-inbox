"""CX-S13 (Phase 13 skeptic counterexample): flat predictions on the admissible evidence still give a CALIBRATED card.

Wrong-but-plausible situation: in the prospective period the champion's inputs break (for example a required column is imputed
to its training mean by an upstream change), so every prospective score is the same number. The development calibration set
is not flat, so the fit gate passes and a calibrator is fitted honestly. The prospective evidence (all one score) is then
checked with the frozen tolerance: in the large the mean is close to the observed rate, and every quantile bin has the same
mean prediction, so the check passes. The card becomes CALIBRATED, and forecasts are published for any raw score inside the
calibration range, although the evidence tested only one point of the calibration curve.

Pre-registration rule 8 (ACCEPTANCE_CHECKLIST.md at 0fdf698): "FLAT when max minus min of the predictions is at most 1e-9
(calibration set, evidence or a fixture stream): UNCALIBRATED, detail DEGENERATE_FLAT_PREDICTIONS." The code checks the
calibration set only (`build_card` -> `degeneracy(use)`); `_evidence` never checks.

    python -B p13_cx_s13_flat_evidence.py CLONE OUT.json
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
    from memelab.predictive import calibration as CAL
    from memelab.predictive import contract as C
    BT = C.BACKTEST_NOT_AVAILABLE
    out = {}
    w = T.world(seed=1)
    out["honest_card"] = {"status": w["cal"]["status"], "method": w["cal"]["calibrator"]["method"]}
    ev = copy.deepcopy(w["ev"])
    scores = np.array([r["score"] for r in w["rows"]])
    flat_value = float(np.median(scores))
    for r in ev["rows"]:
        r["score"] = flat_value
    card = CAL.build_card(T.T1, w["card"], w["rows"], T.H, level="SHADOW", evidence=ev, is_fixture=True)
    out["flat_evidence_card"] = {"status": card["status"], "details": card["details"], "evidence_passed": card["evidence"]["passed"],
                                 "evidence_n": card["evidence"]["n"], "evidence_k": card["evidence"]["k"],
                                 "evidence_score_ptp": 0.0, "calibration_set_degeneracy": card["degeneracy"],
                                 "check_in_the_large": card["evidence"]["check"]["in_the_large_ok"],
                                 "check_bins_ok": card["evidence"]["check"]["every_bin_ok"],
                                 "bin_mean_preds": [b["mean_pred"] for b in card["evidence"]["check"]["bins"]]}
    pubs = []
    for q in (0.1, 0.5, 0.9):
        raw = float(np.quantile(scores, q))
        doc, rec = AB.forecast_result(w["req"], card=w["card"], level="SHADOW", cal_card=card, raw=raw, raw_why=None,
                                      drift_alarms=[], generated_at_utc="2026-11-01T00:00:00Z", backtest_status=BT, is_fixture=True)
        errs = AB.validate_publication(doc, model_card=w["card"], calibration_card=card, record=rec, backtest=BT)
        pubs.append({"raw_quantile": q, "raw": raw, "status": doc["prediction_status"], "probability": doc["probability"],
                     "interval": doc["uncertainty_interval"], "validator_errors": errs})
    out["published_at_scores_the_evidence_never_tested"] = pubs
    out["CAUGHT_BY_CODE"] = not any(p["status"] == "FORECAST" and not p["validator_errors"] for p in pubs) or card["status"] != "CALIBRATED"
    # the repair the rule asks for, shown as a monkeypatch: evidence degeneracy turns the card UNCALIBRATED
    orig = CAL._evidence

    def patched(evidence, cal, fit_rows):
        e = orig(evidence, cal, fit_rows)
        rows = evidence.get("rows") or []
        if rows and CAL.degeneracy([r["score"] for r in rows])["flat"]:
            e = dict(e, passed=False)
        return e
    CAL._evidence = patched
    try:
        c2 = CAL.build_card(T.T1, w["card"], w["rows"], T.H, level="SHADOW", evidence=ev, is_fixture=True)
        out["with_evidence_flat_check"] = {"status": c2["status"], "details": c2["details"]}
    finally:
        CAL._evidence = orig
    outp.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps(out, indent=1)[:3000])


if __name__ == "__main__":
    main()
