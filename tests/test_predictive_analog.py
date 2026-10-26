"""Phase 11: analog cohorts and as-of regime labels (memelab/predictive/analog.py, analog-1). Synthetic fixtures only; no network,
no clock, no store. The real run is audits/predictive-intelligence/phase_11/probes/run_analog.py."""
from __future__ import annotations

import ast
import json
import math
from pathlib import Path

import numpy as np
import pytest

from memelab.predictive import analog as A
from memelab.predictive import baselines as B
from memelab.predictive import contract as C
from memelab.predictive import features as F
from memelab.predictive import labels as L
from memelab.social import replay_core as RC

ROOT = Path(__file__).resolve().parents[1]
DAY = 86400.0
T0 = C.parse_utc("2026-10-01T10:00:00Z")
LAG = C.label_matures_at(L.T1, 0.0)


def ex(key, mint, t, y, *, creator=None, liq=10.0, mcap=12.0, vol=9.0, age=1.0, lp=0.0, t22=0.0, regime="QUIET/RISK_OFF",
       narrative=None, first_seen=None, hist_prior=0.0, oc=None, cell=("1d_7d", "20k_100k"), chain="solana", avail=None):
    x = {B.LIQ: liq, B.MCAP: mcap, B.VOL: vol, B.FATAL: 0.0, B.AGE: age, B.SCORE: 50.0, A.LAUNCH: lp, A.T22: t22}
    av = {c: (t if avail is None else avail) for c in x}
    return A.AExample(decision_key=key, chain=chain, mint=mint, decision_time=t, label_matures_at=t + LAG, y=y, x=x, avail=av,
                      status="WATCH", creator=creator, narrative=narrative, route="PIT_RECORDED", label_key="L" + key,
                      snapshot_sha256="s" + key, cohort={"launch_age_bucket": cell[0], "liquidity_bucket": cell[1]},
                      cluster=A.cluster_of(chain, mint, creator), regime=regime, launchpad="PUMP_FUN", first_seen_at=first_seen,
                      hist_prior=hist_prior, oc=dict(oc or {"oc_mint_authority_active": 0.0, "oc_freeze_authority_active": 0.0,
                                                           "oc_transfer_fee_present": 0.0, "oc_token2022": t22,
                                                           "oc_exit_cap_share": 0.02, "oc_round_trip_friction_pct": 0.5}),
                      pool_address="POOL" + mint)


