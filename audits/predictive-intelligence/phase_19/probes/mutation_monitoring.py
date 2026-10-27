"""Phase 19 mutation probe: each mutation of memelab/predictive/monitoring.py must make tests/test_predictive_monitoring.py fail.
Works on a temporary copy of the tracked memelab and tests trees plus the files the tests read (the checkout is never edited).
Since CP19-1 (PI-D-107) the list holds the independent skeptic's 14 mutations (K2 to K17) and 11 repair mutations (X1 to X11).
Each original fragment must occur exactly once. Writes a JSON report.

    python -B mutation_monitoring.py OUT.json [--only NAME_PREFIX ...]
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
MOD = "memelab/predictive/monitoring.py"
TEST = "tests/test_predictive_monitoring.py"
A = "audits/predictive-intelligence"
EXTRA_DIRS = [f"{A}/phase_07/artifacts", f"{A}/phase_09/artifacts", f"{A}/phase_19/probes", f"{A}/phase_12/probes", f"{A}/phase_07/probes",
              f"{A}/phase_10/probes", f"{A}/phase_11/probes", f"{A}/phase_17/probes"]

MUTATIONS = [
    # the chain
    ("L1 prev not checked", 'e["seq"] != i or e["prev"] != prev', 'e["seq"] != i'),
    ("L2 sha not recomputed", 'if sha(body) != e["sha"] or canon(e) != line.strip():', 'if False:'),
    ("L3 sequence not checked", 'e["seq"] != i or e["prev"] != prev', 'e["prev"] != prev'),
    ("L4 is_append_only ignores the prefix", '    return new_text.startswith(old_text)\n', '    return True\n'),
    # the append rules
    ("R1 edit of a prediction accepted", '            raise LedgerError("PREDICTION_EDIT_REFUSED", f"{pid[:16]} exists with other content (never rewritten)")',
     '            return "APPEND"'),
    ("R2 late prediction accepted (CX-19)", '        if idx.outcome_pairs.get(_pair(p)):\n            raise LedgerError("LATE_PREDICTION_REFUSED"',
     '        if False:\n            raise LedgerError("LATE_PREDICTION_REFUSED"'),
    ("R3 late prediction set accepted", '            if any(idx.outcome_pairs.get((d["decision_key"], t)) for t in L.TARGETS):',
     '            if False:'),
    ("R4 maturity of the read not checked", 'float(p["label_observed_at"]) < mat or float(p["recorded_at"]) < mat',
     'float(p["recorded_at"]) < mat'),
    ("R5 maturity of the record time not checked", 'float(p["label_observed_at"]) < mat or float(p["recorded_at"]) < mat',
     'float(p["label_observed_at"]) < mat'),
    ("R6 a pending outcome may carry a label", '        elif p["label"] is not None or p["label_class"] is not None:', '        elif False:'),
    ("R7 censored bit not checked", '        if int(p["censored"]) != cen:', '        if False:'),
    ("R8 outcome identity not checked", 'd["chain"] != p["chain"] or d["mint"] != p["mint"] or float(d["decision_time"]) != float(p["decision_time"]):\n            raise LedgerError("IDENTITY_MISMATCH", "chain, mint',
     'False:\n            raise LedgerError("IDENTITY_MISMATCH", "chain, mint'),
    ("R9 token parameter not checked", '            if "token=" + p["mint"] not in p["request_url"]:', '            if False:'),
    ("R10 final outcome replaced", '            if p["revision_of"] != cur["outcome_id"] or not p["revision_reason"] or p["supersedes"]:', '            if False:'),
    ("R11 pending superseded without naming it", '            if p["supersedes"] != cur["outcome_id"] or p["revision_of"]:', '            if False:'),
    ("R12 concurrent writer accepted", '    if expect_sha is not None and head_sha(entries) != expect_sha:', '    if False:'),
    ("R13 number range not checked", 'if p["number"] is not None and not (_fin(p["number"]) and 0.0 <= float(p["number"]) <= 1.0):', 'if False:'),
    ("R14 verify does not replay the rules", '            if check_payload(idx, e["payload"]) == "DUPLICATE":', '            if False:'),
    ("R15 outcome without prediction set", '            raise LedgerError("OUTCOME_WITHOUT_PREDICTION"', '            return "APPEND"\n            raise LedgerError("OUTCOME_WITHOUT_PREDICTION"'),
    # scoring
    ("S1 censored scored", 'if o["state"] != "LABELED" or int(o["censored"]) or o["label"] not in (0, 1):', 'if o["state"] != "LABELED" or o["label"] not in (0, 1):'),
    ("S2 unmatured scored", 'if mat > as_of or float(o["recorded_at"]) > as_of or float(o["label_observed_at"]) < mat:', 'if False:'),
    ("S3 revised flag dropped", '            cur["flags"] = sorted(set(cur.get("flags") or []) | {"REVISED"})', '            pass'),
    # prospective records
    ("P1 read before maturity classified", '                if rd.retrieved_at < rec["label_matures_at"]:\n                    rec["state"] = "PENDING"',
     '                if False:\n                    rec["state"] = "PENDING"'),
    ("P2 no pool counted as not read", '                    rec["state"] = "VENDOR_OR_ROUTE_GAP" if mature else "PENDING"', '                    rec["state"] = "NOT_READ" if mature else "PENDING"'),
    ("P3 unread matured counted as pending", '                    rec["state"] = "NOT_READ" if mature else "PENDING"', '                    rec["state"] = "PENDING"'),
    ("P4 supersede chain broken", '            out.append(outcome_payload(rec, recorded_at=recorded_at, supersedes=cur["outcome_id"], cite_read=True))',
     '            out.append(outcome_payload(rec, recorded_at=recorded_at, cite_read=True))'),
    # monitors
    ("D1 PSI alert threshold moved", 'st = "DRIFT_ALERT" if pr["psi"] >= PSI_ALERT else', 'st = "DRIFT_ALERT" if pr["psi"] >= 10 * PSI_ALERT else'),
    ("D1b missingness ignored", '        if cv and miss_r is not None and miss_c - miss_r > MISSING_SHARE_ALERT:', '        if False:'),
    ("D1c PSI floor removed", '    rs, cs = np.maximum(rs, floor), np.maximum(cs, floor)', '    rs, cs = rs + 1e-12, cs + 1e-12'),
    ("D1d unseen category dropped", '+ [float(np.mean(~np.isin(c, vals)))])', '+ [0.0])'),
    ("D2 Wilson check inverted", '    st = "OK" if lo <= train_prevalence <= hi else "DRIFT_ALERT"', '    st = "OK"'),
    ("D3 calibration failure ignored", '    ok = res["in_the_large_ok"] and res["every_bin_ok"] in (True, None)', '    ok = True'),
    ("D3b Page-Hinkley alarm dropped", '    return out | {"state": "DRIFT_ALERT" if al else "OK", "alarms": al}', '    return out | {"state": "OK", "alarms": al}'),
    ("D3c Page-Hinkley minimum ignored", '    if len(stream) < DRIFT["min_obs"]:', '    if False:'),
    ("D4 coverage alert removed", '"DRIFT_ALERT" if abs(a - b) > COVERAGE_DIFF_ALERT else "OK"', '"OK"'),
    ("D6 stale export not reported", '    if age is None or age > SOURCE_MAX_AGE_S:', '    if age is not None and age > 10 * SOURCE_MAX_AGE_S:'),
    ("D6b source problem reported as drift", '"state": "SOURCE_PROBLEM" if', '"state": "DRIFT_ALERT" if'),
    ("D7 regime alert removed", '"DRIFT_ALERT" if unseen > REGIME_UNSEEN_SHARE_ALERT else "OK"', '"OK"'),
    ("D8 model age never stale", '"state": "MODEL_STALE" if late or now > stale_at else "OK"}', '"state": "OK"}'),
    ("M1 constant prediction not flagged", '    if out["constant_prediction"]:\n        out["flags"].append("CONSTANT_PREDICTION")', '    if False:\n        out["flags"].append("CONSTANT_PREDICTION")'),
    # response and notices
    ("A1 drift on a champion kept", '    if pin_mode == "CHAMPION" and model_problem:', '    if False:'),
    ("A2 validated champion rolled back instead of demoted", '"DEGRADE_TO_SHADOW" if level == "VALIDATED_EXPERIMENTAL" else "ROLLBACK_TO_ABSTAIN"', '"ROLLBACK_TO_ABSTAIN"'),
    ("A3 source problem ignored", '    elif source_problem:\n        act = "KEEP_ABSTAIN_SOURCE"', '    elif False:\n        act = "KEEP_ABSTAIN_SOURCE"'),
    ("A4 trading word check off", '    if not plain_ok(txt):', '    if False:'),
    ("A5 automatic retrain flag", '"automatic_retrain": False,', '"automatic_retrain": True,'),
    ("A6 status codes not collected", '        for c in m.get("codes") or []:', '        for c in []:'),
    # the independent skeptic's own mutations (phase_19/skeptic/p19_own_mutations.py), adapted to the CP19-1 code where a line moved
    ("K2 current outcome is the first, not the newest", "        cur = dict(xs[-1])", "        cur = dict(xs[0])"),
    ("K3 scorable ignores the read time", ' or float(o["label_observed_at"]) < mat:\n            continue', ":\n            continue"),
    ("K4 scorable ignores the record time", 'if mat > as_of or float(o["recorded_at"]) > as_of or', "if mat > as_of or"),
    ("K5 D1 minimum 30 becomes 29", "        if cf.size < MIN_FEATURE_VALUES:", "        if cf.size < MIN_FEATURE_VALUES - 1:"),
    ("K6 champion without states abstains", '    elif pin_mode == "CHAMPION":\n        act = "NO_CHANGE"', '    elif pin_mode == "CHAMPION":\n        act = "KEEP_ABSTAIN"'),
    ("K7 D6 failure share at the threshold alerts", "if share is not None and share > READ_FAILURE_SHARE_ALERT:",
     "if share is not None and share >= READ_FAILURE_SHARE_ALERT:"),
    ("K8 a class change with the same state is not a revision",
     'same = (cur["state"] == rec["state"] and cur["label_class"] == (rec.get("label_class") if rec["state"] == "LABELED" else None))',
     'same = cur["state"] == rec["state"]'),
    ("K9 revision without a reason accepted", 'if p["revision_of"] != cur["outcome_id"] or not p["revision_reason"] or p["supersedes"]:',
     'if p["revision_of"] != cur["outcome_id"] or p["supersedes"]:'),
    ("K11 prediction identity not checked",
     'raise LedgerError("IDENTITY_MISMATCH", "decision key, chain, mint and time must equal the prediction set\'s (P01)")', 'pass'),
    ("K12 load accepts duplicate entries", '            raise LedgerError("DUPLICATE_ENTRY", f"seq {e[\'seq\']}")', "            pass"),
    ("K13 misses never flags an unmatured label", '            st = "NOT_MATURED_AT_EVALUATION"', "            pass"),
    ("K15 prediction set key reuse accepted", 'raise LedgerError("IDENTITY_MISMATCH", "a decision key reused with another identity")', "pass"),
    ("K16 PENDING outcomes treated as final", 'NON_FINAL = ("PENDING", "NOT_READ")', 'NON_FINAL = ("NOT_READ",)'),
    ("K17 Page-Hinkley stream not time ordered", "for t, v in sorted(stream, key=lambda tv: tv[0]) if", "for t, v in stream if"),
    # CP19-1 repair (PI-D-107)
    ("X1 revision may cite no read", '    if not (p.get("response_key") and p.get("body_sha256") and p.get("request_url") and _fin(p.get("label_observed_at"))):\n        raise LedgerError("REVISION_NEEDS_A_LATER_READ"',
     '    if False:\n        raise LedgerError("REVISION_NEEDS_A_LATER_READ"'),
    ("X2 revision may cite the read it replaces (CX-SK19)", '    if p["response_key"] == cur.get("response_key") or p["body_sha256"] == cur.get("body_sha256"):', '    if False:'),
    ("X3 revision may cite an earlier read", '    if float(p["label_observed_at"]) <= float(before):', '    if False:'),
    ("X4 revision read without token", '    if "token=" + p["mint"] not in p["request_url"]:\n        raise LedgerError("IDENTITY_MISMATCH", "the read must carry', '    if False:\n        raise LedgerError("IDENTITY_MISMATCH", "the read must carry'),
    ("X5 supersede never checks a read", '            if not no_read_ok:\n                _later_read(p, cur)', '            if False:\n                _later_read(p, cur)'),
    ("X6 unread gap allowed before maturity", 'and float(p["recorded_at"]) >= mat and not p["response_key"]', 'and not p["response_key"]'),
    ("X7 revision of a final outcome never checks a read", '                raise LedgerError("FINAL_OUTCOME_REPLACED", "a final outcome is revised only with revision_of and a reason")\n            _later_read(p, cur)',
     '                raise LedgerError("FINAL_OUTCOME_REPLACED", "a final outcome is revised only with revision_of and a reason")'),
    ("X8 next_outcomes does not cite the read on a revision", 'revision_reason=reason,\n                                       cite_read=True))', 'revision_reason=reason))'),
    ("X9 short boundary classified", '                elif rd.boundary < L.needed_boundary(t, d["decision_time"]):', '                elif False:'),
    ("X10 D1 overall ignores unmeasurable columns", '    elif "INSUFFICIENT_DATA" in sts or not sts:', '    elif not sts:'),
    ("X11 champion below the support minimum unchanged", '    elif "SUPPORT_BELOW_MINIMUM" in s:\n        act = "KEEP_ABSTAIN"', '    elif False:\n        act = "KEEP_ABSTAIN"'),
]


def main(out: str, only: list[str] | None = None) -> int:
    src = (REPO / MOD).read_text()
    muts = [(m[0], [(m[1], m[2])]) for m in MUTATIONS]
    muts = [m for m in muts if not only or any(m[0].startswith(o) for o in only)]
    for name, pairs in muts:
        for a, b in pairs:
            if src.count(a) != 1:
                raise SystemExit(f"{name}: fragment occurs {src.count(a)} times")
    results = []
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="p19_mut_") as td:
        root = Path(td)
        for d in ("memelab", "tests"):
            shutil.copytree(REPO / d, root / d, ignore=shutil.ignore_patterns("__pycache__"))
        for d in EXTRA_DIRS:
            shutil.copytree(REPO / d, root / d, ignore=shutil.ignore_patterns("__pycache__"))
        cmd = [sys.executable, "-B", "-m", "pytest", TEST, "-q", "-x", "-p", "no:cacheprovider"]
        base = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        if base.returncode != 0:
            raise SystemExit("baseline fails: " + base.stdout[-3000:])
        for name, pairs in muts:
            mutated = src
            for a, b in pairs:
                mutated = mutated.replace(a, b)
            (root / MOD).write_text(mutated)
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=900)
            failed = [ln.split(" ")[1] for ln in r.stdout.splitlines() if ln.startswith("FAILED") or ln.startswith("ERROR")]
            results.append({"mutation": name, "caught": r.returncode != 0,
                            "first_failure": failed[0] if failed else (r.stdout.strip().splitlines() or [""])[-1]})
            (root / MOD).write_text(src)
    rep = {"module": MOD, "tests": TEST, "mutations": len(results), "caught": sum(r["caught"] for r in results),
           "survivors": [r["mutation"] for r in results if not r["caught"]], "results": results, "wall_s": round(time.time() - t0, 1)}
    Path(out).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("mutations", "caught", "survivors", "wall_s")}))
    return 0 if not rep["survivors"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[3:] if len(sys.argv) > 2 and sys.argv[2] == "--only" else None))
