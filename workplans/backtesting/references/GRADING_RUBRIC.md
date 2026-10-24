# Locked evidence-based GitHub scoring rubric (100 points)

Final project-specific refinements in Phase 01 must be **recorded before** evaluating candidates, including reason, reweighted sum 100, and applicability to all contenders. Base rubric:

| Criterion | Max | 5/5 requires proof of... | Typical penalty |
|---|---:|---|---|
| **A. Memecoin/DEX transferability** | 15 | Solana/crypto signal semantics, irregular markets, relevant adapters or reusable abstractions | equities-only fixed sessions, ticker-centric data |
| **B. Executable market microstructure** | 17 | sizes, dynamic costs, liquidity/depth, fees, execution state, adverse fill conditions | candle-close fills, flat % fees, no reserves |
| **C. Point-in-time integrity** | 15 | no future access, correct data timestamps, replay, tests preventing lookahead | future labels/rolling indicators leak |
| **D. Social/catalyst/on-chain events** | 11 | asynchronous event ingestion, temporal joins, causal event windows | text sentiment without timestamps |
| **E. TA/strategy flexibility** | 9 | programmable breakout/retest/regime rules and explicit exits | toy moving average hardcoded |
| **F. Statistical validation** | 11 | walk-forward/holdout, multiple testing, baselines, uncertainty and cohort correctness | training-only optimization |
| **G. Integration fit** | 9 | Python compatibility, modular APIs, simple subprocess/adapter integration with actual Lab stack | monolithic bot requiring wallets |
| **H. Maintenance and test credibility** | 6 | fresh/relevant CI, deterministic tests, no critical unresolved issues | untested claims or broken install |
| **I. License/supply-chain safety** | 5 | clear compatible license, pinned deps, auditable minimal imports, provenance | unknown/copyleft obligations unresolved |
| **J. Operational footprint** | 2 | reproducible install, bounded CPU/RAM, clear documentation | major service stack, expensive infra |
| **TOTAL** | **100** | | |

### Numeric scoring

Grade each item from **0–5** in half-point increments, using `criterion_points = max_points * grade / 5`. Round only the **total** to two decimals. A perfect score is not required to be a useful *single-module* source; track category fit separately. Supply one credible negative finding per candidate. Stars may influence only maintenance investigation, **never create score points themselves**.

`0` absent / contradicts safety; `1` marketing or unverified; `2` partial / major adaptation; `3` workable with explicit constraints; `4` confirmed good implementation and credible tests; `5` reproducibly demonstrated in relevant conditions plus documented limitations.

### Eligibility thresholds

- Final top-ten **research ranking** may include scored but `RESEARCH_ONLY` code with unmistakable exclusion/status annotations.
- **Adoptable dependency/borrowed code:** must pass licensing/security gate, score >=70/100, score >=3/5 in C (point-in-time) **or** be strictly sandboxed outside chronologically sensitive execution, and demonstrate isolated proof-of-concept success.
- Any engine responsible for historical fill assumptions must score >=3/5 in B **plus** pass the custom Golden Scenarios; this cannot be compensated by other scores.
- **Architecture selection:** favor a modest composition of **1–3** best-fit pieces + independently tested custom adapters, not necessarily the #1 monolithic repository.
- If no finalist is adequate, implement a small purpose-built engine informed by documented ideas, with a baseline independent test oracle and without copied incompatible code.

### Supplemental fit matrix

For each candidate mark capabilities `NATIVE/ADAPTABLE/NOT_SUPPORTED/UNKNOWN`: OHLCV, tick transactions, CPMM, CLMM, DLMM, routes, fees/taxes, thin exits, price structure, catalysts, point-in-time ingestion, wallets, cross-token cohorts, portfolio, event replay, validation, metrics, report output, API, Windows/Linux, current exact provider APIs.
