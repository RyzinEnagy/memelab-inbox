"""Phase 19 skeptic: own mutations of memelab/predictive/monitoring.py, run through the phase's own harness
(probes/mutation_monitoring.py, temporary copy, tests/test_predictive_monitoring.py with -x).

    python -B p19_own_mutations.py CLONE OUT.json
"""
import importlib.util
import sys
from pathlib import Path

clone = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("mm", clone / "audits/predictive-intelligence/phase_19/probes/mutation_monitoring.py")
mm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mm)

mm.MUTATIONS = [
    ("K2 current outcome is the first, not the newest", "        cur = dict(xs[-1])", "        cur = dict(xs[0])"),
    ("K3 scorable ignores the read time", ' or float(o["label_observed_at"]) < mat:\n            continue', ":\n            continue"),
    ("K4 scorable ignores the record time", 'if mat > as_of or float(o["recorded_at"]) > as_of or', "if mat > as_of or"),
    ("K5 D1 minimum 30 becomes 29", "        if cf.size < MIN_FEATURE_VALUES:", "        if cf.size < MIN_FEATURE_VALUES - 1:"),
    ("K6 champion with low support abstains (rule 10 literal)", '    elif pin_mode == "CHAMPION":\n        act = "NO_CHANGE"',
     '    elif pin_mode == "CHAMPION":\n        act = "KEEP_ABSTAIN"'),
    ("K7 D6 failure share at the threshold alerts", "if share is not None and share > READ_FAILURE_SHARE_ALERT:",
     "if share is not None and share >= READ_FAILURE_SHARE_ALERT:"),
    ("K8 a class change with the same state is not a revision",
     'same = (cur["state"] == rec["state"] and cur["label_class"] == (rec.get("label_class") if rec["state"] == "LABELED" else None))',
     'same = cur["state"] == rec["state"]'),
    ("K9 revision without a reason accepted", 'if p["revision_of"] != cur["outcome_id"] or not p["revision_reason"]:',
     'if p["revision_of"] != cur["outcome_id"]:'),
    ("K11 prediction identity not checked",
     'raise LedgerError("IDENTITY_MISMATCH", "decision key, chain, mint and time must equal the prediction set\'s (P01)")',
     'pass'),
    ("K12 load accepts duplicate entries", '            raise LedgerError("DUPLICATE_ENTRY", f"seq {e[\'seq\']}")', "            pass"),
    ("K13 misses never flags an unmatured label", '            st = "NOT_MATURED_AT_EVALUATION"', "            pass"),
    ("K15 prediction set key reuse accepted",
     'raise LedgerError("IDENTITY_MISMATCH", "a decision key reused with another identity")', "pass"),
    ("K16 PENDING outcomes treated as final", 'NON_FINAL = ("PENDING", "NOT_READ")', 'NON_FINAL = ("NOT_READ",)'),
    ("K17 Page-Hinkley stream not time ordered", "for t, v in sorted(stream, key=lambda tv: tv[0]) if", "for t, v in stream if"),
]
sys.exit(mm.main(sys.argv[2]))
