"""Phase 01: mutation check of the predictive tests. Copies memelab/, tests/ and the Phase 01 acceptance document to a temporary
folder, applies one mutation at a time, and runs tests/test_predictive_contract.py and tests/test_predictive_decisions.py with bytecode
writing off. Every mutation must make at least one test fail. Never touches the checkout.

Repair pass 2 added the twelve mutations of the independent skeptic (skeptic_01_mutations.py, ten of which survived the first test
set) and mutations for the CC-02 rules (decision identity, eligibility classes, frozen acceptance plan).

    python audits/predictive-intelligence/phase_01/probes/mutation_check.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
C = "memelab/predictive/contract.py"
D = "memelab/predictive/decisions.py"
DOC = "audits/predictive-intelligence/phase_01/architecture/ACCEPTANCE_METRICS.md"
MUTATIONS = [
    # phase agent, pass 2
    ("P46 feature check removed", C, 'if model_card.get("feature_set_sha") != doc["feature_set_sha"]:', "if False:"),
    ("P34 assessment ref check removed", C, 'if doc["backtest_assessment_ref"] is not None and bt != "VERIFIED":', "if False:"),
    ("CC-01 reference may use a post-decision candle", C, "if end + lag <= decision_time and", "if end <= decision_time + 300 and"),
    ("P05 pending label scorable", C, 'if label_state(outcome["target"], outcome["decision_time"], as_of) == "PENDING" or outcome.get("label_status") == "PENDING":', "if False:"),
    ("P08 blocked target forecastable", C, 'if tgt["status"] != "PRIMARY":', "if False:"),
    ("silent barrier edit", C, "upper=1.25, lower=0.85, confirm_s=0,", "upper=1.20, lower=0.85, confirm_s=0,"),
    ("P06 path includes the entry candle", C, "if float(c[0]) >= t_entry and", "if float(c[0]) + period_s > t_entry and"),
    ("P13 future-trained model allowed", C, "            if cut > dt_:", "            if False:"),
    ("PI-D-011 decision basis check removed", C, 'if doc["decision_time_basis"] not in DECISION_TIME_BASES:', "if False:"),
    ("P38 range check removed entirely", C, "return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and 0.0 <= x <= 1.0", "return True"),
    # independent skeptic (skeptic_01_mutations.py), adapted to the current text where it moved
    ("range [0,1] dropped, finiteness and type kept", C, "math.isfinite(x) and 0.0 <= x <= 1.0", "math.isfinite(x)"),
    ("bool accepted as a probability", C, "not isinstance(x, bool) and math.isfinite(x) and 0.0", "math.isfinite(x) and 0.0"),
    ("FORECAST no longer needs training_cutoff_utc", C, '("model_id", "model_sha", "feature_set_sha", "data_snapshot_sha", "training_cutoff_utc")',
     '("model_id", "model_sha", "feature_set_sha", "data_snapshot_sha")'),
    ("FORECAST no longer needs model, feature-set or data fingerprints", C,
     '("model_id", "model_sha", "feature_set_sha", "data_snapshot_sha", "training_cutoff_utc")', '("model_id",)'),
    ("ABSTAIN may carry an interval", C, 'for k in ("probability", "uncertainty_interval"):', 'for k in ("probability",):'),
    ("generated_at before decision allowed", C, "if gen < dt_:", "if False:"),
    ("base_rate range check removed", C, 'if doc["base_rate"] is not None and not _num01(doc["base_rate"]):', "if False:"),
    ("forbidden-key check removed", C, "if any(f in str(k).lower() for f in FORBIDDEN_KEYS):", "if False:"),
    ("calibration passed flag ignored", C, 'elif cal.get("passed") is not True:', "elif False:"),
    ("ABSTAIN with NaN or 0 probability", C, "            if doc[k] is not None:", "            if doc[k] is not None and doc[k] == doc[k] and doc[k] != 0:"),
    ("existing module imports via 'from memelab import predictive'", "memelab/cli.py", "from __future__ import annotations",
     "from __future__ import annotations\nfrom memelab import predictive  # noqa"),
    ("existing module imports via importlib", "memelab/pipeline.py", "from __future__ import annotations",
     "from __future__ import annotations\nimport importlib as _il; _il.import_module('memelab.predictive.contract')  # noqa"),
    # skeptic M3 gaps closed in repair pass 2
    ("MODEL_STALE not enforced", C, '            elif dt_ - cut > ACCEPTANCE["max_model_age_s"]:', "            elif False:"),
    ("model card cutoff not compared", C, 'if model_card.get("training_cutoff_utc") != doc["training_cutoff_utc"]:', "if False:"),
    ("mint regex matches a trailing newline", C, "return _B58.fullmatch(addr) is not None", "return _B58.match(addr) is not None and addr.rstrip() == addr.rstrip('\\n')"),
    ("unknown top-level fields allowed", C, "        elif k not in REQUIRED:", "        elif False:"),
    # CC-02 F1: decision identity
    ("decision identity keyed on (mint, created_at) only", D, 'ident = (row["mint"], float(row["created_at"]), row_sha256(row))',
     'ident = (row["mint"], float(row["created_at"]), "")'),
    ("same-time tie broken by last position", D, 'key=lambda c: (c["first_visible"], c["position"]))', 'key=lambda c: (c["first_visible"], -c["position"]))'),
    ("KEY_CONFLICT never flagged", D, "            if len(sigs) > 1:", "            if False:"),
    ("revision of the newest key becomes the decision row", D, 'key=lambda c: (c["first_visible"], c["position"]))', 'key=lambda c: (-c["first_visible"], c["position"]))'),
    # CC-02 F3: eligibility
    ("vendor gap called a quiet market", C, '    return "VENDOR_OR_ROUTE_GAP"\n\n\ndef path_candles', '    return "MARKET_INACTIVE"\n\n\ndef path_candles'),
    ("quiet-route evidence accepted from a vendor-list pool", C, 'if route == "PIT_RECORDED" and any(', "if any("),
    # CC-02 F2: frozen acceptance plan, code and document
    ("Holm loosened in code", C, '"multiple_testing": {"method": "holm"', '"multiple_testing": {"method": "none"'),
    ("calibration interval loosened in code", C, '"calibration": {"interval": "wilson", "conf": 0.95', '"calibration": {"interval": "wilson", "conf": 0.999'),
    ("minimum days loosened in code", C, '"min_effective_days": 5,', '"min_effective_days": 1,'),
    ("calibration interval loosened in the document block", DOC, '"conf": 0.95,\n  "descriptive_only"', '"conf": 0.999,\n  "descriptive_only"'),
]


def run(cwd: Path) -> tuple[int, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, "-m", "pytest", "tests/test_predictive_contract.py", "tests/test_predictive_decisions.py", "-q",
                        "-p", "no:cacheprovider"], cwd=cwd, env=env, capture_output=True, text=True)
    return p.returncode, (p.stdout.strip().splitlines() or [""])[-1]


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        w = Path(td)
        for d in ("memelab", "tests"):
            shutil.copytree(ROOT / d, w / d, ignore=shutil.ignore_patterns("__pycache__"))
        (w / DOC).parent.mkdir(parents=True)
        shutil.copy2(ROOT / DOC, w / DOC)
        code, line = run(w)
        print(f"baseline: exit {code}, {line}")
        bad = 0 if code == 0 else 1
        for name, f, a, b in MUTATIONS:
            p = w / f
            orig = p.read_text()
            if a not in orig:
                print(f"{name}: NOT APPLIED (pattern missing)")
                bad += 1
                continue
            p.write_text(orig.replace(a, b, 1))
            code, line = run(w)
            ok = code != 0
            bad += 0 if ok else 1
            print(f"{name}: {'caught' if ok else 'SURVIVED'} ({line})")
            p.write_text(orig)
        print(f"mutations {len(MUTATIONS)}, survived or not applied {bad}")
        return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
