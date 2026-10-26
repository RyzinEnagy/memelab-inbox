"""Phase 10: social, narrative and catalyst evidence socialcat-1, the social models on the frozen targets, the catalyst classifier,
the read-only social evidence adapter and the catalyst target proposals (memelab/predictive/socialcat.py).

Synthetic, seeded fixtures and temp files only; fitted fixture cards carry NO_REAL_HISTORICAL_EVIDENCE, and every catalyst and
social adapter result here is TEST_ONLY (no catalyst or social row is exported for the lab's decisions). The real run is
audits/predictive-intelligence/phase_10/probes/run_social.py. No network, fixed times, no language model. Scenario ids from the
package's ADVERSARIAL_SCENARIOS.md; CX-10 is this phase's new counterexample (the token row read from a later export).
"""
from __future__ import annotations

import ast
import inspect
import json
import math
import socket
import sqlite3
import types
from pathlib import Path

import numpy as np
import pytest

from memelab.predictive import baselines as B
from memelab.predictive import contract as C
from memelab.predictive import features as F
from memelab.predictive import labels as L
from memelab.predictive import socialcat as SC
from memelab.predictive import sources as SRC
from memelab.predictive import store as S
from memelab.social import alpha_core as AC
from memelab.social import replay_core as RC

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures" / "predictive"
H = types.ModuleType("asof_helpers")
exec(compile((FIX / "asof_helpers.py").read_text(), str(FIX / "asof_helpers.py"), "exec"), H.__dict__)
T1, T1B, T2 = L.T1, L.T1B, L.T2
D0 = C.parse_utc("2026-10-01T00:00:00Z")
MINT = H.MINT_A
MINT_B = H.MINT_B
NID = "kw:wolves"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("network use in a Phase 10 test")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(SRC, "curl_get", refuse)


# ---------------------------------------------------------------- export fixtures with the lab's attention lines
def breakdown(*, trend="attention trend STABILITY", strength="narrative strength 0.50", organic="attention organic",
              manip="manipulation screen MOSTLY ORGANIC / wash LOW", lifecycle="lifecycle BROAD_ATTENTION (confidence MODERATE)"):
    return json.dumps({"attention_narrative": {"rationale": [x for x in (trend, strength, organic) if x]},
                       "demand_order_flow": {"rationale": [x for x in ("net buyers 24h +12", manip) if x]},
                       "lifecycle_relative_strength": {"rationale": [x for x in (lifecycle, "peer position MID_PACK") if x]}})


def thesis(mint, created_at, *, bd=None, t=None, attention="STABILITY", lifecycle="BROAD_ATTENTION", **kw):
    row = H.thesis(mint, created_at, **kw)
    sn = json.loads(row["snapshot_json"])
    sn["t"] = created_at if t is None else t
    sn["attention"], sn["lifecycle"] = attention, lifecycle
    row["snapshot_json"] = json.dumps(sn)
    row["score_breakdown_json"] = bd if bd is not None else breakdown()
    return row


def token(mint, pool=H.POOL_A, *, website=None, twitter=None, telegram=None, narrative_id=None, chain="solana"):
    tk = H.token(mint, pool=pool, first_seen_at=H.T0, chain=chain)
    tk.update(website=website, twitter=twitter, telegram=telegram, narrative_id=narrative_id)
    return tk


def store(tmp_path, versions, name="s.sqlite"):
    """versions: [(t, theses, tokens)], oldest first."""
    con = S.connect(tmp_path / name)
    S.ingest_exports(con, [H.export(f"c{i + 1}", t, rows, toks) for i, (t, rows, toks) in enumerate(versions)], now=H.T0 + 30 * 86400)
    con.commit()
    return con


def ctx(commit, t, *, snaps=(), narratives=None, blob=None):
    return {"commit": commit, "commit_time": t, "blob": blob or "b" + commit,
            "narratives": narratives if narratives is not None else [{"narrative_id": NID, "first_seen_at": H.T0 - 3 * 86400}],
            "narrative_snapshots": list(snaps)}


def world(tmp_path, *, second_bd=None, second_attention="EXHAUSTION", name="s.sqlite"):
    d1, d2, d3 = H.D1, H.D2, H.D3
    r1 = thesis(MINT, d1 - 900, bd=breakdown(trend="attention trend ACCELERATION"), attention="ACCELERATION")
    r2 = thesis(MINT, d2 - 700, bd=second_bd or breakdown(trend="attention trend EXHAUSTION", organic="attention paid/boosted",
                                                          lifecycle="lifecycle DISTRIBUTION (confidence HIGH)"),
                attention=second_attention, lifecycle="DISTRIBUTION")
    r3 = thesis(MINT, d3 - 500, bd=breakdown(trend="attention trend STABILITY"))
    b1 = thesis(MINT_B, d2 - 600)
    t_plain = [token(MINT), token(MINT_B, pool=H.POOL_B)]
    t_later = [token(MINT, website="https://x.example", twitter="https://x.com/proj", narrative_id=NID), token(MINT_B, pool=H.POOL_B)]
    versions = [(d1, [r1], t_plain), (d2, [r1, r2, b1], t_plain), (d3, [r1, r2, r3, b1], t_later)]
    return store(tmp_path, versions, name=name), (d1, d2, d3)


def key_at(con, mint, t):
    return con.execute("SELECT decision_key FROM predictive_decisions WHERE mint=? AND decision_time=?", (mint, t)).fetchone()[0]


def vals(s):
    return {k: v["value"] for k, v in s["values"].items()}


def why(s):
    return {k: v["missing_reason"] for k, v in s["values"].items() if v["value"] is None}


# ---------------------------------------------------------------- parsing the lab's readings
def test_current_values_from_the_attention_manipulation_and_lifecycle_lines():
    p = SC.parse_row(thesis(MINT, 100.0, bd=breakdown(trend="attention trend ACCELERATION", strength="narrative strength 0.92",
                                                       manip="manipulation screen MIXED / UNCERTAIN / wash MODERATE",
                                                       lifecycle="lifecycle POST_BREAKDOWN/EXTINCTION (confidence LOW)"),
                            attention="ACCELERATION", lifecycle="POST_BREAKDOWN"))
    v = SC.current_values(p)
    assert v["sc_attention_trend_ord"] == (2.0, None) and v["sc_narrative_strength"] == (0.92, None)
    assert v["sc_attention_paid"] == (0.0, None) and v["sc_manipulation_ord"] == (1.0, None)
    assert v["sc_attention_suspect"] == (0.0, None) and v["sc_organic_acceleration"] == (1.0, None)
    assert v["sc_lifecycle_late"] == (1.0, None) and v["sc_lifecycle_conf_ord"] == (0.0, None)


def test_unknown_lines_are_not_observed_new_formats_unparseable_and_a_contradiction_is_refused():
    p = SC.parse_row(thesis(MINT, 100.0, bd=breakdown(trend="UNKNOWN: attention trend missing", strength="UNKNOWN: narrative strength missing",
                                                       organic="UNKNOWN: organic vs paid attention unknown"), attention=None))
    v = SC.current_values(p)
    assert v["sc_attention_trend_ord"] == (None, "NOT_OBSERVED_BY_LAB") and v["sc_narrative_strength"] == (None, "NOT_OBSERVED_BY_LAB")
    assert v["sc_attention_paid"] == (None, "NOT_OBSERVED_BY_LAB") and v["sc_attention_suspect"] == (None, "NOT_OBSERVED_BY_LAB")
    p2 = SC.parse_row(thesis(MINT, 100.0, bd=breakdown(trend="attention is rising fast"), attention=None))
    assert SC.current_values(p2)["sc_attention_trend_ord"] == (None, "UNPARSEABLE")
    p2b = SC.parse_row(thesis(MINT, 100.0, bd=breakdown(trend="attention trend SURGING"), attention=None))
    assert SC.current_values(p2b)["sc_attention_trend_ord"] == (None, "UNPARSEABLE")          # an unknown word is never guessed
    for stage, late in (("MANIA", 0.0), ("BROAD_ATTENTION", 0.0), ("DISTRIBUTION", 1.0), ("BREAKDOWN", 1.0)):
        assert SC.current_values(SC.parse_row(thesis(MINT, 100.0, lifecycle=stage)))["sc_lifecycle_late"] == (late, None), stage
    p3 = SC.parse_row(thesis(MINT, 100.0, bd=breakdown(trend="attention trend ACCELERATION"), attention="EXHAUSTION"))
    assert SC.current_values(p3)["sc_attention_trend_ord"] == (None, "INCONSISTENT_RECORD")
    p4 = SC.parse_row(thesis(MINT, 100.0, bd=breakdown(manip="manipulation screen TOTALLY FINE / wash LOW")))
    assert SC.current_values(p4)["sc_manipulation_ord"] == (None, "UNPARSEABLE")
    p5 = SC.parse_row(thesis(MINT, 100.0, lifecycle="SOMETHING_NEW"))
    assert SC.current_values(p5)["sc_lifecycle_late"] == (None, "UNPARSEABLE")
    p6 = SC.parse_row(thesis(MINT, 100.0, lifecycle="UNKNOWN"))
    assert SC.current_values(p6)["sc_lifecycle_late"] == (None, "NOT_OBSERVED_BY_LAB")
    p7 = SC.parse_row({"mint": MINT, "snapshot_json": "{not json", "score_breakdown_json": None})
    v7 = SC.current_values(p7)
    assert v7["sc_attention_trend_ord"][1] == "ABSENT_IN_SNAPSHOT" and v7["sc_lifecycle_late"][1] == "UNPARSEABLE"


