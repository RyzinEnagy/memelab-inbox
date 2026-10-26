"""Phase 12 independent check of the holdout rows that were scored (a REPRODUCTION read of the sealed label file, logged in the
evidence; no analysis beyond the plan). Plain standard library, without memelab: the sealed file's sha256 must equal the pin, the
scorable rows (HOLDOUT, LABELED, uncensored, label 0 or 1, not one of the two contacted decisions of ACCEPTANCE) are counted by
target, and each scored row's label in validation/HOLDOUT_SCORED.csv must equal the sealed label of the same decision.

    python -B independent_label_check.py OUT.json
"""
import csv
import gzip
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PIN = "e695500d01014936cf4a4a46f9975dcf9a9ca1351fe067f28ec36117cb82682b"
CONTACTED = {("CnPL1xnAVHYGH92FpmiNoNhgh3gctkH5y988hMg4bonk", "2026-10-17T10:20:42Z"),
             ("Tm2iqbxYjKpW8xCMe6q1xUraNMNzcG5xMztAir3pump", "2026-10-19T10:34:05Z")}
SHORT = {"price_path_target_before_invalidation_24h": "T1_24h", "price_path_target_before_invalidation_6h": "T1b_6h",
         "price_path_severe_drawdown_or_halt_24h": "T2_24h"}


def main() -> int:
    raw = (REPO / "audits/predictive-intelligence/phase_06/sealed/holdout_labels.jsonl.gz").read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    rows = [json.loads(x) for x in gzip.decompress(raw).decode().splitlines() if x.strip()]
    keep = {}
    for r in rows:
        iso = datetime.fromtimestamp(r["decision_time"], timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if r["split"] == "HOLDOUT" and r["state"] == "LABELED" and not r["censored"] and r["label"] in (0, 1) \
                and (r["mint"], iso) not in CONTACTED:
            keep[(SHORT[r["target"]], r["decision_key"])] = r["label"]
    with open(REPO / "audits/predictive-intelligence/phase_12/validation/HOLDOUT_SCORED.csv") as f:
        scored = {(r["target_short"], r["decision_key"]): int(r["y"]) for r in csv.DictReader(f)}
    per = {s: {"sealed_scorable": sum(1 for k in keep if k[0] == s), "sealed_positives": sum(v for k, v in keep.items() if k[0] == s),
               "scored": sum(1 for k in scored if k[0] == s)} for s in SHORT.values()}
    mism = [list(k) for k in scored if keep.get(k) != scored[k]]
    missing = [list(k) for k in keep if k not in scored]
    rep = {"mode": "REPRODUCTION read (independent of memelab)", "time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "sha256_equals_pin": sha == PIN, "per_target": per, "label_mismatches": mism, "sealed_rows_not_scored": missing}
    Path(sys.argv[1]).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps(rep))
    return 0 if sha == PIN and not mism and not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
