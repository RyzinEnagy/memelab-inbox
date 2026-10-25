# Phase 06 evidence: outcome label registry and censoring

Status: NEEDS_REVIEW after repair pass 2 (2026-10-25), with one item open: the frozen 48 h revision re-read, which cannot run before 2026-10-26T13:49Z for all 16 sampled reads. Every other gate item holds; the independent skeptic is folded in (section "Repair pass 2").

| Item | Value |
|---|---|
| Branch | `feature/predictive-intelligence` |
| HEAD before | `ed82f3a9d89b091579bd4ed43646acf14e355d64` (Phase 05 PASS) |
| Work window (UTC) | 2026-10-24T12:30Z to about 14:50Z |
| Package | "Memecoin Predictive Intelligence Engine" 1.0, `sha256sum -c SHA256SUMS.txt` all OK |
| Export ref for decisions | `efdaee91ebbeabf14268d858fa033d36ebd4ca06` (`git fetch origin main` at 12:3xZ; newest export 2026-10-24T10:11:50Z) |
| Spend | 0 Firecrawl credits; free GeckoTerminal calls only (COST_LEDGER.md; holdout call counts inside `sealed/`) |

## Entry gate

| Check | Command | Exit | Result |
|---|---|---:|---|
| Package checksums | `sha256sum -c SHA256SUMS.txt` | 0 | every line OK |
| Full suite at `ed82f3a` | `python -m pytest tests -q` | 1 | `1 failed, 1066 passed in 152.58s`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (known); stray `data/reports/20261024_1226_BRETT_0x532f.md` removed by hand |
| Checkout | `git status --short` | 0 | clean on `feature/predictive-intelligence` |

## What was built

