# Skeptic packet: forward depth collector (D-BT-034, repair D-BT-035)

For an independent reviewer. This packet states the task, where everything is and how to rerun it. It makes no claim about the result; judge from the artifacts.

## Task as given

Build a forward market-depth collector for the lab, folded into the backtesting module's hourly shadow tracker (Elving's approval of 2026-10-25: predictive PI-D-020, now PI-D-044; he chose the hourly tracker over a second job). Requirements:

1. Find what the tracker already records and what PI-D-020 needs: per chain, mint and pool, point-in-time pool reserves and executable sell quotes at fixed USD sizes, with the token amount used.
2. Sources: GeckoTerminal pool data (multi-pool endpoint) for reserves; the free Jupiter quote API for sell quotes, its terms and limits read from its docs. If quotes cannot be had free and within terms, record QUOTE_SOURCE_BLOCKED and still collect reserves. GeckoTerminal at most 6 calls a minute shared with the refresh step; a per-run call cap.
3. Mints: every mint with a thesis in the lab's exports (`data/state/latest.json` on `main` and its history) first seen within the last 24 h, with the pool the export names; a first snapshot at the next hourly run after the export, then hourly to 24 h. Record captured_at (UTC, when the response arrived), request URL, raw body sha256, and the lag from the export commit time to the first snapshot. Identity by chain plus exact mint and pool.
4. A step `collect` in hourly_shadow.sh between refresh and track, well inside 175 s on Elving's computer; a failed collect must not corrupt the store; additive schema migration with rollback; existing tables unchanged.
5. Offline tests with recorded fixtures, mutation checks, full suite green except the known clock test; one small live smoke recorded as evidence.
6. RUNBOOK (new step, exact revised scheduled-task prompt, deployment steps), HANDOFF, DECISIONS.

Hard rules: research only; no trade, wallet, key or seed phrase; no credentials printed or committed; no paid API; free public endpoints only; no change to tracked files under inbox/, state/, data/. Deployment to Elving's computer was out of scope.

Background to read: predictive branch `feature/predictive-intelligence` (121384b), docs/predictive-intelligence/DECISIONS.md entries PI-D-015, PI-D-020, PI-D-021, PI-D-034, PI-D-038, PI-D-039, PI-D-043, and audits/predictive-intelligence/phase_01/architecture/TARGET_REGISTRY.md (rows `exit_adjusted_target_before_invalidation_24h`, `liquidity_degradation_24h`). Backtesting contract: docs/backtesting/EXECUTION.md, DECISIONS.md, HANDOFF.md, RUNBOOK.md, OUTCOMES.md.

## Where things are

Branch `work/backtesting-collector` (local, not pushed), base feature/backtesting 054a619.

