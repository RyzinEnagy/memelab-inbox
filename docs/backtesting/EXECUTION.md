# Backtesting and stress testing: execution contract

The binding contract is the prompt package copied verbatim into [`workplans/backtesting/`](../../workplans/backtesting/) (v1.2, 32 files, sha256 checked against its `MANIFEST.json` on 2026-10-23). Read `START_HERE.md` and `EXECUTION_RULES.md` there first. This file records how that contract is applied in this repository.

## Namespace

- Governance: `docs/backtesting/` (this file, `ROADMAP.md`, `DECISIONS.md`, `HANDOFF.md`, operator docs).
- Evidence: `audits/backtesting/` (phase notes, `research/`, `data/`, `testing/`, `testing/logs/`).
- Code: `memelab/backtest/` (new package). Tests: `tests/test_backtest_*.py`. Fixtures: `tests/fixtures/backtest/`.
- The social-intelligence governance files in `docs/social-intelligence/` belong to a different project and are not edited.

## Every phase

1. Read `docs/backtesting/HANDOFF.md`, `ROADMAP.md`, `DECISIONS.md`, this file and the phase file.
2. Re-run the predecessor's gate command recorded in HANDOFF. A failure there stops the phase.
3. Work only on `feature/backtesting`. Bounded loop of at most five passes: inspect, change, test (positive, negative, leakage, regression), adversarial review, repair, rerun.
4. Save command, exit code, UTC time, commit and fixture hash under `audits/backtesting/testing/logs/`.
5. Update HANDOFF, ROADMAP (with a reason when it changes) and DECISIONS. Commit locally.

## Regression checks (every phase that changes code)

```
python -m pytest tests -q -p no:cacheprovider        # baseline: 1 failed (C-1, clock dependent), 785 passed
python tools/release_audit.py                        # "Needs action: no"
python tools/release_e2e.py --out e2e.md             # "Result: PASS" (tests the committed HEAD, so commit first)
```

The EVM test writes `data/reports/<stamp>_BRETT_*.md`; delete it after each run so the tree stays clean.

## Status words

PASS, FAILED, BLOCKED, NEEDS_REVIEW, DEFERRED, PROVISIONAL, as defined in `EXECUTION_RULES.md`. Machine states for assessments: COMPLETE, PARTIAL_WITH_LIMITATIONS, INSUFFICIENT_HISTORY, INSUFFICIENT_EXECUTION_DATA, UNSUPPORTED_POOL, STALE_DATA, INVALID_TOKEN_ID, UNVERIFIED_CATALYST, RISK_FATAL_FLAW, SOURCE_BLOCKED, ERROR.

## Hard limits

No wallet, key, signing, order or swap-transaction code. No push to `main`, no merge, no paid API beyond the budgets Elving approved on 2026-10-23 (Firecrawl about 100 calls, Maxun Cloud one-shot runs within its 5 trial credits, local Crawl4AI). No standing schedules. No destructive migration. Secrets are never printed, logged or committed.

## Push route

The session git proxy refuses `git push` (social-intel HANDOFF). Approved route for this project (Elving, 2026-10-23): push `feature/backtesting` only, fast-forward, no force, through the Composio GitHub connection (Git Data API), and also drop a git bundle and zip in `D:\memelab` on the work computer. No pull request merge.
