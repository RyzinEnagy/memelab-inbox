#!/usr/bin/env bash
# Phase 03 lead: build the blind rescore working copy for the second reviewer. Copies only the seven packet
# repositories' reviews (with section 6, the original reviewer's proposed scores, removed) and smoke folders, the
# challenge, the lead's re-execution outputs that are evidence (no scores), and the locked rubric. Never copies
# SCORECARD.csv, SCORE_ITEMS.csv, RUBRIC_ITEMS.csv, RANKED_TOP10.md, CATEGORY_WINNERS.md, sensitivity output or records.
# Usage: bash make_blind_copy.sh <target_dir>   (target outside the repository)
set -euo pipefail
T="$1"; R="$(cd "$(dirname "$0")/.." && pwd)"
PKG=/mnt/user-data/uploads/Memecoin_Predictive_Intelligence_Engine_Prompt_Package
REPOS="eslazarev__purged-cross-validation interpretml__interpret online-ml__river scikit-learn-contrib__MAPIE scikit-learn__scikit-learn soda-inria__hazardous statsmodels__statsmodels"
mkdir -p "$T/REVIEWS" "$T/SMOKES" "$T/evidence"
for r in $REPOS; do
  python3 - "$R/REVIEWS/$r.md" "$T/REVIEWS/$r.md" <<'PY'
import re, sys
t = open(sys.argv[1], encoding="utf-8").read()
a = t.index("## 6"); b = t.index("## 7")
open(sys.argv[2], "w", encoding="utf-8").write(t[:a] + "## 6. Proposed rubric scores\n\n(removed for the blind rescore)\n\n" + t[b:])
PY
  cp -r "$R/SMOKES/$r" "$T/SMOKES/"
done
cp -r "$R/SMOKES/_challenge" "$T/SMOKES/"
cp "$R/verify/VERIFY_RESULTS.json" "$R/verify/VERIFY_GENERIC.json" "$R/verify/pypi_wheels.json" "$R/verify/repeat_runs.json" "$R"/verify/rerun_*.out.txt "$T/evidence/"
cp "$PKG/references/GRADING_RUBRIC.md" "$PKG/phases/PHASE_03_pinned_source_audit_rubric_and_ranked_top_ten.md" "$T/"
echo "blind copy at $T"
