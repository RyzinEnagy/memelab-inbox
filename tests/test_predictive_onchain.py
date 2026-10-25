"""Phase 09: on-chain, liquidity and authority features onchain-1, the on-chain models, the structural veto and size cap, the
wallet-movement rules (memelab/predictive/onchain.py) and the read-only collector adapter (memelab/predictive/depth_adapter.py).

Synthetic, seeded fixtures and temp files only; fitted fixture cards carry NO_REAL_HISTORICAL_EVIDENCE and every adapter result
here is TEST_ONLY (no forward collector row exists). The real run is audits/predictive-intelligence/phase_09/probes/run_onchain.py.
No network, fixed times. Scenario ids from the package's ADVERSARIAL_SCENARIOS.md; CX-09 is this phase's new counterexample (a
collector read captured after the decision used as depth at the decision).
"""
from __future__ import annotations

import ast
import inspect
import json
import math
import socket
import sqlite3
import types
from pathlib import Path

import numpy as np
import pytest

from memelab.predictive import baselines as B
from memelab.predictive import contract as C
from memelab.predictive import depth_adapter as DA
from memelab.predictive import features as F
from memelab.predictive import labels as L
from memelab.predictive import onchain as O
from memelab.predictive import sources as SRC
from memelab.predictive import store as S

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures" / "predictive"
H = types.ModuleType("asof_helpers")
exec(compile((FIX / "asof_helpers.py").read_text(), str(FIX / "asof_helpers.py"), "exec"), H.__dict__)
T1, T1B, T2 = L.T1, L.T1B, L.T2
H0 = L.holdout_start()
D0 = C.parse_utc("2026-10-01T00:00:00Z")
MINT = H.MINT_A
MINT_B = H.MINT_B


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network use in a Phase 09 test")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(SRC, "curl_get", refuse)


# ---------------------------------------------------------------- export fixtures with the lab's rationale lines
def breakdown(*, mech="token mechanics clean (no mint/freeze/delegate/fee/hook issues)", fee="transfer fee 0.00%", lp="LP risk HIGH",
              locked="LP locked/burned 40%", route="route OK, 2 hop(s)", friction="round-trip friction 1.84%",
              largest="largest unexplained holder 9.4%", cluster="cluster-adjusted ownership 12.0% (confidence HIGH)",
              early="early wallets HOLDING", wash="manipulation screen MOSTLY ORGANIC / wash LOW", extra=None):
    b = {"token_lp_safety": {"rationale": [x for x in (mech, fee, "metadata immutable", lp, locked) if x]},
         "market_execution": {"rationale": [x for x in ("liquidity $50,000", "executable sell depth $1,000 at 3% impact", route, friction) if x]},
         "supply_ownership": {"rationale": [x for x in ("adjusted top-10 holds 12.5%", largest, cluster, "dev/insider holding 0.0%", early) if x]},
         "demand_order_flow": {"rationale": [x for x in ("net buyers 24h -4", wash) if x]}}
    for k, v in (extra or {}).items():
        b[k]["rationale"].append(v)
    return json.dumps(b)


def thesis(mint, created_at, *, fatal=None, bd=None, t=None, **snapkw):
    row = H.thesis(mint, created_at, fatal=fatal, **snapkw)
    sn = json.loads(row["snapshot_json"])
    sn["t"] = created_at if t is None else t
    row["snapshot_json"] = json.dumps(sn)
    row["score_breakdown_json"] = bd if bd is not None else breakdown()
    return row


def token(mint, program=O.TOKEN_2022, pool=H.POOL_A, **kw):
    tk = H.token(mint, pool=pool, first_seen_at=H.T0, **kw)
    tk["token_program"] = program
    return tk


def exports(rows_by_commit):
    out = []
    for i, (t, rows) in enumerate(rows_by_commit):
        out.append(H.export(f"c{i + 1}", t, rows, [token(MINT), token(MINT_B, pool=H.POOL_B)]))
    return out


def store(tmp_path, rows_by_commit, name="s.sqlite"):
    con = S.connect(tmp_path / name)
    S.ingest_exports(con, exports(rows_by_commit), now=H.T0 + 30 * 86400)
    con.commit()
    return con


def world(tmp_path, *, second_fatal=None, second_bd=None, second_snap=None, third=True, name="s.sqlite"):
    d1, d2, d3 = H.D1, H.D2, H.D3
    r1 = thesis(MINT, d1 - 900, liquidity=50000.0, exit_cap_3pct=1000.0, adj_top10=12.5)
    r2 = thesis(MINT, d2 - 700, fatal=second_fatal or [], bd=second_bd, status="REJECTED",
                **(second_snap or dict(liquidity=20000.0, exit_cap_3pct=500.0, adj_top10=30.0)))
    r3 = thesis(MINT, d3 - 500, fatal=[{"flag": "CANNOT_EXIT_5K", "category": "exitability"}], liquidity=5000.0, exit_cap_3pct=50.0,
                adj_top10=60.0, bd=breakdown(lp="LP risk CRITICAL", locked="LP locked/burned 0%"))
    b1 = thesis(MINT_B, d2 - 600)
    commits = [(d1, [r1]), (d2, [r1, r2, b1])] + ([(d3, [r1, r2, r3, b1])] if third else [])
    return store(tmp_path, commits, name=name), (d1, d2, d3)


def vals(s):
    return {k: v["value"] for k, v in s["values"].items()}


def why(s):
    return {k: v["missing_reason"] for k, v in s["values"].items() if v["value"] is None}


