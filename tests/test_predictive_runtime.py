"""Predictive intelligence Phase 04: runtime error states, circuit breakers, install guard and copyleft gate
(memelab/predictive/runtime.py). Scenarios P30 (missing Zep or LLM), P31 (copied AGPL code), P32 (hostile setup), P34 (absent
backtest), plus absent crawler, GPU, weights, network and optional libraries. Standard library and pytest only: no third-party
package, no network, no clock, no writes outside tmp_path, no key read (the environment is replaced by a guard that raises).
"""
import ast
import collections.abc
import copy
import hashlib
import json
import os
import socket
import urllib.error
from pathlib import Path

import pytest

from memelab.predictive import contract as C
from memelab.predictive import runtime as R

ROOT = Path(__file__).resolve().parent.parent
FIX = json.loads((ROOT / "tests/fixtures/predictive/forecast_examples_format_only.json").read_text())
FINGERPRINTS = ROOT / "tests/fixtures/predictive/copyleft_fingerprints.json"
LOCK = ROOT / "docs/predictive-intelligence/locks/research-py313.txt"
LAB_CODE_ROOTS = ("memelab", "tests", "tools", "bridge", "skills")


class KeyGuardEnviron(collections.abc.MutableMapping):
    """Stands in for os.environ: reading any key-like name raises, so a test fails if runtime code looks for a credential."""
    BAD = ("KEY", "TOKEN", "SECRET", "PASSWORD", "ZEP", "OPENAI", "LLM", "ANTHROPIC", "API")

    def __init__(self, base):
        self._d = dict(base)
        self.reads = []

    def _check(self, k):
        self.reads.append(k)
        if any(b in str(k).upper() for b in self.BAD):
            raise AssertionError(f"runtime read a key-like environment variable: {k}")

    def __getitem__(self, k):
        self._check(k)
        return self._d[k]

    def __contains__(self, k):
        self._check(k)
        return k in self._d

    def get(self, k, default=None):
        self._check(k)
        return self._d.get(k, default)

    def __setitem__(self, k, v):
        self._d[k] = v

    def __delitem__(self, k):
        del self._d[k]

    def __iter__(self):
        raise AssertionError("runtime enumerated the environment")

    def __len__(self):
        return len(self._d)


@pytest.fixture
def no_keys(monkeypatch):
    g = KeyGuardEnviron({"ZEP_API_KEY": "must-never-be-read", "LLM_API_KEY": "must-never-be-read", "PATH": os.environ.get("PATH", "")})
    monkeypatch.setattr(os, "environ", g)
    return g


def abstain_doc(reasons):
    d = copy.deepcopy(FIX["abstain_example"])
    d["abstain_reasons"] = reasons
    return d


class Adapter:
    def __init__(self, result=None, exc=None):
        self.result, self.exc, self.calls = result, exc, 0

    def run(self):
        self.calls += 1
        if self.exc is not None:
            raise self.exc
        return self.result


APPROVED = {"predictive": {"behavioral": {"approved": True}}}


# ---------- P30: missing Zep, LLM or quota ----------

@pytest.mark.parametrize("config, adapter, detail", [
    (None, None, "NOT_APPROVED"),
    ({"predictive": {"behavioral": {"approved": "true"}}}, Adapter({"llm_actions": 5}), "NOT_APPROVED"),   # only JSON true approves
    (APPROVED, None, "ADAPTER_ABSENT"),
    (APPROVED, Adapter(exc=PermissionError("ZEP_API_KEY missing")), "ADAPTER_COMPONENT_ERROR"),
    (APPROVED, Adapter(exc=RuntimeError("insufficient_quota")), "ADAPTER_COMPONENT_ERROR"),
    (APPROVED, Adapter(exc=ConnectionError("llm endpoint down")), "ADAPTER_NETWORK_UNAVAILABLE"),
    (APPROVED, Adapter(exc=ImportError("no module named zep_cloud")), "ADAPTER_DEPENDENCY_MISSING"),
    (APPROVED, Adapter({"exit_code": 0, "llm_actions": 0}), "NO_LLM_ACTIONS"),        # MiroFish exits 0 with its LLM down
    (APPROVED, Adapter({"exit_code": 0}), "NO_LLM_ACTIONS"),
    (APPROVED, Adapter("simulation loop complete"), "NO_LLM_ACTIONS"),
])
def test_p30_simulation_not_available_and_the_core_is_unaffected(no_keys, config, adapter, detail):
    st = R.simulation_state(config, adapter)
    assert st["state"] == R.SIMULATION_NOT_AVAILABLE
    assert st["detail"].startswith(detail)
    assert st["abstain_reason"] is None                       # the statistical forecast is unaffected
    rep = R.capability_report(config, adapter=adapter)
    doc = abstain_doc(R.abstain_reasons(rep) + ["MODEL_NOT_SELECTED"])
    assert doc["behavioral_scenarios"] == []
    assert C.validate(doc, backtest=C.BACKTEST_NOT_AVAILABLE) == []
    assert not any(any(b in str(k).upper() for b in KeyGuardEnviron.BAD) for k in no_keys.reads)


