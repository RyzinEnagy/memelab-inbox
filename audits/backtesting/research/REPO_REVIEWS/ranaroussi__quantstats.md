# ranaroussi/quantstats

- URL: https://github.com/ranaroussi/quantstats
- Pinned commit: 9ef4c6d0a4ffe7831f6ebba6a5824fd33a90c05a (2026-09-27T20:38:37+01:00), cloned 2026-10-23T15:52Z with `git clone --depth 1`. Matches LONGLIST head_sha_2026_10_23 (no difference).
- Category: validation/metrics (performance analytics; not a backtesting engine)
- Discovery channel: seed (LONGLIST)
- Stars/forks (low weight, from search time): not recorded in LONGLIST / not recorded
- License (from LICENSE file text, not badge): Apache-2.0 (LICENSE.txt, full Apache License 2.0 text) ; transitive notes: hard dependency on yfinance (Apache-2.0) which pulls requests and curl_cffi (bundles a native libcurl-impersonate build); seaborn, matplotlib, scipy, tabulate.
- Package: PyPI `quantstats` 0.0.86 (py3-none-any; installed tree identical to the pinned source) ; Python/OS: requires-python >=3.10; CI ubuntu-latest only, Python 3.10-3.13 x pandas/numpy combos (.github/workflows/test-compatibility.yml:38-60) ; native deps: none directly; curl_cffi wheel via yfinance
- Maintenance: last commit 2026-09-27 (0.0.86); CI test-compatibility.yml, python-publish.yml; tests: 8 test files, 199 `def test_` (pytest) incl. tests/test_regressions.py (74) and tests/test_montecarlo.py (20)
- Security surface: `import yfinance as yf` executes at package import (quantstats/_compat.py:16); network download happens only when a ticker string is passed as benchmark or to download_returns (quantstats/utils.py:758-791, :808-810; quantstats/stats.py:3109-3110); HTML tearsheet template references an external favicon `https://qtpylib.io/favicon.ico` (quantstats/report.html:11), fetched when the report is opened in a browser. No order, wallet or key code.

## Verified capabilities (cite file:line at the pinned SHA)

| Capability | Mark | Evidence |
|---|---|---|
| OHLCV bars | NOT_SUPPORTED | inputs are return (or price) series only |
| tick/trade replay | NOT_SUPPORTED | none |
| CPMM math | NOT_SUPPORTED | none |
| CLMM/DLMM math | NOT_SUPPORTED | none |
| routes | NOT_SUPPORTED | none |
| fees/taxes | NOT_SUPPORTED | none; returns are taken as already net |
| thin exits / size-dependent impact | NOT_SUPPORTED | none |
| fill timing (next bar, latency) | NOT_SUPPORTED | no orders or fills; smoke [1] shows it does not re-time a supplied returns series |
| point-in-time guard / no lookahead | NOT_SUPPORTED | not applicable to post-hoc metrics; a full-sample-mean bug in `rolling_greeks()` alpha was only fixed in 0.0.86 (CHANGELOG.md:19-20) |
| async event/catalyst injection | NOT_SUPPORTED | none |
| wallets/on-chain | NOT_SUPPORTED | none |
| cross-token cohorts / portfolio | NOT_SUPPORTED | DataFrame columns are scored independently; no cohort logic |
| walk-forward / holdout / multiple testing | SOURCE_CODE_VERIFIED (uncertainty only) | Probabilistic Sharpe/Sortino (quantstats/stats.py:1297-1366, :1369), autocorrelation-penalized "smart" Sharpe (stats.py:875, :1000), permutation Monte Carlo (quantstats/_montecarlo.py:218-294); no walk-forward, holdout, deflated Sharpe or multiple-testing correction |
| metrics/report | SOURCE_CODE_VERIFIED | ~70 metrics (stats.py), VaR/CVaR (:2014, :2086), drawdown_details (:3301), HTML/text tearsheets (quantstats/reports.py:206 html, :1193 metrics) |
| live trading code present (must be avoidable) | NOT_SUPPORTED | none; only optional yfinance downloads |

## Fill and chronology assumptions (read the code)

