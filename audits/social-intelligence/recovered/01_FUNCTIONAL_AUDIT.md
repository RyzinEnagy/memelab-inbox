# Phase 01 — Independent functional and integration audit

Audit date: 2026-10-13 (America/New_York). Repository: https://github.com/RyzinEnagy/memelab-inbox. Baseline: **698f73b854567ce60b56ce275b5ab6822a9d5f60**, exactly the primary commit established in Phase 00.

## Verdict

**The completed engine is not demonstrated to work correctly from initial collection through final research output.** Substantial offline components work. A deliberately supplied text handoff produces resolved claims, correct repost accounting and cited reports. The normal primary ingestion boundary produces observations but no claims. Historical report reads also admit future-derived information. Passing deterministic fixture demos does not establish a working unattended intelligence service.

| Execution | Result | Meaning |
|---|---|---|
| Existing automated suite, independently rerun | **651 passed, 1 failed**, exit 1, 120.34 seconds | Existing catalyst corroboration regression persists; AUD-011 |
| Repository release fixture harness | **45/45 stages passed**, exit 0 | Stage CLI compatibility and isolation pass; not a shared-observation pipeline |
| New independent acceptance probes | **17 passed, 5 failed**, exit 1, 0.86 seconds | Two confirmed baseline findings and three new defects |
| Python network/DNS attempts in guarded runs | **0** | Offline execution; no live source functionality demonstrated |
| Production source and tracked database | **Unchanged** | Audit-only artifacts; no application fixes, transactions, deployment, commit or push |

The three new issues are **AUD-015** (explicit snapshot cutoff bypass), **AUD-016** (unhandled adapter iteration failures), and **AUD-017** (future chronology output in historical feeds). AUD-001 and AUD-003 are independently reconfirmed. Other Phase 00 findings remain open; absence of a new failing test is not closure.

## Preparation and scope

Read the actual Phase 00 baseline, requirements matrix and findings register from the separately saved files and placed unchanged copies under this audit directory before testing. The specified files were absent from the repository default branch. The matrix is the Phase 00 mapping of the original staged requirements, not a replacement software specification. The attached chapter and curriculum do not define this engine's contract.

Inspected production implementations and their existing tests before designing probes: ingestion/X/Telegram adapters; identity/market projection/extraction; narratives; registry import/review; wallet assertions/activity/performance; information alpha; chronology; research/scout integration; feeds; alerts; outcome ledger; replay adapters and release tooling. Read architecture, control records and relevant phase documentation under `docs/social-intelligence`, including the explicit stage-separation design and deferred collection-to-extraction wiring.

Only the pinned **main** feature set was executed. Optional phases 19–21 on another branch are outside this functional test result. Do not substitute the moving feature branch for the baseline. Python 3.12.14, pytest 9.1.1; no Python 3.13 compatibility result is claimed.

Execution used a detached disposable worktree. All independent databases, private text/model stores, alert state and signal ledgers were temporary. Migrations used a copy of the tracked database. The original test suite writes an untracked BRETT report into its disposable checkout; no production tracked file changed. This reproduces the isolation limitation already recorded as AUD-011.

## Commands and evidence

Executed from `/workspace/scratch/122055c1bdba/functional-test` unless noted:

```bash
git worktree add --detach ../functional-test 698f73b854567ce60b56ce275b5ab6822a9d5f60
python3 -m pytest tests -q
python3 tools/release_e2e.py --out ../memelab-inbox/audits/social-intelligence/evidence/release-e2e.md --json ../memelab-inbox/audits/social-intelligence/evidence/release-e2e.json
python3 -m pytest ../memelab-inbox/audits/social-intelligence/evidence/test_functional_audit.py -v -s
```

All Python commands above ran with `PYTHONPATH=/workspace/scratch/122055c1bdba/audit-control:/workspace/scratch/122055c1bdba/functional-test` and `AUDIT_NETWORK_LOG=/workspace/scratch/122055c1bdba/memelab-inbox/audits/social-intelligence/evidence/network.log`. The startup guard removes credential-shaped environment variables and raises on Python socket connections/DNS. The release harness additionally creates its own pinned isolated clone and guards its children. Network restriction is a Python guard, not a claim of OS-wide packet capture.

Exact output: `evidence/existing-suite.log`, `release-e2e.log`, `release-e2e.md`, `release-e2e.json`, `independent-tests.log`. Reproductions: `evidence/test_functional_audit.py`. Safety/identity metadata: `execution-metadata.json`, `network.log`, `network-guard/sitecustomize.py`.