def test_p16_paid_or_manufactured_attention_is_suspect_and_never_organic_acceleration():
    for organic, manip, suspect in (("attention paid/boosted", "manipulation screen MOSTLY ORGANIC / wash LOW", 1.0),
                                    ("attention organic", "manipulation screen LIKELY MANUFACTURED / wash MODERATE", 1.0),
                                    ("attention organic", "manipulation screen SEVERELY MANIPULATED / wash HIGH", 1.0),
                                    ("attention organic", "manipulation screen MIXED / UNCERTAIN / wash MODERATE", 0.0)):
        v = SC.current_values(SC.parse_row(thesis(MINT, 1.0, bd=breakdown(trend="attention trend ACCELERATION", organic=organic, manip=manip),
                                                  attention="ACCELERATION")))
        assert v["sc_attention_suspect"] == (suspect, None)
        assert v["sc_organic_acceleration"] == (1.0 - suspect, None)
    v = SC.current_values(SC.parse_row(thesis(MINT, 1.0, bd=breakdown(trend="attention trend ACCELERATION", organic="UNKNOWN: organic vs paid attention unknown",
                                                                       manip="manipulation screen LIKELY MANUFACTURED / wash HIGH"), attention="ACCELERATION")))
    assert v["sc_attention_suspect"] == (1.0, None) and v["sc_organic_acceleration"] == (0.0, None)   # known suspect without the paid line
    v = SC.current_values(SC.parse_row(thesis(MINT, 1.0, bd=breakdown(trend="attention trend ACCELERATION", organic="UNKNOWN: organic vs paid attention unknown"),
                                              attention="ACCELERATION")))
    assert v["sc_attention_suspect"][0] is None and v["sc_organic_acceleration"][0] is None    # unknown never counts as organic


def test_channels_count_http_links_only_and_search_pages_are_fake():
    v = SC.channel_values(token(MINT, website="https://site.example", twitter="https://x.com/search?q=%24ABC&src=typed_query",
                                telegram="None"))
    assert v["sc_channels_n"] == (1.0, None) and v["sc_channel_search_url"] == (1.0, None) and v["sc_narrative_tagged"] == (0.0, None)
    v = SC.channel_values(token(MINT, website="", twitter="https://x.com/proj", telegram="https://t.me/proj", narrative_id=NID))
    assert v["sc_channels_n"] == (2.0, None) and v["sc_channel_search_url"] == (0.0, None) and v["sc_narrative_tagged"] == (1.0, None)
    assert SC.channel_values(token(MINT, website="not a link"))["sc_channels_n"] == (0.0, None)
    assert SC.channel_values(token(MINT, narrative_id="None"))["sc_narrative_tagged"] == (0.0, None)   # the export's "None" string
    assert SC.channel_values(None)["sc_channels_n"] == (None, "NO_TOKEN_ROW")


# ---------------------------------------------------------------- the as-of snapshot on a store
def test_values_are_available_at_the_decision_and_never_use_a_later_decision(tmp_path):
    con, (d1, d2, d3) = world(tmp_path)
    s1 = SC.socialcat_as_of(con, "solana", MINT, d1, decision_key=key_at(con, MINT, d1), context=ctx("c1", d1))
    assert vals(s1)["sc_attention_trend_ord"] == 2.0 and vals(s1)["sc_attention_suspect"] == 0.0
    assert all(v["available_at"] == d1 for v in s1["values"].values() if v["value"] is not None)
    assert why(s1)["sc_d_attention_trend"] == "NO_PRIOR_DECISION"
    assert s1["catalyst_state"] == SC.CATALYST_STATE_REAL and s1["social_state"] == SC.SOCIAL_STATE_REAL
    assert s1["lab_event_classes"] == ["HIGH_ATTENTION_PROXY"]
    s3n = SC.socialcat_as_of(con, "solana", MINT, d3, context=ctx("c3", d3))       # without a key: the newest visible decision
    assert s3n["decision_key"] == key_at(con, MINT, d3)
    with pytest.raises(SC.SocialCatError):                                       # the d2 decision is not visible at d1
        SC.socialcat_as_of(con, "solana", MINT, d1, decision_key=key_at(con, MINT, d2))
    with pytest.raises(RC.LeakageError):
        F.AsOfView(con, d1).audit.check("decision", [{"_avail": d2}], d1)


def test_truncated_store_gives_the_same_snapshot(tmp_path):
    con, (d1, d2, d3) = world(tmp_path)
    k = key_at(con, MINT, d2)
    full = SC.socialcat_as_of(con, "solana", MINT, d2, decision_key=k, context=ctx("c2", d2))
    cut = F.truncated_copy(con, d2)
    trunc = SC.socialcat_as_of(cut, "solana", MINT, d2, decision_key=k, context=ctx("c2", d2))
    assert trunc["socialcat_snapshot_sha"] == full["socialcat_snapshot_sha"]


def test_change_features_and_the_attention_reversal_use_the_previous_decision_only(tmp_path):
    con, (d1, d2, d3) = world(tmp_path)
    s2 = SC.socialcat_as_of(con, "solana", MINT, d2, decision_key=key_at(con, MINT, d2), context=ctx("c2", d2))
    v = vals(s2)
    assert v["sc_d_attention_trend"] == -2.0 and v["sc_attention_reversal"] == 1.0 and v["sc_attention_suspect"] == 1.0
    assert v["sc_lifecycle_late"] == 1.0 and "NARRATIVE_REVERSAL" in s2["lab_event_classes"]
    assert "HIGH_ATTENTION_PROXY" not in s2["lab_event_classes"]
    s3 = SC.socialcat_as_of(con, "solana", MINT, d3, decision_key=key_at(con, MINT, d3), context=ctx("c3", d3))
    assert vals(s3)["sc_d_attention_trend"] == 1.0 and vals(s3)["sc_attention_reversal"] == 0.0     # d2 is the previous one, not d1


def test_no_reversal_from_exhaustion_and_suspect_acceleration_is_not_high_attention(tmp_path):
    d1, d2 = H.D1, H.D2
    r1 = thesis(MINT, d1 - 900, bd=breakdown(trend="attention trend EXHAUSTION"), attention="EXHAUSTION")
    r2 = thesis(MINT, d2 - 700, bd=breakdown(trend="attention trend EXHAUSTION"), attention="EXHAUSTION")
    con = store(tmp_path, [(d1, [r1], [token(MINT)]), (d2, [r1, r2], [token(MINT)])])
    v = vals(SC.socialcat_as_of(con, "solana", MINT, d2, decision_key=key_at(con, MINT, d2), context=ctx("c2", d2)))
    assert v["sc_attention_reversal"] == 0.0 and v["sc_d_attention_trend"] == 0.0
    r3 = thesis(MINT_B, d1 - 900, bd=breakdown(trend="attention trend ACCELERATION", organic="attention paid/boosted"), attention="ACCELERATION")
    con2 = store(tmp_path, [(d1, [r3], [token(MINT_B, pool=H.POOL_B)])], name="s2.sqlite")
    s = SC.socialcat_as_of(con2, "solana", MINT_B, d1, decision_key=key_at(con2, MINT_B, d1), context=ctx("c1", d1))
    assert vals(s)["sc_organic_acceleration"] == 0.0 and s["lab_event_classes"] == []


