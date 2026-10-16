# Independent M00 verification — BLOCKED

> **Current Phase 03 substitute review, 2026-10-15:** recovery package hashes and report/later-test continuity verified; newly reconstructed A–E runs now include D/E. Historical original full inputs/executions remain unrecovered. **M00 BLOCKED pending explicit reviewed acceptance of the substitute evidence; M01 unauthorized.** See [current decision and concrete reviewer action](M00_PHASE03_REPLICATION_REVIEW.md). Earlier dated statements retain their historical scope.


> **Current archive follow-up, 2026-10-15:** four original ZIPs and 50 member files recovered; 43 embedded hashes and all 105 original requirement texts verified. Original Phase 04/05 bytes are now available. OPS-001–010 are primary labels in the recovered Phase 05 findings, correcting the earlier secondary-only attribution. Phase 03 A–E executable inputs/scripts/raw outputs remain absent; **M00 BLOCKED, M01 unauthorized**. See [current checklist and next steps](M00_ARCHIVE_RECOVERY_VERIFICATION.md). Earlier dated statements below describe their historical review state.


**Review date:** 2026-10-14 America/New_York; executions on 2026-10-15 UTC. **Package:** M00/R-00 evidence recovery only. **Decision:** **BLOCKED — acceptance withheld. M01 must not start.** No application defect is resolved by this review.

This review was conducted in a fresh Codex chat separate from the recovery implementation. Source passages and code were read directly, crosswalk mappings were selected independently, new counterexamples were designed against the pinned implementation, and existing suites ran in disposable clean checkouts. This is an AI-session review record, not human approval or a cryptographically authenticated reviewer signature. Supporting evidence is incomplete, so no independent approval is certified.

## Immutable scope

| Role | Commit |
|---|---|
| Audited application | `698f73b854567ce60b56ce275b5ab6822a9d5f60` |
| Audit publication / PR #2 base | `b4c4216b9391227be5fdfe7cfe20b60e32d9e8f6` (`audit/social-intelligence-phase06`) |
| Recovery reviewed / PR #2 head | `3b434e1dcc59290d993a638ca615f61b929189bc` (`remediation/social-intelligence-m00`) |
| Optional comparison, not substituted for application | `3f27fc788f9ab88286b8041355e5445fdfdf012c` |
| Observed current `main` | `45a28eedc942220d245d8de8707fcb8f4d713da7`; moved since the audit |

Verification changes are on `verification/social-intelligence-m00-independent`, based on the recovery head, for a separate draft PR into the recovery branch. PR #2 remains unmerged. The original seven missing audit-publication inputs were independently confirmed absent at `b4c4216`; Phase 06 was present. Nothing under `sources/` in the ChatGPT project was modified.

## Acceptance checklist

