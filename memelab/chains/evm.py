"""Reusable EVM engine (Base, BNB Chain, Ethereum, Arbitrum, Avalanche, Polygon).

build_bundle(): produces the same bundle shape the Solana modules consume, from DEX Screener + GeckoTerminal (shared parsers),
GoPlus token_security, honeypot.is, KyberSwap route quotes and public-node eth_call results.
mechanics(): chain-specific contract risk in the m08 output contract plus EVM fields (owner, proxy, hidden mint, blacklist, pause,
max wallet/tx, taxes, tax authority, renounce claims, honeypot, LP ownership, source verification).
identity(): the m02 contract for EVM tokens (name/symbol agreement across sources, source verification, official links).

Every field keeps its source. Missing data is UNKNOWN; UNKNOWN never improves a grade.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from ..normalize import build_bundle as _solana_shape_bundle, _f
from . import registry as R

DEAD = {"0x000000000000000000000000000000000000dead", "0x0000000000000000000000000000000000000000", "0x0000000000000000000000000000000000000001"}
KNOWN_LOCKERS = ("unicrypt", "team.finance", "pinklock", "pinksale", "mudra", "dxlock", "flokifi", "uncx", "gempad", "onlymoons", "lock")


def _lower_ds(bodies: dict[str, Any]) -> dict[str, Any]:
    """DEX Screener returns checksummed EVM addresses; the system compares lowercase."""
    out = {}
    for k, v in bodies.items():
        if k.startswith("ds") and isinstance(v, list):
            vv = []
            for p in v:
                if not isinstance(p, dict):
                    continue
                p = dict(p)
                for side in ("baseToken", "quoteToken"):
                    t = dict(p.get(side) or {})
                    if t.get("address"):
                        t["address"] = t["address"].lower()
                    p[side] = t
                if p.get("pairAddress"):
                    p["pairAddress"] = p["pairAddress"].lower()
                vv.append(p)
            out[k] = vv
        else:
            out[k] = v
    return out


def _goplus_for(bodies: dict[str, Any], chain: str, addr: str) -> dict | None:
    for k, v in bodies.items():
        if k.startswith(f"goplus:{chain}") and isinstance(v, dict):
            rec = v.get(addr) or v.get(addr.lower())
            if isinstance(rec, dict):
                return rec
    return None


def _hex_int(x: str | None) -> int | None:
    try:
        return int(x, 16) if x and x not in ("0x",) else None
    except ValueError:
        return None


def build_bundle(chain: str, addr: str, bodies: dict[str, Any], observed_at: float | None = None, native_price: float | None = None) -> dict[str, Any]:
    cfg = R.get(chain)
    addr = R.norm_address(chain, addr)
    bodies = _lower_ds(bodies)
    b = _solana_shape_bundle(addr, bodies, observed_at=observed_at, sol_price=None)
    b["chain"] = chain
    src, ident, mk, a = b["sources"], b["identity"], b["market"], b["authorities"]
    ident["chain"] = chain
    ident["token_standard"] = cfg["token_standards"][0]
    mk["native_symbol"] = cfg["native_symbol"]; mk["native_decimals"] = 18
    if native_price:
        mk["native_price"] = native_price; src["native_price"] = "coingecko"
    # restrict DS/GT pools to this chain (DS batches can carry other chains only if mis-planned; GT is per network)
    b["pools"] = [p for p in b["pools"] if p.get("pool")]

    # ---- GoPlus ----
    gp = _goplus_for(bodies, chain, addr)
    b["evm"] = {}
    if gp:
        e = b["evm"]
        for k in ("is_open_source", "is_proxy", "is_mintable", "can_take_back_ownership", "hidden_owner", "selfdestruct", "external_call", "cannot_buy", "cannot_sell_all",
                  "slippage_modifiable", "is_honeypot", "honeypot_with_same_creator", "transfer_pausable", "is_blacklisted", "is_whitelisted", "is_anti_whale", "anti_whale_modifiable",
                  "trading_cooldown", "personal_slippage_modifiable", "is_in_dex", "is_airdrop_scam", "trust_list", "gas_abuse", "is_in_cex"):
            v = gp.get(k)
            e[k] = (v == "1" or v is True) if v not in (None, "") else None
        e["buy_tax"] = _f(gp.get("buy_tax")); e["sell_tax"] = _f(gp.get("sell_tax")); e["transfer_tax"] = _f(gp.get("transfer_tax"))
        for k in ("buy_tax", "sell_tax", "transfer_tax"):
            if e[k] is not None:
                e[k] = round(e[k], 4)
        e["owner_address"] = gp.get("owner_address") or None; e["owner_percent"] = _f(gp.get("owner_percent")); e["owner_balance"] = _f(gp.get("owner_balance"))
        e["creator_address"] = gp.get("creator_address"); e["creator_percent"] = _f(gp.get("creator_percent"))
        e["holder_count"] = int(gp["holder_count"]) if str(gp.get("holder_count") or "").isdigit() else None
        e["lp_holder_count"] = int(gp["lp_holder_count"]) if str(gp.get("lp_holder_count") or "").isdigit() else None
        e["total_supply"] = _f(gp.get("total_supply")); e["other_risks"] = gp.get("other_potential_risks"); e["note"] = gp.get("note")
        e["dex"] = gp.get("dex") or []
        ident.setdefault("name", gp.get("token_name")); ident.setdefault("symbol", gp.get("token_symbol"))
        ident["goplus_name"], ident["goplus_symbol"] = gp.get("token_name"), gp.get("token_symbol")
        ident["creator"] = e["creator_address"]; src["creator"] = "goplus.token_security"
        ident["owner"] = e["owner_address"]
        if e["holder_count"] is not None:
            b["holders"]["total"] = e["holder_count"]; src["holder_count"] = "goplus.token_security"
            mk.setdefault("holder_count", e["holder_count"])
        if mk.get("total_supply") is None and e["total_supply"]:
            mk["total_supply"] = e["total_supply"]; src["total_supply"] = "goplus.token_security"
        pools = {p["pool"] for p in b["pools"]}
        top = []
        for i, h in enumerate(gp.get("holders") or []):
            ad = (h.get("address") or "").lower()
            pct = _f(h.get("percent"))
            top.append({"account": ad, "owner": ad, "pct": pct * 100 if pct is not None else None, "amount": _f(h.get("balance")), "insider": False,
                        "tag": h.get("tag"), "is_contract": h.get("is_contract") in (1, "1", True), "is_locked": h.get("is_locked") in (1, "1", True),
                        "is_pool": ad in pools or any(ad == (d.get("pair") or "").lower() for d in e["dex"])})
        b["holders"]["top"] = top
        src["holders"] = "goplus.token_security"
        # LP holders -> attach to the largest known pool (GoPlus reports LP token holders without naming the pool)
        lph = gp.get("lp_holders") or []
        if lph:
            locked = 0.0; known = 0.0; holders = []
            for h in lph:
                ad = (h.get("address") or "").lower(); pct = _f(h.get("percent"))
                if pct is None:
                    continue
                known += pct
                is_dead = ad in DEAD; is_locked = h.get("is_locked") in (1, "1", True) or any(x in (h.get("tag") or "").lower() for x in KNOWN_LOCKERS)
                if is_dead or is_locked:
                    locked += pct
                holders.append({"owner": ad, "account": ad, "pct": pct * 100, "insider": False, "tag": h.get("tag"), "locked": is_locked, "burned": is_dead, "nft": bool(h.get("NFT_list"))})
            lpinfo = {"locked_pct": (locked / known * 100) if known else None, "holders": sorted(holders, key=lambda h: -(h["pct"] or 0)), "lp_total_supply": _f(gp.get("lp_total_supply")),
                      "lp_holder_count": e["lp_holder_count"], "source": "goplus.lp_holders", "covered_pct": known * 100}
            target = max(b["pools"], key=lambda p: p.get("reserve_usd") or 0) if b["pools"] else None
            if target is not None:
                target["lp"] = lpinfo
            else:
                b["pools"].append({"pool": None, "dex": (e["dex"][0] or {}).get("name") if e["dex"] else None, "quote": None, "quote_symbol": None, "created": None, "reserve_usd": _f((e["dex"][0] or {}).get("liquidity")) if e["dex"] else None,
                                   "base_reserve": None, "quote_reserve": None, "vol_24h": None, "vol_1h": None, "txns_h24": None, "price": None, "source": "goplus", "lp": lpinfo, "market_type": None})
            src["lp"] = "goplus.lp_holders"
    # ---- honeypot.is ----
    hp = next((v for k, v in bodies.items() if k.startswith(f"hp:{chain}:{addr}") and isinstance(v, dict)), None)
    if hp:
        b["evm"]["hp"] = {"is_honeypot": (hp.get("honeypotResult") or {}).get("isHoneypot"), "reason": (hp.get("honeypotResult") or {}).get("honeypotReason"),
                          "sim_ok": hp.get("simulationSuccess"), "sim_error": hp.get("simulationError"), "buy_tax": _f((hp.get("sim") or {}).get("buyTax")), "sell_tax": _f((hp.get("sim") or {}).get("sellTax")),
                          "transfer_tax": _f((hp.get("sim") or {}).get("transferTax")), "buy_gas": (hp.get("sim") or {}).get("buyGas"), "sell_gas": (hp.get("sim") or {}).get("sellGas"),
                          "flags": hp.get("flags") or [], "risk": hp.get("risk"), "risk_level": hp.get("riskLevel"), "open_source": (hp.get("contract") or {}).get("openSource"),
                          "is_proxy": (hp.get("contract") or {}).get("isProxy"), "pair": hp.get("pair"), "total_holders": (hp.get("token") or {}).get("totalHolders")}
        ident["hp_name"], ident["hp_symbol"] = (hp.get("token") or {}).get("name"), (hp.get("token") or {}).get("symbol")
        ident.setdefault("decimals", (hp.get("token") or {}).get("decimals"))
        src["honeypot"] = "honeypot.is"
    # ---- eth_call ----
    rpc = {}
    for k, v in bodies.items():
        if k.startswith(f"rpc_evm:{chain}:") and k.endswith(f":{addr}") and isinstance(v, dict):
            what = k.split(":")[2]
            rpc[what] = v.get("result") if "result" in v else {"error": v.get("error")}
    if rpc:
        b["rpc_evm"] = rpc
        ts = _hex_int(rpc.get("totalSupply")) if isinstance(rpc.get("totalSupply"), str) else None
        dec = _hex_int(rpc.get("decimals")) if isinstance(rpc.get("decimals"), str) else None
        if dec is not None and 0 <= dec <= 36:
            a["decimals_rpc"] = dec; ident.setdefault("decimals", dec)
        if ts is not None:
            a["supply_raw_rpc"] = str(ts)
            if dec is not None and mk.get("total_supply") is None:
                mk["total_supply"] = ts / 10 ** dec; src["total_supply"] = "evm_rpc.totalSupply"
        own = rpc.get("owner")
        if isinstance(own, str) and len(own) == 66:
            a["owner_rpc"] = "0x" + own[-40:]
        elif isinstance(own, dict) and own.get("error"):
            a["owner_rpc"] = "NO_OWNER_FUNCTION"  # owner() reverted or absent: not Ownable, or renounced via a different pattern
        code = rpc.get("code")
        if isinstance(code, str):
            a["code_size"] = max((len(code) - 2) // 2, 0)
            a["is_contract_rpc"] = a["code_size"] > 0
        src["rpc"] = f"{cfg['rpc']}"
    # ---- KyberSwap quotes -> bundle quotes ----
    for k, v in bodies.items():
        if k.startswith(f"kq:{chain}:") and isinstance(v, dict):
            parts = k.split(":")
            if len(parts) != 5 or parts[4] != addr:
                continue
            side, usd = parts[2], float(parts[3])
            if v.get("error") or not v.get("amountOut"):
                b["quotes"][side][usd] = {"status": "NO_ROUTE" if "route" in str(v.get("error", "")).lower() or v.get("code") in (4008, 4221) else "ERROR", "error": v.get("error") or v.get("code")}
            else:
                ai, ao = _f(v.get("amountInUsd")), _f(v.get("amountOutUsd"))
                impact = (1 - ao / ai) if ai and ao and ai > 0 else None
                route = []
                for path in v.get("route") or []:
                    for hop in path:
                        route.append([hop[0], hop[1], None, hop[3], hop[4], hop[5], hop[6]])
                b["quotes"][side][usd] = {"in": _f(v.get("amountIn")), "out": _f(v.get("amountOut")), "impact": impact, "usd": ai, "usd_out": ao, "gas_usd": _f(v.get("gasUsd")),
                                          "route": route, "status": "OK"}
    if b["quotes"]["BUY"] or b["quotes"]["SELL"]:
        src["quotes"] = "kyberswap.routes"
    # ---- identity agreement across EVM sources ----
    names = {s: ident.get(f"{s}_name") for s in ("ds", "gt", "goplus", "hp")}
    present = {s: n for s, n in names.items() if n}
    ident["sources_agreeing"] = len(present)
    ident["name_matches"] = (len({n.strip().lower() for n in present.values()}) == 1) if len(present) >= 2 else None
    syms = {s: ident.get(f"{s}_symbol") for s in ("ds", "gt", "goplus", "hp")}
    ps = {s: n for s, n in syms.items() if n}
    ident["symbol_matches"] = (len({n.strip().upper() for n in ps.values()}) == 1) if len(ps) >= 2 else None
    ident["primary_pool"] = max(b["pools"], key=lambda p: p.get("reserve_usd") or 0)["pool"] if b["pools"] else None
    ident["explorer_url"] = f"{cfg['explorer']}{addr}"
    return b


def mechanics(bundle: dict[str, Any], depth: dict | None = None) -> dict[str, Any]:
    """EVM contract risk. Same keys m24 reads from the Solana mechanics module, plus EVM-specific fields and flags."""
    e = bundle.get("evm") or {}
    a = bundle.get("authorities") or {}
    hp = e.get("hp") or {}
    facts, inferences, heur, unknowns, flags = [], [], [], [], []
    if not e and not hp and not a.get("owner_rpc"):
        return {"standard": (bundle.get("identity") or {}).get("token_standard"), "flags": ["CONTRACT_RISK_UNKNOWN"], "contract_risk": "UNKNOWN",
                "mint_authority_active": None, "freeze_authority_active": None, "permanent_delegate_active": None, "transfer_fee_bps": None,
                "facts": [], "inferences": [], "heuristics": [], "unknowns": ["no GoPlus, honeypot.is or RPC data: every contract check is UNKNOWN"]}

    def tri(k):  # True / False / None(unknown)
        return e.get(k)

    # ownership
    owner = e.get("owner_address") or (a.get("owner_rpc") if a.get("owner_rpc") not in (None, "NO_OWNER_FUNCTION") else None)
    renounced = owner is not None and owner.lower() in DEAD
    if owner is None and (a.get("owner_rpc") == "NO_OWNER_FUNCTION" or (e and e.get("owner_address") == "")):
        facts.append("no owner() / owner address reported (not Ownable, or renounced through a non-standard pattern)")
        owner_state = "NONE_REPORTED"
    elif renounced:
        facts.append(f"ownership renounced: owner is {owner[:10]}.."); owner_state = "RENOUNCED"
    elif owner:
        facts.append(f"contract owner {owner[:10]}.. is a live address" + (f" holding {e['owner_percent'] * 100:.1f}% of supply" if e.get("owner_percent") else "")); owner_state = "ACTIVE"
    else:
        owner_state = "UNKNOWN"; unknowns.append("owner address")
    if tri("hidden_owner"):
        flags.append("HIDDEN_OWNER"); facts.append("GoPlus: hidden owner (ownership can be exercised despite an apparent renounce)")
    if tri("can_take_back_ownership"):
        flags.append("OWNERSHIP_RECLAIMABLE"); facts.append("GoPlus: ownership can be taken back")
    # proxy / source
    proxy = tri("is_proxy") if tri("is_proxy") is not None else hp.get("is_proxy")
    if proxy:
        flags.append("UPGRADEABLE_PROXY"); facts.append("proxy contract: logic can be replaced by whoever controls the proxy admin")
    open_src = tri("is_open_source") if tri("is_open_source") is not None else hp.get("open_source")
    if open_src is False:
        flags.append("SOURCE_UNVERIFIED"); facts.append("contract source not verified on the explorer")
    elif open_src is None:
        unknowns.append("source verification")
    # mint / pause / blacklist / limits
    mint_active = tri("is_mintable")
    if mint_active:
        flags.append("MINT_FUNCTION"); facts.append("GoPlus: supply can be minted (owner can dilute holders)")
    if tri("transfer_pausable"):
        flags.append("TRANSFER_PAUSABLE"); facts.append("transfers can be paused")
    if tri("is_blacklisted"):
        flags.append("BLACKLIST"); facts.append("blacklist function present (specific wallets can be blocked from selling)")
    if tri("is_whitelisted"):
        facts.append("whitelist function present (often tax exemptions; check who is exempt)")
    if tri("is_anti_whale"):
        facts.append("max wallet / max transaction limits present" + (" and modifiable by owner" if tri("anti_whale_modifiable") else ""))
        if tri("anti_whale_modifiable"):
            flags.append("LIMITS_MODIFIABLE")
    if tri("trading_cooldown"):
        facts.append("trading cooldown between transactions")
    if tri("cannot_sell_all"):
        flags.append("CANNOT_SELL_ALL"); facts.append("holders cannot sell their whole balance in one transaction")
    if tri("cannot_buy"):
        flags.append("CANNOT_BUY")
    if tri("selfdestruct"):
        flags.append("SELFDESTRUCT")
    if tri("external_call"):
        facts.append("external calls in transfer path (behaviour can depend on another contract)")
    # taxes: GoPlus static vs honeypot.is simulated
    bt, st = e.get("buy_tax"), e.get("sell_tax")
    sbt, sst = hp.get("buy_tax"), hp.get("sell_tax")
    buy_pct = round(sbt if sbt is not None else (bt * 100 if bt is not None else None), 2) if (sbt is not None or bt is not None) else None
    sell_pct = round(sst if sst is not None else (st * 100 if st is not None else None), 2) if (sst is not None or st is not None) else None
    if buy_pct is None and sell_pct is None:
        unknowns.append("buy/sell tax")
    else:
        facts.append(f"tax buy {buy_pct if buy_pct is not None else '?'}% / sell {sell_pct if sell_pct is not None else '?'}%" + (" (simulated, honeypot.is)" if sbt is not None else " (static, GoPlus)"))
        if bt is not None and sbt is not None and abs(bt * 100 - sbt) > 2:
            inferences.append(f"static tax ({bt * 100:.0f}%) and simulated tax ({sbt:.0f}%) disagree: tax may be dynamic or wallet-dependent")
    if tri("slippage_modifiable") or tri("personal_slippage_modifiable"):
        flags.append("TAX_MODIFIABLE"); facts.append("tax rate can be changed by the owner" + (" per wallet" if tri("personal_slippage_modifiable") else ""))
    total_tax = (buy_pct or 0) + (sell_pct or 0)
    if sell_pct is not None and sell_pct > 10:
        flags.append("HIGH_SELL_TAX")
    if total_tax > 20:
        flags.append("EXTREME_TAX")
    # honeypot
    hp_flag = tri("is_honeypot") or hp.get("is_honeypot")
    if hp_flag:
        flags.append("HONEYPOT"); facts.append("flagged honeypot: " + str(hp.get("reason") or "GoPlus is_honeypot=1"))
    elif hp.get("sim_ok") is False:
        flags.append("SIMULATION_FAILED"); facts.append(f"honeypot.is could not simulate a sell: {hp.get('sim_error')}")
    elif hp.get("is_honeypot") is False:
        facts.append("honeypot.is buy/sell simulation succeeded")
    if tri("honeypot_with_same_creator"):
        flags.append("CREATOR_PRIOR_HONEYPOT"); facts.append("creator deployed honeypots before (GoPlus)")
    if tri("is_airdrop_scam"):
        flags.append("AIRDROP_SCAM")
    if hp.get("flags"):
        facts.append("honeypot.is flags: " + ", ".join(str(f.get("flag") if isinstance(f, dict) else f) for f in hp["flags"][:6]))
    # LP ownership summary (details in m07)
    lp = next((p.get("lp") for p in bundle.get("pools") or [] if p.get("lp")), None)
    if lp:
        lk = lp.get("locked_pct")
        if lk is not None:
            facts.append(f"LP tokens locked/burned {lk:.0f}% (GoPlus lp_holders, {lp.get('covered_pct', 0):.0f}% of LP supply covered)")
        if any(h.get("nft") for h in lp.get("holders") or []):
            heur.append("concentrated-liquidity (V3/V4) positions are NFTs: 'locked %' understates removable liquidity unless the NFT itself is locked")
    else:
        unknowns.append("LP ownership")
    # consequence: round-trip friction = taxes + two swaps' gas relative to a $1000 position
    rt = total_tax
    gas = (depth or {}).get("gas_usd_round_trip") if depth else None
    cfg = R.CHAINS.get(bundle.get("chain") or "", {})
    gas = gas if gas is not None else (cfg.get("typical_gas_usd") or 0) * 2
    rt_1000 = rt + gas / 1000 * 100
    facts.append(f"round-trip friction about {rt_1000:.1f}% on a $1,000 position (taxes {rt:.1f}% + ~${gas:.2f} gas)")
    callable_ = owner_state in ("ACTIVE", "UNKNOWN") or bool(tri("hidden_owner")) or bool(tri("can_take_back_ownership"))
    # overall
    fatal = {"HONEYPOT", "CANNOT_BUY", "EXTREME_TAX", "HIDDEN_OWNER"}
    severe = {"MINT_FUNCTION", "TRANSFER_PAUSABLE", "BLACKLIST", "TAX_MODIFIABLE", "UPGRADEABLE_PROXY", "OWNERSHIP_RECLAIMABLE", "SELFDESTRUCT", "CANNOT_SELL_ALL", "CREATOR_PRIOR_HONEYPOT", "SIMULATION_FAILED"}
    if fatal & set(flags):
        risk = "FATAL"
    elif severe & set(flags):
        risk = "HIGH" if owner_state == "ACTIVE" or "UPGRADEABLE_PROXY" in flags or "SIMULATION_FAILED" in flags else "ELEVATED"
        inferences.append("dangerous functions exist but ownership is renounced: they cannot be exercised unless a hidden owner or proxy exists" if owner_state != "ACTIVE" and risk == "ELEVATED" else "dangerous functions exist and an owner can call them")
    elif unknowns and not facts:
        risk = "UNKNOWN"
    else:
        risk = "LOW" if owner_state in ("RENOUNCED", "NONE_REPORTED") and open_src else "MODERATE"
    heur.append("a function that exists is a mechanism that can be used later, even if it has not been; a renounce claim is checked against the owner address, not the project's word")
    return {"standard": (bundle.get("identity") or {}).get("token_standard") or "ERC-20", "token_program": None, "contract_risk": risk, "owner": owner, "owner_state": owner_state,
            "renounced": renounced if owner else None, "proxy": proxy, "source_verified": open_src,
            # m24-compatible keys: on EVM, a live mint function maps to mint authority, pause/blacklist to freeze, taxes to transfer fee
            # a dangerous function is "active" only while someone can call it: live owner, hidden owner or reclaimable ownership
            "mint_authority": owner if (mint_active and callable_) else None, "mint_authority_active": (bool(mint_active) and callable_) if mint_active is not None else None,
            "freeze_authority": owner if ((tri("transfer_pausable") or tri("is_blacklisted")) and callable_) else None,
            "freeze_authority_active": (bool(tri("transfer_pausable") or tri("is_blacklisted")) and callable_) if (tri("transfer_pausable") is not None or tri("is_blacklisted") is not None) else None,
            "dangerous_functions_dormant": bool((mint_active or tri("transfer_pausable") or tri("is_blacklisted")) and not callable_),
            "permanent_delegate": None, "permanent_delegate_active": False, "transfer_hook_unknown": False, "non_transferable": False,
            "transfer_fee_bps": int(round(total_tax * 100)) if (buy_pct is not None or sell_pct is not None) else None, "transfer_fee_pct": total_tax if (buy_pct is not None or sell_pct is not None) else None,
            "buy_tax_pct": buy_pct, "sell_tax_pct": sell_pct, "tax_modifiable": bool(tri("slippage_modifiable") or tri("personal_slippage_modifiable")), "metadata_mutable": None,
            "honeypot": bool(hp_flag), "round_trip_friction_pct": rt_1000, "flags": flags, "facts": facts, "inferences": inferences, "heuristics": heur, "unknowns": unknowns}


def identity(bundle: dict[str, Any]) -> dict[str, Any]:
    ident = bundle.get("identity") or {}
    mk = bundle.get("market") or {}
    addr = bundle.get("mint") or ""
    facts, inferences, heur, unknowns = [], [], [], []
    if not (addr.startswith("0x") and len(addr) == 42):
        return {"confidence": "NOT VERIFIED", "status": "IDENTITY NOT VERIFIED", "facts": [], "inferences": [], "heuristics": [], "unknowns": ["address malformed for an EVM chain"]}
    a = bundle.get("authorities") or {}
    if a.get("is_contract_rpc") is False:
        return {"confidence": "NOT VERIFIED", "status": "IDENTITY NOT VERIFIED", "facts": ["eth_getCode returned no bytecode at this address"], "inferences": [], "heuristics": [], "unknowns": []}
    n = ident.get("sources_agreeing") or 0
    facts.append(f"{n} market/security source(s) describe this address" + (": " + ", ".join(s for s in ("ds", "gt", "goplus", "hp") if ident.get(f"{s}_name")) if n else ""))
    if ident.get("name_matches") is False:
        facts.append("sources disagree on the token name: " + "; ".join(f"{s} {ident.get(f'{s}_name')}" for s in ("ds", "gt", "goplus", "hp") if ident.get(f"{s}_name")))
    if ident.get("symbol_matches") is False:
        facts.append("sources disagree on the symbol")
    if a.get("is_contract_rpc"):
        facts.append(f"bytecode present on {bundle.get('chain')} ({a.get('code_size')} bytes)")
    if (bundle.get("evm") or {}).get("is_open_source") is True:
        facts.append("source verified")
    links = {k: v for k, v in (bundle.get("social") or {}).items() if k in ("website", "twitter", "telegram", "discord_url") and v}
    if links:
        facts.append("official links from screeners: " + ", ".join(f"{k} {v}" for k, v in links.items()))
    else:
        unknowns.append("official links (none listed on DEX Screener / GeckoTerminal)")
    heur.append("the same ticker exists on many chains; identity is chain + contract address, never the symbol")
    if n >= 2 and ident.get("name_matches") is not False and ident.get("symbol_matches") is not False and (a.get("is_contract_rpc") or (bundle.get("evm") or {}).get("is_in_dex")):
        conf = "HIGH"
    elif n >= 2 and ident.get("name_matches") is not False:
        conf = "MODERATE"
    elif n >= 1:
        conf = "LOW"; inferences.append("single-source identity: the pair data exists but nothing independent confirms the name")
    else:
        conf = "NOT VERIFIED"
    age_h = mk.get("age_hours")
    return {"confidence": conf, "status": "IDENTITY NOT VERIFIED" if conf == "NOT VERIFIED" else "OK", "name": ident.get("name"), "symbol": ident.get("symbol"), "mint": addr,
            "chain": bundle.get("chain"), "token_program": ident.get("token_standard"), "token_standard": ident.get("token_standard"), "primary_pool": ident.get("primary_pool"),
            "explorer_url": ident.get("explorer_url"), "official_links": links, "age_hours": age_h,
            "timestamp": datetime.fromtimestamp(bundle.get("observed_at", 0), tz=timezone.utc).isoformat(timespec="seconds"),
            "facts": facts, "inferences": inferences, "heuristics": heur, "unknowns": unknowns}


def execution_profile(bundle: dict[str, Any], depth: dict | None, mech: dict | None) -> dict[str, Any]:
    """Realistic execution comparison inputs: gas, taxes, routing, impact at the account's size."""
    chain = bundle.get("chain") or "solana"
    cfg = R.CHAINS.get(chain, {})
    q = bundle.get("quotes") or {}
    gas = [v.get("gas_usd") for side in ("BUY", "SELL") for v in (q.get(side) or {}).values() if isinstance(v, dict) and v.get("gas_usd") is not None]
    gas_rt = (sum(gas) / len(gas) * 2) if gas else (cfg.get("typical_gas_usd") or 0) * 2
    tax = (mech or {}).get("transfer_fee_pct") or 0
    hops = 0
    for side in ("BUY", "SELL"):
        for v in (q.get(side) or {}).values():
            if isinstance(v, dict) and v.get("route"):
                hops = max(hops, len(v["route"]))
    return {"chain": chain, "router": cfg.get("router"), "gas_round_trip_usd": gas_rt, "tax_round_trip_pct": tax, "max_route_legs": hops,
            "exit_capacity_usd_3pct": (depth or {}).get("exit_capacity_usd_3pct"), "entry_capacity_usd_1_5pct": (depth or {}).get("entry_capacity_usd_1_5pct"),
            "block_time_s": cfg.get("block_time_s"), "friction_pct_on_1000": tax + gas_rt / 10,
            "note": "friction = taxes + two swaps' gas; impact is read from the depth curve at the intended size, never assumed"}
