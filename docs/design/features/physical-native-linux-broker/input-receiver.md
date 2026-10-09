# Native input receiver implementation contract

This unit implements the receiver side of section 4, without changing LBR1,
LCX1, scientific limits, peer authorization or production profiles. The caller
must supply a connected filesystem SOCK_SEQPACKET socket already authenticated
against the retained live peer PIDFD and immutable worker-unit identity. This
unit does not substitute supplied credentials for that authorization.

The next kernel-peer subunit obtains SO_PEERCRED and SO_PEERPIDFD directly
from the same AF_UNIX/SOCK_SEQPACKET connection, retains a CLOEXEC PIDFD,
and checks its liveness before/after input receipt. Unsupported headers/kernel
option reject; there is no pidfd_open(numeric PID), name or UID-only fallback.
This still does not authenticate the manager unit, executable or registry.
Actual controls must distinguish inherited/passed socket sender credentials
from its original connector, reject stream/datagram sockets, retain a dead-peer
PIDFD rather than reopen a PID, and preserve the descriptor census.
The reviewed Linux 6.8 implementation retains the socket's peer struct pid:
[kernel getsockopt implementation](https://raw.githubusercontent.com/torvalds/linux/v6.8/net/core/sock.c).

The receiver uses exactly one nonblocking recvmsg with MSG_CMSG_CLOEXEC, a
352-byte payload and fixed ancillary buffer. It requires one three-descriptor
SCM_RIGHTS and one exact native SCM_CREDENTIALS matching the authenticated
principal. Truncated packets, duplicate/unknown ancillary records, short/long
framing, nil identities, reserved bits and excessive lengths reject. All
delivered descriptors, including unexpected extra ones, close on refusal.
EAGAIN does not block the broker loop or consume a pending command.

Before reading any body, all three descriptors must be CLOEXEC, read-only,
regular sealed shmem inputs with exact admitted lengths and all four seals.
Hashing uses the existing reviewed native SHA-256 implementation, fixed 64KiB
buffers, pread and an actual monotonic two-second total deadline. Original bytes
and file offsets remain unchanged. Success transfers exactly three retained
read-only FDs to the caller; its explicit disposal closes only those descriptors.
Fixed safe error codes contain no errno, paths or bytes.

Named actual-Linux controls: exact packet/credential/byte binding; malformed
framing and lengths; missing/extra/truncated FDs; foreign credentials; unsealed,
writable, ordinary-file and wrong-size inputs; wrong original-byte hash;
nonblocking no-message; rejected/accepted descriptor census and disposal.
The fixture must assert the reviewed ELF/source hash before loading. Missing
Linux evidence is not a skip PASS. These controls are not B02, B07..B14 or
production acceptance.

Primary semantics reviewed on 2026-10-09:
[Unix credentials and descriptor transport](https://man7.org/linux/man-pages/man7/unix.7.html),
[recvmsg truncation and CLOEXEC](https://man7.org/linux/man-pages/man2/recvmsg.2.html),
[kernel file seals](https://man7.org/linux/man-pages/man2/F_GET_SEALS.2const.html).
