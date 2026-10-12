"""Phase 12: social claims against on-chain chronology.

Invented data only (tests/fixtures/social/chrono/make_chrono.py builds every input). No network, no clock: every run has a fixed as_of.
"""
import copy
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from memelab import db
from memelab.social import alpha_store, chrono_core as C, chrono_store as S, registry as R, schema, store, wallet_assertions as WAS

ROOT = Path(__file__).resolve().parent.parent
FX = ROOT / "tests" / "fixtures" / "social" / "chrono"
_spec = importlib.util.spec_from_file_location("make_chrono", FX / "make_chrono.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
T0, H, MINT, W1, W2, W3 = M.T0, M.H, M.MINT, M.W1, M.W2, M.W3
CONF = json.loads((FX / "confident.json").read_text())
IND = json.loads((FX / "indeterminate.json").read_text())


def doc(posts=(), wallets=(), events=(), market=(), pool=(), monitoring=None, as_of=None, **kw):
    cov = {"posts_enumerated": True, "providers": {"social": "OK", "wallet": "OK", "market": "OK"},
           "wallet_monitoring": monitoring if monitoring is not None else [M.monitored(w["wallet"], T0 - 72 * H, T0 + 30 * H) for w in wallets]}
    cov.update(kw.pop("coverage", {}))
    return M.base("test", as_of or T0 + 32 * H, posts=list(posts), wallets=list(wallets), wallet_events=list(events), market=list(market),
                  pool_events=list(pool), coverage=cov, **kw)


def run(d, **pol):
    return C.analyze(d, pol or None)


def pats(r, name=None):
    return [p for p in r["patterns"] if name is None or p["pattern"] == name]


def flags(r, name=None):
    return [f for f in r["flags"] if name is None or f["flag"] == name]


def P(key="1", t=T0 + 2 * H, **kw):
    kw.setdefault("seen", t + 30 if t is not None else None)
    return M.post(key, t, **kw)


LINKED = M.wallet(W1, "SIGNATURE_VERIFIED")


def BUY(seed, t, w=W1, **kw):
    return M.event(seed, w, t, "SWAP", "BUY", **kw)


def SELL(seed, t, w=W1, **kw):
    return M.event(seed, w, t, "SWAP", "SELL", **kw)


# ---------- the two demonstration fixtures ----------

def test_fixture_files_match_their_generator(tmp_path):
    M.write(tmp_path)
    for n in ("confident.json", "indeterminate.json"):
        assert (tmp_path / n).read_text() == (FX / n).read_text()


def test_confident_fixture_orders_every_pair():
    r = run(CONF)
    assert r["order_status"] == "CONFIDENT" and r["is_fixture"]
    tb = pats(r, "TRADE_BEFORE_TALK")[0]
    assert tb["order"] == "CONFIDENT" and tb["action"] == "BUY" and tb["bucket"] == "INFERENCE"
    assert tb["trade_minus_talk"]["max_s"] < 0                   # the buy certainly came first
    assert abs(tb["trade_minus_talk"]["max_s"]) == 2 * H - 1 - 2 - 1   # 2 h minus provider and chain tolerances
    ta = pats(r, "TALK_BEFORE_TRADE")[0]
    assert ta["action"] == "SELL" and ta["trade_minus_talk"]["min_s"] > 0
    d = pats(r, "POTENTIAL_DISTRIBUTION_DURING_PROMOTION")[0]
    assert d["order"] == "CONFIDENT" and d["bucket"] == "INFERENCE"
    kinds = [e["kind"] for e in r["timeline"]]
    assert kinds.index("WALLET_BUY") < kinds.index("POST_PUBLISHED") < kinds.index("POST_FIRST_SEEN") < kinds.index("WALLET_SELL")
    assert "POOL_LP_REMOVE" in kinds and "PRICE_MOVE" in kinds and "LIQUIDITY_CHANGE" in kinds
    risk = {f["flag"] for f in r["flags"] if f["category"] == "RISK"}
    assert risk == {"TRADE_BEFORE_TALK", "POTENTIAL_DISTRIBUTION_DURING_PROMOTION"}
    # the uncertain wallet's buy is on the timeline but feeds no pattern
    assert all(p.get("wallet") != W2 for p in r["patterns"]) and flags(r, "ATTRIBUTION_UNCERTAIN")
    assert any(e.get("wallet") == W2 and e["wallet_class"] == "UNCERTAIN" for e in r["timeline"])


def test_indeterminate_fixture_says_so_and_claims_no_order():
    r = run(IND)
    assert r["order_status"] == "INDETERMINATE"
    assert {p["order"] for p in pats(r) if p["pattern"] in ("ORDER_INDETERMINATE", "POTENTIAL_DISTRIBUTION_DURING_PROMOTION")} == {"INDETERMINATE"}
    assert not pats(r, "TRADE_BEFORE_TALK") and not pats(r, "TALK_BEFORE_TRADE")
    assert all(p["bucket"] == "UNKNOWN" for p in pats(r, "ORDER_INDETERMINATE"))
    d = pats(r, "POTENTIAL_DISTRIBUTION_DURING_PROMOTION")[0]
    assert d["bucket"] == "HEURISTIC" and "not established" in d["note"]
    assert not r["summary"]["inference"][1:]                     # only the wallet association line; no ordered pattern is inferred
    assert any("intervals overlap" in x["text"] for x in r["summary"]["not_established"])
    assert {e["order_group"] for e in r["timeline"]} == {1}      # one overlapping group
    assert all(e["order_within_group"] == "NOT_ESTABLISHED" for e in r["timeline"])


# ---------- the prompt's test list ----------

def test_delayed_api_delivery_orders_by_publication_and_says_when_the_lab_knew():
    # published 02:00, delivered to the collector at 05:00; the wallet bought at 03:00
    r = run(doc([P(t=T0 + 2 * H, seen=T0 + 5 * H)], [LINKED], [BUY("d1", T0 + 3 * H)]))
    assert pats(r, "TALK_BEFORE_TRADE")[0]["order"] == "CONFIDENT"
    w = [x for x in r["warnings"] if x["code"] == "DELAYED_COLLECTION"][0]
    assert w["lag_s"] == 3 * H and "could not have reacted before it saw the post" in w["detail"]
    kinds = [e["kind"] for e in r["timeline"]]
    assert kinds.index("POST_PUBLISHED") < kinds.index("WALLET_BUY") < kinds.index("POST_FIRST_SEEN")
    assert flags(r, "DELAYED_COLLECTION")[0]["category"] == "DATA_QUALITY"


def test_missing_publication_time_uses_first_sighting_as_an_upper_bound_only():
    # unknown publication, first seen 03:00. A buy at 04:00 is certainly after; a buy at 01:00 is not ordered.
    r = run(doc([P(t=None, seen=T0 + 3 * H)], [LINKED], [BUY("m1", T0 + 4 * H), BUY("m2", T0 + 1 * H)]))
    by = {p["trade"]: p for p in pats(r) if p.get("trade")}
    assert by[M.sig("m1")]["pattern"] == "TALK_BEFORE_TRADE"
    assert by[M.sig("m2")]["pattern"] == "ORDER_INDETERMINATE"
    t = [e for e in r["timeline"] if e["kind"] == "POST_PUBLISHED"][0]
    assert t["at"]["lo"] is None and t["time_display"].startswith("no later than")


def test_missing_block_time_is_bounded_by_neighbouring_slots_or_left_unplaced():
    e_known1 = BUY("b1", T0 + 1 * H, slot=100)
    e_known2 = SELL("b2", T0 + 4 * H, slot=300)
    e_gap = BUY("b3", None, slot=200)
    r = run(doc([P(t=T0 + 5 * H)], [LINKED], [e_known1, e_known2, e_gap]))
    x = [e for e in r["timeline"] if e.get("signature") == M.sig("b3")][0]
    assert x["basis"] == "SLOT_BOUNDED" and x["at"]["lo"] == T0 + H - 2 and x["at"]["hi"] == T0 + 4 * H + 3
    assert pats(r, "TRADE_BEFORE_TALK") and any(p["trade"] == M.sig("b3") for p in pats(r, "TRADE_BEFORE_TALK"))
    assert flags(r, "CHAIN_TIME_MISSING")
    r2 = run(doc([P()], [LINKED], [BUY("b4", None, slot=None)]))
    assert [e["reason"] for e in r2["exclusions"]] == ["CHAIN_TIME_MISSING"]
    assert not any(p.get("trade") for p in r2["patterns"])


def test_token_symbol_collision_never_joins():
    impostor = {"chain": "solana", "contract": M.OTHER_MINT, "status": "resolved", "symbol": "LABCAT"}
    ticker_only = {"chain": None, "contract": None, "status": "unresolved", "symbol": "LABCAT"}
    other_chain = {"chain": "base", "contract": "0x" + "ab" * 20, "status": "resolved", "symbol": "LABCAT"}
    posts = [P("10", token=impostor), P("11", token=ticker_only), P("12", token=other_chain)]
    ev = BUY("s1", T0 + 1 * H, contract=M.OTHER_MINT)            # the wallet bought the impostor token
    r = run(doc(posts, [LINKED], [ev]))
    assert not r["patterns"] and not [e for e in r["timeline"] if e["kind"] in ("POST_PUBLISHED", "WALLET_BUY")]
    reasons = {(x["ref"], x["reason"]) for x in r["exclusions"]}
    assert ("x:10", "TOKEN_MISMATCH") in reasons and ("x:11", "TOKEN_UNRESOLVED") in reasons and ("x:12", "CHAIN_MISMATCH") in reasons
    assert (M.sig("s1"), "UNRELATED_ASSET") in reasons
    assert r["join_checks"]["rejected"]["TOKEN_MISMATCH"] == 1 and flags(r, "IDENTITY_JOIN_REJECTED")
    # wrong chain on wallets and candles is refused too
    bad_w = dict(LINKED, chain="base")
    bad_m = dict(M.candles([1.0] * 5, T0), chain="base")
    r = run(doc([P()], [bad_w], [], market=[bad_m]))
    assert {x["what"] for x in r["exclusions"] if x["reason"] == "CHAIN_MISMATCH"} == {"wallet", "candles"}


def test_conflicting_wallets_are_shown_but_never_attributed():
    contested = M.wallet(W2, "SELF_CLAIMED", others=["acct:x:id:fx2"], aid=5)
    disputed = M.wallet(W3, "DISPUTED", aid=6)
    claimed = M.wallet(W1, "SELF_CLAIMED", aid=7)
    evs = [BUY("cw2", T0 + H, w=W2), BUY("cw3", T0 + H + 60, w=W3), BUY("cw1", T0 + H + 120, w=W1)]
    r = run(doc([P()], [contested, disputed, claimed], evs))
    cls = {w["wallet"]: w["class"] for w in r["wallets"]}
    assert cls == {W1: "CLAIMED", W2: "CONTESTED", W3: "DISPUTED"}
    pairs = [p for p in pats(r) if p.get("trade")]
    assert {p["wallet"] for p in pairs} == {W1}
    assert pairs[0]["bucket"] == "HEURISTIC"                      # self-claimed only: heuristic, never inference
    assert {f["flag"] for f in r["flags"] if f["category"] == "DATA_QUALITY"} >= {"ATTRIBUTION_CONTESTED", "ATTRIBUTION_DISPUTED"}
    ne = " ".join(x["text"] for x in r["summary"]["not_established"])
    assert short(W2) in ne and short(W3) in ne


def short(a):
    return C.short(a)


def test_same_minute_ordering_ambiguity():
    # the page shows 02:00 (minute precision); the buy's block time is 02:00:40
    r = run(doc([P(t=T0 + 2 * H, precision=60, seen=T0 + 2 * H + 120)], [LINKED], [BUY("sm", T0 + 2 * H + 40)]))
    assert r["order_status"] == "INDETERMINATE"
    p = pats(r, "ORDER_INDETERMINATE")[0]
    assert p["trade_minus_talk"]["min_s"] < 0 < p["trade_minus_talk"]["max_s"]
    # the same timestamps at second precision are ordered
    r = run(doc([P(t=T0 + 2 * H, seen=T0 + 2 * H + 120)], [LINKED], [BUY("sm", T0 + 2 * H + 40)]))
    assert r["order_status"] == "CONFIDENT"
    # inside the tolerances they are not
    r = run(doc([P(t=T0 + 2 * H)], [LINKED], [BUY("sm2", T0 + 2 * H + 2)]))
    assert r["order_status"] == "INDETERMINATE"


def test_unrelated_transfer_and_transfers_are_never_sales():
    native = M.event("u1", W1, T0 + 3 * H, "NATIVE_TRANSFER_OUT", amount=5.0)
    native["legs"] = [{"asset_kind": "NATIVE", "contract": None, "direction": "OUT", "amount": 5.0}]
    other = M.event("u2", W1, T0 + 3 * H, "TOKEN_TRANSFER_OUT", amount=10.0, contract=M.OTHER_MINT)
    out = M.event("u3", W1, T0 + 3 * H + 60, "TOKEN_TRANSFER_OUT", amount=200.0, counterparty=W3)
    r = run(doc([P()], [LINKED], [native, other, out]))
    assert {x["reason"] for x in r["exclusions"] if x["ref"] in (M.sig("u1"), M.sig("u2"))} == {"UNRELATED_ASSET"}
    t = [e for e in r["timeline"] if e.get("signature") == M.sig("u3")][0]
    assert t["action"] == "TRANSFER_OUT" and "not a sale" in t["text"]
    assert not pats(r, "POTENTIAL_DISTRIBUTION_DURING_PROMOTION") and not pats(r, "TALK_BEFORE_TRADE")
    assert pats(r, "TALK_WITHOUT_OBSERVED_TRADE")


def test_transfer_between_two_associated_wallets_is_internal():
    w2 = M.wallet(W2, "SIGNATURE_VERIFIED", aid=9)
    o = M.event("int", W1, T0 + 3 * H, "TOKEN_TRANSFER_OUT", counterparty=W2)
    i = dict(M.event("int", W2, T0 + 3 * H, "TOKEN_TRANSFER_IN", counterparty=W1))
    r = run(doc([P()], [LINKED, w2], [o, i]))
    assert {e["action"] for e in r["timeline"] if e.get("signature") == M.sig("int")} == {"INTERNAL_TRANSFER"}


def test_two_people_using_one_custodian():
    # two accounts both say an exchange deposit address is theirs; the address is labelled exchange custody
    cex_a = M.wallet(M.CEX, "UNSUPPORTED_CUSTODY", label="CUSTODY_EXCHANGE", others=["acct:x:id:fx2"], aid=11)
    r = run(doc([P()], [cex_a], [SELL("cx", T0 + 3 * H, w=M.CEX)]))
    assert r["wallets"][0]["class"] == "EXCLUDED_CUSTODY"
    assert not [e for e in r["timeline"] if e.get("signature")] and not [p for p in r["patterns"] if p.get("trade")]
    assert [x["reason"] for x in r["exclusions"]] == ["CUSTODY_WALLET"]
    assert flags(r, "CUSTODY_WALLET_EXCLUDED") and not [f for f in r["flags"] if f["category"] == "RISK"]
    assert pats(r, "TALK_WITHOUT_OBSERVED_TRADE")[0]["monitoring_coverage"] == "NO_ATTRIBUTED_WALLET"
    # a linked wallet sending to the exchange: moved to custody, not an observed sale
    dep = M.event("dep", W1, T0 + 3 * H, "TOKEN_TRANSFER_OUT", counterparty=M.CEX, label="CUSTODY_EXCHANGE", custody="CUSTODY_EXCHANGE")
    r = run(doc([P()], [LINKED], [dep]))
    e = [x for x in r["timeline"] if x.get("signature") == M.sig("dep")][0]
    assert e["action"] == "TRANSFER_TO_CUSTODY" and "not observable" in e["text"]
    assert not pats(r, "POTENTIAL_DISTRIBUTION_DURING_PROMOTION")


def test_promotional_repost_uses_the_repost_time_and_is_marked():
    orig_time, repost_time = T0 - 10 * H, T0 + 2 * H
    rp = P("20", t=repost_time, kind="REPOST", repost_of="x:999")
    r = run(doc([rp], [LINKED], [BUY("rp1", T0 + 1 * H), SELL("rp2", T0 + 3 * H)]))
    t = [e for e in r["timeline"] if e["kind"] == "POST_PUBLISHED"][0]
    assert t["talk_kind"] == "REPOST" and t["at"]["lo"] == repost_time - 1 and "not the source's own words" in t["text"]
    assert pats(r, "TRADE_BEFORE_TALK")[0]["talk_kind"] == "REPOST"
    d = pats(r, "POTENTIAL_DISTRIBUTION_DURING_PROMOTION")[0]
    assert d["talk_kind"] == "REPOST" and d["order"] == "CONFIDENT"
    assert orig_time not in [e.get("point") for e in r["timeline"]]


def test_missing_price_is_not_established_and_live_quotes_never_stand_in():
    live = dict(M.candles([1.0, 2.0, 3.0], T0), as_of_kind="OBSERVED_AT_FETCH")
    r = run(doc([P()], [LINKED], [BUY("mp", T0 + 3 * H)], market=[live]))
    assert r["market"]["status"] == "NO_HISTORY" and not [e for e in r["timeline"] if e["kind"] == "PRICE_MOVE"]
    assert [x["reason"] for x in r["exclusions"] if x["what"] == "candles"] == ["LIVE_QUOTE_AS_HISTORY"]
    assert flags(r, "MISSING_PRICE_HISTORY")
    assert any("no historical candles" in x["text"] for x in r["summary"]["not_established"])
    # a provider marked unavailable is reported as such
    r = run(doc([P()], [LINKED], [], coverage={"providers": {"social": "OK", "wallet": "OK", "market": "UNAVAILABLE"}}))
    assert r["market"]["status"] == "PROVIDER_UNAVAILABLE"


def test_market_source_fallback_and_no_future_candles():
    a = M.candles([1.0] * 10, T0 - 2 * H, source="primary")
    b = M.candles([1.0, 1.0, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5], T0 - 2 * H, source="secondary")
    r = run(doc([P()], [LINKED], [], market=[b, a]), market_source_preference=["primary", "secondary"])
    assert r["market"]["source"] == "primary" and not r["market"]["fallback_used"]
    r = run(doc([P()], [LINKED], [], market=[b]), market_source_preference=["primary", "secondary"])
    assert r["market"]["source"] == "secondary" and r["market"]["fallback_used"]
    late = M.candles([1.0, 9.0], T0 + 40 * H)                     # after as_of
    r = run(doc([P()], [LINKED], [], market=[late]))
    assert r["market"]["status"] == "NO_HISTORY"


def test_source_deletion_keeps_the_evidence_and_brackets_the_removal():
    obs = [{"observation_id": "o2", "observed_at": T0 + 6 * H, "status": "OK"}, {"observation_id": "o3", "observed_at": T0 + 9 * H, "status": "DELETED"}]
    r = run(doc([P(extra_obs=obs)], [LINKED], [SELL("del", T0 + 7 * H)]))
    rm = [e for e in r["timeline"] if e["kind"] == "POST_REMOVAL_OBSERVED"][0]
    assert rm["at"]["lo"] == T0 + 6 * H - 5 and rm["at"]["hi"] == T0 + 9 * H + 5
    assert "remaining evidence" in rm["text"] and "o3" in rm["links"][-1]["ref"]
    t = [e for e in r["timeline"] if e["kind"] == "POST_PUBLISHED"][0]
    assert t["links"][0]["ref"].startswith("https://example.invalid/fixture/status/")
    assert pats(r, "TALK_BEFORE_TRADE")                            # the deleted post still counts as said
    assert any("returned DELETED" in x["text"] for x in r["summary"]["fact"])


# ---------- absence, attribution and wording ----------

def test_absence_of_a_monitored_trade_is_never_evidence():
    for wallets, mon, expect in (([], [], "NO_ATTRIBUTED_WALLET"), ([LINKED], [], "NONE"),
                                 ([LINKED], [M.monitored(W1, T0, T0 + 3 * H)], "PARTIAL"), ([LINKED], None, "FULL")):
        r = run(doc([P()], wallets, [], monitoring=mon))
        p = pats(r, "TALK_WITHOUT_OBSERVED_TRADE")[0]
        assert p["monitoring_coverage"] == expect and p["bucket"] == "UNKNOWN" and "not evidence that none happened" in p["note"]
        assert not [f for f in r["flags"] if f["category"] == "RISK"]
    r = run(doc([P()], [LINKED], [], coverage={"providers": {"social": "OK", "wallet": "UNAVAILABLE", "market": "OK"}}))
    assert pats(r, "TALK_WITHOUT_OBSERVED_TRADE")[0]["monitoring_coverage"] == "PROVIDER_UNAVAILABLE"
    # trade without observed talk says whether posts were enumerated
    r = run(doc([], [LINKED], [BUY("tw", T0)], window={"from": T0 - H, "to": T0 + H}, coverage={"posts_enumerated": False}))
    p = pats(r, "TRADE_WITHOUT_OBSERVED_TALK")[0]
    assert p["posts_enumerated"] is False and "may exist" in p["note"]


def test_uncertain_attribution_never_becomes_an_accusation():
    for level in ("THIRD_PARTY_CLAIMED", "HYPOTHESIS_ONLY", "NONE"):
        r = run(doc([P()], [M.wallet(W1, level)], [BUY("ua1", T0), SELL("ua2", T0 + 3 * H)]))
        assert not [p for p in r["patterns"] if p.get("trade")]
        assert not [f for f in r["flags"] if f["category"] in ("RISK", "CORROBORATION")]
        assert flags(r, "ATTRIBUTION_UNCERTAIN")
        assert all("linked to the source" not in e["text"] for e in r["timeline"])


def test_disclosed_position_is_corroboration_not_risk():
    r = run(doc([P(position="holds")], [LINKED], [BUY("dp", T0)]))
    assert [f["category"] for f in flags(r, "DISCLOSED_POSITION_CONSISTENT")] == ["CORROBORATION"]
    assert not [f for f in r["flags"] if f["category"] == "RISK"]


def test_risk_flags_are_never_fact_and_the_text_guard_refuses_accusations():
    r = run(CONF)
    for f in r["flags"]:
        if f["category"] == "RISK":
            assert f["bucket"] in ("INFERENCE", "HEURISTIC") and f["attribution"] in ("LINKED", "CLAIMED") and f["evidence"]
    with pytest.raises(ValueError):
        C._flag(("solana", MINT), "s", "X", "RISK", "FACT", "r", attribution="LINKED")
    with pytest.raises(ValueError):
        C._flag(("solana", MINT), "s", "X", "RISK", "INFERENCE", "r", attribution="UNCERTAIN")
    bad = copy.deepcopy(r)
    bad["patterns"][0]["note"] = "the source is an insider"
    with pytest.raises(RuntimeError):
        C.guard_text(bad)
    C.guard_text({"note": "supplied by the provider"})              # whole words only ('lied' inside 'supplied' is fine)
    text = C.report(r) + C.report(run(IND))
    assert not C._FORBIDDEN_RE.search(text)
    # a post id or label that happens to contain a forbidden word does not get past the guard either
    d = copy.deepcopy(CONF)
    d["posts"][0]["item_key"] = "x:scam-alert"
    with pytest.raises(RuntimeError):
        run(d)


def test_links_trace_to_original_evidence():
    r = run(CONF)
    for x in r["summary"]["fact"]:
        assert x["links"], x["text"]
    for x in r["summary"]["inference"]:
        assert x["links"], x["text"]
    sell = [e for e in r["timeline"] if e["kind"] == "WALLET_SELL"][0]
    assert {l["kind"] for l in sell["links"]} >= {"tx_url", "tx"} and sell["links"][0]["ref"].startswith("https://solscan.io/tx/")
    d = flags(r, "POTENTIAL_DISTRIBUTION_DURING_PROMOTION")[0]
    assert any(e.startswith("https://example.invalid/fixture/status/") for e in d["evidence"]) and M.sig("c-sell-w1") in d["evidence"]


# ---------- configuration, dedupe, staleness, leakage, determinism ----------

def test_time_window_configuration():
    far = BUY("far", T0 + 2 * H - 30 * H)                          # 30 h before the post
    r = run(doc([P()], [LINKED], [far]))
    assert pats(r, "TRADE_WITHOUT_OBSERVED_TALK") and pats(r, "TALK_WITHOUT_OBSERVED_TRADE")
    r = run(doc([P()], [LINKED], [far]), pair_window_s=40 * H)
    assert pats(r, "TRADE_BEFORE_TALK")
    r = run(doc([P()], [LINKED], [far]), window_before_s=10 * H)
    assert [x["reason"] for x in r["exclusions"]] == ["OUTSIDE_WINDOW"]
    with pytest.raises(ValueError):
        run(doc([P()]), not_a_key=1)


def test_dedupe_of_posts_sightings_and_events():
    p1 = P("30")
    p2 = P("30", extra_obs=[{"observation_id": "o9", "observed_at": T0 + 4 * H, "status": "OK"}])
    e = BUY("dd", T0)
    r = run(doc([p1, p2, copy.deepcopy(p1)], [LINKED, LINKED], [e, copy.deepcopy(e)]))
    assert len([x for x in r["timeline"] if x["kind"] == "POST_PUBLISHED"]) == 1
    assert len([x for x in r["timeline"] if x.get("signature") == M.sig("dd")]) == 1
    assert r["dedupe"]["wallet_events_dropped"] == 1 and r["dedupe"]["post_rows_merged"] >= 2
    assert len(r["wallets"]) == 1


def test_stale_evidence_warnings():
    r = run(doc([P()], [LINKED], [], monitoring=[M.monitored(W1, T0 - 72 * H, T0 + 3 * H)],
                market=[M.candles([1.0] * 6, T0)]))
    codes = {w["code"] for w in r["warnings"]}
    assert {"STALE_WALLET_DATA", "STALE_MARKET_DATA", "STALE_POST_CHECK"} <= codes


def test_nothing_after_as_of_is_used():
    r = run(doc([P()], [LINKED], [SELL("fut", T0 + 40 * H)], as_of=T0 + 30 * H), window_after_s=30 * 24 * H)
    assert r["window"]["to"] == T0 + 30 * H                         # the window is clamped to as_of
    assert [x["reason"] for x in r["exclusions"]] == ["OUTSIDE_WINDOW"]
    assert not [e for e in r["timeline"] if e.get("signature")]
    r = run(doc([P()], [LINKED], [SELL("fut2", T0 + 40 * H)], as_of=T0 + 30 * H, window={"from": T0, "to": T0 + 50 * H}))
    assert r["window"]["to"] == T0 + 30 * H and not [e for e in r["timeline"] if e.get("signature")]


def test_deterministic_and_input_hash_follows_the_policy():
    a, b = run(CONF), run(copy.deepcopy(CONF))
    assert a["result_sha256"] == b["result_sha256"]
    c = run(CONF, pair_window_s=3600)
    assert c["input_sha256"] != a["input_sha256"]
    with pytest.raises(ValueError):
        C.analyze({"schema": "nope"})
    with pytest.raises(ValueError):
        C.analyze(dict(CONF, token={"symbol": "LABCAT"}))


# ---------- database, migration, CLI ----------

def _con(tmp_path, name="c.sqlite"):
    p = tmp_path / name
    db.init_db(p)
    con = sqlite3.connect(p)
    con.row_factory = sqlite3.Row
    return con, p


def test_migration_12_rolls_back_cleanly_and_leaves_phase_11_alone(tmp_path):
    con, _ = _con(tmp_path)
    assert schema.current_version(con) == schema.LATEST and 12 in schema.ALL_VERSIONS
    before = {r[0]: r[1] for r in con.execute("SELECT name, sql FROM sqlite_master WHERE name LIKE 'social_alpha_%'")}
    assert schema.rollback(con, 11) == [12]
    assert not con.execute("SELECT 1 FROM sqlite_master WHERE name LIKE 'social_chrono_%'").fetchall()
    assert {r[0]: r[1] for r in con.execute("SELECT name, sql FROM sqlite_master WHERE name LIKE 'social_alpha_%'")} == before
    assert schema.migrate(con) == [12]


def test_schema_refuses_fact_risk_flags_and_risk_without_attribution(tmp_path):
    con, _ = _con(tmp_path)
    con.execute("INSERT INTO social_chrono_runs(engine_version,rules_version,chain,contract,source_id,as_of,order_status,policy_sha256,input_sha256,result_sha256,"
                "n_timeline,n_patterns,input_json,result_json,created_at) VALUES ('e','r','solana','M','s',1,'CONFIDENT','p','i','r',0,0,'{}','{}',1)")
    ins = ("INSERT INTO social_chrono_flags(run_id,flag_key,chain,contract,source_id,flag,category,bucket,rule,order_status,attribution,evidence_json) "
           "VALUES (1,?,'solana','M','s','X',?,?,'r','CONFIDENT',?,?)")
    for k, cat, bucket, att, ev in (("a", "RISK", "FACT", "LINKED", '["e"]'), ("b", "RISK", "INFERENCE", "UNCERTAIN", '["e"]'),
                                    ("c", "CONTEXT", "FACT", None, '["e"]'), ("d", "RISK", "HEURISTIC", "CLAIMED", "[]")):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute(ins, (k, cat, bucket, att, ev))
    con.execute(ins, ("ok", "RISK", "HEURISTIC", "CLAIMED", '["e"]'))


def test_run_store_verify_flags_and_tamper(tmp_path):
    con, _ = _con(tmp_path)
    r = run(CONF)
    s = S.save_run(con, CONF, r, now=5)
    assert s["created"] and not S.save_run(con, CONF, r, now=6)["created"]
    assert S.verify_run(con, s["run_id"])["verified"]
    assert S.current_flags(con) == []                              # fixtures hidden by default
    fl = S.current_flags(con, chain="solana", contract=MINT, category="RISK", include_fixtures=True)
    assert {f["flag"] for f in fl} == {"TRADE_BEFORE_TALK", "POTENTIAL_DISTRIBUTION_DURING_PROMOTION"} and all(f["evidence"] for f in fl)
    stored = json.loads(con.execute("SELECT result_json FROM social_chrono_runs").fetchone()[0])
    stored["order_status"] = "INDETERMINATE"
    con.execute("UPDATE social_chrono_runs SET result_json=?", (C.canon(stored),))
    assert not S.verify_run(con, s["run_id"])["verified"]
    assert S.status(con)["flags"] == len(r["flags"])


def _claim(con, *, item, account, token_ref, published, observed, tokens, direction="LONG", position="not_disclosed"):
    store.register_analysis_version(con, "extract-v1", "claims", "fixture")
    ob = store.record_observation(con, platform="x", access_mode="fixture", collector="fixture", provider_item_id=item, account_id=account,
                                  published_at=published, observed_at=observed, content_hash="a" * 64, now=T0 + 31 * H,
                                  original_url=f"https://example.invalid/fixture/status/{item}")
    cid = store.add_claim(con, claim_type="CALL", analysis_version="extract-v1", item_key=ob["item_key"], account_id=account, token_ref_id=token_ref,
                          direction=direction, observation_id=ob["id"], now=T0 + 31 * H)["id"]
    con.execute("INSERT INTO social_claim_extractions(extraction_key,observation_id,item_key,content_hash,context_sha,extractor,extractor_version,analysis_version,status,mode,extracted_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)", (f"k{item}", ob["id"], ob["item_key"], "a" * 64, "c", "deterministic", "v1", "extract-v1", "ok", "none", T0 + 31 * H))
    eid = con.execute("SELECT MAX(extraction_id) FROM social_claim_extractions").fetchone()[0]
    con.execute("INSERT INTO social_claim_attributes(claim_id,extraction_id,claim_index,category,assertion_type,stance,negated,conditional,sarcasm_suspected,time_horizon,"
                "author_position,attribution,uncertainty,uncertainty_reasons_json,verification,narrative_tags_json,tokens_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, eid, 0, "bullish", "prediction", "positive", 0, 0, 0, "days", position, "author", "low", "[]", "unverified_text_claim", "[]", json.dumps(tokens)))
    return ob["item_key"]


def _event_rows(con, wallet, sig, t, etype, side, amount, fetch_id):
    con.execute("INSERT INTO social_wallet_events(event_key,chain,wallet_address,signature,slot,block_time,event_type,swap_side,classification_rule,classification_version,"
                "classification_confidence,classification_basis_json,observed_scope,freshness,provider,fetch_id,row_sha256,ingested_at,is_fixture) "
                "VALUES (?,?,?,?,?,?,?,?,'fixture.v1','v1','HIGH','{}','LIVE','FRESH','fixture',?,?,?,1)",
                (sig + wallet, "solana", wallet, sig, None, t, etype, side, fetch_id, "f" * 64, T0 + 31 * H))
    eid = con.execute("SELECT MAX(event_id) FROM social_wallet_events").fetchone()[0]
    con.execute("INSERT INTO social_wallet_event_legs VALUES (?,0,'TOKEN',?,?,?,NULL,NULL)", (eid, MINT, "IN" if side == "BUY" else "OUT", amount))


def test_build_input_from_stored_rows_end_to_end(tmp_path):
    con, _ = _con(tmp_path)
    ent = R.ensure_account(con, "x", handle="fixture_src", provider_user_id="fx1", fixture_label="invented source", now=T0 - 100 * H)
    acct = R.get_entity(con, ent)["account_id"]
    store.upsert_trader(con, "fx_trader", "Invented trader", now=T0 - 100 * H)
    store.link_trader_account(con, "fx_trader", acct, "LAB_ASSERTED", evidence_status="INFERENCE", now=T0 - 100 * H)
    ref = store.upsert_token_ref(con, chain="solana", contract=MINT, symbol="LABCAT", now=T0 - 100 * H)
    ref_id = ref["ref_id"] if isinstance(ref, dict) else ref
    oref = store.upsert_token_ref(con, chain="solana", contract=M.OTHER_MINT, symbol="LABCAT", now=T0 - 100 * H)
    oref_id = oref["ref_id"] if isinstance(oref, dict) else oref
    good = [{"status": "resolved", "chain": "solana", "contract": MINT}]
    _claim(con, item="501", account=acct, token_ref=ref_id, published=T0 + 2 * H, observed=T0 + 2 * H + 30, tokens=good)
    _claim(con, item="502", account=acct, token_ref=oref_id, published=T0 + 2 * H, observed=T0 + 2 * H + 30,
           tokens=[{"status": "resolved", "chain": "solana", "contract": M.OTHER_MINT}])
    WAS.record(con, account_entity=ent, chain="solana", wallet_address=W1, evidence_type="OFFICIAL_SELF_DISCLOSURE",
               evidence_ref="https://example.invalid/fixture/bio-wallet", recorded_by="elving", observed_at=T0 - 50 * H, now=T0 - 50 * H)
    con.execute("INSERT INTO social_tracked_wallets(chain,wallet_address,status,reason,selection_basis,added_by,added_at,watch_since,is_fixture) "
                "VALUES ('solana',?,'ACTIVE','fixture','MANUAL','elving',?,?,1)", (W1, T0 - 72 * H, T0 - 72 * H))
    con.execute("INSERT INTO social_wallet_fetches(fetch_key,provider,chain,wallet_address,fetched_at,status,is_fixture) VALUES ('fk','fixture','solana',?,?,'OK',1)",
                (W1, T0 + 30 * H))
    _event_rows(con, W1, M.sig("db-buy"), T0, "SWAP", "BUY", 1000.0, 1)
    _event_rows(con, W1, M.sig("db-sell"), T0 + 5 * H, "SWAP", "SELL", 400.0, 1)
    alpha_store.put_series(con, [M.candles([1.0] * 8 + [1.5] * 30, T0 - 6 * H)], fixture=True, now=T0 + 31 * H)
    con.commit()
    d = S.build_input(con, chain="solana", contract=MINT, source_id="fx_trader", as_of=T0 + 32 * H, annotations={"posts_enumerated": True})
    assert {p["item_key"] for p in d["posts"]} == {"x:501", "x:502"} and d["wallets"][0]["level"] == "SELF_CLAIMED"
    assert d["coverage"]["wallet_monitoring"][0]["from"] == T0 - 72 * H
    r = C.analyze(d)
    assert r["order_status"] == "CONFIDENT"
    assert {p["pattern"] for p in r["patterns"]} >= {"TRADE_BEFORE_TALK", "TALK_BEFORE_TRADE", "POTENTIAL_DISTRIBUTION_DURING_PROMOTION"}
    assert all(p["bucket"] == "HEURISTIC" for p in r["patterns"] if p.get("trade"))     # self-claimed wallet only
    assert ("x:502", "TOKEN_MISMATCH") in {(x["ref"], x["reason"]) for x in r["exclusions"]}
    assert r["market"]["status"] == "CANDLES" and r["market"]["moves"]
    s = S.save_run(con, d, r, now=T0 + 32 * H)
    assert S.verify_run(con, s["run_id"])["verified"]
    with pytest.raises(ValueError):
        S.build_input(con, chain="solana", contract=MINT, source_id="nobody", as_of=T0)


def _cli(args):
    env = {k: v for k, v in os.environ.items() if k != "MEMELAB_DB"}
    return subprocess.run([sys.executable, "-m", "memelab", "social", "chrono"] + args, cwd=ROOT, capture_output=True, text=True, env=env)


def test_cli_demo_and_fixtures_never_reach_the_tracked_database(tmp_path):
    p = _cli(["run", "--input", str(FX / "confident.json")])
    assert p.returncode == 0, p.stderr
    assert "INVENTED FIXTURE DATA" in p.stdout and "Order between posts and trades: CONFIDENT" in p.stdout
    assert "Absence of a monitored trade is not evidence" in p.stdout
    p = _cli(["run", "--input", str(FX / "indeterminate.json")])
    assert p.returncode == 0 and "Order between posts and trades: INDETERMINATE" in p.stdout
    dbp = str(tmp_path / "cli.sqlite")
    p = _cli(["run", "--input", str(FX / "confident.json"), "--save", "--db", dbp])
    assert p.returncode == 0 and "Stored as run 1 (new)" in p.stdout, p.stderr
    assert json.loads(_cli(["verify", "1", "--db", dbp]).stdout)["verified"] is True
    fl = json.loads(_cli(["flags", "--db", dbp, "--include-fixtures", "--category", "RISK"]).stdout)
    assert {f["flag"] for f in fl} == {"TRADE_BEFORE_TALK", "POTENTIAL_DISTRIBUTION_DURING_PROMOTION"}
    assert "Timeline" in _cli(["show", "1", "--db", dbp]).stdout
    assert json.loads(_cli(["status", "--db", dbp]).stdout)["runs"][0]["is_fixture"] == 1
    p = _cli(["run", "--input", str(FX / "confident.json"), "--save"])
    assert p.returncode == 1 and "never written to the tracked database" in p.stderr
    bad = tmp_path / "bad.json"; bad.write_text("{}")
    assert _cli(["run", "--input", str(bad)]).returncode == 1
    assert _cli(["run", "--token", "LABCAT", "--source", "x", "--as-of", "1", "--db", dbp]).returncode == 1
