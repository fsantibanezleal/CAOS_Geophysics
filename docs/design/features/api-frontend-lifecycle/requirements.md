# Authenticated project/raw frontend requirements

Date: 2026-09-28. Parent: `docs/design/SDD.md` sections 2, 7–9; ADR-0016, ADR-0017, ADR-0044, ADR-0071, ADR-0075. Dependency: merged `docs/design/features/project-raw-api/` and its explicit INT-API-FE-01 gate. This feature is a frontend integration, not a dataset or solver release.

R-FE-API-01 WHEN the frontend reads an owner raw-asset receipt, THE parser SHALL accept only the merged versioned source/asset view, nullable DOI/citation, `private_storage_permission`, and `raw_metadata_checked`; it SHALL neither require nor expose `storage_key`, and SHALL never call this status scientific validity. Gate: `frontend/src/test/api-live-contract-parity.test.ts` against an API-owner-view fixture and `frontend/src/test/foundation-contracts.test.ts`.

R-FE-API-02 WHEN a single-origin API is available, THE App SHALL provide registration, verification by emailed token, login, logout, and account recovery using the API's cookie/CSRF protocol; private controls SHALL require the verified account, while the existing curated guest workbench stays readable. The legacy Pages build SHALL not advertise an unavailable account service. Gate: `frontend/src/test/lifecycle-client.test.ts` and `frontend/e2e/api-lifecycle.spec.ts`.

R-FE-API-03 WHEN an owner creates or lists projects, THE App SHALL show only the API-returned projects and selected project, with no seventh route and no suggestion that a raw project can run a solver. Gate: `frontend/src/test/lifecycle-client.test.ts` and `frontend/e2e/api-lifecycle.spec.ts`.

R-FE-API-04 BEFORE upload, THE App SHALL collect a real local file plus explicit provider, citation/DOI where known, rights statement, rights decision, separate private-storage attestation, attribution, declared format/MIME, CRS/datum/axis order/vertical sign/units/epoch/component frame and format-specific geometry. It SHALL send exact file bytes with byte count and SHA-256 declaration, and show field-specific rejections without recording a success. Gate: `frontend/src/test/upload-metadata.test.ts` and `frontend/e2e/api-lifecycle.spec.ts`.

R-FE-API-05 WHEN a raw upload succeeds, THE App SHALL show the owner receipt, source rights, file hash/size and a download; it SHALL offer project export and confirmed project deletion with the API deletion receipt and backup non-erasure caveat. It SHALL not imply per-asset deletion exists. Gate: `frontend/src/test/lifecycle-client.test.ts` and `frontend/e2e/api-lifecycle.spec.ts`.

R-FE-API-06 IF authentication expires, CSRF fails, rights/metadata is rejected, quota is exceeded, raw integrity fails, or project deletion is refused for backup/recovery state, THEN THE App SHALL preserve unsent user input where possible and display an actionable, non-success explanation. Gate: `frontend/src/test/lifecycle-client.test.ts` and `frontend/e2e/api-lifecycle.spec.ts`.

R-FE-API-07 THE feature SHALL preserve exactly six top-level routes, shared-shell fonts/tokens, usable fixed App viewport, and rendered EN/ES desktop/phone interaction. Gate: `frontend/src/test/foundation-routes.test.ts`, `frontend/src/test/content.test.ts`, and `frontend/e2e/api-lifecycle.spec.ts` screenshot inspection.

Deferred dependencies: public catalogue and rights-cleared guest API entries; observation-dataset QC, processing, methods/jobs/results; backup inventory/purge policy; production single-origin hostname and cutover. No UI claims those are live. The API currently has no individual raw-asset DELETE route, and the frontend shall not invent one.
