"""Cross-phase reproduction check (PI-D-090, Phase 16 repair pass 2, skeptic m9): the recorded reproduction entry points of
Phases 07, 12, 13 and 16 still run as committed and give their committed outputs, so a later phase that breaks one (as the
Phase 13 calibration cards broke the Phase 12 card glob) fails the suite. The Phase 12 plan step reads committed files only
and always runs; the steps that need the private research stores (rebuild recipes in the Phase 05 and 06 records) are skipped
with that reason when the stores are absent. Every runner refuses network calls and leaves the stores unchanged."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / "audits/predictive-intelligence"
DEV = Path("/home/claude/pi_research/p06/dev_store.sqlite")
FS = Path("/home/claude/pi_research/p05/predictive_store.sqlite")
STORES = DEV.is_file() and FS.is_file()
needs_stores = pytest.mark.skipif(not STORES, reason="private research stores absent (rebuild: phase_05 and phase_06 records)")


def run(args, timeout=900):
    r = subprocess.run([sys.executable, "-B", *args], cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    assert r.returncode == 0, (args[0], r.stdout[-1500:], r.stderr[-1500:])
    return r


def differing(out: Path, committed: Path, skip: set[str]) -> list[str]:
    bad = []
    for p in sorted(out.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(out).as_posix()
        if rel in skip or rel.startswith("run_log") or rel.endswith("/run_log.json"):
            continue
        c = committed / rel
        if not c.is_file() or c.read_bytes() != p.read_bytes():
            bad.append(rel)
    return bad


def test_phase_12_plan_reproduces_its_committed_files(tmp_path):
    run(["audits/predictive-intelligence/phase_12/probes/run_holdout.py", "plan", str(tmp_path)])
    for f in ("CANDIDATES.json", "LEDGER_TOTALS.json"):
        assert (tmp_path / f).read_bytes() == (AUD / "phase_12/validation" / f).read_bytes(), f


@needs_stores
def test_phase_12_plan_and_predict_reproduce_seven_of_seven(tmp_path):
    run(["audits/predictive-intelligence/phase_12/probes/run_holdout.py", "plan", str(tmp_path)])
    run(["audits/predictive-intelligence/phase_12/probes/run_holdout.py", "predict", str(tmp_path)])
    files = ("CANDIDATES.json", "LEDGER_TOTALS.json", "HOLDOUT_PREDICTIONS.csv", "HOLDOUT_DECISIONS.csv", "PREOPEN_TRAPS.json",
             "REPLAY_AUDIT.json", "PREOPEN_MANIFEST.json")
    assert [f for f in files if (tmp_path / f).read_bytes() != (AUD / "phase_12/validation" / f).read_bytes()] == []


@needs_stores
def test_phase_07_baselines_reproduce_their_33_recorded_files(tmp_path):
    run(["audits/predictive-intelligence/phase_07/probes/run_baselines.py", str(tmp_path)])
    det = json.loads((AUD / "phase_07/evidence/determinism.json").read_text())["sha256"]
    assert len(det) == 33
    assert [k for k in det if (tmp_path / k).read_bytes() != (AUD / "phase_07" / k).read_bytes()] == []


@needs_stores
def test_phase_13_calibration_reproduces_its_committed_files(tmp_path):
    run(["audits/predictive-intelligence/phase_13/probes/run_calibration.py", str(tmp_path)])
    # POST_OPENING_LOG.json carries the head commit of the run
    assert differing(tmp_path, AUD / "phase_13", {"calibration/POST_OPENING_LOG.json"}) == []
    a = json.loads((tmp_path / "calibration/POST_OPENING_LOG.json").read_text())
    b = json.loads((AUD / "phase_13/calibration/POST_OPENING_LOG.json").read_text())
    assert {k: v for k, v in a.items() if k != "head_code"} == {k: v for k, v in b.items() if k != "head_code"}


@needs_stores
def test_phase_16_registry_reproduces_its_committed_files(tmp_path):
    run(["audits/predictive-intelligence/phase_16/probes/build_registry.py", str(tmp_path)])
    assert differing(tmp_path, AUD / "phase_16", {"ensemble/LATENCY.json"}) == []
