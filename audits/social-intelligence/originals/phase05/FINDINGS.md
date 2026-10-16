# Findings register

Audit date: 2026-10-13. Primary baseline `698f73b854567ce60b56ce275b5ab6822a9d5f60`; additional reviewed feature tip `3f27fc788f9ab88286b8041355e5445fdfdf012c`. No application fixes were made.

Severity describes impact on research/operational reliability: High can invalidate core intelligence or readiness; Medium affects coverage, provenance, lifecycle or release confidence. None is a demonstrated financial loss or exploited vulnerability. Confidence is High unless noted; live-service behavior remains unverified. Findings include defects, delivery gaps and documented limitations; a documented limitation is not concealment.

| ID | Finding | Severity | Evidence state |
|---|---|---|---|
| AUD-001 | Historical narrative cutoff includes later extractions | High | Verified |
| AUD-002 | Replay database adapter backdates derived claims and current wallet links | High | Verified for claim timing; source-confirmed for links |
| AUD-003 | X and Telegram collection is disconnected from token resolution and claims | High | Verified |
| AUD-004 | Fixtures can be exported as real alpha input | High | Verified |
| AUD-005 | X page-cap truncation advances the newest cursor | Medium | Verified |
| AUD-006 | Zero-price configuration defeats zero monthly model cost cap | Medium | Verified for guard arithmetic; live untested |
| AUD-007 | Scheduled operation and real forward recording are not wired | High | Verified absence in repository paths; external scheduler unknown |
| AUD-008 | No real social efficacy or trader ranking has been validated | High | Verified data absence; performance claims unverified |
| AUD-009 | Deleted X observations have no erasure path | Medium | Verified |
| AUD-010 | Latest source expansions are not present in main; handoff and release instructions drifted | Medium | Verified |
| AUD-011 | Full suite remains red and tests write reports into their checkout | Medium | Verified; pre-existing |
| AUD-012 | Wallet accounting depends on incomplete imported history and supplied prices | Medium | Verified limitation |
| AUD-013 | Discord live Gateway transport is not shipped | Medium | Verified |
| AUD-014 | Release PASS is a staged fixture demonstration, not one production data flow | Medium | Verified |
| AUD-015 | Explicit feed snapshot ID bypasses historical cutoff | High | Phase 01 independently reproduced |
| AUD-016 | Adapter iterator exception escapes ingestion and leaves RUNNING status | Medium | Phase 01 custom-adapter reproduction |
| AUD-017 | Historical feed loads chronology flags created after its cutoff | High | Phase 01 independently reproduced |

## AUD-001 — Historical narrative cutoff includes later extractions

- **Description:** Historical narrative cutoff includes later extractions.
- **Evidence:** `narratives.py::_load_claims` accepts cutoff but does not filter extraction timestamps; it selects current unsuperseded extractions. `snapshot` filters observation time instead. Both branch probes return one cluster at cutoff 1791849600 from a claim extracted at 1791936000.
- **Affected component:** Narrative history / feed.
- **Severity:** High.
- **Confidence:** High; Verified.
- **User impact:** Past snapshots can acquire interpretations or token resolutions the engine did not know at the time. Immutable storage preserves a computed run; it does not make its input selection causal.
- **Recommended next investigation:** Investigate extraction, identity, supersession, account classification, references and coverage availability at every historical read; add late-extraction and later-revision mutation cases.

## AUD-002 — Replay database adapter backdates derived claims and current wallet links

- **Description:** Replay database adapter backdates derived claims and current wallet links.
- **Evidence:** `replay_sources.py::from_db` sets claim availability to item first_observed_at and reads all CALL rows without current-extraction filtering. Wallet assertions are selected by current ACTIVE status, without historical observed/validity/review clocks. Probe: extracted_at=10000 becomes available_at=120. The cutoff harness sees only that already-backdated export.
- **Affected component:** Historical replay.
- **Severity:** High.
- **Confidence:** High; Verified for claim timing; source-confirmed for links.
- **User impact:** No-leakage output can be true for the exported document while the database-to-document transformation has already leaked future knowledge. Superseded CALLs can also remain eligible.
- **Recommended next investigation:** Independently test database export plus replay together using late extraction, corrected identity, superseded claims and future wallet approvals; reconcile account entity IDs with social account IDs.

