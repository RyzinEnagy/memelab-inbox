# Predictive Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Phase 00 evidence: `audits/predictive-intelligence/phase_00/` (PHASE_00_EVIDENCE.md, PHASE_00_RESULTS.json, baseline/, probes/, SKEPTIC_PACKET.md). Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position

- Phase completed: 00 (authoritative repository baseline), 2026-10-24. Status NEEDS_REVIEW: every baseline item reproduced; the independent skeptic could not be started inside the phase run (PI-D-009).
- Branch `feature/predictive-intelligence`. Start HEAD `f99c6c7`, clean. Phase 00 commit: see "Commit" below.
- No production code changed. Nothing under `inbox/`, `state/` or `data/` changed. Not pushed (the orchestrator pushes, PI-D-003).
- Spend: 0 credits.

## What the baseline found

- Authoritative code line: this branch (`f99c6c7` contains `main`'s code `f084b60` and social-intel 19 to 21). The scheduled runs execute `main`'s code and rebuild from `main`; code from this branch reaches them only after a merge, which is Elving's call (PI-D-005).
- Real history: 17 days of sparse thesis snapshots (1,801 across 89 daily-ish exports, 248 mints, 93 with 2 or more priced snapshots) plus candles for 33 pools from 2026-10-06 to 2026-10-08. No candles, pool snapshots or quotes are kept after 2026-10-08. Launch-cohort outcomes exist for 8 of 1,422 launches.
- Free GeckoTerminal OHLCV reaches back to pool creation for a recent pool (about 10 calls a minute per its current spec); DEX Screener is current-state only.
- Existing reusable pieces: social signal ledger and outcome engine (outcomes_core.py), event study (alpha_core.py), causal replay with leakage proof (replay_core.py). No forecaster, calibration, proper scoring or model registry exists.
- Backtesting & Stress-Testing v1.2: not on any branch, not in uploads or project knowledge: BACKTEST_NOT_AVAILABLE (PI-D-006).
- Identity: tables key on mint; 102 symbols are shared by 2 or more real mints; the catalyst matcher can link a mint from a ticker alone (MODERATE), so TICKER_MATCH and NAME_MATCH are not identity here (PI-D-007).
- Lineage: the HIGGS report of 2026-10-07 00:16 UTC is reproduced line for line by the code of that day (`b6c424d`) on the full input set; current code changes pool facts, and a partial input set changes score and status. Theses record neither inputs nor code version (PI-D-008).
- Untrusted text is handled as data in social extraction, feeds and Firecrawl page reads (tests cited in the evidence); a hostile page can still name a contract that becomes a STRONG link.

## Tests

- Baseline: `python -m pytest tests -q -rs -p no:cacheprovider` exit 1, `1 failed, 785 passed in 133.57s (0:02:13)`, 786 collected, 0 skipped. Only failure: `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known, clock dependent).
- After the records were written (exact command, 2026-10-24T00:49Z): `python -m pytest tests -q` exit 1, `1 failed, 785 passed in 132.19s (0:02:12)`, same single failure.
- `python tools/release_e2e.py --out <scratch>/e2e.md` in a clone: exit 0, `Result: PASS. Stages with the expected exit code: 78 of 78. Network attempts: 0. Tracked files changed in the clone: 0. Tracked database byte-identical: yes.`
- Strays after each suite run: `data/reports/<stamp>_BRETT_0x532f.md` (tests/test_evm.py), `data/memelab.sqlite-shm` and an empty `-wal` (ignored). Removed by hand; `git status` clean.

## Blockers and open items

- Independent skeptic for Phase 00 (orchestrator, from SKEPTIC_PACKET.md).
- Windows-side checks BLOCKED for verification: `D:\memelab\crawl4ai-token.txt`, any Crawl4AI or Maxun install, the scheduled task definitions, the Firecrawl key file. Nothing assumed present or absent; no token read.
- Whether GeckoTerminal keeps candles for pools whose liquidity was pulled is UNKNOWN (one inactive pool checked).

## Approvals needed

None new for Phase 01 as scoped by the package. Any later paid data, LLM, Zep or MiroFish use, scheduled collection, or a merge into `main` needs Elving (PI-D-005).

## Next

Next eligible phase: 01 (gap analysis, placement and prediction requirements), only after the orchestrator's independent skeptic review of Phase 00 is recorded and Phase 00 is marked PASS. Phase 01 starts by re-running `python -m pytest tests -q` (expect `1 failed, 785 passed`) and reading `audits/predictive-intelligence/phase_00/baseline/DATA_COVERAGE.md` and `EXISTING_PREDICTION_INVENTORY.md`.

## Commit

Pending in this file until the Phase 00 commit exists.
