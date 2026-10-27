"""Phase 19: the prospective label reads (checklist rules 1 and 6, PI-D-104). Network: GeckoTerminal public API only.

    python -B fetch_labels.py open       # refuses unless the tree is clean and PREREG_MANIFEST.json equals HEAD's and matches its
                                         # files; writes monitoring/OPENING_LOG.json (FIRST_OPENING) before any call
    python -B fetch_labels.py lists      # vendor pool list per window mint without a point-in-time pool (CURRENT_VENDOR_LIST route)
    python -B fetch_labels.py fetch      # one read per decision, boundary = the largest needed boundary of the matured targets
    python -B fetch_labels.py others     # up to 3 other vendor pools for T2 records that need them (an evidenced reference halt)
    python -B fetch_labels.py reread     # same-session re-read of the lowest 10% of read URLs by sha256 (short-gap revision check)
    python -B fetch_labels.py archive    # raw/ gzip bodies and raw/MANIFEST.csv of every Phase 19 response, lists included
    python -B fetch_labels.py reread48   # the frozen 48 h re-read of data/revision_sample.json (PI-D-018, PI-D-106); refuses before
                                         # 48 h after each sample read; changed labels become revision entries citing the new read

Every call goes through runtime.CallGuard at 5.7 a minute (the frozen limit is 6), at most 300 calls for the phase, breaker after 5
consecutive failures, HTTP 429 back-off of 60 s; each call is logged in evidence/label_calls.json with its request window. Every
OHLCV URL carries token=<mint>; candles ending after the boundary are dropped by store.ingest_gt_response (PI-D-034). Labels and
bodies stay in the private store /home/claude/pi_research/p19/dev_store.sqlite until the archive step.
"""
from __future__ import annotations

import base64
import collections
import csv
import gzip
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PH = HERE.parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import monitoring as M  # noqa: E402
from memelab.predictive import runtime as R  # noqa: E402
from memelab.predictive import sources as SRC  # noqa: E402
from memelab.predictive import store as S  # noqa: E402

import run_prospective as RP  # noqa: E402

WORK = RP.WORK
MON = PH / "monitoring"
CALLS = PH / "evidence/label_calls.json"
LISTS, READMAP, OTHERS = WORK / "vendor_lists.json", WORK / "read_map.json", WORK / "other_pool_reads.json"
PLAN = WORK / "read_plan.json"
REREAD = PH / "evidence/revision_reread.json"
REREAD48 = PH / "evidence/revision_reread_48h.json"
SAMPLE = PH / "data/revision_sample.json"
SAMPLE_SHA256 = "11874dd9c4719662e07b8e8eabc5e7209aca6016fd4cec27a748da6212fb61fe"     # PI-D-106 item 2
PER_MIN, MAX_CALLS = 5.7, 300
LIST_URL = "https://api.geckoterminal.com/api/v2/networks/solana/tokens/{mint}/pools?page=1"
COLLECTOR = "phase_19/fetch_labels.py"


def jload(p, default):
    return json.loads(Path(p).read_text()) if Path(p).exists() else default


def jsave(p, o):
    RP.jsave(Path(p), o)


_G = {}


def guard():
    if "g" not in _G:
        used = len(jload(CALLS, []))
        _G["g"] = R.CallGuard(max_per_min=PER_MIN, max_calls=max(0, MAX_CALLS - used))
    return _G["g"]


def require_opening():
    log = jload(MON / "OPENING_LOG.json", {})
    if not log.get("entries"):
        raise SystemExit("no opening logged: run `open` first")


def http(url, *, kind, window=None, tries=4):
    """One paced GET with 429 back-off; every attempt is logged before the next."""
    require_opening()
    log = jload(CALLS, [])
    code, body, req, got = 0, b"", time.time(), time.time()
    for attempt in range(tries):
        last = {}

        def call(u):
            last["sent"] = time.time()
            c, b = SRC.curl_get(u)
            last["r"] = (c, b)
            if c != 200:
                raise SRC.HTTPStatusError(f"HTTP {c}")
            return c, b

        req = time.time()
        st, val = guard().call("geckoterminal", call, url)
        got = time.time()
        if st["state"] in (R.CIRCUIT_OPEN, R.CALL_CAP_REACHED, R.COST_CAP_REACHED):
            raise SystemExit(f"stopping: {st['state']} {st['detail']}")
        code, body = val if st["state"] == R.AVAILABLE else last.get("r", (0, b""))
        req = last.get("sent", req)
        log.append({"n": len(log), "kind": kind, "url": url, "requested_at": RP.iso(req), "sent_t": req, "retrieved_at": RP.iso(got),
                    "retrieved_t": got, "http": code, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                    "window_from": RP.iso(window[0]) if window and window[0] else None,
                    "window_to": RP.iso(window[1]) if window and window[1] else None, "attempt": attempt})
        jsave(CALLS, log)
        if len(log) >= 2:
            recent = [x["sent_t"] for x in log if x["sent_t"] >= req - 60.0]
            if len(recent) > 6:
                raise SystemExit("rate check: more than 6 calls in 60 s")
        if code == 429 and attempt + 1 < tries:
            time.sleep(60)
            continue
        return code, body, req, got
    return code, body, req, got


