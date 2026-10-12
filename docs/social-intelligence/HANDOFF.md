# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Baseline: [AUDIT_00.md](AUDIT_00.md). Schema and connectors: [SCHEMA_01.md](SCHEMA_01.md), [CONNECTORS_02.md](CONNECTORS_02.md), [X_API_03.md](X_API_03.md), [TELEGRAM_04.md](TELEGRAM_04.md), [IDENTITY_05.md](IDENTITY_05.md), [CLAIMS_06.md](CLAIMS_06.md), [NARRATIVES_07.md](NARRATIVES_07.md), [REGISTRY_08.md](REGISTRY_08.md), [WALLETS_09.md](WALLETS_09.md), [PERFORMANCE_10.md](PERFORMANCE_10.md), [ALPHA_11.md](ALPHA_11.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).

## Position

- Current phase completed: 11 (Prompt 11: Information Alpha Score), 2026-10-12. Prompt 11 took the Phase 11 slot; the old proposed Phase 11 (attention metrics) is now carry-over C-11 (D-079).
- Model status: unchanged, none configured (D-036). Phase 11 makes no model call.
- Data status: no live provider call, no candle source and no live claim was used. Every proof ran on invented, labelled fixtures. The tracked database holds no alpha rows; fixture runs into it are refused.
- Next phase: 12 as proposed in ROADMAP.md, or a carry-over, unless Elving supplies Prompt 12. Not started.
- Active branch: `feature/social-intelligence`.
- Phase 11 started from `980a417` ("social-intel phase 10: record push in handoff"), the commit on the remote branch. No drift (remote ref checked before work and again before the push). Baseline `python -m pytest tests -q` at the start: `1 failed, 435 passed` as the Phase 10 handoff said.
- Commit and push: see the end of this file.

## What Phase 11 added

- `memelab/social/alpha_core.py`: the engine, no I/O and no clock. Candle validation (`prep_series`), eligibility rules, entry and exit with delay and costs, matched baseline, per-horizon returns, excursions, lead time and move lag, author-trade context, per-source metrics, conservative shrunk score with tiers, `rank`, `analyze` (evaluates twice and compares hashes), `report`. Versions `information-alpha-v1` and `alpha-rules-v1`.
- `memelab/social/alpha_store.py`: stores supplied candles, builds an input document from current Phase 06 claims (newest extraction only, Phase 05 resolved tokens only, trader link or account as the source), stores runs with their exact input, verifies a run by recomputation.
- `memelab/social/alpha_cli.py` and `cli.py`: `python -m memelab social alpha <run|series import|show|verify|rank|status>`.
- `memelab/social/schema.py`: migration 11 (`social_alpha_series`, `social_alpha_candles`, `social_alpha_runs`, `social_alpha_scores`). The schema refuses any candle kind other than HISTORICAL_CANDLE and a scored row without a score or a declined row with one.
- Tests: `tests/test_social_alpha.py` (39). `tests/test_social_performance.py::test_migration_10_rolls_back_cleanly_and_leaves_phase_09_tables_alone` changed to stop assuming 10 is the newest migration (same fix Phase 06 made for 5).
- Fixture: `tests/fixtures/social/alpha/alpha_main.json`, built by `make_alpha.py` (a test checks the file matches the script). Invented sources, tokens, posts and prices.
- Docs: `ALPHA_11.md` (rules, formulas, hand check, fixture walkthrough, limits), DECISIONS D-073 to D-079, ROADMAP (11 DONE, C-11 added), SCHEMA_01, SOURCE_COVERAGE.

## Gate, item by item

