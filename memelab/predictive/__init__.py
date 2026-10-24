"""Predictive intelligence (research only). Phase 01 holds only the forecast output contract and the pre-registered target
registry (contract.py). Nothing here forecasts, fetches, trains or persists, and no existing module imports this package.

Feature flag: data/config.json {"predictive": {"enabled": true}} turns later phases' hooks on. It defaults to OFF and stays OFF
until the final empirical QA gate (package EXECUTION_RULES "Integration policy"; docs/predictive-intelligence/DECISIONS.md).
"""
