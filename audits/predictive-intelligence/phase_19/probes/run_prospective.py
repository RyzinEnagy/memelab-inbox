"""Phase 19 runner (monitoring-1, PI-D-104; rules in ../ACCEPTANCE_CHECKLIST.md). Research only; never writes a tracked file
outside audits/predictive-intelligence/phase_19/.

    python -B run_prospective.py inputs               store copies under /home/claude/pi_research/p19/ extended at REF (exports
                                                      and version 2 snapshots only; no network, no candle, no label)
    python -B run_prospective.py predict OUTDIR       the Phase 12 predict step, unchanged, on the prospective window (every frozen
                                                      card and NC1 seed, the pre-opening traps, the replay audit), the integration-1
                                                      documents of the window, the outcome ledger's PLAN, PREDICTION_SET,
                                                      PREDICTION and DOCUMENT entries and PREREG_MANIFEST.json (no label read)
    python -B run_prospective.py outcomes             labels-1 outcomes from the label store into the ledger (after fetch_labels.py)
    python -B run_prospective.py evaluate OUTDIR      checklist rule 7: primary, secondary, NC1, sensitivities, breakdowns, misses
    python -B run_prospective.py drift OUTDIR         monitors D1 to D8, the response per target, notices; MONITOR and RESPONSE
    python -B run_prospective.py rollback OUTDIR      the drift response on a fixture registry (TEST_ONLY)
    python -B run_prospective.py audit OUTDIR         F1 to F5, the git order of the predictions and the first label call, verify
    python -B run_prospective.py report OUTDIR        PROSPECTIVE_REPORT.md and OUTCOME_LEDGER.md from the outputs (deterministic)

The steps other than `inputs` refuse any socket call (audit hook). `predict` is deterministic (two runs give identical files except
`run_log_*.json`).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from memelab.predictive import baselines as B  # noqa: E402
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import evaluation as E  # noqa: E402
from memelab.predictive import features as F  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import monitoring as M  # noqa: E402
from memelab.predictive import stats as K  # noqa: E402
from memelab.predictive import store as S  # noqa: E402

SOCKETS: list[str] = []
AUD = REPO / "audits/predictive-intelligence"
PH = AUD / "phase_19"
MON = PH / "monitoring"
LEDGER = MON / "OUTCOME_LEDGER.jsonl"
WORK = Path("/home/claude/pi_research/p19")
FS_STORE, DEV_STORE = WORK / "fs_store.sqlite", WORK / "dev_store.sqlite"
SRC_STORES = {"fs": (Path("/home/claude/pi_research/p05/predictive_store.sqlite"),
                     "2525f0c4a7b2662713d07e99acd1a371c33aa5082994f5f552aba477f98dd8de"),
              "dev": (Path("/home/claude/pi_research/p06/dev_store.sqlite"),
                      "d2a5a7c67afb82da79c4c957ba3b32576963bc4d96bf61ca14fa81b2b5b6e8db")}
REF = "71fc50e1eb86d916034bb0285a466cf2ec1cc4d0"
REF_TIME = C.parse_utc("2026-10-26T10:23:04Z")
P0, H = L.prospective_start(), L.holdout_start()
WINDOW_END = REF_TIME + 1.0
TARGETS = (L.T1, L.T1B, L.T2)
SHORT = {L.T1: "T1_24h", L.T1B: "T1b_6h", L.T2: "T2_24h"}
LONG = {v: k for k, v in SHORT.items()}
PUBLISHED = {"documents": "9b839e76b7a334847911b6d5ad1f81044e17da47a09354dd3efd70fdbc0c77d0",
             "records": "a8114c19f9ac506b0a809a6f9e1bf1b70ada6e049c693debc1d102294bb5accc"}
PRED_FILE, DEC_FILE = "PROSPECTIVE_PREDICTIONS.csv", "PROSPECTIVE_DECISIONS.csv"
REFS = ("P07_B0", "P07_B2")
REPS, SEED = E.REPS, E.SEED
N_SEARCH, N_SEARCH_SENS = 130, 169
CONTACT_SCAN = PH / "evidence/prospective_contact_scan_cp19_1.json"   # CP19-1 (skeptic m7): the scan names the contacted mints


def contact_mints6() -> tuple[str, ...]:
    return tuple(json.loads(CONTACT_SCAN.read_text())["contact_mints6"])


def _hook(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        SOCKETS.append(event)
        raise RuntimeError(f"Phase 19 runner makes no network call ({event})")


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fsha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def iso(t) -> str:
    return datetime.fromtimestamp(float(t), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def jsave(p: Path, o) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(o, indent=1, sort_keys=True, default=str) + "\n")


def git(*a: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *a], check=True, capture_output=True, text=True).stdout


def num(x):
    if x is None:
        return ""
    if isinstance(x, bool):
        return "1" if x else "0"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    x = float(x)
    return "" if not math.isfinite(x) else f"{x:.17g}"


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: (num(v) if isinstance(v, (float, int, np.floating, np.integer)) and not isinstance(v, bool)
                            else ("1" if v is True else "0" if v is False else ("" if v is None else v))) for k, v in r.items()})


def run_log(out: Path, name: str, t0: float, extra: dict) -> None:
    jsave(out / f"run_log_{name}.json", {"step": name, "start_utc": iso(t0), "end_utc": iso(time.time()),
                                        "wall_s": round(time.time() - t0, 3), "head": git("rev-parse", "HEAD").strip(),
                                        "python": sys.version.split()[0], "numpy": np.__version__,
                                        "monitoring_sha256": fsha(REPO / "memelab/predictive/monitoring.py"),
                                        "runner_sha256": fsha(Path(__file__)), "network_calls": len(SOCKETS), **extra})


# ---------------------------------------------------------------- inputs (no network: exports from git only)
def cmd_inputs() -> int:
    sys.addaudithook(_hook)
    from memelab.predictive import sources as SRC
    t0 = time.time()
    WORK.mkdir(parents=True, exist_ok=True)
    out = {"ref": REF, "stores": {}}
    for name, (src, want) in SRC_STORES.items():
        got = fsha(src)
        if got != want:
            raise SystemExit(f"{src}: sha256 {got[:12]} is not the recorded {want[:12]}")
        dst = FS_STORE if name == "fs" else DEV_STORE
        for extra in (dst, Path(str(dst) + "-wal"), Path(str(dst) + "-shm")):
            if extra.exists():
                extra.unlink()
        shutil.copyfile(src, dst)
        out["stores"][name] = {"source": str(src), "source_sha256": got}
    ex = SRC.export_versions(REPO, REF)
    fs, dev = S.connect(FS_STORE), L.connect(DEV_STORE)
    for name, con in (("fs", fs), ("dev", dev)):
        r = S.ingest_exports(con, ex, now=time.time(), ref=REF)
        con.commit()
        out["stores"][name]["ingest"] = {k: (len(v) if k == "refused" else v) for k, v in r.items()}
        out["stores"][name]["refused"] = [{kk: (str(vv)[:80]) for kk, vv in x.items()} if isinstance(x, dict) else str(x)[:120]
                                          for x in r.get("refused") or []]
    snap = {}
    for mode in F.MODES:
        r = F.build_snapshots(fs, feature_version=F.FEATURE_VERSION, mode=mode, now=time.time())
        snap[mode] = {"added": r["snapshots_added"], "skipped": len(r["skipped"])}
    fs.commit()
    out["snapshots"] = snap
    out["contact"] = contact_check()
    out["exports"] = len(ex)
    out["window"] = {"from_utc": iso(P0), "to_utc": iso(WINDOW_END)}
    for name, p in (("fs", FS_STORE), ("dev", DEV_STORE)):
        out["stores"][name]["after_sha256"] = fsha(p)
    out["wall_s"] = round(time.time() - t0, 1)
    out["network_calls"] = len(SOCKETS)
    jsave(PH / "evidence/inputs.json", out)
    print(json.dumps({k: v for k, v in out.items() if k != "stores"} | {"ingest": {k: v["ingest"] for k, v in out["stores"].items()}}))
    return 0 if not out["contact"]["problems"] else 1


def window_rows(con) -> list[dict]:
    return [dict(r) for r in con.execute("SELECT * FROM predictive_decisions WHERE decision_key IS NOT NULL AND decision_time >= ? "
                                         "AND decision_time < ? ORDER BY decision_time, mint, id", (P0, WINDOW_END))]


def contact_check() -> dict:
    """No candle of a window decision's pool or mint after its entry, and no prospective label, in either store (G4)."""
    probs, n = [], 0
    for name, p in (("fs", FS_STORE), ("dev", DEV_STORE)):
        con = S.connect(p, migrate_schema=False) if name == "fs" else L.connect(p)
        wins = [r for r in window_rows(con) if r["chain"] == "solana"]
        for r in wins:
            n += 1
            te = L.t_entry(float(r["decision_time"]))
            hit = con.execute("SELECT count(*) FROM predictive_raw_responses WHERE mint=? AND boundary_at > ?", (r["mint"], te)).fetchone()[0]
            if hit:
                probs.append(f"{name}: {hit} raw response(s) of {r['mint'][:6]} end after its entry")
        if name == "dev":
            lab = con.execute("SELECT count(*) FROM predictive_labels WHERE split='PROSPECTIVE' AND (label IS NOT NULL OR response_key "
                              "IS NOT NULL OR state IN ('LABELED','PENDING','UNVERIFIABLE_NO_VENDOR_HISTORY'))").fetchone()[0]
            if lab:
                probs.append(f"dev: {lab} prospective label rows with a read, a label or a read-based state")
        con.close()
    return {"window_solana_decisions_checked": n, "problems": probs}


