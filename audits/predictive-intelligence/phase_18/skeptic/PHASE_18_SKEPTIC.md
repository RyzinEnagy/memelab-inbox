# Phase 18 independent skeptic review

Reviewer: independent skeptic (orchestrator subagent), 2026-10-27. Branch `feature/predictive-intelligence`, tip `e77d62e` (code commit `ea799da`, CP18-1). Own clones: `/home/claude/pi_orchestration/skeptic_18` (attacks, probes) and `/home/claude/pi_orchestration/skeptic_18_suite` (full suite, post-commit checks). Temp `MEMELAB_DB` under `/tmp/sk18*`. Real-path runs inside `unshare -n`. No network calls, no Firecrawl, nothing written in `/home/claude/memelab-inbox`.

Scripts next to this file:

- `PHASE_18_attacks.py`: 9 pytest attacks (A1 to A9) on the phase code; each asserts today's behavior, so a pass documents the finding. Run: `cd skeptic_18 && MEMELAB_DB=/tmp/x.sqlite python -m pytest -q -p no:cacheprovider -s /home/claude/pi_orchestration/skeptic/PHASE_18_attacks.py --rootdir .` Result: `9 passed in 5.19s`.
- `PHASE_18_extra_mutations.py`: 12 extra mutations of `reports.py` run through the phase's own harness. Result: 7 caught, 5 survivors.

## Verdict

Material failures found (4). The abstain-only real outputs reproduce exactly and show no probability, no score boost and no trade step; the flag-off claim, golden files, pins, suite and post-commit checks all reproduce. The failures are in the alert rules and the visibility of risk: a liquidity risk flag does not override an optimistic forecast (prompt item 4), alert evaluation silently skips everything after a state reset or when two states share an alert database, a deferred newest snapshot carrying a new fatal flag is shown as "covered" with vetoes "none", and token symbols such as `SELLNOW` reach a "WARNING: risk override" alert label.

## Checks reproduced

