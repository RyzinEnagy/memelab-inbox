"""Phase 08 skeptic: replay the run-1 P06-T probe logic (first differing value per decision) and show the one 'accepted' case."""
import sys, json, sqlite3
sys.path.insert(0, "/home/claude/pi_orchestration/skeptic_08")
from memelab.predictive import technical as T, features as F
fs = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True); fs.row_factory = sqlite3.Row
keys = [l.split(",")[0] for l in open(sys.argv[2]).read().splitlines()[1:]]
rows = {l.split(",")[0]: l.split(",") for l in open(sys.argv[2]).read().splitlines()[1:]}
acc = []
n = 0
for k in keys:
    d = fs.execute("SELECT chain, mint, decision_time FROM predictive_decisions WHERE decision_key=?", (k,)).fetchone()
    s = T.technical_as_of(fs, d["chain"], d["mint"], d["decision_time"], decision_key=k)
    if T.row_status(s) is not None:
        continue
    n += 1
    later = T.technical_as_of(fs, d["chain"], d["mint"], d["decision_time"] + 600)["values"]
    diff = [c for c in T.TECH if later[c]["value"] != s["values"][c]["value"]]
    if not diff:
        continue
    c = diff[0]
    row = {"decision_time": d["decision_time"], c: later[c]["value"], c + "__available_at": later[c]["available_at"]}
    try:
        F.validate_rows([row], columns=list(row), availability=[c + "__available_at"]); acc.append({"key": k[:12], "first_diff": c, "all_diffs": diff,
            "avail_minus_T": later[c]["available_at"] - d["decision_time"], "newest_end_at_T+600_minus_T": None})
    except F.AsOfError:
        pass
print(json.dumps({"complete": n, "accepted_by_run1_logic": acc}, indent=1))
