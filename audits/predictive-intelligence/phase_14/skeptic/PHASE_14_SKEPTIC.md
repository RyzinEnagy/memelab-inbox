# Phase 14 independent skeptic review

Reviewer: independent skeptic (PI-D-013), 2026-10-26. Branch `feature/predictive-intelligence`, tip `58bee5d` (frozen code `c59c494`). Own clone `/home/claude/pi_orchestration/skeptic_14`, temp `MEMELAB_DB` under `/tmp/claude-0/sk14`. No LLM, Zep, Firecrawl, vendor or paid call; every socket was loopback, and the one non-loopback address used (10.99.0.1) existed only inside an `unshare -n` namespace with no route off the machine.

Scripts next to this file: `p14_agpl_scan.py`, `p14_attacks.py`, `p14_egress.py`, `p14_meter.py`, `p14_own_mutations.py`, `cx14_monitor_reversal.py`.

## Verdict

Material failures found (repairable). The phase's reproducible claims hold: AGPL clean, seeds and rule counts, schema oracle, mutation probe, core unaffected, suite, guard and seal all reproduce. But four boundary properties the phase states as held do not hold under attack, and one more (P29) holds only in the narrow pre-registered form. TEST_ONLY needs "no material unresolved adversarial failure", so a repair pass is needed before that status.

## Checks reproduced