def test_p30_an_approved_run_with_llm_actions_is_the_only_available_case(no_keys):
    a = Adapter({"exit_code": 0, "llm_actions": 7})
    assert R.simulation_state(APPROVED, a)["state"] == R.AVAILABLE
    assert a.calls == 1
    assert R.simulation_state(None, a)["state"] == R.SIMULATION_NOT_AVAILABLE and a.calls == 1   # not approved: never called


# ---------- absent crawler, GPU, weights, network, optional library: states, never crashes ----------

@pytest.mark.parametrize("exc, state, reason", [
    (ImportError("No module named 'lightgbm'"), R.DEPENDENCY_MISSING, "MODEL_NOT_SELECTED"),
    (ModuleNotFoundError("No module named 'networkx'"), R.DEPENDENCY_MISSING, "MODEL_NOT_SELECTED"),
    (FileNotFoundError("model.json"), R.MODEL_WEIGHTS_MISSING, "MODEL_NOT_SELECTED"),
    (ConnectionError("reset"), R.NETWORK_UNAVAILABLE, "SOURCE_STALE"),
    (TimeoutError("read timed out"), R.NETWORK_UNAVAILABLE, "SOURCE_STALE"),
    (socket.gaierror(-3, "Temporary failure in name resolution"), R.NETWORK_UNAVAILABLE, "SOURCE_STALE"),
    (urllib.error.URLError("unreachable"), R.NETWORK_UNAVAILABLE, "SOURCE_STALE"),
    (RuntimeError("CUDA driver not found"), R.COMPONENT_ERROR, "MODEL_NOT_SELECTED"),
    (MemoryError(), R.COMPONENT_ERROR, "MODEL_NOT_SELECTED"),
    (ValueError("Input contains NaN"), R.COMPONENT_ERROR, "MODEL_NOT_SELECTED"),
])
def test_absent_components_become_states_and_a_valid_abstention(no_keys, exc, state, reason):
    def boom():
        raise exc
    st, val = R.guarded("component", boom)
    assert (st["state"], st["abstain_reason"], val) == (state, reason, None)
    assert reason in C.ABSTAIN_REASONS
    assert C.validate(abstain_doc(R.abstain_reasons([st])), backtest=C.BACKTEST_NOT_AVAILABLE) == []


def test_gpu_and_crawler_are_not_required_and_every_state_maps_to_a_contract_reason(no_keys):
    assert R.gpu_state()["state"] == R.NOT_REQUIRED and R.gpu_state()["abstain_reason"] is None
    assert R.crawler_state()["state"] == R.NOT_REQUIRED
    for s, r in R.ABSTAIN_FOR.items():
        assert r is None or r in C.ABSTAIN_REASONS, s
    assert R.guarded("ok", lambda: 41 + 1) == (R._state("ok", R.AVAILABLE), 42)


def test_weights_need_the_registered_sha256(tmp_path, no_keys):
    p = tmp_path / "model.json"
    assert R.weights_state(p, "0" * 64)["state"] == R.MODEL_WEIGHTS_MISSING
    p.write_text('{"coef": [0.1]}')
    good = hashlib.sha256(p.read_bytes()).hexdigest()
    assert R.weights_state(p, good)["state"] == R.AVAILABLE
    p.write_text('{"coef": [0.2]}')
    st = R.weights_state(p, good)
    assert st["state"] == R.MODEL_HASH_MISMATCH and st["abstain_reason"] == "MODEL_NOT_SELECTED"


