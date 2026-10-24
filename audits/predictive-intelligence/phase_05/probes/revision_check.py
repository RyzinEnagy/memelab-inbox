"""Phase 05 vendor revision check (P07) on real data. Three comparisons, each counting identical, changed, newly appearing and
vanished candles inside the window both reads covered:

  p04      Phase 04's raw bodies (read 2026-10-24 from 08:02Z, kept outside the repository) against the Phase 05 store's first
           read of the same pools (offline, no call). Phase 04 requested no token parameter, so only pools whose body names the
           mint as base token are compared; the others are counted (they price another token).
  inbox15  GeckoTerminal 15-minute candles captured by the lab's collector on 2026-10-06/07 (tracked inbox/ files, a projection
           of the vendor body; the collector's request carried token=<mint>) against one re-read now of each development pool
           that has such a series (network: 9 calls through runtime.CallGuard). Both reads go through store.ingest_gt_response
           into a separate comparison store, so the store's own revision rules classify every difference.
  store    the main store's re-read series (build_store.py reread): revisions, appearances and vanished candles it recorded.

    python -B revision_check.py p04
    python -B revision_check.py inbox15
    python -B revision_check.py inbox15cmp   # offline: only inbox reads whose request URL is recorded
    python -B revision_check.py store
Writes evidence/revision_check_<name>.json.
"""
from __future__ import annotations

import collections
import datetime as dt
import glob
import gzip
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHASE = HERE.parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
from memelab.predictive import runtime as R  # noqa: E402
from memelab.predictive import sources as SRC  # noqa: E402
from memelab.predictive import store as S  # noqa: E402

STORE = Path("/home/claude/pi_research/p05/predictive_store.sqlite")
P04_RAW = Path("/home/claude/pi_research/p04_gt_raw")
P04_CALLS = REPO / "audits/predictive-intelligence/phase_04/adoption/data/dev_sample_calls.json"
CMP_STORE = Path("/home/claude/pi_research/p05/revision_inbox15.sqlite")
PLAN = PHASE / "data" / "backfill_plan.json"
OUT = PHASE / "evidence"


def ts(s: str) -> float:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def compare(a: dict, b: dict, lo: float, hi: float) -> dict:
    """a, b: start -> [o, h, l, c, v]; compare positions with start in [lo, hi]."""
    ka = {k for k in a if lo <= k <= hi}
    kb = {k for k in b if lo <= k <= hi}
    same = sum(1 for k in ka & kb if a[k] == b[k])
    changed = [k for k in ka & kb if a[k] != b[k]]
    rel = [max(abs(x - y) / max(abs(x), 1e-30) for x, y in zip(a[k], b[k])) for k in changed]
    fields = collections.Counter("".join(n for n, x, y in zip("ohlcv", a[k], b[k]) if x != y) for k in changed)
    return {"both": len(ka & kb), "identical": same, "changed": len(changed), "only_first": len(ka - kb),
            "only_second": len(kb - ka), "max_rel_diff": max(rel) if rel else 0.0, "changed_fields": dict(fields)}


