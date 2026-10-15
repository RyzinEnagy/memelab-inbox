# Phase 03 — Independent research-validity audit

**Audit date:** 2026-10-13 (America/New_York)  
**Repository:** [RyzinEnagy/memelab-inbox](https://github.com/RyzinEnagy/memelab-inbox)  
**Pinned code baseline:** [`698f73b854567ce60b56ce275b5ab6822a9d5f60`](https://github.com/RyzinEnagy/memelab-inbox/tree/698f73b854567ce60b56ce275b5ab6822a9d5f60)  
**Scope:** Research methodology, not deployment, trading, profitability certification, or financial advice. Production source, configuration, tests, and database were not changed.

## Executive verdict

**REMEDIATION REQUIRED.** The software implements numerous useful protections against elementary research errors: exact chain/contract identity, separate wallet/account attribution, lots and partial dispositions, conservative abstention on small or incomplete samples, separate observed and modeled execution, repost grouping, rejection-preserving discovery integration, and a chronological replay design. Those features are meaningful but **do not establish that its trader rankings or Information Alpha Score predict future investable returns**.

Two **independently reproduced temporal calculation flaws** are material:

1. **Alpha intrabar execution:** a decision within a historical candle is priced at that candle's *earlier open* (`entry_for` and `exit_for`), or by a complete candle's high/low that is not known before the candle ends. The published execution delay is not honored by the price observation in these situations. The same flaw affects candidate controls.
2. **Wallet USD mark timing:** the performance engine's nearest-price lookup can value a transaction using a future mark within the price-tolerance window. This affects historical USD costs, proceeds, fees and derived wallet results, not the actual on-chain transfer quantities.

The historical replay documentation explicitly says the lab's then-tracked history supports **no validated strategies**: all four are `INSUFFICIENT_DATA`, with no social events in the tracked database. No real-world win rate, excess return, hit rate, alpha, Sharpe ratio, or prospective selection uplift can honestly be inferred from fixture tests. See [`REPLAY_17.md`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/docs/social-intelligence/REPLAY_17.md#L1-L22).

### Overall confidence in the outputs

| Output type | Audit confidence | Appropriate current use |
|---|---|---|
| Ledger handling of recognized swaps, known partial lots, transfers and fees | **Moderate** for supplied/fixture data | Investigative reconciliation, with coverage and transaction classification reviewed |
| Observed wallet realized P&L in USD | **Low–moderate** | Conditional estimate for observed wallet and window; **not** trader skill or comprehensive lifetime P&L |
| Unrealized wallet profit and executable liquidation proceeds | **Low** without size-specific live quotes | Scenario display only; missing routes cannot imply realizable value |
| Source's historical Information Alpha Score | **Low** | Exploratory relative-return statistic, **not** validated predictive information alpha |
| Narrative volume, independence and emergence labels | **Moderate for explicit repost grouping; low for organic independence or true novelty** | Candidate discovery with provenance, bot/coordination and sampling qualifications |
| Wallet-to-trader attribution | **Moderate where signed and reviewed; otherwise low/unknown** | Evidence-qualified association only; never infer person-level profits from an address |
| Social-assisted research priority | **Moderate as a safe presentation workflow; unvalidated as an improvement** | Decide what to investigate next, not what to buy or size |
| Historical backtest / positive predictive or investable performance claim | **Not established** | **Cannot validate yet** |

**Evidence grades:** *Reproduced* = a deterministic synthetic probe exercised the pinned implementation; *Code-confirmed* = behavior follows directly from inspected code; *Methodological limitation* = model cannot support a stronger financial claim; *Not evaluated* = no trustworthy real observations were supplied. Severity measures threat to defensible research, not demonstrated investor loss.

## Preparation, evidence and reproducibility

The requested audit files from previous phases are **not tracked in the GitHub checkout**. We recovered the prior Phase 00/01 findings register from the project's available personal Library, and reviewed the Phase 01/02 audit conclusions available in prior project context. Phase 02 is known to have added **AUD-018–AUD-023**, but its full text was not accessible in this execution environment. Those six IDs are **reserved and not overwritten or reconstructed from guesses**. This report cross-references the known earlier issues without treating the missing full Phase 02 artifact as verified firsthand. The accompanying `FINDINGS.md` is an explicitly marked *recovered-and-extended copy*, not a certified byte-identical merge of Phase 02.

Inspected actual pinned implementations: `wallet_activity`, `wallet_assertions`, `perf_core`, `perf_analysis`, `perf_store`, `alpha_core`, `alpha_store`, `narratives`, `identity`, `chrono_core`, `research_core`, `outcomes_core`, `outcomes_cli`, `replay_core`, `replay_sources`, with their stage documentation and test inventory. The Phase 01 independent audit had already reported **651 passing / 1 failing** tests (the pre-existing catalyst regression), and **17 passing / 5 failing** independent integration tests; those results were **reviewed, not rerun** during this quantitative Phase 03. Existing fixtures are not real-market validation. No social API, wallet, paid model, exchange, or live execution route was contacted or used here.

**Independent offline probes run in Phase 03** (no external requests, no production writes):

| Probe | Synthetic setup | Observed pinned-code output | Financial interpretation |
|---|---|---|---|
| A: alpha entry | 1-hour candle starts at `t=0`, opens 10, high 100; decision at `t=1800`, trade value $500, reported liquidity $100,000 | `entry_for(...OPEN...)` returns `price=10`, `candle_t=0`, `fill_t=1800`; `CANDLE_ADVERSE` returns `price=100` | Former is an already elapsed open; latter can be a high only observed later in candle; neither is a demonstrated fill at t=1800 |
| B: alpha exit | Same candle, target exit `t=3000` | `exit_for` reports `price=10`, `t=3000`, `candle_t=0` | The target-time exit has been priced using a prior open |
| C: wallet mark | Native midpoint $100 timestamped `t=1100`; transaction `t=1000`; allowed tolerance 200 seconds | `Book.near` and `Book.unit_usd` return that later observation as `OBSERVED` | Future price can enter contemporaneous USD ledger calculation; default tolerance is 900 seconds |
| D: executable quote | Sell 50 tokens, larger synthetic route quote 100 tokens → $100 | `liquidation` returns `QUOTED_PRORATA` $50, explicitly calling it a “lower bound” | This is arithmetic extrapolation, not a guaranteed executable lower bound |
| E: missing quote | Same holding without a supplied quote | Per-asset `NO_QUOTE` with `value=None`; aggregate `_sum([])` returns zero | Per-asset uncertainty is preserved but aggregate zero may be mistaken for a measured executable P&L unless prominently labeled partial |

Probes establish deterministic behaviors **of invented inputs only**; they do not estimate bias size, historical trading returns, or live latency. The baseline's default alpha policy is a 300-second lag and $500 theoretical order with 100bps fees, 50bps slippage each side and `2 × size / reported liquidity` price-impact approximation. These parameters are assumptions, not measured venue-specific execution costs. [Implementation](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/alpha_core.py#L27-L63).

## Audit 1 — Trader performance

### Validated analytical methods

- The activity classifier uses both provider transaction type and inbound/outbound token/quote legs. It **does not equate an ordinary transfer with a sale**, and ambiguous mixtures are left `UNCLASSIFIED`. See [`wallet_activity.py:197–263`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/wallet_activity.py#L197-L263).
- Parsed ledgers explicitly reject malformed/duplicate entries, negative/nonpositive amounts and out-of-scope wallets. Unknown prior holdings become unknown-basis lots, not magically profitable buys. FIFO and average-cost lot consumption accommodate partial sales, and unmatched external transfers preserve unknown basis. See [`perf_core.py:180–309`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/perf_core.py#L180-L309), [`465–537`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/perf_core.py#L465-L537), [`757–861`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/perf_core.py#L757-L861).
- Realized trading P&L, unknown-basis proceeds, airdrops, network costs, open mark-to-market and modeled liquidation are **separate accounting views**; token-sale legs use recorded executed amounts when available. Position-level fee knowledge, duration, basis coverage, classification coverage and a minimum of 20 closed positions gate wallet scores. The reported win interval is Wilson; single-winner concentration is explicitly measured. See [`perf_analysis.py:89–191`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/perf_analysis.py#L89-L191) and [`512–564`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/perf_analysis.py#L512-L564).
- Self-disclosure and transaction patterns are **not** equivalent to signed, reviewed control proof. `person_level_claim` is false. See [`wallet_assertions.py:269–313`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/wallet_assertions.py#L269-L313).

### Incorrect, questionable or misleading calculations

1. **[AUD-025 — High; reproduced] Future price in historical wallet valuation.** `Book.near` minimizes absolute distance from an event, not distance among prior observations. In a synthetic case a later $100 native mark was accepted for an earlier fee/quote conversion. Historical valuation is therefore not fully point-in-time clean. It may be acceptable as *retrospective valuation* only when explicitly identified as such; it cannot become the contemporaneously executable price or an alpha input. [`perf_core.py:342–369`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/perf_core.py#L342-L369).
2. **[AUD-029 — Medium; reproduced/model qualification] “Lower bound” is not contractually or empirically ensured by pro-rata quoting.** For a known route and fixed unchanged constant-product pool, a smaller order would normally have less average impact; this is a *model tendency*, not a guaranteed floor across routes, changing pool states, taxes, MEV or competing orders. When quote size is below inventory size, the partial proceeds cannot be called proceeds for the whole position. `IMPACT_CURVE` estimates must retain extrapolation flags. [`perf_analysis.py:196–222`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/perf_analysis.py#L196-L222).
3. **[AUD-029 — Medium; code-confirmed] Aggregate unrealized numbers can be numerically zero despite incomplete coverage.** `inventory_block` sums only assets with available estimates; with none available, the sum defaults to zero while coverage fields separately describe the missing values. Zero must be clearly represented as **unknown/partial** at the headline, not as zero realizable profit. [`perf_analysis.py:225–261`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/perf_analysis.py#L225-L261).
4. **[AUD-012 carried forward — Medium] Complete-wallet-history and external-profit assumptions remain unverifiable.** On-chain feeds may be truncated, exchange trades are unobserved, fee payer/tax information can be missing, LP impermanent loss is not fully modeled, and grouped addresses are analyst-chosen associations. The importer marks short fetches `PLAUSIBLY_COMPLETE`, not an archival proof of full wallet history. Some incomplete history can still produce a *scored* but low-confidence window metric. No evidence here establishes user/person-level aggregate P&L. [`perf_store.py:97–162`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/perf_store.py#L97-L162).

### Sample, survivorship and skill

The sample gate is a useful minimum, **not a statistical skill validator**. The ranking universe includes only wallets discovered and tracked, with incomplete backfills and unknown failures. A profitable observed wallet can be selected precisely because it survived to be noticed. To assess trader skill, require a prospectively fixed wallet universe; complete sampled histories including inactive/loss-making wallets; gains decomposed by largest token and time cohort; fees/taxes/failed swaps/capital at risk; and hierarchical clustering by common wallet controller when **evidence-backed**, rather than equating wallets with people. Examine the return **net of feasible exit execution for the relevant size**, not just wallet mark-to-market or transaction-price returns.

## Audit 2 — Information Alpha

### Validated analytical methods

The engine enforces exact token identity, publication and first-sighting timestamps, excludes reposts, ambiguous/conditional claims and late-captured items, applies an explicit response delay, treats unknown future horizons and missing histories as unevaluable, avoids counting one source's same-direction repeats as independent calls, and matches control tokens by pre-entry liquidity and trailing volume. Popularity/followers and wallet performance are **not fed into the Information Alpha score**. Scoring includes median relative signed return, confidence intervals, sample and distinct-token thresholds, shrinkage, completeness and a chronological-half sign check. [`alpha_core.py:27–75`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/alpha_core.py#L27-L75), [`287–351`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/alpha_core.py#L287-L351), [`565–632`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/alpha_core.py#L565-L632).

### Incorrect or unsupported aspects

1. **[AUD-024 — High; reproduced] Historical fill-time error.** `_candle_at` returns a candle *covering* a decision time; `entry_for` and `exit_for` price it at that candle's `o` (earlier open) for `OPEN`, or `h/l` (may be future intrabar extrema) for `CANDLE_ADVERSE`. These are not point-in-time executable fills following publication + capture + delay. Changing the policy's delay does not fix intrabar price timing. This may materially alter both signed returns and relative control comparisons. [`alpha_core.py:182–253`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/alpha_core.py#L182-L253).
2. **[AUD-026 — High; methodological limitation] A `VALIDATED` Information Alpha tier is not prospective predictive validation.** That tier requires 30+ historical calls, 20+ tokens, adequate coverage, a confidence interval excluding zero and agreement between chronological halves. There is no locked independent prospective forward holdout in this scoring path, nor adjustment for correlated overlapping calls, source selection, parameter exploration or multiple searches over traders and horizons. The score is a transformed, shrunk historical median relative return, **not a probability of future outperformance and not a proof of causal information advantage**. [`alpha_core.py:511–645`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/alpha_core.py#L511-L645).
3. **[AUD-027 — Medium; methodological limitation] Matching does not isolate exogenous predictive alpha.** The control distance uses liquidity and trailing volume within the same chain. It does **not** require matching market cap, token age, volatility, pre-post momentum, launch cohort, sector/narrative or liquidity trajectory. Surviving baseline assets with valid future candles can differ systematically from the promoted tokens. The source's post may itself cause a tradable attention spike rather than forecast exogenous value; later positive return is not independently corroborated information. [`alpha_core.py:358–376`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/alpha_core.py#L358-L376).
4. Source `universe_count` and completeness are supplied externally, not independently reconciled against complete X/Telegram access. If omitted, a *PRELIMINARY* score may still appear. Selectively imported historic winners are not automatically disqualified. [`alpha_core.py:557–585`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/alpha_core.py#L557-L585).
5. The execution-cost model assumes a constant-product first-order penalty `2*trade_size/liquidity` plus fixed bps. This is not a size-specific route quote and can fail badly for concentrated liquidity, transfer taxes, exhausted routes, dynamic fees and large exits. `SHORT` and `EXIT` are signed directional information returns and explicitly not executable spot shorts; never market them as realizable short profits. [`alpha_core.py:196–261`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/alpha_core.py#L196-L261).

**Conclusion:** The current statistic is a conditional *historical relative-return association under supplied prices and assumptions*. After the observed fill-timing defect, even that calculation needs repair and restatement. Predictive Information Alpha is **unproven**.

## Audit 3 — Narrative intelligence

### What works

Reposts, forwards, original-referencing quotes/replies, and byte-identical text are grouped in dependency families rather than each appearing as a new independent origin. The engine separately reports raw item volume, amplification, dependent commentary, independent sources, changes in stance, burst amplification and identical-copy flags. Coordination is labeled a **hypothesis**, not proof of a common operator. Source coverage and freshness can cap confidence. [`narratives.py:213–349`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/narratives.py#L213-L349).

### Unsupported independence and novelty claims

- **[AUD-028 — Medium] Source-independence ≠ ownership or thought independence.** Each distinct social source can count once toward corroboration even if different coordinated handles post unique, non-identical copy; explicit repost/identical hashes cannot catch sophisticated coordinated networks, paid promotion, mutual amplification or shared funding. Five apparent sources can reach the uncapped HIGH confidence rule. [`narratives.py:311–429`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/narratives.py#L311-L429).
- Raw `window_mentions` and `peak_sliding` count posts, including repeated posts from one source. `windows.origins` is a better measure of separate origin events, but neither proves separate economic interests or organic demand. [`narratives.py:192–205`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/narratives.py#L192-L205), [`360–365`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/narratives.py#L360-L365).
- The social `EMERGING` level means **few identified independent sources in the collected window**, not that the narrative did not exist earlier on uncollected platforms or was new to the market. Historical lookback and external novelty benchmarks are not established. [`research_core.py:112–133`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/research_core.py#L112-L133).
- **Existing AUD-001 / AUD-015 / AUD-017 remain relevant:** late extraction and later-generated chronology flags can leak into historical feed/narrative views. A timestamp printed in an old report does not prove its input interpretation was available then.

**Recommended wording:** “N unique sources in the sampled dataset independently *appear* to have originated claims under the current dependency heuristic; coordinated control and true market novelty are not established.” Avoid “organic consensus” or “new narrative confirmed.”

## Audit 4 — On-chain interpretation

**Validated discipline:** Token joins use exact `(chain, contract)`, not ticker. Attribution preserves social-account versus wallet distinctions; reviewed signed claims carry stronger status than transaction-pattern hypotheses. Chronology checks wallet chain, token identity, event timing and ambiguous linkage. Transfers are separated from sales at ingestion. [`chrono_core.py:364–460`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/chrono_core.py#L364-L460). These are valuable analytical controls.

**Limits requiring qualification:**

- Shared funders, common timing and destinations support a *possible cluster*, not a single individual, legal beneficial owner or proven collusion. The system's source labels cannot by themselves prove physical-wallet control; self-claims and signed proofs have differing evidentiary strengths.
- An exchange deposit/transfer is **not** a completed sale. Swaps with recognizable executed legs are stronger evidence of executed purchases or sales; absent complete provider history, “accumulation” or “distribution” remains a bounded interpretation rather than a proven balance-sheet trend.
- Social token `structure_lane` inherits the upstream discovery engine's `fatal_flags` and `untradeable` statuses rather than redoing security screening. **[AUD-031 — Medium] An absence of those flags is not affirmative evidence of verified mint/freeze/fee authority, LP custody, token transfer restrictions, holder identity, actual executable depth, or sell-route availability.** [`research_core.py:136–154`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/research_core.py#L136-L154). Especially on Solana Token-2022 and dynamically configurable pools, each tradeable conclusion needs dated program/authority checks and route quotes.
- Reported liquidity and market cap are valuation/context, **not order-book or swap-curve depth**. A quoted capitalization multiplied by supply cannot be converted directly into realizable liquidation proceeds. For every contemplated trade, require size-specific post-fee sell estimates and token-authority readings at the report's timestamp; flag missing evidence explicitly.

## Audit 5 — Research prioritization

The integration is **structurally safer than mixing influencer enthusiasm into a buy score**. It deliberately maintains separate attention, token-structure and entry lanes; editorial `attention_weight` cannot change core scout score, status, ranking, watchlist, prior fatal rejection or execution. A missing social signal is not a penalty. An unresolved ticker stays outside identified-token ranking. [`research_core.py:1–17`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/research_core.py#L1-L17), [`220–329`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/research_core.py#L220-L329).

**[AUD-030 — Medium] Editorial ordering is not an empirically useful candidate-selection policy.** Within each research state, candidates are ordered by a heuristic that gives more weight to nominally independent sources and confidence, minus conflict/risk deductions. There is no demonstrated incremental precision, risk-adjusted return or analyst-time value against the original discovery pipeline. Sophisticated promotional networks can raise the apparent source count; a lone genuinely valuable contrarian signal can rank lower; social buzz can mechanically coincide with rising prices rather than add independent evidence. A structurally unevaluated token gets a `NEEDS_STRUCTURAL_ANALYSIS` label, not automatic rejection, and there is no mandatory size-specific route-depth gate before a `RESEARCH_CANDIDATE` is displayed. These are **research workload risks**, not evidence that the engine automatically trades unsafe tokens.

Before claiming improvement, freeze two matched versions of the screening process (original discovery alone vs original + social ordering); compare prospective candidates under identical time budgets, exact chain/contract identity, blinded analyst review, token-age cohorts, negative information, and liquidity/authority filters. Measure incremental calibration, precision and coverage of credible actionable setups—not merely more mentions or later price increases.

## Audit 6 — Historical validation

The replay framework **does** contain real guard structures: evidence availability clocks, source/contract matching, controls, chronological train/validation/test partition, embargoed outcome labels and a frozen-configuration gate. These are technically defensible design elements. [`replay_core.py:700–778`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/replay_core.py#L700-L778).

**But the data preconditions are not satisfied.** The [authoritative Phase 17 replay document](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/docs/social-intelligence/REPLAY_17.md#L5-L22) records `INSUFFICIENT_DATA` for all four real-data strategies and no realized 90-day validation. A seeded synthetic world with invented planted pumps and delistings proves code-path behavior, not transferable edge. The existing observed ledger similarly depends on user-supplied/collector prices, and no comprehensive real price-and-quote archive was demonstrated.

**[AUD-032 — High; code-confirmed] The replay database export may assign derived CALLs the time an original item was first observed, not the later time its token identity/direction was extracted.** It also imports currently active wallet assertions without reconstructing historical availability. Thus the replay core can correctly reject *within-document* future data while the exporter has already backdated later knowledge. This reconfirms and extends existing `AUD-002`, and is not independent proof of a new external outcome. [`replay_sources.py:68–109`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/replay_sources.py#L68-L109).

**[AUD-033 — Medium; code-confirmed] Emission-time market facts can be selected using market `as_of` rather than `fetched_at`.** `market_at_generation` chooses `as_of` if supplied, and only checks that against signal generation. A fact whose market measurement predates generation but was fetched afterward can be written into the recorded generation-time context unless upstream guarantees stop it. This is a potential context leakage, not proof that a live signal has in fact been contaminated. The later outcome observation importer separately records both clocks, which is a positive distinction. [`outcomes_core.py:115–166`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/outcomes_core.py#L115-L166), [`outcomes_cli.py:85–109`](https://github.com/RyzinEnagy/memelab-inbox/blob/698f73b854567ce60b56ce275b5ab6822a9d5f60/memelab/social/outcomes_cli.py#L85-L109).

Historical data also face **selection/survivorship bias**: sources with retrospective discovery, promoted/successful token lists, absent delisted control prices, platform/API sampling limits and outcome windows overlapping across tokens and traders. Missing data must exclude the claim from validated performance, not be imputed as profits, losses or an optimistic baseline. Chronological splits must embargo overlapping horizons and account for dependence; confidence intervals over identically or economically correlated calls are not automatically well calibrated.

**Finding: Reliable live historical predictive validation is unavailable. No performance estimate is made.**

## Improvements to scoring methodology

**Wallet accounting / rankings:**

1. Separate three independently titled numbers: (i) observed execution-ledger realized P&L, (ii) marked open inventory, and (iii) executable liquidation value for an explicitly dated size; show `UNKNOWN` instead of zero or a guaranteed floor for missing size-specific exit depth.
2. Require for eligibility: complete history or a bounded audited observation window, source provenance per swap leg, known fee payer and token taxes, pricing strictly at or before historical transaction for real-time claims, and exclusion or interval bounds for unknown-basis inventory. Report the top-1/top-3 token and period contribution, active capital, loss tail, sample span and wallet-selection universe.
3. Rank **wallets** on demonstrably realized, coverage-adjusted results only; do not infer trader-level aggregate profit or publicly provided informational edge from wallet execution gains. Maintain explicit linkage evidence and confidence.

**Information Alpha / trader sources:**

4. Enforce next *available executable* price at or after `max(publication, first_seen) + delay`, with timestamp granularity compatible with execution. At most use already **closed** candles for decision features. If only coarse candles exist, publish return **bounds**, not an exact timed fill; never use uncompleted-candle extrema.
5. Keep a pre-registered direction/horizon, fixed cost-size policy and independent complete post universe. Score actual prospective calls including losses, delistings, amended/deleted claims, silence and missing outcomes as explicitly classified failures of evidence.
6. Replace naive single-candle cost assumptions with route/pool-specific quotes or depth curves, fees, transfer-tax configuration and stressed unwind scenarios; mark failure/no route as **non-executable**, and report how conclusions move with fee, delay and size.
7. Report an interpretable effect in percentage points relative to pre-registered matching controls, uncertainty clustered by source, token, narrative and time; perform multiple-testing adjustment and shrinkage across all candidates screened. Avoid an arbitrary 0–100 score until it is calibrated to an out-of-sample event frequency or decision utility. Rename current `VALIDATED` tier to **internally qualified historical association** until prospective evidence exists.

**Narrative and research ranking:**

8. Use independent-controller/coordination *hypotheses* with confidence, account longevity, shared source patterns, textual similarity beyond byte-identical copying, and sample-platform coverage. Publish raw volume separately from distinct author and dependency-group growth. Define “emerging” as *new within the observed corpus* unless benchmarked externally.
9. Weight contradictory evidence and contrarian but evidence-rich reports by historical reliability rather than penalizing lack of consensus. Gate any high-priority tradable presentation on token authority, liquidity concentration and **the planned sell quote**; unknown route is an abstention, not a favorable structure verdict.

## Improvements to signal validation — acceptance gates

| Gate | Required acceptance test | Why it matters |
|---|---|---|
| QV-01 Intrabar price integrity | Synthetic post at 30 min into a 1-hour candle; require no earlier candle open or not-yet-closed high/low used as execution; make wrong implementation fail | Eliminates demonstrable alpha timing error |
| QV-02 Point-in-time ledger marks | Every historical cost/proceeds/fee observation must have `available_at <= event time` for decision-time analysis; later marks only in explicitly retrospective analyses | Eliminates hidden future price inputs |
| QV-03 Complete source universe | Document provider cursor coverage, deletion/revisions, source sampling, denominator for every trader; retroactively selected winners trigger abstention | Controls post-hoc sample selection |
| QV-04 Matched-control design | Match token age, market cap, liquidity/depth, pre-call momentum, era and sector; include delisted and silent controls; log matching balance and failures | Reduces confounding and survivorship |
| QV-05 Realistic tradability | Timestamped size-specific buy/sell route quotes, fees/taxes, slippage/MEV scenarios, liquidity shocks, and no-route refusals | Paper gains are not necessarily cash-out proceeds |
| QV-06 Correlated uncertainty | Bootstrap/block by independent trader group, token and calendar cohort, embargo overlapping horizons; correct multiple comparisons | Avoids overstated statistical certainty |
| QV-07 Locked prospective test | Freeze source universe, mapping, features, policy and comparison model on train/validation; run untouched test and forward paper observation; publish all attempted signals | Distinguishes prediction from retrospective selection |
| QV-08 End-to-end as-of integrity | Inject a post observed at T, extracted at T+1d, wallet linked at T+2d, revised price fetched at T+3d; replay at each cutoff excludes knowledge until available | Addresses AUD-001/002/015/017/032/033 |
| QV-09 Organic-versus-coordinated | Several unique-text social accounts under a common actor plus a lone accurate contrarian; ensure confidence and rank do not infer distinct operators or automatically suppress dissent | Prevents promotion bias |
| QV-10 Incremental research utility | Randomized/blinded historical folds followed by prospective comparison: original discovery vs social-assisted, same resources and risk filters | Tests whether integration actually improves selection |

**Release criterion:** No predictive-value language, live leaderboard claim, or evidence-based trade recommendation from these scores until QV-01, QV-02, QV-03, QV-05, QV-07 and QV-08 pass with *genuine, independently traceable* data; QV-04/06/09/10 before a validated incremental-performance claim. Lack of a real archive is an `INSUFFICIENT_DATA` conclusion, not a license to substitute fixture returns.

## Findings / remediations in order of priority

| ID | Severity | Evidence | Summary | Prior relationship |
|---|---|---|---|---|
| AUD-024 | High | Reproduced | Alpha's intrabar historical entry/exit price is not a timed fill | New |
| AUD-025 | High | Reproduced | Wallet historical USD mark can come from the future | New |
| AUD-026 | High | Methodological | `VALIDATED` Information Alpha still in-sample/uncalibrated; no predictive validation | Expands AUD-008 |
| AUD-027 | Medium | Code-confirmed | Baselines matched on few confounders; social movement/selection not isolated | New |
| AUD-028 | Medium | Code-confirmed | Distinct sources and raw bursts need not be independent/organic or truly emerging | New |
| AUD-029 | Medium | Reproduced + code-confirmed | Quote scaling wrongly suggests guaranteed lower bound; partial/zero aggregate can mislead | Related AUD-012 |
| AUD-030 | Medium | Code-confirmed | Social heuristic research ordering has no verified incremental utility or universal exit-depth gate | New |
| AUD-031 | Medium | Code-confirmed | Inherited nonfatal structure does not prove token authority/exit risk was verified | New |
| AUD-032 | High | Code-confirmed; previously recognized | Replay input exporter backdates derived claims and current attribution | Explicit confirmation of AUD-002 |
| AUD-033 | Medium | Code-confirmed | Signal context may use market `as_of` before fact was fetched | New |

**Historical carry-forward:** AUD-001/002/008/012/015/017 are not closed. AUD-018–023 are intentionally reserved pending the original Phase 02 register. No production change or backtest-result fabrication was performed. **STOP — Phase 03 only.**
