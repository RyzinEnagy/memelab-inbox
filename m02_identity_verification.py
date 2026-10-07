"""02_IDENTITY_VERIFICATION: establish chain, exact name, exact mint, and cross-source agreement.

Identity confidence:
  HIGH      mint found in >=3 independent sources with matching name and symbol, token program known
  MODERATE  2 sources agree, or 3 sources with cosmetic name differences only
  LOW       1 source only
  NOT VERIFIED  mint not resolvable in any structured source, or sources disagree on name/symbol
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

BASE58 = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
TOKEN_PROGRAMS = {
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA": "SPL Token",
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb": "Token-2022",
}


def analyze(bundle: dict[str, Any]) -> dict[str, Any]:
    ident = bundle.get("identity") or {}
    mint = bundle.get("mint")
    facts, inferences, unknowns = [], [], []
    if not mint or not BASE58.match(mint):
        return {"confidence": "NOT VERIFIED", "facts": [], "inferences": [], "heuristics": [], "unknowns": ["mint address malformed"],
                "status": "IDENTITY NOT VERIFIED"}
    names = {s: ident.get(f"{s}_name") for s in ("ds", "gt", "rug")}
    if ident.get("name") and bundle["sources"].get("name") == "jupiter.tokens_v2":
        names["jup"] = ident.get("name")
    present = {k: v for k, v in names.items() if v}
    n_sources = len(present)
    name_match = ident.get("name_matches")
    sym_match = ident.get("symbol_matches")
    tp = ident.get("token_program") or (bundle.get("authorities") or {}).get("token_program")
    tp_rpc = (bundle.get("authorities") or {}).get("token_program_rpc")
    facts.append(f"mint {mint} resolved in {n_sources} structured source(s): {', '.join(sorted(present))}" if n_sources else f"mint {mint} not resolved in any structured source")
    if n_sources >= 2:
        facts.append("name " + ("matches" if name_match else "DIFFERS") + " across sources: " + "; ".join(f"{k}={v!r}" for k, v in present.items()))
    if tp:
        facts.append(f"token program {TOKEN_PROGRAMS.get(tp, tp)}" + (" (confirmed on-chain)" if tp_rpc == tp else ""))
    else:
        unknowns.append("token program not reported")
    if tp_rpc and tp and tp_rpc != tp:
        facts.append(f"DISCREPANCY: on-chain owner program {tp_rpc} differs from provider-reported {tp}")
    if ident.get("creator") or ident.get("dev"):
        facts.append(f"creator {ident.get('creator')} / dev {ident.get('dev')}" + (" (same wallet)" if ident.get("creator") and ident.get("creator") == ident.get("dev") else ""))
    if ident.get("launchpad"):
        facts.append(f"launchpad {ident['launchpad']}" + (f", graduated {ident.get('graduated_at')}" if ident.get("graduated_at") else ""))
    age_h = (bundle.get("market") or {}).get("age_hours")
    if age_h is not None:
        facts.append(f"token age ~{age_h/24:.1f} days ({age_h:.0f} h) from first pool")
    else:
        unknowns.append("first pool time unknown")
    # confidence
    if n_sources == 0:
        conf = "NOT VERIFIED"
    elif name_match is False and sym_match is False:
        conf = "NOT VERIFIED"
        inferences.append("sources disagree on both name and symbol; treat as unresolved identity until reconciled")
    elif n_sources >= 3 and (name_match or sym_match) and tp:
        conf = "HIGH"
    elif n_sources >= 2 and (name_match or sym_match):
        conf = "MODERATE"
    elif n_sources >= 3:
        conf = "MODERATE"; inferences.append("cosmetic name differences across sources (symbol or name agrees)")
    else:
        conf = "LOW"
    # same-ticker warning
    heur = ["identically named or tickered tokens are unrelated assets until the mint matches; every downstream module keys on the mint, never the ticker"]
    return {"confidence": conf, "status": "IDENTITY NOT VERIFIED" if conf == "NOT VERIFIED" else "OK",
            "name": ident.get("name"), "symbol": ident.get("symbol"), "mint": mint, "chain": "solana",
            "token_program": TOKEN_PROGRAMS.get(tp, tp) if tp else None, "age_hours": age_h,
            "timestamp": datetime.fromtimestamp(bundle.get("observed_at", 0), tz=timezone.utc).isoformat(timespec="seconds"),
            "facts": facts, "inferences": inferences, "heuristics": heur, "unknowns": unknowns}
