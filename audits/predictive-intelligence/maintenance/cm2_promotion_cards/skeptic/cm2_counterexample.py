"""CM-2 skeptic counterexample: the prediction-before-read anchor (predictive_daily.commit_times) is keyed by ledger LINE
NUMBER, not line content, and nothing compares a committed ledger with the ledger of the commit before it. A commit that
rewrites the ledger (a fresh, self-consistent chain with different prediction numbers) after the outcomes are known keeps the
old commit time for every rewritten line, so admissibility() still says 'committed before the read'.
Usage: python -B cm2_counterexample.py <repo clone> <scratch dir>   (no network)."""
import importlib.util, json, os, subprocess, sys
from pathlib import Path
repo, tmp = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(repo))
spec = importlib.util.spec_from_file_location("pd", repo / "audits/predictive-intelligence/daily/predictive_daily.py")
D = importlib.util.module_from_spec(spec); spec.loader.exec_module(D)
from memelab.predictive import monitoring as M, promotion as P
subprocess.run(["rm", "-rf", str(tmp)]); (tmp / D.REL).mkdir(parents=True)
led = tmp / D.REL / "LEDGER.jsonl"
def g(*a, t):
    env = dict(os.environ, GIT_COMMITTER_DATE=f"@{t} +0000", GIT_AUTHOR_DATE=f"@{t} +0000")
    subprocess.run(["git", "-C", str(tmp), "-c", "user.name=x", "-c", "user.email=x@x", "-c", "commit.gpgsign=false", *a],
                   check=True, capture_output=True, env=env)
subprocess.run(["git", "init", "-q", str(tmp)], check=True)
T1, T_READ, T3 = 1_800_000_000, 1_800_000_600, 1_800_001_200
M.append(led, [{"kind": "MONITOR", "monitor": "STAND_IN_PREDICTION", "number": 0.10, "recorded_at": 0.0} for _ in range(1)])
M.append(led, [{"kind": "MONITOR", "monitor": "STAND_IN_PREDICTION", "number": 0.11, "recorded_at": 1.0}])
g("add", "-A", t=T1); g("commit", "-q", "-m", "predictions", t=T1)
first = led.read_text()
led.unlink()                                                      # rewrite after the outcomes were read at T_READ
M.append(led, [{"kind": "MONITOR", "monitor": "STAND_IN_PREDICTION", "number": 0.90, "recorded_at": 0.0}])
M.append(led, [{"kind": "MONITOR", "monitor": "STAND_IN_PREDICTION", "number": 0.91, "recorded_at": 1.0}])
M.append(led, [{"kind": "MONITOR", "monitor": "STAND_IN_OUTCOME", "recorded_at": 2.0}])
g("add", "-A", t=T3); g("commit", "-q", "-m", "rewrite", t=T3)
D.REPO = tmp
ct = D.commit_times()
rows = [{"decision_key": f"k{i}", "decision_time": 1.0e9 + i, "prediction_seq": i, "outcome_seq": 2,
         "prediction_committed_at": ct[i], "label_observed_at": T_READ, "version_registered_at": 0.0, "version_stale": False}
        for i in (0, 1)]
out = {"ledger_verifies_after_rewrite": M.verify(led)["ok"],
       "rewrite_is_append_of_previous_commit": M.is_append_only(first, led.read_text()),
       "anchor_of_rewritten_lines": {i: ct[i] for i in (0, 1)}, "rewrite_commit_time": T3, "outcome_read_time": T_READ,
       "admissibility_problems": P.admissibility(rows, freeze=0.0)}
print(json.dumps(out, indent=1))
print("COUNTEREXAMPLE HOLDS" if out["ledger_verifies_after_rewrite"] and not out["rewrite_is_append_of_previous_commit"]
      and not out["admissibility_problems"] else "caught")
