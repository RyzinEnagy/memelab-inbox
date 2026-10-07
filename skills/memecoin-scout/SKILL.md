---
name: memecoin-scout
description: Run the Memecoin Investing Lab opportunity scout or a single-token deep analysis on Solana (discovery funnel, identity check, liquidity depth, LP, mechanics, holders, wallet forensics, structure, entries, R:R, sizing, exits, scoring, watchlist). Use when asked to find memecoin opportunities, analyze a Solana memecoin, refresh the watchlist, or review a memecoin trade.
---

# Memecoin Investing Lab: opportunity scout

Research system only. Never execute trades, never ask for seed phrases or private keys, never connect a wallet with signing authority. "ENTRY CONDITIONS MET" is an evidence statement, not an instruction. Finding nothing is a valid result.

## Where things live

- Code and database: the `memelab` project folder (Python package `memelab/`, SQLite at `data/memelab.sqlite`, reports in `data/reports/`, inbox in `data/inbox/`). If the folder is not in the sandbox, pull it from the user's computer or the hand-off repo first.
- Hand-off repo for data: GitHub `RyzinEnagy/memelab-inbox` (public, market data only). The sandbox reads `raw.githubusercontent.com`; the browser writes by committing files.
- Config: `data/config.json` holds `gh_owner`, `gh_repo`, `gh_branch`, `helius_api_key`. Never print the key, never commit it.
- Docs: `docs/ARCHITECTURE.md` (module contract), `docs/SOURCES.md` (what each source gives and its tier).

## Why the browser bridge exists

The cloud sandbox cannot reach any crypto API (egress 403). The user's Chrome can, and raw.githubusercontent.com is reachable from the sandbox. So: Chrome fetches, commits JSON to the repo, the sandbox pulls and analyzes. Use Claude in Chrome (the user's Chrome), work in a tab on `https://example.com/` (no CSP, so fetch and eval work). GitHub pages have a strict CSP: never fetch APIs from a github.com tab.

## Standard run: "Find memecoin opportunities"

1. `python -m memelab init` (idempotent).
2. Load the collector in the example.com tab. If `bridge/collector.js` exists in the repo: `eval(await (await fetch("https://raw.githubusercontent.com/RyzinEnagy/memelab-inbox/main/bridge/collector.js")).text())`. Otherwise paste `memelab/bridge/collector.js` as one javascript_tool call. Same for `bridge/screen.js` and `bridge/stage2.js` when needed.
3. Discovery (stage 1): `python -m memelab plan discovery --id <disc_id>` prints the `await __ML.run({...})` call. Run it, then `await __ML.screen({minLiq:20000,minVol:50000})`, then the pre-score/trim step (top 28 full rows + rest summary, drop names), then `__ML.ship("inbox/<disc_id>.json")`.
4. On the GitHub new-file page: run the `land` snippet (decode `location.hash`, synthetic paste into `.cm-content`, then `history.replaceState`), click "Commit changes..." (top right, about x=1467,y=125 at 1553-wide viewport) and confirm. The user gave standing approval for data commits into this repo; ask again for anything else on GitHub.
5. Pull: `python - <<'EOF'` using `memelab.bridge.github_inbox.pull("inbox/<disc_id>.json", result_name="<disc_id>")`. Then `python -m memelab discover <disc_id>`.
6. Stage 2: in the example.com tab, `await __ML.stage2([...survivor mints...], {keep: 8})`, then the slimming step for rug/jup/ds bodies, ship as `inbox/<s2_id>.json`, commit, pull, then `python -m memelab stage2 <disc_id> --results <disc_id> <s2_id>`.
7. Deep fetch: print token params with the snippet in the CLI notes (`[mint, mainPool, decimals, price, liq]` per candidate). In the tab: `__ML.plan = __ML.deepPlan("<deep_id>", TOKENS, SOL_PRICE, {rpc: "https://mainnet.helius-rpc.com/?api-key=<key>"})`; `__ML.start(__ML.plan, 5)`; poll `__ML.done ? __ML.summary : __ML.progress()` (GeckoTerminal is paced at one call per 2.6 s; 3 tokens take about 2 minutes). Batch 3 tokens per file (URL fragment limit ~2 MB). Ship, commit, pull.
8. Optional forensics: for the top economic holders and the dev wallet, `Plan().wallet_forensics(wallets)` (Helius Enhanced Transactions) and `Plan().holders_full(mint)`; run in the tab, ship as `inbox/<id>_wallets.json`, pull. The pipeline picks up `helius_tx:*` bodies automatically.
9. Analyze and report: `python -m memelab scout --mints <deep candidates> --results <all result ids> --stage1 <disc_id>`. Per-token reports land in `data/reports/`, the scout report as `*_SCOUT.md`. Deliver the scout report and the top per-token reports to the user.
10. Watchlist and rejections: `python -m memelab watchlist`, `python -m memelab rejections`. Every analysis diffs against the previous thesis snapshot and prints WHAT CHANGED.

## Single token: "Analyze <mint>"

Never analyze from a ticker. Require the mint. Run stage2 for that mint alone (identity + structure), then the deep plan, then `python -m memelab analyze <mint> --results ... [--account-size X --max-loss-usd Y]`. Without account inputs the report gives only the liquidity-implied maximum size.

## Known data behaviours

- RugCheck `token_extensions` lists every Token-2022 extension with null/false when absent; only non-null values count. pump.fun now mints Token-2022 with metadataPointer, which is benign.
- RugCheck `insiderNetworks[].tokenAmount` is in base units.
- GeckoTerminal answers 429 without CORS headers; the browser sees "Failed to fetch". The collector paces and retries.
- GeckoTerminal trades: when the memecoin is the quote side of a pool, price_from/price_to flip; the normalizer picks the side closest to the reference price.
- Only candles/trades from the token's own pools are used; the normalizer filters by pool id.
- Jupiter `priceImpactPct` is a fraction (0.0186 = 1.86%).
- Holder counts differ across providers (RugCheck counts all accounts, Jupiter/GeckoTerminal filter); the report records the discrepancy rather than choosing.

## Evidence discipline

Every report keeps FACT / INFERENCE / HEURISTIC / UNKNOWN separate. Never promote an inference. Never fabricate missing data; write UNABLE TO DETERMINE. A fatal flag overrides the score. Write "what would make this token unacceptable" before deep research.
