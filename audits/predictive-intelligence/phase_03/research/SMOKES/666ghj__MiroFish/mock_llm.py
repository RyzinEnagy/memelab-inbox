"""Canned OpenAI-compatible chat endpoint for offline simulator smokes (Phase 03, reviewer R5).

Listens on 127.0.0.1 only. Never forwards anything. Every response is a deterministic
function of the request body (sha256), so any run-to-run difference comes from the
simulator, not from this mock. Each request is logged as one JSON line (sizes only,
no content) to measure call volume as a cost proxy.

Usage: python -I mock_llm.py PORT LOG_JSONL
"""
import hashlib
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1])
LOG = sys.argv[2]


def pick_tool(tools, digest):
    names = [t.get("function", {}).get("name") for t in tools or []]
    h = int(digest[:8], 16)
    if "create_post" in names and h % 3 == 0:
        return "create_post", {"content": "synthetic post " + digest[:6]}
    if "like_post" in names and h % 3 == 1:
        return "like_post", {"post_id": 1}
    if "do_nothing" in names:
        return "do_nothing", {}
    if names:
        return names[0], {}
    return None, None


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        body = json.dumps({"object": "list", "data": [{"id": "gpt-4o-mini", "object": "model"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n)
        req = json.loads(raw or b"{}")
        digest = hashlib.sha256(raw).hexdigest()
        msgs = req.get("messages", [])
        last_role = msgs[-1].get("role") if msgs else None
        tools = req.get("tools")
        msg = {"role": "assistant", "content": None}
        finish = "stop"
        kind = "text"
        if tools and last_role != "tool":
            name, args = pick_tool(tools, digest)
            if name:
                msg["tool_calls"] = [{"id": "call_" + digest[:12], "type": "function",
                                      "function": {"name": name, "arguments": json.dumps(args)}}]
                finish = "tool_calls"
                kind = "tool:" + name
        if "tool_calls" not in msg:
            rf = req.get("response_format") or {}
            if rf.get("type") == "json_object":
                msg["content"] = json.dumps({"mock": True, "digest": digest[:8]})
                kind = "json"
            else:
                msg["content"] = "mock reply " + digest[:8]
        prompt_chars = sum(len(str(m.get("content") or "")) for m in msgs)
        out = {"id": "chatcmpl-" + digest[:16], "object": "chat.completion", "created": 1790000000,
               "model": req.get("model", "mock"),
               "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
               "usage": {"prompt_tokens": prompt_chars // 4, "completion_tokens": 10,
                         "total_tokens": prompt_chars // 4 + 10}}
        body = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        with open(LOG, "a") as fh:
            fh.write(json.dumps({"t": time.time(), "path": self.path, "model": req.get("model"),
                                 "n_messages": len(msgs), "n_tools": len(tools or []),
                                 "prompt_chars": prompt_chars, "reply": kind,
                                 "req_sha256": digest}) + "\n")


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
