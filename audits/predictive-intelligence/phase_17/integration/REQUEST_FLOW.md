# Phase 17 request flow: from a discovered or changed opportunity to a forecast or a visible abstention

Code: `memelab/predictive/integration.py` (integration-1), `memelab/predictive/bt_adapter.py` (bt-adapter-1) and the hook in `memelab/cli.py`. Rules: `../ACCEPTANCE_CHECKLIST.md` (rules 1 to 17), PI-D-093. Tests: `tests/test_predictive_integration.py`. Evidence: `../smoke/`, `../evidence/`.

Research only. Nothing in this flow places, signs, sizes or suggests a trade, and nothing in it feeds the 100-point score, the fatal flags, the status, the watchlist or the scout lists (PI-D-017).

## Where the hook sits in the real path

The lab's verified path (read in the code, not the README):

```
python -m memelab fetch / save          browser or API pulls -> data/inbox/<id>.result.json
python -m memelab discover, stage2      stage-1 survivors, structural filter
python -m memelab scout --mints ...     cmd_scout:
  for each mint: pipeline.analyze_token   normalize.build_bundle -> modules m02..m22 -> m24 score -> m24 status -> m25 monitor
                                          -> m23 thesis -> report.render_token_report -> persist_result (thesis row, tokens,
                                          watchlist, rejections, token report file)
  scout_lists -> render_scout_report      the unchanged scout body (and the opt-in social section)
  _predictive_section(results, s2, t, path)   NEW (flag on only): integration.scout_section -> appended after the body
  path.write_text(md); print(md)
python -m memelab analyze <mint>        cmd_analyze: analyze_token, the existing line, then _predictive_line (flag on only)
```

With the flag off (`data/config.json` has no `predictive.enabled` equal to the JSON value true, or the file is missing or malformed) both helpers return None before any file other than the config is opened, so the report file and stdout are byte-identical to the code before Phase 17 (fixture test `test_g3_*`; real sandbox run `base_off` against `frozen_off`, `../smoke/REAL_PATH_SMOKE.json`).

## One pass

`integration.run_pass(results, capture_time=..., lab_db=..., state_dir=..., config_path=...)`:

1. Read the flag; off returns None.
2. Load and check the state (`load_state`: every line's record id, the pass chain, every file's sha256 against the last pass). Any difference is STATE_TAMPERED: nothing is assessed or written, and the section says so.
3. Load the Phase 16 registry (`read_entries`, `read_log`); an unreadable or tampered registry is REGISTRY_UNAVAILABLE and every target abstains MODEL_NOT_SELECTED with that detail.
4. For every result (linear, one database read each): identity (`store.check_address`, no default chain), the decision snapshot (the thesis row just persisted, read back read-only by mint and `created_at`, newest id), `snapshot_hash = decisions.row_sha256(row)`.
5. One per chain and mint per pass: the newest snapshot; the others SUPERSEDED_IN_PASS.
6. Per kept trigger, in order: the 30 s pass budget (else DEFERRED_LATENCY_BUDGET); `registry.serve` for each primary target as of the decision time (runtime facts of family 07; fixture champions only with `allow_fixture`, never from the CLI); the forecast ids; DUPLICATE when all three exist; otherwise the material gate against the last attempt at or before this capture (UNCHANGED names the covering forecast ids); the 64-attempt cap (else DEFERRED_QUEUE_FULL).
7. Attempted (DISCOVERY or MATERIAL_CHANGE): staleness (inputs older than 7,200 s at a CAPTURE_TIME decision: INPUT_STALE), eligibility (NOT_ASSESSED without a champion; with one, a single reference-price read through `runtime.CallGuard`), as-of features only when a champion is served or in research mode (`capture_features`: an in-memory store holding only this row and its token row, `features.features_as_of(..., mode="capture")`, feature version 2), then per target `abstention.forecast_result` with serve's inputs, `check_document` with the record, `verify_point` (the point and interval recomputed from the raw number kept in the request), persisted documents and records; research mode adds internal reference records (`registry.reference_record`, never documents).
8. Decision support beside the documents (`onchain.decision_support`): the lab's fatal flags as a veto, a size cap from collector depth only (COLLECTOR_NOT_AVAILABLE here, so EXECUTION_DATA_MISSING), the backtest adapter's veto; `position_usd` is always None.
9. Append requests, documents, records, references and the pass record (`abstention.append` with the sha the last pass recorded), then render the section.

## Events (exactly one per trigger)

| Event | Meaning | Documents |
|---|---|---|
| DISCOVERY | first attempt for this chain and mint | 3 (one per primary target) |
| MATERIAL_CHANGE | a frozen trigger fired against the last attempt at or before the capture | 3 |
| UNCHANGED | no trigger: covered by the last attempt (cache hit), named | 0 |
| DUPLICATE | this exact snapshot was already attempted with the same models (P35) | 0 |
| SUPERSEDED_IN_PASS | a newer snapshot of the same mint is in this pass | 0 |
| DEFERRED_QUEUE_FULL, DEFERRED_LATENCY_BUDGET | bounded work (P35, P48); visible, waits for the next scout pass | 0 |
| NO_DECISION_SNAPSHOT | no persisted thesis row (for example `analyze --no-persist`); not a decision | 0 |
| NOT_EXACT_IDENTITY | not an exact address of its chain, or no chain (P01) | 0 |
| ERROR | a component failed; the error class is recorded; the scout report still goes out | 0 |
| CATALYST_REFRESH_REQUESTED | catalyst pass: a new exact-address link for an attempted mint; the next scout pass reassesses | 0 |

