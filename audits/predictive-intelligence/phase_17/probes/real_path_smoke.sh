#!/usr/bin/env bash
# Phase 17 real-path smoke (research only). Runs the lab's real scout command on the committed inbox bodies, after importing
# the newest state export into a temporary lab database, in a sandbox clone; every run inside `unshare -n` (no network
# namespace: no call can leave the machine). Nothing is written in the checkout: the sandbox clone, the databases, the reports
# and the predictive state all live under OUTDIR.
#
#   bash real_path_smoke.sh FROZEN_COMMIT OUTDIR
#
# Runs (pre-registered in ../experiments/EXPERIMENT_REGISTRY.csv):
#   base_off      b0fad12 (the pre-Phase-17 code), no config                       -> the reference body
#   frozen_off    FROZEN, no config                                               -> must equal base_off byte for byte (P40)
#   frozen_on     FROZEN, predictive.enabled true, fresh database and state       -> appended section, every request ABSTAIN
#   rerun         the same command again on the same database and state           -> no new document
#   retry         a fresh database (same import), the same state                  -> the same snapshots: DUPLICATE
#   storm         PAID listed four times, fresh database and state                -> one attempt for PAID
#   research      mode research, fresh database and state                         -> internal B0 and B2 reference records
#   analyze_on    `analyze` of PAID with the flag on, fresh database and state    -> one predictive line
set -u
FROZEN="$1"
OUT="$2"
REPO="$(cd "$(dirname "$0")/../../../.." && pwd)"
BASE=b0fad12e529ef9687fcd3c1dae96e208f7b3e3c6
EXPORT=71fc50e1eb86d916034bb0285a466cf2ec1cc4d0
MINTS="98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump 6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx 7KEPApdbBMByrmqihz3bht2uMhFQcatjfSFQCKq66kH3 9XKzy4KahcZaGJPJtz1PtqGPB3CiseoBrx7TcQhEpump DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump HcRLc9VDgjLeK154xDawfb1dmVJ98DoSqcwTHGqiDeJR Hg5Ja55T5wESq4vyFoiVCMeHXtGyVA69X2UHq8hgpump 55Vr2VpSwxsDkB6uGGHAvRv86K6zax2Zb4TT8ivwDEzW"
PAID=98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump
RESULTS="disc01 s2_01 deep01a deep02 deep03 deep04 forensics01"
SB="$OUT/sandbox"
mkdir -p "$OUT/logs" "$OUT/runs"
rm -rf "$SB" "$OUT/state" "$OUT/state_storm" "$OUT/state_research" "$OUT/state_analyze"
git clone -q "$REPO" "$SB"
git -C "$REPO" show "$EXPORT:data/state/latest.json" > "$OUT/latest_export.json"
sha256sum "$OUT/latest_export.json" > "$OUT/logs/latest_export.sha256"

fresh_db() {
  rm -f "$OUT/lab.sqlite" "$OUT/lab.sqlite-shm" "$OUT/lab.sqlite-wal"
  (cd "$SB" && MEMELAB_DB="$OUT/lab.sqlite" unshare -n python -B -m memelab init > /dev/null)
  (cd "$SB" && MEMELAB_DB="$OUT/lab.sqlite" unshare -n python -B -m memelab.state import "$OUT/latest_export.json" > "$OUT/logs/import_$1.txt")
}

config() {   # $1: off | on | research | state dir name
  rm -f "$SB/data/config.json"
  if [ "$1" != "off" ]; then
    mode=fast; [ "$1" = "state_research" ] && mode=research
    printf '{"predictive": {"enabled": true, "state_dir": "%s", "mode": "%s"}}\n' "$OUT/$1" "$mode" > "$SB/data/config.json"
  fi
}

scout() {    # $1 run name, $2 mints
  rm -rf "$OUT/reports"; mkdir -p "$OUT/reports"
  start=$(date -u +%FT%TZ)
  (cd "$SB" && MEMELAB_DB="$OUT/lab.sqlite" unshare -n python -B -m memelab scout --mints $2 --results $RESULTS --stage1 disc01 \
     --report-dir "$OUT/reports" > "$OUT/logs/$1.stdout" 2> "$OUT/logs/$1.stderr")
  rc=$?
  echo "$1 start $start end $(date -u +%FT%TZ) exit $rc commit $(git -C "$SB" rev-parse --short HEAD)" >> "$OUT/logs/runs.txt"
  rm -rf "$OUT/runs/$1"; cp -r "$OUT/reports" "$OUT/runs/$1"
  cp "$OUT/lab.sqlite" "$OUT/runs/$1/lab.sqlite"
  git -C "$SB" status --porcelain --ignored > "$OUT/logs/$1.git_status"
}

git -C "$SB" checkout -q "$BASE";   config off; fresh_db base_off;   scout base_off "$MINTS"
if [ "$FROZEN" = "WORKTREE" ]; then          # debug runs only (logged as such): HEAD plus the checkout's uncommitted code files
  git -C "$SB" checkout -q HEAD
  for f in memelab/cli.py memelab/predictive/integration.py memelab/predictive/bt_adapter.py; do cp "$REPO/$f" "$SB/$f"; done
else
  git -C "$SB" checkout -q "$FROZEN"
fi
config off; fresh_db frozen_off; scout frozen_off "$MINTS"
config state; fresh_db frozen_on; scout frozen_on "$MINTS"
scout rerun "$MINTS"
fresh_db retry; scout retry "$MINTS"
config state_storm; fresh_db storm; scout storm "$PAID $PAID $PAID $PAID $MINTS"
config state_research; fresh_db research; scout research "$MINTS"
config state_analyze; fresh_db analyze_on
(cd "$SB" && MEMELAB_DB="$OUT/lab.sqlite" unshare -n python -B -m memelab analyze "$PAID" --results $RESULTS --stage1 disc01 \
   > "$OUT/logs/analyze_on.stdout" 2> "$OUT/logs/analyze_on.stderr"); echo "analyze_on exit $?" >> "$OUT/logs/runs.txt"
# `analyze` has no report-dir option: by design it writes its token report under the sandbox's data/reports (a tracked path of
# the sandbox clone, never of the checkout). Recorded, then the sandbox file is restored.
git -C "$SB" status --porcelain > "$OUT/logs/analyze_on.git_status"
git -C "$SB" checkout -q -- data/reports
rm -f "$SB/data/config.json"
for s in state state_storm state_research state_analyze; do
  (cd "$SB" && unshare -n python -B -m memelab.predictive.integration status --state-dir "$OUT/$s" > "$OUT/logs/status_$s.json"); echo "status $s exit $?" >> "$OUT/logs/runs.txt"
  (cd "$SB" && unshare -n python -B -m memelab.predictive.integration check --state-dir "$OUT/$s" > "$OUT/logs/check_$s.json"); echo "check $s exit $?" >> "$OUT/logs/runs.txt"
done
git -C "$SB" status --porcelain > "$OUT/logs/final_git_status_tracked.txt"
git -C "$REPO" status --porcelain > "$OUT/logs/checkout_git_status.txt"
echo done
