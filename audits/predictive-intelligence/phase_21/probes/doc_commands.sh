#!/usr/bin/env bash
# Phase 21 (G9): run the operator commands that USER_GUIDE.md and INSTALL_RUNBOOK.md give, once, in a sandbox. Research only.
#
#   bash doc_commands.sh SMOKE_DIR OUTDIR
#
# SMOKE_DIR is the real-path smoke folder of the release checks (its `state` folder holds the flag-on run on the 71fc50e export,
# its `runs/frozen_on/lab.sqlite` the lab database of that run). Copies are used; nothing in SMOKE_DIR or in this checkout is
# changed. A sandbox clone of this checkout at HEAD runs every command under `env -i` and `unshare -n`. Each command's exit code
# and output go to OUTDIR/logs; OUTDIR/doc_commands.txt lists them.
set -u
SMOKE="$1"
OUT="$2"
REPO="$(cd "$(dirname "$0")/../../../.." && pwd)"
A=audits/predictive-intelligence
SB="$OUT/sandbox"
mkdir -p "$OUT/logs" "$OUT/private"
rm -rf "$SB" "$OUT/state" "$OUT/state_tampered"
git clone -q "$REPO" "$SB"
git -C "$SB" checkout -q "$(git -C "$REPO" rev-parse HEAD)"
cp -r "$SMOKE/state" "$OUT/state"
cp "$SMOKE/runs/frozen_on/lab.sqlite" "$OUT/lab.sqlite"
printf '{"predictive": {"enabled": true, "state_dir": "%s", "mode": "fast"}}\n' "$OUT/state" > "$OUT/cfg_on.json"
printf '{"predictive": {"enabled": false}}\n' > "$OUT/cfg_off.json"
E="env -i HOME=/root PATH=$PATH LANG=C.UTF-8 LC_ALL=C.UTF-8"
: > "$OUT/doc_commands.txt"
run() {   # $1 name, rest: command (run in the sandbox)
  n="$1"; shift
  (cd "$SB" && $E unshare -n "$@" > "$OUT/logs/$n.out" 2>&1)
  echo "$n exit $? :: $*" | sed "s#$OUT#OUTDIR#g; s#$SB#SANDBOX#g" >> "$OUT/doc_commands.txt"
}
run status        python -B -m memelab.predictive.integration status --state-dir "$OUT/state" --config "$OUT/cfg_on.json"
run check         python -B -m memelab.predictive.integration check --state-dir "$OUT/state" --config "$OUT/cfg_on.json"
run report_on     python -B -m memelab.predictive.reports report --state-dir "$OUT/state" --config "$OUT/cfg_on.json" \
                    --lab-db "$OUT/lab.sqlite" --registry-dir "$SB/$A/phase_16/registry" --out "$OUT/private/report.md"
run report_off    python -B -m memelab.predictive.reports report --state-dir "$OUT/state" --config "$OUT/cfg_off.json"
run alerts_dry    python -B -m memelab.predictive.reports alerts --state-dir "$OUT/state" --config "$OUT/cfg_on.json" \
                    --alert-db "$OUT/private/alerts.sqlite" --outbox "$OUT/private/outbox" --lab-db "$OUT/lab.sqlite" \
                    --registry-dir "$SB/$A/phase_16/registry"
run alerts_state  python -B -m memelab.predictive.reports alerts-state --alert-db "$OUT/private/alerts.sqlite" --config "$OUT/cfg_on.json"
run alerts_off    python -B -m memelab.predictive.reports alerts --state-dir "$OUT/state" --config "$OUT/cfg_off.json"
run seal          python -B "$A/phase_06/probes/check_seal.py"
run docs_demo     python -B "$A/phase_21/probes/docs_demo.py" 2026-11-09T00:00:00Z "$OUT/docs_demo.json"
# disaster recovery: a damaged copy of the state is refused by `check` (one byte of the first JSONL file changed)
cp -r "$OUT/state" "$OUT/state_tampered"
f="$(ls "$OUT/state_tampered"/*.jsonl | head -1)"
python3 - "$f" <<'PY'
import sys
p = sys.argv[1]
b = bytearray(open(p, "rb").read())
i = b.index(b'"', 10)
b[i + 1] = ord("Z") if b[i + 1] != ord("Z") else ord("Y")
open(p, "wb").write(bytes(b))
PY
echo "tampered $(basename "$f")" >> "$OUT/doc_commands.txt"
run check_tampered python -B -m memelab.predictive.integration check --state-dir "$OUT/state_tampered" --config "$OUT/cfg_on.json"
git -C "$SB" status --porcelain > "$OUT/logs/sandbox_status.txt"
git -C "$REPO" status --porcelain > "$OUT/logs/checkout_status.txt"
ls -R "$OUT/private" > "$OUT/logs/private_files.txt"
cat "$OUT/doc_commands.txt"
