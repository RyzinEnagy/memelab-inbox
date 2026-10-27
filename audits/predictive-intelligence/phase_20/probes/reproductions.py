"""Phase 20 (G5): rerun every phase's reproduction entry point in a sandbox clone of the frozen commit and compare its outputs
byte for byte with the committed ones.

    python -B reproductions.py REF OUTJSON [--keep]

The sandbox is `git clone --local` of this checkout at REF under a temporary folder (the exports of origin/main are fetched
into it from this checkout, no network). Runners write only inside the sandbox or into scratch folders. The private research
stores under /home/claude/pi_research/ are read by the runners as they were in their phases (read-only use). Every runner that
can open a socket runs under `unshare -n`. A file that differs is listed with its path; differences limited to recorded wall
times, run logs or latencies are named as such. Exit 0 when every committed output reproduces (apart from those named timing
fields), else 1. The sandbox is deleted unless --keep.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
A = "audits/predictive-intelligence"
EXPORT_REF = "71fc50e1eb86d916034bb0285a466cf2ec1cc4d0"
PUBLISHED = {"documents": "9b839e76", "records": "a8114c19"}      # Phase 18 published replay (Phase 19 rule 3)
TIMING = ("run_log", "LATENCY", "latency", "wall")
# committed outputs whose differences are limited to named fields (checked field by field, everything else must be equal)
NAMED_FIELDS = {"evidence/collector_state.json": {"path"},                 # the checkout path of the (absent) collector database
                "PRIMARY_RESULTS.json": {"ledger_head"},                  # the ledger head grew after the recorded evaluate (drift entries)
                "evidence/asof_real_truncation.json": {"seconds"},       # wall-clock seconds of the check
                # Phase 14 rule documents carry their creation time, so their doc_sha256 changes with every run (Phase 14 rerun_diff.py)
                "behavioral/RULE_SCENARIOS_DEV.jsonl": {"doc_sha256", "created_at_utc"},
                "behavioral/RULE_COUNTS.json": {"created_at_utc", "rule_scenarios_sha256"},
                "behavioral/MOCK_GRID_RUNS.json": {"wall_s", "doc_sha256", "created_at_utc"},
                "behavioral/COST_CAP.json": {"wall_s"},
                "behavioral/SEEDS_DEV_LOG.json": {"start_utc", "end_utc", "head", "wall_s"}}


def strip(o, keys):
    if isinstance(o, dict):
        return {k: strip(v, keys) for k, v in o.items() if k not in keys}
    if isinstance(o, list):
        return [strip(v, keys) for v in o]
    return o


def equal_except(a: Path, b: Path, keys) -> bool:
    try:
        if a.suffix == ".jsonl":
            la, lb = a.read_text().splitlines(), b.read_text().splitlines()
            return len(la) == len(lb) and all(strip(json.loads(x), keys) == strip(json.loads(y), keys) for x, y in zip(la, lb))
        return strip(json.loads(a.read_text()), keys) == strip(json.loads(b.read_text()), keys)
    except ValueError:
        return False


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(argv, cwd, timeout=3600, net=False):
    cmd = (["unshare", "-n"] if not net else []) + argv
    t = time.time()
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return {"argv": " ".join(argv), "exit": p.returncode, "seconds": round(time.time() - t, 1),
            "tail": (p.stdout.strip().splitlines() or [""])[-1][:400], "stderr_tail": p.stderr.strip()[-400:]}


def compare_dir(out: Path, committed: Path, *, skip=()) -> dict:
    same, diff, absent, named = [], [], [], []
    for p in sorted(out.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(out).as_posix()
        if any(s in rel for s in skip):
            continue
        c = committed / rel
        if not c.is_file():
            absent.append(rel)
        elif c.read_bytes() == p.read_bytes():
            same.append(rel)
        elif rel in NAMED_FIELDS and equal_except(p, c, NAMED_FIELDS[rel]):
            named.append(f"{rel} (differs only in {sorted(NAMED_FIELDS[rel])})")
        else:
            diff.append(rel)
    return {"identical": len(same), "identical_except_named_fields": named, "different": diff, "not_committed": absent}


def git_changes(sb: Path) -> list[str]:
    p = subprocess.run(["git", "status", "--porcelain"], cwd=sb, capture_output=True, text=True)
    return [x for x in p.stdout.splitlines() if x.strip()]


def main(ref: str, outjson: Path, keep: bool) -> int:
    t0 = time.time()
    base = Path(tempfile.mkdtemp(prefix="p20_repro_", dir=outjson.parent))
    sb = base / "sandbox"
    subprocess.run(["git", "clone", "-q", "--local", str(REPO), str(sb)], check=True)
    subprocess.run(["git", "checkout", "-q", ref], cwd=sb, check=True)
    subprocess.run(["git", "fetch", "-q", str(REPO), "refs/remotes/origin/main:refs/remotes/origin/main"], cwd=sb, check=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=sb, capture_output=True, text=True).stdout.strip()
    py = sys.executable
    res: dict = {"ref": ref, "sandbox_head": head, "steps": {}}
    S = res["steps"]

    # Phases 07, 12, 13, 16: the committed cross-phase reproduction test, in the sandbox
    S["07_12_13_16_reproductions_test"] = run([py, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_predictive_reproductions.py"], sb)
    # Phase 05: as-of real checks (truncation, recompute, traps, fresh) rewrite their committed evidence files in the sandbox
    for name in ("truncation", "recompute", "traps", "fresh"):
        S[f"05_asof_{name}"] = run([py, "-B", f"{A}/phase_05/probes/asof_real_checks.py", name], sb)
    # Phase 06: the seal and the Phase 05 comparison (no network)
    S["06_check_seal"] = run([py, "-B", f"{A}/phase_06/probes/check_seal.py"], sb)
    S["06_compare05"] = run([py, "-B", f"{A}/phase_06/probes/make_labels.py", "compare05"], sb)
    ch = git_changes(sb)
    named = []
    for line in ch:
        rel = line[3:]
        c = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=sb, capture_output=True, text=True).stdout
        tmp = base / "committed_copy.json"
        tmp.write_text(c)
        key = rel.split("phase_05/")[-1]
        if key in NAMED_FIELDS and equal_except(sb / rel, tmp, NAMED_FIELDS[key]):
            named.append(rel)
    S["05_06_sandbox_tracked_changes"] = {"changed": ch, "differs_only_in_named_fields": named,
                                          "unexplained": [x for x in ch if x[3:] not in named]}
    # Phases 08 to 11: runners into scratch folders, compared with the committed phase folders
    for ph, script in (("08", "run_technical.py"), ("09", "run_onchain.py"), ("10", "run_social.py"), ("11", "run_analog.py")):
        out = base / f"out_{ph}"
        r = run([py, "-B", f"{A}/phase_{ph}/probes/{script}", str(out)], sb)
        r["compare"] = compare_dir(out, sb / A / f"phase_{ph}", skip=TIMING + ("trace/",))
        tr = compare_dir(out, sb / A / f"phase_{ph}")
        r["trace_and_timing_files_differing"] = [x for x in tr["different"] if x not in r["compare"]["different"]]
        S[f"{ph}_{script}"] = r
    # Phase 14: the behavioral runner without MiroFish (the MiroFish run needs its pinned clone and venv)
    out = base / "out_14"
    # its loopback mock services need a loopback interface, which `unshare -n` leaves down here (no `ip` tool): the runner's own
    # audit hook refuses every socket that is not 127.0.0.1 (Phase 14 rule), so it runs in the normal namespace
    S["14_build_seeds"] = run([py, "-B", f"{A}/phase_14/probes/build_seeds.py", str(out)], sb, net=True)
    r = run([py, "-B", f"{A}/phase_14/probes/run_behavioral.py", str(out), "--skip-mirofish"], sb, net=True)
    r["compare"] = compare_dir(out, sb / A / "phase_14", skip=TIMING)
    S["14_run_behavioral_skip_mirofish"] = r
    # Phase 15: scoring
    out = base / "out_15"
    r = run([py, "-B", f"{A}/phase_15/probes/score_scenarios.py", str(out)], sb)
    r["compare"] = compare_dir(out, sb / A / "phase_15", skip=TIMING)
    S["15_score_scenarios"] = r
    # Phase 17: the export replay (research mode), documents and records against the Phase 18 published run
    out = base / "out_17"
    out.mkdir()
    r = run([py, "-B", f"{A}/phase_17/probes/run_integration.py", "replay", str(out), "--ref", EXPORT_REF], sb)
    st = out / "state_replay"
    r["documents_sha256"] = sha(st / "DOCUMENTS.jsonl") if (st / "DOCUMENTS.jsonl").exists() else None
    r["records_sha256"] = sha(st / "RECORDS.jsonl") if (st / "RECORDS.jsonl").exists() else None
    pub = sb / A / "phase_19/monitoring/published"
    r["equal_to_phase19_published_copy"] = {k: (st / f).exists() and (pub / f).exists() and sha(st / f) == sha(pub / f)
                                            for k, f in (("documents", "DOCUMENTS.jsonl"), ("records", "RECORDS.jsonl"))}
    r["published_prefixes"] = {k: (r[f"{k}_sha256"] or "").startswith(v) for k, v in PUBLISHED.items()}
    S["17_export_replay"] = r
    # Phase 18: the golden reports from the fixtures
    out = base / "out_18"
    r = run([py, "-B", f"{A}/phase_18/probes/run_reports.py", "goldens", str(out)], sb)
    r["compare"] = compare_dir(out, sb / "tests/fixtures/predictive/phase18/golden")
    S["18_goldens"] = r
    # Phase 19: offline rebuild of the outcomes and the evaluation from the committed ledger
    r = run([py, "-B", f"{A}/phase_19/probes/rebuild_outcomes.py", str(base / "p19_rebuild.json")], sb)
    r["rebuild"] = json.loads((base / "p19_rebuild.json").read_text()) if (base / "p19_rebuild.json").exists() else None
    S["19_rebuild_outcomes"] = r
    out = base / "out_19"
    r = run([py, "-B", f"{A}/phase_19/probes/run_prospective.py", "evaluate", str(out)], sb)
    r["compare"] = compare_dir(out, sb / A / "phase_19/monitoring", skip=TIMING)
    S["19_evaluate"] = r
    S["19_monitoring_and_outputs_tests"] = run([py, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_predictive_monitoring.py",
                                                "tests/test_predictive_phase19_outputs.py"], sb)
    S["final_sandbox_tracked_changes"] = {"changed": git_changes(sb)}
    S["final_sandbox_tracked_changes"]["unexplained"] = [x for x in S["final_sandbox_tracked_changes"]["changed"]
                                                         if x not in S["05_06_sandbox_tracked_changes"]["changed"]
                                                         or x in S["05_06_sandbox_tracked_changes"]["unexplained"]]
    res["wall_s"] = round(time.time() - t0, 1)
    ok = True
    for k, v in S.items():
        if "exit" in v and v["exit"] != 0:
            ok = False
        if (v.get("compare") or {}).get("different"):
            ok = False
    ok = ok and all(S["17_export_replay"]["equal_to_phase19_published_copy"].values())
    ok = ok and not S["final_sandbox_tracked_changes"]["unexplained"]
    res["all_reproduced"] = ok
    outjson.parent.mkdir(parents=True, exist_ok=True)
    outjson.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"all_reproduced": ok, "wall_s": res["wall_s"],
                      "exits": {k: v.get("exit") for k, v in S.items() if "exit" in v},
                      "differing": {k: (v.get("compare") or {}).get("different") for k, v in S.items() if (v.get("compare") or {}).get("different")}}))
    if not keep:
        shutil.rmtree(base, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    a = sys.argv[1:]
    sys.exit(main(a[0], Path(a[1]), "--keep" in a))
