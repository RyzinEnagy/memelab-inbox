"""Phase 10: wallet performance accounting.

Invented data only. Every expected number is worked out by hand in the test or in tests/fixtures/social/perf/expected_main.json
(arithmetic in docs/social-intelligence/PERFORMANCE_10.md). No network, fixed clocks.
"""
import copy
import json
import sqlite3
import subprocess
import sys
from decimal import Decimal as D
from pathlib import Path

import pytest

from memelab import db
from memelab.social import perf_analysis as A, perf_core as C, perf_store as S, schema, wallet_activity as WA

ROOT = Path(__file__).resolve().parent.parent
FX = ROOT / "tests" / "fixtures" / "social" / "perf"
WFX = ROOT / "tests" / "fixtures" / "social" / "wallets"
T = 1790000000
H = 3600
MAIN = json.loads((FX / "ledger_main.json").read_text())
EXP = json.loads((FX / "expected_main.json").read_text())


def load(name):
    return json.loads((FX / name).read_text())


def sw(i, t, give, get, wallet="W1", fee="0.0001", sig=None):
    """A swap entry: give and get are (asset, amount) pairs."""
    return {"id": f"x{i}", "wallet": wallet, "time": T + t * H, "type": "SWAP", "signature": sig or f"s{i}",
            "legs": [{"asset": give[0], "dir": "OUT", "amount": str(give[1])}, {"asset": get[0], "dir": "IN", "amount": str(get[1])}],
            "fee": None if fee is None else {"amount": fee, "unit": "SOL"}}


def tr(i, t, typ, asset, amount, cp, wallet="W1", sig=None, fee="0.00005", paid=None):
    e = {"id": f"x{i}", "wallet": wallet, "time": T + t * H, "type": typ, "signature": sig or f"s{i}",
         "legs": [{"asset": asset, "dir": "OUT" if typ == "TRANSFER_OUT" else "IN", "amount": str(amount), "counterparty": cp}],
         "fee": None if fee is None else {"amount": fee, "unit": "SOL"}}
    if paid is not None:
        e["fee_paid_by_wallet"] = paid
    return e


def sol(hours, usd=100, upto=None):
    return [{"asset": "NATIVE", "t": T + h * H, "kind": "MID", "usd": str(usd), "source": "fixture:invented"} for h in hours]


def ledger(entries, prices=None, assets=None, wallets=("W1",), hist="PLAUSIBLY_COMPLETE", as_of=None, **extra):
    toks = {"NATIVE": {"kind": "NATIVE", "symbol": "SOL"}, "WSOL": {"kind": "NATIVE", "alias_of": "NATIVE"}, "USDC": {"kind": "STABLE", "decimals": 6}}
    for e in entries:
        for lg in e["legs"]:
            toks.setdefault(lg["asset"], {"kind": "TOKEN", "decimals": 6})
    toks.update(assets or {})
    last = max([e["time"] for e in entries] + [T])
    d = {"schema": "memelab.perf.ledger/1", "label": "FIXTURE: invented", "chain": "solana", "wallets": list(wallets), "as_of": as_of or last + H,
         "assets": toks, "entries": entries, "prices": prices if prices is not None else sol(range(0, 40)), "coverage": {"history": hist, "evidence": "invented"}}
    d.update(extra)
    return d


def run(doc, **pol):
    return A.analyze(doc, pol or None)


def check(res, name):
    return next(c for c in res["reconciliation"]["checks"] if c["check"] == name)


def head(res):
    return D(res["headline"]["realized_trading_known_usd_before_fees"])


# ---------- the main fixture against hand-checked numbers ----------

def test_main_fixture_matches_the_hand_checked_numbers():
    r = run(copy.deepcopy(MAIN))
    pos = {p["asset"]: p["units"]["USD"] for p in r["positions"]}
    for a, e in EXP["positions"].items():
        for k in ("cost", "proceeds", "realized_gross", "fees_known", "net", "return"):
            ek = {"fees_known": "fees"}.get(k, k)
            if ek in e:
                assert D(pos[a][k]) == D(e[ek]), (a, k)
    h = r["headline"]
    x = EXP["realized"]
    assert D(h["realized_trading_known_usd_before_fees"]) == D(x["trading_known_before_fees"]) == 1720
    assert D(h["known_fees_usd"]) == D(x["known_fees_usd"]) == D("0.178")
    assert D(h["realized_trading_known_usd_after_known_fees"]) == D(x["after_known_fees"])
    assert D(r["realized"]["unknown_basis_proceeds"]["proceeds_usd"]) == 600
    assert D(r["realized"]["airdrop_proceeds"]["proceeds_usd"]) == 120
    n = r["native_unit_view"]
    assert (D(n["cost_native"]), D(n["proceeds_native"]), D(n["realized_pnl_native"])) == (35, 51, 16)
    assert D(r["costs"]["native_known"]) == D(x["fees_native_known"])
    assert D(r["costs"]["usd_known_attributed_to_positions"]) == D(x["fees_attached_to_positions"])


def test_main_fixture_metrics_and_unrealized_lines_are_separate():
    r = run(copy.deepcopy(MAIN))
    m, e = r["metrics"]["USD"], EXP["metrics"]
    for k in ("sample_size", "wins", "losses"):
        assert m[k] == e[k]
    for k in ("win_rate", "median_return", "aggregate_return", "total_net", "total_cost", "profit_share_from_biggest_winner", "return_excluding_biggest_winner"):
        assert D(m[k]) == D(e[k]), k
    assert m["biggest_winner"]["asset"] == "TOKA"
    inv = {a["asset"]: a for a in r["open_inventory"]["assets"]}
    for a in ("TOKR", "TOKE"):
        x = EXP["open_inventory"][a]
        assert D(inv[a]["mtm_value_usd"]) == D(x["mtm_value"])
        assert D(inv[a]["unrealized_mtm_usd"]) == D(x["unrealized_mtm"])
        assert D(inv[a]["unrealized_executable_usd"]) == D(x["unrealized_executable"])
        assert D(inv[a]["mtm_minus_executable_usd"]) == D(x["gap"])
    assert inv["TOKR"]["liquidation"]["status"] == "UNEXITABLE" and inv["TOKE"]["liquidation"]["status"] == "QUOTED_PRORATA"
    t = EXP["open_inventory"]["total"]
    assert (D(r["headline"]["unrealized_mark_to_market_usd"]), D(r["headline"]["unrealized_if_sold_now_usd_lower_bound"]), D(r["headline"]["mark_minus_executable_gap_usd"])) == \
           (D(t["unrealized_mtm"]), D(t["unrealized_executable"]), D(t["gap"]))
    sens = {s["name"]: D(s["delta_vs_primary_usd"]) for s in r["sensitivity"]}
    assert sens["convention_AVCO"] == 0 and sens["stablecoins_at_1.00"] == -120 and sens["no_return_matching"] == 0


