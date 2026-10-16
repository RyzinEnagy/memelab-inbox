# Findings register

> **Current Phase 03 substitute review, 2026-10-15:** recovery package hashes and report/later-test continuity verified; newly reconstructed A–E runs now include D/E. Historical original full inputs/executions remain unrecovered. **M00 BLOCKED pending explicit reviewed acceptance of the substitute evidence; M01 unauthorized.** See [current decision and concrete reviewer action](M00_PHASE03_REPLICATION_REVIEW.md). Earlier dated statements retain their historical scope.


> **Current archive follow-up, 2026-10-15:** four original ZIPs and 50 member files recovered; 43 embedded hashes and all 105 original requirement texts verified. Original Phase 04/05 bytes are now available. OPS-001–010 are primary labels in the recovered Phase 05 findings, correcting the earlier secondary-only attribution. Phase 03 A–E executable inputs/scripts/raw outputs remain absent; **M00 BLOCKED, M01 unauthorized**. See [current checklist and next steps](M00_ARCHIVE_RECOVERY_VERIFICATION.md). Earlier dated statements below describe their historical review state.


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
| AUD-018 | SQLite foreign keys not uniformly enabled on each connection | High | Phase 02 inspected connection implementation; no orphan incident claimed |
| AUD-019 | Legacy mint-only tokens may collide with chain-qualified social identity | High | Phase 02 design exposure; real collision not demonstrated |
| AUD-020 | Published conclusions lack end-to-end provenance/supersession lineage | High | Phase 02 architecture finding |
| AUD-021 | Unexpected chronology failures can be rendered as zero flags | Medium | Phase 02 inspected code; incident not reproduced |
| AUD-022 | Public/private/alert/outcome persistence lacks tested consistent restore | High | Phase 02 design and test gap; crash impact unproven |
| AUD-023 | Append-only derivatives lack complete capacity/retention checks | Medium | Phase 02 architecture risk; performance failure unmeasured |
| AUD-024 | Intrabar Information Alpha uses earlier candle open or future high/low | High | Phase 03 independently reproduced on synthetic data |
| AUD-025 | Historical wallet valuation accepts later price marks | High | Phase 03 independently reproduced on synthetic data |
| AUD-026 | Information Alpha `VALIDATED` lacks independent forward validation | High | Phase 03 methodology review, no live efficacy claim |
| AUD-027 | Controls and source universe insufficiently adjust selection bias | Medium | Phase 03 code / methodology review |
| AUD-028 | Distinct social sources can overstate independent organic origins | Medium | Phase 03 code / methodology review |
| AUD-029 | Quoted liquidation lower bound and partial-zero aggregation mislead | Medium | Phase 03 reproduced/model-qualified |
| AUD-030 | Social editorial ordering lacks demonstrated incremental utility | Medium | Phase 03 code / methodology review |
| AUD-031 | Missing inherited flags do not verify token authority and exit depth | Medium | Phase 03 code / scope review |
| AUD-032 | Replay exporter backdates derived claims/attribution | High | Phase 03 reconfirms AUD-002; code-confirmed |
| AUD-033 | Signal market context may use fact before it was fetched | Medium | Phase 03 code-confirmed, live contamination unverified |

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

## M00 evidence reconciliation — original Phase 02 / Phase 03 findings

The paragraphs below preserve the **original auditor wording** from the separately archived historical `recovered/phase02_FINDINGS.md` and `recovered/phase03_FINDINGS.md`. M00 has **not** independently reexecuted the audit's offline experiments and has not closed any finding. The original Phase 03 text says the Phase 02 report was inaccessible *at the time Phase 03 was written*. It was subsequently restored in M00: that historical note is preserved as written but is no longer the current archive status. The original source snapshots remain byte-identical and may be consulted independently. AUD-032 explicitly reaffirms AUD-002 rather than adding an independently demonstrated new incident.

## Phase 02 architecture audit additions — 2026-10-13

