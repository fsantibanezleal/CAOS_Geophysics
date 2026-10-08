# M04 owned leaf and owner mount proposal

This contract supplies executable numeric projection, surveyed-input custody
and scientific views. It does not activate shared API routes, worker or frontend root.
No new authentication, server, default field metadata or persistence authority.
The API owner integrates against its CURRENT branch, not this older foundation.
`app.magnetic_results.validate_owned_magnetic_result` is an executable ownership,
state and durable-receipt guard for the proposed local method ID. It is NOT
registered in the service method allow-list or routes. Existing result byte
verification must run first. Actual dataset/import/read/export functions are now
`app.magnetic_contract` and `app.magnetic_custody`; the shared dispatcher must
bind them to its existing auth/project/CSRF/storage lifecycle. Focused portable
negative tests are not a mounted two-account HTTP or native-host claim.

## Executable protected owner ABI

The canonical parser version is `mag-survey/v1:<full lexical request SHA256>`.
The dataset create union accepts an exact `magnetic_request_utf8` string for an
owned `magnetic_csv` asset, not a JSON object rebuilt from JavaScript numbers.
The method ID is `magnetic.survey-l2-irls-local/v1`. Every public custody function
requires the URL's selected `project_id`, even for another project of one owner.

```python
from app.magnetic_contract import magnetic_dataset_receipt, refuse_online_submission
from app.magnetic_custody import (
    install_dataset, install_replay, read_dataset, read_method, read_replay,
    exact_zip_inventory,
)

# Existing verified authenticated user and CSRF middleware are unchanged.
# Authentication may already hold a read transaction. Writers use an existing
# fresh session from the application's session factory, not BEGIN inside it.
async with app.state.sessions() as owned_session:
    dataset = await install_dataset(
        owned_session, settings, user, asset_id, request_utf8.encode("utf-8"),
        project_id=project_id,
    )
    receipt = magnetic_dataset_receipt(dataset)

# This is a local replay import, NEVER an online queued inverse. The owner
# resolves checked_private_generation through its own staging boundary;
# a browser-supplied filesystem path is not accepted authority.
async with app.state.sessions() as owned_session:
    job = await install_replay(
        owned_session, settings, user, dataset_id, checked_private_generation,
        project_id=project_id, temp_root=configured_external_scratch,
    )

# Existing read session, after current authenticated owner resolution.
payload = await read_dataset(session, settings, user, dataset_id, project_id=project_id)
mapping = await read_method(session, settings, user, dataset_id, project_id=project_id)
view = await read_replay(session, settings, user, job_id,
                         project_id=project_id, temp_root=configured_external_scratch)
zip_bytes = await read_replay(session, settings, user, job_id,
                              project_id=project_id, temp_root=configured_external_scratch,
                              export=True)
# Only after that full owned validation, the existing restart/delete dispatcher
# may use the exact single ZIP descriptor. It must still retain its own held-path
# checks, transaction/lease and original-preserving cleanup protocol.
descriptor = exact_zip_inventory(settings, job)

# An attempted online method submission refuses; it does not queue a replay.
refuse_online_submission()
```

Existing `/datasets/<id>` returns the revalidated lexical dataset; `/methods`
returns the closed magnetic-owned-method-1 mapping for this modality. Existing
job views retain `_job_view` shape and successful result URL. `/result` returns
the newly verified projection; `/export` returns the exact ZIP with no-store and
a numeric-ZIP download media type. The browser `MagneticProcessingApi` uses those
same-origin routes and authenticates selected receipt bindings before display.
It does not invent an import endpoint or an online method allow-list.

Before mounting, the owner assembly must add magnetic parser/receipt dispatch
for list/read/create, explicit local import, request/preflight/job validation,
single-ZIP quota/result handling, startup reconciliation, export and deletion.
The ordinary gravity JSON result validator is NOT a magnetic ZIP validator.
Controller union changes and actual two-account HTTP/restart/delete/native
queue gates remain distinct from these portable implementation controls.

## Required existing-owner sequence

1. Resolve current authenticated account, owned project, immutable dataset and
   owned processing job using the existing dependencies and owner predicates.
   Unknown and cross-owner IDs retain the same non-disclosing404 response.
2. Require the durable exact method/version and complete success state; failed,
   cancelled, capped, incomplete and not-run jobs never provide a result URL.
   Local candidate results may be imported only as explicit local replay, not
   queued online work. Actual hosted admission remains the native owner's gate.
3. Resolve the storage path through existing checked private storage, NEVER a
   URL/body-supplied path. Verify source original SHA/bytes/fullness/rights,
   canonical physical request and actual source/optimizer/runtime receipts.
4. Call `magnetic_result_view.project_result(path, receipt)` with exactly the
   persisted job/dataset/source IDs, configuration/original/generation SHA256.
   Full numeric readback validates all members, physical units, original rows,
   actual residual signs and frozen final history before projection. Dataset
   content SHA and API job-request SHA remain their OWN types: neither is
   substituted with the magnetic configuration or generation hash.
