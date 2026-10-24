# Phase 04 skeptic packet

For the orchestrator's independent skeptic (PI-D-013). Task: falsify Phase 04 (adoption, install, adapter or build bake-off). This packet lists artifacts, code paths and commands; it states no conclusions to accept. Read `/home/claude/pi_orchestration/SKEPTIC_BRIEF.md`, the phase prompt `phases/PHASE_04_adoption_install_adapter_or_build_bakeoff.md`, `EXECUTION_RULES.md`, the references `MIROFISH_EVALUATION.md`, `SCIENTIFIC_VALIDATION.md`, `DATA_TIME_CONTRACT.md`, `NO_GO_DECISION_TREE.md`, `ADVERSARIAL_SCENARIOS.md`, and `docs/predictive-intelligence/DECISIONS.md` (PI-D-016, PI-D-018, PI-D-021, PI-D-028 to PI-D-034).

## Artifacts (paths relative to `audits/predictive-intelligence/phase_04/`)

- `ACCEPTANCE_CHECKLIST.md` (B1 to B22, written before any change; one dated amendment)
- `adoption/BAKEOFF.md`, `adoption/BAKEOFF_RESULTS.json`, `adoption/INSTALL_DECISION.md`, `adoption/BOM_LOCKS.md`, `adoption/MIROFISH_FEASIBILITY.md`
- `adoption/data/`: `dev_sample_plan.json`, `dev_sample_calls.json` (132 GeckoTerminal calls), `dev_sample_summary.json`, `dev_t1_24h.csv`, `dev_t1b_6h.csv` (BAKEOFF_ONLY labels)
- `adoption/prototypes/`: `build_dev_sample.py`, `core_numpy.py`, `bakeoff.py`, `measure.py`, `run_measurements.py`, `summarize.py`, `render_tables.py`, `import_probe.py`, `calibration_check.py`, `splitter_check.py`, `drift_check.py`, `schema_check.py`, `behavior_check.py`, `error_semantics.py`, `mirofish_adapter.py`, `hostile_setup_demo.py`, `rollback_demo.py`, `build_lock.py`, `render_bom.py`, `wheel_licenses.py`, `build_copyleft_fingerprints.py`, `mutation_runtime.py`, `holdout_candle_check.py`, `banned_scan.py`, `write_results.py`
- `adoption/evidence/`: `measure/*.json` (every measured run), `outputs/*.json` (third runs), `first_real_run_failures/`, `strace/`, `error_semantics.json`, `mirofish_adapter_runs.json`, `hostile_setup_demo.json`, `rollback_demo.json`, `mutation_runtime.json`, `holdout_candle_check.json`, `wheel_licenses.json`, `wheel_availability.json`, `wheelhouse_check.txt`, `banned_scan.json`, `research-py313.bom.json`, `core-py313.bom.json`, `research-py313.in`, `research-py313.overrides.txt`, `bakeoff-bundle.in`
- `postcommit/` (suite, content guard and release audit run after the commit)
- `PHASE_04_EVIDENCE.md`, `PHASE_04_RESULTS.json`

## Code outside the phase folder

- `memelab/predictive/runtime.py` (new) and `tests/test_predictive_runtime.py` (new), `tests/fixtures/predictive/copyleft_fingerprints.json` (new)
- `docs/predictive-intelligence/locks/core-py313.txt`, `research-py313.txt` (new)
- unchanged and relied on: `memelab/predictive/contract.py`, `memelab/predictive/decisions.py`, `tests/test_predictive_contract.py`

## External state the claims rest on

- Raw GeckoTerminal bodies: `/home/claude/pi_research/p04_gt_raw/` (their sha256 are in `dev_sample_calls.json`).
- Venvs: `/home/claude/pi_research/venvs/p04_bundle`, `p04_core`, `p04_mesa`, `p04_mirofish`, Phase 03's `ip200__venn-abers`; lock inputs and wheelhouses `/home/claude/pi_research/p04/` (`wh_linux`, `wh_win`, `wh_mac`, `pypi_versions/`, `bakeoff-bundle` lock in the session scratchpad).
- Pinned clones: `/home/claude/pi_research/src/666ghj__MiroFish` (`7657031a`), `bancaditalia__black-it` (`6577b3cc`), `eslazarev__purged-cross-validation` (`07692dd8`), `ip200__venn-abers`.
- Exports: `git show 98338a8:data/state/latest.json` and its first-parent history.

## Commands to reproduce (from your own clone; `adoption/prototypes/` as the working directory where relative)

```
python -B build_dev_sample.py label ../data /home/claude/pi_research/p04_gt_raw   # offline relabel; diff the CSVs
python -B holdout_candle_check.py /home/claude/pi_research/p04_gt_raw
python -B banned_scan.py /tmp/banned.json
python -B run_measurements.py approaches    # or a single run: <venv>/bin/python -I -B bakeoff.py dev24 LR_NUMPY --min-train 30
python -B summarize.py
/home/claude/pi_research/venvs/ip200__venn-abers/bin/python -B calibration_check.py oracle
/home/claude/pi_research/venvs/p04_bundle/bin/python -B splitter_check.py
python -B mutation_runtime.py /tmp/mut.json
python -B hostile_setup_demo.py /tmp/hostile.json         # needs root for unshare -n
python -B rollback_demo.py /home/claude/pi_research/p04/wh_linux /tmp/rollback.json
python -B mirofish_adapter.py /tmp/mf.json                # about 1 minute; needs the p04_mirofish venv
python -m pytest tests/test_predictive_runtime.py tests/test_predictive_contract.py -q
python -m pytest tests -q && python -m memelab social guard && python tools/release_audit.py --history   # repository root
```

## Questions worth attacking

- Holdout seal: can any holdout or holdout-contacted decision, or any price of the holdout window, have influenced a file, a number or a decision in this phase? Check the request windows, the inclusive `before_timestamp` behaviour, the dropped candles and the decision filter in `build_dev_sample.py`.
- Labels and features: re-derive a few labels by hand from the raw bodies against the frozen registry (reference candle and its lag, gap, path start, AMBIGUOUS_BAR, thinning after eligibility). Is any feature available only after its decision?
- Do the approaches really share rows and folds? Is the fold audit able to fail, and does it check what the frozen walk-forward rule requires (training cutoff, label maturity)?
- Are the equivalence claims (numpy logistic, Platt and Venn-Abers against scikit-learn and the reference package) true on inputs the probes did not cover (ties, extreme scores, separable data, weights)?
- Are the measured costs, the network counts and the determinism claims what the raw `measure/*.json` files show? Could a library phone home through a path the audit hook and strace would miss?
- Install route and locks: does `--require-hashes --only-binary=:all: --no-deps` with these files really refuse an sdist, an unlisted package and a changed wheel on every platform? Is any hash in a lock not a PyPI digest? Does the rollback leave anything behind?
- `runtime.py`: can any absent component still crash, read a key, or count as available when it is not? Do the tests fail for real defects (mutate it yourself)? Does any existing module import it?
- P31: could AGPL code enter the lab without the copyleft gate noticing (short copies, reformatted code, other file types)? Are the fingerprints really hashes only?
- MiroFish: does any deliverable give it a probability, an accuracy or a role in the forecast? Is the adapter's AGPL boundary sound?
- Decisions: is any INSTALL, ADAPTER, REJECT or DEFERRED unsupported by a measurement, or does any contradict Phase 03's banned defaults or REJECT routes?
- Construct one new wrong-but-plausible counterexample and show which check catches it, or that nothing does.
