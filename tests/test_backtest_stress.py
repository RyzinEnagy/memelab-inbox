"""Phase 12: adversarial position and opportunity stress engine (G12, G17, G25, G30, G31, G35). Synthetic snapshots."""
import json

from memelab.backtest import stress as S

T = 1_800_000_000.0


def snap(**kw):
    base = dict(chain="solana", mint="SNAP", as_of=T, price_usd=0.01, liquidity_usd=200_000.0, sol_usd=150.0, invalidation_price=0.008,
                concentrated_pct=30.0, circulating_tokens=1e9)
    base.update(kw)
    return S.Snapshot(**base)


def by(rep, sid, size):
    return next(r for r in rep["scenarios"] if r["scenario"] == sid and r["size_usd"] == size)


def test_g12_g30_shocks_degrade_and_stay_coherent():
    rep = S.stress(snap(), [500, 5_000, 50_000])
    for size in (500, 5_000, 50_000):
        base, l75, worst = by(rep, "BASE", size), by(rep, "LIQ_75", size), by(rep, "COMBINED_WORST", size)
        assert l75["proceeds_usd"] < base["proceeds_usd"] and worst["proceeds_usd"] <= l75["proceeds_usd"]
    for r in rep["scenarios"]:
        if "proceeds_usd" in r:
            assert r["proceeds_usd"] >= 0 and r["ret"] >= -1.0          # no negative or impossible outputs
    assert rep["probabilities"].startswith("NOT_ASSIGNED")
    assert all(r["hypothetical"] for r in rep["scenarios"] if r["scenario"] != "BASE")


def test_g25_gap_loss_exceeds_planned_stop():
    s = snap()
    rep = S.stress(s, [1_000])
    planned = 1 - s.invalidation_price / s.price_usd                    # 20% planned risk
    gap = by(rep, "STOP_GAP", 1_000)
    assert -gap["ret"] > planned


def test_g17_g35_realizable_below_marked_and_capacity():
    thin = snap(liquidity_usd=20_000.0)
    rep = S.stress(thin, [500, 10_000], max_loss_usd=300, max_exit_impact=0.05)
    big = by(rep, "BASE", 10_000)
    assert big["realizable_vs_marked"] < 0.8                            # screen value is not cash
    small = by(rep, "BASE", 500)
    assert small["realizable_vs_marked"] > big["realizable_vs_marked"]
    assert rep["max_size"]["max_size_usd"] < 10_000


def test_fatal_flag_never_positive_and_clmm_and_missing_inputs():
    assert S.stress(snap(fatal_flags=["LP_RISK_CRITICAL"]), [500])["decision"] == "RISK_FATAL_FLAW"
    cl = S.stress(snap(pool_type="CLMM"), [500])
    assert cl["decision"] == "INSUFFICIENT_EXECUTION_DATA" and by(cl, "BASE", 500)["status"] == "UNSUPPORTED_POOL"
    nosol = S.stress(snap(sol_usd=None), [500])
    assert by(nosol, "BASE", 500)["status"] == "INSUFFICIENT_EXECUTION_DATA"
    hp = S.stress(snap(has_sell_route=False), [500])
    assert hp["decision"] == "STRUCTURALLY_UNTRADEABLE"


def test_authority_shocks_appear_only_when_relevant():
    plain = {s.id for s in S.default_shocks(snap())}
    risky = {s.id for s in S.default_shocks(snap(fee_authority_active=True, freeze_authority_active=True, mint_authority_active=True, quote_asset="USDC"))}
    assert {"FEE_HIKE", "FREEZE", "MINT_DILUTION", "STABLE_DEPEG"} <= risky and not ({"FEE_HIKE", "FREEZE", "MINT_DILUTION"} & plain)
    rep = S.stress(snap(freeze_authority_active=True, transfer_fee_bps=100, fee_authority_active=True), [1_000])
    assert by(rep, "FREEZE", 1_000)["ret"] == -1.0
    assert by(rep, "FEE_HIKE", 1_000)["proceeds_usd"] < by(rep, "BASE", 1_000)["proceeds_usd"]


def test_g31_new_token_has_no_historical_claim():
    rep = S.stress(snap(), [500])
    assert rep["historical_evidence"]["tier"] == "UNAVAILABLE"
    assert rep["decision"] in ("RESEARCHABLE", "INCONCLUSIVE", "NO_TRADE")


def test_unknown_insider_share_is_not_assumed_zero():
    rep = S.stress(snap(concentrated_pct=None), [500])
    r = by(rep, "INSIDER_DUMP", 500)
    assert any("not modeled" in n for n in r.get("notes", []))


# ---------------- Phase 12 additions: pool fee, observed quotes, delayed exit, quote depletion, empirical cohort ----------------

def _snap(**kw):
    base = dict(chain="solana", mint="SNAPmint", as_of=1_800_000_000.0, price_usd=0.01, liquidity_usd=200_000.0, sol_usd=150.0,
                invalidation_price=0.008, concentrated_pct=None, circulating_tokens=None)
    base.update(kw)
    return S.Snapshot(**base)