def test_p36_snapshot_time_after_the_decision_refuses_the_row(tmp_path):
    d1 = H.D1
    con = store(tmp_path, [(d1, [thesis(MINT, d1 - 900, t=d1 + 60)], [token(MINT)])])
    s = SC.socialcat_as_of(con, "solana", MINT, d1, decision_key=key_at(con, MINT, d1), context=ctx("c1", d1))
    assert set(why(s).values()) == {"INCONSISTENT_TIME"} and len(why(s)) == len(SC.SC)


def test_identity_and_scope(tmp_path):
    d1 = H.D1
    evm = "0x1b54e762aa34cf6e28e9c082f2848e28e45da6b8"
    con = store(tmp_path, [(d1, [thesis(MINT, d1 - 900), thesis(evm, d1 - 800)],
                            [token(MINT), token(evm, pool="0x" + "ab" * 20, chain="bsc")])])
    s = SC.socialcat_as_of(con, "solana", "So11111111111111111111111111111111111111112", d1)
    assert set(why(s).values()) == {"NOT_IN_UNIVERSE"}
    sb = SC.socialcat_as_of(con, "bsc", evm, d1)
    assert set(why(sb).values()) == {"OUT_OF_SCOPE_CHAIN"}
    with pytest.raises(SC.SocialCatError):
        SC.socialcat_as_of(con, "solana", MINT, d1 + 5, decision_key=key_at(con, MINT, d1))


def test_cx10_the_token_row_and_narrative_tables_come_from_the_decisions_own_export(tmp_path):
    """CX-10: the later export tags the mint and adds channels; a decision at the earlier export never sees them."""
    con, (d1, d2, d3) = world(tmp_path)
    s2 = SC.socialcat_as_of(con, "solana", MINT, d2, decision_key=key_at(con, MINT, d2), context=ctx("c2", d2))
    assert vals(s2)["sc_narrative_tagged"] == 0.0 and vals(s2)["sc_channels_n"] == 0.0
    assert why(s2)["sc_narrative_lifecycle_ord"] == "NO_NARRATIVE_TAG"
    s3 = SC.socialcat_as_of(con, "solana", MINT, d3, decision_key=key_at(con, MINT, d3), context=ctx("c3", d3))
    assert vals(s3)["sc_narrative_tagged"] == 1.0 and vals(s3)["sc_channels_n"] == 2.0
    dec2 = dict(con.execute("SELECT * FROM predictive_decisions WHERE decision_key=?", (key_at(con, MINT, d2),)).fetchone())
    for bad in (ctx("c3", d3), ctx("c3", d2), ctx("c2", d3), ctx("c2", d2, blob="bc3"), ctx("c3", d2, blob="bc2")):     # P04
        with pytest.raises(SC.ContextRefused):
            SC.socialcat_as_of(con, "solana", MINT, d2, decision_key=dec2["decision_key"], context=bad)
    assert json.loads(dec2["token_json"]).get("narrative_id") is None


def test_narrative_context_newest_snapshot_at_or_before_t(tmp_path):
    con, (d1, d2, d3) = world(tmp_path)
    k = key_at(con, MINT, d3)
    snaps = [{"id": 1, "narrative_id": NID, "observed_at": d3 - 7200, "lifecycle": "EMERGING", "catalyst_events_7d": 2, "mcap_chg_24h_pct": 5.0},
             {"id": 2, "narrative_id": NID, "observed_at": d3 - 3600, "lifecycle": "ACCELERATING", "catalyst_events_7d": 3, "mcap_chg_24h_pct": 9.0},
             {"id": 3, "narrative_id": "kw:other", "observed_at": d3 - 60, "lifecycle": "DEAD", "catalyst_events_7d": 0, "mcap_chg_24h_pct": -50.0}]
    v = vals(SC.socialcat_as_of(con, "solana", MINT, d3, decision_key=k, context=ctx("c3", d3, snaps=snaps)))
    assert v["sc_narrative_lifecycle_ord"] == 4.0 and v["sc_narrative_catalyst_kw_7d"] == 3.0 and v["sc_narrative_mcap_chg_24h_pct"] == 9.0
    assert v["sc_narrative_snapshot_age_h"] == 1.0 and v["sc_narrative_age_h"] == pytest.approx((d3 - (H.T0 - 3 * 86400)) / 3600)
    late = snaps + [{"id": 4, "narrative_id": NID, "observed_at": d3 + 1, "lifecycle": "MANIA"}]
    w = why(SC.socialcat_as_of(con, "solana", MINT, d3, decision_key=k, context=ctx("c3", d3, snaps=late)))
    assert w["sc_narrative_lifecycle_ord"] == "INCONSISTENT_TIME"
    w = why(SC.socialcat_as_of(con, "solana", MINT, d3, decision_key=k, context=ctx("c3", d3, narratives=[{"narrative_id": NID, "first_seen_at": d3 + 5}])))
    assert w["sc_narrative_age_h"] == "INCONSISTENT_TIME" and w["sc_narrative_lifecycle_ord"] == "NO_NARRATIVE_SNAPSHOT"
    w = why(SC.socialcat_as_of(con, "solana", MINT, d3, decision_key=k, context=None))
    assert w["sc_narrative_lifecycle_ord"] == "CONTEXT_NOT_SUPPLIED"
    unk = [dict(snaps[1], lifecycle="UNKNOWN")]
    assert why(SC.socialcat_as_of(con, "solana", MINT, d3, decision_key=k, context=ctx("c3", d3, snaps=unk)))["sc_narrative_lifecycle_ord"] == "NOT_OBSERVED_BY_LAB"


def test_snapshot_is_deterministic_and_values_are_finite(tmp_path):
    con, (d1, d2, d3) = world(tmp_path)
    a = SC.socialcat_as_of(con, "solana", MINT, d3, decision_key=key_at(con, MINT, d3), context=ctx("c3", d3))
    b = SC.socialcat_as_of(con, "solana", MINT, d3, decision_key=key_at(con, MINT, d3), context=ctx("c3", d3))
    assert a == b
    for v in a["values"].values():
        assert v["value"] is None or math.isfinite(v["value"])
        assert v["missing_reason"] is None or v["missing_reason"] in SC.REASONS
    with pytest.raises(SC.SocialCatError):
        SC._value(float("nan"), None, d3, ["x"])                     # P38
    with pytest.raises(SC.SocialCatError):
        SC._value(None, "MADE_UP_REASON", None, ())


# ---------------------------------------------------------------- synthetic examples for the models
def ex(i, *, t, y, trend, suspect=0.0, mat=None, mint=None, narrative=None, extra=None):
    x = {c: float("nan") for c in SC.ALLOWED}
    x.update({B.LIQ: 10.0 + (i % 7) * 0.1, B.MCAP: 13.0 + (i % 5) * 0.1, B.VOL: 11.0 + (i % 3) * 0.2, B.FATAL: 0.0,
              "sc_attention_trend_ord": trend, "sc_attention_suspect": suspect, "sc_narrative_strength": 0.1 * (i % 10),
              "sc_manipulation_ord": float(i % 4), "sc_lifecycle_late": float(i % 2), "sc_channels_n": float(i % 3),
              "sc_d_attention_trend": float(i % 3) - 1.0, "sc_attention_reversal": float(i % 5 == 0)})
    x.update(extra or {})
    av = {c: t for c in SC.ALLOWED}
    return SC.SExample(decision_key=f"k{i:04d}", chain="solana", mint=mint or f"M{i:04d}", decision_time=t,
                       label_matures_at=mat if mat is not None else t + 86400 + 900, y=int(y), x=x, avail=av, narrative=narrative)


