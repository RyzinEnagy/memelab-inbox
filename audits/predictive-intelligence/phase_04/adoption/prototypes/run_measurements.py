"""Phase 04: every measurement of the bake-off, through measure.py (fresh process, inside `unshare -n`, audit-hook socket count,
stdout sha256 for determinism). Writes one JSON per measurement under evidence/measure/ and a summary table.

    python run_measurements.py imports|approaches|checks|strace
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EV = HERE.parent / "evidence" / "measure"
V = "/home/claude/pi_research/venvs"
BUNDLE, CORE, MESA, VA = f"{V}/p04_bundle/bin/python", f"{V}/p04_core/bin/python", f"{V}/p04_mesa/bin/python", f"{V}/ip200__venn-abers/bin/python"
SYS = "/usr/bin/python3.13"

IMPORTS = [
    ("lab_runtime_stdlib", SYS, "memelab.predictive.runtime"),
    ("core_numpy_prototype", CORE, "core_numpy"),
    ("numpy", CORE, "numpy"),
    ("sklearn_linear_calibration", BUNDLE, "sklearn.linear_model,sklearn.calibration,sklearn.frozen"),
    ("sklearn_hgb", BUNDLE, "sklearn.ensemble"),
    ("lightgbm", BUNDLE, "lightgbm"),
    ("lifelines", BUNDLE, "lifelines"),
    ("mapie", BUNDLE, "mapie.risk_control,mapie.metrics.calibration"),
    ("purgedcv", BUNDLE, "purgedcv"),
    ("river_drift", BUNDLE, "river.drift"),
    ("pandera", BUNDLE, "pandera.pandas"),
    ("statsmodels", BUNDLE, "statsmodels.api"),
    ("arch", BUNDLE, "arch.bootstrap"),
    ("crepes", BUNDLE, "crepes"),
    ("interpret", BUNDLE, "interpret.glassbox"),
    ("mesa", MESA, "mesa"),
    ("venn_abers_oracle", VA, "venn_abers"),
]
APPROACHES = ["B0", "LR_NUMPY", "LR_SKLEARN", "HGB_SKLEARN", "LGBM", "COX_LIFELINES", "LR_NUMPY_PLATT", "LR_SKLEARN_SIGMOID_FROZEN",
              "LR_NUMPY_VENN_ABERS"]
CORE_ONLY = ["B0", "LR_NUMPY", "LR_NUMPY_PLATT", "LR_NUMPY_VENN_ABERS"]
CHECKS = [
    ("calibration_bundle", BUNDLE, "calibration_check.py", ["bundle"]),
    ("calibration_oracle", VA, "calibration_check.py", ["oracle"]),
    ("splitter", BUNDLE, "splitter_check.py", []),
    ("drift", BUNDLE, "drift_check.py", []),
    ("schema", BUNDLE, "schema_check.py", []),
    ("behavior_numpy", CORE, "behavior_check.py", ["numpy"]),
    ("behavior_mesa", MESA, "behavior_check.py", ["mesa"]),
    ("behavior_mesa_plain_install", BUNDLE, "behavior_check.py", ["mesa", "5", "1"]),
]


def m(label, py, args, repeat):
    out = EV / f"{label}.json"
    cmd = [sys.executable, "-B", str(HERE / "measure.py"), py, str(out), "--label", label, "--repeat", str(repeat), *args]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    print(p.stdout.strip() or p.stderr[-400:], flush=True)


def main(which: str) -> None:
    EV.mkdir(parents=True, exist_ok=True)
    if which == "imports":
        for label, py, mods in IMPORTS:
            m(f"import__{label}", py, ["--script", str(HERE / "import_probe.py"), "--", mods], 5)
    elif which == "approaches":
        for ds in ("challenge", "dev24", "dev6"):
            extra = [] if ds == "challenge" else ["--min-train", "30"]
            for a in APPROACHES:
                m(f"approach__{ds}__{a}__bundle", BUNDLE, ["--script", str(HERE / "bakeoff.py"), "--", ds, a, *extra], 2)
            for a in CORE_ONLY:
                m(f"approach__{ds}__{a}__core_numpy_only", CORE, ["--script", str(HERE / "bakeoff.py"), "--", ds, a, *extra], 2)
    elif which == "checks":
        for label, py, script, args in CHECKS:
            m(f"check__{label}", py, ["--script", str(HERE / script), "--", *args], 2)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1])