## AUD-003 — X and Telegram collection is disconnected from token resolution and claims

- **Description:** X and Telegram collection is disconnected from token resolution and claims.
- **Evidence:** `x_api.py::post_item`, `telegram_bot.py::message_item` hash/drop text. Their CLI ingest path calls ingestion, not extraction. `extraction.py::extract_observation` requires text from caller/private storage. `CLAIMS_06.md` explicitly defers wiring. Probe: X ingests one contract-bearing observation, creates zero token resolutions and zero claims on both branches. Later TextSink exists for optional adapters only.
- **Affected component:** Core source-to-intelligence pipeline.
- **Severity:** High.
- **Confidence:** High; Verified.
- **User impact:** Adding source credentials will not by itself produce token-linked narratives, alpha or a useful digest from the primary sources.
- **Recommended next investigation:** Run an offline primary-source-to-resolved-claim-to-narrative acceptance test with provider bodies and inspect an authorized in-memory handoff design.

## AUD-004 — Fixtures can be exported as real alpha input

- **Description:** Fixtures can be exported as real alpha input.
- **Evidence:** `alpha_store.py::build_input` hardcodes is_fixture=False, selects claims without fixture filtering; `load_series` also loads all series without filtering is_fixture. Probe exports one claim from access_mode=fixture and labels input_is_fixture=false on both branches. This is a provenance failure; the probe does not establish a numerically validated false score.
- **Affected component:** Information alpha provenance.
- **Severity:** High.
- **Confidence:** High; Verified.
- **User impact:** Synthetic observations can enter an apparently real analysis and undermine evidence separation.
- **Recommended next investigation:** Test mixed real/fixture databases through alpha CLI, enforce origin propagation, and inspect other database export boundaries.

## AUD-005 — X page-cap truncation advances the newest cursor

- **Description:** X page-cap truncation advances the newest cursor.
- **Evidence:** `x_api.py::XApiAdapter._timeline` emits a GAP at max_pages_per_scope, breaks, then writes newest_id and last_status=OK for committed pages. Existing `test_page_cap_records_gap_and_advances_cursor` expects this. Probe: health DEGRADED but cursor last_status=OK and newest_id advanced despite an outstanding page. Later since_id filters out older unread posts.
- **Affected component:** X incremental collection.
- **Severity:** Medium.
- **Confidence:** High; Verified.
- **User impact:** Busy sources can permanently lose the capped backlog through ordinary incremental runs unless deliberately backfilled; missing calls distort source comparisons. The gap itself is honestly recorded.
- **Recommended next investigation:** Simulate two capped runs and prove recovery of every eligible post; investigate separate head and backlog cursors.

## AUD-006 — Zero-price configuration defeats zero monthly model cost cap

- **Description:** Zero-price configuration defeats zero monthly model cost cap.
- **Evidence:** `llm.py::Budget.allow` rejects missing prices but accepts 0; `worst_case_usd` returns 0 and checks estimated spend > cap. `provider_from_config` checks allow_billable, provider/model and key but not positive rates. Offline probe: live-mode guard with cap=0, input/output prices=0 returns no refusal. No request or credential was used.
- **Affected component:** Model billing guard.
- **Severity:** Medium.
- **Confidence:** High; Verified for guard arithmetic; live untested.
- **User impact:** An operator who enables billing while leaving zero prices can permit a real paid call under a purported zero cost cap. This does not affect off-by-default configurations. Concurrent-spend reservations and token estimates also need investigation.
- **Recommended next investigation:** Exercise the full fake-transport provider path with enabled billing and zero/negative prices, missing usage and concurrent workers before any paid testing.

