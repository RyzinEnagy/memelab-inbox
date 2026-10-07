from memelab import wallet as W

A = "EGqWiy5bCjtvFgC8kU9AAr9P6FVE7aC6hDboCbRwoS8R"
M = "98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump"

def test_positions_from_wallet_synthetic():
    bodies = {
        f"rpc:bal:{A}": {"result": {"value": 1_500_000_000}},
        f"rpc:toks:{A}": {"result": {"value": [{"account": {"data": {"parsed": {"info": {"mint": M, "tokenAmount": {"uiAmount": 1000.0, "decimals": 6}}}}}}]}},
        f"rpc:toks22:{A}": {"result": {"value": []}},
        f"helius_tx:{A}": [
            {"sig": "s1", "ts": 1, "type": "SWAP", "src": "JUPITER", "fee": 5000, "payer": A, "nt": [[A, "pool", 0.5]], "tt": [["pool", A, M, 1000.0]]},
        ],
    }
    w = W.positions_from_wallet(A, bodies, prices={M: 0.005}, sol_price=120.0)
    assert w["balances"]["sol"] == 1.5
    assert len(w["positions"]) == 1
    p = w["positions"][0]
    assert p["mint"] == M and p["tokens"] == 1000.0
    assert abs(p["entry_price"] - 0.06) < 1e-9          # 0.5 SOL * $120 / 1000 tokens
    assert abs(p["current_value_usd"] - 5.0) < 1e-9
    assert any("inferred" in x for x in w["inferences"])

def test_empty_wallet():
    bodies = {f"rpc:bal:{A}": {"result": {"value": 15440823}}, f"rpc:toks:{A}": {"result": {"value": []}}, f"rpc:toks22:{A}": {"result": {"value": []}}}
    w = W.positions_from_wallet(A, bodies, sol_price=120.8)
    assert w["positions"] == [] and abs(w["balances"]["sol"] - 0.015440823) < 1e-12