To reproduce elsewhere, clone the repository, detach at the full baseline SHA, obtain the audit evidence folder, and run from that repository root. Put the delivered `network-guard` directory and repository root on `PYTHONPATH`; set `AUDIT_NETWORK_LOG` to a writable absolute path. Point pytest at the delivered audit test file. It intentionally returns failure until the five acceptance defects/gaps are resolved. Existing builder imports require the baseline's `tests` directory. `ROOT=Path.cwd()` intentionally binds fixtures and production imports to the tested checkout. Do not run it from the evidence directory.

Initial audit-harness errors were corrected before the final run: incorrect narrative keyword names and an unintended stale-data window. The archived `independent-tests-initial-harness.log` records that initial iteration and is **not** a product-defect count. Final script and `independent-tests.log` are authoritative. The outage fixture is older than the default freshness threshold; its surviving connector is correctly DEGRADED rather than falsely healthy. Gap disclosure is tested separately with fresh observations.

## Scenario A — Two independent Solana observations and one repost

Synthetic account IDs 2001–2003 publish items 1001–1003. The exact invented Solana mint is `8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ`. The first two bodies differ; item 1003 repeats item 1001 and has a provider `retweeted` reference. Each body passes through `x_api.post_item` and the real normalized ingester.

**Required automatic path:** preserve all observations, resolve the contract, extract claims, group the narrative, produce cited output. **Actual:** three observations persist and no claims are created. `test_A_primary_ingestion_reaches_claims_without_manual_handoff` fails. This reconfirms AUD-003; adding credentials cannot repair an absent handoff.

**Explicitly assisted component path:** the test supplies the original bodies and synthetic market-provider responses to `extract_observation`, the handoff missing from the primary path. Actual: one exact contract cluster, three items, **two independent sources and one amplifier**. A brief cites all three canonical X URLs. Reingestion/reextraction produces no extra observations or claims; repeated feed construction from identical input is byte-equal JSON. This passes `test_A_explicit_handoff_resolves_groups_cites_and_repeats`.

This second result is a valid connected ingestion→resolution→deterministic extraction→narrative→report demonstration **with an audit-supplied bridge**. It does not prove that the shipped collector invokes the bridge, that a live model understands the discussion, or that alerts/outcomes are automatically recorded from those same observations. In this fixture the narrative groups by contract; semantic theme classification is not inferred by deterministic extraction.

## Scenario B — Mention after a 400% increase

A synthetic price series rises from 1 to 5 before the mention and stays at 5 afterward. Six matched control tokens remain flat. The independent test supplies the call at hour 12 with its first observation lag and evaluates the 24-hour horizon.

Expected: earlier gains must not become the trader's discovery return. Actual: hypothetical entry price **5**, nonpositive net return after modeled costs, and **zero relative return** against controls. The test passes. This validates event-time return attribution for the supplied data. It does not establish that trader selection correctly identifies early discoverers from live history, nor certify the modeled liquidity cost as an executable quote.

## Scenario C — Hype, concentrated ownership and thin executable liquidity

Passed module inputs directly to the actual core opportunity ranker: largest unexplained holder 30%, adjusted top-10 85%, $100 sell capacity within 5% impact, and 60% impact for a $5,000 sale. No ready-made fatal flag was supplied.

Expected: core checks identify the risks and the social layer cannot clear them. Actual core flags: `LARGEST_HOLDER_GT_15PCT`, `TOP10_GT_50PCT`, `CANNOT_EXIT_5K`. Feeding that evaluated result into research enrichment with 100 independent social sources and HIGH confidence leaves `REJECTED_STRUCTURE` and excludes it from tradable ranking. Test passes.

The legacy pipeline produces ownership/depth module results separately; this probe starts at that module-output boundary. It does **not** validate live holder classification, wallet clustering or quote acquisition. It also does not establish that those risks appear in every standalone social brief: the scout/research rejection path is the proved boundary.

## Scenario D — Failure halfway through collection

Two failure forms were deliberately separated:

