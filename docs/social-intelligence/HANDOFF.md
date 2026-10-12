# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Baseline: [AUDIT_00.md](AUDIT_00.md). Schema and connectors: [SCHEMA_01.md](SCHEMA_01.md), [CONNECTORS_02.md](CONNECTORS_02.md), [X_API_03.md](X_API_03.md), [TELEGRAM_04.md](TELEGRAM_04.md), [IDENTITY_05.md](IDENTITY_05.md), [CLAIMS_06.md](CLAIMS_06.md), [NARRATIVES_07.md](NARRATIVES_07.md), [REGISTRY_08.md](REGISTRY_08.md), [WALLETS_09.md](WALLETS_09.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).

## Position

- Current phase completed: 09 (Prompt 09: wallet attribution and wallet activity), 2026-10-12. Prompt 09 took the Phase 09 slot; the old proposed Phase 09 (entity resolution) is now carry-over C-9 (D-056).
- Model status: unchanged, none configured (D-036). Phase 09 makes no model call.
- Data status: no live provider call was made and no real wallet or account was used. Every proof ran on invented, labelled fixtures. The tracked database holds no wallet rows; fixture ingests into it are refused.
- Next phase: 10 as proposed in ROADMAP.md, or a carry-over, unless Elving supplies Prompt 10. Not started.
- Active branch: `feature/social-intelligence`.
- Baseline at start: one known clock failure, the rest passing.
- Commit and push: see the end of this file.

## What Phase 09 added

- `memelab/social/wallet_assertions.py`: attribution assertions (append-only, audited), evidence rules and levels, labels, review, revoke, the `explain` view, funding lookup, adoption of Phase 08 registry links. Version `wallet-assertions-v1`.
- `memelab/social/wallet_activity.py`: tracked wallets with safe defaults, Helius and provider-neutral normalizers, classifier (`wallet-classifier-v1`), ingestion with 429, stale, missing-signature and future-time handling, provenance check, funding hypotheses.
- `memelab/social/sigverify.py`: pure-Python ed25519 and EIP-191 verification, checked against public vectors. Verify only.
- `memelab/social/wallet_cli.py` and `cli.py`: `python -m memelab social wallet <action>`.
- `memelab/social/schema.py`: migration 9 (eight `social_wallet_*` tables).
- `bridge/collector.js`, `memelab/bridge/collector.js`, `memelab/bridge/plan.py`: projection `helius_wallet_tx` (full signatures) and `Plan.wallet_activity`.
- Tests: `tests/test_social_wallets.py` (43). Fixtures: `tests/fixtures/social/wallets/` (invented).
- Docs: `WALLETS_09.md`, DECISIONS D-056 to D-064, ROADMAP (09 DONE, C-9 added), SOURCE_COVERAGE (wallet activity row), SCHEMA_01 (migrations line).

## Gate, item by item

- A reviewer can inspect why a wallet is linked or not: `social wallet why`, with every assertion, why it counts or not, level, label source, funding hypotheses and `Real-world identity: UNKNOWN` (tests `test_reviewer_can_read_why_in_plain_english_and_the_audit_trail_is_complete`, `test_revoked_superseded_rejected_and_out_of_window_assertions_stay_visible`).
- No link from matching names or suggestive transfers: self-disclosure reaches SELF_CLAIMED at most, patterns never count, funding is a hypothesis (tests listed in the WALLETS_09.md test map).
- Activity survives reload and repeat ingestion adds nothing: `test_events_survive_reload_and_repeat_ingestion_adds_nothing`.
- Not P&L: no price, USD, cost basis or profit column in any wallet table (`test_activity_never_becomes_profit_and_loss`).
- Prompt test list: fake ownership claim, transfer vs sell, same-funder clustering, custody address, relabelling, multiple chains, 429, missing signatures, stale transactions, each a named test.
- Exact classification flow with realistic fixtures and a verifiable provenance chain: `test_provenance_chain_is_checkable_and_tampering_is_caught`, CLI demo in WALLETS_09.md.

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest numpy`).
- Outcome after the last code change: exit 1, `1 failed, 373 passed`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1, untouched).
- `python -m memelab social guard` exit 0 (0 violations).
- Migration 9 applied on a copy of the tracked database: versions 1 to 9 applied, content guard returned no violations, the tracked file hash was unchanged.
- The EVM test still writes `data/reports/<stamp>_BRETT_*.md`; deleted by hand after the run (C-1).
- When running modules together, `MEMELAB_DB` can leak from other test modules; the wallet tests unset it where it matters.

## Things the next phase should know

- Read levels from `wallet_assertions.explain()`. The Phase 01 mirror `social_wallet_attributions` is not written by Phase 09 and can disagree on custody, disputes and signature evidence.
- Activity events are observations in provider units. Any P&L work (next phase) must build on `social_wallet_events` and `social_wallet_event_legs` and must add its own tables, not columns here.
- Helius response fields `slot` and `transactionError` and the 429 behavior were not confirmed against live responses. The first live fetch should be checked against a stored fixture shape.
- The new collector projection reaches scheduled runs only after this branch is merged to main (D-063).
- EVM has no transaction provider (coverage GAP). Move chains have no signature check.
- Only the newest transactions up to the limit are read; no paging, so "first funder" can be wrong for old wallets.
- The signed message text is not stored, only its sha256. The reviewer checks that the account posted it from `evidence_ref`.
- Nothing is scheduled; scheduling belongs to a later phase.

## Blockers and open decisions

- Push: the session's own `git push` gets 403. Working route: Elving's GitHub connection in Composio, Git Data API, fast-forward of the feature branch ref, no force (D-001).
- No permitted live wallet list and no Helius key in session; live wallet status is UNAVAILABLE.
- D-025, D-028, D-023 and D-036 remain open.
- Phase prompts 10 onward not supplied; ROADMAP.md entries are proposals.

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q
```

Expect `1 failed, 373 passed` and `python -m memelab social guard` exit 0.

## Commit and push

Phase 09 is committed on feature/social-intelligence; the commit hash and push result are recorded in a follow-up note below.
