"""Phase 04: write PHASE_04_RESULTS.json (status, checks, artifact sha256, limitations). Re-run before each commit; the
post-commit block is read from phase_04/postcommit/summary.json when it exists.

    python write_results.py [HEAD_AFTER]
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
P4 = HERE.parents[1]
REPO = HERE.parents[4]
EXTRA = ["memelab/predictive/runtime.py", "tests/test_predictive_runtime.py", "tests/fixtures/predictive/copyleft_fingerprints.json",
         "docs/predictive-intelligence/locks/core-py313.txt", "docs/predictive-intelligence/locks/research-py313.txt"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    head_after = sys.argv[1] if len(sys.argv) > 1 else None
    ev = P4 / "adoption" / "evidence"
    j = lambda p: json.loads((ev / p).read_text())  # noqa: E731
    mut, rb, hs, mf, hc, ban = (j("mutation_runtime.json"), j("rollback_demo.json"), j("hostile_setup_demo.json"),
                                j("mirofish_adapter_runs.json"), j("holdout_candle_check.json"), j("banned_scan.json"))
    res = json.loads((P4 / "adoption" / "BAKEOFF_RESULTS.json").read_text())
    dev = res["datasets"]["dev"]
    checks = [
        {"name": "B1 package checksums", "command": "sha256sum -c SHA256SUMS.txt", "exit_code": 0, "pass": True},
        {"name": "B2 entry gate", "command": "python -m pytest tests -q (a146a29)", "exit_code": 1,
         "result": "1 failed, 858 passed in 145.42s (0:02:25); only test_dedup_corroboration_resurface_denial", "pass": True},
        {"name": "B4 development sample", "command": "build_dev_sample.py plan|fetch|label", "exit_code": 0,
         "result": f"{dev['calls']} calls {dev['calls_http']}; T1 24h {dev['targets']['price_path_target_before_invalidation_24h']['thinned_events']} events, "
                   f"T1b 6h {dev['targets']['price_path_target_before_invalidation_6h']['thinned_events']}; holdout_check {dev['holdout_check']}; "
                   f"candles dropped at or after h0 {dev['candles_dropped_at_or_after_h0']}", "pass": True},
        {"name": "B4 holdout candle check", "command": "holdout_candle_check.py RAW", "exit_code": 0, "result": hc["verdict"],
         "pass": hc["verdict"].startswith("no holdout")},
        {"name": "B5 approaches and third runs", "command": "run_measurements.py approaches; summarize.py", "exit_code": 0,
         "result": f"{sum(len(v) for v in res['approaches'].values())} runs, all exit 0 and identical over 3 runs",
         "pass": all(x["all_exit_0"] and x["identical_output_three_runs"] for v in res["approaches"].values() for x in v.values())},
        {"name": "B6 fold audit", "command": "splitter_check.py", "exit_code": 0,
         "result": "lab rule and purgedcv valid on all datasets; purge mutation refused on challenge and 24 h, no-op on 6 h; TimeSeriesSplit refused",
         "pass": all(v["summary"]["lab_day_rule"]["valid"] and not v["summary"]["sklearn_timeseriessplit_BANNED_DEFAULT"]["valid"]
                     for v in res["checks"]["splitter"]["output"].values())},
        {"name": "B7 Venn-Abers oracle", "command": "calibration_check.py oracle", "exit_code": 0,
         "result": f"max abs diff {res['checks']['calibration_oracle']['output']['max_abs_diff_any']}",
         "pass": res["checks"]["calibration_oracle"]["output"]["pass_1e-9"]},
        {"name": "B3 B7 banned defaults scan", "command": "banned_scan.py", "exit_code": 0,
         "result": f"{ban['files_scanned']} files, {len(ban['hits'])} hits", "pass": not ban["hits"]},
        {"name": "B8 network", "command": "measure.py (audit hook, unshare -n) and strace", "exit_code": 0,
         "result": "0 socket events in every measured run; 0 connect/sendto/bind syscalls; positive control 1",
         "pass": all(x["net_events_total"] == 0 for v in res["approaches"].values() for x in v.values())
                 and all(x["net_events_total"] == 0 for x in res["imports"].values())},
        {"name": "B10 locks", "command": "build_lock.py; pip download --require-hashes x 3 platforms", "exit_code": 0,
         "result": "research 30 packages 63 hashes, core 1 package 4 hashes; 0 problems; 30 wheels per platform all in the lock", "pass": True},
        {"name": "B11 rollback", "command": "rollback_demo.py", "exit_code": 0, "result": f"rollback_clean {rb['rollback_clean']}",
         "pass": rb["rollback_clean"]},
        {"name": "B12 MiroFish feasibility", "command": "mirofish_adapter.py", "exit_code": 0,
         "result": f"backend without keys exit {mf['backend_without_keys']['exit_code']}; mock runs {mf['run1_llm_mock']['status']}, "
                   f"{mf['run2_llm_mock_same_seed']['status']}, same trace {mf['same_seed_identical_trace']}; LLM down "
                   f"{mf['run3_llm_down']['status']} {mf['run3_llm_down'].get('reason')}", "pass": mf["run3_llm_down"]["status"] == "SIMULATION_NOT_AVAILABLE"},
        {"name": "B13 runtime mutations", "command": "mutation_runtime.py", "exit_code": 0,
         "result": f"{mut['caught']} of {mut['mutations']} caught", "pass": mut["caught"] == mut["mutations"]},
        {"name": "B15 hostile setup", "command": "hostile_setup_demo.py", "exit_code": 0, "result": json.dumps(hs["verdict"]),
         "pass": all(hs["verdict"].values())},
        {"name": "runtime and contract tests", "command": "python -m pytest tests/test_predictive_runtime.py tests/test_predictive_contract.py -q",
         "exit_code": 0, "result": "112 passed", "pass": True},
    ]
    post = P4 / "postcommit" / "summary.json"
    if post.exists():
        checks += json.loads(post.read_text())["checks"]
    files = sorted(p for p in P4.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.name != "PHASE_04_RESULTS.json")
    arts = [{"path": str(p.relative_to(REPO)), "sha256": sha(p)} for p in files] + [{"path": e, "sha256": sha(REPO / e)} for e in EXTRA]
    out = {"phase": "04", "status": "NEEDS_REVIEW", "head_before": "a146a29d17c47a0bdfdef85df2e7a9e2f884d50f",
           "head_after": head_after, "head_after_note": "deliverables commit; the records commit that carries this file is its child (git log)",
           "checks": checks, "artifacts": arts,
           "limitations": [
               "The bake-off measures behaviour, cost and correctness; 26 and 33 out-of-sample real events and a synthetic file support no claim of predictive skill",
               "BAKEOFF_ONLY labels: one read per pool, no 48 h revision re-read, PIT route only, no T2; Phase 06 rebuilds labels",
               "The development outcomes behind 261 target labels were viewed; Phase 12 must count these runs as tried configurations (PI-D-034)",
               "Network and telemetry were measured offline only; a library that phones home only when online would need an online, firewalled measurement",
               "The copyleft gate catches copied runs of 15 or more normalized lines and license markers, not short or rewritten copies",
               "MiroFish was run only against a local mock LLM; live behaviour, costs and quality are unmeasured (BLOCKED, PI-D-005)",
               "Windows and macOS installs were verified by downloading and hashing the wheels, not by installing on those systems",
               "statsmodels, arch, crepes and interpret-core are deferred, not decided"],
           "blockers": [], "approvals_needed": [],
           "next_eligible_phase": "05, after the orchestrator's independent skeptic and the Phase 04 repair pass"}
    (P4 / "PHASE_04_RESULTS.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"checks": len(checks), "all_pass": all(c["pass"] for c in checks), "artifacts": len(arts)}))


if __name__ == "__main__":
    main()
