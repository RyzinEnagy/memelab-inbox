# camel-ai/oasis (reviewer R5)

OASIS is the LLM social-media simulator MiroFish runs on. Evaluated as a behavioral scenario engine only; it produces agent actions on a simulated Twitter or Reddit, not forecasts. Agent agreement is not a probability (P27).

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | camel-ai/oasis, https://github.com/camel-ai/oasis |
| Pinned SHA | `8607dba82d73f7bfc371b3beafe57cc844687be2` ("Update WeChat QR code via QR Code Updater"), equal to the remote HEAD at review time |
| Commit date | 2026-10-19T17:33:52+08:00 (2026-10-19T09:33:52Z) |
| How fetched | `git fetch --depth 1 origin <sha>` into `/home/claude/pi_research/src/camel-ai__oasis` (111 MB, mostly `data/` and `assets/`), 2026-10-24T04:33Z; tag `v0.2.5` (`e97a1d83`) also fetched to compare |
| Review time (UTC) | 2026-10-24T04:48Z to 05:25Z |
| Version tested | the pinned tree on `PYTHONPATH` (no build). Dependencies: the exact pins in `pyproject.toml` at the pin (camel-ai 0.2.90, mcp 1.29.0, neo4j 5.23.0, igraph 0.11.6, sentence-transformers 3.0.0, unstructured 0.13.7, pandas 2.2.2) plus `torch==2.9.1+cpu`; Python 3.11.17 (`SMOKES/camel-ai__oasis/installed_requirements.txt`, `venv_freeze.txt`). There is no lock file, so transitive versions float (this run: numpy 2.4.6, openai 3.37.0, transformers 4.57.6, tiktoken 0.12.0) |
| Venv and clone | venv `/home/claude/pi_research/venvs/camel-ai__oasis` (1.3 GB) deleted after the review; clone kept at `/home/claude/pi_research/src/camel-ai__oasis`; `venv_freeze.txt` in SMOKES lists every installed version |
| Relation to releases | PyPI `camel-oasis 0.2.5` (2025-12-04, requires Python <3.12, camel-ai 0.2.78) corresponds to tag v0.2.5. The pin keeps the version string 0.2.5 but differs from the tag in 5 files (`git diff --stat`: `social_agent/agent.py`, `social_platform/config/user.py`, `social_platform/database.py`, `social_platform/recsys.py`, `pyproject.toml`, 27 insertions and 26 deletions; camel-ai bumped to 0.2.90, mcp added). MiroFish uses the PyPI release, not this pin |

## 2. License and security

| Item | Finding |
|---|---|
| Root license | Apache-2.0, `LICENSE` sha256 `950deb34b1341a0ac95236fae92fe247c318c3a83a62c9ebacbe1882530ab1f6` (matches Phase 02); per-file Apache headers; `licenses/license_template.txt` is the header template |
| Key transitive licenses | python-igraph 0.11.6: GPL-2.0 (LICENSE in the wheel), imported unconditionally at `oasis/social_agent/agent_graph.py:18`; neo4j driver: Apache-2.0 (imported at `:19`); camel-ai, sentence-transformers, unstructured: Apache-2.0; mcp, prance: MIT; cairocffi: BSD. In-process use in memelab would combine with GPL code; a separate process avoids that (INFERENCE, not legal advice) |
| Model weights | Twitter platform default recommender `twhin-bert` loads `Twitter/twhin-bert-base` with `from_pretrained` and no revision pin (`oasis/social_platform/recsys.py:64-80`); Hugging Face card metadata: apache-2.0, sha `82ac392c`. `RecsysType.TWITTER` loads `paraphrase-MiniLM-L6-v2` into `./models` (`recsys.py:86-89`). Reddit and random recommenders load nothing |
| Data files | `data/twitter_dataset/real_world_prop_data/*.pkl` are pickles of real Twitter propagation data used by `visualization/.../result_ana_*.py` (`pickle.load`); not loaded by the package. Data rights for that dataset: UNKNOWN |
| Install-time scripts | none needed: source used from the clone; all dependencies installed as wheels |
| Network at runtime | the LLM endpoint (any camel backend, `url=` supported); tiktoken encodings downloaded by camel's token counter on first use; Hugging Face downloads for the Twitter recommenders. Observed: with `HF_HUB_OFFLINE=1` in a loopback-only namespace the Twitter platform logged "Failed to load the model: Twitter/twhin-bert-base" and continued with exit 0 (`SMOKES/camel-ai__oasis/smoke_tw_log_errors.txt`) |
| Telemetry | none in OASIS; `unstructured` analytics as described in the MiroFish review (`unstructured/utils.py:308`, disabled by `DO_NOT_TRACK=true` or `SCARF_NO_ANALYTICS=true`; not triggered by importing `oasis`) |
| Side effects at import | `oasis/environment/env.py:30-45` creates `./log` in the current directory and opens a timestamped log file at import time; `social_agent/agent.py` and `platform.py` do the same for their loggers |
| Secrets | API keys come from the environment through camel (`OPENAI_API_KEY`); the test `test_agent_graph` fails without one. No key printing seen |

