"""Predictive intelligence Phase 01 repair pass 2: point-in-time decision records (CC-02, PI-D-021).

Built from skeptic counterexample CX-S1: real rows of mint 6GmAFSYs... from exports 15c2087e and 996190ce. Under the old rule
(identity = (mint, created_at), decision time = first export holding the key, row taken from a later export) the REJECTED,
fatal-flagged row first exported at 22:20:37Z would carry the 21:53:55Z decision time. No network, no clock, no file writes.
"""
import copy
import json
from pathlib import Path

import pytest

from memelab.predictive import decisions as D

FIX = json.loads((Path(__file__).resolve().parent / "fixtures/predictive/cx_s1_exports.json").read_text())
EXPORTS = FIX["exports"]
T1, T2 = EXPORTS[0]["commit_time"], EXPORTS[1]["commit_time"]
KEY = 1791331150.554


def test_cx_s1_a_row_first_exported_later_never_inherits_its_key_time():
    assert T2 - T1 == 1602                      # 26.7 min
    cands = D.candidates(EXPORTS)
    rejected = [c for c in cands if c["created_at"] == KEY and c["row"]["status"] == "REJECTED"]
    assert len(rejected) == 1
    assert rejected[0]["first_visible"] == T2 and rejected[0]["first_commit"].startswith("996190ce")
    assert json.loads(rejected[0]["row"]["fatal_flags_json"])[0]["flag"] == "CLUSTER_OWNERSHIP_GT_25PCT"
    at_t1 = [c for c in cands if c["created_at"] == KEY and c["first_visible"] == T1]
    assert [c["row"]["status"] for c in at_t1] == ["SETUP DEVELOPING"]
    # the old rule, written out: the key's first export time with a row read from a later export
    key_first = next(e["commit_time"] for e in EXPORTS if any(float(r["created_at"]) == KEY for r in e["theses"]))
    assert key_first == T1 != rejected[0]["first_visible"]


def test_every_candidate_row_exists_in_the_export_at_its_first_visible_time():
    by_commit = {e["commit"]: {D.row_sha256(r) for r in e["theses"]} for e in EXPORTS}
    for c in D.candidates(EXPORTS):
        assert c["row_sha256"] in by_commit[c["first_commit"]]
        earlier = [e for e in EXPORTS if e["commit_time"] < c["first_visible"]]
        assert all(c["row_sha256"] not in by_commit[e["commit"]] for e in earlier)


def test_decision_rows_are_point_in_time_and_conflicts_are_flagged():
    evs = D.decisions(D.candidates(EXPORTS))
    assert [(e["decision_time"], e["created_at"], e["status"]) for e in evs] == [
        (T1, 1791391795.507, "DISTRIBUTION RISK"),          # newest row visible at 21:53:55Z
        (T2, 1791394883.462, "REJECTED")]                    # newest key at 22:20:37Z, two rows: first in file order
    assert evs[0]["flags"] == [] and json.loads(evs[0]["fatal_flags_json"]) == []
    assert evs[1]["flags"] == ["KEY_CONFLICT"] and evs[1]["rows_sharing_key"] == 2
    assert all(e["row_first_visible"] <= e["decision_time"] for e in evs)
    assert not any(e["status"] == "REJECTED" and e["decision_time"] == T1 for e in evs)
    assert [e["decision_time"] for e in D.thin(evs, 86400)] == [T1]
    assert all(e["chain"] == "solana" and e["decision_time_basis"] == "EXPORT_COMMIT" for e in evs)


def _ex(commit, t, rows, chain="solana"):
    return {"commit": commit, "commit_time": t, "theses": rows, "tokens": [{"mint": "M", "chain": chain}] if chain else []}


def _row(created, status, score=50):
    return {"mint": "M", "created_at": created, "status": status, "score": score, "fatal_flags_json": "[]", "snapshot_json": '{"price": 1.0}'}


def test_equal_created_at_tie_is_file_order_and_flagged():
    a, b = _row(100.0, "WATCH", 56), _row(100.0, "REJECTED", 0)
    e1 = D.decisions(D.candidates([_ex("c1", 1000, [a, b])]))
    e2 = D.decisions(D.candidates([_ex("c1", 1000, [b, a])]))
    assert e1[0]["status"] == "WATCH" and e2[0]["status"] == "REJECTED"
    assert e1[0]["flags"] == e2[0]["flags"] == ["KEY_CONFLICT"]
    same = D.decisions(D.candidates([_ex("c1", 1000, [a, dict(a, id=7)])]))      # same content, other id: one row, no conflict
    assert same[0]["flags"] == [] and same[0]["rows_sharing_key"] == 1


def test_a_later_revision_of_the_newest_key_is_not_a_new_decision():
    a, a2 = _row(100.0, "SETUP DEVELOPING", 69), _row(100.0, "REJECTED", 60)
    evs = D.decisions(D.candidates([_ex("c1", 1000, [a]), _ex("c2", 2000, [a2, a])]))
    assert [(e["decision_time"], e["status"]) for e in evs] == [(1000, "SETUP DEVELOPING")]
    newer = _row(150.0, "WATCH")
    evs = D.decisions(D.candidates([_ex("c1", 1000, [a]), _ex("c2", 2000, [a2, a]), _ex("c3", 3000, [newer, a2])]))
    assert [(e["decision_time"], e["status"]) for e in evs] == [(1000, "SETUP DEVELOPING"), (3000, "WATCH")]


def test_missing_token_row_gives_no_chain_and_exports_must_be_ordered():
    evs = D.decisions(D.candidates([_ex("c1", 1000, [_row(1.0, "WATCH")], chain=None)]))
    assert evs[0]["chain"] is None
    with pytest.raises(ValueError):
        D.candidates([_ex("c2", 2000, []), _ex("c1", 1000, [])])


def test_both_export_layouts_are_read():
    doc_new = {"_exported_at": 1.0, "_tables": {"theses": [_row(1.0, "WATCH")], "tokens": [{"mint": "M", "chain": "solana"}]}}
    doc_old = {"theses": [_row(1.0, "WATCH")], "tokens": [{"mint": "M", "chain": "solana"}]}
    for doc in (doc_new, copy.deepcopy(doc_old)):
        ex = D.export_from_doc("c", 5, doc)
        assert len(ex["theses"]) == 1 and ex["tokens"][0]["chain"] == "solana"
