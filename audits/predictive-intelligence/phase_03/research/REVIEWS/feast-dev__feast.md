# Source review: feast-dev/feast

Reviewer R1, Phase 03. Feast is a feature store, so the model smokes (S2 to S5) do not apply; the review concentrates on its point-in-time (PIT) join against the lab's rule "a feature value may be used only if it was available at or before the decision time" (PLANNED_SEAMS "Point-in-time features", TARGET_REGISTRY). Smoke data are the shared synthetic challenge (`challenge.csv`, sha256 `18fda40cc7a2a6f5aa607a32f1a096976317f901f5b75d1ae23b4bcaddd5f23d`) plus an 8-row hand-built table with known answers.

## 1. Identity

| Item | Value |
|---|---|
| Canonical repo | feast-dev/feast, https://github.com/feast-dev/feast |
| Pinned SHA | `e304a84f979b0f3b828b7c778618d7b7eaa6a2d2` |
| Commit date | 2026-10-19T14:53:15-07:00 ("fix: Populate spec.project in registry REST feature view responses (#7037)") |
| How fetched | `git init; git fetch --depth 1 https://github.com/feast-dev/feast.git <sha>; git checkout FETCH_HEAD` into `/home/claude/pi_research/src/feast-dev__feast` (301 MB) |
| Review time (UTC) | 2026-10-24T04:35Z to 06:05Z |
| Version tested | PyPI `feast==0.67.0` (pure wheel, released 2026-10-13) in `/home/claude/pi_research/venvs/feast-dev__feast` (Python 3.13.17). Not the pin, but `git diff v0.67.0 HEAD` shows `sdk/python/feast/infra/offline_stores/dask.py` unchanged and `feature_store.py` changed by 53 lines that only add PushSource validation; the PIT path tested is the pinned code. The pin itself was not installed (setuptools_scm build that also compiles protobufs) |

## 2. License and security

| Item | Finding |
|---|---|
| Root license | `LICENSE` at the pin: Apache License 2.0 |
| Per-file | MIT grants in docs tutorial files and `sdk/python/feast/infra/registry/contrib/azure/azure_registry_store.py` (Phase 02 LICENSE_SCAN); not used here |
| Dependency footprint | core install: 64 distributions, venv 440 MB, including a server stack (fastapi, starlette, uvicorn with uvloop and websockets, gunicorn), dask, pyarrow 26.0.0, SQLAlchemy 2.1.6 with its mypy extra (pulls mypy 2.4.0), protobuf, prometheus_client, opentelemetry-api, PyJWT. Licenses from installed metadata: Apache-2.0, MIT, BSD (2- and 3-clause), PSF-2.0, and MPL-2.0 for certifi, pathspec and part of tqdm (file-level copyleft, no effect on use) |
| Model weights | none |
| Install scripts | pure wheel, nothing run at install |
| Network | none observed: 0 connect attempts at import (3.1 to 6.4 s), `apply`, and `get_historical_features`. Code that does reach out exists for auth (`permissions/oidc_service.py:31`, `permissions/client/oidc_authentication_client_manager.py:203`) and remote registries or stores, all unused in a local provider |
| Telemetry | none at the pin: no `usage.py`, no `FEAST_USAGE` switch, no usage endpoint in `sdk/python/feast` (OpenTelemetry appears only as optional audit-log trace ids, `audit/audit_logger.py:182-186`) |
| Files written | `registry.db` (feature definitions), `online.db` (sqlite online store) under the repo path given in the config |

## 3. Code paths inspected at the pin

