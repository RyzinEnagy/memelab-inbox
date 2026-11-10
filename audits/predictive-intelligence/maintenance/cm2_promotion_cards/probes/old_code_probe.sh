#!/usr/bin/env bash
# CM-2 G4: the CM-2 tests at HEAD run against the code before CM-2 (ed85b2c: change control and recipe only). Usage:
# old_code_probe.sh <repo> <out_dir>. Writes only into <out_dir>. Expect failures: contract pin, training splits, promotion
# (module absent), daily (script absent).
set -u
REPO="$1"; OUT="$2"; rm -rf "$OUT"; mkdir -p "$OUT"; C="$OUT/old"
git clone -q --no-local "$REPO" "$C" && git -C "$C" checkout -q ed85b2c
for t in tests/test_predictive_contract.py tests/test_predictive_labels.py tests/test_predictive_promotion.py tests/test_predictive_daily.py; do
  cp "$REPO/$t" "$C/$t"
  ( cd "$C" && python3 -m pytest -q -p no:cacheprovider "$t" 2>&1 | tail -1 ) > "$OUT/$(basename $t .py).txt"
  echo "$t: $(cat "$OUT/$(basename $t .py).txt")"
done
