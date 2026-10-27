"""Phase 17 probes for integration-1 (research only; no network; never writes a tracked file).

    python -B run_integration.py replay OUTDIR [--ref 71fc50e1eb86d916034bb0285a466cf2ec1cc4d0]
        The decision events of the prospective window (decision time from 2026-10-24T00:00Z) of the state-export history on
        origin/main up to REF, through the integration core, one pass per export commit at its commit time (EXPORT_COMMIT basis,
        research mode: capture-store features and internal B0 and B2 reference records), then the same replay again on the same
        state (expected: no new document). Writes OUTDIR/state_replay/ (scratch) and OUTDIR/REAL_EXPORT_REPLAY.json.
    python -B run_integration.py summarize STATE_DIR REPORT_DIR OUTJSON
        Counts, events, reasons and checks of a sandbox scout run (no number is copied out: hashes and counts only).
    python -B run_integration.py fixture OUTDIR
        The fixture path of the tests (scout command -> section) with a fixture champion: TEST_ONLY evidence.

Pre-registration: ../ACCEPTANCE_CHECKLIST.md, PI-D-093. No label, no holdout, no vendor call: an audit hook refuses sockets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

SOCKETS: list[str] = []


def _hook(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        SOCKETS.append(event)
        raise RuntimeError(f"Phase 17 probe makes no network call ({event})")


sys.addaudithook(_hook)

from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import decisions as D  # noqa: E402
from memelab.predictive import integration as I  # noqa: E402
from memelab.predictive import sources as SRC  # noqa: E402

REF = "71fc50e1eb86d916034bb0285a466cf2ec1cc4d0"
P0 = C.parse_utc(C.ACCEPTANCE["prospective_from_utc"])


def sha_file(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def _synth(e: dict, row: dict, tok: dict | None) -> dict:
    """A trigger built from an export decision row (the row is the decision snapshot itself)."""
    ff = row.get("fatal_flags_json")
    try:
        ff = json.loads(ff) if isinstance(ff, str) else ff
    except ValueError:
        ff = None
    snap = D._snap(row)
    return {"mint": e["mint"], "bundle": {"chain": e["chain"], "observed_at": float(row["created_at"]),
                                          "identity": {"symbol": (tok or {}).get("symbol")}},
            "score": {"total": row.get("score"), "fatal_flags": ff if isinstance(ff, list) else None},
            "status": {"status": row.get("status")}, "snapshot": snap, "report_path": None}


def replay(out: Path, ref: str) -> dict:
    t0 = time.time()
    exports = SRC.export_versions(REPO, ref)
    cands = D.candidates(exports)
    row_of = {(c["mint"], c["created_at"], c["row_sha256"]): c["row"] for c in cands}
    tok_at = {(ex["commit"], k["mint"]): k for ex in exports for k in ex.get("tokens") or []}
    evs = D.decisions(cands)
    seen: dict[str, int] = {}
    prior: dict[tuple, int] = {}
    for e in sorted(evs, key=lambda e: (e["decision_time"], e["mint"])):
        prior[(e["mint"], e["decision_time"])] = seen.get(e["mint"], 0)
        seen[e["mint"]] = seen.get(e["mint"], 0) + 1
    win = [e for e in evs if e["decision_time"] >= P0]
    by_commit: dict[str, list[dict]] = {}
    for e in sorted(win, key=lambda e: (e["decision_time"], e["mint"])):
        by_commit.setdefault(e["commit"], []).append(e)
    tmp = Path(tempfile.mkdtemp(prefix="p17_cfg_"))
    cfg = tmp / "config.json"
    cfg.write_text(json.dumps({"predictive": {"enabled": True}}))
    state = out / "state_replay"
    rounds = []
    for rnd in (1, 2):
        passes = []
        for commit, lst in by_commit.items():
            results, rows = [], []
            for e in lst:
                row = row_of[(e["mint"], e["created_at"], e["row_sha256"])]
                assert D.row_sha256(row) == e["row_sha256"]
                tok = tok_at.get((commit, e["mint"]))
                results.append(_synth(e, row, tok))
                rows.append({"row": row, "token": tok, "decision_time": e["decision_time"], "basis": "EXPORT_COMMIT",
                             "earlier": prior[(e["mint"], e["decision_time"])], "sharing": e["rows_sharing_key"]})
            s = I.run_pass(results, capture_time=float(lst[0]["decision_time"]), source="export_replay", state_dir=state,
                           config_path=cfg, mode="research", decision_rows=rows,
                           report_refs={"export_commit": commit, "export_path": "data/state/latest.json"})
            assert s is not None and s["state"] == "OK" and s["persisted"], s.get("errors")
            passes.append({"commit": commit[:12], "decision_time_utc": I._iso(lst[0]["decision_time"]),
                           "events": s["metrics"]["events"], "event_counts": s["metrics"]["event_counts"],
                           "documents": s["metrics"]["documents"], "forecasts": s["metrics"]["completed_forecasts"],
                           "references": s["metrics"]["reference_records"], "registry_modes": sorted({v["mode"] for v in
                                                                                                    s["registry"]["targets"].values()})})
        rounds.append(passes)
    m = I.metrics(state)
    chk = I.check_state(state, config_path=cfg)
    docs = [json.loads(x) for x in (state / I.FILES["documents"]).read_text().splitlines()]
    recs = [json.loads(x) for x in (state / I.FILES["records"]).read_text().splitlines()]
    reqs = [json.loads(x) for x in (state / I.FILES["requests"]).read_text().splitlines()]
    rp = state / I.FILES["references"]
    refs = [json.loads(x) for x in rp.read_text().splitlines()] if rp.exists() else []     # none before the registry's pins
    att = [r for r in reqs if r["event"] in I.ATTEMPTED]
    r1 = Counter(e for p in rounds[0] for e, n in p["event_counts"].items() for _ in range(n))
    r2 = Counter(e for p in rounds[1] for e, n in p["event_counts"].items() for _ in range(n))
    out_doc = {
        "probe": "run_integration.py replay", "ref": ref, "exports_read": len(exports),
        "decision_events_total": len(evs), "window_from_utc": C.ACCEPTANCE["prospective_from_utc"],
        "window_decision_events": len(win), "window_commits": len(by_commit),
        "round_1_events": dict(sorted(r1.items())), "round_2_events": dict(sorted(r2.items())),
        "round_1_documents": sum(p["documents"] for p in rounds[0]), "round_2_documents": sum(p["documents"] for p in rounds[1]),
        "documents": len(docs), "records": len(recs), "requests": len(reqs), "reference_records": len(refs),
        "forecast_documents": sum(1 for d in docs if d["document"]["prediction_status"] == "FORECAST"),
        "probabilities_published": sum(1 for d in docs if d["document"]["probability"] is not None),
        "model_ids": sorted({d["document"]["model_id"] for d in docs}),
        "backtest_status": sorted({d["document"]["backtest_status"] for d in docs}),
        "reason_counts": m["reason_counts"], "registry_modes": sorted({x for p in rounds[0] for x in p["registry_modes"]}),
        "pin_reasons_seen": sorted({x for r in att for t in r["targets"] for x in t["registry"]["pin_reasons"]}),
        "every_document_has_its_record": chk["problems"] == [] and len(docs) == len(recs),
        "check_state_problems": chk["problems"][:5],
        "unique_forecast_ids": len({d["forecast_id"] for d in docs}) == len(docs),
        "documents_equal_three_per_attempt": len(docs) == 3 * len(att),
        "attempted_events": len(att), "attempted_mints": len({r["mint"] for r in att}),
        "references_are_internal": all(x["reference_record"]["published"] is False for x in refs),
        "reference_numbers_sha256": hashlib.sha256(json.dumps(sorted([x["reference_record"]["entry_id"][:12],
                                                                      x["reference_record"]["decision_key"][:12],
                                                                      x["reference_record"]["raw_number"]] for x in refs),
                                                              sort_keys=True).encode()).hexdigest(),
        "reference_numbers_note": "B0 and B2 raw numbers are internal records for the Phase 19 comparison; only their hash is kept here",
        "feature_scope": sorted({(r.get("features") or {}).get("scope") or "NONE" for r in att}),
        "latency_ms_p50": m["latency_ms_p50"], "latency_ms_max": m["latency_ms_max"],
        "socket_events": len(SOCKETS), "wall_s": round(time.time() - t0, 2),
        "files_sha256": {k: sha_file(state / f) for k, f in I.FILES.items()},
        "passes_round_1": rounds[0],
    }
    (out / "REAL_EXPORT_REPLAY.json").write_text(json.dumps(out_doc, indent=1, sort_keys=True) + "\n")
    return out_doc


def summarize(state: Path, reports: Path, outjson: Path) -> dict:
    m = I.metrics(state)
    chk = I.check_state(state)
    reqs = [json.loads(x) for x in (state / I.FILES["requests"]).read_text().splitlines()]
    docs = [json.loads(x) for x in (state / I.FILES["documents"]).read_text().splitlines()]
    scout = sorted(reports.glob("*_SCOUT.md"))
    sec = scout[-1].read_text() if scout else ""
    i = sec.find("## Predictive research section")
    out = {"metrics": m, "check_state_problems": chk["problems"], "requests": len(reqs), "documents": len(docs),
           "events": [{"mint": r["mint"], "event": r["event"], "snapshot": (r.get("snapshot_hash") or "")[:12],
                       "staleness": (r.get("staleness") or {}).get("state"), "eligibility": (r.get("eligibility") or {}).get("state"),
                       "veto": (r.get("decision_support") or {}).get("veto"),
                       "size_basis": ((r.get("decision_support") or {}).get("size_cap") or {}).get("basis"),
                       "backtest": (r.get("backtest") or {}).get("result"),
                       "targets": [{"target": t["target"], "status": t["prediction_status"], "reasons": t["reasons"],
                                    "registry_mode": t["registry"]["mode"], "model_id": t["model_id"]} for t in r.get("targets") or []]}
                      for r in reqs],
           "probabilities_published": sum(1 for d in docs if d["document"]["probability"] is not None),
           "section_present": i >= 0, "section_sha256": hashlib.sha256(sec[i:].encode()).hexdigest() if i >= 0 else None,
           "section_lines": sec[i:].count("\n") if i >= 0 else 0, "files_sha256": {k: sha_file(state / f) for k, f in I.FILES.items()}}
    outjson.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return out


def _tables(path: Path) -> dict:
    import sqlite3
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    out = {}
    for t in ("tokens", "theses", "entries", "watchlist", "rejections"):
        rows = [{k: r[k] for k in r.keys() if not (t == "tokens" and k in ("first_seen_at", "last_seen_at"))}
                for r in con.execute(f"SELECT * FROM {t} ORDER BY rowid")]
        out[t] = hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()
    con.close()
    return out


def smoke(out: Path, outjson: Path) -> dict:
    """Compare the sandbox runs of real_path_smoke.sh; hashes, counts and booleans only."""
    runs = {}
    for ln in (out / "logs" / "runs.txt").read_text().splitlines():
        parts = ln.split()
        runs[parts[0] if parts[0] not in ("status", "check") else f"{parts[0]}_{parts[1]}"] = int(parts[parts.index("exit") + 1])
    def files(name):
        d = out / "runs" / name
        return {p.name: p.read_bytes() for p in sorted(d.glob("*.md"))}
    base, off, on = files("base_off"), files("frozen_off"), files("frozen_on")
    sc = [k for k in base if k.endswith("_SCOUT.md")][0]
    tables = {n: _tables(out / "runs" / n / "lab.sqlite") for n in ("base_off", "frozen_off", "frozen_on", "rerun", "retry")}
    st = {s: json.loads((out / "logs" / f"status_{s}.json").read_text())["metrics"] for s in ("state", "state_storm", "state_research", "state_analyze")}
    ck = {s: json.loads((out / "logs" / f"check_{s}.json").read_text()) for s in ("state", "state_storm", "state_research", "state_analyze")}
    on_text, base_text = on[sc].decode(), base[sc].decode()
    sec = on_text[len(base_text):]
    res = {
        "exit_codes": runs,
        "base_vs_frozen_off_all_reports_byte_equal": base == off,
        "reports_compared": len(base),
        "frozen_on_token_reports_byte_equal_to_base": {k: v for k, v in on.items() if k != sc} == {k: v for k, v in base.items() if k != sc},
        "frozen_on_scout_is_base_plus_appended_section": on_text.startswith(base_text) and sec.startswith("\n## Predictive research section"),
        "lab_tables_sha256": tables,
        "lab_tables_equal_base_off_frozen_off_frozen_on": tables["base_off"] == tables["frozen_off"] == tables["frozen_on"],
        "states": st, "checks": ck,
        "section_sha256": hashlib.sha256(sec.encode()).hexdigest(), "section_abstain_lines": sec.count(": ABSTAIN ("),
        "section_forecast_lines": sec.count(": FORECAST;"),
        "analyze_line": [l for l in (out / "logs" / "analyze_on.stdout").read_text().splitlines() if l.startswith("predictive:")],
        "sandbox_tracked_changes_after_scout_runs": {n: [l for l in (out / "logs" / f"{n}.git_status").read_text().splitlines()
                                                         if not l.startswith("!!")]
                                                     for n in ("base_off", "frozen_off", "frozen_on", "rerun", "retry", "storm", "research")},
        "sandbox_tracked_changes_after_analyze": (out / "logs" / "analyze_on.git_status").read_text().splitlines(),
        "sandbox_final_tracked_changes": (out / "logs" / "final_git_status_tracked.txt").read_text().splitlines(),
        "checkout_status": (out / "logs" / "checkout_git_status.txt").read_text().splitlines(),
        "latest_export_sha256": (out / "logs" / "latest_export.sha256").read_text().split()[0],
    }
    outjson.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    (outjson.parent / "REAL_SCOUT_SECTION.md").write_text(sec.replace(str(out), "OUTDIR"))
    return res


TRACE_SCOUT = {"PAID": "98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump", "GOMO": "9XKzy4KahcZaGJPJtz1PtqGPB3CiseoBrx7TcQhEpump"}
TRACE_REPLAY_PREFIX = "0x3d4f0513"


def _docs_and_records(state: Path) -> tuple[dict, dict]:
    docs = {json.loads(x)["forecast_id"]: json.loads(x) for x in (state / I.FILES["documents"]).read_text().splitlines()}
    recs = {json.loads(x)["record_id"]: json.loads(x) for x in (state / I.FILES["records"]).read_text().splitlines()}
    return docs, recs


def _trace_request(r: dict, docs: dict, recs: dict) -> dict:
    out = {"request_seq": r["seq"], "request_record_id": r["record_id"], "event": r["event"], "changes": r.get("changes"),
           "chain": r["chain"], "mint": r["mint"], "snapshot_hash": r["snapshot_hash"], "decision_time_utc": r["decision_time_utc"],
           "decision_time_basis": r["decision_time_basis"], "staleness": (r.get("staleness") or {}).get("state"),
           "veto": (r.get("decision_support") or {}).get("structural_veto"), "size_basis":
           ((r.get("decision_support") or {}).get("size_cap") or {}).get("basis"), "backtest": (r.get("backtest") or {}).get("result"),
           "targets": []}
    for t in r.get("targets") or []:
        d = docs[t["forecast_id"]]
        rec = recs[d["abstention_record_id"]]
        out["targets"].append({"target": t["target"], "forecast_id": t["forecast_id"], "abstention_record_id": rec["record_id"],
                               "prediction_status": d["document"]["prediction_status"], "probability": d["document"]["probability"],
                               "reasons": rec["reasons"], "model_id": d["document"]["model_id"],
                               "registry_mode": t["registry"]["mode"], "pin_reasons": t["registry"]["pin_reasons"],
                               "document_checks": I.pair_errors(d["document"], rec) + C.validate(d["document"])})
    return out


def trace(smoke_out: Path, replay_out: Path, outjson: Path) -> dict:
    import sqlite3
    ex = []
    state = smoke_out / "state"
    docs, recs = _docs_and_records(state)
    reqs = [json.loads(x) for x in (state / I.FILES["requests"]).read_text().splitlines()]
    scout_md = sorted((smoke_out / "runs" / "frozen_on").glob("*_SCOUT.md"))[0].read_text()
    con = sqlite3.connect(smoke_out / "runs" / "frozen_on" / "lab.sqlite")
    con.row_factory = sqlite3.Row
    for sym, mint in TRACE_SCOUT.items():
        r = next(x for x in reqs if x["mint"] == mint and x["event"] in I.ATTEMPTED)
        row = dict(con.execute("SELECT * FROM theses WHERE mint=? ORDER BY id DESC LIMIT 1", (mint,)).fetchone())
        t = _trace_request(r, docs, recs)
        t.update(example=f"scout ON, {sym}", source="python -m memelab scout (sandbox, flag on)",
                 thesis_row={"created_at_utc": I._iso(row["created_at"]), "status": row["status"], "score": row["score"],
                             "row_sha256_recomputed_from_the_lab_database": D.row_sha256(row)},
                 snapshot_hash_equals_row_sha256=D.row_sha256(row) == r["snapshot_hash"],
                 token_report=Path(r["report_refs"]["token_report"]).name,
                 token_report_named_in_section=Path(r["report_refs"]["token_report"]).name in scout_md,
                 record_ids_in_section=all(x["abstention_record_id"][:12] in scout_md for x in t["targets"]))
        ex.append(t)
    con.close()
    rstate = replay_out / "state_replay"
    docs, recs = _docs_and_records(rstate)
    reqs = [json.loads(x) for x in (rstate / I.FILES["requests"]).read_text().splitlines()]
    chain = [x for x in reqs if x["mint"].startswith(TRACE_REPLAY_PREFIX) and x["source"] == "export_replay"]
    attempts = [x for x in chain if x["event"] in I.ATTEMPTED]
    rows = []
    for x in attempts:
        commit = x["report_refs"]["export_commit"]
        doc = json.loads(SRC._git(REPO, "show", f"{commit}:data/state/latest.json"))
        th = D.export_from_doc(commit, 0, doc)["theses"]
        hit = [D.row_sha256(rw) for rw in th if rw["mint"] == x["mint"] and D.row_sha256(rw) == x["snapshot_hash"]]
        t = _trace_request(x, docs, recs)
        t.update(export_commit=commit, snapshot_row_found_in_that_export=bool(hit))
        rows.append(t)
    ex.append({"example": f"export replay, {chain[0]['chain']} {chain[0]['mint']}", "source": "run_integration.py replay",
               "requests": rows, "events_all_rounds": [x["event"] for x in chain]})
    outjson.write_text(json.dumps({"examples": ex, "note": "real data; every target abstains; probabilities are null by contract"},
                                  indent=1, sort_keys=True) + "\n")
    return {"examples": len(ex)}


def fixture(out: Path) -> dict:
    sys.path.insert(0, str(REPO / "tests"))
    import pytest  # noqa: F401  (the test module imports it)
    import test_predictive_integration as TI
    from memelab import db
    tmp = Path(tempfile.mkdtemp(prefix="p17_fx_"))
    db.DB_PATH = tmp / "lab.sqlite"
    db.DATA_DIR = tmp / "data"
    (tmp / "data").mkdir()
    db.init_db()
    w = TI.fixture_world(tmp)
    rs = [TI.persist(TI.result("FXA", TI.M1, TI.T_FX - 600), tmp),
          TI.persist(TI.result("FXB", TI.M2, TI.T_FX - 600, fatal=("MINT_AUTHORITY_ACTIVE",), status="REJECTED", score=0), tmp)]
    text = I.scout_section(rs, capture_time=TI.T_FX, config_path=TI.cfg(tmp), state_dir=tmp / "state", lab_db=db.DB_PATH,
                           **TI.fx_kw(w, tmp))
    m = I.metrics(tmp / "state")
    docs = [json.loads(x)["document"] for x in (tmp / "state" / I.FILES["documents"]).read_text().splitlines()]
    res = {"probe": "run_integration.py fixture", "evidence_class": "TEST_ONLY", "metrics": m,
           "forecast_documents": [{"target": d["target"], "mint": d["mint_address"][:8], "is_fixture": d["is_fixture"],
                                   "caveats": d["caveats"]} for d in docs if d["prediction_status"] == "FORECAST"],
           "abstentions": sum(1 for d in docs if d["prediction_status"] == "ABSTAIN"),
           "section_has_veto": "Fatal-flag veto: MINT_AUTHORITY_ACTIVE; no forecast clears it" in text,
           "section_has_record_ids": all(json.loads(x)["abstention_record_id"][:12] in text
                                         for x in (tmp / "state" / I.FILES["documents"]).read_text().splitlines()),
           "check_state": I.check_state(tmp / "state", config_path=TI.cfg(tmp)), "socket_events": len(SOCKETS)}
    (out / "FIXTURE_E2E.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("replay")
    p.add_argument("out")
    p.add_argument("--ref", default=REF)
    p = sp.add_parser("summarize")
    p.add_argument("state")
    p.add_argument("reports")
    p.add_argument("outjson")
    p = sp.add_parser("fixture")
    p.add_argument("out")
    p = sp.add_parser("smoke")
    p.add_argument("out")
    p.add_argument("outjson")
    p = sp.add_parser("trace")
    p.add_argument("smoke_out")
    p.add_argument("replay_out")
    p.add_argument("outjson")
    a = ap.parse_args()
    if a.cmd == "replay":
        Path(a.out).mkdir(parents=True, exist_ok=True)
        r = replay(Path(a.out), a.ref)
        print(json.dumps({k: r[k] for k in ("window_decision_events", "round_1_events", "round_2_events", "round_2_documents",
                                            "probabilities_published", "every_document_has_its_record", "socket_events")}))
    elif a.cmd == "summarize":
        r = summarize(Path(a.state), Path(a.reports), Path(a.outjson))
        print(json.dumps({"events": r["metrics"]["event_counts"], "documents": r["documents"],
                          "probabilities": r["probabilities_published"], "problems": r["check_state_problems"]}))
    elif a.cmd == "trace":
        print(json.dumps(trace(Path(a.smoke_out), Path(a.replay_out), Path(a.outjson))))
    elif a.cmd == "smoke":
        r = smoke(Path(a.out), Path(a.outjson))
        print(json.dumps({k: r[k] for k in ("exit_codes", "base_vs_frozen_off_all_reports_byte_equal",
                                            "frozen_on_scout_is_base_plus_appended_section", "lab_tables_equal_base_off_frozen_off_frozen_on",
                                            "section_abstain_lines", "section_forecast_lines")}))
    else:
        Path(a.out).mkdir(parents=True, exist_ok=True)
        r = fixture(Path(a.out))
        print(json.dumps({"metrics": r["metrics"]["event_counts"], "forecasts": len(r["forecast_documents"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
