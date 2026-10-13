# Phase 05: token identity and market context

Prompt 05 ("Resolve exact token identity and snapshot market conditions"). Code: `memelab/social/identity.py`, `memelab/social/market_context.py`, `memelab/social/_keccak.py`, migration 5 in `memelab/social/schema.py`, CLI `social resolve` and `social identity`. Tests: `tests/test_social_identity.py` (29). Fixtures: `tests/fixtures/social/resolve/` (synthetic).

Related: [HANDOFF.md](HANDOFF.md), [DECISIONS.md](DECISIONS.md) D-030 to D-034, [SCHEMA_01.md](SCHEMA_01.md).

## What existed and what was reused

- `normalize.build_bundle` (Solana) and `chains/evm.build_bundle` (Base, BNB Chain, Ethereum and the other EVM chains) already parse every provider body the lab collects. Market context calls them; it does not parse DEX Screener, Jupiter, GeckoTerminal, GoPlus or KyberSwap again.
- `chains/registry.py` gives chain ids, DEX Screener and GeckoTerminal chain names, wrapped natives and stablecoins. The resolver uses it for link chains and as the trusted list of infrastructure assets.
- `bridge/plan.py` and `chains/plan.py` build the collector plans. `identity.resolution_plan()` and `market_context.context_plan()` compose those builders (DEX Screener token and search calls, Jupiter search, GoPlus, the deep plans with OHLCV pinned to the token and executable quotes).
- `social.store.upsert_token_ref` and `social_token_refs` (Phase 01) already hold identity as (chain, contract) and keep tickers as `TICKER_ONLY` with no contract. Resolutions point at those refs.
- `pipeline.analyze_token` was read and not called: it writes reports, the `tokens` table (keyed by mint only, so one EVM address on two chains would collide) and theses. Phase 05 only needs identity and a snapshot, so it uses the bundle builders under the pipeline.
- `catalyst/match.py` links news to the most liquid Solana token for a term and labels it AMBIGUOUS when several compete. That is a different, older contract (catalyst links, Solana only). It was left unchanged. The social side uses the new resolver, which never picks a token by liquidity.

## Resolution

Input: one post's text (read in memory, never stored or returned), its links, its cashtags, an optional chain the caller knows (for example the chain a channel is about), and collector bodies.

Mentions found:
- CONTRACT: 0x plus 40 hex, or a base58 string that decodes to 32 bytes. A base58 run inside a 0x address is ignored.
- LINK: dexscreener.com/<chain>/<pair or token>, geckoterminal.com/<network>/pools|tokens/<addr>, pump.fun/coin/<mint>, birdeye.so/token/<addr>?chain=, jup.ag, etherscan.io, basescan.org, bscscan.com, solscan.io, solana.fm, explorer.solana.com, dextools.io pair-explorer. The host or path gives the chain.
- TICKER: `$` plus a letter and up to 9 more characters. `$100` is not a ticker.

Outcomes (lower-case, as the prompt names them):

| status | when |
|---|---|
| resolved | one supported (chain, contract) backed by a chain-valid address and at least one provider record or the registry, nothing in the post contradicting it |
| ambiguous | the same address on several supported chains, a pair link that maps to several tokens, a registry ticker with no chain stated, or any ticker with candidates and no same-post contract |
| unresolved | malformed address, bad EIP-55 checksum, wrong length, unknown chain, unsupported chain, no provider record, or a ticker with no candidates |
| conflicted | a link's chain disagrees with where providers find the address, or the post's ticker is not the symbol providers report for the contract in the same post (both mentions become conflicted) |

Rules:
- A ticker alone never resolves, even with one search hit (`single_search_candidate_not_proof`): a search only sees what it indexes.
- A ticker resolves when a contract in the same post resolves and providers report that ticker for it (`corroborated_by_contract_in_same_post`), or when it names a registry asset (WETH, WBNB, WSOL, USDC, USDT, USDbC) and the caller states the chain.
- Contract identity wins over names. A contract that copies a better-known token's symbol still resolves to itself, flagged `symbol_shared_with_other_contracts` and `a_more_liquid_contract_uses_this_symbol`; the other contracts are stored as rejected candidates.
- A pair or pool link is mapped to its base token through provider records (`pair_mapped_to_base_token`).
- Typos are never corrected. A malformed or unknown address lists known addresses within edit distance 2 (from the provider bodies, `social_token_refs` and `tokens`) as `near_match` candidates; a bad checksum lists the same hex address as `same_hex_bad_checksum`.
- Migration: a trusted relation (`record_relation`, basis OFFICIAL_SOURCE needs the https URL that states it) is listed as a successor or predecessor candidate. The old contract still resolves to the old contract.
- Providers that disagree on a contract's symbol do not change its identity (`providers_disagree_on_symbol`).
- Every candidate is stored with chain, provider chain, contract, symbol and name seen, support, verdict, reason, providers and largest reported liquidity.

