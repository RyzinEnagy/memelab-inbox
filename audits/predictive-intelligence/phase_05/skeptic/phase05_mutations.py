"""Phase 05 skeptic: mutations not in the phase's own list, run against the three Phase 05 test files (no -x: all failures
counted). Usage: python phase05_mutations.py CLONE OUT.json"""
import json, subprocess, sys
from pathlib import Path
clone, out = Path(sys.argv[1]), Path(sys.argv[2])
P = "memelab/predictive/"
TESTS = ["tests/test_predictive_asof_store.py", "tests/test_predictive_asof_features.py", "tests/test_predictive_asof_fixture.py"]
M = [
 ("any token parameter counts as the mint's price", "store.py", "    if token_param == mint:", "    if token_param:"),
 ("provider-lag availability from candle start", "store.py", 'av, basis, rev = end + lag, "PROVIDER_LAG_RECONSTRUCTION", None',
  'av, basis, rev = start + lag, "PROVIDER_LAG_RECONSTRUCTION", None'),
 ("boundary drop by candle start (PI-D-034 m4 regression)", "store.py", "if boundary is not None and start + period > float(boundary):",
  "if boundary is not None and start > float(boundary):"),
 ("as-of view mixes candle periods", "features.py", 'f"AND period_s = ? AND {col} <= ?", (chain, mint, pool, PERIOD_S, self.cutoff))',
  'f"AND ? > 0 AND {col} <= ?", (chain, mint, pool, PERIOD_S, self.cutoff))'),
 ("reference candle chosen by start, not end", "features.py", 'cand = [c for c in cs if c["end_at"] <= x]',
  'cand = [c for c in cs if c["start_at"] <= x]'),
 ("token row taken from the newest export (future pool/token facts)", "store.py", 'tk = tok_at.get((e["commit"], e["mint"]))',
  'tk = next((k for ex2 in reversed(exports) for k in ex2.get("tokens") or [] if k["mint"] == e["mint"]), None)'),
 ("every read claims the vendor had nothing earlier (censoring becomes BEFORE_FIRST_CANDLE)", "store.py",
  "cover_complete = 1 if (status == 200 and bad_body is None and ident_ok and len(rows) < limit) else 0",
  "cover_complete = 1 if (status == 200 and bad_body is None and ident_ok) else 0"),
 ("vendor NO_DATA treated as an as-of fact (model input)", "features.py", '"VENDOR_NO_DATA": RETRIEVAL,', '"VENDOR_NO_DATA": AS_OF,'),
 ("reconstructed values labelled FACT", "features.py", 'evidence = "HEURISTIC" if "PROVIDER_LAG_RECONSTRUCTION" in bases else "FACT"',
  'evidence = "FACT"'),
 ("revision compared with the oldest version", "store.py", "ORDER BY available_at DESC, id DESC LIMIT 1", "ORDER BY available_at ASC, id ASC LIMIT 1"),
 ("check_plan allows a boundary after the pool's last development decision", "sources.py",
  'if p["boundary"] > h0 - HOLDOUT_CONTACT_PAD_S or p["boundary"] > p["last_decision"]:',
  'if p["boundary"] > h0 - HOLDOUT_CONTACT_PAD_S:'),
]
def run():
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *TESTS], cwd=clone, capture_output=True, text=True)
    return r.returncode, (r.stdout.strip().splitlines() or [""])[-1]
res = {"control": run(), "mutations": []}
for name, f, old, new in M:
    p = clone / P / f
    src = p.read_text()
    assert src.count(old) == 1, (name, src.count(old))
    p.write_text(src.replace(old, new))
    try:
        code, line = run()
    finally:
        p.write_text(src)
    res["mutations"].append({"mutation": name, "file": f, "caught": code != 0, "result": line})
    print(name, "|", code != 0, "|", line, flush=True)
res["caught"] = sum(m["caught"] for m in res["mutations"]); res["total"] = len(M)
out.write_text(json.dumps(res, indent=1) + "\n")
print(res["control"], res["caught"], "of", res["total"])