## AUD-007 — Scheduled operation and real forward recording are not wired

- **Description:** Scheduled operation and real forward recording are not wired.
- **Evidence:** `alerts_schedule.py` defines disabled templates; `outcomes_ledger.py::record_signal` and outcomes CLI exist, but collectors/feed/alerts do not automatically record all real signals. `state.py` does not export the new social table set. ROADMAP carry-overs retain scheduling and state integration. Release paths invoke stages manually; tracked DB contains only legacy social_snapshots, not the new social schema. No scheduled connector run was demonstrated.
- **Affected component:** Operations / outcomes / integration.
- **Severity:** High.
- **Confidence:** High; Verified absence in repository paths; external scheduler unknown.
- **User impact:** There is no demonstrated unattended collection-to-digest-to-alert-to-forward-evaluation service. Private ledger continuity across ephemeral sessions is not established.
- **Recommended next investigation:** Inventory actual job definitions and persistence locations read-only, then design a full scheduled dry run including export/import and restart continuity.

## AUD-008 — No real social efficacy or trader ranking has been validated

- **Description:** No real social efficacy or trader ranking has been validated.
- **Evidence:** Tracked DB has no new social tables. Alpha/performance consume supplied data. Replay real-data output is INSUFFICIENT_DATA for all four strategies. Registry does not certify profitable people. `REPLAY_17.md` admits correlated outcome windows. Fixture tests and supplied ledger hand checks pass; no real public-source alpha, complete wallet P&L or forward outcome evidence exists in the audited stores.
- **Affected component:** Quantitative research / trader discovery.
- **Severity:** High.
- **Confidence:** High; Verified data absence; performance claims unverified.
- **User impact:** The system cannot establish who is currently a strong trader, whether social calls predict returns, or whether hypothetical profits can actually be exited.
- **Recommended next investigation:** Collect an authorized, complete selection universe with losing/delisted tokens and timestamped controls; investigate dependence-aware intervals and sensitivity to executable-depth assumptions.

## AUD-009 — Deleted X observations have no erasure path

- **Description:** Deleted X observations have no erasure path.
- **Evidence:** `XApiAdapter._recheck` records NOT_FOUND/access loss; ROADMAP C-3 and OPERATIONS explicitly say old X observations are not purged. No X purge CLI exists. Optional source erasure helpers on the feature branch do not wire an X purge. Recheck fixture tests verify state changes, not expiry/erasure of all historical hashes, metrics and derived evidence.
- **Affected component:** X retention / data lifecycle.
- **Severity:** Medium.
- **Confidence:** High; Verified.
- **User impact:** Live X retention cannot satisfy the implementation's own stated deletion policy. This is a software-policy discrepancy, not an independent legal conclusion.
- **Recommended next investigation:** Trace deletion through public DB, private copies, claim caches, narrative snapshots, exports and git history; verify an eventual-erasure acceptance contract before live storage.

## AUD-010 — Latest source expansions are not present in main; handoff and release instructions drifted

- **Description:** Latest source expansions are not present in main; handoff and release instructions drifted.
- **Evidence:** Main merges phases 00–18 at f084b603. Feature tip 3f27fc7 additionally contains Reddit, Farcaster, Discord and YouTube. Main HANDOFF/RELEASE still say PR #1 open/unmerged; README instructs checkout of the moving feature branch. Git refs and commit diff independently inspected. Feature-specific fixture release passes 71 stages versus 45 on main.
- **Affected component:** Release configuration / documentation.
- **Severity:** Medium.
- **Confidence:** High; Verified.
- **User impact:** A reader may test or deploy a different feature set from the reviewed baseline, or incorrectly believe optional sources are installed on main.
- **Recommended next investigation:** Pin release refs, regenerate branch-specific handoff/status and document deployment target; review optional changes separately before any merge.

## AUD-011 — Full suite remains red and tests write reports into their checkout

