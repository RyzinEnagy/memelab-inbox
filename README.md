# Memecoin Investing Lab: Opportunity Scout and Trade Research System

Evidence-driven research system for Solana memecoins. It discovers candidates, verifies identity by mint, measures executable depth with real router quotes, inspects LP control and Token-2022 mechanics, classifies holders and wallet clusters, reads order flow and price structure, constructs entries with structural invalidation, estimates risk/reward with scenario bands, sizes positions under both a risk and a liquidity constraint, plans exits before entry, scores on a transparent 100-point scale with a fatal-flaw override, keeps every snapshot, and reports what changed.

It never executes trades, never touches keys, and treats finding nothing as a success.

## Layout

```
memelab/              Python package
  db.py               SQLite schema (append-only snapshots) and helpers
  normalize.py        provider bodies -> Bundle contract (docs/ARCHITECTURE.md)
  pipeline.py         run modules, adapt to ranker, persist, render
  report.py           markdown token report and scout report
  forensics.py        Helius transaction history -> wallet profiles
  cli.py              python -m memelab {init, plan, save, discover, stage2, analyze, scout, watchlist, rejections, social-note}
  bridge/             browser bridge: collector.js, screen.js, stage2.js (run in Chrome), plan.py, ingest.py, github_inbox.py
  modules/            m01 .. m28 (one file per curriculum module; see docs/ARCHITECTURE.md)
data/                 memelab.sqlite, inbox/ (collected JSON), reports/ (markdown), config.json (keys; gitignored)
docs/                 ARCHITECTURE.md, SOURCES.md
skills/memecoin-scout/SKILL.md   operating procedure for Cowork sessions
tests/                pytest suite (synthetic + live-fixture integration test)
```

## Data path

Cloud sandbox -> cannot reach crypto APIs. Chrome (via Claude in Chrome) -> can. GitHub raw -> reachable from the sandbox.
So: Chrome collects and commits `inbox/*.json` to `RyzinEnagy/memelab-inbox`; the sandbox pulls and analyzes. Details in `docs/SOURCES.md` and the skill file.

## Quick start (sandbox side)

```
python -m memelab init
python -m memelab plan discovery --id disc02          # prints the browser call
# ... browser: run, screen, ship, commit ...
python -m memelab discover disc02
python -m memelab stage2 disc02 --results disc02 s2_02
python -m memelab scout --mints <mints> --results disc02 s2_02 deep02a deep02b --stage1 disc02
python -m memelab watchlist ; python -m memelab rejections
```

Account inputs for personal sizing: `--account-size`, `--max-loss-usd` or `--max-loss-pct`, `--position-usd` on `analyze`.

## Tests

`python -m pytest tests -q`
