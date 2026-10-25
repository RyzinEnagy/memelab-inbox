"""Phase 08 skeptic counterexample CX-S08: score-time re-standardisation. A plausible 'fix' standardises the rows being scored
with their own mean and sd (Prep fitted on the scoring batch) instead of the card's training statistics. Each scored row then
depends on the other rows of its day (some decided after it): look-ahead across rows at prediction time, and train-only
standardisation broken. The script applies it to memelab/predictive/technical.py in the skeptic clone, runs the phase tests,
reruns the recorded runner on store copies, compares the outputs with the committed ones and runs verify_trace on both traces;
then restores the file. A second mutation (a fetch series ending up to an hour before T counted as covering T) is run the same way.
"""
import hashlib, json, subprocess, sys
from pathlib import Path
REPO = Path("/home/claude/pi_orchestration/skeptic_08")
W = Path("/home/claude/pi_orchestration/skeptic/p08work")
TGT = REPO / "memelab/predictive/technical.py"
P08 = REPO / "audits/predictive-intelligence/phase_08"
MUT = {
 "CX-S08 score-time re-standardisation": ('prep, lr = K.Prep.from_dict(body["prep"]), K.Logistic.from_dict(body["logistic"])',
                                          ('prep, lr = K.Prep.from_dict(body["prep"]), K.Logistic.from_dict(body["logistic"])\n'
                                           '            if len(X) > 1:\n'
                                           '                _z = prep._fill(X); prep.mu = _z.mean(axis=0); prep.sd = np.where(_z.std(axis=0) > 0, _z.std(axis=0), 1.0)')),
 "series boundary up to 1 h before T counts as covering T": ("need_to = T - lag", "need_to = T - lag - 3600.0"),
 "value availability is the earliest input": ('round(max(float(c["_avail"]) for c in inputs), 6)', 'round(min(float(c["_avail"]) for c in inputs), 6)'),
}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
orig = TGT.read_text()
rep = {}
try:
    for name, (a, b) in MUT.items():
        assert orig.count(a) == 1, name
        TGT.write_text(orig.replace(a, b))
        t = subprocess.run([sys.executable, "-B", "-m", "pytest", "tests/test_predictive_technical.py", "-q", "-p", "no:cacheprovider"],
                           cwd=REPO, capture_output=True, text=True)
        out = W / ("mut_" + hashlib.sha1(name.encode()).hexdigest()[:8])
        subprocess.run(["rm", "-rf", str(out)])
        r = subprocess.run([sys.executable, "-B", str(P08 / "probes/run_technical.py"), str(out), "--dev-store", str(W / "dev_store.sqlite"),
                            "--feature-store", str(W / "predictive_store.sqlite")], cwd=REPO, capture_output=True, text=True)
        changed = []
        if r.returncode == 0:
            for f in sorted(out.rglob("*")):
                if f.is_file() and "run_log" not in f.name and "FORECAST_TRACE" not in f.name:
                    c = P08 / f.relative_to(out)
                    if not c.exists() or sha(c) != sha(f):
                        changed.append(str(f.relative_to(out)))
        vt = {}
        for tr in ("evidence/trace/FORECAST_TRACE.json", "evidence/trace/second/FORECAST_TRACE.json"):
            if (out / tr).exists():
                TGT.write_text(orig)          # the verifier must not depend on the mutated code (it does not import it anyway)
                v = subprocess.run([sys.executable, "-B", str(P08 / "probes/verify_trace.py"), str(out / tr), "--feature-store",
                                    str(W / "predictive_store.sqlite")], cwd=REPO, capture_output=True, text=True)
                vt[tr] = {"exit": v.returncode, "tail": v.stdout.strip()[-300:]}
                TGT.write_text(orig.replace(a, b))
        rep[name] = {"phase_tests": t.stdout.strip().splitlines()[-1] if t.stdout.strip() else t.stderr[-200:],
                     "runner_exit": r.returncode, "runner_tail": (r.stdout + r.stderr).strip()[-300:],
                     "outputs_changed_vs_committed": changed, "verify_trace": vt}
        TGT.write_text(orig)
finally:
    TGT.write_text(orig)
print(json.dumps(rep, indent=1))
json.dump(rep, open(W.parent / "p08_counterexample_out.json", "w"), indent=1)
