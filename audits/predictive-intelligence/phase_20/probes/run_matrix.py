"""Phase 20: run the 48 scenario checks and the existing tests mapped to them; write the scenario matrix.

    python -B run_matrix.py OUTDIR      writes OUTDIR/SCENARIO_MATRIX.csv, OUTDIR/raw/Pxx.json, OUTDIR/mapped_tests.xml,
                                        OUTDIR/matrix_run.json

Each scenario runs as its own command (`python -B probes/scenarios.py Pxx`, sockets refused inside); its exit code and raw
output are kept. The mapped existing tests run once in one pytest call (junit file). Results per ../ACCEPTANCE_CHECKLIST.md:
PASS, PASS_EXPECTED_ERROR, TEST_ONLY, N_A or FAIL; a scenario whose required behaviour holds but whose defense-in-depth probe
failed is PASS_WITH_PROBE_FINDING and the finding goes to the findings file.
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PKG = Path("/mnt/user-data/uploads/Memecoin_Predictive_Intelligence_Engine_Prompt_Package/references/ADVERSARIAL_SCENARIOS.md")

# component under test and the result class when the required behaviour holds (fixed with the checks, before the recorded run)
COMPONENT = {
    "P01": ("integration, baselines, contract, labels", "PASS"), "P02": ("integration, labels, onchain", "PASS"),
    "P03": ("socialcat (social adapter)", "TEST_ONLY"), "P04": ("socialcat (catalyst classifier)", "TEST_ONLY"),
    "P05": ("contract, baselines, evaluation, monitoring ledger", "PASS_EXPECTED_ERROR"), "P06": ("contract (reference price, path)", "PASS"),
    "P07": ("labels (revision check, revise)", "PASS"), "P08": ("contract, onchain size cap", "PASS_EXPECTED_ERROR"),
    "P09": ("labels (eligibility, censoring)", "PASS"), "P10": ("monitoring, calibration scores", "PASS"),
    "P11": ("calibration, monitoring, abstention", "PASS"), "P12": ("integration, abstention", "PASS"),
    "P13": ("integration, evaluation, abstention, contract", "PASS_EXPECTED_ERROR"), "P14": ("analog, labels groups", "PASS"),
    "P15": ("socialcat", "TEST_ONLY"), "P16": ("socialcat", "TEST_ONLY"), "P17": ("socialcat (catalyst classifier)", "TEST_ONLY"),
    "P18": ("onchain wallet movements", "TEST_ONLY"), "P19": ("onchain wallet roles", "TEST_ONLY"),
    "P20": ("labels split, baselines fold audit, decisions thinning", "PASS_EXPECTED_ERROR"),
    "P21": ("baselines evaluation gate, monitoring D7, Phase 12 record", "PASS"), "P22": ("evaluation, registry, search ledger", "PASS"),
    "P23": ("calibration score report", "PASS"), "P24": ("calibration gate, abstention, Phase 13 cards", "PASS"),
    "P25": ("reports (risk override), onchain decision support, labels wick flag", "TEST_ONLY"),
    "P26": ("behavioral contamination, socialcat, features", "PASS"), "P27": ("abstention, contract, behavioral, registry", "PASS_EXPECTED_ERROR"),
    "P28": ("behavioral seed check", "TEST_ONLY"), "P29": ("behavioral stability", "TEST_ONLY"),
    "P30": ("runtime simulation state, integration", "PASS"), "P31": ("runtime copyleft gate (whole repository)", "PASS"),
    "P32": ("runtime lock guard and install route", "PASS_EXPECTED_ERROR"), "P33": ("store and label migrations on a lab copy", "PASS"),
    "P34": ("contract backtest status, integration", "PASS"), "P35": ("integration (idempotency, storms, queue cap)", "PASS"),
    "P36": ("features, abstention, baselines", "PASS_EXPECTED_ERROR"), "P37": ("labels, monitoring ledger", "PASS"),
    "P38": ("contract, abstention, baselines serialisation, calibration", "PASS_EXPECTED_ERROR"),
    "P39": ("monitoring response, abstention, integration", "TEST_ONLY"), "P40": ("integration flag, cli hook", "PASS"),
    "P41": ("socialcat, behavioral, reports, integration", "PASS"), "P42": ("Phase 03 scorecard checker", "PASS_EXPECTED_ERROR"),
    "P43": ("analog pool check, baselines fit, monitoring", "PASS_EXPECTED_ERROR"), "P44": ("abstention, analog, reports, integration", "PASS"),
    "P45": ("socialcat classifier, behavioral grounding", "TEST_ONLY"), "P46": ("integration, registry compatibility", "TEST_ONLY"),
    "P47": ("integration, monitoring sources", "PASS"), "P48": ("runtime CallGuard, integration", "PASS"),
}
# existing tests mapped by hand where the test names carry no scenario id (found by reading the tests)
EXTRA = {
    "P28": ["tests/test_predictive_behavioral.py::test_check_seed_refuses"],
    "P29": ["tests/test_predictive_behavioral.py::test_stability_rules_directly"],
    "P33": ["tests/test_predictive_asof_store.py::test_migrate_then_rollback_leaves_a_full_lab_database_identical",
            "tests/test_predictive_labels.py::test_label_migration_is_additive_append_only_and_reversible"],
    "P35": ["tests/test_predictive_integration.py::test_g6_the_same_snapshot_again_is_a_duplicate_with_no_new_document",
            "tests/test_predictive_integration.py::test_g8_a_storm_of_updates_gives_one_attempt_per_mint_and_linear_work"],
    "P42": [],
    "P48": ["tests/test_predictive_runtime.py::test_call_guard_opens_after_five_failures_and_never_calls_again",
            "tests/test_predictive_runtime.py::test_call_and_cost_caps_stop_before_the_call",
            "tests/test_predictive_runtime.py::test_a_non_finite_or_negative_cost_setting_fails_closed"],
}


def scenario_table() -> dict[str, dict]:
    out = {}
    for line in PKG.read_text().splitlines():
        m = re.match(r"\|\s*(P\d\d)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|$", line)
        if m:
            out[m.group(1)] = {"trap": m.group(2), "required": m.group(3)}
    return out


def mapped_tests() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {f"P{i:02d}": [] for i in range(1, 49)}
    for f in sorted((REPO / "tests").glob("test_predictive_*.py")):
        if f.name == "test_predictive_phase20_cross.py":
            continue
        for m in re.finditer(r"^def (test_[a-z0-9_]+)\(", f.read_text(), re.M):
            name = m.group(1)
            for pid in re.findall(r"(?:^|_)p(\d\d)(?=_|$)", name):
                k = f"P{pid}"
                if k in out:
                    out[k].append(f"tests/{f.name}::{name}")
    for k, v in EXTRA.items():
        out[k] = sorted(set(out[k]) | set(v))
    return out


def main(outdir: Path) -> int:
    outdir.mkdir(parents=True, exist_ok=True)
    raw = outdir / "raw"
    raw.mkdir(exist_ok=True)
    table = scenario_table()
    assert sorted(table) == [f"P{i:02d}" for i in range(1, 49)], "the package table must list P01 to P48"
    mt = mapped_tests()
    t0 = time.time()
    rows, runs = [], {}
    for sid in sorted(table):
        cmd = [sys.executable, "-B", str(HERE / "scenarios.py"), sid]
        a = time.time()
        p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=900)
        (raw / f"{sid}.json").write_text(p.stdout + (("\n--- stderr ---\n" + p.stderr) if p.stderr.strip() else ""))
        try:
            res = json.loads(p.stdout)
        except ValueError:
            res = {"result": "CHECK_ERROR", "assertions": [], "passed": 0, "total": 0, "probes_failed": []}
        runs[sid] = {"exit": p.returncode, "seconds": round(time.time() - a, 2), "result": res.get("result")}
        rows.append((sid, p.returncode, res))
    node_ids = sorted({n for v in mt.values() for n in v})
    junit = outdir / "mapped_tests.xml"
    pt = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={junit}", *node_ids],
                        cwd=REPO, capture_output=True, text=True, timeout=3600)
    (outdir / "mapped_tests.txt").write_text(pt.stdout[-20000:] + pt.stderr[-5000:])
    outcome: dict[str, str] = {}
    for tc in ET.parse(junit).getroot().iter("testcase"):
        cls, name = tc.get("classname", ""), tc.get("name", "")
        base = name.split("[")[0]
        key = f"tests/{cls.split('.')[-1]}.py::{base}"
        st = "passed"
        for child in tc:
            if child.tag in ("failure", "error"):
                st = "failed"
            elif child.tag == "skipped":
                st = "skipped"
        prev = outcome.get(key)
        outcome[key] = "failed" if "failed" in (prev, st) else (st if prev in (None, st) else "mixed")
    with open(outdir / "SCENARIO_MATRIX.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "trap", "required_behaviour", "component", "check_command", "exit_code", "assertions_passed", "assertions_total",
                    "probe_findings", "result", "mapped_tests", "mapped_tests_outcome", "unpatched_severity", "raw_output"])
        for sid, code, res in rows:
            comp, cls = COMPONENT[sid]
            tests = mt[sid]
            outs = [outcome.get(t, "not_collected") for t in tests]
            ok_tests = all(o in ("passed", "skipped") for o in outs)
            if code == 0 and ok_tests:
                result = cls if not res.get("probes_failed") else "PASS_WITH_PROBE_FINDING"
            else:
                result = "FAIL"
            w.writerow([sid, table[sid]["trap"], table[sid]["required"], comp, f"python -B audits/predictive-intelligence/phase_20/probes/scenarios.py {sid}",
                        code, res.get("passed"), res.get("total"), "; ".join(res.get("probes_failed") or []), result, " ".join(tests),
                        " ".join(f"{o}" for o in outs) if tests else "none mapped (own check only)",
                        "" if result != "FAIL" else "SEE_FINDINGS", f"qa/raw/{sid}.json"])
    summary = {"scenarios": len(rows), "exit_codes": {k: v["exit"] for k, v in runs.items()},
               "results": {sid: r["result"] for sid, r in runs.items()}, "mapped_tests": len(node_ids),
               "mapped_tests_exit": pt.returncode, "mapped_tests_tail": pt.stdout.strip().splitlines()[-1] if pt.stdout.strip() else "",
               "mapped_outcomes": {k: sum(1 for v in outcome.values() if v == k) for k in ("passed", "failed", "skipped", "mixed")},
               "wall_s": round(time.time() - t0, 1), "seconds": {k: v["seconds"] for k, v in runs.items()}}
    (outdir / "matrix_run.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: summary[k] for k in ("scenarios", "mapped_tests", "mapped_tests_exit", "mapped_tests_tail", "wall_s")}))
    bad = [sid for sid, code, _ in rows if code != 0]
    return 0 if not bad and pt.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