def test_main_fixture_counts_gaps_and_refusal():
    r = run(copy.deepcopy(MAIN))
    for k, v in EXP["counts"].items():
        if k in r["counts"]:
            assert r["counts"][k] == v, k
    assert r["counts"]["positions"]["CLOSED"] == 3 and r["counts"]["positions"]["OPEN"] == 2
    assert r["person_level_claim"] is False
    assert r["reconstruction"]["status"] == "PARTIAL" and "cannot be achieved" in r["reconstruction"]["statement"]
    assert r["equity"]["status"] == "INSUFFICIENT_DATA" and r["equity"]["max_drawdown_usd"] is None
    assert r["score"]["status"] == "INSUFFICIENT_DATA" and r["score"]["value"] is None and r["score"]["rankable"] is False
    assert any("below the minimum of 20" in x for x in r["score"]["reasons"])
    assert r["reconciliation"]["reconciled"] is True
    assert [f["code"] for f in r["flags"]] == ["SHORTFALL_OPENING_LOT"]
    assert r["round_trip_transfers"][0]["counterparty"] == "W2x"
    assert r["coverage"]["history"]["status"] == "UNKNOWN"


def test_main_fixture_reconciliation_checks_are_all_present_and_pass():
    r = run(copy.deepcopy(MAIN))
    names = {c["check"]: c["status"] for c in r["reconciliation"]["checks"]}
    for n in ("lot_quantity_conservation", "asset_quantity_conservation", "off_book_conservation", "basis_conservation", "proceeds_conservation",
              "position_total_equals_slice_total", "fee_partition", "entries_accounted", "deterministic_recomputation", "no_entries_after_as_of"):
        assert names[n] == "PASS", n
    assert names["inventory_explained_by_ledger"] == "WARN"
    assert "FAIL" not in names.values()


# ---------- scored fixtures: the gate lets a wallet through, and says how much to trust it ----------

def test_outlier_wallet_is_scored_but_flagged_low_confidence():
    r = run(load("ledger_scored_outlier.json"))
    m = r["metrics"]["USD"]
    assert m["sample_size"] == 24
    assert D(m["win_rate"]) == D("0.5") and D(m["median_return"]) == D("-0.05") and D(m["aggregate_return"]) == D("0.775")
    assert D(m["profit_share_from_biggest_winner"]) == D("0.900900900901")
    assert D(m["return_excluding_biggest_winner"]) == D("-0.060869565217")
    assert r["score"]["status"] == "SCORED" and r["score"]["confidence"] == "LOW_CONFIDENCE"
    assert D(r["score"]["value"]) == D("-0.060869565217")        # the score is the return without the outlier
    assert any("produced" in n and "all profit" in n for n in r["score"]["notes"])
    assert r["equity"]["status"] == "INSUFFICIENT_DATA"


def test_clean_wallet_is_scored_with_a_drawdown():
    r = run(load("ledger_scored_clean.json"))
    m = r["metrics"]["USD"]
    assert m["sample_size"] == 50
    assert D(m["win_rate"]) == D("0.6") and D(m["median_return"]) == D("0.1") and D(m["aggregate_return"]) == D("0.02")
    assert D(m["profit_share_from_biggest_winner"]) == D("0.033333333333") and D(m["return_excluding_biggest_winner"]) == D("0.018367346939")
    assert r["score"]["status"] == "SCORED" and r["score"]["confidence"] == "OK"
    assert r["equity"]["status"] == "COMPUTED" and D(r["equity"]["max_drawdown_usd"]) == 200 and D(r["equity"]["max_drawdown_share_of_peak_capital"]) == 2


# ---------- lot convention ----------

def avco_ledger():
    e = [sw(1, 0, ("NATIVE", 10), ("TOKA", 1000)), sw(2, 1, ("NATIVE", 20), ("TOKA", 1000)), sw(3, 2, ("TOKA", 1500), ("NATIVE", 45))]
    return ledger(e)


def test_fifo_vs_avco_on_a_partly_closed_position():
    # buys: 1000 units for $1000 and 1000 for $2000. Sell 1500 for $4500.
    # FIFO consumes lot 1 (cost 1000) and half of lot 2 (cost 1000): realized 4500 - 2000 = 2500.
    # AVCO: average cost 1.5 per unit, 1500 units cost 2250: realized 2250. Delta -250 is 10% of 2500, so it is material.
    r = run(avco_ledger())
    assert head(r) == 2500
    s = next(x for x in r["sensitivity"] if x["name"] == "convention_AVCO")
    assert D(s["realized_usd"]) == 2250 and D(s["delta_vs_primary_usd"]) == -250 and s["material"] is True and s["sign_flip"] is False
    r2 = run(avco_ledger(), convention="AVCO")
    assert head(r2) == 2250 and r2["convention"] == "AVCO"
    s2 = next(x for x in r2["sensitivity"] if x["name"].startswith("convention_FIFO"))
    assert D(s2["realized_usd"]) == 2500


def test_closed_position_has_the_same_total_under_every_convention():
    e = [sw(1, 0, ("NATIVE", 10), ("TOKA", 1000)), sw(2, 1, ("NATIVE", 20), ("TOKA", 1000)), sw(3, 2, ("TOKA", 1500), ("NATIVE", 45)), sw(4, 3, ("TOKA", 500), ("NATIVE", 5))]
    a, b = run(ledger(e)), run(ledger(e), convention="AVCO")
    assert head(a) == head(b) == 2000       # proceeds 5000 less cost 3000
    assert next(x for x in a["sensitivity"] if x["name"] == "convention_AVCO")["material"] is False


