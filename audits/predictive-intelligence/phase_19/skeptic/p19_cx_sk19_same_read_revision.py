"""CX-SK19: a 'revision' of a final LABELED prospective outcome appended through monitoring.append that cites the SAME read
(same response key, URL and body sha256) with the class flipped and revision_reason LATER_READ. No line is edited, the chain
verifies, the evaluation would use the flipped label (current outcome, flagged REVISED).

    python -B p19_cx_sk19_same_read_revision.py CLONE      # modifies CLONE's committed ledger in place; restore with git checkout
"""
import sys, time
from pathlib import Path
clone = Path(sys.argv[1]); sys.path.insert(0, str(clone))
from memelab.predictive import monitoring as M
P = clone / "audits/predictive-intelligence/phase_19/monitoring/OUTCOME_LEDGER.jsonl"
cur = M.current_outcomes(M.load(P))
lab = next(o for o in cur.values() if o["state"] == "LABELED" and o["label_class"] == "TARGET_FIRST")
rev = {k: v for k, v in lab.items() if k != "outcome_id"}
rev.update(label=0, label_class="INVALIDATION_FIRST", conservative_lens=0, revision_of=lab["outcome_id"], revision_reason="LATER_READ",
           supersedes=None, recorded_at=time.time(), flags=[])
rev["outcome_id"] = "oc_" + M.sha({k: v for k, v in rev.items() if k != "recorded_at"})[:40]
print(M.append(P, [rev]))
c2 = M.current_outcomes(M.load(P))[(lab["decision_key"], lab["target"])]
print({"verify_ok": M.verify(P)["ok"], "current_label": c2["label"], "flags": c2["flags"], "same_body": c2["body_sha256"] == lab["body_sha256"],
       "scorable_with_flipped_label": any(o["outcome_id"] == c2["outcome_id"] for o in M.scorable(M.load(P), time.time()))})
