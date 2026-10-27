# MiroFish behavioral-simulation interface (Phase 14)

Updated after repair pass 2 (PI-D-076, frozen code `69a3584`, recorded run repeated there). The first-pass numbers it replaces are in git at `872578d`.

## Gate

| Item | State |
|---|---|
| MIROFISH_GATE (live use) | **BLOCKED**: no LLM, Zep or other paid spend and no API key is approved (PI-D-005). Also, for any retrospective use: non-deterministic for a fixed seed, and every LLM's pretraining postdates the lab's decisions (P26). |
| Simulator path (`memelab/predictive/behavioral.py` adapters, metering proxy) | **TEST_ONLY**: proved on the lab's mock service, mock LLM and fictional seeds, and on MiroFish's own script with a canned mock LLM; no live LLM exists on this path. The safety items (egress, no probability, seed, stability, failure states, cost) hold under the independent skeptic's attacks after repair pass 2. |
| Rule-based generator `behavioral-rules-1` | Real code run on 830 real point-in-time development seeds; deterministic; **unscored** (Phase 15 scores it). |
| Statistical engine | Unaffected: Phase 13's runner, with the behavioral module blocked from import, writes 24 files: 22 byte-equal to the committed Phase 13 outputs and its two run logs, which differ only in head and time. |

Nothing here is a probability, an accuracy, a score input or a forecast. A simulated agreement is never a likelihood (P27).

## What was rechecked (G3)

- Pin `666ghj/MiroFish` `7657031ac01184afe2cb220f5ee3545573b5e843`; the clone outside the repository is clean at the pin and `git ls-remote` on 2026-10-26 shows upstream HEAD still equal to it.
- Root LICENSE sha256 `8486a10c4393cee1c25392769ddd3b2d6c242d6ec7928e1414efff7dfb2f07ef` (AGPL-3.0). `backend/pyproject.toml:5` requires Python `>=3.11,<3.13`. `backend/app/config.py` `validate()` requires `LLM_API_KEY` and `ZEP_API_KEY` and refuses `ZEP_API_URL`.
- Phase 03 (`phase_03/research/MIROFISH.md`) and Phase 04 (`phase_04/adoption/MIROFISH_FEASIBILITY.md`, ISOLATED_MOCK_ONLY) stand: in-process use, copying and serving are REJECT; the script path is the only route without paid services; the script exits 0 when its LLM is down; same-seed runs differ.

## The boundary

```
lab caller (on demand only)
  |  seed: point-in-time observations of one exact (chain, mint) at the decision     check_seed (P28, P41, P45)
  v
behavioral.preflight: approved true, mode ON_DEMAND_LOCAL, no kill switch, loopback IP literal,
                      engine not paid, bounds, worst-case cost <= cap (0 calls when refused)
  |
  +-- ServiceAdapter  -> http://127.0.0.1:<port>/v1/scenario   (lab-written engines only; an external engine is refused)
  +-- SubprocessAdapter -> /usr/bin/unshare -n <argv>, always  (environment built from scratch; process group killed on timeout)
          |  inside the namespace: lo only
          +-- mirofish_runner.py -> MiroFish run_reddit_simulation.py (unmodified, its own Python 3.12 venv)
                 LLM calls -> behavioral.LLMMeter (127.0.0.1) -> mock LLM (127.0.0.1)
  |
  v
code_response: vocabulary codes only, one hypothesis per label, refs must be seed observations, no number but counts, no injected text
  v
scenario document memelab.predictive.behavioral_scenario/1 (fictional)  ->  forecast_entries (strings only)
```

