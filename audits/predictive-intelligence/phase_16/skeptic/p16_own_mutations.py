"""Phase 16 skeptic: new mutations of memelab/predictive/registry.py, each run against the two Phase 16 test files in a
throwaway full copy of the repository. Usage: python -B p16_own_mutations.py <throwaway repo copy> <out.json>"""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(sys.argv[1]); OUT = Path(sys.argv[2]); MP = ROOT / "memelab/predictive/registry.py"
M = [
 ("S1 stale at the edge", 'elif T - cut > float(ACC["max_model_age_s"]):', 'elif T - cut >= float(ACC["max_model_age_s"]) + 3600:'),
 ("S2 serve ignores staleness", '[s for s in status_at(e, decision_time, drift_alarms=drift_alarms) if s["state"] != MODEL_NOT_PROMOTED]', '[s for s in status_at(e, decision_time, drift_alarms=drift_alarms) if s["state"] not in (MODEL_NOT_PROMOTED, MODEL_STALE)]'),
 ("S3 drift alarm after the decision counts only", 'hits = [float(a) for a in drift_alarms if float(a) <= T]', 'hits = [float(a) for a in drift_alarms if float(a) < T - 86400]'),
 ("R1 range up to 1.5", 'if not 0.0 <= float(num) <= 1.0:', 'if not 0.0 <= float(num) <= 1.5:'),
 ("R2 duplicate decisions allowed", '    if len(set(keys)) != len(keys):\n        raise MalformedScore', '    if False:\n        raise MalformedScore'),
 ("L1 resolve uses a later pin", 'and C.parse_utc(ev["as_of_utc"]) <= T:\n            cur = ev', 'and C.parse_utc(ev["as_of_utc"]) <= T + 86400:\n            cur = ev'),
 ("L2 log time order unchecked", '        if t < last_t:\n            raise LogError', '        if False:\n            raise LogError'),
 ("L3 append ignores expect_sha", '    if file_sha(p) != expect_sha:\n        raise LogError', '    if False:\n        raise LogError'),
 ("L4 resolve ignores champion level", '    if cur["mode"] == "CHAMPION" and entries[cur["champion"]]["promotion"]["level"] not in PUBLISHABLE_LEVELS:', '    if False:'),
 ("C1 labels version unchecked", '    if runtime.get("labels_version") != entry["labels_version"]:', '    if False:'),
 ("C2 family version unchecked", '    if (runtime.get("family_version") or {}).get(ph) != entry["family_version"]:', '    if False:'),
 ("C3 request feature version unchecked", '        if request.get("feature_version") is not None and request.get("feature_version") != entry["feature_version"]:', '        if False:'),
 ("E1 verify_entry skips card feature set", '("feature_set_sha", "feature_set_sha"), ("training_cutoff_utc", "training_cutoff_utc"),', '("training_cutoff_utc", "training_cutoff_utc"),'),
 ("E2 publishable ignores the card level", ' and \\\n        cal.get("level") == entry["promotion"]["level"]', ''),
 ("E3 per-class count one-sided", 'return n >= min_n and k >= min_k and n - k >= min_k', 'return n >= min_n and k >= min_k'),
 ("E4 every-bin missing passes even above 40", 'calibration_every_bin_ok": None if m_b0["cal_every_bin_ok"] == "" else m_b0["cal_every_bin_ok"] == "1"', 'calibration_every_bin_ok": None if m_b0["cal_every_bin_ok"] in ("", "0") else m_b0["cal_every_bin_ok"] == "1"'),
 ("E5 pin_event accepts fixtures", '        if e["is_fixture"] and not allow_fixture:\n            raise PinRefused("a fixture entry is never pinned', '        if False:\n            raise PinRefused("a fixture entry is never pinned'),
 ("E6 references of another target", '        if e["target"] != target or e["role"] != "REFERENCE_BASELINE"', '        if e["role"] != "REFERENCE_BASELINE"'),
 ("E7 rollback forgets earlier rollbacks", '        if ev["kind"] == "ROLLBACK" and ev.get("from"):\n            bad.add(ev["from"])', '        if False:\n            bad.add(ev["from"])'),
 ("O1 out-of-fold allows a day in sample", '        if T < cut:\n            raise NotOutOfFold', '        if T < cut - 86400:\n            raise NotOutOfFold'),
 ("O2 stack fit rows need not be matured", 'if not (float(r["decision_time"]) < cut and float(r["label_matures_at"]) <= cut):', 'if not (float(r["decision_time"]) < cut):'),
 ("O3 undeclared columns pass", '        if c not in EVIDENCE_SOURCES:\n            raise UndeclaredColumn', '        if c not in EVIDENCE_SOURCES:\n            continue\n            raise UndeclaredColumn'),
 ("O4 agent marker dropped", '"agent", "behavioral", "persona", "swarm")', '"behavioral", "persona", "swarm")'),
 ("H1 champion rule takes holdout rows", '        if any(m in txt for m in HOLDOUT_MARKERS):', '        if False:'),
 ("H2 stack gate days", '    if days < STACK_GATE["min_days"]:', '    if days < 1:'),
 ("F1 VE retrospective Holm unchecked", 'and _fin(ret.get("p_holm"))\n                and float(ret["p_holm"]) < ALPHA):', '):'),
]
src = MP.read_text(); res = []
cmd = [sys.executable, "-B", "-m", "pytest", "tests/test_predictive_registry.py", "tests/test_predictive_phase16_outputs.py", "-q", "-x", "-p", "no:cacheprovider"]
base = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True); assert base.returncode == 0, base.stdout[-1500:]
try:
    for name, a, b in M:
        n = src.count(a)
        if n != 1:
            res.append({"mutation": name, "error": f"fragment occurs {n} times"}); continue
        MP.write_text(src.replace(a, b))
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=900)
        failed = [ln.split(" ")[1] for ln in r.stdout.splitlines() if ln.startswith("FAILED")]
        res.append({"mutation": name, "caught": r.returncode != 0, "first_failure": failed[0] if failed else r.stdout.strip().splitlines()[-1]})
finally:
    MP.write_text(src)
rep = {"mutations": len(res), "caught": sum(1 for r in res if r.get("caught")), "survivors": [r["mutation"] for r in res if r.get("caught") is False],
       "errors": [r for r in res if "error" in r], "results": res}
OUT.write_text(json.dumps(rep, indent=1)); print(json.dumps({k: rep[k] for k in ("mutations", "caught", "survivors", "errors")}, indent=1))