def con():
    return L.connect(RP.DEV_STORE)


def window_solana(c):
    lists = jload(LISTS, {})
    out = []
    for r in RP.window_rows(c):
        if r["chain"] != "solana":
            continue
        vl = lists.get(r["mint"])
        vp = (vl["pools"] if vl.get("pools") is not None else L.LIST_FAILED) if vl else None
        out.append(L.decision_from_row(r, vendor_pools=vp))
    return out


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


def ingest(c, url, code, body, req, got, *, mint, pool, boundary, window):
    resp = {"url": url, "params": {"pool": pool, "timeframe": "minute", "aggregate": 5, "limit": L.LIMIT, "before_timestamp": int(boundary),
                                   "currency": "usd", "token": mint, "requested_at": req, "window_from": window[0], "window_to": window[1]},
            "retrieved_at": got, "http_status": code, "body": body, "boundary_at": int(boundary), "timeframe": "minute", "aggregate": 5,
            "collector": COLLECTOR}
    r = S.ingest_gt_response(c, resp, chain="solana", mint=mint, pool=pool, now=time.time())
    c.commit()
    return r["response_key"]


# ---------------------------------------------------------------- the opening
def cmd_open():
    if RP.git("status", "--porcelain").strip():
        raise SystemExit("the working tree is not clean: commit the predictions before the opening")
    man_path = MON / "PREREG_MANIFEST.json"
    if RP.git("show", "HEAD:audits/predictive-intelligence/phase_19/monitoring/PREREG_MANIFEST.json") != man_path.read_text():
        raise SystemExit("PREREG_MANIFEST.json differs from HEAD")
    man = json.loads(man_path.read_text())
    for n, h in man["files"].items():
        if RP.fsha(MON / n) != h:
            raise SystemExit(f"{n} differs from the manifest: a prediction changed")
    ver = M.verify(MON / "OUTCOME_LEDGER.jsonl")
    if not ver["ok"]:
        raise SystemExit(f"ledger does not verify: {ver['problems'][:2]}")
    log = jload(MON / "OPENING_LOG.json", {"rule": "checklist rule 1: label reads only after the predictions commit", "entries": []})
    mode = "FIRST_OPENING" if not log["entries"] else "LATER_READ"
    log["entries"].append({"mode": mode, "time_utc": RP.iso(time.time()), "head": RP.git("rev-parse", "HEAD").strip(),
                           "manifest_sha256": RP.fsha(man_path), "ledger_head": ver["head"], "ledger_entries": ver["entries"],
                           "calls_before": len(jload(CALLS, []))})
    jsave(MON / "OPENING_LOG.json", log)
    print(json.dumps(log["entries"][-1]))


# ---------------------------------------------------------------- lists, plan, fetch
def cmd_lists():
    require_opening()
    c = con()
    lists = jload(LISTS, {})
    need = sorted({d["mint"] for d in window_solana(c) if not d.get("pool") and L.snapshot_price(d) is not None})
    for m in need:
        if m in lists:
            continue
        url = LIST_URL.format(mint=m)
        code, body, req, got = http(url, kind="pool_list")
        lists[m] = {"url": url, "http": code, "retrieved_at": got, "sha256": hashlib.sha256(body).hexdigest(),
                    "pools": pools_of_list(body) if code == 200 else None,
                    "body_gz_b64": base64.b64encode(gzip.compress(body, mtime=0)).decode()}
        jsave(LISTS, lists)
        print(json.dumps({"mint": m[:6], "http": code, "pools": len(lists[m]["pools"] or [])}), flush=True)
    print(json.dumps({"mints_needing_a_list": len(need), "lists": len(lists)}))


