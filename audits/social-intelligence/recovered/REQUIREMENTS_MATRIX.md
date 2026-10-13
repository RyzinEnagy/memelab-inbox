# Requirements traceability matrix

Primary baseline: `698f73b854567ce60b56ce275b5ab6822a9d5f60` (main). Supplemental baseline: `3f27fc788f9ab88286b8041355e5445fdfdf012c` (feature). Audit date: 2026-10-13.

## How to read this matrix

Requirement IDs REQ-PP-NN refer to the original staged prompt number and paragraph (Phase 00 numbered instructions are separated). Exact requirement text is retained below, not substituted with the implementer's roadmap. Each row links to a phase evidence mapping P-PP below, which specifies implementation files/functions, relevant tests, observed behavior, completion evidence and limitations. Process instructions are separately classified as historical-record evidence, not runtime functionality. Test-suite success verifies existing cases only; targeted probes override stronger completion claims.

Paths such as `schema.py` in P-PP mean `memelab/social/schema.py`; listed test basenames mean `tests/<basename>`. Modules without a function suffix are reviewed component paths. Test functions and source locations are indexed in `evidence/{main,feature}-test-inventory.json` and `*-source-symbols.json`. Symbols do not imply all branches of a function were tested. Phase 19–21 files are in the feature baseline only.

Original source: `evidence/original-staged-prompts.md`, full content read from Memecoin_Social_Intelligence_Staged_Prompts.md. Older unstaged mega-prompt not independently recovered. No requirements are invented for it.

## Phase evidence mappings

### P-00

| Field | Evidence |
|---|---|
| Audited classification | Partially implemented governance |
| Implementation files and relevant functions | `docs/social-intelligence/{EXECUTION,ROADMAP,DECISIONS,HANDOFF,AUDIT_00}.md; git history` |
| Relevant tests | `test_release_tools.py` |
| Representative test functions | `test_release_tools.py::test_credential_shapes_are_caught_and_values_never_reported`; `test_release_tools.py::test_placeholder_shapes_are_reviewed_not_findings`; `test_release_tools.py::test_tracked_tree_has_no_credentials_or_key_material` |
| Observed behavior | Control files and phase commits exist; branch/HEAD and CLI help independently inspected. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | Historical workflow/author permissions cannot be reconstructed just from commits; main handoff stale (AUD-010). |

### P-01

| Field | Evidence |
|---|---|
| Audited classification | Fully implemented offline persistence slice |
| Implementation files and relevant functions | `schema.py::{migrate,rollback,backup_db}; store.py::{record_observation,add_claim,link_evidence,assert_wallet}; private.py` |
| Relevant tests | `test_social_store.py` |
| Representative test functions | `test_social_store.py::test_empty_db_init_and_repeat`; `test_social_store.py::test_migration_on_synthetic_legacy_db`; `test_social_store.py::test_migration_on_copy_of_tracked_db` |
| Observed behavior | Empty/idempotent init and tracked-copy migration 0→12; checked legacy counts unchanged. SQLite CRUD, rollback cases pass. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | New schema absent from tracked DB; lifecycle/extraction gaps remain. |

### P-02

| Field | Evidence |
|---|---|
| Audited classification | Fully implemented fixture-backed ingestion slice |
| Implementation files and relevant functions | `ingest.py::{validate_envelope,validate_item,ingest,_process_unit,event_record,with_retries}; bridge_adapter.py; memelab/bridge/social.js` |
| Relevant tests | `test_social_ingest.py` |
| Representative test functions | `test_social_ingest.py::test_cli_ingest_persists_verifiable_observation`; `test_social_ingest.py::test_status_command`; `test_social_ingest.py::test_pull_route_then_ingest` |
| Observed behavior | Fixture load creates accepted observations and quarantines invalid/private/text items; repeated input deduplicates; degraded connectors retained. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | Bridge is a shaping/import adapter, not a page collector; same-file replay may exit 1 by design. |

### P-03

| Field | Evidence |
|---|---|
| Audited classification | Partially implemented; credentials dependent; mock-only source evidence |
| Implementation files and relevant functions | `x_api.py::{XApiAdapter,post_item,FixtureTransport,health}; social/cli.py` |
| Relevant tests | `test_social_x_api.py` |
| Representative test functions | `test_social_x_api.py::test_main_fixture_originals_replies_reposts_quotes_edits`; `test_social_x_api.py::test_text_is_hashed_never_stored_and_long_form_wins`; `test_social_x_api.py::test_provenance_and_freshness` |
| Observed behavior | Original/reply/repost/quote/edit fixtures persist; rate/billing/secret tests pass; no-credentials health/refusal executes offline. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | No live access proof; extraction missing AUD-003; page cap skips backlog AUD-005; erasure missing AUD-009. |

### P-04

| Field | Evidence |
|---|---|
| Audited classification | Partially implemented product path; credentials dependent |
| Implementation files and relevant functions | `telegram_bot.py::{TelegramBotAdapter,message_item,health}; social/cli.py` |
| Relevant tests | `test_social_telegram.py` |
| Representative test functions | `test_social_telegram.py::test_main_fixture_channel_posts_into_observations`; `test_social_telegram.py::test_provenance_of_one_event`; `test_social_telegram.py::test_text_signature_and_forward_sender_never_stored` |
| Observed behavior | Authorized-channel, polling, webhook, forward and crash/resume fixtures pass; no-credential refusal reproduced. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | No live bot/admin permission tested; dropped text is not handed to extraction (AUD-003). |

### P-05

| Field | Evidence |
|---|---|
| Audited classification | Fully implemented supplied-body slice; fixture-only demonstration |
| Implementation files and relevant functions | `identity.py::{resolve_post,resolve_address,resolve_ticker,token_identity,persist}; market_context.py::{attach,observed_facts,posting_time_facts}` |
| Relevant tests | `test_social_identity.py` |
| Representative test functions | `test_social_identity.py::test_keccak_and_eip55_vectors`; `test_social_identity.py::test_extraction_reads_text_in_memory_and_returns_only_tokens`; `test_social_identity.py::test_same_ticker_across_chains_and_contracts_is_ambiguous` |
| Observed behavior | Exact supplied-body identity resolves, cashtag collision remains ambiguous; quotes and reported liquidity remain separate. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | Four chains; supplied provider bodies and posting candles only; provider denominator meanings not freshly certified. |

### P-06

| Field | Evidence |
|---|---|
| Audited classification | Partially implemented operational pipeline; standalone code tested |
| Implementation files and relevant functions | `extraction.py::{extract_observation,validate_model_output,deterministic_claims,replay}; llm.py::{AnthropicProvider,Budget,llm_status}` |
| Relevant tests | `test_social_extraction.py` |
| Representative test functions | `test_social_extraction.py::test_without_a_model_a_cited_reference_claim_is_stored_and_reported`; `test_social_extraction.py::test_mock_provider_structured_analysis_end_to_end`; `test_social_extraction.py::test_sarcasm_raises_uncertainty` |
| Observed behavior | Standalone deterministic reference and mock grounded claims persist; missing model accurately reported; cache/schema/injection cases pass. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | No real model semantic validation; collector handoff missing for X/TG; zero-price budget edge AUD-006. |

### P-07

| Field | Evidence |
|---|---|
| Audited classification | Partially implemented; temporal claim disproved |
| Implementation files and relevant functions | `narratives.py::{snapshot,_load_claims,_load_items,run_view,report}` |
| Relevant tests | `test_social_narratives.py` |
| Representative test functions | `test_social_narratives.py::test_one_hundred_reposts_of_one_original_are_one_independent_source`; `test_social_narratives.py::test_reposts_whose_original_was_never_observed_make_volume_but_not_independence`; `test_social_narratives.py::test_reposts_group_with_their_original_even_when_the_text_differs` |
| Observed behavior | Fixtures demonstrate clusters, snapshots/deltas, 100 reposts collapsed, uncertainty and time zones. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | Later extraction appears in older cutoff snapshot (AUD-001); semantic clustering intentionally not enabled, allowed by prompt. |

### P-08

| Field | Evidence |
|---|---|
| Audited classification | Fully implemented offline registry slice; mock-only population |
| Implementation files and relevant functions | `registry.py::{ensure_account,ensure_wallet,add_evidence,review_link,approve,reject,search,discover_from_narratives}; registry_import.py` |
| Relevant tests | `test_social_registry.py` |
| Representative test functions | `test_social_registry.py::test_migration_8_rolls_back_cleanly_and_reapplies`; `test_social_registry.py::test_import_creates_labelled_candidates_and_nothing_else`; `test_social_registry.py::test_import_is_idempotent_and_dry_run_writes_nothing` |
| Observed behavior | Candidate/import/review records, handle collisions, provenance and abstention pass on labelled fixtures. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | No current real source selection or validated best-trader list; no person identity certainty. |

### P-09

| Field | Evidence |
|---|---|
| Audited classification | Partially implemented user capability; fixture tested |
| Implementation files and relevant functions | `wallet_assertions.py::{record,review,revoke,explain}; sigverify.py; wallet_activity.py::{add_wallet,ingest,classify,provenance}` |
| Relevant tests | `test_social_wallets.py` |
| Representative test functions | `test_social_wallets.py::test_migration_9_rolls_back_cleanly_and_reapplies`; `test_social_wallets.py::test_signature_verifier_matches_public_test_vectors`; `test_social_wallets.py::test_track_add_pause_resume_remove_keep_history_and_claim_no_owner` |
| Observed behavior | Pure verification vectors, tracked-wallet status, transfers/swaps/LP distinction and provenance fixture cases pass. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | No real Helius fetch tested; default 50 newest transactions; no EVM provider; live attribution collection absent (AUD-012). |

### P-10

| Field | Evidence |
|---|---|
| Audited classification | Implemented accounting slice; real result unverified |
| Implementation files and relevant functions | `perf_core.py::{parse_ledger,run_engine}; perf_analysis.py::{analyze,run_checks,score,rank_wallets}; perf_store.py::{ledger_from_events,run_wallet}` |
| Relevant tests | `test_social_performance.py` |
| Representative test functions | `test_social_performance.py::test_main_fixture_matches_the_hand_checked_numbers`; `test_social_performance.py::test_main_fixture_metrics_and_unrealized_lines_are_separate`; `test_social_performance.py::test_main_fixture_counts_gaps_and_refusal` |
| Observed behavior | Hand-checked supplied lots/fees reconcile; FIFO/AVCO, unknown cost and exit distinctions, outlier and refusal tests pass. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | No complete real-wallet reconstruction or exit proof; uncertain fetched-history inference (AUD-012). |

