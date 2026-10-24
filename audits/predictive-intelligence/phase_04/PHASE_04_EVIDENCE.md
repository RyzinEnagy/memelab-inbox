# Phase 04 evidence: adoption, install, adapter or build bake-off

Status: **PASS** (repair pass): the orchestrator's independent skeptic (PI-D-013, 2 MATERIAL, 8 MINOR) is folded in (PI-D-035), and the post-commit suite, content guard and release audit on the repair commit `783fde4` hold (section "Post-commit results, repair pass"). The first pass was NEEDS_REVIEW.

| Item | Value |
|---|---|
| Branch | `feature/predictive-intelligence` |
| HEAD before | `a146a29d17c47a0bdfdef85df2e7a9e2f884d50f` (Phase 03 records commit) |
| Phase start (UTC) | 2026-10-24T07:55:08Z (entry gate) |
| Acceptance checklist written | 2026-10-24T07:59Z, before any change (`ACCEPTANCE_CHECKLIST.md`, B1 to B22, one dated amendment at 08:20Z widening B16 to the P31 fixture and the lock folder) |
| Commits | first pass: deliverables commit `4a19d7135db809ed30f8bb5ce2390a800d1f92c3` (2026-10-24T09:04Z) and records commit `84f8c867e33c639f36a7f8c777f6cc848e6f31c9`; repair pass: repair commit `783fde4c45fd0ddc23d3d4434592159fb37271af` (2026-10-24T10:06Z) and the records commit on top of it (its hash: `git log -1`) |
| Spend | 0 Firecrawl credits; free calls only (below) |

## Entry gate and standing checks

| Check | Command | Result |
|---|---|---|
| Package unchanged (B1) | `cd <package> && sha256sum -c SHA256SUMS.txt` | exit 0, every line OK |
| Entry gate (B2) | `python -m pytest tests -q` at `a146a29`, clean checkout | exit 1, `1 failed, 858 passed in 145.42s (0:02:25)`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known); strays `data/reports/20261024_0754_BRETT_0x532f.md` (from an aborted first start of the same command), `data/reports/20261024_0755_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal` removed by hand; `data/memelab.sqlite` sha256 `068287c0...` unchanged |
| System interpreter untouched (B11) | `pip freeze \| sha256sum` at the start and the end | `4bbf5c51faf183d2...` both times |
| Untracked state found, not this phase's | `git status --ignored` | an ignored uv venv `hazardous/` at the repository root, created 2026-10-24T06:48Z by a Phase 03 reviewer; left in place in the first pass, removed in the repair pass |

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
| Banned defaults | `python -B banned_scan.py ../evidence/banned_scan.json` | 0 | 15 self-tested rules, 26 files (28 after the repair), 0 hits, 1 allowed negative control |
| Locks | `uv pip compile ... --universal --generate-hashes --only-binary :all:`; `python -B build_lock.py IN OUT BOM CACHE` | 0 | research 30 packages / 63 hashes, core 1 / 4; 0 problems; `check_lock` 0 problems |
| Three-platform download | `pip download --require-hashes --only-binary=:all: --no-deps [--platform ...] -r <lock>` x 3 platforms x 2 locks | 0 x 6 | 30 wheels per platform, every sha256 in the lock (`evidence/wheelhouse_check.txt`) |
| Wheel licenses | `python -B wheel_licenses.py WH ../evidence/wheel_licenses.json` | 0 | 30 of 30 wheels carry license files; GPL or LGPL text only as bundled-runtime notices or references |
| Rollback | `python -B rollback_demo.py /home/claude/pi_research/p04/wh_linux ../evidence/rollback_demo.json` | 0 | 30 installed offline, smoke of 4 approaches exit 0, uninstall, `rollback_clean: true` (files); `pip check` reports only lifelines' `pandas<3`. Rerun in the repair pass with directories in the manifest: one empty `mpl_toolkits/` left (`rollback_clean_with_dirs: false`, m8); the four smoke predictions now equal the measured runs (the first-pass file held an LR_SKLEARN hash, `c9c0050e...`, from an earlier run that did not equal the measured output) |
| Hostile setup (P32) | `python -B hostile_setup_demo.py ../evidence/hostile_setup_demo.json` | 0 | lab route refuses the sdist (marker not written) and the wrong hash; plain pip runs the sdist's setup.py (marker written) |
| MiroFish | `python -B mirofish_adapter.py ../evidence/mirofish_adapter_runs.json` | 0 | backend exit 1 without keys; 2 mock runs SIMULATION_RAN with different traces; LLM down: exit 0, SIMULATION_NOT_AVAILABLE |
| Copyleft fingerprints | `python -B build_copyleft_fingerprints.py tests/fixtures/predictive/copyleft_fingerprints.json` (repository root) | 0 | 5,393 fingerprints from MiroFish (82 files) and black-it (42 files) at their pins; 0 findings in the lab's 209 code files and the 25 prototypes; MiroFish files flagged (repair: rebuilt as version 2 with the runtime's hash spec and a self-test; the test scans every code file of the working tree, 411) |
| Runtime tests | `python -m pytest tests/test_predictive_runtime.py tests/test_predictive_contract.py -q` (root) | 0 | `112 passed` (first pass); `201 passed` after the repair (135 runtime, 66 contract) |
| Runtime mutations | `python -B mutation_runtime.py ../evidence/mutation_runtime.json` | 0 | 17 of 17 mutations make the tests fail; baseline 46 passed (first pass); 41 of 41 after the repair, baseline 135 passed |

