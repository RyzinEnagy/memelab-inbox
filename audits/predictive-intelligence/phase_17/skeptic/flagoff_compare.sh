#!/usr/bin/env bash
# Phase 17 skeptic: flag-OFF byte identity, independent harness. Two clones (base b0fad12, head ea73cfb), same export,
# fresh DB per run, every lab command inside unshare -n. Captures stdout, stderr, every report file, full DB dump, git status.
set -u
SRC=/home/claude/pi_orchestration/skeptic_17
OUT=${1:-/home/claude/pi_orchestration/skeptic/p17/run}
BASE=b0fad12; HEAD_=ea73cfb
MINTS="98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump 6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx 7KEPApdbBMByrmqihz3bht2uMhFQcatjfSFQCKq66kH3 9XKzy4KahcZaGJPJtz1PtqGPB3CiseoBrx7TcQhEpump DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump HcRLc9VDgjLeK154xDawfb1dmVJ98DoSqcwTHGqiDeJR Hg5Ja55T5wESq4vyFoiVCMeHXtGyVA69X2UHq8hgpump 55Vr2VpSwxsDkB6uGGHAvRv86K6zax2Zb4TT8ivwDEzW"
PAID=98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump
RESULTS="disc01 s2_01 deep01a deep02 deep03 deep04 forensics01"
rm -rf "$OUT"; mkdir -p "$OUT"
git -C "$SRC" show 71fc50e:data/state/latest.json > "$OUT/export.json"
for v in base head base2 headbroken; do
  git clone -q "$SRC" "$OUT/$v"; c=$BASE; case $v in head|headbroken) c=$HEAD_;; esac; git -C "$OUT/$v" checkout -q $c
done
dumpdb() { python - "$1" > "$2" <<'PY'
import sqlite3,sys
con=sqlite3.connect(sys.argv[1])
for l in con.iterdump(): print(l)
PY
}
# run CASE VER CONFIGMODE CMD
run() {
  case_=$1; v=$2; cfg=$3; cmd=$4
  d="$OUT/res/$case_/$v"; mkdir -p "$d/reports"
  db="$OUT/db_${case_}_$v.sqlite"; rm -f "$db"*
  R="$OUT/$v"; rm -f "$R/data/config.json"
  case $cfg in
    none) ;;
    false) echo '{"predictive": {"enabled": false}}' > "$R/data/config.json" ;;
    strtrue) echo '{"predictive": {"enabled": "true"}}' > "$R/data/config.json" ;;
    malformed) echo '{"predictive": {"enabled": true' > "$R/data/config.json" ;;
    deep) python -c "print('{\"predictive\": {\"enabled\": false}, \"x\": ' + '['*100000 + ']'*100000 + '}')" > "$R/data/config.json" ;;
    on) printf '{"predictive": {"enabled": true, "state_dir": "%s"}}\n' "$OUT/state_${case_}_$v" > "$R/data/config.json" ;;
  esac
  (cd "$R" && MEMELAB_DB="$db" unshare -n python -B -m memelab init >/dev/null 2>&1 && MEMELAB_DB="$db" unshare -n python -B -m memelab.state import "$OUT/export.json" > /dev/null 2>&1)
  if [ "$cmd" = scout ]; then
    (cd "$R" && MEMELAB_DB="$db" unshare -n python -B -m memelab scout --mints $MINTS --results $RESULTS --stage1 disc01 --report-dir "$d/reports" > "$d/stdout" 2> "$d/stderr"); echo $? > "$d/exit"
  else
    (cd "$R" && MEMELAB_DB="$db" unshare -n python -B -m memelab analyze $PAID --results $RESULTS --stage1 disc01 > "$d/stdout" 2> "$d/stderr"); echo $? > "$d/exit"
    git -C "$R" status --porcelain > "$d/git_status"
    git -C "$R" diff --binary -- data/reports > "$d/analyze_report.diff"; git -C "$R" checkout -q -- data/reports; git -C "$R" clean -qfd data/reports
  fi
  sed -i "s#$OUT/res/$case_/$v#OUTDIR#g; s#$OUT/$v#REPO#g" "$d/stdout"
  dumpdb "$db" "$d/db.sql"
  git -C "$R" status --porcelain --ignored > "$d/git_status_all"
  rm -f "$R/data/config.json"
}
normrep() { for f in "$OUT"/res/$1/$2/reports/*; do [ -f "$f" ] && sed -i "s#$OUT/res/$1/$2#OUTDIR#g; s#$OUT/$2#REPO#g" "$f"; done; }
for c in none false strtrue malformed deep; do
  for v in base head; do run scout_$c $v $c scout; normrep scout_$c $v; run analyze_$c $v $c analyze; done
done
# noise floor: base twice
run scout_none base2 none scout; normrep scout_none base2; run analyze_none base2 none analyze
# P40: predictive package fails to import (head clone with a raising module), flag on and off
sed -i '1i raise RuntimeError("skeptic: predictive import broken")' "$OUT/headbroken/memelab/predictive/abstention.py"
for c in none on; do run scoutbroken_$c headbroken $c scout; normrep scoutbroken_$c headbroken; run analyzebroken_$c headbroken $c analyze; done
git -C "$OUT/headbroken" checkout -q -- memelab/predictive/abstention.py
echo done