### P-11

| Field | Evidence |
|---|---|
| Audited classification | Partially implemented research capability |
| Implementation files and relevant functions | `alpha_core.py::{analyze,evaluate,_eligibility,_baseline,_score,rank}; alpha_store.py::{build_input,load_series,put_series}` |
| Relevant tests | `test_social_alpha.py` |
| Representative test functions | `test_social_alpha.py::test_hand_checked_single_call`; `test_social_alpha.py::test_fixture_calls_recompute_independently_from_raw_candles`; `test_social_alpha.py::test_short_signed_return_and_mfe_mae` |
| Observed behavior | Supplied candles yield abstention/tiers, matched comparisons, net modeled returns and transparent fixture hand checks. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | Real trader alpha unvalidated; selection enumeration/historical provider absent; fixture export labelled real AUD-004. |

### P-12

| Field | Evidence |
|---|---|
| Audited classification | Implemented fixture-tested chronology slice |
| Implementation files and relevant functions | `chrono_core.py::{evaluate,analyze,relation,report}; chrono_store.py::{build_input,verify_run,current_flags}` |
| Relevant tests | `test_social_chronology.py` |
| Representative test functions | `test_social_chronology.py::test_fixture_files_match_their_generator`; `test_social_chronology.py::test_confident_fixture_orders_every_pair`; `test_social_chronology.py::test_indeterminate_fixture_says_so_and_claims_no_order` |
| Observed behavior | Confident and indeterminate fixture timelines preserve clock intervals and cautious attribution. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | No joined real post/wallet/candle coverage; current-state historical joins warrant follow-up AUD-001/002. |

### P-13

| Field | Evidence |
|---|---|
| Audited classification | Fully implemented report-enrichment slice; operationally partial |
| Implementation files and relevant functions | `research_core.py; research_store.py::{findings_from_db,evaluated_from_scout,evaluated_from_catalyst,prior_rejections}; report.py; catalyst/cli.py` |
| Relevant tests | `test_social_research.py` |
| Representative test functions | `test_social_research.py::test_fixture_file_matches_its_builder`; `test_social_research.py::test_before_after_report_enriches_one_candidate_and_leaves_rejections_alone`; `test_social_research.py::test_demo_cli_runs_and_writes_side_by_side` |
| Observed behavior | Opt-in fixture report enriches research candidates while fatal/rejected entries stay constrained; policy off/no-data no-op. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | Report adapter, not autonomous discovery/schedule; legacy core attention/launch integration remains absent. |

### P-14

| Field | Evidence |
|---|---|
| Audited classification | Implemented fixture-tested renderer; no real feed populated |
| Implementation files and relevant functions | `feed_store.py::{load_input,load_from_path}; feed_core.py::{build,render_brief,render_digest,render_feed,safe_url}; feed_cli.py` |
| Relevant tests | `test_social_feed.py` |
| Representative test functions | `test_social_feed.py::test_zero_narratives_says_no_supported_high_priority_observations`; `test_social_feed.py::test_one_narrative_has_every_required_field`; `test_social_feed.py::test_multiple_narratives_are_grouped_by_token_and_theme_and_ordered` |
| Observed behavior | Brief/digest/filter JSON, URL/markdown sanitization, missing model and fixture watermark/no-signal cases pass. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | Real main has no social schema; summaries omitted by D-095; cutoff inherits upstream defects. |

### P-15

| Field | Evidence |
|---|---|
| Audited classification | Implemented file/dry-run slice; live delivery untested/credential dependent |
| Implementation files and relevant functions | `alerts_core.py; alerts_engine.py::{run,deliver,_deliver_one,claim_slot}; alerts_transport.py; alerts_schedule.py::{next_runs,due_slot}` |
| Relevant tests | `test_social_alerts.py` |
| Representative test functions | `test_social_alerts.py::test_fixture_alert_deduped_second_run_and_sample_reproduced`; `test_social_alerts.py::test_alert_fixture_spec_matches_its_builder`; `test_social_alerts.py::test_duplicate_alert_across_retries_and_new_snapshots` |
| Observed behavior | Fixture file dry-run, dedupe/cooldown/caps, timezone/DST and refused nonconsensual send pass. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | External transports live-untested, no job enabled; templates are not scheduler deployment. |

### P-16

| Field | Evidence |
|---|---|
| Audited classification | Partially implemented end-user feature; standalone slice tested |
| Implementation files and relevant functions | `outcomes_core.py::{make_signal,signals_from_feed,evaluate,coverage}; outcomes_ledger.py::{record_signal,_append,verify}; outcomes_cli.py` |
| Relevant tests | `test_social_outcomes.py` |
| Representative test functions | `test_social_outcomes.py::test_lookahead_context_drops_later_facts_and_entry_is_never_before_the_signal`; `test_social_outcomes.py::test_evaluation_clock_cannot_run_ahead_or_backwards`; `test_social_outcomes.py::test_revised_provider_snapshot_appends_a_revision_and_keeps_the_original` |
| Observed behavior | Immutable context/revision ledger and dated horizon evaluation pass with missing/invalid/non-executable outcomes. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | Not automatically invoked from real signals/schedules; no historical/live provider; no real forward efficacy. |

### P-17

| Field | Evidence |
|---|---|
| Audited classification | Partially implemented; database-path no-leakage claim unverified/disproved |
| Implementation files and relevant functions | `replay_core.py::{CutoffView,Audit,LabelGate,run,leakage_check,tune,controls_for}; replay_sources.py::{from_db,from_inbox}` |
| Relevant tests | `test_social_replay.py` |
| Representative test functions | `test_social_replay.py::test_backdated_post_is_decided_when_it_became_available_not_when_published`; `test_social_replay.py::test_harness_that_reads_future_evidence_fails`; `test_social_replay.py::test_future_information_injected_into_training_window_does_not_change_tuning` |
| Observed behavior | Synthetic cutoff/held-out/embargo mutation tests and honest insufficient-data real run pass. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | Database claim availability backdated and assertion history not causal (AUD-002); intervals ignore some dependence. |

### P-18

| Field | Evidence |
|---|---|
| Audited classification | Partially implemented release acceptance |
| Implementation files and relevant functions | `tools/release_e2e.py::{main,STAGES,migrate_check}; tools/release_audit.py; docs/social-intelligence/{README,ARCHITECTURE,OPERATIONS,RELEASE_18}.md` |
| Relevant tests | `test_release_tools.py` |
| Representative test functions | `test_release_tools.py::test_credential_shapes_are_caught_and_values_never_reported`; `test_release_tools.py::test_placeholder_shapes_are_reviewed_not_findings`; `test_release_tools.py::test_tracked_tree_has_no_credentials_or_key_material` |
| Observed behavior | Main 45/45 and feature 71/71 fixture steps reproduce, no network, tracked DB unchanged; security/syntax scan rerun. |
| Evidence of completion | `evidence/main-tests.log` (651 pass/1 known failure) and `main-e2e.json` (45/45; corresponding stages). |
| Remaining limitations | Full suite red; static types absent; single-data-flow proof absent AUD-014; live/deployment gates remain blocked. |

### P-19

| Field | Evidence |
|---|---|
| Audited classification | Main missing; feature built/fixture-only/access dependent |
| Implementation files and relevant functions | `api_common.py::{TextSink,extract_after_ingest,purge_gone_items}; reddit_api.py::{RedditApiAdapter,purge_deleted,health}; farcaster_hub.py::{FarcasterHubAdapter,health}; sources_cli.py` |
| Relevant tests | `test_social_reddit.py`; `test_social_farcaster.py` |
| Representative test functions | `test_social_reddit.py::test_main_fixture_submissions_comments_crosspost_deleted_edited`; `test_social_reddit.py::test_text_titles_flair_and_slugs_are_never_stored`; `test_social_reddit.py::test_provenance_rights_basis_and_fixture_labels`; `test_social_farcaster.py::test_main_fixture_casts_replies_quotes_recasts`; `test_social_farcaster.py::test_only_the_username_is_requested_and_no_text_is_stored`; `test_social_farcaster.py::test_recasts_are_amplification_quotes_and_replies_are_own_words` |
| Observed behavior | Feature-only HTTP fixtures exercise each adapter, source→claims→narrative/report plus explicit missing-access refusal. |
| Evidence of completion | `evidence/feature-tests.log` (748 pass/1 known failure) and `feature-e2e.json` (71/71). |
| Remaining limitations | Missing entirely on main; no actual Reddit approval or Farcaster hub availability; no scheduled operation. |

### P-20

| Field | Evidence |
|---|---|
| Audited classification | Main missing; feature partial; mock-only Gateway |
| Implementation files and relevant functions | `discord_bot.py::{DiscordBotAdapter,DiscordGatewayAdapter,purge_deleted,health}; sources_cli.py::{cmd_discord_ingest,cmd_discord_gateway}` |
| Relevant tests | `test_social_discord.py` |
| Representative test functions | `test_social_discord.py::test_main_fixture_ids_authors_replies_forwards_links_edits`; `test_social_discord.py::test_text_embeds_names_and_topics_are_never_stored`; `test_social_discord.py::test_provenance_rights_basis_and_fixture_labels` |
| Observed behavior | Feature REST fixtures and Gateway frame cases pass, linked claims/report shown; access/intent failures explicit. |
| Evidence of completion | `evidence/feature-tests.log` (748 pass/1 known failure) and `feature-e2e.json` (71/71). |
| Remaining limitations | Missing on main; live Gateway transport NOT IMPLEMENTED (AUD-013); no consenting live server tested. |

### P-21

