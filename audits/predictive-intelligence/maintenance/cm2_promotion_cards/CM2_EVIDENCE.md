# CM-2 evidence: promotion from prospective evidence, fresh reference cards, the daily cycle

Branch `feature/predictive-intelligence`. Approved by Elving on 2026-11-09 (ED-1, ED-10). Decisions PI-D-122 to PI-D-129. Status: NEEDS_REVIEW (the independent skeptic has `SKEPTIC_PACKET.md`). Local only, not pushed (remote at `60eb729`). Times are UTC.

## Order of events

| Time | Commit or event | What |
|---|---|---|
| 2026-11-10T01:13:46Z | `ed85b2c` | change control PI-D-122 and `daily/RECIPE.json` (the recipe freeze) |
| 01:25:40Z | `e79d846` | frozen code: PROMOTION_CM2, training splits, `promotion.py`, the daily cycle, `build_cm2.py`, tests; pins PI-D-123 |
| 01:25:45Z | first T2 read | `fetch_t2` read 1 of 7, HTTP 200; then the session restarted |
| 01:27:35Z | resume | `check_partial_reads.py`: the read is consistent with the plan (`evidence/interruption.json`) |
| 01:28:27Z to 01:30:28Z | 7 calls | the other 6 reads (one 429 retried after 60 s) |
| 01:30:39Z, 01:30:46Z | `labels`, `cards` | base label set; cards fitted twice, registered |
| 01:32:46Z | `a140986` | reads, labels, cards, registry, search ledger rows, cost ledger row |
| 01:33:27Z | fresh clone | two daily runs at `a140986` (frozen cycle code) |
| | `43a485b` | PI-D-124, test fixture; probes |
| | `b7aabe3`, `07a815e` | PI-D-126 tests; `daily/PROCEDURE.md` (PI-D-125) |
| | `a8c96d7` | PI-D-128, the one change to frozen cycle code |
| | `2f72034`, `4e020cb` | PI-D-129, mutation probe offline |

## Acceptance checklist (from `CHANGE_CONTROL.md`)

| Id | Result | Evidence |
|---|---|---|
| G1 | met: `ed85b2c` (change control, recipe) precedes `e79d846` (code) precedes the first read (5 s after the code commit) | `git log`, `evidence/t2_reads.json` |
| G2 | met: `git diff ed85b2c HEAD -- memelab/predictive/contract.py` only adds after `registry_sha256`; `registry_sha256()` `4b4aabce77a5...`; rule `57f7fb7cb255...`; governing `b88f0058a3c8...`, pinned in `predictive_daily.py` and `tests/test_predictive_contract.py` | contract tests pass |
| G3 | met by `tests/test_predictive_promotion.py` (22) and `tests/test_predictive_cm2_guards.py` (6) | mutation probe |
| G4 | met: on `ed85b2c` the CM-2 tests give contract 2 failed, labels 1 failed, promotion and daily collection errors (modules absent) | `evidence/old_code_probe.txt` |
| G5 | met: 7 labels; 8 calls (1 before the restart, reconstructed in the log from its read record), `token=<mint>`, boundary 1793183400 (2026-10-28T10:30:00Z), at most 6 in any 60 s, bodies archived with sha256 | `evidence/t2_reads.json`, `evidence/label_calls.json`, `raw/`, `COST_LEDGER.md` |
| G6 | met: 6 cards, cutoff 2026-10-28T10:43:04Z, second fit identical; label sets T1 225 (55), T1b 317 (42), T2 213 (40); 333 training decisions; B2 inputs equal to the Phase 19 store | `evidence/cards.json` |
| G7 | met with one reading stated: the RETIRE is one event naming the 69 entry ids (Part B item 5), not 69 events; 6 REGISTER at ABSTAIN; 3 PIN NO_VIABLE_CHAMPION; `verify` ok | `daily/registry/` |
| G8 | met: two runs in a fresh clone, exit 0 and 0, second run appends nothing to the ledger (none exists: 0 decisions after the freeze), 0 calls, changes only in allowed paths; repeated at `a8c96d7`; exit codes and reasons tested | `evidence/daily_fresh_clone.json`, `evidence/daily_fresh_clone_pi_d_128.json` |
| G9 | met with one equivalent mutant (D07): 35 applied, 34 caught | `evidence/mutation_probe.json` |
| G10 | see "Post-commit checks" | `postcommit/` |
| G11 | records written; `SKEPTIC_PACKET.md`; status NEEDS_REVIEW | this folder, `docs/predictive-intelligence/` |