- `memelab/predictive/labels.py` (new, standard library only, flag OFF, imported by no existing module): reads (`read_from_body`, the store's exact candle rules), absence evidence, eligibility through `contract.eligibility`, classes for T1, T1b and T2 through `contract.reference_candle`, `path_candles` and `label_matures_at`, thinning through `decisions.thin`, splits, the label store (additive migration 2, append-only, HOLDOUT refused), the sealed-row writer, seal manifest and check, revisions (`revision_changes`, `revise`), cross-target invariants, and the mature-only training gate `training_labels`.
- `memelab/predictive/contract.py`: change control CC-03 only (`_COMMON.absence_evidence`, `one_read_per_decision`, `unverifiable_rule`; T2 `halt_span_rule`, `halt_other_pools`), made before any label; fingerprint `91d03c76...` to `4b4aabce77a5a6f9214c4cfdddf5223f410ed6126410cf4b213b3c80b035f896`, re-pinned in `tests/test_predictive_contract.py` (PI-D-040). ACCEPTANCE unchanged.
- `memelab/predictive/__init__.py`: one docstring line.
- `tests/test_predictive_labels.py` (41 tests) and `tests/fixtures/predictive/labels_hand_trace.json` (6 hand-checked cases).
- Probes under `phase_06/probes/`: `build_labels.py` (exports, vendor lists, plan, paced shared reads, transient repair), `make_labels.py` (other pools, labels, seal, revisions, archive, coverage, offline rebuild), `real_traces.py`, `render_report.py`, `check_seal.py`, `mutation_labels.py`, `make_hand_fixture.py`.
- Deliverables: `labels/TARGET_SCHEMA.md`, `labels/COVERAGE_CENSORED_REPORT.md` (with `labels/coverage_tables.md`, `labels/coverage.json`), `labels/HAND_CHECKED_TRACE.md`, `ACCEPTANCE_CHECKLIST.md` (12:35Z, before any change), `SKEPTIC_PACKET.md`; data `data/read_plan.json`, `data/read_map.json`, `data/revision_sample.json`; raw `raw/` (256 files, 5.8 MB, `MANIFEST.csv`); sealed `sealed/` (`SEAL.json` lists every file and its sha256).

## Real data run (commands in order)

| Step | Command (in `phase_06/probes/`) | Exit | Result |
|---|---|---:|---|
| Decisions | `python -B build_labels.py exports` | 0 | 90 export versions, 1,519 events, 1,518 stored, 1 refused (`MukLDtJ8...`, 31 bytes) |
| Vendor lists | `python -B build_labels.py lists` | 0 | 59 mints without a point-in-time pool, 59 HTTP 200 (1 empty list) |
| Plan | `python -B build_labels.py plan` | 0 | development 795 decisions on 143 pools, sealed 85 on 73 pools, 47 no snapshot price, 583 EVM, 7 prospective, 1 holdout with no pool |
| Development reads | `python -B build_labels.py fetch dev` | 0 | 795 decisions mapped to 191 responses (shared only with demonstrated coverage) |
| Holdout reads | `python -B build_labels.py plan; python -B build_labels.py fetch sealed` | 0 | 85 decisions mapped; response and call counts inside `sealed/` (holdout call, response and body counts are kept inside `sealed/`, skeptic m8) |
| Transient repair | `python -B build_labels.py unmap_transient dev` and `sealed`, then `fetch dev` | 0 | 1 development decision had been mapped to an HTTP 429 that survived four tries; unmapped and read again (200); sealed 0 |
| Other pools | `python -B make_labels.py others dev`, `others sealed` | 0 | development 0 decisions needed other pools; the sealed count is written to `sealed/others_summary.json` only |
| Labels | `python -B make_labels.py labels` | 0 | 4,026 rows into the development store; 528 sealed lines; cross-target violations 0 and 0 |
| Revision sample and re-read | `python -B make_labels.py sample; python -B make_labels.py reread` | 0 | 16 of 151 development label reads; gap 1,681 to 4,685 s; 12,617 candles compared, 0 changed, 0 appeared, 0 vanished; 44 labels re-derived, 0 changed |
| Phase 05 comparison | `python -B make_labels.py compare05` | 0 | 182 read pairs, gap 5,461 to 9,214 s, 76,120 positions: 76,019 identical, 101 open-only or open with high or low (54 o, 26 oh, 21 ol), 0 close or volume; 111 labels recomputed from a Phase 05 read: 111 identical |
| Archive and seal | `python -B make_labels.py archive` | 0 | 256 development bodies (5.8 MB), sealed bodies hashed in `SEAL.json`; seal digest `d5059bae...`, holdout labels `e695500d...` |
| Coverage | `python -B make_labels.py coverage; python -B render_report.py` | 0 | `labels/coverage.json`, `labels/coverage_tables.md` |
| Real traces | `python -B real_traces.py` | 0 | 4 development traces (`evidence/real_traces.json`), hand-checked in HAND_CHECKED_TRACE.md Part B |
| Offline rebuild | `python -B make_labels.py rebuild` | 0 | from `raw/` and git only: 3,888 development records, 0 differences, 491 labelled |
| Seal check | `python -B check_seal.py` | 0 | `"problems": []` |
| Pacing | both call logs together | | at most 6 in any 60 s window by send time (where recorded) and by arrival time (all calls); development log 280 calls, 25 HTTP 429 retried; every OHLCV URL carries `token=<mint>`; every 200 OHLCV body OK_TOKEN_PARAM (0 refused) |

## Development label counts per target and class

| Class | T1 24 h | T1b 6 h | T2 24 h |
|---|---:|---:|---:|
| TARGET_FIRST | 34 | 26 | |
| INVALIDATION_FIRST | 70 | 67 | |
| AMBIGUOUS_BAR | 1 | 1 | |
| NEITHER | 31 | 129 | |
| NO_TRADES_AFTER_ENTRY | 0 | 1 | |
| DRAWDOWN_50 | | | 28 |
| TRADING_HALT | | | 0 |
| NO_SEVERE_EVENT | | | 103 |
| Labelled (positive) | 136 (34) | 224 (26) | 131 (28) |
| THINNED / MARKET_INACTIVE / VENDOR_OR_ROUTE_GAP / UNVERIFIABLE / PENDING | 568 / 35 / 39 / 0 / 0 | 490 / 40 / 41 / 0 / 0 | 566 / 26 / 37 / 0 / 0 |

Holdout (sealed, counts and censoring only): LABELED 67 / 69 / 60, PENDING 0 / 0 / 7, THINNED 2 / 0 / 2, MARKET_INACTIVE 12, VENDOR_OR_ROUTE_GAP 5, UNVERIFIABLE 0, NO_SNAPSHOT_PRICE 9, OUT_OF_SCOPE_CHAIN 81 for each target.

## Tests

| Check | Command | Exit | Result |
|---|---|---:|---|
| Label tests | `python -m pytest tests/test_predictive_labels.py -q` | 0 | `41 passed` at the first pass, `58 passed` after repair pass 2 (P05, P06, P07, P09, P14, P20, P37, P44, P01, P02, tie rule, absence evidence, other pools, migration, seal, training gate, CX-06, 6 hand cases) |
| Contract tests after CC-03 | `python -m pytest tests/test_predictive_contract.py -q` | 0 | `66 passed` (fingerprint re-pinned) |
| Mutation check | `python -B probes/mutation_labels.py evidence/mutation_labels.json` | 0 | control exit 0; 25 of 25 mutations caught (tie positive, strict barrier, pending ignored, same-candle path, empty page as no trade, boundary ignored, other pool not evidenced, halt without other pools, list failure as halt, wrong drawdown level, no thinning, no purge, identity unchecked, boundary candle kept, another mint's read, gate maturity, bake-off guard removed, capture mode ignored, revision used early, holdout row allowed, 48 h gap ignored, invariant off, seal ignores content, wick flag off, forbidden names) |
| Full suite before commit | `python -m pytest tests -q --deselect tests/test_catalyst.py::test_dedup_corroboration_resurface_denial -x` | 0 | `1106 passed, 1 deselected in 147.56s` (before the last label test was added) |
| Content guard before commit | `python -m memelab social guard` | 0 | `"violations": []` |
| Release audit before commit | `python tools/release_audit.py` | 0 | "Needs action: no." |

Post-commit results are recorded in the section below, after the commit.

## Acceptance checklist results

| Id | Result |
|---|---|
| A1, A2 | pass (above) |
| A3 | pass: only the primary targets, registry values (test); fingerprint changed only by CC-03, recorded and re-pinned at 12:39:00Z, first price read 12:57:59Z |
| A4 | pass: `token=<mint>` on every OHLCV URL, identity checked, boundary drop, pacing at most 6 per 60 s, cap and breaker through `CallGuard`, archive 8.2 MB with sha256 manifests, COST_LEDGER row |
| A5 | pass: every one of 1,518 events has one state per target; per-target totals 1,518 (`labels_run.json`, `coverage.json`) |
| A6 to A9, A11 to A13, A15, A16 | pass by tests and the mutation check (above) |
| A10 | partly: code and tests pass; real comparisons at 0.5 to 2.6 h gaps show no close, volume or label change; the frozen 48 h re-read is open (from 2026-10-26T13:05Z) |
| A14 | pass: sealed file and 98 other sealed files hashed, `check_seal.py` exit 0, holdout printed as counts and censoring only, the training path never reads `sealed/` (test) |
| A17 | pass: 0 violations in development and holdout; CX-06 tests |
| A18 | pass: COVERAGE_CENSORED_REPORT.md, coverage_tables.md; rebuild from the archive 0 differences |
| A19 | pass: 6 fixture cases and 4 real traces, every code label equals the hand label |
| A20 | pass: isolation test (`test_no_existing_module_imports_the_predictive_package`), only `labels.py` names the sealed folder (test), no network in tests |
| A21, A22 | recorded after the commit |

## Iteration log (one pass so far)

Pass 1, INSPECT: package, records, Phase 01 to 05 deliverables, `contract.py`, `decisions.py`, `store.py`, `sources.py`, `runtime.py`; found that the frozen absence classes cannot be applied as written under PI-D-039 (an empty page is not evidence), so CC-03 was written into the checklist and the registry before any label (PI-D-040). DO: `labels.py`, tests, fixture, probes; the real run above. CHECK: tests, mutations, rebuild, seal, comparisons. ATTACK (my own, not independent): the defects below, and counterexample CX-06. FIX: each defect fixed before the final run; the development label tables were rebuilt twice in the private store (they hold no committed state; the final run is the one archived and rebuilt from the archive).

| Defect found in pass 1 | Fix |
|---|---|
| The first 59 calls (vendor lists) logged the time before the guard's pacing wait as `requested_at` | the send time is logged from then on (`sent_t`); pacing for all calls of both logs verified on arrival times (at most 6 in 60 s) and on send times where recorded |
| An HTTP 429 that survived four tries mapped one development decision to a failed read (it would have been a VENDOR_OR_ROUTE_GAP, against the registry's "429 is retried, never a class") | `fetch` never maps a 429, 0 or 5xx; `unmap_transient` removed the one mapping and the decision was read again |
| A holdout decision whose vendor list was empty was NOT_READ instead of VENDOR_OR_ROUTE_GAP (no pool resolved) | `build` makes a no-pool decision a censored gap; test `test_p09_a_decision_whose_route_resolves_no_pool_is_a_censored_gap_not_unread`; labels rebuilt and resealed |
| `store._insert` (INSERT OR IGNORE) silently dropped label rows that failed a CHECK, found by the tests before any real row | strict insert that raises on a CHECK and skips only an existing label key |
| EVM decisions' cohort route said PIT_RECORDED | cohort route OUT_OF_SCOPE_CHAIN for other chains; labels rebuilt and resealed (sealed file sha256 changed to `e695500d...`) |

## Counterexample CX-06 (own, not independent)

Wrong but plausible: label each target from whichever read covers its window (the shortest read for 6 h, a later or longer one for 24 h). GeckoTerminal computes a response's earliest open, and with it a high or low, from the request window (PI-D-037), so the same candle can carry a +25% high in one read and a -15% low in another: T1b TARGET_FIRST and T1 INVALIDATION_FIRST for one decision, both "correct" for their read. Caught by: CC-03 rule 4 (one read per decision, enforced structurally because `Universe.read_of` holds one read per decision) and `labels.cross_target_violations`; `tests/test_predictive_labels.py::test_cx06_a_label_built_from_another_read_breaks_an_invariant` fails the mixed set and passes each single-read set; the mutation that turns the invariant off is caught. Real data: 0 violations over the development and holdout records.

## Sources

- GeckoTerminal public API v2 (OHLCV `https://api.geckoterminal.com/api/v2/networks/solana/pools/<pool>/ohlcv/minute?aggregate=5&limit=1000&before_timestamp=<b>&currency=usd&token=<mint>` and token pools `https://api.geckoterminal.com/api/v2/networks/solana/tokens/<mint>/pools?page=1`); every request URL and body hash is in `raw/MANIFEST.csv` and `sealed/raw/MANIFEST.csv`.
- State exports: `data/state/latest.json` on `main`, first-parent history to `efdaee91`.

## Artifact sha256

First-pass values; the current hashes after repair pass 2 are in PHASE_06_RESULTS.json.

| Artifact | sha256 |
|---|---|
| `memelab/predictive/labels.py` | `fc8496ed4f1082ab515ae78b4b138dc5a3c8e1dc5b3dfbf5b14b2baf0a17d2dd` |
| `tests/test_predictive_labels.py` | `58e15b03c428bd37215d37afb5496550160bed145b15659519066326296ca575` |
| `tests/fixtures/predictive/labels_hand_trace.json` | `70ab9cf3ec9777422e71245a25304888c41bc9f8737ba566912eeabc0e5526ba` |
| `labels/TARGET_SCHEMA.md` | `a9a0bc4b08d7907e4378c54d05989ab6d6dfa8edf4c92ab66cced773a9408b18` |
| `labels/COVERAGE_CENSORED_REPORT.md` | recorded in PHASE_06_RESULTS.json |
| `labels/HAND_CHECKED_TRACE.md` | recorded in PHASE_06_RESULTS.json |
| `labels/coverage.json` | `d7544c7eee739ae1d76aafc13f5d36044357ded9dda7d1602100e8540cd93c87` |
| `sealed/holdout_labels.jsonl.gz` | `e695500d01014936cf4a4a46f9975dcf9a9ca1351fe067f28ec36117cb82682b` |
| `sealed/SEAL.json` (seal digest of its files block) | `d5059baeb07099d5d73d74249d4487e362cb38b2e1dafe974139d2d4d0d25390` |
| `raw/MANIFEST.csv` | `f6ac14c05bee85c5e6c4f23e61b9d4c1ef95200907b1f679b5b7af6fa44c329f` |
| `evidence/label_calls.json` | `a37b09f0a61aa2e81bba3b6de139fcb522dd2f2d63b47935954dc43803eed02f` |
| `evidence/rebuild_from_archive.json` | `17e2ecbd27c759e388f3f5f78b56a4ab433470b97f5c3630cb0ac4ce18ab132e` |

## Limitations

- The frozen 48 h revision re-read (PI-D-018) has not run; earliest 2026-10-26T13:05Z (`make_labels.py reread48`). Shorter-gap evidence only.
- TRADING_HALT never occurs in development; the halt path is proven on fixtures and by one real reference-pool halt kept as a flag.
- Development has 9 (T1), 10 (T1b) and 8 (T2) decision days from one market regime; the CURRENT_VENDOR_LIST route is censored much more often than PIT_RECORDED.
- Provider-lag availability is a HEURISTIC reconstruction; `label_observed_at` is a 2026-10-24 retrieval time, never historical availability.
- These are price-path labels: no fill, size, depth or proceeds are claimed (PRICE_PATH_NOT_PROCEEDS, NO_HISTORICAL_EXECUTABLE_DEPTH).

## Repair pass 2 (2026-10-25, after the independent skeptic)

Input: `skeptic/PHASE_06_SKEPTIC.md` (copied with its scripts into `phase_06/skeptic/`; `p06_independent_out.json` stored gzip). The skeptic recomputed every development and purged label independently (standard library, not importing the lab's label code): all counts and 1,324 records per target identical. Each finding was verified first; decisions in PI-D-045 (and PI-D-044 for the forward collector). HEAD before: `121384b`.

| Finding | Verified | Repair | Check |
|---|---|---|---|
| M1 (MATERIAL): 14 of the skeptic's 17 mutations survive the label tests | yes: reran `skeptic/p06_own_mutations.py` logic; P0 from the open moves 25 real records | 13 tests pin P0 = close, thinning after eligibility, halt span start at 18 h (absolute times), overlap at the span start, exactly three other pools, a low at exactly 0.5 P0, rounding up on the grid, strict absence, inclusive pending and purge, lens values, the T2 to T1 invariant; `mutation_labels.py` extended | 44 of 44 mutations caught (`evidence/mutation_labels.json`); the gate's `censored` filter listed as equivalent |
| CX-S06 and m6: a `token=<mint>` body keeping the other token as base is accepted | yes: the skeptic's script prints CAUGHT False on `121384b` | `store.gt_identity` requires `meta.base == mint` with `token=<mint>` (TOKEN_PARAM_NOT_BASE); P0_FAR_FROM_SNAPSHOT_PRICE flag (P0 outside 0.1 to 10 times the snapshot price); Phase 05's test that accepted the default orientation corrected, FEATURE_STORE_CONTRACT.md amended | `test_cx_s06_*` (real ZEC/ZCAT pool and mints) and the asof store test fail on the first-pass code (`evidence/repair2_checks.json`); the skeptic's script now prints CAUGHT True; 0 of 207 real development token reads and 0 of 9 Phase 05 token reads refused |
| m1: gate trusts stored split and maturity | yes (`skeptic/p06_gate_attacks.py`) | split and maturity recomputed from the registry; a disagreeing row raises | `test_m1_gate_recomputes_split_and_maturity_from_the_registry`, `test_m1_gate_never_returns_a_purged_labeled_row` |
| m2: bake-off and sealed refusals not on the gate path | yes | the gate refuses a store file under the sealed or bake-off folder, besides the row check | `test_m2_gate_refuses_a_sealed_or_bakeoff_store_file` |
| m3: a revision leaving LABELED keeps the original | yes | the newest available version of every state decides | `test_m3_a_revision_that_leaves_labeled_removes_the_label` |
| m4: a rewritten SEAL.json passes the check | yes (reproduced in a throwaway copy) | `check_seal.py` requires the seal digest and SEAL.json's own sha256 (`f362ca12...`) in DECISIONS.md (PI-D-045 item 4) | throwaway copy: raw edit exit 1, raw edit plus rewritten SEAL.json exit 1 |
| m5: pre-registration not provable from git | yes, the file times are as the skeptic states | recorded honestly (PI-D-045 item 5): checklist header edited at 14:30Z, registry doc paragraph 14:31Z, Phase 04 had already seen BAKEOFF_ONLY T1 and T1b outcomes on development decisions; CC-03 changed 0 development states | |
| m8: public counts may bound holdout other-pool reads | plausible; not computed by anyone | holdout call, response, body and file counts removed from current public records (ledger, evidence, coverage report, roadmap, decisions, results); kept inside `sealed/`; history not rewritten; Phase 12 states it beside any T2 holdout result (PI-D-045 item 6) | `grep` of current public records |
| m7: release audit on a full clone flags another branch | yes, the blob is on local `work/backtesting-collector`, not reachable from this branch | noted only (PI-D-045 item 7) | this branch's audit passes |

Real data after the repair (no network): the development label tables were rebuilt in the private store with the repaired code: 4,026 of 4,026 rows identical in split, state, class, P0, flags and label key; holdout state counts identical; the archive rewrote byte-identical bodies and the same sealed label file (`e695500d...`), so `SEAL.json` was kept as committed (only its `made_at` would have changed); offline rebuild from the archive 0 differences. Development label counts unchanged: T1 136 (34 positive), T1b 224 (26), T2 131 (28).

Tests after the repair: `python -m pytest tests/test_predictive_labels.py tests/test_predictive_contract.py tests/test_predictive_asof_store.py tests/test_predictive_asof_features.py tests/test_predictive_asof_fixture.py -q`: exit 0, `197 passed` (label tests 58). The new tests run on the first-pass `labels.py` and `store.py`: 6 failed (the gate, revision, path, CX-S06, P0 flag and orientation tests), 95 passed; the M1 tests pin rules the first-pass code already applied and fail only under the mutations.

Skeptic's counterexample CX-S06 and what catches it now: a quote-side pool's response to `token=<mint>` that keeps the default orientation (meta base ZEC, quote ZCAT, ZEC prices) was labelled TARGET_FIRST for ZCAT with P0 1,161 against a snapshot price of 0.0456. Now refused at identity (TOKEN_PARAM_NOT_BASE, no candle, VENDOR_OR_ROUTE_GAP); had it passed, P0_FAR_FROM_SNAPSHOT_PRICE would flag it.

## Post-commit results

Run by the orchestrator on the committed tree at `4565e0b`, 2026-10-24 (the phase agent stopped at the provider usage limit before it could run them):

- `python -m pytest tests -q -p no:cacheprovider`: exit 1, `1 failed, 1107 passed in 165.16s (0:02:45)`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`. The stray `data/reports/<stamp>_BRETT_0x532f.md` and `data/memelab.sqlite-shm`/`-wal` were removed by hand; tracked `data/memelab.sqlite` sha256 unchanged.
- `python -m memelab social guard`: `"violations": []`.
- `python tools/release_audit.py --history`: `Needs action: no.`
- `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py`: `"problems": []`, seal sha256 `d5059baeb07099d5d73d74249d4487e362cb38b2e1dafe974139d2d4d0d25390`.

Not yet run: the independent skeptic (PI-D-013) and the frozen 48 h revision re-read (PI-D-018, PI-D-041). Phase 06 stays NEEDS_REVIEW.
