"""Apply attack A4 (truncate the OUTCOME tail, re-append through monitoring.append with one T1 label flipped) to a clone's
committed ledger, in place, so the suite's outputs test and the rebuild probe can be run against it. Restore with git checkout."""
import copy, sys
from pathlib import Path
clone = Path(sys.argv[1]); sys.path.insert(0, str(clone))
from memelab.predictive import monitoring as M
P = clone / "audits/predictive-intelligence/phase_19/monitoring/OUTCOME_LEDGER.jsonl"
base = M.read_ledger(P.read_text()); pls = [e["payload"] for e in base]
cur = M.current_outcomes(M.load(P))
lab = next(o for o in cur.values() if o["state"] == "LABELED" and o["label_class"] == "TARGET_FIRST")
fo = next(i for i, x in enumerate(pls) if x["kind"] == "OUTCOME")
P.write_text("".join(M.canon(e) + "\n" for e in base[:fo]))
tail = copy.deepcopy(pls[fo:])
for x in tail:
    if x["kind"] == "OUTCOME" and x["outcome_id"] == lab["outcome_id"]:
        x["label"], x["label_class"], x["conservative_lens"] = 0, "INVALIDATION_FIRST", 0
print(M.append(P, tail), lab["decision_key"][:12], lab["target"])
