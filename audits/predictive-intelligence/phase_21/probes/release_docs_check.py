"""Phase 21 (G9, G10): check the release documents against the repository, read-only, no network.

    python -B release_docs_check.py OUTJSON [--plant]

1. Level: the highest promotion level in the committed registry; the release decision may name SHADOW_ONLY or
   VALIDATED_EXPERIMENTAL as a GO only when an entry holds that level (G10). Checked on the "GO" rows of the decision table.
2. Paths: every backticked path in the release documents that names a repository file or folder exists (relative to the
   repository root or to audits/predictive-intelligence/); evidence paths are resolved under phase_21/.
3. Style: no em dash or en dash in the release documents and docs/predictive-intelligence/RELEASE.md.
4. Commands: every `python -B -m memelab.predictive...` command of USER_GUIDE.md has its module and subcommand in the doc-command
   log (evidence/doc_commands/doc_commands.txt).
5. Run commands (CP21-1, skeptic F6): every command line in a fenced block of INSTALL_RUNBOOK.md and USER_GUIDE.md has its
   signature (module and subcommand, script and subcommand, or git/pip verb) in the scripts or logs of the recorded runs
   (release_checks.sh, doc_commands.sh, guide_sandbox.sh, e2e.sh, real_path_smoke.sh, the doc-command and guide logs, the
   maturity record), or in RUN_ELSEWHERE with the evidence of the earlier run.
With --plant, four planted defects on in-memory copies (a GO row naming SHADOW_ONLY, a missing path, an em dash, a runbook
command that no recorded run executed) must each be caught; the result is recorded beside the real one.
Exit 0 when the real documents pass (and, with --plant, every planted defect is caught).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from memelab.predictive import registry as R  # noqa: E402

AUD = REPO / "audits/predictive-intelligence"
P21 = AUD / "phase_21"
DOCS = sorted((P21 / "release").glob("*.md")) + [REPO / "docs/predictive-intelligence/RELEASE.md"]
PUBLISHABLE = {"SHADOW", "VALIDATED_EXPERIMENTAL"}
PATH_RE = re.compile(r"`([A-Za-z0-9_./*<>-]+/[A-Za-z0-9_./*<>-]*|[A-Za-z0-9_-]+\.(?:md|json|jsonl|csv|py|sh|txt))`")


def top_level() -> set[str]:
    return {e["promotion"]["level"] for e in R.read_entries(AUD / "phase_16/registry/entries").values()}


def level_problems(texts: dict[str, str], levels: set[str]) -> list[str]:
    out = []
    dec = texts.get("RELEASE_DECISION.md", "")
    for line in dec.splitlines():
        if line.startswith("|") and "| GO" in line:
            for lv, name in (("SHADOW", "SHADOW_ONLY"), ("VALIDATED_EXPERIMENTAL", "VALIDATED_EXPERIMENTAL")):
                if name in line and lv not in levels:
                    out.append(f"GO row names {name} but no registry entry is at {lv}")
    return out


NOT_PATHS = {"feature/predictive-intelligence", "origin/main", "feature/backtesting"}


def names_index() -> set[str]:
    import subprocess
    files = subprocess.run(["git", "-C", str(REPO), "ls-files"], capture_output=True, text=True, check=True).stdout.splitlines()
    files += [str(p.relative_to(REPO)) for p in P21.rglob("*") if p.is_file()]
    return {Path(f).name for f in files}


NAMES: set[str] = set()
CORPUS: list[str] = []


def resolve(p: str, doc: Path) -> bool:
    """A path resolves when it exists under one of the bases; a bare file name when a tracked or Phase 21 file has that name."""
    if any(c in p for c in "<>") or p.startswith(("http", "/tmp", "/path")) or p in NOT_PATHS:
        return True
    folder = p.endswith("/")
    p = p.rstrip("/")
    if "/" not in p and not folder:
        return p in NAMES
    bases = [REPO, AUD, P21, P21 / "release", P21 / "evidence/release_checks", P21 / "evidence/doc_commands", doc.parent,
             REPO / "docs/predictive-intelligence"]
    cands = [b / p for b in bases]
    if "*" in p:
        return any(list(c.parent.glob(c.name)) for c in cands)
    return any(c.exists() for c in cands)


def path_problems(texts: dict[str, Path | str], paths: dict[str, Path]) -> list[str]:
    out = []
    for name, t in texts.items():
        for p in PATH_RE.findall(t):
            if p.startswith(("memelab.", "python")) or p in ("data/config.json",) or p.startswith(("data/private", ".venv")):
                continue
            if not resolve(p, paths[name]):
                out.append(f"{name}: {p}")
    return sorted(set(out))


def dash_problems(texts: dict[str, str]) -> list[str]:
    return [f"{n}: line {i + 1}" for n, t in texts.items() for i, line in enumerate(t.splitlines()) if "—" in line or "–" in line]


def command_problems(guide: str, log: str) -> list[str]:
    out = []
    for m in re.finditer(r"python -B -m (memelab\.predictive\.\w+) ([\w-]+)", guide):
        if f"{m.group(1)} {m.group(2)}" not in log:
            out.append(f"{m.group(1)} {m.group(2)} not in the doc-command log")
    return sorted(set(out))


RUN_ELSEWHERE = {"fetch_labels.py reread48": "phase_19/evidence/revision_reread_48h.json (orchestrator, 2026-10-29, PI-D-112)"}
SKIP_PREFIXES = ("cd ", "printf ", "python -c ")


def signature(cmd: str) -> str | None:
    toks = cmd.replace(".venv/bin/", "").split()
    while toks and "=" in toks[0] and not toks[0].startswith("-"):
        toks = toks[1:]                                      # environment assignments
    line = " ".join(toks)
    if not toks or line.startswith(SKIP_PREFIXES):
        return None
    bare = lambda t: re.fullmatch(r"[a-z][a-z0-9_-]*", t) is not None     # noqa: E731
    if "-m" in toks:
        i = toks.index("-m")
        mod = toks[i + 1] if i + 1 < len(toks) else ""
        nxt = toks[i + 2] if i + 2 < len(toks) and bare(toks[i + 2]) else ""
        return f"-m {mod} {nxt}".strip()
    for i, t in enumerate(toks):
        if t.endswith((".py", ".sh")):
            nxt = toks[i + 1] if i + 1 < len(toks) and bare(toks[i + 1]) else ""
            return f"{Path(t).name} {nxt}".strip()
    if toks[0] in ("git", "pip") and len(toks) > 1:
        return f"{toks[0]} {toks[1]}"
    return line


def corpus_text() -> str:
    files = [P21 / "probes/release_checks.sh", P21 / "probes/doc_commands.sh", P21 / "probes/guide_sandbox.sh",
             AUD / "phase_20/probes/e2e.sh", AUD / "phase_17/probes/real_path_smoke.sh",
             P21 / "evidence/doc_commands/doc_commands.txt", P21 / "evidence/maturity/MATURITY_RUN.json"]
    files += sorted(P21.glob("evidence/repair_rerun/**/guide_sandbox.txt"))
    return "\n".join(f.read_text() for f in files if f.exists())


def run_command_problems(texts: dict[str, str], corpus: str) -> list[str]:
    out = []
    norm = re.sub(r"\s+", " ", corpus.replace(".venv/bin/", "").replace("$OUT/venv/bin/", ""))
    norm = re.sub(r"git -C \S+ ", "git ", norm)              # `git -C "$C" checkout` runs `git checkout`
    for name in ("INSTALL_RUNBOOK.md", "USER_GUIDE.md"):
        for block in texts.get(name, "").split("```")[1::2]:
            for raw in block.splitlines():
                for part in raw.strip().split("&&"):
                    sig = signature(part.strip())
                    if sig and sig not in norm and sig not in RUN_ELSEWHERE:
                        out.append(f"{name}: {sig}")
    return sorted(set(out))


def run(texts: dict[str, str], paths: dict[str, Path], levels: set[str], log: str) -> dict:
    res = {"level": level_problems(texts, levels), "paths": path_problems(texts, paths), "dashes": dash_problems(texts),
           "commands": command_problems(texts.get("USER_GUIDE.md", ""), log),
           "run_commands": run_command_problems(texts, CORPUS[0] if CORPUS else "")}
    res["ok"] = not any(res.values())
    return res


def main() -> int:
    out = Path(sys.argv[1])
    NAMES.update(names_index())
    CORPUS.append(corpus_text())
    texts = {d.name: d.read_text() for d in DOCS}
    paths = {d.name: d for d in DOCS}
    levels = top_level()
    log = (P21 / "evidence/doc_commands/doc_commands.txt").read_text()
    real = run(texts, paths, levels, log)
    res = {"documents": sorted(texts), "registry_levels": sorted(levels), "real": real}
    ok = real["ok"]
    if "--plant" in sys.argv:
        t1 = dict(texts)
        t1["RELEASE_DECISION.md"] += "\n| planted | SHADOW_ONLY | GO |\n"
        t2 = dict(texts)
        t2["MODEL_LIMITS.md"] += "\nSee `phase_12/validation/NO_SUCH_FILE.json`.\n"
        t3 = dict(texts)
        t3["RELEASE.md"] += "\nA planted — dash.\n"
        t4 = dict(texts)
        t4["INSTALL_RUNBOOK.md"] += "\n```\npython -B audits/predictive-intelligence/phase_19/probes/run_prospective.py never_run\n```\n"
        planted = {"go_row_above_registry": bool(run(t1, paths, levels, log)["level"]),
                   "command_never_run": bool(run(t4, paths, levels, log)["run_commands"]),
                   "missing_path": bool(run(t2, paths, levels, log)["paths"]),
                   "em_dash": bool(run(t3, paths, levels, log)["dashes"])}
        res["planted_caught"] = planted
        ok = ok and all(planted.values())
    res["ok"] = ok
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"ok": ok, "real": {k: (len(v) if isinstance(v, list) else v) for k, v in real.items()},
                      "planted": res.get("planted_caught")}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