# ---------------------------------------------------------------- parsing (rationale and flags)
def test_current_values_match_the_rationale_lines_and_flags():
    row = thesis(MINT, 100.0, fatal=[{"flag": "MINT_AUTHORITY_ACTIVE"}, {"flag": "TOP10_GT_50PCT"}],
                 bd=breakdown(mech="token mechanics 1 critical issue(s)", fee="transfer fee 2.50%", lp="LP risk MODERATE",
                              locked="LP locked/burned 95%", route="route OK, 3 hop(s)", friction="round-trip friction 4.20%",
                              largest="largest unexplained holder 16.0%", cluster="cluster-adjusted ownership 30.0% (confidence LOW)",
                              early="early wallets DISTRIBUTING", wash="manipulation screen MIXED / UNCERTAIN / wash MODERATE"),
                 liquidity=40000.0, exit_cap_3pct=2000.0)
    v = O.current_values(O.parse_row(row, token(MINT, program=O.TOKEN_SPL)))
    want = {"oc_structural_fatal": 1.0, "oc_distribution_fatal": 1.0, "oc_mechanics_issues": 1.0, "oc_mint_authority_active": 1.0,
            "oc_freeze_authority_active": 0.0, "oc_transfer_fee_pct": 2.5, "oc_token2022": 0.0, "oc_lp_risk_ord": 1.0,
            "oc_lp_locked_pct": 95.0, "oc_exit_cap_share": 0.05, "oc_no_sell_route": 0.0, "oc_route_hops": 3.0,
            "oc_round_trip_friction_pct": 4.2, "oc_largest_unexplained_pct": 16.0, "oc_cluster_confidence_ord": 0.0,
            "oc_early_wallet_dir_ord": 3.0, "oc_wash_ord": 1.0}
    assert {k: v[k][0] for k in want} == want
    assert all(v[k][1] is None for k in want)


def test_flag_families_and_unknown_flags():
    for flags, s, d in (([], 0, 0), (["NO_SELL_ROUTE"], 1, 0), (["CANNOT_EXIT_5K"], 1, 0), (["LP_RISK_CRITICAL"], 1, 0),
                        (["INSIDER_DISTRIBUTION"], 0, 1), (["WASH_TRADING_HIGH"], 0, 0), (["SOMETHING_NEW"], 0, 0),
                        (["FREEZE_AUTHORITY_ACTIVE", "DEV_WALLET_FARM"], 1, 1)):
        row = thesis(MINT, 100.0, fatal=[{"flag": f} for f in flags])
        v = O.current_values(O.parse_row(row, token(MINT)))
        assert (v["oc_structural_fatal"][0], v["oc_distribution_fatal"][0]) == (s, d), flags


def test_unknown_lines_are_not_observed_and_new_formats_are_unparseable():
    bd = breakdown(lp="UNKNOWN: lp_risk label missing", locked="UNKNOWN: LP locked/burned % missing", early="early wallets UNKNOWN",
                   wash="manipulation screen n/a / wash n/a", largest=None, cluster=None, route=None, friction=None)
    v = O.current_values(O.parse_row(thesis(MINT, 100.0, bd=bd), token(MINT)))
    assert v["oc_lp_risk_ord"] == (None, "NOT_OBSERVED_BY_LAB")
    assert v["oc_lp_locked_pct"] == (None, "NOT_OBSERVED_BY_LAB")
    assert v["oc_early_wallet_dir_ord"] == (None, "NOT_OBSERVED_BY_LAB")
    assert v["oc_wash_ord"] == (None, "NOT_OBSERVED_BY_LAB")
    assert v["oc_largest_unexplained_pct"] == (None, "UNPARSEABLE")          # bucket present, no line, no UNKNOWN line
    # a rationale written by a later m24 version in another wording is never guessed (PI-D-008)
    bd2 = breakdown(locked="LP is 40% locked", lp="lp risk: high")
    v2 = O.current_values(O.parse_row(thesis(MINT, 100.0, bd=bd2), token(MINT)))
    assert v2["oc_lp_locked_pct"] == (None, "UNPARSEABLE") and v2["oc_lp_risk_ord"] == (None, "UNPARSEABLE")
    v3 = O.current_values(O.parse_row(dict(thesis(MINT, 100.0), score_breakdown_json="{not json"), token(MINT)))
    assert v3["oc_lp_risk_ord"][1] == "UNPARSEABLE"
    v4 = O.current_values(O.parse_row(dict(thesis(MINT, 100.0), score_breakdown_json=None), token(MINT)))
    assert v4["oc_lp_risk_ord"][1] == "ABSENT_IN_SNAPSHOT"


def test_authority_needs_observed_mechanics_and_a_contradiction_is_refused():
    no_mech = breakdown(mech="UNKNOWN: token mechanics missing")
    v = O.current_values(O.parse_row(thesis(MINT, 100.0, bd=no_mech), token(MINT)))
    assert v["oc_mint_authority_active"] == (None, "NOT_OBSERVED_BY_LAB")      # no flag is not "revoked" without a reading
    clash = O.current_values(O.parse_row(thesis(MINT, 100.0, fatal=[{"flag": "MINT_AUTHORITY_ACTIVE"}]), token(MINT)))
    assert clash["oc_mint_authority_active"] == (None, "INCONSISTENT_RECORD")
    assert clash["oc_freeze_authority_active"] == (0.0, None)


def test_no_sell_route_and_exit_share():
    row = thesis(MINT, 100.0, bd=breakdown(route="no sell route (NO_ROUTE)"), liquidity=0.0)
    v = O.current_values(O.parse_row(row, token(MINT)))
    assert v["oc_no_sell_route"] == (1.0, None)
    assert v["oc_route_hops"] == (None, "NOT_OBSERVED_BY_LAB")
    assert v["oc_exit_cap_share"] == (None, "NON_POSITIVE")
    flagged = O.current_values(O.parse_row(thesis(MINT, 100.0, fatal=[{"flag": "NO_SELL_ROUTE"}], bd=breakdown(route=None)), token(MINT)))
    assert flagged["oc_no_sell_route"] == (1.0, None)
    assert O.current_values(O.parse_row(thesis(MINT, 100.0, exit_cap_3pct=None), token(MINT)))["oc_exit_cap_share"] == (None, "ABSENT_IN_SNAPSHOT")


def test_p08_reported_liquidity_is_not_exit_capacity():
    """A pool reporting $1M liquidity with $2k sellable at 3% impact: the share is 0.002, a separate input from liquidity."""
    v = O.current_values(O.parse_row(thesis(MINT, 100.0, liquidity=1_000_000.0, exit_cap_3pct=2_000.0), token(MINT)))
    assert v["oc_exit_cap_share"][0] == pytest.approx(0.002)


# ---------------------------------------------------------------- the as-of snapshot
def test_values_are_available_at_the_decision_and_never_use_a_later_decision(tmp_path):
    con, (d1, d2, d3) = world(tmp_path)
    s2 = O.onchain_as_of(con, "solana", MINT, d2)
    assert all(v["available_at"] == d2 for v in s2["values"].values() if v["value"] is not None)
    con2, _ = world(tmp_path, third=False, name="t.sqlite")
    assert O.onchain_as_of(con2, "solana", MINT, d2)["onchain_snapshot_sha"] == s2["onchain_snapshot_sha"]   # the later export changes nothing
    s3 = O.onchain_as_of(con, "solana", MINT, d3)
    assert vals(s3)["oc_structural_fatal"] == 1.0 and vals(s2)["oc_structural_fatal"] == 0.0