| Check | Result | Evidence / qualification |
|---|---|---|
| Eight primary documents plus two preserved findings snapshots exist and match manifest bytes | PASS for recovered-copy integrity | `evidence/independent_m00/results/independent-integrity.json`: 10/10 hashes and byte counts |
| Four original uploads independently match recovered files | PASS | Original attachment bytes available from the referenced remediation chat; hashes recomputed separately from the manifest |
| All eight inputs authenticated as original source bytes | BLOCKED | Phase 04/05 are indexed copies. Original Library-byte comparison for 00/matrix/01 is also unavailable; no stronger provenance inferred. Phase 06 equals its original Git publication. |
| Original requirements/source/probe/log archive complete | BLOCKED | `M00_MISSING_EVIDENCE.md`; original staged prompt and Phase 00/01/03/04/05 execution artifacts remain unavailable |
| 67 AUD/ARCH/ADV/OPS IDs mapped to source evidence and precise code | PASS for traceability, not universal runtime confirmation | New `M00_INDEPENDENT_CROSSWALK.md/json`; 83 unique code spans checked against immutable Git objects; all IDs remain OPEN |
| OPS-001–010 independently reconciled with Phase 05 | PASS with qualifications | Each mapped to exact operating-dimension/scenario/backlog/acceptance lines; IDs and severity ratings are secondary indexing conventions |
| Duplicates, overlap, evidence grades and severity differences retained | PASS | AUD-032 reconfirms AUD-002; ARCH/OPS/ADV overlap listed, no 67-incident claim; methodological/design risks not upgraded to incidents |
| Representative high-impact defects reproduced offline | PASS as defect confirmation | Nine acceptance failures and one positive-control pass on each pinned/recovery checkout; exact observations and logs archived |
| M00 integrity tests and negative mutations | PASS | Seven focused tests; byte mutation and missing report both rejected with exit 1; strict gate exit 2 |
| Full available suites completed / baseline preserved | EXECUTED, RED BASELINE | Baseline 651 pass/1 fail; recovery 658 pass/1 fail; both exit 1. Same catalyst assertion, no new full-suite failure observed. |
| Prior ingest logging failure resolved | NOT ESTABLISHED | Full suites, isolated test, selected ordering and preconfigured-CLI-logger probe pass here. Original failing environment/order/logs absent; do not silently close. |
| No M00 application/data/schema change | PASS | Original M00 diff has 23 audit/control/test/tool files; zero changes to `memelab`, `bridge`, `data`, `state`, `inbox`; those paths also identical to pinned application |
| No new secrets/raw private social content found | PASS within reviewed/scanned scope | Existing content guard + release scan, manual review of changed audit prose; new fixtures invented; public execution logs replace machine-specific paths only |
| Independent acceptance / next package authorized | BLOCKED | No acceptance approval; source fidelity and historical probe evidence remain incomplete. No M01 work performed. |

## Document integrity and source fidelity

The full digests/byte counts are recorded in `independent-integrity.json`. The independently available originals yielded:

| Original upload | SHA-256 |
|---|---|
| Phase 02 architecture report | `0584201710ce79b47e00c9e05547df2eefda4c9756e5211e92de4e4d2fbb24de` |
| Phase 02 findings snapshot | `694dd5e52acc6ac4074c010363acc9a283f9f2c06a5106247de89c149d78fc8d` |
| Phase 03 research-validity report | `06cd96136950a1bcebe03a6fcd8cf92ca68d1d82b6a72385b54d93112d203322` |
| Phase 03 findings snapshot | `4a4a18c1462c8047eb03f86f6a67a49984ebd6b9ef5c6963f3f47b1493192964` |

All four match both uploaded bytes and committed recovered files. Preserved source files are unchanged. For the indexed Phase 04/05 reports, a matching hash proves only that this recovered copy stayed unchanged. It cannot prove equality to an unavailable original. Phase 03's reservation of AUD-018–023 reflects its author's earlier missing Phase 02 file, not a contradiction in today's restored inventory. Phase 05's architecture count of 12 conflicts with the actual Phase 02 table of 15; the independent map retains all 15 without rewriting the original.

A fresh deterministic `git archive --format=tar 698f73b...` is 32,040,960 bytes, SHA-256 `2066f6f2dbef5a50f55d6333fbce44fc9554b1ea1a79103bc44c3c11de27b9a8`; Git tree `7f7a408e116db0827722e5c23a749f842dde6702`. `pinned-source-snapshot.json` archives hashes of all 360 tracked files. The source remains recoverable by immutable Git SHA. This fresh source digest does not recover the earlier audit ZIP or authenticate its absent logs.

## Independent representative defect probes

`test_pinned_acceptance.py` imports the actual package from the checkout being tested. The existing narrative builder supplies schema-valid invented records only; expected causal and provenance rules are asserted independently. No production code, assertions or clock were changed. Tests are intentionally red on defective code, with no `xfail` or bypass. Baseline and recovery produce identical observations in `probe-observations.json`.