- No MiroFish file is imported, copied or modified; the runner writes MiroFish's config and fictional profiles to a temporary directory and reads the SQLite trace MiroFish writes. The P31 copyleft gate (`tests/test_predictive_runtime.py::test_p31_*`, winnowed fingerprints) passes on the tree with the new files, and `tests/test_predictive_behavioral.py::test_new_files_carry_no_copyleft_marker_or_fingerprint` checks them directly.
- Egress: only `http://127.0.0.1:<port>` and `http://[::1]:<port>` exactly (host names including `localhost`, other IPs, `::ffff:127.0.0.1`, `127.1`, integer hosts, userinfo, https, queries and non-canonical ports are refused before a socket opens). `http.client` is used directly, so no proxy variable and no redirect is followed. Every subprocess engine runs inside `unshare -n`, whatever kind it declares (repair M4: in the first pass a child declared MOCK_SIMULATOR could post the request to a non-loopback address; `NETNS_EGRESS.json` and two suite tests now show a child in its own namespace reaching nothing, with a positive control from the parent). The repeated run's audit hook saw 259 connects, all to 127.0.0.1.
- Keys: the lab code reads no environment variable. The subprocess gets PATH, HOME (its temporary directory), LANG, PYTHONHASHSEED and the caller's `extra_env`; a key-like name is accepted only with the literal `mock-not-a-key`, and a URL value only when it is a loopback literal. A planted parent `LLM_API_KEY` never reaches the child (test).
- On demand only: `mode` must be `ON_DEMAND_LOCAL`; `PER_OPPORTUNITY`, `SCHEDULED` or a missing mode is NOT_SUPPORTED. No other module imports `behavioral.py` (AST test), so nothing calls it per opportunity.

## The scenario document (no probability)

Schema `SCENARIO_SCHEMA.json` (structure) plus `behavioral.validate_scenario` (rules). Every document: `kind` BEHAVIORAL_HYPOTHESIS_NOT_A_FORECAST, `fictional` true and a fixed notice; the subject (exact mint, snapshot sha256, decision time); the seed reference (seed sha256, cutoff equal to the decision, observation ids, kinds and states, no observation text); the engine (name, mode, pin, model id, declared training cutoff, instruction template sha256, run seeds, persona sets); hypotheses with a vocabulary label, named assumptions (OBSERVED_FACT citing seed observations, SYNTHETIC_PERSONA_BEHAVIOR, SYNTHETIC_SPECULATION), source refs, a falsifiable monitor whose window the adapter sets from the decision time (a registered target with EVENT or NO_EVENT, CATALYST_VERIFIED_BY_WINDOW_END, or ATTENTION_TREND_AT_NEXT_DECISION) and `synthetic` true; stability; contamination flags recomputed from the engine; cost; provenance (run ids, response and trace sha256); refused-claim counts; `doc_sha256`.

Refused anywhere in a document: a key matching the Phase 13 pattern (`prob|likel|confid|share|vote|agree|pct|percent|odds|chance|consensus|certain`), a float outside `cost.est_cost_usd`, `cost.cap_usd`, `cost.wall_s`, an int outside the listed counts. Refused in a response: any probability-like key, any float, any int other than `llm_actions`, `llm_calls` and the meter's integer counts, codes with digits or outside the vocabulary (CX-14: "8 of 10 agents" as a code), a repeated label (repair M3: 8 and 2 same-label hypotheses would have encoded 80 percent), injected instructions, secrets or URLs (matched after NFKC normalization and removal of invisible characters). Reasons, stability flags and refused-claim keys come from fixed vocabularies (repair m3). The forecast projection carries strings only and leaves `abstention.validate_publication`'s result unchanged on a real Phase 13 ABSTAIN document; `calibration.build_card` refuses a behavioral source; `abstention.evaluate` treats behavioral inputs as RESTRICTED_SOURCE (Phase 13).

## Seeds and responses (P28, P41, P45, identity)