def test_multiple_lots_of_the_same_token_keep_their_own_cost():
    # sell 1000 from lot 1 only (cost $1000) for $1500: +500. Lot 2 stays open at its own cost.
    e = [sw(1, 0, ("NATIVE", 10), ("TOKA", 1000)), sw(2, 1, ("NATIVE", 20), ("TOKA", 1000)), sw(3, 2, ("TOKA", 1000), ("NATIVE", 15))]
    r = run(ledger(e))
    assert head(r) == 500
    inv = r["open_inventory"]["assets"][0]
    assert D(inv["qty_open"]) == 1000 and D(inv["basis_known_usd"]) == 2000


# ---------- missing history ----------

def test_a_sale_with_no_visible_buy_gets_an_unknown_lot_and_no_gain():
    r = run(ledger([sw(1, 0, ("TOKZ", 100), ("NATIVE", 3))]))
    assert head(r) == 0 and D(r["realized"]["unknown_basis_proceeds"]["proceeds_usd"]) == 300
    assert r["flags"][0]["code"] == "SHORTFALL_OPENING_LOT"
    assert r["coverage"]["history"]["opening_lots_from_missing_history"] == 1
    assert r["reconstruction"]["status"] != "COMPLETE"
    assert r["metrics"]["USD"]["sample_size"] == 0


def test_a_position_that_touches_missing_history_is_left_out_of_the_sample():
    e = [sw(1, 0, ("NATIVE", 10), ("TOKZ", 100)), sw(2, 1, ("TOKZ", 150), ("NATIVE", 20))]     # sells 50 more than was bought
    r = run(ledger(e))
    p = r["positions"][0]["units"]["USD"]
    assert p["in_sample"] is False and r["metrics"]["USD"]["sample_size"] == 0
    assert any("MISSING_HISTORY" in x or "history" in x.lower() for x in p["exclusion_reasons"])
    # proceeds $2000 for 150 units. The 100 units with a known basis get 2000 * 100/150 = 1333.33 against cost 1000: +333.33.
    # The other 50 units (proceeds 666.67) came from before the visible history: proceeds shown, no gain.
    assert head(r) == D("333.333333333333") and D(r["realized"]["unknown_basis_proceeds"]["proceeds_usd"]).quantize(D("0.01")) == D("666.67")


# ---------- wash-like transfers and wallet-to-wallet moves ----------

def wash(cp_back):
    return ledger([sw(1, 0, ("NATIVE", 10), ("TOKA", 1000)), tr(2, 1, "TRANSFER_OUT", "TOKA", 1000, "CP1"), tr(3, 2, "TRANSFER_IN", "TOKA", 1000, cp_back, paid=False),
                   sw(4, 3, ("TOKA", 1000), ("NATIVE", 15))])


def test_tokens_sent_away_and_back_from_the_same_counterparty_keep_their_basis():
    # bought for $1000, sold for $1500: +500, whatever the round trip did. The transfers are not trades and create no profit.
    r = run(wash("CP1"))
    assert head(r) == 500 and r["counts"]["returns_matched"] == 1 and r["counts"]["buys"] == 1 and r["counts"]["sells"] == 1
    assert D(r["realized"]["unknown_basis_proceeds"]["proceeds_usd"]) == 0


def test_tokens_that_come_back_from_somebody_else_have_unknown_basis_and_no_gain():
    r = run(wash("CP2"))
    assert head(r) == 0 and D(r["realized"]["unknown_basis_proceeds"]["proceeds_usd"]) == 1500
    assert r["counts"]["returns_matched"] == 0
    assert D(r["realized"]["off_book"]["TRANSFER_OUT"]["qty_not_returned"]) == 1000     # the original lot never came back


def test_a_transfer_in_is_never_a_free_profitable_buy():
    e = [tr(1, 0, "TRANSFER_IN", "TOKX", 1000, "EXT", paid=False), sw(2, 1, ("TOKX", 1000), ("NATIVE", 2))]
    r = run(ledger(e))
    assert head(r) == 0 and D(r["realized"]["unknown_basis_proceeds"]["proceeds_usd"]) == 200 and r["counts"]["buys"] == 0
    assert r["metrics"]["USD"]["sample_size"] == 0 and r["counts"]["transfers_in"] == 1


def test_an_airdrop_needs_an_annotation_and_stays_out_of_trading_performance():
    e = [tr(1, 0, "TRANSFER_IN", "TOKY", 500, "DROP", sig="sigdrop", paid=False), sw(2, 1, ("TOKY", 500), ("NATIVE", 1))]
    plain = run(ledger(e))
    marked = run(ledger(e, annotations=[{"signature": "sigdrop", "origin": "AIRDROP", "reason": "invented"}]))
    assert D(plain["realized"]["unknown_basis_proceeds"]["proceeds_usd"]) == 100 and plain["counts"]["airdrops"] == 0
    assert D(marked["realized"]["airdrop_proceeds"]["proceeds_usd"]) == 100 and marked["counts"]["airdrops"] == 1
    assert head(marked) == head(plain) == 0


def group(entries):
    return ledger(entries, wallets=("W1", "W2"), linked_wallets={"declared": ["W1", "W2"], "reason": "invented: analyst declared these two wallets one group"})


def test_a_transfer_between_declared_group_wallets_moves_basis_and_makes_no_profit():
    e = [sw(1, 0, ("NATIVE", 10), ("TOKA", 1000)), tr(2, 1, "TRANSFER_OUT", "TOKA", 1000, "W2", sig="shared"),
         tr(3, 2, "TRANSFER_IN", "TOKA", 1000, "W1", wallet="W2", sig="shared", paid=False), sw(4, 3, ("TOKA", 1000), ("NATIVE", 15), wallet="W2")]
    r = run(group(e))
    assert head(r) == 500 and r["counts"]["internal_transfer_pairs"] == 1 and r["group"]["declared"] == ["W1", "W2"]


def test_a_group_needs_a_declaration_and_unmatched_signatures_are_not_matched():
    e = [sw(1, 0, ("NATIVE", 10), ("TOKA", 1000)), tr(2, 1, "TRANSFER_OUT", "TOKA", 1000, "W2", sig="a"),
         tr(3, 2, "TRANSFER_IN", "TOKA", 1000, "W1", wallet="W2", sig="b", paid=False), sw(4, 3, ("TOKA", 1000), ("NATIVE", 15), wallet="W2")]
    with pytest.raises(ValueError, match="linked_wallets"):
        run(ledger(e, wallets=("W1", "W2")))
    r = run(group(e))      # declared, but the two sides carry different signatures: no match is guessed
    assert r["counts"]["internal_transfer_pairs"] == 0 and head(r) == 0 and D(r["realized"]["unknown_basis_proceeds"]["proceeds_usd"]) == 1500


