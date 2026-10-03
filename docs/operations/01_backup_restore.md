# Private SQLite and immutable-byte backup/recovery

Actual-host drill: NOT RUN. This guide describes the recipe the main agent executes after review. Local fixture receipts cannot establish host recovery or release readiness.

## Scope, data policy and unresolved integration

`scripts/ops_recovery.py` is a standalone maintenance tool, without application configuration imports, service stop/start, key generation, backup purge, production replacement or a package. Three operations are available: `backup`, `checkpoint` and `restore`. Each requires an explicitly named new output. It never overwrites a source, previous backup, existing restore directory or key. Backups cover migrated private SQLite and every DB-referenced original, dataset and successful processing result. Secrets from environment/SMTP configuration are excluded. SQLite contains password hashes, email addresses, sessions, private metadata and deletion receipts: the whole snapshot is RESTRICTED even if some source rights say mirror.

Successful projects remain stored until explicit deletion or an announced policy change, subject to account admission quotas. API deletion permanently removes the exact owned active-tree rows and raw/derived/result files after a durable tombstone commit. Current API responses honestly say backup erasure `not_attempted` and external reconciliation pending. A restricted encrypted snapshot can still contain those historical bytes. Recovery always applies the latest authority so those projects cannot return in the validated active target. No command here claims media-level erasure or cryptographic destruction of historical snapshots.

The operational schedule used in examples is **30 days** of backup eligibility (`restricted-30-days-v1`), with an exact absolute expiry recorded per snapshot. Operators choose and announce the real schedule before production use; there is no hidden hard-coded purge. Expired snapshots are refused by `restore`; no forensic bypass is provided. This utility never erases backups. An operator-managed inventory must record off-host copies, policy, storage location, owner, retention deadline, holds, deletion reconciliation and eventual disposal evidence separately. Retain authority/tombstones at least while ANY retained snapshot or copy could contain the deleted project; never discard them merely because a routine schedule elapsed. A legal hold requires a separately reviewed policy and access procedure, not editing an old authority to extend an archive silently.

**Release gate:** deletion currently commits only to the source SQLite DB. It has no synchronous durable off-host recovery-authority replication. If the source is lost after deletion but before `checkpoint`, an older externally copied authority has no information about that deletion. Neither age nor SHA-256 can recreate missing history. Main must integrate durable replication/acknowledgment in the deletion path (or an independently durable journal with an equivalent verified watermark), test the crash window and publish the retention policy before cutover. A local ops test does not close that gate. Never use `--initialize-authority` to recover from missing or stale authority history. Before a drill on a surviving host, checkpoint every latest receipt under maintenance and transfer/verify the checkpoint to a separate failure domain. Disaster recovery without a trusted latest authority hash/watermark is blocked.

## Security assumptions

The operator controls the host, approved executable, maintenance evidence and independently protected latest authority checkpoint. All filesystem parents are trusted, not writable by another principal during capture/recovery. Input paths are canonical absolute paths; no relative path, `..`, symlink, junction/reparse point, special file, hardlink or repository-resident private input is accepted. Source, scratch, backup and restore roots must be distinct. `--database` names `source/api.sqlite3` or an external database, never another descendant in the source tree. An existing directory is refused even if empty. Scratch and output parents must already exist with restricted permissions. Newly created POSIX directories are 0700; files are 0600. Restrict source tree ownership, scratch mount and off-host destination yourself. Production mode is Linux/systemd only; Windows supports temporary fixture mode under a private inherited ACL, using a short temp path to avoid the workstation's legacy path-length restrictions.

Use age v1.3.1 or later from its maintained official distribution. Verify the installed binary's provenance separately; a version string does not authenticate an executable. Supply the absolute path in `--age-binary`. Only native x25519 public recipients (`age1...`) and a single native identity (`AGE-SECRET-KEY-1...`, possibly with comment lines) are allowed. No password/plugin/SSH recipient mode, custom crypto or network key service is used. The public recipient can enter an operational command; the private identity exists only in a protected vault outside public repositories. Do not place keys in this repo, temporary PR bodies, environment dumps or logs. The utility does not generate keys. The test suite invokes upstream `age-keygen` only inside newly allocated temporary fixtures and discards its diagnostics. Host key provisioning/escrow/rotation is a separate existing owner procedure.

