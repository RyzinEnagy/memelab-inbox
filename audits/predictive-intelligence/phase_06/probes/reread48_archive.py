"""Phase 06, 48 h revision re-read: archive the 16 second reads and check them independently (2026-10-26).

    python -B reread48_archive.py archive   # the second reads named in evidence/revision_reread_48h.json, from the development store
                                            # into raw_reread48/ (gzip, mtime 0) with MANIFEST.csv; no network
    python -B reread48_archive.py check     # standard library only, no lab module: parse both archived bodies of each pair,
                                            # drop candles ending after the request boundary, compare every shared 5-minute
                                            # position field by field; writes evidence/revision_reread_48h_independent.json

The frozen check itself is `make_labels.py reread48` (PI-D-018, PI-D-041 item 5); this script does not change it.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

PHASE = Path(__file__).resolve().parent.parent
RAW = PHASE / "raw"
OUT = PHASE / "raw_reread48"
RES = PHASE / "evidence" / "revision_reread_48h.json"
IND = PHASE / "evidence" / "revision_reread_48h_independent.json"
DEV_DB = Path("/home/claude/pi_research/p06/dev_store.sqlite")
PERIOD = 300
FIELDS = ["file", "file_sha256", "body_sha256", "response_key", "request_url", "retrieved_t", "http_status", "pool", "mint",
          "boundary_t", "identity_check"]


def cmd_archive():
    res = json.loads(RES.read_text())
    con = sqlite3.connect(f"file:{DEV_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    OUT.mkdir(exist_ok=True)
    man = []
    for x in res["reads"]:
        r = con.execute("SELECT * FROM predictive_raw_responses WHERE response_key=?", (x["second"],)).fetchone()
        body = gzip.decompress(r["body_gzip"])
        assert hashlib.sha256(body).hexdigest() == r["body_sha256"]
        name = f"gt_{r['response_key'][:16]}_{r['body_sha256'][:8]}.json.gz"
        blob = gzip.compress(body, compresslevel=9, mtime=0)
        (OUT / name).write_bytes(blob)
        man.append({"file": name, "file_sha256": hashlib.sha256(blob).hexdigest(), "body_sha256": r["body_sha256"],
                    "response_key": r["response_key"], "request_url": r["request_url"], "retrieved_t": r["retrieved_at"],
                    "http_status": r["http_status"], "pool": r["pool_address"], "mint": r["mint"], "boundary_t": r["boundary_at"],
                    "identity_check": r["identity_check"]})
    with open(OUT / "MANIFEST.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(man)
    print(json.dumps({"archived": len(man), "bytes": sum((OUT / m["file"]).stat().st_size for m in man)}))


def _candles(body: bytes, boundary: float) -> dict:
    d = json.loads(body)
    rows = d["data"]["attributes"]["ohlcv_list"]
    return {int(r[0]): tuple(r[1:6]) for r in rows if int(r[0]) + PERIOD <= boundary}


def _load(folder: Path, rk: str, man: dict):
    m = man[rk]
    blob = (folder / m["file"]).read_bytes()
    assert hashlib.sha256(blob).hexdigest() == m["file_sha256"], m["file"]
    body = gzip.decompress(blob)
    assert hashlib.sha256(body).hexdigest() == m["body_sha256"], m["file"]
    b = float(parse_qs(urlsplit(m["request_url"]).query)["before_timestamp"][0])
    meta = json.loads(body).get("meta") or {}
    base = (meta.get("base") or {}).get("address")
    return m, _candles(body, b), base


def cmd_check():
    res = json.loads(RES.read_text())
    first_man = {m["response_key"]: m for m in csv.DictReader(open(RAW / "MANIFEST.csv"))}
    second_man = {m["response_key"]: m for m in csv.DictReader(open(OUT / "MANIFEST.csv"))}
    out, tot = [], {"pairs": 0, "positions_compared": 0, "positions_changed": 0, "close_changed": 0, "volume_changed": 0,
                    "open_high_low_changed": 0, "only_in_one": 0}
    for x in res["reads"]:
        m1, a, base1 = _load(RAW, x["first"], first_man)
        m2, b, base2 = _load(OUT, x["second"], second_man)
        assert m1["request_url"] == m2["request_url"] and m1["pool"] == m2["pool"] and m1["mint"] == m2["mint"]
        assert base1 == base2 == m1["mint"], "the mint must be the base in both reads"
        gap = float(m2["retrieved_t"]) - float(m1["retrieved_t"])
        lo = max(min(a), min(b)) if a and b else None
        shared = [t for t in a if t in b]
        one = [t for t in set(a) ^ set(b) if lo is not None and t >= lo]
        ch = [t for t in shared if a[t] != b[t]]
        cc = sum(1 for t in shared if a[t][3] != b[t][3])
        vc = sum(1 for t in shared if a[t][4] != b[t][4])
        ohl = sum(1 for t in shared if a[t][:3] != b[t][:3])
        out.append({"pool": m1["pool"], "gap_s": round(gap, 1), "gap_at_least_48h": gap >= 172800, "positions_compared": len(shared),
                    "positions_changed": len(ch), "close_changed": cc, "volume_changed": vc, "open_high_low_changed": ohl,
                    "only_in_one_read_in_overlap": len(one)})
        tot["pairs"] += 1
        tot["positions_compared"] += len(shared)
        tot["positions_changed"] += len(ch)
        tot["close_changed"] += cc
        tot["volume_changed"] += vc
        tot["open_high_low_changed"] += ohl
        tot["only_in_one"] += len(one)
    tot["all_gaps_at_least_48h"] = all(o["gap_at_least_48h"] for o in out)
    IND.write_text(json.dumps({"method": __doc__.strip().splitlines()[0], "pairs": out, "summary": tot}, indent=1, sort_keys=True) + "\n")
    print(json.dumps(tot))


if __name__ == "__main__":
    {"archive": cmd_archive, "check": cmd_check}[sys.argv[1]]()
