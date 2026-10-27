# Registry schema (registry-1)

Code: `memelab/predictive/registry.py` (numpy, the standard library, `contract` and `stats` only; flag OFF; imported by no other lab module). Rules: `../ACCEPTANCE_CHECKLIST.md` rules 4 to 12 and PI-D-085. Data: `../registry/`.

## Files

| Path | What it is | Written how |
|---|---|---|
| `registry/entries/<entry_id>.json` | one immutable entry per frozen card (69) | `write_entry`: write once; an existing file must hold the same bytes; the file name is the entry id |
| `registry/REGISTRY_LOG.jsonl` | append-only event log (REGISTER, ENSEMBLE_DECISION, PIN, ROLLBACK) | `append_events` with the sha256 the file had after the last append; `read_log` refuses a changed, dropped, reordered, non-canonical, partial or out-of-time-order line |
| `registry/REGISTRY_INDEX.json` | summary per target (mode, references, levels, ensemble decision) and the plain statement of the state | derived from the entries and the log |
| `registry/TODAY_STATUS.json`, `TODAY_RESULTS.jsonl`, `TODAY_RECORDS.jsonl` | the registry's answer at 2026-10-27T00:00Z: abstention-1 documents and records for the prospective decisions | `abstention.forecast_result` with what `serve` resolves, checked by `validate_publication` |

## Entry

The entry id is the sha256 of the canonical JSON of the entry without `entry_id` (sorted keys, no spaces, no NaN). `verify_entry` refuses an entry whose keys differ from the list below, whose id differs, whose level, registry status or publishable flag differ from what its facts give, or whose card, card file or calibration card (when given) is not the one it names.

| Key | Meaning |
|---|---|
| `registry_version`, `entry_kind` | `registry-1`, `MODEL` |
| `is_fixture` | true only in tests and the fixture rollback demonstration; a fixture entry is never pinned in a real registry |
| `target`, `target_version`, `target_registry_sha` | the registered target, its version and the registry fingerprint the card was trained under (`4b4aabce...`) |
| `family` | `phase` (07 to 11), `kind`, `candidate` id, `module_version` (baselines-phase07, tech-1, onchain-1, socialcat-1, analog-1; read from the card by the caller) |
| `model_id`, `model_sha` | the card's id and sha (sha256 of the canonical card without `model_sha`, recomputed) |
| `card_path`, `card_file_sha256` | where the frozen card is and the sha256 of its bytes |
| `feature_set_sha`, `feature_version`, `family_version` | the versioned feature and transform definitions the card was trained on (P46) |
| `training_cutoff`, `training_cutoff_utc`, `max_train_decision_time`, `max_train_label_matures_at`, `n_train`, `k_train` | training cutoff and the training set's last decision, last label maturity and counts |
| `labels_version`, `label_set_sha`, `data_snapshot_sha` | label version (`labels-1`), the sha of the training labels and the dataset (decision snapshots) sha |
| `fitted`, `abstain_reason` | whether the card holds a model or abstains, and why |
| `source` | `STATISTICAL_MODEL`; anything behavioral is refused (P27) |
| `calibration` | for B2: Phase 13 calibration card path, card sha, file sha256, status, level, details; null otherwise |
| `facts` | the inputs of `promotion_decision`: role, kind, fitted, tests, training counts, the FIRST_OPENING retrospective evaluation (n, k, days, calibration flags, BSS, governing lower bound, Holm p, verdict), POST_OPENING selection states, selection status, comparison with B2, calibration status and evidence, prospective status |
| `evidence` | development verdicts (view ALL) and the sha256 of every committed file the facts come from |
| `min_support` | the ACCEPTANCE gates (training 100 and 20, holdout 50 and 10, bin 20, days 5, prospective 50) |
| `risk_flags` | PRICE_PATH_NOT_PROCEEDS, NO_HISTORICAL_EXECUTABLE_DEPTH, BACKTEST_NOT_AVAILABLE, NO_NET_TRADING_EDGE_CLAIMABLE, RETROSPECTIVE_HOLDOUT_SPENT, UNCALIBRATED, MODEL_STALE_AFTER_<date>, CURRENT_VENDOR_LIST_ROUTE_ABSTAINS, plus family and target flags |
| `role` | REFERENCE_BASELINE (Phase 07 B0 and B2) or CANDIDATE |
| `promotion` | `level` (ABSTAIN, SHADOW, VALIDATED_EXPERIMENTAL, NO_GO), `reasons`, `shadow_reached`, `rule` |
| `registry_status` | PROMOTED_<level>, REFERENCE_ONLY_NEVER_PUBLISHED or NO_GO |
| `publishable` | true only at SHADOW or VALIDATED_EXPERIMENTAL with a CALIBRATED calibration card of the same level |
| `inference` | the identical-inference check: probe set and its sha, rows, numbers, abstentions by reason, `outputs_sha`, the recorded predictions file and its sha256, `equal_to_recorded`, `differences`; Phase 07 entries also `synthetic_probe_set`, its sha256 and `synthetic_outputs_sha` |
| `retrain_policy`, `thresholds` | the policy and state thresholds in force when the entry was made |
| `registered_as_of_utc` | fixed registration time (no clock) |