def test_dependency_state_never_imports_the_module(tmp_path, monkeypatch, no_keys):
    (tmp_path / "p04_hostile_mod.py").write_text("raise SystemExit('imported: side effects ran')\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    assert R.dependency_state("p04_hostile_mod")["state"] == R.AVAILABLE      # found, not executed
    assert R.dependency_state("p04_module_that_does_not_exist")["state"] == R.DEPENDENCY_MISSING
    assert R.dependency_state("")["state"] == R.DEPENDENCY_MISSING


# ---------- breaker, caps and pace (P47, P48) ----------

class FakeClock:
    def __init__(self):
        self.t, self.slept = 1000.0, []

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


def test_call_guard_opens_after_five_failures_and_never_calls_again(no_keys):
    clk = FakeClock()
    g = R.CallGuard(clock=clk, sleep=clk.sleep)
    calls = []

    def down():
        calls.append(1)
        raise ConnectionError("down")
    states = [g.call("gt", down)[0]["state"] for _ in range(8)]
    assert states[:5] == [R.NETWORK_UNAVAILABLE] * 5 and states[5:] == [R.CIRCUIT_OPEN] * 3
    assert len(calls) == 5
    assert g.call("gt", lambda: 1)[0]["abstain_reason"] == "SOURCE_STALE"


def test_call_guard_paces_at_the_frozen_rate_and_resets_on_success(no_keys):
    clk = FakeClock()
    g = R.CallGuard(clock=clk, sleep=clk.sleep)
    assert g.interval == pytest.approx(10.0)                    # 6 calls a minute (ACCEPTANCE api_limits)
    for _ in range(4):
        assert g.call("gt", lambda: "ok")[1] == "ok"
    assert clk.slept == [pytest.approx(10.0)] * 3
    for _ in range(4):
        g.call("gt", lambda: (_ for _ in ()).throw(TimeoutError()))
    assert g.call("gt", lambda: "ok")[1] == "ok" and g.failures == 0


def test_call_and_cost_caps_stop_before_the_call(no_keys):
    clk = FakeClock()
    g = R.CallGuard(max_calls=2, clock=clk, sleep=clk.sleep)
    assert [g.call("x", lambda: 1)[0]["state"] for _ in range(3)] == [R.AVAILABLE, R.AVAILABLE, R.CALL_CAP_REACHED]
    spent = []
    g = R.CallGuard(max_cost=2.0, cost_per_call=1.0, clock=clk, sleep=clk.sleep)
    out = [g.call("paid", lambda: spent.append(1))[0]["state"] for _ in range(4)]
    assert out == [R.AVAILABLE, R.AVAILABLE, R.COST_CAP_REACHED, R.COST_CAP_REACHED] and len(spent) == 2
    assert R.CallGuard().max_calls == C.ACCEPTANCE["api_limits"]["calls_per_run"]
    assert R.CallGuard().breaker == C.ACCEPTANCE["api_limits"]["breaker_consecutive_failures"]


# ---------- P34: backtest absent ----------

def test_p34_absent_backtest_is_reported_never_claimed(no_keys):
    rep = R.capability_report(None, installed_backtest={m: False for m in C.BACKTEST_MODULES})
    bt = next(s for s in rep if s["component"] == "backtest")
    assert bt["state"] == C.BACKTEST_NOT_AVAILABLE and bt["abstain_reason"] is None
    assert R.backtest_state({"memelab.backtest": True})["state"] == "UNVERIFIED"       # importable is not verified
    assert R.backtest_state()["state"] == C.BACKTEST_NOT_AVAILABLE                       # nothing installed in this repository


# ---------- P32: hostile setup ----------

GOOD = "numpy==2.5.3 \\\n    --hash=sha256:" + "a" * 64 + "\ncolorama==0.4.6 ; sys_platform == 'win32' \\\n    --hash=sha256:" + "b" * 64 + "\n"


@pytest.mark.parametrize("bad, why", [
    ("numpy>=2.0 --hash=sha256:" + "a" * 64, "not an exact pin"),
    ("numpy==2.5.3", "no sha256 hash"),
    ("numpy==2.5.3 --hash=sha256:" + "a" * 63, "no sha256 hash"),
    ("numpy==2.5.3 --hash=md5:" + "a" * 32, "no sha256 hash"),
    ("git+https://example.org/evil.git#egg=evil", "URL, VCS or path"),
    ("evil @ https://example.org/evil-1.0.tar.gz", "URL, VCS or path"),
    ("./local_pkg", "URL, VCS or path"),
    ("-e .", "option not allowed"),
    ("--index-url https://mirror.example.org/simple", "option not allowed"),
    ("--extra-index-url https://mirror.example.org/simple", "option not allowed"),
    ("--find-links /tmp/wheels", "option not allowed"),
    ("-r other.txt", "option not allowed"),
    ("--no-binary :all:", "option not allowed"),
])
def test_p32_lock_guard_refuses_anything_but_hashed_exact_pins(bad, why):
    assert R.check_lock(GOOD) == []
    probs = R.check_lock(GOOD + bad + "\n")
    assert probs and why in " | ".join(probs)


def test_p32_the_research_lock_passes_the_guard_and_install_flags_forbid_builds():
    assert LOCK.is_file()
    assert R.check_lock(LOCK.read_text()) == []
    assert set(R.INSTALL_FLAGS) == {"--require-hashes", "--only-binary=:all:", "--no-deps"}
    assert R.check_lock("") == ["empty lock"]


def test_p32_sdists_and_wrong_hashes_are_refused_before_install(tmp_path):
    whl = tmp_path / "pkg-1.0-py3-none-any.whl"
    whl.write_bytes(b"PK\x03\x04 wheel bytes")
    sd = tmp_path / "pkg-1.0.tar.gz"
    sd.write_bytes(b"setup.py would run here")
    h_whl, h_sd = (hashlib.sha256(p.read_bytes()).hexdigest() for p in (whl, sd))
    assert R.verify_artifact(whl, [h_whl]) == R.AVAILABLE
    assert R.verify_artifact(whl, ["0" * 64]) == "REFUSED_HASH_MISMATCH"
    assert R.verify_artifact(sd, [h_sd]) == "REFUSED_NOT_A_WHEEL"        # even with a matching hash


# ---------- P31: copied AGPL code ----------

def _lab_code_files():
    return [p for r in LAB_CODE_ROOTS for p in (ROOT / r).rglob("*") if p.is_file() and p.suffix in R.CODE_SUFFIXES]


def test_p31_lab_code_has_no_copyleft_marker_or_fingerprint():
    fp = R.load_fingerprints(FINGERPRINTS)
    doc = json.loads(FINGERPRINTS.read_text())
    assert {s["repo"] for s in doc["sources"]} == {"666ghj/MiroFish", "bancaditalia/black-it"}
    assert len(fp) > 1000 and all(len(h) == R.HASH_HEX for h in fp)
    files = _lab_code_files()
    assert len(files) > 100
    assert R.copyleft_findings(files, fp) == []


def test_p31_gate_catches_a_license_header_and_a_copied_block(tmp_path):
    marker = "# This program is free software: you can redistribute it under the GNU Affero " + "General Public License"
    f = tmp_path / "copied_header.py"
    f.write_text(marker + "\nx = 1\n")
    assert {x["kind"] for x in R.copyleft_findings([f])} == {"license_marker"}
    spdx = tmp_path / "spdx.js"
    spdx.write_text("// SPDX-License-Identifier: " + "AGPL-3.0-only\n")
    assert R.copyleft_findings([spdx])
    # a synthetic stand-in for a protected source: its winnowed fingerprints catch a copied run of 15 lines, not 3
    src = "\n".join(f"value_{i:03d} = compute_something(alpha={i}, beta={i * 7 % 13})" for i in range(200))
    fps = R.winnow(R.shingle_hashes(src))
    lines = src.splitlines()
    for start in (0, 37, 120, 185):
        block = tmp_path / f"block_{start}.py"
        block.write_text("import os\n\n" + "\n".join("    " + ln for ln in lines[start:start + 15]) + "\n")
        assert any(x["kind"] == "fingerprint" for x in R.copyleft_findings([block], fps)), start
    small = tmp_path / "small.py"
    small.write_text("\n".join(lines[50:53]) + "\n")
    assert R.copyleft_findings([small], fps) == []
    assert R.copyleft_findings([tmp_path / "notes.md"], fps) == []          # only code files are scanned


# ---------- the runtime itself stays standard library only ----------

def test_runtime_imports_only_the_standard_library_and_the_contract():
    tree = ast.parse((ROOT / "memelab/predictive/runtime.py").read_text())
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            mods.add("." * n.level + (n.module or ""))
    assert mods <= {"__future__", "hashlib", "json", "re", "time", "pathlib", "typing", "importlib", "."}, mods