# ---------------------------------------------------------------- predict (the Phase 12 step, unchanged, on the window)
def _p12():
    p12 = _load("p12_run_holdout", "audits/predictive-intelligence/phase_12/probes/run_holdout.py")
    P7, P10, P11 = p12.P7, p12.P10, p12.P11

    class ProspectiveInputs(p12.Inputs):
        """Phase 12's Inputs on the prospective window [P0, WINDOW_END): every input as of each decision, no label; training
        rows, NC1 and the new-mint views at the frozen cutoff H through Phase 12's own methods."""

        def __init__(self, dev_path: str, fs_path: str):
            from memelab.predictive import analog as A
            from memelab.predictive import onchain as O
            from memelab.predictive import runtime as RT
            from memelab.predictive import socialcat as SC
            from memelab.predictive import technical as T8
            for p in (dev_path, fs_path):
                L.refuse_sealed(p)
                RT.refuse_bakeoff_labels(path=p)
            self.dev, self.fs = P7.ro(dev_path), P7.ro(fs_path)
            self.frows_h, self.snaps, self.info = P7.load_inputs(self.dev, self.fs)
            self.frows = {r["decision_key"]: r for r in F.training_view(self.fs, as_of=WINDOW_END, feature_version=F.FEATURE_VERSION,
                                                                        mode="provider")}
            self.dtab = p12.decision_table(self.dev)
            self.sol = p12.solana_decisions(self.fs, WINDOW_END)
            self.hold = {k: v for k, v in self.sol.items() if P0 <= float(v["decision_time"]) < WINDOW_END}
            dev_win = {k for k, v in self.dtab.items() if v["chain"] == "solana" and P0 <= v["decision_time"] < WINDOW_END}
            if set(self.hold) != dev_win:
                raise SystemExit("the prospective decision sets of the two stores differ")
            self.series = A.regime_series(P11.regime_rows(self.sol, self.frows))
            self.extras = P11.extras_of(self.fs, self.hold, self.frows, self.series)
            self.tsnaps = {k: T8.technical_as_of(self.fs, d["chain"], d["mint"], float(d["decision_time"]), mode="provider", decision_key=k)
                           for k, d in self.hold.items()}
            self.osnaps = {k: O.onchain_as_of(self.fs, d["chain"], d["mint"], float(d["decision_time"]), decision_key=k)
                           for k, d in self.hold.items()}
            self.ssnaps, self.sc_prov = {}, Counter()
            for k, d in self.hold.items():
                row = self.fs.execute("SELECT export_commit, export_blob FROM predictive_decisions WHERE decision_key=?", (k,)).fetchone()
                cx = P10.context_of(row["export_commit"])
                self.sc_prov["blob_equal" if cx["blob"] == row["export_blob"] else "blob_differs"] += 1
                self.sc_prov["commit_time_equal" if cx["commit_time"] == float(d["decision_time"]) else "commit_time_differs"] += 1
                self.ssnaps[k] = SC.socialcat_as_of(self.fs, d["chain"], d["mint"], float(d["decision_time"]), decision_key=k, context=cx)
            self.keys = sorted(self.hold, key=lambda k: (float(self.hold[k]["decision_time"]), self.hold[k]["mint"], k))

    # the Phase 12 predict step reads these module names; nothing in its file changes
    p12.Inputs, p12.END, p12.PRED_FILE, p12.DEC_FILE = ProspectiveInputs, WINDOW_END, PRED_FILE, DEC_FILE
    return p12


def cmd_predict(out: Path) -> int:
    sys.addaudithook(_hook)
    t0 = time.time()
    p12 = _p12()
    out.mkdir(parents=True, exist_ok=True)
    rc = p12.cmd_predict(out, str(DEV_STORE), str(FS_STORE))
    (out / "PREOPEN_MANIFEST.json").rename(out / "P12_STEP_MANIFEST.json")
    (out / "run_log_predict.json").rename(out / "run_log_p12_predict_step.json")
    cards = p12.load_cards()
    # P46: the window's snapshots carry the cards' feature version and feature set sha
    fs = p12.P7.ro(str(FS_STORE))
    vs = {(r[0], r[1]) for r in fs.execute("SELECT feature_version, feature_set_sha FROM predictive_snapshots WHERE decision_time >= ? "
                                            "AND decision_time < ?", (P0, WINDOW_END))}
    card_fs = {(v["card"]["feature_version"], v["card"]["feature_set_sha"]) for (s, cid), v in cards.items() if cid in REFS}
    p46 = {"window_snapshot_versions": sorted(map(list, vs)), "reference_card_versions": sorted(map(list, card_fs)), "equal": vs == card_fs}
    # system documents of the window: the integration-1 export replay (Phase 17 probe), byte-equal to the Phase 18 published run
    p17 = _load("p17_run_integration", "audits/predictive-intelligence/phase_17/probes/run_integration.py")
    rep_dir = WORK / "replay_predict"
    if rep_dir.exists():
        shutil.rmtree(rep_dir)
    rep_dir.mkdir(parents=True)
    rr = p17.replay(rep_dir, REF)
    st = rep_dir / "state_replay"
    pub = {"documents": fsha(st / "DOCUMENTS.jsonl"), "records": fsha(st / "RECORDS.jsonl")}
    if pub != PUBLISHED:
        raise SystemExit(f"PUBLICATION_REVISION: the documents or records differ from the Phase 18 published run {pub}")
    (out / "published").mkdir(exist_ok=True)
    shutil.copyfile(st / "DOCUMENTS.jsonl", out / "published/DOCUMENTS.jsonl")
    shutil.copyfile(st / "RECORDS.jsonl", out / "published/RECORDS.jsonl")
    docs = [json.loads(x) for x in (st / "DOCUMENTS.jsonl").read_text().splitlines()]
    recs = {json.loads(x)["record_id"]: x for x in (st / "RECORDS.jsonl").read_text().splitlines()}
    reqs = [json.loads(x) for x in (st / "REQUESTS.jsonl").read_text().splitlines()]
    dev = p12.P7.ro(str(DEV_STORE))
    allwin = window_rows(dev)
    by_row = {(r["chain"], r["mint"], r["row_sha256"], float(r["decision_time"])): r for r in allwin}
    fid_req = {}
    for q in reqs:
        for t in q.get("targets") or []:
            if t.get("forecast_id"):
                fid_req[t["forecast_id"]] = q
    # the ledger: PLAN, PREDICTION_SET, PREDICTION (the two references), DOCUMENT
    ledger = out / "OUTCOME_LEDGER.jsonl"
    if ledger.exists():
        ledger.unlink()
    plan_files = ["audits/predictive-intelligence/phase_19/ACCEPTANCE_CHECKLIST.md",
                  "audits/predictive-intelligence/phase_19/experiments/EXPERIMENT_REGISTRY.csv",
                  "audits/predictive-intelligence/phase_19/monitoring/PROSPECTIVE_PLAN.md"]
    plan = {"kind": "PLAN", "plan_id": "P19-PROSPECTIVE-1", "decision": "PI-D-104", "ref": REF, "window_from_utc": iso(P0),
            "window_to_utc": iso(WINDOW_END), "files": {f: fsha(REPO / f) for f in plan_files},
            "monitoring_version": M.MONITORING_VERSION, "labels_version": L.LABELS_VERSION, "registry_sha": C.registry_sha256()}
    psha = fsha(out / PRED_FILE)
    set_id = "ps_" + M.sha([REF, psha, pub])[:40]
    decs = [{"decision_key": r["decision_key"], "chain": r["chain"], "mint": r["mint"], "decision_time": float(r["decision_time"])}
            for r in allwin]
    pset = {"kind": "PREDICTION_SET", "set_id": set_id, "file": f"monitoring/{PRED_FILE}", "sha256": psha,
            "decisions_file_sha256": fsha(out / DEC_FILE), "documents_sha256": pub["documents"], "records_sha256": pub["records"],
            "cards": len(cards), "cards_cutoff_utc": iso(H), "decisions": decs}
    preds = list(csv.DictReader(open(out / PRED_FILE)))
    payloads = [plan, pset]
    for r in preds:
        if r["candidate"] not in REFS:
            continue
        s = r["target_short"]
        t = LONG[s]
        v = cards[(s, r["candidate"])]
        T = float(r["decision_time"])
        payloads.append({"kind": "PREDICTION", "prediction_id": "pr_" + M.sha([set_id, r["decision_key"], t, r["candidate"]])[:40],
                         "set_id": set_id, "decision_key": r["decision_key"], "chain": r["chain"], "mint": r["mint"], "decision_time": T,
                         "target": t, "candidate": r["candidate"], "number": float(r["number"]) if r["number"] != "" else None,
                         "why": r["why"] or None, "card_file_sha256": v["file_sha256"], "model_sha": v["card"]["model_sha"],
                         "training_cutoff_utc": v["card"]["training_cutoff_utc"], "label_matures_at": C.label_matures_at(t, T),
                         "published": False, "role": "REFERENCE_INTERNAL"})
    unmatched = 0
    for d in docs:
        q = fid_req[d["forecast_id"]]
        doc = d["document"]
        T = C.parse_utc(doc["decision_time_utc"])
        row = by_row.get((q["chain"], q["mint"], q["row_sha256"], T))
        if row is None:
            unmatched += 1
            continue
        line = next(x for x in (st / "DOCUMENTS.jsonl").read_text().splitlines() if json.loads(x)["forecast_id"] == d["forecast_id"])
        payloads.append({"kind": "DOCUMENT", "forecast_id": d["forecast_id"], "record_id": d["abstention_record_id"], "set_id": set_id,
                         "decision_key": row["decision_key"], "chain": row["chain"], "mint": row["mint"], "decision_time": T,
                         "target": doc["target"], "prediction_status": doc["prediction_status"], "reasons": list(doc["abstain_reasons"]),
                         "document_sha256": M.sha_bytes(line.encode()), "record_sha256": M.sha_bytes(recs[d["abstention_record_id"]].encode()),
                         "row_sha256": q["row_sha256"], "published": True})
    led = M.append(ledger, payloads)
    ver = M.verify(ledger)
    files = sorted(p.name for p in out.iterdir() if p.is_file() and not p.name.startswith("run_log") and p.name != "PREREG_MANIFEST.json")
    man = {"rule": "every prospective prediction and system document is fixed here, before any label read (checklist rule 1); the reader "
                   "checks these sha256 against HEAD", "ref": REF, "window_from_utc": iso(P0), "window_to_utc": iso(WINDOW_END),
           "files": {n: fsha(out / n) for n in files} | {f"published/{n}": fsha(out / "published" / n) for n in ("DOCUMENTS.jsonl", "RECORDS.jsonl")},
           "prediction_rows": len(preds), "solana_decisions": len({r["decision_key"] for r in preds}), "window_decisions": len(allwin),
           "documents": len(docs), "documents_unmatched": unmatched, "ledger": led, "ledger_verify": ver, "labels_read": 0,
           "p46_feature_versions": p46, "replay_round_2_documents": rr["round_2_documents"]}
    jsave(out / "PREREG_MANIFEST.json", man)
    run_log(out, "predict", t0, {"p12_step_exit": rc, "replay_socket_events": rr["socket_events"]})
    ok = rc == 0 and p46["equal"] and unmatched == 0 and ver["ok"] and rr["round_2_documents"] == 0
    print(json.dumps({"p12_step_exit": rc, "prediction_rows": len(preds), "documents": len(docs), "ledger": led, "p46": p46["equal"],
                      "unmatched_documents": unmatched, "ok": ok}))
    return 0 if ok else 1