## Facts and their sources (CP16-0, PI-D-086)

A level is only as true as the facts it is computed from, so the facts are rebuilt, not trusted. `derive_facts(candidate, phase, card, tests, m_b0, m_b2, post_states, cal_card)` builds them from the committed records: the card's rows of `phase_12/validation/HOLDOUT_METRICS.csv` against B0 and B2, its selection states in `POST_OPENING_CORRECTIONS.csv`, the Phase 13 calibration card (B2 only), the card's training counts and the pre-opening checks. `verify_facts(entry, card=..., ...)` rebuilds them and refuses any difference (FACTS_MISMATCH); `verify_sources(entry, read)` checks the sha256 of the card file, the calibration card file and every evidence file the entry names. An entry with edited facts and a recomputed id passes `verify_entry` (it is self-consistent) but fails `verify_facts`; for that reason a CHAMPION pin, a rollback to a champion and `serve` run `check_facts(entry, root)` themselves (CP16-2 after the skeptic's CX-S16: a caller-supplied check could be `verify_sources` alone, which passes forged facts). `facts_from_repo(card_path, root)` reads fixed paths (`FACT_SOURCES`, the Phase 13 calibration card of the card's target) and takes a card's PRIMARY_HOLDOUT row before its SECONDARY_HOLDOUT row (`metric_rows`); a pin records `facts_check` REBUILT_FROM_COMMITTED_FILES or, for fixtures, FIXTURE_FACTS_NOT_CHECKED. Each entry also records `code`: the sha256 of features, baselines, stats, contract, labels and the family module.

## Events

Every event carries `kind`, `as_of_utc`, `seq` (its line number), `prev` (sha256 of the previous line, or 64 zeros) and `event_id` (sha256 of the canonical event without `event_id`).

| Kind | Payload |
|---|---|
| REGISTER | target, entry id, model id, level, registry status |
| ENSEMBLE_DECISION | target, decision (ENSEMBLE or NO_ENSEMBLE), configuration, reasons, evidence per configuration, evidence file |
| PIN | target, mode (CHAMPION or NO_VIABLE_CHAMPION), champion entry or null, the champion's `outputs_sha`, references `{base_rate, simple_model}`, reasons |
| ROLLBACK | a PIN payload plus `from` (the champion that failed) and `from_event` |

`resolve(target, decision_time)` returns the last PIN or ROLLBACK of the target with `as_of_utc` at or before the decision (NO_PIN before any). A CHAMPION pin needs an entry whose recomputed level is SHADOW or VALIDATED_EXPERIMENTAL, of the same target, not a fixture; references must be the target's own B0 and B2 entries.

## Using an entry

`serve(events, entries, target, decision_time, runtime=..., request=..., drift_alarms=..., inference=..., root=...)` gives what the publication path may use (repair pass 2, CP16-2). A pinned champion is used only when: `verify_entry` holds; the registry itself rebuilds its facts from the committed files under `root` and finds them equal (`check_facts`; FACTS_NOT_VERIFIED without a root, FACTS_MISMATCH on a difference; no caller-supplied verifier exists any more); the code files the entry records are unchanged under `root` (`code_changes`, P46 even without a version bump); a fixture champion appears only with `allow_fixture` (FIXTURE_IN_REAL_REGISTRY otherwise); `compatibility` reports nothing (running code's feature set, feature version, family version, registry fingerprint and labels version equal to the entry's; the request's feature set equal to the entry's); `status_at` reports no MODEL_STALE, RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF or DRIFT_ALERT; and the caller's recomputed inference rows give the pin's `inference_hash` (INFERENCE_NOT_CHECKED without rows). Otherwise `forecast_inputs` is `{card_entry: null, model_id: not_selected, level: ABSTAIN, calibration_card_sha: null}`, `rollback_required` is true for a failed champion, and `retrain` lists the requirements.

## Internal reference scores (shadow baseline mode)

`reference_record` writes `reference-score-1` records for B0 and B2 only: `kind` REFERENCE_SCORE_INTERNAL, `published` false, purpose PROSPECTIVE_COMPARISON_ONLY_NEVER_A_FORECAST, the raw number or null with its reason (checked like inference rows), the reference's states at the decision, and a `record_id`. A record has none of the forecast document keys (`is_document` false) and `validate_publication` refuses it as a document. Phase 19 writes them for prospective decisions; Phase 16 writes none (no prospective decision has features).
