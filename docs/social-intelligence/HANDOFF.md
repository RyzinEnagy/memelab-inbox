# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Baseline: [AUDIT_00.md](AUDIT_00.md). Schema and connectors: [SCHEMA_01.md](SCHEMA_01.md), [CONNECTORS_02.md](CONNECTORS_02.md), [X_API_03.md](X_API_03.md).

## Position

- Current phase completed: 03 (Prompt 03: X monitoring through the official X API v2), 2026-10-10. Prompt 03 took the Phase 03 slot that was SUPERSEDED (D-022).
- Live X ingest: UNAVAILABLE (D-023). No X developer app, token or budget consent exists; no live X API call has been made. `social x-health` reports `credentials_missing`, `live_evidence: none`.
- Next phase: 04 (manual capture onto the inbound schema) as proposed in ROADMAP.md, unless Elving supplies Prompt 04.
- Active branch: `feature/social-intelligence`.
- Phase 03 started from `71fddc4` ("Add files via upload", the D-021 upload). The Phase 02 handoff named `94046c7` plus "a further manual upload"; `71fddc4` is that upload. Tree clean; baseline `python -m pytest tests -q` gave `1 failed, 106 passed`, same as recorded.
- Local commits: `42aa49c` "social-intel phase 03: X API v2 adapter, billing guard, fixtures (live unavailable)" and the commit that adds this HANDOFF on top of it. Not pushed: the git proxy refused the push (403, `RyzinEnagy/memelab-inbox` is not in this session's authorized repository set), `GH_TOKEN` is invalid, and no GitHub connector is installed for the account. The commits were delivered to Elving as a git bundle and a patch.

## What Phase 03 added

- `memelab/social/x_api.py`: config loader (`memelab.x_api.config/1`, refuses credentials), `UrllibTransport` (only network code; token in one header), `FixtureTransport` (recorded synthetic exchanges, `memelab.x_api.fixture/1`), `BillingGuard`, `post_item()` (post to inbound/2 item; text hashed and dropped), `classify_error()`, `XApiAdapter` (scopes user, list, search, recheck), `health()`.
- `memelab/social/cli.py`: `python -m memelab social x-health [--config] [--db]` and `python -m memelab social x-ingest [--config] [--fixture] [--db] [--now] [--run-id] [--max-items] [--max-age-hours] [-v]`. Default config path `data/private/x_api.json` (gitignored).
- `memelab/social/ingest.py`: inbound schema `memelab.social.inbound/2` (optional item `context`), `_persist_context()`, provenance records the unit's schema, `redact()` now strips `Bearer <token>` first.
- `memelab/social/schema.py`: migration 3 (`social_item_context`, `social_item_refs`, `social_source_cursors`, `social_api_spend`, `social_api_billed_resources`), added to `SOCIAL_TABLES`.
- `tests/test_social_x_api.py` (36 tests), `tests/fixtures/social/x_api/fx_x_main.json`, `fx_x_second.json`, `fx_x_config.json` (invented accounts, ids and sentences).
- `tests/test_social_ingest.py::test_schema_v2_rolls_back_to_v1_only`: now uses `schema.ALL_VERSIONS` instead of the literal version 2 (needed once migration 3 exists; same change Phase 02 made to the store tests).
- Docs: `X_API_03.md` (verified contract with sources, what is stored, what is not visible, safety rails, authorization steps, rough cost, limits), `x_api.example.json`, DECISIONS D-022 to D-025, ROADMAP (row 03 DONE, C-3 added, row 06 flagged).

## Gate, item by item

- Real adapter with confirmed API contract: `memelab/social/x_api.py`; contract and sources in X_API_03.md (docs.x.com pages read 2026-10-10: pricing, usage and billing, user posts, list posts, recent search and its quickstart, rate limits, response codes, developer guidelines). Open contract points (field parameter spelling, whether expansions are billed, credits-exhausted status) are listed there as UNKNOWN.
- Live authorized ingest or explicitly marked unavailable: marked unavailable (D-023, X_API_03.md "Status", `social x-health` output below). `test_cli_fixture_flow_and_no_false_live_claim` proves fixture rows are not reported as live evidence and live `x-ingest` exits 1 with `NOT_RUN credentials_missing` and no network call (urlopen patched to fail).
- Reproducible fixture tests, by prompt item:
  - originals, replies, reposts, quotes, original author: `test_main_fixture_originals_replies_reposts_quotes_edits`
  - duplicate ids and re-ingest: `test_duplicate_ids_and_rerun_add_nothing`, `test_billing_dedupe_within_utc_day`, `test_list_cursor_applied_client_side`
  - author changes: `test_author_handle_change_keeps_one_account_and_history`
  - edited and deleted access limits: `test_edit_creates_new_id_and_longer_history_wins`, `test_recheck_marks_missing_and_protected_posts`, `test_protected_post_in_includes_is_quarantined_not_stored`, `test_protected_or_missing_user_scope`
  - pagination: main test (token on page 2), `test_page_cap_records_gap_and_advances_cursor`, `test_remaining_zero_stops_before_next_page`
  - 429: `test_429_records_reset_and_stops_scope`, `test_rate_limited_scope_is_not_called_before_reset`, `test_429_short_wait_is_waited_once_when_configured`
  - 403 and other errors: `test_http_errors_map_to_connector_status` (401, 403 x2, 404, 400), `test_5xx_bounded_retries_then_down`
  - billing guard and budget: `test_no_consent_means_no_request`, `test_run_cap_blocks_before_the_request_that_could_exceed_it`, `test_monthly_cap_counts_spend_of_the_same_mode_only`, `test_ingest_cost_budget_also_stops_requests`, `test_example_config_loads_and_is_off_by_default`
  - timestamps: `test_timestamps_provider_vs_fetch_and_future_post_quarantined`, `test_provenance_and_freshness`
  - cache freshness: `test_stale_response_is_flagged_and_health_reports_cursor_age`, `test_cursor_since_id_and_rate_limit_window`
  - secret redaction: `test_token_never_leaks`, `test_config_refuses_credentials_and_bad_scopes`, `test_health_states_without_network`, `test_credentials_missing_no_request`
  - text never stored: `test_text_is_hashed_never_stored_and_long_form_wins`
  - `/1` unchanged: `test_inbound_v1_units_unchanged_by_v2_support`
- CLI flow through stored observations (smoke, temp DB, no token in the environment):
  - `social x-health --config tests/fixtures/social/x_api/fx_x_config.json` exit 1: `credentials_missing missing 0 none: no live X API read has been made`
  - `social x-ingest --config <same>` (live) exit 1: `{"network_calls_made": 0, "reason": "credentials_missing", "status": "NOT_RUN", ...}`
  - `social x-ingest --config <same> --fixture tests/fixtures/social/x_api/fx_x_main.json --now 1791561600` exit 0: `PARTIAL fixture`, 7 requests, 7 created, 1 duplicate; health user OK, list RATE_LIMITED, search BLOCKED
  - same with `fx_x_second.json --now 1791568800` exit 0: 3 requests, 1 created, 1 duplicate; list OK after its window, user asked `since_id`
  - `social status --event x:api.1840000000000000103.9ce02d4ff96e18ed`: schema inbound/2, rights_basis synthetic_fixture, fetched 1791558000, provider 1791556200, FRESH, access_mode fixture, URL `https://x.com/example_alpha/status/1840000000000000103`, account handle `example_alpha_new`
  - `social x-health` after both runs: still `credentials_missing`, live_evidence requests 0; cursors list `...202` OK, search BLOCKED, user `...105` OK
- Migration on a copy of the tracked DB: `init_db` on a copy of `data/memelab.sqlite` applied versions `[1, 2, 3]`; `content_guard.check_sqlite` on the migrated copy: no violations. The tracked file itself is unchanged.

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest`; numpy required; node optional).
- Outcome after the last code change: exit 1, `1 failed, 142 passed in 10.22s`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (carry-over C-1, untouched).
- `python -m pytest tests/test_social_x_api.py -q` -> `36 passed`.
- `python -m memelab social guard` exit 0 (217 tracked files, 57 JSON, 0 violations, before this HANDOFF commit).
- Side effect still present: the EVM test writes `data/reports/<stamp>_BRETT_0x532f.md`; deleted by hand after each run (C-1). `git status` clean after that.

## Things the next phase should know

- Live X needs Elving's steps in X_API_03.md ("How to authorize it"). Start with one scope and `max_pages_per_scope` 1, then check `x-health` live_evidence and the console bill.
- D-025: X's Developer Guidelines say browser automation leads to permanent suspension. Proposed Phase 06 (X via signed-in Chrome) should wait for Elving's answer.
- C-3: before keeping live X data, purge earlier observations of posts that `recheck` finds NOT_FOUND (24-hour rule).
- When a test run uses the Phase 02 CLI logging setup and a later test logs inside an exception handler, Python prints "Logging error" tracebacks to stderr (stale handler on a closed stream). Harmless, pre-existing; it is why transport errors are now re-raised with the token scrubbed and no exception chain.
- Social tables are still not in the `state.py` export (scheduled-run phase).

## Blockers and open decisions

- Push: this session could not push (see Position). Elving applies the bundle or patch, or uploads the 14 files through the GitHub web page as before.
- D-025 (X browser automation vs X guidelines) and the X API budget (D-023) are Elving's decisions.
- Phase prompts 04 onward not supplied; ROADMAP.md entries are proposals.

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q
```

Expect `1 failed, 142 passed` once the Phase 03 commits are on the remote branch (`1 failed, 106 passed` if they are not yet), and `python -m memelab social guard` exit 0. Then start the next phase.
