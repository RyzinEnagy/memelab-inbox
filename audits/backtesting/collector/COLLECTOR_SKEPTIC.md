# Skeptic review: forward depth collector (D-BT-034)

Reviewer: independent skeptic, 2026-10-25. Branch `work/backtesting-collector` (50565ad, 53008cb on 054a619), reviewed in my own clone `/home/claude/pi_orchestration/skeptic_collector`. Nothing was written in /home/claude/bt-wt or the inbox. Scratch tests and the live run are in `/tmp/claude-0/-home-claude/6c3ea1ef-d097-5873-a280-98af7bc5c45c/scratchpad/sk/`.

Live calls made: GitHub 1 shallow fetch, GeckoTerminal 3 (one was a retry after a failed call), Jupiter 6. Total 10. Docs read with WebFetch: developers.jup.ag rate-limits and plans pages.

## Verdict

The point-in-time core is sound and the evidence is honest, but the step can crash on a routine rate limit, and a crash now takes the whole hourly run (refresh and track included) down with it. Fix M1 before deployment. M2 to M4 should be fixed or written into D-BT-034 as known limits before any predictive label reads these rows.

## MATERIAL

### M1. A 429, 5xx or timeout on the last budgeted call crashes collect

`gecko.get_json` counts a retry as a call and raises `BudgetExhausted` when the retry would pass the cap. `depth.collect` does not catch it. So any failed first attempt made when `calls == max_calls - 1` ends the program with a traceback (the message says "GeckoTerminal budget" even for Jupiter).

Reproduced offline (scratchpad `test_probe429.py`):
- Jupiter cap 4, the 4th call returns 429: `BudgetExhausted: GeckoTerminal budget of 4 calls used`.
- GeckoTerminal: one 200, then network errors, default cap 6: the third pool task starts at 5 calls, fails, its retry raises.

Why it matters: on a normal day the Jupiter cap or deadline is always reached (see M3), so the last call is always made, and a 429 on it (keyless 30 per minute, shared with anything else on the same IP) becomes a crashed run. The script prints FAILED, and the scheduled-task prompt then stops before `track` and `save`. The hour's refresh bars, collect rows and track outcomes are thrown away (setup deletes the work copy next hour), and a push notification fires. Before this change only refresh and track could fail. RUNBOOK says "one retry on 429" and "Only a program error makes the step print FAILED"; both are false at the cap edge. My live run hit one GeckoTerminal retry in 3 calls. No test or mutation covers 429 or retries.

Fix: catch `BudgetExhausted` in `depth._get` and record the row as BUDGET_EXHAUSTED (or skip the retry when no call is left); add a test with a 429 on the last call.

### M2. GeckoTerminal "6 a minute shared with refresh" is not met

Collect keeps its own calls 10 s apart and waits 10 s after its own start. Refresh, which runs just before, still makes up to 12 calls 3 s apart. Any 60 s window around the hand-off can hold 12 refresh calls plus collect's first one or two, about 14 a minute, more than twice the rule. COLLECTOR.md lists this under Limits, but D-BT-034 and RUNBOOK ("the first one 10 s after the step starts (refresh called GeckoTerminal just before)") read as if the shared budget were kept. Simple fix: refresh at 10 s spacing (12 calls, about 120 s, still under 175 s), or keep the rule written as "collect only".

### M3. The first snapshot is not "at the decision", and the gap is not random

The lab exports once a day: e245d91 2026-10-25 10:10Z, efdaee9 10:11Z the day before, 98338a8 10:20Z the day before that (from my fetch). So about 16 Solana decisions arrive together, and all of them want 3 quotes in the first run. Simulation with 16 Solana pools, 2 BSC and 1 Base (scratchpad `sim_cap.py`): 37 Jupiter calls before the 100 s deadline, 13 of 16 pools quoted, deadline hit, 11 quotes not attempted, every hour. The 3 pools that miss are the last 3 in export order (every never-quoted pool sorts at -1 and ties keep export order). Every day, the same positions get their first quote up to about 2 h after the decision. On top of that, the first snapshot of any decision is at the next hourly run, so the lag is up to about an hour even when nothing is capped.

RUNBOOK says "at the decision and every hour to 24 h". The lag is recorded on every row, so nothing is hidden, but the exit-adjusted target needs a quote "at entry" (TARGET_REGISTRY), and PI-D-021 is all about selection that depends on row position. Fix: sort ties by a hash of the row, give the first run after an export more Jupiter calls (the keyless 30 per minute allows about 45 in 100 s at 2.2 s), and change the wording to "first run after the export".

### M4. Counterexample: a stale pool price reads as a large exit haircut, and nothing catches it

The token amount is size divided by the export pool's GeckoTerminal price. Jupiter routes the sale through any pool at the market price. If the export's pool is thin or stale (an old graduated pool, a dislocated secondary pool) and its last price is twice the market, the "$100" sale is really $50 of tokens.

