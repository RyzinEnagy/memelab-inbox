"""Phase 21: strict chronology audit of the committed state, read-only, no network.

    python -B chronology_audit.py AS_OF_UTC OUTJSON

AS_OF_UTC is a fixed instant (for example 2026-11-09T00:00:00Z) so the result never depends on the wall clock. Checks:

  C1 registry: every entry in phase_16/registry/entries keeps its training cutoff (registry.training_after_cutoff is None, P05,
     P43); the registry log replays (registry.read_log: chain, canonical form, time order); at AS_OF every entry is MODEL_STALE or
     not available, and no target resolves to a CHAMPION.
  C2 prospective predictions: every Phase 19 PREDICTION entry's card cutoff is before its decision time, and its label matures
     after the decision (no card trained on its own outcome).
  C3 outcomes: the ledger verifies (monitoring.verify); every OUTCOME comes after the PREDICTION_SET that holds its decision (ledger
     order); a LABELED outcome was recorded at or after its label_matures_at and observed at or after it; a PENDING outcome was
     recorded before its maturity.
  C4 git order: in each phase 05 to 20 the acceptance checklist (pre-registration) was added in a commit no later than the commit
     that added the phase's RESULTS.json; the Phase 19 predictions commit precedes its first label call
     (run_prospective.py audit, run separately).
  C5 seal: phase_06/probes/check_seal.py exit 0 (run separately and recorded beside this file).
  Negative controls: five planted violations on in-memory copies (a LABELED outcome recorded before maturity, a prediction card
  cut off after its decision, a PENDING outcome recorded after maturity, an outcome placed before its prediction set, a registry
  entry with a training decision at its cutoff); each must be caught.

Exit 0 when every check holds, else 1.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from memelab.predictive import contract as C  # noqa: E402
from memelab.predictive import monitoring as M  # noqa: E402
from memelab.predictive import registry as R  # noqa: E402

AUD = REPO / "audits/predictive-intelligence"
SOCKETS: list[str] = []


def _hook(event, args):
    if event.startswith("socket."):
        SOCKETS.append(event)
        raise RuntimeError("network refused in the chronology audit")


def git(*a: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *a], check=True, capture_output=True, text=True).stdout


def first_add(path: str) -> tuple[str, int] | None:
    out = git("log", "--diff-filter=A", "--format=%H %ct", "--", path).strip().splitlines()
    if not out:
        return None
    h, t = out[-1].split()
    return h, int(t)


def c1(as_of: float) -> dict:
    entries = R.read_entries(AUD / "phase_16/registry/entries")
    leaks = {k[:12]: R.training_after_cutoff(e) for k, e in entries.items() if R.training_after_cutoff(e)}
    events = R.read_log((AUD / "phase_16/registry/REGISTRY_LOG.jsonl").read_text())
    states = Counter()
    for e in entries.values():
        st = {s["state"] for s in R.status_at(e, as_of)}
        states["MODEL_STALE" if "MODEL_STALE" in st else ("NOT_AVAILABLE_AS_OF" if "NOT_AVAILABLE_AS_OF" in st else "IN_AGE")] += 1
    modes = {t: R.resolve(events, entries, t, as_of)["mode"] for t in sorted({e["target"] for e in entries.values()})}
    ok = not leaks and states["IN_AGE"] == 0 and all(m != "CHAMPION" for m in modes.values())
    return {"entries": len(entries), "training_after_cutoff": leaks, "log_events": len(events), "age_states_at_as_of": dict(states),
            "modes_at_as_of": modes, "ok": ok}


def c2_c3(seqs: list[int], pays: list[dict], verify: dict) -> tuple[dict, dict]:
    bad_pred = []
    for p in pays:
        if p["kind"] != "PREDICTION":
            continue
        cut = C.parse_utc(p["training_cutoff_utc"]) if p.get("training_cutoff_utc") else None
        if cut is None or not cut < float(p["decision_time"]) or not float(p["label_matures_at"]) > float(p["decision_time"]):
            bad_pred.append(p["prediction_id"])
    n_pred = sum(1 for p in pays if p["kind"] == "PREDICTION")
    set_seq = {}
    for s, p in zip(seqs, pays):
        if p["kind"] == "PREDICTION_SET":
            for d in p["decisions"]:
                set_seq.setdefault(d["decision_key"], s)
    order_bad, mature_bad, pending_bad, states = [], [], [], Counter()
    for s, p in zip(seqs, pays):
        if p["kind"] != "OUTCOME":
            continue
        states[p["state"]] += 1
        if p["decision_key"] not in set_seq or set_seq[p["decision_key"]] >= s:
            order_bad.append(p["outcome_id"])
        if p["state"] == "LABELED":
            obs = p.get("label_observed_at")
            if float(p["recorded_at"]) < float(p["label_matures_at"]) or obs is None or float(obs) < float(p["label_matures_at"]):
                mature_bad.append(p["outcome_id"])
        if p["state"] == "PENDING" and float(p["recorded_at"]) >= float(p["label_matures_at"]):
            pending_bad.append(p["outcome_id"])
    c2 = {"predictions": n_pred, "cutoff_not_before_decision": bad_pred, "ok": n_pred > 0 and not bad_pred}
    c3 = {"verify": verify, "outcome_states": dict(states),
          "outcome_before_its_prediction_set": order_bad, "labeled_before_maturity": mature_bad,
          "pending_recorded_after_maturity": pending_bad}
    c3["ok"] = c3["verify"]["ok"] and not order_bad and not mature_bad and not pending_bad
    return c2, c3


def c4() -> dict:
    rows = []
    for n in range(5, 21):
        ph = f"audits/predictive-intelligence/phase_{n:02d}"
        a, r = first_add(f"{ph}/ACCEPTANCE_CHECKLIST.md"), first_add(f"{ph}/PHASE_{n:02d}_RESULTS.json")
        rows.append({"phase": f"{n:02d}", "checklist_commit": a and a[0][:7], "results_commit": r and r[0][:7],
                     "checklist_not_after_results": bool(a and r and a[1] <= r[1])})
    return {"phases": rows, "ok": all(x["checklist_not_after_results"] for x in rows)}


def negative_controls(seqs: list[int], pays: list[dict], verify: dict, entries: dict) -> dict:
    """Planted violations on copies of the committed records; each must turn its check false."""
    import copy
    res = {}
    lab = next(i for i, p in enumerate(pays) if p["kind"] == "OUTCOME" and p["state"] == "LABELED")
    pr = next(i for i, p in enumerate(pays) if p["kind"] == "PREDICTION")
    pen = next(i for i, p in enumerate(pays) if p["kind"] == "OUTCOME" and p["state"] == "PENDING")
    ps = next(i for i, p in enumerate(pays) if p["kind"] == "PREDICTION_SET")

    def run(mut):
        q = copy.deepcopy(pays)
        s = list(seqs)
        mut(q, s)
        return c2_c3(s, q, verify)

    def early_label(q, s):
        q[lab]["recorded_at"] = float(q[lab]["label_matures_at"]) - 1.0
    def late_cut(q, s):
        t = float(q[pr]["decision_time"]) + 1.0
        q[pr]["training_cutoff_utc"] = datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    def late_pending(q, s):
        q[pen]["recorded_at"] = float(q[pen]["label_matures_at"]) + 1.0
    def outcome_first(q, s):
        s[lab] = s[ps] - 1
    res["labeled_recorded_before_maturity"] = not run(early_label)[1]["ok"]
    res["prediction_card_cutoff_after_decision"] = not run(late_cut)[0]["ok"]
    res["pending_recorded_after_maturity"] = not run(late_pending)[1]["ok"]
    res["outcome_before_prediction_set"] = not run(outcome_first)[1]["ok"]
    e = copy.deepcopy(next(iter(entries.values())))
    e["max_train_decision_time"] = float(e["training_cutoff"])
    res["registry_training_row_at_cutoff"] = R.training_after_cutoff(e) is not None
    res["all_caught"] = all(res.values())
    return res


def main() -> int:
    as_of = C.parse_utc(sys.argv[1])
    out = Path(sys.argv[2])
    sys.addaudithook(_hook)
    idx = M.load(AUD / "phase_19/monitoring/OUTCOME_LEDGER.jsonl")
    r1 = c1(as_of)
    seqs, pays = [e["seq"] for e in idx.entries], [e["payload"] for e in idx.entries]
    ver = M.verify(AUD / "phase_19/monitoring/OUTCOME_LEDGER.jsonl")
    r2, r3 = c2_c3(seqs, pays, ver)
    nc = negative_controls(seqs, pays, ver, R.read_entries(AUD / "phase_16/registry/entries"))
    r4 = c4()
    res = {"as_of_utc": sys.argv[1], "head": git("rev-parse", "HEAD").strip(), "C1_registry": r1, "C2_predictions": r2,
           "C3_outcomes": r3, "C4_git_order": r4, "negative_controls": nc, "network_events": len(SOCKETS)}
    res["ok"] = all(x["ok"] for x in (r1, r2, r3, r4)) and nc["all_caught"] and not SOCKETS
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"ok": res["ok"], "C1": r1["ok"], "C2": r2["ok"], "C3": r3["ok"], "C4": r4["ok"], "negative_controls_caught": nc["all_caught"]}))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