def signal_world(n=400, seed=7, start=D0, step=1800.0):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        tr = float(rng.integers(0, 3))
        p = 0.6 if tr == 2.0 else 0.1
        out.append(ex(i, t=start + i * step, y=rng.random() < p, trend=tr, suspect=float(rng.random() < 0.2)))
    return out


def test_count_gate_abstains_below_the_minimum():
    train = signal_world(60)
    cut = max(e.label_matures_at for e in train) + 1
    for m in SC.MODEL_IDS:
        c = SC.fit(m, T1, train, cut, is_fixture=True)
        assert c["body"]["abstain"] == "INSUFFICIENT_HISTORY"
        p, w = SC.predict(c, [ex(9999, t=cut + 10, y=0, trend=2.0)])
        assert not math.isfinite(p[0]) and w[0] == "INSUFFICIENT_HISTORY"


def test_fixture_signal_is_found_and_flagged_as_fixture():
    train = signal_world(400)
    cut = max(e.label_matures_at for e in train) + 1
    test = [ex(5000 + i, t=cut + 60 * i, y=0, trend=2.0 if i % 2 else 0.0) for i in range(20)]
    for m in ("R2_SC_RULE", "S1_SC_LOGIT", "S2_SC_LOGIT_B2", "S3_SC_LOGIT_TREND", "G1_SC_STUMPS_B2"):
        c = SC.fit(m, T1, train, cut, is_fixture=True)
        assert c["evidence_class"] == B.FIXTURE_FLAG and c["promotion"] == "MODEL_NOT_PROMOTED" and c["status"] == B.PROVISIONAL
        assert c["llm_used"] is False and c["catalyst_state"] == SC.CATALYST_STATE_REAL
        p, _ = SC.predict(c, test)
        assert np.mean(p[1::2]) > np.mean(p[0::2]) + 0.2, m
    nc = SC.fit(SC.PRIMARY, T1, train, cut, y_override=np.random.default_rng(0).permutation(B.labels_of(train)), card_kind="NC1SC")
    p, _ = SC.predict(nc, test)
    assert abs(np.mean(p[1::2]) - np.mean(p[0::2])) < 0.2


def test_rule_cells_are_shrunk_to_the_training_prevalence_and_a_missing_cell_gives_b0():
    train = signal_world(400)
    cut = max(e.label_matures_at for e in train) + 1
    c = SC.fit("R2_SC_RULE", T1, train, cut)
    b0 = float(B.labels_of(train).mean())
    cell = [e for e in train if e.x["sc_attention_trend_ord"] == 2.0 and e.x["sc_attention_suspect"] == 1.0]
    k = sum(e.y for e in cell)
    assert c["body"]["cells"]["T2S1"]["p"] == pytest.approx((k + 20 * b0) / (len(cell) + 20))
    assert SC.predict(c, [ex(9000, t=cut + 1, y=0, trend=float("nan"))])[0][0] == pytest.approx(b0)


def test_s2_uses_required_rows_optional_missing_inputs_and_a2_the_same_rows():
    train = signal_world(400)
    for i, e in enumerate(train):
        if i % 5 == 0:
            e.x["sc_narrative_strength"] = float("nan")
        if i % 9 == 0:
            e.x["sc_attention_suspect"] = float("nan")                # required: the row is not used
    cut = max(e.label_matures_at for e in train) + 1
    c = SC.fit(SC.PRIMARY, T1, train, cut)
    n_req = sum(1 for e in train if math.isfinite(e.x["sc_attention_suspect"]))
    assert c["n_used"] == n_req and c["body"]["prep"]["ind"]
    p, w = SC.predict(c, [ex(9001, t=cut + 1, y=0, trend=float("nan"))])
    assert not math.isfinite(p[0]) and w[0] == "OOD"
    a2 = SC.fit("A2_SC_B2_TC", T1, train, cut)
    g1 = SC.fit("G1_SC_STUMPS_B2", T1, train, cut)
    assert a2["n_used"] == c["n_used"] == g1["n_used"] and a2["body"]["spec"]["columns"] == list(B.B2_COLUMNS)
    assert len(g1["body"]["stumps"]["trees"]) == 100


def test_p13_a_card_never_scores_an_earlier_decision():
    train = signal_world(400)
    cut = max(e.label_matures_at for e in train) + 1
    for m in ("S1_SC_LOGIT", "G1_SC_STUMPS_B2", "R2_SC_RULE"):
        c = SC.fit(m, T1, train, cut)
        with pytest.raises(SC.ModelTrainedAfterDecision):
            SC.predict(c, [ex(9002, t=cut - 1, y=0, trend=1.0)])


def test_training_rows_must_be_matured_and_inputs_declared():
    train = signal_world(400)
    cut = max(e.label_matures_at for e in train) + 1
    late = train[:-1] + [ex(9003, t=cut - 10, y=1, trend=2.0, mat=cut + 100)]
    with pytest.raises((B.BaselineError, F.AsOfError)):
        SC.fit("S1_SC_LOGIT", T1, late, cut)
    e = train[0]
    e2 = SC.SExample(**{**e.__dict__, "x": {**e.x, "trap_next_decision_trend": 2.0}, "avail": {**e.avail, "trap_next_decision_trend": e.decision_time}})
    with pytest.raises(F.AsOfError):                               # NC2-SC: an undeclared column never reaches a fit
        SC.check_asof([e2], ["trap_next_decision_trend"], as_of=None, with_labels=False)
    e3 = SC.SExample(**{**e.__dict__, "avail": {**e.avail, "sc_attention_trend_ord": e.decision_time + 1}})
    with pytest.raises(F.AsOfError):                               # P36: a value available after the decision
        SC.check_asof([e3], ["sc_attention_trend_ord"], as_of=None, with_labels=False)


def test_card_roundtrip_tamper_and_version():
    train = signal_world(400)
    cut = max(e.label_matures_at for e in train) + 1
    for m, field_ in ((SC.PRIMARY, "logistic"), ("G1_SC_STUMPS_B2", "stumps")):
        c = SC.fit(m, T1, train, cut)
        back = SC.loads(SC.dumps(c))
        assert back == c
        p1, _ = SC.predict(c, [ex(7000, t=cut + 5, y=0, trend=2.0)])
        p2, _ = SC.predict(back, [ex(7000, t=cut + 5, y=0, trend=2.0)])
        assert np.array_equal(p1, p2)
        t = json.loads(SC.dumps(c))
        if field_ == "logistic":
            t["body"]["logistic"]["coef"][0] += 1e-9
        else:
            t["body"]["stumps"]["trees"][0][2] += 1e-9
        with pytest.raises(B.ModelHashMismatch):
            SC.verify_card(t)
        t2 = json.loads(SC.dumps(c))
        t2["socialcat_version"] = "socialcat-0"
        t2["model_sha"] = B.sha({k: v for k, v in t2.items() if k != "model_sha"})
        with pytest.raises(F.FeatureVersionError):
            SC.verify_card(t2)
        assert "pickle" not in SC.dumps(c)


def test_walk_forward_reuses_phase_07_folds_and_b0_b2_numbers():
    dev = signal_world(400, start=C.parse_utc("2026-10-05T00:00:00Z"), step=2700.0)
    for e in dev:
        e.label_matures_at = e.decision_time + B.maturity_lag(T1)
    dev = [e for e in dev if e.label_matures_at <= L.holdout_start()]

    def train_at(cut):
        return [e for e in dev if e.decision_time < cut and e.label_matures_at <= cut]

    def strip(e):
        return B.Example(**{k: v for k, v in e.__dict__.items() if k in B.Example.__dataclass_fields__})
    res = SC.walk_forward(T1, dev, train_at, nc1_seeds=range(2), is_fixture=True)
    ref = B.walk_forward(T1, [strip(e) for e in dev], lambda c: [strip(e) for e in train_at(c)], nc1_seeds=range(2), is_fixture=True)
    assert res["split_fingerprint"] == ref["split_fingerprint"] and res["folds"]
    for a, b in zip(res["oos"], ref["oos"]):
        for k in ("B0", "B2"):
            assert (math.isnan(a[k]) and math.isnan(b[k])) or a[k] == pytest.approx(b[k], abs=1e-15)
    assert all(r["R3_alarm"] in (True, False) for r in res["oos"]) and all(r["campaign"].startswith("mint:") for r in res["oos"])


