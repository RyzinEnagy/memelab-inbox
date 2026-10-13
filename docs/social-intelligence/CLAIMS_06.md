# Phase 06: evidence-grounded claim extraction

Prompt 06 ("Evidence-grounded structured claim extraction"). Code: `memelab/social/extraction.py` (pipeline, prompt, validator, storage, report), `memelab/social/llm.py` (model config, providers, budget, status), migration 6 in `memelab/social/schema.py`, private model-response cache in `memelab/social/private.py`, a new rule in `content_guard.py`. CLI: `social extract`, `social claims`, `social llm-health`. Tests: `tests/test_social_extraction.py` (28). Fixtures: `tests/fixtures/social/claims/` (invented posts and an offline mock response).

Related: [HANDOFF.md](HANDOFF.md), [DECISIONS.md](DECISIONS.md) D-035 to D-040, [IDENTITY_05.md](IDENTITY_05.md), [SCHEMA_01.md](SCHEMA_01.md).

## Model status

No model was configured in the repo before this phase, and none is configured now. `python -m memelab social llm-health` reports `model_not_configured`. Every model-side proof in this phase runs on an offline mock provider (rows labelled `mode='fixture'`) or on a fake HTTP transport. No live model call was made and none is claimed.

To turn the model on, Elving would create `data/private/llm.json` from `docs/social-intelligence/llm.example.json` (provider, model id, `allow_billable: true`, prices per million tokens, caps), and set `ANTHROPIC_API_KEY` in the environment. The status then reads `configured_unverified` until a live call returns 200, then `live_ok`. A config file that holds a key is refused.

## What one run does

For one stored observation (`extract_observation`):

1. Text. The public database holds only the text hash (D-013, D-016). The text comes from the caller (the collector, at read time) or from the gitignored private store. It must hash to the observation's `content_hash`; otherwise the result is `analysis_unavailable` with `text_hash_mismatch` or `text_unavailable`.
2. Provenance context from provider ids already stored: reference type, quoted, replied-to and reposted items with their author ids, Telegram forward origin, and `store.is_independent_original` (D-029).
3. Token mentions from `identity.extract_mentions`, each with a character offset, resolved through Phase 05: a stored resolution for the item, or `resolve_post` with collector bodies, or an offline resolution that comes out `unresolved`. Nothing resolves on a symbol alone (D-031).
4. Deterministic extraction, always: one `token_reference` claim per address, link or cashtag, with its offset and the Phase 05 identity. This is the claim the lab can make with no model: the post contains this reference. It is stored as FACT about the post.
5. Model extraction, only with a configured provider and room in the budget. Otherwise the model row is `analysis_unavailable` with the reason (`model_not_configured`, `credentials_missing`, `billing_not_consented`, `budget_exhausted`, `input_too_long`, `provider_error`). No category, stance or opinion is guessed without a model.
6. Validation of the model's JSON, then storage.

## Stored shape

Public database (migration 6):

- `social_claim_extractions`: one row per observation x extractor x provider x model x prompt version x extractor version. Status `ok`, `partial`, `analysis_unavailable` or `invalid_model_output`; reason; cache key and cache hit; model calls, tokens, estimated cost, `mode` (`live`, `fixture`, `none`); the validated output as JSON (`memelab.social.claims/1`); error and flag codes; `superseded_by`.
- `social_claims` (Phase 01 table): one row per claim, a coarse projection. bullish -> CALL/LONG, bearish -> CALL/SHORT, launch -> LAUNCH, risk -> RUG_WARNING, wallet -> WALLET_CLAIM, all other categories -> OTHER. `evidence_status` is FACT for deterministic references and INFERENCE for model claims. `token_ref_id` is set only when the claim names exactly one resolved token.
- `social_claim_attributes`: the full classification of each claim (below).
- `social_claim_spans`: evidence anchors, `role`, `char_start`, `char_end` into the normalized post text (`store.normalize_text`, the text the hash is computed on) and the sha256 of the span. Never the wording.
- `social_evidence_links`: each claim -> its observation, role SOURCE.
- `social_claim_relations`: CONTRADICTS between claims in the same post with opposite stance on the same token.
- `social_api_spend`: one row per model request, connector `llm:<provider>`.

