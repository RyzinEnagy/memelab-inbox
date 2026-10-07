import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("MEMELAB_DB", "/tmp/memelab_test_eco.sqlite")

from memelab import db
from memelab.chains import regime, rotation, narrative, emerging, report, registry

T = time.time()


def chart(start, end, n=91):
    return {"prices": [[(T - (n - i) * 86400) * 1000, start + (end - start) * i / (n - 1)] for i in range(n)], "volumes": [], "mcaps": []}


def pool(name, net, reserve=300_000, vol=500_000, buyers=400, sellers=300, created_h=48, fdv=5e6, dex="uniswap-v3"):
    import datetime
    return {"pool": "0x" + str(abs(hash(name + net)))[:38].ljust(40, "0"), "name": f"{name} / WETH", "net": net, "dex": dex, "created": datetime.datetime.fromtimestamp(T - created_h * 3600, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "base": "0x" + str(abs(hash(name)))[:38].ljust(40, "1"), "price": 0.01, "fdv": fdv, "mcap": fdv, "reserve": reserve, "chg": {"h1": 1, "h6": 2, "h24": 5}, "tx": {"h24": [900, 800, buyers, sellers], "h1": [50, 40, 30, 20]}, "vol": {"h1": vol / 24, "h6": vol / 4, "h24": vol}}


def bodies():
    b = {"cg_chart:bitcoin": chart(60000, 83000), "cg_chart:ethereum": chart(2000, 2600), "cg_chart:solana": chart(90, 117), "cg_chart:binancecoin": chart(600, 770),
         "cg_global": {"total_mcap": 2.8e12, "mcap_chg_24h": 1.2, "btc_dom": 58.0}, "hl_meta": {"BTC": {"funding": 0.0000125, "oi": 50000, "mark": 83000}, "ETH": {"funding": 0.00001, "oi": 600000, "mark": 2600}, "SOL": {"funding": 0.00002, "oi": 3000000, "mark": 117}},
         "llama_stables": [["Solana", 16e9], ["Base", 5e9], ["BSC", 13e9], ["Ethereum", 146e9]], "llama_chains": [["Solana", 6.4e9], ["Base", 6.2e9], ["BSC", 5.6e9], ["Ethereum", 52e9], ["Monad", 1.0e9], ["Robinhood Chain", 1.0e9]],
         "cg_cat": [{"id": "meme-token", "name": "Meme", "market_cap": 33e9, "market_cap_change_24h": 6.0, "volume_24h": 3.4e9, "top_3_coins_id": ["dogecoin"]}, {"id": "base-meme-coins", "name": "Base Meme", "market_cap": 3e8, "market_cap_change_24h": 30.0, "volume_24h": 4e8, "top_3_coins_id": ["brett"]},
                    {"id": "real-world-assets-rwa", "name": "Real World Assets (RWA)", "market_cap": 7e10, "market_cap_change_24h": 1, "volume_24h": 1e9, "top_3_coins_id": []}],
         "cg_mkts:meme-token:1": [{"id": f"m{i}", "symbol": f"M{i}", "name": f"Doge Cat {i}", "market_cap": 1e7 * (i + 1) ** 3, "total_volume": 1e6 * (i + 1), "price_change_percentage_24h": 8 - i, "p7d": 10 - i} for i in range(12)],
         "cg_mkts:solana-meme-coins:1": [{"id": f"s{i}", "symbol": f"S{i}", "name": f"Sol Dog {i}", "market_cap": 2e7 * (i + 1), "total_volume": 2e6, "price_change_percentage_24h": -5 + i} for i in range(6)],
         "cg_mkts:base-meme-coins:1": [{"id": f"b{i}", "symbol": f"B{i}", "name": f"Based Frog {i}", "market_cap": 1e7 * (i + 1), "total_volume": 3e6, "price_change_percentage_24h": 12 + i} for i in range(6)],
         "cg_price": {"solana": {"usd": 117, "usd_24h_change": 1.0}, "ethereum": {"usd": 2600, "usd_24h_change": -1.0}, "binancecoin": {"usd": 770, "usd_24h_change": 0.5}},
         "gt_xnet:1": {"pools": [pool(f"X{i}", "robinhood") for i in range(7)] + [pool(f"Y{i}", "solana") for i in range(5)] + [pool("Z", "base")], "networks": [["robinhood", "Robinhood"], ["solana", "Solana"], ["base", "Base"]]},
         "gt_nets": [["solana", "Solana"], ["base", "Base"], ["robinhood", "Robinhood"]], "ds_boosts": [{"chainId": "base", "tokenAddress": "0x1"}], "ds_profiles:latest": [{"chainId": "solana", "tokenAddress": "A"}]}
    for cid, cfg in registry.CHAINS.items():
        net = cfg["gt_network"]
        scale = {"solana": 1.0, "base": 0.8, "bsc": 0.6}.get(cid, 0.1)
        b[f"llama_dex:{cid}"] = {"total24h": 2e9 * scale, "chart": [[T - (40 - i) * 86400, (1.6e9 + 1e7 * i) * scale] for i in range(40)], "protocols": [["DexA", 1e9, 5]]}
        b[f"gt_pools:{net}:trending:1"] = {"pools": [pool(f"T{i}{cid}", net, reserve=2e5 + 1e5 * i, vol=(1e6 + 1e5 * i) * scale, buyers=int(500 * scale) + 300, sellers=int(400 * scale) + 250) for i in range(20)]}
        b[f"gt_pools:{net}:new:1"] = {"pools": [pool(f"N{i}{cid}", net, reserve=20_000, created_h=i * 2, dex="pump-fun" if cid == "solana" else "uniswap-v4") for i in range(20)]}
    return b


def test_regime_rotation_narrative_emerging_end_to_end():
    db.init_db()
    b = bodies()
    reg = regime.compute(b, T)
    assert reg["regime"] in ("RISK-ON", "NEUTRAL") and reg["confidence"] in ("HIGH", "MODERATE")
    assert reg["coins"]["BTC"]["trend"] == "UP"
    rot = rotation.compute(b, T)
    chains = rot["chains"]
    assert all(0 <= s["soi"] <= 100 for s in chains.values())
    assert chains["solana"]["soi"] > chains["polygon"]["soi"]
    comp = chains["base"]["components"]
    assert abs(sum(c["points"] for c in comp.values()) - chains["base"]["soi"]) < 0.2 and set(comp) == {"dex_activity", "meme_activity", "participation", "capital_flows", "attention", "opportunity_quality"}
    # unknown parts earn zero and are listed, never redistributed
    unk = [u for u in chains["solana"]["components"]["capital_flows"]["unknowns"]]
    assert any("previous snapshot" in u for u in unk)
    assert chains["solana"]["trend"] == "UNKNOWN" and "first measurement" in chains["solana"]["statement"]
    assert chains["solana"]["research_allocation"] in ("FULL", "PARTIAL", "WATCHLIST")
    nar = narrative.compute(b, T)
    names = [n["name"] for n in nar["narratives"]]
    assert "Base Meme" in names and "Real World Assets (RWA)" not in names
    base_meme = next(n for n in nar["narratives"] if n["name"] == "Base Meme")
    assert base_meme["lifecycle"] == "MANIA"  # +30% in 24h and volume/mcap > 1
    assert any(n["source"] == "keyword" for n in nar["narratives"])
    em = emerging.detect(b, T)
    rob = next(c for c in em["candidates"] if c["name"] == "Robinhood")
    assert rob["level"] == "BUILD PARTIAL" and rob["trending_pools"] == 7
    lp = emerging.launchpads(b, T)
    pf = next(r for r in lp["rows"] if r["launchpad_id"] == "solana:pump.fun")
    assert pf["new_pools_sample"] == 20
    bk = emerging.benchmark_baskets(b, T)
    assert bk["buckets"]["MICRO"]["n"] >= 1
    md = report.render(reg, rot, nar, em, lp, bk, when=T)
    for h in ("# MARKET REGIME", "# CHAIN ROTATION", "# NARRATIVE ROTATION", "# EMERGING CHAINS", "# CHAINS BEING DE-EMPHASIZED", "# WHAT WOULD CHANGE THE CURRENT ECOSYSTEM VIEW"):
        assert h in md
    # second run: trend becomes measurable and reruns at the same t stay idempotent
    rot2 = rotation.compute(b, T + 7200)
    assert rot2["chains"]["solana"]["trend"] in ("FLAT", "RISING", "FALLING")
    with db.connect() as con:
        n1 = con.execute("SELECT COUNT(*) FROM chain_scores WHERE observed_at=?", (T,)).fetchone()[0]
        rotation.compute(b, T)
        n2 = con.execute("SELECT COUNT(*) FROM chain_scores WHERE observed_at=?", (T,)).fetchone()[0]
    assert n1 == n2 == len(registry.CHAINS)
