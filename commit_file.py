# Commits one file to RyzinEnagy/memelab-inbox through the GitHub contents API. Never prints the token.
# usage: python3 commit_file.py <repo_path> <local_file> <commit_message> [branch]
# The token is NOT in this repo. It is looked up, in order, at:
#   $MEMELAB_GH_TOKEN_FILE, gh_token.txt next to this script, ~/mnt/memelab/gh_token.txt (Cowork connected folder),
#   C:\Users\<user>\memelab\gh_token.txt
import sys, json, base64, os, glob, urllib.request, urllib.error

OWNER, REPO = "RyzinEnagy", "memelab-inbox"


def find_token():
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [os.environ.get("MEMELAB_GH_TOKEN_FILE"), os.path.join(here, "gh_token.txt"),
             os.path.expanduser("~/mnt/memelab/gh_token.txt")] + glob.glob(os.path.expanduser("~/mnt/*/gh_token.txt")) + glob.glob(r"C:\Users\*\memelab\gh_token.txt")
    for c in cands:
        if c and os.path.isfile(c):
            with open(c) as f:
                t = f.read().strip()
            if t:
                return t
    print("ERROR: gh_token.txt not found. Put it next to this script, in the connected memelab folder, or set MEMELAB_GH_TOKEN_FILE.")
    sys.exit(3)


def main():
    if len(sys.argv) < 4:
        print("usage: commit_file.py <repo_path> <local_file> <message> [branch]"); sys.exit(2)
    repo_path, local_file, message = sys.argv[1], sys.argv[2], sys.argv[3]
    branch = sys.argv[4] if len(sys.argv) > 4 else "main"
    token = find_token()
    api = "https://api.github.com/repos/%s/%s/contents/%s" % (OWNER, REPO, repo_path)
    hdr = {"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json", "User-Agent": "memelab-commit"}
    sha = None
    try:
        req = urllib.request.Request(api + "?ref=" + branch, headers=hdr)
        with urllib.request.urlopen(req) as r:
            sha = json.load(r).get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print("ERROR checking existing file:", e.code, e.read().decode()[:200]); sys.exit(1)
    with open(local_file, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()
    body = {"message": message, "content": content_b64, "branch": branch}
    if sha:
        body["sha"] = sha
    req = urllib.request.Request(api, data=json.dumps(body).encode(), headers=hdr, method="PUT")
    try:
        with urllib.request.urlopen(req) as r:
            print("committed:", json.load(r).get("commit", {}).get("html_url"))
    except urllib.error.HTTPError as e:
        print("ERROR committing:", e.code, e.read().decode()[:300]); sys.exit(1)


if __name__ == "__main__":
    main()
