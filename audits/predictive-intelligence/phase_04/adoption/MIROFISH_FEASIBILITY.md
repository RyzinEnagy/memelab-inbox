# MiroFish feasibility (Phase 04)

Status, kept separate from every forecast score: **MIROFISH_FEASIBILITY = ISOLATED_MOCK_ONLY**. A live run is BLOCKED (paid LLM and Zep Cloud are not approved, PI-D-005); in-process use, copying and serving are REJECT (AGPL-3.0, P31); the statistical engine does not depend on it in any way. Nothing here is a probability, an accuracy or an input to the 100-point score, and no number below may be read as one (P27).

Pin: `666ghj/MiroFish` at `7657031ac01184afe2cb220f5ee3545573b5e843` (Phase 02 and 03 pin; clone outside the repository, `git rev-parse HEAD` checked by the adapter before every run). Phase 03's source review is `phase_03/research/MIROFISH.md`; this file adds what Phase 04 measured.

## What was run

All runs on 2026-10-24, inside `unshare -n` (only a loopback interface, raised by `phase_03/.../lo_up.py`), no key, no Zep, no outbound connection. Command: `python -B prototypes/mirofish_adapter.py evidence/mirofish_adapter_runs.json` (exit 0; output sha256 `21bb03e8...`).

| Run | What it shows | Result |
|---|---|---|
| Backend `backend/run.py` started with no keys | P30 at the service level | exit 1; the program prints both `LLM_API_KEY` and `ZEP_API_KEY` as missing; no server started (`backend/app/config.py:64-70`, `backend/run.py:28-33`) |
| Script path, mock LLM, synthetic seed, run 1 | the only path that runs without paid services: MiroFish's own unmodified `backend/scripts/run_reddit_simulation.py` as a separate process in its own Python 3.12 venv, against the Phase 03 canned LLM on 127.0.0.1 | SIMULATION_RAN: exit 0, 8 LLM-generated actions (5 posts including the seeded one, 3 do_nothing, 1 like), 8 mock LLM requests, 9.8 s wall, 7.4 s CPU, children peak RSS 593 MB |
| Same seed, run 2 | determinism (P29) | SIMULATION_RAN with 9 LLM actions and 11 mock requests; trace sha256 differs from run 1 (`f5848ee2...` versus `5ae031ab...`) although the seed, the config and the mock (replies are a function of the request bytes) were identical |
| LLM endpoint down (no mock) | P30 silent success | the script exits 0 with only sign-ups, the seeded post and refreshes in its trace; the adapter reports SIMULATION_NOT_AVAILABLE with reason NO_LLM_ACTIONS instead of accepting the exit code |
| Paid route requested | approval boundary | the adapter answers NOT_SUPPORTED without starting anything |

The seed is fictional: four placeholder agents, one invented token name and one invented post. The profile strings exist only in a temporary directory during the run; the committed output holds counts and hashes, no profile or post text (content guard, PI-D-030).

## Runtime constraints (measured or read at the pin)

| Item | Fact |
|---|---|
| Python | `requires-python = ">=3.11,<3.13"` (`backend/pyproject.toml:5`); the lab runs 3.13, so MiroFish needs its own 3.12 interpreter and venv (here `/usr/bin/python3.12`, venv 1.4 GB with CPU torch 2.9.1, 132 packages in all) |
| Network | the script path needs only the LLM endpoint; it tries to download a tokenizer file unless `TIKTOKEN_CACHE_DIR` is pre-filled (Phase 03 attempt 1); the Twitter platform needs a Hugging Face model download; the full pipeline needs Zep Cloud (`ZEP_API_URL` for a self-hosted Zep is refused, `config.py:71-72`) |
| Keys | read from `.env` with `override=True` (`config.py:11-14`); the adapter refuses to run when a `.env` exists in the clone and builds the child environment from scratch, so no real key can be picked up |
| Exposure if the backend were used | Flask on `0.0.0.0` (`run.py:40`), CORS `*` on `/api/*` (`app/__init__.py:43`), default `SECRET_KEY` (`config.py:21`): never served on a reachable network |
| Cost controls at the pin | round truncation, a semaphore and `REPORT_AGENT_MAX_TOOL_CALLS=5` (`config.py:59`); no token budget, spend cap or breaker (P48). A live run would have to sit behind `runtime.CallGuard` with a cost cap |
| Cost with a real LLM (INFERENCE) | the 4-agent, 4-round mock run made 8 to 11 LLM calls; Phase 03's reading of the code puts a default 50-entity run at 1,000 to 2,000 agent calls per platform plus profile, config and report calls; no price is quoted because no paid run is approved |
| Determinism | none: same seed, different traces (above); the repository has no seed control (Phase 03 MI-1) |
| GPU | not needed for the Reddit script path (CPU torch) |

