# Phase 10 evidence: social and catalyst outcome forecasts without future text

Status: PASS after repair pass 2 (the orchestrator's independent skeptic: 2 MATERIAL, 6 minor, counterexamples CX-10b-A and CX-10b-B; each verified and repaired, see "Independent skeptic and repair pass 2"; PI-D-060). The catalyst classifier, the social evidence adapter and the catalyst proposals are TEST_ONLY. The cards carry `revision_check_claimed: false` as written; the Phase 06 48 h re-read changed no label and lifted PI-D-046's condition (PI-D-059).

- Branch `feature/predictive-intelligence`; HEAD before `1a52308`; pre-registration `c3f04c8` (2026-10-25T23:58:29Z); frozen code `0784a9a` (2026-10-26T00:20:46Z); outputs and records in the commit that carries this file (hash in HANDOFF.md and `PHASE_10_RESULTS.json` after the post-commit records commit).
- Package: `sha256sum -c SHA256SUMS.txt` 41 OK, 0 failed.
- Spend: 0 Firecrawl credits, 0 vendor calls, 0 language-model calls, 0 socket events in the runner; 1 `git fetch` of `origin/main` (COST_LEDGER.md).

## Entry gate (G2)

| Command | Result | Exit |
|---|---|---|
| `python -m pytest tests -q -p no:cacheprovider` at `1a52308` (2026-10-25T23:49Z) | `1 failed, 1279 passed in 179.56s`; the failure is the known `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` | 1 |
| stray files after the suite | `data/reports/20261025_2349_BRETT_0x532f.md` and `data/memelab.sqlite-shm`, `-wal`, removed by hand | |
| `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | `"problems": []`, seal digest `d5059bae...` | 0 |
| sha256 of `data/memelab.sqlite`, the p05 and p06 stores | `068287c0...`, `2525f0c4...`, `58213988...`, equal to Phase 09's run log | |

## Commands of this phase

| Command | Result | Exit |
|---|---|---|
| features-only probe (scratchpad, after `c3f04c8`, 00:02:17Z to 00:02:26Z) | socialcat-1 over 925 Solana decisions, 0 UNPARSEABLE; no label read, no fit (logged as the one debug run in the ledger) | 0 |
| `python -m pytest tests/test_predictive_social.py -q` (first pass) | 1 failed (fixture used a base58 address for a BSC token; corrected), then 1 failed (a test's own arithmetic; corrected), then `48 passed` | 0 |
| `python -B probes/mutation_social.py` (first) | 86 mutations, 71 caught, 15 survived | 1 |
| repairs after the survivors (before the code commit) | RUMOR reason made explicit, a redundant deleted-source branch removed (DELETED_SOURCE stays a withdrawal), 11 tests added, 1 mutation recorded as equivalent (fit's own maturity check behind `check_asof`, as Phase 08) | |
| `python -B probes/mutation_social.py` (second) | 85 of 85 caught, 1 equivalent reported apart | 0 |
| commit `0784a9a` (code, tests, probes, provenance, proposals) | before any fit on real labels | |
| `python -B probes/run_social.py audits/predictive-intelligence/phase_10 --npz ...` (recorded run 1, 00:20:50Z to 00:21:52Z, head `0784a9a`) | `{"targets": {"T1_24h": "OK", "T2_24h": "OK", "T1b_6h": "OK"}, "socket_events": 0, "stores_unchanged": true, "ledger_missing": 0}` | 0 |
| `python -B probes/run_social.py /home/claude/pi_orchestration/phase10/run2` (determinism) | 37 common files identical except the trace's latency (`evidence/determinism.json`) | 0 |
| `python -B probes/verify_trace_social.py evidence/trace/FORECAST_TRACE.json` | 8 values, 11 inputs, 8 models, 0 differences, token row equals its own export, pass | 0 |
| `python -B probes/recompute_oos_social.py` | 76 rows, 456 model values, 326 numbers recomputed without socialcat.py, features.py or stats.py, 0 differences | 0 |
| `p04_bundle/bin/python -B probes/sklearn_crosscheck_social.py arrays.npz evidence/sklearn_crosscheck.json` | 40 real logistic designs, newton-cholesky max coefficient difference 1.88e-11, Prep 4.9e-15, all within 1e-9 | 0 |
| `python -m pytest tests/test_predictive_social.py -q` (with the committed-outputs test) | `51 passed` | 0 |
| `python -B probes/mutation_social.py evidence/mutation_social.json` (with the committed outputs in place) | 85 of 85 caught, 0 survived, 1 equivalent | 0 |
| `python -m memelab social guard` | 0 violations | 0 |

## Post-commit results at `f4b3a89` (outputs and records commit)

| Command | Result | Exit |
|---|---|---|
| `python -m pytest tests -q -p no:cacheprovider` (2026-10-26T00:30:57Z) | `1 failed, 1330 passed in 181.86s`; only the known `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; strays removed by hand; `data/memelab.sqlite` sha256 unchanged | 1 |
| `python -m memelab social guard` | 0 violations | 0 |
| `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | `"problems": []` | 0 |
| `python tools/release_audit.py --history` on a single-branch clone at `f4b3a89` | `Needs action: no.` | 0 |
| `git status --short` | clean after the stray removal | |

Files: `postcommit/pytest_summary.txt`, `social_guard.out.txt`, `seal_check.json`, `release_audit_history.summary.txt`.

## What was built

- `memelab/predictive/socialcat.py` (numpy, the standard library, the predictive package and two reused social seams: `replay_core` and `alpha_core.wilson`; flag OFF; imported by no other module, test and runner check): socialcat-1 features, the models, the catalyst classifier, the read-only social adapter, the proposals. No file under `memelab/social`, `memelab/catalyst`, `memelab/chains` or `memelab/modules` changed since the branch base `f99c6c7` (`evidence/crosschecks.json`).
- `tests/test_predictive_social.py`, 51 tests: P03, P04, P15, P16, P17, P26, P36, P38, P41, P45, P13, PI-D-007 ticker and name links, CX-10, the event without post-event text (fixture twin), the duplicated influencer article, read-only adapter, model gates, cards, the walk-forward equality with Phase 07, the proposals, imports and isolation, committed outputs.
- Deliverables: `models/CATALYST_MODEL_CARD.md`, `data/CATALYST_PROVENANCE.md`, `models/CATALYST_TARGET_PROPOSALS.md`, `experiments/ABLATION.csv` (comparative ablation), the experiment tables, cards and evidence listed in `PHASE_10_RESULTS.json` with sha256.

## Result

- Data sufficiency: no social item and no catalyst event, link or assessment exists for any decision (FACT); every one of 925 Solana decisions carries CATALYST_TABLES_NOT_EXPORTED and SOCIAL_TABLES_NOT_EXPORTED; no verified catalyst, no catalyst probability; the catalyst-follow-through target stays BLOCKED_NO_DATA as a proposal.
- Models on the frozen targets: 306 metric rows, every one INSUFFICIENT_HISTORY (84), INSUFFICIENT_DAYS (120) or INSUFFICIENT_EVENTS (102); no incremental value of social features beyond B2 claimed; all MODEL_NOT_PROMOTED. Folds and B0/B2 equal Phase 07's (split fingerprints equal; 0 differences at 6 decimals).
- Leakage controls on real data: CX-10 925 of 925 token rows equal their own export (the newest export would add 20 narrative tags, 74 websites, 4 twitter links); export contexts 925 of 925 with equal blob and commit time; P04-SC 240 of 240 refused; NC2-SC 156 of 156 refused by both guards; P36-SC 19 of 19 INCONSISTENT_TIME; P13-SC all refused.
- Real cross-checks: inbox catalyst reads of 2026-10-07 name 11 Solana decision mints by exact address in the Coinbase asset list (a listing state, not an event; 14 counting EVM decision mints, which is the figure the checklist's pre-look gave over all chains), 1 in the DEX Screener boosts list (that mint's three later decisions show the lab's paid flag 0, a boost read days earlier is not a reading at those decisions), 0 in any news feed; ticker and name searches name 22 decision mints and are never identity.

## Iteration log

1. Pass 1 (this report): inspection and the data sufficiency statement; pre-registration `c3f04c8`; module, tests and probes; two test-fixture corrections; mutation probe 71 of 86, then 11 tests and two code clarifications, 85 of 85 plus 1 equivalent; frozen code `0784a9a`; one recorded run (exit 0, no repair of the runner was needed); determinism, trace, full out-of-sample recomputation, oracle, mutation at HEAD; records. Correction recorded: the checklist's pre-look said 14 decision mints in the Coinbase list; that count covered every chain, the Solana count used by the run is 11 (the checklist is pre-registration and is not edited). `data/CATALYST_PROVENANCE.md` was corrected after the recorded run to the run's counts (11 Solana mints in the Coinbase list, 22 in ticker searches), so its sha256 in `evidence/run_log.json` (which lists every file in the phase folder at run time) differs from the committed one; the committed sha256 is in `PHASE_10_RESULTS.json`.
2. Pass 2 (repair after the independent skeptic, PI-D-060): code commit `1c75a12` (classifier availability, follow-through entry rule, account labels as known at T, versions recorded after T, classifier edges, runner pinned to `e245d91`, G1 designs for the oracle; 5 new tests, 7 corrected, 17 new mutations); recorded run repeated at `1c75a12` with no number changed; outputs commit `06999b7`; records commit after.

## Own adversarial pass (not independent)

- Wrong-but-plausible designs tried against the code: reading the token row from the newest export (CX-10, caught by the stored token row and the export checks, real counts above); handing an earlier decision the next export's narrative tables (P04-SC, refused 240 of 240); treating a TICKER resolution the resolver marked `resolved` as identity (excluded by mention kind, test); counting an item deleted after T as unseen at T (the item counts, it was visible at T; deletions by T exclude it; test); taking a revision's `evidence_status` from the event row edited after T (UNKNOWN_AS_OF unless the row was last updated by T; test); a STRONG link whose mint sits only in a syndicated copy (not identity: only ORIGINAL and INDEPENDENT items count; conservative).
- Residual risks stated for the skeptic: `sc_narrative_strength` is built by m19 from Jupiter organic score, holder growth and trader counts, so it can overlap B2's volume column (collinearity, not leakage); the m19, m20 and m21 lines depend on the lab's code version at each export (PI-D-008), a changed meaning under the same wording is not detectable; the trace row falls in T1 fold 0 where the attention models abstain, so the trace recomputes B0, B2 and R2 numbers only, and the full out-of-sample recomputation covers the logistic and stump numbers.

## Counterexample of this phase

CX-10: the token row read from a later export (or the lab's `tokens` table) instead of the export that holds the decision. Caught by `socialcat_as_of` reading the token row stored with the decision, by `narrative_values` refusing tables whose commit, commit time or blob differ (`test_cx10_the_token_row_and_narrative_tables_come_from_the_decisions_own_export`, mutations "CX-10 context commit/time/blob not checked"), by the runner's provenance count (925 of 925) and by `verify_trace_social.py` comparing the stored token row with the export read from git. The skeptic's counterexamples CX-10b-A and CX-10b-B are recorded in the next section.

## Independent skeptic and repair pass 2

Review: `skeptic/PHASE_10_SKEPTIC.md` (attempt 10b, at `564be76`) with its scripts `skeptic/p10b_*.py` and outputs. The skeptic reproduced the recorded run, the oracle, the trace, every out-of-sample number, every socialcat-1 value of the 240 development rows (4,560 values, 0 differences, own code), the CX-10 and coverage counts, the suite, guard, seal check and release audit, and found no real-data number to change. Each finding was verified before repair (`evidence/cx10b_check.json` runs the counterexamples against the first-pass code `0784a9a`). Commits: code `1c75a12` (2026-10-26T14:34:34Z), outputs `06999b7`, records after (PI-D-060).

| Finding | Verified | Repair | Caught by |
|---|---|---|---|
| M1, CX-10b-A: a VERIFIED catalyst's `available_at` from first sighting and link, not from verification; follow-through could start before the decision | yes: at `0784a9a` the case gives VERIFIED with `available_at` T-2900 (UNVERIFIED_EVENT at T-1000) and labels a +30% move at T-1500 TARGET_FIRST | `available_at` is the latest of the first sighting, the strong links, the first independent item naming the mint, the start of the CONFIRMED status (`confirmed_since`, from the revision log; the row's `updated_at` without revisions) and the sighting that met the source rule; the classifier refuses a VERIFIED state without one at or before T; `proposed_follow_through_label` requires `decision_time` and starts at `max(available_at, decision_time) + lag`, refusing an availability after the decision. The test asserting the old rule (`test_verified_needs_*`) now states the new one | `test_cx10b_a_*` and `test_verified_availability_*` (fail at `0784a9a`), 8 mutations; `evidence/cx10b_check.json` (first pass: available_at T-2900, label 1; repaired: T-600, label 0) |
| M2, CX-10b-B: later suspensions and untimed BOT labels applied at earlier T | yes: at `0784a9a` mentions 1 and bot share 0.5 where the store as of T gives 2 and 0 (same for a BOT kind) | `account_as_of`: with no read time at or before T (a replay) an identity status counts only when recorded by T (its `identity_checked_at` and any ACCOUNT_STATUS review in `social_registry_reviews` that set it), else UNKNOWN_AS_OF; `account_kind` has no time and is UNKNOWN at T; such items count as accounts of unknown kind and are reported in `counts["account_label_unknown_as_of"]`; `accounts_read_at` at or before T (a live read) applies the row as read. Same rule for PROJECT (official) | `test_cx10b_b_*` (fails at `0784a9a`), 4 mutations; `evidence/cx10b_check.json` |
| m1 provenance incomplete | yes, with the skeptic's scripts at `e245d91`: `social_snapshots` 99 rows, 8 mints, 216 decisions; `upcoming_launches` 24 mints, 52 decisions (telegram 5, twitter 9, website 16 beyond the token row), `launch_cohort` 38, `launch_monitor` 18; boosts 3 mints (cat01, eco01, lp_t1_pump); 45 inbox files name decision mints (46 at the skeptic's earlier ref) | new section in `data/CATALYST_PROVENANCE.md`; "telegram 0 of 925" scoped to token rows | `evidence/provenance_rescan.json` |
| m2 "paid/boosted" wording | yes: m19 sets `organic` False when Jupiter's organic score is below 40 or a boost is active (`m19_attention_analysis.py` line 77) | card, provenance and proposals reworded | |
| m3 surviving mutant (versions after T) | yes; also a related defect: an item with only a version recorded after T was excluded at T although the truncated view counts it | `social_as_of` tests the versions visible at T (`if vs`) | `test_m3_*` (fails at `0784a9a`), 2 mutations; the skeptic's own mutation now caught (`evidence/skeptic_mutations_at_repair.json`: 16 caught, 1 equivalent as the skeptic found, 1 pattern renamed and covered by the phase probe's "P16 bots counted") |
| m4 G1 fits without an oracle | yes | the runner's `--npz` writes every fitted G1 design; `sklearn_crosscheck_social.py` refits them with GradientBoostingClassifier (the Phase 08 stump oracle): 10 designs, max probability difference 2.2e-16; the recomputation's scope stated (predictions from cards, features from the committed CSV) | `evidence/sklearn_crosscheck.json` |
| m5 classifier edges | yes | an item without a role is not independent (counted in `items_without_role`); OFFICIAL / STRONG is a strong link; an official source counts only when its own item names the mint | `test_classifier_edges_*`, 3 mutations |
| m6 `traps.json` depends on `origin/main` | yes (local `origin/main` is now `71fc50e`) | the runner reads the pinned `MAIN_REF` `e245d91` for the export walk, the newest export and the inbox first commits | repair run: `traps.json` byte-equal to the first pass with `origin/main` at `71fc50e` |

Repair run: `python -B probes/run_social.py audits/predictive-intelligence/phase_10 --npz <scratch>` at `1c75a12`, 14:34:40Z to 14:35:48Z, exit 0, `{"targets": {"T1_24h": "OK", "T2_24h": "OK", "T1b_6h": "OK"}, "socket_events": 0, "stores_unchanged": true, "ledger_missing": 0}`; a second run into a scratch folder (14:35:53Z) byte-identical. Against the first pass, 36 of 37 outputs are byte-equal and the trace differs by its latency only (`evidence/determinism.json`); the development store gained the 16 raw re-read rows of PI-D-059 (no label row) and the result did not change. Then: `verify_trace_social.py` 0 differences, `recompute_oos_social.py` 326 numbers 0 differences, oracle 40 logistic designs within 1.88e-11 and 10 stump designs within 2.2e-16 (exit 0), `cx10b_check.py 0784a9a 1c75a12` exit 0, `pytest tests/test_predictive_social.py` `56 passed`, `mutation_social.py` at HEAD 102 of 102 caught, 1 equivalent reported apart (exit 0).

Residual risks (not repaired, stated for later phases): `catalyst_event_sources.role` and the event `category` have no time in the lab schema, so a role or category changed after T cannot be detected (roles only gate independence, the category only names the type, and neither gives a number); in a replay the adapter can no longer exclude bot accounts at all, because no timed bot label exists in the lab, so replayed bot shares are lower bounds.
