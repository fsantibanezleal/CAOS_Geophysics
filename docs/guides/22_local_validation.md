# Local validation prerequisite runner

`scripts/validate_local.py` runs a bounded local DAG, serially, without a shell or
automatic retries. It orchestrates existing commands; it does not replace their
numerical verdicts, native science controls, deployment gates or acceptance.
Use a reviewed complete declaration. A receipt cannot discover undeclared
imports, a remote service changing, or hidden ambient input inside a command.
Declare those runtime files/installation manifests as inputs, or do not cache
that command. There is no general remote execution or service activation API.

## Configuration and command

The CLI requires `--config`, `--device-root`, `--cache-root`, `--report-root`, all
absolute. Configuration, receipts, logs, reports and each node's `TMP`, `TEMP`,
`TMPDIR` must be in the explicitly selected external device root, never a Git
repository, filesystem root or system temporary directory. Existing paths and
ancestors cannot be symlinks/reparse points. Commands must configure all of their
own generated outputs externally too; this tool is not a filesystem sandbox.

Example (substitute absolute configured paths; do not save working JSON in the
repository):

```json
{
  "schema": 1,
  "nodes": [{
    "id": "contract",
    "argv": ["<absolute-python-image>", "-B", "-m", "pytest", "tests/api/test_profile_contract.py", "-q", "-p", "no:cacheprovider", "--basetemp=<external-unique-test-root>"],
    "cwd": "<absolute-source-root>",
    "sources": ["<complete-source-file-or-directory>"],
    "inputs": ["<complete-runtime-file-or-directory>"],
    "env": {"TMP": "<external-existing-scratch>", "TEMP": "<external-existing-scratch>", "TMPDIR": "<external-existing-scratch>", "PYTHONDONTWRITEBYTECODE": "1"},
    "timeout_s": 900,
    "log_bytes": 1048576,
    "needs": []
  }]
}
```

Windows also requires explicit `SystemRoot`. Environment is replaced, not
inherited. Explicit `PATH`, runtime/case/fixture variables and output arguments
must retain the original gate's binding. Windows batch/PowerShell/shell scripts
are not executable entries; call a real interpreter with explicit arguments.
Keep browser fixture-copy, build and browser gates in the same prerequisite
chain. All nodes are serialized, including independent branches.

```text
python -B scripts/validate_local.py --config <external-config> --device-root <device-data-root> --cache-root <external-cache> --report-root <external-reports>
```

Closed schema: exactly the fields above, 1..64 nodes, distinct bounded names,
acyclic dependencies, explicit absolute executable/cwd, complete source/input
file or directory declarations (including directory membership), finite timeout
0.1..86400 seconds and combined stdout/stderr bound 1..67108864 bytes. These are
orchestration bounds, not scientific CPU, RAM or scratch caps. The whole graph
and every file are validated before spawning anything.

## Evidence and failure reuse

Each fingerprint includes exact argv/cwd/env/operational bounds, executable
bytes, harness and both dispatcher redirector and actual mapped interpreter
image bytes/version/platform, declared source
and input bytes, complete declared directory membership and predecessor
fingerprints/status/seal hashes. Hashing verifies file identity before, during
and after reads. The declaration is rechecked immediately before execution and
after completion; a changed source/input cannot produce a PASS receipt.
Directory snapshots store the SHA-256 of the canonical complete inventory,
member count and total bytes, rather than repeating every long absolute path in
the plan. Every relative name, file type, byte count and file content hash is
included; empty directories are included too. No runtime dependency is omitted
to fit the 4 MiB plan bound. A membership/content change invalidates the digest.

An exclusive fingerprint directory is created before launch, containing the
plan. Completion creates bounded separate stdout/stderr, a PASS or FAIL receipt
and a final seal of the exact four evidence files. All creation is exclusive and
fsynced. Reuse verifies plan, closed inventory, receipt and every sealed file.
Nothing overwrites an existing receipt or retries a failure. Identical failures
are reported as `reused FAIL`; dependents are `BLOCKED`; unrelated nodes continue.
A changed declared source/input/runtime/environment/predecessor creates a new
fingerprint, retaining the old failure. Log overflow is a FAIL, never silently
truncated proof represented as success.

Reuse is validation evidence only. A prior PASS does NOT prove that generated
outputs still exist, remain unchanged, or have been materialized for this run.
The runner never recreates them. Consumers of external generated artifacts must
declare/check those exact existing files as inputs, or use a separate export
verification gate. Never treat a predecessor PASS receipt as proof of current
build/dist/ZIP files. The closed DAG preflights all declared input paths before
execution, so it is designed for validators over fixed source/fixtures, not
creation of missing dependent inputs. There is no generated-output DAG schema.

A dispatcher lock refuses concurrent/unknown ownership. Abrupt interruption
leaves the lock and/or incomplete fingerprint as visible debt, never success.
There is no automatic stale-lock takeover or explicit replay feature. After
independently verifying all descendants extinct, an operator may retain the
entire old cache and choose a fresh cache root; this is an explicit new run, not
replacement evidence. Do not delete unknown locks or incomplete evidence.

