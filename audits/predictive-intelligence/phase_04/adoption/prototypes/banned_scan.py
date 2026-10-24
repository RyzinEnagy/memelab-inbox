"""Phase 04 (B3, B7): scan the prototypes and the new lab code for the defaults Phase 03 banned (ROADMAP "Known constraints
carried from Phase 03"). A hit is allowed only where this file names it as a deliberate negative control.

    python banned_scan.py OUT.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
BANNED = {
    "CalibratedClassifierCV without FrozenEstimator": r"CalibratedClassifierCV\((?!FrozenEstimator)",
    "row-gap TimeSeriesSplit": r"TimeSeriesSplit\(",
    "LightGBM lgb.cv defaults": r"\blgb\.cv\(",
    "purgedcv PurgedKFold": r"\bPurgedKFold\(",
    "purgedcv CPCV": r"CombinatorialPurgedCV\(",
    "purgedcv PurgedGroupKFold": r"PurgedGroupKFold\(",
    "MAPIE Venn-Abers port": r"VennAbersCalibrator|mapie\._venn_abers|from mapie\.calibration import",
    "cv='prefit' with a fitted Pipeline": r"cv\s*=\s*[\"']prefit[\"']",
    "river progressive_val_score (end-of-stream flush learned)": r"progressive_val_score|simulate_qa",
    "statsmodels Markov smoothed probabilities": r"smoothed_marginal_probabilities|MarkovRegression",
    "hazardous recalibrate_survival_function": r"recalibrate_survival_function",
    "lifelines k_fold_cross_validation": r"k_fold_cross_validation",
    "venn-abers estimator mode with shuffle": r"VennAbersCalibrator\(.*shuffle\s*=\s*True",
    "feast without created timestamp filter": r"get_historical_features",
    "pickle load": r"pickle\.loads?\(|joblib\.load\(",
}
EXAMPLES = {   # each rule must match its example and must not match the allowed form next to it (self-test below)
    "CalibratedClassifierCV without FrozenEstimator": ("CalibratedClassifierCV(lr, cv=None)", "CalibratedClassifierCV(FrozenEstimator(lr))"),
    "row-gap TimeSeriesSplit": ("TimeSeriesSplit(n_splits=5)", "day_walk_forward(t, m)"),
    "LightGBM lgb.cv defaults": ("lgb.cv(params, ds)", "lgb.LGBMClassifier()"),
    "purgedcv PurgedKFold": ("PurgedKFold(n_splits=5)", "WalkForwardSplit(n_splits=5)"),
    "purgedcv CPCV": ("CombinatorialPurgedCV(n_splits=6)", "WalkForwardSplit(n_splits=6)"),
    "purgedcv PurgedGroupKFold": ("PurgedGroupKFold(n_splits=5)", "WalkForwardSplit(n_splits=5)"),
    "MAPIE Venn-Abers port": ("from mapie.calibration import VennAbersCalibrator", "from mapie.risk_control import BinaryClassificationController"),
    "cv='prefit' with a fitted Pipeline": ("X(estimator=pipe, cv='prefit')", "X(estimator=pipe)"),
    "river progressive_val_score (end-of-stream flush learned)": ("evaluate.progressive_val_score(ds, m, met)", "drift.ADWIN()"),
    "statsmodels Markov smoothed probabilities": ("res.smoothed_marginal_probabilities", "res.filtered_marginal_probabilities"),
    "hazardous recalibrate_survival_function": ("recalibrate_survival_function(m)", "survival_function(m)"),
    "lifelines k_fold_cross_validation": ("k_fold_cross_validation(cph, df)", "cph.fit(df)"),
    "venn-abers estimator mode with shuffle": ("VennAbersCalibrator(estimator=m, shuffle=True)", "VennAbers()"),
    "feast without created timestamp filter": ("store.get_historical_features(entity_df)", "store.get_online_features()"),
    "pickle load": ("pickle.load(fh)", "json.load(fh)"),
}
NEGATIVE_CONTROLS = {("splitter_check.py", "row-gap TimeSeriesSplit")}
SELF = {"banned_scan.py"}


def main(out: str) -> None:
    for name, (bad, good) in EXAMPLES.items():
        assert re.search(BANNED[name], bad) and not re.search(BANNED[name], good), f"self-test failed for rule {name}"
    assert set(EXAMPLES) == set(BANNED)
    files = sorted(HERE.glob("*.py")) + [REPO / "memelab/predictive/runtime.py", REPO / "tests/test_predictive_runtime.py"]
    hits, allowed = [], []
    for f in files:
        if f.name in SELF:
            continue
        for i, line in enumerate(f.read_text().splitlines(), 1):
            for name, rx in BANNED.items():
                if re.search(rx, line):
                    rec = {"file": str(f.relative_to(REPO)), "line": i, "rule": name}
                    (allowed if (f.name, name) in NEGATIVE_CONTROLS else hits).append(rec)
    res = {"files_scanned": len(files) - len(SELF & {f.name for f in files}), "rules": len(BANNED), "hits": hits,
           "negative_controls": allowed}
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({"files_scanned": res["files_scanned"], "hits": len(hits), "negative_controls": len(allowed)}))
    if hits:
        print(json.dumps(hits, indent=1))
        raise SystemExit(1)


if __name__ == "__main__":
    main(sys.argv[1])
