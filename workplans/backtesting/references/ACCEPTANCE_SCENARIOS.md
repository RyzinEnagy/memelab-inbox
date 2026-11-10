# Fixed golden scenarios: minimum adversarial acceptance corpus

The implementing agent must derive exact datasets, expected results and independent hand calculations, then check in reusable fixtures and machine-readable golden reports. **Synthetic fixtures prove model behavior, not fidelity to a live historic market.**

## Identity & time (fail-closed)

- G01: Same ticker on two different mints → never merge trades/catalysts/price series.
- G02: Same mint, two pools with divergent liquidity → only compatible, time-valid routes counted; no sum-double-counting.
- G03: News first posted at 09:00, ingested at 09:08, processed at 09:12 → no trade at 09:00 based on this collector's knowledge.
- G04: Wallet transfer known 10:00 but actual sale 11:00 → transfer is not retrospectively labeled sale at 10:00.
- G05: Candle high occurs before candle closes; signal uses the high/close at 12:00 → earliest executable order after bar close and realistic fill delay.
- G06: Delisted or rugged token excluded by today's API → historical universe still contains it, or study marked selection-biased.
- G07: A zero data value is distinct from not observed / stale / missing; unknown must not silently become zero.
- G08: Retroactively corrected influencer-post timestamp and deleted posts → as-known-at observations remain immutable and late edits can't improve earlier backtests.

## Execution & cost

- G09: Static constant-product pool before/after sell with explicit separate reserves and fee, independently hand-calculated output (no negative reserves or free money).
- G10: $1k/$10k/$100k sales in thin reserves → non-linear worse effective fills; result changes with *own* position size.
- G11: Same reported USD liquidity but distinct CLMM concentration → cannot reuse CPMM approximation as accurate; refuse or true tested bin/tick math.
- G12: Pool drained between signal and order → modeled delay/failed fill/gap, not idealized prior price.
- G13: Partial route fails; only executable path counts; failure penalties included and no phantom fills.
- G14: Buy and sell fees, Token-2022 transfer fee/withheld balances, token decimals, swap fee, network fee and fee-authority change modeled with clear source fields or explicit unsupported labels; double counting prohibited.
- G15: Stale Jupiter quote → report STALE/UNKNOWN and do not treat as historic fill.
- G16: Stablecoin depeg, SOL/USD conversion change and multi-hop path → consistent P&L denominators.
- G17: Small quote may execute but full position cannot exit within max-impact constraint → available profit estimate constrained by exits.

## TA & catalyst

- G18: Breakout wick vs confirmed close vs failed retest → exactly defined signals; prove no pivot/repaint hindsight.
- G19: Insider supply sells, price holds, then selling dries → distinguish observed sales, interpretation of absorption and subsequent outcome; no proof of a future rise.
- G20: Coordinated social posts from one original source → no independent confirmation multiplicity.
- G21: High social activity after price rally → can't train on later attention as if a prescient catalyst.
- G22: Negative control: shuffled catalyst times should weaken claimed relationship; test remains meaningful with no discovered edge.
- G23: Conflicting sentiment, verified on-chain selling and low depth → do not turn positive posts into an unconditional buy.

## Portfolio/statistics/stress

- G24: 50 candidate signals same minute competing for limited account capital and liquidity → conserve cash and risk limits.
- G25: Stop price gaps through and cannot execute at threshold → real realized-loss scenario may exceed intended stop risk.
- G26: Tiny sample with huge win rate and leaked labels → abstain from significance claims.
- G27: Multiple parameter trials / nested tuning → seal test sample and report winner's curse/uncertainty, not best in-sample only.
- G28: Benchmark buy/hold and simple random/no-trade or naive baseline under identical execution costs and eligible universe.
- G29: Paired engine validation (pure independent math vs chosen framework) yields reconciled ledgers on deterministic cases.
- G30: Extreme stress: liquidity 75% withdrawn, insider cluster sells, transfer fee increases, volatility gap and transaction failure → coherent worst-case handling, no negative impossible outputs.
- G31: Brand-new token with no token history → never claim token-specific historical validation; analog-cohort stress with evidence or `INSUFFICIENT_HISTORY`.
- G32: Historical discovery timestamp replayed with frozen information, then daily outcome reconciled and ranked report reproduced byte-for-byte or within documented stable tolerances.
- G33: Existing `scout` / `analyze` tests still pass unchanged and research-only guard rejects any live-order hook.
- G34: Missing/blocked provider still produces a useful, explicit degraded report without blanking the entire candidate or fabricating a backtest.
- G35: Dramatically profitable *paper* strategy becomes negative after realistic exit costs; engine must surface deteriorated ranking rather than retain optimistic recommendation.

## Maxun conditional robot and collector tests — required in phases 06A, 09 and 16

- **G36: History laundering.** A newly crawled announcement has an old publication timestamp. The strategy never uses it at the old cutoff unless verified contemporaneous availability exists; mark `UNKNOWN_AS_OF`.
- **G37: Cross-collector dedup & page revision.** Maxun and Firecrawl/Crawl4AI (or existing collector) scrape one origin; they create one canonical original event; later corrected page becomes a distinct timestamped immutable version, not overwrite or spurious independent confirmation.
- **G38: Identity and spoof resistance.** Same ticker on a different chain/mint, counterfeit exchange announcement or copycat domain does not produce a verified catalyst for the genuine token; preserve original claim and corroboration status.
- **G39: Robot reliability and source bounds.** Test schema/selector drift, 401, 429, timeout, partially successful runs, outage, off-allowlist traversal and retry budget. No uncontrolled recursion, secret exposure, invented event or failed-source bullish signal.
- **G40: API, webhook and scheduling safety.** Distinguish OSS from Cloud endpoint and auth; reject spoofed/replayed webhook, enforce idempotent polling fallback, prevent unapproved standing schedules/paid calls, and prove stop/disable capability.
- **G41: Measured adoption and integration.** If ADOPT, reproduce authorized robot → real run → API/MCP/SDK result → existing source registry → eligible as-of feature → report/alert without placing an order. If NO_GO, verify measured comparison, tested alternative and no dead dependency. If BLOCKED, mark explicitly and validate fallback; don't claim a live Maxun feature on fixture-only evidence.



## Minimum phase-16 adversarial run

Run G01–G41, include at least three realistically dated historical cases with full provenance (not synthetic), at least one collapsed/rugged token, one catalyst that failed, one that preceded a positive outcome, and one freshly detected opportunity without enough history. If such live data cannot be fetched, release classification is **historical source integration BLOCKED** regardless of synthetic pass results.