def test_a_single_wallet_receiving_from_its_own_other_wallet_is_still_unknown_basis():
    e = [tr(1, 0, "TRANSFER_IN", "TOKA", 1000, "W2", paid=False), sw(2, 1, ("TOKA", 1000), ("NATIVE", 15))]
    r = run(ledger(e))
    assert head(r) == 0 and D(r["realized"]["unknown_basis_proceeds"]["proceeds_usd"]) == 1500


# ---------- fee-on-transfer tokens ----------

def test_fee_on_transfer_token_bought_by_swap_costs_what_was_paid():
    # paid 10 SOL ($1000), received 95 units (5% taken on the way). Sold 95 for 12 SOL ($1200): +200.
    r = run(ledger([sw(1, 0, ("NATIVE", 10), ("TOKF", 95)), sw(2, 1, ("TOKF", 95), ("NATIVE", 12))]))
    assert head(r) == 200


def test_fee_on_transfer_between_group_wallets_books_the_loss_as_a_tax_slice():
    # W1 buys 100 for $1000 and sends 100; W2 receives 95. The 5 missing units carried $50 of basis and are a TRANSFER_TAX slice.
    # W2 sells 95 for 12 SOL ($1200) from basis $950: +250. Tax slice: -50. Net +200 = 1200 - 1000.
    e = [sw(1, 0, ("NATIVE", 10), ("TOKF", 100)), tr(2, 1, "TRANSFER_OUT", "TOKF", 100, "W2", sig="shared"),
         tr(3, 2, "TRANSFER_IN", "TOKF", 95, "W1", wallet="W2", sig="shared", paid=False), sw(4, 3, ("TOKF", 95), ("NATIVE", 12), wallet="W2")]
    r = run(group(e))
    assert head(r) == 200 and D(r["costs"]["transfer_tax_basis_usd"]) == 50
    assert check(r, "basis_conservation")["status"] == "PASS"


# ---------- decimals ----------

def test_raw_amount_and_decimals_give_the_human_amount():
    L = C.parse_ledger(ledger([{"id": "d", "wallet": "W1", "time": T, "type": "SWAP", "signature": "d",
                                "legs": [{"asset": "NATIVE", "dir": "OUT", "amount": "1"}, {"asset": "TOKA", "dir": "IN", "raw": "1500000", "decimals": 6}]}]))
    assert L.entries[0]["legs"][1]["amount"] == D("1.5")


def test_decimal_conflicts_and_mismatched_raw_amounts_are_rejected_and_counted():
    bad = [{"id": "c", "wallet": "W1", "time": T, "type": "SWAP", "signature": "c",
            "legs": [{"asset": "NATIVE", "dir": "OUT", "amount": "1"}, {"asset": "TOKA", "dir": "IN", "raw": "1500000", "decimals": 9}]},
           {"id": "m", "wallet": "W1", "time": T + H, "type": "SWAP", "signature": "m",
            "legs": [{"asset": "NATIVE", "dir": "OUT", "amount": "1"}, {"asset": "TOKA", "dir": "IN", "raw": "1500000", "decimals": 6, "amount": "15"}]}]
    r = run(ledger(bad))
    assert [x["reason"] for x in r["rejects"]] == ["DECIMALS_CONFLICT", "AMOUNT_RAW_MISMATCH"]
    assert r["counts"]["rejected"] == 2 and r["counts"]["entries_input"] == 2 and r["counts"]["buys"] == 0
    assert "TOKA" in " ".join(r["reconstruction"]["reasons"])        # the token the rejected entries touched is named as contaminated


def test_a_sale_far_larger_than_known_inventory_is_flagged_as_a_possible_decimals_error():
    # bought 100 units, sold 1,000,000 (a 10^4 decimals slip): the position is excluded and the unit error is named
    e = [sw(1, 0, ("NATIVE", 10), ("TOKA", 100)), sw(2, 1, ("TOKA", 1000000), ("NATIVE", 20))]
    r = run(ledger(e))
    assert "UNIT_ERROR_SUSPECTED" in [f["code"] for f in r["flags"]]
    assert r["metrics"]["USD"]["sample_size"] == 0 and r["reconstruction"]["status"] != "COMPLETE"


def test_a_swap_price_far_from_the_observed_price_is_flagged_and_excluded():
    prices = sol(range(0, 5)) + [{"asset": "TOKA", "t": T, "kind": "MID", "usd": "0.0001", "source": "fixture:invented"}]
    e = [sw(1, 0, ("NATIVE", 10), ("TOKA", 100)), sw(2, 1, ("TOKA", 100), ("NATIVE", 12))]    # implies $10 per unit against an observed $0.0001
    r = run(ledger(e, prices=prices))
    assert "IMPLIED_PRICE_MISMATCH" in [f["code"] for f in r["flags"]]
    assert r["metrics"]["USD"]["sample_size"] == 0


# ---------- rug, quotes, marks, no price ----------

def test_rug_position_marks_at_cost_but_sells_for_nothing():
    e = [sw(1, 0, ("NATIVE", 10), ("TOKR", 5000000))]
    pr = sol(range(0, 3)) + [{"asset": "TOKR", "t": T + 2 * H, "kind": "MID", "usd": "0.0002", "source": "fixture:invented"},
                              {"asset": "TOKR", "t": T + 2 * H, "kind": "NO_ROUTE", "source": "fixture:invented", "detail": "no sell route"}]
    r = run(ledger(e, prices=pr, as_of=T + 3 * H))
    h = r["headline"]
    assert D(h["unrealized_mark_to_market_usd"]) == 0 and D(h["unrealized_if_sold_now_usd_lower_bound"]) == -1000 and D(h["mark_minus_executable_gap_usd"]) == 1000
    assert r["open_inventory"]["assets"][0]["liquidation"]["status"] == "UNEXITABLE"


