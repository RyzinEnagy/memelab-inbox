#!/usr/bin/env bash
# Phase 17 clean-install reproduction. Clones the committed branch into a temp dir, builds a fresh venv with the
# pinned test dependencies only, and runs: migration from empty, schema rollback, offline historical import, a
# deterministic backtest run twice, an opportunity report with adversarial scenarios, the disabled-feature check, the
# backtest tests and the release audit. No network except pip; no credentials are present in the clone.
# Usage: bash audits/backtesting/release/p17_clean_install.sh <repo path> <out dir>
set -u
REPO="$1"; OUT="$2"; mkdir -p "$OUT"
FAIL=0
ok() { local rc=$?; echo "exit $rc"; [ $rc -eq 0 ] || FAIL=1; }
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
step() { echo; echo "## $1"; }
{
step "environment"
uname -srm; python3 --version; python3 -c "import sqlite3; print('sqlite', sqlite3.sqlite_version)"
git clone -q "$REPO" "$W/clone" && cd "$W/clone" && git checkout -q feature/backtesting && echo "clone HEAD $(git rev-parse HEAD)"
echo "secrets in clone: $(ls data/private 2>/dev/null | wc -l) files under data/private; .env present: $(test -f .env && echo yes || echo no)"
python3 -m venv "$W/venv" && "$W/venv/bin/pip" install -q -r docs/backtesting/requirements-test.txt && echo "venv: $("$W/venv/bin/python" -m pytest --version) numpy $("$W/venv/bin/python" -c 'import numpy; print(numpy.__version__)')"
PY="$W/venv/bin/python"; DB="$W/bt/bt.sqlite"; mkdir -p "$W/bt"
export MEMELAB_BT_DB="$DB" MEMELAB_BT_RAW="$W/bt/raw" MEMELAB_HISTORY_REPO="$REPO"
LABDB_HASH_BEFORE=$(sha256sum data/memelab.sqlite | cut -c1-16)

step "1 migration from an empty research database"
$PY -m memelab backtest status --db "$DB"; ok

step "2 schema rollback and re-apply (bt tables only)"
$PY - "$DB" <<'PYX'
import sqlite3, sys
from memelab.backtest import schema, store
con = store.connect(sys.argv[1])
undone = schema.rollback(con, 0)
left = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'bt_%' AND name!='bt_schema_migrations'")]
redo = schema.migrate(con)
print({"rolled_back": undone, "bt_tables_left": left, "reapplied": redo})
PYX
ok

step "3 offline historical import (committed real GeckoTerminal responses)"
$PY audits/backtesting/release/p17_fixture_import.py "$DB"; ok
$PY -m memelab backtest data --db "$DB"; ok

step "4 deterministic backtest, run twice"
for i in 1 2; do $PY -m memelab backtest run --strategy BREAKOUT_CLOSE --params '{"lookback": 6, "vol_mult": 0.0}' --label p17 --db "$DB" > "$W/run$i.json"; ok; $PY -c "import json,sys; d=json.load(open(sys.argv[1])); print({k: d[k] for k in ('run_id','cache','dataset_hash','n_trades','ledger_hash')})" "$W/run$i.json"; done
$PY - "$W/run1.json" "$W/run2.json" <<'PYX'
import json, sys
a, b = (json.load(open(f)) for f in sys.argv[1:3])
same = a["run_id"] == b["run_id"] and a["ledger_hash"] == b["ledger_hash"]
print(f"same run id and ledger: {'yes' if same else 'NO'}; caches {a['cache']} then {b['cache']}")
sys.exit(0 if same and a["cache"] == "MISS" and b["cache"] == "HIT" else 1)
PYX
ok
RID=$($PY -m memelab backtest run --strategy BREAKOUT_CLOSE --params '{"lookback": 6, "vol_mult": 0.0}' --label p17 --db "$DB" | $PY -c "import json,sys; print(json.load(sys.stdin)['run_id'])")
$PY -m memelab backtest inspect "$RID" --db "$DB" > "$W/inspect.txt"; ok; head -5 "$W/inspect.txt"

step "5 opportunity report with adversarial scenarios (real PAID captures, judged at their own time)"
NOW=$($PY -c "
from memelab.bridge import ingest
from pathlib import Path
import datetime
t = max(ingest.load_result(Path('data/inbox')/f'{i}.result.json').observed_at for i in ('disc01','s2_01','deep01a'))
print(datetime.datetime.fromtimestamp(t + 60, datetime.timezone.utc).isoformat().replace('+00:00','Z'))")
$PY -m memelab backtest stress 98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump --results disc01 s2_01 deep01a --now "$NOW" --db "$DB" > "$W/report.md"; ok
grep -E "^# |^Label|^Decision|^- (BASE|LIQ_75|INSIDER_DUMP|COMBINED_WORST|HONEYPOT):" "$W/report.md"
echo "report sha256 $(sha256sum "$W/report.md" | cut -c1-16)"

step "6 disabled-feature rollback: analyze output with the policy off vs on (no persistence)"
MEMELAB_BACKTEST=0 $PY -m memelab analyze 98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump --results disc01 s2_01 deep01a --no-persist > "$W/off.txt"; ok
MEMELAB_BACKTEST=1 $PY -m memelab analyze 98kfF7rmsg1QDUEoCqNE7g7M1FdrTt92TEp2CLzypump --results disc01 s2_01 deep01a --no-persist > "$W/on.txt"; ok
diff "$W/off.txt" "$W/on.txt"; echo "diff lines above: only the one backtest line may appear (with the policy on)"
[ "$(diff "$W/off.txt" "$W/on.txt" | grep -c '^>')" -le 1 ] || { echo "UNEXPECTED analyze difference"; FAIL=1; }
if [ "$(sha256sum data/memelab.sqlite | cut -c1-16)" = "$LABDB_HASH_BEFORE" ]; then echo "lab database unchanged: yes"; else echo "lab database unchanged: NO"; FAIL=1; fi

step "7 backtest tests in the clean clone"
$PY -m pytest -q -p no:cacheprovider tests/test_backtest_*.py > "$W/pytest.txt" 2>&1; ok; tail -1 "$W/pytest.txt"

step "8 release audit in the clean clone"
$PY tools/release_audit.py > "$W/audit.txt" 2>&1; ok; grep -E "Needs action" "$W/audit.txt" | grep -q "Needs action: no" || FAIL=1; grep -E "Needs action" "$W/audit.txt"

step "9 release documents checked against code and evidence (reviewer's checker; runs in the source checkout, which holds the gitignored corpus)"
if [ -f "$REPO/data/backtest/bt.sqlite" ]; then cp "$REPO/data/backtest/bt.sqlite" "$W/corpus_copy.sqlite"; (cd "$REPO" && $PY audits/backtesting/testing/p17_doc_claims_check.py "$W/corpus_copy.sqlite") > "$W/claims.txt" 2>&1; ok; grep "^FAIL" "$W/claims.txt"; tail -1 "$W/claims.txt"; else echo "no research corpus on this machine: skipped"; fi

echo; echo "RESULT: $([ $FAIL -eq 0 ] && echo PASS || echo FAIL)"
exit $FAIL
} 2>&1 | tee "$OUT/p17_clean_install.log"
exit ${PIPESTATUS[0]}
