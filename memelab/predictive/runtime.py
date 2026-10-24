"""Phase 04: runtime error states, circuit breakers and install guards for the predictive engine. Research only, flag OFF.

Standard library only (no numpy, no third-party import), so it works where nothing optional is installed. Nothing here
forecasts, fetches or trains, and no existing module imports this package. Phase 17 wires these states into the scout's
predictive section; until then they are exercised by tests/test_predictive_runtime.py only.

What it guarantees (package ADVERSARIAL_SCENARIOS P30, P31, P32, P34, P47, P48; audits/predictive-intelligence/phase_04/adoption/
INSTALL_DECISION.md):
  - an absent crawler, Zep, LLM, GPU, model weights, network or optional library becomes a named state, never an exception that
    reaches discovery; every state maps to an existing contract abstain reason or to "no effect on the forecast";
  - behavioral simulation is SIMULATION_NOT_AVAILABLE unless it is approved in the config AND an adapter is given AND the
    adapter's run holds LLM-generated actions (MiroFish exits 0 when its LLM is down, phase_03 MIROFISH.md); no environment
    variable or key is ever read here;
  - a paced call guard with a consecutive-failure breaker, a call cap and a cost cap (ACCEPTANCE api_limits);
  - an install guard that accepts only exact pins with sha256 hashes and wheels (no sdist, so no setup.py runs) and refuses any
    alternate index or local path (P32);
  - a copyleft gate: license markers and fingerprints of the pinned AGPL sources (MiroFish, black-it) in the lab's code (P31).
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Callable, Iterable

from . import contract as C

# ---------------------------------------------------------------- states
AVAILABLE = "AVAILABLE"
NOT_REQUIRED = "NOT_REQUIRED"
DEPENDENCY_MISSING = "DEPENDENCY_MISSING"
MODEL_WEIGHTS_MISSING = "MODEL_WEIGHTS_MISSING"
MODEL_HASH_MISMATCH = "MODEL_HASH_MISMATCH"
NETWORK_UNAVAILABLE = "NETWORK_UNAVAILABLE"
CIRCUIT_OPEN = "CIRCUIT_OPEN"
CALL_CAP_REACHED = "CALL_CAP_REACHED"
COST_CAP_REACHED = "COST_CAP_REACHED"
COMPONENT_ERROR = "COMPONENT_ERROR"
SIMULATION_NOT_AVAILABLE = "SIMULATION_NOT_AVAILABLE"
CRAWLER_NOT_AVAILABLE = "CRAWLER_NOT_AVAILABLE"

# state -> contract abstain reason (None: no effect on the forecast; the state is still reported)
ABSTAIN_FOR = {
    AVAILABLE: None, NOT_REQUIRED: None,
    DEPENDENCY_MISSING: "MODEL_NOT_SELECTED", MODEL_WEIGHTS_MISSING: "MODEL_NOT_SELECTED", MODEL_HASH_MISMATCH: "MODEL_NOT_SELECTED",
    COMPONENT_ERROR: "MODEL_NOT_SELECTED",
    NETWORK_UNAVAILABLE: "SOURCE_STALE", CIRCUIT_OPEN: "SOURCE_STALE", CALL_CAP_REACHED: "SOURCE_STALE", COST_CAP_REACHED: "SOURCE_STALE",
    SIMULATION_NOT_AVAILABLE: None,        # behavioral scenarios stay empty; the statistical forecast is unaffected (P30)
    CRAWLER_NOT_AVAILABLE: None,           # v1 targets use no crawled input (TARGET_REGISTRY)
    C.BACKTEST_NOT_AVAILABLE: None,        # carried in backtest_status, never a combined claim (P34)
    "UNVERIFIED": None,
}
assert all(r is None or r in C.ABSTAIN_REASONS for r in ABSTAIN_FOR.values())

NETWORK_ERRORS = (ConnectionError, TimeoutError)


def _state(name: str, state: str, detail: str = "") -> dict:
    return {"component": name, "state": state, "abstain_reason": ABSTAIN_FOR.get(state, "MODEL_NOT_SELECTED"), "detail": detail}


def guarded(name: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> tuple[dict, Any]:
    """Run one optional component. Any failure becomes a state; nothing propagates to the caller (discovery never crashes)."""
    try:
        return _state(name, AVAILABLE), fn(*args, **kwargs)
    except ImportError as e:
        return _state(name, DEPENDENCY_MISSING, type(e).__name__), None
    except FileNotFoundError as e:
        return _state(name, MODEL_WEIGHTS_MISSING, type(e).__name__), None
    except NETWORK_ERRORS as e:
        return _state(name, NETWORK_UNAVAILABLE, type(e).__name__), None
    except OSError as e:          # socket.gaierror, URLError and other OS-level I/O failures
        return _state(name, NETWORK_UNAVAILABLE if _looks_network(e) else COMPONENT_ERROR, type(e).__name__), None
    except Exception as e:  # noqa: BLE001  (a visible abstention with the error class, PLANNED_SEAMS "Failure handling")
        return _state(name, COMPONENT_ERROR, type(e).__name__), None


def _looks_network(e: OSError) -> bool:
    return type(e).__name__ in ("gaierror", "herror", "URLError", "HTTPError", "SSLError") or isinstance(e, NETWORK_ERRORS)


def dependency_state(module: str) -> dict:
    """Whether an optional library could be imported, without importing it (some imports mutate the process, e.g. pandera)."""
    import importlib.util
    try:
        found = importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        found = False
    return _state(module, AVAILABLE if found else DEPENDENCY_MISSING)


def weights_state(path: str | Path, expected_sha256: str) -> dict:
    """A model artifact is usable only when it exists and its sha256 equals the registered one."""
    p = Path(path)
    if not p.is_file():
        return _state(f"weights:{p.name}", MODEL_WEIGHTS_MISSING)
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    return _state(f"weights:{p.name}", AVAILABLE if h == expected_sha256 else MODEL_HASH_MISMATCH, h[:12])


def gpu_state() -> dict:
    """The engine is CPU-only (INSTALL_DECISION.md); a GPU is never probed and its absence never matters."""
    return _state("gpu", NOT_REQUIRED)


def crawler_state() -> dict:
    """v1 targets use no crawled input; the catalyst crawler belongs to another initiative and is never called here."""
    return _state("crawler", NOT_REQUIRED)


def backtest_state(installed: dict[str, bool] | None = None) -> dict:
    return _state("backtest", C.backtest_status(installed))


def simulation_state(config: dict | None, adapter: Any = None) -> dict:
    """P30. Behavioral simulation (MiroFish or any LLM simulator) is off unless approved in the config, an adapter object is
    supplied and its run holds LLM-generated actions. Reads no environment variable and no key: a missing Zep or LLM key, an
    exhausted quota, an unreachable service and a silent run all end in SIMULATION_NOT_AVAILABLE."""
    sect = ((config or {}).get(C.FLAG_SECTION) or {}).get("behavioral") or {}
    if sect.get("approved") is not True:
        return _state("behavioral", SIMULATION_NOT_AVAILABLE, "NOT_APPROVED")
    if adapter is None:
        return _state("behavioral", SIMULATION_NOT_AVAILABLE, "ADAPTER_ABSENT")
    st, run = guarded("behavioral", adapter.run)
    if st["state"] != AVAILABLE:
        return _state("behavioral", SIMULATION_NOT_AVAILABLE, f"ADAPTER_{st['state']}:{st['detail']}")
    if not isinstance(run, dict) or int(run.get("llm_actions") or 0) <= 0:
        return _state("behavioral", SIMULATION_NOT_AVAILABLE, "NO_LLM_ACTIONS")
    return _state("behavioral", AVAILABLE)


def capability_report(config: dict | None = None, *, optional_modules: Iterable[str] = (), adapter: Any = None,
                      installed_backtest: dict[str, bool] | None = None) -> list[dict]:
    """Every optional component's state. Never raises."""
    out = [gpu_state(), crawler_state(), backtest_state(installed_backtest), simulation_state(config, adapter)]
    out += [dependency_state(m) for m in optional_modules]
    return out


