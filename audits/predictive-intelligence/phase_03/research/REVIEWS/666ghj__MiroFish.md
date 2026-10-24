# 666ghj/MiroFish (reviewer R5)

Evaluated only as a behavioral scenario generator (PI-D-024, references/MIROFISH_EVALUATION.md). Its outputs are qualitative scenarios and an LLM-written report. Agent agreement inside a MiroFish run is not a probability of anything (P27), and nothing below assigns it numerical accuracy.

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | 666ghj/MiroFish, https://github.com/666ghj/MiroFish |
| Pinned SHA | `7657031ac01184afe2cb220f5ee3545573b5e843` ("chore: update Star History (#832)") |
| Commit date | 2026-10-02T02:20:36+08:00 (2026-10-01T18:20:36Z) |
| How fetched | `git init; git fetch --depth 1 origin <sha>; git checkout FETCH_HEAD` into `/home/claude/pi_research/src/666ghj__MiroFish` (18 MB), 2026-10-24T04:33Z |
| Review time (UTC) | 2026-10-24T04:33Z to 05:20Z |
| Version tested | the pinned tree itself (backend run from the clone; `backend/pyproject.toml` version 0.1.0). Dependencies: the frozen `backend/uv.lock` exported with `uv export --frozen --no-dev --python 3.12` and installed with `--no-deps`, except `torch==2.9.1` replaced by `2.9.1+cpu` from the PyTorch CPU index and the 15 `nvidia-*` packages and `triton` left out (`SMOKES/666ghj__MiroFish/installed_from_uv_lock_cpu.txt`, `venv_freeze.txt`). Python 3.12.3. `uv pip check` reports that `camel-oasis 0.2.5` and `unstructured 0.13.7` declare Python <3.12; the lock installs them on 3.12 anyway. The Dockerfile uses `python:3.11` |
| Venv and clone | venv `/home/claude/pi_research/venvs/666ghj__MiroFish` (1.4 GB) deleted after the review; clone kept at `/home/claude/pi_research/src/666ghj__MiroFish`; `venv_freeze.txt` in SMOKES lists every installed version |
| Relation to releases | not on PyPI (`pypi.org/pypi/mirofish/json` 404). Git tags v0.1.0 to v0.1.2 exist; the pin is a later untagged commit. It depends on PyPI `camel-oasis==0.2.5` (OASIS tag v0.2.5 `e97a1d83`), not on the OASIS pin reviewed separately |
| Maintainer FAQ (issue 726) | UNKNOWN: WebFetch of https://github.com/666ghj/MiroFish/issues/726 returned "permission request not answered in time" (blocked URL); WebSearch for the issue returned no matching page. Nothing in this review rests on it |

## 2. License and security