## AGPL obligations and the boundary

- Root `LICENSE` is AGPL-3.0 (Phase 03 MI-1, sha256 `8486a10c...`). The adapter (`prototypes/mirofish_adapter.py`) imports nothing from MiroFish, copies no file and runs the program unmodified as a separate process; it reads the SQLite trace the program writes. Whether a client of an AGPL program is a separate work is INFERENCE, not a legal opinion; running an unmodified copy privately carries no source obligation beyond keeping its notices, and section 13 would apply only to a modified copy served over a network, which this design never does.
- P31 gate: `runtime.copyleft_findings` with 5,393 winnowed fingerprints of the pinned MiroFish and black-it sources (hashes only, `tests/fixtures/predictive/copyleft_fingerprints.json`) finds 0 matches and 0 license markers in every code file of the working tree (411 at the repair commit: package, tests, tools, root scripts, every audits/ phase including the 27 prototypes and the copied skeptic scripts; two license-detection probes of Phases 02 and 03 hold the marker phrases as data and are exempt from the marker check only) and flags at least 80% of MiroFish's backend files when the pinned clone is present; `tests/test_predictive_runtime.py::test_p31_*` keeps it enforced.

## Adapter contract (sample)

The adapter returns one scenario document per run. Fields: `kind` = BEHAVIORAL_HYPOTHESIS_NOT_A_FORECAST, `engine`, `engine_pin`, `license_boundary`, `seed_sha256`, `fictional_seed`, `agents`, `rounds`, `script_exit_code`, `action_counts`, `llm_actions`, `trace_sha256`, `llm_requests_seen_by_mock`, cost fields, `status` (SIMULATION_RAN, SIMULATION_NOT_AVAILABLE or NOT_SUPPORTED) and `reason`. It asserts that no `probability`, `likelihood`, `confidence_pct` or `confidence` key is present, the same rule `contract.validate` applies to `behavioral_scenarios` (P27).

In the lab, `memelab/predictive/runtime.simulation_state` decides availability without reading any environment variable: SIMULATION_NOT_AVAILABLE unless `predictive.behavioral.approved` is the JSON value true, an adapter object is supplied, and the adapter's run reports a positive integer count of LLM-generated actions. Missing keys, an exhausted quota, an unreachable endpoint, a missing dependency, a `sys.exit` inside the adapter (MiroFish's service exits on missing keys), a malformed config and a silent exit 0 all end in SIMULATION_NOT_AVAILABLE with the statistical forecast unaffected; LLM actions count only as a positive int (tests P30, 27 cases after the repair pass, PI-D-035).

## What would have to change before Phase 14 or 15 could run MiroFish for real

1. Elving approves an LLM budget (Zep can be avoided on the script path) with a cap enforced by `CallGuard`.
2. An LLM whose training cutoff precedes every evaluated event (P26); otherwise retrospective runs are LEAKAGE_FAIL.
3. Seed control imposed from outside and many repetitions per scenario, because single runs are not reproducible (P29).
4. Pre-registered scenario coding and blind scoring against the LLM-free comparator (the numpy trader loop, BAKEOFF.md) and abstention (package MIROFISH_EVALUATION.md).

Until then Phase 14's expected outcome is BLOCKED or NO_GO, and the engine ships without behavioral simulation.
