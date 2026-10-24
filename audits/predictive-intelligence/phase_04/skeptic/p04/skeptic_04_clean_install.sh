#!/bin/bash
# Skeptic 04: clean-venv INSTALL of the research lock (offline, lab flags), smoke, uninstall, compare manifests.
# usage: skeptic_04_clean_install.sh REPO WHEELHOUSE WORKDIR
set -u
REPO=$1; WH=$2; W=$3
rm -rf "$W"; mkdir -p "$W"; python3 -m venv "$W/v"; PY="$W/v/bin/python"
SP=$($PY -c "import sysconfig;print(sysconfig.get_paths()['purelib'])")
manifest() { (cd "$SP" && find . -type f -not -path '*/__pycache__/*' | sort | xargs sha256sum) | sha256sum | cut -c1-16; }
echo "pip: $($PY -m pip --version | cut -d' ' -f1,2)"
B_FREEZE=$($PY -m pip freeze --all | sha256sum | cut -c1-16); B_MAN=$(manifest)
T0=$(date +%s.%N)
unshare -n $PY -m pip --disable-pip-version-check install --require-hashes --only-binary=:all: --no-deps --no-index --find-links "$WH" -r "$REPO/docs/predictive-intelligence/locks/research-py313.txt" > "$W/install.log" 2>&1; echo "install exit $? in $(echo "$(date +%s.%N) - $T0" | bc) s"
tail -1 "$W/install.log" | cut -c1-200
$PY -m pip list --format=freeze 2>/dev/null | grep -vE "^(pip|setuptools)==" | wc -l | sed 's/^/installed packages: /'
unshare -n $PY -I -B -c "
import numpy as np, sklearn, lightgbm, lifelines, river, purgedcv, mapie
from sklearn.linear_model import LogisticRegression
X=np.random.default_rng(0).normal(size=(200,3)); y=(X[:,0]>0).astype(int)
p=LogisticRegression().fit(X,y).predict_proba(X)[:,1]
m=lightgbm.LGBMClassifier(n_estimators=10,deterministic=True,num_threads=1,verbose=-1,force_row_wise=True).fit(X,y)
print('smoke ok', sklearn.__version__, lightgbm.__version__, round(float(p.mean()),6), round(float(m.predict_proba(X)[:,1].mean()),6))
"; echo "smoke exit $?"
$PY -m pip check 2>&1 | head -3
$PY -m pip uninstall -y $(grep -E "^[a-z]" "$REPO/docs/predictive-intelligence/locks/research-py313.txt" | cut -d= -f1) > "$W/uninstall.log" 2>&1; echo "uninstall exit $?"
A_FREEZE=$($PY -m pip freeze --all | sha256sum | cut -c1-16); A_MAN=$(manifest)
echo "freeze before $B_FREEZE after $A_FREEZE; site-packages manifest before $B_MAN after $A_MAN"
(cd "$SP" && find . -mindepth 1 -maxdepth 1 | sort) > "$W/after_top.txt"; echo "top-level entries after uninstall:"; cat "$W/after_top.txt" | tr '\n' ' '; echo
# lock hashes against the wheelhouse files
python3 - "$REPO/docs/predictive-intelligence/locks/research-py313.txt" "$WH" <<'PY'
import hashlib,re,sys,pathlib
lock=set(re.findall(r"sha256:([0-9a-f]{64})",open(sys.argv[1]).read()))
whs={hashlib.sha256(p.read_bytes()).hexdigest():p.name for p in pathlib.Path(sys.argv[2]).glob("*.whl")}
print("wheelhouse files whose sha256 is in the lock:",sum(h in lock for h in whs),"of",len(whs))
PY
