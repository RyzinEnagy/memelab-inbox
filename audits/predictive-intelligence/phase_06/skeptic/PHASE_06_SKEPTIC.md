# Phase 06 independent skeptic review

Reviewer: orchestrator's independent skeptic (PI-D-013), 2026-10-25. Branch `feature/predictive-intelligence` at `121384b` (Phase 06 content `4565e0b` plus a records-only commit). Own clone `/home/claude/pi_orchestration/skeptic_06`; private stores copied to `/tmp/claude-0/sk06/` (dev store only; the sealed store was not opened). No vendor call, no Firecrawl, nothing written in `/home/claude/memelab-inbox` or `/home/claude/bt-wt`. The sealed holdout labels were never decompressed; I flipped bytes only in a throwaway copy.

Verdict: one material finding (test adequacy: the label tests do not pin several frozen rules; the labels themselves are correct), eight minor findings, one new counterexample that nothing catches.

## Scripts (next to this file)

| Script | What it does |
|---|---|
| `p06_independent_labels.py` | independent recomputation of every development and purged label from `phase_06/raw/` (MANIFEST.csv, bodies, `raw/lists/`), `data/read_map.json` and the decision rows of a copy of the dev store; standard library only, does not import `labels.py`, `contract.py`, `decisions.py` or `store.py`; holdout decisions are skipped |
| `p06_independent_out.json` | its output (per-record states and classes, development and purged only) |
| `p06_hand_traces.py` | prints raw candle rows around the decisive points of a decision |
| `p06_gate_attacks.py` | pytest file attacking `labels.training_labels` |
| `p06_own_mutations.py`, `p06_own_mutations.json` | 17 mutations of `labels.py` not in the phase's list |
| `p06_independent_mut.py` | the recomputation with a switch per mutation, to measure real-data impact |
| `p06_counterexample_cx_s06.py` | counterexample CX-S06 |

