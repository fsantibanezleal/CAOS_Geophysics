# M04 owned leaf and owner mount proposal

This proposal supplies executable numeric projection and scientific views. It
does not edit or activate the existing API, database, worker or frontend root.
No new authentication, server, default field metadata or persistence authority.
The API owner integrates against its CURRENT branch, not this older foundation.
`app.magnetic_results.validate_owned_magnetic_result` is an executable ownership,
state and durable-receipt guard for the proposed local method ID. It is NOT
registered in the service method allow-list or routes. Existing result byte
verification must run first; method/dataset request-schema review remains owned
by the API parent. Its focused negative tests are not a mounted auth claim.

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
5. Persist a projection byte hash in existing durable result storage if the API
   returns that JSON. Recheck dataset-input mapping and owner identity on every
   read/export; database method state is not upgraded by a bundle alone.
6. Frontend receives the expected selected-job receipt from authenticated job
   state, calls `verifyMagneticView(response, expected)` and then renders
   `MagneticSurveyResult`. Changing selection clears obsolete views and aborts
   an old request, using the existing lifecycle/client. All descriptor SHA256s
   are independently rechecked little-endian in WebCrypto, not just shape cast.
7. Wire `onExport` only to the existing owned verified numeric-bundle export.
   This viewer does NOT pretend a JSON screenshot/projection is the NPY bundle.
   Keep deletion, cancellation, quotas, CSRF and recovery in the existing owner.

## Explicit mount patch outline for MAIN review

The accompanying [unapplied dispatcher patch](owner-result-mount.patch) applies
against this branch's existing result dispatcher (verified with `git apply
--check`, never applied). It reuses authenticated owned lookups, checked private
result bytes and a durable `preflight.magnetic_binding` proposed for the local
import transaction. Missing owner context rejects. The API owner must review
that durable receipt and dataset parser ABI on its current branch; this patch
does not add a submission allow-list, dataset parser, import transaction,
worker command or ZIP export route. Existing nonmagnetic calls are unchanged.

This is a branch-specific integration proposal, NOT a secretly applied patch:

```python
# Existing owner result dispatcher, AFTER owned-job/dataset lookup and storage
# resolution. Retain the owner's exact response/error/request lifecycle.
if job.method_id == MAGNETIC_METHOD_VERSION:
    receipt = durable_magnetic_receipt(job, dataset, source, native_manifest)
    # Resolver must also prove immutable dataset -> physical request mapping.
    return project_result(checked_generation_path, receipt)
```

```tsx
// Existing processing result dispatcher and request cancellation lifecycle.
// expected comes from selected authenticated job state, not response.binding.
const verified = await verifyMagneticView(response, expected);
return <MagneticSurveyResult value={verified} onExport={ownedBundleExport} />;
```

`MAGNETIC_METHOD_VERSION`, durable request/dataset mapping and native profile
admission need the API owner's reviewed versioned schema. They are intentionally
not invented in this module or added to the existing gravity/MT union by force.
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
