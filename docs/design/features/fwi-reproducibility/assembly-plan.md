# Complete source-consistent FWI candidate assembly

Date: 2026-10-03. Authority: owner reviewed the numerical fix and draft PR #97,
then requested a full isolated candidate for independent integration review.
This plan precedes implementation of the assembly wrapper. It changes no
scientific solver, canonical data, artifact gate, threshold or release version.

## Audit and design

`catalog.assemble` already builds the complete case/variant catalogue from
source-matched runs, preserves ten-digit summary metrics, and computes display
scales from the existing models. `check_artifacts.py --data` already validates
20 cases, 120 conditions, 348 methods, every catalogue hash/size, current family
fingerprints, evaluation/state identity, checkpoint hashes and EDI attachments.
Neither needs a weakened check or numerical change.

The missing operation is safe, reproducible selection and copying. Add a
stdlib-oriented offline wrapper `data-pipeline/assemble_fwi_candidate.py` with
`plan` and `assemble` commands. The wrapper imports the existing catalogue only
after the selection plan has passed. It never invokes any solver or training.

1. Read the canonical catalogue without modification. Select its 96 non-seismic
   conditions only after original hash/size, identity, method matrix and current
   version-specific generator fingerprint checks. Compare every fingerprint
   module's current bytes against the pinned pre-FWI `develop` commit `dce92a1`.
   Reject reuse if either proof fails; do not annotate or relabel the run.
2. Select all 24 precision-10 seismic conditions from the independently baked
   candidate, checking the frozen worker ledger hashes, current generator,
   solver and writer provenance, identities, call budget and precision. Old
   canonical seismic files are never fallback inputs.
3. Copy the unchanged learned checkpoints/training ledger and EDI files
   byte-for-byte. Record their original hashes and verify the existing gate;
   new training or field FWI claims are not inferred from copying evidence.
4. Record a frozen ignored plan with 120 run receipts, auxiliary receipts,
   family fingerprint/module proofs, source/gate/wrapper hashes, explicit
   excluded stale validation receipts and separate candidate version semantics.
   Assembly rechecks this plan before writing anything. The destination must
   be a fresh, distinct child of this worktree's `data/experiments/`, never a
   source, ancestor, canonical path, receipts directory or unrelated worktree.
5. Copy exactly the planned files; verify destination hashes; call the existing
   catalogue assembler; run the unchanged artifact gate on this candidate.
   Retain its full receipt and catalogue diff against canonical data. Do not
   copy old `validation.json` or `fwi-replay.json` as new acceptance evidence.

## Requirements and named acceptance gates

| ID | Requirement | Verification |
| --- | --- | --- |
| A1 | THE assembler SHALL keep all inputs and canonical files unchanged. | Planned input hashes rechecked after assembly; destination/path negative tests in `tests/test_fwi_assembly.py`. |
| A2 | WHEN a family is reused, THE assembler SHALL require both current version-specific fingerprint and unchanged baseline module bytes. | `validate_run`/`family_proof` negative tests; 96 original-to-copy SHA-256 equalities in the plan/receipt. |
| A3 | IF any seismic run is stale, missing, reduced-budget or written at seven digits, THEN THE assembler SHALL reject assembly without old-seismic fallback. | Seismic provenance/precision/budget negative tests; all 24 ledger receipts; `validate_fwi_exports.py` unchanged tolerances. |
| A4 | THE candidate SHALL contain exactly 20 cases, 120 conditions and 348 methods. | Existing `scripts/check_artifacts.py --data <candidate>` plus exact catalogue matrix in the receipt. |
| A5 | THE candidate SHALL preserve existing physical and scientific gates. | Original solver suite with `INVERSE_EARTH_DATA` and `FWI_RECOVERY_ARTIFACTS` pointed at the full candidate; new assembly/FWI tests; CUDA replay of all 48 seismic models. |
| A6 | THE assembly SHALL not represent the candidate as a published version. | `candidate.json`, frozen plan and receipt version fields; no `RELEASE_VERSION`, canonical, main or deployment changes. |

## Version semantics and release handoff

The existing catalogue format uses `RELEASE_VERSION=0.04.001`; its validator
accepts that catalogue version and legacy 0.04.000 run provenance. For this
isolated compatibility candidate, retain that format value and every original
run version/fingerprint byte-for-byte. A separate `candidate.json` explicitly
states `published=false`, `canonical_import=false`, `release_version_assigned=false`
and `next_release_required=true`. The 0.04.001 compatibility value is **not** a
claim that this changed solver belonged to the published 0.04.001 release.

An actual release containing the scientific fix must receive the next release
version, not overwrite the old main claim (0.04.002 is the expected next patch,
subject to owner integration). Version is part of each generator fingerprint:
changing version requires producer/gate-consistent versioned evidence or an
explicit independently reviewed provenance migration, never rewriting old
solver hashes to look current. No such migration or gate modification is part
of this assembly. Main owns version assignment, canonical import and PR readiness.

## Sequence and convergence record

- [x] Audit current assembler and unchanged acceptance gate; specify isolated wrapper.
- [ ] Freeze complete source-valid selection plan and family proofs.
- [ ] Implement/test rejection paths, copy and hash-check the complete candidate.
- [ ] Pass full artifact gate, original solver suite and all 48 CUDA replays.
- [ ] Persist compact plan/diff/receipt, commit/push and update draft #97.
- [ ] Owner independent review, versioned release, canonical import: not authorized here.

Detailed ignored outputs will live under `data/experiments/fwi-full-candidate-2026-10-03`
and `data/experiments/fwi-full-assembly-receipts-2026-10-03`.
