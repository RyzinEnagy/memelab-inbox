# mesa/mesa (reviewer R5)

Classic, LLM-free agent-based modeling framework. Reviewed for one question: can a cheap, deterministic trader-reaction model built on it serve the behavioral-hypothesis role (Phase 14 and 15 comparator against LLM simulation and abstention)? Mesa ships no market model; everything market-specific in the smoke below was written for this review and is synthetic.

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | mesa/mesa, https://github.com/mesa/mesa (the seed URL projectmesa/mesa serves the same HEAD, Phase 02) |
| Pinned SHA | `949dc8c5c6b75092364f4052233a39ef5612c8fc` ("Fix the rng docstring of Scenario.from_dataframe and from_ndarray (#3964)"), equal to the remote HEAD at review time |
| Commit date | 2026-10-22T15:51:53+02:00 (2026-10-22T13:51:53Z) |
| How fetched | `git fetch --depth 1 origin <sha>` into `/home/claude/pi_research/src/mesa__mesa` (5.6 MB), 2026-10-24T04:33Z |
| Review time (UTC) | 2026-10-24T04:55Z to 05:30Z |
| Version tested | the pinned tree on `PYTHONPATH`, `mesa.__version__` 4.0.0a0 (main branch after tag `v4.0.0a0` `d07108ed`); Python 3.13.17 with numpy 2.5.4, pandas 3.1.0, scipy 1.18.1, tqdm 4.70.1, networkx 3.7 (`SMOKES/mesa__mesa/venv_freeze.txt`) |
| Venv and clone | venv `/home/claude/pi_research/venvs/mesa__mesa` (254 MB) kept; clone at `/home/claude/pi_research/src/mesa__mesa` |
| Relation to releases | PyPI latest is 3.5.1 (2026-03-15, `mesa-3.5.1-py3-none-any.whl`, requires Python >=3.12); the pin is an unreleased 4.0 alpha. 3.5.1 was not tested |

## 2. License and security

