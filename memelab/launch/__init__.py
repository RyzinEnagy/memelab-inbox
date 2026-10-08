"""Pre-launch and new-launch intelligence.

Sits between narrative rotation and normal due diligence:
  PRE_LAUNCH_DISCOVERY / LAUNCH_CALENDAR (discover.py) -> identity states A-E -> TOKENOMICS_ANALYSIS (tokenomics.py)
  -> DEPLOYER_HISTORY (deployer.py) -> PRE_LAUNCH_WALLET_ANALYSIS + SNIPER_ANALYSIS (wallets.py) -> PRE_LAUNCH_SOCIAL_ANALYSIS (social.py)
  -> LAUNCHPAD_ANALYTICS + COMPARABLE_LAUNCH_ANALYSIS (cohort.py) -> PRE_LAUNCH_RANKER (ranker.py)
  -> LAUNCH_MONITOR + POST_LAUNCH_THESIS_CONVERTER (monitor.py) -> normal memelab pipeline.

The question is "which upcoming launches deserve attention, and what must happen after launch before the risk/reward is attractive",
never "buy before everyone else". There is no BUY status. Before trading there is no executable depth.
"""