**Scope:** Pinned main `698f73b854567ce60b56ce275b5ab6822a9d5f60`; independent static design/code review backed by Phase 00/01 findings. No new production edits, no new stress-test claims. Full trade-offs, impact, complexity and acceptance gates: `02_ARCHITECTURE_AUDIT.md`. Existing AUD-001–AUD-017 remain open unless explicitly resolved elsewhere; Phase 02 does not close any.

## AUD-018 — SQLite foreign keys are not uniformly enabled per connection
- **Severity / confidence:** High / High (connection implementation directly inspected; no orphan occurrence claimed).
- **Evidence:** `memelab/db.py` enables foreign keys in schema initialization script, while `social/store.py:98` states db connections do not automatically enable them. Social `ingest._connect` opens its own `sqlite3.connect(..., isolation_level=None)` without setting `PRAGMA foreign_keys=ON`. Social schema declares many `REFERENCES`.
- **Impact:** Unchecked writes can create orphan claim, observation, account or provenance links; report joins can silently discard evidence.
- **Action:** Centralize per-connection FK enforcement and verify it; audit `PRAGMA foreign_key_check` on restored production copy before enabling and test all writer paths. Complexity medium, essential.

## AUD-019 — Legacy mint-only keys conflict with chain-qualified social identity
- **Severity / confidence:** High / High design exposure; real collision impact unproven.
- **Evidence:** `memelab/db.py` primary `tokens(mint)`, `state.TABLES/KEYS` and legacy watchlist/thesis access are mint-keyed, while `social_token_refs` and social normalization use `(chain,contract)`.
- **Impact:** Ambiguous chain projection may conflate or misjoin otherwise distinct assets.
- **Action:** Canonical asset identity map, chain-aware joins and ambiguity abstention; retain backwards-compatible legacy keys until measured safe migration. High complexity, essential for multi-chain joins.

## AUD-020 — No comprehensive publication provenance and correction lineage
- **Severity / confidence:** High / High that single publication-manifest contract is absent; impacts inferred from AUD-001/002/015/017 and code paths.
- **Evidence:** Run-level input/result hashes in alpha/performance/chrono coexist with historical readers that can select future/current derived state; no complete frozen publication→all dependency versions→source availability ledger demonstrated.
- **Impact:** Cannot reliably reconstruct *what was known when* or how a previously published conclusion changed after wallet/source/scoring revision.
- **Action:** Versioned `research_publications` manifest with commit, model/config/score versions, dependency IDs, event and knowledge cutoffs and supersession chain; central temporal filtering. High complexity, essential.

## AUD-021 — Unexpected chronology errors are suppressed as zero risk flags
- **Severity / confidence:** Medium / High for inspected behavior; incident not reproduced.
- **Evidence:** `feed_store.py::_flags` catches all `Exception` from `chrono_store.current_flags` and returns an empty list; malformed JSON flags/reasons are also mapped to `[]` in feed formatting.
- **Impact:** A failed risk lookup can be visually indistinguishable from a successful lookup returning no risk.
- **Action:** Distinguish `NO_FLAGS`, `UNAVAILABLE`, `FAILED` with typed status and logged errors; catch only anticipated unsupported cases. Low–medium complexity, essential.

## AUD-022 — Private/public/multi-ledger continuity has no proven consistent recovery unit
- **Severity / confidence:** High / High for architectural separation, medium for crash consequences (not experimentally proven).
- **Evidence:** `state.py` exports only legacy tables; social public SQLite, `private.py`, alert SQLite and `outcomes_ledger.py` operate with separate persistence and transactions. Phase 00 AUD-007 confirms restart continuity not wired.
- **Impact:** Recovery can preserve a watchlist but not original text, social evidence, alert delivery history or outcome scoring; cross-store partial writes may leave inconsistent references.
- **Action:** Reproducible public/private state manifests and consistent encrypted backups, transactional outbox, crash/restart integration tests; never export exact private content to public GitHub. Medium–high complexity, essential.

