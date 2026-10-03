# M01 ordinary station adapter: pre-code research and evidence

Date: 2026-10-03. This pre-code dossier was persisted in 60f9b2e before main's feature-contract review. Main subsequently approved the boundary, with an imported same-file/preloaded-shadow condition, before code. This dossier narrows the existing [station API proposal](../m01-station-api-proposal/design.md) to one ordinary local adapter and its unit tests. The parent product SDD is approved. No API, storage or worker implementation is included.

## Authority, baseline and direct repository evidence

The user assigned only prospective data-pipeline/gravity_station_adapter.py and tests/numerics/test_gravity_station_adapter.py. Main retains shared API/schema/storage/registry/worker/requirements and coordinated MT integration. ADR-0069 requires real pinned engine execution, independent physical controls and honest acceptance limits; ADR-0075 requires this feature design to be reviewed before code. The approved product SDD sections 2, 3, 4 and 9 govern M01 and R-003/R-004/R-006/R-009/R-011; adapter-local gates cannot close the integrated requirements.

Owned worktree: D:/_worktrees/geophysics-m01-corrections. Documentation-only branch: task/geophysics-m01-station-adapter-sdd. Base: origin/develop 6050100aeb3d1d482eefa1856ac67b2bc04b5bb1, which contains PR #109 merged at 66b3d52 and the reviewed transform fix f42d3816d2fb094ee81102dd0f39e65367fd29d4. No change is appended to the merged transform branch.

The approved scientific source is data-pipeline/gravity_processing.py, SHA-256 7863699269b491c2895bcf030d3fb65cf27ac32a652fce91112bc2c7c9c73321. Its process_survey(dataset, config) validates strict station/metadata/history keys, finite physics, units/sign, WGS84/height/geoid/instrument declarations, stage order, hashes and prior parameters. It requires explicit density and density SD for plate/terrain targets, refuses backward/repeated corrections and preserves original station values and supplied source lineage. Normal/reference/elevation/plate/residual operations are actual Boule/Harmonica calls, not CSV flags. Its output has exact dataset, processing and qc objects; processing contains no generated timestamp. Conservative marginal contributions are bounds, not covariance or standard deviations.

The existing core accepts 1..10000 stations; a proposed adapter ceiling of 1..400 is a separate reviewed boundary, not a scientific-core edit or measured online limit. The correction schema has no mask/metric XY/transform configuration/job/owner fields. The new adapter must not insert those keys, drop flagged stations or infer projected/geographic equivalence. Its prospective caller supplies the complete exact parent dataset, so its parent hash can be checked directly, without the transform's bounded earlier-state reconstruction policy. Original numeric serialization such as integer current observations must not be rewritten merely to fit a reconstructed hash.

Existing independent tests/numerics/test_gravity_processing.py includes published Somigliana/normal-field controls, plate/sign/unit controls, orthometric/geoid/error propagation, terrain dependence, strict metadata/state negatives and the exact product gate test_station_correction_lineage. Existing station-control.json is explicitly authored and synthetic. Adapter tests must call the real core and reuse its declared physics and independent formula tolerances; mocked rejection spies alone are not positive evidence.

The owned isolated .venv-m01 remains unchanged: CPython 3.12.10, Boule 0.5.0, Harmonica 0.7.0, NumPy 2.2.6 and SciPy 1.15.2, with the already pinned transform dependencies. pip check on 2026-10-03 reports no broken requirements. No environment installation, requirements edit or scientific execution gate is added by this documentation unit.

## Independent review evidence versus field acceptance

Main reported an independent pinned f42d381 rerun: 89 passed, no skips, 22.57 s, including the actual author ZIP supplied through the existing environment gate. Main's external receipt identifier is externalmg-e2fd5764/m01-review.xml. This is explicitly main-reported evidence; this unit did not open, copy, hash or independently inspect that external receipt or the protected archive. The archive test is negative physical admission, not eligible field modelling, source reinterpretation or a full-M01 verdict. Original transform receipts, images, history and gravity_processing.py stay unchanged.

