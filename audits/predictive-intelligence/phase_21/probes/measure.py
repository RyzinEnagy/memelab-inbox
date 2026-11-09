"""Phase 21: run one command, append one JSON line with its name, exit code, wall seconds and the peak resident memory of its
process tree (getrusage of the children, in MiB) to a log. Stdout and stderr of the command go to the files given.

    python -B measure.py LOG NAME STDOUT_FILE -- CMD [ARG...]
"""
from __future__ import annotations

import json
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone


def main() -> int:
    log, name, out = sys.argv[1], sys.argv[2], sys.argv[3]
    cmd = sys.argv[sys.argv.index("--") + 1:]
    t0 = time.time()
    with open(out, "w") as f:
        p = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    dt = time.time() - t0
    rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024.0
    rec = {"step": name, "exit": p.returncode, "seconds": round(dt, 1), "peak_rss_mib_children": round(rss, 1),
           "start_utc": datetime.fromtimestamp(t0, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    with open(log, "a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
    print(json.dumps(rec, sort_keys=True))
    return p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
