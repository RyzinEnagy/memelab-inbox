# Phase 00 evidence: authoritative repository baseline

| Item | Value |
|---|---|
| Phase | 00, "Audit actual Memecoin Lab and establish an executable baseline" |
| Status | NEEDS_REVIEW (see "Status reasoning") |
| Branch | `feature/predictive-intelligence` |
| HEAD before | `f99c6c7` (`git status` clean) |
| HEAD after | the Phase 00 commit; hash recorded in docs/predictive-intelligence/HANDOFF.md |
| Work window (UTC) | from 2026-10-24T00:26:06Z (first recorded `date -u`) to the commit time recorded in HANDOFF.md |
| Package | Memecoin Predictive Intelligence Engine 1.0; `sha256sum -c SHA256SUMS.txt` 41 of 41 OK, exit 0 |
| Production code changed | none (only files under `docs/predictive-intelligence/` and `audits/predictive-intelligence/`) |
| Spend | 0 credits (COST_LEDGER.md) |

## Acceptance checklist (written before any repo change)

A1 package integrity; A2 checkout identity; A3 branch map; A4 authoritative code line with evidence; A5 full suite with exact counts, exit, duration, interpreter, dependency state; A6 stray files removed and recorded; A7 CLI smoke on a temp DB in a separate clone; A8 feature trace with anchors, diagram and a missing or untested path; A9 data coverage (tables, counts, time ranges, cadence, clocks, per-mint history, dead tokens, tracked or ignored); A10 public API reachability and rate limits from provider docs (at most four single calls); A11 tooling (Firecrawl, Crawl4AI, Maxun, MiroFish) with the Windows token file recorded BLOCKED; A12 P34; A13 P01; A14 P41; A15 prediction inventory with anchors; A16 independent skeptic; A17 namespaced records only; A18 no production change; A19 RESULTS.json valid with matching hashes; A20 suite rerun after the records gives the same counts; A21 zero spend unless a billable call is made.

## Results against the checklist