| What | Path |
|---|---|
| collector code | memelab/backtest/depth.py |
| changed code | memelab/backtest/schema.py (migration 2: three tables), memelab/backtest/cli.py (`backtest depth`, `--gt-prior-calls`, `--gt-prior-end`), memelab/backtest/sources/gecko.py (`get_json(..., provider=)`) |
| hourly script | audits/backtesting/release/hourly_shadow.sh (step `collect`, save log line) |
| tests | tests/test_backtest_depth.py; tests/test_backtest_timeguard.py (migration list) |
| fixtures | tests/fixtures/backtest/depth/ (recorded smoke bodies; the no-route and 401 bodies in the test file are written by hand) |
| mutations | audits/backtesting/testing/collector_mutations.json |
| work record and repair table | audits/backtesting/collector/COLLECTOR.md |
| first review and its probes | audits/backtesting/collector/COLLECTOR_SKEPTIC.md, audits/backtesting/collector/skeptic_probes/ (paths inside point at the reviewer's clone) |
| smoke artifacts | audits/backtesting/collector/smoke/ (collect.json, status.json, decisions.csv, snapshots.csv, raw/, dev_run_collect.json) |
| logs | first pass: audits/backtesting/testing/logs/c01_*.log; repair pass: c01r_*.log |
| operator text | docs/backtesting/RUNBOOK.md, "Forward depth collection", "Deployment to Elving's computer", "Scheduled task prompt" |
| records | docs/backtesting/DECISIONS.md (D-BT-034, D-BT-035), docs/backtesting/HANDOFF.md |

## Commands

From the repository root, Python 3.13, `pip install -r docs/backtesting/requirements-test.txt` if needed.

```
git log --oneline 054a619..HEAD
git diff 054a619..HEAD --stat
python -m pytest tests/test_backtest_depth.py -q -p no:cacheprovider
python audits/backtesting/testing/mutate.py audits/backtesting/testing/collector_mutations.json
python -m pytest tests -q -p no:cacheprovider          # known failure: tests/test_catalyst.py::test_dedup_corroboration_resurface_denial
python tools/release_audit.py --history
python tools/release_e2e.py --out e2e.md
rm -f data/reports/*_BRETT_*.md data/memelab.sqlite-shm data/memelab.sqlite-wal   # strays the suite leaves
```

Raw body hashes of the smoke: `cd audits/backtesting/collector/smoke/raw && sha256sum */*.json` (each file is named by its sha256), then compare with the raw_sha256 column of smoke/snapshots.csv.

Live rerun (network, read-only, about 10 free calls; needs a git checkout with network):

```
git init -q --bare /tmp/lab.git
GIT_TERMINAL_PROMPT=0 git -C /tmp/lab.git fetch -q --shallow-since="$(date -u -d '-72 hours' +%Y-%m-%dT%H:%M:%SZ)" https://github.com/RyzinEnagy/memelab-inbox.git +refs/heads/main:refs/remotes/origin/main
python -m memelab backtest depth collect --repo /tmp/lab.git --db /tmp/bt_review.sqlite --max-gt-calls 4 --max-quote-calls 6
python -m memelab backtest depth status --db /tmp/bt_review.sqlite
```

Local script run without market calls (as in c01_hourly_script_e2e.log): make a scratch HOME with mnt/memelab/backtesting_live holding code.bundle (a bundle whose branch is named feature/backtesting), bt.sqlite and hourly_shadow.sh; run `HOME=... bash .../hourly_shadow.sh setup`, then refresh, collect, track and save with `HTTPS_PROXY=http://127.0.0.1:9 HTTP_PROXY=http://127.0.0.1:9`.

## Questions a reviewer may want to test

- Does a thesis row count as a decision only at the first export that holds it, and never when it is in the oldest export read?
- Is the pool the one the export's token row names, and is a pool that does not hold the mint refused?
- Is captured_at the time the response arrived, and does the stored raw body hash to raw_sha256?
- Is the token amount sold equal to size / price at the mint's decimals, and does the quote's inAmount match it?
- Can GeckoTerminal ever be called faster than 10 s apart, or within 10 s of the step start, or more than the cap?
- Can any call start after the deadline, and what bounds the step's wall time on a slow network?
- What happens when GitHub, GeckoTerminal or Jupiter is down, rate limited or refuses keyless access?
- Can a failed collect change the stored database on Elving's computer?
- Are the v1 tables and their migration checksum unchanged, and does rollback to 1 remove only the new tables?
- Does the revised scheduled-task prompt keep every rule of the four-step prompt at 054a619 (docs/backtesting/HANDOFF.md)?
- For each row of the repair table in COLLECTOR.md: does the named test fail on the first-pass code (50565ad) and pass now, and does the named mutation survive anywhere?
- Can any 60 s window that holds a collect call hold more than 6 GeckoTerminal calls, given the refresh step's count and end time?
- Can a quote be OK while the router's implied price for the tokens sold is far from the pool price used, and can real price impact be flagged as PRICE_DISAGREES (see live_repair_run/)?
