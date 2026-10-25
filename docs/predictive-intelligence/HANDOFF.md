# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-045). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_06/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position on 2026-10-25

- Elving stopped the run after Phase 06's first pass and asked for handoff records (PI-D-042). No later phase was started.
- Phases 00 to 05: PASS, each with an independent skeptic review and a repair pass folded in, re-verified by the orchestrator and pushed.
- Phase 06 (outcome labels and censoring): NEEDS_REVIEW with one item open, the frozen 48 h revision re-read (not before 2026-10-26T13:49Z). Elving asked to continue Phase 06 on 2026-10-25: the independent skeptic (1 MATERIAL test-coverage finding, 8 minor, counterexample CX-S06; all development counts reproduced independently) is folded in by repair pass 2 (PI-D-045, `phase_06/skeptic/`): 13 tests for frozen rules (44 of 44 mutations caught), orientation check for `token=<mint>` reads plus a P0 sanity flag, a stricter training gate, the seal manifest's own hash pinned, holdout call counts removed from public records. Relabel with the repaired code: 0 changes. Commits: first pass `4565e0b`, stop records `121384b`, repair pass 2 `2f4b53e` and its records commit on top; post-commit at `2f4b53e`: `1 failed, 1124 passed` (known failure only), guard 0 violations, release audit (this branch) exit 0, seal check 0 problems.
- Branch `feature/predictive-intelligence`: the repair-pass commits are local, not pushed (the orchestrator pushes). `main` untouched. No pull request.
- Spend: 0 Firecrawl credits; free GeckoTerminal calls only (counts per phase in COST_LEDGER.md; Phase 06's holdout calls are counted only inside `phase_06/sealed/`, PI-D-045 item 6).

## What exists now

- Targets frozen before any price data was read (Phase 01, fingerprint checked by tests): T1 +25% before -15% within 24 h; T1b the same within 6 h; T2 a fall to half the reference price or trading stopping within 24 h. Price-path labels only, no fill, size, depth or profit claims. The exit-adjusted target is BLOCKED (no historical depth); a liquidity target needs forward data: Elving approved forward depth and quote collection on 2026-10-25 inside the backtesting module's hourly tracker (D-BT-034), read here through an adapter; both targets stay deferred and unfrozen until enough forward data exists (PI-D-044).
- Decision unit and time: an exact thesis row, timed by the first state export on `main` that holds it (PI-D-015, PI-D-021). `theses.created_at` is never used as decision time (PI-D-011).
- Library choice (Phases 02 to 04): 132 repos found, 30 audited at pinned commits, ranked top ten with a blind rescore. The engine core is plain numpy and runs offline (PI-D-031). scikit-learn, LightGBM, MAPIE, lifelines and river stay in a research venv, never the lab's runtime. MiroFish scored 8 of 100: AGPL, needs paid LLM and Zep, runs do not repeat, reports success when the LLM is down; isolated mock-only, no paid use approved.
- Code (flag OFF, imported by no existing module): `memelab/predictive/` contract.py, decisions.py, runtime.py, store.py, sources.py, features.py, labels.py, with `tests/test_predictive_*.py`.
- Data: point-in-time feature store (1,500 decisions, 3,000 snapshots) and labels, rebuilt offline from committed raw GeckoTerminal bodies (`phase_05/raw/`, `phase_06/raw/`) plus git history. Development labels: T1 136 (34 positive), T1b 224 (26), T2 131 (28). Holdout labels are sealed in `phase_06/sealed/` (counts only; open only in Phase 12 after `check_seal.py`).
- The honest outlook stated in Phase 01 still holds: with about 9 decision days of development data from one market regime, the likely result is "no measurable skill over the base rate" or not enough history. Data from 2026-10-24 on is the real prospective test.

## New since Phase 00: a backtesting module on another branch

Another session built `memelab/backtest/` on `origin/feature/backtesting` (scenario-only CONDITIONAL RELEASE accepted by Elving, pull request #4 open, hourly shadow store on his computer at `D:\memelab\backtesting_live`). Phase 00's BACKTEST_NOT_AVAILABLE was correct when checked but is now partly out of date. Before Phase 07, read that branch and decide on an adapter so the two efforts do not keep two GeckoTerminal loaders or two outcome ledgers (PI-D-043).

## Open items, in order

1. Done 2026-10-25: Phase 06 skeptic and repair pass 2 (PI-D-045).
2. Phase 06 48 h revision re-read: `python -B audits/predictive-intelligence/phase_06/probes/make_labels.py reread48`, at or after 2026-10-26T13:49Z (it refuses earlier). It needs the development store; if the cloud workspace was reclaimed, rebuild the stores first from the committed raw archives (see `phase_05/data/FEATURE_STORE_CONTRACT.md` and `phase_06/labels/TARGET_SCHEMA.md`).
3. Fold the re-read's result into the evidence (a revision that changes a label is stored as a new row, PI-D-041); mark Phase 06 PASS only then (or after a recorded decision that moves the re-read), then push.
4. Reconcile with `feature/backtesting` (PI-D-043), then Phase 07 (transparent baselines).

## Waiting on Elving

- Any paid data, LLM, Zep or MiroFish use; adding research packages to the lab's runtime; a merge into `main`.

## Note outside this branch

The release audit on a full clone (all local branches) flags a blob on the local branch `work/backtesting-collector` (another session's worktree); it is not reachable from `feature/predictive-intelligence`, and that branch's owner reviews it before pushing (PI-D-045 item 7).

## Lab rules that still bind

Research only: no trades, no wallets with signing authority, no seed phrases or private keys, no credentials printed or committed. No change under `inbox/`, `state/` or `data/` on this branch. Existing 100-point score and fatal-flaw overrides unchanged. Forecasts stay a separate evidence section with the flag OFF.

## Exact next commands

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox
git checkout feature/predictive-intelligence && git log -3 --oneline
pip install pytest
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -m pytest tests -q
```

Expect `"problems": []` from the seal check and `1 failed, 1124 passed` from the suite (only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`, a known clock-dependent failure). Then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand.
