"""Phase 04 MiroFish feasibility: a sample structured scenario adapter (prototype, outside memelab/, research only).

The adapter never imports, copies or modifies MiroFish (AGPL-3.0, P31). It runs MiroFish's own, unmodified
`backend/scripts/run_reddit_simulation.py` as a separate process in its own Python 3.12 venv, inside a network namespace whose
only interface is loopback, against a canned LLM on 127.0.0.1 (the Phase 03 mock, `phase_03/.../mock_llm.py`), with a fictional
scenario seed written to a temporary directory. It reads back the SQLite trace and returns a scenario document that carries
no probability, likelihood or confidence field (P27). A run counts as failed unless its trace holds LLM-generated actions,
because MiroFish exits 0 and prints "simulation loop complete" when its LLM is unreachable (Phase 03 MI-3, P30).

No key is read: the child environment is built from scratch with the literal LLM_API_KEY "mock-not-a-key". Paid LLM and Zep use
is not approved (PI-D-005), so a live run is NOT_SUPPORTED by this adapter.

    python mirofish_adapter.py OUT.json        # needs root for unshare -n; venv and clone paths below
"""
from __future__ import annotations

import hashlib
import json
import os
import resource
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
P03 = HERE.parents[2] / "phase_03" / "research" / "SMOKES" / "666ghj__MiroFish"
VENV_PY = "/home/claude/pi_research/venvs/p04_mirofish/bin/python"
CLONE = Path("/home/claude/pi_research/src/666ghj__MiroFish")
PIN = "7657031ac01184afe2cb220f5ee3545573b5e843"
SCRIPT = CLONE / "backend/scripts/run_reddit_simulation.py"
TIKTOKEN_CACHE = "/tmp/claude-0/-home-claude/6c3ea1ef-d097-5873-a280-98af7bc5c45c/scratchpad/r5/tiktoken_cache"
PORT = 18081
NON_LLM_ACTIONS = {"sign_up", "refresh"}
FORBIDDEN = ("probability", "likelihood", "confidence_pct", "confidence")


def scenario_seed(n_agents: int) -> tuple[list, dict]:
    """A fictional seed: no real token, account or post. Persona strings are generic placeholders."""
    profiles = [{"user_id": i, "username": f"agent_{i}", "name": f"Agent {i}", "bio": "fictional persona for a feasibility run",
                 "persona": "A fictional market participant used only to exercise the simulator.", "karma": 1000,
                 "created_at": "2026-01-01", "age": 30, "gender": "female" if i % 2 else "male", "mbti": "ISTJ", "country": "Nowhere"}
                for i in range(n_agents)]
    config = {"simulation_id": "p04_feasibility",
              "time_config": {"total_simulation_hours": 24, "minutes_per_round": 60, "agents_per_hour_min": 2,
                              "agents_per_hour_max": n_agents, "peak_hours": [], "off_peak_hours": []},
              "agent_configs": [{"agent_id": i, "active_hours": list(range(24)), "activity_level": 0.7} for i in range(n_agents)],
              "event_config": {"initial_posts": [{"poster_agent_id": 0, "content": "Fictional token FAKE2 announces a fictional exchange listing."}]}}
    return profiles, config


