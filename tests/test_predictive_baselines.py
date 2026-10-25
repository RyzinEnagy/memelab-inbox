"""Phase 07: transparent baselines, negative controls and the frozen walk-forward (memelab/predictive/baselines.py).

Synthetic, seeded fixtures only; every fixture result carries NO_REAL_HISTORICAL_EVIDENCE. The real run is
audits/predictive-intelligence/phase_07/probes/run_baselines.py. No network, temp stores, fixed times. Scenario ids from the
package's ADVERSARIAL_SCENARIOS.md; CX-07 is this phase's new counterexample.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

from memelab.predictive import baselines as B
from memelab.predictive import contract as C
from memelab.predictive import features as F
from memelab.predictive import labels as L
from memelab.predictive import stats as K

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests" / "fixtures" / "predictive"))
import asof_helpers as H  # noqa: E402

T1, T1B = L.T1, L.T1B
H0 = L.holdout_start()
D0 = C.parse_utc("2026-10-01T00:00:00Z")
MINTS = [H.MINT_A, H.MINT_B, H.POOL_A, H.POOL_B, H.POOL_A2]       # valid base58 strings used as distinct identities


def make(n=600, *, seed=7, signal=0.9, days=16, target=T1, missing_age=0.1):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        t = D0 + rng.uniform(0, days * 86400)
        liq = rng.normal(11, 1.5)
        z = -1.2 + signal * (liq - 11)
        y = int(rng.uniform() < 1 / (1 + math.exp(-z)))
        x = {B.LIQ: liq, B.MCAP: liq + rng.normal(1, 0.3), B.VOL: rng.normal(12, 1), B.FATAL: float(rng.uniform() < 0.2),
             B.AGE: (float("nan") if rng.uniform() < missing_age else math.log1p(rng.uniform(0, 30))),
             B.SCORE: float(rng.integers(20, 80))}
        out.append(B.Example(f"k{i:04d}", "solana", f"{MINTS[i % 5]}{i % 150}", t, C.label_matures_at(target, t), y, x,
                             {c: t for c in x}, status=["REJECTED", "WATCH", "DISTRIBUTION RISK"][i % 3], creator=f"c{i % 40}",
                             route="PIT_RECORDED", label_key=f"l{i}", snapshot_sha256="0" * 64))
    return [e for e in out if e.label_matures_at <= H0]


def gate_like(dev):
    return lambda c: [e for e in dev if e.decision_time < c and e.label_matures_at <= c]


@pytest.fixture(scope="module")
def fixture_run():
    dev = make()
    return dev, B.walk_forward(T1, dev, gate_like(dev), nc1_seeds=range(5), is_fixture=True)


# ---------------------------------------------------------------- G16: synthetic fixture with known signal
def test_fixture_b2_beats_b0_nc1_does_not_and_everything_says_no_real_evidence(fixture_run):
    dev, res = fixture_run
    assert res["evidence_class"] == B.FIXTURE_FLAG
    assert all(c["evidence_class"] == B.FIXTURE_FLAG for f in res["folds"] for c in f["cards"].values())
    b2 = B.evaluate(res["oos"], "B2", reps=200)
    assert b2["bss"] > 0.1 and b2["auc"] > 0.7
    nc = [B.evaluate(res["oos"], f"NC1_{s}", boot=False)["bss"] for s in range(5)]
    assert np.mean(nc) < b2["bss"] / 3                     # shuffled training labels lose the signal
    assert res["audit"]["valid_walk_forward"]


def test_every_card_is_provisional_and_claims_no_revision_check(fixture_run):
    _, res = fixture_run
    for f in res["folds"]:
        for c in f["cards"].values():
            assert c["status"] == B.PROVISIONAL and c["revision_check_claimed"] is False and c["publishable"] is False
            assert c["training_cutoff"] == f["cutoff"] and c["max_train_label_matures_at"] <= f["cutoff"]


# ---------------------------------------------------------------- count gates and abstention
def test_count_gate_abstains_below_the_frozen_minimums():
    dev = make(n=400, seed=3)
    cut = H0
    train = gate_like(dev)(cut)
    pos = [e for e in train if e.y == 1]
    neg = [e for e in train if e.y == 0]
    few_pos = neg[:150] + pos[:19]
    cards = B.fit_all(T1, few_pos, cut)
    assert "p" in cards["B0"]["body"]
    for b in B.GATED:
        assert cards[b]["body"] == {"abstain": "INSUFFICIENT_HISTORY"}, b
        p, why = B.predict(cards[b], train[:3])
        assert np.all(np.isnan(p)) and why == ["INSUFFICIENT_HISTORY"] * 3
    small = neg[:79] + pos[:20]                              # 99 events
    assert all(B.fit_all(T1, small, cut)[b]["body"].get("abstain") == "INSUFFICIENT_HISTORY" for b in B.GATED)
    ok = neg[:80] + pos[:20]
    assert all("abstain" not in B.fit_all(T1, ok, cut)[b]["body"] for b in B.GATED)


def test_missing_required_inputs_abstain_ood_and_optional_age_does_not():
    dev = make(n=400, seed=4)
    cards = B.fit_all(T1, gate_like(dev)(H0), H0)
    e = dev[0]
    no_liq = B.Example(**{**e.__dict__, "x": {**e.x, B.LIQ: float("nan")}})
    no_score = B.Example(**{**e.__dict__, "x": {**e.x, B.SCORE: float("nan")}})
    no_age = B.Example(**{**e.__dict__, "x": {**e.x, B.AGE: float("nan")}})
    p, why = B.predict(cards["B2"], [no_liq, no_age])
    assert math.isnan(p[0]) and why[0] == "OOD" and math.isfinite(p[1]) and why[1] is None
    p, why = B.predict(cards["B3"], [no_score])
    assert math.isnan(p[0]) and why == ["OOD"]
    p, _ = B.predict(cards["B4"], [no_liq])
    assert p[0] == cards["B4"]["body"]["b0"]                 # no match information: the training prevalence


def test_token_age_in_days_and_a_negative_age_is_missing():
    base = {B.SOURCE_OF[c]: 1.0 for c in B.ALLOWED_COLUMNS}
    base.update({B.SOURCE_OF[c] + "__available_at": 0.0 for c in B.ALLOWED_COLUMNS})
    x, _ = B.model_inputs(dict(base, token_age_s=2 * 86400.0))
    assert x[B.AGE] == pytest.approx(math.log1p(2.0))
    x, _ = B.model_inputs(dict(base, token_age_s=-3600.0))           # a first pool after the decision is not "young"
    assert math.isnan(x[B.AGE])
    x, _ = B.model_inputs(dict(base, token_age_s=None))
    assert math.isnan(x[B.AGE])


def test_b1_b3f_b4_shrink_toward_b0_and_b4_never_matches_the_same_mint():
    dev = make(n=400, seed=5)
    train = gate_like(dev)(H0)
    cards = B.fit_all(T1, train, H0)
    b0 = cards["B0"]["body"]["p"]
    for g, v in cards["B1"]["body"]["groups"].items():
        assert v["p"] == pytest.approx((v["k"] + 20 * b0) / (v["n"] + 20))
    one = B.Example(**{**train[0].__dict__})
    tr_same = [B.Example(**{**e.__dict__, "mint": one.mint}) for e in train]
    c4 = B.fit_b4(T1, tr_same, H0)
    p, _ = B.predict(c4, [one])
    assert p[0] == pytest.approx(c4["body"]["b0"])           # every training row is the same mint: no control


# ---------------------------------------------------------------- the gate, the walk-forward and time rules
def test_walk_forward_refuses_a_gate_that_disagrees_with_the_frozen_index():
    dev = make(n=400, seed=6)
    extra = dev[-1]
    with pytest.raises(B.WalkForwardMismatch):
        B.walk_forward(T1, dev, lambda c: gate_like(dev)(c) + [extra], nc1_seeds=())


def test_p05_p43_fit_refuses_a_row_decided_after_or_maturing_after_the_cutoff():
    dev = make(n=300, seed=8)
    cut = C.parse_utc("2026-10-12T00:00:00Z")
    train = gate_like(dev)(cut)
    late = [e for e in dev if e.decision_time >= cut][0]               # a token decided after the cutoff (P43)
    with pytest.raises(F.AsOfError):
        B.fit_all(T1, train + [late], cut)
    unmatured = [e for e in dev if e.decision_time < cut < e.label_matures_at][0]   # P05
    with pytest.raises(F.AsOfError):
        B.fit_all(T1, train + [unmatured], cut)


def test_p20_six_hour_maturities_given_for_a_24_hour_target_fail_the_fold_audit():
    dev = make(n=500, seed=9)
    short = [B.Example(**{**e.__dict__, "label_matures_at": C.label_matures_at(T1B, e.decision_time)}) for e in dev]
    with pytest.raises(B.BaselineError, match="fold audit failed"):
        B.walk_forward(T1, short, gate_like(short), nc1_seeds=())


def test_p13_a_card_trained_after_the_decision_cannot_back_a_forecast():
    dev = make(n=400, seed=10)
    card = B.fit_all(T1, gate_like(dev)(H0), H0)["B2"]
    e = dev[0]
    doc = B.abstain_document(T1, mint=H.MINT_A, snapshot_hash="a" * 64, decision_time_utc=B._iso(e.decision_time),
                             generated_at_utc=B._iso(e.decision_time + 60), reasons=["MODEL_NOT_SELECTED"], base_rate=0.2,
                             card=card)
    fc = dict(doc, prediction_status="FORECAST", abstain_reasons=[], probability=0.3, uncertainty_interval=[0.2, 0.4],
              calibration_reference={"holdout_n": 60, "passed": True})
    mc = {k: card[k] for k in ("model_sha", "feature_set_sha", "targets", "target_version", "training_cutoff_utc")}
    errs = C.validate(fc, model_card=mc, backtest=C.BACKTEST_NOT_AVAILABLE)
    assert any("model trained after the decision" in x for x in errs)


# ---------------------------------------------------------------- traps: NC2, NC3, CX-07
def test_nc2_a_future_feature_is_refused_by_the_allowlist_and_by_validate_rows():
    e = make(n=50, seed=11)[0]
    e2 = B.Example(**{**e.__dict__, "x": {**e.x, "trap_future_label": float(e.y)},
                      "avail": {**e.avail, "trap_future_label": e.label_matures_at}})
    with pytest.raises(F.AsOfError, match="allowlist"):
        B.check_asof([e2], ["trap_future_label"], as_of=None, with_labels=False)
    with pytest.raises(F.AsOfError, match="allowlist"):
        B.matrix([e2], ["trap_future_label"])
    row = {"decision_time": e.decision_time, "trap": float(e.y), "trap__available_at": e.label_matures_at}
    with pytest.raises(F.AsOfError, match="future feature"):
        F.validate_rows([row], columns=list(row), availability=["trap__available_at"])
    late = B.Example(**{**e.__dict__, "avail": {**e.avail, B.LIQ: e.decision_time + 1}})     # an allowed column, one second late
    with pytest.raises(F.AsOfError, match="future feature"):
        B.check_asof([late], [B.LIQ], as_of=None, with_labels=False)


def _label_row(e: B.Example) -> dict:
    return {"decision_key": e.decision_key, "chain": e.chain, "mint": e.mint, "decision_time": e.decision_time,
            "label_matures_at": e.label_matures_at, "label": e.y, "label_key": e.label_key, "groups_json": "{}",
            "cohort_json": "{}", "flags_json": "[]", "route": "PIT_RECORDED"}


def _feature_row(e: B.Example, **over) -> dict:
    r = {"decision_key": e.decision_key, "chain": e.chain, "mint": e.mint, "decision_time": e.decision_time}
    for col in B.ALLOWED_COLUMNS:
        src = B.SOURCE_OF[col]
        v = e.x[col]
        if col == B.AGE:
            v = math.expm1(v) * 86400 if math.isfinite(v) else None
        r[src], r[src + "__available_at"] = v, e.decision_time
    r.update(over)
    return r


def test_nc3_p01_a_same_symbol_join_of_another_mint_is_refused():
    a, b = make(n=10, seed=12)[:2]
    assert a.mint != b.mint
    with pytest.raises(B.IdentityJoinError):
        B.join_by_symbol(_label_row(a), {"SAME": _feature_row(b)}, "SAME")
    with pytest.raises(B.IdentityJoinError):
        B.join([_label_row(a)], {a.decision_key: _feature_row(b, decision_key=a.decision_key)})
    case = _feature_row(a, mint=a.mint.lower(), decision_key=a.decision_key)     # same mint up to letter case is another identity
    with pytest.raises(B.IdentityJoinError):
        B.join([_label_row(a)], {a.decision_key: case})
    got = B.join([_label_row(a)], {a.decision_key: _feature_row(a)})
    assert got[0].mint == a.mint and got[0].x[B.LIQ] == pytest.approx(a.x[B.LIQ])


def test_cx07_join_by_mint_with_its_latest_snapshot_is_refused():
    """CX-07 (new, this phase): a plausible join keyed by mint that takes the mint's newest stored snapshot attaches a later
    decision's features to an earlier label (on the real development labels, 250 of 491 label rows have a later snapshot of
    the same mint, evidence/traps.json). The identity join refuses it: the decision time and key must match."""
    e = make(n=10, seed=13)[0]
    later = _feature_row(e, decision_key="later", decision_time=e.decision_time + 3600)
    with pytest.raises(B.IdentityJoinError, match="decision time"):
        B.join([_label_row(e)], {e.decision_key: later})
    with pytest.raises(B.BaselineError, match="no stored feature snapshot"):
        B.join([_label_row(e)], {})


def test_join_reads_training_labels_from_a_real_label_store(tmp_path):
    """The gate's own rows (labels.training_labels on a temp store) join to feature rows of the same decision only."""
    from test_predictive_labels import DT, LATE, MINT, POOL, T2B, TE, dec, grid, mkread, ref_rows  # noqa: E402
    con = L.connect(tmp_path / "labels.sqlite")
    d = dec(t=DT, key="a")
    recs, _ = L.build(L.Universe([d], as_of=LATE, read_of={"a": mkread(ref_rows() + grid(TE, TE + 2 * 86400), T2B())}))
    L.store_labels(con, recs, export_ref="x", params={}, now=LATE)
    rows = L.training_labels(con, LATE, T1)
    assert len(rows) == 1
    ex = B.Example("a", "solana", MINT, DT, C.label_matures_at(T1, DT), 0, {c: 1.0 for c in B.ALLOWED_COLUMNS},
                   {c: DT for c in B.ALLOWED_COLUMNS})
    fr = _feature_row(ex)
    got = B.join(rows, {"a": fr})
    assert got[0].label_key == rows[0]["label_key"] and got[0].y == rows[0]["label"]
    with pytest.raises(B.IdentityJoinError):
        B.join(rows, {"a": dict(fr, mint=H.MINT_B)})
    con.close()


