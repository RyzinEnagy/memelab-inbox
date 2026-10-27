"""Phase 20 (G7): run the lab CLI exactly as `python -m memelab ARGS` and, at exit, write the memelab.predictive modules that were
imported to OUTFILE (one JSON list). Used to show that a flag-off run imports nothing of the predictive package.

    python -B cli_import_trace.py OUTFILE ARGS...
"""
import atexit
import json
import os
import runpy
import sys

sys.path.insert(0, os.getcwd())     # the lab checkout the command runs in, as `python -m` would

out = sys.argv[1]
atexit.register(lambda: open(out, "w").write(json.dumps(sorted(m for m in sys.modules if m.startswith("memelab.predictive")))))
sys.argv = ["memelab"] + sys.argv[2:]
runpy.run_module("memelab", run_name="__main__", alter_sys=True)