def test_truncated_store_gives_the_same_snapshot(tmp_path):
    con, (d1, d2, d3) = world(tmp_path)
    for t in (d1, d2):
        cut = F.truncated_copy(con, t)
        assert O.onchain_as_of(cut, "solana", MINT, t)["onchain_snapshot_sha"] == O.onchain_as_of(con, "solana", MINT, t)["onchain_snapshot_sha"]


def test_change_features_use_the_previous_decision_only(tmp_path):
    con, (d1, d2, d3) = world(tmp_path)
    s1 = O.onchain_as_of(con, "solana", MINT, d1)
    assert why(s1)["oc_d_log1p_liquidity"] == "NO_PRIOR_DECISION" and why(s1)["oc_prior_gap_h"] == "NO_PRIOR_DECISION"
    v2 = vals(O.onchain_as_of(con, "solana", MINT, d2))
    assert v2["oc_d_log1p_liquidity"] == pytest.approx(math.log1p(20000) - math.log1p(50000), rel=1e-9)
    assert v2["oc_d_log1p_exit_cap"] == pytest.approx(math.log1p(500) - math.log1p(1000), rel=1e-9)
    assert v2["oc_d_adj_top10_pp"] == pytest.approx(17.5)
    assert v2["oc_prior_gap_h"] == pytest.approx((d2 - d1) / 3600)
    v3 = vals(O.onchain_as_of(con, "solana", MINT, d3))
    assert v3["oc_d_lp_locked_pp"] == pytest.approx(-40.0)          # previous is d2's row, not d1's
    assert v3["oc_d_adj_top10_pp"] == pytest.approx(30.0)


def test_authority_switch_between_decisions(tmp_path):
    con, (d1, d2, d3) = world(tmp_path, second_fatal=[{"flag": "MINT_AUTHORITY_ACTIVE"}],
                              second_bd=breakdown(mech="token mechanics 1 critical issue(s)"))
    assert vals(O.onchain_as_of(con, "solana", MINT, d2))["oc_authority_switch"] == 1.0
    assert vals(O.onchain_as_of(con, "solana", MINT, d3))["oc_authority_switch"] == 1.0
    con2, _ = world(tmp_path, name="u.sqlite")
    assert vals(O.onchain_as_of(con2, "solana", MINT, d2))["oc_authority_switch"] == 0.0
    con3, _ = world(tmp_path, second_fatal=[{"flag": "FREEZE_AUTHORITY_ACTIVE"}],
                    second_bd=breakdown(mech="token mechanics 1 critical issue(s)"), name="f.sqlite")
    v = vals(O.onchain_as_of(con3, "solana", MINT, d2))
    assert v["oc_freeze_authority_active"] == 1.0 and v["oc_mint_authority_active"] == 0.0 and v["oc_authority_switch"] == 1.0


def test_p36_snapshot_time_after_the_decision_refuses_the_row(tmp_path):
    d1 = H.D1
    con = store(tmp_path, [(d1, [thesis(MINT, d1 - 900, t=d1 + 60)])])
    s = O.onchain_as_of(con, "solana", MINT, d1)
    assert set(why(s).values()) == {"INCONSISTENT_TIME"} and len(why(s)) == len(O.OC)
    con2 = store(tmp_path, [(d1, [thesis(MINT, d1 - 900, t=d1 - 30)])], name="ok.sqlite")
    assert vals(O.onchain_as_of(con2, "solana", MINT, d1))["oc_capture_delay_s"] == pytest.approx(30.0)


def test_identity_and_scope(tmp_path):
    con, (d1, d2, d3) = world(tmp_path)
    assert set(why(O.onchain_as_of(con, "solana", "So11111111111111111111111111111111111111112", d2)).values()) == {"NOT_IN_UNIVERSE"}
    assert set(why(O.onchain_as_of(con, "base", MINT, d2)).values()) == {"NOT_IN_UNIVERSE"}
    s = O.onchain_as_of(con, "solana", MINT_B, d2)             # same symbol, another mint: its own row only (P01)
    assert s["mint"] == MINT_B and vals(s)["oc_structural_fatal"] == 0.0
    key = s["decision_key"]
    with pytest.raises(O.OnchainError):
        O.onchain_as_of(con, "solana", MINT, d2, decision_key=key)


def test_p09_rejected_and_fatal_decisions_are_kept(tmp_path):
    con, (d1, d2, d3) = world(tmp_path)
    s = O.onchain_as_of(con, "solana", MINT, d3)
    assert s["decision_key"] is not None and vals(s)["oc_structural_fatal"] == 1.0 and vals(s)["oc_lp_risk_ord"] == 3.0


def test_v2_consistency(tmp_path):
    con, (d1, d2, d3) = world(tmp_path)
    s = O.onchain_as_of(con, "solana", MINT, d2)
    f = F.features_as_of(con, "solana", MINT, d2, F.FEATURE_VERSION)
    row = {v["feature_name"]: v["value"] for v in f["values"]}
    assert O.v2_consistency(s, row) == []
    assert O.v2_consistency(s, dict(row, thesis_adj_top10_pct=row["thesis_adj_top10_pct"] + 1e-6)) != []
    assert O.v2_consistency(s, dict(row, thesis_log1p_exit_cap_3pct_usd=None)) != []


def test_snapshot_is_deterministic_and_values_are_finite(tmp_path):
    con, (d1, d2, d3) = world(tmp_path)
    a, b = O.onchain_as_of(con, "solana", MINT, d3), O.onchain_as_of(con, "solana", MINT, d3)
    assert a["onchain_snapshot_sha"] == b["onchain_snapshot_sha"]
    with pytest.raises(O.OnchainError):
        O._value(float("inf"), None, d3, ["x"])                    # P38
    with pytest.raises(O.OnchainError):
        O._value(None, "MADE_UP_REASON", None, ())


