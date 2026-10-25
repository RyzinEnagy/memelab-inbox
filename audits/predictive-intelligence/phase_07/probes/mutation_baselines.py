"""Phase 07 mutation check: every mutation of baselines.py or stats.py must make the Phase 07 tests fail.

Each mutation is one exact text replacement, applied to a copy of memelab/ and tests/ in a temporary folder; the two Phase 07
test files run there with `-x -q`. A mutation whose text is not found is an error (the check would be vacuous). Nothing in the
repository is changed.

    python -B mutation_baselines.py OUT.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TESTS = ["tests/test_predictive_baselines.py", "tests/test_predictive_stats.py"]
BL, ST = "memelab/predictive/baselines.py", "memelab/predictive/stats.py"

MUTATIONS = [
    (BL, "count gate ignores the event minimum", 'if n < a["min_train_events"] or', "if n < 10 or"),
    (BL, "count gate ignores the per-class minimum", 'k < a["min_train_per_class"] or n - k < a["min_train_per_class"]', "False"),
    (BL, "identity join ignores the mint", '    for a, b in (("chain", "chain"), ("mint", "mint")):', '    for a, b in (("chain", "chain"),):'),
    (BL, "identity join ignores the decision time (CX-07)",
     '    if float(label_row["decision_time"]) != float(feature_row["decision_time"]):', "    if False:"),
    (BL, "allowlist off (NC2)", '    bad = [c for c in columns if c not in ALLOWED_COLUMNS]\n    if bad:\n        raise F.AsOfError(f"columns {bad} are not in the Phase 07 allowlist (NC2',
     '    bad = []\n    if bad:\n        raise F.AsOfError(f"columns {bad} are not in the Phase 07 allowlist (NC2'),
    (BL, "availability not validated", "    F.validate_rows(rows, columns=cols, availability=[c + \"__available_at\" for c in columns], as_of=as_of)",
     "    pass"),
    (BL, "no shrinkage toward B0", '"p": (sum(v) + M_SHRINK * b0) / (len(v) + M_SHRINK)', '"p": sum(v) / len(v)'),
    (BL, "walk-forward trusts the gate without comparing", "        if want != got:\n            raise WalkForwardMismatch", "        if False:\n            raise WalkForwardMismatch"),
    (BL, "fold audit without the target's maturity lag", "min_maturity_lag_s=maturity_lag(target)", "min_maturity_lag_s=None"),
    (BL, "claims on fewer than 5 days", '    if res["days"] < a["min_effective_days"] or res.get("gov_ci") is None:', '    if res.get("gov_ci") is None:'),
    (BL, "skill without Holm", "    if lo > 0 and p_holm is not None and p_holm < 1 - a[\"bootstrap\"][\"conf\"]:", "    if lo > 0:"),
    (BL, "day bootstrap on fewer than 5 days", '        if unit == "day" and ng < a["min_effective_days"]:', "        if False:"),
    (BL, "B4 matches the same mint", "if r[0] != e.mint and _within(", "if _within("),
    (BL, "fixture flag lost", "    return FIXTURE_FLAG if is_fixture else", "    return"),
    (BL, "card hash not verified", "    if card.get(\"model_sha\") != want:\n        raise ModelHashMismatch", "    if False:\n        raise ModelHashMismatch"),
    (BL, "missing required input not OOD", '        ok = [i for i, e in enumerate(examples) if all(math.isfinite(_num(e.x.get(c))) for c in body["required"])]',
     "        ok = list(range(n))"),
    (BL, "negative token age kept", "math.log1p(v / 86400.0) if math.isfinite(v) and v >= 0 else", "math.log1p(abs(v) / 86400.0) if math.isfinite(v) else"),
    (BL, "AUC on a constant prediction", '    if k >= mpc and len(y) - k >= mpc and np.ptp(p) > 0:', '    if k >= mpc and len(y) - k >= mpc:'),
    (ST, "AUC ties by order", "        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0", "        ranks[order[i:j + 1]] = np.arange(i, j + 1) + 1.0"),
    (ST, "average precision without tie groups", "    last = np.r_[np.where(np.diff(ss) != 0)[0], len(ss) - 1]", "    last = np.arange(len(ss))"),
    (ST, "calibration bins below 40 events", "    if n < in_the_large_only_below:", "    if n < 2:"),
    (ST, "Holm drops undefined tests from the family", "    m = len(pvalues)\n    vals =", "    m = sum(1 for p in pvalues if p is not None and math.isfinite(p))\n    vals ="),
    (ST, "walk-forward ignores maturity", "        tr = np.where((dt_ < cut) & (mat <= cut))[0]", "        tr = np.where(dt_ < cut)[0]"),
    (ST, "fold audit ignores a late declared cutoff", "cut <= t0)", "True)"),
    (ST, "probabilities outside [0, 1] accepted", "np.any(p < 0) or np.any(p > 1)", "False"),
    (ST, "Platt constant-score optimum lost", "            self.a_, self.b_ = 0.0, math.log((1 - tbar) / tbar)", "            self.a_, self.b_ = 0.0, 0.0"),
    (ST, "Prep median from zero", "np.nanmedian(c) if np.any(np.isfinite(c)) else 0.0", "0.0"),
    (ST, "Wilson without the continuity of z", "    c = (ph + z * z / (2 * n)) / den", "    c = ph"),
    (ST, "Brier skill reference ignored", "    return float(\"nan\") if den == 0 else 1.0 - float(np.sum((p - y) ** 2)) / den",
     "    return 1.0 - float(np.sum((p - y) ** 2)) / max(den, 1e-300)"),
]


def apply(root: Path, path: str, old: str, new: str) -> None:
    f = root / path
    s = f.read_text()
    if s.count(old) != 1:
        raise SystemExit(f"mutation text found {s.count(old)} times in {path}: {old[:60]!r}")
    f.write_text(s.replace(old, new))


def run(root: Path) -> int:
    return subprocess.run([sys.executable, "-m", "pytest", *TESTS, "-x", "-q", "-p", "no:cacheprovider"], cwd=root,
                          capture_output=True, text=True, timeout=600).returncode


def main(out: str) -> None:
    res, t0 = [], time.time()
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "clean"
        shutil.copytree(REPO / "memelab", base / "memelab", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(REPO / "tests", base / "tests", ignore=shutil.ignore_patterns("__pycache__"))
        clean = run(base)
        for path, name, old, new in MUTATIONS:
            work = Path(td) / "m"
            if work.exists():
                shutil.rmtree(work)
            shutil.copytree(base, work)
            apply(work, path, old, new)
            rc = run(work)
            res.append({"file": path, "mutation": name, "exit_code": rc, "caught": rc != 0})
            print(f"{'caught' if rc else 'SURVIVED'}: {name}", flush=True)
    doc = {"clean_exit_code": clean, "mutations": len(res), "caught": sum(r["caught"] for r in res), "results": res,
           "seconds": round(time.time() - t0, 1)}
    Path(out).write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps({k: doc[k] for k in ("clean_exit_code", "mutations", "caught")}))


if __name__ == "__main__":
    main(sys.argv[1])
