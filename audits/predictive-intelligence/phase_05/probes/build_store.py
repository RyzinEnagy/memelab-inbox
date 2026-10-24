"""Phase 05: build the real point-in-time store from the state exports on main and a bounded GeckoTerminal backfill.

The store lives outside the repository (STORE below, a private SQLite file). Committed outputs: the call log, the plan, the raw
body archive (gzip) with its manifest, and summaries under audits/predictive-intelligence/phase_05/.

    python -B build_store.py exports            # read 89 export versions from git at REF, store decision records
    python -B build_store.py plan               # write data/backfill_plan.json (holdout seal checked)
    python -B build_store.py fetch              # paced GeckoTerminal reads (network), ingested as they arrive; resumable
    python -B build_store.py rebuild [SRC]      # replay every stored read of SRC (default: the first-run store) through the current code
    python -B build_store.py token              # re-fetch with token=<mint> the series whose reads priced another token
    python -B build_store.py reread N           # re-read N already-read requests (P07), ingested as later reads
    python -B build_store.py snapshots          # one persisted snapshot per decision, provider and capture modes
    python -B build_store.py archive            # raw/ gzip bodies, raw/MANIFEST.csv and data/series_status.json from the store
    python -B build_store.py fromarchive PATH   # offline rebuild from the committed archive; snapshot hashes compared
    python -B build_store.py summary            # evidence/store_summary.json

Network: GeckoTerminal public OHLCV only, through runtime.CallGuard at 5.7 calls a minute (under the frozen 6), at most 1,200
calls, breaker after 5 consecutive failures, HTTP 429 back-off of 60 s. No label, barrier or class is computed.
"""
from __future__ import annotations

import collections
import csv
import gzip
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHASE = HERE.parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
from memelab.predictive import features as F  # noqa: E402
from memelab.predictive import runtime as R  # noqa: E402
from memelab.predictive import sources as SRC  # noqa: E402
from memelab.predictive import store as S  # noqa: E402

REF = "98338a8ba3c5e65c5850933a35c06885b6ef991a"     # origin/main as read by Phases 01 and 04
STORE = Path("/home/claude/pi_research/p05/predictive_store.sqlite")
CALLS = PHASE / "evidence" / "backfill_calls.json"
PLAN = PHASE / "data" / "backfill_plan.json"
PER_MIN = 5.7


def con():
    return S.connect(STORE)


def iso(t):
    import datetime as dt
    return None if t is None else dt.datetime.fromtimestamp(float(t), dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def cmd_exports():
    c = con()
    ex = SRC.export_versions(REPO, REF)
    r = S.ingest_exports(c, ex, now=time.time(), ref=REF)
    c.commit()
    print(json.dumps({k: v for k, v in r.items() if k != "refused"} | {"refused": len(r["refused"]),
                                                                       "skipped_versions": ex[-1].get("skipped_versions")}))


def cmd_plan():
    c = con()
    decs = S.iter_rows(c, "SELECT * FROM predictive_decisions ORDER BY decision_time, id")
    plan = SRC.plan_backfill(decs)
    SRC.check_plan(plan)
    scope = collections.Counter(SRC.fetch_scope(d) for d in decs)
    out = {"ref": REF, "holdout_start": iso(SRC.holdout_start()), "max_boundary_allowed": iso(SRC.holdout_start() - SRC.HOLDOUT_CONTACT_PAD_S),
           "max_boundary": iso(max(p["boundary"] for p in plan)), "series": len(plan),
           "decisions_in_plan": sum(p["decisions"] for p in plan), "fetch_scope": dict(sorted(scope.items())),
           "plan": [p | {"boundary_utc": iso(p["boundary"]), "need_from_utc": iso(p["need_from"])} for p in plan]}
    PLAN.parent.mkdir(parents=True, exist_ok=True)
    PLAN.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "plan"}))


def _log():
    return json.loads(CALLS.read_text()) if CALLS.exists() else []


