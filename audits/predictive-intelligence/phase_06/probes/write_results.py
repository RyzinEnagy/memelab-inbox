"""Phase 06: write PHASE_06_RESULTS.json from the evidence files (artifact hashes computed here).

    python -B write_results.py [HEAD_AFTER] [POSTCOMMIT_JSON]
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PHASE = Path(__file__).resolve().parent.parent
REPO = PHASE.parents[2]


def sha(p):
    return hashlib.sha256((REPO / p).read_bytes()).hexdigest()


def j(p):
    return json.loads((PHASE / p).read_text())


def main():
    head_after = sys.argv[1] if len(sys.argv) > 1 else None
    post = json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv) > 2 else None
    run, cov, rr, c05, mut, rb = (j("evidence/labels_run.json"), j("labels/coverage.json"), j("evidence/revision_reread.json"),
                                 j("evidence/revision_vs_phase05.json"), j("evidence/mutation_labels.json"),
                                 j("evidence/rebuild_from_archive.json"))
    seal = j("sealed/SEAL.json")
    checks = [
        {"name": "package checksums", "command": "sha256sum -c SHA256SUMS.txt", "exit_code": 0, "pass": True},
        {"name": "entry gate at ed82f3a", "command": "python -m pytest tests -q", "exit_code": 1,
         "result": "1 failed, 1066 passed in 152.58s (known failure only)", "pass": True},
        {"name": "label tests", "command": "python -m pytest tests/test_predictive_labels.py -q", "exit_code": 0, "result": "58 passed (repair pass 2)", "pass": True},
        {"name": "contract tests after CC-03", "command": "python -m pytest tests/test_predictive_contract.py -q", "exit_code": 0,
         "result": "66 passed", "pass": True},
        {"name": "mutation check", "command": "python -B probes/mutation_labels.py evidence/mutation_labels.json", "exit_code": 0,
         "result": f"{mut['caught']} of {mut['mutations']} caught, control exit {mut['control_exit']}", "pass": mut["caught"] == mut["mutations"]},
        {"name": "development labels", "input": "evidence/labels_run.json", "result": run["dev_class"], "pass": True},
        {"name": "cross-target invariants (CX-06)", "input": "evidence/labels_run.json", "result": run["cross_target_violations"],
         "pass": run["cross_target_violations"] == {"development": 0, "holdout": 0}},
        {"name": "offline rebuild from the committed archive", "command": "python -B probes/make_labels.py rebuild", "exit_code": 0,
         "result": rb, "pass": rb["differences"] == 0},
        {"name": "holdout seal", "command": "python -B probes/check_seal.py", "exit_code": 0,
         "result": {"seal_sha256": seal["seal_sha256"], "problems": []}, "pass": True},
        {"name": "revision re-read in session (P07, short gap)", "input": "evidence/revision_reread.json", "result": rr["summary"], "pass": True},
        {"name": "revision against Phase 05 reads", "input": "evidence/revision_vs_phase05.json",
         "result": {k: c05[k] for k in ("read_pairs", "positions_compared", "unchanged", "changed_by_fields", "labels_same", "labels_different")},
         "pass": c05["labels_different"] == 0},
        {"name": "independent skeptic", "input": "skeptic/PHASE_06_SKEPTIC.md", "result": "1 MATERIAL (M1 tests), 8 minor, counterexample CX-S06; all development counts reproduced independently", "pass": True},
        {"name": "repair pass 2", "input": "evidence/repair2_checks.json", "result": json.loads((PHASE / "evidence/repair2_checks.json").read_text())["relabel_comparison"], "pass": True},
        {"name": "asof store tests after the identity change", "command": "python -m pytest tests/test_predictive_asof_store.py tests/test_predictive_asof_features.py tests/test_predictive_asof_fixture.py -q", "exit_code": 0, "result": "passed (197 with the label and contract tests)", "pass": True},
        {"name": "frozen 48 h revision re-read (PI-D-018)", "command": "python -B probes/make_labels.py reread48",
         "result": "NOT RUN: earliest 2026-10-26T13:05Z to 13:49Z for the 16 sampled reads", "pass": False},
        {"name": "pacing", "input": "evidence/label_calls.json + sealed/label_calls.json",
         "result": "both logs at most 6 calls in any 60 s window; development log 280 calls, 25 HTTP 429 retried; holdout counts inside sealed/ (m8); 0 Firecrawl credits", "pass": True},
    ]
    if post:
        checks += post
    arts = ["memelab/predictive/labels.py", "memelab/predictive/contract.py", "memelab/predictive/__init__.py",
            "tests/test_predictive_labels.py", "tests/test_predictive_contract.py", "tests/fixtures/predictive/labels_hand_trace.json"]
    arts += [str(p.relative_to(REPO)) for p in sorted((PHASE / "labels").glob("*"))]
    arts += [str((PHASE / x).relative_to(REPO)) for x in ("ACCEPTANCE_CHECKLIST.md", "SKEPTIC_PACKET.md", "PHASE_06_EVIDENCE.md",
                                                         "sealed/SEAL.json", "sealed/holdout_labels.jsonl.gz", "raw/MANIFEST.csv",
                                                         "data/read_map.json", "data/read_plan.json", "data/revision_sample.json")]
    arts += [str(p.relative_to(REPO)) for p in sorted((PHASE / "evidence").glob("*.json"))]
    arts += [str(p.relative_to(REPO)) for p in sorted((PHASE / "skeptic").glob("*"))]
    arts += ["memelab/predictive/store.py", "tests/test_predictive_asof_store.py", "audits/predictive-intelligence/phase_05/data/FEATURE_STORE_CONTRACT.md"]
    out = {
        "phase": "06", "status": "NEEDS_REVIEW", "open_items": ["frozen 48 h revision re-read (PI-D-018), not before 2026-10-26T13:49Z"], "head_before": "ed82f3a9d89b091579bd4ed43646acf14e355d64", "repair_pass_2_head_before": "121384bf25adbe4dd004d4d9da2a2069e9af64a8", "head_after": head_after,
        "registry_sha256": "4b4aabce77a5a6f9214c4cfdddf5223f410ed6126410cf4b213b3c80b035f896",
        "holdout_labels_sha256": seal["files"]["holdout_labels.jsonl.gz"]["sha256"], "seal_sha256": seal["seal_sha256"], "seal_json_sha256": hashlib.sha256((PHASE / "sealed/SEAL.json").read_bytes()).hexdigest(),
        "development_label_counts": run["dev_class"], "holdout_state_counts": run["holdout_state"],
        "checks": checks,
        "artifacts": [{"path": a, "sha256": sha(a)} for a in arts],
        "limitations": [
            "first-pass public records stated holdout call counts that may bound the number of holdout T2 decisions needing other pools (m8, PI-D-045 item 6); removed from current records, history not rewritten",
            "CC-03 pre-registration is consistent with file times but not provable from git (m5, PI-D-045 item 5)",
            "the frozen 48 h revision re-read (PI-D-018) has not run; earliest 2026-10-26T13:05Z",
            "TRADING_HALT does not occur in development; the halt path is shown on fixtures and as one real reference-pool flag",
            "development spans 9 (T1), 10 (T1b) and 8 (T2) decision days of one regime",
            "CURRENT_VENDOR_LIST decisions are censored far more often than PIT_RECORDED ones (39 of 274 against 2 of 521)",
            "provider-lag availability is a HEURISTIC reconstruction; label_observed_at is a 2026-10-24 retrieval time",
            "price-path labels only: no fill, size, depth or proceeds"],
        "blockers": ["time: the 48 h revision re-read cannot run before 2026-10-26T13:49Z for all 16 sampled reads (PI-D-041 item 5, PI-D-045 item 8); the only open gate item"],
        "approvals_needed": [],
        "next_eligible_phase": "none until the 48 h revision re-read has run (or its timing is decided by a recorded decision); then 07",
    }
    (PHASE / "PHASE_06_RESULTS.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"status": out["status"], "checks": len(checks), "artifacts": len(out["artifacts"])}))


if __name__ == "__main__":
    main()
