# Native CPU controller full pre-code review packet

## Current measured I01 evidence

The original documentation-only review below is retained as historical evidence.
Actual I01 build, Windows SDK layout47 and compiled-pure179 PASS0skip are recorded
separately in [the measured receipt](../../../validation/native-i01-abi-pure-20261004.json).
The [worker operations supplement](worker-operations.md) specifies the next real
native operation boundary. No historical docs result is relabelled as execution;
all platform/security/resource/parent-tail/durable-release gates remain distinct.

## Original pre-execution review

Date: 2026-10-03. Status: original67c621c FULL MAIN read; narrow I01 authoring
approved, compiler execution and later amendments pending separate review.
Issue [140](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/140).
This milestone contains docs only. Source/test authority is narrowly recorded
in [approval](approval.md); native/platform/profile/host authority is NOT granted.
[Draft PR145](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/145) targets
develop. Its exact-head self-review/final handoff identifies the stable packet;
it is not merged. Approval was persisted at914a4bbe BEFORE any new source/test.
The [read-only build inventory and unexecuted recipe](build-inventory.md) require
a NEW exact MAIN decision before any compiler/linker/compiled test or probe run.

## 1. Exact immutable context and complete read order

Branch: task/geophysics-native-cpu-controller-sdd.
Isolated base: ba54d32f0932a09502f463f3aff9c8f21270dca1, clean before this unit.
Preserved builder:41f705245116e1f9d0a2ec4555bbeb050e4dea62.
Preserved pure:3bedfe0bad821b3638cd9e7de718f7232a0198e7, source/test bytes
unchanged from965b0a248bc4fd74d9047757da2a06922bcabfae and merged throughPR129.
Base is retained intentionally; later develop evidence changes are not folded
into this bounded branch or claimed as newly tested native capability.

MAIN fully read/accepted parent direction at3959ffc and pure design at2c94da4;
pure419 suite plus43MAIN independent supplied-record checks are existing evidence.
They remain distinct from all15 original native gates, CLOSED/NOT_RUN.
MAIN accepted monitored aggregate accounting, NOT instantaneous zero overshoot.
The new packet concretizes a native implementation candidate without authorizing it.

Read ALL seven files in order, not only requirements or the Windows route:

1. [Research,34 fresh official HTTPS receipts and installed source/toolchain inventory](research.md).
2. [Sixteen EARS requirements and exact future gate names](requirements.md).
3. [Concrete source paths, native bindings/lifecycle/budgets and unresolved integration](design.md).
4. [Fixed private wire, unchanged pure bridge contracts, safe errors and custody](contracts.md).
5. [Test-first ABI/actual OS controls, adversarials/oracles/timing and crash matrix](validation-plan.md).
6. [Ownership, dependency sequence and H00..06 holds](tasks.md).
7. This packet, measured docs checks, exclusions and decisions to request.

The original67c621c milestone contains exactly these seven new Markdown files.
The next bounded milestone adds approval.md/build-inventory.md and updates five
of the original own docs; no source/test/probe exists yet. Parent packets and
pure code/tests remain unchanged. No code/prerequisite helper/fixture file is
created merely to validate the inventory. Human-only Git
authorship, no package/installer or deploy commands, no merge.

## 2. Concrete proposals for MAIN to approve or correct

- Direct C17 SDK/UAPI native executable plus bounded Python bridge to unchanged
  pure module. No ctypes-packed ABI, pywin32 install, Python preexec callback,
  Popen child assignment after start, shell or generic provider hooks.
- Windows JOB_LIST creation plus suspended readback/resume1; fresh fixed user-time
  SECONDARY backstop, process/affinity/kill-on-close flags, total user+kernel
  lifetime charge and exact last-handle death/no-broker/duplication prerequisites.
- Linux clone3 INTO_CGROUP/PIDFD in a fresh retained domain, native credential
  setup beforeGO, strict cpu.stat lifetime parsing, cgroup.kill/reap/finality and
  exact existing manager context. No current Linux capability or delegation claim.
- Fixed native64-byte header/kind payload schemas and independent nonblocking
  observation loop. B60/240,S57/237,M3 unchanged; G/A/K/Q/N are actual admission
  obligations, not vendor scheduling promises. CPU>B alwaysFAIL.
- No complete production release while parent tail/final custody and durable
  storage/recovery seams H04/H05 are unresolved. Complete finite-fixture lifetime
  oracle is not a production supervisor that already exists.
- Proposed new implementation paths and16 native gates are exact but absent.
  Implementation/test/native compilation requires explicit separate authorization;
  actual Windows/Linux context and profile admission still require their own evidence.

## 3. Unresolved mechanisms, not hidden behind digest/status

H01 effective Windows token/DACL/job ancestry/handle/broker denial;
H02 effective Linux credentials/delegation/control ownership/manager death;
H03 supported max visibility/rounding/gap/kill/drain bounds under monitored risk;
H04 full controller/worker final-write/exit/publication CPU and final custody;
H05 durable file+intent/ack/release, uncertain commit/deletion/quota and explicit
new schema/DDL/recovery adapter; H06 per-platform native ABI/binary provenance.
No existing caller, manager or external authority provider is fabricated to
resolve them. Windows compiler/header bytes are available to inspect, but not
a tested toolchain or credential context. Linux toolchain/host context absent.