Before the commit, on the staged tree: `python -m pytest tests -q` exit 1, `1 failed, 904 passed in 142.75s (0:02:22)` (known failure only); content guard 0 violations; release audit exit 0. The results that count are the post-commit ones below (PI-D-030).

## Acceptance checklist results (after the repair pass)

| Id | Result |
|---|---|
| B1 | OK (above) |
| B2 | OK: `1 failed, 858 passed`, known failure only |
| B3 | OK: every component maps to a Phase 03 role and review id (BAKEOFF.md "Candidates and roles"); banned scan 0 hits in 28 files |
| B4 | OK: one dataset family with identical folds; real sample from development decisions only, every request ended at the holdout start, 0 holdout decisions labelled; pace at most 6 a minute; every call logged; raw bodies outside the repository. Repair (m4, m5): candles are dropped when they end after the holdout start, the six holdout-start candles were purged from the raw store (`evidence/raw_store_quarantine.json`, original and redacted sha256, start times only), the relabel gives byte-identical CSVs, and `holdout_candle_check.py` finds 0 candles ending after the holdout start. Synthetic challenge with the maturity purge |
| B5 | OK: six approaches (B0, numpy logistic, scikit-learn logistic, HGB, LightGBM, lifelines Cox) plus three calibration variants, same rows and folds, metrics with N, positives and folds, no edge claim; re-measured after the repair, every prediction byte-identical |
| B6 | OK: fold audit with test-start and declared-cutoff checks; lab rule and purgedcv valid on all datasets; mutation refused on the challenge (2,304) and the 24 h sample (31) and a no-op on the 6 h sample (stated); TimeSeriesSplit refused on all three. Repair (m1): the audit fails closed on non-finite times, a cutoff after the test start and, given the target's lag, a shorter-horizon maturity column, and reports shared mints (1, 4, 4, 1 on the 24 h sample); the splitter refuses non-finite times; `prototypes/test_core_numpy.py` 9 passed, 8 of them fail on the first-pass code |
| B7 | OK: Venn-Abers max difference 1.4e-17 (bound 1e-9) on five probes that feed both implementations the same probabilities, including scores above 37 (m7); Platt on constant scores equals the exact optimum within 7e-18; MAPIE port and prefit Pipelines absent (scan) |
| B8 | OK: cold start, peak RSS, CPU, audit-hook and strace network counts, determinism over three runs, wheels for Linux, Windows and macOS arm64 at each exact version, every run on numpy 2.5.3 and pandas 3.0.5, telemetry none found |
| B9 | OK: INSTALL_DECISION.md, a decision and fallback per component; the essential engine ran in a numpy-only venv offline with identical predictions |
| B10 | OK: two hash locks, 63 + 4 hashes equal to PyPI digests and to the downloaded files; offline install from a wheelhouse with the lab's flags; install route PI-D-032 as amended by PI-D-035; lock sha256 pinned in the tests (`1347f84b...`, `89fe4f4d...`; headers changed in the repair, hash lines unchanged) |
| B11 | OK: rollback clean for files and freeze; one empty `mpl_toolkits/` directory remains (reported, m8; the documented rollback deletes the venv); system freeze unchanged |
| B12 | OK: MIROFISH_FEASIBILITY.md, ISOLATED_MOCK_ONLY, no probability, no paid call, no copied code, silent success caught, NOT_SUPPORTED for the paid route |
| B13 | OK after the repair (M2, m2, m6): `runtime.py` standard library only; `guarded` contains every exception including SystemExit, and only KeyboardInterrupt and GeneratorExit pass through, on purpose; any config shape gives OFF or a named state (`capability_report`, `contract.enabled`); 135 tests, 41 of 41 mutations caught (including the skeptic's six survivors and a narrowed catch); the skeptic's probes rerun: no exception escapes (`skeptic/p04/runtime_probes_after_repair.json`); no existing module imports the package |
| B14 | OK after the repair (m2, m3): 0 findings in every code file of the working tree (411, `audits/` and root scripts included); fixture spec checked at load and a self-test text reproduced; sha1 and lower-casing mutations caught; positive control against the pinned MiroFish clone flags at least 80% of its backend files when the clone is present |
| B15 | OK after the repair (M1): the skeptic's two lines are refused by `check_lock` and by `install_argv` before pip starts (test cases and `hostile_setup_demo.py` case E); pip run directly with the lab's flags still builds that sdist (control, so the guard is required); committed locks hold only known wheel digests (test) |
| B16 | OK: `git diff --name-only a146a29..HEAD` lists only `audits/predictive-intelligence/`, `docs/predictive-intelligence/`, `memelab/predictive/runtime.py`, `memelab/predictive/contract.py` (`enabled()` only, Amendment 2; fingerprint `91d03c76...` unchanged, contract tests unedited and passing), `tests/test_predictive_runtime.py` and `tests/fixtures/predictive/copyleft_fingerprints.json`; no existing test changed; no new test needs a third-party package; strays removed; `data/memelab.sqlite` sha256 unchanged |
| B17 | OK: first pass and repair commit, each on the committed tree: suite with only the known failure, content guard 0 violations, release audit exit 0 (below) |
| B18 | OK: no wheel, venv, pickle, weights, raw API body, token, file over 1 MB or social content in the phase folder (largest file under 500 KB); labels marked BAKEOFF_ONLY and refused as a label source by `runtime.refuse_bakeoff_labels` (test) |
| B19 | OK: COST_LEDGER rows for the first pass and the repair pass, 0 credits |
| B20 | OK: records written; PASS only after the repair and its post-commit checks |
| B21 | OK: every new or changed file scanned before each commit for en and em dashes, curly quotes and 20 marketing words: 0 hits |
| B22 | first pass two commits; repair pass one repair commit and one records commit (Amendment 2); no push |

## Post-commit results, first pass (deliverables commit `4a19d7135db809ed30f8bb5ce2390a800d1f92c3`)

| Check | Command | Exit | Result |
|---|---|---|---|
| Full suite | `python -m pytest tests -q` (09:04:41Z to 09:07:15Z) | 1 | `1 failed, 904 passed in 153.99s (0:02:33)`; only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known); 46 new tests pass; stray `data/reports/20261024_0904_BRETT_0x532f.md` and the sqlite `-shm` and `-wal` removed by hand; `data/memelab.sqlite` sha256 `068287c0...` unchanged |
| Content guard | `python -m memelab social guard` | 0 | `"violations": []` (1,175 files scanned) |
| Release audit | `python tools/release_audit.py --history` | 0 | "Needs action: no"; this phase adds two network-path rows without credentialed or paid hosts (`build_dev_sample.py`, `measure.py`) and no trade-execution or signing hit |
| System interpreter | `pip freeze \| sha256sum` | 0 | `4bbf5c51...`, unchanged since the start |

