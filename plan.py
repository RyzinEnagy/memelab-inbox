"""Chain-aware fetch plans. Every request names its projection explicitly (proj=) so key prefixes never collide."""
from __future__ import annotations

from typing import Any

from ..bridge.plan import Plan, DEFAULT_SIZES
from . import registry as R

GT = "https://api.geckoterminal.com/api/v2"
LLAMA = "https://api.llama.fi"
LLAMA_STABLES = "https://stablecoins.llama.fi"
CG = "https://api.coingecko.com/api/v3"
GOPLUS = "https://api.gopluslabs.io/api/v1/token_security"
HP = "https://api.honeypot.is/v2/IsHoneypot"
KYBER = "https://aggregator-api.kyberswap.com"
DS = "https://api.dexscreener.com"
HL = "https://api.hyperliquid.xyz/info"

REGIME_COINS = ["bitcoin", "ethereum", "solana", "binancecoin"]
MEME_CATEGORIES = ["meme-token", "solana-meme-coins", "base-meme-coins", "four-meme-ecosystem", "sui-meme", "ai-meme-coins"]  # verified against /coins/categories 2026-10-07; no ETH/AVAX meme category exists


def ecosystem(plan_id: str | None = None, chains: list[str] | None = None, chart_days: int = 90) -> Plan:
    """Layer 0-2 inputs: regime, chain rotation, narratives, launchpads, emerging chains. One plan, ~45 requests."""
    p = Plan(plan_id or "eco")
    chains = chains or list(R.CHAINS)
    # regime
    for cid in REGIME_COINS:
        p.add(f"cg_chart:{cid}", f"{CG}/coins/{cid}/market_chart?vs_currency=usd&days={chart_days}&interval=daily", proj="cg_chart", delay_ms=1500)
    p.add("cg_global", f"{CG}/global", proj="cg_global")
    p.add("hl_meta", HL, "POST", {"type": "metaAndAssetCtxs"}, proj="hl_meta")
    p.add("llama_stables", f"{LLAMA_STABLES}/stablecoinchains", proj="llama_stables")
    p.add("llama_chains", f"{LLAMA}/v2/chains", proj="llama_chains")
    # chain rotation inputs
    for c in chains:
        cfg = R.CHAINS[c]
        p.add(f"llama_dex:{c}", f"{LLAMA}/overview/dexs/{cfg['llama']}?excludeTotalDataChart=false&excludeTotalDataChartBreakdown=true", proj="llama_dex")
        p.add(f"gt_pools:{cfg['gt_network']}:trending:1", f"{GT}/networks/{cfg['gt_network']}/trending_pools?page=1&duration=24h", proj="gt_pools")
        p.add(f"gt_pools:{cfg['gt_network']}:new:1", f"{GT}/networks/{cfg['gt_network']}/new_pools?page=1", proj="gt_pools")
        if cfg["tier"] == 1:
            p.add(f"gt_pools:{cfg['gt_network']}:trending1h:1", f"{GT}/networks/{cfg['gt_network']}/trending_pools?page=1&duration=1h", proj="gt_pools")
            p.add(f"gt_pools:{cfg['gt_network']}:top24:1", f"{GT}/networks/{cfg['gt_network']}/pools?page=1&sort=h24_volume_usd_desc", proj="gt_pools")
    # narratives + meme activity
    p.add("cg_cat", f"{CG}/coins/categories?order=market_cap_change_24h_desc", proj="cg_cat", delay_ms=1500)
    for cat in MEME_CATEGORIES:
        p.add(f"cg_mkts:{cat}:1", f"{CG}/coins/markets?vs_currency=usd&category={cat}&order=market_cap_desc&per_page=100&page=1&price_change_percentage=1h,24h,7d,30d", proj="cg_mkts", delay_ms=1500)
    p.add("ds_boosts", f"{DS}/token-boosts/top/v1", proj="ds_boosts")
    p.add("ds_boosts:latest", f"{DS}/token-boosts/latest/v1", proj="ds_boosts")
    p.add("ds_profiles:latest", f"{DS}/token-profiles/latest/v1", proj="ds_profiles")
    # emerging chains
    p.add("gt_nets", f"{GT}/networks?page=1", proj="gt_nets")
    p.add("gt_xnet:1", f"{GT}/networks/trending_pools?page=1&include=network&duration=24h", proj="gt_xnet")
    p.add("gt_xnet:2", f"{GT}/networks/trending_pools?page=2&include=network&duration=24h", proj="gt_xnet")
    p.add("cg_price", f"{CG}/simple/price?ids=solana,bitcoin,ethereum,binancecoin,avalanche-2,sui,hyperliquid,polygon-ecosystem-token&vs_currencies=usd&include_24hr_change=true", proj="raw")
    return p


def evm_discovery(chain: str, plan_id: str | None = None, pages: int = 2) -> Plan:
    cfg = R.get(chain); net = cfg["gt_network"]
    p = Plan(plan_id or f"disc_{chain}")
    for pg in range(1, pages + 1):
        p.add(f"gt_pools:{net}:trending:{pg}", f"{GT}/networks/{net}/trending_pools?page={pg}&duration=1h", proj="gt_pools")
        p.add(f"gt_pools:{net}:trending24:{pg}", f"{GT}/networks/{net}/trending_pools?page={pg}&duration=24h", proj="gt_pools")
    p.add(f"gt_pools:{net}:new:1", f"{GT}/networks/{net}/new_pools?page=1", proj="gt_pools")
    p.add(f"gt_pools:{net}:top24:1", f"{GT}/networks/{net}/pools?page=1&sort=h24_volume_usd_desc", proj="gt_pools")
    p.add(f"gt_pools:{net}:top6:1", f"{GT}/networks/{net}/pools?page=1&sort=h6_volume_usd_desc", proj="gt_pools")
    p.add("ds_boosts", f"{DS}/token-boosts/top/v1", proj="ds_boosts")
    p.add("ds_profiles:latest", f"{DS}/token-profiles/latest/v1", proj="ds_profiles")
    p.add("cg_price", f"{CG}/simple/price?ids={cfg['cg_native']},bitcoin&vs_currencies=usd&include_24hr_change=true", proj="raw")
    return p