| Check | Command | Result |
|---|---|---|
| Phase 18 tests | `python -m pytest tests/test_predictive_reports.py tests/test_predictive_phase18_outputs.py tests/test_predictive_contract.py -q -p no:cacheprovider` | `150 passed in 26.43s` |
| Full suite at `e77d62e` | `python -m pytest tests -q -p no:cacheprovider` (separate clone) | `2 failed, 2122 passed, 1 skipped, 1 warning in 500.23s`; failures exactly the two known clock-dependent tests; stray `data/reports/20261027_1122_BRETT_0x532f.md`, `data/memelab.sqlite-shm`, `-wal` (pre-existing test leak, removed) |
| Seal | `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | exit 0, `"problems": []` |
| Guard | `python -m memelab social guard` | exit 0, `"violations": []` (843 JSON files at `e77d62e`, 842 at `ac19668`: one more committed JSON) |
| Release audit | single-branch clone, `python tools/release_audit.py --history` | exit 0, "Needs action: no." |
| Goldens | `run_reports.py goldens /tmp/sk18/gold && diff -r /tmp/sk18/gold tests/fixtures/predictive/phase18/golden` | identical (7 files) |
| Real-path smoke at `e77d62e` | `bash .../phase_17/probes/real_path_smoke.sh e77d62e /tmp/sk18/smoke` then `run_integration.py smoke` | every exit 0; 9 flag-off reports and stdout byte-equal to `b0fad12`; my own table dump differs only in wall-clock columns (`chains.first_seen_at`, `social_schema_migrations.applied_at`, `tokens.last_seen_at`); 24 ABSTAIN lines, 0 FORECAST lines |
| Export replay | `unshare -n ... run_integration.py replay /tmp/sk18/replay` | 52 window events, DISCOVERY 47, MATERIAL_CHANGE 5, round 2 DUPLICATE 52, 0 documents, 0 probabilities, 0 sockets |
| Real reports and alerts (re-derived numbers) | `unshare -n ... run_reports.py real ...` | scout: 8 opportunities, 24 targets, 0 probabilities, 24 abstained, 16 not attempted, 3 vetoes, 8 of 8 snapshots verified; replay: 47, 141, 0, 22 vetoes; scout alerts 0 new, 3 SOURCE_STALE; replay alerts 8 new, 15 SOURCE_STALE. Committed outputs equal mine after masking ids and times, except the wall-clock "age at capture 20.4 days" vs "20.5 days" |
| Percents in the real replay report | `grep "%"` excluding definitions and the labelled line | only the one labelled measured-change line and the units line |
| Phase mutation probe | `python -B .../probes/mutation_reports.py /tmp/sk18/p18_mut.json` | `{"mutations": 49, "caught": 49, "survivors": []}` (632 s); the harness does report survivors (my extra run below) |
| Pin file | compare `PINNED_SHA256.json` to `git show 4ebccc3:<path>` | 164 entries, 0 mismatches, every `.py` under `memelab/` at `4ebccc3` is pinned; only new module is `reports.py`; the 8 `memelab/bridge/*.js` files are not pinned but unchanged (`git diff 4ebccc3 HEAD` touches only `reports.py`, three test files, fixtures, phase_18 audits, ledger and the three predictive docs) |
| Amended test | `git diff 4ebccc3 HEAD -- tests/test_predictive_contract.py` | one assert `[] -> ["reports.py"]`, exact list, negative cases still present: justified |
| `--send` | CLI with `--send` | exit 2, "no external delivery is approved", no alert folder created; `reports.py` uses only `AT.FileSink` and `AT.dest_ref` |
| Flag off | CLI `report` with `{}` config | "FLAG_OFF; nothing read or rendered" |
| Ledger | `LEDGER_TOTALS.json`, `SEARCH_LEDGER.csv` | 22 P18 rows, all `REPORT_RUN_NOT_A_CONFIGURATION`; N_search 130, sensitivity 169 |
| CP18-1 honesty | PI-D-100, `rerun_cp18_1_diff.json`, real replay | recorded openly before the code change, rule 4 kept; a loosening of the phase's own rule 13 after seeing a result, adopted by self-review, not the prompt gate. Not quietly moved. Wording nit: the label "measured market changes" also covers "status changed" and "last attempt N s ago" |

## Findings

### MATERIAL

1. **A liquidity risk flag does not override an optimistic forecast (prompt item 4).** `alert_candidates` suppresses reevaluate only for `ex["veto"]` or a backtest veto; a liquidity fall of 20% or more is a risk_override trigger but not a veto, and the report's override marker also keys on `veto` only. Attack A1: fixture SHADOW forecast 47% (41% to 65%, base rate 29%); 13 h later the same token at liquidity -33%, fresh inputs. Alert run 2 emits for the same pass-2 snapshot both `risk_override warning` ("... liquidity -33% since the previous attempt ... The research estimate on this snapshot is overridden.") and `reevaluate notice` ("A verified research estimate ... 47% ... above the base rate"); suppressed list empty. The report row reads `FORECAST 47% (41% to 65%) FORMAT-ONLY FIXTURE | ... | none | FRESH` with no "overridden". The prompt says "sudden liquidity/whale source risk flags override optimistic forecast and force warning"; frozen rule 10 narrowed this to vetoes, and CX-18 claims the optimistic notice beside the warning is caught. TEST_ONLY path today, but it is this phase's alert rule.
2. **Alert evaluation silently skips everything after a state reset or when two states share one alert database.** `alert_run` picks passes by seq only (`first = prev.snapshot_run_id + 1`); `feed_sha256` (the pass record id) is stored but never compared. Attack A4: state with 3 passes evaluated; state folder replaced (the natural recovery from STATE_TAMPERED, or a second state on the default `data/private/predictive_alerts/alerts.sqlite`) by a state whose one pass holds CANNOT_EXIT_5K. A fresh alert database gives the risk_override warning; the shared one returns outcome `evaluated`, 0 candidates, no reason. This path is live today (the replay produced 8 risk_override previews). No test covers it.
3. **A deferred newest snapshot that adds a fatal flag is shown as covered, with vetoes "none".** Attack A8: ABC attempted clean in pass 1; in pass 2 its newest snapshot carries CANNOT_EXIT_5K but is DEFERRED_LATENCY_BUDGET. The report shows ABC from the older attempt (`| none | FRESH |`), the not-attempted row says `| yes | ... | none |` under "Covered by a report above", and the alert run gives no alert and no suppression. `covered_by_report` only checks that the mint has some opportunity, not that the shown attempt is the newest snapshot. With a FORECAST on the older attempt this would show a number beside a concealed exit veto. The lab's own token report still shows the flag.
4. **Counterexample CX-SK18 (new): run-together trade words in a symbol pass the sanitization.** `integration._ident` and `check_text` match trading words on word boundaries only, so `BUY-NOW` is withheld (the injection world tests it) but `SELLNOW`, `BUYNOW`, `TAKEPROFIT`, `APEIN`, `LONGNOW`, `EXITNOW`, `MOONSHOT`, `PUMPIT`, `100X` are printed. Attack A9 renders `## SELLNOW \`solana:...\`` and `| SELLNOW |` in the report and a dry-run alert reading "memelab predictive research alert, WARNING: risk override / SELLNOW on solana (...)". Rule 7 says token text carrying a trading word is withheld; no test or check catches the run-together form. The helper is Phase 17's, but Phase 18 relies on it for its own rule 7.

### MINOR

5. A FORECAST number is tied to the stored point, not to the raw number. Attack A3: editing the document probability and the request's `calibrated_point` together (raw number untouched) and re-sealing shows 60% while the raw number recomputes to 47% through the card's calibrator. `reports.py` never calls `verify_point`, yet every report prints the FACT "a FORECAST's number must equal the point recomputed from the raw number ... (verify_point)". CX-18 covers only the one-sided forgery. Needs write access to the private state, so minor; the FACT line should say "checked when written" or the reader should recompute.
6. Mutation coverage is narrower than G22 suggests. Extra mutations surviving the phase tests: X1 token row of another chain used, X3 "unknown" veto dropped from the at-a-glance Vetoes column, X4 non-vocabulary lab status printed raw, X5 change strings printed raw, X10 backtest-veto reasons dropped from the execution section (X3 and X10 are veto-visibility paths). Caught: X2, X6 to X9, X11, X12.
7. Attack A2: an uncovered not-attempted event whose exact mint contains `1profit2` (base58 vanity, `EXTRA_WORDS` uses letter-only lookarounds) makes `render` raise; no report at all. Only opportunity mints are removed before the check.
8. Attack A5: a clock that goes back one day leaves alerts `too_soon` ("last evaluation -1440 min ago") until it catches up.
9. Attack A6: "liquidity became unknown" (a rug where the vendor drops liquidity) never triggers the liquidity rule.
10. Rule 9 says the alert database is refused for the lab database; only the active `MEMELAB_DB` is refused. `alerts --lab-db X --alert-db X` with X outside the repository wrote the 8 alert tables into a lab database copy.
11. "A notice never takes a warning's place" holds within one run only: `used` counts all severities for the local day, so notices from an earlier run can push a later warning into `daily_cap` (code reading, same as the social engine).
12. Rule 14 lists the allowed imports without `memelab.db`; `default_alert_db` imports it and the G19 test allows `(None, "db")` silently.
13. Alert risk text prints "liquidity -33% since the previous attempt", outside the amended rule 13 (event line only, labelled).

## Counterexample

CX-SK18 (finding 4, script `PHASE_18_attacks.py::test_a9_...`): a token whose symbol is `SELLNOW` with the fatal flag CANNOT_EXIT_5K. Every check passes: `_ident("SELLNOW") == "SELLNOW"`, `check_text` sees no `\bsell\b`, the golden and injection tests only try `BUY-NOW`. The dry-run alert prints "WARNING: risk override" above "SELLNOW on solana (...)", which reads as an instruction. Nothing in the suite or the probes catches it; a substring check on the letters of token text (as `FORECAST_WORDS` already does) would.
