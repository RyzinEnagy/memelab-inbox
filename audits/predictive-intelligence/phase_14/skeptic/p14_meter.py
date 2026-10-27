"""Skeptic 14 meter probe (loopback only). An upstream mock that honours `n` (choices per call) and `stream`, the way an
OpenAI-compatible server does, and bills n x max_tokens output tokens. Does the meter's charge bound the upstream's bill?
    python -B p14_meter.py REPO"""
import json, sys, threading, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
REPO = Path(sys.argv[1]); sys.path.insert(0, str(REPO))
from memelab.predictive import behavioral as B
PIN, POUT = 1.0, 2.0           # fictional USD per 1k tokens
bill = {"micro": 0, "calls": 0}
class Up(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        n, mt = int(req.get("n") or 1), int(req.get("max_tokens") or 16)
        pt, ct = len(json.dumps(req)) // 4, n * mt
        bill["micro"] += -(-(pt * int(PIN * 1e6) + ct * int(POUT * 1e6)) // 1000); bill["calls"] += 1
        if req.get("stream"):
            body = b"data: {\"choices\":[{\"delta\":{\"content\":\"x\"}}]}\n\ndata: [DONE]\n\n"
        else:
            body = json.dumps({"choices": [{"index": i, "message": {"role": "assistant", "content": "x"}} for i in range(n)],
                               "usage": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct}}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
def run(extra, calls=60):
    bill.update(micro=0, calls=0)
    up = ThreadingHTTPServer(("127.0.0.1", 0), Up); threading.Thread(target=up.serve_forever, daemon=True).start()
    m = B.LLMMeter(f"http://127.0.0.1:{up.server_address[1]}", max_cost_usd=50.0, price_in_per_1k_tokens_usd=PIN, price_out_per_1k_tokens_usd=POUT)
    url = m.start(); codes = []
    for _ in range(calls):
        body = json.dumps({"model": "m", "messages": [{"role": "user", "content": "hi"}], **extra}).encode()
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(urllib.request.Request(url + "/v1/chat/completions", data=body, headers={"Content-Type": "application/json"}), timeout=5) as r:
                codes.append(r.status)
        except urllib.error.HTTPError as e:
            codes.append(e.code)
    s = m.summary(); m.stop(); up.shutdown()
    print(f"{json.dumps(extra):28s} forwarded={s['calls_forwarded']:2d} charged={s['charged_microusd']:6d} cap={s['cap_microusd']} "
          f"upstream_bill={bill['micro']:6d} bill/cap={bill['micro']/s['cap_microusd']:.2f} killed={s['killed']} usage_above_charge={s['usage_above_charge']}")
run({})
run({"n": 8})
run({"n": 8, "stream": True})
run({"n": 64, "stream": True})