An age ciphertext authenticates its content to an identity holder, not its age or producer. Someone with the public recipient can create an encrypted archive. The independently authenticated snapshot SHA-256 and latest authority SHA-256 are mandatory inputs, obtained from a protected operational checkpoint, not from an untrusted archive sidecar or copied old receipt. The hash is a public integrity digest, not encryption and not a signature. An administrator can defeat local permissions or replace the trusted checkpoint; this tool does not promise protection from a compromised root/admin or malicious approval authority.

The authority binds a deployment UUID, cumulative tombstones, sequence, preceding ciphertext hash, observation time, and cumulative snapshot records. Every snapshot registration binds snapshot UUID/ciphertext hash, creation, expiry and policy. Full receipts and project IDs remain inside encrypted authority; the private success receipt has summary counts and integrity digests. CLI stdout contains only operation/validated/fixture status; errors are stable codes with no paths or key contents. Keep all receipts restricted: never publish real project hashes, IDs, inventory, SQLite or host proof in public PRs.

## Coherent maintenance capture

SQLite online backup freezes database pages, not the external immutable file inventory or a concurrent DELETE move/unlink. Therefore a live API or worker is never an acceptable backup source. Stop and mask API/worker AND all timer/socket/path activation units, block ingress and account for manually started workers/compute children and maintenance writers. The declared writer set is an operator assertion; the tool cannot discover an omitted process by magic. Capture state is read twice. A changed proof, resumed/unmasked unit, nonzero MainPID, populated existing service cgroup, changed database or changed file inventory aborts before publication. Masking is not a hostile-admin lock.

`systemctl show` is read-only in the tool. Required service state is `LoadState=masked`, `ActiveState=inactive`, `SubState=dead`, `UnitFileState=masked` or `masked-runtime`, `MainPID=0`, and an empty/nonexistent ControlGroup. For a still-existing named cgroup its `cgroup.events` must report `populated 0`. An empty ControlGroup after a completed stop is acceptable only with the operator's all-writers attestation. Unit names are literal service/timer/socket/path names; patterns are not accepted. At least two service units must be declared. Check timers, sockets, manual processes, scheduled scripts and upstream ingestion independently. Unit names shown below are recipe examples, not verified installed units.

No nonempty `-wal`, `-shm` or rollback `-journal` is accepted. A cleanly closed SQLite client normally checkpoints/removes WAL sidecars. If any remain, stop and inspect. Never remove or truncate them by shell. If appropriate, an operator must use the maintained SQLite interface to complete recovery/checkpoint after every writer is stopped, confirm integrity and close the connection before invoking this tool. That operation changes source DB state and is deliberately not implemented here. Unknown staged/export/deleting/job-staging bytes, `.backups` entries, orphaned files, corrupt content, active queued/running jobs or unsupported schemas block capture. Resolve abandoned jobs/staging through the application owner's reviewed recovery procedure, retaining unexplained bytes outside the active tree; do not age-sweep them.

Crash recovery is fail-closed and operator-assisted, never unattended. The existing `run_one` first marks an abandoned running job failed, then its startup reconciliation refuses preserved `.job-staging` bytes. A failed job row does not establish a clean private tree. The parallel host admission unit (`task/geophysics-host-admission`, reported base `7b69404`) tests that refusal, preserves the exact harness stage outside the private root under operator-controlled quarantine, and reruns reconciliation. Use its bounded, user-owned private `StateDirectory` drill after the ops handoff; main owns verification on the actual host. Do not move an entire staging tree or unknown user bytes based on a name, delete the evidence, or infer automatic worker restart/success from a status transition. This backup utility also refuses any nonempty `.job-staging` until that exact reviewed quarantine/reconciliation procedure is complete. No host crash drill is claimed here.

