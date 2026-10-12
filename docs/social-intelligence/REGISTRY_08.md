# Phase 08: source and trader registry

Code: `memelab/social/registry.py` (model and rules), `registry_import.py` (file import), `registry_cli.py` (commands). Schema: migration 8 (nine `social_registry_*` tables). Tests: `tests/test_social_registry.py` (51). Fixtures: `tests/fixtures/social/registry/` (invented, every file labelled). Version string `registry-v1`.

The registry records which accounts, wallets, organizations and lists exist, where each was seen, how sure the lab is that two of them belong together, and what a person decided. It does not rank anyone, call anyone a best trader, or decide that a wallet belongs to an account. A leaderboard row is a claim by a list. It starts as a candidate and stays one until a person reviews it.

## Identities

Seven things from the prompt map onto five entity kinds plus link types.

| Prompt identity | Stored as |
|---|---|
| Social account | entity SOCIAL_ACCOUNT, keyed by provider id when known, else platform and handle (Phase 01 `social_accounts`) |
| Wallet | entity OBSERVED_WALLET, keyed by chain and normalized address |
| Source organization | entity SOURCE_ORGANIZATION (a board, a desk, a publisher) |
| Social network | entity SOCIAL_NETWORK, linked by MEMBER_OF_NETWORK |
| Leaderboard candidate | entity LEADERBOARD_CANDIDATE, one per source and identifier, created by import |
| Claimed or verified link | links: WALLET_SELF_DISCLOSED, WALLET_THIRD_PARTY_LABEL, WALLET_ON_CHAIN_PROOF, WALLET_DISPUTED |
| Same operator, organization operation | links: SAME_OPERATOR, OPERATED_BY_ORG, plus OBSERVED_AS and LISTED_BY for import provenance |

Entities are never merged. A group of accounts that belong to one operator exists only as the set of entities joined by reviewed SAME_OPERATOR links (`identity_cluster`).

## Rules

- Names are not evidence. Identical screen names or display names stay separate entities. A link whose basis is a name is refused. Both accounts show a warning ("same screen name as ...").
- A handle rename on a known provider id keeps one entity and adds to its handle history. A rename without a provider id looks like a new account until a person links the two.
- A link is a claim with a basis, a time window, an evidence reference and a review state. Only reviewed links count. Retracting a link adds a RETRACTED row; nothing is deleted.
- Wallet attribution level is computed, not stored by hand: NONE, THIRD_PARTY_LABELED, SELF_CLAIMED, CORROBORATED, DISPUTED. A self claim stays SELF_CLAIMED until an independent reviewed label or a reviewed on-chain proof exists. A label from an organization that operates the account is not independent. A dispute overrides. Windows (`valid_from`, `valid_to`, `as_of`) are respected.
- `social_wallet_attributions` (Phase 01) is kept in step by recomputing the level after every change, so retracting a dispute restores the earlier level.
- Evidence freshness: a capture older than the source's max age (or undated) is stale. Approval needs fresh evidence or a written `accept_stale_reason`, which is stored and shown.
- Categories (INFORMATION_ORIGINATOR, AMPLIFIER, ANALYTICAL_SOURCE, PROFITABLE_TRADING_CLAIMANT, VERIFIED_WALLET_CANDIDATE, PROMOTER_HIGH_CONFLICT, ...) are independent, append-only and evidence-gated. A profit claim says nothing about whether the person writes useful commentary.
- No text with superlatives ("best trader", "top trader", "#1 trader", "guaranteed", "most profitable", "verified profitable") is accepted in any reason, basis, note or focus field. Search orders by label and never by rank or score. No table has a rank, score or grade column of the lab's own.
- Duplicate rankings and duplicate identifiers in a list are flagged and kept as stated.
- Fixtures: stored with a label, cannot be watched, cannot be linked to real entities, and fixture imports and `import-catalyst` are refused against the tracked database before it is opened.
- Suspension: `account-status SUSPENDED` pauses any watch, keeps all history and links, and blocks a new WATCH until the status changes.

## Import format

