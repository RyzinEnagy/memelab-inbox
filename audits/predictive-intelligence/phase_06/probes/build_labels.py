"""Phase 06: build the real label store from the state exports on main and bounded GeckoTerminal label reads.

Two private stores outside the repository: DEV (development, purged and prospective decisions; reads with boundaries at or before
the holdout start) and SEALED (holdout decisions' reads). Holdout labels are written only to the sealed file; this script prints
counts and censoring for the holdout, never a class count (ACCEPTANCE holdout_seal, CC-03 rule 6).

    python -B build_labels.py exports            # decision records from git at REF into the DEV store
    python -B build_labels.py lists              # vendor pool list per mint that needs one for its route (network)
    python -B build_labels.py plan               # read requirements per decision (data/read_plan.json, sealed/read_plan.json)
    python -B build_labels.py fetch dev|sealed   # paced label reads, shared per pool when a read demonstrably covers (network)
    python -B build_labels.py others dev|sealed  # other vendor pools for evidenced reference-pool halts without drawdown (network)
    python -B build_labels.py labels             # build labels; DEV rows to the store, holdout lines to the sealed file
    python -B build_labels.py reread             # in-session re-read of the pre-registered 10% sample (network)
    python -B build_labels.py reread48           # the 48 h re-read of the same sample; refuses before its earliest time
    python -B build_labels.py archive            # raw bodies gzip and manifests (raw/, sealed/raw/)

Network: GeckoTerminal public API only, through runtime.CallGuard at 5.7 calls a minute (under the frozen 6), at most 1,200 calls
per run, breaker after 5 consecutive failures, HTTP 429 back-off of 60 s. Every call is logged with its request window.
"""
from __future__ import annotations

import collections
import csv
import gzip
import hashlib
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHASE = HERE.parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import runtime as R  # noqa: E402
from memelab.predictive import sources as SRC  # noqa: E402
from memelab.predictive import store as S  # noqa: E402

REF = "efdaee91ebbeabf14268d858fa033d36ebd4ca06"     # origin/main fetched 2026-10-24T12:3xZ (export of 2026-10-24T10:11:50Z)
WORK = Path("/home/claude/pi_research/p06")
DEV_DB, SEALED_DB = WORK / "dev_store.sqlite", WORK / "sealed_store.sqlite"
DATA, SEALED = PHASE / "data", PHASE / "sealed"
EVID = PHASE / "evidence"
CALLS = {"dev": EVID / "label_calls.json", "sealed": SEALED / "label_calls.json"}
LISTS = WORK / "vendor_lists.json"          # bodies archived by `archive`; the per-mint pools are not printed for holdout mints
PLAN = {"dev": DATA / "read_plan.json", "sealed": SEALED / "read_plan.json"}
READMAP = {"dev": DATA / "read_map.json", "sealed": SEALED / "read_map.json"}
OTHERS = {"dev": DATA / "other_pool_reads.json", "sealed": SEALED / "other_pool_reads.json"}
PER_MIN = 5.7
LIST_URL = "https://api.geckoterminal.com/api/v2/networks/solana/tokens/{mint}/pools?page=1"


def iso(t):
    import datetime as dt
    return None if t is None else dt.datetime.fromtimestamp(float(t), dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def db(which="dev"):
    WORK.mkdir(parents=True, exist_ok=True)
    return L.connect(DEV_DB if which == "dev" else SEALED_DB)


def jload(p, default):
    return json.loads(Path(p).read_text()) if Path(p).exists() else default


def jsave(p, o):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(o, indent=1, sort_keys=True) + "\n")


# ---------------------------------------------------------------- calls (shared by every network command)
_GUARD = {}


def guard():
    if "g" not in _GUARD:
        _GUARD["g"] = R.CallGuard(max_per_min=PER_MIN, max_calls=1200)
    return _GUARD["g"]


def http(url, *, which, kind, window=None, tries=4):
    """One paced GET with 429 back-off. Returns (status, body, requested_at, retrieved_at). Every attempt is logged."""
    log = jload(CALLS[which], [])
    for attempt in range(tries):
        last = {}

        def call(u):
            last["sent"] = time.time()             # the actual send time, after the guard's pacing wait
            code, body = SRC.curl_get(u)
            last["r"] = (code, body)
            if code != 200:
                raise SRC.HTTPStatusError(f"HTTP {code}")
            return code, body

        req = time.time()
        st, val = guard().call("geckoterminal", call, url)
        got = time.time()
        if st["state"] in (R.CIRCUIT_OPEN, R.CALL_CAP_REACHED, R.COST_CAP_REACHED):
            raise SystemExit(f"stopping: {st['state']} {st['detail']}")
        code, body = val if st["state"] == R.AVAILABLE else last.get("r", (0, b""))
        req = last.get("sent", req)
        log.append({"n": len(log), "kind": kind, "url": url, "requested_at": iso(req), "sent_t": req, "retrieved_at": iso(got),
                    "retrieved_t": got,
                    "http": code, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                    "window_from": iso(window[0]) if window else None, "window_to": iso(window[1]) if window else None,
                    "attempt": attempt})
        jsave(CALLS[which], log)
        if code == 429 and attempt + 1 < tries:
            time.sleep(60)
            continue
        return code, body, req, got
    return code, body, req, got


