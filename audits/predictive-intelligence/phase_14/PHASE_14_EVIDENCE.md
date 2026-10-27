# Phase 14 evidence: isolated behavioral-simulation hypothesis interface

Status: **TEST_ONLY** after repair pass 2 (PI-D-076, PI-D-077): the simulator path is proved only on fixtures, the lab's mocks and MiroFish's script against a canned mock LLM; MIROFISH_GATE BLOCKED for live use until Elving approves LLM spend. The statistical-engine-unaffected item and the safety items hold under the independent skeptic's attacks. The first-pass sections below are kept as recorded; the repair pass section at the end supersedes their numbers where they differ.

- Branch `feature/predictive-intelligence`; HEAD before `2fd0aae` (Phase 13 PASS); pre-registration `9ed8377` (2026-10-26T22:21:08Z); frozen code `c59c494` (23:08:49Z); recorded run outputs `872578d` (23:18:04Z); records on top.
- Machine: Linux, Python 3.13.17 (lab), Python 3.12.3 (MiroFish venv `/home/claude/pi_research/venvs/p04_mirofish`), root (for `unshare -n`).
- Package: 41 of 41 checksums OK (`sha256sum -c SHA256SUMS.txt`).
- Spend: 0 credits, 0 vendor calls, 0 language-model calls, no key. Network: 1 `git ls-remote` of github.com/666ghj/MiroFish. Every socket the Phase 14 runner and tests opened went to 127.0.0.1.

## Entry gate (G2), at `2fd0aae`

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests -q -p no:cacheprovider` | 1 | `1 failed, 1596 passed, 1 warning in 190.45s`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; strays `data/reports/20261026_2212_BRETT_0x532f.md` and the sqlite side files removed by hand |
| `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | 0 | `"problems": []` (`evidence/entry/seal_check.json`) |
| `python -m pytest tests/test_predictive_calibration.py tests/test_predictive_abstention.py tests/test_predictive_phase13_outputs.py tests/test_predictive_runtime.py -q` | 0 | 276 passed |
| `python -B audits/predictive-intelligence/phase_13/probes/run_calibration.py <scratch>` | 0 | 22 of 24 files byte-equal to the committed Phase 13 outputs; `POST_OPENING_LOG.json` and `run_log.json` differ only in head and time |
| Phase 13 RESULTS.json | | PASS; tracked `data/memelab.sqlite` sha256 `068287c0...` |

## MiroFish recheck (G3)

Clone `/home/claude/pi_research/src/666ghj__MiroFish` at `7657031ac01184afe2cb220f5ee3545573b5e843`, clean; `git ls-remote https://github.com/666ghj/MiroFish HEAD` gives the same commit (2026-10-26); LICENSE sha256 `8486a10c4393cee1c25392769ddd3b2d6c242d6ec7928e1414efff7dfb2f07ef` (AGPL-3.0); `backend/pyproject.toml:5` `requires-python = ">=3.11,<3.13"`; `backend/app/config.py` `validate()` requires `LLM_API_KEY` and `ZEP_API_KEY` and refuses `ZEP_API_URL`. Sources: https://github.com/666ghj/MiroFish (pinned clone), Phase 03 `research/MIROFISH.md`, Phase 04 `adoption/MIROFISH_FEASIBILITY.md` (ISOLATED_MOCK_ONLY).

## What was built

- `memelab/predictive/behavioral.py` (behavioral-1; standard library plus the stdlib-only `contract` and `runtime`; flag OFF; imported by no other module). Details: `behavioral/MIROFISH_INTERFACE.md`; schema `behavioral/SCENARIO_SCHEMA.json`.
- `tests/fixtures/predictive/behavioral_mock.py` (lab mock service in 24 behaviour and failure modes plus 3 subprocess-only modes, mock LLM in 3 modes, subprocess entry).
- `tests/test_predictive_behavioral.py` (170 passed, 1 skipped: IPv6 loopback is not available in this sandbox) and `tests/test_predictive_phase14_outputs.py` (6).
- Probes in `probes/`: `build_seeds.py` and `seed_convert.py` (real seeds), `run_behavioral.py` (recorded run), `mirofish_runner.py` (inside `unshare -n`), `mutation_behavioral.py`, `oracle_schema.py`, `release_exempt_compare.py`.
- `tools/release_audit.py`: three EXPLAINED entries for the refusal words, with unchanged findings elsewhere (PI-D-074).

