"""Phase 18 probes for report-1 and alerts-rules-1 (research only; no network; never writes a tracked file unless asked to
write the golden files).

    python -B run_reports.py goldens OUTDIR
        The golden texts of tests/test_predictive_reports.py (format-only fixture worlds, fixed clocks), written to OUTDIR.
        To refresh the committed goldens: OUTDIR = tests/fixtures/predictive/phase18/golden (a deliberate, reviewed step).
    python -B run_reports.py real SMOKE_OUT REPLAY_OUT OUTDIR
        The real-data runs: report-1 over the Phase 17 real-path smoke state (with the sandbox lab database of the flag-on run)
        and over the Phase 17 export replay state, then dry-run alerts over both at the newest capture plus 60 s. Writes the
        reports and the run outputs to OUTDIR and REAL_RUN_CHECKS.json (counts, reasons, properties; no local path).

Pre-registration: ../ACCEPTANCE_CHECKLIST.md, PI-D-098. An audit hook refuses sockets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

SOCKETS: list[str] = []


def _hook(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        SOCKETS.append(event)
        raise RuntimeError(f"Phase 18 probe makes no network call ({event})")


sys.addaudithook(_hook)

from memelab.predictive import abstention as AB  # noqa: E402
from memelab.predictive import integration as I  # noqa: E402
from memelab.predictive import reports as RP  # noqa: E402
from memelab.social import alerts_engine as AE  # noqa: E402

PCT = re.compile(r"\d+(\.\d+)?\s*%")


def goldens(out: Path) -> dict:
    import pytest  # noqa: F401  (the test module imports it)
    import test_predictive_reports as T
    from memelab import db
    old = (db.DB_PATH, db.DATA_DIR)
    tmp = Path(tempfile.mkdtemp(prefix="p18_gold_"))
    try:
        texts = T.golden_texts(tmp)
    finally:
        db.DB_PATH, db.DATA_DIR = old
        shutil.rmtree(tmp, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    for name, text in sorted(texts.items()):
        (out / name).write_text(text)
    return {name: hashlib.sha256(t.encode()).hexdigest() for name, t in sorted(texts.items())}


def _cfg(tmp: Path) -> Path:
    p = tmp / "cfg_on.json"
    p.write_text('{"predictive": {"enabled": true}}\n')
    return p


def _newest_capture(state: Path) -> float:
    return max(json.loads(x)["capture_time"] for x in (state / I.FILES["requests"]).read_text().splitlines())


def _checks(view: dict, text: str) -> dict:
    t = text.replace("rises 25% before it falls 15%", "")
    for o in view["opportunities"]:
        t = t.replace(o["mint"], "")
    reasons = Counter(r for o in view["opportunities"] for x in o["targets"] for r in x.get("reasons") or [])
    return {"state": view["state"], "counts": view["counts"], "format_only": view["format_only"],
            "reason_counts": dict(sorted(reasons.items())),
            "statuses": dict(Counter(x["status"] for o in view["opportunities"] for x in o["targets"])),
            "input_states": dict(Counter(o["snapshot"]["input_state"] for o in view["opportunities"])),
            "lab_states": dict(Counter(o["snapshot"]["lab_state"] for o in view["opportunities"])),
            "vetoes": sorted({f for o in view["opportunities"] for f in o["execution"]["fatal_flags"]}),
            "veto_opportunities": sum(1 for o in view["opportunities"] if o["execution"]["veto"]),
            "backtest_results": sorted({o["execution"]["backtest_result"] for o in view["opportunities"]}),
            "not_attempted_events": dict(Counter(r["event"] for r in view["not_attempted"])),
            "percent_or_fraction_outside_definitions": len(PCT.findall(t)) + len(re.findall(r"(?<![\w.])0\.\d+", t)),
            "simulation_lines": text.count("SIMULATION_NOT_AVAILABLE"),
            "backtest_not_available_lines": text.count("BACKTEST_NOT_AVAILABLE"),
            "local_path": bool(RP.LOCAL_PATH.search(t)),
            "trading_word": not RP._plain(t),
            "sha256": hashlib.sha256(text.encode()).hexdigest(), "lines": text.count("\n")}


def _alerts(state: Path, cfg: Path, tmp: Path, name: str, lab_db: Path | None) -> dict:
    now = _newest_capture(state) + 60.0
    adb = tmp / f"alerts_{name}" / "alerts.sqlite"
    out = RP.alert_run(state, config_path=cfg, alert_db=adb, now=now, lab_db=lab_db)
    con = AE.connect(adb)
    try:
        view = AE.state_view(con)
        ledger = [dict(r) for r in con.execute("SELECT transport, status FROM alert_deliveries")]
    finally:
        con.close()
    previews = sorted((adb.parent / "outbox" / "preview").glob("alert_*.txt")) if (adb.parent / "outbox" / "preview").exists() else []
    texts = "".join(f"----- {p.name}\n{p.read_text()}" for p in previews)
    sent = adb.parent / "outbox" / "sent"
    return {"now_utc": AB._iso(now), "outcome": out["outcome"], "candidates": out["evaluation"]["candidates"],
            "new": len(out["evaluation"]["new"]), "deduped": out["evaluation"]["deduped"],
            "alerts": [{"policy": a["policy"], "severity": a["severity"], "fixture": a["fixture"]} for a in out["evaluation"]["alerts"]],
            "alert_policies": dict(Counter(a["policy"] for a in out["evaluation"]["alerts"])),
            "suppressed": dict(Counter(f"{s['policy']}:{s['reason_code']}" for s in out["evaluation"]["suppressed"])),
            "ledger": dict(Counter(f"{x['transport']}:{x['status']}" for x in ledger)),
            "remote_deliveries_succeeded": view["remote_deliveries_succeeded"], "sent_folder_exists": sent.exists(),
            "previews": len(previews), "run_text": AE.render_run(out, "America/New_York"), "preview_texts": texts}


def real(smoke: Path, replay: Path, out: Path) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="p18_real_"))
    cfg = _cfg(tmp)
    out.mkdir(parents=True, exist_ok=True)
    res: dict = {"probe": "run_reports.py real", "socket_events": None}
    lab = smoke / "runs" / "frozen_on" / "lab.sqlite"
    v = RP.build(smoke / "state", config_path=cfg, lab_db=lab)
    text = RP.render(v)
    (out / "REAL_SCOUT_REPORT.md").write_text(text)
    res["scout_report"] = _checks(v, text)
    v2 = RP.build(replay / "state_replay", config_path=cfg)
    text2 = RP.render(v2)
    (out / "REAL_REPLAY_REPORT.md").write_text(text2)
    res["replay_report"] = _checks(v2, text2)
    a1 = _alerts(smoke / "state", cfg, tmp, "scout", lab)
    a2 = _alerts(replay / "state_replay", cfg, tmp, "replay", None)
    for name, a in (("scout", a1), ("replay", a2)):
        (out / f"REAL_ALERTS_{name.upper()}_DRY_RUN.txt").write_text(a.pop("run_text") + "\n" + (a.pop("preview_texts") or "(no preview)\n"))
        res[f"{name}_alerts"] = a
    res["state_files_sha256"] = {f"{n}/{f}": AB.file_sha(d / f) for n, d in (("smoke", smoke / "state"), ("replay", replay / "state_replay"))
                                 for f in I.FILES.values()}
    res["socket_events"] = len(SOCKETS)
    blob = json.dumps(res, indent=1, sort_keys=True, default=str)
    if RP.LOCAL_PATH.search(blob):
        raise SystemExit("a local path would be written into the checks")
    (out / "REAL_RUN_CHECKS.json").write_text(blob + "\n")
    shutil.rmtree(tmp, ignore_errors=True)
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("goldens")
    p.add_argument("out")
    p = sp.add_parser("real")
    p.add_argument("smoke")
    p.add_argument("replay")
    p.add_argument("out")
    a = ap.parse_args()
    if a.cmd == "goldens":
        print(json.dumps(goldens(Path(a.out)), indent=1))
    else:
        r = real(Path(a.smoke), Path(a.replay), Path(a.out))
        print(json.dumps({k: (r[k]["counts"] if k.endswith("report") else {x: r[k][x] for x in ("outcome", "new", "suppressed")})
                          for k in ("scout_report", "replay_report", "scout_alerts", "replay_alerts")} | {"socket_events": r["socket_events"]},
                         indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
