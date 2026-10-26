"""Phase 14 mutation probe: each mutation of memelab/predictive/behavioral.py must make tests/test_predictive_behavioral.py fail.

Works on a temporary copy of the tracked memelab and tests trees plus the files the tests read (the checkout is never edited),
so it runs at HEAD. Each original fragment must occur exactly once. Writes a JSON report.

    python -B mutation_behavioral.py OUT.json
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
BP = "memelab/predictive/behavioral.py"
TEST = "tests/test_predictive_behavioral.py"
EXTRA = ["audits/predictive-intelligence/phase_14/behavioral/SCENARIO_SCHEMA.json",
         "audits/predictive-intelligence/phase_14/probes/seed_convert.py",
         "audits/predictive-intelligence/phase_13/calibration/FORECAST_RESULTS_DEV.jsonl"]

MUTATIONS = [
    # seed checks (P28, P41)
    ("S1 post-decision observation accepted", '            if C.parse_utc(o.get("available_at_utc")) > T:', '            if C.parse_utc(o.get("available_at_utc")) > T + 3600:'),
    ("S2 missing time accepted", '        except C.ContractError:\n            errs.add("OBSERVATION_TIME_MISSING")', '        except C.ContractError:\n            pass'),
    ("S3 unsourced observation accepted", '        if not isinstance(sr, str) or not sr.strip():', "        if not isinstance(sr, str):"),
    ("S4 observation sha not checked", '        if want is None or o.get("content_sha256") != want or', '        if want is None or False or'),
    ("S5 outcome key accepted", '        if k is not None and OUTCOME_KEY.search(str(k)):\n            errs.add("POST_DECISION_FIELD")',
     '        if False:\n            errs.add("POST_DECISION_FIELD")'),
    ("S6 outcome name accepted", '        if isinstance(o.get("name"), str) and OUTCOME_KEY.search(o["name"]):', "        if False:"),
    ("S7 post-decision date accepted", '        if _dates_after(s, T):', "        if False:"),
    ("S8 bare later date accepted", '            if f"{y}-{mo}-{d}" > day_cut:', '            if f"{y}-{mo}-{d}" > "2099-12-31":'),
    ("S9 unix time ignored", '        if float(m.group(1)) > cutoff:', "        if False:"),
    ("S10 injection accepted in seeds", '        if INJECTION.search(s):\n            errs.add("PROMPT_INJECTION_SUSPECTED")',
     '        if False:\n            errs.add("PROMPT_INJECTION_SUSPECTED")'),
    ("S11 behavioral feedback accepted", '            errs.add("BEHAVIORAL_FEEDBACK")\n    for _, k, v', "            pass\n    for _, k, v"),
    ("S12 observation cap off", "    if len(obs) > MAX_OBSERVATIONS:", "    if len(obs) > 10 * MAX_OBSERVATIONS:"),
    ("S13 mint not verified", '    if not C._address_ok(seed.get("chain"), seed.get("mint_address")):\n        errs.add("MINT_NOT_VERIFIED")',
     '    if False:\n        errs.add("MINT_NOT_VERIFIED")'),
    ("S14 seed sha not checked", "    if not seed_sha_ok(seed):", "    if False:"),
    ("S15 catalyst state unchecked", '        if o.get("kind") == CATALYST_EVENT and o.get("state") not in CATALYST_STATES:', "        if False:"),
    ("S16 url allowed", r"|https?://|\bwww\.", r"|\bwww\."),
    # response coding (P27, P41, P45, identity)
    ("R1 probability key accepted", '        if k is not None and PROB_LIKE.search(str(k)):\n            raise ResponseRefused("RESPONSE_REFUSED_PROBABILITY"',
     '        if False:\n            raise ResponseRefused("RESPONSE_REFUSED_PROBABILITY"'),
    ("R2 fractions accepted", "        if isinstance(v, float) or (isinstance(v, (int, float))", "        if False and (isinstance(v, (int, float))"),
    ("R3 injection accepted in responses", "        if INJECTION.search(s) or KIND in s:", "        if KIND in s:"),
    ("R4 digits allowed in codes", 'CODE = re.compile(r"^[A-Z][A-Z_]*[A-Z]$")', 'CODE = re.compile(r"^[A-Z0-9_]+$")'),
    ("R5 codes outside vocabulary accepted", " or not CODE.fullmatch(cd) or cd not in ASSUMPTION_CODES[kd]:", " or not CODE.fullmatch(cd):"),
    ("R6 ungrounded catalyst accepted", "            if not grounded:\n", "            if False:\n"),
    ("R7 refs outside the seed accepted", '        if any(r not in ids for r in refs):\n            raise ResponseRefused("UNGROUNDED_HYPOTHESIS"',
     '        if False:\n            raise ResponseRefused("UNGROUNDED_HYPOTHESIS"'),
    ("R8 wallet claims not counted", '            refused[c["kind"]] += 1', "            pass"),
    ("R9 llm_actions bool accepted", "    return type(x) is int and x >= 0", "    return isinstance(x, int) and x >= 0"),
    ("R10 named assumptions not required", '            if not asms:\n                raise ResponseRefused("BAD_RESPONSE", "a hypothesis needs named assumptions")',
     '            if False:\n                raise ResponseRefused("BAD_RESPONSE", "a hypothesis needs named assumptions")'),
    ("R11 silent run accepted", "            elif llm_actions <= 0:", "            elif llm_actions < 0:"),
    ("R12 meter cap ignored", '            if coded["meter"] and coded["meter"]["cap_reached"]:', "            if False:"),
    # document validator (P27, P26)
    ("V1 floats anywhere", '        return path in _FLOAT_PATHS and math.isfinite(v) and v >= 0', "        return True"),
    ("V2 prob-like key in documents", '            errs.append(f"probability-like key at {path}: simulated agreement is not a likelihood (P27)")', "            pass"),
    ("V3 fiction not required", '    if doc["fictional"] is not True or doc["fiction_notice"] != FICTION_NOTICE:', '    if doc["fictional"] is None:'),
    ("V4 contamination not recomputed", '    if doc["contamination_flags"] != contamination(eng, sub.get("decision_time_utc")):', "    if False:"),
    ("V5 p26 late cutoff accepted", "        late = cut is None or cut == NOT_APPLICABLE or C.parse_utc(cut) > C.parse_utc(decision_time_utc)",
     "        late = cut is None"),
    ("V6 doc sha unchecked", '    if doc["doc_sha256"] != _try_sha(', '    if False and doc["doc_sha256"] != _try_sha('),
    # stability (P29)
    ("T1 majority counts as stable", "        status = STABLE if (len(sets) == 1 and rep_same) else UNSTABLE", "        status = STABLE if len(sets) <= 2 else UNSTABLE"),
    ("T2 repeat ignored", "        status = STABLE if (len(sets) == 1 and rep_same) else UNSTABLE", "        status = STABLE if len(sets) == 1 else UNSTABLE"),
    ("T3 short grid assessed", "    complete = set(grid) == want and", "    complete = set(grid) <= want and"),
    ("T4 source grounding ignored", '    if "NOT_SOURCE_GROUNDED" in flags and status == STABLE:', "    if False:"),
    # gates, egress, cost (P30, P48)
    ("G1 approval truthy", '    if b.get("approved") is not True:\n        return NOT_AVAILABLE, ["NOT_APPROVED"], {}',
     '    if not b.get("approved"):\n        return NOT_AVAILABLE, ["NOT_APPROVED"], {}'),
    ("G2 kill switch ignored", '    if b.get("kill_switch") is True:', "    if False:"),
    ("G3 any mode", '    if b.get("mode") != ON_DEMAND_LOCAL:', "    if False:"),
    ("G4 host names allowed", '    if u.netloc not in (f"127.0.0.1:{port}", f"[::1]:{port}"):\n        return None', "    if False:\n        return None"),
    ("G5 paid engine allowed", '    if engine.get("paid") is not False:', '    if engine.get("paid") is True:'),
    ("G6 worst case not checked", "    ok = worst <= cap", "    ok = True"),
    ("G7 worst case undercounted", "    return agents * rounds + agents + 2", "    return agents"),
    ("G8 meter charges past cap", "                if self.charged + charge > self.cap:", "                if self.charged > self.cap:"),
    ("G9 max_tokens not forced", "                mt = min(int(mt), self.max_tokens) if", "                mt = int(mt) if"),
    ("G10 meter breaker off", "            elif self.failures >= self.breaker:", "            elif False:"),
    ("G11 meter call cap off", "            elif self.forwarded >= self.max_calls:", "            elif False:"),
    ("G12 prompt cap off", "            elif chars > self.max_prompt_chars or len(raw) > MAX_CALL_BODY_BYTES:", "            elif False:"),
    ("G12b body cap off", " or len(raw) > MAX_CALL_BODY_BYTES:", ":"),
    ("G19 charge on characters / 4", "    tokens_in = b + TOKEN_OVERHEAD", "    tokens_in = b // 4"),
    ("G20 usage above charge ignored", "            if last is not None and used > last[\"charged_microusd\"]:", "            if False:"),
    ("G21 external engine as a loopback service", '        if self.engine.get("mode") == EXTERNAL_SIMULATOR:      # an engine', '        if False:      # an engine'),
    ("G13 key-like env allowed", "            if SECRET_ENV.search(k) and v != MOCK_KEY:\n                return", "            if False:\n                return"),
    ("G14 parent environment inherited", '        env = {"PATH": "/usr/bin:/bin", "HOME": home, "LANG": "C.UTF-8", "PYTHONHASHSEED": "0"}',
     '        env = {**os.environ, "PATH": "/usr/bin:/bin", "HOME": home, "LANG": "C.UTF-8", "PYTHONHASHSEED": "0"}'),
    ("G15 401 not named", "        if r.status in (401, 403):", "        if r.status in (403,):"),
    ("G16 retries on key errors", '            if reason not in ("SERVICE_DOWN", "TIMEOUT", "SERVICE_ERROR"):', '            if reason not in ("SERVICE_DOWN", "TIMEOUT", "SERVICE_ERROR", "KEY_MISSING"):'),
    ("G17 netns not required", '        if self.engine.get("mode") == EXTERNAL_SIMULATOR and not self.netns:', "        if False:"),
    ("G18 cost setting nan accepted", "    if not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) or x < 0:",
     "    if not isinstance(x, (int, float)) or isinstance(x, bool):"),
    # rules
    ("U1 rule R5 dropped", '    if v("sc_attention_suspect") == 1:', '    if v("sc_attention_suspect") == 2:'),
    ("U2 missing fires R3", '    elif v("sc_attention_trend_ord") == 0 and v("sc_lifecycle_late") == 1:', '    elif v("sc_attention_trend_ord") in (0, None):'),
    ("U3 projection carries a count", '            "stability": doc["stability"]["status"], "engine_mode"', '            "stability": doc["stability"]["status"], "runs": doc["stability"].get("runs", 0), "engine_mode"'),
]


def main(out: str) -> int:
    src = (REPO / BP).read_text()
    for name, a, b in MUTATIONS:
        if src.count(a) != 1:
            raise SystemExit(f"{name}: fragment occurs {src.count(a)} times")
    results = []
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="p14_mut_") as td:
        root = Path(td)
        for d in ("memelab", "tests"):
            shutil.copytree(REPO / d, root / d, ignore=shutil.ignore_patterns("__pycache__"))
        for f in EXTRA:
            (root / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / f, root / f)
        base = subprocess.run([sys.executable, "-B", "-m", "pytest", TEST, "-q", "-x", "-p", "no:cacheprovider"], cwd=root,
                              capture_output=True, text=True)
        if base.returncode != 0:
            raise SystemExit("baseline fails: " + base.stdout[-2000:])
        for name, a, b in MUTATIONS:
            (root / BP).write_text(src.replace(a, b))
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", TEST, "-q", "-x", "-p", "no:cacheprovider"], cwd=root,
                               capture_output=True, text=True, timeout=900)
            failed = [ln.split(" ")[1] for ln in r.stdout.splitlines() if ln.startswith("FAILED")]
            results.append({"mutation": name, "caught": r.returncode != 0, "first_failure": failed[0] if failed else r.stdout.strip().splitlines()[-1]})
        (root / BP).write_text(src)
    rep = {"module": BP, "tests": TEST, "mutations": len(results), "caught": sum(r["caught"] for r in results),
           "survivors": [r["mutation"] for r in results if not r["caught"]], "results": results, "wall_s": round(time.time() - t0, 1)}
    Path(out).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("mutations", "caught", "survivors", "wall_s")}))
    return 0 if not rep["survivors"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