The schema adapter accepts exactly migration `0003_processing_jobs` and its committed SQLite DDL fingerprint. It rejects a fake revision label over altered tables/indexes/triggers/views. New MT tables/migrations require a separately reviewed adapter update and migrated-fixture gates by the integration owner. No dynamic unknown-schema bypass exists. The stored dataset/result formats currently supported are the application's observation-dataset/v1 and processing-result/v1, with receipt-bound identity/hash checks. This is integrity/ownership validation, not geophysical numerical acceptance.

## Paths and preparation

PowerShell launchers and Bash launchers forward identical arguments to the same Python program. On Windows, run fixture tests in an isolated environment; do not invoke host mode. Activate the repository/API environment before using `scripts/ops-recovery.ps1` or select the explicit interpreter directly:

```powershell
python scripts/ops_recovery.py --help
python scripts/ops_recovery.py backup --help
python -m pytest tests/ops/test_backup.py --tb=short
python -m ruff check scripts/ops_recovery.py tests/ops/test_backup.py
```

On this Windows host use a newly created, short temp parent outside every repository for pytest `--basetemp`; choose a new GUID name on every invocation. Pytest owns/removes its basetemp, so NEVER point it at a directory containing user files or a real backup/key. The tests create all state and fixture keys beneath that fresh path. No real service/host state is accessed.

The following host paths are examples with no real credentials, identity or deployment assertion. Before execution replace every sample with the actual reviewed absolute path, deployment UUID and protected receipt digest. Output parent `/srv/restricted/geophysics-backups` and scratch `/srv/restricted/geophysics-scratch` are distinct from live `/srv/geophysics-private`. Create/restrict those parents under the main agent's approved host procedure. Scratch has plaintext SQLite, arrays and archive during execution, including deleted rows before reconciliation; use an encrypted restricted local volume, no web root/shared `/tmp`, and adequate free disk. `VACUUM`, archive creation/verification and copy publication need additional disk beyond `--max-bytes`; reserve conservatively about six times the declared total plus source/retained backups, measured on the host. There is no compression or expansion-ratio problem in the snapshot format (uncompressed USTAR); nested content is treated only as opaque bytes, never recursively extracted.

Maintenance proof is a mode-0600 JSON file outside source and repository. It must have exactly these fields; issue/expiry are timezone-aware and the total window is at most one hour:

```json
{
  "schema": "geophysics.maintenance-proof/v1",
  "source": "/srv/geophysics-private",
  "database": "/srv/geophysics-private/api.sqlite3",
  "deployment_id": "d10f5c4a-8de8-4bce-b379-9931a374db12",
  "mode": "systemd",
  "issued_at": "2026-10-03T12:00:00Z",
  "expires_at": "2026-10-03T12:45:00Z",
  "ingress_blocked": true,
  "all_writers_accounted": true,
  "units": ["geophysics-api.service", "geophysics-worker.service"]
}
```

Sample dates must be replaced with the actual maintenance window. Add every installed activation/writer unit to `units`. Keep a protected operational incident/change reference alongside the proof; the exact proof hash is recorded in the success receipt. The tool cannot create a proof that services were stopped when it did not observe them.

## Initial bootstrap and routine backup

Only the first audited deployment authority uses `--initialize-authority`. Audit pre-existing backups/deletion history and escrow the deployment UUID first. Thereafter always provide the predecessor authority and its independently recorded hash, plus the existing protected identity to read it. Do not bootstrap after a restore or a missing-checkpoint incident.

```bash
python scripts/ops_recovery.py backup \
  --source /srv/geophysics-private \
  --database /srv/geophysics-private/api.sqlite3 \
  --maintenance-proof /srv/restricted/proofs/maintenance-20261003.json \
  --deployment-id d10f5c4a-8de8-4bce-b379-9931a374db12 \
  --age-binary /usr/bin/age \
  --recipient "$RECOVERY_PUBLIC_RECIPIENT" \
  --initialize-authority \
  --scratch-parent /srv/restricted/geophysics-scratch \
  --new-output /srv/restricted/geophysics-backups/20261003-bootstrap \
  --policy-id restricted-30-days-v1 --expires-at 2026-11-02T12:00:00Z \
  --max-bytes 4294967296 --max-file-bytes 1073741824 --max-files 100000
```

