"""Phase 18 skeptic attacks (independent reviewer). Run from a clone of feature/predictive-intelligence:

    cd <clone> && MEMELAB_DB=/tmp/x.sqlite python -m pytest -q -p no:cacheprovider \
        /home/claude/pi_orchestration/skeptic/PHASE_18_attacks.py --rootdir <clone>

Each test asserts what the code does today, so a passing test documents the behavior; the docstring says whether that
behavior is a finding. Temp folders only, fixed clocks, no network.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

CLONE = Path(os.environ.get("P18_CLONE", "/home/claude/pi_orchestration/skeptic_18"))
sys.path[:0] = [str(CLONE), str(CLONE / "tests")]

import pytest  # noqa: E402

from memelab import db  # noqa: E402
from memelab.predictive import integration as I  # noqa: E402
from memelab.predictive import reports as RP  # noqa: E402
import test_predictive_integration as TI  # noqa: E402
import test_predictive_reports as TR  # noqa: E402

DAY = 86400.0


@pytest.fixture
def lab(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "lab.sqlite")
    monkeypatch.setattr(db, "DATA_DIR", tmp_path / "data")
    (tmp_path / "data").mkdir()
    db.init_db()
    return tmp_path


def _alerts(d, tmp, now, name="al", fixture_run=True):
    out = RP.alert_run(d["state_dir"], config_path=d["config"], alert_db=tmp / name / "a.sqlite", now=now, fixture_run=fixture_run,
                       registry_dir=d["registry_dir"], extra_cal_cards=d["extra"], lab_db=d["lab_db"])
    return out


# ------------------------------------------------------------------------------------------------ A1
def test_a1_liquidity_collapse_does_not_override_an_optimistic_forecast(lab):
    """Prompt item 4: 'sudden liquidity/whale source risk flags override optimistic forecast and force warning'.
    Pass 1: a fixture SHADOW forecast (interval above base rate); an alert run consumes it. Pass 2, 13 hours later (past the 12 h
    reevaluate cooldown): the same token with liquidity down 33% (fresh inputs, no fatal flag) and the same optimistic forecast.
    Today the second alert run emits the risk_override warning AND an optimistic reevaluate notice for the same snapshot, and the
    report prints the FORECAST row with vetoes 'none' and no 'overridden'. FINDING if the asserts below pass."""
    d = TR.world_forecast(lab)
    w = d["world"]
    first = _alerts(d, lab, TI.T_FX + 60)
    assert first["outcome"] == "evaluated"
    T2 = TI.T_FX + 13 * 3600
    r2 = TI.persist(TI.result("FXA", TI.M1, T2 - 600, liq=100000.0, mcap=3.0e6, vol=3.0e5), lab)
    TR._pass([r2], T2, lab, **TI.fx_kw(w, lab, sleep=lambda s: None))
    v = RP.build(d["state_dir"], config_path=d["config"], lab_db=d["lab_db"], registry_dir=d["registry_dir"], extra_cal_cards=d["extra"])
    fxa = next(o for o in v["opportunities"] if o["mint"] == TI.M1)
    print("changes:", fxa["changes"], "veto:", fxa["execution"]["veto"])
    shown = [(t["short"], t["number"]["probability"], t["number"]["interval"], t["number"]["base_rate"]) for t in fxa["targets"] if t.get("number")]
    print("pass-2 numbers:", shown)
    text = RP.render(v)
    row = [ln for ln in text.splitlines() if TI.M1 in ln and ln.startswith("|")][0]
    print("at-a-glance row:", row)
    out = _alerts(d, lab, T2 + 60)
    import sqlite3
    con = sqlite3.connect(lab / "al" / "a.sqlite")
    p2 = fxa["ids"]["request_record_id"]
    got = []
    for (aj, rid) in con.execute("SELECT alert_json, run_id FROM alert_events"):
        a = json.loads(aj)
        tag = "pass-2" if a["request_record_id"] == p2 else "pass-1"
        print("alert run", rid, a["policy"], a["severity"], a["label"][:4], tag, "|", a["reason"][:110])
        if rid == out["run_id"]:
            got.append((a["policy"], tag))
    print("suppressed in run 2:", [(s["policy"], s["reason_code"]) for s in out["evaluation"]["suppressed"]])
    assert fxa["execution"]["veto"] is False and any(c.startswith("liquidity -") for c in fxa["changes"])
    assert shown and shown[0][2][0] > shown[0][3]
    assert "overridden" not in row and "| none |" in row
    assert ("risk_override", "pass-2") in got and ("reevaluate", "pass-2") in got


# ------------------------------------------------------------------------------------------------ A2
def _vanity(word: str) -> str:
    base = TI.b58("vanity")
    m = "2" + base[1:20] + word + base[20 + len(word):]
    I.S.check_address("solana", m)
    return m


def test_a2_an_uncovered_vanity_mint_with_a_digit_bounded_trading_word_breaks_the_whole_report(lab):
    """A not-attempted event (no lab decision row) whose exact mint contains '1profit2'. Only the opportunities' mints are removed
    before the trading-word check, so the not-attempted table makes `render` raise and no report is produced at all
    (fail-closed denial of the whole report by one token anyone can grind). FINDING (minor) if it raises."""
    m = _vanity("1profit2")
    T = TI.T_TODAY
    rs = [TI.persist(TI.result("ABC", TI.M1, T - 600), lab), TI.result("VAN", m, T - 600)]
    TR._pass(rs, T, lab)
    v = RP.build(lab / "state", config_path=TI.cfg(lab), lab_db=db.DB_PATH)
    assert any(r["mint"] == m for r in v["not_attempted"]), v["not_attempted"]
    with pytest.raises(RP.ReportError):
        RP.render(v)


# ------------------------------------------------------------------------------------------------ A3
def test_a3_consistent_reseal_of_document_and_request_point_shows_an_unrecomputed_number(lab):
    """CX-18 forges only the document's probability. An adversary who edits the document probability AND the request record's
    calibrated_point (raw_number untouched) and re-seals. reports.py compares to the stored point but never calls
    integration.verify_point, although its own 'Carried constraints' text says the number 'must equal the point recomputed from
    the raw number'. FINDING if the forged number is shown."""
    d = TR.world_forecast(lab)
    target = {}

    def mutate(lines):
        for dl in lines["documents"]:
            doc = dl["document"]
            if doc["prediction_status"] == "FORECAST" and doc["mint_address"] == TI.M1:
                lo, hi = doc["uncertainty_interval"]
                newp = round((lo + hi) / 2 + (hi - lo) * 0.3, 6)
                target.update(fid=doc["forecast_id"], old=doc["probability"], new=newp)
                doc["probability"] = newp
                break
        for r in lines["requests"]:
            for t in r.get("targets") or []:
                if t.get("forecast_id") == target["fid"]:
                    t["calibrated_point"] = target["new"]
    TR.reseal(d["state_dir"], mutate)
    v = RP.build(d["state_dir"], config_path=d["config"], lab_db=d["lab_db"], registry_dir=d["registry_dir"], extra_cal_cards=d["extra"])
    t = next(t for o in v["opportunities"] for t in o["targets"] if t["forecast_id"] == target["fid"])
    print("forged", target, "->", t["status"], t.get("number"), t.get("checks"))
    # independent recomputation with the Phase 17 verifier
    st = I.load_state(d["state_dir"])
    dl = st["documents"][target["fid"]]
    req = next(r for r in st["lines"]["requests"] if r.get("seq") == dl["request_seq"] and r["pass_id"] == dl["pass_id"])
    trec = next(x for x in req["targets"] if x["forecast_id"] == target["fid"])
    reg = I.load_registry(d["registry_dir"])
    card, cal, why = RP._resolve_cards(dl["document"], trec, reg, I.ROOT, d["extra"])
    from memelab.predictive import calibration as CAL
    recomputed = float(CAL.apply_calibrator(cal["calibrator"], [float(trec["raw_number"])])[0][0])
    print("recomputed from the untouched raw number:", recomputed)
    vp = [] if abs(recomputed - target["new"]) <= 1e-12 else ["point is not the recomputed one"]
    assert t["status"] == "FORECAST" and abs(t["number"]["probability"] - target["new"]) < 1e-12
    assert vp, "verify_point would refuse the forged point"


