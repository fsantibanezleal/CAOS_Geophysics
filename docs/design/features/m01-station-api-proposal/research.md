# M01 station upload/correction API: design-only research

Date: 2026-10-03. Requested after the reviewable local transform unit. This is a proposal for main's coordination, not backend ownership or implementation approval. PR #109 contains the local transform unit; station corrections remain the existing ordinary gravity_processing function. Full M01 and actual field eligibility remain open.

## Repository evidence inspected

The starting develop snapshot 9b0cbe5 has app/formats.py, app/schemas.py, app/processing_contract.py, app/processing.py, app/compute.py and app/worker.py. The existing scientific-looking CSV adapter actually produces geophysics.observation-dataset/v1 with gravity-station-csv/v1 parsing, empty correction history and flag-only verdict. Its method is gravity.station-outlier-flags/v1. app/compute.py explicitly computes reversible statistical flags, not normal/reference/elevation/Bouguer/terrain corrections. Its six-column projected-XY CSV has no automatic equivalence to gravity-stations-1 latitude/longitude/WGS84 physical contracts. That distinction must survive any integration.

The API already has authenticated owner/project/raw/derived identity checks, private storage, quotas, durable jobs and bounded subprocess execution. The proposal reuses those security/lifecycle seams under main ownership, rather than creating independent account/session or worker implementations. MT runtime and ops adapter changes are concurrent and main-owned: re-inspect the converged dispatcher/registry before assigning any backend paths. Current method/host approval cannot be inferred from a flag parser, a transform-local pass or an ops recovery recipe.

## Primary transport/parser references inspected

- [FastAPI request files](https://fastapi.tiangolo.com/tutorial/request-files/): file transport and metadata have explicit multipart semantics; UploadFile is a spooled-file interface, not an automatic scientific validator. Existing bounded upload transport should remain the controlled entrypoint; duplicate physics in an unrelated generic CSV form must not override exact uploaded scientific metadata.
- [FastAPI dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/): reusable dependencies support the existing authenticated-user and owner/project checks. Framework injection does not establish authorization by itself; every asset/dataset/job/result/export needs server-side ownership verification.
- [Python 3.12 JSON documentation](https://docs.python.org/3.12/library/json.html): default JSON decoding accepts repeated object keys and nonfinite constants. Scientific ingestion must explicitly reject both, enforce byte/depth/resource limits and use the existing strict local numeric/schema validation rather than coercing arbitrary JSON into plausible physics.

These official pages were inspected for this design. No claim of a new security audit, measured host benchmark or dependency upgrade is made. Main must verify the actual pinned runtime versions before implementation. Do not extend another agent's environment or add scientific/download work to CI.

## Scientific/API seam

Preserve uploaded exact gravity-stations-1 bytes as immutable private RawAsset with a separately computed transport-byte hash. The scientific metadata.source_sha256 is a supplied source-provenance identity, not the hash of a self-referential JSON file; preserve both instead of requiring a fabricated equality. The dataset's scientific payload stays exactly the existing schema, with independent API identity/version/ownership envelope.

An explicitly allowlisted fixed child adapter invokes process_survey with a bounded reviewed config and the exact parsed scientific payload. It produces a true correction child retaining original observations, known correction history, error model/components, QC and engine/module/config hashes. A CSV flag result never becomes that payload by renaming columns or marking corrections applied.

The transform derivative boundary is separate: metric geometry and fixed-geometry conditional errors are not needed for station reduction and cannot be inferred for a subsequent transform. Unknown raw relative-meter, legacy principal-facts or operational-script variants need their own reviewed parser/physics/engine adapter. Unresolved Bartlett datum, sigma and original lineage remain ineligible. This proposal must not make field eligibility or API host approval true.
