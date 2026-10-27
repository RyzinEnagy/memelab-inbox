# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-077). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_14/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position on 2026-10-27

- Phases 00 to 13: PASS (Phase 13 after repair pass 2, PI-D-070; G7 closed by PI-D-071).
- Phase 14 (isolated behavioral-simulation interface): **TEST_ONLY** after repair pass 2 (PI-D-076, PI-D-077). MIROFISH_GATE BLOCKED for live use until Elving approves LLM spend. The orchestrator's independent skeptic found 5 MATERIAL findings and 6 minor (counterexample CX-S14, a monitor that reverses with the seed while the label stays); all repaired at `69a3584` with tests that fail on the first-pass code; the recorded run was repeated with no status, rule count or verdict change. The statistical-engine-unaffected item and the safety items PASS.
- Spend: 0 Firecrawl credits, 0 vendor calls, 0 language-model calls, no key. Network: one `git ls-remote` of MiroFish; every other socket was loopback.

## What Phase 14 did (PI-D-072 to PI-D-077)

- Rules frozen before any code or real seed (`phase_14/ACCEPTANCE_CHECKLIST.md`, `9ed8377`), then two recorded stricter changes before the frozen code: the meter charges call body bytes (characters / 4 would undercount MiroFish's Chinese prompts) and external engines run only in a network namespace (PI-D-073); the seed converter moved out of `memelab/` and three narrow release-audit entries were added for the refusal words, with unchanged findings elsewhere (PI-D-074).
- `memelab/predictive/behavioral.py` (behavioral-1, standard library, flag OFF, imported by no other module): loopback-only `ServiceAdapter` and `SubprocessAdapter` (environment from scratch, always inside `unshare -n`, timeouts, retries, breaker), approval plus `ON_DEMAND_LOCAL` plus kill switch, `check_seed` (post-decision detail, outcome fields, dates, injection, secrets, URLs, behavioral feedback), `code_response` (vocabulary codes only, grounding, wallet and identity claims dropped and counted), the fictional `behavioral_scenario/1` document and `validate_scenario` (no probability-like key, floats only in cost fields), `stability` (frozen grid of 3 seeds by 2 persona sets, repeat, degraded and no-evidence runs), `cost_plan` and `LLMMeter` (pre-call ceiling, cap, max_tokens, prompt and body caps, call cap, breaker, kill switch, fail closed on usage above charge), `forecast_entries` (strings only) and `rule_scenarios` (behavioral-rules-1).
- Repair pass 2 (PI-D-076): capped, refused and tripped runs carry `llm_actions` 0 (never AVAILABLE); the meter refuses `n`, `stream` and keys outside an allowlist, meters usage per call and stops without usage; one hypothesis per label; every subprocess inside `unshare -n`; stability on label plus monitor direction (MONITOR_REVERSED); wider date, wording and normalized injection checks; fixed vocabularies for reasons, flags and claim keys.
- Tests: `tests/test_predictive_behavioral.py` (204 passed, 1 skipped for IPv6) and `tests/test_predictive_phase14_outputs.py` (7); mutation probe 83 of 83 at the repair code.

## Result

- Rules on 830 development seeds: ATTENTION_EXHAUSTION 309, MANUFACTURED_ATTENTION_DUMP 313, ORGANIC_ATTENTION_CONTINUATION 66, NO_GROUNDED_SCENARIO 227; 0 catalyst hypotheses (no catalyst rows exported); deterministic; unscored.
- Mock grids: STABLE mode STABLE; seed-sensitive, persona-sensitive, non-reproducible, evidence-blind and monitor-reversal (CX-S14) modes UNSTABLE with their flags, on a fictional and on a real seed.
- 45-case failure matrix: AVAILABLE exactly when SIMULATION_RAN; every failure with its reason; gates make no request. Subprocess children in their own namespace reached nothing (`NETNS_EGRESS.json`).
- Cost: worst case refused with 0 calls; meter stops at its cap; breaker after 5 upstream failures; `n`, `stream` and unlisted keys refused with nothing forwarded.
- MiroFish 7657031a through the boundary: SIMULATION_RAN but NOT_CODABLE (free text), stopped by a low meter cap, NO_LLM_ACTIONS when its LLM is down (exit 0), same-seed traces differ.
- Core: Phase 13's runner unchanged with the behavioral module blocked.

## Open items, in order

1. The orchestrator re-verifies Phase 14 (TEST_ONLY) and pushes.
2. Phase 15 entry: its gate asks for PASS from Phase 14; with a TEST_ONLY Phase 14 the orchestrator or Elving decides. Phase 15 has comparator A (`behavioral.rule_scenarios`, real seeds in `phase_14/behavioral/SEEDS_DEV.jsonl`), B and D BLOCKED without spend, C UNCALIBRATED; expect INSUFFICIENT_VALIDATION or BLOCKED for the simulation question.
3. Before any live behavioral run (Elving): a budget, a named upstream for the meter only with change control, an LLM with a declared training cutoff before the evaluated events, filesystem isolation for the engine, a persistent spend ledger, a pre-registered coder for free text.
4. Carried from Phase 13: Phase 16 sets levels and cannot promote from the retrospective holdout; Phase 17 calls `abstention.forecast_result` and `validate_publication`, keeps the raw model number, recomputes the published point and validates every document with its record; Phase 19 supplies prospective evidence; champion cards MODEL_STALE after 2026-10-31; catalyst and social tables are not exported; forward depth collection approved but not deployed (PI-D-044).

## Phase 14 commits

- First pass: HEAD before `2fd0aae`; pre-registration `9ed8377`; frozen code `c59c494`; recorded run `872578d`; records `bf06b87`; post-commit record `58bee5d` (pushed, reviewed by the skeptic).
- Repair pass 2: code `69a3584` (frozen before the repeated run), outputs and records on top, post-commit record after that (local only; the orchestrator pushes). Post-commit results: `phase_14/postcommit/rp2_*`.

## Waiting on Elving

- Any paid data, LLM, Zep or MiroFish use (the Phase 14 boundary is ready for a mock-only protocol); social API credentials or consent; scheduled catalyst or social collection into a store this engine can read; research packages in the lab's runtime; a merge into `main`; deploying the forward depth collector (approved, PI-D-044; not yet done).

## Note outside this branch

The release audit on a full local clone flags a history blob reachable only from `origin/feature/backtesting` (a reviewed false positive on that branch, D-BT-016; PI-D-049 item 6). It is not reachable from `feature/predictive-intelligence`, whose own audit passes on a single-branch clone.

## Lab rules that still bind

Research only: no trades, no wallets with signing authority, no seed phrases or private keys, no credentials printed or committed. No change under `inbox/`, `state/` or `data/` on this branch. Existing 100-point score and fatal-flag overrides unchanged. Forecasts stay a separate evidence section with the flag OFF. No raw social content in the repository. Behavioral output is fictional, never a probability.

## Exact next commands

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox
git checkout feature/predictive-intelligence && git log -12 --oneline
pip install pytest
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -m pytest tests -q
python -m pytest tests/test_predictive_behavioral.py tests/test_predictive_phase14_outputs.py -q
python -B audits/predictive-intelligence/phase_14/probes/build_seeds.py /tmp/p14
python -B audits/predictive-intelligence/phase_14/probes/run_behavioral.py /tmp/p14 --skip-mirofish
```

Expect `"problems": []` from the seal check and only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` failing in the suite; then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand. The seed builder needs the Phase 05 store under `/home/claude/pi_research/` (rebuild it from the committed archives if the workspace was reclaimed: `phase_05/data/FEATURE_STORE_CONTRACT.md`); the MiroFish part of the runner needs root, the MiroFish venv and clone, and a tokenizer cache.
