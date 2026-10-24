# Source review: PriorLabs/TabPFN

Reviewer R1, Phase 03. Smoke data are the shared synthetic challenge (`challenge.csv`, sha256 `18fda40cc7a2a6f5aa607a32f1a096976317f901f5b75d1ae23b4bcaddd5f23d`): format and behaviour only, never memecoin predictive value. Holdout scored rows 527 (17 positives), 107 censored rows excluded, training prevalence B0 = 0.04238.

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | PriorLabs/TabPFN, https://github.com/PriorLabs/TabPFN |
| Pinned SHA | `9d9d8725168810e5f9de76bc68e0d4d6688ae26f` |
| Commit date | 2026-10-21T16:39:33+00:00 ("fix(deps): stop trusting the compromised eMudhra CAs (certifi, uv, pip) (#1377)") |
| How fetched | `git init; git fetch --depth 1 https://github.com/PriorLabs/TabPFN.git <sha>; git checkout FETCH_HEAD` into `/home/claude/pi_research/src/PriorLabs__TabPFN` (9.3 MB) |
| Review time (UTC) | 2026-10-24T04:38Z to 06:00Z |
| Version tested | the pin: `uv pip install <clone>` (setuptools build backend, `pyproject.toml` only, no `setup.py`) into `/home/claude/pi_research/venvs/PriorLabs__TabPFN` (Python 3.13.17) with `torch 2.14.1+cpu` from `download.pytorch.org/whl/cpu`. All 91 installed `.py` files are byte-identical to `src/tabpfn` at the pin. `pyproject.toml` version `9.2.0` (PyPI 9.2.0 was released 2026-10-12; the pin carries five unreleased changelog fragments in `changelog/`) |
| Cleanup | the venv (947 MB on disk) and the weight cache were deleted after the smokes; the clone at the pin is kept; reinstall with the commands above and re-fetch with `tabpfn_fetch_v2.py`, then check the sha256 below |
| Weights tested | TabPFN-2 classifier `tabpfn-v2-classifier-finetuned-zk73skhh.ckpt` from Hugging Face repo `Prior-Labs/TabPFN-v2-clf`, fetched by TabPFN's own `download_model` (`SMOKES/PriorLabs__TabPFN/tabpfn_fetch_v2.py`, exit 0, 29,009,539 bytes, sha256 `cf8c519c01eaf1613ee91239006d57b1c806ff5f23ac1aeb1315ba1015210e49`). The default TabPFN-3.5 weights were NOT fetched (license terms below; no token or account was used) |

## 2. License and security

| Item | Finding |
|---|---|
| Code license | `LICENSE` at the pin: Apache-2.0; `NOTICE` "Copyright (c) 2026 Prior Labs GmbH"; `THIRD-PARTY-NOTICES.md` lists two files adapted from skrub (BSD-3-Clause) |
| Default weights | `settings.py:37-40` default `model_version = V3_5`. Hugging Face `Prior-Labs/tabpfn_3_5` card license `tabpfn-3-5-license-v1.0`; LICENSE read from `https://huggingface.co/Prior-Labs/tabpfn_3_5/resolve/main/LICENSE` (16,905 bytes, sha256 `9570fdd6...`): "freely available for your non-commercial and non-production use"; acceptance by downloading; "not available to consumers within the meaning of Section 13 of the German Civil Code (BGB)"; 1.c Non-Commercial Purpose excludes use "tied to commercial gain" and results "used in commercial decision-making"; 2.d Outputs "may be used only for Non-Commercial Purposes"; 3.d no hosted service. TabPFN-2.5, 2.6 and 3 weights carry their own non-commercial licenses per README `:113` (card ids `tabpfn-2.5-license-v1.1`, `tabpfn-2.6-license-v1.0`, `tabpfn-3-license-v1.0`; texts not read) |
| TabPFN-2 weights | Prior Labs License v1.1 (Apache-2.0 plus Paragraph 10), `https://huggingface.co/Prior-Labs/TabPFN-v2-clf/resolve/main/LICENSE.txt` (11,483 bytes, sha256 `08b1851b...`): if the weights or a product containing them are distributed, include the license and display "Built with PriorLabs-TabPFN"; "internal benchmarking and testing without external communication" needs no attribution |
| License gate | client-side: `model_loading.py:557-571` calls `browser_auth.ensure_license_accepted` for v2.5, 2.6, 3, 3.5 and 3.5-fast; it verifies a token at `https://api.priorlabs.ai` (`settings.py:43-50`, `browser_auth.py:155-170`) and caches it in `~/.cache/tabpfn/auth_token` (`browser_auth.py:110`), also reading `TABPFN_TOKEN` and `~/.tabpfn/token` (`:116-135`). The Hugging Face API reports `gated: false` for all five weight repos, so the gate lives in this client |
| Network at runtime | first use downloads weights from Hugging Face (`model_loading.py:267-345`, `hf_hub_download` with no `revision`, so the `main` branch is fetched and weights are not pinned to a revision), with a fallback for v2 at `https://storage.googleapis.com/tabpfn-v2-model-files/05152025` (`:63`). It also downloads `config.json` "only to increment the download counter" and deletes it (`:330-341`). With the guard on, the default constructor made 1 connect attempt (to the local proxy) and failed; v2 fit and predict from the cache made 0 attempts |
| Telemetry | no analytics code at the pin (no posthog or telemetry module; the CHANGELOG records anonymous usage analytics added in 2.1.4 and later releases, gone from `src/` at the pin); the download-counter call above remains |
| Settings | `settings.py:28` reads a `.env` file from the current working directory for any `TABPFN_` variable |
| Weight file safety | `.ckpt` checkpoints load with `torch.load(..., weights_only=None)` (`checkpoint.py:73`; the comment says they "rely on the legacy behavior"); `.safetensors` (3.5) load through `safe_open` (`checkpoint.py:55-64`) |
| Fitted model format | `save_fitted_tabpfn_model` (`model_loading.py:1363`): zip of `init_params.json` plus `joblib` files (pickle, code execution on load) |
| Install footprint | venv 1.2 GB (torch CPU 780 MB), deps include huggingface-hub, lightgbm, skrub, matplotlib, pydantic-settings |

