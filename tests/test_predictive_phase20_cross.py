"""Phase 20: cross-component negative scenarios X01 to X06 (pre-registration: audits/predictive-intelligence/phase_20/
ACCEPTANCE_CHECKLIST.md; X06 added before the frozen audit code, see the evidence file). Each scenario runs one path through at
least three components with one planted defect, beside a positive control on the same path.

A scenario whose expected behaviour does not hold at the code is marked xfail(strict=True) with its finding id, so the suite
records the open defect without failing, and a repair that fixes it turns the xfail into an error until the marker is removed.
At the audited code 0d66379, X02, the X03 run_pass case, X06 and the carried Phase 18 minor 5 were such markers; change control
CP20-1 (PI-D-110) repaired them and removed the markers. X04 stays marked (F20-04 waits for G25). Temp folders, fixed clocks, no
network (an audit hook refuses sockets). Every FORECAST here is a fixture."""
from __future__ import annotations

import copy
import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tests" / "fixtures" / "predictive"))

import test_predictive_integration as TI  # noqa: E402  (fixture champion builders, Phase 17)
import test_predictive_monitoring as TM  # noqa: E402  (outcome ledger builders, Phase 19)
import test_predictive_reports as TRP  # noqa: E402  (report helpers, Phase 18)
import asof_helpers as H  # noqa: E402

from memelab import db  # noqa: E402
from memelab.predictive import baselines as B  # noqa: E402
from memelab.predictive import calibration as CAL  # noqa: E402
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import evaluation as E  # noqa: E402
from memelab.predictive import integration as I  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import monitoring as M  # noqa: E402
from memelab.predictive import registry as R  # noqa: E402
from memelab.predictive import reports as RP  # noqa: E402

DAY = 86400.0
T_FX = TI.T_FX


@pytest.fixture
def lab(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "lab.sqlite")
    monkeypatch.setattr(db, "DATA_DIR", tmp_path / "data")
    (tmp_path / "data").mkdir()
    db.init_db()
    return tmp_path


def _pass(tmp, w, rs, *, T=T_FX, state="state", **kw):
    return I.run_pass(rs, capture_time=T, lab_db=db.DB_PATH, state_dir=tmp / state, config_path=TI.cfg(tmp), **TI.fx_kw(w, tmp, **kw))


def _report(tmp, w, state="state"):
    v = RP.build(tmp / state, config_path=TI.cfg(tmp), lab_db=db.DB_PATH, registry_dir=w["registry_dir"], extra_cal_cards=w["extra"])
    return v, RP.render(v)


def _numbers(v):
    return [t["number"] for o in v["opportunities"] for t in o["targets"] if t["number"] is not None]


def _lines(tmp, name, state="state"):
    p = tmp / state / I.FILES[name]
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


# ---------------------------------------------------------------- X01 future vendor candles
def test_x01_control_a_served_reference_candle_gives_the_fixture_forecast_and_the_report_shows_it(lab):
    w = TI.fixture_world(lab)
    s = _pass(lab, w, [TI.persist(TI.result("FXA", TI.M1, T_FX - 600), lab)])
    assert s["metrics"]["completed_forecasts"] == 1
    v, text = _report(lab, w)
    assert len(_numbers(v)) == 1 and v["format_only"] is True


