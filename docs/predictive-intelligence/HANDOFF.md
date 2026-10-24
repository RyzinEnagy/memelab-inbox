# Predictive Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Phase 04 evidence: `audits/predictive-intelligence/phase_04/` (PHASE_04_EVIDENCE.md, PHASE_04_RESULTS.json, ACCEPTANCE_CHECKLIST.md, SKEPTIC_PACKET.md, skeptic/, adoption/). Earlier phases stay in `phase_00/` to `phase_03/`. Spend: `audits/predictive-intelligence/COST_LEDGER.md`.

## Position

- Phase 04 (adoption, install, adapter or build bake-off): PASS, 2026-10-24, after the repair pass that folds in the orchestrator's independent skeptic (2 MATERIAL, 8 MINOR, `phase_04/skeptic/PHASE_04_SKEPTIC.md`; PI-D-035). Post-commit suite, content guard and release audit with history are clean (`phase_04/postcommit/`, `phase_04/PHASE_04_RESULTS.json`).
- Branch `feature/predictive-intelligence`, four Phase 04 commits on top of `a146a29`: first pass `4a19d71` and its records commit `84f8c86`, the repair commit `783fde4` and the records commit on top of it (read its hash with `git log -1`; this file is part of it). Not pushed. Spend 0 credits.
- Code added in Phase 04: `memelab/predictive/runtime.py` (standard library only, flag OFF, imported by no existing module), `tests/test_predictive_runtime.py`, `tests/fixtures/predictive/copyleft_fingerprints.json` (hashes only), `docs/predictive-intelligence/locks/` (two hash locks). The repair also changed `memelab/predictive/contract.py` in `enabled()` only (malformed config means OFF; registry fingerprint unchanged). No other file under `memelab/` or `tests/` changed; nothing under `inbox/`, `state/` or `data/` changed. The ignored venv `hazardous/` at the repository root was removed.

## What the repair changed

- M1, lock guard (P32). The skeptic's line `p04sk==1.0 ; python_version >= "3" --hash=sha256:<sdist> --only-binary=:none:` passed `check_lock`, and pip with the lab's flags then ran its `setup.py`, because pip honours per-line options. `check_lock` now accepts only `name==version`, an optional plain marker and `--hash=sha256:<64 hex>` tokens that are known wheel digests; `runtime.install_argv` is the only route and refuses before pip starts. Both of the skeptic's lines are test cases; `hostile_setup_demo.py` case E shows pip alone still runs the `setup.py` and `install_argv` refuses it. Lock sha256 pinned in the tests.
- M2, containment. `guarded` contains every exception including SystemExit; KeyboardInterrupt and GeneratorExit pass through on purpose. LLM actions count only as a positive int. Any config section that is not an object means OFF, in `capability_report` and in `contract.enabled`.
- m1, fold audit (prototype): fails closed on NaN times, a cutoff after the test start and, given the target's lag, a shorter-horizon maturity column; shared mints reported. `prototypes/test_core_numpy.py`, 9 tests.
- m2: the skeptic's 6 surviving mutations plus one or more per repair: 41 of 41 caught. P31 fixture declares its hash algorithm and normalization, checked at load, with a self-test text and a skip-if-absent positive control against the pinned MiroFish clone.
- m3 to m7: copyleft scan of every code file in the working tree (411); candles dropped by end time, the six holdout-start candles purged from the raw store with recorded hashes, `refuse_bakeoff_labels` plus a test; NaN or negative cost refuses calls, `is_failure` for returned error responses, dotted names refused; Platt on constant scores returns the exact optimum; the Venn-Abers oracle feeds both sides the same probabilities. m8: core lock header; the rollback reports the empty `mpl_toolkits/` directory it leaves (the documented rollback deletes the venv).
- The new tests fail on the first-pass code: runtime 88 failed of 135, prototype 8 of 9 (`evidence/old_code_check.json`). Re-measured bake-off: every prediction byte-identical to the first pass.

## What Phase 04 found (first pass, unchanged)

- Six approaches on one point-in-time dataset (BAKEOFF_ONLY development labels, T1 24 h 102 events, T1b 6 h 159, holdout untouched, plus the synthetic challenge), identical folds. Behaviour, cost and correctness only; 26 and 33 out-of-sample real events rank nothing on skill.
- The essential engine is numpy code equal to scikit-learn, the frozen sigmoid and the Venn-Abers reference, byte-identical in a numpy-only venv offline. Research packages live only in a hash-locked venv (PI-D-031, PI-D-032). pandera and Mesa REJECT; statsmodels, arch, crepes and interpret-core DEFERRED. MiroFish ISOLATED_MOCK_ONLY.

## How to check it

From `audits/predictive-intelligence/phase_04/adoption/prototypes/`:

```
python -B build_dev_sample.py label ../data /home/claude/pi_research/p04_gt_raw && git diff --stat -- ../data   # expect no diff
python -B holdout_candle_check.py /home/claude/pi_research/p04_gt_raw     # 0 candles ending after the holdout start
python -B summarize.py                                                     # not_identical_or_failed: []
python -B mutation_runtime.py /tmp/mut.json                                # 41 of 41 caught
python -B old_code_check.py /tmp/old.json                                  # runtime 88 failed, prototype 8 failed
python -m pytest test_core_numpy.py -q                                     # 9 passed
```

From the repository root: `python -m pytest tests/test_predictive_runtime.py tests/test_predictive_contract.py -q` (201 passed), `python -m memelab social guard`, `python tools/release_audit.py --history`.

## Tests

- Entry gate at `a146a29`: `1 failed, 858 passed in 145.42s`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known).
- First pass after `4a19d71`: `1 failed, 904 passed`. Orchestrator at `84f8c86`: `1 failed, 904 passed`.
- Repair pass, after the repair commit `783fde4`, on the committed tree: exit 1, `1 failed, 993 passed in 152.42s (0:02:32)` (858 earlier tests plus 135), only the known failure; `python -m memelab social guard` exit 0 with no violations; `python tools/release_audit.py --history` exit 0, "Needs action: no".
- Strays after each run: `data/reports/<stamp>_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal`; remove by hand; tracked DB sha256 `068287c0...` unchanged.

## Blockers and open items

- None. The orchestrator verifies the four Phase 04 commits and pushes.
- PI-D-020 (forward depth and quote collector) stays PROPOSED for Elving.

## Approvals needed

None for Phase 05. Paid data, LLM, Zep or MiroFish use, any scheduled collector (PI-D-020), copying AGPL or GPL code, accepting non-commercial weight terms, adding a research package to the lab's runtime, or a merge into `main` need Elving (PI-D-005, PI-D-032).

## Next

Next eligible phase after the orchestrator verifies Phase 04: 05 (immutable temporal evidence and feature store). It starts from PI-D-031 to PI-D-035 and the Phase 04 constraints in ROADMAP.md: install only through `install_argv`, drop candles by end time, pass every label source through `refuse_bakeoff_labels`.

## Exact next command

```
cd /home/claude/memelab-inbox && git checkout feature/predictive-intelligence && git log -5 --oneline && python -m memelab social guard && python -m pytest tests/test_predictive_runtime.py tests/test_predictive_contract.py -q && python -m pytest tests -q
```

Expect four Phase 04 commits on top of `a146a29`, `"violations": []`, `201 passed`, and `1 failed, 993 passed`; then remove `data/reports/*_BRETT_*.md`, `data/memelab.sqlite-shm` and `-wal` by hand.