def _fetch_plan(plan, tag, token_param=True):
    c = con()
    calls = _log()
    guard = R.CallGuard(max_per_min=PER_MIN, max_calls=1200 - len(calls))
    done = {r["series_id"] for r in S.iter_rows(c, "SELECT series_id FROM predictive_source_status WHERE status IN ('OK','NO_DATA')")}
    for p in plan:
        sid = p["series_id"] + tag
        if sid in done:
            continue

        def on_response(resp, p=p):
            r = S.ingest_gt_response(c, resp, chain=p["chain"], mint=p["mint"], pool=p["pool"], now=time.time())
            c.commit()
            calls.append({"n": len(calls), "series_id": sid, "url": resp["url"], "requested_at": iso(resp["params"]["requested_at"]),
                          "retrieved_at": iso(resp["retrieved_at"]), "retrieved_t": resp["retrieved_at"],
                          "http": resp["http_status"], "bytes": len(resp["body"]),
                          "sha256": hashlib.sha256(resp["body"]).hexdigest(), "response_key": r["response_key"],
                          "kept": r.get("kept"), "added": r.get("added"), "revisions": r.get("revisions"),
                          "vanished": r.get("vanished"), "reads": r.get("reads"), "dropped_after_boundary": r.get("dropped"),
                          "refused": r.get("refused")})
            CALLS.parent.mkdir(parents=True, exist_ok=True)
            CALLS.write_text(json.dumps(calls, indent=1) + "\n")
            return r

        res = SRC.fetch_series(p, http_get=SRC.curl_get, guard=guard, on_response=on_response, token_param=token_param)
        S.record_series_status(c, chain=p["chain"], mint=p["mint"], pool=p["pool"], series_id=sid, boundary_at=p["boundary"],
                               need_from=p["need_from"], status=res["status"], detail=res["detail"],
                               response_keys=res["response_keys"], calls=res["calls"], candles_kept=res["candles_kept"],
                               last_end_at=res["last_end_at"], checked_at=res["checked_at"], now=time.time(),
                               period_s=res["period_s"])
        c.commit()
        print(json.dumps({"series": sid[:20], "status": res["status"], "calls": res["calls"], "kept": res["candles_kept"],
                          "total_calls": len(calls)}), flush=True)
        if res["status"] in ("CIRCUIT_OPEN", "CALL_CAP_REACHED"):
            print("stopping: " + res["status"], flush=True)
            break


def cmd_fetch():
    plan = json.loads(PLAN.read_text())["plan"]
    _fetch_plan(plan, "")


FIRST = STORE.with_name("predictive_store_firstread.sqlite")


def cmd_rebuild(source=None):
    """Rebuild the store with the current code from the first run's stored reads (no network). The first backfill ran before
    the identity check existed and without token=<mint>; its bodies are replayed in retrieval order through
    store.ingest_gt_response, so a body that prices another token is refused, and each series keeps its original status unless
    one of its reads failed the identity check (IDENTITY_MISMATCH)."""
    import sqlite3
    src = Path(source) if source else FIRST
    old = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    old.row_factory = sqlite3.Row
    if STORE.exists():
        raise SystemExit(f"{STORE} exists: move it away first")
    c = con()
    ex = SRC.export_versions(REPO, REF)
    S.ingest_exports(c, ex, now=time.time(), ref=REF)
    c.commit()
    res = {}
    for r in old.execute("SELECT * FROM predictive_raw_responses WHERE source_id='geckoterminal-ohlcv' ORDER BY retrieved_at, id"):
        params = json.loads(r["request_json"])
        resp = {"url": r["request_url"], "params": params, "retrieved_at": r["retrieved_at"], "http_status": r["http_status"],
                "body": gzip.decompress(r["body_gzip"]), "boundary_at": r["boundary_at"], "timeframe": params.get("timeframe", "minute"),
                "aggregate": int(params.get("aggregate", 5)), "collector": r["collector"]}
        out = S.ingest_gt_response(c, resp, chain=r["chain"], mint=r["mint"], pool=r["pool_address"], now=time.time())
        assert out["response_key"] == r["response_key"]
        res[r["response_key"]] = out
    c.commit()
    n = collections.Counter()
    for s in old.execute("SELECT * FROM predictive_source_status ORDER BY checked_at, id"):
        keys = json.loads(s["response_keys_json"])
        bad = [res[k]["identity_check"] for k in keys if res[k].get("identity_check") and not res[k]["identity_check"].startswith("OK")]
        status = "IDENTITY_MISMATCH" if bad else s["status"]
        kept = sum(res[k].get("kept") or 0 for k in keys) if not bad else 0
        S.record_series_status(c, chain=s["chain"], mint=s["mint"], pool=s["pool_address"], series_id=s["series_id"],
                               boundary_at=s["boundary_at"], need_from=s["need_from"], status=status,
                               detail=bad[0] if bad else s["detail"], response_keys=keys, calls=s["calls"], candles_kept=kept,
                               last_end_at=None if bad else s["last_end_at"], checked_at=s["checked_at"], now=time.time(),
                               period_s=s["period_s"] if "period_s" in s.keys() else 300)
        n[status] += 1
    c.commit()
    ids = collections.Counter(o.get("identity_check") for o in res.values())
    print(json.dumps({"responses": len(res), "identity": dict(ids), "series": dict(n), "counts": S.table_counts(c)}))


