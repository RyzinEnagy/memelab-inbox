# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Baseline: [AUDIT_00.md](AUDIT_00.md). Schema and connectors: [SCHEMA_01.md](SCHEMA_01.md), [CONNECTORS_02.md](CONNECTORS_02.md), [X_API_03.md](X_API_03.md), [TELEGRAM_04.md](TELEGRAM_04.md), [IDENTITY_05.md](IDENTITY_05.md), [CLAIMS_06.md](CLAIMS_06.md), [NARRATIVES_07.md](NARRATIVES_07.md), [REGISTRY_08.md](REGISTRY_08.md), [WALLETS_09.md](WALLETS_09.md), [PERFORMANCE_10.md](PERFORMANCE_10.md), [ALPHA_11.md](ALPHA_11.md), [CHRONOLOGY_12.md](CHRONOLOGY_12.md), [INTEGRATION_13.md](INTEGRATION_13.md), [REPORTS_14.md](REPORTS_14.md), [ALERTS_15.md](ALERTS_15.md), [OUTCOMES_16.md](OUTCOMES_16.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).

## Position

- Current phase completed: 16 (Prompt 16: immutable signal ledger and forward evaluation), 2026-10-12. Prompt 16 took the Phase 16 slot; the old proposed Phase 16 (call outcome tracking and trader scoring) is now carry-over C-16 (D-105).
- Model status: unchanged, none configured (D-036). The ledger never calls a model.
- Data status: no live signal, post, wallet fetch or price source was used. The tracked database has no social tables, so `social evaluate observe --from-db data/memelab.sqlite` appends 0 observations and `social evaluate run` on an empty ledger prints "no signals recorded. Nothing to evaluate." Every signal and price in this phase is an invented, watermarked fixture.
- Nothing records signals automatically yet: the feed, research and alert commands do not call the ledger. `social evaluate record` takes their JSON output.
- Next phase: 17 as proposed in ROADMAP.md, or a carry-over, unless Elving supplies Prompt 17. Not started.
- Active branch: `feature/social-intelligence`.
- Phase 16 started from `283fe89` ("social-intel phase 15: record commit and push route in handoff"), the commit on the remote branch. No drift. Baseline `python -m pytest tests -q --deselect tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`: `593 passed, 1 deselected`, matching the Phase 15 handoff (`1 failed, 593 passed` with the C-1 test included).
- No migration. Public schema stays at 12. The ledger is a separate private SQLite file.

## What Phase 16 added

- `memelab/social/outcomes_core.py` (pure): policy `memelab.social.outcomes.policy/1` (trading keys refused, `trade_execution_impact: none`), signal context `memelab.social.signal/1` built by `make_signal()` (market facts after generation dropped and counted, LATE_CAPTURE and EVENT_AFTER_GENERATION flags, missing fields with reasons), adapters `signals_from_feed()` and `signals_from_research()` (rejected candidates kept), observation validation (future-dated observations and unfinished candles refused), revision-aware `visible()`, `evaluate()` for one signal and horizon, `coverage()` and plain-text rendering.
- `memelab/social/outcomes_ledger.py`: private journal `data/private/signal_ledger.sqlite` (`MEMELAB_SIGNAL_LEDGER`; tracked database refused), SIGNAL / OBSERVATION / ANNOTATION / OUTCOME entries, UPDATE and DELETE refused by triggers, body and chain hashes, `record_signals`, `add_observations`, `annotate`, `evaluate_all` (append only when new or changed, resumable, clock may not go backwards), read-only `compute` replay, `report`, `verify`.
- `memelab/social/outcomes_cli.py`: `social evaluate record|observe|run|annotate|show|report|verify|demo`, registered in `memelab/social/cli.py`. `observe --from-db` reads `social_market_facts`.
- Tests: `tests/test_social_outcomes.py` (28). Fixture: `tests/fixtures/social/outcomes/` (`make_outcomes.py` builds `outcomes_fixture.json`; `sample_run.md` is the demo output, checked byte for byte).
- Docs: `OUTCOMES_16.md`, DECISIONS D-105 to D-111, ROADMAP (16 DONE, C-16 added), SOURCE_COVERAGE row.

## Gate, item by item

