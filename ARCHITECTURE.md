# Memecoin Investing Lab: architecture

## Flow

```
discovery plan ──► browser collector ──► result JSON ──► normalize ──► Bundle
                                                               │
   Stage 1 broad universe (m01) ◄──────────────────────────────┘
   Stage 2 structural filter (m02 identity, m03 market, m04 supply, m08 mechanics, m07 LP)
   Stage 3 behavioral filter (m09 holders, m11 early wallets, m12 order flow, m19 attention)
   Stage 4 setup filter (m13 structure, m14 breakout, m21 lifecycle, m15 entry/invalidation)
   Stage 5 deep DD (m06 depth, m10 clustering, m20 manipulation, m16 R:R, m17 sizing, m18 exit)
   m23 thesis ─► m24 ranker/score ─► report.py (markdown) ─► DB theses/entries/rejections/watchlist
   m25 monitor diffs new snapshot against previous thesis snapshot_json
```

All modules are pure functions of a `Bundle` dict (plus optional account inputs) returning a dict with
`facts`, `inferences`, `unknowns`, plus module-specific fields. They never fetch. This keeps them testable.

## Bundle contract (memelab/normalize.py builds it)

```
bundle = {
  "mint": str, "observed_at": float (epoch), "sources": {field: source_name},
  "identity": {"name","symbol","decimals","token_program","creator","dev","launchpad","graduated_pool",
               "graduated_at","first_pool_at","website","twitter","telegram",
               "name_matches": bool|None, "symbol_matches": bool|None, "sources_agreeing": int},
  "market": {"price_usd","price_sol","sol_price","circ_supply","total_supply","supply_raw_onchain",
             "market_cap","fdv","fdv_provider_denominator","liquidity_usd_total","holder_count",
             "vol": {"m5","h1","h6","h24"}, "chg": {...}, "buy_vol_24h","sell_vol_24h",
             "organic_buy_vol_24h","organic_sell_vol_24h","organic_score","net_buyers": {"m5","h1","h6","h24"},
             "txns": {"h1": [buys,sells,buyers,sellers], "h24": [...]}, "age_hours"},
  "pools": [ {"pool","dex","quote","created","reserve_usd","base_reserve","quote_reserve","vol_24h",
               "txns_h24": [b,s,buyers,sellers], "price","lp": {"locked_pct","locked_usd","holders":[{owner,pct}]},
               "market_type"} ],
  "authorities": {"mint_authority","freeze_authority","token_program","extensions": [..],"transfer_fee_bps",
                  "transfer_fee_max","permanent_delegate","metadata_mutable","update_authority","supply_raw","decimals"},
  "holders": {"total": int, "top": [{"account","owner","pct","amount","insider": bool}], "distribution": {"top_10","11_20","21_40","rest"},
              "dev_holding_pct", "insider_networks": [{"id","size","type","tokenAmount","activeAccounts"}]},
  "quotes": {"BUY": {usd: {"in","out","impact","route":[...],"status"}}, "SELL": {...}},
  "ohlcv": {"day1": [[ts,o,h,l,c,v],...], "hour1": [...], "minute15": [...]},
  "trades": [[ts, wallet, kind, base_amt, usd, price, tx]],
  "rpc_mint": {parsed getAccountInfo or None},
  "social": {"website","twitter","telegram","discord","description","boost_active","profile_listed"},
  "risks": [{"name","level","score","description"}],
}
```

Numbers are floats or None. Never fabricate: a missing field stays None and the module records it in `unknowns`.

## Evidence discipline

Each module returns:
```
{"facts": [str], "inferences": [str], "heuristics": [str], "unknowns": [str], ...module fields}
```
Report rendering preserves the four buckets. Inference is never promoted to fact.

## Scoring

m24 computes 8 components (15/15/10/10/15/10/10/15 = 100) and a FATAL_FLAGS list. Any fatal flag forces
status to REJECTED or DISTRIBUTION_RISK / THESIS_INVALIDATED as appropriate regardless of the numeric score.

## Status vocabulary

