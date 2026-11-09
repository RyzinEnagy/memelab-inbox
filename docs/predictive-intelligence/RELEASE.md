# Predictive engine: release summary for Elving

Date: 2026-11-09. This is the plain-language version of the Phase 21 release decision. The full memo is `audits/predictive-intelligence/phase_21/release/RELEASE_DECISION.md`.

## The short answer

- Ready (GO): a research-only engine that sits beside the lab, switched OFF by default. When you switch it on in a test copy, it adds a section to the scout report that says, for each token and each question, "no forecast" and why. That is all it does today.
- Not ready (NO-GO): any version that shows you a probability. No model has shown it can beat a plain base rate on data it had not seen, and none is calibrated.
- Not decided here: anything that needs your approval (list below). Nothing was merged, sent, deployed or paid for.

## What exists

1. An abstention engine. For each new or changed opportunity it records the exact token (chain plus mint address), the time, and an answer for three questions: does the price touch +25% before -15% within 24 hours, the same within 6 hours, and does it halve or stop trading within 24 hours. Today every answer is ABSTAIN, with reasons such as "no model selected", "not calibrated", "not enough history", "inputs too old".
2. The flag is OFF. With it off, the lab's reports are byte for byte what they were before this work (checked on two real exports and six kinds of settings file).
3. Two simple reference models (a base rate and a simple logistic model) are kept for comparison only. They are never shown to you, and since 2026-10-31 they are out of date (MODEL_STALE), so they abstain too.
4. No validated model, no shadow model, no ensemble.
5. MiroFish (the multi-agent simulator): NO-GO. It stays off. There was no dated catalyst data to test it on and no approved budget.
6. The backtesting engine is not merged into this branch, so every answer carries BACKTEST_NOT_AVAILABLE.

## How it was checked today

All from a fresh copy of the branch downloaded from GitHub, in a new Python environment with only numpy and pytest, with no network and no passwords or tokens visible to the checks:

- The full test suite: only the two known clock-related failures.
- A real run on the 2026-10-26 data: 8 tokens, 24 answers, all ABSTAIN, no probability printed; rerunning added nothing.
- A timeline check: no model used information from after its cutoff and no outcome was recorded before it was due. For phases 07 to 20 the git history shows the rules were committed before the results; phases 05 and 06 committed their rules and results together, so for those two git cannot show the order (their target rules were already frozen in Phase 01).
- 48 trap scenarios: every check held, but 12 of them can only be shown on test fixtures (TEST_ONLY), because the live feature they guard does not exist yet (for example crawled pages or a real champion model), and one (P46) still has a small open wording issue (F20-07). 39 earlier counterexamples: all caught.
- The out-of-sample results, recomputed: still no edge.
- Security: no copied copyleft code, no wallet, key, signing or order code, no scheduled job, nothing beyond numpy and the standard library; spend 0.

## Decisions waiting on you

1. Who maintains it: you are the owner of every decision below; code changes go through a reviewed phase.
2. Whether to change the promotion rules so a model could ever reach "shadow" from new data (PI-D-091). Without this, no model can be promoted.
3. Any spend on LLMs, Zep or MiroFish, and any paid data source.
4. Whether to collect catalyst and social data into a store this engine can read.
5. Deploying the forward depth collector on your computer (already approved in PI-D-044, not yet running).
6. Merging the backtesting work (PR #4) into this line.
7. Any merge into `main`.
8. Any real alert delivery (Telegram or email). Today alerts are previews in a local folder only.
9. Turning the flag on anywhere other than a test copy.
10. A signing key for the engine's private records (only if you want tampering with a re-seal caught).
11. Retiring or replacing the out-of-date reference models.

## Small open items (no approval needed)

- The private research stores live only on the cloud Linux session; rebuilding them elsewhere is documented but not tried (OI21-2).
- 7 outcomes from 2026-10-26 are still "pending" because the label script skips tokens it already read once. Fixing it is a small code change; it cannot change any result (there are too few days of data either way).
- F20-07: one status label could be clearer. F20-10: one evidence file has a full folder path in it. F20-11: the tests need a loopback network interface (now in the install guide). F20-13: a broken `data/config.json` stops the scout (an older lab behaviour, outside this engine). F20-14: one monitoring command writes to a tracked file, so run it in a test copy.

## Where to read more

- Install: `audits/predictive-intelligence/phase_21/release/INSTALL_RUNBOOK.md`
- How to use it, track outcomes, re-read, retire old models: `USER_GUIDE.md` (same folder)
- What the models can and cannot say: `MODEL_LIMITS.md`
- How to switch it off and recover: `ROLLBACK_PROOF.md`
- Every pending decision with owner and blocker: `OPEN_DECISIONS.md`
