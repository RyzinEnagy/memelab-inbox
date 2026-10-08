"""Launch-source registry and fetch plans (verified from the browser bridge 2026-10-08).

Three plan groups because two launchpads answer only same-origin requests:
  example  : run on https://example.com/ (CORS-open APIs)
  pump     : run on https://frontend-api-v3.pump.fun/coins?limit=1   (pump.fun list, creator filter, coins-v2 per mint)
  clanker  : run on https://www.clanker.world/api/tokens            (Clanker list, deployed-by-address)
Gaps recorded in every report: four.meme is geo-restricted from the user's location (not circumvented); Moonshot, Meteora DBC,
Believe answer neither fetch nor navigation; no public launch calendar (CryptoRank, CoinMarketCap, CoinMarketCal) is reachable;
X, Telegram and Discord are not readable without accounts.
"""
from __future__ import annotations

from ..bridge.plan import Plan

PUMP = "https://frontend-api-v3.pump.fun"
RAY = "https://launch-mint-v1.raydium.io"
CLANKER = "https://www.clanker.world"
GT = "https://api.geckoterminal.com/api/v2"
JUP = "https://lite-api.jup.ag"
RUG = "https://api.rugcheck.xyz/v1"
DS = "https://api.dexscreener.com"

GROUP_PAGES = {"example": "https://example.com/", "pump": f"{PUMP}/coins?offset=0&limit=1", "clanker": f"{CLANKER}/api/tokens?sort=desc&page=1"}

SOURCES = [
    # (source_id, chain, platform, what it gives, identity state(s) it can establish)
    ("pump:new", "solana", "pump.fun", "newest bonding-curve launches with creator, reserves, replies, livestream flag", "C/E"),
    ("pump:mcap", "solana", "pump.fun", "highest-cap curves (near graduation) and freshly migrated tokens", "C/E"),
    ("pump:grad", "solana", "pump.fun", "recently traded graduated tokens (survivorship-biased cohort sample)", "E"),
    ("pump:live", "solana", "pump.fun", "tokens with an active creator livestream", "C/E"),
    ("ray:new", "solana", "raydium-launchlab", "newest LaunchLab/Bonk.fun launches with supply, curve progress, locked/vesting allocation", "C/E"),
    ("ray:hot", "solana", "raydium-launchlab", "LaunchLab curves by market cap (near migration)", "C/E"),
    ("jup:recent", "solana", None, "tokens whose first pool was just created, with launchpad, dev, audit and 5m-24h stats", "E"),
    ("rug:new", "solana", None, "newest mints seen by RugCheck (may have no market yet)", "B"),
    ("clanker:new", "base", "clanker", "newest Clanker deployments: deployer, starting cap, LP locker, vault/airdrop/sniper-tax extensions", "E"),
    ("zora:new", "base", "zora", "newest Zora coins (trade from creation on Uniswap v4)", "E"),
    ("virt:genesis", "base", "virtuals", "Virtuals Genesis launches with scheduled start times", "A/B"),
    ("gt:new:solana", "solana", None, "newest pools on Solana", "E"),
    ("gt:new:base", "base", None, "newest pools on Base", "E"),
    ("gt:new:bsc", "bsc", None, "newest pools on BNB Chain (four.meme graduations appear here)", "E"),
    ("ds:profiles", None, None, "newest DEX Screener profiles (a paid listing: promotion signal, not organic interest)", "E"),
    ("catalyst:launch", None, None, "news and catalyst events announcing a launch, TGE, airdrop or presale with no verified contract", "A"),
    ("manual", None, None, "launches you add with `launch note` (claimed details stay CLAIMED until verified)", "A/B"),
]
GAPS = ["four.meme (BNB launchpad): access restricted from your location; BNB launches are seen only after they reach PancakeSwap",
        "Moonshot, Meteora DBC, Believe: no browser-readable API",
        "Clanker (Base): clanker.world reset the connection from your browser's network on 2026-10-08; Base launches come from Zora and GeckoTerminal new pools until it answers again",
        "launch calendars (CryptoRank, CoinMarketCap, CoinMarketCal): not reachable; scheduled launches come from Virtuals Genesis, news, and manual notes",
        "X, Telegram, Discord: not readable without accounts; follower growth, group growth and post velocity stay UNKNOWN"]