# ---------------------------------------------------------------- P10, P11, P23, P24, P38, P21
def _rows(y, p, b0, days, mints):
    return [{"y": int(yy), "M": float(pp), "B0": float(bb), "fold": 0,
             "example": B.Example(f"k{i}", "solana", mm, D0 + dd * 86400, D0, int(yy))}
            for i, (yy, pp, bb, dd, mm) in enumerate(zip(y, p, b0, days, mints))]


def test_p10_an_always_negative_model_on_a_rare_event_loses_to_the_base_rate():
    n = 500
    y = np.zeros(n)
    y[::50] = 1                                                     # 2% positives
    rows = _rows(y, np.zeros(n), np.full(n, 0.02), np.arange(n) % 10, [f"m{i}" for i in range(n)])
    ev = B.evaluate(rows, "M", reps=200)
    assert ev["bss"] < 0 and ev["auc"] is None and "constant" in ev["auc_note"]
    assert ev["brier"] == pytest.approx(0.02) and ev["log_loss"] > ev["log_loss_ref"]


def test_p11_flat_all_positive_predictions_fail_calibration_and_skill():
    n = 200
    y = (np.arange(n) % 4 == 0).astype(float)
    rows = _rows(y, np.full(n, 0.99), np.full(n, 0.25), np.arange(n) // 25, [f"m{i % 50}" for i in range(n)])
    ev = B.evaluate(rows, "M", reps=200)
    assert not ev["calibration"]["in_the_large_ok"] and ev["bss"] < -1
    assert B.verdict(ev) == "WORSE_THAN_BASE_RATE"


def test_p23_p24_few_days_give_no_interval_and_no_claim_but_both_scores_with_counts():
    n = 60
    rng = np.random.default_rng(1)
    y = (rng.uniform(size=n) < 0.3).astype(float)
    p = np.clip(y * 0.6 + 0.2, 0, 1)                                 # very good numbers on 3 days only
    rows = _rows(y, p, np.full(n, 0.3), np.arange(n) % 3, [f"m{i}" for i in range(n)])
    ev = B.evaluate(rows, "M", reps=200)
    assert ev["bss"] > 0.3 and ev["days"] == 3
    assert ev["intervals"]["day"]["ci"] is None and ev["gov_ci"] is None and ev["verdict"] == "INSUFFICIENT_DAYS"
    assert {"brier", "log_loss", "positives", "prevalence", "mints"} <= set(ev)
    assert B.verdict(ev, p_holm=0.0) == "INSUFFICIENT_DAYS"          # Holm cannot rescue a claim on 3 days


def test_verdicts_need_five_days_an_interval_above_zero_and_holm():
    base = {"n_with_number": 50, "positives": 15, "days": 6}
    assert B.verdict(dict(base, gov_ci=[0.01, 0.2]), p_holm=0.01) == "SKILL_INDICATED_DEVELOPMENT_ONLY"
    assert B.verdict(dict(base, gov_ci=[0.01, 0.2]), p_holm=0.2) == "NOT_DISTINGUISHABLE_FROM_BASE_RATE"
    assert B.verdict(dict(base, gov_ci=[0.01, 0.2])) == "NOT_DISTINGUISHABLE_FROM_BASE_RATE"
    assert B.verdict(dict(base, gov_ci=[-0.1, 0.2]), p_holm=0.01) == "NOT_DISTINGUISHABLE_FROM_BASE_RATE"
    assert B.verdict(dict(base, gov_ci=[-0.3, -0.01])) == "WORSE_THAN_BASE_RATE"
    assert B.verdict(dict(base, days=4, gov_ci=[0.1, 0.2]), p_holm=0.0) == "INSUFFICIENT_DAYS"
    assert B.verdict({"n_with_number": 0}) == "INSUFFICIENT_HISTORY"


def test_p38_a_card_with_a_non_finite_number_cannot_be_serialised_or_used():
    dev = make(n=300, seed=14)
    card = B.fit_all(T1, gate_like(dev)(H0), H0)["B2"]
    bad = json.loads(B.dumps(card))
    bad["body"]["logistic"]["coef"][0] = float("nan")
    with pytest.raises(ValueError):
        B.dumps(bad)
    with pytest.raises(ValueError):                         # canonical JSON refuses NaN before any hash comparison
        B.verify_card(bad)


def test_p21_cohort_tables_split_by_week_and_claim_no_rate_below_20(fixture_run):
    _, res = fixture_run
    tab = B.cohort_table(res["oos"], lambda e: e.cohort.get("week_utc") or B._iso(e.decision_time)[:8])
    assert sum(r["n"] for r in tab) == len(res["oos"])
    assert all((r["support_note"] == "n >= 20") == (r["n"] >= 20) for r in tab)


# ---------------------------------------------------------------- artifacts, serialization and the contract
def test_cards_round_trip_exactly_and_a_changed_number_is_refused(tmp_path):
    dev = make(n=400, seed=15)
    train = gate_like(dev)(H0)
    cards = B.fit_all(T1, train, H0)
    for b, card in cards.items():
        p = tmp_path / f"{b}.json"
        p.write_text(B.dumps(card))
        back = B.loads(p.read_text())
        a1, w1 = B.predict(card, train)
        a2, w2 = B.predict(back, train)
        assert np.array_equal(a1, a2) and w1 == w2, b
        assert back["model_sha"] == card["model_sha"] and back["training_cutoff_utc"] == "2026-10-17T00:00:00Z"
        assert back["feature_set_sha"] == F.feature_set_sha() and back["registry_sha"] == C.registry_sha256()
        t = json.loads(p.read_text())
        t["n_train"] += 1
        with pytest.raises(B.ModelHashMismatch):
            B.verify_card(t)
    src = Path(B.__file__).read_text()
    assert not list(tmp_path.glob("*.pkl")) and "import pickle" not in src and "pickle.load" not in src


def test_an_abstain_document_from_a_card_is_valid_and_a_forecast_without_holdout_calibration_is_refused():
    dev = make(n=400, seed=16)
    cards = B.fit_all(T1, gate_like(dev)(H0), H0)
    e = dev[-1]
    doc = B.abstain_document(T1, mint=H.MINT_A, snapshot_hash="b" * 64, decision_time_utc="2026-10-18T00:00:00Z",
                             generated_at_utc="2026-10-18T00:00:01Z", reasons=["INSUFFICIENT_HISTORY", "MODEL_NOT_SELECTED"],
                             base_rate=cards["B0"]["body"]["p"], card=cards["B2"])
    assert C.validate(doc, backtest=C.BACKTEST_NOT_AVAILABLE) == []
    fc = dict(doc, prediction_status="FORECAST", abstain_reasons=[], probability=0.3, uncertainty_interval=[0.2, 0.4])
    mc = {k: cards["B2"][k] for k in ("model_sha", "feature_set_sha", "targets", "target_version", "training_cutoff_utc")}
    errs = C.validate(fc, model_card=mc, backtest=C.BACKTEST_NOT_AVAILABLE)
    assert any("calibration_reference" in x for x in errs)
    assert e.decision_time < H0


def test_the_new_modules_use_only_numpy_and_the_standard_library():
    import ast
    for mod in (B, K):
        tree = ast.parse(Path(mod.__file__).read_text())
        names = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        names |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module and n.level == 0}
        assert names <= {"__future__", "hashlib", "json", "math", "dataclasses", "typing", "numpy", "datetime"}, (mod, names)