def test_missing_stale_and_curve_quotes():
    pol = C.merge_policy(None)
    assert A.liquidation("X", D(10), D(1), None, 100, pol)["status"] == "NO_QUOTE" and A.liquidation("X", D(10), D(1), None, 100, pol)["value"] is None      # unknown, not zero
    old = {"kind": "EXEC_QUOTE", "t": 0, "source": "s", "amount_in": D(10), "usd_out": D(9)}
    st = A.liquidation("X", D(10), D(1), old, 10 * H, pol)
    assert st["status"] == "STALE_QUOTE" and st["value"] is None
    part = A.liquidation("X", D(20), D(1), dict(old, t=9 * H), 10 * H, pol)
    assert part["status"] == "QUOTED_PARTIAL" and part["value"] == 9          # covers half the units: the rest is not valued
    pro = A.liquidation("X", D(5), D(1), dict(old, t=9 * H), 10 * H, pol)
    assert pro["status"] == "QUOTED_PRORATA" and pro["value"] == D("4.5")
    sell = {"100": {"priceImpactPct": "0.01"}, "1000": {"priceImpactPct": "0.05"}}
    crv = {"kind": "IMPACT_CURVE", "t": 9 * H, "source": "s", "sell": sell}
    assert A.liquidation("X", D(1000), D(1), crv, 10 * H, pol)["value"] == 950      # size $1000, 5% impact
    assert A.liquidation("X", D(100), D(1), crv, 10 * H, pol)["value"] == 99        # size $100, 1% impact
    assert A.liquidation("X", D(100), None, crv, 10 * H, pol)["status"] == "NO_MARK_TO_SIZE"


def test_an_old_mark_is_stale_and_not_counted():
    e = [sw(1, 0, ("NATIVE", 10), ("TOKA", 1000))]
    pr = sol(range(0, 2)) + [{"asset": "TOKA", "t": T, "kind": "MID", "usd": "2", "source": "fixture:invented"}]
    fresh = run(ledger(e, prices=pr, as_of=T + H))
    stale = run(ledger(e, prices=pr, as_of=T + 3 * 86400))
    assert D(fresh["headline"]["unrealized_mark_to_market_usd"]) == 1000           # 1000 units at $2 against basis $1000
    assert stale["open_inventory"]["assets"][0]["mark"]["status"] == "STALE"
    assert stale["headline"]["unrealized_mark_to_market_usd"] in (None, "0") or D(stale["headline"]["unrealized_mark_to_market_usd"]) == 0


def test_no_price_scenario_still_gives_native_units_and_refuses_a_score():
    e = [sw(1, 0, ("NATIVE", 10), ("TOKA", 1000)), sw(2, 1, ("TOKA", 1000), ("NATIVE", 15))]
    r = run(ledger(e, prices=[]))
    assert r["coverage"]["prices"]["unpriced"] > 0 and head(r) == 0
    n = r["native_unit_view"]
    assert (D(n["cost_native"]), D(n["proceeds_native"]), D(n["realized_pnl_native"])) == (10, 15, 5)
    assert r["score"]["status"] == "INSUFFICIENT_DATA" and any("could be priced" in x for x in r["score"]["reasons"])
    assert r["metrics"]["USD"]["sample_size"] == 0 and r["metrics"]["NATIVE"]["sample_size"] == 1


# ---------- stablecoin peg ----------

def peg_ledger():
    e = [sw(1, 0, ("USDC", 1000), ("TOKC", 400)), sw(2, 1, ("TOKC", 400), ("USDC", 1000))]
    pr = sol(range(0, 3)) + [{"asset": "USDC", "t": T, "kind": "MID", "usd": "0.88", "source": "fixture:invented"},
                              {"asset": "USDC", "t": T + H, "kind": "MID", "usd": "1.00", "source": "fixture:invented"}]
    return ledger(e, prices=pr)


def test_stablecoin_depeg_is_priced_at_the_observed_peg_not_one_dollar():
    # 1000 USDC at $0.88 cost $880; the same 1000 USDC back at $1.00 is $1000: +120. At par both sides are $1000 and the gain is 0.
    r = run(peg_ledger())
    assert head(r) == 120
    par = run(peg_ledger(), force_stable_par=True)
    assert head(par) == 0
    s = next(x for x in r["sensitivity"] if x["name"] == "stablecoins_at_1.00")
    assert D(s["delta_vs_primary_usd"]) == -120 and s["material"] is True


def test_stablecoin_without_a_price_is_assumed_at_par_and_labelled():
    e = [sw(1, 0, ("USDC", 1000), ("TOKC", 400)), sw(2, 1, ("TOKC", 400), ("USDC", 1100))]
    a = run(ledger(e))
    assert head(a) == 100 and a["coverage"]["prices"]["entries_using_assumed_stable_peg"] == 2
    b = run(ledger(e), assume_stable_peg=False)
    assert head(b) == 0 and b["coverage"]["prices"]["unpriced"] == 2


# ---------- fees, liquidity, rejects ----------

def test_unknown_fees_are_counted_and_keep_the_position_out_of_the_sample():
    e = [sw(1, 0, ("NATIVE", 10), ("TOKA", 1000), fee=None), sw(2, 1, ("TOKA", 1000), ("NATIVE", 15))]
    r = run(ledger(e))
    assert r["costs"]["amount_unknown"] == 1 and r["coverage"]["fees"]["unknown_or_unpriced"] == 1 and D(r["coverage"]["fees"]["unknown_share"]) == D("0.5")
    p = r["positions"][0]["units"]["USD"]
    assert p["in_sample"] is False and "FEE_UNKNOWN" in p["exclusion_reasons"] and p["net"] is None and D(p["realized_gross"]) == 500
    assert r["metrics"]["USD"]["sample_size"] == 0


def test_liquidity_withdrawal_restores_basis_and_the_excess_has_unknown_basis():
    # bought 1000 for $1000, deposited 1000 to POOL1, withdrew 1100 (100 more: fees and price movement). 1000 units return at basis $1000, 100 are an unknown lot.
    # Sold all 1100 for 20 SOL ($2000): the 1000 known units get 2000 * 1000/1100 = 1818.18 against cost 1000.
    e = [sw(1, 0, ("NATIVE", 10), ("TOKA", 1000)),
         {"id": "x2", "wallet": "W1", "time": T + H, "type": "LP_ADD", "signature": "s2", "pool": "POOL1", "legs": [{"asset": "TOKA", "dir": "OUT", "amount": "1000"}], "fee": {"amount": "0.0001", "unit": "SOL"}},
         {"id": "x3", "wallet": "W1", "time": T + 2 * H, "type": "LP_REMOVE", "signature": "s3", "pool": "POOL1", "legs": [{"asset": "TOKA", "dir": "IN", "amount": "1100"}], "fee": {"amount": "0.0001", "unit": "SOL"}},
         sw(4, 3, ("TOKA", 1100), ("NATIVE", 20))]
    r = run(ledger(e))
    assert head(r) == D("818.181818181818") and D(r["realized"]["unknown_basis_proceeds"]["proceeds_usd"]).quantize(D("0.01")) == D("181.82")
    assert r["counts"]["buys"] == 1 and r["counts"]["sells"] == 1 and check(r, "off_book_conservation")["status"] == "PASS"


