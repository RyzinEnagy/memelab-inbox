"""Phase 04: collect the bake-off into adoption/BAKEOFF_RESULTS.json.

For every approach and check measured by run_measurements.py it runs the same command once more inside `unshare -n`, keeps
the full output under evidence/outputs/, and requires the sha256 of that output to equal the sha256 recorded by both
measured runs (three identical runs in three fresh processes). It then joins the outputs with the cost numbers.

    python summarize.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AD = HERE.parent
EV = AD / "evidence"
sys.path.insert(0, str(HERE))
import run_measurements as RM  # noqa: E402

ENV = {"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": "0", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}


def rerun(py: str, script: str, args: list[str]) -> bytes:
    p = subprocess.run(["unshare", "-n", py, "-I", "-B", str(HERE / script), *args], capture_output=True, env=ENV, timeout=3600)
    return p.stdout


def cost(m: dict) -> dict:
    return {k: m[k] for k in ("all_exit_0", "wall_median_s", "cpu_median_s", "peak_rss_max_mb", "net_events_total", "deterministic_stdout")}


def main() -> None:
    (EV / "outputs").mkdir(parents=True, exist_ok=True)
    res = {"note": "behaviour, cost and correctness on a small real development sample and a synthetic file; not evidence of "
                   "predictive edge (BAKEOFF.md)", "datasets": {}, "approaches": {}, "checks": {}, "imports": {}}
    res["datasets"]["dev"] = json.loads((AD / "data/dev_sample_summary.json").read_text())
    res["datasets"]["challenge"] = {"file": "phase_03/research/SMOKES/_challenge/challenge.csv",
                                    "sha256": hashlib.sha256((HERE.parents[2] / "phase_03/research/SMOKES/_challenge/challenge.csv").read_bytes()).hexdigest()}
    for f in sorted((EV / "measure").glob("import__*.json")):
        m = json.loads(f.read_text())
        res["imports"][m["label"].removeprefix("import__")] = {**cost(m), "python": m["python"],
                                                                "loaded": m["runs"][0]["stdout_tail"].strip()}
    for f in sorted((EV / "measure").glob("approach__*.json")):
        m = json.loads(f.read_text())
        _, ds, ap, venv = m["label"].split("__")
        out = rerun(m["python"], "bakeoff.py", m["args"])
        (EV / "outputs" / f"{m['label']}.json").write_bytes(out)
        same = hashlib.sha256(out).hexdigest() == m["runs"][0]["stdout_sha256"] and m["deterministic_stdout"]
        try:
            metrics = json.loads(out.decode().strip().splitlines()[-1])
        except (ValueError, IndexError):
            metrics = {"error": m["runs"][0]["stderr_tail"][-300:]}
        res["approaches"].setdefault(ds, {})[f"{ap}__{venv}"] = {**cost(m), "identical_output_three_runs": same, "metrics": metrics}
    for label, py, script, args in RM.CHECKS:
        f = EV / "measure" / f"check__{label}.json"
        if not f.exists():
            continue
        m = json.loads(f.read_text())
        out = rerun(py, script, args)
        (EV / "outputs" / f"check__{label}.json").write_bytes(out)
        same = hashlib.sha256(out).hexdigest() == m["runs"][0]["stdout_sha256"] and m["deterministic_stdout"]
        try:
            body = json.loads(out.decode()) if script != "behavior_check.py" else json.loads(out.decode().strip().splitlines()[-1])
        except (ValueError, IndexError):
            body = {"error": m["runs"][0]["stderr_tail"][-300:]}
        res["checks"][label] = {**cost(m), "identical_output_three_runs": same, "output": body}
    for extra in ("error_semantics.json", "mirofish_adapter_runs.json", "hostile_setup_demo.json", "rollback_demo.json",
                  "mutation_runtime.json", "holdout_candle_check.json", "wheel_licenses.json"):
        p = EV / extra
        if p.exists():
            d = json.loads(p.read_text())
            res.setdefault("other_evidence", {})[extra] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                                                           "summary": {k: d[k] for k in list(d)[:12] if not isinstance(d[k], (list,)) or len(d[k]) < 8}}
    (AD / "BAKEOFF_RESULTS.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    bad = [f"{ds}/{k}" for ds, v in res["approaches"].items() for k, x in v.items() if not x["identical_output_three_runs"] or not x["all_exit_0"]]
    bad += [f"check/{k}" for k, x in res["checks"].items() if not x["identical_output_three_runs"]]
    print(json.dumps({"approach_runs": sum(len(v) for v in res["approaches"].values()), "checks": len(res["checks"]),
                      "not_identical_or_failed": bad}))


if __name__ == "__main__":
    main()