None: quantstats never sees prices-at-decision or orders, only a realized return series the caller supplies, so all fill and chronology assumptions live upstream. Defaults assume equities: `periods=252` in sharpe/sortino and friends (stats.py:938-943), `periods_per_year=252` in reports (quantstats/reports.py:214), and `montecarlo_cagr` hardcodes `years = n_periods / 252  # Assume daily data` (stats.py:3597). Monte Carlo shuffles the observed returns with `rng.permutation` (_montecarlo.py:273), which destroys autocorrelation and leaves terminal wealth unchanged, so it can only widen path statistics (drawdown), not outcome statistics.

## Smoke test (if feasible, no wallets, no network beyond pip)

```
python3 -m venv /home/claude/ext/venvs/ranaroussi__quantstats
/home/claude/ext/venvs/ranaroussi__quantstats/bin/pip install -q --prefer-binary quantstats   # exit 0, quantstats 0.0.86, yfinance 1.7.0, curl_cffi 0.16.3
cd audits/backtesting/research/smoke/ranaroussi__quantstats
/home/claude/ext/venvs/ranaroussi__quantstats/bin/python -I script.py > output.txt   # EXIT_CODE=0
```
Outcome: exit 0, no benchmark ticker so no network. [1] a returns series built with entry at bar k+1 is reported as-is (first non-zero return 11:00). [2] Sharpe 20.16 with default periods=252 vs 118.86 with periods=8760 on the same hourly series (5.9x from annualization alone). [3] `montecarlo_cagr` on 2,000 hourly returns, 200 sims: min = max = -0.2488502687, std = 0.0 (degenerate). [4] `montecarlo_drawdown` gives a real spread (p5 -0.9703, p95 -0.9116).

## Scores (rubric R1.0, grades 0-5 in half points)

| Criterion | Max | Grade | Points | Evidence |
|---|---:|---:|---:|---|
| A transferability | 15 | 1.5 | 4.50 | works on any return series if `periods` is overridden; equity defaults (252) and a hardcoded 252 in montecarlo_cagr |
| B microstructure | 17 | 0.0 | 0.00 | no execution model at all |
| C point-in-time | 15 | 1.0 | 3.00 | nothing to guard; recent fix of a full-sample-mean rolling bug shows past leakage in rolling stats |
| D catalyst/on-chain events | 11 | 0.0 | 0.00 | none |
| E TA/strategy flexibility | 9 | 0.0 | 0.00 | none |
| F statistical validation | 11 | 2.0 | 4.40 | PSR and autocorrelation penalty; Monte Carlo is permutation-only (degenerate for CAGR); no walk-forward/holdout/DSR |
| G integration fit | 9 | 3.5 | 6.30 | pure Python, Series in, dict/HTML out; Py3.13 OK; Windows not in CI; imports yfinance at import time |
| H maintenance/tests | 6 | 3.5 | 4.20 | active (0.0.86 Sept 2026), 199 tests incl. regressions; Linux-only CI; 0.0.86 changelog lists several number-changing statistical corrections |
| I license/supply chain | 5 | 3.5 | 3.50 | Apache-2.0; unneeded network stack (yfinance, curl_cffi native lib) is a hard dependency |
| J operational footprint | 2 | 4.0 | 1.60 | 471 MB venv, no services |
| Total | 100 | | 27.50 | |

Hard gates: none. Most important limitation for memecoins: it only describes a return series someone else produced, with 252-period equity defaults; it cannot tell whether those returns were executable. Single capability it would contribute: a post-hoc tearsheet on the lab's own equity curves (drawdown_details, CVaR, Probabilistic Sharpe with explicit `periods`), strictly outside chronology-sensitive paths. One credible negative finding: `montecarlo_cagr` shuffles returns (_montecarlo.py:273) so every simulated path ends at the same wealth and divides by 252 bars per year (stats.py:3597); smoke [3] returned std = 0.0, a "distribution" that conveys no uncertainty.
Disposition: REIMPLEMENT_IDEA (PSR and drawdown-detail formulas are short and easy to re-derive with tests; avoids pulling yfinance/curl_cffi into the lab). Suggested use: REFERENCE.
