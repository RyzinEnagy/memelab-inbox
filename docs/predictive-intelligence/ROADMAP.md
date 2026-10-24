# Predictive Intelligence: roadmap

Contract: [EXECUTION.md](EXECUTION.md). Choices: [DECISIONS.md](DECISIONS.md). Current position: [HANDOFF.md](HANDOFF.md). Source: the package's PHASE_INDEX.md (canonical order 00 to 21, never lexical) and each `phases/PHASE_XX_*.md`. Evidence per phase: `audits/predictive-intelligence/phase_XX/`.

Status values: PASS, NEEDS_REVIEW, TEST_ONLY, BLOCKED, FAILED, NOT STARTED.

Every gate also includes the standing gate: package checksums verified, predecessor gate re-run independently, full suite run and recorded with no new failure, no stray files, nothing written under tracked `inbox/`, `state/`, `data/`, an independent skeptic's new counterexample recorded, HANDOFF.md rewritten, local commit made.

| Phase | Objective (from the phase prompt) | Entry gate | Deliverables and phase gate (from the phase prompt) | Status |
|---|---|---|---|---|
| 00 | Audit the actual lab and establish an executable baseline | none | `baseline/REPO_MAP.md`, `FEATURE_TRACE.md`, `COMMIT_AND_TEST_LOG.md`, `DATA_COVERAGE.md`, `EXISTING_PREDICTION_INVENTORY.md`; pinned HEAD, successful evidence commands or explicit blocker | NEEDS_REVIEW (2026-10-24): every baseline item reproduced; the independent skeptic could not be started inside the phase run (PI-D-009). Orchestrator runs it from `audits/predictive-intelligence/phase_00/SKEPTIC_PACKET.md` |
| 01 | Freeze measurable prediction objectives and the minimally invasive architecture | PASS from 00 | `architecture/GAP_MATRIX.csv`, `PLANNED_SEAMS.md`, `TARGET_REGISTRY.md`, `ACCEPTANCE_METRICS.md`, `DEPENDENCY_GRAPH.md`; objective, labels and placement pre-registered with no duplicate subsystem | NOT STARTED |
| 02 | Broad, verifiable, diversified discovery of prediction tools | PASS from 01 | `research/SEARCH_LOG.md`, `CANDIDATES.csv` (at least 45 unique verified), `SHORTLIST.csv` (at least 20), `EXCLUSIONS.md`; audited reproducible query corpus | NOT STARTED |
| 03 | Inspect candidate code, score and rank the strongest transferable repos | PASS from 02 | `research/REVIEWS/*.md` (at least 20), `SCORECARD.csv`, `RANKED_TOP10.md`, `CATEGORY_WINNERS.md`, `LICENSE_AND_SECURITY_GATE.md`, `INDEPENDENT_RESCORE.md`; reproducible evidence-backed top ten | NOT STARTED |
| 04 | Choose libraries through isolated comparisons and lawful integration plans | PASS from 03 | `adoption/BAKEOFF.md`, `INSTALL_DECISION.md`, `BOM_LOCKS.md`, `MIROFISH_FEASIBILITY.md`, isolated prototypes; executable choice and lawful, budget-aware fallback | NOT STARTED |
| 05 | Provenance-preserving point-in-time feature storage without leakage | PASS from 04 | `data/FEATURE_STORE_CONTRACT.md`, additive migration and rollback, `tests/test_predictive_asof_*.py`, source coverage report, frozen fixture snapshot; executable as-of invariants | NOT STARTED |
| 06 | Time-correct, economically meaningful labels and cohort coverage | PASS from 05 | `labels/TARGET_SCHEMA.md`, `COVERAGE_CENSORED_REPORT.md`, code and tests, hand-checked event trace; mature-only training labels | NOT STARTED |
| 07 | Weak and simple honest predictors first | PASS from 06 | `models/BASELINE_SPEC.md`, `experiments/BASELINE_METRICS.csv`, train-only artifacts, serialization smoke; actual baseline numbers or explicit insufficient-evidence stop | NOT STARTED |
| 08 | Price-structure and event classifiers beyond baselines | PASS from 07 | `models/TECHNICAL_MODEL_CARD.md`, code, run manifest, OOS vs baseline tables; genuine trained model or explicit no-go | NOT STARTED |
| 09 | Prospective liquidity, execution capacity and distribution risk | PASS from 08 | `models/ONCHAIN_LIQUIDITY_CARD.md`, source ledger, temporal features, tests, comparison with simple rules; honest data sufficiency | NOT STARTED |
| 10 | Response to verified narratives and catalysts without future text | PASS from 09 | `models/CATALYST_MODEL_CARD.md`, `data/CATALYST_PROVENANCE.md`, adapter tests, ablations; no social leakage | NOT STARTED |
| 11 | Low-history opportunities through analog cohorts and regimes | PASS from 10 | `models/ANALOG_MATCHING_SPEC.md`, cohort query, coverage validation, abstention and OOD tests; no survivorship or time contamination | NOT STARTED |
| 12 | Defensible OOS evaluation and search discipline | PASS from 11 | `validation/WALK_FORWARD_PROTOCOL.md`, `FULL_EXPERIMENT_LEDGER.csv`, `FINAL_HOLDOUT_RESULTS.md`, scripts and model SHAs; protected holdout, no future-trained replay | NOT STARTED |
| 13 | Calibration, uncertainty and abstention | PASS from 12 | `models/CALIBRATION_CARD.md`, schema tests, reliability and coverage table, abstention matrix, calibrated artifact; no unsupported numeric confidence | NOT STARTED |
| 14 | Isolated behavioral-simulation interface, only if feasible | PASS from 13 | `behavioral/MIROFISH_INTERFACE.md`, optional adapter, no-probability schema, run logs; MIROFISH_AVAILABLE, NO_GO or BLOCKED (paid LLM or Zep use is not approved, EXECUTION.md) | NOT STARTED |
| 15 | Incremental value of behavioral simulation | PASS from 14 | `behavioral/EXPERIMENT_PROTOCOL.md`, `EVENT_SET.csv`, `SCENARIO_CODING.csv`, `INCREMENTAL_VALUE_RESULTS.md`, `GO_NO_GO.md`; valid comparison, conservative decision | NOT STARTED |
| 16 | Champion selection, ensemble and model registry | PASS from 15 | `models/CHAMPION_POLICY.md`, `REGISTRY_SCHEMA.md`, pinned artifacts, ablations, rollback test; champion on evidence | NOT STARTED |
| 17 | Every eligible discovery or catalyst change gets a forecast or a visible abstention | PASS from 16 | `integration/REQUEST_FLOW.md`, code and CLI tests, three traceable examples, feature flag (default off), real-path smoke log | NOT STARTED |
| 18 | Reports, CLI and alerts without trading directives | PASS from 17 | `ui/EXAMPLE_REPORTS.md`, report code and golden tests, alert rule matrix, missing-data UX | NOT STARTED |
| 19 | Outcome tracking, prospective replay and drift | PASS from 18 | `monitoring/OUTCOME_LEDGER.md`, calibration report, drift tests, rollback demo, prospective plan | NOT STARTED |
| 20 | Independent adversarial integration and scientific audit | PASS from 19 | `qa/INDEPENDENT_FINDINGS.md`, `SCENARIO_MATRIX.csv`, `FULL_E2E_LOG.md`, `SCIENTIFIC_CLAIMS_AUDIT.md`; P01 to P48 evidenced, no unresolved critical or high defect | NOT STARTED |
| 21 | Reproducible research-only release or explicit NO-GO | PASS from 20 | `release/RELEASE_DECISION.md`, `INSTALL_RUNBOOK.md`, `USER_GUIDE.md`, `MODEL_LIMITS.md`, `ROLLBACK_PROOF.md`, smoke logs; truthful final classification | NOT STARTED |

## Known constraints carried from Phase 00 into Phase 01

- Real dated history is 17 days of sparse thesis snapshots plus collector candles for 33 pools from 2026-10-06 to 2026-10-08 (DATA_COVERAGE.md). Free GeckoTerminal OHLCV reaches back at least to pool creation for recent pools at about 10 calls per minute; DEX Screener has no history.
- Backtesting & Stress-Testing v1.2 is not installed on any branch: BACKTEST_NOT_AVAILABLE (PI-D-006).
- Code reaches the scheduled runs only after a merge into `main` (PI-D-005).
- Stored thesis scores depend on the code version and inputs that produced them, neither of which is recorded (PI-D-008).
