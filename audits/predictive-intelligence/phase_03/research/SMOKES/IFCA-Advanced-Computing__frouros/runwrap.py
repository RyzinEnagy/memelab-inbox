"""Run one smoke command, capture output, exit code, wall time and peak RSS of the child.

Usage: python3 -I runwrap.py OUT_PREFIX [--offline] [--strace] -- CMD ARGS...
  --offline  run the command inside a fresh network namespace (unshare -n): no route, no DNS
  --strace   wrap with strace -f -e trace=connect,sendto and save OUT_PREFIX.connect.txt
Writes OUT_PREFIX.out.txt (stdout+stderr) and OUT_PREFIX.meta.json.
"""
import json
import os
import re
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone


def main():
    argv = sys.argv[1:]
    out = argv[0]
    sep = argv.index("--")
    flags = argv[1:sep]
    cmd = argv[sep + 1:]
    full = list(cmd)
    trace_path = None
    if "--strace" in flags:
        trace_path = out + ".connect.txt"
        full = ["strace", "-f", "-qq", "-e", "trace=connect,sendto", "-o", trace_path] + full
    if "--offline" in flags:
        full = ["unshare", "-n"] + full
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    t0 = time.perf_counter()
    with open(out + ".out.txt", "w") as fh:
        proc = subprocess.run(full, stdout=fh, stderr=subprocess.STDOUT)
    wall = time.perf_counter() - t0
    ru = resource.getrusage(resource.RUSAGE_CHILDREN)
    meta = {
        "command": cmd,
        "wrapped_command": full,
        "started_utc": started,
        "exit_code": proc.returncode,
        "wall_s": round(wall, 3),
        "peak_rss_kb_children": ru.ru_maxrss,
        "env_switches": {k: os.environ[k] for k in sorted(os.environ) if k in (
            "DO_NOT_TRACK", "EVIDENTLY_DISABLE_TELEMETRY", "NML_DISABLE_USAGE_LOGGING", "MLFLOW_DISABLE_TELEMETRY",
            "SKORE_DISABLE_TELEMETRY", "MLFLOW_TRACKING_URI", "NETGUARD")},
        "offline_netns": "--offline" in flags,
    }
    if trace_path and os.path.exists(trace_path):
        lines = open(trace_path, errors="replace").read().splitlines()
        inet = [ln for ln in lines if "AF_INET" in ln]
        targets = {}
        for ln in inet:
            m = re.search(r'sin6?_port=htons\((\d+)\).*?(?:inet_addr\("([^"]+)"\)|inet_pton\(AF_INET6, "([^"]+)")', ln)
            if m:
                key = (m.group(2) or m.group(3)) + ":" + m.group(1)
                targets[key] = targets.get(key, 0) + 1
        meta["strace_inet_connect_lines"] = len(inet)
        meta["strace_inet_targets"] = targets
        meta["strace_unix_connect_lines"] = sum(1 for ln in lines if "AF_UNIX" in ln)
    with open(out + ".meta.json", "w") as fh:
        json.dump(meta, fh, indent=1)
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
