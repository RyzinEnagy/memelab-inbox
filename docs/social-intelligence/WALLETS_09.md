# Phase 09: wallet attribution and wallet activity

Code: `memelab/social/wallet_assertions.py` (attribution records and the "why" view), `wallet_activity.py` (tracked wallets, provider adapters, classifier, ingestion, provenance, funding hypotheses), `sigverify.py` (signature checks), `wallet_cli.py` (commands). Schema: migration 9 (eight tables). Tests: `tests/test_social_wallets.py` (43). Fixtures: `tests/fixtures/social/wallets/` (invented, every file labelled). Versions: `wallet-assertions-v1`, `wallet-activity-v1`, `wallet-classifier-v1`, `sigverify-v1`.

Two separate jobs live here and neither feeds the other without a person in between.

1. Attribution: which social account might control which exact wallet, on what evidence. Real-world identity is a separate question and the answer stored is always UNKNOWN. A level says how well a key is tied to an account, never who the person is.
2. Activity: what a tracked wallet did on chain. Observations only. A transfer, a swap and an LP operation are different events. No price, cost basis, profit or loss exists in these tables (checked by a test that scans every column name).

A wallet can be tracked with no owner. Monitoring never says whose wallet it is.

## Attribution assertions

One row per claim in `social_wallet_assertions`. The claim never changes. Review and status change, and every change is a row in `social_wallet_audit` with who and why.

| Field | Meaning |
|---|---|
| account_entity | the asserted account (registry `acct:...` entity); a trader is reached through its accounts |
| chain, wallet_address | exact, canonical for the chain; a handle or social id is refused |
| evidence_type | OFFICIAL_SELF_DISCLOSURE, SIGNED_MESSAGE, INDEPENDENT_LINKED_SOURCE, THIRD_PARTY_CLAIM, TRANSACTION_PATTERN |
| asserter_entity | who made the statement (the account itself for a self-disclosure) |
| evidence_ref, evidence_sha256 | https URL, `observation:<id>`, `tx:<signature>` or `repo:<path>`; for a signed message the sha256 of the message (the text is not stored) |
| signature_check, signature_detail, signature_verifier | NOT_APPLICABLE, VALID_BOUND, VALID_UNBOUND, INVALID, MALFORMED or UNSUPPORTED, with the reason and verifier version |
| observed_at, valid_from, valid_to | when the lab saw the evidence; the period the claim is said to hold (empty means not stated) |
| confidence | HIGH, MODERATE, LOW, UNKNOWN; cannot exceed what the evidence type supports |
| control_hypothesis | ACCOUNT_CLAIMS_WALLET, ACCOUNT_CONTROLS_KEY (valid bound signature only), RELATED_BY_ACTIVITY (patterns) |
| real_world_identity | UNKNOWN, or SUBJECT_DISCLOSED; no name field exists |
| review_state, reviewed_by, reviewed_at, review_reason | UNREVIEWED, APPROVED, REJECTED |
| status, status_reason, superseded_by | ACTIVE, REVOKED, SUPERSEDED |

What each evidence type can do:

| Evidence | Best it can reach | Why it stops there |
|---|---|---|
| OFFICIAL_SELF_DISCLOSURE | SELF_CLAIMED | the account says so; anyone can say so. Must come from the account itself, otherwise it is a third-party claim |
| SIGNED_MESSAGE | SIGNATURE_VERIFIED (HIGH) | the signature must verify (ed25519 for Solana, EIP-191 for EVM), the message must name one of the account's handles as a whole word, and a person must approve. A valid signature over a message that does not name the account says nothing about the account and never counts. A signature shows control of a key, not who holds it |
| INDEPENDENT_LINKED_SOURCE | CORROBORATED (with a self claim) | the source must neither be nor operate the account (Phase 08 independence rule), and a person must approve. Alone it is only THIRD_PARTY_CLAIMED |
| THIRD_PARTY_CLAIM | THIRD_PARTY_CLAIMED | someone else says so |
| TRANSACTION_PATTERN | HYPOTHESIS_ONLY | funding or timing similarity never establishes control; it cites `tx:` signatures and is never counted |

Levels, in the order `explain()` decides them: UNSUPPORTED_CUSTODY (the wallet is labelled exchange custody, protocol or pool), DISPUTED (another account holds approved verified control of the same wallet), SIGNATURE_VERIFIED, CORROBORATED, SELF_CLAIMED, THIRD_PARTY_CLAIMED, HYPOTHESIS_ONLY, NONE. `linked_status` collapses them for a reader: LINKED (the first two), CLAIMED, NOT_LINKED, DISPUTED.

