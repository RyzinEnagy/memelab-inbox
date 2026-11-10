"""CM-2: check the label reads made before the 2026-11-10 01:25 UTC session restart against the frozen plan (build_cm2.py
fetch_t2 at e79d846) before resuming. Read-only; writes evidence/interruption.json. No network."""
from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_cm2 as B  # noqa: E402

L, C, M, SRC = B.L, B.C, B.M, B.SRC
done = json.loads((B.EV / "t2_reads.json").read_text())
cur = M.current_outcomes(M.load(B.LEDGER19))
pend = sorted(k for (k, t), o in cur.items() if t == L.T2 and o["state"] == "PENDING")
decs = {d["decision_key"]: d for d in B.p19_universe(time.time(), {}).decisions}
checks = []
for i, r in enumerate(done["reads"]):
    d = decs[r["decision_key"]]
    b = int(L.needed_boundary(L.T2, d["decision_time"]))
    blob = (B.CM2 / "raw" / r["file"]).read_bytes()
    body = gzip.decompress(blob)
    c = {"decision_key": r["decision_key"],
         "is_pending_t2": r["decision_key"] in pend,
         "is_next_in_frozen_order": r["decision_key"] == pend[i],
         "boundary_is_t2_window_end": r["boundary"] == b,
         "url_is_frozen_url": r["url"] == SRC.gt_url(d["pool"], b, token=d["mint"]),
         "token_is_mint": ("token=" + d["mint"]) in r["url"] and r["mint"] == d["mint"],
         "pool_is_decision_pool": r["pool"] == d["pool"],
         "matured_before_read": C.label_matures_at(L.T2, d["decision_time"]) < r["requested_at"],
         "file_sha256_ok": hashlib.sha256(blob).hexdigest() == r["file_sha256"],
         "body_sha256_ok": hashlib.sha256(body).hexdigest() == r["body_sha256"],
         "http": r["http"]}
    c["consistent"] = all(v for k, v in c.items() if k not in ("decision_key", "http")) and r["http"] == 200
    checks.append(c)
untracked = subprocess.run(["git", "-C", str(B.REPO), "status", "--porcelain", "--untracked-files=all"], capture_output=True,
                           text=True).stdout.split("\n")
res = {"head_at_check": subprocess.run(["git", "-C", str(B.REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
       "pending_t2": len(pend), "reads_before_restart": len(done["reads"]), "others_before_restart": len(done["others"]),
       "checks": checks, "all_consistent": all(c["consistent"] for c in checks),
       "label_calls_json_present": (B.EV / "label_calls.json").exists(),
       "untracked_at_check": sorted(x[3:] for x in untracked if x.strip()),
       "note": ("fetch_t2 writes t2_reads.json after each read but writes label_calls.json only at its end, so the call log of the "
                "read made before the restart is missing; that call is reconstructed from its t2_reads record (one call, attempt 0, "
                "http 200) and added by the resume step as a separate, labelled entry")}
B.D.jsave(B.EV / "interruption.json", res)
print(json.dumps({k: v for k, v in res.items() if k != "checks"}), json.dumps(checks))
