# CM-2 change control: promotion from prospective evidence, fresh reference cards, the daily cycle

Approved by Elving on 2026-11-09 (ED-1 and ED-10 of `phase_21/release/OPEN_DECISIONS.md`). Decision PI-D-122. Written and committed before any code change, any label read and any fit of CM-2. Maintenance after Phase 21; the release decision (PI-D-115) is not reopened.

## Why

1. ED-1, PI-D-091: under the frozen ACCEPTANCE table SHADOW needs a first-opening retrospective evaluation, and the retrospective holdout was spent in Phase 12. So no model can ever reach SHADOW. Elving approved a new route through prospective evidence.
2. ED-10: the 69 frozen cards (cutoff 2026-10-17) have been MODEL_STALE since 2026-10-31. Elving approved retiring them and fitting fresh cards on all matured data.

## Part A: the new promotion route (PROMOTION_CM2)

The rule is written into `memelab/predictive/contract.py` as `PROMOTION_CM2`, with its own fingerprint `promotion_rule_sha256()` and a governing fingerprint `governing_sha256()` (target registry fingerprint plus the rule). Both are pinned by a test in `tests/test_predictive_contract.py`.

What changes:

- `ACCEPTANCE["promotion"]` is superseded for promotion decisions by `PROMOTION_CM2`. The ACCEPTANCE dictionary itself is not edited: the target registry fingerprint `4b4aabce...` stays, because the targets, label rules, holdout definitions and every minimum are unchanged and the fingerprint is the compatibility key of every stored label row and card. The governing fingerprint is new and is the one the promotion code and the daily cycle check.
- SHADOW comes only from a prospective window that starts strictly after the recipe's freeze (the commit time of `audits/predictive-intelligence/daily/RECIPE.json`), whose predictions were committed to git before any of its outcomes was read (Phase 19 discipline).
- VALIDATED_EXPERIMENTAL needs SHADOW and then a second, later prospective window that passes the same checks; for a candidate other than B2 its Brier point on that window must also not be worse than B2's (as in ACCEPTANCE).

What stays (every frozen minimum and correction):

| Item | Value | Source |
|---|---|---|
| events per window | at least 50 | ACCEPTANCE min_holdout_events |
| per class | at least 10 positives and 10 negatives | ACCEPTANCE min_holdout_per_class |
| decision days per window | at least 5 distinct UTC decision days | ACCEPTANCE min_effective_days |
| skill | Brier skill against B0 of the same recipe version in force at the decision; lower bound above 0 | ACCEPTANCE skill_reference, VALIDATED_EXPERIMENTAL bss_lower_bound_gt |
| interval | bootstrap by decision day and by mint, the wider (lower of the two bounds) governs, at least 2,000 replicates | ACCEPTANCE bootstrap |
| selection correction | Bonferroni over the cumulative N_search (130 today, from the ledger) times the number of windows already tried for that target and candidate: the bound is the alpha / (N_search x windows) lower quantile, alpha 0.05 | ACCEPTANCE multiple_testing, PI-D-065 |
| replicates | max(2000, ceil(10 x N_search x windows / alpha)), so the corrected quantile is resolved (26,000 for one window) | stricter than 2,000 |
| calibration | Wilson 95% interval of the observed rate holds the mean predicted probability, in the large and in every quantile bin of 20 or more events (at most 5 bins) | ACCEPTANCE calibration |
| tests | leakage, provenance and contract tests pass for the card | ACCEPTANCE promotion SHADOW requires |

Window rule (fixed now, before any prospective outcome of CM-2 exists):

