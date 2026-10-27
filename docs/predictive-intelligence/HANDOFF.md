# Predictive Intelligence: handoff

Read this first. Contract: [EXECUTION.md](EXECUTION.md). Method used so far: [ORCHESTRATION.md](ORCHESTRATION.md). Plan and gates: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md) (PI-D-001 to PI-D-095). Evidence: `audits/predictive-intelligence/phase_00/` to `phase_17/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position on 2026-10-27

- Phases 00 to 13 and 16: PASS. Phases 14 and 15: TEST_ONLY (behavioral path, optional, OFF).
- Phase 17 (discovery and catalyst changes connected to a forecast or a visible abstention): **NEEDS_REVIEW**, first pass plus the self-review change control CP17-0 (PI-D-093 to PI-D-095). Every gate item holds on the agent's own checks; the orchestrator's independent skeptic has not run yet (`phase_17/SKEPTIC_PACKET.md`).
- Spend: 0 Firecrawl credits, 0 vendor calls, 0 language-model calls; every real-data command ran inside `unshare -n` or under a socket-refusing audit hook.

## What Phase 17 built

- The first change to existing lab code: `memelab/cli.py` gets `_predictive_section` (called in `cmd_scout` after the unchanged report body, before the file is written) and `_predictive_line` (after `cmd_analyze`'s line). Each imports `memelab.predictive.integration` lazily and returns None on any import failure. Flag `predictive.enabled` in `data/config.json` (gitignored) is off unless it is the JSON value true; off means nothing is read but the config, nothing is written, and the output is byte-identical (P40).
- `memelab/predictive/integration.py` (integration-1): one request record per trigger (DISCOVERY, MATERIAL_CHANGE, UNCHANGED, DUPLICATE, SUPERSEDED_IN_PASS, DEFERRED_*, NO_DECISION_SNAPSHOT, NOT_EXACT_IDENTITY, ERROR, CATALYST_REFRESH_REQUESTED); three documents and abstention-1 records per attempt with `contract.forecast_id`; `snapshot_hash` = the persisted thesis row's `row_sha256`; capture time as the decision time; the frozen material gate as of the capture (with each target's served model, pin and serve state); one attempt per mint and 64 per pass; 30 s budget; no socket; reads only for a served champion through `CallGuard` with cost cap 0; INPUT_STALE after 7,200 s; capture-store features; `registry.serve` then `abstention.forecast_result`; `check_document` and `verify_point` (Phase 13 m4 and m3 closed); decision support with every lab fatal flag and a backtest fatal or untradeable assessment as vetoes, no size from a forecast; append-only sha-checked state in `data/private/predictive/` (a state directory inside the repository elsewhere is refused); section; ops metrics; `python -m memelab.predictive.integration status|check|catalyst-pass`.
- `memelab/predictive/bt_adapter.py` (bt-adapter-1): read-only interface to the backtesting branch's assessment record and `bt_assessments` table (`origin/feature/backtesting` at `69bc5c3`), fixtures only.
- Isolation tests of Phases 01, 09, 13 and 16 amended to exactly the two seams, with negative cases. Found: the Phase 09 test cannot see relative imports, and `analog.py` imports `onchain` lazily (Phase 11 design); pinned, not changed.
- Tests: `tests/test_predictive_integration.py` (91), `tests/test_predictive_phase17_outputs.py` (9); mutation probe 59 of 59.

## Results (PI-D-095)

- Real scout in a sandbox (committed inbox bodies, the `71fc50e` export imported into a temporary lab database): flag off byte-identical to `b0fad12`; flag on, the body unchanged plus the section; 8 attempts, 24 documents all ABSTAIN (MODEL_NOT_SELECTED, UNCALIBRATED, INSUFFICIENT_HISTORY, SOURCE_STALE; inputs INPUT_STALE because the bodies are from 2026-10-07); rerun and retry 16 DUPLICATE and no new document; storm one attempt per mint; research mode 48 internal reference records.
- Export replay of the 52 prospective-window decision events (from 2026-10-24): 156 abstentions, the replay again 52 DUPLICATE and 0 documents.
- Three traced examples (PAID, GOMO with a CANNOT_EXIT_5K veto, a BSC token across three exports) and the fixture FORECAST path (TEST_ONLY).

## Open items, in order

1. The orchestrator runs the independent skeptic on Phase 17; the phase agent folds the review in (repair pass), then the orchestrator records the status and pushes.
2. Phase 18 (after a PASS): reports, CLI and alerts read the persisted state only through document and record pairs; keep the flag-off byte equality and the trading-word checks; show decision support and the registry and calibration states beside any document.
3. If Elving wants a promotion path: the change control to ACCEPTANCE `promotion` (PI-D-091), registered before prospective labels are read; then Phase 19's prospective evidence. A promoted champion would still abstain in integration-1 (family 07 only; INFERENCE_NOT_CHECKED for a real champion) until a change control adds its feature builder and probe inputs.
4. Frozen cards are MODEL_STALE after 2026-10-31T00:00:00Z; the internal reference records stop being current then.
5. Carried: catalyst and social tables are not exported (catalyst-triggered refreshes are exercised on fixtures only); forward depth collection approved but not deployed (PI-D-044); keep `tests/test_predictive_reproductions.py` green; a merge of the backtesting PR #4 needs the steps in `phase_17/integration/REQUEST_FLOW.md`.

## Phase 17 commits

HEAD before `b0fad12`; pre-registration `7f7bc28`; frozen code `3d2089b`; recorded outputs `6f4e8f7`; CP17-0 code `6172b49`; repeated outputs `30be448`; records after it; post-commit checks recorded in `phase_17/postcommit/` and in the commit that adds them. Local only; the orchestrator pushes.

## Waiting on Elving

- The change control that could reopen promotion (ACCEPTANCE `promotion`), any paid data, LLM, Zep or MiroFish use, scheduled catalyst or social collection into a store this engine can read, a merge of the backtesting PR #4 into this line, a merge into `main` (only then do the scheduled runs see the hook, and only with the flag on), deploying the forward depth collector (approved, PI-D-044; not yet done), and turning the flag on anywhere outside a sandbox.

## Note outside this branch

The release audit on a full local clone flags a history blob reachable only from `origin/feature/backtesting` (a reviewed false positive on that branch, D-BT-016; PI-D-049 item 6). It is not reachable from `feature/predictive-intelligence`, whose own audit passes on a single-branch clone.

## Lab rules that still bind

Research only: no trades, no wallets with signing authority, no seed phrases or private keys, no credentials printed or committed. No change under `inbox/`, `state/` or `data/` on this branch. Existing 100-point score and fatal-flag overrides unchanged. Forecasts stay a separate evidence section with the flag OFF by default. No raw social content in the repository. Behavioral output is fictional, never a probability. References are never forecasts.

## Exact next commands

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox
git checkout feature/predictive-intelligence && git log -12 --oneline
pip install pytest
python -B audits/predictive-intelligence/phase_06/probes/check_seal.py
python -m pytest tests -q
python -m pytest tests/test_predictive_integration.py tests/test_predictive_phase17_outputs.py -q
bash audits/predictive-intelligence/phase_17/probes/real_path_smoke.sh $(git rev-parse HEAD) /tmp/p17_smoke
python -B audits/predictive-intelligence/phase_17/probes/run_integration.py smoke /tmp/p17_smoke /tmp/p17_smoke/REAL_PATH_SMOKE.json
python -B audits/predictive-intelligence/phase_17/probes/run_integration.py replay /tmp/p17_replay
python -B audits/predictive-intelligence/phase_17/probes/mutation_integration.py /tmp/p17_mut.json
```

Use a full clone (the commit-order tests of Phases 15 to 17 fail on a shallow one by design) and fetch `origin/main` so `71fc50e` exists. Expect `"problems": []` from the seal check and only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` failing in the suite; then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand. The smoke script needs `unshare -n`.