# ---------------------------------------------------------------- exports and decisions
def cmd_exports():
    c = db("dev")
    ex = SRC.export_versions(REPO, REF)
    r = S.ingest_exports(c, ex, now=time.time(), ref=REF)
    c.commit()
    print(json.dumps({k: v for k, v in r.items() if k != "refused"} | {"refused": r["refused"], "versions": len(ex),
                                                                       "skipped_versions": ex[-1].get("skipped_versions")}))


def rows(c):
    return S.iter_rows(c, "SELECT * FROM predictive_decisions ORDER BY mint, decision_time, id")


def vendor_lists():
    return jload(LISTS, {})


def pools_of_list(body):
    try:
        d = json.loads(body)
    except ValueError:
        return None
    out = []
    for it in d.get("data") or []:
        a = (it.get("attributes") or {}).get("address")
        if isinstance(a, str):
            try:
                out.append(S.check_address("solana", a, "pool"))
            except S.StoreError:
                continue
    return out


def decisions(c):
    lists = vendor_lists()
    out = []
    for r in rows(c):
        vl = lists.get(r["mint"])
        vp = (vl["pools"] if vl and vl.get("pools") is not None else L.LIST_FAILED) if vl else None
        out.append(L.decision_from_row(r, vendor_pools=vp))
    return out


def archive_of(d):
    return "dev" if d["decision_time"] < L.holdout_start() else ("sealed" if d["decision_time"] < L.prospective_start() else None)


def cmd_lists():
    """Vendor pool list for every Solana mint with a priced, non-prospective decision that has no point-in-time pool."""
    c = db("dev")
    lists = vendor_lists()
    need = sorted({r["mint"] for r in rows(c) if r["chain"] == "solana" and not r["pool_address"]
                   and L.snapshot_price(L.decision_from_row(r)) is not None and float(r["decision_time"]) < L.prospective_start()})
    for m in need:
        if m in lists:
            continue
        which = "dev" if any(archive_of(d) == "dev" for d in [L.decision_from_row(r) for r in rows(c) if r["mint"] == m]) else "sealed"
        code, body, req, got = http(LIST_URL.format(mint=m), which=which, kind="pool_list")
        lists[m] = {"url": LIST_URL.format(mint=m), "http": code, "retrieved_at": got, "sha256": hashlib.sha256(body).hexdigest(),
                    "pools": pools_of_list(body) if code == 200 else None, "archive": which,
                    "body_gz_b64": __import__("base64").b64encode(gzip.compress(body, mtime=0)).decode()}
        jsave(LISTS, lists)
        print(json.dumps({"mint": m[:8], "http": code, "pools": len(lists[m]["pools"] or []), "archive": which}), flush=True)
    print(json.dumps({"mints": len(need), "lists": len(lists)}))


# ---------------------------------------------------------------- plan
def requirement(d, which, fetch_time):
    """Request boundary and coverage start one decision's read needs, or None (no read: prospective or every label pending)."""
    t = d["decision_time"]
    need_from = t - 86400 - 600                # 24 h quiet-route lookback plus the reference hour's margin
    if which == "dev":
        bs = [L.needed_boundary(tg, t) for tg in L.TARGETS if L.split_of(tg, t) == "DEVELOPMENT"]
        b = max(bs) if bs else L.ceil_grid(t)     # purged everywhere: eligibility only (thinning of later decisions needs it)
        if b > L.holdout_start():
            raise SystemExit(f"plan error: development read boundary {iso(b)} after the holdout start")
        return b, need_from
    bs = [L.needed_boundary(tg, t) for tg in L.TARGETS if C.label_matures_at(tg, t) <= fetch_time]
    return (max(bs), need_from) if bs else None


def cmd_plan():
    c = db("dev")
    now = time.time()
    plan = {"dev": [], "sealed": []}
    counts = collections.Counter()
    for d in decisions(c):
        if d["chain"] != "solana":
            counts["out_of_scope_chain"] += 1
            continue
        if L.snapshot_price(d) is None:
            counts["no_snapshot_price"] += 1
            continue
        w = archive_of(d)
        if w is None:
            counts["prospective"] += 1
            continue
        if not d["pool"]:
            counts[f"{w}_no_pool"] += 1
            continue
        rq = requirement(d, w, now - 120)
        if rq is None:
            counts[f"{w}_all_pending"] += 1
            continue
        plan[w].append({"decision_key": d["decision_key"], "mint": d["mint"], "pool": d["pool"], "route": d["route"],
                        "decision_time": d["decision_time"], "boundary": rq[0], "need_from": rq[1]})
        counts[f"{w}_planned"] += 1
    for w in ("dev", "sealed"):
        jsave(PLAN[w], {"ref": REF, "made_at": iso(now), "holdout_start": iso(L.holdout_start()), "decisions": plan[w],
                        "pools": len({p["pool"] for p in plan[w]}),
                        "max_boundary": iso(max((p["boundary"] for p in plan[w]), default=None))})
    print(json.dumps(dict(sorted(counts.items())) | {"dev_pools": len({p['pool'] for p in plan['dev']}),
                                                     "sealed_pools": len({p['pool'] for p in plan['sealed']})}))