Other rules, each with a test: nothing reaches SIGNATURE_VERIFIED or CORROBORATED without a named reviewer; a signature that did not verify and bind cannot be approved; a custody, protocol or pool wallet cannot be approved as controlled (correct the label with a source first); a fixture entity only links to fixture entities; revoked, superseded, rejected, unreviewed and out-of-window rows stay visible with the reason they are not counted; two accounts claiming the same wallet with no proof both stay SELF_CLAIMED and each shows the other.

Funding relations are not assertions. See "Funding hypotheses" below.

## The reviewer's view

`social wallet why ACCOUNT CHAIN ADDRESS [--as-of T] [--json]` lists every assertion about the wallet (this account's and other accounts'), what each contributes or why it does not, the level, the confidence, the wallet's label and where the label came from, funding hypotheses and wallets related by funding, and `Real-world identity: UNKNOWN`. Sample (fixture wallets, invented account, run with a fixed clock):

```
Account acct:x:id:1001  wallet solana:GKSw5BerNKY1fb14QzgWXcxMweiKdmtu6oJ3NjxAzRZc
Level: NONE (NOT_LINKED), confidence UNKNOWN
Real-world identity: UNKNOWN. This says nothing about who the person is.
Why: no counted assertion links this account to this wallet

(after: social wallet assert ... --type OFFICIAL_SELF_DISCLOSURE --ref https://example.invalid/post/1 --by elving)
Level: SELF_CLAIMED (CLAIMED), confidence LOW
Why: the account says so; nothing independent confirms it
Awaiting review: assertions 1
  #1 OFFICIAL_SELF_DISCLOSURE by acct:x:id:1001 ref https://example.invalid/post/1 seen 1791846000.0 [UNREVIEWED/ACTIVE] counts as SELF_CLAIM

(second wallet, funded by the same address as the first)
Level: NONE (NOT_LINKED), confidence UNKNOWN
  funding hypothesis 1: funder 77mnaWe2.. members 2, the first funding we saw for these wallets came from this address: a reason to look, not evidence of common control
  related by funding only: GKSw5Ber.. has an assertion from acct:x:id:1001; not counted here
```

## Wallet labels

`social_wallet_labels` (append-only, newest ACTIVE row wins): CUSTODY_EXCHANGE, CUSTODY_OTHER, PROTOCOL, POOL, NO_SPECIAL_LABEL, each with a source reference. A row beats the built-in list the lab already uses for holders (`m09_holder_classification.KNOWN_LABELS`: CEX becomes CUSTODY_EXCHANGE, POOL stays POOL, LOCKER becomes PROTOCOL). Relabelling supersedes the old row and keeps it. NO_SPECIAL_LABEL with a source is how a reviewer corrects a wrong built-in label. Changing a label changes every later `why` answer for that wallet.

## Tracked wallets and safe defaults

`social wallet track add|pause|resume|remove|list`. Defaults:

- a reason and a name are required; the reason says why the wallet is worth watching and claims nothing about its owner;
- at most 25 active wallets;
- 50 transactions per fetch (1 to 100);
- a wallet labelled custody, protocol or pool is refused unless `--allow-custody` is given, because its activity is many people's;
- fetching starts at the time of adding; older transactions are stored as BACKFILL, later ones as LIVE;
- pause and remove stop ingestion but keep the wallet and its events; resume re-activates; every change is in the audit table;
- a paused, removed or untracked wallet in a provider document is skipped and counted, never stored;
- fixture wallets are refused against the tracked database before it is opened.

## Providers and ingestion

Every provider becomes one normalized transaction (`memelab.wallet.tx/1`) before classification. Two inputs exist:

- `memelab.wallet.fetch/1`: a wrapper around bridge result bodies `helius_wallet_tx:<wallet>` (`{"s": status, "body": [...]}`). The new projection `helius_wallet_tx` in `bridge/collector.js` and `memelab/bridge/collector.js` keeps the full signature, slot, failure flag, up to 24 transfers per kind and the true transfer counts (to detect truncation). `Plan.wallet_activity(wallets, limit)` builds the requests. The older `helius_tx` projection cuts signatures to 12 characters, which is not a signature, so a row with one is rejected as INVALID_SIGNATURE rather than stored.
- `memelab.wallet.tx/1`: provider-neutral transactions for any chain. No EVM provider is built. An EVM wallet can be tracked and attributed; until a provider is wired in, its coverage reads "GAP: no transaction provider is configured for this chain", which is not the same as no activity.

Per wallet, one response becomes one `social_wallet_fetches` row, then events:

| Situation | What happens |
|---|---|
| HTTP 429 | fetch RATE_LIMITED with retry-after, no events, connector health RATE_LIMITED, coverage GAP; the other wallets in the document continue; the run is FAILED only when nothing was usable |
| other non-200, or a body that is not a list | fetch ERROR, connector DOWN, coverage GAP |
| missing, truncated or malformed signature | row rejected (MISSING_SIGNATURE or INVALID_SIGNATURE), counted with a row hash, never stored |
| missing block time, or one after the fetch time plus 5 minutes | rejected (MISSING_BLOCK_TIME, FUTURE_BLOCK_TIME) |
| a signature repeated in one response, or an event already stored | counted as already stored; nothing is added or rewritten |
| fetch older than 12 hours at ingestion | events stored with freshness STALE, fetch STALE, connector DEGRADED, coverage PARTIAL with the age |
| more rows than the per-fetch limit | newest rows up to the limit are stored, the rest counted as beyond the limit |
| a fixture document for a real wallet, or the reverse | refused |

Re-ingesting the same file adds nothing (the fetch key includes the file hash).

## Classification

One event per (chain, transaction, monitored wallet). The provider's own type is kept verbatim. Type names for swaps, transfers and liquidity operations come from the Helius transaction-type list (docs read 2026-10-12); the response fields (`signature`, `slot`, `timestamp`, `fee`, `feePayer`, `transactionError`, `nativeTransfers`, `tokenTransfers`) were not re-confirmed in this session, the existing collector already used all but `slot` and `transactionError`.

| Event type | Rule |
|---|---|
| SWAP | provider type SWAP, SWAP_EXACT_OUT or SWAP_WITH_PRICE_IMPACT, and the wallet both sent and received something. `swap_side` BUY (non-quote received, quote sent), SELL (the reverse), TOKEN_TO_TOKEN; quote means wrapped native, a chain stablecoin or the native asset |
| LP_ADD, LP_REMOVE | provider type in the ADD_LIQUIDITY or REMOVE_LIQUIDITY families and the wallet sent (add) or received (remove) something |
| TOKEN_TRANSFER_IN / OUT | provider type TRANSFER and tokens moved in one direction only |
| NATIVE_TRANSFER_IN / OUT | provider type TRANSFER and only the native asset moved |
| FAILED | the provider reports a transaction error; fee only, no legs |
| UNCLASSIFIED | anything else, with the rule that says why: `swap.one_sided`, `transfer.token_out_with_native_in`, `transfer.token_in_with_native_out`, `transfer.mixed_*`, `lp.*_without_*`, `none.no_wallet_legs`, `provider_type_unmapped` |

A token sent away is never a sale. Token out with native coming back under a TRANSFER type could be an over-the-counter trade, a payment or a refund, so it is UNCLASSIFIED. A transfer to an exchange address is a TOKEN_TRANSFER_OUT with `custody_touch` set. Confidence is HIGH, MODERATE when the provider's transfer list was truncated, LOW for UNCLASSIFIED. Each event stores the rule id, classifier version and the inputs the rule saw.

Fields: signature, chain, slot, block time, fee (native units) and fee payer, whether the wallet paid the fee, counterparties with labels, protocol source, legs (asset, contract, direction, amount in provider units, counterparty), observed scope, freshness, provider, fetch id, row hash. Relevant contracts are the leg contracts; `identity` (Phase 05) is not consulted here, so no token is called resolved by this phase.

## Provenance chain

event (signature, row sha256) to fetch (provider, fetched at, HTTP status, file sha256, source file name) to the transaction signature, which anyone can open on the chain explorer (`tx_url`). `social wallet verify EVENT --source FILE` recomputes the file hash and the row hash. Demo: event 3 against the file it came from gives `verified True`; event 2 (ingested from a different file) against the first file gives `False` on the file hash while the row hash still matches. Without `--source` nothing is claimed as verified.

## Funding hypotheses

`social wallet funding` takes each tracked wallet's earliest plain native transfer in (never a swap payout) among stored events as its first funder, and records the funder with everything it first funded as a HYPOTHESIS (`status` is constrained to that value). Only the stored window is seen, so "first" means first seen. `informative` is 0 when the funder is an exchange, custody, protocol or pool address. A funding hypothesis never creates an assertion, never changes a level, and appears in `why` as "related by funding only" with `counts_toward_level: false`.

## Commands

See the header of `memelab/social/wallet_cli.py`. Exit codes: 0 done, 1 refused (message on stderr, nothing written), 2 usage.

## Demo (fixtures, temp database, fixed clock)

