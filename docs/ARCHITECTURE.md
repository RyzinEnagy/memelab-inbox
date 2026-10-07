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