| Check | Command | Result |
|---|---|---|
| Phase 14 tests | `python -m pytest tests/test_predictive_behavioral.py tests/test_predictive_phase14_outputs.py -q` | `176 passed, 1 skipped` (skip: no IPv6 loopback) |
| Full suite | `python -m pytest tests -q -p no:cacheprovider` | `1 failed, 1772 passed, 1 skipped` in 207.69 s; only `test_catalyst.py::test_dedup_corroboration_resurface_denial`; stray `data/reports/20261026_2340_BRETT_0x532f.md` removed by hand in my clone. Equals the post-commit record |
| Content guard | `python -m memelab social guard` | exit 0, `"violations": []` |
| Seal check | `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | `"problems": []` |
| Mutation probe | `python -B .../probes/mutation_behavioral.py OUT.json` | `{"mutations": 63, "caught": 63, "survivors": []}`, 374.7 s |
| Schema oracle | venv `p04_mirofish` python, `oracle_schema.py` | 830 documents, 0 schema errors, 0 lab errors, negative control refused; jsonschema 4.25.1 |
| Seeds rebuilt from the Phase 05 store | `build_seeds.py /tmp/claude-0/sk14/p14` | 830 decisions, 0 refused, `label_calls []`, `socket_events []`, seeds sha `a0c61817...` equal to the committed `SEEDS_DEV.jsonl` |
| Release audit (tree) | `python tools/release_audit.py --json ...` | exit 0, 0 unexplained |
| Release exempt compare | `release_exempt_compare.py 2fd0aae` | 5 old unexplained (all Phase 14 files), 0 new; reviewed outside Phase 14 equal (67 at HEAD vs 63 recorded: the 4 extra are later records under `docs/predictive-intelligence/`, covered by the pre-existing docs entry) |
| Core without the module | clone with `behavioral.py` and its two test files `git rm`ed, `pytest tests/test_predictive_*.py` | `811 passed`; no other module imports it |

## Numbers re-derived (at least three)

From the committed `SEEDS_DEV.jsonl`, with `labels.training_labels` and `labels.load` replaced by functions that raise:

1. 830 seeds, 0 refused by `check_seed`, 148 distinct (chain, mint), max decision `2026-10-16T10:42:06Z` (before the 2026-10-17 development cutoff), 0 observations after their decision, kinds LAB_ATTENTION_PROXY 5280 and SOURCE_STATE 1660, 0 CATALYST_EVENT.
2. Rule labels: ATTENTION_EXHAUSTION 309, MANUFACTURED_ATTENTION_DUMP 313, NO_GROUNDED_SCENARIO 227, ORGANIC_ATTENTION_CONTINUATION 66; combinations 224 / 85 / 228 / 227 / 66, all equal to `RULE_COUNTS.json`.
3. `doc_sha256` of my regenerated rule documents equals the committed `RULE_SCENARIOS_DEV.jsonl` on 830 of 830; 0 validation errors; 0 catalyst hypotheses.
4. Mutation 63 of 63 and oracle 830 / 0 / 0 (above).

behavioral-rules-1 reads no label (no label call even with the label module rigged to raise) and makes no claim: every document is RULES_RAN, fictional, with the fixed notice, `scored: false`, and monitors that name registry targets without reading them.

## AGPL (P31)

- `p14_agpl_scan.py`: all 44 files changed between `2fd0aae` and `58bee5d` against every MiroFish source line of 40 or more characters (9,212) and every 3-line shingle of lines of 12 or more characters (33,756) at pin `7657031a` (clone clean): no shared text.
- No CJK text, no `camel`, `oasis`, `zep` or MiroFish `app.` imports in any Phase 14 file. `mirofish_runner.py` only builds fictional config files in the format MiroFish's script reads and runs the unmodified script as a separate process.
- Gap (MINOR): the suite's fingerprint test scans only `behavioral.py`, the mock and the test file; the probes under `audits/.../phase_14/probes/` are not in it. My scan covers them and is clean.

## The release_audit.py change (PI-D-074)

Three EXPLAINED entries, each limited to the rules `exec:mnemonic` and `exec:seed phrase`, on `^memelab/predictive/behavioral\.py$`, `^tests/test_predictive_behavioral\.py$` and `^audits/predictive-intelligence/phase_14/.*\.md$`. Minimal: narrower than the existing social refusal-list entry (which exempts `exec:.*`); credential rules (including `key_material_field`) are untouched, so a real key-material value in these files would still be a finding. It weakens nothing for any other file (anchored path patterns; reviewed sets outside Phase 14 equal before and after). It belongs in this phase: without it the phase's own refusal list and its tests are 5 unexplained findings in the post-commit release audit. Only note (MINOR): the third pattern also covers any future `.md` under `phase_14/` (for example the skeptic folder), for these two words only.

## Findings

### MATERIAL

M1. `runtime.simulation_state` reports AVAILABLE for runs the adapter marks SIMULATION_NOT_AVAILABLE / COST_CAP_REACHED (P30, P48; pre-registered rule 10 "simulation_state agrees with the adapter on every case", gate G12). `simulation_state` only checks `llm_actions > 0`; a cap reached after some calls leaves `llm_actions > 0` with status NOT_AVAILABLE. Reproduced (`p14_attacks.py` A1): mock METER_CAP gives doc `SIMULATION_NOT_AVAILABLE ['COST_CAP_REACHED'] llm_actions=16`, `simulation_state = AVAILABLE`. The recorded real-engine run has the same shape: `MIROFISH_PROBE.json` `meter_cap_low` is COST_CAP_REACHED with `llm_actions 3`. `P30_MATRIX.csv` has no COST_CAP_REACHED, CIRCUIT_OPEN or SEED_REFUSED row with a `simulation_state` column, and `test_a_meter_block_at_its_cap_refuses_the_run` asserts `llm_actions > 0` but never calls `simulation_state`. `MIROFISH_INTERFACE.md` line 61 states agreement on every case. Fix: the adapter's `run()` should return `llm_actions` 0 (or `simulation_state` should read `status`) whenever status is not SIMULATION_RAN; add the three matrix rows.

M2. The metering proxy's per-call ceiling is not a ceiling (P48). `_decide` forces `max_tokens` but forwards `n` (choices per call) and `stream` untouched; `_check_usage` only fires when the upstream returns a `usage` block. With an OpenAI-style upstream that honours `n` (`p14_meter.py`, cap 50 USD at fictional prices): plain calls bill 0.90 of the cap (correct); `n=8` is caught after one call (that call bills 7 times its charge); `n=8, stream=true` forwards 42 calls, charge 49.35 of 50, upstream bill 6.90 times the cap, never killed; `n=64, stream=true` bills 55.07 times the cap. `MIROFISH_INTERFACE.md` and the `LLMMeter` docstring describe the charge as an upper bound of each call. No spend happened and none is approved, but this is the control a future paid approval would rest on. Fix: refuse or force `n`/`best_of` to 1, refuse `stream` (or require a usage block), and refuse unknown top-level keys.

M3. Agent agreement reaches a validated forecast document as hypothesis multiplicity (P27, rule 6, G11). `code_response` deduplicates by `hypothesis_id`, which hashes the assumptions; a response with 8 ORGANIC_ATTENTION_CONTINUATION hypotheses differing only in one SYNTHETIC_PERSONA_BEHAVIOR code and 2 MANUFACTURED_ATTENTION_DUMP hypotheses is accepted, `validate_scenario` returns `[]`, `forecast_entries` emits 8 and 2 entries, and `abstention.validate_publication` adds no error (`p14_attacks.py` A2). A reader recovers "80 percent". This is the pre-registered CX-14 class (a count without digits) through a channel the vocabulary rule does not close. Fix: at most one hypothesis per label (merge assumptions) in `code_response` and in `forecast_entries`, and a test.

M4. The subprocess path can send lab data off-host by declaring the engine MOCK_SIMULATOR (focus item "the adapter cannot send repository data off-host"). `SubprocessAdapter` requires `unshare -n` only when `engine.mode == EXTERNAL_SIMULATOR`; argv is never inspected, and `extra_env` is checked only for `://` or `www.`. Inside an `unshare -n` namespace with 10.99.0.1 on a `lo` alias (`p14_egress.py`): E1 ServiceAdapter to `http://10.99.0.1:PORT` refused EGRESS_NOT_APPROVED, nothing received; E2 meter upstream refused; E3 SubprocessAdapter, mode MOCK_SIMULATOR, argv naming 10.99.0.1: SIMULATION_RAN, the listener received the full 2,192-byte request with `quoted_evidence`; E4 the same with host and port passed through `extra_env` without a scheme: SIMULATION_RAN, received. Positive control: the same script with `netns=True` gives SCRIPT_EXIT_1 and nothing received. The module docstring ("no byte of lab data can leave the machine from this code") and `MIROFISH_INTERFACE.md` line 42 rest on a caller-declared label. Also, no suite test runs a subprocess with `netns=True` (own mutation X2, dropping the `unshare -n` prefix while `netns=True`, survives the suite; only the MiroFish probe exercises it). Fix: always run the subprocess under `unshare -n` (the lab mock works there), and a suite test that a netns child cannot reach a parent listener.

