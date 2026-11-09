"""Phase 21 skeptic counterexample CX-S21: a censored outcome recorded before its label matures.

Wrong but plausible: a maturity run (or a one-line bug in monitoring.prospective_records that drops `if mature else "PENDING"`)
records a T2 decision as VENDOR_OR_ROUTE_GAP (censored, final) before label_matures_at, because the vendor pool list was empty at
that moment. For T2 ("halves, or trading stops and stays stopped") a vanished pool is exactly the decision most likely to be a
positive; censoring it early drops a positive from every later evaluation, and as a FINAL state it can only be replaced by a
revision. VENDOR_OR_ROUTE_GAP depends on the window (production code emits it only once matured, else PENDING), so this is a
premature outcome, the same class as "LABELED before maturity" which the chronology audit and the ledger both refuse.
(MARKET_INACTIVE, THINNED, NO_SNAPSHOT_PRICE and OUT_OF_SCOPE_CHAIN are decision-time classes and may be recorded early.)

Checks run (no network, nothing in the repository is changed; a temp copy of the ledger is used):
  A. phase_21/probes/chronology_audit.py c2_c3 on the committed ledger with one first-of-pair T2 VENDOR_OR_ROUTE_GAP outcome's recorded_at moved to
     label_matures_at - 3600 (in memory).
  B. memelab.predictive.monitoring.append on a temp copy of the ledger truncated just before that outcome, re-appending the
     same payload with recorded_at = label_matures_at - 3600, then monitoring.verify on the result.
  C. control: the same two checks with state LABELED-before-maturity are refused (so the harness is live).

    python -B p21_cx_early_censor.py REPO OUTJSON
"""
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "audits/predictive-intelligence/phase_21/probes"))
import chronology_audit as CA  # noqa: E402
from memelab.predictive import monitoring as M  # noqa: E402

LED = REPO / "audits/predictive-intelligence/phase_19/monitoring/OUTCOME_LEDGER.jsonl"
idx = M.load(LED)
seqs, pays = [e["seq"] for e in idx.entries], [e["payload"] for e in idx.entries]
ver = M.verify(LED)
res = {}

# A: chronology audit
i = next(k for k, p in enumerate(pays) if p["kind"] == "OUTCOME" and p["state"] == "VENDOR_OR_ROUTE_GAP"
         and p["target"].endswith("halt_24h") and not p["supersedes"])
q = copy.deepcopy(pays)
q[i]["recorded_at"] = float(q[i]["label_matures_at"]) - 3600.0
_, c3 = CA.c2_c3(seqs, q, ver)
res["A_chronology_C3_ok_with_early_VENDOR_OR_ROUTE_GAP"] = c3["ok"]
lab = next(k for k, p in enumerate(pays) if p["kind"] == "OUTCOME" and p["state"] == "LABELED")
q2 = copy.deepcopy(pays)
q2[lab]["recorded_at"] = float(q2[lab]["label_matures_at"]) - 3600.0
res["C_control_chronology_C3_ok_with_early_LABELED"] = CA.c2_c3(seqs, q2, ver)[1]["ok"]

# B: the ledger's own append check
lines = LED.read_text().splitlines(keepends=True)
tmp = Path(tempfile.mkdtemp())


def try_append(pos, payload):
    t = tmp / f"ledger_{pos}.jsonl"
    t.write_text("".join(lines[:pos]))
    try:
        M.append(t, [payload])
        v = M.verify(t)
        return {"appended": True, "verify_ok": v["ok"]}
    except M.LedgerError as e:
        return {"appended": False, "refused": str(e)[:160]}


p = copy.deepcopy(pays[i])
p["recorded_at"] = float(p["label_matures_at"]) - 3600.0
res["B_monitoring_append_early_VENDOR_OR_ROUTE_GAP"] = try_append(i, p)
p2 = copy.deepcopy(pays[lab])
p2["recorded_at"] = float(p2["label_matures_at"]) - 3600.0
res["C_control_monitoring_append_early_LABELED"] = try_append(lab, p2)
res["target_of_planted_outcome"] = pays[i]["target"]
res["caught_by_anything"] = (not res["A_chronology_C3_ok_with_early_VENDOR_OR_ROUTE_GAP"]) or (
    not res["B_monitoring_append_early_VENDOR_OR_ROUTE_GAP"].get("appended"))
shutil.rmtree(tmp)
Path(sys.argv[2]).write_text(json.dumps(res, indent=1) + "\n")
print(json.dumps(res, indent=1))
