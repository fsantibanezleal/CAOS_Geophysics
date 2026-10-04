# App-specific native Linux launch broker requirements

Status: SOURCE DESIGN FOR FULL REVIEW, not implemented or admitted. This is a
separate production seam for the [native CPU controller](../physical-native-cpu-controller/linux-systemd255.md).
The existing controller is qualification-only; its resource classes and private
protocol do not activate a method. No API/worker/unit/environment changes are in
this packet. Necessary project-only provisioning is normal authorized deployment
work, not a missing permission prerequisite. Full design/source/build/import
reviews and measured execution remain separate technical boundaries.

## Scope and threat boundary

The worker stays unprivileged with NoNewPrivileges, empty capabilities,
ProtectControlGroups and PrivateNetwork. A root-owned native broker authenticates
one exact worker service process and constructs only an immutable allowlisted
scientific launch. Neither API nor worker obtains root, arbitrary systemd access,
caller-defined commands, capabilities or writable cgroup descriptors. Science
starts accounted by clone3, then loses privileges before its READY/GO barrier.
The API's database/project authorization remains the API owner's contract; Unix
peer credentials are not authentication of the scientific user's ownership.

Same-UID API/worker services are distinct principals at this boundary. Peer UID
alone is insufficient. Same-UID ptrace/FD theft must also be denied by actual
worker nondumpability or a separate account; empty capabilities/ProtectProc alone
are not proof. This seam never weakens the worker sandbox or changes global Yama.
Root compromise and a deliberately compromised authorized worker remain outside
the Unix authorization guarantee; fixed profiles still restrict its launch
authority. Attempts, source identity and owner/project/job lineage stay explicit.

## Required behavior

| ID | Exact requirement and negative |
| --- | --- |
| LBR01 | Filesystem AF_UNIX SOCK_SEQPACKET only, root-owned endpoint ancestry, mode0660 and exact configured worker group; no TCP, abstract socket, public second origin, sudo, setuid helper or PolicyKit grant. Test under actual PrivateNetwork/mount restrictions. |
| LBR02 | Require native SO_PEERCRED and SO_PEERPIDFD; retained live peer must equal exact worker service MainPID, cgroup identity, executable/runtime identity and configured UID/GID. API same UID, child/sibling/stale process, changed unit and unsupported peer-PIDFD reject. No later numeric-PID open as fallback. |
| LBR03 | Actual worker PR_SET_DUMPABLE=0 before connecting, or distinct worker UID under separately reviewed configuration. No signal/ptrace/FD acquisition by same-UID API or science. Worker death must kill the whole attempt even when its root already exited. |
| LBR04 | One production attempt at a time; listener has bounded pending handshakes and no stored job queue. Busy returns safely before launch; no auto retry/adoption. Two independent qualification accounts are for isolation testing, not a production concurrency grant. |
| LBR05 | Fixed binary352-byte SUBMIT with exactly three sealed input memfds. Validate framing/types/FD count/size/seals before reading or copying. Unknown operation/profile/runtime/schema/extra ancillary data rejects. No request paths, argv, environment, unit properties, UID or cgroup names. |
| LBR06 | Stream SHA256 over exactly declared bytes of retained sealed source/parameter/lineage FDs; reject +1/short/nonregular/unsealed/writable input. Hash actual bytes, never scientific JSON reserialization; no root science parsing or imports. Preserve all existing method/parser/parameter/owner/source validation after unprivileged GO. |
| LBR07 | Root-owned immutable deployment registry fixes runtime, entrypoint, method ID, input/output limits, environment, UID allocation and unit properties. Qualification LCX1/classes1/2 are not production profiles. Missing/unmeasured profile stays disabled without inventing scientific eligibility. |
| LBR08 | Dedicated per-attempt unit binds to both exact worker and broker service; root native observer is sole delegatee. Science gets distinct nonroot account, no groups/capabilities/control FDs/network/namespace authority. clone3 denied or incomplete setup has no science marker. |
| LBR09 | Broker work cannot defer independent native CPU observation/kill. EOF/cancel/backpressure/broker death kills the entire job; manager crash backstop is not native250ms kill proof. No Python wait/rusage/live-PID aggregation. |
| LBR10 | Bind source, config, lineage, runtime/profile, attempt/job/project/owner and immutable native transcript to retained result identity. CPU availability does not mean scientific or resource pass. File/DB durability/publication tails remain separate storage/worker gates; local ACK alone cannot pass them. |
| LBR11 | Safe fixed error codes, no private bytes/paths/secrets/exception context. Retain first failure, original output and unknown-state custody; never reopen/retry/delete an uncertain prior attempt. Bounded diagnostics cannot be labelled whole-output capture when truncated. |
| LBR12 | Pin native sources, compiler/header/library closure and exact recipe before compile; inspect emitted ELF imports before ABI or controller execution. Actual adversarial qualification and production sandbox replay precede admission. No fixture, skipped gate or Windows pure result becomes Linux/whole-method acceptance. |

## Scientific and ownership invariants

Existing gravity station outlier flagging stays correction/QC, not a physical
inversion. Exact MT method IDs, full tensor screen, units/sign/variance/rotation,
fixed-thickness assumption, conditional uncertainty, parameter effects, raw EDI
hashes and Clear Lake cl061 ineligibility remain unchanged. An allowlisted launch
does not establish field truth or accept unsupported methods. M13/checkpoints,
canonical scientific artifacts, legacy adapters and client view states are not
edited. Method resource proofs are required independently, not inferred from a
finite native fixture or a successful API transport test.

No generic512MiB device claim, SMTP/off-host backup requirement or arbitrary
disk-percentage gate is introduced. Storage must instead enforce the actual
measured per-attempt byte/quota/reserve and uncertain-write behavior. This design
does not implement that storage subsystem or waive its gates.

## Acceptance

All named gates in [tasks](tasks.md) are pending actual implementations and raw
measured evidence. The [design](design.md) fixes the request, unit topology,
authorization and child descriptor contract for full review before authoring the
broker. Current local controller tests validate source/transport only; no broker
binary, socket, production controller or live admission is claimed here.