1. **Normalized unavailable source unit:** one X batch succeeds, a DOWN unit represents page-two failure, and another connector supplies a batch. Actual: earlier observations survive, the failed source is DOWN, the other connector continues, coverage stores GAP, and retry introduces no duplicates. The reported run is PARTIAL. With fresh assisted claims, a resulting brief explicitly reports GAP and counts as lower bounds. Both tests pass.
2. **Adapter generator raises during the next fetch:** after one committed item, `adapter.units()` raises `TimeoutError`. Expected: finalized partial run with failure health. Actual: the exception escapes, the item survives, the run remains **RUNNING**, and final DOWN health is not recorded. Acceptance test fails: AUD-016.

The second is a source-adapter contract robustness defect. The shipped X adapter has its own per-scope exception normalization, so this custom adapter reproduction is **not evidence that the live X API always crashes this way**. It identifies a hole in the advertised provider-neutral ingester and an untested recovery boundary.

## Major-component assessment

Every row combines the independently rerun existing suite with the specified new probe. PASS applies only to the tested slice.

| Component | Independent probe / existing coverage | Result and limit |
|---|---|---|
| Trader discovery | `source_registration_discovery_idempotent`; registry suite | Import creates 12 fixture candidate entities; repeated import stable. No automatic current profitable-trader discovery or verified population established |
| Social ingestion | A and both D forms; X/Telegram/ingest suites | Provenance, persistence and normalized outages work; automatic claims missing; generator failure handling defective |
| Source registration | Fixture import plus registry tests | Fixture marking and identity import persist; no real source activation demonstrated |
| Token identification | A exact mint; `token_ticker_collision_abstains` | Exact chain/contract resolves; ambiguous Solana $PEPE abstains |
| AI extraction | Hash-mismatch rejection; `model_output_cannot_invent_a_resolved_token`; extraction suite | Wrong text rejected; mock invented mention rejected without invented resolved token. Model output is PARTIAL; no live semantic-quality proof |
| Narrative grouping | Assisted A; late-extraction test; narrative suite | Reposts counted correctly; later extraction leaks into past snapshot (AUD-001) |
| Trader scoring | B; `wallet_performance_recomputes_and_abstains_on_incomplete_history`; alpha/performance suites | Premention gains not credited; wallet fixture has only 3 positions/2 days and remains unrankable. Deterministic hashes pass; no live ranking validation |
| Wallet attribution | `wallet_disclosure_is_not_control_proof`; assertions suite | SELF_CLAIMED disclosure never becomes control proof; owner unknown |
| On-chain corroboration | Activity import/retry; chronology save/verify; late flag test | 13 classified wallet events stable on retry; chronology saved hash recomputes. Historical feed admits later flags (AUD-017); on-chain input is synthetic |
| Discovery integration | C; research suite | Real ranker creates risk flags; opt-in social research preserves rejection; core attention/launch carry-overs remain outside this integration |
| Report generation | Assisted A, D gap report, future-run test; feed suite | Cites all three items; discloses incomplete coverage. Explicit snapshot ID bypasses cutoff (AUD-015) |
| Alerts | `alert_repeat_dry_run_no_remote_delivery`; alert suite/release | Local event dedupe succeeds; zero remote deliveries. No live delivery or automatic signal recording proved |
| Historical persistence | Legacy-copy migration; extraction/snapshot/chronology cutoff tests | All 20 legacy table counts preserved; migration to 12 and reopen succeed. Physical persistence works; historical causality fails |
| Outcome tracking | `outcome_ledger_append_idempotence_and_integrity`; outcome suite/release | Caller-supplied signal dedupes, observations evaluate, hash chain verifies after reopen. Automatic collector/feed→signal recording absent |

## Historical correctness, repetition and reproducibility

Physical durability is not causal correctness. The tests separately establish:

- Repeated normalized ingestion, deterministic extraction, registry import, wallet activity ingestion, alert dry runs and signal recording do not multiply logical evidence in the tested cases.
- Copied legacy DB migration to version 12 is idempotent and preserves every legacy table's row count. The existing suite also exercises rollback, changed migration checksums and failed-migration rollback. No production database migration was performed.
- Empty collections create zero observations; an empty social store produces an explicit no-signal feed. Missing X credentials report `credentials_missing`, zero requests and no live read evidence. Release checks cover missing Telegram/Helius credentials and delivery refusal.
- Identical supplied feed input produces identical JSON. Wallet performance result hashes reproduce; saved chronology recomputes against its input; outcome hash-chain integrity survives reopening.
- Historical narrative selection fails when `extracted_at` is moved one day beyond the cutoff (AUD-001). The test changes only temporary fixture records.
- `feed_store.load_input(..., run_id=..., as_of=...)` returns a later snapshot instead of rejecting it (AUD-015). Without an explicit ID the query applies `cutoff<=as_of`; the ID branch does not. The report CLI exposes both `--run` and `--as-of`.
- Four chronology flags saved a day after the requested historical time appear through `feed_store._flags` (AUD-017). That function filters flag event time, but neither run creation nor knowledge availability. Recomputable outputs can therefore still contain hindsight.