Scratchpad `test_cx.py` doubles the A pool's `base_token_price_usd` and has Jupiter answer at the market. Result: all three quotes are state OK, `proceeds_ratio` 0.500, 0.498, 0.495 with `priceImpactPct` 0.0015 to 0.011. A labeler using out_usd / size_usd sees a 50% haircut that is really a pricing error. The identity check passes (inAmount is echoed exactly). No test, mutation or state flags it. What would catch it: the stored `swap_usd_value` (Jupiter's own USD value of the input, here 49.96 for size 100). In my live run it was within 0.1% of size, so it does not happen today on these two mints. Fix: a state or flag when swap_usd_value / size is outside, say, 0.9 to 1.1, and a test.

## MINOR

1. Step wall time: the git fetch has `timeout 60` and the program `timeout 160`, so the step can run about 220 s, beyond the 175 s call limit. The script comment says "about 110 s at most", and the test only checks for `$T 160`. It fails safe (no save) but loses the hour. Normal case is fine: my live fetch took 2 s and a capped run 44 s; the simulated full run 100.6 s plus a retry tail of up to about 26 s.
2. When a pool read is not OK (SOURCE_BLOCKED, NOT_IN_RESPONSE, IDENTITY_MISMATCH), its quotes are skipped with no QUOTE row and no `not_attempted` count. One GeckoTerminal 429 on Solana costs the hour's quotes even when Jupiter is up. The POOL row shows why, so it can be worked out, but the quote record has holes.
3. Test gaps. Of 14 extra mutations of depth.py (scratchpad `my_mut.json`), 4 were caught (sell turned into a buy, size times price, 9-decimal USDC, ceil) and 10 survived: price from the base side always, decimals from the base token always (all fixtures have the mint as base; I checked by flipping a fixture that the code itself handles a quote-side mint correctly), Solana identity ignoring case, a future-dated export accepted, a failed pool read dropped, ExactOut instead of ExactIn, decision_id pointing at the oldest decision, NOT_IN_RESPONSE turned into OK, slippage left out of the URL, route left out of the values. The branch's own 18 mutations were all caught.
4. A decision whose export names no pool and whose vendor lookup keeps failing is never recorded and is gone after 24 h; a NO_POOL decision is never looked up again. The VENDOR_TOP_POOL choice keeps no request URL or raw hash on the decision row (the smoke has 10 raw bodies, 9 referenced by rows; the tokens/multi body is the orphan).
5. A run repeated in the same hour adds a second set of snapshot rows (content_hash includes run_id) and 6 more GeckoTerminal calls. `status` counts distinct hours, so it is harmless, but the predictive adapter must choose one row per hour.
6. Sales are sized in USD at each hour's price, not as the token quantity bought at the decision. Proceeds of the held position need interpolation between 100, 500 and 2,000 USD. Nothing is frozen yet (PI-D-044); a note for the adapter.
7. `float(row["created_at"])` and `row["mint"]`: one ISO-string timestamp or one malformed row makes the whole export EXPORTS_UNREADABLE for every decision (labstate uses `utc_ts`).
8. The intermediate response that caused a retry is not kept; only the final one is.
9. `release_audit.py --history` on 53008cb: exit 0, "Needs action: no", history clean (3,145 blobs). The line it flags for this branch is `audits/backtesting/collector/SKEPTIC_PACKET.md` line 16, rule `exec:seed phrase`: the hard-rules sentence, waved through by the broad rule `^audits/backtesting/.*\.md$` with any `exec:` pattern (also `docs/backtesting/RUNBOOK.md` line 140, the prompt text). It does not matter, but that path rule would also pass real signing code pasted into an audit note. The committed c01_release_audit.log was made without `--history` (no history section) though its body says "Generated by ... --history"; that heading is a fixed string in the tool.
10. The suite leaves `data/reports/20261025_1402_BRETT_0x532f.md` behind, as the packet says.

## Checked and holding

- Decision time is the committer time (`%ct`) of the first export holding the exact row; the oldest export read is the baseline; rows first seen more than 24 h ago are marked seen and skipped. The shallow boundary commit serves as the baseline, which is correct.
- captured_at is taken after `http_get` returns. Raw bodies hash to raw_sha256: all smoke files and all 8 bodies of my live run.
- Live run (14:08Z, caps 3 and 6): 19 decisions, 16 Solana pools OK, 6 quotes OK. inAmount equals the stored raw amount on all 6 (for example 41,635,112,931 for $100 of 7M3g...), swapUsdValue within 0.1% of size, slippageBps 300 and route labels stored, lag 14,322 s (the export was 4 h old).
- The only Jupiter URL is a GET to `/swap/v1/quote` with ExactIn, mint to USDC. No swap, sign or key code in the diff; the audit's trade section is empty.
- Jupiter keyless: 0.5 requests a second (30 a minute, 60 s sliding window); "great for AI agent or test use cases", with a key recommended for production apps used by people. 2.5 s spacing is 24 a minute. No deprecation of `/swap/v1/quote` on the pages I read.
- Identity: chain plus exact mint plus pool; Solana compared exactly, EVM without case; a pool that does not hold the mint gives IDENTITY_MISMATCH and no quote.
- Migration 2 is additive; the v1 checksum is unchanged; rollback to 1 drops only the two new tables; code at 054a619 ignores version 2. A failed collect cannot touch the stored database (work copy, save only after all steps).
- The revised prompt keeps every rule of the four-step prompt at 054a619.
- Full suite in my clone: 1,043 passed with the known test deselected; that test fails alone as expected.