## Checks

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Label and contract tests | `python -m pytest tests/test_predictive_labels.py tests/test_predictive_contract.py -q -p no:cacheprovider` | exit 0, `107 passed` |
| 2 | Independent recomputation of the development counts | `python3 -I p06_independent_labels.py <clone> <dev store copy> p06_independent_out.json` | T1 136 labelled (34 TARGET_FIRST, 70 INVALIDATION_FIRST, 31 NEITHER, 1 AMBIGUOUS_BAR); T1b 224 (26, 67, 129, 1, NO_TRADES_AFTER_ENTRY 1); T2 131 (DRAWDOWN_50 28, NO_SEVERE_EVENT 103, TRADING_HALT 0). THINNED / MARKET_INACTIVE / VENDOR_OR_ROUTE_GAP / UNVERIFIABLE / PENDING: T1 568/35/39/0/0, T1b 490/40/41/0/0, T2 566/26/37/0/0. Purged rows identical to the report. Eligibility over all Solana non-holdout decisions: ELIGIBLE 714, MARKET_INACTIVE 40, VENDOR_OR_ROUTE_GAP 41, NO_SNAPSHOT_PRICE 47, OUT_OF_SCOPE_CHAIN 583. Every number matches the evidence |
| 3 | Record-level comparison | my records vs the dev store's `predictive_labels` (state, class, P0, P0 candle, first-touch candle) | 1,324 records per target compared, 0 differences |
| 4 | Route strata | my records vs `coverage.json` `development_class_by_route` | identical for all three targets |
| 5 | Hand-checked real traces | `python3 -I p06_hand_traces.py <clone> <store copy> 19ddfd5de2:T1b 8ff1f5a3b3:T1b ...` | 8 traces, below; every hand label equals the code label |
| 6 | Entry and boundary | my script drops candles ending after the request boundary and uses only path candles starting at or after `t_entry` | 503 candles dropped by the boundary rule (PI-D-034), 0 invalid candles; the candle holding `t_entry` is excluded in every hand trace |
| 7 | `token=<mint>` (PI-D-038) | manifest URLs and the development call log | 0 OHLCV rows or calls without `token=<mint>`; 207 of 207 HTTP 200 bodies have `meta.base == mint` |
| 8 | Pacing (development log) | max calls in any 60 s window | 6 by arrival (280 calls), 6 by send time (227 with a send time) |
| 9 | Reads cover the reference window | for every mapped decision: page full (1,000 rows) and earliest kept candle after `decision - 3,900 s` | 0 full pages fail; all 40 MARKET_INACTIVE reads cover the window; the 3 gaps with a short page not reaching back are censored, never labelled |
| 10 | Empty page not evidence (PI-D-039) | decision `2c3f66f43a` (PIT pool, HTTP 200, 0 rows, snapshot 24 h volume $51,392) | VENDOR_OR_ROUTE_GAP, censored, as required |
| 11 | CC-03 timing | `stat` in `/home/claude/memelab-inbox`, `evidence/label_calls.json`, `predictive_label_runs`, `predictive_schema_migrations` | `contract.py` 12:38:53Z, pin 12:39:00Z, first pool list call 12:40:56Z, first OHLCV call 12:57:59Z, label migration 14:25:46Z, the only run row carries fingerprint `4b4aabce...`. Consistent with the claim; see m5 |
| 12 | Holdout independence | my recomputation never opens a holdout read and reproduces every development number | no development statistic depends on sealed data |
| 13 | Seal check | `python -B audits/predictive-intelligence/phase_06/probes/check_seal.py` | exit 0, 99 files, `"problems": []`, seal `d5059bae...` |
| 14 | Seal catches an edit | throwaway copy: flip a byte in a sealed raw file; then also rewrite SEAL.json; then flip a byte in `holdout_labels.jsonl.gz` and rewrite SEAL.json | raw edit: exit 1; raw edit plus rewritten SEAL.json: exit 0 (m4); labels edit plus rewritten SEAL.json: exit 1 (pinned in RESULTS and DECISIONS) |
| 15 | Holdout summarised beyond counts | `grep` of COVERAGE report, coverage tables and `coverage.json` | only state counts per target, line count and hashes; the cross-target invariant check reports "0 violations in the holdout" (a count). See m8 |
| 16 | Training gate attacks | `python -m pytest -q -p no:cacheprovider p06_gate_attacks.py` (from the clone) | 7 passed: the legit path refuses pending, purged and holdout; four gaps shown (m1 to m3) |
| 17 | Phase mutation check | `python -B audits/predictive-intelligence/phase_06/probes/mutation_labels.py /tmp/.../mut.json` | control 0, 25 of 25 caught (reproduced) |
| 18 | New mutations | `python -B p06_own_mutations.py <clone> p06_own_mutations.json` | control 0, **3 of 17 caught** (M1) |
| 19 | Full suite at `121384b` | `MEMELAB_DB=<tmp> python -m pytest tests -q -p no:cacheprovider` | exit 1, `1 failed, 1107 passed in 177.38s`, only `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`; stray `data/reports/20261025_1318_BRETT_0x532f.md` removed; `git status` clean |
| 20 | Content guard | `python -m memelab social guard` | exit 0, `"violations": []` |
| 21 | Release audit | `python tools/release_audit.py --history` | on a single-branch clone of `feature/predictive-intelligence`: exit 0, "Needs action: no." On a full clone: exit 1 because of a blob on another local branch (m7) |

## Hand-checked real traces (raw rows from the committed bodies)

| Decision | Case | Worked by hand | Code |
|---|---|---|---|
| `19ddfd5de2` (FgnSJwFo, PIT) | tie within one candle | decision 10-08 19:28:51Z, entry 19:33:51Z. 19:15 candle ends 19:20, served 19:25, so it is the reference (19:20 candle served 19:30, too late): P0 = 0.000318664, U = 0.000398331, L = 0.000270865. The 19:30 candle holds the entry and is skipped. 19:35 candle: high 0.000400637 >= U and low 0.000213398 <= L | AMBIGUOUS_BAR at 19:35 for T1 and T1b |
| `8ff1f5a3b3` (61cfz6tc, PIT) | NO_TRADES_AFTER_ENTRY with absence evidence | reference 19:00 candle close 2.02151e-06 (post-rug price); 8 rows in the read, none from 19:05 to 01:35; boundary 10-10 19:35 >= ceil(01:33:51); earliest candle 18:35 < entry | T1b NO_TRADES_AFTER_ENTRY |
| `b4ad12fbcd` (PENGU, vendor list) | NEITHER | reference 22:10 candle (end 22:15, served 22:20 <= 22:20:37) close 0.00854895; U 0.01068619, L 0.00726661; path 251 candles, max high 0.0088153, min low 0.0076006; full page reaching back to 10-06 | T1 NEITHER |
| `5c881e3466` (ZCAT, vendor list pool ZEC/ZCAT) | quote-side pool | the vendor list names ZEC base and ZCAT quote; with `token=<mint>` the body's meta shows ZCAT as base and prices near 0.046 (ZCAT), not 1,161 (ZEC). Reference 21:40 candle close 0.0456269; L 0.0387829; first touch 10-08 13:40, low 0.0385365 | T1 INVALIDATION_FIRST at 13:40 |
| `1ec073a4ab` (PANDA, PIT) | DRAWDOWN_50 | reference 19:15 close 0.000177632, half 8.8816e-05; first path low under it 20:05 (7.503e-05) | T2 DRAWDOWN_50 at 20:05 |
| `b5ddb6ad15` (C3AEVqFn, PIT) | rug with an evidenced quiet halt span | reference close 0.0728117; 23:40 low 1.97e-06 (rug); last candle 23:45; 0 candles in [10-09 13:33:51, 10-10 19:33:51), boundary 10-10 19:35, earliest 10-08 03:40 | T1 and T1b INVALIDATION_FIRST and T2 DRAWDOWN_50 at 23:40, halt kept as a flag |
| `e564a679e5` (7JoGUTea, vendor list) | censored gap | no candle ending between 09:21:31 and 10:16:31 (only $1 candles at 10:20 and 10:25, served after the decision); snapshot 24 h volume $3,884 (not below $1,000); route is not PIT, so the quiet-route rule does not apply | VENDOR_OR_ROUTE_GAP |
| `2c3f66f43a` (B3DE8d6C, PIT) | empty page | HTTP 200 with 0 rows; volume $51,392 | VENDOR_OR_ROUTE_GAP |

