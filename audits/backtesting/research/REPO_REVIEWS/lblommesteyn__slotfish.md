# lblommesteyn/slotfish

- URL: https://github.com/lblommesteyn/slotfish
- Pinned commit: 4f760c8076bbebc15106cc03ddc3ea527e79dcd4 (2026-10-12T10:22:10-04:00), cloned 2026-10-23T15:52Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23 (no difference).
- Category: crypto/DEX/Solana (event-driven replay engine for pump.fun bonding curve and PumpSwap, Rust core plus Python research scripts)
- Discovery channel: GITHUB_API search "pump.fun backtest"
- Stars/forks (low weight, from search time): 0/n.a. (forks not recorded in LONGLIST)
- License (from LICENSE file text, not badge): MIT (Copyright (c) 2026 Luke Blommesteyn) ; transitive notes: Rust crates (arrow 55, parquet 55, reqwest 0.12 native-tls, rayon, clap, serde, sha2, bs58) are MIT/Apache-2.0 family; Cargo.lock committed; Python requirements pinned exactly (polars 1.41.2, lightgbm 4.7.0, scikit-learn 1.9.1, scipy 1.14.1, statsmodels 0.15.0, numpy 2.2.6, pyarrow 24.0.0).
- Package: none (no crate or PyPI release) ; Python/OS: Rust 1.85+, Python 3.12 for research scripts, scripts handle Windows `.exe` (scripts/run_baseline.py:24) ; native deps: full Rust toolchain build, LightGBM wheel for research.
- Maintenance: last commit 2026-10-12; CI files `.github/workflows/ci.yml` (cargo fmt --check, clippy -D warnings, cargo test --release; Python job only `py_compile`); tests: 2 Rust integration test files (tests/engine.rs 5 tests, tests/decode.rs 2 tests) plus 3 unit tests in src/amm.rs, real-chain fixtures (tests/fixtures/blocks_3.jsonl.gz, events_1000slots.parquet). Single author, 0 stars, about 11 days old at review.
- Security surface: no install scripts run; `scripts/fetch_supervised.sh` is a restart loop around the fetcher (not run). Network: `fetch` and `paper` subcommands call a public Solana RPC (default https://solana-rpc.publicnode.com, src/main.rs:132 and :199) with read-only `getBlock`/`getSlot` (src/fetch.rs:56-93, src/paper.rs:90-121). No keypairs, signing, transaction sending or wallet code anywhere (grep for sign/keypair/private/sendTransaction found none; src/paper.rs:1-6 states nothing is sent). No binaries; committed results JSON/parquet only.

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | NOT_SUPPORTED | engine iterates a per-event tape only (src/engine.rs:180-246); no bar type anywhere |
| tick/trade replay | SOURCE_CODE_VERIFIED | events ordered by (slot, tx_idx, ev_idx), every reserve field is post-event state (src/events.rs:1-3, src/store.rs:1-3); replay loop src/engine.rs:180-246; chain-order test tests/engine.rs:32-43 |
| CPMM math | SOURCE_CODE_VERIFIED | src/amm.rs:27-52: buy `net = budget*1e4/(1e4+fee_bps)`, `out = net*tok/(sol+net)`, sell `gross = tokens*sol/(tok+tokens)`, fee `ceil(gross*bps/1e4)`; exact x*y=k with fee on top for buys and from proceeds for sells, floor on outputs. Curve uses virtual reserves (src/market.rs:91-121); tests src/amm.rs:68-104 |
| CLMM/DLMM math | NOT_SUPPORTED | only pump.fun curve and PumpSwap CPMM (src/decode.rs:19-20) |
| routes | NOT_SUPPORTED | one venue per token: curve, then canonical migration pool only (src/market.rs:119-121) |
| fees/taxes | SOURCE_CODE_VERIFIED (partial) | per-event fee bps: curve protocol+creator (src/decode.rs:171-183), PumpSwap lp+protocol+creator (src/decode.rs:244-261), so dynamic fee tiers are read from data; tx base + priority fee per landed tx (src/exec.rs:47-49, 119, 152). Token-2022 transfer fees NOT_SUPPORTED. PumpSwap `virtual_quote_reserves` NOT decoded (src/decode.rs:241-273) |
| thin exits / size-dependent impact | SOURCE_CODE_VERIFIED | size-dependent CPMM impact (src/amm.rs:86-93 test); no feedback, so round trips pay impact twice (src/exec.rs:8-10, amm.rs:95-104); exits retry next slot and are written off at zero after 20 failures (src/exec.rs:137-168). Curve real-token cap at graduation not enforced (Pool has no real reserves, src/amm.rs:11-16) |
| fill timing (next bar, latency) | SOURCE_CODE_VERIFIED | decision after the mint's last trade in slot s, fill at END of slot s+L (default L=2) (src/exec.rs:3-7, 105-110; src/engine.rs:97-110, 213-218, 243; docs/EXECUTION.md:10-16); engine equals reference round trip (tests/engine.rs:79-111) |
| point-in-time guard / no lookahead | SOURCE_CODE_VERIFIED | features from events 0..=i only, wallet skill outcomes revealed after horizon and strictly before current slot (src/features.rs:1-17, 140-157, 166-169); tradability uses launch-time facts and slot comparisons (src/market.rs:41-51); lookahead test recomputes features on a physically truncated tape (tests/engine.rs:129-165); purged chronological split (python/slotfish/research.py:85-95) |
| async event/catalyst injection | NOT_SUPPORTED | Strategy sees only the tape event plus fixed features (src/engine.rs:19-36); no external event channel |
| wallets/on-chain | SOURCE_CODE_VERIFIED (analytics only) | on-chain wallet features: Beta-Binomial wallet skill, co-buying coordination, creator holdings, snipers (src/features.rs:8-17, 186-208); no key handling |
| cross-token cohorts / portfolio | SOURCE_CODE_VERIFIED (partial) | survivorship-free cohort from contiguous slots (src/fetch.rs:1-12, src/market.rs:41-44); max open positions (src/engine.rs:232); fixed size per trade, PnL per round trip, no cash ledger (src/exec.rs:82-90) |
| walk-forward / holdout / multiple testing | SOURCE_CODE_VERIFIED (holdout only) | train/val/test with purge gap (research.py:85-95), threshold chosen on validation (research.py:220-230), token-cluster bootstrap CI (research.py:146-161), 15-min block IC t-stats and paired IC test (research.py:164-206); walk-forward NOT_SUPPORTED; no multiple-testing correction although 6 ablations and 3x90 execution sweeps run on the test window (research.py:287-300, scripts/run_baseline.py:79-90) |
| metrics/report | SOURCE_CODE_VERIFIED | src/report.rs; research.py:164-191; committed results/ JSON |
| live trading code present (must be avoidable) | NOT_SUPPORTED (none present) | `paper` mode tails blocks read-only and records hypothetical orders (src/paper.rs:1-19, 172-207) |

## Fill and chronology assumptions (read the code)

A decision is taken at most once per (mint, slot), after the mint's last curve trade in that slot (src/engine.rs:213-218). This peeks at later events in the same slot (`next_same_mint_in_slot`, src/engine.rs:276-286), which is valid only under the stated assumption that a whole block is observed at once (docs/EXECUTION.md:18-21). The order lands at slot s+L and fills against the pool state at the end of that slot, i.e. after every observed trade in the landing slot (src/engine.rs:97-110 settles only when the clock passes the landing slot). Entry fails with probability p_fail (seeded hash, src/exec.rs:52-60) or if the fill is worse than the decision quote by more than 2,000 bps (src/exec.rs:124-129); entries are skipped once the token graduated (src/exec.rs:111-118). Exits are fixed-horizon only (src/strategy.rs:1-2), never slippage-limited, retried one slot later on random failure (src/exec.rs:137-168). Our own trades never move the replayed pool. Fees are the event-reported rate of the latest state event, so a fee tier change shows up one event late at most. There are no bars, so "unfinished bar" leakage does not apply; features use only events up to i plus timeline states strictly in the past (src/features.rs:246-251). Exits on graduated tokens use PumpSwap reserves decoded from the event's raw `pool_quote_token_reserves` (src/decode.rs:241-273); the appended signed `virtual_quote_reserves` field is ignored. Upstream pump-fun/pump-public-docs (docs/PUMP_SWAP_README.md and docs/VIRTUAL_QUOTE_RESERVES_FEE_ADJUSTMENT.md at 639b87fb) say quotes must use effective quote reserves = vault balance + virtual_quote_reserves, and v2 trades keep protocol and creator fees in the vault while subtracting them from virtual_quote_reserves; pump-public-docs issue #55 reports non-zero values around slot 453.0M. That matches slotfish's own unexplained ~10% PumpSwap SOL-continuity breaks in 500/508/515-byte BuyEvent variants (docs/DATA.md:60-71). Evidence source: one Firecrawl developer search, 2026-10-23.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
not run: Rust engine; brief forbids building niche Rust/TS repos. See smoke/lblommesteyn__slotfish/output.txt
```
Outcome: not run. Math files and tests read instead; analytic check confirms amm.rs is exact x*y=k with integer floors and fee placement matching the curve (fee added on buys, deducted on sells).

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 4 | 12.00 | native pump.fun curve + PumpSwap decoding from raw blocks, Mayhem and non-SOL-quote exclusions at launch (src/market.rs:19-51), slot clock measured at 0.217 s; only one venue family |
| B microstructure | 17 | 3.5 | 11.90 | virtual-reserve CPMM, event fee bps, latency in slots, end-of-slot fills, priority fees, failures, slippage rejects, exit retries; misses PumpSwap virtual_quote_reserves, curve real-token cap, MEV, CLMM/DLMM, Token-2022 fees |
| C point-in-time | 15 | 4 | 12.00 | streaming features, delayed skill outcomes, truncated-tape lookahead test (tests/engine.rs:129-165), purged split; observed_at is assumed equal to end of slot (block lag measured only in paper mode, src/paper.rs:128-137) |
| D catalyst/on-chain events | 11 | 2.5 | 5.50 | strong point-in-time on-chain wallet/creator/sniper features; no social/catalyst or external async events |
| E TA/strategy flexibility | 9 | 1.5 | 2.70 | entry-only boolean Strategy trait in Rust, fixed-horizon exits, fixed feature list; no bars, stops or retest logic |
| F statistical validation | 11 | 3.5 | 7.70 | purged chrono split, val-chosen threshold, random/momentum/no-trade baselines, cluster bootstrap, block t-stats, paired test, calibration, survival; single split, no walk-forward, no multiple-testing correction |
| G integration fit | 9 | 2.5 | 4.50 | CLI with JSON output could be a subprocess; parquet not SQLite; needs Rust build; research pinned to 3.12; no wallets |
| H maintenance/tests | 6 | 3 | 3.60 | CI runs fmt, clippy and cargo test on real-chain fixtures; very new, single author, Python only syntax-checked |
| I license/supply chain | 5 | 4 | 4.00 | MIT text, Cargo.lock and exact Python pins, minimal standard crates |
| J operational footprint | 2 | 3 | 1.20 | no services; Rust toolchain build, about 650 MB/day of event parquet, free RPC with about 25 h rolling history (docs/DATA.md:12, 24-27) |
| Total | 100 | | 65.10 | |

Hard gates: none. Most important limitation for memecoins: pump.fun/PumpSwap only, entries only on the bonding curve, exits fixed-horizon; graduated-token exits price PumpSwap on raw vault reserves without `virtual_quote_reserves`, so post-migration fills are wrong whenever that field is non-zero (third-party PumpSim docs claim about 20.69% of effective quote on migrated coins, unverified; if true, slotfish exit prices on migrated pools would be about 20.7% too low). One credible negative finding: the README says evaluation "only ever touches the test period once", but research.py:287-300 fits and evaluates 6 ablation feature sets on the test split and run_baseline.py:79-90 runs 270 execution sweeps on the test window, with no multiple-testing adjustment.
Disposition: REIMPLEMENT_IDEA (port the end-of-landing-slot fill rule, event-reported fee decoding, Mayhem/non-SOL exclusions, delayed-outcome wallet skill and the truncated-tape lookahead test to Python; add effective-reserve PumpSwap pricing). Suggested use: REFERENCE.
