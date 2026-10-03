# M01 ordinary station adapter: scoped convergence and pinned handoff

Date: 2026-10-03. Verdict: all eleven approved adapter-local requirements pass. This is an ordinary scientific seam, not API/storage/registry/worker coverage, actual-host admission, source authentication, eligible Bartlett field modelling or full M01 acceptance. Main independently reviews the final pinned commit before promotion; no merge/deploy occurs here.

Design commit 60f9b2eae7fa86cec8a00fc32fddc27c3c7e13ea was pushed before code. Main read the complete research/design/requirements/tasks and current app contracts, then approved the exact shapes, bounds, safe errors, CPython 3.12/core pin and exact-parent policy. Approval/imported-same-file amendment 15b94da4461993e81c8ced569e8c2613dab4f0b0 was also pushed before implementation. Branch: task/geophysics-m01-station-adapter-sdd, base develop 6050100, after main merged PR #109. No implementation is appended to that merged PR.

## Exact implementation and local verdicts

Only new data-pipeline/gravity_station_adapter.py and new tests/numerics/test_gravity_station_adapter.py implement this feature. The callable accepts the approved six-key native request and returns the approved four-key envelope. It verifies the exact supplied parent/config hashes, preserving integer serialization and complete genuine resume parents, then calls the unchanged real core exactly once. It validates fresh result keys/identities/history/originals/QC/error aggregate semantics and retains the entire core result unchanged. Its receipt binds the full result, submitted and normalized configs separately, exact parent/output, modules/engines and actual fresh runtime. All acceptance declarations stay false.

Before lazy import, the fixed sibling core hash must match the reviewed pin. Preloaded and newly returned module __file__ must identify that same fixed resolved sibling, with lexical rejection of foreign/remote paths before filesystem resolution. Actual core PINS and CPython 3.12.x are checked. This does not authenticate package/runtime origin or protect against a malicious interpreter/live monkeypatch. There is no imported package of our own, dynamic provider code or sys.path change.

Native-object walk rejects custom hooks/subclasses/arrays/bytes/nonfinite/overflow/cycles and the approved bounds before copy/hash/core calls. Canonical encoding is streamed with the actual 16-MiB byte limit. Raw transport parsing and duplicate-key detection remain main-owned; a decoded object cannot reveal keys already discarded by an unsafe decoder. Errors serialize only fixed allowlisted code/field/message/retryable records, never arbitrary exception strings or traceback/context/locals. The adapter prints nothing and reads only its two fixed own module paths for fingerprints; no user-directed writes/network/process/storage/approval actions occur.

| Requirement | Exact new gate | Local verdict |
| --- | --- | --- |
| R-GA01 | test_exact_contract_and_unsupported_inputs | PASS, eight unsupported/extra/missing/method/provider/flag/mask cases |
| R-GA02 | test_bounded_native_request_before_numerics | PASS, eighteen native/hook/cycle/finite/size/depth/node/station controls; no core call |
| R-GA03 | test_exact_input_and_config_identity | PASS, five stale/malformed/source-as-parent controls; separate exact hashes |
| R-GA04 | test_real_core_parity_preserves_request | PASS, three genuine target states, one real call each, exact full result parity and unchanged originals |
| R-GA05 | test_exact_parent_resume_and_no_double_correction | PASS, integer original input and two exact-parent resumes; repeated/backward/changed histories reject |
| R-GA06 | test_formula_sign_and_uncertainty_oracles | PASS, independent published surface/height/plate/unit/sign/geoid/primitive-error formulas; no weakened tolerance |
| R-GA07 | test_uncertainty_kind_and_flags_preserved | PASS, contribution bounds versus SD semantics, primitive zero SD and retained outlier flags |
| R-GA08 | test_safe_errors_do_not_disclose_input | PASS, four core/ordinary exception classes with private markers and no emitted output |
| R-GA09 | test_runtime_and_core_pin_fail_closed | PASS, twelve runtime/pin/file/preloaded/returned-shadow/import/exception-class controls |
| R-GA10 | test_result_receipt_integrity | PASS, twenty-five key/type/hash/config/history/values/errors/QC/acceptance mutations |
| R-GA11 | test_pure_boundary_and_false_acceptance | PASS, complete digests, only fixed own reads, no writes/process/network/log output, deterministic result and false acceptance |

Additional tests: test_exact_station_bounds_without_thinning [1,400], test_missing_physics_never_guessed [7], test_lazy_import_and_system_exit_are_not_relabelled, and test_fresh_lazy_core_real_worked_control. The last test executes the real lazy-loaded core in a fresh isolated Python process against the existing committed authored 12-mGal control, compares the entire core result and checks exact receipt identity. It is not a worker/API lifecycle or field test.