5. Retain the exact numeric ZIP, whose SHA/count cover all result bytes in the
   existing job receipt. Derive the projection on read after fresh reimport;
   do not persist a projection-only pointer with unaccounted numeric siblings.
6. Frontend receives the expected selected-job receipt from authenticated job
   state, calls `verifyMagneticView(response, expected)` and then renders
   `MagneticSurveyResult`. Changing selection clears obsolete views and aborts
   an old request, using the existing lifecycle/client. All descriptor SHA256s
   are independently rechecked little-endian in WebCrypto, not just shape cast.
7. Wire `onExport` only to the existing owned verified numeric-bundle export.
   This viewer does NOT pretend a JSON screenshot/projection is the NPY bundle.
   Keep deletion, cancellation, quotas, CSRF and recovery in the existing owner.

## Explicit mount patch outline for MAIN review

The retained [unapplied projection-only patch](owner-result-mount.patch) describes
the earlier JSON-result proposal, NOT the single-ZIP custody ABI above. Do not
apply it to a ZIP job. It never supplied input parsing, import transactions,
startup/delete dispatch or native execution and is not evidence that those routes
exist. Use the actual public custody functions above in the owner's explicit
method union; existing nonmagnetic calls are unchanged.

This is a branch-specific integration proposal, NOT a secretly applied patch:

```python
# Existing owner result dispatcher, retaining auth/project/error lifecycle.
if job.method_id == "magnetic.survey-l2-irls-local/v1":
    return await read_replay(session, settings, user, job.id,
                             project_id=project_id,
                             temp_root=configured_external_scratch)
```

```tsx
// Existing processing result dispatcher and request cancellation lifecycle.
// expected comes from selected authenticated job state, not response.binding.
const verified = await verifyMagneticView(response, expected);
return <MagneticSurveyResult value={verified} onExport={ownedBundleExport} />;
```

The durable request/dataset mapping is executable in the closed magnetic
custody schema. Native profile admission and shared union remain owner assembly
gates, not inferred from those schema names or forced into gravity/MT dispatch.
No request parameters are executable callbacks. Field direction, covariance,
mesh/prior and beta edits submit a NEW immutable physical configuration through
the accepted method job; they cannot repaint an old result as a new fit.

## Actual leaf semantics and independent gates

The additive `MagneticSurveyCourse` component is the source-linked nine-chapter
EN/ES course. It uses existing shared-shell equation/callout/language primitives
and only a parent-verified `MagneticView`; it introduces no calculation service.
Original quantities, physical units, covariance, L2, true-p1 IRLS, sealed
selection, nonlinear norm proof, conditional diagnostics and custody/export each
name actual source functions and primary version-pinned references. Its worked
readout derives counts/outer RMS from the same selected immutable generation,
never an independent fabricated example. Parent may mount it in its existing
method/course view; the private loopback harness is not that integration.

Original rows remain ordered and identifiable in map, selected flight and signed
observed-minus-predicted residual views. Missing/excluded predictions remain
null. Map and line selection share the same original row. Susceptibility cells
use exact nonuniform TensorMesh Fortran-order active mapping; depth slices and
3D physical-cell projection never manufacture between-cell geology. Rotation is VIEW
rotation, explicitly not magnetic refitting. Cell χ and volume use SI and m³.

Resolution is the actual local fixed-objective free-face point spread, not
posterior geology. Full matrix and singular spectrum only exist for small
generations where the backend actually computed them. Unexported physical
sensitivity is explicitly unavailable, not zero or a fabricated derivative.
Iteration playback uses real saved candidate/stage/objective records, not
invented intermediate models. Different beta/epsilon objectives are not a
single joined monotone history. Uniform-line spectra use original horizontal
spacing, demeaned Hann window and one-sided power; irregular/gapped lines are
unavailable without interpolation, and spectra never affect fitting/noise/QC.

Local controls, screenshots and native descriptor parity validate this leaf,
not authenticated owner integration, current parent UI, field scientific
acceptance or deployment. Parent source mounts and independently reviews these
receipts before an integration claim. EN/ES and theme use the existing pinned
shared shell, no local shell imitation or global selector edits.

## Numeric export available for the existing owner export dispatcher

`magnetic_result_export.export_zip` builds a deterministic uncompressed numeric
ZIP from an actually verified immutable generation. Every source member is
rechecked against the pinned manifest, the complete original file is excluded,
and the whole archive is bounded128MiB. `import_zip` rejects duplicate paths,
traversal, symlinks, encryption, compression, extra/partial members, object NPY
and hash corruption before accepting a generation. Fresh destinations only;
ordinary failure removes only its own fresh partial files, preserving old
generations. Hosted atomic installation/deletion/quotas remain the existing
owner's task, not an implied new persistence service.

The local command is `scripts/magnetic_numeric_export.py export|import` with
explicit input/output/data/temp roots. Browser leaf QA serves an actual numeric
ZIP, downloads it through the export button and checks exact bytes before
backend reimport. That is local export parity, not an authenticated HTTP export.
