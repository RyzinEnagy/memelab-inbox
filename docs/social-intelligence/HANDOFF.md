# Social & Trader Intelligence: handoff

Rewritten at the end of every phase. Read this first. Contract: [EXECUTION.md](EXECUTION.md). Plan: [ROADMAP.md](ROADMAP.md). Choices: [DECISIONS.md](DECISIONS.md). Baseline: [AUDIT_00.md](AUDIT_00.md). Schema and connectors: [SCHEMA_01.md](SCHEMA_01.md), [CONNECTORS_02.md](CONNECTORS_02.md), [X_API_03.md](X_API_03.md), [TELEGRAM_04.md](TELEGRAM_04.md), [IDENTITY_05.md](IDENTITY_05.md), [CLAIMS_06.md](CLAIMS_06.md), [NARRATIVES_07.md](NARRATIVES_07.md), [REGISTRY_08.md](REGISTRY_08.md), [WALLETS_09.md](WALLETS_09.md), [PERFORMANCE_10.md](PERFORMANCE_10.md), [ALPHA_11.md](ALPHA_11.md), [CHRONOLOGY_12.md](CHRONOLOGY_12.md), [INTEGRATION_13.md](INTEGRATION_13.md), [REPORTS_14.md](REPORTS_14.md), [ALERTS_15.md](ALERTS_15.md), [OUTCOMES_16.md](OUTCOMES_16.md), [REPLAY_17.md](REPLAY_17.md). Source status: [SOURCE_COVERAGE.md](SOURCE_COVERAGE.md).

## Position

- Current phase completed: 17 (Prompt 17: historical replay, baselines and statistical honesty), 2026-10-12. Prompt 17 took the Phase 17 slot; the old proposed Phase 17 (m19 attention and launch social) is now carry-over C-17 (D-112).
- Model status: unchanged, none configured (D-036). The replay never calls a model.
- Data status: real history was read, read-only: the tracked database (no social tables; 33 legacy market snapshots) and a scratch copy of the collector files on `origin/main:inbox/` (40 files). Nothing was fetched and nothing from `main` was committed.
- Honest result: all four strategies are INSUFFICIENT_DATA on real history (0 posts, 0 wallet events; 410 trending entries and 16,847 candles from about one day, 2026-10-07T17:14Z to 2026-10-08T14:01Z; no trending entry has 24 h of later prices; no delisted tokens tracked). See REPLAY_17.md "Result first".
- Next phase: 18 as proposed in ROADMAP.md, or a carry-over, unless Elving supplies Prompt 18. Not started.
- Active branch: `feature/social-intelligence`.
- Phase 17 started from `b605f8b` ("social-intel phase 16: record commit and push route in handoff"), the remote branch head. No drift. Baseline `python -m pytest tests -q --deselect tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`: `621 passed, 1 deselected`, matching the Phase 16 handoff.
- No migration. Public schema stays at 12. The replay writes nothing unless `--out` is given.

## What Phase 17 added

- `memelab/social/replay_core.py` (pure): input `memelab.social.replay.input/1`, policy `memelab.social.replay.policy/1` (trading keys refused), `prepare` (availability per record, exclusions counted by reason), `CutoffView` plus `Audit` (LeakageError), four strategies and `generate`, `outcome` (Phase 16 engine), `controls_for`, `split_bounds`, `LabelGate`, `samples`, `tune`, `summarize`, `verdict`, `survivorship`, `run`, `truncate`, `leakage_check`, `render`.
- `memelab/social/replay_synth.py`: seeded synthetic world (`DEFAULT_SPEC`).
- `memelab/social/replay_sources.py`: `from_db` (legacy snapshots; social claims, reposts, wallet events with linkage, alpha candles, market facts when the social schema exists), `from_inbox` (GeckoTerminal OHLCV and trending lists, DexScreener boosts; chain only from evidence), `merge`, `inventory`.
- `memelab/social/replay_cli.py`: `social replay inventory|run|demo|export`, registered in `memelab/social/cli.py`.
- Tests: `tests/test_social_replay.py` (22). Fixture: `tests/fixtures/social/replay/` (`synthetic_spec.json`, `sample_report.md` checked byte for byte).
- Docs: `REPLAY_17.md`, DECISIONS D-112 to D-118, ROADMAP (17 DONE, C-17 added, 19 depends on C-17), SOURCE_COVERAGE row.

## Gate, item by item

