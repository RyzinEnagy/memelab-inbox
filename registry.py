"""Chain registry: one record per chain the system knows how to research.

Fields describe *how* the chain is read (which identifiers each data source uses), not opinions about it.
Tier and status are starting points; the rotation engine moves research allocation, never this file.

family: solana | evm | move | other.  EVM chains share one engine (evm.py); the emerging-chain adapter builds a
partial record for anything that only DefiLlama / GeckoTerminal know about.
"""
from __future__ import annotations

from typing import Any

CHAINS: dict[str, dict[str, Any]] = {
    "solana": {
        "name": "Solana", "tier": 1, "family": "solana", "chain_id": None, "gt_network": "solana", "llama": "Solana",
        "cg_platform": "solana", "cg_native": "solana", "cg_meme_category": "solana-meme-coins", "ds_chain": "solana",
        "native_symbol": "SOL", "wrapped_native": "So11111111111111111111111111111111111111112",
        "stables": {"EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC", "Es9vMGANM1E2EjMA4c6kQX8m3KdMMw2sCkChfR4ZF9": "USDT"},
        "rpc": "https://solana-rpc.publicnode.com", "router": "jupiter", "goplus_id": "solana", "explorer": "https://solscan.io/token/",
        "launchpads": ["pump.fun", "letsbonk", "moonshot", "believe"], "typical_gas_usd": 0.01, "block_time_s": 0.4,
        "token_standards": ["SPL", "Token-2022"], "status": "ACTIVE",
    },
    "base": {
        "name": "Base", "tier": 1, "family": "evm", "chain_id": 8453, "gt_network": "base", "llama": "Base",
        "cg_platform": "base", "cg_native": "ethereum", "cg_meme_category": "base-meme-coins", "ds_chain": "base",
        "native_symbol": "ETH", "wrapped_native": "0x4200000000000000000000000000000000000006",
        "stables": {"0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": "USDC", "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca": "USDbC"},
        "rpc": "https://base-rpc.publicnode.com", "router": "kyberswap", "kyber": "base", "goplus_id": "8453", "explorer": "https://basescan.org/token/",
        "launchpads": ["clanker", "zora", "virtuals", "flaunch"], "typical_gas_usd": 0.02, "block_time_s": 2,
        "token_standards": ["ERC-20"], "status": "ACTIVE",
    },
    "bsc": {
        "name": "BNB Chain", "tier": 1, "family": "evm", "chain_id": 56, "gt_network": "bsc", "llama": "BSC",
        "cg_platform": "binance-smart-chain", "cg_native": "binancecoin", "cg_meme_category": "four-meme-ecosystem", "ds_chain": "bsc",
        "native_symbol": "BNB", "wrapped_native": "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c",
        "stables": {"0x55d398326f99059ff775485246999027b3197955": "USDT", "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d": "USDC"},
        "rpc": "https://bsc-rpc.publicnode.com", "router": "kyberswap", "kyber": "bsc", "goplus_id": "56", "explorer": "https://bscscan.com/token/",
        "launchpads": ["four.meme", "flap"], "typical_gas_usd": 0.05, "block_time_s": 0.75,
        "token_standards": ["BEP-20"], "status": "ACTIVE",
    },
    "ethereum": {
        "name": "Ethereum", "tier": 2, "family": "evm", "chain_id": 1, "gt_network": "eth", "llama": "Ethereum",
        "cg_platform": "ethereum", "cg_native": "ethereum", "cg_meme_category": None, "ds_chain": "ethereum",
        "native_symbol": "ETH", "wrapped_native": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        "stables": {"0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "USDC", "0xdac17f958d2ee523a2206206994597c13d831ec7": "USDT"},
        "rpc": "https://ethereum-rpc.publicnode.com", "router": "kyberswap", "kyber": "ethereum", "goplus_id": "1", "explorer": "https://etherscan.io/token/",
        "launchpads": [], "typical_gas_usd": 2.0, "block_time_s": 12,
        "token_standards": ["ERC-20"], "status": "LOW-PRIORITY MONITORING",
    },
    "arbitrum": {
        "name": "Arbitrum", "tier": 2, "family": "evm", "chain_id": 42161, "gt_network": "arbitrum", "llama": "Arbitrum",
        "cg_platform": "arbitrum-one", "cg_native": "ethereum", "cg_meme_category": None, "ds_chain": "arbitrum",
        "native_symbol": "ETH", "wrapped_native": "0x82af49447d8a07e3bd95bd0d56f35241523fbab1", "stables": {"0xaf88d065e77c8cc2239327c5edb3a432268e5831": "USDC"},
        "rpc": "https://arbitrum-one-rpc.publicnode.com", "router": "kyberswap", "kyber": "arbitrum", "goplus_id": "42161", "explorer": "https://arbiscan.io/token/",
        "launchpads": [], "typical_gas_usd": 0.05, "block_time_s": 0.25, "token_standards": ["ERC-20"], "status": "LOW-PRIORITY MONITORING",
    },
    "avalanche": {
        "name": "Avalanche", "tier": 2, "family": "evm", "chain_id": 43114, "gt_network": "avax", "llama": "Avalanche",
        "cg_platform": "avalanche", "cg_native": "avalanche-2", "cg_meme_category": None, "ds_chain": "avalanche",
        "native_symbol": "AVAX", "wrapped_native": "0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7", "stables": {"0xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e": "USDC"},
        "rpc": "https://avalanche-c-chain-rpc.publicnode.com", "router": "kyberswap", "kyber": "avalanche", "goplus_id": "43114", "explorer": "https://snowtrace.io/token/",
        "launchpads": ["arena"], "typical_gas_usd": 0.05, "block_time_s": 2, "token_standards": ["ERC-20"], "status": "LOW-PRIORITY MONITORING",
    },
    "polygon": {
        "name": "Polygon", "tier": 2, "family": "evm", "chain_id": 137, "gt_network": "polygon_pos", "llama": "Polygon",
        "cg_platform": "polygon-pos", "cg_native": "polygon-ecosystem-token", "cg_meme_category": None, "ds_chain": "polygon",
        "native_symbol": "POL", "wrapped_native": "0x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270", "stables": {"0x3c499c542cef5e3811e1192ce70d8cc03d5c3359": "USDC"},
        "rpc": "https://polygon-bor-rpc.publicnode.com", "router": "kyberswap", "kyber": "polygon", "goplus_id": "137", "explorer": "https://polygonscan.com/token/",
        "launchpads": [], "typical_gas_usd": 0.01, "block_time_s": 2, "token_standards": ["ERC-20"], "status": "LOW-PRIORITY MONITORING",
    },
    "hyperevm": {
        "name": "Hyperliquid (HyperEVM)", "tier": 2, "family": "evm", "chain_id": 999, "gt_network": "hyperevm", "llama": "Hyperliquid L1",
        "cg_platform": "hyperevm", "cg_native": "hyperliquid", "cg_meme_category": None, "ds_chain": "hyperevm",
        "native_symbol": "HYPE", "wrapped_native": "0x5555555555555555555555555555555555555555", "stables": {},
        "rpc": "https://rpc.hyperliquid.xyz/evm", "router": None, "kyber": None, "goplus_id": None, "explorer": "https://hyperevmscan.io/token/",
        "launchpads": [], "typical_gas_usd": 0.01, "block_time_s": 1, "token_standards": ["ERC-20"], "status": "LOW-PRIORITY MONITORING",
        "notes": "no GoPlus or KyberSwap coverage confirmed; contract risk and executable depth stay UNKNOWN until an adapter exists",
    },
    "sui": {
        "name": "Sui", "tier": 2, "family": "move", "chain_id": None, "gt_network": "sui-network", "llama": "Sui",
        "cg_platform": "sui", "cg_native": "sui", "cg_meme_category": "sui-meme", "ds_chain": "sui",
        "native_symbol": "SUI", "wrapped_native": "0x2::sui::SUI", "stables": {},
        "rpc": None, "router": None, "kyber": None, "goplus_id": "sui", "explorer": "https://suiscan.xyz/mainnet/coin/",
        "launchpads": ["movepump"], "typical_gas_usd": 0.01, "block_time_s": 0.5, "token_standards": ["Move coin"], "status": "LOW-PRIORITY MONITORING",
        "notes": "Sui fullnode RPC blocks browser CORS; only market-level data (GeckoTerminal, DefiLlama, CoinGecko) is available",
    },
}

TIER1 = [c for c, v in CHAINS.items() if v["tier"] == 1]
TIER2 = [c for c, v in CHAINS.items() if v["tier"] == 2]


def get(chain: str) -> dict[str, Any]:
    c = CHAINS.get(chain)
    if not c:
        raise KeyError(f"unknown chain {chain!r}; known: {', '.join(CHAINS)}")
    return {"id": chain, **c}


def by_gt_network(net: str) -> str | None:
    return next((k for k, v in CHAINS.items() if v["gt_network"] == net), None)


def by_llama(name: str) -> str | None:
    return next((k for k, v in CHAINS.items() if v["llama"].lower() == (name or "").lower()), None)


def by_ds_chain(name: str) -> str | None:
    return next((k for k, v in CHAINS.items() if v["ds_chain"] == name), None)


def family(chain: str) -> str:
    return CHAINS.get(chain, {}).get("family", "other")


def is_evm(chain: str) -> bool:
    return family(chain) == "evm"


def norm_address(chain: str, addr: str) -> str:
    """EVM addresses are case-insensitive; store and compare lowercase. Solana mints are case-sensitive base58."""
    return addr.lower() if is_evm(chain) and addr and addr[:2].lower() == "0x" else addr


def detect_chain(addr: str) -> str | None:
    """Only the address *shape* is inferable: 0x + 40 hex is EVM (chain still unknown); 32-44 base58 is Solana."""
    if not addr:
        return None
    if addr.startswith("0x") and len(addr) == 42:
        return "evm?"
    if 32 <= len(addr) <= 44 and all(c not in "0OIl" for c in addr):
        return "solana"
    return None


def sync(con) -> None:
    """Upsert the registry into the chains table without touching rotation-managed fields (research_allocation, status_reason)."""
    import json
    import time
    t = time.time()
    for cid, c in CHAINS.items():
        row = con.execute("SELECT chain_id FROM chains WHERE chain_id=?", (cid,)).fetchone()
        base = {"name": c["name"], "tier": c["tier"], "family": c["family"], "evm_chain_id": c.get("chain_id"), "gt_network": c["gt_network"], "llama_slug": c["llama"],
                "cg_platform": c.get("cg_platform"), "cg_native_id": c.get("cg_native"), "cg_meme_category": c.get("cg_meme_category"), "ds_chain": c["ds_chain"],
                "native_symbol": c["native_symbol"], "wrapped_native": c["wrapped_native"], "router": c.get("router"), "rpc_url": c.get("rpc"), "goplus_id": c.get("goplus_id"),
                "explorer": c.get("explorer"), "launchpads_json": json.dumps(c.get("launchpads") or []), "typical_gas_usd": c.get("typical_gas_usd"), "block_time_s": c.get("block_time_s"),
                "token_standards_json": json.dumps(c.get("token_standards") or []), "notes": c.get("notes"), "updated_at": t}
        if row is None:
            base.update({"chain_id": cid, "status": c["status"], "research_allocation": "FULL" if c["tier"] == 1 else "WATCHLIST", "first_seen_at": t})
            con.execute(f"INSERT INTO chains ({','.join(base)}) VALUES ({','.join('?' * len(base))})", list(base.values()))
        else:
            con.execute(f"UPDATE chains SET {','.join(k + '=?' for k in base)} WHERE chain_id=?", list(base.values()) + [cid])
