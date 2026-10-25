"""Print raw candle rows around the decisive points for hand checks (no label code imported)."""
import csv, gzip, json, sys, sqlite3
from datetime import datetime, timezone
P6 = sys.argv[1] + "/audits/predictive-intelligence/phase_06"
man = {m["response_key"]: m for m in csv.DictReader(open(P6 + "/raw/MANIFEST.csv"))}
rm = json.load(open(P6 + "/data/read_map.json"))
con = sqlite3.connect(sys.argv[2])
iso = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%m-%dT%H:%M:%S")
def show(prefix, mode):
    k, mint, pool, dt, rj = con.execute("select decision_key,mint,pool_address,decision_time,row_json from predictive_decisions where decision_key like ?", (prefix + "%",)).fetchone()
    s = json.loads(rj).get("snapshot_json"); s = s if isinstance(s, dict) else json.loads(s or "{}")
    print(f"\n=== {prefix} mint {mint[:10]} pit_pool {pool} dt {iso(dt)} ({dt}) te {iso(dt+300)} snap price {s.get('price')} vol24 {s.get('vol_24h')}")
    if k not in rm: print("  not in read_map"); return
    m = man[rm[k]]
    print(f"  read {m['file']} pool {m['pool']} boundary {m['boundary_at']} retrieved {m['retrieved_at']} http {m['http_status']} url token ok {m['request_url'].endswith('token='+mint)}")
    if m["http_status"] != "200": return
    d = json.loads(gzip.open(P6 + "/raw/" + m["file"]).read())
    rows = sorted(d["data"]["attributes"]["ohlcv_list"])
    print(f"  meta base {d['meta']['base']['address'][:10]} ({d['meta']['base']['symbol']}) quote {d['meta']['quote']['address'][:10]} ({d['meta']['quote']['symbol']}); rows {len(rows)}; earliest {iso(rows[0][0]) if rows else None} latest {iso(rows[-1][0]) if rows else None}")
    te = dt + 300
    near = [r for r in rows if dt - 3900 <= r[0] <= te + 600]
    for r in near: print(f"   {iso(r[0])} end {iso(r[0]+300)} o {r[1]:.6g} h {r[2]:.6g} l {r[3]:.6g} c {r[4]:.6g} v {r[5]:.4g}")
    if mode:
        H = {"T1": 86400, "T1b": 21600, "T2": 86400}[mode]
        path = [r for r in rows if r[0] >= te and r[0] + 300 <= te + H]
        print(f"  path {mode}: {len(path)} rows from {iso(path[0][0]) if path else None} to {iso(path[-1][0]) if path else None}; window end {iso(te+H)}")
        return path
if __name__ == "__main__":
    for a in sys.argv[3:]:
        p, _, m = a.partition(":"); show(p, m or None)
