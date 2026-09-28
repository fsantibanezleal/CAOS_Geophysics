# Frontend foundation requirements

Authority: approved product SDD, 2026-09-27, sections 2, 3, 7 and R-012/R-015. This unit establishes the shell, routing and evidence boundary for the future single-origin platform. The existing 0.04.001 static release remains the live application. No API operation is activated by this unit.

R-FF01 THE frontend SHALL define exactly App `/`, Introduction `/introduction`, Methodology `/methodology`, Implementation `/implementation`, Experiments `/experiments` and Benchmark `/benchmark` in one ordered route manifest consumed by the shell, router and legacy static entrypoint generator. Gate: `frontend/src/test/foundation-routes.test.ts::six_routes_share_one_manifest` and `frontend/scripts/qa-foundation.mjs::pointer_navigation`.

R-FF02 WHILE the legacy deployment mode is selected, THE frontend SHALL retain current root and `/CAOS_Geophysics` navigation and artifact URLs; WHEN the explicit single-origin build mode is selected, THE frontend SHALL use root-relative routes and assets without a Pages basename. Gate: `frontend/src/test/foundation-routes.test.ts::deployment_modes_preserve_legacy_and_target_paths` and `frontend/scripts/qa-foundation.mjs::direct_routes_and_assets`.

R-FF03 THE frontend SHALL mirror the approved source, raw asset, observation dataset, processing run, solver job and result artifact identity, rights, units, axes, geometry, lineage, state and hash fields with TypeScript types and boundary checks. IF a payload has an invalid hash, ambiguous physical coordinate/unit, incompatible array shape, synthetic truth on a field result or missing provenance, THEN THE contract parser SHALL reject it. Gate: `frontend/src/test/foundation-contracts.test.ts::rejects_invalid_evidence` and `::accepts_valid_contract_records`.

R-FF04 WHEN the future API client requests JSON, THE client SHALL use same-origin `/api/` paths, same-origin credentials, abort signals and explicit error responses. IF a caller supplies a remote or escaping URL, an unexpected content type or a failed status, THEN THE client SHALL fail without manufacturing a success payload. Unsafe requests require a supplied CSRF token. Gate: `frontend/src/test/foundation-api-client.test.ts::same_origin_transport_and_errors` and `::unsafe_request_requires_csrf`.

R-FF05 THE shell SHALL use the published shared package for header, footer, EN/ES, theme, tabs, citations and architecture modal, with no product font or palette override. Gate: `frontend/src/test/foundation-routes.test.ts::shell_tokens_and_chrome_are_centralized` and `frontend/scripts/qa-foundation.mjs::render_matrix`.

R-FF06 THE five architecture diagrams and their modal explanations SHALL describe the approved target as planned and identify the 0.04.001 static release as live, including the one-origin API/worker boundary, offline/GPU and replay lanes, M13 parity gate, rights-aware contracts and Clear Lake QC-only verdict. Gate: `frontend/src/test/foundation-architecture.test.ts::target_is_distinct_from_live_release` and `frontend/scripts/qa-architecture.mjs` in EN/ES and light/dark.

R-FF07 THE foundation SHALL preserve existing scientific figures, EDI screen logic and released artifact loading while leaving absent backend operations undiscoverable as runnable UI. Gate: `frontend/src/test/edi.test.ts`, `frontend/src/test/contract.test.ts`, `frontend/src/test/foundation-routes.test.ts::no_unreleased_operation_route` and `frontend/scripts/qa-foundation.mjs::render_matrix`.

R-FF08 WHEN local desktop or phone navigation opens any of the six routes, THE shared shell SHALL render usable content and the architecture modal without a browser error or document-level horizontal overflow. Gate: `frontend/scripts/qa-foundation.mjs::render_matrix`, `::pointer_navigation` and `frontend/scripts/qa-architecture.mjs`.

R-FF09 THE change SHALL remain limited to `frontend/` and `docs/design/features/frontend-foundation/`, and SHALL leave backend, data pipeline, hosts and deployment untouched. Gate: `git diff --name-only origin/develop...HEAD` scope audit before push.
