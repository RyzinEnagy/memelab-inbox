# Phase 05 evidence: provenance-preserving point-in-time feature storage

Status: NEEDS_REVIEW (first pass; the orchestrator runs the independent skeptic, PI-D-013). Branch `feature/predictive-intelligence`, HEAD before `074953d`, work 2026-10-24T10:15Z to 11:45Z (UTC). Package verified (`sha256sum -c SHA256SUMS.txt`: every line OK). Acceptance checklist written before any change: `ACCEPTANCE_CHECKLIST.md` (A1 to A28).

## What was built

- `memelab/predictive/store.py`: the private point-in-time store (schema v1, eight append-only `predictive_*` tables, checksum-ledger migrations and a rollback that restores the database byte for byte), identity checks (base58 to 32 bytes, EVM address or pool id), epoch-seconds unit checks, export ingestion through `decisions.py`, vendor read ingestion with the boundary rule, candle validation by `outcomes_core.normalize_observation`, vendor identity check, revisions, late appearances and tombstones, series statuses, `verify`.
- `memelab/predictive/sources.py`: git reader of every export version (first parent, oldest first), the development-period plan with the holdout seal, the paced fetch through `runtime.CallGuard`.
- `memelab/predictive/features.py`: the as-of view (SQL filter, `outcomes_core.visible`, `replay_core.Audit` with `LeakageError`), 32 features of version 1, `features_as_of`, immutable snapshots, `training_view`, the ported row validator, the truncation proof.
- Tests: `tests/test_predictive_asof_store.py` (37), `tests/test_predictive_asof_features.py` (25), `tests/test_predictive_asof_fixture.py` (4); helpers and real fixtures in `tests/fixtures/predictive/asof_*`.
- Deliverables: `data/FEATURE_STORE_CONTRACT.md` (contract and versioned schema), `data/SOURCE_COVERAGE.md` (source matrix and counts), `data/backfill_plan.json`, `data/series_status.json`, `raw/` (147 gzip bodies, 3.4 MB, `raw/MANIFEST.csv`), `evidence/*.json`, `probes/*.py`. The phase prompt names `data/FEATURE_STORE_CONTRACT.md`; it sits in this phase's `data/` sub-folder because tracked `data/` belongs to the scheduled runs.
- Not changed: `db.py`, every existing schema, migration, module and test; nothing under `inbox/`, `state/`, `data/`. `memelab/predictive/__init__.py` docstring lists the modules. Flag OFF; no existing module imports the package.

## Commands and results

