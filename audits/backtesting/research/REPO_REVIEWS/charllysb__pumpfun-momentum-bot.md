# charllysb/pumpfun-momentum-bot

- URL: https://github.com/charllysb/pumpfun-momentum-bot
- Pinned commit: 0dccad2fa55937ba8d0bea2b31c650de8480db9d (2026-07-25T20:07:30-03:00), cloned 2026-10-23T15:52Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23 (no difference).
- Category: crypto/DEX/Solana (live pump.fun momentum bot with forward paper-trading mode; not a backtester)
- Discovery channel: GITHUB_API search "pump.fun backtest"
- Stars/forks (low weight, from search time): 1/n.a.
- License (from LICENSE file text, not badge): MIT (Copyright (c) 2026 Charllys) ; transitive notes: requirements.txt pins requests==2.32.3 and python-dotenv==1.0.1, others are lower bounds (solders>=0.21, solana>=0.34, mnemonic, httpx, websockets, cryptography).
- Package: none ; Python/OS: Python with asyncio and Tkinter, Windows-oriented TLS handling (live_executor.py:37-60) ; native deps: none beyond wheels.
- Maintenance: last commit 2026-07-25; no CI; no tests; 5 Python files (2,061 lines including docs image).
- Security surface: LIVE TRADING AND WALLET CODE PRESENT. live_executor.py loads a seed phrase or private key from env (live_executor.py:93-106), signs and sends PumpPortal-built transactions without inspecting their instructions (live_executor.py:164-195), and can transfer SOL (live_executor.py:113-136; GUI recharge bot_gui.py:325-340). Live mode is enabled by `TS_LIVE=1` or `--live` (token_stream.py:41) with a typed "REAL" confirmation on the CLI (token_stream.py:545-546) and a dialog in the GUI (bot_gui.py:384-388); loading a preset JSON can switch the live checkbox on (bot_gui.py:300). On Windows it trusts every cert in the OS ROOT and CA stores (live_executor.py:47-57). vault.py writes a plaintext key backup on request (vault.py:243-255) and injects secrets into os.environ (vault.py:68-74). slippage_test.py spends real SOL. Network: PumpPortal WebSocket and trade API, Solana RPC. Nothing was executed.

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | NOT_SUPPORTED | ticks only |
| tick/trade replay | NOT_SUPPORTED | consumes the live PumpPortal stream (token_stream.py:483-497); raw ticks are never stored, only closed-trade CSV rows (token_stream.py:193-211) |
| CPMM math | NOT_SUPPORTED | spot price from bonding-curve PDA virtual reserves, read live (slippage_test.py:52-74: offsets 8 and 16 = virtual token and virtual SOL reserves); no swap output math |
| CLMM/DLMM math | NOT_SUPPORTED | none |
| routes | NOT_SUPPORTED | delegated to PumpPortal `"pool": "auto"` in live mode (live_executor.py:173) |
| fees/taxes | SOURCE_CODE_VERIFIED (flat) | 1.5% per side fee, 2% entry and exit slippage, 0.0006 SOL fixed cost (token_stream.py:74-78, 395-405); no Token-2022 fee model (Token-2022 only for balance lookup, live_executor.py:34, 141) |
| thin exits / size-dependent impact | NOT_SUPPORTED | friction is a flat percentage of a fixed 0.05 SOL stake; inactivity exit fills at last seen price (token_stream.py:443-446) |
| fill timing (next bar, latency) | SOURCE_CODE_VERIFIED | paper entry at the triggering tick's marketCapSol x 1.02 with zero latency (token_stream.py:277-305); paper exit at the tick that trips the stop x 0.98 (token_stream.py:372-405) |
| point-in-time guard / no lookahead | NOT_SUPPORTED | wall-clock `time.time()` receipt time (token_stream.py:81-82, 252); no replay, so nothing to guard |
| async event/catalyst injection | NOT_SUPPORTED | only create/buy/sell stream messages (token_stream.py:507-524) |
| wallets/on-chain | SOURCE_CODE_VERIFIED (live signing) | unique buyer sets from traderPublicKey (token_stream.py:267-268); live keypair, signing, sending, SOL transfer (live_executor.py:93-136, 180-195) |
| cross-token cohorts / portfolio | SOURCE_CODE_VERIFIED (minimal) | watchlist of up to 60 new tokens, max positions, loss circuit breaker (token_stream.py:66-72, 230-231, 363-370) |
| walk-forward / holdout / multiple testing | NOT_SUPPORTED | none; study results are README prose (README.md:66-86) |
| metrics/report | SOURCE_CODE_VERIFIED (minimal) | win rate, gross vs net PnL summary (token_stream.py:452-461) |
| live trading code present (must be avoidable) | SOURCE_CODE_VERIFIED (present) | live_executor.py, slippage_test.py, bot_gui.py live toggle and recharge; avoidable only by never importing these modules |