def test_walk_forward_refuses_a_training_set_other_than_the_index():
    dev = signal_world(400, start=C.parse_utc("2026-10-05T00:00:00Z"), step=2700.0)
    for e in dev:
        e.label_matures_at = e.decision_time + B.maturity_lag(T1)
    dev = [e for e in dev if e.label_matures_at <= L.holdout_start()]
    with pytest.raises(B.WalkForwardMismatch):
        SC.walk_forward(T1, dev, lambda c: [e for e in dev if e.decision_time < c][:-1], nc1_seeds=range(1))


def _snap_for(e, *, t=None, missing=()):
    vals_ = {c: {"value": (None if c in missing else 1.0), "missing_reason": ("NOT_OBSERVED_BY_LAB" if c in missing else None),
                 "available_at": (None if c in missing else e.decision_time)} for c in SC.SC}
    return {"decision_key": e.decision_key, "chain": e.chain, "mint": e.mint, "decision_time": e.decision_time if t is None else t,
            "values": vals_, "socialcat_snapshot_sha": "x", "row_sha256": "r"}


def test_attach_checks_identity_and_keeps_missing_values_missing():
    e = B.Example(decision_key="k1", chain="solana", mint=MINT, decision_time=1000.0, label_matures_at=2000.0, y=0)
    out = SC.attach([e], {"k1": _snap_for(e, missing=("sc_narrative_strength",))})[0]
    assert math.isnan(out.x["sc_narrative_strength"]) and out.avail["sc_narrative_strength"] == 1000.0
    assert out.sc_reasons == {"sc_narrative_strength": "NOT_OBSERVED_BY_LAB"} and out.x["sc_attention_trend_ord"] == 1.0
    with pytest.raises(B.IdentityJoinError):
        SC.attach([e], {"k1": _snap_for(e, t=999.0)})
    with pytest.raises(B.IdentityJoinError):
        SC.attach([e], {"k1": dict(_snap_for(e), mint=MINT_B)})
    bad = _snap_for(e)
    bad["values"]["sc_channels_n"]["available_at"] = None
    with pytest.raises(SC.SocialCatError):
        SC.attach([e], {"k1": bad})


def test_count_gate_counts_the_rows_a_model_uses():
    train = signal_world(400)
    for e in train[50:]:
        e.x["sc_attention_trend_ord"] = float("nan")
    cut = max(e.label_matures_at for e in train) + 1
    c = SC.fit("S1_SC_LOGIT", T1, train, cut)
    assert c["body"]["abstain"] == "INSUFFICIENT_HISTORY" and c["n_used"] == 50 and c["n_train"] == 400


def test_degenerate_flag_and_campaign_groups():
    assert SC.degenerate([0.2, 0.2, 0.2]) and not SC.degenerate([0.2, 0.3]) and not SC.degenerate([0.2])
    a = ex(1, t=1.0, y=0, trend=1.0, narrative=NID)
    b = ex(2, t=1.0, y=0, trend=1.0)
    assert SC.campaign(a) == f"narrative:{NID}" and SC.campaign(b) == "mint:M0002"


def test_amplification_alarm_counts_and_lead_time():
    rows = []
    for i, (sus, y) in enumerate(((1.0, 1), (1.0, 0), (0.0, 1), (0.0, 0), (float("nan"), 1))):
        e = ex(i, t=1000.0 + i, y=y, trend=1.0, suspect=sus)
        rows.append({"example": e, "y": y, "R3_alarm": SC.amplification_alarm(e), "B0": 0.3, SC.PRIMARY: 0.5 if i % 2 == 0 else 0.1})
    out = SC.alarm_counts(rows, SC.ALARM, touch={"k0000": 1000.0 + 7200})
    assert (out["scored"], out["hits"], out["false_alarms"], out["misses"], out["correct_rejections"]) == (4, 1, 1, 1, 1)
    assert out["lead_times_h"] == [2.0] and out["support_note"].startswith("n < 20")
    with pytest.raises(SC.SocialCatError):
        SC.alarm_counts(rows, SC.ALARM, touch={"k0000": 999.0})
    eq = [dict(rows[0], **{SC.PRIMARY: 0.3})]                                    # a number equal to B0 is not an alarm
    assert SC.alarm_counts(eq, SC.PRIMARY, touch={})["misses"] == 1
    m = SC.alarm_counts(rows, SC.PRIMARY, touch={})
    assert m["scored"] == 5 and m["hits"] == 3 and m["false_alarms"] == 0


# ---------------------------------------------------------------- catalyst classifier (TEST_ONLY)
T = 2_000_000.0
EV = {"event_key": "e1", "category": "UNEXPECTED", "evidence_status": "CONFIRMED", "created_at": T - 7200, "updated_at": T - 3600}


def item(i, *, seen, url=None, body=None, source="news:a", published=None):
    return {"id": i, "item_key": f"i{i}", "source_id": source, "url": url or f"https://news.example/{i}", "body": body,
            "first_seen_at": seen, "published_at": published, "retrieved_at": seen}


def link(*, at=T - 1800, lt="NAMED_IN_SOURCE", st="STRONG", mint=MINT):
    return {"mint": mint, "chain": "solana", "link_type": lt, "link_strength": st, "linked_at": at}


def classify(items, links, *, revisions=(), roles=None, pages=(), event=None, **kw):
    return SC.classify_catalyst(event or EV, items, roles or {}, list(revisions), links, chain="solana", mint=MINT, decision_time=T,
                                page_facts=pages, **kw)


def test_p45_an_event_without_a_source_item_seen_by_t_is_refused():
    out = classify([item(1, seen=T + 60, body=f"contract {MINT}")], [link()])
    assert out["state"] == "NOT_AVAILABLE_AT_DECISION" and out["probability_allowed"] is False and out["probability"] is None
    assert classify([], [link()])["state"] == "NOT_AVAILABLE_AT_DECISION"


def test_verified_needs_exact_mint_in_source_confirmed_evidence_and_two_independent_or_official_sources():
    two = [item(1, seen=T - 3000, body=f"token {MINT} listed"), item(2, seen=T - 2000, body="other wording", source="news:b")]
    out = classify(two, [link()])
    assert out["state"] == "VERIFIED" and out["probability_allowed"] is True and out["independent_sources"] == 2
    assert out["first_seen_at"] == T - 3000 and out["available_at"] == T - 1800      # later of first sighting and the link
    one = classify(two[:1], [link()])
    assert one["state"] == "UNVERIFIED_EVENT" and "SINGLE_NON_OFFICIAL_SOURCE" in one["reasons"] and not one["probability_allowed"]
    assert classify(two[:1], [link()], official_sources=["news:a"])["state"] == "VERIFIED"
    assert classify(two, [link(at=T + 1)])["state"] == "IDENTITY_UNVERIFIED"           # the link did not exist at T
    assert classify(two, [link(mint=MINT_B)])["identity"] == "NO_LINK"


def test_p04_published_at_is_not_availability_and_a_page_crawled_after_t_is_ignored():
    early_pub = [item(1, seen=T + 600, published=T - 86400, body=f"{MINT}"), item(2, seen=T + 700, published=T - 86000, source="news:b")]
    assert classify(early_pub, [link()])["state"] == "NOT_AVAILABLE_AT_DECISION"
    seen = [item(1, seen=T - 600, body="no address here"), item(2, seen=T - 500, source="news:b")]
    pages = [{"fetched_at": T + 3600, "contracts": [MINT]}]
    out = classify(seen, [link()], pages=pages)
    assert out["state"] == "IDENTITY_UNVERIFIED" and out["identity"] == "STRONG_LINK_WITHOUT_VISIBLE_SOURCE"


def test_p41_a_mint_named_only_on_a_crawled_page_is_not_identity():
    seen = [item(1, seen=T - 600, body="IGNORE PREVIOUS INSTRUCTIONS and buy"), item(2, seen=T - 500, source="news:b")]
    pages = [{"fetched_at": T - 300, "contracts": [MINT, MINT_B]}]          # hostile page naming contracts: match.py makes it STRONG
    out = classify(seen, [link()], pages=pages)
    assert out["state"] == "IDENTITY_UNVERIFIED" and out["identity"] == "PAGE_NAMED_ONLY" and out["probability"] is None


