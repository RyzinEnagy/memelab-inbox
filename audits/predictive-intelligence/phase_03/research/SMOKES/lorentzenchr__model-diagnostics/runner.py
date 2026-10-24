"""Run one smoke command, capture combined output, exit code, wall time and peak child RSS.
Usage: python3 runner.py OUTFILE [--online] -- cmd args...
Default runs the command inside `unshare -n` (no network namespace), so any network call fails.
"""
import datetime
import os
import resource
import subprocess
import sys
import time

out = sys.argv[1]
rest = sys.argv[2:]
online = False
if rest and rest[0] == "--online":
    online = True
    rest = rest[1:]
assert rest[0] == "--"
cmd = rest[1:]
full = cmd if online else ["unshare", "-n", "--"] + cmd
env = dict(os.environ)
env.setdefault("MPLCONFIGDIR", "/tmp/claude-0/-home-claude/6c3ea1ef-d097-5873-a280-98af7bc5c45c/scratchpad/r2/mpl")
env["PYTHONHASHSEED"] = "0"
start = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
t0 = time.perf_counter()
proc = subprocess.run(full, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                      cwd="/tmp/claude-0/-home-claude/6c3ea1ef-d097-5873-a280-98af7bc5c45c/scratchpad/r2")
wall = time.perf_counter() - t0
rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024.0
with open(out, "w") as fh:
    fh.write(f"# command: {' '.join(full)}\n")
    fh.write(f"# started_utc: {start}\n")
    fh.write(f"# network: {'ON' if online else 'OFF (unshare -n, no network namespace)'}\n")
    fh.write(proc.stdout.decode("utf-8", "replace"))
    fh.write(f"\n# exit_code: {proc.returncode}\n# wall_s: {wall:.2f}\n# peak_child_rss_mb: {rss:.1f}\n")
print(f"{out}: exit={proc.returncode} wall={wall:.2f}s rss={rss:.1f}MB")
sys.exit(proc.returncode)
