"""Predictive intelligence (research only). No existing module imports this package.

  contract.py   forecast output contract, pre-registered target registry and format validator (Phase 01)
  decisions.py  point-in-time decision records from state-export versions (Phase 01)
  runtime.py    error states, call guard, install guard, copyleft gate (Phase 04)
  store.py      point-in-time evidence store: private SQLite, predictive_* tables, append-only (Phase 05)
  sources.py    git export reader and bounded GeckoTerminal backfill with the holdout seal (Phase 05)
  features.py   as-of view, features_as_of, immutable snapshots, truncation proof (Phase 05)
  labels.py     price-path labels of the primary targets, censoring, holdout seal, mature-only training gate (Phase 06)
  stats.py      numpy statistical engine: scores, intervals, logistic, Platt, Venn-Abers, day walk-forward, fold audit (Phase 07)
  baselines.py  transparent baselines B0 to B4, negative controls, walk-forward evaluation, JSON model cards (Phase 07)

Nothing here publishes a forecast: Phase 07 fits baselines offline as research artifacts only. Feature flag:
data/config.json {"predictive": {"enabled": true}} turns later phases' hooks on. It defaults to OFF and stays OFF until the final empirical QA gate (package EXECUTION_RULES "Integration
policy"; docs/predictive-intelligence/DECISIONS.md).
"""
