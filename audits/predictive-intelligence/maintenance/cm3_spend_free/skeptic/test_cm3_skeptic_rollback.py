"""CM-3 skeptic counterexample: a signed state rolled back to an earlier signed snapshot (files plus its own
STATE_SIGNATURE.json) is accepted as SIGNED_VERIFIED, so a withdrawn pass or alert history can be silently undone.
Run from the clone root: PYTHONPATH=.:tests python -m pytest -q <this file>"""
import json, shutil
import test_predictive_cm3 as T
from test_predictive_cm3 import lab  # noqa: F401  fixture
from memelab.predictive import integration as I
import test_predictive_integration as TI


def test_rollback_to_an_older_signed_snapshot_is_accepted(lab, monkeypatch, tmp_path):
    sd = T._signed_world(lab, monkeypatch)
    snap = tmp_path / "snap"
    shutil.copytree(sd, snap)                                   # pass 0, signed
    r2 = TI.persist(TI.result("BBB", T.MINT_B, TI.T_TODAY - 300), lab)
    TI.run([r2], TI.T_TODAY + 60, lab)
    assert json.loads((sd / I.SIG_FILE).read_text())["seq"] == 1
    shutil.rmtree(sd); shutil.copytree(snap, sd)                # roll back: pass 1 disappears
    st = I.signature_status(sd)
    # The engine has no monotonic counter outside the folder, so this is SIGNED_VERIFIED, not REFUSED.
    assert st["signature"] == "SIGNED_VERIFIED" and st["seq"] == 0
