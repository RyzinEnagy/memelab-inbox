# Phase 09 forecast trace

Decision `6070e73636132d818acc46fe134dd097aadbac0bed79ff8de90a0e44ebf74f9e` of mint `2j5SaS7xy776qCBpyPQbZjyQSAtKiFgrwjfErthnW2ZM` at 2026-10-14T10:17:43Z (EXPORT_COMMIT), target `price_path_severe_drawdown_or_halt_24h`, fold 0 (cutoff 2026-10-14T00:00:00Z), label 1.
Row sha256 `114d0e156ebb64d1266ec820c03034114005a821ddba335ea2871f1b333880c8`; onchain-1 snapshot sha `9d5cc20390df5f2f970932a156824464c2d400e02ffd2f3c6f85bd2c9a0b581c`. Status PROVISIONAL_PENDING_REVISION_REREAD.

## Lab readings behind the values

- Fatal flags: none
- Token program: `TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb`
- Snapshot fields: {"adj_top10": 15.833756066832372, "exit_cap_3pct": 6770.513814530456, "liquidity": 698562.1392754536, "t": 1791971620.093}
- demand_order_flow: net buyers 24h +1799; buy/sell volume ratio 0.88; organic share 9%; buyer quality 0.13; manipulation screen MIXED / UNCERTAIN / wash MODERATE
- market_execution: liquidity $698,562; executable sell depth $6,771 at 3% impact; route OK, 3 hop(s); round-trip friction 2.15%
- supply_ownership: adjusted top-10 holds 15.8%; largest unexplained holder 2.3%; cluster-adjusted ownership 3.7% (confidence MODERATE); dev/insider holding 0.0%; early wallets SCALING_OUT
- token_lp_safety: token mechanics clean (no mint/freeze/delegate/fee/hook issues); transfer fee 0.00%; metadata immutable; LP risk HIGH; LP locked/burned 38%
- Previous decision `495d548ea782a24b9db7de6675775ccccb80efd5e00d398f130d662c60201706` at 2026-10-09T12:11:54Z: {"adj_top10": 17.702303126465146, "exit_cap_3pct": 2569.830578689184, "liquidity": 105075.26334394474, "t": 1791546774.685}

## onchain-1 values

| Feature | Value | Missing reason |
|---|---|---|
| `oc_authority_switch` | 0.0 |  |
| `oc_capture_delay_s` | 1442.907 |  |
| `oc_cluster_confidence_ord` | 1.0 |  |
| `oc_d_adj_top10_pp` | -1.86854706 |  |
| `oc_d_log1p_exit_cap` | 0.9684956391 |  |
| `oc_d_log1p_liquidity` | 1.894339163 |  |
| `oc_d_lp_locked_pp` | -25.0 |  |
| `oc_distribution_fatal` | 0.0 |  |
| `oc_early_wallet_dir_ord` | 2.0 |  |
| `oc_exit_cap_share` | 0.009692070947 |  |
| `oc_fee_change_pp` | 0.0 |  |
| `oc_freeze_authority_active` | 0.0 |  |
| `oc_largest_unexplained_pct` | 2.3 |  |
| `oc_lp_locked_pct` | 38.0 |  |
| `oc_lp_risk_ord` | 2.0 |  |
| `oc_mechanics_issues` | 0.0 |  |
| `oc_mint_authority_active` | 0.0 |  |
| `oc_no_sell_route` | 0.0 |  |
| `oc_prior_gap_h` | 118.0969444 |  |
| `oc_round_trip_friction_pct` | 2.15 |  |
| `oc_route_hops` | 3.0 |  |
| `oc_structural_fatal` | 0.0 |  |
| `oc_token2022` | 1.0 |  |
| `oc_transfer_fee_pct` | 0.0 |  |
| `oc_wash_ord` | 1.0 |  |

## Models (fold cards)

| Model | Card sha | Cutoff | Number | Abstain |
|---|---|---|---|---|
| A1_OC_B2_TC | `4f45641771ad2357` | 2026-10-14T00:00:00Z | 0.212652 |  |
| B0 | `9dfd5ddf9fb9042e` | 2026-10-14T00:00:00Z | 0.259615 |  |
| B2 | `c1078be8fd8a5889` | 2026-10-14T00:00:00Z | 0.212652 |  |
| M1_OC_LOGIT | `05270bc6f95f6670` | 2026-10-14T00:00:00Z | 0.223695 |  |
| M2_OC_LOGIT_B2 | `368b44ded1453db4` | 2026-10-14T00:00:00Z | 0.265329 |  |
| M3_OC_LOGIT_TREND | `2e9306a97d1ba124` | 2026-10-14T00:00:00Z | 0.013998 |  |
| R1_OC_RULE | `02e37eeb2a292316` | 2026-10-14T00:00:00Z | 0.215897 |  |

## Invalid inputs

- holdout_start_card_on_this_development_decision: REFUSED: card M2_OC_LOGIT_B2:price_path_severe_drawdown_or_halt_24h trained to 2026-10-17T00:00:00Z cannot score 1 earlier decision(s) (P13, RETROSPECTIVE_MODEL_NOT_AVAILABLE_AS_OF)
- next_decision_value_used: REFUSED: row 0: oc_lp_risk_ord__available_at 1792147326.0 is after the decision 1791973063.0 (future feature, P36)
- non_finite_value: REFUSED: value nan is not finite (P38)
- view_row_available_after_T: REFUSED: decision record available at 1791973064.0 reached a strategy at cutoff 1791973063.0

## Independent recomputation

`verify_trace_onchain.py` (no onchain.py, no features.py): 25 values, 13 model inputs and 7 model numbers recomputed; differences: 0; values available after the decision: 0; pass: True.
