"""MiroFish offline simulation smoke (Phase 03, reviewer R5).

Runs MiroFish's own backend/scripts/run_reddit_simulation.py at the pinned SHA against a
canned localhost LLM (mock_llm.py) with a fictional 4-agent fixture, twice, with identical
inputs, then compares the two SQLite outputs. Meant to run inside `unshare -n` after
lo_up.py, so any outbound network call fails instead of leaving the machine.
No real key: LLM_API_KEY is the literal string "mock-not-a-key".

Usage: python3 -I smoke_mf_sim.py VENV_PY SCRIPT OUT_DIR [MAX_ROUNDS]
"""
import hashlib
import json
import os
import resource
import sqlite3
import subprocess
import sys
import time

VENV_PY, SCRIPT, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
MAX_ROUNDS = int(sys.argv[4]) if len(sys.argv) > 4 else 4
HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 18080

PROFILES = [
    {"user_id": i, "username": f"agent_{i}", "name": f"Agent {i}",
     "bio": "fictional trader persona for a format smoke",
     "persona": "A fictional crypto trader used only to test the simulator plumbing.",
     "karma": 1000, "created_at": "2026-01-01", "age": 30, "gender": "female" if i % 2 else "male",
     "mbti": "ISTJ", "country": "Nowhere"} for i in range(4)
]
CONFIG = {
    "simulation_id": "smoke_r5",
    "time_config": {"total_simulation_hours": 24, "minutes_per_round": 60,
                    "agents_per_hour_min": 2, "agents_per_hour_max": 4,
                    "peak_hours": [], "off_peak_hours": []},
    "agent_configs": [{"agent_id": i, "active_hours": list(range(24)), "activity_level": 0.7}
                      for i in range(4)],
    "event_config": {"initial_posts": [{"poster_agent_id": 0,
                                        "content": "Fictional token FAKE1 announces a fictional listing."}]},
}


def run_once(tag):
    d = os.path.join(OUT, tag)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "reddit_profiles.json"), "w") as fh:
        json.dump(PROFILES, fh)
    cfg = os.path.join(d, "simulation_config.json")
    with open(cfg, "w") as fh:
        json.dump(CONFIG, fh)
    log = os.path.join(d, "mock_requests.jsonl")
    mock = subprocess.Popen([sys.executable, "-I", os.path.join(HERE, "mock_llm.py"), str(PORT), log])
    time.sleep(1.0)
    env = {k: v for k, v in os.environ.items() if not k.endswith("_PROXY") and not k.endswith("_proxy")}
    env.update({"LLM_API_KEY": "mock-not-a-key", "LLM_BASE_URL": f"http://127.0.0.1:{PORT}/v1",
                "LLM_MODEL_NAME": "gpt-4o-mini", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                "PYTHONHASHSEED": "0"})
    t0 = time.time()
    p = subprocess.run([VENV_PY, SCRIPT, "--config", cfg, "--no-wait", "--max-rounds", str(MAX_ROUNDS)],
                       cwd=d, env=env, capture_output=True, text=True, timeout=900)
    wall = time.time() - t0
    mock.terminate()
    mock.wait()
    with open(os.path.join(d, "stdout_stderr.txt"), "w") as fh:
        fh.write(p.stdout + "\n--- stderr ---\n" + p.stderr)
    res = {"tag": tag, "exit_code": p.returncode, "wall_s": round(wall, 2)}
    db = os.path.join(d, "reddit_simulation.db")
    if os.path.exists(db):
        con = sqlite3.connect(db)
        tables = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
        res["tables"] = tables
        res["counts"] = {t: con.execute(f"select count(*) from {t}").fetchone()[0] for t in tables}
        trace = con.execute("select user_id, action from trace order by rowid").fetchall()
        res["trace_user_action"] = trace
        res["trace_sha256"] = hashlib.sha256(json.dumps(trace).encode()).hexdigest()
        posts = con.execute("select user_id, content from post order by post_id").fetchall()
        res["posts_sha256"] = hashlib.sha256(json.dumps(posts).encode()).hexdigest()
        con.close()
    reqs = []
    if os.path.exists(log):
        reqs = [json.loads(x) for x in open(log)]
    res["llm_requests"] = len(reqs)
    res["llm_prompt_chars_total"] = sum(r["prompt_chars"] for r in reqs)
    res["llm_reply_kinds"] = {k: sum(1 for r in reqs if r["reply"] == k) for k in sorted({r["reply"] for r in reqs})}
    return res


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    results = [run_once("run1"), run_once("run2")]
    ru = resource.getrusage(resource.RUSAGE_CHILDREN)
    same_trace = results[0].get("trace_sha256") == results[1].get("trace_sha256")
    summary = {"max_rounds": MAX_ROUNDS, "runs": results, "identical_trace_across_runs": same_trace,
               "peak_rss_children_mb": round(ru.ru_maxrss / 1024, 1)}
    print(json.dumps(summary, indent=1, default=str))