# ---------------------------------------------------------------- synthetic examples for the models
def ex(i, *, t, y, structural, distribution=0.0, lp=1.0, mat=None, mint=None, extra=None):
    x = {c: float("nan") for c in O.ALLOWED}
    x.update({B.LIQ: 10.0 + (i % 7) * 0.1, B.MCAP: 13.0 + (i % 5) * 0.1, B.VOL: 11.0 + (i % 3) * 0.2, B.FATAL: structural,
              "oc_structural_fatal": structural, "oc_distribution_fatal": distribution, "oc_lp_risk_ord": lp,
              "oc_lp_locked_pct": 50.0 + (i % 9), "oc_exit_cap_share": 0.01 * (1 + i % 4), "oc_largest_unexplained_pct": 5.0 + i % 6,
              "thesis_adj_top10_pct": 20.0 + i % 11, "oc_wash_ord": float(i % 3)})
    x.update(extra or {})
    av = {c: t for c in O.ALLOWED}
    return O.OExample(decision_key=f"k{i:04d}", chain="solana", mint=mint or f"M{i:04d}", decision_time=t,
                      label_matures_at=mat if mat is not None else t + 86400 + 900, y=int(y), x=x, avail=av)


def signal_world(n=400, seed=7, start=D0, step=1800.0):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        s = float(rng.random() < 0.3)
        p = 0.6 if s else 0.1
        out.append(ex(i, t=start + i * step, y=rng.random() < p, structural=s, distribution=float(rng.random() < 0.2)))
    return out


def test_count_gate_abstains_below_the_minimum():
    train = signal_world(60)
    cut = max(e.label_matures_at for e in train) + 1
    for m in O.MODEL_IDS:
        c = O.fit(m, T2, train, cut, is_fixture=True)
        assert c["body"]["abstain"] == "INSUFFICIENT_HISTORY"
        p, w = O.predict(c, [ex(9999, t=cut + 10, y=0, structural=1.0)])
        assert not math.isfinite(p[0]) and w[0] == "INSUFFICIENT_HISTORY"


def test_fixture_signal_is_found_and_flagged_as_fixture():
    train = signal_world(400)
    cut = max(e.label_matures_at for e in train) + 1
    test = [ex(5000 + i, t=cut + 60 * i, y=0, structural=float(i % 2)) for i in range(20)]
    for m in ("R1_OC_RULE", "M1_OC_LOGIT", "M2_OC_LOGIT_B2"):
        c = O.fit(m, T2, train, cut, is_fixture=True)
        assert c["evidence_class"] == B.FIXTURE_FLAG and c["promotion"] == "MODEL_NOT_PROMOTED" and c["status"] == B.PROVISIONAL
        p, _ = O.predict(c, test)
        assert np.mean(p[1::2]) > np.mean(p[0::2]) + 0.2, m           # structural rows score higher
    nc = O.fit("M2_OC_LOGIT_B2", T2, train, cut, y_override=np.random.default_rng(0).permutation(B.labels_of(train)), card_kind="NC1OC")
    p, _ = O.predict(nc, test)
    assert abs(np.mean(p[1::2]) - np.mean(p[0::2])) < 0.2


def test_rule_cells_are_shrunk_to_the_training_prevalence_and_a_missing_cell_gives_b0():
    train = signal_world(400)
    cut = max(e.label_matures_at for e in train) + 1
    c = O.fit("R1_OC_RULE", T2, train, cut)
    y = B.labels_of(train)
    b0 = float(y.mean())
    cell = [e for e in train if e.x["oc_structural_fatal"] == 1.0 and e.x["oc_distribution_fatal"] == 0.0]
    k = sum(e.y for e in cell)
    assert c["body"]["cells"]["S1D0"]["p"] == pytest.approx((k + 20 * b0) / (len(cell) + 20))
    miss = ex(9000, t=cut + 1, y=0, structural=float("nan"))
    assert O.predict(c, [miss])[0][0] == pytest.approx(b0)


def test_m2_uses_required_rows_and_optional_missing_inputs():
    train = signal_world(400)
    for i, e in enumerate(train):
        if i % 5 == 0:
            e.x["oc_lp_locked_pct"] = float("nan")                # optional, AS_OF missing: median fill and indicator
    cut = max(e.label_matures_at for e in train) + 1
    c = O.fit("M2_OC_LOGIT_B2", T2, train, cut)
    assert c["n_used"] == 400 and c["body"]["prep"]["ind"]
    gap = ex(9001, t=cut + 1, y=0, structural=float("nan"))       # a required input missing: OOD, no number
    p, w = O.predict(c, [gap])
    assert not math.isfinite(p[0]) and w[0] == "OOD"
    a1 = O.fit("A1_OC_B2_TC", T2, train, cut)
    assert a1["n_used"] == c["n_used"] and a1["body"]["spec"]["columns"] == list(B.B2_COLUMNS)


def test_p13_a_card_never_scores_an_earlier_decision():
    train = signal_world(400)
    cut = max(e.label_matures_at for e in train) + 1
    c = O.fit("M1_OC_LOGIT", T2, train, cut)
    with pytest.raises(O.ModelTrainedAfterDecision):
        O.predict(c, [ex(9002, t=cut - 1, y=0, structural=1.0)])


def test_training_rows_must_be_matured_and_inputs_declared():
    train = signal_world(400)
    cut = max(e.label_matures_at for e in train) + 1
    late = train[:-1] + [ex(9003, t=cut - 10, y=1, structural=1.0, mat=cut + 100)]
    with pytest.raises((B.BaselineError, F.AsOfError)):
        O.fit("M1_OC_LOGIT", T2, late, cut)
    e = train[0]
    e2 = O.OExample(**{**e.__dict__, "x": {**e.x, "trap_next_decision_structural": 1.0}, "avail": {**e.avail, "trap_next_decision_structural": e.decision_time}})
    with pytest.raises(F.AsOfError):                               # NC2-OC: an undeclared column never reaches a fit
        O.check_asof([e2], ["trap_next_decision_structural"], as_of=None, with_labels=False)
    e3 = O.OExample(**{**e.__dict__, "avail": {**e.avail, "oc_lp_risk_ord": e.decision_time + 1}})
    with pytest.raises(F.AsOfError):                               # P36: a value available after the decision
        O.check_asof([e3], ["oc_lp_risk_ord"], as_of=None, with_labels=False)