The recipient variable is a previously provisioned public key, never the private key text. For later backups replace the bootstrap flag with:

```bash
  --identity /srv/restricted/key-vault/geophysics-recovery-identity.txt \
  --authority /srv/restricted/geophysics-backups/20261003-bootstrap/authority.age \
  --authority-sha256 "$TRUSTED_LATEST_AUTHORITY_SHA256"
```

The new directory contains `snapshot.age`, `authority.age` and `receipt.json`, and no plaintext. After success verify its receipt hashes independently with `sha256sum` (or `Get-FileHash` for fixture files), copy both ciphertexts/receipt through the existing approved restricted off-host transfer mechanism, verify remote hashes and record the latest authority sequence/hash/watermark independently. A local success receipt or local-only backup is not off-host durability. The tool neither sends nor erases anything remotely. Failed captures clean only their freshly allocated owned scratch directory; existing backups/source/keys remain intact. A failed publication may leave a new restricted partial target with no `receipt.json`; preserve/inspect it, select another new output for retry, and never treat it as validated.

## Post-deletion authority checkpoint

This copies no project files into a new snapshot, but audits the current exact active inventory and durable DB receipts under the same maintenance proof. It preserves every preceding snapshot registration/tombstone, appends newly observed receipts and rejects a changed receipt identity/owner/hash. It never purges an encrypted backup.

```bash
python scripts/ops_recovery.py checkpoint \
  --source /srv/geophysics-private --database /srv/geophysics-private/api.sqlite3 \
  --maintenance-proof /srv/restricted/proofs/maintenance-after-deletion.json \
  --deployment-id d10f5c4a-8de8-4bce-b379-9931a374db12 \
  --age-binary /usr/bin/age --recipient "$RECOVERY_PUBLIC_RECIPIENT" \
  --identity /srv/restricted/key-vault/geophysics-recovery-identity.txt \
  --authority /srv/restricted/geophysics-backups/20261003-bootstrap/authority.age \
  --authority-sha256 "$TRUSTED_LATEST_AUTHORITY_SHA256" \
  --scratch-parent /srv/restricted/geophysics-scratch \
  --new-output /srv/restricted/geophysics-backups/20261003-deletion-checkpoint
```

Transfer and verify the NEW `authority.age` and receipt off-host, then advance the independently protected latest hash/sequence/watermark. The preceding ciphertext remains. If a prior authority names a deleted project still active in this source, capture refuses (`authority_deleted_project_in_source`), preventing a rolled-back source database from establishing a new authority. A previously known receipt missing from a newer source is retained in the cumulative authority. Duplicate/conflicting receipts fail. Legacy receipts without complete raw/derived manifests require an audited adapter; the tool refuses them rather than inventing deletion detail.

## Restore into a new validated target

![Maintenance capture and independently fresh deletion authority](recovery-flow.svg)

For a snapshot's project set S and the latest durable deleted-project set D, the accepted restored set is S minus D. For every surviving file f, SHA-256(restored f) must equal the original receipt hash. The database inventory and file-member set must agree exactly before and after reconciliation; a hash-valid archive alone does not establish that relation. The latest authority is an independently trusted input, never selected from inside the old snapshot.

Restore reads an immutable encrypted snapshot and the latest authority, requiring both trusted ciphertext hashes. It performs no production service changes and needs no live DB write. Its source-of-freshness prerequisite is the latest independently durable authority/watermark, not a proof bundled in an old snapshot. If the current source survives, first compare/checkpoint its latest deletion receipts under maintenance; never choose a convenient older authority. Loss of that authority blocks the operation.

