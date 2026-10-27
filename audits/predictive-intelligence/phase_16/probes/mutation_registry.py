"""Phase 16 mutation probe: each mutation of memelab/predictive/registry.py must make tests/test_predictive_registry.py fail.
Works on a temporary copy of the tracked memelab and tests trees plus the committed artifacts the tests read (the checkout is
never edited), so it runs at HEAD. Each original fragment must occur exactly once. Writes a JSON report.

    python -B mutation_registry.py OUT.json
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
MP = "memelab/predictive/registry.py"
TEST = "tests/test_predictive_registry.py"
A = "audits/predictive-intelligence"
EXTRA_DIRS = [f"{A}/phase_07/artifacts/T1_24h", f"{A}/phase_09/artifacts/T1_24h", f"{A}/phase_10/artifacts/T1_24h",
              f"{A}/phase_13/artifacts/T1_24h", f"{A}/phase_13/artifacts/T2_24h"]

MUTATIONS = [
    # promotion (rule 3)
    ("P1 SHADOW bss bound strict", 'float(ret["bss"]) >= ACC["promotion"]["SHADOW"]["bss_point_min"]', 'float(ret["bss"]) > ACC["promotion"]["SHADOW"]["bss_point_min"]'),
    ("P2 prospective calibration not required", '        reasons.append("NO_ADMISSIBLE_PROSPECTIVE_CALIBRATION")', "        pass"),
    ("P3 evidence source unchecked", '            and cal.get("evidence_source") == "PROSPECTIVE_HOLDOUT"):', "            ):"),
    ("P4 post-opening may promote", '    if ret.get("evaluation") != FIRST_OPENING:', '    if ret.get("evaluation") not in (FIRST_OPENING, "POST_OPENING"):'),
    ("P5 retrospective counts unchecked", '            reasons.append("RETROSPECTIVE_BELOW_MINIMUM")', "            pass"),
    ("P6 failed bins ignored", 'calibration_every_bin_ok") in (True, None))', 'calibration_every_bin_ok") in (True, None, False))'),
    ("P7 selection correction ignored", '            ve_reasons.append("SELECTION_CORRECTION_NOT_SURVIVED")', "            pass"),
    ("P8 B2 comparison skipped", '        if facts.get("kind") != "B2":', "        if False:"),
    ("P9 prospective bound unchecked", '            ve_reasons.append("PROSPECTIVE_LOWER_BOUND_NOT_ABOVE_0")', "            pass"),
    ("P10 candidates abstain instead of no-go", '    elif role == "REFERENCE_BASELINE":\n        level = "ABSTAIN"', '    elif True:\n        level = "ABSTAIN"'),
    ("P11 post-opening failure ignored", '        reasons.append("POST_OPENING_FAILS")', "        pass"),
    ("P12 training counts unchecked", '        reasons.append("TRAINING_BELOW_MINIMUM")', "        pass"),
    ("P13 test flags unchecked", '        reasons.append("TESTS_NOT_PASSED")', "        pass"),
    ("P14 behavioral facts accepted", '    if facts.get("source") != SOURCE or _behavioral(facts.get("kind"), facts.get("model_id")):', "    if False:"),
    ("P15 retrospective bound unchecked", '            ve_reasons.append("RETROSPECTIVE_LOWER_BOUND_NOT_ABOVE_0")', "            pass"),
    ("P16 alpha not exact", 'ALPHA = round(1 - ACC["bootstrap"]["conf"], 12)', 'ALPHA = 1 - ACC["bootstrap"]["conf"]'),
    # entries (rule 4)
    ("E1 level not recomputed", '    if promo != entry["promotion"]:', "    if False:"),
    ("E2 entry id not checked", '    if entry["entry_id"] != want:', "    if False:"),
    ("E3 card content unchecked", '        if card.get("model_sha") != entry["model_sha"] or card_sha_of(card) != entry["model_sha"]:', '        if card.get("model_sha") != entry["model_sha"]:'),
    ("E4 card bytes unchecked", '    if card_bytes is not None and sha_bytes(card_bytes) != entry["card_file_sha256"]:', "    if False:"),
    ("E5 calibration card hash unchecked", '        if cal_card.get("card_sha") != sha({k: v for k, v in cal_card.items() if k != "card_sha"}) or \\', "        if False or \\"),
    ("E6 overwrite allowed", '    if p.exists() and p.read_text() != text:', "    if False:"),
    ("E7 file name unchecked", '        if p.stem != e["entry_id"]:', "        if False:"),
    ("E8 publishable ignores calibration", 'in PUBLISHABLE_LEVELS and cal.get("status") == CALIBRATED and', "in PUBLISHABLE_LEVELS and True and"),
    ("E9 publishable flag unchecked", '    if entry["registry_status"] != registry_status(promo["level"], entry["role"]) or entry["publishable"] != publishable(entry):', "    if False:"),
    ("E10 behavioral entry accepted", '    if entry["source"] != SOURCE or _behavioral(entry["family"].get("kind"), entry["model_id"], entry["family"].get("candidate")):', "    if False:"),
    ("E11 facts kind unchecked", '    if facts.get("role") != role or facts.get("kind") != kind:', "    if False:"),
    # inference (rule 7, P38)
    ("I1 no number and no reason", "            if not why:\n                raise MalformedScore", "            if False:\n                raise MalformedScore"),
    ("I2 range unchecked", "        if not 0.0 <= float(num) <= 1.0:", "        if False:"),
    ("I3 duplicates allowed", "    if len(set(keys)) != len(keys):", "    if False:"),
    ("I4 inference compare skipped", "    if got != want:\n        raise InferenceMismatchError", "    if False:\n        raise InferenceMismatchError"),
    ("I5 non-finite accepted", "        if isinstance(num, bool) or not isinstance(num, (int, float, np.floating)) or not math.isfinite(float(num)):", "        if False:"),
    # compatibility (rule 6)
    ("C1 runtime feature set unchecked", '    if fs != entry["feature_set_sha"]:', "    if False:"),
    ("C2 feature version unchecked", '    if runtime.get("feature_version") != entry["feature_version"]:', "    if False:"),
    ("C3 request feature set unchecked", '        if request.get("feature_set_sha") != entry["feature_set_sha"]:', "        if False:"),
    ("C4 registry fingerprint unchecked", '    if runtime.get("registry_sha") != entry["target_registry_sha"]:', "    if False:"),
    ("C5 labels version unchecked", '    if runtime.get("labels_version") != entry["labels_version"]:', "    if False:"),
    # staleness (rule 8)
    ("S1 stale at the edge", '    elif T - cut > float(ACC["max_model_age_s"]):', '    elif T - cut >= float(ACC["max_model_age_s"]):'),
    ("S2 later alarms counted", "    hits = [float(a) for a in drift_alarms if float(a) <= T]", "    hits = [float(a) for a in drift_alarms if True]"),
    ("S3 earlier decision accepted", "    if T < cut:\n        out.append({\"state\": NOT_AVAILABLE_AS_OF", "    if False:\n        out.append({\"state\": NOT_AVAILABLE_AS_OF"),
    # log (rule 5)
    ("L1 chain not checked", '        if ev.get("seq") != i or ev.get("prev") != prev or ev.get("event_id") != _event_id(ev):', '        if ev.get("seq") != i:'),
    ("L2 canonical form unchecked", "        if canon(ev) != line:", "        if False:"),
    ("L3 time order unchecked", "        if t < last_t:", "        if False:"),
    ("L4 append ignores a changed file", "    if file_sha(p) != expect_sha:", "    if False:"),
    ("L5 partial write accepted", '    if text and not text.endswith("\\n"):', "    if False:"),
    ("L6 unknown event kind accepted", '        if p.get("kind") not in EVENT_KINDS:', "        if False:"),
    # pins, resolve, rollback, serve (rules 5, 9)
    ("R1 resolve ignores time", 'ev["target"] == target and C.parse_utc(ev["as_of_utc"]) <= T:', 'ev["target"] == target:'),
    ("R2 resolve accepts a low champion", '    if cur["mode"] == "CHAMPION" and entries[cur["champion"]]["promotion"]["level"] not in PUBLISHABLE_LEVELS:', "    if False:"),
    ("R3 pin accepts any level", '        if e["promotion"]["level"] not in PUBLISHABLE_LEVELS:\n            raise PinRefused(f"champion level', '        if False:\n            raise PinRefused(f"champion level'),
    ("R4 pin accepts a fixture champion", '        if e["is_fixture"] and not allow_fixture:', "        if False:"),
    ("R5 references unchecked", '        if e["target"] != target or e["role"] != "REFERENCE_BASELINE" or REFERENCE_NAMES.get(e["family"]["kind"]) != name:', "        if False:"),
    ("R6 rollback reuses the failed champion", '    bad = {now["champion"]} if now["champion"] else set()', "    bad = set()"),
    ("R7 rollback ignores usability", '        if ev["mode"] == "CHAMPION" and c and c not in bad and usable(entries[c]):', '        if ev["mode"] == "CHAMPION" and c and c not in bad:'),
    ("R8 unknown entries accepted", '        if eid is not None and eid not in entries:', "        if False:"),
    ("R9 fixture references accepted", '        if entries[eid]["is_fixture"] and not allow_fixture:', "        if False:"),
    ("V1 serve ignores status", '        blocking += [s for s in status_at(e, decision_time, drift_alarms=drift_alarms) if s["state"] != MODEL_NOT_PROMOTED]', "        pass"),
    ("V2 serve ignores compatibility", "        blocking += compatibility(e, runtime=runtime, request=request)", "        pass"),
    ("V3 serve ignores inference", '                if got != res["champion_inference_sha"]:', "                if False:"),
    # champion restatement (rule 2)
    ("H1 holdout rows accepted", "        if any(m in txt for m in HOLDOUT_MARKERS):", "        if False:"),
    # ensembles (rule 12)
    ("N1 shared sources accepted", "            if s in seen:\n                raise DoubleCountedEvidence", "            if False:\n                raise DoubleCountedEvidence"),
    ("N2 in-sample row accepted", "        if T < cut:\n            raise NotOutOfFold", "        if False:\n            raise NotOutOfFold"),
    ("N3 fold disagreement accepted", "        if len(cuts) != 1 or len(ys) != 1:", "        if len(ys) != 1:"),
    ("N4 stack overlap allowed", '        if r["decision_key"] in ek:\n            raise InSampleStacking', '        if False:\n            raise InSampleStacking'),
    ("N5 stack chronology unchecked", '        if not (float(r["decision_time"]) < cut and float(r["label_matures_at"]) <= cut):', "        if False:"),
    ("N6 stack gate days ignored", '    if days < STACK_GATE["min_days"]:', "    if False:"),
    ("N7 fit_stack ignores the gate", "    g = stack_gate(fit_rows)\n    if g:", "    g = []\n    if g:"),
    ("N8 ensemble decision ignores the correction", 'and r.get("selection_status") == SELECTION_SURVIVES and r.get("level_possible") in PUBLISHABLE_LEVELS]', "]"),
    ("N9 behavioral member accepted", "        if _behavioral(name):", "        if False:"),
    ("N10 single member accepted", "    if len(members) < 2:", "    if False:"),
    # target plan and reference records (rules 11, 2)
    ("T1 deferred targets attempted", '        if reg["status"] != "PRIMARY":', "        if False:"),
    ("T2 chain unchecked", '        elif opportunity.get("chain") != reg.get("scope_chain", "solana"):', "        elif False:"),
    ("F1 reference record published", '"published": False,\n           "purpose"', '"published": True,\n           "purpose"'),
    ("F2 candidates scored as references", '    if entry["role"] != "REFERENCE_BASELINE":\n        raise RegistryError("only a reference', '    if False:\n        raise RegistryError("only a reference'),
]


def main(out: str) -> int:
    src = (REPO / MP).read_text()
    for name, a, b in MUTATIONS:
        if src.count(a) != 1:
            raise SystemExit(f"{name}: fragment occurs {src.count(a)} times")
    results = []
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="p16_mut_") as td:
        root = Path(td)
        for d in ("memelab", "tests"):
            shutil.copytree(REPO / d, root / d, ignore=shutil.ignore_patterns("__pycache__"))
        for d in EXTRA_DIRS:
            shutil.copytree(REPO / d, root / d)
        cmd = [sys.executable, "-B", "-m", "pytest", TEST, "-q", "-x", "-p", "no:cacheprovider"]
        base = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        if base.returncode != 0:
            raise SystemExit("baseline fails: " + base.stdout[-2000:])
        for name, a, b in MUTATIONS:
            (root / MP).write_text(src.replace(a, b))
            r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=900)
            failed = [ln.split(" ")[1] for ln in r.stdout.splitlines() if ln.startswith("FAILED")]
            results.append({"mutation": name, "caught": r.returncode != 0,
                            "first_failure": failed[0] if failed else (r.stdout.strip().splitlines() or [""])[-1]})
        (root / MP).write_text(src)
    rep = {"module": MP, "tests": TEST, "mutations": len(results), "caught": sum(r["caught"] for r in results),
           "survivors": [r["mutation"] for r in results if not r["caught"]], "results": results, "wall_s": round(time.time() - t0, 1)}
    Path(out).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("mutations", "caught", "survivors", "wall_s")}))
    return 0 if not rep["survivors"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
