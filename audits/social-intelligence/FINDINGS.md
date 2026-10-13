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

## Cumulative audit continuity: later independent phases, 2026-10-13

The register above is the complete recovered Phase 00/01 findings as in the available \`FINDINGS.md\`. Subsequent Phase 02/04/05 audit reports were archived separately in the project Library, rather than Git. Their original documents remain unchanged. The following is an **index** to those additional findings, not a fabricated claim that the repository ran those tests again. No prior issue has been independently closed.

**Architecture audit ARCH-001–015:** historical knowledge-time selection; per-connection SQLite foreign keys; primary-source to extractor handoff; iterator lifecycle; public/private/outcome state recovery; cross-chain legacy identity; publication lineage; append-only growth; unknown-as-none in reporting; cursor contiguousness; cross-store atomicity; provider lifecycle; LLM billing/cost; deletion/retention; modularization. \`02_ARCHITECTURE_AUDIT.md\` is the full source.

**Adversarial ADV-001–009:** overly permissive private DB files; expired private text availability before purge; model credential config gaps; conditional Helius redaction; malformed model response; Telegram retry/error handling; non-atomic LLM reservations; content guard doesn't inspect arbitrary Markdown/CSV; live X deletion not complete. \`04_ADVERSARIAL_AUDIT.md\` is the full source. These are graded code/theoretical risks; none is evidence of a live exploited attack.

**Operational audit index (full evidence in \`05_OPERATIONS_AND_UX.md\`):**

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

**The Phase 03 primary audit could not be recovered.** Do not cite its inferred outcomes as reproduced facts.

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
