# Non-negotiable completion checklist

[ ] Baseline source commit + actual tests verified; integration seam evidenced.
[ ] Data/requirements gap matrix and point-in-time spec approved.
[ ] >=40 candidates found, >=20 source-inspected, top 10 scored/reviewed, with rejected candidates documented.
[ ] Chosen upstream licenses/versions and adoption method pinned; no accidental live trading dependency in runtime.
[ ] Exact mint, pool, UTC and raw-provenance versioned; early-feature leakage prevented by tests.
[ ] Real historical data covers dead/delisted tokens, or absence is conspicuously labeled.
[ ] CPMM/CLMM/DLMM and missing reserves treated correctly; execution is not just closing candle price.
[ ] Size-specific route quotes and historic models separated; taxes, fees, impact and exit proceeds traced.
[ ] Point-in-time technical strategy validated with structural invalidation.
[ ] Catalyst strategy validated with original known-at times and negative/failed catalyst controls.
[ ] Maxun capability/AGPLv3/edition assessed as separate *robot acquisition* candidate; 06A comparative bake-off and ADOPT/NO_GO/BLOCKED decision recorded.
[ ] If adopted, real public robot run → canonical existing source registry demonstrated, with dedup/versioning, safety budget and no unapproved standing schedule. If rejected, evidence-backed alternative verified.
[ ] G36–G41 pass as applicable with honest live-versus-test-only status; present-day crawls never laundered as historical known-at evidence.
[ ] Deterministic trade/portfolio journal validated independently; cash/exposure conserved.
[ ] Strategy selection uses sealed out-of-sample, baselines, multiple-trial disclosure and uncertainty.
[ ] Stress includes liquidity collapse, whale distribution, stop gaps, manipulation and taxes.
[ ] Every discovered eligible opportunity triggers assessment or explicit reason to abstain.
[ ] Report distinguishes setup, entry, token attractiveness, empirical backtest and hypothetical scenario.
[ ] No-signal, no-history, no-depth, future-knowledge and failed-source states are safe.
[ ] No real orders/keys; existing fatal flaw overrides retained; existing tests pass.
[ ] Three real historical E2E studies, including failed/rugged token, where source access allows.
[ ] Independent adversarial suite G01–G41 and clean-environment checks proven.
[ ] Hand-offs, licensing, runbooks, docs, operational burden and release decision complete.

**Release decision cannot be PASS if key evidence on historical data, execution, temporal integrity, or source license is BLOCKED.** Conditional release can support a bounded **scenario-only research mode**, clearly labeled—not an empirically validated strategy engine.
