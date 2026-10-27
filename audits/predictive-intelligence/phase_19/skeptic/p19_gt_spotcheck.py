"""Phase 19 skeptic: re-request the two archived OHLCV reads with the highest sha256 of the request URL (same URL, token=<mint>,
15 s apart, 2 free GeckoTerminal calls) and compare every candle with the archived body.  python3 -I p19_gt_spotcheck.py CLONE OUT.json"""
import csv, gzip, hashlib, json, subprocess, sys, time
PH = sys.argv[1] + "/audits/predictive-intelligence/phase_19/"
man = [r for r in csv.DictReader(open(PH + "raw/MANIFEST.csv")) if r["response_key"] and r["http_status"] == "200"]
man.sort(key=lambda r: hashlib.sha256(r["request_url"].encode()).hexdigest(), reverse=True)
out = []
for i, m in enumerate(man[:2]):
    if i:
        time.sleep(15)
    t = time.time()
    r = subprocess.run(["curl", "-sS", "--max-time", "30", "-w", "\n%{http_code}", m["request_url"]], capture_output=True, text=True)
    body, code = r.stdout.rsplit("\n", 1)
    a = {c[0]: c for c in json.loads(gzip.open(PH + "raw/" + m["file"]).read())["data"]["attributes"]["ohlcv_list"]}
    if code != "200":
        out.append({"pool6": m["pool"][:6], "http": code}); continue
    b = {c[0]: c for c in json.loads(body)["data"]["attributes"]["ohlcv_list"]}
    common = set(a) & set(b)
    changed = [k for k in common if [round(x, 12) for x in a[k][1:]] != [round(x, 12) for x in b[k][1:]]]
    out.append({"pool6": m["pool"][:6], "first_read": m["retrieved_at"], "second_read_t": t, "http": code, "n_first": len(a),
                "n_second": len(b), "common": len(common), "changed": len(changed)})
json.dump(out, open(sys.argv[2], "w"), indent=1)
print(json.dumps(out))
