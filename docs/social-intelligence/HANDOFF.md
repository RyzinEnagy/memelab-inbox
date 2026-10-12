# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Baseline: [AUDIT_00.md](AUDIT_00.md). Schema and connectors: [SCHEMA_01.md](SCHEMA_01.md), [CONNECTORS_02.md](CONNECTORS_02.md), [X_API_03.md](X_API_03.md), [TELEGRAM_04.md](TELEGRAM_04.md), [IDENTITY_05.md](IDENTITY_05.md), [CLAIMS_06.md](CLAIMS_06.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).

## Position

- Current phase completed: 06 (Prompt 06: evidence-grounded structured claim extraction), 2026-10-12. Prompt 06 took the Phase 06 slot; the old proposed Phase 06 (X via signed-in Chrome) is now carry-over C-6 (D-035).
- Model status: none configured. `python -m memelab social llm-health` -> `model_not_configured` (D-036). Every model-side proof ran on the offline mock provider (`mode='fixture'`) or a fake HTTP transport. No live model call, no live provider data.
- Next phase: 07 as proposed in ROADMAP.md (needs D-028), or C-5 / C-6, unless Elving supplies Prompt 07.
- Active branch: `feature/social-intelligence`.
- Phase 06 started from `76c105b` ("social-intel phase 05: move uploaded files to their real paths"), the commit the Phase 05 fix left on the remote branch. No drift. Tree clean; baseline `python -m pytest tests -q` gave `1 failed, 212 passed`, as recorded in the Phase 05 handoff.
- Local commits: `6dcf3b3` (code, tests, fixtures, docs) and the handoff commit on top of it. Not pushed; see Blockers.

## What Phase 06 added