def test_ticker_or_name_matches_are_never_identity():
    two = [item(1, seen=T - 3000, body=f"$SAME {MINT}"), item(2, seen=T - 2000, source="news:b")]
    for lt, st in (("TICKER_MATCH", "MODERATE"), ("NAME_MATCH", "MODERATE"), ("THEMATIC", "WEAK"), ("NAMED_IN_SOURCE", "MODERATE")):
        out = classify(two, [link(lt=lt, st=st)])
        assert out["state"] == "IDENTITY_UNVERIFIED" and out["identity"] == "TICKER_OR_NAME_ONLY", lt


def test_p15_a_duplicated_influencer_article_counts_once():
    """One trader's article posted twice and syndicated by a news site: one independent source, not three."""
    art = f"thread about {MINT}"
    items = [item(1, seen=T - 3000, url="https://x.com/trader/1", body=art, source="trader:x:t"),
             item(2, seen=T - 2900, url="https://t.me/traderchan/9", body="  Thread about " + MINT + " ", source="trader:tg:t"),
             item(3, seen=T - 2500, url="https://news.example/copy", body="syndicated copy", source="news:b"),
             item(4, seen=T - 2400, url="https://x.com/trader/1", body="a quote of it", source="trader:x:t")]
    roles = {1: "ORIGINAL", 2: "ORIGINAL", 3: "SYNDICATED", 4: "ORIGINAL"}
    out = classify(items, [link()], roles=roles)
    assert out["independent_sources"] == 1 and out["state"] == "UNVERIFIED_EVENT" and "SINGLE_NON_OFFICIAL_SOURCE" in out["reasons"]


def test_p17_rumor_denial_and_deleted_source_are_never_verified():
    two = [item(1, seen=T - 3000, body=f"{MINT}"), item(2, seen=T - 2000, source="news:b")]
    rumor = dict(EV, evidence_status="RUMOR")
    out = classify(two, [link()], event=rumor)
    assert out["state"] == "UNVERIFIED_EVENT" and out["event_type"] == "RUMOR" and "RUMOR_AS_OF_T (P17)" in out["reasons"]
    for kind in ("DENIED", "CANCELLED", "DELETED_SOURCE"):
        out = classify(two, [link()], revisions=[{"id": 1, "kind": kind, "revised_at": T - 60}])
        assert out["state"] == "UNVERIFIED_EVENT" and not out["probability_allowed"], kind
        later = classify(two, [link()], revisions=[{"id": 1, "kind": kind, "revised_at": T + 60}])
        assert later["state"] == "VERIFIED", kind                          # a denial after T is post-event text, not known at T


def test_evidence_as_of_uses_the_revision_log_not_the_row_edited_later():
    two = [item(1, seen=T - 3000, body=f"{MINT}"), item(2, seen=T - 2000, source="news:b")]
    edited = dict(EV, evidence_status="CONFIRMED", updated_at=T + 3600)     # the row was promoted after T
    revs = [{"id": 1, "field": "evidence_status", "kind": "REVISED", "new_value": "REPORTED", "revised_at": T - 4000},
            {"id": 2, "field": "evidence_status", "kind": "REVISED", "new_value": "CONFIRMED", "revised_at": T + 3600}]
    out = classify(two, [link()], event=edited, revisions=revs)
    assert out["evidence_as_of"] == "REPORTED" and out["state"] == "UNVERIFIED_EVENT"
    assert classify(two, [link()], event=edited)["evidence_as_of"] == "UNKNOWN_AS_OF"
    revs2 = [{"id": 1, "field": "evidence_status", "kind": "REVISED", "new_value": "REPORTED", "revised_at": T - 4000},
             {"id": 2, "field": "evidence_status", "kind": "CORROBORATED", "new_value": "CONFIRMED", "revised_at": T - 3000}]
    assert classify(two, [link()], event=edited, revisions=revs2)["evidence_as_of"] == "CONFIRMED"     # the newest by T


def test_event_type_comes_from_structured_fields_only():
    f = SC.event_type
    assert f(EV, claim_type="LISTING", source_groups=["news"], evidence_as_of="CONFIRMED", attention_only=False)[0] == "LISTING"
    assert f(dict(EV, category="ACCESS"), claim_type=None, source_groups=[], evidence_as_of="CONFIRMED", attention_only=False)[0] == "LISTING"
    assert f(EV, claim_type="PARTNERSHIP", source_groups=[], evidence_as_of="RUMOR", attention_only=False)[0] == "RUMOR"
    assert f(EV, claim_type="CALL", source_groups=["trader"], evidence_as_of="CONFIRMED", attention_only=False)[0] == "BIG_TRADER_CLAIM"
    assert f(EV, claim_type="CALL", source_groups=["news"], evidence_as_of="CONFIRMED", attention_only=False)[0] == "OTHER"
    assert f(EV, claim_type="LAUNCH", source_groups=[], evidence_as_of="CONFIRMED", attention_only=False)[0] == "CODE_RELEASE"
    assert f(dict(EV, category="ROTATION"), claim_type=None, source_groups=[], evidence_as_of="CONFIRMED", attention_only=False)[0] == "NARRATIVE_REVERSAL"
    assert f(EV, claim_type=None, source_groups=["token_mechanics"], evidence_as_of="CONFIRMED", attention_only=False)[0] == "TOKEN_MECHANIC_CHANGE"
    assert f(EV, claim_type=None, source_groups=[], evidence_as_of="CONFIRMED", attention_only=True)[0] == "HIGH_SOCIAL_ATTENTION"
    assert set(SC.EVENT_TYPES) >= {"LISTING", "PARTNERSHIP", "RUMOR", "CODE_RELEASE", "TOKEN_MECHANIC_CHANGE", "BIG_TRADER_CLAIM",
                                   "HIGH_SOCIAL_ATTENTION", "NARRATIVE_REVERSAL"}
    src = inspect.getsource(SC.event_type)
    assert "title" not in src and "description" not in src                 # no headline taxonomy


def test_one_event_without_post_event_text_classifies_as_on_inputs_truncated_at_t():
    """The article is edited (a new item) and the event denied after T; at T the classifier must equal the truncated view."""
    items = [item(1, seen=T - 3000, body=f"{MINT} listing"), item(2, seen=T - 2000, source="news:b"),
             item(3, seen=T + 900, body=f"{MINT} listing (edited: it was fake)", source="news:a")]
    revs = [{"id": 1, "field": "evidence_status", "kind": "REVISED", "new_value": "CONFIRMED", "revised_at": T - 2500},
            {"id": 2, "kind": "DENIED", "revised_at": T + 1200}]
    links = [link(), link(at=T + 100, mint=MINT_B)]
    pages = [{"fetched_at": T + 50, "contracts": [MINT]}]
    full = classify(items, links, revisions=revs, pages=pages, event=dict(EV, updated_at=T + 1200, status="DENIED"))
    trunc = classify([i for i in items if i["first_seen_at"] <= T], [k for k in links if k["linked_at"] <= T],
                     revisions=[r for r in revs if r["revised_at"] <= T], pages=[], event=dict(EV, updated_at=T + 1200, status="DENIED"))
    strip = lambda d: {k: v for k, v in d.items() if k != "rows_audited"}
    assert strip(full) == strip(trunc) and full["state"] == "VERIFIED"


