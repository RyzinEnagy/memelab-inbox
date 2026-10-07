"""Markdown report rendering in the curriculum format."""
from __future__ import annotations

import time
from typing import Any


def _ev(d: dict | None, keys=("facts", "inferences", "heuristics", "unknowns")) -> str:
    if not d:
        return "UNABLE TO DETERMINE (module did not run)\n"
    out = []
    labels = {"facts": "FACT", "inferences": "INFERENCE", "heuristics": "HEURISTIC", "unknowns": "UNKNOWN"}
    for k in keys:
        for line in d.get(k) or []:
            out.append(f"- {labels[k]}: {line}")
    if d.get("error"):
        out.append(f"- UNKNOWN: module error {d['error']}")
    return "\n".join(out) + "\n" if out else "- UNKNOWN: no observations\n"


def _usd(v):
    return "n/a" if v is None else f"${v:,.0f}"


def _pct(v, d=2):
    return "n/a" if v is None else f"{v:.{d}f}%"


def render_token_report(r: dict[str, Any]) -> str:
    b, m = r["bundle"], r["modules"]
    ident, mk = b.get("identity") or {}, b.get("market") or {}
    idm, sc, st = m["identity"], r["score"], r["status"]
    ts = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(b["observed_at"]))
    L = []
    L.append(f"# {ident.get('name') or 'UNKNOWN'} — {ident.get('symbol') or '?'}\n")
    L.append(f"TOKEN: {ident.get('name')}  \nTICKER: {ident.get('symbol')}  \nCHAIN: solana  \nCONTRACT: `{r['mint']}`  \n"
             f"TOKEN AGE: {('%.1f days' % (mk['age_hours']/24)) if mk.get('age_hours') else 'UNKNOWN'}  \nIDENTITY CONFIDENCE: {idm.get('confidence')}  \nTIMESTAMP: {ts}\n")
    if idm.get("status") == "IDENTITY NOT VERIFIED":
        L.append("\n## Status\n\nIDENTITY NOT VERIFIED. Analysis stopped.\n")
        L.append(_ev(idm))
        return "\n".join(L)
    # executive
    lc, dp, lp, hold, early = m.get("lifecycle") or {}, m.get("depth") or {}, m.get("lp") or {}, m.get("holders") or {}, m.get("early") or {}
    L.append("## Executive assessment\n")
    L.append(f"{ident.get('symbol')} is a {lc.get('stage', 'UNKNOWN')}-stage token (confidence {lc.get('confidence')}) with market cap {_usd(mk.get('market_cap'))}, displayed liquidity {_usd(mk.get('liquidity_usd_total'))} "
             f"and executable sell depth of about {_usd(dp.get('exit_capacity_usd_3pct'))} at 3% impact. Price structure is {(m.get('structure') or {}).get('structure', 'UNKNOWN')}; breakout state {(m.get('breakout') or {}).get('classification', 'UNKNOWN')}. "
             f"Adjusted top-10 ownership is {_pct(hold.get('adjusted_top10_pct'), 1)} with material wallets {early.get('large_holder_net_direction', 'UNKNOWN')}; LP risk {lp.get('lp_risk')}. "
             f"Opportunity score {sc.get('total')}/100{' with FATAL FLAGS: ' + ', '.join(f['flag'] for f in sc.get('fatal_flags') or []) if sc.get('fatal_flags') else ''}. Status: {st['status']}. {st.get('reasoning', '')}\n")
    L.append("## Before research: what would make this token unacceptable?\n")
    L += [f"- {c}" for c in r.get("unacceptable") or []]
    L.append("")
    if m.get("monitor") and not m["monitor"].get("first_snapshot"):
        mon = m["monitor"]
        L.append("## What changed since the last snapshot?\n")
        L += [f"- {x}" for x in mon.get("lines") or []]
        L.append(f"\nPREVIOUS INTERPRETATION: {mon.get('previous_interpretation')}\n\nNEW EVIDENCE: {'; '.join(mon.get('lines') or [])}\n\nREVISED INTERPRETATION: {mon.get('revised_interpretation')}\n")
        if mon.get("invalidated"):
            L.append(f"THESIS INVALIDATED: {mon.get('reason')}\n")
    L.append("## Why it surfaced\n")
    L.append((r["thesis"]["questions"].get("WHY IS IT RECEIVING ATTENTION?") or "on request") + "\n")
    L.append("## Identity\n" + _ev(idm))
    L.append("## Valuation and supply\n" + _ev(m.get("market")) + _ev(m.get("supply")))
    L.append("## Liquidity\n" + _ev(m.get("pools")))
    L.append("## Executable depth\n")
    tbl = dp.get("table") or []
    if tbl:
        L.append("| Side | Size (USD) | Status | Impact | Effective price | Proceeds / value | Route legs | Pools |\n|---|---|---|---|---|---|---|---|")
        for t in tbl:
            if t.get("status") == "OK":
                L.append(f"| {t['side']} | {_usd(t['usd'])} | OK | {t['impact_pct']:.2f}% | {t['effective_price']:.6g} | {_usd(t.get('usd_value'))} | {t['n_route_legs']} | {', '.join(t.get('pools') or [])} |")
            else:
                L.append(f"| {t['side']} | {_usd(t['usd'])} | {t.get('status')} | | | | | {t.get('error', '')} |")
        L.append("")
    L.append(_ev(dp))
    L.append("## LP structure\n" + f"LP RISK: {lp.get('lp_risk')} — {lp.get('reason')}\n\n" + _ev(lp))
    L.append("## Token mechanics\n" + _ev(m.get("mechanics")))
    L.append("## Ownership\n" + _ev(hold))
    cls = hold.get("classified") or []
    if cls:
        L.append("| Rank | Owner | % | Class | Basis |\n|---|---|---|---|---|")
        for c in cls[:15]:
            L.append(f"| {c['rank']} | `{c.get('owner')}` | {_pct(c.get('pct'))} | {c['classification']} | {c['basis']} |")
        L.append("")
    L.append("## Wallet clusters\n" + _ev(m.get("clusters")))
    for c in (m.get("clusters") or {}).get("clusters") or []:
        for e in c.get("evidence") or []:
            L.append(f"- FACT: {e['fact']}\n- INFERENCE: {e['inference']}\n- CONFIDENCE: {e['confidence']}")
    fo = m.get("forensics")
    if fo:
        L.append("\n## Wallet forensics (Helius transaction history)\n" + _ev(fo))
        L.append("| Wallet | First tx | First funder | Acquired via | Token in | Token out | Buy swaps | Sell swaps | CEX dest |\n|---|---|---|---|---|---|---|---|---|")
        for fr in (fo.get("rows") or [])[:15]:
            L.append(f"| `{fr['wallet']}` | {fr.get('first_tx') or ''} | `{(fr.get('first_funder') or '')}` | {fr.get('acquisition_mechanism') or ''} | {fr['token_in']:,.0f} | {fr['token_out']:,.0f} | {fr['swaps_buy']} | {fr['swaps_sell']} | {', '.join(fr.get('cex_destinations') or [])} |")
    L.append("\n## Dev / early-wallet behavior\n" + _ev(early))
    L.append("## Accumulation / distribution / absorption\n" + f"Direction: {early.get('large_holder_net_direction')}; pattern: {early.get('absorption') or 'UNABLE TO DETERMINE'}\n")
    L.append("## Order flow\n" + _ev(m.get("orderflow")))
    stt = m.get("structure") or {}
    L.append("## Price structure\n" + f"Structure: {stt.get('structure')} — {stt.get('structure_summary', '')}\n\n" + _ev(stt))
    L.append("## Support and resistance\n")
    zones = stt.get("zones") or []
    if zones:
        L.append("| TF | Kind | Low | High | Touches | Strength | Distance | Why |\n|---|---|---|---|---|---|---|---|")
        for z in zones[:14]:
            L.append(f"| {z.get('tf')} | {z.get('kind')} | {z.get('low'):.6g} | {z.get('high'):.6g} | {z.get('touches')} | {z.get('strength'):.2f} | {z.get('distance_pct'):+.1f}% | {z.get('why')} |")
        L.append("")
    else:
        L.append("UNABLE TO DETERMINE (insufficient candles)\n")
    bo = m.get("breakout") or {}
    cr = bo.get("chase_risk") if isinstance(bo.get("chase_risk"), dict) else {}
    cr_txt = (f"{'OVEREXTENDED' if cr.get('overextended') else 'not overextended'}: price {cr.get('distance_pct')}% / {cr.get('distance_atr')} ATR above {cr.get('invalidation_source')} {cr.get('invalidation_level'):.6g}" if cr.get("invalidation_level") else "n/a")
    L.append("## Breakout / retest assessment\n" + f"Classification: {bo.get('classification')}; chase risk: {cr_txt}\n\n" + _ev(bo))
    L.append("## Relative strength\n" + _ev(m.get("rs")))
    L.append("## Attention and narrative\n" + _ev(m.get("attention")))
    man = m.get("manipulation") or {}
    L.append("## Organic vs manufactured assessment\n" + f"ATTENTION QUALITY: {man.get('label')} (confidence {man.get('confidence')}, wash-trading {man.get('wash_trading')})\n")
    L.append("OBSERVED FACTS:\n" + "\n".join(f"- {x}" for x in man.get("observed_facts") or ["none"]) + "\n\nPOSSIBLE INTERPRETATION:\n" + "\n".join(f"- {x}" for x in man.get("possible_interpretation") or ["none"]) + "\n\nALTERNATIVE EXPLANATIONS:\n" + "\n".join(f"- {x}" for x in man.get("alternative_explanations") or ["none"]) + "\n\n" + "\n".join(f"- UNKNOWN: {u}" for u in man.get("unknowns") or []) + "\n")
    L.append("## Lifecycle\n" + f"MOST LIKELY STAGE: {lc.get('stage')}{('/' + str(lc.get('sub_stage'))) if lc.get('sub_stage') else ''} (confidence {lc.get('confidence')})\n\nEVIDENCE:\n" + "\n".join(f"- {e}" for e in lc.get("evidence") or ["none"]) + f"\n\nALTERNATIVE STAGE: {lc.get('alternative_stage')} — {lc.get('alternative_reason')}\n\nCONFIRM IF: {lc.get('confirm_if')}\n\nREJECT IF: {lc.get('reject_if')}\n")
    en = m.get("entries") or {}
    L.append("## Candidate entries\n")
    rr = {p.get("style"): p for p in (m.get("rr") or {}).get("per_entry") or []}
    for e in en.get("entries") or []:
        p = rr.get(e.get("style")) or {}
        L.append(f"### {e.get('style')}{' (pending)' if e.get('pending') else ''}\n")
        L.append(f"- ENTRY CONDITION: {e.get('condition')}\n- ENTRY ZONE: {e.get('zone_low'):.6g} – {e.get('zone_high'):.6g}\n- THESIS: {e.get('thesis')}\n- WHY THIS ENTRY EXISTS: {e.get('why_exists')}\n- EVIDENCE: {'; '.join(e.get('evidence') or [])}\n- INVALIDATION: {e.get('invalidation_text')} (level {e.get('invalidation_level'):.6g})\n- STOP LOCATION: {e.get('stop_text') or e.get('stop_location')}\n- EXPECTED EXECUTION: {e.get('expected_execution')}\n- ADVANTAGES: {'; '.join(e.get('advantages') or [])}\n- DISADVANTAGES: {'; '.join(e.get('disadvantages') or [])}")
        if p:
            sc_ = p.get("scenarios") or {}
            L.append(f"- RISK/REWARD: {p.get('rr_base')}R to first supply ({_fmt_sc(sc_.get('BASE'))}); {p.get('rr_bull')}R bull ({_fmt_sc(sc_.get('BULL'))}); EV range {p.get('ev_r_low')} to {p.get('ev_r_high')}R; {p.get('verdict')}")
        L.append("")
    for s, why in (en.get("omitted") or {}).items():
        L.append(f"- {s} omitted: {why}")
    L.append("\n## Risk/reward\n" + _ev(m.get("rr")))
    sz = m.get("sizing") or {}
    L.append("## Position-size constraints\n")
    if sz.get("needs_account_inputs"):
        L.append("Account-risk inputs not supplied; no dollar position is invented. Maximum position implied by executable liquidity:\n")
    lq = sz.get("liquidity_constraint") or {}
    L.append(f"- Entry max (<=1.5% impact): {_usd(lq.get('entry_max'))}\n- Exit max now (<=3% impact): {_usd(lq.get('exit_max_now'))}\n- Exit-constrained initial size by future multiple: " + ", ".join(f"{k}x -> {_usd(v)}" for k, v in (lq.get('exit_max_by_multiple') or {}).items()) + f"\n- Allowed size: {_usd(sz.get('allowed_size_usd'))} (binding: {sz.get('binding_constraint')})\n- Haircuts: " + ("; ".join(f"{h.get('name')} x{h.get('factor')} ({h.get('reason')})" for h in sz.get("haircuts") or []) or "none") + "\n")
    L.append(_ev(sz))
    ex = m.get("exit") or {}
    L.append("## Exit plan\n")
    for rung in ex.get("ladder") or []:
        L.append(f"- {rung.get('trigger')}: sell {rung.get('pct_of_position')}% — {rung.get('rationale')}")
    if ex.get("principal_reclaim"):
        L.append(f"- Principal reclaim: {ex['principal_reclaim'].get('text')}")
    if ex.get("trailing_invalidation"):
        L.append(f"- Trailing invalidation: {ex['trailing_invalidation'].get('text')}")
    if ex.get("blowoff"):
        L.append(f"- Blow-off rule: {ex['blowoff'].get('rule')}")
    real = ex.get("realizable") or {}
    if real:
        L.append(f"\nRealizable proceeds (basis {_usd(ex.get('realizable_basis_usd'))} position):\n\n| Multiple | Displayed | Realizable | Impact | Flag |\n|---|---|---|---|---|")
        for k, v in real.items():
            L.append(f"| {k}x | {_usd(v.get('displayed'))} | {_usd(v.get('realizable'))} | {_pct(v.get('impact_pct'))} | {v.get('flag') or ''} |")
    L.append("\n" + _ev(ex))
    L.append("## What improves the setup\n" + (r["thesis"]["questions"].get("WHAT WOULD IMPROVE THE SETUP?") or "UNABLE TO DETERMINE") + "\n")
    L.append("## What deteriorates the setup\n" + (r["thesis"]["questions"].get("WHAT WOULD DETERIORATE IT?") or "UNABLE TO DETERMINE") + "\n")
    L.append("## Fatal risks / unresolved questions\n")
    for f in sc.get("fatal_flags") or []:
        L.append(f"- FATAL {f.get('flag')}: {f.get('evidence')}")
    unk = []
    for k, v in m.items():
        for u in (v or {}).get("unknowns") or []:
            unk.append(f"- UNKNOWN ({k}): {u}")
    L += unk or ["- none recorded"]
    L.append("\n## Opportunity score\n")
    L.append(f"**{sc.get('total')}/100**" + (" — UNTRADEABLE (fatal flaw override)" if sc.get("untradeable") else "") + "\n")
    L.append("| Component | Points | Max | Rationale |\n|---|---|---|---|")
    for k, v in (sc.get("breakdown") or {}).items():
        L.append(f"| {k} | {v.get('points'):.1f} | {v.get('max')} | {'; '.join(v.get('rationale') or [])} |")
    L.append(f"\n## Confidence\n\n{_conf(r)}\n")
    L.append(f"## Current status\n\n**{st['status']}** — {st.get('reasoning', '')}\n")
    L.append("## Complete trade thesis\n")
    for q, a in r["thesis"]["questions"].items():
        L.append(f"**{q}** {a}\n")
    L.append("## Bottom line\n")
    L.append(_bottom_line(r))
    return "\n".join(L)