Each invocation retains a new report directory, per-completion fsynced JSONL
journal and one final compact JSON report. Console prints only node
started/reused/blocked/refused, status/reason and report path. Full bounded logs
stay external. Exit 0 means all commands PASS, 1 includes FAIL/BLOCKED/REFUSED,
2 means preflight/dispatcher refusal. The original scientific/API/browser/content
assertions determine acceptance, not this return code alone.

## Local command ownership

Windows uses a non-inheritable Job Object with only
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, no breakaway permission or scientific
limits. A trusted stdlib bootstrap waits on a private `GO` stdin gate. The
dispatcher atomically enrolls it at birth with `PROC_THREAD_ATTRIBUTE_JOB_LIST`
(Windows 10 or newer), verifies membership, then releases GO. The actual
bootstrap separately queries its membership and closes the query handle before
starting any command; a launcher PID's membership is not sufficient. Creation,
membership failure or EOF cannot start the requested command. Native Win32
descendants inherit job membership. On
normal exit, timeout, cancellation or output overflow, terminate and query the
job until active count is zero before closing it. Dispatcher death closes the
last job handle and kills descendants. Tests exercise actual child/grandchild
timeout and abrupt dispatcher death, plus rejected assignment before command.
Use a native Win32 Python image for the runner. Windows Store activation
redirectors were observed escaping custody and are not qualified by successful
assignment of their proxy PID. The actual bootstrap refuses if it is outside
the selected job. Known Python Store images and venv selector files targeting
Store activation are refused during node preflight, never silently substituted.
Python venv selectors and the selected native base image are fingerprinted too.
Validators must be trusted local processes, not activation
brokers/services that launch unrelated processes outside the owned job. This
operational boundary does not change any protected science interpreter or
admission requirement.

POSIX uses an independent trusted guardian, private control pipe and new command
session/process group. The guardian watches caller EOF/cancellation and timeout,
retains its direct leader unreaped with `waitid(WNOWAIT)`, kills the owned group
before reaping, and drains output. Dispatcher SIGINT/SIGTERM closes control;
SIGKILL closes it in the kernel. This custody is for trusted local validators
whose descendants stay in the group, not hostile daemons that deliberately
escape with `setsid`, nor a root broker. Such commands are outside this lane.

The bootstrap itself has no request-command execution before GO. It is not a
paused-before-native-science admission contract. Existing protected waveform
and profile supervisors retain their separate scientific/environment controls.

Primary references: [Python subprocess](https://docs.python.org/3/library/subprocess.html)
and [Microsoft Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects),
including [Job List and Handle List creation attributes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute).

## Verification map

All gates are in `tests/ops/test_local_validation.py`:

- `test_unchanged_failure_runs_once`: immutable FAIL reuse, no rerun.
- `test_exact_binding_changes_invalidate`: source/input/executable/env/directory changes.
- `test_cached_pass_does_not_materialize_outputs`: evidence reuse cannot recreate
  or silently satisfy missing consumer artifact inputs.
- `test_predecessor_evidence_in_fingerprint`: dependency evidence invalidates descendants.
- `test_blocked_descendants_independent_continue`: fail-closed dependencies, independent continuation.
- `test_all_preflight_before_any_spawn`: cycles, missing dependencies/files, closed bounds.
- `test_changed_or_incomplete_cache_refused`, `test_interruption_plan_cannot_become_success`,
  `test_unknown_live_lock_refuses`: tamper/incomplete/interrupted/concurrent debt.
- `test_report_allocation_failure_releases_owned_lock`: report setup failure
  releases only the dispatcher's own lock.
- `test_external_paths_checked`: device/repository/system temporary boundary.
- `test_log_overflow_failed_and_reused`: bounded output, retained failure.
- `test_actual_child_grandchild_timeout`, `test_actual_parent_death_and_cancel`:
  real OS descendants, not authored cleanup receipts.
- `test_windows_assignment_failure_cannot_execute`: actual native job gate refusal.
- `test_windows_activation_selector_refused_before_spawn`: known activation
  redirector cannot start a request outside this local command lane.
- `test_windows_redirector_base_image_hash_changes`: changing native base
  image bytes invalidates the selector even if the redirector/config are unchanged.
- `test_closed_schema_rejects_boolean`: schema version is not a truthy substitute.

Tests must themselves use external `--basetemp`, external TMP/TEMP/TMPDIR,
`PYTHONDONTWRITEBYTECODE=1` and `-p no:cacheprovider`. Windows gate is platform
specific; POSIX custody tests run under POSIX. There is no UI or SQL migration.
The executable-mutation test on Windows requires `VALIDATION_COPYABLE_PYTHON`
to identify a configured standalone Python image; Windows Store activation
images are not relocatable binaries. This is a test input, not a product runtime
prerequisite. The test actually executes the copied image before and after
changing its trailing bytes, not an authored executable-hash receipt.
