# PHASE 04: adoption bake-off

State: PASS. Date 2026-10-23. Entry gate: Phase 03 PASS (RANKING.csv totals recomputed from cards: 25/25 match).

## Commands and exits

| Command | Exit | Result |
|---|---|---|
| `python3 dataset.py` | 0 | dataset sha256 f287bf0f59d6a47048cdad99a5e06efd23a8ecf9001cfe5b4df967ec9619bf43 |
| `python3 oracle_hand.py` | 0 | oracle_expected.json |
| `python3 run_proto.py` | 0 | result_proto.json |
| `<venv backtesting.py>/python run_backtestingpy.py` | 0 | result_backtestingpy.json |
| `<venv vectorbt>/python run_vectorbt.py` | 0 | result_vectorbt.json |
| `python3 compare.py` | 0 | 16/16 checks pass (compare_output.txt) |
| speed scripts (3) | 0 | result_speed.jsonl |
| `python3 adapter_proto.py` | 0 | result_adapter.json (real fixture through the unchanged pipeline) |

Hashes: bakeoff/hashes.txt.

## Gate

Strategy and ledger smoke scenarios validated against an independent oracle; alternatives rejected with evidence (ADOPTION_DECISIONS.md); legal status safe (no copyleft or unlicensed code copied, no new runtime dependency); installation footprint and Windows/Linux paths recorded; live-trading features rejected.

## Negative review

Plausible claim: "vectorbt run with default settings gives the same entry as a next-bar engine." compare.py check "vectorbt DEFAULT fills on the signal bar close" catches it: entry 1.10 at bar 20 instead of 1.11 at bar 21, and the gap stop booked at 0.93 close instead of the 0.95 open, a $10.34 difference on $1,000. Second: "different P&L between the prototype and backtesting.py means one engine is wrong." Reconciled exactly by formula (integer units and fee basis), so the disagreement is convention, not a bug.

## Limitations

The dataset is synthetic. Timing numbers are from this workspace only. CLMM/DLMM not prototyped (no historical state source).

NEXT ELIGIBLE PHASE: 05.
