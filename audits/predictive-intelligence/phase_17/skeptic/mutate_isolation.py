"""Isolation-test mutation probe: each mutation applied to a fresh checkout, the four amended test files run under unshare -n."""
import subprocess, sys, json
from pathlib import Path
R = Path(sys.argv[1])
FILES = ["tests/test_predictive_contract.py", "tests/test_predictive_registry.py", "tests/test_predictive_calibration.py", "tests/test_predictive_onchain.py"]
def append_fn(path, body):
    return (path, "\n\ndef _skeptic_probe():\n" + "".join("    " + l + "\n" for l in body.splitlines()))
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
 "cli_helper_imports_registry_too": None,
 "cli_module_level_import": None,
}
out = {}
for name, m in M.items():
    subprocess.run(["git", "-C", str(R), "checkout", "-q", "--", "."], check=True)
    if name == "cli_helper_imports_registry_too":
        p = R / "memelab/cli.py"; s = p.read_text(); p.write_text(s.replace("        from .predictive import integration\n    except Exception:\n        return None\n    return integration.analyze_line(r)",
                                                                              "        from .predictive import integration, registry\n    except Exception:\n        return None\n    return integration.analyze_line(r)"))
    elif name == "cli_module_level_import":
        p = R / "memelab/cli.py"; s = p.read_text(); p.write_text(s.replace("\ndef _predictive_section", "\ntry:\n    from .predictive import integration as _PI\nexcept Exception:\n    _PI = None\n\n\ndef _predictive_section", 1))
    else:
        p = R / m[0]; p.write_text(p.read_text() + m[1])
    diff = subprocess.run(["git", "-C", str(R), "diff", "--stat"], capture_output=True, text=True).stdout.strip().splitlines()
    r = subprocess.run(["unshare", "-n", sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *FILES], cwd=R, capture_output=True, text=True,
                       env={"MEMELAB_DB": str(R.parent / "mut.sqlite"), "PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": "/root"})
    fails = [l for l in r.stdout.splitlines() if l.startswith("FAILED")]
    out[name] = {"changed": diff[:1], "exit": r.returncode, "caught": r.returncode != 0, "first_failure": fails[:1] or r.stdout.strip().splitlines()[-1:]}
    print(name, out[name]["caught"], out[name]["first_failure"], flush=True)
subprocess.run(["git", "-C", str(R), "checkout", "-q", "--", "."], check=True)
Path(sys.argv[2]).write_text(json.dumps(out, indent=1) + "\n")
