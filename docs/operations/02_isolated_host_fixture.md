# Isolated Linux recovery fixture: main-owned nongate recipe

Status: code/local tests belong to the ops unit; actual Linux execution by this unit **NOT RUN**. Main owns installation, review, execution and every private host receipt. A completed disposable fixture is **nongate** evidence: it cannot close disk/admission/release, production key escrow, independently durable off-host deletion history, actual-user recovery, SMTP or live activation gates. No production change, global upgrade, service control or installer is performed by the harness.

The [separate fixture SDD](../design/features/ops-host-fixture/requirements.md) was declared after strict adapter handoff `fb3895e`. [Core operations](01_backup_restore.md) still enforce exact 0003 DDL, strict MT formats, authenticated bounded archives, fresh coherent maintenance and independently latest authority for production recovery. Fixture-only archives still cannot be restored as host archives. `--prepare-state` emits ordinary private application state, not a backup archive; later host-mode capture has genuine Linux systemd observations for this NEW disposable state only.

## Preconditions and scope

1. Main reviews the final strict MT adapter and the fixture diff, plus its separately owned cross-platform parity runtime. Main reports 84 private API tests passed, two opt-ins skipped and five Linux ZIP re-imports passed; these are **main-agent supplied**, not user-authored or ops-executed facts. The near-zero M06 residual one-ULP semantic issue must be addressed without widening tolerances. Pass a reviewed runtime's explicit full commit via `--runtime-commit`. Choose either a clean Git root (HEAD plus tracked/index/untracked/ignored cleanliness) or the independently pinned selected archive route below; both recheck source around each child stage. Keep the interpreter/environment outside the clean source root; otherwise ignored environment/bytecode files intentionally refuse this route. Use an existing read-only interpreter with dependencies; no package install/environment mutation here. Root-owned admission archives intentionally lacking `.git` do not need cloning or a global Git trust exception.
2. Allocate a dedicated owner-private parent outside every public repository, served web path, production data/config root, vault and real backup tree. Example parent `/var/lib/geophysics-ops-fixtures` must already exist privately (0700), be owner-authorized, and have trusted non-linked ancestors. The NEW child fixture root must not exist. The harness rejects existing/linked/repository/overlapping roots; it cannot infer whether an arbitrary directory is web-served or production, so main must establish that placement. Do not point it at real user state.
3. The unchanged disk guard requires at least **30%** free on that parent filesystem AND 128 MiB free before any fixture directory/key is created. The reported 29.42% host gate remains FAILED. Do not lower the threshold, compress/remove obsolete releases without user approval, or claim a pass if this blocks execution. More measured headroom may be required by main; a local guard is not an admission benchmark.
4. Main pre-provisions only two dummy services whose names match `geophysics-ops-fixture-*.service`. Their only purpose is stopped/masked fixture evidence; they are NOT production API/worker services. Minimal main-owned dummy definition may use `Type=oneshot`, `ExecStart=/usr/bin/true`, `RemainAfterExit=no`, `Restart=no`, `KillMode=control-group`, and no activation source/production paths. Main installs/controls those units separately after validating exact unit paths. The harness never creates unit files or runs start/stop/mask/reload/unmask.
5. Main accounts for every fixture writer and activation source. The fixture child uses in-process authenticated TestClient, not a bound HTTP listener; actual M05/M06 child processes complete and the app/engine close before backup. Only deliberately known fixture credentials/test auth secret are used; no SMTP or production flags/config are consulted. Closed fixture children, NEW exclusive 0700/0600 storage, and real stopped/masked dummy-unit observations provide coherence for this fixture. Dummy units alone cannot attest production quiescence or freeze arbitrary manual writers.

Main's exact-unit operations, after review, may be:

```bash
sudo systemctl mask --runtime --now geophysics-ops-fixture-api.service geophysics-ops-fixture-worker.service
systemctl show --no-pager --property=LoadState,ActiveState,SubState,UnitFileState,MainPID,ControlGroup geophysics-ops-fixture-api.service geophysics-ops-fixture-worker.service
```

Require LoadState masked, ActiveState inactive, SubState dead, UnitFileState masked/masked-runtime, MainPID zero and an empty/absent actual cgroup. The harness checks these observations before creating the fixture, then core checks them again at each fresh capture proof and before/after capture. Inadequate state fails closed. These are operations for main, not actions performed or claimed by this ops unit. Main owns restoration/cleanup of exactly its dummy unit configuration afterward; the harness does not sweep anything. Main owns any service context caps for its invocation; a masked dummy service does not place this manually invoked harness in its cgroup. No production service limits are inherited or represented as tested here.

## Immutable selected archive route (no Git metadata)

Main supplies a selected-source bundle and independently reviewed manifest after this feature's reviewed commit. No producer/installer/extractor is provided here: MAIN owns selection from exact reviewed Git objects, conversion to bounded regular USTAR, installation and source/environment provenance. The harness only reads and validates. No full clone, `git config`, `safe.directory='*'`, Git ownership workaround, dependency install or venv mutation is attempted. The explicit manifest digest must come from MAIN's trusted review channel, not be recomputed from an arbitrary host manifest and called trusted. A commit string alone is insufficient.