## Recorded run at `c59c494`

| Command | Exit | Result |
|---|---|---|
| `python -B audits/predictive-intelligence/phase_14/probes/build_seeds.py <scratch>/rec` (23:09:02Z) | 0 | 830 development seeds of 925 store decisions, 0 refused, 0 label calls, 0 socket events, feature store sha256 unchanged, seeds sha256 `a0c61817...` (equal to the debug run) |
| `python -B audits/predictive-intelligence/phase_14/probes/run_behavioral.py <scratch>/rec` (23:09:12Z to 23:11:05Z, 113 s) | 0 | head `c59c494`, dirty code none, 211 socket connects all to 127.0.0.1, 0 label calls, 0 sealed opens; outputs copied to `behavioral/` and `evidence/run_log.json` |
| `python -B audits/predictive-intelligence/phase_14/probes/mutation_behavioral.py <scratch>/rec_mutation.json` (23:11:26Z) | 0 | 63 mutations, 63 caught, 0 survivors, 341 s (`evidence/mutation_behavioral.json`) |
| `python -B audits/predictive-intelligence/phase_14/probes/oracle_schema.py audits/.../evidence/oracle_jsonschema.json` | 0 | jsonschema 4.26.0: 0 errors on 830 documents; lab validator 0; negative control refused by both |
| `python -m pytest tests/test_predictive_phase14_outputs.py -q` | 0 | 6 passed |
| `python -m memelab social guard` | 0 | 0 violations |

Results (numbers from the committed outputs):

- Rules on real seeds (`RULE_COUNTS.json`): 830 RULES_RAN; ATTENTION_EXHAUSTION 309, MANUFACTURED_ATTENTION_DUMP 313, ORGANIC_ATTENTION_CONTINUATION 66, NO_GROUNDED_SCENARIO 227; 0 catalyst hypotheses (no seed holds a catalyst event); twin byte-equal; 0 validation errors; unscored. Real seed with one post-decision observation, one post-decision date, one behavioral-derived observation: each SEED_REFUSED.
- Grids (`MOCK_GRID_RUNS.json`): STABLE mode STABLE on both seeds; SEED_SENSITIVE, PERSONA_SENSITIVE, NONREPRODUCIBLE and EVIDENCE_BLIND modes UNSTABLE with their flags on both seeds.
- Failure matrix (`P30_MATRIX.csv`): 39 cases; 36 SIMULATION_NOT_AVAILABLE or NOT_SUPPORTED with named reasons, 3 run (service STABLE, WALLET_CLAIM with both claims dropped, subprocess STABLE); `simulation_state` agrees on all; gates make 0 requests; no case changes a contract abstain reason.
- Cost (`COST_CAP.json`): worst case 1,465,728 micro-USD against cap 0, 0 requests; meter charged 9,709 of 10,000 micro-USD then refused, second run 0 upstream calls; max_tokens 512 upstream; breaker 500 x5 then 503; prompt 413; call cap 429; kill 503.
- MiroFish (`MIROFISH_PROBE.json`): cap 1.0 SIMULATION_RAN NOT_CODABLE (8 actions, 8 calls, 0.080473 USD fictional, 10.5 s); repeat 9 actions, 0.097535, different trace; cap 0.03 COST_CAP_REACHED (3 forwarded, 60 refused, 0.027665); LLM down NO_LLM_ACTIONS with script exit 0 and the meter breaker open; config cap 0.05 refused before start; all carry the P26 flags.
- Core (`CORE_UNAFFECTED.json`): the import blocker works; Phase 13's runner exit 0; 22 files byte-equal, the 2 run logs differ, 0 new.

Scope of "no label read": Phase 14's own code, seed builder and runner read no label (`labels.training_labels` replaced by a raising function, 0 calls). The core-unaffected check re-executes Phase 13's recorded runner in a subprocess, which reads what Phase 13 read (development labels and committed Phase 12 files) and writes only to a temporary folder; no new outcome is computed or seen.

## Gate items