## Findings

### MATERIAL

**M1. The label tests do not pin several frozen rules; 14 of 17 new mutations of `labels.py` survive.** The phase reports "25 of 25 mutations caught" and marks A3, A7, A9 and A12 as passed "by tests and the mutation check". My own 17 mutations (`p06_own_mutations.py`), run the same way (`pytest tests/test_predictive_labels.py -x`), give 3 caught. Surviving mutations that are not equivalent:

| Mutation | Frozen rule it breaks | Real development records changed (`p06_independent_mut.py`) |
|---|---|---|
| P0 from the reference candle's open, not its close | registry "Reference price P0: close of the newest 5-minute candle" | 25 records; positives T1 34 to 32, T1b 26 to 23, T2 28 to 29 |
| thinning over decisions that are not eligible | CC-01 "thinning runs after eligibility" | 1 (T1b labelled 224 to 223) |
| halt span starts at `t_entry` + 24 h | T2 "from `t_entry` + 18 h to `t_entry` + 48 h" | 0 today |
| halt span by containment instead of overlap | CC-03 rule 3 | 0 today |
| two other pools instead of three | CC-03 rule 2 | 0 today (no development halt) |
| drawdown `<` instead of `<=` | T2 "low <= 0.5 x P0" | 0 today |
| `ceil_grid` becomes floor (needed boundary and absence evidence) | CC-03 rule 1, span end "on the candle grid" | 0 today |
| conservative lens flipped (T1 positive, T2 negative) | registry "conservative lens counts them T1 negative and T2 positive" | 0 labels; the lens column of every censored row |
| training gate admits split PURGED | A12, A15 | 0 rows today |
| T2 to T1 cross-target invariant off | A17 | 0 today |

Equivalent or edge-only survivors (not counted against the phase): the gate's `censored=0` filter (the table CHECK makes it redundant for LABELED rows), pending at equality, purge at equality, absence `<` vs `<=`. Cause of the P0 survivor: `asof_helpers.candle` sets open equal to close by default, so no fixture distinguishes them.

Why material: the labels at `121384b` are correct (checks 2 to 5), so no count changes. But the suite is the only guard on these definitions, the next step edits `labels.py` (48 h revision pass, repair pass), and Phase 07 onward relies on "25 of 25" as proof that the frozen targets are enforced. A change to P0 that moves 25 real labels would pass the suite today. Repair: add tests with open different from close, a candle in [18 h, 24 h) and one overlapping the span start, a fourth other pool that trades, a low exactly at 0.5 P0, a non-eligible decision that would thin an eligible one, an unaligned span end, the lens values, a PURGED LABELED row at the gate, and a T2 drawdown without a T1 touch; add these mutations to `mutation_labels.py`.

### MINOR

**m1. The training gate trusts stored `split` and `label_matures_at`.** `p06_gate_attacks.py`: a row whose `decision_time` is inside the holdout window but whose `split` says DEVELOPMENT is returned; a row whose stored `label_matures_at` is earlier than `contract.label_matures_at(decision_time)` passes an `as_of` before the true maturity in provider mode, because `assert_scorable` is called with `max(as_of, label_observed_at)`. Not reachable through `build` and `record_row` today. Repair: recompute `split_of(target, decision_time)` and `C.label_matures_at` inside the gate and call `assert_scorable` with `as_of`.

