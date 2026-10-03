# Reviewed stage ready for owner execution, no agent import

Date: 2026-10-03. Implementation revision:
`bb8e601c4a83e1a37bedb28121036da1c9d2963b`. The normal ancestry merge retains
PR106 `59f46c5` at `00bd362`; latest develop `3b0fd0e` is integrated at
`7376b8c`. The two README link conflicts were resolved by retaining both lists.
Scientific modules, original accepted candidate and canonical bytes are intact.
Main independently reviewed this implementation and reran all 39 import controls
and the actual run3 full artifact guard successfully. This handoff completes
regression and evidence persistence only; main executes the exact reviewed plan.
See the [pre-implementation plan](version-import-plan.md) and
[combined acceptance](combined-acceptance.md) for scientific scope and negatives.

## Frozen final rehearsal

- Candidate, immutable: `data/experiments/fwi-mt-full-candidate-20261003-run1`.
- Final 0.04.002 stage: `data/experiments/fwi-release-container-004002-run3`.
- Frozen plan and receipts: `data/experiments/fwi-import-receipts-004002-run3`.
- Planned private original backup:
  `data/raw/canonical-backups/pre-004002-20261003-run3` (**not created**).
- Exact canonical target: this checkout's `data/derived/v2` (**not modified**).

| Receipt | SHA-256 |
| --- | --- |
| Frozen plan | `8ee0c2caf9470b320816417fa083a51ebf2e5010388a275a9edfd577e9941ad9` |
| Stage receipt | `e695f7bb7f6fc8abf4542c4b4b4e57c0fc9d087d7c41fafaf4d583141f275eeb` |
| Staged catalog | `81248370d6ded868cdc71cace05bc343b275e2814f7a96ce96f426f37315a8cf` |
| Staged release | `16d9931c5edcd426acf71d0e6a7c1314d5f7f5e559db2745632cf761e87c3116` |
| Staged migration manifest | `0f14b7786b551f9625bfc2b6d3f43035ea57848aa6ebcd9af19689ac727aead6` |
| Frozen original 137-file canonical tree | `7dfc0fc18a0a45988f501a7aaedbda12abca3628cfa403b19696bda618aba266` |

The stage has **139 files**: 120 unchanged condition files, 13 unchanged
model/EDI auxiliaries, catalog/release, the two exact owner replay receipts,
migration manifest and source-bound LF-only validation descriptor. All 133
producer/auxiliary byte hashes match the accepted candidate. Catalog bytes
change only its top-level version string, not metrics, verdicts or source/run
provenance. Release gets the new container version and two evidence hashes.
Every method's original version-specific fingerprint still must match current
scientific code. No default producer version, solver, replay tolerance,
source fingerprint algorithm, frontend or phase source was changed.

The older run1 and run2 stages/plans remain preserved. Its initial 80-test implementation
already passed full artifact and pipeline checks, but final self-review added
strict historical/current checker epoch validation inside the stdlib guard.
Main then independently passed all 37 import-control tests at `e1d13bf` and
requested an immediately-before-publication target-existence guard. Final
`bb8e601` adds that guard, with both empty and nonempty external-directory
controls, now 39 import-control tests. The old plans are deliberately not reused
under changed importer/policy bytes.

## Explicit source epochs, never substituted old hashes

Owner independent replay still names scientific execution revision `421b999`.
Both exact original receipts are preserved:
FWI SHA `79721c8b1f167559a96dc481e631b1869c6bdd66dbe2dc5b945dbae5464a0c2a`,
MT SHA `4e1b65090884f71bdc6475aee45a24716a01c676849d5aa5698053232dbf9167`.
The MT receipt binds the full 120/348 candidate inventory, 4,038 objective states,
3,072 actual bootstrap refits, source/dependency versions and real cl061 parsing.
The unchanged scientific bytes therefore require no new bake or GPU training.

Every one of its 14 producer/checker source hashes is checked. Only the
explicitly reviewed artifact-guard epoch can differ; its old bytes are verified
against the executed Git revision, not rewritten. The manifest and CI guard
cross-check old/current epochs and reject any other replay/producer drift:

| Component | SHA-256 |
| --- | --- |
| Independent historical guard | `b7fbb8b2f24b24d6ab8828c7f4c40abd6f5fdd1820c063ae4b6290bfbe9a6872` |
| Current migration guard | `3d43177eeb14f03f0ef02be1593ee50e944b68f53af68f134fc8d7a97400d452` |
| New explicit version policy | `07e737bc72b0a597caf29c5db100181f675a9572f4cd06bc4e345a66dc7bef3c` |
| Importer | `3028378e7ca6233caf92a13bb6aec94640825824d953452fb1c29506ae8f4cd2` |

All 12 scientific producer/writer/fingerprint modules are independently frozen
in the plan, including reused-family modules not listed by the MT-only producer.
0.04.000/0.04.001 reuse is now an explicit reviewed policy under 0.04.002,
not arbitrary matching versions or relaxed stale-SHA acceptance. Unknown/newer
container/run versions and stale version-specific fingerprints fail closed.

## Import safety and review limits

`plan` and `stage` are read-only against canonical data. `import` first requires
the exact operator approval token tied to the frozen plan, then rechecks clean
tracked canonical state, its exact 137-file inventory/digest, all candidate and
staging hashes, independent receipt pins and tool/source bytes. Changed/dirty
canonical, existing backup, overlapping paths and symlink/junction targets reject
before any canonical mutation. This is tested, not a permission bypass.