- **Description:** Full suite remains red and tests write reports into their checkout.
- **Evidence:** Both suites fail `test_catalyst.py::test_dedup_corroboration_resurface_denial`; evidence status remains REPORTED rather than expected CONFIRMED. Existing EVM test writes a BRETT report under data/reports. Independent Python 3.12.14 runs: main 1 failed/651 passed (155.63s); feature 1 failed/748 passed (150.94s). Disposable-copy status contains an untracked BRETT report. Historical handoff identifies both as C-1.
- **Affected component:** Regression QA / test isolation.
- **Severity:** Medium.
- **Confidence:** High; Verified; pre-existing.
- **User impact:** Full green acceptance gates are unmet. Time-dependent tests obscure regressions and runs pollute working copies. This is not a newly introduced social regression.
- **Recommended next investigation:** Reproduce with controlled clocks and isolated report paths in the next testing phase; retain this failure as baseline until independently resolved.

## AUD-012 — Wallet accounting depends on incomplete imported history and supplied prices

- **Description:** Wallet accounting depends on incomplete imported history and supplied prices.
- **Evidence:** `wallet_activity.py` imports classified documents with per-fetch limits (default 50); `perf_store.py::ledger_from_events` infers TRUNCATED or PLAUSIBLY_COMPLETE from response sizes. No EVM transaction provider is implemented. Helius plan exists but live history retrieval was not verified. Fixture lots, transfer handling, fees and score refusal work. No fetched full real-wallet ledger or executable exit proof was captured.
- **Affected component:** Wallet activity / P&L.
- **Severity:** Medium.
- **Confidence:** High; Verified limitation.
- **User impact:** Wallet rankings can abstain correctly, but the code cannot demonstrate comprehensive person-level profit or validate completeness merely from short responses.
- **Recommended next investigation:** Test provider pagination, requested-limit provenance, opening inventory, fee coverage, token precision and router quotes using a permitted wallet and offline captured data.

## AUD-013 — Discord live Gateway transport is not shipped

- **Description:** Discord live Gateway transport is not shipped.
- **Evidence:** `discord_bot.py` provides REST and a Gateway frame/state adapter; `sources_cli.py::cmd_discord_gateway` refuses non-fixture operation with gateway_transport_not_shipped. `DISCORD_20.md` explicitly documents it. Gateway restart/intents cases pass on invented frames; live Gateway connection is not available in the shipped CLI. REST polling is implemented but live-unverified.
- **Affected component:** Optional Discord connector, feature branch only.
- **Severity:** Medium.
- **Confidence:** High; Verified.
- **User impact:** Fixture Gateway success is not live streaming capability. A consenting server plus bot credentials is insufficient for the Gateway command.
- **Recommended next investigation:** Inspect REST polling freshness/deletion coverage separately; require a real transport and controlled reconnect/resume test if live Gateway is a requirement.

## AUD-014 — Release PASS is a staged fixture demonstration, not one production data flow

- **Description:** Release PASS is a staged fixture demonstration, not one production data flow.
- **Evidence:** `tools/release_e2e.py::STAGES` separately invokes --post, --ledger, --input and multiple independent demos. It checks expected exit codes and after-checks; a number of substantive stages create their own fixture worlds. 45/45 and 71/71 are reproduced with zero network attempts; audit probes still expose AUD-001 to AUD-006.
- **Affected component:** Acceptance evidence / release tooling.
- **Severity:** Medium.
- **Confidence:** High; Verified.
- **User impact:** A passing release run proves CLI compatibility and local safety properties, not complete primary-source wiring, model quality, temporal correctness of all adapters or operational service readiness.
- **Recommended next investigation:** Build one independent acceptance scenario carrying one source observation through identity, claims, narrative, report, alerts, immutable record and outcomes, with assertions on shared evidence IDs and causal clocks.

## Evidence and verification limits

