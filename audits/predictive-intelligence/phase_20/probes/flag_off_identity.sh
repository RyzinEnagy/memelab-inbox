#!/usr/bin/env bash
# Phase 20 (G7): flag-off byte identity of the lab's scout against the pre-Phase-17 code b0fad12, on two real state exports and
# under every non-true flag config. Research only; every lab command runs inside `unshare -n`; everything is written under OUTDIR
# (a sandbox clone, lab databases, reports); nothing in the checkout.
#
#   bash flag_off_identity.sh FROZEN_COMMIT OUTDIR
#
# For each export E in {71fc50e (2026-10-26), efdaee9 (2026-10-24)} and each config C in {none, malformed JSON, "enabled": "true"
# (a string), "predictive": true, "enabled": false, "enabled": 1}: a base run at b0fad12 with C and a frozen run with C (the
# lab's own social research policy also reads data/config.json, so a malformed file is compared against the base under the same
# file). Each run: fresh lab database, the export imported, the scout on the committed inbox bodies (the Phase 17 smoke's mints
# and result files). Recorded: every report's sha256, the lab tables' sha256 (tokens without the two wall-clock columns),
# whether data/private exists afterwards, the memelab.predictive modules imported (cli_import_trace.py), git status of the sandbox.
set -u
FROZEN="$1"
OUT="$2"
REPO="$(cd "$(dirname "$0")/../../../.." && pwd)"
HERE="$(cd "$(dirname "$0")" && pwd)"
BASE=b0fad12e529ef9687fcd3c1dae96e208f7b3e3c6
EXPORTS="71fc50e1eb86d916034bb0285a466cf2ec1cc4d0 efdaee9"
MINTS="98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump 6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx 7KEPApdbBMByrmqihz3bht2uMhFQcatjfSFQCKq66kH3 9XKzy4KahcZaGJPJtz1PtqGPB3CiseoBrx7TcQhEpump DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump HcRLc9VDgjLeK154xDawfb1dmVJ98DoSqcwTHGqiDeJR Hg5Ja55T5wESq4vyFoiVCMeHXtGyVA69X2UHq8hgpump 55Vr2VpSwxsDkB6uGGHAvRv86K6zax2Zb4TT8ivwDEzW"
RESULTS="disc01 s2_01 deep01a deep02 deep03 deep04 forensics01"
SB="$OUT/sandbox"
mkdir -p "$OUT/logs" "$OUT/runs"
rm -rf "$SB"
git clone -q "$REPO" "$SB"
cp "$HERE/cli_import_trace.py" "$OUT/cli_import_trace.py"
: > "$OUT/logs/runs.txt"

config() {   # $1: none | malformed | string_true | section_true | false | one
  rm -f "$SB/data/config.json"
  case "$1" in
    none) ;;
    malformed) printf '{not json\n' > "$SB/data/config.json" ;;
    string_true) printf '{"predictive": {"enabled": "true"}}\n' > "$SB/data/config.json" ;;
    section_true) printf '{"predictive": true}\n' > "$SB/data/config.json" ;;
    false) printf '{"predictive": {"enabled": false}}\n' > "$SB/data/config.json" ;;
    one) printf '{"predictive": {"enabled": 1}}\n' > "$SB/data/config.json" ;;
  esac
}

one_run() {  # $1 run name, $2 export commit
  rm -f "$OUT/lab.sqlite" "$OUT/lab.sqlite-shm" "$OUT/lab.sqlite-wal"
  rm -rf "$SB/data/private" "$OUT/reports"; mkdir -p "$OUT/reports"
  (cd "$SB" && MEMELAB_DB="$OUT/lab.sqlite" unshare -n python -B -m memelab init > /dev/null)
  (cd "$SB" && MEMELAB_DB="$OUT/lab.sqlite" unshare -n python -B -m memelab.state import "$OUT/export_$2.json" > "$OUT/logs/import_$1.txt")
  (cd "$SB" && MEMELAB_DB="$OUT/lab.sqlite" unshare -n python -B "$OUT/cli_import_trace.py" "$OUT/logs/$1.imports.json" scout --mints $MINTS \
     --results $RESULTS --stage1 disc01 --report-dir "$OUT/reports" > "$OUT/logs/$1.stdout" 2> "$OUT/logs/$1.stderr")
  rc=$?
  echo "$1 export $2 exit $rc commit $(git -C "$SB" rev-parse --short HEAD) private_dir $([ -e "$SB/data/private" ] && echo yes || echo no)" >> "$OUT/logs/runs.txt"
  rm -rf "$OUT/runs/$1"; cp -r "$OUT/reports" "$OUT/runs/$1"; cp "$OUT/lab.sqlite" "$OUT/runs/$1/lab.sqlite"
  git -C "$SB" status --porcelain > "$OUT/logs/$1.git_status"
}

for E in $EXPORTS; do
  git -C "$REPO" show "$E:data/state/latest.json" > "$OUT/export_$E.json"
  sha256sum "$OUT/export_$E.json" >> "$OUT/logs/exports.sha256"
  for c in none malformed string_true section_true false one; do
    git -C "$SB" checkout -q "$BASE"; config "$c"; one_run "base_${c}_$E" "$E"
    git -C "$SB" checkout -q "$FROZEN"; config "$c"; one_run "frozen_${c}_$E" "$E"
  done
done
rm -f "$SB/data/config.json"
git -C "$REPO" status --porcelain > "$OUT/logs/checkout_git_status.txt"
echo done
