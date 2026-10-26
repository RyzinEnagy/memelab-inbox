"""Phase 11 skeptic: mutations of memelab/predictive/analog.py not in the phase's own probe. Each is applied in the skeptic
clone, tests/test_predictive_analog.py is run, and the file is restored."""
import json, subprocess, sys
from pathlib import Path
REPO = Path("/home/claude/pi_orchestration/skeptic_11")
TARGET = REPO / "memelab/predictive/analog.py"
TEST = "tests/test_predictive_analog.py"
M = [
 ("kNN ignores the same-mint and same-creator exclusion (allowed mask dropped)",
  "            nn = idx.nearest_clusters(d, allowed)[:K_NEIGHBOURS]", "            nn = idx.nearest_clusters(d)[:K_NEIGHBOURS]"),
 ("index cache ignores the regime (AC3 reuses another regime's reference rows)",
  '            ck = (model, target.regime if model == "AC3_KNN_REGIME" else None, id(pool))', "            ck = (model, None, id(pool))"),
 ("router uses the regime-blind cohort", "        a = select(PRIMARY, target, pool, as_of=as_of, check=False)", '        a = select("AC2_KNN", target, pool, as_of=as_of, check=False)'),
 ("ACTIVE when equal to the past median", '    return ("ACTIVE" if a > ma else "QUIET")', '    return ("ACTIVE" if a >= ma else "QUIET")'),
 ("regime window 48 h", "REGIME_WINDOW_S = 86400.0", "REGIME_WINDOW_S = 172800.0"),
 ("regime window excludes the current export", "    w = [r for r in rows if T - REGIME_WINDOW_S < r.decision_time <= T]", "    w = [r for r in rows if T - REGIME_WINDOW_S < r.decision_time < T]"),
 ("day Kish ESS reported as the day count", "    return float(c.sum() ** 2 / np.sum(c ** 2))", "    return float(len(c))"),
 ("shrinkage toward 0.5 instead of the pool prevalence", '"shrunk_number": (k + M_SHRINK * b0) / (G + M_SHRINK) if G else None}', '"shrunk_number": (k + M_SHRINK * 0.5) / (G + M_SHRINK) if G else None}'),
 ("OOD threshold from the nearest other cluster, not the K-th", "                    kth.append(v[min(k, len(v)) - 1])", "                    kth.append(v[0])"),
 ("depth flag band widened to min..max", "            lo, hi = np.quantile(np.array(known, float), [0.1, 0.9])", "            lo, hi = np.quantile(np.array(known, float), [0.0, 1.0])"),
 ("new_mint always False", '"new_mint": not any(r.chain == target.chain and r.mint == target.mint for r in pool),', '"new_mint": False,'),
 ("time split puts one analog in OLDER", "    h = G // 2\n", "    h = 1\n"),
 ("NC1 permutation with a fixed seed", "                yy = np.random.default_rng(s).permutation(B.labels_of(train))", "                yy = np.random.default_rng(0).permutation(B.labels_of(train))"),
 ("degenerate never flagged", "    return bool(q.size > 1 and np.ptp(q) == 0)", "    return False"),
 ("pool rows with a missing input used as candidates (NaN distances)", "        ref = [r for r in pool if complete(r)]", "        ref = [r for r in pool if complete(r, NUMERIC[:1])]"),
 ("first_seen check uses the decision time", "        if r.first_seen_at is not None and r.first_seen_at > as_of:", "        if r.first_seen_at is not None and r.first_seen_at > as_of + 86400.0:"),
 ("AC3 on a WARMUP target uses the whole pool", '                reasons.append("REGIME_UNKNOWN")\n                ref = []', '                ref = ref'),
 ("same creator only excluded in AC1", "    cset = {r.decision_key for r in cands}" if False else '        cset = {r.decision_key for r in cands}', '        cset = {r.decision_key for r in pool if r.mint != target.mint}'),
]
orig = TARGET.read_text()
res = []
try:
    for name, a, b in M:
        n = orig.count(a)
        if n != 1:
            res.append({"mutation": name, "applied": False, "count": n}); continue
        TARGET.write_text(orig.replace(a, b))
        r = subprocess.run([sys.executable, "-B", "-m", "pytest", TEST, "-q", "-x", "-p", "no:cacheprovider"], cwd=REPO, capture_output=True, text=True)
        first = next((l for l in r.stdout.splitlines() if l.startswith(("FAILED", "ERROR"))), "")
        res.append({"mutation": name, "applied": True, "caught": r.returncode != 0, "first_failure": first[:160]})
        TARGET.write_text(orig)
finally:
    TARGET.write_text(orig)
print(json.dumps(res, indent=1))
json.dump(res, open(sys.argv[1], "w"), indent=1)
