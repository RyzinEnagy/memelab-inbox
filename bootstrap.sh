#!/bin/bash
# Rebuild the memelab project from the public repo (fresh-session bootstrap). Usage: bash bootstrap.sh <dest>
set -e
DEST=${1:-memelab}; BASE="https://raw.githubusercontent.com/RyzinEnagy/memelab-inbox/main"
mkdir -p "$DEST"; cd "$DEST"
FILES=$(curl -sS "https://api.github.com/repos/RyzinEnagy/memelab-inbox/git/trees/main?recursive=1" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(t['path'] for t in d.get('tree',[]) if t['type']=='blob'))" 2>/dev/null || true)
if [ -z "$FILES" ]; then
  # api.github.com blocked from the sandbox: fall back to the manifest committed in the repo
  FILES=$(curl -sS "$BASE/MANIFEST.txt?x=$RANDOM")
fi
for f in $FILES; do case "$f" in inbox/*|bridge/*) continue;; esac; mkdir -p "$(dirname "$f")"; curl -sS -o "$f" "$BASE/$f?x=$RANDOM"; done
echo "fetched $(echo "$FILES" | wc -l) files into $DEST"