## AUD-023 — Append-only analytical stores lack system-wide capacity and retention gates
- **Severity / confidence:** Medium / High for absence of uniform lifecycle; no measured performance failure.
- **Evidence:** Many observation, provenance, market, registry, narrative, wallet, score and chronology tables append indefinitely. `private.purge_expired` and alert dedupe `purge` cover only select stores.
- **Impact:** Potential growth, progressively slow historical scans and large backups; blanket deletion would undermine audit history.
- **Action:** Separate legal erasure from archival/rollups; row-count monitoring, retention tiers, indexes guided by EXPLAIN, backup/capacity tests. Medium complexity; essential before scaling, optional at current low-volume offline use.

**Traceability:** AUD-001/002/015/017 are concrete temporal instances under ARCH-001; AUD-003 links ARCH-003; AUD-005 links ARCH-010; AUD-006 links ARCH-013; AUD-007 links ARCH-005/011; AUD-009 links ARCH-014; AUD-016 links ARCH-004. Do not double count cross-references as newly reproduced failures.

## Phase 03 quantitative research validity — 2026-10-13

Pinned baseline: `698f73b854567ce60b56ce275b5ab6822a9d5f60`; methodology and source reviewed without modifying production. Full report: [`03_RESEARCH_VALIDITY.md`](03_RESEARCH_VALIDITY.md). Independent offline, synthetic reproduction exercised alpha intrabar entry/exit, performance future-mark matching, and liquidation quote behavior. Real historic predictive results remain unavailable; no live-market performance assertion is made.

**Continuity restriction:** This register copy was recovered from the Phase 00/01 personal Library artifact (AUD-001–017). The Phase 02 report and latest FINDINGS.md are absent from GitHub and unavailable as raw files in this execution. Prior conversation confirms AUD-018–023 were created, but their exact descriptions/severities cannot be retrieved. **AUD-018–023 remain explicitly reserved; no Phase 02 item has been renumbered, closed, fabricated, or deliberately replaced.** This is an incomplete consolidation until the original Phase 02 file is recovered. Phase 03 starts at AUD-024 to avoid collisions.

| ID | Description | Severity | Evidence | Status |
|---|---|---|---|---|
| AUD-024 | Intrabar historical alpha fill uses past candle open or not-yet-known high/low | High | Reproduced offline | Open |
| AUD-025 | Future midpoint accepted for historical wallet USD valuation | High | Reproduced offline | Open |
| AUD-026 | `VALIDATED` alpha tier lacks truly prospective independent predictive validation | High | Code-confirmed + methodological | Open |
| AUD-027 | Alpha control matching and call-universe sampling do not isolate information advantage | Medium | Code-confirmed + methodological | Open |
| AUD-028 | Narrative independence/emergence and raw mention counts vulnerable to sophisticated coordinated sources | Medium | Code-confirmed + methodological | Open |
| AUD-029 | Executable quote pro-rata “lower bound” overstated; missing quote aggregated as zero | Medium | Reproduced / code-confirmed | Open |
| AUD-030 | Editorial research priority is not proven to improve candidate selection; depth not universal gate | Medium | Code-confirmed + methodological | Open |
| AUD-031 | No fatal flag in inherited structure is not evidence of authority/depth checks for every token | Medium | Code-confirmed + scope qualification | Open |
| AUD-032 | Replay DB exporter backdates extracted CALLs/current wallet assertions; pre-existing AUD-002 | High | Code-confirmed; reconfirms earlier finding | Open; cross-reference |
| AUD-033 | Signal-generation market context can use `as_of` without checking later `fetched_at` | Medium | Code-confirmed; live exposure not established | Open |

### AUD-024 — Intrabar alpha execution timing invalidates claimed historical fills

