"""Phase 05 skeptic counterexample CX-05: the vendor identity check trusts the recorded `params["token"]`, not the URL that was
requested. A real archived default read (no token= in its URL) of a pool whose mint is the QUOTE token is ingested with
params {"token": <mint>} (the caller's intent, the same slip as the phase's own first inbox15 pass). The store accepts it as
OK_TOKEN_PARAM, keeps the other token's candles as the mint's price, verify() is clean, and the feature snapshot carries them.
Usage: python phase05_counterexample.py CLONE"""
import csv, gzip, json, sys, urllib.parse
from pathlib import Path
clone = Path(sys.argv[1]); sys.path.insert(0, str(clone))
from memelab.predictive import store as S, sources as SRC, features as F
PH = clone / "audits/predictive-intelligence/phase_05"
rows = list(csv.DictReader(open(PH / "raw/MANIFEST.csv")))
bad = next(r for r in rows if r["identity_check"] == "MINT_IS_QUOTE")
good = next(r for r in rows if r["identity_check"] == "OK_TOKEN_PARAM" and r["pool"] == bad["pool"])
print("pool", bad["pool"], "mint", bad["mint"])
print("URL token param in the default read:", urllib.parse.parse_qs(urllib.parse.urlparse(bad["url"]).query).get("token"))
def store(rec, params_override=None):
    c = S.connect(":memory:")
    S.ingest_exports(c, SRC.export_versions(clone, "98338a8ba3c5e65c5850933a35c06885b6ef991a"), now=1.8e9)
    body = gzip.decompress((PH / "raw" / rec["file"]).read_bytes())
    p = json.loads(rec["params_json"]); p.update(params_override or {})
    g = S.ingest_gt_response(c, {"url": rec["url"], "params": p, "retrieved_at": float(rec["retrieved_t"]), "http_status": 200,
                                 "body": body, "boundary_at": float(rec["boundary_at"])}, chain="solana", mint=rec["mint"],
                             pool=rec["pool"], now=1.8e9)
    S.record_series_status(c, chain="solana", mint=rec["mint"], pool=rec["pool"], series_id="cx", boundary_at=float(rec["boundary_at"]),
                           need_from=0 + 1.0e9, status="OK" if g["identity_check"].startswith("OK") else "IDENTITY_MISMATCH",
                           detail=None, response_keys=[g["response_key"]], calls=1, candles_kept=g["kept"], last_end_at=None,
                           checked_at=float(rec["retrieved_t"]), now=1.8e9)
    d = c.execute("SELECT decision_time FROM predictive_decisions WHERE mint=? AND pool_address=? AND decision_time < ? ORDER BY decision_time DESC LIMIT 1",
                  (rec["mint"], rec["pool"], float(rec["boundary_at"]) + 1)).fetchone()
    snap = F.features_as_of(c, "solana", rec["mint"], d[0], "1")
    x = next(v for v in snap["values"] if v["feature_name"] == "xsrc_log_close_over_thesis_price")
    return g["identity_check"], g["kept"], x["value"], x["missing_reason"], S.verify(c)
print("honest record of the default read :", store(bad))
print("same bytes, params token=<mint>   :", store(bad, {"token": bad["mint"]}))
print("the real token=<mint> re-read     :", store(good))