## Fill and chronology assumptions (read the code)

There is no historical backtest. The "simulated mode" is forward paper trading on the live PumpPortal WebSocket. A token enters the watchlist at its create message with reference market cap `marketCapSol` (token_stream.py:225-244). On each trade message the bot updates the current market cap and unique buyers; when the market cap is up at least 20% within 90 s of first sight with at least 8 unique buyers, it "enters" at that same tick's market cap plus 2% (token_stream.py:275-305). Exits are evaluated on every subsequent tick (hard stop -12%, trailing -13% from peak after +12%) and on a 3 s janitor for 25 s inactivity, filling at the current tick minus 2% (token_stream.py:372-405, 443-446). PnL deducts 1.5% per side and a fixed 0.0006 SOL (token_stream.py:399-405). Price is PumpPortal's reported market cap, timestamps are local receive times, and the fill has no latency, no curve math and no size dependence. The README itself reports that the live run lost money because orders took 1 to 3 s to confirm and the price had reversed (README.md:76-79), which is exactly what this paper fill model omits.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
not run: no offline or replay path; every module imports network or wallet libraries; live signing code present. See smoke/charllysb__pumpfun-momentum-bot/output.txt
```
Outcome: not run. All five Python files read in full.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 2 | 6.00 | genuinely pump.fun-native signals (fresh launches, unique buyers, market cap in SOL, curve PDA read) but live-stream only |
| B microstructure | 17 | 1 | 3.40 | flat fee and slippage percentages, fixed stake, zero-latency tick fills |
| C point-in-time | 15 | 0.5 | 1.50 | no replay or stored data; wall-clock receipt times |
| D catalyst/on-chain events | 11 | 1 | 2.20 | live on-chain trade stream drives decisions; no async external events, no persistence |
| E TA/strategy flexibility | 9 | 1 | 1.80 | one hardcoded momentum/trailing strategy with env-tunable thresholds |
| F statistical validation | 11 | 0.5 | 1.10 | README anecdotes (2 paper runs, 1 live run), no statistics code |
| G integration fit | 9 | 0.5 | 0.90 | monolithic live bot with wallet, GUI, paid stream key |
| H maintenance/tests | 6 | 0.5 | 0.60 | no tests, no CI, one author |
| I license/supply chain | 5 | 2 | 2.00 | MIT text; loose pins; live path blind-signs third-party transactions |
| J operational footprint | 2 | 1 | 0.40 | needs always-on WebSocket and a PumpPortal key with balance |
| Total | 100 | | 19.90 | |

Hard gates: serious unresolved security hazard (seed-phrase wallet that blind-signs PumpPortal-built transactions and can transfer SOL; plaintext key backup export). RESEARCH_ONLY; do not import any module. Most important limitation for memecoins: no historical replay at all, so nothing can be backtested point-in-time; the paper mode fills at the trigger tick with no latency, which the author's own live run showed is the dominant cost. One credible negative finding: README.md:39-42 calls the friction model "realistic" and "explicit", but it is a flat 1.5% fee plus 2% slippage per side on a fixed 0.05 SOL stake with zero-latency fills (token_stream.py:74-78, 297-298), and the README's own live result contradicts the simulated positive result.
Disposition: REJECT. Suggested use: REFERENCE (README live-versus-paper latency finding only, as a cautionary data point).
