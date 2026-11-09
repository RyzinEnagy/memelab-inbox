#!/usr/bin/env bash
# Phase 21: the release checks, run from a fresh clone of the pushed branch. Research only.
#
#   bash release_checks.sh PUSHED_HEAD FROZEN_COMMIT OUTDIR
#
# 1. Network part (the only one): `git ls-remote` and a fresh `git clone` of https://github.com/RyzinEnagy/memelab-inbox.git,
#    branch feature/predictive-intelligence, which must be at PUSHED_HEAD; then the local Phase 21 commit FROZEN_COMMIT (a
#    descendant of PUSHED_HEAD that adds only files under audits/predictive-intelligence/phase_21/) is fetched from this checkout
#    and fast-forwarded, so the probes below exist in the clone; the changed paths are recorded. A new virtual environment
#    (no system site packages) gets only numpy and pytest at the baseline versions from PyPI.
# 2. Every check after that runs in the clone with the venv's python first on PATH, under `env -i` (no credential, token or proxy
#    variable reaches it) and, where a lab or test command runs, inside `unshare -n` (no network; loopback raised by lo_up.py for
#    the Phase 14 tests, finding F20-11). Each step is timed by measure.py (wall seconds, peak memory of its children).
# Nothing is written in this checkout; everything is under OUTDIR.
set -u
PUSHED="$1"
LOCAL0="$(cd "$(dirname "$0")/../../../.." && pwd)"
FROZEN="$(git -C "$LOCAL0" rev-parse --verify "$2^{commit}")" || { echo "cannot resolve $2" >&2; exit 2; }   # a full sha: git fetch by short sha fails
OUT="$3"
LOCAL="$(cd "$(dirname "$0")/../../../.." && pwd)"
URL=https://github.com/RyzinEnagy/memelab-inbox.git
BR=feature/predictive-intelligence
A=audits/predictive-intelligence
mkdir -p "$OUT/logs"
: > "$OUT/logs/steps.jsonl"
log() { echo "$(date -u +%FT%TZ) $*" >> "$OUT/logs/release_checks.txt"; }
: > "$OUT/logs/release_checks.txt"

# ---- 1. fresh clone of the pushed branch, fresh venv
git ls-remote "$URL" "refs/heads/$BR" > "$OUT/logs/ls_remote.txt" 2>&1
log "ls-remote exit $? $(cat "$OUT/logs/ls_remote.txt")"
rm -rf "$OUT/clone" "$OUT/venv"
git clone -q "$URL" "$OUT/clone"
log "clone exit $?"
C="$OUT/clone"
git -C "$C" checkout -q "$BR"
GOT="$(git -C "$C" rev-parse HEAD)"
log "clone HEAD $GOT expected $PUSHED"
[ "$GOT" = "$(git -C "$LOCAL" rev-parse "$PUSHED")" ] || { log "STOP: the remote branch is not at the pushed head"; exit 3; }
git -C "$C" fetch -q "$LOCAL" "$FROZEN" || { log "STOP: fetch of $FROZEN failed"; exit 3; }
git -C "$C" merge -q --ff-only FETCH_HEAD || { log "STOP: not a fast-forward"; exit 3; }
log "fast-forward to $(git -C "$C" rev-parse HEAD)"
[ "$(git -C "$C" rev-parse HEAD)" = "$FROZEN" ] || { log "STOP: clone not at $FROZEN"; exit 3; }
git -C "$C" diff --name-only "$GOT" HEAD > "$OUT/logs/changed_since_pushed.txt"
log "paths changed since the pushed head: $(wc -l < "$OUT/logs/changed_since_pushed.txt"), outside phase_21: $(grep -vc "^$A/phase_21/" "$OUT/logs/changed_since_pushed.txt")"
git -C "$C" log -1 --format=%cI origin/main > "$OUT/logs/origin_main_date.txt"
python3 -m venv "$OUT/venv"
"$OUT/venv/bin/python" -m pip install -q --disable-pip-version-check numpy==2.5.3 pytest==9.1.1 iniconfig==2.3.1 pluggy==1.7.0 \
  packaging==26.3 > "$OUT/logs/pip.txt" 2>&1
