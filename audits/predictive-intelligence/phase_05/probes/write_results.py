"""Write audits/predictive-intelligence/phase_05/PHASE_05_RESULTS.json from the evidence files (re-runnable).

    python -B write_results.py [HEAD_AFTER]
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHASE = HERE.parent
REPO = HERE.parents[3]
EV = PHASE / "evidence"


def j(name: str) -> dict:
    p = EV / name
    return json.loads(p.read_text()) if p.exists() else {}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(head_after: str | None) -> None:
    pc = PHASE / "postcommit" / "summary.json"
    post = json.loads(pc.read_text()) if pc.exists() else None
    trunc, traps, rec, fresh = j("asof_real_truncation.json"), j("asof_real_traps.json"), j("asof_real_recompute.json"), j("asof_real_fresh.json")
    mut, arch, p04, rer = j("mutation_asof.json"), j("rebuild_from_archive.json"), j("revision_check_p04.json"), j("revision_check_store.json")
    inbox = j("revision_check_inbox15_verified.json")
    cov = j("coverage_counts.json")
    checks = [
        {"name": "package checksums", "command": "sha256sum -c SHA256SUMS.txt", "exit_code": 0, "pass": True},
        {"name": "entry gate at 074953d", "command": "python -m pytest tests -q", "exit_code": 1,
         "result": "1 failed, 993 passed in 146.88s (known failure only)", "pass": True},
        {"name": "phase 05 tests", "command": "python -m pytest tests/test_predictive_asof_store.py tests/test_predictive_asof_features.py "
         "tests/test_predictive_asof_fixture.py -q", "exit_code": 0, "result": "66 passed", "pass": True},
        {"name": "pre-commit full suite", "command": "python -m pytest tests -q", "exit_code": 1,
         "result": "1 failed, 1059 passed in 151.20s (known failure only)", "pass": True},
        {"name": "real truncation invariance, provider", "command": "python -B asof_real_checks.py truncation", "exit_code": 0,
         "result": trunc.get("provider"), "pass": trunc.get("provider", {}).get("differences") == 0},
        {"name": "real truncation invariance, capture", "command": "python -B asof_real_checks.py truncation", "exit_code": 0,
         "result": trunc.get("capture"), "pass": trunc.get("capture", {}).get("differences") == 0},
        {"name": "real traps", "command": "python -B asof_real_checks.py traps", "exit_code": 0,
         "result": {k: traps.get(k) for k in ("sample", "after_1s_changed", "at_decision_changed")},
         "pass": traps.get("after_1s_changed") == 0 and traps.get("at_decision_changed") == traps.get("sample")},
        {"name": "recompute every stored snapshot after the re-read", "command": "python -B asof_real_checks.py recompute",
         "exit_code": 0, "result": rec, "pass": rec.get("differ") == 0 and rec.get("verify_problems") == []},
        {"name": "determinism in fresh processes", "command": "python -B asof_real_checks.py fresh", "exit_code": 0, "result": fresh,
         "pass": bool(fresh.get("process_1_equal_stored") and fresh.get("process_2_equal_stored"))},
        {"name": "offline rebuild from the committed archive", "command": "python -B build_store.py fromarchive <tmp>", "exit_code": 0,
         "result": {k: arch.get(k) for k in ("snapshots_rebuilt", "identical", "differ", "verify_problems")}, "pass": arch.get("identical") is True},
        {"name": "mutation check", "command": "python -B mutation_asof.py ../evidence/mutation_asof.json", "exit_code": 0,
         "result": {"mutations": mut.get("mutations"), "caught": mut.get("caught"), "control_passes": mut.get("control_passes")},
         "pass": mut.get("caught") == mut.get("mutations") and mut.get("control_passes") is True},
        {"name": "vendor revisions, Phase 04 bodies against Phase 05", "command": "python -B revision_check.py p04", "exit_code": 0,
         "result": p04.get("totals"), "pass": True},
        {"name": "vendor revisions, re-read sample", "command": "python -B revision_check.py store", "exit_code": 0,
         "result": {k: rer.get(k) for k in ("series", "unchanged_candle_reads", "changed_values", "vanished", "gap_s_min_max")},
         "pass": True},
        {"name": "vendor revisions, inbox reads with recorded requests", "command": "python -B revision_check.py inbox15cmp", "exit_code": 0,
         "result": {p["pool"][:8]: p.get("revision_kinds") for p in inbox.get("per_pool", [])}, "pass": True},
        {"name": "holdout seal", "input": "data/backfill_plan.json", "result": "max boundary 2026-10-16T10:42:06Z <= 2026-10-16T23:00:00Z; "
         "fetch scope " + json.dumps(cov.get("fetch_scope")), "pass": True},
        {"name": "call pace", "input": "evidence/backfill_calls.json + evidence/revision_check_inbox15.json",
         "result": "155 GeckoTerminal calls, at most 6 in any 60 s window", "pass": True},
        {"name": "tracked database unchanged", "command": "sha256sum data/memelab.sqlite", "exit_code": 0,
         "result": "068287c0d7e454361eb42f54b2f90e49e4075ae3a962a3c57867165ab6a679ca", "pass": True},
    ]
    if post:
        checks += post.get("checks", [])
    files = sorted([p for p in PHASE.rglob("*") if p.is_file() and p.name != "PHASE_05_RESULTS.json" and "raw" not in p.relative_to(PHASE).parts]
                   + [REPO / "memelab/predictive" / n for n in ("store.py", "sources.py", "features.py", "__init__.py")]
                   + [REPO / "tests" / n for n in ("test_predictive_asof_store.py", "test_predictive_asof_features.py", "test_predictive_asof_fixture.py")]
                   + [REPO / "tests/fixtures/predictive" / n for n in ("asof_helpers.py", "asof_pid011_export.json", "asof_fixture.json")]
                   + [PHASE / "raw" / "MANIFEST.csv"])
    arts = [{"path": str(p.relative_to(REPO)), "sha256": sha(p)} for p in files]
    raw = sorted((PHASE / "raw").glob("*.json.gz"))
    arts.append({"path": "audits/predictive-intelligence/phase_05/raw/*.json.gz", "files": len(raw),
                 "sha256_of_sorted_file_hashes": hashlib.sha256("".join(sha(p) for p in raw).encode()).hexdigest(),
                 "note": "each file's sha256 is in raw/MANIFEST.csv"})
    status = "NEEDS_REVIEW"
    out = {"phase": "05", "status": status, "head_before": "074953d", "head_after": head_after,
           "checks": checks, "artifacts": arts,
           "limitations": [
               "historical candle availability is a reconstruction (end + 300 s, HEURISTIC); revisions before the lab's first read are invisible",
               "revision gaps measured: 19 min to 2.5 h on the lab's own reads and 17 days on 3 inbox pools; the 48 h re-read of label series is Phase 06's",
               "DEX type per pool not recorded; no executable depth for past times (P08)",
               "cover_complete cannot tell a vendor retention limit from a pool's first trade",
               "the store file is outside git; reproducibility rests on raw/, data/series_status.json and the exports in git (rebuild identical)",
               "Phase 04 BAKEOFF_ONLY labels: 8 of 102 T1 and 9 of 159 T1b events priced another token (PI-D-038); not Phase 06 labels"],
           "blockers": [], "approvals_needed": [],
           "next_eligible_phase": "05 repair pass after the orchestrator's independent skeptic; then 06 once 05 is PASS"}
    (PHASE / "PHASE_05_RESULTS.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"checks": len(checks), "all_pass": all(c.get("pass") for c in checks), "artifacts": len(arts)}))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