Use two separate immutable source roots outside repositories and production: a selected MT runtime and a selected ops root containing this implementation. The manifest must be outside both. The uncompressed `.tar` contains exactly `runtime/<relative path>` and `ops/<relative path>` regular members from those roots. Necessary parent directory members are optional; unknown/duplicate directories are not. Only USTAR headers with regular files and zero-length necessary directories are accepted. PAX/GNU/sparse/link/device members, traversal, case aliases, hardlinked installed files, unknown/missing files or directories, nonzero padding/trailing bytes and hash/size disagreement fail closed. Raw Git archives with PAX commit comments are not silently accepted: MAIN must construct the selected regular USTAR bundle and pin its resulting exact bytes. The utility never extracts that archive.

Manifest JSON schema and exact top-level keys:

```text
schema: geophysics.ops-selected-source/v1
runtime_commit: independently reviewed full 40-lowercase-hex MT commit
ops_commit: independently reviewed full 40-lowercase-hex host-feature commit
archive: {sha256: exact 64-lowercase-hex archive digest, bytes: exact integer byte count}
files:
  runtime: {each selected relative POSIX path: {sha256: exact file digest, bytes: exact integer size}}
  ops:     {each selected relative POSIX path: {sha256: exact file digest, bytes: exact integer size}}
```

No additional fields, booleans-as-sizes, duplicate JSON keys or unknown schema variants. Required paths are explicitly listed in `scripts/ops_source_pin.py`: runtime app/config/worker/MT/contracts/bundle/migrations and fixture helpers, EDI/electromagnetics/geology pipeline, original halfspace/layered EDI fixtures; ops core, host harness, source verifier and actual API fixture producer. Include the complete runtime app tree needed by those imports. The manifest must describe EVERY regular installed source file; all actual directory entries must be necessary parents of those files. Do not place a venv, pycache, metadata/receipt, Git directory, key or generated fixture inside either source tree. Additional reviewed helper files may be selected and declared; undeclared variants are refused. Caps: 4096 files, 8 MiB/file, 64 MiB selected file total and 80 MiB uncompressed archive. This is a selected-code fixture, not a full scientific release archive.

Pass all four archive options together (partial inputs fail; a failed archive never falls back to Git). Add them to the scenario command below:

```bash
  --source-manifest /absolute/private/main-reviewed-selected-source.json \
  --source-manifest-sha256 "$MAIN_REVIEWED_MANIFEST_SHA256" \
  --source-archive /absolute/private/main-reviewed-selected-source.tar \
  --ops-commit "$REVIEWED_OPS_HOST_COMMIT"
```

The harness and API producer recheck the exact manifest/archive hashes, archive member bytes, both installed source inventories and full commit bindings before imports and after each child stage. Private fixture markers and the final receipt retain the source provenance summary. These are independently reviewed byte-provenance checks, not server-derived cryptographic proof of Git history or a signature claim. MAIN must keep both source trees and manifest/archive immutable to untrusted writers throughout execution; rechecks detect drift but do not eliminate a malicious concurrent TOCTOU writer. The existing hardlinked/read-only interpreter's full environment provenance remains separate, MAIN-owned; an app-file digest is not a dependency-environment pin. No global trust changes are made even if clean Git ownership checks fail; choose the reviewed archive route explicitly.

## Explicit isolated maintained tools

Main reports installation of only official age/age-keygen/ LICENSE beneath:

```text
/opt/fasl-admission/geophysics-tools/age-v1.3.1/age/age
/opt/fasl-admission/geophysics-tools/age-v1.3.1/age/age-keygen
```

The pinned official HTTPS release-API archive digest is `bdc69c09cbdd6cf8b1f333d372a1f58247b3a33146406333e30c0f26e8f51377`, exact size 10,263,766 bytes. Main verified regular bounded tar members during isolated installation. Binary SHA-256:

| Executable | SHA-256 |
| --- | --- |
| age | `2e305637f2a0555305e21c17fb74446acbb39b53135d43d4b744e50c287133a5` |
| age-keygen | `c56ef69834e18ca4d3b953117f4481522c35fb6862a5d2871685aa4685893664` |

This is official HTTPS-digest provenance, **not sigsum proof verification**, signature verification or a reproducible-build claim. The harness recomputes both executable hashes and requires exact `v1.3.1` before writing fixture state. No downloader, installer, binary overwrite or global upgrade exists. Existing global age1.1.1 is not used. A future tool version needs reviewed provenance/pins/tests, not a hash bypass.

The harness invokes the pinned keygen only to create `fixture-identity.txt` inside its NEW restricted disposable root. No real recovery/vault key is accepted or overwritten, no key is generated in a public repo, and keygen diagnostics/identity contents never enter stdout. Keys/ciphertexts are preserved for main's private evidence; this utility does not erase them or claim secure media destruction. Main must never promote a fixture key to production escrow.

## One bounded scenario command, after review/headroom clearance