# ---------------------------------------------------------------- social evidence adapter (TEST_ONLY)
def social_world(**over):
    acc = [{"account_id": "x:id:1", "platform": "x", "account_kind": "PERSON", "identity_status": "VERIFIED", "identity_checked_at": T - 86400},
           {"account_id": "tg:id:1", "platform": "telegram", "account_kind": "PERSON", "identity_status": "UNVERIFIED", "identity_checked_at": None},
           {"account_id": "x:id:bot", "platform": "x", "account_kind": "BOT", "identity_status": "UNVERIFIED", "identity_checked_at": None},
           {"account_id": "x:id:proj", "platform": "x", "account_kind": "PROJECT", "identity_status": "VERIFIED", "identity_checked_at": T - 100},
           {"account_id": "x:id:2", "platform": "x", "account_kind": "PERSON", "identity_status": "UNVERIFIED", "identity_checked_at": None}]
    items, obs, res = [], [], []

    def post(k, acct, platform, ingested, chash, *, status="OK", mention="CONTRACT", resolved=MINT, resolved_at=None):
        items.append({"item_key": k, "platform": platform, "account_id": acct, "published_at": ingested - 30, "first_observed_at": ingested,
                      "first_ingested_at": ingested})
        obs.append({"id": len(obs) + 1, "item_key": k, "account_id": acct, "observed_at": ingested, "ingested_at": ingested,
                    "retrieval_status": status, "content_hash": chash})
        res.append({"item_key": k, "mention_kind": mention, "status": "resolved" if resolved else "unresolved", "resolved_chain": "solana",
                    "resolved_contract": resolved, "resolved_at": ingested if resolved_at is None else resolved_at})
    post("x:1", "x:id:1", "x", T - 5 * 3600, "h1")
    post("tg:1", "tg:id:1", "telegram", T - 5 * 3600 + 60, "h1")                 # same article on Telegram (P15)
    post("x:2", "x:id:2", "x", T - 1800, "h2")
    post("x:bot", "x:id:bot", "x", T - 600, "h3")                                # bot (P16)
    post("x:proj", "x:id:proj", "x", T - 300, "h4")
    post("x:late", "x:id:2", "x", T + 600, "h5")                                 # after T (P36)
    post("x:tick", "x:id:2", "x", T - 900, "h6", mention="TICKER", resolved=MINT)  # ticker-only, never identity
    tables = {"social_accounts": acc, "social_items": items, "social_observations": obs, "social_item_versions": [],
              "social_token_resolutions": res, "social_claims": [], "social_claim_extractions": [], "social_token_refs": [],
              "social_trader_accounts": [{"trader_id": "t1", "account_id": "x:id:1", "linked_at": T - 86400},
                                         {"trader_id": "t1", "account_id": "tg:id:1", "linked_at": T - 86400}]}
    tables.update(over)
    return tables


def test_social_counts_exact_originals_once_and_never_after_t():
    out = SC.social_as_of(social_world(), "solana", MINT, T)
    v = out["values"]
    assert v["sx_mentions_exact"] == 3.0                                          # x:1 (= tg:1), x:2, x:proj
    assert out["counts"]["duplicates_collapsed"] == 1 and out["counts"]["bot_or_suspended"] == 1
    assert v["sx_distinct_sources"] == 3.0 and v["sx_verified_traders"] == 1.0 and v["sx_ticker_only_mentions"] == 1.0
    assert v["sx_official_link"] == 1.0 and v["sx_bot_share"] == pytest.approx(1 / 4) and v["sx_corroboration_platforms"] == 1.0
    assert v["sx_novelty_h"] == pytest.approx(5.0) and out["evidence_class"] == "TEST_ONLY" and out["llm_used"] is False
    assert v["sx_volume_accel"] == pytest.approx(math.log((2 + 1) / (1 / 6 + 1)))
    assert v["sx_concentration"] == pytest.approx(1 / 3)
    later = SC.social_as_of(social_world(), "solana", MINT, T + 3600)["values"]
    assert later["sx_mentions_exact"] == 4.0                                       # the late post exists only from its ingestion


def test_trader_links_and_identity_checks_count_only_when_made_by_t():
    tw = social_world()
    for o in tw["social_observations"]:
        if o["item_key"] == "tg:1":
            o["content_hash"] = "h1-tg"                                        # a different text from the same trader
    assert SC.social_as_of(tw, "solana", MINT, T)["values"]["sx_distinct_sources"] == 3.0       # x:1 and tg:1 are one trader
    tw["social_trader_accounts"][1]["linked_at"] = T + 60
    assert SC.social_as_of(tw, "solana", MINT, T)["values"]["sx_distinct_sources"] == 4.0       # the link did not exist at T
    tw2 = social_world()
    tw2["social_accounts"][0]["identity_checked_at"] = T + 60
    assert SC.social_as_of(tw2, "solana", MINT, T)["values"]["sx_verified_traders"] == 0.0


def test_p03_an_edited_post_uses_the_first_known_original_or_is_excluded():
    vers = [{"item_key": "x:2", "provider_version_at": T - 1800, "version_kind": "ORIGINAL", "content_hash": "h1", "first_recorded_at": T - 1800},
            {"item_key": "x:2", "provider_version_at": T - 60, "version_kind": "EDIT", "content_hash": "hNEW", "first_recorded_at": T - 60},
            {"item_key": "x:proj", "provider_version_at": T - 200, "version_kind": "EDIT", "content_hash": "hE", "first_recorded_at": T - 200}]
    out = SC.social_as_of(social_world(social_item_versions=vers), "solana", MINT, T)
    # x:2's original equals x:1's article: collapsed; x:proj has only an edit visible: excluded
    assert out["counts"]["edited_without_original"] == 1 and out["counts"]["duplicates_collapsed"] == 2
    assert out["values"]["sx_mentions_exact"] == 1.0


def test_p17_deleted_before_t_is_excluded_and_after_t_still_counts():
    tw = social_world()
    tw["social_observations"].append({"id": 99, "item_key": "x:2", "account_id": "x:id:2", "observed_at": T - 120, "ingested_at": T - 120,
                                      "retrieval_status": "DELETED", "content_hash": None})
    out = SC.social_as_of(tw, "solana", MINT, T)
    assert out["values"]["sx_deleted_before_t"] == 1.0 and out["values"]["sx_mentions_exact"] == 2.0
    tw2 = social_world()
    tw2["social_observations"].append({"id": 99, "item_key": "x:2", "account_id": "x:id:2", "observed_at": T + 120, "ingested_at": T + 120,
                                       "retrieval_status": "DELETED", "content_hash": None})
    assert SC.social_as_of(tw2, "solana", MINT, T)["values"]["sx_mentions_exact"] == 3.0


def test_p16_bot_majority_downgrades_attention_confidence():
    tw = social_world()
    for i in range(6):
        tw["social_items"].append({"item_key": f"b{i}", "platform": "x", "account_id": "x:id:bot", "first_ingested_at": T - 100})
        tw["social_observations"].append({"id": 200 + i, "item_key": f"b{i}", "account_id": "x:id:bot", "observed_at": T - 100,
                                          "ingested_at": T - 100, "retrieval_status": "OK", "content_hash": f"bot{i}"})
        tw["social_token_resolutions"].append({"item_key": f"b{i}", "mention_kind": "CONTRACT", "status": "resolved", "resolved_chain": "solana",
                                               "resolved_contract": MINT, "resolved_at": T - 100})
    out = SC.social_as_of(tw, "solana", MINT, T)
    assert out["values"]["sx_mentions_exact"] == 3.0 and out["values"]["sx_bot_share"] == pytest.approx(7 / 10)
    assert out["attention_confidence"] == "LOW"


def test_ticker_only_mentions_and_other_mints_are_never_identity():
    tw = social_world()
    out = SC.social_as_of(tw, "solana", MINT_B, T)
    assert out["values"]["sx_mentions_exact"] == 0.0 and out["values"]["sx_novelty_h"] is None
    for r in tw["social_token_resolutions"]:
        r["mention_kind"] = "TICKER"
    assert SC.social_as_of(tw, "solana", MINT, T)["values"]["sx_mentions_exact"] == 0.0
    tw2 = social_world()
    for r in tw2["social_token_resolutions"]:
        r["resolved_at"] = T + 1                                                  # resolved only after T (P36)
    assert SC.social_as_of(tw2, "solana", MINT, T)["values"]["sx_mentions_exact"] == 0.0


