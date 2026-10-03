# Paired selected-source builder: local object provenance, not production trust

The [builder SDD](../design/features/ops-source-bundle/requirements.md) was fully reviewed at `85d3bfc` and explicitly approved before implementation. This ordinary R-HFIX-06 prerequisite builds selected public code and two named public EDI test fixtures from exact local Git objects. It does not build a release, install/extract code, fetch objects, generate keys, access production/private app state, alter environments, control services or run the Linux drill. MAIN's independently reported PR112 validation is 180 pass/two Windows privilege skips/one upstream warning in282.70s against fresh parity59f; it is MAIN evidence, not this builder's execution.

## Primary-source basis and policy

This source-only Git-blob helper produces local provenance evidence, not restore support for unknown future child/result modalities.

[Official Git command documentation](https://git-scm.com/docs/git) specifies no-replace-object and no-lazy-fetch controls plus optional-lock suppression and literal pathspecs. This helper clears inherited `GIT_*` selectors/config/trace/alternate injection, establishes its own offline/noninteractive settings and uses those command flags. Global/system config are not loaded and never edited; no safe.directory exception is installed. Repositories with partial/promisor configuration, promisor pack markers or object alternates are refused, even with no-lazy-fetch set. Trusted local repositories must already have the required objects. An unavailable Git option or dubious ownership fails closed, not an upgrade or bypass.

[Git cat-file](https://git-scm.com/docs/git-cat-file) provides raw object contents/type/size; the helper uses exact full object IDs with no textconv, filters or LFS hydration. [Git ls-tree](https://git-scm.com/docs/git-ls-tree) provides tree modes/types/OIDs and NUL-terminated paths. The helper verifies raw commit, tree and blob object hashes, follows immutable tree entries for literal selected paths and records that chain. No selected filesystem content is read, so dirty/deleted/untracked worktree files do not enter the archive and remain untouched.

[Git archive documentation](https://git-scm.com/docs/git-archive) states that tar archives from commits carry a global PAX commit header and may apply export attributes. The existing HFIX verifier correctly forbids PAX/GNU variants. This helper does NOT call git archive or alter its tar output; it constructs normalized files-only USTAR from verified blob bytes. Git content addressing is source integrity, not encryption/signature/key-authority proof. SHA-256 in the compatible manifest binds exact transmitted bytes; no custom cryptography is introduced.

## Exact selection and provenance prerequisites

The trusted installed Git executable may be a regular hardlink (the maintained Windows Git installation uses these). Only this read-only tool-provenance check permits that link count; it records and rechecks the executable hash/link count and rejects symlink/reparse/special paths. Every source-object/output path retains the frozen strict no-hardlink guards. MAIN must independently establish the installed Git distribution and helper trust; hashing the PATH-selected launcher cannot authenticate its dependencies or its producer.

MAIN must provide explicit canonical local Git worktree roots, independently reviewed full40 lowercase-hex runtime/ops commits, an independently reviewed SHA-256-pinned selection JSON outside repositories, one explicit nonnegative epoch (0..2147483647), and a NEW owner-private output child outside repositories/production/served/vault/backup paths. The existing private parent must be0700 on POSIX and have trusted non-linked ancestors. The builder cannot infer arbitrary web/production placement; MAIN establishes it. Git executable, invoking helper and local repository ownership/immutability are trusted prerequisites; no script can authenticate its own already-corrupt execution.

Selection schema: `geophysics.ops-source-selection/v1`, EXACT keys `schema runtime_commit ops_commit files`; `files` EXACT `runtime ops`, each a sorted unique relative POSIX path list. Full commits must match the CLI. No refs/tags/branches, absolute/relative source ambiguity, extra fields, duplicate JSON keys, case aliases or path traversal. Lists must equal the precise published policy: frozen verifier-required paths plus all27 reviewed app source/config/migration paths for the runtime, named EDI/electromagnetics/geology modules, the two API helpers, and the four frozen ops code/producer files. No generic app/ or data/ prefix relaxation. The two public EDI paths are the only scientific input exceptions: `data/fixtures/edi/halfspace-100-native.edi` and `data/fixtures/edi/two-layer-noisy-rotated.edi`. No data/downloads, private/user raw, SQLite, archives, keys, native binaries, environment/bytecode/package artifacts or LFS pointers. A future additional module requires a reviewed policy change, not an arbitrary selection entry. Content checks for native/SQLite/archive/LFS/private-key markers are defensive only; MAIN must review all selected public source for secrets. No exhaustive secret-scanner claim.

MAIN constructs/reviews the selection from the published policy and exact Git commits before invoking the builder; hashing an arbitrary unreviewed selection and trusting that digest is not review. The helper does not authorize its own selection. Paired outputs remain selected-code source evidence; MAIN separately pins the helper commit/tool provenance and retains independent interpreter/environment provenance.

The exact 34 runtime paths are listed below. Ops selection is exactly `scripts/ops_recovery.py`, `scripts/ops_host_fixture.py`, `scripts/ops_source_pin.py`, `tests/ops/mt_drill.py`; both selection lists must be sorted lexically. MAIN binds the reviewed full commits in the selection JSON as well as on the CLI. There is no generated default selection or automatic trust in a file produced from this list.

```text
app/__init__.py
app/alembic.ini
app/auth.py
app/bundle.py
app/compute.py
app/config.py
app/database.py
app/errors.py
app/formats.py
app/main.py
app/migrations/env.py
app/migrations/versions/0001_api_foundation.py
app/migrations/versions/0002_private_storage_permission.py
app/migrations/versions/0003_processing_jobs.py
app/models.py
app/mt_bundle.py
app/mt_compute.py
app/mt_contract.py
app/processing.py
app/processing_contract.py
app/processing_storage.py
app/projects.py
app/schemas.py
app/security.py
app/server.py
app/views.py
app/worker.py
data-pipeline/edi.py
data-pipeline/electromagnetics.py
data-pipeline/geology.py
data/fixtures/edi/halfspace-100-native.edi
data/fixtures/edi/two-layer-noisy-rotated.edi
tests/api/conftest.py
tests/api/test_online_mt.py
```

Selection structure (substitute both reviewed full commits and the exact sorted inventories above, not literal ellipses):

```json
{"schema":"geophysics.ops-source-selection/v1","runtime_commit":"FULL_REVIEWED_RUNTIME_COMMIT","ops_commit":"FULL_REVIEWED_OPS_COMMIT","files":{"runtime":["...exact 34 names..."],"ops":["...exact four names..."]}}
```

## Local build command

Run on MAIN's already authorized Git-owning workstation, never on production or archived Linux source. No install needed (stdlib helper).

```bash
"$EXISTING_PYTHON" -B /absolute/reviewed/ops/scripts/ops_source_bundle.py \
  --runtime-repo /absolute/trusted/local/mt-git-root \
  --runtime-commit "$REVIEWED_MT_FULL_COMMIT" \
  --ops-repo /absolute/trusted/local/ops-git-root \
  --ops-commit 5bc20eb3253c88c0cd903ccf06fc42aeb2a26b77 \
  --selection /absolute/private/main-reviewed-selection.json \
  --selection-sha256 "$MAIN_REVIEWED_SELECTION_SHA256" \
  --epoch 1790985600 \
  --new-output /absolute/private/NEW-selected-source-bundle
```

PowerShell uses the same flags with `& 'C:\absolute\existing\python.exe' -B 'C:\absolute\reviewed\ops\scripts\ops_source_bundle.py'`; pass explicit Windows canonical roots and a NEW restricted parent/output. No environment epoch/default commit/cap override. The epoch is an explicit reproducibility input, not an assertion that a build/commit/event occurred at that time. Repeated identical inputs produce identical archive and compatible manifest bytes; observational timestamps live only in the separate provenance receipt.

The builder prevalidates selection/root/object type/mode/size/content/hash and total caps, then atomically creates ONLY the exact NEW output0700. Existing or linked outputs/parents fail without changes. Files are exclusively created0600. Each member is a regular FILE with sorted scope/path name, uid/gid0, empty names, mode0644, one explicit epoch and zero padding; no directory/link/PAX/GNU headers. Modes100644/100755 from Git are recorded in provenance but normalized in tar. Caps remain4096 files,8MiB/file,64MiB selected bytes,80MiB final archive. Commands/diagnostics/object reads and whole build time are bounded, private child diagnostics are never printed. No API/scientific computation occurs.

Outputs: `selected-source.tar`, compatible `selected-source.json`, and `build-receipt.json` written last. The existing `geophysics.ops-selected-source/v1` manifest is UNCHANGED: full two commits, exact archive SHA/bytes and each scope/path SHA/bytes, no provenance fields added. Separate `geophysics.ops-source-build/v1` receipt records selection hash, commits/trees/tree chains/blob OIDs/modes, per-file SHA/size, epoch/policy/tool provenance and archive/manifest hashes, completed/source_only=true and production_activated/release_accepted/key_authority_verified=false. Fsync output files/directory before completion. Failure preserves existing data and leaves newly created partial private diagnostic output with NO completion receipt; no automatic cleanup, erasure or overwrite.

Receipt publication atomically refuses an existing final filename. Its temporary second hardlink is between ONLY our NEW receipt files and is removed before completion; failure preserves pending diagnostic evidence. This is not permission to admit linked archive/source/installed files.

## Independent MAIN review and handoff

Compare receipt commit/tree chains and each mode/path/blob OID to exact trusted Git objects independently. Recompute each blob hash/size, archive hash/size, every member hash/size, and manifest digest. Confirm expected sorted normalized USTAR headers and no extensions, and compare the selection to the reviewed exact policy. Receipt creation is not proof that its producing machine/helper/Git binary was trustworthy; MAIN must establish those prerequisites independently. Commit identity alone is insufficient, and this is not a signature/sigsum/Git-history-authentication or production authority proof.

Read-only independent Git checks, from each already authorized explicit Git root (no global trust/config changes): `git --no-lazy-fetch --no-replace-objects --no-optional-locks cat-file -t FULL_COMMIT`, `git --no-lazy-fetch --no-replace-objects --no-optional-locks cat-file commit FULL_COMMIT`, `git --no-lazy-fetch --no-replace-objects --no-optional-locks ls-tree -r -z --full-tree ROOT_TREE -- EXACT_SELECTED_PATHS`, then `git --no-lazy-fetch --no-replace-objects --no-optional-locks cat-file blob EXACT_BLOB_OID`. MAIN independently clears inherited Git redirection/config/trace variables as in the helper and reviews raw trees, OIDs, modes, lengths and SHA-256; do not replace these checks with `git show HEAD:path` or filesystem reads. No fetch, mutable-ref selection or `git archive` is needed.

MAIN owns immutable regular installation into two NEW selected source roots outside production and repositories; this helper never extracts/installs. Preserve selection/bundle/receipt originals, transmit the independently trusted manifest digest through the review channel, and use the [HFIX protocol](02_isolated_host_fixture.md#immutable-selected-archive-route-no-git-metadata): `--source-manifest`, `--source-manifest-sha256`, `--source-archive`, `--ops-commit` plus explicit reviewed runtime commit. The HFIX verifier rechecks the exact installed inventories and archive around children without Git metadata. Existing read-only interpreter/environment provenance remains separate; no Linux clone/global trust/install shortcut.

Actual host execution by ops: **NOT RUN**. MAIN-reported29.42% disk remains below unchanged30%; owner authorization/headroom must be resolved before any actual Linux nongate fixture run. A source bundle or successful private fixture cannot close production keys/latest durable deletion history, disk admission, real-user restoration, SMTP or activation. MAIN owns eventual private nongate host receipts. [Executed local convergence](../design/features/ops-source-bundle/convergence.md): 250 passed/three Windows symlink-privilege skips/one existing upstream warning in300.06s, including70 builder passes. These are local selected-source/fixture controls, not actual Linux or production acceptance. Unknown future M01/child/result identities remain unsupported pending their separately reviewed adapter.
