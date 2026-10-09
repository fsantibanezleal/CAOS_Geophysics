# Kernel peer identity subunit

The peer helper reads actual SO_PEERCRED and SO_PEERPIDFD from the same
AF_UNIX/SOCK_SEQPACKET socket. It retains a CLOEXEC PIDFD, rejects occupied
output handles and checks liveness before/after receiving inputs. There is no
numeric-PID pidfd_open, process-name or UID-only fallback. Unsupported headers
fail compilation; unsupported kernel options fail closed.

This authenticates neither a systemd service nor a scientific user. Exact
MainPID/cgroup/runtime/registry and nondumpability checks remain separate.
The Linux kernel retains the socket's peer struct pid rather than reopening a
later numeric identity: [reviewed Linux 6.8 implementation](https://raw.githubusercontent.com/torvalds/linux/v6.8/net/core/sock.c).

## Actual source and operations

- Native C SHA-256: `900e1014d861c5d1c8d95237e3524e8a84b138b463b7f02f44f2783e2394c515`
- Header: `4e79eab58d64ef40a7713d2f56a7390924a1faceb599c45f577efdddf3ebc4b4`
- Peer control: `3dbcb6005cbd08a86de96a1552f29749dba721b7e92c9d2d764db96218b05567`
- Library: `5a1229f544c8572a0b103ee62f6f894faabab373687aba29c39729512b6ab998`

Fresh nonroot capability-empty build checks all source/tool hashes, 44 pinned
compiler/link/runtime inputs and 181 actual dependency headers before/after.
Build elapsed 2.6931566s; ELF64/x86-64 imports/exports reviewed before load;
libc-only NEEDED, no RPATH/RUNPATH, nonexecutable stack. Retained inspection SHA:
`42aacb3d4c95251b542f32a5c66ddcd625e88f3babf1aa0a13cc8470a67b1583`.

Six actual peer cases pass: local sequenced connection and retained live PIDFD,
stream/datagram rejection, successful same-connector input, a different test
child using an inherited connection rejected by SCM_CREDENTIALS, and an actual
filesystem connector's retained PIDFD becoming unavailable after exit. The
original connector remains explicit when a socket is inherited. No PID is
reopened after exit. The FD census is unchanged, including idempotent disposal.
Test children are ordinary fixture forks, NOT native/scientific birth evidence.
Saved peer result SHA:
`c810dcc24e68d8d51d91b0844873f2b45b9b249efab2f948d8d365a414de2d9c`.

The changed library separately passes the 46 actual sealed-input regressions;
saved regression SHA:
`07620b1fe6b56f1244006df5bf4a996514117fa103eb4ee9625cef099dc9a9d5`.
The regression JSON intentionally has the same values as the prior receiver
epoch; its distinct retained command and library hash bind this new execution.
Neither receipt is scientific, service-authorization or production acceptance.

The private 20s capability-empty test units preserve NNP/private networking/
protected system/cgroup mounts. No production worker, DB or current release
was changed. Full broker/profile/LCX2/worker/publication and scientific/resource
gates remain open. Earlier source and first-run receipts remain retained.