def cmd_p04():
    calls = json.loads(P04_CALLS.read_text())
    con = S.connect(STORE)
    first = collections.defaultdict(dict)
    for r in S.iter_rows(con, "SELECT pool_address, start_at, o, h, l, c, v, revision_of, vanished FROM predictive_candles "
                              "WHERE period_s=300 AND revision_of IS NULL AND vanished=0 AND available_basis <> 'REVISION_FIRST_READ'"):
        first[r["pool_address"]][r["start_at"]] = [r["o"], r["h"], r["l"], r["c"], r["v"]]
    mint_of = {p["pool"]: p["mint"] for p in json.loads(PLAN.read_text())["plan"]}
    p05_first_read = {}
    for r in S.iter_rows(con, "SELECT pool_address, MIN(retrieved_at) t FROM predictive_raw_responses WHERE source_id="
                              "'geckoterminal-ohlcv' GROUP BY pool_address"):
        p05_first_read[r["pool_address"]] = r["t"]
    tot = collections.Counter()
    per_pool, skipped = [], collections.Counter()
    by_pool = collections.defaultdict(dict)
    p04_times = collections.defaultdict(list)
    for c in calls:
        if c["http"] != 200:
            continue
        pool = c["url"].split("/pools/")[1].split("/")[0]
        body = (P04_RAW / c["file"]).read_bytes()
        mint = mint_of.get(pool)
        if mint is None:
            skipped["pool_not_in_phase05_plan"] += 1
            continue
        ident = S.gt_identity(body, mint, None)
        if ident != "OK_BASE":
            skipped["p04_body_prices_another_token:" + ident] += 1
            continue
        for row in S.parse_gt_ohlcv(body):
            by_pool[pool][float(row[0])] = [float(x) for x in row[1:6]]
        p04_times[pool].append(c["retrieved_t"])
    for pool, a in sorted(by_pool.items()):
        b = first.get(pool, {})
        if not b:
            skipped["no_phase05_candles"] += 1
            continue
        lo, hi = max(min(a), min(b)), min(max(a), max(b))
        r = compare(a, b, lo, hi)
        r.update(pool=pool, gap_s=round(p05_first_read.get(pool, 0) - max(p04_times[pool]), 1))
        per_pool.append(r)
        for k in ("both", "identical", "changed", "only_first", "only_second"):
            tot[k] += r[k]
        for f, n in r["changed_fields"].items():
            tot["changed_fields:" + f] += n
    out = {"comparison": "Phase 04 bodies (first) against the Phase 05 store's first read (second), 5-minute candles",
           "pools_compared": len(per_pool), "totals": dict(tot), "skipped": dict(skipped),
           "gap_s_min_max": [min(p["gap_s"] for p in per_pool), max(p["gap_s"] for p in per_pool)] if per_pool else None,
           "max_rel_diff": max((p["max_rel_diff"] for p in per_pool), default=0.0), "per_pool": per_pool,
           "note": "only_first / only_second count positions inside the overlap that one read had and the other did not"}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "revision_check_p04.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "per_pool"}))


def _inbox_reads(dev: dict) -> list[dict]:
    out = []
    for f in sorted(glob.glob(str(REPO / "inbox" / "*.json"))):
        rel = str(Path(f).relative_to(REPO))
        d = json.loads(Path(f).read_text())
        for k, v in d.items():
            if not (k.startswith("gt_ohlcv:") and k.endswith(":minute15")):
                continue
            pool = k.split(":")[1]
            if pool not in dev or not isinstance(v, dict) or v.get("s") != 200:
                continue
            rows = (v.get("body") or {}).get("ohlcv") or []
            blob = subprocess.run(["git", "-C", str(REPO), "rev-parse", f"HEAD:{rel}"], capture_output=True, text=True).stdout.strip()
            commit_t = int(subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%ct", "--diff-filter=A", "--", rel],
                                          capture_output=True, text=True).stdout.strip() or 0)
            out.append({"file": rel, "blob": blob, "key": k, "pool": pool, "mint": dev[pool], "at": ts(d["_at"]),
                        "first_commit_t": commit_t, "rows": rows})
    return sorted(out, key=lambda r: (r["pool"], r["at"]))