## 3. Code paths inspected at the pin

| Area | Anchor |
|---|---|
| Estimator | `src/tabpfn/classifier.py:141` TabPFNClassifier, `:255` `__init__` (`n_estimators="auto"`, `softmax_temperature`, `balance_probabilities`, `ignore_pretraining_limits`, `fit_mode`, `random_state=0`), `:620` `create_default_for_version`, `:959` fit, `:1712` predict_proba, `:2114` save_fit_state |
| CPU guard | `src/tabpfn/validation.py:130` `max_cpu_samples=1000`: more than 1,000 training rows on CPU raises unless `ignore_pretraining_limits=True` or `TABPFN_ALLOW_CPU_LARGE_DATASET=1` |
| Weights resolution | `src/tabpfn/model_loading.py:86-104` v2 classifier files, `:237` `_get_model_source`, `:463` get_cache_dir (`TABPFN_MODEL_CACHE_DIR`), `:517` download_model |
| Time handling | none: an in-context learner; whatever rows are passed to `fit` are the context |
| Calibration | none post hoc; `softmax_temperature` (resolved 0.9 for v2) and `balance_probabilities` are output transforms |
| Tests | 86 `test_*.py` files under `tests/`. Offline subset at the pin: `test_browser_auth.py test_validation.py test_checkpoint.py test_settings.py`: 72 passed, 1 skipped, exit 0 (`SMOKES/PriorLabs__TabPFN/repo_tests_subset.txt`) |

## 4. Smoke results

Script `SMOKES/PriorLabs__TabPFN/smoke_tabpfn.py`, output `smoke_output.txt`, run line `smoke_run.txt`: `TABPFN_MODEL_CACHE_DIR=<scratch> TABPFN_NO_BROWSER=1 python -I smoke_tabpfn.py ...`, exit 0, wall 235.8 s, peak RSS 995.6 MB, torch 2 threads. A first attempt with a larger plan was stopped by the 10-minute tool limit (no output kept); the plan was cut (determinism and persistence checked on 100 holdout rows, 5 single-row timings).