def test_pool_fee_tier_changes_every_scenario_and_is_labeled():
    lo, hi = _snap(swap_fee=0.003, fee_basis="OBSERVED"), _snap()
    a = S.run_scenario(lo, 1000, S.default_shocks(lo)[0])
    b = S.run_scenario(hi, 1000, S.default_shocks(hi)[0])
    assert a["proceeds_usd"] > b["proceeds_usd"] and b["swap_fee"] == 0.0125 and b["fee_basis"] == "ASSUMED_UPPER_OBSERVED_TIER"


def test_observed_quotes_cap_an_optimistic_model_and_depletion_fails_large_sizes():
    quotes = [(250.0, 240.0, 0.02, "OK"), (1000.0, 900.0, 0.08, "OK"), (5000.0, None, None, "NO_ROUTE")]
    s = _snap(sell_quotes=quotes)
    base = S.run_scenario(s, 1000, S.default_shocks(s)[0])
    assert base["capped_by_observed_quote"] < 1.0 and base["proceeds_usd"] <= 900.0 + 1e-6
    ids = [x.id for x in S.default_shocks(s)]
    assert "QUOTE_DEPLETION" in ids and "QUOTE_DEPLETION" not in [x.id for x in S.default_shocks(_snap())]
    dep = {x.id: x for x in S.default_shocks(s)}["QUOTE_DEPLETION"]
    assert S.run_scenario(s, 5000, dep)["status"] == "FAILED"
    assert S.run_scenario(s, 1000, dep)["status"] == "FILLED"
    assert S.observed_sell_proceeds(s, 5000) is None                       # never extrapolated above the largest working quote


def test_delayed_exit_degrades_and_no_probability_labels_anywhere():
    s = _snap()
    out = S.stress(s, [250, 1000, 5000], max_loss_usd=200)
    by = {(r["scenario"], r["size_usd"]): r for r in out["scenarios"]}
    for size in (250, 1000, 5000):
        assert by[("DELAYED_EXIT", size)]["proceeds_usd"] < by[("BASE", size)]["proceeds_usd"]
    assert out["probabilities"].startswith("NOT_ASSIGNED")
    assert not any(k in json.dumps(out).lower() for k in ("likely", "probability of", "chance of"))


def test_empirical_cohort_needs_enough_cases(tmp_path):
    from memelab.backtest import store
    con = store.connect(tmp_path / "bt.sqlite")
    T0 = 1_800_000_000.0
    for k in range(12):
        m = f"COH{k:02d}"
        store.record_universe_member(con, universe_id="lab_state_history", chain="solana", mint=m, basis="THESIS", entered_at=T0, status_at_entry="WATCH")
        for i in range(30):
            store.record_bar(con, chain="solana", mint=m, pool_address=f"P{k}", tf=3600, start=T0 + i * 3600, o=1, h=1.1, l=0.5, c=0.8,
                             volume_usd=1, observed_at=T0 + 40 * 86400, provider="test")
    con.commit()
    assert S.empirical_cohort(con, "WATCH")["tier"] == "INSUFFICIENT_HISTORY"
    c = S.empirical_cohort(con, "WATCH", min_n=10)
    assert c["tier"] == "HISTORICAL_COHORT" and c["n"] == 12 and c["worst_drop_p10_p50"][1] == -0.5


def test_better_observed_quotes_never_scale_the_model_up():
    quotes = [(250.0, 249.9, 0.0, "OK"), (2000.0, 1999.0, 0.0, "OK")]       # a generous router quote
    r = S.run_scenario(_snap(sell_quotes=quotes), 1000, S.default_shocks(_snap(sell_quotes=quotes))[0])
    m = S.run_scenario(_snap(), 1000, S.default_shocks(_snap())[0])
    assert "capped_by_observed_quote" not in r and abs(r["proceeds_usd"] - m["proceeds_usd"]) < 1e-9


def test_usd_depth_shrinks_with_price_and_honeypot_returns_nothing():
    s = _snap()
    base = S.run_scenario(s, 5000, S.default_shocks(s)[0])
    crash = S.run_scenario(s, 5000, S.Shock("PRICE_ONLY", "price -75%, nobody adds liquidity", price_move=-0.75))
    # constant product: after others sell the price down 75%, the token reserve doubles and the USD reserve halves
    # (depth scales with sqrt(price)); keeping the USD depth unchanged would make our exit look far easier
    assert 0.45 < crash["exit_impact"] / base["exit_impact"] < 0.8
    hp = {x.id: x for x in S.default_shocks(s)}["HONEYPOT"]
    r = S.run_scenario(s, 500, hp)
    assert r["status"] == "FAILED" and r["proceeds_usd"] == 0.0 and r["ret"] == -1.0
    nr = S.run_scenario(_snap(has_sell_route=False), 500, S.default_shocks(s)[0])
    assert nr["status"] == "FAILED" and nr["proceeds_usd"] == 0.0
