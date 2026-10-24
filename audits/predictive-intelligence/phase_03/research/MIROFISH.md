# MiroFish (666ghj/MiroFish at `7657031a`): source-level review summary

Lead summary of `REVIEWS/666ghj__MiroFish.md` (reviewer R5), with the claims that decide its place checked by the lead (MI-1 to MI-4 in `verify/VERIFY_RESULTS.json`) and the companion review of its engine, `REVIEWS/camel-ai__oasis.md` (OA-1, OA-2). No numeric accuracy is assigned anywhere in this phase: MiroFish produces no probability or testable event, and agreement among its agents is not a probability of anything (P27). Lead total 8 of 100 (reviewer 10), rank 29 of 29 eligible; integration decision ISOLATED_RESEARCH.

## What it is, at the pin

- A behavioral scenario generator: uploaded documents and a free-text "simulation requirement" become an LLM-built entity graph in Zep Cloud, an LLM writes personas and a simulation config, the OASIS engine runs LLM agents on a simulated Reddit or Twitter, and a ReportAgent writes a narrative report. Flask backend with 59 routes, Vue frontend, simulation scripts run as subprocesses.
- Its only legitimate role for the lab is behavioral hypothesis generation for Phases 14 and 15 behind the PLANNED_SEAMS "Behavioral simulation" boundary, with the default state SIMULATION_NOT_AVAILABLE. It fills no model-training gap and is never a feature, score input or probability.
- No probability output exists in the backend (no `probab` in its English code; the Chinese "probability" mentions are agent activation rates).

## AGPL obligations (P31)

- Root `LICENSE` is AGPL-3.0, sha256 `8486a10c4393cee1...`, equal to Phase 02 (MI-1); transitive AGPL PyMuPDF and GPL-2.0 python-igraph.
- Copying any MiroFish file into memelab would make the result a covered work that the public repository (no LICENSE file) could not convey under its terms; copying is also not approved (PI-D-005). Nothing was copied: the repository scan finds AGPL text only in the license reviews and a Phase 02 classifier string.
- Running it unmodified, privately, as a separate process carries no source obligation beyond keeping notices. Section 13 applies if a modified copy is reachable by others over a network, and the shipped defaults make that easy by accident: Flask binds `0.0.0.0` (`backend/run.py:40`), CORS allows every origin (`backend/app/__init__.py:43`), the default `SECRET_KEY` is a constant (`config.py:21`), the list route answers 200 without credentials and reflects an untrusted origin (MI-1, MI-4). Whether a memelab HTTP client is a separate work is INFERENCE, not a legal opinion.

## LLM and Zep costs (BLOCKED for paid use)

- The full pipeline needs an LLM key and Zep Cloud (`ZEP_API_URL` is refused, `config.py:71-72`); both are paid and not approved (PI-D-005), so nothing beyond an offline mock ran.
- Cost controls at the pin: `max_rounds` truncation, `semaphore=30`, `REPORT_AGENT_MAX_TOOL_CALLS=5`; no token budget, spend cap or circuit breaker (P48).
- Measured on the smallest case (4 fictional agents, 4 rounds, deterministic mock LLM on 127.0.0.1): 8 LLM calls per run, about 2,700 prompt characters per call in a near-empty world, 15 to 17 s wall, 610 MB peak memory in the child processes. INFERENCE from the code: a default run with 50 entities is on the order of 1,000 to 2,000 agent calls per platform before profile, config and report calls; OASIS's own reference is 335,600 input tokens for 100 agents for one step.
- Data rights: every uploaded document, the entity graph and (with the frontend default) all simulated activity go to Zep Cloud and the LLM provider, whose terms were not read (UNKNOWN).

## Offline mock run results

