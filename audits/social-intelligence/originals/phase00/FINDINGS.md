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
