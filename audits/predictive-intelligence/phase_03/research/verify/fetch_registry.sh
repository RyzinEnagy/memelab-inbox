#!/usr/bin/env bash
# Phase 03 lead: free public fetches that back REJECT drivers. Downloads go to a scratch dir passed as $1 (never
# into the repo); only hashes, sizes and short quoted lines are written to registry/*.txt next to this script.
# Usage: bash fetch_registry.sh <scratch_dir>
set -euo pipefail
S="$1"; R="$(cd "$(dirname "$0")" && pwd)/registry"; mkdir -p "$S" "$R"
# 1. TabPFN weight licenses on Hugging Face (TP-1, TP-2)
curl -sS -L -o "$S/lic35.txt" https://huggingface.co/Prior-Labs/tabpfn_3_5/resolve/main/LICENSE
curl -sS -L -o "$S/lic2.txt" https://huggingface.co/Prior-Labs/TabPFN-v2-clf/resolve/main/LICENSE.txt
{
  echo "fetched_utc $(date -u +%FT%TZ)"
  echo "tabpfn_3_5_LICENSE url https://huggingface.co/Prior-Labs/tabpfn_3_5/resolve/main/LICENSE bytes $(wc -c < "$S/lic35.txt") sha256 $(sha256sum "$S/lic35.txt" | cut -d' ' -f1)"
  for p in "non-commercial and non-production" "Section 13 of the German Civil Code" "Outputs may be used only for Non-Commercial Purposes" "commercial decision-making"; do
    echo "tabpfn_3_5_contains '$p' $(grep -c -F "$p" "$S/lic35.txt")"; done
  echo "tabpfn_v2_clf_LICENSE url https://huggingface.co/Prior-Labs/TabPFN-v2-clf/resolve/main/LICENSE.txt bytes $(wc -c < "$S/lic2.txt") sha256 $(sha256sum "$S/lic2.txt" | cut -d' ' -f1)"
  for p in "Built with PriorLabs-TabPFN" "internal benchmarking and testing without external" "at the beginning of any such AI model name"; do
    echo "tabpfn_v2_contains '$p' $(grep -c -F "$p" "$S/lic2.txt")"; done
} > "$R/tabpfn_licenses.txt"
# 2. hazardous 0.2.0 wheel on PyPI (HZ-1)
curl -sS -o "$S/hz.json" https://pypi.org/pypi/hazardous/0.2.0/json
URL=$(python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print([u['url'] for u in d['urls'] if u['filename'].endswith('.whl')][0])" "$S/hz.json")
curl -sS -o "$S/hazardous-0.2.0-py3-none-any.whl" "$URL"
python3 - "$S/hazardous-0.2.0-py3-none-any.whl" > "$R/hazardous_0.2.0_wheel_listing.txt" <<'PY'
import hashlib, sys, zipfile
p = sys.argv[1]; z = zipfile.ZipFile(p)
print("fetched_from https://pypi.org/pypi/hazardous/0.2.0/json")
print("wheel_sha256", hashlib.sha256(open(p, "rb").read()).hexdigest())
for i in z.infolist():
    if i.file_size > 100000 or ".DS_Store" in i.filename or "checkpoint" in i.filename or "_negative_log_likelihood" in i.filename:
        print(i.filename, i.file_size)
PY
# 3. mlfinlab BSD-3 fork used for the provenance check (MF-2)
F="$S/mlfinlab_fork"; rm -rf "$F"; mkdir -p "$F"; git -C "$F" init -q
git -C "$F" fetch -q --depth 1 https://github.com/closedloop/mlfinlab.git 47889b884c7e7e4ca850ce2b87ea1514e0834866; git -C "$F" checkout -q FETCH_HEAD
M=/home/claude/pi_research/src/baobach__mlfinpy
{
  echo "fork_head $(git -C "$F" rev-parse HEAD)"
  LF=$(ls "$F"/LICENSE* | head -1); echo "fork_license_file $(basename "$LF") bsd3_hudson $(grep -q 'Hudson and Thames' "$LF" && head -1 "$LF" | grep -q 'BSD 3-Clause' && echo True || echo False)"
  echo "fork_line_91_defect $(sed -n 91p "$F/mlfinlab/cross_validation/cross_validation.py" | grep -q 'index=\[self.samples_info_sets\[start_ix\]\]' && echo True || echo False)"
  echo "mlfinpy_line_122_124 $(sed -n 122,124p "$M/mlfinpy/cross_validation/cross_validation.py" | tr -s ' ' | tr '\n' ' ')"
  echo "mlfinpy_hudson_notices $(grep -rli 'hudson' "$M/LICENSE" "$M/mlfinpy" | wc -l)"
  echo "shared_test_docstring $(grep -q 'This is how the observations dataset looks like' "$F/mlfinlab/tests/test_cross_validation.py" && grep -q 'This is how the observations dataset looks like' "$M/tests/test_cross_validation.py" && echo True || echo False)"
} > "$(dirname "$R")/rerun_mlfinpy_provenance.out.txt"
echo done