On a separately authorized import, rename the exact original canonical directory
intact into its private ignored backup and verify every original file. Publish
the validated stage into that exact path. Retain the original private backup
forever, ignored and unstaged; do not publish, delete or replace it. A failed
publication restores by copying the retained original backup; a failed new
publication is preserved in ignored recovery storage. Immediately before stage publication, target existence is checked again.
Both empty and nonempty external directories are preserved with stage/backup
intact; tests prove publication is not called when they appear. There remains a
check-to-rename race without a distributed lock, so the owner must coordinate
offline writers. An unexpected external
writer found in the rename gap is not overwritten. The attempt/error/success receipts
record recovery and backup state. No claim of live-host atomic cutover or
cross-process writer locking is made; the owner coordinates this offline step.

Unit tests import only temporary synthetic trees. The first tiny migration
fixture lacked `release.json`, yielding one failed/46 passed test receipt; that
fixture omission was corrected without relaxing code or a threshold. Its XML
and the earlier M01 missing-dependency collection failure remain preserved.

Main independently reviewed the importer, source epoch/policy diff and tests,
then passed 39 controls at `bb8e601` and the exact actual run3 20/120/348 guard.
**No real `import` command has run.** No backup directory,
canonical data mutation, merge to trunk, deployment or host cutover is claimed.
R008 remains fail, 18 requirements remain unresolved, and the actual-host
free-disk failure at 29.42% versus 30% is not altered by this container unit.

## Completed final regression and reader handoff

The [portable migration proof](../../../validation/fwi-container-migration-20261003.json)
records every one of the 133 preserved and 139 staged file hashes, tool/source
epochs, exact plan/stage hashes, XML hashes, skips, failures and owner review.
Final source is `bb8e601`; this publication changes feature/evidence docs only.
Neither tools, plan, stage nor the original compatibility candidate is rewritten.

| Suite | Result | Receipt |
| --- | --- | --- |
| Full pipeline, final run3 stage | 339 passed, 15 skipped, no failures/errors | `data/experiments/fwi-import-receipts-004002-run3/pipeline-tests.xml` |
| Import/artifact/assembly controls | 85 passed, no skips/failures/errors | `data/experiments/fwi-import-unit-tests-20261003-run6.xml` |
| Complete isolated API suite | 85 passed, one opt-in benchmark skip, no failures/errors | `data/experiments/fwi-import-receipts-004002-run2/api-tests.xml` |

The focused suite comprises 39 import, 14 artifact and 32 assembly controls.
The API suite ran at `e1d13bf` (222.084 s), before the offline-only publish guard;
`git diff e1d13bf bb8e601 -- app tests/api` is empty. Its receipt is explicitly
reused for unchanged API bytes, not relabeled as a rerun at the final revision.
The final pipeline elapsed 60.633 s; focused controls elapsed 11.280 s.
All 172 tests in the original nine solver/data files pass without skips.
The 15 broader-suite skips cover opt-in source acquisition, unavailable PyGIMLi,
rights-restricted ERT/SGT originals, absent C15 EDI and Windows symlink privilege;
none skips FWI or the pinned measured cl061 control. The upstream API
TestClient deprecation warning is retained, not treated as numerical evidence.

Ruff, content, template, CI-budget and diff checks pass. Product convergence
remains one failure and 18 unresolved. No GPU rebake or training was added to CI.
All regression and evidence-reader jobs have completed. Main may now perform
its separately authorized execution after coordinating offline writers;
this worker will not run the import. Frozen canonical 137-file digest remains
unchanged and the planned private backup does not exist before that execution.

## Reproduce the approved rehearsal only

Use fresh stage/backup/receipts paths. `python` denotes the existing local
pipeline interpreter; no shared environment is modified. CPU/BLAS thread pins
and the isolated API runtime are documented in combined acceptance.

```powershell
python scripts/import_fwi_candidate.py plan --candidate data/experiments/fwi-mt-full-candidate-20261003-run1 --independent-fwi data/experiments/main-independent-review-20261003-run1/fwi-replay.json --independent-mt data/experiments/main-independent-review-20261003-run1/mt-replay.json --fwi-sha256 79721c8b1f167559a96dc481e631b1869c6bdd66dbe2dc5b945dbae5464a0c2a --mt-sha256 4e1b65090884f71bdc6475aee45a24716a01c676849d5aa5698053232dbf9167 --expected-canonical-sha256 7dfc0fc18a0a45988f501a7aaedbda12abca3628cfa403b19696bda618aba266 --stage data/experiments/fwi-release-container-004002-run3 --backup data/raw/canonical-backups/pre-004002-20261003-run3 --receipts data/experiments/fwi-import-receipts-004002-run3
python scripts/import_fwi_candidate.py stage --receipts data/experiments/fwi-import-receipts-004002-run3
python scripts/check_artifacts.py --data data/experiments/fwi-release-container-004002-run3
$env:INVERSE_EARTH_DATA = (Resolve-Path data/experiments/fwi-release-container-004002-run3).Path
$env:FWI_RECOVERY_ARTIFACTS = $env:INVERSE_EARTH_DATA
$env:PYTHONPATH = (Resolve-Path data/experiments/fwi-test-dependencies-pinned).Path
python -m pytest tests --ignore=tests/api --ignore=tests/learning --ignore=tests/ops -q -o addopts='' -ra --junitxml=data/experiments/fwi-import-receipts-004002-run3/pipeline-tests.xml
python -m pytest tests/test_fwi_import.py tests/test_artifact_contract.py tests/test_fwi_assembly.py -q -o addopts='' --junitxml=data/experiments/fwi-import-unit-tests-20261003-run6.xml
python -m pytest tests/api -q -o addopts='' -ra --tb=short --junitxml=data/experiments/fwi-import-receipts-004002-run2/api-tests.xml
```

The API command uses the separately measured existing isolated online-MT
interpreter, not the pipeline dependency overlay. Phase retraining, operations
drills and live-host admission are deliberately separate owner scopes.
