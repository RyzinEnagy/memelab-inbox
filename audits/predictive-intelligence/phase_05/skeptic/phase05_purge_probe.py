"""Phase 05 skeptic probe: does retrieval metadata recorded AFTER a decision change its provider-mode snapshot?
On a copy of the rebuilt store, every OK development pool gets one later honest read (2026-10-25, token=<mint>, HTTP 200) whose
vendor body has no candle, as when a dead pool's history is purged, recorded as a NO_DATA series with the same boundary. Stored
candles stay; the read only adds tombstones available at its own read time. Then every stored provider snapshot is recomputed.
Usage: python phase05_purge_probe.py CLONE STORE_COPY"""
import collections, json, sys
from pathlib import Path
clone = Path(sys.argv[1]); sys.path.insert(0, str(clone))
from memelab.predictive import store as S, features as F, sources as SRC
c = S.connect(sys.argv[2])
LATER = 1792915200.0          # 2026-10-25T00:00Z, after every decision in the store
ok = S.iter_rows(c, "SELECT * FROM predictive_source_status WHERE status='OK'")
for s in ok:
    body = json.dumps({"data": {"attributes": {"ohlcv_list": []}}, "meta": {"base": {"address": s["mint"]},
                                                                             "quote": {"address": "So11111111111111111111111111111111111111112"}}}).encode()
    url = SRC.gt_url(s["pool_address"], int(s["boundary_at"]), token=s["mint"])
    g = S.ingest_gt_response(c, {"url": url, "params": {"token": s["mint"]}, "retrieved_at": LATER, "http_status": 200, "body": body,
                                 "boundary_at": s["boundary_at"]}, chain="solana", mint=s["mint"], pool=s["pool_address"], now=LATER)
    S.record_series_status(c, chain="solana", mint=s["mint"], pool=s["pool_address"], series_id=s["series_id"] + "#later",
                           boundary_at=s["boundary_at"], need_from=s["need_from"], status="NO_DATA", detail="probe", response_keys=[g["response_key"]],
                           calls=1, candles_kept=0, last_end_at=None, checked_at=LATER, now=LATER)
c.commit()
n = collections.Counter(); feats = collections.Counter(); ex = None
for r in S.iter_rows(c, "SELECT snapshot_key FROM predictive_snapshots WHERE availability_mode='provider'"):
    same = F.recompute_matches(c, r["snapshot_key"])
    n[same] += 1
    if not same:
        s = F.stored_snapshot(c, r["snapshot_key"])
        again = F.features_as_of(c, s["chain"], s["mint"], s["decision_time"], "1")
        for a, b in zip(s["values"], again["values"]):
            if (a["value"], a["missing_reason"]) != (b["value"], b["missing_reason"]):
                feats[(a["feature_name"], a["missing_reason"] or "value", b["missing_reason"] or "value")] += 1
                ex = ex or (s["mint"], s["decision_time"], a["feature_name"], a["value"], a["missing_reason"], b["value"], b["missing_reason"])
print("pools given a later empty read:", len(ok))
print("provider snapshots unchanged/changed:", dict(n))
for k, v in feats.most_common(): print(" ", k, v)
print("example:", ex)
