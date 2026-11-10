"""CM-2 G9: mutation probe on memelab/predictive/promotion.py and the daily cycle's guards. Usage: mutation_probe.py <scratch_dir>
Clones the repository at HEAD into <scratch_dir> (never edits this checkout), applies one mutation at a time, runs the named
test file and records whether a test failed (caught). Writes evidence/mutation_probe.json in this checkout."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
OUT = HERE.parent / "evidence/mutation_probe.json"
PROMO = "memelab/predictive/promotion.py"
DAILY = "audits/predictive-intelligence/daily/predictive_daily.py"
G = "tests/test_predictive_cm2_guards.py"           # PI-D-126: tests added for the survivors of the first probe run
TP, TD = ("tests/test_predictive_promotion.py", G), ("tests/test_predictive_daily.py", G)
M = [
    ("P01 window start not strict", PROMO, 'float(r["decision_time"]) > lo and', 'float(r["decision_time"]) >= lo - 1e9 and', TP),
    ("P02 incomplete day does not stop", PROMO, "        if not all(r[\"final\"] for r in days[d]):\n            break", "        if False:\n            break", TP),
    ("P03 events minimum off by one", PROMO, 'if n >= RULE["min_events"] and k', 'if n >= RULE["min_events"] - 1 and k', TP),
    ("P04 per-class minimum dropped (window)", PROMO, 'and k >= RULE["min_per_class"] and n - k >= RULE["min_per_class"] and nd', 'and nd', TP),
    ("P05 day minimum dropped (window)", PROMO, ' and nd >= RULE["min_effective_days"]:\n            return {"state": CLOSED', ':\n            return {"state": CLOSED', TP),
    ("P06 freeze check removed", PROMO, 'if not float(r["decision_time"]) > float(freeze):', 'if False:', TP),
    ("P07 ledger order check removed", PROMO, 'and r["prediction_seq"] < r["outcome_seq"]):', 'or True):', TP),
    ("P08 commit-before-read check weakened", PROMO, 'not float(pc) < float(lo):', 'not float(pc) <= float(lo) + 1e9:', TP),
    ("P09 registration check removed", PROMO, 'if reg is None or float(reg) > float(r["decision_time"]):', 'if reg is None:', TP),
    ("P10 stale check removed", PROMO, 'if r.get("version_stale") is not False:', 'if r.get("version_stale") is True and False:', TP),
    ("P11 admissibility not a reason", PROMO, '    if adm:\n        reasons.append("WINDOW_NOT_ADMISSIBLE")', '    if adm and False:\n        reasons.append("WINDOW_NOT_ADMISSIBLE")', TP),
    ("P12 tests flag ignored", PROMO, 'reasons.append("TESTS_NOT_PASSED")', 'pass', TP),
    ("P13 event minimum dropped (evaluate)", PROMO, '        reasons.append("BELOW_EVENT_MINIMUM")', '        pass', TP),
    ("P14 day minimum dropped (evaluate)", PROMO, '        reasons.append("BELOW_DAY_MINIMUM")', '        pass', TP),
    ("P15 skill bound at or above 0 accepted", PROMO, 'sk["lower"] > RULE["skill"]["lower_bound_gt"]', 'sk["lower"] >= RULE["skill"]["lower_bound_gt"] - 1', TP),
    ("P16 no Bonferroni (q = alpha)", PROMO, 'return RULE["skill"]["alpha"] / (n_search * windows)', 'return RULE["skill"]["alpha"]', TP),
    ("P17 windows not counted in correction", PROMO, 'int(math.ceil(10 * n_search * windows / s["alpha"]))', 'int(math.ceil(10 * n_search / s["alpha"]))', TP),
    ("P18 governing bound is the max of units", PROMO, '"lower": min(lows.values())', '"lower": max(lows.values())', TP),
    ("P19 calibration ignored", PROMO, '            reasons.append("CALIBRATION_FAILED")', '            pass', TP),
    ("P20 undefined replicate counts for skill", PROMO, '1.0 - num / den, -np.inf)', '1.0 - num / den, np.inf)', TP),
    ("P21 VE without a second window", PROMO, 'for r in results[shadow_at + 1:])', 'for r in results[shadow_at:])', TP),
    ("P22 VE ignores B2 comparison", PROMO, 'and r.get("not_worse_than_b2") is True for r', 'for r', TP),
    ("P23 registration at a publishable level allowed", PROMO, '    if kw["level"] in PUBLISHABLE:\n        raise', '    if False:\n        raise', TP),
    ("P24 log chain not checked", PROMO, 'if ev.get("seq") != i or ev.get("prev") != prev or ev.get("event_id") != _event_id(ev):', 'if ev.get("seq") != i:', TP),
    ("P25 retire twice allowed", PROMO, '            if i in retired:\n                raise', '            if False:\n                raise', TP),
    ("D01 recipe pin not checked", DAILY, 'if fsha(RECIPE) != RECIPE_SHA256:', 'if False:', TD),
    ("D02 governing pin not checked", DAILY, 'if C.governing_sha256() != GOVERNING_SHA:', 'if False:', TD),
    ("D03 rate check above 6 a minute", DAILY, 'for t in ts) > 6:', 'for t in ts) > 60:', TD),
    ("D04 allowed paths widened", DAILY, 'ALLOWED = (REL, COST_REL)', 'ALLOWED = (REL, COST_REL, "data", "memelab")', TD),
    ("D05 no-commit mode reads labels", DAILY, '    offline = bool(args.no_commit)', '    offline = False', TD),
    ("D06 predictions not committed before reads", DAILY, '            commit(f"predictive-intel daily: {len(rows)} decisions predicted ({st[\'day\']})", reason="PREDICTION_COMMIT_FAILED")', '            pass', TD),
    ("D07 tampered ledger not refused", DAILY, '            if LEDGER.exists() and not M.verify(LEDGER)["ok"]:\n                raise Fail("PREFLIGHT_FAILED", "the working ledger does not verify")', '            pass', TD),
    ("D08 decisions at the freeze predicted", DAILY, 'AND decision_time > ? ', 'AND decision_time > ? - 1e10 ', TD),
    ("D09 label read without token", DAILY, '        url = SRC.gt_url(d["pool"], b, token=d["mint"])\n        if "token="', '        url = SRC.gt_url(d["pool"], b)\n        if "token="', TD),
]


def sh(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=1800)


def main(scratch: str) -> None:
    s = Path(scratch)
    c = s / "mut"
    sh(["rm", "-rf", str(c)], REPO)
    s.mkdir(parents=True, exist_ok=True)
    sh(["git", "clone", "-q", "--no-local", str(REPO), str(c)], REPO)
    sh(["git", "checkout", "-q", subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()], c)
    sh(["git", "config", "user.email", "m@localhost"], c)
    sh(["git", "config", "user.name", "m"], c)
    sh(["git", "fetch", "-q", str(REPO), "refs/remotes/origin/main:refs/remotes/origin/main"], c)
    base = {}
    for t in (TP, TD):
        r = sh([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *t], c)
        base[" ".join(t)] = {"exit": r.returncode, "tail": r.stdout.strip().splitlines()[-1:]}
    res = []
    for name, f, old, new, t in M:
        p = c / f
        orig = p.read_text()
        n = orig.count(old)
        if n != 1:
            res.append({"mutation": name, "file": f, "applied": False, "occurrences": n})
            continue
        p.write_text(orig.replace(old, new))
        # committed, because the end-to-end tests clone the committed tree of this checkout (an uncommitted mutation would
        # never reach the script they run); reset afterwards
        sh(["git", "commit", "-q", "-am", f"mutation {name}"], c)
        try:
            r = sh([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *t], c)
        finally:
            sh(["git", "reset", "-q", "--hard", "HEAD~1"], c)
            assert p.read_text() == orig
        res.append({"mutation": name, "file": f, "applied": True, "tests": list(t), "exit": r.returncode, "caught": r.returncode != 0,
                    "tail": r.stdout.strip().splitlines()[-1:]})
        print(name, "caught" if r.returncode else "SURVIVED", flush=True)
    out = {"head": subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
           "baseline": base, "mutations": res, "applied": sum(r["applied"] for r in res),
           "caught": sum(r.get("caught", False) for r in res), "survived": [r["mutation"] for r in res if r["applied"] and not r["caught"]],
           "not_applied": [r["mutation"] for r in res if not r["applied"]]}
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: out[k] for k in ("applied", "caught", "survived", "not_applied", "baseline")}))


if __name__ == "__main__":
    main(sys.argv[1])