def _fmt_sc(s):
    if not s:
        return "n/a"
    return f"target {s.get('target'):.6g}, {s.get('return_pct'):+.0f}%" if s.get("target") is not None and s.get("return_pct") is not None else "n/a"


def _conf(r):
    unk = r["score"].get("unknown_count") or 0
    idc = r["modules"]["identity"].get("confidence")
    if idc in ("LOW", "NOT VERIFIED") or unk >= 4:
        return "LOW"
    return "MODERATE" if unk >= 2 else "HIGH"


def _bottom_line(r):
    sc, st, m = r["score"], r["status"], r["modules"]
    dp, lp, early, bo, lc = m.get("depth") or {}, m.get("lp") or {}, m.get("early") or {}, m.get("breakout") or {}, m.get("lifecycle") or {}
    pros, cons = [], []
    if (dp.get("exit_capacity_usd_3pct") or 0) >= 25000: pros.append(f"exit depth ~{_usd(dp['exit_capacity_usd_3pct'])} at 3% impact")
    elif dp.get("exit_capacity_usd_3pct") is not None: cons.append(f"exit depth only ~{_usd(dp['exit_capacity_usd_3pct'])} at 3% impact")
    if lp.get("lp_risk") in ("LOW",): pros.append("LP protocol-custodied or locked")
    elif lp.get("lp_risk") in ("HIGH", "CRITICAL"): cons.append(f"LP risk {lp['lp_risk']}")
    d = early.get("large_holder_net_direction")
    if d in ("ACCUMULATING", "HOLDING"): pros.append(f"material wallets {d.lower()}")
    elif d in ("DISTRIBUTING", "EXITING"): cons.append(f"material wallets {d.lower()}")
    if bo.get("classification") in ("BREAKOUT_RETEST", "CONFIRMED_BREAKOUT", "RECLAIM"): pros.append(f"structure: {bo['classification'].lower().replace('_', ' ')}")
    if (bo.get("chase_risk") or {}).get("overextended") if isinstance(bo.get("chase_risk"), dict) else bo.get("chase_risk"): cons.append("price extended from invalidation (chase risk)")
    if lc.get("stage") in ("DISTRIBUTION", "BREAKDOWN", "MANIA"): cons.append(f"lifecycle {lc['stage']}")
    text = f"Score {sc.get('total')}/100, status {st['status']}. "
    text += ("In favor: " + "; ".join(pros) + ". ") if pros else "Little in favor beyond surface activity. "
    text += ("Against: " + "; ".join(cons) + ". ") if cons else ""
    if sc.get("untradeable"):
        text += "A fatal flaw makes this untradeable regardless of score until the flagged condition changes. "
    text += "This is a tradeoff statement, not a buy/sell instruction: the entry conditions above define when evidence would be sufficient, and the invalidation defines when the thesis is wrong."
    return text + "\n"


