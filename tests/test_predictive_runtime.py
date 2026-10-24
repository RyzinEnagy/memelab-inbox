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
CORE_LOCK = ROOT / "docs/predictive-intelligence/locks/core-py313.txt"
BOM_DIR = ROOT / "audits/predictive-intelligence/phase_04/adoption/evidence"
BAKEOFF_CSV = ROOT / "audits/predictive-intelligence/phase_04/adoption/data/dev_t1_24h.csv"
MIROFISH_CLONE = Path("/home/claude/pi_research/src/666ghj__MiroFish")
# license detectors that hold license titles as data (marker check only; the fingerprint check still applies to them)
MARKER_DATA_FILES = ("audits/predictive-intelligence/phase_02/probes/verify_repos.py",
                     "audits/predictive-intelligence/phase_03/research/verify/verify_generic.py")
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache", ".venv", "venv"}
# sha256 of the committed locks; changing a lock is a recorded decision (PI-D-032, PI-D-035) that updates these and BOM_LOCKS.md
LOCK_SHA256 = {"research-py313.txt": "1347f84bb2639143e85e8532e09c8513e0ab679b3982ed8ba5d5bf3b45f2ba84",
               "core-py313.txt": "89fe4f4dc37a450ffd2b660eedcff8d4e93a81ac9df2566c21b504ce5a722865"}


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
    (APPROVED, Adapter(exc=SystemExit(1)), "ADAPTER_COMPONENT_ERROR:SystemExit"),        # MiroFish's run.py exits on missing keys
    (APPROVED, Adapter({"llm_actions": "many"}), "NO_LLM_ACTIONS"),
    (APPROVED, Adapter({"llm_actions": float("nan")}), "NO_LLM_ACTIONS"),
    (APPROVED, Adapter({"llm_actions": float("inf")}), "NO_LLM_ACTIONS"),
    (APPROVED, Adapter({"llm_actions": [3]}), "NO_LLM_ACTIONS"),
    (APPROVED, Adapter({"llm_actions": {"n": 1}}), "NO_LLM_ACTIONS"),
    (APPROVED, Adapter({"llm_actions": True}), "NO_LLM_ACTIONS"),
    (APPROVED, Adapter({"llm_actions": "5"}), "NO_LLM_ACTIONS"),
    (APPROVED, Adapter({"llm_actions": 5.0}), "NO_LLM_ACTIONS"),
    (APPROVED, Adapter({"llm_actions": -2}), "NO_LLM_ACTIONS"),
    (APPROVED, object(), "ADAPTER_COMPONENT_ERROR:AttributeError"),                    # no run() at all
    ({"predictive": True}, Adapter({"llm_actions": 5}), "NOT_APPROVED"),
    ({"predictive": "on"}, Adapter({"llm_actions": 5}), "NOT_APPROVED"),
    ({"predictive": {"behavioral": "yes"}}, Adapter({"llm_actions": 5}), "NOT_APPROVED"),
    (["predictive"], Adapter({"llm_actions": 5}), "NOT_APPROVED"),
    ("approved", Adapter({"llm_actions": 5}), "NOT_APPROVED"),
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
    (SystemExit(1), R.COMPONENT_ERROR, "MODEL_NOT_SELECTED"),           # a component's sys.exit must not end discovery
    (SystemExit("missing key"), R.COMPONENT_ERROR, "MODEL_NOT_SELECTED"),
    (KeyError("price"), R.COMPONENT_ERROR, "MODEL_NOT_SELECTED"),
    (TypeError("unsupported operand"), R.COMPONENT_ERROR, "MODEL_NOT_SELECTED"),
    (AttributeError("no attribute"), R.COMPONENT_ERROR, "MODEL_NOT_SELECTED"),
    (ZeroDivisionError(), R.COMPONENT_ERROR, "MODEL_NOT_SELECTED"),
    (IndexError(), R.COMPONENT_ERROR, "MODEL_NOT_SELECTED"),
    (RecursionError(), R.COMPONENT_ERROR, "MODEL_NOT_SELECTED"),
    (UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad"), R.COMPONENT_ERROR, "MODEL_NOT_SELECTED"),
    (PermissionError("denied"), R.COMPONENT_ERROR, "MODEL_NOT_SELECTED"),
    (type("CustomBase", (BaseException,), {})(), R.COMPONENT_ERROR, "MODEL_NOT_SELECTED"),
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


@pytest.mark.parametrize("exc", [KeyboardInterrupt(), GeneratorExit()])
def test_operator_stop_and_generator_exit_are_not_contained_on_purpose(exc):
    def stop():
        raise exc
    with pytest.raises(type(exc)):
        R.guarded("component", stop)
    assert R.NOT_CONTAINED == (KeyboardInterrupt, GeneratorExit)


@pytest.mark.parametrize("config", [None, {}, [], "x", 3, {"predictive": True}, {"predictive": "on"}, {"predictive": []},
                                    {"predictive": {"behavioral": "yes"}}, {"predictive": {"behavioral": None}}, ["predictive"]])
def test_capability_report_never_raises_on_any_config_shape(no_keys, config):
    rep = R.capability_report(config, optional_modules=["json", "p04_absent_module", "pkg.sub", None, 7],
                              adapter=Adapter(exc=SystemExit(2)))
    assert [s["component"] for s in rep][:4] == ["gpu", "crawler", "backtest", "behavioral"]
    assert next(s for s in rep if s["component"] == "behavioral")["state"] == R.SIMULATION_NOT_AVAILABLE
    assert all(s["abstain_reason"] is None or s["abstain_reason"] in C.ABSTAIN_REASONS for s in rep)


def test_capability_report_survives_a_raising_module_iterable(no_keys):
    def bad_modules():
        yield "json"
        raise RuntimeError("iterator broke")
    rep = R.capability_report(None, optional_modules=bad_modules())
    assert rep[-1]["component"] == "optional_modules" and rep[-1]["state"] == R.COMPONENT_ERROR


@pytest.mark.parametrize("text", ['{"predictive": true}', "[]", '"x"', "3", "null", '{"predictive": {"enabled": "true"}}',
                                  '{"predictive": ["enabled"]}', "{not json", ""])
def test_feature_flag_is_off_for_malformed_config(tmp_path, text):
    f = tmp_path / "config.json"
    f.write_text(text)
    assert C.enabled(f) is False
    f.write_text('{"predictive": {"enabled": true}}')
    assert C.enabled(f) is True


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
    # a dotted name would make find_spec import the parent package and run its code: refused without importing
    pkg = tmp_path / "p04_hostile_pkg"
    pkg.mkdir()
    marker = tmp_path / "PARENT_RAN"
    (pkg / "__init__.py").write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n")
    (pkg / "sub.py").write_text("x = 1\n")
    st = R.dependency_state("p04_hostile_pkg.sub")
    assert st["state"] == R.DEPENDENCY_MISSING and "top-level" in st["detail"] and not marker.exists()
    assert R.dependency_state("p04_hostile_pkg")["state"] == R.AVAILABLE and not marker.exists()
    assert R.dependency_state(None)["state"] == R.DEPENDENCY_MISSING


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


def test_breaker_counts_any_failure_not_only_network_errors(no_keys):
    clk = FakeClock()
    g = R.CallGuard(clock=clk, sleep=clk.sleep)

    def http_500():
        raise RuntimeError("HTTP 500")
    out = [g.call("gt", http_500)[0]["state"] for _ in range(7)]
    assert out == [R.COMPONENT_ERROR] * 5 + [R.CIRCUIT_OPEN] * 2


def test_returned_error_responses_count_when_the_caller_says_how(no_keys):
    clk = FakeClock()
    g = R.CallGuard(clock=clk, sleep=clk.sleep, is_failure=lambda r: r["status"] != 200)
    out = [g.call("gt", lambda: {"status": 429}) for _ in range(6)]
    assert [st["state"] for st, _ in out] == [R.BAD_RESPONSE] * 5 + [R.CIRCUIT_OPEN]
    assert all(v is None for _, v in out) and out[0][0]["abstain_reason"] == "SOURCE_STALE"
    g2 = R.CallGuard(clock=clk, sleep=clk.sleep, is_failure=lambda r: r["status"] != 200)
    assert g2.call("gt", lambda: {"status": 200})[1] == {"status": 200}
    g3 = R.CallGuard(clock=clk, sleep=clk.sleep, is_failure=lambda r: r["missing_key"])
    assert g3.call("gt", lambda: {"status": 200})[0]["state"] == R.BAD_RESPONSE    # a raising predicate is a failure too


@pytest.mark.parametrize("state", [R.CIRCUIT_OPEN, R.CALL_CAP_REACHED, R.COST_CAP_REACHED, R.NETWORK_UNAVAILABLE, R.BAD_RESPONSE])
def test_refusals_and_network_states_abstain_as_source_stale(state):
    assert R.ABSTAIN_FOR[state] == "SOURCE_STALE"


@pytest.mark.parametrize("kw", [{"max_cost": 1.0, "cost_per_call": float("nan")}, {"max_cost": float("nan"), "cost_per_call": 1.0},
                                {"max_cost": float("inf"), "cost_per_call": 1.0}, {"max_cost": 1.0, "cost_per_call": -1.0},
                                {"max_cost": "1", "cost_per_call": 1.0}, {"max_cost": True, "cost_per_call": 1.0}])
def test_a_non_finite_or_negative_cost_setting_fails_closed(no_keys, kw):
    clk = FakeClock()
    g = R.CallGuard(clock=clk, sleep=clk.sleep, **kw)
    spent = []
    out = [g.call("paid", lambda: spent.append(1))[0]["state"] for _ in range(3)]
    assert out == [R.COST_CAP_REACHED] * 3 and spent == []


@pytest.mark.parametrize("kw", [{"max_per_min": 0}, {"max_per_min": float("nan")}, {"max_calls": -1}, {"max_calls": 1.5},
                                {"breaker": 0}, {"breaker": float("inf")}])
def test_invalid_pace_or_caps_are_refused_when_the_guard_is_built(kw):
    with pytest.raises(ValueError):
        R.CallGuard(**kw)


# ---------- P34: backtest absent ----------

def test_p34_absent_backtest_is_reported_never_claimed(no_keys):
    rep = R.capability_report(None, installed_backtest={m: False for m in C.BACKTEST_MODULES})
    bt = next(s for s in rep if s["component"] == "backtest")
    assert bt["state"] == C.BACKTEST_NOT_AVAILABLE and bt["abstain_reason"] is None
    assert R.backtest_state({"memelab.backtest": True})["state"] == "UNVERIFIED"       # importable is not verified
    assert R.backtest_state()["state"] == C.BACKTEST_NOT_AVAILABLE                       # nothing installed in this repository


# ---------- P32: hostile setup ----------

GOOD = "numpy==2.5.3 \\\n    --hash=sha256:" + "a" * 64 + "\ncolorama==0.4.6 ; sys_platform == 'win32' \\\n    --hash=sha256:" + "b" * 64 + "\n"


H = "a" * 64
ONLY_HASH = "only --hash=sha256:<64 hex> may follow"


@pytest.mark.parametrize("bad, why", [
    ("numpy>=2.0 --hash=sha256:" + "a" * 64, "not an exact pin"),
    ("numpy==2.* --hash=sha256:" + H, "not an exact pin"),
    ("numpy==2.5.3", "no sha256 hash"),
    ("numpy==2.5.3 --hash=sha256:" + "a" * 63, ONLY_HASH),
    ("numpy==2.5.3 --hash=sha256:" + "A" * 64, ONLY_HASH),
    ("numpy==2.5.3 --hash=md5:" + "a" * 32, ONLY_HASH),
    # the Phase 04 skeptic's counterexample (M1): an option after a marker re-enables sdists, so setup.py would run
    ('p04sk==1.0 ; python_version >= "3" --hash=sha256:' + H + " --only-binary=:none:", ONLY_HASH),
    # and its variant: an extra non-sha256 hash admits a file whose sha256 is not locked
    ('pkg==1.0 ; python_version >= "3" --hash=sha256:' + H + " --hash=sha512:" + "b" * 128, ONLY_HASH),
    ("pkg==1.0 --hash=sha256:" + H + " --hash=sha384:" + "c" * 96, ONLY_HASH),
    ("pkg==1.0 --hash=sha256:" + H + " --only-binary=:none:", ONLY_HASH),
    ("pkg==1.0 --hash=sha256:" + H + " --config-settings=--build-option=x", ONLY_HASH),
    ("pkg==1.0 --hash=sha256:" + H + " --global-option=build_ext", ONLY_HASH),
    ("pkg==1.0 --hash=sha256:" + H + " --no-binary=:all:", ONLY_HASH),
    ("pkg==1.0 --prefer-binary --hash=sha256:" + H, ONLY_HASH),
    ('pkg==1.0 ; python_version >= "3"--only-binary=:none: --hash=sha256:' + H, "environment marker not allowed"),
    ("pkg==1.0 ; os_name == 'posix' -x --hash=sha256:" + H, ONLY_HASH),
    ("pkg==1.0 ; os_name == 'posix' # --only-binary=:none:\n", "no sha256 hash"),
    ("pkg==1.0 ; os_name == 'posix' $(touch x) --hash=sha256:" + H, "environment marker not allowed"),
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
def test_p32_lock_guard_refuses_anything_but_hashed_exact_pins(bad, why, tmp_path):
    assert R.check_lock(GOOD) == []
    probs = R.check_lock(GOOD + bad + "\n")
    assert probs and why in " | ".join(probs)
    f = tmp_path / "lock.txt"
    f.write_text(GOOD + bad + "\n")
    with pytest.raises(R.InstallRefused):
        R.install_argv(f)                                # the install command is never built for such a lock


def _bom_wheel_hashes(name):
    bom = json.loads((BOM_DIR / f"{name}.bom.json").read_text())
    return {w["sha256"] for p in bom["packages"] for w in p["wheels"] if w["file"].endswith(".whl")}


@pytest.mark.parametrize("lock, bom", [(LOCK, "research-py313"), (CORE_LOCK, "core-py313")])
def test_p32_committed_locks_hold_only_known_wheel_digests_and_are_pinned(lock, bom):
    text = lock.read_text()
    wheels = _bom_wheel_hashes(bom)
    assert R.check_lock(text, wheels) == []
    assert R.check_lock(text, wheels - {sorted(wheels)[0]})        # a hash outside the BOM's wheels is refused
    assert sum(len(v) for v in R.lock_hashes(text).values()) == len(wheels)
    # any edit to a lock is a recorded decision (PI-D-032): its sha256 is pinned here and in BOM_LOCKS.md
    assert hashlib.sha256(lock.read_bytes()).hexdigest() == LOCK_SHA256[lock.name]
    assert LOCK_SHA256[lock.name] in (ROOT / "audits/predictive-intelligence/phase_04/adoption/BOM_LOCKS.md").read_text()


def test_p32_install_argv_is_the_only_route_and_carries_the_flags(tmp_path):
    argv = R.install_argv(LOCK, python="py", wheel_hashes=_bom_wheel_hashes("research-py313"))
    assert argv[:4] == ["py", "-m", "pip", "install"] and set(R.INSTALL_FLAGS) <= set(argv) and argv[-2:] == ["-r", str(LOCK)]
    assert set(R.INSTALL_FLAGS) == {"--require-hashes", "--only-binary=:all:", "--no-deps"}
    assert R.check_lock("") == ["empty lock"]
    other = tmp_path / "other.txt"
    other.write_text("numpy==2.5.3 --hash=sha256:" + "f" * 64 + "\n")
    with pytest.raises(R.InstallRefused):
        R.install_argv(other, wheel_hashes=_bom_wheel_hashes("core-py313"))


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

def _repo_code_files():
    """Every code file in the repository (lab code, tests, tools, audits and root scripts), skipping caches and any venv."""
    out = []
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT).parts
        if any(x in SKIP_DIRS for x in rel) or not p.is_file() or p.suffix not in R.CODE_SUFFIXES:
            continue
        if any((ROOT.joinpath(*rel[:i]) / "pyvenv.cfg").exists() for i in range(1, len(rel))):
            continue
        out.append(p)
    return out


def test_p31_no_code_file_in_the_repository_has_a_copyleft_marker_or_fingerprint():
    fp = R.load_fingerprints(FINGERPRINTS)
    doc = json.loads(FINGERPRINTS.read_text())
    assert {s["repo"] for s in doc["sources"]} == {"666ghj/MiroFish", "bancaditalia/black-it"}
    assert len(fp) > 1000 and all(len(h) == R.HASH_HEX for h in fp)
    files = _repo_code_files()
    rels = {p.relative_to(ROOT).as_posix() for p in files}
    assert len(files) > 300 and "bootstrap.sh" in rels and any(r.startswith("audits/") for r in rels)
    assert R.copyleft_findings(files, fp, marker_allowed=[ROOT / m for m in MARKER_DATA_FILES]) == []
    # the two exempt detectors do hold the titles (so the exemption is needed) and stay under the fingerprint check
    assert all(R.copyleft_findings([ROOT / m]) for m in MARKER_DATA_FILES)


def test_p31_fixture_matches_the_runtime_hashing_exactly():
    doc = json.loads(FINGERPRINTS.read_text())
    assert {k: doc[k] for k in R.fingerprint_spec()} == R.fingerprint_spec()
    assert R.FINGERPRINT_ALGO == "sha256" and R.HASH_HEX == 12 and R.SHINGLE_LINES == 4 and R.WINNOW_WINDOW == 12
    # golden self-test: the builder's fingerprints of a mixed-case synthetic text must be reproduced byte for byte
    st = doc["selftest"]
    assert sorted(R.winnow(R.shingle_hashes(st["text"]))) == st["fingerprints"] and len(st["fingerprints"]) > 10


def test_p31_a_fixture_built_differently_is_refused(tmp_path):
    doc = json.loads(FINGERPRINTS.read_text())
    doc["hash"] = "sha1 hex prefix 12"
    f = tmp_path / "fp.json"
    f.write_text(json.dumps(doc))
    with pytest.raises(ValueError):
        R.load_fingerprints(f)


@pytest.mark.skipif(not (MIROFISH_CLONE / "backend").is_dir(), reason="pinned MiroFish clone not present on this machine")
def test_p31_positive_control_on_the_pinned_mirofish_clone():
    files = [p for p in (MIROFISH_CLONE / "backend").rglob("*.py") if ".venv" not in p.parts]
    hits = {x["path"] for x in R.copyleft_findings(files, R.load_fingerprints(FINGERPRINTS)) if x["kind"] == "fingerprint"}
    assert len(hits) >= 0.8 * len(files)


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
    # a file exempt from the marker check (a license detector) is still under the fingerprint check
    assert any(x["kind"] == "fingerprint" for x in R.copyleft_findings([block], fps, marker_allowed=[block]))
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
    assert mods <= {"__future__", "hashlib", "json", "math", "re", "time", "pathlib", "typing", "importlib", "."}, mods


# ---------- bake-off labels stay out of later phases (PI-D-034) ----------

def test_bakeoff_labels_are_refused_as_a_label_source():
    import csv
    rows = list(csv.DictReader(BAKEOFF_CSV.open()))
    assert rows and all(r["use"] == R.BAKEOFF_ONLY for r in rows)
    with pytest.raises(ValueError):
        R.refuse_bakeoff_labels(rows)
    with pytest.raises(ValueError):
        R.refuse_bakeoff_labels(path=BAKEOFF_CSV)
    R.refuse_bakeoff_labels([{"use": "PHASE06_LABEL"}], path=ROOT / "tests/fixtures/predictive/forecast_examples_format_only.json")
    # no lab module other than the guard itself names the bake-off data folder
    named = [p.relative_to(ROOT).as_posix() for p in (ROOT / "memelab").rglob("*.py")
             if "phase_04/adoption/data" in p.read_text() and p.name != "runtime.py"]
    assert named == []
