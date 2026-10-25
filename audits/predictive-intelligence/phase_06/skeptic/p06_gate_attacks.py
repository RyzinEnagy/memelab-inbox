"""Phase 06 skeptic: attacks on labels.training_labels. Run from the skeptic clone root:
   python -m pytest -q -p no:cacheprovider /home/claude/pi_orchestration/skeptic/p06_gate_attacks.py --rootdir=. -c /dev/null
Each test documents what the gate does; 'GAP' tests show a row the gate lets through."""
import json, sys
from pathlib import Path
import pytest
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
import test_predictive_labels as T            # helpers only (dec, mkread, build_one, ref_rows, grid)
from memelab.predictive import contract as C, labels as L, runtime as R, store as S

H0 = L.holdout_start()

@pytest.fixture
def con(tmp_path):
    c = L.connect(tmp_path / "g.sqlite"); yield c; c.close()

def stored_row(con, **tamper):
    recs, _ = T.build_one(T.ref_rows(1.0) + T.grid(T.TE, T.TE + 2 * 86400, c=1.0))
    rec = recs[L.T1]
    assert rec["state"] == "LABELED"
    reg = C.registry_sha256()
    L.store_labels(con, [], export_ref="x", params={}, now=T.LATE)        # creates the run row
    run_key = L.sha([L.LABELS_VERSION, reg, "x", {}])
    row = L.record_row(rec, run_key=run_key, registry_sha=reg, now=T.LATE)
    row.update(tamper); row["label_key"] = L.sha([row["label_key"], sorted(tamper.items())])
    L._insert_strict(con, "predictive_labels", row)
    return row

def test_legit_pending_censored_purged_holdout_are_refused(con):
    # legit build path: pending (read before maturity) never reaches the gate; HOLDOUT rows cannot be stored
    recs, _ = T.build_one(T.ref_rows(1.0) + T.grid(T.TE, T.TE + 2 * 86400, c=1.0), boundary=L.needed_boundary(L.T1B, T.DT),
                          retrieved=C.label_matures_at(L.T1, T.DT) - 1)
    L.store_labels(con, list(recs.values()), export_ref="x", params={}, now=T.LATE)
    assert L.training_labels(con, T.LATE, L.T1) == []
    with pytest.raises(Exception):
        stored_row(con, split="HOLDOUT")
    stored_row(con, split="PURGED"); assert L.training_labels(con, T.LATE, L.T1) == []

def test_censored_and_pending_state_rows_refused(con):
    with pytest.raises(Exception):     # CHECK: LABELED needs a label; censored flag must match state
        stored_row(con, state="PENDING")
    with pytest.raises(Exception):
        stored_row(con, censored=1)

def test_GAP_holdout_decision_time_with_split_development_passes(con):
    """split is trusted: a row whose decision_time is inside the holdout window but split says DEVELOPMENT is returned."""
    dt = H0 + 3600
    row = stored_row(con, decision_time=dt, label_matures_at=C.label_matures_at(L.T1, dt), label_observed_at=dt + 30 * 86400)
    got = L.training_labels(con, dt + 30 * 86400, L.T1)
    assert any(r["label_key"] == row["label_key"] for r in got)

def test_GAP_stored_maturity_is_trusted_not_recomputed(con):
    """provider mode: a row whose stored label_matures_at is earlier than contract.label_matures_at(decision_time) passes an
    as_of before the true maturity, because assert_scorable is called with max(as_of, label_observed_at)."""
    true_m = C.label_matures_at(L.T1, T.DT)
    row = stored_row(con, label_matures_at=true_m - 40000)
    as_of = true_m - 30000                      # the label has NOT matured at as_of under the registry rule
    got = L.training_labels(con, as_of, L.T1)
    assert any(r["label_key"] == row["label_key"] for r in got)
    assert L.training_labels(con, as_of, L.T1, mode="capture") == []      # capture mode refuses it (observed after as_of)

def test_GAP_bakeoff_guard_cannot_fire_on_table_rows(con):
    """predictive_labels has no 'use' column, so refuse_bakeoff_labels never sees BAKEOFF_ONLY on a stored row."""
    cols = [r[1] for r in con.execute("PRAGMA table_info(predictive_labels)")]
    assert "use" not in cols

def test_refuse_sealed_is_not_on_the_gate_path():
    import inspect
    assert "refuse_sealed" not in inspect.getsource(L.training_labels)

def test_GAP_revision_to_censored_keeps_original_label(con):
    """A later re-read that makes the label UNVERIFIABLE (censored) is stored as a revision row, but the gate filters
    on state=LABELED before choosing the newest version, so the original label stays in training after the revision."""
    row = stored_row(con)
    rev = dict(row, state="UNVERIFIABLE_NO_VENDOR_HISTORY", label=None, label_class=None, censored=1,
               revision_of=row["label_key"], revision_reason="re-read", label_observed_at=T.LATE + 86400)
    rev["label_key"] = L.sha(["rev", row["label_key"]])
    L._insert_strict(con, "predictive_labels", rev)
    got = L.training_labels(con, T.LATE + 2 * 86400, L.T1)
    assert [r["label_key"] for r in got] == [row["label_key"]]
