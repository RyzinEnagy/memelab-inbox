#!/bin/sh
# Inside unshare -n: start the canned LLM, run the reddit smoke twice and the twitter offline check once.
python3 -I /home/claude/memelab-inbox/audits/predictive-intelligence/phase_03/research/SMOKES/666ghj__MiroFish/mock_llm.py 18080 /tmp/claude-0/-home-claude/6c3ea1ef-d097-5873-a280-98af7bc5c45c/scratchpad/r5/oasis_sim/mock_requests.jsonl & MP=$!
sleep 1
for r in run1 run2; do
  env -u HTTPS_PROXY -u HTTP_PROXY DO_NOT_TRACK=true HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TIKTOKEN_CACHE_DIR=/tmp/claude-0/-home-claude/6c3ea1ef-d097-5873-a280-98af7bc5c45c/scratchpad/r5/tiktoken_cache PYTHONPATH=/home/claude/pi_research/src/camel-ai__oasis /home/claude/pi_research/venvs/camel-ai__oasis/bin/python /home/claude/memelab-inbox/audits/predictive-intelligence/phase_03/research/SMOKES/camel-ai__oasis/smoke_oasis.py reddit /tmp/claude-0/-home-claude/6c3ea1ef-d097-5873-a280-98af7bc5c45c/scratchpad/r5/oasis_sim/$r 3 http://127.0.0.1:18080/v1 > /tmp/claude-0/-home-claude/6c3ea1ef-d097-5873-a280-98af7bc5c45c/scratchpad/r5/oasis_sim/$r.json 2> /tmp/claude-0/-home-claude/6c3ea1ef-d097-5873-a280-98af7bc5c45c/scratchpad/r5/oasis_sim/$r.err
  echo "$r exit_code=$?"
done
env -u HTTPS_PROXY -u HTTP_PROXY DO_NOT_TRACK=true HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TIKTOKEN_CACHE_DIR=/tmp/claude-0/-home-claude/6c3ea1ef-d097-5873-a280-98af7bc5c45c/scratchpad/r5/tiktoken_cache PYTHONPATH=/home/claude/pi_research/src/camel-ai__oasis timeout 300 /home/claude/pi_research/venvs/camel-ai__oasis/bin/python /home/claude/memelab-inbox/audits/predictive-intelligence/phase_03/research/SMOKES/camel-ai__oasis/smoke_oasis.py twitter /tmp/claude-0/-home-claude/6c3ea1ef-d097-5873-a280-98af7bc5c45c/scratchpad/r5/oasis_sim/tw 1 http://127.0.0.1:18080/v1 > /tmp/claude-0/-home-claude/6c3ea1ef-d097-5873-a280-98af7bc5c45c/scratchpad/r5/oasis_sim/tw.json 2> /tmp/claude-0/-home-claude/6c3ea1ef-d097-5873-a280-98af7bc5c45c/scratchpad/r5/oasis_sim/tw.err
echo "twitter exit_code=$?"
kill $MP
