# Phase 04 evidence: adoption, install, adapter or build bake-off

Status: **NEEDS_REVIEW** (first pass complete; the orchestrator runs the independent skeptic, PI-D-013, and a repair pass folds it in before any PASS).

| Item | Value |
|---|---|
| Branch | `feature/predictive-intelligence` |
| HEAD before | `a146a29d17c47a0bdfdef85df2e7a9e2f884d50f` (Phase 03 records commit) |
| Phase start (UTC) | 2026-10-24T07:55:08Z (entry gate) |
| Acceptance checklist written | 2026-10-24T07:59Z, before any change (`ACCEPTANCE_CHECKLIST.md`, B1 to B22, one dated amendment at 08:20Z widening B16 to the P31 fixture and the lock folder) |
| Commits | deliverables commit `4a19d7135db809ed30f8bb5ce2390a800d1f92c3` (2026-10-24T09:04Z) and the records commit on top of it, which adds `postcommit/` and these results (its hash: `git log -1`) |
| Spend | 0 Firecrawl credits; free calls only (below) |

## Entry gate and standing checks

| Check | Command | Result |
|---|---|---|
| Package unchanged (B1) | `cd <package> && sha256sum -c SHA256SUMS.txt` | exit 0, every line OK |
| Entry gate (B2) | `python -m pytest tests -q` at `a146a29`, clean checkout | exit 1, `1 failed, 858 passed in 145.42s (0:02:25)`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known); strays `data/reports/20261024_0754_BRETT_0x532f.md` (from an aborted first start of the same command), `data/reports/20261024_0755_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal` removed by hand; `data/memelab.sqlite` sha256 `068287c0...` unchanged |
| System interpreter untouched (B11) | `pip freeze \| sha256sum` at the start and the end | `4bbf5c51faf183d2...` both times |
| Untracked state found, not this phase's | `git status --ignored` | an ignored uv venv `hazardous/` at the repository root, created 2026-10-24T06:48Z by an earlier session; left in place, not tracked |

## What was built and run (all under `adoption/` unless noted)