Audit-added reproductions are in `evidence/probes.py`, with `probes-main.json` and `probes-feature.json`. They use invented inputs, temporary databases and no network calls. They reproduce source selection/budget arithmetic, not paid-service behavior. Existing application tests were not modified. Test logs, release runs, source/test inventories and original requirements are included alongside this register.

The repository security scan reported no credential/key-material shapes or order/signing paths. Pattern matching does not establish absence of every secret or vulnerability; platform terms, prices and authentication contracts were not freshly certified. `pyflakes` was unavailable in this audit environment; syntax checks ran. Read-only source inspection and offline execution do not validate remote account state, scheduler state or service availability.


## Phase 01 functional verification — 2026-10-13

Pinned main baseline unchanged: `698f73b854567ce60b56ce275b5ab6822a9d5f60`. Existing suite: 651 passed / 1 failed (120.34 seconds), the same catalyst assertion recorded as AUD-011. Release fixtures: 45/45. Independent acceptance tests: 17 passed / 5 failed. Zero Python network attempts. All new tests use synthetic data and temporary stores; no application fixes, paid calls, external deliveries or transactions.

AUD-003 is reconfirmed by three normalized X observations creating zero automatic claims. Supplying the missing text/provider handoff produces exact identity, two independent sources, one repost and citations, clarifying that the gap is orchestration rather than failure of every downstream component. AUD-001 is reconfirmed by later extraction timestamps populating a past snapshot. AUD-014 remains supported: staged demos pass while independent boundaries fail. AUD-011 remains open. No AUD-001–014 finding is closed by this phase.

Evidence: `01_FUNCTIONAL_AUDIT.md`, `evidence/test_functional_audit.py`, `evidence/independent-tests.log`, `evidence/existing-suite.log`, `evidence/release-e2e.json`, `evidence/execution-metadata.json`. Initial audit-harness errors were corrected and are not counted as product defects; the final 22-test run is authoritative.

## AUD-015 — Explicit feed snapshot ID bypasses historical cutoff

- **Affected component:** Historical report generation; `feed_store.py::load_input` (lines 122–141), `feed_cli.py::_input` exposing `--run` alongside `--as-of`.
- **Severity / confidence:** High / High. Independently reproduced on pinned main.
- **Expected:** A supplied snapshot ID must obey the historical knowledge cutoff, or the command must explicitly reject incompatible historical parameters.
- **Actual:** The ID query selects `WHERE run_id=?` without `cutoff<=as_of`. A snapshot with cutoff 1791849600 is returned at requested `as_of=1791835200`, including its contract cluster. The default no-ID path applies a cutoff.
- **Reproduction:** Run `test_historical_explicit_future_run_rejected` from the independent script. Ingest/extract the three invented posts; create the later snapshot; request it by ID at the earlier as-of. Expected no eligible clusters; assertion fails because the future cluster is returned.
- **Impact:** Historical brief/feed/digest can contain information from a later snapshot while displaying an earlier as-of time. Correct default selection does not protect explicit-ID reads.
- **Recommended fix:** Validate snapshot cutoff and knowledge availability for explicit IDs. If stored-run inspection is supported, clearly separate it from historical as-of rendering. Add CLI and database-level adversarial regression coverage.

## AUD-016 — Adapter iterator exception escapes ingestion and leaves RUNNING status

- **Affected component:** Provider-neutral ingestion; `ingest.py::ingest`, iterator advancement at line 540 outside the per-unit try block.
- **Severity / confidence:** Medium / High for the demonstrated adapter-contract boundary. Not a demonstrated live X outage.
- **Expected:** Fetch failure after a committed page preserves data, finalizes PARTIAL/FAILED appropriately, records unavailable health and supports recovery.
- **Actual:** Custom adapter yields one valid unit then raises TimeoutError on its next iteration. One observation survives; the exception escapes; the ingest run remains RUNNING; final DOWN health is absent.
- **Reproduction:** `test_D_adapter_iterator_exception_is_contained`. The adjacent normalized-DOWN-unit test passes, showing the exact boundary distinction.
- **Impact:** New or faulty adapters can leave misleading run state and skip final health bookkeeping. The current X adapter separately catches per-scope failures; do not extrapolate this generic reproduction into a claim that every shipped connector fails this way.
- **Recommended fix:** Protect iterator advancement or require enforced normalization into SourceUnits; finalize run/health even when iteration fails; retain committed checkpoints. Add interruption/retry acceptance tests at fetch boundaries, not only persistence hooks.