| Item | Finding |
|---|---|
| Root license | AGPL-3.0, `LICENSE` 661 lines, sha256 `8486a10c4393cee1c25392769ddd3b2d6c242d6ec7928e1414efff7dfb2f07ef` (matches Phase 02); `backend/pyproject.toml` and `package.json` both say AGPL-3.0 |
| Nested notices | `.github/star-history/THIRD_PARTY_NOTICES.md` (MIT, star-history tooling only) |
| Key transitive licenses (installed metadata) | PyMuPDF 1.26.7: dual AGPL-3.0 or Artifex commercial; python-igraph 0.11.6 (via camel-oasis): GPL-2.0 (LICENSE file in the wheel); chardet 5.2.0: LGPL-2.1+; camel-ai, camel-oasis, openai, zep-cloud 3.25.0: Apache-2.0; Flask: BSD-3-Clause |
| AGPL obligations | Copying any MiroFish file into memelab makes the result a covered work; memelab is a public repo with no LICENSE file, so it could not be conveyed under its current terms (P31; also forbidden by PI-D-005). Running it unmodified, privately, as a separate process: no source obligation beyond keeping notices. Section 13 (network use): if a modified MiroFish is reachable by other users over a network, every such user must be offered the corresponding source. The defaults make network exposure easy by accident: `backend/run.py:40` binds `0.0.0.0`, the frontend dev server runs `vite --host` (`frontend/package.json:7`), the Dockerfile `CMD` runs that dev mode (`Dockerfile:29`). Whether an HTTP/JSON client in memelab is a separate work is INFERENCE (arm's-length communication is the usual reading), not a legal opinion |
| Model weights | the default Twitter platform (and the default `parallel` mode) builds OASIS's `twhin-bert` recommender, which calls `AutoModel.from_pretrained("Twitter/twhin-bert-base")` with no revision pin (OASIS `recsys.py:64-80`); Hugging Face model card metadata: license apache-2.0, sha `82ac392c` at 2026-10-24. The Reddit platform downloads nothing |
| Install-time scripts | all locked packages install from wheels except `langdetect 1.0.9` and `docopt 0.6.2` (sdist only); `langdetect`'s `setup.py` was read (plain `setup()`). No post-install hooks found |
| Network calls at runtime | LLM (any OpenAI-compatible URL, default `https://api.openai.com/v1`, `backend/app/config.py:29`); Zep Cloud only (`ZEP_API_URL` refused, `config.py:71-72`); camel's token counter downloads `o200k_base.tiktoken` from `openaipublic.blob.core.windows.net` on first use (observed: offline attempt 1 failed with `NameResolutionError`, `SMOKES/666ghj__MiroFish/sim_attempt1_offline_tiktoken_fetch.txt`); Hugging Face model download for the Twitter platform |
| Telemetry | none in MiroFish code. `unstructured` (OASIS dependency) has `scarf_analytics()` (`unstructured/utils.py:308`) that GETs `packages.unstructured.io/python-telemetry` when `unstructured.logger` is imported, unless `SCARF_NO_ANALYTICS=true` or `DO_NOT_TRACK=true`; importing `oasis` did not import that module and made no connection attempt (socket spy, inside the namespace). camel's AgentOps hooks activate only when `AGENTOPS_API_KEY` is set |
| Secrets handling | keys from `.env` at the project root loaded with `override=True` (`config.py:11`), so the file beats the process environment; the simulation subprocess gets a full copy of the backend environment (`simulation_runner.py:533`) and the scripts copy `LLM_API_KEY` into `OPENAI_API_KEY`. Keys are not printed (only the first 40 characters of the base URL) |
| Service security | 59 `/api/*` routes, none authenticated (`SMOKES/666ghj__MiroFish/api_smoke_output.txt`: `GET /api/simulation/list` returns 200 with no credential); CORS `origins: "*"` (`backend/app/__init__.py:43`), observed reflecting `http://untrusted.example`; default `SECRET_KEY = 'mirofish-secret-key'` (`config.py:21`); 50 error handlers return `traceback.format_exc()` to the client (3 in `api/graph.py`, 17 in `api/report.py`, 30 in `api/simulation.py`); IDs from request bodies are joined into filesystem paths without validation (for example `api/simulation.py:289`), exploitability not tested; debug logging writes JSON request bodies (`__init__.py:57`) |
| Data rights | every uploaded seed document, the extracted entity graph and (with the frontend default) all simulated activity are sent to Zep Cloud, and prompts with that text go to the LLM provider. Zep Cloud and LLM provider terms: UNKNOWN (not read) |

## 3. Code paths inspected at the pin

| Concern | Anchor |
|---|---|
| API surface | `backend/app/__init__.py:66-69` registers `graph`, `simulation`, `report` blueprints; 59 routes (`api/graph.py:132-907`, `api/simulation.py:78-2811`, `api/report.py:32-1102`) |
| Graph ingestion | `api/graph.py:265` `/ontology/generate` takes files plus a free-text `simulation_requirement`; `services/ontology_generator.py:203` LLM ontology; `services/graph_builder.py:407` `add_text_batches` sends chunks as Zep `BatchAddItem` (`:470-485`) with no source or event time (no `created_at` is passed, so the Zep server default applies; INFERENCE: that default is ingestion time). The `Project` model (`models/project.py:27-55`) has no as-of or source-date field |
| Persona generation | `services/oasis_profile_generator.py:274` per entity; Zep `graph.search` for context with no `search_filters` (`:386`, `:399`; zep-cloud 3.25.0 supports `created_at`, `valid_at`, `invalid_at` and episode-metadata filters, none used anywhere in `app/`); LLM persona at `:540`, system prompt `:718` and user prompts `:734`, `:783` tell the model to "restore the existing real situation to the maximum extent" (最大程度还原已有现实情况); silent fallback to a rule-based profile after 3 failed calls (`:622-625`) |
| Simulation config | `services/simulation_config_generator.py:244` `generate_config`; `:648-719` LLM writes `hot_topics`, `narrative_direction` and the initial posts; an LLM failure returns an empty event config with a log warning only (`:710-719`); temperature 0.7 (`:452`) |
| Simulation runner | `services/simulation_runner.py:204` `SimulationRunner`, `:371` `start_simulation`, `:539` `subprocess.Popen` of `backend/scripts/run_{twitter,reddit,parallel}_simulation.py` in a new process group; per-round agent activation with the unseeded module `random` (`scripts/run_twitter_simulation.py:497`, `:511`, `:515`; same pattern in the Reddit and parallel scripts). `git grep` for `random.seed`, `np.random`, `seed=`: 0 hits in the repo |
| Agent behaviour | OASIS `SocialAgent` with one shared LLM backend for all agents (`scripts/run_reddit_simulation.py` `_create_model` via camel `ModelFactory`, base URL from `LLM_BASE_URL`); `oasis.make(..., semaphore=30)` is the only concurrency limit |
| Zep memory write-back | `services/zep_graph_memory_updater.py:494-499` writes simulated agent activity into the same Zep graph as the source documents, `created_at` taken from the activity timestamp, which defaults to `datetime.now()` (`:405`). API default off (`api/simulation.py:1554`), frontend sends `enable_graph_memory_update: true` (`frontend/src/components/Step3Simulation.vue:402`) |
| ReportAgent | `services/report_agent.py:871` `ReportAgent`; tools `insight_forge`, `panorama_search`, `quick_search`, `interview_agents` (`:925-960`) search the whole graph with no filter separating document facts from simulated activity; `PLAN_SYSTEM_PROMPT` (`:552-567`) says the simulated world's evolution "is the prediction of what may happen in the future", that the model is reading "a rehearsal of the future", and that "agent words and deeds in the simulated world are the prediction of future crowd behaviour"; section prompt `:615-663` repeats it; `_strip_fake_tool_results` (`:1144`) removes tool results the LLM invents |
| Probability output | none: no `probab` in backend English code; the only Chinese mentions (概率) are agent activation comments (`simulation_config_generator.py:80`, `run_twitter_simulation.py:499`, `:510`) |
| Persistence | projects and reports as JSON files under `backend/uploads/` (`models/project.py:111-180`); `run_state.json` per simulation (`simulation_runner.py:301-370`); OASIS SQLite per platform (`reddit_simulation.db`, `twitter_simulation.db`); `actions.jsonl` logs; task status only in memory (`models/task.py:56-72`, lost on restart) |
| Recovery | no resume of an interrupted simulation; on shutdown the cleanup handler kills simulation process groups (`simulation_runner.py:1554` `register_cleanup`); a restarted backend reads the last `run_state.json` as is |
| Cost controls | `max_rounds` truncation (`simulation_runner.py:407-412`), `semaphore=30`, `REPORT_AGENT_MAX_TOOL_CALLS=5` (`config.py:59`). No token budget, spend cap or circuit breaker (`git grep -i "budget|cost|spend"` finds only an excerpt budget in the ontology prompt builder) |
| Tests | `backend/tests/` 19 files, 110 test functions; plus 2 root tests for star-history scripts. Ran all backend tests offline inside a loopback-only network namespace: 129 passed, exit 0, 17 s wall (`SMOKES/666ghj__MiroFish/backend_pytest.txt`). They cover Zep contracts, paging, retry, graph lifecycle barriers, ontology validation, JSON parsing and the report tool sanitizer with fakes; none covers seeding, reproducibility or output validity |

## 4. Smoke results

All runs inside `unshare -n` with only loopback up (`lo_up.py`), so any outbound call fails instead of leaving the machine. No key, no Zep. Commands: `SMOKES/666ghj__MiroFish/commands.txt`.

| Smoke | Result | Numbers and raw output |
|---|---|---|
| S1 leak trap | FAIL (static) and SKIPPED (metric) | No feature, timestamp or availability concept for seeds: uploads, `simulation_requirement` and Zep searches have no as-of filter (section 3). Metric inflation cannot be shown: there is no probability or score to evaluate on the challenge |
| S2 probability shape | SKIPPED | no probability output exists |
| S3 missing covariates | SKIPPED | inputs are documents and text, not covariates |
| S4 calibration or uncertainty | SKIPPED (none offered) | no calibration, interval or abstention; the report prompt presents simulated behaviour as the future (P27) |
| S5 persistence and reproducibility | FAIL | outputs persist (SQLite, JSON, logs), but two runs of the pinned Reddit script with identical config, profiles and a deterministic localhost mock LLM produced different traces: run1 19 trace rows (posts 3, likes 3), run2 20 rows (posts 5, likes 1), trace sha256 `a0a70f5f...` versus `3159ba9f...` (`sim_summary.json`). Cause in code: unseeded agent activation (`run_*_simulation.py`), and no seed parameter exists |
| S6 cost | measured on the smallest case | 4 fictional agents, 4 rounds of 60 simulated minutes: script exit 0, 15.0 s and 17.0 s wall, peak RSS of child processes 609.9 MB (torch and sentence-transformers are imported); 8 LLM calls per run, 21,455 and 21,968 prompt characters in total (about 2,700 characters, roughly 680 tokens, per call in a near-empty world; OASIS's README reference is 335,600 input tokens for 100 agents for one step). Offline only after pre-fetching tiktoken files; Twitter or parallel mode also needs the Hugging Face model. No Python 3.13 support (`requires-python >=3.11,<3.13`); not on PyPI, so no wheel list; Windows handling exists in `run.py:8-16` (not tested) |
| Role: smallest offline example | PASS with caveats | attempt 1 failed (exit 1) because camel tried to download `o200k_base.tiktoken`; attempt 2 with `TIKTOKEN_CACHE_DIR` pre-filled ran the unmodified script end to end against the mock (`sim_run1/`, `sim_run2/`, `mock_requests.jsonl`). This path uses no Zep, no Flask backend and no MiroFish source copy |
| Role: missing or failing LLM (P30) | FAIL | the backend refuses to start without keys (`Config.validate`, `api_smoke_output.txt`), but with the LLM endpoint unreachable the simulation script still exits 0, prints "模拟循环完成!" (loop complete) and leaves a database with only sign-ups, the initial post and refreshes; agent errors go to `log/social.agent.log` only (`llm_down_output.txt`). Persona and event-config generation also fall back silently (section 3) |

Estimated scale of a default run (INFERENCE from code, not measured): the fallback time config is 72 simulated hours at 30 minutes per round (144 rounds) with `agents_per_hour` between `max(1, n/15)` and `max(5, n/5)` (`simulation_config_generator.py:604-605`), per platform, with the default `parallel` mode running two platforms. For 50 entities that is on the order of 1,000 to 2,000 agent LLM calls, plus profile, config and report calls, before any retry. `.env.example` itself warns that consumption is high and suggests fewer than 40 rounds first.

## 5. README or docs claims the code does not support (P42)

| Claim (README.md) | Status |
|---|---|
| "Predicting Anything", "AI prediction engine", "precisely deduce future trajectories" (lines 9, 29, 41) | UNSUPPORTED: no forecast output, no evaluation code, no backtest, no test of accuracy |
| "win decisions after countless simulations" (line 29) | UNSUPPORTED: no multi-run ensemble, seed sweep or aggregation code; each simulation is one unseeded run |
| "high-fidelity parallel digital world", "maps reality" (lines 29, 36) | UNSUPPORTED: no validation against observed behaviour |
| "thousands of intelligent agents with independent personalities" (line 29) | UNSUPPORTED as independence: all agents call one shared LLM (or one boost LLM); personas are prompts to that model, so agent votes are not independent evidence |
| "test policies at zero risk" (line 38) | UNSUPPORTED: no risk measure; a wrong scenario carries the risk of acting on it |
| Demo "predicting the lost ending" of Dream of the Red Chamber from the first 80 chapters (line 81) | not a valid retrospective test: the novel's 120-chapter continuation is in LLM pretraining data (P26, INFERENCE) |

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity and leakage safeguards (18) | 0 | No as-of concept for seeds, no time filter on Zep searches although the SDK offers one, persona prompts ask the LLM to reconstruct reality from its own knowledge (`oasis_profile_generator.py:718`), simulated activity is written into the fact graph, wall-clock timestamps (section 3) |
| Transferable measurable predictive outcomes (14) | 0 | No event classification, survival or regression output; outputs are agent actions and an LLM report (S2 SKIPPED) |
| Calibration, uncertainty and abstention (12) | 0 | Nothing offered; the report prompt states simulated behaviour is the future (`report_agent.py:552-567`) |
| Catalyst/social/on-chain features (10) | 2 | Turns catalyst documents into a typed entity graph (`ontology_generator.py:203`, `graph_builder.py:407`) and produces structured simulated social actions (SQLite `trace`, `post`, `like` tables in `sim_run1/`); no observational timestamps, wallet or cross-token features |
| Decision/execution and stress compatibility (10) | 0 | No hooks; presents scenarios as predictions, the opposite of "no false price confidence" |
| Code quality, maintenance and tests (8) | 3 | 129 backend tests pass offline (Zep plumbing, barriers, sanitizer); active in October 2026; but no auth, tracebacks to clients, unseeded randomness, silent fallbacks, inconsistent Python bounds with its own dependencies (sections 2 to 4) |
| Integration fit and extensibility (8) | 2 | The unmodified simulation script runs as a subprocess in its own venv with JSON inputs and SQLite output (S6 role row); everything else needs Flask, Node, Zep Cloud, torch and Python <3.13 (memelab runs 3.13) |
| Experiment reproducibility and audit (8) | 1 | Per-run config, profiles, action logs and SQLite are saved (lineage of one run); identical inputs gave different outputs (S5), no seed parameter |
| Cost, latency and operational reliability (5) | 1 | `max_rounds`, `semaphore=30` and a report tool-call cap exist; no spend cap, LLM calls scale with agents times rounds times platforms, 610 MB for a 4-agent run, no resume, silent success when the LLM is down (S6, P30 rows) |
| Licensing, security and data rights (7) | 1 | AGPL-3.0 verified and usable for private isolated runs; AGPL PyMuPDF and GPL igraph transitively; unauthenticated API with reflected CORS on 0.0.0.0, default secret key, traceback disclosure; seeds sent to Zep Cloud and the LLM provider under terms not reviewed |
| **Total** | **10** | |

## 7. Flags

- RESEARCH_ONLY: cannot generate testable events by itself and has no independent empirical accuracy evidence. Any use is hypothesis generation whose outputs must be coded into pre-registered, falsifiable events by memelab (MIROFISH_EVALUATION.md two-stage gate).
- LEAKAGE_FAIL: cannot be configured for strict as-of operation. Pretraining knowledge of every LLM call (ontology, persona, config, each agent, ReportAgent) cannot be cut at a decision time (P26). For retrospective tests on 2026-10-07 to 10-23 decisions the contamination depends on the model's training cutoff; with any model trained after those dates the test is invalid.
- NOT_REALTIME: LLM-bound, minutes to hours per simulation at default scale; unsuitable for the discovery path.
- Not REJECT for isolated private research (license permits it, no malware or unsafe install seen); REJECT for in-process use, for copying code into memelab (P31, PI-D-005), and for running it as a reachable service with the shipped defaults.
- P27: agent agreement is not a probability. Agents share one model and one prompt template; in the smoke, 4 agents each acted on canned replies, so any "consensus" is a property of the model and the prompts. Even a frequency over many runs would be a frequency over simulator randomness, not a calibrated likelihood.
- P28, places where post-event information can enter seeds: (1) uploaded documents and the free-text `simulation_requirement` and `additional_context` (`api/graph.py:265-300`), no source date or as-of check; (2) Zep ingestion passes no source time, so the graph cannot tell when a fact became known (`graph_builder.py:470-485`); (3) persona prompts that ask the LLM to restore the real situation (`oasis_profile_generator.py:718`, `:734`, `:783`); (4) LLM-written initial posts and `narrative_direction` (`simulation_config_generator.py:648-719`); (5) simulated activity written back into the same graph (frontend default on), which later persona generation and the ReportAgent read without a filter, so one simulation's fiction becomes the next one's "facts" (`zep_graph_memory_updater.py:494`, `oasis_profile_generator.py:386`, `zep_tools.py:486`); (6) `interview_agents` answers generated by the same LLM.
- P26: every LLM stage above; the README's novel-ending demo is an example.
- P29: two identical runs already differ (S5), so persona or seed perturbations cannot be separated from run noise without many repetitions.
- P30: missing keys are refused at startup, but a failing LLM produces a normal-looking completed simulation.
- P31: AGPL root plus AGPL PyMuPDF and GPL igraph.
- P32: inspected the only sdists (`langdetect`, `docopt`); no unsafe install step found.
- P41: uploaded documents go straight into LLM prompts (ontology, persona, config), so a crafted document can steer every stage (prompt injection surface; not exercised).
- P42: section 5.
- P45: agents and the config LLM write new posts freely; nothing ties simulated content to a source.
- P48: no cost cap or circuit breaker.

## 8. Proposed role and integration decision

- Role: optional, offline hypothesis generator for Phase 14 and 15 only, behind the PLANNED_SEAMS "Behavioral simulation" boundary, default `SIMULATION_NOT_AVAILABLE`. Never a feature, score input or probability.
- Candidate INTEGRATION_DECISION: ISOLATED_RESEARCH. Viable isolation without copying source, shown in S6 and the offline example: invoke the unmodified `backend/scripts/run_reddit_simulation.py --config <json> --no-wait --max-rounds N` as a subprocess in its own venv (Python 3.11 or 3.12), inside a loopback-only network namespace, with JSON config and profiles written by memelab and the SQLite trace read back; tokenizer files pre-fetched; Reddit platform only (Twitter needs a model download). This path drops ontology, Zep graph, persona generation and the ReportAgent, which all need Zep Cloud and a paid LLM (not approved, PI-D-005). If an LLM simulation is ever approved, OASIS used directly (Apache-2.0, no Zep) does the same job with fewer obligations; see `camel-ai__oasis.md`.
- Requirements before any Phase 14 trial: per-run seed control added outside MiroFish (not possible without modifying its scripts, which would trigger section 13 duties if served), many repetitions per scenario, pre-registered outcome coding, blinded scoring, matched comparison against the LLM-free comparator (`mesa__mesa.md`) and abstention, and a model whose training cutoff precedes the evaluated events.
- Gap cells: N13 (PLANNED_SEAMS boundary "Behavioral simulation"); proxy cells CATALYST:MODEL_TRAINING and SOCIAL_SIGNALS:MODEL_TRAINING, where Phase 15 would test incremental value. It fills no model-training gap.