# ------------------------------------------------------------------------------------------------ A4
def test_a4_a_reset_state_sharing_the_alert_db_silently_evaluates_nothing(lab, tmp_path_factory):
    """Rule 11 records feed_sha256 = the pass record id but never compares it. State A has 3 passes; it is replaced by a new state
    (or a second state shares the alert database) with 1 pass that carries a fresh fatal flag (CANNOT_EXIT_5K). The next run is
    'evaluated' with 0 candidates: the risk warning is never produced and nothing says why. FINDING if the asserts pass."""
    T = TI.T_TODAY
    rs = [TI.persist(TI.result("ABC", TI.M1, T - 600), lab)]
    TR._pass(rs, T, lab)
    TR._pass([TI.persist(TI.result("ABC", TI.M1, T + 2 * 3600 - 600, price=2.0), lab)], T + 2 * 3600, lab)
    TR._pass([TI.persist(TI.result("ABC", TI.M1, T + 4 * 3600 - 600, price=4.0), lab)], T + 4 * 3600, lab)
    cfg = TI.cfg(lab)
    adb = lab / "al" / "a.sqlite"
    a1 = RP.alert_run(lab / "state", config_path=cfg, alert_db=adb, now=T + 4 * 3600 + 60)
    assert a1["outcome"] == "evaluated"
    # the state folder is reset (new sandbox, moved folder, or a second state on the same alert db)
    import shutil
    shutil.rmtree(lab / "state")
    r = TI.persist(TI.result("GOMOX", TI.M2, T + 6 * 3600 - 600, fatal=("CANNOT_EXIT_5K",), status="REJECTED", score=0), lab)
    TR._pass([r], T + 6 * 3600, lab)
    # control: a fresh alert db sees the warning
    ctl = RP.alert_run(lab / "state", config_path=cfg, alert_db=lab / "ctl" / "a.sqlite", now=T + 6 * 3600 + 60)
    assert [a["policy"] for a in ctl["evaluation"]["alerts"]] == ["risk_override"], ctl
    a2 = RP.alert_run(lab / "state", config_path=cfg, alert_db=adb, now=T + 6 * 3600 + 60)
    print("shared alert db after reset:", a2["outcome"], a2["evaluation"]["candidates"], a2.get("reason"))
    assert a2["outcome"] == "evaluated" and a2["evaluation"]["candidates"] == 0


