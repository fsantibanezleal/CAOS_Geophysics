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

| Requirement | Passing gate | Evidence scope |
| --- | --- | --- |
| PFI-01 | `test_pinned_source_identity_and_rights`; `test_archive_contract_limits_in_ledger`; `test_archive_contract_member_pins_in_ledger`; `test_archive_contract_required_only_for_research_zip` | Metadata versus author-derived bytes/rights; bounded schema/pins |
| PFI-02 | `test_selected_members_immutable`; `test_all_selected_pins_before_any_publication`; `test_existing_receipt_drift_before_publication` | Exact reuse; preserve disputed member/receipt; validate selection before install |
| PFI-03 | `test_archive_negative_controls`; `test_archive_path_negative_controls`; `test_file_parent_and_case_aliases`; `test_unsupported_encrypted_and_special_entries`; `test_corrupted_compression_rejected_before_publication`; `test_storage_windows_junction_rejected`; `test_unselected_arrays_and_code_not_opened` | Actual malformed original fixtures, path/platform/expansion/type/pin controls; no provider execution |
| PFI-04 | `test_profile_preserves_correction_and_missingness`; `test_profile_physical_diagnostics_do_not_clip_or_fill`; `test_profile_rejects_ambiguous_or_incomplete_layout` | Explicit processed channels, null/raw-token flags, unchanged diagnostics/row identifiers, no corrections or invented errors |
| PFI-05 | `test_profile_guide_and_real_source`; `test_compact_inspection_evidence_not_solver_arrays`; opt-in `test_real_local_source_intake` | Paired entrypoints and honest compact evidence; actual pinned ZIP/2929 rows |

The ordinary Windows symlink test skips because this machine lacks symlink creation privilege. The independent **Windows junction/reparse-path rejection test passes**. Hermetic runs additionally skip the deliberately opt-in actual archive test; enabled real runs do not skip it and do not download.

## Actual execution and inspection

`acquire.py --source-id clear-lake-author-potentials-v2 --file data/raw/source-research/natural-hydrogen-16975696.zip` completed with `local-import` provenance. The FGDC XML was independently imported with its pinned local `--file`. Both paired scripts completed against the original ZIP, using different new ignored profile filenames. Their full results match excluding only `profiled_at_utc`; selected members/receipts are unchanged on repetition. Git Bash syntax checking also passed.

The [compact evidence JSON](../../../research/potential-source-intake-evidence-2026-10-03.json) contains the actual archive/metadata/member/receipt/profile hashes and aggregate inspection. Archive 121295137 bytes, 40 entries / 299907397 expanded bytes; selective extraction 4 objects / 221999149 bytes. Gravity has 2929 rows, 140 explicit flags (70 missing FAA + 70 missing SBA), two duplicated station IDs and one duplicated finite XYZ tuple. All rows remain present. Datum, uncertainty and original station/processing lineage are still unresolved. No extraction of code/notebooks/arrays/models or original-USGS byte-identity claim occurred.

Raw ZIP, selected objects, receipts and full profiles are confirmed ignored. `git ls-files data/raw data/downloads` returns no entries; no raw 121 MB object or station/canonical array is staged. The evidence file contains aggregate bounds and hashes, not full observations or solver input arrays. Rights and author/version attribution accompany the derivative.

## Self-review and remaining gates

Reviewed: ledger changes preserve existing modes/rights/URL restrictions; contracts fail closed; ZIP selection is explicit and staged; publication uses exclusive hard links and never overwrites; receipt disagreements fail before ordinary member installation; archive/profile digest rechecks expose byte changes; parser rejects unknown layouts and keeps correction-state attribution separate from independently verified lineage; all new outputs are ignored local inspection artifacts.

Known limitation: multi-file installation is not a transaction across OS faults or competing writers, although every installed object is independently byte-verified and immutable; use a single writer and identical retry. No claim of a complete product suite, full method acceptance, original field-data provenance closure, inversion, deploy or merge is made.

Open scientific gates: original USGS attachment bytes and station-level author transformation lineage; adjudicated horizontal/vertical transforms and elevation datum; a real error model; magnetic acquisition/grid height semantics; applicable correction-state admission; independent field forward/heldout/inverse/uncertainty controls and full M01/M02 acceptance. Those are intentionally not fabricated to close this intake unit.
