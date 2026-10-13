# Phase 10: wallet performance accounting

Code: `memelab/social/perf_core.py` (engine, no I/O), `perf_analysis.py` (positions, metrics, checks, score gate), `perf_store.py` (Phase 09 events to a ledger, stored runs), `perf_cli.py`. Migration 10 adds five tables, all `social_perf_*`. Tests: `tests/test_social_performance.py` (57). Fixtures: `tests/fixtures/social/perf/` (invented, labelled). Engine version `wallet-performance-v1`.

This is wallet-level accounting. It says nothing about the person behind a wallet. Every result carries `person_level_claim: false` and a statement of what is outside the data (other wallets, exchange flows, earlier history, off-chain activity). No leaderboard or provider figure is an input.

## What goes in

A ledger document (`memelab.perf.ledger/1`): wallets, asset roles and decimals, entries (SWAP, TRANSFER_IN, TRANSFER_OUT, LP_ADD, LP_REMOVE, FAILED, UNCLASSIFIED), supplied price observations, history coverage, optional airdrop annotations and a declared wallet group. `perf_store.ledger_from_events` builds one from stored Phase 09 events without changing them. Prices are supplied (`social perf prices import`), never fetched, and are labelled estimates. Amounts use exact decimals (precision 50). Outputs are strings rounded half-even to 12 places.

## Rules

Buys and sells. A swap that pays the native coin or a stablecoin for a token is a buy; the lot costs the quote paid, valued in USD at the nearest price observation within 900 s. The wrapped-native mint is an alias of the native coin. A stablecoin uses an observed price, else an assumed 1.00 labelled PEG_ASSUMED (policy `assume_stable_peg`). A swap of token for quote is a sell. Token for token is a disposal and a new lot at the value given up.

Transfers. A transfer in is never a buy. It makes a lot of unknown basis (UNKNOWN_EXTERNAL). A sale from it shows proceeds and no gain or loss. If an analyst marks the transaction signature AIRDROP (signature, reason required) the lot has zero basis by convention and its proceeds are reported apart from trading performance. A transfer out leaves the books holding its basis in an off-book pool. If the same counterparty sends the same token back, the original basis comes back (return matching). Anything else that comes in has unknown basis.

