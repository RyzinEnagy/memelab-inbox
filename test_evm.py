import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("MEMELAB_DB", "/tmp/memelab_test_evm.sqlite")

from memelab import db, pipeline
from memelab.chains import evm, registry

ADDR = "0x532f27101965dd16442e59d40670faf5ebb142e4"
POOL = "0x76bf0abd20f1e0155ce40a62615a90a709a6c3d8"


def bodies(honeypot=False, owner_live=False, tax_mod=False):
    return {
        f"ds:base:one:{ADDR}": [{"chainId": "base", "dexId": "uniswap", "pairAddress": POOL.upper(), "baseToken": {"address": ADDR.upper(), "name": "Brett", "symbol": "BRETT"},
                                 "quoteToken": {"address": "0x4200000000000000000000000000000000000006", "symbol": "WETH"}, "priceUsd": "0.05", "liquidity": {"usd": 5_000_000, "base": 1, "quote": 1},
                                 "volume": {"h24": 3_000_000, "h1": 100_000}, "txns": {"h24": {"buys": 1000, "sells": 900}, "h1": {"buys": 50, "sells": 40}}, "fdv": 500_000_000, "marketCap": 495_000_000,
                                 "pairCreatedAt": int((time.time() - 400 * 86400) * 1000), "info": {"websites": [{"url": "https://brett.example"}], "socials": [{"type": "twitter", "url": "https://x.com/brett"}]}}],
        f"gt_info:{ADDR}": {"address": ADDR, "name": "Brett", "symbol": "BRETT", "decimals": 18, "holders": {"count": 300000}},
        f"goplus:base:{ADDR}": {ADDR: {"token_name": "Brett", "token_symbol": "BRETT", "holder_count": "300000", "total_supply": "9910000000", "is_open_source": "1", "is_proxy": "0", "is_mintable": "0",
                                      "owner_address": "0x1111111111111111111111111111111111111111" if owner_live else "0x000000000000000000000000000000000000dead", "owner_percent": "0.0",
                                      "hidden_owner": "0", "can_take_back_ownership": "0", "buy_tax": "0", "sell_tax": "0", "transfer_pausable": "0", "is_blacklisted": "0", "is_honeypot": "1" if honeypot else "0",
                                      "slippage_modifiable": "1" if tax_mod else "0", "is_in_dex": "1", "lp_holder_count": "3000",
                                      "dex": [{"name": "UniswapV3", "liquidity": "5000000", "pair": POOL}],
                                      "holders": [{"address": POOL, "percent": "0.12", "is_contract": 1, "is_locked": 0, "tag": "UniswapV3"}, {"address": "0xaaaa000000000000000000000000000000000001", "percent": "0.05", "is_contract": 0, "is_locked": 0}],
                                      "lp_holders": [{"address": "0x000000000000000000000000000000000000dead", "percent": "0.6", "is_locked": 1}, {"address": "0xbbbb000000000000000000000000000000000001", "percent": "0.3", "is_locked": 0}]}},
        f"hp:base:{ADDR}": {"honeypotResult": {"isHoneypot": honeypot, "honeypotReason": "sell reverted" if honeypot else None}, "simulationSuccess": True, "sim": {"buyTax": 0.0, "sellTax": 0.0, "buyGas": "150000", "sellGas": "170000"},
                            "token": {"name": "Brett", "symbol": "BRETT", "decimals": 18, "totalHolders": 300000}, "contract": {"openSource": True, "isProxy": False}, "flags": []},
        f"rpc_evm:base:owner:{ADDR}": {"result": "0x000000000000000000000000" + ("1111111111111111111111111111111111111111" if owner_live else "000000000000000000000000000000000000dead")},
        f"rpc_evm:base:decimals:{ADDR}": {"result": "0x12"}, f"rpc_evm:base:totalSupply:{ADDR}": {"result": hex(9910000000 * 10 ** 18)}, f"rpc_evm:base:code:{ADDR}": {"result": "0x60806040" + "00" * 500},
        **{f"kq:base:{side}:{usd}:{ADDR}": {"amountIn": str(int(usd / 4000 * 1e18)) if side == "BUY" else str(int(usd / 0.05 * 1e18)), "amountOut": str(int(usd / 0.05 * 1e18 * (1 - usd / 2e6))) if side == "BUY" else str(int(usd / 4000 * 1e18 * (1 - usd / 2e6))),
                                             "amountInUsd": usd, "amountOutUsd": usd * (1 - usd / 2e6), "gasUsd": 0.03, "route": [[["0xpool", "uniswapv3", "v3", ADDR, "0x4200000000000000000000000000000000000006", "1", "1"]]]}
           for side in ("BUY", "SELL") for usd in (500, 1000, 5000, 25000, 100000)},
    }


def test_evm_bundle_shape_and_mechanics():
    db.init_db()
    b = evm.build_bundle("base", ADDR.upper(), bodies(), native_price=4000)
    assert b["mint"] == ADDR and b["chain"] == "base"
    assert b["identity"]["symbol"] == "BRETT" and b["identity"]["name_matches"] is True and b["identity"]["sources_agreeing"] >= 3
    assert b["pools"][0]["pool"] == POOL  # 0.6 locked of 0.9 covered -> 66.7%
    assert abs(b["pools"][0]["lp"]["locked_pct"] - 66.67) < 0.1
    assert b["quotes"]["SELL"][100000.0]["status"] == "OK" and b["quotes"]["SELL"][100000.0]["impact"] > b["quotes"]["SELL"][500.0]["impact"]
    m = evm.mechanics(b)
    assert m["contract_risk"] == "LOW" and m["owner_state"] == "RENOUNCED" and not m["flags"]
    assert m["mint_authority_active"] is False and m["transfer_fee_bps"] == 0
    ident = evm.identity(b)
    assert ident["confidence"] == "HIGH" and ident["status"] == "OK"


def test_evm_fatal_paths():
    b = evm.build_bundle("base", ADDR, bodies(honeypot=True), native_price=4000)
    m = evm.mechanics(b)
    assert m["contract_risk"] == "FATAL" and "HONEYPOT" in m["flags"]
    b2 = evm.build_bundle("base", ADDR, bodies(owner_live=True, tax_mod=True), native_price=4000)
    m2 = evm.mechanics(b2)
    assert m2["owner_state"] == "ACTIVE" and "TAX_MODIFIABLE" in m2["flags"] and m2["contract_risk"] == "HIGH"
    from memelab.modules import m24_opportunity_ranker as m24
    flags = {f["flag"] for f in m24.fatal_flags(mechanics=m2)}
    assert "TAX_MODIFIABLE_BY_OWNER" in flags


def test_pipeline_runs_evm_token():
    r = pipeline.analyze_token(ADDR, bodies(), chain="base", native_price=4000, persist=True)
    assert r["bundle"]["chain"] == "base" and r["modules"]["identity"]["confidence"] == "HIGH"
    assert r["modules"]["mechanics"]["contract_risk"] == "LOW" and r["modules"]["execution"]["router"] == "kyberswap"
    assert r["modules"]["depth"].get("exit_capacity_usd_3pct")
    assert "REJECTED" != r["status"]["status"] or r["score"]["fatal_flags"] == []
    with db.connect() as con:
        row = con.execute("SELECT chain, token_standard, primary_pool FROM tokens WHERE mint=?", (ADDR,)).fetchone()
    assert tuple(row) == ("base", "ERC-20", POOL)
    assert "CHAIN" in r["report_md"] or "base" in r["report_md"].lower()