| Area | Anchor | Behaviour |
|---|---|---|
| Public API | `sdk/python/feast/feature_store.py:2007` get_historical_features; `filter_by_created_timestamp=False` default (`:2014`, documented at `:2046-2050`, forwarded at `:2157-2158`); non-entity mode uses `end_date = datetime.now()` when none is given (`:2089-2090`) | |
| Offline store (local) | `sdk/python/feast/infra/offline_stores/dask.py:145` DaskOfflineStore, `:149` get_historical_features, call order `:312` `_merge`, `:320` `_filter_ttl`, `:328` `_apply_created_timestamp_cutoff`, `:338` `_drop_duplicates` | |
| Join | `dask.py:1113` `_merge`: left join of entity rows to every feature row of the same key | |
| PIT and TTL filter | `dask.py:1187-1220` `_filter_ttl`: keeps feature rows with `timestamp <= entity_ts` and, with a TTL, `>= entity_ts - ttl`; rows with a null feature timestamp are kept, but an entity row whose every candidate is filtered out disappears | inclusive `<=` |
| Revision cutoff | `dask.py:1223-1246` `_apply_created_timestamp_cutoff`: blanks (does not drop) versions whose `created_timestamp` is after the entity time; only when `filter_by_created_timestamp=True` | |
| Dedup | `dask.py:1249-1291` `_drop_duplicates`: sort by created then event timestamp, `drop_duplicates(join_keys + [entity_ts], keep="last")` (`:1285`), so two entity rows with the same key and timestamp collapse into one | |
| Store config | `repo_config.py:97-99` offline store types `file` and `dask` both map to DaskOfflineStore; `:173` registry type `file` | |
| Tests | 270 `test_*.py` files under `sdk/python/tests`. Pin tests against the 0.67.0 wheel: `tests/unit/infra/offline_stores/test_dask_non_entity.py` 7 passed, exit 0; `test_filter_by_created_timestamp.py` could not be collected (needs the `ibis` extra), recorded as not run (`SMOKES/feast-dev__feast/repo_tests_subset.txt`) | |

## 4. Smoke results

Script `SMOKES/feast-dev__feast/smoke_feast.py`, output `smoke_output.txt`, run line `smoke_run.txt`: `OMP_NUM_THREADS=1 <venv>/bin/python -I smoke_feast.py challenge.csv <scratch>`, exit 0, wall 4.9 s, peak RSS 242.2 MB. Local provider, dask offline store, sqlite online store, file registry, all in a scratch directory.

Hand-built table (mint A: value 1 at T+1000; value 2 at T+2000 created T+2000; a revision 99 for T+2000 created T+5000. Mint B with the same symbol: 50 at T+1500. TTL 3,600 s):

| Probe (entity time) | Expected under the lab's rule | filter False (default) | filter True |
|---|---|---|---|
| A at T+999 (before any value) | null | row missing from output | row missing |
| A at T+1999 | 1 | 1 | 1 |
| A at T+2000 (exactly at the second value) | 2 (the revision was not known yet) | 99 (late revision used) | 2 |
| A at T+5000 | 99 | 99 | 99 |
| A at T+5601 (beyond TTL) | null | row missing | row missing |
| B at T+2000, same symbol as A | 50 | 50 | 50 |
| A at T+4000, two entity rows with identical key and time | 2 for both | one row (99), the other missing | one row (2), the other missing |

Output row order differed from input order in both modes (callers must re-key).

| Smoke | Result | Numbers |
|---|---|---|
| S1 leak trap through availability time | PASS when the source declares availability time | a feature view on the trap column with `timestamp_field = leak_available_at` (decision + 6 h): 0 of 3,000 rows received their own future value; holdout AUC of the joined value vs the label 0.547 (n 527). The same column declared with `timestamp_field = decision time`: 2,670 rows received their own future value and holdout AUC 1.000. Feast enforces `event_timestamp <= entity time` for whatever column the source names; it cannot know whether that column is availability time |
| Row loss | FAIL | joined to the availability-time view, 330 of 3,000 entity rows vanished from the result: exactly the rows whose mint had only later feature rows (`per_view_row_counts`). The same rows are present with the decision-time views. Rows are dropped, not returned with nulls, and nothing warns |
| Revision leakage (P07) | FAIL by default, PASS with option | see table: default serves a value created after the decision; `filter_by_created_timestamp=True` serves the value known at the time |
| Identity (P01) | PASS | entity key is the mint; the same-symbol mint B kept its own value |
| S2 to S5 | SKIPPED | no model, no probabilities, nothing to persist beyond the registry |
| S6 cost | PASS for batch | 3,000 entity rows joined to three views in 0.51 s; import 3.1 to 6.4 s; 242 MB peak; offline; pure wheel (Windows install not tested; `gunicorn` is excluded on Windows by a marker) |

