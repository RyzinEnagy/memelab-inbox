"""Phase 17: integration-1 (memelab/predictive/integration.py), bt-adapter-1 (memelab/predictive/bt_adapter.py) and the hook in
memelab/cli.py. Pre-registration: audits/predictive-intelligence/phase_17/ACCEPTANCE_CHECKLIST.md (rules 1 to 17, G1 to G27).

Temp databases and folders only, fixed clocks, no network (an audit hook refuses sockets in every test of this file). Every
FORECAST here is a fixture: no real card is calibrated and no real champion exists."""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import io
import json
import math
import sqlite3
import subprocess
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import pytest

from memelab import cli, db, pipeline
from memelab.predictive import abstention as AB
from memelab.predictive import baselines as B
from memelab.predictive import bt_adapter as BT
from memelab.predictive import calibration as CAL
from memelab.predictive import contract as C
from memelab.predictive import decisions as D
from memelab.predictive import integration as I
from memelab.predictive import labels as L
from memelab.predictive import registry as R

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import test_predictive_registry as TR  # noqa: E402  (the Phase 16 fixture builders)

OLD_CLI = ROOT / "tests/fixtures/predictive/cli_before_phase17.py.txt"
OLD_CLI_SHA = "12f95f3af9bdb8f00b6974c27ee6ab2cb0341e6f2806d87ec9d565ef676b4348"     # b0fad12:memelab/cli.py
H = L.holdout_start()
P0 = CAL.PROSPECTIVE_START
DAY = 86400.0
T_TODAY = C.parse_utc("2026-10-27T08:00:00Z")
T_FX = P0 + 6 * DAY                                     # 2026-10-30T00:00Z: a fixture champion is current then
T1, T1B, T2 = L.T1, L.T1B, L.T2
_ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
SOCKETS: list[str] = []


