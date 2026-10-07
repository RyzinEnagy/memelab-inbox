"""m22: relative strength vs SOL, BTC and a peer basket.

Public interface:
    analyze(bundle, benchmarks) -> dict

benchmarks = {
    "SOL": {"chg_1h", "chg_6h", "chg_24h"},
    "BTC": {"chg_1h", "chg_6h", "chg_24h"},
    "peers": [{"symbol", "mint", "chg_1h", "chg_6h", "chg_24h", "vol_24h", "vol_6h"?}],
}

Output keys: rs_vs_sol, rs_vs_btc, rs_vs_peers, label (per window), peer_rank,
leader_laggard, rotation_note, plus facts/inferences/heuristics/unknowns.
"""
from __future__ import annotations

from statistics import median
from typing import Any

WINDOWS = ["1h", "6h", "24h"]

STRONG_T = 5.0   # percentage points of outperformance to call STRONG
WEAK_T = -5.0


def _num(x: Any) -> float | None:
    try:
        if x is None or isinstance(x, bool):
            return None
        v = float(x)
        return None if v != v else v
    except (TypeError, ValueError):
        return None


def _token_changes(bundle: dict) -> dict[str, float | None]:
    market = bundle.get("market") if isinstance(bundle.get("market"), dict) else {}
    chg = market.get("chg") if isinstance(market.get("chg"), dict) else {}
    out: dict[str, float | None] = {}
    for w in WINDOWS:
        v = chg.get(f"h{w[:-1]}")
        if v is None:
            v = chg.get(w) if w in chg else chg.get(f"chg_{w}")
        out[w] = _num(v)
    return out


def _bench_changes(b: Any) -> dict[str, float | None]:
    b = b if isinstance(b, dict) else {}
    return {w: _num(b.get(f"chg_{w}")) for w in WINDOWS}


def _label(diff: float | None) -> str | None:
    if diff is None:
        return None
    if diff >= STRONG_T:
        return "STRONG"
    if diff <= WEAK_T:
        return "WEAK"
    return "NEUTRAL"