1. A window belongs to one (recipe, kind, target). Predictions of every version of the recipe pool into it.
2. Days are UTC decision days after the start. A day is complete for a target when every predicted decision of that day has a final outcome (not PENDING or NOT_READ) for it. The window is the shortest run of complete days, from its start, whose scorable outcomes meet the three count minimums. Scorable: LABELED, uncensored, the prediction has a number.
3. A window is evaluated once, when it closes. The result is appended to the ledger (`WINDOW_RESULT`) and never recomputed for a promotion. A failed window counts: the next window starts after its last day, and its correction uses windows + 1.
4. Admissibility: every scored prediction precedes its outcome in the ledger sequence, and the first git commit of the ledger that holds the prediction has a commit time before the outcome's `label_observed_at`; every scored decision is after the recipe freeze; the card version that made the prediction was registered at or before the decision and was not stale. A window that fails admissibility cannot promote (WINDOW_NOT_ADMISSIBLE).
5. Nothing else promotes: a development, retrospective or in-sample evaluation never does; a level is recomputed from the ledger, never given.

Stated plainly: with today's data volume no card will qualify. The state exports on `origin/main` stop at `71fc50e` (2026-10-26); no decision exists after the recipe freeze, so the first window has 0 events. At the Phase 19 rate (about 7 to 8 labeled Solana decisions per day and target) a window needs at least 7 to 10 days of exports after they resume, and then it must also pass the corrected bound.

## Part B: fresh cards and retirement

1. Recipe R-CM2-1 (`daily/RECIPE.json`): B0 and B2 for the three primary targets, with the Phase 07 configurations already in the ledger (P07_B0, P07_B2). No search, no new configuration: N_search stays 130. Any configuration added later counts in N_search.
2. Training labels: everything `labels.training_labels` returns at the cutoff with the splits widened by a new, explicit argument: DEVELOPMENT (as before), the spent retrospective HOLDOUT (from the Phase 06 sealed file, verified against the Phase 12 seal pins; it was opened once in Phase 12 and can no longer support any promotion) and the Phase 19 PROSPECTIVE outcomes (scored once in Phase 19, verdict INSUFFICIENT_DAYS). This is stated: both may now be training data. The default of `training_labels` is unchanged (DEVELOPMENT only), so every earlier phase reproduces.
3. Missing labels: the state exports on `origin/main` after the last labeled decision are none (the newest export is `71fc50e`, the one Phase 19 read). The labels still missing for decisions in those exports are the 7 PENDING T2 outcomes of 2026-10-26 (OI21-1). They are read now with the frozen label rules: one OHLCV read per decision whose boundary is the T2 window end on the candle grid, `token=<mint>`, other pools only for an evidenced reference halt, free GeckoTerminal only, paced by `runtime.CallGuard` at 5.7 calls a minute (never more than 6 in 60 s), at most 40 calls, raw bodies archived gzip with sha256 in `maintenance/cm2_promotion_cards/raw/`, every call in `evidence/label_calls.json` and the total in `COST_LEDGER.md`. The Phase 19 ledger and folder are not edited (they are a frozen record with their own rebuild test); the labels enter the CM-2 base label set.
4. Cutoff: the largest `label_matures_at` among the LABELED rows available now. Expected stated in advance: the 7 T2 labels mature 2026-10-28, so the fresh cards go MODEL_STALE about 2026-11-11 unless new exports arrive. That is a data fact, not hidden: the alert says so.
5. Registry: a CM-2 registry (`daily/registry/`): hash-addressed entries and an append-only, sha-chained log (events REGISTER, PIN, RETIRE). The 69 Phase 16 entries are RETIRED (an event naming each entry id and the Phase 16 log head; the entries and the Phase 16 log are kept unchanged). Each fresh card is REGISTERED with a level recomputed by the CM-2 rule (ABSTAIN for a reference with no window passed, NO_GO for a candidate; here both kinds are references). One PIN per target: NO_VIABLE_CHAMPION with the fresh B0 and B2 as references.
6. Retrain cadence before MODEL_STALE: when the newest version's age is 7 days or more and at least one label matured after its cutoff, refit the same recipe (a new version, registered, the previous one SUPERSEDED by the new PIN, never deleted). With no new labels nothing is refit and the alert says NO_NEW_MATURED_LABELS.
7. integration-1 (the scout hook) keeps reading the Phase 16 registry: changing what the scout reads is a separate change control. Its answers stay ABSTAIN either way.

## Part C: the daily cycle

One command: `python -B audits/predictive-intelligence/daily/predictive_daily.py run`. Steps, in this order, each refusing to start if the one before failed:

