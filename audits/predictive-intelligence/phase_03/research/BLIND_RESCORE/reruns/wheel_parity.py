import sys, zipfile, hashlib, os
whl, src_root, pkg = sys.argv[1:4]
z = zipfile.ZipFile(whl); same = diff = missing = 0; diffs = []
for n in z.namelist():
    if not n.endswith(".py") or not n.startswith(pkg + "/"): continue
    p = os.path.join(src_root, n)
    if not os.path.exists(p): missing += 1; diffs.append("missing:" + n); continue
    if hashlib.sha256(z.read(n)).digest() == hashlib.sha256(open(p, "rb").read()).digest(): same += 1
    else: diff += 1; diffs.append("diff:" + n)
print(whl, "py files identical", same, "different", diff, "not in pin", missing, diffs[:5])
