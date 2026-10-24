"""Phase 06: labels, other pools, revision checks, seal, archive and coverage from the reads build_labels.py made.

    python -B make_labels.py others dev|sealed   # other vendor pools for evidenced reference-pool halts (network)
    python -B make_labels.py labels              # DEV rows into the store, holdout lines into the sealed file, SEAL.json
    python -B make_labels.py compare05           # Phase 05 reads of the same pools against the label reads (no network)
    python -B make_labels.py reread              # in-session re-read of the pre-registered 10% sample (network)
    python -B make_labels.py reread48            # the 48 h re-read of the same sample; refuses before its earliest time
    python -B make_labels.py archive             # raw/ and sealed/raw/ gzip bodies and manifests, then the seal
    python -B make_labels.py coverage            # labels/coverage.json from the DEV store and the seal's counts

The holdout is never summarized beyond counts and censoring: this script prints and writes, for HOLDOUT records, the state
counts per target only (ACCEPTANCE holdout_seal). Development statistics read the DEV store only.
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
sys.path.insert(0, str(HERE))
import build_labels as B  # noqa: E402
from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import sources as SRC  # noqa: E402
from memelab.predictive import store as S  # noqa: E402

LABELS_DIR = B.PHASE / "labels"
SEALED_FILE = B.SEALED / "holdout_labels.jsonl.gz"
SEAL_JSON = B.SEALED / "SEAL.json"
P05_STORE = Path("/home/claude/pi_research/p05/predictive_store.sqlite")
SAMPLE = B.DATA / "revision_sample.json"
REREAD = B.EVID / "revision_reread.json"
REREAD48 = B.EVID / "revision_reread_48h.json"
COMPARE05 = B.EVID / "revision_vs_phase05.json"
COVERAGE = LABELS_DIR / "coverage.json"


def universe(as_of=None):
    cd, cs = B.db("dev"), B.db("sealed")
    decs = B.decisions(cd)
    read_of = {}
    for which, con in (("dev", cd), ("sealed", cs)):
        for k, rk in B.jload(B.READMAP[which], {}).items():
            read_of[k] = L.read_from_store(con, rk)
    others = {}
    for which, con in (("dev", cd), ("sealed", cs)):
        for k, v in B.jload(B.OTHERS[which], {}).items():
            others[k] = L.LIST_FAILED if v == L.LIST_FAILED else [L.read_from_store(con, rk) if rk else None for rk in v]
    return L.Universe(decs, as_of=as_of or time.time(), read_of=read_of, other_reads=others), cd, cs


# ---------------------------------------------------------------- other pools
def cmd_others(which):
    u, cd, cs = universe()
    con = cd if which == "dev" else cs
    want_split = "DEVELOPMENT" if which == "dev" else "HOLDOUT"
    recs, _ = L.build(u)
    need = [r for r in recs if r["target"] == L.T2 and r["state"] == L.NEEDS_OTHER_POOLS and r["split"] == want_split]
    done = B.jload(B.OTHERS[which], {})
    lists = B.vendor_lists()
    n = 0
    for r in need:
        d = r["decision"]
        k = d["decision_key"]
        if k in done:
            continue
        vl = lists.get(d["mint"])
        if vl is None:
            code, body, req, got = B.http(B.LIST_URL.format(mint=d["mint"]), which=which, kind="pool_list")
            vl = {"url": B.LIST_URL.format(mint=d["mint"]), "http": code, "retrieved_at": got, "sha256": hashlib.sha256(body).hexdigest(),
                  "pools": B.pools_of_list(body) if code == 200 else None, "archive": which,
                  "body_gz_b64": __import__("base64").b64encode(gzip.compress(body, mtime=0)).decode()}
            lists[d["mint"]] = vl
            B.jsave(B.LISTS, lists)
        if vl.get("pools") is None:
            done[k] = L.LIST_FAILED
            B.jsave(B.OTHERS[which], done)
            continue
        pools = [p for p in vl["pools"] if p != d["pool"]][:3]
        b = int(L.needed_boundary(L.T2, d["decision_time"]))
        s, e = L.halt_span(d["decision_time"])
        keys = []
        for p in pools:
            url = SRC.gt_url(p, b, token=d["mint"])
            try:
                code, body, req, got = B.http(url, which=which, kind="ohlcv_other_pool", window=(s, e))
                keys.append(B.ingest(con, which, url, code, body, req, got, mint=d["mint"], pool=p, boundary=b, window=(s, e)))
            except S.StoreError as err:            # a pool already owned by another mint in this store: identity conflict
                print(json.dumps({"other_pool_refused": str(err)[:80]}))
                keys.append(None)
        done[k] = keys
        B.jsave(B.OTHERS[which], done)
        n += 1
    summary = {"archive": which, "needing_other_pools": len(need), "fetched_now": n, "calls": B.guard().calls}
    if which == "sealed":                  # a holdout count of candidate halts is not printed (counts and censoring only)
        B.jsave(B.SEALED / "others_summary.json", summary)
        print(json.dumps({"archive": which, "written": "sealed/others_summary.json"}))
    else:
        print(json.dumps(summary))


# ---------------------------------------------------------------- labels and the seal
def _counts(recs, key):
    out = collections.defaultdict(collections.Counter)
    for r in recs:
        out[r["target"]][key(r)] += 1
    return {t: dict(sorted(c.items())) for t, c in sorted(out.items())}


def cmd_labels():
    u, cd, cs = universe()
    recs, elig = L.build(u)
    left = [r for r in recs if r["state"] == L.NEEDS_OTHER_POOLS]
    if left:
        raise SystemExit(f"{len(left)} T2 records still need other pools: run `others` first")
    dev = [r for r in recs if r["split"] != "HOLDOUT"]
    hold = [r for r in recs if r["split"] == "HOLDOUT"]
    res = L.store_labels(cd, dev, export_ref=B.REF, params={"labels_version": L.LABELS_VERSION, "as_of": u.as_of}, now=time.time())
    cd.commit()
    lines = sorted(L.canon(L.sealed_row(r)) for r in hold)
    B.SEALED.mkdir(parents=True, exist_ok=True)
    SEALED_FILE.write_bytes(gzip.compress(("\n".join(lines) + "\n").encode(), compresslevel=9, mtime=0))
    viol_dev = L.cross_target_violations(dev)
    viol_hold = L.cross_target_violations(hold)
    out = {"run_key": res["run_key"], "dev_rows_added": res["added"], "registry_sha": C.registry_sha256(),
           "dev_state_by_split": _counts(dev, lambda r: f"{r['split']}:{r['state']}"),
           "dev_class": _counts([r for r in dev if r["split"] == "DEVELOPMENT" and r["state"] == "LABELED"], lambda r: r["label_class"]),
           "holdout_state": _counts(hold, lambda r: r["state"]),       # counts and censoring only (ACCEPTANCE holdout_seal)
           "holdout_sealed_lines": len(lines), "cross_target_violations": {"development": len(viol_dev), "holdout": len(viol_hold)},
           "eligibility": dict(collections.Counter(elig.values()))}
    B.jsave(B.EVID / "labels_run.json", out)
    print(json.dumps(out, indent=1))


# ---------------------------------------------------------------- revisions
def _dev_label_reads():
    cd = B.db("dev")
    rows = S.iter_rows(cd, "SELECT DISTINCT response_key, request_url FROM predictive_labels WHERE split='DEVELOPMENT' AND state='LABELED'")
    return cd, sorted(rows, key=lambda r: hashlib.sha256(r["request_url"].encode()).hexdigest())


def cmd_sample():
    cd, rs = _dev_label_reads()
    k = math.ceil(len(rs) * C.ACCEPTANCE["api_limits"]["revision_reread_share"])
    pick = rs[:k]
    first = {r["response_key"]: L.read_from_store(cd, r["response_key"]) for r in pick}
    B.jsave(SAMPLE, {"rule": "label reads of LABELED development records, ordered by sha256 of the request URL, lowest ceil(10%)",
                     "label_reads": len(rs), "sample": [{"response_key": r["response_key"], "url": r["request_url"],
                                                         "first_retrieved_at": first[r["response_key"]].retrieved_at,
                                                         "earliest_48h_reread": B.iso(first[r["response_key"]].retrieved_at + 172800)}
                                                        for r in pick]})
    print(json.dumps({"label_reads": len(rs), "sample": k}))


def _reread(out_path, min_gap):
    cd = B.db("dev")
    smp = B.jload(SAMPLE, None)
    if smp is None:
        raise SystemExit("run sample first")
    res = B.jload(out_path, {"reads": []})
    done = {x["first"] for x in res["reads"]}
    now = time.time()
    for it in smp["sample"]:
        if it["response_key"] in done:
            continue
        first = L.read_from_store(cd, it["response_key"])
        if now - first.retrieved_at < min_gap:
            raise SystemExit(f"too early: {it['url'][:60]} can be re-read from {B.iso(first.retrieved_at + min_gap)}")
        code, body, req, got = B.http(first.url, which="dev", kind="ohlcv_reread", window=None)
        rk = B.ingest(cd, "dev", first.url, code, body, req, got, mint=first.mint, pool=first.pool, boundary=first.boundary,
                      window=(None, None))
        second = L.read_from_store(cd, rk)
        ch = L.revision_changes(first, second)
        short = L.revision_changes(first, second, min_gap_s=0, older_than_s=0)
        res["reads"].append({"first": first.response_key, "second": rk, "pool": first.pool, "gap_s": round(second.retrieved_at - first.retrieved_at, 1),
                             "frozen_check": ch["frozen_check"], "compared_older_than_48h": ch["compared"],
                             "changed_older_than_48h": ch["changed"], "appeared": len(ch["appeared"]), "vanished": len(ch["vanished"]),
                             "compared_all": short["compared"], "changed_all": short["changed"]})
        B.jsave(out_path, res)
    # labels that the re-read would change (both versions kept when one changes)
    u, _, _ = universe()
    recs, _ = L.build(u)
    lab = {(r["decision_key"], r["target"]): r for r in recs if r["split"] == "DEVELOPMENT" and r["state"] == "LABELED"}
    stored = {(r["decision_key"], r["target"]): r["label_key"] for r in
              S.iter_rows(cd, "SELECT decision_key, target, label_key FROM predictive_labels WHERE revision_of IS NULL")}
    second_of = {x["first"]: x["second"] for x in res["reads"]}
    revs, checked = [], 0
    for key, r in lab.items():
        rk = r["read"].response_key
        if rk not in second_of:
            continue
        checked += 1
        rv = L.revise(dict(r, label_key=stored.get(key), other_reads_used=u.other_reads.get(r["decision_key"])),
                      L.read_from_store(cd, second_of[rk]), reason="REREAD_" + ("48H" if min_gap else "SAME_DAY"))
        if rv is not None:
            revs.append(rv)
    if revs:
        L.store_labels(cd, revs, export_ref=B.REF, params={"revision": out_path.name}, now=time.time())
        cd.commit()
    res["labels_checked"] = checked
    res["labels_revised"] = [{"decision_key": r["decision_key"][:16], "target": r["target"], "new_class": r["label_class"]} for r in revs]
    res["summary"] = {"reads": len(res["reads"]), "gap_s_min": min(x["gap_s"] for x in res["reads"]),
                      "gap_s_max": max(x["gap_s"] for x in res["reads"]),
                      "frozen_48h_checks": sum(1 for x in res["reads"] if x["frozen_check"]),
                      "candles_compared": sum(x["compared_all"] for x in res["reads"]),
                      "candles_changed": sum(len(x["changed_all"]) for x in res["reads"]),
                      "appeared": sum(x["appeared"] for x in res["reads"]), "vanished": sum(x["vanished"] for x in res["reads"]),
                      "labels_checked": checked, "labels_revised": len(revs)}
    B.jsave(out_path, res)
    print(json.dumps(res["summary"]))


def cmd_reread():
    _reread(REREAD, 0)


def cmd_reread48():
    _reread(REREAD48, C.ACCEPTANCE["api_limits"]["revision_reread_min_gap_s"])


def cmd_compare05():
    """Phase 05's reads of the same pools (read earlier the same day, token=<mint> or the mint as base) against the label reads:
    candle values at shared positions, and each development label recomputed from a Phase 05 read that covers its window."""
    import sqlite3
    p5 = sqlite3.connect(f"file:{P05_STORE}?mode=ro", uri=True)
    p5.row_factory = sqlite3.Row
    u, cd, _ = universe()
    recs, _ = L.build(u)
    p5reads = collections.defaultdict(list)
    for r in p5.execute("SELECT response_key FROM predictive_raw_responses WHERE source_id=? AND http_status=200 AND identity_check LIKE 'OK%'",
                        (S.SOURCE_GT,)):
        rd = L.read_from_store(p5, r["response_key"])
        if rd.ok and S.url_period(rd.url) == 300:
            p5reads[rd.pool].append(rd)
    fields = collections.Counter()
    pos = same = 0
    gaps = []
    seen_pairs = set()
    lab_same = lab_diff = 0
    diffs = []
    for r in recs:
        if r["split"] != "DEVELOPMENT" or r["state"] != "LABELED":
            continue
        rd = r["read"]
        for old in p5reads.get(rd.pool, []):
            pair = (old.response_key, rd.response_key)
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                ch = L.revision_changes(old, rd, min_gap_s=0, older_than_s=0)
                pos += ch["compared"]
                same += ch["unchanged"]
                for x in ch["changed"]:
                    fields[x["fields"]] += 1
                gaps.append(ch["gap_s"])
        d = r["decision"]
        cover = [o for o in p5reads.get(rd.pool, []) if o.boundary >= L.needed_boundary(r["target"], d["decision_time"])
                 and C.reference_candle(list(o.candles), d["decision_time"]) is not None]
        if not cover:
            continue
        alt = L.classify(r["target"], d["decision_time"], cover[0], u.other_reads.get(d["decision_key"]) if r["target"] == L.T2 else None)
        if alt.get("label_class") == r["label_class"] and alt.get("p0") == r["p0"]:
            lab_same += 1
        else:
            lab_diff += 1
            diffs.append({"decision_key": d["decision_key"][:16], "target": r["target"], "label_read_class": r["label_class"],
                          "phase05_read_class": alt.get("label_class") or alt["state"]})
    out = {"comparison": "Phase 05 reads (earlier) against Phase 06 label reads (later) of the same pools, 5-minute, both identity-checked",
           "read_pairs": len(seen_pairs), "gap_s_min": min(gaps) if gaps else None, "gap_s_max": max(gaps) if gaps else None,
           "positions_compared": pos, "unchanged": same, "changed_by_fields": dict(fields),
           "labels_recomputed_from_phase05_read": lab_same + lab_diff, "labels_same": lab_same, "labels_different": lab_diff,
           "differences": diffs}
    B.jsave(COMPARE05, out)
    print(json.dumps({k: v for k, v in out.items() if k != "differences"}))


# ---------------------------------------------------------------- archive and seal
def _archive_store(con, folder, which):
    folder.mkdir(parents=True, exist_ok=True)
    man = []
    for r in S.iter_rows(con, "SELECT * FROM predictive_raw_responses WHERE source_id=? ORDER BY retrieved_at, id", (S.SOURCE_GT,)):
        body = gzip.decompress(r["body_gzip"])
        name = f"gt_{r['response_key'][:16]}_{r['body_sha256'][:8]}.json.gz"
        blob = gzip.compress(body, compresslevel=9, mtime=0)
        (folder / name).write_bytes(blob)
        man.append({"file": name, "file_sha256": hashlib.sha256(blob).hexdigest(), "body_sha256": r["body_sha256"],
                    "response_key": r["response_key"], "request_url": r["request_url"], "retrieved_at": B.iso(r["retrieved_at"]),
                    "retrieved_t": r["retrieved_at"], "http_status": r["http_status"], "pool": r["pool_address"], "mint": r["mint"],
                    "boundary_at": B.iso(r["boundary_at"]), "identity_check": r["identity_check"], "archive": which})
    return man


def _write_manifest(path, man):
    with open(path, "w", newline="") as f:
        if not man:
            return
        w = csv.DictWriter(f, fieldnames=list(man[0]))
        w.writeheader()
        w.writerows(man)


def cmd_archive():
    cd, cs = B.db("dev"), B.db("sealed")
    dev_raw, seal_raw = B.PHASE / "raw", B.SEALED / "raw"
    m1 = _archive_store(cd, dev_raw, "dev")
    m2 = _archive_store(cs, seal_raw, "sealed")
    lists = B.vendor_lists()
    for m, vl in sorted(lists.items()):
        folder = (dev_raw if vl["archive"] == "dev" else seal_raw) / "lists"
        folder.mkdir(parents=True, exist_ok=True)
        blob = __import__("base64").b64decode(vl["body_gz_b64"])
        name = f"pools_{hashlib.sha256(m.encode()).hexdigest()[:16]}_{vl['sha256'][:8]}.json.gz"
        (folder / name).write_bytes(blob)
        (m1 if vl["archive"] == "dev" else m2).append({"file": "lists/" + name, "file_sha256": hashlib.sha256(blob).hexdigest(),
                                                        "body_sha256": vl["sha256"], "response_key": None, "request_url": vl["url"],
                                                        "retrieved_at": B.iso(vl["retrieved_at"]), "retrieved_t": vl["retrieved_at"],
                                                        "http_status": vl["http"], "pool": None, "mint": m, "boundary_at": None,
                                                        "identity_check": None, "archive": vl["archive"]})
    _write_manifest(dev_raw / "MANIFEST.csv", m1)
    _write_manifest(seal_raw / "MANIFEST.csv", m2)
    sealed_files = [SEALED_FILE, seal_raw / "MANIFEST.csv", B.SEALED / "read_map.json", B.SEALED / "read_plan.json",
                    B.SEALED / "label_calls.json"] + sorted(p for p in seal_raw.rglob("*.json.gz"))
    for extra in (B.OTHERS["sealed"], B.SEALED / "others_summary.json"):
        if extra.exists():
            sealed_files.append(extra)
    run = B.jload(B.EVID / "labels_run.json", {})
    seal = {"rule": C.ACCEPTANCE["holdout_seal"], "made_at": B.iso(time.time()), "registry_sha": C.registry_sha256(),
            "labels_version": L.LABELS_VERSION, "export_ref": B.REF, "holdout_window_utc": C.ACCEPTANCE["holdout_window_utc"],
            "holdout_state_counts": run.get("holdout_state"), "sealed_label_lines": run.get("holdout_sealed_lines"),
            "contacted_excluded": C.ACCEPTANCE["holdout_contacted"]["decisions"],
            "files": L.seal_manifest(sealed_files, B.SEALED)}
    seal["seal_sha256"] = L.sha(seal["files"])
    B.jsave(SEAL_JSON, seal)
    size = sum(p.stat().st_size for p in list(dev_raw.rglob("*")) + list(seal_raw.rglob("*")) if p.is_file())
    print(json.dumps({"dev_raw": len(m1), "sealed_raw": len(m2), "bytes": size, "seal_sha256": seal["seal_sha256"],
                      "holdout_labels_sha256": seal["files"]["holdout_labels.jsonl.gz"]["sha256"]}))


# ---------------------------------------------------------------- coverage (development detail, holdout counts only)
def cmd_coverage():
    cd = B.db("dev")
    rows = S.iter_rows(cd, "SELECT * FROM predictive_labels WHERE revision_of IS NULL ORDER BY id")
    seal = B.jload(SEAL_JSON, {})
    for r in rows:
        r["cohort"] = json.loads(r["cohort_json"])
        r["flags"] = json.loads(r["flags_json"])
        r["sens"] = json.loads(r["sensitivity_json"])
    dev = [r for r in rows if r["split"] == "DEVELOPMENT"]
    lab = [r for r in dev if r["state"] == "LABELED"]
    out = {"registry_sha": C.registry_sha256(), "labels_version": L.LABELS_VERSION, "export_ref": B.REF}
    out["state_by_split"] = _counts(rows, lambda r: f"{r['split']}:{r['state']}")
    out["development_class"] = _counts(lab, lambda r: r["label_class"])
    out["development_label"] = _counts(lab, lambda r: r["label"])
    for dim in ("launch_age_bucket", "liquidity_bucket", "day_utc", "week_utc", "status_group", "route"):
        out[f"development_class_by_{dim}"] = _counts(lab, lambda r, dim=dim: f"{r['cohort'][dim]}|{r['label_class']}")
        out[f"development_state_by_{dim}"] = _counts(dev, lambda r, dim=dim: f"{r['cohort'][dim]}|{r['state']}")
    out["development_without_key_conflict"] = _counts([r for r in lab if not r["cohort"]["key_conflict"]], lambda r: r["label_class"])
    out["development_key_conflict_labeled"] = sum(1 for r in lab if r["cohort"]["key_conflict"])
    # censoring and the conservative lens: censored decisions counted T1 negative and T2 positive, thinned with the eligible ones
    lens = {}
    for t in L.TARGETS:
        pool_ = [r for r in dev if r["target"] == t and r["state"] in ("LABELED", "UNVERIFIABLE_NO_VENDOR_HISTORY")]
        gaps = [r for r in rows if r["target"] == t and r["eligibility"] == "VENDOR_OR_ROUTE_GAP" and r["split"] == "DEVELOPMENT"]
        lens[t] = {"labeled": len([r for r in pool_ if r["state"] == "LABELED"]),
                   "positive_labeled": sum(r["label"] for r in pool_ if r["state"] == "LABELED"),
                   "unverifiable": len([r for r in pool_ if r["state"] != "LABELED"]),
                   "vendor_or_route_gap_unthinned": len(gaps),
                   "lens_rule": "censored counted negative" if t != L.T2 else "censored counted positive"}
    out["censoring_lens"] = lens
    out["wick_touch_share"] = {t: {"touches": sum(1 for r in lab if r["target"] == t and r["first_touch_start"] is not None),
                                   "wick": sum(1 for r in lab if r["target"] == t and "WICK_TOUCH" in r["flags"])} for t in L.TARGETS}
    out["sparse_path"] = {t: sum(1 for r in lab if r["target"] == t and "SPARSE_PATH" in r["flags"]) for t in L.TARGETS}
    out["window_edge_candle"] = sum(1 for r in lab if "WINDOW_EDGE_CANDLE" in r["flags"])
    out["ambiguous"] = {t: {"ambiguous": sum(1 for r in lab if r["target"] == t and r["label_class"] == "AMBIGUOUS_BAR"),
                            "labeled": sum(1 for r in lab if r["target"] == t),
                            "positive_if_tie_positive": sum(r["sens"]["label_tie_positive"] or 0 for r in lab if r["target"] == t)}
                        for t in L.TARGETS}
    out["unverifiable_detail"] = _counts([r for r in dev if r["state"] == "UNVERIFIABLE_NO_VENDOR_HISTORY"], lambda r: r["detail"])
    out["halt_flags"] = _counts([r for r in lab if r["target"] == L.T2], lambda r: ",".join(sorted(f for f in r["flags"] if "HALT" in f)) or "none")
    # survivorship: route, read outcome and vendor list by decision (development reads)
    read_stat = collections.Counter()
    for r in rows:
        if r["target"] != L.T1B or r["split"] not in ("DEVELOPMENT", "PURGED") or r["chain"] != "solana":
            continue
        rr = cd.execute("SELECT http_status, identity_check, candles_in_body FROM predictive_raw_responses WHERE response_key=?",
                        (r["response_key"],)).fetchone() if r["response_key"] else None
        st = "NOT_READ" if rr is None else (f"HTTP_{rr['http_status']}" if rr["http_status"] != 200 else
                                            ("EMPTY_PAGE" if not rr["candles_in_body"] else (rr["identity_check"] or "NO_META")))
        read_stat[f"{r['route']}|{st}|{r['eligibility']}"] += 1
    out["survivorship_reads_development_and_purged"] = dict(sorted(read_stat.items()))
    lists = B.vendor_lists()
    out["vendor_lists"] = {"mints": len(lists), "http": dict(collections.Counter(str(v["http"]) for v in lists.values())),
                           "empty": sum(1 for v in lists.values() if v.get("pools") == [])}
    out["holdout"] = {"rule": C.ACCEPTANCE["holdout_seal"], "state_counts": seal.get("holdout_state_counts"),
                      "sealed_label_lines": seal.get("sealed_label_lines"),
                      "holdout_labels_sha256": (seal.get("files") or {}).get("holdout_labels.jsonl.gz", {}).get("sha256")}
    B.jsave(COVERAGE, out)
    print(json.dumps({"development_class": out["development_class"], "censoring_lens": lens}, indent=1))


def cmd_rebuild():
    """Offline rebuild of the development labels from the committed archive only (raw/ bodies, raw/lists/, the read map and the
    exports from git), compared with the development store's rows. No network; the sealed archive is not opened."""
    import base64
    import tempfile
    tmp = Path(tempfile.mkdtemp()) / "rebuild.sqlite"
    con = L.connect(tmp)
    ex = SRC.export_versions(B.REPO, B.REF)
    S.ingest_exports(con, ex, now=time.time(), ref=B.REF)
    man = list(csv.DictReader(open(B.PHASE / "raw" / "MANIFEST.csv")))
    lists = {}
    for m in man:
        blob = (B.PHASE / "raw" / m["file"]).read_bytes()
        assert hashlib.sha256(blob).hexdigest() == m["file_sha256"], m["file"]
        body = gzip.decompress(blob)
        assert hashlib.sha256(body).hexdigest() == m["body_sha256"], m["file"]
        if m["file"].startswith("lists/"):
            lists[m["mint"]] = B.pools_of_list(body) if m["http_status"] == "200" else None
            continue
        from urllib.parse import parse_qs, urlsplit
        b = float(parse_qs(urlsplit(m["request_url"]).query)["before_timestamp"][0])
        resp = {"url": m["request_url"], "params": {"token": S.url_token(m["request_url"])}, "retrieved_at": float(m["retrieved_t"]),
                "http_status": int(m["http_status"]), "body": body, "boundary_at": int(b), "timeframe": "minute", "aggregate": 5}
        r = S.ingest_gt_response(con, resp, chain="solana", mint=m["mint"], pool=m["pool"], now=time.time())
        assert r["response_key"] == m["response_key"], m["file"]
    con.commit()
    decs = []
    for row in B.rows(con):
        vl = lists.get(row["mint"])
        decs.append(L.decision_from_row(row, vendor_pools=vl if row["mint"] in lists else None))
    rmap = B.jload(B.READMAP["dev"], {})
    read_of = {k: L.read_from_store(con, rk) for k, rk in rmap.items()}
    others = {k: (L.LIST_FAILED if v == L.LIST_FAILED else [L.read_from_store(con, rk) if rk else None for rk in v])
              for k, v in B.jload(B.OTHERS["dev"], {}).items()}
    u = L.Universe(decs, as_of=time.time(), read_of=read_of, other_reads=others)
    recs, _ = L.build(u)
    mine = {(r["decision_key"], r["target"]): (r["state"], r["label_class"], r.get("p0")) for r in recs if r["split"] == "DEVELOPMENT"}
    stored = {(r["decision_key"], r["target"]): (r["state"], r["label_class"], r["p0"]) for r in
              S.iter_rows(B.db("dev"), "SELECT * FROM predictive_labels WHERE split='DEVELOPMENT' AND revision_of IS NULL")}
    diff = [k for k in set(mine) | set(stored) if mine.get(k) != stored.get(k)]
    out = {"archive_files": len(man), "development_records": len(mine), "stored_records": len(stored), "differences": len(diff),
           "labeled": sum(1 for v in mine.values() if v[0] == "LABELED")}
    B.jsave(B.EVID / "rebuild_from_archive.json", out)
    print(json.dumps(out))


if __name__ == "__main__":
    cmd = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    fn = globals().get("cmd_" + cmd)
    if fn is None:
        raise SystemExit(f"unknown command {cmd}")
    fn(arg) if arg else fn()
