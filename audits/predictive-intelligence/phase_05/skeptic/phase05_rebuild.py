"""Phase 05 skeptic: independent offline rebuild of the point-in-time store from committed artifacts only, both modes,
compared with a copy of the phase's real store. Usage: python phase05_rebuild.py CLONE REALSTORE_COPY OUT"""
import collections, csv, gzip, hashlib, json, sqlite3, sys, time
from pathlib import Path
clone, real_p, out_p = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
sys.path.insert(0, str(clone))
from memelab.predictive import store as S, sources as SRC, features as F
PH = clone / "audits/predictive-intelligence/phase_05"
REF = "98338a8ba3c5e65c5850933a35c06885b6ef991a"
if out_p.exists(): out_p.unlink()
c = S.connect(out_p)
ex = SRC.export_versions(clone, REF)
r = S.ingest_exports(c, ex, now=1.8e9, ref=REF)
print("exports", r["exports"], "events", r["decision_events"], "added", r["decisions_added"], "refused", r["refused"])
rows = sorted(csv.DictReader(open(PH / "raw/MANIFEST.csv")), key=lambda r: float(r["retrieved_t"]))
ingest = {}
for m in rows:
    data = (PH / "raw" / m["file"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == m["file_sha256"]
    body = gzip.decompress(data)
    assert hashlib.sha256(body).hexdigest() == m["body_sha256"]
    p = json.loads(m["params_json"])
    g = S.ingest_gt_response(c, {"url": m["url"], "params": p, "retrieved_at": float(m["retrieved_t"]), "http_status": int(m["http_status"]),
                                 "body": body, "boundary_at": float(m["boundary_at"]), "timeframe": p.get("timeframe", "minute"),
                                 "aggregate": int(p.get("aggregate", 5))}, chain=m["chain"], mint=m["mint"], pool=m["pool"], now=1.8e9)
    assert g["response_key"] == m["response_key"]
    assert (g.get("identity_check") or "") == m["identity_check"], (m["file"], g.get("identity_check"), m["identity_check"])
    ingest[m["response_key"]] = (m, g)
# cross-check the committed series statuses against the raw reads they name
bad = []
st = json.loads((PH / "data/series_status.json").read_text())
for s in st:
    ks = json.loads(s["response_keys_json"])
    gs = [ingest[k][1] for k in ks]
    codes = [ingest[k][0]["http_status"] for k in ks]
    kept = sum(g.get("kept", 0) for g in gs if (g.get("identity_check") or "").startswith("OK"))
    ids = [g.get("identity_check") for g in gs if g.get("identity_check")]
    exp = None
    if any(i and not i.startswith("OK") for i in ids): exp = "IDENTITY_MISMATCH"
    elif codes and codes[-1] != "200": exp = "READ_FAILED"
    elif kept == 0: exp = "NO_DATA"
    else: exp = "OK"
    if exp != s["status"]: bad.append((s["series_id"], s["status"], exp, codes))
    S.record_series_status(c, chain=s["chain"], mint=s["mint"], pool=s["pool_address"], series_id=s["series_id"], boundary_at=s["boundary_at"],
                           need_from=s["need_from"], status=s["status"], detail=s["detail"], response_keys=ks, calls=s["calls"],
                           candles_kept=s["candles_kept"], last_end_at=s["last_end_at"], checked_at=s["checked_at"], now=1.8e9, period_s=s["period_s"])
c.commit()
print("series", len(st), collections.Counter(s["status"] for s in st), "status disagreements with raw", bad)
t0 = time.time()
for mode in F.MODES:
    print(mode, F.build_snapshots(c, feature_version="1", mode=mode, now=1.8e9)["snapshots_added"])
print("snapshots built in", round(time.time() - t0, 1), "s")
real = sqlite3.connect(real_p); real.row_factory = sqlite3.Row
a = {(r[0], r[1]): r[2] for r in c.execute("SELECT snapshot_key, availability_mode, snapshot_sha256 FROM predictive_snapshots")}
b = {(r[0], r[1]): r[2] for r in real.execute("SELECT snapshot_key, availability_mode, snapshot_sha256 FROM predictive_snapshots")}
print("rebuilt", len(a), "real", len(b), "identical", a == b, "differ", sum(1 for k in a if b.get(k) != a[k]))
for t in ("predictive_candles", "predictive_decisions", "predictive_raw_responses"):
    key = {"predictive_candles": "obs_key", "predictive_decisions": "decision_key", "predictive_raw_responses": "response_key"}[t]
    x = {r[0] for r in c.execute(f"SELECT {key} FROM {t}")}; y = {r[0] for r in real.execute(f"SELECT {key} FROM {t}")}
    print(t, len(x), len(y), "same keys", x == y)
x = {r[0]: tuple(r[1:]) for r in c.execute("SELECT obs_key, available_at, available_basis, revision_kind FROM predictive_candles")}
y = {r[0]: tuple(r[1:]) for r in real.execute("SELECT obs_key, available_at, available_basis, revision_kind FROM predictive_candles")}
print("candle availability identical", x == y, collections.Counter(v[1] for v in x.values()), collections.Counter(v[2] for v in x.values()))
print("verify", S.verify(c))