def run_scenario(*, llm_up: bool, n_agents: int = 4, rounds: int = 4, approved_for_paid_llm: bool = False) -> dict:
    if approved_for_paid_llm:
        return {"status": "NOT_SUPPORTED", "reason": "paid LLM or Zep use is not approved (PI-D-005); this adapter only runs a local mock"}
    head = subprocess.run(["git", "-C", str(CLONE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head != PIN or not Path(VENV_PY).exists() or (CLONE / ".env").exists():
        return {"status": "SIMULATION_NOT_AVAILABLE", "reason": "clone not at the pin, venv absent, or a .env present"}
    profiles, config = scenario_seed(n_agents)
    seed_sha = hashlib.sha256(json.dumps([profiles, config], sort_keys=True).encode()).hexdigest()
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "reddit_profiles.json").write_text(json.dumps(profiles))
        (d / "simulation_config.json").write_text(json.dumps(config))
        log = d / "mock_requests.jsonl"
        env = {"PATH": "/usr/bin:/bin", "HOME": td, "LLM_API_KEY": "mock-not-a-key", "LLM_BASE_URL": f"http://127.0.0.1:{PORT}/v1",
               "LLM_MODEL_NAME": "gpt-4o-mini", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PYTHONHASHSEED": "0",
               "TIKTOKEN_CACHE_DIR": TIKTOKEN_CACHE}
        mock = (f"{sys.executable} -I {P03 / 'mock_llm.py'} {PORT} {log} >/dev/null 2>&1 & MOCK=$!; sleep 1;" if llm_up
                else "MOCK=;")
        inner = (f"{sys.executable} -I {P03 / 'lo_up.py'} >/dev/null; {mock} "
                 f"{VENV_PY} {SCRIPT} --config {d / 'simulation_config.json'} --no-wait --max-rounds {rounds}; RC=$?; "
                 f"[ -n \"$MOCK\" ] && kill $MOCK; echo EXIT_CODE=$RC")
        r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
        t0 = time.time()
        p = subprocess.run(["unshare", "-n", "sh", "-c", inner], cwd=td, env=env, capture_output=True, text=True, timeout=900)
        wall = time.time() - t0
        r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        exit_line = [ln for ln in p.stdout.splitlines() if ln.startswith("EXIT_CODE=")]
        script_exit = int(exit_line[-1].split("=")[1]) if exit_line else None
        trace, counts = [], {}
        db = d / "reddit_simulation.db"
        if db.exists():
            con = sqlite3.connect(db)
            trace = con.execute("select user_id, action from trace order by rowid").fetchall()
            con.close()
        for _, a in trace:
            counts[a] = counts.get(a, 0) + 1
        initial = len(config["event_config"]["initial_posts"])
        llm_actions = sum(v for k, v in counts.items() if k not in NON_LLM_ACTIONS) - initial
        reqs = [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
        doc = {"kind": "BEHAVIORAL_HYPOTHESIS_NOT_A_FORECAST", "engine": "MiroFish run_reddit_simulation.py (unmodified, separate process)",
               "engine_pin": PIN, "license_boundary": "AGPL-3.0 program run as a separate process; no code imported or copied",
               "seed_sha256": seed_sha, "fictional_seed": True, "agents": n_agents, "rounds": rounds,
               "script_exit_code": script_exit, "action_counts": dict(sorted(counts.items())), "llm_actions": max(llm_actions, 0),
               "trace_sha256": hashlib.sha256(json.dumps(trace).encode()).hexdigest(), "llm_requests_seen_by_mock": len(reqs),
               "wall_s": round(wall, 2), "children_cpu_s": round((r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime), 2),
               "children_peak_rss_mb": round(r1.ru_maxrss / 1024, 1), "llm_up": llm_up}
    doc["status"] = "SIMULATION_RAN" if (doc["script_exit_code"] == 0 and doc["llm_actions"] > 0) else "SIMULATION_NOT_AVAILABLE"
    if doc["status"] != "SIMULATION_RAN":
        doc["reason"] = "NO_LLM_ACTIONS" if doc["script_exit_code"] == 0 else f"SCRIPT_EXIT_{doc['script_exit_code']}"
    assert not any(k in doc for k in FORBIDDEN), "a behavioral scenario never carries a probability (P27)"
    return doc


def backend_without_keys() -> dict:
    """P30 at the service level: MiroFish's backend refuses to start without LLM and Zep keys (config.py:64-72, run.py:28-33)."""
    env = {"PATH": "/usr/bin:/bin", "HOME": tempfile.gettempdir(), "PYTHONHASHSEED": "0"}
    p = subprocess.run(["unshare", "-n", VENV_PY, str(CLONE / "backend/run.py")], cwd=str(CLONE / "backend"), env=env,
                       capture_output=True, text=True, timeout=120)
    missing = [k for k in ("LLM_API_KEY", "ZEP_API_KEY") if k in p.stdout]
    return {"exit_code": p.returncode, "missing_keys_reported": missing, "started_server": "Running on" in (p.stdout + p.stderr)}


def main(out: str) -> None:
    res = {"backend_without_keys": backend_without_keys(),
           "run1_llm_mock": run_scenario(llm_up=True), "run2_llm_mock_same_seed": run_scenario(llm_up=True),
           "run3_llm_down": run_scenario(llm_up=False), "paid_route": run_scenario(llm_up=True, approved_for_paid_llm=True)}
    res["same_seed_identical_trace"] = res["run1_llm_mock"].get("trace_sha256") == res["run2_llm_mock_same_seed"].get("trace_sha256")
    Path(out).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps(res, indent=1, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1])
