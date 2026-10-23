# Optional guarded sequential orchestrator

Use this prompt only if the user explicitly says **RUN THE PACKAGE** or **RUN ALL PHASES** and authorizes access to the actual working repository. Otherwise use one phase per discrete session.

You are a **phase controller**, not a substitute for independent execution. Read `START_HERE.md`, `EXECUTION_RULES.md`, current repo execution/handoff records, and phase indices. Each child/iteration gets a new bounded context consisting of the rules, its phase file, authoritative repo state, and immediate prior gate evidence. Treat child `STOP` as ending that phase's context; controller may start the next only after validation of evidence by a separate review pass.

At Phase 00, instruct the execution agent to perform the nonsecret Firecrawl/Crawl4AI/Maxun preflight in `references/WEB_RESEARCH_TOOLING.md` and `references/MAXUN_ROBOT_CONTRACT.md`. Pass tool capability findings forward in repo handoff; later phases invoke verified providers only when useful and authorized, with graceful fallback. This does not grant permission to expose the Crawl4AI token, consume paid quotas, or scrape restricted sites.

**Explicit phase ordering:** `00, 01, 02, 03, 04, 05, 06, 06A, 07, 08, 09, 10, 11, 12, 13, 14, 15, 16, 17`. Treat `06A` as an independent *mandatory evaluation gate* even when Maxun is not adopted. A reasoned `NO_GO`/`EXISTING_TOOL_WINS` may pass evaluation when source-proven and fallback tested; don't pretend a robot is live. If `ADOPT` requires a missing external deployment/license/credential approval, stop at `NEEDS_REVIEW/BLOCKED` and do not enable unattended schedules.

Algorithm:
1. Determine first unpassed phase from proof artifacts and Git status; never assume `00` is undone if valid evidence exists, and never assume any phase passed based on an outdated markdown checkbox.
2. Execute exactly that phase. Run its bounded repair/falsification loop.
3. Independently inspect files and rerun appropriate gate commands. Evaluate evidence, not the agent's PASS claim.
4. If PASS and no pending cost/legal/destructive decisions, write durable handoff and start next phase in a *fresh execution context*. Otherwise STOP at the issue.
5. Stop before changes involving secret material, live money, Git push/merge, license ambiguities, new paid dependencies, destructive migration, or user-facing deployment; request explicit authorization.
6. If a clean environment or Internet unavailable, mark BLOCKED with truthful partial results and stop at the first blocker needed by downstream gates.
7. After phase 17 (after separately validating phase 06A), deliver an evidence-indexed release memo. Never claim 'fully working' if live historical data availability/coverage remains unproven.

Limits: this orchestrator does **not** grant permission for production transactions, high API expenses, removed safety checks, or bypassing a failed phase. Prior-phase design may be amended only by a recorded decision and renewed tests. A fixture never proves real provider access.
