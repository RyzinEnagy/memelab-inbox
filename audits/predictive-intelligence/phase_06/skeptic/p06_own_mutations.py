"""Phase 06 skeptic: mutations NOT in the phase's own list. Usage: python -B p06_own_mutations.py <clone> <out.json>"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path
REPO = Path(sys.argv[1]); F = "memelab/predictive/labels.py"
M = [
 ("thinning before eligibility (CC-01)", '        eligible = [d for d in u.decisions if elig[d["decision_key"]] == "ELIGIBLE"]',
  '        eligible = [d for d in u.decisions if elig[d["decision_key"]] not in ("OUT_OF_SCOPE_CHAIN", "NO_SNAPSHOT_PRICE")]'),
 ("pending at equality (< to <=)", 'elif rd.retrieved_at < rec["label_matures_at"]:', 'elif rd.retrieved_at <= rec["label_matures_at"]:'),
 ("purge boundary (<= to <)", 'C.label_matures_at(target, decision_time) <= h0 else "PURGED"', 'C.label_matures_at(target, decision_time) < h0 else "PURGED"'),
 ("halt span starts at 24 h", '    return te + tg["halt_quiet_from_s"], te + tg["horizon_s"] + tg["confirm_s"]',
  '    return te + tg["horizon_s"], te + tg["horizon_s"] + tg["confirm_s"]'),
 ("halt span overlap -> containment", "    return float(c[0]) < e and float(c[0]) + period > s", "    return float(c[0]) >= s and float(c[0]) + period <= e"),
 ("NEITHER and NO_TRADES swapped", '            cls = "NEITHER" if path else "NO_TRADES_AFTER_ENTRY"', '            cls = "NO_TRADES_AFTER_ENTRY" if path else "NEITHER"'),
 ("reference = newest candle in read before entry", "    ref = C.reference_candle(list(read.candles), decision_time)",
  "    ref = max((c for c in read.candles if c[0] + 300 <= decision_time + 300), default=None, key=lambda c: c[0])"),
 ("p0 from candle open", "    p0 = float(ref[4])", "    p0 = float(ref[1])"),
 ("T2 drawdown inclusive -> strict", "        if c[3] <= Dd:", "        if c[3] < Dd:"),
 ("absence cover strict -> non-strict", "            and read.cover_from < s)", "            and read.cover_from <= s)"),
 ("first-touch scan from the end", "        for c in path:\n            up, lo", "        for c in reversed(path):\n            up, lo"),
 ("training gate allows censored", "AND censored=0 ORDER BY decision_key, id", "ORDER BY decision_key, id"),
 ("training gate allows purged split", "WHERE target=? AND split='DEVELOPMENT' AND state='LABELED'", "WHERE target=? AND split IN ('DEVELOPMENT','PURGED') AND state='LABELED'"),
 ("conservative lens flipped", '(0 if rec["target"] != T2 else 1) if rec["censored"]', '(1 if rec["target"] != T2 else 0) if rec["censored"]'),
 ("ceil_grid -> floor", "    return float(math.ceil(float(t) / period) * period)", "    return float(math.floor(float(t) / period) * period)"),
 ("other pools: only first 2", "    for o in other_reads[:3]:", "    for o in other_reads[:2]:"),
 ("cross-target drawdown invariant off", "            if ft is None or ft > r.get(\"first_touch_start\"):", "            if False:"),
]
def run(root):
    return subprocess.run([sys.executable, "-m", "pytest", "tests/test_predictive_labels.py", "-x", "-q", "-p", "no:cacheprovider"],
                          cwd=root, capture_output=True, text=True).returncode
res = []
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp) / "b"; base.mkdir()
    for d in ("memelab", "tests"): shutil.copytree(REPO / d, base / d, ignore=shutil.ignore_patterns("__pycache__"))
    ctl = run(base)
    for name, old, new in M:
        w = Path(tmp) / "w"
        if w.exists(): shutil.rmtree(w)
        shutil.copytree(base, w)
        p = w / F; s = p.read_text()
        assert s.count(old) == 1, (name, s.count(old))
        p.write_text(s.replace(old, new))
        rc = run(w); res.append({"mutation": name, "caught": rc != 0}); print(json.dumps(res[-1]), flush=True)
out = {"control_exit": ctl, "n": len(res), "caught": sum(r["caught"] for r in res), "results": res}
Path(sys.argv[2]).write_text(json.dumps(out, indent=1)); print({k: v for k, v in out.items() if k != "results"})
