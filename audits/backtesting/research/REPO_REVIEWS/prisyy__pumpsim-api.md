# prisyy/pumpsim-api

- URL: https://github.com/prisyy/pumpsim-api
- Pinned commit: fd92630fec3e61b6faa4708122ea15001cb37d63 (2026-09-19T19:19:11+01:00), cloned 2026-10-23T15:52Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23 (no difference). `git ls-remote` shows a single ref (refs/heads/main).
- Category: crypto/DEX/Solana (README for a closed-source hosted simulation API)
- Discovery channel: GITHUB_API search "pump.fun backtest"
- Stars/forks (low weight, from search time): 0/n.a.
- License (from LICENSE file text, not badge): MIT (Copyright (c) 2026 prisyy) ; transitive notes: the MIT text covers only README.md; the simulator runs on api.pumpsim.dev under unknown terms of service.
- Package: none ; Python/OS: n.a. (HTTP API, JavaScript fetch example in README.md:21-40) ; native deps: n.a.
- Maintenance: single commit "Update README.md" adding 2 files, 78 lines (git log -1 --stat); no CI; no tests; no code.
- Security surface: no code to run. Using the product means sending order flow and strategy state to a third party with a bearer API key and credits (README.md:19-28, 42); unauthenticated demo endpoint documented (README.md:11-13), not called. Docs claim no wallet signing (Firecrawl scrape of https://docs.pumpsim.dev, 2026-10-23, 5 credits).

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | NOT_SUPPORTED | nothing in repo |
| tick/trade replay | DOCS_ONLY | docs claim replay of a real buy or sell from its transaction signature (docs.pumpsim.dev); no code |
| CPMM math | DOCS_ONLY | "real bonding-curve/AMM math, not an approximation" (README.md:47); no formulas or code |
| CLMM/DLMM math | NOT_SUPPORTED | not claimed |
| routes | NOT_SUPPORTED | not claimed |
| fees/taxes | DOCS_ONLY | docs claim creator fees, creator cashback, per-coin creator-fee overrides, Holder Rewards; no fee tiers or rates published on the landing page |
| thin exits / size-dependent impact | DOCS_ONLY | implied by curve math claims; unverifiable |
| fill timing (next bar, latency) | NOT_SUPPORTED | stateless quote calls; no latency or landing model documented |
| point-in-time guard / no lookahead | NOT_SUPPORTED | seeds from a coin's CURRENT reserves by mint or pool (README.md:49; docs `GET /sim/coin/{mint}`, `GET /sim/pool/{address}`); no historical as-of state |
| async event/catalyst injection | NOT_SUPPORTED | none |
| wallets/on-chain | DOCS_ONLY | live reserve lookup by mint is a remote call; no wallet |
| cross-token cohorts / portfolio | NOT_SUPPORTED | single-coin state chaining (README.md:32-42) |
| walk-forward / holdout / multiple testing | NOT_SUPPORTED | none |
| metrics/report | DOCS_ONLY | trader PnL claimed (README.md:3) |
| live trading code present (must be avoidable) | NOT_SUPPORTED | none in repo |

## Fill and chronology assumptions (read the code)

No code exists in the repository, so no fill path can be audited. Per README.md:42 each response returns `state`, `stats`, `fees` and `trade`, and the caller passes `state` back to chain trades, so any backtest built on it is the caller's own loop calling a remote black box. The documented data seeding is current on-chain state by mint (README.md:49), which cannot give point-in-time historical reserves. The docs page states every migrated pump coin carries BOOST dead-liquidity reserves of about 20.69% of effective quote, exposed as `virtual_quote_reserves`; this is the only concrete PumpSwap detail and it is useful as a pointer, not as evidence (upstream pump-fun/pump-public-docs at 639b87fb defines effective quote reserves = vault balance + virtual_quote_reserves).

## Smoke test (if feasible, no wallets, no network beyond pip)

```
not run: repository has README.md and LICENSE only; hosted API not called. See smoke/prisyy__pumpsim-api/output.txt
```
Outcome: not run (nothing executable).

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 1 | 3.00 | pump.fun curve, PumpSwap, custom quote pairs claimed (README.md:3, 48); marketing only |
| B microstructure | 17 | 1 | 3.40 | creator fees, cashback, boost reserves claimed in docs; unverifiable |
| C point-in-time | 15 | 0.5 | 1.50 | current-state seeding only; no as-of history |
| D catalyst/on-chain events | 11 | 0 | 0.00 | none |
| E TA/strategy flexibility | 9 | 0 | 0.00 | not a strategy framework |
| F statistical validation | 11 | 0 | 0.00 | none |
| G integration fit | 9 | 1 | 1.80 | remote HTTP API with key and credits; violates no-always-on-service and leaks order flow |
| H maintenance/tests | 6 | 0 | 0.00 | one README commit, no code or tests |
| I license/supply chain | 5 | 0.5 | 0.50 | MIT on a README; service code and terms unknown |
| J operational footprint | 2 | 0.5 | 0.20 | depends on a third-party SaaS and credits |
| Total | 100 | | 10.40 | |

Hard gates: no verifiable source; unknown license for the intended use (closed hosted service, ToS unknown). Kept only as RESEARCH_ONLY. Most important limitation for memecoins: no historical point-in-time reserves, so it cannot replay past decisions; it can only quote against current state. One credible negative finding: the repository presented as "pumpsim-api" contains no API code at all (2 files, 78 lines of README and LICENSE), so the "real curve math, not an approximation" claim (README.md:47) cannot be audited.
Disposition: REJECT. Suggested use: REJECT.
