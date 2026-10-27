"""Phase 18: report-1 and alerts-rules-1 (memelab/predictive/reports.py). Pre-registration:
audits/predictive-intelligence/phase_18/ACCEPTANCE_CHECKLIST.md (rules 1 to 15, G1 to G24, CX-18).

Temp databases and folders only, fixed clocks, no network (an audit hook refuses sockets in every test of this file). Every
FORECAST here is a format-only fixture: no real card is calibrated and no real champion exists. The world builders below are
also used by audits/predictive-intelligence/phase_18/probes/run_reports.py to write the golden files and the examples."""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from memelab import db
from memelab.predictive import abstention as AB
from memelab.predictive import contract as C
from memelab.predictive import integration as I
from memelab.predictive import registry as R
from memelab.predictive import reports as RP
from memelab.social import alerts_engine as AE

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import test_predictive_integration as TI  # noqa: E402  (the Phase 17 fixture builders)

GOLDEN = ROOT / "tests/fixtures/predictive/phase18/golden"
DAY = 86400.0
T_TODAY, T_FX = TI.T_TODAY, TI.T_FX
M1, M2, M3 = TI.M1, TI.M2, TI.M3
M4, M5 = TI.b58("m4"), TI.b58("m5")
EVM1 = "0x" + hashlib.sha256(b"evm1").hexdigest()[:40]
SOCKETS: list[str] = []
_ACTIVE = [False]


def _hook(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto") and _ACTIVE[0]:
        SOCKETS.append(event)
        raise RuntimeError(f"no network in the Phase 18 tests ({event})")


sys.addaudithook(_hook)


@pytest.fixture(autouse=True)
def no_network():
    _ACTIVE[0] = True
    SOCKETS.clear()
    yield
    _ACTIVE[0] = False
    assert SOCKETS == []


def _setdb(tmp: Path) -> None:
    db.DB_PATH = tmp / "lab.sqlite"
    db.DATA_DIR = tmp / "data"
    (tmp / "data").mkdir(parents=True, exist_ok=True)
    db.init_db()


@pytest.fixture
def lab(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "lab.sqlite")
    monkeypatch.setattr(db, "DATA_DIR", tmp_path / "data")
    (tmp_path / "data").mkdir()
    db.init_db()
    return tmp_path


def _pass(results, T, tmp, **kw):
    kw.setdefault("config_path", TI.cfg(tmp))
    kw.setdefault("state_dir", tmp / "state")
    kw.setdefault("clock", lambda: 0.0)
    kw.setdefault("sleep", lambda s: None)
    return I.run_pass(results, capture_time=T, lab_db=db.DB_PATH, **kw)


# ---------------------------------------------------------------- worlds (deterministic: fixed clocks and seeds)
def world_abstain(tmp: Path) -> dict:
    """The real committed registry (NO_VIABLE_CHAMPION): a clean token, an impossible exit, no pool, stale inputs, an EVM token,
    a result that is not a decision and one that is not an exact address."""
    T = T_TODAY
    rs = [TI.persist(TI.result("ABC", M1, T - 600), tmp),
          TI.persist(TI.result("GOMOX", M2, T - 600, fatal=("CANNOT_EXIT_5K",), status="REJECTED", score=0), tmp),
          TI.persist(TI.result("NOPOOL", M3, T - 600, pool=None), tmp),
          TI.persist(TI.result("OLDX", M4, T - 3 * DAY), tmp),
          TI.persist(TI.result("EVMX", EVM1, T - 600, chain="base"), tmp),
          TI.result("NOROW", M5, T - 600),
          TI.result("BAD", "not-a-mint", T - 600)]
    _pass(rs, T, tmp)
    return {"state_dir": tmp / "state", "config": TI.cfg(tmp), "lab_db": db.DB_PATH, "registry_dir": None, "extra": None, "now": T + 60}


def world_forecast(tmp: Path) -> dict:
    """A format-only fixture champion (SHADOW, CALIBRATED fixture card): a clean token whose interval is above the base rate,
    and a strong forecast on a token whose exit is impossible (CANNOT_EXIT_5K)."""
    w = TI.fixture_world(tmp)
    rs = [TI.persist(TI.result("FXA", M1, T_FX - 600, liq=150000.0, mcap=3.0e6, vol=3.0e5), tmp),
          TI.persist(TI.result("FXC", M2, T_FX - 600, liq=400000.0, mcap=8.0e6, vol=8.0e5, fatal=("CANNOT_EXIT_5K",), status="REJECTED",
                               score=62), tmp)]
    _pass(rs, T_FX, tmp, **TI.fx_kw(w, tmp, sleep=lambda s: None))
    return {"state_dir": tmp / "state", "config": TI.cfg(tmp), "lab_db": db.DB_PATH, "registry_dir": w["registry_dir"],
            "extra": w["extra"], "now": T_FX + 60, "world": w}


def world_withdrawn(tmp: Path) -> dict:
    """A fixture FORECAST, then the champion rolled back: the same content again is MATERIAL and abstains (CX-17 path)."""
    d = world_forecast(tmp)
    w = d["world"]
    evs = R.read_log((w["registry_dir"] / "REGISTRY_LOG.jsonl").read_text())
    rb = R.rollback_event(evs, w["entries"], TI.T1, reason="FIXTURE_ROLLBACK", as_of_utc=AB._iso(T_FX + 60), usable=lambda e: False,
                          allow_fixture=True)
    R.append_events(w["registry_dir"] / "REGISTRY_LOG.jsonl", [rb], expect_sha=R.file_sha(w["registry_dir"] / "REGISTRY_LOG.jsonl"))
    r2 = TI.persist(TI.result("FXA", M1, T_FX + 3000, liq=150000.0, mcap=3.0e6, vol=3.0e5), tmp)
    _pass([r2], T_FX + 3600, tmp, **TI.fx_kw(w, tmp, sleep=lambda s: None))
    d["now"] = T_FX + 3660
    return d


INJECT = ["BUY-NOW", "## 99% chance", "a|b|c", "line1\nline2", "/tmp/evil/path", "<script>x</script>", "pump.fun"]


def world_injection(tmp: Path) -> dict:
    """Token text that tries to inject headings, table cells, trade words, forecast words and a local path; a lab status with
    trade wording (NEAR ENTRY)."""
    T = T_TODAY
    rs = []
    for i, sym in enumerate(INJECT):
        rs.append(TI.persist(TI.result(sym, TI.b58(f"inj{i}"), T - 600, status="NEAR ENTRY" if i == 0 else "WATCH"), tmp))
    _pass(rs, T, tmp)
    return {"state_dir": tmp / "state", "config": TI.cfg(tmp), "lab_db": db.DB_PATH, "registry_dir": None, "extra": None, "now": T + 60}


def reseal(state_dir: Path, mutate) -> None:
    """An adversary who edits the state and recomputes every record id, file sha and the pass chain, so `load_state` still
    passes (CX-18). `mutate(lines)` edits the dict of parsed lines in place."""
    names = I.FILES
    lines = {k: [json.loads(x) for x in (state_dir / f).read_text().splitlines()] if (state_dir / f).exists() else []
             for k, f in names.items()}
    mutate(lines)
    for k in ("requests", "documents", "records", "references"):
        lines[k] = [I._sealed(r) for r in lines[k]]
        (state_dir / names[k]).write_text("".join(AB.canon(r) + "\n" for r in lines[k]) if lines[k] else "")
        if not lines[k]:
            (state_dir / names[k]).unlink()
    prev = I.GENESIS
    out = []
    for i, p in enumerate(lines["passes"]):
        p = dict(p, seq=i, prev=prev)
        if i == len(lines["passes"]) - 1:
            p["files_after"] = {k: AB.file_sha(state_dir / names[k]) for k in ("requests", "documents", "records", "references")}
        p = I._sealed(p)
        prev = p["record_id"]
        out.append(p)
    (state_dir / names["passes"]).write_text("".join(AB.canon(p) + "\n" for p in out))


def forge_probability(lines: dict, delta: float = 0.05) -> None:
    for d in lines["documents"]:
        if d["document"]["prediction_status"] == "FORECAST":
            d["document"]["probability"] = round(d["document"]["probability"] + delta, 6)
            return
    raise AssertionError("no FORECAST to forge")


def report(d: dict, **kw) -> tuple[dict, str]:
    v = RP.build(d["state_dir"], config_path=d["config"], lab_db=kw.pop("lab_db", d["lab_db"]), registry_dir=d["registry_dir"],
                 extra_cal_cards=d["extra"], **kw)
    return v, RP.render(v)


def _varying(v: dict) -> list[str]:
    """Values that depend on the temp folder (report paths inside row hashes and request ids, card paths inside fixture registry
    ids): replaced by a placeholder in the golden comparison. Everything else is compared byte for byte."""
    out = set()
    for o in v.get("opportunities") or []:
        out |= {o["ids"]["request_record_id"], o["snapshot"]["row_sha256"], o.get("previous_request_record_id")}
        for t in o["targets"]:
            out.add(t["registry"].get("pin_event_id"))
    for r in v.get("not_attempted") or []:
        out.add(r["request_record_id"])
    s = v.get("system") or {}
    out |= {s.get("registry_log_sha256"), s.get("last_pass_record_id")}
    for x in (s.get("served") or {}).values():
        out.add(x.get("pin_event_id"))
    return sorted(x for x in out if isinstance(x, str) and re.fullmatch(r"[0-9a-f]{64}", x))


def normalize(text: str, v: dict) -> str:
    for x in _varying(v):
        for n in (64, 16, 12):
            text = text.replace(x[:n], "<varies>")
    return text


def golden_texts(tmp: Path) -> dict[str, str]:
    """Every golden text, built in sub-folders of tmp (each world with its own lab database)."""
    out = {}
    for name, fn in (("abstain", world_abstain), ("forecast_format_only", world_forecast), ("withdrawn_format_only", world_withdrawn),
                     ("injection", world_injection)):
        sub = tmp / name
        sub.mkdir()
        _setdb(sub)
        d = fn(sub)
        v, text = report(d)
        out[f"report_{name}.md"] = normalize(text, v)
        if name in ("forecast_format_only", "withdrawn_format_only"):
            a = RP.alert_run(d["state_dir"], config_path=d["config"], alert_db=sub / "alerts" / "alerts.sqlite", now=d["now"],
                             fixture_run=True, registry_dir=d["registry_dir"], extra_cal_cards=d["extra"], lab_db=d["lab_db"])
            texts = sorted((sub / "alerts" / "outbox" / "preview").glob("alert_*.txt"))
            body = "".join(f"----- {p.name}\n{p.read_text()}" for p in texts)
            out[f"alerts_{name}.txt"] = normalize(body, v) + normalize(AE.render_run(a, "America/New_York"), v)
    sub = tmp / "forged"
    sub.mkdir()
    _setdb(sub)
    d = world_forecast(sub)
    reseal(d["state_dir"], forge_probability)
    v, text = report(d)
    out["report_forged_refused.md"] = normalize(text, v)
    return out


# ---------------------------------------------------------------- G2: no existing file changed
def test_g2_files_phase18_must_not_change_are_byte_identical_to_4ebccc3():
    want = json.loads((GOLDEN.parent / "PINNED_SHA256.json").read_text())
    assert set(want) >= {"memelab/cli.py", "memelab/predictive/integration.py", "memelab/report.py", "memelab/social/alerts_core.py",
                         "memelab/social/alerts_engine.py", "memelab/social/alerts_transport.py", "memelab/predictive/contract.py",
                         "memelab/predictive/abstention.py", "memelab/predictive/registry.py", "memelab/predictive/calibration.py"}
    for rel, sha in want.items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == sha, rel


# ---------------------------------------------------------------- G3: flag off
def test_g3_flag_off_builds_nothing_and_the_commands_write_nothing(lab):
    d = world_abstain(lab)
    off = TI.cfg(lab, on=False)
    v = RP.build(d["state_dir"], config_path=off)
    assert v["state"] == "FLAG_OFF" and v["opportunities"] == [] and "system" not in v
    assert RP.alert_run(d["state_dir"], config_path=off, alert_db=lab / "al" / "a.sqlite", now=d["now"]) is None
    assert not (lab / "al").exists()
    for bad in ('{"predictive": {"enabled": "true"}}', '{"predictive": true}', "not json", '{"predictive": {"enabled": 1}}'):
        (lab / "bad.json").write_text(bad)
        assert RP.build(d["state_dir"], config_path=lab / "bad.json")["state"] == "FLAG_OFF"
    base = [sys.executable, "-m", "memelab.predictive.reports"]
    for args in (["report", "--state-dir", str(d["state_dir"]), "--out", str(lab / "out" / "r.md")],
                 ["alerts", "--state-dir", str(d["state_dir"]), "--alert-db", str(lab / "al" / "a.sqlite")],
                 ["alerts-state", "--alert-db", str(lab / "al" / "a.sqlite")]):
        p = subprocess.run(base + args + ["--config", str(off)], cwd=ROOT, capture_output=True, text=True)
        assert p.returncode == 0 and "FLAG_OFF" in p.stdout, (args, p.stdout, p.stderr)
    assert not (lab / "out").exists() and not (lab / "al").exists()


def test_g3_no_module_imports_reports_so_lab_outputs_cannot_change():
    for p in (ROOT / "memelab").rglob("*.py"):
        if p.name == "reports.py" and p.parent.name == "predictive":
            continue
        tree = ast.parse(p.read_text())
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom):
                mod = n.module or ""
                assert not (mod.endswith("predictive.reports") or (mod.endswith("predictive") and any(a.name == "reports" for a in n.names))), p
                if p.parent.name == "predictive":
                    assert not (n.level == 1 and (mod == "reports" or (not mod and any(a.name == "reports" for a in n.names)))), p
            if isinstance(n, ast.Import):
                assert not any(a.name.endswith("predictive.reports") for a in n.names), p
        assert "predictive.reports" not in p.read_text(), p