| Check | Command (from the repository root unless noted) | Exit | Result |
|---|---|---:|---|
| A1 package | `sha256sum -c SHA256SUMS.txt` (package folder) | 0 | all OK |
| A2 entry gate | `python -m pytest tests -q` at `074953d` (10:15:38Z) | 1 | `1 failed, 993 passed in 146.88s`, only `test_dedup_corroboration_resurface_denial`; stray `data/reports/20261024_1015_BRETT_0x532f.md` removed |
| Exports | `python -B build_store.py exports` (probes/) | 0 | 89 versions, 1,501 decision events, 1,500 stored, 1 refused (31-byte mint), 0 versions skipped |
| Plan and seal | `python -B build_store.py plan` | 0 | 96 series, 541 decisions; max boundary 2026-10-16T10:42:06Z, allowed up to 2026-10-16T23:00:00Z; fetch scope DEVELOPMENT 541, NOT_FETCHED_SEALED 62, NO_POOL_AT_DECISION 322, OUT_OF_SCOPE_CHAIN 575 |
| Backfill | `python -B build_store.py fetch` (10:37:19Z to 11:13:26Z) | 0 | 127 calls, 112 HTTP 200, 15 HTTP 429 (retried after 60 s); 85 OK, 2 NO_DATA, 9 later IDENTITY_MISMATCH; 88 candles dropped for ending after the boundary |
| Identity rebuild | `python -B build_store.py rebuild` then `token` then `rebuild <store with token reads>` | 0 | first-run bodies replayed offline: 103 OK_BASE, 9 MINT_IS_QUOTE refused; 9 series re-read with `token=<mint>` (11:14 to 11:16Z): 9 OK_TOKEN_PARAM |
| Inbox comparison | `python -B revision_check.py inbox15` (11:16:46Z to 11:18:05Z), then `inbox15cmp` (offline) | 0, 0 | 8 calls; first pass superseded (assumed every inbox read asked for `token=<mint>`); verified pass: 3 pools 198 of 199 identical and 1 OPEN_WINDOW each; 1 pool priced another token in 2026-10-06 (closes differ by a median factor 3,325, volumes within 0.15%) |
| Snapshots | `python -B build_store.py snapshots` | 0 | 1,500 provider and 1,500 capture snapshots (16.0 s and 9.3 s) |
| Truncation, real | `python -B asof_real_checks.py truncation` | 0 | provider: 1,500 checked, 0 differences (433.7 s); capture: 1,500 checked, 0 differences (45.7 s) |
| Traps, real | `python -B asof_real_checks.py traps` | 0 | 40 sampled development decisions with candle values: extreme candle available 1 s after: 0 snapshots changed; available at the decision: 40 changed |
| Re-read | `python -B build_store.py reread 10` (11:27:47Z to 11:29:39Z) | 0 | 10 series, 11 calls, all OK_BASE; `revision_check.py store`: 7,223 candles unchanged, 0 changed, appeared or vanished; gaps 19 to 51 min |
| Phase 04 comparison | `python -B revision_check.py p04` | 0 | 84 pools, 57,584 positions in both, 57,504 identical, 80 differ in open only (36), open and low (23), open and high (21); 0 in close or volume; gap 2.5 h; 9 Phase 04 pools skipped (their bodies priced another token) |
| Recompute | `python -B asof_real_checks.py recompute` (after the re-read) | 0 | 3,000 snapshots, 0 differ, `verify` problems [] |
| Fresh processes | `python -B asof_real_checks.py fresh` | 0 | 25 sampled snapshots recomputed in two fresh processes, both equal to the stored hashes |
| Archive rebuild | `python -B build_store.py archive`, `fromarchive <tmp>` | 0, 0 | 147 files, 3,375,127 bytes; offline rebuild from `raw/`, `data/series_status.json` and git: 1,500 snapshots, identical hashes, verify [] |
| Coverage | `python -B coverage_counts.py`, `build_store.py summary` | 0, 0 | `evidence/coverage_counts.json`, `evidence/store_summary.json` |
| Phase 05 tests | `python -m pytest tests/test_predictive_asof_store.py tests/test_predictive_asof_features.py tests/test_predictive_asof_fixture.py -q` | 0 | `66 passed` |
| Mutations | `python -B mutation_asof.py ../evidence/mutation_asof.json` | 0 | control passes; 35 of 35 mutations caught; 3 single-layer mutations of deliberately doubled protections survive alone and are caught when mutated together (reported in the file) |
| Pre-commit suite | `python -m pytest tests -q` (staged tree checks: guard 0 violations, release audit exit 0, tracked-file tests 206 passed) | 1 | `1 failed, 1059 passed in 151.20s`, only the known failure |
| Deliverables commit | `git commit` | 0 | `b4baa78b9c744e0a4e4c0a9c5d6a924bda27fbac` (2026-10-24T11:38:13Z) |
| Post-commit suite | `python -m pytest tests -q` on `b4baa78` | 1 | `1 failed, 1059 passed in 165.68s`, only the known failure (`postcommit/pytest_summary.txt`); stray BRETT report removed |
| Post-commit guard | `python -m memelab social guard` | 0 | `"violations": []` (`postcommit/social_guard.out.txt`) |
| Post-commit release audit | `python tools/release_audit.py --history` | 0 | "Needs action: no"; no Phase 05 file named (`postcommit/release_audit_history.summary.txt`) |
| CLI regression | `python -B probes/cli_regression.py 074953d b4baa78 postcommit/cli_regression.json` | 0 | 6 commands (`--help`, `init`, two `analyze`, `scout`, `catalyst fc-health`) in two clean clones with temp DBs and the network cut: outputs and report files identical; exits 0, 0, 0, 0, 0, 1 on both sides (fc-health without a key) |