def _hook(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto") and SOCKETS is not None and _ACTIVE[0]:
        SOCKETS.append(event)
        raise RuntimeError(f"no network in the Phase 17 tests ({event})")


_ACTIVE = [False]
sys.addaudithook(_hook)


@pytest.fixture(autouse=True)
def no_network():
    _ACTIVE[0] = True
    SOCKETS.clear()
    yield
    _ACTIVE[0] = False
    assert SOCKETS == []


def b58(seed: str) -> str:
    n = int.from_bytes(hashlib.sha256(seed.encode()).digest(), "big")
    s = ""
    while n:
        n, r = divmod(n, 58)
        s = _ALPH[r] + s
    return s


M1, M2, M3 = b58("m1"), b58("m2"), b58("m3")
POOL1, POOL2 = b58("pool1"), b58("pool2")


def result(sym: str, mint: str, t: float, *, score=60, status="WATCH", fatal=(), price=1.0, liq=49000.0, vol=1.0e5,
           mcap=1.0e6, pool=POOL1, chain="solana", first_pool_at="2026-10-25T00:00:00Z") -> dict:
    ident = {"symbol": sym, "name": sym, "primary_pool": pool, "decimals": 6, "token_program": "spl", "first_pool_at": first_pool_at}
    b = {"chain": chain, "observed_at": t, "identity": ident,
         "market": {"price_usd": price, "liquidity_usd_total": liq, "market_cap": mcap, "vol": {"24h": vol}},
         "pools": [], "quotes": {}, "authorities": {}, "trades": [], "social": {}, "sources": {}, "discrepancies": []}
    sc = {"total": score, "breakdown": {}, "fatal_flags": [{"flag": f, "evidence": "fx", "severity": "FATAL"} for f in fatal],
          "untradeable": bool(fatal), "unknown_count": 0, "unknown_buckets": []}
    st = {"status": status, "reasoning": "fixture"}
    mods = {"identity": {"confidence": "HIGH", "status": "OK"}, "lifecycle": {"stage": "fx", "confidence": "LOW"},
            "structure": {"structure": "fx"}, "depth": {}, "holders": {}, "early": {}, "breakout": {}, "attention": {}, "entries": {},
            "manipulation": {}}
    snap = {"t": t, "price": price, "mcap": mcap, "liquidity": liq, "vol_24h": vol, "score": score, "status": status, "fatal": list(fatal)}
    th = {"questions": {"IS SUPPLY BEING ACCUMULATED OR DISTRIBUTED?": "fixture", "WHAT INVALIDATES THE THESIS?": "fixture",
                        "WHY IS IT RECEIVING ATTENTION?": "fixture"}}
    return {"mint": mint, "bundle": b, "modules": mods, "ranker_inputs": {}, "score": sc, "status": st, "thesis": th,
            "snapshot": snap, "report_md": f"# {sym} fixture report\n", "unacceptable": []}


@pytest.fixture
def lab(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "lab.sqlite")
    monkeypatch.setattr(db, "DATA_DIR", tmp_path / "data")
    (tmp_path / "data").mkdir()
    db.init_db()
    return tmp_path


def persist(r: dict, tmp: Path) -> dict:
    p = pipeline.persist_result(r, tmp / "reports")
    r["report_path"] = str(p)
    return r


def cfg(tmp: Path, on: bool = True, **extra) -> Path:
    p = tmp / ("cfg_on.json" if on else "cfg_off.json")
    if on:
        p.write_text(json.dumps({"predictive": {"enabled": True, **extra}}))
    return p


def run(results, T, tmp, **kw):
    kw.setdefault("config_path", cfg(tmp))
    kw.setdefault("state_dir", tmp / "state")
    return I.run_pass(results, capture_time=T, lab_db=db.DB_PATH, **kw)


def lines(tmp, name, state="state"):
    p = tmp / state / I.FILES[name]
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


# ---------------------------------------------------------------- the fixture champion (TEST_ONLY)
def _ex(i, t, rng, y=None):
    x = {B.LIQ: float(rng.normal(10.8, 0.8)), B.MCAP: float(rng.normal(13.8, 0.8)), B.VOL: float(rng.normal(11.5, 1.0)),
         B.FATAL: float(rng.random() < 0.2), B.AGE: float(rng.normal(1.2, 0.4)), B.SCORE: float(rng.normal(55, 10))}
    if y is None:
        y = int(rng.random() < 1 / (1 + math.exp(-(1.1 * (x[B.LIQ] - 10.8) - 0.9))))
    return B.Example(decision_key=f"k{i}", chain="solana", mint=b58(f"w{i}"), decision_time=t, label_matures_at=t + DAY, y=y, x=x,
                     avail={c: t for c in x})


def fixture_world(tmp: Path, *, level="SHADOW"):
    rng = np.random.default_rng(17)
    train = [_ex(i, H - 40 * DAY + i * 3000.0, rng) for i in range(300)]
    card = B.fit_b2(T1, train, H)
    dev = [_ex(1000 + i, H - 12 * DAY + i * 2400.0, rng) for i in range(300)]
    p = B.predict(card, dev)[0]
    rows = [{"decision_key": e.decision_key, "mint": e.mint, "decision_time": e.decision_time, "label_matures_at": e.label_matures_at,
             "y": e.y, "score": float(s), "scored_by_cutoff": e.decision_time - 60.0, "split": "DEVELOPMENT"} for e, s in zip(dev, p)]
    ev_ex = [_ex(5000 + i, P0 + i * 1800.0, rng) for i in range(160)]
    pe = B.predict(card, ev_ex)[0]
    ev_rows = [{"decision_key": e.decision_key, "mint": e.mint, "decision_time": e.decision_time, "label_matures_at": e.label_matures_at,
                "y": e.y, "score": float(s), "scored_by_cutoff": H, "split": "PROSPECTIVE"} for e, s in zip(ev_ex, pe)]
    ev = {"status": "ADMISSIBLE", "rows": ev_rows, "fit_cutoff": H, "cutoff": P0 + 5 * DAY, "source": "PROSPECTIVE_HOLDOUT"}
    cal = CAL.build_card(T1, card, rows, H, level=level, evidence=ev, is_fixture=True)
    cdir = tmp / "cards"
    cdir.mkdir(exist_ok=True)
    cpath = cdir / "B2_T1.json"
    cpath.write_text(B.dumps(card))
    inf = {"probe_set": "synthetic", "probe_set_sha": "0" * 64, "rows": 1, "numbers": 1, "abstentions": {},
           "outputs_sha": R.inference_hash(I.probe_rows(card, ROOT)), "recorded_predictions_file": None,
           "recorded_predictions_sha256": None, "equal_to_recorded": True, "differences": 0}
    b2 = R.make_entry(target=T1, family={"phase": "07", "kind": "B2", "candidate": "P07_B2", "module_version": R.PHASE07_FAMILY_VERSION},
                      card=card, card_path=str(cpath), card_file_sha256=hashlib.sha256(cpath.read_bytes()).hexdigest(),
                      calibration={"path": None, "card_sha": cal["card_sha"], "file_sha256": "b" * 64, "status": cal["status"],
                                   "level": cal["level"], "details": []},
                      facts=TR.facts("B2", level="SHADOW"), evidence={"fixture": True}, risk_flags=["FIXTURE"], inference=inf,
                      registered_as_of_utc="2026-10-29T00:00:00Z", is_fixture=True, code=TR.code_for("07"))
    b0 = TR.make("07", "B0", TR.facts("B0"))
    ents = {b2["entry_id"]: b2, b0["entry_id"]: b0}
    refs = {"base_rate": b0["entry_id"], "simple_model": b2["entry_id"]}
    evs = [R.register_event(e, as_of_utc="2026-10-29T00:00:00Z") for e in (b0, b2)]
    evs.append(R.pin_event(ents, T1, mode="CHAMPION", champion=b2["entry_id"], references=refs, reasons=["FIXTURE_CHAMPION"],
                           as_of_utc="2026-10-29T00:00:00Z", allow_fixture=True))
    rdir = tmp / "registry"
    for e in ents.values():
        R.write_entry(rdir / "entries", e)
    R.append_events(rdir / "REGISTRY_LOG.jsonl", evs, expect_sha=None)
    return {"card": card, "cal": cal, "b2": b2, "b0": b0, "entries": ents, "refs": refs, "registry_dir": rdir,
            "extra": {cal["card_sha"]: cal}}


def candles_ok(pool, mint, T):
    end = (int(T) // 300) * 300 - 300                 # a candle that ended at least 300 s before T
    return [[end - 300 * i - 300, 1.0, 1.01, 0.99, 1.0, 1000.0] for i in range(6)]


def fx_kw(w, tmp, **kw):
    out = {"registry_dir": w["registry_dir"], "allow_fixture": True, "extra_cal_cards": w["extra"], "reader": candles_ok,
           "sleep": lambda s: None}
    out.update(kw)
    return out


def forecast_pass(tmp, w, rs=None, T=T_FX, **kw):
    rs = rs if rs is not None else [persist(result("FXA", M1, T - 600), tmp)]
    return run(rs, T, tmp, **fx_kw(w, tmp, **kw)), rs


# ---------------------------------------------------------------- G3: flag off, byte-identical (P40)
def _load_old_cli():
    text = OLD_CLI.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == OLD_CLI_SHA
    mod = types.ModuleType("memelab._cli_before_phase17")
    mod.__package__ = "memelab"
    mod.__file__ = str(ROOT / "memelab" / "cli.py")
    exec(compile(text, str(OLD_CLI), "exec"), mod.__dict__)
    return mod


class _A:
    def __init__(self, mints, **kw):
        self.__dict__.update({"mints": mints, "results": ["fx"], "stage1": None, "min_score": 55, "social": False,
                              "social_policy": None, "social_include_fixtures": False, "report_dir": None, **kw})


def _scout(module, monkeypatch, tmp, rs, T_obs):
    by = {}
    for r in rs:
        by.setdefault(r["mint"], []).append(r)
    monkeypatch.setattr(module, "_bodies", lambda ids: ({}, T_obs))
    monkeypatch.setattr(module, "_sol_price", lambda b: 150.0)

    def fake(mint, bodies, **k):
        r = copy.deepcopy(by[mint][0])
        return persist(r, Path(k["report_dir"]).parent)
    monkeypatch.setattr(pipeline, "analyze_token", fake)
    rd = tmp / "reports"
    rd.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    with redirect_stdout(buf):
        module.cmd_scout(_A([r["mint"] for r in rs], report_dir=str(rd)))
    rep = next(rd.glob("*_SCOUT.md")).read_text()
    return rep, buf.getvalue()


def _lab_dump(path):
    """The lab tables a scout writes, without the two wall-clock write times of the tokens table (db.now(), PI-D-011)."""
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    out = {}
    for t in ("tokens", "theses", "watchlist", "rejections", "entries"):
        out[t] = [{k: r[k] for k in r.keys() if not (t == "tokens" and k in ("first_seen_at", "last_seen_at"))}
                  for r in con.execute(f"SELECT * FROM {t} ORDER BY rowid")]
    con.close()
    return out


def _fresh_lab(tmp, monkeypatch, name):
    d = tmp / name
    (d / "data").mkdir(parents=True)
    monkeypatch.setattr(db, "DB_PATH", d / "lab.sqlite")
    monkeypatch.setattr(db, "DATA_DIR", d / "data")
    db.init_db()
    return d


def _three(T):
    return [result("AAA", M1, T - 600), result("BBB", M2, T - 600, fatal=("MINT_AUTHORITY_ACTIVE",), status="REJECTED", score=0),
            result("CCC", M3, T - 600, score=40, status="RESEARCH REQUIRED")]


def test_g3_flag_off_scout_report_and_stdout_are_byte_identical_to_the_pre_phase17_cli(tmp_path, monkeypatch):
    import shutil
    old = _load_old_cli()
    da = _fresh_lab(tmp_path, monkeypatch, "run")                     # the same folder for both runs: paths in the report are equal
    rep_old, out_old = _scout(old, monkeypatch, da, _three(T_TODAY), T_TODAY - 600)
    dump_old = _lab_dump(da / "lab.sqlite")
    files_old = {p.name: p.read_bytes() for p in (da / "reports").iterdir()}
    shutil.rmtree(da)
    dn = _fresh_lab(tmp_path, monkeypatch, "run")
    rep_new, out_new = _scout(cli, monkeypatch, dn, _three(T_TODAY), T_TODAY - 600)
    assert rep_new == rep_old and out_new == out_old
    assert _lab_dump(dn / "lab.sqlite") == dump_old
    assert not (dn / "data" / "private").exists()                     # the hook wrote nothing
    assert {p.name: p.read_bytes() for p in (dn / "reports").iterdir()} == files_old


def test_g3_flag_off_analyze_output_is_unchanged(lab, monkeypatch):
    r = result("AAA", M1, T_TODAY - 600)
    monkeypatch.setattr(cli, "_bodies", lambda ids: ({}, T_TODAY - 600))
    monkeypatch.setattr(pipeline, "analyze_token", lambda mint, bodies, **k: persist(copy.deepcopy(r), lab))

    class A:
        mint, results, stage1, account_size, max_loss_usd, max_loss_pct, position_usd, no_persist, print = M1, ["fx"], None, None, None, None, None, False, False
    buf = io.StringIO()
    with redirect_stdout(buf):
        cli.cmd_analyze(A())
    assert buf.getvalue().count("\n") == 1 and "predictive" not in buf.getvalue()
    (lab / "data" / "config.json").write_text(json.dumps({"predictive": {"enabled": True, "state_dir": str(lab / "st")}}))
    real = I.analyze_line
    monkeypatch.setattr(I, "analyze_line", lambda r, **k: real(r, capture_time=T_TODAY, **k))     # fixed clock
    buf = io.StringIO()
    with redirect_stdout(buf):
        cli.cmd_analyze(A())
    out = buf.getvalue().splitlines()
    assert len(out) == 2 and out[1].startswith("predictive: DISCOVERY ABSTAIN") and "research only" in out[1]


def test_p40_malformed_or_non_true_flag_is_off_and_writes_nothing(lab):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    for text in ("{not json", json.dumps({"predictive": {"enabled": "true"}}), json.dumps({"predictive": True}), json.dumps([1])):
        p = lab / "c.json"
        p.write_text(text)
        assert I.run_pass([r], capture_time=T_TODAY, lab_db=db.DB_PATH, config_path=p, state_dir=lab / "st") is None
        assert I.scout_section([r], config_path=p, state_dir=lab / "st") is None
        assert I.analyze_line(r, config_path=p, state_dir=lab / "st") is None
    assert not (lab / "st").exists()


# ---------------------------------------------------------------- G4: flag on, appended only, results untouched
def test_g4_flag_on_appends_a_section_and_changes_no_result_list_or_table(tmp_path, monkeypatch):
    import shutil
    doff = _fresh_lab(tmp_path, monkeypatch, "run")
    off, _ = _scout(cli, monkeypatch, doff, _three(T_TODAY), T_TODAY - 600)
    dump_off = _lab_dump(doff / "lab.sqlite")
    shutil.rmtree(doff)
    don = _fresh_lab(tmp_path, monkeypatch, "run")
    (don / "data" / "config.json").write_text(json.dumps({"predictive": {"enabled": True, "state_dir": str(don / "st")}}))
    seen = []
    real = I.scout_section

    def spy(results, **k):
        before = copy.deepcopy(results)
        out = real(results, capture_time=T_TODAY, **k)
        seen.append(before == results)
        return out
    monkeypatch.setattr(I, "scout_section", spy)
    on, _ = _scout(cli, monkeypatch, don, _three(T_TODAY), T_TODAY - 600)
    assert seen == [True]                                             # score, fatal flags, status, thesis, inputs untouched
    assert on.startswith(off) and on != off
    tail = on[len(off):]
    assert tail.startswith("\n## Predictive research section (flag on, research only)")
    assert _lab_dump(don / "lab.sqlite") == dump_off                   # watchlist, rejections, theses as without the flag
    assert "Fatal-flag veto: MINT_AUTHORITY_ACTIVE; no forecast clears it" in tail
    assert tail.count(": ABSTAIN (") == 9 and "FORECAST" not in tail.replace("FORECAST_", "")
    assert "BACKTEST_NOT_AVAILABLE" in tail and "NO_VIABLE_CHAMPION" in tail


# ---------------------------------------------------------------- G5, G6: exactly once, idempotent (P35)
def test_g5_every_trigger_gets_exactly_one_request_and_every_attempt_three_documents_with_records(lab):
    rs = [persist(r, lab) for r in _three(T_TODAY)]
    rs.append(result("NOROW", b58("norow"), T_TODAY - 600))           # not persisted: not a decision
    rs.append(dict(result("BAD", "not-a-mint", T_TODAY - 600)))
    s = run(rs, T_TODAY, lab)
    m = s["metrics"]
    assert m["events"] == 5 and m["attempted"] == 3 and m["documents"] == m["records"] == 9 and m["not_attempted"] == 2
    req, docs, recs = lines(lab, "requests"), lines(lab, "documents"), lines(lab, "records")
    assert [r["event"] for r in req] == ["DISCOVERY"] * 3 + ["NO_DECISION_SNAPSHOT", "NOT_EXACT_IDENTITY"]
    fids = [d["forecast_id"] for d in docs]
    assert len(set(fids)) == 9
    for d in docs:
        doc = d["document"]
        rec = next(r for r in recs if r["record_id"] == d["abstention_record_id"])
        assert I.check_document(doc, rec, config_path=cfg(lab)) == []
        assert doc["forecast_id"] == C.forecast_id(doc["chain"], doc["mint_address"], doc["snapshot_hash"], doc["target"],
                                                   doc["target_version"], doc["horizon_seconds"], doc["model_sha"])
    for r in req[:3]:
        assert {p["target"] for p in r["not_attempted_targets"]} == {t for t, v in C.TARGETS.items() if v["status"] != "PRIMARY"}
        assert all(p["reasons"] == ["TARGET_NOT_FEASIBLE"] for p in r["not_attempted_targets"])


def test_g5_snapshot_hash_is_the_row_sha_a_state_export_of_the_same_row_carries(lab):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    run([r], T_TODAY, lab)
    from memelab import state
    out = state.export(lab / "export.json")
    row = next(x for x in json.loads(out.read_text())["_tables"]["theses"] if x["mint"] == M1)
    doc = lines(lab, "documents")[0]["document"]
    rq = lines(lab, "requests")[0]
    assert rq["row_sha256"] == D.row_sha256(row)                       # PI-D-022: the value the export will carry, kept in the request
    cands = D.candidates([{"commit": "c", "commit_time": T_TODAY + 60, "theses": [row], "tokens": []}])
    assert cands[0]["row_sha256"] == rq["row_sha256"]
    assert doc["snapshot_hash"] == I.snapshot_sha(row) == D.row_sha256({k: v for k, v in row.items() if k != "report_path"})


def test_g6_the_same_snapshot_again_is_a_duplicate_with_no_new_document(lab):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    run([r], T_TODAY, lab)
    n = len(lines(lab, "documents"))
    s = run([r], T_TODAY + 30, lab)
    assert s["metrics"]["event_counts"] == {"DUPLICATE": 1} and s["metrics"]["documents"] == 0
    assert len(lines(lab, "documents")) == n
    req = lines(lab, "requests")[-1]
    assert req["covered_by"] == [d["forecast_id"] for d in lines(lab, "documents")]
    # a second identical persisted row (same content, new id) has the same snapshot hash: also a duplicate
    persist(result("AAA", M1, T_TODAY - 600), lab)
    assert run([r], T_TODAY + 60, lab)["metrics"]["event_counts"] == {"DUPLICATE": 1}


# ---------------------------------------------------------------- G7: the material-change gate
BASE_MAT = {"chain": "solana", "mint": M1, "pool": POOL1, "status": "WATCH", "fatal": [], "score": 60, "price": 1.0, "liquidity": 49000.0,
            "vol_24h": 1.0e5, "catalyst": None, "served": {"T1_24h": {"model_sha": None, "pin": "p"}}}


@pytest.mark.parametrize("change, material", [
    ({"price": 1.099}, False), ({"price": 1.10}, True), ({"price": 0.90}, True), ({"liquidity": 49000 * 1.19}, False),
    ({"liquidity": 49000 * 1.2}, True), ({"vol_24h": 1.49e5}, False), ({"vol_24h": 1.5e5}, True), ({"score": 64}, False),
    ({"score": 65}, True), ({"score": 55}, True), ({"status": "NEAR ENTRY"}, True), ({"fatal": ["LP_UNLOCKED"]}, True),
    ({"pool": POOL2}, True), ({"catalyst": "f" * 64}, True), ({"served": {"T1_24h": {"model_sha": "a" * 64, "pin": "p"}}}, True),
    ({"served": {"T1_24h": {"model_sha": None, "pin": "q"}}}, True), ({"price": None}, True), ({"score": None}, True),
])
def test_g7_each_material_trigger_and_each_non_trigger(change, material):
    cur = dict(BASE_MAT, **change)
    got = I.material_changes(BASE_MAT, 0.0, cur, 100.0)
    assert bool(got) is material, got


def test_g7_age_triggers_after_an_hour_and_unchanged_names_its_covering_forecasts(lab):
    assert I.material_changes(BASE_MAT, 0.0, BASE_MAT, 3599.0) == []
    assert I.material_changes(BASE_MAT, 0.0, BASE_MAT, 3600.0) == ["last attempt 3600 s ago"]
    r1 = persist(result("AAA", M1, T_TODAY - 600, price=1.0), lab)
    run([r1], T_TODAY, lab)
    fids = [d["forecast_id"] for d in lines(lab, "documents")]
    r2 = persist(result("AAA", M1, T_TODAY - 300, price=1.05), lab)        # +5%: below the 10% trigger
    s = run([r2], T_TODAY + 300, lab)
    assert s["metrics"]["event_counts"] == {"UNCHANGED": 1} and s["metrics"]["documents"] == 0
    rq = lines(lab, "requests")[-1]
    assert rq["covered_by"] == fids and rq["measured"][0] == "price +5.0%"
    r3 = persist(result("AAA", M1, T_TODAY - 200, price=1.12), lab)        # +12%: a new attempt
    s = run([r3], T_TODAY + 400, lab)
    assert s["metrics"]["event_counts"] == {"MATERIAL_CHANGE": 1} and s["metrics"]["documents"] == 3
    assert lines(lab, "requests")[-1]["changes"] == ["price +12.0%"]


# ---------------------------------------------------------------- G8: storms and the bounded queue (P35)
def test_g8_a_storm_of_updates_gives_one_attempt_per_mint_and_linear_work(lab, monkeypatch):
    mints = [b58(f"s{i}") for i in range(10)]
    rs = []
    for k in range(100):
        for i, m in enumerate(mints):
            rs.append(result(f"S{i}", m, T_TODAY - 1000 + k, price=1.0 + 0.001 * k))
    for r in rs:
        persist(r, lab)
    calls = {"serve": 0}
    real = R.serve

    def counting(*a, **k):
        calls["serve"] += 1
        return real(*a, **k)
    monkeypatch.setattr(R, "serve", counting)
    s = run(rs, T_TODAY, lab)
    m = s["metrics"]
    assert m["events"] == 1000 and m["attempted"] == 10 and m["superseded"] == 990 and m["documents"] == 30
    assert calls["serve"] == 30                                           # three targets per attempt, nothing pairwise
    req = lines(lab, "requests")
    kept = {r["mint"]: r["snapshot_hash"] for r in req if r["event"] == "DISCOVERY"}
    con = sqlite3.connect(db.DB_PATH)
    con.row_factory = sqlite3.Row
    newest = {m_: I.snapshot_sha(dict(con.execute("SELECT * FROM theses WHERE mint=? ORDER BY created_at DESC, id DESC LIMIT 1",
                                                (m_,)).fetchone())) for m_ in mints}
    con.close()
    assert kept == newest                                                 # the newest snapshot of each mint is the one attempted


def test_g8_more_than_64_new_mints_in_one_pass_defer_the_rest_visibly(lab):
    rs = [persist(result(f"Q{i}", b58(f"q{i}"), T_TODAY - 600), lab) for i in range(200)]
    s = run(rs, T_TODAY, lab)
    m = s["metrics"]
    assert m["attempted"] == 64 and m["event_counts"]["DEFERRED_QUEUE_FULL"] == 136 and m["documents"] == 192
    assert I.FROZEN["queue_max"] == 64


def test_g9_the_pass_budget_defers_events_reached_after_30_seconds(lab):
    rs = [persist(result(f"Q{i}", b58(f"q{i}"), T_TODAY - 600), lab) for i in range(5)]
    tick = iter(range(0, 10_000, 9))
    s = run(rs, T_TODAY, lab, clock=lambda: float(next(tick)))
    ev = s["metrics"]["event_counts"]
    assert ev.get("DEFERRED_LATENCY_BUDGET", 0) >= 1 and ev.get("DISCOVERY", 0) >= 1
    assert sum(ev.values()) == 5


# ---------------------------------------------------------------- G9: no network, the reader only through the guard (P48)
def test_g9_the_integration_module_has_no_network_import_and_the_real_pass_makes_no_call(lab):
    txt = (ROOT / "memelab/predictive/integration.py").read_text()
    for banned in ("import socket", "import urllib", "import requests", "import http", "import subprocess", "memelab.backtest"):
        assert banned not in txt, banned
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    s = run([r], T_TODAY, lab, reader=lambda *a: pytest.fail("no read without a champion"))
    assert s["metrics"]["reader_calls"] == 0


def test_g9_a_priced_reader_is_refused_before_any_call_and_the_breaker_opens_after_five_failures(tmp_path, lab):
    w = fixture_world(tmp_path)
    calls = []

    def priced(*a):
        calls.append(a)
        return candles_ok(*a)
    priced.cost_per_call = 0.01
    s, _ = forecast_pass(tmp_path, w, reader=priced)
    assert calls == [] and s["metrics"]["reader_states"] == {"COST_CAP_REACHED": 1}
    doc = lines(tmp_path, "documents")[0]["document"]
    assert doc["prediction_status"] == "ABSTAIN" and "SOURCE_STALE" in doc["abstain_reasons"]
    fails = []

    def broken(*a):
        fails.append(a)
        raise ConnectionError("down")
    rs = [persist(result(f"F{i}", b58(f"f{i}"), T_FX - 600), tmp_path) for i in range(8)]
    s = run(rs, T_FX, tmp_path, state_dir=tmp_path / "st2", **fx_kw(w, tmp_path, reader=broken))
    assert len(fails) == 5 and s["metrics"]["reader_states"] == {"CIRCUIT_OPEN": 3, "NETWORK_UNAVAILABLE": 5}
    assert s["metrics"]["completed_forecasts"] == 0


# ---------------------------------------------------------------- G10: outages are visible and never bullish (P47)
def test_g10_an_unreadable_or_tampered_registry_abstains_visibly(lab, tmp_path):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    s = run([r], T_TODAY, lab, registry_dir=tmp_path / "missing")
    assert s["registry"]["state"] == "REGISTRY_UNAVAILABLE" and s["metrics"]["completed_forecasts"] == 0
    assert all(t["registry"]["blocking"] == ["REGISTRY_UNAVAILABLE"] for t in lines(lab, "requests")[0]["targets"])
    assert "Model registry: REGISTRY_UNAVAILABLE" in I.render(s)
    bad = tmp_path / "badreg"
    (bad / "entries").mkdir(parents=True)
    src = ROOT / I.REGISTRY_DIR
    for p in (src / "entries").glob("*.json"):
        (bad / "entries" / p.name).write_text(p.read_text())
    log = (src / "REGISTRY_LOG.jsonl").read_text().splitlines()
    (bad / "REGISTRY_LOG.jsonl").write_text("\n".join(log[:5] + log[6:]) + "\n")      # one event dropped
    r2 = persist(result("BBB", M2, T_TODAY - 600), lab)
    s = run([r2], T_TODAY, lab, registry_dir=bad)
    assert s["registry"]["state"] == "REGISTRY_UNAVAILABLE" and "chain broken" in s["registry"]["detail"]


def test_g10_a_tampered_state_file_refuses_the_pass_and_writes_nothing(lab):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    run([r], T_TODAY, lab)
    p = lab / "state" / I.FILES["records"]
    text = p.read_text().splitlines()
    rec = json.loads(text[0])
    rec["reasons"] = ["MODEL_NOT_SELECTED"]                                   # a reason dropped, id kept
    p.write_text("\n".join([json.dumps(rec, sort_keys=True, separators=(",", ":"))] + text[1:]) + "\n")
    before = {f: (lab / "state" / f).read_bytes() for f in I.FILES.values() if (lab / "state" / f).exists()}
    r2 = persist(result("BBB", M2, T_TODAY - 600), lab)
    s = run([r2], T_TODAY + 10, lab)
    assert s["state"] == "STATE_TAMPERED" and "record id" in s["detail"]
    assert {f: (lab / "state" / f).read_bytes() for f in before} == before
    assert "State refused: STATE_TAMPERED" in I.render(s)
    # dropping a whole line keeps every id valid but breaks the file sha the last pass recorded
    run2 = lab / "state2"
    run([r], T_TODAY, lab, state_dir=run2)
    q = run2 / I.FILES["documents"]
    q.write_text("\n".join(q.read_text().splitlines()[1:]) + "\n")
    assert run([r2], T_TODAY + 10, lab, state_dir=run2)["state"] == "STATE_TAMPERED"


def test_g10_stale_inputs_abstain_as_source_stale_with_the_detail(lab):
    r = persist(result("OLD", M1, T_TODAY - 20 * DAY), lab)                    # the committed inbox bodies are this old
    s = run([r], T_TODAY, lab)
    req = lines(lab, "requests")[0]
    assert req["staleness"]["state"] == "INPUT_STALE" and req["eligibility"]["state"] == "INPUT_STALE"
    for rec in lines(lab, "records"):
        assert "SOURCE_STALE" in rec["reasons"]
        assert any(c["code"] == "SOURCE_GAP" and "INPUT_STALE" in c["detail"] for c in rec["conditions"])
    assert "Inputs: INPUT_STALE" in I.render(s)


def test_g10_stale_inputs_keep_a_fixture_champion_from_publishing(tmp_path, lab):
    w = fixture_world(tmp_path)
    r = persist(result("OLD", M1, T_FX - 3 * 3600), tmp_path)
    s, _ = forecast_pass(tmp_path, w, rs=[r])
    assert s["metrics"]["completed_forecasts"] == 0 and s["metrics"]["reader_calls"] == 0


def test_g10_a_missing_collector_and_missing_catalyst_tables_are_named(lab):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    con = sqlite3.connect(db.DB_PATH)
    con.execute("DROP TABLE catalyst_token_links")
    con.commit()
    con.close()
    s = run([r], T_TODAY, lab, depth_db=lab / "no_bt.sqlite")
    req = lines(lab, "requests")[0]
    assert s["depth"]["state"] == "COLLECTOR_NOT_AVAILABLE" and req["decision_support"]["size_cap"]["basis"] == "EXECUTION_DATA_MISSING"
    assert req["catalyst"]["source_status"] == "CATALYST_SOURCE_NOT_AVAILABLE"


def test_g10_a_reader_failure_with_a_champion_is_source_stale_never_a_forecast(tmp_path, lab):
    w = fixture_world(tmp_path)

    def broken(*a):
        raise TimeoutError("slow")
    s, rs = forecast_pass(tmp_path, w, reader=broken)
    doc = lines(tmp_path, "documents")[0]["document"]
    assert doc["prediction_status"] == "ABSTAIN" and "SOURCE_STALE" in doc["abstain_reasons"]
    _, serious, near, rejected = cli.scout_lists(rs, {}, 55)
    _, serious0, near0, rejected0 = cli.scout_lists(copy.deepcopy(rs), {}, 55)
    assert [x["mint"] for x in serious] == [x["mint"] for x in serious0] and near == near0 and rejected == rejected0


# ---------------------------------------------------------------- G11: today, on the committed registry
def test_g11_today_every_request_abstains_with_no_viable_champion_and_uncalibrated(lab):
    rs = [persist(r, lab) for r in _three(T_TODAY)]
    s = run(rs, T_TODAY, lab, mode="research")
    assert s["registry"]["state"] == "OK" and s["registry"]["entries"] == 69
    assert {v["mode"] for v in s["registry"]["targets"].values()} == {"NO_VIABLE_CHAMPION"}
    assert {v["status"] for v in s["calibration"].values()} == {"UNCALIBRATED"}
    for d in lines(lab, "documents"):
        doc = d["document"]
        assert doc["prediction_status"] == "ABSTAIN" and doc["probability"] is None and doc["model_id"] == "not_selected"
        assert {"MODEL_NOT_SELECTED", "UNCALIBRATED"} <= set(doc["abstain_reasons"])
        assert doc["backtest_status"] == "BACKTEST_NOT_AVAILABLE" and doc["backtest_assessment_ref"] is None
    for rq in lines(lab, "requests"):
        assert all(t["registry"]["mode"] == "NO_VIABLE_CHAMPION" and t["calibration_status_phase13"] == "UNCALIBRATED"
                   for t in rq["targets"])
    refs = lines(lab, "references")
    assert len(refs) == 18                                             # research mode: B0 and B2 per target per attempt, internal
    assert all(not R.is_document(x["reference_record"]) and x["reference_record"]["published"] is False for x in refs)


# ---------------------------------------------------------------- G12: backtesting adapter (TEST_ONLY)
def _assessment(**kw):
    a = {"request_key": "k" * 64, "chain": "solana", "mint": M1, "as_of": T_TODAY - 60, "engine_version": "bt-0.2.0", "tier": "SCENARIO_ONLY",
         "state": "PARTIAL_WITH_LIMITATIONS", "stress": {"decision": "RESEARCHABLE", "max_size": {"max_size_usd": 1000.0}}}
    a.update(kw)
    return a


def test_g12_backtesting_is_not_installed_here_and_every_document_says_so(lab):
    import importlib.util
    assert importlib.util.find_spec("memelab.backtest") is None and C.backtest_status() == "BACKTEST_NOT_AVAILABLE"
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    r["backtest_assessment"] = _assessment()
    run([r], T_TODAY, lab)
    rq = lines(lab, "requests")[0]
    assert rq["backtest"]["result"] == "ASSESSMENT_UNVERIFIED" and rq["backtest"]["verified"] is False
    assert all(d["document"]["backtest_assessment_ref"] is None and d["document"]["execution_stress_assessment_ref"] is None
               for d in lines(lab, "documents"))


@pytest.mark.parametrize("kw, why", [({"mint": M2}, "IDENTITY_MISMATCH"), ({"chain": "base"}, "IDENTITY_MISMATCH"),
                                     ({"as_of": T_TODAY + 1}, "AFTER_DECISION"), ({"state": "GREAT"}, "UNKNOWN_STATE"),
                                     ({"as_of": None}, "NO_AS_OF"), ({"stress": {"decision": "BUY"}}, "UNKNOWN_STRESS_DECISION")])
def test_g12_the_adapter_refuses_identity_time_and_vocabulary_problems(kw, why):
    got = BT.from_result({"backtest_assessment": _assessment(**kw)}, chain="solana", mint=M1, decision_time=T_TODAY,
                         installed_status="BACKTEST_NOT_AVAILABLE")
    assert got["result"] == "ASSESSMENT_REFUSED" and any(why in x for x in got["refusals"]) and got["veto"]["veto"] is None


@pytest.mark.parametrize("kw, veto", [({"state": "RISK_FATAL_FLAW"}, True), ({"stress": {"decision": "STRUCTURALLY_UNTRADEABLE"}}, True),
                                      ({"stress": {"decision": "NO_TRADE"}}, True), ({"flags": ["BT_STRUCTURALLY_UNTRADEABLE"]}, True),
                                      ({}, None)])
def test_g12_a_fatal_or_untradeable_assessment_is_a_veto_and_nothing_clears_one(kw, veto):
    got = BT.from_result({"backtest_assessment": _assessment(**kw)}, chain="solana", mint=M1, decision_time=T_TODAY,
                         installed_status="BACKTEST_NOT_AVAILABLE")
    assert got["veto"]["veto"] is veto
    assert BT.veto_of(None) == {"veto": None, "reasons": ["UNTESTED"]}


BT_DDL = """CREATE TABLE bt_assessments (id INTEGER PRIMARY KEY, request_key TEXT NOT NULL, chain TEXT NOT NULL, mint TEXT NOT NULL,
  snapshot_hash TEXT NOT NULL, engine_version TEXT NOT NULL, as_of REAL NOT NULL, stage TEXT NOT NULL CHECK (stage IN ('FAST','DEEP')),
  tier TEXT NOT NULL, state TEXT NOT NULL, result_json TEXT NOT NULL, result_hash TEXT NOT NULL, created_at REAL NOT NULL,
  UNIQUE(request_key, stage));"""


def test_g12_the_table_reader_is_read_only_takes_the_newest_assessment_at_or_before_the_decision_and_checks_the_schema(tmp_path):
    p = tmp_path / "bt.sqlite"
    con = sqlite3.connect(p)
    con.executescript(BT_DDL)
    for i, (t, st) in enumerate(((T_TODAY - 600, "PARTIAL_WITH_LIMITATIONS"), (T_TODAY - 60, "RISK_FATAL_FLAW"), (T_TODAY + 60, "COMPLETE"))):
        a = _assessment(request_key=f"{i}" * 64, as_of=t, state=st)
        con.execute("INSERT INTO bt_assessments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (i + 1, a["request_key"], "solana", M1, "s", "bt-0.2.0", t, "FAST", "SCENARIO_ONLY", st, json.dumps(a), "h", t))
    con.execute("INSERT INTO bt_assessments VALUES (9,'x','solana',?, 's','e',?, 'FAST','SCENARIO_ONLY','COMPLETE','{}','h',0)",
                (M1.lower(), T_TODAY - 10))                                   # another identity (case differs)
    con.commit()
    con.close()
    before = p.read_bytes()
    got = BT.from_table(p, chain="solana", mint=M1, decision_time=T_TODAY, installed_status="BACKTEST_NOT_AVAILABLE")
    assert got["assessment"]["state"] == "RISK_FATAL_FLAW" and got["veto"]["veto"] is True
    assert p.read_bytes() == before
    with pytest.raises(sqlite3.OperationalError):
        BT.connect_ro(p).execute("INSERT INTO bt_assessments(request_key) VALUES ('z')")
    con = sqlite3.connect(p)
    con.execute("ALTER TABLE bt_assessments ADD COLUMN extra TEXT")
    con.commit()
    con.close()
    got = BT.from_table(p, chain="solana", mint=M1, decision_time=T_TODAY, installed_status="BACKTEST_NOT_AVAILABLE")
    assert got["result"] == "ASSESSMENT_REFUSED" and "SCHEMA_MISMATCH" in got["refusals"]
    assert BT.from_table(None, chain="solana", mint=M1, decision_time=T_TODAY,
                         installed_status="BACKTEST_NOT_AVAILABLE")["result"] == "BACKTEST_NOT_AVAILABLE"


def test_g12_the_adapter_imports_nothing_from_the_backtesting_branch():
    txt = (ROOT / "memelab/predictive/bt_adapter.py").read_text()
    imps = _imports(ROOT / "memelab/predictive/bt_adapter.py")
    assert imps <= {"__future__", "json", "math", "sqlite3", "pathlib", "typing"}, imps
    assert "import memelab.backtest" not in txt and "from memelab.backtest" not in txt and "from ..backtest" not in txt


# ---------------------------------------------------------------- the fixture FORECAST path (TEST_ONLY)
def test_g16_a_fixture_champion_publishes_one_recomputable_forecast_beside_the_veto(tmp_path, lab):
    w = fixture_world(tmp_path)
    s, _ = forecast_pass(tmp_path, w)
    m = s["metrics"]
    assert m["attempted"] == 1 and m["completed_forecasts"] == 1 and m["abstained"] == 2 and m["reader_calls"] == 1
    docs = lines(tmp_path, "documents")
    fd = next(d["document"] for d in docs if d["document"]["target"] == T1)
    assert fd["prediction_status"] == "FORECAST" and fd["is_fixture"] is True and 0.01 <= fd["probability"] <= 0.99
    assert fd["model_sha"] == w["card"]["model_sha"] and AB.NEW_MINT_CAVEAT in fd["caveats"]
    rq = lines(tmp_path, "requests")[0]
    t1 = next(t for t in rq["targets"] if t["target"] == T1)
    assert _fin_(t1["raw_number"]) and t1["calibration_card_sha"] == w["cal"]["card_sha"] and t1["inputs"][B.LIQ] == pytest.approx(math.log1p(49000.0))
    assert rq["features"]["availability_mode"] == "capture" and rq["features"]["scope"] == "CAPTURE_SINGLE_ROW"
    assert rq["eligibility"]["state"] == "ELIGIBLE"
    for d in docs:
        if d["document"]["target"] != T1:
            assert d["document"]["prediction_status"] == "ABSTAIN" and "MODEL_NOT_SELECTED" in d["document"]["abstain_reasons"]
    text = I.render(s)
    assert "FORECAST; record" in text and "Research estimate (SHADOW), not advice" in text


def _fin_(x):
    return isinstance(x, float) and math.isfinite(x)


def test_g13_a_fatal_flag_and_a_lost_route_stay_vetoes_beside_a_forecast(tmp_path, lab):
    w = fixture_world(tmp_path)
    p = tmp_path / "depth.sqlite"
    con = sqlite3.connect(p)
    con.executescript((ROOT / "tests/fixtures/predictive/bt_depth_schema_v2.sql").read_text())
    con.execute("INSERT INTO bt_schema_migrations VALUES (1,'v1','x',0)")
    con.execute("INSERT INTO bt_schema_migrations VALUES (2,'forward depth collector','y',0)")
    con.execute("INSERT INTO bt_depth_decisions VALUES (1,'solana',?,?,'EXPORT_PRIMARY_POOL','c',?,NULL,?, 'r','WATCH',?, 'h1')",
                (M1, POOL1, T_FX - 7200, T_FX - 7300, T_FX - 7200))
    for i, (pool, size, state, out) in enumerate(((POOL1, 1000.0, "NO_ROUTE", None), (POOL2, 1000.0, "OK", 999.0))):
        con.execute("INSERT INTO bt_depth_snapshots (id, run_id, decision_id, chain, mint, pool_address, kind, provider, size_usd, "
                    "captured_at, state, out_usd, recorded_at, content_hash) VALUES (?, 'r', 1, 'solana', ?, ?, 'QUOTE', 'jup', ?, ?, ?, ?, ?, ?)",
                    (i + 1, M1, pool, size, T_FX - 1800, state, out, T_FX - 1800, f"c{i}"))
    con.commit()
    con.close()
    r = persist(result("FAT", M1, T_FX - 600, fatal=("MINT_AUTHORITY_ACTIVE",), status="REJECTED", score=0), tmp_path)
    s, rs = forecast_pass(tmp_path, w, rs=[r], depth_db=p)
    rq = lines(tmp_path, "requests")[0]
    sup = rq["decision_support"]
    assert sup["veto"] is True and sup["structural_veto"]["flags"] == ["MINT_AUTHORITY_ACTIVE"] and sup["position_usd_from_forecast"] is None
    assert sup["size_cap"]["basis"] == "EXECUTION_DATA_MISSING" and sup["size_cap"]["route_lost_sizes"] == [1000.0]   # P02: POOL2 ignored
    fd = next(d["document"] for d in lines(tmp_path, "documents") if d["document"]["target"] == T1)
    assert fd["prediction_status"] == "FORECAST" and fd["position_usd"] is None
    _, serious, near, rejected = cli.scout_lists(rs, {}, 55)
    assert serious == [] and [x["mint"] for x in rejected] == [M1]          # the lab's override wins; the forecast is research
    assert "Fatal-flag veto: MINT_AUTHORITY_ACTIVE; no forecast clears it" in I.render(s)
    r2 = persist(result("BTV", M2, T_FX - 600), tmp_path)
    r2["backtest_assessment"] = _assessment(mint=M2, as_of=T_FX - 60, stress={"decision": "STRUCTURALLY_UNTRADEABLE"})
    s2 = run([r2], T_FX, tmp_path, state_dir=tmp_path / "st_bt", **fx_kw(w, tmp_path))
    rq2 = lines(tmp_path, "requests", "st_bt")[0]
    assert rq2["decision_support"]["veto"] is True and rq2["decision_support"]["backtest_veto"]["veto"] is True
    assert "Backtest veto: stress STRUCTURALLY_UNTRADEABLE; no forecast clears it" in I.render(s2)


def test_g14_phase13_m3_a_forged_point_inside_the_interval_is_refused_by_verify_point(tmp_path, lab):
    w = fixture_world(tmp_path)
    forecast_pass(tmp_path, w)
    d = next(x for x in lines(tmp_path, "documents") if x["document"]["target"] == T1)
    doc = d["document"]
    rec = next(x for x in lines(tmp_path, "records") if x["record_id"] == d["abstention_record_id"])
    rq = lines(tmp_path, "requests")[0]
    t1 = next(t for t in rq["targets"] if t["target"] == T1)
    lo, hi = doc["uncertainty_interval"]
    forged = dict(doc, probability=round((doc["probability"] + hi) / 2, 6))
    assert lo <= forged["probability"] <= hi and forged["probability"] != doc["probability"]
    kw = dict(model_card=w["card"], calibration_card=w["cal"], record=rec, backtest="BACKTEST_NOT_AVAILABLE", config_path=cfg(tmp_path))
    assert AB.validate_publication(forged, **kw) == []                      # what Phase 13 left open: the validator alone accepts it
    req = {"chain": "solana", "mint": M1, "target": T1, "decision_time": T_FX, "decision_time_basis": "CAPTURE_TIME",
           "snapshot_hash": doc["snapshot_hash"], "flag_on": True, "pool_point_in_time": True, "route": "PIT_RECORDED",
           "eligibility": "ELIGIBLE", "position_usd": None, "backtest_required": False,
           "x": {k: (float("nan") if v is None else v) for k, v in t1["inputs"].items()},
           "avail": {k: T_FX for k in t1["inputs"]}, "feature_set_sha": w["card"]["feature_set_sha"], "new_mint": True, "token_history_rows": 0}
    vp = dict(req=req, card=w["card"], level="SHADOW", cal_card=w["cal"], config_path=cfg(tmp_path))
    assert I.verify_point(doc, t1, **vp) == []
    assert any("not the recomputed" in e for e in I.verify_point(forged, t1, **vp))
    wide = dict(doc, uncertainty_interval=[max(0.0, lo - 0.05), min(1.0, hi + 0.05)])
    assert AB.validate_publication(wide, **kw) == [] and any("interval" in e for e in I.verify_point(wide, t1, **vp))
    assert I.verify_point(doc, dict(t1, raw_number=None), **vp) and I.verify_point(doc, dict(t1, calibration_card_sha="0" * 64), **vp)


def test_g15_phase13_m4_a_document_never_travels_without_its_record(lab):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    run([r], T_TODAY, lab)
    d = lines(lab, "documents")[0]
    doc = d["document"]
    rec = next(x for x in lines(lab, "records") if x["record_id"] == d["abstention_record_id"])
    assert AB.validate_publication(doc, model_card=None, calibration_card=None, record=None, config_path=cfg(lab)) == []
    assert I.check_document(doc, None, config_path=cfg(lab)) == ["a document without its persisted abstention record is never shown (Phase 13 m4)"]
    dropped = dict(doc, abstain_reasons=doc["abstain_reasons"][:1])
    assert I.check_document(dropped, rec, config_path=cfg(lab))
    assert "the document's reasons differ from its record" in I.pair_errors(dropped, rec)      # without validate_publication too
    other = next(x for x in lines(lab, "records") if x["record_id"] != rec["record_id"])
    assert "record of another forecast" in I.check_document(doc, other, config_path=cfg(lab))
    assert I.check_state(lab / "state", config_path=cfg(lab)) == {"documents": 3, "problems": []}


def test_g15_the_section_takes_reasons_and_explanations_from_the_record(lab):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    s = run([r], T_TODAY, lab)
    ev = s["events"][0]
    ev["records"][0] = dict(ev["records"][0], reasons=["UNCALIBRATED"],
                            conditions=[{"code": "NO_CALIBRATOR", "reason": "UNCALIBRATED", "detail": "", "explanation": "from the record"}])
    text = I.render(s)
    assert "ABSTAIN (UNCALIBRATED); record" in text and "from the record" in text


# ---------------------------------------------------------------- G16: the full fixture path through the real hook
def test_g16_end_to_end_through_the_scout_command_with_a_fixture_champion(tmp_path, monkeypatch):
    w = fixture_world(tmp_path)
    d = _fresh_lab(tmp_path, monkeypatch, "e2e")
    (d / "data" / "config.json").write_text(json.dumps({"predictive": {"enabled": True, "state_dir": str(d / "st")}}))
    real = I.scout_section
    monkeypatch.setattr(I, "scout_section", lambda results, **k: real(results, capture_time=T_FX, **fx_kw(w, tmp_path), **k))
    rep, _ = _scout(cli, monkeypatch, d, [result("E2E", M1, T_FX - 600)], T_FX - 600)
    rq = json.loads((d / "st" / I.FILES["requests"]).read_text().splitlines()[0])
    docs = [json.loads(x) for x in (d / "st" / I.FILES["documents"]).read_text().splitlines()]
    assert rq["event"] == "DISCOVERY" and rq["features"]["feature_version"] == "2" and len(docs) == 3
    assert rq["report_refs"]["token_report"].endswith("_E2E_" + M1[:6] + ".md") and rq["report_refs"]["scout_report"].endswith("_SCOUT.md")
    for x in docs:
        assert x["abstention_record_id"][:12] in rep
    assert rq["report_refs"]["token_report"] in rep
    assert I.check_state(d / "st", config_path=d / "data" / "config.json")["problems"] == []


# ---------------------------------------------------------------- G18: identity (P01, P02, P15)
def test_g18_the_same_symbol_on_two_mints_is_never_joined(lab):
    a = persist(result("TWIN", M1, T_TODAY - 600), lab)
    b = persist(result("TWIN", M2, T_TODAY - 600, price=7.0), lab)
    s = run([a, b], T_TODAY, lab)
    assert s["metrics"]["attempted"] == 2
    req = lines(lab, "requests")
    assert {r["mint"] for r in req} == {M1, M2} and req[0]["snapshot_hash"] != req[1]["snapshot_hash"]
    c = persist(result("TWIN", M2, T_TODAY - 300, price=7.0), lab)       # M2 again: UNCHANGED against M2's own attempt only
    assert run([c], T_TODAY + 60, lab)["metrics"]["event_counts"] == {"UNCHANGED": 1}


def _catalyst(con, eid, key, mint, link_type, strength, t, chain="solana", status="NEW"):
    con.execute("INSERT OR IGNORE INTO catalyst_events(id, event_key, category, title, discovered_at, retrieved_at, evidence_status, "
                "status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)", (eid, key, "CULTURAL", "invented event", t, t, "REPORTED", status, t, t))
    con.execute("INSERT INTO catalyst_token_links(event_id, mint, chain, link_type, link_strength, linked_at) VALUES (?,?,?,?,?,?)",
                (eid, mint, chain, link_type, strength, t))


def test_g18_only_exact_address_links_count_and_one_event_counts_once(lab):
    con = sqlite3.connect(db.DB_PATH)
    _catalyst(con, 1, "ev-1", M1, "TICKER_MATCH", "MODERATE", T_TODAY - 900)
    _catalyst(con, 2, "ev-2", M1.lower(), "NAMED_IN_SOURCE", "STRONG", T_TODAY - 900)      # another identity byte for byte
    con.commit()
    st = I.catalyst_state(con, "solana", M1, T_TODAY)
    assert st["fingerprint"] is None and st["exact_events"] == 0 and st["context_links"] == 1
    _catalyst(con, 3, "ev-3", M1, "NAMED_IN_SOURCE", "STRONG", T_TODAY - 900)
    _catalyst(con, 3, "ev-3", M2, "OFFICIAL", "STRONG", T_TODAY - 900)
    con.commit()
    st = I.catalyst_state(con, "solana", M1, T_TODAY)
    assert st["exact_events"] == 1
    con.execute("INSERT INTO catalyst_events(id, event_key, category, title, discovered_at, retrieved_at, evidence_status, status, created_at, "
                "updated_at) VALUES (4, 'ev-3-syndicated', 'CULTURAL', 'invented', ?, ?, 'REPORTED', 'NEW', ?, ?)", (T_TODAY + 10,) * 4)
    _catalyst(con, 5, "ev-5", M1, "OFFICIAL", "STRONG", T_TODAY - 900, chain="base")
    con.commit()
    _catalyst(con, 7, "ev-7", M1, "NAMED_IN_SOURCE", "STRONG", T_TODAY + 60)               # discovered and linked after T
    _catalyst(con, 8, "ev-8", M2, "NAMED_IN_SOURCE", "STRONG", T_TODAY - 900)              # discovered before T ...
    con.execute("INSERT INTO catalyst_token_links(event_id, mint, chain, link_type, link_strength, linked_at) VALUES (8, ?, 'solana', "
                "'NAMED_IN_SOURCE', 'STRONG', ?)", (M1, T_TODAY + 60))           # ... but linked to this mint only after T
    con.execute("INSERT INTO catalyst_token_links(event_id, mint, chain, link_type, link_strength, linked_at) VALUES (4, ?, 'solana', "
                "'OFFICIAL', 'STRONG', ?)", (M1, T_TODAY - 900))                  # linked before T to an event discovered after T
    con.commit()
    assert I.catalyst_state(con, "solana", M1, T_TODAY) == st                   # later links, later events, another chain: none enter
    assert I.catalyst_state(con, "solana", M1, T_TODAY + 100)["exact_events"] == 4
    con.close()


def test_g18_a_catalyst_change_is_material_and_the_catalyst_pass_requests_a_refresh_once(lab):
    r1 = persist(result("AAA", M1, T_TODAY - 600), lab)
    run([r1], T_TODAY, lab)
    con = sqlite3.connect(db.DB_PATH)
    _catalyst(con, 1, "ev-1", M1, "TICKER_MATCH", "MODERATE", T_TODAY + 100)
    _catalyst(con, 2, "ev-2", M1, "NAMED_IN_SOURCE", "STRONG", T_TODAY + 100)
    _catalyst(con, 3, "ev-3", M3, "NAMED_IN_SOURCE", "STRONG", T_TODAY + 100)
    con.commit()
    con.close()
    out = I.catalyst_pass(lab_db=db.DB_PATH, state_dir=lab / "state", now=T_TODAY + 200, config_path=cfg(lab))
    acts = {(a["mint"], a["event_key"]): a for a in out["actions"]}
    assert acts[(M1, "ev-2")]["action"] == "REFRESH_REQUESTED" and out["refresh_requested"] == 1
    assert acts[(M1, "ev-1")]["action"] == "IGNORED" and "UNVERIFIED_CATALYST" in acts[(M1, "ev-1")]["reason"]
    assert acts[(M3, "ev-3")]["action"] == "IGNORED" and "NO_DECISION_SNAPSHOT" in acts[(M3, "ev-3")]["reason"]
    n_docs = len(lines(lab, "documents"))
    again = I.catalyst_pass(lab_db=db.DB_PATH, state_dir=lab / "state", now=T_TODAY + 300, config_path=cfg(lab))
    assert again["refresh_requested"] == 0 and len(lines(lab, "documents")) == n_docs
    r2 = persist(result("AAA", M1, T_TODAY + 200), lab)                       # same market values, catalyst fingerprint changed
    s = run([r2], T_TODAY + 400, lab)
    assert s["metrics"]["event_counts"] == {"MATERIAL_CHANGE": 1} and lines(lab, "requests")[-1]["changes"] == ["catalyst changed"]


def test_g18_a_catalyst_source_outage_requests_nothing(lab):
    con = sqlite3.connect(db.DB_PATH)
    con.execute("DROP TABLE catalyst_token_links")
    con.commit()
    con.close()
    out = I.catalyst_pass(lab_db=db.DB_PATH, state_dir=lab / "state", now=T_TODAY, config_path=cfg(lab))
    assert out["state"] == "CATALYST_SOURCE_NOT_AVAILABLE" and out["actions"] == []
    assert I.catalyst_pass(lab_db=db.DB_PATH, state_dir=lab / "state", now=T_TODAY, config_path=lab / "absent.json") is None


# ---------------------------------------------------------------- G19: drift and staleness (P39)
def test_g19_a_drift_alarm_degrades_a_fixture_forecast_and_earlier_records_are_never_rewritten(tmp_path, lab):
    w = fixture_world(tmp_path)
    forecast_pass(tmp_path, w)
    before = {f: (tmp_path / "state" / f).read_text() for f in I.FILES.values() if (tmp_path / "state" / f).exists()}
    r2 = persist(result("FXA", M1, T_FX + 3000, price=1.5), tmp_path)
    s = run([r2], T_FX + 3600, tmp_path, **fx_kw(w, tmp_path, drift_alarms=[T_FX + 1000]))
    assert s["metrics"]["completed_forecasts"] == 0
    rq = lines(tmp_path, "requests")[-1]
    t1 = next(t for t in rq["targets"] if t["target"] == T1)
    assert "DRIFT_ALERT" in t1["registry"]["blocking"] and t1["model_id"] == "not_selected"
    for f, old in before.items():
        assert (tmp_path / "state" / f).read_text().startswith(old)


def test_g19_a_stale_model_after_the_frozen_age_is_not_served(tmp_path, lab):
    w = fixture_world(tmp_path)
    T = C.parse_utc("2026-10-31T00:00:01Z")
    r = persist(result("FXA", M1, T - 600), tmp_path)
    s = run([r], T, tmp_path, **fx_kw(w, tmp_path))
    assert s["metrics"]["completed_forecasts"] == 0
    t1 = next(t for t in lines(tmp_path, "requests")[0]["targets"] if t["target"] == T1)
    assert "MODEL_STALE" in t1["registry"]["blocking"]


# ---------------------------------------------------------------- G27: CX-17, a cache reused across a pin change
def test_cx17_a_rollback_makes_an_unchanged_snapshot_material_so_the_withdrawn_forecast_is_not_kept(tmp_path, lab):
    w = fixture_world(tmp_path)
    forecast_pass(tmp_path, w)
    assert lines(tmp_path, "documents")[0]["document"]["prediction_status"] == "FORECAST"
    evs = R.read_log((w["registry_dir"] / "REGISTRY_LOG.jsonl").read_text())
    rb = R.rollback_event(evs, w["entries"], T1, reason="FIXTURE_ROLLBACK", as_of_utc=AB._iso(T_FX + 60), usable=lambda e: False,
                          allow_fixture=True)
    R.append_events(w["registry_dir"] / "REGISTRY_LOG.jsonl", [rb], expect_sha=R.file_sha(w["registry_dir"] / "REGISTRY_LOG.jsonl"))
    r2 = persist(result("FXA", M1, T_FX - 500), tmp_path)                    # the same content one minute later
    s = run([r2], T_FX + 120, tmp_path, **fx_kw(w, tmp_path))
    assert s["metrics"]["event_counts"] == {"MATERIAL_CHANGE": 1} and lines(tmp_path, "requests")[-1]["changes"] == ["served changed"]
    new = [d["document"] for d in lines(tmp_path, "documents")][-3:]
    assert all(d["prediction_status"] == "ABSTAIN" and d["model_id"] == "not_selected" for d in new)
    assert "FORECAST" not in I.render(s).replace("FORECAST_", "")


# ---------------------------------------------------------------- G20: ops metrics and the CLI
def test_g20_the_cli_prints_metrics_checks_the_state_and_runs_a_catalyst_pass(lab):
    rs = [persist(r, lab) for r in _three(T_TODAY)]
    run(rs, T_TODAY, lab)
    run(rs, T_TODAY + 10, lab)
    base = [sys.executable, "-m", "memelab.predictive.integration"]
    out = subprocess.run(base + ["status", "--state-dir", str(lab / "state"), "--config", str(cfg(lab))], cwd=ROOT,
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    m = json.loads(out.stdout)["metrics"]
    assert m["events"] == 6 and m["attempted"] == 3 and m["duplicates"] == 3 and m["documents"] == 9 and m["abstained"] == 9
    assert m["models_in_use"] == ["not_selected"] and m["completed_forecasts"] == 0 and m["passes"] == 2
    chk = subprocess.run(base + ["check", "--state-dir", str(lab / "state"), "--config", str(cfg(lab))], cwd=ROOT, capture_output=True, text=True)
    assert chk.returncode == 0 and json.loads(chk.stdout) == {"documents": 9, "problems": []}
    cp = subprocess.run(base + ["catalyst-pass", "--state-dir", str(lab / "state"), "--config", str(cfg(lab)), "--lab-db", str(db.DB_PATH),
                                "--now", str(T_TODAY + 20)], cwd=ROOT, capture_output=True, text=True)
    assert cp.returncode == 0 and json.loads(cp.stdout)["state"] == "OK"
    p = lab / "state" / I.FILES["documents"]
    p.write_text(p.read_text() + "{}\n")
    bad = subprocess.run(base + ["status", "--state-dir", str(lab / "state")], cwd=ROOT, capture_output=True, text=True)
    assert bad.returncode == 2 and json.loads(bad.stdout)["state"] == "STATE_TAMPERED"


def test_g20_the_section_and_line_carry_the_metrics_and_no_trading_word(lab):
    rs = [persist(r, lab) for r in _three(T_TODAY)]
    text = I.scout_section(rs, capture_time=T_TODAY, config_path=cfg(lab), state_dir=lab / "state", lab_db=db.DB_PATH,
                           stage2={"rejected_stage2": [{"mint": "x"}]})
    assert "- Counts: 3 events, 3 attempted, 0 published, 9 abstentions" in text and "latency p50" in text
    assert "Stage-2 structural rejects (1) are not decisions" in text
    assert I._plain_ok(text.replace(M1, "").replace(M2, "").replace(M3, ""))
    with pytest.raises(I.IntegrationError):
        I.render({"state": "OK", "events": [{"symbol": "x", "chain": "solana", "mint": "m", "snapshot_hash": "s", "event": "buy now"}]})


# ---------------------------------------------------------------- G21: isolation seams
def _imports(p: Path) -> set[str]:
    out = set()
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n, ast.Import):
            out.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            out.add(("." * n.level) + (n.module or ""))
    return out


def test_g21_integration_imports_only_the_standard_library_and_the_named_package_modules():
    got = _imports(ROOT / "memelab/predictive/integration.py")
    std = {"__future__", "hashlib", "json", "math", "sqlite3", "sys", "time", "pathlib", "typing", "argparse", "re", "..", "..db"}
    assert got <= std | {"."}, got
    tree = ast.parse((ROOT / "memelab/predictive/integration.py").read_text())
    rel = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level == 1 for a in n.names}
    assert rel == {"abstention", "baselines", "bt_adapter", "calibration", "contract", "decisions", "depth_adapter", "features",
                   "labels", "onchain", "registry", "runtime", "store"}, rel
    up = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level == 2 for a in n.names}
    assert up <= {"db", "DATA_DIR"}, up
    txt = (ROOT / "memelab/predictive/integration.py").read_text()
    for name in ("evaluation", "technical", "analog", "behavioral", "scenario_eval"):
        assert f"import {name}" not in txt and f"predictive.{name}" not in txt


def test_g21_only_the_two_cli_helpers_import_the_integration_lazily():
    importers = {}
    for p in (ROOT / "memelab").rglob("*.py"):
        if p.name in ("integration.py",):
            continue
        tree = ast.parse(p.read_text())
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and any(a.name == "integration" for a in n.names) and (n.module or "").endswith("predictive"):
                importers.setdefault(str(p.relative_to(ROOT)), []).append(n)
            if isinstance(n, ast.ImportFrom) and (n.module or "").endswith("integration"):
                importers.setdefault(str(p.relative_to(ROOT)), []).append(n)
    assert list(importers) == ["memelab/cli.py"] and len(importers["memelab/cli.py"]) == 2
    tree = ast.parse((ROOT / "memelab/cli.py").read_text())
    funcs = {f.name: f for f in tree.body if isinstance(f, ast.FunctionDef)}
    for name in ("_predictive_section", "_predictive_line"):
        assert any(isinstance(n, ast.ImportFrom) and n.module == "predictive" for n in ast.walk(funcs[name]))
    top = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert not any("predictive" in (getattr(n, "module", "") or "") for n in top)


def test_g2_cli_differs_from_the_pre_phase17_copy_only_by_the_hook():
    import difflib
    old = OLD_CLI.read_text().splitlines()
    new = (ROOT / "memelab/cli.py").read_text().splitlines()
    added = [l[1:] for l in difflib.unified_diff(old, new, lineterm="", n=0) if l.startswith("+") and not l.startswith("+++")]
    removed = [l for l in difflib.unified_diff(old, new, lineterm="", n=0) if l.startswith("-") and not l.startswith("---")]
    assert removed == []
    assert len(added) == 42 and sum("_predictive" in l for l in added) == 7
    body = "\n".join(added)
    for w in ("score", "status", "watchlist", "serious", "rejected", "near"):
        assert f"{w} =" not in body and f"{w}[" not in body


# ---------------------------------------------------------------- G22: frozen modules and registry code files unchanged
def test_g22_every_registry_entry_still_sees_its_code_files_unchanged():
    reg = I.load_registry(ROOT / I.REGISTRY_DIR)
    assert reg["state"] == "OK"
    assert all(R.code_changes(e, ROOT) == [] for e in reg["entries"].values())


# ---------------------------------------------------------------- research mode, references and the append-only files
def test_research_mode_scores_references_internally_and_documents_stay_abstentions(lab):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    run([r], T_TODAY, lab, mode="research")
    refs = lines(lab, "references")
    assert {x["reference"] for x in refs} == {"base_rate", "simple_model"} and len(refs) == 6
    nums = [x["reference_record"]["raw_number"] for x in refs]
    assert all(n is None or 0.0 <= n <= 1.0 for n in nums)
    assert all(x["reference_record"]["purpose"] == "PROSPECTIVE_COMPARISON_ONLY_NEVER_A_FORECAST" for x in refs)
    rq = lines(lab, "requests")[0]
    assert rq["features"]["feature_version"] == "2" and rq["features"]["source_status"]["state-export"] == "OK"
    assert all(t["raw_number"] is None for t in rq["targets"])            # no champion: no model number for any target


def test_every_pass_only_appends(lab):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    run([r], T_TODAY, lab)
    old = {f: (lab / "state" / f).read_text() for f in I.FILES.values() if (lab / "state" / f).exists()}
    r2 = persist(result("AAA", M1, T_TODAY + 4000, price=2.0), lab)
    run([r2], T_TODAY + 5000, lab)
    for f, t in old.items():
        assert (lab / "state" / f).read_text().startswith(t)
    ps = lines(lab, "passes")
    assert [p["seq"] for p in ps] == [0, 1] and ps[1]["prev"] == ps[0]["record_id"]


def test_a_failing_component_is_a_visible_error_event_never_an_exception(lab, monkeypatch):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)

    def boom(*a, **k):
        raise RuntimeError("injected")
    monkeypatch.setattr(I.AB, "forecast_result", boom)
    s = run([r], T_TODAY, lab)
    assert s["metrics"]["event_counts"] == {"ERROR": 1} and "injected" in lines(lab, "requests")[0]["errors"][0]
    monkeypatch.setattr(I, "run_pass", boom)
    text = I.scout_section([r], capture_time=T_TODAY, config_path=cfg(lab), state_dir=lab / "state", lab_db=db.DB_PATH)
    assert "Failed: RuntimeError" in text and "the report above is unchanged" in text


