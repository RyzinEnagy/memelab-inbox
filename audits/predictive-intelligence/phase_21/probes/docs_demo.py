"""Phase 21: the registry facts the user guide states, checked on the committed registry (read-only, no network).

    python -B docs_demo.py AS_OF_UTC OUTJSON

1. Every entry's status at AS_OF (registry.status_at): the frozen cards are MODEL_STALE after 2026-10-31T00:00:00Z.
2. registry.serve for each target at AS_OF: no champion is used; the forecast inputs are level ABSTAIN, model not selected.
3. Retiring the stale reference cards by a pin without references is refused by registry-1 (references must name both B0 and
   B2), so retiring them means registering retrained references (a committed plan) or a change control to registry-1.
4. A rollback on a copy of the log in a temporary folder (registry.rollback_event, then registry.append_events): with no champion
   pinned it falls back to NO_VIABLE_CHAMPION with the current references, the copy stays a valid chained log, and the committed
   log is unchanged.
Exit 0 when each statement holds.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import registry as R  # noqa: E402

REG = REPO / "audits/predictive-intelligence/phase_16/registry"


def main() -> int:
    as_of_s, out = sys.argv[1], Path(sys.argv[2])
    as_of = C.parse_utc(as_of_s)
    entries = R.read_entries(REG / "entries")
    events = R.read_log((REG / "REGISTRY_LOG.jsonl").read_text())
    stale = Counter()
    stale_after = set()
    for e in entries.values():
        st = [s["state"] for s in R.status_at(e, as_of)]
        stale["MODEL_STALE" if "MODEL_STALE" in st else "OTHER"] += 1
        stale_after.add(R._iso(R.stale_after(e)))
    targets = sorted({e["target"] for e in entries.values()})
    served = {}
    for t in targets:
        s = R.serve(events, entries, t, as_of, runtime={}, root=REPO)
        served[t] = {"use_champion": s["use_champion"], "mode": s["resolved"]["mode"], "level": s["forecast_inputs"]["level"],
                     "model_id": s["forecast_inputs"]["model_id"], "reference_names": sorted(s["references"])}
    try:
        R.pin_event(entries, targets[0], mode="NO_VIABLE_CHAMPION", champion=None, references={}, reasons=["RETIRE_TEST"],
                    as_of_utc=as_of_s)
        retire = {"refused": False}
    except R.PinRefused as e:
        retire = {"refused": True, "reason": str(e)}
    committed_before = R.file_sha(REG / "REGISTRY_LOG.jsonl")
    tmp = Path(tempfile.mkdtemp(prefix="p21_rollback_"))
    try:
        shutil.copy(REG / "REGISTRY_LOG.jsonl", tmp / "log.jsonl")
        ev = R.rollback_event(events, entries, targets[0], reason="PHASE21_ROLLBACK_DEMO", as_of_utc=as_of_s, usable=lambda e: False)
        sha, new = R.append_events(tmp / "log.jsonl", [ev], expect_sha=R.file_sha(tmp / "log.jsonl"))
        after = R.read_log((tmp / "log.jsonl").read_text())
        rollback = {"event_kind": ev["kind"], "mode": ev["mode"], "references_kept": sorted(ev.get("references") or {}),
                    "copy_events_before": len(events), "copy_events_after": len(after),
                    "resolved_after": R.resolve(after, entries, targets[0], as_of)["mode"]}
        log_unchanged = R.file_sha(REG / "REGISTRY_LOG.jsonl") == committed_before
    finally:
        shutil.rmtree(tmp)
    res = {"as_of_utc": as_of_s, "entries": len(entries), "status_at_as_of": dict(stale), "stale_after_utc": sorted(stale_after),
           "serve": served, "retire_by_empty_references": retire, "rollback_without_champion": rollback,
           "committed_log_unchanged": log_unchanged}
    res["ok"] = (stale["OTHER"] == 0 and all(not v["use_champion"] and v["level"] == "ABSTAIN" for v in served.values())
                 and retire["refused"] and log_unchanged and rollback["copy_events_after"] == len(events) + 1
                 and rollback["resolved_after"] == "NO_VIABLE_CHAMPION")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"ok": res["ok"], "stale": dict(stale), "retire_refused": retire["refused"], "rollback": rollback["mode"]}))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
