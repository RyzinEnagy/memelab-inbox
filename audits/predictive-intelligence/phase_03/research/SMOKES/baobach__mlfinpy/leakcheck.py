"""Independent brute-force leak checks for splitters (R2, Phase 03).

Label window of a row = half-open [decision_time, label_matures_at): the label is unknown before label_matures_at
and usable from then on (memelab contract: a training label must have matured by the training cutoff).
A training row leaks into a test fold when its window overlaps any test row's window:
    dec_i < mat_j  and  dec_j < mat_i
For a walk-forward fold this is the same as: the training label matures after the first test decision.
"""
import numpy as np


def overlap_leaks(train_idx, test_idx, dec, mat):
    train_idx = np.asarray(train_idx, dtype=int)
    test_idx = np.asarray(test_idx, dtype=int)
    if len(train_idx) == 0 or len(test_idx) == 0:
        return np.array([], dtype=int)
    a_s, a_e = dec[train_idx][:, None], mat[train_idx][:, None]
    b_s, b_e = dec[test_idx][None, :], mat[test_idx][None, :]
    hit = ((a_s < b_e) & (b_s < a_e)).any(axis=1)
    return train_idx[hit]


def embargo_violations(train_idx, test_idx, dec, mat, embargo_s):
    """Training rows decided inside [max test maturity, max test maturity + embargo] after a contiguous test block."""
    train_idx = np.asarray(train_idx, dtype=int)
    test_idx = np.sort(np.asarray(test_idx, dtype=int))
    if len(train_idx) == 0 or len(test_idx) == 0 or embargo_s <= 0:
        return np.array([], dtype=int)
    runs = np.split(test_idx, np.where(np.diff(test_idx) > 1)[0] + 1)
    bad = np.zeros(len(train_idx), dtype=bool)
    for r in runs:
        end = mat[r].max()
        bad |= (dec[train_idx] >= end) & (dec[train_idx] <= end + embargo_s)
    return train_idx[bad]