# ---------------------------------------------------------------- G4: golden reports and alerts
@pytest.fixture(scope="module")
def goldens(tmp_path_factory):
    old = (db.DB_PATH, db.DATA_DIR)
    try:
        return golden_texts(tmp_path_factory.mktemp("p18_golden"))
    finally:
        db.DB_PATH, db.DATA_DIR = old


@pytest.mark.parametrize("name", ["report_abstain.md", "report_forecast_format_only.md", "report_withdrawn_format_only.md",
                                  "report_injection.md", "report_forged_refused.md", "alerts_forecast_format_only.txt",
                                  "alerts_withdrawn_format_only.txt"])
def test_g4_golden_files_are_reproduced_byte_for_byte(goldens, name):
    assert goldens[name] == (GOLDEN / name).read_text(), name


def test_g4_the_golden_normalization_only_replaces_temp_folder_ids(lab):
    d = world_abstain(lab)
    v, text = report(d)
    vs = _varying(v)
    assert vs and all(re.fullmatch(r"[0-9a-f]{64}", x) for x in vs)
    norm = normalize(text, v)
    assert norm.count("\n") == text.count("\n") and "ABSTAIN (no number)" in norm and "fc_" in norm
    for t in v["opportunities"][0]["targets"]:
        assert t["forecast_id"] in norm and t["record_id"][:12] in norm      # forecast and record ids are stable and kept


# ---------------------------------------------------------------- G5, G6: required fields; no number for an abstention
def test_g5_every_attempted_target_carries_the_required_fields(lab):
    d = world_abstain(lab)
    v, text = report(d)
    assert v["state"] == "OK" and v["counts"]["opportunities"] == 5 and v["counts"]["targets"] == 15
    for o in v["opportunities"]:
        sn = o["snapshot"]
        assert o["mint_text"] == o["mint"] and f"{o['chain_text']}:{o['mint']}" in text
        for k in ("snapshot_hash", "row_sha256", "decision_time_utc", "decision_time_basis", "capture_time_utc", "observed_at_utc", "input_state"):
            assert sn[k] is not None, k
        assert sn["lab_state"] == "SNAPSHOT_VERIFIED" and sn["token_age_s"] is not None and o["symbol"]
        assert {t["short"] for t in o["targets"]} == {"T1_24h", "T1b_6h", "T2_24h"}
        for t in o["targets"]:
            assert t["status"] == "ABSTAIN" and t["reasons"] and t["forecast_id"].startswith("fc_") and t["horizon_seconds"] in (21600, 86400)
            assert "MODEL_NOT_SELECTED" in t["reasons"] and "UNCALIBRATED" in t["reasons"] and t["number"] is None
            assert t["forecast_id"] in text and t["record_id"][:12] in text
        assert o["not_attempted_targets"] and o["execution"]["size_basis"] == "EXECUTION_DATA_MISSING"
    for needle in ("token age at the snapshot", "inputs observed", "decision time", "Training as of", "Cohort N and base rate",
                   "not shown: no model selected", "fatal-flag veto", "Caveats", "Registered targets not attempted", "INPUT_STALE",
                   "## Target definitions", "## Carried constraints", "## Units and times", "## Events not attempted"):
        assert needle in text, needle


_PCT = re.compile(r"\d+(\.\d+)?\s*%")


def _numbers_outside_definitions(text: str) -> list[str]:
    t = re.sub(r"rises 25% before it falls 15%", "", text)
    t = t.replace("+25% before -15%", "")
    return _PCT.findall(t) + re.findall(r"(?<![\w.])0\.\d+", t)


def _numeric_keys(o, path=""):
    """Keys of the view that carry a probability-like number (a base rate, a probability, an interval, a skill score)."""
    out = []
    if isinstance(o, dict):
        for k, v in o.items():
            if re.search(r"base_rate|probab|interval|bss|brier|skill", str(k), re.I) and v is not None:
                out.append(path + str(k))
            out += _numeric_keys(v, path + str(k) + ".")
    elif isinstance(o, list):
        for i, x in enumerate(o):
            out += _numeric_keys(x, path + f"{i}.")
    return out


def test_g6_an_abstaining_target_shows_no_number_no_base_rate_and_no_reference_number(lab):
    d = world_abstain(lab)
    v, text = report(d)
    assert v["counts"]["probabilities_shown"] == 0
    assert _numbers_outside_definitions(text) == []
    assert [k for k in _numeric_keys(v) if not k.startswith("counts.")] == []
    assert not re.search(r"(?i)(brier|bss|skill)\D{0,3}-?\d+\.\d", text)          # codes such as B2_RETROSPECTIVE_BSS_BELOW_0 only
    assert "Probabilities shown: 0 of 15" in text and "No probability is shown" in text
    for o in v["opportunities"]:
        for t in o["targets"]:
            assert t["number"] is None