# ------------------------------------------------------------------------------------------------ A5
def test_a5_a_clock_that_goes_back_keeps_alerts_too_soon_until_it_catches_up(lab):
    """A run at T+1 day, then the clock corrected to T: prev is chosen by started_at, now - prev < 0 < 60 min, so the run is
    'too_soon' (with a negative minute count) until the clock passes the bad run. MINOR."""
    d = TR.world_abstain(lab)
    adb = lab / "al" / "a.sqlite"
    a = RP.alert_run(d["state_dir"], config_path=d["config"], alert_db=adb, now=d["now"] + DAY)
    assert a["outcome"] == "evaluated"
    b = RP.alert_run(d["state_dir"], config_path=d["config"], alert_db=adb, now=d["now"])
    print(b["outcome"], b.get("reason"))
    assert b["outcome"] == "too_soon" and "-" in b["reason"]


# ------------------------------------------------------------------------------------------------ A6
def test_a6_liquidity_that_becomes_unknown_never_triggers_the_liquidity_rule(lab):
    """A rug where the vendor stops reporting liquidity: the change is 'liquidity became unknown', which `_liquidity_fall` does
    not read, so no risk_override fires on liquidity (only a fatal flag would). MINOR, depends on the lab's flags."""
    T = TI.T_TODAY
    TR._pass([TI.persist(TI.result("ABC", TI.M1, T - 600), lab)], T, lab)
    r = TI.persist(TI.result("ABC", TI.M1, T + 2 * 3600 - 600, liq=None), lab)
    TR._pass([r], T + 2 * 3600, lab)
    v = RP.build(lab / "state", config_path=TI.cfg(lab), lab_db=db.DB_PATH)
    o = v["opportunities"][0]
    print("changes:", o["changes"])
    out = RP.alert_run(lab / "state", config_path=TI.cfg(lab), alert_db=lab / "al" / "a.sqlite", now=T + 2 * 3600 + 60)
    print("alerts:", [a["policy"] for a in out["evaluation"]["alerts"]])
    assert "liquidity became unknown" in o["changes"]
    assert not any(a["policy"] == "risk_override" for a in out["evaluation"]["alerts"])


# ------------------------------------------------------------------------------------------------ A7
def test_a7_send_is_refused_before_anything_is_written(lab):
    d = TR.world_abstain(lab)
    with pytest.raises(RP.AlertRefused):
        RP.alert_run(d["state_dir"], config_path=d["config"], alert_db=lab / "al" / "a.sqlite", now=d["now"], send=True)
    assert not (lab / "al").exists()
    src = (CLONE / "memelab/predictive/reports.py").read_text()
    assert re.findall(r"AT\.(\w+)", src) and set(re.findall(r"AT\.(\w+)", src)) <= {"FileSink", "dest_ref"}