def cmd_token():
    """Re-fetch, with token=<mint>, every planned series whose first read priced another token."""
    c = con()
    bad = {r["series_id"] for r in S.iter_rows(c, "SELECT series_id FROM predictive_source_status WHERE status='IDENTITY_MISMATCH'")}
    plan = [p for p in json.loads(PLAN.read_text())["plan"] if p["series_id"] in bad]
    print(json.dumps({"refetch": [p["series_id"] for p in plan]}))
    _fetch_plan(plan, "#token")


def cmd_reread(n):
    """Re-read every page of N series chosen by a fixed rule (every k-th series of the plan whose first read was the mint's
    own price), with the first run's exact request (no token parameter), as a new series id: any difference is the vendor's."""
    c = con()
    ok = {r["series_id"] for r in S.iter_rows(c, "SELECT series_id FROM predictive_source_status WHERE status='OK'")}
    plan = [p for p in json.loads(PLAN.read_text())["plan"] if p["series_id"] in ok]
    k = max(1, len(plan) // int(n))
    pick = plan[::k][: int(n)]
    _fetch_plan(pick, "#reread1", token_param=False)


def cmd_snapshots():
    c = con()
    now = time.time()
    out = {}
    for mode in F.MODES:
        t0 = time.time()
        r = F.build_snapshots(c, feature_version=F.FEATURE_VERSION, mode=mode, now=now)
        out[mode] = {"added": r["snapshots_added"], "skipped": len(r["skipped"]), "seconds": round(time.time() - t0, 1)}
    print(json.dumps(out))


def cmd_archive():
    c = con()
    raw = PHASE / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in S.responses(c, S.SOURCE_GT):
        body = gzip.decompress(r["body_gzip"])
        assert hashlib.sha256(body).hexdigest() == r["body_sha256"]
        name = f"gt_{r['body_sha256'][:16]}_{r['response_key'][:8]}.json.gz"
        data = S.gz(body)
        (raw / name).write_bytes(data)
        rows.append({"file": name, "file_sha256": hashlib.sha256(data).hexdigest(), "body_sha256": r["body_sha256"],
                     "body_bytes": r["body_bytes"], "response_key": r["response_key"], "url": r["request_url"],
                     "retrieved_at": iso(r["retrieved_at"]), "retrieved_t": repr(r["retrieved_at"]), "http_status": r["http_status"],
                     "chain": r["chain"], "pool": r["pool_address"], "mint": r["mint"], "boundary_at": r["boundary_at"],
                     "identity_check": r["identity_check"], "params_json": r["request_json"]})
    with open(raw / "MANIFEST.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    status = [{k: v for k, v in r.items() if k not in ("id", "recorded_at")}
              for r in S.iter_rows(c, "SELECT * FROM predictive_source_status ORDER BY checked_at, id")]
    (PHASE / "data" / "series_status.json").write_text(json.dumps(status, indent=1, sort_keys=True) + "\n")
    total = sum((raw / x["file"]).stat().st_size for x in rows)
    print(json.dumps({"files": len(rows), "bytes": total, "series": len(status)}))


def cmd_fromarchive(out_path):
    """Rebuild a store offline from committed artifacts only (raw/MANIFEST.csv, raw/*.json.gz, data/series_status.json, git at
    REF), build its provider snapshots and compare every snapshot hash with the real store's."""
    out = Path(out_path)
    if out.exists():
        out.unlink()
    c = S.connect(out)
    S.ingest_exports(c, SRC.export_versions(REPO, REF), now=time.time(), ref=REF)
    with open(PHASE / "raw" / "MANIFEST.csv") as fh:
        rows = sorted(csv.DictReader(fh), key=lambda r: float(r["retrieved_t"]))
    for r in rows:
        data = (PHASE / "raw" / r["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == r["file_sha256"]
        body = gzip.decompress(data)
        assert hashlib.sha256(body).hexdigest() == r["body_sha256"]
        params = json.loads(r["params_json"])
        tf, agg = params.get("timeframe", "minute"), int(params.get("aggregate", 5))
        got = S.ingest_gt_response(c, {"url": r["url"], "params": params, "retrieved_at": float(r["retrieved_t"]),
                                       "http_status": int(r["http_status"]), "body": body,
                                       "boundary_at": float(r["boundary_at"]) if r["boundary_at"] else None, "timeframe": tf,
                                       "aggregate": agg}, chain=r["chain"], mint=r["mint"], pool=r["pool"], now=time.time())
        assert got["response_key"] == r["response_key"], r["file"]
    for s in json.loads((PHASE / "data" / "series_status.json").read_text()):
        S.record_series_status(c, chain=s["chain"], mint=s["mint"], pool=s["pool_address"], series_id=s["series_id"],
                               boundary_at=s["boundary_at"], need_from=s["need_from"], status=s["status"], detail=s["detail"],
                               response_keys=json.loads(s["response_keys_json"]), calls=s["calls"], candles_kept=s["candles_kept"],
                               last_end_at=s["last_end_at"], checked_at=s["checked_at"], now=time.time(), period_s=s["period_s"])
    c.commit()
    F.build_snapshots(c, feature_version=F.FEATURE_VERSION, mode="provider", now=time.time())
    real = con()
    a = {r["snapshot_key"]: r["snapshot_sha256"] for r in S.iter_rows(c, "SELECT snapshot_key, snapshot_sha256 FROM predictive_snapshots")}
    b = {r["snapshot_key"]: r["snapshot_sha256"] for r in S.iter_rows(real, "SELECT snapshot_key, snapshot_sha256 FROM "
                                                                            "predictive_snapshots WHERE availability_mode='provider'")}
    res = {"snapshots_rebuilt": len(a), "snapshots_real": len(b), "identical": a == b,
           "differ": sum(1 for k in a if b.get(k) != a[k]), "counts": S.table_counts(c),
           "real_counts": S.table_counts(real), "verify_problems": S.verify(c)}
    (PHASE / "evidence" / "rebuild_from_archive.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps(res))


def cmd_summary():
    c = con()
    out = {"store": str(STORE), "store_sha256_note": "the store file changes with every write; its tables are summarised here",
           "counts": S.table_counts(c), "verify_problems": S.verify(c),
           "responses_by_http": dict(collections.Counter(r["http_status"] for r in S.responses(c, S.SOURCE_GT))),
           "series_status": dict(collections.Counter(r["status"] for r in S.iter_rows(c, "SELECT status FROM predictive_source_status"))),
           "candle_bases": dict(collections.Counter(r["available_basis"] for r in S.iter_rows(c, "SELECT available_basis FROM predictive_candles"))),
           "vanished": c.execute("SELECT COUNT(*) FROM predictive_candles WHERE vanished=1").fetchone()[0],
           "revisions": c.execute("SELECT COUNT(*) FROM predictive_candles WHERE available_basis='REVISION_FIRST_READ'").fetchone()[0],
           "dropped_after_boundary": c.execute("SELECT COALESCE(SUM(candles_dropped_after_boundary),0) FROM predictive_raw_responses").fetchone()[0],
           "refused_candles": c.execute("SELECT COALESCE(SUM(candles_refused),0) FROM predictive_raw_responses").fetchone()[0]}
    (PHASE / "evidence").mkdir(parents=True, exist_ok=True)
    (PHASE / "evidence" / "store_summary.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps(out))


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"exports": cmd_exports, "plan": cmd_plan, "fetch": cmd_fetch, "snapshots": cmd_snapshots, "archive": cmd_archive,
     "summary": cmd_summary,
     "token": cmd_token}.get(cmd, lambda: cmd_fromarchive(sys.argv[2]) if cmd == "fromarchive" else (
        cmd_rebuild(sys.argv[2] if len(sys.argv) > 2 else None) if cmd == "rebuild" else cmd_reread(sys.argv[2])))()