Bartlett author principal facts remain unresolved for datum, primitive errors and original correction lineage. A CSV with OG/FAA/SBA/TTC/CBA/ISO does not become gravity-stations-1 by relabelling. No parser, field convenience subset, guessed sigma, projection or instrument reduction belongs in this adapter.

## Primary references checked for this narrow design

[Python 3.12 JSON documentation](https://docs.python.org/3.12/library/json.html) supports explicit native-type/finite-number/circular/size validation. Default JSON handling is not sufficient for strict scientific transport: repeated keys and nonfinite constants require explicit rejection. The ordinary adapter receives an already strictly decoded object; raw-byte parsing, duplicate-key checks and transport-byte receipts remain main-owned. It checks bounded object structure before copying/hashing; that cannot retroactively detect duplicates lost by an unsafe decoder.

[Python 3.12 exception documentation](https://docs.python.org/3.12/library/exceptions.html) distinguishes safe displayed messages from retained exception context. Suppressing chaining alone does not remove an original exception from introspection. The adapter error contract therefore exposes only fixed code/field/message/retryable values and never serializes raw exception arguments/context/tracebacks. Main must not serialize traceback locals or arbitrary exception attributes into API/log records. System-exiting exceptions are not converted into a successful or retryable scientific response.

[Pinned Boule normal gravity](https://www.fatiando.org/boule/v0.5.0/user_guide/normal_gravity.html) supports the core's height-aware normal field; adding another empirical free-air term would duplicate that height dependence. [Pinned Harmonica Bouguer correction](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.bouguer_correction.html) defines the plate effect and its ellipsoidal-height/metre, density and mGal semantics. The adapter does not replace these algorithms, infer a terrain model or introduce curvature/isostatic/raw-instrument operations.

Actual public-document byte receipts, fetched with PowerShell only into memory on 2026-10-03:

| Official document | HTTP | Bytes | SHA-256 | Retrieved UTC |
| --- | ---: | ---: | --- | --- |
| Python 3.12 JSON, linked above | 200 | 107891 | 1a5e4ba18342b32f5f174d129f9c226a21a9445a89384f13a3f33ec327c2b68f | 08:50:32.5774760Z |
| Python 3.12 exceptions, linked above | 200 | 139853 | d4f18fa368d9b84e07a2d888686cacc9d6164f7587793dca6056d5f2c17e7905 | 08:50:32.8275919Z |
| Harmonica 0.7.0 plate API, linked above | 200 | 36170 | 602224789f53b724416d04c41c86d0b50693409992d03d50f21f838f1f11e5a3 | 08:50:33.3659850Z |
| Boule 0.5.0 normal-field guide, linked above | 200 | 72969 | 1f3efd89115714649e18d562d45f3a607aa1a367467221c48948db817b1a0af1 | 08:50:57.9537965Z |

A guessed Boule generated-method URL failed both browser access and direct fetch before the verified guide was used. The failed URL is not evidence. These are documentation snapshots, not package upgrade advice, physics benchmark receipts or protected provider acquisition. No official HTML or source/archive bytes are committed.

## Design consequences requiring main review

Use one explicitly versioned plain-dict request/result boundary, not app schemas or a generic modality fallback. Carry dataset/config integrity hashes separately from supplied source identity; raw byte, owner, job, attempt and storage identities remain outside this scientific boundary. Invoke the exact pinned core once on an unchanged deep copy and validate fresh output receipt invariants without creating a second correction stage. Preserve full core errors/warnings/error-kind arrays privately inside a successful result; expose fixed safe error records on failure. Declare host/full-method/field-source acceptance false in the adapter receipt; successful local reduction is not online authorization. Main must approve the proposed shapes, limits and safe-error mapping before the two new implementation files are created.
