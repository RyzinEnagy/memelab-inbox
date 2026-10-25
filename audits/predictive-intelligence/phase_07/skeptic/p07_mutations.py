"""Phase 07 skeptic: new mutations of stats.py and baselines.py (none of them in the agent's list of 29), each applied to a copy
of the clone, then the two Phase 07 test files are run. A surviving mutation is a test gap.

    python -B p07_mutations.py CLONE OUT_JSON
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ST, BL = "memelab/predictive/stats.py", "memelab/predictive/baselines.py"
TESTS = ["tests/test_predictive_stats.py", "tests/test_predictive_baselines.py"]
M = [
    (ST, "bootstrap resamples rows, not groups", "        idx = np.concatenate([rows_of[i] for i in pick])\n        vals[r] = stat(idx)",
     "        idx = rng.integers(0, len(g), size=len(g))\n        vals[r] = stat(idx)"),
    (ST, "bootstrap 90% interval", "    a = (1 - conf) / 2\n", "    a = (1 - conf)\n"),
    (BL, "narrower interval governs", 'w = max(intervals, key=lambda u: intervals[u]["ci"][1] - intervals[u]["ci"][0])',
     'w = min(intervals, key=lambda u: intervals[u]["ci"][1] - intervals[u]["ci"][0])'),
    (BL, "mint bootstrap groups by day (copy error)", '(("day", days), ("mint", mints))', '(("day", days), ("mint", days))'),
    (ST, "intercept penalised", "lam = np.r_[0.0, np.full(d, 1.0 / self.C)]", "lam = np.r_[1.0 / self.C, np.full(d, 1.0 / self.C)]"),
    (ST, "standardisation with ddof=1", "        sd = Z.std(axis=0)\n", "        sd = Z.std(axis=0, ddof=1)\n"),
    (ST, "test window two days (pooled rows counted twice)", "te = np.where((dt_ >= cut) & (dt_ < cut + DAY))[0]",
     "te = np.where((dt_ >= cut) & (dt_ < cut + 2 * DAY))[0]"),
    (BL, "unseen status gets 0.5, not B0", 'p[i] = body["groups"][key]["p"] if key in body["groups"] else body["b0"]',
     'p[i] = body["groups"][key]["p"] if key in body["groups"] else 0.5'),
    (BL, "NC1 labels not shuffled", "yy = np.random.default_rng(s).permutation(labels_of(train))", "yy = labels_of(train)"),
    (BL, "identity join ignores the chain", '    for a, b in (("chain", "chain"), ("mint", "mint")):', '    for a, b in (("mint", "mint"),):'),
    (ST, "Holm without monotone step-down", "        run = max(run, min(1.0, (m - rank) * vals[i]))", "        run = min(1.0, (m - rank) * vals[i])"),
    (ST, "Holm as plain Bonferroni", "        run = max(run, min(1.0, (m - rank) * vals[i]))", "        run = max(run, min(1.0, m * vals[i]))"),
    (ST, "log loss clip ignored", "    q = np.clip(p, clip, 1 - clip)\n", "    q = np.clip(p, 1e-15, 1 - 1e-15)\n"),
    (BL, "fit_all accepts unmatured training rows", "if not (e.decision_time < cutoff and e.label_matures_at <= cutoff):",
     "if not (e.decision_time < cutoff):"),
    (BL, "one-sided p counts only BSS < 0", '"p_one_sided": (1 + int(np.sum(~(bs["values"] > 0)))) / (reps + 1)',
     '"p_one_sided": (1 + int(np.sum(bs["values"] < 0))) / (reps + 1)'),
    (BL, "B3 OOD row predicted at Platt(0)", "            else:\n                why[i] = \"OOD\"\n    elif kind == \"B4\":",
     "            else:\n                p[i] = float(pl.predict(np.array([0.0]))[0])\n    elif kind == \"B4\":"),
    (BL, "B4 missing liquidity predicts 0", '            if not (math.isfinite(liq) and math.isfinite(mc)):\n                p[i] = body["b0"]',
     '            if not (math.isfinite(liq) and math.isfinite(mc)):\n                p[i] = 0.0'),
    (BL, "B4C window 10x", "B4C_WINDOW_S = 43200.0", "B4C_WINDOW_S = 432000.0"),
    (BL, "worse-than-base when upper bound <= 0.05", "    if hi < 0:\n", "    if hi < 0.05:\n"),
    (ST, "calibration bin minimum 10", "    nb = min(max_bins, n // min_bin)", "    nb = min(max_bins, n // 10)"),
]


def apply(root, path, old, new):
    f = root / path
    s = f.read_text()
    if s.count(old) != 1:
        raise SystemExit(f"{path}: mutation text found {s.count(old)} times: {old[:70]!r}")
    f.write_text(s.replace(old, new))


def run(root):
    return subprocess.run([sys.executable, "-m", "pytest", *TESTS, "-x", "-q", "-p", "no:cacheprovider"], cwd=root,
                          capture_output=True, text=True, timeout=600).returncode


def main(clone, out):
    clone = Path(clone)
    res = []
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "clean"
        for d in ("memelab", "tests"):
            shutil.copytree(clone / d, base / d, ignore=shutil.ignore_patterns("__pycache__"))
        clean = run(base)
        for path, name, old, new in M:
            w = Path(td) / "m"
            if w.exists():
                shutil.rmtree(w)
            shutil.copytree(base, w)
            apply(w, path, old, new)
            rc = run(w)
            res.append({"file": path, "mutation": name, "exit_code": rc, "caught": rc != 0})
            print(("caught  " if rc else "SURVIVED"), name, flush=True)
    doc = {"clean_exit_code": clean, "mutations": len(res), "caught": sum(r["caught"] for r in res), "results": res}
    Path(out).write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps({k: doc[k] for k in ("clean_exit_code", "mutations", "caught")}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
