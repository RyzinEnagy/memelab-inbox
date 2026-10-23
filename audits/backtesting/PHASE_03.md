# PHASE 03: source-code due diligence and ranked top 10

State: PASS. Date 2026-10-23. Entry gate: Phase 02 PASS (LONGLIST.csv 73 rows, SHORTLIST 25, raw search sha256 65e23b10... re-checked).

## Evidence

- research/REPO_REVIEWS/: 25 cards at pinned commits (every pinned sha equals the Phase 02 `git ls-remote` HEAD), file:line evidence, capability marks, fill/chronology analysis, scores, negative finding, disposition.
- research/smoke/: 49 files; real installs and runs for vectorbt, backtesting.py, bt, quantstats, alphalens-reloaded, nautilus (v1 and v2 rc7), freqtrade, jesse (py3.12, fails on 3.13), basana, hftbacktest, PolarBT (sandboxed, no network), purgedcv, uniswappy; recorded failures for trade-executor (Python <3.11 only) and pypbo (not packaged); formula re-derivations for Raydium, Orca, Meteora (SDKs not installed).
- research/RANKING.csv (25 rows, totals recomputed from grades), research/TOP10.md, research/LEGAL_LICENSE_GATE.md, research/BLIND_RESCORE.md.
- Firecrawl use so far in the project: 7 calls (budget about 100).

## Gate

| Item | Result |
|---|---|
| >= 20 source reviews at pinned commits | 25 |
| Rubric applied without tailoring; totals reproducible | yes: script recomputation equals every card |
| Blind challenge of 5 finalists, resolve > 10 point gaps | 5 random finalists (seed 20261023: Lean, backtesting.py, basana, purgedcv, sol-trade) plus the winner; largest gap 7.1 (basana); none > 10 |
| Winner's strongest weakness investigated | slotfish: one trade shape only; skips graduated tokens; strategies see the full tape (engine.rs:20-27) |
| License from files, not badges | yes (LEGAL_LICENSE_GATE) |
| No unlicensed or unevidenced integration recommendation | yes: nothing reaches 70; purpose-built engine with ideas only |
| Fewer than 10 adoptable: documented, not fabricated | yes: 0 adoptable; ten researched candidates ranked with status |
| Maxun kept out of ranking | yes |

## Negative review

Plausible claim: "a repo whose README promises AMM-aware slippage and has a passing test suite models AMM buys correctly." PolarBT's `AMMSlippage` uses v/(R+v) for buys (the sell formula) and its test asserts the resulting 1.5x instead of the correct 2.0x; reproduced in a network-isolated sandbox (smoke/nikkisora__PolarBT/output.txt, exit 0). Second: "flint provides Solana/Jupiter MEV research" is contradicted by docstring-only modules and a NotImplementedError fill model. Third: hftbacktest's binding accepts a temporary array and produced a fill at 4.6e18 with exit 0 (use-after-free). Each was caught by reading code at the pinned commit and, where safe, running it.

## Limitations

Stars could not be refreshed (GitHub REST blocked); they carry no score weight. Orca's proprietary license defines reading as use: flagged NEEDS_REVIEW for awareness; no code or text copied and no dependency planned.

NEXT ELIGIBLE PHASE: 04.
