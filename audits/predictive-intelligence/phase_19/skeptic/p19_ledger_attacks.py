"""Phase 19 skeptic: attacks on the outcome ledger (monitoring-1). Works on temporary copies only.

    python -B p19_ledger_attacks.py CLONE OUT.json

A1 CX-19 backdated PREDICTION after its outcome, through append and written around append.
A2 a PREDICTION number edited in place (no re-chain).
A3 a PREDICTION number edited and the whole chain re-sealed from that line (consistent rewrite).
A4 the OUTCOME tail truncated and re-appended through `append` with one label flipped (TARGET_FIRST -> INVALIDATION_FIRST).
A5 a final LABELED outcome "revised" through `append` with the SAME read (same response key and body sha), label flipped.
A6 a final LABELED outcome "revised" to VENDOR_OR_ROUTE_GAP (censored, no read at all), dropping it from scoring.
A7 a PENDING T2 outcome superseded NOW (before its maturity) by a censored VENDOR_OR_ROUTE_GAP.
A8 a PENDING outcome superseded by a LABELED one whose label_observed_at is claimed after maturity but recorded before it.
A9 a new PREDICTION_SET re-using a decision key with another mint (identity attack).
"""
import copy
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

clone = Path(sys.argv[1])
sys.path.insert(0, str(clone))
from memelab.predictive import monitoring as M  # noqa: E402
from memelab.predictive import labels as L  # noqa: E402

SRC = clone / "audits/predictive-intelligence/phase_19/monitoring/OUTCOME_LEDGER.jsonl"
tmpd = Path(tempfile.mkdtemp(prefix="p19_attack_"))
res = {}


def fresh(name):
    p = tmpd / name
    shutil.copyfile(SRC, p)
    return p


def entries(p):
    return M.read_ledger(p.read_text())


def try_append(p, payloads):
    try:
        r = M.append(p, payloads)
        return {"accepted": True, "appended": r["appended"]}
    except M.LedgerError as e:
        return {"accepted": False, "code": e.code}


def write_entries(p, ents):
    p.write_text("".join(M.canon(e) + "\n" for e in ents))


def reseal(payloads):
    out, prev = [], M.GENESIS
    for i, pl in enumerate(payloads):
        e = M.seal(pl, seq=i, prev=prev)
        out.append(e)
        prev = e["sha"]
    return out


base = entries(SRC)
pls = [e["payload"] for e in base]
idx = M.load(SRC)
cur = M.current_outcomes(idx)
lab = next(o for o in cur.values() if o["state"] == "LABELED" and o["label_class"] == "TARGET_FIRST")
pend = next(o for o in cur.values() if o["state"] == "PENDING")
pred = next(p for p in pls if p["kind"] == "PREDICTION" and p["decision_key"] == lab["decision_key"] and p["target"] == lab["target"])

# A1
p = fresh("a1.jsonl")
bd = dict(pred, prediction_id="pred_backdated_0001", candidate="P07_B2_BACKDATED", number=0.99, why=None)
bd["recorded_at"] = 1.0
res["A1_append"] = try_append(p, [bd])
ents = entries(p)
e = M.seal(bd, seq=len(ents), prev=ents[-1]["sha"])
p.write_text(p.read_text() + M.canon(e) + "\n")
v = M.verify(p)
res["A1_around_append_verify"] = {"ok": v["ok"], "problems": v["problems"][:1]}

# A2
p = fresh("a2.jsonl")
lines = p.read_text().splitlines()
i = next(i for i, l in enumerate(lines) if '"kind":"PREDICTION"' in l)
lines[i] = lines[i].replace('"number":', '"number":0.5,"x_":', 1) if False else lines[i]
e = json.loads(lines[i]); e["payload"]["number"] = 0.999 if e["payload"]["number"] != 0.999 else 0.5
lines[i] = M.canon(e)
p.write_text("\n".join(lines) + "\n")
v = M.verify(p)
res["A2_edit_in_place_verify"] = {"ok": v["ok"], "problems": v["problems"][:1]}

# A3 consistent rewrite of a prediction (chain re-sealed)
p = fresh("a3.jsonl")
pl3 = copy.deepcopy(pls)
j = next(i for i, x in enumerate(pl3) if x["kind"] == "PREDICTION" and x["number"] is not None)
pl3[j]["number"] = round(1 - pl3[j]["number"], 6)
write_entries(p, reseal(pl3))
v = M.verify(p)
res["A3_consistent_rewrite_verify"] = {"ok": v["ok"], "problems": v["problems"][:1], "head_changed": v.get("head") != base[-1]["sha"]}

# A4 truncate the tail and re-append through append with one label flipped
p = tmpd / "a4.jsonl"
first_out = next(i for i, x in enumerate(pls) if x["kind"] == "OUTCOME")
write_entries(p, base[:first_out])
tail = copy.deepcopy(pls[first_out:])
for x in tail:
    if x["kind"] == "OUTCOME" and x["outcome_id"] == lab["outcome_id"]:
        x["label"], x["label_class"], x["conservative_lens"] = 0, "INVALIDATION_FIRST", 0