| Item | Result | Proof |
|---|---|---|
| A1 | met | `sha256sum -c SHA256SUMS.txt` exit 0, 41 OK |
| A2 | met | `git status` clean, HEAD `f99c6c7`, remote RyzinEnagy/memelab-inbox |
| A3 | met | baseline/REPO_MAP.md "Branches" (tips, merge bases, counts, diff stats) |
| A4 | met | REPO_MAP.md "Authoritative code line"; `git merge-base --is-ancestor` f084b60 and 3f27fc7 exit 0; `git diff --stat f084b60 origin/main -- memelab tests tools bridge skills docs` empty |
| A5 | met | `python -m pytest tests -q -rs -p no:cacheprovider`: exit 1, `1 failed, 785 passed in 133.57s`, 786 collected, 0 skipped; only the known clock failure; Python 3.13.17; no lock file; baseline/PIP_FREEZE.txt |
| A6 | met | `data/reports/20261024_0027_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, empty `-wal` removed; tracked DB sha256 unchanged |
| A7 | met | COMMIT_AND_TEST_LOG.md "CLI smoke": help, init, analyze, scout exit 0; `catalyst fc-health` exit 1 config_missing; clone status empty |
| A8 | met | baseline/FEATURE_TRACE.md (mermaid diagram, anchors, 5 gaps) and probes/lineage_reproduction_probe.py exit 0 |
| A9 | met | baseline/DATA_COVERAGE.md; probes/state_history_probe.py exit 0 |
| A10 | met | DATA_COVERAGE.md "Free public APIs": GeckoTerminal 2 calls HTTP 200, DEX Screener 1 call HTTP 200, GitHub REST 1 call HTTP 403; limits quoted from provider specs with sha256 |
| A11 | met with a recorded block | REPO_MAP.md "Research tooling found"; Windows files BLOCKED for verification |
| A12 | met | P34 below |
| A13 | met | P01 below; probes/p01_ticker_identity_probe.py exit 0 |
| A14 | met | P41 below; probes/p41_untrusted_page_probe.py exit 0 |
| A15 | met | baseline/EXISTING_PREDICTION_INVENTORY.md |
| A16 | not met | no independent fresh-context skeptic could be started (PI-D-009); own adversarial pass below is labelled not independent; SKEPTIC_PACKET.md ready for the orchestrator |
| A17, A18 | met | `git diff --name-only f99c6c7..HEAD` lists only docs/predictive-intelligence/ and audits/predictive-intelligence/ (checked after commit, HANDOFF.md) |
| A19 | met | PHASE_00_RESULTS.json parsed with `python -m json.tool`; hashes recomputed with `sha256sum` |
| A20 | met | `python -m pytest tests -q` after all records were written: exit 1, `1 failed, 785 passed in 132.19s`, same counts as the baseline |
| A21 | met | no billable call; COST_LEDGER.md total 0 |

## Commands with exit codes (verbatim results)

| Command | Exit | Result |
|---|---:|---|
| `git fetch --all --prune` | 0 | remote tips as in REPO_MAP.md |
| `pip install pytest` | 0 | pytest 9.1.1, pluggy 1.7.0, iniconfig 2.3.1 |
| `python -m pytest tests -q --collect-only` | 0 | `786 tests collected in 2.90s` |
| `python -m pytest tests -q -rs -p no:cacheprovider` (00:27:15Z to 00:29:29Z) | 1 | `1 failed, 785 passed in 133.57s (0:02:13)`; failure `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` |
| `python -m pytest tests -q` (exact command, after all records and probes were written, before commit; 00:49:02Z to 00:51:15Z) | 1 | `1 failed, 785 passed in 132.19s (0:02:12)`; same single failure; strays `data/reports/20261024_0049_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, empty `-wal`, `.pytest_cache/` removed by hand; tracked DB sha256 unchanged |
| `python tools/release_e2e.py --out <scratch>/e2e.md` (in a clone, 00:45:32Z to 00:46:58Z) | 0 | `Result: PASS. Stages with the expected exit code: 78 of 78. Network attempts: 0. Tracked files changed in the clone: 0. Tracked database byte-identical: yes.` (output sha256 `21af9c58d276499ee63612812009e21ecd2d9a3bbc1641d7f10c88eace16b3a5`) |
| `python -m memelab --help` / `init` / `analyze ... --no-persist` / `scout ... --report-dir <scratch>` (clone, temp DB) | 0 / 0 / 0 / 0 | see COMMIT_AND_TEST_LOG.md |
| `python -m memelab catalyst fc-health` (clone, temp DB, no key) | 1 | `config_missing`, key `missing` |
| `python3 audits/predictive-intelligence/phase_00/probes/state_history_probe.py origin/main <scratch>/state_history_main.json` | 0 | 89 export versions parsed, 0 failed; output sha256 `120d6bb9a9e75455e85f5c000f1924d8432f582fda6e00373f9df4285d14856d` |
| `python3 audits/predictive-intelligence/phase_00/probes/p01_ticker_identity_probe.py origin/main` | 0 | see P01 |
| `python3 audits/predictive-intelligence/phase_00/probes/p41_untrusted_page_probe.py` | 0 | see P41 |
| `python3 audits/predictive-intelligence/phase_00/probes/lineage_reproduction_probe.py` | 0 | see FEATURE_TRACE.md |
| `curl` GeckoTerminal day OHLCV (HIGGS pool) | 0 | HTTP 200, 17 candles 2026-10-04 to 2026-10-20 |
| `curl` GeckoTerminal 15-minute OHLCV with `before_timestamp=1791331200` | 0 | HTTP 200, 237 candles 2026-10-04T13:00Z to 2026-10-07T00:00Z |
| `curl` DEX Screener `/tokens/v1/solana/<HIGGS mint>` | 0 | HTTP 200, 1 pair |
| `curl` GitHub REST pulls list, unauthenticated | 0 | HTTP 403 |

## Sources consulted (links)

