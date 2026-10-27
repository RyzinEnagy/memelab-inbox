#!/usr/bin/env bash
# Phase 20 (G6, G9): clean-clone end-to-end paths at the frozen commit. Research only; network blocked for every lab command.
#   1. tools/release_e2e.py on the frozen commit (its own clone, sockets refused by its audit hook, credentials removed);
#   2. the predictive real-path smoke of Phase 17, unchanged (`phase_17/probes/real_path_smoke.sh FROZEN OUT`, sandbox clone,
#      every lab command under `unshare -n`), and its comparison (`run_integration.py smoke`);
#   3. tools/release_audit.py --history on a single-branch clone of feature/predictive-intelligence at the frozen commit.
# Everything under OUTDIR; the caller deletes the sandboxes after the summaries are written.
#
#   bash e2e.sh FROZEN_COMMIT OUTDIR
set -u
FROZEN="$1"
OUT="$2"
REPO="$(cd "$(dirname "$0")/../../../.." && pwd)"
A=audits/predictive-intelligence
mkdir -p "$OUT"
log() { echo "$(date -u +%FT%TZ) $*" >> "$OUT/e2e_runs.txt"; }
: > "$OUT/e2e_runs.txt"
# 1. release_e2e in a clone of the frozen commit (release_e2e clones the committed HEAD of --src)
rm -rf "$OUT/src"; git clone -q "$REPO" "$OUT/src"; git -C "$OUT/src" checkout -q "$FROZEN"
log "release_e2e start"
(cd "$OUT/src" && python -B tools/release_e2e.py --src "$OUT/src" --out "$OUT/release_e2e.md" --json "$OUT/release_e2e.json" > "$OUT/release_e2e.stdout" 2>&1)
log "release_e2e exit $?"
# 2. predictive real-path smoke
log "smoke start"
bash "$REPO/$A/phase_17/probes/real_path_smoke.sh" "$FROZEN" "$OUT/smoke" > "$OUT/smoke.stdout" 2>&1
log "smoke exit $?"
mkdir -p "$OUT/smoke_summary"
(cd "$REPO" && python -B "$A/phase_17/probes/run_integration.py" smoke "$OUT/smoke" "$OUT/smoke_summary/REAL_PATH_SMOKE.json" > "$OUT/smoke_summary.stdout" 2>&1)
log "smoke summary exit $?"
# 3. release audit with history on a single-branch clone
rm -rf "$OUT/single"
git clone -q --single-branch --branch feature/predictive-intelligence "file://$REPO" "$OUT/single"
git -C "$OUT/single" checkout -q "$FROZEN"
log "single-branch clone $(git -C "$OUT/single" rev-parse --short HEAD) refs $(git -C "$OUT/single" for-each-ref | wc -l)"
(cd "$OUT/single" && python -B tools/release_audit.py --history > "$OUT/release_audit_history.txt" 2>&1)
log "release_audit --history exit $?"
grep -n "Needs action" "$OUT/release_audit_history.txt" | tail -1 >> "$OUT/e2e_runs.txt"
git -C "$REPO" status --porcelain > "$OUT/checkout_status.txt"
cat "$OUT/e2e_runs.txt"
