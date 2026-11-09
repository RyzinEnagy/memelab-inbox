# Release decision: Memecoin Predictive Intelligence Engine

Date: 2026-11-09. Branch `feature/predictive-intelligence`, pushed head `90e4c6f` (checked against GitHub with `git ls-remote` at 22:20:55Z), release checks at `b048aac` (the pushed head plus five files under `phase_21/`, nothing else). Decided by the Phase 21 agent on the evidence below, NEEDS_REVIEW until the orchestrator's independent skeptic has run. Paths are relative to `audits/predictive-intelligence/`.

## Decision

| Scope | Classification | Decision |
|---|---|---|
| The engine as it is: a research-only abstention engine behind a flag that is OFF by default; every forecast ABSTAIN with named reasons; B0 and B2 kept as internal references, never shown | RESEARCH_BASELINE_ONLY (read as "research-only release, flag OFF, abstention engine") | GO, for what is proven: install, run the checks, turn the flag on in a sandbox, read the abstentions |
| Any predictive release: a probability shown to a user, a SHADOW or VALIDATED_EXPERIMENTAL model, an ensemble | NOT_READY | NO-GO: no registry entry is at SHADOW or above, no target is calibrated, no out-of-sample edge exists (NO_INCREMENTAL_PREDICTIVE_EDGE) |
| Combined prediction plus backtest stress | NOT_READY | BACKTEST_NOT_AVAILABLE (PR #4 not merged) |
| Behavioral simulation (MiroFish) | MIROFISH_NO_GO, INSUFFICIENT_VALIDATION | OFF, research-optional, never a probability |
| Turning the flag on outside a sandbox, alert delivery, merges, spend | not decided here | waits on Elving (`OPEN_DECISIONS.md`) |

Not claimed: skill, edge, calibration, profit, an executable fill, a regime result. Nothing is pushed, merged or deployed by this decision.

## The five checks of ORCHESTRATOR item 8

| Check | Result | Evidence |
|---|---|---|
| Real clean-environment system run | PASS: fresh clone of the pushed branch from GitHub, new venv (numpy 2.5.3, pytest 9.1.1 and its four dependencies, nothing else), every check under `env -i` (only HOME, LANG, LC_ALL, PATH and one marker variable inside) and `unshare -n`. Full suite 2 failed (the two known clock tests), 2,239 passed, 5 skipped (3 need node, 1 jsonschema, 1 IPv6 loopback); predictive tests with the private stores hidden 1,453 passed, 7 skipped, 0 failed; release_e2e exit 0; real-path smoke on the `71fc50e` export: 8 opportunities attempted, 24 documents, 24 ABSTAIN, 0 forecast lines, 16 duplicates on rerun and retry, storm one attempt, `check_state` problems [] for all four states | `evidence/release_checks/` (`logs/steps.jsonl`, `suite_full_tail.txt`, `suite_predictive_no_stores_tail.txt`, `e2e/`) |
| Strict chronology audit | PASS with deviation D21-1: registry cutoffs hold for 69 of 69 entries, the log replays, 69 of 69 MODEL_STALE at 2026-11-09, no champion; 198 prospective predictions all cut off before their decisions; ledger verifies, no outcome before its prediction set, no LABELED before maturity; every checklist of phases 05 to 20 committed no later than its results; 5 of 5 planted violations caught; Phase 19 predictions commit before the first label call; seal intact; chronology scenarios P05, P06, P07, P13, P20, P36, P43 pass. D21-1: P04 (a crawled page describing an older event) is TEST_ONLY, not PASS: no crawl source feeds the engine, so the guard is proved on fixtures only (3 of 3 assertions); the checklist row did not foresee this class | `evidence/release_checks/chronology_audit.json`, `p19_audit/FEEDBACK_AUDIT.json`, `seal_check.json`, `matrix/SCENARIO_MATRIX.csv` |
| Positive and negative integration | PASS: cross-component tests 43 passed; 48 scenarios, 239 of 239 gating assertions, results 25 PASS, 10 PASS_EXPECTED_ERROR, 12 TEST_ONLY, 1 PASS_WITH_PROBE_FINDING (P46, finding F20-07), identical to Phase 20's last run; 39 of 39 counterexamples caught; flag-off identity on two real exports and six configs all identical; two real event traces hold; collector outage (P47) and absent credentials degrade to visible abstention | `evidence/release_checks/cross_component.txt`, `matrix/`, `cx/`, `flag_off_identity.json`, `independent_recalc.json` |
| Out-of-sample test | PASS as a check, result negative: rerun identical to Phase 20 (0 differences); no target shows out-of-sample value over the base rate; T1 and T1b NOT_DISTINGUISHABLE on the spent retrospective holdout, T2 INSUFFICIENT_EVENTS; prospective INSUFFICIENT_DAYS for all three; UNCALIBRATED for all three. This passes the release of an abstention engine and blocks any predictive release | `MODEL_LIMITS.md`, `evidence/release_checks/oos_sensitivity.json`, `independent_recalc.json` |
| Safety and security | PASS: threat scan equal to Phase 20's apart from head and its own output file (no copyleft, no key, signing or order path in the package, no schedule, no import beyond numpy and the standard library, no dependency manifest change); release audit with history on a single-branch clone exit 0, "Needs action: no."; social guard 0 violations; no network in any check; no `data/config.json` in the tree; spend 0 | `evidence/release_checks/threat_scan.json`, `e2e/release_audit_history.txt`, `social_guard.txt`, `logs/env_names_inside.txt`, `../COST_LEDGER.md` |

Reproductions (every committed output of Phases 05 to 19 rerun in a sandbox): see `SMOKE_LOG.md` and `evidence/release_checks/reproductions.json`.

## Evidence for each statement about what exists

| Statement | Evidence |
|---|---|
| Research-only abstention engine, numpy core, imported only by two helpers in `memelab/cli.py` | `phase_17/` (PI-D-093), flag-off import traces in `evidence/release_checks/flagoff/imports/*.imports.json` |
| Flag OFF by default; anything but the JSON value true is OFF | `memelab/cli.py` `_predictive_enabled`, `flag_off_identity.json` (six configs) |
| Every forecast ABSTAIN | `e2e/smoke_summary/REAL_PATH_SMOKE.json` (24 of 24), `evidence/doc_commands/private/report.md` ("Probabilities shown: 0 of 24") |
| No validated or shadow model; no ensemble | `phase_16/registry/` (69 entries, NO_VIABLE_CHAMPION x3), `phase_16/ensemble/ENSEMBLE_ABLATION.json`, `chronology_audit.json` C1 |
| MiroFish NO_GO | `phase_15/PHASE_15_EVIDENCE.md`, PI-D-081 |
| Backtesting not merged: BACKTEST_NOT_AVAILABLE | `phase_17/integration/REQUEST_FLOW.md`, every request record in the smoke state |
| Model artifact versions | registry entries carry card file sha256, model sha, feature set sha, labels version and code-file hashes; `tests/fixtures/predictive/phase18/PINNED_SHA256.json` pins the lab modules |
| Source data and rights | `phase_05/data/SOURCE_COVERAGE.md` ("Terms and rights" column): the lab's own state exports and collector files, GeckoTerminal free public OHLCV (no key), DEX Screener only as current state; no social content in the store |
| License review | `phase_03/research/LICENSE_AND_SECURITY_GATE.md`, `phase_04/adoption/INSTALL_DECISION.md`; no third-party code copied; copyleft gate over 5,393 fingerprints (`threat_scan.json` copyleft_gate []) |
| Operational cost, latency, memory | `SMOKE_LOG.md`; spend 0 for the whole initiative's Phase 21 |

## Blockers to a predictive release, with owners

| Blocker | Owner | Path out |
|---|---|---|
| Promotion closed under the frozen ACCEPTANCE table (PI-D-091) | Elving | ED-1: a change control before new prospective labels are read |
| Too little prospective evidence (3 decision days; minimums 5 days, 50 events, 10 per class) and stale reference cards | Elving (decision), next phase (work) | retrained references from a committed plan, then weeks of decisions |
| No calibration card passes | follows from the above | prospective out-of-sample evidence only |
| No execution data | Elving | ED-4: deploy the forward depth collector |
| No catalyst or social data | Elving and the social-intel and catalyst owners | ED-3 |
| Backtesting not merged | Elving | ED-5 |

## Open items carried

OI21-1 (7 PENDING T2 outcomes need a `fetch_labels.py` change), F20-07, F20-10, F20-11 (closed by the runbook), F20-13, F20-14: each with its recommendation in `OPEN_DECISIONS.md`.

## Sign-off

Phase 21 agent, 2026-11-09. Status NEEDS_REVIEW pending the orchestrator's independent skeptic (PI-D-013). The decision above is final only for the scope it names; any change to what is shown to a user needs the decisions listed in `OPEN_DECISIONS.md`.