| Step | Command (from `adoption/prototypes/` unless noted) | Exit | Result |
|---|---|---|---|
| Decision plan | `python -B build_dev_sample.py plan ../data` | 0 | 521 development decision events, 95 PIT pools, from the 89 exports at `98338a8` |
| Price fetch (network) | `python -B build_dev_sample.py fetch ../data /home/claude/pi_research/p04_gt_raw` | 0 | 132 calls 08:02:05Z to 08:40:44Z: 115 HTTP 200, 17 HTTP 429 retried after 60 s; at most 6 calls in any 60 s window, minimum gap 11.1 s; largest `before_timestamp` equal to the holdout start |
| Labels (offline) | `python -B build_dev_sample.py label ../data RAW` | 0 | T1 24 h 102 events (30 positive), T1b 6 h 159 (23 positive); eligibility 502 / 17 / 2; 6 candles at the holdout start dropped; builder assertions on holdout and maturity pass |
| Holdout candle check | `python -B holdout_candle_check.py RAW` | 0 | 6 candles, 6 pools, 3 holdout decisions on them, 0 within the 4,200 s reference window: no holdout decision can use them |
| Venvs | `uv venv` + `uv pip install --require-hashes --only-binary :all: --no-deps` | 0 | `p04_bundle` (45 packages), `p04_core` (numpy only), `p04_mesa` (`mesa[network]`), `p04_mirofish` (Python 3.12, 132 packages incl. CPU torch 2.9.1) |
| Cold start | `python -B run_measurements.py imports` | 0 | 17 components x 5 fresh processes, all inside `unshare -n`, 0 socket events |
| Approaches | `python -B run_measurements.py approaches` | 0 | 39 runs (3 datasets x 9 bundle + 4 numpy-only) x 2, all exit 0, all deterministic |
| Checks | `python -B run_measurements.py checks` | 0 | 8 checks x 2; `behavior_mesa_plain_install` fails as expected (networkx) |
| Third runs and results | `python -B summarize.py` | 0 | `{"approach_runs": 39, "checks": 8, "not_identical_or_failed": []}`; `BAKEOFF_RESULTS.json` |
| Tables | `python -B render_tables.py ../BAKEOFF.md ../BAKEOFF_RESULTS.json`; `python -B render_bom.py ../BOM_LOCKS.md ../evidence/core-py313.bom.json ../evidence/research-py313.bom.json` | 0 | generated sections of BAKEOFF.md and BOM_LOCKS.md |
| Network syscalls | `unshare -n strace -f -e trace=connect,sendto,bind ...` | 0 | 0 for LGBM, COX_LIFELINES, HGB_SKLEARN, LR_NUMPY, drift and schema checks; positive control 1 |
| Error semantics | `p04_bundle/bin/python -B error_semantics.py > ../evidence/error_semantics.json` | 0 | table in BAKEOFF.md |
| Calibration oracle | `ip200__venn-abers/bin/python -B calibration_check.py oracle` | 0 | max difference 1.39e-17 |
| Banned defaults | `python -B banned_scan.py ../evidence/banned_scan.json` | 0 | 15 self-tested rules, 26 files, 0 hits, 1 allowed negative control |
| Locks | `uv pip compile ... --universal --generate-hashes --only-binary :all:`; `python -B build_lock.py IN OUT BOM CACHE` | 0 | research 30 packages / 63 hashes, core 1 / 4; 0 problems; `check_lock` 0 problems |
| Three-platform download | `pip download --require-hashes --only-binary=:all: --no-deps [--platform ...] -r <lock>` x 3 platforms x 2 locks | 0 x 6 | 30 wheels per platform, every sha256 in the lock (`evidence/wheelhouse_check.txt`) |
| Wheel licenses | `python -B wheel_licenses.py WH ../evidence/wheel_licenses.json` | 0 | 30 of 30 wheels carry license files; GPL or LGPL text only as bundled-runtime notices or references |
| Rollback | `python -B rollback_demo.py /home/claude/pi_research/p04/wh_linux ../evidence/rollback_demo.json` | 0 | 30 installed offline, smoke of 4 approaches exit 0, uninstall, `rollback_clean: true`; `pip check` reports only lifelines' `pandas<3` |
| Hostile setup (P32) | `python -B hostile_setup_demo.py ../evidence/hostile_setup_demo.json` | 0 | lab route refuses the sdist (marker not written) and the wrong hash; plain pip runs the sdist's setup.py (marker written) |
| MiroFish | `python -B mirofish_adapter.py ../evidence/mirofish_adapter_runs.json` | 0 | backend exit 1 without keys; 2 mock runs SIMULATION_RAN with different traces; LLM down: exit 0, SIMULATION_NOT_AVAILABLE |
| Copyleft fingerprints | `python -B build_copyleft_fingerprints.py tests/fixtures/predictive/copyleft_fingerprints.json` (repository root) | 0 | 5,393 fingerprints from MiroFish (82 files) and black-it (42 files) at their pins; 0 findings in the lab's 209 code files and the 25 prototypes; MiroFish files flagged |
| Runtime tests | `python -m pytest tests/test_predictive_runtime.py tests/test_predictive_contract.py -q` (root) | 0 | `112 passed` |
| Runtime mutations | `python -B mutation_runtime.py ../evidence/mutation_runtime.json` | 0 | 17 of 17 mutations make the tests fail; baseline 46 passed |

Before the commit, on the staged tree: `python -m pytest tests -q` exit 1, `1 failed, 904 passed in 142.75s (0:02:22)` (known failure only); content guard 0 violations; release audit exit 0. The results that count are the post-commit ones below (PI-D-030).

## Acceptance checklist results