- Repository: https://github.com/RyzinEnagy/memelab-inbox (local clone, branches listed in REPO_MAP.md).
- GeckoTerminal OpenAPI spec: https://api.geckoterminal.com/docs/v2/swagger.json (fetched 2026-10-24, sha256 `041b6d03d6a49e69a146e6787462cc3e36191c5b21709de277aa0c31f521fbbe`); GeckoTerminal API page https://www.geckoterminal.com/dex-api; CoinGecko support article https://support.coingecko.com/hc/en-us/articles/22612838274841-Does-GeckoTerminal-have-an-API.
- DEX Screener API reference https://docs.dexscreener.com/api/reference and its OpenAPI file (sha256 `e40964ed9f7c598680b80abf4d296c23f20d67991735ada30c4a9a5ef5d12992`).
- claude.ai project "Memecoin Investing Lab" knowledge search for the backtesting package (no hit; hits were social-intel docs only).

## P34: backtesting package only exists as a ZIP

Searched: every remote branch's file list for "backtest" or "stress" paths (0 on every branch); `git grep -i -E "Backtesting (&|and) (Opportunity )?Stress|Stress-Testing|BACKTEST_NOT_AVAILABLE|audits/backtesting|Prompt_Package_v1\.2|v1\.2"` on every branch (0 files); `git log --all -i --grep="backtest\|stress"` (0 commits); `/mnt/user-data/uploads/` (only the predictive package); the linked Mac's connected folder (only the predictive package, 7 entries); the claude.ai project knowledge (no backtesting document). The word "backtest" appears only in social replay text ("a historical replay (backtest) on stored data", memelab/social/replay_core.py:1067). Result: the Backtesting & Stress-Testing v1.2 engine is not implemented anywhere reachable. Status BACKTEST_NOT_AVAILABLE (PI-D-006). The package's own reference file BACKTEST_V12_BRIDGE.md is a specification, not an installation.

## P01: same symbol, different mints

- Real data: across all exports, 102 symbols are shared by two or more mints (XMR 10, BTC 7, ETH 5, XRP 5, PLAGUE 5). Importing main's latest export into a temp DB (p01 probe): 984 tokens, 984 distinct mints, 101 symbols with 2 or more mints covering 261 mints; 701 theses, 0 without a token row; joining theses to tokens by mint gives 701 rows, by symbol 970 rows. Stored keys are mints (db.py tokens primary key; state.py `KEYS` tokens by `mint`), so the existing tables do not merge same-ticker tokens.
- Code search for SQL that filters or joins on `symbol`: one hit, launch/discover.py:298, which counts symbols to flag `TICKER_COLLISION` (a warning, not a join).
- One existing path links by ticker: the catalyst matcher (catalyst/match.py:109-160). With two candidates it marks AMBIGUOUS (tests/test_catalyst.py:85); with a single visible candidate the probe got `link_type TICKER_MATCH`, `link_strength MODERATE` for an impostor mint, and `catalyst/monitor.py:64 record_outcomes` would key outcomes on that mint. Recorded as PI-D-007 (not identity for this initiative). Existing tests that prove separation elsewhere: tests/test_social_identity.py:71, :80, :90, :99, :108, :190; tests/test_social_narratives.py:247, :264; tests/test_social_chronology.py:145; tests/test_social_store.py:301; tests/test_social_research.py:97, :236; tests/test_social_feed.py:172; tests/test_social_extraction.py:205; tests/test_catalyst_firecrawl.py:502 (symbol collision AMBIGUOUS when a page names a different contract).

## P41: malformed or hostile incoming content

- Social text: model prompts wrap post text in nonce-delimited blocks, validate output against a schema, and flag injection (tests/test_social_extraction.py:240 `test_prompt_injection_inside_a_post_is_data`); rendered feeds drop hostile handles, links and summaries (tests/test_social_feed.py:218 `test_prompt_injection_text_never_reaches_the_report`).
- Crawled pages: Firecrawl page text is read only by regular expressions, never by a model, and never stored in the public DB (FC-1, FC-7; tests/test_catalyst_firecrawl.py:158, :657, :689). The probe fed `page_facts` a page with model-directed instructions, a key-shaped string, a `<script>` block and a `javascript:` link: output held only identifiers (one CONTRACT, one ADDRESS_LINK, one TICKER, two CITED_DOMAINs), no instruction words, no key shape, no `javascript`; `redact` and `scrub` removed the key shape. Text is treated as data.
- Residual risk (data, not instructions): every valid contract on a page is kept, including one in a related-articles list or a "SYSTEM:" line, and match.py then links that exact mint NAMED_IN_SOURCE / STRONG. FIRECRAWL.md "First live run" notes the same. No test covers a hostile page that names a contract. For this initiative, a page-named contract is evidence about the page, not about the token (FC-8 already says so).
- State import accepts any http URL (state.py:70-74) and merges rows without validation; it is trusted only as far as the repository is.

