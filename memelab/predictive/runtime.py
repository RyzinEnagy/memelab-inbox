"""Phase 04: runtime error states, circuit breakers and install guards for the predictive engine. Research only, flag OFF.

Standard library only (no numpy, no third-party import), so it works where nothing optional is installed. Nothing here
forecasts, fetches or trains, and no existing module imports this package. Phase 17 wires these states into the scout's
predictive section; until then they are exercised by tests/test_predictive_runtime.py only.

What it guarantees (package ADVERSARIAL_SCENARIOS P30, P31, P32, P34, P47, P48; audits/predictive-intelligence/phase_04/adoption/
INSTALL_DECISION.md; repaired after the Phase 04 skeptic, PI-D-035):
  - an absent crawler, Zep, LLM, GPU, model weights, network or optional library becomes a named state, never an exception that
    reaches discovery; every state maps to an existing contract abstain reason or to "no effect on the forecast". `guarded`
    contains every exception including SystemExit; only KeyboardInterrupt (an operator stopping the run) and GeneratorExit (the
    interpreter's generator protocol) pass through, on purpose. `capability_report` and `simulation_state` never raise, for any
    config shape and any adapter result;
  - behavioral simulation is SIMULATION_NOT_AVAILABLE unless it is approved in the config (the JSON value true) AND an adapter
    is given AND the adapter's run reports a positive integer count of LLM-generated actions (MiroFish exits 0 when its LLM is
    down, phase_03 MIROFISH.md); no environment variable or key is ever read here;
  - a paced call guard with a consecutive-failure breaker, a call cap and a cost cap that fails closed on a non-finite or
    negative cost setting (ACCEPTANCE api_limits);
  - an install guard: every lock entry is `name==version`, an optional plain environment marker, then only
    `--hash=sha256:<64 hex>` tokens; any other option anywhere in an entry is refused, because pip honours per-line options such
    as `--only-binary=:none:` (which re-enables sdists, so a setup.py would run) or `--hash=sha512:` (which admits another file).
    With known wheel digests supplied, every hash must be one of them. `install_argv` is the only way the lab builds an install
    command (P32);
  - a copyleft gate: license markers and winnowed fingerprints of the pinned AGPL sources (MiroFish, black-it) in code (P31);
    the hash algorithm, normalization, shingle length and window are constants the fixture must declare identically.
"""
from __future__ import annotations

import hashlib
import json
import math
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
BAD_RESPONSE = "BAD_RESPONSE"
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
    NETWORK_UNAVAILABLE: "SOURCE_STALE", BAD_RESPONSE: "SOURCE_STALE", CIRCUIT_OPEN: "SOURCE_STALE", CALL_CAP_REACHED: "SOURCE_STALE",
    COST_CAP_REACHED: "SOURCE_STALE",
    SIMULATION_NOT_AVAILABLE: None,        # behavioral scenarios stay empty; the statistical forecast is unaffected (P30)
    CRAWLER_NOT_AVAILABLE: None,           # v1 targets use no crawled input (TARGET_REGISTRY)
    C.BACKTEST_NOT_AVAILABLE: None,        # carried in backtest_status, never a combined claim (P34)
    "UNVERIFIED": None,
}
assert all(r is None or r in C.ABSTAIN_REASONS for r in ABSTAIN_FOR.values())

NETWORK_ERRORS = (ConnectionError, TimeoutError)
NOT_CONTAINED = (KeyboardInterrupt, GeneratorExit)     # deliberate: an operator's stop and the generator protocol


def _state(name: str, state: str, detail: str = "") -> dict:
    return {"component": name, "state": state, "abstain_reason": ABSTAIN_FOR.get(state, "MODEL_NOT_SELECTED"), "detail": detail}


