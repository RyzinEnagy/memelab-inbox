"""CP17-1 (PI-D-096, skeptic m4): the skeptic's isolation mutations of ea73cfb (skeptic/mutate_isolation.py), re-run against
the repaired isolation tests. Each mutation is applied to a temporary copy of the tracked memelab and tests trees (the checkout
is never edited) and the isolation test files run. A mutation that adds a dynamic import from a concatenated string inside a
function nobody calls is the one gap no static scan closes; it is listed as KNOWN_LIMIT, not counted as caught.

    python -B rp2_isolation_mutations.py OUT.json
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
A = "audits/predictive-intelligence"
FILES = ["tests/test_predictive_contract.py", "tests/test_predictive_registry.py", "tests/test_predictive_calibration.py",
         "tests/test_predictive_onchain.py",
         "tests/test_predictive_integration.py::test_rp2_m4_no_lab_module_names_the_cli_helpers_and_no_lab_import_loads_the_package"]
KNOWN_LIMIT = {"pipeline_concat_string"}


def append_fn(path: str, body: str) -> tuple[str, str]:
    return path, "\n\ndef _skeptic_probe():\n" + "".join("    " + ln + "\n" for ln in body.splitlines())


M = {
    "report_lazy_integration": append_fn("memelab/report.py", "from .predictive import integration\nreturn integration"),
    "pipeline_import_module_string": append_fn("memelab/pipeline.py", "import importlib\nreturn importlib.import_module('memelab.predictive.integration')"),
    "pipeline_concat_string": append_fn("memelab/pipeline.py", "import importlib\nreturn importlib.import_module('memelab.predic' + 'tive.integration')"),
    "farm_imports_cli_helper": append_fn("memelab/farm.py", "from .cli import _predictive_section\nreturn _predictive_section"),
    "labels_from_dot_import_stats_registry": append_fn("memelab/predictive/labels.py", "from . import stats, registry\nreturn registry"),
    "labels_from_dot_import_registry_alias": append_fn("memelab/predictive/labels.py", "from . import registry as RR\nreturn RR"),
    "features_from_dot_import_onchain": append_fn("memelab/predictive/features.py", "from . import onchain\nreturn onchain"),
    "features_from_onchain_import_name": append_fn("memelab/predictive/features.py", "from .onchain import decision_support\nreturn decision_support"),
    "stats_from_dot_import_abstention": append_fn("memelab/predictive/stats.py", "from . import abstention\nreturn abstention"),
    "stats_from_dot_import_integration": append_fn("memelab/predictive/stats.py", "from . import integration\nreturn integration"),
    "analog_also_depth_adapter": append_fn("memelab/predictive/analog.py", "from . import depth_adapter\nreturn depth_adapter"),
    "social_imports_predictive": append_fn("memelab/social/research_store.py", "from ..predictive import contract\nreturn contract"),
    "cli_helper_imports_registry_too": ("memelab/cli.py", None),
    "cli_module_level_import": ("memelab/cli.py", None),
    "module_level_import_loads_the_package": append_fn("memelab/report.py", "return None"),
}


def apply(root: Path, name: str) -> None:
    f, body = M[name]
    p = root / f
    s = p.read_text()
    if name == "cli_helper_imports_registry_too":
        a = "        from .predictive import integration\n    except Exception as e:\n        return f\"predictive: not available"
        assert s.count(a) == 1
        p.write_text(s.replace(a, a.replace("import integration", "import integration, registry")))
    elif name == "cli_module_level_import":
        a = "\ndef _predictive_section"
        p.write_text(s.replace(a, "\ntry:\n    from .predictive import integration as _PI\nexcept Exception:\n    _PI = None\n\n" + a, 1))
    elif name == "module_level_import_loads_the_package":   # a module-level dynamic import from a built string, at import time
        p.write_text(s + "\nimport importlib as _il\n_PRED = _il.import_module('memelab.predic' + 'tive.contract')\n")
    else:
        p.write_text(s + body)


def main(out: str) -> int:
    res = {}
    with tempfile.TemporaryDirectory(prefix="p17_iso_") as td:
        root = Path(td)
        tracked = subprocess.run(["git", "-C", str(REPO), "ls-files", "memelab", "tests", "docs", A], capture_output=True, text=True,
                                 check=True).stdout.splitlines()
        for f in tracked:                       # working-tree copies of tracked files; the sealed folder is never copied or read
            if f.startswith(f"{A}/phase_06/sealed/") or not (REPO / f).is_file():
                continue
            (root / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / f, root / f)
        cmd = [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *FILES]
        env = {"MEMELAB_DB": str(root / "mut.sqlite"), "PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(root)}
        base = subprocess.run(cmd, cwd=root, capture_output=True, text=True, env=env)
        if base.returncode != 0:
            raise SystemExit("baseline fails: " + base.stdout[-3000:])
        for name in M:
            f = M[name][0]
            orig = (root / f).read_text()
            apply(root, name)
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, env=env, timeout=900)
            fails = [ln.split(" ")[1] for ln in r.stdout.splitlines() if ln.startswith("FAILED")]
            res[name] = {"file": f, "caught": r.returncode != 0, "known_limit": name in KNOWN_LIMIT,
                         "first_failure": fails[0] if fails else (r.stdout.strip().splitlines() or [""])[-1]}
            (root / f).write_text(orig)
            print(name, res[name]["caught"], flush=True)
    surv = [k for k, v in res.items() if not v["caught"] and not v["known_limit"]]
    rep = {"mutations": len(res), "caught": sum(v["caught"] for v in res.values()), "survivors": surv,
           "known_limit_survivors": [k for k, v in res.items() if not v["caught"] and v["known_limit"]], "results": res,
           "known_limit_note": "an importlib call on a string built at run time inside a function no test calls is invisible to the AST "
                               "and constant scans; the same string at module level is caught by the import-every-module subprocess test"}
    Path(out).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("mutations", "caught", "survivors", "known_limit_survivors")}))
    return 0 if not surv else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
