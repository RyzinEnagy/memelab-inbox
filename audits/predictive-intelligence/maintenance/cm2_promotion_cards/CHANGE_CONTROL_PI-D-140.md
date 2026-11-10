# CM-2 repair pass: change control PI-D-140 (skeptic findings 1 to 6 and counterexample CX-CM2-1)

Written 2026-11-10, before any code change of the repair, after the orchestrator's independent skeptic review of `cdff266` (`skeptic/CM2_SKEPTIC.txt`; scripts `skeptic/cm2_counterexample.py`, `skeptic/cm2_refit.py`). The skeptic found no material failure, six minor findings and one counterexample. The orchestrator requires items 1 to 6 below before any window can close. The CM-2 range PI-D-122 to PI-D-129 is used up and PI-D-130 to PI-D-139 belong to CM-3, so this is PI-D-140.

## Counterexample CX-CM2-1

A later commit replaces the ledger with a fresh, self-consistent chain (different prediction numbers) after the outcomes were read. `monitoring.verify` passes, `commit_times()` keys anchors by line number so the rewritten lines keep the first commit's time, and `promotion.admissibility` reports nothing. Reproduced here at `cdff266`: "COUNTEREXAMPLE HOLDS".

## Changes (frozen code, so each is a change control item)

1. Ledger history (finding 1, CX-CM2-1). `predictive_daily.commit_times()` walks the commits that touch `LEDGER.jsonl` in order (first parent) and requires each committed ledger to be `monitoring.is_append_only` of the one before it. Anchors are by content: a line's anchor is the time of the first commit whose ledger holds that exact line text. If any commit breaks the append-only rule, no line has an anchor, so every window is WINDOW_NOT_ADMISSIBLE, and the alert and `verify` name LEDGER_HISTORY_NOT_APPEND_ONLY. The counterexample becomes a test (and a check script) that must say "caught".
2. Push before reads, and the branch (finding 2). `run` refuses to start unless HEAD is the branch `--branch` (default `feature/predictive-intelligence`). Before the first label call of a run, the script pushes HEAD to `--push-remote` (default `origin`) on that branch, fast-forward only (no force), and checks that the remote ref equals HEAD; otherwise it stops with PREDICTION_PUSH_FAILED and reads nothing. After its last commit it pushes again (PUSH_FAILED on failure). So GitHub's record of the push holds the predictions before any outcome is read. `main` and any other branch are refused as targets.
3. A writable promotion path, references never SHADOW (finding 3). `promotion.level()` never gives SHADOW or VALIDATED_EXPERIMENTAL to a REFERENCE_BASELINE: a reference stays ABSTAIN (reason REFERENCE_BASELINE_NEVER_PUBLISHED, with the count of passed windows). A new log event PROMOTE (entry, level, the window results it rests on) is accepted only for a CANDIDATE entry and only when `level()` recomputed from those results gives that level; a CHAMPION pin needs a champion whose promoted level is publishable. The daily cycle writes PROMOTE and a CHAMPION pin when a CANDIDATE kind of the recipe reaches SHADOW. R-CM2-1 has only references (B0, B2), so today nothing can be promoted; the path is tested on fixtures.
4. Windows per recipe (finding 4). `window_results()` filters by recipe_id as well as target and kind.
5. Negative-class minimum (finding 5). A test that `evaluate_window` refuses a closed window with fewer than 10 negatives on its own.
6. Limits (finding 6). `--max-calls` 0 to 60 (the change control's per-run cap). `--now` is refused unless the environment variable `PREDICTIVE_DAILY_TEST_CLOCK=1` is set (tests only).

Left, with reasons (finding 6 rest): the registered_at of a retrained version is the run start, minutes before its commit (it only delays when a version counts as in force; fail closed); entry tests leakage and provenance are literals True at registration (they record that the card passed `baselines.verify_card` and `check_asof` in the fit; a later change control can attach the test run ids).

## Tests changed

The end-to-end fixture and runner of `tests/test_predictive_daily.py` and `tests/test_predictive_cm2_guards.py` check out the branch by name, add a local bare repository as the push remote, pass `--push-remote` and set `PREDICTIVE_DAILY_TEST_CLOCK=1`. `tests/test_predictive_promotion.py`: the two assertions that a passing window gives a REFERENCE_BASELINE SHADOW or VALIDATED_EXPERIMENTAL now use role CANDIDATE, and a reference is asserted ABSTAIN. Each new guard gets a test that fails on `cdff266`.

## Recorded runs after the change

Repeated from the new frozen commit: the fresh-clone daily runs (with a local bare push remote) and the mutation probe; the cards and registry are not refit (no fit code changes). Outputs that change are listed in the evidence with the reason.
