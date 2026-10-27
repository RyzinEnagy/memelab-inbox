# Phase 15 GO / NO_GO

Decision computed by `memelab.predictive.scenario_eval.decide` from the recorded outputs (`INCREMENTAL_VALUE_RESULTS.json`, key `decision`), under the rule frozen before any coding or label read (`EXPERIMENT_PROTOCOL.md` section 10, PI-D-079).

| Item | Result | Reasons |
|---|---|---|
| Validation of the simulation question | **INSUFFICIENT_VALIDATION** | ELIGIBLE_EVENTS_BELOW_100 (actual N = 0 eligible, independently dated catalyst events; 100 required), D_NOT_RUN, B_NOT_RUN |
| MiroFish adoption | **MIROFISH_NO_GO** | the same three; adoption needs an evaluable, stable, budgeted MiroFish with a verified training cutoff before the evaluated events that beats every comparator out of sample after selection correction, and even then only as a prospective-only candidate |
| behavioral-rules-1 as a forecast input | **RULES_NOT_PROMOTED** | A_WARN NO_UNCORRECTED_SKILL on every target (E1: INSUFFICIENT_DAYS on T1 and T2, INSUFFICIENT_EVENTS on T1b) |
| Probability created | no | |
| Live capability created | no | |

## What this means

- The question "does behavioral simulation improve the forecast of the same outcome beyond simpler approaches?" is not answered by this data. It is not answered "no" by experiment either: MiroFish and the evidence-only LLM were not run, because no LLM, Zep or other paid spend is approved, and no catalyst event exists to run them on. MIROFISH_NO_GO is the conservative default the package prescribes when the module is weak or cannot be scored (NO_GO_DECISION_TREE): the optional module stays OFF and research-optional, and the statistical engine proceeds without it (ORCHESTRATOR.md, PI-D-078).
- A retrospective MiroFish or LLM evaluation on these dates (2026-10-06 to 2026-10-23) would not fix this even with spend: the lab cannot verify a hosted model's training cutoff or the absence of later retrieval, so the result would be EXPLORATORY_NOT_AS_OF (P26). A valid trial needs prospective, independently dated catalyst events with the simulation run committed before each outcome matures.
- The rule-based comparator that could be run without spend shows nothing an out-of-sample test can use (E1), nothing distinguishable from chance on development data after Holm (E2, descriptive only), and its one tempting development subgroup reverses on the opened holdout (E3, POST_OPENING). It stays a fallback descriptor, never a model input or a probability.
- This result cannot satisfy any live-release prerequisite (PI-D-078).

## What would reopen the question (all need Elving)

1. Catalyst and social rows the engine can read as of each decision (scheduled catalyst or social collection into a store, or an export of those tables), until at least 100 eligible, independently dated events exist on the prospective side.
2. An approved LLM budget, a named upstream for the Phase 14 meter only, change control, an LLM with a declared training cutoff before the evaluated events, filesystem isolation for the engine and a persistent spend ledger (Phase 14 conditions).
3. A pre-registered coder for MiroFish's free text, or a structured output path, and enough repetitions under the frozen seed and persona grid to judge stability.
4. A fresh protocol committed before any of those events mature.
