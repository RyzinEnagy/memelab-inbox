"""Phase 01 skeptic: mutations the phase's own mutation_check.py does not try. Each mutation weakens one rule the contract
claims to enforce; a mutation that SURVIVES means no test pins that rule (the test passes for another reason or never asks).

    python skeptic_01_mutations.py /home/claude/pi_orchestration/skeptic_01
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

C = "memelab/predictive/contract.py"
MUT = [
    # (name, file, old, new)
    ("range [0,1] check dropped, finiteness and type kept", C,
     "math.isfinite(x) and 0.0 <= x <= 1.0", "math.isfinite(x)"),
    ("bool accepted as a probability", C,
     "not isinstance(x, bool) and math.isfinite", "math.isfinite"),
    ("FORECAST no longer needs training_cutoff_utc", C,
     '("model_id", "model_sha", "feature_set_sha", "data_snapshot_sha", "training_cutoff_utc")',
     '("model_id", "model_sha", "feature_set_sha", "data_snapshot_sha")'),
    ("FORECAST no longer needs model_sha / feature_set_sha / data_snapshot_sha", C,
     '("model_id", "model_sha", "feature_set_sha", "data_snapshot_sha", "training_cutoff_utc")', '("model_id",)'),
    ("ABSTAIN may carry an uncertainty interval", C,
     'for k in ("probability", "uncertainty_interval"):', 'for k in ("probability",):'),
    ("generated_at before decision allowed", C,
     "if gen < dt_:", "if False:"),
    ("base_rate range check removed", C,
     'if not _num01(doc["base_rate"]):', "if False:"),
    ("forbidden-key check removed", C,
     "if k.lower() in FORBIDDEN_KEYS:", "if False:"),
    ("calibration passed flag ignored", C,
     'elif cal.get("passed") is not True:', "elif False:"),
    ("ABSTAIN with NaN probability: None check replaced by numeric-zero check", C,
     "if doc[k] is not None:", "if doc[k] is not None and doc[k] == doc[k] and doc[k] != 0:"),
    ("an existing module imports the package via 'from memelab import predictive'", "memelab/cli.py",
     "from __future__ import annotations", "from __future__ import annotations\nfrom memelab import predictive  # noqa"),
    ("an existing module imports the package via importlib", "memelab/pipeline.py",
     "from __future__ import annotations", "from __future__ import annotations\nimport importlib as _il; _il.import_module('memelab.predictive.contract')  # noqa"),
]


def run(cwd):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, "-m", "pytest", "tests/test_predictive_contract.py", "-q", "-p", "no:cacheprovider"],
                       cwd=cwd, env=env, capture_output=True, text=True)
    return p.returncode, (p.stdout.strip().splitlines() or [""])[-1]


def main(root):
    root = Path(root)
    with tempfile.TemporaryDirectory() as td:
        w = Path(td)
        for d in ("memelab", "tests"):
            shutil.copytree(root / d, w / d, ignore=shutil.ignore_patterns("__pycache__"))
        code, line = run(w)
        print(f"baseline: exit {code}, {line}")
        for name, f, a, b in MUT:
            p = w / f
            orig = p.read_text()
            if a not in orig:
                print(f"NOT APPLIED  {name}")
                continue
            p.write_text(orig.replace(a, b, 1))
            code, line = run(w)
            print(f"{'caught  ' if code else 'SURVIVED'}  {name}  ({line})")
            p.write_text(orig)


if __name__ == "__main__":
    main(sys.argv[1])
