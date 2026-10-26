"""Phase 10 skeptic (10b) counterexamples against the TEST_ONLY catalyst classifier and
social adapter, plus a read-only probe of connect_social_ro. Runs the clone's code.
usage: python -B p10b_counterexamples.py CLONE_DIR SCRATCH_DIR
Each case prints the phase code's answer and the answer of the same call on inputs
truncated to what existed at T (the phase's own 'truncated view' standard)."""
import json, sqlite3, sys, copy
from pathlib import Path
sys.path.insert(0, sys.argv[1]); SCR = Path(sys.argv[2]); SCR.mkdir(parents=True, exist_ok=True)
from memelab.predictive import socialcat as SC
MINT = "So11111111111111111111111111111111111111112"[:-1] + "3"
T = 2_000_000.0
res = {}

# CX-10b-A: VERIFIED availability earlier than verification.
# Rumor-tier item A at T-3000 and an independent item B at T-2800 open the event as RUMOR;
# the strong link exists from T-2900; an official item C joins at T-600 and the lab upgrades
# evidence to CONFIRMED at T-600 (ingest.py:282-290 writes updated_at and the revision together).
EV = {"event_key": "e1", "category": "ACCESS", "evidence_status": "CONFIRMED", "created_at": T - 3000, "updated_at": T - 600}
items = [{"id": 1, "source_id": "social:x", "url": "https://x.example/1", "body": f"{MINT} soon on exchange", "first_seen_at": T - 3000},
         {"id": 2, "source_id": "agg:b", "url": "https://agg.example/2", "body": "exchange rumour", "first_seen_at": T - 2800},
         {"id": 3, "source_id": "exch:official", "url": "https://exchange.example/notice", "body": "listing notice", "first_seen_at": T - 600}]
roles = {1: "ORIGINAL", 2: "INDEPENDENT", 3: "INDEPENDENT"}
revs = [{"id": 1, "kind": "CREATED", "revised_at": T - 3000},
        {"id": 2, "kind": "REVISED", "field": "evidence_status", "old_value": "RUMOR", "new_value": "CONFIRMED", "revised_at": T - 600}]
links = [{"mint": MINT, "chain": "solana", "link_type": "NAMED_IN_SOURCE", "link_strength": "STRONG", "linked_at": T - 2900}]
out = SC.classify_catalyst(EV, items, roles, revs, links, chain="solana", mint=MINT, decision_time=T, official_sources=["exch:official"])
# the same event asked at T-1000 (before the confirmation) is not VERIFIED
early = SC.classify_catalyst(dict(EV, updated_at=T - 2800, evidence_status="RUMOR"), items, roles, revs, links, chain="solana", mint=MINT,
                             decision_time=T - 1000, official_sources=["exch:official"])
lab = SC.proposed_follow_through_label(
    [{"t": T - 3000 + 300 * k, "close": 1.0 + (0.3 if T - 3000 + 300 * k >= T - 1500 else 0.0), "high": 1.0 + (0.3 if T - 3000 + 300 * k >= T - 1500 else 0.0),
      "low": 1.0} for k in range(40)], available_at=out["available_at"], provider_lag_s=300, up=0.25, down=0.15, horizon_s=7200)
res["CX_A_available_at_before_verification"] = {
    "state_at_T": out["state"], "available_at_minus_T_s": out["available_at"] - T if out["available_at"] else None,
    "verified_from_minus_T_s": -600, "state_at_T_minus_1000": early["state"],
    "follow_through_label_from_available_at": lab, "defect": out["state"] == "VERIFIED" and out["available_at"] < T - 600}

# CX-10b-B: a suspension recorded after T removes an item from the as-of social features.
acc = {"account_id": "x:id:1", "account_kind": "PERSON", "identity_status": "VERIFIED", "identity_checked_at": T - 86400}
it = {"item_key": "k1", "account_id": "x:id:1", "platform": "x", "first_ingested_at": T - 2900}
obs = {"item_key": "k1", "account_id": "x:id:1", "ingested_at": T - 2900, "retrieval_status": "OK", "content_hash": "h1"}
it2 = dict(it, item_key="k2", account_id="x:id:2"); obs2 = dict(obs, item_key="k2", account_id="x:id:2", content_hash="h2")
acc2 = dict(acc, account_id="x:id:2")
resol = [{"item_key": k, "mention_kind": "CONTRACT", "status": "resolved", "resolved_chain": "solana", "resolved_contract": MINT, "resolved_at": T - 2800}
         for k in ("k1", "k2")]
def tables(a1):
    return {"social_accounts": [a1, acc2], "social_items": [it, it2], "social_observations": [obs, obs2], "social_item_versions": [],
            "social_token_resolutions": resol, "social_claims": [], "social_claim_extractions": [], "social_trader_accounts": [],
            "social_token_refs": []}
at_T = SC.social_as_of(tables(acc), "solana", MINT, T)
later = SC.social_as_of(tables(dict(acc, identity_status="SUSPENDED", identity_checked_at=T + 86400)), "solana", MINT, T)
res["CX_B_suspension_after_T"] = {"truncated_view": {k: at_T["values"][k] for k in ("sx_mentions_exact", "sx_bot_share")} | {"conf": at_T["attention_confidence"]},
    "full_store_later": {k: later["values"][k] for k in ("sx_mentions_exact", "sx_bot_share")} | {"conf": later["attention_confidence"]},
    "defect": at_T["values"] != later["values"]}
# same for account_kind relabelled BOT later (no timestamp exists for the kind)
botl = SC.social_as_of(tables(dict(acc, account_kind="BOT")), "solana", MINT, T)
res["CX_B2_bot_label_has_no_time"] = {"sx_bot_share_when_relabelled": botl["values"]["sx_bot_share"], "note": "social_accounts.account_kind has no timestamp; a later BOT label is applied at every past T"}

# read-only probe
db = SCR / "social_probe.sqlite"
if db.exists(): db.unlink()
c = sqlite3.connect(db); c.execute("create table social_items(item_key text)"); c.commit(); c.close()
ro = SC.connect_social_ro(db)
try:
    ro.execute("insert into social_items values ('x')"); ro.commit(); w = "WROTE"
except sqlite3.OperationalError as e:
    w = f"refused: {e}"
refuse = {}
for p in ("/home/claude/pi_research/p06/dev_store.sqlite", str(Path(sys.argv[1]) / "data/memelab.sqlite")):
    try: SC.connect_social_ro(p); refuse[p] = "OPENED"
    except Exception as e: refuse[p] = type(e).__name__
res["read_only_probe"] = {"write_attempt": w, "refusals": refuse}
print(json.dumps(res, indent=1, default=str))
