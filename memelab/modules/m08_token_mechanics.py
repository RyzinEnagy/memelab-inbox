"""08_TOKEN_MECHANICS: SPL vs Token-2022, authorities, extensions, round-trip friction consequence."""
from __future__ import annotations

from typing import Any

TOKEN_2022 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
SPL = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
DANGEROUS_EXT = {"permanentDelegate": "permanent delegate can move or burn any holder's tokens",
                 "nonTransferable": "token is non-transferable (soulbound)",
                 "defaultAccountState": "new token accounts can default to frozen",
                 "transferHook": "a program runs on every transfer and can reject transfers",
                 "confidentialTransferMint": "confidential transfers obscure flows",
                 "interestBearingConfig": "displayed balance changes over time via interest rate (UI amount, not supply)",
                 "mintCloseAuthority": "mint account can be closed and re-created",
                 "transferFeeConfig": "a transfer fee is taken on every transfer"}


def _ext_list(a: dict) -> list[dict]:
    raw = a.get("extensions_rpc") or a.get("extensions")
    out = []
    if isinstance(raw, list):
        for e in raw:
            if isinstance(e, dict):
                out.append({"extension": e.get("extension") or e.get("name") or str(e)[:40], "state": e.get("state") or e})
            else:
                out.append({"extension": str(e), "state": None})
    elif isinstance(raw, dict):
        # RugCheck form: every known extension key present, null/false when absent. Keep only extensions that are set.
        for k, v in raw.items():
            if v is None or v is False:
                continue
            if k == "transferFeeConfig" and isinstance(v, dict):
                nf = v.get("newerTransferFee") or v.get("olderTransferFee") or v
                if not (nf.get("transferFeeBasisPoints") or v.get("transferFeeConfigAuthority") or v.get("withdrawWithheldAuthority")):
                    continue
            if k == "transferHook" and isinstance(v, dict) and not (v.get("programId") or v.get("authority")):
                continue
            if k == "defaultAccountState" and isinstance(v, dict) and "frozen" not in str(v.get("state") or v.get("accountState") or "").lower():
                continue
            if k == "pausableConfig" and isinstance(v, dict) and not v.get("paused") and not v.get("authority"):
                continue
            out.append({"extension": k, "state": v})
    return out


