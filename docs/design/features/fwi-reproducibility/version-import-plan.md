# Guarded 0.04.002 container migration, before implementation

Date: 2026-10-03. Owner independent 120/348, 48-CUDA-model and MT
4,038-state/3,072-refit review passed at `421b999`. Exact receipt pins are
recorded in [combined acceptance](combined-acceptance.md). Authority here is
design/test only; **do not execute canonical import before owner feedback**.

## Scientific and version semantics

Version 0.04.002 names the new scientifically corrected release container, not
a retroactive producer version. Every candidate run, learned model/training
file, EDI fixture/calibration and measured-screen byte remains unchanged.
Reuse provenance 0.04.000 and 0.04.001 explicitly under the new header only if
the original version-specific fingerprint matches the actual current modules.
No historical seed, solver hash, metric, verdict or producer runtime is relabeled.
The compatibility candidate remains 0.04.001 and immutable for review.

Add a dependency-free version policy shared by the importer and artifact guard.
Supported container/version pairs are explicit, not arbitrary matching strings.
The guard gains a strict 0.04.002 migration contract, while all original physics,
case/method matrices, source fingerprint checks and thresholds remain intact.
Old 0.04.001 candidates retain their original acceptance rules. Leave
`rebuild.py`, `catalog.py`, `provenance.py` and scientific modules untouched;
future producer/release/UI version work is not inferred from this migration.

## Plan, stage, import separation

Add an offline stdlib importer with three explicit commands:

1. **Plan:** target must resolve to this checkout's exact `data/derived/v2`.
   Require clean tracked canonical files, the independently pinned 137-file
   canonical tree digest, an ignored immutable candidate, and both owner's
   independently accepted receipts with their supplied SHA pins. Cross-bind
   all 120 candidate hashes/bytes, current scientific source hashes, full matrix,
   FWI 48-result coverage, MT states/refits, catalog/release hashes and retained
   verdicts. Verify the candidate with the unchanged numerical artifact checks.
   Check every recorded replay source hash, not only the solver modules. The
   sole intentional exception is the artifact guard's reviewed version-policy
   epoch: verify its historical bytes against the actual independent execution
   revision, and record historical/current guard hashes plus the new policy hash.
   Freeze this exact difference for owner review; never replace the old receipt
   hash or silently allow another producer/checker change.
   Freeze source paths/hash/size, all tools, exact canonical inventory/digest,
   fresh private backup path and fresh ignored staging path. No canonical writes.
2. **Stage:** recheck the frozen plan, byte-copy 120 conditions and 13 auxiliary
   files, plus the two owner's independent replay receipts. Change only the
   catalog's top-level version bytes, and the release header/explicit migration
   attachment. Add a compact migration manifest binding original/new catalog,
   preserved run inventory, gate/tool hashes and independent receipts. The
   Also emit a source-bound LF-only `validation.json`, preserving the existing
   evidence-file regression contract without copying old canonical acceptance.
   The resulting 139-file staged container must pass the strict 0.04.002 guard.
   Recheck candidate, original canonical and copied bytes. No canonical writes.
3. **Import:** separately gated by exact `IMPORT-<plan SHA256>` operator approval.
   Recheck clean canonical inventory/digest, candidate, stage, tool hashes and
   all receipts immediately before publication. Reject pre-existing backup,
   unsafe/junction paths or dirty/changed canonical. The private ignored backup
   is the original directory, renamed intact and verified against all 137
   frozen receipts. Rename the validated staging directory into the exact
   canonical path. Never delete originals. If publication fails while canonical
   is absent, restore by copying the retained backup; do not overwrite an
   unexpected externally created canonical directory. Record final backup and
   publication digests, or explicit recovery status. No deployment/host writes.
   Check target existence immediately before stage publication: preserve even
   an unexpected empty directory, with the stage and private backup intact.
   This is still a check-to-rename race, not a distributed lock; the owner must
   coordinate all offline writers during the authorized operation.

Both backup and staging must be fresh non-overlapping children of this worktree's
ignored `data/raw/canonical-backups` and `data/experiments`, respectively. Reject
symlinks/junctions on inputs/outputs and ancestors. There is a short directory
rename gap: this is an offline repository operation, not a live-host atomic
release or distributed lock. Owner coordinates concurrent writers. Private
backup is never staged, published or served by the product. No broad delete.

## Named gates and limitations

- VI-01: exact-target, ignored/fresh paths, clean canonical and frozen digest.
- VI-02: independent receipt pins, matrix/coverage and scientific source binding.
- VI-03: unchanged producer/fixture bytes; only container header migration.
- VI-04: stale version-specific fingerprints reject even with rehashed files.
- VI-05: plan/input/tool drift rejects before backup or canonical mutation.
- VI-06: original private backup retained and publish failure restores safely.
- VI-07: actual ignored 0.04.002 rehearsal passes full 120/348 artifact guard.

Test these with isolated temporary trees and failure injection; no test imports
into real canonical data. Rehearse only plan/stage on the actual accepted
candidate. No GPU rebake or numerical training enters CI. Whole-product R008,
host disk gate and all unresolved requirements remain outside this unit.
Main reviews the importer/diff/staged receipt before any import command.