def cmd_inbox15():
    dev = {p["pool"]: p["mint"] for p in json.loads(PLAN.read_text())["plan"]}
    reads = _inbox_reads(dev)
    if CMP_STORE.exists():
        CMP_STORE.unlink()
    con = S.connect(CMP_STORE)
    log, per_pool = [], []
    guard = R.CallGuard(max_per_min=5.7)
    for pool in sorted({r["pool"] for r in reads}):
        mint = dev[pool]
        mine = [r for r in reads if r["pool"] == pool]
        summaries = []
        for r in mine:                                    # earlier reads: the collector's projection, meta reconstructed
            body = json.dumps({"data": {"attributes": {"ohlcv_list": r["rows"]}},
                               "meta": {"base": {"address": mint}, "reconstructed": "inbox projection; request carried token=<mint>"}},
                              sort_keys=True).encode()
            resp = {"url": f"inbox:{r['file']}#{r['key']}", "params": {"source": "inbox", "file": r["file"], "blob": r["blob"],
                                                                         "token": mint, "first_commit_t": r["first_commit_t"]},
                    "retrieved_at": r["at"], "http_status": 200, "body": body, "boundary_at": r["at"], "timeframe": "minute",
                    "aggregate": 15, "collector": "memelab bridge collector (inbox/)"}
            s = S.ingest_gt_response(con, resp, chain="solana", mint=mint, pool=pool, now=time.time(), limit=len(r["rows"]) or 1)
            summaries.append({"read": r["file"], "at": r["at"], "kept": s.get("kept"), "added": s.get("added"),
                              "revisions": s.get("revisions"), "vanished": s.get("vanished"), "reads": s.get("reads"),
                              "dropped_after_boundary": s.get("dropped")})
        before = int(max(r["at"] for r in mine))
        url = SRC.gt_url(pool, before, token=mint, timeframe="minute", aggregate=15)
        last = {}

        def call(u):
            code, body = SRC.curl_get(u)
            last["r"] = (code, body)
            if code != 200:
                raise SRC.HTTPStatusError(f"HTTP {code}")
            return code, body
        for attempt in range(4):
            st, val = guard.call("geckoterminal", call, url)
            code, body = last.get("r", (0, b""))
            arrived = time.time()
            log.append({"url": url, "retrieved_at": dt.datetime.fromtimestamp(arrived, dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "http": code, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
            if code == 429:
                time.sleep(60)
                continue
            break
        if code == 200:
            resp = {"url": url, "params": {"pool": pool, "before_timestamp": before, "token": mint, "timeframe": "minute",
                                           "aggregate": 15, "limit": 1000}, "retrieved_at": arrived, "http_status": 200,
                    "body": body, "boundary_at": before, "timeframe": "minute", "aggregate": 15}
            s = S.ingest_gt_response(con, resp, chain="solana", mint=mint, pool=pool, now=time.time())
            summaries.append({"read": "geckoterminal re-read", "at": arrived, "identity_check": s.get("identity_check"),
                              "kept": s.get("kept"), "added": s.get("added"), "revisions": s.get("revisions"),
                              "vanished": s.get("vanished"), "reads": s.get("reads"), "dropped_after_boundary": s.get("dropped")})
        con.commit()
        per_pool.append({"pool": pool, "inbox_reads": len(mine), "gap_days": round((arrived - max(r["at"] for r in mine)) / 86400, 2),
                         "reads": summaries})
    con.commit()
    rv = S.iter_rows(con, "SELECT c.pool_address, c.start_at, c.o, c.h, c.l, c.c, c.v, c.vanished, p.o po, p.h ph, p.l pl, p.c pc, "
                          "p.v pv FROM predictive_candles c LEFT JOIN predictive_candles p ON p.obs_key = c.revision_of "
                          "WHERE c.available_basis = 'REVISION_FIRST_READ'")
    changed = [r for r in rv if r["po"] is not None and not r["vanished"]]
    rel = [max(abs(a - b) / max(abs(a), 1e-30) for a, b in ((r["po"], r["o"]), (r["ph"], r["h"]), (r["pl"], r["l"]),
                                                           (r["pc"], r["c"]), (r["pv"], r["v"]))) for r in changed]
    vol_only = sum(1 for r in changed if (r["po"], r["ph"], r["pl"], r["pc"]) == (r["o"], r["h"], r["l"], r["c"]))
    out = {"comparison": "inbox 15-minute candles (2026-10-06/07, collector projection) against one GeckoTerminal re-read now; "
                         "classified by store.ingest_gt_response in a separate comparison store",
           "pools": len(per_pool), "inbox_reads": len(reads), "calls": log,
           "store_counts": S.table_counts(con),
           "revision_rows": len(rv), "changed_values": len(changed), "appeared_after_covering_read":
               sum(1 for r in rv if r["po"] is None and not r["vanished"]), "vanished": sum(1 for r in rv if r["vanished"]),
           "changed_volume_only": vol_only, "max_rel_diff_changed": max(rel) if rel else 0.0,
           "per_pool": per_pool}
    (OUT / "revision_check_inbox15.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k not in ("per_pool", "calls")}))


CMP2 = Path("/home/claude/pi_research/p05/revision_inbox15_v2.sqlite")


def _plan_url(inbox_file: str, key: str) -> str | None:
    """The exact request URL of an inbox read, when its plan file is in the repository (data/inbox/<plan>.plan.json)."""
    d = json.loads((REPO / inbox_file).read_text())
    for cand in (REPO / "data" / "inbox" / f"{d.get('_plan')}.plan.json", REPO / "inbox" / "plans" / f"{d.get('_plan')}.plan.json"):
        if cand.exists():
            for r in json.loads(cand.read_text()).get("reqs") or []:
                if r.get("key") == key:
                    return r.get("url")
    return None


def cmd_inbox15cmp():
    """Offline second pass of inbox15 (no call): the first pass reconstructed the inbox reads' vendor meta as if every read had
    asked for token=<mint>, which is not true for the early collector plans. Here an inbox read is compared only when its exact
    request URL is in the repository; its token parameter comes from that URL and the pool's base and quote come from the
    vendor's own meta in the re-read body (a pool's sides do not change). Reads without a recorded URL are counted as
    UNVERIFIABLE_REQUEST and left out of the revision counts."""
    old = S.connect(CMP_STORE)
    gt = {r["pool_address"]: r for r in S.responses(old, S.SOURCE_GT) if r["request_url"].startswith("https://")}
    dev = {p["pool"]: p["mint"] for p in json.loads(PLAN.read_text())["plan"]}
    reads = _inbox_reads(dev)
    if CMP2.exists():
        CMP2.unlink()
    con = S.connect(CMP2)
    per, skipped = [], collections.Counter()
    for pool in sorted({r["pool"] for r in reads}):
        g = gt.get(pool)
        if g is None:
            skipped["no_reread"] += 1
            continue
        mint = dev[pool]
        gbody = gzip.decompress(g["body_gzip"])
        meta = json.loads(gbody).get("meta") or {}
        used = []
        for r in [x for x in reads if x["pool"] == pool]:
            url = _plan_url(r["file"], r["key"])
            if url is None:
                skipped["UNVERIFIABLE_REQUEST"] += 1
                continue
            tok = url.split("token=")[1].split("&")[0] if "token=" in url else None
            body = json.dumps({"data": {"attributes": {"ohlcv_list": r["rows"]}}, "meta": meta}, sort_keys=True).encode()
            resp = {"url": url, "params": {"source": "inbox", "file": r["file"], "blob": r["blob"], "token": tok},
                    "retrieved_at": r["at"], "http_status": 200, "body": body, "boundary_at": r["at"], "timeframe": "minute",
                    "aggregate": 15}
            o = S.ingest_gt_response(con, resp, chain="solana", mint=mint, pool=pool, now=time.time(), limit=len(r["rows"]) or 1)
            used.append({"read": r["file"], "token_param": tok, "identity_check": o["identity_check"], "kept": o["kept"]})
        if not used:
            continue
        resp = {"url": g["request_url"], "params": json.loads(g["request_json"]), "retrieved_at": g["retrieved_at"], "http_status": 200,
                "body": gbody, "boundary_at": g["boundary_at"], "timeframe": "minute", "aggregate": 15}
        o = S.ingest_gt_response(con, resp, chain="solana", mint=mint, pool=pool, now=time.time())
        used.append({"read": "geckoterminal re-read", "identity_check": o["identity_check"], "kept": o["kept"], "reads": o["reads"],
                     "revisions": o["revisions"], "vanished": o["vanished"]})
        per.append({"pool": pool, "reads": used})
    con.commit()
    kinds = dict(collections.Counter(r["revision_kind"] for r in S.iter_rows(con, "SELECT revision_kind FROM predictive_candles "
                                                                                    "WHERE revision_kind IS NOT NULL")))
    fields = collections.Counter()
    for r in S.iter_rows(con, "SELECT n.*, p.o po, p.h ph, p.l pl, p.c pc, p.v pv FROM predictive_candles n JOIN predictive_candles p "
                              "ON p.obs_key = n.revision_of WHERE n.vanished = 0 AND p.vanished = 0"):
        fields["".join(k for k in "ohlcv" if r["p" + k] != r[k])] += 1
    import statistics
    for pp in per:
        rows = S.iter_rows(con, "SELECT n.revision_kind k, n.c, n.v, p.c pc, p.v pv FROM predictive_candles n JOIN predictive_candles p "
                                "ON p.obs_key = n.revision_of WHERE n.pool_address = ?", (pp["pool"],))
        pp["revision_kinds"] = dict(collections.Counter(r["k"] for r in rows))
        vals = [r for r in rows if r["k"] == "VALUES"]
        if vals:
            pp["values_median_close_ratio"] = statistics.median(r["pc"] / r["c"] for r in vals)
            pp["values_median_volume_ratio"] = statistics.median(r["pv"] / r["v"] for r in vals if r["v"])
    out = {"comparison": "inbox 15-minute reads with a recorded request URL against the GeckoTerminal re-read of the first pass "
                         "(no new call)", "pools": len(per), "skipped": dict(skipped), "store_counts": S.table_counts(con),
           "unchanged_reads": con.execute("SELECT COUNT(*) FROM predictive_candle_reads").fetchone()[0],
           "revision_kinds": kinds, "changed_fields": dict(fields), "per_pool": per}
    (OUT / "revision_check_inbox15_verified.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "per_pool"}))


def cmd_store():
    con = S.connect(STORE)
    rer = S.iter_rows(con, "SELECT * FROM predictive_source_status WHERE series_id LIKE '%#reread%' ORDER BY checked_at")
    keys = [k for r in rer for k in json.loads(r["response_keys_json"])]
    if not keys:
        print(json.dumps({"rereads": 0}))
        return
    q = ",".join("?" * len(keys))
    resp = S.iter_rows(con, f"SELECT * FROM predictive_raw_responses WHERE response_key IN ({q})", keys)
    rv = S.iter_rows(con, f"SELECT c.*, p.o po, p.h ph, p.l pl, p.c pc, p.v pv, p.retrieved_at prt FROM predictive_candles c "
                          f"LEFT JOIN predictive_candles p ON p.obs_key = c.revision_of WHERE c.response_key IN ({q})", keys)
    reads = con.execute(f"SELECT COUNT(*) FROM predictive_candle_reads WHERE response_key IN ({q})", keys).fetchone()[0]
    first = {r["pool_address"]: r["t"] for r in S.iter_rows(con, "SELECT pool_address, MIN(retrieved_at) t FROM "
                                                                  "predictive_raw_responses WHERE source_id='geckoterminal-ohlcv' GROUP BY 1")}
    gaps = [r["retrieved_at"] - first[r["pool_address"]] for r in resp]
    changed = [r for r in rv if r["revision_of"] and not r["vanished"]]
    out = {"comparison": "main store: re-read series against the first read of the same pools",
           "series": len(rer), "series_status": dict(collections.Counter(r["status"] for r in rer)),
           "responses": len(resp), "identity": dict(collections.Counter(r["identity_check"] for r in resp)),
           "unchanged_candle_reads": reads, "changed_values": len(changed),
           "appeared_after_covering_read": sum(1 for r in rv if not r["revision_of"] and r["available_basis"] == "REVISION_FIRST_READ"),
           "new_positions_outside_earlier_coverage": sum(1 for r in rv if r["available_basis"] != "REVISION_FIRST_READ"),
           "vanished": sum(1 for r in rv if r["vanished"]),
           "gap_s_min_max": [round(min(gaps), 1), round(max(gaps), 1)] if gaps else None,
           "changed_examples": [{"pool": r["pool_address"], "start": r["start_at"], "first": [r["po"], r["ph"], r["pl"], r["pc"], r["pv"]],
                                 "later": [r["o"], r["h"], r["l"], r["c"], r["v"]]} for r in changed[:10]]}
    (OUT / "revision_check_store.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "changed_examples"}))


if __name__ == "__main__":
    {"p04": cmd_p04, "inbox15": cmd_inbox15, "inbox15cmp": cmd_inbox15cmp, "store": cmd_store}[sys.argv[1]]()