- Path that works without copying source: the unmodified `backend/scripts/run_reddit_simulation.py` as a subprocess in its own Python 3.12 venv, inside a loopback-only network namespace, with config and fictional profiles written by the caller and the SQLite trace read back. Attempt 1 failed because camel's token counter tried to download `o200k_base.tiktoken`; attempt 2 with the tokenizer cache pre-filled ran end to end (`SMOKES/666ghj__MiroFish/sim_summary.json`). The Twitter platform also needs a Hugging Face model download. The profile files kept from that run hold only the sha256 and length of the fictional `bio` and `persona` strings, because the lab's content guard bars a stored `bio` key in any tracked JSON file (repair pass, `SMOKES/666ghj__MiroFish/PROFILES_TRANSFORMED.txt`).
- This path drops the ontology, Zep graph, persona generation and ReportAgent, which all need paid services.
- Python 3.13 is not supported (`requires-python >=3.11,<3.13`); the lock installs two dependencies that declare Python below 3.12 on 3.12.

## Non-determinism (P29)

- Two runs with identical config, profiles and a deterministic mock (replies are a function of the request sha256) produced different traces: 19 rows with 3 posts versus 20 rows with 5 posts, trace sha256 `a0a70f5f...` versus `3159ba9f...` (MI-3). The repository has no `random.seed` or `np.random.seed` anywhere (MI-1); agent activation uses the unseeded module `random`, and the OASIS clock starts at `datetime.now()` so wall-clock time enters every prompt (OA-1, OA-2).
- Consequence: persona or seed perturbations cannot be separated from run noise without many repetitions, and a seed cannot be imposed without modifying the scripts (which would bring Section 13 duties if served).

## Silent success on LLM failure (P30)

- With the LLM endpoint unreachable, the simulation script exits 0, prints "模拟循环完成!" (simulation loop complete) and leaves a database with only sign-ups, the initial post and refreshes; each agent's `APIConnectionError` goes to a log file only (MI-3, `llm_down_output.txt`). Persona and event-config generation also fall back silently after failed calls. The backend does refuse to start without keys.
- Any adapter must treat a run as failed unless the trace contains LLM-generated actions, and must report SIMULATION_NOT_AVAILABLE otherwise.

## P26, P27, P28

- P26 (LLM knows the future): every stage is an LLM call (ontology, persona, config, each agent, ReportAgent) whose pretraining cannot be cut at a decision time; persona prompts ask the model to "restore the existing real situation to the maximum extent" (`oasis_profile_generator.py:718`). Retrospective tests on 2026-10-07 to 10-23 decisions are invalid with any model trained after those dates. The README's "lost ending" novel demo is a P26 case: the ending is in pretraining data. Flag LEAKAGE_FAIL.
- P27 (agent consensus is not probability): all agents share one model and one prompt template, so "90% of agents agree" is a property of that model, not a 90% likelihood. The ReportAgent's plan prompt states that the simulated world's evolution is "the prediction of what may happen in the future" and a "rehearsal of the future" (`report_agent.py:552-567`, MI-2): the lab must never surface that text as a forecast. The scorecard checker refuses any probability or calibration point for a behavioral simulator.
- P28 (post-event seeds): six entry points for post-event information, none with an as-of check: uploaded documents and free-text requirement; Zep ingestion without a source time; persona prompts; LLM-written initial posts and narrative direction; simulated activity written back into the same graph and read later as facts; `interview_agents` answers from the same LLM.

## README claims not supported by the code (P42)

"Predicting Anything", "precisely deduce future trajectories", "win decisions after countless simulations", "high-fidelity parallel digital world", "thousands of intelligent agents with independent personalities" and "test policies at zero risk": no forecast output, no evaluation code, no multi-run aggregation, no behavioral validation, and agents share one model. None of it earned a point.

## What it would take before any Phase 14 trial

Elving's approval for LLM spend (Zep is avoidable on the script path), a model whose training cutoff precedes the evaluated events, seed control imposed from outside, many repetitions per scenario, pre-registered outcome coding with blind scoring, and comparison against the LLM-free comparator (a seeded numpy trader loop, see `REVIEWS/mesa__mesa.md`) and against abstention (MIROFISH_EVALUATION.md two-stage gate). If an LLM simulation is ever approved, OASIS used directly (Apache-2.0, no Zep, no web service) does the same job with fewer obligations.