Calls: 155 GeckoTerminal calls in all, at most 6 in any 60 s window across both call logs (checked from `evidence/backfill_calls.json` and `evidence/revision_check_inbox15.json`); 0 Firecrawl credits, no WebSearch or WebFetch (COST_LEDGER.md).

## Acceptance checklist results

| Id | Result |
|---|---|
| A1, A2 | reproduced (above) |
| A3 | `connect` refuses the tracked DB and `MEMELAB_DB` (test); `init_db` creates no predictive table (test); no existing schema file changed (`git diff --name-only`) |
| A4 | migrate then rollback on a database with the lab, social, catalyst, chains and launch tables: schema and rows identical (test); edited migration refused; UPDATE and DELETE refused on all 8 tables (8 tests) |
| A5 | 31-byte base58 refused (real export string), case variants distinct, EVM pool ids accepted only as pools, one pool one mint (tests); no symbol column exists |
| A6 | decision rows from `decisions.py` unchanged; Phase 00 skeptic's SQL on real rows of export `996190ce` imported with `state.import_` finds the write lag in 4 mints, and every stored decision is at or after both `created_at` and the token's `first_seen_at` (test); other bases refused by code and by a CHECK; re-import adds 0 rows; a partial history is refused |
| A7 | raw read kept with hash and retrieval time, same read twice adds nothing, boundary candle dropped, malformed, unfinished and millisecond candles refused, revisions, appearances and tombstones as new versions (tests); real data: 98 boundary candles dropped, 8,212 candles of quote-side bodies refused |
| A8 | provider and capture modes (tests); real capture snapshots hold NOT_RETRIEVED_BY_DECISION for every candle value of a historical decision |
| A9 | 1 s after absent, at the decision present (test, and 40 real traps); audit raises LeakageError when both filters are bypassed (test); row validator (test) |
| A10 | deterministic in process and across fresh processes (test and 25 real snapshots); other version refused; malformed identity refused; value XOR reason with basis (code, CHECK, test); DATA_TIME_CONTRACT fields on every value row (test) |
| A11 | stored snapshots unchanged after a later revision and a later edited export, `recompute_matches` true (test); real: 3,000 of 3,000 equal after the re-read; drift refused (test) |
| A12 | 0 differences over 1,500 real decisions in each mode; a peeking feature is caught (test); traps sensitive at the decision |
| A13 | a later mint changes nothing, one exactly at the decision does (test); training view takes decisions up to its as-of and refuses another version (test) |
| A14 | outage gives READ_FAILED, the breaker opens after 5 failures, network errors are READ_FAILED, values MISSING VENDOR_READ_FAILED with source status visible and decision features kept (tests) |
| A15 | NO_DATA pool keeps its decision and snapshot with VENDOR_NO_DATA (test); real: 2 pools, 2 decisions |
| A16 | plan refuses a boundary in the holdout contact window even with a broken development rule (test); real: max boundary 2026-10-16T10:42:06Z; 0 holdout, purged or contacted decisions read; no label code (the modules compute no barrier or class) |
| A17 | 155 calls, at most 6 in any 60 s, under 1,200, breaker 5 (logs) |
| A18 | re-read 10 of 96 series (10.4%) and two more comparisons (above); the 48 h rule stays Phase 06's |
| A19, A20, A21 | `data/SOURCE_COVERAGE.md`; `data/FEATURE_STORE_CONTRACT.md` checked against the code by a test; `tests/fixtures/predictive/asof_fixture.json` (real rows of 3 mints from 12 exports, 4 real reads including a refused quote-side read and its `token=<mint>` re-read) with 8 pinned snapshot hashes |
| A22 | sockets and the curl wrapper raise inside the Phase 05 tests; temp files; fixed clocks; 35 of 35 mutations caught |
| A23 | `git diff --name-only 074953d b4baa78` lists only `audits/predictive-intelligence/`, `docs/predictive-intelligence/`, `memelab/predictive/` (three new modules and the package docstring), `tests/test_predictive_asof_*.py` and `tests/fixtures/predictive/asof_*`; existing syntax-tree test confirms no existing module imports the package; new modules import the standard library and existing lab modules only; CLI outputs identical; tracked DB sha256 `068287c0...` unchanged; nothing under `inbox/`, `state/`, `data/` |
| A24 | post-commit suite, guard and release audit above |
| A25 | 147 gzip bodies, 3.4 MB, every file and body sha256 in `raw/MANIFEST.csv`; largest committed file `tests/fixtures/predictive/asof_fixture.json` (189,461 bytes); no venv, pickle, key or social content |
| A26 | COST_LEDGER.md row: 0 credits, 155 free calls |
| A27 | records written; style scan of every file this phase wrote: no dashes, curly quotes or listed marketing words; status NEEDS_REVIEW |
| A28 | two commits (deliverables `b4baa78` and the records commit on top); `git status` clean including ignored files (the ignored set equals the one at the start); not pushed |

