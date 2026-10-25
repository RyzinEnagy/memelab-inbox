"""Phase 08 skeptic: mutations of memelab/predictive/technical.py not in the phase's own probe. Each is applied in the skeptic
clone, tests/test_predictive_technical.py is run, and the file is restored."""
import json, subprocess, sys
from pathlib import Path
REPO = Path("/home/claude/pi_orchestration/skeptic_08")
TARGET = REPO / "memelab/predictive/technical.py"
TEST = "tests/test_predictive_technical.py"
M = [
 ("availability is the earliest input, not the latest (hides a late input from the P36 guard)",
  'round(max(float(c["_avail"]) for c in inputs), 6)', 'round(min(float(c["_avail"]) for c in inputs), 6)'),
 ("test rows standardised with their own statistics (test-time prep refit)",
  'prep, lr = K.Prep.from_dict(body["prep"]), K.Logistic.from_dict(body["logistic"])',
  'prep, lr = K.Prep().fit(X), K.Logistic.from_dict(body["logistic"])'),
 ("as-of view one provider lag late", "view = F.AsOfView(con, T, mode)", "view = F.AsOfView(con, T + 300.0, mode)"),
 ("series boundary may end an hour before T", "need_to = T - lag", "need_to = T - lag - 3600.0"),
 ("P13 guard lets the cutoff instant through only for later cards",
  'early = [e for e in examples if e.decision_time < float(card["training_cutoff"])]',
  'early = [e for e in examples if e.decision_time < float(card["training_cutoff"]) - 86400.0]'),
 ("predict-time as-of check removed", "        check_asof(examples, cols, as_of=None, with_labels=False)\n", ""),
 ("identity join ignores the decision time", ' or float(s["decision_time"]) != e.decision_time:', ':'),
 ("missing-reason swap at px", '("OUTSIDE_FETCHED_WINDOW" if cover_from > x - PERIOD_S else "NO_CANDLE_AVAILABLE")',
  '("NO_CANDLE_AVAILABLE" if cover_from > x - PERIOD_S else "OUTSIDE_FETCHED_WINDOW")'),
 ("v2 derived tolerance loosened to 1e-3", "abs(a - _r(b)) > 1e-9 * max(1.0, abs(a))", "abs(a - _r(b)) > 1e-3 * max(1.0, abs(a))"),
 ("failed breakout uses <= the prior high", 'RH > PH and last["c"] < PH', 'RH > PH and last["c"] <= PH'),
 ("retest break counts a close equal to the prior high", 'broke = any(c["c"] > PH6 for c in w6)', 'broke = any(c["c"] >= PH6 for c in w6)'),
 ("stump split equality tolerance removed", "SPLIT_EPS = 1e-7", "SPLIT_EPS = 0.0"),
 ("stump min leaf off by one", "(nl >= self.min_leaf) & (nr >= self.min_leaf)", "(nl > self.min_leaf) & (nr > self.min_leaf)"),
 ("NC1 permutes only the first seed", "yy = np.random.default_rng(s).permutation(B.labels_of(train))", "yy = np.random.default_rng(0).permutation(B.labels_of(train))"),
 ("training rows not checked for maturity in fit", "if not (e.decision_time < cutoff and e.label_matures_at <= cutoff):", "if not (e.decision_time < cutoff):"),
 ("rows used by M2 do not require B2 columns", '"M2_T_LOGIT_B2": {"kind": "logit", "rows": list(M2_ROWS)', '"M2_T_LOGIT_B2": {"kind": "logit", "rows": list(TECH)'),
 ("relative volume window 1 h replaced by 2 h", "w1, why1 = win(H1)", "w1, why1 = win(2 * H1)"),
 ("last close age in seconds", "math.log1p((T - last[\"end_at\"]) / 60.0)", "math.log1p((T - last[\"end_at\"]) / 1.0)"),
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
