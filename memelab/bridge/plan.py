"""Fetch-plan builders for the browser bridge.

A plan is a JSON document {id, reqs:[{key,url,method,body,proj}]} that the in-browser collector executes.
Keys are prefixed by projection family (gt_pools, gt_info, gt_ohlcv, gt_trades, rug, jup_tok, jq, ds, ds_profiles, rpc).
The suffix after the family carries identifiers, e.g. "jq:BUY:1000:<mint>".
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..db import DATA_DIR

SOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
RPC = "https://solana-rpc.publicnode.com"
HELIUS_RPC = "https://mainnet.helius-rpc.com/?api-key={key}"
HELIUS_TX = "https://api.helius.xyz/v0/addresses/{addr}/transactions?api-key={key}&limit={limit}"


def rpc_url() -> str:
    """Helius RPC when a key is configured (data/config.json), otherwise the public endpoint."""
    try:
        from .github_inbox import load_config
        key = load_config().get("helius_api_key")
        return HELIUS_RPC.format(key=key) if key else RPC
    except Exception:
        return RPC
GT = "https://api.geckoterminal.com/api/v2/networks/solana"
JUP = "https://lite-api.jup.ag"
DS = "https://api.dexscreener.com"
RUG = "https://api.rugcheck.xyz/v1"
CG = "https://api.coingecko.com/api/v3"

DEFAULT_SIZES = [500, 1000, 2500, 5000, 10000, 25000, 50000, 100000]


class Plan:
    def __init__(self, plan_id: str | None = None):
        self.id = plan_id or f"plan_{int(time.time())}"
        self.reqs: list[dict[str, Any]] = []
        self.dedupe = False

    def add(self, key: str, url: str, method: str = "GET", body: Any = None, proj: str | None = None, delay_ms: int | None = None):
        r: dict[str, Any] = {"key": key, "url": url}
        if method != "GET":
            r["method"] = method
        if body is not None:
            r["body"] = body
        if proj:
            r["proj"] = proj
        if delay_ms:
            r["delayMs"] = delay_ms
        self.reqs.append(r)
        return self

    # ---- discovery universe ----
    def discovery(self, gt_pages: int = 3):
        for p in range(1, gt_pages + 1):
            self.add(f"gt_pools:trending:{p}", f"{GT}/trending_pools?page={p}&duration=1h")
        for p in range(1, gt_pages + 1):
            self.add(f"gt_pools:trending24:{p}", f"{GT}/trending_pools?page={p}&duration=24h")
        self.add("gt_pools:new:1", f"{GT}/new_pools?page=1")
        self.add("gt_pools:top24:1", f"{GT}/pools?page=1&sort=h24_volume_usd_desc")
        self.add("gt_pools:top6:1", f"{GT}/pools?page=1&sort=h6_volume_usd_desc")
        for iv in ("1h", "6h", "24h"):
            self.add(f"jup_disc:trending:{iv}", f"{JUP}/tokens/v2/toptrending/{iv}?limit=100")
            self.add(f"jup_disc:organic:{iv}", f"{JUP}/tokens/v2/toporganicscore/{iv}?limit=100")
        self.add("jup_disc:traded:24h", f"{JUP}/tokens/v2/toptraded/24h?limit=100")
        self.dedupe = True
        self.add("ds_profiles:latest", f"{DS}/token-profiles/latest/v1")
        self.add("ds_profiles:boosts", f"{DS}/token-boosts/top/v1")
        self.add("raw:rug_trending", f"{RUG}/stats/trending")
        self.add("raw:cg_sol", f"{CG}/simple/price?ids=solana,bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true&include_market_cap=true")
        return self

    # ---- per token structural pass (stage 2) ----
    def structural(self, mints: list[str], holders: bool = True):
        for i in range(0, len(mints), 30):
            chunk = mints[i:i + 30]
            self.add(f"ds:batch:{i}", f"{DS}/tokens/v1/solana/{','.join(chunk)}")
        for m in mints:
            self.add(f"jup_tok:{m}", f"{JUP}/tokens/v2/search?query={m}")
            self.add(f"rug:{m}", f"{RUG}/tokens/{m}/report", delay_ms=250)
            if holders:
                self.holders_full(m, pages=1)  # first 1,000 token accounts: enough for the wallet-farm check
        return self

    # ---- deep pass (stage 3-5) ----
    def deep(self, mint: str, pools: list[str], sizes: list[float] | None = None, sol_price: float | None = None,
             decimals: int = 6, price_usd: float | None = None, ohlcv_tfs=(("day", 1, 120), ("hour", 1, 400), ("minute", 15, 400))):
        sizes = sizes or DEFAULT_SIZES
        self.add(f"gt_info:{mint}", f"{GT}/tokens/{mint}/info")
        self.add(f"gt_pools:token:{mint}", f"{GT}/tokens/{mint}/pools?page=1")
        for pool in pools[:2]:
            for tf, agg, lim in ohlcv_tfs:
                self.add(f"gt_ohlcv:{pool}:{tf}{agg}", f"{GT}/pools/{pool}/ohlcv/{tf}?aggregate={agg}&limit={lim}&currency=usd&token={mint}")
            self.add(f"gt_trades:{pool}:all", f"{GT}/pools/{pool}/trades")
            self.add(f"gt_trades:{pool}:big", f"{GT}/pools/{pool}/trades?trade_volume_in_usd_greater_than=2000")
        if sol_price and price_usd:
            for usd in sizes:
                lamports = int(usd / sol_price * 1e9)
                self.add(f"jq:BUY:{usd}:{mint}", f"{JUP}/swap/v1/quote?inputMint={SOL}&outputMint={mint}&amount={lamports}&slippageBps=300")
                base_units = int(usd / price_usd * (10 ** decimals))
                self.add(f"jq:SELL:{usd}:{mint}", f"{JUP}/swap/v1/quote?inputMint={mint}&outputMint={SOL}&amount={base_units}&slippageBps=300")
        self.add(f"rpc:mint:{mint}", rpc_url(), "POST", {"jsonrpc": "2.0", "id": 1, "method": "getAccountInfo", "params": [mint, {"encoding": "jsonParsed"}]})
        return self

    def wallet_sigs(self, wallets: list[str], limit: int = 50):
        for w in wallets:
            self.add(f"rpc:sigs:{w}", rpc_url(), "POST", {"jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress", "params": [w, {"limit": limit}]}, delay_ms=400)
        return self

    def wallet_forensics(self, wallets: list[str], limit: int = 100):
        """Helius Enhanced Transactions per wallet (parsed swaps/transfers). Requires helius_api_key in config."""
        from .github_inbox import load_config
        key = load_config().get("helius_api_key")
        if not key:
            raise RuntimeError("helius_api_key missing in data/config.json")
        for w in wallets:
            self.add(f"helius_tx:{w}", HELIUS_TX.format(addr=w, key=key, limit=limit), proj="helius_tx", delay_ms=250)
        return self

    def holders_full(self, mint: str, pages: int = 3):
        """Helius DAS getTokenAccounts: complete holder list, 1000 per page."""
        for pg in range(1, pages + 1):
            self.add(f"helius_holders:{mint}:{pg}", rpc_url(), "POST", {"jsonrpc": "2.0", "id": 1, "method": "getTokenAccounts", "params": {"mint": mint, "page": pg, "limit": 1000}}, proj="raw", delay_ms=300)
        return self

    def wallet_txs(self, sigs: list[str]):
        for s in sigs:
            self.add(f"rpc:tx:{s}", RPC, "POST", {"jsonrpc": "2.0", "id": 1, "method": "getTransaction", "params": [s, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]}, delay_ms=400)
        return self

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"id": self.id, "reqs": self.reqs}
        if self.dedupe:
            d["dedupe"] = True
        return d

    def save(self, path: Path | None = None) -> Path:
        path = path or DATA_DIR / "inbox" / f"{self.id}.plan.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), separators=(",", ":")))
        return path

    def js_call(self) -> str:
        """The exact JS to paste into the browser tab after collector.js has been defined."""
        return f"await __ML.run({json.dumps(self.to_dict(), separators=(',', ':'))})"