1. lock and preflight (repository clean under the audit folder, ledger verifies, recipe and governing fingerprints equal the pins);
2. read new state exports (`git fetch origin main`, then exports up to `origin/main`), rebuild the private store (exports and feature snapshots only);
3. for every new Solana decision after the recipe freeze: one PREDICTION per target and kind (a number from the version in force, or an abstention with its reason), appended to the ledger;
4. commit the ledger (only paths under the audit folder) and check that HEAD holds every prediction before any read;
5. fetch matured labels (free GeckoTerminal, paced at 5.7 a minute, at most 60 calls and 25 minutes per run, breaker after 5 failures, raw bodies archived with sha256, calls logged, one line in COST_LEDGER.md);
6. append outcomes (labels-1 through `monitoring.prospective_records`);
7. evaluate windows with PROMOTION_CM2, append WINDOW_RESULT entries;
8. retrain on cadence;
9. write `daily/ALERT_SUMMARY.txt` (short, for a push notification) and the run record; commit.

Idempotent: a second run with nothing new appends nothing and makes no call. Writes only under the private state directory (default `data/private/predictive_daily/`, git-ignored), `audits/predictive-intelligence/daily/` and one line in `audits/predictive-intelligence/COST_LEDGER.md`, plus git commits whose paths are only those. Exit 0 when the cycle completed; otherwise a nonzero code with a named reason (`LOCKED`, `PREFLIGHT_FAILED`, `EXPORT_FETCH_FAILED`, `PREDICTION_COMMIT_FAILED`, `LABEL_FETCH_FAILED`, `LEDGER_REFUSED`, `TIME_BUDGET_EXCEEDED`, `RETRAIN_FAILED`). The scheduled task itself is not created here (the orchestrator does that).

## Acceptance checklist (measurable; each item is checked in the evidence)

| Id | Item |
|---|---|
| G1 | This change control and `daily/RECIPE.json` are committed before any code change, label read or fit of CM-2 (git order) |
| G2 | `ACCEPTANCE` is byte-identical; `registry_sha256()` still `4b4aabce...`; `PROMOTION_CM2` and both new fingerprints pinned by a test; a test proves every frozen minimum in PROMOTION_CM2 equals ACCEPTANCE's value |
| G3 | the promotion function refuses: a window before or at the freeze, a prediction committed after its outcome's read, below 50 events, below 10 per class, below 5 days, a corrected lower bound at or below 0, a bin outside its Wilson interval; and gives SHADOW then VALIDATED_EXPERIMENTAL only on fixtures that pass two windows; each with a test |
| G4 | tests that fail on the old code: the contract pin test, the `training_labels` split test, the promotion tests (module absent), the daily tests (script absent); shown by a probe on a copy of the old code |
| G5 | the 7 T2 labels read with the frozen rules (token=<mint>, end-time boundary), at most 6 calls in any 60 s, bodies archived with sha256, logged, COST_LEDGER line |
| G6 | fresh cards: 6 (B0 and B2 by 3 targets), fitted through `training_labels` with the widened splits, cutoff as stated, label set and feature counts recorded, reproduced byte for byte by a second fit |
| G7 | registry: 69 RETIRE, 6 REGISTER, 3 PIN events; log verifies; levels ABSTAIN with the CM-2 reasons |
| G8 | the daily command runs end to end in a fresh clone (no private store), twice: the second run appends nothing and makes no call; exit codes and named reasons tested; writes only in the allowed paths (checked by a file listing before and after) |
| G9 | mutation probe on `promotion.py` and the daily cycle's guards: every mutation caught by a test |
| G10 | full suite (only the two known clock-dependent failures), social guard 0 violations, seal 0 problems, reproductions pass, single-branch release audit with history exit 0 |
| G11 | records: HANDOFF, ROADMAP maintenance section, DECISIONS (PI-D-122 to PI-D-129 only), RELEASE.md current state, OPEN_DECISIONS ED-1 and ED-10 closed, SKEPTIC_PACKET.md; git status clean; not pushed |
