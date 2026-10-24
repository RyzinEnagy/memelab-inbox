# Phase 03 reviewer R1: fetch TabPFN v2 classifier weights through TabPFN's own download path, logging
# every host contacted (network allowed in this step only). v2 weights: Prior Labs License v1.1
# (Apache 2.0 plus an attribution clause). The default v3.5 weights are NOT fetched (non-commercial terms).
# Usage: TABPFN_MODEL_CACHE_DIR=<dir> python -I tabpfn_fetch_v2.py
import hashlib
import json
import os
import socket
import time

HOSTS = []
_orig_gai = socket.getaddrinfo


def _log_gai(host, *a, **k):
    HOSTS.append(str(host))
    return _orig_gai(host, *a, **k)


socket.getaddrinfo = _log_gai

from tabpfn.constants import ModelVersion  # noqa: E402
from tabpfn.model_loading import ModelSource, download_model, get_cache_dir  # noqa: E402

cache = get_cache_dir()
src = ModelSource.get_classifier_v2()
target = cache / src.default_filename
t = time.perf_counter()
res = download_model(target, version=ModelVersion.V2, which="classifier")
elapsed = time.perf_counter() - t
out = {"result": res if res == "ok" else [repr(e)[:300] for e in res], "seconds": round(elapsed, 2),
       "cache_dir": str(cache), "file": src.default_filename, "repo_id": src.repo_id,
       "hosts_resolved": sorted(set(HOSTS)), "files_in_cache": sorted(os.listdir(cache))}
if target.exists():
    h = hashlib.sha256(target.read_bytes()).hexdigest()
    out.update({"bytes": target.stat().st_size, "sha256": h})
print("FETCH_JSON " + json.dumps(out, sort_keys=True))
