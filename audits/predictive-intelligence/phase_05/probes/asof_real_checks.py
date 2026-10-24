"""Phase 05 as-of checks on the real store (read only on the store; traps run on in-memory copies).

  truncation  for every decision record: features from the store truncated at its decision time (memelab.predictive.features
              .truncated_copy) equal the features from the full store; provider mode for every decision, capture mode too
  recompute   every stored snapshot equals its recomputation from the store as it is now (after the re-read series)
  traps       on copies of the store, for a deterministic sample of development decisions that have candle values: a candle
              with an extreme price available 1 s after the decision changes nothing; the same candle available exactly at
              the decision changes the snapshot (the check is sensitive)
  fresh       snapshot sha256 of a sample recomputed in two fresh Python processes equals the stored one

    python -B asof_real_checks.py truncation|recompute|traps|fresh     # writes evidence/asof_real_<name>.json
"""
from __future__ import annotations

import json
import random
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHASE = HERE.parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
from memelab.predictive import features as F  # noqa: E402
from memelab.predictive import sources as SRC  # noqa: E402
from memelab.predictive import store as S  # noqa: E402

STORE = Path("/home/claude/pi_research/p05/predictive_store.sqlite")
OUT = PHASE / "evidence"


def decs(con):
    return [d for d in S.iter_rows(con, "SELECT * FROM predictive_decisions ORDER BY decision_time, id") if d["chain"] in S.KNOWN_CHAINS]


def cmd_truncation():
    con = S.connect(STORE)
    ds = decs(con)
    res = {}
    for mode in F.MODES:
        t0 = time.time()
        r = F.truncation_check(con, [(d["chain"], d["mint"], d["decision_time"]) for d in ds], mode)
        res[mode] = {"checked": r["checked"], "differences": len(r["differences"]), "examples": r["differences"][:5],
                     "seconds": round(time.time() - t0, 1)}
        print(json.dumps({mode: res[mode]}), flush=True)
    (OUT / "asof_real_truncation.json").write_text(json.dumps(res, indent=1) + "\n")


