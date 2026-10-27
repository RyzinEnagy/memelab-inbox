"""Skeptic 14 own mutations (not in the phase's 63): copy the clone, apply one mutation, run the behavioral tests.
    python -B p14_own_mutations.py REPO"""
import shutil, subprocess, sys, tempfile
from pathlib import Path
REPO = Path(sys.argv[1]); BP = "memelab/predictive/behavioral.py"
MUT = [
 ("X1 meter cap reached during the run ignored by the adapter",
  '            elif self.meter and self.meter.summary()["cap_reached"] and self.meter.summary()["calls_refused"] > before["calls_refused"]:\n                reason = "COST_CAP_REACHED"\n',
  ''),
 ("X2 netns requested but unshare prefix dropped", "            if self.netns:\n                argv = [\"/usr/bin/unshare\", \"-n\", *argv]", "            if False:\n                argv = [\"/usr/bin/unshare\", \"-n\", *argv]"),
 ("X3 any IP literal accepted as loopback", '    if not ip.is_loopback or str(ip) not in ("127.0.0.1", "::1"):', "    if False:"),
 ("X4 response size cap off (service)", "        if len(data) > MAX_RESPONSE_BYTES:\n            return \"BAD_RESPONSE\", None\n        if r.status in (401, 403):", "        if r.status in (401, 403):"),
 ("X5 stability compares only the first persona set", "        for p in GRID_PERSONAS:\n            if len({tuple(grid[(s, p)][\"labels\"]) for s in GRID_SEEDS}) > 1:", "        for p in GRID_PERSONAS[:1]:\n            if len({tuple(grid[(s, p)][\"labels\"]) for s in GRID_SEEDS}) > 1:"),
]
for name, a, b in MUT:
    td = Path(tempfile.mkdtemp(prefix="sk14m_"))
    for d in ("memelab", "tests", "audits/predictive-intelligence/phase_14", "audits/predictive-intelligence/phase_13/calibration"):
        shutil.copytree(REPO / d, td / d)
    src = (td / BP).read_text(); assert src.count(a) == 1, name
    (td / BP).write_text(src.replace(a, b))
    p = subprocess.run([sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", "tests/test_predictive_behavioral.py"], cwd=td, capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "MEMELAB_DB": str(td / "m.db"), "HOME": str(td)})
    last = [l for l in p.stdout.splitlines() if l.strip()][-1:]
    fail = next((l for l in p.stdout.splitlines() if l.startswith("FAILED")), "")
    print(f"{name}: {'CAUGHT' if p.returncode else 'SURVIVED'} | {last} {fail[:110]}")
    shutil.rmtree(td)