- The engine can decline to rank: `test_zero_eligible_calls_decline_and_rank_nothing`, `test_three_great_calls_never_make_a_great_score`, `test_hindsight_selected_calls_are_ineligible_and_the_source_is_declined`, CLI `alpha run` on an empty input exits 0 and prints "Declining is the correct output", `alpha rank --input` returns an empty ranking. In the end-to-end fixture, source B (3 calls) and source C (late-found winners, 6 of 40 posts supplied) are declined; only source A is ranked, preliminary, score 50 (point estimate 53).
- Wallet profits remain separate: `alpha_core` imports nothing from Phase 10 (asserted in `test_popularity_and_wallet_profit_stay_out_of_the_formula`); author trades are context only and changing them does not move the score (`test_author_trades_are_context_only`); migration 11 touches no `social_perf_*` table (`test_migration_11_rolls_back_cleanly_and_leaves_phase_10_alone`); no alpha table has a profit, follower or engagement column.
- Prompt test list, each a named test: late promotion after pump (`test_late_promotion_after_pump_is_kept_flagged_and_negative`), hindsight-selected call, repeated reposts (`test_repeated_reposts_and_repeat_posts_do_not_inflate_the_sample`), delisted tokens, price gaps (`test_price_gaps_are_not_filled`), illiquid execution (`test_illiquid_execution_is_refused_or_charged`), null baseline (`test_null_baseline_gives_no_edge_and_no_validation`), temporal leakage (`test_nothing_after_as_of_is_used`, `test_entry_and_matching_do_not_depend_on_later_candles`, `test_a_live_quote_replayed_as_history_is_rejected`), zero eligible calls, conflicting bullish and bearish statements (`test_conflicting_bullish_and_bearish_statements_exclude_both`), statistically noisy sample (`test_noisy_sample_stays_preliminary_with_an_interval_that_spans_zero`).
- End-to-end fixture with transparent calculations and a source for every observation: `test_end_to_end_fixture_evaluation`, `test_hand_checked_single_call` (arithmetic in ALPHA_11.md), `test_fixture_calls_recompute_independently_from_raw_candles` (a second implementation reproduces six calls and their control medians), `test_rules_are_written_down_and_versioned` (every call has a reference, every series a source). The printed report is in ALPHA_11.md.
- Explainable metrics and tiers: coverage, independent calls, median relative return against matched tokens, lead-time distribution, false positives, failures to beat controls, 95% intervals from 8 values, shrinkage, abstention, UNVERIFIED, PRELIMINARY and VALIDATED (`test_score_grows_with_evidence_and_validated_needs_every_gate`, `test_ranking_orders_validated_above_preliminary_and_lists_declines`). Source popularity is not read (`test_popularity_and_wallet_profit_stay_out_of_the_formula`).

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest numpy`).
- Outcome after the last code change: exit 1, `1 failed, 474 passed`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1, untouched).
- `python -m pytest tests/test_social_alpha.py -q` -> `39 passed`.
- `python -m memelab social guard` exit 0 (0 violations).
- Migration 11 applies, rolls back to 10 (Phase 10 table definitions byte-identical) and reapplies.
- The EVM test still writes `data/reports/<stamp>_BRETT_*.md`; deleted by hand after each run (C-1).

## Things the next phase should know

- No candle provider is wired in. Real runs need `alpha series import` of historical candles with pool liquidity per candle (taken as liquidity at the candle start). Until then every real source is declined, which is correct.
- The number of posts the collector enumerated for a source is not stored by earlier phases. `alpha run --as-of` leaves `universe_count` unknown unless `--annotations` supplies `{"universe": {"<source>": {"count": N, "basis": "..."}}}`; unknown caps the tier at PRELIMINARY. Phase 15 (call capture) should record it.
- Attributed author trades also come from the annotations file (`author_trades`). Wiring Phase 09 wallet events in as attributed trades is not done.
- The comparison pool is every supplied series not called by any source in the run. If supplied candles are only for tokens someone already cared about, the pool is thin and relative returns will be missing (fewer than 5 controls).
- Thresholds are in `alpha_core.DEFAULT_POLICY` and are part of the input hash; change one and the run is a new run.
- Count claims only from current extractions and resolved tokens (D-029); `build_input` does both.
- Ingestion still does not call extraction or the resolver (Phase 06 note).
- Nothing is scheduled; scheduling belongs to a later phase.

## Helius key

The key is not in the repo and must never be committed. Code reads it through `memelab/secrets.py`, in this order:

1. The `HELIUS_API_KEY` environment variable. Use this for a scheduled run, CI or a cloud session (set it as a secret there).
2. `helius_api_key` in `data/config.json`. That file is gitignored. On a machine, create it with `python -m memelab.secrets set` (prompts without echo).

Check with `python -m memelab.secrets status` (prints "set" or "missing" and the source, never the value). `Plan.wallet_activity`, `Plan.wallet_forensics`, `wallet_plan` and `rpc_url` all use it. If it is missing, plan building raises "helius_api_key missing" and the public RPC is used for plain RPC calls.

Saved plan files under `data/inbox` are tracked, so `Plan.save` rewrites `api-key=...` to `api-key=REDACTED`. The pasted browser call (`Plan.js_call`) keeps the real key because the collector needs it. `tests/test_secrets.py` fails if any tracked file holds a real `api-key=` value.

A new session that needs the key should ask Elving to supply it (it is not stored in memory or project docs) and write it to `data/config.json` or export `HELIUS_API_KEY`. The key was pasted into a chat once; rotate it if that chat is shared.

## Blockers and open decisions

- Push: the session's own `git push` is not used. Working route: Elving's GitHub connection in Composio, Git Data API (blobs, trees, commits, fast-forward of the feature branch ref, no force, D-001).
- No candle provider and no permitted live claims in session, so live alpha status is UNAVAILABLE.
- D-025, D-028, D-023 and D-036 remain open.
- Phase prompts 12 onward not supplied; ROADMAP.md entries are proposals.

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q
```

Expect `1 failed, 474 passed` and `python -m memelab social guard` exit 0.

## Commit and push

Recorded in the commit that follows the Phase 11 code commit (see `git log`). Phase 12 is not started.
