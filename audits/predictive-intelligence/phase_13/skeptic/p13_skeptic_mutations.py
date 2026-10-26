"""Phase 13 skeptic: mutations NOT in the phase's own probe, run against the Phase 13 tests (and test_predictive_stats.py for
the Platt solver) on a temporary copy of the clone. A surviving mutation is a rule no test pins.

    python -B p13_skeptic_mutations.py CLONE OUT.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CP = "memelab/predictive/calibration.py"
AP = "memelab/predictive/abstention.py"
SP = "memelab/predictive/stats.py"
TESTS = ["tests/test_predictive_calibration.py", "tests/test_predictive_abstention.py", "tests/test_predictive_phase13_outputs.py",
         "tests/test_predictive_stats.py"]
MUT = [
    (SP, "K1 Platt tolerance 1e-12 -> 1e-2", "max_iter: int = 200, tol: float = 1e-12", "max_iter: int = 200, tol: float = 1e-2"),
    (SP, "K2 Platt one Newton step", "max_iter: int = 200, tol: float = 1e-12", "max_iter: int = 1, tol: float = 1e-12"),
    (CP, "M1 Venn-Abers per-class gate 40 -> 20", 'VENN_ABERS_GATE = {"min_events": 200, "min_per_class": 40}', 'VENN_ABERS_GATE = {"min_events": 200, "min_per_class": 20}'),
    (CP, "M2 OOD bound 4 -> 40", "OOD_Z = 4.0", "OOD_Z = 40.0"),
    (CP, "M3 near-flat sd 0.005 -> 0", "NEAR_FLAT_SD = 0.005", "NEAR_FLAT_SD = 0.0"),
    (CP, "M4 support interval Wilson z 1.96 -> 1.0", "    wl, wh = K.wilson(int(support_k), int(support_n))\n    return",
     "    wl, wh = K.wilson(int(support_k), int(support_n), z=1.0)\n    return"),
    (CP, "M5 support ties to the upper bin", "        if g < gap:", "        if g <= gap:"),
    (CP, "M6 exchangeability alpha 0.05 -> 0.01", "alpha: float = 0.05", "alpha: float = 0.01"),
    (CP, "M7 drift threshold 2.0 -> 20.0", 'DRIFT = {"delta": 0.005, "threshold": 2.0,', 'DRIFT = {"delta": 0.005, "threshold": 20.0,'),
    (CP, "M8 drift alarm counts only strictly earlier", "    return any(a <= decision_time for a in alarms)", "    return any(a < decision_time for a in alarms)"),
    (CP, "M9 evidence status NONE not named", '        elif ev["status"] == "NONE":\n            details.append("CALIBRATION_EVIDENCE_TOO_SMALL")',
     '        elif False:\n            details.append("CALIBRATION_EVIDENCE_TOO_SMALL")'),
    (CP, "M10 verify_card publishable check off", '    if card.get("publishable") != (card.get("status") == CALIBRATED and card.get("level") in PUBLISHABLE_LEVELS):',
     "    if False:"),
    (CP, "M11 verify_card registry check off", '    if card.get("registry_sha") != C.registry_sha256():', "    if False:"),
    (CP, "M12 base-rate bootstrap reps 20000 -> 200", "BASE_REPS = 20000", "BASE_REPS = 200"),
    (AP, "M13 validator display range dropped", "    if not (_fin(p) and CAL.DISPLAY_RANGE[0] <= p <= CAL.DISPLAY_RANGE[1]):", "    if not _fin(p):"),
    (AP, "M14 validator support minimum 20 -> 1", "    if not (isinstance(sn, int) and isinstance(sk, int) and 0 <= sk <= sn) or sn < CAL.SUPPORT_MIN:",
     "    if not (isinstance(sn, int) and isinstance(sk, int) and 0 <= sk <= sn) or sn < 1:"),
    (AP, "M15 evaluate evidence-too-small dropped", "    elif CAL.evidence_gate(int(ev.get(\"n\") or 0), int(ev.get(\"k\") or 0)):\n",
     "    elif False:\n"),
    (AP, "M16 model age boundary > -> >=", '        elif T - cut > C.ACCEPTANCE["max_model_age_s"]:', '        elif T - cut >= C.ACCEPTANCE["max_model_age_s"]:'),
    (AP, "M17 token history minimum 20 -> 1", "TOKEN_HISTORY_MIN_ROWS = 20", "TOKEN_HISTORY_MIN_ROWS = 1"),
    (AP, "M18 validator FORECAST record conditions not checked", '        if record is not None and record.get("conditions"):\n            errs.append("a FORECAST whose record',
     '        if False:\n            errs.append("a FORECAST whose record'),
    (AP, "M19 degenerate flag from card ignored in evaluate",
     '    if cal_card is not None and ((cal_card.get("degeneracy") or {}).get("flat") or "DEGENERATE_FLAT_PREDICTIONS" in details):',
     "    if False:"),
]


def main() -> int:
    clone, out = Path(sys.argv[1]), Path(sys.argv[2])
    files = subprocess.run(["git", "ls-files"], cwd=clone, capture_output=True, text=True, check=True).stdout.split()
    files = [f for f in files if f.startswith(("memelab/", "tests/", "docs/predictive-intelligence/"))
             or f.startswith("audits/predictive-intelligence/")]
    res = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "repo"
        for f in files:
            src = clone / f
            if src.is_file():
                (root / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, root / f)
        cmd = [sys.executable, "-B", "-m", "pytest", *TESTS, "-q", "-x", "-p", "no:cacheprovider"]
        base = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        if base.returncode != 0:
            raise SystemExit("unmutated copy fails:\n" + base.stdout[-2000:])
        orig = {p: (root / p).read_text() for p in (CP, AP, SP)}
        for path, name, old, new in MUT:
            src = orig[path]
            if src.count(old) != 1:
                res.append({"mutation": name, "applied": False, "count": src.count(old)})
                continue
            (root / path).write_text(src.replace(old, new))
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
            first = next((ln for ln in r.stdout.splitlines() if ln.startswith(("FAILED", "ERROR"))), "")
            res.append({"mutation": name, "applied": True, "caught": r.returncode != 0, "first_failure": first[:180]})
            (root / path).write_text(src)
            print(name, "caught" if r.returncode else "SURVIVED", first[:120], flush=True)
    rep = {"applied": sum(1 for r in res if r["applied"]), "caught": sum(1 for r in res if r.get("caught")),
           "survived": [r["mutation"] for r in res if r["applied"] and not r["caught"]],
           "not_applied": [r["mutation"] for r in res if not r["applied"]], "results": res}
    out.write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("applied", "caught", "survived", "not_applied")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