# ---------------------------------------------------------------- repair pass 2: frozen interval and verdict rules (skeptic M1)
def _clustered_rows(seed=3, days=6, per_day=20, mints=60):
    """Rows over `days` decision days and `mints` mints; the model beats B0 strongly on some days and not on others."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(days * per_day):
        d = i // per_day
        y = int(rng.uniform() < 0.3)
        good = d % 2 == 0
        p = (0.6 if y else 0.15) if good else (0.25 if y else 0.35)
        rows.append({"y": y, "M": p, "B0": 0.3, "fold": d,
                     "example": B.Example(f"k{i}", "solana", f"m{i % mints}", D0 + d * 86400 + 600, D0, y)})
    return rows


def test_the_interval_is_the_95_percent_percentile_of_the_group_bootstrap():
    rng = np.random.default_rng(0)
    v = rng.normal(size=200)
    groups = [f"g{i % 40}" for i in range(200)]
    bs = K.group_bootstrap(groups, lambda idx: float(np.mean(v[idx])), reps=1000, seed=4)
    fin = bs["values"][np.isfinite(bs["values"])]
    assert bs["ci"] == pytest.approx((float(np.quantile(fin, 0.025)), float(np.quantile(fin, 0.975))), abs=1e-12)
    assert bs["ci"][0] < float(np.quantile(fin, 0.05)) - 1e-6                  # not a 90% interval


def test_the_wider_interval_governs_and_the_mint_bootstrap_groups_by_mint():
    rows = _clustered_rows()
    ev = B.evaluate(rows, "M", reps=500)
    iv = ev["intervals"]
    assert iv["day"]["groups"] == 6 and iv["mint"]["groups"] == 60          # mint intervals resample mints, not days
    widths = {u: iv[u]["ci"][1] - iv[u]["ci"][0] for u in iv}
    assert widths["day"] != widths["mint"]
    assert ev["governing"] == max(widths, key=widths.get) and ev["gov_ci"] == iv[ev["governing"]]["ci"]
    # an explicit case where the narrower interval excludes 0 and the wider does not: not a WORSE verdict
    res = {"n_with_number": 120, "positives": 36, "days": 6, "gov_ci": None}
    res.update(intervals={"day": {"ci": [-0.19, -0.06]}, "mint": {"ci": [-0.49, 0.03]}})
    w = max(res["intervals"], key=lambda u: res["intervals"][u]["ci"][1] - res["intervals"][u]["ci"][0])
    assert w == "mint"
    assert B.verdict(dict(res, gov_ci=res["intervals"][w]["ci"])) == "NOT_DISTINGUISHABLE_FROM_BASE_RATE"


def test_worse_than_base_rate_needs_the_upper_bound_below_zero():
    base = {"n_with_number": 60, "positives": 15, "days": 6}
    assert B.verdict(dict(base, gov_ci=[-0.3, -0.001])) == "WORSE_THAN_BASE_RATE"
    assert B.verdict(dict(base, gov_ci=[-0.3, 0.01])) == "NOT_DISTINGUISHABLE_FROM_BASE_RATE"
    assert B.verdict(dict(base, gov_ci=[-0.3, 0.0])) == "NOT_DISTINGUISHABLE_FROM_BASE_RATE"


def test_the_one_sided_p_counts_replicates_at_zero_as_no_skill():
    rows = _clustered_rows()
    for r in rows:
        r["M"] = r["B0"]                                                      # every replicate's skill is exactly 0
    ev = B.evaluate(rows, "M", reps=300)
    assert ev["bss"] == 0.0 and ev["p_one_sided"] == 1.0
    assert all(ev["intervals"][u]["p_one_sided"] == 1.0 for u in ev["intervals"])


def test_an_unseen_status_group_gets_the_training_prevalence():
    dev = make(n=400, seed=21)
    card = B.fit_all(T1, gate_like(dev)(H0), H0)["B1"]
    e = B.Example(**{**dev[0].__dict__, "status": "A STATUS NEVER SEEN"})
    p, why = B.predict(card, [e])
    assert p[0] == card["body"]["b0"] and why == [None]


def test_log_loss_clip_and_population_standardisation():
    assert K.log_loss(np.array([1.0, 0.0]), np.array([0.0, 0.0])) == pytest.approx((-math.log(1e-6) - math.log(1 - 1e-6)) / 2, abs=1e-12)
    X = np.array([[1.0, 2.0], [3.0, 2.5], [5.0, 7.0], [7.0, 1.0]])
    prep = K.Prep().fit(X)
    assert np.allclose(prep.sd, X.std(axis=0, ddof=0)) and np.allclose(prep.transform(X).std(axis=0), 1.0)


def test_b4c_uses_controls_within_12_hours_only():
    e0 = make(n=10, seed=22)[0]
    def ctl(i, dt, y):
        return B.Example(**{**e0.__dict__, "decision_key": f"c{i}", "mint": f"{H.MINT_B}{i}", "decision_time": e0.decision_time + dt, "y": y})
    near = [ctl(i, 11 * 3600, 1) for i in range(3)]
    far = [ctl(10 + i, 13 * 3600, 0) for i in range(3)]
    assert B.contemporaneous_control(e0, near + far) == 1.0
    assert math.isnan(B.contemporaneous_control(e0, far[:0] + near[:2]))         # fewer than 3 controls: none


# ---------------------------------------------------------------- repair pass 2: CX-S07 and the out-of-sample count gate (m1, m2)
def test_cx_s07_one_positive_over_five_days_never_earns_a_skill_verdict():
    """CX-S07 (Phase 07 skeptic): 6 rows with one positive over 5 days had earned SKILL_INDICATED_DEVELOPMENT_ONLY. The frozen
    out-of-sample minimums (50 events, 10 per class) now stand behind every directional verdict."""
    base = C.parse_utc("2026-10-12T12:00:00Z")
    spec = [(0, 1, 0.45), (0, 0, 0.05), (1, 0, 0.06), (2, 0, 0.05), (3, 0, 0.07), (4, 0, 0.05)]
    rows = [{"fold": d, "y": y, "B0": 0.20, "B2": p, "B2_why": None,
             "example": B.Example(f"k{i}", "solana", f"Mint{i}pump", base + d * 86400.0, base + d * 86400.0 + 87600, y)}
            for i, (d, y, p) in enumerate(spec)]
    ev = B.evaluate(rows, "B2")
    p_holm = K.holm([float("nan"), ev["p_one_sided"], float("nan")])[1]
    assert ev["days"] == 5 and ev["gov_ci"][0] > 0 and p_holm < 0.05            # the interval alone would say skill
    assert B.verdict(ev, p_holm) == "INSUFFICIENT_EVENTS"


def test_the_out_of_sample_count_gate_uses_the_frozen_minimums():
    a = C.ACCEPTANCE
    assert (a["min_holdout_events"], a["min_holdout_per_class"]) == (50, 10)
    assert B.evaluation_gate(50, 10) is None and B.evaluation_gate(50, 40) is None
    assert B.evaluation_gate(49, 20) == B.evaluation_gate(50, 9) == B.evaluation_gate(50, 41) == "INSUFFICIENT_EVENTS"
    ok = {"n_with_number": 50, "positives": 10, "days": 5, "gov_ci": [0.01, 0.2]}
    assert B.verdict(ok, p_holm=0.01) == "SKILL_INDICATED_DEVELOPMENT_ONLY"
    for bad in (dict(ok, n_with_number=49), dict(ok, positives=9), dict(ok, positives=41)):
        assert B.verdict(bad, p_holm=0.01) == "INSUFFICIENT_EVENTS"
        assert B.verdict(dict(bad, gov_ci=[-0.3, -0.1])) == "INSUFFICIENT_EVENTS"     # no WORSE claim either
    assert B.verdict(dict(ok, days=4, n_with_number=10), p_holm=0.01) == "INSUFFICIENT_DAYS"   # days first


def test_nc1_verdicts_follow_the_same_minimums():
    assert B.nc1_verdict(8, 1, 1, 0.02) == "INSUFFICIENT_DAYS"
    assert B.nc1_verdict(44, 3, 5, -0.03) == "INSUFFICIENT_EVENTS"
    assert B.nc1_verdict(60, 12, 6, -0.03) == "NC1_DEGRADES_OR_EQUAL"
    assert B.nc1_verdict(60, 12, 6, 0.01) == "NC1_FAILS_MEAN_BSS_ABOVE_0"
    assert B.nc1_verdict(0, 0, 0, None) == "INSUFFICIENT_HISTORY"


def test_the_identity_join_also_checks_the_chain():
    a = make(n=10, seed=23)[0]
    with pytest.raises(B.IdentityJoinError, match="chain"):
        B.join([_label_row(a)], {a.decision_key: _feature_row(a, chain="base")})
