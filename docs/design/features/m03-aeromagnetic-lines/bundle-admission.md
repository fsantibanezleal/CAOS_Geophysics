# Schema-derived owner intake preparation

This implements the previously reviewed finite bundle and full original-row
inspection responsibilities, without adding an HTTP input, host authority,
solver policy or field grant. The binary envelope is defined in
[owned intake](owned-intake.md). The scientific objects retain the exact
[streamed contracts](full-survey-contracts.md) and explicit /1 or /2 pairing.

## Requirements and gates

R-BUNDLE-001 WHEN a claimed owned attempt prepares inputs, THE service SHALL
rebind genuine registered assets and the admitted source/authority receipt,
commit its running transition before allocation, and emit only the fixed
native preparation plan.
Gate: tests/api/test_magnetic_line_survey_preparation.py::test_claim_and_registered_roles_precede_plan_allocation

R-BUNDLE-002 WHEN a finite bundle is extracted, THE fixed child SHALL verify the
entire envelope and actual original identities before extraction, refuse
duplicate/case-alias/unknown members, and verify the schema-derived closure.
Gate: tests/data/test_magnetic_line_survey_bundle.py::test_exact_closure_and_unknown_alias_refusal

R-BUNDLE-003 WHILE preparation precedes the fresh scientific seal, THE child
SHALL leave every binary measurement payload encoded and every original
magnetic token opaque, never fit or score a candidate.
Gate: tests/data/test_magnetic_line_survey_bundle.py::test_native_full_geometry_without_measurement_decode

R-BUNDLE-004 IF bytes or semantic geometry disagree, THE child SHALL preserve
the index, partial extraction and inspection as counted non-success evidence.
Gate: tests/data/test_magnetic_line_survey_bundle.py::test_geometry_mismatch_preserves_failure

## Design

Backend `prepare_intake_plan` accepts only an already claimed attempt, fixed
worker ID and actual admitted authority hash, not a posted path/module/flag.
It rebinds every parent in BEGIN IMMEDIATE and requires genuine M03 intake
discriminators. A missing bundle, wrong role, changed byte parent, cancellation
or admission refuses before creating the attempt namespace. The immutable
plan is emitted only after the running transition commits. This is preparation
inside the owned lifecycle, not a job-success transition or dataset publication.

The fixed `m03-owner-preparation-plan/1` contains exactly schema, original,
metadata, request, bundles. Each original/document entry is exactly path,
bytes, sha256. Each bundle entry has the same three keys; paths are generated
from registered internal custody, never HTTP data. Documents are bounded to
2 MiB, combined auxiliary containers to 4 GiB, count to 16. The child verifies
the actual Windows Job before document decoding or allocation.

An on-disk SQLite index contains envelope offsets and the recognized byte
closure; no million-entry Python list/dict is created. Index cache is 8 MiB,
page ceiling is 2 GiB, journals/temp are inside counted attempt storage.
Before extraction, every envelope has been completely streamed and checked.
Casefold names are globally unique across containers. Extraction uses exclusive
file creation, bounded 1 MiB copies, independent payload hashes and fsync.
Original containers remain registered originals, not uncounted scratch copies.

Only refs reached from the closed input/request may authorize members. Arrays
are checked with encoded chunks, not `cells`; table schemas validate their
canonical rows. The Reader's known-byte ledger is replaced by the same bounded
SQLite index, including indexed case-alias checks. Manifests/pages/chunks keep
their 2/4/8 MiB limits. Logical roots are at most 192; physical files at most
one million. Unknown JSON/executables/source bodies are not accepted by name
or extension. A separately required reference original is still a rights-bearing
parent, not an implicit bundle exception.

The child then streams ALL original CSV rows through `inspect_geometry`, with
the independently checked line/sensor dictionaries, and compares every
reconstructed geometry array/dictionary with the closed input. The geometry
receipt retains actual rows, ordered identities and exact raw-byte hash.
This inspection is not the later NAV-aware value-free fit seal. No measurement
values, outer score, prediction or numerical fit is opened here.

Before index/extraction allocation, an independent full geometry-token pass
measures actual original rows without decoding magnetic tokens. Prospective
scratch is actual auxiliary-container bytes + 4 GiB index/journal allowance +
64 KiB per actual original row + 128 MiB fixed geometry/controller/roots. It
must fit the unchanged 32 GiB cap; excessive original count refuses, never
thins. The per-row allowance includes the bounded 4096-byte input record,
independent geometry database/index/journal/overflow pages and generated typed
records. The final measured bytes must also fit this conservative bound. Original
and auxiliary uploads remain additional account raw debt; reservation covers
this phase and MUST NOT replace the larger full-job admission proof. Actual
native CPU/RSS/commit/disk/drain controls remain those of the existing fixed
controller. Failures preserve bytes; exact terminal inventory is recorded by
the lifecycle before any result publication. A preparation receipt cannot
authorize Result publication, field acceptance, recovery deletion or a retry.

## Tasks and interpretation

1. Implement bounded indexed extraction and exact /1-or-/2 closure (R-BUNDLE-002).
2. Run actual cold native original-row inspection, no values (R-BUNDLE-003/004).
3. Add claimed-attempt/source-rebinding assembly leaf (R-BUNDLE-001).
4. Validate all named gates and retained negative controls.

Component convergence: R-BUNDLE-001 passes the genuine intake UUID/second-SQL-
transaction fence control; dataset/job authority assembly in that test is
explicitly fixture-only. R-BUNDLE-002 passes closed-byte/unknown/case-alias
controls. R-BUNDLE-003 passes actual cold native untouched S1 geometry and a
separate opaque-token negative control, all363 rows, no fit or outer decoding.
R-BUNDLE-004 passes independent full-original coordinate reconstruction
disagreement, retaining index/extracted members/geometry and no success receipt.
These are component verdicts, not a completed online or field workflow.

Parent owns final dataset UUID/descriptor publication, combined accounting,
fixed configuration authority, startup/recovery, route mount and client flow.
Those remain required for the whole workflow; preparation alone is not online
implementation. Full97 remains blocked by its failed first solver prerequisite.

## Espanol

La extraccion deriva permisos solo de referencias del esquema cerrado, no de
extensiones. Se conservan contenedores originales, indice y parciales como
deuda real. La inspeccion recorre todas las filas originales sin decodificar
mediciones ni abrir validacion externa. La transicion SQL precede asignacion;
este recibo no concede resultado, campo, host, borrado ni repeticion automatica.