## Iteration log

| Pass | What was done | Result |
|---|---|---|
| 1 | Inspection, checklist, suite, smoke, data and API inventory, probes for P01, P41 and history | all checks ran; first lineage smoke with deep files only gave 47 / DISTRIBUTION RISK vs stored 48 / REJECTED |
| 2 | Investigated the mismatch: full input set at HEAD (48 / REJECTED, 18 pools vs stored 4), then code `b6c424d` (stored report reproduced line for line except the change section) | lineage confirmed; gaps recorded (FEATURE_TRACE.md 1 to 5, PI-D-008) |
| 3 | Own adversarial pass (not independent) and records | below; skeptic not startable, PI-D-009 |

Three passes of the five allowed.

## Adversarial pass (run by the phase agent, NOT independent)

New wrong-but-plausible counterexample: "The state export's thesis rows are an as-of record: re-running the scorer on the archived inputs gives the stored score, so a stored `score`, `status` or `snapshot_json` can be used directly as a historical feature or label at `created_at`." It is wrong in two ways that an executable check catches: (a) with a plausible input set (the deep result files only) the current code gives 47 / DISTRIBUTION RISK / no fatal flag instead of 48 / REJECTED / WASH_TRADING_HIGH; (b) with the full input set the current code matches the score but reports 18 pools instead of 4 and different liquidity, because normalize.py changed in `4a9155b` after the report. Only the code of the day (`b6c424d`) with the full input set reproduces the stored report. Caught by `probes/lineage_reproduction_probe.py` (exit 0, runs A, B, C). A second strand of the same counterexample: `created_at` is not the availability time of the features (cli.py:44 takes the newest `_at`; collector.js:86 stamps run start; HIGGS inputs span 23:25Z to 23:59Z under 00:16Z). What was done: PI-D-008 and DATA_COVERAGE.md "Clocks"; no code change (Phase 00 is read-only).

Other attempts to falsify this phase's own claims:

- "main has code the branch lacks": `git diff --stat f084b60 origin/main` lists only `data/state/latest.json`. Holds.
- "the 785 passes are a regression from 748 + 37": consistent with the social handoff and the Firecrawl test count. Holds.
- "GeckoTerminal history survives token death": shown for one pool that stopped trading on 2026-10-20; not shown for a pool whose liquidity was pulled. Left UNKNOWN for Phase 01 (check a few rejected mints).
- "launch cohort gives outcome labels": 8 of 1,422 have a 24 h value; the read time is not stored. Recorded.
- "suite does not touch the tracked DB": a test opens it in WAL mode (shm and empty wal appear); hash unchanged. Recorded, not fixed (not Phase 00's scope).

## Status reasoning

Every baseline item is reproduced from source and commands (A1 to A15, A17 to A21). The independent attack (A16) could not run inside this phase, so the phase is NEEDS_REVIEW, not PASS. Recovery: the orchestrator gives `SKEPTIC_PACKET.md` to a fresh skeptic; if the skeptic finds no material failure and its counterexample is recorded, Phase 00 can be marked PASS and Phase 01 becomes eligible.

## Limitations

- Windows machines unreachable: `D:\memelab\crawl4ai-token.txt`, any Crawl4AI or Maxun install, the scheduled task definitions and the Firecrawl key file could not be checked (BLOCKED for verification, not assumed present or absent; the token file was not read).
- PR states come from docs; GitHub REST answered 403 unauthenticated and `gh` has no access.
- API depth was tested on one pool; rate limits come from provider documents that disagree (10 vs 30 calls a minute).
- The known failing test was not re-diagnosed; its clock dependence is taken from social-intel AUDIT_00.md and C-1.
- No independent skeptic in this phase (PI-D-009).

## Artifacts

Hashes are in PHASE_00_RESULTS.json `artifacts`.
