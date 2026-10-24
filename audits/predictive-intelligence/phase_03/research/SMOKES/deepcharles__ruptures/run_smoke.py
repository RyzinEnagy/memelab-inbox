"""Run one smoke script with no network (unshare -n), record command, exit code, wall time, peak RSS (resource).
Usage: python3 run_smoke.py OUT_DIR NAME PYTHON SCRIPT [args...]"""
import os, sys, subprocess, time, resource, json, datetime, shutil
out_dir, name, py, script, *args = sys.argv[1:]
os.makedirs(out_dir, exist_ok=True)
cmd = ["unshare", "-n", py, "-I", "-B", script, *args]
env = dict(os.environ)
env["NUMBA_CACHE_DIR"] = os.path.join(out_dir, ".numba_cache_unused")
env.pop("PYTHONPATH", None)
start = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
t0 = time.perf_counter()
with open(os.path.join(out_dir, name + ".out.txt"), "w") as fh:
    p = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, env=env, cwd=out_dir)
wall = time.perf_counter() - t0
ru = resource.getrusage(resource.RUSAGE_CHILDREN)
meta = {"name": name, "command": " ".join(cmd), "cwd": out_dir, "start_utc": start, "exit_code": p.returncode,
        "wall_s": round(wall, 3), "peak_rss_mb": round(ru.ru_maxrss / 1024, 1), "user_cpu_s": round(ru.ru_utime, 2),
        "network": "none (unshare -n)"}
open(os.path.join(out_dir, name + ".meta.json"), "w").write(json.dumps(meta, indent=1))
shutil.rmtree(env["NUMBA_CACHE_DIR"], ignore_errors=True)
print(json.dumps(meta))
