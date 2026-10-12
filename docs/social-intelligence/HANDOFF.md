# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Baseline: [AUDIT_00.md](AUDIT_00.md). Schema and connectors: [SCHEMA_01.md](SCHEMA_01.md), [CONNECTORS_02.md](CONNECTORS_02.md), [X_API_03.md](X_API_03.md), [TELEGRAM_04.md](TELEGRAM_04.md), [IDENTITY_05.md](IDENTITY_05.md), [CLAIMS_06.md](CLAIMS_06.md), [NARRATIVES_07.md](NARRATIVES_07.md), [REGISTRY_08.md](REGISTRY_08.md), [WALLETS_09.md](WALLETS_09.md), [PERFORMANCE_10.md](PERFORMANCE_10.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).

## Position

- Current phase completed: 10 (Prompt 10: wallet performance accounting), 2026-10-12. Prompt 10 took the Phase 10 slot; the old proposed Phase 10 (mentions by contract address) is now carry-over C-10 (D-065).
- Model status: unchanged, none configured (D-036). Phase 10 makes no model call.
- Data status: no live provider call was made, no price source was fetched and no real wallet was used. Every proof ran on invented, labelled fixtures. The tracked database holds no wallet or performance rows; fixture runs into it are refused.
- Next phase: 11 as proposed in ROADMAP.md, or a carry-over, unless Elving supplies Prompt 11. Not started.
- Active branch: `feature/social-intelligence`.
- Baseline at start: two failures, not the one the Phase 09 handoff expected: the clock test (C-1) and `tests/test_secrets.py`, which flagged prose such as `api-key=...` in this file. The secrets check now looks at key shape (D-072). The Phase 09 handoff said 377 passed; the real count at the start was 376.
- Commit and push: see the end of this file.

## What Phase 10 added

- `memelab/social/perf_core.py`: the accounting engine, no I/O and no network. Ledger parsing and validation, price book, lots, FIFO and AVCO, swaps, transfers, airdrops, group transfers, liquidity, dust, contamination. Version `wallet-performance-v1`.
- `memelab/social/perf_analysis.py`: positions, metrics, realized / unrealized / liquidation lines, coverage, reconstruction status, reconciliation checks, equity and drawdown, sensitivities, score gate, ranking, provider comparison, plain-English report.
- `memelab/social/perf_store.py`: builds a ledger from Phase 09 events (reads them, changes nothing), stores supplied prices and asset roles, stores and verifies runs.
- `memelab/social/perf_cli.py` and `cli.py`: `python -m memelab social perf <run|prices|meta|show|verify|rank|compare|status>`.
- `memelab/social/schema.py`: migration 10 (five `social_perf_*` tables).
- `tests/test_secrets.py`: key-shape check (D-072).
- Tests: `tests/test_social_performance.py` (57). Fixtures: `tests/fixtures/social/perf/` (`ledger_main.json`, `expected_main.json`, `ledger_scored_outlier.json`, `ledger_scored_clean.json`, `make_scored.py`), all invented and labelled.
- Docs: `PERFORMANCE_10.md` (rules, definitions, thresholds, hand-check tables, demo, limits), DECISIONS D-065 to D-072, ROADMAP (10 DONE, C-10 added), SOURCE_COVERAGE, SCHEMA_01.

## Gate, item by item

