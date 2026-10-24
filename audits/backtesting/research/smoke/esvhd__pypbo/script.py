"""Smoke test for esvhd/pypbo: installability only.

Brief rule for this repo: AGPL, review only, smoke test only if it installs cleanly.
This script records whether it installs. It never imports or executes repo code.
Run: /home/claude/ext/venvs/esvhd__pypbo/bin/python -I script.py
"""
import subprocess
import sys

VENV_PIP = "/home/claude/ext/venvs/esvhd__pypbo/bin/pip"
CLONE = "/home/claude/ext/reviews/esvhd__pypbo"

steps = [
    ("pip install from PyPI (wheels only)", [VENV_PIP, "install", "--only-binary=:all:", "pypbo"]),
    ("pip install from PyPI (any dist, no deps)", [VENV_PIP, "install", "--no-deps", "pypbo"]),
    ("pip install from local clone (no build files expected)", [VENV_PIP, "install", "--no-deps", "--no-build-isolation", CLONE]),
]
installed = False
for label, cmd in steps:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
    print(f"[{label}] exit={r.returncode}")
    for line in tail:
        print("   ", line)
    installed = installed or r.returncode == 0

print("\ninstalled cleanly:", installed)
print("functional smoke test:", "eligible" if installed else "NOT RUN (did not install cleanly; brief says review only)")
sys.exit(0 if installed else 2)