Stage-2 structural rejects have no thesis row and are named in the section as not decisions.

## Material gate (frozen)

Material when any of: pool, status, the set of fatal flags, the exact-address catalyst fingerprint, the served model sha or pin event of any primary target differs (CX-17); integer score moved by 5 or more; price by 10% or more; liquidity by 20% or more; 24 h volume by 50% or more; one of these became known or unknown; the last attempt is 3,600 s or more before the capture.

## Visible states for outages (P47) and cost (P48)

| Situation | State shown | Effect |
|---|---|---|
| registry files missing or log chain broken | REGISTRY_UNAVAILABLE | every target abstains MODEL_NOT_SELECTED |
| state file changed, dropped or reordered | STATE_TAMPERED | nothing assessed or written |
| inputs older than 7,200 s at the capture | INPUT_STALE | eligibility INPUT_STALE, every target SOURCE_STALE |
| reader failure, timeout over 10 s, open breaker, priced call | VENDOR_OR_ROUTE_GAP with the guard state | SOURCE_STALE |
| no depth collector file | COLLECTOR_NOT_AVAILABLE | size EXECUTION_DATA_MISSING |
| catalyst tables absent | CATALYST_SOURCE_NOT_AVAILABLE | no refresh, no fingerprint |
| backtesting not installed | BACKTEST_NOT_AVAILABLE | in every document |

integration-1 opens no socket. The lab's CLI passes no reader; with no champion no read is needed. A reader (tests only) goes through `runtime.CallGuard`: 6 a minute, at most 64 calls a pass, a breaker after 5 consecutive failures and a cost cap of 0, so a priced call is refused before it is made. The real runs ran inside `unshare -n` (no network namespace).

## Persistence

State directory `data/private/predictive/` (gitignored) or `predictive.state_dir`: `REQUESTS.jsonl` (integration-request-1), `DOCUMENTS.jsonl` (integration-document-1 envelopes around contract documents), `RECORDS.jsonl` (abstention-1), `REFERENCE_RECORDS.jsonl` (research mode only), `PASSES.jsonl` (integration-pass-1, chained). Append only; every line carries its content hash. `python -m memelab.predictive.integration status|check|catalyst-pass --state-dir DIR`.

## Backtesting and what a merge would require (Elving's decision)

The backtesting module is on `origin/feature/backtesting` (PR #4, tip `69bc5c3`), not merged into this branch or `main`. Here `memelab.backtest` is not importable, so every document carries BACKTEST_NOT_AVAILABLE and no assessment reference. `bt_adapter` reads the assessment record that branch attaches to a scout result (`backtest_assessment`) or its `bt_assessments` table, read-only, on fixtures only (TEST_ONLY); its output stays in the request record and its fatal or untradeable states are an extra veto. A merge of PR #4 into this line would require:

1. Resolving `memelab/cli.py` by hand: both branches hook `cmd_scout` and `cmd_analyze` at neighbouring lines. Keep both hooks, both appended after the unchanged body, each behind its own flag (`data/backtest/policy.json` or `MEMELAB_BACKTEST`, and `predictive.enabled`), and run both P40 tests with both flags off together.
2. `contract.backtest_status()` would then say UNVERIFIED, not VERIFIED: the contract keeps refusing an assessment reference until a phase verifies the installed engine and records a change control for that rule.
3. Re-pinning `bt_adapter` (columns and vocabularies of `69bc5c3`) and `depth_adapter` (`bt_depth_schema_v2.sql` of `12f278b`) against the merged schema; a difference is SCHEMA_MISMATCH until then.
4. Running both suites together, the content guard and the release audit on the merged history (the backtesting branch carries a reviewed history blob, D-BT-016).
5. Keeping the backtesting LAB_STATUS strategy's `created_at` timing (PI-D-047) out of this engine.
6. The scheduled runs see nothing until a merge into `main` (PI-D-005).

## Limits (recorded, fail closed)

- Family 07 only: a champion of families 08 to 11 is MODEL_INCOMPATIBLE_RETRAIN_REQUIRED; a real champion gets INFERENCE_NOT_CHECKED (no Phase 12 probe inputs here). Both abstain.
- Capture features cover the thesis and token groups of the single row; history, universe and candle groups are missing with their reasons.
- A crash between two appends leaves a file sha that the next pass refuses (STATE_TAMPERED): a manual repair, never a silent continue.
- No scheduler: deferred events wait for the next scout pass; a catalyst refresh is a request for the next scout pass.