def test_g6_no_text_says_a_forecast_changes_the_score(lab):
    d = world_forecast(lab)
    _, text = report(d)
    low = text.lower()
    for w in ("boost", "raises the score", "score increase", "upgrade"):
        assert w not in low
    assert "nothing here changes the 100-point score" in text


# ---------------------------------------------------------------- G7 and CX-18: documents that must never show a number
def test_g7_cx18_a_forged_probability_in_a_resealed_state_is_refused_and_shows_no_number(lab):
    d = world_forecast(lab)
    v0, t0 = report(d)
    assert v0["counts"]["probabilities_shown"] == 1 and v0["counts"]["overridden"] == 1      # FXC: its risk withholds the number
    reseal(d["state_dir"], forge_probability)
    assert I.check_state(d["state_dir"], config_path=d["config"])["problems"] == []          # the adversary kept the state consistent
    v, text = report(d)
    t1 = [t for o in v["opportunities"] for t in o["targets"] if t["short"] == "T1_24h"]
    refused = [t for t in t1 if t["status"] == "DOCUMENT_REFUSED"]
    assert len(refused) == 1 and "probability differs from the point stored with the raw number" in refused[0]["checks"]
    assert refused[0]["number"] is None and v["counts"]["probabilities_shown"] == 0
    assert "REFUSED (no number)" in text


def test_g7_a_record_with_other_reasons_an_orphan_document_and_an_out_of_range_number_are_refused(lab):
    d = world_forecast(lab)

    def other_reasons(lines):
        for r in lines["records"]:
            if r["prediction_status"] == "ABSTAIN":
                r["reasons"] = [x for x in r["reasons"] if x != "UNCALIBRATED"]
                rid_old = r["record_id"]
                r.pop("record_id")
                new = I._sealed(r)
                for dl in lines["documents"]:
                    if dl["abstention_record_id"] == rid_old:
                        dl["abstention_record_id"] = new["record_id"]
                        dl["document"]["evidence_refs"] = [f"{AB.ABSTENTION_VERSION}:{new['record_id']}" if x.endswith(rid_old) else x
                                                           for x in dl["document"]["evidence_refs"]]
                return
    reseal(d["state_dir"], other_reasons)
    v, _ = report(d)
    ref = [t for o in v["opportunities"] for t in o["targets"] if t["status"] == "DOCUMENT_REFUSED"]
    assert len(ref) == 1 and any("reasons differ" in c for c in ref[0]["checks"])

    def orphan(lines):
        x = copy.deepcopy(lines["documents"][0])
        x["request_seq"] = 999
        x["document"]["forecast_id"] = "fc_" + "0" * 32
        x["forecast_id"] = "fc_" + "0" * 32
        lines["documents"].append(x)
    reseal(d["state_dir"], orphan)
    v, text = report(d)
    assert v["state"] == "STATE_CHECK_FAILED" and "State check:" in text


def test_g7_an_out_of_range_number_is_refused_even_when_request_and_document_agree(lab):
    d = world_forecast(lab)

    def out_of_range(lines):
        for dl in lines["documents"]:
            if dl["document"]["prediction_status"] == "FORECAST":
                dl["document"]["probability"] = 1.5
        for r in lines["requests"]:
            for t in r.get("targets") or []:
                if t.get("calibrated_point") is not None:
                    t["calibrated_point"] = 1.5
    reseal(d["state_dir"], out_of_range)
    v, text = report(d)
    assert v["counts"]["probabilities_shown"] == 0 and v["counts"]["refused"] == 2 and "150%" not in text


def test_g7_cards_that_do_not_resolve_refuse_the_forecast_and_a_tampered_state_shows_nothing(lab):
    d = world_forecast(lab)
    v = RP.build(d["state_dir"], config_path=d["config"], lab_db=d["lab_db"], registry_dir=None, extra_cal_cards=None)
    assert v["counts"]["probabilities_shown"] == 0 and v["counts"]["refused"] == 2
    assert all(any(c.startswith("cards:") for c in t["checks"]) for o in v["opportunities"] for t in o["targets"] if t["status"] == "DOCUMENT_REFUSED")
    p = d["state_dir"] / I.FILES["documents"]
    p.write_text(p.read_text().replace('"FORECAST"', '"ABSTAIN"', 1))
    v2, text = report(d)
    assert v2["state"] == "STATE_TAMPERED" and v2["opportunities"] == [] and "No opportunity is shown and no number is shown." in text


def test_g7_a_flag_turned_off_after_the_pass_shows_nothing(lab):
    d = world_forecast(lab)
    (TI.cfg(lab)).write_text('{"predictive": {"enabled": false}}')
    assert RP.build(d["state_dir"], config_path=d["config"])["state"] == "FLAG_OFF"


# ---------------------------------------------------------------- G8: strong forecast with an impossible exit
def test_g8_the_impossible_exit_shows_the_veto_and_the_alerts_override_the_forecast(lab):
    d = world_forecast(lab)
    v, text = report(d)
    by = {o["symbol"]: o for o in v["opportunities"]}
    fxc = by["FXC"]
    t1 = next(t for t in fxc["targets"] if t["short"] == "T1_24h")
    assert t1["status"] == "FORECAST" and t1["overridden"] and t1["number"] is None and t1["overridden_level"] == "SHADOW"
    assert fxc["execution"]["veto"] and fxc["execution"]["fatal_flags"] == ["CANNOT_EXIT_5K"] and "83%" not in text
    sec = text.split("## FXC")[1].split("\n## ")[0]
    assert "FORECAST OVERRIDDEN by risk (number withheld)" in sec and "CANNOT_EXIT_5K; no forecast clears it" in sec
    assert "a verified research estimate exists for this snapshot (level SHADOW), but a risk overrides it" in sec
    assert "PRICE_PATH_NOT_PROCEEDS" in sec and "EXECUTION_DATA_MISSING" in sec
    out = RP.alert_run(d["state_dir"], config_path=d["config"], alert_db=lab / "al" / "a.sqlite", now=d["now"], fixture_run=True,
                       registry_dir=d["registry_dir"], extra_cal_cards=d["extra"], lab_db=d["lab_db"])
    pol = [(a["policy"], a["label"].split(" ")[0]) for a in out["evaluation"]["alerts"]]
    assert pol[0] == ("risk_override", "FXC")                                          # warnings first
    assert ("reevaluate", "FXA") in pol and ("reevaluate", "FXC") not in pol
    sup = [(s["policy"], s["reason_code"]) for s in out["evaluation"]["suppressed"] if "FXC" in s["label"]]
    assert ("reevaluate", "RISK_OVERRIDES_FORECAST") in sup
    risk = next((lab / "al" / "outbox" / "preview").glob(f"alert_{out['evaluation']['alerts'][0]['alert_id']:06d}.txt")).read_text()
    assert "The research estimate on this snapshot is overridden." in risk and RP.WATERMARK in risk.splitlines()[0]


# ---------------------------------------------------------------- G9: no-simulation status
def test_g9_every_report_says_simulation_not_available_and_scenarios_are_labels_only(lab):
    d = world_abstain(lab)
    _, text = report(d)
    assert text.count("SIMULATION_NOT_AVAILABLE") >= 1 + 4 and "MIROFISH_NO_GO" in text

    def label_only(lines):
        dl = lines["documents"][0]
        dl["document"]["behavioral_scenarios"] = [{"label": "ATTENTION_FADE", "kind": "SYNTHETIC_HYPOTHESIS"}]
    reseal(d["state_dir"], label_only)
    v, text = report(d)
    t = [t for o in v["opportunities"] for t in o["targets"] if t.get("scenarios")]
    assert len(t) == 1 and t[0]["status"] == "ABSTAIN" and "synthetic hypotheses listed by label only, never a probability: ATTENTION_FADE" in text

    def with_number(lines):
        dl = lines["documents"][0]
        dl["document"]["behavioral_scenarios"] = [{"label": "ATTENTION_FADE", "agreement": 0.9}]
    reseal(d["state_dir"], with_number)
    v, text = report(d)
    ref = [t for o in v["opportunities"] for t in o["targets"] if t["status"] == "DOCUMENT_REFUSED"]
    assert len(ref) == 1 and "0.9" not in text and "90%" not in text


# ---------------------------------------------------------------- G10: missing-data UX
def test_g10_every_contract_reason_has_an_unblock_text():
    assert set(RP.UNBLOCK) == set(C.ABSTAIN_REASONS)
    for k, v in RP.UNBLOCK.items():
        assert v and RP._plain(v), k