r = try_append(p, tail)
v = M.verify(p)
res["A4_truncate_reappend"] = dict(r, verify_ok=v["ok"], entries=v["entries"],
                                   prefix_head_equal=entries(p)[first_out - 1]["sha"] == base[first_out - 1]["sha"],
                                   is_append_only_vs_committed=M.is_append_only(SRC.read_text(), p.read_text()))

# A5 revision through append with the same read, label flipped
p = fresh("a5.jsonl")
rev = {k: v for k, v in lab.items() if k != "outcome_id"}
rev.update(label=0, label_class="INVALIDATION_FIRST", conservative_lens=0, revision_of=lab["outcome_id"], revision_reason="LATER_READ",
           supersedes=None, recorded_at=time.time(), flags=[])
rev["outcome_id"] = "oc_" + M.sha({k: v for k, v in rev.items() if k != "recorded_at"})[:40]
res["A5_same_read_revision"] = try_append(p, [rev])
if res["A5_same_read_revision"]["accepted"]:
    c2 = M.current_outcomes(M.load(p))[(lab["decision_key"], lab["target"])]
    res["A5_same_read_revision"].update(current_label=c2["label"], flags=c2["flags"], verify_ok=M.verify(p)["ok"],
                                        same_response_key=c2["response_key"] == lab["response_key"])

# A6 revision to a censored state without any read
p = fresh("a6.jsonl")
rv = {k: v for k, v in lab.items() if k != "outcome_id"}
rv.update(state="VENDOR_OR_ROUTE_GAP", censored=1, label=None, label_class=None, label_observed_at=None, response_key=None,
          request_url=None, body_sha256=None, conservative_lens=0, revision_of=lab["outcome_id"], revision_reason="x", supersedes=None,
          recorded_at=time.time(), flags=[])
rv["outcome_id"] = "oc_" + M.sha({k: v for k, v in rv.items() if k != "recorded_at"})[:40]
res["A6_revise_to_censored_no_read"] = try_append(p, [rv])
if res["A6_revise_to_censored_no_read"]["accepted"]:
    i6 = M.load(p)
    asof = time.time()
    res["A6_revise_to_censored_no_read"]["still_scorable"] = any(o["outcome_id"] == lab["outcome_id"] or
                                                                (o["decision_key"], o["target"]) == (lab["decision_key"], lab["target"])
                                                                for o in M.scorable(i6, asof))

# A7 a PENDING superseded now (before maturity) by a censored state without a read
p = fresh("a7.jsonl")
sv = {k: v for k, v in pend.items() if k != "outcome_id"}
sv.update(state="VENDOR_OR_ROUTE_GAP", censored=1, conservative_lens=1, supersedes=pend["outcome_id"], revision_of=None,
          revision_reason=None, recorded_at=pend["recorded_at"] + 1, eligibility="VENDOR_OR_ROUTE_GAP", flags=[])
sv["outcome_id"] = "oc_" + M.sha({k: v for k, v in sv.items() if k != "recorded_at"})[:40]
res["A7_pending_censored_before_maturity"] = try_append(p, [sv])
res["A7_pending_censored_before_maturity"]["recorded_before_maturity"] = sv["recorded_at"] < pend["label_matures_at"]

# A8 PENDING -> LABELED with recorded_at before maturity
p = fresh("a8.jsonl")
lv = {k: v for k, v in pend.items() if k != "outcome_id"}
lv.update(state="LABELED", label=1, label_class="DRAWDOWN_50", conservative_lens=1, supersedes=pend["outcome_id"], revision_of=None,
          revision_reason=None, recorded_at=pend["label_matures_at"] - 10, label_observed_at=pend["label_matures_at"] + 10,
          response_key="k" * 64, request_url="https://x/?token=" + pend["mint"], body_sha256="0" * 64)
lv["outcome_id"] = "oc_" + M.sha({k: v for k, v in lv.items() if k != "recorded_at"})[:40]
res["A8_labeled_recorded_before_maturity"] = try_append(p, [lv])
lv2 = dict(lv, recorded_at=pend["label_matures_at"] + 20)
lv2["outcome_id"] = "oc_" + M.sha({k: v for k, v in lv2.items() if k != "recorded_at"})[:40]
res["A8b_labeled_claimed_times_after_maturity_fake_read"] = try_append(fresh("a8b.jsonl"), [lv2])

# A9 identity attack through a new prediction set
p = fresh("a9.jsonl")
ps = next(x for x in pls if x["kind"] == "PREDICTION_SET")
d0 = dict(ps["decisions"][0], mint="So11111111111111111111111111111111111111112")
res["A9_set_reuses_key_other_mint"] = try_append(p, [{"kind": "PREDICTION_SET", "set_id": "set_attack", "decisions": [d0], "sha256": "0" * 64}])

shutil.rmtree(tmpd)
Path(sys.argv[2]).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
print(json.dumps(res, indent=1, sort_keys=True))