def test_card_roundtrip_tamper_and_version():
    train = signal_world(400)
    cut = max(e.label_matures_at for e in train) + 1
    c = O.fit("M2_OC_LOGIT_B2", T2, train, cut)
    back = O.loads(O.dumps(c))
    assert back == c
    t = json.loads(O.dumps(c))
    t["body"]["logistic"]["coef"][0] += 1e-9
    with pytest.raises(B.ModelHashMismatch):
        O.verify_card(t)
    t2 = json.loads(O.dumps(c))
    t2["onchain_version"] = "onchain-0"
    t2["model_sha"] = B.sha({k: v for k, v in t2.items() if k != "model_sha"})
    with pytest.raises(F.FeatureVersionError):
        O.verify_card(t2)
    assert "pickle" not in O.dumps(c)


def test_walk_forward_reuses_phase_07_folds_and_b0_b2_numbers():
    dev = [e for e in signal_world(400, start=C.parse_utc("2026-10-05T00:00:00Z"), step=2700.0)]
    for e in dev:
        e.label_matures_at = e.decision_time + B.maturity_lag(T2)
    H0_ = L.holdout_start()
    dev = [e for e in dev if e.label_matures_at <= H0_]

    def train_at(cut):
        return [e for e in dev if e.decision_time < cut and e.label_matures_at <= cut]
    res = O.walk_forward(T2, dev, train_at, nc1_seeds=range(2), is_fixture=True)
    ref = B.walk_forward(T2, [B.Example(**{k: v for k, v in e.__dict__.items() if k in B.Example.__dataclass_fields__}) for e in dev],
                         lambda c: [B.Example(**{k: v for k, v in e.__dict__.items() if k in B.Example.__dataclass_fields__}) for e in train_at(c)],
                         nc1_seeds=range(2), is_fixture=True)
    assert res["split_fingerprint"] == ref["split_fingerprint"] and res["folds"]
    for a, b in zip(res["oos"], ref["oos"]):
        for k in ("B0", "B2"):
            assert (math.isnan(a[k]) and math.isnan(b[k])) or a[k] == pytest.approx(b[k], abs=1e-15)
    assert all(r["R0_alarm"] in (True, False) for r in res["oos"])


def _snap_for(e, *, t=None, missing=()):
    vals_ = {c: {"value": (None if c in missing else 1.0), "missing_reason": ("NOT_OBSERVED_BY_LAB" if c in missing else None),
                 "available_at": (None if c in missing else e.decision_time)} for c in O.OC}
    return {"decision_key": e.decision_key, "chain": e.chain, "mint": e.mint, "decision_time": e.decision_time if t is None else t,
            "values": vals_, "onchain_snapshot_sha": "x", "row_sha256": "r"}


def test_attach_checks_identity_and_keeps_missing_values_missing():
    e = B.Example(decision_key="k1", chain="solana", mint=MINT, decision_time=1000.0, label_matures_at=2000.0, y=0)
    v2 = {"k1": {"chain": "solana", "mint": MINT, "decision_time": 1000.0, "decision_key": "k1", "thesis_adj_top10_pct": 12.0,
                 "thesis_adj_top10_pct__available_at": 1000.0}}
    out = O.attach([e], {"k1": _snap_for(e, missing=("oc_lp_locked_pct",))}, v2)[0]
    assert math.isnan(out.x["oc_lp_locked_pct"]) and out.avail["oc_lp_locked_pct"] == 1000.0 and out.x["oc_lp_risk_ord"] == 1.0
    assert out.oc_reasons == {"oc_lp_locked_pct": "NOT_OBSERVED_BY_LAB"} and out.x["thesis_adj_top10_pct"] == 12.0
    with pytest.raises(B.IdentityJoinError):
        O.attach([e], {"k1": _snap_for(e, t=999.0)}, v2)                  # another decision of the same mint
    with pytest.raises(B.IdentityJoinError):
        O.attach([e], {"k1": dict(_snap_for(e), mint=MINT_B)}, v2)
    with pytest.raises(B.IdentityJoinError):
        O.attach([e], {"k1": _snap_for(e)}, {"k1": dict(v2["k1"], decision_time=999.0)})


def test_count_gate_counts_the_rows_a_model_uses():
    train = signal_world(400)
    for e in train[50:]:
        e.x["oc_structural_fatal"] = float("nan")                  # required input missing on 350 rows
    cut = max(e.label_matures_at for e in train) + 1
    c = O.fit("M1_OC_LOGIT", T2, train, cut)
    assert c["body"]["abstain"] == "INSUFFICIENT_HISTORY" and c["n_used"] == 50 and c["n_train"] == 400


def test_walk_forward_refuses_a_training_set_other_than_the_index():
    dev = [e for e in signal_world(400, start=C.parse_utc("2026-10-05T00:00:00Z"), step=2700.0)]
    for e in dev:
        e.label_matures_at = e.decision_time + B.maturity_lag(T2)
    dev = [e for e in dev if e.label_matures_at <= L.holdout_start()]
    with pytest.raises(B.WalkForwardMismatch):
        O.walk_forward(T2, dev, lambda c: [e for e in dev if e.decision_time < c][:-1], nc1_seeds=range(1))


def test_degenerate_flag():
    assert O.degenerate([0.2, 0.2, 0.2]) and not O.degenerate([0.2, 0.3]) and not O.degenerate([0.2])


# ---------------------------------------------------------------- early warning
def _rows(alarms, ys, b0=0.2, t=1000.0):
    rows = []
    for i, (a, y) in enumerate(zip(alarms, ys)):
        e = ex(i, t=t, y=y, structural=float(a))
        rows.append({"example": e, "y": y, "B0": b0, "M": 0.5 if a else 0.1, "R0_alarm": bool(a)})
    return rows


def test_early_warning_counts_and_lead_time():
    rows = _rows([1, 1, 0, 0, 1], [1, 0, 1, 0, 1])
    touch = {"k0000": 1000.0 + 7200, "k0004": 1000.0 + 3600}
    for m in ("R0_OC_VETO", "M"):
        e = O.early_warning(rows, m, touch=touch)
        assert (e["hits"], e["misses"], e["false_alarms"], e["correct_rejections"]) == (2, 1, 1, 1)
        assert sorted(e["lead_times_h"]) == [1.0, 2.0] and e["support_note"].startswith("n < 20")
    with pytest.raises(O.OnchainError):                              # an "alarm" after the event is not early warning
        O.early_warning(rows, "M", touch={"k0000": 999.0})
    tie = _rows([0], [1])
    tie[0]["M"] = tie[0]["B0"]                                       # equal to the prevalence is not an alarm
    assert O.early_warning(tie, "M", touch={})["misses"] == 1


