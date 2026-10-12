# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Baseline: [AUDIT_00.md](AUDIT_00.md). Schema and connectors: [SCHEMA_01.md](SCHEMA_01.md), [CONNECTORS_02.md](CONNECTORS_02.md), [X_API_03.md](X_API_03.md), [TELEGRAM_04.md](TELEGRAM_04.md), [IDENTITY_05.md](IDENTITY_05.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).

## Position

- Current phase completed: 05 (Prompt 05: resolve exact token identity and snapshot market conditions), 2026-10-12. Prompt 05 took the Phase 05 slot; the old proposed Phase 05 (source registry) is now carry-over C-5 (D-030).
- Live provider data: none used. All proof runs on synthetic bodies in `tests/fixtures/social/resolve/`. Live X and Telegram ingest are still UNAVAILABLE (D-023, D-027).
- Next phase: 06 as proposed in ROADMAP.md (needs D-025), or C-5, unless Elving supplies Prompt 06.
- Active branch: `feature/social-intelligence`.
- Phase 05 started from `1576dda` ("Add files via upload"), as recorded in the Phase 04 handoff. No drift. Tree clean; baseline `python -m pytest tests -q` gave `1 failed, 183 passed`, as recorded.
- Pushed: Phase 05 was first uploaded through the GitHub page as `f10b406` with every file under a `files/` folder and two `.patch` files at the root (packaging error in the delivered zip). The fix commit on top of it moves the files to their real paths and removes `files/` and the patches; after it, the branch tree is identical to the session's local commit `cb1091e` (local commits `9245c0d` code and docs, `cb1091e` handoff, not pushed themselves). The fix commit was made by the session through Elving's GitHub connection in the Composio connector (GitHub Git Data API: tree, commit, fast-forward of the branch ref), 2026-10-12; the session's own git push stayed blocked (403, repo not in its sources).

## What Phase 05 added