def test_g10_each_missing_state_has_a_visible_line(lab):
    d = world_abstain(lab)
    v, text = report(d)
    sec = {o["symbol"]: o for o in v["opportunities"]}
    assert sec["OLDX"]["snapshot"]["input_state"] == "INPUT_STALE" and "INPUT_STALE" in text
    assert any("TARGET_NOT_FEASIBLE" in t["reasons"] for t in sec["NOPOOL"]["targets"])
    na = {r["event"] for r in v["not_attempted"]}
    assert {"NO_DECISION_SNAPSHOT", "NOT_EXACT_IDENTITY"} <= na and "not-an-exact-address" in text
    evm = [o for o in v["opportunities"] if o["chain"] == "base"]
    assert evm and all("OUT_OF_SCOPE_CHAIN" in t["reasons"] for t in evm[0]["targets"])
    assert "COLLECTOR_NOT_AVAILABLE" in text and "BACKTEST_NOT_AVAILABLE" in text and "SIMULATION_NOT_AVAILABLE" in text
    for r in ("TARGET_NOT_FEASIBLE", "SOURCE_STALE", "OUT_OF_SCOPE_CHAIN", "MODEL_NOT_SELECTED", "UNCALIBRATED"):
        assert f"  - {r}: {RP.UNBLOCK[r]}." in text
    v2, t2 = report(d, lab_db=None)
    assert v2["counts"]["snapshots_verified"] == 0 and "SNAPSHOT_NOT_VERIFIED" in t2 and "symbol not verified" in t2
    empty = lab / "nostate"
    assert RP.build(empty, config_path=d["config"])["state"] == "NO_STATE"
    assert "State: NO_STATE" in RP.render(RP.build(empty, config_path=d["config"]))


def test_g10_registry_unavailable_at_the_pass_is_named(lab):
    (lab / "noreg").mkdir()
    rs = [TI.persist(TI.result("ABC", M1, T_TODAY - 600), lab)]
    _pass(rs, T_TODAY, lab, registry_dir=lab / "noreg")
    v, text = report({"state_dir": lab / "state", "config": TI.cfg(lab), "lab_db": db.DB_PATH, "registry_dir": None, "extra": None})
    assert v["system"]["served"]["T1_24h"]["state"] == "REGISTRY_UNAVAILABLE" or "REGISTRY_UNAVAILABLE" in json.dumps(v)
    assert "REGISTRY_UNAVAILABLE" in text


# ---------------------------------------------------------------- G11: sanitization
def test_g11_injected_token_text_is_withheld_or_reduced_and_trade_wording_never_printed(lab):
    d = world_injection(lab)
    v, text = report(d)
    assert "withheld" in text
    for bad in ("BUY", "## 99", "<script>", "/tmp/evil", "line1\nline2", "NEAR ENTRY", "a|b|c"):
        assert bad not in text, bad
    for line in text.splitlines():
        if line.startswith("| ") and "Exact chain:mint" not in line and not line.startswith("|---"):
            assert line.count("|") in (7, 8, 9), line                  # no injected cell
    heads = [l for l in text.splitlines() if l.startswith("## ")]
    assert all(not re.search(r"99|chance", h) for h in heads)
    st = [o["structural"]["status"] for o in v["opportunities"]]
    assert "kept in the lab's token report (its label uses trade wording)" in st


def test_g11_the_text_check_raises_on_a_trade_word_or_a_local_path():
    for bad in ("buy now", "a target price", "take profit at", "position size 5k", "see /home/claude/x", "a stop-loss"):
        with pytest.raises(RP.ReportError):
            RP.check_text("ok " + bad)
    RP.check_text("NO_ENTRY_AT_SHADOW_OR_ABOVE and NO_TRADES_AFTER_ENTRY are registry codes")
    mint = TI.b58("buy")
    RP.check_text(f"exact {mint}", [mint])


def test_g11_the_lab_status_words_are_the_m24_list():
    from memelab.modules import m24_opportunity_ranker as M24
    assert tuple(M24.STATUSES) == RP.LAB_STATUSES
    shown = {s: RP._status_text(s)[1] for s in RP.LAB_STATUSES}
    assert shown["NEAR ENTRY"] == shown["ENTRY CONDITIONS MET"] == "UNKNOWN" and shown["WATCH"] == "FACT"


# ---------------------------------------------------------------- G12: format-only watermark
def test_g12_a_fixture_report_is_watermarked_first_last_and_on_every_forecast_row(lab):
    d = world_forecast(lab)
    v, text = report(d)
    lines = text.splitlines()
    assert v["format_only"] and lines[0] == RP.WATERMARK and lines[-1] == RP.WATERMARK
    rows = [l for l in lines if "FORECAST " in l and l.startswith("| ")]
    assert rows and all("FORMAT-ONLY FIXTURE" in l for l in rows)
    v["format_only"] = False
    with pytest.raises(RP.ReportError):
        RP.render(v)


def test_g12_a_fixture_document_in_a_live_alert_run_is_suppressed(lab):
    d = world_forecast(lab)
    out = RP.alert_run(d["state_dir"], config_path=d["config"], alert_db=lab / "al" / "a.sqlite", now=d["now"], fixture_run=False,
                       registry_dir=d["registry_dir"], extra_cal_cards=d["extra"])
    assert out["evaluation"]["new"] == [] and {s["reason_code"] for s in out["evaluation"]["suppressed"]} == {"FIXTURE_IN_LIVE_RUN"}


# ---------------------------------------------------------------- G13: alert conventions (social-intel)
def _arun(d, lab, now, **kw):
    kw.setdefault("fixture_run", True)
    return RP.alert_run(d["state_dir"], config_path=d["config"], alert_db=lab / "al" / "a.sqlite", now=now,
                        registry_dir=d["registry_dir"], extra_cal_cards=d["extra"], lab_db=d["lab_db"], **kw)


def test_g13_dedupe_new_passes_only_too_soon_and_the_ledger(lab):
    d = world_forecast(lab)
    a = _arun(d, lab, d["now"])
    assert a["outcome"] == "evaluated" and len(a["evaluation"]["new"]) == 2
    b = _arun(d, lab, d["now"] + 600)
    assert b["outcome"] == "too_soon"
    c = _arun(d, lab, d["now"] + 3700)
    assert c["outcome"] == "no_new_upstream_data"
    con = AE.connect(lab / "al" / "a.sqlite")
    st = [dict(r) for r in con.execute("SELECT status, transport, error FROM alert_deliveries")]
    ev = [dict(r) for r in con.execute("SELECT status, mode FROM alert_events")]
    view = AE.state_view(con)
    con.close()
    assert {x["status"] for x in st} == {"dry_run_preview"} and {x["transport"] for x in st} == {"file"}
    assert {x["status"] for x in ev} == {"PREVIEW"} and {x["mode"] for x in ev} == {"dry_run"}
    txt = AE.render_state(view)
    assert "Nothing has been sent to a device." in txt and "dry run: preview only, nothing sent" in txt
    assert not (lab / "al" / "outbox" / "sent").exists() and len(list((lab / "al" / "outbox" / "preview").iterdir())) == 2
    # a later pass is evaluated alone: its clean token gives no candidate, the earlier ones are not evaluated again
    _pass([TI.persist(TI.result("ZZZ", M3, T_FX + 7000), lab)], T_FX + 7200, lab, **TI.fx_kw(d["world"], lab, sleep=lambda s: None))
    f = _arun(d, lab, d["now"] + 7300)
    assert f["outcome"] == "evaluated" and f["evaluation"]["candidates"] == 0 and f["evaluation"]["deduped"] == 0
    # the same data evaluated again (the run record lost): every candidate is deduplicated, nothing new
    con = AE.connect(lab / "al" / "a.sqlite")
    con.execute("DELETE FROM alert_runs")
    con.commit()
    con.close()
    e = _arun(d, lab, d["now"] + 11000)
    assert e["outcome"] == "evaluated" and e["evaluation"]["new"] == [] and e["evaluation"]["deduped"] == 2


def test_g13_cp18_2_notices_and_warnings_have_separate_daily_caps_so_a_warning_is_never_crowded_out(lab):
    d = world_forecast(lab)
    a = _arun(d, lab, d["now"], policy=RP.make_alert_policy({"daily_cap": 0}))
    assert [x["policy"] for x in a["evaluation"]["alerts"]] == ["risk_override"]
    assert ("reevaluate", "daily_cap") in {(s["policy"], s["reason_code"]) for s in a["evaluation"]["suppressed"]}
    d2 = world_forecast(lab / "b") if (lab / "b").mkdir() is None else None
    b = RP.alert_run(d2["state_dir"], config_path=d2["config"], alert_db=lab / "al2" / "a.sqlite", now=d2["now"], fixture_run=True,
                     registry_dir=d2["registry_dir"], extra_cal_cards=d2["extra"], policy=RP.make_alert_policy({"daily_cap_warning": 0}))
    assert [x["policy"] for x in b["evaluation"]["alerts"]] == ["reevaluate"]
    assert ("risk_override", "daily_cap") in {(s["policy"], s["reason_code"]) for s in b["evaluation"]["suppressed"]}
    # notices from earlier runs of the day never use the warnings' room
    con = AE.connect(lab / "al" / "a.sqlite")
    for i in range(10):
        con.execute("INSERT INTO alert_events(mode, dedupe_key, cooldown_key, policy, severity, item_id, label, created_at, local_day, status, "
                    "fixture, transports_json, alert_json, run_id) VALUES ('dry_run',?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (f"n{i}", f"c{i}", "reevaluate", "notice", "x", "x", d["now"], RP.AC.local_day(d["now"] + 7300, "America/New_York"),
                     "PREVIEW", 1, "[]", "{}", 1))
    con.commit()
    con.close()
    r = TI.persist(TI.result("NEWV", M3, T_FX + 7000, fatal=("NO_SELL_ROUTE",), status="REJECTED", score=0), lab)
    _pass([r], T_FX + 7200, lab, **TI.fx_kw(d["world"], lab, sleep=lambda s: None))
    c = _arun(d, lab, d["now"] + 7300)
    assert ("risk_override", "warning") in {(x["policy"], x["severity"]) for x in c["evaluation"]["alerts"]}