def pool_fixture(n=120, days=6, seed=0, **kw):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        d = i % days
        t = T0 + d * DAY + (i // days) * 60.0
        rows.append(ex(f"k{i:04d}", f"M{i:04d}", t, int(rng.random() < 0.3), creator=f"C{i:04d}",
                       liq=float(rng.normal(10, 1)), mcap=float(rng.normal(12, 1)), vol=float(rng.normal(9, 1)),
                       age=float(abs(rng.normal(1, 0.5))), **kw))
    return rows


AS_OF = T0 + 8 * DAY


def target(**kw):
    base = dict(liq=10.0, mcap=12.0, vol=9.0, age=1.0)
    base.update(kw)
    return ex("TGT", kw.pop("mint", "TARGETMINT"), AS_OF + 3600.0, 0, creator=kw.pop("creator", "TC"), **{k: v for k, v in base.items() if k not in ("mint", "creator")})


# ---------------------------------------------------------------- as-of pool (P43, NC2-AC, P09)
def test_pool_row_decided_at_or_after_the_cohort_time_is_refused():
    pool = pool_fixture()
    late = ex("late", "LATE", AS_OF, 1, creator="CL")
    late.label_matures_at = AS_OF - 1          # even a matured-looking label: decided at as_of is not before it
    with pytest.raises(A.FutureUniverseError):
        A.check_pool(pool + [late], AS_OF)


def test_pool_label_maturing_after_the_cohort_time_is_refused_nc2():
    pool = pool_fixture()
    imm = ex("imm", "IMM", AS_OF - 3600.0, 1, creator="CI")
    with pytest.raises(A.FutureUniverseError, match="maturing"):
        A.check_pool(pool + [imm], AS_OF)


def test_future_issued_token_is_refused_p43():
    pool = pool_fixture()
    fut = ex("fut", "FUT", T0, 1, creator="CF", first_seen=AS_OF + 10.0)
    with pytest.raises(A.FutureUniverseError, match="future-issued"):
        A.check_pool(pool + [fut], AS_OF)
    with pytest.raises(A.FutureUniverseError):
        A.select("AC2_KNN", target(), pool + [fut], as_of=AS_OF)


def test_target_input_available_after_its_decision_is_refused_p36():
    t = target()
    t.avail[B.LIQ] = t.decision_time + 1.0
    with pytest.raises(F.AsOfError, match="future feature"):
        A.select("AC2_KNN", t, pool_fixture(), as_of=AS_OF)


def test_a_cohort_as_of_after_the_decision_is_refused():
    t = target()
    with pytest.raises(F.AsOfError):
        A.select("AC2_KNN", t, pool_fixture(), as_of=t.decision_time + 1.0)


def test_a_column_outside_the_allowlist_never_reaches_a_cohort_nc2():
    pool = pool_fixture()
    with pytest.raises(F.AsOfError, match="allowlist"):
        A.check_asof(pool, list(A.DIST_COLUMNS) + ["y_next"], as_of=AS_OF, with_labels=True)


def pool_at(rows, as_of):
    return [r for r in rows if r.decision_time < as_of and r.label_matures_at <= as_of
            and (r.first_seen_at is None or r.first_seen_at <= as_of)]


def test_later_rows_and_later_outcomes_never_change_a_cohort_p09_p43():
    pool = pool_fixture()
    later = [ex(f"z{i}", f"Z{i}", AS_OF + i * 60.0, 1, creator=f"CZ{i}") for i in range(40)]
    a1 = A.select("AC2_KNN", target(), pool_at(pool, AS_OF), as_of=AS_OF)
    a2 = A.select("AC2_KNN", target(), pool_at(pool + later, AS_OF), as_of=AS_OF)
    assert a1["number"] == a2["number"] and [x["decision_key"] for x in a1["analogs"]] == [x["decision_key"] for x in a2["analogs"]]


def test_a_token_that_later_died_stays_in_the_pool_survivorship_p09():
    pool = pool_fixture()
    dead = pool[0]                              # nothing in the module asks whether a pool token still trades today
    a = A.select("AC1_STRATA", target(), pool, as_of=AS_OF)
    assert a["G"] == len(pool) and dead.decision_key in {x["decision_key"] for x in a["analogs"]}
    assert "current" not in A.select.__code__.co_varnames and "vendor" not in A.select.__code__.co_varnames


# ---------------------------------------------------------------- identity and groups (P01, P14)
def test_the_same_mint_is_token_history_never_an_analog_p01():
    pool = pool_fixture()
    t = target(mint="M0003", creator="NEWC")
    a = A.select("AC2_KNN", t, pool, as_of=AS_OF)
    assert "M0003" not in {x["mint"] for x in a["analogs"]}
    assert a["excluded"]["same_mint"] == 1 and a["new_mint"] is False
    assert [r.mint for r in A.token_history(t, pool)] == ["M0003"]


def test_a_same_symbol_other_mint_is_an_analog_never_token_history_p01():
    pool = pool_fixture()
    t = target(mint="OTHERMINT", creator="NEWC")
    twin = ex("twin", "TWINMINT", T0 + 3 * DAY, 1, creator="CT", liq=10.0, mcap=12.0, vol=9.0, age=1.0)
    a = A.select("AC2_KNN", t, pool + [twin], as_of=AS_OF)
    assert A.token_history(t, pool + [twin]) == []
    assert a["analogs"][0]["mint"] == "TWINMINT" and a["analogs"][0]["distance"] == 0.0     # identical-looking, still another token
    f = A.cohort_forecast(t, pool + [twin], as_of=AS_OF)
    assert f["path"] != "TOKEN_HISTORY" and f["token_history_n"] == 0


def test_the_same_creator_is_excluded_p14():
    pool = pool_fixture()
    for r in pool[:10]:
        r.creator, r.cluster = "DEPLOYER", A.cluster_of(r.chain, r.mint, "DEPLOYER")
    t = target(creator="DEPLOYER")
    a = A.select("AC2_KNN", t, pool, as_of=AS_OF)
    assert a["excluded"]["same_creator"] == 10
    assert not any(x["cluster"] == "creator:DEPLOYER" for x in a["analogs"])


def test_one_analog_per_cluster_so_duplicate_windows_count_once():
    pool = pool_fixture()
    dup = [ex(f"d{i}", "DUPMINT", T0 + i * DAY + 30.0, 1, creator=None, liq=10.0, mcap=12.0, vol=9.0, age=1.0) for i in range(6)]
    a = A.select("AC2_KNN", target(), pool + dup, as_of=AS_OF)
    clusters = [x["cluster"] for x in a["analogs"]]
    assert len(clusters) == len(set(clusters)) and clusters.count("mint:solana:DUPMINT") == 1
    s = A.select("AC1_STRATA", target(), pool + dup, as_of=AS_OF)
    assert [x["cluster"] for x in s["analogs"]].count("mint:solana:DUPMINT") == 1
    assert [x for x in s["analogs"] if x["mint"] == "DUPMINT"][0]["decision_key"] == "d5"      # the newest row of the cluster


def test_creator_cluster_merges_two_mints_of_one_deployer():
    pool = pool_fixture()
    pool[1].creator = pool[2].creator = "SAME"
    pool[1].cluster = pool[2].cluster = A.cluster_of("solana", pool[1].mint, "SAME")
    a = A.select("AC2_KNN", target(), pool, as_of=AS_OF)
    assert sum(1 for x in a["analogs"] if x["cluster"] == "creator:SAME") <= 1


# ---------------------------------------------------------------- minimums and states
def test_analogs_too_few_below_g_20():
    pool = pool_fixture(n=120)
    for r in pool[19:]:
        r.cohort = {"launch_age_bucket": "ge_30d", "liquidity_bucket": "ge_1m"}
    a = A.select("AC1_STRATA", target(), pool, as_of=AS_OF)
    assert a["G"] == 19 and a["number"] is None and "ANALOGS_TOO_FEW:G_BELOW_MIN" in a["reasons"]


def test_analogs_too_few_below_5_days():
    pool = pool_fixture(n=120, days=4)
    a = A.select("AC2_KNN", target(), pool, as_of=AS_OF)
    assert a["analog_days"] == 4 and a["number"] is None and "ANALOGS_TOO_FEW:DAYS_BELOW_MIN" in a["reasons"]
    assert A.state_of(a["reasons"]) == "ANALOGS_TOO_FEW"


def test_a_pool_below_the_training_gate_gives_insufficient_history():
    pool = pool_fixture(n=99)
    a = A.select("AC2_KNN", target(), pool, as_of=AS_OF)
    assert a["reasons"] == ["INSUFFICIENT_HISTORY"] and a["number"] is None


def test_far_from_analogs_is_out_of_distribution():
    a = A.select("AC2_KNN", target(liq=40.0, mcap=50.0), pool_fixture(), as_of=AS_OF)
    assert "OUT_OF_DISTRIBUTION:FAR_FROM_ANALOGS" in a["reasons"] and a["number"] is None
    assert a["kth_distance"] > a["ood_threshold"]
    b = A.select("AC2_KNN", target(), pool_fixture(), as_of=AS_OF)
    assert b["number"] is not None and b["kth_distance"] <= b["ood_threshold"]


def test_a_missing_target_input_is_out_of_distribution_not_imputed():
    t = target()
    t.x[B.AGE] = float("nan")
    a = A.select("AC2_KNN", t, pool_fixture(), as_of=AS_OF)
    assert a["reasons"] == ["OUT_OF_DISTRIBUTION:MISSING_INPUT"] and a["number"] is None
    t2 = target()
    t2.cohort = {"launch_age_bucket": "UNKNOWN", "liquidity_bucket": "20k_100k"}
    assert A.select("AC1_STRATA", t2, pool_fixture(), as_of=AS_OF)["reasons"] == ["OUT_OF_DISTRIBUTION:MISSING_INPUT"]


def test_an_unseen_cell_is_out_of_distribution():
    t = target()
    t.cohort = {"launch_age_bucket": "lt_1d", "liquidity_bucket": "ge_1m"}
    a = A.select("AC1_STRATA", t, pool_fixture(), as_of=AS_OF)
    assert a["reasons"] == ["OUT_OF_DISTRIBUTION:CELL_UNSEEN"]


def test_regime_warmup_abstains_and_an_unseen_regime_is_ood():
    t = target()
    t.regime = A.WARMUP
    assert A.select("AC3_KNN_REGIME", t, pool_fixture(), as_of=AS_OF)["reasons"] == ["REGIME_UNKNOWN"]
    t.regime = "ACTIVE/RISK_ON"
    assert A.select("AC3_KNN_REGIME", t, pool_fixture(), as_of=AS_OF)["reasons"] == ["OUT_OF_DISTRIBUTION:REGIME_UNSEEN"]


def test_regime_matching_restricts_the_analogs_to_the_targets_regime():
    pool = pool_fixture(n=200)
    for r in pool[:100]:
        r.regime = "ACTIVE/RISK_ON"                # an older, different regime
    t = target()
    a3 = A.select("AC3_KNN_REGIME", t, pool, as_of=AS_OF)
    keys = {r.decision_key: r for r in pool}
    assert all(keys[x["decision_key"]].regime == "QUIET/RISK_OFF" for x in a3["analogs"])
    a2 = A.select("AC2_KNN", t, pool, as_of=AS_OF)
    assert any(keys[x["decision_key"]].regime == "ACTIVE/RISK_ON" for x in a2["analogs"])


# ---------------------------------------------------------------- numbers and uncertainty (P24)
def test_number_is_shrunk_to_the_pool_prevalence_with_a_wilson_interval_on_g():
    pool = pool_fixture()
    a = A.select("AC2_KNN", target(), pool, as_of=AS_OF)
    k, G = a["positives"], a["G"]
    b0 = float(np.mean([r.y for r in pool]))
    assert G == A.K_NEIGHBOURS and math.isclose(a["number"], (k + 20 * b0) / (G + 20))
    lo, hi = a["wilson"]
    assert lo <= k / G <= hi and a["raw_rate"] == k / G


def test_a_small_confident_cohort_gets_no_number_and_a_large_one_an_interval_p24():
    pool = pool_fixture()
    for r in pool:
        r.y = 1 if r.cohort["launch_age_bucket"] == "lt_1d" else r.y
    few = [ex(f"f{i}", f"F{i}", T0 + (i % 6) * DAY, 1, creator=f"CF{i}", cell=("lt_1d", "lt_20k")) for i in range(5)]
    t = target()
    t.cohort = {"launch_age_bucket": "lt_1d", "liquidity_bucket": "lt_20k"}
    a = A.select("AC1_STRATA", t, pool + few, as_of=AS_OF)
    assert a["raw_rate"] == 1.0 and a["number"] is None and a["G"] == 5
    many = [ex(f"g{i}", f"G{i}", T0 + (i % 6) * DAY, 1, creator=f"CG{i}", cell=("lt_1d", "lt_20k")) for i in range(25)]
    b = A.select("AC1_STRATA", t, pool + many, as_of=AS_OF)
    assert b["raw_rate"] == 1.0 and b["number"] < 1.0 and b["wilson"][0] < 0.9


def test_time_change_sensitivity_flags_an_unstable_cohort():
    pool = pool_fixture(n=120)
    for r in pool:
        r.y = 0 if r.decision_time < T0 + 3 * DAY else 1
    a = A.select("AC2_KNN", target(), pool, as_of=AS_OF)
    ts = a["time_sensitivity"]
    assert ts["older_rate"] == 0.0 and ts["newer_rate"] == 1.0 and ts["time_unstable"] is True
    assert "TIME_UNSTABLE" in a["flags"]


# ---------------------------------------------------------------- neighbours
def test_neighbours_equal_a_plain_python_brute_force_with_ties_by_key():
    pool = pool_fixture(seed=3)
    t = target(liq=10.3, mcap=11.8)
    a = A.select("AC2_KNN", t, pool, as_of=AS_OF)
    X = np.array([[r.x[c] for c in A.NUMERIC] for r in pool])
    mu, sd = X.mean(0), X.std(0)
    q = (np.array([t.x[c] for c in A.NUMERIC]) - mu) / sd
    d = []
    for r in pool:
        z = (np.array([r.x[c] for c in A.NUMERIC]) - mu) / sd
        mm = sum(1 for c in A.CATEGORICAL if r.x[c] != t.x[c])
        d.append((math.sqrt(float(np.sum((z - q) ** 2)) + mm), r.decision_key))
    want = [k for _, k in sorted(d)[:30]]
    assert [x["decision_key"] for x in a["analogs"]] == want
    tie = A.KnnIndex(pool)
    assert tie.nearest_clusters(np.zeros(len(pool)))[:2] == [0, 1]       # equal distances: ordered by decision key


def test_categorical_mismatch_adds_one_to_the_squared_distance():
    pool = pool_fixture()
    idx = A.KnnIndex(pool)
    t = target()
    d0 = idx.query(t)
    t.x[A.LAUNCH] = 2.0
    t.x[A.T22] = 1.0
    d1 = idx.query(t)
    assert np.allclose(d1 ** 2, d0 ** 2 + 2.0)


def test_ood_threshold_is_the_95th_percentile_of_kth_other_cluster_distances():
    pool = pool_fixture(n=60)
    idx = A.KnnIndex(pool)
    kth = []
    for i, r in enumerate(pool):
        d = idx.query(r)
        cl = {}
        for j, s in enumerate(pool):
            if s.cluster == r.cluster:
                continue
            cl[s.cluster] = min(cl.get(s.cluster, np.inf), d[j])
        kth.append(sorted(cl.values())[29])
    assert math.isclose(idx.threshold(), float(np.quantile(kth, 0.95)), rel_tol=1e-12)


# ---------------------------------------------------------------- regime as of T (CX-11, P21)
def rr(t, status="WATCH", lv=10.0, avail=None):
    return A.RegimeRow(decision_time=t, status=status, log_vol=lv, available_at=avail)


def regime_fixture():
    rows = []
    for d in range(12):
        lv = 13.0 if d < 6 else 11.0            # volume falls in the second half
        st = "WATCH" if d % 2 else "REJECTED"
        rows += [rr(T0 + d * DAY + i, st, lv + 0.01 * i) for i in range(5)]
    return rows


def test_regime_as_of_refuses_a_later_row_cx11():
    rows = regime_fixture()
    with pytest.raises(RC.LeakageError):
        A.regime_as_of(rows, T0 + 3 * DAY)
    with pytest.raises(RC.LeakageError):
        A.regime_as_of([rr(T0, avail=T0 + 5)], T0)


def test_regime_warmup_below_five_earlier_instants():
    rows = regime_fixture()
    inst = sorted({r.decision_time for r in rows})
    assert A.regime_as_of(A.visible_at(rows, inst[4]), inst[4])["label"] == A.WARMUP
    assert A.regime_as_of(A.visible_at(rows, inst[5]), inst[5])["label"] != A.WARMUP


def test_regime_series_equals_regime_as_of_on_truncated_rows_at_every_instant():
    rows = regime_fixture()
    ser = A.regime_series(rows)
    for T, rec in ser.items():
        assert A.regime_as_of(A.visible_at(rows, T), T) == rec
        assert A.truncation_invariant(A.regime_as_of, rows, T)


def test_full_sample_regime_trap_is_caught_by_the_truncation_check_cx11():
    rows = regime_fixture()
    inst = sorted({r.decision_time for r in rows})
    leaks = [T for T in inst if not A.truncation_invariant(A.regime_full_sample, rows, T)]
    assert leaks, "the full-sample variant must differ somewhere"
    flips = [T for T in inst if A.regime_series(rows)[T]["label"] not in (A.WARMUP,)
             and A.regime_full_sample(rows, T)["label"] != A.regime_series(rows)[T]["label"]]
    assert flips


def test_regime_labels_compare_with_the_past_median_only():
    rows = [rr(T0 + i * 3600.0, "WATCH" if i % 2 else "REJECTED", float(i)) for i in range(8)]
    T = T0 + 7 * 3600.0
    rec = A.regime_as_of(rows, T)
    assert rec["prior_instants"] == 7 and rec["label"].startswith("ACTIVE")
    assert rec["chain_wide_state"] == A.CHAIN_WIDE_STATE and rec["catalyst_category"] == A.CATALYST_CATEGORY


# ---------------------------------------------------------------- router, P12, P44, divergence, LOCO
def test_a_new_mint_gets_a_labelled_cohort_estimate_or_abstains_p12():
    pool = pool_fixture()
    f = A.cohort_forecast(target(), pool, as_of=AS_OF)
    assert f["path"] == "ANALOG_COHORT" and f["label"] == A.COHORT_LABEL and f["new_mint"] is True
    assert f["probability"] is None and f["publishable"] is False and "NO_HISTORICAL_EXECUTABLE_DEPTH" in f["flags"]
    g = A.cohort_forecast(target(liq=40.0, mcap=50.0), pool, as_of=AS_OF)
    assert g["path"] == "ABSTAIN" and g["number"] is None and g["reasons"][0] == "TOKEN_HISTORY_TOO_SHORT"
    assert "OUT_OF_DISTRIBUTION:FAR_FROM_ANALOGS" in g["reasons"] and g["state"] == "OUT_OF_DISTRIBUTION"


def test_token_history_is_used_only_with_twenty_matured_rows_of_the_exact_mint():
    pool = pool_fixture()
    hist = [ex(f"h{i}", "TARGETMINT", T0 + (i % 6) * DAY + 90.0 + i, 1, creator="TC") for i in range(20)]
    f = A.cohort_forecast(target(), pool + hist, as_of=AS_OF)
    assert f["path"] == "TOKEN_HISTORY" and f["token_history_n"] == 20
    f19 = A.cohort_forecast(target(), pool + hist[:19], as_of=AS_OF)
    assert f19["path"] != "TOKEN_HISTORY" and f19["token_history_n"] == 19


def test_a_position_size_gives_execution_data_missing_p44():
    f = A.cohort_forecast(target(), pool_fixture(), as_of=AS_OF, position_usd=5000.0)
    assert f["size_cap"]["basis"] == "EXECUTION_DATA_MISSING" and "EXECUTION_DATA_MISSING" in f["flags"]
    assert f.get("probability") is None


def test_divergence_flags_stay_beside_a_number_step5():
    pool = pool_fixture()
    t = target()
    t.oc["oc_freeze_authority_active"] = 1.0
    t.oc["oc_exit_cap_share"] = 0.5
    f = A.cohort_forecast(t, pool, as_of=AS_OF)
    assert f["number"] is not None
    assert "OC_FREEZE_AUTHORITY_ACTIVE_DIFFERS_FROM_ANALOGS" in f["flags"] and "EXIT_CAP_SHARE_DIFFERS" in f["flags"]
    t.oc["oc_mint_authority_active"] = float("nan")
    assert "OC_MINT_AUTHORITY_ACTIVE_UNKNOWN" in A.divergence_flags(t, pool)
    same = target()
    assert not [x for x in A.divergence_flags(same, pool) if "AUTHORITY" in x]


def test_leave_one_campaign_out_excludes_the_same_narrative():
    pool = pool_fixture()
    for r in pool[:30]:
        r.narrative = "N1"
    t = target()
    t.narrative = "N1"
    a = A.select("AC3_KNN_REGIME", t, pool, as_of=AS_OF, loco=True)
    keys = {r.decision_key: r for r in pool}
    assert a["excluded"]["same_campaign"] == 30 and not any(keys[x["decision_key"]].narrative == "N1" for x in a["analogs"])
    assert a["model"] == "AC3_KNN_REGIME_LOCO"


def test_state_vocabulary_and_contract_mapping():
    assert A.state_of(["OUT_OF_DISTRIBUTION:FAR_FROM_ANALOGS", "ANALOGS_TOO_FEW:G_BELOW_MIN"]) == "ANALOGS_TOO_FEW"
    assert A.contract_reasons(["ANALOGS_TOO_FEW:G_BELOW_MIN", "REGIME_UNKNOWN"]) == ["INSUFFICIENT_HISTORY", "UNCALIBRATED", "MODEL_NOT_SELECTED"]
    assert A.contract_reasons(["OUT_OF_DISTRIBUTION:REGIME_UNSEEN"])[0] == "OOD"
    with pytest.raises(A.AnalogError):
        A.contract_reasons(["SOMETHING_NEW"])
    assert set(A.contract_reasons([])) <= set(C.ABSTAIN_REASONS)


def test_launchpad_class_and_day_kish():
    assert A.launchpad_class({"launchpad": "pump.fun"}) == "PUMP_FUN"
    assert A.launchpad_class({"launchpad": None}) == "NONE_RECORDED" and A.launchpad_class(None) == "NONE_RECORDED"
    assert A.launchpad_class({"launchpad": "met-dbc"}) == "OTHER_LAUNCHPAD"
    assert A._kish(["a"] * 10) == 1.0 and A._kish(["a", "b"] * 5) == 2.0


# ---------------------------------------------------------------- cards, P13, contract
def test_card_roundtrip_tamper_and_trained_after_decision_p13(tmp_path):
    pool = pool_fixture()
    card = A.fit("AC3_KNN_REGIME", L.T1, pool, AS_OF)
    p = tmp_path / "c.json"
    p.write_text(A.dumps(card))
    back = A.loads(p.read_text())
    t = target()
    n1, w1, a1 = A.predict(card, [t])
    n2, w2, a2 = A.predict(back, [t])
    assert np.array_equal(np.nan_to_num(n1, nan=-1), np.nan_to_num(n2, nan=-1)) and w1 == w2
    bad = json.loads(p.read_text())
    bad["body"]["pool"][0]["y"] = 1 - bad["body"]["pool"][0]["y"]
    with pytest.raises(B.ModelHashMismatch):
        A.verify_card(bad)
    early = ex("early", "EARLY", AS_OF - 3600.0, 0, creator="CE")
    with pytest.raises(A.ModelTrainedAfterDecision):
        A.predict(card, [early])
    assert card["publishable"] is False and card["revision_check_claimed"] is True and "pickle" not in p.read_text()


def test_fit_refuses_a_pool_row_from_after_the_cutoff():
    pool = pool_fixture() + [ex("late", "LATE", AS_OF + 1.0, 1, creator="CL")]
    with pytest.raises(A.FutureUniverseError):
        A.fit("AC2_KNN", L.T1, pool, AS_OF)


def test_abstain_document_passes_the_contract_and_a_cohort_number_cannot_be_a_forecast():
    pool = pool_fixture()
    card = A.fit("AC3_KNN_REGIME", L.T1, pool, AS_OF)
    t = target()
    t.mint = "So11111111111111111111111111111111111111112"
    t.chain = "solana"
    a = A.select("AC3_KNN_REGIME", t, pool, as_of=AS_OF)
    doc = A.abstain_document(L.T1, a, snapshot_hash="a" * 64, generated_at_utc=B._iso(AS_OF + 7200), base_rate=a["b0"], card=card)
    assert C.validate(doc, backtest=C.BACKTEST_NOT_AVAILABLE) == []
    assert "number" not in doc["cohort"] and doc["probability"] is None
    fc = dict(doc, prediction_status="FORECAST", abstain_reasons=[], probability=a["number"], uncertainty_interval=a["wilson"],
              training_cutoff_utc=card["training_cutoff_utc"])
    mc = {"model_sha": card["model_sha"], "feature_set_sha": card["feature_set_sha"], "targets": card["targets"],
          "target_version": card["target_version"], "training_cutoff_utc": card["training_cutoff_utc"]}
    assert C.validate(fc, model_card=mc, backtest=C.BACKTEST_NOT_AVAILABLE)


# ---------------------------------------------------------------- walk-forward on a fixture
def wf_fixture():
    rows = []
    rng = np.random.default_rng(7)
    start = C.parse_utc("2026-10-02T10:00:00Z")
    for d in range(14):
        for i in range(25):
            t = start + d * DAY + i
            rows.append(ex(f"w{d:02d}{i:02d}", f"W{d:02d}{i:02d}", t, int(rng.random() < 0.35), creator=f"WC{d}{i}",
                           liq=float(rng.normal(10, 1)), mcap=float(rng.normal(12, 1)), vol=float(rng.normal(9, 1)),
                           age=float(abs(rng.normal(1, 0.5))), regime="QUIET/RISK_OFF" if d % 3 else "QUIET/RISK_ON"))
    dev = [r for r in rows if r.label_matures_at <= L.holdout_start()]
    return dev


def test_walk_forward_fixture_scores_only_from_pools_at_each_cutoff():
    dev = wf_fixture()
    res = A.walk_forward(L.T1, dev, lambda c: [e for e in dev if e.decision_time < c and e.label_matures_at <= c],
                         nc1_seeds=range(2), is_fixture=True)
    assert res["status"] == "OK" and res["oos"]
    for f in res["folds"]:
        for m in A.MODEL_IDS:
            assert f["cards"][m]["max_train_label_matures_at"] <= f["cutoff"]
    for r in res["oos"]:
        assert r["example"].decision_time >= r["cutoff"]
        for m in A.MODEL_IDS:
            ans = r["answers"][m]
            if ans.get("number") is not None:
                assert ans["as_of"] == r["cutoff"] and ans["G"] >= A.MIN_G and ans["analog_days"] >= A.MIN_DAYS
    assert res["folds"][0]["cards"]["AC1_STRATA"]["evidence_class"] == B.FIXTURE_FLAG


# ---------------------------------------------------------------- isolation
def _imports(p):
    tree = ast.parse(p.read_text())
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            out.add(("." * n.level) + (n.module or ""))
    return out


def test_imports_numpy_standard_library_and_the_replay_seam_only():
    std = {"__future__", "json", "math", "dataclasses", "typing"}
    assert _imports(ROOT / "memelab/predictive/analog.py") <= std | {"numpy", ".", "..social"}
    txt = (ROOT / "memelab/predictive/analog.py").read_text()
    assert "statsmodels" not in txt.replace("statsmodels MarkovRegression", "") and "sklearn" not in txt


def test_no_other_module_imports_the_phase_11_code():
    for p in (ROOT / "memelab").rglob("*.py"):
        if p.name == "analog.py":
            continue
        assert not any(i.endswith("analog") for i in _imports(p)), p
        assert "predictive.analog" not in p.read_text(), p


# ---------------------------------------------------------------- added after the first mutation probe (5 survivors)
def test_a_pool_row_with_an_input_available_after_its_own_decision_is_refused_p36():
    pool = pool_fixture()
    pool[3].avail[B.VOL] = pool[3].decision_time + 60.0
    with pytest.raises(F.AsOfError, match="future feature"):
        A.check_pool(pool, AS_OF)


def test_cluster_is_the_creator_when_known_else_the_mint():
    assert A.cluster_of("solana", "M1", "C1") == "creator:C1"
    assert A.cluster_of("solana", "M1", None) == "mint:solana:M1" and A.cluster_of("solana", "M1", "") == "mint:solana:M1"
    pool = pool_fixture()
    twins = [ex(f"tw{i}", f"TW{i}", T0 + i * DAY, 1, creator="ONEDEV", liq=10.0, mcap=12.0, vol=9.0, age=1.0) for i in range(2)]
    a = A.select("AC2_KNN", target(), pool + twins, as_of=AS_OF)
    assert sum(1 for x in a["analogs"] if x["mint"] in ("TW0", "TW1")) == 1


def test_scale_uses_the_population_sd_and_distances_equal_the_brute_force():
    pool = pool_fixture(seed=5)
    a = A.select("AC2_KNN", target(), pool, as_of=AS_OF)
    X = np.array([[r.x[c] for c in A.NUMERIC] for r in pool])
    assert np.allclose(a["scale"]["sd"], X.std(0)) and np.allclose(a["scale"]["mean"], X.mean(0))
    keys = {r.decision_key: r for r in pool}
    q = (np.array([target().x[c] for c in A.NUMERIC]) - X.mean(0)) / X.std(0)
    for x in a["analogs"]:
        z = (np.array([keys[x["decision_key"]].x[c] for c in A.NUMERIC]) - X.mean(0)) / X.std(0)
        assert math.isclose(x["distance"], math.sqrt(float(np.sum((z - q) ** 2))), rel_tol=1e-12)


def test_ties_inside_a_cluster_go_to_the_smaller_decision_key_whatever_the_order():
    rows = [ex("kb", "MB", T0, 1, creator="SAMEDEV"), ex("ka", "MA", T0 + DAY, 0, creator="SAMEDEV")]
    idx = A.KnnIndex(rows)
    assert [idx.keys[i] for i in idx.nearest_clusters(np.zeros(2))] == ["ka"]


def test_tone_is_the_share_of_constructive_lab_statuses():
    rows = [rr(T0 + i * 3600.0, s, 10.0) for i, s in enumerate(["WATCH", "REJECTED", "DISTRIBUTION RISK", "NEAR ENTRY"])]
    rec = A.regime_as_of(rows, T0 + 3 * 3600.0)
    assert rec["tone_constructive_share"] == 0.5 and rec["window_decisions"] == 4


# ---------------------------------------------------------------- committed outputs (added with them)
def test_committed_outputs_ledger_registry_verdicts_and_traps():
    import csv
    p11 = ROOT / "audits/predictive-intelligence/phase_11"
    led = list(csv.DictReader(open(p11 / "experiments/SEARCH_LEDGER.csv")))
    prior = list(csv.DictReader(open(ROOT / "audits/predictive-intelligence/phase_10/experiments/SEARCH_LEDGER.csv")))
    assert led[:len(prior)] == prior
    ids = {r["experiment_id"] for r in led[len(prior):]}
    reg = [r["experiment_id"] for r in csv.DictReader(open(p11 / "experiments/EXPERIMENT_REGISTRY.csv"))]
    traps = {"NC2AC", "P13AC", "P36AC", "P43AC", "P14AC", "CX11"}
    missing = [x for x in reg if x.split(":")[-1] not in traps and not any(i.startswith(x) for i in ids)]
    assert missing == []
    assert sum(1 for r in led[len(prior):] if r["kind"] == "DEBUG_RUN_REAL_DATA") == 2
    metrics = list(csv.DictReader(open(p11 / "experiments/ANALOG_METRICS.csv")))
    assert all(r["verdict"] in ("INSUFFICIENT_DAYS", "INSUFFICIENT_EVENTS", "INSUFFICIENT_HISTORY") for r in metrics)
    assert all(r["promotion"] == "MODEL_NOT_PROMOTED" for r in metrics)
    t = json.loads((p11 / "evidence/traps.json").read_text())
    assert all(v.get("pass") is not False for v in t.values()) and t["CX11"]["full_sample_label_differs"] == 32