# ------------------------------------------------------------------------------------------------ A8
def test_a8_a_deferred_event_that_adds_a_fatal_flag_is_shown_as_covered_with_no_veto(lab):
    """Pass 1: token ABC attempted, no fatal flag. Pass 2: the pass budget (30 s) is exhausted before ABC, whose newest snapshot
    now carries CANNOT_EXIT_5K; ABC is DEFERRED_LATENCY_BUDGET. The report shows ABC from the older attempt with vetoes 'none';
    the not-attempted table says 'Covered by a report above: yes' with detail 'none' (nothing says the newer snapshot differs),
    and the alert run evaluates no request for it. FINDING if the asserts pass."""
    T = TI.T_TODAY
    TR._pass([TI.persist(TI.result("ABC", TI.M1, T - 600), lab)], T, lab)
    rs = [TI.persist(TI.result(f"Q{i}", TI.b58(f"q{i}"), T + 2 * 3600 - 600), lab) for i in range(3)]
    rs.append(TI.persist(TI.result("ABC", TI.M1, T + 2 * 3600 - 600, fatal=("CANNOT_EXIT_5K",), status="REJECTED", score=0), lab))
    tick = iter(range(0, 10_000, 11))
    TR._pass(rs, T + 2 * 3600, lab, clock=lambda: float(next(tick)))
    st = I.load_state(lab / "state")
    evs = [(r["event"], r["mint"] == TI.M1, r.get("changes")) for r in st["lines"]["requests"] if r["mint"] == TI.M1]
    print("ABC events:", evs)
    v = RP.build(lab / "state", config_path=TI.cfg(lab), lab_db=db.DB_PATH)
    text = RP.render(v)
    abc = next(o for o in v["opportunities"] if o["mint"] == TI.M1)
    rows = [ln for ln in text.splitlines() if TI.M1 in ln and ln.startswith("|")]
    for r_ in rows:
        print("row:", r_)
    out = RP.alert_run(lab / "state", config_path=TI.cfg(lab), alert_db=lab / "al" / "a.sqlite", now=T + 2 * 3600 + 60)
    print("alerts:", [(a["policy"], a["label"][:4]) for a in out["evaluation"]["alerts"]], "suppressed:",
          [(s["policy"], s["label"][:4], s["reason_code"]) for s in out["evaluation"]["suppressed"]])
    deferred = [e for e in evs if e[0].startswith("DEFERRED")]
    assert deferred                       # (the latency deferral is decided before the change list, so no change is recorded)
    assert abc["execution"]["veto"] is False
    assert any("DEFERRED" in r_ and "| yes |" in r_ and r_.rstrip().endswith("| none |") for r_ in rows)
    assert not any(a["label"].startswith("ABC") for a in out["evaluation"]["alerts"])


# ------------------------------------------------------------------------------------------------ A9 (the new counterexample)
def test_a9_concatenated_trade_words_in_a_symbol_reach_the_report_and_the_alert(lab):
    """CX-SK18: memecoin symbols are often run-together phrases. 'BUY-NOW' is withheld (the injection world tests it), but
    'SELLNOW', 'BUYNOW', 'TAKEPROFIT', 'APEIN' pass `integration._ident` (trading words are matched on word boundaries only) and
    the whole-report check (same boundaries), so the report's at-a-glance table, the section heading and the alert label print
    them. FINDING if the asserts pass."""
    T = TI.T_TODAY
    syms = ["SELLNOW", "BUYNOW", "TAKEPROFIT", "APEIN"]
    rs = [TI.persist(TI.result(s, TI.b58(f"cx{i}"), T - 600, fatal=("CANNOT_EXIT_5K",) if i == 0 else (),
                               status="REJECTED" if i == 0 else "WATCH"), lab) for i, s in enumerate(syms)]
    TR._pass(rs, T, lab)
    v = RP.build(lab / "state", config_path=TI.cfg(lab), lab_db=db.DB_PATH)
    text = RP.render(v)
    for s in syms:
        assert f"## {s} `solana:" in text and f"| {s} |" in text, s
    out = RP.alert_run(lab / "state", config_path=TI.cfg(lab), alert_db=lab / "al" / "a.sqlite", now=T + 60, lab_db=db.DB_PATH)
    txt = "".join(p.read_text() for p in sorted((lab / "al" / "outbox" / "preview").glob("alert_*.txt")))
    print(txt)
    assert "SELLNOW on solana" in txt and "WARNING: risk override" in txt