def test_g13_the_policy_is_validated_like_the_social_policy():
    c_pol = RP.make_alert_policy({"daily_cap": 5})
    assert c_pol["policies"]["risk_override"]["cooldown_hours"] == 6.0 and len(c_pol["policy_sha256"]) == 64
    for bad in ({"daily_cap": 51}, {"min_interval_minutes": 5}, {"trade_execution_impact": "auto"}, {"delivery": "telegram"},
                {"policies": {"risk_override": {"cooldown_hours": 0.5}}}, {"policies": {"risk_override": {"severity": "urgent"}}},
                {"order": 1}, {"tz": "Mars/Base"}):
        with pytest.raises(Exception):
            RP.make_alert_policy(bad)


def test_g13_a_cooldown_inside_six_hours_suppresses_the_second_warning(lab):
    d = world_forecast(lab)
    _arun(d, lab, d["now"])
    r = TI.persist(TI.result("FXC", M2, T_FX + 3000, liq=400000.0, mcap=8.0e6, vol=8.0e5, fatal=("CANNOT_EXIT_5K", "TOP10_GT_50PCT"),
                             status="REJECTED", score=62), lab)
    _pass([r], T_FX + 3600, lab, **TI.fx_kw(d["world"], lab, sleep=lambda s: None))
    b = _arun(d, lab, T_FX + 3600 + 3700)
    assert ("risk_override", "cooldown") in {(s["policy"], s["reason_code"]) for s in b["evaluation"]["suppressed"]}


def test_g13_quiet_hours_send_refused_and_paths_inside_the_repository_refused(lab):
    d = world_forecast(lab)
    quiet = T_FX + 3 * 3600 + 60                                      # 2026-10-29T23:01 New York time
    a = _arun(d, lab, quiet)
    assert a["evaluation"]["quiet_hours"] is True and a["evaluation"]["new"]
    with pytest.raises(RP.AlertRefused, match="no external delivery is approved"):
        _arun(d, lab, quiet, send=True)
    with pytest.raises(RP.AlertRefused):
        RP.alert_run(d["state_dir"], config_path=d["config"], alert_db=ROOT / "audits" / "x.sqlite", now=quiet)
    with pytest.raises(RP.AlertRefused):
        RP.alert_run(d["state_dir"], config_path=d["config"], alert_db=lab / "ok.sqlite", outbox=ROOT / "inbox" / "box", now=quiet)
    assert not (ROOT / "audits" / "x.sqlite").exists() and not (ROOT / "inbox" / "box").exists()


# ---------------------------------------------------------------- G14: alert rules (pure function)
def _opp(**kw) -> dict:
    o = {"chain": "solana", "mint": M1, "chain_text": "solana", "mint_text": M1, "symbol": "ABC", "changes": [],
         "snapshot": {"capture_time_utc": AB._iso(T_TODAY), "observed_at_utc": AB._iso(T_TODAY - 600), "input_state": "FRESH",
                      "snapshot_hash": "a" * 64},
         "execution": {"structural_veto": False, "veto_unknown": False, "fatal_flags": [], "backtest_veto": None,
                       "backtest_veto_reasons": [], "veto": False},
         "ids": {"request_record_id": "b" * 64, "pass_id": "c" * 64},
         "targets": [{"short": "T1_24h", "target": TI.T1, "status": "ABSTAIN", "reasons": ["MODEL_NOT_SELECTED"], "number": None,
                      "forecast_id": "fc_1", "record_id": "d" * 64, "registry": {"blocking": []}, "is_fixture": False}],
         "previous_targets": {}}
    for k, v in kw.items():
        if isinstance(v, dict) and isinstance(o.get(k), dict):
            o[k] = {**o[k], **v}
        else:
            o[k] = v
    return o


def _cands(opps, view=None, **kw):
    return RP.alert_candidates(view or {"state": "OK"}, opps, policy=RP.make_alert_policy(), now=T_TODAY + 60, **kw)


def test_g14_an_abstention_alone_never_alerts():
    c, s = _cands([_opp()])
    assert c == [] and s == []


@pytest.mark.parametrize("kw,fires", [
    ({"execution": {"structural_veto": True, "fatal_flags": ["CANNOT_EXIT_5K"], "veto": True}}, True),
    ({"execution": {"veto_unknown": True, "veto": True}}, True),
    ({"execution": {"backtest_veto": True, "backtest_veto_reasons": ["UNTRADEABLE"], "veto": True}}, True),
    ({"changes": ["liquidity -25.0%"]}, True),
    ({"changes": ["liquidity -20.0%"]}, True),
    ({"changes": ["liquidity -19.9%"]}, False),
    ({"changes": ["liquidity +40.0%"]}, False),
    ({"execution": {"backtest_veto": None}}, False),
])
def test_g14_risk_override_triggers_and_non_triggers(kw, fires):
    c, _ = _cands([_opp(**kw)])
    assert bool([x for x in c if x["policy"] == "risk_override"]) is fires
    if fires:
        assert c[0]["severity"] == "warning" and "No forecast clears it" in c[0]["reason"]


def test_g14_suppression_reasons_stale_fixture_and_identity():
    risky = {"execution": {"structural_veto": True, "fatal_flags": ["X"], "veto": True}}
    _, s = _cands([_opp(snapshot={"input_state": "INPUT_STALE"}, **risky)])
    assert [x["reason_code"] for x in s] == ["SOURCE_STALE"]
    _, s = _cands([_opp(snapshot={"capture_time_utc": AB._iso(T_TODAY - 2 * DAY)}, **risky)])
    assert [x["reason_code"] for x in s] == ["SOURCE_STALE"]
    tg = [dict(_opp()["targets"][0], is_fixture=True)]
    _, s = _cands([_opp(targets=tg, **risky)])
    assert [x["reason_code"] for x in s] == ["FIXTURE_IN_LIVE_RUN"]
    c, s = _cands([_opp(targets=tg, **risky)], fixture_run=True)
    assert len(c) == 1 and s == []
    _, s = _cands([_opp(mint_text="not-an-exact-address", **risky)])
    assert [x["reason_code"] for x in s] == ["NOT_EXACT_IDENTITY"]


def _forecast_target(lo, base, level="SHADOW", target=None, short="T1_24h"):
    return {"short": short, "target": target or TI.T1, "status": "FORECAST", "reasons": [], "forecast_id": "fc_f" + short, "record_id": "e" * 64,
            "registry": {"blocking": []}, "is_fixture": False,
            "number": {"probability": lo + 0.1, "interval": [lo, lo + 0.2], "base_rate": base, "level": level}}


def test_g14_reevaluate_only_for_a_verified_estimate_above_its_base_rate_and_never_beside_a_veto():
    c, _ = _cands([_opp(targets=[_forecast_target(0.41, 0.29)])])
    assert [x["policy"] for x in c] == ["reevaluate"] and c[0]["severity"] == "notice" and "re-evaluation only" in c[0]["reason"]
    assert _cands([_opp(targets=[_forecast_target(0.25, 0.29)])])[0] == []
    assert _cands([_opp(targets=[_forecast_target(0.41, 0.29, level="ABSTAIN")])])[0] == []
    c, s = _cands([_opp(targets=[_forecast_target(0.41, 0.29)], execution={"structural_veto": True, "fatal_flags": ["CANNOT_EXIT_5K"], "veto": True})])
    assert [x["policy"] for x in c] == ["risk_override"] and [x["reason_code"] for x in s] == ["RISK_OVERRIDES_FORECAST"]
    assert "overridden" in c[0]["reason"]
    c, _ = _cands([_opp(targets=[_forecast_target(0.41, 0.29, target=TI.T2, short="T2_24h")])])
    assert c[0]["severity"] == "warning"                               # an elevated drawdown estimate is a warning


def test_g14_forecast_withdrawn_and_pipeline_health():
    o = _opp(previous_targets={"T1_24h": "fc_old"})
    c, _ = _cands([o])
    assert [x["policy"] for x in c] == ["forecast_withdrawn"] and "withdrawn" in c[0]["reason"]
    tg = [dict(_opp()["targets"][0], registry={"blocking": ["MODEL_STALE"]})]
    c, _ = _cands([_opp(targets=tg)])
    assert [x["policy"] for x in c] == ["pipeline_health"] and "MODEL_STALE" in c[0]["reason"]
    c, _ = _cands([], view={"state": "STATE_TAMPERED"})
    assert [(x["policy"], x["severity"]) for x in c] == [("pipeline_health", "warning")]
    c, _ = _cands([], errors=[{"record_id": "f" * 64, "pass_id": "p", "errors": ["IntegrationError"]}])
    assert [(x["policy"], x["severity"]) for x in c] == [("pipeline_health", "notice")]