- `check_seed` refuses: an inexact mint; an observation without availability, source ref or a sha256 matching its content; anything available after the decision (no tolerance); outcome-like keys or names (`label`, `outcome`, `matur`, `realiz`, `future`, `peak`, `max_price`, `drawdown`, `pnl`, `touch`, `ath` and others); ISO, slash and month-name dates, bare dates and unix times in seconds or milliseconds after the decision, in strings or as numbers; after-the-fact wording ("the next day", "days later", "rugged"; POST_DECISION_WORDING); injection, secret and URL patterns; observations derived from a behavioral document (no generated rumor feeds back as observed news); over 50 observations or a quote over 1,000 characters. Recorded run: all 830 real development seeds pass; one real seed with an observation one second after the decision, with a quoted post dated after it, or with a behavioral-derived observation is refused (SEED_REFUSED, no hypothesis).
- The request keeps a fixed instruction template (sha256 `6109e668...`, pinned) apart from `quoted_evidence` (each item `role: data`) and fictional persona archetypes made by the lab.
- The response coder refuses a catalyst label without a CATALYST_EVENT observation (CATALYST_FOLLOW_THROUGH needs a VERIFIED one; UNGROUNDED_CATALYST, P45) and any label whose refs are not seed observations of the kind it needs. WALLET_CONTROL and IDENTITY_LINK claims are dropped and counted; INSIDER_INTENT survives only as a counted SYNTHETIC_SPECULATION code.
- Limit, stated plainly: grounding is checked by observation kind and state, not by value (a hypothesis may cite a reading that does not support it), and the date, wording and injection patterns are heuristics even after repair m1 and m2. The hard boundary is that nothing but vocabulary codes leaves a response, one per label.

## Failure states (P30), from `P30_MATRIX.csv` (45 cases)

Every case below ends SIMULATION_NOT_AVAILABLE, NOT_SUPPORTED or SEED_REFUSED with a named reason, `runtime.simulation_state` agrees on every row (repair M1: a run that is not SIMULATION_RAN carries top-level `llm_actions` 0, the observed count is `cost.llm_actions_observed`; in the first pass a capped run with actions was AVAILABLE), the abstain reason is none, so the statistical forecast is unaffected, and every document validates:

| Group | Cases and reasons |
|---|---|
| gates (0 service requests) | NOT_APPROVED (absent, `"true"` string), MODE_NOT_ON_DEMAND_LOCAL (SCHEDULED, PER_OPPORTUNITY), KILL_SWITCH, PAID_ENGINE_NOT_APPROVED, EGRESS_NOT_APPROVED (localhost name, public IP, https, userinfo) |
| service | KEY_MISSING (401, 403), QUOTA_EXHAUSTED (402, 429), SERVICE_ERROR (500, 3 attempts), BAD_RESPONSE (418, non-JSON, count codes, digits in a claim, a response over 256 KB), NO_LLM_ACTIONS (200 with zero actions), RESPONSE_REFUSED_PROBABILITY (likelihood key, nested fraction), RESPONSE_REFUSED_INJECTION (instruction text, URL, fullwidth URL), RESPONSE_REFUSED_REPEATED_LABEL, UNGROUNDED_CATALYST, COST_CAP_REACHED (meter block at its cap), CIRCUIT_OPEN, SEED_REFUSED, SERVICE_DOWN (3 attempts), TIMEOUT (3 attempts) |
| subprocess | SCRIPT_EXIT_3, NO_OUTPUT, NO_LLM_ACTIONS, BAD_RESPONSE, TIMEOUT_KILLED, KEY_NOT_APPROVED, EGRESS_NOT_APPROVED, METER_OUTSIDE_NAMESPACE |

Three cases run (service STABLE, service WALLET_CLAIM with both claims dropped and counted, subprocess STABLE). Tests add an adapter that raises SystemExit.

## Cost cap and breakers (P48), from `COST_CAP.json` and PI-D-073