| Smoke | Result | Numbers |
|---|---|---|
| Default weights offline | FAIL (needs network and license login) | `TabPFNClassifier()` with the network guard: `TabPFNHuggingFaceGatedRepoError: HuggingFace authentication error downloading from 'Prior-Labs/tabpfn_3_5'. This model is gated...` after 1 blocked connect. The message names gating although the cause was the blocked network |
| CPU size guard | as documented | 1,746 training rows: `RuntimeError: Running on CPU with more than 1000 samples is not allowed by default`; the lab's 100 to 300 events are under the limit |
| S1 leak trap | FAIL (library stops nothing) | v2, 1,746-row context: BSS 0.0115, AUC 0.669 without the trap; BSS 0.9678, AUC 1.000 with it |
| S2 probability shape | PASS | shape (527, 2), rows sum to 1, finite, in [0, 1]; Brier 0.030960 vs B0 0.031320, log loss 0.1385 vs 0.1439; `n_estimators` resolved to 8 |
| Small N (300 rows, 13 positives) | PASS vs base rate | BSS 0.0013, AUC 0.658 (the only model in this reviewer's set not worse than B0 at 300 rows; the difference is within noise at 17 holdout events) |
| S3 missing covariates | PASS | 252 training rows with NaN, native handling, finite output |
| S4 calibration | PARTIAL | raw v2 probabilities 3 of 3 quantile bins inside the Wilson 95% interval; `balance_probabilities=True` moved mean p to 0.355 (BSS -3.87); no interval or abstention for classification |
| S5 persistence | PASS within 6e-8 | `save_fit_state` 998,225 bytes, reload max abs diff 5.96e-08 on 100 rows (not bit-identical); pickle 30.6 MB (embeds weights), not bit-identical either |
| Determinism | PASS within 6e-8 | same seed twice: max abs diff 5.96e-08 (float32), not bit-identical |
| S6 cost | FAIL for real-time | fit 0.96 s (no training), predict 527 rows 32.6 s (62 ms per row); single row 17.5 s median (`fit_preprocessors`), 0.27 s with `fit_mode="fit_with_cache"`; RSS 996 MB; first use needs the network; Python 3.13 works; Windows: pure wheel, torch has `cp313-win_amd64` |

## 5. Claims the code does not support (P42)

- README `:253` and the license prompts say "TabPFN works offline once the weights are downloaded": true for v2 in this test (0 connect attempts after the cache was filled), not tested for the gated versions, whose first use requires the PriorLabs token check.
- README `:10` says the model "trains on synthetic datasets": not verifiable from the code (pretraining is not in the repo); UNSUPPORTED for scoring, so no credit was given for absence of pretraining contamination (P26).

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity (18) | 1 | The context passed to `fit` is the only data a prediction uses, so a training cutoff is explicit and auditable; nothing else: no splitter, no availability concept, leak passed through (BSS 0.9678), pretraining data UNKNOWN |
| Transferable predictive outcomes (14) | 7 | Binary probabilities with correct shape; not worse than base rate at 300 rows; regression exists; no survival |
| Calibration and uncertainty (12) | 3 | Raw probabilities inside Wilson bins on this fixture; `balance_probabilities` breaks calibration; no interval, conformal or abstention for classification |
| Catalyst, social, on-chain features (10) | 2 | Native NaN, up to 500 features (`inference_config.py:343`); nothing time- or event-aware |
| Decision and execution compatibility (10) | 0 | No hooks found (no sample weights, no cost-aware options) |
| Code quality, maintenance, tests (8) | 4 | 86 test files, offline subset passes; very active, but frequent major versions (8.4.0 on 2026-08-19 to 9.2.0 on 2026-10-12) and a default model that changes across versions |
| Integration fit (8) | 2 | 1.2 GB environment for CPU, weights download on first use, license token flow, CPU guard above 1,000 rows, `.env` read from cwd |
| Reproducibility and audit (8) | 3 | Seeded but only reproducible to 6e-8; weights fetched from the `main` revision (not pinned), so the lab must pin by sha256; fitted state is a pickle zip |
| Cost, latency, reliability (5) | 1 | 62 ms per row in batch, 17.5 s single row without cache, 0.27 s with cache, 1 GB RAM |
| Licensing, security, data rights (7) | 2 | Code Apache-2.0; default and all newer weights non-commercial and non-production, outputs restricted, consumers excluded; only TabPFN-2 weights fit the lab (Apache-2.0 plus attribution); `.ckpt` loaded through `torch.load` legacy mode; download counter call |
| Total | 25 | |

## 7. Flags and adversarial scenarios

- REJECT for the default TabPFN-3.5 weights and any 2.5, 2.6 or 3 weights: their terms do not permit use of outputs in trading decisions, and the 3.5 license is not available to an individual acting as a consumer. Accepting them would be a legal agreement on Elving's behalf (not approved, PI-D-005 scope).
- RESEARCH_ONLY with TabPFN-2 weights (pinned by sha256 `cf8c519c...`, cache dir set, network blocked after the fetch).
- NOT_REALTIME on CPU: 17.5 s per single prediction without the cache mode; 0.27 s with it.
- P26: pretraining data cannot be inspected; a contamination claim either way is UNKNOWN.
- P31: weight license is separate from the code license; the Phase 02 flags NONCOMMERCIAL_WEIGHTS and WEIGHTS_REQUIRE_LICENSE_LOGIN are confirmed.
- P32: weights are fetched from `main` at run time; a changed upstream file would change the model silently unless the sha256 is checked.

## 8. Proposed role and integration decision

- Role: an offline small-N comparator in Phase 08 research only, with TabPFN-2 weights, at the lab's 100 to 300 events (inside the CPU guard), scored like any other model against B0 and B2. Never the default weights; never in the scout path.
- INTEGRATION_DECISION: ISOLATED_RESEARCH (separate venv, `TABPFN_MODEL_CACHE_DIR` set, weights checked by sha256, network blocked after the one fetch, `TABPFN_NO_BROWSER=1`, no token).
- Gap cells addressed: DECISION_RECORDS:MODEL_TRAINING, HIST_MARKET:MODEL_TRAINING (N01), research only.