def test_g14_a_tampered_state_gives_one_pipeline_health_alert_and_nothing_else(lab):
    d = world_forecast(lab)
    p = d["state_dir"] / I.FILES["requests"]
    p.write_text(p.read_text() + "x")
    a = _arun(d, lab, d["now"])
    assert a["outcome"] == "feed_unavailable" and [x["policy"] for x in a["evaluation"]["alerts"]] == ["pipeline_health"]


def test_g14_an_error_event_in_a_new_pass_gives_a_pipeline_health_alert(lab, monkeypatch):
    d = world_forecast(lab)
    _arun(d, lab, d["now"])

    def boom(*a, **k):
        raise I.IntegrationError("fixture failure")
    monkeypatch.setattr(I, "_process", boom)
    _pass([TI.persist(TI.result("ERR", M3, T_FX + 7000), lab)], T_FX + 7200, lab, **TI.fx_kw(d["world"], lab, sleep=lambda s: None))
    monkeypatch.undo()
    b = _arun(d, lab, T_FX + 7300)
    assert ("pipeline_health", "notice") in {(x["policy"], x["severity"]) for x in b["evaluation"]["alerts"]}


def test_g14_withdrawn_in_a_real_state_after_a_rollback(lab):
    d = world_withdrawn(lab)
    a = _arun(d, lab, d["now"])
    assert "forecast_withdrawn" in [x["policy"] for x in a["evaluation"]["alerts"]]


# ---------------------------------------------------------------- G15: lab snapshot verification
def test_g15_a_lab_row_of_another_snapshot_is_never_used(lab):
    d = world_abstain(lab)
    r = TI.result("ABC", M1, T_TODAY + 100, score=99)
    r["modules"]["lifecycle"]["stage"] = "OTHERSTAGE"
    TI.persist(r, lab)                                                 # a later row of the same mint, never assessed
    v, text = report(d)
    o = next(o for o in v["opportunities"] if o["mint"] == M1)
    assert o["structural"]["score"] == 60 and "OTHERSTAGE" not in text
    con = sqlite3.connect(db.DB_PATH)
    con.execute("DELETE FROM theses WHERE mint=? AND score=60", (M1,))
    con.commit()
    con.close()
    v, text = report(d)
    o = next(o for o in v["opportunities"] if o["mint"] == M1)
    assert o["snapshot"]["lab_state"] == "SNAPSHOT_NOT_VERIFIED" and o["technical"] is None and o["symbol"] is None
    assert "OTHERSTAGE" not in text


# ---------------------------------------------------------------- G19: isolation (rule 14)
def _imports(p: Path) -> set[str]:
    out = set()
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n, ast.Import):
            out.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            out.add(("." * n.level) + (n.module or ""))
    return out


def test_g19_reports_imports_exactly_the_named_modules():
    p = ROOT / "memelab/predictive/reports.py"
    got = _imports(p)
    std = {"__future__", "argparse", "json", "math", "re", "sqlite3", "sys", "time", "datetime", "pathlib", "typing"}
    assert got <= std | {".", "..", "..report", "..social"}, got
    tree = ast.parse(p.read_text())
    rel1 = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level == 1 for a in n.names}
    assert rel1 == {"contract", "integration"}, rel1
    rel2 = {(n.module, a.name) for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level == 2 for a in n.names}
    assert rel2 == {("report", "_ev"), ("social", "alerts_core"), ("social", "alerts_engine"), ("social", "alerts_transport"), (None, "db")}, rel2
    txt = p.read_text()
    for banned in ("abstention", "calibration", "registry import", "onchain", "features", "baselines", "behavioral", "scenario_eval",
                   "evaluation", "analog", "socialcat", "technical", "memelab.backtest", "urllib", "socket", "requests", "http.client",
                   "phase_06/sealed", "holdout_labels"):
        assert f"import {banned}" not in txt and f"predictive.{banned}" not in txt, banned


def test_g19_the_integration_seam_allows_exactly_reports_and_a_negative_case_still_fails():
    import test_predictive_contract as TC
    users = sorted(p.name for p in (ROOT / "memelab/predictive").glob("*.py") if TC._relative_users(p.read_text(), "integration"))
    assert users == ["reports.py"]
    assert TC._relative_users("from . import stats, integration", "integration")


