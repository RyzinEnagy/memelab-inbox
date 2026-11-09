"""Phase 20 skeptic: mutate the system under test (not the audit code) and confirm the audit's checks fail.

    python -B p20_mutations.py WORKTREE OUT.json

WORKTREE is a scratch git worktree of the branch (never the shared checkout). Each mutation replaces one exact string in one
lab module, runs the named check(s) under `unshare -n` with a temp MEMELAB_DB, records the exit codes, and restores the file with
`git checkout`. A mutation is KILLED when at least one named check exits non-zero. Research only: no network, no vendor call.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2])
PROBE = "audits/predictive-intelligence/phase_20/probes/scenarios.py"
CROSS = "tests/test_predictive_phase20_cross.py"

# (id, file, old, new, checks); a check is "Pxx" (scenario probe) or "pytest:<-k expr>" (cross tests)
MUT = [
    ("M01 reference candle ignores provider lag", "memelab/predictive/contract.py",
     "if end + lag <= decision_time and end >= decision_time - max_age_s",
     "if end <= decision_time + period_s and end >= decision_time - max_age_s", ["P06"]),
    ("M02 path keeps the candle holding t_entry", "memelab/predictive/contract.py",
     "c for c in candles if float(c[0]) >= t_entry and", "c for c in candles if float(c[0]) + period_s > t_entry - period_s and",
     ["P06"]),
    ("M03 label_state always MATURED", "memelab/predictive/contract.py",
     'return "PENDING" if as_of < label_matures_at(target, decision_time) else "MATURED"', 'return "MATURED"', ["P05"]),
    ("M04 new-mint caveat not required", "memelab/predictive/abstention.py",
     'if (doc.get("cohort") or {}).get("new_mint") and NEW_MINT_CAVEAT not in cav:', "if False:", ["P12"]),
    ("M05 degeneracy never flat", "memelab/predictive/calibration.py",
     'return {"flat": ptp <= FLAT_PTP,', 'return {"flat": False,', ["P11"]),
    ("M06 minority note never flags a constant", "memelab/predictive/monitoring.py",
     '"constant_prediction": bool(n and np.ptp(pp) == 0)', '"constant_prediction": False', ["P10", "P11"]),
    ("M07 cost cap not enforced", "memelab/predictive/runtime.py",
     "if self.cost_per_call and self.cost + self.cost_per_call > self.max_cost:", "if False:", ["P48"]),
    ("M08 vendor identity check off", "memelab/predictive/labels.py",
     'if not ident.startswith("OK"):\n        return Read(identity=ident, raw_count=len(rows), **base)',
     'if False:\n        return Read(identity=ident, raw_count=len(rows), **base)', ["P01"]),
    ("M09 model staleness off", "memelab/predictive/registry.py",
     'out.append({"state": MODEL_STALE, "detail": f"stale after {_iso(stale_after(entry))}"})', "pass", ["P39", "P46"]),
    ("M10 drift alarm off", "memelab/predictive/registry.py",
     'out.append({"state": DRIFT_ALERT, "detail": f"alarm at {_iso(min(hits))}"})', "pass", ["P39"]),
    ("M11 report text check off", "memelab/predictive/reports.py",
     '    if not _plain(t):\n        raise ReportError("the text would carry a trading word")',
     '    if False:\n        raise ReportError("the text would carry a trading word")', ["P41", "P44"]),
    ("M12 CP20-1 training_after_cutoff off", "memelab/predictive/registry.py",
     '    cut = float(entry["training_cutoff"])\n    mt, mm = entry.get("max_train_decision_time"), entry.get("max_train_label_matures_at")',
     '    return None\n    cut = float(entry["training_cutoff"])\n    mt, mm = entry.get("max_train_decision_time"), entry.get("max_train_label_matures_at")',
     ["P05", "P43", "pytest:x06"]),
    ("M13 CP20-1 token identity check off", "memelab/predictive/integration.py",
     'if tok and (tok.get("mint") != tr["mint"] or tok.get("chain", tr["chain"]) != tr["chain"]):',
     "if False:", ["P01", "pytest:x02"]),
    ("M14 CP20-1 capture time check off", "memelab/predictive/integration.py",
     '        S.epoch_seconds(capture_time, "capture_time")\n', "        pass\n", ["pytest:x03"]),
    ("M15 CP20-1 recompute_point off", "memelab/predictive/integration.py",
     '    if trec.get("prediction_status") != "FORECAST":\n        return []\n    inputs, raw',
     '    return []\n    inputs, raw', ["pytest:carried"]),
    ("M16 fit_all maturity check off", "memelab/predictive/baselines.py",
     "if not (e.decision_time < cutoff and e.label_matures_at <= cutoff):", "if False:", ["P05", "P43"]),
    ("M17 dedup off (P35)", "memelab/predictive/integration.py",
     "    if all(have):\n        shown.append(dict(view, event=\"DUPLICATE\"",
     "    if False:\n        shown.append(dict(view, event=\"DUPLICATE\"", ["P35"]),
]


def run(check: str, env: dict) -> int:
    if check.startswith("pytest:"):
        cmd = ["unshare", "-n", sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", CROSS, "-k", check[7:]]
    else:
        cmd = ["unshare", "-n", sys.executable, "-B", PROBE, check]
    r = subprocess.run(cmd, cwd=WT, env=env, capture_output=True, text=True, timeout=900)
    return r.returncode


def main():
    env = dict(os.environ, MEMELAB_DB=str(Path(tempfile.mkdtemp(prefix="sk20m_")) / "lab.sqlite"), PYTHONDONTWRITEBYTECODE="1")
    out = []
    for mid, f, old, new, checks in MUT:
        p = WT / f
        src = p.read_text()
        n = src.count(old)
        row = {"id": mid, "file": f, "occurrences": n}
        if n != 1:
            row["error"] = "pattern not found exactly once"
            out.append(row)
            continue
        p.write_text(src.replace(old, new))
        try:
            row["exits"] = {c: run(c, env) for c in checks}
        finally:
            subprocess.run(["git", "checkout", "--", f], cwd=WT, check=True)
        row["killed"] = any(v != 0 for v in row["exits"].values())
        out.append(row)
        print(mid, row["exits"], "KILLED" if row["killed"] else "SURVIVED", flush=True)
    st = subprocess.run(["git", "status", "--porcelain"], cwd=WT, capture_output=True, text=True).stdout
    OUT.write_text(json.dumps({"worktree_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=WT, capture_output=True,
                                                                text=True).stdout.strip(),
                               "mutations": out, "killed": sum(1 for r in out if r.get("killed")), "total": len(out),
                               "git_status_after": st}, indent=1))


if __name__ == "__main__":
    main()