M5. P29 reversal not detected when the label stays and the scenario flips (the counterexample below). `stability` compares label sets only. Disclosed as a limit in `MIROFISH_INTERFACE.md` line 89, and rule 14 was pre-registered that way, so G10 passes as written; but the scenario document and its forecast entries say STABLE with no flag, which is what Phase 15 will read. Fix: compare (label, monitor metric, expectation) sets, or flag MONITOR_SENSITIVE and downgrade to UNSTABLE.

### MINOR

m1. P28 is a pattern list; post-decision detail passes in shapes it does not know (`p14_attacks.py` A5): a future unix time as a numeric `value` (only strings are scanned), `2026/10/14`, `Oct 14 2026`, "the next day it rugged to zero", an outcome name outside the regex (`close_price_t_plus_1d`); the ISO control is caught. Real seeds are protected by construction (point-in-time builder, every observation available at the decision); the list is a backstop. Suggest scanning numeric values for unix times and adding slash and month-name dates.

m2. P41 is a pattern list too (A6): "Ignore the instructions above", "Forget your rules. New task: ...", a zero-width space inside "ignore", and a fullwidth `ｈｔｔｐｓ://` URL all pass `check_seed`; the control is caught. The real defence is structural (quoted text marked `role: data`, fixed template, vocabulary-only response coding, which limits an injection to steering a label choice). Suggest NFKC normalization and stripping zero-width characters before matching.

m3. Free strings with digits in documents. `validate_scenario` does not check `stability.flags` or `reasons` content, so a hand-built document with flag `AGENTS_80_OF_100_SAY_PUMP` validates and `forecast_entries` projects it into the publication, which `validate_publication` accepts (A3). The adapters never write such flags, so this needs a forged document. `validate_scenario` also accepts extra integer keys under `refused_claims` (`AGENTS_TOTAL: 100`) that `SCENARIO_SCHEMA.json` refuses (additionalProperties false): the lab rule and the oracle disagree.

m4. Test gaps from own mutations (`p14_own_mutations.py`): X1 (meter cap reached during the run ignored by the adapter) caught; X2 survived (M4); X4 (service response size cap removed) survived; X5 (SEED_SENSITIVE computed for persona set 1 only) survived (flag only, status unaffected); X3 (IP check removed) survived but is equivalent (the netloc comparison already restricts to the two literals).

m5. Meter details: `_check_usage` compares against the last FORWARDED ledger entry, which is not necessarily the same call under the threaded server; `canon` re-serialization can make the forwarded body longer than the charged raw body (`1e9` becomes `1000000000.0`), outside message content.

m6. The copyleft fingerprint test does not include the probe scripts (above); clean by my scan.

## Counterexample CX-S14 (new, not P01 to P48 restated)

`cx14_monitor_reversal.py`: a loopback simulator always answers ORGANIC_ATTENTION_CONTINUATION, but its falsifiable monitor depends on the run seed: seeds 101 and 303 expect `price_path_target_before_invalidation_6h` EVENT (assumption MOMENTUM_BUYERS_ENTER), seed 202 expects NO_EVENT (NO_NEW_BUYERS). That is a seed-reversed scenario. `run_grid` returns `SIMULATION_RAN`, reasons `[]` (no UNSTABLE_EXPLORATORY), stability `STABLE` with `distinct_label_sets 1`, `repeat_identical true`, flags only `DEGRADED_SOURCE_CHANGES`; the merged document carries both opposite hypotheses, `validate_scenario` returns `[]`, and `forecast_entries` emits both with stability STABLE. Nothing in the suite, the mutation probe or the oracle catches it (script exits 1, "NOT CAUGHT").