No broad claim is made that every output is reproducible under future database mutations. Current account links, symbols, source kinds, claim supersession and coverage records also require historical availability review; Phase 00 AUD-002 remains open. Pure replay fixture correctness does not cure database-export defects.

## Superficial assertions and missing coverage

Much of the existing suite is substantive: it checks risk overrides, FIFO accounting, ambiguous contracts, repost independence, malformed model grounding, unknown inventory, retries and ledger integrity. The issue is **boundary coverage**, not that all tests are superficial.

Specific weak acceptance evidence:

- `test_release_tools.py::test_e2e_stages_reference_existing_fixtures_and_expect_refusals_without_credentials` checks fixture existence, stage titles and expected exits. It cannot show that the data flows between stages.
- Fixture-builder equality tests in alpha/research/feed/alerts check synchronization with the implementation's fixture generator; they are not independent financial or provenance oracles.
- Sample Markdown equality proves deterministic presentation of that supplied world; it cannot prove completeness of primary source collection, live permissions or correct source selection.
- `release_e2e.py` checks expected CLI exit codes across independent `--post`, `--ledger`, `--input` and demo inputs. Its safety/unchanged-tree checks are useful, but PASS is not a collection-through-outcome guarantee (AUD-014).
- Existing narrative past-window replay tests did not insert a late extraction after the historical cutoff. Existing feed tests did not enforce cutoff for explicitly selected future runs. Chronology pure-core future-event tests did not test when DB-derived output became available.
- Existing connector isolation tests exercise unavailable units or failures *inside* unit processing. They do not cover the `next(adapter.units())` exception outside that protected region.

Important unproved or missing acceptance coverage: one shipped primary-source event ID continuing through automatic extraction, narratives, report, alert and forward signal; real model semantic accuracy against independently labeled posts; live source pagination and interruption; future correction/supersession/identity/link/coverage changes; restart across private-store export/import; provider history completeness; exact token precision and executable quote costs; calibrated uncertainty with correlated trader/token samples; paid quota enforcement in real transports; deletion across stored/derived/exported content; running schedule and live delivery. Some have component fixtures and code; none should be called demonstrated live functionality on that basis.

## New defects and recommended fixes

| Stable ID | Severity | Expected → actual | Recommended fix |
|---|---|---|---|
| AUD-015 | High | Explicit historical run respects cutoff → future snapshot returned | Apply cutoff/availability validation to explicit IDs; distinguish inspection of a stored run from an as-of historical report |
| AUD-016 | Medium | Fetch failure finalizes partial run → exception escapes, RUNNING persists | Normalize iterator failures before iteration or protect advancement; finalize run/health on failure and retain transactional checkpoints |
| AUD-017 | High | Derived flags available only after computation → four later-created flags appear in historical feed | Select chronology runs as of both evidence and creation/availability clocks; choose latest eligible run, not latest overall |

First resolve the collection handoff and historical availability invariants (AUD-003/001/002/015/017), then run these exact acceptance probes and one genuinely connected signal-to-outcome scenario. Normalize generator failure handling and test recovery without losing committed data. Keep proven structural risk separation. Repair the existing catalyst red test independently; it is not a newly introduced social failure. Do not make a live readiness claim until authorized source operation and continuous private-store persistence are separately demonstrated.

## Live versus simulated evidence and stop condition

**Every functional result in this phase is offline/simulated.** GitHub was read to obtain the repository, not used as a social data connector test. No source was activated, model queried, external alert sent, paid quota consumed, wallet connected or financial transaction triggered. Existing authentication/health refusal commands ran with missing credentials. These prove safe refusal paths, not upstream service access.

Tracked DB SHA-256 remains `068287c0d7e454361eb42f54b2f90e49e4075ae3a962a3c57867165ab6a679ca`. `git diff` over application code, existing tests, tools, docs and that database is empty. All new scripts, logs and documentation reside in `audits/social-intelligence` or disposable scratch directories. FINDINGS retains AUD-001–014 and adds AUD-015–017. This phase stops here; no recommended fix has been implemented.