```bash
python scripts/ops_recovery.py restore \
  --snapshot /srv/restricted/geophysics-backups/20261003-bootstrap/snapshot.age \
  --snapshot-sha256 "$TRUSTED_SNAPSHOT_SHA256" \
  --authority /srv/restricted/geophysics-backups/20261003-deletion-checkpoint/authority.age \
  --authority-sha256 "$TRUSTED_LATEST_AUTHORITY_SHA256" \
  --deployment-id d10f5c4a-8de8-4bce-b379-9931a374db12 \
  --age-binary /usr/bin/age \
  --identity /srv/restricted/key-vault/geophysics-recovery-identity.txt \
  --scratch-parent /srv/restricted/geophysics-scratch \
  --new-target /srv/restricted/restore-candidates/20261003-drill-01 \
  --max-bytes 4294967296 --max-file-bytes 1073741824 --max-files 100000
```

The target parent must exist privately; the target itself must not exist. There is no production target/default path and no overwrite option. Byte/count/time limits are independently configurable; defaults are 4 GiB total payload, 1 GiB/file, 100,000 files and 600 seconds per age subprocess. Set smaller measured limits for a drill. Database integrity operations have a 60-second SQLite progress deadline. Input JSON caps at 16 MiB; identity input caps at 4 KiB. Exceeding limits produces failure, not partial success. Decryption must finish/authenticate before extraction. Header preflight rejects PAX/GNU extensions, sparse headers, links, directories and unsafe paths before tarfile can consume extension payload. The manifest must be first; every exact ordinary-file member has bounded size/SHA-256; duplicates, unknowns, missing bytes, concatenated archive data and unknown schema fail. `extractall` is never used.

Restoration validates every original snapshot hash/DB reference BEFORE mutation. It then removes tombstoned projects' jobs/datasets/assets/sources/projects in explicit FK order only inside the new scratch copy, preserves deletion receipts for accounts known to that snapshot and keeps all newer-account receipts in the encrypted authority. Tombstones are keyed by globally unique project UUID and checked against the snapshot owner. It revokes all access tokens, clears rate windows, recalculates account raw-byte usage and vacuums only that new DB so deleted values do not remain in its freelist. Snapshot password hashes/accounts are otherwise retained for review; do not expose the candidate to a real public origin during a drill. Survivors must keep their original hashes. No full-path recursive deletion of a project or existing directory is used.

The result is `private/api.sqlite3`, exact surviving `private/projects/...` and `private/derived/...`, encrypted `authority.age` and private `receipt.json`. Keep authority outside `private` to respect application startup inventory. The receipt records source snapshot and latest authority hash/sequence/observation, removed/surviving file counts, final DB hash, revoked sessions and `production_activated=false`, `backup_erasure=not_attempted`, `host_drill=not_run`. A success receipt is written last after new file/directory fsync; absence means incomplete. Inspect target contents/receipt with the main agent, run the existing startup audit on the candidate and verify permissions/hashes before a separately authorized activation. The utility does not configure/start that candidate or copy it over production.

## Failure and quarantine procedure

| Failure code/category | Required response |
| --- | --- |
| `maintenance_*`, `writer_*`, `systemd_*` | Re-establish a measured stopped/masked window; account for cgroups and every writer. Never fake a proof. |
| `sqlite_sidecar_requires_maintenance_checkpoint` | Preserve main DB and sidecars; inspect with SQLite after stopping all writers. Never unlink WAL/journal. |
| `unknown_sqlite_schema`, `unknown_sqlite_revision`, derivative schema failures | Review the migrated adapter against the integration owner's new schema and rerun local hostile/migration fixtures. |
| `asset_hash_mismatch`, orphan/interrupted/private-state errors | Preserve original state and identify the exact receipt/file discrepancy under the app owner's procedure. No sweep. |
| authority hash/freshness/conflict/missing registration | Retrieve the separately trusted latest authority, verify chain/watermark and inventory. Do not bootstrap or forge a record. |
| `snapshot_retention_expired` | Select a permitted unexpired snapshot according to published policy; recovery eligibility is not evidence of deletion. |
| traversal/link/count/size/hash/tar errors | Preserve encrypted original for restricted investigation. No retry with weaker parser/limits unless the actual bounded size was independently reviewed. |
| age/authentication/identity errors | Verify trusted binary, escrowed existing key and ciphertext digest offline. Do not log key/plaintext or generate a replacement. |
| disk/full/publication interruption | Treat every new target without a valid receipt as incomplete. Preserve it privately; use a different new path. Never reuse/overwrite it. |

