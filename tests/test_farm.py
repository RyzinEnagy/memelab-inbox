from memelab import farm

MINT = "FarmMint1111111111111111111111111111111pump"


def _bodies(n_farm, bal, n_other=40, supply_tokens=1_000_000_000, dec=6, rug_risks=(), liq=900_000, mcap=440_000_000):
    accts = [{"owner": f"F{i}", "amount": bal * 10 ** dec} for i in range(n_farm)]
    accts += [{"owner": f"O{i}", "amount": (1000 + i) * 10 ** dec} for i in range(n_other)]
    accts.append({"owner": "POOL", "amount": 2_000_000 * 10 ** dec})
    return {
        f"helius_holders:{MINT}:1": {"result": {"token_accounts": accts}},
        f"rug:{MINT}": {"token": {"decimals": dec, "supply": supply_tokens * 10 ** dec}, "markets": [{"pubkey": "POOL"}],
                        "risks": [{"name": r} for r in rug_risks], "creator": "DEV"},
        f"jup_tok:{MINT}": [{"liquidity": liq, "mcap": mcap, "dev": "DEV", "decimals": dec}],
    }


def test_farm_detected_and_fatal():
    r = farm.detect(MINT, _bodies(1500, 497_983))
    assert r["status"] == "DETECTED" and r["fatal"] and r["group_wallets"] == 1500
    assert 70 < r["share_pct"] < 80


def test_normal_distribution_not_flagged():
    r = farm.detect(MINT, _bodies(0, 0, n_other=900))
    assert r["status"] == "NOT DETECTED" and not r["fatal"]


def test_dust_group_ignored():
    b = _bodies(0, 0)
    b[f"helius_holders:{MINT}:1"]["result"]["token_accounts"] += [{"owner": f"D{i}", "amount": 10} for i in range(500)]
    assert farm.detect(MINT, b)["status"] == "NOT DETECTED"


def test_rug_pattern_with_dev_paid_accounts_is_suspected():
    b = _bodies(0, 0, rug_risks=("High holder correlation", "High market cap per holder"))
    del b[f"helius_holders:{MINT}:1"]
    for i in range(6):
        b[f"helius_tx:W{i}"] = [{"type": "INITIALIZE_ACCOUNT", "payer": "DEV"}]
    r = farm.detect(MINT, b)
    assert r["status"] == "SUSPECTED" and r["fatal"] and r["dev_paid_accounts"] == 6
