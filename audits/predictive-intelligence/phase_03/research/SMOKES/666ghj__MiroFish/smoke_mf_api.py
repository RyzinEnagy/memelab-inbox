"""MiroFish Flask API smoke (Phase 03, reviewer R5): key gate, auth, CORS, error disclosure.

Run from backend/ of the pinned clone with the MiroFish venv, inside `unshare -n`:
  python smoke_mf_api.py
No key is set. Uses Flask's test client only (no socket is opened).
"""
import json
import os
import sys

for k in ("LLM_API_KEY", "ZEP_API_KEY", "ZEP_API_URL"):
    os.environ.pop(k, None)
sys.path.insert(0, os.getcwd())

from app.config import Config  # noqa: E402

out = {"config_validate_errors_without_keys": Config.validate(),
       "secret_key_default": Config.SECRET_KEY == "mirofish-secret-key",
       "llm_base_url_default": Config.LLM_BASE_URL}

from app import create_app  # noqa: E402

app = create_app()
rules = sorted({(r.rule, ",".join(sorted(m for m in r.methods if m not in ("HEAD", "OPTIONS"))))
                for r in app.url_map.iter_rules() if r.rule.startswith("/api/")})
out["api_rule_count"] = len(rules)
c = app.test_client()
r = c.get("/api/simulation/list", headers={"Origin": "http://untrusted.example"})
out["list_without_auth_status"] = r.status_code
out["cors_allow_origin"] = r.headers.get("Access-Control-Allow-Origin")
r = c.post("/api/simulation/start", json={"simulation_id": "does_not_exist", "platform": "reddit"})
body = r.get_json(silent=True) or {}
out["start_unknown_status"] = r.status_code
out["start_unknown_keys"] = sorted(body.keys())
out["start_unknown_has_traceback"] = "traceback" in body
r = c.post("/api/report/generate", json={"simulation_id": "does_not_exist"})
body = r.get_json(silent=True) or {}
out["report_unknown_status"] = r.status_code
out["report_unknown_has_traceback"] = "traceback" in body
print(json.dumps(out, indent=1, ensure_ascii=False))