- `memelab/social/identity.py`: `extract_mentions()` (addresses, address-bearing links, cashtags; text read in memory only), `address_shape()` (EVM length and EIP-55 checksum, base58 decoding to 32 bytes), `provider_records()` (ds, ds_search, jup_tok, gt_pools, goplus, gt_info bodies), `resolve_address()`, `resolve_ticker()`, `resolve_post()` (same-post corroboration and conflict), `persist()`, `record_relation()`, `token_identity()` (downstream API), `resolution_plan()`.
- `memelab/social/market_context.py`: `build_bundle()` (calls `normalize.build_bundle` or `chains/evm.build_bundle`), `observed_facts()`, `posting_time_facts()` (covering GeckoTerminal candle), `store_fact()` (versioned series), `attach()` (stores facts and one `social_market_context` row; refuses a non-resolved mention), `context_plan()`.
- `memelab/social/_keccak.py`: Keccak-256 and EIP-55 (hashlib's sha3_256 is not Keccak).
- `memelab/social/schema.py`: migration 5 (`social_token_resolutions`, `social_token_candidates`, `social_token_relations`, `social_market_facts`, `social_market_context`), added to `SOCIAL_TABLES`.
- `memelab/social/cli.py`: `social resolve --post --bodies [--context]`, `social identity --item|--resolution`.
- Tests: `tests/test_social_identity.py` (29). `tests/test_social_telegram.py::test_migration_4_rolls_back_cleanly` changed to stop assuming 4 is the newest migration (it compared `rollback(con, 3)` with `[4]`; now with every version above 3).
- Fixtures: `tests/fixtures/social/resolve/fx_providers.json` (invented tokens, addresses, pairs, prices; collector shapes), `post_ambiguous.json`, `post_resolved.json` (invented messages).
- Docs: `IDENTITY_05.md`, DECISIONS D-030 to D-034, ROADMAP (row 05 DONE, C-5 added, 06 NEXT, notes on 09 and 10), SCHEMA_01 (later migrations line).

## Gate, item by item

- Downstream can request exact token identity plus timestamped evidence: `identity.token_identity(con, item_key=...)` returns status, identity (chain, contract, ref_id, asset_class), candidates, evidence keys, resolver version, and market context with posting and observed price facts. Tests `test_resolved_reference_is_stored_with_ref_and_evidence`, `test_posting_time_price_comes_from_a_historical_candle_not_from_today`, CLI demo below.
- No silent symbol-only matches: `test_ticker_never_resolves_on_symbol_alone_even_with_one_candidate`, `test_same_ticker_across_chains_and_contracts_is_ambiguous`, `test_ticker_resolves_only_through_a_contract_in_the_same_post`, `test_ticker_contradicting_the_posted_contract_is_conflicted`, `test_wrapped_tokens_are_registry_assets_and_need_a_chain`.
- Prompt test list:
  - same ticker across chains and contracts: `test_same_ticker_across_chains_and_contracts_is_ambiguous`, `test_same_evm_address_on_two_chains_is_ambiguous_and_link_chain_conflict`
  - contract typo: `test_contract_typos_are_unresolved_with_near_matches` (Solana one-character typo, EIP-55 checksum mismatch, 39 hex digits)
  - spoofed name: `test_spoofed_name_contract_resolves_to_itself_and_is_flagged`
  - token migration: `test_token_migration_keeps_exact_identity_and_lists_the_successor`
  - wrapped tokens: `test_wrapped_tokens_are_registry_assets_and_need_a_chain`
  - invalid chain: `test_invalid_and_unsupported_chains` (also unsupported chains and a Solana address with an EVM chain)
  - no history: `test_no_history_leaves_the_posting_price_empty` (also unknown publication time and fetch at posting)
  - missing pool: `test_missing_pool`
  - disagreeing providers: `test_disagreeing_providers_on_symbol_keep_the_address_identity`, `test_disagreeing_price_providers_each_keep_a_row`
  - liquidity versus executable proceeds: `test_reported_liquidity_versus_executable_proceeds`, `test_evm_context_uses_provider_usd_proceeds`
  - also: `test_valuation_fields_carry_supply_denominators_units_and_windows`, `test_facts_are_versioned_per_series_and_refetch_is_idempotent`, `test_persist_is_idempotent_and_ambiguous_stores_candidates`, `test_context_refuses_anything_not_resolved`, `test_no_text_reaches_the_database_and_guard_passes`, `test_migration_5_rolls_back_cleanly`, `test_resolution_plan_reuses_existing_builders`, `test_keccak_and_eip55_vectors`, `test_extraction_reads_text_in_memory_and_returns_only_tokens`, `test_pair_link_maps_to_its_base_token`
- Demo (temp DB, `--now 1791676800`, both exit 0; also `test_cli_demo_ambiguous_message_and_resolved_address`):
  - `social resolve --post tests/fixtures/social/resolve/post_ambiguous.json --bodies tests/fixtures/social/resolve/fx_providers.json --context`: status `ambiguous`; mention TICKER PEPE; reasons `symbol_only, multiple_candidates, candidates_on_several_chains`; identity None; 4 viable candidates (ethereum, two solana, bsc) and 1 rejected (arbitrum, unsupported); no market context.
  - `social resolve --post .../post_resolved.json --bodies .../fx_providers.json --context`: status `resolved`; LINK `https://pump.fun/coin/8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ` -> solana `8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ`, stored as a `social_token_refs` CONTRACT_ADDRESS ref; ticker LABDOG resolved through it; context `HISTORICAL_CANDLE`, posting price 0.0062 (hourly candle open), observed price 0.01 (jupiter), lag 77400 s.
  - `social identity --item telegram:-1001000000001_22`: exit 0, both mentions resolved.
- Migration on a copy of the tracked DB: `schema.migrate()` applied `[1, 2, 3, 4, 5]`; `content_guard.check_sqlite` on the copy: `[]`. The tracked file is unchanged.

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest numpy`).
- Outcome after the last code change: exit 1, `1 failed, 212 passed in 13.27s`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1, untouched).
- `python -m pytest tests/test_social_identity.py -q` -> `29 passed`.
- `python -m memelab social guard` exit 0 (241 files, 69 JSON, 0 violations, Phase 05 files staged).
- Side effect still present: the EVM test writes `data/reports/<stamp>_BRETT_0x532f.md`; deleted by hand after each run (C-1). `git status` clean after that.

## Files changed in Phase 05

`docs/social-intelligence/DECISIONS.md`, `HANDOFF.md`, `IDENTITY_05.md`, `ROADMAP.md`, `SCHEMA_01.md`; `memelab/social/_keccak.py`, `cli.py`, `identity.py`, `market_context.py`, `schema.py`; `tests/test_social_identity.py`, `tests/test_social_telegram.py`; `tests/fixtures/social/resolve/fx_providers.json`, `post_ambiguous.json`, `post_resolved.json`.

## Things the next phase should know

- Ingestion does not call the resolver yet. Inbound items carry a content hash, not text (D-016), so a connector has to run `identity.resolve_post()` on the text before hashing it, or a later inbound version has to carry the addresses and links it found. Planned for proposed Phase 10.
- Counting phases must use `status='resolved'` rows only, and still call `store.is_independent_original()` (D-029).
- `catalyst/match.py` still picks the most liquid Solana token for a term (its own AMBIGUOUS label, catalyst tables only). It was left alone (D-034).
- Supply-basis readings of provider fields and the validity windows are lab conventions not checked against provider docs (D-033).
- The legacy `tokens` table is keyed by mint only; Phase 05 does not write it.

## Blockers and open decisions

- Push: `git push` from a Cowork session is blocked unless the session is started with `memelab-inbox` as a source. Working route used in Phase 05: Elving's GitHub connection in Composio (writes as RyzinEnagy). The standing rule still holds: feature work only on `feature/social-intelligence`, never `main` (D-001).
- D-025 (X browser automation), D-028 (Telegram bot terms) and the X budget (D-023) are still open.
- Phase prompts 06 onward not supplied; ROADMAP.md entries are proposals.

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q
```

Expect `1 failed, 212 passed` and `python -m memelab social guard` exit 0. Then start the next phase.
