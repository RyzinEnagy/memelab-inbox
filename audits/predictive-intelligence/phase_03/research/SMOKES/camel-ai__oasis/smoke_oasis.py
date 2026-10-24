"""OASIS offline smoke at the pinned SHA (Phase 03, reviewer R5).

Mode "reddit": 4 fictional agents, Reddit platform (hot-score recsys, no model download),
every agent takes one LLMAction per round for N rounds against the canned localhost LLM
(../666ghj__MiroFish/mock_llm.py, started by the caller), then prints the trace.
Mode "twitter": builds the default Twitter platform and takes one step, to see whether
the twhin-bert recsys needs a model download (run with HF_HUB_OFFLINE=1 inside unshare -n).

Usage (inside unshare -n, PYTHONPATH=<oasis clone>):
  python smoke_oasis.py reddit WORKDIR ROUNDS BASE_URL
  python smoke_oasis.py twitter WORKDIR 1 BASE_URL
"""
import asyncio
import hashlib
import json
import os
import sqlite3
import sys
import time

MODE, WORK, ROUNDS, BASE_URL = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
os.makedirs(WORK, exist_ok=True)
os.chdir(WORK)

import oasis  # noqa: E402
from camel.models import ModelFactory  # noqa: E402
from camel.types import ModelPlatformType  # noqa: E402
from oasis import ActionType, LLMAction, ManualAction  # noqa: E402

PROFILES = [{"username": f"agent_{i}", "realname": f"Agent {i}", "bio": "fictional trader persona",
             "persona": "A fictional crypto trader used only to test simulator plumbing.",
             "mbti": "ISTJ", "gender": "male", "age": 30, "country": "Nowhere"} for i in range(4)]


async def main():
    model = ModelFactory.create(model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
                                model_type="gpt-4o-mini", url=BASE_URL, api_key="mock-not-a-key")
    prof = os.path.join(WORK, "profiles.json")
    with open(prof, "w") as fh:
        json.dump(PROFILES, fh)
    db = os.path.join(WORK, f"{MODE}.db")
    if os.path.exists(db):
        os.remove(db)
    if MODE == "reddit":
        graph = await oasis.generate_reddit_agent_graph(
            profile_path=prof, model=model,
            available_actions=[ActionType.CREATE_POST, ActionType.LIKE_POST, ActionType.DO_NOTHING,
                               ActionType.REFRESH])
        env = oasis.make(agent_graph=graph, platform=oasis.DefaultPlatformType.REDDIT, database_path=db)
    else:
        graph = oasis.AgentGraph()
        for i, p in enumerate(PROFILES):
            graph.add_agent(oasis.SocialAgent(agent_id=i, user_info=oasis.UserInfo(
                name=p["username"], description=p["bio"],
                profile={"other_info": {"user_profile": p["persona"]}}, recsys_type="twhin-bert"),
                agent_graph=graph, model=model))
        env = oasis.make(agent_graph=graph, platform=oasis.DefaultPlatformType.TWITTER, database_path=db)
    t0 = time.time()
    await env.reset()
    agents = [a for _, a in env.agent_graph.get_agents()]
    await env.step({agents[0]: ManualAction(action_type=ActionType.CREATE_POST,
                                            action_args={"content": "Fictional token FAKE1 news."})})
    for _ in range(ROUNDS):
        await env.step({a: LLMAction() for a in agents})
    await env.close()
    wall = time.time() - t0
    con = sqlite3.connect(db)
    trace = con.execute("select user_id, action from trace order by rowid").fetchall()
    times = con.execute("select created_at from post order by post_id").fetchall()
    out = {"mode": MODE, "rounds": ROUNDS, "wall_s": round(wall, 2), "trace": trace,
           "trace_sha256": hashlib.sha256(json.dumps(trace).encode()).hexdigest(),
           "post_created_at": times}
    print(json.dumps(out, default=str))


asyncio.run(main())