| Item | Result |
|---|---|
| G1 | 41 OK |
| G2 | entry gate above |
| G3 | pin, license, keys and Python limits re-read; upstream HEAD equal |
| G4 | P31 tests pass in the full suite; AST tests: stdlib and two stdlib-only package modules; no other module imports behavioral.py |
| G5 | default NOT_APPROVED; `"true"` string NOT_APPROVED; non ON_DEMAND_LOCAL modes NOT_SUPPORTED; kill switch before contact; `simulation_state` agrees |
| G6 | 20 non-loopback forms refused with no socket; suite audit hook and run hook see only loopback; meter upstream and bind loopback only |
| G7 | planted parent key absent in the child; key-like and remote-URL extra_env refused; meter ledger holds sizes and hashes only |
| G8 | schema committed; 26 violation cases plus 3 sha and status checks; jsonschema oracle agrees |
| G9 | 26 refusal tests; 830 real seeds pass; 3 real-seed mutations refused |
| G10 | five grid modes as designed; direct stability rules (short grid, failed cell, deterministic repeat, five of six) |
| G11 | probability, fraction, count codes (CX-14) refused; projection strings only, `validate_publication` result unchanged; calibration refuses behavioral source |
| G12 | every rule 10 state reached; statistical fields of a real Phase 13 document unchanged by the projection |
| G13 | worst-case refusal, cap, breaker, max_tokens, prompt and body caps, call cap, kill, bad settings, usage above charge (fail closed) |
| G14 | seed and response injection refused; sections separated; invented catalyst refused; wallet and identity claims dropped and counted; insider intent only as speculation |
| G15 | eight contamination cases |
| G16 | twin byte-equal, rules sha pinned, 830 valid documents, 0 catalyst hypotheses, 0 label calls |
| G17 | MiroFish table above |
| G18 | core check above; full suite below |
| G19 | 63 of 63 mutations caught at the frozen code |
| G20 | records and post-commit checks (below and `postcommit/`) |

## Iteration log (bounded loop, not independent)

