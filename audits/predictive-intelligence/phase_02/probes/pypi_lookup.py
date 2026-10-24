"""Look up PyPI packages through the public JSON API (https://pypi.org/pypi/<name>/json).

Usage:
  python pypi_lookup.py OUT_JSONL RAW_DIR NAME [NAME ...]

Records per package: UTC retrieval time, HTTP status, sha256 of the body,
latest version and its upload time, requires_python, the license fields as
declared (a declaration, not the license file), Python 3.13 support (trove
classifier or a cp313 / abi3 / py3-none-any wheel), the GitHub repositories
linked from the project metadata (cross-link discovery), and flags for heavy
or paid-service dependencies found in requires_dist (base requirements only,
extras listed separately). The raw body is kept outside the repository.
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

GH = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
HEAVY = {
    "GPU_FRAMEWORK": ("torch", "tensorflow", "jax", "jaxlib", "mxnet", "paddlepaddle", "cupy"),
    "LLM_CLIENT": ("openai", "anthropic", "litellm", "langchain", "langchain-core", "transformers",
                   "google-generativeai", "google-genai", "ollama", "tiktoken", "groq", "mistralai"),
    "MEMORY_OR_GRAPH_SERVICE": ("zep-cloud", "zep-python", "neo4j", "falkordb", "graphiti-core"),
    "SERVER_STACK": ("fastapi", "uvicorn", "flask", "sqlalchemy", "psycopg2", "psycopg2-binary", "boto3"),
}


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def req_name(spec):
    return re.split(r"[\s;\[<>=!~(]", spec.strip(), maxsplit=1)[0].lower()


def main(argv):
    out, raw_dir, names = argv[1], argv[2], argv[3:]
    os.makedirs(raw_dir, exist_ok=True)
    for name in names:
        url = "https://pypi.org/pypi/%s/json" % name
        t = utc_now()
        try:
            with urllib.request.urlopen(urllib.request.Request(
                    url, headers={"User-Agent": "memelab-predictive-phase02"}), timeout=60) as r:
                status, body = r.status, r.read()
        except urllib.error.HTTPError as e:
            status, body = e.code, e.read()
        with open(os.path.join(raw_dir, "pypi_%s.json" % name), "wb") as f:
            f.write(body)
        rec = {"package": name, "url": url, "retrieved_at": t, "http_status": status,
               "body_sha256": hashlib.sha256(body).hexdigest(), "mechanism": "PYPI_JSON"}
        if status == 200:
            d = json.loads(body)
            info = d["info"]
            files = d.get("urls") or []
            links = [info.get("home_page") or "", info.get("download_url") or ""]
            links += list((info.get("project_urls") or {}).values())
            repos = []
            for u in links:
                m = GH.search(u or "")
                if m:
                    r = m.group(1) + "/" + re.sub(r"\.git$", "", m.group(2))
                    if r.lower() not in [x.lower() for x in repos]:
                        repos.append(r)
            base, extra = [], []
            for spec in info.get("requires_dist") or []:
                (extra if "extra ==" in spec else base).append(req_name(spec))
            flags = sorted({k for k, v in HEAVY.items() for b in base if b in v})
            extra_flags = sorted({k for k, v in HEAVY.items() for b in extra if b in v})
            cls = info.get("classifiers") or []
            wheels = [f["filename"] for f in files if f.get("packagetype") == "bdist_wheel"]
            py313 = ("Programming Language :: Python :: 3.13" in cls
                     or any("cp313" in w or "abi3" in w or "py3-none-any" in w or "py2.py3-none-any" in w for w in wheels))
            uploads = [f.get("upload_time_iso_8601") for f in files if f.get("upload_time_iso_8601")]
            rec.update({
                "version": info.get("version"), "latest_upload": max(uploads) if uploads else None,
                "requires_python": info.get("requires_python"),
                "license_declared": info.get("license_expression") or (info.get("license") or "")[:80],
                "license_classifiers": [c for c in cls if c.startswith("License ::")],
                "py313_supported": py313, "wheel_count": len(wheels),
                "github_repos": repos, "base_requires": base, "dep_flags": flags,
                "extra_dep_flags": extra_flags, "summary": (info.get("summary") or "")[:160],
                "inactive_classifier": any("7 - Inactive" in c for c in cls),
            })
        with open(out, "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")
        print(name, status, rec.get("version"), rec.get("github_repos"), rec.get("dep_flags"), rec.get("py313_supported"))
        time.sleep(0.5)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