- `memelab/social/extraction.py`: `extract_observation()` (text checked against the observation hash, provenance context, Phase 05 mentions with offsets, deterministic token-reference claims, model claims or `analysis_unavailable`), `validate_model_output()`, `build_user_prompt()` and `SYSTEM_PROMPT`, `injection_flags()`, `replay()`, `claims_for()`, `extraction_status()`, `report()` (plain English).
- `memelab/social/llm.py`: `load_config()` (gitignored `data/private/llm.json`, key from `ANTHROPIC_API_KEY` only), `MockProvider`, `AnthropicProvider` (Messages API, injectable transport, not exercised live), `Budget` (run, monthly-call and monthly-dollar caps, spend in `social_api_spend`), `provider_from_config()`, `llm_status()`.
- `memelab/social/schema.py`: migration 6 (`social_claim_extractions`, `social_claim_attributes`, `social_claim_spans`).
- `memelab/social/private.py`: `private_model_responses` table, `put_model_response()`, `get_model_response()`, `get_text()`; `purge_expired()` also clears model responses.
- `memelab/social/content_guard.py`: fails if `social_claim_extractions.output_json` holds a `quote` or `exact_text` key.
- `memelab/social/cli.py`: `social extract --post|--observation [--bodies] [--mock]`, `social claims --item|--claim [--json] [--show-private]`, `social llm-health`.
- Tests: `tests/test_social_extraction.py` (28). `tests/test_social_identity.py::test_migration_5_rolls_back_cleanly` changed to stop assuming 5 is the newest migration.
- Fixtures: `tests/fixtures/social/claims/demo_post_nollm.json`, `demo_post_model.json`, `demo_mock.json` (invented posts; mock reply keyed by the post's content hash).
- Docs: `CLAIMS_06.md` (pipeline, rubric, rules, sample output), `llm.example.json`, DECISIONS D-035 to D-040, ROADMAP (row 06 DONE, C-6 added, 07 NEXT, note on 15), SCHEMA_01 (later migrations line).

## Gate, item by item

- Observable, schema-validated pipeline from ingested item to cited claim: `extract_observation` -> `social_claim_extractions` (status, versions, cache, errors) -> `social_claims` + `social_claim_attributes` + `social_claim_spans` (offsets, span sha256) + `social_evidence_links` (claim -> observation, SOURCE). Tests `test_without_a_model_a_cited_reference_claim_is_stored_and_reported`, `test_mock_provider_structured_analysis_end_to_end`.
- Real/model-not-configured status truthful: `test_provider_configuration_is_truthful` (model_not_configured, config_invalid, credentials_missing, billing_not_consented, configured_unverified); fixture calls never count as live (`test_mock_provider_structured_analysis_end_to_end`); `live_calls_ok` counts only live 200 rows (`test_anthropic_request_shape_and_errors_offline`). CLI `social llm-health` -> `model_not_configured`.
- Prompt test list:
  - sarcasm: `test_sarcasm_raises_uncertainty`
  - conditional claims: `test_conditional_claims_need_an_anchored_condition`
  - negations: `test_negation`
  - repost attribution: `test_repost_attribution_comes_from_provider_ids_not_the_model`, `test_quote_attribution_points_at_the_quoted_item`
  - contradictory statements: `test_contradictory_statements_are_linked_and_uncertain`
  - two similarly named tokens: `test_two_similarly_named_tokens_keep_separate_mentions_and_never_resolve_on_symbol`
  - unsupported token: `test_unsupported_token_and_name_only_reference_stay_unresolved`
  - fabricated contract: `test_fabricated_contract_is_removed`
  - prompt injection inside a post: `test_prompt_injection_inside_a_post_is_data`
  - malformed model output: `test_malformed_model_output` (4 cases), `test_partially_valid_output_keeps_good_claims`
  - dedupe and reprocess: `test_dedupe_and_cache`, `test_reprocess_after_extractor_or_prompt_change`
  - also: `test_smart_money_text_never_becomes_wallet_evidence`, `test_summary_copying_the_post_is_dropped`, `test_text_must_match_the_observation_and_can_come_from_the_private_store`, `test_budget_and_input_limits`, `test_no_post_text_reaches_the_public_database_and_guard_passes`, `test_migration_6_rolls_back_cleanly`, `test_cli_demo_without_model_and_with_mock_provider`
- Demo (temp DB, temp private store, no LLM config, `--now 1791676800`, every command exit 0; also the CLI test):
  - `social extract --post tests/fixtures/social/claims/demo_post_nollm.json --bodies tests/fixtures/social/resolve/fx_providers.json`: deterministic `ok`, 2 claims (link and `$LABDOG`, both resolved to solana `8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ`, FACT, offsets 62-106 and 32-39); model `analysis_unavailable`, reason `model_not_configured`.
  - `social extract --post .../demo_post_model.json --bodies ... --mock tests/fixtures/social/claims/demo_mock.json`: model `ok`, 1 call, claim 5: bullish prediction, weeks, author holds, uncertainty medium (hedged_language), evidence claim 49-77 and position 23-47, INFERENCE, "fixture run, not a live model".
  - `social claims --claim 1`, `social claims --item x:1900000000000000002`: plain-English reports (copied into CLAIMS_06.md, "Sample output").
  - `social llm-health`: `model_not_configured`, `live_calls_ok` 0, `fixture_calls` 1.
- Migration on a copy of the tracked DB: `schema.migrate()` applied `[1, 2, 3, 4, 5, 6]`; `content_guard.check_sqlite` on the copy: `[]`. The tracked file is unchanged.

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest numpy`).
- Outcome after the last code change: exit 1, `1 failed, 240 passed in 22.10s`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1, untouched).
- `python -m pytest tests/test_social_extraction.py -q` -> `28 passed`.
- `python -m memelab social guard` exit 0 (249 files, 73 JSON, 0 violations, Phase 06 files staged).
- Side effect still present: the EVM test writes `data/reports/<stamp>_BRETT_0x532f.md`; deleted by hand after each run (C-1). `git status` clean after that.

## Files changed in Phase 06

`docs/social-intelligence/CLAIMS_06.md`, `DECISIONS.md`, `HANDOFF.md`, `ROADMAP.md`, `SCHEMA_01.md`, `llm.example.json`; `memelab/social/cli.py`, `content_guard.py`, `extraction.py`, `llm.py`, `private.py`, `schema.py`; `tests/test_social_extraction.py`, `tests/test_social_identity.py`; `tests/fixtures/social/claims/demo_mock.json`, `demo_post_model.json`, `demo_post_nollm.json`.

## Things the next phase should know

- Ingestion still does not call extraction or the resolver. Inbound items carry a hash, not text (D-016), so a collector has to run `extraction.extract_observation()` while it holds the text, or keep the text in the private store with a reason (`record_observation(keep_exact_reason=...)`).
- Count claims only from current extractions (`superseded_by IS NULL`, as `claims_for` does), only `resolved` tokens (D-029), and call `store.is_independent_original()`.
- `social_claims.claim_type` is a coarse projection; read `social_claim_attributes` for the classification.
- Model claims are always INFERENCE and `unverified_text_claim`; a wallet claim never creates a wallet attribution.
- Turning on a live model: `data/private/llm.json` from the example, `ANTHROPIC_API_KEY`, prices and caps, `allow_billable: true`. Elving's cost decision (D-036).

## Blockers and open decisions

- Push: not done by the session. Its own `git push` got 403 (repo not in its sources), and the Composio GitHub route would mean re-sending about 280 KB of file content through tool arguments, which risks corrupting files. Phase 06 was delivered to Elving as `phase06_upload.zip` (the 17 changed files at their real repo paths, no wrapper folder), `phase06.patch` (`git format-patch 76c105b..HEAD`) and `phase06.bundle`. Upload target: `feature/social-intelligence` only, never `main` (D-001). If the upload lands with wrong paths, the next session fixes it as in Phase 05. After upload, the remote commit hashes will differ from the local ones; the remote branch is the record (D-008).
- D-025 (X browser automation), D-028 (Telegram bot terms), the X budget (D-023) and now the model choice and budget (D-036) are open.
- Phase prompts 07 onward not supplied; ROADMAP.md entries are proposals.

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q
```

Expect `1 failed, 240 passed` and `python -m memelab social guard` exit 0. Then start the next phase.
