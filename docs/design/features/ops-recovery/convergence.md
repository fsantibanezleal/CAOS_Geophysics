# Ops recovery convergence, 2026-10-03

Verdict: scoped standalone maintenance tooling and local ops gates implemented. Actual-host drill: NOT RUN. This is a PR handoff, not product/cutover acceptance and not issue #80/#37 closure.

## Requirements and exact local gates

All names are in `tests/ops/test_backup.py`; each is backed by the local runs below.

| Requirement | Named gate | Local verdict / limits |
| --- | --- | --- |
| R-OPS-01 | test_maintenance_rejection, test_systemd_proof, test_stop_proof_rechecked_before_publication | PASS for fresh/changed/stale/path-bound proofs and controlled stopped/masked/MainPID/cgroup responses. Actual Linux service control/permissions remain host gates. |
| R-OPS-02 | test_encrypted_roundtrip, test_source_rejection | PASS using real upstream age v1.3.1, real Alembic-migrated SQLite and actual admitted processing outputs. Unknown schemas/revision/ownership/quota/content/staging/sidecars/active jobs refused. Source DB unchanged. |
| R-OPS-03 | test_path_rejection, test_windows_junction_rejected, test_restore_never_overwrites_existing_target | PASS for explicit paths, overlap/existing target/key/hardlink/fixture boundary and a real Windows junction. Ordinary symlink-creation case SKIPPED because this Windows session lacks privilege; Linux symlink and POSIX permissions require host confirmation. |
| R-OPS-04 | test_deleted_project_cannot_return, test_tombstone_for_newer_owner_survives_external_authority | PASS for actual API project DELETE after an earlier snapshot, checkpoint, restore and application startup audit. Three deleted raw/dataset/result files and all corresponding rows absent; survivor has three original hashes, quota is rebuilt, sessions revoked and latest tombstones retained. Unknown newer owners remain in the encrypted external authority. |
| R-OPS-05 | test_archive_rejection | PASS for traversal/absolute/drive/backslash paths, symlink/hardlink/directory/PAX headers, duplicate/unknown/missing/truncated/trailing members, byte/count/schema/hash failures. Raw-header preflight precedes tarfile parsing; no extractall. |
| R-OPS-06 | test_authority_rejection, test_retention_and_chain, test_strict_json_and_tombstone_conflicts | PASS for wrong authority/snapshot digest, deployment/fixture/schema mismatch, expired/unregistered snapshot, preserved cumulative snapshot registrations/predecessor hashes, stale authority versus independently trusted latest hash, conflicting receipt identities and duplicate/nonfinite JSON. Freshness is an independent checkpoint trust assumption. |
| R-OPS-07 | test_operational_contract | PASS for full guide, declared 30-day example eligibility, retention/erasure non-claims, exact commands, separate unrun host recipe, synchronous deletion-replication gap and operator-assisted exact-stage quarantine policy. |
| R-OPS-08 | test_age_failure, test_wrong_identity_and_timeout, test_encrypted_roundtrip | PASS for real age authenticated encryption/decryption, wrong identity/ciphertext, bounded streamed output, timeout failure, redacted CLI and no plaintext/key in snapshot output. Test keys exist only under temporary fixtures outside repositories. |

## Verification receipts

Commands below used an existing isolated API validation interpreter and unique newly created short temporary roots outside every repository. The short `--basetemp` parent avoids the workstation's legacy Windows file-path limit. Never reuse a basetemp containing user files. No server command, real user state or real recovery identity was used.

```powershell
python -m pytest tests/ops/test_backup.py --tb=short --basetemp <NEW-PRIVATE-TEMP-ROOT>/p
# Expanded full ops run: 67 passed, 1 skipped, 1 warning, 192.25 seconds.
python -m pytest tests/ops/test_backup.py --tb=short -k 'job_staging or operational_contract' --basetemp <ANOTHER-NEW-PRIVATE-TEMP-ROOT>/p
# Handoff follow-up: 2 passed, 67 deselected, 1 warning, 6.68 seconds.
python -m pytest tests/api --tb=short --basetemp <ANOTHER-NEW-PRIVATE-TEMP-ROOT>/p
# Existing API regression: 68 passed, 1 warning, 70.24 seconds.
python -m ruff check app scripts/ops_recovery.py tests/api tests/ops
python scripts/check_artifacts.py
python scripts/check_template_residue.py
python scripts/check_ci_budget.py
python scripts/check_content_standards.py
git diff --cached --check
```

