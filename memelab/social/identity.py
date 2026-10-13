"""Token identity resolution for social posts (Phase 05).

A post can point at a token three ways: a contract address, a link that carries an address (DEX Screener, pump.fun,
an explorer ...), or a ticker. Only the first two can identify a token. This module maps each reference to
(chain, contract) with one of four outcomes and keeps every candidate it considered:

  resolved     exactly one supported (chain, contract) is backed by a chain-valid address and at least one provider
               record (or the chain registry), and nothing in the same post contradicts it
  ambiguous    more than one viable identity, or a ticker with candidates but nothing that pins one of them
  unresolved   no viable identity: malformed address, bad EIP-55 checksum, unknown or unsupported chain, no record
  conflicted   strong evidence disagrees: a link's chain vs where providers find the address, or a ticker in the
               post vs the symbol every provider reports for the contract in the same post

A ticker on its own never resolves, however few candidates a search returns (a search sees only what it indexes).
It resolves only when a contract in the same post resolves to a token with that symbol, or when it names a
registry asset (wrapped native, stablecoin) on a chain the caller states.

Inputs are collector bodies in the shape the bridge already produces (ds:*, ds_search:*, jup_tok:*, gt_info:*,
gt_pools:*, goplus:<chain>:*), so the same fetch plans and projections are reused. Post text, when given, is read
in memory to find addresses, links and cashtags and is never stored or returned.

Supported chains: Solana, Ethereum, Base and BNB Chain (registry ids solana, ethereum, base, bsc). Other registry
chains are recorded as candidates with support='unsupported' and never resolve.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from typing import Any, Iterable
from urllib.parse import urlparse, parse_qs

from ..chains import registry
from . import store
from ._keccak import eip55

RESOLVER_VERSION = "resolve-v1"
SUPPORTED = ("solana", "ethereum", "base", "bsc")
SUPPORTED_EVM = ("ethereum", "base", "bsc")
STATUSES = ("resolved", "ambiguous", "unresolved", "conflicted")

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
EVM_RX = re.compile(r"(?<![0-9A-Za-z])0x[0-9a-fA-F]{38,42}(?![0-9A-Za-z])")
SOL_RX = re.compile(r"(?<![1-9A-HJ-NP-Za-km-z])[1-9A-HJ-NP-Za-km-z]{32,44}(?![1-9A-HJ-NP-Za-km-z])")
CASHTAG_RX = re.compile(r"(?<![A-Za-z0-9_$])\$([A-Za-z][A-Za-z0-9]{0,9})(?![A-Za-z0-9])")
URL_RX = re.compile(r"https?://[^\s<>\"')\]]+")

# explorer and app hosts whose path carries a token or pair address; chain is fixed by the host where it can be
EXPLORER_HOSTS = {"etherscan.io": "ethereum", "basescan.org": "base", "bscscan.com": "bsc", "solscan.io": "solana",
                  "solana.fm": "solana", "explorer.solana.com": "solana"}
DEXTOOLS_CHAINS = {"ether": "ethereum", "base": "base", "bnb": "bsc", "solana": "solana"}

# a wrapped-native or stablecoin ticker names infrastructure, not a memecoin; the registry is the trusted source
REGISTRY_TICKERS = {"WETH": "WRAPPED_NATIVE", "WBNB": "WRAPPED_NATIVE", "WSOL": "WRAPPED_NATIVE", "SOL": "WRAPPED_NATIVE",
                    "USDC": "STABLECOIN", "USDT": "STABLECOIN", "USDBC": "STABLECOIN"}


# ---------- address checks ----------

def b58decode(s: str) -> bytes | None:
    n = 0
    for ch in s:
        i = _B58.find(ch)
        if i < 0:
            return None
        n = n * 58 + i
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    return b"\x00" * (len(s) - len(s.lstrip("1"))) + raw


def address_shape(addr: str) -> tuple[str, str | None]:
    """('evm'|'solana'|'invalid', problem). The shape says which family an address can belong to, never which chain."""
    a = (addr or "").strip()
    if a[:2].lower() == "0x":
        body = a[2:]
        if not re.fullmatch(r"[0-9a-fA-F]+", body or "x"):
            return "invalid", "not_hex"
        if len(body) != 40:
            return "invalid", "address_wrong_length"
        if body != body.lower() and body != body.upper() and eip55(a) != "0x" + body:
            return "invalid", "checksum_mismatch"
        return "evm", None
    if 32 <= len(a) <= 44 and all(c in _B58 for c in a):
        raw = b58decode(a)
        if raw is None or len(raw) != 32:
            return "invalid", "base58_not_32_bytes"
        return "solana", None
    return "invalid", "not_an_address"


def canon(chain: str | None, addr: str) -> str:
    return registry.norm_address(chain, addr) if chain else (addr.lower() if addr[:2].lower() == "0x" else addr)


def _family_ok(chain: str, shape: str) -> bool:
    fam = registry.family(chain)
    return (fam == "solana" and shape == "solana") or (fam == "evm" and shape == "evm")


# ---------- extraction (text is read in memory only) ----------

def _link_mention(url: str) -> dict | None:
    try:
        u = urlparse(url)
    except ValueError:
        return None
    host = (u.hostname or "").lower().removeprefix("www.")
    parts = [p for p in u.path.split("/") if p]
    chain, addr, path_kind, chain_raw = None, None, "unknown", None
    if host == "dexscreener.com" and len(parts) >= 2:
        chain_raw, addr, path_kind = parts[0], parts[1], "pair_or_token"
        chain = registry.by_ds_chain(chain_raw)
    elif host == "geckoterminal.com" and len(parts) >= 3 and parts[1] in ("pools", "tokens"):
        chain_raw, addr, path_kind = parts[0], parts[2], "pair" if parts[1] == "pools" else "token"
        chain = registry.by_gt_network(chain_raw)
    elif host == "pump.fun" and parts:
        chain_raw, chain, path_kind = "solana", "solana", "token"
        addr = parts[1] if parts[0] == "coin" and len(parts) > 1 else parts[0]
    elif host == "birdeye.so" and len(parts) >= 2 and parts[0] == "token":
        chain_raw = (parse_qs(u.query).get("chain") or ["solana"])[0]
        chain = {"solana": "solana", "ethereum": "ethereum", "base": "base", "bsc": "bsc"}.get(chain_raw)
        addr, path_kind = parts[1], "token"
    elif host == "jup.ag" and parts:
        chain_raw, chain, path_kind = "solana", "solana", "token"
        last = parts[-1]
        addr = last.split("-")[-1] if "-" in last else last
    elif host in EXPLORER_HOSTS and len(parts) >= 2 and parts[0] in ("token", "address"):
        chain_raw, chain, addr, path_kind = host, EXPLORER_HOSTS[host], parts[1], "token"
    elif host == "dextools.io" and len(parts) >= 4 and "pair-explorer" in parts:
        i = parts.index("pair-explorer")
        chain_raw, addr, path_kind = parts[i - 1], parts[i + 1] if i + 1 < len(parts) else None, "pair"
        chain = DEXTOOLS_CHAINS.get(chain_raw)
    if not addr:
        return None
    return {"kind": "LINK", "value": f"https://{host}/{'/'.join(parts)}"[:300], "address": addr.split("?")[0],
            "link_host": host, "path_kind": path_kind, "link_chain": chain, "link_chain_raw": chain_raw}


def extract_mentions(text: str | None = None, urls: Iterable[str] = (), cashtags: Iterable[str] = ()) -> list[dict]:
    """Addresses, address-bearing links and cashtags. Returns no text; only the matched tokens."""
    out: list[dict] = []
    seen: set[str] = set()
    all_urls = list(urls) + (URL_RX.findall(text) if text else [])
    link_addrs: set[str] = set()
    for url in all_urls:
        m = _link_mention(url)
        if m and ("link:" + m["value"]) not in seen:
            seen.add("link:" + m["value"]); out.append(m); link_addrs.add(m["address"])
    body = URL_RX.sub(" ", text) if text else ""
    for rx in (EVM_RX, SOL_RX):
        scan = EVM_RX.sub(" ", body) if rx is SOL_RX else body   # a base58 run inside a 0x address is not a mint
        for a in rx.findall(scan):
            if a in link_addrs or ("ca:" + a.lower() if a[:2] == "0x" else "ca:" + a) in seen:
                continue
            if rx is SOL_RX and (a.isdigit() or a.isalpha()):   # plain words and numbers are not base58 keys
                continue
            seen.add("ca:" + a.lower() if a[:2] == "0x" else "ca:" + a)
            out.append({"kind": "CONTRACT", "value": a, "address": a})
    tags = [t for t in cashtags] + (CASHTAG_RX.findall(body) if body else [])
    for t in tags:
        sym = t.strip().lstrip("$").upper()
        if sym and "ticker:" + sym not in seen:
            seen.add("ticker:" + sym); out.append({"kind": "TICKER", "value": sym})
    return out


# ---------- provider records from collector bodies ----------

def _unwrap(v: Any) -> Any:
    return v["body"] if isinstance(v, dict) and "body" in v and "s" in v else v


def provider_records(bodies: dict[str, Any]) -> list[dict]:
    """One record per (provider, chain, token address[, pair]) found in the bodies. Keys say where each came from."""
    recs: list[dict] = []

    def add(**r):
        r.setdefault("pair", None); r.setdefault("liquidity_usd", None); r.setdefault("name", None)
        recs.append(r)

    for key, raw in bodies.items():
        v = _unwrap(raw)
        if key.startswith("ds"):
            pairs = v.get("pairs") if isinstance(v, dict) else v
            if key.startswith("ds_profiles") or not isinstance(pairs, list):
                continue
            for p in pairs:
                if not isinstance(p, dict):
                    continue
                bt = p.get("baseToken") or {}
                if not bt.get("address"):
                    continue
                cid = p.get("chainId")
                ch = registry.by_ds_chain(cid) if cid else None
                add(provider="dexscreener", source_key=key, chain=ch, provider_chain=cid, token=canon(ch, bt["address"]),
                    symbol=bt.get("symbol"), name=bt.get("name"), pair=canon(ch, p["pairAddress"]) if p.get("pairAddress") else None,
                    liquidity_usd=_num((p.get("liquidity") or {}).get("usd")))
        elif key.startswith("jup_tok") and isinstance(v, list):
            for t in v:
                if isinstance(t, dict) and t.get("id") and not t.get("_dup"):
                    add(provider="jupiter", source_key=key, chain="solana", provider_chain="solana", token=t["id"],
                        symbol=t.get("symbol"), name=t.get("name"), liquidity_usd=_num(t.get("liquidity")))
        elif key.startswith("gt_pools") and isinstance(v, dict):
            for p in v.get("pools") or []:
                net = p.get("net")
                ch = registry.by_gt_network(net) if net else None
                if p.get("base"):
                    add(provider="geckoterminal", source_key=key, chain=ch, provider_chain=net, token=canon(ch, p["base"]),
                        symbol=None, pair=canon(ch, p["pool"]) if p.get("pool") else None, liquidity_usd=_num(p.get("reserve")))
        elif key.startswith("goplus:") and isinstance(v, dict):
            parts = key.split(":")
            ch = parts[1] if len(parts) > 2 and parts[1] in registry.CHAINS else None
            for addr, rec in v.items():
                if isinstance(rec, dict) and addr[:2].lower() == "0x":
                    add(provider="goplus", source_key=key, chain=ch, provider_chain=parts[1] if len(parts) > 2 else None,
                        token=canon(ch, addr), symbol=rec.get("token_symbol"), name=rec.get("token_name"))
        elif key.startswith("gt_info") and isinstance(v, dict) and v.get("address"):
            # gt_info bodies carry no network; usable only to corroborate a chain another provider established
            add(provider="geckoterminal", source_key=key, chain=None, provider_chain=None, token=canon(None, v["address"]),
                symbol=v.get("symbol"), name=v.get("name"), chainless=True)
    return recs


def _num(x) -> float | None:
    try:
        f = float(x)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def _same(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    return a.lower() == b.lower() if a[:2].lower() == "0x" else a == b


# ---------- resolution ----------

def _registry_assets(chains: Iterable[str]) -> list[dict]:
    out = []
    for ch in chains:
        cfg = registry.CHAINS[ch]
        wn = cfg["wrapped_native"]
        sym = {"ethereum": "WETH", "base": "WETH", "bsc": "WBNB", "solana": "WSOL"}.get(ch, "W" + cfg["native_symbol"])
        out.append({"chain": ch, "token": canon(ch, wn), "symbol": sym, "asset_class": "WRAPPED_NATIVE"})
        for a, s in (cfg.get("stables") or {}).items():
            out.append({"chain": ch, "token": canon(ch, a), "symbol": s, "asset_class": "STABLECOIN"})
    return out


def _group(recs: list[dict]) -> dict[tuple, dict]:
    """Merge provider records into candidate identities keyed by (chain or provider chain, token)."""
    g: dict[tuple, dict] = {}
    for r in recs:
        k = (r["chain"] or f"?{r.get('provider_chain')}", r["token"])
        c = g.setdefault(k, {"chain": r["chain"], "provider_chain": r.get("provider_chain"), "contract": r["token"],
                             "symbols": {}, "names": {}, "providers": set(), "liquidity_usd": None, "keys": set(), "pairs": set()})
        c["providers"].add(r["provider"]); c["keys"].add(r["source_key"])
        if r.get("symbol"):
            c["symbols"][r["provider"]] = r["symbol"]
        if r.get("name"):
            c["names"][r["provider"]] = r["name"]
        if r.get("pair"):
            c["pairs"].add(r["pair"])
        if r.get("liquidity_usd") is not None:
            c["liquidity_usd"] = max(c["liquidity_usd"] or 0, r["liquidity_usd"])
    return g


def _cand(c: dict, verdict: str, why: str) -> dict:
    sym = next(iter(c["symbols"].values()), None) if c.get("symbols") else c.get("symbol")
    name = next(iter(c["names"].values()), None) if c.get("names") else c.get("name")
    return {"chain": c.get("chain"), "provider_chain": c.get("provider_chain") or c.get("chain"), "contract": c["contract"],
            "symbol_seen": sym, "name_seen": name, "support": "supported" if c.get("chain") in SUPPORTED else "unsupported",
            "verdict": verdict, "why": why, "providers": sorted(c.get("providers") or []),
            "liquidity_usd_seen": c.get("liquidity_usd"), "symbols_by_provider": dict(c.get("symbols") or {}),
            "source_keys": sorted(c.get("keys") or []), "asset_class": c.get("asset_class")}


def _relations(con: sqlite3.Connection | None, chain: str, contract: str) -> list[dict]:
    if con is None:
        return []
    rows = con.execute("SELECT * FROM social_token_relations WHERE (from_chain=? AND from_contract=?) OR (to_chain=? AND to_contract=?)",
                       (chain, contract, chain, contract)).fetchall()
    return [dict(r) for r in rows]


def _lev(a: str, b: str, cap: int = 3) -> int:
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > cap:
            return cap + 1
        prev = cur
    return prev[-1]


def near_matches(con: sqlite3.Connection | None, addr: str, recs: list[dict], max_dist: int = 2) -> list[dict]:
    """Known addresses within edit distance 2 of a malformed or unknown one: a possible typo, never a correction."""
    known: dict[tuple, str] = {}
    for r in recs:
        if r.get("chain"):
            known[(r["chain"], r["token"])] = "provider_body"
    if con is not None:
        for row in con.execute("SELECT chain, contract FROM social_token_refs WHERE contract IS NOT NULL"):
            known.setdefault((row[0], row[1]), "lab_token_refs")
        try:
            for row in con.execute("SELECT chain, mint FROM tokens"):
                known.setdefault((row[0], row[1]), "lab_tokens")
        except sqlite3.OperationalError:
            pass
    a = addr.lower() if addr[:2].lower() == "0x" else addr
    out = []
    for (ch, tok), where in known.items():
        t = tok.lower() if tok[:2].lower() == "0x" else tok
        if t != a and abs(len(t) - len(a)) <= max_dist and _lev(a, t, max_dist) <= max_dist:
            out.append({"chain": ch, "contract": tok, "providers": [where], "symbols": {}, "names": {}})
    return out


def _result(mention: dict, status: str, reasons: list[str], candidates: list[dict], chosen: dict | None = None,
            chain_hint: str | None = None, hint_basis: str | None = None) -> dict:
    ev = []
    for c in candidates:
        for k in c.get("source_keys") or []:
            ev.append({"kind": "provider_record", "provider": None, "source_key": k, "chain": c["chain"], "contract": c["contract"],
                       "bucket": "FACT"})
    if mention.get("link_host"):
        ev.append({"kind": "link", "provider": mention["link_host"], "source_key": None, "chain": mention.get("link_chain"),
                   "contract": mention.get("address"), "bucket": "FACT"})
    return {"mention_kind": mention["kind"], "mention_value": mention["value"], "mention_key": _mention_key(mention),
            "chain_hint": chain_hint, "chain_hint_basis": hint_basis, "status": status, "reasons": reasons,
            "resolved": {"chain": chosen["chain"], "contract": chosen["contract"], "asset_class": chosen.get("asset_class") or "TOKEN",
                         "symbol_seen": chosen.get("symbol_seen")} if chosen and status == "resolved" else None,
            "candidates": candidates, "evidence": ev}


def _mention_key(m: dict) -> str:
    if m["kind"] == "TICKER":
        return f"ticker:{m['value']}"
    if m["kind"] == "LINK":
        return f"link:{m['value']}"
    return f"ca:{m['value'].lower() if m['value'][:2].lower() == '0x' else m['value']}"


def resolve_address(mention: dict, recs: list[dict], chain_hint: str | None = None, con: sqlite3.Connection | None = None) -> dict:
    addr = mention["address"].strip()
    hint, basis = (mention.get("link_chain"), "LINK") if mention.get("kind") == "LINK" else (chain_hint, "CALLER" if chain_hint else None)
    if mention.get("kind") == "LINK" and not hint and chain_hint:
        hint, basis = chain_hint, "CALLER"
    shape, problem = address_shape(addr)
    if shape == "invalid":
        near = [_cand(n, "near_match", "edit_distance_le_2") for n in near_matches(con, addr, recs)]
        if problem == "checksum_mismatch":
            near = [_cand(g, "near_match", "same_hex_bad_checksum") for g in _group([r for r in recs if _same(r["token"], addr.lower())
                                                                                    and not r.get("chainless")]).values()] + near
        reasons = [problem] + (["possible_typo_of_known_address"] if near else [])
        return _result(mention, "unresolved", reasons, near, chain_hint=hint, hint_basis=basis)
    if mention.get("kind") == "LINK" and mention.get("link_chain_raw") and not mention.get("link_chain"):
        return _result(mention, "unresolved", ["invalid_chain"], [], chain_hint=None, hint_basis=None)
    if hint is not None:
        if hint not in registry.CHAINS:
            return _result(mention, "unresolved", ["invalid_chain"], [], chain_hint=hint, hint_basis=basis)
        if not _family_ok(hint, shape):
            return _result(mention, "unresolved", ["address_not_valid_for_chain"], [], chain_hint=hint, hint_basis=basis)
    a = canon(hint, addr) if hint else canon("ethereum" if shape == "evm" else "solana", addr)

    # a link to a pair or pool: map the pair to its base token through provider records
    reasons: list[str] = []
    pair_hits = [r for r in recs if r.get("pair") and _same(r["pair"], a) and r.get("chain") and (hint is None or r["chain"] == hint)]
    if pair_hits and not any(_same(r["token"], a) for r in recs):
        bases = {(r["chain"], r["token"]) for r in pair_hits}
        if len(bases) == 1:
            reasons.append("pair_mapped_to_base_token")
            a = next(iter(bases))[1]
        else:
            cands = [_cand(c, "viable", "base_token_of_linked_pair") for c in _group(pair_hits).values()]
            return _result(mention, "ambiguous", ["pair_maps_to_several_tokens"], cands, chain_hint=hint, hint_basis=basis)

    hits = [r for r in recs if _same(r["token"], a) and not r.get("chainless")]
    chainless = [r for r in recs if _same(r["token"], a) and r.get("chainless")]
    reg = [x for x in _registry_assets(SUPPORTED) if _same(x["token"], a)]
    groups = _group(hits)
    for x in reg:
        k = (x["chain"], x["token"])
        g = groups.setdefault(k, {"chain": x["chain"], "provider_chain": x["chain"], "contract": x["token"], "symbols": {}, "names": {},
                                  "providers": set(), "liquidity_usd": None, "keys": set(), "pairs": set()})
        g["providers"].add("registry"); g["symbols"].setdefault("registry", x["symbol"]); g["asset_class"] = x["asset_class"]
    if shape == "solana":
        allowed = {"solana"}
    else:
        allowed = set(SUPPORTED_EVM) | {c for c in registry.CHAINS if registry.is_evm(c)}
    in_family = {k: g for k, g in groups.items() if g["chain"] in allowed or g["chain"] is None}
    if hint:
        on_hint = {k: g for k, g in in_family.items() if g["chain"] == hint}
        elsewhere = {k: g for k, g in in_family.items() if g["chain"] != hint and g["chain"] in SUPPORTED}
        if not on_hint and elsewhere:
            cands = [_cand(g, "viable", "found_on_other_chain") for g in elsewhere.values()]
            return _result(mention, "conflicted", reasons + ["chain_hint_disagrees_with_providers"], cands, chain_hint=hint, hint_basis=basis)
        in_family = on_hint
    supported = {k: g for k, g in in_family.items() if g["chain"] in SUPPORTED}
    unsupported = {k: g for k, g in in_family.items() if g["chain"] not in SUPPORTED}
    rej = [_cand(g, "rejected", "unsupported_chain") for g in unsupported.values()]
    if hint and hint not in SUPPORTED:
        return _result(mention, "unresolved", reasons + ["unsupported_chain"], rej, chain_hint=hint, hint_basis=basis)
    if not supported:
        near = [] if rej else [_cand(n, "near_match", "edit_distance_le_2") for n in near_matches(con, a, recs)]
        why = "unsupported_chain" if rej else ("not_found_possible_typo" if near else "no_provider_record")
        if chainless and not rej:
            why = "only_chainless_record"
        return _result(mention, "unresolved", reasons + [why], rej + near, chain_hint=hint, hint_basis=basis)
    if len(supported) > 1:
        cands = [_cand(g, "viable", "same_address_on_several_chains") for g in supported.values()] + rej
        return _result(mention, "ambiguous", reasons + ["same_address_on_several_chains"], cands, chain_hint=hint, hint_basis=basis)
    g = next(iter(supported.values()))
    for r in chainless:
        g["providers"].add(r["provider"]); g["keys"].add(r["source_key"])
        if r.get("symbol"):
            g["symbols"].setdefault(r["provider"] + "_info", r["symbol"])
    chosen = _cand(g, "chosen", "contract_found_on_chain")
    cands = [chosen] + rej
    syms = {s.upper() for s in g["symbols"].values() if s}
    if len(syms) > 1:
        reasons.append("providers_disagree_on_symbol")
    # spoof risk: other contracts on the same chain reporting the same symbol
    if syms:
        others = [c for c in _group([r for r in recs if r.get("chain") == g["chain"] and not _same(r["token"], g["contract"])
                                     and (r.get("symbol") or "").upper() in syms]).values()]
        if others:
            reasons.append("symbol_shared_with_other_contracts")
            mine = g.get("liquidity_usd") or 0
            if any((o.get("liquidity_usd") or 0) > mine for o in others):
                reasons.append("a_more_liquid_contract_uses_this_symbol")
            cands += [_cand(o, "rejected", "same_symbol_different_contract") for o in others]
    for rel in _relations(con, g["chain"], g["contract"]):
        if rel["relation"] == "MIGRATED_TO" and rel["from_contract"] == g["contract"]:
            reasons.append("migrated_successor_known")
            cands.append(_cand({"chain": rel["to_chain"], "contract": rel["to_contract"], "providers": {rel["basis"].lower()}},
                               "successor", "relation_" + rel["basis"].lower()))
        elif rel["relation"] == "MIGRATED_TO" and rel["to_contract"] == g["contract"]:
            reasons.append("is_successor_of_migrated_contract")
            cands.append(_cand({"chain": rel["from_chain"], "contract": rel["from_contract"], "providers": {rel["basis"].lower()}},
                               "predecessor", "relation_" + rel["basis"].lower()))
    if g.get("asset_class"):
        reasons.append("registry_asset_" + g["asset_class"].lower())
    return _result(mention, "resolved", reasons or ["contract_found_on_chain"], cands, chosen=chosen, chain_hint=hint, hint_basis=basis)


def resolve_ticker(mention: dict, recs: list[dict], chain_hint: str | None = None, con: sqlite3.Connection | None = None) -> dict:
    sym = mention["value"].upper()
    hint = chain_hint
    if hint is not None and hint not in registry.CHAINS:
        return _result(mention, "unresolved", ["invalid_chain"], [], chain_hint=hint, hint_basis="CALLER")
    if sym in REGISTRY_TICKERS:
        reg = [x for x in _registry_assets(SUPPORTED) if x["symbol"].upper() == sym and (hint is None or x["chain"] == hint)]
        cands = [_cand({**x, "contract": x["token"], "providers": {"registry"}, "symbols": {"registry": x["symbol"]}}, "viable", "registry_asset")
                 for x in reg]
        if hint and len(reg) == 1:
            cands[0]["verdict"] = "chosen"
            return _result(mention, "resolved", ["registry_asset_on_stated_chain", "registry_asset_" + reg[0]["asset_class"].lower()],
                           cands, chosen=cands[0], chain_hint=hint, hint_basis="CALLER")
        if reg:
            return _result(mention, "ambiguous", ["registry_asset_chain_not_stated"], cands, chain_hint=hint, hint_basis="CALLER" if hint else None)
    matches = [r for r in recs if (r.get("symbol") or "").upper() == sym and not r.get("chainless")]
    groups = _group(matches)
    cands: list[dict] = []
    for g in groups.values():
        if hint and g["chain"] != hint:
            cands.append(_cand(g, "rejected", "other_chain_than_stated"))
        elif g["chain"] not in SUPPORTED:
            cands.append(_cand(g, "rejected", "unsupported_chain"))
        else:
            cands.append(_cand(g, "viable", "symbol_match_only"))
    # a migrated contract and its successor share the ticker; both stay candidates
    for c in list(cands):
        if c["verdict"] == "viable" and c["chain"]:
            for rel in _relations(con, c["chain"], c["contract"]):
                other = (rel["to_chain"], rel["to_contract"]) if rel["from_contract"] == c["contract"] else (rel["from_chain"], rel["from_contract"])
                if not any(x["contract"] == other[1] for x in cands):
                    cands.append(_cand({"chain": other[0], "contract": other[1], "providers": {rel["basis"].lower()}}, "viable", "migration_relation"))
    cands.sort(key=lambda c: (c["verdict"] != "viable", -(c["liquidity_usd_seen"] or 0)))
    viable = [c for c in cands if c["verdict"] == "viable"]
    if not viable:
        why = "no_candidates" if not cands else "only_rejected_candidates"
        return _result(mention, "unresolved", ["symbol_only", why], cands, chain_hint=hint, hint_basis="CALLER" if hint else None)
    reasons = ["symbol_only"] + (["multiple_candidates"] if len(viable) > 1 else ["single_search_candidate_not_proof"])
    if len({c["chain"] for c in viable}) > 1:
        reasons.append("candidates_on_several_chains")
    return _result(mention, "ambiguous", reasons, cands, chain_hint=hint, hint_basis="CALLER" if hint else None)


def resolve_post(bodies: dict[str, Any], *, text: str | None = None, urls: Iterable[str] = (), cashtags: Iterable[str] = (),
                 chain_hint: str | None = None, con: sqlite3.Connection | None = None) -> dict:
    """Resolve every reference in one post. Returns {status, mentions:[...]}; nothing is stored here."""
    mentions = extract_mentions(text, urls, cashtags)
    recs = provider_records(bodies)
    results = []
    for m in mentions:
        results.append(resolve_ticker(m, recs, chain_hint, con) if m["kind"] == "TICKER" else resolve_address(m, recs, chain_hint, con))
    # same-post corroboration: a ticker resolves only through a contract the post itself carries
    addr_res = [r for r in results if r["mention_kind"] != "TICKER" and r["status"] == "resolved"]
    for r in results:
        if r["mention_kind"] != "TICKER" or not addr_res or r["status"] == "resolved":
            continue
        sym = r["mention_value"]
        match = [a for a in addr_res if sym in {s.upper() for s in a["candidates"][0]["symbols_by_provider"].values() if s}]
        if match:
            a = match[0]
            chosen = dict(a["candidates"][0])
            flags = [x for x in a["reasons"] if x in ("symbol_shared_with_other_contracts", "a_more_liquid_contract_uses_this_symbol")]
            r.update(status="resolved", reasons=["corroborated_by_contract_in_same_post"] + flags,
                     resolved=dict(a["resolved"]), candidates=[chosen] + [dict(c, verdict="rejected" if c["verdict"] == "viable" else c["verdict"])
                                                                          for c in r["candidates"] if c["contract"] != chosen["contract"]])
            r["evidence"] = r["evidence"] + [{"kind": "same_post_contract", "provider": None, "source_key": None,
                                              "chain": chosen["chain"], "contract": chosen["contract"], "bucket": "FACT"}]
        else:
            r.update(status="conflicted", reasons=["ticker_disagrees_with_contract_in_same_post"] + r["reasons"])
            for a in addr_res:
                a.update(status="conflicted", reasons=a["reasons"] + ["post_ticker_disagrees_with_contract_symbol"], resolved=None)
                a["candidates"][0]["verdict"] = "viable"
    statuses = {r["status"] for r in results}
    post = ("conflicted" if "conflicted" in statuses else "resolved" if statuses == {"resolved"} else
            "ambiguous" if "ambiguous" in statuses else "unresolved" if results else "unresolved")
    return {"status": post, "mentions": results, "n_provider_records": len(recs)}


# ---------- persistence ----------

def _sha(*parts: Any) -> str:
    return hashlib.sha256("|".join("" if p is None else str(p) for p in parts).encode()).hexdigest()


def ensure_version(con: sqlite3.Connection, now: float | None = None) -> None:
    store.register_analysis_version(con, RESOLVER_VERSION, "resolver",
                                    "Phase 05 token identity resolver: contract and link evidence, ticker only by same-post corroboration or registry",
                                    {"supported": list(SUPPORTED)}, now=now)


def persist(con: sqlite3.Connection, post: dict, item_key: str | None = None, now: float | None = None) -> list[int]:
    """Store each mention's resolution, its candidates and token refs. Idempotent: the same evidence adds nothing."""
    t = time.time() if now is None else float(now)
    ensure_version(con, t)
    ids = []
    for r in post["mentions"]:
        ev_sha = hashlib.sha256(json.dumps([r["evidence"], r["candidates"], r["reasons"], r["status"]], sort_keys=True, default=str).encode()).hexdigest()
        key = _sha(item_key, r["mention_key"], r["chain_hint"], RESOLVER_VERSION, ev_sha)
        row = con.execute("SELECT resolution_id FROM social_token_resolutions WHERE resolution_key=?", (key,)).fetchone()
        if row:
            ids.append(row[0]); continue
        ref_id = None
        res = r.get("resolved")
        if res:
            ref_id = store.upsert_token_ref(con, res["chain"], res["contract"], symbol=res.get("symbol_seen"), now=t)
        elif r["mention_kind"] == "TICKER":
            store.upsert_token_ref(con, symbol=r["mention_value"], now=t)
        cur = con.execute(
            "INSERT INTO social_token_resolutions(resolution_key,item_key,mention_key,mention_kind,mention_value,chain_hint,chain_hint_basis,"
            "status,reasons_json,resolved_ref_id,resolved_chain,resolved_contract,asset_class,evidence_json,evidence_sha,resolver_version,resolved_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (key, item_key, r["mention_key"], r["mention_kind"], r["mention_value"][:300], r["chain_hint"], r["chain_hint_basis"], r["status"],
             json.dumps(r["reasons"]), ref_id, res["chain"] if res else None, res["contract"] if res else None,
             res.get("asset_class") if res else None, json.dumps(r["evidence"], sort_keys=True), ev_sha, RESOLVER_VERSION, t))
        rid = cur.lastrowid
        for i, c in enumerate(r["candidates"]):
            cref = None
            if c["chain"] in registry.CHAINS and c["support"] == "supported":
                try:
                    cref = store.upsert_token_ref(con, c["chain"], c["contract"], symbol=c.get("symbol_seen"), now=t)
                except ValueError:
                    cref = None
            con.execute("INSERT INTO social_token_candidates(resolution_id,rank,chain,provider_chain,contract,symbol_seen,name_seen,support,verdict,why,"
                        "providers_json,liquidity_usd_seen,ref_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (rid, i, c["chain"], c.get("provider_chain"), c["contract"], c.get("symbol_seen"), (c.get("name_seen") or "")[:80] or None,
                         c["support"], c["verdict"], c["why"], json.dumps(c["providers"]), c.get("liquidity_usd_seen"), cref))
        ids.append(rid)
    return ids


