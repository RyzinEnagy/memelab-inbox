#!/usr/bin/env bash
# CM-2 repair (PI-D-140): the repair's tests run against the code before the repair (833b2f6: change control only on top of
# cdff266). Usage: old_code_probe_repair.sh <repo> <out_dir>. Writes only into <out_dir>. The end-to-end tests clone the
# committed tree of the clone, so the old script is what they run.
set -u
REPO="$1"; OUT="$2"; rm -rf "$OUT"; mkdir -p "$OUT"; C="$OUT/old"
git clone -q --no-local "$REPO" "$C" && git -C "$C" checkout -q -B feature/predictive-intelligence 833b2f6
git -C "$C" fetch -q "$REPO" refs/remotes/origin/main:refs/remotes/origin/main
for t in tests/test_predictive_promotion.py tests/test_predictive_daily.py tests/test_predictive_cm2_guards.py; do cp "$REPO/$t" "$C/$t"; done
git -C "$C" -c user.email=o@localhost -c user.name=o commit -q -am "repair tests on the old code"
( cd "$C" && python3 -m pytest -q -p no:cacheprovider tests/test_predictive_promotion.py tests/test_predictive_daily.py tests/test_predictive_cm2_guards.py 2>&1 | grep -E "^(FAILED|ERROR)|passed|failed" ) > "$OUT/result.txt"
cat "$OUT/result.txt"