Use the existing parity-reviewed MT interpreter. Set variables to the actual reviewed full SHA and a NEW main-authorized private child path; placeholders are deliberately not production defaults. Run as the dedicated fixture owner. Working directory is irrelevant; explicit paths choose runtime and data. Do not run until main's disk and scope prerequisites are satisfied.

```bash
"$REVIEWED_MT_PYTHON" -B /absolute/reviewed/ops-checkout/scripts/ops_host_fixture.py \
  --runtime-checkout /absolute/reviewed/mt-runtime \
  --runtime-commit "$REVIEWED_MT_RUNTIME_COMMIT" \
  --new-fixture-root /var/lib/geophysics-ops-fixtures/ops-fixture-NEW-UNIQUE-ID \
  --age-binary /opt/fasl-admission/geophysics-tools/age-v1.3.1/age/age \
  --age-keygen-binary /opt/fasl-admission/geophysics-tools/age-v1.3.1/age/age-keygen \
  --units geophysics-ops-fixture-api.service geophysics-ops-fixture-worker.service
```

Sequence: platform/new-path/disk/tool/source/dummy-state preflight; NEW private state generation with original halfspace and noisy layered EDI M05/M06 plus gravity control; close writers; local fixture identity; genuine fresh path-bound systemd proof; coherent host-mode 11-file snapshot; unchanged source/ciphertext roundtrip; exact actual API disposable project deletion; fresh proof and cumulative tombstone checkpoint; pre-deletion snapshot restore with four files/all corresponding rows absent and seven survivor hashes intact, sessions revoked, quota rebuilt and tombstone present; existing app startup reconciliation on only the NEW candidate through read-only immutable SQLite (DB hash unchanged); final main-owned nongate receipt written last. No scientific inverse is rerun during restore. Snapshot limits are 32 MiB total, 8 MiB/file, 128 members, 300 seconds per core/child subprocess; child stdout/stderr are bounded during reads to 256 KiB each and never exposed as private diagnostics. SQLite/JSON bounds remain in core. Source caps above are separate. Failure preserves encrypted originals and existing user data, emits no validated scenario receipt and leaves newly owned restricted diagnostic state for main, without automatic cleanup. An interrupted actual worker's preserved `.job-staging` still requires exact operator quarantine; no unattended crash recovery is claimed by this recipe.

Outputs stay below the exclusive root: `state/case-0/private`, `state/fixture-state.json`, local `fixture-identity.txt`, `scratch`, fresh `proof-before.json`/`proof-after.json`, `backup`, `checkpoint`, `state/roundtrip`, `state/restored` and `main-owned-fixture-receipt.json`. Do not publish UUIDs, raw/result/DB hashes, keys, SQLite or proofs. The final receipt explicitly records main_owned/nongate/fixture_only=true, release_accepted/production_activated/key_escrow_tested/offhost_durability_tested=false. Core host_drill remains `not_run`; the outer fixture receipt is not a release-gate override. Local latest-authority trust in this controlled scenario is not synchronous independently durable production tombstone replication.

## CLI reuse without duplicated fixtures

The host harness uses these same actual API controls; they can be run separately by main for restricted diagnostics. Preparation creates only a NEW fixture; it creates no key, proof, backup or service. Deletion requires that exact original marker/runtime/DB/full immutable inventory, authenticates as the fixture account and can delete only the marker's recorded disposable project. A repeated, stale, unmarked, linked or repository-root request fails before deleting anything. No arbitrary project/production-source option exists.

```bash
"$REVIEWED_MT_PYTHON" -B /absolute/reviewed/ops-checkout/tests/ops/mt_drill.py --prepare-state \
  /absolute/reviewed/mt-runtime /var/lib/geophysics-ops-fixtures/NEW-state-only
"$REVIEWED_MT_PYTHON" -B /absolute/reviewed/ops-checkout/tests/ops/mt_drill.py --delete-fixture-project \
  /absolute/reviewed/mt-runtime /var/lib/geophysics-ops-fixtures/NEW-state-only
```

Only fresh source application state may be subsequently captured using the genuine host maintenance path. Never edit encrypted fixture manifests, remove `--fixture-root` to promote an existing fixture-only archive, substitute fake systemd proof or infer a host pass from the local Windows fixture tests. Review/execute before publishing any actual-host receipt; all such receipts belong to main and remain nongate fixture evidence.

For archive-mode standalone controls append `--runtime-commit "$REVIEWED_MT_RUNTIME_COMMIT"` and all four pinned archive options before the two positional paths. The producer infers HEAD only in the clean Git mode. Archive mode never invokes Git, including after preparation/deletion/audit. On any source/marker/raw/DB drift deletion fails before the API is reopened. Existing caller directories and keys are never swept or overwritten.

Local reproduction uses the existing read-only MT interpreter and explicit pinned checkout plus NEW outside-repo pytest basetemp/cache, as in [the adapter recipe](01_backup_restore.md#strict-modality-adapter-and-poincaremain-integration-contract), selecting `tests/ops/test_host_fixture.py` and then the complete ops suite. Controlled orchestration tests bridge core into explicit fixture mode; they do not assert Linux pinned binaries or actual systemd ran. See [convergence](../design/features/ops-host-fixture/convergence.md) for exact executed local counts and limitations.