def test_frozen_constants_are_the_preregistered_ones():
    f = I.FROZEN
    assert f["queue_max"] == 64 and f["per_mint_per_pass"] == 1 and f["pass_budget_s"] == 30.0 and f["stale_input_s"] == 7200.0
    assert f["material"] == {"score_abs": 5, "price_rel": 0.10, "liquidity_rel": 0.20, "volume_rel": 0.50, "max_age_s": 3600.0}
    assert f["catalyst"] == {"link_types": ["OFFICIAL", "NAMED_IN_SOURCE"], "strength": "STRONG", "refresh_min_interval_s": 3600.0}
    assert f["decision_support"] == {"max_loss": 0.05, "max_age_s": 3600.0}
    assert f["reads_per_request"] == 1 and f["reader_timeout_s"] == 10.0 and f["calls_per_minute"] == 6 and f["calls_per_pass"] == 64
    assert f["breaker_failures"] == 5 and f["cost_cap_usd"] == 0.0
    assert C.registry_sha256().startswith("4b4aabce")


# ---------------------------------------------------------------- added before the freeze (own review)
def test_the_gate_compares_with_the_last_attempt_at_or_before_the_capture_so_a_replay_is_idempotent(lab):
    r1 = persist(result("AAA", M1, T_TODAY - 600, price=1.0), lab)
    r2 = persist(result("AAA", M1, T_TODAY + 7000, price=1.03), lab)
    run([r2], T_TODAY + 7200, lab)                                        # the later one first (a replay out of order)
    s = run([r1], T_TODAY, lab)
    assert s["metrics"]["event_counts"] == {"DISCOVERY": 1}               # nothing earlier than T_TODAY: a first attempt as of then
    s = run([persist(result("AAA", M1, T_TODAY + 100, price=1.01), lab)], T_TODAY + 300, lab)
    assert s["metrics"]["event_counts"] == {"UNCHANGED": 1}
    assert lines(lab, "requests")[-1]["covered_by"] == [t["forecast_id"] for t in lines(lab, "requests")[1]["targets"]]