def requirement(d, fetch_time):
    t = d["decision_time"]
    bs = [L.needed_boundary(tg, t) for tg in L.TARGETS if C.label_matures_at(tg, t) <= fetch_time]
    return (max(bs), t - 86400 - 600) if bs else None


def cmd_fetch():
    require_opening()
    c = con()
    now = time.time() - 120
    plan, counts = [], collections.Counter()
    for d in window_solana(c):
        if L.snapshot_price(d) is None:
            counts["no_snapshot_price"] += 1
            continue
        if not d.get("pool"):
            counts["no_pool"] += 1
            continue
        rq = requirement(d, now)
        if rq is None:
            counts["all_pending"] += 1
            continue
        plan.append({"decision_key": d["decision_key"], "mint": d["mint"], "pool": d["pool"], "route": d["route"],
                     "decision_time": d["decision_time"], "boundary": rq[0], "need_from": rq[1]})
        counts["planned"] += 1
    jsave(PLAN, {"made_at": RP.iso(time.time()), "decisions": plan, "counts": dict(counts)})
    rmap = jload(READMAP, {})
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
            assert "token=" + mint in url
            code, body, req, got = http(url, kind="ohlcv", window=(pend[0]["need_from"], b))
            rk = ingest(c, url, code, body, req, got, mint=mint, pool=pool, boundary=b, window=(pend[0]["need_from"], b))
            rd = L.read_from_store(c, rk)
            if code == 429 or code == 0 or code >= 500:
                transient += 1
                print(json.dumps({"pool": pool[:6], "http": code, "transient": transient}), flush=True)
                if transient >= 3:
                    break
                time.sleep(120)
                continue
            take = [pend[0]]
            if rd.ok:
                take += [p for p in pend[1:] if p["boundary"] <= b and rd.cover_from is not None and rd.cover_from <= p["need_from"]]
            elif rd.http_status in (404,) or (rd.identity and not rd.identity.startswith("OK")):
                take = list(pend)
            for p in take:
                rmap[p["decision_key"]] = rk
            jsave(READMAP, rmap)
            keys = {p["decision_key"] for p in take}
            pend = [p for p in pend if p["decision_key"] not in keys]
            print(json.dumps({"pool": pool[:6], "http": code, "ok": rd.ok, "candles": len(rd.candles), "took": len(take),
                              "left": len(pend), "calls": guard().calls}), flush=True)
    print(json.dumps({"mapped": len(rmap), "planned": len(plan), "counts": dict(counts)}))


def cmd_others():
    require_opening()
    c = con()
    u, _ = RP.universe(time.time())
    recs = M.prospective_records(u)
    need = [r for r in recs if r["target"] == L.T2 and r["state"] == L.NEEDS_OTHER_POOLS]
    done = jload(OTHERS, {})
    lists = jload(LISTS, {})
    n = 0
    for r in need:
        d = r["decision"]
        k = d["decision_key"]
        if k in done:
            continue
        vl = lists.get(d["mint"])
        if vl is None:
            url = LIST_URL.format(mint=d["mint"])
            code, body, req, got = http(url, kind="pool_list")
            vl = {"url": url, "http": code, "retrieved_at": got, "sha256": hashlib.sha256(body).hexdigest(),
                  "pools": pools_of_list(body) if code == 200 else None,
                  "body_gz_b64": base64.b64encode(gzip.compress(body, mtime=0)).decode()}
            lists[d["mint"]] = vl
            jsave(LISTS, lists)
        if vl.get("pools") is None:
            done[k] = L.LIST_FAILED
            jsave(OTHERS, done)
            continue
        pools = [p for p in vl["pools"] if p != d["pool"]][:3]
        b = int(L.needed_boundary(L.T2, d["decision_time"]))
        s, e = L.halt_span(d["decision_time"])
        keys = []
        for p in pools:
            url = SRC.gt_url(p, b, token=d["mint"])
            try:
                code, body, req, got = http(url, kind="ohlcv_other_pool", window=(s, e))
                keys.append(ingest(c, url, code, body, req, got, mint=d["mint"], pool=p, boundary=b, window=(s, e)))
            except S.StoreError as err:
                print(json.dumps({"other_pool_refused": str(err)[:80]}))
                keys.append(None)
        done[k] = keys
        jsave(OTHERS, done)
        n += 1
    print(json.dumps({"needing_other_pools": len(need), "fetched_now": n}))


