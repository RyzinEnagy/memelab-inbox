"""Phase 11 mutation probe: each mutation of memelab/predictive/analog.py must make tests/test_predictive_analog.py fail.

Works on a temporary copy of the repository's tracked files plus the Phase 11 files (the checkout is never edited), so it runs
at HEAD. Writes a JSON report.

    python -B mutation_analog.py OUT.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
AP = "memelab/predictive/analog.py"
TEST = "tests/test_predictive_analog.py"
EXTRA = [AP, TEST]

MUTATIONS = [
    # the as-of pool (P43, NC2-AC, P36)
    (AP, "pool row decided at as_of accepted", "        if not r.decision_time < as_of:", "        if not r.decision_time <= as_of:"),
    (AP, "label maturity check removed", "        if not r.label_matures_at <= as_of:\n", "        if False:\n"),
    (AP, "future-issued token accepted", "        if r.first_seen_at is not None and r.first_seen_at > as_of:", "        if False:"),
    (AP, "pool availability check removed", "    if pool:\n        check_asof(pool, list(DIST_COLUMNS), as_of=as_of, with_labels=True)", "    pass"),
    (AP, "target availability check removed", "    check_asof([e], list(DIST_COLUMNS), as_of=None, with_labels=False)", "    pass"),
    (AP, "cohort after the decision accepted", "    if as_of > e.decision_time:", "    if False:"),
    (AP, "allowlist removed", "    bad = [c for c in columns if c not in ALLOWED]", "    bad = []"),
    (AP, "select skips the checks", "    if check:\n        check_target(target, as_of)\n        check_pool(pool, as_of)", "    pass"),
    # identity and groups (P01, P14)
    (AP, "same mint kept as an analog", '        if r.chain == target.chain and r.mint == target.mint:\n            ex["same_mint"] += 1\n            continue',
     '        if False:\n            continue'),
    (AP, "same creator kept (P14)", "        if target.creator and r.creator == target.creator:", "        if False:"),
    (AP, "campaign kept in LOCO", "        if loco and target.narrative and r.narrative == target.narrative:", "        if False:"),
    (AP, "cluster by mint only", 'return f"creator:{creator}" if isinstance(creator, str) and creator else f"mint:{chain}:{mint}"',
     'return f"mint:{chain}:{mint}"'),
    (AP, "token history by any mint", "    return [r for r in pool if r.chain == target.chain and r.mint == target.mint]", "    return [r for r in pool if r.chain == target.chain]"),
    (AP, "AC1 keeps every row of a cluster", "                if cur is None or (r.decision_time, r.decision_key) > (cur.decision_time, cur.decision_key):\n                    newest[r.cluster] = r",
     "                newest[r.decision_key] = r"),
    (AP, "AC1 keeps the oldest row", "                if cur is None or (r.decision_time, r.decision_key) > (cur.decision_time, cur.decision_key):",
     "                if cur is None or (r.decision_time, r.decision_key) < (cur.decision_time, cur.decision_key):"),
    # minimums and states
    (AP, "G minimum lowered", "        if ans[\"G\"] < MIN_G:", "        if ans[\"G\"] < 5:"),
    (AP, "days minimum removed", "        if ans[\"analog_days\"] < MIN_DAYS:", "        if False:"),
    (AP, "training gate skipped", "    g = B.gate(len(pool), int(y.sum()) if len(pool) else 0)\n    if g:\n        ans", "    g = None\n    if g:\n        ans"),
    (AP, "OOD rule removed", "            elif not (math.isfinite(thr) and kth <= thr):", "            elif False:"),
    (AP, "OOD quantile 0.99", "OOD_Q = 0.95", "OOD_Q = 0.99"),
    (AP, "missing target input imputed", "        if not complete(target):\n            reasons.append(\"OUT_OF_DISTRIBUTION:MISSING_INPUT\")", "        pass"),
    (AP, "unknown cell accepted", '        if None in cell or "UNKNOWN" in cell:', "        if None in cell:"),
    (AP, "empty cell not OOD", '            if not rows:\n                reasons.append("OUT_OF_DISTRIBUTION:CELL_UNSEEN")', "            pass"),
    (AP, "regime filter removed", "                ref = [r for r in ref if r.regime == target.regime]", "                ref = list(ref)"),
    (AP, "warmup regime accepted", "            if target.regime in (None, WARMUP, UNKNOWN):", "            if target.regime is None:"),
    (AP, "K = 20", "K_NEIGHBOURS = 30", "K_NEIGHBOURS = 20"),
    # distance
    (AP, "categorical mismatch ignored", "        d2 = np.sum((self.Z - z) ** 2, axis=1) + np.sum(self.cat != c, axis=1)", "        d2 = np.sum((self.Z - z) ** 2, axis=1)"),
    (AP, "sample sd instead of population", "        sd = X.std(axis=0) if len(self.rows) else np.ones(len(NUMERIC))", "        sd = X.std(axis=0, ddof=1) if len(self.rows) else np.ones(len(NUMERIC))"),
    (AP, "own cluster kept in the threshold", "                    cm[self.cid[i]] = np.inf\n", "                    pass\n"),
    (AP, "ties broken by position", "            if j is None or (d[i], self.keys[i]) < (d[j], self.keys[j]):", "            if j is None or d[i] < d[j]:"),
    # number
    (AP, "no shrinkage", '           "shrunk_number": (k + M_SHRINK * b0) / (G + M_SHRINK) if G else None}', '           "shrunk_number": (k / G) if G else None}'),
    (AP, "time instability never flagged", '"time_unstable": bool(wo[1] < wn[0] or wn[1] < wo[0])}', '"time_unstable": False}'),
    # regime (CX-11)
    (AP, "regime reads later rows", "    _assert_visible(rows, T)\n    instants", "    instants"),
    (AP, "regime uses instants at T too", "    instants = sorted({r.decision_time for r in rows if r.decision_time < T})", "    instants = sorted({r.decision_time for r in rows if r.decision_time <= T})"),
    (AP, "regime warmup 3", "REGIME_WARMUP = 5", "REGIME_WARMUP = 3"),
    (AP, "regime series uses every instant", "        prior = instants[:i]\n", "        prior = instants\n"),
    (AP, "availability after T accepted in regime", "        if r.available_at is not None and r.available_at > T:", "        if False:"),
    (AP, "tone counts every status", "    tone = (sum(1 for r in w if B.status_group(r.status) == CONSTRUCTIVE) / len(w)) if w else float(\"nan\")",
     "    tone = (sum(1 for r in w if r.status) / len(w)) if w else float(\"nan\")"),
    # router, P44, divergence, cards, P13
    (AP, "token history at 1 row", "    if len(th) >= MIN_TOKEN_HISTORY:", "    if len(th) >= 1:"),
    (AP, "execution data never missing", '        if cap.get("basis") == "EXECUTION_DATA_MISSING":\n            out["flags"].append("EXECUTION_DATA_MISSING")', "        pass"),
    (AP, "divergence flags dropped", '            out["flags"] += divergence_flags(target, [r for r in pool if r.decision_key in sel])', "            pass"),
    (AP, "authority differs never flagged", "        if known and sum(1 for v in known if v == float(tv)) < 0.5 * len(known):", "        if False:"),
    (AP, "unknown authority not flagged", '            flags.append(f"{a.upper()}_UNKNOWN")\n            continue', "            continue"),
    (AP, "P13 check removed", "    early = [e for e in examples if e.decision_time < float(card[\"training_cutoff\"])]", "    early = []"),
    (AP, "card hash not verified", "    if card.get(\"model_sha\") != want:", "    if False:"),
    (AP, "fit accepts a later pool row", "    check_pool(pool, cutoff)\n    y = B.labels_of(pool)", "    y = B.labels_of(pool)"),
    (AP, "contract mapping accepts unknown", "        if c is None:\n            raise AnalogError", "        if c is None:\n            continue\n            raise AnalogError"),
]

EQUIVALENT: list = []


def main() -> int:
    out = Path(sys.argv[1])
    files = subprocess.run(["git", "ls-files", "memelab", "tests"], cwd=REPO, capture_output=True, text=True, check=True).stdout.split()
    files += EXTRA
    results = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "repo"
        for f in sorted(set(files)):
            src = REPO / f
            if src.is_file():
                (root / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, root / f)
        orig = {p: (root / p).read_text() for p in (AP,)}
        cmd = [sys.executable, "-B", "-m", "pytest", TEST, "-q", "-x", "-p", "no:cacheprovider"]
        base = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        if base.returncode != 0:
            raise SystemExit("tests fail on the unmutated copy:\n" + base.stdout[-2000:])
        for path, name, old, new in MUTATIONS + EQUIVALENT:
            src = orig[path]
            if src.count(old) != 1:
                results.append({"file": path, "mutation": name, "applied": False, "caught": None, "note": f"pattern found {src.count(old)} times"})
                continue
            (root / path).write_text(src.replace(old, new))
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
            first = next((ln for ln in r.stdout.splitlines() if ln.startswith("FAILED") or ln.startswith("ERROR")), "")
            results.append({"file": path, "mutation": name, "applied": True, "caught": r.returncode != 0, "first_failure": first[:200]})
            (root / path).write_text(src)
    eq_names = {n for _, n, _, _ in EQUIVALENT}
    applied = [r for r in results if r["applied"] and r["mutation"] not in eq_names]
    rep = {"mutations": len(MUTATIONS), "applied": len(applied), "caught": sum(1 for r in applied if r["caught"]),
           "survived": [r["mutation"] for r in applied if not r["caught"]],
           "equivalent": [{"mutation": r["mutation"], "caught": r["caught"]} for r in results if r["mutation"] in eq_names],
           "not_applied": [r["mutation"] for r in results if not r["applied"]], "results": results}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rep[k] for k in ("mutations", "applied", "caught", "survived", "not_applied")}))
    return 0 if rep["caught"] == rep["mutations"] else 1


if __name__ == "__main__":
    sys.exit(main())