def test_a_result_without_a_chain_is_not_an_exact_identity_no_default_chain(lab):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    r2 = copy.deepcopy(r)
    del r2["bundle"]["chain"]
    s = run([r2], T_TODAY, lab)
    assert s["metrics"]["event_counts"] == {"NOT_EXACT_IDENTITY": 1}


def test_the_pass_never_writes_the_lab_database(lab):
    rs = [persist(r, lab) for r in _three(T_TODAY)]
    before = Path(db.DB_PATH).read_bytes()
    run(rs, T_TODAY, lab, mode="research")
    assert Path(db.DB_PATH).read_bytes() == before
    with pytest.raises(sqlite3.OperationalError):
        I.connect_lab_ro(db.DB_PATH).execute("DELETE FROM theses")


def test_a_row_that_differs_from_its_result_is_an_error_not_an_attempt(lab):
    r = persist(result("AAA", M1, T_TODAY - 600, score=60), lab)
    r2 = copy.deepcopy(r)
    r2["score"]["total"] = 61
    s = run([r2], T_TODAY, lab)
    assert s["metrics"]["event_counts"] == {"ERROR": 1} and "differs from the result" in lines(lab, "requests")[0]["errors"][0]


def test_analyze_without_a_persisted_row_says_no_decision_snapshot(lab):
    r = result("AAA", M1, T_TODAY - 600)
    line = I.analyze_line(r, capture_time=T_TODAY, config_path=cfg(lab), state_dir=lab / "state", lab_db=db.DB_PATH)
    assert line.startswith("predictive: NO_DECISION_SNAPSHOT") and "research only" in line


