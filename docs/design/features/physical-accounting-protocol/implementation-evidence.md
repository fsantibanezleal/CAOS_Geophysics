# Pure implementation evidence and review hold

Date: 2026-10-03. Approved design pin2c94da44b6205652cd2d89d73ebbf78cc4626903.
Pre-code approval persisted/pushed at49d32e6dad68334a8733f6d6ae9b6ed25c9f1f5b
before source/test creation; see
[approval](approval.md). No native/OS/profile capability evidence here.

## Test-first receipt

All twelve named requirement gates were authored in the sole approved NEW test
path before the module existed. Additional parametrized negative subcases stay
in that same file. Literal/synthetic in-memory inputs only; no source measurements,
clock/file/network/native calls or private fixture directories.

Actual local command, with authorized read-only interpreter and no install:

```text
<READ_ONLY_PYTHON> -B -m pytest --noconftest -p no:cacheprovider -q tests/worker_accounting/test_protocol.py
```

Expected RED: exit1, collection ImportError because
scripts/physical_accounting_protocol.py did not yet exist. One collection error;
NONE of the assertions executed. This is pre-implementation ordering evidence,
not twelve failed functional assertions or any accounting gate pass. --noconftest
avoids unrelated app/pipeline test fixtures; -B and disabled cache avoid local
test bytecode/cache outputs. Only ordinary test/module loading occurs.
Test-first commit:3515bb903684e53c07ade6aa176796a6e0d52241, containing all12 named
gates and this RED receipt while the source module was still absent in its Git tree.

## Actual local GREEN receipt

Implementation uses only dataclasses, enum, hashlib and json (private import
aliases). No CLI/package/caller hook or measurement surface. Returned nested
records are frozen typed objects. The session retains previous/final3 records,
bounded metadata and incremental sample digest, not a trace buffer. Required
object tokens cannot be null, and malformed invocation shapes fail held with a
fixed error rather than leaving prior success intact. No numerical tolerance.

Measured local command with the same read-only interpreter, no install, -B,
no shared conftest and no pytest cache. Override only pytest's invocation-level
addopts so its actual summary is visible; no environment/config file change:

```text
<READ_ONLY_PYTHON> -B -m pytest --noconftest -p no:cacheprovider -o addopts= -q tests/worker_accounting/test_protocol.py
```

Validated source/test pin:965b0a248bc4fd74d9047757da2a06922bcabfae. The final
documentation-only handoff preserves that pin's exact source/test Git blobs.
Actual result:419 passed in0.54s, exit0, no skip/xfail. All12 exact named gates
in requirements pass, including supplemental parametrized negatives/positives.
The duration is ordinary test-runner output, not measured native job CPU/time.
Forbidden phase/event combinations are individually asserted with exact transition
error codes and otherwise-valid trace/receipt prerequisites (no duplicate-receipt
failure substituted for a phase failure); legal transitions
use synthetic traces, not vacuous success rows. Golden counter expectations do
not call converters-under-test to produce expected values. Both platform/lane
thresholds, B+1 mismatch and first native-representable above-B finals are tested.

No actual Job Objects/cgroups/SDK/controller/profile/host, app/API/worker/database/
ops integration, scientific computation or private fixture directory. Source
remains outside existing source-bundle/manifests/runtime/admission policies.
Synthetic SHA references/flags and even protocol_eligible=true never constitute
containment/authenticity/durability/production admission; runtime_authorized=false.

Interpreter: Python3.12.10, reused read-only without dependency/environment edits.
Actual cheap guards PASS after exact staging: content standards, template residue
(860 tracked files), CI budget and git diff --cached --check. No CI/science suite
or full-runtime-suite claim. Public recipe uses an interpreter alias; private
handoff identifies the authorized explicit interpreter path, not a PATH search.

External read-only code/Git audit PASS: exactly two NEW source/test paths plus
nine own subdoc paths changed since MAIN-approved2c94da4; all12 original gate
functions already authored at the test-first commit; all12 current requirements
map to existing functions and PASS rows;44 local doc links valid; exactly the
four approved private stdlib import aliases; no eval/exec/compile/open/input/print
or dynamic import calls. All other tracked paths, including parent packet/research,
app/worker/database/models/ops/manifests/admission/source-policy blobs unchanged.
Builder local/remote41f705245116e1f9d0a2ec4555bbeb050e4dea62 preserved. This audit
is ordinary review tooling, not a measurement/interface of the implemented unit.
Final exact source commit and scoped self-review are pinned in draft PR129.

## Consumer constraints

Load as ordinary Python module, with no CLI entrypoint or package install.
Use the named interfaces in design/contracts; immutable nested returned records
are data, never callable/native capabilities. Both successful and unsuccessful
ProtocolEligibility/ProtocolDecision objects reject bool(...) with a fixed error;
read their explicit fields instead. protocol_eligible is solely stream consistency;
runtime_authorized is ALWAYS false. Direct constructors cannot select an inconsistent
success/reason variant or runtime true. Public record constructors are not accepted
session input: mutators accept only their fixed scalar/byte arguments and validate.

Unknown schemas/platforms/methods and additional keys reject. No tolerance, coercion,
bounded-size decode fallback, complete-counter zero repair or held reset. Required
start bindings/opaque token persist through samples, final3, sealed receipt hash and
release parent total. Caller timestamp assertions cannot prove actual scheduling,
silence/EOF/heartbeat timing, no-escape/finality, native counter visibility or source
integrity. There is no transport/disk receipt writer here. Python traceback frames
are not safe public fields; no trace/debug/exception serialization or logging.

## Review and native holds

MAIN independent pinned review/rerun REQUIRED before develop promotion. No merge,
OS/native controller/probe/profile/auth/storage/environment/source-policy change,
actual platform admission, source-integrity/durability proof or production action.
All15 parent platform gates CLOSED/NOT_RUN.