# ---------------------------------------------------------------- G20: CLI
def test_g20_the_cli_writes_a_report_and_a_json_view_and_refuses_a_path_in_the_repository(lab):
    d = world_abstain(lab)
    base = [sys.executable, "-m", "memelab.predictive.reports"]
    p = subprocess.run(base + ["report", "--state-dir", str(d["state_dir"]), "--config", str(d["config"]), "--lab-db", str(db.DB_PATH),
                               "--out", str(lab / "out" / "r.md")], cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "0 probabilities shown" in p.stdout and (lab / "out" / "r.md").read_text().startswith("# Predictive research report")
    p = subprocess.run(base + ["report", "--state-dir", str(d["state_dir"]), "--config", str(d["config"]), "--json"], cwd=ROOT,
                       capture_output=True, text=True)
    v = json.loads(p.stdout)
    assert v["state"] == "OK" and v["counts"]["probabilities_shown"] == 0
    p = subprocess.run(base + ["report", "--state-dir", str(d["state_dir"]), "--config", str(d["config"]), "--out",
                               str(ROOT / "audits" / "p18_should_not_exist.md")], cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 2 and not (ROOT / "audits" / "p18_should_not_exist.md").exists()
    p = subprocess.run(base + ["alerts", "--state-dir", str(d["state_dir"]), "--config", str(d["config"]), "--alert-db",
                               str(lab / "al" / "a.sqlite"), "--as-of", str(d["now"])], cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 0 and "Outcome: evaluated" in p.stdout and "nothing was sent to any device" in p.stdout
    p = subprocess.run(base + ["alerts", "--state-dir", str(d["state_dir"]), "--config", str(d["config"]), "--alert-db",
                               str(lab / "al" / "a.sqlite"), "--send"], cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 2 and "no external delivery is approved" in p.stderr
    p = subprocess.run(base + ["alerts-state", "--config", str(d["config"]), "--alert-db", str(lab / "al" / "a.sqlite")], cwd=ROOT,
                       capture_output=True, text=True)
    assert p.returncode == 0 and "Nothing has been sent to a device." in p.stdout


# ---------------------------------------------------------------- the real-state shape (property checks, no golden)
def test_the_abstain_world_alerts_fire_only_for_the_vetoed_token(lab):
    d = world_abstain(lab)
    a = _arun(d, lab, d["now"], fixture_run=False)
    assert [(x["policy"], x["label"].split(" ")[0]) for x in a["evaluation"]["alerts"]] == [("risk_override", "GOMOX")]
    codes = {(s["policy"], s["reason_code"]) for s in a["evaluation"]["suppressed"]}
    assert codes <= {("risk_override", "SOURCE_STALE")}


# ---------------------------------------------------------------- registry index cross-checks and the alert text check
def _registry_copy(tmp: Path, edit) -> Path:
    import shutil
    dst = tmp / "regcopy"
    shutil.copytree(ROOT / I.REGISTRY_DIR, dst)
    idx = json.loads((dst / "REGISTRY_INDEX.json").read_text())
    edit(idx)
    (dst / "REGISTRY_INDEX.json").write_text(json.dumps(idx))
    return dst


def test_an_index_whose_pin_differs_from_the_request_is_a_mismatch_and_shows_no_record(lab):
    d = world_abstain(lab)
    d["registry_dir"] = _registry_copy(lab, lambda idx: idx["targets"]["T1_24h"].update(event_id="0" * 64))
    v, text = report(d)
    assert "T1 24 h: REGISTRY_INDEX_MISMATCH" in text and "T1b 6 h: registry NO_VIABLE_CHAMPION, pin matches" in text


def test_an_index_of_another_log_is_not_used(lab):
    d = world_abstain(lab)
    d["registry_dir"] = _registry_copy(lab, lambda idx: idx.update(log_sha256="0" * 64))
    v, text = report(d)
    assert v["opportunities"][0]["registry_facts"]["state"] == "REGISTRY_INDEX_MISMATCH" and "pin matches" not in text


def test_an_alert_text_with_a_trade_word_is_refused():
    a = {"severity": "notice", "policy": "reevaluate", "label": "ABC on solana (x)", "reason": "buy it now", "bucket": "FACT",
         "dedupe_key": "0" * 32, "forecasts": [], "records": []}
    with pytest.raises(RP.ReportError):
        RP.render_alert_text(a, "America/New_York")
    a["reason"] = "a plain reason"
    assert RP.render_alert_text(a, "America/New_York").splitlines()[-1] == "Research only. Not a trade instruction, not a score, not a watchlist change."


def test_g10_absent_catalyst_tables_are_named_in_the_catalyst_section(lab):
    con = sqlite3.connect(db.DB_PATH)
    for t in ("catalyst_token_links", "catalyst_events"):
        con.execute(f"DROP TABLE IF EXISTS {t}")
    con.commit()
    con.close()
    rs = [TI.persist(TI.result("ABC", M1, T_TODAY - 600), lab)]
    _pass(rs, T_TODAY, lab)
    v, text = report({"state_dir": lab / "state", "config": TI.cfg(lab), "lab_db": db.DB_PATH, "registry_dir": None, "extra": None})
    assert v["opportunities"][0]["catalyst"]["source_status"] == "CATALYST_SOURCE_NOT_AVAILABLE"
    assert "UNKNOWN: catalyst evidence: CATALYST_SOURCE_NOT_AVAILABLE (the catalyst tables were not available to the pass)" in text


def test_g7_a_wider_forged_interval_is_refused_even_though_it_still_holds_the_support_interval(lab):
    d = world_forecast(lab)

    def widen(lines):
        for dl in lines["documents"]:
            if dl["document"]["prediction_status"] == "FORECAST":
                lo, hi = dl["document"]["uncertainty_interval"]
                dl["document"]["uncertainty_interval"] = [round(max(0.0, lo - 0.05), 6), hi]
                return
    reseal(d["state_dir"], widen)
    assert I.check_state(d["state_dir"], config_path=d["config"])["problems"] == []
    v, _ = report(d)
    ref = [t for o in v["opportunities"] for t in o["targets"] if t["status"] == "DOCUMENT_REFUSED"]
    assert len(ref) == 1 and "interval differs from the one stored with the raw number" in ref[0]["checks"] and v["counts"]["probabilities_shown"] == 0


def test_g7_a_document_moved_to_another_request_is_refused(lab):
    d = world_forecast(lab)
    _pass([TI.persist(TI.result("FXA", M1, T_FX - 600, liq=150000.0, mcap=3.0e6, vol=3.0e5), lab)], T_FX + 30, lab,
          **TI.fx_kw(d["world"], lab, sleep=lambda s: None))                  # a DUPLICATE request in a second pass

    def move(lines):
        dup = next(r for r in lines["requests"] if r["event"] == "DUPLICATE")
        for dl in lines["documents"]:
            if dl["document"]["prediction_status"] == "FORECAST" and dl["document"]["mint_address"] == M1:
                dl["pass_id"], dl["request_seq"] = dup["pass_id"], dup["seq"]
    reseal(d["state_dir"], move)
    v, text = report(d)
    o = next(o for o in v["opportunities"] if o["mint"] == M1)
    t1 = next(t for t in o["targets"] if t["short"] == "T1_24h")
    assert v["state"] == "STATE_CHECK_FAILED" and t1["status"] == "DOCUMENT_REFUSED" and t1["number"] is None


def test_g7_a_state_problem_that_names_no_document_refuses_every_document(lab):
    d = world_forecast(lab)

    def duplicate(lines):
        lines["documents"].append(copy.deepcopy(lines["documents"][0]))
    reseal(d["state_dir"], duplicate)
    assert "a forecast id appears twice" in I.check_state(d["state_dir"], config_path=d["config"])["problems"]
    v, text = report(d)
    assert v["state"] == "STATE_CHECK_FAILED" and v["counts"]["probabilities_shown"] == 0
    assert all(t["status"] == "DOCUMENT_REFUSED" for o in v["opportunities"] for t in o["targets"])


# ---------------------------------------------------------------- CP18-0 (PI-D-099): lab codes as codes, own details readable
def test_cp18_0_a_fatal_flag_whose_words_include_a_trade_word_is_shown_by_its_code_never_withheld(lab):
    rs = [TI.persist(TI.result("ABC", M1, T_TODAY - 600, fatal=("NO_SELL_ROUTE", "CANNOT_EXIT_5K"), status="REJECTED", score=0), lab)]
    _pass(rs, T_TODAY, lab)
    d = {"state_dir": lab / "state", "config": TI.cfg(lab), "lab_db": db.DB_PATH, "registry_dir": None, "extra": None, "now": T_TODAY + 60}
    v, text = report(d)
    o = v["opportunities"][0]
    assert sorted(o["execution"]["fatal_flags"]) == ["CANNOT_EXIT_5K", "NO_SELL_ROUTE"] and "withheld" not in json.dumps(o["execution"])
    assert "NO_SELL_ROUTE" in text.split("## At a glance")[1].split("## System status")[0]
    assert "fatal-flag veto: CANNOT_EXIT_5K, NO_SELL_ROUTE; no forecast clears it" in text or \
           "fatal-flag veto: NO_SELL_ROUTE, CANNOT_EXIT_5K; no forecast clears it" in text
    a = _arun(d, lab, d["now"], fixture_run=False)
    txt = next((lab / "al" / "outbox" / "preview").glob("alert_*.txt")).read_text()
    assert [x["policy"] for x in a["evaluation"]["alerts"]] == ["risk_override"] and "NO_SELL_ROUTE" in txt and "withheld" not in txt


def test_cp18_0_codes_keep_only_code_characters_and_own_details_stay_readable(lab):
    assert RP._code("NO_SELL_ROUTE") == "NO_SELL_ROUTE" and RP._code("a|b\n## x") == "ABX" and RP._code(None) == "UNKNOWN_CODE"
    assert len(RP._code("X" * 99)) == 40
    d = world_abstain(lab)
    _, text = report(d, lab_db=None)
    assert "SNAPSHOT_NOT_VERIFIED (no lab database given)" in text


# ---------------------------------------------------------------- CP18-1 (PI-D-100): measured changes labelled; refused line
def test_cp18_1_measured_market_changes_are_labelled_and_the_units_line_says_so(lab):
    d = world_abstain(lab)
    _pass([TI.persist(TI.result("ABC", M1, T_TODAY + 3000, liq=30000.0), lab)], T_TODAY + 3600, lab)    # liquidity -38.8%
    v, text = report(d)
    line = next(l for l in text.splitlines() if l.startswith("- FACT: exact identity") and M1 in l)
    assert "MATERIAL_CHANGE (measured market changes since the previous attempt, not probabilities: " in line and "liquidity -38.8%" in line
    assert "in measured market changes between two attempts of a token" in text
    t = re.sub(re.escape(RP.MEASURED_LABEL) + r": [^)]*\)", "", text)
    assert _numbers_outside_definitions(t) == []


def test_cp18_1_a_refused_target_line_reads_cleanly(lab):
    d = world_forecast(lab)
    reseal(d["state_dir"], forge_probability)
    _, text = report(d)
    assert "DOCUMENT_REFUSED: the document failed a check: it is not shown and no number is shown. Failed checks: probability differs" in text


# ---------------------------------------------------------------- repair pass 2 (CP18-2, PI-D-102): the skeptic's findings
def _vanity(word: str) -> str:
    base = TI.b58("vanity")
    m = "2" + base[1:20] + word + base[20 + len(word):]
    I.S.check_address("solana", m)
    return m


def test_rp2_m1_a_liquidity_fall_overrides_an_optimistic_forecast_in_the_report_and_the_alerts(lab):
    d = world_forecast(lab)
    _arun(d, lab, T_FX + 60)
    T2 = T_FX + 13 * 3600
    r2 = TI.persist(TI.result("FXA", M1, T2 - 600, liq=100000.0, mcap=3.0e6, vol=3.0e5), lab)        # liquidity -33%, no fatal flag
    _pass([r2], T2, lab, **TI.fx_kw(d["world"], lab, sleep=lambda s: None))
    v, text = report(d)
    fxa = next(o for o in v["opportunities"] if o["mint"] == M1)
    assert [r["code"] for r in fxa["risks"]] == [RP.LIQUIDITY_FALL] and not fxa["execution"]["veto"]
    row = next(l for l in text.splitlines() if M1 in l and l.startswith("| FXA"))
    assert "FORECAST OVERRIDDEN by risk (number withheld)" in row and RP.LIQUIDITY_FALL in row and "47%" not in row
    assert all(t["number"] is None for t in fxa["targets"])
    out = _arun(d, lab, T2 + 60)
    got = [(a["policy"], a["label"].split(" ")[0]) for a in out["evaluation"]["alerts"]]
    assert ("risk_override", "FXA") in got and ("reevaluate", "FXA") not in got
    assert ("reevaluate", "RISK_OVERRIDES_FORECAST") in {(s["policy"], s["reason_code"]) for s in out["evaluation"]["suppressed"]}
    txt = "".join(p.read_text() for p in (lab / "al" / "outbox" / "preview").glob("alert_*.txt"))
    assert "-33%" not in txt and f"{RP.LIQUIDITY_FALL} since the previous attempt" in txt          # minor 13: a code, no percent


def test_rp2_m2_a_reset_state_on_a_shared_alert_database_is_detected_reported_and_evaluated(lab):
    import shutil
    T = T_TODAY
    _pass([TI.persist(TI.result("ABC", M1, T - 600), lab)], T, lab)
    _pass([TI.persist(TI.result("ABC", M1, T + 2 * 3600 - 600, price=2.0), lab)], T + 2 * 3600, lab)
    _pass([TI.persist(TI.result("ABC", M1, T + 4 * 3600 - 600, price=4.0), lab)], T + 4 * 3600, lab)
    adb = lab / "al" / "a.sqlite"
    assert RP.alert_run(lab / "state", config_path=TI.cfg(lab), alert_db=adb, now=T + 4 * 3600 + 60)["outcome"] == "evaluated"
    shutil.rmtree(lab / "state")
    r = TI.persist(TI.result("GOMOX", M2, T + 6 * 3600 - 600, fatal=("CANNOT_EXIT_5K",), status="REJECTED", score=0), lab)
    _pass([r], T + 6 * 3600, lab)
    a = RP.alert_run(lab / "state", config_path=TI.cfg(lab), alert_db=adb, now=T + 6 * 3600 + 60)
    assert a["outcome"] == "evaluated" and "FEED_CHANGED" in a["reason"]
    pol = {(x["policy"], x["severity"]) for x in a["evaluation"]["alerts"]}
    assert ("risk_override", "warning") in pol and ("pipeline_health", "notice") in pol
    b = RP.alert_run(lab / "state", config_path=TI.cfg(lab), alert_db=adb, now=T + 8 * 3600)
    assert b["outcome"] == "no_new_upstream_data"                          # the feed is bound again


def test_rp2_m3_a_deferred_newer_snapshot_with_a_new_fatal_flag_is_shown_and_alerted_never_covered(lab):
    T = T_TODAY
    _pass([TI.persist(TI.result("ABC", M1, T - 600), lab)], T, lab)
    rs = [TI.persist(TI.result(f"Q{i}", TI.b58(f"q{i}"), T + 2 * 3600 - 600), lab) for i in range(3)]
    rs.append(TI.persist(TI.result("ABC", M1, T + 2 * 3600 - 600, fatal=("CANNOT_EXIT_5K",), status="REJECTED", score=0), lab))
    tick = iter(range(0, 10_000, 11))
    _pass(rs, T + 2 * 3600, lab, clock=lambda: float(next(tick)))
    v, text = report({"state_dir": lab / "state", "config": TI.cfg(lab), "lab_db": db.DB_PATH, "registry_dir": None, "extra": None})
    abc = next(o for o in v["opportunities"] if o["mint"] == M1)
    assert abc["newer_not_assessed"] and abc["newer_not_assessed"][0]["fatal_flags"] == ["CANNOT_EXIT_5K"]
    assert "CANNOT_EXIT_5K (newer)" in next(l for l in text.splitlines() if l.startswith("| ABC"))
    rows = [l for l in text.splitlines() if M1 in l and "DEFERRED" in l]
    assert rows and all("| yes |" not in r for r in rows) and all(RP.NEWER_NOT_ASSESSED in r for r in rows)
    out = RP.alert_run(lab / "state", config_path=TI.cfg(lab), alert_db=lab / "al" / "a.sqlite", now=T + 2 * 3600 + 60, lab_db=db.DB_PATH)
    assert any(a["policy"] == "risk_override" and a["label"].startswith("ABC") for a in out["evaluation"]["alerts"])
    # without the lab database the newer snapshot's flags are unknown and still alerted
    out2 = RP.alert_run(lab / "state", config_path=TI.cfg(lab), alert_db=lab / "al2" / "a.sqlite", now=T + 2 * 3600 + 60)
    assert any(a["policy"] == "risk_override" and M1 in a["label"] for a in out2["evaluation"]["alerts"])


@pytest.mark.parametrize("sym", ["SELLNOW", "BUYNOW", "TAKEPROFIT", "APEIN", "LONGNOW", "EXITNOW", "MOONSHOT", "PUMPIT", "100X",
                                 "StopLossCat", "x1000"])
def test_rp2_m4_cx_sk18_run_together_trade_words_in_token_text_are_withheld(sym):
    assert RP._token_text(sym) == "withheld"


def test_rp2_m4_cx_sk18_the_report_and_the_alert_never_print_a_run_together_trade_word(lab):
    syms = ["SELLNOW", "BUYNOW", "TAKEPROFIT", "APEIN"]
    rs = [TI.persist(TI.result(s, TI.b58(f"cx{i}"), T_TODAY - 600, fatal=("CANNOT_EXIT_5K",) if i == 0 else (),
                               status="REJECTED" if i == 0 else "WATCH"), lab) for i, s in enumerate(syms)]
    _pass(rs, T_TODAY, lab)
    v, text = report({"state_dir": lab / "state", "config": TI.cfg(lab), "lab_db": db.DB_PATH, "registry_dir": None, "extra": None})
    for s in syms:
        assert s not in text and s.lower() not in text.lower().replace("withheld", "")
    RP.alert_run(lab / "state", config_path=TI.cfg(lab), alert_db=lab / "al" / "a.sqlite", now=T_TODAY + 60, lab_db=db.DB_PATH)
    txt = "".join(p.read_text() for p in (lab / "al" / "outbox" / "preview").glob("alert_*.txt"))
    assert "SELLNOW" not in txt and "withheld on solana" in txt
    assert RP._token_text("ABC") == "ABC" and RP._token_text("PEPE") == "PEPE"


def test_rp2_minor7_a_vanity_mint_with_a_trade_word_never_blocks_the_report(lab):
    m = _vanity("1profit2")
    _pass([TI.persist(TI.result("ABC", M1, T_TODAY - 600), lab), TI.result("VAN", m, T_TODAY - 600)], T_TODAY, lab)
    v = RP.build(lab / "state", config_path=TI.cfg(lab), lab_db=db.DB_PATH)
    text = RP.render(v)
    assert m in text


def test_rp2_minor8_a_clock_behind_the_last_evaluation_is_said_and_not_too_soon(lab):
    d = world_abstain(lab)
    adb = lab / "al" / "a.sqlite"
    assert RP.alert_run(d["state_dir"], config_path=d["config"], alert_db=adb, now=d["now"] + DAY)["outcome"] == "evaluated"
    b = RP.alert_run(d["state_dir"], config_path=d["config"], alert_db=adb, now=d["now"])
    assert b["outcome"] == "no_new_upstream_data" and "CLOCK_BEHIND" in b["reason"]


def test_rp2_minor9_liquidity_that_became_unknown_is_a_risk(lab):
    T = T_TODAY
    _pass([TI.persist(TI.result("ABC", M1, T - 600), lab)], T, lab)
    _pass([TI.persist(TI.result("ABC", M1, T + 2 * 3600 - 600, liq=None), lab)], T + 2 * 3600, lab)
    out = RP.alert_run(lab / "state", config_path=TI.cfg(lab), alert_db=lab / "al" / "a.sqlite", now=T + 2 * 3600 + 60)
    assert any(a["policy"] == "risk_override" for a in out["evaluation"]["alerts"])
    v, text = report({"state_dir": lab / "state", "config": TI.cfg(lab), "lab_db": db.DB_PATH, "registry_dir": None, "extra": None})
    assert RP.LIQUIDITY_UNKNOWN in next(l for l in text.splitlines() if l.startswith("| ABC"))


def test_rp2_minor10_the_alert_database_is_never_a_lab_database(lab):
    d = world_abstain(lab)
    for bad in (db.DB_PATH, lab / "copy.sqlite"):
        if bad != db.DB_PATH:
            import shutil
            shutil.copy(db.DB_PATH, bad)
        with pytest.raises(RP.AlertRefused):
            RP.alert_run(d["state_dir"], config_path=d["config"], alert_db=bad, now=d["now"], lab_db=bad)
    with pytest.raises(RP.AlertRefused, match="other tables"):
        RP.alert_run(d["state_dir"], config_path=d["config"], alert_db=lab / "copy.sqlite", now=d["now"])


def test_rp2_minor5_the_report_no_longer_claims_it_recomputes_the_point(lab):
    _, text = report(world_abstain(lab))
    assert "must equal the point recomputed" not in text and "without recomputing it" in text


def test_rp2_minor6_x1_a_token_row_of_another_chain_is_not_used(lab):
    d = world_abstain(lab)
    con = sqlite3.connect(db.DB_PATH)
    con.execute("UPDATE tokens SET chain='bsc' WHERE mint=?", (M1,))
    con.commit()
    con.close()
    v, _ = report(d)
    o = next(o for o in v["opportunities"] if o["mint"] == M1)
    assert o["symbol"] is None and o["snapshot"]["token_age_s"] is None


def test_rp2_minor6_x3_x10_unknown_veto_and_backtest_veto_reasons_are_shown(lab):
    d = world_abstain(lab)

    def edit(lines):
        for r in lines["requests"]:
            if r.get("event") == "DISCOVERY" and r["mint"] == M1:
                ds = r["decision_support"]
                ds["veto_unknown"] = True
                ds["backtest_veto"] = {"veto": True, "reasons": ["UNTRADEABLE"]}
                ds["veto"] = True
                ds["structural_veto"] = dict(ds["structural_veto"], veto=None)
    reseal(d["state_dir"], edit)
    v, text = report(d)
    row = next(l for l in text.splitlines() if l.startswith("| ABC"))
    assert "unknown" in row and "backtest veto" in row
    sec = text.split("## ABC")[1].split("### Behavioral")[0]
    assert "backtest veto UNTRADEABLE" in sec
    # the backtest line itself names the reasons, not only the risk list (X10 after CP18-2)
    assert any("backtest:" in l and "; backtest veto UNTRADEABLE" in l for l in sec.splitlines()), sec


def test_rp2_minor6_x4_x5_a_status_outside_the_vocabulary_and_a_raw_change_string_are_reduced(lab):
    d = world_abstain(lab)

    def edit(lines):
        for r in lines["requests"]:
            if r.get("event") == "DISCOVERY" and r["mint"] == M1:
                r["material"]["status"] = "MOON|SOON"
                r["changes"] = ["## injected | cell"]
    reseal(d["state_dir"], edit)
    _, text = report(d)
    assert "MOON|SOON" not in text and "## injected" not in text and "| cell" not in text
