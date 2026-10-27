#!/usr/bin/env bash
# flag ON: body unchanged, lab tables unchanged, storms; reuses clones from flagoff_compare.sh
set -u
OUT=/home/claude/pi_orchestration/skeptic/p17/run
source <(sed -n '/^dumpdb()/,/^}/p; /^MINTS=/p; /^PAID=/p; /^RESULTS=/p' /home/claude/pi_orchestration/skeptic/p17/flagoff_compare.sh)
R=$OUT/head; S=$OUT/onstate; rm -rf $S $OUT/on; mkdir -p $OUT/on
db=$OUT/on/lab.sqlite
printf '{"predictive": {"enabled": true, "state_dir": "%s"}}\n' "$S" > $R/data/config.json
(cd $R && MEMELAB_DB=$db unshare -n python -B -m memelab init >/dev/null && MEMELAB_DB=$db unshare -n python -B -m memelab.state import $OUT/export.json >/dev/null)
sc() { mkdir -p $OUT/on/$1; s0=$(date +%s.%N); ( cd $R && MEMELAB_DB=$db unshare -n python -B -m memelab scout --mints $2 --results $RESULTS --stage1 disc01 --report-dir $OUT/on/$1 > $OUT/on/$1/stdout 2> $OUT/on/$1/stderr ); echo $? > $OUT/on/$1/exit; echo "$(date +%s.%N) - $s0" | bc > $OUT/on/$1/time; }
sc first "$MINTS"
cp $db $OUT/on/after_first.sqlite
sc rerun "$MINTS"
sc storm "$PAID $PAID $PAID $PAID $PAID $PAID $MINTS $MINTS"
for i in 1 2 3 4 5; do sc storm$i "$MINTS"; done
rm -f $R/data/config.json
(cd $R && unshare -n python -B -m memelab.predictive.integration status --state-dir $S > $OUT/on/status.json; unshare -n python -B -m memelab.predictive.integration check --state-dir $S > $OUT/on/check.json; echo "check exit $?" >> $OUT/on/check.json)
git -C $R status --porcelain --ignored > $OUT/on/git_status
echo done
