"""Phase 04 mutation check for tests/test_predictive_runtime.py: each mutation of memelab/predictive/runtime.py (or of the flag
reader in contract.py) must make the test file fail. Works on a temporary copy of the working tree (without .git); the repository
is never modified. The repair pass added the skeptic's six surviving mutations (m2) and one or more mutations for every repair.

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
RT, CT = "memelab/predictive/runtime.py", "memelab/predictive/contract.py"

MUTATIONS = [
    # P30 and the behavioral approval rule
    (RT, "P30 reads a key from the environment",
     'if _section(config, C.FLAG_SECTION, "behavioral").get("approved") is not True:',
     'import os\n    _k = os.environ.get("ZEP_API_KEY")\n    if _section(config, C.FLAG_SECTION, "behavioral").get("approved") is not True:'),
    (RT, "P30 silent success accepted (exit 0 without LLM actions)", 'if _llm_action_count(run) <= 0:', 'if run is None:'),
    (RT, "P30 approval read loosely (any truthy value)",
     'if _section(config, C.FLAG_SECTION, "behavioral").get("approved") is not True:',
     'if not _section(config, C.FLAG_SECTION, "behavioral").get("approved"):'),
    (RT, "M2 llm_actions coerced with int()", 'return n if type(n) is int and n > 0 else 0', 'return int(n) if n else 0'),
    (RT, "M2 llm_actions accepts bool and str", 'return n if type(n) is int and n > 0 else 0',
     'return int(n) if isinstance(n, (int, str)) and str(n).isdigit() and int(n) > 0 else 0'),
    (RT, "M2 config sections not type-checked", '        if not isinstance(cur, dict):\n            return {}',
     '        if cur is None:\n            return {}'),
    # guarded
    (RT, "M2 narrowed catch (skeptic's surviving mutant)", '    except BaseException as e:  # noqa: BLE001',
     '    except (ValueError, RuntimeError, MemoryError) as e:  # noqa: BLE001'),
    (RT, "M2 catch only Exception (SystemExit escapes)", '    except BaseException as e:  # noqa: BLE001', '    except Exception as e:  # noqa: BLE001'),
    (RT, "M2 SystemExit deliberately not contained", 'NOT_CONTAINED = (KeyboardInterrupt, GeneratorExit)',
     'NOT_CONTAINED = (KeyboardInterrupt, GeneratorExit, SystemExit)'),
    (RT, "KeyboardInterrupt swallowed", 'NOT_CONTAINED = (KeyboardInterrupt, GeneratorExit)', 'NOT_CONTAINED = ()'),
    (RT, "network failure no longer abstains", 'NETWORK_UNAVAILABLE: "SOURCE_STALE", BAD_RESPONSE',
     'NETWORK_UNAVAILABLE: None, BAD_RESPONSE'),
    # CallGuard
    (RT, "breaker never opens", 'if self.failures >= self.breaker:', 'if False and self.failures >= self.breaker:'),
    (RT, "breaker counts only network failures (skeptic's surviving mutant)",
     'self.failures = 0 if st["state"] == AVAILABLE else self.failures + 1',
     'self.failures = self.failures + 1 if st["state"] == NETWORK_UNAVAILABLE else 0'),
    (RT, "call and cost caps no longer abstain (skeptic's surviving mutant)",
     'CALL_CAP_REACHED: "SOURCE_STALE",\n    COST_CAP_REACHED: "SOURCE_STALE",', 'CALL_CAP_REACHED: None,\n    COST_CAP_REACHED: None,'),
    (RT, "no pacing between calls", '            if wait > 0:\n                self.sleep(wait)', '            if False:\n                self.sleep(wait)'),
    (RT, "cost cap ignored", 'if self.cost_per_call and self.cost + self.cost_per_call > self.max_cost:', 'if False:'),
    (RT, "m6 NaN cost no longer fails closed", 'self.cost_ok = _finite_nonneg(max_cost) and _finite_nonneg(cost_per_call)',
     'self.cost_ok = True'),
    (RT, "m6 returned error responses ignored", 'if st["state"] == AVAILABLE and self.is_failure is not None:', 'if False:'),
    (RT, "m6 invalid pace accepted", '        if not (_finite_nonneg(per_min) and per_min > 0', '        if False and not (_finite_nonneg(per_min) and per_min > 0'),
    # install guard (M1)
    (RT, "M1 only the first option after a requirement is checked", 'bad = [t for t in opts if not _HASH_TOKEN.fullmatch(t)]',
     'bad = [t for t in opts[:1] if not _HASH_TOKEN.fullmatch(t)]'),
    (RT, "M1 sha512 and other hash algorithms accepted", '_HASH_TOKEN = re.compile(r"--hash=sha256:([0-9a-f]{64})")',
     '_HASH_TOKEN = re.compile(r"--hash=sha(?:256|384|512):([0-9a-f]{64,128})")'),
    (RT, "M1 marker content not checked", 'if sep and (not marker.strip()', 'if False and (not marker.strip()'),
    (RT, "M1 known wheel digests not enforced", '                if h not in known:', '                if False:'),
    (RT, "M1 install_argv skips the guard", 'probs = check_lock(Path(lock_path).read_text(), wheel_hashes)', 'probs = []'),
    (RT, "banned options only at line start (skeptic's surviving mutant, new parser)", '        if k == 0:\n            problems.append',
     '        if False:\n            problems.append'),
    (RT, "P32 sdist accepted when its hash matches", 'if not p.name.endswith(".whl"):', 'if p.name.endswith(".exe"):'),
    # copyleft gate (P31)
    (RT, "P31 license markers ignored", '            for m in _MARKERS:\n                if m in low:', '            for m in _MARKERS:\n                if False:'),
    (RT, "P31 fingerprints never compared", 'hits = sorted(set(shingle_hashes(text)) & fingerprints)', 'hits = []'),
    (RT, "P31 shingle hash computed with sha1 (skeptic's surviving mutant)",
     'hashlib.new(FINGERPRINT_ALGO, "\\n".join(ls[i:i + SHINGLE_LINES]).encode())', 'hashlib.new("sha1", "\\n".join(ls[i:i + SHINGLE_LINES]).encode())'),
    (RT, "P31 algorithm constant changed", 'FINGERPRINT_ALGO = "sha256"', 'FINGERPRINT_ALGO = "sha1"'),
    (RT, "P31 lines lower-cased before hashing (skeptic's surviving mutant)", 's = " ".join(ln.split())', 's = " ".join(ln.lower().split())'),
    (RT, "P31 marker exemption also skips fingerprints", '        if fingerprints:\n            hits', '        if fingerprints and p.resolve() not in allowed:\n            hits'),
    (RT, "P31 fixture parameters not checked", '    if any(doc.get(k) != v for k, v in spec.items()):', '    if False:'),
    # other states
    (RT, "P34 importable backtest reported as not available", 'return _state("backtest", C.backtest_status(installed))',
     'return _state("backtest", C.BACKTEST_NOT_AVAILABLE)'),
    (RT, "dependency probe imports the module", 'found = importlib.util.find_spec(module) is not None', 'found = __import__(module) is not None'),
    (RT, "m6 dotted names probed (imports the parent)", 'if not isinstance(module, str) or not module.isidentifier():',
     'if not isinstance(module, str) or not module:'),
    (RT, "third-party import added to the runtime", 'from . import contract as C', 'from . import contract as C\nimport numpy as _np  # noqa: F401'),
    (RT, "weights accepted without the hash",
     'return _state(f"weights:{p.name}", AVAILABLE if h == expected_sha256 else MODEL_HASH_MISMATCH, h[:12])',
     'return _state(f"weights:{p.name}", AVAILABLE, h[:12])'),
    (RT, "m5 bake-off rows accepted", '        if isinstance(r, dict) and r.get("use") == BAKEOFF_ONLY:', '        if False:'),
    (RT, "m5 bake-off path accepted", '    if path is not None and BAKEOFF_DATA_DIR in', '    if False and BAKEOFF_DATA_DIR in'),
    # the flag reader (contract.enabled)
    (CT, "M2 flag reader crashes on malformed config (old code)",
     '    sect = cfg.get(FLAG_SECTION) if isinstance(cfg, dict) else None     # malformed config means OFF (Phase 04 skeptic M2)\n'
     '    return isinstance(sect, dict) and sect.get("enabled") is True',
     '    return (cfg.get(FLAG_SECTION) or {}).get("enabled") is True'),
]


def run(tmp: Path) -> tuple[int, str]:
    p = subprocess.run([sys.executable, "-B", "-m", "pytest", "tests/test_predictive_runtime.py", "-q", "-p", "no:cacheprovider", "-x"],
                       cwd=tmp, capture_output=True, text=True, timeout=900)
    return p.returncode, (p.stdout.strip().splitlines() or [""])[-1]


def main(out: str) -> None:
    res = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "repo"
        shutil.copytree(REPO, tmp, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.sqlite-shm", "*.sqlite-wal"))
        originals = {f: (tmp / f).read_text() for f in (RT, CT)}
        code, line = run(tmp)
        res.append({"mutation": "none (baseline)", "exit": code, "result": line, "caught": None})
        for target, name, old, new in MUTATIONS:
            src = originals[target]
            assert src.count(old) == 1, f"mutation anchor not unique or missing: {name}"
            (tmp / target).write_text(src.replace(old, new))
            code, line = run(tmp)
            (tmp / target).write_text(src)
            res.append({"mutation": name, "file": target, "exit": code, "result": line, "caught": code != 0})
    summary = {"baseline_exit": res[0]["exit"], "mutations": len(MUTATIONS), "caught": sum(1 for r in res[1:] if r["caught"]),
               "survived": [r["mutation"] for r in res[1:] if not r["caught"]], "results": res}
    Path(out).write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: summary[k] for k in ("baseline_exit", "mutations", "caught", "survived")}))


if __name__ == "__main__":
    main(sys.argv[1])