Test-first collection initially failed because the approved new adapter did not yet exist. The first implementation run exposed an authored SI conversion fixture whose current value differed by one floating-point rounding unit from its exact converted original; the core correctly rejected it. The test now supplies that exact canonical current value. No physics tolerance, source field or core rule was changed to make it pass.

## Actual runs and environment

Final full local command:

```powershell
.venv-m01/Scripts/python.exe -m pytest -o addopts='' tests/numerics/test_gravity_station_adapter.py tests/numerics/test_gravity_processing.py tests/numerics/test_gravity_transforms.py tests/data/test_sources.py tests/data/test_ingest_dispatch.py -q --disable-warnings
```

Actual result: **222 passed, 1 skipped in 21.18 s**. The new adapter file has **90 collected/passing cases**. The one existing principal-fact archive negative gate skipped because the main-owned M01_PRINCIPAL_FACT_ARCHIVE environment was not set here. No synthetic substitute was supplied. Main's earlier independently reported 89/no-skip pinned f42d381 review and externalmg-e2fd5764/m01-review.xml remain separately attributed prior-core evidence, not this branch's field-byte execution or adapter coverage.

Ruff check/format pass on both new implementation files; pip check reports no broken requirements. Tracked-content/template/CI-budget and staged diff guards are run before the scoped commit. Tests are local only, no scientific CI/download/requirements changes. Owned unchanged .venv-m01: CPython 3.12.10, Boule 0.5.0, Harmonica 0.7.0, NumPy 2.2.6, SciPy 1.15.2 plus the prior unchanged transform pins. No install or other environment edit occurred.

Exact current bytes:

- New adapter SHA-256: b770b16ef87e83dd92f65a90472145ef93a525a9cedf7f55ee3e6f20f8a10cf8.
- New test SHA-256: ccf5faa9a4b7422b7fadf0ac587dcce3f64a749d02c24168b112df30c73c4268.
- Unchanged core SHA-256: 7863699269b491c2895bcf030d3fb65cf27ac32a652fce91112bc2c7c9c73321.

[Actual local execution receipt](evidence/local-execution.json), generated by the adapter against the existing 1831-byte synthetic station-control.json (SHA-256 11c68ecd3c938591fe705bca95be6a89702f6e92963e371dded4fd837748b052), records output 12.000000000024315 mGal, exact unchanged request and pinned engines/modules. The full adapter envelope digest is 3a454db790e502e92ff35a1db02454379035c88f9b490f313676a61bf40a3174; full core result digest 495b28c748571e219951e9c2b7d46f10ad26cc0f275424f1a8838fc84f90dd6a. The evidence timestamp is outside the deterministic function receipt. Zero protected field bytes were read. One initial shell smoke command had a quoting SyntaxError before any execution; the passing evidence is from the subsequent actual run, not that failed command.

## Exact scope and remaining gates

Changed paths are exactly:

- data-pipeline/gravity_station_adapter.py, new.
- tests/numerics/test_gravity_station_adapter.py, new.
- docs/design/features/m01-gravity-station-adapter/research.md.
- docs/design/features/m01-gravity-station-adapter/requirements.md.
- docs/design/features/m01-gravity-station-adapter/design.md.
- docs/design/features/m01-gravity-station-adapter/tasks.md.
- docs/design/features/m01-gravity-station-adapter/convergence.md, new.
- docs/design/features/m01-gravity-station-adapter/evidence/local-execution.json, new.

No original core, transform, receipts, images, history, source profiles, protected archives, app/shared schema/API/storage/registry/worker/requirements/scripts/existing tests/canonical arrays or release path changed. Existing scientific theory/wiki/rendered images remain unchanged; this ordinary adapter does not add or claim a browser surface.

Main owns independently reviewed pinned promotion, shared API integration after MT convergence, authenticated exact raw transport/owner/source identity, durable correction-child storage/job/export/quotas/cancel/crash behavior and measured actual-host approval. Unknown operational/provider variants need separately reviewed adapters, never a fallback. The author 2929-row principal facts remain unresolved for datum/errors/original lineage; no CSV relabelling, guessed uncertainty or source reinterpretation makes them eligible. Host approval and field/full-M01 acceptance remain false/open respectively. No merge/deploy is performed by this unit.

Review handoff: [PR #119 to develop](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/119), implementation 39f490f410b699c28200884fdda8f2aeff96864d, [named-gate self-review](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/119#issuecomment-5967785698). The final pinned PR head includes this documentation-only handoff, without changing either implementation hash. Main reported full source/test review with no scope fault and confirmed that the receipt has 13 keys as approved; this does not replace main's independent pinned rerun or shared API tests. Additive branch only, no course/builder/shared work merged into this unit. PR checks are not reported as green CI; actual evidence is the local pinned suite and receipts above.
