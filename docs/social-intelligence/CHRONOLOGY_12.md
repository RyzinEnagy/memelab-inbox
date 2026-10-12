# Phase 12: social claims against on-chain chronology

Code: `memelab/social/chrono_core.py` (pure engine, no I/O and no clock), `chrono_store.py` (builds the input from stored rows, stores runs and flags), `chrono_cli.py` (commands). Schema: migration 12 (`social_chrono_runs`, `social_chrono_flags`). Tests: `tests/test_social_chronology.py` (31). Fixtures: `tests/fixtures/social/chrono/` built by `make_chrono.py` (a test checks the files match the script). Versions: `chronology-v1`, `chrono-rules-v1`. Decisions: D-080 to D-084.

For one resolved token and one social source the engine builds one ordered timeline: the source's posts about the token (published, first seen by the lab, removal observed), what the source's associated wallets did with the token (buy, sell, transfer in or out, LP), pool liquidity observations and price and liquidity moves from historical candles. It then says, for every post and trade pair, whether the order is established. It never says who a person is and never claims intent.

## Three clocks

| Clock | What it is | Interval used |
|---|---|---|
| SOURCE_PUBLICATION | the time the platform reports for the post | [t - 1, t + precision + 1); precision 1 s by default, 60 s for a minute display, +/- 3600 s for "x ago" text; capped by the first sighting |
| CHAIN_BLOCK | the block time of the transaction (validator estimate) | [t - 2, t + 3); a slot without a block time is bounded by the block times of neighbouring slots in the input |
| COLLECTION | when the lab's collector saw or re-checked the post | +/- 5 s; an upper bound on publication, and the earliest moment the lab could have known |
| CANDLE | a historical candle from a named source | [start, end) |

They differ for real reasons. A post can be published at 02:00 and reach the collector at 05:00 (late API delivery or a late run): the order uses 02:00, and the report says when the lab first saw it. A page that shows only minutes cannot be ordered against a swap in the same minute. A post with no publication time is only "no later than" its first sighting, so a trade after that sighting is ordered and a trade before it is not. Two entries are ordered only when one interval ends before the other starts; everything else is INDETERMINATE (D-081). Entries whose intervals overlap share an order group, marked `~` in the report.

## Joins and identity

Chain and contract are checked on every join: posts (Phase 05 resolved mention only), wallets, every event leg, pool rows and candles. A ticker or name never joins. A post resolved to another contract with the same symbol is TOKEN_MISMATCH; a ticker-only mention is TOKEN_UNRESOLVED; another chain is CHAIN_MISMATCH. An event whose legs move another token or the native coin is UNRELATED_ASSET. Every rejection is listed with its reason, counted in `join_checks`, and raises an IDENTITY_JOIN_REJECTED data-quality flag.

## Which wallets count (D-082)

| Phase 09 level | Class here | Used for patterns |
|---|---|---|
| SIGNATURE_VERIFIED, CORROBORATED | LINKED | yes, INFERENCE |
| SELF_CLAIMED, nobody else claims it | CLAIMED | yes, HEURISTIC |
| SELF_CLAIMED, another account also claims it | CONTESTED | no |
| DISPUTED | DISPUTED | no |
| THIRD_PARTY_CLAIMED, HYPOTHESIS_ONLY, NONE | UNCERTAIN | no |
| UNSUPPORTED_CUSTODY or labelled custody, protocol or pool | EXCLUDED_CUSTODY | no, and not on the timeline |

Not-attributed wallets stay visible as "a wallet with an unverified association" and get a data-quality flag. Every wallet carries `real_world_identity: UNKNOWN`.

Event actions: a SWAP is BUY or SELL; a token transfer out is TRANSFER_OUT ("not a sale"); a transfer out to a custody-labelled address is TRANSFER_TO_CUSTODY ("a sale there is not observable"); a transfer between two associated wallets in one transaction is INTERNAL_TRANSFER; failed transactions are dropped.

## Observed patterns

| Pattern | When | Bucket |
|---|---|---|
| TRADE_BEFORE_TALK | an associated buy or sell certainly before the post, within 24 h | INFERENCE (LINKED) / HEURISTIC (CLAIMED) |
| TALK_BEFORE_TRADE | certainly after the post, within 24 h | same |
| ORDER_INDETERMINATE | within 24 h and the intervals overlap | UNKNOWN |
| TALK_WITHOUT_OBSERVED_TRADE | a post with no associated trade within 24 h; carries monitoring coverage NO_ATTRIBUTED_WALLET, PROVIDER_UNAVAILABLE, NONE, PARTIAL or FULL | UNKNOWN |
| TRADE_WITHOUT_OBSERVED_TALK | a trade with no post within 24 h; says whether the source's posts were enumerated | UNKNOWN |
| POTENTIAL_DISTRIBUTION_DURING_PROMOTION | an associated sale after a bullish post and within 24 h of it; INDETERMINATE when the sale may precede the post | INFERENCE if certain and LINKED, otherwise HEURISTIC |

