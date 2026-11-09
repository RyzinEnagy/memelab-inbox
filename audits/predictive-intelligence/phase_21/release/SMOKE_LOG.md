# Smoke and release-check log, 2026-11-09

Command: `bash audits/predictive-intelligence/phase_21/probes/release_checks.sh 90e4c6f b048aac OUTDIR` from the checkout at `b048aac`. Raw outputs: `audits/predictive-intelligence/phase_21/evidence/release_checks/` (scratch paths replaced by OUTDIR).

## Setup (the only network use)

| Step | Result |
|---|---|
| `git ls-remote https://github.com/RyzinEnagy/memelab-inbox.git refs/heads/feature/predictive-intelligence` (22:20:55Z) | `90e4c6fddae267759e67d928d5297726c5910785` |
| `git clone` of that URL, checkout of the branch | HEAD `90e4c6f`, equal to the pushed head |
| fetch `b048aac` from the checkout, `merge --ff-only` | HEAD `b048aacf...`; 5 paths changed, all under `phase_21/` (`logs/changed_since_pushed.txt`) |
| `python3 -m venv`, `pip install numpy==2.5.3 pytest==9.1.1 iniconfig==2.3.1 pluggy==1.7.0 packaging==26.3` | exit 0; freeze: iniconfig, numpy, packaging, pluggy, Pygments 2.21.0 (a pytest 9 dependency), pytest; `include-system-site-packages = false` |
| environment inside every check (`env -i`) | HOME, LANG, LC_ALL, MEMELAB_RELEASE_CHECK, PATH only (`logs/env_names_inside.txt`): no token, key or proxy variable |

A first attempt at `2a29c68` fetched the frozen commit by its short sha, which git refuses; the fast-forward did not happen and no step ran. The script was fixed to resolve a full sha and stop on a failed fast-forward (`b048aac`), and rerun. Both attempts are in the search ledger.

## Steps (`logs/steps.jsonl`; every lab or test command inside `unshare -n`)

| Step | Exit | Wall s | Peak MiB | Result |
|---|---:|---:|---:|---|
| full suite (loopback raised) | 1 | 259.4 | 985.5 | 2 failed (the two known clock tests), 2,239 passed, 5 skipped (3 node not installed, 1 jsonschema absent, 1 no IPv6 loopback) |
| predictive tests, private stores hidden (tmpfs over `/home/claude/pi_research`) | 0 | 95.5 | 278.5 | 1,453 passed, 7 skipped (4 stores absent, 1 MiroFish clone absent, 1 jsonschema, 1 IPv6) |
| cross-component tests | 0 | 4.1 | 71.4 | 43 passed |
| seal check | 0 | 0.0 | 18.9 | `problems: []` |
| social guard | 0 | 0.7 | 76.7 | 0 violations |
| chronology audit (as of 2026-11-09T00:00:00Z) | 0 | 0.4 | 46.3 | C1 to C4 ok, 5 of 5 planted violations caught |
| Phase 19 feedback audit (`run_prospective.py audit`) | 0 | 0.2 | 51.0 | predictions commit before the first label call; F1, F3, F4 ok; ledger verifies |
| scenario matrix P01 to P48 | 0 | 26.0 | 93.3 | 239 of 239 assertions; 25 PASS, 10 PASS_EXPECTED_ERROR, 12 TEST_ONLY, 1 PASS_WITH_PROBE_FINDING; mapped tests 232 passed; identical to Phase 20's last run |
| counterexamples | 0 | 10.2 | 86.1 | 39 of 39 caught; 85 tests passed |
| out-of-sample sensitivity | 0 | 20.3 | 43.9 | identical to the committed Phase 20 output |
| independent recalculation | 0 | 3.6 | 88.0 | 61 of 61 outcomes, 40 of 40 labels, 168 of 168 numbers, 2 traces all links; identical to Phase 20 |
| threat scan | 0 | 6.9 | 316.0 | as in Phase 20 apart from head, file count and its own output file |
| e2e: `tools/release_e2e.py` | 0 | (in e2e) | | 78 of 78 stages ok, 0 network attempts, tracked database unchanged |
| e2e: real-path smoke (`71fc50e` export, 8 mints) | 0 | (in e2e) | | see below |
| e2e: release audit with history, single-branch clone | 0 | (in e2e) | | "Needs action: no." |
| e2e total | 0 | 166.8 | 900.6 | |
| flag-off identity (2 exports x 6 configs, base `b0fad12` and `b048aac`) | 0 | 44.4 | 79.2 | all identical; frozen runs at the requested commit |
| reproductions (Phases 05 to 19 in a sandbox) | 0 | 717.7 | 919.7 | all reproduced, 19 runners exit 0, 0 differing files |

Clone `git status` after the checks: clean (one test stray, `data/reports/<stamp>_BRETT_0x532f.md`, removed as usual).

## Real-path smoke (`e2e/smoke_summary/REAL_PATH_SMOKE.json`)

| Check | Result |
|---|---|
| flag off at `b048aac` against `b0fad12`: every report byte-equal | true |
| lab tables equal (base off, frozen off, frozen on) | true |
| flag on: scout body is the base body plus an appended section | true |
| section: ABSTAIN lines, forecast lines | 24, 0 |
| first pass: events, attempted, documents, abstained, errors | 24 events (8 DISCOVERY), 8, 24, 24, 0 |
| rerun and retry | DUPLICATE (16 duplicates), no new document |
| storm (PAID listed four times) | one attempt |
| `integration check` on the four states | problems [] each (24, 24, 24, 3 documents) |
| analyze line | `predictive: DISCOVERY ABSTAIN (INSUFFICIENT_HISTORY, MODEL_NOT_SELECTED, SOURCE_STALE, UNCALIBRATED) ... research only, not advice` |
| vendor reader calls | 0 (`reader_calls` 0 in every pass) |
| latency per request | p50 0.327 ms, max 1.96 ms (state metrics; no read made) |

Repeatability: the section equals the Phase 20 repair-pass smoke section apart from the capture time, the pass id, the latency figures and the record ids (each record hashes its capture time) (`evidence/release_checks/e2e/REAL_SCOUT_SECTION.md`).

## Doc commands (`evidence/doc_commands/doc_commands.txt`, `probes/doc_commands.sh` at `24c02a6`)

`integration status` 0, `integration check` 0, `reports report` with the flag on 0 ("0 probabilities shown"), with the flag off 0 (`FLAG_OFF`), `reports alerts` dry run 0 (0 new alerts, 3 suppressed SOURCE_STALE, nothing sent), `alerts-state` 0 ("Nothing has been sent to a device"), `alerts` with the flag off 0 (`FLAG_OFF`), seal check 0, `docs_demo.py` 0, `integration check` on a damaged state copy 2 (`STATE_TAMPERED`).

## Operations

- Cost: 0. No vendor, model or paid call in any step; GeckoTerminal not called (the maturity fetch planned 0 reads).
- External services at run time: none. Needed only for the clone and the pip install.
- Caching: a repeated scout on the same snapshot writes nothing new (DUPLICATE); `unchanged_cache_hits` 0 in the smoke because each run used a fresh database.
- Skipped tasks: none of the checks skipped; test skips are listed above with their reasons.
