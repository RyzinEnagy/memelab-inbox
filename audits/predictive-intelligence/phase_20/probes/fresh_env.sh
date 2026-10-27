#!/usr/bin/env bash
# Phase 20 (G8): a fresh environment. A single-branch clone of the frozen commit, a new virtual environment without system site
# packages holding only the baseline numpy and pytest (phase_00/baseline/PIP_FREEZE.txt; free PyPI downloads, the only network use
# of this script), then the predictive tests and the cross-component tests run with the network removed (`unshare -n`) and the
# private research stores hidden (`unshare -m` with an empty tmpfs over /home/claude/pi_research), as on a machine that has never
# held them. Everything under OUTDIR; deleted by the caller after the summary.
#
#   bash fresh_env.sh FROZEN_COMMIT OUTDIR
set -u
FROZEN="$1"
OUT="$2"
REPO="$(cd "$(dirname "$0")/../../../.." && pwd)"
mkdir -p "$OUT"
rm -rf "$OUT/clone" "$OUT/venv"
git clone -q --single-branch --branch feature/predictive-intelligence "file://$REPO" "$OUT/clone"
git -C "$OUT/clone" checkout -q "$FROZEN"
echo "clone $(git -C "$OUT/clone" rev-parse HEAD) branches $(git -C "$OUT/clone" branch -a | wc -l)" > "$OUT/fresh_env.log"
python3 -m venv "$OUT/venv"
"$OUT/venv/bin/python" -m pip install -q --disable-pip-version-check numpy==2.5.3 pytest==9.1.1 iniconfig==2.3.1 pluggy==1.7.0 packaging==26.3 >> "$OUT/fresh_env.log" 2>&1
echo "pip exit $?" >> "$OUT/fresh_env.log"
"$OUT/venv/bin/python" -m pip freeze > "$OUT/pip_freeze.txt"
"$OUT/venv/bin/python" -c "import sys; print('python', sys.version.split()[0], 'system_site', sys.flags.no_site == 0)" >> "$OUT/fresh_env.log"
cd "$OUT/clone"
unshare -m -n sh -c "mount -t tmpfs tmpfs /home/claude/pi_research && '$OUT/venv/bin/python' -m pytest -q -p no:cacheprovider -rs \
  tests/test_predictive_*.py > '$OUT/pytest_predictive.txt' 2>&1; echo \"pytest exit \$?\" >> '$OUT/fresh_env.log'; \
  ls /home/claude/pi_research | wc -l | sed 's/^/stores visible inside: /' >> '$OUT/fresh_env.log'"
git -C "$OUT/clone" status --porcelain > "$OUT/clone_status.txt"
tail -3 "$OUT/pytest_predictive.txt" >> "$OUT/fresh_env.log"
cat "$OUT/fresh_env.log"
