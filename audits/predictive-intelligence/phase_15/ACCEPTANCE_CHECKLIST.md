# Phase 15 acceptance checklist and pre-registration (written before any Phase 15 code, coding or label read)

Written 2026-10-27 from 00:50Z by the Phase 15 agent, after the entry gate at `b0243b4` (equal to `origin/feature/predictive-intelligence`; `git status` clean): package 41 of 41 checksums OK; full suite `python -m pytest tests -q -p no:cacheprovider` from 00:41:31Z gave `1 failed, 1807 passed, 1 skipped, 1 warning in 211.13s` (exit 1, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`), stray `data/reports/20261027_0041_BRETT_0x532f.md` removed by hand; seal check `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` exit 0 with `"problems": []`; Phase 14 key tests `tests/test_predictive_behavioral.py tests/test_predictive_phase14_outputs.py` 211 passed, 1 skipped; Phase 14's seed builder rerun into the scratchpad gives `SEEDS_DEV.jsonl` byte-equal to the committed file (830 seeds, 0 refused, sha256 `a0c61817...`, no label call, no socket); Phase 14 RESULTS.json TEST_ONLY; tracked `data/memelab.sqlite` sha256 `068287c0...`. Read first: START_HERE, EXECUTION_RULES, PHASE_INDEX, ORCHESTRATOR, the Phase 15 prompt, MIROFISH_EVALUATION, ADVERSARIAL_SCENARIOS, DATA_TIME_CONTRACT, SCIENTIFIC_VALIDATION, NO_GO_DECISION_TREE, HANDOFF, EXECUTION, ORCHESTRATION, ROADMAP (all known constraints), DECISIONS PI-D-001 to PI-D-077, Phase 14's checklist, results and interface, and the code of `behavioral.py`, `baselines.py`, `evaluation.py`, `labels.py`, `stats.py`, `contract.py`. Entry evidence: `evidence/entry/`.

The orchestrator's entry decision is PI-D-078 (Phase 14 TEST_ONLY admitted; no spend; the result cannot satisfy a live-release prerequisite). The frozen experiment rules are `behavioral/EXPERIMENT_PROTOCOL.md` and PI-D-079. This file, the protocol, `experiments/EXPERIMENT_REGISTRY.csv`, PI-D-078 and PI-D-079 are committed before any Phase 15 code is written, before any scenario is coded and before any label is read by Phase 15.

## Status rules carried in (not changed here)

- No LLM, Zep or MiroFish spend and no key (PI-D-005, PI-D-078). No vendor call, no Firecrawl, no language-model call; no socket at all in the Phase 15 probes.
- Labels only through `labels.training_labels` on the development store; `phase_06/sealed/` is never opened; the opened retrospective holdout is used only through the committed public `phase_12/validation/HOLDOUT_SCORED.csv` and only as a POST_OPENING description (PI-D-066).
- Behavioral output is never a probability, a calibration source, a model input or a score input (P27, PI-D-076). A_WARN is a research comparator, never published.
- New code is numpy plus `memelab.predictive` only, in `memelab/predictive/scenario_eval.py` (scenario-eval-1, flag OFF, imported by no other `memelab` module, imports neither `behavioral` nor the Phase 10 module, does not contain the Phase 10 module's name); probes in `phase_15/probes/` may import `behavioral` (as Phase 14's probes do).

## Gate items (each objectively checked)

| Item | Check | Pass when |
|---|---|---|
| G1 | package checksums | 41 OK |
| G2 | entry gate | suite only the known failure; seal problems []; Phase 14 key tests pass; seeds rebuilt byte-equal |
| G3 | pre-registration order | protocol, checklist, registry, PI-D-078 and PI-D-079 committed before the first commit holding `scenario_eval.py`; the frozen code committed before the recorded coding run; coding outputs committed before the scoring run; scoring code frozen before the recorded scoring run |
| G4 | isolation | `scenario_eval.py` imports only numpy, the standard library and `memelab.predictive` modules other than `behavioral`; no other `memelab` module imports it; the Phase 10 and Phase 14 isolation tests still pass |
| G5 | event count | the protocol 2 count over every listed source, with each candidate item and its reason in `EVENT_SET.csv`; the actual N recorded against 100 |
| G6 | blind coding | coding run with `training_labels` raising, sealed open raising, sockets raising: 0 label calls, 0 sealed opens, 0 socket events; the coder refuses an input with an outcome-like key (test); `CODING_LOG.json` hashes committed before scoring; the scorer refuses a coding file with another hash (test) |
| G7 | coding rules | one test per protocol 4 rule (NOT_CODABLE, statement, REFUSED_WINDOW, UNSCORABLE_NO_OUTCOME_SOURCE, NO_STATEMENT, the four warnings including CONFLICT); the Phase 14 MiroFish free-text output is NOT_CODABLE |
| G8 | rules reproduce | rerunning `rule_scenarios` on the 830 seeds with the committed creation time gives documents equal to `phase_14/behavioral/RULE_SCENARIOS_DEV.jsonl` (sha256 `15ccd5f1...`); every document validates; twin coding runs byte-equal |
| G9 | label join | every E1 row's `y` equals the `training_labels` label; E2 labelled counts equal the Phase 06 development counts (136, 224, 131); A_WARN training rows only decided before and matured by each cutoff (raises otherwise, test) |
| G10 | E1 scored with the frozen functions | `baselines.evaluate` and `verdict` for A_WARN against B0 and B2 per target, Holm over three, selection status; the restated B2, R2 and S2 numbers equal the Phase 10 SOCIAL_METRICS values for the same rows |
| G11 | E2 | protocol 6 measures and gates per target; permutation p reproducible from the seed |
| G12 | controls | NCB VERIFIED not flagged (or NCB_FAILED recorded); NCB UNVERIFIED all UNSCORABLE_NO_OUTCOME_SOURCE; NCS reported; P28 830 of 830 refused for both traps with no statement |
| G13 | E3 POST_OPENING | holdout seeds built and coded in the blind step; scored only from the public file; logged; `conservative_status` applied; nothing promoted |
| G14 | not compared, stated | B and D NOT_RUN with the blocking reason; P26 statement; P27, P29, P30 references |
| G15 | examples | the protocol 9 rule applied by code; examples written from its output |
| G16 | decision | `scenario_eval.decide` gives the result from the recorded inputs; tests for every branch, including a GO-candidate fixture and every NO_GO reason |
| G17 | tests bite | mutation probe on `scenario_eval.py`: every mutation caught (equivalent mutations recorded) |
| G18 | ledger | Phase 13's 3,206 rows unchanged at the head, every registry row present, totals recomputed by `evaluation.ledger_totals` |
| G19 | deliverables | `behavioral/EXPERIMENT_PROTOCOL.md`, `EVENT_SET.csv`, `SCENARIO_CODING.csv`, `INCREMENTAL_VALUE_RESULTS.md`, `GO_NO_GO.md`; evidence, RESULTS.json, skeptic packet, ROADMAP, DECISIONS, HANDOFF |
| G20 | post-commit | full suite (only the known failure), `python -m memelab social guard` 0 violations, seal check problems [], single-branch `python tools/release_audit.py --history` exit 0; `git status` clean |

Status rule: if every item holds, Phase 15 is TEST_ONLY (protocol 12): the comparison that can be made without spend is valid and the decision is conservative, but the simulation comparators were not run, so the phase cannot be a release-complete PASS of the simulation question and cannot satisfy a live-release prerequisite (PI-D-078). A failed item makes it FAILED or NEEDS_REVIEW with the item named.

Counterexample named in advance (CX-15, the agent's own, not independent): a scorer that counts a bogus planted catalyst's CATALYST_FOLLOW_THROUGH statements as hits whenever T1 happens to be positive, and reports the hit count over all positives (recall) as "warning accuracy". On a T1 prevalence near 25% and a planted half, this reads as "half of all pumps were warned" and looks like signal. Caught when: precision is always compared with the prevalence on the same rows (lift) under the day-stratified permutation null, and NCB must come out not distinguishable; recall is reported beside coverage, never alone.