- Trustworthy replay tooling: cutoff clock with audited accessors (`test_harness_that_reads_future_evidence_fails`: a leaky view raises LeakageError; with the audit removed, truncation invariance reports differences). Mutation check: dropping the cutoff in `_raw_posts_on` made `tests/test_social_replay.py` give `9 failed, 13 passed`; restored, `22 passed`. Train-only tuning behind `LabelGate` (`test_label_gate_refuses_held_out_labels_before_they_are_allowed`); rewriting all prices after the train boundary and adding backdated posts leaves tuning and the frozen hash unchanged (`test_future_information_injected_into_training_window_does_not_change_tuning`).
- Synthetic fixture replay: `python -m memelab social replay demo` exit 0, about 35 s, prints `sample_report.md`, "No leakage detected: yes". Verdicts there: INDIVIDUAL, CONVERGENCE, SOCIAL_WALLET INSUFFICIENT_SAMPLE; TRENDING CANNOT_VALIDATE_YET. The harness can also say yes (`test_harness_can_report_an_edge_when_one_exists`).
- Honest real result: `python -m memelab social replay run --db data/memelab.sqlite --inbox <scratch copy of main:inbox>` exit 0, INSUFFICIENT_DATA for all four, leakage check identical at both boundaries and for tuning. `social replay run --db data/memelab.sqlite` alone: exit 0, INSUFFICIENT_DATA (CLI test).
- Prompt test list: each case is a named test, see REPLAY_17.md "Test list".
- Full pytest: below.

## Tests

- Command: `python -m pytest tests -q` (needs `pip install pytest numpy`).
- Outcome after the last code change: exit 1, `1 failed, 643 passed` in 137 s. The only failure is the known clock-dependent `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` (C-1, untouched).
- `python -m pytest tests/test_social_replay.py -q` -> `22 passed` (about 55 s; the sample-report test runs the full demo).
- `python -m memelab social guard` exit 0 (0 violations, 100 JSON files scanned, new files staged).
- The EVM test still writes `data/reports/<stamp>_BRETT_*.md`; deleted by hand after each run (C-1). `git status` clean after that.

## Things the next phase should know

- To get a real answer the replay needs: posts and wallet events in a migrated database (C-6, C-7, Phase 09 fetches), the Phase 16 ledger recording signals at emission, and price history for signalled and control tokens over weeks, delisted tokens included (declare `universe.includes_delisted` only when true).
- `social replay export --db ... --inbox ... --out FILE` writes the assembled input; `run --input FILE` replays it. Policies go in with `--policy FILE` (unknown or trading keys refused).
- The replay's candle availability defaults to the collector's capture time; `--candle-availability provider` uses close + an assumed 300 s GeckoTerminal lag (HEURISTIC).

## Helius key

The key is not in the repo and must never be committed. Code reads it through `memelab/secrets.py`, in this order:

1. The `HELIUS_API_KEY` environment variable. Use this for a scheduled run, CI or a cloud session (set it as a secret there).
2. `helius_api_key` in `data/config.json`. That file is gitignored. On a machine, create it with `python -m memelab.secrets set` (prompts without echo).

Check with `python -m memelab.secrets status` (prints "set" or "missing" and the source, never the value). A new session that needs the key should ask Elving to supply it (it is not stored in memory or project docs). The key was pasted into a chat once; rotate it if that chat is shared.

## Blockers and open decisions

- Push: the session's own `git push` is refused by the git proxy (repo not in the session's authorized set). Working route: Elving's GitHub connection in Composio, Git Data API (blobs, trees, commits, fast-forward of the feature branch ref, no force, D-001).
- No live posts, wallet fetches or price provider in session; the tracked database has no social schema. Real replay results stay INSUFFICIENT_DATA until that changes.
- No alert transport configured and no consent recorded; enabling delivery or a scheduled job is Elving's call.
- C-1 (the clock-dependent catalyst test) keeps the full suite from being fully green.
- D-025, D-028, D-023 and D-036 remain open.
- Phase prompts 18 onward not supplied; ROADMAP.md entries are proposals.

## Exact next command

```
git clone https://github.com/RyzinEnagy/memelab-inbox.git && cd memelab-inbox && git checkout feature/social-intelligence && pip install pytest numpy && python -m pytest tests -q
```

Expect `1 failed, 643 passed` and `python -m memelab social guard` exit 0.

## Commit and push

Phase 17 code commit on `feature/social-intelligence`: `34819ab08aaabdafbfe7540d905757e779cc36cd` locally (tree `50c4c67a9b0dcb64540ac131d88accd7483a1b98`, parent `b605f8b`). This handoff is the commit on top of it. The remote commit hashes differ from the local ones (author metadata) when pushed through the Git Data API; the trees are checked equal.

Phase 18 is not started.