## 3. Code paths inspected at the pin

| Concern | Anchor |
|---|---|
| Environment and step | `oasis/environment/env.py:48` `OasisEnv`, `:118` `reset`, `:136` `step` (updates the recommendation table, then `asyncio.gather` of all agent actions), `:197-198` Twitter clock step |
| Platform | `oasis/social_platform/platform.py:53` `Platform`, SQLite schema in `social_platform/schema/*.sql`; default `recsys_type="reddit"` (`:64`) |
| Time | `platform.py:76-81`: default `Clock(60)` and `start_time = datetime.now()`; Reddit timestamps are wall-clock time scaled by 60 (`clock/clock.py:25-30`, `platform.py:180-184`), so the simulated timeline depends on how fast the LLM answers; Twitter uses an integer `time_step` |
| Agent | `social_agent/agent.py:55` `SocialAgent(ChatAgent)`, system prompt from the user profile, actions exposed as tools; `perform_action_by_llm` (`:125`) catches every exception, logs it and returns it (`:153-155`), so a failed LLM call becomes a skipped action |
| Observation prompt | `social_agent/agent_environment.py:33-60` `SocialEnvironment`; posts are serialised with `created_at` (`social_platform/platform_utils.py:80-138`), so wall-clock time enters every prompt |
| Recommenders | `social_platform/recsys.py:213` `rec_sys_reddit` (hot score), twhin-bert and TF-IDF paths; unseeded `random.sample` and `random.random` at `recsys.py:163`, `:413`, `:646-647`, `:749` and `platform.py:277`; `platform.py:373` logs and swallows any recommender exception and skips the update |
| Seeds | no `random.seed` or `np.random.seed` in `oasis/`; `agents_generator.py:53` documents a `model_random_seed` argument that `generate_agents` (`:34`) does not accept |
| Persistence | one SQLite file per simulation with `trace`, `post`, `like`, `follow`, `rec` and other tables (`social_platform/database.py`) |
| Actions | 32 `ActionType` members (`social_platform/typing.py`), including internal `exit`, `sign_up`, `update_rec_table` |
| Evaluation code | `visualization/twitter_simulation/align_with_real_world/code/result_ana_mse.py` and `result_ana_mean.py` compare simulated propagation scale, depth and breadth to the pickled real cascades (paper replication); there is no event forecast or probability evaluation |
| Tests | 31 test files. CI runs the whole suite with a real `OPENAI_API_KEY` (`.github/workflows/python-app.yml`). Offline subset (`test/infra/database`, Reddit rec-table test, action docstring, agent graph): 31 passed, 1 skipped, 1 failed (`test_agent_graph`: "Missing or empty required API keys ... OPENAI_API_KEY"), exit 1, 18 s (`SMOKES/camel-ai__oasis/oasis_pytest_offline.txt`) |

## 4. Smoke results

All runs inside `unshare -n` with loopback only, a deterministic canned LLM on 127.0.0.1 (`SMOKES/666ghj__MiroFish/mock_llm.py`, replies are a function of the request sha256), no key. Commands: `SMOKES/camel-ai__oasis/commands.txt`.

| Smoke | Result | Numbers and raw output |
|---|---|---|
| S1 leak trap | FAIL (static) and SKIPPED (metric) | no availability-time concept; any text placed in profiles or posts is used; no score exists to show inflation |
| S2 probability shape | SKIPPED | no probability output |
| S3 missing covariates | SKIPPED | not a covariate model |
| S4 calibration or uncertainty | SKIPPED (none offered) | |
| S5 persistence and reproducibility | FAIL | SQLite output persists, but two Reddit runs with the same 4 fictional agents, 3 rounds and the deterministic mock gave different traces (sha256 `7bb959b1...` with 28 rows and 8 posts versus `10472c0f...` with 26 rows and 2 posts, `smoke_run1.json`, `smoke_run2.json`). Already in round 1 none of the 4 request bodies matched between runs (equal lengths, different hashes): the observation prompt carries wall-clock `created_at` values, so even a deterministic model receives different inputs |
| S6 cost | measured | Reddit, 4 agents, 3 rounds: 1.76 s and 1.38 s inside the simulation, 15.57 s including imports, peak RSS 608.6 MB (`measure_rss_output.txt`); 28 LLM requests over the three runs averaging about 2,700 prompt characters (max 5,094), about 700 to 1,300 tokens per call in a near-empty world (`mock_requests.jsonl`). README reference: 335,600 input and 16,750 output tokens for 100 agents for one step (README.md "Token Consumption Reference"). No Python 3.12 or 3.13 support (`python >=3.10,<3.12`); pure-Python wheel on PyPI (`camel_oasis-0.2.5-py3-none-any.whl`), Windows not tested |
| Role: smallest offline example | PASS (Reddit), FAIL (Twitter offline) | Reddit runs end to end offline once tiktoken files are cached; Twitter exits 0 but its recommender never loads offline, and the run continues without recommendations (`smoke_tw.json`, `smoke_tw_log_errors.txt`) |

