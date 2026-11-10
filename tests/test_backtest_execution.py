"""Phase 07: execution-aware DEX/AMM simulation (G09-G17, G29). Synthetic numbers; independent hand arithmetic."""
import random

import pytest

from memelab.backtest import execution as X

F0 = X.Fees(swap_fee=0.0, transfer_fee_bps=0, network_fee_sol=0.0)
F25 = X.Fees(swap_fee=0.0025, transfer_fee_bps=0, network_fee_sol=0.0)


# G09 static constant-product pool, hand-calculated
def test_g09_cpmm_hand_calculation_and_no_free_money():
    pool = X.CpmmPool(reserve_base=1_000_000.0, reserve_quote=100.0, fees=F25)
    f, p2 = pool.buy(1.0)
    # by hand: net = 1 * (1 - 0.0025) = 0.9975; out = 1_000_000 * 0.9975 / (100 + 0.9975) = 9876.457338...
    assert f.out == pytest.approx(997_500.0 / 100.9975, rel=1e-12)
    assert p2.reserve_base == pytest.approx(1_000_000 - 997_500.0 / 100.9975) and p2.reserve_quote == 101.0
    assert p2.reserve_base * p2.reserve_quote > pool.reserve_base * pool.reserve_quote      # fees grow k
    s, p3 = p2.sell(f.out)
    assert s.out < 1.0 and s.out > 0.99                                                     # no free money on a round trip
    assert p3.reserve_base > 0 and p3.reserve_quote > 0
    # integer form, as constant-product programs compute it: fee rounds up, output rounds down
    raw = X.cpmm_out_raw(100_000_000_000, 1_000_000_000_000, 1_000_000_000, 25, 10_000)
    assert raw == (1_000_000_000_000 * 997_500_000) // (100_000_000_000 + 997_500_000)
    assert abs(raw / 1e6 - f.out) < 1e-3                                                    # float and raw agree to 1 base unit
    with pytest.raises(ValueError):
        X.CpmmPool(0, 1)
    with pytest.raises(ValueError):
        pool.buy(-1)


# G10 own size changes the fill non-linearly
def test_g10_size_dependent_fills():
    pool = X.CpmmPool(reserve_base=50_000.0, reserve_quote=50_000.0, fees=F25)   # thin: $50k a side at $1
    rows = [X.round_trip(pool, s) for s in (1_000, 10_000, 100_000)]
    entry = [r["entry_impact"] for r in rows]
    exit_ = [r["exit_impact"] for r in rows]
    assert entry[0] < entry[1] < entry[2] and exit_[0] < exit_[1] < exit_[2]
    assert entry[2] > 10 * entry[0] and entry[1] > 5 * entry[0]                  # non-linear growth
    # selling a position worth $X at the current mid: proceeds per marked dollar fall non-linearly with X
    sells = [pool.sell(x / pool.mid)[0].out / x for x in (1_000, 10_000, 100_000)]
    assert sells[0] > sells[1] > sells[2] and sells[2] < 0.35
    # an immediate round trip in one constant-product pool mostly costs fees (impact unwinds): never a profit
    assert all(0 < r["loss_frac"] < 0.006 for r in rows)


# G11 same USD liquidity, different pool type: CLMM never gets the CPMM approximation
def test_g11_clmm_not_approximated_as_cpmm():
    assert X.classify_pool("CPMM", True, True, False) == X.EXACT_CPMM
    assert X.classify_pool("CPMM", False, True, False) == X.LIQ_SNAPSHOT_APPROX
    for t in ("CLMM", "DLMM", "BONDING_CURVE", "UNKNOWN"):
        assert X.classify_pool(t, False, True, False) == X.UNSUPPORTED_POOL
        assert X.classify_pool(t, False, True, True) == X.QUOTE_OBSERVED       # only an observed quote can price it
        assert X.classify_pool(t, True, True, False) == X.UNSUPPORTED_POOL     # vault balances of a CLMM/DLMM are not x*y=k reserves


# G12 pool drained between signal and order
def test_g12_execution_uses_state_at_execution_time():
    t_dec, t_exec = 1_800_000_000.0, 1_800_000_030.0
    full = X.CpmmPool(100_000.0, 100_000.0, F25)
    drained = X.CpmmPool(25_000.0, 25_000.0, F25)        # 75% withdrawn 10 s after the decision
    states = [(t_dec - 60, full), (t_dec + 10, drained)]
    p_exec, st = X.state_at(states, t_exec)
    assert st == "OBSERVED" and p_exec is drained
    f_exec, _ = p_exec.buy(5_000.0)
    f_ideal, _ = full.buy(5_000.0)
    assert f_exec.out < f_ideal.out * 0.9                 # modeled worse fill, not the idealized prior price
    assert X.state_at(states, t_dec - 3600)[1] == "MISSING"
    assert X.state_at(states, t_exec + 7200, max_age_s=600)[1] == "STALE"


