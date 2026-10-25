# Target schema (Phase 06, label version `labels-1`)

What a Phase 06 label is, how it is computed, and where it is stored. Code: `memelab/predictive/labels.py` (standard library only, flag OFF, imported by no existing module). Targets, barriers, horizons, maturity, eligibility and thinning come unchanged from the registry `memelab/predictive/contract.py` (`TARGETS`, `ACCEPTANCE`; human-readable `phase_01/architecture/TARGET_REGISTRY.md`). Registry fingerprint after change control CC-03 (PI-D-040): `4b4aabce77a5a6f9214c4cfdddf5223f410ed6126410cf4b213b3c80b035f896`, pinned by `tests/test_predictive_contract.py`. Where this document and the code differ, the code is the schema and this document is wrong.

These are price-path labels. A barrier touch is a displayed 5-minute candle high or low on one pool, not a fill at any size. Every row carries `PRICE_PATH_NOT_PROCEEDS` and `NO_HISTORICAL_EXECUTABLE_DEPTH`, no position size, and no field named after profit, return, exit or proceeds (P08, P25, P44).

## Targets labelled (exactly the registry's primary targets)

| Id | Name | Version | Horizon | Barriers (relative to P0) | Positive | Negative | Maturity |
|---|---|---|---|---|---|---|---|
| T1 | `price_path_target_before_invalidation_24h` | 1 | 24 h after `t_entry` | high >= 1.25, low <= 0.85 | TARGET_FIRST | INVALIDATION_FIRST, AMBIGUOUS_BAR, NEITHER, NO_TRADES_AFTER_ENTRY | `t_entry` + 24 h + 900 s |
| T1b | `price_path_target_before_invalidation_6h` | 1 | 6 h | same | TARGET_FIRST | same | `t_entry` + 6 h + 900 s |
| T2 | `price_path_severe_drawdown_or_halt_24h` | 1 | 24 h (drawdown), halt span 18 h to 48 h | low <= 0.5 | DRAWDOWN_50, TRADING_HALT | NO_SEVERE_EVENT | `t_entry` + 48 h + 900 s |

Registered but not labelled (unchanged): the exit-adjusted target (BLOCKED_NO_HISTORICAL_DEPTH), liquidity degradation (DEFERRED_FORWARD_COLLECTION, PI-D-020), failed breakout (DEFERRED_PHASE_08), catalyst follow-through and distribution (BLOCKED_NO_DATA), the 7-day target and launch-cohort collapse (EXPLORATORY).

## Times

| Item | Rule |
|---|---|
| Decision | a decision event of `decisions.py` (identity `(mint, created_at, row_sha256)`), time = commit time of the first export holding the exact row (EXPORT_COMMIT); never `theses.created_at` |
| `t_entry` | decision + 300 s |
| Reference candle, P0 | `contract.reference_candle`: newest candle with end + 300 s at or before the decision and end at or after decision - 3600 s; P0 is its close |
| Path | `contract.path_candles`: candles starting at or after `t_entry` and ending at or before `t_entry` + horizon; the candle holding `t_entry` is never used (P06) |
| Halt span (T2) | [`t_entry` + 18 h, `t_entry` + 48 h); a candle is in it when it overlaps it (CC-03) |
| `label_matures_at` | `contract.label_matures_at`: entry lag + horizon + confirmation (T2: 24 h) + 900 s |
| `label_observed_at` | retrieval time of the read the label used; a label exists only when it is at or after `label_matures_at`, else PENDING (P05); never a claim of historical availability (P04, P07) |
| Read boundary | the window end on the 5-minute grid (`labels.needed_boundary`); GeckoTerminal's `before_timestamp` is inclusive and returns the candle containing an unaligned boundary, so every candle ending after the boundary is dropped (PI-D-034) |

## One read per decision (CC-03 rule 4, counterexample CX-06)

