#!/usr/bin/env bash
# CM-2 G8: the daily command end to end in a fresh clone (no private store), twice. Usage: fresh_clone_daily.sh <repo> <out_dir>
# Clones the branch, points origin at the public GitHub repository (as a cloud task would see it), runs
# `predictive_daily.py run` twice, and records exit codes, the file listing before and after, and the clone's commits.
# Never pushes. Writes only into <out_dir> (outside the repository).
set -u
REPO="$1"; OUT="$2"
rm -rf "$OUT"; mkdir -p "$OUT"
C="$OUT/clone"
git clone -q --no-local --branch feature/predictive-intelligence "$REPO" "$C" || exit 20
git -C "$C" remote set-url origin https://github.com/RyzinEnagy/memelab-inbox.git
git -C "$C" remote set-url --push origin DISABLED_NO_PUSH
git -C "$C" rev-parse HEAD > "$OUT/head_before.txt"
list() { (cd "$C" && find . -path ./.git -prune -o -type f -print | LC_ALL=C sort | xargs sha256sum); }
list > "$OUT/files_before.txt"
for i in 1 2; do
  t0=$SECONDS
  ( cd "$C" && python3 -B audits/predictive-intelligence/daily/predictive_daily.py run \
      > "$OUT/run${i}_stdout.txt" 2> "$OUT/run${i}_stderr.txt" ); echo $? > "$OUT/run${i}_exit.txt"
  echo $((SECONDS - t0)) > "$OUT/run${i}_wall.txt"
  list > "$OUT/files_after_run${i}.txt"
  git -C "$C" status --porcelain --untracked-files=all > "$OUT/status_after_run${i}.txt"
  cp "$C/audits/predictive-intelligence/daily/ALERT_SUMMARY.txt" "$OUT/alert_run${i}.txt" 2>/dev/null
done
git -C "$C" log --format='%H %ct %s' "$(cat "$OUT/head_before.txt")"..HEAD > "$OUT/clone_commits.txt"
git -C "$C" diff --name-only "$(cat "$OUT/head_before.txt")" HEAD > "$OUT/committed_paths.txt"
git -C "$C" rev-parse origin/main > "$OUT/origin_main.txt"
( cd "$C" && python3 -B audits/predictive-intelligence/daily/predictive_daily.py verify ) > "$OUT/verify.txt"; echo $? >> "$OUT/verify.txt"
echo done