# ---------------------------------------------------------------- decision support: veto and size cap (step 5, P25, P44)
QUOTES = [{"kind": "QUOTE", "state": "OK", "size_usd": 100.0, "proceeds_ratio": 0.99},
          {"kind": "QUOTE", "state": "OK", "size_usd": 500.0, "proceeds_ratio": 0.96},
          {"kind": "QUOTE", "state": "OK", "size_usd": 2000.0, "proceeds_ratio": 0.80}]


def _doc(p=None):
    d = {"prediction_status": "ABSTAIN" if p is None else "FORECAST", "probability": p}
    return d


def test_a_forecast_never_clears_a_fatal_flag_and_the_cap_ignores_the_forecast():
    flags = [{"flag": "CANNOT_EXIT_5K", "category": "exitability"}]
    outs = [O.decision_support(_doc(p), flags, QUOTES, max_loss=0.05) for p in (None, 0.001, 0.5, 0.999)]
    assert all(o["veto_overrides_forecast"] and o["structural_veto"]["structural"] == ["CANNOT_EXIT_5K"] for o in outs)
    assert len({json.dumps(o["size_cap"], sort_keys=True) for o in outs}) == 1
    assert outs[0]["size_cap"]["size_cap_usd"] == 500.0
    assert "probability" not in inspect.signature(O.size_cap_usd).parameters
    none = O.decision_support(_doc(0.9), None, [], max_loss=0.05)
    assert none["structural_veto"]["state"] == "VETO_UNKNOWN" and none["veto_overrides_forecast"]   # unknown is not a pass
    clean = O.decision_support(_doc(0.9), [], [], max_loss=0.05)
    assert clean["structural_veto"]["veto"] is False and clean["size_cap"]["basis"] == "EXECUTION_DATA_MISSING"   # P44
    assert clean["position_usd_from_forecast"] is None


def test_p25_tvl_says_fine_but_the_quote_says_no_exit():
    cap = O.size_cap_usd([{"kind": "QUOTE", "state": "OK", "size_usd": 100.0, "proceeds_ratio": 0.6, "reported_reserve_usd": 5e6}], max_loss=0.05)
    assert cap["size_cap_usd"] == 0.0
    with pytest.raises(O.OnchainError):
        O.size_cap_usd(QUOTES, max_loss=1.5)


# ---------------------------------------------------------------- wallet movements (P18, P19, developer wallet)
TOKEN_ROW = {"creator": "CreatorWa11et1111111111111111111111111111111", "dev_wallet": "DevWa11et11111111111111111111111111111111111"}


def test_p18_a_transfer_is_never_a_sale():
    dev = O.wallet_role(TOKEN_ROW["dev_wallet"], token_row=TOKEN_ROW)
    assert dev["role"] == "DEV" and dev["basis"] == "OBSERVED"
    whale = O.movement_class({"kind": "TRANSFER", "direction": "OUT"}, dev)
    assert whale["class"] == "MOVEMENT_NOT_SALE" and not whale["is_sale"] and not whale["counts_as_insider_distribution"]
    sale = O.movement_class({"kind": "SWAP", "direction": "SELL", "counterparty_is_pool": True}, dev)
    assert sale["is_sale"] and sale["counts_as_insider_distribution"]
    otc = O.movement_class({"kind": "SWAP", "direction": "SELL", "counterparty_is_pool": False}, dev)
    assert not otc["is_sale"]
    to_cex = O.movement_class({"kind": "TRANSFER", "direction": "OUT", "to_role": "CUSTODY_OR_EXCHANGE"}, dev)
    assert to_cex["note"] == "TRANSFER_TO_CUSTODY_SALE_UNOBSERVED" and not to_cex["is_sale"]


def test_p19_exchange_or_custody_is_never_an_insider():
    for addr, kw in (("CexHot", {"cex_labels": {"CexHot": "MEXC"}}), ("Custody1", {"custody": ["Custody1"]})):
        r = O.wallet_role(addr, token_row=TOKEN_ROW, **kw)
        assert r["role"] == "CUSTODY_OR_EXCHANGE" and r["insider"] is False
        m = O.movement_class({"kind": "SWAP", "direction": "SELL", "counterparty_is_pool": True}, r)
        assert m["is_sale"] and not m["counts_as_insider_distribution"] and not m["counts_as_inferred_distribution"]
    # an exchange address that is also listed as the creator stays an exchange (a deposit address reused by a launcher)
    r = O.wallet_role(TOKEN_ROW["creator"], token_row=TOKEN_ROW, cex_labels={TOKEN_ROW["creator"]: "Gate.io"})
    assert r["role"] == "CUSTODY_OR_EXCHANGE"


def test_developer_wallet_misclassification_and_inferred_clusters():
    row = {"creator": "3p7f4xNVj7nGcmXe1J1vxt1fvqcY3k8aMwM72PKFN42q", "dev_wallet": "HBYzRFKRHGdd6N7UkY4QkGU5Vmt26qZu9pTV8mopump"}
    r = O.wallet_role(row["dev_wallet"], token_row=row)                 # the real token row of 55Vr2VpS... (likely a mint address)
    assert r["role"] == "DEV_LABEL_SUSPECT" and r["insider"] is None
    sale = O.movement_class({"kind": "SWAP", "direction": "SELL", "counterparty_is_pool": True}, r)
    assert sale["is_sale"] and not sale["counts_as_insider_distribution"]
    known = O.wallet_role("Mint1111", token_row={"dev_wallet": "Mint1111"}, known_mints=["Mint1111"])
    assert known["role"] == "DEV_LABEL_SUSPECT"
    c = O.wallet_role("W1", token_row=TOKEN_ROW, clusters={"W1": "HIGH"})
    assert c["role"] == "CLUSTER_MEMBER_INFERRED" and c["basis"] == "INFERRED"
    m = O.movement_class({"kind": "SWAP", "direction": "SELL", "counterparty_is_pool": True}, c)
    assert m["counts_as_inferred_distribution"] and not m["counts_as_insider_distribution"]


# ---------------------------------------------------------------- the collector adapter (TEST_ONLY)
SNAP_SQL = ("INSERT INTO bt_depth_snapshots (run_id,decision_id,chain,mint,pool_address,kind,provider,size_usd,captured_at,http_status,state,"
            "since_export_s,reserve_usd,price_usd,out_usd,price_impact,recorded_at,content_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")