Files: `postcommit/first_pass/pytest_summary.txt`, `social_guard.out.txt`, `release_audit_history.summary.txt` (summary only, PI-D-030), `summary.json` (moved from `postcommit/` in the repair pass, unchanged).

## Post-commit results, repair pass (repair commit `783fde4c45fd0ddc23d3d4434592159fb37271af`)

| Check | Command | Exit | Result |
|---|---|---|---|
| Full suite | `python -m pytest tests -q` (10:06:04Z to 10:08:37Z) | 1 | `1 failed, 993 passed in 152.42s (0:02:32)`; only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known); 135 runtime tests pass; stray `data/reports/20261024_1006_BRETT_0x532f.md` and the sqlite `-shm` and `-wal` removed by hand; `data/memelab.sqlite` sha256 `068287c0...` unchanged |
| Content guard | `python -m memelab social guard` | 0 | `"violations": []` (1,204 files scanned) |
| Release audit | `python tools/release_audit.py --history` | 0 | "Needs action: no"; one new reviewed placeholder shape (a test id of 64 `A` characters in `evidence/old_code_check.json`); no new network-path row; no trade-execution or signing hit in this phase's files |
| Paths | `git diff --name-only a146a29..HEAD` | 0 | only the B16 set (Amendment 2) |
| System interpreter | `pip freeze \| sha256sum` | 0 | `4bbf5c51...`, unchanged since the start |