def test_capture_features_are_the_phase05_features_of_the_same_row(lab):
    from memelab.predictive import features as F
    from memelab.predictive import store as S
    r = persist(result("AAA", M1, T_TODAY - 600, liq=12345.0, vol=678.0, mcap=9.0e5, fatal=("LP_UNLOCKED",)), lab)
    con = I.connect_lab_ro(db.DB_PATH)
    row, tok, n, _ = I.decision_row(con, M1, T_TODAY - 600)
    con.close()
    got = I.capture_features(row, tok, "solana", M1, T_TODAY)
    sc = S.connect(":memory:")
    S.ingest_exports(sc, [{"commit": "c1", "commit_time": T_TODAY, "theses": [row], "tokens": [tok]}], now=T_TODAY)
    snap = F.features_as_of(sc, "solana", M1, T_TODAY, F.FEATURE_VERSION, mode="capture")
    vals = {v["feature_name"]: v["value"] for v in snap["values"]}
    assert got["x"][B.LIQ] == pytest.approx(vals[B.LIQ]) == pytest.approx(math.log1p(12345.0))
    assert got["x"][B.FATAL] == 1.0 and got["x"][B.VOL] == pytest.approx(math.log1p(678.0))
    assert got["x"][B.AGE] == pytest.approx(math.log1p((T_TODAY - C.parse_utc("2026-10-25T00:00:00Z")) / DAY))
    assert all(v <= T_TODAY for v in got["avail"].values()) and got["summary"]["feature_set_sha"] == F.feature_set_sha()