- **Component / source:** `memelab/social/alpha_core.py::_candle_at`, `entry_for`, `exit_for` (lines 182–253).
- **Severity / confidence:** **High / High; independently reproduced** in-memory with synthetic candle data on the pinned source.
- **Expected:** Entries after publication, capture and delay execute on quotes/prices at or after the resulting decision time, never from earlier opens or uncompleted candle extremes; horizon exits must likewise use prices executable at the horizon.
- **Actual:** A 3600-second candle `t=0`, `o=10`, `h=100`, and a decision `t=1800` returned `fill_t=1800`, `candle_t=0`, `price=10` in OPEN mode. CANDLE_ADVERSE mode returned `price=100` even though the high is only known for the completed candle. Exit targeted `t=3000` returned the same earlier open `price=10`.
- **Research impact:** The code's nominal delay does not imply a real delayed fill, so absolute/relative returns and Information Alpha may be directionally wrong. No magnitude or sign of actual financial bias is claimed.
- **Remediation and test:** Reject intrabar exact fills from OHLC unless there is a precisely timestamped executable quote/tick; use only prior **completed** candles for features, separate timestamp of observation from execution, compare to strict later-onset price, and regression-test after publication and horizon boundaries.

### AUD-025 — Future midpoint enters wallet USD history

- **Component / source:** `memelab/social/perf_core.py::Book.near`, `Book.unit_usd` (lines 342–369).
- **Severity / confidence:** **High / High; independently reproduced** with supplied synthetic mark, native asset and `price_tolerance_s=200`.
- **Expected:** For point-in-time P&L or trader-ranking features available to a historical decision, the price mark must have been observed by that time.
- **Actual:** For a `t=1000` historical transaction, the nearest price at `t=1100`, `$100`, was returned as `OBSERVED`; default price tolerance is **900 seconds**. Nearest lookup uses absolute temporal distance.
- **Research impact:** Historical USD wallet results, fees and capital normalization can use later information; this does not mean on-chain native quantities were altered. Retrospective accounting based on ex-post marks must be distinguished from contemporaneous tradable evidence.
- **Remediation and test:** Store distinct market-effective, published and available-at times; use last-known-before lookup for ex-ante comparisons, flag stale marks. Permit later restatements only in an explicitly retrospective column and test both modes independently.

### AUD-026 — `VALIDATED` Information Alpha is an internally qualified historical association

- **Component / source:** `memelab/social/alpha_core.py::_score` (lines 565–632), `DEFAULT_POLICY` (27–63).
- **Severity / confidence:** **High / High for the methodological gap; no realized future performance examined**.
- **Actual:** A `VALIDATED` tier can result from at least 30 eligible calls, 20 distinct contracts, fixed in-sample median-relative confidence interval, completeness checks and same-sample chronological-half sign consistency. It does not require a prospective untouched test period, multiple-comparison correction across sources/parameter choices, or robust dependence-aware confidence intervals.
- **Impact:** “Validated” can be incorrectly read as proof the source's public posts predict future net investable edge; the function estimates historical signed returns under caller-supplied data/assumptions, not causal or calibrated predictive value.
- **Remediation:** Rename current tier to a historical evidence status, lock the full universe/policy before outcomes, use prospective independent test and forward observation, bootstrap by token/trader/cohort, adjust selection multiplicity and benchmark net executable returns.
- **Relationship:** Extends the unresolved no-real-efficacy baseline AUD-008 rather than asserting a new observed profitable result.

### AUD-027 — Matched baseline and coverage denominators do not control selection/confounding

- **Component / source:** `alpha_core.py::_baseline` (358–376), `_summarise` (557–561), `_score` (565–585).
- **Severity / confidence:** **Medium / High for observed matching and completeness logic; uncertain size of resulting bias**.
- **Actual:** Controls are selected based primarily on same-chain pool liquidity and trailing volume; other economically important factors (token age, launch cohort, valuation, pretrend, volatility, promotional regime, market listing survivorship) are not matched. A source's enumerated universe is supplied, and absent completeness can still permit a PRELIMINARY score.
- **Impact:** Correlated pumps, post-induced buying or cherry-picked called tokens can masquerade as unique informational value.
- **Remediation:** Pre-register a complete public post sampling frame; match launch age/valuation/volatility/momentum plus liquidity/executable depth; include inactive and delisted contracts; show covariate balance and unmatched fraction; use placebo and permutation controls.

