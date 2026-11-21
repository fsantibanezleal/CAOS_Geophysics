# Potential-source intake validation and handoff

2026-10-03. Worktree `D:/_worktrees/geophysics-plan-convergence`, branch `task/geophysics-bartlett-acquisition`, starting commit `2202ebdf5f3ae0c6b796cc63dc5ee10e0e113bf1`. Exclusive ownership was transferred for this bounded continuation. The five pre-existing authorized source/ledger/test edits and their feature/research documents were preserved and finished, not reset. No app/backend/frontend/canonical case files were changed. Correction-module integration is excluded.

## Environment and test gates

Python 3.12.10 from `D:/_worktrees/geophysics-m01-corrections/.venv-m01/Scripts/python.exe` was used as an already-installed isolated interpreter, **read-only**: no installs, upgrades or environment edits. pytest 9.1.1 and Ruff 0.15.18 match `requirements-dev.txt`. Intake itself uses only the Python standard library. Existing data adapters' tests also use already-installed NumPy; no provider array is loaded/executed by the new intake.

Commands (run at the owned worktree root):

```powershell
$PythonPath = 'D:/_worktrees/geophysics-m01-corrections/.venv-m01/Scripts/python.exe'
& $PythonPath -m pytest tests/data/test_sources.py tests/data/test_potential_sources.py
$env:GEOPHYSICS_REAL_POTENTIAL_SOURCE = '1'
& $PythonPath -m pytest tests/data
Remove-Item Env:GEOPHYSICS_REAL_POTENTIAL_SOURCE
& $PythonPath -m ruff check data-pipeline/sources.py data-pipeline/potential_sources.py tests/data/test_sources.py tests/data/test_potential_sources.py
git diff --check
git ls-files data/raw data/downloads
```

Named requirement gates:

Final actual-enabled `tests/data` result: **79 passed, 1 skipped**. Focused hermetic source/intake result: **66 passed, 2 skipped**. Ruff and whitespace checks pass. The explicit skips are detailed below, not counted as passing controls.

| requirement | adversarial check | gate |
|---|---|---|
| PFI-001 | Plant inconsistent source identity, rights and archive pins; require exact metadata to remain explicit. | `tests/data/test_potential_sources.py::test_adversarial_pinned_source_identity_and_rights` |
| PFI-002 | Mutate selected extracted bytes and re-import; require refusal without replacing the disputed bytes. | `tests/data/test_potential_sources.py::test_adversarial_selected_members_immutable` |
| PFI-003 | Plant hostile paths, archive limits and hash mismatches; require rejection before selected members are published. | `tests/data/test_potential_sources.py::test_adversarial_archive_negative_controls` |
| PFI-004 | Plant missing or invalid physical channels; require original correction distinctions and missingness, with no inferred truth or solve. | `tests/data/test_potential_sources.py::test_adversarial_profile_preserves_correction_and_missingness` |
| PFI-005 | Run the intake CLI against a synthetic archive under an external root; require all selected members, receipts and profile output to stay there, then check that the guide preserves rights and processing limits. | `tests/data/test_potential_sources.py::test_adversarial_profile_guide_and_real_source` and `tests/data/test_potential_sources.py::test_adversarial_cli_preserves_external_data_root` |

The ordinary Windows symlink test skips because this machine lacks symlink creation privilege. The independent **Windows junction/reparse-path rejection test passes**. Hermetic runs additionally skip the deliberately opt-in actual archive test; enabled real runs do not skip it and do not download.

## Actual execution and inspection

`acquire.py --source-id clear-lake-author-potentials-v2 --file data/raw/source-research/natural-hydrogen-16975696.zip` completed with `local-import` provenance. The FGDC XML was independently imported with its pinned local `--file`. Both paired scripts completed against the original ZIP, using different new ignored profile filenames. Their full results match excluding only `profiled_at_utc`; selected members/receipts are unchanged on repetition. Git Bash syntax checking also passed.

The [compact evidence JSON](../../../research/potential-source-intake-evidence-2026-10-03.json) contains the actual archive/metadata/member/receipt/profile hashes and aggregate inspection. Archive 121295137 bytes, 40 entries / 299907397 expanded bytes; selective extraction 4 objects / 221999149 bytes. Gravity has 2929 rows, 140 explicit flags (70 missing FAA + 70 missing SBA), two duplicated station IDs and one duplicated finite XYZ tuple. All rows remain present. Datum, uncertainty and original station/processing lineage are still unresolved. No extraction of code/notebooks/arrays/models or original-USGS byte-identity claim occurred.