Private store (gitignored): `private_model_responses` holds the raw model reply, which can quote the post. It is the replay cache. Retention 30 days, `purge_expired()`.

Exact wording of an evidence span can be shown on screen with `social claims --show-private` when the post text was kept in the private store. It is never written to a tracked file.

## Classification rubric

Each model claim is one statement. Fields and allowed values:

| Field | Values | Meaning |
|---|---|---|
| category | bullish, bearish, launch, catalyst, wallet, volume, liquidity, risk, commentary, education, promotion | What the statement is about. Deterministic references use `token_reference`. |
| assertion_type | claimed_fact, opinion, prediction, question | claimed_fact = presented as fact, never treated as verified. opinion = a view. prediction = about the future. question = asked, not asserted. Deterministic references use `reference`. |
| stance | positive, negative, neutral, mixed | The stance after negation and sarcasm are taken into account. |
| negated | true/false | The statement is negated ("not bullish"). |
| conditional | true/false | Depends on a condition ("if it holds 0.006"). The condition must be quoted. |
| sarcasm_suspected | true/false | The literal words and the meaning may differ. |
| time_horizon | intraday, days, weeks, months, long_term, unspecified | Only when the post gives one. |
| author_position | holds, no_position, sold, not_disclosed (lab adds not_applicable) | Only what the author discloses. |
| attribution | author, quoted, reposted, unclear | Whose words these are. |
| tokens | mention ids from the lab's list, or a name written in the post | Never a contract the post does not contain. |
| narrative_tags | ai_agent, animal, political, celebrity, culture_meme, gaming, sports, defi, infrastructure, rwa, launchpad, exchange_listing, other | Fixed vocabulary; unknown tags are dropped. |
| evidence | role claim / condition / position / attribution / token, plus an exact quote | At least one `claim` quote. Quotes become offsets. |
| uncertainty | low, medium, high, plus reasons | The model's reasons: hedged_language, sarcasm, conditional, vague_reference, ambiguous_token, missing_context, other. |
| summary | own words, at most 240 characters | Dropped if it repeats 8+ consecutive words of the post (`store.check_summary`). |

Category guide, in short: bullish or bearish for a view on price or prospects; launch for a new token, pool or listing going live; catalyst for an event said to move the token (partnership, listing, product); wallet for statements about wallets, whales, insiders, "smart money" or developer holdings; volume and liquidity for statements about those numbers; risk for warnings (rug, honeypot, unlock, dev selling); commentary for general talk; education for explanations; promotion for shilling, giveaways, paid or affiliate pushes.

### Rules applied after the model

The lab enforces these whatever the model returned:

- The output must be one JSON object with `schema`, `claims`, `injection_attempt_seen` and nothing else; otherwise `invalid_model_output` and no claims are kept.
- A claim with any key outside the rubric, a wrong type or an unknown enum value is dropped (`partial`).
- Every quote must be an exact substring of the normalized post. A quote not found is dropped; a claim with no `claim` quote left is dropped (`unsupported_claim_dropped`).
- Tokens: an unknown mention id is dropped; a contract the post does not contain is removed (`fabricated_contract_removed`, uncertainty high); a name not written in the post is dropped; a name that is written in the post is kept as an unresolved name-only reference.
- A conditional claim without a quoted condition: uncertainty high (`condition_not_anchored`).
- Sarcasm: uncertainty at least medium.
- negated + bullish + positive stance is inconsistent: uncertainty high.
- wallet category: uncertainty at least medium, verification `unverified_text_claim`, evidence INFERENCE. A post saying wallets are buying is never written to `social_wallet_attributions`.
- Any token in the claim not `resolved`: uncertainty at least medium (`ambiguous_token`).
- Provider context wins on attribution: an item that is a repost or forward gets `reposted`, `author_position` `not_applicable` and the origin item id; `quoted` gets the quoted item and author id from `social_item_refs`; a model `reposted` reading on an item the provider calls original becomes `unclear`.
- Opposite stances on the same token in one post: both claims uncertainty high and a CONTRADICTS relation.
- Text that matches the injection rules sets a flag on the extraction; every claim from that post is at least medium (`injection_suspected`) and the report warns.
- Model claims are always `unverified_text_claim`, INFERENCE. They record what was said, never that it is true.