def analyze(bundle: dict[str, Any], depth: dict | None = None) -> dict[str, Any]:
    a = bundle.get("authorities") or {}
    facts, inferences, unknowns, heur = [], [], [], []
    tp = a.get("token_program_rpc") or a.get("token_program") or (bundle.get("identity") or {}).get("token_program")
    std = "Token-2022" if tp == TOKEN_2022 else "SPL Token" if tp == SPL else (tp or None)
    if std:
        facts.append(f"standard: {std}" + (" (on-chain)" if a.get("token_program_rpc") else ""))
    else:
        unknowns.append("token program unknown")
    # authorities with source precedence rpc > rugcheck > jupiter/gt flags
    def auth(name):
        if f"{name}_rpc" in a:
            return a[f"{name}_rpc"], "rpc"
        if name in a:
            return a[name], "rugcheck"
        j = a.get(f"{name}_disabled_jup")
        if j is not None:
            return (None if j else "ACTIVE (address not reported)"), "jupiter"
        g = a.get(f"{name}_gt")
        if g in ("yes", "no"):
            return (None if g == "no" else "ACTIVE (address not reported)"), "geckoterminal"
        return "UNOBSERVED", None
    mint_auth, ms = auth("mint_authority"); frz, fs = auth("freeze_authority")
    mint_active = mint_auth not in (None, "UNOBSERVED"); freeze_active = frz not in (None, "UNOBSERVED")
    if mint_auth == "UNOBSERVED":
        unknowns.append("mint authority unobserved")
    else:
        facts.append(("MINT AUTHORITY ACTIVE: " + str(mint_auth)) if mint_active else "mint authority revoked" + f" ({ms})")
    if frz == "UNOBSERVED":
        unknowns.append("freeze authority unobserved")
    else:
        facts.append(("FREEZE AUTHORITY ACTIVE: " + str(frz)) if freeze_active else "freeze authority revoked" + f" ({fs})")
    # cross-source disagreement
    if "mint_authority" in a and a.get("mint_authority_disabled_jup") is not None and (a["mint_authority"] is None) != bool(a["mint_authority_disabled_jup"]):
        facts.append("DISCREPANCY: rugcheck and jupiter disagree on mint authority status")
    exts = _ext_list(a)
    fee_bps = None; fee_max = None; fee_auth = None; perm = None; hook = None; non_transferable = False; default_frozen = False
    for e in exts:
        name, st = e["extension"], e["state"] if isinstance(e["state"], dict) else {}
        if name == "transferFeeConfig":
            nf = st.get("newerTransferFee") or st.get("olderTransferFee") or {}
            fee_bps = nf.get("transferFeeBasisPoints"); fee_max = nf.get("maximumFee"); fee_auth = st.get("transferFeeConfigAuthority")
        if name == "permanentDelegate":
            perm = st.get("delegate") or "set"
        if name == "transferHook":
            hook = st.get("programId") or "set"
        if name == "nonTransferable":
            non_transferable = True
        if name == "defaultAccountState" and str(st.get("accountState", "")).lower() == "frozen":
            default_frozen = True
        if name in DANGEROUS_EXT:
            facts.append(f"extension {name}: {DANGEROUS_EXT[name]}")
    if a.get("transfer_fee") and fee_bps is None:
        tf = a["transfer_fee"]
        if isinstance(tf, dict):
            fee_bps = tf.get("pct", 0) * 100 if tf.get("pct") is not None else fee_bps
            fee_max = tf.get("maxAmount"); fee_auth = tf.get("authority")
    if std == "Token-2022" and not exts:
        unknowns.append("Token-2022 mint but no extension list observed (fetch RPC getAccountInfo to enumerate)")
    meta_mut = a.get("metadata_mutable")
    if meta_mut is not None:
        facts.append(f"metadata {'MUTABLE' if meta_mut else 'immutable'}" + (f" (update authority {a.get('update_authority')})" if meta_mut and a.get('update_authority') else ""))
        if meta_mut:
            inferences.append("mutable metadata lets the update authority change name, symbol or image later (impersonation / rebrand risk, not a direct fund risk)")
    # friction consequence
    fee_pct = (fee_bps or 0) / 100
    rt = None
    if depth and depth.get("friction_pct") is not None:
        rt = depth["friction_pct"]
    elif fee_pct:
        rt = 2 * fee_pct + 0.5
    if fee_pct:
        facts.append(f"transfer fee {fee_pct:.2f}% per transfer" + (f", capped at {fee_max} base units" if fee_max else "") + (f"; fee authority {fee_auth} can change it" if fee_auth else "; fee authority revoked" if fee_auth is None and fee_bps is not None else ""))
        inferences.append(f"economic consequence: a round trip pays the fee twice ({2*fee_pct:.2f}%) plus DEX fees and impact; the token must rise about {rt:.1f}% before a trade breaks even" if rt else f"economic consequence: round trip pays {2*fee_pct:.2f}% in transfer fees before DEX fees and impact")
        if fee_auth:
            inferences.append("because the fee authority is live, the fee can be raised later; this is a mechanism that could materially change")
    flags = []
    if mint_active: flags.append("MINT_AUTHORITY_ACTIVE")
    if freeze_active: flags.append("FREEZE_AUTHORITY_ACTIVE")
    if perm: flags.append("PERMANENT_DELEGATE")
    if hook: flags.append("TRANSFER_HOOK")
    if non_transferable: flags.append("NON_TRANSFERABLE")
    if default_frozen: flags.append("DEFAULT_FROZEN")
    if fee_pct > 5: flags.append("EXTREME_TRANSFER_FEE")
    honeypot_gt = (bundle.get("social") or {}).get("is_honeypot_gt")
    if honeypot_gt == "yes":
        flags.append("HONEYPOT_FLAG_GT")
    heur.append("an authority that remains active is a mechanism that can change later, even if it has not been used")
    return {"standard": std, "token_program": tp, "mint_authority": mint_auth if mint_active else None, "mint_authority_active": mint_active,
            "freeze_authority": frz if freeze_active else None, "freeze_authority_active": freeze_active,
            "extensions": exts, "transfer_fee_bps": fee_bps, "transfer_fee_pct": fee_pct, "transfer_fee_authority": fee_auth,
            "permanent_delegate": perm, "permanent_delegate_active": bool(perm), "transfer_hook_program": hook,
            "transfer_hook_known": False if hook else None, "transfer_hook_unknown": bool(hook), "non_transferable": non_transferable,
            "metadata_mutable": meta_mut, "update_authority": a.get("update_authority"), "round_trip_friction_pct": rt, "flags": flags,
            "facts": facts, "inferences": inferences, "heuristics": heur, "unknowns": unknowns}
