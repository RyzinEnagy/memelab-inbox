# esvhd/pypbo

- URL: https://github.com/esvhd/pypbo
- Pinned commit: 4d723f06498267a2a6280cb9d7d5649348e961d1 (2026-07-07T04:04:04+08:00, "Merge pull request #11 from esvhd/claude-bug-fixes"), cloned 2026-10-23T15:52Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23.
- Category: validation/metrics
- Discovery channel: GITHUB_API search "backtest overfitting probability" (raw/p02_github_search_hits.csv, rank 1)
- Stars/forks (low weight, from search time): 144 / not recorded
- License (from LICENSE file text, not badge): AGPL-3.0 (LICENSE is the GNU Affero GPL v3 text) ; transitive notes: strong copyleft including the network-use clause; importing or vendoring into the lab creates AGPL obligations if the lab is ever distributed or served; imports numpy, pandas, scipy, statsmodels, seaborn, matplotlib, joblib, psutil (README lists only joblib, seaborn, statsmodels; psutil is imported at pypbo/pbo.py:14).
- Package: none. Not on PyPI (pypi.org/pypi/pypbo/json returns 404) and the repo has no setup.py, pyproject.toml or setup.cfg ; Python/OS: pure Python source; Python 3.13 compatibility untested ; native deps: none beyond scientific wheels.
- Maintenance: last commit 2026-07-07; CI files: none; tests: 2 files (tests/test_pbo.py with 5 tests, tests/test_metrics.py), pytest.
- Security surface: none found (no network, no subprocess, no eval); `plot_pbo` calls `plt.show()` (pypbo/pbo.py:418).

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | NOT_SUPPORTED | input is a T x N returns matrix |
| tick/trade replay | NOT_SUPPORTED | |
| CPMM math | NOT_SUPPORTED | |
| CLMM/DLMM math | NOT_SUPPORTED | |
| routes | NOT_SUPPORTED | |
| fees/taxes | NOT_SUPPORTED | |
| thin exits / size-dependent impact | NOT_SUPPORTED | |
| fill timing (next bar, latency) | NOT_SUPPORTED | |
| point-in-time guard / no lookahead | NOT_SUPPORTED | CSCV keeps chunk order inside each half (pypbo/pbo.py:176-191) but by design trains on later chunks and tests on earlier ones; no purging or embargo |
| async event/catalyst injection | NOT_SUPPORTED | |
| wallets/on-chain | NOT_SUPPORTED | |
| cross-token cohorts / portfolio | NOT_SUPPORTED | |
| walk-forward / holdout / multiple testing | SOURCE_CODE_VERIFIED (multiple testing only) | PBO via CSCV pypbo/pbo.py:60-303; Deflated Sharpe 481-540; PSR 421-478; MinTRL 554-578; MinBTL 595-619; expected max of N trials 581-592; no walk-forward or holdout helpers |
| metrics/report | SOURCE_CODE_VERIFIED | pypbo/perf/metrics.py (sharpe_iid 383, sharpe_non_iid 494, sortino 287, omega 248, drawdown 714, calmar 752; trading_days = 252 at line 19); plot_pbo pypbo/pbo.py:353-418 |
| live trading code present (must be avoidable) | NOT_SUPPORTED (none) | |

## Fill and chronology assumptions (read the code)

No fills: pypbo consumes a returns matrix produced elsewhere. `pbo()` drops the first `T % S` rows (oldest data) silently (pypbo/pbo.py:140-144), splits the rest into S equal chunks, enumerates all C(S, S/2) halves (164), and for each computes the metric on the in-sample half and its complement (176-195), picks the in-sample best by rank (203), and records its out-of-sample relative rank w = rank/(N+1) and logit (206-213); PBO is the share of logits <= 0 (250-251). It also reports a linear IS-vs-OOS degradation fit (254-256), probability of OOS loss below `threshold` (258-260) and an ECDF stochastic-dominance table (263-278). Every J and J_bar array is kept in memory and returned in the result (173-191, 286-287): with S=16 that is 12,870 combinations, so a 1,000 x 100 matrix holds about 10 GB of copies. Plotting uses `sns.distplot` (392), deprecated since seaborn 0.11. The docstring itself warns CSCV is "Not suitable for time series with strong auto-correlation" (93-94). Annualisation defaults assume 252 trading days (perf/metrics.py:19), which is wrong for 24/7 crypto unless overridden.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
python3 -m venv /home/claude/ext/venvs/esvhd__pypbo
cd audits/backtesting/research/smoke/esvhd__pypbo
/home/claude/ext/venvs/esvhd__pypbo/bin/python -I script.py > output.txt   # exit_code=2
```
Outcome (output.txt): `pip install --only-binary=:all: pypbo` and `pip install --no-deps pypbo` both fail with "No matching distribution found" (not on PyPI); `pip install <clone>` fails with "Neither 'setup.py' nor 'pyproject.toml' found". Per the brief (AGPL, review only, smoke test only if it installs cleanly) no repo code was imported or run.

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 1.0 | 3.00 | asset-agnostic statistics; equity defaults (252 days); nothing crypto-specific |
| B microstructure | 17 | 0.0 | 0.00 | none |
| C point-in-time | 15 | 1.0 | 3.00 | keeps intra-chunk order; CSCV mixes future chunks into training by design; no purge/embargo |
| D catalyst/on-chain events | 11 | 0.0 | 0.00 | none |
| E TA/strategy flexibility | 9 | 0.5 | 0.90 | evaluates any N-config return matrix with a user metric; no strategy layer |
| F statistical validation | 11 | 3.0 | 6.60 | PBO/CSCV, DSR, PSR, MinTRL, MinBTL implemented and matching the papers' formulas; PSR/DSR/MinTRL/MinBTL tests use paper values (tests/test_pbo.py:7-93); the main `pbo()` function has no test; no walk-forward |
| G integration fit | 9 | 2.0 | 3.60 | Python and numpy/pandas based, but not installable, heavy import-time deps (seaborn, matplotlib, statsmodels, psutil), AGPL |
| H maintenance/tests | 6 | 1.5 | 1.80 | small test suite, `pbo()` untested, README TODO "Add test cases", no CI, no packaging |
| I license/supply chain | 5 | 1.5 | 1.50 | clear AGPL-3.0 text but strong copyleft; unpinned, undeclared deps (psutil) |
| J operational footprint | 2 | 1.5 | 0.60 | no install path; memory grows as C(S,S/2) x T x N |
| Total | 100 | | 21.00 | |

Hard gates: conditional license gate (AGPL-3.0): reading and independent re-implementation of the published formulas are fine; no import or vendoring into the lab without license approval. Most important limitation for memecoins: CSCV assumes stationary, comparable chunks and keeps every combination in memory; memecoin strategy returns are short-lived, heavy-tailed, autocorrelated and cohort-dependent, so PBO needs purging/embargo and per-cohort chunking that this code does not provide. One credible negative finding: the headline `pbo()` function has no test at all (tests cover only expected_max, psr, dsr, minTRL, minBTL) and retains every J/J_bar copy in the result (pypbo/pbo.py:173-191, 286-287), about 10 GB for S=16 on a 1,000 x 100 matrix.
Disposition: REIMPLEMENT_IDEA (fresh PBO/CSCV, PSR, DSR in the lab with the paper reference values as test fixtures and streaming combinations). Suggested use: REFERENCE.
