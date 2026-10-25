"""Phase 06 skeptic: independent recomputation of the development labels from the committed raw archive.

Does NOT import memelab.predictive.labels (or contract, decisions, store). Reads:
  - decisions: a COPY of the private dev store (predictive_decisions rows only; no label table is read for the computation)
  - raw/MANIFEST.csv, raw/*.json.gz, raw/lists/*.json.gz, data/read_map.json (committed archive)
Rules re-implemented from TARGET_REGISTRY.md text (CC-01, CC-02, CC-03) and ACCEPTANCE values written out by hand.
Holdout decisions (decision_time in [2026-10-17, 2026-10-24)) are never classified here; only development and purged.

usage: python3 -I p06_independent_labels.py <clone_root> <dev_store_copy> <out_json>
"""
import csv, gzip, json, math, sqlite3, sys, hashlib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from urllib.parse import urlsplit, parse_qs

ROOT, DB, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
import os; MUT=os.environ.get("MUT","")
P6 = ROOT + "/audits/predictive-intelligence/phase_06"

def utc(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()

H0, P0T = utc("2026-10-17T00:00:00Z"), utc("2026-10-24T00:00:00Z")
PER, LAG_EXEC, LAG_PROV, FETCH_MARGIN = 300, 300, 300, 900
REF_MAX_AGE, VOL_INACTIVE, QUIET_LOOKBACK = 3600, 1000, 86400
TG = {  # name: horizon, confirm
    "T1": dict(h=86400, c=0), "T1b": dict(h=21600, c=0), "T2": dict(h=86400, c=86400)}

def matures(t, dt):
    return dt + LAG_EXEC + TG[t]["h"] + TG[t]["c"] + FETCH_MARGIN

def split(t, dt):
    if dt >= P0T: return "PROSPECTIVE"
    if dt >= H0: return "HOLDOUT"
    return "DEVELOPMENT" if matures(t, dt) <= H0 else "PURGED"

# ---------------- archive
man = list(csv.DictReader(open(P6 + "/raw/MANIFEST.csv")))
by_rk = {m["response_key"]: m for m in man if not m["file"].startswith("lists/")}
lists = {}
for m in man:
    if m["file"].startswith("lists/"):
        body = gzip.open(P6 + "/raw/" + m["file"]).read()
        assert hashlib.sha256(body).hexdigest() == m["body_sha256"], m["file"]
        d = json.loads(body)
        lists[m["mint"]] = [it["attributes"]["address"] for it in d.get("data") or []] if m["http_status"] == "200" else None
read_map = json.load(open(P6 + "/data/read_map.json"))
dropped_invalid = Counter()

def load_read(rk, mint, pool):
    m = by_rk[rk]
    body = gzip.open(P6 + "/raw/" + m["file"]).read()
    assert hashlib.sha256(body).hexdigest() == m["body_sha256"]
    url = m["request_url"]
    q = parse_qs(urlsplit(url).query)
    r = dict(rk=rk, pool=m["pool"], mint=m["mint"], boundary=utc(m["boundary_at"]), retrieved=float(m["retrieved_t"]),
             http=int(m["http_status"]), url=url, ok=False, candles=[], cover_from=None, raw_rows=0)
    assert m["mint"] == mint, ("read for another mint", rk)
    assert pool is None or m["pool"] == pool, ("read for another pool", rk, pool, m["pool"])
    if r["http"] != 200: return r
    if q.get("aggregate") != ["5"] or not urlsplit(url).path.endswith("/ohlcv/minute"): return r
    d = json.loads(body)
    meta = d.get("meta") or {}
    addrs = ((meta.get("base") or {}).get("address"), (meta.get("quote") or {}).get("address"))
    if mint not in addrs or q.get("token") != [mint]:
        r["ident"] = "BAD"; return r
    r["quote_side"] = addrs[1] == mint
    rows = d["data"]["attributes"]["ohlcv_list"]
    r["raw_rows"] = len(rows)
    kept = {}
    for row in rows:
        s = float(row[0]); o, h, l, c, v = (float(x) for x in row[1:6])
        if s + PER > r["boundary"]:
            dropped_invalid["after_boundary"] += 1; continue
        if s in kept: continue
        if not (o > 0 and h > 0 and l > 0 and c > 0 and v >= 0) or h < max(o, c) or l > min(o, c) or s + PER > r["retrieved"]:
            dropped_invalid["invalid"] += 1; r.setdefault("invalid_starts", []).append(s); continue
        kept[s] = (s, o, h, l, c, v)
    r["candles"] = [kept[k] for k in sorted(kept)]
    r["cover_from"] = r["candles"][0][0] if r["candles"] else None
    r["ok"] = True
    return r

# ---------------- decisions (copy of the dev store; decision rows only)
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
decs = []
for row in con.execute("SELECT decision_key, chain, mint, pool_address, decision_time, row_json, flags_json FROM predictive_decisions"):
    rj = json.loads(row["row_json"]); sj = rj.get("snapshot_json")
    snap = sj if isinstance(sj, dict) else json.loads(sj or "{}")
    pool, route = row["pool_address"], "PIT_RECORDED"
    if not pool:
        route = "CURRENT_VENDOR_LIST"
        vl = lists.get(row["mint"])
        pool = vl[0] if vl else None
    decs.append(dict(key=row["decision_key"], chain=row["chain"], mint=row["mint"], pool=pool, route=route,
                     dt=float(row["decision_time"]), price=snap.get("price"), vol=snap.get("vol_24h"),
                     kc="KEY_CONFLICT" in json.loads(row["flags_json"] or "[]")))
con.close()

def ref_candle(cs, dt):
    best = None
    for c in cs:
        end = c[0] + PER
        if end + LAG_PROV <= dt and end >= dt - REF_MAX_AGE and (best is None or c[0] > best[0]):
            best = c
    return best

def elig(d, r):
    if not d["pool"] or r is None or not r["ok"]: return "VENDOR_OR_ROUTE_GAP"
    if ref_candle(r["candles"], d["dt"]) is not None: return "ELIGIBLE"
    v = d["vol"]
    if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and 0 <= v < VOL_INACTIVE: return "MARKET_INACTIVE"
    if d["route"] == "PIT_RECORDED" and any(c[0] + PER >= d["dt"] - QUIET_LOOKBACK and c[0] + PER + LAG_PROV <= d["dt"] for c in r["candles"]):
        return "MARKET_INACTIVE"
    return "VENDOR_OR_ROUTE_GAP"

def grid_up(t): return math.ceil(t / PER) * PER

def seen(r, s, e):  # CC-03 absence evidence
    return r["ok"] and r["boundary"] >= grid_up(e) and r["cover_from"] is not None and r["cover_from"] < s

def classify(t, d, r):
    dt = d["dt"]; te = dt + LAG_EXEC; H = TG[t]["h"]
    ref = ref_candle(r["candles"], dt); p0 = ref[1] if MUT=="p0open" else ref[4]
    assert r["boundary"] >= grid_up(te + H + TG[t]["c"]), "boundary short"
    path = sorted(c for c in r["candles"] if c[0] >= te and c[0] + PER <= te + H)
    inval_in_path = [s for s in r.get("invalid_starts", []) if s >= te and s + PER <= te + H]
    base = dict(p0=p0, p0_start=ref[0], n_path=len(path), invalid_in_path=len(inval_in_path))
    if t in ("T1", "T1b"):
        U, L = 1.25 * p0, 0.85 * p0
        for c in path:
            up, lo = c[2] >= U, c[3] <= L
            if up or lo:
                return dict(base, state="LABELED", cls="AMBIGUOUS_BAR" if up and lo else "TARGET_FIRST" if up else "INVALIDATION_FIRST",
                            first=c[0], touch_vol=c[5])
        if not seen(r, te, te + H): return dict(base, state="UNVERIFIABLE_NO_VENDOR_HISTORY", cls=None)
        return dict(base, state="LABELED", cls="NEITHER" if path else "NO_TRADES_AFTER_ENTRY", first=None)
    for c in path:
        if (c[3] < 0.5 * p0) if MUT=="ddstrict" else (c[3] <= 0.5 * p0):
            return dict(base, state="LABELED", cls="DRAWDOWN_50", first=c[0], touch_vol=c[5])
    if not seen(r, te, te + H): return dict(base, state="UNVERIFIABLE_NO_VENDOR_HISTORY", cls=None)
    s, e = (te + 86400 if MUT=="halt24" else te + 64800), te + 172800
    if any((c[0] >= s and c[0] + PER <= e) if MUT=="contain" else (c[0] < e and c[0] + PER > s) for c in r["candles"]): return dict(base, state="LABELED", cls="NO_SEVERE_EVENT", first=None)
    if not seen(r, s, e): return dict(base, state="UNVERIFIABLE_NO_VENDOR_HISTORY", cls=None)
    return dict(base, state="NEEDS_OTHER_POOLS", cls=None)

# eligibility for non-holdout Solana decisions only (holdout reads are never opened here)
reads, E = {}, {}
for d in decs:
    k = d["key"]
    if d["chain"] != "solana": E[k] = "OUT_OF_SCOPE_CHAIN"; continue
    if not (isinstance(d["price"], (int, float)) and d["price"] > 0): E[k] = "NO_SNAPSHOT_PRICE"; continue
    if d["dt"] >= H0:
        E[k] = "HOLDOUT_NOT_OPENED" if d["dt"] < P0T else "PROSPECTIVE"; continue
    if k not in read_map:
        E[k] = "VENDOR_OR_ROUTE_GAP" if not d["pool"] else "NOT_READ"; continue
    r = load_read(read_map[k], d["mint"], d["pool"])
    reads[k] = r
    E[k] = elig(d, r)

out = {"targets": {}, "eligibility": dict(Counter(E.values())), "dropped": dict(dropped_invalid), "records": {}}
for t in TG:
    H = TG[t]["h"]
    # thinning: eligible only (holdout eligibility is unknown here; holdout decisions are later than every development one
    # per mint, so they cannot thin a development decision)
    last, kept = {}, set()
    for d in sorted((d for d in decs if (E[d["key"]] in ("ELIGIBLE","MARKET_INACTIVE","VENDOR_OR_ROUTE_GAP") if MUT=="thinfirst" else E[d["key"]] == "ELIGIBLE")), key=lambda d: (d["mint"], d["dt"])):
        if d["mint"] not in last or d["dt"] >= last[d["mint"]] + H:
            kept.add(d["key"]); last[d["mint"]] = d["dt"]
    states, classes, recs = Counter(), Counter(), {}
    for d in decs:
        k = d["key"]; sp = split(t, d["dt"])
        if sp in ("HOLDOUT", "PROSPECTIVE"): continue
        e = E[k]
        if e != "ELIGIBLE": st = e; res = {}
        elif k not in kept: st = "THINNED"; res = {}
        elif sp == "PURGED": st = "PURGED"; res = {}
        elif reads[k]["retrieved"] < matures(t, d["dt"]): st = "PENDING"; res = {}
        else:
            res = classify(t, d, reads[k]); st = res["state"]
        states[(sp, st)] += 1
        if st == "LABELED": classes[res["cls"]] += 1
        recs[k] = dict(state=st, split=sp, **{x: res.get(x) for x in ("cls", "p0", "p0_start", "first", "n_path", "invalid_in_path")},
                       route=d["route"], quote_side=reads.get(k, {}).get("quote_side"))
    out["targets"][t] = {"states": {f"{a}/{b}": n for (a, b), n in sorted(states.items())}, "classes": dict(classes),
                         "labelled": sum(classes.values()),
                         "positive": classes["TARGET_FIRST"] if t != "T2" else classes["DRAWDOWN_50"] + classes["TRADING_HALT"]}
    out["records"][t] = recs
json.dump(out, open(OUT, "w"), indent=1, default=str)
print(json.dumps({t: {k: v for k, v in out["targets"][t].items()} for t in TG}, indent=1))
print(json.dumps({"eligibility": out["eligibility"], "dropped": out["dropped"]}))