def abstain_reasons(states: Iterable[dict]) -> list[str]:
    return sorted({s["abstain_reason"] for s in states if s.get("abstain_reason")})


# ---------------------------------------------------------------- paced calls, breaker and caps (P47, P48)
class CallGuard:
    """Paced external calls with a consecutive-failure breaker, a call cap and a cost cap. Failures and refusals are states;
    the callable's exception never escapes. Defaults are the frozen api_limits (6 a minute, 1,200 a run, 5 failures)."""

    def __init__(self, *, max_per_min: float | None = None, max_calls: int | None = None, breaker: int | None = None,
                 max_cost: float = 0.0, cost_per_call: float = 0.0, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        lim = C.ACCEPTANCE["api_limits"]
        self.interval = 60.0 / float(max_per_min if max_per_min is not None else lim["geckoterminal_calls_per_min"])
        self.max_calls = int(max_calls if max_calls is not None else lim["calls_per_run"])
        self.breaker = int(breaker if breaker is not None else lim["breaker_consecutive_failures"])
        self.max_cost, self.cost_per_call = float(max_cost), float(cost_per_call)
        self.clock, self.sleep = clock, sleep
        self.calls, self.failures, self.cost, self.last = 0, 0, 0.0, None

    def call(self, name: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> tuple[dict, Any]:
        if self.failures >= self.breaker:
            return _state(name, CIRCUIT_OPEN, f"{self.failures} consecutive failures"), None
        if self.calls >= self.max_calls:
            return _state(name, CALL_CAP_REACHED, f"{self.calls} calls"), None
        if self.cost_per_call and self.cost + self.cost_per_call > self.max_cost:
            return _state(name, COST_CAP_REACHED, f"cost {self.cost} + {self.cost_per_call} > {self.max_cost}"), None
        if self.last is not None:
            wait = self.last + self.interval - self.clock()
            if wait > 0:
                self.sleep(wait)
        self.calls += 1
        self.cost += self.cost_per_call
        st, val = guarded(name, fn, *args, **kwargs)
        self.last = self.clock()
        self.failures = 0 if st["state"] == AVAILABLE else self.failures + 1
        return st, val


# ---------------------------------------------------------------- install guard (P32)
_REQ = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[A-Za-z0-9,._-]+\])?==([A-Za-z0-9.+!-]+)(\s*;\s*[^\\#]+?)?\s*$")
_HASH = re.compile(r"--hash=sha256:([0-9a-f]{64})")
_BANNED_OPTIONS = ("--index-url", "-i ", "--extra-index-url", "--find-links", "-f ", "--trusted-host", "--pre", "-e ", "--editable",
                   "--no-binary", "-c ", "--constraint", "-r ", "--requirement")
INSTALL_FLAGS = ("--require-hashes", "--only-binary=:all:", "--no-deps")


def check_lock(text: str) -> list[str]:
    """Problems with a hash lock (empty list: acceptable). Every requirement is `name==version` (environment markers allowed)
    with at least one sha256 hash; no URL, VCS, path, editable, nested file or alternate index. The lab installs a lock only with
    INSTALL_FLAGS, so pip never builds an sdist (no setup.py runs) and never resolves an unlisted package."""
    problems, entries = [], []
    cur: list[str] = []
    for raw in text.splitlines():
        line = raw.split(" #", 1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if not line.strip():
            continue
        cur.append(line.rstrip("\\").strip())
        if not line.endswith("\\"):
            entries.append(" ".join(cur))
            cur = []
    if cur:
        entries.append(" ".join(cur))
    if not entries:
        return ["empty lock"]
    for e in entries:
        low = e.lower()
        if any(low.startswith(o.strip()) or f" {o}" in f" {low}" for o in _BANNED_OPTIONS):
            problems.append(f"option not allowed in a lock: {e[:60]}")
            continue
        if "://" in e or low.startswith(("git+", "file:", ".", "/")) or " @ " in e:
            problems.append(f"URL, VCS or path requirement: {e[:60]}")
            continue
        spec = _HASH.sub("", e).strip()
        if not _REQ.match(spec):
            problems.append(f"not an exact pin: {spec[:60]}")
        if not _HASH.search(e):
            problems.append(f"no sha256 hash: {spec[:60]}")
    return problems


def verify_artifact(path: str | Path, allowed_sha256: Iterable[str]) -> str:
    """AVAILABLE only for a wheel whose sha256 is in the lock; an sdist is refused before anything could run its setup.py."""
    p = Path(path)
    if not p.name.endswith(".whl"):
        return "REFUSED_NOT_A_WHEEL"
    if hashlib.sha256(p.read_bytes()).hexdigest() not in set(allowed_sha256):
        return "REFUSED_HASH_MISMATCH"
    return AVAILABLE


# ---------------------------------------------------------------- copyleft gate (P31)
_MARKERS = tuple(m.lower() for m in ("GNU AFFERO" + " GENERAL PUBLIC LICENSE", "GNU GENERAL" + " PUBLIC LICENSE",
                                      "SPDX-License-Identifier: " + "AGPL", "SPDX-License-Identifier: " + "GPL",
                                      "SPDX-License-Identifier: " + "LGPL", "Affero General" + " Public License"))
CODE_SUFFIXES = (".py", ".js", ".mjs", ".ts", ".vue", ".sh", ".html")
SHINGLE_LINES, WINNOW_WINDOW, HASH_HEX = 4, 12, 12


def normalized_lines(text: str) -> list[str]:
    """Whitespace collapsed, case kept; lines shorter than 8 characters (braces, `else:`, `pass`) dropped."""
    out = []
    for ln in text.splitlines():
        s = " ".join(ln.split())
        if len(s) >= 8:
            out.append(s)
    return out


def shingle_hashes(text: str) -> list[str]:
    ls = normalized_lines(text)
    return [hashlib.sha256("\n".join(ls[i:i + SHINGLE_LINES]).encode()).hexdigest()[:HASH_HEX]
            for i in range(len(ls) - SHINGLE_LINES + 1)]


def winnow(hashes: list[str], w: int = WINNOW_WINDOW) -> set[str]:
    """Winnowing (Schleimer, Wilkerson and Aiken 2003): the minimum hash of every window of w shingles, so any copied run of at
    least w + SHINGLE_LINES - 1 normalized lines shares at least one kept fingerprint."""
    if len(hashes) <= w:
        return {min(hashes)} if hashes else set()
    return {min(hashes[i:i + w]) for i in range(len(hashes) - w + 1)}


def load_fingerprints(path: str | Path) -> set[str]:
    return set(json.loads(Path(path).read_text())["fingerprints"])


def copyleft_findings(paths: Iterable[str | Path], fingerprints: set[str] | None = None) -> list[dict]:
    """License markers and fingerprint matches in code files. Empty list: the gate passes."""
    found = []
    for p in paths:
        p = Path(p)
        if p.suffix not in CODE_SUFFIXES or not p.is_file():
            continue
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        low = text.lower()
        for m in _MARKERS:
            if m in low:
                found.append({"path": str(p), "kind": "license_marker", "match": m})
        if fingerprints:
            hits = sorted(set(shingle_hashes(text)) & fingerprints)
            if hits:
                found.append({"path": str(p), "kind": "fingerprint", "match": hits[:5], "count": len(hits)})
    return found
