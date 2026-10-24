"""Phase 05 skeptic trap: a REVISION of the newest candle before each decision (close x1000, volume x1000), inserted as a new
version available 1 s after the decision, then (separately) exactly at the decision. Provider mode. Usage: CLONE STORE_COPY"""
import random, sqlite3, sys
from pathlib import Path
clone = Path(sys.argv[1]); sys.path.insert(0, str(clone))
from memelab.predictive import store as S, features as F
src = sys.argv[2]
base = S.connect(src)
decs = S.iter_rows(base, "SELECT s.* FROM predictive_snapshots s JOIN predictive_feature_values v USING(snapshot_key) WHERE "
                         "s.availability_mode='provider' AND v.feature_name='cdl_last_close_age_s' AND v.value IS NOT NULL")
random.Random(5).shuffle(decs)
res = {"after": 0, "at": 0, "n": 0}
for d in decs[:30]:
    for when, key in ((1.0, "after"), (0.0, "at")):
        c = sqlite3.connect(":memory:"); base.backup(c); c.row_factory = sqlite3.Row
        T = d["decision_time"]
        last = c.execute("SELECT * FROM predictive_candles WHERE chain='solana' AND mint=? AND pool_address=? AND available_at<=? "
                         "AND period_s=300 ORDER BY end_at DESC, available_at DESC LIMIT 1", (d["mint"], d["pool_address"], T)).fetchone()
        row = dict(last); row.pop("id")
        row.update(c=last["c"] * 1000, v=last["v"] * 1000, h=max(last["h"], last["c"] * 1000), available_at=T + when, retrieved_at=T + when,
                   available_basis="REVISION_FIRST_READ", revision_of=last["obs_key"], revision_kind="VALUES",
                   obs_key=S.sha([last["series_key"], "trap", when]))
        cols = list(row); c.execute(f"INSERT INTO predictive_candles ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})", [row[k] for k in cols])
        snap = F.features_as_of(c, "solana", d["mint"], T, "1")
        res[key] += snap["snapshot_sha256"] != d["snapshot_sha256"]
        c.close()
    res["n"] += 1
print(res)
