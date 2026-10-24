"""Phase 03 lead: answer rubric item R1 (same inputs and seed give identical outputs) uniformly by re-running a
reviewer's own smoke script once more in a scratch copy and comparing its results with the committed reviewer run.

Timing, memory, wall-clock and path fields are removed before comparing (see DROP and the text filter); every other
value must be equal. Runs inside `unshare -n` with the reviewer's venv. Writes nothing into the repository except
the summary file named on the command line.
Usage: python3 repeat_runs.py SCRATCH_DIR OUT_JSON repo [repo ...]
"""
import json, os, re, shutil, subprocess, sys, time

SMK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SMOKES")
V = "/home/claude/pi_research/venvs/%s/bin/python"
CH = os.path.join(SMK, "_challenge", "challenge.csv")
# repo: (script, args, how results are read, committed reference)
JOBS = {
    "statsmodels__statsmodels": ("smoke_statsmodels.py", [CH, "{scratch}/work"], "stdout_results_json", "smoke_output.txt"),
    "online-ml__river": ("smoke_river.py", [], "file_json:smoke_river.result.json", "smoke_river.result.json"),
    "sktime__sktime": ("smoke_sktime.py", [], "file_json:smoke_sktime.result.json", "smoke_sktime.result.json"),
    "deepcharles__ruptures": ("smoke_ruptures.py", [], "file_json:smoke_ruptures.result.json", "smoke_ruptures.result.json"),
    "IFCA-Advanced-Computing__frouros": ("smoke_frouros.py", [], "stdout_result_lines", "smoke_frouros.out.txt"),
    "probabl-ai__skore": ("smoke_skore.py", [], "stdout_result_lines", "smoke_skore.out.txt"),
    "unionai-oss__pandera": ("smoke_pandera.py", [], "stdout_result_lines", "smoke_pandera.out.txt"),
    "scikit-learn-contrib__MAPIE": ("smoke_mapie.py", [], "stdout_text", "raw_smoke_mapie.txt"),
    "baobach__mlfinpy": ("smoke_mlfinpy.py", [], "stdout_text", "raw_smoke_mlfinpy.txt"),
}
DROP = re.compile(r"(^|_)(s|ms|us|sec|secs|seconds|wall|time|times|utc|rss|mb|latency|import|cpu|started|finished|"
                  r"path|paths|file|files|executable|cwd|workdir|dir|tmp|xdg|env|platform|duration|elapsed|"
                  r"per|row|rows_per_s|timings|bytes)($|_)", re.I)
TIMING_WORDS = re.compile(r"(\bms\b|\bus\b|\bs\b(?!\w)|wall|rss|seconds|started_utc|exit_code|peak|/row|per row|"
                          r"[0-9.]+ ?s\b|[0-9.]+ ?ms\b|warning|Warning|^#|^\s+warnings\.warn|elapsed|import \d)", re.I)

def norm(x):
    if isinstance(x, dict):
        return {k: norm(v) for k, v in x.items() if not DROP.search(k)}
    if isinstance(x, list):
        return [norm(v) for v in x]
    if isinstance(x, str):
        return re.sub(r"/(tmp|home)/[^\s'\"]+", "<path>", x)
    if isinstance(x, float):
        return round(x, 12)
    return x

def results_from(mode, text, folder):
    if mode == "stdout_results_json":
        i = text.index("RESULTS_JSON ")
        return norm(json.loads(text[i + 13:].strip().splitlines()[0]))
    if mode.startswith("file_json:"):
        return norm(json.loads(open(os.path.join(folder, mode.split(":", 1)[1])).read().replace("NaN", "null")))
    if mode == "stdout_result_lines":
        out = {}
        for ln in text.splitlines():
            m = re.match(r"RESULT (\S+) (\{.*\})\s*$", ln)
            if m:
                out[m.group(1)] = norm(json.loads(m.group(2).replace("NaN", "null")))
        return out
    lines = [re.split(r"/(?:tmp|home)/", ln)[0] for ln in text.splitlines()]  # a path tail is stderr interleaving
    return [ln for ln in lines if ln.strip() and not TIMING_WORDS.search(ln)]

def leaves(x):
    if isinstance(x, dict):
        return sum(leaves(v) for v in x.values())
    if isinstance(x, list):
        return sum(leaves(v) for v in x) if x and isinstance(x[0], (dict, list)) else len(x)
    return 1

def diff(a, b, p=""):
    if type(a) != type(b):
        return [p]
    if isinstance(a, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            out += diff(a.get(k), b.get(k), p + "." + k) if k in a and k in b else [p + "." + k]
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [p + "[len]"]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, "%s[%d]" % (p, i))
        return out
    return [] if a == b else [p]

def main():
    scratch, out_json, repos = sys.argv[1], sys.argv[2], sys.argv[3:]
    summary = json.load(open(out_json)) if os.path.exists(out_json) else {}
    for repo in repos:
        script, args, mode, ref = JOBS[repo]
        work = os.path.join(scratch, repo)
        shutil.rmtree(work, ignore_errors=True)
        shutil.copytree(os.path.join(SMK, repo), work)
        os.makedirs(os.path.join(work, "work"), exist_ok=True)
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        env.update({"R4_HARNESS": work, "NML_DISABLE_USAGE_LOGGING": "1", "DO_NOT_TRACK": "true", "OMP_NUM_THREADS": "1",
                    "MPLCONFIGDIR": os.path.join(work, "mpl"), "TMPDIR": os.path.join(work, "work"), "SKORE_WORKSPACE": os.path.join(work, "work", "skore")})
        cmd = ["unshare", "-n", V % repo, "-I", os.path.join(work, script)] + [a.format(scratch=work) for a in args]
        t0 = time.time()
        p = subprocess.run(cmd, cwd=os.path.join(work, "work"), env=env, capture_output=True, text=True)
        wall = round(time.time() - t0, 1)
        new = results_from(mode, p.stdout + "\n" + p.stderr if mode == "stdout_text" else p.stdout, work)
        ref_text = open(os.path.join(SMK, repo, ref)).read()
        old = results_from(mode, ref_text, os.path.join(SMK, repo))
        if mode == "stdout_text":
            d = sorted(set(old) ^ set(new))
        else:
            d = diff(old, new)
        summary[repo] = {"command": " ".join(cmd[:4]) + " ...", "exit_code": p.returncode, "wall_s": wall, "compared_against": "SMOKES/%s/%s" % (repo, ref),
                         "identical_after_normalization": not d, "differences": d[:20], "n_differences": len(d),
                         "values_compared": leaves(old)}
        print(repo, p.returncode, wall, "identical" if not d else "DIFF %d %s" % (len(d), d[:5]))
        json.dump(summary, open(out_json, "w"), indent=1, sort_keys=True)

if __name__ == "__main__":
    main()
