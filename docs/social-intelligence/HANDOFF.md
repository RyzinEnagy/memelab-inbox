# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Baseline: [AUDIT_00.md](AUDIT_00.md). Schema: [SCHEMA_01.md](SCHEMA_01.md).

## Position

- Current phase completed: 01 (Prompt 01: durable schemas, evidence provenance and migration safety), 2026-10-10. Prompt 01 replaced the proposed Phase 01 and absorbed proposed Phase 03 (D-011).
- Next phase: 02. ROADMAP.md has a proposal ("Content policy and public/private storage split"); if Elving supplies Prompt 02, it replaces that entry.
- Active branch: `feature/social-intelligence`.
- Phase 01 started from `d0a0c19` (head of `origin/feature/social-intelligence`, "social-intel phase 00: ROADMAP gates follow D-009 and D-010"). Branch, HEAD and clean tree matched the Phase 00 handoff.
- Latest commit: the head of `origin/feature/social-intelligence`. Phase 01 was pushed on 2026-10-10 through the GitHub web editor in Elving's signed-in Chrome (Browser 1), same route as D-008 and approved by Elving: 14 commits whose messages start `social-intel phase 01:`, one per file plus two fix-ups (the editor appended instead of replacing on the first edits of `.gitignore` and `memelab/db.py`). The final remote tree was checked with `git diff` against the session's local commit and matched for every file. Confirm with `git log -14 origin/feature/social-intelligence`.

## What Phase 01 added

- `memelab/social/schema.py`: 14 `social_*` tables (version 1), migration ledger `social_schema_migrations` with checksums, `migrate()`, `rollback()`, `backup_db()`, CLI `python -m memelab.social.schema status|migrate|rollback [target]`.
- `memelab/social/store.py`: idempotent CRUD for accounts (with handle history), traders, trader-account links, items, append-only observations, token refs, claims and claim relations, evidence links, append-only wallet attributions, connector health, coverage, analysis versions. Timestamp normalization to UTC epoch; unknowns stay NULL with a basis column.
- `memelab/social/private.py`: gitignored private store for exact wording with retention and purge.
- `memelab/db.py`: `init_db()` calls the social migration last (2 lines). No other existing code changed.
- `.gitignore`: `data/private/` added.
- `tests/test_social_store.py` (15 tests) and `tests/fixtures/social/roundtrip_01.json` (invented accounts and text; the BRETT Base contract is the only real identifier).
- `docs/social-intelligence/SCHEMA_01.md`: exact DDL (copied from code by script), conventions, content, retention and reprocessing policy, migration and rollback plan.

## Gate, item by item

- Exact schema and migrations documented: SCHEMA_01.md.
- Insert/read/update/idempotency: `test_fixture_round_trip_and_idempotency` (same batch loaded twice, row counts identical, same ids returned), `test_account_handle_change_and_late_provider_id`, `test_connector_health_and_coverage`.
- Empty DB: `test_empty_db_init_and_repeat`. Migration from an existing DB: `test_migration_on_copy_of_tracked_db` (sqlite backup of `data/memelab.sqlite` into a temp dir, read-only source) and `test_migration_on_synthetic_legacy_db`.
- Missing timestamps: `test_missing_timestamps_and_naive_times`. Duplicate provider ids: `test_duplicate_provider_ids`. Conflicting claims: `test_conflicting_claims_are_both_kept`. Rollback and recovery: `test_backup_rollback_and_recovery`, `test_failed_migration_leaves_db_unchanged`, `test_changed_applied_migration_is_refused`.
- Current-state compatibility: row fingerprints of watchlist, theses, entries, rejections, market_snapshots, pool_snapshots, social_snapshots, holders, liquidity_quotes, price_levels, wallet_clusters and the original token columns are identical before and after migration, after full `init_db()`, and after rollback.
- Identity rules: `test_ticker_is_not_a_token_id`, `test_social_id_is_not_a_wallet_and_retractions_append`. Public-repo safety: fixture round trip asserts no source text in any social table; `test_private_store_and_summary_guard`.
- Fixture round trip runs through real SQLite, no mocks.

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest`; numpy required).
- Outcome after the last code change: exit 1, `1 failed, 78 passed in 1.69s`. The only failure is the known pre-existing, clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (same as Phase 00, untouched; carry-over C-1).
- New tests alone: `python -m pytest tests/test_social_store.py -q` -> `15 passed in 0.84s`.
- Side effect still present: the EVM test writes `data/reports/<stamp>_BRETT_0x532f.md`; deleted by hand after each run (carry-over C-1). The tracked `data/memelab.sqlite` is not modified by the suite.
- Smoke: `python -m memelab --help` exit 0; `python -m memelab social-note --help` exit 0; `MEMELAB_DB=<tmp> python -m memelab.social.schema status` -> `social schema version 1 latest 1`, exit 0.

## Things the next phase should know

- When this branch reaches `main`, the next scheduled `init_db()` on the tracked database will create the empty social tables in it. That is intended, and the tables hold no source text by design, but it changes the binary committed by scheduled runs.
- Social tables are not in the `state.py` export (decided in the scheduled-run integration phase).
- Foreign keys are off repo-wide (D-014); new writers should go through `memelab/social/store.py`.

## Blockers and open decisions

- The cloud session still has no GitHub credential; pushes go through the web editor in Elving's signed-in Chrome (Browser 1) with his approval each phase.
- Phase prompts 02 to 21 not yet supplied; ROADMAP.md entries for them are proposals.

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q
```

Expect `1 failed, 78 passed`. Then start Phase 02.