- Repeatable P&L with deterministic reconciliation checks: every result runs 10 checks (plus 4 warnings), analyses twice and compares hashes; a stored run is verified by recomputation; the same ledger gives the same hash (`test_the_same_ledger_gives_the_same_result_hash_and_a_changed_ledger_does_not`, `test_stored_run_repeats_verifies_and_detects_tampering`, `test_a_broken_engine_fails_reconciliation_and_the_score_is_refused`).
- Gaps explicit: history coverage (UNKNOWN, TRUNCATED, PLAUSIBLY_COMPLETE), opening lots from missing history, contaminated tokens, rejects with reasons, unknown fees, unpriced swaps, and a reconstruction status with the sentence "Comprehensive reconstruction cannot be achieved: ..." (tests on the main fixture, truncated and 429 cases).
- Mark-to-market vs executable proceeds explicit and separate, with the gap (`test_main_fixture_metrics_and_unrealized_lines_are_separate`, `test_rug_position_marks_at_cost_but_sells_for_nothing`, `test_missing_stale_and_curve_quotes`).
- Prompt test list, each a named test: partially missing history, multiple lots, wash-like transfers, fee-on-transfer, decimal errors, rug with no route, wallet to wallet, profitable outlier, stablecoin peg change, no price. Hand-checked fixture ledger with an expected file. Score refusal demonstrated (`test_wallet_score_refuses_a_sparse_wallet_and_says_why`, CLI demo in PERFORMANCE_10.md).
- Full existing suite: see Tests.

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest numpy`).
- Outcome after the last code change: exit 1, `1 failed, 435 passed`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1, untouched).
- `python -m memelab social guard` exit 0 (0 violations).
- Migration 10 applies, rolls back to 9 (Phase 09 table definitions byte-identical) and reapplies in `test_migration_10_rolls_back_cleanly_and_leaves_phase_09_tables_alone`.
- The EVM test still writes `data/reports/<stamp>_BRETT_*.md`; deleted by hand after each run (C-1).
- `MEMELAB_DB` can leak from other test modules into subprocesses; the Phase 10 CLI helper unsets it.

## Things the next phase should know

- No price source is wired in. Real wallets need prices imported with `social perf prices import` before any USD figure exists. Native-unit figures need none. A first real run will mostly show INSUFFICIENT_DATA, which is correct.
- Phase 09 stores decimal amounts only, so decimals cannot be re-verified from stored events. A ledger built by hand can carry raw amounts and decimals and is checked.
- Only the newest transactions up to the fetch limit are read, so history is rarely shown complete. PLAUSIBLY_COMPLETE is not proof, because the limit actually requested from the provider is not stored.
- Wallet groups are declared by an analyst with a reason and matched by signature. Nothing links wallets automatically.
- Liquidity fees and impermanent loss are not computed; LP tokens are not valued.
- Thresholds are in `perf_core.DEFAULT_POLICY` and are part of the input hash; change one and the run is a new run.
- Nothing is scheduled; scheduling belongs to a later phase.

## Helius key

The key is not in the repo and must never be committed. Code reads it through `memelab/secrets.py`, in this order:

1. The `HELIUS_API_KEY` environment variable. Use this for a scheduled run, CI or a cloud session (set it as a secret there).
2. `helius_api_key` in `data/config.json`. That file is gitignored. On a machine, create it with `python -m memelab.secrets set` (prompts without echo).

Check with `python -m memelab.secrets status` (prints "set" or "missing" and the source, never the value). `Plan.wallet_activity`, `Plan.wallet_forensics`, `wallet_plan` and `rpc_url` all use it. If it is missing, plan building raises "helius_api_key missing" and the public RPC is used for plain RPC calls.

Saved plan files under `data/inbox` are tracked, so `Plan.save` rewrites `api-key=...` to `api-key=REDACTED`. The pasted browser call (`Plan.js_call`) keeps the real key because the collector needs it. `tests/test_secrets.py` fails if any tracked file holds a real `api-key=` value.

A new session that needs the key should ask Elving to supply it (it is not stored in memory or project docs) and write it to `data/config.json` or export `HELIUS_API_KEY`. The key was pasted into a chat once; rotate it if that chat is shared.

## Blockers and open decisions

- Push: the session's own `git push` gets 403. Working route: Elving's GitHub connection in Composio, Git Data API, fast-forward of the feature branch ref, no force (D-001).
- No permitted live wallet list in session and no price source, so live performance status is UNAVAILABLE.
- D-025, D-028, D-023 and D-036 remain open.
- Phase prompts 11 onward not supplied; ROADMAP.md entries are proposals.

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q
```

Expect `1 failed, 435 passed` and `python -m memelab social guard` exit 0.

## Commit and push

PUSH_PLACEHOLDER