| Field | Evidence |
|---|---|
| Audited classification | Main missing; feature built/fixture-only/access dependent |
| Implementation files and relevant functions | `youtube_data.py::{YouTubeDataAdapter,QuotaGuard,purge,health}; sources_cli.py::{cmd_youtube_ingest,cmd_youtube_purge}; feed_core.py::safe_url` |
| Relevant tests | `test_social_youtube.py` |
| Representative test functions | `test_social_youtube.py::test_config_refuses_credentials_translation_downloaders_and_weak_permission`; `test_social_youtube.py::test_gates_terms_credentials_make_no_request`; `test_social_youtube.py::test_run1_stores_ids_times_and_hashes_only_and_reads_a_duplicate_channel_once` |
| Observed behavior | Feature metadata/licensed or authorized caption fixture→claim/report, timing drift/language/quota/retention cases pass. |
| Evidence of completion | `evidence/feature-tests.log` (748 pass/1 known failure) and `feature-e2e.json` (71/71). |
| Remaining limitations | Missing on main; keys/rights/terms review unavailable; outside-channel public captions not generally accessible; guest attribution is channel-level. |

## Original requirement paragraphs

The phase evidence mapping is repeated by link in every requirement row. For runtime subrequirements, the audited classification and limitations in that mapping apply; a compound paragraph is not marked fully complete when one mandatory path is partial. Procedural/history paragraphs are evidence-limited as noted.