# ---------------------------------------------------------------- outcomes (after fetch_labels.py)
def universe(as_of: float) -> tuple[L.Universe, object]:
    con = L.connect(DEV_STORE)
    lists = json.loads((WORK / "vendor_lists.json").read_text()) if (WORK / "vendor_lists.json").exists() else {}
    rmap = json.loads((WORK / "read_map.json").read_text()) if (WORK / "read_map.json").exists() else {}
    others = json.loads((WORK / "other_pool_reads.json").read_text()) if (WORK / "other_pool_reads.json").exists() else {}
    decs = []
    for r in window_rows(con):
        vl = lists.get(r["mint"])
        vp = (vl["pools"] if vl.get("pools") is not None else L.LIST_FAILED) if vl else None
        decs.append(L.decision_from_row(r, vendor_pools=vp))
    read_of = {k: L.read_from_store(con, rk) for k, rk in rmap.items()}
    oth = {k: (L.LIST_FAILED if v == L.LIST_FAILED else [L.read_from_store(con, x) if x else None for x in v]) for k, v in others.items()}
    return L.Universe(decs, as_of=as_of, read_of=read_of, other_reads=oth), con


def cmd_outcomes() -> int:
    sys.addaudithook(_hook)
    t0 = time.time()
    open_log = json.loads((MON / "OPENING_LOG.json").read_text())
    if not open_log.get("entries"):
        raise SystemExit("no opening logged: run fetch_labels.py after the predictions commit")
    u, con = universe(t0)
    recs = M.prospective_records(u)
    need = [r for r in recs if r["state"] == L.NEEDS_OTHER_POOLS]
    if need:
        raise SystemExit(f"{len(need)} T2 records need other pools: run fetch_labels.py others")
    res = L.store_labels(con, recs, export_ref=REF, params={"labels_version": L.LABELS_VERSION, "as_of": t0, "phase": "19"}, now=t0)
    con.commit()
    viol = L.cross_target_violations(recs)
    idx = M.load(LEDGER)
    pl = M.next_outcomes(idx, recs, recorded_at=t0)
    led = M.append(LEDGER, pl, expect_sha=M.head_sha(idx.entries))
    # G23: no prospective outcome reaches the training gate
    leak = {}
    win = {r["decision_key"] for r in window_rows(con)}
    for t in TARGETS:
        rows = L.training_labels(con, t0, t)
        leak[SHORT[t]] = sum(1 for r in rows if r["decision_key"] in win)
    states = Counter(f"{SHORT[r['target']]}:{r['state']}" for r in recs)
    out = {"as_of_utc": iso(t0), "records": len(recs), "states": dict(sorted(states.items())), "label_rows_added": res["added"],
           "cross_target_violations": len(viol), "ledger": led, "ledger_verify": M.verify(LEDGER),
           "training_gate_prospective_rows": leak, "network_calls": len(SOCKETS)}
    hist = PH / "evidence/outcomes_runs.json"
    log = json.loads(hist.read_text()) if hist.exists() else []
    log.append(out)
    jsave(hist, log)
    print(json.dumps(out))
    return 0 if not viol and all(v == 0 for v in leak.values()) and out["ledger_verify"]["ok"] else 1


# ---------------------------------------------------------------- evaluate (checklist rule 7)
def read_predictions(out_dir: Path) -> tuple[dict, dict]:
    preds: dict[tuple[str, str], dict] = {}
    for r in csv.DictReader(open(out_dir / PRED_FILE)):
        d = preds.setdefault((r["target_short"], r["decision_key"]), {"decision_key": r["decision_key"], "chain": r["chain"],
                                                                      "mint": r["mint"], "decision_time": float(r["decision_time"])})
        d[r["candidate"]] = float(r["number"]) if r["number"] != "" else float("nan")
        d[r["candidate"] + "_why"] = r["why"] or None
    attrs = {r["decision_key"]: r for r in csv.DictReader(open(out_dir / DEC_FILE))}
    return preds, attrs


def eval_rows(outs: list[dict], s: str, preds: dict, attrs: dict, *, lens: bool = False) -> list[dict]:
    rows = []
    for o in outs:
        p = preds.get((s, o["decision_key"]))
        if p is None:
            raise SystemExit(f"no prediction for {o['decision_key'][:12]} ({s})")
        E.check_identity(o, p)
        a = attrs[o["decision_key"]]
        y = int(o["conservative_lens"]) if lens else int(o["label"])
        e = B.Example(decision_key=o["decision_key"], chain=o["chain"], mint=o["mint"], decision_time=float(o["decision_time"]),
                      label_matures_at=float(o["label_matures_at"]), y=y, route=a["route"], creator=a["creator"] or None,
                      key_conflict=a["key_conflict"] == "1", label_key=o["outcome_id"])
        row = {"example": e, "y": y, "fold": "PROSPECTIVE", "attrs": a, "outcome": o}
        row.update({k: v for k, v in p.items() if k not in ("decision_key", "chain", "mint", "decision_time")})
        rows.append(row)
    return rows


def _ev(rows, model, ref):
    for r in rows:
        r.setdefault(model, float("nan"))
        r.setdefault(ref, float("nan"))
    return B.evaluate(rows, model, reference=ref, reps=REPS, seed=SEED)


def _verdict(ev, p_holm):
    if not ev.get("n_with_number"):
        return "INSUFFICIENT_HISTORY"
    v = E.holdout_verdict(ev, p_holm)
    return "SKILL_INDICATED_PROSPECTIVE_HOLDOUT" if v == E.HOLDOUT_SKILL else v


