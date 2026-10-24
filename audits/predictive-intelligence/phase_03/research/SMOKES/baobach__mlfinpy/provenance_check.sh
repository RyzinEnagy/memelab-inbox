#!/usr/bin/env bash
# Provenance check: does mlfinpy (MIT, 2024) carry code from mlfinlab (BSD-3-Clause, 2019 Hudson and Thames)?
# Uses a public fork of the BSD-era mlfinlab (closedloop/mlfinlab), shallow clone in a scratch dir, deleted afterwards.
set -u
W=/tmp/claude-0/-home-claude/6c3ea1ef-d097-5873-a280-98af7bc5c45c/scratchpad/r2/prov
PIN=/home/claude/pi_research/src/baobach__mlfinpy
rm -rf "$W" && mkdir -p "$W" && cd "$W"
git clone -q --depth 1 https://github.com/closedloop/mlfinlab.git && cd mlfinlab || exit 1
echo "fork HEAD: $(git log -1 --format='%H %cI')"
echo "--- fork LICENSE (first 4 lines)"; head -4 LICENSE*
echo "--- mlfinpy LICENSE (first 4 lines)"; head -4 "$PIN/LICENSE"
echo "--- identical defect line"
grep -n "test_times = pd.Series(index=\[self.samples_info_sets" mlfinlab/cross_validation/cross_validation.py
grep -n "test_times = pd.Series" -A 2 "$PIN/mlfinpy/cross_validation/cross_validation.py"
echo "--- shared test docstring"
grep -c "This is how the observations dataset looks like" mlfinlab/tests/test_cross_validation.py "$PIN/tests/test_cross_validation.py"
python3 - "$PIN" <<'EOF'
import difflib, sys
pin = sys.argv[1]
pairs = [("mlfinlab/cross_validation/cross_validation.py", f"{pin}/mlfinpy/cross_validation/cross_validation.py"),
         ("mlfinlab/labeling/labeling.py", f"{pin}/mlfinpy/labeling/labeling.py"),
         ("mlfinlab/tests/test_cross_validation.py", f"{pin}/tests/test_cross_validation.py")]
for a, b in pairs:
    A = [l.strip() for l in open(a) if l.strip()]
    B = [l.strip() for l in open(b) if l.strip()]
    sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
    same = sum(bl.size for bl in sm.get_matching_blocks())
    print(f"{a}: {len(A)} vs {len(B)} non-blank lines; lines in matching blocks {same} ({same/len(B):.0%} of the mlfinpy file)")
EOF
grep -rn "Hudson\|hudson" "$PIN/LICENSE" "$PIN/mlfinpy" --include=*.py --include=LICENSE | head -5
echo "Hudson and Thames notices found in mlfinpy LICENSE or package code: $(grep -rln 'Hudson' "$PIN/LICENSE" "$PIN/mlfinpy" --include=*.py 2>/dev/null | wc -l)"
cd / && rm -rf "$W"