### Prompt 00 — Audit the actual repository and establish a resumable execution contract

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-00-01** — You are implementing Social & Trader Intelligence for `https://github.com/RyzinEnagy/memelab-inbox`. **This is Phase 00 only.** Treat the actual checkout as truth. Do not implement social functionality yet. | [P-00](#p-00) | P-00 test mapping | P-00 observed/proof mapping | Partially implemented governance. Historical workflow/author permissions cannot be reconstructed just from commits; main handoff stale (AUD-010). |
| **REQ-00-02** — 1. Open the authorized local clone or clone without executing remote bootstrap scripts. Record branch, HEAD, working-tree state, Python version, entrypoints and dependency management. Create one feature branch (suggested `feature/social-intelligence`) from current main if this will not disturb existing work; if uncommitted changes exist, preserve them and explain the safe branch strategy. Never force-push. | [P-00](#p-00) | P-00 test mapping | P-00 observed/proof mapping | Partially implemented governance. Historical workflow/author permissions cannot be reconstructed just from commits; main handoff stale (AUD-010). |
| **REQ-00-03** — 2. Read the real `README.md`, `docs/ARCHITECTURE.md`, `docs/SOURCES.md`, `skills/memecoin-scout/SKILL.md` when present. Inspect `memelab/db.py`, `normalize.py`, `pipeline.py`, `report.py`, `cli.py`, `memelab/bridge/`, actual `social-note` implementation, existing modules, tests, .gitignore, and the public inbox/bridge flow. Document differences between the current code and earlier assumptions. Distinguish facts seen in source code from README claims. | [P-00](#p-00) | P-00 test mapping | P-00 observed/proof mapping | Partially implemented governance. Historical workflow/author permissions cannot be reconstructed just from commits; main handoff stale (AUD-010). |
| **REQ-00-04** — 3. Run the project's existing test command, expected `python -m pytest tests -q`, plus a harmless CLI help/smoke check. Preserve verbatim outputs and pre-existing failures. Identify any runtime inability to call upstream APIs and whether Chrome-to-GitHub is the established collection route. | [P-00](#p-00) | P-00 test mapping | P-00 observed/proof mapping | Partially implemented governance. Historical workflow/author permissions cannot be reconstructed just from commits; main handoff stale (AUD-010). |
| **REQ-00-05** — 4. Audit secret-handling boundaries and public-repo redistribution risks. Do **not** print or commit credentials. Warn if known secrets may already have been exposed; propose rotation without reproducing values. Determine what raw social content may legally/safely be stored in the public repo. | [P-00](#p-00) | P-00 test mapping | P-00 observed/proof mapping | Partially implemented governance. Historical workflow/author permissions cannot be reconstructed just from commits; main handoff stale (AUD-010). |
| **REQ-00-06** — 5. Create `docs/social-intelligence/EXECUTION.md`, `ROADMAP.md`, `DECISIONS.md`, `HANDOFF.md`. EXECUTION is the contract that all future fresh sessions must follow: **one phase/session; implement, test, prove, commit, handoff, stop**. ROADMAP lists phases 00–21, dependencies and pass gates. HANDOFF records active branch, latest commit, verified modules, test command/outcome, current phase, next phase, blockers and exact next command. DECISIONS records durable architectural choices and their reasons. Do not invent evidence. | [P-00](#p-00) | P-00 test mapping | P-00 observed/proof mapping | Partially implemented governance. Historical workflow/author permissions cannot be reconstructed just from commits; main handoff stale (AUD-010). |
| **REQ-00-07** — 6. Add a tiny automated `social-phase-check` script only if it directly validates the handoff/roadmap contract; otherwise skip new code in Phase 00. | [P-00](#p-00) | P-00 test mapping | P-00 observed/proof mapping | Partially implemented governance. Historical workflow/author permissions cannot be reconstructed just from commits; main handoff stale (AUD-010). |
| **REQ-00-08** — **Gate:** baseline test results recorded; architecture and source-access constraints mapped; working branch established; four durable documents exist, accurate and linked; no existing functionality changed unintentionally. Commit these docs if authorized. Report changed files, tested commands with exit codes, commit hash, blockers. **Stop; do not start Phase 01.** | [P-00](#p-00) | P-00 test mapping | P-00 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Historical workflow/author permissions cannot be reconstructed just from commits; main handoff stale (AUD-010). |

### Prompt 01 — Implement durable schemas, evidence provenance, and migration safety

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-01-01** — Work only on Phase 01 of `RyzinEnagy/memelab-inbox`. First read `docs/social-intelligence/{EXECUTION,ROADMAP,DECISIONS,HANDOFF}.md`, verify checked-out branch/HEAD and previous acceptance gate, and inspect actual existing SQLite/state/normalization code. **Do not design a parallel data store without justification.** | [P-01](#p-01) | P-01 test mapping | P-01 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. New schema absent from tracked DB; lifecycle/extraction gaps remain. |
| **REQ-01-02** — Implement a minimal complete persistence layer for social intelligence, using repository conventions. Models/tables should support: source accounts and platform identities; trader registry; wallet-attribution assertions with evidence and confidence; source observations with original URL, provider ID, publication time, observation time, ingestion time, content hash, retrieval status, permissible retained content; token references with chain+contract; extracted claims; narratives; links between evidence and claims; connector health; analysis version; and source-coverage records. Leave future performance/outcome tables for their dedicated phases unless needed for referential integrity. | [P-01](#p-01) | P-01 test mapping | P-01 observed/proof mapping | Fully implemented offline persistence slice. New schema absent from tracked DB; lifecycle/extraction gaps remain. |
| **REQ-01-03** — Explicitly represent unknown values and tentative assertions. UTC storage, schema versions, append-only historical observations where appropriate, stable uniqueness constraints, idempotent upserts, migration and rollback plan. Social IDs are not automatically wallet IDs; ticker strings are not token IDs. Prevent public-repo leakage of sensitive raw posts with safe persistence defaults (metadata/references only, private gitignored store for content where allowed). Document retention and reprocessing policy. | [P-01](#p-01) | P-01 test mapping | P-01 observed/proof mapping | Fully implemented offline persistence slice. New schema absent from tracked DB; lifecycle/extraction gaps remain. |
| **REQ-01-04** — Build concrete storage CRUD/round-trip functionality. Test schema initialization in an empty DB, migration from a copy of an existing DB, repeated ingestion, missing timestamps, duplicate provider IDs, conflicting claims, and rollback/recovery. Prove existing watchlists, theses, snapshot tables and rejection records remain unchanged. Show a tiny fixture-driven round trip through real persistence, not mocks alone. | [P-01](#p-01) | P-01 test mapping | P-01 observed/proof mapping | Fully implemented offline persistence slice. New schema absent from tracked DB; lifecycle/extraction gaps remain. |
| **REQ-01-05** — **Gate:** exact schema and migrations documented; tests prove insert/read/update/idempotency and current-state compatibility; full pytest baseline passes or any known pre-existing failure is clearly isolated. Update HANDOFF/DECISIONS/ROADMAP, commit on existing feature branch if authorized, report exact commands and outputs, then **stop before Phase 02**. | [P-01](#p-01) | P-01 test mapping | P-01 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. New schema absent from tracked DB; lifecycle/extraction gaps remain. |

### Prompt 02 — Build one operational ingestion contract and the existing browser bridge adapter

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-02-01** — Execute Phase 02 only. Read social-intelligence EXECUTION, ROADMAP, DECISIONS, HANDOFF and verify Phase 01. Inspect the repo's real browser/Chrome/collector-to-GitHub inbox path (`memelab/bridge/`, inbox, manifests, CLI) and existing request/cache/error-handling utilities. Do not presume that cloud Python can reach crypto/social APIs. | [P-02](#p-02) | P-02 test mapping | P-02 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Bridge is a shaping/import adapter, not a page collector; same-file replay may exit 1 by design. |
| **REQ-02-02** — Implement a working provider-neutral ingestion framework with one **fixture-backed bridge/inbox adapter**, not a dozen unimplemented provider classes. Define versioned inbound observation schema, source identity, provider timestamp vs fetched timestamp, source URL, event IDs, content hash, access/rights metadata, validation errors, provenance, and connector health state. Provide an import/ingest command integrated with the existing CLI patterns. Support replay-safe checkpoints, bounded retries, rate-limit/cost budget hooks, batch size, stale-data detection, dedupe, quarantine for malformed payloads and structured logging that never prints secrets or prohibited content. | [P-02](#p-02) | P-02 test mapping | P-02 observed/proof mapping | Fully implemented fixture-backed ingestion slice. Bridge is a shaping/import adapter, not a page collector; same-file replay may exit 1 by design. |
| **REQ-02-03** — Demonstrate the actual established inbox ingestion route using a properly shaped fixture placed in the correct test location; do not commit privileged or copyrighted raw content. Re-running it twice must not create duplicate events. A bad item must be quarantined without discarding other good entries. One unavailable connector must not mark all sources healthy or destroy the run. | [P-02](#p-02) | P-02 test mapping | P-02 observed/proof mapping | Fully implemented fixture-backed ingestion slice. Bridge is a shaping/import adapter, not a page collector; same-file replay may exit 1 by design. |
| **REQ-02-04** — Create a provider adapter interface only for methods truly used by this implementation; document how X/Telegram will plug in. Respect existing object contracts instead of inventing `state/latest.json` integration if not present. | [P-02](#p-02) | P-02 test mapping | P-02 observed/proof mapping | Fully implemented fixture-backed ingestion slice. Bridge is a shaping/import adapter, not a page collector; same-file replay may exit 1 by design. |
| **REQ-02-05** — **Gate:** runnable import CLI; persisted verifiable observation; repeated ingestion idempotent; malformed and stale events handled; unit/integration tests pass and existing tests still pass. Update handoff/decision log, commit if authorized, show test output, **stop**. | [P-02](#p-02) | P-02 test mapping | P-02 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Bridge is a shaping/import adapter, not a page collector; same-file replay may exit 1 by design. |

### Prompt 03 — X/Twitter monitoring as a real, permitted source

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-03-01** — Execute Phase 03 only. Load the four social-intelligence handoff documents; check preceding gates and source-access design. Verify **current** X API availability, endpoint capabilities, read pricing, terms, historical windows and authorization requirements from official documentation. Do not scrape through unauthorized means or misrepresent API access. | [P-03](#p-03) | P-03 test mapping | P-03 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. No live access proof; extraction missing AUD-003; page cap skips backlog AUD-005; erasure missing AUD-009. |
| **REQ-03-02** — Implement one adapter for explicitly configured public X accounts/lists/search scopes insofar as official allowed APIs support them. Capture stable post IDs, original author, published time, link, text only when license/terms allow retention, reference type (original/reply/repost/quote), conversation context where accessible, and provenance/freshness. Produce normalized source observations via Phase 02. Implement pagination, rate limits, graceful 429/403 handling, incremental cursor/checkpoint, bounded budget and reingest deduplication. Mark unsupported reply/quote/repost/list visibility accurately. | [P-03](#p-03) | P-03 test mapping | P-03 observed/proof mapping | Partially implemented; credentials dependent; mock-only source evidence. No live access proof; extraction missing AUD-003; page cap skips backlog AUD-005; erasure missing AUD-009. |
| **REQ-03-03** — **Crucial:** if credentials or permission are not available, do not invent a live integration demo. Implement verified request/response contract from official docs with recorded synthetic HTTP fixtures, a connection-health command that reports `credentials_missing`, and a clearly documented sequence to authorize it. Skip actual billable reads unless explicit configured budget/consent exists. If X integration is commercially impractical, record justified source-alternative decision rather than substituting noncompliant scraping. | [P-03](#p-03) | P-03 test mapping | P-03 observed/proof mapping | Partially implemented; credentials dependent; mock-only source evidence. No live access proof; extraction missing AUD-003; page cap skips backlog AUD-005; erasure missing AUD-009. |
| **REQ-03-04** — Test originals/reposts/quotes, duplicate IDs, author changes, edited/deleted access limits, pagination, 429, 403, billing guard, timestamp correctness, cache freshness, and secret redaction. Show one CLI or integration-harness flow through stored observations. | [P-03](#p-03) | P-03 test mapping | P-03 observed/proof mapping | Partially implemented; credentials dependent; mock-only source evidence. No live access proof; extraction missing AUD-003; page cap skips backlog AUD-005; erasure missing AUD-009. |
| **REQ-03-05** — **Gate:** real adapter with confirmed API contract; either evidenced live authorized ingest **or explicitly marked unavailable**; reproducible fixture tests, budget behavior and no false live claims. Update docs, commit if authorized and **stop**. | [P-03](#p-03) | P-03 test mapping | P-03 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. No live access proof; extraction missing AUD-003; page cap skips backlog AUD-005; erasure missing AUD-009. |

### Prompt 04 — Telegram public-channel monitoring

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-04-01** — Execute Phase 04 only; read EXECUTION/ROADMAP/DECISIONS/HANDOFF and real connector code. Verify official Telegram Bot API or another explicitly permitted integration; explain channel membership/admin requirements and inaccessible historical/private content. Never pretend an arbitrary public channel can be read by a newly created bot. | [P-04](#p-04) | P-04 test mapping | P-04 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. No live bot/admin permission tested; dropped text is not handed to extraction (AUD-003). |
| **REQ-04-02** — Build an adapter for **authorized** channel messages and/or webhook/update capture into Phase 02's normalized observation model. Support channel ID, message ID, author/poster where provided, sent/edited time, forwarded-from provenance when actually available, message text only if rights permit, external source link if resolvable, and reply-to context when available. Include webhook authentication/validation as relevant, secret redaction, retry/idempotency, cursor/offset handling and channel-level health states. Integrate with current Chrome/GitHub inbox collection route only if that is actually the legitimate operational path. | [P-04](#p-04) | P-04 test mapping | P-04 observed/proof mapping | Partially implemented product path; credentials dependent. No live bot/admin permission tested; dropped text is not handed to extraction (AUD-003). |
| **REQ-04-03** — Test message edits, duplicate updates, forwards, deleted/inaccessible messages, authorization denial, out-of-order updates, and restart/resume after interrupted ingest. Do not count forwards as independent original claims. A small fixture-driven CLI demo must persist an observation with source provenance. If credentials and approved channels are not configured, surface explicit setup steps and `credentials_missing`/`access_denied` status without fabricating live observations. | [P-04](#p-04) | P-04 test mapping | P-04 observed/proof mapping | Partially implemented product path; credentials dependent. No live bot/admin permission tested; dropped text is not handed to extraction (AUD-003). |
| **REQ-04-04** — **Gate:** adapter is operational under documented permissions, or truthfully blocked while all permitted fixture paths work; full pytest passes. Update handoff, decisions, source-coverage table, commit on branch if authorized, **stop**. | [P-04](#p-04) | P-04 test mapping | P-04 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. No live bot/admin permission tested; dropped text is not handed to extraction (AUD-003). |

### Prompt 05 — Resolve exact token identity and snapshot market conditions

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-05-01** — Execute Phase 05 only. Read durable social handoff and inspect existing token identity, chain, provider, `normalize.py`, SQLite, DEX routing, market snapshots, and `pipeline.py`. **Reuse this infrastructure** rather than building another token analyst. | [P-05](#p-05) | P-05 test mapping | P-05 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Four chains; supplied provider bodies and posting candles only; provider denominator meanings not freshly certified. |
| **REQ-05-02** — Build a normalization/resolution service that maps post references to `(chain_id, verified_contract_or_mint)` and supports `resolved`, `ambiguous`, `unresolved`, and `conflicted`. Token symbols are weak evidence and may refer to unrelated assets. Contract references must be chain-valid; resolve quoted tickers only when corroborating trusted links/data are adequate. Store candidate identities and evidence rather than guessing. Honor Solana, Ethereum, Base, and BNB Chain only to extent supported by real upstream sources; mark others unsupported. | [P-05](#p-05) | P-05 test mapping | P-05 observed/proof mapping | Fully implemented supplied-body slice; fixture-only demonstration. Four chains; supplied provider bodies and posting candles only; provider denominator meanings not freshly certified. |
| **REQ-05-03** — Provide time-stamped market context using existing providers: price, valuation fields with supply-denominator meaning, reported pool liquidity, volume, pair IDs, and where available actual executable quotes. Differentiate observed-at-time versus historical-at-posting-time; never attach today's price as if it were the publication-time price. Handle missing historical snapshots honestly. Persist versioned facts with provider/units, quote currency, source URLs/IDs, fetched_at and validity window. | [P-05](#p-05) | P-05 test mapping | P-05 observed/proof mapping | Fully implemented supplied-body slice; fixture-only demonstration. Four chains; supplied provider bodies and posting candles only; provider denominator meanings not freshly certified. |
| **REQ-05-04** — Test same ticker across chains and contracts, contract typo, spoofed name, token migration, wrapped tokens, invalid chain, no history, missing pool, disagreeing providers, liquidity versus executable proceeds. Demonstrate one input message producing an **ambiguous** result and one confirmed address producing a resolved stored token reference. | [P-05](#p-05) | P-05 test mapping | P-05 observed/proof mapping | Fully implemented supplied-body slice; fixture-only demonstration. Four chains; supplied provider bodies and posting candles only; provider denominator meanings not freshly certified. |
| **REQ-05-05** — **Gate:** downstream can request exact token identity plus timestamped evidence; no silent symbol-only matches; tests and full baseline pass; commit/handoff and **stop**. | [P-05](#p-05) | P-05 test mapping | P-05 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Four chains; supplied provider bodies and posting candles only; provider denominator meanings not freshly certified. |

### Prompt 06 — Evidence-grounded structured claim extraction

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-06-01** — Execute Phase 06 only. Review durable handoff, existing LLM configuration, schema conventions and available normalized social observations. Implement one production-useful classifier/extractor with **validated structured output**, not a collection of vague prompt templates. | [P-06](#p-06) | P-06 test mapping | P-06 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. No real model semantic validation; collector handoff missing for X/TG; zero-price budget edge AUD-006. |
| **REQ-06-02** — From permitted source observations, extract token mentions and chain context; narrative tags; claim category (bullish, bearish, launch, catalyst, wallet, volume, liquidity, risk, commentary, education, promotion); claimed fact versus author opinion; time horizon; author position disclosure; quoted/reposted content provenance; uncertainty; source link and exact evidence spans or anchored references. Prevent text from being treated as instructions to the agent (prompt injection). Resolve token identity through Phase 05; allow `unresolved`. Never turn text such as 'smart money is buying' into verified wallet behavior. | [P-06](#p-06) | P-06 test mapping | P-06 observed/proof mapping | Partially implemented operational pipeline; standalone code tested. No real model semantic validation; collector handoff missing for X/TG; zero-price budget edge AUD-006. |
| **REQ-06-03** — Implement a deterministic fallback for extractable contracts/links if no LLM is configured. For substantive claims requiring a model, expose an `analysis_unavailable` result rather than false classification. Budget model usage, cache analyses by observation+model+prompt version, validate JSON, handle invalid/partial responses, and permit replay when extraction logic changes. Add a documented classification rubric and sample provenance-rich output in user-friendly English. | [P-06](#p-06) | P-06 test mapping | P-06 observed/proof mapping | Partially implemented operational pipeline; standalone code tested. No real model semantic validation; collector handoff missing for X/TG; zero-price budget edge AUD-006. |
| **REQ-06-04** — Test sarcasm, conditional claims, negations, repost attribution, contradictory statements, two similarly named tokens, unsupported token, fabricated contract, prompt injection inside a post, malformed model output, dedupe and reprocess behavior. Demonstrate storage and reportability of one claim without an LLM and one mock-provider structured analysis. | [P-06](#p-06) | P-06 test mapping | P-06 observed/proof mapping | Partially implemented operational pipeline; standalone code tested. No real model semantic validation; collector handoff missing for X/TG; zero-price budget edge AUD-006. |
| **REQ-06-05** — **Gate:** observable schema-validated pipeline from ingested item to cited claim; real/model-not-configured status truthful, tests pass. Record commit and handoff, then **stop**. | [P-06](#p-06) | P-06 test mapping | P-06 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. No real model semantic validation; collector handoff missing for X/TG; zero-price budget edge AUD-006. |

### Prompt 07 — Narrative clustering, originators, amplifiers and independent corroboration

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-07-01** — Execute Phase 07 only after inspecting the handoff and actual Phase 06 outputs. Build a **working** narrative engine that groups related claims by resolved contract or clearly labeled theme without conflating similarly named assets or fabricated social topics. | [P-07](#p-07) | P-07 test mapping | P-07 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Later extraction appears in older cutoff snapshot (AUD-001); semantic clustering intentionally not enabled, allowed by prompt. |
| **REQ-07-02** — Maintain first-observed time (not unknowable first-ever mention), source count, independently originated source count, forwarding/repost edges, common source dependencies, mentions per sliding window, rate of change, confidence, coverage limits, chain and linked-token context. Reposts/quotes that repeat a claim count as amplification, not independent validation. Avoid treating 'different accounts' as independent when all cite a shared original or show coordinated repost patterns. Mark inferred coordination as hypothesis rather than proven ownership. | [P-07](#p-07) | P-07 test mapping | P-07 observed/proof mapping | Partially implemented; temporal claim disproved. Later extraction appears in older cutoff snapshot (AUD-001); semantic clustering intentionally not enabled, allowed by prompt. |
| **REQ-07-03** — Implement deterministic clustering first (contract and structured tag/topic keys); use vector/LLM semantic clustering only where it can be evaluated against fixtures and has a reproducible fallback. Compute narrative snapshots and deltas across runs with timestamps, versioning and provenance links. Emit `insufficient_coverage` when volume/independence is not estimable. | [P-07](#p-07) | P-07 test mapping | P-07 observed/proof mapping | Partially implemented; temporal claim disproved. Later extraction appears in older cutoff snapshot (AUD-001); semantic clustering intentionally not enabled, allowed by prompt. |
| **REQ-07-04** — Tests: repeated reposts by 100 handles, two separate early originals, same token ticker different contracts, multi-token themes, conflicting narratives, changed opinion, deleted/inaccessible source, time-zone boundaries, stale data. Prove daily change results using two controlled fixture windows. Include explainable 'why this cluster' output. | [P-07](#p-07) | P-07 test mapping | P-07 observed/proof mapping | Partially implemented; temporal claim disproved. Later extraction appears in older cutoff snapshot (AUD-001); semantic clustering intentionally not enabled, allowed by prompt. |
| **REQ-07-05** — **Gate:** durable narrative snapshot and change summary; independent count defensible; full suite passes; update DECISIONS/HANDOFF, commit and **stop**. | [P-07](#p-07) | P-07 test mapping | P-07 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Later extraction appears in older cutoff snapshot (AUD-001); semantic clustering intentionally not enabled, allowed by prompt. |

### Prompt 08 — Trader registry, source credibility and evidence-based discovery

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-08-01** — Execute Phase 08 only. Read handoff, SQLite models, source coverage and narrative outputs. Implement a real, persistent **source/trader registry** that does not assume a profitable wallet owner is also a valuable public commentator. | [P-08](#p-08) | P-08 test mapping | P-08 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. No current real source selection or validated best-trader list; no person identity certainty. |
| **REQ-08-02** — Define distinguishable identities: social account, self-disclosed public wallet, observed wallet, verified attribution assertion, third-party leaderboard candidate, source organization and social network. Support multiple handles and multiple wallets without merging by name. Record explicit provenance, attribution confidence, timespan, platform, specialty, watch status, topical focus, and reason for following. Candidate categories: profitable-trading claimant, verified-wallet candidate, information originator, analytical source, amplifier, promoter/high-conflict. Never fabricate current rankings or seed 100 arbitrary accounts. | [P-08](#p-08) | P-08 test mapping | P-08 observed/proof mapping | Fully implemented offline registry slice; mock-only population. No current real source selection or validated best-trader list; no person identity certainty. |
| **REQ-08-03** — Implement candidate discovery from *sources actually accessible*, such as ingesting a permitted leaderboard file/API or analyst posts; evaluate claims about leaderboards separately. Implement manual review/approve/reject/update commands, searchable CLI list and safe import. Populate fixture candidates to demonstrate controls; label fixtures. Where provider access permits, ingest real current candidates with capture timestamps and direct URLs; otherwise explicitly leave candidates unverified. | [P-08](#p-08) | P-08 test mapping | P-08 observed/proof mapping | Fully implemented offline registry slice; mock-only population. No current real source selection or validated best-trader list; no person identity certainty. |
| **REQ-08-04** — Tests: identical screen names, handle rename, account suspension, wallet self-claim versus independently corroborated ownership, stale leaderboard, duplicate rankings, missing platform link, sources without wallets. Show candidate -> evidence -> reviewed registry record through the CLI. | [P-08](#p-08) | P-08 test mapping | P-08 observed/proof mapping | Fully implemented offline registry slice; mock-only population. No current real source selection or validated best-trader list; no person identity certainty. |
| **REQ-08-05** — **Gate:** registry records can be used by later attribution/performance stages; no unsupported 'best trader' assertions; tests and baseline pass, update handoff/commit, **stop**. | [P-08](#p-08) | P-08 test mapping | P-08 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. No current real source selection or validated best-trader list; no person identity certainty. |

### Prompt 09 — Verify wallet links and observe activity without identity overreach

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-09-01** — Execute Phase 09 only. Read handoff and inspect actual Helius/on-chain forensics (`memelab/forensics.py`, other on-chain modules), existing wallet tracker, provider abstraction and registry. Do not create wallet identity links from matching usernames or suggestive transfers alone. | [P-09](#p-09) | P-09 test mapping | P-09 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. No real Helius fetch tested; default 50 newest transactions; no EVM provider; live attribution collection absent (AUD-012). |
| **REQ-09-02** — Implement wallet-attribution assertions as independently auditable records: asserted trader/account; exact chain+wallet; evidence type (official account self-disclosure, signed message, independent linked source, third-party claim, transaction pattern); evidence URL/ID; observation and validity timestamps; confidence; reviewed/unreviewed; revoked/superseded. Separate real-world identity (generally unknown) from on-chain control hypothesis. Use publicly available wallets only. | [P-09](#p-09) | P-09 test mapping | P-09 observed/proof mapping | Partially implemented user capability; fixture tested. No real Helius fetch tested; default 50 newest transactions; no EVM provider; live attribution collection absent (AUD-012). |
| **REQ-09-03** — Reuse upstream transaction ingestion to monitor selected wallets, classify transfers/swaps/LP operations as distinct events, link relevant contracts, record transaction signature, chain, block time, fees, counterparties and source. Provide tracked-wallet add/remove/pause commands with safe defaults. When attribution is uncertain, permit wallet-level monitoring without claiming which person it belongs to. | [P-09](#p-09) | P-09 test mapping | P-09 observed/proof mapping | Partially implemented user capability; fixture tested. No real Helius fetch tested; default 50 newest transactions; no EVM provider; live attribution collection absent (AUD-012). |
| **REQ-09-04** — Tests: fake ownership claim, token transfer misclassified as sell, wallet-funded-by-same-wallet clustering hypothesis, custody address, relabeling of wallets, multiple chains, provider 429, missing signatures, stale transactions. Demonstrate exact transaction-classification flow using realistic fixtures and a verifiable provenance chain. | [P-09](#p-09) | P-09 test mapping | P-09 observed/proof mapping | Partially implemented user capability; fixture tested. No real Helius fetch tested; default 50 newest transactions; no EVM provider; live attribution collection absent (AUD-012). |
| **REQ-09-05** — **Gate:** reviewer can inspect *why* a wallet is linked or not linked; activity survives reload and does not become P&L until next phase; full tests and handoff/commit, **stop**. | [P-09](#p-09) | P-09 test mapping | P-09 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. No real Helius fetch tested; default 50 newest transactions; no EVM provider; live attribution collection absent (AUD-012). |

### Prompt 10 — Trading performance accounting with realistic limitations

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-10-01** — Execute Phase 10 only. Read handoff, inspect Phase 09 on-chain transaction classification and existing cost/quote modules. Implement transparent **wallet-level** performance reconstruction rather than trusting a leaderboard field or claiming complete person-level profitability. | [P-10](#p-10) | P-10 test mapping | P-10 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. No complete real-wallet reconstruction or exit proof; uncertain fetched-history inference (AUD-012). |
| **REQ-10-02** — Account for buys, sells, token decimals, swaps, fees, token transfers, airdrops, liquidity deposits/withdrawals, open inventory, cost basis, and missing-history intervals. Choose and document a defensible lot convention (e.g., FIFO or weighted average), including sensitivity where material. Separate realized P&L, unrealized mark-to-market, transaction costs and estimated liquidation proceeds. Do not classify incoming transfers as free profitable buys or assume external-wallet flows are gains. State when comprehensive reconstruction cannot be achieved. | [P-10](#p-10) | P-10 test mapping | P-10 observed/proof mapping | Implemented accounting slice; real result unverified. No complete real-wallet reconstruction or exit proof; uncertain fetched-history inference (AUD-012). |
| **REQ-10-03** — Calculate trade count, win rate with declared definition, median return, profit share from biggest winner, return excluding biggest winner, drawdown only where sufficient equity-series data exist, sample size and confidence/coverage. Report source history coverage and unknown fees. Prevent rankings on sparse or highly incomplete observations. Optional live provider comparisons must be labeled estimates and never substitute for accounting validation. | [P-10](#p-10) | P-10 test mapping | P-10 observed/proof mapping | Implemented accounting slice; real result unverified. No complete real-wallet reconstruction or exit proof; uncertain fetched-history inference (AUD-012). |
| **REQ-10-04** — Test partially missing transaction history, same token with multiple lots, wash-like transfers, fee-on-transfer tokens, decimal errors, rug with unexitable position, wallet-to-wallet transfers, profitable outlier, stablecoin peg changes and no-price scenario. Include fixture ledger with hand-checked numeric expected results; demonstrate wallet score refusing insufficient data. | [P-10](#p-10) | P-10 test mapping | P-10 observed/proof mapping | Implemented accounting slice; real result unverified. No complete real-wallet reconstruction or exit proof; uncertain fetched-history inference (AUD-012). |
| **REQ-10-05** — **Gate:** repeatable P&L calculation with deterministic reconciliation checks; gaps and mark-to-market vs executable proceeds explicit; existing full test suite passes; update docs/commit/handoff, **stop**. | [P-10](#p-10) | P-10 test mapping | P-10 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. No complete real-wallet reconstruction or exit proof; uncertain fetched-history inference (AUD-012). |

### Prompt 11 — Measure the predictive value of public posts, not just wallet profits

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-11-01** — Execute Phase 11 only. Read handoff, real historical market-data coverage, trader registry, stored claims and performance records. Implement the **Information Alpha Score** as a separate, uncertainty-aware evaluation of public commentary. | [P-11](#p-11) | P-11 test mapping | P-11 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Real trader alpha unvalidated; selection enumeration/historical provider absent; fixture export labelled real AUD-004. |
| **REQ-11-02** — Define timestamped event study: original public post timestamp, first observed timestamp, token identity, disclosed position/conflicts, pre/post trading if attributed, publication-to-price move lag, pre/post liquidity and matched comparison token group. Compute returns at configurable 1h, 6h, 24h, 72h, 7d only where history exists, maximum favorable/adverse excursion if observed path coverage permits, a realistic delay, estimated fees and execution frictions. Do not fabricate historic prices by replaying live quotes as if known at post time. Predefine selection rules and include all eligible negative/neutral calls, not only winners. | [P-11](#p-11) | P-11 test mapping | P-11 observed/proof mapping | Partially implemented research capability. Real trader alpha unvalidated; selection enumeration/historical provider absent; fixture export labelled real AUD-004. |
| **REQ-11-03** — Produce explainable metrics: coverage, number of independently evaluable calls, median relative return versus matched baseline, information lead-time distribution, false positives, failure to beat matched tokens, confidence intervals when statistically appropriate. Use conservative shrinkage / insufficient-data abstention; never assign a score of 95/100 on 3 calls. Keep source popularity out of the formula except as explicitly justified context. Version scoring rules and separate 'unverified', 'preliminary', and 'validated'. | [P-11](#p-11) | P-11 test mapping | P-11 observed/proof mapping | Partially implemented research capability. Real trader alpha unvalidated; selection enumeration/historical provider absent; fixture export labelled real AUD-004. |
| **REQ-11-04** — Tests: late promotion after pump, hindsight-selected call, repeated reposts, delisted tokens, price gaps, illiquid execution, null baseline, temporal leakage, zero eligible calls, conflicting bullish/bearish statements and a statistically noisy sample. Show an end-to-end fixture evaluation with transparent calculations and a source for every observation. | [P-11](#p-11) | P-11 test mapping | P-11 observed/proof mapping | Partially implemented research capability. Real trader alpha unvalidated; selection enumeration/historical provider absent; fixture export labelled real AUD-004. |
| **REQ-11-05** — **Gate:** the engine can legitimately decline to rank; wallet profits remain separate; tests pass; commit and record handoff, **stop**. | [P-11](#p-11) | P-11 test mapping | P-11 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Real trader alpha unvalidated; selection enumeration/historical provider absent; fixture export labelled real AUD-004. |

### Prompt 12 — Reconcile social claims with actual on-chain chronology

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-12-01** — Execute Phase 12 only. Read handoff and inspect observed claims, verified/uncertain wallet associations, swaps, on-chain timestamps and market snapshots. Build a clear **chronology/corroboration** component. | [P-12](#p-12) | P-12 test mapping | P-12 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. No joined real post/wallet/candle coverage; current-state historical joins warrant follow-up AUD-001/002. |
| **REQ-12-02** — For a resolved token and social source, generate one ordered timeline containing published post, first seen post, attributed-wallet buy/sell/transfer, major pool liquidity changes where observed, and market movement. Preserve timestamp precision/uncertainty and explain differences between chain slot time, source publication time, and collection time. Identify *observed patterns*: trade before talk, talk before trade, talk without observed trade, trade without observed talk, potential distribution during promotion. Absence of a monitored trade is not evidence that none occurred. An uncertain attribution must never become a definitive accusation. | [P-12](#p-12) | P-12 test mapping | P-12 observed/proof mapping | Implemented fixture-tested chronology slice. No joined real post/wallet/candle coverage; current-state historical joins warrant follow-up AUD-001/002. |
| **REQ-12-03** — Build a concise evidence summary with independent links and labeled **fact / inference / not established**. Register corroboration/risk flags in normalized outputs for later discovery pipeline use. Validate token and chain identity on every join. Implement time-window configuration, dedupe, missing-provider fallbacks, stale-evidence warnings and human-readable output. | [P-12](#p-12) | P-12 test mapping | P-12 observed/proof mapping | Implemented fixture-tested chronology slice. No joined real post/wallet/candle coverage; current-state historical joins warrant follow-up AUD-001/002. |
| **REQ-12-04** — Tests: delayed API delivery, missing/block timestamp, token symbol collision, conflicting wallets, same-minute ordering ambiguity, unrelated transfer, two separate persons using one custodian, promotional repost, missing price and source deletion. Demonstrate two fixtures: confident order and indeterminate order. | [P-12](#p-12) | P-12 test mapping | P-12 observed/proof mapping | Implemented fixture-tested chronology slice. No joined real post/wallet/candle coverage; current-state historical joins warrant follow-up AUD-001/002. |
| **REQ-12-05** — **Gate:** ordering is accurate or explicitly uncertain; links trace to original evidence; no unsupported ownership or manipulation claims; tests pass, handoff/commit, **stop**. | [P-12](#p-12) | P-12 test mapping | P-12 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. No joined real post/wallet/candle coverage; current-state historical joins warrant follow-up AUD-001/002. |

### Prompt 13 — Integrate social signals into the existing scout and catalyst workflow

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-13-01** — Execute Phase 13 only. Read handoff and inspect *actual* discovery/scout pipeline, ranking, module outputs, fatal-flaw criteria, watchlists, rejections, theses and report adapters. **Do not replace the existing research system.** | [P-13](#p-13) | P-13 test mapping | P-13 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Report adapter, not autonomous discovery/schedule; legacy core attention/launch integration remains absent. |
| **REQ-13-02** — Implement a focused adapter that transforms sourced social/narrative findings into **research candidates** compatible with the existing system. A social signal should attach originators/independent corroboration, freshness, contract+chain, confidence, promotional risks and relevant timeline evidence. Reuse existing token verification, liquidity, executable depth, holder concentration, LP control, token mechanics and risk screening. Preserve a hard separation between (a) narrative attention, (b) acceptable token structure, and (c) attractive executable entry. High hype cannot override fatal flaws. Candidates with only ticker mentions stay unresolved and out of tradable rankings. | [P-13](#p-13) | P-13 test mapping | P-13 observed/proof mapping | Fully implemented report-enrichment slice; operationally partial. Report adapter, not autonomous discovery/schedule; legacy core attention/launch integration remains absent. |
| **REQ-13-03** — Extend the existing CLI/`social-note` workflow where it fits; don't create duplicate token scoring or two parallel watchlists. Ensure existing `scout` runs with social intelligence disabled or no data produce backward-compatible results. Define opt-in enablement and configurable weight/signal policy with provenance. Social findings must have zero *automatic* trade execution impact. | [P-13](#p-13) | P-13 test mapping | P-13 observed/proof mapping | Fully implemented report-enrichment slice; operationally partial. Report adapter, not autonomous discovery/schedule; legacy core attention/launch integration remains absent. |
| **REQ-13-04** — Tests: fatal-flaw override, spoof contract, social 'top pick' with no liquidity, valid candidate with credible early discussion, no social data, stale sources, conflicting narratives, repeated ingest, rejected thesis and later materially changed evidence. Produce a side-by-side before/after fixture scout report demonstrating an enriched research candidate and an unchanged rejected token. | [P-13](#p-13) | P-13 test mapping | P-13 observed/proof mapping | Fully implemented report-enrichment slice; operationally partial. Report adapter, not autonomous discovery/schedule; legacy core attention/launch integration remains absent. |
| **REQ-13-05** — **Gate:** integrated path genuinely executes; old pipeline still works; explicit no-op when source unavailable; baseline full pytest passes, commit/handoff, **stop**. | [P-13](#p-13) | P-13 test mapping | P-13 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Report adapter, not autonomous discovery/schedule; legacy core attention/launch integration remains absent. |

### Prompt 14 — Produce a readable, cited intelligence feed and digest

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-14-01** — Execute Phase 14 only. Read handoff and inspect existing markdown reporting, CLI and output conventions. Produce one useful **read-only feed renderer** over real stored observations/claims/narratives that works without a paid dashboard or a configured LLM. | [P-14](#p-14) | P-14 test mapping | P-14 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Real main has no social schema; summaries omitted by D-095; cutoff inherits upstream defects. |
| **REQ-14-02** — Create CLI commands consistent with current code, e.g. `social feed`, `social brief`, `social trader-digest`, if parser structure supports them. Generate (1) last-24-hour narrative-first morning brief, (2) trader conversation digest with changed positions and disagreements, and (3) searchable/filterable feed by chain, token, source, time or risk. Every item should give: what happened, first observed/published time, who said it, original links, independence vs repetition, why it matters, what is corroborated, what is speculation, reasons to doubt, liquidity/exit caveat, research next step, and data freshness/coverage. Do not fabricate current conversations when using fixtures; clearly watermark fixture demo outputs. Group discussion by token/theme rather than reverse-chronological influencer spam. | [P-14](#p-14) | P-14 test mapping | P-14 observed/proof mapping | Implemented fixture-tested renderer; no real feed populated. Real main has no social schema; summaries omitted by D-095; cutoff inherits upstream defects. |
| **REQ-14-03** — Render through current report pipeline, with safe markdown escaping and no raw sensitive text in a public report. Add a stable machine-readable JSON representation so later alerts/scheduler can consume it. Handle no signals by reporting 'no supported high-priority observations' rather than inventing news. Do not yet send notifications or schedule jobs. | [P-14](#p-14) | P-14 test mapping | P-14 observed/proof mapping | Implemented fixture-tested renderer; no real feed populated. Real main has no social schema; summaries omitted by D-095; cutoff inherits upstream defects. |
| **REQ-14-04** — Tests: 0/1/multiple narratives, conflicting opinions, repeated forwards, unresolved ticker, source-link sanitation, stale data, time zone formatting, missing paid model, prompt-injection text, identical rerun. Include readable sample fixture report and one CLI command to reproduce it. | [P-14](#p-14) | P-14 test mapping | P-14 observed/proof mapping | Implemented fixture-tested renderer; no real feed populated. Real main has no social schema; summaries omitted by D-095; cutoff inherits upstream defects. |
| **REQ-14-05** — **Gate:** durable useful generated report, linked sources and provenance, no fake live output, full suite green; handoff/commit, **stop**. | [P-14](#p-14) | P-14 test mapping | P-14 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Real main has no social schema; summaries omitted by D-095; cutoff inherits upstream defects. |

### Prompt 15 — Controlled research alerts and scheduling

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-15-01** — Execute Phase 15 only. Read the four durable handoff documents and inspect current report, workflow, browser bridge, repo Actions/scheduler and configuration patterns. Implement **research-only** alerts consuming Phase 14 events, not another detector. | [P-15](#p-15) | P-15 test mapping | P-15 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. External transports live-untested, no job enabled; templates are not scheduler deployment. |
| **REQ-15-02** — Define alert policies for: independent reputable sources converging on a narrative; verified monitored-wallet activity corroborating a claim; new important risk evidence; previously bullish analyst switching stance; exceptional growth in conversation vs its baseline. Require chain+contract and source freshness for token-specific alerts. Add severity, reason, confidence, provenance, cooldown, dedupe key, per-day message cap, per-provider API cost ceiling, quiet hours and time-zone-aware schedule (America/New_York). Avoid more frequent polling than upstream refresh capability. | [P-15](#p-15) | P-15 test mapping | P-15 observed/proof mapping | Implemented file/dry-run slice; live delivery untested/credential dependent. External transports live-untested, no job enabled; templates are not scheduler deployment. |
| **REQ-15-03** — Create an operational local/file sink first and optionally one authorized Telegram bot or email transport only if credentials are configured. Never claim delivery occurred when only a local preview was written. Implement dry-run mode and explicit send enablement, safe handling for destination tokens, retry policy and delivery ledger (attempted, succeeded, failed). Respect public-repo secrets and opt-in user notification preferences. Make daily/weekly job templates with timezone/DST tests, but avoid enabling jobs without consent/configuration. | [P-15](#p-15) | P-15 test mapping | P-15 observed/proof mapping | Implemented file/dry-run slice; live delivery untested/credential dependent. External transports live-untested, no job enabled; templates are not scheduler deployment. |
| **REQ-15-04** — Tests: duplicate alert across retries, cooldown reset, 100 reposts and no independent corroboration, stale wallet event, repeated schedule after restart, missing token, notification transport failure, timezone/DST changes and no-alert day. Show a fixture-generated alert, a deduped second run, and readable delivery-state output. | [P-15](#p-15) | P-15 test mapping | P-15 observed/proof mapping | Implemented file/dry-run slice; live delivery untested/credential dependent. External transports live-untested, no job enabled; templates are not scheduler deployment. |
| **REQ-15-05** — **Gate:** no alert spam, explicit configured delivery, work under missing credentials via dry-run, full tests pass. Handoff/commit, **stop**. | [P-15](#p-15) | P-15 test mapping | P-15 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. External transports live-untested, no job enabled; templates are not scheduler deployment. |

### Prompt 16 — Build immutable signal ledger and forward evaluation

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-16-01** — Execute Phase 16 only. Read handoff and inspect data models, market snapshot retrieval, reports and timing conventions. Implement a **forward-looking signal/outcome ledger** that records what the system knew when it emitted a research signal. | [P-16](#p-16) | P-16 test mapping | P-16 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Not automatically invoked from real signals/schedules; no historical/live provider; no real forward efficacy. |
| **REQ-16-02** — Capture signal ID, classifier/scoring versions, source/claim references, resolved contract+chain, event time, generated time, observed price, route/liquidity conditions where available, evaluation horizon, position-size assumptions, hypothetical execution lag/fees and missing data. Record immutable original context; later fetched market outcomes must append rather than rewrite the original signal. Compute returns only with dated price observations; max excursion only with sufficiently granular path history; distinguish actual route quotes from modeled impact. Never fabricate unobserved exits or treat displayed P&L as executable proceeds. | [P-16](#p-16) | P-16 test mapping | P-16 observed/proof mapping | Partially implemented end-user feature; standalone slice tested. Not automatically invoked from real signals/schedules; no historical/live provider; no real forward efficacy. |
| **REQ-16-03** — Build `social evaluate` or codebase-conforming command that appends 1h/6h/24h/72h/7d outcomes as they mature; mark outcomes `pending`, `measured`, `missing`, `non-executable`, or `invalidated` with reasons. Preserve failures and rejected candidates (no cherry-picking). Add a report showing outcome-coverage rates and reasons for exclusion. | [P-16](#p-16) | P-16 test mapping | P-16 observed/proof mapping | Partially implemented end-user feature; standalone slice tested. Not automatically invoked from real signals/schedules; no historical/live provider; no real forward efficacy. |
| **REQ-16-04** — Tests: look-ahead protection, revising underlying provider snapshots, delayed publication, delisted tokens, lost liquidity, missing midpoints, duplicate evaluation, source deletion, postponed windows, price-quote mismatch, and no outcomes matured. Demonstrate fixture signal snapshot before/after two forward evaluations with zero original-context mutation. | [P-16](#p-16) | P-16 test mapping | P-16 observed/proof mapping | Partially implemented end-user feature; standalone slice tested. Not automatically invoked from real signals/schedules; no historical/live provider; no real forward efficacy. |
| **REQ-16-05** — **Gate:** auditable chronological ledger, deterministic resumption, transparent missing outcomes, baseline suite passes. Update handoff and commit, **stop**. | [P-16](#p-16) | P-16 test mapping | P-16 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Not automatically invoked from real signals/schedules; no historical/live provider; no real forward efficacy. |

### Prompt 17 — Historical replay, baselines and statistical honesty

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-17-01** — Execute Phase 17 only. Read handoff, available historical social and market windows, information-value scoring, outcome ledger and existing testing methodology. This phase is **not** permission to fabricate a 90-day backtest where history is missing. | [P-17](#p-17) | P-17 test mapping | P-17 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Database claim availability backdated and assertion history not causal (AUD-002); intervals ignore some dependence. |
| **REQ-17-02** — Implement a causal chronological replay harness with a cutoff clock: at each replay step, only posts, trades, prices and provider data demonstrably available at or before the cutoff are accessible. Version source coverage and scoring rules. Support matched-token baselines by chain, capitalization/liquidity band and calendar regime where samples allow. Compare (a) individual analyst signal, (b) independent convergence, (c) social+wallet confirmation, (d) raw mention/trending baseline; estimate eligible sample count, coverage, precision, median relative performance, max adverse excursion and hypothetical executability, with credible uncertainty ranges and multiple-testing cautions where meaningful. | [P-17](#p-17) | P-17 test mapping | P-17 observed/proof mapping | Partially implemented; database-path no-leakage claim unverified/disproved. Database claim availability backdated and assertion history not causal (AUD-002); intervals ignore some dependence. |
| **REQ-17-03** — Design strict chronological train/validation/test splits. Do not tune thresholds on held-out future outcomes. Make it easy to run a **synthetic fixture replay** demonstrating no leakage. Real results must be labeled 'insufficient sample/data' if coverage is poor; do not extrapolate absent data. Produce readable validation report distinguishing forward test from backtest and selection bias. | [P-17](#p-17) | P-17 test mapping | P-17 observed/proof mapping | Partially implemented; database-path no-leakage claim unverified/disproved. Database claim availability backdated and assertion history not causal (AUD-002); intervals ignore some dependence. |
| **REQ-17-04** — Tests: future information injected into training, duplicated reposts, missing delisted-token prices, huge win dominating results, survivorship bias, provider publication lag, no valid matched controls, contradictory signals, no tradable depth and insufficient sample. Demonstrate a test that fails if the harness accesses future evidence. | [P-17](#p-17) | P-17 test mapping | P-17 observed/proof mapping | Partially implemented; database-path no-leakage claim unverified/disproved. Database claim availability backdated and assertion history not causal (AUD-002); intervals ignore some dependence. |
| **REQ-17-05** — **Gate:** trustworthy replay tooling, and an honest result (including 'cannot validate yet' when necessary); full pytest passes. Handoff/commit, **stop**. | [P-17](#p-17) | P-17 test mapping | P-17 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Database claim availability backdated and assertion history not causal (AUD-002); intervals ignore some dependence. |

### Prompt 18 — End-to-end release engineering, operational audit and delivery

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-18-01** — Execute Phase 18 only. Read handoff and every prior phase's commit/change/test record. Audit the **actual implemented code** against acceptance criteria, not the original conceptual specification. No new speculative provider integrations or sweeping refactors in this release phase. | [P-18](#p-18) | P-18 test mapping | P-18 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Full suite red; static types absent; single-data-flow proof absent AUD-014; live/deployment gates remain blocked. |
| **REQ-18-02** — Run clean-environment setup, migrations, fresh fixture inbox load, duplicate replay, token resolution, structured extraction, narrative change, trader registry, wallet attribution, P&L reconstruction, information-alpha evaluation, social/on-chain chronology, main discovery integration, report generation, alert dry-run, forward outcome evaluation and causal replay. Capture exact commands and outputs. Run full test suite and reasonable lint/type/static/security checks already used in repo. Audit public repo for credential leakage, restricted social content, accidental wallet keys, public redistribution concerns, schema incompatibility, accidental live billable requests and excessive logs. Verify no trading execution exists. | [P-18](#p-18) | P-18 test mapping | P-18 observed/proof mapping | Partially implemented release acceptance. Full suite red; static types absent; single-data-flow proof absent AUD-014; live/deployment gates remain blocked. |
| **REQ-18-03** — Provide README, architecture and operations runbook for non-programmer: source access, costs, env variable names (never secret values), CLI quick start, first-ever setup, schedule enable/disable, maintenance, data deletion, troubleshooting, known unsupported features, and proper citation/uncertainty standards. Make configuration opt-in, defaults safe and routes replayable. Produce two example reports: clearly fixture-only and authorized real-data only if genuinely captured. Validate no-signal/no-credentials behavior. Create a release checklist with each requirement `PASS`, `BLOCKED`, or `NOT IMPLEMENTED`, proof location and decision, not a vague 'done'. | [P-18](#p-18) | P-18 test mapping | P-18 observed/proof mapping | Partially implemented release acceptance. Full suite red; static types absent; single-data-flow proof absent AUD-014; live/deployment gates remain blocked. |
| **REQ-18-04** — Commit finalized changes on feature branch if authorized, open a pull request if repo access permits; never force-push `main`. Record commit/PR URL. Summarize operational integrations and exact blockers. **Stop after delivery.** | [P-18](#p-18) | P-18 test mapping | P-18 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Full suite red; static types absent; single-data-flow proof absent AUD-014; live/deployment gates remain blocked. |

### Prompt 19 — Add Reddit and Farcaster sources after the core system works

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-19-01** — Run only after Phase 18 is accepted, or earlier only if there is a proven research-critical requirement. Read EXECUTION/ROADMAP/DECISIONS/HANDOFF; inspect actual connector contract and official/authorized Reddit and Farcaster API options, including current limits and rights. Keep these as two distinct adapters; if one is blocked, complete and test the other rather than creating empty stubs. | [P-19](#p-19) | P-19 test mapping | P-19 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Missing entirely on main; no actual Reddit approval or Farcaster hub availability; no scheduled operation. |
| **REQ-19-02** — For Reddit, support selected approved communities and submissions/comments with canonical IDs, parent relations, edited/deleted states, rate limits, cross-post provenance and enough context to distinguish independent threads from cross-post amplification. For Farcaster, support the available approved cast/channel APIs and recasts/replies, with stable identifiers and social identity/provenance. In both, conform to the Phase 02 normalized event schema and data minimization controls; do not ingest private messages or bypass terms. | [P-19](#p-19) | P-19 test mapping | P-19 observed/proof mapping | Main missing; feature built/fixture-only/access dependent. Missing entirely on main; no actual Reddit approval or Farcaster hub availability; no scheduled operation. |
| **REQ-19-03** — Deliver adapter-specific fixtures and tests; run one source-to-storage-to-claim-to-narrative report flow for each functioning adapter. Add connector cost/health status and precise setup instructions. If permission unavailable, mark blocked without claiming operational status. Update docs and handoff, commit if authorized; **stop**. | [P-19](#p-19) | P-19 test mapping | P-19 observed/proof mapping | Main missing; feature built/fixture-only/access dependent. Missing entirely on main; no actual Reddit approval or Farcaster hub availability; no scheduled operation. |

### Prompt 20 — Add compliant Discord community monitoring

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-20-01** — Run after Phase 18 unless priority and access justify earlier execution. Read durable handoff and inspect official Discord gateway/API docs and privileged message-content-intent rules. Confirm bot installation and permissions for selected servers/channels. Never assume a public invite grants programmatic collection rights. Never attempt private-message access or token-based self-bot scraping. | [P-20](#p-20) | P-20 test mapping | P-20 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Missing on main; live Gateway transport NOT IMPLEMENTED (AUD-013); no consenting live server tested. |
| **REQ-20-02** — Implement permitted server/channel observations with channel IDs, message IDs, author/account, reply thread, edits/deletions when observable, UTC publication and ingestion times, forwarding/link provenance and allowed content retention. Rate-limit and permission-denied handling must be correct and connectors must report missing privileged intent clearly. Integrate into the existing normalized ingestion, token resolver, claim extraction and narrative feed; do not introduce a second social schema. | [P-20](#p-20) | P-20 test mapping | P-20 observed/proof mapping | Main missing; feature partial; mock-only Gateway. Missing on main; live Gateway transport NOT IMPLEMENTED (AUD-013); no consenting live server tested. |
| **REQ-20-03** — Test channel permission revocation, intent missing, duplicate gateway events, message edits, quote/link duplication, out-of-order events, reset checkpoint, no available text and no-source day. Demonstrate a full fixture flow. Live demonstration only with authorized guild and configured bot. Commit tests/docs, update handoff, **stop**. | [P-20](#p-20) | P-20 test mapping | P-20 observed/proof mapping | Main missing; feature partial; mock-only Gateway. Missing on main; live Gateway transport NOT IMPLEMENTED (AUD-013); no consenting live server tested. |

### Prompt 21 — Add YouTube metadata and public captions when permitted

| Requirement ID / original text | Implementation / functions | Tests | Observed behavior and proof | Completion / limitations |
|---|---|---|---|---|
| **REQ-21-01** — Run after Phase 18 unless a verified high-value analyst relies substantially on public long-form content. Read handoff and verify official YouTube Data API, available captions/transcript access, quota terms and content retention rights. No prohibited downloads or fictional transcription access. | [P-21](#p-21) | P-21 test mapping | P-21 observed/proof mapping | Historical/process evidence only; current tests do not prove all prior approvals or gates.. Missing on main; keys/rights/terms review unavailable; outside-channel public captions not generally accessible; guest attribution is channel-level. |
| **REQ-21-02** — Implement authorized channel/video metadata ingestion and transcript snippets where access is legally/technically allowed. Preserve video ID, channel, published time, caption/transcript time offsets, source link/timepoint and quotation context. Do not mistake video publication time for a claim's exact spoken timestamp when transcripts are unavailable; never evaluate a prediction using a future livestream transcript prior to its broadcast. Add verified extracted token mentions, attribution and narrative relevance through current pipeline. Focus on periodic contextual intelligence, not real-time launch detection. | [P-21](#p-21) | P-21 test mapping | P-21 observed/proof mapping | Main missing; feature built/fixture-only/access dependent. Missing on main; keys/rights/terms review unavailable; outside-channel public captions not generally accessible; guest attribution is channel-level. |
| **REQ-21-03** — Test multi-token mentions, missing captions, delayed livestream archiving, timestamp drift, channel/video dedupe, language/translation uncertainty, YouTube quota failure, and unavailable authorized transcripts. Demonstrate source-to-report fixture path and, only when permitted, an authenticated public-data smoke test. Document costs and limitations, update handoff/commit, **stop**. | [P-21](#p-21) | P-21 test mapping | P-21 observed/proof mapping | Main missing; feature built/fixture-only/access dependent. Missing on main; keys/rights/terms review unavailable; outside-channel public captions not generally accessible; guest attribution is channel-level. |

## Cross-phase and carry-over requirements

| Requirement | Implementation / functions | Tests and observed behavior | Audited state and limitations |
|---|---|---|---|
| Research-only, no signing/trading | sigverify.py verification only; release_audit.py patterns; policy trade_execution_impact | test_release_tools.py / content guard; main scan finds no execution path; fixture runs zero network | Verified within inspected source/scan scope; no comprehensive security certification |
| Accurate source health; never call fixture success live | X/TG health; feature sources_cli/api health; labelled fixtures | No-credentials expected refusals pass; main DB lacks new social schema | Implemented health reporting; no upstream access or remote scheduler state verified |
| Public/private minimization and source provenance | store.check_summary; ingest.validate_item; private.py; content_guard.scan | Existing guards pass; alpha export provenance probe fails | Partial end-to-end guarantee: AUD-004; source erasure gaps AUD-009 |
| Browser X/Telegram route, manual captures using inbound contract | bridge/social.js only shapes supplied items; legacy social-note distinct | No new page collector/manual-capture-to-ingester acceptance path found; roadmap C-4/C-6/C-7 | Documented but not implemented; earlier standing browser preference was not delivered |
| Core m19 attention, launch social and catalyst attention consume new metrics | New report research adapter; legacy modules remain older logic | test_social_research covers reporting, not these module integrations | Documented carry-overs C-17/C-18, missing integration; opt-in report enrichment exists |
| Historical prices and real-time immutable recording / state continuity | alpha_store.put_series; outcomes_ledger.record_signal; state.py | Supplied series/manual records demonstrated; no automatically captured real path | Missing historical provider/automatic wiring/social state export: AUD-007/008 |
| Full-suite-green gates | full tests, same catalyst assertion failure on both refs | main 651/1, feature 748/1; disposable tree gets BRETT report | Unmet; known pre-existing exception recorded, AUD-011 |
| No unused success-shaped interfaces | Built APIs and pure engines; fixture-only DiscordGatewayAdapter | Release demos pass, Gateway live command explicitly unavailable | Partial; Gateway protocol is not a transport, AUD-013; no claim it is live |

Coverage: 105 exact original requirement paragraphs/numbered instructions across all 22 prompts, plus cross-phase expectations and explicit carry-overs. Runtime demonstration evidence is confined to offline fixtures and inspected code.

## Release-18 checklist reconciliation

The repository's 66-row release checklist is a secondary claim register. Its PASS/BLOCKED values are not imported as this audit's verdict. Rows 1–22 are assessed through P-00–P-18 and AUD-003/014; rows 23–26 through actual suite/static results (full green/type checks unmet); rows 27–35 through the limited scanner/content/migration evidence (zero matches is not universal proof); rows 36–54 through docs/renderers/defaults and historical paths (live and lifecycle limits retained); rows 55–57 and 66 through git history (merge now happened, stale checklist); rows 58–65 through credentials, live transport, historical provider and scheduling limitations. Fixture-safe source demos were permitted by original prompts 03/04/19–21. No missing-credential feature is falsely declared live.