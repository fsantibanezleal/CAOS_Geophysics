# Broker tasks, exact gate ownership and review order

Current: production design packet plus independently implemented literal client
input codec and sealed-memfd preparation. Its177 local transport/qualification-
context/scope tests and actual Linux input-sealing controls are recorded in
[transport evidence](../../../validation/native-broker-input-20261008.md).
No broker native build/launch/socket or app
integration executed. All B gates below NOT_RUN; native15/H01..H05 unchanged.
Project-only account/unit setup is normal scoped deployment work. MAIN owns
deploy/API/app/storage; native source owner owns the paths in design section7.

## Milestones

- [x] C1 Implement and independently check literal352-byte client input,
  corruption/cap/type/native-JSON-byte controls and owned descriptor preparation.
  Actual Linux seals/read-only/9 mutation refusals/normal/partial/caller failure
  closure pass. This is a section4 subunit, not B04/B05 end-to-end acceptance or
  production D3/I1..I4 completion. All production identity/profile seams remain.

- [x] C2 Implement the native input receiver subunit with exact packet, sender,
  sealed-byte hashing and owned FD disposal. Actual Linux controls pass39,
  then46 after added seal/hash/offset/maximum-size negatives. See
  [receiver evidence](../../../validation/native-broker-receiver-20261009.md).
  This does not close socket/unit/PIDFD authorization, production profiles,
  native launch, durability or the full B04/B05 end-to-end gates.

- [x] C3 Kernel peer subunit implements native credential/PIDFD acquisition,
  before/after receipt liveness, type refusals and explicit closure. Six actual
  peer cases and46 receiver regressions pass under fresh source/library pins;
  [evidence](../../../validation/native-broker-peer-20261009.md). This is not
  MainPID/cgroup/runtime authorization, B02/B03 or production launch acceptance.

- [x] D1 Read existing worker/MT contracts, native source, applicable ADRs and
  primary Linux6.8/systemd255 Unix socket/peer-PIDFD/nondumpability semantics.
  Retain actual bounded retrieval timestamps/bytes/hashes privately, no runtime
  assertion from documentation. Persist research before this SDD.
- [x] D2 Specify literal broker protocol, immutable allowlist, preserved worker
  sandbox, distinct science identity, actual manager-death ownership and closed
  durability/production-context seams. No generic root-launch capability.
- [ ] D3 FULL MAIN read of this complete packet; resolve exact worker startup
  nondumpability/account choice, method profile/LCX2 and durable release seams.
  No new human permission is requested; these are concrete design reviews.
- [ ] I1 Test-first native broker/client/context authoring, complete source pin,
  bounded build recipe and current private tool/header/library identity packet.
- [ ] I2 Reviewed compile; actual emitted dependency/ELF imports; reviewed ABI
  probe then pure native protocol/seal/identity tests. No OS proof by analogy.
- [ ] I3 Isolated app-specific delegated setup and real adversarial B gates;
  retain source-bound raw measurements/negative failures, no root science.
- [ ] I4 MAIN-owned API/worker/storage bridge and exact production sandbox
  replay; independently qualify every enabled method/worker/resource profile.

## Named gates (planned tests, not authored PASS)

All proposed B tests belong in test_linux_broker.py plus isolated host receipt
matrix. Absent real host receipt is NOT_RUN/error, not a passing skip or fake live
fixture. Static/unit tests use explicitly authored bytes and stay separate.

| Gate / test name | Required evidence |
| --- | --- |
| B01 test_actual_worker_socket_sandbox | Filesystem socket works under real NNP/cap-empty/PrivateNetwork/ProtectControlGroups; no worker root/systemd permission. Abstract/TCP/unsafe endpoint reject. |
| B02 test_peer_pidfd_unit_identity | Correct live MainPID accepted; same UID API, worker child/sibling, stale invocation/PID, forged identity and dead retained PIDFD rejected before launch. Unsupported peer-PIDFD CLOSED. |
| B03 test_same_uid_and_science_fd_theft | Actual ptrace/proc-FD/socket passing and signal controls, nondumpability/account choice proved; same-UID termination triggers whole group extinction. No global Yama relaxation. |
| B04 test_before_allocation_protocol | Exact352 packet/three FDs; +1/short/truncated/extra ancillary/reserved/invalid ID/unknown op/sequence/profile rejected, no FD leak/materialized input. |
| B05 test_exact_sealed_source_bytes | Exact raw bytes/hash/native JSON dialect; wrong/short/+1 hash, mutable/unsealed/ordinary path input reject; retained seals cannot mutate through writer FD after hash. No root science parsing. |
| B06 test_immutable_allowlist | No caller argv/env/UID/unit/runtime/property override; disabled/stale release/profile rejects. Existing gravity flag scope and both MT schemas/limits exact. |
| B07 test_birth_data_fd_and_venv | Actual clone3 birth/zero-cap distinct UID/GO; only RO data7/8/9 survive exec, no control/broker/cgroup/secret FD. Actual pinned Python/venv engine resolution; clone/setup/filter failure has no science marker. |
| B08 test_worker_broker_controller_deaths | Worker, broker, controller and combined SIGKILL after root exit with descendants; PID1 extinction and unavailable final retained, no publish/adoption. |
| B09 test_native_loop_independence | Broker hashing/slow client/output pressure cannot defer native sampling/kill; real G/A/K maxima, overflow/gap/unavailable counters fail. Native charge vs wait4 family oracle, no Python accounting. |
| B10 test_capacity_replay_slowloris | One live attempt, two bounded handshakes, request-rate/burst/FD/time caps; busy before launch, duplicate old IDs/partial files/stale unit held. Concurrent qualification sibling excluded from charge. |
| B11 test_cancel_and_control_binding | Wrong principal/object/attempt/sequence, EOF/lost heartbeat/repeated START/early ACK/wrong digest; whole-group stop and sticky error; no unrelated cancellation. |
| B12 test_final_durability_release | Exact raw native transcript plus result/source/parameter/runtime/owner identities; real worker/storage intent+commit+receipt fsync before ACK/release, crash/uncertain commit/full disk remain HELD. MAIN storage integration required. |
| B13 test_complete_parent_cpu_and_resources | Actual broker/controller/worker tails through publication, memory distinct RSS/memcg, enforced scratch/result quotas, cold/nominal/upper/malformed/crash measurements under exact enabled method. No sampled inventory labelled hard quota. |
| B14 test_source_science_regression | Unchanged MT tensor/units/fixed-h/conditional uncertainty/actual parameter effects and cl061 QC-only; gravity flag and M13/canonical invariants. Native gate is not numerical or field eligibility. |

## Current evidence and handoff

The existing e4 controller packet and historical339 local tests remain distinct
from the fresh system-CPU fixture control. Fresh controller code/test hashes and
private manifest are provided separately at its next freeze. No controller code
was relabelled as production broker; no original evidence overwritten. Full
scope guard, source pin and current actual local receipt accompany the handoff.
All broker/native admission and whole-method acceptance remain pending measured
Linux proof. This packet requests immediate full technical seam review while
the already authorized native qualification source continues independently.