def cmd_reread():
    require_opening()
    c = con()
    rmap = jload(READMAP, {})
    keys = sorted(set(rmap.values()))
    reads = [L.read_from_store(c, k) for k in keys]
    reads = [r for r in reads if r.ok]
    reads.sort(key=lambda r: hashlib.sha256(r.url.encode()).hexdigest())
    k = -(-len(reads) * 10 // 100)
    res = jload(REREAD, {"rule": "lowest ceil(10%) of the OK label reads by sha256 of the request URL; same-session gap (short)",
                         "reads": []})
    done = {x["first"] for x in res["reads"]}
    for first in reads[:k]:
        if first.response_key in done:
            continue
        code, body, req, got = http(first.url, kind="ohlcv_reread")
        rk = ingest(c, first.url, code, body, req, got, mint=first.mint, pool=first.pool, boundary=first.boundary, window=(None, None))
        second = L.read_from_store(c, rk)
        ch = L.revision_changes(first, second, min_gap_s=0, older_than_s=0)
        res["reads"].append({"first": first.response_key, "second": rk, "pool6": first.pool[:6], "gap_s": round(second.retrieved_at - first.retrieved_at, 1),
                             "compared": ch["compared"], "changed": ch["changed"], "appeared": len(ch["appeared"]),
                             "vanished": len(ch["vanished"])})
        jsave(REREAD, res)
    rs = res["reads"]
    res["summary"] = {"reads": len(rs), "label_reads_ok": len(reads), "gap_s_min": min((x["gap_s"] for x in rs), default=None),
                      "gap_s_max": max((x["gap_s"] for x in rs), default=None), "candles_compared": sum(x["compared"] for x in rs),
                      "candles_changed": sum(len(x["changed"]) for x in rs), "appeared": sum(x["appeared"] for x in rs),
                      "vanished": sum(x["vanished"] for x in rs),
                      "frozen_48h_reread": "owed: not before 48 h after the first reads (PI-D-018)"}
    jsave(REREAD, res)
    print(json.dumps(res["summary"]))


def cmd_reread48():
    """PI-D-106: re-read each frozen sample read at least 48 h after its first retrieval (refuses otherwise, before any call),
    measure revisions with the frozen check (labels.revision_changes defaults: 48 h gap, candles 48 h old), then recompute the
    outcomes of the window with the re-read in place of each sample read and append every changed LABELED outcome as a revision
    citing the new read (monitoring.next_outcomes; both versions kept). Writes evidence/revision_reread_48h.json. If a label
    changed, the scoring is rerun from the frozen code into monitoring/after_reread48/ (evaluate, drift, report)."""
    require_opening()
    if RP.fsha(SAMPLE) != SAMPLE_SHA256:
        raise SystemExit("the frozen sample file differs from its recorded sha256")
    smp = json.loads(SAMPLE.read_text())
    now = time.time()
    early = [s for s in smp["sample"] if now - float(s["first_retrieved_at"]) < smp["min_gap_s"]]
    if early:
        raise SystemExit("too early: " + ", ".join(f"{s['response_key'][:12]} from {s['earliest_48h_reread']}" for s in early))
    c = con()
    res = jload(REREAD48, {"rule": smp["rule"], "sample_sha256": SAMPLE_SHA256, "reads": []})
    done = {x["first"]: x["second"] for x in res["reads"]}
    second_of = {}
    for it in smp["sample"]:
        first = L.read_from_store(c, it["response_key"])
        if first.url != it["url"] or first.body_sha256 != it["body_sha256"]:
            raise SystemExit("a sample read differs from the frozen sample")
        if it["response_key"] in done:
            second_of[it["response_key"]] = done[it["response_key"]]
            continue
        code, body, req, got = http(first.url, kind="ohlcv_reread48")
        rk = ingest(c, first.url, code, body, req, got, mint=first.mint, pool=first.pool, boundary=first.boundary, window=(None, None))
        second = L.read_from_store(c, rk)
        ch = L.revision_changes(first, second)
        res["reads"].append({"first": first.response_key, "second": rk, "http": code, "gap_s": round(second.retrieved_at - first.retrieved_at, 1),
                             "frozen_check": ch["frozen_check"], "compared_older_than_48h": ch["compared"], "changed": ch["changed"],
                             "appeared": len(ch["appeared"]), "vanished": len(ch["vanished"])})
        jsave(REREAD48, res)
        if second.ok:
            second_of[it["response_key"]] = rk
    # outcomes with the re-read in place of each sample read; only pairs whose current LABELED outcome used a sample read
    u, _ = RP.universe(now)
    for k, rd in list(u.read_of.items()):
        if rd.response_key in second_of:
            u.read_of[k] = L.read_from_store(c, second_of[rd.response_key])
    idx = M.load(RP.LEDGER)
    cur = M.current_outcomes(idx)
    recs = [r for r in M.prospective_records(u)
            if (cur.get((r["decision_key"], r["target"])) or {}).get("state") == "LABELED"
            and cur[(r["decision_key"], r["target"])]["response_key"] in second_of]
    revs = M.next_outcomes(idx, recs, recorded_at=now, reason="REREAD_48H")
    led = M.append(RP.LEDGER, revs, expect_sha=M.head_sha(idx.entries)) if revs else {"appended": 0}
    res["labels_checked"] = len(recs)
    res["labels_revised"] = [{"decision_key": r["decision_key"][:16], "target": r["target"], "state": r["state"],
                              "label_class": r["label_class"]} for r in revs]
    res["summary"] = {"reads": len(res["reads"]), "frozen_48h_checks": sum(1 for x in res["reads"] if x["frozen_check"]),
                      "candles_compared": sum(x["compared_older_than_48h"] for x in res["reads"]),
                      "candles_changed": sum(len(x["changed"]) for x in res["reads"]), "labels_checked": len(recs),
                      "labels_revised": len(revs), "ledger": led,
                      "next": ("rerun run_prospective.py evaluate, drift and report into monitoring/after_reread48/ (PI-D-106 item 4)"
                               if revs else "no label changed: the Phase 19 outputs stand; record it and lift the provisional marker")}
    jsave(REREAD48, res)
    print(json.dumps(res["summary"]))


def cmd_archive():
    c = con()
    raw = PH / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    man = []
    for r in S.iter_rows(c, "SELECT * FROM predictive_raw_responses WHERE source_id=? AND collector=? ORDER BY retrieved_at, id",
                         (S.SOURCE_GT, COLLECTOR)):
        body = gzip.decompress(r["body_gzip"])
        name = f"gt_{r['response_key'][:16]}_{r['body_sha256'][:8]}.json.gz"
        blob = gzip.compress(body, compresslevel=9, mtime=0)
        (raw / name).write_bytes(blob)
        man.append({"file": name, "file_sha256": hashlib.sha256(blob).hexdigest(), "body_sha256": r["body_sha256"],
                    "response_key": r["response_key"], "request_url": r["request_url"], "retrieved_at": RP.iso(r["retrieved_at"]),
                    "retrieved_t": r["retrieved_at"], "http_status": r["http_status"], "pool": r["pool_address"], "mint": r["mint"],
                    "boundary_at": RP.iso(r["boundary_at"]), "identity_check": r["identity_check"]})
    for m, vl in sorted(jload(LISTS, {}).items()):
        (raw / "lists").mkdir(exist_ok=True)
        blob = base64.b64decode(vl["body_gz_b64"])
        name = f"pools_{hashlib.sha256(m.encode()).hexdigest()[:16]}_{vl['sha256'][:8]}.json.gz"
        (raw / "lists" / name).write_bytes(blob)
        man.append({"file": "lists/" + name, "file_sha256": hashlib.sha256(blob).hexdigest(), "body_sha256": vl["sha256"],
                    "response_key": None, "request_url": vl["url"], "retrieved_at": RP.iso(vl["retrieved_at"]),
                    "retrieved_t": vl["retrieved_at"], "http_status": vl["http"], "pool": None, "mint": m, "boundary_at": None,
                    "identity_check": None})
    with open(raw / "MANIFEST.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(man[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(man)
    for src, name in ((READMAP, "read_map.json"), (OTHERS, "other_pool_reads.json"), (PLAN, "read_plan.json")):
        if Path(src).exists():
            (PH / "data").mkdir(exist_ok=True)
            (PH / "data" / name).write_text(Path(src).read_text())
    print(json.dumps({"files": len(man), "bytes": sum(p.stat().st_size for p in raw.rglob("*") if p.is_file())}))


if __name__ == "__main__":
    cmd = sys.argv[1]
    fn = globals().get("cmd_" + cmd)
    if fn is None:
        raise SystemExit(f"unknown command {cmd}")
    fn()