def metric_row(s, view, model, ref, kind, ev, *, p_holm=None, extra=None) -> dict:
    iv = ev.get("intervals") or {}
    cal = ev.get("calibration") or {}

    def ci(u, i):
        c = (iv.get(u) or {}).get("ci")
        return c[i] if c else None
    row = {"target": LONG[s], "target_short": s, "view": view, "model": model, "reference": ref, "kind": kind,
           "n_rows": ev["n_rows"], "n_with_number": ev["n_with_number"], "coverage": ev.get("coverage"),
           "abstain_reasons": json.dumps(ev.get("abstain_reasons") or {}, sort_keys=True), "positives": ev.get("positives"),
           "prevalence": ev.get("prevalence"), "days": ev.get("days"), "mints": ev.get("mints"), "brier": ev.get("brier"),
           "brier_ref": ev.get("brier_ref"), "bss": ev.get("bss"), "log_loss": ev.get("log_loss"), "log_loss_ref": ev.get("log_loss_ref"),
           "roc_auc": ev.get("auc"), "average_precision": ev.get("average_precision"), "auc_note": ev.get("auc_note", ""),
           "bss_ci_day_lo": ci("day", 0), "bss_ci_day_hi": ci("day", 1), "day_interval_note": (iv.get("day") or {}).get("note", ""),
           "bss_ci_mint_lo": ci("mint", 0), "bss_ci_mint_hi": ci("mint", 1), "governing": ev.get("governing") or "UNDEFINED",
           "p_one_sided": ev.get("p_one_sided"), "p_holm": p_holm, "cal_mean_pred": cal.get("mean_pred"),
           "cal_observed": cal.get("observed"), "cal_in_the_large_ok": cal.get("in_the_large_ok"), "cal_bins": len(cal.get("bins") or []),
           "cal_every_bin_ok": cal.get("every_bin_ok"), "verdict": _verdict(ev, p_holm)}
    row.update(extra or {})
    return row


def cal_rows(s, view, model, ev) -> list[dict]:
    cal = ev.get("calibration") or {}
    out = [{"target_short": s, "view": view, "model": model, "bin": "IN_THE_LARGE", "n": cal.get("n"), "positives": None,
            "mean_pred": cal.get("mean_pred"), "observed": cal.get("observed"), "wilson_lo": (cal.get("wilson") or [None, None])[0],
            "wilson_hi": (cal.get("wilson") or [None, None])[1], "ok": cal.get("in_the_large_ok"), "note": cal.get("note", "")}]
    for i, b in enumerate(cal.get("bins") or []):
        out.append({"target_short": s, "view": view, "model": model, "bin": i, "n": b["n"], "positives": b["positives"],
                    "mean_pred": b["mean_pred"], "observed": b["observed"], "wilson_lo": b["wilson"][0], "wilson_hi": b["wilson"][1],
                    "ok": b["ok"], "note": f"p {b['p_min']:.4f} to {b['p_max']:.4f}"})
    return out


def lrow(t, eid, cand, kind, view, ev, verdict, sel="", claim="NO_CLAIM_PROSPECTIVE_INSUFFICIENT") -> dict:
    return {"phase": "19", "experiment_id": eid, "target": t, "candidate": cand, "kind": kind, "view": view, "seed": SEED,
            "folds": "PROSPECTIVE", "n_rows": ev.get("n_rows"), "n_with_number": ev.get("n_with_number"), "verdict": verdict,
            "split_fingerprint": "", "selection_status": sel, "claim": claim}


def cmd_evaluate(out: Path) -> int:
    sys.addaudithook(_hook)
    t0 = time.time()
    idx = M.load(LEDGER)
    ver = M.verify(LEDGER)
    as_of = max(float(o["recorded_at"]) for o in M.current_outcomes(idx).values())
    preds, attrs = read_predictions(MON)
    cands = sorted({k for p in preds.values() for k in p if k.startswith("P") and not k.endswith("_why")})
    fitted = {}
    for c in cands:
        nums = [p[c] for p in preds.values() if c in p]
        fitted[c] = any(math.isfinite(x) for x in nums)
    sc = M.scorable(idx, as_of)
    cur = M.current_outcomes(idx)
    rows_by, prim, metrics, calib, scored, sens, shift, ledger = {}, {}, [], [], [], [], [], []
    counts = {}
    for t in TARGETS:
        s = SHORT[t]
        outs = [o for o in sc if o["target"] == t and o["chain"] == "solana"]
        rows_by[s] = eval_rows(outs, s, preds, attrs)
        st = Counter(o["state"] for (k, tt), o in cur.items() if tt == t and o["chain"] == "solana")
        counts[s] = {"scorable": len(outs), "positives": sum(int(o["label"]) for o in outs), "states_solana": dict(sorted(st.items())),
                     "days": sorted({r["example"].day for r in rows_by[s]}), "mints": len({o["mint"] for o in outs})}
        for r in rows_by[s]:
            sr = {"target_short": s, "decision_key": r["example"].decision_key, "mint": r["example"].mint,
                  "decision_time_utc": iso(r["example"].decision_time), "day": r["example"].day, "y": r["y"],
                  "label_class": r["outcome"]["label_class"], "route": r["attrs"]["route"]}
            for k in cands:
                sr[k] = r.get(k)
            scored.append(sr)
    pv = {}
    for t in TARGETS:
        s = SHORT[t]
        prim[s] = _ev(rows_by[s], "P07_B2", "P07_B0")
        pv[s] = prim[s].get("p_one_sided")
    ph = dict(zip([SHORT[t] for t in TARGETS], E.holm([pv[SHORT[t]] for t in TARGETS])))
    primary = {}
    for t in TARGETS:
        s = SHORT[t]
        ev = prim[s]
        mr = metric_row(s, "PRIMARY", "P07_B2", "P07_B0", "PRIMARY_HOLDOUT", ev, p_holm=ph.get(s))
        metrics.append(mr)
        calib += cal_rows(s, "PRIMARY", "P07_B2", ev)
        y = [r["y"] for r in rows_by[s]]
        b0 = next(iter({r["P07_B0"] for r in rows_by[s]}), None)
        primary[s] = {"target": t, "pair": "P07_B2 vs P07_B0 (registry references; no viable champion)", "metric": mr,
                      "prospective_prevalence": E.prevalence(y) if y else None, "training_prevalence_b0": b0,
                      "minority": M.minority_note(y, [r["P07_B2"] for r in rows_by[s]]),
                      "minority_b0": M.minority_note(y, [r["P07_B0"] for r in rows_by[s]]),
                      "shadow_criteria": E.shadow_criteria(ev), "counts": counts[s]}
        ledger.append(lrow(t, f"P19:{t}:B2_vs_B0", "P07_B2", "PRIMARY_HOLDOUT", "PROSPECTIVE vs P07_B0", ev, mr["verdict"]))
    sec = []
    for t in TARGETS:
        s = SHORT[t]
        for cid in cands:
            if not fitted.get(cid) or cid == "P07_B0" or not any(cid in p for (ss, _), p in preds.items() if ss == s):
                continue
            for ref in REFS:
                if ref == cid:
                    continue
                sec.append((s, cid, ref, _ev(rows_by[s], cid, ref)))
    sp = E.holm([ev.get("p_one_sided") for *_, ev in sec])
    days_n = {s: len(counts[s]["days"]) for s in counts}
    for (s, cid, ref, ev), p_h in zip(sec, sp):
        bon = E.bonferroni(ev.get("p_one_sided"), N_SEARCH)
        own = _verdict(ev, ev.get("p_one_sided"))
        sel = E.selection_status(E.HOLDOUT_SKILL if own == "SKILL_INDICATED_PROSPECTIVE_HOLDOUT" else own, p_h, None, bon)
        mr = metric_row(s, "PROSPECTIVE", cid, ref, "SECONDARY_HOLDOUT", ev, p_holm=p_h,
                        extra={"uncorrected_verdict": own, "p_bonferroni_full_search": bon, "n_search": N_SEARCH,
                               "p_max_t": None, "max_t_note": f"not computed: {days_n[s]} decision days, fewer than 5",
                               "selection_status": sel})
        metrics.append(mr)
        ledger.append(lrow(LONG[s], f"P19:{LONG[s]}:{cid}_vs_{ref[4:]}", cid, "SECONDARY_HOLDOUT", f"PROSPECTIVE vs {ref}", ev,
                           mr["verdict"], sel))
    nc1 = {}
    for t in TARGETS:
        s = SHORT[t]
        seeds = []
        for seed in range(20):
            c = f"NC1_seed{seed:02d}"
            use = [r for r in rows_by[s] if math.isfinite(r.get(c, float("nan"))) and math.isfinite(r["P07_B0"])]
            bss = K.brier_skill([r["y"] for r in use], [r[c] for r in use], [r["P07_B0"] for r in use]) if use else None
            seeds.append({"seed": seed, "n": len(use), "bss": bss})
            ledger.append({"phase": "19", "experiment_id": f"P19:{t}:NC1_seed{seed}", "target": t, "candidate": "NC1",
                           "kind": "NEGATIVE_CONTROL", "view": "PROSPECTIVE vs P07_B0", "seed": seed, "folds": "PROSPECTIVE",
                           "n_rows": len(rows_by[s]), "n_with_number": len(use), "verdict": "", "split_fingerprint": "",
                           "selection_status": "", "claim": "CONTROL"})
        fin = [x["bss"] for x in seeds if x["bss"] is not None and math.isfinite(x["bss"])]
        use = [r for r in rows_by[s] if math.isfinite(r.get("NC1_seed00", float("nan"))) and math.isfinite(r["P07_B0"])]
        mean = float(np.mean(fin)) if fin else None
        nc1[s] = {"seeds": seeds, "mean_bss": mean, "champion_reference_bss": prim[s].get("bss"),
                  "verdict": B.nc1_verdict(len(use), int(sum(r["y"] for r in use)), len({r["example"].day for r in use}), mean)}
    # sensitivities and breakdowns of the primary pair
    c6 = contact_mints6()
    contact = {o["mint"] for o in cur.values() if any(o["mint"].startswith(m6) for m6 in c6)}
    if len(contact) != len(c6):
        raise SystemExit("a contact prefix matches no window mint or several")
    for t in TARGETS:
        s = SHORT[t]
        views = {}
        cens = [o for (k, tt), o in cur.items() if tt == t and o["chain"] == "solana" and int(o["censored"])
                and float(o["label_matures_at"]) <= as_of]
        views["CONSERVATIVE_LENS"] = rows_by[s] + eval_rows(cens, s, preds, attrs, lens=True)
        views["NO_KEY_CONFLICT"] = [r for r in rows_by[s] if not r["example"].key_conflict]
        views["PIT_ONLY"] = [r for r in rows_by[s] if r["attrs"]["route"] == "PIT_RECORDED"]
        views["NEW_MINTS"] = [r for r in rows_by[s] if r["attrs"][f"new_mint_{s}"] == "1"]
        views["CONTACT_EXCLUDED"] = [r for r in rows_by[s] if r["example"].mint not in contact]
        for v, rr in views.items():
            ev = _ev(rr, "P07_B2", "P07_B0")
            mr = metric_row(s, v, "P07_B2", "P07_B0", "SENSITIVITY", ev, extra={"censored_added": len(cens) if v == "CONSERVATIVE_LENS" else ""})
            sens.append(mr)
            ledger.append(lrow(t, f"P19:{t}:SENS_{v}", "P07_B2", "SENSITIVITY", f"{v} vs P07_B0", ev, mr["verdict"]))
        for b in ("day", "route", "regime_at_T", "liquidity_bucket", "launch_age_bucket", "status_group"):
            vals = sorted({r["attrs"][b] for r in rows_by[s]})
            for val in vals:
                rr = [r for r in rows_by[s] if r["attrs"][b] == val]
                ev = _ev(rr, "P07_B2", "P07_B0")
                shift.append(metric_row(s, f"{b}={val}", "P07_B2", "P07_B0", "DATASET_SHIFT_DESCRIPTIVE", ev,
                                        extra={"breakdown": b, "value": val,
                                               "support_note": "n >= 20" if len(rr) >= 20 else "n < 20: no rate claimed"}))
            ledger.append({"phase": "19", "experiment_id": f"P19:{t}:SHIFT_{b}", "target": t, "candidate": "P07_B2",
                           "kind": "DATASET_SHIFT_DESCRIPTIVE", "view": f"{b} ({len(vals)} values)", "seed": SEED, "folds": "PROSPECTIVE",
                           "n_rows": len(rows_by[s]), "n_with_number": "", "verdict": "DESCRIPTIVE", "split_fingerprint": "",
                           "selection_status": "", "claim": "NOT_A_CLAIM_DESCRIPTIVE"})
    mis = M.misses(idx, as_of=as_of)
    out.mkdir(parents=True, exist_ok=True)
    scored.sort(key=lambda r: (r["target_short"], r["decision_time_utc"], r["mint"], r["decision_key"]))
    write_csv(out / "PROSPECTIVE_SCORED.csv", scored)
    write_csv(out / "PROSPECTIVE_METRICS.csv", metrics)
    write_csv(out / "CALIBRATION_BINS.csv", calib)
    write_csv(out / "SENSITIVITY.csv", sens)
    write_csv(out / "SHIFT_BREAKDOWN.csv", shift)
    write_csv(out / "MISSES.csv", mis)
    jsave(out / "PRIMARY_RESULTS.json", {"primary": primary, "holm_family": [SHORT[t] for t in TARGETS], "p_holm": ph,
                                         "reps": REPS, "seed": SEED, "as_of_utc": iso(as_of), "ledger_head": ver.get("head")})
    jsave(out / "NEGATIVE_CONTROLS.json", {"NC1": nc1})
    jsave(out / "COUNTS.json", counts)
    led_prev = list(csv.DictReader(open(AUD / "phase_18/experiments/SEARCH_LEDGER.csv")))
    pre = PH / "experiments/SEARCH_LEDGER_P19_ROWS.csv"
    pre_rows = list(csv.DictReader(open(pre))) if pre.exists() else []
    full = led_prev + pre_rows + ledger
    if out.resolve() == MON.resolve():
        write_csv(PH / "experiments/SEARCH_LEDGER.csv", full)
    else:                                  # a rerun into its own folder (PI-D-106 item 4) never touches the cumulative ledger
        write_csv(out / "SEARCH_LEDGER_ROWS.csv", ledger)
    tot = E.ledger_totals(full)
    jsave(out / "LEDGER_TOTALS.json", tot)
    run_log(out, "evaluate", t0, {"as_of_utc": iso(as_of), "ledger_verify": ver})
    print(json.dumps({s: {"n": prim[s].get("n_with_number"), "positives": prim[s].get("positives"), "days": prim[s].get("days"),
                          "verdict": metrics[i]["verdict"]} for i, s in enumerate(SHORT[t] for t in TARGETS)} | {"n_search": tot["n_search"]}))
    return 0 if ver["ok"] and tot["n_search"] == N_SEARCH else 1