DEC_SQL = ("INSERT INTO bt_depth_decisions (chain,mint,pool_address,pool_source,export_commit,export_time,created_at,row_sha256,status,"
           "recorded_at,content_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?)")
TD = 1791500000.0


def collector(tmp_path, snaps=(), *, migration=2, drop_col=None, mint=MINT, name="bt.sqlite"):
    p = tmp_path / name
    con = sqlite3.connect(p)
    sql = (FIX / "bt_depth_schema_v2.sql").read_text()
    if drop_col:
        sql = sql.replace(drop_col, f"{drop_col}_renamed")
    con.executescript(sql)
    con.execute("INSERT INTO bt_schema_migrations VALUES (1,'v1','x',0)")
    if migration >= 2:
        con.execute("INSERT INTO bt_schema_migrations VALUES (2,'forward depth collector','y',0)")
    con.execute(DEC_SQL, ("solana", mint, "POOL1", "EXPORT_PRIMARY_POOL", "c1", TD, TD - 600, "rowsha", "WATCH", TD + 10, "h"))
    for i, s in enumerate(snaps):
        con.execute(SNAP_SQL, ("run", 1, "solana", s.get("mint", mint), s.get("pool", "POOL1"), s.get("kind", "QUOTE"), "jupiter",
                               s.get("size", 500.0), s.get("t"), s.get("http", 200), s.get("state", "OK"), None, s.get("reserve"),
                               1.0, s.get("out"), s.get("impact", 0.01), TD, f"h{i}"))
    con.commit()
    con.close()
    return p


def q(t, out=None, state="OK", size=500.0, pool="POOL1", **kw):
    return dict(t=t, out=out, state=state, size=size, pool=pool, **kw)


def test_adapter_schema_states_and_read_only(tmp_path):
    assert DA.status(tmp_path / "none.sqlite")["state"] == "COLLECTOR_NOT_AVAILABLE"
    assert not (tmp_path / "none.sqlite").exists()                       # never created
    assert DA.status(collector(tmp_path, name="a.sqlite"))["state"] == "NO_ROWS"
    assert DA.status(collector(tmp_path, [q(TD + 400, 495.0)], name="b.sqlite"))["state"] == "OK"
    assert DA.status(collector(tmp_path, migration=1, name="c.sqlite"))["state"] == "SCHEMA_MISMATCH"
    bad = DA.status(collector(tmp_path, drop_col="since_export_s", name="d.sqlite"))
    assert bad["state"] == "SCHEMA_MISMATCH" and "since_export_s" in " ".join(bad["problems"])
    con = DA.connect_ro(collector(tmp_path, name="e.sqlite"))
    with pytest.raises(sqlite3.OperationalError):
        con.execute("INSERT INTO bt_schema_migrations VALUES (9,'x','y',0)")
    con.execute("PRAGMA query_only=OFF")                             # the file itself is opened read-only, not only the session
    with pytest.raises(sqlite3.OperationalError):
        con.execute("INSERT INTO bt_schema_migrations VALUES (9,'x','y',0)")
    with pytest.raises(DA.AdapterError):
        DA.connect_ro(ROOT / "data" / "memelab.sqlite")


def test_adapter_identity_link(tmp_path):
    con = DA.connect_ro(collector(tmp_path))
    assert DA.link(con, chain="solana", mint=MINT, row_sha256="rowsha", decision_time=TD)["pool_address"] == "POOL1"
    assert DA.link(con, chain="solana", mint=MINT.lower(), row_sha256="rowsha", decision_time=TD) is None    # Solana is case sensitive
    assert DA.link(con, chain="solana", mint=MINT, row_sha256="other", decision_time=TD) is None
    with pytest.raises(DA.DepthIdentityError):
        DA.link(con, chain="solana", mint=MINT, row_sha256="rowsha", decision_time=TD + 3600)   # another export of the row
    other = DA.connect_ro(collector(tmp_path, [q(TD + 400, 1.0, mint=MINT_B)], name="o.sqlite"))
    assert DA.observations(other, chain="solana", mint=MINT) == []


def test_cx09_a_post_decision_read_is_never_depth_at_the_decision(tmp_path):
    con = DA.connect_ro(collector(tmp_path, [q(TD + 420, 495.0), q(TD + 420, kind="POOL", size=None, reserve=80000.0)]))
    obs = DA.observations(con, chain="solana", mint=MINT)
    assert len(obs) == 2 and all(o["available_at"] > TD for o in obs)
    assert DA.visible_at(obs, TD) == []
    with pytest.raises(DA.DepthLeakageError):
        DA.assert_visible(obs, TD)
    assert len(DA.visible_at(obs, TD + 3600)) == 2                       # usable for a later decision of the mint


def test_p02_rows_stay_per_pool_and_p08_reserve_is_never_exit_capacity(tmp_path):
    con = DA.connect_ro(collector(tmp_path, [q(TD + 400, 20.0, pool="POOL1"), q(TD + 400, kind="POOL", size=None, reserve=5e6, pool="POOL1"),
                                             q(TD + 400, 490.0, pool="POOL2")]))
    obs = DA.observations(con, chain="solana", mint=MINT)
    g = DA.by_pool(obs)
    assert set(g) == {"POOL1", "POOL2"}
    pool_row = [o for o in g["POOL1"] if o["kind"] == "POOL"][0]
    assert pool_row["proceeds_ratio"] is None and pool_row["reserve_semantics"] == "REPORTED_RESERVE_NOT_EXIT_CAPACITY"
    ctx = DA.exit_context(obs, T=TD + 500, pool_address="POOL1", size_usd=500.0)
    assert ctx["proceeds_ratio"] == pytest.approx(0.04)                  # $5M reported reserve, $20 back for $500
    con2 = DA.connect_ro(collector(tmp_path, [q(TD + 400, 20.0, reserve=5e6), q(TD + 500, 480.0, state="PRICE_DISAGREES")], name="r.sqlite"))
    o2 = DA.observations(con2, chain="solana", mint=MINT)
    assert o2[0]["proceeds_ratio"] == pytest.approx(0.04)                 # a reserve on the row never enters proceeds
    assert o2[1]["proceeds_ratio"] is None and o2[1]["out_usd"] is None   # PRICE_DISAGREES has no number


