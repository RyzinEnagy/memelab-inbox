# Backtesting and stress testing: handoff

Rewritten at the end of every phase. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Package: [workplans/backtesting/](../../workplans/backtesting/).

## Position

- Phase completed: 00 (repository baseline and architectural truth), 2026-10-23. State: PASS.
- Baseline SHA: f99c6c74f00f52fb9e8f1259227a63994a419a5d (`feature/catalyst-firecrawl`). Branch: `feature/backtesting`.
- Changed files: new only (`audits/backtesting/**`, `docs/backtesting/**`, `workplans/backtesting/**`). No change under `memelab/` or `tests/`.

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests -q -p no:cacheprovider` | 1 | 1 failed (C-1), 785 passed |
| `python tools/release_audit.py` | 0 | Needs action: no |
| `python tools/release_e2e.py --out e2e.md` | 0 | Result: PASS, 78 of 78 |
| `python audits/backtesting/testing/p00_counterexamples.py` | 0 | 3 of 3 reproduced |

## Proven

End-to-end route traced (00_BASELINE section 3); module and table inventory (CURRENT_FUNCTIONALITY.md); three real defects reproduced by script; Firecrawl and Crawl4AI working; Maxun Cloud authenticated (TRIAL, 5 credits, 0 robots, 0 schedules); the lab's own exported history is a usable point-in-time universe.

## Not proven / limitations

No historical pool reserves, ticks or bins from free sources. Maxun not run yet. GitHub REST blocked per repo by the proxy (clones work).

## Surprises

The workspace reaches GeckoTerminal, DexScreener and Jupiter directly (the README says it cannot). `data/memelab.sqlite` is tracked in git despite the ignore rule.

## Next eligible phase

01. First action: build the requirements matrix against `workplans/backtesting/references/REQUIRED_DATA_CONTRACTS.md` and G01 to G35 using CURRENT_FUNCTIONALITY.md.

## Roadmap changes

None.