# ---------------------------------------------------------------- drift (checklist rule 9) and response (rule 10)
def cmd_drift(out: Path) -> int:
    sys.addaudithook(_hook)
    t0 = time.time()
    p12 = _p12()
    inp = p12.Inputs(str(DEV_STORE), str(FS_STORE))
    idx = M.load(LEDGER)
    as_of = max(float(o["recorded_at"]) for o in M.current_outcomes(idx).values())
    cards = p12.load_cards()
    # D1: B2 input columns, training rows at H (union over targets, one row per decision) against the window's rows
    cols = list(B.B2_COLUMNS)
    ref_rows = {}
    for t in TARGETS:
        for e in inp.training(t):
            ref_rows[e.decision_key] = e.x
    cur_rows = {e.decision_key: e.x for e in inp.examples(L.T1)}
    d1 = M.feature_drift({c: [x.get(c) for x in ref_rows.values()] for c in cols}, {c: [x.get(c) for x in cur_rows.values()] for c in cols})
    # D7: regime labels as of each decision
    ref_reg = [inp.series[float(inp.dtab[k]["decision_time"])]["label"] for k in ref_rows if float(inp.dtab[k]["decision_time"]) in inp.series]
    cur_reg = [inp.extras[k]["regime"] for k in inp.keys]
    d7 = M.regime_drift(cur_reg, ref_reg)
    # D4: B2 number share among Solana decisions with a snapshot price, window against the retrospective holdout predictions
    preds, attrs = read_predictions(MON)
    price = {k for k, d in inp.dtab.items() if L.snapshot_price(d) is not None}
    cur_k = [k for k in inp.keys if k in price]
    cur_n = sum(1 for k in cur_k if math.isfinite(preds[("T1_24h", k)].get("P07_B2", float("nan"))))
    hold = [r for r in csv.DictReader(open(AUD / "phase_12/validation/HOLDOUT_PREDICTIONS.csv"))
            if r["candidate"] == "P07_B2" and r["target_short"] == "T1_24h" and r["decision_key"] in price]
    d4 = M.coverage_drift(cur_n, len(cur_k), sum(1 for r in hold if r["number"] != ""), len(hold))
    d4["system_publication_coverage"] = {"documents": len(M.documents(idx)),
                                         "forecasts": sum(1 for d in M.documents(idx).values() if d["prediction_status"] == "FORECAST")}
    # D6 and D8
    calls = json.loads((PH / "evidence/label_calls.json").read_text()) if (PH / "evidence/label_calls.json").exists() else []
    ohlcv = [c for c in calls if c["kind"].startswith("ohlcv")]
    # CP19-1 (m4): the alarm counts final reads of the planned decisions; attempts and retries are reported beside it
    plan = json.loads((WORK / "read_plan.json").read_text())["decisions"] if (WORK / "read_plan.json").exists() else []
    rmap = json.loads((WORK / "read_map.json").read_text()) if (WORK / "read_map.json").exists() else {}
    con = L.connect(DEV_STORE)
    final_failed = 0
    for pd in plan:
        rk = rmap.get(pd["decision_key"])
        if rk is None or not L.read_from_store(con, rk).ok:
            final_failed += 1
    con.close()
    d6 = M.source_state(newest_export_time=REF_TIME, now=as_of, reads_total=len(plan), reads_failed=final_failed, depth_rows=0,
                        attempts_total=len(ohlcv), attempts_failed=sum(1 for c in ohlcv if c["http"] != 200))
    d6["depth_note"] = ("forward depth collector (feature/backtesting D-BT-034, D-BT-035) built and pushed, not deployed on Elving's "
                        "computer; the hourly task runs four steps without collect: no depth snapshot exists for the window")
    d8 = M.model_age(as_of, H, [float(inp.hold[k]["decision_time"]) for k in inp.keys])
    sc = M.scorable(idx, as_of)
    per_target, notices, resp_payloads = {}, {}, []
    from memelab.predictive import registry as R
    rdir = AUD / "phase_16/registry"
    entries = R.read_entries(rdir / "entries")
    events = R.read_log((rdir / "REGISTRY_LOG.jsonl").read_text())
    words = {L.T1: "T1 (24 hours, +25% before -15%)", L.T1B: "T1b (6 hours, +25% before -15%)", L.T2: "T2 (24 hours, halving or halt)"}
    for t in TARGETS:
        s = SHORT[t]
        rows = [o for o in sc if o["target"] == t and o["chain"] == "solana"]
        y = [int(o["label"]) for o in rows]
        b0 = [preds[(s, o["decision_key"])].get("P07_B0", float("nan")) for o in rows]
        b2 = [preds[(s, o["decision_key"])].get("P07_B2", float("nan")) for o in rows]
        d2 = M.label_rate_drift(cards[(s, "P07_B0")]["card"]["body"]["p"], y)
        d3a = [M.calibration_drift(y, b0, "P07_B0"), M.calibration_drift(y, b2, "P07_B2")]
        stream = [(max(float(o["label_observed_at"]), float(o["label_matures_at"])), (pb2 - yy) ** 2 - (pb0 - yy) ** 2)
                  for o, yy, pb0, pb2 in zip(rows, y, b0, b2) if math.isfinite(pb0) and math.isfinite(pb2)]
        d3b = M.page_hinkley_alarms(stream)
        d5 = M.support_state(len(y), sum(y))
        mons = [d1, d2, *d3a, d3b, d4, d5, d6, d7, d8]
        states = M.target_states(mons)
        pin = R.resolve(events, entries, t, as_of)
        act = M.response(states, pin_mode=pin["mode"], level=None)
        facts = [f"{len(y)} matured labelled events with {sum(y)} positive (minimum 50 and 10 per class)",
                 f"label-rate monitor {d2['state']}", f"calibration monitors {d3a[0]['state']} (B0) and {d3a[1]['state']} (B2)",
                 f"feature monitor {d1['state']} (OK on {d1['columns_ok']} of {d1['columns_total']} columns, "
                 f"{d1['columns_insufficient']} not measurable)", f"regime monitor {d7['state']}",
                 f"label reads: {d6['reads_failed']} of {d6['reads_total']} planned decisions without a usable read "
                 f"({d6['attempts_failed']} of {d6['attempts_total']} attempts retried)"]
        txt = M.notice(words[t], states, act, facts)
        per_target[s] = {"D2": d2, "D3_calibration": d3a, "D3_page_hinkley": d3b, "D5": d5, "states": states, "pin": pin["mode"],
                         "response": act, "notice": txt}
        notices[s] = txt
        resp_payloads.append({"kind": "RESPONSE", "response_id": "rs_" + M.sha([s, as_of, states, act["action"]])[:40], "target": t,
                              "as_of": as_of, "states": states, "pin_mode": pin["mode"], "action": act["action"], "notice": txt,
                              "automatic_retrain": False})
    report = {"as_of_utc": iso(as_of), "thresholds": {"psi": [M.PSI_WATCH, M.PSI_ALERT], "min_feature_values": M.MIN_FEATURE_VALUES,
                                                      "missing_share_alert": M.MISSING_SHARE_ALERT, "min_labelled_for_rate": M.MIN_LABELLED_FOR_RATE,
                                                      "min_rows_for_calibration": M.MIN_ROWS_FOR_CALIBRATION, "page_hinkley": M.DRIFT,
                                                      "coverage_diff_alert": M.COVERAGE_DIFF_ALERT, "source_max_age_s": M.SOURCE_MAX_AGE_S,
                                                      "read_failure_share_alert": M.READ_FAILURE_SHARE_ALERT,
                                                      "regime_unseen_share_alert": M.REGIME_UNSEEN_SHARE_ALERT},
              "D1_feature": d1, "D4_prediction_rate": d4, "D6_sources": d6, "D7_regime": d7, "D8_model_age": d8, "per_target": per_target}
    out.mkdir(parents=True, exist_ok=True)
    jsave(out / "DRIFT_REPORT.json", report)
    mon = {"kind": "MONITOR", "monitor_id": "mo_" + M.sha([as_of, fsha(out / "DRIFT_REPORT.json")])[:40], "as_of": as_of,
           "report_file": "monitoring/DRIFT_REPORT.json", "report_sha256": fsha(out / "DRIFT_REPORT.json"),
           "states": {SHORT[t]: per_target[SHORT[t]]["states"] for t in TARGETS}}
    led = M.append(LEDGER, [mon] + resp_payloads)
    run_log(out, "drift", t0, {"ledger": led})
    print(json.dumps({s: {"states": v["states"], "action": v["response"]["action"]} for s, v in per_target.items()}
                     | {"D1": d1["state"], "D4": d4["state"], "D6": d6["codes"], "D7": d7["state"], "D8": d8["state"]}))
    return 0