| Id | Result |
|---|---|
| B1 | OK (above) |
| B2 | OK: `1 failed, 858 passed`, known failure only |
| B3 | OK: every component maps to a Phase 03 role and review id (BAKEOFF.md "Candidates and roles"); banned scan 0 hits |
| B4 | OK: one dataset family with identical folds; real sample from development decisions only, every request ended at the holdout start, 6 returned candles at the holdout start dropped and shown harmless, 0 holdout decisions labelled; pace at most 6 a minute; every call logged; raw bodies outside the repository. Synthetic challenge with the maturity purge |
| B5 | OK: six approaches (B0, numpy logistic, scikit-learn logistic, HGB, LightGBM, lifelines Cox) plus three calibration variants, same rows and folds, metrics with N, positives and folds, no edge claim |
| B6 | OK: fold audit with test-start and declared-cutoff checks; lab rule and purgedcv valid on all datasets; mutation refused on the challenge (2,304) and the 24 h sample (31) and a no-op on the 6 h sample (stated); TimeSeriesSplit refused on all three. The smallest training fold holds 16% (purgedcv on the challenge) to 79% of the labelled rows, above the 10% minimum; the real samples have only 4 and 5 folds |
| B7 | OK: Venn-Abers max difference 1.4e-17 (bound 1e-9); MAPIE port and prefit Pipelines absent (scan) |
| B8 | OK: cold start, peak RSS, CPU, audit-hook and strace network counts, determinism over three runs, wheels for Linux, Windows and macOS arm64 at each exact version, every run on numpy 2.5.3 and pandas 3.0.5, telemetry none found |
| B9 | OK: INSTALL_DECISION.md, a decision and fallback per component; the essential engine ran in a numpy-only venv offline with identical predictions |
| B10 | OK: two hash locks, 63 + 4 hashes equal to PyPI digests and to the downloaded files; offline install from a wheelhouse with the lab's flags; install route PI-D-032 |
| B11 | OK: rollback clean; system freeze unchanged |
| B12 | OK: MIROFISH_FEASIBILITY.md, ISOLATED_MOCK_ONLY, no probability, no paid call, no copied code, silent success caught, NOT_SUPPORTED for the paid route |
| B13 | OK: `runtime.py` standard library only, 46 tests, key guard on `os.environ`, 17 of 17 mutations caught, no existing module imports the package (existing AST test passes) |
| B14 | OK: 0 findings in the lab; injected header and copied block flagged (test) |
| B15 | OK: hostile setup demo; `check_lock` refusals (13 parametrized cases) |
| B16 | OK: `git diff --name-only a146a29..4a19d71` lists only `audits/predictive-intelligence/`, `docs/predictive-intelligence/`, `memelab/predictive/runtime.py`, `tests/test_predictive_runtime.py` and `tests/fixtures/predictive/copyleft_fingerprints.json`; no existing test changed; no new test needs a third-party package; post-commit suite shows only the known failure; strays removed; `data/memelab.sqlite` sha256 unchanged |
| B17 | OK: after the commit, on the committed tree: suite `1 failed, 904 passed`, content guard 0 violations, release audit exit 0 (below) |
| B18 | OK: no wheel, venv, pickle, weights, raw API body, token, file over 1 MB or social content in the phase folder (largest file under 500 KB); labels marked BAKEOFF_ONLY |
| B19 | OK: COST_LEDGER row, 0 credits |
| B20 | OK: records written; status NEEDS_REVIEW |
| B21 | OK: 180 new or changed files scanned before the commit for en and em dashes, curly quotes and 20 marketing words: 0 hits |
| B22 | two commits, no push |

## Post-commit results (deliverables commit `4a19d7135db809ed30f8bb5ce2390a800d1f92c3`)

| Check | Command | Exit | Result |
|---|---|---|---|
| Full suite | `python -m pytest tests -q` (09:04:41Z to 09:07:15Z) | 1 | `1 failed, 904 passed in 153.99s (0:02:33)`; only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known); 46 new tests pass; stray `data/reports/20261024_0904_BRETT_0x532f.md` and the sqlite `-shm` and `-wal` removed by hand; `data/memelab.sqlite` sha256 `068287c0...` unchanged |
| Content guard | `python -m memelab social guard` | 0 | `"violations": []` (1,175 files scanned) |
| Release audit | `python tools/release_audit.py --history` | 0 | "Needs action: no"; this phase adds two network-path rows without credentialed or paid hosts (`build_dev_sample.py`, `measure.py`) and no trade-execution or signing hit |
| System interpreter | `pip freeze \| sha256sum` | 0 | `4bbf5c51...`, unchanged since the start |

Files: `postcommit/pytest_summary.txt`, `postcommit/social_guard.out.txt`, `postcommit/release_audit_history.summary.txt` (summary only, PI-D-030), `postcommit/summary.json`.