def cmd_recompute():
    con = S.connect(STORE)
    keys = [r[0] for r in con.execute("SELECT snapshot_key FROM predictive_snapshots ORDER BY id")]
    bad = [k for k in keys if not F.recompute_matches(con, k)]
    out = {"snapshots": len(keys), "differ": len(bad), "examples": bad[:5], "verify_problems": S.verify(con),
           "reread_rows": con.execute("SELECT COUNT(*) FROM predictive_source_status WHERE series_id LIKE '%#reread%'").fetchone()[0]}
    (OUT / "asof_real_recompute.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out))


def _plant(c, d, avail, start):
    """Insert, on a copy, one raw read and one candle version of the decision's pool at `start`, with an extreme price, available
    (and read) at `avail`: a later version of an existing position or a new position, exactly as a live read would store it."""
    body = json.dumps({"trap": True}).encode()
    rk = S.sha(["trap", d["mint"], avail, start])
    S._insert(c, "predictive_raw_responses", {
        "response_key": rk, "source_id": S.SOURCE_GT, "request_url": "trap", "request_json": "{}", "chain": "solana",
        "mint": d["mint"], "pool_address": d["pool_address"], "boundary_at": avail, "retrieved_at": avail, "http_status": 200,
        "body_sha256": S.sha(body), "body_bytes": len(body), "body_gzip": None, "cover_from": start, "cover_complete": 0,
        "candles_in_body": 1, "candles_dropped_after_boundary": 0, "candles_refused": 0, "identity_check": "OK_TOKEN_PARAM",
        "collector": "trap", "ingest_version": "trap", "schema_version": S.SCHEMA_VERSION, "recorded_at": avail})
    sk = S._series_key(S.SOURCE_GT, "solana", d["pool_address"], 300, start)
    prev = S._latest_version(c, sk)
    S._insert(c, "predictive_candles", {
        "obs_key": S.sha(["trap", sk, avail]), "series_key": sk, "source_id": S.SOURCE_GT,
        "source_record_id": f"{d['pool_address']}:300:{start}", "chain": "solana", "mint": d["mint"],
        "pool_address": d["pool_address"], "period_s": 300, "start_at": float(start), "end_at": float(start + 300),
        "o": 1e6, "h": 1e6, "l": 1e6, "c": 1e6, "v": 1e9, "vanished": 0, "event_time": float(start), "published_at": None,
        "retrieved_at": avail, "available_at": avail, "available_basis": "CAPTURE" if prev is None else "REVISION_FIRST_READ",
        "revision_of": prev["obs_key"] if prev is not None else None, "response_key": rk, "raw_sha256": S.sha(body),
        "ingest_version": "trap", "schema_version": S.SCHEMA_VERSION, "recorded_at": avail})
    c.commit()


def cmd_traps():
    con = S.connect(STORE)
    rows = S.iter_rows(con, "SELECT s.decision_key, s.chain, s.mint, s.pool_address, s.decision_time FROM predictive_snapshots s "
                            "JOIN predictive_feature_values v USING(snapshot_key) WHERE s.availability_mode='provider' AND "
                            "v.feature_name='cdl_last_close_age_s' AND v.value IS NOT NULL ORDER BY s.decision_time, s.id")
    rnd = random.Random(20261024)
    sample = sorted(rnd.sample(rows, min(40, len(rows))), key=lambda r: r["decision_time"])
    out = []
    for d in sample:
        T = d["decision_time"]
        base = F.features_as_of(con, d["chain"], d["mint"], T, F.FEATURE_VERSION)
        start = int((T - 300) // 300 * 300)              # the newest 5-minute position that ends at or before T
        res = {"mint": d["mint"], "decision_time": T, "trap_start": start}
        for label, avail in (("after_1s", T + 1), ("at_decision", T)):
            c = F.truncated_copy(con, 1e12, "provider")
            _plant(c, d, avail, start)
            snap = F.features_as_of(c, d["chain"], d["mint"], T, F.FEATURE_VERSION)
            changed = [a["feature_name"] for a, b in zip(base["values"], snap["values"]) if a["value"] != b["value"]]
            c.close()
            res[label] = {"changed": snap["snapshot_sha256"] != base["snapshot_sha256"], "features_changed": changed}
        out.append(res)
    summ = {"sample": len(out), "after_1s_changed": sum(r["after_1s"]["changed"] for r in out),
            "at_decision_changed": sum(r["at_decision"]["changed"] for r in out), "results": out}
    (OUT / "asof_real_traps.json").write_text(json.dumps(summ, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summ.items() if k != "results"}))


def cmd_fresh():
    con = S.connect(STORE)
    rows = S.iter_rows(con, "SELECT chain, mint, decision_time, snapshot_sha256 FROM predictive_snapshots WHERE "
                            "availability_mode='provider' ORDER BY id")
    rnd = random.Random(5)
    sample = rnd.sample(rows, min(25, len(rows)))
    code = ("import sys,json; sys.path.insert(0, sys.argv[1]); from memelab.predictive import store as S, features as F; "
            "c=S.connect(sys.argv[2]); rows=json.loads(sys.argv[3]); "
            "print(json.dumps([F.features_as_of(c,r['chain'],r['mint'],r['decision_time'],'1')['snapshot_sha256'] for r in rows]))")
    outs = [json.loads(subprocess.run([sys.executable, "-B", "-c", code, str(REPO), str(STORE), json.dumps(sample)], capture_output=True,
                                      text=True, check=True).stdout) for _ in range(2)]
    stored = [r["snapshot_sha256"] for r in sample]
    out = {"sample": len(sample), "process_1_equal_stored": outs[0] == stored, "process_2_equal_stored": outs[1] == stored}
    (OUT / "asof_real_fresh.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out))


if __name__ == "__main__":
    {"truncation": cmd_truncation, "recompute": cmd_recompute, "traps": cmd_traps, "fresh": cmd_fresh}[sys.argv[1]]()