# ---------------------------------------------------------------- rollback demo (fixtures; TEST_ONLY)
def rollback_demo() -> dict:
    """A fixture registry (the Phase 16 test fixtures: B2 at SHADOW pinned first, a model at VALIDATED_EXPERIMENTAL pinned later);
    matured losses where the model loses to B0 drive the Page-Hinkley alarm; serve then blocks DRIFT_ALERT, the response policy
    says DEGRADE_TO_SHADOW, rollback_event falls back to the earlier SHADOW pin; a second alarm on B2 rolls back to
    NO_VIABLE_CHAMPION. Earlier pins resolve unchanged and the log only grows."""
    from memelab.predictive import registry as R
    reg = _load("p19_registry_fixtures", "tests/test_predictive_registry.py")
    ents, ctx = reg.fixture_registry()
    rt = reg.runtime()
    events = R.chain_events(ctx["initial"])
    text0 = "".join(R.canon(e) + "\n" for e in events)
    tgt = reg.FX_TARGET
    inf = [(f"fx-{i}", 0.2 + 0.01 * i, "") for i in range(5)]
    base = C.parse_utc("2026-10-23T00:00:00Z")
    rng = np.random.default_rng(19)
    stream_m = [(base + 600 * i, float(rng.normal(0.0, 0.01) + (0.0 if i < 20 else 0.25))) for i in range(80)]
    ph_m = M.page_hinkley_alarms(stream_m)
    alarm_m = ph_m["alarms"][0]
    T = alarm_m + 3600
    sv = R.serve(events, ents, tgt, T, runtime=rt, drift_alarms=[alarm_m], inference=inf, root=REPO, allow_fixture=True)
    st = M.target_states([ph_m])
    act = M.response(st, pin_mode="CHAMPION", level=ents[sv["resolved"]["champion"]]["promotion"]["level"])
    rb1 = R.rollback_event(events, ents, tgt, reason="DRIFT_ALERT", as_of_utc=iso(T),
                           usable=lambda e: e["promotion"]["level"] in R.PUBLISHABLE_LEVELS and e["entry_id"] != ctx["model"],
                           root=REPO, allow_fixture=True)
    events1 = events + R.chain_events([rb1], prev=_last(events), start_seq=len(events))
    after1 = R.resolve(events1, ents, tgt, T + 60)
    sv_b2 = R.serve(events1, ents, tgt, T + 60, runtime=rt, drift_alarms=[], inference=inf, root=REPO, allow_fixture=True)
    stream_b = [(T + 600 * i, float(rng.normal(0.0, 0.01) + (0.0 if i < 15 else 0.25))) for i in range(80)]
    ph_b = M.page_hinkley_alarms(stream_b)
    alarm_b = ph_b["alarms"][0]
    T2 = alarm_b + 3600
    sv2 = R.serve(events1, ents, tgt, T2, runtime=rt, drift_alarms=[alarm_b], inference=inf, root=REPO, allow_fixture=True)
    act2 = M.response(M.target_states([ph_b]), pin_mode="CHAMPION", level=ents[sv2["resolved"]["champion"]]["promotion"]["level"])
    rb2 = R.rollback_event(events1, ents, tgt, reason="DRIFT_ALERT", as_of_utc=iso(T2),
                           usable=lambda e: e["promotion"]["level"] in R.PUBLISHABLE_LEVELS and e["entry_id"] not in (ctx["model"], ctx["b2"]),
                           root=REPO, allow_fixture=True)
    events2 = events1 + R.chain_events([rb2], prev=_last(events1), start_seq=len(events1))
    after2 = R.resolve(events2, ents, tgt, T2 + 60)
    text2 = "".join(R.canon(e) + "\n" for e in events2)
    before_model = R.resolve(events2, ents, tgt, C.parse_utc(ctx["t_model_pin"]) + 60)
    notice_txt = M.notice("T1 fixture (24 hours, +25% before -15%)", st, act, [f"Page-Hinkley alarm at {iso(alarm_m)} on 80 matured pairs"])
    return {"evidence_class": "FIXTURE_TEST_ONLY", "model_alarm_utc": iso(alarm_m), "serve_at_alarm": {
                "use_champion": sv["use_champion"], "blocking": [b["state"] for b in sv["blocking"]], "rollback_required": sv["rollback_required"],
                "retrain": sv["retrain"]},
            "response_1": act, "rollback_1": {"mode": after1["mode"], "champion_is_b2": after1["champion"] == ctx["b2"],
                                              "reasons": after1["reasons"]},
            "serve_after_rollback_1": {"use_champion": sv_b2["use_champion"], "blocking": [b["state"] for b in sv_b2["blocking"]]},
            "b2_alarm_utc": iso(alarm_b), "response_2": act2, "rollback_2": {"mode": after2["mode"], "reasons": after2["reasons"]},
            "earlier_pin_unchanged": before_model["champion"] == ctx["model"] and before_model["mode"] == "CHAMPION",
            "log_append_only": R.is_append_only(text0, text2), "log_events": len(events2), "notice": notice_txt}


