# Phase 00 audit of memelab-inbox (2026-10-10)

Facts below were seen in the checked-out code or in command output in this session. README and doc statements are labelled as claims where the code says otherwise.

Related: [EXECUTION.md](EXECUTION.md), [ROADMAP.md](ROADMAP.md), [DECISIONS.md](DECISIONS.md), [HANDOFF.md](HANDOFF.md).

## Checkout

- Clone: `git clone https://github.com/RyzinEnagy/memelab-inbox.git` (no bootstrap script run).
- Branch `main`, HEAD `48fe2900fa2e8643e592365a558fa0d469551e41` ("state: watchlist refresh 2026-10-10 pm"), working tree clean, 324 commits.
- Python 3.13.16, Node v22.22.0 (cloud sandbox).
- Entry points: `python -m memelab` (memelab/__main__.py -> cli.py), `python -m memelab.state export|import`, `tools/direct/direct_refresh.py`, `commit_file.py`, `bootstrap.sh`, `tools_bundle.py`.
- Dependency management: none. No pyproject, setup.py or requirements file. Third-party imports: numpy (m13, m14, m28, _common) and pytest (tests). Everything else is stdlib.

## Baseline tests (verbatim outcomes)

1. `python -m pytest tests -q` before installing anything: exit 1, `/usr/bin/python: No module named pytest`.
2. After `pip install pytest` (9.1.1): exit 1, `1 failed, 63 passed in 1.47s`. Failure: `tests/test_catalyst.py::test_dedup_corroboration_resurface_denial`, `AssertionError: assert ('REPORTED' == 'CONFIRMED')` at tests/test_catalyst.py:44.
3. Same test with `time.time` fixed to 2026-10-07 00:00 UTC: `1 passed`. The failure is clock dependent: the fixture announces a listing for 2026-10-09 and the run date (2026-10-10) is past it. Pre-existing; not changed in Phase 00.
4. The suite leaves a stray file behind: `data/reports/20261010_1724_BRETT_0x532f.md` (from the EVM test; it sets `MEMELAB_DB` to /tmp but reports still go to the repo's data/reports). Removed by hand after each run.
5. Smoke: `python -m memelab --help` exit 0, subcommands `init, plan, fetch, save, discover, stage2, analyze, scout, wallet, catalyst, chains, launch, watchlist, rejections, social-note`. `python -m memelab social-note --help` exit 0.

## Architecture as found in code

- Core pipeline: `normalize.py` builds the Bundle; `modules/m01..m28` are pure functions; `pipeline.py` runs them and persists; `report.py` renders markdown. Matches docs/ARCHITECTURE.md.
- Layers added since the README was written: `memelab/catalyst/` (event intelligence), `memelab/chains/` (multi-chain ecosystem), `memelab/launch/` (pre-launch engine), `farm.py` (dev wallet-farm check), `state.py` (portable state export), `wallet.py` (read-only personal wallet tracking). README layout section does not list these.
- Storage: SQLite at `data/memelab.sqlite` (path overridable with `MEMELAB_DB`). Schema in `db.py` with `CREATE TABLE IF NOT EXISTS`.
- Continuity between sessions: `state.py` exports selected tables to `data/state/latest.json`; scheduled runs commit state files to `state/` on `main`.

## Existing social and trader functionality

- `social-note` (cli.py:269): inserts one row into `social_snapshots` (mint, observed_at, source, metric, value, text_value, notes). Manual capture only, no validation.
- `social_snapshots` in the committed DB: 99 rows, all `jupiter` numeric holder-change metrics (1h, 6h, 24h), no text values.
- `modules/m19_attention_analysis.py`: attention from proxies (holder growth, traders, organic score, DEX Screener boosts) plus optional manual `social_obs`.
- `launch/social.py`: PRE_LAUNCH_SOCIAL_ANALYSIS (ORGANIC-LEANING / MIXED / PAID / COORDINATED-LEANING / UNKNOWN); X, Telegram, Discord, Farcaster explicitly UNKNOWN.
- `catalyst/attention.py`: publisher-level attention; social platforms UNKNOWN.
- `catalyst/sources.py`: registry rows for X timelines (manual), Reddit, TikTok, Instagram (blocked), YouTube feeds and Telegram public previews (navigate, none configured), and a trader research list as `trader:x:<handle>` rows (identity verification from profile pages only).
- No collector exists yet for X, Telegram or any social platform. No trader call tracking or trader scoring exists.

## Source access, observed 2026-10-10 from the cloud sandbox

- HTTP 200: lite-api.jup.ag, api.geckoterminal.com, api.dexscreener.com, api.rugcheck.xyz, raw.githubusercontent.com, x.com (home page), nitter.net.
- HTTP 403: api.github.com (proxy), reddit.com JSON.
- HTTP 302: t.me/s/solana (redirect; not followed in this check).
- Claim vs fact: README ("Cloud sandbox -> cannot reach crypto APIs") and docs/SOURCES.md (verified 2026-10-06) say the sandbox is blocked. SKILL.md (since 2026-10-08) and the observation above say direct API pulls work. Chrome-to-GitHub is now the fallback route, not the main one.
- GitHub writes: `gh` in the sandbox has an invalid GH_TOKEN, and api.github.com is blocked by the proxy, so the sandbox cannot push or use `commit_file.py`. Commits on `main` are authored by RyzinEnagy (293 via git/API, 31 via the GitHub web UI).

## Differences from earlier assumptions

- Two copies of the bridge JS exist: `bridge/*.js` at the repo root and `memelab/bridge/*.js`. They are identical today. SKILL.md loads the root copies from raw GitHub; `bootstrap.sh` skips `bridge/*`. A future edit to one copy without the other would split behaviour.
- `data/memelab.sqlite` is tracked in git although `.gitignore` lists `*.sqlite*` (added through upload). `data/inbox/` and `data/reports/` are also tracked alongside the root `inbox/`.
- `MANIFEST.txt` does not list `.gitignore`, `MANIFEST.txt`, the root `bridge/` files or the tracked `data/` files.
- No `github_upload.js` exists although `memelab/bridge/github_inbox.py` refers to it; the upload step lives in SKILL.md instructions.

## Secret handling and public-repo risk

- Credentials are designed to stay out of the repo: `data/config.json`, `data/wallet/`, `gh_token.txt` are gitignored; `commit_file.py` reads the token from local paths and never prints it; `state.py` exports no key or wallet tables.
- Scan of the current tree and all history for key patterns (Helius `api-key=` values, `ghp_`, `github_pat_`, `helius_api_key` values, Bearer tokens, `x-api-key`): no matches. Values were never printed. Placeholder URLs only (`api-key=<key>`, `api-key={key}`).
- No personal-wallet plan keys (`rpc:bal:`) in tracked data; history hits are code files only.
- Risk: Helius plans embed the key in the request URL (`HELIUS_TX.format(key=...)`). A shipped plan or result file that keeps request URLs would publish the key. No such file was found, but nothing enforces it. A pre-commit or test guard would close this.
- Risk: the GH_TOKEN environment variable seen in this sandbox is invalid; whether it was ever a live credential is unknown. If any GitHub token has been pasted into a chat, a file or a scheduled-task prompt, rotate it in GitHub settings.
- Redistribution: the public repo already republishes news RSS titles and descriptions (`inbox/cat01_*.json`) and the full analysis DB including third-party holder wallet addresses and transactions (public chain data). Social content would add a larger copyright, platform-terms and privacy exposure. See D-004.
