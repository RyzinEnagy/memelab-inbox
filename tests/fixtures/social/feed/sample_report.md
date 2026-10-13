# Phase 14 sample: social intelligence feed on an invented fixture

FIXTURE DEMO: invented accounts, tokens, posts and times. This is not live data and not a current conversation.

Reproduce: `python -m memelab social feed-demo --fixture tests/fixtures/social/feed/demo_day.json`

The fixture is written into a throwaway SQLite store through the real store functions, snapshotted by the real narrative engine and read back by the same read path the lab database uses. Section headings below are shifted one level down.

## View 1: morning brief

## Morning brief: social narratives, last 24 hours

FIXTURE DEMO: invented accounts, tokens, posts and times. This is not live data and not a current conversation.

As of 2026-10-13 08:00 EDT (12:00 UTC). Window: 2026-10-12 08:00 EDT (12:00 UTC) to 2026-10-13 08:00 EDT (12:00 UTC) (24 h).
Data: narrative snapshot run 2 (2026-10-13 UTC), cutoff 2026-10-13 08:00 EDT (12:00 UTC), 0.0 h old, FRESH.
Coverage: telegram COVERED 1; x COVERED 1.
Not clustered: 3 token not resolved to a contract.
Model: not used (status on this machine: not checked in the fixture demo). The feed is built from stored structure only.

### High priority

#### GOODCAT on solana (B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY)