log "pip exit $?"
"$OUT/venv/bin/python" -m pip freeze > "$OUT/logs/pip_freeze.txt"
cp "$OUT/venv/pyvenv.cfg" "$OUT/logs/pyvenv.cfg"
"$OUT/venv/bin/python" -c "import sys; print('python', sys.version.split()[0], 'in_venv', sys.prefix != sys.base_prefix)" > "$OUT/logs/venv.txt"

# ---- 2. checks (no network, no credentials)
E="env -i HOME=/root PATH=$OUT/venv/bin:/usr/sbin:/usr/bin:/sbin:/bin LANG=C.UTF-8 LC_ALL=C.UTF-8 MEMELAB_RELEASE_CHECK=1"
M="$OUT/venv/bin/python -B $C/$A/phase_21/probes/measure.py $OUT/logs/steps.jsonl"
LO="python -B $A/phase_20/probes/lo_up.py"
cd "$C"
$E env | sort | sed 's/=.*//' > "$OUT/logs/env_names_inside.txt"
strays() { git -C "$C" status --porcelain >> "$OUT/logs/strays_seen.txt"; git -C "$C" clean -fq data/reports; rm -f "$C/data/memelab.sqlite-shm" "$C/data/memelab.sqlite-wal"; }

$M suite_full "$OUT/suite_full.txt" -- $E unshare -n sh -c "$LO && python -m pytest tests -q -p no:cacheprovider"
strays
$M suite_predictive_no_private_stores "$OUT/suite_predictive_no_stores.txt" -- $E unshare -m -n sh -c \
  "mount -t tmpfs tmpfs /home/claude/pi_research && $LO && python -m pytest -q -p no:cacheprovider -rs tests/test_predictive_*.py"
strays
$M cross_component "$OUT/cross_component.txt" -- $E unshare -n sh -c "$LO && python -m pytest -q -p no:cacheprovider tests/test_predictive_phase20_cross.py"
strays
$M seal_check "$OUT/seal_check.json" -- $E unshare -n python -B $A/phase_06/probes/check_seal.py
$M social_guard "$OUT/social_guard.txt" -- $E unshare -n python -m memelab social guard
$M chronology_audit "$OUT/chronology_audit.stdout" -- $E unshare -n python -B $A/phase_21/probes/chronology_audit.py 2026-11-09T00:00:00Z "$OUT/chronology_audit.json"
mkdir -p "$OUT/p19_audit"
$M p19_feedback_audit "$OUT/p19_audit.stdout" -- $E unshare -n python -B $A/phase_19/probes/run_prospective.py audit "$OUT/p19_audit"
$M scenario_matrix "$OUT/matrix.stdout" -- $E unshare -n sh -c "$LO && python -B $A/phase_20/probes/run_matrix.py '$OUT/matrix'"
strays
$M counterexamples "$OUT/cx.stdout" -- $E unshare -n sh -c "$LO && python -B $A/phase_20/probes/cx_rerun.py '$OUT/cx'"
strays
$M oos_sensitivity "$OUT/oos.stdout" -- $E unshare -n python -B $A/phase_20/probes/oos_sensitivity.py "$OUT/oos_sensitivity.json"
$M independent_recalc "$OUT/recalc.stdout" -- $E unshare -n python -B $A/phase_20/probes/recalc.py "$OUT/independent_recalc.json"
$M threat_scan "$OUT/threat.stdout" -- $E unshare -n python -B $A/phase_20/probes/threat_scan.py "$OUT/threat_scan.json"
$M e2e "$OUT/e2e.stdout" -- $E bash $A/phase_20/probes/e2e.sh "$(git rev-parse HEAD)" "$OUT/e2e"
$M flag_off_identity "$OUT/flagoff.stdout" -- $E bash $A/phase_20/probes/flag_off_identity.sh "$(git rev-parse HEAD)" "$OUT/flagoff"
$M flag_off_summary "$OUT/flagoff_summary.stdout" -- $E python -B $A/phase_20/probes/flag_off_summary.py "$OUT/flagoff" "$OUT/flag_off_identity.json"
$M reproductions "$OUT/reproductions.stdout" -- $E python -B $A/phase_20/probes/reproductions.py "$(git rev-parse HEAD)" "$OUT/reproductions.json"
strays
git -C "$C" status --porcelain > "$OUT/logs/clone_status_end.txt"
git -C "$LOCAL" status --porcelain > "$OUT/logs/checkout_status_end.txt"
log "done"
cat "$OUT/logs/steps.jsonl"
