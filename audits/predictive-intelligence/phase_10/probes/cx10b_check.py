"""Phase 10 repair pass 2: the skeptic's counterexamples CX-10b-A and CX-10b-B and minor m3, run against the socialcat.py of
two commits (the first-pass frozen code and the repaired code). Each commit's `memelab/` tree is extracted with `git archive` into
a temporary folder and imported in a fresh interpreter, so the checkout is never edited. Fixtures only (TEST_ONLY): no store, no
network. Writes a JSON report; exit 0 when the first-pass code shows each defect and the repaired code shows none.

    python -B cx10b_check.py OLD_REF NEW_REF OUT.json
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]

CASES = r'''
import inspect, json, sys
from memelab.predictive import socialcat as SC
MINT = "So11111111111111111111111111111111111111113"
T = 2_000_000.0
out = {}
# CX-10b-A: a rumor at T-3000, linked by exact mint at T-2900, an independent rumor at T-2800, the exchange's own notice and the
# CONFIRMED revision at T-600 (the lab writes the revision and the row update together, catalyst ingest).
ev = {"event_key": "e1", "category": "ACCESS", "evidence_status": "CONFIRMED", "created_at": T - 3000, "updated_at": T - 600}
items = [{"id": 1, "source_id": "social:x", "url": "https://x.example/1", "body": MINT + " soon on exchange", "first_seen_at": T - 3000},
         {"id": 2, "source_id": "agg:b", "url": "https://agg.example/2", "body": "exchange rumour", "first_seen_at": T - 2800},
         {"id": 3, "source_id": "exch:official", "url": "https://exchange.example/notice", "body": "listing notice " + MINT, "first_seen_at": T - 600}]
roles = {1: "ORIGINAL", 2: "INDEPENDENT", 3: "INDEPENDENT"}
revs = [{"id": 1, "kind": "CREATED", "revised_at": T - 3000},
        {"id": 2, "kind": "REVISED", "field": "evidence_status", "old_value": "RUMOR", "new_value": "CONFIRMED", "revised_at": T - 600}]
links = [{"mint": MINT, "chain": "solana", "link_type": "NAMED_IN_SOURCE", "link_strength": "STRONG", "linked_at": T - 2900}]
c = SC.classify_catalyst(ev, items, roles, revs, links, chain="solana", mint=MINT, decision_time=T, official_sources=["exch:official"])
early = SC.classify_catalyst(ev, items, roles, revs, links, chain="solana", mint=MINT, decision_time=T - 1000, official_sources=["exch:official"])
path = [{"t": T - 3000 + 300 * k, "close": 1.3 if T - 3000 + 300 * k >= T - 1500 else 1.0,
         "high": 1.3 if T - 3000 + 300 * k >= T - 1500 else 1.0, "low": 1.3 if T - 3000 + 300 * k >= T - 1500 else 1.0} for k in range(40)]
kw = dict(available_at=c["available_at"], provider_lag_s=300, up=0.25, down=0.15, horizon_s=7200)
if "decision_time" in inspect.signature(SC.proposed_follow_through_label).parameters:
    kw["decision_time"] = T
lab = SC.proposed_follow_through_label(path, **kw)
out["CX_10b_A"] = {"state_at_T": c["state"], "available_at_minus_T_s": c["available_at"] - T, "state_at_T_minus_1000": early["state"],
                   "follow_through": {"label": lab["label"], "state": lab["state"]},
                   "defect": c["state"] == "VERIFIED" and (c["available_at"] < T - 600 or lab["label"] == 1)}
# CX-10b-B: an account VERIFIED at T-1 d, exact-mint post ingested at T-2900, suspended at T+1 d (row updated in place); a BOT
# kind with no time.
acc = {"account_id": "x:id:1", "account_kind": "PERSON", "identity_status": "VERIFIED", "identity_checked_at": T - 86400}
acc2 = dict(acc, account_id="x:id:2")
its = [{"item_key": k, "account_id": a, "platform": "x", "first_ingested_at": T - 2900} for k, a in (("k1", "x:id:1"), ("k2", "x:id:2"))]
obs = [{"id": n, "item_key": k, "account_id": a, "ingested_at": T - 2900, "retrieval_status": "OK", "content_hash": h}
       for n, (k, a, h) in enumerate((("k1", "x:id:1", "h1"), ("k2", "x:id:2", "h2")), 1)]
res = [{"item_key": k, "mention_kind": "CONTRACT", "status": "resolved", "resolved_chain": "solana", "resolved_contract": MINT,
        "resolved_at": T - 2800} for k in ("k1", "k2")]
def world(a1, vers=()):
    return {"social_accounts": [a1, acc2], "social_items": its, "social_observations": obs, "social_item_versions": list(vers),
            "social_token_resolutions": res, "social_claims": [], "social_claim_extractions": [], "social_trader_accounts": [],
            "social_token_refs": []}
pick = lambda r: {k: r["values"][k] for k in ("sx_mentions_exact", "sx_bot_share")}
at_t = pick(SC.social_as_of(world(acc), "solana", MINT, T))
susp = pick(SC.social_as_of(world(dict(acc, identity_status="SUSPENDED", identity_checked_at=T + 86400)), "solana", MINT, T))
bot = pick(SC.social_as_of(world(dict(acc, account_kind="BOT")), "solana", MINT, T))
out["CX_10b_B"] = {"truncated_view_at_T": at_t, "suspended_after_T": susp, "bot_kind_without_time": bot,
                   "defect": susp != at_t or bot != at_t}
# m3: an ORIGINAL version of k2 recorded only after T (its hash equals k1's article)
v = [{"item_key": "k2", "provider_version_at": T - 2900, "version_kind": "ORIGINAL", "content_hash": "h1", "first_recorded_at": T + 60}]
m3 = pick(SC.social_as_of(world(acc, v), "solana", MINT, T))
out["m3_version_after_T"] = {"truncated_view_at_T": at_t, "with_a_version_recorded_after_T": m3, "defect": m3 != at_t}
print(json.dumps(out))
'''


def run_at(ref: str) -> dict:
    sha = subprocess.run(["git", "-C", str(REPO), "rev-parse", ref], check=True, capture_output=True, text=True).stdout.strip()
    with tempfile.TemporaryDirectory() as td:
        arc = subprocess.run(["git", "-C", str(REPO), "archive", sha, "memelab"], check=True, capture_output=True).stdout
        subprocess.run(["tar", "-x", "-C", td], input=arc, check=True)
        r = subprocess.run([sys.executable, "-B", "-I", "-c", f"import sys; sys.path.insert(0, {td!r})\n" + CASES],
                           capture_output=True, text=True, cwd=td)
        if r.returncode != 0:
            raise SystemExit(f"cases failed at {sha}:\n{r.stderr[-2000:]}")
        return {"commit": sha, **json.loads(r.stdout)}


def main(old: str, new: str, out: str) -> int:
    rep = {"first_pass": run_at(old), "repaired": run_at(new)}
    keys = ("CX_10b_A", "CX_10b_B", "m3_version_after_T")
    rep["pass"] = all(rep["first_pass"][k]["defect"] for k in keys) and not any(rep["repaired"][k]["defect"] for k in keys)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"first_pass_defects": {k: rep["first_pass"][k]["defect"] for k in keys},
                      "repaired_defects": {k: rep["repaired"][k]["defect"] for k in keys}, "pass": rep["pass"]}))
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
