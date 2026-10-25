#!/usr/bin/env bash
# Hourly shadow tracking for the backtesting module, approved by Elving on 2026-10-24 (D-BT-033).
# Runs on Elving's computer through the scheduled task "Memelab backtest hourly tracking", one step per call:
#   bash hourly_shadow.sh setup     python 3.13 venv, code from code.bundle, working copy of the database
#   bash hourly_shadow.sh refresh   backtest refresh: GeckoTerminal only, read-only, at most 12 calls, 3 s apart (about 95 s)
#   bash hourly_shadow.sh collect   backtest depth collect (D-BT-034): the lab's exports of the last 72 h from the public
#                                   GitHub repository (shallow git fetch), then pool reserves (GeckoTerminal, at most 6
#                                   calls, 10 s apart) and keyless Jupiter sell quotes (at most 40, 2.5 s apart) for
#                                   decisions of the last 24 h; no new call after 100 s (about 110 s at most)
#   bash hourly_shadow.sh track     backtest outcomes track (no network)
#   bash hourly_shadow.sh save      WAL-safe backup, integrity check, write back, one log line
#   bash hourly_shadow.sh status    last log lines and the store state
# The persistent store is D:\memelab\backtesting_live (bt.sqlite, raw/, code.bundle, hourly.log). Work happens in a
# session-local copy, so a failed or interrupted run never touches the stored database. No credentials are used.
# If the GitHub fetch fails, collect still runs for the decisions already stored (it prints EXPORTS_NOT_FETCHED).
set -u
L="$HOME/mnt/memelab/backtesting_live"
W="$HOME/bt_hourly"
LAB_REPO="https://github.com/RyzinEnagy/memelab-inbox.git"
LOG="$L/hourly.log"
STATE="$L/hourly.state"
PY="$W/venv/bin/python"
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
fail() { echo "FAILED: $1"; printf '{"t": "%s", "step": "%s", "result": "FAILED", "detail": "%s"}\n' "$(now)" "$STEP" "$1" >> "$LOG"; echo "idle $(now) after failure" > "$STATE"; exit 1; }
STEP="${1:-}"
case "$STEP" in
setup)
  [ -f "$L/bt.sqlite" ] && [ -f "$L/code.bundle" ] || fail "store missing in $L"
  if [ -f "$STATE" ] && grep -q '^running' "$STATE"; then
    started=$(date -u -d "$(cut -d' ' -f2 "$STATE")" +%s 2>/dev/null || echo 0)
    [ $(( $(date -u +%s) - started )) -lt 2700 ] && { echo "SKIPPED: another run started at $(cut -d' ' -f2 "$STATE")"; exit 2; }
  fi
  echo "running $(now)" > "$STATE"
  rm -rf "$W"; mkdir -p "$W/raw"
  uv python install 3.13 >/dev/null 2>&1 || fail "uv python install"
  uv venv -q --python 3.13 "$W/venv" >/dev/null 2>&1 || fail "uv venv"
  uv pip install -q --python "$PY" numpy==2.5.3 >/dev/null 2>&1 || fail "numpy install"
  git clone -q -b feature/backtesting "$L/code.bundle" "$W/repo" || fail "clone from code.bundle"
  cp "$L/bt.sqlite" "$W/bt.sqlite" || fail "copy database in"
  [ "$("$PY" -c "import sqlite3,sys; print(sqlite3.connect(sys.argv[1]).execute('PRAGMA quick_check').fetchone()[0])" "$W/bt.sqlite")" = ok ] || fail "working copy failed quick_check"
  echo "setup ok: code $(git -C "$W/repo" rev-parse --short HEAD), python $("$PY" -V 2>&1 | cut -d' ' -f2)"
  ;;
refresh)
  cd "$W/repo" || fail "no working copy; run setup first"
  MEMELAB_BT_RAW="$W/raw" "$PY" -m memelab backtest refresh --max-calls 12 --spacing 3 --db "$W/bt.sqlite" > "$W/refresh.json" 2> "$W/refresh.err" || fail "backtest refresh exit $?"
  tail -c 600 "$W/refresh.json"; echo
  ;;