Eligibility, P0 and every target of one decision come from one GeckoTerminal response: `/networks/solana/pools/<pool>/ohlcv/minute?aggregate=5&limit=1000&before_timestamp=<boundary>&currency=usd&token=<mint>`. The token parameter is read from the URL actually sent and the body's meta must show the mint as base (`store.gt_identity`, PI-D-038, PI-D-039; with `token=<mint>` a body that keeps the other token as base is TOKEN_PARAM_NOT_BASE since repair pass 2, PI-D-045); otherwise no candle of the read is used. Candles pass the store's rules (`labels.read_from_body` keeps exactly what `store.ingest_gt_response` keeps; test). A read may serve several decisions of the same pool and archive when it demonstrably covers each of them (its earliest candle at or before the decision's need start, 24 h 10 min before the decision). Because the vendor computes a response's earliest open (and with it a high or low) from the request window, targets of one decision never mix reads; `labels.cross_target_violations` checks the invariants (same P0; a T1b first touch is T1's first touch; a T2 drawdown means T1 touched a barrier no later).

## Absence needs evidence (CC-03 rule 1, PI-D-039)

NO_TRADES_AFTER_ENTRY and TRADING_HALT are absences. An absence over a span counts only on an identity-checked read whose boundary reaches the span end on the candle grid and that returned a candle starting before the span (the vendor answers newest first, so every candle between that one and the boundary was served): `labels.absence_evidenced`. An empty or short page alone is never evidence of no trade; the label is then UNVERIFIABLE_NO_VENDOR_HISTORY. For eligible decisions the reference candle is in the same read, so the path is always evidenced when the boundary is right.

## T2 halt and other pools (CC-03 rules 2 and 3)

TRADING_HALT needs no candle in the halt span on the reference pool (with absence evidence) and none on up to three other pools: the first three pools other than the reference pool in the vendor's current list for the mint (`/networks/solana/tokens/<mint>/pools?page=1`, vendor order), each read with `token=<mint>` and the T2 boundary. A candle in the span on any of them gives NO_SEVERE_EVENT (flag HALT_ON_REFERENCE_POOL_ONLY); an other pool without absence evidence, a failed read or a failed list gives UNVERIFIABLE_NO_VENDOR_HISTORY. Other pools are read only when the reference pool shows an evidenced halt and there is no drawdown. A drawdown wins over a halt; an evidenced reference-pool halt is then kept as the flag HALT_ON_REFERENCE_POOL.

## States (one per decision and target)

| State | Meaning | Scored | Censored |
|---|---|---|---|
| LABELED | class computed from a matured read | development only, through the training gate | no |
| PENDING | the read came before `label_matures_at`, or the decision was not read because every label was still pending (P05) | never | no |
| PURGED | decision before 2026-10-17T00:00Z whose label matures after it (development rule); no class is computed | never | no |
| THINNED | eligible but inside the label window of the mint's previous kept decision for this target (`decisions.thin`, P20, P35) | never | no |
| MARKET_INACTIVE | no reference candle, with evidence of a quiet market (thesis 24 h volume under $1,000, or a candle on the point-in-time pool in the 24 h before) | never | no, counted |
| VENDOR_OR_ROUTE_GAP | no pool, a failed or identity-refused read, or no reference candle without that evidence (P09, P37) | never | yes, conservative lens |
| UNVERIFIABLE_NO_VENDOR_HISTORY | eligible, but an absence the label needs is not evidenced (detail: PATH_NOT_EVIDENCED, HALT_NOT_EVIDENCED_ON_REFERENCE_POOL, OTHER_POOL_NOT_EVIDENCED, VENDOR_POOL_LIST_FAILED) | never | yes, conservative lens |
| NO_SNAPSHOT_PRICE | the decision row's snapshot has no price (registry eligibility) | never | no, counted |
| OUT_OF_SCOPE_CHAIN | not Solana (v1 scope) | never | no, counted |
| PROSPECTIVE | decision from 2026-10-24T00:00Z (Phase 19's holdout) | never | no |
| NOT_READ | matured but never read: a visible plan gap | never | no, counted |

Conservative lens (frozen `ACCEPTANCE.eligibility.vendor_or_route_gap`): censored counted T1 and T1b negative, T2 positive. Tie rule (frozen): a candle touching both T1 barriers is AMBIGUOUS_BAR, a negative; `label_tie_positive` keeps the opposite resolution for the sensitivity that the registry requires when AMBIGUOUS_BAR exceeds 10% of labelled development events.

## Splits

Per target: DEVELOPMENT (decision before 2026-10-17T00:00Z and `label_matures_at` at or before it), PURGED (decision before it, maturity after), HOLDOUT (decision in [2026-10-17T00:00Z, 2026-10-24T00:00Z)), PROSPECTIVE (from 2026-10-24T00:00Z). Development reads have boundaries at or before the holdout start; holdout reads live in a separate sealed store and archive. The two decisions in `ACCEPTANCE.holdout_contacted` carry `holdout_contacted: true` in the sealed file and are excluded from the primary holdout in Phase 12.

## Flags and sensitivities kept per row

`KEY_CONFLICT` (decision rows sharing `created_at` that differ; every result repeated without), `CURRENT_VENDOR_LIST` (route from today's vendor list: survivorship risk, stratified), `WICK_TOUCH` (the touching candle traded under $500), `SPARSE_PATH` (largest gap in the path over 2 h), `WINDOW_EDGE_CANDLE` (a path candle is the read's earliest, so its open, high or low may depend on the request window), `HALT_ON_REFERENCE_POOL`, `HALT_ON_REFERENCE_POOL_ONLY`, `REVISED` (a later read changed the label; both rows kept), `P0_FAR_FROM_SNAPSHOT_PRICE` (P0 outside 0.1 to 10 times the decision's own snapshot price: a sanity flag against wrong-token reads, never a class; PI-D-045). `sensitivity_json`: `label_tie_positive`, `conservative_lens`.

## Storage

Additive migration 2 (`labels.LABEL_MIGRATIONS`, applied by `labels.connect` beside Phase 05's migration 1, which is unchanged): tables `predictive_label_runs` and `predictive_labels`, append-only (triggers), rollback by `labels.rollback_labels` leaves the Phase 05 tables. `predictive_labels` refuses HOLDOUT rows by a CHECK; holdout records exist only in `phase_06/sealed/holdout_labels.jsonl.gz`, hashed in `phase_06/sealed/SEAL.json`. Row fields: label key; run key; decision key; chain, mint, pool, route; target, target version, label version, registry fingerprint; split, state, class, label, censored, eligibility, `thinned_by`; decision time and basis, export commit; `t_entry`, P0 and its candle start, first touch candle start and its volume; `label_matures_at`, `label_observed_at`; response key, request URL, body sha256; other pools' evidence; flags; caveats; groups (exact mint, creator wallet of the decision's own token row, P14); cohort (launch age from `first_pool_at`, liquidity, UTC day and week, thesis status group, route, decision staleness, KEY_CONFLICT); sensitivities; detail; `revision_of` and its reason. CHECKs: a label exists exactly when the state is LABELED, a LABELED row was observed at or after maturity and has its read, P0 and entry; censored exactly for the two censored states.

## The training gate (the phase gate)

`labels.training_labels(con, as_of, target, mode="provider")` returns only DEVELOPMENT, LABELED, uncensored rows matured by `as_of`. Split and maturity are recomputed from the decision time and the registry, and a stored row that disagrees raises (repair pass 2). Every version of a decision and target is considered and the newest one available by `as_of` decides (a revised row is available from its own read, the original from its maturity), so a revision that leaves LABELED removes the label. `mode="capture"` also requires `label_observed_at <= as_of` (what the lab actually held). It refuses a store file under the sealed or bake-off folders (`labels.refuse_sealed`, `runtime.refuse_bakeoff_labels(path=...)`), calls `runtime.refuse_bakeoff_labels` on its rows (PI-D-034) and `contract.assert_scorable` with `as_of` on every row. Only `labels.py` names the sealed folder (test).

## Revisions (P07, PI-D-018)

`labels.revision_changes(first, second)` compares two reads of one pool: positions in both with different values, and positions that appear or vanish inside both reads' coverage. It is the frozen check only for reads at least 48 h apart and candles that ended at least 48 h before the second read; shorter gaps are measured and reported as such. `labels.revise` recomputes a label from the later read and, when the class or P0 changes, returns a new row (`revision_of`, `REVISED`); the original stays.