Files: `postcommit/pytest_summary.txt`, `postcommit/social_guard.out.txt`, `postcommit/release_audit_history.summary.txt` (summary only, PI-D-030), `postcommit/summary.json`. `git status` clean after the strays were removed.

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

Packet: `SKEPTIC_PACKET.md`. The orchestrator's independent skeptic reviewed `84f8c86` (`skeptic/PHASE_04_SKEPTIC.md`; its scripts and raw outputs copied to `skeptic/p04/`): 2 MATERIAL (M1 lock guard, M2 containment), 8 MINOR (m1 to m8). The holdout seal, all 261 labels, B0, the folds, five prediction hashes, the equivalences and both REJECT reasons were re-derived independently and held. The orchestrator's rerun at `84f8c86`: `1 failed, 904 passed in 147.82s`, DB unchanged.

### The counterexample and what catches it now

`skeptic/p04/skeptic_04_lock_bypass.py`: one added lock line, `p04sk==1.0 ; python_version >= "3" --hash=sha256:<sha256 of the sdist> --only-binary=:none:`, passed `runtime.check_lock`, and pip run with exactly `INSTALL_FLAGS` (offline, local index) built the sdist and ran its `setup.py`, because pip applies the per-line option and clears the command line's `--only-binary=:all:`. A variant with an extra `--hash=sha512:` installed a wheel whose sha256 is not locked. Nothing in the repository caught either.

Now caught by three things, each shown to fail on the first-pass code:

1. `runtime.check_lock` (strict): after `name==version` and an optional plain marker, only `--hash=sha256:<64 lowercase hex>` tokens; the line is refused with "only --hash=sha256:<64 hex> may follow a requirement; refused '--only-binary=:none:'". Test cases `test_p32_lock_guard_refuses_anything_but_hashed_exact_pins[p04sk==1.0 ; python_version >= "3" ... --only-binary=:none:]` and the sha512 variant, plus 25 more bad lines (`--config-settings`, `--global-option`, `--prefer-binary`, `--no-binary`, sha384, md5, upper-case hex, a marker running into an option, a comment hiding an option). The first-pass `check_lock` accepted 5 of the 27, all with a marker (the skeptic's two lines, a marker running into `--only-binary`, a marker followed by `-x`, a marker holding `$(touch x)`); all 27 cases fail on the first-pass code because its route had no refusal before pip (`evidence/old_code_check.json`).
2. `runtime.install_argv` is the only way the lab builds an install command; it raises `InstallRefused` before pip starts (`test_p32_install_argv_is_the_only_route_and_carries_the_flags`; `hostile_setup_demo.py` case E: marker absent after `install_argv`, present when pip is run directly with the same flags, so the flags alone are not enough).
3. The committed locks may hold only digests of wheels recorded in the BOM, and their sha256 is pinned (`test_p32_committed_locks_hold_only_known_wheel_digests_and_are_pinned`), so adding any line is a failing test until a decision records it.

The skeptic's script rerun on the repaired code: `check_lock` refuses the line, verdict "no bypass" (`skeptic/p04/lock_bypass_after_repair.json`; its own "lab route" is pip run directly and still writes the marker, which is the control above).

## Repair pass (2026-10-24, after the skeptic; PI-D-035)

Each finding was verified first against the first-pass code (the skeptic's scripts rerun where it had one, otherwise by reading the code and data it cites); all ten reproduced.

| Finding | Change | Evidence |
|---|---|---|
| M1 lock guard | strict `check_lock`, `install_argv`, known wheel digests, lock sha256 pinned | 27 bad-line cases; hostile demo case E; `lock_bypass_after_repair.json` |
| M2 never raises | `guarded` catches BaseException except `NOT_CONTAINED = (KeyboardInterrupt, GeneratorExit)`; LLM actions only a positive int; non-object config sections mean OFF in `capability_report` and `contract.enabled`; every probe guarded | 27 P30 cases (SystemExit, bad `llm_actions`, malformed configs), SystemExit, KeyError, TypeError and a custom BaseException contained, KeyboardInterrupt passes; narrowed-catch and `except Exception` mutations caught; `runtime_probes_after_repair.json`: no exception escapes |
| m1 fold audit | non-finite times, cutoff after test start, maturity shorter than the target's lag, shared groups | `test_core_numpy.py` (the skeptic's cases A, A2, B, C, D) |
| m2 surviving mutations | fixture spec (`sha256`, normalization, shingle 4, window 12) checked at load; self-test text; MiroFish positive control when the clone is present | 41 of 41 mutations caught, including sha1, `FINGERPRINT_ALGO`, lower-casing, breaker, caps, line-start-only option check |
| m3 scan scope | whole working tree, `.css`, `.jsx`, `.tsx`, `.cjs` added; two license detectors exempt from the marker check only | 411 files, 0 findings |
| m4 boundary | drop candles with `start + 300 > boundary`; PI-D-034 amended | 0 candles ending after the holdout start |
| m5 isolation | six holdout-start candles purged from the raw store (hashes recorded); `refuse_bakeoff_labels`; a test keeps lab modules from naming the bake-off data folder | `raw_store_quarantine.json`, `holdout_candle_check_after_purge.json` |
| m6 CallGuard and probe | NaN or negative cost or pace refused; `is_failure` for returned error responses; any exception counts toward the breaker; dotted names refused | tests with a hostile parent package and a NaN cap |
| m7 equivalence edges | Platt on constant scores returns the exact optimum; Venn-Abers oracle gets the same probabilities on both sides, with a large-scores probe | max difference 1.4e-17; constant-score optimum within 7e-18 |
| m8 cosmetic | core lock header; rollback lists directories | `leftover_dirs: ["mpl_toolkits"]` reported |
| Housekeeping | ignored venv `hazardous/` removed from the repository root | `git status --ignored` |

| Step | Command | Exit | Result |
|---|---|---|---|
| Raw store purge | `python -B build_dev_sample.py quarantine ../data RAW` (writes `../evidence/raw_store_quarantine.json`) then `label ../data RAW` | 0 | 6 bodies redacted (one candle each, start equal to the holdout start); CSVs byte-identical; summary keys renamed |
| Holdout candle check | `python -B holdout_candle_check.py RAW > ../evidence/holdout_candle_check_after_purge.json` | 0 | 0 candles ending after the holdout start |
| Re-measurement | `python -B run_measurements.py approaches`, `checks`; `python -B summarize.py`; `render_tables.py` | 0 | `not_identical_or_failed: []`; every approach's predictions byte-identical to the first pass |
| Prototype tests | `python -m pytest audits/predictive-intelligence/phase_04/adoption/prototypes/test_core_numpy.py -q` | 0 | `9 passed` |
| Runtime and contract tests | `python -m pytest tests/test_predictive_runtime.py tests/test_predictive_contract.py -q` | 0 | `201 passed` |
| Mutations | `python -B mutation_runtime.py ../evidence/mutation_runtime.json` | 0 | 41 of 41 caught, baseline 135 passed |
| Tests against the first-pass code | `python -B old_code_check.py ../evidence/old_code_check.json` | 0 | runtime `88 failed, 47 passed`, prototype `8 failed, 1 passed` |
| Hostile setup | `python -B hostile_setup_demo.py ../evidence/hostile_setup_demo.json` | 0 | every verdict true, case E included |
| Rollback | `python -B rollback_demo.py /home/claude/pi_research/p04/wh_linux ../evidence/rollback_demo.json` | 0 | as above; `leftover_dirs: ["mpl_toolkits"]` |
| Fingerprint fixture | `python -B build_copyleft_fingerprints.py tests/fixtures/predictive/copyleft_fingerprints.json` (root) | 0 | version 2, 5,393 fingerprints, 21 self-test fingerprints |
| Locks | `python -B build_lock.py ...` (cached PyPI metadata) | 0 | headers only; 63 + 4 hashes unchanged |
| Banned defaults | `python -B banned_scan.py ../evidence/banned_scan.json` | 0 | 28 files, 0 hits |
| Skeptic probes | from `skeptic/p04/`: `python -I -B skeptic_04_runtime_probes.py REPO TMP`, `python -I -B skeptic_04_lock_bypass.py REPO /home/claude/pi_research/p04/wheels_setuptools OUT` | 0 | no exception escapes; no bypass |

Before the repair commit, on the working tree and then the staged tree: `python -m pytest tests -q` exit 1, `1 failed, 993 passed in 148.46s (0:02:28)` (10:01:11Z to 10:03:40Z; only the known catalyst failure; stray `data/reports/20261024_1001_BRETT_0x532f.md` and the sqlite `-shm` and `-wal` removed by hand; `data/memelab.sqlite` sha256 `068287c0...` unchanged); content guard exit 0, `violations: []` (1,204 files); release audit with history exit 0, "Needs action: no" (one new reviewed placeholder shape: a test id of 64 `A` characters in `evidence/old_code_check.json`). The results that count are the post-commit ones (section "Post-commit results, repair pass").

Disagreements with the review: none material. Two precisions: the install flags alone cannot stop per-line options, so the guard and `install_argv` are both required and documented as such; a callable that returns an HTTP error status instead of raising is detected only when the caller supplies `is_failure` (documented, not automatic).

## Artifacts

sha256 of every committed artifact of this phase: `PHASE_04_RESULTS.json` (`artifacts`).