def test_liquidity_still_deployed_is_reported_off_book_and_not_valued():
    e = [sw(1, 0, ("NATIVE", 10), ("TOKA", 1000)),
         {"id": "x2", "wallet": "W1", "time": T + H, "type": "LP_ADD", "signature": "s2", "pool": "POOL1", "legs": [{"asset": "TOKA", "dir": "OUT", "amount": "1000"}], "fee": {"amount": "0.0001", "unit": "SOL"}}]
    r = run(ledger(e))
    ob = r["realized"]["off_book"]["LP_DEPLOY"]
    assert D(ob["qty_not_returned"]) == 1000 and D(ob["basis_not_returned_usd"]) == 1000 and r["positions"][0]["status"] == "OFF_BOOK"
    assert D(r["headline"]["unrealized_mark_to_market_usd"]) == 0 and any("off-book" in x for x in r["reconstruction"]["reasons"])


def test_rejected_entries_are_counted_with_reasons_and_never_dropped():
    good = sw(1, 0, ("NATIVE", 10), ("TOKA", 1000))
    e = [good, dict(good, id="x1", signature="other"), dict(sw(3, 1, ("NATIVE", 1), ("TOKB", 10)), time=T + 99 * H), sw(4, 2, ("NATIVE", 1), ("TOKB", 10), wallet="NOBODY"),
         {"id": "x5", "wallet": "W1", "time": T, "type": "WEIRD", "legs": []}]
    r = run(ledger(e, as_of=T + 10 * H))
    assert sorted(x["reason"] for x in r["rejects"]) == ["AFTER_AS_OF", "BAD_TYPE", "DUPLICATE_ID", "WALLET_NOT_IN_SCOPE"]
    assert r["counts"]["entries_input"] == 5 and r["counts"]["rejected"] == 4 and r["counts"]["buys"] == 1
    assert check(r, "no_rejected_entries")["status"] == "WARN"


# ---------- reconciliation, determinism, storage ----------

def test_the_same_ledger_gives_the_same_result_hash_and_a_changed_ledger_does_not():
    a, b = run(copy.deepcopy(MAIN)), run(copy.deepcopy(MAIN))
    assert a["result_sha256"] == b["result_sha256"] and check(a, "deterministic_recomputation")["status"] == "PASS"
    changed = copy.deepcopy(MAIN)
    changed["entries"][0]["legs"][0]["amount"] = "11"
    assert run(changed)["result_sha256"] != a["result_sha256"]


def test_a_broken_engine_fails_reconciliation_and_the_score_is_refused(monkeypatch):
    real = C.Run.new_lot

    def broken(self, *a, **k):
        out = real(self, *a, **k)
        if self.lots and self.lots[-1].cost0 is not None:
            self.lots[-1].cost0 += 1        # basis appears from nowhere
        return out
    monkeypatch.setattr(C.Run, "new_lot", broken)
    r = run(load("ledger_scored_clean.json"))
    assert check(r, "basis_conservation")["status"] == "FAIL" and r["reconciliation"]["reconciled"] is False
    assert r["reconstruction"]["status"] == "NOT_POSSIBLE" and r["score"]["status"] == "INSUFFICIENT_DATA"
    assert any("reconciliation failed" in x for x in r["score"]["reasons"])


def test_entries_after_as_of_are_refused_so_a_run_cannot_peek_forward():
    r = run(ledger([sw(1, 0, ("NATIVE", 10), ("TOKA", 1000)), sw(2, 5, ("TOKA", 1000), ("NATIVE", 15))], as_of=T + H))
    assert r["counts"]["sells"] == 0 and r["rejects"][0]["reason"] == "AFTER_AS_OF"


# ---------- the score gate and rankings ----------

def test_score_gate_refuses_each_kind_of_insufficient_data():
    clean = load("ledger_scored_clean.json")
    assert run(clean)["score"]["status"] == "SCORED"
    assert any("below the minimum of 60" in x for x in run(clean, min_closed_positions=60)["score"]["reasons"])
    assert any("spans" in x for x in run(clean, min_span_days=10000)["score"]["reasons"])
    assert any("lots of known basis" in x for x in run(clean, min_basis_coverage="1.1")["score"]["reasons"])
    assert any("of fees are unknown" in x for x in run(clean, max_unknown_fee_share="-1")["score"]["reasons"])
    nofee = copy.deepcopy(clean)
    for en in nofee["entries"][:30]:
        en["fee"] = None
    s = run(nofee)["score"]
    assert s["status"] == "INSUFFICIENT_DATA" and s["value"] is None


def test_wallet_score_refuses_a_sparse_wallet_and_says_why():
    r = run(copy.deepcopy(MAIN))
    s = r["score"]
    assert s["status"] == "INSUFFICIENT_DATA" and s["value"] is None and s["rankable"] is False and "no score and no ranking" in s["note"]
    assert len(s["reasons"]) >= 2


def test_ranking_lists_only_scored_wallets_and_refuses_the_rest():
    clean, out, sparse = run(load("ledger_scored_clean.json")), run(load("ledger_scored_outlier.json")), run(copy.deepcopy(MAIN))
    rk = A.rank_wallets([sparse, out, clean])
    assert [x["rank"] for x in rk["ranked"]] == [1, 2]
    assert D(rk["ranked"][0]["score"]) > D(rk["ranked"][1]["score"]) and rk["ranked"][1]["confidence"] == "LOW_CONFIDENCE"
    assert len(rk["refused"]) == 1 and rk["refused"][0]["reasons"]
    assert A.rank_wallets([sparse])["ranked"] == []


