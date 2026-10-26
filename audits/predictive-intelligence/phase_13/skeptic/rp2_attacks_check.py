"""Repair pass 2 check: rerun the skeptic's publication attacks (p13_publication_attacks.py) and CX-S13 script against the
repaired code. The attack script calls the layer without a config, so with the flag OFF its legitimate baseline no longer
publishes (M1 repaired). To test every other attack on its own merits, this wrapper also runs it with `contract.enabled`
replaced by a stub that returns True (the flag ON), and reports which attacks still publish.

    python -B rp2_attacks_check.py REPO OUT.json
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    repo, outp = Path(sys.argv[1]), Path(sys.argv[2])
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(repo))
    sys.path.insert(0, str(repo / "tests"))
    from memelab.predictive import contract as C
    res = {"flag_in_this_checkout": C.enabled()}
    a = load("p13_attacks", here / "p13_publication_attacks.py")
    td = Path(tempfile.mkdtemp())
    try:
        a.sys.argv = ["x", str(repo), str(td / "off.json")]
        a.main()
        res["flag_off_run"] = json.loads((td / "off.json").read_text())
    except Exception as e:                                 # the baseline cannot publish with the flag OFF
        res["flag_off_run"] = f"stops: {type(e).__name__}: {e} (the legitimate fixture no longer publishes with the flag OFF)"
    C.enabled = lambda config_path=None: True              # flag ON for every remaining attack
    a.sys.argv = ["x", str(repo), str(td / "on.json")]
    a.main()
    on = json.loads((td / "on.json").read_text())
    res["flag_on_run"] = on
    res["published_with_flag_on"] = sorted(k for k, v in on.items() if isinstance(v, dict) and v.get("PUBLISHED") and k != "baseline_legit_fixture"
                                           and not k.startswith("A1"))
    x = load("p13_cx", here / "p13_cx_s13_flat_evidence.py")
    x.sys.argv = ["x", str(repo), str(td / "cx.json")]
    try:
        x.main()
        res["cx_s13"] = json.loads((td / "cx.json").read_text())
    except Exception as e:
        res["cx_s13"] = f"stops: {type(e).__name__}: {e}"
    outp.write_text(json.dumps(res, indent=1, sort_keys=True, default=str) + "\n")
    print(json.dumps({"published_with_flag_on": res["published_with_flag_on"], "flag_off": str(res["flag_off_run"])[:120]}))


if __name__ == "__main__":
    main()