## Interruption

The previous session stopped after the first of the 7 T2 reads (retrieved 01:25:46Z). Before resuming, `probes/check_partial_reads.py` (added, read-only) checked that read: it is a pending T2 decision, the first in the frozen order, its boundary is the T2 window end, its URL is the frozen one with `token=<mint>` and the decision's pool, the target had matured, and the archived file and body match their sha256. All true. `fetch_t2` keeps its call log in memory until it ends, so that call had no log entry; it is in `label_calls.json` as an entry with `reconstructed_from`. The resumed `fetch_t2` skipped the decision it already held and read the other 6.

## Commands and results

| Command | Exit | Result |
|---|---|---|
| `python -B probes/check_partial_reads.py` | 0 | all_consistent true |
| `python -B probes/build_cm2.py fetch_t2` | 0 | pending 7, reads 7, others 0, calls 7 |
| `python -B probes/build_cm2.py labels` | 0 | 4,161 lines; 7 T2 rows (2 DRAWDOWN_50, 5 NO_SEVERE_EVENT); ledger pairs 61 of 61 equal; other pairs 149 equal, 0 different |
| `python -B probes/build_cm2.py cards` | 0 | as G6, G7; stale after 2026-11-11T10:43:04Z |
| `python -B audits/predictive-intelligence/daily/predictive_daily.py verify` | 0 | `{"ok": true, "problems": []}` |
| `bash probes/fresh_clone_daily.sh REPO OUT` at `a140986` | 0 | runs 0 and 0; 23 s and 1 s |
| same at `a8c96d7` | 0 | runs 0 and 0; alerts equal to the first record |
| `bash probes/old_code_probe.sh REPO OUT` | 0 | as G4 |
| `python -m pytest -q tests/test_predictive_daily.py` after PI-D-124 | 0 | 11 passed |
| `python -m pytest -q tests/test_predictive_cm2_guards.py tests/test_predictive_daily.py` after PI-D-128 | 0 | 17 passed |
| `python tools/release_audit.py` (working tree, before the records) | 0 | "Needs action: no." |

## Mutation probe

`python -B probes/mutation_probe.py SCRATCH` at `4e020cb`, every mutant's tests inside `unshare -n`, each mutation committed in a scratch clone so the end-to-end tests run it. Baseline: promotion plus guards 28 passed; daily plus guards 17 passed. Result: 35 mutations applied (25 on `promotion.py`, 10 on the cycle's guards), 34 caught, 1 survivor, D07, an equivalent mutant (the removed check is repeated by `monitoring.is_append_only`; `CHANGE_CONTROL_PI-D-128.md`).

Earlier runs, kept: run 1 at `43a485b` (34 applied, 23 caught; 6 untested guards and 5 mutations that never reached the script, PI-D-126); runs 2 and 3 stopped by hand during D08, which made 63 free calls from test clones (PI-D-129, `evidence/mutation_probe_network.json`); run 4 offline but invalid (baseline failed on commit signing, every mutant counted as caught; not used).

## Change controls after the freeze

PI-D-124 (test fixture), PI-D-126 (tests for untested guards), PI-D-128 (a failed run never commits a ledger that does not verify; test fails on the frozen script), PI-D-129 (probe offline; 63 free calls a mutant made are logged). `memelab/predictive/*` and `build_cm2.py` are unchanged since `e79d846`; `predictive_daily.py` changed only by PI-D-128.

## Deviations

1. The experiment registry names `probes/fetch_pending_t2.py`, `probes/build_cards.py` and `probes/fresh_clone_daily.sh`; the frozen code put the first two in `build_cm2.py` subcommands, and the third was written in this session (`experiments/EXPERIMENT_STATUS.csv`).
2. PI-D-123 was used by the pin file at `e79d846`; its DECISIONS entry was written with these records.
3. Commit `2f72034` also carried the OPEN_DECISIONS update, the skeptic packet and the second fresh-clone record, besides what its message names.
4. The daily cycle's own commits have no Co-Authored-By trailer (the frozen message format); the two fresh-clone runs committed only inside their scratch clones.

