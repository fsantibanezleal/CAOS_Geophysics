# FWI completion and refreshed MT integration handoff

Latest completion: [combined acceptance](combined-acceptance.md) and
[portable proof](../../../validation/fwi-mt-full-candidate-20261003.json).
READY was received, full 72+24+24 assembly and owner independent numerical
review passed at `421b999`. The older snapshots below remain historical.
Canonical import is not executed; its separate guarded migration needs review.

Date: 2026-10-03. Completed FWI evidence is persisted at `630e0c4` on
`task/geophysics-fwi-regression`, draft PR #97. The standalone guarded assembler
is `56cebd4`; the original numerical fix is `6f7b718`.

## Completed snapshot, not current combined acceptance

The [full candidate receipt](../../../validation/fwi-full-candidate-2026-10-03.json)
binds the complete legacy 20-case / 120-condition / 348-method candidate to
its actual source revision `0871c86`. The unchanged artifact gate, all 48 CUDA
FWI replays and 179 tests passed. The candidate, plan, auxiliary copies, original
input hashes, gate source hashes and XML/replay receipts are preserved under
`data/experiments/fwi-full-candidate-2026-10-03` and
`data/experiments/fwi-full-assembly-receipts-2026-10-03`.
It retains 122 recovered, 184 unresolved, 6 failed and 36 negative controls.
Compatibility format version 0.04.001 is not a new release assignment; actual
release needs the next version and reviewed producer/gate-consistent evidence.

Current develop `59437a6` adds independently reviewed M01 code without changing
the existing fingerprinted physics modules. Online MT PR #100 was fetched at
`701732f2ec44bea97125d6020882025b6395d488`, newer than `7b69404`.
Its changes to `electromagnetics.py` and `edi.py` invalidate the 24 old MT
run fingerprints and cl061 parser receipt. The old complete candidate therefore
does **not** establish acceptance at a combined FWI+MT revision. No earlier
receipt, non-pass, source hash or version is rewritten to claim otherwise.

## READY transfer contract

Poincare/main supplies a direct READY notification and actual ignored candidate
files accessible in this worktree, preferably `data/experiments/mt-refreshed-handoff`
with a separate receipts sibling. No source or branch edits by the courier.
Required evidence:

- Immutable MT commit, scientific/producer/gate source hashes and runtime versions.
- Exactly 24 genuinely recomputed MT conditions, original seeds, baselines,
  settings, version-specific fingerprints and complete SHA-256/size ledger.
- Actual freshly screened measured cl061, original source hash, current EDI
  parser hash, artifact hash/bytes and refreshed EDI manifest. Preserve the
  tensor criterion, QC-only/ineligible result, null field truth and no inversion.
- Explicit inventory/proofs for reused versus refreshed EDI fixtures/calibration,
  exact paths and executed validation commands/results. No metadata-only relabel.

The runtime has no exposed cross-agent resume/message connector. The authorized
handoff request is sent via PR #100; main must relay the READY notification to
this agent's thread. A PR comment is not claimed to automatically activate a
worker, and no background watcher is installed or silently assumed.

## Combined assembly design, before implementation

On READY, resume immediately rather than waiting for host testing. Safely
integrate current develop and the exact reviewed MT source into this existing
task branch after persisting local work. Preserve FWI source and all historical
receipts. Check actual module hashes after integration; the candidate must be
validated with that combined tree, not under old code with new hash labels.

The existing wrapper correctly refuses MT reuse once its source changes.
Extend its frozen selection plan to allow a second fresh-family input and
refreshed EDI attachments, with no change to `check_artifacts.py` or the solver:

1. Reuse only **72 unchanged non-MT/non-FWI conditions** after original bytes,
   identity, current fingerprints and unchanged baseline source proofs.
2. Select **24 precision-10 FWI conditions** from the current frozen CUDA bake
   only if their combined-tree fingerprint remains valid.
3. Select **24 newly computed MT conditions** solely from the source-pinned
   refreshed ledger; no canonical fallback. Revalidate current generator and
   actual producer/runtime receipts before copying.
4. Select refreshed cl061/manifest only against actual current EDI parser bytes,
   unchanged measured source identity and retained field ineligibility. Any
   reused auxiliary files require explicit unchanged-source/content proof.
5. Assemble a fresh ignored destination; do not overwrite the accepted earlier
   candidate. Record original-to-combined diffs and all source/version proofs.
6. Pass the complete 20/120/348 artifact gate, original solver/data suite, new
   FWI/assembly tests, MT/EDI independent numerics, and all 48 CUDA replays at
   untouched tolerances. Bind gate source hashes and outputs to the combined
   revision. Retain every non-pass and current R-008 failure.

Main owns final canonical import, next-version evidence, PR readiness and any
product-convergence note refresh. The isolated host harness (PR #101) is a
separate measurement, not a public deployment or prerequisite to data handoff.

## Status at handoff publication

- FWI completion/179-test evidence already committed/pushed, draft #97 preserved.
- No refreshed MT candidate or new MT ledger is present in this worktree yet.
- READY transfer resumes combined assembly; no idle delay if files are available.
- Canonical data, old receipts, scientific gates, phase/frontend work and product
  convergence verdicts remain untouched.
