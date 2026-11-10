# Reproducible GitHub discovery and deep research protocol

## Research question

Which **ten** public, legally usable repositories offer the most transferable, **actually implemented** capabilities for an execution-aware, catalyst-aware, point-in-time Solana memecoin research/stress-testing module integrated into the actual existing Memecoin Lab codebase? The top ten are research findings, **not necessarily ten installed dependencies**. **Maxun is tracked separately as a potential robot acquisition subsystem under Phase 06A, not included in the ten backtesting-engine rankings.**

## Tooling requirement

Read `WEB_RESEARCH_TOOLING.md`. Keep `GITHUB_API`/`GIT_CLONE` as the auditable primary discovery and code review source; use Firecrawl and/or Crawl4AI, where confirmed accessible, for multi-site documentation and related-repository discovery. Record tool used, URL, timestamp, content hash and exact claim-to-code verification for every crawler-derived finding. A crawler extract cannot satisfy a source-code due diligence gate without actual Git/code inspection.

## Minimum search breadth

- Record **>=40 unique repo URLs** with search date, terms, origin and explicit inclusion/rejection reasons. This is a *discovery* threshold; do not manufacture results if access blocks searches.
- Search across >=6 distinct categories: (1) fast vectorized parameter testing; (2) event-driven/backtest/ledger engines; (3) crypto/DEX/Solana strategy tools; (4) historic AMM/CLMM/DLMM and routing simulators; (5) social/catalyst/event studies and wallet features; (6) validation/metrics/robustness or immutable data/replay tooling.
- Independently search GitHub code/topics/README, project docs, PyPI/packaging if Python, recent issues/PRs/releases, maintainers/CI, and source citations from quant/crypto curated lists. Follow **backward and forward citations** from promising projects, dependencies, forks, and alternatives; do not just query 'memecoin backtest'.
- Search queries should include combinations of `crypto backtesting`, `Solana DEX backtest`, `AMM reserve replay`, `concentrated liquidity math backtest`, `Meteora DLMM historical bins`, `Jupiter routing quote simulation`, `historical onchain events`, `social sentiment lookahead`, `event driven simulator`, `walk forward purged CV`, `post trade slippage`, `latency MEV`, `factor evaluation`, `portfolio stress`, `token rug liquidity withdrawal`.
- Exclude commercial-only software **from installable rankings**, but research paid tooling as a comparator where useful. Do not silently equate vectorbt open source with PRO features.
- Read code, not only marketing READMEs. For final 20, review specific simulation/fee/data/strategy/test files and reproduce one runnable scenario when feasible.

## Per-repo due diligence evidence card

Capture: exact URL, commit SHA, review timestamp, latest activity with observed date, star/fork signals (low priority), maintainers/CI, release/dependency lock status, precise **license text** and transitive issues, Python/OS compatibility, whether an official package exists, dependencies/native compilation, security surface, provenance of claims, real file paths + tested function names, realistic test coverage, ease of using features *without* live trading, backtest chronology, execution fill assumptions, OHLCV vs tick/AMM support, liquidity/fee/router behavior, ability to inject asynchronous catalysts, multi-asset/portfolio/rebalance support, strategy parameter search, train-test controls, reports, reproducibility, adaptation work estimate, **limitation that matters most for memecoins**, and disposition (`PIP`, `VENDOR_EXCERPT_IF_LICENSE_APPROVED`, `REIMPLEMENT_IDEA`, `REJECT`).

For each relevant claimed capability mark `SOURCE_CODE_VERIFIED`, `DOCS_ONLY`, `DEMO_ONLY`, `NOT_SUPPORTED`, or `UNKNOWN`; cite SHA/file/line, run log if tested. A program's self-reported performance and claims are not independent validation.

## Ranking protocol

1. Finalize project-specific demands from Phase 01 before reviewing winners.
2. Use `GRADING_RUBRIC.md` weights; assign 0–5 evidence-anchored per criterion, multiply by weight/5, sum 100. Missing evidence scores 0–1, not assumed 3. Record rubric version **before** scoring.
3. Apply hard exclusions independent of total score. Explain any high-scoring exclusion.
4. Make a reproducible table of **>=20 deeply inspected** repos (if available); sort by hard-gate eligibility, numerical score, then evidence coverage, then lower integration risk. Rank ten top candidates with a separate integration shortlist of 1–3 components.
5. Run a `devil's advocate` pass: independently rescore a randomly sampled five finalists; investigate score differences >10 points and apparent winner's strongest weakness. Include a comparable niche project with fewer stars.
6. Tie-break by needed project capability, point-in-time guarantees, and cost/complexity; not by GitHub stars.
7. Persist search URLs, queries, evaluation facts, source links, exact commits, archived review notes and score calculations in machine-readable CSV/JSON and human-readable memo.

## Hard exclusion / legal / safety check

- No verifiable source or code at review commit, malicious installer, undisclosed network/execution requirement, inability to audit critical fill path, serious unresolved security hazard = not safely adoptable.
- Unknown/incompatible license = DO NOT copy/install into distributed project without authorization/legal review. Repo can remain a `RESEARCH_ONLY` ranked comparator with explicit gate, if research criteria met.
- Last push age alone is not automatic disqualification; weigh verified maintenance and dependency security.
- A historical backtest using end-of-bar closes or today's route quotes as yesterday's fills cannot pass execution realism without an explicit lower-fidelity label.
- Do not copy third-party source text/code during research without checking licenses and attribution; ideas/algorithms require fresh implementation and independent testing if direct reuse is barred.
