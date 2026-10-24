"""Phase 05: build the frozen test fixtures from real data (run once; the outputs are committed).

    python -B build_fixtures.py pid011   # tests/fixtures/predictive/asof_pid011_export.json
    python -B build_fixtures.py golden   # tests/fixtures/predictive/asof_fixture.json (needs the real store of build_store.py)

pid011: real rows of export 996190ce (2026-10-07T22:20:37Z, the second export on main): every thesis row and the token row of
four mints whose token row was written after their first thesis's created_at and two whose token row was older. Free-text
columns (thesis_text, invalidation_text, score_breakdown_json, report_path) are removed to keep the file small; every time
column is untouched.

golden: the real decision events of a few mints (a pool the vendor has no data for, a sparse pool with two decisions, a pool
whose mint is the quote token, an EVM decision), every export version holding their rows (exact rows, each stored once), and
the real GeckoTerminal bodies of their pools from the Phase 05 store, base64 of gzip, with request, retrieval time and sha256.
The test rebuilds a store from it and pins the snapshot hashes.
"""
from __future__ import annotations

import base64
import collections
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
from memelab.predictive import decisions as D  # noqa: E402
from memelab.predictive import store as S  # noqa: E402

FIX = REPO / "tests" / "fixtures" / "predictive"
DROP = ("thesis_text", "invalidation_text", "score_breakdown_json", "report_path")
STORE = Path("/home/claude/pi_research/p05/predictive_store.sqlite")


def git(*a):
    return subprocess.run(["git", "-C", str(REPO), *a], check=True, capture_output=True).stdout


def pid011():
    commit = git("rev-parse", "996190ce").decode().strip()
    ct = int(git("show", "-s", "--format=%ct", commit).decode())
    doc = json.loads(git("show", f"{commit}:data/state/latest.json"))
    T = doc["_tables"]
    first = collections.defaultdict(lambda: float("inf"))
    for r in T["theses"]:
        first[r["mint"]] = min(first[r["mint"]], r["created_at"])
    tok = {k["mint"]: k for k in T["tokens"]}
    lag = sorted(m for m in first if m in tok and tok[m]["first_seen_at"] > first[m])[:4]
    nolag = sorted(m for m in first if m in tok and tok[m]["first_seen_at"] <= first[m])[:2]
    keep = set(lag + nolag)
    theses = [{k: v for k, v in r.items() if k not in DROP} for r in T["theses"] if r["mint"] in keep]
    tokens = [tok[m] for m in sorted(keep)]
    out = {"source": f"git show {commit}:data/state/latest.json (origin/main first-parent), rows of 6 mints, free text removed",
           "commit": commit, "commit_time": ct,
           "doc": {"_exported_at": doc.get("_exported_at"), "_tables": {"tokens": tokens, "theses": theses}},
           "expected_lagged_mints": len(lag),
           "expected_decisions": len(D.decisions(D.candidates([D.export_from_doc(commit, ct, {"_tables": {"tokens": tokens,
                                                                                                         "theses": theses}})])))}
    (FIX / "asof_pid011_export.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"lag": len(lag), "nolag": len(nolag), "theses": len(theses), "decisions": out["expected_decisions"]}))


def golden(mints: list[str]):
    con = S.connect(STORE)
    decs = S.iter_rows(con, "SELECT * FROM predictive_decisions WHERE mint IN (%s) ORDER BY decision_time" % ",".join("?" * len(mints)),
                       mints)
    exports, rows = [], {}
    for c in S.iter_rows(con, "SELECT * FROM predictive_raw_responses WHERE source_id='state-export'"):
        req = json.loads(c["request_json"])
        doc = json.loads(git("show", f"{req['commit']}:data/state/latest.json"))
        ex = D.export_from_doc(req["commit"], req["commit_time"], doc)
        th = [r for r in ex["theses"] if r["mint"] in mints]          # exact rows: row_sha256 must equal the real store's
        if not th:
            continue
        tk = [k for k in ex["tokens"] if k["mint"] in mints]
        refs = []
        for r in th + tk:
            h = S.sha(r)
            rows[h] = r
            refs.append(h)
        exports.append({"commit": req["commit"], "commit_time": req["commit_time"], "blob": req["blob"],
                        "thesis_refs": refs[:len(th)], "token_refs": refs[len(th):]})
    exports.sort(key=lambda e: e["commit_time"])
    pools = sorted({d["pool_address"] for d in decs if d["pool_address"] and d["chain"] == "solana"})
    reads = []
    for r in S.iter_rows(con, "SELECT * FROM predictive_raw_responses WHERE source_id='geckoterminal-ohlcv' AND pool_address IN (%s) "
                              "ORDER BY retrieved_at, id" % ",".join("?" * len(pools)), pools):
        reads.append({"url": r["request_url"], "params": json.loads(r["request_json"]), "retrieved_at": r["retrieved_at"],
                      "http_status": r["http_status"], "boundary_at": r["boundary_at"], "body_sha256": r["body_sha256"],
                      "chain": r["chain"], "mint": r["mint"], "pool": r["pool_address"],
                      "body_gzip_b64": base64.b64encode(r["body_gzip"]).decode()})
    status = [{k: s[k] for k in ("mint", "pool_address", "series_id", "boundary_at", "need_from", "status", "detail", "calls",
                                 "candles_kept", "last_end_at", "checked_at")} | {"response_keys": json.loads(s["response_keys_json"])}
              for s in S.iter_rows(con, "SELECT * FROM predictive_source_status WHERE pool_address IN (%s) ORDER BY checked_at, id"
                                   % ",".join("?" * len(pools)), pools)]
    out = {"source": "Phase 05 real store: export rows of these mints from git at 98338a8 (each distinct row once, exports refer to "
                     "rows by sha256 of the row as exported, in file order), GeckoTerminal reads of their pools",
           "mints": mints, "rows": rows, "exports": exports, "reads": reads, "series_status": status,
           "decisions": [{k: d[k] for k in ("decision_key", "chain", "mint", "pool_address", "decision_time")} for d in decs]}
    (FIX / "asof_fixture.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"exports": len(exports), "reads": len(reads), "decisions": len(decs), "bytes": len(json.dumps(out))}))


if __name__ == "__main__":
    if sys.argv[1] == "pid011":
        pid011()
    else:
        golden(sys.argv[2:])