JSON `memelab.social.registry.import/1` (or CSV plus a `--meta` JSON file). Top level keys: `schema`, `source` (source_key, kind LEADERBOARD or ANALYST_LIST, organization, url, access_mode file|api|fixture, permitted_basis, is_fixture, fixture_label, max_age_seconds), `capture` (captured_at, url, period), `rows` (rank, wallet, handle, display_name, metrics, row_url). Unknown keys refuse the file. Per-row problems reject only that row (INVALID_WALLET, INVALID_HANDLE, UNSUPPORTED_PLATFORM, INVALID_METRIC, INVALID_RANK, BLOCKED_CONTENT_KEY, UNKNOWN_ROW_KEY, NO_IDENTIFIER, INVALID_URL). Whole-file refusals write nothing (BAD_SCHEMA, NOT_JSON, FILE_TOO_LARGE, TOO_MANY_ROWS, UNKNOWN_KEY, BAD_SOURCE, BAD_CAPTURE, CAPTURED_IN_FUTURE, UNLABELLED_FIXTURE). Import is all or nothing, idempotent by file hash, and `--dry-run` writes nothing. Import never approves, categorizes, ranks or marks ownership.

## Commands

`python -m memelab social registry <action>`: import, import-catalyst, add (account, wallet, org, network), evidence, link, review-link, retract-link, list, show, approve, reject, update, category, account-status, check-listing, attribution, discover, status. Exit 0 ok, 1 refused (JSON error on stderr), 2 usage. `list` filters: `--q`, `--kind`, `--state`, `--watch`, `--category`, `--platform`, `--attribution`, `--stale`, `--suspended`, `--fixture` or `--real`, `--limit`, `--json`.

## Sample: candidate, evidence, reviewed record

Temp database, `--now 1791849600`, fixture list. Every command exit 0.

```
$ social registry import tests/fixtures/social/registry/leaderboard_fresh.json
status IMPORTED, rows_total 8, rows_accepted 6, rows_rejected 2 (INVALID_WALLET row 5, BLOCKED_CONTENT_KEY row 6)
row_flags: duplicate_identifier 1, duplicate_rank 2, no_wallet 2, platform_link_missing 2
entities_new 11, links_new 12, never_done: approve, assign category, mark wallet as owned, rank

$ social registry list --q demo_trader_a --kind SOCIAL_ACCOUNT
1 entities (ordered by label; no ranking, no scores)
acct:x:id:9001001 | SOCIAL_ACCOUNT | CANDIDATE/NONE | Demo Trader A | wallet THIRD_PARTY_LABELED | categories - | flags FIXTURE

$ social registry show acct:x:id:9001001
Demo Trader A (SOCIAL_ACCOUNT, acct:x:id:9001001)
  FIXTURE, demonstration data only: invented demonstration list; no real people, wallets or figures
  record: CANDIDATE, watch NONE
  wallet wallet:solana:FCvX...: THIRD_PARTY_LABELED, confidence LOW (label_unreviewed; third_party_label_only)
  evidence: 2 rows (2 current, 0 stale, 0 undated)

$ social registry approve acct:x:id:9001001 --reviewer elving --reason demo_of_the_approve_control
review_state APPROVED, watch_status NONE, evidence fresh 2
```

A reason such as "best trader on the board" is refused (exit 1). `update --watch WATCH` on this fixture is refused (exit 1).

## Test map

Migration 8 up and down; candidates only; idempotent import and dry run; twelve whole-file refusals; row rejections; CSV; undated evidence; identical screen names; name basis refused; handle rename; suspension; self claim versus corroboration ladder; downstream table follows the level; timespans; leaderboard plus self claim; multiple handles and wallets; link validation; networks and organizations; stale leaderboard; duplicate rankings; missing platform link; sources without wallets; categories; listing claim review; approve, reject, update log; no superlatives; search; fixture controls; tracked-database refusal; catalyst list import; narrative discovery; later-stage read; no network imports; content guard; three CLI subprocess tests including the demo above.

## Limits

- No live list exists. No permitted live source was supplied, so every capture here is a fixture. Live status: UNAVAILABLE.
- `import-catalyst` loads the repo's research list as undated, unreviewed candidates. Approval of those needs `accept_stale_reason`.
- `discover` proposes INFORMATION_ORIGINATOR and AMPLIFIER categories from a stored Phase 07 snapshot. Proposals are PROPOSED until a person confirms. With fixture-mode observations the derived entities are fixture-labelled.
- The superlative filter is a regex. It will miss novel phrasing. It is a guard, not proof.
- Nothing here scores or ranks traders. Outcome tracking is a later phase.