def render_scout_report(env: dict[str, Any], candidates: list[dict], near_misses: list[dict], rejected: list[dict], when: float | None = None) -> str:
    ts = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(when or time.time()))
    L = [f"# Opportunity Scout report — {ts}\n", "## Market environment\n"]
    L += [f"- {k}: {v}" for k, v in env.items()]
    L.append("")
    if not candidates:
        L.append("## Candidates\n\nNo token met the bar for a serious candidate in this run. That is a valid outcome.\n")
    for i, c in enumerate(candidates, 1):
        m, b, sc, st = c["modules"], c["bundle"], c["score"], c["status"]
        ident, mk = b.get("identity") or {}, b.get("market") or {}
        dp, hold, early, bo, lc, att, en = (m.get(k) or {} for k in ("depth", "holders", "early", "breakout", "lifecycle", "attention", "entries"))
        e0 = (en.get("entries") or [{}])[0]
        L.append(f"## #{i} {ident.get('symbol')} — {ident.get('name')}\n")
        L.append(f"- Contract: `{c['mint']}`\n- Why it surfaced: {c['thesis']['questions'].get('WHY IS IT RECEIVING ATTENTION?')}\n- Lifecycle: {lc.get('stage')} ({lc.get('confidence')})\n- Market cap: {_usd(mk.get('market_cap'))}; liquidity: {_usd(mk.get('liquidity_usd_total'))}\n"
                 f"- Executable depth: sell ~{_usd(dp.get('exit_capacity_usd_3pct'))} at 3%, ~{_usd(dp.get('exit_capacity_usd_10pct'))} at 10%\n- Ownership: adjusted top-10 {_pct(hold.get('adjusted_top10_pct'), 1)}, largest unexplained {_pct(hold.get('largest_unexplained_pct'))}\n"
                 f"- Notable wallet behavior: {early.get('large_holder_net_direction')} / {early.get('absorption')}\n- Price structure: {(m.get('structure') or {}).get('structure')} / {bo.get('classification')}\n- Attention quality: {(m.get('manipulation') or {}).get('label')}; trend {att.get('trend')}\n"
                 f"- Entry condition: {e0.get('condition') or 'none defined'}\n- Invalidation concept: {e0.get('invalidation_text') or 'n/a'}\n- Primary risk: {(sc.get('fatal_flags') or [{}])[0].get('flag') if sc.get('fatal_flags') else _primary_risk(c)}\n- Score: {sc.get('total')}/100\n- Status: {st['status']}\n- Report: {c.get('report_path')}\n")
    L.append("## Near misses\n")
    L += [f"- {n['symbol']} `{n['mint']}`: score {n['score']}, status {n['status']} — {n['why']}" for n in near_misses] or ["- none"]
    L.append("\n## Rejected after due diligence\n")
    L += [f"- {x['symbol']} `{x['mint']}`: {x['why']}" for x in rejected] or ["- none"]
    L.append("")
    return "\n".join(L)


def _primary_risk(c):
    bd = c["score"].get("breakdown") or {}
    if not bd:
        return "n/a"
    worst = min(bd.items(), key=lambda kv: (kv[1].get("score") or 0))
    return f"{worst[0]} ({worst[1].get('points'):.1f}/{worst[1].get('max')})"
