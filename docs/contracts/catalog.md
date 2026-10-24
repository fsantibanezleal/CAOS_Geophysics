# Geophysics data and API contracts

This catalogue registers contracts that are already present in the repository. It does not turn a documented SDD capability into an implemented API. The six public pages are defined in `product.json` and `frontend/src/lib/routes.json`; authenticated project and processing routes are described in `docs/data-contract/` and implemented under `app/`. The schemas here formalize only the committed case catalogue and its readiness record. Runtime request and result models remain the versioned Python and TypeScript contracts listed below until their JSON Schema exports are added.

The experiment catalogue is the precomputed public data lane. Its `version` may be newer than `VERSION` while a candidate bake is under review. `data/derived/readiness.json` reports the product version and catalogue version separately. Readiness means files exist with their catalogued lengths and the index says complete; it does not establish scientific validity, rights clearance, measured-field eligibility, API availability, or release acceptance. `scripts/check_artifacts.py` independently checks content hashes and numerical artifact closure.

## Contracts

| id | version | owner | schema file | example | documents | producer test | consumer test | missing-data behavior | provider | model io | swap test | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| experiment-catalog | 2.0.0 | data-pipeline/catalog.py | docs/contracts/schemas/catalog.schema.json | data/derived/v2/catalog.json | data/derived/v2/catalog.json | scripts/check_artifacts.py | frontend/src/test/contract.test.ts | missing: no selectable baked cases; surface an unavailable state | fixture:data/derived/v2/catalog.json | - | tests/test_artifact_contract.py | real |
| data-readiness | 1.0.0 | scripts/check_readiness.py | docs/contracts/schemas/readiness.schema.json | data/derived/readiness.json | data/derived/readiness.json | scripts/check_readiness.py | frontend/src/test/foundation-contracts.test.ts | missing: show readiness unavailable; never infer completeness | fixture:data/derived/readiness.json | - | scripts/check_readiness.py | real |
| private-api | 1.0.0 | app/server.py | docs/contracts/api.openapi.json | - | - | tests/api/test_projects.py | frontend/src/test/api-live-contract-parity.test.ts | API disabled or unavailable is an explicit error; no fabricated success | fixture:docs/contracts/api.openapi.json | - | tests/api/test_frontend_contract_fixture.py | real |

## History

| contract | version | date | change | kind |
| --- | --- | --- | --- | --- |
| experiment-catalog | 2.0.0 | 2026-10-24 | Register the existing inverse-earth.catalog/v2 wire shape. | initial |
| data-readiness | 1.0.0 | 2026-10-24 | Add a deterministic presence and declared-size summary for the committed catalogue. | initial |
| private-api | 1.0.0 | 2026-10-24 | Record the existing private API boundary and route groups; no API behavior is changed. | initial |

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

`docs/contracts/versions.lock.json` locks the hashes of the checked-in JSON Schema/OpenAPI files. It is not a claim that every runtime payload has already been exported as JSON Schema. New schema exports must preserve the existing payload versions and receive their own contract rows before becoming canonical.
