# Native sealed-input receiver validation

The C receiver implements the existing 352-byte LBR1 input, fixed ancillary
storage, exact kernel sender credentials, CLOEXEC/read-only sealed inputs,
original-byte SHA-256, nonblocking receipt and owned descriptor disposal.
Its caller separately authenticates the live peer PIDFD and exact worker unit.
This is not a listener, launch authorization or production profile.

Source SHA-256:

- C: `963e7f8105f1b456de4c2838f80faa65af5736078a595ab03961f1264008e893`
- Header: `4f73a41d460562f75f91cd4282ae098f4ed6a9248ccb8f0c56b6e7e192a6c5a3`
- Final drill: `62cb8c6ef87ad89546e3e59b70877abba564df76bd41b38b82df5f35d2376d78`

The existing controller/SHA and Python codec are unchanged. The qualification
library includes existing native exports, not a production installation. Its
SHA-256 is `2ffb9de56c9a97832b3a1192aaa1339883b10b4473929fd1a3a713b4759e62e2`.

## Actual Linux evidence

Linux 6.8.0-117, GCC 13.3.0 and CPython 3.12.3 were inspected. The bounded
nonroot capability-empty build checks source/tool and 181 dependency-header
hashes before/after compilation. C17 warnings-as-errors, stack protection,
PIC, RELRO, NOW and nonexecutable stack are enabled. Build elapsed: 2.227272s.
ELF64/x86-64 imports/exports were reviewed before loading; libc is the only
NEEDED library. Current libc/loader/Python hashes match retained runtime pins.
This is not the complete production compiler-library/worker/context closure.
Build inspection SHA-256:
`d6cfdb3195d50a90e968e41ab57a3e0e346c720d26cd916e455fe7d55bdeb628`.

The initial actual socket gate passes 39 controls. The changed gate passes 46,
adding read-only unsealed/partially sealed/ordinary-file refusals, all three
hash domains, nonzero shared offsets and maximum 5MiB/64KiB/16KiB inputs.
Real SOCK_SEQPACKET/SCM_RIGHTS/SCM_CREDENTIALS, memfds and FD censuses are used.
Malformed/truncated/extra descriptors, framing/identity/cap errors, foreign
credentials, wrong sizes/hashes and writable inputs reject without leaking FDs.
No-message is nonblocking; accepted bytes/offsets persist; disposal is idempotent.

The separate capability-empty unit has a 20s wall and 128MiB test memory bound,
private network, NNP and protected system/cgroup mounts. These are test bounds,
not method profiles. It exits 0 and is actually inactive/dead afterward.
CPUUsageNSec/MemoryPeak/TasksCurrent are unavailable, not zero or measured passes.
The saved final control bytes hash to
`07620b1fe6b56f1244006df5bf4a996514117fa103eb4ee9625cef099dc9a9d5`.

Original first-run evidence is retained. No science child, service MainPID
authorization, hard storage quota or durability is proved. The full listener,
registry, LCX2, native launch, worker/storage and scientific/resource gates
remain required before production admission or a replacement deployment.