Absence of a monitored trade is not evidence that none occurred, and every "without observed" pattern says what was and was not covered (D-084). A repost is the source's act at the repost time and is marked "not the source's own words". A post that later returned DELETED or NOT_FOUND still counts as said; the timeline adds POST_REMOVAL_OBSERVED bracketed by the last good and the first failed sighting, and the observation record and content hash are the remaining evidence.

## Flags for later pipelines

`social_chrono_flags`, one row per flag per run, read with `chrono_store.current_flags(con, chain=..., contract=..., category=...)` (newest run per token and source; fixtures hidden unless asked). Fields: flag, category, bucket, rule id, order status, attribution class, time, evidence references, note.

- CORROBORATION: DISCLOSED_POSITION_CONSISTENT (the post says the author holds, and an associated wallet bought before it).
- RISK: TRADE_BEFORE_TALK (buy before a bullish post that disclosed no position), POTENTIAL_DISTRIBUTION_DURING_PROMOTION.
- CONTEXT: TALK_BEFORE_TRADE, TRADE_BEFORE_TALK in other combinations, TALK_WITHOUT_OBSERVED_TRADE, TRADE_WITHOUT_OBSERVED_TALK.
- DATA_QUALITY: ORDER_INDETERMINATE, ATTRIBUTION_UNCERTAIN, ATTRIBUTION_CONTESTED, ATTRIBUTION_DISPUTED, CUSTODY_WALLET_EXCLUDED, IDENTITY_JOIN_REJECTED, DELAYED_COLLECTION, CHAIN_TIME_MISSING, MISSING_PRICE_HISTORY, STALE_WALLET_DATA, STALE_MARKET_DATA, STALE_POST_CHECK, PUBLISHED_AFTER_FIRST_SEEN, PUBLISHED_TIME_CONFLICT.

The schema refuses a RISK flag that is FACT or UNKNOWN, a RISK flag without a LINKED or CLAIMED wallet, a FACT flag outside DATA_QUALITY and a non-data-quality flag without evidence (D-083). Generated text is checked against a list of accusatory words, matched as whole words; a hit refuses the result.

## Evidence summary

Three lists, each line with links to the original evidence: post URL, item key and observation id; explorer URL, `tx:` signature and wallet event id; assertion id and the assertion's evidence reference; candle source. Fact: what was published, seen, removed, traded and how the price moved. Inference: wallet association at its level and ordered patterns. Not established: unordered pairs, unattributed wallets, trades the coverage could not see, and always the real-world controller of any wallet, intent, other wallets and price causation.

## Configuration, fallbacks, staleness

`chrono_core.DEFAULT_POLICY` (part of the input hash): window 72 h either side of the posts (or an explicit `window`, always clamped to `as_of`), pairing 24 h, promotion 24 h, tolerances, delayed-collection 600 s, stale thresholds (wallet and market 6 h, post re-check 24 h), zigzag thresholds 20% for price and 25% for liquidity, and `market_source_preference` (first usable source wins, `fallback_used` says when it did not). A live quote is never used as a past price. A provider marked UNAVAILABLE is reported as such. Duplicate post rows, sightings and wallet events are merged and counted.

## Commands

```
python -m memelab social chrono run --input FILE [--policy JSON] [--save --db PATH] [--json]
python -m memelab social chrono run --token CHAIN:CONTRACT --source ACCOUNT_OR_TRADER --as-of T [--window-from T --window-to T] [--annotations FILE] [--no-save]
python -m memelab social chrono show RUN | verify RUN | flags [--token ..] [--category ..] [--include-fixtures] | status
```

`--annotations` may set `posts_enumerated` and `providers`, which earlier phases do not store. Fixtures are never written to the tracked database.

## Fixture walkthrough: confident order (`confident.json`)