1. Build pass: first test run 4 failures, each a real defect or test error: a None endpoint passed the egress gate (fixed: the service adapter refuses any endpoint that is not a loopback literal); NaN made `check_seed` raise instead of refusing (fixed: canonical hashing failures become refusal codes); the NONREPRODUCIBLE mock's repeat matched its first cell (mock fixed); a test compared the wrong keys.
2. Self-review pass (PI-D-073): characters / 4 would undercount MiroFish's Chinese prompts, so a live bill could pass the cap; the meter now charges body bytes plus 64 tokens, refuses bodies over 64 KB and stops forwarding if usage ever exceeds a charge; a loopback service could itself reach the network, so external engines run only in `unshare -n`. First mutation probe (59 mutations, old code): 54 caught; the 5 survivors were a redundant branch (removed), two missing reason checks, a missing assumptions test, an untested response-meter branch and a non-canonical port; tests added; 63 of 63 caught afterwards.
3. Pre-freeze suite (PI-D-074): two earlier guards fired (the Phase 10 isolation text test; the release audit's refusal words); the converter moved out of `memelab/`, three narrow EXPLAINED entries added with unchanged findings elsewhere. Suite then `1 failed, 1766 passed, 1 skipped`.
4. Debug runs before the frozen code (listed in `run_behavioral.py` DEBUG_RUNS): seed builder, two MiroFish boundary runs (one to size the low cap), one runner run without MiroFish. None read a label or scored anything.

## Own adversarial pass (not independent; the orchestrator's skeptic follows)

- CX-14 (named in advance): a simulator reports "8 of 10 agents expect a pump" as code `AGENTS_8_OF_10` or `EIGHT_OF_TEN_AGENTS_EXPECT_PUMP`, so no probability key and no float appear. Caught: codes must match `^[A-Z][A-Z_]*[A-Z]$` and the fixed vocabulary; both forms give BAD_RESPONSE (`test_agreement_never_becomes_a_number[COUNT_CODE]`, `[COUNT_WORDS]`; P30 matrix rows).
- A string-valued agreement key (`consensus: "most"`, `chance: "high"` inside a claim) is refused as RESPONSE_REFUSED_PROBABILITY, not only as an unknown key (test added after the mutation probe).
- Known limits left open (recorded, not fixed): grounding is by observation kind and state, not value; stability compares label sets only; the injection patterns are heuristic; `unshare -n` isolates the network, not the filesystem; the meter cap is per meter lifetime.

## Artifacts (sha256, first 16 hex; full digests in PHASE_14_RESULTS.json)

| Path | sha256 |
|---|---|
| memelab/predictive/behavioral.py | c2da788fd7c0b348 |
| tests/test_predictive_behavioral.py | 8c693ff4a0f106a9 |
| tests/test_predictive_phase14_outputs.py | a1e5f15012655928 |
| tests/fixtures/predictive/behavioral_mock.py | 30af30241d56e0b1 |
| tools/release_audit.py | 0d10aec3f8ccf1ad |
| behavioral/SCENARIO_SCHEMA.json | ddd010355a20c444 |
| behavioral/SEEDS_DEV.jsonl | a0c6181775030130 |
| behavioral/RULE_SCENARIOS_DEV.jsonl | 1e4ad4bb0527263c |
| behavioral/RULE_COUNTS.json | 0fe08f3050acc424 |
| behavioral/MOCK_GRID_RUNS.json | 34f9906d0b5c715b |
| behavioral/P30_MATRIX.csv | b928fbb073e6e743 |
| behavioral/COST_CAP.json | 8cff7d08921ac22c |
| behavioral/MIROFISH_PROBE.json | cb17b844017d54ec |
| behavioral/CORE_UNAFFECTED.json | dea41481ebbdcb66 |
| evidence/run_log.json | 27a7a1776c0e8503 |
| evidence/mutation_behavioral.json | ee4a0c0bd412e19b |
| ACCEPTANCE_CHECKLIST.md | 7920cdc0129eff83 |

## Skeptic

Packet: `SKEPTIC_PACKET.md`. The independent review and its counterexample are folded in by the repair pass.

## Post-commit at the records commit `bf06b87`

| Command | Exit | Result |
|---|---|---|
| `python -m pytest tests -q -p no:cacheprovider` (from 23:23:05Z) | 1 | `1 failed, 1772 passed, 1 skipped, 1 warning in 203.75s`, only the known failure; stray `data/reports/20261026_2323_BRETT_0x532f.md` removed by hand |
| `python -m memelab social guard` | 0 | 0 violations |
| `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | 0 | `"problems": []` |
| `python tools/release_audit.py --history` on a single-branch clone | 0 | "Needs action: no." |
| `git status --short` | 0 | clean after the post-commit record |

## Repair pass 2 (after the independent skeptic, PI-D-076)

Review: `skeptic/PHASE_14_SKEPTIC.md` (at `58bee5d`; 5 MATERIAL, 6 minor, CX-S14) with its scripts copied beside it; `skeptic/p14_attacks_rp2.py` is the skeptic's attack script with one change (the publication baseline is defined before A2, because its A3 branch raised NameError once A2 is refused). Every finding was verified against the first-pass code before any change (`skeptic/rp2_recheck.py`, `skeptic/rp2_recheck.json`):

| Finding | First-pass code `c59c494` | Repaired code `69a3584` | Test that fails on the first pass |
|---|---|---|---|
| M1 capped run AVAILABLE | A1 NOT CAUGHT (llm_actions 16, AVAILABLE); MiroFish low cap had 3 actions | llm_actions 0 unless SIMULATION_RAN; AVAILABLE exactly when RAN on all 45 matrix rows | `test_m1_no_capped_refused_or_tripped_run_is_ever_available`, `test_a_meter_block_at_its_cap_refuses_the_run` |
| M2 meter not a ceiling | `n` 8 with stream: 42 calls, bill 6.90 times the cap; `n` 64: 55.07 times | 0 forwarded for every multiplying parameter; usage metered per call; stop on missing usage | `test_m2_*` (12 cases) |
| M3 agreement as multiplicity | A2 NOT CAUGHT (8 and 2 entries published) | RESPONSE_REFUSED_REPEATED_LABEL; validator and projection refuse repeated labels | `test_m3_repeated_labels_never_reach_a_document` |
| M4 subprocess egress | E3 and E4 delivered the 2,192-byte request to 10.99.0.1 | SCRIPT_EXIT_1, nothing received; children in their own namespace | `test_every_subprocess_runs_in_its_own_network_namespace`, `test_a_subprocess_cannot_reach_a_listener_of_the_parent` |
| M5 and CX-S14 | STABLE, both opposite hypotheses published | UNSTABLE, MONITOR_REVERSED, one hypothesis | `test_cx_s14_a_seed_reversed_monitor_is_unstable`, `test_stability_rules_directly` |
| m1 P28 shapes | slash, month-name, wording, outcome name passed | refused (POST_DECISION_DATE, POST_DECISION_WORDING, POST_DECISION_FIELD) | `test_minor_m1_m2_wider_seed_checks` |
| m2 P41 shapes | four wordings and unicode tricks passed | refused after NFKC and invisible-character removal, seeds and responses | same, `test_minor_m4_response_size_cap_and_normalized_response_scan` |
| m3 free strings | A3 NOT CAUGHT | refused (vocabularies, claim keys) | `test_minor_m3_flags_reasons_and_claim_keys_come_from_the_vocabulary` |
| m4 test gaps | X2, X4, X5 survived the suite | caught (mutations G17, P11, P12); X3 equivalent | mutation probe |
| m5 meter details | last-entry usage; re-serialized body uncharged | per-entry usage; larger body charged | `test_m2_charge_covers_the_forwarded_body_not_only_the_received_one` |
| m6 copyleft scope | probes not scanned | probes scanned | `test_new_files_carry_no_copyleft_marker_or_fingerprint` |

Disagreements, recorded: the skeptic's A5 "future unix time as a number value" uses 1790000000 (2026-09-21T14:13:20Z), which is before the decision (2026-10-12T05:00:00Z); accepting it is correct, and a value after the decision is refused. X3 (IP check removed) is equivalent, as the skeptic says.

Commands and results at the repair:

| Command | Exit | Result |
|---|---|---|
| pre-freeze `python -m pytest tests -q -p no:cacheprovider --deselect tests/test_predictive_phase14_outputs.py` | 1 | `1 failed, 1800 passed, 1 skipped, 7 deselected` (known failure only; output tests deselected until the outputs were regenerated) |
| `python -B probes/build_seeds.py <scratch>/rec2` (from 00:15:43Z, 2026-10-27) | 0 | 830 seeds, 0 refused, head `69a3584`, seeds byte-equal to the first pass |
| `python -B probes/run_behavioral.py <scratch>/rec2` (00:15:55Z to 00:17:58Z) | 0 | head `69a3584`, dirty code none, 259 connects all to 127.0.0.1, 0 label calls |
| `python -B probes/mutation_behavioral.py <scratch>/rec2_mutation.json` | 0 | 83 mutations, 83 caught, 0 survivors, 705 s (63 first-pass mutations, fragments updated, plus 20 for the repair) |
| `python -B probes/oracle_schema.py evidence/oracle_jsonschema.json` | 0 | 0 errors on 830 documents |
| `python -B probes/rerun_diff.py <scratch>/rec2 evidence/rerun_rp2_diff.json` | 0 | see below |

What changed in the outputs and why (`evidence/rerun_rp2_diff.json`): `SEEDS_DEV.jsonl` and `CORE_UNAFFECTED.json` byte-equal; `RULE_COUNTS.json` equal in every count and verdict (labels 309, 313, 227, 66; 0 catalyst), different only in creation time and documents digest; `RULE_SCENARIOS_DEV.jsonl` 830 of 830 documents equal after removing the new `cost.llm_actions_observed`, the creation time and the digest, every hypothesis set equal; `P30_MATRIX.csv` 39 to 45 rows (new rows, `subprocess:external_without_netns` replaced by `subprocess:meter_outside_namespace` since every subprocess now runs in a namespace); `MOCK_GRID_RUNS.json` gains MONITOR_REVERSAL grids (UNSTABLE) and the scenario-set counts; `COST_CAP.json` gains the multiplying-parameter and missing-usage cases, the cap run's numbers unchanged (9,709 of 10,000); `MIROFISH_PROBE.json` is a new run of a non-reproducible engine (actions 10 and 9, low cap 3 observed with top-level 0, statuses unchanged); `NETNS_EGRESS.json` new. No status, rule count or verdict changed.

