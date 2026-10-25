"""Phase 06 skeptic counterexample CX-S06: a quote-side pool whose response ignores token=<mint>.

Wrong but plausible: GeckoTerminal answers a token=<mint> request for a pool where the mint is the QUOTE token with its default
orientation (meta base = the other token, quote = the mint; candles price the other token). PI-D-038 notes the vendor's default
side has changed before. store.gt_identity accepts it as OK_TOKEN_PARAM because it only asks that the mint be in the pool and
the URL token equal the mint; it never checks that the vendor actually flipped the base to the mint. labels.build then labels
the decision from the other token's price path.

Real anchor: pool BTccxxTFi7a9xJTE1exKn38Jgie35s6gNeRxd8DM61Rc (ZEC / ZCAT, ZCAT = HcRLc9VDgjLeK154xDawfb1dmVJ98DoSqcwTHGqiDeJR is
quote in the vendor list), development decision 5c881e3466...: with token=<mint> the real body's meta has base = ZCAT and prices
near 0.046 (ZCAT); ZEC trades near 1,161 USD.

Run from the skeptic clone root:  MEMELAB_DB=<tmp> python -B /home/claude/pi_orchestration/skeptic/p06_counterexample_cx_s06.py
"""
import csv, gzip, json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd())); sys.path.insert(0, str(Path.cwd() / "tests"))
import test_predictive_labels as T
from memelab.predictive import labels as L, store as S

ZCAT, ZEC, POOL = "HcRLc9VDgjLeK154xDawfb1dmVJ98DoSqcwTHGqiDeJR", "A7bdiYdS5GjqGFtxf17ppRHtDKPkkRqbKtR27dxvQXaS", "BTccxxTFi7a9xJTE1exKn38Jgie35s6gNeRxd8DM61Rc"
DT = T.DT; TE = DT + 300
# ZEC path: flat near 1161, then +30% (a TARGET_FIRST for ZEC); ZCAT itself would have done something else entirely
rows = T.ref_rows(1161.0) + [T.H.candle(int(L.ceil_grid(TE)) + 600, c=1161.0, h=1161.0 * 1.3, l=1160.0)] + T.grid(TE + 3600, TE + 2 * 86400, c=1161.0)
b = L.needed_boundary(L.T2, DT)
url = T.H.GT.format(pool=POOL, b=int(b)) + f"&token={ZCAT}"
body = json.dumps({"data": {"id": "x", "type": "ohlcv_request_response", "attributes": {"ohlcv_list": rows}},
                   "meta": {"base": {"address": ZEC, "symbol": "ZEC"}, "quote": {"address": ZCAT, "symbol": "ZCAT"}}}).encode()
rd = L.read_from_body(body, mint=ZCAT, pool=POOL, url=url, boundary=b, retrieved_at=T.LATE, http_status=200, response_key="cx")
print("identity:", rd.identity, "ok:", rd.ok, "candles:", len(rd.candles))
d = T.dec(mint=ZCAT, pool=POOL, price=0.0456, vol=2e6, route="CURRENT_VENDOR_LIST")
recs, elig = L.build(L.Universe([d], as_of=T.LATE, read_of={d["decision_key"]: rd}))
for r in recs:
    print(r["target"][-20:], r["state"], r["label_class"], "p0", r.get("p0"), "flags", r.get("flags"))
caught = (not rd.ok) or any(r["state"] != "LABELED" for r in recs)
print("CAUGHT by current code:", caught)

# Proposed check: with token=<mint>, require meta.base == mint. It holds on every real development read.
P6 = Path.cwd() / "audits/predictive-intelligence/phase_06"
n = bad = 0
for m in csv.DictReader(open(P6 / "raw/MANIFEST.csv")):
    if m["file"].startswith("lists/") or m["http_status"] != "200":
        continue
    meta = json.loads(gzip.open(P6 / "raw" / m["file"]).read())["meta"]
    n += 1; bad += meta["base"]["address"] != m["mint"]
print(f"real development reads with token=<mint>: {n}; meta.base != mint: {bad}")
print("proposed check would refuse the counterexample:", json.loads(body)["meta"]["base"]["address"] != ZCAT)
print("snapshot price vs P0 ratio:", recs[0].get("p0") / d["snapshot"]["price"])