### AUD-028 — Social origin count does not prove independent operators or true emergence

- **Component / source:** `narratives.py::_build` (213–429), `_sliding` (192–205), `research_core.py::attention_lane` (112–133).
- **Severity / confidence:** **Medium / High for counting behavior, low for external synthetic-network prevalence**.
- **Actual:** Explicit reposts/forwards/identical texts collapse as intended, but different accounts using different original text remain independently counted even if they may be controlled together. Raw mention windows count repeat content. `EMERGING` is a heuristic threshold relative to an incomplete collected corpus, not objective global novelty.
- **Impact:** Coordinated artificial activity can drive perceived corroboration and analyst attention; a lone useful contrarian can receive less editorial weight.
- **Remediation:** Show one-per-verified-owner only where ownership is established, otherwise give hypotheses and uncertainty; independently assess novelty against prior broad corpus; separate original per-source counts from total post rates; test unique-text coordinated networks and platform coverage gaps.

### AUD-029 — Liquidity liquidation bounds and missing-estimate headline are overconfident

- **Component / source:** `perf_analysis.py::liquidation` (196–222), `inventory_block` (225–261), `_sum` helper.
- **Severity / confidence:** **Medium / High; synthetic quote behavior reproduced**.
- **Actual:** Synthetic `EXEC_QUOTE` for 100 token units returning $100, with a 50-unit holding, is prorated to $50 and labeled a lower bound. Lower-bound guarantee ignores time drift, router changes, MEV and token-tax distinctions. Per-asset no-quote is correctly `None`, while the aggregate sum of known values is zero even when all lots lack valid quote values; the count of unavailable estimates is separately reported.
- **Impact:** Presenting the aggregate as zero without conspicuous “partial/unknown” can mislead about realizable P&L. Prorated quote is an illustrative estimate, not guaranteed minimum dollars receivable.
- **Remediation:** Require a fresh exact-size route quote, or label bounds explicitly model-conditional; add missing-coverage state to headline (`null/partial`) and tests for stale/no-route/partial/taxed-asset cases.
- **Relationship:** Supplements AUD-012 (supplied data/historical coverage limitations).

### AUD-030 — Social-based research priority lacks incremental outcome evidence

- **Component / source:** `research_core.py::_weight` (156–165), `build` (257–329), `DEFAULT_POLICY` (29–44).
- **Severity / confidence:** **Medium / High for scope; no verified market uplift**.
- **Actual:** Risk/attention weights only sort the social research section; this positive separation does not demonstrate that order is economically useful. Attention from nominal independent sources may dominate the editorial queue; contrarian observations are disadvantaged if not corroborated. A `RESEARCH_CANDIDATE` state need not include a fresh exact-size exit quote.
- **Impact:** Potential analyst-time waste and exposure to promotion or unexitability if editorial candidates are confused with investable recommendations. The engine itself does not change trade execution or core trading rank.
- **Remediation:** Prospective controlled comparison against the prior engine on the same universe/time budget with blinded adjudication; require depth/authority evidence before investable priority labels; label missing route as abstention.

### AUD-031 — Social structural nonfatal status is not verified token safety

- **Component / source:** `research_core.py::structure_lane`, `entry_lane` (136–154).
- **Severity / confidence:** **Medium / High; scope/design limitation**.
- **Actual:** The social system calls structure ACCEPTABLE when the upstream candidate has no supplied `fatal_flags` and is not explicitly `untradeable`. It does not independently verify token mint/freeze/fee authorities, LP withdrawal control, holder clustering, transfer restrictions or exact-size exit quotes.
- **Impact:** A consumer may mistake absence of observed fatal evidence for evidence that all relevant hazards were checked. This is particularly consequential for Token-2022 tokens and small concentrated pools.
- **Remediation:** Carry per-hazard coverage and dated evidence status (`PASS/FAIL/UNKNOWN`), require explicit acceptance criteria before implying tradeability, expose missing required checks prominently.