## Sources

- GeckoTerminal public API, `https://api.geckoterminal.com/api/v2/networks/solana/pools/<pool>/ohlcv/minute?aggregate=5&limit=1000&before_timestamp=<t>&currency=usd` (132 calls, `adoption/data/dev_sample_calls.json`).
- PyPI JSON API, `https://pypi.org/pypi/<name>/json` (20 reads, one 404 for `purged-cross-validation` before the package name `purgedcv` was used) and `https://pypi.org/pypi/<name>/<version>/json` (37 reads).
- PyPI simple index and files through uv 0.11.32 and pip 24.0 / 26.2.2; CPU torch from `https://download.pytorch.org/whl/cpu` for the isolated MiroFish venv.
- Pinned clones (Phase 02/03): MiroFish `7657031ac01184afe2cb220f5ee3545573b5e843`, black-it `6577b3cc12d26be0eff1924694dd58ede7a5ae6e`, purged-cross-validation `07692dd862d37a988233e190706afb18c5101948`, ip200/venn-abers (Phase 03 venv).
- No Firecrawl, WebSearch, WebFetch or GitHub API call.

## Iteration log (first pass)

1. Built the decision plan and started the paced fetch; built the bake-off venv from a wide hash lock; wrote the numpy prototype, the measurement harness and the six approaches; first runs on the synthetic challenge.
2. Calibration, splitter, drift, schema, behavior and MiroFish checks. Found: Mesa 3.5.1 cannot be imported after a plain install; river's detectors absorb NaN; pandera mutates numpy and the environment at import; purgedcv's docstring contradicts its purge default; the MiroFish adapter hung because the mock outlived the run (fixed: the shell kills it). Narrowed the research lock from 35 to 30 packages (pandera and Mesa rejected; statsmodels, arch, crepes and interpret-core deferred) and rebuilt, re-downloaded and re-verified it.
3. First real-data run: HGB and lifelines failed on both real samples; cause, a builder bug (ISO `first_pool_at` parsed as a number, so the age column was empty) plus two library behaviours (HGB on an all-missing column, Cox on a constant column). Fixed the builder and added the training-window column rule; kept the failing runs as evidence.
4. Error-semantics probe: the numpy core returned silent probabilities on one-class windows; it now raises. Own adversarial pass on the splitter: the purge mutation passed the test-start audit on the 6 h sample; the audit now also checks each fold's declared training cutoff (on the 24 h sample it counts 31 leaked labels where the test-start check counted 29); on the 6 h sample the mutation changes no fold.
5. Final re-measurement of everything with the final code, third runs and tables; documents written from the generated numbers.

## Own adversarial pass (not independent)

- Counterexample (new, wrong but plausible): a walk-forward that trains each fold on every row decided before a midnight cutoff and records that midnight as the model's training cutoff. A fold audit that checks only "no training label matures after the first test decision" certifies it on the 24 h sample for 2 labels that matured between midnight and the first decision of the next day, so the model card's cutoff would be false (P13) while every overlap count is 0. Caught by the declared-cutoff check added to `core_numpy.fold_audit` (`splitter_check.py`: 31 leaked labels after the cutoff against 29 after the test start).
- Second case: a lock line carrying the sha256 of an sdist passes `runtime.check_lock`, which reads text only; it is refused by the install flags (`--only-binary=:all:`), shown by `hostile_setup_demo.py` (marker never written). The guard and the flags are both required; PI-D-032 states both.
- Limits that remain: the real sample has 26 and 33 out-of-sample events; the bake-off cannot rank approaches on skill and does not try. The copyleft gate catches copied runs of 15 or more normalized lines and license markers; a shorter or heavily rewritten copy would pass. Telemetry was measured offline only (a library that phones home only when online and fails silently offline would show 0 events; none of the adopted libraries has such code per Phase 03's source scan).

## Skeptic

Packet: `SKEPTIC_PACKET.md`. Review, counterexample and repair: pending (orchestrator).

## Artifacts

sha256 of every committed artifact of this phase: `PHASE_04_RESULTS.json` (`artifacts`).