REJECTED, RESEARCH REQUIRED, WATCH, SETUP DEVELOPING, NEAR ENTRY, ENTRY CONDITIONS MET, OVEREXTENDED,
DISTRIBUTION RISK, THESIS DETERIORATING, THESIS INVALIDATED.

## Catalyst Intelligence (memelab/catalyst)

Operating question: what is new, who could buy because of it, who could sell to them, and can a realistic position exit?

Flow: sources.py (registry with access modes and coverage gaps) -> bridge/catalyst.js (fetch projections and a navigate-mode page parser) -> ingest.py (items -> events: four timestamps, evidence status from source tier, dedup by title similarity with publisher-level corroboration, syndication/circular roles, resurfacing, denials and cancellations as revisions, asset-list diffs as ACCESS events) -> match.py (terms -> Jupiter/DEX Screener search -> links by MINT with competing matches; common words and exchange products downgraded to THEMATIC/WEAK) -> attention.py (publisher-level metrics with sampling notes; social platforms stay UNKNOWN) -> assess.py (eight graded components, UNKNOWN earns zero, fatal core checks override, triage score for sorting only) -> monitor.py (token-first alerts: new catalysts, contradictions, deteriorations, event-day reassessment, expiry, outcomes) -> report.py (UTC stored, America/New_York displayed).

Tables: catalyst_sources, catalyst_items, catalyst_events, catalyst_event_revisions, catalyst_event_sources, catalyst_token_links, catalyst_attention_samples, catalyst_assessments, catalyst_alerts, catalyst_outcomes. Assessments and samples are append-only; events change only through revisions.

Verdicts: EVENT_ONLY (no verified token), RESEARCH (needs deep data), TRACKED (credible but no demand evidence, extended, late, or negative), WATCH_FOR_ENTRY (credible event, verified token, demand visible, ownership known and acceptable, exit feasible; entry still comes from the core entry module), REJECTED (fatal core check).

## Multi-chain ecosystem layer (memelab/chains)

Layers above the per-token pipeline, all chain-agnostic:

- registry.py: one record per chain (family solana/evm/move, GeckoTerminal network id, DefiLlama slug, CoinGecko platform / native coin / meme category, DEX Screener chain id, wrapped native, stables, router, public RPC, GoPlus chain id, explorer, launchpads, typical gas). `sync()` upserts into the `chains` table without touching rotation-managed fields. Tier and status are starting points; the rotation engine moves research allocation.
- evm.py: the reusable EVM engine. `build_bundle()` reuses the Solana bundle shape from DEX Screener and GeckoTerminal (shared parsers; EVM addresses are lowercased everywhere) and overlays GoPlus token_security (ownership, proxy, mint, pause, blacklist, limits, taxes, holders, LP holders), honeypot.is (simulated buy/sell, taxes, gas), KyberSwap route quotes (-> `quotes`, impact = 1 - amountOutUsd/amountInUsd, gas per leg) and eth_call results (totalSupply, decimals, owner, bytecode). `mechanics()` returns the m08 contract plus EVM fields; dangerous functions count as active only while someone can call them (live owner, hidden owner, reclaimable ownership). `identity()` replaces m02 for EVM tokens (name/symbol agreement across DS/GT/GoPlus/honeypot.is, bytecode present, source verified, official links). `execution_profile()` feeds the realistic execution comparison (gas round trip, taxes, route legs, exit capacity).
- pipeline.analyze_token(chain=...) swaps identity/mechanics for EVM chains; everything else (depth, LP, holders, clusters, order flow, structure, breakout, entries, R/R, sizing, exits, attention, manipulation, lifecycle, RS, thesis, ranker, monitor) runs unchanged. m06 reads `market.native_price` / `native_decimals` so ETH/BNB quotes price correctly. m24 fatal flags include HONEYPOT, CANNOT_BUY, HIDDEN_OWNER, EXTREME_TAX, SIMULATION_FAILED, AIRDROP_SCAM, SELFDESTRUCT, CREATOR_PRIOR_HONEYPOT, PROXY_WITH_LIVE_OWNER, TAX_MODIFIABLE_BY_OWNER.
- regime.py (layer 0): BTC/ETH/SOL/BNB trend vs 20d/50d MAs, 30d realized vol, 90d drawdown, CoinGecko global, DefiLlama stablecoin supply (7d change needs a 6-day-old snapshot), Hyperliquid funding/OI, meme breadth -> RISK-ON / NEUTRAL / RISK-OFF / HIGH-VOLATILITY SPECULATION / CAPITAL FLIGHT with a size multiplier.
- rotation.py (layer 1): Speculative Opportunity Index per chain, 0-100 = DEX activity 20 + meme activity 20 + participation 15 + capital flows 15 + attention 15 + opportunity quality 15. Every part lists its scale and value; UNKNOWN parts earn zero and are never redistributed; coverage is reported. Trend vs the previous score (RISING/FLAT/FALLING at +-5), FACT / INFERENCE / CONFIDENCE statements, research allocation FULL (>=55, coverage >=60%) / PARTIAL (>=40) / WATCHLIST, de-emphasis to LOW-PRIORITY MONITORING after three runs below 30 (Tier 1 never drops below WATCHLIST), Tier-2 BUILD PARTIAL/FULL alerts at SOI >= 60/70. Cross-chain rotation is inferred only from divergence sustained over two runs. Known bias: the opportunity-quality parts that read the system's own DB and the catalyst part of attention reflect research history; they are weighted down and labelled.
- narrative.py (layer 2): CoinGecko categories filtered to speculative themes (meme, launchpad ecosystems, animals, politics, celebrities, AI agents...), keyword clusters shared by >= 3 token names across chains, catalyst-event counts by specific keyword only. Lifecycle EMERGING / ACCELERATING / MANIA / EXHAUSTING / DEAD / MATURE from 24h change, volume/mcap and drawdown versus stored 14- and 30-day highs; UNKNOWN with a reason until history exists.
- emerging.py: Emerging Chain Detector (networks outside the registry in GeckoTerminal cross-network trending, DefiLlama TVL >= $20M; MONITOR at 2 pools or $200M TVL, BUILD PARTIAL at 6 pools or TVL +25% with 2 pools, BUILD FULL when sustained three runs; writes a partial `chains` record with status EMERGING), launchpad snapshots by pool dex id (Clanker/four.meme/Virtuals pools trade on general DEXes and stay UNKNOWN), dynamic meme benchmark baskets by cap bucket (MICRO/SMALL/MID/LARGE from the CoinGecko meme-token top 100), cross-chain relative strength (vs chain meme median, vs global basket of the same cap bucket, vs native coin).
- report.py / cli.py: `python -m memelab chains plan eco|disc|struct|deep`, `eco`, `discover <chain>`, `struct`, `analyze <chain> <addr>`, `scout --tokens chain:addr ...`. The scout report carries MARKET REGIME, CHAIN ROTATION (Chain / SOI / Trend / Research allocation / Major change), NARRATIVE ROTATION, benchmark basket, LAUNCHPADS, EMERGING CHAINS, CHAINS BEING DE-EMPHASIZED, WHAT WOULD CHANGE THE CURRENT ECOSYSTEM VIEW, then BEST CROSS-CHAIN OPPORTUNITIES (<= 5, each with CHAIN / CONTRACT / TOKEN STANDARD / PRIMARY POOL / IDENTITY CONFIDENCE / execution friction / cross-chain RS), correlation-aware allocation (same chain + same narrative share one budget; regime multiplier), NEAR MISSES, REJECTED AFTER DUE DILIGENCE.

Tables: chains, chain_snapshots, chain_dex_activity, chain_meme_activity, chain_flows, chain_scores, narratives, narrative_snapshots, narrative_tokens, launchpads, launchpad_snapshots, cross_chain_relative_strength, regime_snapshots, benchmark_baskets, ecosystem_alerts. tokens gained chain_id (= chain), narrative_id, token_standard, primary_pool. Reruns on the same result file are idempotent (rows at the same observed_at are replaced).