# G13 partial route failure: only executable legs count, never phantom fills
def test_g13_route_failure_and_impact_cap():
    a, b = X.CpmmPool(40_000, 40_000, F25), X.CpmmPool(60_000, 60_000, F25)
    full, _ = X.route_sell([a, b], 10_000)
    degraded, _ = X.route_sell([a, b], 10_000, available=[False, True])
    assert full.status == X.FILLED and degraded.status == X.FILLED and degraded.out < full.out
    assert any("ROUTE_DEGRADED" in w for w in degraded.warnings)
    none, _ = X.route_sell([a, b], 10_000, available=[False, False])
    assert none.status == X.FAILED and none.out == 0 and none.filled_in == 0
    capped, _ = X.route_sell([a], 30_000, max_impact=0.10)
    assert capped.status == X.PARTIAL and 0 < capped.filled_in < 30_000 and capped.impact_frac <= 0.10 + 1e-9
    # two pools, no double counting: routing across both never beats the sum of liquidity being used once
    one_big = X.CpmmPool(100_000, 100_000, F25)
    split, _ = X.route_buy([a, b], 10_000)
    single, _ = one_big.buy(10_000)
    assert split.out <= single.out * (1 + 1e-6)


# G14 fees and decimals, each applied once
def test_g14_fee_stack_applied_once():
    fees = X.Fees(swap_fee=0.0025, transfer_fee_bps=500, network_fee_sol=0.0)
    deep = X.CpmmPool(1e12, 1e12, fees)                  # deep pool: impact ~0, isolates the fee stack
    b, p2 = deep.buy(1_000.0)
    assert b.out == pytest.approx(1_000 * 0.9975 * 0.95, rel=1e-6)          # swap fee then transfer fee on received tokens
    s, _ = p2.sell(b.out)
    assert s.out == pytest.approx(b.out * 0.95 * 0.9975, rel=1e-6)          # transfer fee into pool then swap fee
    rt = s.out / 1_000
    assert rt == pytest.approx((0.9975 * 0.95) ** 2, rel=1e-6)              # not (0.9975*0.95)**3, not 0.9975**2
    # a fee-authority increase before exit is visible in proceeds
    hiked = X.CpmmPool(p2.reserve_base, p2.reserve_quote, X.Fees(0.0025, 1500, None, 0.0))
    s2, _ = hiked.sell(b.out)
    assert s2.out < s.out * 0.9
    # capped transfer fee
    capped = X.Fees(0.0, 500, transfer_fee_max_tokens=10.0, network_fee_sol=0.0)
    assert capped.transfer_fee(1_000_000) == 10.0
    assert X.network_fee_usd(X.Fees(network_fee_sol=0.000105), 150.0, transactions=2) == pytest.approx(0.0315)
    with pytest.raises(ValueError):
        X.Fees(swap_fee=1.2)


def _curve(at=1_800_000_000.0, ttl=120):
    return X.QuoteCurve(side="SELL", quote_at=at, ttl_s=ttl, mid_price=1.0, points=((1_000, 990.0), (10_000, 9_500.0), (100_000, 80_000.0)))


# G15 stale or future quotes are never fills
def test_g15_quote_freshness():
    c = _curve()
    assert c.fill(5_000, c.quote_at + 60).status == X.FILLED
    assert c.fill(5_000, c.quote_at + 121).reason == "STALE_DATA"
    assert c.fill(5_000, c.quote_at - 1).reason == "QUOTE_FROM_THE_FUTURE"
    assert c.fill(200_000, c.quote_at + 1).reason.startswith("INSUFFICIENT_EXECUTION_DATA")
    f = c.fill(10_000, c.quote_at + 1)
    assert f.out == pytest.approx(9_500.0) and f.impact_frac == pytest.approx(0.05)


# G16 denominators: SOL/USD move and stablecoin depeg
def test_g16_denominators():
    r = X.pnl(cost_quote=1.0, proceeds_quote=1.1, quote_asset="SOL", rates_entry={"SOL": 150.0}, rates_exit={"SOL": 120.0})
    assert r["pnl_quote"] == pytest.approx(0.1) and r["pnl_usd"] == pytest.approx(132.0 - 150.0)
    u = X.pnl(cost_quote=1000.0, proceeds_quote=1000.0, quote_asset="USDC", rates_entry={"USDC": 1.0}, rates_exit={"USDC": 0.97})
    assert u["ret_quote"] == 0 and u["ret_usd"] == pytest.approx(-0.03)
    with pytest.raises(KeyError):
        X.to_usd(1.0, "SOL", {})                         # never a silent 1.0 or latest price


# G17 small size executes, the full position cannot exit within the cap
def test_g17_exit_capacity_limits_profit():
    pool = X.CpmmPool(100_000, 100_000, F25)
    cap = X.max_size(pool, max_exit_impact=0.03)
    assert 0 < cap < 5_000
    small = X.round_trip(pool, cap * 0.5)
    assert small["exit_impact"] <= 0.03
    position_tokens = 20_000
    f, _ = X.route_sell([pool], position_tokens, max_impact=0.03)
    assert f.status == X.PARTIAL and f.filled_in < position_tokens
    marked = position_tokens * pool.mid
    assert f.out < marked * 0.5                           # realizable value is far below the screen value


