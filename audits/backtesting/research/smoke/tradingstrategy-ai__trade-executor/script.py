"""Install probe for tradingstrategy-ai/trade-executor @ 34fc7eb0b659 (Python 3.13).

The planned fill-timing smoke test (30 hourly bars, signal on bar k close, check
fill at bar k close vs bar k+1 open) could not run: the only PyPI releases
(0.1.0 to 0.3, last upload 2023-04-29) declare Requires-Python >=3.10,<3.11, and
the repo itself (0.3.2) installs only through Poetry with path dependencies on two
git submodules (deps/trading-strategy, deps/web3-ethereum-defi) plus a git-pinned
fork (lighter-sdk, ships a native signer). Building from the repo would mean
running a niche build of submodules and a forked native signer, which the review
brief forbids, so this probe stops at pip's resolver. No package code is executed.

Usage: python -I script.py <venv_python>
"""

import subprocess
import sys

venv_python = sys.argv[1]
print(f"interpreter: {subprocess.run([venv_python, '--version'], capture_output=True, text=True).stdout.strip()}")
codes = []
for spec in ("trade-executor", "trade-executor==0.3"):
    cmd = [venv_python, "-m", "pip", "install", "--only-binary", ":all:", "--no-cache-dir", spec]
    print("$", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    print((r.stdout + r.stderr).strip())
    print(f"pip_exit_code={r.returncode}")
    codes.append(r.returncode)
print("RESULT:", "INSTALL_FAILED (no release supports Python 3.13)" if all(codes) else "INSTALLED")
sys.exit(1 if all(codes) else 0)