```
INVENTED FIXTURE DATA: no real post, wallet, token or person.
Chronology for solana:S5vznK6GJNtHJWH66MPdNBLHGx35G7HyS5vznK6GJNtH (LABCAT, symbol shown for reading only)
Source: FIXTURE source A (invented)   evaluated as of 2026-10-12 08:00:00Z   window 2026-10-08 01:59:59Z to 2026-10-12 08:00:00Z
Order between posts and trades: CONFIDENT

Clocks: SOURCE_PUBLICATION is the platform's time for a post; CHAIN_BLOCK is the block time of a transaction; COLLECTION is when the lab saw the post. Entries in the same group overlap in time and their order is not established.

Timeline
   1 g1    2026-10-11 00:00:00Z       CHAIN_BLOCK         ut3Tma..zF3E (a wallet linked to the source) bought 1,000,000 of the token in tx fyYNUQ..i8Mn.
   2 g2    2026-10-11 02:00:00Z       SOURCE_PUBLICATION  The source posted about the token in x:1900000000000000101, stance LONG (platform timestamp, 1 s precision).
   3 g3    2026-10-11 02:00:30Z       COLLECTION          The lab first saw post x:1900000000000000101 (collector clock).
   4 g4    2026-10-11 02:10:00Z       CHAIN_BLOCK         5xX8F4..ipwA (a wallet with an unverified association) bought 50,000 of the token in tx pMRRu2..kp2C.
   5 g5  ~ 2026-10-11 05:00:00Z       CANDLE              Price rose 60% between 2026-10-11 02:00:00Z and 2026-10-11 05:00:00Z (candle closes, fixture-candles (INVENTED)).
   6 g5  ~ 2026-10-11 05:00:00Z       CHAIN_BLOCK         ut3Tma..zF3E (a wallet linked to the source) sold 400,000 of the token in tx oWNTxW..PGwK.
   7 g6  ~ 2026-10-11 06:00:00Z       CHAIN_BLOCK         Liquidity was removed from pool 5Au11f..1a49 (liquidity 30,000 USD as reported).
   8 g6  ~ 2026-10-11 07:00:00Z       CANDLE              Pool liquidity fell 40% to 30,000 USD between 2026-10-11 06:00:00Z and 2026-10-11 07:00:00Z (fixture-candles (INVENTED)).
   9 g7    2026-10-11 09:00:00Z       CANDLE              Price fell 31% between 2026-10-11 05:00:00Z and 2026-10-11 09:00:00Z (candle closes, fixture-candles (INVENTED)).

Observed patterns
  TRADE_BEFORE_TALK [INFERENCE, order CONFIDENT] post x:1900000000000000101 trade fyYNUQ..i8Mn
  TALK_BEFORE_TRADE [INFERENCE, order CONFIDENT] post x:1900000000000000101 trade oWNTxW..PGwK
  POTENTIAL_DISTRIBUTION_DURING_PROMOTION [INFERENCE, order CONFIDENT] post x:1900000000000000101 trade oWNTxW..PGwK: A wallet associated with the source sold after its bullish post and while the post was recent. This is an observed sequence. Intent, the source's total holding and any coordination are not established.
```

## Fixture walkthrough: indeterminate order (`indeterminate.json`)

```
INVENTED FIXTURE DATA: no real post, wallet, token or person.
Chronology for solana:S5vznK6GJNtHJWH66MPdNBLHGx35G7HyS5vznK6GJNtH (LABCAT, symbol shown for reading only)
Source: FIXTURE source A (invented)   evaluated as of 2026-10-12 08:00:00Z   window 2026-10-08 01:59:59Z to 2026-10-12 08:00:00Z
Order between posts and trades: INDETERMINATE

Clocks: SOURCE_PUBLICATION is the platform's time for a post; CHAIN_BLOCK is the block time of a transaction; COLLECTION is when the lab saw the post. Entries in the same group overlap in time and their order is not established.

Timeline
   1 g1  ~ no later than 2026-10-11 03:00:05Z SOURCE_PUBLICATION  The source posted about the token in x:1900000000000000202, stance LONG (publication time unknown; published no later than the lab's first sighting).
   2 g1  ~ 2026-10-11 02:00:00Z       SOURCE_PUBLICATION  The source posted about the token in x:1900000000000000201, stance LONG (platform timestamp, 60 s precision).
   3 g1  ~ 2026-10-11 02:00:25Z       CHAIN_BLOCK         ut3Tma..zF3E (a wallet linked to the source) bought 800,000 of the token in tx m9WBmK..aDzf.
   4 g1  ~ 2026-10-11 02:00:50Z       CHAIN_BLOCK         ut3Tma..zF3E (a wallet linked to the source) sold 300,000 of the token in tx fk1o2B..ABsA.
   5 g1  ~ 2026-10-11 02:01:30Z       COLLECTION          The lab first saw post x:1900000000000000201 (collector clock).
   6 g1  ~ 2026-10-11 03:00:00Z       COLLECTION          The lab first saw post x:1900000000000000202 (collector clock).

Observed patterns
  ORDER_INDETERMINATE [UNKNOWN, order INDETERMINATE] post x:1900000000000000201 trade m9WBmK..aDzf
  ORDER_INDETERMINATE [UNKNOWN, order INDETERMINATE] post x:1900000000000000201 trade fk1o2B..ABsA
  ORDER_INDETERMINATE [UNKNOWN, order INDETERMINATE] post x:1900000000000000202 trade m9WBmK..aDzf
  ORDER_INDETERMINATE [UNKNOWN, order INDETERMINATE] post x:1900000000000000202 trade fk1o2B..ABsA
  POTENTIAL_DISTRIBUTION_DURING_PROMOTION [HEURISTIC, order INDETERMINATE] post x:1900000000000000201 trade fk1o2B..ABsA: A wallet associated with the source sold close to its bullish post; whether the sale came after the post is not established. This is an observed sequence. Intent, the source's total holding and any coordination are not established.
```

The full printed reports, with the fact, inference and not-established lists and their links, come from the two commands above.

## Limits

- No live data was used. No live post, wallet fetch or candle source is wired in for this phase; real runs need Phase 09 events from a Helius fetch and Phase 11 candles.
- Monitoring coverage for stored wallets runs from `watch_since` to the last good fetch. A fetch that hit its transaction cap can hide older transactions, so FULL can overstate coverage.
- Whether the collector enumerated all of the source's posts is not stored by earlier phases; it defaults to false unless supplied.
- Amounts are provider units. The source's total holding is not known, so no sale is described as a share of a position.
- One token and one source per run. Cross-source coordination belongs to C-12.