def evm_structural(chain: str, addrs: list[str], plan_id: str | None = None) -> Plan:
    """Stage 2 for EVM: DEX Screener pairs (30 per call), GoPlus security in batches of 20, honeypot.is per token."""
    cfg = R.get(chain)
    addrs = [R.norm_address(chain, a) for a in addrs]
    p = Plan(plan_id or f"struct_{chain}")
    for i in range(0, len(addrs), 30):
        p.add(f"ds:{chain}:batch:{i}", f"{DS}/tokens/v1/{cfg['ds_chain']}/{','.join(addrs[i:i + 30])}", proj="ds")
    if cfg.get("goplus_id"):
        # GoPlus accepts a comma list but (verified 2026-10-07) answers with only the first address on the free tier: one call per token
        for a in addrs:
            p.add(f"goplus:{chain}:{a}", f"{GOPLUS}/{cfg['goplus_id']}?contract_addresses={a}", proj="goplus")
    if cfg.get("chain_id"):
        for a in addrs:
            p.add(f"hp:{chain}:{a}", f"{HP}?address={a}&chainID={cfg['chain_id']}", proj="hp", delay_ms=400)
    return p


def evm_deep(chain: str, addr: str, pools: list[str], decimals: int, price_usd: float | None, native_price: float | None, liq_usd: float | None = None,
             plan_id: str | None = None, sizes: list[float] | None = None, ohlcv_tfs=(("day", 1, 120), ("hour", 1, 300), ("minute", 15, 200))) -> Plan:
    cfg = R.get(chain); net = cfg["gt_network"]; addr = R.norm_address(chain, addr)
    p = Plan(plan_id or f"deep_{chain}_{addr[:8]}")
    sizes = sizes or DEFAULT_SIZES
    if liq_usd and liq_usd < 100_000:
        sizes = [s for s in sizes if s <= 25_000]
    elif liq_usd and liq_usd < 400_000:
        sizes = [s for s in sizes if s <= 50_000]
    p.add(f"gt_info:{addr}", f"{GT}/networks/{net}/tokens/{addr}/info", proj="gt_info")
    p.add(f"gt_pools:token:{addr}", f"{GT}/networks/{net}/tokens/{addr}/pools?page=1", proj="gt_pools")
    for pool in pools[:2]:
        for tf, agg, lim in ohlcv_tfs:
            p.add(f"gt_ohlcv:{pool}:{tf}{agg}", f"{GT}/networks/{net}/pools/{pool}/ohlcv/{tf}?aggregate={agg}&limit={lim}&currency=usd&token={addr}", proj="gt_ohlcv")
        p.add(f"gt_trades:{pool}:all", f"{GT}/networks/{net}/pools/{pool}/trades", proj="gt_trades")
        p.add(f"gt_trades:{pool}:big", f"{GT}/networks/{net}/pools/{pool}/trades?trade_volume_in_usd_greater_than=2000", proj="gt_trades")
    if cfg.get("goplus_id"):
        p.add(f"goplus:{chain}:{addr}", f"{GOPLUS}/{cfg['goplus_id']}?contract_addresses={addr}", proj="goplus")
    if cfg.get("chain_id"):
        p.add(f"hp:{chain}:{addr}", f"{HP}?address={addr}&chainID={cfg['chain_id']}", proj="hp")
    p.add(f"ds:{chain}:one:{addr}", f"{DS}/tokens/v1/{cfg['ds_chain']}/{addr}", proj="ds")
    if cfg.get("kyber") and native_price and price_usd:
        for usd in sizes:
            in_wei = int(usd / native_price * 1e18)
            base = int(usd / price_usd * (10 ** decimals))
            p.add(f"kq:{chain}:BUY:{usd}:{addr}", f"{KYBER}/{cfg['kyber']}/api/v1/routes?tokenIn={cfg['wrapped_native']}&tokenOut={addr}&amountIn={in_wei}", proj="kq", delay_ms=150)
            p.add(f"kq:{chain}:SELL:{usd}:{addr}", f"{KYBER}/{cfg['kyber']}/api/v1/routes?tokenIn={addr}&tokenOut={cfg['wrapped_native']}&amountIn={base}", proj="kq", delay_ms=150)
    if cfg.get("rpc"):
        def call(data: str, what: str):
            p.add(f"rpc_evm:{chain}:{what}:{addr}", cfg["rpc"], "POST", {"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"to": addr, "data": data}, "latest"]}, proj="rpc_evm")
        call("0x18160ddd", "totalSupply"); call("0x313ce567", "decimals"); call("0x8da5cb5b", "owner")
        p.add(f"rpc_evm:{chain}:code:{addr}", cfg["rpc"], "POST", {"jsonrpc": "2.0", "id": 1, "method": "eth_getCode", "params": [addr, "latest"]}, proj="rpc_evm")
    return p


def js_cfg(chain: str) -> dict[str, Any]:
    """Compact config for chains.js evmDeepPlan()."""
    c = R.get(chain)
    return {"gt": c["gt_network"], "goplus": c.get("goplus_id"), "chainId": c.get("chain_id"), "kyber": c.get("kyber"), "wnative": c["wrapped_native"], "rpc": c.get("rpc")}
