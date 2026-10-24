"""Skeptic 04: folds that core_numpy.fold_audit certifies although they train on information not available at the cutoff.
    python -I -B skeptic_04_fold_attack.py REPO
"""
import csv, json, subprocess, sys
from pathlib import Path
import numpy as np
repo = Path(sys.argv[1]); proto = repo / "audits/predictive-intelligence/phase_04/adoption/prototypes"
sys.path.insert(0, str(proto)); import core_numpy as K
rows = list(csv.DictReader(open(proto.parent / "data/dev_t1_24h.csv")))
t = np.array([float(r["decision_time"]) for r in rows]); m = np.array([float(r["label_matures_at"]) for r in rows])
mint = np.array([r["mint"] for r in rows]); n = len(t)
first = 1791676800.0  # 2026-10-11T00:00Z: the first cutoff is the midnight after it (frozen rule)
res = {}
lab = K.day_walk_forward(t, m, first_last_train_day=first, min_train=30)
res["0_lab_rule_real_24h"] = {"valid": K.fold_audit(t, m, lab, n)["valid_walk_forward"], "folds": len(lab)}
# A. one test row with a missing decision time (NaN) switches every leak check off
leaky = K.day_walk_forward(t, np.minimum(m, t), first_last_train_day=first, min_train=30)    # maturity purge removed
t_nan = t.copy()
for f in leaky:
    t_nan[f["test"][0]] = np.nan          # one test row per fold without a decision time
a_ref = K.fold_audit(t, m, [{"train": f["train"], "test": f["test"]} for f in leaky], n)
a_nan = K.fold_audit(t_nan, m, [{"train": f["train"], "test": f["test"]} for f in leaky], n)
res["A_purge_removed_audit"] = {"valid": a_ref["valid_walk_forward"], "leaked_labels": sum(r["train_labels_maturing_after_test_start"] for r in a_ref["folds"])}
res["A_same_folds_one_test_decision_time_NaN"] = {"valid": a_nan["valid_walk_forward"], "leaked_labels_counted": sum(r["train_labels_maturing_after_test_start"] for r in a_nan["folds"])}
m_nan = m.copy()
leak_rows = sorted({int(i) for f in leaky for i in f["train"] if m[i] > f["cutoff"]})
m_nan[leak_rows] = np.nan        # only the leaking training rows lose their maturity time
a_mn = K.fold_audit(t, m_nan, [dict(f) for f in leaky], n)
res["A2_purge_removed_leaking_rows_maturity_NaN"] = {"valid": a_mn["valid_walk_forward"], "rows_set_to_NaN": len(leak_rows)}
# B. declared cutoff after the test start (model card would claim a training time later than the decisions it predicts)
late = [dict(f, cutoff=f["cutoff"] + 2 * 86400) for f in lab]
res["B_cutoff_declared_two_days_after_test_start"] = {"valid": K.fold_audit(t, m, late, n)["valid_walk_forward"]}
# C. maturity of the wrong horizon (6 h) given for 24 h labels: folds built and audited on the same wrong column
m6 = t + 300 + 21600 + 900
wrong = K.day_walk_forward(t, m6, first_last_train_day=first, min_train=30)
res["C_6h_maturity_for_24h_labels"] = {"audit_on_supplied_column_valid": K.fold_audit(t, m6, wrong, n)["valid_walk_forward"],
    "audit_on_true_column_valid": K.fold_audit(t, m, wrong, n)["valid_walk_forward"],
    "labels_maturing_after_cutoff_true": sum(r["train_labels_maturing_after_cutoff"] for r in K.fold_audit(t, m, wrong, n)["folds"])}
# D. same mint in training and test (allowed by the frozen plan as a sensitivity; the audit has no group field)
res["D_test_rows_whose_mint_is_in_training"] = [int(np.isin(mint[f["test"]], mint[f["train"]]).sum()) for f in lab]
res["D_test_rows"] = [int(len(f["test"])) for f in lab]
# E. decision_time equals the committer time of the commit recorded in the row (PI-D-015), all rows
ct = {}
bad = 0
for r in rows:
    c = r["commit"]
    if c not in ct:
        ct[c] = float(subprocess.run(["git", "show", "-s", "--format=%ct", c], cwd=repo, capture_output=True, text=True).stdout.strip())
    bad += ct[c] != float(r["decision_time"])
res["E_rows_whose_decision_time_is_not_their_commit_time"] = bad
print(json.dumps(res, indent=1))
