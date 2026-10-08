"""PRE_LAUNCH_DISCOVERY + LAUNCH_CALENDAR + identity states.

Every candidate gets exactly one identity state:
  A ANNOUNCED_NO_CONTRACT     announced (news, Genesis schedule, manual note), no publicly established contract
  B DEPLOYED_NOT_TRADING      contract/mint exists on chain, no market yet
  C BONDING_CURVE             launchpad curve active: price forms inside the launch mechanism, no DEX pool
  D LIQUIDITY_PENDING         curve finished or token exists, DEX pool expected but not observed
  E JUST_LAUNCHED             DEX trading observed, within the new-launch window
A contract counts as established only when a chain index (launchpad API built from chain data, GeckoTerminal/Jupiter/RugCheck
indexing, or an RPC read) reports it. A project's own claim is not enough. No contract -> CONTRACT NOT YET VERIFIED.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Any

from .. import db

PUMP_CURVE_TOKENS = 793_100_000      # tokens sold through the pump.fun curve (of 1B)
PUMP_LP_TOKENS = 206_900_000         # tokens reserved for the migration pool
PUMP_GRAD_MCAP_SOL = 410.9           # curve completes at virtual reserves 115 SOL / 279.9M tokens -> 410.9 SOL market cap
PUMP_GRAD_LP_SOL = 79.0              # SOL that reaches the AMM pool after the migration fee (approx.; observed liquidity replaces it)
NEW_LAUNCH_HOURS = 72
# only these lists sample launches by creation time; others (by market cap, livestream, recent trade) are selected samples and stay out of rates
NEWEST_SOURCES = {"pump:new", "ray:new", "clanker:new", "zora:new", "jup:recent", "rug:new", "gt:new:solana", "gt:new:base", "gt:new:bsc"}
STATES = {"A": "ANNOUNCED - NO CONTRACT", "B": "CONTRACT DEPLOYED - NOT TRADING", "C": "LAUNCHPAD / BONDING CURVE ACTIVE", "D": "LIQUIDITY PENDING", "E": "JUST LAUNCHED"}
LAUNCH_RX = re.compile(r"\b(token launch|launches? (?:a |its |the )?(?:token|coin|memecoin)|TGE|token generation|airdrop|presale|pre-sale|fair launch|launching (?:a |its )?(?:token|coin)|\$[A-Z]{2,10} (?:launch|goes live|listing))\b", re.I)


def _f(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def _iso(s):
    if not s:
        return None
    if isinstance(s, (int, float)):
        return s / 1000 if s > 1e11 else float(s)
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _cand(chain, contract, **kw) -> dict[str, Any]:
    c = {"launch_id": f"{chain}:{contract.lower() if contract and contract.startswith('0x') else contract}" if contract else kw.pop("launch_id"),
         "chain": chain, "contract": (contract.lower() if contract and contract.startswith("0x") else contract), "sources": [], "links": {}, "obs": {}, "tokenomics": {}, "flags": [], "signals": {}}
    c.update(kw)
    return c


def _merge(into: dict, c: dict) -> None:
    for k, v in c.items():
        if k in ("sources",):
            into["sources"] = sorted(set(into["sources"]) | set(v))
        elif k in ("links", "obs", "tokenomics", "signals"):
            for kk, vv in v.items():
                if vv is not None and into[k].get(kk) is None:
                    into[k][kk] = vv
        elif k == "flags":
            into["flags"] = sorted(set(into["flags"]) | set(v))
        elif k == "state":
            # the most advanced observed state wins (E > D > C > B > A)
            if "ABCDE".index(v) > "ABCDE".index(into.get("state", "A")):
                into["state"] = v
        elif into.get(k) is None and v is not None:
            into[k] = v


def from_bodies(bodies: dict[str, Any], t: float, sol_price: float | None, eth_price: float | None) -> dict[str, dict]:
    out: dict[str, dict] = {}

    def add(c):
        if c["launch_id"] in out:
            _merge(out[c["launch_id"]], c)
        else:
            out[c["launch_id"]] = c

    # ---- pump.fun ----
    for k, v in bodies.items():
        if k.startswith("pump:coin:") and isinstance(v, dict):
            v = [v]
        if not (k.startswith("pump:") and not k.startswith("pump:creator")) or not isinstance(v, list):
            continue
        for r in v:
            if not r.get("mint") or r.get("is_banned"):
                continue
            rtok = _f(r.get("real_token_reserves"))
            dec = int(r.get("base_decimals") or 6)
            progress = None
            if rtok is not None:
                progress = max(0.0, min(100.0, (1 - (rtok / 10 ** dec) / PUMP_CURVE_TOKENS) * 100))
            migrated = bool(r.get("complete")) or (rtok == 0 and _f(r.get("real_sol_reserves")) == 0)
            state = "E" if migrated else ("D" if progress is not None and progress >= 99.9 else "C")
            mc = _f(r.get("usd_market_cap"))
            c = _cand("solana", r["mint"], project=r.get("name"), symbol=r.get("symbol"), launchpad="pump.fun", state=state, creator=r.get("creator"),
                      created_at=_iso(r.get("created_timestamp")), contract_verified=1, contract_source="pump.fun index (chain-derived)",
                      pool=r.get("pool_address") if migrated else None, sources=["pump:" + k.split(":")[1]], bonding_curve=r.get("bonding_curve"))
            c["links"] = {"twitter": r.get("twitter"), "telegram": r.get("telegram"), "website": r.get("website")}
            c["obs"] = {"mcap_usd": mc, "fdv_usd": mc, "curve_progress_pct": progress, "raised_quote": (_f(r.get("real_sol_reserves")) or 0) / 1e9 if not migrated else None,
                        "quote_symbol": "SOL", "replies": r.get("reply_count"), "is_live": 1 if r.get("is_currently_live") else 0, "ath_usd": _f(r.get("ath_market_cap")),
                        "last_trade_at": _iso(r.get("last_trade_timestamp"))}
            c["tokenomics"] = {"basis": "MECHANISM (pump.fun curve rules)", "total_supply": 1_000_000_000, "curve_sale_pct": 79.31, "lp_reserved_pct": 20.69,
                               "team_alloc_pct_mechanism": 0.0, "vesting": "none by mechanism", "transfer_fee_bps": r.get("transfer_fee_bps"),
                               "transfer_hook": r.get("transfer_hook_program"), "token_program": r.get("token_program")}
            if sol_price:
                c["expected"] = {"grad_mcap_usd": PUMP_GRAD_MCAP_SOL * sol_price, "grad_liquidity_usd": 2 * PUMP_GRAD_LP_SOL * sol_price,
                                 "basis": "PROJECTED from curve constants; replaced by observed pool liquidity after migration"}
            if r.get("nsfw"):
                c["flags"].append("NSFW")
            add(c)
    # ---- Raydium LaunchLab / Bonk.fun ----
    for k, v in bodies.items():
        if not k.startswith("ray:") or k.startswith("ray:user") or not isinstance(v, list):
            continue
        for r in v:
            if not r.get("mint"):
                continue
            dec = int(r.get("decimals") or 6)
            sup = _f(r.get("supply"))
            sale, locked = _f(r.get("totalSellA")), _f(r.get("totalLockedAmount"))
            fr = _f(r.get("finishingRate"))
            state = "E" if (fr is not None and fr >= 100 and r.get("migrateType") is not None and _f(r.get("marketCap")) and fr >= 100) else ("D" if fr is not None and fr >= 99.9 else "C")
            if fr is not None and fr >= 100:
                state = "E"
            tk = {"basis": "MECHANISM (LaunchLab pool config, chain-derived)", "total_supply": sup / 10 ** dec if sup else None}
            if sup and sale is not None:
                tk["curve_sale_pct"] = sale / sup * 100
            if sup and locked is not None:
                tk["locked_vesting_pct"] = locked / sup * 100
                tk["vesting"] = f"cliff {int(_f(r.get('cliffPeriod')) or 0) / 86400:.1f}d, unlock {int(_f(r.get('unlockPeriod')) or 0) / 86400:.1f}d" if locked else "none"
            if "curve_sale_pct" in tk:
                tk["lp_reserved_pct"] = max(0.0, 100 - tk["curve_sale_pct"] - (tk.get("locked_vesting_pct") or 0))
            tk["transfer_fee_bps"] = r.get("transferFeeBasePoints")
            c = _cand("solana", r["mint"], project=r.get("name"), symbol=r.get("symbol"), launchpad="raydium-launchlab" if not r.get("platform") else f"raydium-launchlab:{r.get('platform')}",
                      state=state, creator=r.get("creator"), created_at=_iso(r.get("createAt")), contract_verified=1, contract_source="Raydium LaunchLab index (chain-derived)",
                      sources=[k], tokenomics=tk)
            c["links"] = {"twitter": r.get("twitter"), "telegram": r.get("telegram"), "website": r.get("website")}
            c["obs"] = {"mcap_usd": _f(r.get("marketCap")), "curve_progress_pct": fr, "raised_quote": None, "quote_symbol": r.get("quote"), "vol_usd": _f(r.get("volumeU"))}
            add(c)
    # ---- Clanker (Base) ----
    for k, v in bodies.items():
        if not k.startswith("clanker:new") or not isinstance(v, list):
            continue
        for r in v:
            if not r.get("contract_address") or r.get("chain_id") not in (8453, None):
                continue
            ext = r.get("ext") or {}
            vault = ext.get("vault") or {}
            air = ext.get("airdrop") or {}
            vpct = _f(vault.get("percentage")) or 0.0
            apct = _f(air.get("percentage")) or 0.0
            tk = {"basis": "MECHANISM (Clanker deployment config)", "total_supply": (_f(r.get("supply")) or 0) / 1e18 or None, "vault_pct": vpct, "airdrop_pct": apct,
                  "pool_pct": max(0.0, 100 - vpct - apct), "vault_terms": vault or None, "lp_control": "Clanker locker (protocol-held LP position)" if r.get("locker_address") else "UNKNOWN",
                  "sniper_tax": ext.get("sniperTax"), "fees": ext.get("fees"), "team_alloc_pct_mechanism": vpct}
            smc = _f(r.get("starting_market_cap"))
            c = _cand("base", r["contract_address"], project=r.get("name"), symbol=r.get("symbol"), launchpad="clanker", state="E", creator=(r.get("admin") or "").lower() or None,
                      created_at=_iso(r.get("deployed_at") or r.get("created_at")), contract_verified=1, contract_source="Clanker index (chain-derived)",
                      pool=r.get("pool_address"), sources=["clanker:new"], tokenomics=tk)
            c["obs"] = {"mcap_usd": _f((r.get("mkt") or {}).get("marketCap")), "vol_usd": _f((r.get("mkt") or {}).get("volume24h"))}
            if smc and eth_price:
                c["expected"] = {"start_mcap_usd": smc * eth_price, "basis": "Clanker starting market cap (ETH) x ETH price"}
            if r.get("warnings"):
                c["flags"].append("CLANKER_WARNINGS:" + ",".join(map(str, r["warnings"]))[:80])
            add(c)
    # ---- Zora ----
    for r in bodies.get("zora:new") or []:
        if not isinstance(r, dict) or not r.get("address"):
            continue
        c = _cand("base", r["address"], project=r.get("name"), symbol=r.get("symbol"), launchpad=f"zora:{(r.get('coinType') or '').lower()}", state="E",
                  creator=(r.get("creatorAddress") or "").lower() or None, created_at=_iso(r.get("createdAt")), contract_verified=1, contract_source="Zora index (chain-derived)", sources=["zora:new"])
        c["obs"] = {"mcap_usd": _f(r.get("marketCap")), "vol_usd": _f(r.get("volume24h")), "holders": r.get("uniqueHolders")}
        c["tokenomics"] = {"basis": "MECHANISM (Zora coin)", "total_supply": _f(r.get("totalSupply")), "team_alloc_pct_mechanism": None, "note": "creator allocation and vesting depend on coin type; not exposed by the API"}
        add(c)
    # ---- Virtuals Genesis (scheduled) ----
    for g in bodies.get("virt:genesis") or []:
        if not isinstance(g, dict):
            continue
        v = g.get("v") or {}
        start = _iso(g.get("startsAt"))
        status = (g.get("status") or "").upper()
        if status in ("FINALIZED",) or (start and start < t - 86400 and status != "STARTED"):
            continue
        addr = v.get("tokenAddress")
        lid = f"base:{addr.lower()}" if addr else f"ann:virtuals-genesis-{g.get('genesisId')}"
        c = _cand("base", addr, launch_id=lid, project=v.get("name"), symbol=v.get("symbol"), launchpad="virtuals-genesis", state="B" if addr else "A",
                  scheduled_at=start, contract_verified=1 if addr else 0, contract_source="Virtuals API" if addr else None, sources=["virt:genesis"])
        c["signals"] = {"genesis_status": status, "participants": g.get("totalParticipants")}
        if status == "CANCELLED":
            c["flags"].append("LAUNCH_CANCELLED")
        add(c)
    # ---- Jupiter recent (Solana, any launchpad) ----
    for r in bodies.get("jup:recent") or []:
        if not isinstance(r, dict) or not r.get("id"):
            continue
        grad = r.get("graduatedPool")
        pad = r.get("launchpad")
        fp = (r.get("firstPool") or {})
        state = "E" if (grad or not pad) else "C"
        c = _cand("solana", r["id"], project=r.get("name"), symbol=r.get("symbol"), launchpad=pad, state=state, creator=r.get("dev"), created_at=_iso(fp.get("createdAt") or r.get("createdAt")),
                  first_trade_at=_iso(r.get("graduatedAt")) if grad else (_iso(fp.get("createdAt")) if not pad else None), contract_verified=1, contract_source="Jupiter token index",
                  pool=grad or (fp.get("id") if not pad else None), sources=["jup:recent"])
        s24 = r.get("stats24h") or {}
        c["obs"] = {"mcap_usd": _f(r.get("mcap")), "fdv_usd": _f(r.get("fdv")), "liquidity_usd": _f(r.get("liquidity")), "holders": r.get("holderCount"),
                    "vol_usd": (_f(s24.get("buyVolume")) or 0) + (_f(s24.get("sellVolume")) or 0) or None, "organic_score": _f(r.get("organicScore"))}
        au = r.get("audit") or {}
        c["signals"] = {"mint_disabled": au.get("mintAuthorityDisabled"), "freeze_disabled": au.get("freezeAuthorityDisabled"), "top_holders_pct": _f(au.get("topHoldersPercentage")),
                        "dev_balance_pct": _f(au.get("devBalancePercentage")), "dev_migrations": au.get("devMigrations")}
        add(c)
    # ---- GeckoTerminal new pools (E, or C for curve dexes) ----
    for k, v in bodies.items():
        if not (k.startswith("gt_pools:") and ":new:" in k) or not isinstance(v, dict):
            continue
        net = k.split(":")[1]
        chain = {"solana": "solana", "base": "base", "bsc": "bsc"}.get(net, net)
        for p in v.get("pools") or []:
            base = p.get("base")
            if not base:
                continue
            curve = any(x in (p.get("dex") or "") for x in ("pump-fun", "launchlab", "meteora-dbc", "moonshot", "boop"))
            c = _cand(chain, base, project=(p.get("name") or "").split("/")[0].strip(), symbol=(p.get("name") or "").split("/")[0].strip(), launchpad=p.get("dex") if curve else None,
                      state="C" if curve else "E", created_at=_iso(p.get("created")), first_trade_at=None if curve else _iso(p.get("created")),
                      pool=None if curve else p.get("pool"), contract_verified=1, contract_source="GeckoTerminal pool index", sources=[f"gt:new:{chain}"])
            tx = (p.get("tx") or {}).get("h24") or [None, None, None, None]
            c["obs"] = {"mcap_usd": p.get("mcap") or p.get("fdv"), "fdv_usd": p.get("fdv"), "liquidity_usd": p.get("reserve"), "vol_usd": (p.get("vol") or {}).get("h24"),
                        "buyers": tx[2], "sellers": tx[3], "price_usd": p.get("price")}
            c["dex"] = p.get("dex")
            if curve:
                c["curve_pool"] = p.get("pool")
            add(c)
    # ---- RugCheck newest mints (B until a market is seen) ----
    for r in bodies.get("rug:new") or []:
        if isinstance(r, dict) and r.get("mint"):
            c = _cand("solana", r["mint"], symbol=r.get("symbol"), state="B", created_at=_iso(r.get("createAt")), contract_verified=1, contract_source="RugCheck mint index",
                      creator=r.get("creator") or None, sources=["rug:new"])
            c["signals"] = {"mint_authority": r.get("mintAuthority") or None, "freeze_authority": r.get("freezeAuthority") or None, "token_program": r.get("program")}
            add(c)
    # ---- DEX Screener profiles: paid listing signal only ----
    prof = {(p.get("tokenAddress") or "").lower(): p for p in bodies.get("ds_profiles:latest") or [] if isinstance(p, dict)}
    boost = {(p.get("tokenAddress") or "").lower(): p for p in bodies.get("ds_boosts:latest") or [] if isinstance(p, dict)}
    for c in out.values():
        key = (c["contract"] or "").lower()
        if key in prof:
            c["signals"]["ds_profile"] = True
            for l in prof[key].get("links") or []:
                c["links"].setdefault((l.get("type") or l.get("label") or "link").lower(), l.get("url"))
        if key in boost:
            c["signals"]["ds_boost"] = boost[key].get("totalAmount") or boost[key].get("amount") or True
    # within-sample serial-launcher count (cheap deployer signal before the creator query)
    by_creator: dict[str, int] = {}
    for c in out.values():
        if c.get("creator"):
            by_creator[c["creator"]] = by_creator.get(c["creator"], 0) + 1
    for c in out.values():
        if c.get("creator"):
            c["signals"]["creator_launches_in_sample"] = by_creator[c["creator"]]
    return out


def from_catalyst(con, t: float) -> list[dict]:
    """State A candidates from catalyst events that announce a token launch and have no verified token link."""
    rows = con.execute("SELECT e.* FROM catalyst_events e WHERE e.discovered_at > ? AND e.status NOT IN ('DENIED','EXPIRED') "
                       "AND NOT EXISTS (SELECT 1 FROM catalyst_token_links l WHERE l.event_id=e.id AND l.link_strength IN ('STRONG','MODERATE'))", (t - 7 * 86400,)).fetchall()
    out = []
    for e in rows:
        title = e["title"] or ""
        if not LAUNCH_RX.search(title):
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower())[:60].strip("-")
        tick = re.search(r"\$([A-Z]{2,10})\b", title)
        c = _cand(None, None, launch_id=f"ann:{slug}", project=title[:120], symbol=tick.group(1) if tick else None, state="A", scheduled_at=e["event_at"],
                  contract_verified=0, sources=[f"catalyst:{e['original_source_id']}"])
        c["signals"] = {"evidence_status": e["evidence_status"], "independent_sources": e["independent_sources"], "event_id": e["id"], "url": e["original_url"]}
        c["flags"].append("CONTRACT_NOT_YET_VERIFIED")
        out.append(c)
    return out


def impersonation_check(con, cands: dict[str, dict]) -> None:
    """Same ticker on several contracts: identity is chain + contract, never the symbol. Flag every collision."""
    by_sym: dict[str, set] = {}
    for c in cands.values():
        if c.get("symbol") and c.get("contract"):
            by_sym.setdefault(c["symbol"].upper(), set()).add(c["launch_id"])
    known = {}
    for r in con.execute("SELECT upper(symbol) s, COUNT(*) n FROM tokens WHERE symbol IS NOT NULL GROUP BY upper(symbol)"):
        known[r["s"]] = r["n"]
    for c in cands.values():
        s = (c.get("symbol") or "").upper()
        if not s:
            continue
        n = len(by_sym.get(s, ())) - (1 if c.get("contract") else 0) + known.get(s, 0)
        if n > 0:
            c["flags"].append(f"TICKER_COLLISION:{n}")
        if c["state"] == "A":
            c["flags"].append("IMPERSONATION_RISK: no published contract; any token using this name or ticker before an official contract is published is unverified")


def persist(con, cands: dict[str, dict], t: float) -> dict[str, list]:
    """Upsert candidates, append observations, feed the cohort, and emit transition alerts."""
    alerts: list[dict] = []
    for c in cands.values():
        prev = con.execute("SELECT * FROM upcoming_launches WHERE launch_id=?", (c["launch_id"],)).fetchone()
        tk = json.dumps(c.get("tokenomics") or {})
        exp = c.get("expected") or {}
        row = {"project": c.get("project"), "symbol": c.get("symbol"), "chain": c.get("chain"), "contract": c.get("contract"), "contract_verified": int(bool(c.get("contract_verified"))),
               "contract_source": c.get("contract_source"), "launchpad": c.get("launchpad"), "state": c["state"], "scheduled_at": c.get("scheduled_at"), "created_at": c.get("created_at"),
               "first_trade_at": c.get("first_trade_at"), "source": (c["sources"] or [None])[0], "sources_json": json.dumps(c["sources"]), "official_links_json": json.dumps({k: v for k, v in c["links"].items() if v}),
               "creator": c.get("creator"), "pool": c.get("pool"), "curve_pool": c.get("curve_pool") or c.get("bonding_curve"), "expected_valuation_usd": exp.get("grad_mcap_usd") or exp.get("start_mcap_usd"), "expected_liquidity_usd": exp.get("grad_liquidity_usd"),
               "valuation_basis": exp.get("basis"), "tokenomics_json": tk, "social_json": json.dumps(c.get("signals") or {}), "risk_flags_json": json.dumps(c.get("flags") or []), "updated_at": t}
        if prev is None:
            row.update({"launch_id": c["launch_id"], "discovered_at": t, "phase": "NEW_LAUNCH_MONITOR" if c["state"] == "E" else "PRE_LAUNCH"})
            db.insert(con, "upcoming_launches", row)
        else:
            p = dict(prev)
            if p["phase"] in ("REJECTED", "NORMAL_WATCHLIST"):
                row.pop("state")
            else:
                if "ABCDE".index(c["state"]) < "ABCDE".index(p["state"]):
                    row["state"] = p["state"]  # never regress a state on a partial view
                if p["state"] == "A" and row["state"] != "A" and c.get("contract"):
                    alerts.append({"launch_id": c["launch_id"], "kind": "CONTRACT_PUBLISHED", "text": f"{c.get('symbol')}: contract {c['contract']} established ({c.get('contract_source')})"})
                if p["state"] in ("A", "B", "C", "D") and row["state"] == "E":
                    alerts.append({"launch_id": c["launch_id"], "kind": "TRADING_LIVE", "text": f"{c.get('symbol')} ({c.get('chain')}) DEX trading observed"})
                    row["phase"] = "NEW_LAUNCH_MONITOR"
                if p["state"] in ("C", "D") and row["state"] == "E" and c.get("pool"):
                    alerts.append({"launch_id": c["launch_id"], "kind": "LIQUIDITY_CREATED", "text": f"{c.get('symbol')}: pool {c['pool']} created"})
                if not p["scheduled_at"] and c.get("scheduled_at"):
                    alerts.append({"launch_id": c["launch_id"], "kind": "LAUNCH_TIME_CONFIRMED", "text": f"{c.get('symbol')}: launch scheduled {datetime.fromtimestamp(c['scheduled_at'], tz=timezone.utc).isoformat()}"})
                elif p["scheduled_at"] and c.get("scheduled_at") and c["scheduled_at"] > p["scheduled_at"] + 3600:
                    alerts.append({"launch_id": c["launch_id"], "kind": "LAUNCH_DELAYED", "text": f"{c.get('symbol')}: launch moved later by {(c['scheduled_at'] - p['scheduled_at']) / 3600:.1f}h"})
                if "LAUNCH_CANCELLED" in (c.get("flags") or []) and "LAUNCH_CANCELLED" not in (p["risk_flags_json"] or ""):
                    alerts.append({"launch_id": c["launch_id"], "kind": "LAUNCH_CANCELLED", "text": f"{c.get('symbol')}: launch cancelled"})
                old_tk = json.loads(p["tokenomics_json"] or "{}")
                for key in ("curve_sale_pct", "locked_vesting_pct", "vault_pct", "airdrop_pct", "total_supply", "team_alloc_pct_mechanism"):
                    a, b = old_tk.get(key), (c.get("tokenomics") or {}).get(key)
                    if a is not None and b is not None and abs((a or 0) - (b or 0)) > max(0.5, 0.01 * abs(a or 1)):
                        alerts.append({"launch_id": c["launch_id"], "kind": "MAJOR_TOKENOMICS_CHANGE", "text": f"{c.get('symbol')}: {key} {a} -> {b}"}); break
                for keep in ("first_trade_at", "created_at", "scheduled_at", "creator", "contract", "pool", "curve_pool", "expected_valuation_usd", "expected_liquidity_usd", "valuation_basis"):
                    if row.get(keep) is None:
                        row[keep] = p[keep]
            con.execute(f"UPDATE upcoming_launches SET {','.join(k + '=?' for k in row)} WHERE launch_id=?", list(row.values()) + [c["launch_id"]])
        o = c.get("obs") or {}
        if any(v is not None for v in o.values()):
            db.insert(con, "launch_observations", {"launch_id": c["launch_id"], "observed_at": t, "source": ",".join(c["sources"])[:80], "state": c["state"], "price_usd": o.get("price_usd"),
                      "mcap_usd": o.get("mcap_usd"), "fdv_usd": o.get("fdv_usd"), "liquidity_usd": o.get("liquidity_usd"), "curve_progress_pct": o.get("curve_progress_pct"),
                      "raised_quote": o.get("raised_quote"), "quote_symbol": o.get("quote_symbol"), "holders": o.get("holders"), "buyers": o.get("buyers"), "sellers": o.get("sellers"),
                      "vol_usd": o.get("vol_usd"), "replies": o.get("replies"), "is_live": o.get("is_live"), "raw_json": json.dumps({k: v for k, v in o.items() if k in ("ath_usd", "organic_score", "last_trade_at")})})
        # cohort: every launchpad launch we see enters the comparable base once
        if c.get("contract") and c.get("launchpad") and c.get("created_at"):
            basis = "newest" if set(c["sources"]) & NEWEST_SOURCES else ("graduated" if "pump:grad" in c["sources"] else "selected")
            if not con.execute("SELECT 1 FROM launch_cohort WHERE mint=?", (c["contract"],)).fetchone():
                db.insert(con, "launch_cohort", {"mint": c["contract"], "chain": c["chain"], "platform": c["launchpad"], "symbol": c.get("symbol"), "creator": c.get("creator"),
                          "created_at": c["created_at"], "start_mcap_usd": o.get("mcap_usd") if (t - c["created_at"]) < 1800 else None, "first_seen_at": t, "last_checked": t,
                          "mcap_usd": o.get("mcap_usd"), "ath_usd": o.get("ath_usd"), "graduated": 1 if c["state"] == "E" else 0, "last_trade_at": o.get("last_trade_at"), "sample_basis": basis})
            else:
                update_cohort(con, c["contract"], o, c["state"] == "E", t)
    for a in alerts:
        db.insert(con, "launch_alerts", {"alerted_at": t, **a})
    return {"alerts": alerts}


def update_cohort(con, mint: str, o: dict, graduated: bool, t: float) -> None:
    r = con.execute("SELECT * FROM launch_cohort WHERE mint=?", (mint,)).fetchone()
    if not r:
        return
    age = t - (r["created_at"] or t)
    upd = {"last_checked": t, "mcap_usd": o.get("mcap_usd") if o.get("mcap_usd") is not None else r["mcap_usd"],
           "ath_usd": max([x for x in (r["ath_usd"], o.get("ath_usd"), o.get("mcap_usd")) if x is not None], default=None),
           "graduated": 1 if (graduated or r["graduated"]) else 0, "last_trade_at": o.get("last_trade_at") or r["last_trade_at"]}
    for col, lo, hi in (("mcap_24h", 20 * 3600, 48 * 3600), ("mcap_7d", 6 * 86400, 10 * 86400), ("mcap_30d", 27 * 86400, 40 * 86400)):
        if r[col] is None and lo <= age <= hi and o.get("mcap_usd") is not None:
            upd[col] = o["mcap_usd"]
    con.execute(f"UPDATE launch_cohort SET {','.join(k + '=?' for k in upd)} WHERE mint=?", list(upd.values()) + [mint])