## AUD-017 — Historical feed loads chronology flags created after its cutoff

- **Affected component:** Derived corroboration/risk in historical reports; `feed_store.py::_flags` (line 111) and `chrono_store.py::current_flags` (line 199).
- **Severity / confidence:** High / High. Independently reproduced on pinned main.
- **Expected:** A derived chronology flag is usable only after its supporting computation was available. Select the most recent eligible run at the historical cutoff.
- **Actual:** Save the supplied confident chronology fixture at `doc.as_of + 86400`. Request `_flags` at `doc.as_of`: four flags appear. `current_flags` selects latest run IDs overall; `_flags` filters event `at`, ignoring run creation/availability. A late recomputation can also replace historical interpretation; that replacement variant is source-confirmed, not separately executed here.
- **Reproduction:** `test_historical_feed_ignores_chronology_created_after_cutoff`. No production data is changed. Positive saved-run recomputation/idempotence passes, showing hash integrity does not imply causal selection.
- **Impact:** A past feed can present later-developed corroboration or risk conclusions as though known then, invalidating historical research interpretation.
- **Recommended fix:** Carry and enforce derived availability clocks; select latest eligible chronology run under creation/availability and evidence cutoffs, preserving historical revisions. Test late computation, future run IDs and later replacement of old flags together.

---

## Phase 02/04 continuity — recovered documents, no closure implied

**Phase 05 continuity note (2026-10-13):** Original Phase 00–01 register above has been preserved without removing or renumbering AUD-001–017. The separately archived `02_ARCHITECTURE_AUDIT.md` includes ARCH-001 through ARCH-012, covering historical knowledge-time selection, FK enforcement, source→extraction orchestration, iterator failure cleanup, public/private state separation, cross-chain identity mapping, publication dependency manifests, append-only growth, suppressed error states, cursor safety, cross-store crash consistency and adapter contract divergence. The separately archived `04_ADVERSARIAL_AUDIT.md` includes ADV-001 through ADV-009. Those reports were read; their audit files are **not present in the pinned source Git tree**. No Phase 03 primary report was available. Phase 04's separate reconstructed partial FINDINGS document is *not* used to overwrite this recovered primary register. All prior issues remain open absent independently verified repair; this phase makes no such claim.

Phase 04 additions carried forward by reference (these are *not* newly reexecuted in Phase 05): **ADV-001** private SQLite permissions; **ADV-002** expired wording read until purge; **ADV-003** top-level-only LLM secret config detection; **ADV-004** conditional Helius redactor gaps; **ADV-005** malformed model-response exception; **ADV-006** malformed Telegram transport/429 exception; **ADV-007** non-atomic LLM budget reservation; **ADV-008** incomplete content guard coverage; **ADV-009** missing X deletion/purge path. See archived `04_ADVERSARIAL_AUDIT.md` for exact evidence qualifiers.

## Phase 05 — Operations, costs and usability findings (2026-10-13)

**Evidence standard:** `SOURCE` = independently inspected pinned repository code; `PRIOR` = reproducible earlier audit finding; `RUNBOOK` = documented procedure; `MODEL` = reasoned operational/financial scenario, no runtime proof. None of these new entries claims a seven-day live soak, real provider access, notification delivery, restoration, or invoices. **Baseline** remains `698f73b854567ce60b56ce275b5ab6822a9d5f60`. Full analysis: `05_OPERATIONS_AND_UX.md`. Existing IDs AUD/ARCH/ADV remain authoritative for their original technical defects.