**m2. Two gate protections are not on the gate path.** `predictive_labels` has no `use` column, so `runtime.refuse_bakeoff_labels(rows)` can fire only under the test's monkeypatch; `labels.refuse_sealed` is called by nothing except its own test. PI-D-041 item 2 and A15 read as if both guard training. Structural protections (HOLDOUT CHECK, no bake-off rows in the table) do hold.

**m3. A revision that leaves LABELED keeps the original in training.** The gate filters `state='LABELED'` before choosing the newest version, so a revision row stored as UNVERIFIABLE (censored) leaves the original label in use (`test_GAP_revision_to_censored_keeps_original_label`). For T1 and T1b `classify` cannot return that state on a read holding the reference; for T2 it returns NEEDS_OTHER_POOLS, which the CHECK refuses loudly. Low risk, worth one test.

**m4. `check_seal.py` pins only the label file's hash outside the seal.** Editing any other sealed file (raw bodies, read map, call log) and rewriting `SEAL.json` passes (check 14). The seal digest `d5059bae...` is recorded in DECISIONS.md and RESULTS.json but not compared. Git history would still show the edit. Repair: compare `seal_sha256` to the recorded value.

**m5. Pre-registration is consistent but not provable from git.** One commit holds CC-03, the checklist and the labels. `ACCEPTANCE_CHECKLIST.md` was last modified at 14:30:11Z (after the label run at 14:26Z) and its header cites the 12:40:56Z first call, so it was edited after it was "written before any change"; `TARGET_REGISTRY.md` was modified at 14:31Z. The code registry (`contract.py` 12:38:53Z, pin 12:39:00Z) predates every price read, and the only label run row carries the CC-03 fingerprint. Also, Phase 04's bake-off had computed T1 and T1b outcomes on development decisions (PI-D-034), so "before any label was seen" holds for Phase 06's labels only. CC-03 changed 0 development states (UNVERIFIABLE 0, TRADING_HALT 0). Repair for later phases: commit the checklist and any change control before the first data call.

**m6. Identity accepts a quote-side pool whose response ignored `token=<mint>`.** See CX-S06. No real read is affected (207 of 207 bodies show the mint as `meta.base`).

**m7. Release audit on a full clone flags another branch.** `audits/backtesting/research/smoke/etcherfx__sol-trade/output.txt` line 42, `key_material_field`, in commit `2922adb` on the local branch `work/backtesting-collector` (the other agent's worktree), not reachable from `feature/predictive-intelligence`. Outside Phase 06; whoever owns that branch should review it before it is pushed.

**m8. Possible side channel on the seal.** The public evidence gives combined call totals (381 calls, 33 HTTP 429, 1 HTTP 500), the development call log, the sealed body count (93), the holdout response count (81) and the vendor list counts. Together these may bound the number of holdout other-pool reads, which is the number of holdout T2 decisions with an evidenced reference-pool halt and no drawdown. I did not compute it. Repair: report sealed call and body counts only inside `sealed/`.

**Note for Phase 07 (not a defect).** The route is a strong label correlate: T1 positives 3 of 34 on CURRENT_VENDOR_LIST against 31 of 102 on PIT_RECORDED, and 37 of 39 T1 gaps are vendor-list decisions. The vendor-list pool is chosen at label time from today's list, so no feature may use it; stratify as the registry says.

## Counterexample CX-S06 (new): a quote-side response that ignored `token=<mint>`

Wrong but plausible: GeckoTerminal answers a `token=<mint>` request for a pool where the mint is the quote token with its default orientation (meta base = the other token, quote = the mint), for example after a vendor change (PI-D-038 records that the default side has changed before) or a proxy that drops the parameter. `store.gt_identity` returns OK_TOKEN_PARAM because the mint is in the pool and the URL token equals the mint; it never checks that the vendor actually put the mint in `meta.base`. `labels.build` then labels the decision from the other token's prices.

`p06_counterexample_cx_s06.py` builds that body for the real ZEC/ZCAT pool `BTccxx...` (ZCAT quote) with ZEC-level candles: `identity: OK_TOKEN_PARAM ok: True`; T1 and T1b TARGET_FIRST, T2 NO_SEVERE_EVENT, P0 1161.0 against a snapshot price of 0.0456 (ratio 25,461). `CAUGHT by current code: False`. Nothing catches it: no test, no identity rule, no P0 against snapshot-price sanity check. Two cheap checks would: with `token=<mint>`, require `meta.base.address == mint` (true for all 207 real development reads, so it refuses nothing real), and flag a P0 more than, say, 10 times away from the decision's own snapshot price (all 224 real T1b ratios lie in 0.23 to 1.47).
