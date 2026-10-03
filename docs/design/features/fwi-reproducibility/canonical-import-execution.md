# Owner-executed canonical container import

Date: 2026-10-03. Main executed the exact reviewed run3 import at `8285517`
using the plan-bound approval token. The implementation remains `bb8e601`.
This worker did not execute the importer; it verifies and persists the owner's
published canonical files and a separate execution receipt. Historical
[rehearsal evidence](../../../validation/fwi-container-migration-20261003.json)
and [review snapshot](version-import-review.md) remain unchanged, including
their accurate pre-execution `canonical_import_executed: false` statements.

## Actual execution and scoped bytes

The [portable execution proof](../../../validation/fwi-canonical-import-20261003.json)
copies the exact main attempt/success receipt values with original byte hashes,
and binds the published 139-file inventory to the reviewed stage. It records
every changed canonical path: 53 modified and two new files (`migration.json`
and `mt-replay.json`). There is no solver/tool/app-version change.

| Evidence | SHA-256 |
| --- | --- |
| Reviewed plan | `8ee0c2caf9470b320816417fa083a51ebf2e5010388a275a9edfd577e9941ad9` |
| Reviewed stage receipt | `e695f7bb7f6fc8abf4542c4b4b4e57c0fc9d087d7c41fafaf4d583141f275eeb` |
| Original private 137-file backup | `7dfc0fc18a0a45988f501a7aaedbda12abca3628cfa403b19696bda618aba266` |
| Published 139-file canonical tree | `2e19fadf4f5500295e9bf5a90f15634086247d1bdc66ea2082aef547906332a8` |

The backup is `data/raw/canonical-backups/pre-004002-20261003-run3`.
Its inventory exactly equals the frozen original plan; `git ls-files` is empty
and `git check-ignore` succeeds. Retain this original forever private, ignored
and unstaged: do not publish, delete or replace it. Only hashes/counts and its
retention policy appear in the portable proof, not its original file contents.
The ignored original combined candidate and all 133 producer/auxiliary bytes
remain identical. The stage was renamed into canonical, not erased.

0.04.002 is the new corrected container header. Original 0.04.000/0.04.001
producer versions and all version-specific current source fingerprints remain
intact. The reviewed guard epoch exception is explicit and unchanged; old
tool hashes in independent receipts are not replaced. Full scientific coverage
is 20 cases /120 conditions /348 methods, with 122 recovered, 184 unresolved,
six failed and 36 negative controls retained. Both main and this worker passed
the post-import full artifact guard. A separate `python -S` guard run passes
without third-party site packages, preserving the no-rebake CI contract.

## Integration and post-import regression

Canonical milestone `c8671022940fe0b0e249c90cf3fa8d238e645395` was committed
and pushed before normal integration of reviewed develop
`54277f95b836a302ab02ccb4af1fdd4d822a7eb2` at
`0e1e4bc76f719ea6770f5bf26fc6dc402ae83f0a`. No conflicts occurred; both
documentation nav lists remain unchanged. Upstream's metadata-verification
source unit and its 22 additional tests are integrated, not authored by this
worker. All frozen scientific producer/importer/guard hashes remain identical.

All final tests execute at that merged source against actual `data/derived/v2`,
not the old candidate/stage. New XML receipts are private ignored outputs,
with their exact hashes, skips and coverage recorded in the portable proof:

| Suite | Result | Receipt |
| --- | --- | --- |
| Full pipeline, strict setup and isolated cache | 361 passed, 15 skipped, zero failures/errors | `data/experiments/fwi-post-import-regression-20261003-run2/pipeline-tests.xml` |
| Focused import/artifact/assembly controls | 85 passed, no skips/failures/errors | `data/experiments/fwi-post-import-regression-20261003-run1/focused-controls.xml` |
| Fresh isolated API regression | 85 passed, one opt-in benchmark skip, zero failures/errors | `data/experiments/fwi-post-import-regression-20261003-run1/api-tests.xml` |