| ID | Finding | Severity | Evidence | Current status | Cross-reference |
|---|---|---|---|---|---|
| OPS-001 | Social schedules are disabled templates; no demonstrated unattended source→report→signal job or independent missed-run watchdog | High | SOURCE + RUNBOOK + PRIOR | OPEN / operational activation not proved | AUD-003, AUD-007, AUD-014 |
| OPS-002 | Source and processing health do not provide a trustworthy whole-universe completeness/contiguous-cursor guarantee | High | SOURCE + PRIOR | OPEN | AUD-005, AUD-016, ARCH-009, ARCH-010 |
| OPS-003 | Coordinated, encrypted backup and verified **whole-system** restore of main/private/alert/outcome stores absent | High | RUNBOOK + ARCH | NOT VERIFIED | ARCH-005, ARCH-011 |
| OPS-004 | Budget guard is not an assured hard cash/charged-resource ceiling under bad unit prices or concurrent workers | High if billing enabled | SOURCE + PRIOR | OPEN; off-by-default mitigates present exposure | AUD-006, ADV-007 |
| OPS-005 | Real alert receipt, retries after ambiguous sends, malformed API error handling and recovery are unproved | Medium | SOURCE + PRIOR | NOT VERIFIED live | ADV-006, AUD-007 |
| OPS-006 | Missing/stale/unclassified data can be mistaken for a complete no-signal day; UX lacks independently validated seven-question research workflow | High | SOURCE + RUNBOOK + PRIOR | OPEN as end-user gap | AUD-003, ARCH-009 |
| OPS-007 | Manual scheduling, testing, content purges, repair and preupgrade backup dominate an individual operator's maintenance burden | Medium | RUNBOOK | OPEN | AUD-007, AUD-009, ADV-002 |
| OPS-008 | Research-time savings, live analyst trust and cost-per-actionable-signal are not measured | High for stated product objective | PRIOR + MODEL | NOT ESTABLISHED | AUD-008, AUD-014 |
| OPS-009 | Append-only data and per-source retention lack an automated, measured sizing/erasure plan | Medium | SOURCE + ARCH + PRIOR | OPEN | ARCH-008, AUD-009, ADV-002/009 |
| OPS-010 | Deployment ref selection and rollback procedure do not constitute a verified upgrade/restore/service runbook | Medium | RUNBOOK + PRIOR | NOT VERIFIED | AUD-010, ARCH-005 |

### OPS-001 — No unattended service contract

- **Observed:** `alerts_schedule.py` explicitly sets both templates `enabled=False`. `OPERATIONS.md` instructs the operator to ask an external scheduler to create them; other daily tasks currently do not run social steps. This is not evidence that no external unpublished automation exists, but such automation is not documented or demonstrated in the audited artifact set.
- **Impact:** An empty morning brief may reflect a missed job; seven days unattended cannot be called reliable.
- **Gate:** Time-advance a persistent hosted job through seven days, startup/restart and schedule-miss handling; validate shared evidence IDs from authorized source to later signal outcome, no duplicate/missing publication.

### OPS-002 — Source completeness cannot be guaranteed

- **Observed:** Prior AUD-005 page cap moves X newest cursor past a backlog; AUD-016 leaves `RUNNING` after iterator failure. `feed_store.py` explicitly handles stale/missing snapshots but `_flags` catches an unexpected exception as no flags. These are independently narrower facts, not a proof of widespread live data loss.
- **Impact:** The system can fail to notice unvisited data or imply a clean risk state with partial processing.
- **Gate:** Per-source expected/reached status, time range, contiguous cursor, oldest gap, post count and classification rate; 429/timeout/capped pagination backfill must converge with no hole after restart.

### OPS-003 — Recovery point not proven