def test_two_rows_sharing_a_key_use_the_one_just_persisted(lab):
    r1 = persist(result("AAA", M1, T_TODAY - 600, score=60), lab)
    con = sqlite3.connect(db.DB_PATH)
    con.execute("UPDATE theses SET thesis_text = 'an older row of the same key' WHERE mint=?", (M1,))
    con.commit()
    con.close()
    persist(result("AAA", M1, T_TODAY - 600, score=60), lab)                # the newest id: the row the pipeline just wrote
    run([r1], T_TODAY, lab)
    rq = lines(lab, "requests")[0]
    con = sqlite3.connect(db.DB_PATH)
    con.row_factory = sqlite3.Row
    newest = dict(con.execute("SELECT * FROM theses WHERE mint=? ORDER BY id DESC LIMIT 1", (M1,)).fetchone())
    con.close()
    assert rq["snapshot_hash"] == I.snapshot_sha(newest) and rq["row_sha256"] == D.row_sha256(newest) and rq["rows_sharing_key"] == 2


def test_a_capture_before_the_row_existed_is_an_error(lab):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    s = run([r], T_TODAY - 601, lab)
    assert s["metrics"]["event_counts"] == {"ERROR": 1} and "before the row" in lines(lab, "requests")[0]["errors"][0]


def test_a_slow_reader_is_a_source_gap(tmp_path, lab):
    w = fixture_world(tmp_path)
    tick = {"t": 0.0}

    def clock():
        return tick["t"]

    def slow(*a):
        tick["t"] += 11.0                                                  # over the frozen 10 s
        return candles_ok(*a)
    s, _ = forecast_pass(tmp_path, w, reader=slow, clock=clock)
    rq = lines(tmp_path, "requests")[0]
    assert rq["eligibility"]["state"] == "VENDOR_OR_ROUTE_GAP" and "over 10.0 s" in rq["eligibility"]["detail"]
    assert s["metrics"]["completed_forecasts"] == 0


