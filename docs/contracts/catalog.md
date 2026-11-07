# Geophysics data and API contracts

This catalogue registers contracts that are already present in the repository. It does not turn a documented SDD capability into an implemented API. The six public pages are defined in `product.json` and `frontend/src/lib/routes.json`; authenticated project and processing routes are described in `docs/data-contract/` and implemented under `app/`. The schemas here formalize only the committed case catalogue and its readiness record. Runtime request and result models remain the versioned Python and TypeScript contracts listed below until their JSON Schema exports are added.

The experiment catalogue is the precomputed public data lane. Its `version` may be newer than `VERSION` while a candidate bake is under review. `data/derived/readiness.json` reports the product version and catalogue version separately. Readiness means files exist with their catalogued lengths and the index says complete; it does not establish scientific validity, rights clearance, measured-field eligibility, API availability, or release acceptance. `scripts/check_artifacts.py` independently checks content hashes and numerical artifact closure.

## Contracts

| id | version | owner | schema file | example | documents | producer test | consumer test | missing-data behavior | provider | model io | swap test | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| experiment-catalog | 2.0.0 | data-pipeline/catalog.py | docs/contracts/schemas/catalog.schema.json | data/derived/v2/catalog.json | data/derived/v2/catalog.json | scripts/check_artifacts.py | frontend/src/test/contract.test.ts | missing: no selectable baked cases; surface an unavailable state | fixture:data/derived/v2/catalog.json | - | tests/test_artifact_contract.py | real |
| data-readiness | 1.0.0 | scripts/check_readiness.py | docs/contracts/schemas/readiness.schema.json | data/derived/readiness.json | data/derived/readiness.json | scripts/check_readiness.py | frontend/src/test/foundation-contracts.test.ts | missing: show readiness unavailable; never infer completeness | fixture:data/derived/readiness.json | - | scripts/check_readiness.py | real |
| private-api | 1.1.0 | app/server.py | docs/contracts/api.openapi.json | - | docs/contracts/api.openapi.json#paths | scripts/check_api_contracts.py | tests/test_api_contract_catalog.py | auth unavailable or owner-scope miss is an explicit error; no fabricated success | fixture:docs/contracts/api.openapi.json | - | tests/test_api_contract_catalog.py | real |
| api-payloads | 1.1.0 | app/schemas.py, app/views.py, app/processing.py | docs/contracts/schemas/api-payloads.schema.json | - | docs/data-contract/*.md | scripts/check_api_contracts.py | tests/test_api_contract_catalog.py | reject invalid wire payloads; method availability and scientific admission remain explicit | fixture:docs/contracts/schemas/api-payloads.schema.json | - | tests/test_api_contract_catalog.py | real |

## History

| contract | version | date | change | kind |
| --- | --- | --- | --- | --- |
| experiment-catalog | 2.0.0 | 2026-10-24 | Register the existing inverse-earth.catalog/v2 wire shape. | initial |
| data-readiness | 1.0.0 | 2026-10-24 | Add a deterministic presence and declared-size summary for the committed catalogue. | initial |
| private-api | 1.0.0 | 2026-10-24 | Record the existing private API boundary and route groups; no API behavior is changed. | initial |
| private-api | 1.1.0 | 2026-10-24 | Add the complete current route/operation inventory, request and response media, auth modes, CSRF and error shapes. No API behavior is changed. | minor |
| api-payloads | 1.0.0 | 2026-10-24 | Export request, response, dataset and scientific result envelope JSON Schema definitions; retain modality-specific runtime validation. | initial |
| api-payloads | 1.1.0 | 2026-10-31 | Add the uploaded-data method eligibility response fields to the exported API payload schema. | minor |

## Existing versioned runtime contracts

These identifiers are defined in executable Python and TypeScript validators. Their versions are part of the payload schema strings; the catalog rows above do not replace them:

| Boundary | Current identifier | Source of truth |
| --- | --- | --- |
| Experiment result | `inverse-earth/v2` | `docs/data-contract/data-contract.md`, `data-pipeline/rebuild.py`, `frontend/src/api/contracts.ts` |
| Source ledger | `inverse-earth.sources/v2` | `data/source-ledger.json`, `docs/data-contract/data-contract.md` |
| Raw asset receipt | `inverse-earth.raw-asset/v1` | `data-pipeline/acquire.py`, `docs/data-contract/data-contract.md` |
| Observation dataset | `geophysics.observation-dataset/v1` | `app/processing_contract.py`, modality adapters under `app/`, `frontend/src/api/` |
| Processing request/result | `geophysics.processing-request/v1`, `geophysics.processing-result/v1` | `app/processing.py`, `app/processing_contract.py`, `frontend/src/api/` |
| Project and authenticated API | Resource-specific Pydantic models and FastAPI routes | `app/projects.py`, `app/processing.py`, `app/auth.py`, `app/schemas.py` |

## API payload inventory and fidelity boundary

`api.openapi.json` lists every operation installed by the default assembly plus the five FastAPI-Users email-mode operations marked `x-registered-when`. `scripts/check_api_contracts.py` compares this set to route decorators and router inclusion sites; it checks every schema reference and representative accepted/rejected payloads. `X-Asset-Metadata` is a JSON header; uploaded scientific bytes are the separate binary request body. ZIP and raw download responses are binary.

### Export gap reconciliation

Before this export, the application already had validators for several payloads, but the repository did not provide their exported JSON Schemas/OpenAPI shapes. The missing export coverage was: project create/update and returned project views; source/physical upload metadata; dataset/job submissions and solver parameter variants; source/asset receipts; dataset receipts and list wrappers; method eligibility; job views and lists; full dataset/result response families; auth config/CSRF/current-user and conditional email-account payloads; structured error bodies; raw file upload/download and ZIP media types. Those route request/response roots are now catalogued in OpenAPI and `api-payloads.schema.json`.

The source validators that existed before the export are the Pydantic types in `app/schemas.py`, `app/views.py`, `app/processing.py`, `app/mt_contract.py`, `app/profile_contract.py`, `app/waveform_contract.py`, and `app/physical_upload.py`, plus the integrity/read validators in their modality modules and TypeScript runtime parsers. A schema being newly exported does not replace those validators.

The remaining nested-schema gaps are specifically: per-row gravity observation/correction arrays; EDI full-tensor and observed-curve arrays plus nested M05/M06 screen, inverse, bootstrap and evaluation trees; profile geometry/QC/engine-report/result trees; waveform submitted-request, channel/QC/descriptor/resource subtrees; and physical gravity history parameter variants and conditional uncertainty fields. They remain checked by the named scientific readers/validators and method documentation, but are not yet fully expressed as JSON Schema. Browser-local FWI, velocity and joint-processing structures are not runtime API payloads and stay outside this API catalogue.

| API wire payload | Export | Executable validation / producer | Fidelity |
| --- | --- | --- | --- |
| Project create/update, source and physical upload metadata, dataset create, method parameters | `schemas/api-payloads.schema.json` | `app/schemas.py`, `app/processing.py`, `app/mt_contract.py`, `app/profile_contract.py`, `app/waveform_contract.py`, `app/physical_upload.py` | Field requirements and bounds exported; runtime validators remain authoritative for cross-field rules, file-format parsing and timezone semantics. |
| Auth config, CSRF, user, project, source/asset receipt and list wrappers | `schemas/api-payloads.schema.json` | `app/auth.py`, `app/security.py`, `app/views.py`, `app/projects.py` | Explicit wire properties exported. Email registration/reset/verify routes are conditional on `auth_mode=email`; local mode has no registration endpoint. |
| Dataset receipt, method eligibility and job/list responses | `schemas/api-payloads.schema.json` | `app/processing.py` | Common response properties exported. `preflight` and immutable request details vary with the selected method. |
| Gravity, EDI and supplied-profile datasets | `ObservationDatasetPayload` in `schemas/api-payloads.schema.json`; tags include `gravity_station`, `edi_transfer_function`, `ert_profile`, `traveltime_profile` | `app/processing_contract.py`, `app/mt_contract.py`, `app/profile_contract.py`; frontend `processing-contracts.ts`, `mt-contracts.ts`, `profile-local-contracts.ts` | Versioned root identity is typed; adapter-specific tensor/profile arrays are still validated by code/docs and are not fully constrained in JSON Schema. |
| Waveform datasets | `WaveformDatasetPayload`; `geophysics.waveform-dataset/v1` | `app/waveform_contract.py`; frontend `waveform-contracts.ts` | Exact root keys, dimensions, modality and receipt identity are described; nested source and submitted scientific request objects remain permissive. |
| Physical gravity root datasets | `PhysicalDatasetPayload`; `geophysics.physical-dataset/v2` carrying `gravity-stations-1` | `app/physical_wire.py`, `app/physical_read.py` | Root identity and structural state are described; detailed gravity history/uncertainty constraints remain enforced by the native structural validator. |
| Gravity flags, MT QC/inversion, supplied-profile solver and waveform results | `ScientificProcessingResult` / `WaveformProcessingResult` in `schemas/api-payloads.schema.json`; tags `geophysics.processing-result/v1` and `geophysics.waveform-result/v1` | `app/compute.py`, `app/mt_compute.py`, `app/profile_contract.py`, `app/waveform_result.py`; frontend modality validators | Method identity and common receipts are typed; several nested numerical output trees remain permissive and are explicitly the outstanding schema-fidelity gap. |
| Binary upload/downloads and ZIP exports | OpenAPI media types | `app/projects.py`, `app/processing.py` | Binary body and media type documented; member schemas are defined by the corresponding archive manifest/data contracts. |

Browser-local FWI, velocity-model and joint-processing contracts do not cross these HTTP routes; they remain in their client-side contract modules and are therefore excluded from this API inventory. `docs/contracts/versions.lock.json` locks hashes of catalogued schema/OpenAPI files. The exported schemas formalize current route payloads and tagged envelope families while preserving existing version tags. They also name the remaining nested scientific schema-fidelity gaps rather than presenting permissive objects as complete scientific schemas.
