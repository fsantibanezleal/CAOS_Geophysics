# Physical accounting tasks and approval boundary

Date: 2026-10-03. Status: design proposal, runtime NOT_RUN, admission CLOSED.
Issue: [126](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/126).
This unit delivers only new research and feature docs. Checking research/design
tasks does not check any implementation or actual OS gate.

## 1. Current authorized docs unit

- [x] D01: Preserve clean builder refs/evidence at 41f7052 and create the separate
  requested branch from freshly fetched develop 7e26d253; no other-agent switch.
- [x] D02: Read full management Entry_point, applicable ADR-0075/0069/0067/0074,
  spec/workflow/no-package conventions and approved product SDD before writing.
- [x] D03: Research official Microsoft/kernel/Linux-man-pages/systemd interfaces
  and persist dated HTTPS body hash/status/size/UTC receipts before feature design.
- [x] D04: Write exact EARS requirements, OS calls/types/units, lifecycle, strict
  profile/receipt/errors and prospective named gates covering PWA-001..015.
- [x] D05: Make monitored-enforcement versus instantaneous hard-cap limitation,
  launch authority/no-escape/backstop prerequisites and all NOT_RUN states explicit.
- [x] D06: Finish path/link/receipt/requirement audits and existing cheap docs
  guards; record actual results in review packet; commit/push this scope only.
- [x] D07: Open a draft PR to develop, self-review exact docs head and hand off
  the entire folder/research for FULL MAIN read. Do not merge or mark implementation ready.
  [Draft PR 129](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/129)
  records the exact head/self-review handoff. MAIN approval is still pending;
  no implementation or OS task is checked by this remote docs handoff.

## 2. Mandatory hold and dependency order

HOLD-01: MAIN must read ALL research/requirements/design/contracts/validation/
tasks/review packet and explicitly approve the exact docs revision BEFORE any
source or test implementation or native OS probe. A docs merge is not this
approval. Silence, an earlier product SDD approval or a previous ops test pass
does not release the hold. Approve or amend monitored versus strict kernel-hard
CPU semantics; the proposal cannot silently reinterpret a hard-zero-overshoot bar.

HOLD-02: MAIN/owner must identify actual permissible Windows credential/job-chain
policy and Linux existing delegation/launch credential/manager context. If any
are absent, that platform remains CLOSED. Do not invent a provider, new privileged
daemon, global cgroup edit, AppContainer or setuid installation as an assumption.
New security/provisioning authority requires a separately reviewed unit.

After BOTH holds, sequential future scopes (not authorized by this document):

| ID | Future work and prerequisite | Requirements | Ownership / present verdict |
| --- | --- | --- | --- |
| I01 | Pin SDK/UAPI/oracle ABI and exact allowed native helper source paths; implement bounded parsers/state machine only after assigned source scope | 001,010,014 | MAIN assigns native worker owner; NOT_RUN |
| I02 | Windows creation-time job, counters/kill/last-handle and credential/ancestor proof; after I01 and concrete context | 001,002,004,006-012 | Native worker owner; MAIN independent OS review; NOT_RUN |
| I03 | Linux birth cgroup, separate credentials/permissions, retained counters/kill/reap and existing manager death proof; after I01 and concrete context | 001,003-012 | Native worker owner; MAIN owns delegation/context execution; NOT_RUN |
| I04 | Named contract/failure unit tests and isolated actual platform controls, timing/oracle provenance; I02/I03 evidence independently per platform | 001-014 | Assigned test owner; MAIN installer/actual-host owner; NOT_RUN |
| I05 | Exact worker request/result/cancel/publication integration; requires I04 and Bacon's separately approved seven storage/migration corrections | 007,008,010,013-015 | MAIN coordinates worker, Bacon storage and API owners; NOT_RUN |
| I06 | New explicit revision/DDL/receipt/debt recovery adapter and exact module/source policies; after approved storage integration, no wildcard | 013,015 | Separate ops bounded unit; MAIN review; NOT_RUN |
| I07 | Independently review real correction/transform resource/physics/API states on each selected platform and exact pin, plus existing global capacity/deletion gates | 011,012,014,015 | MAIN admission owner; NOT_RUN |

All scientific tests, code changes, service/cgroup/Job Object setup, installation,
host drill, integration and promotion need explicit subsequent authority. No
source/test tasks are checked. Do not turn a failed/untestable platform into a
portable live-PID fallback. Documentation gate passes count only for D06.

## 3. Interface ownership and exclusions

This design owner supplies the OS contract and safe errors. Bacon owns seven
physical storage findings, lifecycle publication/cleanup debt and explicit future
migration/recovery design. The native worker owner remains unassigned until MAIN
approval. MAIN owns exact profile/security/manager review, host installation and
execution, independent verification and any deployment authority.

Current app/worker/database/API/models/migrations, private/public admission,
ops_recovery/ops_host_fixture/ops_source_bundle, all module/source inventories,
environments, canonical data and artifacts are untouched. The original encrypted
backup, keys, tombstones/authority and existing user directories are not targets.
Preserved builder branch/head and external receipts remain historical; no test
receipt is overwritten. Owner headroom decision is still absent, production
host verdict CLOSED; no host access in this unit.

## 4. Convergence

| Layer | Verdict |
| --- | --- |
| Research/interface selection and explicit limits | Authored docs; pending full MAIN approval |
| Documentation scope/cheap guards | Record measured results in review packet |
| PWA-001..015 source and named runtime tests | ALL NOT_RUN |
| Windows actual capability | CLOSED, NOT_RUN |
| Linux actual capability/delegation/manager | CLOSED, NOT_RUN |
| Physical API/migration/new recovery adapter | NOT_IMPLEMENTED / not authorized here |
| Host/release/production | CLOSED; no execution or deployment |