| Finding / invented input | Required behavior | Actual result on both refs |
|---|---|---|
| AUD-001: cutoff 1791849600, extraction 1791936000 | Later interpretation absent from past snapshot | One cluster included |
| AUD-015: explicit run cutoff 1791849600, requested as-of 1791770400 | Same historical eligibility as default selection | Explicit selection returns one cluster; default returns none |
| AUD-024: hourly candle t=0, open 10, high 100; decision 1800 | No claim of executing the earlier open at a later decision | OPEN returns price 10, candle_t 0, fill_t 1800 |
| AUD-024: same candle, adverse rule, as-of 1800 | Uncompleted high unavailable | Price 100 accepted before candle end 3600 |
| AUD-024: horizon exit at 3000 | No timed exit priced at earlier open | Price 10, candle_t 0, reported exit t 3000 |
| AUD-025: transaction 1000, sole mark at 1100, tolerance 200 | Future mark unavailable for contemporaneous valuation | $100 returned as OBSERVED; causal `latest_mid` control returns none |
| AUD-004: fixture observation and fixture candle series | Preserve fixture lineage | One claim + one series exported with is_fixture=false; no false numerical alpha-score claim made |
| AUD-002/AUD-032: extraction 1791936000 | Export availability no earlier than extraction | available_at=1791766830 from original observation; current-wallet-link part remains static review |
| AUD-033: generation 1000, fact as_of 900, fetched_at 1100 | Exclude late-fetched context | Price 10 included; facts_after_generation_excluded=0 |
| Positive controls | Valid boundary/prior mark still usable | t=0 fill uses t=0 open; t=900 wallet mark usable at t=1000 |

These invented cases demonstrate mechanics, not financial loss, bias magnitude, live exploitation, source skill or predictive alpha. AUD-029's original quotation/aggregation claim is source-confirmed here, not newly reproduced; architecture concurrency/load, adversarial C microprobes and Phase 05 modeled operations retain their original limits.

## Execution ledger and resource limits

Python 3.12.14, pytest 9.1.1, numpy 2.4.2, macOS arm64; dependencies installed into a disposable virtual environment. Test environments were reconstructed without inherited credentials; Python audit hooks refused socket connection/DNS calls in child processes. All three new network logs contain zero events. This is Python-level control, not OS-wide packet capture. No paid calls, model/source calls, deliveries, wallet connections or trades were made. Suite timeout 900 seconds; other checks 180 seconds; no additional address-space cap. No test run here was killed or timed out.

| Check | Exact exit | Result / evidence |
|---|---:|---|
| Pinned `python -m pytest tests -q` | 1 | 651 passed, 1 failed; 53.13 s pytest time |
| Recovery `python -m pytest tests -q` | 1 | 658 passed, 1 failed; 51.45 s pytest time |
| Recovery `python -m pytest tests/test_audit_evidence.py -q` | 0 | 7 passed |
| Recovery `python tools/check_audit_evidence.py` | 0 | Integrity clean, BLOCKED; zero is not acceptance |
| Recovery same command with `--require-complete` | 2 | missing=[]; independent_review=PENDING at reviewed commit |
| Append one byte / delete report in disposable archive copies | 1 / 1 | Integrity rejects tamper and false RECOVERED claim |
| Independent acceptance tests, baseline / recovery | 1 / 1 | Each 9 failed, 1 passed; all nine failures match intended defects, no setup errors |
| Content guard, baseline / recovery | 0 / 0 | Zero violations |
| Release audit, baseline | 0 | Completed |
| Release audit, recovery, initial invocation | 1 | Incomplete: worktree could not materialize the missing pinned Git object in shallow recovery clone; FileNotFoundError. Not a clean scan or application regression. |
| Release audit, recovery, after fetching exact pinned object locally | 0 | Completed; original failed log retained, no scanner rule weakened |
| Release E2E, recovery | 0 | 45/45 expected stage exits, zero network attempts, tracked DB identical; fixture compatibility only |
| Ingest logging isolated / chosen CLI-test ordering / CLI logger preconfigured before pytest | 0 / 0 / 0 | 1 / 2 / 1 tests passed. Prior additional failure not reproduced; exact prior environment still unknown. |
| Final publication-tree release scan | 1 | 110 trading-keyword self-matches in two archived scanner Markdown reports; credentials=[]; manually reviewed as rule-name echoes, no new execution code; scanner unchanged |
| New reference verifier | 0 | 10 document hashes, 67 IDs, 83 code spans, 105 unique requirement IDs |

