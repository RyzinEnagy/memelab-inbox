"""Phase 01: mutation check of the contract tests. Copies memelab/ and tests/ to a temporary folder, applies one mutation at a time
to memelab/predictive/contract.py, and runs tests/test_predictive_contract.py with bytecode writing off. Every mutation must make at
least one test fail. Never touches the checkout.

    python audits/predictive-intelligence/phase_01/probes/mutation_check.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MUTATIONS = [
    ("P46 feature check removed", 'if model_card.get("feature_set_sha") != doc["feature_set_sha"]:', "if False:"),
    ("P34 assessment ref check removed", 'if doc["backtest_assessment_ref"] is not None and bt != "VERIFIED":', "if False:"),
    ("CC-01 reference may use a post-decision candle", "if end + provider_lag_s <= decision_time and", "if end <= decision_time + 300 and"),
    ("P05 pending label scorable", 'if label_state(outcome["target"], outcome["decision_time"], as_of) == "PENDING" or outcome.get("label_status") == "PENDING":', "if False:"),
    ("P08 blocked target forecastable", 'if tgt["status"] != "PRIMARY":', "if False:"),
    ("silent barrier edit", "upper=1.25, lower=0.85, confirm_s=0,", "upper=1.20, lower=0.85, confirm_s=0,"),
    ("P06 path includes the entry candle", "if float(c[0]) >= t_entry and", "if float(c[0]) + period_s > t_entry and"),
    ("P13 future-trained model allowed", '            if parse_utc(doc["training_cutoff_utc"]) > dt_:', "            if False:"),
    ("PI-D-011 decision basis check removed", 'if doc["decision_time_basis"] not in DECISION_TIME_BASES:', "if False:"),
    ("P38 range check removed", "return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and 0.0 <= x <= 1.0", "return True"),
]


def run(cwd: Path) -> tuple[int, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, "-m", "pytest", "tests/test_predictive_contract.py", "-q", "-p", "no:cacheprovider"],
                       cwd=cwd, env=env, capture_output=True, text=True)
    return p.returncode, (p.stdout.strip().splitlines() or [""])[-1]


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        w = Path(td)
        for d in ("memelab", "tests"):
            shutil.copytree(ROOT / d, w / d, ignore=shutil.ignore_patterns("__pycache__"))
        target = w / "memelab/predictive/contract.py"
        orig = target.read_text()
        code, line = run(w)
        print(f"baseline: exit {code}, {line}")
        survived = 0 if code == 0 else 1
        for name, a, b in MUTATIONS:
            if a not in orig:
                print(f"{name}: NOT APPLIED (pattern missing)")
                survived += 1
                continue
            target.write_text(orig.replace(a, b, 1))
            code, line = run(w)
            ok = code != 0
            survived += 0 if ok else 1
            print(f"{name}: {'caught' if ok else 'SURVIVED'} ({line})")
            target.write_text(orig)
        print(f"mutations {len(MUTATIONS)}, survived or not applied {survived}")
        return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(main())
