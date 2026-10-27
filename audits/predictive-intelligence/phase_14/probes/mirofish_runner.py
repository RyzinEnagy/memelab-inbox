"""Phase 14 MiroFish runner (lab-written; runs inside `unshare -n`, launched by `behavioral.SubprocessAdapter`, which always uses `unshare -n`).

Inside the loopback-only namespace it raises `lo`, starts the Phase 03 mock LLM on 127.0.0.1 (unless MF_LLM=DOWN), starts the
lab's `behavioral.LLMMeter` between MiroFish and that mock, and runs MiroFish's own unmodified
`backend/scripts/run_reddit_simulation.py` (pin 7657031a, its own Python 3.12 venv) with a fictional profile set and a fictional
initial post. Nothing of MiroFish is imported, copied or modified (AGPL-3.0, P31). It reads the SQLite trace MiroFish writes and
answers in `memelab.behavioral_service/1`: llm_actions and llm_calls as integers, the trace sha256, the meter summary as integers,
and no hypothesis: the script path writes free-text posts, and the lab does not turn free text into codes (NOT_CODABLE).

    python -I mirofish_runner.py REQUEST RESPONSE      # environment: MF_REPO, MF_VENV_PY, MF_CLONE, MF_TT_CACHE, MF_LLM,
                                                         # MF_METER_CAP_USD, MF_PRICE_IN, MF_PRICE_OUT, MF_SIDE_OUT
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(os.environ["MF_REPO"])
sys.path.insert(0, str(REPO))
from memelab.predictive import behavioral as BH  # noqa: E402

P03 = REPO / "audits/predictive-intelligence/phase_03/research/SMOKES/666ghj__MiroFish"
PIN = "7657031ac01184afe2cb220f5ee3545573b5e843"
MOCK_PORT = 18091
NON_LLM_ACTIONS = {"sign_up", "refresh"}


def fictional_config(n_agents: int, rounds: int) -> tuple[list, dict]:
    profiles = [{"user_id": i, "username": f"agent_{i}", "name": f"Agent {i}", "bio": "fictional persona for a boundary run",
                 "persona": "A fictional market participant used only to exercise the simulator.", "karma": 1000,
                 "created_at": "2026-01-01", "age": 30, "gender": "female" if i % 2 else "male", "mbti": "ISTJ", "country": "Nowhere"}
                for i in range(n_agents)]
    config = {"simulation_id": "p14_boundary",
              "time_config": {"total_simulation_hours": 24, "minutes_per_round": 60, "agents_per_hour_min": 2,
                              "agents_per_hour_max": n_agents, "peak_hours": [], "off_peak_hours": []},
              "agent_configs": [{"agent_id": i, "active_hours": list(range(24)), "activity_level": 0.7} for i in range(n_agents)],
              "event_config": {"initial_posts": [{"poster_agent_id": 0, "content": "Fictional token FAKE2 announces a fictional exchange listing."}]}}
    return profiles, config


def main(req_path: str, resp_path: str) -> int:
    req = json.loads(Path(req_path).read_text())
    agents, rounds = req["run"]["agents"], req["run"]["rounds"]
    subprocess.run([sys.executable, "-I", str(P03 / "lo_up.py")], check=True, capture_output=True)
    clone = Path(os.environ["MF_CLONE"])
    head = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head != PIN or (clone / ".env").exists():
        return 3
    with tempfile.TemporaryDirectory(prefix="p14_mf_") as td:
        d = Path(td)
        mock = None
        if os.environ.get("MF_LLM") != "DOWN":
            mock = subprocess.Popen([sys.executable, "-I", str(P03 / "mock_llm.py"), str(MOCK_PORT), str(d / "mock.jsonl")],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.0)
        meter = BH.LLMMeter(f"http://127.0.0.1:{MOCK_PORT}", max_cost_usd=float(os.environ["MF_METER_CAP_USD"]),
                            price_in_per_1k_tokens_usd=float(os.environ["MF_PRICE_IN"]),
                            price_out_per_1k_tokens_usd=float(os.environ["MF_PRICE_OUT"]))
        url = meter.start()
        profiles, config = fictional_config(agents, rounds)
        (d / "reddit_profiles.json").write_text(json.dumps(profiles))
        (d / "simulation_config.json").write_text(json.dumps(config))
        env = {"PATH": "/usr/bin:/bin", "HOME": td, "LLM_API_KEY": BH.MOCK_KEY, "LLM_BASE_URL": url + "/v1", "LLM_MODEL_NAME": "gpt-4o-mini",
               "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PYTHONHASHSEED": "0", "TIKTOKEN_CACHE_DIR": os.environ["MF_TT_CACHE"]}
        p = subprocess.run([os.environ["MF_VENV_PY"], str(clone / "backend/scripts/run_reddit_simulation.py"), "--config",
                            str(d / "simulation_config.json"), "--no-wait", "--max-rounds", str(rounds)],
                           cwd=td, env=env, capture_output=True, text=True, timeout=600)
        meter.stop()
        if mock is not None:
            mock.kill()
            mock.wait()
        trace = []
        db = d / "reddit_simulation.db"
        if db.exists():
            con = sqlite3.connect(db)
            trace = con.execute("select user_id, action from trace order by rowid").fetchall()
            con.close()
        counts: dict[str, int] = {}
        for _, a in trace:
            counts[a] = counts.get(a, 0) + 1
        llm_actions = max(sum(v for k, v in counts.items() if k not in NON_LLM_ACTIONS) - len(config["event_config"]["initial_posts"]), 0)
        sm = meter.summary()
        resp = {"protocol": BH.PROTOCOL, "status": "OK", "llm_actions": llm_actions, "llm_calls": sm["calls_forwarded"] + sm["calls_refused"],
                "trace_sha256": hashlib.sha256(json.dumps(trace).encode()).hexdigest(), "hypotheses": [], "claims": [],
                "meter": {"calls_forwarded": sm["calls_forwarded"], "calls_refused": sm["calls_refused"],
                          "charged_microusd": sm["charged_microusd"], "cap_microusd": sm["cap_microusd"], "cap_reached": sm["cap_reached"],
                          "prompt_chars": sm["prompt_chars"]}}
        Path(resp_path).write_text(json.dumps(resp))
        side = {"script_exit_code": p.returncode, "action_counts": dict(sorted(counts.items())), "meter_breaker_open": sm["breaker_open"],
                "meter_ledger_statuses": sorted({e["status"] for e in meter.ledger}), "trace_rows": len(trace)}
        if os.environ.get("MF_SIDE_OUT"):
            Path(os.environ["MF_SIDE_OUT"]).write_text(json.dumps(side, sort_keys=True))
    return 0 if p.returncode == 0 else 10 + p.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
