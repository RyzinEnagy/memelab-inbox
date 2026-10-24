"""Phase 04 measurement harness: run one Python snippet or script in a fresh process, offline, and record what it cost.

For every run: exit code, wall seconds, CPU seconds (user + system of the child), peak RSS of the child (MB), network attempts
counted by a Python audit hook (socket.connect, socket.getaddrinfo, socket.gethostbyname, urllib.Request, http.client.connect)
and the sha256 of the child's stdout (determinism). The child runs inside `unshare -n` (no network namespace interface but
loopback down), so a library that needs the network fails visibly instead of silently.

    python measure.py VENV_PYTHON OUT.json --label NAME --import "sklearn.linear_model" [--repeat 5]
    python measure.py VENV_PYTHON OUT.json --label NAME --script path/to/run.py -- args...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BOOT = r'''
import sys, os, json, time, runpy
_t0 = time.perf_counter()
_events = []
_NET = ("socket.connect", "socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyname_ex", "urllib.Request",
        "http.client.connect", "socket.sendto", "socket.bind")
def _hook(ev, args):
    if ev in _NET:
        _events.append([ev, repr(args)[:200]])
sys.addaudithook(_hook)
_side = os.environ["P04_SIDE"]
_mode, _arg = sys.argv[1], sys.argv[2]
try:
    if _mode == "import":
        import importlib
        for m in _arg.split(","):
            importlib.import_module(m.strip())
        print(json.dumps({"imported": _arg, "seconds": time.perf_counter() - _t0}))
    else:
        sys.argv = [_arg] + sys.argv[3:]
        runpy.run_path(_arg, run_name="__main__")
finally:
    import resource as _r
    with open(_side, "w") as _fh:
        json.dump({"net_events": _events, "wall_in_child": time.perf_counter() - _t0,
                   "child_self_maxrss_mb": _r.getrusage(_r.RUSAGE_SELF).ru_maxrss / 1024.0}, _fh)
'''


def run_once(py: str, mode: str, arg: str, extra: list[str], offline: bool, env_extra: dict) -> dict:
    with tempfile.TemporaryDirectory() as td:
        side = os.path.join(td, "side.json")
        boot = os.path.join(td, "boot.py")
        Path(boot).write_text(BOOT)
        env = dict(os.environ, P04_SIDE=side, PYTHONHASHSEED="0", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                   OPENBLAS_NUM_THREADS="1", **env_extra)
        cmd = [py, "-I", boot, mode, arg, *extra]
        if offline:
            cmd = ["unshare", "-n", *cmd]
        r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
        t0 = time.perf_counter()
        p = subprocess.run(cmd, capture_output=True, env=env, timeout=3600)
        wall = time.perf_counter() - t0
        r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        sidej = json.loads(Path(side).read_text()) if os.path.exists(side) else {}
    return {"exit": p.returncode, "wall_s": round(wall, 4), "cpu_s": round((r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime), 4),
            "peak_rss_mb": round(sidej.get("child_self_maxrss_mb", r1.ru_maxrss / 1024.0), 1),
            "net_events": len(sidej.get("net_events", [])), "net_examples": sidej.get("net_events", [])[:3],
            "stdout_sha256": hashlib.sha256(p.stdout).hexdigest(), "stdout_tail": p.stdout.decode(errors="replace")[-400:],
            "stderr_tail": p.stderr.decode(errors="replace")[-400:]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("py")
    ap.add_argument("out")
    ap.add_argument("--label", required=True)
    ap.add_argument("--import", dest="imp")
    ap.add_argument("--script")
    ap.add_argument("--repeat", type=int, default=2)
    ap.add_argument("--online", action="store_true")
    ap.add_argument("--env", action="append", default=[])
    ap.add_argument("rest", nargs="*")
    a = ap.parse_args()
    env_extra = dict(e.split("=", 1) for e in a.env)
    mode, arg = ("import", a.imp) if a.imp else ("script", a.script)
    runs = [run_once(a.py, mode, arg, a.rest, not a.online, env_extra) for _ in range(a.repeat)]
    walls = [r["wall_s"] for r in runs]
    res = {"label": a.label, "python": a.py, "mode": mode, "target": arg, "args": a.rest, "offline_unshare_n": not a.online,
           "env_extra": env_extra, "repeat": a.repeat, "all_exit_0": all(r["exit"] == 0 for r in runs),
           "wall_median_s": round(statistics.median(walls), 4), "wall_min_s": min(walls), "wall_max_s": max(walls),
           "cpu_median_s": round(statistics.median(r["cpu_s"] for r in runs), 4),
           "peak_rss_max_mb": max(r["peak_rss_mb"] for r in runs), "net_events_total": sum(r["net_events"] for r in runs),
           "deterministic_stdout": len({r["stdout_sha256"] for r in runs}) == 1, "runs": runs}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("label", "all_exit_0", "wall_median_s", "cpu_median_s", "peak_rss_max_mb",
                                           "net_events_total", "deterministic_stdout")}))


if __name__ == "__main__":
    main()