def _last(events):
    from memelab.predictive import registry as R
    return R.line_sha(R.canon(events[-1]))


def cmd_rollback(out: Path) -> int:
    sys.addaudithook(_hook)
    t0 = time.time()
    r = rollback_demo()
    jsave(out / "ROLLBACK_DEMO.json", r)
    run_log(out, "rollback", t0, {})
    ok = (r["serve_at_alarm"]["rollback_required"] and "DRIFT_ALERT" in r["serve_at_alarm"]["blocking"] and r["rollback_1"]["champion_is_b2"]
          and r["rollback_2"]["mode"] == "NO_VIABLE_CHAMPION" and r["earlier_pin_unchanged"] and r["log_append_only"])
    print(json.dumps({"ok": ok, "response_1": r["response_1"]["action"], "rollback_2": r["rollback_2"]["mode"]}))
    return 0 if ok else 1


# ---------------------------------------------------------------- audit: F1 to F5 and the git order (CX-19)
def cmd_audit(out: Path) -> int:
    sys.addaudithook(_hook)
    t0 = time.time()
    tree = git("ls-tree", "-r", "--name-only", REF).splitlines()
    f1 = {"ref_has_predictive_package": any(p.startswith("memelab/predictive/") for p in tree),
          "ref_has_data_config": "data/config.json" in tree}
    f1["ok"] = not f1["ref_has_predictive_package"] and not f1["ref_has_data_config"]
    idx = M.load(LEDGER)
    cur = M.current_outcomes(idx)
    sets = [e["payload"] for e in idx.entries if e["payload"]["kind"] == "PREDICTION_SET"]
    want = {(d["decision_key"], t) for s in sets for d in s["decisions"] for t in TARGETS}
    f3 = {"pairs_expected": len(want), "pairs_with_outcome": len(want & set(cur)),
          "states": dict(sorted(Counter(o["state"] for o in cur.values()).items()))}
    f3["ok"] = f3["pairs_expected"] == f3["pairs_with_outcome"]
    f4 = {"documents_sha256": fsha(MON / "published/DOCUMENTS.jsonl"), "records_sha256": fsha(MON / "published/RECORDS.jsonl")}
    f4["ok"] = f4["documents_sha256"] == PUBLISHED["documents"] and f4["records_sha256"] == PUBLISHED["records"]
    rr = PH / "evidence/revision_reread.json"
    f5 = json.loads(rr.read_text())["summary"] if rr.exists() else {"note": "no re-read made"}
    f2 = {"rule": "the evaluation uses every scorable decision; the Phase 18 dry-run alert previews are never a selection",
          "evaluated_pairs_are_all_scorable": True}
    # git order: the commit that added the PREDICTION_SET precedes the first label call
    log = json.loads((MON / "OPENING_LOG.json").read_text())
    pred_commit = log["entries"][0]["head"]
    ctime = float(git("log", "-1", "--format=%ct", pred_commit).strip())
    calls = json.loads((PH / "evidence/label_calls.json").read_text())
    first = min(float(c["sent_t"]) for c in calls)
    in_head = git("show", f"{pred_commit}:audits/predictive-intelligence/phase_19/monitoring/OUTCOME_LEDGER.jsonl")
    preds_before = [json.loads(x)["payload"]["kind"] for x in in_head.splitlines() if x.strip()]
    order = {"predictions_commit": pred_commit, "predictions_commit_time_utc": iso(ctime), "first_label_call_utc": iso(first),
             "commit_before_first_call": ctime < first, "ledger_at_that_commit_kinds": dict(Counter(preds_before)),
             "no_outcome_at_that_commit": "OUTCOME" not in preds_before}
    ver = M.verify(LEDGER)
    res = {"F1_forecast_independent_watchlist": f1, "F2_alert_selection": f2, "F3_survivorship": f3, "F4_publication_revision": f4,
           "F5_vendor_revision_short_gap": f5, "order": order, "ledger_verify": ver}
    jsave(out / "FEEDBACK_AUDIT.json", res)
    run_log(out, "audit", t0, {})
    ok = f1["ok"] and f3["ok"] and f4["ok"] and order["commit_before_first_call"] and order["no_outcome_at_that_commit"] and ver["ok"]
    print(json.dumps({"ok": ok, "F3": f3, "order": {k: order[k] for k in ("commit_before_first_call", "no_outcome_at_that_commit")}}))
    return 0 if ok else 1


# ---------------------------------------------------------------- report: the deterministic calibration dashboard and ledger view
def _f(x, d=4):
    if x in (None, ""):
        return "n/a"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    return "n/a" if not math.isfinite(v) else f"{v:.{d}f}"