def record_relation(con: sqlite3.Connection, from_chain: str, from_contract: str, relation: str, to_chain: str, to_contract: str,
                    basis: str, source_url: str | None = None, effective_at: Any = None, now: float | None = None) -> None:
    """A trusted link between identities. OFFICIAL_SOURCE needs the URL that states it."""
    if basis == "OFFICIAL_SOURCE" and not (source_url or "").startswith("https://"):
        raise ValueError("an OFFICIAL_SOURCE relation needs the https URL that states it")
    f = store.normalize_contract(from_chain, from_contract)
    to = store.normalize_contract(to_chain, to_contract)
    con.execute("INSERT OR IGNORE INTO social_token_relations(from_chain,from_contract,relation,to_chain,to_contract,basis,source_url,effective_at,recorded_at)"
                " VALUES (?,?,?,?,?,?,?,?,?)", (from_chain, f, relation, to_chain, to, basis, source_url, store.to_utc(effective_at),
                                                 time.time() if now is None else float(now)))


# ---------- downstream API ----------

def token_identity(con: sqlite3.Connection, item_key: str | None = None, resolution_id: int | None = None) -> list[dict]:
    """What downstream asks for: per mention, status, exact identity (or none), candidates, evidence and market context."""
    if resolution_id is not None:
        rows = con.execute("SELECT * FROM social_token_resolutions WHERE resolution_id=?", (resolution_id,)).fetchall()
    else:
        rows = con.execute("SELECT * FROM social_token_resolutions WHERE item_key IS ? ORDER BY resolution_id", (item_key,)).fetchall()
    out = []
    for r in rows:
        cands = [dict(c) for c in con.execute("SELECT * FROM social_token_candidates WHERE resolution_id=? ORDER BY rank", (r["resolution_id"],))]
        for c in cands:
            c["providers"] = json.loads(c.pop("providers_json"))
        ctx = [dict(x) for x in con.execute("SELECT * FROM social_market_context WHERE resolution_id=? ORDER BY fetched_at", (r["resolution_id"],))]
        for x in ctx:
            x["notes"] = json.loads(x.pop("notes_json"))
            for k in ("posting_price_fact_id", "observed_price_fact_id"):
                if x.get(k):
                    x[k.replace("_fact_id", "")] = dict(con.execute("SELECT * FROM social_market_facts WHERE fact_id=?", (x[k],)).fetchone())
        out.append({"resolution_id": r["resolution_id"], "item_key": r["item_key"], "mention": {"kind": r["mention_kind"], "value": r["mention_value"]},
                    "status": r["status"], "reasons": json.loads(r["reasons_json"]),
                    "identity": {"chain": r["resolved_chain"], "contract": r["resolved_contract"], "ref_id": r["resolved_ref_id"],
                                 "asset_class": r["asset_class"]} if r["status"] == "resolved" else None,
                    "candidates": cands, "evidence": json.loads(r["evidence_json"]), "resolver_version": r["resolver_version"],
                    "resolved_at": r["resolved_at"], "market_context": ctx})
    return out