# ---------------------------------------------------------------- fetch
def ingest(c, which, url, code, body, req, got, *, mint, pool, boundary, window):
    resp = {"url": url, "params": {"pool": pool, "timeframe": "minute", "aggregate": 5, "limit": L.LIMIT, "before_timestamp": int(boundary),
                                   "currency": "usd", "token": mint, "requested_at": req, "window_from": window[0], "window_to": window[1]},
            "retrieved_at": got, "http_status": code, "body": body, "boundary_at": int(boundary), "timeframe": "minute", "aggregate": 5,
            "collector": "phase_06/build_labels.py"}
    r = S.ingest_gt_response(c, resp, chain="solana", mint=mint, pool=pool, now=time.time())
    c.commit()
    return r["response_key"]


def cmd_fetch(which):
    c = db(which)
    plan = jload(PLAN[which], None)["decisions"]
    rmap = jload(READMAP[which], {})
    by_pool = collections.defaultdict(list)
    for p in plan:
        if p["decision_key"] not in rmap:
            by_pool[p["pool"]].append(p)
    for pool, ps in sorted(by_pool.items()):
        pend = sorted(ps, key=lambda p: -p["boundary"])
        mint = pend[0]["mint"]
        transient = 0
        while pend:
            b = int(pend[0]["boundary"])
            if b > time.time() - 60:
                raise SystemExit("plan error: boundary in the future")
            url = SRC.gt_url(pool, b, token=mint)
            code, body, req, got = http(url, which=which, kind="ohlcv", window=(pend[0]["need_from"], b))
            rk = ingest(c, which, url, code, body, req, got, mint=mint, pool=pool, boundary=b, window=(pend[0]["need_from"], b))
            rd = L.read_from_store(c, rk)
            if code == 429 or code == 0 or code >= 500:
                # a rate limit or a server or network failure is retried, never a class (TARGET_REGISTRY eligibility row): the
                # decisions stay unmapped and the next run reads them again
                transient += 1
                print(json.dumps({"pool": pool[:8], "http": code, "transient": transient}), flush=True)
                if transient >= 3:
                    break
                time.sleep(120)
                continue
            take = [pend[0]]
            if rd.ok:
                take += [p for p in pend[1:] if p["boundary"] <= b and rd.cover_from is not None and rd.cover_from <= p["need_from"]]
            elif rd.http_status in (404,) or (rd.identity and not rd.identity.startswith("OK")):
                take = list(pend)                    # the pool is not served for this mint: one failed read stands for all
            for p in take:
                rmap[p["decision_key"]] = rk
            jsave(READMAP[which], rmap)
            keys = {p["decision_key"] for p in take}
            pend = [p for p in pend if p["decision_key"] not in keys]
            print(json.dumps({"pool": pool[:8], "http": code, "ok": rd.ok, "candles": len(rd.candles), "took": len(take),
                              "left": len(pend), "calls": guard().calls}), flush=True)
    print(json.dumps({"mapped": len(rmap), "planned": len(plan)}))


def cmd_unmap_transient(which):
    """Remove from the read map every decision whose read was a rate limit or a server or network failure (the first dev run
    mapped decisions to an HTTP 429 that survived its retries); the responses stay in the append-only store and the call log."""
    c = db(which)
    rmap = jload(READMAP[which], {})
    bad = {}
    for k, rk in list(rmap.items()):
        st = c.execute("SELECT http_status FROM predictive_raw_responses WHERE response_key=?", (rk,)).fetchone()[0]
        if st == 429 or st == 0 or st >= 500:
            bad[k] = st
            del rmap[k]
    jsave(READMAP[which], rmap)
    log = jload(EVID / "unmapped_transient.json", [])
    log.append({"at": iso(time.time()), "archive": which, "unmapped": len(bad), "statuses": dict(collections.Counter(bad.values()))})
    jsave(EVID / "unmapped_transient.json", log)
    print(json.dumps(log[-1]))


if __name__ == "__main__":
    cmd = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    fn = globals().get("cmd_" + cmd)
    if fn is None:
        raise SystemExit(f"unknown command {cmd}")
    fn(arg) if arg else fn()