- Default `max_cost_usd` is 0: no spend is approved. Before any call the adapter refuses when the worst case passes the cap: calls = agents x rounds + agents + 2, each at the per-call ceiling (64 KB body bytes plus 64 tokens at the input price, max_tokens 512 at the output price). Recorded: worst case 1,465,728 micro-USD at fictional prices against cap 0, COST_CAP_REACHED, 0 service requests.
- `LLMMeter` (loopback only) charges each forwarded call its pre-call ceiling on the call's body bytes (a byte-level BPE token covers at least one byte, so Chinese prompts are not undercounted; characters / 4 would have been), so the charge cannot pass the cap: recorded 9,709 of 10,000 micro-USD, 7 calls forwarded, the rest refused with 429, and a second run made no upstream call. It forces max_tokens to 512 (every upstream call saw 512), refuses prompts over 16,000 characters or bodies over 64 KB (413), stops at 200 calls (429 after the cap in the test with 3), opens its breaker after 5 upstream failures (500 x5 then 503 x2, upstream saw 5), honours a kill switch (503), refuses everything on a non-finite or negative setting, and stops forwarding if an upstream ever reports more tokens than were charged. Charges count failed forwards too (conservative).
- Repair M2 and m5: the first-pass meter forwarded `n` and `stream`, so with an upstream that honours them the bill reached 6.9 and 55 times the cap (skeptic, `skeptic/rp2_recheck.json`). The meter now refuses `n` other than 1, `stream` other than false and any key outside a fixed allowlist (400, nothing forwarded; recorded: `n` 8, `n` 8 with stream, `n` 64 with stream, stream, `best_of`, `logprobs` all 400, plain and `n` 1 with stream false 200, upstream saw 2 calls), meters the upstream's usage per call on that call's ledger entry (21 micro-USD used against 9,709 charged in the cap run), stops forwarding on a 200 without integer usage (200, 503, 503; upstream saw 1) or usage above the charge, and charges the larger of the received and forwarded body. MiroFish's own calls all pass the allowlist (every ledger entry FORWARDED).
- Limit: the meter's cap holds for the meter's lifetime (one grid); a live route would also need a persistent spend ledger across runs.

## Stability (P29), from `MOCK_GRID_RUNS.json`

Frozen grid: run seeds 101, 202, 303 by persona sets 1 and 2, a repeat of the first cell, one run per observation kind removed, one with no evidence (10 runs here). STABLE only when all six grid runs and the repeat give the identical scenario set, each scenario being a label with its monitor metric and expectation; never from a share of runs (repair M5: the first pass compared labels only, so CX-S14 below was STABLE).

| Mock mode | Fictional seed | Real development seed |
|---|---|---|
| STABLE | STABLE | STABLE |
| SEED_SENSITIVE | UNSTABLE (SEED_SENSITIVE) | UNSTABLE (SEED_SENSITIVE) |
| PERSONA_SENSITIVE | UNSTABLE (PERSONA_SENSITIVE) | UNSTABLE (PERSONA_SENSITIVE) |
| NONREPRODUCIBLE | UNSTABLE (NOT_REPRODUCIBLE, SEED_SENSITIVE, PERSONA_SENSITIVE) | same |
| EVIDENCE_BLIND | UNSTABLE (NOT_SOURCE_GROUNDED) | same |
| MONITOR_REVERSAL (CX-S14) | UNSTABLE (MONITOR_REVERSED, SEED_SENSITIVE) | same |

