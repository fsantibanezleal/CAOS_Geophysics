# Acquisition and ingestion foundation convergence

Date: 2026-09-27. Scope: task branch only, local acquisition and ingestion scripts, tests, data contract and source guide. Parent approval: [product SDD](../../SDD.md). No API, frontend, host or canonical release mutation.

| Requirement | Gate and observed result | Verdict |
| --- | --- | --- |
| AIF-01 | `test_ledger_contract_and_rights` and `test_stead_is_unverified_provider_metadata_only`: seven stable IDs, typed modes, pins and rights; STEAD has no raw key or acquirable asset. | Pass |
| AIF-02 | `test_immutable_raw_asset_and_receipt`: exact byte/hash installation, idempotent reuse, asset tamper and rights/owner receipt drift rejected without overwrite. | Pass |
| AIF-03 | `test_source_allowlist_and_link_only`: unknown ID, HTTP, unapproved host and traversal rejected; manual mode points to a verified local import. STEAD acquisition CLI rejected with its provider link. | Pass |
| AIF-04 | `test_external_edi_never_opened_as_tar` and `test_selected_edi_dispatch`: `--external` selects only two SimPEG tar observations; explicit EDI routes to tensor QC. Live `--external` ran both archives without touching EDI. | Pass |
| AIF-05 | `test_archive_member_bounds_and_observation_contract`: path traversal, nonfinite rows, missing/duplicate observation member and oversize rejected. Live gravity and magnetics each yielded 289 local observations with source SHA-256, declared unit, assumed sigma and flag-only outliers in ignored receipts. | Pass |
| AIF-06 | `test_clear_lake_source_pin`, `test_selected_edi_dispatch` and live `python data-pipeline/ingest.py --source-id clear-lake-cl061`: exact EarthScope object was 16,411 bytes, SHA-256 `90c5c96cd69d6d29c866a768097cb3b38bc20e8b9c143e24bf10b2d253261e83`; screen reported 42 frequencies, `one_d_inversion_eligible=false`, `inversion_performed=false`. | Pass, QC only |
| AIF-07 | `test_pygimli_provider_links_and_pins`, `test_stead_is_unverified_provider_metadata_only` and `test_no_external_raw_tracked`: Slagdump/Koenigsee pinned to upstream objects, local import only; STEAD metadata user-reported but unverified here; `git ls-files data/downloads data/raw` empty. | Pass, no raw mirror |
| AIF-08 | `test_actionable_acquisition_errors` and `test_unsupported_adapter_is_explicit`: byte/hash mismatch, missing local file, metadata-only request and unsupported ERT adapter each give source-specific action; no false processed result. | Pass |
| AIF-09 | `test_documented_source_inventory` plus review below: source guide, data contract, run/BYOD/data/script docs name commands, physical meaning, rights and method limits. | Pass |

Final targeted command before staging: `.venv-ingestion/Scripts/python.exe -m pytest -o addopts= tests/data tests/test_edi.py tests/test_artifact_contract.py` -> **71 passed**. `.venv-ingestion/Scripts/ruff.exe check data-pipeline/sources.py data-pipeline/acquire.py data-pipeline/ingest.py tests/data` -> **All checks passed**. `python scripts/check_artifacts.py` -> **PASS: 20 distinct truths / 120 experiments / 348 method results; all SHA-256 and sizes match**. `python scripts/check_content_standards.py` -> pass for tracked files; rerun after staging to include new files. `git diff --check` -> pass, with only Git's PowerShell LF-to-CRLF notice.

## Source-to-document and release-boundary review

| Source group | Ledger identity and local behavior | Guide/contract decision |
| --- | --- | --- |
| SimPEG gravity/magnetics | Exact provider objects, bytes, SHA-256; fetch to ignored raw; parse only bounded `_data.obs`. | Synthetic tutorial observations, local-only derivatives and assumed uncertainty, not field truth or a publishable raw mirror. |
| Clear Lake `cl061` | Pinned EarthScope EDI, fetched and hash-verified locally; 42-frequency full-tensor screen; no inverse. | CC0 release plus station citation; only the already-attributed QC derivative is public. No new canonical artifact in this unit. |
| pyGIMLi Slagdump/Koenigsee | Fixed example-data commit and independently checked byte/hash; manual local import, unsupported modelling adapter. | Field electrodes/resistances and traveltime picks; library code licence is not raw-data redistribution permission. Provider links only publicly. |
| STEAD metadata | Official repository and SeisBench metadata URL recorded; user-reported 402,560,190 bytes and SHA-256, not independently verified or acquired here. | Official dataset declares CC BY 4.0, but this branch makes only a provider-link catalogue entry. The 91,127,786,704-byte waveform download reported elsewhere is unverified, untouched, unprocessed and unpublished here. M13 is separately owned. |
| Original synthetic | Constructor-generated cases, no external raw asset. | Known truth only for the original synthetic controls, never for measured field inputs. |

Scientific non-claims: no ERT/traveltime/waveform adapter, no STEAD waveform, no fabricated field inversion, no new public data mirror, no release promotion. A source checksum identifies bytes and does not establish measurement adequacy or redistribution rights.