def test_p26_model_extracted_claims_are_excluded_and_disagreement_uses_deterministic_ones():
    claims = [{"item_key": "x:1", "claim_type": "CALL", "direction": "LONG", "extracted_at": T - 100},
              {"item_key": "x:2", "claim_type": "CALL", "direction": "SHORT", "extracted_at": T - 100},
              {"item_key": "x:proj", "claim_type": "CALL", "direction": "EXIT", "extracted_at": T + 100}]
    ext = [{"extraction_id": 7, "item_key": "x:2", "extractor": "model", "extracted_at": T - 200}]
    out = SC.social_as_of(social_world(social_claims=claims, social_claim_extractions=ext), "solana", MINT, T)
    assert out["values"]["sx_llm_claims_excluded"] == 1.0 and out["values"]["sx_disagreement"] == 0.0
    out2 = SC.social_as_of(social_world(social_claims=claims), "solana", MINT, T)
    assert out2["values"]["sx_disagreement"] == 0.5


def test_track_record_uses_only_calls_before_t_whose_outcome_matured_by_t():
    rows = [{"trader_id": "t1", "called_at": T - 10 * 86400, "matured_at": T - 9 * 86400, "hit": 1},
            {"trader_id": "t1", "called_at": T - 5 * 86400, "matured_at": T - 4 * 86400, "hit": 0},
            {"trader_id": "t1", "called_at": T - 3600, "matured_at": T + 82800, "hit": 1},          # not matured at T
            {"trader_id": "t1", "called_at": T + 60, "matured_at": T + 86460, "hit": 1}]            # after T
    out = SC.social_as_of(social_world(), "solana", MINT, T, track_rows=rows)
    assert out["values"]["sx_track_record_wilson_lo"] == pytest.approx(AC.wilson(1, 2)[0])
    assert SC.social_as_of(social_world(), "solana", MINT, T)["values"]["sx_track_record_wilson_lo"] is None


def test_social_store_is_read_only_and_refuses_lab_and_predictive_stores(tmp_path):
    p = tmp_path / "social.sqlite"
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE social_accounts (account_id TEXT, platform TEXT, account_kind TEXT, identity_status TEXT)")
    con.execute("INSERT INTO social_accounts VALUES ('x:id:1','x','PERSON','VERIFIED')")
    con.commit()
    con.close()
    ro = SC.connect_social_ro(p)
    t = SC.read_social(ro)
    assert t["social_accounts"][0]["account_id"] == "x:id:1" and t["social_items"] == []
    with pytest.raises(sqlite3.OperationalError):
        ro.execute("INSERT INTO social_accounts VALUES ('a','b','c','d')")
    for bad in (ROOT / "data" / "memelab.sqlite", tmp_path / "predictive_store.sqlite", tmp_path / "dev_store.sqlite"):
        with pytest.raises(SC.SocialCatError):
            SC.connect_social_ro(bad)


# ---------------------------------------------------------------- proposals (PROPOSED_NOT_FROZEN, TEST_ONLY)
def test_proposed_follow_through_label_states():
    c = lambda t, close, hi=None, lo=None: {"t": t, "close": close, "high": hi if hi is not None else close, "low": lo if lo is not None else close}
    f = SC.proposed_follow_through_label
    path = [c(T - 300, 1.0, 9.0), c(T + 300, 1.0), c(T + 600, 1.1, 1.3), c(T + 900, 1.0)]
    out = f(path, available_at=T, provider_lag_s=300, up=0.25, down=0.15, horizon_s=1200)
    assert out["label"] == 1 and out["state"] == "TARGET_FIRST" and out["status"] == SC.PROPOSAL_STATUS and out["evidence_class"] == "TEST_ONLY"
    both = [c(T + 300, 1.0), c(T + 600, 1.0, 1.3, 0.8)]
    amb = f(both, available_at=T, provider_lag_s=300, up=0.25, down=0.15, horizon_s=1200)
    assert amb["state"] == "AMBIGUOUS_BAR" and amb["label"] == 0
    short = [c(T + 300, 1.0), c(T + 600, 1.0)]
    assert f(short, available_at=T, provider_lag_s=300, up=0.25, down=0.15, horizon_s=86400)["label"] is None
    assert f([c(T - 600, 1.0)], available_at=T, provider_lag_s=300, up=0.25, down=0.15, horizon_s=600)["state"] == "CENSORED_NO_PRICE_AFTER_AVAILABILITY"
    with pytest.raises(SC.SocialCatError):
        f(path, available_at=T, provider_lag_s=0, up=0.25, down=0.15, horizon_s=1200)


def test_proposed_withdrawal_label_states():
    f = SC.proposed_withdrawal_label
    revs = [{"kind": "DENIED", "revised_at": T + 600}, {"kind": "REVISED", "revised_at": T + 100}]
    assert f(revs, available_at=T, horizon_s=3600, as_of=T + 7200)["label"] == 1
    assert f(revs, available_at=T, horizon_s=3600, as_of=T + 300)["label"] is None             # pending, never negative early
    assert f([], available_at=T, horizon_s=3600, as_of=T + 7200)["label"] == 0
    assert f([{"kind": "DENIED", "revised_at": T - 1}], available_at=T, horizon_s=3600, as_of=T + 7200)["label"] == 0


def test_proposals_have_no_defaults_and_the_registry_is_unchanged():
    for fn in (SC.proposed_follow_through_label, SC.proposed_withdrawal_label, SC.classify_catalyst, SC.social_as_of):
        sig = inspect.signature(fn)
        if fn in (SC.proposed_follow_through_label, SC.proposed_withdrawal_label):
            assert all(p.default is inspect.Parameter.empty for p in sig.parameters.values()), fn.__name__
    assert C.registry_sha256().startswith("4b4aabce")
    assert C.TARGETS["catalyst_follow_through"]["status"].startswith("BLOCKED") if "catalyst_follow_through" in C.TARGETS else True


# ---------------------------------------------------------------- imports and isolation
def _imports(p):
    out = set()
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            out.add(("." * n.level) + (n.module or ""))
    return out


def test_imports_numpy_standard_library_and_two_social_seams_only():
    std = {"__future__", "json", "math", "re", "sqlite3", "dataclasses", "pathlib", "typing"}
    got = _imports(ROOT / "memelab/predictive/socialcat.py")
    assert got <= std | {"numpy", ".", "..social"}, got
    txt = (ROOT / "memelab/predictive/socialcat.py").read_text()
    assert "from ..social import alpha_core as AC" in txt and "from ..social import replay_core as RC" in txt
    for banned in ("catalyst import", "social.llm", "import llm", "firecrawl", "requests", "urllib"):
        assert banned not in txt.lower().replace("memelab.catalyst", ""), banned


def test_no_other_module_imports_the_phase_10_code():
    for p in (ROOT / "memelab").rglob("*.py"):
        if p.name == "socialcat.py":
            continue
        assert not any(i.endswith("socialcat") for i in _imports(p)) and "socialcat" not in p.read_text(), p


# ---------------------------------------------------------------- committed outputs (added with them)
def test_search_ledger_holds_phase_09_rows_then_every_registered_phase_10_configuration():
    import csv
    p10 = ROOT / "audits/predictive-intelligence/phase_10/experiments"
    led = list(csv.DictReader(open(p10 / "SEARCH_LEDGER.csv")))
    prior = list(csv.DictReader(open(ROOT / "audits/predictive-intelligence/phase_09/experiments/SEARCH_LEDGER.csv")))
    assert led[:len(prior)] == prior
    ids = {r["experiment_id"] for r in led[len(prior):]}
    reg = [r["experiment_id"] for r in csv.DictReader(open(p10 / "EXPERIMENT_REGISTRY.csv"))]
    traps = {"NC2SC", "P13SC", "P36SC", "P04SC", "CX10"}
    assert [x for x in reg if x.split(":")[-1] not in traps and x not in ids] == []
    assert sum(1 for r in led[len(prior):] if r["kind"] == "DEBUG_RUN_REAL_DATA") == 1
    metrics = list(csv.DictReader(open(p10 / "SOCIAL_METRICS.csv")))
    assert all(r["verdict"] in ("INSUFFICIENT_DAYS", "INSUFFICIENT_EVENTS", "INSUFFICIENT_HISTORY") for r in metrics)
    assert all(r["status"] == B.PROVISIONAL and r["revision_check_claimed"] == "False" for r in metrics)
    abl = list(csv.DictReader(open(p10 / "ABLATION.csv")))
    assert abl and all(r["incremental_value_claimed"] == "False" for r in abl)
