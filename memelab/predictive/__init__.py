"""Predictive intelligence (research only). No existing module imports this package.

  contract.py   forecast output contract, pre-registered target registry and format validator (Phase 01)
  decisions.py  point-in-time decision records from state-export versions (Phase 01)
  runtime.py    error states, call guard, install guard, copyleft gate (Phase 04)
  store.py      point-in-time evidence store: private SQLite, predictive_* tables, append-only (Phase 05)
  sources.py    git export reader and bounded GeckoTerminal backfill with the holdout seal (Phase 05)
  features.py   as-of view, features_as_of, immutable snapshots, truncation proof (Phase 05)

Nothing here forecasts, labels or trains yet. Feature flag: data/config.json {"predictive": {"enabled": true}} turns later
phases' hooks on. It defaults to OFF and stays OFF until the final empirical QA gate (package EXECUTION_RULES "Integration
policy"; docs/predictive-intelligence/DECISIONS.md).
"""