## Post-commit checks

Run after the records commit and recorded in `postcommit/` and in a follow-up commit: full suite, social guard, Phase 06 seal, reproductions, single-branch release audit with history, `git status`.

## Artifacts (sha256)

| Path | sha256 |
|---|---|
| `audits/predictive-intelligence/daily/BASE_LABELS.jsonl.gz` | `80b0d04e35bed473fa446b3bffd2e935c35c8cb539a120b3a9b78b119dbd7af3` |
| `audits/predictive-intelligence/daily/PROCEDURE.md` | `a10262b9c1e5f392af482b27d5cf4efffb85be11c6feb85e3407fdb5c4c02155` |
| `audits/predictive-intelligence/daily/RECIPE.json` | `93b6671433e9e94147d8728a1dcdd7b605fb37cbc82de5285a9a670fe2ddb50a` |
| `audits/predictive-intelligence/daily/cards/R-CM2-1_v1_B0_T1_24h.json` | `0f5dcfe8fa1e2a6001c48e970de1fa112f9c2df505462f9c8a3f8a54438255d7` |
| `audits/predictive-intelligence/daily/cards/R-CM2-1_v1_B0_T1b_6h.json` | `78bb802b96701c92e9e8ee174aed20c97bc0cedf3a452fded8c156a27062ef65` |
| `audits/predictive-intelligence/daily/cards/R-CM2-1_v1_B0_T2_24h.json` | `84c3f3fe26403e5367150b501562417c698f3bbbeb144eb7e967554014a0e633` |
| `audits/predictive-intelligence/daily/cards/R-CM2-1_v1_B2_T1_24h.json` | `630323cbc3db8b1c204c0964ad00d12ace9a68fb4d766096e9f4d9080886c4ff` |
| `audits/predictive-intelligence/daily/cards/R-CM2-1_v1_B2_T1b_6h.json` | `9354df7a5eff4bf8b1ce43a9effb20d0990f31bade46aa24675bf14dd82d2a93` |
| `audits/predictive-intelligence/daily/cards/R-CM2-1_v1_B2_T2_24h.json` | `d4348a6d3fdb3ae20edb16e872802b357de1f7264b53888301a4b1d3f9fc5f48` |
| `audits/predictive-intelligence/daily/predictive_daily.py` | `54abd7572e90adc884d42501a81efb6529afa2384ff3f845e96b894fb8602834` |
| `audits/predictive-intelligence/daily/registry/REGISTRY_LOG.jsonl` | `1fcb21c46a6f3934683e8b43e7a330f1a235ac84eadc34eb41fcc213291837a8` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/CHANGE_CONTROL.md` | `b261cca828818b64e614ea885f55aa722caa6a3380788a94de4f4c5de6459782` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/CHANGE_CONTROL_PI-D-124.md` | `b0fdc85eec4498238b2b270bc9085eb36aaef6863d437d53ffc1705fdc6c8877` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/CHANGE_CONTROL_PI-D-126.md` | `d608b9569307e49ebe37257b1c1b498833ecfea01614e726719ec8f79deed564` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/CHANGE_CONTROL_PI-D-128.md` | `4da88bca0a654025fda912e75a4374b7a288ca56503530c22acd04b82240d9d1` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/SKEPTIC_PACKET.md` | `9da0363ece94c6e6fb04921e24ec5f015d08e3ed38f228c0728556f12c68a88c` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/evidence/base_labels.json` | `aaac9365419fc331a68fb99317b4f9c33ca7d83c1a006d595b710ea04af51e18` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/evidence/cards.json` | `c13568bc98f928fd0ff75f3f39fa036e602a3896b5dd12d12df8bdc41376772d` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/evidence/daily_fresh_clone.json` | `4c09c4cadc90868b28716e4a991617134501d2eb4778047922a712d51f6059fc` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/evidence/daily_fresh_clone_pi_d_128.json` | `38b7f88c54d388404a8e99a069544173f94862e1041f823219ee8ece6a96791a` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/evidence/entry_suite_summary.txt` | `586fb28cc4313e0edf061107d27f7d002d9abdea968ef787526d00387a6cbbf5` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/evidence/interruption.json` | `c5d3b8a4af54682ff546e4ec80a4fe5d25d689a873816ee4435d8f0bf2a62dd9` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/evidence/label_calls.json` | `f91c1ed66f0a705bc9d89ce44f126e53d7b4661ba9a70989875af5de623273a0` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/evidence/mutation_probe.json` | `0147a0f36df3d95cfef209fcd53e859c39cbbe6883f7c7a4b6270939c0c8985a` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/evidence/mutation_probe_network.json` | `f3209541f5382d23d99d8d1f501920c464ff546f6bada907d37f0f7c5d511558` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/evidence/mutation_probe_run1.json` | `9a80211385d0bbab6e5b3fcb5f08626ed527cd2ce05ffe071dab6e92a65de575` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/evidence/mutation_probe_run2_partial.log` | `839b8fd56c4e669bb7eb1c11476d2ddd514b2fc0f654787aa4406654672421ec` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/evidence/mutation_probe_run3_partial.log` | `839b8fd56c4e669bb7eb1c11476d2ddd514b2fc0f654787aa4406654672421ec` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/evidence/mutation_probe_run4_invalid_baseline.log` | `2f20ccebb4dce6ea1de40dfaced9c3df858cdeb6c146d80e202981c074e61888` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/evidence/old_code_probe.txt` | `f74f46a9645b6debb8cb60f3529b4760fb493848344f66a31d417182f8776fbe` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/evidence/t2_reads.json` | `363b18141e57c169f742801a4cd03a68ccdd55c43b2cc29f8abc6f15b8a90436` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/experiments/EXPERIMENT_REGISTRY.csv` | `8897aba4b8e589c75ac4ff5d9415ecfc95f577d9cddb55222ae3cc8426a5a148` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/experiments/EXPERIMENT_STATUS.csv` | `9bbc5e141d2d4f537e07a6b95a2271cd979411656695c45ce9c85ea9f393894c` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/experiments/LEDGER_TOTALS.json` | `8b3210097145262674574b815a8a208f92230a075353536a1e6b966a5e1075fb` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/experiments/SEARCH_LEDGER.csv` | `5db2ae7cc43d0d518e22a47eb30cae714b756dce024fc21df91e1ac472364234` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/experiments/SEARCH_LEDGER_CM2_ROWS.csv` | `b82f25851734cd99c0ca5e5b8e0c9f73321efc2d5d46f9ac05c3d0ac58812b9a` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/probes/build_cm2.py` | `6e3c499f013c30b200e5ce6c78d05eb9612d9db40b82d7f9e6949344ca0aadb1` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/probes/check_partial_reads.py` | `3699850296b9c22e09153ff734aa8768c7f129170423be35f574d6d8e0a69828` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/probes/fresh_clone_daily.sh` | `b74ef7e32779ab5b1703a0ff319bc98792471518936ed9f78cdede1080043f2f` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/probes/mutation_probe.py` | `59fe42b41d1c9cf12f6a15ceffe507ace9355d2e0b9a90ceda27620847eaf524` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/probes/old_code_probe.sh` | `7d6da1ba4e71e567d4d497c2098434cb1e053a471f497fb72c04ee3a8e66f937` |
| `memelab/predictive/contract.py` | `e40808e3b8e5f1dc7167dfc4f791b2d048a6f52d26cf4aaaedb1ba3bc09fb2c9` |
| `memelab/predictive/labels.py` | `0cd59ba27f52bf856d05ca0f3ebf74aebb19f2cf3f8548e38a98769ef9131dcb` |
| `memelab/predictive/promotion.py` | `39172a64a144d19f605845d01b60e8853ef6d5ea6c6a11798b7c20c16091c3df` |
| `tests/test_predictive_cm2_guards.py` | `810d7d2710979b4236087e8f12a2c2c93c6762d8652948b9066687a1ecf14df2` |
| `tests/test_predictive_daily.py` | `e016ea04cd8e0cd188dfc33b6df5592521fdf3b7bce6e5e4d3a5fafc2993936f` |
| `tests/test_predictive_promotion.py` | `c2800cad7df34b6e3283af78a1fff4006a2c220ec3712123514a77743969489e` |
| `audits/predictive-intelligence/maintenance/cm2_promotion_cards/raw/` | 7 gzip bodies, each sha256 in `evidence/t2_reads.json` |