Wallet to wallet. Between wallets of a declared group (analyst's choice, a reason is required, never an ownership claim), a transfer is matched by transaction signature. Basis moves and no profit is made. If fewer units arrive than left (fee-on-transfer), the missing units are a TRANSFER_TAX slice carrying their share of basis. Unmatched signatures are not matched by guessing.

Liquidity. LP add and remove are capital moves, not trades. Basis is pooled per pool key and restored per token on removal. Extra units on removal are an LP_EXCESS lot of unknown basis. LP tokens are not valued. Fees earned and impermanent loss are not computed.

Missing history. A sale larger than the inventory the ledger can explain creates an UNKNOWN_PRIOR_HISTORY opening lot at the front of the queue and marks the token contaminated from that time. Positions touching a contaminated token are out of the sample. A sale more than 100 times the known inventory is also flagged UNIT_ERROR_SUSPECTED. A swap price more than 50 times off an observed price is flagged IMPLIED_PRICE_MISMATCH.

Decimals. A leg may carry raw and decimals. The human amount is raw / 10^decimals. A decimals value that disagrees with the asset record is rejected as DECIMALS_CONFLICT; an amount that disagrees with raw/decimals is rejected as AMOUNT_RAW_MISMATCH. Rejected entries are counted with the reason, and the tokens they touched are contaminated.

Fees. Network fees are not added to lot cost. They are listed, valued at the native price at the fee time, attached to the position where they belong, and subtracted in net P&L. A fee the wallet did not pay is not counted. A missing fee amount is unknown and keeps the position out of the sample.

Position. First swap buy of a token to flat. Dust below 0.01% of the bought quantity is written off at closing. In the sample only if CLOSED, basis known, proceeds known, fees known and no contamination.

## Lot convention

FIFO is primary. Average cost (AVCO, pro rata across all open lots) is always computed as a sensitivity. A position that closes with only trading lots has the same total under every convention; the convention only moves realized P&L between partly closed positions. A sensitivity is material when it moves realized P&L by more than 5% of the primary figure or flips its sign. Other sensitivities: stablecoins forced to 1.00, and no return matching.

## Separate lines

Realized (before and after known fees), unrealized at the last supplied mark (stale after 24 h), and estimated liquidation proceeds are separate figures and are not added together. Liquidation comes from a supplied sell quote: EXEC_QUOTE (scaled down pro rata, a lower bound), NO_ROUTE (zero, UNEXITABLE), IMPACT_CURVE (read through the lab's own `parse_quote_side` and `interp_impact` from `modules/_common.py`), or UNKNOWN when there is no quote or it is older than 1 h. A missing quote is never zero. The gap between mark and executable value is reported per asset and in total.

## Metrics, with definitions

Trade count: closed, fully known positions (swaps are counted apart). Win: net P&L after known fees strictly above zero. Return: net P&L / cost. Win rate has a Wilson 95% interval. Median return per position. Aggregate return: total net / total cost. Profit share from the biggest winner: biggest net / sum of positive nets. Return excluding the biggest winner: (sum of net minus biggest) / (sum of cost minus its cost). Drawdown: computed only when at least 20 equity points are fully valued and they cover at least 80% of all points; it is sampled at event times, so it is a lower bound. Equity never includes deposits or withdrawals.

## Score gate

A wallet is scored only when all hold: at least 20 closed fully known positions, a sample spanning at least 7 days, at least 0.8 of disposed value from lots of known basis, at least 0.9 of swaps priced, at most 0.2 of fees unknown, at most 0.1 of entries unclassified, reconciliation passed, reconstruction not NOT_POSSIBLE. Otherwise the status is INSUFFICIENT_DATA with each reason and no number. The 20 and 50 floors come from `m28_statistical_analysis` (N_INSUFFICIENT, N_LOW_CONF). A scored wallet is LOW_CONFIDENCE when n < 50, history coverage is UNKNOWN or TRUNCATED, or one position produced more than half the profit. The score is the return excluding the biggest winner. `rank_wallets` ranks only scored, reconciled wallets and lists the rest with reasons. A refusal is not a bad score.

## Coverage and status

History coverage from stored fetches: TRUNCATED if any usable fetch returned as many rows as the per-fetch limit, PLAUSIBLY_COMPLETE if all returned fewer (the limit actually requested is not stored, so this is not proof), UNKNOWN if no usable fetch. A RATE_LIMITED or ERROR fetch is a gap. Reconstruction status: COMPLETE, PARTIAL (reasons listed), or NOT_POSSIBLE (no swap accounted for, or a reconciliation check failed). Wording when not complete: "Comprehensive reconstruction cannot be achieved: ...".

## Reconciliation checks

Run on every result: lot_quantity_conservation, asset_quantity_conservation, off_book_conservation, basis_conservation, proceeds_conservation, position_total_equals_slice_total, fee_partition, entries_accounted, no_entries_after_as_of, deterministic_recomputation (the analysis runs twice and the result hashes must match). Warnings: decimals_consistent, inventory_explained_by_ledger, no_rejected_entries, no_suspect_units. A FAIL makes the run NOT_POSSIBLE and refuses the score (tested with a deliberately broken engine). Runs are stored with their input and result; `social perf verify` recomputes from the stored input and compares hashes, and a stored result edited afterwards is detected.

## Provider comparison

`compare_provider_estimates` lines up a provider's stated figures against the ledger, labelled "PROVIDER ESTIMATE, NOT VALIDATED, NOT USED IN THE LEDGER". It never changes the result or its hash. A match does not validate the ledger; the reconciliation checks do.

## Hand check of ledger_main.json

SOL is $100 up to entry e10 and $120 from e11. Fee per swap 0.0001 SOL.

| Position | Entries | Cost USD | Proceeds USD | Gross | Fees | Net | Return |
|---|---|---|---|---|---|---|---|
| TOKA | e01-e04 | 1000 + 2000 = 3000 | 4500 + 500 = 5000 | 2000 | 0.04 | 1999.96 | 0.666653 |
| TOKB | e05-e06 | 500 | 100 | -400 | 0.02 | -400.02 | -0.80004 |
| TOKC | e07-e08 | 1000 USDC at 0.88 = 880 | 1000 USDC at 1.00 = 1000 | 120 | 0.02 | 119.98 | 0.136341 |

TOKA under FIFO: e03 sells 1500 units, which is lot 1 (1000 units, cost 1000) plus 500 units of lot 2 (cost 1000), proceeds 45 SOL = 4500, so +2500. e04 sells the other 500 units (cost 1000) for 5 SOL = 500, so -500. Total +2000. Native units: cost 30 + 5 = 35 SOL, proceeds 50 + 1 = 51 SOL, +16 (TOKC is paid in a stablecoin and is not in the native view).

Realized before fees 2000 - 400 + 120 = 1720. Fees: ten swaps e01 to e10 at 0.0001 SOL x $100 = 0.10; e12, e14, e15 and e19 at 0.0001, e16 at 0.00005 and the failed e18 at 0.0002, all at $120: 0.00065 x 120 = 0.078. Total 0.178 (e11, e13, e17 are transfers in the wallet did not pay for). Positions carry 0.08 of that on closed positions and 0.02 on the two open ones. After known fees 1719.822.

Metrics: n = 3, wins 2, win rate 2/3. Median of (0.666653, -0.80004, 0.136341) is 0.136341. Aggregate 1719.92 / 4380 = 0.392676. Profit share 1999.96 / (1999.96 + 119.98) = 0.943404. Ex-best (1719.92 - 1999.96) / (4380 - 3000) = -280.04 / 1380 = -0.202928.

Not trading P&L: TOKX arrives by transfer (e11) and sells for 2 SOL at $120 = 240, unknown basis. TOKY arrives by annotated airdrop (e13) and sells for 1 SOL = 120, airdrop proceeds. TOKZ (e15) is sold with no visible buy, 3 SOL = 360, opening lot from missing history. Unknown-basis proceeds 240 + 360 = 600.

Open: TOKR (10 SOL = $1000 for 5,000,000 units) marks at 0.0002 = 1000, quote NO_ROUTE, so liquidation 0. TOKE (10 WSOL = $1000 for 200,000 units, 50,000 sent to W2x and back, basis restored) marks at 0.01 = 2000, quote 200,000 units for $1700. Unrealized at mark: 0 + 1000 = 1000. If sold now: (0 - 1000) + (1700 - 1000) = -300. Gap 1300.

Sensitivities: AVCO delta 0 (all three positions close flat). Stablecoins at 1.00: TOKC cost and proceeds both 1000, so -120, material. No return matching: TOKE is open and the delta is 0.

Reconciliation: 13 pass, 1 warn (inventory_explained_by_ledger, because of TOKZ). Drawdown: 3 of 19 points fully valued, so INSUFFICIENT_DATA. Score: INSUFFICIENT_DATA (n = 3 below 20, span 2.0 days below 7).

The other two ledgers (`make_scored.py` generates them) have these hand numbers. ledger_scored_outlier: 24 positions, win rate 0.5, median -0.05, aggregate 0.775, profit share 0.900901, ex-best -0.060870, SCORED with LOW_CONFIDENCE, drawdown INSUFFICIENT_DATA. ledger_scored_clean: 50 positions, win rate 0.6, median 0.1, aggregate 0.02, profit share 0.033333, ex-best 0.018367, SCORED with confidence OK, drawdown computed at 200 USD (peak capital 100).

Small unit cases are hand-checked in the tests themselves: partly closed FIFO 2500 vs AVCO 2250; wash round trip +500; fee-on-transfer +200; liquidity 818.18 known plus 181.82 unknown-basis proceeds; stablecoin peg +120 vs 0 at par; impact curve 950 at size 1000 with 5% impact and 99 at size 100 with 1%.

Phase 09 integration (fx_helius_ok.json, SOL at $100 at every event): buy X for 1.5 SOL = $150, sell 100000 of 250000 for 0.9 SOL = $90, cost 60, realized +30; 70000 X sent to R1 and a CEX, off-book; LP deposit and withdrawal with 1000 excess; 12 wallet-paid fees of 0.0005 SOL = $0.006; 4 of 13 events unclassified; history PLAUSIBLY_COMPLETE; score refused.

## Demo: score refusal

```
$ python -m memelab social perf run --ledger tests/fixtures/social/perf/ledger_main.json
Reconstruction: PARTIAL. Comprehensive reconstruction cannot be achieved: history coverage is UNKNOWN: ...
Reconciled: True (13 pass, 1 warn, 0 fail)
Realized (trading lots, known basis and proceeds, before fees): 1720 USD
Known fees: 0.178 USD (0 fee(s) unknown, 0 unpriced)
Unrealized, marked at last supplied price: 1000 USD on 2 of 2 open positions of known basis
If sold now per supplied quotes (lower bound): -300 USD on 2 of 2; the mark overstates the executable value by 1300 USD where both are known
Drawdown: INSUFFICIENT_DATA (3 fully valued points of 19 (need at least 20 and 0.8 of all points))
Score: INSUFFICIENT_DATA
  refused because: sample of 3 closed, fully known position(s) is below the minimum of 20
  refused because: the sample spans 2.0 days, below the minimum of 7
```

`social perf rank --ledger clean --ledger outlier --ledger main` ranks the clean wallet (0.018367, OK) first and the outlier wallet (-0.060870, LOW_CONFIDENCE) second, and lists the main wallet as refused with the two reasons above.

## Commands

```
python -m memelab social perf run --ledger FILE [--save --db DB] [--policy JSON|FILE] [--json]
python -m memelab social perf run --chain solana --wallet ADDR [--wallet ADDR2 --group-reason TEXT] [--no-save]
python -m memelab social perf prices import FILE --chain solana [--fixture]
python -m memelab social perf meta set CHAIN ASSET --kind TOKEN --source TEXT [--decimals N]
python -m memelab social perf show|verify RUN
python -m memelab social perf rank [--ledger FILE ...]
python -m memelab social perf compare (--run N | --ledger FILE) --provider FILE
python -m memelab social perf status
```

A refused score exits 0 (it is an answer). Fixtures are never written to the tracked database.

## Limits

Prices and quotes must be supplied; no price source is wired in, so a real wallet needs imported prices before USD figures exist (native-unit figures need none). Decimals cannot be re-verified from stored Phase 09 events, which hold decimal amounts only. Only the newest transactions up to the fetch limit are read, so history is rarely shown complete. EVM has no transaction provider. Liquidity fees and impermanent loss are not computed. Equity is sampled at event times. A group of wallets is the analyst's declaration, not a finding. No live provider call was made in this phase and every proof ran on invented data.