Raw ZIP, selected objects, receipts and full profiles are confirmed ignored. `git ls-files data/raw data/downloads` returns no entries; no raw 121 MB object or station/canonical array is staged. The evidence file contains aggregate bounds and hashes, not full observations or solver input arrays. Rights and author/version attribution accompany the derivative.

## Self-review and remaining gates

Reviewed: ledger changes preserve existing modes/rights/URL restrictions; contracts fail closed; ZIP selection is explicit and staged; publication uses exclusive hard links and never overwrites; receipt disagreements fail before ordinary member installation; archive/profile digest rechecks expose byte changes; parser rejects unknown layouts and keeps correction-state attribution separate from independently verified lineage; all new outputs are ignored local inspection artifacts.

Known limitation: multi-file installation is not a transaction across OS faults or competing writers, although every installed object is independently byte-verified and immutable; use a single writer and identical retry. No claim of a complete product suite, full method acceptance, original field-data provenance closure, inversion, deploy or merge is made.

Open scientific gates: original USGS attachment bytes and station-level author transformation lineage; adjudicated horizontal/vertical transforms and elevation datum; a real error model; magnetic acquisition/grid height semantics; applicable correction-state admission; independent field forward/heldout/inverse/uncertainty controls and full M01/M02 acceptance. Those are intentionally not fabricated to close this intake unit.

## Persistence and exact changed paths

Implementation milestone `241250041478167da5d05a4181a9a1acd5d3361d` was committed and pushed on the scoped branch. [PR #104](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/104) is open against develop and reports mergeable; the dedicated [named-test self-review](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/104#issuecomment-5966522136) is posted. At inspection, GitHub reports no PR status checks; this record does not claim remote CI success. No merge/deploy was performed. This closing documentation update is a separate scoped persistence milestone; the main agent owns subsequent integration.

Compact evidence file SHA-256: `7ede18b5253f3ba6ef49ff5864f1c0c71a0a4f04b2c4a504b093afbe32b11fd7`. Its acquisition/member/profile receipt hashes describe actual on-disk bytes and are not substitutes for the retained ignored files.

Exactly 14 changed paths relative to the starting commit:

```text
data-pipeline/potential_sources.py
data-pipeline/sources.py
data/source-ledger.json
docs/design/features/potential-source-intake/design.md
docs/design/features/potential-source-intake/requirements.md
docs/design/features/potential-source-intake/tasks.md
docs/design/features/potential-source-intake/validation.md
docs/guides/11_potential_source_intake.md
docs/research/bartlett-source-review-2026-10-03.md
docs/research/potential-source-intake-evidence-2026-10-03.json
scripts/intake-potential-sources.ps1
scripts/intake-potential-sources.sh
tests/data/test_potential_sources.py
tests/data/test_sources.py
```

## External-root CLI regression and real archive run: 2026-11-21

The intake CLI now resolves one declared external root and passes it to acquisition, selective member extraction, profiling and immutable report publication. Relative report paths resolve under that root's `data/raw/`; absolute outputs outside that directory are refused. The test `test_adversarial_cli_preserves_external_data_root` exercises the complete CLI with a synthetic pinned archive and asserts that the extracted member and report remain under the external root.

The official Zenodo v2 metadata was rechecked: DOI `10.5281/zenodo.16975696`, CC BY 4.0, five named creators, and a 121295137-byte ZIP whose published MD5 matches `7ef5beb984425bf0edabd829cf880187`. The bounded fetcher verified the ledger's SHA-256 `337a2d9070493773af06aee11a19d591e6468ecf0f062dd75c194a04476c0cdf` before publication. The external selective intake verified 40 archive entries and 299907397 expanded bytes, then installed only the four pinned members. The actual profile retained all 2929 rows, including 70 missing FAA and 70 missing SBA values. It remains `modelling_eligible=false` and `inversion_performed=false` because the vertical datum/transforms, uncertainty and station-level source lineage remain unresolved.

Focused verification with the real archive gate enabled: 36 passed, 1 skipped (Windows symlink privilege unavailable; junction rejection passed). Ruff and the dedicated external-root CLI regression passed. No selected data or receipt remains under the repository's ignored `data/` paths; raw, selected members, acquisition/member receipts and profile output are under the configured external root. This intake does not authorize a field inversion or close M01/M02 acceptance.