- **Observed:** A helper backs up main SQLite, but no source evidence for atomic point-in-time captures of private text, alerts and outcome ledger. The public `state` exporter excludes social tables. Prior migrations on disposable copies do not establish a four-store restore.
- **Impact:** A host failure can lose/reorder alert or historical intelligence state even when legacy watchlist state is recovered.
- **Gate:** On a stopped or coordinated snapshot, take encrypted backups of all stores, restore on clean host, check integrity/hash/row counts, verified working signal history, notification dedupe and model cache; measure RPO/RTO.

### OPS-004 — FinOps controls are incomplete

- **Observed:** AUD-006 reproduces live-mode 0-priced provider under purported $0 cap; ADV-007 identifies non-atomic reserve-before-bill behavior for simultaneous workers. `llm.py` handles 429/529 as provider errors but does not itself demonstrate cross-run retry-after backoff. Paid mode remains off by default.
- **Impact:** A budget setting can give false assurance after explicit provider activation; tenfold input spikes risk uncontrolled reads or inference unless account-side controls are also in place.
- **Gate:** Two-workers and 10× surge tests with fake billed 429 and unknown token price; hard preapproved $/resource reservations, no spend above cap and source read resources reconciled to provider bill.

### OPS-005 — Delivery status not equivalent to receipt

- **Observed:** Fixture file dry runs, slot deduplication, policy cooldowns and caps exist; no external Telegram/email receipt test was demonstrated. ADV-006 shows malformed retry data can error. The system has no independently demonstrated crash-after-send delivery recovery.
- **Impact:** Important warnings may be silently unsent, repeated or ambiguous.
- **Gate:** Persist states queued/attempted/acknowledged/unknown/dead-letter, test 429/timeout/malformed payload and retry-after-send, only claim receipt when transport confirms it.

### OPS-006 — No-data UX can overstate certainty

- **Observed:** The source/claim gap (AUD-003), `feed_store` empty availability output and absence of an expected-source coverage denominator make the difference between “no finding” and “no data” critical. No layperson validation study has been recovered.
- **Impact:** The report can look polished while lacking a meaningful signal or missing a dangerous one.
- **Gate:** A default reader must correctly answer the seven Phase 05 research questions, see fetched/classified/expected source counts, be shown last complete snapshot and unknown risks, and never infer zero activity from zero acquired data.

### OPS-007–OPS-010 — Maintenance, ROI, growth, release

- **Evidence:** `OPERATIONS.md` manual weekly suite/guards/ledger verification, monthly purge, backup-before-upgrade and external scheduler activation; `private.py` retains expiration deadlines but manual purge required; architecture notes append-only growth; AUD-010 establishes main/feature drift. No timed user study, longitudinal hosting log, restore drill, provider invoice or deployed target has been recovered.
- **Impact:** The personal system does not yet establish net time savings or bounded maintenance/disk costs, and a branch change can silently change capabilities.
- **Gates:** Schedule retention/housekeeping, measure row sizes and storage/backups, publish pinned deploy manifest and safe rollback, and run a 14-day manual vs 14-day assisted research comparison including accuracy, elapsed time, upkeep and incremental spend.

### Phase 05 modeled direct costs (not measured bills)

With 30 days/month, 50% charged X reads at **$0.005/post**, 30% model calls of 1,800 input + 250 output tokens at **Haiku 5.5 $0.10/$0.50 per million**, and arbitrary 30k/300k/3M Helius credits, monthly illustrations are **$7.77 / $77.75 / $826.45** for **100 / 1,000 / 10,000 monitored posts per day** (including $0/$0/$49 Helius plan in each subtotal). Does not include compute, backup, X user reads, paid alternate platforms, duplicate fetches, taxes, network/candle/market data or time spent. Calculation reproduced offline with `evidence/phase05_cost_model.py` and result JSON. Price pages are linked in `05_OPERATIONS_AND_UX.md`.

**Status:** REJECT unattended release; supervised/offline research only. This is an audit/documentation update, not remediation. No prior findings closed. No production code, data, credentials, paid services, transports or operational schedules changed. Stop Phase 05.
