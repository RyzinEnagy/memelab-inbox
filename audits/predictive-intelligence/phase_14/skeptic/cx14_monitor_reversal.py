"""Skeptic 14 counterexample CX-S14 (loopback only, lab mock style service).
A simulator keeps the label ORGANIC_ATTENTION_CONTINUATION in every grid cell but reverses its falsifiable monitor with the run
seed: seeds 101 and 303 expect price_path_target_before_invalidation_6h EVENT (momentum buyers enter), seed 202 expects NO_EVENT
(no new buyers). The scenario is reversed by a seed change (P29), yet run_grid reports STABLE, no UNSTABLE_EXPLORATORY, and the
merged document carries both opposite hypotheses. Exit 1 when the reversal is NOT detected.
    python -B cx14_monitor_reversal.py REPO"""
import json, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, sys.argv[1])
from memelab.predictive import behavioral as B

class Flip(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        ids = [e["obs_id"] for e in req["quoted_evidence"] if e["kind"] == "LAB_ATTENTION_PROXY"]
        up = req["run"]["run_seed"] != 202
        h = [{"label": "NO_GROUNDED_SCENARIO", "source_refs": [], "assumptions": [], "monitor": None}] if not ids else [
             {"label": "ORGANIC_ATTENTION_CONTINUATION", "source_refs": ids[:1], "monitor": {"metric": B._T1B, "expect": "EVENT" if up else "NO_EVENT"},
              "assumptions": [{"kind": "OBSERVED_FACT", "code": "CITES_OBSERVATION", "source_refs": ids[:1]},
                              {"kind": B.SYN_BEHAVIOR, "code": "MOMENTUM_BUYERS_ENTER" if up else "NO_NEW_BUYERS", "source_refs": []}]}]
        body = json.dumps({"protocol": B.PROTOCOL, "status": "OK", "llm_actions": 4, "llm_calls": 4, "trace_sha256": "f" * 64,
                           "hypotheses": h, "claims": []}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

srv = ThreadingHTTPServer(("127.0.0.1", 0), Flip); threading.Thread(target=srv.serve_forever, daemon=True).start()
seed = B.build_seed("solana", "So11111111111111111111111111111111111111112", "a" * 64, "2026-10-12T05:00:00Z",
                    [B.observation(B.LAB_ATTENTION_PROXY, "sc_organic_acceleration", 1.0, "2026-10-12T04:00:00Z", "socialcat-1:x:sc_organic_acceleration")])
eng = {"name": "lab-mock", "mode": B.MOCK_SIMULATOR, "pin": "fixture", "model_id": "NONE", "model_training_cutoff_utc": B.NOT_APPLICABLE, "paid": False}
cfg = {"predictive": {"behavioral": {"approved": True, "mode": "ON_DEMAND_LOCAL"}}}
d = B.ServiceAdapter(cfg, eng, f"http://127.0.0.1:{srv.server_address[1]}", seed=seed, sleep=lambda _: None, created_at_utc="2026-10-26T00:00:00Z").run_grid()
srv.shutdown()
pairs = sorted((h["label"], h["monitor"]["expect"]) for h in d["hypotheses"] if h["monitor"])
print(json.dumps({"status": d["status"], "reasons": d["reasons"], "stability": d["stability"], "hypotheses": pairs,
                  "validate_scenario": B.validate_scenario(d), "forecast_entries": [(e["label"], e["monitor_expect"], e["stability"]) for e in B.forecast_entries(d)]}, indent=1))
caught = d["stability"]["status"] != B.STABLE
print("CX-S14", "CAUGHT" if caught else "NOT CAUGHT: a seed-reversed scenario is published as STABLE")
sys.exit(0 if caught else 1)