# ---------- fetch plans (reuse the existing builders) ----------

def resolution_plan(post_mentions: list[dict], chain_hint: str | None = None, plan_id: str | None = None):
    """Collector plan that gathers the bodies resolve_post() reads: DEX Screener token lookups per candidate chain,
    Jupiter search for Solana, GoPlus for EVM, DEX Screener and Jupiter searches for tickers."""
    from ..bridge.plan import Plan, JUP, DS
    from ..chains import plan as cplan
    p = Plan(plan_id or f"resolve_{int(time.time())}")
    for m in post_mentions:
        if m["kind"] == "TICKER":
            p.add(f"ds_search:{m['value']}", f"{DS}/latest/dex/search?q={m['value']}", proj="ds", delay_ms=250)
            if chain_hint in (None, "solana"):
                p.add(f"jup_tok:{m['value']}", f"{JUP}/tokens/v2/search?query={m['value']}", proj="jup_tok", delay_ms=250)
            continue
        addr = m["address"]
        shape, _ = address_shape(addr)
        hint = m.get("link_chain") or chain_hint
        if shape == "solana" and hint in (None, "solana"):
            p.add(f"ds:solana:one:{addr}", f"{DS}/tokens/v1/solana/{addr}", proj="ds")
            p.add(f"jup_tok:{addr}", f"{JUP}/tokens/v2/search?query={addr}", proj="jup_tok")
            if m.get("path_kind") in ("pair", "pair_or_token"):
                p.add(f"ds:solana:pair:{addr}", f"{DS}/latest/dex/pairs/solana/{addr}", proj="ds")
        elif shape == "evm":
            for ch in ([hint] if hint in SUPPORTED_EVM else SUPPORTED_EVM if hint is None else []):
                sub = cplan.evm_structural(ch, [addr])
                p.reqs += [r for r in sub.reqs if not r["key"].startswith("hp:")]
                if m.get("path_kind") in ("pair", "pair_or_token"):
                    p.add(f"ds:{ch}:pair:{addr.lower()}", f"{DS}/latest/dex/pairs/{registry.CHAINS[ch]['ds_chain']}/{addr}", proj="ds")
    return p