## 5. Claims the code does not support (P42)

- UNSUPPORTED in the dask (local) offline store: the docstring of `get_historical_features` says a shorter TTL "may result in null values being returned" (`feature_store.py:2026-2028`) and describes enriching the entity dataframe; in the code, entity rows without any valid feature row inside the TTL window are removed, not nulled (`dask.py:1187-1220`, 330 of 3,000 rows in the smoke). Other offline stores were not tested.

## 6. Proposed rubric scores

| Criterion (max) | Score | Evidence |
|---|---:|---|
| Temporal integrity (18) | 10 | Inclusive as-of join with TTL verified to the second; created-timestamp cutoff blocks late revisions when switched on; trap excluded when keyed on availability time. Against it: the default serves late revisions, rows silently vanish (330 of 3,000) and duplicate entity rows collapse, which can bias a replay sample; no label maturity, no splitter |
| Transferable predictive outcomes (14) | 0 | Produces no predictions |
| Calibration and uncertainty (12) | 0 | Not applicable |
| Catalyst, social, on-chain features (10) | 5 | Irregular per-entity event timestamps, mint join keys, per-view TTL, several views joined in one call; catalyst or wallet sources would have to be exported to parquet first |
| Decision and execution compatibility (10) | 0 | Online serving exists but was not tested; no execution hooks |
| Code quality, maintenance, tests (8) | 4 | 270 test files, dask tests pass; daily dev releases; the row-dropping behaviour contradicts its own docstring; one relevant test needs an optional extra |
| Integration fit (8) | 2 | 64 packages and 440 MB including a web server stack for an offline join; registry and online store files; overlaps the planned in-house as-of view instead of filling a missing one |
| Reproducibility and audit (8) | 4 | Deterministic join, versioned feature definitions in `registry.db`; output order not preserved; non-entity mode depends on the wall clock |
| Cost, latency, reliability (5) | 3 | Half a second for 3,000 rows, offline; slow import and heavy install |
| Licensing, security, data rights (7) | 6 | Apache-2.0 verified, permissive dependencies, no telemetry at the pin, network code only in unused auth and remote backends |
| Total | 34 | |

## 7. Flags and adversarial scenarios

- Not LEAKAGE_FAIL: strict as-of retrieval can be configured (source `timestamp_field` = availability time, `created_timestamp_column` = first-known time, `filter_by_created_timestamp=True`), but the defaults leak revisions and must be overridden.
- P07 (vendor backfill revisions): the default returns a value created after the decision; caught by the hand-built probe.
- P36 (feature used after its available_at): enforced only if the declared timestamp is the availability time; the misconfigured view returned the future value for 2,670 rows.
- P09 and P47 style coverage loss: silent removal of entity rows would shrink a replay sample without a count warning; a wrapper must assert rows out = rows in.
- P01: identity by mint holds.
- P42: the TTL docstring claim above.

## 8. Proposed role and integration decision

- Role: a reference oracle for the lab's own as-of view in Phase 05, not a dependency. Its semantics worth copying: inclusive `available_at <= decision_time`, per-source TTL, and a separate first-known (created) timestamp that blocks revisions. Its behaviours to avoid: silent row removal, duplicate-row collapse, revision leakage by default. A Phase 05 test can feed the same parquet tables to both and require identical values plus explicit nulls where Feast drops rows.
- INTEGRATION_DECISION: INSPIRED_IMPLEMENTATION (no install in the lab; keep the 0.67.0 venv only as an offline comparator).
- Gap cells addressed: HIST_MARKET:POINT_IN_TIME_FEATURES, REGIME_NARRATIVE:POINT_IN_TIME_FEATURES (N06). The MODEL_REGISTRY cells listed for it in Phase 02 are not served: Feast's registry holds feature definitions, not model artifacts, training cutoffs or metrics (N10 not met).