Supported chains: solana, ethereum, base, bsc. Their upstream coverage in the existing code:

| chain | identity sources | market sources | executable quotes |
|---|---|---|---|
| solana | DEX Screener, Jupiter tokens v2, GeckoTerminal | same, plus RugCheck markets through normalize.py | Jupiter quote v1 |
| base, bsc, ethereum | DEX Screener, GeckoTerminal, GoPlus | DEX Screener, GeckoTerminal | KyberSwap routes |

Every other registry chain (arbitrum, avalanche, polygon, hyperevm, sui) and every chain a provider names that the registry does not know is stored as `support='unsupported'` and never resolves.

## Market context

`market_context.attach(con, resolution_id, bodies, fetched_at, published_at)` runs only on a resolved mention (it raises otherwise). It stores one row per provider value in `social_market_facts`:

- fields: price, market_cap, fdv, circulating_supply, total_supply, liquidity_reported (per pair and per provider), volume_24h, pair, sell_quote_out, buy_quote_out, sell_quote_out_usd, sell_price_impact, buy_price_impact, price_candle_open/high/low/close
- unit (USD, token, SOL, ETH or BNB, token_base_units, ratio, id, status) and quote currency
- supply basis for valuation fields: market_cap is circulating, fdv is total, per provider (Jupiter mcap/fdv with circSupply/totalSupply, DEX Screener marketCap/fdv). This is the lab's reading of the provider fields; it was not re-checked against provider docs in this phase (UNKNOWN until checked).
- provider, collector key, source URL, as_of, as_of_kind (OBSERVED_AT_FETCH or HISTORICAL_CANDLE), fetched_at, validity window, evidence bucket
- versioning: a series is (chain, contract, provider, field, pair, size, as_of_kind). A new value is version n+1 with `supersedes_fact_id`; the same fetch again adds nothing.

Validity windows for observed values (lab convention): prices and quotes 120 s, liquidity and valuation 300 s, 24 h volume 3600 s, supply and pair ids 86400 s. A historical candle is valid for its own interval.

Posting time versus fetch time (`social_market_context`):
- HISTORICAL_CANDLE: the finest GeckoTerminal candle of the token's own pool that contains published_at; the posting price is its open, high and low are stored with it.
- FETCHED_AT_POSTING: no candle, but the fetch happened within 120 s of publication.
- NO_HISTORY: no candle covers the post. The posting price stays NULL; today's price is stored only as observed-at-fetch, with `observed_lag_seconds`.
- PUBLISHED_AT_UNKNOWN: the post has no time.

Liquidity versus proceeds: reported pool liquidity and executable sell quotes are separate facts. A sell quote's proceeds are stored in the quote asset (SOL, ETH, BNB); KyberSwap's own USD figure is FACT, a USD figure the lab computes from a supplied native price is INFERENCE. NO_ROUTE is stored as a status. Notes record proceeds/size ratios and `reported_liquidity_is_not_exit_proceeds`.

Disagreeing providers keep separate rows; the context notes the price spread and `providers_disagree_on_price` above 3 percent (the threshold `normalize.py` already uses). The observed price shown is Jupiter for Solana, otherwise the deepest pair's price; the others stay stored.

Missing pool: `market_status='NO_POOL'`, no pair or liquidity fact, note `no_pool_reported_at_fetch`.

## Downstream API

```python
from memelab.social import identity
identity.token_identity(con, item_key="telegram:-1001000000001_22")
# -> [{status, reasons, identity: {chain, contract, ref_id, asset_class} or None, candidates, evidence,
#      resolver_version, resolved_at, market_context: [{posting_time_status, posting_price, observed_price, notes, ...}]}]
```

CLI demo (temp DB, synthetic fixtures):

```
python -m memelab social resolve --post tests/fixtures/social/resolve/post_ambiguous.json --bodies tests/fixtures/social/resolve/fx_providers.json --context --db /tmp/demo.sqlite --now 1791676800
python -m memelab social resolve --post tests/fixtures/social/resolve/post_resolved.json --bodies tests/fixtures/social/resolve/fx_providers.json --context --db /tmp/demo.sqlite --now 1791676800
python -m memelab social identity --item telegram:-1001000000001_22 --db /tmp/demo.sqlite
```

## Not done here

- No live provider call was made; every proof runs on synthetic bodies. The plans exist (`resolution_plan`, `context_plan`) and use the collector's existing projections.
- Ingestion does not yet call the resolver: the inbound schemas carry no post text and no extracted addresses (D-016), so a connector must resolve before it hashes the text, or a later inbound version must carry addresses and links. That wiring is left to the extraction phase (proposed 10).
- GeckoTerminal OHLCV reaches back only as far as the deep plan asks (120 daily, 300 to 400 hourly, 200 to 400 fifteen-minute candles). Older posts get a daily candle or NO_HISTORY.