## Findings (beyond the gate)

1. Vendor identity (PI-D-038): without `token=<mint>`, GeckoTerminal prices the pool's base token; for 9 of 96 development pools the mint is the quote token. Phase 01's probe and Phase 04's bake-off requested no token parameter: 8 of 102 T1 and 9 of 159 T1b BAKEOFF_ONLY events were computed on another token's price (counted from the bodies' meta, no class looked at). The vendor's default side can change over time (inbox read of 2026-10-06).
2. Window-dependent open (PI-D-037 item 5): 80 of 57,584 candles read twice differed only in open, high or low; closes and volumes never differed. Features use closes and volumes; Phase 06 barrier tests on highs and lows inherit this.
3. Partial export history (PI-D-037 item 4): computing decisions over a subset of export versions turns a re-exported old row into a false new decision; the store refuses such a call.
4. A 31-byte "mint" in the exports (PI-D-022 check): refused and counted.

## Iteration log (bounded loop, first pass)

| Pass | What changed | Why |
|---|---|---|
| 1a | store, sources, features, tests | build |
| 1b | EVM pool ids accepted as pools | 49 EVM decisions had a Uniswap v4 bytes32 pool id and were first refused |
| 1c | full-history rule | own test: a single later export created a false decision |
| 1d | vendor identity check and `token=<mint>`; store rebuilt offline from the first run's bodies | 3 of the first 40 bodies named the mint as quote |
| 1e | period filter on candles and series | the inbox comparison would have mixed 15-minute candles into 5-minute features |
| 1f | closes only for drawdown and range; `revision_kind` | Phase 04 versus Phase 05 comparison showed window-dependent opens |
| 1g | inbox comparison redone offline with recorded request URLs | the first pass assumed a token parameter the early plans did not have |
| 1h | 4 tests added; mutation list made explicit about doubled protections | first mutation run: 5 of 33 survived (two doubled layers, no uncovered-window test, the holdout pad unreachable through the plan) |

## Own adversarial pass (not independent)

Counterexamples tried against this phase and what caught them: a candle available exactly at versus 1 s after the decision (real traps and test); a feature that peeks one day ahead and hides it from the audit (truncation check); a revised candle read after the decision (stored snapshots unchanged); a late-appearing candle inside an earlier read's window (APPEARED, available from its read); a read that prices the other token (identity check, real data); a partial export history (refused); a millisecond timestamp (refused); a 33-byte or 31-byte base58 string (refused); a holdout boundary with a broken development rule (refused). The independent skeptic's counterexample is added in the repair pass.

## Limitations

- Candle availability for past decisions is a reconstruction (HEURISTIC); revisions before the lab's first read are invisible. Revision gaps measured: 19 min to 2.5 h on the lab's own reads, 17 days on 3 inbox pools.
- DEX type per pool is not recorded; executable depth for past times does not exist (P08).
- `cover_complete` cannot tell the vendor's retention limit from a pool's first trade.
- The store file itself is outside git; its reproducibility rests on the committed raw archive, `data/series_status.json` and the exports in git (rebuild check identical).