def test_a_fixture_champion_is_never_served_outside_a_fixture_run(tmp_path, lab):
    w = fixture_world(tmp_path)
    r = persist(result("FXA", M1, T_FX - 600), tmp_path)
    s = run([r], T_FX, tmp_path, **fx_kw(w, tmp_path, allow_fixture=False))
    t1 = next(t for t in lines(tmp_path, "requests")[0]["targets"] if t["target"] == T1)
    assert s["metrics"]["completed_forecasts"] == 0 and "FIXTURE_IN_REAL_REGISTRY" in t1["registry"]["blocking"]


def test_an_export_commit_decision_is_not_judged_stale_by_its_created_at(lab):
    r = persist(result("AAA", M1, T_TODAY - 3 * DAY), lab)
    con = I.connect_lab_ro(db.DB_PATH)
    row, tok, n, e = I.decision_row(con, M1, T_TODAY - 3 * DAY)
    con.close()
    s = run([r], T_TODAY, lab, decision_rows=[{"row": row, "token": tok, "decision_time": T_TODAY - 3 * DAY + 3 * 3600,
                                               "basis": "EXPORT_COMMIT", "earlier": 0, "sharing": 1}])
    rq = lines(lab, "requests")[0]
    assert rq["decision_time_basis"] == "EXPORT_COMMIT" and rq["staleness"]["state"] == "FRESH" and rq["event"] == "DISCOVERY"
    assert all(d["document"]["decision_time_basis"] == "EXPORT_COMMIT" for d in lines(lab, "documents"))


def test_the_catalyst_pass_is_rate_limited_per_mint_and_never_requests_twice_for_one_event(lab):
    r1 = persist(result("AAA", M1, T_TODAY - 600), lab)
    run([r1], T_TODAY, lab)
    con = sqlite3.connect(db.DB_PATH)
    _catalyst(con, 2, "ev-2", M1, "NAMED_IN_SOURCE", "STRONG", T_TODAY + 100)
    con.commit()
    assert I.catalyst_pass(lab_db=db.DB_PATH, state_dir=lab / "state", now=T_TODAY + 200, config_path=cfg(lab))["refresh_requested"] == 1
    _catalyst(con, 6, "ev-6", M1, "OFFICIAL", "STRONG", T_TODAY + 300)
    con.commit()
    con.close()
    out = I.catalyst_pass(lab_db=db.DB_PATH, state_dir=lab / "state", now=T_TODAY + 400, config_path=cfg(lab))
    assert out["refresh_requested"] == 0 and any("rate limited" in a["reason"] for a in out["actions"] if a.get("event_key") == "ev-6")
    later = I.catalyst_pass(lab_db=db.DB_PATH, state_dir=lab / "state", now=T_TODAY + 2 * 3600, config_path=cfg(lab))
    acts = {a["event_key"]: a for a in later["actions"]}
    assert later["refresh_requested"] == 1 and acts["ev-6"]["action"] == "REFRESH_REQUESTED"
    assert acts["ev-2"]["action"] == "IGNORED" and "duplicate" in acts["ev-2"]["reason"]


def test_a_dropped_pass_line_breaks_the_pass_chain(lab):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    run([r], T_TODAY, lab)
    run([persist(result("BBB", M2, T_TODAY - 500), lab)], T_TODAY + 10, lab)
    p = lab / "state" / I.FILES["passes"]
    p.write_text("\n".join(p.read_text().splitlines()[1:]) + "\n")
    s = run([persist(result("CCC", M3, T_TODAY - 400), lab)], T_TODAY + 20, lab)
    assert s["state"] == "STATE_TAMPERED" and "chain broken" in s["detail"]


# ---------------------------------------------------------------- CP17-0 (PI-D-094): self-review pass 2, each fails on 3d2089b
def test_cp17_0_a_state_directory_inside_the_repository_but_outside_data_private_is_refused(lab):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    for rel in ("data/state/p17_must_not_exist", "inbox/p17_must_not_exist", "p17_must_not_exist"):
        target = ROOT / rel
        assert not target.exists()
        s = run([r], T_TODAY, lab, state_dir=target)
        assert s["state"] == "STATE_DIR_REFUSED" and not target.exists(), rel
        assert "State refused: STATE_DIR_REFUSED" in I.render(s)
    assert I.state_dir_refusal(ROOT / "data/private/predictive") is None and I.state_dir_refusal(lab / "state") is None
    line = I.analyze_line(r, capture_time=T_TODAY, config_path=cfg(lab), state_dir=ROOT / "state/p17_x", lab_db=db.DB_PATH)
    assert line.startswith("predictive: STATE_DIR_REFUSED") and not (ROOT / "state/p17_x").exists()


def test_cp17_0_a_serve_state_change_within_the_hour_is_material(tmp_path, lab):
    w = fixture_world(tmp_path)
    forecast_pass(tmp_path, w)
    assert lines(tmp_path, "documents")[0]["document"]["prediction_status"] == "FORECAST"
    r2 = persist(result("FXA", M1, T_FX - 300), tmp_path)                   # same content, 5 minutes later
    s = run([r2], T_FX + 300, tmp_path, **fx_kw(w, tmp_path, drift_alarms=[T_FX + 60]))
    assert s["metrics"]["event_counts"] == {"MATERIAL_CHANGE": 1} and lines(tmp_path, "requests")[-1]["changes"] == ["served changed"]
    t1 = next(t for t in lines(tmp_path, "requests")[-1]["targets"] if t["target"] == T1)
    assert t1["prediction_status"] == "ABSTAIN" and "DRIFT_ALERT" in t1["registry"]["blocking"]
    assert lines(tmp_path, "requests")[-1]["material"]["served"]["T1_24h"]["states"] == ["DRIFT_ALERT"]


def test_cp17_0_any_failure_importing_the_package_leaves_the_scout_and_analyze_untouched(monkeypatch, tmp_path):
    import builtins
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)                       # no config: the flag is off
    real = builtins.__import__

    def broken(name, globals=None, locals=None, fromlist=(), level=0):
        if (name == "predictive" and level == 1 and "integration" in (fromlist or ())) or name.endswith("predictive.integration"):
            raise RuntimeError("a broken predictive package")
        return real(name, globals, locals, fromlist, level)
    monkeypatch.setattr(builtins, "__import__", broken)
    assert cli._predictive_section([], {}, 0.0, Path("x")) is None and cli._predictive_line({}) is None