If MAIN cannot provide/approve a concrete mechanism, that platform or integration
remains CLOSED, not a source scope quietly accepted as whole runtime approval.
Docs approval alone cannot activate a profile, relax headroom, install a binary,
touch OS objects/services, patch a worker or expand current ops inventory.

## 4. Historical original67c621c documentation validation evidence

Actual local docs verification on2026-10-03, using the existing read-only
CPython3.12.10 interpreter alias (exact private path in handoff), -B, no installs:

```text
<READ_ONLY_PYTHON> -B scripts/check_content_standards.py
<READ_ONLY_PYTHON> -B scripts/check_template_residue.py
<READ_ONLY_PYTHON> -B scripts/check_ci_budget.py
git diff --cached --check
```

All four PASS after staging the seven docs so tracked guards include this scope.
Template guard inspected895 tracked files. Actual read-only inline PowerShell
audit PASS: exactly seven allowed added paths,16 EARS requirements and16 exact
gate names in validation,31 valid local Markdown links, all34 receipt table
rows equal to original bounded HTTPS metadata, no protected-path diff fromHEAD.
Builder41f and pure3bed refs remain unchanged; pure source/test SHA values match
550a49d5b6ab3ec289f0c8722339c4a84af1d3b59e2786febce3c6d5566be622 and
662c9b1e0cf642b9ec0cea79bde897885752d4255188fc71de70e19ff3ce9215.
No proposed native/test/probe path is created. Scope is only seven new docs.

These are documentation evidence, NOT ABI/OS/native capability. No scientific,
pure-producer or native suite was run for this docs delta. Existing
check_sdd_convergence validates the unchanged product ledger, not native gates;
it is not reported as native convergence. No scripts/check_sdd.py exists atbase.

## 5. New inventory and amendment review, before compiled tests

MAIN FULL read original67c621c and authorized the exact deterministic core and
three test paths plus optional ABI probe; see the committed approval record.
This does not approve two later material docs changes: DRAINED payload16->24
with an explicit drain timestamp, and waiting the admitted50ms BEFORE first
final read (three equal reads over40ms alone do not cover50ms visibility).
Contracts/design/validation mark those amendments PENDING. Do not adopt them in
source until MAIN reviews the exact amended packet. Native100ns/1000ns quantum
versus supplied B+1ns clarification is also identified, not fictional OS data.

Build inventory binds actual cl/link, all90 compiler-directory files, four
include roots, static/import libraries, CRT and named system dependency bytes.
Static PE import reads are actual; loaded dependency/ABI evidence is NOT_RUN.
Python's local VC runtime14.42 is older than compiler-local14.43; System32 is
14.50. No assumption that a /MD test DLL selects System32's newer runtime.
Request /MT ONLY for the deterministic test DLL/ABI probe with five explicit
hashed static libraries, no cross-boundary CRT-owned memory. The future native
runner /MD remains unchanged/CLOSED. This choice needs MAIN compiler review.

The build-inventory packet contains the exact read-only observations,49 file
hash rows, five root hashes, eight NEW bounded official HTTPS receipts and full
UNEXECUTED compile/link/probe/test commands. The original34 research receipts
remain unchanged. No toolchain/interpreter/OS environment or output root changed.
No new source/test/probe or compiled result exists; test-first RED/GREEN is next
after the mandatory inventory decision, not silently reported as already run.

Actual new read-only/docs evidence on2026-10-03, same approved interpreter -B:
content standards PASS; template residue PASS across897 tracked files; CI budget
PASS. Nine-path/base scope audit PASS,44 relative Markdown links resolve, two
pure protected hashes PASS, original research/requirements byte-unchanged at67.
Source/tests/probe paths and proposed private output root all ABSENT. Inventory
has49 well-formed file hashes and five root hashes. Parsed recipe contains only
assignments/Join-Path: bound compile argument arrays23/23, link arrays21/20.
That check evaluated string/path assignments only; no tool or generated binary
was launched. Initial expected compile argument count21 was a checker error,
corrected to actual23; no compiler/test result was substituted for this check.
An initial extra blank line at inventory EOF was corrected before final whitespace
validation. Final guards/whitespace are rerun after staging the complete packet.

## 6. Nonclaims and final handoff requirements

No actual Job Object/cgroup, compiled controller, measured job CPU, launch token,
manager policy, OS profile, parent finality, durable receipt/release or migration
implemented. No installation, environment modification, VPS/production access,
service change, package, source/native fixture generation or shared source edit.
The original15 native gates and all16 new gates remain CLOSED/NOT_RUN. Supplied
pure protocol runtime_authorized staysfalse. Source128/131/L2 scientific or
protocol evidence is not OS proof. New physical child restore is NOT supported
by existing0003 adapters; no wildcard/future revision acceptance is added.

MAIN supplied earlier actual host disk29.42% against unchanged30% gate; this
unit did not remeasure it or obtain owner authorization. Host drill/production
activation remain CLOSED. Existing failed controls and immutable encrypted
backups/deletion authority remain preserved, not replaced by these docs.

Final handoff identifies the full pushed SHA, draft PR/base, exact nine new docs
relative tobase (seven original plus approval/build inventory), actual checks and
receipt inventory. MAIN must review the inventory and pending amendments before
compiler execution or amendment adoption. Native OS work has NO authorization.
