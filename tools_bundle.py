"""Build/extract a single-file bundle of the memelab project for the GitHub hand-off.
build:   python tools_bundle.py build  -> dist/memelab_bundle.txt (base64 zip of code, docs, tests, skill, public DB)
extract: python tools_bundle.py extract <bundle.txt> <dest>
Excludes data/config.json, data/wallet/, data/reports, data/inbox, caches."""
import base64, io, sys, zipfile, pathlib
ROOT = pathlib.Path(__file__).resolve().parent
EXCL = ("data/config.json", "data/wallet", "data/reports", "data/inbox", "__pycache__", ".pytest_cache", "dist", "memelab.sqlite-journal")
def build():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in ROOT.rglob("*"):
            rel = p.relative_to(ROOT).as_posix()
            if p.is_dir() or any(x in rel for x in EXCL):
                continue
            z.write(p, rel)
    (ROOT / "dist").mkdir(exist_ok=True)
    out = ROOT / "dist" / "memelab_bundle.txt"
    out.write_text(base64.b64encode(buf.getvalue()).decode())
    print(out, out.stat().st_size, "chars")
def extract(src, dest):
    data = base64.b64decode(pathlib.Path(src).read_text())
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        z.extractall(dest)
    print("extracted to", dest)
if __name__ == "__main__":
    build() if sys.argv[1] == "build" else extract(sys.argv[2], sys.argv[3])