# G29 paired validation: float engine vs independent integer arithmetic on random cases
def test_g29_float_vs_integer_reference():
    rng = random.Random(29)
    for _ in range(500):
        rq = rng.randint(10**9, 10**13)          # lamports
        rb = rng.randint(10**9, 10**16)          # token base units
        amt = rng.randint(1, rq // 2)
        raw = X.cpmm_out_raw(rq, rb, amt, 25, 10_000)
        fl = X.CpmmPool(reserve_base=rb, reserve_quote=rq, fees=X.Fees(0.0025, 0, None, 0.0)).buy(amt)[0].out
        # the integer program rounds the fee up to a whole lamport: one lamport of input moves the output by at most rb/rq
        assert abs(fl - raw) <= rb / rq + 2 + abs(raw) * 1e-12, (rq, rb, amt, raw, fl)


def test_pumpswap_effective_reserves_change_the_price():
    vault_q, vault_b = 85.0, 200_000_000.0
    naive = X.CpmmPool(vault_b, vault_q, F25)
    eff = X.pumpswap_effective(vault_q, 17.6, vault_b, F25)
    assert eff.mid > naive.mid * 1.2
    with pytest.raises(ValueError):
        X.pumpswap_effective(10.0, -11.0, vault_b, F25)


def test_liquidity_snapshot_approx_is_labeled_and_haircut():
    p = X.pool_from_liquidity_snapshot(100_000.0, price_usd=0.5, quote_price_usd=150.0, fees=F25)
    assert p.basis == X.LIQ_SNAPSHOT_APPROX
    assert p.reserve_quote * 150.0 == pytest.approx(40_000.0) and p.reserve_base * 0.5 == pytest.approx(40_000.0)
    assert p.buy(10.0)[0].basis == X.LIQ_SNAPSHOT_APPROX


# ---------------- live spot-check on real PumpSwap pools (fixture from audits/backtesting/execution/p07_spotcheck.py) ----------------

def _spot():
    import json
    from pathlib import Path
    return json.loads((Path(__file__).parent / "fixtures" / "backtest" / "real" / "pumpswap_spotcheck.json").read_text())


def test_pumpswap_math_matches_live_quotes_with_effective_reserves_and_the_pool_fee_tier():
    for p in _spot()["pools"]:
        rb, rq = p["base_raw"], p["quote_vault_raw"] + p["virtual_quote_raw"]
        buys = [q for q in p["quotes"] if q["side"] == "BUY" and q["amm_key"] == p["pool"]]
        assert len(buys) == 3
        # the fee tier implied by the smallest buy (fee on input, effective reserves)
        q0 = buys[0]
        tier = 1 - (q0["jup_out_raw"] * rq / (rb - q0["jup_out_raw"])) / q0["in_raw"]
        tier_bps = round(tier * 10_000 / 5) * 5                        # tiers are whole 5 bp steps: 30, 55, 125 observed
        assert tier_bps in (30, 55, 125)
        for q in buys:
            model = X.cpmm_out_raw(rq, rb, q["in_raw"], tier_bps, 10_000)
            assert abs(model / q["jup_out_raw"] - 1) < 5e-4              # within 0.05% of the router's quote
        sell = next(q for q in p["quotes"] if q["side"] == "SELL")
        gross = rq * sell["in_raw"] / (rb + sell["in_raw"])
        assert abs((1 - sell["jup_out_raw"] / gross) - tier_bps / 10_000) < 3e-4   # same tier on the sell side


def test_pumpswap_vault_only_reserves_misprice_pools_with_large_virtual_reserves():
    p = next(p for p in _spot()["pools"] if abs(p["virtual_quote_raw"]) / p["quote_vault_raw"] > 0.005)
    rb = p["base_raw"]
    buy = next(q for q in p["quotes"] if q["side"] == "BUY")
    sell = next(q for q in p["quotes"] if q["side"] == "SELL")
    implied = lambda rq: (1 - (buy["jup_out_raw"] * rq / (rb - buy["jup_out_raw"])) / buy["in_raw"],
                          1 - sell["jup_out_raw"] / (rq * sell["in_raw"] / (rb + sell["in_raw"])))
    b, s = implied(p["quote_vault_raw"])
    assert abs(b - s) > 0.01                                            # vault-only: buy and sell disagree by over a point
    b, s = implied(p["quote_vault_raw"] + p["virtual_quote_raw"])
    assert abs(b - s) < 5e-4                                            # effective reserves: they agree


def test_assumed_fee_defaults_are_conservative_and_labeled():
    assert X.assumed_swap_fee("pumpswap") == (0.0125, "ASSUMED_UPPER_OBSERVED_TIER")
    assert X.assumed_swap_fee("pumpswap", observed=0.003) == (0.003, "OBSERVED")
    assert X.assumed_swap_fee("someday-dex")[1] == "ASSUMED_UNKNOWN_DEX"