```
social wallet track add solana <T1> --reason "fixture demo wallet" --by elving --fixture   -> created, ACTIVE
social wallet track add solana <exchange hot wallet> ...                                    -> exit 1 custody_wallet_not_monitored_by_default
social wallet ingest fx_helius_429.json --fixture   -> PARTIAL: one wallet RATE_LIMITED, the other OK
social wallet ingest fx_helius_ok.json --fixture    -> OK: 13 events stored for the first wallet, others UNTRACKED or already stored
social wallet events --chain solana --wallet <T1>   -> 13 events:
   SWAP/BUY, SWAP/SELL, TOKEN_TRANSFER_OUT x2 (one to an exchange), NATIVE_TRANSFER_IN, LP_ADD, LP_REMOVE, FAILED,
   UNCLASSIFIED x3 (transfer.token_in_with_native_out, swap.one_sided, transfer.token_out_with_native_in), SWAP/BUY (MODERATE, truncated),
   UNCLASSIFIED (provider_type_unmapped)
social wallet verify 3 --source fx_helius_ok.json   -> verified True (file hash and row hash match)
```

## Test map (prompt list to test)

| Prompt item | Test |
|---|---|
| fake ownership claim | `test_fake_ownership_claim_is_disputed_by_verified_control_and_name_matching_links_nothing`, `test_self_disclosure_must_come_from_the_account_and_is_only_a_claim`, `test_signed_message_must_verify_and_name_the_account_to_count` |
| token transfer misclassified as sell | `test_token_transfer_is_never_classified_as_a_sell` |
| wallet funded by the same wallet | `test_funding_by_the_same_wallet_is_a_hypothesis_not_attribution`, `test_transaction_pattern_is_a_hypothesis_and_never_counts` |
| custody address | `test_custody_address_cannot_be_controlled_or_tracked_by_default` |
| relabelling of wallets | `test_relabelling_a_wallet_changes_the_verdict_and_keeps_the_history` |
| multiple chains | `test_same_address_on_two_chains_stays_two_wallets`, `test_evm_wallet_without_a_provider_is_a_coverage_gap_not_no_activity`, `test_evm_signed_message_and_unreviewed_signature_is_only_a_claim` |
| provider 429 | `test_provider_429_for_one_wallet_does_not_stop_the_others`, `test_every_wallet_rate_limited_is_a_failed_run_with_nothing_stored` |
| missing signatures | `test_missing_truncated_and_duplicate_signatures_and_bad_times_are_rejected_not_stored`, `test_the_old_forensics_projection_with_12_character_signatures_is_refused` |
| stale transactions | `test_stale_fetch_is_stored_flagged_and_degrades_the_connector`, backfill scope in `test_event_fields_signature_chain_time_fee_counterparties_source` |
| gate: why linked or not | `test_reviewer_can_read_why_in_plain_english_and_the_audit_trail_is_complete`, `test_revoked_superseded_rejected_and_out_of_window_assertions_stay_visible`, `test_corroboration_needs_a_self_claim_plus_a_reviewed_independent_source` |
| gate: survives reload, not P&L | `test_events_survive_reload_and_repeat_ingestion_adds_nothing`, `test_activity_never_becomes_profit_and_loss` |
| provenance chain | `test_provenance_chain_is_checkable_and_tampering_is_caught` |
| CLI demo | `test_cli_demo_track_ingest_events_verify_and_why`, `test_cli_refuses_fixtures_in_the_tracked_database_and_refusals_write_nothing` |

## Limits

- No live provider call was made and no real wallet or account was used. Live status: UNAVAILABLE (no Helius key in this session, no permitted wallet list supplied).
- Signatures in the fixtures were produced once with random throwaway keys that were discarded; only public keys, messages and signatures are stored. No real key or seed was handled, and the lab has no signing code (`sigverify.py` verifies only).
- A valid signed message proves control of a key at some time. The lab does not check that the message was posted by the account; the reviewer does that from `evidence_ref` before approving.
- The handle binding is a whole-word match of a handle of 3 or more characters. A handle that is a common word will match more easily; the reviewer still decides.
- Only the newest transactions up to the per-fetch limit are read. There is no history paging, so "first funder" can be wrong for an old wallet.
- The attribution mirror `social_wallet_attributions` (Phase 01, written by the Phase 08 registry) is not written by this phase. A later stage must read `wallet_assertions.explain()`, not the mirror, for custody, disputes and signature evidence. `adopt-registry` brings Phase 08 self-disclosures and labels in as assertions (on-chain proof links are listed as not adopted because they carry no re-checkable signature).
- EVM transaction ingestion has no provider; Move chains have no signature check (UNSUPPORTED).
- Nothing is scheduled. Wiring the plan into the daily run belongs to the scheduling phase.