### AUD-032 — Replay export backdates derived claims and wallet linkage

- **Component / source:** `replay_sources.py::from_db` (68–109).
- **Severity / confidence:** **High / High, code-confirmed; existing AUD-002 previously independently reproduced late extraction**.
- **Actual:** Exports all current CALL rows using `social_items.first_observed_at` as availability for extracted assertions, and evaluates currently active wallet assertions without their approval/recorded time as historical availability. The isolated replay core cannot detect this leakage once the exported document backdates inputs.
- **Impact:** Apparent historical trader/source corroboration and backtest causality may be false even when inner replay leakage checks pass.
- **Remediation:** Enforce derived availability at extraction and wallet-assertion verification, supersession/identity changes as of each cutoff, and add *database-export→replay* adversarial tests.
- **Relationship:** Reconfirms AUD-002 rather than replacing or closing it.

### AUD-033 — Signal generation market context can predate its own retrieval

- **Component / source:** `outcomes_core.py::_fact_time`, `market_at_generation`, `make_signal` (115–223); later observation adapter `outcomes_cli.py` (85–109).
- **Severity / confidence:** **Medium / High code certainty; actual live contamination unverified**.
- **Actual:** `_fact_time` prefers `as_of` over `fetched_at`; market context is eligible if that time is no later than `generated_at`. A backfilled price or route fact that reflects an earlier market moment but was obtained later may appear as known at generation. `make_signal` flags late signal capture, but this does not itself prove each fact was already acquired.
- **Impact:** The immutable emission-time research context may inherit unavailable market evidence; prospective measurement becomes contaminated if upstream fact provenance is not enforced.
- **Remediation:** Check both market time and available-at/fetched-at, refuse unknown retrieval time for point-in-time source facts, and add a late-price-backfill-to-early-signal mutation test. Do not apply this defect to observations already correctly indexed by availability.

### Phase 03 retention and test limits

AUD-001, AUD-002, AUD-008, AUD-012, AUD-015 and AUD-017 remain open or evidence-limited from prior phases. Other existing IDs are preserved as originally recovered. Phase 02 AUD-018–023 **cannot be reconstituted faithfully without the Phase 02 file**. No test suite was rerun in this phase; the earlier reported 651 pass/1 fail is prior Phase 01 evidence, not a new result. All Phase 03 reproductions use invented prices, times, wallets or route quotes; they demonstrate implementation mechanics, not live alpha. No production code, external service, credential, trades or tracked database modified. STOP after this audit.

## Cumulative audit continuity: later independent phases, 2026-10-13