DEGRADED_SOURCE_CHANGES (labels change when the attention readings are removed) is reported, not a failure. An UNSTABLE document keeps one hypothesis per label (the first in grid order) with reason UNSTABLE_EXPLORATORY and no dominant scenario. CX-S14 (the skeptic's counterexample): a simulator keeps ORGANIC_ATTENTION_CONTINUATION in every cell but expects EVENT for seeds 101 and 303 and NO_EVENT for 202; the first-pass code published it as STABLE with both opposite hypotheses, the repaired code gives UNSTABLE with MONITOR_REVERSED (`tests/test_predictive_behavioral.py::test_cx_s14_a_seed_reversed_monitor_is_unstable`, `skeptic/cx14_monitor_reversal.py`). Limit: assumptions are not compared.

## MiroFish through the boundary (G17), from `MIROFISH_PROBE.json`

MiroFish's unmodified script, 4 fictional agents, 4 rounds, inside `unshare -n`, through the meter to the Phase 03 canned mock LLM (no model), fictional prices of 0.001 and 0.002 USD per 1,000 input and output tokens, config cap 5.0 USD:

| Run | Result | LLM actions | Metered calls (refused) | Charged USD | Wall s |
|---|---|---|---|---|---|
| meter cap 1.0 | SIMULATION_RAN, NOT_CODABLE | 10 | 11 (0) | 0.126165 | 10.6 |
| same seed, repeat | SIMULATION_RAN, NOT_CODABLE | 9 | 9 (0) | 0.096776 | 10.6 |
| meter cap 0.03 | SIMULATION_NOT_AVAILABLE, COST_CAP_REACHED; top-level llm_actions 0 | 3 observed | 3 (96) | 0.027716 | 45.3 |
| LLM down | SIMULATION_NOT_AVAILABLE, NO_LLM_ACTIONS (script exit 0, meter breaker open) | 0 | 5 (31) | 0.046194 | 22.0 |
| config cap 0.05 (worst case 1.47) | SIMULATION_NOT_AVAILABLE, COST_CAP_REACHED, never started | 0 | 0 | 0 | 0 |

- The same seed gave different traces again (first pass 8 and 9 actions, repeated run 10 and 9): MiroFish is not reproducible, so any MiroFish scenario would be UNSTABLE under rule 14 without many more repetitions.
- NOT_CODABLE: the script path writes free-text posts and no structured hypothesis; the lab does not turn free text into codes. Coding MiroFish output needs its ReportAgent (Zep and LLM, paid) or blind human or rule coders (Phase 15's protocol).
- Every MiroFish document carries LLM_PRETRAINING_CONTAMINATION_RISK and EXPLORATORY_NOT_AS_OF (no training cutoff declared).

## behavioral-rules-1 on real seeds (G16), from `RULE_COUNTS.json`

830 development seeds (decisions before 2026-10-17T00:00Z) from `socialcat.socialcat_as_of` with each decision's own export (`probes/build_seeds.py`, `probes/seed_convert.py`), no label read (`labels.training_labels` replaced by a raising function; 0 calls), no socket. 830 RULES_RAN; hypotheses ATTENTION_EXHAUSTION 309, MANUFACTURED_ATTENTION_DUMP 313 (85 together with exhaustion), ORGANIC_ATTENTION_CONTINUATION 66, NO_GROUNDED_SCENARIO 227; 0 catalyst hypotheses because no seed holds a catalyst event (CATALYST_TABLES_NOT_EXPORTED), so P45 holds on real data. Two runs byte-equal; jsonschema 0 errors on all 830 documents; the repeated run gives the same 830 hypothesis sets (documents differ only by the new `cost.llm_actions_observed`, the creation time and the digest, `evidence/rerun_rp2_diff.json`); nothing scored, no outcome read. These counts say how often each rule fires, not whether any scenario happened.

## What approval would have to include before any live run

1. Elving's explicit LLM budget, entered as `max_cost_usd`, with a persistent spend ledger across runs (the meter's cap is per lifetime).
2. A code change with change control that opens one named upstream for the meter only; the simulator itself stays in the network namespace.
3. An LLM whose training cutoff is declared and precedes every evaluated event (P26), or a prospective-only design.
4. Filesystem isolation for the engine (a separate container or user with only the request mounted): `unshare -n` blocks the network but not reads of local files.
5. A way to code free text into the vocabulary (blind coders or a pre-registered rule coder), and enough repetitions for the stability grid to mean anything.

## For Phase 15

- Comparator A (predeclared rule-based narratives): `behavioral.rule_scenarios`, available now, with monitors on the registered targets.
- Comparator B (evidence-only LLM) and D (MiroFish): BLOCKED without approved spend; the adapters and the meter are ready for a mock-only protocol test.
- Comparator C (calibrated statistical classifier): none is calibrated (Phase 13, UNCALIBRATED everywhere).
- Catalyst events: none exported, so a catalyst event set from the lab's own data has N = 0; the attention-proxy scenarios are the only real seeds. Expect INSUFFICIENT_VALIDATION or BLOCKED for the simulation question unless new data or approvals arrive.