Temporary plaintext normally disappears when the owned scratch context exits. Filesystem deletion is not secure media erasure (SSD snapshots, journaling, pagefile/swap and volume backups can retain bytes). Protect the scratch volume accordingly. A crash/cleanup failure may leave a private `ops-*` directory under the explicit scratch parent; no success can be inferred from it. Inspect exact ownership and paths before an owner-approved cleanup; this tool does not sweep those directories or previous backups.

## Actual-host drill: main-agent recipe after review

1. Record code commit, schema revision, approved age binary/version/hash, deployment UUID, real service/activation unit list, restricted source/output/scratch paths, off-host destination and trusted latest authority watermark. Confirm no new MT migration has invalidated the adapter. Set explicit CPU/disk/time limits and verify disk headroom. All of this is private operational evidence.
2. Use a disposable operator-authorized test project/account through the real application, upload a distinctive allowed original, process it through the admitted method and record private raw/dataset/result hashes. Use a second disposable survivor project as a positive control. Do not delete a real user's project for the drill.
3. Put ingress into approved maintenance and stop/runtime-mask the exact API, worker and activation units. Example only: `sudo systemctl mask --runtime --now geophysics-api.service geophysics-worker.service`. Read state with `systemctl show`; check children/cgroups/manual jobs. There must be no active queued/running job, interrupted staging or nonempty SQLite sidecar. For a crash control, follow the host unit's fail-closed assertion, exact harness-stage preservation outside the private root and explicit operator-assisted reconciliation before this step; use only its bounded user-owned private `StateDirectory`. Issue fresh private proof with actual times. The local tool performs only the read-only observations, never this service mutation.
4. Create a restricted snapshot and authority with the exact backup command. Verify encrypted file hashes and restricted modes; copy ciphertexts/receipt off-host using the approved channel, verify remote hashes and record the authority watermark. Resume the real service only under the main agent's procedure, not from this tool.
5. Delete only the disposable first project via the application. Record its durable deletion receipt and inspect that owned raw/dataset/result endpoints return inaccessible and survivor remains intact. Confirm API does not claim backup erasure. Re-enter maintenance; checkpoint the latest durable receipts against the preceding authority; verify off-host checkpoint/hash/watermark. This does NOT simulate/close the synchronous replication crash gap.
6. While production remains untouched, restore the pre-deletion snapshot to a NEW restricted candidate with the latest independently recorded checkpoint. Record candidate DB integrity/FK/schema check, absence of deleted project rows/paths, durable receipt presence, complete survivor hashes, recalculated usage, revoked access tokens, file modes and success receipt. Run the application's existing startup audit against this isolated candidate; do not bind it to the public origin or point production config at it.
7. Execute negative drills on NEW targets: wrong trusted hash/key, old authority paired with current trusted latest hash, missing authority, malformed/linked archive, unsupported schema and interrupted publication. Record failures, unchanged source/backup/key digests and absence of a validated receipt. Preserve encrypted originals; cleanup any disposable scratch/candidates is a separate exact-path owner operation.
8. Resume original services/ingress through the reviewed release procedure, verify health and concurrent reads, confirm original production paths/config remain authoritative, and attach a private drill receipt to release review. Only main may change `host_drill` acceptance in its separate evidence; the utility's `host_drill=not_run` field intentionally never pretends a fixture is production evidence. No merge, deploy, server writes or actual drill were performed by this ops unit.

## Primary references

The [source dossier](../research/ops-recovery-2026-10-03.md) records the official SQLite backup/WAL/pragmas/VACUUM documents, age v1.3.1 command/release and official systemd manuals. The [feature design](../design/features/ops-recovery/design.md) records why maintenance and an independently fresh deletion authority are separate, non-substitutable requirements. See [convergence](../design/features/ops-recovery/convergence.md) for actual local verification and outstanding host/integration gates.
