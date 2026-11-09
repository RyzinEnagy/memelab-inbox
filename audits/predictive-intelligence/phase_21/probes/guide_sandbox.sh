#!/usr/bin/env bash
# Phase 21 CP21-1 (skeptic F6): run USER_GUIDE.md section 1 ("Turning the flag on in a sandbox") literally, line by line, with
# `/tmp/pi_` replaced by `OUTDIR/pi_` so that nothing is written outside OUTDIR. The clone line needs the network (GitHub); every
# other line runs inside `unshare -n` (Linux, root) from the sandbox clone. Each line's exit code and output go to OUTDIR/logs.
#
#   bash guide_sandbox.sh OUTDIR
set -u
OUT="$1"
REPO="$(cd "$(dirname "$0")/../../../.." && pwd)"
GUIDE="$REPO/audits/predictive-intelligence/phase_21/release/USER_GUIDE.md"
mkdir -p "$OUT/logs"
rm -rf "$OUT/pi_sandbox" "$OUT/pi_state" "$OUT/pi_reports" "$OUT/pi_private" "$OUT/pi_lab.sqlite" "$OUT/pi_export.json"
python3 - "$GUIDE" "$OUT" > "$OUT/commands.txt" <<'PY'
import sys
text = open(sys.argv[1]).read()
sec = text.split("## 1.", 1)[1].split("## 2.", 1)[0]
blocks = sec.split("```")[1::2]
for b in blocks:
    for line in b.strip("\n").splitlines():
        line = line.strip()
        if line:
            print(line.replace("/tmp/pi_", sys.argv[2] + "/pi_"))
PY
: > "$OUT/guide_sandbox.txt"
SB="$OUT/pi_sandbox"
i=0
while IFS= read -r line; do
  i=$((i + 1))
  case "$line" in
    "git clone "*)
      cmd="${line%% && cd *}"
      bash -c "$cmd" > "$OUT/logs/$i.out" 2>&1; rc=$? ;;
    *)
      (cd "$SB" && unshare -n bash -c "$line" > "$OUT/logs/$i.out" 2>&1); rc=$? ;;
  esac
  echo "$i exit $rc :: $line" | sed "s#$OUT#OUTDIR#g" >> "$OUT/guide_sandbox.txt"
done < "$OUT/commands.txt"
git -C "$SB" status --porcelain > "$OUT/logs/sandbox_status.txt"
git -C "$REPO" status --porcelain > "$OUT/logs/checkout_status.txt"
cat "$OUT/guide_sandbox.txt"