def discovery(plan_id: str) -> dict[str, Plan]:
    ex = Plan(plan_id + "_ex")
    ex.add("jup:recent", f"{JUP}/tokens/v2/recent", proj="jup_tok")
    ex.add("rug:new", f"{RUG}/stats/new_tokens", proj="raw")
    ex.add("ray:new", f"{RAY}/get/list?sort=new&size=100&mintType=default&includeNsfw=false", proj="ray_list")
    ex.add("ray:hot", f"{RAY}/get/list?sort=marketCap&size=60&mintType=default&includeNsfw=false", proj="ray_list")
    ex.add("zora:new", "https://api-sdk.zora.engineering/explore?listType=NEW&count=50", proj="zora_new")
    ex.add("virt:genesis", "https://api.virtuals.io/api/geneses?pagination[pageSize]=25&sort[0]=startsAt%3Adesc", proj="virt_gen")
    for net in ("solana", "base", "bsc"):
        ex.add(f"gt_pools:{net}:new:1", f"{GT}/networks/{net}/new_pools?page=1", proj="gt_pools")
    ex.add("ds_profiles:latest", f"{DS}/token-profiles/latest/v1", proj="ds_profiles")
    ex.add("ds_boosts:latest", f"{DS}/token-boosts/latest/v1", proj="ds_boosts")
    ex.add("cg_price", "https://api.coingecko.com/api/v3/simple/price?ids=solana,ethereum,binancecoin&vs_currencies=usd", proj="raw")
    pu = Plan(plan_id + "_pump")
    q = "includeNsfw=false"
    pu.add("pump:new", f"{PUMP}/coins?offset=0&limit=100&sort=created_timestamp&order=DESC&{q}", proj="pump_coins")
    pu.add("pump:mcap", f"{PUMP}/coins?offset=0&limit=100&sort=market_cap&order=DESC&{q}&complete=false", proj="pump_coins")
    pu.add("pump:grad", f"{PUMP}/coins?offset=0&limit=50&sort=last_trade_timestamp&order=DESC&{q}&complete=true", proj="pump_coins")
    pu.add("pump:live", f"{PUMP}/coins/currently-live?limit=50&offset=0&{q}", proj="pump_coins")
    cl = Plan(plan_id + "_clanker")
    cl.add("clanker:new:1", f"{CLANKER}/api/tokens?sort=desc&page=1", proj="clanker_list")
    cl.add("clanker:new:2", f"{CLANKER}/api/tokens?sort=desc&page=2", proj="clanker_list")
    return {"example": ex, "pump": pu, "clanker": cl}


def deep(plan_id: str, cands: list[dict], helius: bool = False) -> dict[str, Plan]:
    """Per-shortlist research: creator history, current coin state, holders/insiders, early trades, minute candles, EVM contract checks."""
    ex, pu, cl = Plan(plan_id + "_ex"), Plan(plan_id + "_pump"), Plan(plan_id + "_clanker")
    for c in cands:
        mint, chain, creator, pad = c["contract"], c["chain"], c.get("creator"), c.get("launchpad")
        if not mint:
            continue
        if chain == "solana":
            ex.add(f"rug:{mint}", f"{RUG}/tokens/{mint}/report", proj="rug", delay_ms=300)
            ex.add(f"jup_tok:{mint}", f"{JUP}/tokens/v2/search?query={mint}", proj="jup_tok")
            ex.add(f"gt_pools:token:{mint}", f"{GT}/networks/solana/tokens/{mint}/pools?page=1", proj="gt_pools")
            if pad == "pump.fun":
                pu.add(f"pump:coin:{mint}", f"{PUMP}/coins-v2/{mint}", proj="pump_coin")
                if creator:
                    pu.add(f"pump:creator:{creator}", f"{PUMP}/coins?offset=0&limit=50&creator={creator}&includeNsfw=true", proj="pump_coins")
            if pad == "raydium-launchlab" and creator:
                ex.add(f"ray:user:{creator}", f"{RAY}/get/by/user?wallet={creator}&size=50", proj="ray_list")
        else:
            from ..chains import plan as CP, registry as R
            cfg = R.get(chain)
            ex.add(f"gt_pools:token:{mint}", f"{GT}/networks/{cfg['gt_network']}/tokens/{mint}/pools?page=1", proj="gt_pools")
            ex.add(f"ds:{chain}:one:{mint}", f"{DS}/tokens/v1/{cfg['ds_chain']}/{mint}", proj="ds")
            if cfg.get("goplus_id"):
                ex.add(f"goplus:{chain}:{mint}", f"{CP.GOPLUS}/{cfg['goplus_id']}?contract_addresses={mint}", proj="goplus")
            if cfg.get("chain_id"):
                ex.add(f"hp:{chain}:{mint}", f"{CP.HP}?address={mint}&chainID={cfg['chain_id']}", proj="hp")
            if pad == "clanker" and creator:
                cl.add(f"clanker:deployer:{creator}", f"{CLANKER}/api/tokens/fetch-deployed-by-address?address={creator}&page=1", proj="clanker_list")
        pool = c.get("pool") or c.get("curve_pool")
        if pool:
            net = {"solana": "solana", "base": "base", "bsc": "bsc"}.get(chain, chain)
            ex.add(f"gt_trades:{pool}:all", f"{GT}/networks/{net}/pools/{pool}/trades", proj="gt_trades")
            ex.add(f"gt_ohlcv:{pool}:minute1", f"{GT}/networks/{net}/pools/{pool}/ohlcv/minute?aggregate=1&limit=1000&currency=usd&token={mint}", proj="gt_ohlcv")
            ex.add(f"gt_ohlcv:{pool}:minute5", f"{GT}/networks/{net}/pools/{pool}/ohlcv/minute?aggregate=5&limit=1000&currency=usd&token={mint}", proj="gt_ohlcv")
    return {"example": ex, "pump": pu, "clanker": cl}


def cohort_followup(plan_id: str, mints: list[str]) -> Plan:
    """Re-read cohort tokens (pump.fun coins-v2) to measure 24h / 7d / 30d outcomes for comparable-launch distributions."""
    p = Plan(plan_id + "_pump")
    for m in mints:
        p.add(f"pump:coin:{m}", f"{PUMP}/coins-v2/{m}", proj="pump_coin", delay_ms=150)
    return p