| Item | Finding |
|---|---|
| Root license | Apache-2.0, `LICENSE` sha256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` (matches Phase 02); `NOTICE` "Copyright 2014-2024 Core Mesa Team and contributors" |
| Transitive licenses (core) | numpy BSD-3-Clause (plus 0BSD, MIT, Zlib, CC0 parts), pandas BSD-3-Clause, scipy BSD, tqdm MPL-2.0 AND MIT, networkx BSD-3-Clause (optional). Visualization extras (solara, altair, matplotlib) not installed or needed |
| Model weights | none |
| Install-time scripts | none run: source used from the clone; dependencies installed with `--only-binary :all:` |
| Network | no `requests`, `urllib`, `socket` or `subprocess` in `mesa/` core; tests and smoke ran inside a loopback-only namespace without errors |
| Telemetry | none found |
| Secrets | none handled |

## 3. Code paths inspected at the pin

| Concern | Anchor |
|---|---|
| Model and seeding | `mesa/model.py:44` `Model`; `:85-129` `__init__(rng=..., scenario=...)`: `self.rng` is a numpy `Generator` from the scenario and `self.random = random.Random(scenario._stdlib_seed)`; `rng=None` means an unseeded run |
| Agents | `mesa/agent.py:23` `Agent`, `:87` `create_agents`; `mesa/agentset.py:565` `AgentSet`, `:710` `shuffle_do` (shuffles with the model's own RNG), `:1047` `GroupBy` |
| Time | `mesa/model.py:323` `schedule_event`, `:367` `schedule_recurring`, `:391` `run_for`, `:400` `run_until`; `mesa/time/events.py:67` `Event`, `:182` `Schedule`, `:429` `EventList`: events at arbitrary float times, so irregular event times can be simulated. This is simulation time; Mesa has no notion of data availability time |
| Replications and run store | `mesa/experimental/scenarios/scenario.py:70` `Scenario`, `:246` `spawn_replications` (child seeds from `SeedSequence.spawn`), `:231` `to_dict`; `experimental/scenarios/store.py` run records with PENDING, SUCCEEDED, FAILED, ABORTED status, in memory only (`InMemoryStore`) |
| Output | `mesa/datacollection.py:47` `DataCollector`, `:370` `collect`, `:435` `get_model_vars_dataframe` |
| Calibration or uncertainty | none |
| Serialization | none built in for models; reproducibility is parameters plus seed (`Scenario.to_dict`) |
| Tests | 35 Python test files, 827 test functions. Ran 8 core files (model, agent, agentset, datacollector, scenarios, events, schedule run, discrete space) offline: 411 passed, exit 0, 11 s (`SMOKES/mesa__mesa/mesa_pytest_offline.txt`) |

## 4. Smoke results

`SMOKES/mesa__mesa/smoke_mesa_traders.py` on the shared challenge (`challenge.csv`, sha256 `18fda40c...5f23d`). For each holdout decision row a market of 20 traders (8 momentum, 5 contrarian, 4 noise, 3 take-profit exiters, heterogeneous thresholds and sizes) reacts to one signal for up to 12 steps; price moves by net demand divided by log10 of liquidity plus noise. A run "hits" if the synthetic price touches +25% before -15%. The share of 5 seeded runs that hit is the simulator frequency. That frequency is over simulator randomness; it is not a calibrated probability (P27), and the scores below only show what happens if someone treats it as one. 527 scored holdout rows, 107 censored rows excluded, train prevalence 0.04238. Exit 0, 9 s wall, inside a loopback-only namespace (`smoke_mesa_traders_output.json`).

| Smoke | Result | Numbers |
|---|---|---|
| S1 leak trap | FAIL (nothing stops it) | signal `ret_1h` (legitimate): Brier 0.03461, log loss 0.35861, AUC 0.5878; signal `leak_future_ret` (TRAP): Brier 0.02171, log loss 0.18953, AUC 0.8082; baseline Brier 0.03132, log loss 0.14388. Mesa accepts any number as an agent input; the as-of view (PLANNED_SEAMS) must do the filtering |
| S2 probability shape | PASS (shape), worse than baseline | all values finite in [0, 1]; only 3 distinct values {0.0, 0.2, 0.4} with 5 seeds; the legitimate version loses to the train-prevalence baseline on both Brier and log loss |
| S3 missing covariates | FAIL (silent) | 30 holdout rows with NaN `liq_usd`: the price path becomes NaN, no barrier is ever touched, every such row silently scores 0.0; imputation (train median) required |
| S4 calibration or uncertainty | none offered | mean frequency 0.0285 versus observed 0.0323; reliability: 460 rows with frequency 0.0 have observed rate 0.0261, 67 rows with mean frequency 0.2239 have observed rate 0.0746 (miscalibrated, as an uncalibrated simulator should be) |
| S5 persistence and determinism | PASS | same seeds: byte-identical frequency vector (sha256 `61cd4e71...`); different seeds: different vector. No model artifact to save; parameters plus seed reproduce the run |
| S6 cost | PASS | 13,175 model runs in 8.27 s; 0.779 ms per run (20 agents, up to 12 steps); peak RSS 101.6 MB; no network at import or run; Python 3.13 tested; pure-Python wheel on PyPI (3.5.1), so Windows is covered by the dependencies' wheels (not run on Windows) |
| Role: LLM-free behavioral model | PASS (feasibility) | deterministic with a seed, about 1 ms per scenario run, no pretraining knowledge to leak (P26 does not apply), outputs are testable events (barrier hit or not) that Phase 15 can score against abstention and the LLM simulator |

## 5. README or docs claims the code does not support (P42)

No quantitative claims in README.md that the code could fail; "state-of-the-art" wording only (README.md:26). Nothing marked UNSUPPORTED. The `experimental` package is labelled experimental by the project and its API may change.

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity and leakage safeguards (18) | 2 | No pretrained knowledge and output depends only on supplied inputs and seed (S5), so the P26 channel is absent; but no availability-time or split mechanism, and the trap passes straight through (S1) |
| Transferable measurable predictive outcomes (14) | 2 | A user-written model produces per-decision testable binary events scored with Brier and log loss (S2); the library itself supplies no outcome model, and the smoke model has no skill over the base rate |
| Calibration, uncertainty and abstention (12) | 1 | Seeded replications (`scenario.py:246`) give a Monte Carlo spread over simulator noise; no calibration, intervals or abstention (S4) |
| Catalyst/social/on-chain features (10) | 2 | Event scheduling at arbitrary float times (`model.py:323-400`, `time/events.py`) and heterogeneous agent sets; no domain features shipped |
| Decision/execution and stress compatibility (10) | 1 | Liquidity-scaled price impact can be modelled (smoke), nothing provided |
| Code quality, maintenance and tests (8) | 6 | 411 offline tests pass on Python 3.13; commit two days before review; long release history; pin is a 4.0 alpha with experimental modules |
| Integration fit and extensibility (8) | 6 | Pure Python on numpy, pandas, scipy, tqdm; Python 3.13; Apache-2.0; in-process or isolated use both possible; it would be a new subsystem only inside the planned behavioral boundary |
| Experiment reproducibility and audit (8) | 6 | Seeded `rng` and `random` (`model.py:128-129`), byte-identical reruns (S5), `SeedSequence` replications, `DataCollector`; run store is in memory only |
| Cost, latency and operational reliability (5) | 5 | 0.78 ms per run, 102 MB, offline, no LLM or paid service (S6) |
| Licensing, security and data rights (7) | 7 | Apache-2.0 verified with NOTICE; permissive core dependencies; no network, telemetry or secrets (sections 2 and 4) |
| **Total** | **38** | |

## 7. Flags

- RESEARCH_ONLY (for any model built on it): a framework has no empirical accuracy; a trader-reaction model must earn a role in Phase 15 against abstention and simple baselines.
- Not LEAKAGE_FAIL: Mesa reads no data by itself, so strict as-of operation is achieved by feeding it only as-of features; S1 shows it will not stop a leak, so the wrapper's cutoff view is mandatory.
- Not NOT_REALTIME: about 1 ms per scenario run.
- P13: S1 is the in-miniature version: a model fed a feature from after the decision looks much better (AUC 0.81 versus 0.59).
- P27: simulator frequencies are not probabilities; S4 shows a 0.22 simulated frequency next to a 0.07 observed rate.
- P29: with a seed, perturbation effects can be separated from run noise (S5), which the LLM simulators cannot offer.

## 8. Proposed role and integration decision

- Role: the LLM-free behavioral comparator for Phases 14 and 15 (MIROFISH_EVALUATION.md asks for a rule-based narrative and non-simulation comparator): a small seeded trader-reaction model whose parameters can be fitted offline (see `bancaditalia__black-it.md`) and whose outputs are pre-registered barrier events, scored against abstention and B0 to B4. Expected outcome on 17 days of data: no skill over the base rate, which is an acceptable result.
- Candidate INTEGRATION_DECISION: INSPIRED_IMPLEMENTATION first (the trader model needs only a numpy loop, as the 16-line `trader_model` in `SMOKES/bancaditalia__black-it/smoke_blackit_calibrate.py` shows, matching the "numpy first" rule in PLANNED_SEAMS), with ADAPTER on a released Mesa (3.5.x, re-tested in Phase 04) if agent heterogeneity, event scheduling or replication management grows beyond that. Either way it stays outside the core package, flag OFF.
- Gap cells: N13 (PLANNED_SEAMS "Behavioral simulation"); proxy cells CATALYST:MODEL_TRAINING and SOCIAL_SIGNALS:MODEL_TRAINING for the Phase 15 incremental-value test.