def test_provider_comparison_is_an_estimate_and_never_changes_the_ledger_result():
    r = run(copy.deepcopy(MAIN))
    before = copy.deepcopy(r)
    cmp = A.compare_provider_estimates(r, {"source": "invented leaderboard", "claims": {"realized_pnl_usd": "5000", "trade_count": "13", "win_rate": "0.9"}})
    assert cmp["label"] == "PROVIDER ESTIMATE, NOT VALIDATED, NOT USED IN THE LEDGER"
    assert r == before and cmp["ledger_result_sha256"] == r["result_sha256"]
    row = {x["metric"]: x for x in cmp["rows"]}
    assert D(row["realized_pnl_usd"]["difference"]) == 3280 and row["trade_count"]["ledger_value"] == "3"
    assert "does not validate" in cmp["note"]


def test_result_always_states_it_is_wallet_level_and_the_engine_has_no_network_code():
    r = run(copy.deepcopy(MAIN))
    assert r["person_level_claim"] is False and "person" in r["statement"]
    for f in ("perf_core.py", "perf_analysis.py"):
        src = (ROOT / "memelab" / "social" / f).read_text()
        for bad in ("import requests", "urllib", "http.client", "import socket", "httpx", "urlopen"):
            assert bad not in src, (f, bad)


# ---------- database: migration, Phase 09 integration, runs ----------

