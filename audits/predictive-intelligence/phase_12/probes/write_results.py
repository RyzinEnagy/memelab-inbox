"""Write PHASE_12_RESULTS.json from the committed Phase 12 files (artifact sha256 computed here).

    python -B write_results.py [--head-after SHA] [--post FILE.json]
"""
import argparse
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PH = REPO / "audits/predictive-intelligence/phase_12"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--head-after", default=None)
    ap.add_argument("--post", default=None)
    ap.add_argument("--status", default="NEEDS_REVIEW")
    ap.add_argument("--repair", default=None, help="JSON file with repair-pass checks, limitations and commits")
    a = ap.parse_args()
    prim = json.loads((PH / "validation/PRIMARY_RESULTS.json").read_text())["primary"]
    checks = [
        ("G1 package checksums", "sha256sum -c SHA256SUMS.txt", "41 OK, 0 failed", 0, True),
        ("G2 entry suite at 63076ad", "python -m pytest tests -q -p no:cacheprovider", "1 failed, 1398 passed in 251.15s (known test_dedup_corroboration_resurface_denial only)", 1, True),
        ("G2 entry seal check", "python -B audits/predictive-intelligence/phase_06/probes/check_seal.py", "problems [] with the three pinned hashes", 0, True),
        ("G2 Phase 11 key check", "python -B audits/predictive-intelligence/phase_11/probes/verify_trace_analog.py audits/predictive-intelligence/phase_11", "0 differences", 0, True),
        ("G3 pre-registration first", "git log", "79d30f5 (16:41:13Z) before the first code commit 3ea7030 (17:32:01Z); debug runs without holdout labels logged", None, True),
        ("G4 frozen code before the recorded runs", "git log", "plan and predict at 3ea7030, open at d58de61 (code unchanged since 3ea7030)", None, True),
        ("G5 candidates and cards", "run_holdout.py plan", "69 cards verified by their family loaders, cutoff 2026-10-17T00:00Z, training rows inside the cutoff", 0, True),
        ("G6 champion before the opening", "evaluation.champion on committed development metric files", "P07_B2 for T1, T1b, T2 (no development skill row)", 0, True),
        ("G7 ledger totals", "evaluation.ledger_totals", "2896 rows, 87 candidates, 31 bake-off, 306 controls, 15 debug runs, N_search 118", 0, True),
        ("G8 predictions before the opening", "run_holdout.py predict (twice)", "12255 rows, 95 decisions, 0 labels read, committed in d58de61 with PREOPEN_MANIFEST.json; twin identical", 0, True),
        ("G9 seal check and pins", "check_seal.py inside run_holdout.py open", "exit 0, problems [], hashes equal DECISIONS and evaluation.SEAL_PINS; bytes hashed on read", 0, True),
        ("G10 opening once, logged", "validation/OPENING_LOG.json", "one FIRST_OPENING entry (2026-10-26T17:33:27Z, head d58de61); later reads are a REPRODUCTION run and an independent label check", 0, True),
        ("G11 holdout set", "evaluation.holdout_rows", "66, 68, 59 scorable; 1 labelled contacted decision excluded per target; 5 censored and 7 T2 pending counted, not scored", 0, True),
        ("G12 primary result", "run_holdout.py open", "; ".join(f"{s} {v['metric']['n_with_number']} events ({v['metric']['positives']} positive) BSS {v['metric']['bss']:.3f} {v['metric']['verdict']}" for s, v in prim.items()), 0, True),
        ("G13 secondary family and selection correction", "HOLDOUT_METRICS.csv", "129 rows with Holm, max-T, full-search Bonferroni; 0 survive all three", 0, True),
        ("G14 negative controls", "PREOPEN_TRAPS.json, HOLDOUT_NEGATIVE_CONTROLS.json", "NC1 20 seeds per target; NC2 1425 of 1425 and 15 of 15 refused; NC3 22 of 22 refused", 0, True),
        ("G15 replay discipline", "REPLAY_AUDIT.json, P13 traps", "0 violations over 380 development OOS rows and 12255 holdout rows; P13 69 of 69 twice; training label after cutoff 69 of 69", 0, True),
        ("G16 sensitivities and dataset shift", "SENSITIVITY.csv, SHIFT_BREAKDOWN.csv", "7 views, 8 breakdowns and prior shift; T2 rows carry the PI-D-045 note", 0, True),
        ("G17 empirical apart from engineering", "FINAL_HOLDOUT_RESULTS.md", "stated separately; nothing promoted; base rate or abstention", None, True),
        ("G18 oracle", "p04_bundle/bin/python -B probes/sklearn_crosscheck_holdout.py validation evidence/sklearn_crosscheck.json", "572 values within 1.1e-16 (scikit-learn 1.9.1)", 0, True),
        ("G19 determinism and isolation", "predict twin; open --reproduction; independent_label_check.py", "7 of 7 and 10 of 10 files byte-equal; 0 label mismatches; 0 network calls; stores and seal unchanged", 0, True),
        ("G20 tests and mutation probe", "pytest tests/test_predictive_evaluation.py tests/test_predictive_phase12_outputs.py; mutation_evaluation.py", "47 passed; 44 of 44 mutations caught at 3ea7030", 0, True),
        ("G21 full experiment ledger", "FULL_EXPERIMENT_LEDGER.csv", "3145 rows (Phase 12: 249)", 0, True),
        ("G22 flag, imports, registry", "tests", "flag OFF; no existing module imports evaluation; fingerprint 4b4aabce and ACCEPTANCE unchanged", 0, True),
    ]
    rep = json.loads(Path(a.repair).read_text()) if a.repair else None
    if rep:
        for c in rep["checks"]:
            checks.append((c["name"], c["command"], c["result"], c["exit_code"], c["pass"]))
    post = json.loads(Path(a.post).read_text()) if a.post else None
    if post:
        for c in post["checks"]:
            checks.append((c["name"], c["command"], c["result"], c["exit_code"], c["pass"]))
    else:
        checks.append(("G23 suite, guard, seal check, release audit after the commit", "see the post-commit records commit", "pending", None, None))
    files = sorted(p for p in PH.rglob("*") if p.is_file() and p.name != "PHASE_12_RESULTS.json")
    files += [REPO / "memelab/predictive/evaluation.py", REPO / "tests/test_predictive_evaluation.py",
              REPO / "tests/test_predictive_phase12_outputs.py"]
    res = {
        "phase": "12", "status": a.status, "head_before": "63076adb7a42ac7f7c2cc271d535d8e7a6947d0e", "head_after": a.head_after,
        "commits": {"pre_registration": "79d30f5", "frozen_code": "3ea7030", "pre_opening_outputs": "d58de61", "opening_outputs": "de7ac77"},
        "holdout_opening": json.loads((PH / "validation/OPENING_LOG.json").read_text())["entries"][0]["time_utc"],
        "result": {s: {"champion": v["champion"], "n": v["metric"]["n_with_number"], "positives": v["metric"]["positives"],
                       "bss": v["metric"]["bss"], "governing_ci": [v["metric"][f"bss_ci_{v['metric']['governing']}_lo"],
                                                                   v["metric"][f"bss_ci_{v['metric']['governing']}_hi"]],
                       "p_holm": v["metric"]["p_holm"], "verdict": v["metric"]["verdict"]} for s, v in prim.items()},
        "checks": [{"name": n, "command": c, "result": r, "exit_code": e, "pass": p} for n, c, r, e, p in checks],
        "artifacts": [{"path": f.relative_to(REPO).as_posix(), "sha256": sha(f)} for f in files],
        "limitations": [
            "The retrospective holdout is opened and spent; any further use is EXPLORATORY (PI-D-065).",
            "7 decision days with one export batch each; the day bootstrap resamples 7 groups.",
            "tech-1 cards have no holdout inputs (NOT_FETCHED_SEALED, no pool) and were not evaluated; no candle was read.",
            "The max-T correction is centred, not studentized (conservative against low-variance candidates).",
            "The secondary verdict column applies Holm only; the claim rule is skill_after_selection_correction (0 everywhere).",
            "CALIBRATION_BINS.csv repeats the champion's bins (primary and secondary rows), identical copies.",
            "Regime and crash-day shift untestable (one regime label QUIET/RISK_OFF, no crash day).",
            "T2: possible partial contact with the holdout (PI-D-045 item 6); T2 is INSUFFICIENT_EVENTS anyway.",
            "Price-path targets only: no fill, depth or proceeds; no trading claim.",
        ],
        "blockers": [],
        "approvals_needed": [],
        "next_eligible_phase": "13, once the orchestrator's independent skeptic and the repair pass give Phase 12 PASS",
    }
    if rep:
        res["commits"].update(rep.get("commits", {}))
        res["limitations"] = rep.get("limitations", []) + res["limitations"]
        res["next_eligible_phase"] = rep.get("next_eligible_phase", res["next_eligible_phase"])
        res["repair_pass_2"] = rep.get("summary")
    (PH / "PHASE_12_RESULTS.json").write_text(json.dumps(res, indent=1, sort_keys=False) + "\n")
    print(json.dumps(res["result"]))


if __name__ == "__main__":
    main()
