#!/bin/bash
# Phase 16 before/after regression matrix. Runs the lab's analyze, scout and social-alert demo in throwaway local
# clones (base f99c6c7 and HEAD), each with its own temp copy of the tracked lab database, with the backtest policy
# off and on. Never writes to the working copy's data/ files. Usage: bash p16_regression.sh <scratch dir> <repo>
set -u
SCR="$1"; REPO="$2"
PAID=98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump
STONK=6GmAFSYs4gk3FDao5FzzySQpPZaWsa4rUJHacpMpUNgx
HIGGS=DoVAVzViX8Bjy3r15nwikSaSbzE6dV4ovd28aWpJpump
ZCAT=HcRLc9VDgjLeK154xDawfb1dmVJ98DoSqcwTHGqiDeJR
rm -rf "$SCR/reg"; mkdir -p "$SCR/reg"
git clone -q --local "$REPO" "$SCR/reg/head" && git -C "$SCR/reg/head" checkout -q feature/backtesting
git clone -q --local "$REPO" "$SCR/reg/base" && git -C "$SCR/reg/base" checkout -q f99c6c7
for side in base head; do
  for mode in off on; do
    W="$SCR/reg/$side"; O="$SCR/reg/out_${side}_${mode}"; mkdir -p "$O/reports"
    cp "$W/data/memelab.sqlite" "$O/lab.sqlite"
    [ "$mode" = on ] && cp "$SCR/corpus/bt.sqlite" "$O/bt.sqlite"
    export MEMELAB_DB="$O/lab.sqlite" MEMELAB_ALERT_DB="$O/alerts.sqlite" MEMELAB_ALERT_CONFIG="$O/alerts.json" MEMELAB_BT_DB="$O/bt.sqlite"
    export MEMELAB_BACKTEST=$([ "$mode" = on ] && echo 1 || echo 0)
    R="disc01 s2_01 deep01a deep02"
    ( cd "$W" && python3 -m memelab analyze $PAID --results $R --no-persist ) > "$O/analyze.txt" 2>&1; echo "analyze exit $?" >> "$O/exits.txt"
    ( cd "$W" && python3 -m memelab scout --mints $PAID $STONK $HIGGS $ZCAT --results $R --report-dir "$O/reports" ) > "$O/scout.txt" 2>&1; echo "scout exit $?" >> "$O/exits.txt"
    ( cd "$W" && python3 -m memelab social alerts demo --fixture tests/fixtures/social/alerts/alerts_day.json ) > "$O/alerts.txt" 2>&1; echo "alerts exit $?" >> "$O/exits.txt"
    ls "$O/reports" > "$O/report_files.txt"
    sha256sum "$O/lab.sqlite" | cut -c1-64 > "$O/lab_sha.txt"
    [ -f "$O/bt.sqlite" ] && echo "bt db present" >> "$O/exits.txt" || echo "bt db absent" >> "$O/exits.txt"
  done
done
unset MEMELAB_DB MEMELAB_ALERT_DB MEMELAB_ALERT_CONFIG MEMELAB_BT_DB MEMELAB_BACKTEST
cd "$SCR/reg"
for f in analyze.txt scout.txt alerts.txt report_files.txt exits.txt; do
  echo "=== $f: base_off vs head_off"; diff <(sed -E 's#'"$SCR"'/reg/out_[a-z]+_[a-z]+#OUT#g' out_base_off/$f) <(sed -E 's#'"$SCR"'/reg/out_[a-z]+_[a-z]+#OUT#g' out_head_off/$f) && echo IDENTICAL
  echo "=== $f: base_on vs base_off (policy has no effect at base)"; diff -q out_base_on/$f out_base_off/$f >/dev/null && echo IDENTICAL || diff <(sed -E 's#'"$SCR"'/reg/out_[a-z]+_[a-z]+#OUT#g' out_base_off/$f) <(sed -E 's#'"$SCR"'/reg/out_[a-z]+_[a-z]+#OUT#g' out_base_on/$f) | head -20
  echo "=== $f: head_off vs head_on"; diff <(sed -E 's#'"$SCR"'/reg/out_[a-z]+_[a-z]+#OUT#g' out_head_off/$f) <(sed -E 's#'"$SCR"'/reg/out_[a-z]+_[a-z]+#OUT#g' out_head_on/$f) | head -60
done
for x in base_off base_on head_off head_on; do
  echo "=== scout report bodies $x"; for r in out_$x/reports/*_SCOUT.md; do sha256sum "$r" | cut -c1-16; done
done
echo "=== scout report: head_off vs head_on (body diff)"
diff <(cat out_head_off/reports/*_SCOUT.md) <(cat out_head_on/reports/*_SCOUT.md) | head -40
echo "=== per-token report files written with the policy on"
ls out_head_on/reports | grep -c backtest
