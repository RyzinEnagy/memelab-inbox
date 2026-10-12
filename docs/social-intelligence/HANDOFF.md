# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Baseline: [AUDIT_00.md](AUDIT_00.md). Schema and connectors: [SCHEMA_01.md](SCHEMA_01.md), [CONNECTORS_02.md](CONNECTORS_02.md), [X_API_03.md](X_API_03.md), [TELEGRAM_04.md](TELEGRAM_04.md), [IDENTITY_05.md](IDENTITY_05.md), [CLAIMS_06.md](CLAIMS_06.md), [NARRATIVES_07.md](NARRATIVES_07.md), [REGISTRY_08.md](REGISTRY_08.md), [WALLETS_09.md](WALLETS_09.md), [PERFORMANCE_10.md](PERFORMANCE_10.md), [ALPHA_11.md](ALPHA_11.md), [CHRONOLOGY_12.md](CHRONOLOGY_12.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).

## Position

- Current phase completed: 12 (Prompt 12: reconcile social claims with on-chain chronology), 2026-10-12. Prompt 12 took the Phase 12 slot; the old proposed Phase 12 (paid, bot and coordination signals) is now carry-over C-12 (D-080).
- Model status: unchanged, none configured (D-036). Phase 12 makes no model call.
- Data status: no live post, wallet fetch or candle source was used. Every proof ran on invented, labelled fixtures. The tracked database holds no chronology rows; fixture runs into it are refused.
- Next phase: 13 as proposed in ROADMAP.md, or a carry-over, unless Elving supplies Prompt 13. Not started.
- Active branch: `feature/social-intelligence`.
- Phase 12 started from `9dea010` ("social-intel phase 11: record commit and push route in handoff"), the commit on the remote branch. No drift. Baseline `python -m pytest tests -q` at the start (known clock test deselected): `474 passed`, matching the Phase 11 handoff's `1 failed, 474 passed`.
- Commit and push: see the end of this file.

## What Phase 12 added

- `memelab/social/chrono_core.py`: the engine, no I/O and no clock. Post merging and dedupe, intervals per clock (SOURCE_PUBLICATION, CHAIN_BLOCK, COLLECTION, CANDLE), slot bounding for a missing block time, identity checks on every join, wallet classes from the Phase 09 level, event actions (transfer is never a sale, custody, internal), candle preference and fallback, zigzag price and liquidity moves, coverage, the five observed patterns plus ORDER_INDETERMINATE, flags, the fact / inference / not established summary, the accusatory-word guard, `analyze` (evaluates twice and compares hashes), `report`.
- `memelab/social/chrono_store.py`: `build_input` from Phase 01/03/04 items and observations, Phase 06 current claims, Phase 05 resolved tokens, Phase 09 assertions (`wallet_assertions.explain`), tracked wallets, fetches and events, Phase 11 candles and observed-at-fetch liquidity facts; `save_run`, `load_run`, `verify_run`, `current_flags`, `status`.
- `memelab/social/chrono_cli.py` and `cli.py`: `python -m memelab social chrono <run|show|verify|flags|status>`.
- `memelab/social/schema.py`: migration 12 (`social_chrono_runs`, `social_chrono_flags`). The schema refuses a RISK flag that is FACT or UNKNOWN, a RISK flag without a LINKED or CLAIMED wallet, a FACT flag outside DATA_QUALITY, and a non-data-quality flag without evidence.
- Tests: `tests/test_social_chronology.py` (31). `tests/test_social_alpha.py::test_migration_11_rolls_back_cleanly_and_leaves_phase_10_alone` changed to stop assuming 11 is the newest migration.
- Fixtures: `tests/fixtures/social/chrono/confident.json`, `indeterminate.json`, built by `make_chrono.py` (a test checks the files match the script). Invented sources, wallets, posts and prices.
- Docs: `CHRONOLOGY_12.md` (clocks, rules, patterns, flags, both fixture walkthroughs, limits), DECISIONS D-080 to D-084, ROADMAP (12 DONE, C-12 added, 17 and 18 depend on C-12), SCHEMA_01, SOURCE_COVERAGE.

## Gate, item by item

