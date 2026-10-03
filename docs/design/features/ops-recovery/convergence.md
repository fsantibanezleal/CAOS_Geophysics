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
5. Schema adapter convergence if the parallel MT unit adds migrations/data formats. This tooling pins exact `0003_processing_jobs` DDL and cannot silently accept future schema or methods.
6. Published retention policy and restricted copy inventory. Snapshots remain encrypted originals; this utility reports `not_attempted` erasure and never purges them. Latest authority hash/sequence/watermark must be protected independently of rollback-prone backups.
