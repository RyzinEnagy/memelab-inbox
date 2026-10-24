#!/bin/sh
# Inside unshare -n: one reddit run of smoke_oasis.py under a resource wrapper (peak RSS of the child).
python3 -I /home/claude/memelab-inbox/audits/predictive-intelligence/phase_03/research/SMOKES/666ghj__MiroFish/mock_llm.py 18080 /tmp/claude-0/-home-claude/6c3ea1ef-d097-5873-a280-98af7bc5c45c/scratchpad/r5/oasis_sim/mock_requests_rss.jsonl & MP=$!
sleep 1
python3 -I -c "
import resource, subprocess, time, os, sys
env = {k: v for k, v in os.environ.items() if 'PROXY' not in k.upper()}
env.update(DO_NOT_TRACK='true', HF_HUB_OFFLINE='1', TIKTOKEN_CACHE_DIR='/tmp/claude-0/-home-claude/6c3ea1ef-d097-5873-a280-98af7bc5c45c/scratchpad/r5/tiktoken_cache', PYTHONPATH='/home/claude/pi_research/src/camel-ai__oasis')
t0 = time.time()
p = subprocess.run(['/home/claude/pi_research/venvs/camel-ai__oasis/bin/python', '/home/claude/memelab-inbox/audits/predictive-intelligence/phase_03/research/SMOKES/camel-ai__oasis/smoke_oasis.py', 'reddit', '/tmp/claude-0/-home-claude/6c3ea1ef-d097-5873-a280-98af7bc5c45c/scratchpad/r5/oasis_sim/rss', '3', 'http://127.0.0.1:18080/v1'], env=env, capture_output=True, text=True)
print('exit_code', p.returncode, 'wall_incl_import_s', round(time.time() - t0, 2), 'peak_rss_mb', round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 1))
"
kill $MP