def cmd_report(out: Path) -> int:
    """PROSPECTIVE_REPORT.md and OUTCOME_LEDGER.md from the committed outputs in `out` (no computation on labels beyond reading the
    files; the same inputs give the same bytes)."""
    sys.addaudithook(_hook)
    prim = json.loads((out / "PRIMARY_RESULTS.json").read_text())
    counts = json.loads((out / "COUNTS.json").read_text())
    drift = json.loads((out / "DRIFT_REPORT.json").read_text())
    nc = json.loads((out / "NEGATIVE_CONTROLS.json").read_text())["NC1"]
    rb = json.loads((out / "ROLLBACK_DEMO.json").read_text())
    fa = json.loads((out / "FEEDBACK_AUDIT.json").read_text()) if (out / "FEEDBACK_AUDIT.json").exists() else None
    man = json.loads((MON / "PREREG_MANIFEST.json").read_text())        # prediction-time files always come from the committed folder
    traps = json.loads((MON / "PREOPEN_TRAPS.json").read_text())
    rep = json.loads((MON / "REPLAY_AUDIT.json").read_text())
    metrics = list(csv.DictReader(open(out / "PROSPECTIVE_METRICS.csv")))
    sens = list(csv.DictReader(open(out / "SENSITIVITY.csv")))
    shift = list(csv.DictReader(open(out / "SHIFT_BREAKDOWN.csv")))
    cal = list(csv.DictReader(open(out / "CALIBRATION_BINS.csv")))
    mis = list(csv.DictReader(open(out / "MISSES.csv")))
    h12 = list(csv.DictReader(open(AUD / "phase_12/validation/HOLDOUT_METRICS.csv")))
    L_ = []
    w = L_.append
    w("# Prospective outcome report (Phase 19, monitoring-1)")
    w("")
    w("Research evaluation of internal reference predictions of the frozen cards on the prospective holdout. Nothing here is a "
      "published probability: every published document of the window is ABSTAIN. Generated by `probes/run_prospective.py report` "
      "from the committed outputs of this folder.")
    w("")
    w(f"Window: decisions from {man['window_from_utc']} to {man['window_to_utc']} (exports up to `{man['ref'][:7]}`): "
      f"{man['window_decisions']} decisions, {man['solana_decisions']} Solana. Predictions fixed before any label read: "
      f"{man['prediction_rows']} rows, {man['documents']} system documents. Evaluation as of {prim['as_of_utc']}.")
    w("")
    w("## 1. Leakage and as-of tests (not accuracy)")
    w("")
    w(f"- Pre-opening traps on the window: {len(traps['failures'])} failures (NC2 future feature and allowlist, P13 card time, "
      f"training label after the cutoff, B2 refit equal to the frozen card). Replay audit: {'ok' if rep['ok'] else 'FAILED'}; "
      f"oldest card age at a window decision {max(v['max_age_days'] for v in rep['holdout'].values()):.2f} days (MODEL_STALE after 14).")
    w(f"- Feature version and feature set of the window snapshots equal the reference cards': {man['p46_feature_versions']['equal']}.")
    w(f"- The suite's leakage and isolation tests are recorded in the evidence; they say nothing about accuracy.")
    w("")
    w("## 2. Historical out-of-sample record (retrospective holdout, Phase 12; spent, cited, not recomputed)")
    w("")
    w("| Target | Model | n | Positives | BSS vs B0 | Verdict |")
    w("|---|---|---:|---:|---:|---|")
    for r in h12:
        if r["kind"] == "PRIMARY_HOLDOUT":
            w(f"| {r['target_short']} | {r['model']} | {r['n_with_number']} | {r['positives']} | {_f(r['bss'], 3)} | {r['verdict']} |")
    w("")
    w("## 3. Prospective shadow accuracy (this phase)")
    w("")
    w("Primary pair: P07_B2 against P07_B0 per target (the registry's references; no viable champion exists), Holm across the "
      "three targets, frozen verdict order (fewer than 5 decision days: INSUFFICIENT_DAYS; fewer than 50 events or 10 per class: "
      "INSUFFICIENT_EVENTS).")
    w("")
    w("Descriptive only (CP19-1, skeptic m6): no claim. With fewer than 5 decision days no governing interval exists and the p values "
      "are undefined; the mint interval is not the governing interval and is not a test; every count is far below 50 events with 10 per "
      "class. Every number below is PROVISIONAL_PENDING_REVISION_REREAD until the frozen 48 h re-read has run (PI-D-106).")
    w("")
    w("| Target | Scorable | Positives | Days | Mints | Brier B2 | Brier B0 | BSS (descriptive only) | Log loss B2 | Log loss B0 | "
      "Mint interval (not governing) | Verdict |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|")
    for t in TARGETS:
        s = SHORT[t]
        m = prim["primary"][s]["metric"]
        iv = f"{_f(m['bss_ci_mint_lo'], 3)} to {_f(m['bss_ci_mint_hi'], 3)}" if m.get("bss_ci_mint_lo") is not None else "n/a"
        w(f"| {s} | {m['n_with_number']} | {m['positives']} | {m['days']} | {m['mints']} | {_f(m['brier'])} | {_f(m['brier_ref'])} | "
          f"{_f(m['bss'], 3)} | {_f(m['log_loss'])} | {_f(m['log_loss_ref'])} | {iv} | {m['verdict']} |")
    w("")
    w("Outcome states per target (Solana decisions):")
    w("")
    for s, c in counts.items():
        w(f"- {s}: " + ", ".join(f"{k} {v}" for k, v in c["states_solana"].items()) + f"; decision days {', '.join(c['days']) or 'none'}")
    w("")
    w("Calibration in the large and minority metrics (P10, P24):")
    w("")
    w("| Target | Model | n | Mean prediction | Observed | Wilson 95% | In the large | Bins |")
    w("|---|---|---:|---:|---:|---|---|---:|")
    for r in cal:
        if r["view"] == "PRIMARY" and r["bin"] == "IN_THE_LARGE":
            m = next(x for x in metrics if x["target_short"] == r["target_short"] and x["kind"] == "PRIMARY_HOLDOUT")
            w(f"| {r['target_short']} | {r['model']} | {r['n']} | {_f(r['mean_pred'], 3)} | {_f(r['observed'], 3)} | "
              f"{_f(r['wilson_lo'], 3)} to {_f(r['wilson_hi'], 3)} | {r['ok']} | {m['cal_bins']} |")
    w("")
    for t in TARGETS:
        s = SHORT[t]
        mn = prim["primary"][s]["minority"]
        w(f"- {s}: prevalence {_f(mn['prevalence'], 3)} on {mn['n']}; AUC {_f(mn['auc'], 3)}, average precision "
          f"{_f(mn['average_precision'], 3)}; flags {', '.join(mn['flags']) or 'none'}.")
    w("")
    sec = [x for x in metrics if x["kind"] == "SECONDARY_HOLDOUT"]
    w(f"Secondary family: {len(sec)} card comparisons against B0 and B2; verdicts "
      + ", ".join(f"{v} {n}" for v, n in sorted(Counter(x['verdict'] for x in sec).items()))
      + "; selection status " + ", ".join(f"{v} {n}" for v, n in sorted(Counter(x['selection_status'] for x in sec).items()))
      + f" (Bonferroni over N_search {N_SEARCH}; max-T not computed below 5 decision days).")
    w("")
    w("NC1 (training-only shuffled B2): " + "; ".join(f"{s} mean BSS {_f(v['mean_bss'], 3)}, {v['verdict']}" for s, v in nc.items()) + ".")
    w("")
    w("Sensitivities of the primary pair: " + "; ".join(f"{r['target_short']} {r['view']} n {r['n_with_number']} {r['verdict']}"
                                                       for r in sens) + ".")
    w("")
    w(f"Breakdowns (P21, descriptive, no rate claimed below 20): {len(shift)} rows in SHIFT_BREAKDOWN.csv by day, route, regime, "
      "liquidity, launch age and status group.")
    w("")
    w("## 4. Drift monitors and response")
    w("")
    w(f"- D1 feature drift: {drift['D1_feature']['state']} (" + ", ".join(
        f"{c} {v['psi_state']}" + (f" PSI {_f(v['psi'], 3)}" if v.get('psi') is not None else "") for c, v in drift['D1_feature']['columns'].items()) + ")")
    w(f"- D4 prediction rate: {drift['D4_prediction_rate']['state']}; D6 sources: {', '.join(drift['D6_sources']['codes']) or 'OK'}; "
      f"D7 regime: {drift['D7_regime']['state']}; D8 model age: {drift['D8_model_age']['state']}, stale after "
      f"{drift['D8_model_age']['stale_after_utc']}.")
    for s, v in drift["per_target"].items():
        w(f"- {s}: D2 {v['D2']['state']}, D3 {v['D3_calibration'][0]['state']} (B0) and {v['D3_calibration'][1]['state']} (B2), "
          f"Page-Hinkley {v['D3_page_hinkley']['state']}, D5 {v['D5']['state']}; pin {v['pin']}; action {v['response']['action']}.")
    w("")
    w("Notices (plain text, dry run, nothing sent):")
    w("")
    for s, v in drift["per_target"].items():
        w(f"> {v['notice']}")
        w("")
    w(f"Rollback demo (fixtures, TEST_ONLY): drift on a pinned VALIDATED_EXPERIMENTAL fixture champion gives {rb['response_1']['action']} "
      f"(rolled back to the earlier SHADOW pin: {rb['rollback_1']['champion_is_b2']}); a second alarm gives {rb['response_2']['action']} "
      f"({rb['rollback_2']['mode']}); earlier pins unchanged: {rb['earlier_pin_unchanged']}; log append-only: {rb['log_append_only']}.")
    w("")
    w("## 5. Misses, feedback and selection checks")
    w("")
    w("Every decision and target of the window has a row in MISSES.csv: " + ", ".join(
        f"{k} {v}" for k, v in sorted(Counter(r['no_score_reason'] for r in mis).items())) + ".")
    if fa:
        w(f"- F1 forecast-independent watchlist: {fa['F1_forecast_independent_watchlist']['ok']}; F3 survivorship: "
          f"{fa['F3_survivorship']['pairs_with_outcome']} of {fa['F3_survivorship']['pairs_expected']} pairs have an outcome; "
          f"F4 publication revision: documents and records equal to the Phase 18 published run: {fa['F4_publication_revision']['ok']}; "
          f"F5 short-gap re-read: {fa['F5_vendor_revision_short_gap'].get('candles_changed', 'n/a')} changed of "
          f"{fa['F5_vendor_revision_short_gap'].get('candles_compared', 'n/a')} compared candles; the frozen 48 h re-read is owed.")
        w(f"- Order: predictions commit `{fa['order']['predictions_commit'][:7]}` at {fa['order']['predictions_commit_time_utc']}, first "
          f"label call {fa['order']['first_label_call_utc']}.")
    w("")
    w("Not reconciled: liquidity, exit capacity, catalyst and distribution outcomes (targets not frozen; the forward depth collector "
      "is not deployed, so no depth snapshot exists: EXECUTION_DATA_MISSING, COLLECTOR_NOT_DEPLOYED).")
    (out / "PROSPECTIVE_REPORT.md").write_text("\n".join(L_) + "\n")
    # the ledger view
    idx = M.load(LEDGER)
    ver = M.verify(LEDGER)
    kinds = Counter(e["payload"]["kind"] for e in idx.entries)
    cur = M.current_outcomes(idx)
    docs = M.documents(idx)
    G = []
    g = G.append
    g("# Outcome ledger (outcome-ledger-1)")
    g("")
    g("The machine record is `OUTCOME_LEDGER.jsonl` in this folder: one canonical JSON line per entry with `seq`, `prev` (the previous "
      "line's sha256) and `sha`. `memelab.predictive.monitoring.verify` rechecks the chain and replays every append rule. Rules "
      "(checklist rule 4): append only; a prediction or document is written once and never after its outcome; a LABELED outcome only "
      "at or after maturity with its read (URL with token=<mint>, response key, body sha256); PENDING and censored outcomes carry no "
      "label and are never scored; a final outcome is revised only by a new entry with `revision_of`, both kept.")
    g("")
    g(f"Entries {ver['entries']}, head `{ver['head']}`, verify {'ok' if ver['ok'] else 'FAILED'}. By kind: "
      + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) + ".")
    g("")
    g("| Decision (UTC) | Chain | Mint | Target | Document | Outcome | Class | Flags |")
    g("|---|---|---|---|---|---|---|---|")
    for (k, t), o in sorted(cur.items(), key=lambda kv: (kv[1]["decision_time"], kv[1]["mint"], kv[0][1])):
        d = docs.get((k, t))
        g(f"| {iso(o['decision_time'])} | {o['chain']} | `{o['mint']}` | {SHORT[t]} | {d['prediction_status'] if d else 'none'} | "
          f"{o['state']} | {o['label_class'] or ''} | {', '.join(o['flags'])} |")
    (out / "OUTCOME_LEDGER.md").write_text("\n".join(G) + "\n")
    print(json.dumps({"report_lines": len(L_), "ledger_rows": len(cur)}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("inputs", "predict", "outcomes", "evaluate", "drift", "rollback", "audit", "report"))
    ap.add_argument("out", nargs="?")
    a = ap.parse_args()
    if a.step == "inputs":
        return cmd_inputs()
    if a.step == "outcomes":
        return cmd_outcomes()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    return {"predict": cmd_predict, "evaluate": cmd_evaluate, "drift": cmd_drift, "rollback": cmd_rollback, "audit": cmd_audit,
            "report": cmd_report}[a.step](out)


if __name__ == "__main__":
    raise SystemExit(main())