## 5. README or docs claims the code does not support (P42)

| Claim | Status |
|---|---|
| "realistically mimic the behavior of up to one million users" (README.md:43, :66) | NOT VERIFIED here; scale code exists (`agents_generator.py:179` `generate_agents_100w`); realism has only the cascade-alignment scripts above, not behaviour validation in markets |
| "Agents can perform 23 actions" (README.md:74) | outdated: 32 `ActionType` members at the pin |
| `model_random_seed (int): Random seed ... (default: 42)` (`agents_generator.py:53`, `:197`) | UNSUPPORTED: no such parameter; no seed control anywhere in the package |
| `assets/prediction.png` use case (README.md:105) | no forecast evaluation code in the repo |

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity and leakage safeguards (18) | 0 | Wall-clock clock in Reddit mode (`platform.py:76-81`), no as-of concept, every agent is an LLM with pretraining knowledge (P26) |
| Transferable measurable predictive outcomes (14) | 0 | Produces simulated actions only; no event, survival or regression output (S2 SKIPPED) |
| Calibration, uncertainty and abstention (12) | 0 | Nothing offered |
| Catalyst/social/on-chain features (10) | 2 | Structured synthetic social signals: 32 action types, follow graph, recommenders, SQLite trace (S5 traces); no observational timestamps, wallet or cross-token features |
| Decision/execution and stress compatibility (10) | 0 | No hooks |
| Code quality, maintenance and tests (8) | 3 | 31 offline tests pass for the database layer; active (October 2026); but swallowed exceptions (`agent.py:153-155`, `platform.py:373`), import-time file side effects, a stale docstring argument, version string not bumped after dependency changes, CI needs a paid key |
| Integration fit and extensibility (8) | 2 | Small clean API (`oasis.make`, `env.step`, `ManualAction`, `LLMAction`), any camel model backend with `url=`; but Python <3.12 (memelab runs 3.13), torch and sentence-transformers imported at load, GPL igraph, so only a separate process fits |
| Experiment reproducibility and audit (8) | 1 | Full action trace per run in SQLite; no seed, wall-clock in prompts, runs differ with a deterministic LLM (S5) |
| Cost, latency and operational reliability (5) | 1 | `semaphore` concurrency cap (`env.py:55`) and a documented token reference; 609 MB for 4 agents; failed LLM calls and failed model loads are silent |
| Licensing, security and data rights (7) | 3 | Apache-2.0 verified; GPL igraph transitive; unpinned Hugging Face model download (Apache-2.0 card); real-data pickles of unknown rights in the repo; no network service of its own |
| **Total** | **12** | |

## 7. Flags

- RESEARCH_ONLY: no testable event output and no independent accuracy evidence for market behaviour.
- LEAKAGE_FAIL: LLM agents carry pretraining knowledge (P26) that no configuration removes; Reddit timestamps come from the wall clock.
- NOT_REALTIME: LLM-bound per agent per step.
- P27: agents share one model; 90% of agents "agreeing" is a property of that model and prompt, not a 90% likelihood.
- P28: seeds are whatever text the caller puts in profiles and initial posts; nothing checks when that information became available.
- P29: identical inputs already diverge (S5).
- P30: a failing LLM call is logged and swallowed (`agent.py:153-155`); a failed recommender model load is logged and skipped (`platform.py:373`); both runs exit 0.
- P31: Apache-2.0 root, GPL igraph dependency.
- P42: section 5.
- P45: agents generate post text freely.

## 8. Proposed role and integration decision

- Role: if an LLM behavioral simulator is ever approved for Phase 14 and 15, OASIS used directly is the smaller and permissively licensed engine (no Zep Cloud, no AGPL, no web service), compared with MiroFish's wrapper. Until then it has no role beyond this review.
- Candidate INTEGRATION_DECISION: ISOLATED_RESEARCH. Separate venv (Python 3.11), separate process, loopback-only network namespace, Reddit platform or a custom `Platform` with the random recommender, tokenizer files pre-fetched, pinned model revision if a Twitter recommender is ever used, outputs read from SQLite and coded by memelab into pre-registered events, default `SIMULATION_NOT_AVAILABLE`. A seed would have to be imposed from outside (global `random` seeding in the subprocess plus a fixed clock through a custom `Platform(sandbox_clock=..., start_time=...)`), which this review did not test.
- Gap cells: N13 (PLANNED_SEAMS "Behavioral simulation"); proxy cells CATALYST:MODEL_TRAINING and SOCIAL_SIGNALS:MODEL_TRAINING only as the place Phase 15 would test incremental value.