## Prompt injection

The post goes to the model as data between two marker lines that carry a nonce derived from the post's own hash, so the post cannot contain its closing marker. The system prompt says the post is untrusted and not to follow anything in it. The extractor has no tools. The only thing a model can do with a post's instructions is change field values, and the validator throws out anything outside the schema. Deterministic rules flag text that looks like instructions to an AI (`INJECTION_RX`). The test post containing "ignore all previous instructions", a fake end marker, "system:" and a JSON payload ends with no claims from the obeying answer, and a top-level field outside the schema rejects the whole answer.

## Budget, cache, dedupe and replay

- Budget (`llm.Budget`): calls per run, calls per month and dollars per month (live rows in `social_api_spend`), max input characters, max output tokens. A live call needs prices in the config. A refused call is `analysis_unavailable` with the reason and costs nothing.
- One retry, only when the reply is not JSON at all, and only if the budget allows it.
- Dedupe: the same observation with the same versions adds nothing (extraction key).
- Cache: the cache key is the text hash + provenance context + provider + model + prompt version + output schema + mention identities. A second observation of the same text reuses the stored validated output with no model call.
- Replay (`extraction.replay`): when the extractor version changes, the raw reply from the private store is re-validated without a call; when the prompt version changes, a new call is made. Text comes from the caller or the private store; without it the result is `text_unavailable`. A successful new extraction marks older ones `superseded_by`; reports show current extractions only.

## Sample output

From the CLI demo on invented fixture posts (temp DB, `--now 1791676800`). Without a model:

```
Observation 1, deterministic rules: done
Observation 1, model analysis (no provider): not available (model_not_configured)
Claim 1 from post x:1900000000000000001
  Source: https://x.com/example_poster/status/1900000000000000001; posted 2026-10-10 02:30 UTC; seen 2026-10-10 02:31 UTC (fixture); observation 1
  What it is: a token reference, a reference found in the text; stance neutral; time frame: no time frame given
  In the lab's words: The post contains a link reference (solana 8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ).
  Token: link:https://pump.fun/coin/8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ -> solana 8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ (resolved, resolution 1)
  Author position: the author does not say whether they hold it
  Whose words: the poster's own words
  Uncertainty: low
  Evidence (token): characters 62-106 of the post text (sha256 e7df620ffcc3)
  Evidence bucket: FACT (the post contains this); verification: present in text
  Extracted by: deterministic rules (claims-extract-v1), no model used
```

With the mock provider (the model claim only):

```
Claim 5 from post x:1900000000000000002
  Source: https://x.com/example_poster/status/1900000000000000002; posted 2026-10-10 03:00 UTC; seen 2026-10-10 03:01 UTC (fixture); observation 2
  What it is: a bullish view, a prediction; stance positive; time frame: weeks
  In the lab's words: Author says they increased their holding and expects the price to roughly double within the week.
  Token: link:https://pump.fun/coin/8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ -> solana 8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ (resolved, resolution 3)
  Author position: the author says they hold it
  Whose words: the poster's own words
  Uncertainty: medium (hedged_language)
  Narrative tags: animal
  Evidence (claim): characters 49-77 of the post text (sha256 1539e75adb4a)
  Evidence (position): characters 23-47 of the post text (sha256 4ac99823442f)
  Evidence bucket: INFERENCE (what the post says, not verified); verification: unverified text claim
  Extracted by: model mock/mock-claims-1, prompt claims-prompt-v1, claims-extract-v1 (fixture run, not a live model)
```

## Known limits

- Ingestion still does not call extraction: inbound items carry a hash, not text (D-016). A collector has to run extraction while it holds the text, or keep the text in the private store with a reason. Wiring is left to the collector phases.
- A link mention is anchored at the address inside the link, not the whole URL.
- Ticker mentions are found by the `$` cashtag only (Phase 05 rule); a bare word like "PEPE2" in the text is not a mention unless the model names it, and then it is a name-only, unresolved reference.
- The rubric and injection rules are lab conventions. Model quality on real posts is untested because no model is configured.
