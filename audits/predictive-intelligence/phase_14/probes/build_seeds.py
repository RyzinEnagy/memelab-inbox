"""Phase 14 real seeds: one behavioral seed per development decision (decision time before 2026-10-17T00:00Z) of the Phase 05
store, from `socialcat.socialcat_as_of` with the decision's own export tables, built exactly as Phase 10's runner builds the
snapshots (`run_social.all_snapshots`, pinned MAIN_REF). Reads no label: `labels.training_labels` and `labels.load` are replaced
by functions that raise before anything runs, and any open of the sealed folder raises (audit hook). No network (Phase 10's
audit hook refuses every socket call in this process).

    python -B build_seeds.py OUT_DIR [--feature-store PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from memelab.predictive import behavioral as BH  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seed_convert  # noqa: E402

LABEL_CALLS: list[str] = []
SEALED_OPENS: list[str] = []


def _no_labels(*a, **k):
    LABEL_CALLS.append("training_labels")
    raise RuntimeError("Phase 14 reads no label")


L.training_labels = _no_labels


def _hook(event, args):
    if event == "open" and args and "phase_06/sealed" in str(args[0]):
        SEALED_OPENS.append(str(args[0]))
        raise RuntimeError("the sealed folder is never opened in Phase 14")


sys.addaudithook(_hook)

_spec = importlib.util.spec_from_file_location("p10_run_social", REPO / "audits/predictive-intelligence/phase_10/probes/run_social.py")
P10 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P10)
DEV_END = L.holdout_start()            # 2026-10-17T00:00:00Z


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--feature-store", default=P10.P7.FEATURE_STORE)
    a = ap.parse_args()
    out = Path(a.out)
    (out / "behavioral").mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    fs_sha_before = P10.P7.fsha(a.feature_store)
    fs = P10.P7.ro(a.feature_store)
    snaps, provenance = P10.all_snapshots(fs)
    if provenance.get("blob_differs") or provenance.get("commit_time_differs"):
        raise SystemExit(f"export context provenance failed: {provenance}")
    dev = sorted((s for s in snaps.values() if float(s["decision_time"]) < DEV_END), key=lambda s: (s["decision_time"], s["decision_key"]))
    lines, kinds, refused = [], Counter(), Counter()
    for s in dev:
        seed = seed_convert.seed_from_snapshot(s)
        errs = BH.check_seed(seed)
        for e in errs:
            refused[e] += 1
        for o in seed["observations"]:
            kinds[(o["kind"], o["name"])] += 1
        lines.append(BH.canon({"decision_key": s["decision_key"], "export_commit": s["export_commit"], "seed": seed, "check_seed": errs}))
    body = "\n".join(lines) + "\n"
    (out / "behavioral/SEEDS_DEV.jsonl").write_text(body)
    log = {"script": "audits/predictive-intelligence/phase_14/probes/build_seeds.py", "start_utc": BH.iso(t0), "end_utc": BH.iso(time.time()),
           "head": P10.git("rev-parse", "HEAD").strip(), "main_ref": P10.MAIN_REF, "feature_store_sha256_before": fs_sha_before,
           "feature_store_sha256_after": P10.P7.fsha(a.feature_store), "decisions_in_store": len(snaps), "development_decisions": len(dev),
           "dev_end_utc": BH.iso(DEV_END), "export_provenance": provenance, "seeds_refused": sum(1 for x in lines if json.loads(x)["check_seed"]),
           "refusal_codes": dict(refused), "observation_counts": {f"{k}:{n}": v for (k, n), v in sorted(kinds.items())},
           "label_calls": LABEL_CALLS, "sealed_opens": SEALED_OPENS, "socket_events": P10.SOCKET_EVENTS,
           "seeds_sha256": hashlib.sha256(body.encode()).hexdigest()}
    (out / "behavioral/SEEDS_DEV_LOG.json").write_text(json.dumps(log, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: log[k] for k in ("development_decisions", "seeds_refused", "label_calls", "socket_events", "seeds_sha256")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
