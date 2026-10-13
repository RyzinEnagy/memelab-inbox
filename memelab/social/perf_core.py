"""Phase 10: wallet-level performance accounting. Pure functions: a ledger goes in, a result comes out. No database, no network, no clock.

What this is: a transparent reconstruction of what ONE wallet (or one declared group of wallets) did with the tokens it traded, built only from
observed transactions: swaps, transfers, liquidity moves, fees, plus prices and sell quotes the caller supplies. Every number says which inputs it
used, and every gap says what it takes away.

What this is not: a measure of a person. A wallet is a key, not a human. Other wallets the same person may use, flows through exchanges and
trades made before the visible history are outside the data. The result always says so (`person_level_claim` is false), and a provider
leaderboard figure is never an input (see compare_provider_estimates, which only compares).

Rules that decide the numbers (each has a test; the long version is in docs/social-intelligence/PERFORMANCE_10.md):
- Arithmetic is exact (decimal, 50 digits). Amounts are the wallet's actual legs, so a fee-on-transfer token is costed on what arrived.
- A token bought by swap gets a lot whose cost is the net quote asset paid (native coin or stablecoin) valued in dollars at the swap time.
  Stablecoins are valued at an observed price when one exists and at 1.00 only as a labelled assumption (PEG_ASSUMED).
- A token that arrives by transfer is NOT a purchase. It becomes a lot with unknown basis (or zero basis only when an analyst marks it an airdrop,
  and then it is kept out of trading performance). Selling it produces proceeds with no gain or loss figure.
- A sale that exceeds the inventory the ledger can explain creates an opening lot of unknown basis (missing earlier history) at the front of the queue.
- Tokens sent away are not sold. They leave the books holding their basis and come back at that basis only if the same counterparty returns them.
  Between wallets of a declared group, a transfer is matched by transaction signature and moves no profit.
- Liquidity deposits and withdrawals are capital moves, not trades. Liquidity P&L (fees, impermanent loss) is not computed.
- Realized P&L, unrealized mark-to-market, estimated liquidation proceeds and transaction costs are separate lines. A mark is not proceeds.
- A trade for statistics is one closed position: first swap-buy to flat, every disposal a sale at known proceeds with known basis. Open, partial,
  off-book, contaminated and unknown-basis positions are listed and excluded, never silently counted.
"""
from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from typing import Any

VERSION = "wallet-performance-v1"
SCHEMA_LEDGER = "memelab.perf.ledger/1"
SCHEMA_RESULT = "memelab.perf.result/1"
PREC = 50
ZERO = Decimal(0)
ONE = Decimal(1)
STATEMENT = ("Wallet-level reconstruction from observed transactions. It says nothing about the person behind a wallet: other wallets, exchange flows, "
             "earlier history and off-chain activity are outside the data.")

# thresholds are declared here, copied into every result, and part of the input hash
try:    # keep one definition of "enough sample" for the lab
    from ..modules.m28_statistical_analysis import N_INSUFFICIENT as _N_FLOOR, N_LOW_CONF as _N_LOW
except Exception:   # pragma: no cover - numpy missing in a minimal environment
    _N_FLOOR, _N_LOW = 20, 50

DEFAULT_POLICY: dict[str, Any] = {
    "convention": "FIFO",              # FIFO or AVCO (average cost); the other is always computed as a sensitivity
    "price_tolerance_s": 900,          # a price observation counts for a trade if it is this close in time
    "mtm_max_age_s": 86400,            # a mark older than this is stale and not used in headline unrealized P&L
    "quote_max_age_s": 3600,           # a sell quote older than this is stale and not used in headline liquidation value
    "assume_stable_peg": True,         # value a stablecoin at 1.00 when no price was observed (labelled PEG_ASSUMED)
    "force_stable_par": False,         # sensitivity switch: ignore observed stablecoin prices
    "return_matching": True,           # a transfer back from the counterparty it was sent to restores the original basis
    "dust_ratio": "0.0001",            # a remainder below this share of the position's bought quantity is written off at closing
    "large_shortfall_ratio": 100,      # a sale this many times the known inventory is flagged as a possible unit error
    "price_mismatch_factor": 50,       # swap-implied price this many times off a nearby observed price flags a possible unit error
    "min_closed_positions": _N_FLOOR,  # fewer closed, fully known positions than this: no score (same floor as m28)
    "low_confidence_below": _N_LOW,    # fewer than this: score carries LOW_CONFIDENCE
    "min_span_days": 7,
    "min_basis_coverage": "0.8",       # share of disposed value that came from lots with a known basis
    "min_price_coverage": "0.9",       # share of entries needing a price that got one
    "max_unknown_fee_share": "0.2",
    "max_unclassified_share": "0.1",
    "min_equity_points": 20,           # drawdown needs at least this many fully valued points ...
    "min_equity_completeness": "0.8",  # ... covering at least this share of the trading entries
    "material_sensitivity_share": "0.05",  # a sensitivity matters when it moves realized P&L by more than this share of the realized figure
}

QUOTE_KINDS = ("NATIVE", "STABLE")
ENTRY_TYPES = ("SWAP", "TRANSFER_IN", "TRANSFER_OUT", "LP_ADD", "LP_REMOVE", "FAILED", "UNCLASSIFIED")
PRICE_KINDS = ("MID", "EXEC_QUOTE", "NO_ROUTE", "IMPACT_CURVE")
SALE_KINDS = ("SALE", "TOKEN_SWAP", "DUST_WRITE_OFF", "TRANSFER_TAX")    # slices that realize a result
OFFBOOK_KINDS = ("TRANSFER_OUT", "LP_DEPLOY")                              # slices that leave the books without proceeds


# ---------- numbers ----------

def dec(x: Any, what: str = "value") -> Decimal:
    if x is None or isinstance(x, bool):
        raise ValueError(f"{what}: not a number")
    try:
        if isinstance(x, Decimal):
            d = x
        elif isinstance(x, int):
            d = Decimal(x)
        elif isinstance(x, float):
            d = Decimal(repr(x))
        elif isinstance(x, str):
            d = Decimal(x.strip())
        else:
            raise ValueError
    except (InvalidOperation, ValueError):
        raise ValueError(f"{what}: not a number") from None
    if not d.is_finite():
        raise ValueError(f"{what}: not a finite number")
    return d


