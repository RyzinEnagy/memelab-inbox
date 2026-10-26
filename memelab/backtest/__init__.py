"""Point-in-time backtesting and opportunity stress testing (research only).

This package never places orders, signs transactions, holds keys or connects wallets. It reads the lab's own
outputs and public read-only market data, and it never changes how the scout scores or labels a token.
Contract and evidence: docs/backtesting/ and audits/backtesting/.
"""

ENGINE_VERSION = "bt-0.2.0"   # 0.2.0: partial-exit accounting, network fee in the cash check, unsold remainders reported (Phase 16)