def _label(obs, **kw):
    p = dict(decision_time=TD, as_of=TD + 30 * 3600, pool_address="POOL1", size_usd=500.0, drop=0.2, baseline_max_lag_s=7200.0,
             horizon_s=86400.0, horizon_tol_s=3600.0)
    p.update(kw)
    return DA.proposed_liquidity_label(obs, **p)


def test_proposed_liquidity_label_states(tmp_path):
    def run(snaps, name, **kw):
        con = DA.connect_ro(collector(tmp_path, snaps, name=name))
        return _label(DA.observations(con, chain="solana", mint=MINT), **kw)
    base = q(TD + 400, 490.0)
    assert run([base, q(TD + 86400 + 300, 300.0)], "1.sqlite")["label"] == 1
    assert run([base, q(TD + 86400 + 300, 480.0)], "2.sqlite")["label"] == 0
    lost = run([base, q(TD + 86400 + 300, state="NO_ROUTE")], "3.sqlite")
    assert lost["state"] == "ROUTE_LOST" and lost["label"] == 1                          # P37: never a favourable fill
    assert run([q(TD + 400, state="NO_ROUTE"), q(TD + 86400, 480.0)], "4.sqlite")["state"] == "EXIT_UNAVAILABLE_AT_BASELINE"
    assert run([q(TD + 400, state="HTTP_429", http=429), q(TD + 86400, 480.0)], "5.sqlite")["state"] == "CENSORED_NO_BASELINE"
    assert run([base, q(TD + 86400, state="NOT_ATTEMPTED_CAP", http=None)], "6.sqlite")["state"] == "CENSORED_NO_HORIZON_READ"
    assert run([base, q(TD + 86400, 1.0, state="PRICE_DISAGREES")], "7.sqlite")["state"] == "CENSORED_NO_HORIZON_READ"
    nm = run([base, q(TD + 86400, 480.0)], "8.sqlite", as_of=TD + 86400)
    assert nm["state"] == "NOT_YET_MATURED" and nm["label"] is None                     # P05
    other_size = run([q(TD + 400, 490.0, size=100.0), q(TD + 86400, 10.0, size=100.0)], "9.sqlite")
    assert other_size["state"] == "CENSORED_NO_BASELINE"                                 # size-specific only (P44)
    assert all(r["status"] == "PROPOSED_NOT_FROZEN" for r in (lost, nm, other_size))


def test_proposals_have_no_defaults_and_the_registry_is_unchanged():
    sig = inspect.signature(DA.proposed_liquidity_label)
    assert all(p.default is inspect.Parameter.empty for p in sig.parameters.values())
    assert all(p.default is inspect.Parameter.empty for p in inspect.signature(O.size_cap_usd).parameters.values())
    assert C.registry_sha256() == "4b4aabce77a5a6f9214c4cfdddf5223f410ed6126410cf4b213b3c80b035f896"
    assert C.TARGETS["liquidity_degradation_24h"]["status"] == "DEFERRED_FORWARD_COLLECTION"
    assert C.TARGETS["exit_adjusted_target_before_invalidation_24h"]["status"] == "BLOCKED_NO_HISTORICAL_DEPTH"
    assert C.TARGETS["distribution_event_24h"]["status"] == "BLOCKED_NO_DATA"
    with pytest.raises(DA.AdapterError):
        _label([], drop=0.0)


def test_p44_no_quote_means_no_execution_context(tmp_path):
    con = DA.connect_ro(collector(tmp_path, [q(TD + 400, state="NO_ROUTE")]))
    obs = DA.observations(con, chain="solana", mint=MINT)
    assert DA.exit_context(obs, T=TD + 500, pool_address="POOL1", size_usd=500.0)["state"] == "ROUTE_LOST"
    assert DA.exit_context(obs, T=TD + 100, pool_address="POOL1", size_usd=500.0)["state"] == "EXECUTION_DATA_MISSING"


# ---------------------------------------------------------------- isolation
def _imports(path):
    tree = ast.parse(path.read_text())
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            out.add(("." * n.level) + (n.module or ""))
    return out


def test_imports_numpy_and_standard_library_only_and_never_the_backtesting_package():
    std = {"__future__", "json", "math", "re", "sqlite3", "dataclasses", "typing", "os", "pathlib"}
    on = _imports(ROOT / "memelab/predictive/onchain.py")
    assert on <= std | {"numpy", "."}
    da = _imports(ROOT / "memelab/predictive/depth_adapter.py")
    assert da <= std | {"."}
    for p in (ROOT / "memelab/predictive/onchain.py", ROOT / "memelab/predictive/depth_adapter.py"):
        assert "memelab.backtest" not in p.read_text().replace("never imports `memelab.backtest`", "")


def test_no_other_module_imports_the_phase_09_code():
    for p in (ROOT / "memelab").rglob("*.py"):
        if p.name in ("onchain.py", "depth_adapter.py"):
            continue
        txt = p.read_text()
        assert "onchain" not in _imports(p) and "depth_adapter" not in txt, p
        assert not any(i.endswith("onchain") or i.endswith("depth_adapter") for i in _imports(p)), p


# ---------------------------------------------------------------- committed outputs (added with them)
def test_search_ledger_holds_phase_08_rows_then_every_registered_phase_09_configuration():
    import csv
    p9 = ROOT / "audits/predictive-intelligence/phase_09/experiments"
    led = list(csv.DictReader(open(p9 / "SEARCH_LEDGER.csv")))
    prior = list(csv.DictReader(open(ROOT / "audits/predictive-intelligence/phase_08/experiments/SEARCH_LEDGER.csv")))
    assert led[:len(prior)] == prior
    ids = {r["experiment_id"] for r in led[len(prior):]}
    reg = [r["experiment_id"] for r in csv.DictReader(open(p9 / "EXPERIMENT_REGISTRY.csv"))]
    traps = {"NC2OC", "P13OC", "P36OC", "CX09"}
    assert [x for x in reg if x.split(":")[-1] not in traps and x not in ids] == []
    assert sum(1 for r in led[len(prior):] if r["kind"] == "DEBUG_RUN_REAL_DATA") == 3
    metrics = list(csv.DictReader(open(p9 / "ONCHAIN_METRICS.csv")))
    assert all(r["verdict"] in ("INSUFFICIENT_DAYS", "INSUFFICIENT_EVENTS", "INSUFFICIENT_HISTORY") for r in metrics)
    assert all(r["status"] == B.PROVISIONAL and r["revision_check_claimed"] == "False" for r in metrics)