def _q(d: Decimal | None, places: int = 12) -> str | None:
    """Canonical string, rounded half-even to `places`; used for every number that leaves the engine."""
    if d is None:
        return None
    r = d.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN)
    s = format(r, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def canonical_json(o: Any) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def sha(o: Any) -> str:
    return hashlib.sha256(canonical_json(o).encode()).hexdigest()


def _median(xs: list[Decimal]) -> Decimal | None:
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def wilson(wins: int, n: int, z: str = "1.959964") -> tuple[Decimal, Decimal] | None:
    """95% Wilson score interval for a proportion. Deterministic, exact decimal."""
    if n <= 0:
        return None
    zz, p, nn = Decimal(z), Decimal(wins) / n, Decimal(n)
    den = 1 + zz * zz / nn
    centre = (p + zz * zz / (2 * nn)) / den
    half = zz * ((p * (1 - p) / nn + zz * zz / (4 * nn * nn)).sqrt()) / den
    return max(ZERO, centre - half), min(ONE, centre + half)


# ---------- parsing the ledger ----------

def merge_policy(over: dict | None) -> dict:
    pol = dict(DEFAULT_POLICY)
    for k, v in (over or {}).items():
        if k not in DEFAULT_POLICY:
            raise ValueError(f"unknown policy key {k!r}")
        pol[k] = v
    if pol["convention"] not in ("FIFO", "AVCO"):
        raise ValueError("convention must be FIFO or AVCO")
    return pol


def _num_policy(pol: dict, k: str) -> Decimal:
    return dec(pol[k], k)


class Ledger:
    """A parsed, validated ledger. `rejects` are entries the engine refuses to account for, each with a reason; they are counted, never dropped."""

    def __init__(self):
        self.chain = None
        self.as_of = 0.0
        self.assets: dict[str, dict] = {}
        self.alias: dict[str, str] = {}
        self.entries: list[dict] = []
        self.rejects: list[dict] = []
        self.prices: list[dict] = []
        self.coverage_in: dict = {}
        self.group: dict | None = None
        self.annotations: dict[str, dict] = {}
        self.label = None
        self.wallets: list[str] = []

    def canon(self, a: str) -> str:
        return self.alias.get(a, a)

    def kind(self, a: str) -> str:
        return self.assets.get(self.canon(a), {}).get("kind", "NATIVE" if self.canon(a) == "NATIVE" else "TOKEN")


def parse_ledger(doc: dict) -> Ledger:
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA_LEDGER:
        raise ValueError(f"ledger schema must be {SCHEMA_LEDGER}")
    L = Ledger()
    L.label = doc.get("label")
    L.chain = str(doc.get("chain") or "").lower()
    if not L.chain:
        raise ValueError("chain is required")
    L.as_of = float(dec(doc.get("as_of"), "as_of"))
    ws = doc.get("wallets") or []
    if not ws or not all(isinstance(w, str) and w for w in ws):
        raise ValueError("wallets: list at least one wallet address")
    L.wallets = list(ws)
    if len(set(ws)) > 1:
        g = doc.get("linked_wallets") or {}
        if sorted(g.get("declared") or []) != sorted(set(ws)) or not str(g.get("reason") or "").strip():
            raise ValueError("more than one wallet needs linked_wallets.declared (all of them) and a reason; "
                             "the group is the analyst's choice and is never an ownership claim")
        L.group = {"declared": sorted(set(ws)), "reason": str(g["reason"])[:300]}
    for aid, m in (doc.get("assets") or {}).items():
        m = m or {}
        kind = m.get("kind") or ("NATIVE" if aid == "NATIVE" else "TOKEN")
        if kind not in ("NATIVE", "STABLE", "TOKEN", "LP_RECEIPT"):
            raise ValueError(f"asset {aid}: kind must be NATIVE, STABLE, TOKEN or LP_RECEIPT")
        dcm = m.get("decimals")
        if dcm is not None and (not isinstance(dcm, int) or isinstance(dcm, bool) or not 0 <= dcm <= 36):
            raise ValueError(f"asset {aid}: decimals must be an integer from 0 to 36")
        meta = {"kind": kind, "symbol": m.get("symbol"), "decimals": dcm, "transfer_fee_bps": m.get("transfer_fee_bps"), "alias_of": m.get("alias_of")}
        L.assets[aid] = meta
        if m.get("alias_of"):
            L.alias[aid] = m["alias_of"]
    L.assets.setdefault("NATIVE", {"kind": "NATIVE", "symbol": None, "decimals": None, "transfer_fee_bps": None, "alias_of": None})
    for a in doc.get("annotations") or []:
        if a.get("origin") not in ("AIRDROP",) or not a.get("signature") or not str(a.get("reason") or "").strip():
            raise ValueError("annotation needs origin AIRDROP, a signature and a reason")
        L.annotations[a["signature"]] = {"origin": a["origin"], "reason": str(a["reason"])[:300]}
    seen_ids: set[str] = set()
    seen_sig: set[tuple] = set()
    for i, e in enumerate(doc.get("entries") or []):
        eid = str(e.get("id", f"#{i}"))
        base = {"id": eid, "wallet": e.get("wallet"), "time": None, "seq": i}

        def reject(reason: str, detail: str = ""):
            L.rejects.append({"id": eid, "reason": reason, "detail": detail, "time": base["time"], "assets": sorted({str(x.get("asset")) for x in (e.get("legs") or []) if isinstance(x, dict)})})
        try:
            base["time"] = float(dec(e.get("time"), "time"))
        except ValueError:
            reject("BAD_TIME")
            continue
        if eid in seen_ids:
            reject("DUPLICATE_ID")
            continue
        seen_ids.add(eid)
        if e.get("wallet") not in L.wallets:
            reject("WALLET_NOT_IN_SCOPE", str(e.get("wallet")))
            continue
        typ = e.get("type")
        if typ not in ENTRY_TYPES:
            reject("BAD_TYPE", str(typ))
            continue
        sig = e.get("signature")
        if sig:
            if (e["wallet"], sig) in seen_sig:
                reject("DUPLICATE_SIGNATURE", "the same transaction appears twice for this wallet")
                continue
            seen_sig.add((e["wallet"], sig))
        if base["time"] > L.as_of:
            reject("AFTER_AS_OF", "entry is later than the as-of time")
            continue
        legs, bad = [], None
        for lg in e.get("legs") or []:
            try:
                legs.append(_parse_leg(L, lg))
            except ValueError as ex:
                bad = str(ex)
                break
        if bad:
            code, _, det = bad.partition(":")
            reject(code, det.strip())
            continue
        fee = e.get("fee")
        feep = None
        if isinstance(fee, dict):
            try:
                feep = {"amount": dec(fee.get("amount"), "fee"), "unit": fee.get("unit")}
                if feep["amount"] < 0:
                    raise ValueError
            except ValueError:
                reject("BAD_FEE")
                continue
        origin = e.get("origin") or (L.annotations.get(sig) or {}).get("origin")
        if origin and (origin != "AIRDROP" or typ != "TRANSFER_IN"):
            reject("BAD_ORIGIN", "only a TRANSFER_IN can be marked AIRDROP")
            continue
        L.entries.append({"id": eid, "wallet": e["wallet"], "time": base["time"], "seq": i, "type": typ, "legs": legs, "fee": feep, "fee_paid_by_wallet": e.get("fee_paid_by_wallet"),
                          "signature": sig, "origin": origin, "provider_side": e.get("side"), "pool": e.get("pool"), "confidence": e.get("confidence")})
    L.entries.sort(key=lambda x: (x["time"], x["seq"]))
    for j, p in enumerate(doc.get("prices") or []):
        L.prices.append(_parse_price(L, p, j))
    L.coverage_in = doc.get("coverage") or {}
    return L


def _parse_leg(L: Ledger, lg: dict) -> dict:
    if not isinstance(lg, dict) or lg.get("dir") not in ("IN", "OUT") or not lg.get("asset"):
        raise ValueError("BAD_LEG")
    asset = str(lg["asset"])
    meta = L.assets.get(L.canon(asset)) or L.assets.get(asset) or {}
    amt = None
    if lg.get("raw") is not None:
        d = lg.get("decimals")
        if not isinstance(d, int) or isinstance(d, bool) or not 0 <= d <= 36:
            raise ValueError("BAD_LEG: raw amount needs integer decimals")
        if meta.get("decimals") is not None and meta["decimals"] != d:
            raise ValueError(f"DECIMALS_CONFLICT: leg says {d}, asset says {meta['decimals']}")
        try:
            raw = dec(lg["raw"], "raw")
        except ValueError:
            raise ValueError("BAD_LEG: raw is not a number") from None
        amt = raw.scaleb(-d)
        if lg.get("amount") is not None and dec(lg["amount"], "amount") != amt:
            raise ValueError("AMOUNT_RAW_MISMATCH: amount differs from raw / 10^decimals")
    else:
        try:
            amt = dec(lg.get("amount"), "amount")
        except ValueError:
            raise ValueError("BAD_LEG: amount is not a number") from None
    if amt <= 0:
        raise ValueError("NONPOSITIVE_AMOUNT")
    return {"asset": L.canon(asset), "raw_asset": asset, "dir": lg["dir"], "amount": amt, "counterparty": lg.get("counterparty")}


def _parse_price(L: Ledger, p: dict, j: int) -> dict:
    kind = p.get("kind", "MID")
    if kind not in PRICE_KINDS or not p.get("asset") or not p.get("source"):
        raise ValueError(f"price {j}: needs asset, source and kind in {PRICE_KINDS}")
    out = {"asset": L.canon(str(p["asset"])), "t": float(dec(p.get("t"), "price time")), "kind": kind, "source": str(p["source"])[:80], "idx": j, "detail": p.get("detail")}
    if kind == "MID":
        out["usd"] = dec(p.get("usd"), "usd")
        if out["usd"] <= 0:
            raise ValueError(f"price {j}: usd must be positive")
    elif kind == "EXEC_QUOTE":
        out["amount_in"], out["usd_out"] = dec(p.get("amount_in"), "amount_in"), dec(p.get("usd_out"), "usd_out")
        if out["amount_in"] <= 0 or out["usd_out"] < 0:
            raise ValueError(f"price {j}: amount_in must be positive and usd_out not negative")
    elif kind == "IMPACT_CURVE" and not isinstance(p.get("sell"), dict):
        raise ValueError(f"price {j}: IMPACT_CURVE needs a sell quotes dict")
    elif kind == "IMPACT_CURVE":
        out["sell"] = p["sell"]
    return out


# ---------- prices and valuation ----------

class Book:
    def __init__(self, L: Ledger, pol: dict):
        self.L, self.pol = L, pol
        self.mid: dict[str, list[dict]] = {}
        self.exe: dict[str, list[dict]] = {}
        for p in sorted(L.prices, key=lambda x: (x["t"], x["idx"])):
            (self.mid if p["kind"] == "MID" else self.exe).setdefault(p["asset"], []).append(p)

    def near(self, asset: str, t: float) -> dict | None:
        tol, best = float(self.pol["price_tolerance_s"]), None
        for p in self.mid.get(asset, []):
            d = abs(p["t"] - t)
            if d <= tol and (best is None or d < abs(best["t"] - t)):
                best = p
        return best

    def latest_mid(self, asset: str, t: float) -> dict | None:
        c = [p for p in self.mid.get(asset, []) if p["t"] <= t]
        return c[-1] if c else None

    def latest_exec(self, asset: str, t: float) -> dict | None:
        c = [p for p in self.exe.get(asset, []) if p["t"] <= t]
        return c[-1] if c else None

    def unit_usd(self, asset: str, t: float) -> tuple[Decimal | None, str | None]:
        """Dollars per unit of a quote or traded asset at time t, with the basis of the figure."""
        kind = self.L.kind(asset)
        if kind == "STABLE":
            if self.pol["force_stable_par"]:
                return ONE, "PEG_FORCED"
            p = self.near(asset, t)
            if p:
                return p["usd"], "OBSERVED"
            return (ONE, "PEG_ASSUMED") if self.pol["assume_stable_peg"] else (None, None)
        p = self.near(asset, t)
        return (p["usd"], "OBSERVED") if p else (None, None)

    def value_net(self, net: dict[str, Decimal], t: float) -> tuple[Decimal | None, list[str], Decimal | None]:
        """Dollar value and native-unit value of a net quote flow (asset -> signed amount). Either is None when it cannot be known."""
        usd, bases, native, native_ok = ZERO, [], ZERO, True
        for a, q in net.items():
            if q == 0:
                continue
            if self.L.kind(a) == "NATIVE":
                native += q
            else:
                native_ok = False
            u, b = self.unit_usd(a, t)
            if u is None:
                usd = None
            elif usd is not None:
                usd += q * u
                bases.append(b)
        return usd, sorted(set(bases)), (native if native_ok else None)


# ---------- the engine ----------

class Lot:
    __slots__ = ("id", "asset", "wallet", "acquired_at", "origin", "basis_status", "bucket", "qty0", "qty", "cost", "cost_native", "position", "entry", "restored", "seq", "cost0")

    def __init__(self, **k):
        for s in self.__slots__:
            setattr(self, s, k.get(s))


class Run:
    def __init__(self, L: Ledger, pol: dict, book: Book, convention: str):
        self.L, self.pol, self.book, self.conv = L, pol, book, convention
        self.lots: list[Lot] = []
        self.slices: list[dict] = []
        self.positions: list[dict] = []
        self.pool_out: list[dict] = []       # off-book holdings: transferred out, or deployed to liquidity
        self.restored_basis = ZERO
        self.entry_log: list[dict] = []      # one row per input entry: how it was handled
        self.fees: list[dict] = []
        self.quote_flows: dict[str, dict] = {}
        self.contam: dict[str, list[dict]] = {}
        self.flags: list[dict] = []
        self.snapshots: list[dict] = []
        self.synthetic_lots: list[Lot] = []
        self.counts: dict[str, int] = {}
        self.round_trips: list[dict] = []
        self.side_disagreements = 0
        self._lot_seq = 0
        self.realized_usd_cum = ZERO
        self.fees_usd_cum = ZERO
        self.fee_usd_by_entry: dict[str, Decimal | None] = {}
        self.internal_pairs = 0

    # --- helpers
    def n(self, k: str, by: int = 1):
        self.counts[k] = self.counts.get(k, 0) + by

    def flag(self, code: str, entry: str, detail: str = "", asset: str | None = None):
        self.flags.append({"code": code, "entry": entry, "asset": asset, "detail": detail})

    def contaminate(self, asset: str, t: float, entry: str, reason: str):
        self.contam.setdefault(asset, []).append({"time": t, "entry": entry, "reason": reason})

    def new_lot(self, **k) -> Lot:
        self._lot_seq += 1
        lot = Lot(id=self._lot_seq, seq=self._lot_seq, **k)
        lot.qty0 = lot.qty = k["qty"]
        lot.cost0 = lot.cost
        self.lots.append(lot)
        return lot

    def open_lots(self, asset: str) -> list[Lot]:
        ls = [l for l in self.lots if l.asset == asset and l.qty > 0]
        ls.sort(key=lambda l: (float("-inf") if l.acquired_at is None else l.acquired_at, l.seq))
        return ls

    def trading_remaining(self, asset: str, pos: int | None = None) -> Decimal:
        return sum((l.qty for l in self.lots if l.asset == asset and l.bucket == "TRADING" and l.qty > 0 and (pos is None or l.position == pos)), ZERO)

    def open_position_for(self, asset: str) -> int | None:
        for p in reversed([p for p in self.positions if p["asset"] == asset]):
            if self.trading_remaining(asset, p["id"]) > 0:
                return p["id"]
        return None

    def start_or_join_position(self, asset: str, t: float, entry: str) -> int:
        pid = self.open_position_for(asset)
        if pid is None:
            pid = len(self.positions) + 1
            self.positions.append({"id": pid, "asset": asset, "opened_at": t, "entries": [], "fee_entries": []})
        self.positions[pid - 1]["entries"].append(entry)
        return pid

    # --- consuming lots
    def _select(self, asset: str, qty: Decimal) -> list[tuple[Lot, Decimal]]:
        ls = self.open_lots(asset)
        if self.conv == "FIFO":
            out, rem = [], qty
            for l in ls:
                if rem <= 0:
                    break
                take = min(l.qty, rem)
                out.append((l, take))
                rem -= take
            return out
        total = sum((l.qty for l in ls), ZERO)    # AVCO: every open lot gives up the same share, which is the weighted average cost
        out, rem = [], qty
        for i, l in enumerate(ls):
            take = rem if i == len(ls) - 1 else min(l.qty, l.qty * qty / total)
            take = min(take, l.qty)
            out.append((l, take))
            rem -= take
        return out

    def ensure_inventory(self, asset: str, qty: Decimal, t: float, entry: str):
        """If the ledger cannot explain `qty` units, add an opening lot of unknown basis for the shortfall at the front of the queue."""
        have = sum((l.qty for l in self.lots if l.asset == asset and l.qty > 0), ZERO)
        if have >= qty:
            return
        short = qty - have
        ratio = dec(self.pol["large_shortfall_ratio"])
        if have > 0 and short >= ratio * have:
            self.flag("UNIT_ERROR_SUSPECTED", entry, f"sale of {_q(qty)} against known inventory {_q(have)}: decimals error or missing history", asset)
            self.contaminate(asset, t, entry, "UNIT_ERROR_SUSPECTED")
        lot = self.new_lot(asset=asset, wallet=None, acquired_at=None, origin="PRIOR_HISTORY", basis_status="UNKNOWN_PRIOR_HISTORY", bucket="UNKNOWN", qty=short,
                           cost=None, cost_native=None, position=None, entry=entry, restored=False)
        self.synthetic_lots.append(lot)
        self.contaminate(asset, t, entry, "MISSING_HISTORY")     # a position alive when history is missing is not a clean trade
        self.n("shortfall_lots")
        self.flag("SHORTFALL_OPENING_LOT", entry, f"{_q(short)} units were disposed that earlier history would have to explain", asset)

    def consume(self, asset: str, qty: Decimal, kind: str, entry: dict, proceeds: Decimal | None, proceeds_native: Decimal | None, *, pool: dict | None = None,
                proceeds_known: bool = True) -> list[dict]:
        """Take `qty` from the open lots and record one slice per lot touched. Proceeds are apportioned by quantity, the last slice taking the remainder."""
        t = entry["time"]
        self.ensure_inventory(asset, qty, t, entry["id"])
        sel = self._select(asset, qty)
        out, p_rem, pn_rem, q_rem = [], proceeds, proceeds_native, qty
        for i, (lot, take) in enumerate(sel):
            last = i == len(sel) - 1
            basis = basis_n = None
            if lot.cost is not None:
                basis = lot.cost if take == lot.qty else lot.cost * take / lot.qty
                lot.cost -= basis
            if lot.cost_native is not None:
                basis_n = lot.cost_native if take == lot.qty else lot.cost_native * take / lot.qty
                lot.cost_native -= basis_n
            lot.qty -= take
            pr = prn = None
            if proceeds_known:
                if p_rem is not None:
                    pr = p_rem if last else p_rem * take / q_rem
                    p_rem -= pr
                if pn_rem is not None:
                    prn = pn_rem if last else pn_rem * take / q_rem
                    pn_rem -= prn
                q_rem -= take
            sl = {"entry": entry["id"], "time": t, "asset": asset, "lot": lot.id, "qty": take, "kind": kind, "basis": basis, "basis_native": basis_n, "proceeds": pr, "proceeds_native": prn,
                  "proceeds_known": proceeds_known, "bucket": lot.bucket, "position": lot.position, "basis_status": lot.basis_status, "origin": lot.origin, "acquired_at": lot.acquired_at, "wallet": entry["wallet"]}
            self.slices.append(sl)
            out.append(sl)
            if pool is not None:
                self.pool_out.append({"asset": asset, "kind": kind, "key": pool["key"], "qty": take, "qty_rem": take, "basis": basis, "basis_native": basis_n, "origin": lot.origin,
                                      "basis_status": lot.basis_status, "bucket": lot.bucket, "acquired_at": lot.acquired_at, "position": lot.position, "from_entry": entry["id"], "time": t,
                                      "lot_wallet": lot.wallet})
            if kind in SALE_KINDS and lot.bucket == "TRADING" and basis is not None and sl["proceeds_known"] and (pr is not None or kind in ("DUST_WRITE_OFF", "TRANSFER_TAX")):
                self.realized_usd_cum += (pr or ZERO) - basis
        return out

    def dust_close(self, asset: str, entry: dict):
        for p in self.positions:
            if p["asset"] != asset:
                continue
            rem = self.trading_remaining(asset, p["id"])
            if rem <= 0:
                continue
            peak = sum((l.qty0 for l in self.lots if l.position == p["id"] and not l.restored and l.bucket == "TRADING"), ZERO)
            if rem <= dec(self.pol["dust_ratio"]) * peak:
                for l in [x for x in self.lots if x.asset == asset and x.position == p["id"] and x.bucket == "TRADING" and x.qty > 0]:
                    self._write_off(l, entry)
                self.n("dust_write_offs")

    def _write_off(self, lot: Lot, entry: dict):
        take = lot.qty
        basis, basis_n = lot.cost, lot.cost_native
        lot.cost = None if lot.cost is None else ZERO
        lot.cost_native = None if lot.cost_native is None else ZERO
        lot.qty = ZERO
        self.slices.append({"entry": entry["id"], "time": entry["time"], "asset": lot.asset, "lot": lot.id, "qty": take, "kind": "DUST_WRITE_OFF", "basis": basis, "basis_native": basis_n,
                            "proceeds": ZERO, "proceeds_native": ZERO, "proceeds_known": True, "bucket": lot.bucket, "position": lot.position, "basis_status": lot.basis_status,
                            "origin": lot.origin, "acquired_at": lot.acquired_at, "wallet": entry["wallet"]})
        if basis is not None:
            self.realized_usd_cum += -basis

    # --- fees
    def fee(self, e: dict, position: int | None):
        f = e["fee"]
        paid = e.get("fee_paid_by_wallet")
        if paid is False or paid == 0:
            self.entry_log[-1]["fee"] = "NOT_PAID_BY_WALLET"
            return
        if f is None:
            self.n("fee_unknown")
            self.fee_usd_by_entry[e["id"]] = None
            self.fees.append({"entry": e["id"], "native": None, "usd": None, "position": position, "status": "UNKNOWN_AMOUNT", "time": e["time"]})
            return
        unit = (f.get("unit") or "").upper()
        if unit not in ("NATIVE", "SOL", "ETH", "BNB", "AVAX", "MATIC", "POL"):
            self.n("fee_unknown")
            self.fees.append({"entry": e["id"], "native": f["amount"], "usd": None, "position": position, "status": "UNKNOWN_UNIT", "time": e["time"]})
            return
        u, b = self.book.unit_usd("NATIVE", e["time"])
        usd = f["amount"] * u if u is not None else None
        st = "OK" if usd is not None else "UNPRICED"
        if paid is None:
            st += "+PAYER_UNKNOWN"
            self.n("fee_payer_unknown")
        if usd is None:
            self.n("fee_unpriced")
        else:
            self.fees_usd_cum += usd
        self.fee_usd_by_entry[e["id"]] = usd
        self.fees.append({"entry": e["id"], "native": f["amount"], "usd": usd, "position": position, "status": st, "time": e["time"]})

    # --- quote flows
    def quote_flow(self, asset: str, direction: str, qty: Decimal, e: dict):
        q = self.quote_flows.setdefault(asset, {"in": ZERO, "out": ZERO})
        q["in" if direction == "IN" else "out"] += qty

    # --- entry handlers
    def process(self, e: dict):
        h = {"SWAP": self.swap, "TRANSFER_IN": self.transfer_in, "TRANSFER_OUT": self.transfer_out, "LP_ADD": self.lp_add, "LP_REMOVE": self.lp_remove}
        t = e["type"]
        self.entry_log.append({"id": e["id"], "type": t, "handled": None, "fee": None})
        self.n("entries")
        if t == "FAILED":
            self.entry_log[-1]["handled"] = "FEE_ONLY"
            self.n("failed")
            self.fee(e, None)
        elif t == "UNCLASSIFIED":
            self.entry_log[-1]["handled"] = "EXCLUDED_UNCLASSIFIED"
            self.n("unclassified")
            for g in e["legs"]:
                if self.L.kind(g["asset"]) not in QUOTE_KINDS:
                    self.contaminate(g["asset"], e["time"], e["id"], "UNCLASSIFIED_MOVEMENT")
            self.fee(e, None)
        else:
            pos = h[t](e)
            self.fee(e, pos)
        self.snapshot(e)

    def _split(self, e: dict):
        agg: dict[tuple, Decimal] = {}
        for g in e["legs"]:
            agg[(g["asset"], g["dir"])] = agg.get((g["asset"], g["dir"]), ZERO) + g["amount"]
        qin = {a: q for (a, d), q in agg.items() if d == "IN" and self.L.kind(a) in QUOTE_KINDS}
        qout = {a: q for (a, d), q in agg.items() if d == "OUT" and self.L.kind(a) in QUOTE_KINDS}
        tin = {a: q for (a, d), q in agg.items() if d == "IN" and self.L.kind(a) == "TOKEN"}
        tout = {a: q for (a, d), q in agg.items() if d == "OUT" and self.L.kind(a) == "TOKEN"}
        rec = [a for (a, d) in agg if self.L.kind(a) == "LP_RECEIPT"]
        return qin, qout, tin, tout, rec

    def swap(self, e: dict) -> int | None:
        qin, qout, tin, tout, rec = self._split(e)
        log = self.entry_log[-1]
        if rec or len(tin) > 1 or len(tout) > 1:
            log["handled"] = "EXCLUDED_UNSUPPORTED_SHAPE"
            self.n("unsupported_swaps")
            for a in list(tin) + list(tout):
                self.contaminate(a, e["time"], e["id"], "UNSUPPORTED_SWAP_SHAPE")
            return None
        if not tin and not tout:
            log["handled"] = "QUOTE_CONVERSION"
            self.n("quote_conversions")
            for a, q in qin.items():
                self.quote_flow(a, "IN", q, e)
            for a, q in qout.items():
                self.quote_flow(a, "OUT", q, e)
            return None
        net = {a: qout.get(a, ZERO) - qin.get(a, ZERO) for a in set(qout) | set(qin)}    # positive: paid; negative: received
        if tin and tout:
            return self.token_to_token(e, next(iter(tout.items())), next(iter(tin.items())), qin, qout)
        if tin:
            return self.buy(e, *next(iter(tin.items())), net)
        return self.sell(e, *next(iter(tout.items())), net)

    def _price_check(self, asset: str, qty: Decimal, usd: Decimal | None, e: dict):
        """Flag a swap whose implied price is wildly off an observed one nearby: the usual signature of a decimals slip."""
        if usd is None or qty <= 0:
            return
        p = self.book.near(asset, e["time"])
        if not p or usd <= 0:
            return
        implied, f = usd / qty, dec(self.pol["price_mismatch_factor"])
        r = implied / p["usd"]
        if r > f or r < 1 / f:
            self.flag("IMPLIED_PRICE_MISMATCH", e["id"], f"swap implies {_q(implied, 12)} per unit, observed {_q(p['usd'], 12)}; check decimals", asset)
            self.contaminate(asset, e["time"], e["id"], "IMPLIED_PRICE_MISMATCH")

    def buy(self, e, asset, qty, net) -> int | None:
        log = self.entry_log[-1]
        usd, bases, native = self.book.value_net(net, e["time"])
        if not any(v > 0 for v in net.values()) or (usd is not None and usd <= 0):
            self.flag("BUY_WITHOUT_NET_PAYMENT", e["id"], "tokens arrived with no net quote outlay; not treated as a free purchase", asset)
            status, cost, cost_n = "UNKNOWN_ANOMALOUS_COST", None, None
        elif usd is None:
            status, cost, cost_n = "UNKNOWN_UNPRICED", None, native if (native is not None and native > 0) else None
            self.n("unpriced_buys")
        else:
            status, cost, cost_n = "KNOWN", usd, native if (native is not None and native > 0) else None
        self._price_check(asset, qty, cost, e)
        if "PEG_ASSUMED" in bases:
            self.n("peg_assumed_entries")
        pid = self.start_or_join_position(asset, e["time"], e["id"])
        self.new_lot(asset=asset, wallet=e["wallet"], acquired_at=e["time"], origin="SWAP_BUY", basis_status=status, bucket="TRADING", qty=qty, cost=cost, cost_native=cost_n,
                     position=pid, entry=e["id"], restored=False)
        for a, q in net.items():
            self.quote_flow(a, "OUT" if q > 0 else "IN", abs(q), e)
        log["handled"] = "BUY"
        log["basis"] = status
        log["price_basis"] = bases
        self.n("buys")
        return pid

    def sell(self, e, asset, qty, net) -> int | None:
        log = self.entry_log[-1]
        recv = {a: -v for a, v in net.items()}       # positive: received
        usd, bases, native = self.book.value_net(recv, e["time"])
        if usd is not None and usd < 0:
            self.flag("SELL_NET_PROCEEDS_NEGATIVE", e["id"], "quote paid out exceeded quote received; proceeds recorded as zero", asset)
            usd = ZERO
            native = ZERO if native is not None else None
        if native is not None and native < 0:
            native = ZERO
        if usd is None:
            self.n("unpriced_sells")
        if "PEG_ASSUMED" in bases:
            self.n("peg_assumed_entries")
        self._price_check(asset, qty, usd, e)
        pos0 = self.open_position_for(asset)
        slices = self.consume(asset, qty, "SALE", e, usd, native, proceeds_known=True)
        log["proceeds"], log["proceeds_native"] = usd, native
        for a, q in net.items():
            self.quote_flow(a, "IN" if q < 0 else "OUT", abs(q), e)
        self._after_disposal(asset, e)
        log["handled"] = "SELL"
        log["price_basis"] = bases
        self.n("sells")
        tp = next((s["position"] for s in slices if s["bucket"] == "TRADING" and s["position"]), pos0)
        if tp:
            self.positions[tp - 1]["entries"].append(e["id"])
        return tp

    def token_to_token(self, e, out_leg, in_leg, qin, qout) -> int | None:
        (a_out, q_out), (a_in, q_in) = out_leg, in_leg
        log = self.entry_log[-1]
        v_in, _ = self.book.unit_usd(a_in, e["time"])
        v_out, _ = self.book.unit_usd(a_out, e["time"])
        value = q_in * v_in if v_in is not None else (q_out * v_out if v_out is not None else None)
        if v_in is not None and v_out is not None:
            lo, hi = sorted((q_in * v_in, q_out * v_out))
            if lo > 0 and hi / lo > 2:
                self.flag("TOKEN_SWAP_VALUE_DISAGREES", e["id"], "the two tokens' observed prices imply values more than 2x apart", a_in)
        if value is None:
            self.n("unpriced_token_swaps")
        pos0 = self.open_position_for(a_out)
        slices = self.consume(a_out, q_out, "TOKEN_SWAP", e, value, None, proceeds_known=True)
        log["proceeds"], log["proceeds_native"] = value, None
        self._after_disposal(a_out, e)
        pid = self.start_or_join_position(a_in, e["time"], e["id"])
        self.new_lot(asset=a_in, wallet=e["wallet"], acquired_at=e["time"], origin="TOKEN_SWAP", basis_status="KNOWN" if value is not None else "UNKNOWN_UNPRICED", bucket="TRADING",
                     qty=q_in, cost=value, cost_native=None, position=pid, entry=e["id"], restored=False)
        for a, q in qin.items():
            self.quote_flow(a, "IN", q, e)
        for a, q in qout.items():
            self.quote_flow(a, "OUT", q, e)
        log["handled"] = "TOKEN_TO_TOKEN"
        self.n("token_swaps")
        return pid

    def _after_disposal(self, asset: str, e: dict):
        self.dust_close(asset, e)
        for p in self.positions:
            if p["asset"] == asset and p.get("closed_at") is None and self.trading_remaining(asset, p["id"]) <= 0:
                p["closed_at"] = e["time"]

    def transfer_out(self, e: dict) -> int | None:
        log = self.entry_log[-1]
        for g in e["legs"]:
            if g["dir"] != "OUT":
                continue
            if self.L.kind(g["asset"]) in QUOTE_KINDS:
                self.quote_flow(g["asset"], "OUT", g["amount"], e)
            elif self.L.kind(g["asset"]) == "TOKEN":
                self.consume(g["asset"], g["amount"], "TRANSFER_OUT", e, None, None, pool={"key": g["counterparty"] or "?"}, proceeds_known=False)
                self._after_disposal(g["asset"], e)
                self.n("transfers_out")
        log["handled"] = "TRANSFER_OUT"
        return None

    def transfer_in(self, e: dict) -> int | None:
        log = self.entry_log[-1]
        for g in e["legs"]:
            if g["dir"] != "IN":
                continue
            a, q = g["asset"], g["amount"]
            if self.L.kind(a) in QUOTE_KINDS:
                self.quote_flow(a, "IN", q, e)
                continue
            if self.L.kind(a) != "TOKEN":
                continue
            self.n("transfers_in")
            rem = q
            if e.get("origin") == "AIRDROP":
                self.new_lot(asset=a, wallet=e["wallet"], acquired_at=e["time"], origin="AIRDROP", basis_status="AIRDROP_ZERO", bucket="AIRDROP", qty=q, cost=ZERO, cost_native=ZERO,
                             position=None, entry=e["id"], restored=False)
                self.n("airdrops")
                continue
            if self.pol["return_matching"] and g["counterparty"]:
                for pe in [x for x in self.pool_out if x["asset"] == a and x["kind"] == "TRANSFER_OUT" and x["key"] == g["counterparty"] and x["qty_rem"] > 0 and x["time"] <= e["time"]]:
                    if rem <= 0:
                        break
                    r = min(rem, pe["qty_rem"])
                    basis = None if pe["basis"] is None else (pe["basis"] if r == pe["qty_rem"] else pe["basis"] * r / pe["qty_rem"])
                    basis_n = None if pe["basis_native"] is None else (pe["basis_native"] if r == pe["qty_rem"] else pe["basis_native"] * r / pe["qty_rem"])
                    if basis is not None:
                        pe["basis"] -= basis
                        self.restored_basis += basis
                    if basis_n is not None:
                        pe["basis_native"] -= basis_n
                    pe["qty_rem"] -= r
                    self.new_lot(asset=a, wallet=e["wallet"], acquired_at=pe["acquired_at"], origin=pe["origin"], basis_status=pe["basis_status"], bucket=pe["bucket"], qty=r, cost=basis,
                                 cost_native=basis_n, position=pe["position"], entry=e["id"], restored=True)
                    self.round_trips.append({"asset": a, "counterparty": g["counterparty"], "sent": pe["qty"], "returned": r, "out_entry": pe["from_entry"], "in_entry": e["id"]})
                    if pe["position"]:
                        self.positions[pe["position"] - 1]["closed_at"] = None
                    rem -= r
                    self.n("returns_matched")
            if rem > 0:
                self.new_lot(asset=a, wallet=e["wallet"], acquired_at=e["time"], origin="TRANSFER_IN", basis_status="UNKNOWN_EXTERNAL", bucket="UNKNOWN", qty=rem, cost=None, cost_native=None,
                             position=None, entry=e["id"], restored=False)
        log["handled"] = "TRANSFER_IN"
        return None

    def lp_add(self, e: dict) -> int | None:
        log = self.entry_log[-1]
        for g in e["legs"]:
            k = self.L.kind(g["asset"])
            if g["dir"] == "OUT" and k in QUOTE_KINDS:
                self.quote_flow(g["asset"], "OUT", g["amount"], e)
            elif g["dir"] == "OUT" and k == "TOKEN":
                self.consume(g["asset"], g["amount"], "LP_DEPLOY", e, None, None, pool={"key": g["counterparty"] or e.get("pool") or "LP?"}, proceeds_known=False)
                self._after_disposal(g["asset"], e)
                self.n("lp_deployed_legs")
            elif g["dir"] == "IN":
                self.n("lp_receipts_ignored")
        log["handled"] = "LP_ADD"
        return None

    def lp_remove(self, e: dict) -> int | None:
        log = self.entry_log[-1]
        for g in e["legs"]:
            k = self.L.kind(g["asset"])
            if g["dir"] == "IN" and k in QUOTE_KINDS:
                self.quote_flow(g["asset"], "IN", g["amount"], e)
            elif g["dir"] == "IN" and k == "TOKEN":
                a, rem = g["asset"], g["amount"]
                key = g["counterparty"] or e.get("pool") or "LP?"
                for pe in [x for x in self.pool_out if x["asset"] == a and x["kind"] == "LP_DEPLOY" and x["key"] == key and x["qty_rem"] > 0]:
                    if rem <= 0:
                        break
                    r = min(rem, pe["qty_rem"])
                    basis = None if pe["basis"] is None else (pe["basis"] if r == pe["qty_rem"] else pe["basis"] * r / pe["qty_rem"])
                    basis_n = None if pe["basis_native"] is None else (pe["basis_native"] if r == pe["qty_rem"] else pe["basis_native"] * r / pe["qty_rem"])
                    if basis is not None:
                        pe["basis"] -= basis
                        self.restored_basis += basis
                    if basis_n is not None:
                        pe["basis_native"] -= basis_n
                    pe["qty_rem"] -= r
                    self.new_lot(asset=a, wallet=e["wallet"], acquired_at=pe["acquired_at"], origin=pe["origin"], basis_status=pe["basis_status"], bucket=pe["bucket"], qty=r, cost=basis,
                                 cost_native=basis_n, position=pe["position"], entry=e["id"], restored=True)
                    if pe["position"]:
                        self.positions[pe["position"] - 1]["closed_at"] = None
                    rem -= r
                if rem > 0:
                    self.new_lot(asset=a, wallet=e["wallet"], acquired_at=e["time"], origin="LP_EXCESS", basis_status="UNKNOWN_LP_EXCESS", bucket="UNKNOWN", qty=rem, cost=None, cost_native=None,
                                 position=None, entry=e["id"], restored=False)
                    self.n("lp_excess_lots")
        log["handled"] = "LP_REMOVE"
        return None

    def internal_transfer(self, out_e: dict, in_e: dict, asset: str, qout: Decimal, qin: Decimal):
        """Both ends are in the declared group and share a transaction signature: no profit moves. A shortfall (fee-on-transfer) is a transfer tax."""
        self.entry_log.append({"id": out_e["id"] + "+" + in_e["id"], "type": "INTERNAL_TRANSFER", "handled": "INTERNAL_TRANSFER", "fee": None})
        self.internal_pairs += 1
        short = qout - qin
        if short > 0:
            self.consume(asset, short, "TRANSFER_TAX", out_e, ZERO, ZERO, proceeds_known=True)
            self._after_disposal(asset, out_e)
            self.n("transfer_tax_units_events")
        elif short < 0:
            self.new_lot(asset=asset, wallet=in_e["wallet"], acquired_at=in_e["time"], origin="TRANSFER_IN", basis_status="UNKNOWN_EXTERNAL", bucket="UNKNOWN", qty=-short, cost=None, cost_native=None,
                         position=None, entry=in_e["id"], restored=False)
            self.flag("INTERNAL_TRANSFER_RECEIVED_MORE", in_e["id"], "more arrived than left; the excess is an external lot", asset)

    def snapshot(self, e: dict):
        open_ = {}
        for l in self.lots:
            if l.qty > 0 and l.bucket == "TRADING":
                o = open_.setdefault(l.asset, {"qty": ZERO, "basis": ZERO, "unknown": False})
                o["qty"] += l.qty
                if l.cost is None:
                    o["unknown"] = True
                else:
                    o["basis"] += l.cost
        self.snapshots.append({"time": e["time"], "entry": e["id"], "realized": self.realized_usd_cum, "fees": self.fees_usd_cum, "open": open_})


def run_engine(L: Ledger, pol: dict, convention: str) -> Run:
    book = Book(L, pol)
    R = Run(L, pol, book, convention)
    for rj in L.rejects:       # a refused entry may have moved a token: positions alive at that time cannot be trusted
        for a in rj["assets"]:
            if rj["time"] is not None and L.kind(a) == "TOKEN":
                R.contaminate(L.canon(a), rj["time"], rj["id"], "REJECTED_" + rj["reason"])
    entries, skip = list(L.entries), set()
    if L.group:     # match transfers between group wallets by transaction signature
        outs = {(e["signature"], g["asset"]): (e, g) for e in entries if e["type"] == "TRANSFER_OUT" and e["signature"] for g in e["legs"] if g["dir"] == "OUT" and L.kind(g["asset"]) == "TOKEN"}
        pairs = []
        for e in entries:
            if e["type"] == "TRANSFER_IN" and e["signature"]:
                for g in e["legs"]:
                    k = (e["signature"], g["asset"])
                    if g["dir"] == "IN" and k in outs and outs[k][0]["wallet"] != e["wallet"] and (outs[k][0]["id"], k[1]) not in skip:
                        pairs.append((outs[k][0], e, g["asset"], outs[k][1]["amount"], g["amount"]))
                        skip.add((outs[k][0]["id"], k[1]))
                        skip.add((e["id"], k[1]))
    else:
        pairs = []
    pair_at = {(p[0]["id"]): p for p in pairs}
    for e in entries:
        done = False
        if any((e["id"], g["asset"]) in skip for g in e["legs"]):
            if e["id"] in pair_at:
                _, ine, a, qo, qi = pair_at[e["id"]]
                R.entry_log.append({"id": e["id"], "type": e["type"], "handled": "INTERNAL_OUT", "fee": None})
                R.n("entries")
                R.internal_transfer(e, ine, a, qo, qi)
                R.fee(e, None)
                R.snapshot(e)
            else:
                R.entry_log.append({"id": e["id"], "type": e["type"], "handled": "INTERNAL_IN", "fee": None})
                R.n("entries")
                R.fee(e, None)
                R.snapshot(e)
            done = True
        if not done:
            R.process(e)
    return R
