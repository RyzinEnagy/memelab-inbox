"""Cross-phase reproduction check (PI-D-090, Phase 16 repair pass 2, skeptic m9): the recorded reproduction entry points of
Phases 07, 12, 13 and 16 still run as committed and give their committed outputs, so a later phase that breaks one (as the
Phase 13 calibration cards broke the Phase 12 card glob) fails the suite. The Phase 12 plan step reads committed files only
and always runs; the steps that need the private research stores (rebuild recipes in the Phase 05 and 06 records) are skipped
with that reason when the stores are absent. Every runner refuses network calls and leaves the stores unchanged."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / "audits/predictive-intelligence"
RESEARCH = Path(os.environ.get("PI_RESEARCH_DIR") or "/home/claude/pi_research")   # CP21-1 (PI-D-118, F6)
DEV = RESEARCH / "p06/dev_store.sqlite"
FS = RESEARCH / "p05/predictive_store.sqlite"
STORES = DEV.is_file() and FS.is_file()
needs_stores = pytest.mark.skipif(not STORES, reason="private research stores absent (rebuild: phase_05 and phase_06 records)")


# PI-D-120: the backtesting package was merged into this line after Phases 07 to 16 committed their outputs, and documents carry the
# installed backtest state (UNVERIFIED now, BACKTEST_NOT_AVAILABLE then). A reproduction reruns a committed entry point in the state
# of its own commit, so the runners see the package hidden (an import of memelab.backtest fails as it did then); nothing else changes.
HIDE_BACKTEST = """import os, runpy, sys, importlib.abc
class _HideBacktest(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name == "memelab.backtest" or name.startswith("memelab.backtest."):
            raise ModuleNotFoundError(name)
        return None
sys.meta_path.insert(0, _HideBacktest())
script = sys.argv[1]
sys.argv = sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
runpy.run_path(script, run_name="__main__")
"""


def run(args, timeout=900):
    r = subprocess.run([sys.executable, "-B", "-c", HIDE_BACKTEST, *args], cwd=ROOT, capture_output=True, text=True, timeout=timeout)
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


def test_the_reproduction_runner_hides_the_backtesting_package_and_only_that(tmp_path):
    probe = tmp_path / "probe.py"
    probe.write_text("import sys\nfrom memelab.predictive import contract as C\nimport memelab.social\nprint(C.backtest_status(), sys.argv[1:])\n")
    out = run([str(probe), "x"]).stdout.split()
    assert out[0] == "BACKTEST_NOT_AVAILABLE" and out[1:] == ["['x']"]
    from memelab.predictive import contract as C
    assert C.backtest_status() == "UNVERIFIED"                                   # the suite itself sees the installed package


@needs_stores
def test_phase_16_registry_reproduces_its_committed_files(tmp_path):
    # PI-D-129 (CM-2): the Phase 16 entries record the sha256 of their code files, and CM-2 changed contract.py and labels.py
    # (PI-D-122, re-pinned by PI-D-123). As with the backtesting package (PI-D-120), the builder reruns in the state of its own
    # commit for those two files only: a scratch clone of HEAD with each of them restored to the bytes of its PI-D-123 "was" pin.
    pin = json.loads((ROOT / "tests/fixtures/predictive/phase18/PINNED_SHA256_PI-D-123.json").read_text())["files"]
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    tree = tmp_path / "tree"
    subprocess.run(["git", "clone", "-q", "--no-local", "--no-checkout", str(ROOT), str(tree)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tree), "checkout", "-q", head], check=True, capture_output=True)
    for f, v in pin.items():
        old = subprocess.run(["git", "-C", str(ROOT), "show", f"ed85b2c:{f}"], capture_output=True, check=True).stdout
        assert hashlib.sha256(old).hexdigest() == v["was"], f
        (tree / f).write_bytes(old)
    if (ROOT / "data/memelab.sqlite").is_file():                     # git-ignored; the builder checks it is left unchanged
        (tree / "data/memelab.sqlite").write_bytes((ROOT / "data/memelab.sqlite").read_bytes())
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, "-B", "-c", HIDE_BACKTEST, str(tree / "audits/predictive-intelligence/phase_16/probes/build_registry.py"),
                        str(out)], cwd=tree, capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, (r.stdout[-1500:], r.stderr[-1500:])
    assert differing(out, AUD / "phase_16", {"ensemble/LATENCY.json"}) == []