def guarded(name: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> tuple[dict, Any]:
    """Run one optional component. Every failure, SystemExit included, becomes a state; only NOT_CONTAINED passes through."""
    try:
        return _state(name, AVAILABLE), fn(*args, **kwargs)
    except NOT_CONTAINED:
        raise
    except ImportError as e:
        return _state(name, DEPENDENCY_MISSING, type(e).__name__), None
    except FileNotFoundError as e:
        return _state(name, MODEL_WEIGHTS_MISSING, type(e).__name__), None
    except NETWORK_ERRORS as e:
        return _state(name, NETWORK_UNAVAILABLE, type(e).__name__), None
    except OSError as e:          # socket.gaierror, URLError and other OS-level I/O failures
        return _state(name, NETWORK_UNAVAILABLE if _looks_network(e) else COMPONENT_ERROR, type(e).__name__), None
    except BaseException as e:  # noqa: BLE001  (SystemExit and everything else: a visible abstention with the error class)
        return _state(name, COMPONENT_ERROR, type(e).__name__), None


def _looks_network(e: OSError) -> bool:
    return type(e).__name__ in ("gaierror", "herror", "URLError", "HTTPError", "SSLError") or isinstance(e, NETWORK_ERRORS)


def _section(cfg: Any, *keys: str) -> dict:
    """The nested config object at keys, or {} when any level is missing or not a JSON object (malformed means OFF)."""
    cur = cfg
    for k in keys:
        if not isinstance(cur, dict):
            return {}
        cur = cur.get(k)
    return cur if isinstance(cur, dict) else {}


def dependency_state(module: str) -> dict:
    """Whether an optional top-level package could be imported, without importing it (some imports mutate the process, e.g.
    pandera). A dotted name is refused: find_spec("pkg.sub") imports "pkg" to read its path, which runs its code."""
    if not isinstance(module, str) or not module.isidentifier():
        return _state(str(module), DEPENDENCY_MISSING, "refused: only a top-level package name is probed")
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


def _llm_action_count(run: Any) -> int:
    """A positive int (not a bool, not a string, not a float) or 0. Anything else means no LLM-generated action."""
    n = run.get("llm_actions") if isinstance(run, dict) else None
    return n if type(n) is int and n > 0 else 0


def simulation_state(config: Any, adapter: Any = None) -> dict:
    """P30. Behavioral simulation (MiroFish or any LLM simulator) is off unless approved in the config, an adapter object is
    supplied and its run reports LLM-generated actions. Reads no environment variable and no key: a missing Zep or LLM key, an
    exhausted quota, an unreachable service, a sys.exit inside the adapter and a silent run all end in SIMULATION_NOT_AVAILABLE.
    Never raises (except NOT_CONTAINED)."""
    if _section(config, C.FLAG_SECTION, "behavioral").get("approved") is not True:
        return _state("behavioral", SIMULATION_NOT_AVAILABLE, "NOT_APPROVED")
    if adapter is None:
        return _state("behavioral", SIMULATION_NOT_AVAILABLE, "ADAPTER_ABSENT")
    st, run = guarded("behavioral", lambda: adapter.run())
    if st["state"] != AVAILABLE:
        return _state("behavioral", SIMULATION_NOT_AVAILABLE, f"ADAPTER_{st['state']}:{st['detail']}")
    if _llm_action_count(run) <= 0:
        return _state("behavioral", SIMULATION_NOT_AVAILABLE, "NO_LLM_ACTIONS")
    return _state("behavioral", AVAILABLE)


def _probe(name: str, fn: Callable[..., dict], *args: Any) -> dict:
    st, val = guarded(name, fn, *args)
    if st["state"] == AVAILABLE and isinstance(val, dict) and "state" in val:
        return val
    return _state(name, COMPONENT_ERROR, f"probe failed: {st['detail'] or type(val).__name__}")


def capability_report(config: Any = None, *, optional_modules: Iterable[str] = (), adapter: Any = None,
                      installed_backtest: dict[str, bool] | None = None) -> list[dict]:
    """Every optional component's state. Never raises (except NOT_CONTAINED): each probe runs inside `guarded`."""
    out = [_probe("gpu", gpu_state), _probe("crawler", crawler_state), _probe("backtest", backtest_state, installed_backtest),
           _probe("behavioral", simulation_state, config, adapter)]
    st, mods = guarded("optional_modules", lambda: list(optional_modules))
    if st["state"] != AVAILABLE:
        return out + [_state("optional_modules", COMPONENT_ERROR, st["detail"])]
    return out + [_probe(m if isinstance(m, str) else "optional_module", dependency_state, m) for m in mods]


def abstain_reasons(states: Iterable[dict]) -> list[str]:
    return sorted({s["abstain_reason"] for s in states if s.get("abstain_reason")})


# ---------------------------------------------------------------- paced calls, breaker and caps (P47, P48)
def _finite_nonneg(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x >= 0


class CallGuard:
    """Paced external calls with a consecutive-failure breaker, a call cap and a cost cap. Failures and refusals are states;
    the callable's exception never escapes. Defaults are the frozen api_limits (6 a minute, 1,200 a run, 5 failures).

    A callable must raise on a failed request; one that returns an HTTP error instead is caught only through `is_failure`
    (for example `lambda r: r.status != 200`), which turns such a value into BAD_RESPONSE and counts it toward the breaker.
    Any exception counts toward the breaker, not only network errors. A non-finite or negative cost setting fails closed: every
    call is refused with COST_CAP_REACHED. Invalid pace or call settings raise ValueError when the guard is built."""

    def __init__(self, *, max_per_min: float | None = None, max_calls: int | None = None, breaker: int | None = None,
                 max_cost: float = 0.0, cost_per_call: float = 0.0, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep, is_failure: Callable[[Any], bool] | None = None):
        lim = C.ACCEPTANCE["api_limits"]
        per_min = max_per_min if max_per_min is not None else lim["geckoterminal_calls_per_min"]
        calls = max_calls if max_calls is not None else lim["calls_per_run"]
        brk = breaker if breaker is not None else lim["breaker_consecutive_failures"]
        if not (_finite_nonneg(per_min) and per_min > 0 and type(calls) is int and calls >= 0 and type(brk) is int and brk >= 1):
            raise ValueError("CallGuard needs a finite positive pace, an int call cap >= 0 and an int breaker >= 1")
        self.interval, self.max_calls, self.breaker = 60.0 / float(per_min), calls, brk
        self.cost_ok = _finite_nonneg(max_cost) and _finite_nonneg(cost_per_call)
        self.max_cost = float(max_cost) if self.cost_ok else 0.0
        self.cost_per_call = float(cost_per_call) if self.cost_ok else 0.0
        self.clock, self.sleep, self.is_failure = clock, sleep, is_failure
        self.calls, self.failures, self.cost, self.last = 0, 0, 0.0, None

    def call(self, name: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> tuple[dict, Any]:
        if not self.cost_ok:
            return _state(name, COST_CAP_REACHED, "non-finite or negative cost setting: fails closed"), None
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
        if st["state"] == AVAILABLE and self.is_failure is not None:
            chk, bad = guarded(f"{name}:is_failure", self.is_failure, val)
            if chk["state"] != AVAILABLE or bad:
                st, val = _state(name, BAD_RESPONSE, chk["detail"] or "is_failure"), None
        self.failures = 0 if st["state"] == AVAILABLE else self.failures + 1
        return st, val


# ---------------------------------------------------------------- install guard (P32)
_SPEC = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?(?:\[[A-Za-z0-9,._-]+\])?==[A-Za-z0-9.+!]+$")
_MARKER = re.compile(r"""^[A-Za-z0-9_.\s'"()<>=!~,*+/-]+$""")
_HASH_TOKEN = re.compile(r"--hash=sha256:([0-9a-f]{64})")
_COMMENT = re.compile(r"(^|\s+)#.*$")
INSTALL_FLAGS = ("--require-hashes", "--only-binary=:all:", "--no-deps")


class InstallRefused(ValueError):
    pass


def _lock_entries(text: str) -> list[str]:
    entries, cur = [], []
    for raw in text.splitlines():
        line = _COMMENT.sub("", raw).rstrip()          # pip's own comment rule
        if not line.strip():
            if cur and not raw.rstrip().endswith("\\"):
                entries.append(" ".join(cur))
                cur = []
            continue
        cur.append(line.rstrip("\\").strip())
        if not line.endswith("\\"):
            entries.append(" ".join(cur))
            cur = []
    if cur:
        entries.append(" ".join(cur))
    return entries


def lock_hashes(text: str) -> dict[str, list[str]]:
    """Requirement (with marker) -> its sha256 hashes, for entries that pass `check_lock`."""
    out = {}
    for e in _lock_entries(text):
        toks = e.split()
        k = next((i for i, t in enumerate(toks) if t.startswith("-")), len(toks))
        out[" ".join(toks[:k])] = [m.group(1) for m in (_HASH_TOKEN.fullmatch(t) for t in toks[k:]) if m]
    return out


def check_lock(text: str, wheel_hashes: Iterable[str] | None = None) -> list[str]:
    """Problems with a hash lock (empty list: acceptable). Each entry must be exactly: `name==version`, optionally
    `; <environment marker>` made of plain marker characters with no `--` and no word starting with `-`, then one or more
    `--hash=sha256:<64 lowercase hex>` tokens and nothing else. Every other option is refused wherever it appears, including
    after a marker or a hash: pip applies per-line options (`--only-binary=:none:`, `--hash=sha512:`, `--config-settings`,
    `--global-option`) to that requirement and they can defeat INSTALL_FLAGS (Phase 04 skeptic M1). When `wheel_hashes` is
    given (the wheel digests of the lock's BOM), every hash must be one of them, so no entry can admit an sdist."""
    entries = _lock_entries(text)
    if not entries:
        return ["empty lock"]
    known = set(wheel_hashes) if wheel_hashes is not None else None
    problems = []
    for e in entries:
        toks = e.split()
        k = next((i for i, t in enumerate(toks) if t.startswith("-")), None)
        if k == 0:
            problems.append(f"option not allowed in a lock: {e[:60]}")
            continue
        args, opts = " ".join(toks[:k]), toks[k:] if k is not None else []
        if "://" in args or "@" in args or args.startswith(("git+", "file:", ".", "/", "\\")):
            problems.append(f"URL, VCS or path requirement: {args[:60]}")
            continue
        if not opts:
            problems.append(f"no sha256 hash: {e[:60]}")
            continue
        bad = [t for t in opts if not _HASH_TOKEN.fullmatch(t)]
        if bad:
            problems.append(f"only --hash=sha256:<64 hex> may follow a requirement; refused {bad[0][:40]!r} in {args[:40]}")
            continue
        spec, sep, marker = args.partition(";")
        if not _SPEC.match(spec.strip()):
            problems.append(f"not an exact pin: {spec.strip()[:60]}")
            continue
        if sep and (not marker.strip() or not _MARKER.match(marker) or "--" in marker or any(w.startswith("-") for w in marker.split())):
            problems.append(f"environment marker not allowed: {marker.strip()[:60]!r}")
            continue
        if known is not None:
            for t in opts:
                h = _HASH_TOKEN.fullmatch(t).group(1)
                if h not in known:
                    problems.append(f"hash {h[:12]} of {spec.strip()} is not a known wheel digest")
    return problems


def install_argv(lock_path: str | Path, *, python: str = "python", wheel_hashes: Iterable[str] | None = None) -> list[str]:
    """The only install command the lab builds: the lock is checked first, then pip runs with INSTALL_FLAGS. Raises
    InstallRefused (before anything is installed) when the lock has a problem. The caller runs the returned argv at once."""
    probs = check_lock(Path(lock_path).read_text(), wheel_hashes)
    if probs:
        raise InstallRefused("; ".join(probs[:3]))
    return [python, "-m", "pip", "install", *INSTALL_FLAGS, "-r", str(lock_path)]


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
CODE_SUFFIXES = (".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".vue", ".css", ".sh", ".html")
SHINGLE_LINES, WINNOW_WINDOW, HASH_HEX = 4, 12, 12
FINGERPRINT_ALGO = "sha256"
NORMALIZATION = "whitespace collapsed, case kept, lines under 8 characters dropped"


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
    return [hashlib.new(FINGERPRINT_ALGO, "\n".join(ls[i:i + SHINGLE_LINES]).encode()).hexdigest()[:HASH_HEX]
            for i in range(len(ls) - SHINGLE_LINES + 1)]


def winnow(hashes: list[str], w: int = WINNOW_WINDOW) -> set[str]:
    """Winnowing (Schleimer, Wilkerson and Aiken 2003): the minimum hash of every window of w shingles, so any copied run of at
    least w + SHINGLE_LINES - 1 normalized lines shares at least one kept fingerprint."""
    if len(hashes) <= w:
        return {min(hashes)} if hashes else set()
    return {min(hashes[i:i + w]) for i in range(len(hashes) - w + 1)}


def fingerprint_spec() -> dict:
    """What a fingerprint fixture must declare to be comparable with this module (checked by the tests)."""
    return {"shingle_lines": SHINGLE_LINES, "winnow_window": WINNOW_WINDOW, "hash": f"{FINGERPRINT_ALGO} hex prefix {HASH_HEX}",
            "normalization": NORMALIZATION}


def load_fingerprints(path: str | Path) -> set[str]:
    doc = json.loads(Path(path).read_text())
    spec = fingerprint_spec()
    if any(doc.get(k) != v for k, v in spec.items()):
        raise ValueError(f"fingerprint fixture {path} was built with different parameters than this module ({spec})")
    return set(doc["fingerprints"])


def copyleft_findings(paths: Iterable[str | Path], fingerprints: set[str] | None = None,
                      marker_allowed: Iterable[str | Path] = ()) -> list[dict]:
    """License markers and fingerprint matches in code files. Empty list: the gate passes. Files in `marker_allowed` (license
    detectors that hold the titles as data) are exempt from the marker check only, never from the fingerprint check."""
    allowed = {Path(a).resolve() for a in marker_allowed}
    found = []
    for p in paths:
        p = Path(p)
        if p.suffix not in CODE_SUFFIXES or not p.is_file():
            continue
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        if p.resolve() not in allowed:
            low = text.lower()
            for m in _MARKERS:
                if m in low:
                    found.append({"path": str(p), "kind": "license_marker", "match": m})
        if fingerprints:
            hits = sorted(set(shingle_hashes(text)) & fingerprints)
            if hits:
                found.append({"path": str(p), "kind": "fingerprint", "match": hits[:5], "count": len(hits)})
    return found


# ---------------------------------------------------------------- bake-off labels stay out (PI-D-034, skeptic m5)
BAKEOFF_ONLY = "BAKEOFF_ONLY"
BAKEOFF_DATA_DIR = "audits/predictive-intelligence/phase_04/adoption/data"


def refuse_bakeoff_labels(rows: Iterable[dict] = (), path: str | Path | None = None) -> None:
    """Raise if a label set comes from the Phase 04 bake-off: any row marked BAKEOFF_ONLY, or a file under its data folder.
    Phase 06 and later call this on every label source they load; the bake-off labels are not Phase 06 labels."""
    if path is not None and BAKEOFF_DATA_DIR in Path(path).resolve().as_posix():
        raise ValueError(f"{path}: Phase 04 bake-off data is not a label source (PI-D-034)")
    for i, r in enumerate(rows):
        if isinstance(r, dict) and r.get("use") == BAKEOFF_ONLY:
            raise ValueError(f"row {i} is marked BAKEOFF_ONLY: not a label source (PI-D-034)")