The register above is the complete recovered Phase 00/01 findings as in the available \`FINDINGS.md\`. The original Phase 02/03/04/05 reports were produced separately from the consolidated publication. M00 has restored original report bytes (Phase 02/03 uploads and newly supplied Phase 00/01/04/05 archive members), and preserved the Phase 02/03 findings snapshots unchanged. The following is an **index** to those additional findings, not a fabricated claim that the repository ran those tests again. No prior issue has been independently closed.

**Architecture audit ARCH-001–015 (now source-anchored):** historical knowledge-time selection; per-connection SQLite foreign keys; primary-source to extractor handoff; iterator lifecycle; public/private/outcome state recovery; cross-chain legacy identity; publication lineage; append-only growth; unknown-as-none in reporting; cursor contiguousness; cross-store atomicity; provider lifecycle; LLM billing/cost; deletion/retention; modularization. \`02_ARCHITECTURE_AUDIT.md\` is the full source.

**Adversarial ADV-001–009:** overly permissive private DB files; expired private text availability before purge; model credential config gaps; conditional Helius redaction; malformed model response; Telegram retry/error handling; non-atomic LLM reservations; content guard doesn't inspect arbitrary Markdown/CSV; live X deletion not complete. \`04_ADVERSARIAL_AUDIT.md\` is the full source. These are graded code/theoretical risks; none is evidence of a live exploited attack.

**Operational audit index (primary OPS IDs/severity/evidence in `originals/phase05/FINDINGS.md:226–235`; report in `originals/phase05/05_OPERATIONS_AND_UX.md`):**

| ID | Finding | Rating | Evidence |
|---|---|---|---|
| OPS-001 | No demonstrated unattended full pipeline or external missed-run watchdog | High | Source/runbook/prior |
| OPS-002 | Cannot guarantee complete expected source universe and cursor completeness | High | Source/prior |
| OPS-003 | No tested encrypted whole-system multi-store backup and restore | High | Runbook/architecture; not verified |
| OPS-004 | Paid API resource/model budget guard not assured under zero prices/concurrency | High if enabled | Source/prior |
| OPS-005 | Real external delivery receipt/crash-after-send recovery not proved | Medium | Source/prior; no live tests |
| OPS-006 | Missing data and missing classified content can look like no relevant signal | High | Source/prior |
| OPS-007 | High manual scheduling/testing/purge/recovery burden for individual operator | Medium | Runbook |
| OPS-008 | No measured research-time saved, trust or cost/actionable signal | High product impact | Unvalidated |
| OPS-009 | Append-only growth and retention/sizing automation unverified | Medium | Source/architecture |
| OPS-010 | Branch/deployment ref and rollback not a verified service lifecycle | Medium | Source/prior |

**M00 2026-10-13 correction:** the original Phase 03 report and its findings snapshot have now been recovered byte-for-byte from user-supplied originals. The detailed AUD-024–033 entries appear above. Original offline probes/logs remain unarchived; evidence remains report-authored, not independently rerun during M00.

## Phase 06 — new strategic research findings (recommendations, not newly observed code failures)

| ID | Strategic issue | Priority | Supporting evidence | Proposed gate |
|---|---|---|---|---|
| STR-001 | Incremental value over DEX/GMGN/Kaito/wallet baselines is unmeasured | High | AUD-008, OPS-008; vendor capability overlap | STR-B01 fixed cohort forward comparison |
| STR-002 | Independent origins beyond explicit repost tags need labeled evaluation | High | Deterministic Phase 07 source + graph risk hypothesis | STR-B02 origin graph precision/recall |
| STR-003 | Trader quality/popularity cannot be certified as skill | High | AUD-008/012; selected-universe risk | STR-B03/B06/B08 unseen-period scoring |
| STR-004 | Late sponsored amplification versus organic and insider distribution unvalidated | High | Narrative & onchain gap; DEX paid boost field | STR-B04 blinded campaign/flow test |
| STR-005 | Information overload and alert usefulness not measured | Medium | OPS-006/008 | STR-B07 precision@5 + time savings |
| STR-006 | Screen liquidity and historical returns are not size-specific executable proceeds | High | AUD-012; Jupiter V2 routes | STR-A05 route stress and no-quote labels |
| STR-007 | Common market/trending data can be reused rather than rebuilt | Medium | Commercial/free provider capabilities | STR-C03/E03 ROI comparison |
| STR-008 | Core source-to-claim/temporal/state gaps precede provider expansion | High | AUD-001/003/005/007/010/013 | STR-A01–A04, A06 verified gates |
| STR-009 | Historical alpha/trader research needs complete losers and causal market clocks | High | AUD-002/004/008/012 | STR-B01/B08 pre-registered full cohort |
| STR-010 | Curated, persistent SQLite + bounded outbox is preferable to untested complexity | Medium | ARCH-005/011, OPS-003/007 and resource costs | STR-C01/C02/C03 throughput and cost tests |

**Phase 06 disposition:** REFOCUS / CONDITIONAL CONTINUE. All original AUD issues remain open unless separately remedied and independently reproduced. No production code, collectors, data, credentials, schedules, transport configuration or trading behavior changed.