@pytest.fixture()
def con(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMELAB_PRIVATE_DB", str(tmp_path / "private" / "p.sqlite"))
    p = tmp_path / "t.sqlite"
    db.init_db(p)
    c = sqlite3.connect(p)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


IX = json.loads((WFX / "index.json").read_text())
NOW, T0 = IX["now"], IX["t0"]
T1 = IX["wallets"]["T1"]


def ingested(con, name="fx_helius_ok.json", max_tx=50, now=NOW, track=True):
    if track:
        WA.add_wallet(con, "solana", T1, reason="invented fixture wallet", added_by="tester", fixture=True, max_tx=max_tx, now=T0)
    return WA.ingest_file(con, WFX / name, now=now, fixture=True)


def price_events(con, usd=100):
    times = sorted({r[0] for r in con.execute("SELECT block_time FROM social_wallet_events")})
    S.put_prices(con, "solana", [{"asset": "NATIVE", "t": t, "kind": "MID", "usd": str(usd), "source": "fixture:invented"} for t in times], fixture=True, now=NOW)


def test_migration_10_rolls_back_cleanly_and_leaves_phase_09_tables_alone(con):
    assert schema.current_version(con) == schema.LATEST and 10 in schema.ALL_VERSIONS
    before = {r[0]: r[1] for r in con.execute("SELECT name, sql FROM sqlite_master WHERE name LIKE 'social_wallet_%' OR name LIKE 'social_tracked_%'")}
    perf = {n for n in schema.SOCIAL_TABLES if n.startswith("social_perf_")}
    assert len(perf) == 5 and perf <= {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
    newer = [v for v in schema.ALL_VERSIONS if v > 10]          # later phases add migrations on top; roll those back too and reapply them after
    assert schema.rollback(con, 9) == sorted(newer + [10], reverse=True)
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not names & perf
    assert before == {r[0]: r[1] for r in con.execute("SELECT name, sql FROM sqlite_master WHERE name LIKE 'social_wallet_%' OR name LIKE 'social_tracked_%'")}
    assert schema.migrate(con) == sorted(newer + [10])


def test_phase_09_events_become_a_ledger_and_the_hand_numbers_hold(con):
    # Hand check (SOL at $100 at every event time):
    #  buy X 250000 for 1.5 SOL = $150; sell 100000 X for 0.9 SOL = $90, cost 100000/250000 * 150 = 60, realized +30.
    #  50000 X to R1 and 20000 X to the CEX leave the books (basis 30 and 12). LP deposit 30000 X (basis 18) and a withdrawal of 31000 X:
    #  30000 return at basis 18 and 1000 are unknown excess. The exchange and the unknown router are not gains.
    #  12 wallet-paid fees of 0.0005 SOL at $100 = 0.006. 4 of 13 events were not classified.
    ingested(con)
    price_events(con)
    out = S.run_wallet(con, "solana", [T1], now=NOW)
    r = out["result"]
    assert head(r) == 30 and D(r["headline"]["known_fees_usd"]) == D("0.006")
    assert r["counts"]["unclassified"] == 4 and r["counts"]["failed"] == 1 and r["counts"]["entries_input"] == 13
    assert r["coverage"]["history"]["status"] == "PLAUSIBLY_COMPLETE" and r["score"]["status"] == "INSUFFICIENT_DATA"
    assert D(r["realized"]["off_book"]["TRANSFER_OUT"]["qty_not_returned"]) == 70000
    assert r["reconciliation"]["reconciled"] is True and r["label"].startswith("FIXTURE")
    assert out["saved"]["created"] is True


def test_stored_run_repeats_verifies_and_detects_tampering(con):
    ingested(con)
    price_events(con)
    first = S.run_wallet(con, "solana", [T1], now=NOW)
    again = S.run_wallet(con, "solana", [T1], now=NOW + 99)
    assert first["saved"]["run_id"] == again["saved"]["run_id"] and again["saved"]["created"] is False
    assert first["result"]["result_sha256"] == again["result"]["result_sha256"]
    rid = first["saved"]["run_id"]
    assert S.verify_run(con, rid)["verified"] is True
    assert con.execute("SELECT COUNT(*) FROM social_perf_checks WHERE run_id=?", (rid,)).fetchone()[0] >= 13
    assert S.list_runs(con)[0]["is_fixture"] == 1
    r = S.load_run(con, rid)["result"]
    r["headline"]["realized_trading_known_usd_before_fees"] = "999999"
    con.execute("UPDATE social_perf_runs SET result_json=? WHERE run_id=?", (C.canonical_json(r), rid))
    v = S.verify_run(con, rid)
    assert v["verified"] is False and v["stored_result_matches_its_hash"] is False


def test_a_changed_price_table_is_a_new_run_not_an_overwrite(con):
    ingested(con)
    price_events(con)
    a = S.run_wallet(con, "solana", [T1], now=NOW)
    S.put_prices(con, "solana", [{"asset": "NATIVE", "t": T0 + 1, "kind": "MID", "usd": "101", "source": "fixture:invented"}], fixture=True, now=NOW)
    b = S.run_wallet(con, "solana", [T1], now=NOW)
    assert a["saved"]["run_id"] != b["saved"]["run_id"] and len(S.list_runs(con)) == 2


def test_truncated_fetch_and_rate_limited_fetch_show_up_as_coverage_limits(con):
    ingested(con, max_tx=3)
    r = S.run_wallet(con, "solana", [T1], save=False)["result"]
    assert r["coverage"]["history"]["status"] == "TRUNCATED" and "limit" in r["coverage"]["history"]["evidence"]
    assert r["score"]["status"] == "INSUFFICIENT_DATA"


def test_a_wallet_with_only_a_rate_limited_fetch_has_unknown_history_and_a_gap(con):
    WA.add_wallet(con, "solana", T1, reason="invented fixture wallet", added_by="tester", fixture=True, now=T0)
    WA.ingest_file(con, WFX / "fx_helius_429.json", now=NOW, fixture=True)
    r = S.run_wallet(con, "solana", [T1], save=False)["result"]
    assert r["coverage"]["history"]["status"] == "UNKNOWN" and any("RATE_LIMITED" in g["reason"] for g in r["coverage"]["history"]["gaps"])
    assert r["reconstruction"]["status"] == "NOT_POSSIBLE" and r["score"]["status"] == "INSUFFICIENT_DATA"


def test_fixture_and_real_wallets_never_share_a_run(con):
    WA.add_wallet(con, "solana", T1, reason="r", added_by="t", fixture=True, now=T0)
    WA.add_wallet(con, "solana", IX["wallets"]["T2"], reason="r", added_by="t", fixture=False, now=T0)
    with pytest.raises(ValueError, match="never share"):
        S.ledger_from_events(con, "solana", [T1, IX["wallets"]["T2"]], group_reason="x")


def test_a_wallet_group_from_the_database_needs_a_reason(con):
    WA.add_wallet(con, "solana", T1, reason="r", added_by="t", fixture=True, now=T0)
    WA.add_wallet(con, "solana", IX["wallets"]["T2"], reason="r", added_by="t", fixture=True, now=T0)
    with pytest.raises(ValueError, match="needs a reason"):
        S.ledger_from_events(con, "solana", [T1, IX["wallets"]["T2"]])


def test_phase_09_tables_have_no_pnl_columns_and_perf_tables_are_separate(con):
    cols = {r[0]: [c[1] for c in con.execute(f"PRAGMA table_info({r[0]})")] for r in con.execute("SELECT name FROM sqlite_master WHERE name LIKE 'social_wallet_%' OR name LIKE 'social_tracked_%'")}
    assert not [c for cs in cols.values() for c in cs if any(w in c for w in ("pnl", "price", "usd", "profit"))]


# ---------- command line ----------

def cli(*args, env=None, cwd=ROOT):
    import os
    e = dict(os.environ)
    e.pop("MEMELAB_DB", None)      # another test may leave it set; these tests choose their database explicitly or use the tracked default
    e.update(env or {})
    p = subprocess.run([sys.executable, "-m", "memelab", "social", *args], cwd=cwd, capture_output=True, text=True, env=e)
    return p.returncode, p.stdout, p.stderr


def test_cli_runs_a_ledger_and_a_refused_score_exits_zero(tmp_path):
    code, out, err = cli("perf", "run", "--ledger", str(FX / "ledger_main.json"), "--json")
    assert code == 0, err
    r = json.loads(out)["result"]
    assert r["score"]["status"] == "INSUFFICIENT_DATA" and r["headline"]["known_fees_usd"] == "0.178"
    code, out, err = cli("perf", "run", "--ledger", str(FX / "ledger_main.json"))
    assert code == 0 and "Reconstruction: PARTIAL" in out and "wallet-level, not person-level" in out


def test_cli_ranks_and_compares_without_a_database(tmp_path):
    code, out, err = cli("perf", "rank", "--ledger", str(FX / "ledger_scored_clean.json"), "--ledger", str(FX / "ledger_main.json"))
    assert code == 0, err
    rk = json.loads(out)
    assert len(rk["ranked"]) == 1 and len(rk["refused"]) == 1
    prov = tmp_path / "prov.json"
    prov.write_text(json.dumps({"source": "invented", "claims": {"realized_pnl_usd": "5000"}}))
    code, out, err = cli("perf", "compare", "--ledger", str(FX / "ledger_main.json"), "--provider", str(prov))
    assert code == 0 and "NOT VALIDATED" in out


def test_cli_refuses_to_store_a_fixture_in_the_tracked_database(tmp_path):
    code, out, err = cli("perf", "run", "--ledger", str(FX / "ledger_main.json"), "--save")
    assert code == 1 and "fixtures are never written to the tracked database" in err


def test_cli_stores_shows_and_verifies_a_run_in_a_temp_database(tmp_path, monkeypatch):
    dbp = str(tmp_path / "t.sqlite")
    env = {"MEMELAB_PRIVATE_DB": str(tmp_path / "private" / "p.sqlite")}
    code, out, err = cli("perf", "run", "--ledger", str(FX / "ledger_main.json"), "--save", "--db", dbp, "--now", "1791000000", env=env)
    assert code == 0, err
    assert "Stored as run 1 (new)" in out
    code, out, err = cli("perf", "run", "--ledger", str(FX / "ledger_main.json"), "--save", "--db", dbp, "--now", "1791000001", env=env)
    assert code == 0 and "already stored" in out
    code, out, err = cli("perf", "verify", "1", "--db", dbp, env=env)
    assert code == 0 and json.loads(out)["verified"] is True
    code, out, err = cli("perf", "show", "1", "--db", dbp, env=env)
    assert code == 0 and "Reconstruction: PARTIAL" in out
    code, out, err = cli("perf", "status", "--db", dbp, env=env)
    assert code == 0 and len(json.loads(out)["runs"]) == 1
    code, out, err = cli("perf", "verify", "99", "--db", dbp, env=env)
    assert code == 1


def test_cli_bad_ledger_is_an_error_not_a_traceback(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text(json.dumps({"schema": "nope"}))
    code, out, err = cli("perf", "run", "--ledger", str(f))
    assert code == 1 and "Traceback" not in err and "schema" in err


def test_the_content_guard_passes_with_the_new_files():
    code, out, err = cli("guard")
    assert code == 0, out + err