def analyze(bundle: dict | None, benchmarks: dict | None) -> dict:
    bundle = bundle if isinstance(bundle, dict) else {}
    benchmarks = benchmarks if isinstance(benchmarks, dict) else {}
    facts: list[str] = []
    inferences: list[str] = []
    heuristics: list[str] = ["Relative strength = token % change minus benchmark % change (percentage points)",
                             f"STRONG if >= +{STRONG_T:.0f}pp vs peer median, WEAK if <= {WEAK_T:.0f}pp"]
    unknowns: list[str] = []

    symbol = (bundle.get("identity") or {}).get("symbol") if isinstance(bundle.get("identity"), dict) else None
    mint = bundle.get("mint")
    tok = _token_changes(bundle)
    sol = _bench_changes(benchmarks.get("SOL"))
    btc = _bench_changes(benchmarks.get("BTC"))
    raw_peers = benchmarks.get("peers")
    peers = [p for p in raw_peers if isinstance(p, dict)] if isinstance(raw_peers, (list, tuple)) else []
    peers = [p for p in peers if p.get("mint") != mint or mint is None]

    for w in WINDOWS:
        if tok[w] is None:
            unknowns.append(f"token chg_{w} missing")
        if sol[w] is None:
            unknowns.append(f"SOL chg_{w} missing")
    if not peers:
        unknowns.append("no peers supplied: peer-relative metrics unavailable")

    rs_vs_sol: dict[str, Any] = {}
    rs_vs_btc: dict[str, Any] = {}
    rs_vs_peers: dict[str, Any] = {}
    label: dict[str, str | None] = {}
    peer_rank: dict[str, Any] = {}

    for w in WINDOWS:
        t = tok[w]
        d_sol = None if t is None or sol[w] is None else t - sol[w]
        d_btc = None if t is None or btc[w] is None else t - btc[w]
        rs_vs_sol[w] = {"token": t, "benchmark": sol[w], "diff_pp": d_sol, "label": _label(d_sol)}
        rs_vs_btc[w] = {"token": t, "benchmark": btc[w], "diff_pp": d_btc, "label": _label(d_btc)}
        if d_sol is not None:
            facts.append(f"{w}: token {t:+.1f}% vs SOL {sol[w]:+.1f}% (RS {d_sol:+.1f}pp)")

        peer_vals = [_num(p.get(f"chg_{w}")) for p in peers]
        peer_vals_clean = [v for v in peer_vals if v is not None]
        if peer_vals_clean and t is not None:
            med = median(peer_vals_clean)
            d_peer = t - med
            n_better = sum(1 for v in peer_vals_clean if v > t)
            rank = n_better + 1
            n = len(peer_vals_clean) + 1
            pctile = 1.0 - (rank - 1) / max(n - 1, 1)
            rs_vs_peers[w] = {"token": t, "peer_median": med, "diff_pp": d_peer, "label": _label(d_peer),
                              "n_peers": len(peer_vals_clean)}
            peer_rank[w] = {"rank": rank, "of": n, "percentile": round(pctile, 2)}
            facts.append(f"{w}: token {t:+.1f}% vs peer median {med:+.1f}% (rank {rank}/{n})")
            label[w] = _label(d_peer)
        else:
            rs_vs_peers[w] = {"token": t, "peer_median": None, "diff_pp": None, "label": None, "n_peers": len(peer_vals_clean)}
            peer_rank[w] = None
            # fall back to SOL-relative label when peers are missing
            label[w] = _label(d_sol)
            if t is not None and not peer_vals_clean and peers:
                unknowns.append(f"peers lack chg_{w}")

    # leader / laggard
    ranks = [peer_rank[w]["percentile"] for w in WINDOWS if peer_rank.get(w)]
    leader_laggard = None
    if ranks:
        avg_p = sum(ranks) / len(ranks)
        if avg_p >= 0.75:
            leader_laggard = "LEADER"
        elif avg_p <= 0.25:
            leader_laggard = "LAGGARD"
        else:
            leader_laggard = "MID_PACK"
        inferences.append(f"Average peer percentile {avg_p:.0%} across windows -> {leader_laggard}")
    else:
        labels = [l for l in label.values() if l]
        if labels:
            if all(l == "STRONG" for l in labels):
                leader_laggard = "LEADER_VS_SOL"
            elif all(l == "WEAK" for l in labels):
                leader_laggard = "LAGGARD_VS_SOL"
            else:
                leader_laggard = "MIXED_VS_SOL"
            inferences.append(f"No peer ranking; SOL-relative labels {labels} -> {leader_laggard}")

    # trend across windows: improving if 1h RS > 24h RS
    d1 = rs_vs_peers.get("1h", {}).get("diff_pp")
    d24 = rs_vs_peers.get("24h", {}).get("diff_pp")
    if d1 is None:
        d1 = rs_vs_sol["1h"]["diff_pp"]
        d24 = rs_vs_sol["24h"]["diff_pp"]
    rs_trend = None
    if d1 is not None and d24 is not None:
        rs_trend = "IMPROVING" if d1 - d24 > 3 else "FADING" if d1 - d24 < -3 else "STABLE"
        inferences.append(f"RS trend {rs_trend} (1h RS {d1:+.1f}pp vs 24h RS {d24:+.1f}pp)")

    # capital rotation: peer volume rising while token's falling
    rotation_note = None
    market = bundle.get("market") if isinstance(bundle.get("market"), dict) else {}
    vol = market.get("vol") if isinstance(market.get("vol"), dict) else {}
    tv6, tv24 = _num(vol.get("h6")), _num(vol.get("h24"))
    tok_vol_ratio = None if tv6 is None or not tv24 else (tv6 * 4) / tv24
    peer_ratios = []
    for p in peers:
        pv6, pv24 = _num(p.get("vol_6h")), _num(p.get("vol_24h"))
        if pv6 is not None and pv24:
            peer_ratios.append(pv6 * 4 / pv24)
    if tok_vol_ratio is not None and peer_ratios:
        pm = median(peer_ratios)
        facts.append(f"Token 6h volume run-rate {tok_vol_ratio:.2f}x of 24h; peer median {pm:.2f}x")
        if tok_vol_ratio < 0.8 and pm > 1.1:
            rotation_note = ("Capital rotation OUT: peers' volume accelerating while token volume fades. "
                             "Token is losing share of sector flow.")
        elif tok_vol_ratio > 1.1 and pm < 0.9:
            rotation_note = ("Capital rotation IN: token volume accelerating while peers fade. "
                             "Token is gaining share of sector flow.")
        elif tok_vol_ratio > 1.1 and pm > 1.1:
            rotation_note = "Sector-wide volume acceleration; strength is not token-specific."
        elif tok_vol_ratio < 0.8 and pm < 0.9:
            rotation_note = "Sector-wide volume fade; weakness is not token-specific."
        else:
            rotation_note = "No clear rotation signal between token and peers."
        inferences.append(rotation_note)
    elif tok_vol_ratio is not None and peers:
        # peers lack intraday vol; compare 24h vol vs peers for a weaker hint
        pv = [_num(p.get("vol_24h")) for p in peers]
        pv = [v for v in pv if v is not None]
        if pv and tv24 is not None:
            rotation_note = (f"Token 6h run-rate {tok_vol_ratio:.2f}x of its own 24h volume; peers' intraday "
                             f"volume unavailable, so rotation cannot be confirmed (token 24h vol ${tv24:,.0f} vs "
                             f"peer median ${median(pv):,.0f}).")
            unknowns.append("peers lack vol_6h: rotation detection is indicative only")
        else:
            unknowns.append("peer volume missing: rotation undetectable")
    else:
        unknowns.append("volume data insufficient for rotation detection")

    # sector-vs-token decomposition
    if peers and tok["24h"] is not None and sol["24h"] is not None:
        pv24 = [_num(p.get("chg_24h")) for p in peers]
        pv24 = [v for v in pv24 if v is not None]
        if pv24:
            sector = median(pv24) - sol["24h"]
            idio = tok["24h"] - median(pv24)
            inferences.append(f"24h decomposition: SOL {sol['24h']:+.1f}pp, sector-vs-SOL {sector:+.1f}pp, "
                              f"token-specific {idio:+.1f}pp")
            heuristics.append("Token-specific component is the part of the move not explained by SOL or the peer basket")

    return {
        "symbol": symbol,
        "rs_vs_sol": rs_vs_sol,
        "rs_vs_btc": rs_vs_btc,
        "rs_vs_peers": rs_vs_peers,
        "peer_rank": peer_rank,
        "label": label,
        "leader_laggard": leader_laggard,
        "rs_trend": rs_trend,
        "rotation_note": rotation_note,
        "facts": facts,
        "inferences": inferences,
        "heuristics": heuristics,
        "unknowns": unknowns,
    }