The nine original solver/data files at baseline `f2bb280` now contain 194 tests,
all passing without skips (172 prior tests plus 22 integrated source controls).
Focused coverage remains 39 import, 14 artifact and 32 assembly tests. The API
receipt is a fresh post-import run, not reuse of the prior 85/one rehearsal.
Its upstream TestClient deprecation warning remains disclosed.

The first post-import pipeline invocation passed 361/15 but had a non-fatal
PowerShell `Resolve-Path` error for an optional cache directory. Its original
run1 XML remains preserved. Final run2 creates a fresh isolated cache and makes
setup errors terminating, then repeats all 361/15 tests without that error.
No code, seed, physics tolerance or threshold changed between these runs.
Broader skips cover opt-in source acquisition, missing PyGIMLi/rights-restricted
ERT/SGT originals, absent C15 EDI and Windows symlink privilege; none covers
FWI or the pinned cl061 control. Phase retraining, operations/host admission
and frontend builds remain separate owner scopes, not silently claimed passed.

Artifact, Ruff, content, template, CI-budget, base-integrity and diff checks pass.
Read-only M13 asset integrity passes without touching phase files or training.
Convergence is structurally valid with one failure and 18 unresolved. All test
and inventory-reader jobs finished; final snapshots reconfirm unchanged backup,
original candidate and published bytes. Workflow triggers remain trunk-only,
so these are local execution receipts, not an invented task-branch CI run.

## Reproduce read-only post-import checks

`python` below means the existing pipeline interpreter. Install no shared
dependencies: use the existing ignored repository-pinned M01 dependency target.
Use fresh XML/cache output names on reproduction; do not overwrite receipts.
Pin OMP/MKL to four, OpenBLAS/NumExpr to one for pipeline tests. The API uses
the existing isolated online-MT interpreter read-only, no dependency overlay,
with all four CPU thread variables set to one. Its pandas 3.0.6 remains
attributed separately from pipeline pandas 2.2.3.

```powershell
python -S scripts/check_artifacts.py
$env:INVERSE_EARTH_DATA = (Resolve-Path data/derived/v2).Path
$env:FWI_RECOVERY_ARTIFACTS = $env:INVERSE_EARTH_DATA
$env:PYTHONPATH = (Resolve-Path data/experiments/fwi-test-dependencies-pinned).Path
python -m pytest tests --ignore=tests/api --ignore=tests/learning --ignore=tests/ops -q -o addopts='' -ra --junitxml=data/experiments/fwi-post-import-regression-20261003-run2/pipeline-tests.xml
python -m pytest tests/test_fwi_import.py tests/test_artifact_contract.py tests/test_fwi_assembly.py -q -o addopts='' --junitxml=data/experiments/fwi-post-import-regression-20261003-run1/focused-controls.xml
python -m pytest tests/api -q -o addopts='' -ra --tb=short --junitxml=data/experiments/fwi-post-import-regression-20261003-run1/api-tests.xml
python -m ruff check data-pipeline tests scripts/import_fwi_candidate.py scripts/check_artifacts.py scripts/validate_fwi_mt_candidate.py
python scripts/check_content_standards.py
python scripts/check_template_residue.py
python scripts/check_ci_budget.py
python scripts/check_phase_assets.py
python scripts/check_sdd_convergence.py
git diff --check
git ls-files data/raw/canonical-backups
```

Main's original 48-CUDA-model and 4,038-MT-state/3,072-refit independent receipts
remain valid for the exactly preserved 133 producer/auxiliary files and unchanged
scientific code. They are not relabeled as new post-import replays; no GPU rebake
was required or added to CI. The new execution proof records this reuse explicitly.

This canonical milestone is not app-version promotion, host admission, release,
merge to main or deployment. R008 remains failed and 18 requirements unresolved;
main's disk 29.42% is below the unchanged 30% gate. Original independent FWI
48-model and MT 4,038-state/3,072-refit receipts remain separately source-pinned.
Synthetic recovery is not geological truth. The offline race/no distributed
lock limitations remain as originally reviewed.