- Ordering accurate or explicitly uncertain: order is decided by non-overlapping intervals only (D-081). Confident fixture: `order_status` CONFIDENT (`test_confident_fixture_orders_every_pair`). Indeterminate fixture: INDETERMINATE, no ordered pattern inferred, every entry in one overlap group (`test_indeterminate_fixture_says_so_and_claims_no_order`). Also `test_same_minute_ordering_ambiguity`, `test_missing_publication_time_uses_first_sighting_as_an_upper_bound_only`, `test_missing_block_time_is_bounded_by_neighbouring_slots_or_left_unplaced`, `test_nothing_after_as_of_is_used`.
- Links trace to original evidence: every fact and inference line has links (post URL, observation id, explorer URL, `tx:` signature, assertion id and evidence ref, candle source), and risk flags cite the post and the transaction (`test_links_trace_to_original_evidence`, `test_source_deletion_keeps_the_evidence_and_brackets_the_removal`).
- No unsupported ownership or manipulation claims: wallets below LINKED or uncontested SELF_CLAIMED produce no pattern (`test_uncertain_attribution_never_becomes_an_accusation`, `test_conflicting_wallets_are_shown_but_never_attributed`, `test_two_people_using_one_custodian`); risk flags are never FACT, enforced in code and schema (`test_risk_flags_are_never_fact_and_the_text_guard_refuses_accusations`, `test_schema_refuses_fact_risk_flags_and_risk_without_attribution`); every wallet carries `real_world_identity: UNKNOWN`; absence carries coverage and is UNKNOWN (`test_absence_of_a_monitored_trade_is_never_evidence`).
- Prompt test list, each a named test: delayed API delivery (`test_delayed_api_delivery_orders_by_publication_and_says_when_the_lab_knew`), missing/block timestamp (`test_missing_block_time_is_bounded_by_neighbouring_slots_or_left_unplaced`, `test_missing_publication_time_uses_first_sighting_as_an_upper_bound_only`), token symbol collision (`test_token_symbol_collision_never_joins`), conflicting wallets, same-minute ordering ambiguity, unrelated transfer (`test_unrelated_transfer_and_transfers_are_never_sales`), two separate persons using one custodian (`test_two_people_using_one_custodian`), promotional repost (`test_promotional_repost_uses_the_repost_time_and_is_marked`), missing price (`test_missing_price_is_not_established_and_live_quotes_never_stand_in`), source deletion (`test_source_deletion_keeps_the_evidence_and_brackets_the_removal`).
- Also asked for: time-window configuration (`test_time_window_configuration`), dedupe (`test_dedupe_of_posts_sightings_and_events`), missing-provider fallbacks (`test_market_source_fallback_and_no_future_candles`, provider UNAVAILABLE cases in the absence and missing-price tests), stale-evidence warnings (`test_stale_evidence_warnings`), normalized flags stored and read back by token (`test_run_store_verify_flags_and_tamper`), store end to end from DB rows (`test_build_input_from_stored_rows_end_to_end`), human-readable output and CLI (`test_cli_demo_and_fixtures_never_reach_the_tracked_database`).
- Demo: `python -m memelab social chrono run --input tests/fixtures/social/chrono/confident.json` exit 0, "Order between posts and trades: CONFIDENT"; the same with `indeterminate.json` exit 0, "INDETERMINATE". Output is in CHRONOLOGY_12.md.
- Migration on a copy of the tracked DB: `schema.migrate()` applied `[1, ..., 12]`; `content_guard.check_sqlite` on the copy: `[]`. The tracked file is unchanged.

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest numpy`).
- Outcome after the last code change: exit 1, `1 failed, 505 passed`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1, untouched).
- `python -m pytest tests/test_social_chronology.py -q` -> `31 passed`.
- `python -m memelab social guard` exit 0 (0 violations).
- Migration 12 applies, rolls back to 11 (Phase 11 table definitions byte-identical) and reapplies.
- The EVM test still writes `data/reports/<stamp>_BRETT_*.md`; deleted by hand after each run (C-1).

## Things the next phase should know

- Read flags with `chrono_store.current_flags(con, chain=, contract=, category=)`: newest run per token and source, fixtures hidden. A RISK flag is a reason to look, never a verdict.
- `posts_enumerated` and provider status are not stored by earlier phases; pass them in `--annotations` or they default to false and empty.
- Monitoring coverage is `watch_since` to the last good fetch; a capped fetch can hide older transactions.
- The chronology reads only resolved tokens and current extractions, like Phases 07 and 11. Ingestion still does not call extraction or the resolver (Phase 06 note).
- One token and one source per run; cross-source coordination is C-12.
- Nothing is scheduled.

## Helius key

The key is not in the repo and must never be committed. Code reads it through `memelab/secrets.py`, in this order:

1. The `HELIUS_API_KEY` environment variable. Use this for a scheduled run, CI or a cloud session (set it as a secret there).
2. `helius_api_key` in `data/config.json`. That file is gitignored. On a machine, create it with `python -m memelab.secrets set` (prompts without echo).

Check with `python -m memelab.secrets status` (prints "set" or "missing" and the source, never the value). `Plan.wallet_activity`, `Plan.wallet_forensics`, `wallet_plan` and `rpc_url` all use it. If it is missing, plan building raises "helius_api_key missing" and the public RPC is used for plain RPC calls.

Saved plan files under `data/inbox` are tracked, so `Plan.save` rewrites `api-key=...` to `api-key=REDACTED`. The pasted browser call (`Plan.js_call`) keeps the real key because the collector needs it. `tests/test_secrets.py` fails if any tracked file holds a real `api-key=` value.

A new session that needs the key should ask Elving to supply it (it is not stored in memory or project docs) and write it to `data/config.json` or export `HELIUS_API_KEY`. The key was pasted into a chat once; rotate it if that chat is shared.

## Blockers and open decisions

- Push: the session's own `git push` is not used. Working route: Elving's GitHub connection in Composio, Git Data API (blobs, trees, commits, fast-forward of the feature branch ref, no force, D-001).
- No live posts, wallet fetches or candle provider in session, so every real chronology is UNAVAILABLE until those exist.
- D-025, D-028, D-023 and D-036 remain open.
- Phase prompts 13 onward not supplied; ROADMAP.md entries are proposals.

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q
```

Expect `1 failed, 505 passed` and `python -m memelab social guard` exit 0.

## Commit and push

Phase 12 code commit on `feature/social-intelligence`: `821a66d` (tree f4ab11a4d9bbf92fcb70485a2c42c7f8dbdfa103, parent 9dea0106f18007b1ec621f6b01568fa0c8772615; local hash 0ae4036). This handoff correction is the commit on top of it.

The sandbox `git push` is not used. The push went through Composio and the GitHub Git Data API: the changed files went over as a checksummed xz bundle (new files whole, modified files as a patch against 9dea010, fixtures regenerated by `make_chrono.py`), every blob sha was checked against the local file, the tree sha was compared with the local tree before the commit was created, and the branch ref was moved forward once, without force. `main` was not touched.

Phase 13 is not started.