The final test file has 69 collected cases: 68 unique cases passed across the full run and focused staging follow-up, and one ordinary-symlink case skipped. One focused guide gate overlaps the full run. Both suites emitted the existing Starlette TestClient deprecation warning, not a failure. Guard receipts: lint PASS; committed artifact hashes/sizes PASS (20 distinct truth cases, 120 experiments, 348 method results); template residue PASS; CI budget PASS; tracked content standards PASS; scoped whitespace check PASS. Named requirement gates were resolved against actual test functions; the hand-authored SVG parsed as XML. PowerShell wrapper help, Git Bash wrapper help and Python CLI help passed. The Bash launcher is executable and forwards the same arguments; no Linux execution is claimed. Canonical scientific training, baking and unrelated numerical/frontend suites were not run or modified by this bounded ops unit.

## Scope/history safety and main-agent handoff

Worktree: isolated `geophysics-ops-recovery`; branch `task/geophysics-backup-restore`, based on fetched `origin/develop` at `2202ebd`. Every changed tracked path is NEW and owned by this ops unit. Config, worker, database, projects, migrations, frontend, release/version, workflows and management records are unchanged. No production/server writes, backup erasure, key generation outside temporary fixtures, merge or deployment occurred.

Implementation commit: `17b5ea7`. Review handoff: [PR #102](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/102) targets develop and remains unmerged. The subsequent documentation/launcher-mode commit records this handoff; the exact reviewed head is recorded in the PR review thread.

Main must verify these independently before release:

1. Actual host maintenance/stop/mask/activation/cgroup and POSIX 0700/0600 behavior, disk/timeout/headroom and restricted off-host receipt/hash verification.
2. Actual-host new-target recovery including a pre-deletion snapshot, latest checkpoint and exact survivor/absence/startup evidence. Keep production untouched during the drill.
3. Synchronous durable external deletion/tombstone replication or equivalent independently durable journal/watermark, including the source-loss window before routine checkpoint. The current API's pending reconciliation response remains accurate.
4. The parallel host unit's fail-closed crash policy: `run_one` marks abandoned running rows failed, then reconciliation refuses preserved `.job-staging`. Preserve only the exact owned harness stage outside the private root, explicitly rerun, and use the bounded user-owned private `StateDirectory` drill. No unattended crash recovery claim.
5. Run the reviewed R-OPS-09 MT adapter on the final combined runtime before the host drill. It preserves exact `0003_processing_jobs` DDL while explicitly supporting gravity QC and EDI M05/M06; no unknown schema/parser/modality/method is accepted. The local read-only parallel-runtime seam is recorded below; combined release/host acceptance is separate.
6. Published retention policy and restricted copy inventory. Snapshots remain encrypted originals; this utility reports `not_attempted` erasure and never purges them. Latest authority hash/sequence/watermark must be protected independently of rollback-prone backups.

## R-OPS-09 strict MT seam continuation

The originally validated bounded unit was committed/pushed and PR #102 opened before this user-requested extension. Full parallel online MT feature requirements/design/tasks, runtime and data contract were read and the ops SDD amended before adapter code. Application/database/config/worker remain unchanged on this branch. A separate subprocess imports only the explicit read-only MT app tree; its existing interpreter/environment is not modified. Every API DB, original, derivative, result, generated age fixture key and test cache uses a new temporary root outside all repositories. The accidental empty-result pytest cache from an invalid initial command was preserved outside this ops worktree; no user directory or backup was erased.

Integration checkout executed at `0970a09fa7640d3ac6148a9ccdc0335d2a75782b`; its online runtime remains based on `7b69404`. Poincare/main contract coordination is through this persisted adapter/guide and PR #102 handoff, not a claimed acknowledgement. Exact reviewed file SHA-256:

| Parallel contract input | SHA-256 |
| --- | --- |
| app/mt_contract.py | `8064be5c18236b9782d88fbf1ae09278ef6649642750dab1eb38c3982a504d3a` |
| app/mt_compute.py | `688b4778746eca06d5b3c213966daa056c1f6819b8e4959687b2b1dd15a17ba4` |
| app/processing_contract.py | `8f91e480f4fd40908c33e4edfe1c6c7672212374496dcb7e02d2b7d5554ab496` |
| app/mt_bundle.py | `d37115c87240d14c37f692a2c3847232ba0a44288e113df7ef42036b1c501477` |
| docs/data-contract/02_online-edi-mt.md | `1ad16e418584bbf88f220a9ab48cee3f273e4124c63726011dbbd94a0fd99618` |

Adapter dispatch is exact, with no method prefix fallback or generic station relaxation. EDI envelope axes/count/source/physics/parent bytes and hashes remain bound; M05 is QC-only, M06 requires the canonical successful M05 screen from the same owner/project/dataset. Dataset/request/result and screen/inverse/method/uncertainty key sets and schema versions are pinned. Non-success jobs also cannot introduce unknown methods. Serialization checks do not run another solver or establish scientific validity. During review the inventory was changed to retain only M05 screen digests rather than all scientific result bodies, and enforce cumulative byte/count ceilings before derivative reads.

The MT-only final adapter run passed **52 cases in 51.48 seconds**: actual authenticated original halfspace and noisy layered uploads; M05 and M06 worker completion for both; existing scientific bundle re-import; a gravity survivor control; coherent stopped real SQLite + 11 immutable files; real age encryption/immutable new-target roundtrip; actual API deletion of one MT project; cumulative checkpoint; old-snapshot restore removing its four files/all child rows while preserving seven survivor hashes, durable tombstone, rebuilt usage/revoked sessions and application's candidate startup audit. Fifty re-hashed hostile dataset/request/result/M05/M06 variants failed before backup publication. A freshly authenticated/re-hashed/re-registered archive with an unknown M06 inverse schema failed before restore target publication; encrypted original unchanged. Earlier harness iterations failed on private receipt Path serialization and an unclosed fixture DB connection; both were corrected, never bypassed. No host or measured field-geology PASS is inferred.

Exact commands are in the [guide](../../../operations/01_backup_restore.md#strict-modality-adapter-and-poincaremain-integration-contract). Use the same NEW-temp/read-only interpreter recipe for `tests/ops` to run the complete gravity/security/MT matrix together. Full final combined-matrix evidence is recorded at handoff after execution; opt-in MT skips without an explicit checkout are not acceptance. Additional inventory-limit gates demonstrate refusal before any derivative JSON read.

During combined verification the parallel owner legitimately switched its active checkout to `task/geophysics-online-mt-course` at `afac8ab`, which lacks app/mt_contract.py until integration. Two combined attempts consequently failed the explicit MT checkout precondition; they are NOT complete passes. Created a new detached validation worktree at `D:\_worktrees\o-d2983715\mt`, pinned to `0970a09`, without touching that owner's active branch/environment. The complete final rerun uses this pinned tree; its MT section already passed all 52 cases. Two focused inventory-ceiling cases passed in 12.23 seconds after correcting a fixture's invalid zero-byte limit and allowing the earlier database-row ceiling as the valid count rejection. These were test assertion corrections, not validation bypasses. Final single-run combined verification remains in progress for this implementation push.

Latest origin/develop was fetched read-only at `afac8ab7b0be2df474406d1b17f0a165be9e0599`; this branch remains based on `2202ebd`, without copying/cherry-picking application changes owned by parallel units. Full scientific release assembly, CI/cutover, live activation and the ops host drill remain outside this unit. Canonical artifacts were not rebuilt or relabeled here.

Main-agent supplied host receipts are retained in the guide separately from local execution; these are not user-authored facts: corrected distribution `f65e85a` and six host-control gates passed, but disk gate failed at 29.42% against unchanged 30%. Host age 1.1.1 is rejected by this tool. Main must choose an isolated provenance-verified age 1.3.1 executable, not upgrade globally or lower the minimum. External synchronous tombstone durability, independently latest authority watermark, approved storage/headroom and new-target ops drill remain release gates. Obsolete release compression requires user approval; no cleanup/server writes occurred here.

Final pinned-runtime single run: **122 passed, 1 skipped, 1 existing Starlette deprecation warning in 283.52 seconds**, using `tests/ops/test_backup_mt.py tests/ops/test_backup.py` with the existing MT interpreter, `-B -q -ra -o addopts= --tb=short`, a NEW short external `--basetemp` and external cache directory. This supersedes the failed mutable-checkout attempts and the intermediate 121-pass run whose count-limit test expected the later ceiling rather than the correct earlier database-row ceiling. All 52 MT cases and 70 gravity/security cases passed together; ordinary Windows symlink creation remains the one privilege skip. Lint, content/template/CI-budget guards and original canonical artifact hashes/sizes passed again. PR #102 adapter commit `c31a9f8` is pushed; this documentation receipt closes local adapter verification only, not any host/release gate.

Main-agent follow-up: isolated official age 1.3.1 Linux amd64 archive, 10,263,766 bytes, reported HTTPS release-API asset SHA-256 `bdc69c09cbdd6cf8b1f333d372a1f58247b3a33146406333e30c0f26e8f51377`; installer and actual Linux execution remain main-owned. Linux-to-Windows M06 re-import found a near-zero residual 1-ULP recomputation mismatch. Main owns a separate parity branch from `0970a09`, correcting semantics rather than weakening tolerance. This local same-platform ops suite is not cross-platform parity acceptance. Retest the reviewed parity runtime before host execution; no API/worker/migration edit is introduced here.
