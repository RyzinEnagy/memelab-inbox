"""Phase 20 skeptic: attacks on the CP20-1 repairs (PI-D-110) and a new cross-component counterexample.

Run from a scratch clone at the branch tip, offline:
    cd CLONE && MEMELAB_DB=/tmp/x.sqlite unshare -n python -B -m pytest -q -p no:cacheprovider -rA /path/p20_cp20_attacks.py

Each test asserts what the repair SHOULD do; a FAILED test is a defeat of the repair (a finding), a PASSED test means the
attack was refused. Fixtures of the repository's own tests are reused; inputs are this file's. No network, no vendor call.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(os.getcwd())
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tests" / "fixtures" / "predictive"))

import test_predictive_integration as TI  # noqa: E402
from memelab import db  # noqa: E402
from memelab.predictive import baselines as B  # noqa: E402
from memelab.predictive import evaluation as E  # noqa: E402
from memelab.predictive import integration as I  # noqa: E402
from memelab.predictive import registry as R  # noqa: E402

DAY = 86400.0
T_FX = TI.T_FX


@pytest.fixture
def lab(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "lab.sqlite")
    monkeypatch.setattr(db, "DATA_DIR", tmp_path / "data")
    (tmp_path / "data").mkdir()
    db.init_db()
    return tmp_path


def _lines(tmp, name, state="state"):
    p = tmp / state / I.FILES[name]
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


# ---------------------------------------------------------------- A1: TRAINING_ROWS_AFTER_CUTOFF with the maturity fields absent
def _leaky_world_without_fields(tmp, monkeypatch):
    """The X06 leak (every training label matures five days after the cutoff), and the card records no maximum training decision
    time or label maturity (None), as a card written by hand or by a fitter that does not record them would."""
    real = B.fit_b2

    def leaky(target, train, cutoff, **kw):
        card = real(target, [B.Example(**{**e.__dict__, "label_matures_at": cutoff + 5 * DAY}) for e in train], cutoff, **kw)
        card["max_train_decision_time"] = None
        card["max_train_label_matures_at"] = None
        card["model_sha"] = B.sha({k: v for k, v in card.items() if k != "model_sha"})
        return card
    monkeypatch.setattr(B, "fit_b2", leaky)
    w = TI.fixture_world(tmp)
    monkeypatch.setattr(B, "fit_b2", real)
    return w


def test_a1_a_leaky_card_without_maturity_fields_is_refused_at_pin(lab, monkeypatch):
    """Expected (fail closed): a champion card whose record gives no training maturity is not pinned. FAILED = fail open."""
    with pytest.raises(R.PinRefused):
        _leaky_world_without_fields(lab, monkeypatch)


def test_a1b_and_the_replay_guard_refuses_it_too():
    card = {"model_id": "x", "training_cutoff": 100.0, "training_cutoff_utc": "x", "n_train": 300,
            "max_train_decision_time": None, "max_train_label_matures_at": None}
    with pytest.raises(E.TrainingAfterCutoff):
        E.check_card_time(card, [200.0])


def test_a1c_a_leaky_card_without_fields_publishes_no_number(lab, monkeypatch):
    try:
        w = _leaky_world_without_fields(lab, monkeypatch)
    except R.PinRefused:
        return
    r = TI.persist(TI.result("FXA", TI.M1, T_FX - 600), lab)
    s = I.run_pass([r], capture_time=T_FX, lab_db=db.DB_PATH, state_dir=lab / "state", config_path=TI.cfg(lab), **TI.fx_kw(w, lab))
    assert s["metrics"]["completed_forecasts"] == 0, "a card trained on unmatured labels published a FORECAST"


# ---------------------------------------------------------------- A2: right mint, another mint's pool (the F20-02 path, other field)
def _replay(lab, w, token_of, state):
    r = TI.persist(TI.result("FXA", TI.M1, T_FX - 600), lab)
    con = sqlite3.connect(db.DB_PATH)
    con.row_factory = sqlite3.Row
    row = dict(con.execute("SELECT * FROM theses WHERE mint=? ORDER BY id DESC", (TI.M1,)).fetchone())
    own = dict(con.execute("SELECT * FROM tokens WHERE mint=?", (TI.M1,)).fetchone())
    con.close()
    token = token_of(own)
    reads = []

    def reader(pool, mint, T):
        reads.append(pool)
        return TI.candles_ok(pool, mint, T)
    s = I.run_pass([r], capture_time=T_FX, state_dir=lab / state, config_path=TI.cfg(lab),
                   decision_rows=[{"row": row, "token": token, "decision_time": T_FX, "basis": "EXPORT_COMMIT"}],
                   **TI.fx_kw(w, lab, reader=reader))
    return s, reads


def test_a2_a_token_row_with_the_right_mint_but_another_tokens_pool_is_refused(lab):
    """The export row keeps the mint but names POOL2 (another token's pool). Expected: refused like F20-02, POOL2 never read."""
    w = TI.fixture_world(lab)
    s, reads = _replay(lab, w, lambda own: dict(own, primary_pool=TI.POOL2), "st_pool")
    req = _lines(lab, "requests", "st_pool")[-1]
    assert TI.POOL2 not in reads, f"another token's pool was read: event {req['event']}, forecasts {s['metrics']['completed_forecasts']}"


def test_a2b_a_token_row_whose_mint_differs_only_by_case_is_refused(lab):
    w = TI.fixture_world(lab)
    s, reads = _replay(lab, w, lambda own: dict(own, mint=TI.M1.swapcase()), "st_case")
    req = _lines(lab, "requests", "st_case")[-1]
    assert req["event"] == "NOT_EXACT_IDENTITY" and reads == []


def test_a2c_a_token_row_without_a_mint_column_is_refused(lab):
    w = TI.fixture_world(lab)
    s, reads = _replay(lab, w, lambda own: {k: v for k, v in own.items() if k != "mint"}, "st_nomint")
    req = _lines(lab, "requests", "st_nomint")[-1]
    assert req["event"] == "NOT_EXACT_IDENTITY" and reads == []


# ---------------------------------------------------------------- A3: CAPTURE_TIME_REFUSED edges
@pytest.mark.parametrize("cap", [True, float("nan"), float("inf"), "1793000000", T_FX * 1000.0, 999_999_999.0, -T_FX, None])
def test_a3_a_capture_time_not_in_epoch_seconds_is_refused_visibly(lab, cap):
    w = TI.fixture_world(lab)
    r = TI.persist(TI.result("FXA", TI.M1, T_FX - 600), lab)
    s = I.run_pass([r], capture_time=cap, lab_db=db.DB_PATH, state_dir=lab / "state", config_path=TI.cfg(lab), **TI.fx_kw(w, lab))
    assert s["state"] == "CAPTURE_TIME_REFUSED" and not (lab / "state").exists()


def test_a3b_a_numpy_capture_time_in_seconds_is_accepted(lab):
    import numpy as np
    w = TI.fixture_world(lab)
    r = TI.persist(TI.result("FXA", TI.M1, T_FX - 600), lab)
    s = I.run_pass([r], capture_time=np.float64(T_FX), lab_db=db.DB_PATH, state_dir=lab / "state", config_path=TI.cfg(lab),
                   **TI.fx_kw(w, lab))
    assert s.get("state") != "CAPTURE_TIME_REFUSED", "a valid numpy float64 capture time is refused (fails closed, visible)"


def test_a3c_a_capture_time_before_the_observation_gives_no_number(lab):
    """The capture time is in seconds but 10 days before the result's observed_at (a clock set back). Expected: no FORECAST on
    inputs observed after the decision time."""
    w = TI.fixture_world(lab)
    r = TI.persist(TI.result("FXA", TI.M1, T_FX - 600), lab)
    s = I.run_pass([r], capture_time=T_FX - 10 * DAY, lab_db=db.DB_PATH, state_dir=lab / "state", config_path=TI.cfg(lab),
                   **TI.fx_kw(w, lab))
    assert s["metrics"]["completed_forecasts"] == 0


# ---------------------------------------------------------------- CX-SK20 (new): a run-together multiplier symbol reaches the
# Phase 18 report and its alert, and the Phase 17 scout section. The CX-SK18 repair withholds 100X, PUMP100X, MOON100X (a
# trading word or a bounded multiplier) but not 100XGAIN, 1000XGEM, GAIN100X, 10XPLAY: the multiplier regex needs a non-letter
# after the X. F20-01 states the report withholds 100XGAIN; P41 only tries SELLNOW in the scout section.
def test_cx_sk20_a_run_together_multiplier_symbol_is_withheld_in_report_alert_and_section(lab):
    import test_predictive_reports as TRP
    from memelab.predictive import reports as RP
    T = TI.T_TODAY
    syms = ["100XGAIN", "1000XGEM", "GAIN100X"]
    rs = [TI.persist(TI.result(s, TI.b58(f"sk20{i}"), T - 600, fatal=("CANNOT_EXIT_5K",) if i == 0 else (),
                               status="REJECTED" if i == 0 else "WATCH"), lab) for i, s in enumerate(syms)]
    TRP._pass(rs, T, lab)
    v = RP.build(lab / "state", config_path=TI.cfg(lab), lab_db=db.DB_PATH)
    text = RP.render(v)
    out = RP.alert_run(lab / "state", config_path=TI.cfg(lab), alert_db=lab / "al" / "a.sqlite", now=T + 60, lab_db=db.DB_PATH)
    alerts = "".join(p.read_text() for p in sorted((lab / "al" / "outbox" / "preview").glob("alert_*.txt")))
    sec = I.scout_section([TI.persist(TI.result("100XGAIN", TI.b58("sk20s"), T - 600), lab)], capture_time=T,
                          config_path=TI.cfg(lab), state_dir=lab / "state_sec", lab_db=db.DB_PATH) or ""
    shown = {s: (s in text, s in alerts) for s in syms}
    (lab.parent / "cx_sk20_shown.json").write_text(json.dumps({"report_alert": shown, "section": "100XGAIN" in sec,
                                                               "alert_lines": [x for x in alerts.splitlines() if "XG" in x or "100X" in x][:4]}))
    print(json.dumps({"report_alert": shown, "section": "100XGAIN" in sec,
                      "alert_lines": [x for x in alerts.splitlines() if "100X" in x or "1000X" in x][:4],
                      "report_lines": [x for x in text.splitlines() if "100X" in x or "1000X" in x][:4]}))
    assert not any(a or b for a, b in shown.values()) and "100XGAIN" not in sec
