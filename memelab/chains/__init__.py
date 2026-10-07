"""Multi-chain ecosystem layer.

Layers above the per-token pipeline:
  0 crypto regime      (regime.py)
  1 chain rotation     (rotation.py, SOI per chain)
  2 narrative rotation (narrative.py)
  3 token discovery    (chain-aware plans in plan.py; evm.py for EVM chains)
  4-6 due diligence, trade setup, allocation reuse the existing modules through evm bundles that share the Solana bundle shape.

Principle: the system is chain-agnostic. Solana is one chain among many; the Solana engine is untouched.
"""
