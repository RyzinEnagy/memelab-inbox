# Predictive Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Phase 00 evidence: `audits/predictive-intelligence/phase_00/` (PHASE_00_EVIDENCE.md, PHASE_00_RESULTS.json, baseline/, probes/, skeptic/, SKEPTIC_PACKET.md marked USED). Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position

- Phase completed: 00 (authoritative repository baseline), 2026-10-24. Status PASS after repair pass 2. It was NEEDS_REVIEW at `dea735c` because the independent skeptic could not be started inside the phase run; the orchestrator ran it (PI-D-013) and its findings were folded in.
- Branch `feature/predictive-intelligence`. Commits on top of `f99c6c7`: `59a2cfc` (content), `dea735c` (hash record), then the repair pass 2 commit (see "Commit").
- No production code changed. Nothing under `inbox/`, `state/` or `data/` changed. Not pushed (the orchestrator pushes, PI-D-003). Spend: 0 credits.

## What the baseline found

- Authoritative code line: this branch (`f99c6c7` contains `main`'s code `f084b60` and social-intel 19 to 21). The scheduled runs execute `main` (code `f084b60`); code from this branch reaches them only after a merge, which is Elving's call (PI-D-005).
- Real history: 17 days of sparse thesis snapshots (1,801 across 89 exports, 248 mints, 93 with 2 or more priced snapshots) plus candles for 33 pools from 2026-10-06 to 2026-10-08. No candles, pool snapshots or quotes are kept after 2026-10-08. Launch-cohort outcomes exist for 19 (24 h), 8 (7 d) and 2 (30 d) of 1,422 launches; `rug_flag` is NULL everywhere.
- Clocks (corrected after the skeptic, PI-D-011): `theses.created_at` and every other `t`-stamped column are the start time of the newest collector run behind the thesis, not when the thesis existed. The row is written later: for 149 of 248 mints the first thesis was written a median 16.9 min (p90 28.7, max 116.5) after its `created_at`, and its inputs can be about 50 min older than `created_at`. `tokens.first_seen_at` / `last_seen_at` are wall-clock write times.
- Free GeckoTerminal OHLCV reaches back to pool creation for a recent pool (about 10 calls a minute per its spec); DEX Screener is current state only.
- Reusable pieces: the social signal ledger and outcome engine (outcomes_core.py), the event study (alpha_core.py), the causal replay with leakage proof (replay_core.py), and social claim records with stance and horizon. No forecaster, calibration, proper scoring or model registry exists.
- Backtesting & Stress-Testing v1.2: not anywhere reachable: BACKTEST_NOT_AVAILABLE (PI-D-006).
- Identity: tables key on mint; 102 symbols are shared by 2 or more real mints; catalyst ticker or name links and symbol-only catalyst alerts are not identity here (PI-D-007, PI-D-012).
- Lineage: the HIGGS report of 2026-10-07 00:16 UTC is reproduced line for line by the code of that day (`b6c424d`) on the full input set; theses record neither inputs, code version nor module failures (PI-D-008, FEATURE_TRACE gaps 1 and 6).

## Independent skeptic (orchestrator-run)

- Review and script: `audits/predictive-intelligence/phase_00/skeptic/`. 1 MATERIAL (F1, clocks) and 5 MINOR findings (F2 launch-cohort counts from a probe bug, F3 second symbol-only path, F4 social claim forecasts missing from the inventory, F5 module crash not on the thesis, F6 wording and definitions). All verified and corrected in repair pass 2.
- Its counterexample: treating `theses.created_at` as decision time puts a 300 s entry before the score existed and a `first_seen_at <= cutoff` filter drops mints that already had theses. Caught now by `skeptic/skeptic_00_checks.py` section 2; Phase 05 must turn it into an executable fixture test (PI-D-011 rule 3).
- The state-history probe is a summary tool, not a label builder (its docstring and DATA_COVERAGE.md say so; row selection fixed).

## Tests

- Baseline at `f99c6c7`: `python -m pytest tests -q -rs -p no:cacheprovider` exit 1, `1 failed, 785 passed in 133.57s`, 786 collected, 0 skipped.
- After repair pass 2 edits (2026-10-24T01:17Z): `python -m pytest tests -q` exit 1, `1 failed, 785 passed in 132.73s (0:02:12)`. Only failure: `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known, clock dependent). The orchestrator's independent rerun on `dea735c` gave `1 failed, 785 passed in 134.90s`.
- `python tools/release_e2e.py` in a clone: exit 0, `Result: PASS. Stages with the expected exit code: 78 of 78. Network attempts: 0.`
- Strays after each suite run: `data/reports/<stamp>_BRETT_0x532f.md` (tests/test_evm.py), `data/memelab.sqlite-shm`, an empty `-wal`, `.pytest_cache/`. Removed by hand; tracked DB sha256 `068287c0...a6679ca` unchanged.

## Blockers and open items

- Windows-side checks remain BLOCKED for verification: `D:\memelab\crawl4ai-token.txt` (not read), any Crawl4AI or Maxun install, the scheduled task definitions, the Firecrawl key file. Nothing assumed present or absent.
- Whether GeckoTerminal keeps candles for pools whose liquidity was pulled is UNKNOWN (one inactive pool checked).

## Approvals needed

None new for Phase 01 as scoped by the package. Paid data, LLM, Zep or MiroFish use, scheduled collection, or a merge into `main` need Elving (PI-D-005).

## Next

Next eligible phase: 01 (gap analysis, placement and prediction requirements), after the orchestrator verifies this repair pass. Phase 01 starts by re-running `python -m pytest tests -q` (expect `1 failed, 785 passed`) and reading DATA_COVERAGE.md (especially "Clocks"), EXISTING_PREDICTION_INVENTORY.md and DECISIONS.md PI-D-006 to PI-D-013.

## Commit

- Phase 00 content commit `59a2cfc5bc21685607cfa9ee15e40e35ef24b119`; hash record `dea735c7ecf537eebb96c5358fb902cfef7c3fdd`; repair pass 2 is the next commit on top (read it with `git log -1`; this file is part of it, so it cannot hold its own hash).
- `git diff --name-only f99c6c7..HEAD` lists only files under `docs/predictive-intelligence/` and `audits/predictive-intelligence/`.
- Not pushed. `git status` clean after the commit.

## Exact next command

```
cd /home/claude/memelab-inbox && git checkout feature/predictive-intelligence && git log -4 --oneline && python -m pytest tests -q
```

Expect the three Phase 00 commits on top of `f99c6c7` and `1 failed, 785 passed`; then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm`, `-wal` and `.pytest_cache/` by hand.