Both full suites fail `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial` at line 44: expected CONFIRMED, actual REPORTED. Both leave an untracked BRETT Markdown report; tracked diffs are empty and the tracked DB SHA-256 remains `068287c0d7e454361eb42f54b2f90e49e4075ae3a962a3c57867165ab6a679ca`. The reports remain only in disposable checkouts, not this verification commit. This updates the previous incomplete exit-137 evidence with completed current runs without rewriting history or claiming AUD-011 fixed.

The prior logger failure cannot be diagnosed conclusively from a summary. Source inspection found global CLI logger configuration (`cli.py:44–51`), but even explicitly preconfiguring it did not reproduce the failure with this pytest/runtime. Treat test-order/environment interference as a hypothesis, not an established root cause or repaired finding. The original raw failing logs/runtime are still needed.

The initial remote clone attempt timed out before tests; work continued locally. That access failure is not an incomplete test suite. Logs under `evidence/independent_m00/results/` preserve statuses and outputs with machine paths replaced; `publication-redactions.json` records raw versus published hashes. Raw local originals are retained outside Git. No failure marker or assertion was removed. Captured output retains blank-line whitespace; the optional diff whitespace check reports those log lines, not application source changes.

## Requirements and reconciliation decision

The recovered matrix contains 105 unique paragraphs across 22 prompts, with negative cases for malformed data, missing credentials, temporal leakage, fixture labeling, non-executable outcomes and interrupted processing. The new map associates findings with actual requirement IDs. Prompt 03/04/19–21 explicitly permit truthful unavailable/live-disabled states and fixture evidence when access is missing: absence of live credentials is not automatically a violation of those delivery gates. Full-green, temporal correctness and source-to-claim requirements remain distinct unmet claims. Phase 15 asks for disabled schedule templates, so disabled defaults are compliant with that narrow requirement; OPS-001 instead concerns the broader unattended-service goal. Original requirement-text fidelity remains blocked by the absent staged prompt source.

Original grades are preserved. AUD-032 is the AUD-002 family; ARCH rows aggregate/extend AUD paths; many ADV/OPS labels qualify the same risks. Severity differences (for example AUD-020 High versus ARCH-007 Medium–High, and conditional ADV-009 High versus AUD-009 Medium) remain explicit. P0 roadmap priority does not silently rewrite original severity. No unique-independent-defect count or incident frequency is inferred from 67 labels.

The original M00 change is audit evidence/tooling only. New work adds review artifacts, offline probes and control-record corrections. Content guards and credential scans found no matching secret/private-content leak in their bounded scope; the final publication-tree release scan nevertheless exits 1 because its own archived Markdown reports echo 110 execution-rule names (two files). `publication-scan-review.json` records that manual disposition; no rule was suppressed and no scan was claimed green for this publication tree; manual review found audit-authored prose and invented examples. Scanners do not authenticate original report rights or comprehensively inspect arbitrary prose; this review does not claim universal absence of secrets.

## Recorded reviewer decision / next action

**Recorded by:** Codex independent M00 verification, fresh chat `01a13d0d-ef33-7770-aa72-1c3b0bfb392a`. **Decision:** BLOCKED; acceptance refused on missing original-source/probe evidence. `independent_review=REJECTED` means this acceptance attempt did not pass, not that all recovered files are invalid. No reviewer approval, finding closure or M01 authorization is asserted.

Recover the artifacts in `M00_MISSING_EVIDENCE.md`, check original-byte fidelity and source/probe discrepancies, and submit an explicit subsequent independent acceptance record. Keep the baseline catalyst and historical logger limitations visible. **Stop at M00.**