def test_x01_only_candles_that_close_at_or_after_the_decision_minus_the_lag_never_make_a_number(lab):
    w = TI.fixture_world(lab)

    def future(pool, mint, T):                         # the candle holding T, the one closing at T, and later ones
        a = int(T // 300 * 300)
        return [[a - 300, 1.0, 1.0, 1.0, 1.0, 1000.0], [a, 1.0, 1.0, 1.0, 1.0, 1000.0], [a + 300, 1.0, 1.0, 1.0, 1.0, 1000.0]]
    s = _pass(lab, w, [TI.persist(TI.result("FXA", TI.M1, T_FX - 600), lab)], reader=future)
    req = _lines(lab, "requests")[-1]
    assert req["eligibility"]["state"] != "ELIGIBLE"
    assert s["metrics"]["completed_forecasts"] == 0
    assert all(t["prediction_status"] == "ABSTAIN" and t["reasons"] and t["calibrated_point"] is None for t in req["targets"])
    v, text = _report(lab, w)
    assert _numbers(v) == [] and v["counts"]["probabilities_shown"] == 0


# ---------------------------------------------------------------- X02 cross-wired token row in the export replay
def _replay(lab, w, tok, state):
    r = TI.persist(TI.result("FXA", TI.M1, T_FX - 600), lab)
    con = sqlite3.connect(db.DB_PATH)
    con.row_factory = sqlite3.Row
    row = dict(con.execute("SELECT * FROM theses WHERE mint=? ORDER BY id DESC", (TI.M1,)).fetchone())
    own = dict(con.execute("SELECT * FROM tokens WHERE mint=?", (TI.M1,)).fetchone())
    con.close()
    token = own if tok == "own" else dict(own, mint=TI.M2, primary_pool=TI.POOL2)
    reads = []

    def reader(pool, mint, T):
        reads.append(pool)
        return TI.candles_ok(pool, mint, T)
    s = I.run_pass([r], capture_time=T_FX, state_dir=lab / state, config_path=TI.cfg(lab),
                   decision_rows=[{"row": row, "token": token, "decision_time": T_FX, "basis": "EXPORT_COMMIT"}],
                   **TI.fx_kw(w, lab, reader=reader))
    return s, reads


def test_x02_control_the_decisions_own_token_row_gives_the_fixture_forecast(lab):
    w = TI.fixture_world(lab)
    s, reads = _replay(lab, w, "own", "st_own")
    assert s["metrics"]["completed_forecasts"] == 1 and reads == [TI.POOL1]


def test_x02_a_token_row_of_another_mint_is_refused_and_its_pool_never_read_or_recorded(lab):     # F20-02, CP20-1
    w = TI.fixture_world(lab)
    s, reads = _replay(lab, w, "other", "st_other")
    req = _lines(lab, "requests", "st_other")[-1]
    assert reads == [] and TI.POOL2 not in json.dumps(req)
    assert req["event"] == "NOT_EXACT_IDENTITY" and req["detail"].startswith("TOKEN_ROW_OF_ANOTHER_IDENTITY")
    assert s["metrics"]["completed_forecasts"] == 0 and _lines(lab, "documents", "st_other") == []


def test_x02_a_token_row_of_another_chain_is_refused(lab):
    w = TI.fixture_world(lab)
    r = TI.persist(TI.result("FXA", TI.M1, T_FX - 600), lab)
    con = sqlite3.connect(db.DB_PATH)
    con.row_factory = sqlite3.Row
    row = dict(con.execute("SELECT * FROM theses WHERE mint=? ORDER BY id DESC", (TI.M1,)).fetchone())
    own = dict(con.execute("SELECT * FROM tokens WHERE mint=?", (TI.M1,)).fetchone())
    con.close()
    s = I.run_pass([r], capture_time=T_FX, state_dir=lab / "st_chain", config_path=TI.cfg(lab),
                   decision_rows=[{"row": row, "token": dict(own, chain="base"), "decision_time": T_FX, "basis": "EXPORT_COMMIT"}],
                   **TI.fx_kw(w, lab))
    assert s["metrics"]["event_counts"] == {"NOT_EXACT_IDENTITY": 1} and s["metrics"]["documents"] == 0


# ---------------------------------------------------------------- X03 millisecond clock
def test_x03_a_millisecond_capture_time_persists_nothing_and_the_hooks_show_the_refusal(lab):
    w = TI.fixture_world(lab)
    r = TI.persist(TI.result("FXA", TI.M1, T_FX - 600), lab)
    sec = I.scout_section([r], capture_time=T_FX * 1000, config_path=TI.cfg(lab), state_dir=lab / "st_ms", lab_db=db.DB_PATH,
                          registry_dir=w["registry_dir"], allow_fixture=True, extra_cal_cards=w["extra"], reader=TI.candles_ok)
    assert sec is not None and "CAPTURE_TIME_REFUSED" in sec and "Nothing was assessed or written" in sec    # was "Failed" at 0d66379
    line = I.analyze_line(r, capture_time=T_FX * 1000, config_path=TI.cfg(lab), state_dir=lab / "st_ms", lab_db=db.DB_PATH)
    assert line.startswith("predictive: CAPTURE_TIME_REFUSED") and "nothing assessed" in line
    assert not (lab / "st_ms").exists()


def test_x03_a_millisecond_observed_time_is_an_error_event_with_no_document(lab):
    w = TI.fixture_world(lab)
    r = TI.persist(TI.result("FXA", TI.M1, (T_FX - 600) * 1000), lab)
    s = _pass(lab, w, [r])
    assert s["metrics"]["event_counts"] == {"ERROR": 1} and s["metrics"]["documents"] == 0
    assert _lines(lab, "documents") == []


def test_x03_run_pass_itself_returns_a_visible_state_for_a_millisecond_capture_time(lab):      # F20-03, CP20-1
    w = TI.fixture_world(lab)
    r = TI.persist(TI.result("FXA", TI.M1, T_FX - 600), lab)
    for bad in (T_FX * 1000, "2026-10-29T00:00:00Z", float("nan")):
        s = _pass(lab, w, [r], T=bad)
        assert s is not None and s["state"] == "CAPTURE_TIME_REFUSED" and s["events"] == []
        assert "CAPTURE_TIME_REFUSED" in I.render(s)
    assert not (lab / "state").exists()


# ---------------------------------------------------------------- X04 a label read of another mint reaching the outcome ledger
def _ledger(tmp):
    p = tmp / "OUTCOME_LEDGER.jsonl"
    M.append(p, [{"kind": "PLAN", "plan_id": "p"}, TM.pset(), TM.pred(), TM.doc()])
    return p


def test_x04_control_an_identity_checked_labeled_outcome_appends_and_verifies(tmp_path):
    p = _ledger(tmp_path)
    M.append(p, [TM.outcome()])
    assert M.verify(p)["ok"]


def test_x04_a_body_whose_base_is_another_mint_gives_no_labeled_outcome():
    LT = __import__("test_predictive_labels")
    d1 = LT.dec()
    rows = LT.ref_rows() + LT.grid(LT.TE, LT.TE + 2 * DAY)
    url = H.GT.format(pool=d1["pool"], b=int(LT.T2B())) + f"&token={d1['mint']}"
    body = H.gt_body(rows, base=H.MINT_B, quote=d1["mint"])
    rd = L.read_from_body(body, mint=d1["mint"], pool=d1["pool"], url=url, boundary=LT.T2B(), retrieved_at=LT.LATE, http_status=200)
    recs, elig = L.build(L.Universe([d1], as_of=LT.LATE, read_of={d1["decision_key"]: rd}))
    assert not rd.ok and all(r["state"] != "LABELED" for r in recs)
    assert set(elig.values()) == {"VENDOR_OR_ROUTE_GAP"}


@pytest.mark.parametrize("case", ["prefix_extended_token", "token_only_in_another_parameter"])
@pytest.mark.xfail(strict=True, reason="F20-04 open (MINOR): the ledger's identity rule is a substring test on the URL, not the parsed "
                                        "token parameter")
def test_x04_the_ledger_refuses_a_labeled_outcome_whose_token_parameter_is_not_exactly_the_mint(tmp_path, case):
    p = _ledger(tmp_path)
    url = {"prefix_extended_token": f"https://api.geckoterminal.com/x?token={TM.MINT}Z",
           "token_only_in_another_parameter": f"https://api.geckoterminal.com/x?ref=token={TM.MINT}&token={TM.MINT_B}"}[case]
    with pytest.raises(M.LedgerError) as e:
        M.append(p, [TM.outcome(request_url=url)])
    assert e.value.code == "IDENTITY_MISMATCH"


# ---------------------------------------------------------------- X05 a swapped calibration card
def _forged(w, *, resha: bool) -> dict:
    """The fixture calibration card with its evidence moved into the spent retrospective holdout (source and as-of time), with
    its card_sha either recomputed (self-consistent forgery) or left as the original (inconsistent forgery)."""
    c = copy.deepcopy(w["cal"])
    c["evidence"] = dict(c["evidence"], source="RETROSPECTIVE_HOLDOUT", as_of=L.holdout_start() + 3 * DAY,
                         as_of_utc="2026-10-20T00:00:00Z")
    if resha:
        c["card_sha"] = CAL.sha({k: v for k, v in c.items() if k != "card_sha"})
    return c


def test_x05_control_the_admissible_fixture_calibration_card_publishes(lab):
    w = TI.fixture_world(lab)
    s = _pass(lab, w, [TI.persist(TI.result("FXA", TI.M1, T_FX - 600), lab)])
    assert s["metrics"]["completed_forecasts"] == 1


def test_x05_spent_holdout_evidence_is_refused_when_a_calibration_card_is_built(lab):
    w = TI.fixture_world(lab)
    ev = {"status": "ADMISSIBLE", "rows": [], "fit_cutoff": L.holdout_start(), "cutoff": L.holdout_start() + 6 * DAY,
          "source": "RETROSPECTIVE_HOLDOUT"}
    with pytest.raises(CAL.CalibrationError, match="spent"):
        CAL.build_card(TI.T1, w["card"], [], L.holdout_start(), level="SHADOW", evidence=ev, is_fixture=True)


@pytest.mark.parametrize("resha", [True, False])
def test_x05_a_swapped_calibration_card_never_publishes_and_the_report_shows_no_number(lab, resha):
    w = TI.fixture_world(lab)
    bad = _forged(w, resha=resha)
    with pytest.raises(Exception):
        CAL.verify_card(bad)                                   # spent evidence (re-hashed) or a hash mismatch (not re-hashed)
    w2 = dict(w, extra={w["cal"]["card_sha"]: bad})           # served under the sha the registry recorded
    s = _pass(lab, w2, [TI.persist(TI.result("FXA", TI.M1, T_FX - 600), lab)])
    assert s["metrics"]["completed_forecasts"] == 0
    req = _lines(lab, "requests")[-1]
    assert all(t["calibrated_point"] is None for t in req["targets"])
    v, _ = _report(lab, w2)
    assert _numbers(v) == []


# ---------------------------------------------------------------- X06 a card trained on labels that had not matured by its cutoff
def _leaky_world(tmp, monkeypatch):
    real = B.fit_b2

    def leaky(target, train, cutoff, **kw):              # every training label matures five days after the card's cutoff (P05)
        return real(target, [B.Example(**{**e.__dict__, "label_matures_at": cutoff + 5 * DAY}) for e in train], cutoff, **kw)
    monkeypatch.setattr(B, "fit_b2", leaky)
    w = TI.fixture_world(tmp)
    monkeypatch.setattr(B, "fit_b2", real)
    return w


def test_x06_control_the_replay_guard_refuses_the_leaky_card(lab, monkeypatch):
    w = _leaky_world_pinned_by_hand(lab, monkeypatch)
    assert w["card"]["max_train_label_matures_at"] > w["card"]["training_cutoff"]
    with pytest.raises(E.TrainingAfterCutoff):
        E.check_card_time(w["card"], [T_FX])


def test_x06_the_registry_refuses_to_pin_the_leaky_card(lab, monkeypatch):                  # F20-06, CP20-1
    with pytest.raises(R.PinRefused, match=R.TRAINING_AFTER_CUTOFF):
        _leaky_world(lab, monkeypatch)


def _leaky_world_pinned_by_hand(tmp, monkeypatch):
    """The leaky champion pinned as an older registry or a hand-written log line would have pinned it (the pin check is skipped
    while the world is written); the serving path runs with the real code."""
    real = R.training_after_cutoff
    monkeypatch.setattr(R, "training_after_cutoff", lambda e: None)
    w = _leaky_world(tmp, monkeypatch)
    monkeypatch.setattr(R, "training_after_cutoff", real)
    return w


def test_x06_a_champion_card_whose_training_labels_matured_after_its_cutoff_never_publishes(lab, monkeypatch):
    w = _leaky_world_pinned_by_hand(lab, monkeypatch)
    assert any(x["state"] == R.TRAINING_AFTER_CUTOFF for x in R.status_at(w["b2"], T_FX))
    s = _pass(lab, w, [TI.persist(TI.result("FXA", TI.M1, T_FX - 600), lab)])
    assert s["metrics"]["completed_forecasts"] == 0
    req = _lines(lab, "requests")[-1]
    assert all(R.TRAINING_AFTER_CUTOFF in t["registry"]["blocking"] for t in req["targets"] if t["target"] == TI.T1)
    v, _ = _report(lab, w)
    assert _numbers(v) == []


def test_x06_control_the_fixture_champion_keeps_its_cutoff_and_is_pinned(lab):
    w = TI.fixture_world(lab)
    assert R.training_after_cutoff(w["b2"]) is None
    assert not any(x["state"] == R.TRAINING_AFTER_CUTOFF for x in R.status_at(w["b2"], T_FX))


def test_x06_a_training_decision_at_the_cutoff_is_refused_too():
    e = {"training_cutoff": 100.0, "training_cutoff_utc": "x", "max_train_decision_time": 100.0, "max_train_label_matures_at": 50.0}
    assert "P43" in R.training_after_cutoff(e)
    assert R.training_after_cutoff(dict(e, max_train_decision_time=99.0)) is None
    assert "P05" in R.training_after_cutoff(dict(e, max_train_decision_time=99.0, max_train_label_matures_at=100.5))


# ---------------------------------------------------------------- carried Phase 18 minor 5 (not one of the new scenarios)
def _forge_inside_interval(lines: dict) -> None:
    """A point moved inside its own interval, written into the document and into the request record's stored point, resealed."""
    for d in lines["documents"]:
        doc = d["document"]
        if doc["prediction_status"] == "FORECAST":
            doc["probability"] = round(doc["uncertainty_interval"][1] - 0.01, 6)
            for r in lines["requests"]:
                for t in r.get("targets") or []:
                    if t["forecast_id"] == doc["forecast_id"]:
                        t["calibrated_point"] = doc["probability"]
            return
    raise AssertionError("no FORECAST to forge")


def test_carried_control_a_point_moved_outside_the_wilson_band_is_already_refused(lab):
    d = TRP.world_forecast(lab)

    def outside(lines):
        _forge_inside_interval(lines)
        for x in lines["documents"]:
            if x["document"]["prediction_status"] == "FORECAST":
                x["document"]["uncertainty_interval"] = [x["document"]["probability"] - 0.001, x["document"]["probability"] + 0.001]
                for r in lines["requests"]:
                    for t in r.get("targets") or []:
                        if t["forecast_id"] == x["document"]["forecast_id"]:
                            t["interval"] = x["document"]["uncertainty_interval"]
    TRP.reseal(d["state_dir"], outside)
    v, _ = TRP.report(d)
    assert v["counts"]["probabilities_shown"] == 0


def test_carried_a_point_rewritten_in_the_document_and_the_request_record_is_refused(lab):     # F20-08, CP20-1
    d = TRP.world_forecast(lab)
    v0, _ = TRP.report(d)
    shown = [t["number"]["probability"] for o in v0["opportunities"] for t in o["targets"] if t["number"]]
    TRP.reseal(d["state_dir"], _forge_inside_interval)
    v, _ = TRP.report(d)
    forged = [t["number"]["probability"] for o in v["opportunities"] for t in o["targets"] if t["number"]]
    assert shown and forged == []


def _forge_raw(lines: dict) -> None:
    """The stored raw number moved (and nothing else): the card recomputes another raw number from the stored inputs."""
    for r in lines["requests"]:
        for t in r.get("targets") or []:
            if t.get("prediction_status") == "FORECAST":
                t["raw_number"] = round(float(t["raw_number"]) + 0.01, 9)
                return
    raise AssertionError("no FORECAST to forge")


def _forge_inputs(lines: dict) -> None:
    for r in lines["requests"]:
        for t in r.get("targets") or []:
            if t.get("prediction_status") == "FORECAST":
                k = sorted(k for k, v in t["inputs"].items() if v is not None)[0]
                t["inputs"][k] = float(t["inputs"][k]) + 1.0
                return
    raise AssertionError("no FORECAST to forge")


@pytest.mark.parametrize("forge", [_forge_raw, _forge_inputs])
def test_carried_a_stored_raw_number_or_input_that_the_card_does_not_reproduce_is_refused(lab, forge):
    d = TRP.world_forecast(lab)
    TRP.reseal(d["state_dir"], forge)
    v, _ = TRP.report(d)
    assert v["counts"]["probabilities_shown"] == 0


def test_carried_control_recompute_point_holds_on_the_unforged_forecast(lab):
    d = TRP.world_forecast(lab)
    v, _ = TRP.report(d)
    assert v["counts"]["probabilities_shown"] == 1
