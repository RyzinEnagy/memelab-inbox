"""Phase 08 mutation probe: each mutation of memelab/predictive/technical.py must make tests/test_predictive_technical.py fail.

Works on a temporary copy of the repository's tracked files (the checkout is never edited). Writes a JSON report.

    python -B mutation_technical.py OUT.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TARGET = "memelab/predictive/technical.py"
TEST = "tests/test_predictive_technical.py"

MUTATIONS = [
    ("P06: in-progress candle filter removed", 'cs = [c for c in view.candles("solana", dec["mint"], pool) if c["end_at"] <= T]',
     'cs = [c for c in view.candles("solana", dec["mint"], pool)]'),
    ("retest tolerance 3% to 10%", "RETEST_TOL = math.log(1.03)", "RETEST_TOL = math.log(1.10)"),
    ("prior high includes the last hour", "ph_set = [base24] + between(T - H24, T - H1)", "ph_set = [base24] + between(T - H24, T)"),
    ("failed breakout ignores the fall back", 'RH > PH and last["c"] < PH', "RH > PH"),
    ("breakout reads highs", 'PH, RH = max(c["c"] for c in ph_set), max(c["c"] for c in rh_set)',
     'PH, RH = max(c["c"] for c in ph_set), max(c["h"] for c in rh_set)'),
    ("relative volume per day, not per hour", "(v24 / 24.0 + 1.0)", "(v24 / 1.0 + 1.0)"),
    ("window includes its start", 'return [c for c in cs if T - w < c["end_at"] <= T], None',
     'return [c for c in cs if T - w <= c["end_at"] <= T], None'),
    ("price at x uses a candle ending before x only", 'cand = [c for c in cs if c["end_at"] <= x]', 'cand = [c for c in cs if c["end_at"] < x]'),
    ("coverage needs no candle before the window", "if cover_from > T - w - PERIOD_S:", "if cover_from > T - w:"),
    ("retrieval missingness becomes OOD", 'return "CENSORED_RETRIEVAL" if any(m["missing_basis"] == F.RETRIEVAL for m in miss) else "OOD"',
     'return "OOD"'),
    ("count gate on all training rows", "g = B.gate(len(use), int(y.sum()))", "g = B.gate(len(train), int(y_all.sum()))"),
    ("P13 guard removed", 'early = [e for e in examples if e.decision_time < float(card["training_cutoff"])]', "early = []"),
    ("stump leaf minimum 1", "(nl >= self.min_leaf) & (nr >= self.min_leaf)", "(nl >= 1) & (nr >= 1)"),
    ("stump leaf is the mean residual", "vals.append(float(np.sum(r[side])) / den if abs(den) >= 1e-150 else 0.0)",
     "vals.append(float(np.mean(r[side])))"),
    ("stump initial score 0", "self.init = math.log(p0 / (1 - p0))", "self.init = 0.0"),
    ("stump threshold at the lower value", "thr = xs[k] / 2.0 + xs[k + 1] / 2.0", "thr = xs[k]"),
    ("walk-forward index check removed", "        if want != got:\n            raise B.WalkForwardMismatch",
     "        if False:\n            raise B.WalkForwardMismatch"),
    ("allowlist removed", "    bad = [c for c in columns if c not in ALLOWED]\n    if bad:\n        raise F.AsOfError(f\"columns {bad} are not in the Phase 08 allowlist (NC2-T",
     "    bad = []\n    if bad:\n        raise F.AsOfError(f\"columns {bad} are not in the Phase 08 allowlist (NC2-T"),
    ("version 2 comparison skipped", 'if (a is None) != (b is None) or (a is not None and a != b):', "if False:"),
    ("degenerate test inverted", "return bool(q.size > 1 and np.ptp(q) == 0)", "return bool(q.size > 1 and np.ptp(q) > 0)"),
    ("alert at or above the prevalence", 'alerts = [r[model] > r["B0"] for r in rr]', 'alerts = [r[model] >= r["B0"] for r in rr]'),
    ("identity of the decision not checked",
     'if decision_key is not None and (dec is None or dec["decision_key"] != decision_key or float(dec["decision_time"]) != T):',
     "if False:"),
    ("card feature-set check removed", 'if card.get("feature_set_sha") != feature_set_sha() or card.get("tech_version") != TECH_VERSION:',
     "if False:"),
    ("abstain reason always OOD", "        why[i] = why_not(examples[i], spec[\"rows\"])", "        why[i] = \"OOD\""),
    ("pullback against the 24 h high", 'hi6 = max([base6["c"]] + [c["c"] for c in ws6])', 'hi6 = max([base24["c"]] + [c["c"] for c in w24])'),
    ("missing value given the decision availability and a zero", 'x[c] = v["value"] if v["value"] is not None else float("nan")',
     'x[c] = v["value"] if v["value"] is not None else 0.0'),
    ("rv over closes skips the base price", "seq = [base] + [c for c in ws if c is not base]", "seq = [c for c in ws if c is not base]"),
    ("range 6 h uses the 24 h window", 'for name, w in (("tech_log_range_6h", H6), ("tech_log_range_24h", H24)):',
     'for name, w in (("tech_log_range_6h", H24), ("tech_log_range_24h", H24)):'),
]


def main() -> int:
    out = Path(sys.argv[1])
    files = subprocess.run(["git", "ls-files", "memelab", "tests"], cwd=REPO, capture_output=True, text=True, check=True).stdout.split()
    files += [TARGET, TEST]
    results = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "repo"
        for f in sorted(set(files)):
            src = REPO / f
            if src.is_file():
                (root / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, root / f)
        orig = (root / TARGET).read_text()
        base = subprocess.run([sys.executable, "-B", "-m", "pytest", TEST, "-q", "-x", "-p", "no:cacheprovider"], cwd=root,
                              capture_output=True, text=True)
        if base.returncode != 0:
            raise SystemExit("tests fail on the unmutated copy:\n" + base.stdout[-2000:])
        for name, old, new in MUTATIONS:
            if orig.count(old) != 1:
                results.append({"mutation": name, "applied": False, "caught": None, "note": f"pattern found {orig.count(old)} times"})
                continue
            (root / TARGET).write_text(orig.replace(old, new))
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", TEST, "-q", "-x", "-p", "no:cacheprovider"], cwd=root,
                               capture_output=True, text=True)
            first = next((ln for ln in r.stdout.splitlines() if ln.startswith("FAILED") or ln.startswith("ERROR")), "")
            results.append({"mutation": name, "applied": True, "caught": r.returncode != 0, "first_failure": first[:200]})
            (root / TARGET).write_text(orig)
    applied = [r for r in results if r["applied"]]
    rep = {"mutations": len(MUTATIONS), "applied": len(applied), "caught": sum(1 for r in applied if r["caught"]),
           "survived": [r["mutation"] for r in applied if not r["caught"]],
           "not_applied": [r["mutation"] for r in results if not r["applied"]], "results": results}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rep[k] for k in ("mutations", "applied", "caught", "survived", "not_applied")}))
    return 0 if rep["caught"] == rep["mutations"] else 1


if __name__ == "__main__":
    sys.exit(main())
