# <owner>/<repo>

- URL: https://github.com/<owner>/<repo>
- Pinned commit: <full sha> (<commit date ISO>), cloned <UTC time> with `git clone --depth 1`
- Category: <vectorized | event-driven | crypto/DEX/Solana | AMM math | catalyst/event | validation/metrics | other>
- Discovery channel: <GITHUB_API search "..." | curated list | Firecrawl developer search | citation from ...>
- Stars/forks (low weight, from search time): <n>/<n>
- License (from LICENSE file text, not badge): <SPDX or UNKNOWN> ; transitive notes: <...>
- Package: <PyPI name and version | none> ; Python/OS: <...> ; native deps: <...>
- Maintenance: last commit <date>; CI files <list or none>; tests <count of test files, framework>
- Security surface: <install scripts, network calls, wallet/key code, binaries, obfuscation>

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | SOURCE_CODE_VERIFIED / DOCS_ONLY / DEMO_ONLY / NOT_SUPPORTED / UNKNOWN | path:line |
| tick/trade replay | | |
| CPMM math | | |
| CLMM/DLMM math | | |
| routes | | |
| fees/taxes | | |
| thin exits / size-dependent impact | | |
| fill timing (next bar, latency) | | |
| point-in-time guard / no lookahead | | |
| async event/catalyst injection | | |
| wallets/on-chain | | |
| cross-token cohorts / portfolio | | |
| walk-forward / holdout / multiple testing | | |
| metrics/report | | |
| live trading code present (must be avoidable) | | |

## Fill and chronology assumptions (read the code)

<How a signal at bar t becomes a fill: which price, which bar, what slippage/fee model; whether indicators can see the current unfinished bar; stops intrabar behavior.>

## Smoke test (if feasible, no wallets, no network beyond pip)

```
<exact commands>
```
Outcome: <exit codes, key output, or why not run>

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | | | |
| B microstructure | 17 | | | |
| C point-in-time | 15 | | | |
| D catalyst/on-chain events | 11 | | | |
| E TA/strategy flexibility | 9 | | | |
| F statistical validation | 11 | | | |
| G integration fit | 9 | | | |
| H maintenance/tests | 6 | | | |
| I license/supply chain | 5 | | | |
| J operational footprint | 2 | | | |
| Total | 100 | | | |

Hard gates: <none | which>. Most important limitation for memecoins: <...>. One credible negative finding: <...>.
Disposition: PIP | VENDOR_EXCERPT_IF_LICENSE_APPROVED | REIMPLEMENT_IDEA | REFERENCE | REJECT. Suggested use: INSTALL | REFERENCE | ADAPT_WITH_LICENSE_REVIEW | REJECT.
