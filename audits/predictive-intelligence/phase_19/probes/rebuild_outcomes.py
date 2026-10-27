"""Phase 19: offline rebuild of the prospective outcomes from the committed archive only (raw/ bodies and lists, data/read_map.json,
the state exports in git at REF), compared with the ledger's current outcomes. No network (audit hook), no private store: a
temporary store is built from scratch. Written after the recorded runs as an independent check; it changes no output.

    python -B rebuild_outcomes.py OUT.json
"""
from __future__ import annotations

import base64  # noqa: F401
import csv
import gzip
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

HERE = Path(__file__).resolve().parent
PH = HERE.parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))

SOCKETS: list[str] = []


def _hook(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
        SOCKETS.append(event)
        raise RuntimeError("the rebuild makes no network call")


sys.addaudithook(_hook)

from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402
from memelab.predictive import monitoring as M  # noqa: E402
from memelab.predictive import sources as SRC  # noqa: E402
from memelab.predictive import store as S  # noqa: E402

REF = "71fc50e1eb86d916034bb0285a466cf2ec1cc4d0"
P0 = L.prospective_start()
WINDOW_END = C.parse_utc("2026-10-26T10:23:04Z") + 1.0


def pools_of_list(body):
    d = json.loads(body)
    out = []
    for it in d.get("data") or []:
        a = (it.get("attributes") or {}).get("address")
        if isinstance(a, str):
            try:
                out.append(S.check_address("solana", a, "pool"))
            except S.StoreError:
                continue
    return out


def main(out: Path) -> int:
    t0 = time.time()
    tmp = Path(tempfile.mkdtemp(prefix="p19_rebuild_")) / "rebuild.sqlite"
    con = L.connect(tmp)
    S.ingest_exports(con, SRC.export_versions(REPO, REF), now=time.time(), ref=REF)
    man = list(csv.DictReader(open(PH / "raw/MANIFEST.csv")))
    lists, keys_ok = {}, 0
    for m in man:
        blob = (PH / "raw" / m["file"]).read_bytes()
        assert hashlib.sha256(blob).hexdigest() == m["file_sha256"], m["file"]
        body = gzip.decompress(blob)
        assert hashlib.sha256(body).hexdigest() == m["body_sha256"], m["file"]
        if m["file"].startswith("lists/"):
            lists[m["mint"]] = pools_of_list(body) if m["http_status"] == "200" else None
            continue
        b = float(parse_qs(urlsplit(m["request_url"]).query)["before_timestamp"][0])
        resp = {"url": m["request_url"], "params": {"token": S.url_token(m["request_url"])}, "retrieved_at": float(m["retrieved_t"]),
                "http_status": int(m["http_status"]), "body": body, "boundary_at": int(b), "timeframe": "minute", "aggregate": 5,
                "collector": "phase_19/fetch_labels.py"}
        r = S.ingest_gt_response(con, resp, chain="solana", mint=m["mint"], pool=m["pool"], now=time.time())
        keys_ok += r["response_key"] == m["response_key"]
    con.commit()
    rows = [dict(r) for r in con.execute("SELECT * FROM predictive_decisions WHERE decision_key IS NOT NULL AND decision_time >= ? "
                                         "AND decision_time < ? ORDER BY decision_time, mint, id", (P0, WINDOW_END))]
    decs = [L.decision_from_row(r, vendor_pools=(lists[r["mint"]] if lists[r["mint"]] is not None else L.LIST_FAILED)
                                if r["mint"] in lists else None) for r in rows]
    rmap = json.loads((PH / "data/read_map.json").read_text())
    read_of = {k: L.read_from_store(con, rk) for k, rk in rmap.items()}
    op = PH / "data/other_pool_reads.json"
    others = ({k: (L.LIST_FAILED if v == L.LIST_FAILED else [L.read_from_store(con, x) if x else None for x in v])
               for k, v in json.loads(op.read_text()).items()} if op.exists() else {})
    idx = M.load(PH / "monitoring/OUTCOME_LEDGER.jsonl")
    cur = M.current_outcomes(idx)
    as_of = max(float(o["recorded_at"]) for o in cur.values())
    recs = M.prospective_records(L.Universe(decs, as_of=as_of, read_of=read_of, other_reads=others))
    mine = {(r["decision_key"], r["target"]): (r["state"], r.get("label_class") if r["state"] == "LABELED" else None,
                                               r.get("label") if r["state"] == "LABELED" else None) for r in recs}
    led = {k: (o["state"], o["label_class"], o["label"]) for k, o in cur.items()}
    diff = sorted(k for k in set(mine) | set(led) if mine.get(k) != led.get(k))
    res = {"archive_files": len(man), "response_keys_equal": keys_ok, "ohlcv_files": sum(1 for m in man if not m["file"].startswith("lists/")),
           "window_decisions": len(rows), "records": len(mine), "ledger_outcomes": len(led), "differences": len(diff),
           "difference_keys": [[k[0][:12], k[1]] for k in diff[:10]], "as_of_utc": L._iso(as_of), "socket_events": len(SOCKETS),
           "wall_s": round(time.time() - t0, 1)}
    out.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps(res))
    return 0 if not diff and len(mine) == len(led) else 1


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