- Priority: HIGH (HEURISTIC, orders this report only): 3 independent sources, fresh.
- What happened: 6 post(s) about the token GOODCAT on solana (B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY) from 5 account(s): 3 independent source(s), 2 repeat(s) (reposts, forwards, quotes that repeat) and 0 reply or copy item(s). Claim types among originals: bearish 1, bullish 1, catalyst 1, volume 1.
- First observed 2026-10-12 11:00 EDT (15:00 UTC); first published 2026-10-12 11:00 EDT (15:00 UTC); last observed 2026-10-13 05:00 EDT (09:00 UTC).
- Who said it: [fx\_alpha (x)](<https://example.invalid/x/g1>) (independent original, trader fx\_trader\_one, 2026-10-13 03:00 EDT (07:00 UTC), stance positive); [fx\_bravo (x)](<https://example.invalid/x/g2>) (independent original, 2026-10-13 03:40 EDT (07:40 UTC), stance positive); [fx\_charlie\_channel (telegram)](<https://t.me/fx_charlie_channel/101>) (independent original, 2026-10-13 04:15 EDT (08:15 UTC), stance positive); [fx\_amp\_one (x)](<https://example.invalid/x/g4>) (amplifier, 2026-10-13 04:30 EDT (08:30 UTC), stance positive); [fx\_amp\_two (x)](<https://example.invalid/x/g5>) (amplifier, 2026-10-13 05:00 EDT (09:00 UTC), stance positive).
- Independence vs repetition: 3 independent of 5 account(s); 2 repeat(s) counted once with their original; 0 reply or copy item(s); 0 repeat(s) of an unseen original.
- Why it matters (HEURISTIC): activity rose against the previous window; the number of independent sources changed; the balance of opinion shifted; several unrelated sources found it on their own, which is the earliest public signal this lab can see.
- Corroborated: That the token is being discussed: 3 independent sources (INFERENCE). What they claim about it is not corroborated by this.
- Speculation: 3 of 4 original claim(s) are opinion, prediction or question. 1 claim(s) state something as fact; 1 of them are unverified text claims (the lab has not checked them).
- Reasons to doubt: No specific doubt recorded beyond the general limits in the footer.
- Liquidity and exit: liquidity reported: 180,000 USD per fixture\_provider at 2026-10-13 07:30 EDT (11:30 UTC) (FACT). Reported pool liquidity is not exit depth; a sell quote at your size is the real test.
- Next step: Run the existing structural checks on solana:B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY (scout or analyze) before reading anything into the attention. Provenance: `python -m memelab social narrative-why --run 2 --cluster ca:solana:B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY`.
- Freshness and coverage: FRESH, newest observation 3.0 h before as of, confidence MODERATE; coverage telegram COVERED 1; x COVERED 1.
- Provenance: narrative run 2, cluster ca:solana:B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY, claims 3, 5, 7, 9, 10, 11, market facts 1.

#### HYPEDOG on solana (bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ)

- Priority: HIGH (HEURISTIC, orders this report only): a chronology risk flag rests on a linked or self-claimed wallet.
- What happened: 14 post(s) about the token HYPEDOG on solana (bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ) from 14 account(s): 2 independent source(s), 12 repeat(s) (reposts, forwards, quotes that repeat) and 0 reply or copy item(s). Claim types among originals: promotion 1, risk 1.
- First observed 2026-10-13 05:30 EDT (09:30 UTC); first published 2026-10-13 05:30 EDT (09:30 UTC); last observed 2026-10-13 06:10 EDT (10:10 UTC).
- Who said it: [fx\_delta (x)](<https://example.invalid/x/h1>) (independent original, 2026-10-13 05:30 EDT (09:30 UTC), stance positive); [fx\_echo (x)](<https://example.invalid/x/h2>) (independent original, 2026-10-13 06:10 EDT (10:10 UTC), stance negative); [fx\_burst\_00 (x)](<https://example.invalid/x/hr0>) (amplifier, 2026-10-13 05:32 EDT (09:32 UTC), stance positive); [fx\_burst\_01 (x)](<https://example.invalid/x/hr1>) (amplifier, 2026-10-13 05:32 EDT (09:32 UTC), stance positive); and 10 more repeat account(s).
- Independence vs repetition: 2 independent of 14 account(s); 12 repeat(s) counted once with their original; 0 reply or copy item(s); 0 repeat(s) of an unseen original.
- Why it matters (HEURISTIC): new in this snapshot; several unrelated sources found it on their own, which is the earliest public signal this lab can see; a timeline flag suggests trading by a linked or self-claimed wallet around the posts; the pattern of repetition may be promotion rather than discovery.
- Corroborated: That the token is being discussed: 2 independent sources (INFERENCE). What they claim about it is not corroborated by this.
- Speculation: 1 of 2 original claim(s) are opinion, prediction or question. 1 claim(s) state something as fact; 1 of them are unverified text claims (the lab has not checked them).
- Reasons to doubt: Sources disagree (negative 1, positive 1); not resolved here. many accounts amplified it inside a short burst (coordination hypothesis, HEURISTIC, not proven). Chronology risk SALE\_DURING\_PROMOTION (HEURISTIC, not proven, wallet CLAIMED, rule chrono.sale\_during\_promotion.v1, run 1).
- Liquidity and exit: liquidity reported: 42,000 USD per fixture\_provider at 2026-10-13 07:30 EDT (11:30 UTC) (FACT). No sell route found by fixture\_provider at 2026-10-13 07:35 EDT (11:35 UTC) (FACT). Treat as not exitable until a later check shows a route.
- Next step: Run the existing structural checks on solana:bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ (scout or analyze) before reading anything into the attention. Provenance: `python -m memelab social narrative-why --run 2 --cluster ca:solana:bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ`. Review the chronology: `python -m memelab social chrono flags --token solana:bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ`.
- Freshness and coverage: FRESH, newest observation 1.8 h before as of, confidence MODERATE; coverage x COVERED 1.
- Provenance: narrative run 2, cluster ca:solana:bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ, claims 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, chronology runs 1, market facts 2, 3.

#### theme ai\_agent

- Priority: HIGH (HEURISTIC, orders this report only): 2 independent sources, fresh.
- What happened: 2 post(s) about the theme ai\_agent from 2 account(s): 2 independent source(s), 0 repeat(s) (reposts, forwards, quotes that repeat) and 0 reply or copy item(s). Claim types among originals: bullish 1, launch 1.
- First observed 2026-10-13 03:00 EDT (07:00 UTC); first published 2026-10-13 03:00 EDT (07:00 UTC); last observed 2026-10-13 06:30 EDT (10:30 UTC).
- Who said it: [fx\_alpha (x)](<https://example.invalid/x/g1>) (independent original, trader fx\_trader\_one, 2026-10-13 03:00 EDT (07:00 UTC), stance positive); [fx\_foxtrot\_channel (telegram)](<https://t.me/fx_foxtrot_channel/7>) (independent original, 2026-10-13 06:30 EDT (10:30 UTC), stance positive).
- Independence vs repetition: 2 independent of 2 account(s); 0 repeat(s) counted once with their original; 0 reply or copy item(s); 0 repeat(s) of an unseen original.
- Why it matters (HEURISTIC): new in this snapshot; several unrelated sources found it on their own, which is the earliest public signal this lab can see.
- Corroborated: That the theme is being discussed: 2 independent sources (INFERENCE). What they claim about it is not corroborated by this.
- Speculation: 1 of 2 original claim(s) are opinion, prediction or question. 1 claim(s) state something as fact; 1 of them are unverified text claims (the lab has not checked them).
- Reasons to doubt: At least one post looked like it was written to instruct an automated reader (injection suspected); none of its wording is used.
- Liquidity and exit: A theme, not a token: check liquidity and exit for each linked contract separately.
- Next step: Theme only. Look at the linked contracts one by one; `python -m memelab social narrative-why --run 2 --cluster tag:ai_agent` lists the posts behind it.
- Freshness and coverage: FRESH, newest observation 1.5 h before as of, confidence MODERATE; coverage telegram COVERED 1; x COVERED 1.
- Provenance: narrative run 2, cluster tag:ai\_agent, claims 5, 26.

### Also active

#### NEWPUP on solana (aSA48roHpDdByt47MXz4oV5HNLkZSjDVaSA48roHpDdB)

- Priority: MEDIUM (HEURISTIC, orders this report only): one independent source or not estimable.
- What happened: 3 post(s) about the token NEWPUP on solana (aSA48roHpDdByt47MXz4oV5HNLkZSjDVaSA48roHpDdB) from 3 account(s): 1 independent source(s), 2 repeat(s) (reposts, forwards, quotes that repeat) and 0 reply or copy item(s). Claim types among originals: launch 1.
- First observed 2026-10-13 06:30 EDT (10:30 UTC); first published 2026-10-13 06:30 EDT (10:30 UTC); last observed 2026-10-13 07:00 EDT (11:00 UTC).
- Who said it: [fx\_foxtrot\_channel (telegram)](<https://t.me/fx_foxtrot_channel/7>) (independent original, 2026-10-13 06:30 EDT (10:30 UTC), stance positive); fx\_golf\_channel (telegram) (no public link) (amplifier, 2026-10-13 06:45 EDT (10:45 UTC), stance positive); fx\_hotel\_channel (telegram) (no public link) (amplifier, 2026-10-13 07:00 EDT (11:00 UTC), stance positive).
- Independence vs repetition: 1 independent of 3 account(s); 2 repeat(s) counted once with their original; 0 reply or copy item(s); 0 repeat(s) of an unseen original.
- Why it matters (HEURISTIC): new in this snapshot.
- Corroborated: Nothing: one independent source only.
- Speculation: 1 claim(s) state something as fact; 1 of them are unverified text claims (the lab has not checked them).
- Reasons to doubt: At least one post looked like it was written to instruct an automated reader (injection suspected); none of its wording is used. Narrative confidence LOW. Single independent source.
- Liquidity and exit: No liquidity or exit data stored for this contract. Attention says nothing about whether a position could be exited; run the structural checks before anything else.
- Next step: Run the existing structural checks on solana:aSA48roHpDdByt47MXz4oV5HNLkZSjDVaSA48roHpDdB (scout or analyze) before reading anything into the attention. Provenance: `python -m memelab social narrative-why --run 2 --cluster ca:solana:aSA48roHpDdByt47MXz4oV5HNLkZSjDVaSA48roHpDdB`.
- Freshness and coverage: FRESH, newest observation 1.0 h before as of, confidence LOW; coverage telegram COVERED 1.
- Provenance: narrative run 2, cluster ca:solana:aSA48roHpDdByt47MXz4oV5HNLkZSjDVaSA48roHpDdB, claims 26, 27, 28.

### Older or weakly covered

#### SLOWFROG on solana (6DntXA18w931KFERa8e2VvvazqQA4hJp6DntXA18w931)

- Priority: LOW (HEURISTIC, orders this report only): no activity inside the window.
- What happened: 2 post(s) about the token SLOWFROG on solana (6DntXA18w931KFERa8e2VvvazqQA4hJp6DntXA18w931) from 2 account(s): 2 independent source(s), 0 repeat(s) (reposts, forwards, quotes that repeat) and 0 reply or copy item(s). Claim types among originals: bullish 2.
- First observed 2026-10-10 08:00 EDT (12:00 UTC); first published 2026-10-10 08:00 EDT (12:00 UTC); last observed 2026-10-10 09:00 EDT (13:00 UTC).
- Who said it: [fx\_india (x)](<https://example.invalid/x/s1>) (independent original, 2026-10-10 08:00 EDT (12:00 UTC), stance positive); [fx\_juliet (x)](<https://example.invalid/x/s2>) (independent original, 2026-10-10 09:00 EDT (13:00 UTC), stance positive).
- Independence vs repetition: 2 independent of 2 account(s); 0 repeat(s) counted once with their original; 0 reply or copy item(s); 0 repeat(s) of an unseen original.
- Why it matters (HEURISTIC): ongoing discussion with no change recorded.
- Corroborated: That the token is being discussed: 2 independent sources (INFERENCE). What they claim about it is not corroborated by this.
- Speculation: 2 of 2 original claim(s) are opinion, prediction or question.
- Reasons to doubt: Narrative confidence LOW. Stale: newest observation 71.0 h before as of.
- Liquidity and exit: No liquidity or exit data stored for this contract. Attention says nothing about whether a position could be exited; run the structural checks before anything else.
- Next step: Run the existing structural checks on solana:6DntXA18w931KFERa8e2VvvazqQA4hJp6DntXA18w931 (scout or analyze) before reading anything into the attention. Provenance: `python -m memelab social narrative-why --run 2 --cluster ca:solana:6DntXA18w931KFERa8e2VvvazqQA4hJp6DntXA18w931`.
- Freshness and coverage: STALE, newest observation 71.0 h before as of, confidence LOW; coverage x COVERED 1.
- Provenance: narrative run 2, cluster ca:solana:6DntXA18w931KFERa8e2VvvazqQA4hJp6DntXA18w931, claims 1, 2.

### Unresolved ticker-only mentions

Never joined to a token and never ranked.
- MOONX: 3 mention(s). ticker only: no contract on a stated chain, so it is never joined to a token or ranked. Find a contract address on a stated chain from an official source before researching it.

---
Research notes only. Nothing here is a trade instruction, a score or a watchlist change; social attention says nothing about whether a token can be bought or sold.
Feed feed-v1, schema memelab.social.feed/1, sha256 3d95007460266592.
FIXTURE DEMO: invented accounts, tokens, posts and times. This is not live data and not a current conversation.

## View 2: trader conversation digest

## Trader conversation digest

FIXTURE DEMO: invented accounts, tokens, posts and times. This is not live data and not a current conversation.

As of 2026-10-13 08:00 EDT (12:00 UTC). Window: 2026-10-12 08:00 EDT (12:00 UTC) to 2026-10-13 08:00 EDT (12:00 UTC) (24 h).
Data: narrative snapshot run 2 (2026-10-13 UTC), cutoff 2026-10-13 08:00 EDT (12:00 UTC), 0.0 h old, FRESH.
Coverage: telegram COVERED 1; x COVERED 1.
Not clustered: 3 token not resolved to a contract.
Model: not used (status on this machine: not checked in the fixture demo). The feed is built from stored structure only.

### GOODCAT on solana (B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY)

- Priority HIGH (HEURISTIC). 3 independent of 5 account(s); 2 repeat(s) counted once with their original.
- [fx\_alpha (x)](<https://example.invalid/x/g1>), trader fx\_trader\_one: stance positive, disclosed position holds, latest at 2026-10-13 03:00 EDT (07:00 UTC).
- [fx\_bravo (x)](<https://example.invalid/x/g2>): stance positive, disclosed position not\_disclosed, latest at 2026-10-13 03:40 EDT (07:40 UTC).
- [fx\_charlie\_channel (telegram)](<https://t.me/fx_charlie_channel/101>): stance positive, disclosed position not\_disclosed, latest at 2026-10-13 04:15 EDT (08:15 UTC).
- Changed position: fx\_alpha (x) went from negative (no\_position) to positive (holds), previous snapshot run 1.
- Disagreement: none among attributable sources.
- Repetition: 2 repeat(s) are counted once with their original and are not listed as people.
- Liquidity and exit: liquidity reported: 180,000 USD per fixture\_provider at 2026-10-13 07:30 EDT (11:30 UTC) (FACT). Reported pool liquidity is not exit depth; a sell quote at your size is the real test.
- Next step: Run the existing structural checks on solana:B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY (scout or analyze) before reading anything into the attention. Provenance: `python -m memelab social narrative-why --run 2 --cluster ca:solana:B3UnKGxPe2nYt3QGSS5h3Hzwf9qLcoC7B3UnKGxPe2nY`.

### HYPEDOG on solana (bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ)

- Priority HIGH (HEURISTIC). 2 independent of 14 account(s); 12 repeat(s) counted once with their original.
- [fx\_delta (x)](<https://example.invalid/x/h1>): stance positive, disclosed position not\_disclosed, latest at 2026-10-13 05:30 EDT (09:30 UTC).
- [fx\_echo (x)](<https://example.invalid/x/h2>): stance negative, disclosed position not\_disclosed, latest at 2026-10-13 06:10 EDT (10:10 UTC).
- Changed positions: none recorded.
- Disagreement (shown, not resolved): negative: fx\_echo (x); positive: fx\_delta (x).
- Repetition: 12 repeat(s) are counted once with their original and are not listed as people.
- Liquidity and exit: liquidity reported: 42,000 USD per fixture\_provider at 2026-10-13 07:30 EDT (11:30 UTC) (FACT). No sell route found by fixture\_provider at 2026-10-13 07:35 EDT (11:35 UTC) (FACT). Treat as not exitable until a later check shows a route.
- Next step: Run the existing structural checks on solana:bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ (scout or analyze) before reading anything into the attention. Provenance: `python -m memelab social narrative-why --run 2 --cluster ca:solana:bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ`. Review the chronology: `python -m memelab social chrono flags --token solana:bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ`.

### theme ai\_agent

- Priority HIGH (HEURISTIC). 2 independent of 2 account(s); 0 repeat(s) counted once with their original.
- [fx\_alpha (x)](<https://example.invalid/x/g1>), trader fx\_trader\_one: stance positive, disclosed position holds, latest at 2026-10-13 03:00 EDT (07:00 UTC).
- [fx\_foxtrot\_channel (telegram)](<https://t.me/fx_foxtrot_channel/7>): stance positive, disclosed position not\_disclosed, latest at 2026-10-13 06:30 EDT (10:30 UTC).
- Changed positions: none recorded.
- Disagreement: none among attributable sources.
- Repetition: 0 repeat(s) are counted once with their original and are not listed as people.
- Liquidity and exit: A theme, not a token: check liquidity and exit for each linked contract separately.
- Next step: Theme only. Look at the linked contracts one by one; `python -m memelab social narrative-why --run 2 --cluster tag:ai_agent` lists the posts behind it.

### NEWPUP on solana (aSA48roHpDdByt47MXz4oV5HNLkZSjDVaSA48roHpDdB)

- Priority MEDIUM (HEURISTIC). 1 independent of 3 account(s); 2 repeat(s) counted once with their original.
- [fx\_foxtrot\_channel (telegram)](<https://t.me/fx_foxtrot_channel/7>): stance positive, disclosed position not\_disclosed, latest at 2026-10-13 06:30 EDT (10:30 UTC).
- Changed positions: none recorded.
- Disagreement: none among attributable sources.
- Repetition: 2 repeat(s) are counted once with their original and are not listed as people.
- Liquidity and exit: No liquidity or exit data stored for this contract. Attention says nothing about whether a position could be exited; run the structural checks before anything else.
- Next step: Run the existing structural checks on solana:aSA48roHpDdByt47MXz4oV5HNLkZSjDVaSA48roHpDdB (scout or analyze) before reading anything into the attention. Provenance: `python -m memelab social narrative-why --run 2 --cluster ca:solana:aSA48roHpDdByt47MXz4oV5HNLkZSjDVaSA48roHpDdB`.

### SLOWFROG on solana (6DntXA18w931KFERa8e2VvvazqQA4hJp6DntXA18w931)

- Priority LOW (HEURISTIC). 2 independent of 2 account(s); 0 repeat(s) counted once with their original.
- [fx\_india (x)](<https://example.invalid/x/s1>): stance positive, disclosed position not\_disclosed, latest at 2026-10-10 08:00 EDT (12:00 UTC).
- [fx\_juliet (x)](<https://example.invalid/x/s2>): stance positive, disclosed position not\_disclosed, latest at 2026-10-10 09:00 EDT (13:00 UTC).
- Changed positions: none recorded.
- Disagreement: none among attributable sources.
- Repetition: 0 repeat(s) are counted once with their original and are not listed as people.
- Liquidity and exit: No liquidity or exit data stored for this contract. Attention says nothing about whether a position could be exited; run the structural checks before anything else.
- Next step: Run the existing structural checks on solana:6DntXA18w931KFERa8e2VvvazqQA4hJp6DntXA18w931 (scout or analyze) before reading anything into the attention. Provenance: `python -m memelab social narrative-why --run 2 --cluster ca:solana:6DntXA18w931KFERa8e2VvvazqQA4hJp6DntXA18w931`.

### Unresolved ticker-only mentions

Never joined to a token and never ranked.
- MOONX: 3 mention(s). ticker only: no contract on a stated chain, so it is never joined to a token or ranked. Find a contract address on a stated chain from an official source before researching it.

---
Research notes only. Nothing here is a trade instruction, a score or a watchlist change; social attention says nothing about whether a token can be bought or sold.
Feed feed-v1, schema memelab.social.feed/1, sha256 3d95007460266592.
FIXTURE DEMO: invented accounts, tokens, posts and times. This is not live data and not a current conversation.

## View 3: feed filtered to --risk any

## Social intelligence feed

FIXTURE DEMO: invented accounts, tokens, posts and times. This is not live data and not a current conversation.

As of 2026-10-13 08:00 EDT (12:00 UTC). Window: 2026-10-12 08:00 EDT (12:00 UTC) to 2026-10-13 08:00 EDT (12:00 UTC) (24 h).
Data: narrative snapshot run 2 (2026-10-13 UTC), cutoff 2026-10-13 08:00 EDT (12:00 UTC), 0.0 h old, FRESH.
Coverage: telegram COVERED 1; x COVERED 1.
Not clustered: 3 token not resolved to a contract.
Model: not used (status on this machine: not checked in the fixture demo). The feed is built from stored structure only.
Filters: risk any.

1 item(s) shown of 5 (1 high, 0 medium, 0 low), 0 unresolved ticker(s).

#### HYPEDOG on solana (bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ)

- Priority: HIGH (HEURISTIC, orders this report only): a chronology risk flag rests on a linked or self-claimed wallet.
- What happened: 14 post(s) about the token HYPEDOG on solana (bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ) from 14 account(s): 2 independent source(s), 12 repeat(s) (reposts, forwards, quotes that repeat) and 0 reply or copy item(s). Claim types among originals: promotion 1, risk 1.
- First observed 2026-10-13 05:30 EDT (09:30 UTC); first published 2026-10-13 05:30 EDT (09:30 UTC); last observed 2026-10-13 06:10 EDT (10:10 UTC).
- Who said it: [fx\_delta (x)](<https://example.invalid/x/h1>) (independent original, 2026-10-13 05:30 EDT (09:30 UTC), stance positive); [fx\_echo (x)](<https://example.invalid/x/h2>) (independent original, 2026-10-13 06:10 EDT (10:10 UTC), stance negative); [fx\_burst\_00 (x)](<https://example.invalid/x/hr0>) (amplifier, 2026-10-13 05:32 EDT (09:32 UTC), stance positive); [fx\_burst\_01 (x)](<https://example.invalid/x/hr1>) (amplifier, 2026-10-13 05:32 EDT (09:32 UTC), stance positive); and 10 more repeat account(s).
- Independence vs repetition: 2 independent of 14 account(s); 12 repeat(s) counted once with their original; 0 reply or copy item(s); 0 repeat(s) of an unseen original.
- Why it matters (HEURISTIC): new in this snapshot; several unrelated sources found it on their own, which is the earliest public signal this lab can see; a timeline flag suggests trading by a linked or self-claimed wallet around the posts; the pattern of repetition may be promotion rather than discovery.
- Corroborated: That the token is being discussed: 2 independent sources (INFERENCE). What they claim about it is not corroborated by this.
- Speculation: 1 of 2 original claim(s) are opinion, prediction or question. 1 claim(s) state something as fact; 1 of them are unverified text claims (the lab has not checked them).
- Reasons to doubt: Sources disagree (negative 1, positive 1); not resolved here. many accounts amplified it inside a short burst (coordination hypothesis, HEURISTIC, not proven). Chronology risk SALE\_DURING\_PROMOTION (HEURISTIC, not proven, wallet CLAIMED, rule chrono.sale\_during\_promotion.v1, run 1).
- Liquidity and exit: liquidity reported: 42,000 USD per fixture\_provider at 2026-10-13 07:30 EDT (11:30 UTC) (FACT). No sell route found by fixture\_provider at 2026-10-13 07:35 EDT (11:35 UTC) (FACT). Treat as not exitable until a later check shows a route.
- Next step: Run the existing structural checks on solana:bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ (scout or analyze) before reading anything into the attention. Provenance: `python -m memelab social narrative-why --run 2 --cluster ca:solana:bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ`. Review the chronology: `python -m memelab social chrono flags --token solana:bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ`.
- Freshness and coverage: FRESH, newest observation 1.8 h before as of, confidence MODERATE; coverage x COVERED 1.
- Provenance: narrative run 2, cluster ca:solana:bWnSryKtxfLJ822btJYgYbC84qx9RcFqbWnSryKtxfLJ, claims 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, chronology runs 1, market facts 2, 3.

---
Research notes only. Nothing here is a trade instruction, a score or a watchlist change; social attention says nothing about whether a token can be bought or sold.
Feed feed-v1, schema memelab.social.feed/1, sha256 fd0b36e44faf52bd.
FIXTURE DEMO: invented accounts, tokens, posts and times. This is not live data and not a current conversation.