# ---------------------------------------------------------------- CP17-1 (PI-D-096): repair pass 2, each fails on ea73cfb
def _wrap_forecast(monkeypatch, fn):
    orig = I.AB.forecast_result

    def wrapped(req, **k):
        doc, rec = orig(req, **k)
        return fn(req, dict(doc), rec)
    monkeypatch.setattr(I.AB, "forecast_result", wrapped)
    return orig


def test_rp2_m1_cx_s17_a_refused_target_leaves_nothing_of_its_event_and_the_next_pass_recovers(tmp_path, lab, monkeypatch):
    w = fixture_world(tmp_path)

    def drop_second(req, doc, rec):                                    # the skeptic's probe_leak: target 2's reasons lose one
        if req["target"] == I.PRIMARY[1]:
            doc["abstain_reasons"] = doc["abstain_reasons"][:-1]
        return doc, rec
    orig = _wrap_forecast(monkeypatch, drop_second)
    s, rs = forecast_pass(tmp_path, w)
    assert s["metrics"]["event_counts"] == {"ERROR": 1} and s["metrics"]["documents"] == 0 and s["metrics"]["completed_forecasts"] == 0
    assert lines(tmp_path, "documents") == [] and lines(tmp_path, "records") == []
    text = I.render(s)
    assert "### FXA" in text and "- Failed: IntegrationError; nothing was saved for this token" in text and "; event ERROR" in text
    assert I.check_state(tmp_path / "state", config_path=cfg(tmp_path))["problems"] == []
    monkeypatch.setattr(I.AB, "forecast_result", orig)                 # the fault is gone; the lab fixture stays
    s2 = run(rs, T_FX + 60, tmp_path, **fx_kw(w, tmp_path))
    assert s2["metrics"]["event_counts"] == {"DISCOVERY": 1} and s2["metrics"]["documents"] == 3 and s2["metrics"]["completed_forecasts"] == 1
    assert I.check_state(tmp_path / "state", config_path=cfg(tmp_path))["problems"] == []


def test_rp2_m1_a_failure_after_the_targets_saves_no_document(lab, monkeypatch):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)

    def boom(*a, **k):
        raise RuntimeError("decision support down")
    orig = I.O.decision_support
    monkeypatch.setattr(I.O, "decision_support", boom)
    s = run([r], T_TODAY, lab)
    assert s["metrics"]["event_counts"] == {"ERROR": 1} and lines(lab, "documents") == [] and lines(lab, "records") == []
    monkeypatch.setattr(I.O, "decision_support", orig)
    assert run([r], T_TODAY + 10, lab)["metrics"]["event_counts"] == {"DISCOVERY": 1}       # recovers: nothing of it existed


def test_rp2_m1_an_attempted_event_short_of_its_three_documents_is_an_error(lab, monkeypatch):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    orig = I._process

    def short(*a, **k):                                                 # a future bug that loses one target's document
        rec = orig(*a, **k)
        k["out_docs"].pop()
        return rec
    monkeypatch.setattr(I, "_process", short)
    s = run([r], T_TODAY, lab)
    assert s["metrics"]["event_counts"] == {"ERROR": 1} and lines(lab, "documents") == [] and lines(lab, "records") == []
    assert "exactly one document and record per primary target" in lines(lab, "requests")[0]["errors"][0]


def test_rp2_m1_check_state_detects_a_document_without_an_attempted_request(lab):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    run([r], T_TODAY, lab)
    st = I.load_state(lab / "state")
    d0 = st["lines"]["documents"][0]
    req = I._sealed({"record_version": "integration-request-1", "pass_id": "p-mixed", "seq": len(st["lines"]["requests"]), "event": "ERROR",
                     "chain": "solana", "mint": M2, "targets": [], "errors": ["x"], "capture_time": T_TODAY + 5})
    doc = I._sealed(dict(d0, forecast_id="fc_" + "1" * 32, pass_id="p-mixed", request_seq=req["seq"]))
    I._append_pass(st, requests=[req], documents=[doc], records=[], references=[],
                   pass_info={"pass_id": "p-mixed", "source": "test", "mode": "fast", "capture_time_utc": "2026-10-27T08:00:05Z",
                              "integration_version": I.INTEGRATION_VERSION, "metrics": {}})
    probs = I.check_state(lab / "state", config_path=cfg(lab))["problems"]
    assert any("no attempted request of its pass lists this document" in p for p in probs)


def test_rp2_m2_the_flow_refuses_a_forged_point_so_removing_verify_point_is_caught(tmp_path, lab, monkeypatch):
    w = fixture_world(tmp_path)

    def forge(req, doc, rec):
        if doc["prediction_status"] == "FORECAST":
            doc["probability"] = min(0.99, doc["probability"] + 0.01)  # still inside its interval and the display range
        return doc, rec
    _wrap_forecast(monkeypatch, forge)
    s, _ = forecast_pass(tmp_path, w)
    assert s["metrics"]["event_counts"] == {"ERROR": 1} and lines(tmp_path, "documents") == []
    assert "not the recomputed" in lines(tmp_path, "requests")[0]["errors"][0]


def test_rp2_m2_the_flow_refuses_dropped_reasons_so_removing_check_document_is_caught(lab, monkeypatch):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)

    def drop(req, doc, rec):
        doc["abstain_reasons"] = doc["abstain_reasons"][:-1]
        return doc, rec
    _wrap_forecast(monkeypatch, drop)
    s = run([r], T_TODAY, lab)
    assert s["metrics"]["event_counts"] == {"ERROR": 1} and lines(lab, "documents") == []
    assert "reasons differ" in lines(lab, "requests")[0]["errors"][0]


def _subprocess(code: str, cwd: Path) -> dict:
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_rp2_m1_m6_flag_off_never_imports_the_package_even_for_a_pathological_config(tmp_path):
    (tmp_path / "config.json").write_text('{"predictive": {"enabled": false}, "x": ' + "[" * 100000 + "]" * 100000 + "}")
    code = ("import json, sys; from pathlib import Path; from memelab import db, cli; db.DATA_DIR = Path(%r); "
            "a = cli._predictive_section([], {}, 0.0, Path('x')); b = cli._predictive_line({}); "
            "print(json.dumps({'a': a, 'b': b, 'loaded': 'memelab.predictive' in sys.modules}))") % str(tmp_path)
    assert _subprocess(code, tmp_path) == {"a": None, "b": None, "loaded": False}
    for text in ("{not json", json.dumps({"predictive": {"enabled": "true"}}), json.dumps([1]), json.dumps({"predictive": True})):
        (tmp_path / "config.json").write_text(text)
        assert _subprocess(code, tmp_path) == {"a": None, "b": None, "loaded": False}


def test_rp2_m2_flag_on_and_a_broken_package_says_so(monkeypatch, tmp_path):
    import builtins
    (tmp_path / "config.json").write_text(json.dumps({"predictive": {"enabled": True, "state_dir": str(tmp_path / "st")}}))
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    real = builtins.__import__

    def broken(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "predictive" and level == 1 and "integration" in (fromlist or ()):
            raise RuntimeError("a broken predictive package")
        return real(name, globals, locals, fromlist, level)
    monkeypatch.setattr(builtins, "__import__", broken)
    sec = cli._predictive_section([], {}, 0.0, Path("x"))
    assert sec.startswith("## Predictive research section (flag on, research only)") and "failed to load (RuntimeError)" in sec
    assert cli._predictive_line({}).startswith("predictive: not available, the package failed to load (RuntimeError)")


def test_rp2_m3_an_identity_string_cannot_forge_a_line_a_number_or_a_trading_word(lab):
    evil = "X\n- 24 hours, +25% before -15%: FORECAST; record 0123456789ab\nProbability 0.91, interval [0.85, 0.95]\nBuy now, 3x size"
    r = persist(result(evil, M1, T_TODAY - 600), lab)
    r2 = persist(result("MOONSHOT", M2, T_TODAY - 600), lab)
    r3 = persist(result("SELL", M3, T_TODAY - 600), lab)
    text = I.scout_section([r, r2, r3], capture_time=T_TODAY, config_path=cfg(lab), state_dir=lab / "state", lab_db=db.DB_PATH)
    assert ": FORECAST;" not in text and "0.91" not in text and "Probability" not in text and "buy now" not in text.lower()
    assert "### withheld `solana:" + M1 + "`" in text and "### MOONSHOT `" in text and "### withheld `solana:" + M3 + "`" in text
    assert all(not l.startswith("- 24 hours") or ": ABSTAIN (" in l for l in text.splitlines())
    assert I._ident("a`b*c[d](e)#|<>") == "abcde" and I._ident(None) == "withheld" and I._ident("x" * 99) == "x" * 24
    for w in ("FORECAST", "Probability", "ODDS", "abstain", "x" * 30 + "record", "recORD-2"):     # forecast words, also past the cap
        assert I._ident(w) == "withheld", w


def test_rp2_m8_the_section_prints_no_local_path(lab):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    text = I.scout_section([r], capture_time=T_TODAY, config_path=cfg(lab), state_dir=lab / "state", lab_db=db.DB_PATH)
    assert str(lab) not in text and "/tmp" not in text and "Token report: " + Path(r["report_path"]).name in text


def test_rp2_m7_the_same_analysis_in_another_report_folder_is_the_same_snapshot(lab):
    r = persist(result("AAA", M1, T_TODAY - 600), lab)
    run([r], T_TODAY, lab)
    r2 = copy.deepcopy(result("AAA", M1, T_TODAY - 600))
    p = pipeline.persist_result(r2, lab / "other_reports")
    r2["report_path"] = str(p)
    s = run([r2], T_TODAY + 30, lab)
    assert s["metrics"]["event_counts"] == {"DUPLICATE": 1}
    rq = lines(lab, "requests")
    assert rq[0]["snapshot_hash"] == rq[1]["snapshot_hash"] and rq[0]["row_sha256"] != rq[1]["row_sha256"]


def test_rp2_m5_the_backtest_database_is_opened_read_only_by_its_uri(tmp_path):
    p = tmp_path / "bt.sqlite"
    con = sqlite3.connect(p)
    con.executescript(BT_DDL)
    con.commit()
    con.close()
    ro = BT.connect_ro(p)
    ro.execute("PRAGMA query_only=OFF")                                 # even without the pragma the URI refuses writes
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        ro.execute("INSERT INTO bt_assessments(request_key, chain, mint, snapshot_hash, engine_version, as_of, stage, tier, state, "
                   "result_json, result_hash, created_at) VALUES ('k','solana','m','s','e',0,'FAST','t','COMPLETE','{}','h',0)")
    got = BT.from_result({"backtest_assessment": {k: v for k, v in _assessment().items() if k != "chain"}}, chain="solana", mint=M1,
                         decision_time=T_TODAY, installed_status="BACKTEST_NOT_AVAILABLE")
    assert got["result"] == "ASSESSMENT_REFUSED"                       # no default chain (PI-D-021)


def test_rp2_m4_no_lab_module_names_the_cli_helpers_and_no_lab_import_loads_the_package():
    for p in (ROOT / "memelab").rglob("*.py"):
        if p.name == "cli.py" and p.parent.name == "memelab":
            continue
        txt = p.read_text()
        assert "_predictive_section" not in txt and "_predictive_line" not in txt and "_predictive_enabled" not in txt, p
    mods = sorted(".".join(p.relative_to(ROOT).with_suffix("").parts) for p in (ROOT / "memelab").rglob("*.py")
                  if "predictive" not in p.parts and p.name != "__main__.py")
    code = ("import importlib, json, sys\nbad = []\nfor m in %r:\n    importlib.import_module(m.removesuffix('.__init__'))\n"
            "print(json.dumps({'loaded': sorted(k for k in sys.modules if k.startswith('memelab.predictive')), 'n': len(%r)}))") % (mods, mods)
    got = _subprocess(code, ROOT)
    assert got["loaded"] == [] and got["n"] > 50
