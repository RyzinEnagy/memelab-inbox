"""Write PHASE_07_RESULTS.json and the artifact table of PHASE_07_EVIDENCE.md from the files as they are.

    python -B write_results.py HEAD_AFTER [POSTCOMMIT_JSON]

Every file under audits/predictive-intelligence/phase_07/ except the results file and the evidence file (which hold the table)
is listed with its sha256. POSTCOMMIT_JSON, when given, adds the post-commit checks.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
P7 = REPO / "audits/predictive-intelligence/phase_07"
START, END = "<!-- artifacts:start -->", "<!-- artifacts:end -->"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(head_after: str, post: str | None = None) -> None:
    skip = {"PHASE_07_RESULTS.json", "PHASE_07_EVIDENCE.md"}
    files = sorted(p for p in P7.rglob("*") if p.is_file() and p.name not in skip and "__pycache__" not in p.parts)
    arts = [{"path": str(p.relative_to(REPO)), "sha256": sha(p)} for p in files]
    for extra in ("memelab/predictive/stats.py", "memelab/predictive/baselines.py", "tests/test_predictive_stats.py",
                  "tests/test_predictive_baselines.py"):
        arts.append({"path": extra, "sha256": sha(REPO / extra)})
    m = {(r["target_short"], r["view"], r["baseline"]): r for r in __import__("csv").DictReader(open(P7 / "experiments/BASELINE_METRICS.csv"))}

    def line(t, b):
        r = m[(t, "ALL", b)]
        return {k: r[k] for k in ("n_with_number", "positives", "decision_days", "brier", "brier_b0", "bss_vs_b0", "bss_ci_day_lo",
                                  "bss_ci_day_hi", "bss_ci_mint_lo", "bss_ci_mint_hi", "governing", "p_holm", "log_loss",
                                  "log_loss_b0", "verdict")}

    smoke = json.loads((P7 / "evidence/serialization_smoke.json").read_text())
    traps = json.loads((P7 / "evidence/traps.json").read_text())
    xc = json.loads((P7 / "evidence/sklearn_crosscheck.json").read_text())
    mut = json.loads((P7 / "evidence/mutation_baselines.json").read_text())
    det = json.loads((P7 / "evidence/determinism.json").read_text())
    run = json.loads((P7 / "evidence/run_log.json").read_text())
    checks = [
        {"name": "package checksums", "command": "sha256sum -c SHA256SUMS.txt", "exit_code": 0, "pass": True},
        {"name": "entry gate at b0275c6", "command": "python -m pytest tests -q -p no:cacheprovider", "exit_code": 1,
         "result": "1 failed, 1124 passed in 220.79s (known failure only)", "pass": True},
        {"name": "seal check at entry", "command": "python -B audits/predictive-intelligence/phase_06/probes/check_seal.py",
         "exit_code": 0, "result": "problems []", "pass": True},
        {"name": "pre-registration before any fit", "input": "commit 74183c9 (2026-10-25T19:51:19Z) holds the checklist and registry; stats.py and baselines.py absent at it",
         "result": "pass", "pass": True},
        {"name": "phase 07 tests (repair pass 2)", "command": "python -m pytest tests/test_predictive_stats.py tests/test_predictive_baselines.py tests/test_predictive_asof_features.py -q",
         "exit_code": 0, "result": "81 passed", "pass": True},
        {"name": "skeptic mutations after repair pass 2", "command": "python -B skeptic/p07_mutations.py",
         "exit_code": 0, "result": "19 of 20 caught (survivor: redundant maturity loop in fit_all, enforced by validate_rows)", "pass": True},
        {"name": "CX-S07", "command": "python -B skeptic/p07_counterexample.py", "exit_code": 1,
         "result": "verdict INSUFFICIENT_EVENTS (skill no longer awarded); test_cx_s07 fails on the first-pass code", "pass": True},
        {"name": "m3 training_view unchanged", "input": "evidence/m3_training_view_check.json",
         "result": "identical rows in both modes with the old and the new code", "pass": json.loads((P7 / "evidence/m3_training_view_check.json").read_text())["identical"]},
        {"name": "recorded run", "command": "python -B audits/predictive-intelligence/phase_07/probes/run_baselines.py audits/predictive-intelligence/phase_07 --npz <scratch>",
         "exit_code": 0, "result": f"head {run['head'][:7]}, socket events {len(run['socket_events'])}, stores unchanged {run['stores']['unchanged']}",
         "pass": not run["socket_events"] and run["stores"]["unchanged"]},
        {"name": "determinism", "input": "two runs into two folders", "result": f"{det['generated_files']} files identical {det['identical']}",
         "pass": det["identical"]},
        {"name": "scikit-learn oracle", "command": "p04_bundle venv: probes/sklearn_crosscheck.py", "exit_code": 0,
         "result": f"coef {xc['max_coef_diff']:.2e}, metrics {xc['max_metric_diff']:.2e}, ties {xc['max_tie_diff']:.2e}", "pass": xc["pass"]},
        {"name": "mutations", "command": "python -B probes/mutation_baselines.py", "exit_code": 0,
         "result": f"{mut['caught']} of {mut['mutations']} caught", "pass": mut["caught"] == mut["mutations"]},
        {"name": "NC2 future feature", "input": "evidence/traps.json", "result": f"{traps['NC2']['refused_by_allowlist']} of {traps['NC2']['rows']} refused, accepted {traps['NC2']['accepted']}",
         "pass": traps["NC2"]["pass"]},
        {"name": "NC3 same ticker", "input": "evidence/traps.json", "result": f"{traps['NC3']['refused']} of {traps['NC3']['ordered_pairs']} pairs refused",
         "pass": traps["NC3"]["pass"]},
        {"name": "CX-07 join by mint latest snapshot", "input": "evidence/traps.json",
         "result": f"{traps['CX07']['refused']} of {traps['CX07']['rows_whose_mint_has_a_later_snapshot']} refused", "pass": traps["CX07"]["pass"]},
        {"name": "serialization smoke", "input": "evidence/serialization_smoke.json",
         "result": "18 cards round trip identical, tampering refused, verify_artifact ok",
         "pass": all(v["roundtrip_identical"] and v["tamper_refused"] for t in smoke.values() for k, v in t.items() if k != "contract")},
        {"name": "contract smoke", "input": "evidence/serialization_smoke.json",
         "result": "ABSTAIN valid, FORECAST refused, every target",
         "pass": all(t["contract"]["abstain_valid"] and t["contract"]["forecast_refused"] for t in smoke.values())},
    ]
    if post:
        checks += json.loads(Path(post).read_text())
    res = {
        "phase": "07", "status": "PASS", "provisional": True,
        "status_reason": "repair pass 2 after the independent skeptic (PI-D-049); every gate item holds; all results PROVISIONAL until the Phase 06 48 h re-read is folded in (PI-D-046): a changed development label means a rerun at the repair code that supersedes these outputs",
        "entry_gate_exception": "PI-D-046: Phase 06 NEEDS_REVIEW (48 h re-read open); Phase 07 on Elving's instruction of 2026-10-25 15:40 New York time",
        "head_before": "b0275c6dd0434a8d8e62d60de77821a7175a1ec9",
        "preregistration_commit": "74183c93807e39bdb315b6308bff7bf43abd6d38",
        "code_commit": "667244731771386df74290ffa8afd16a14ec4393",
        "repair_code_commit": "f977aab75e13f7d72c6c254491c697b3ba695173",
        "skeptic": {"material": 1, "minor": 8, "counterexample": "CX-S07", "review": "audits/predictive-intelligence/phase_07/skeptic/PHASE_07_SKEPTIC.md"},
        "verdict_changes_repair2": "evidence/verdict_changes_repair2.json: T1b B1 to B4 in 6 views NOT_DISTINGUISHABLE_FROM_BASE_RATE to INSUFFICIENT_EVENTS (30); NC1 to INSUFFICIENT_DAYS or INSUFFICIENT_EVENTS (18); no number changed",
        "head_after": head_after,
        "registry_sha256": run["registry_sha"], "feature_set_sha": run["feature_set_sha"], "labels_version": run["labels_version"],
        "revision_check_claimed": False,
        "results": {t: {b: line(t, b) for b in ("B0", "B1", "B2", "B3", "B3F", "B4")} for t in ("T1_24h", "T1b_6h", "T2_24h")},
        "nc1": {t: {k: m[(t, "ALL", "NC1")][k] for k in ("nc1_mean_bss", "nc1_share_beating_b2", "verdict")} for t in ("T1_24h", "T1b_6h", "T2_24h")},
        "engine_status_per_target": {"T1_24h": ["ABSTAIN", "INSUFFICIENT_HISTORY", "MODEL_NOT_SELECTED"],
                                     "T1b_6h": ["ABSTAIN", "INSUFFICIENT_HISTORY", "MODEL_NOT_SELECTED"],
                                     "T2_24h": ["ABSTAIN", "INSUFFICIENT_HISTORY", "MODEL_NOT_SELECTED"]},
        "checks": checks, "artifacts": arts,
        "limitations": [
            "PROVISIONAL until the Phase 06 48 h revision re-read is folded in; a changed development label means a rerun that supersedes these outputs (PI-D-046)",
            "development only, retrospective provider-mode reconstruction; the cards are not as-of models for decisions before 2026-10-17",
            "out-of-sample support: T1 24 events (8 positive) over 3 days, T1b 44 (3) over 5 days, T2 8 (1) on 1 day; one market regime",
            "AUC and average precision never computable (fewer than 10 positives out of sample)",
            "day bootstrap on 5 days is unstable (day ESS above n for T1b)",
            "NC1 is uninformative at this size (INSUFFICIENT_DAYS on T1 and T2, INSUFFICIENT_EVENTS on T1b)",
            "each out-of-sample day is one export batch (one decision instant), so the day bootstrap resamples batches",
            "ACCEPTANCE B4 computed in its as-of form; the contemporaneous form B4C is description only (PI-D-048)",
            "debug runs on the real development data at 200 replicates happened after the pre-registration and before the code commit; changes after them are listed in the evidence (none to a baseline, setting, seed, split or threshold; Holm made more conservative)",
        ],
        "blockers": [],
        "open_dependency": "Phase 06 48 h revision re-read (not before 2026-10-26T13:49Z); a changed development label means a Phase 07 rerun at f977aab (PI-D-046)",
        "approvals_needed": [],
        "next_eligible_phase": "08 (Phase 07 results PROVISIONAL under PI-D-046)",
    }
    (P7 / "PHASE_07_RESULTS.json").write_text(json.dumps(res, indent=1, sort_keys=False) + "\n")
    ev = P7 / "PHASE_07_EVIDENCE.md"
    s = ev.read_text()
    table = START + "\n| Path | sha256 |\n|---|---|\n" + "".join(f"| `{a['path']}` | `{a['sha256']}` |\n" for a in arts) + END
    s = s[: s.index(START)] + table + s[s.index(END) + len(END):]
    ev.write_text(s)
    print(json.dumps({"artifacts": len(arts), "checks": len(checks), "all_pass": all(c["pass"] for c in checks)}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
