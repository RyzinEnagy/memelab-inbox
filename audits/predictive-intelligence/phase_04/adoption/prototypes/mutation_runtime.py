"""Phase 04 mutation check for tests/test_predictive_runtime.py: each mutation of memelab/predictive/runtime.py must make the test
file fail. Works on a temporary copy of the package, the test file and its fixtures; the repository is never modified.

    python mutation_runtime.py OUT.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]

MUTATIONS = [
    ("P30 reads a key from the environment",
     'sect = ((config or {}).get(C.FLAG_SECTION) or {}).get("behavioral") or {}',
     'import os\n    _k = os.environ.get("ZEP_API_KEY")\n    sect = ((config or {}).get(C.FLAG_SECTION) or {}).get("behavioral") or {}'),
    ("P30 silent success accepted (exit 0 without LLM actions)",
     'if not isinstance(run, dict) or int(run.get("llm_actions") or 0) <= 0:',
     'if not isinstance(run, dict):'),
    ("P30 approval read loosely (any truthy value)",
     'if sect.get("approved") is not True:', 'if not sect.get("approved"):'),
    ("unexpected exceptions propagate to discovery",
     '    except Exception as e:  # noqa: BLE001  (a visible abstention',
     '    except ZeroDivisionError as e:  # noqa: BLE001  (a visible abstention'),
    ("network failure no longer abstains",
     'NETWORK_UNAVAILABLE: "SOURCE_STALE", CIRCUIT_OPEN', 'NETWORK_UNAVAILABLE: None, CIRCUIT_OPEN'),
    ("breaker never opens",
     'if self.failures >= self.breaker:', 'if False and self.failures >= self.breaker:'),
    ("no pacing between calls",
     '            if wait > 0:\n                self.sleep(wait)', '            if False:\n                self.sleep(wait)'),
    ("cost cap ignored",
     'if self.cost_per_call and self.cost + self.cost_per_call > self.max_cost:', 'if False:'),
    ("P32 lock without hashes accepted",
     '        if not _HASH.search(e):\n            problems.append', '        if False:\n            problems.append'),
    ("P32 alternate index accepted",
     '_BANNED_OPTIONS = ("--index-url", "-i ", "--extra-index-url",', '_BANNED_OPTIONS = ("-i ",'),
    ("P32 sdist accepted when its hash matches",
     'if not p.name.endswith(".whl"):', 'if p.name.endswith(".exe"):'),
    ("P31 license markers ignored",
     '        for m in _MARKERS:\n            if m in low:', '        for m in _MARKERS:\n            if False:'),
    ("P31 fingerprints never compared",
     'hits = sorted(set(shingle_hashes(text)) & fingerprints)', 'hits = []'),
    ("P34 importable backtest reported as not available",
     'return _state("backtest", C.backtest_status(installed))', 'return _state("backtest", C.BACKTEST_NOT_AVAILABLE)'),
    ("dependency probe imports the module",
     'found = importlib.util.find_spec(module) is not None', 'found = __import__(module) is not None'),
    ("third-party import added to the runtime",
     'from . import contract as C', 'from . import contract as C\nimport numpy as _np  # noqa: F401'),
    ("weights accepted without the hash",
     'return _state(f"weights:{p.name}", AVAILABLE if h == expected_sha256 else MODEL_HASH_MISMATCH, h[:12])',
     'return _state(f"weights:{p.name}", AVAILABLE, h[:12])'),
]


def run(tmp: Path) -> tuple[int, str]:
    p = subprocess.run([sys.executable, "-B", "-m", "pytest", "tests/test_predictive_runtime.py", "-q", "-p", "no:cacheprovider", "-x"],
                       cwd=tmp, capture_output=True, text=True, timeout=600)
    return p.returncode, (p.stdout.strip().splitlines() or [""])[-1]


def main(out: str) -> None:
    res = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        shutil.copytree(REPO / "memelab", tmp / "memelab", ignore=shutil.ignore_patterns("__pycache__"))
        (tmp / "tests" / "fixtures").mkdir(parents=True)
        shutil.copy(REPO / "tests/test_predictive_runtime.py", tmp / "tests/")
        shutil.copytree(REPO / "tests/fixtures/predictive", tmp / "tests/fixtures/predictive")
        (tmp / "docs/predictive-intelligence/locks").mkdir(parents=True)
        shutil.copy(REPO / "docs/predictive-intelligence/locks/research-py313.txt", tmp / "docs/predictive-intelligence/locks/")
        for r in ("tools", "bridge", "skills"):
            if (REPO / r).exists():
                shutil.copytree(REPO / r, tmp / r, ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
        target = tmp / "memelab/predictive/runtime.py"
        original = target.read_text()
        code, line = run(tmp)
        res.append({"mutation": "none (baseline)", "exit": code, "result": line, "caught": None})
        for name, old, new in MUTATIONS:
            assert original.count(old) == 1, f"mutation anchor not unique or missing: {name}"
            target.write_text(original.replace(old, new))
            code, line = run(tmp)
            res.append({"mutation": name, "exit": code, "result": line, "caught": code != 0})
        target.write_text(original)
    summary = {"baseline_exit": res[0]["exit"], "mutations": len(MUTATIONS), "caught": sum(1 for r in res[1:] if r["caught"]),
               "results": res}
    Path(out).write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: summary[k] for k in ("baseline_exit", "mutations", "caught")}))
    for r in res:
        print(r["caught"], r["exit"], r["mutation"], "|", r["result"])


if __name__ == "__main__":
    main(sys.argv[1])