- Auditable chronological ledger: one journal in recorded order, hash chain and body hashes recomputed by `verify` (`test_ledger_is_append_only_and_verify_detects_tampering`: UPDATE refused; with the trigger dropped and a row edited, verify reports the hash problems). Outcome history per signal with `supersedes_seq` and `revision_reason` (`social evaluate show`).
- Deterministic resumption: a crash on the 7th outcome leaves 6 entries; a rerun ends byte for byte equal to an uninterrupted ledger (`test_deterministic_resumption_after_a_crash`). Repeating an evaluation appends nothing (`test_duplicate_evaluation_appends_nothing`). Replay at an earlier time gives the earlier numbers without writing.
- Transparent missing outcomes: every outcome has a status and reason codes; the coverage report counts each status per horizon, lists exclusion reasons and splits by disposition (`sample_run.md`, "Outcome coverage").
- Zero original-context mutation: `python -m memelab social evaluate demo --fixture tests/fixtures/social/outcomes/outcomes_fixture.json` (exit 0) prints the GOODCAT context before and after two evaluations with the same body sha256 (`0777c37f...`), "Original context unchanged, byte for byte, for all 5 signals: yes.", and an UPDATE refused by the ledger. Evaluation 1 (2026-10-13T19:00Z): 25 outcomes appended. Evaluation 2 (2026-10-14T14:00Z): 6 appended (MATURED 4, INPUTS_REVISED 2), 19 unchanged. Repeat: 0 appended.
- Prompt test list, each a named test: see OUTCOMES_16.md "Test list".
- Baseline suite passes apart from the known C-1 test (below).

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest numpy`).
- Outcome after the last code change: exit 1, `1 failed, 621 passed`. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1, untouched).
- `python -m pytest tests/test_social_outcomes.py -q` -> `28 passed`.
- `python -m memelab social guard` exit 0 (0 violations, 341 files scanned).
- Commands run against the tracked database with a scratch ledger: `social evaluate observe --from-db data/memelab.sqlite` exit 0 (0 appended), `social evaluate run --as-of 2026-10-12T20:00:00+00:00 --now 2026-10-12T20:00:00+00:00` exit 0 ("no signals recorded"), `social evaluate report` exit 0, `social evaluate verify` exit 0 (0 entries, ok).
- The EVM test still writes `data/reports/<stamp>_BRETT_*.md`; deleted by hand after each run (C-1). `git status` clean after that.

## Things the next phase should know

- To use the ledger for real: record each emitted signal at emission time (`social evaluate record --feed-json` on the feed JSON the same run produced, or call `outcomes_ledger.record_signals` from the run), append observations as prices arrive (`observe --from-db` or `--prices`), then `social evaluate run` on a schedule. Recording late is flagged LATE_CAPTURE. Wiring this into scheduled runs is Phase 19/20 work and Elving's call.
- Outcomes use the assumptions stored in each signal (horizons, lag, size, fees), not the current policy, so a policy change never rewrites old evaluations.
- Trader or source scoring on ledger outcomes is C-16 and needs C-15 (call capture) so calls become signals.

## Helius key

The key is not in the repo and must never be committed. Code reads it through `memelab/secrets.py`, in this order:

1. The `HELIUS_API_KEY` environment variable. Use this for a scheduled run, CI or a cloud session (set it as a secret there).
2. `helius_api_key` in `data/config.json`. That file is gitignored. On a machine, create it with `python -m memelab.secrets set` (prompts without echo).

Check with `python -m memelab.secrets status` (prints "set" or "missing" and the source, never the value). A new session that needs the key should ask Elving to supply it (it is not stored in memory or project docs). The key was pasted into a chat once; rotate it if that chat is shared.

## Blockers and open decisions

- Push: the session's own `git push` is refused by the git proxy (repo not in the session's authorized set). Working route: Elving's GitHub connection in Composio, Git Data API (blobs, trees, commits, fast-forward of the feature branch ref, no force, D-001).
- No live posts, wallet fetches or price provider in session; the tracked database has no social schema.
- No alert transport configured and no consent recorded; enabling delivery or a scheduled job is Elving's call.
- C-1 (the clock-dependent catalyst test) keeps the full suite from being fully green.
- D-025, D-028, D-023 and D-036 remain open.
- Phase prompts 17 onward not supplied; ROADMAP.md entries are proposals.

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q
```

Expect `1 failed, 621 passed` and `python -m memelab social guard` exit 0.

## Commit and push

Phase 16 code commit on `feature/social-intelligence`: `8c31e53497052065e898749d712abb4107aebabe` (tree 1ed54ce989626496bd2074877c61f12f1b230dda, parent 283fe897b31cb0d4e766148b93eeba82063d4206). This handoff is the commit on top of it.

The push went through Composio and the GitHub Git Data API: the diff against 283fe89 went over as an xz patch in four base64 chunks (each chunk and the reassembled patch checked by sha256), was applied to the four base files fetched at 283fe89 (their blob shas checked first), all 12 blob shas were checked against the local files, the tree sha matched the local tree before the commit was created, and the branch ref was moved forward once, without force. `main` was not touched. The local commit was then reset to the remote one (same tree, different author metadata).

Phase 17 is not started.