collect)
  cd "$W/repo" || fail "no working copy; run setup first"
  rm -rf "$W/lab.git"; git init -q --bare "$W/lab.git" || fail "git init for the lab exports"
  T=""; command -v timeout >/dev/null 2>&1 && T="timeout"
  since=$(date -u -d '-72 hours' +%Y-%m-%dT%H:%M:%SZ)
  REPO_ARGS=(--repo "$W/lab.git")
  GIT_TERMINAL_PROMPT=0 ${T:+$T 60} git -C "$W/lab.git" fetch -q --shallow-since="$since" "$LAB_REPO" +refs/heads/main:refs/remotes/origin/main > "$W/fetch.err" 2>&1 \
    || { echo "EXPORTS_NOT_FETCHED: git fetch exit $?; collecting for stored decisions only"; REPO_ARGS=(); }
  MEMELAB_BT_RAW="$W/raw" ${T:+$T 160} "$PY" -m memelab backtest depth collect ${REPO_ARGS[@]+"${REPO_ARGS[@]}"} --db "$W/bt.sqlite" > "$W/collect.json" 2> "$W/collect.err" || fail "depth collect exit $?"
  tail -c 600 "$W/collect.json"; echo
  ;;
track)
  cd "$W/repo" || fail "no working copy; run setup first"
  MEMELAB_BT_RAW="$W/raw" "$PY" -m memelab backtest outcomes track --min-interval 1800 --db "$W/bt.sqlite" > "$W/track.json" 2> "$W/track.err" || fail "outcomes track exit $?"
  tail -c 600 "$W/track.json"; echo
  ;;
save)
  cd "$W/repo" || fail "no working copy; run setup first"
  rm -f "$W/out.sqlite"
  "$PY" -m memelab backtest backup --db "$W/bt.sqlite" --to "$W/out.sqlite" > /dev/null 2>&1 || fail "backup"
  [ "$("$PY" -c "import sqlite3,sys; print(sqlite3.connect(sys.argv[1]).execute('PRAGMA integrity_check').fetchone()[0])" "$W/out.sqlite")" = ok ] || fail "new copy failed integrity_check"
  cp "$W/out.sqlite" "$L/bt.sqlite.new" || fail "write bt.sqlite.new"
  [ "$(sha256sum < "$W/out.sqlite")" = "$(sha256sum < "$L/bt.sqlite.new")" ] || fail "bt.sqlite.new differs after copy"
  mv -f "$L/bt.sqlite.new" "$L/bt.sqlite" 2>/dev/null || cp "$L/bt.sqlite.new" "$L/bt.sqlite" || fail "replace bt.sqlite"
  [ "$(sha256sum < "$W/out.sqlite")" = "$(sha256sum < "$L/bt.sqlite")" ] || fail "bt.sqlite differs after replace"
  mkdir -p "$L/raw"; cp -rn "$W/raw/." "$L/raw/" 2>/dev/null
  "$PY" - "$W" "$(now)" >> "$LOG" <<'PYX'
import json, sys
w, t = sys.argv[1], sys.argv[2]
def tail(name):
    try:
        return json.loads(open(f"{w}/{name}").read())
    except Exception as e:
        return {"unparsed": str(e)[:80]}
r, k, c = tail("refresh.json"), tail("track.json"), tail("collect.json")
keep = lambda d, ks: {x: d.get(x) for x in ks if x in d}
print(json.dumps({"t": t, "step": "save", "result": "OK", "refresh": r if len(json.dumps(r)) < 400 else keep(r, ("pools_wanted", "calls", "status")), "collect": keep(c, ("decisions_new", "pools_active", "pool_snapshots", "quotes", "quote_source", "calls", "deadline_hit", "wall_s", "unparsed")),
                  "track": keep(k, ("status", "opportunities", "states", "new_rows", "fetched"))}))
PYX
  echo "idle $(now)" > "$STATE"
  tail -1 "$LOG"
  ;;
status)
  cat "$STATE" 2>/dev/null; tail -3 "$LOG" 2>/dev/null; ls -la "$L/bt.sqlite"
  ;;
*)
  echo "usage: bash hourly_shadow.sh setup|refresh|collect|track|save|status"; exit 64
  ;;
esac
