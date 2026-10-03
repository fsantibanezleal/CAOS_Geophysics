# Physical worker accounting full review packet

Date: 2026-10-03. Status: docs-only proposal; full MAIN read/approval required.
Issue [126](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/126),
related [80](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/80).
Draft review [PR 129](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/129)
targets develop; it is not merged and grants no source/native execution authority.
The PR head SHA and pinned self-review comment identify the final docs handoff;
FULL MAIN approval remains pending for both platform implementations.

## 1. Immutable context and read order

Branch: task/geophysics-physical-worker-accounting-sdd.
Fresh origin/develop base: 7e26d253ac7d3a3688cb6263f669a747681aa077.
Preserved builder local/remote branch: task/geophysics-ops-source-bundle,
head 41f705245116e1f9d0a2ec4555bbeb050e4dea62. Existing evidence is not modified
or reused as CPU containment proof.

Physical design reviewed input: Bacon
e422d94c2c89247c79939cc3de6ae10d16784023, design.md lines 54-65.
The new unit resolves review gap 8 at contract/design-selection level only;
actual-platform capability, approval and any provisioning remain unresolved.
Bacon owns the other seven storage/migration findings. No edit to his docs.

Full review order:

1. [Dated research and 34 primary HTTPS receipts](../../../research/physical-worker-accounting-2026-10-03.md).
2. [Requirements and 15 prospective gates](requirements.md).
3. [Design: budgets, calls/ABI, both OS lifecycles, no-escape/death and limitations](design.md).
4. [Strict private control/profile/counter/receipt/error contracts](contracts.md).
5. [Prospective validation, independent oracle, actual platform negatives and caps](validation-plan.md).
6. [Dependency tasks, explicit holds and ownership](tasks.md).
7. This packet, scope/validation/verdict. Read the whole set, not only the CPU table.

## 2. Concrete MAIN decisions before source authority

- Accept/amend monitored aggregate enforcement with S=B-3 s, final CPU<=B,
  measured maximum timing/lag/kill bounds and closed-profile behavior. Stock
  Linux bandwidth and Windows user-time APIs do not prove an instantaneous
  user+kernel hard limit. If that is the required bar, keep CLOSED and research
  an alternative; don't approve an unknown fallback.
- Accept exact Windows JOB_LIST plus suspended verification and Linux
  clone3 INTO_CGROUP protocols, native-only pre-exec path, integer counter
  units and receipt/null-unavailable semantics. No current ABI probe has run.
- Identify actual existing credential/job/delegation/manager contexts or leave
  platforms CLOSED. No hypothetical provider/delegation daemon may be treated
  as present. Any required provisioning/token/security policy is a separately
  approved unit, not a permission acquired by merging this SDD.
- Accept typed safe errors, control/log/sample caps, independent parent budget
  and strict whole-object drain/ack/release ordering; storage debt release is
  separately Bacon-owned and must outlive uncertainty.
- Assign the future native-worker/source and test owner, constrain paths and
  approve concrete oracle ABI/resolution before implementation/testing.
- Preserve explicit future revision/DDL/admission/module/source-policy review
  boundary. Current 0003 recovery and source bundles are not expanded here.

## 3. Documentation verification

Measured locally on 2026-10-03, using MAIN-authorized read-only MT interpreter
with -B and no installation or environment edits:

```text
<READ_ONLY_PYTHON> -B scripts/check_content_standards.py
<READ_ONLY_PYTHON> -B scripts/check_template_residue.py
<READ_ONLY_PYTHON> -B scripts/check_ci_budget.py
git diff --cached --check
```

All four passed. The scoped read-only inline audit also passed: exactly seven
added allowed docs paths, 15 EARS requirements with all 15 gate names present
in the prospective validation matrix (and no created test files), 23 valid
local Markdown links, all 34 source receipt rows equal to actual HTTPS request
metadata, existing app/worker.py/database.py/models.py and
scripts/ops_recovery.py/ops_host_fixture.py/ops_source_bundle.py Git blobs equal
to the base, and preserved builder ref unchanged. Checks were run after staging
the docs so tracked-content guards included this scope. Native/runtime capability
was not tested by the audit; a guard pass has no OS-admission meaning.

No scripts/check_sdd.py exists at this base. The existing product
check_sdd_convergence.py validates the unchanged product ledger, not these new
prospective feature gates; it is not presented as a feature-convergence pass.
The inline feature audit checks planned gate mapping without creating tests or
editing the shared ledger. Public docs use an interpreter alias; the private
handoff command identifies the explicit read-only interpreter path.

No scientific/ops suite, native probe, actual Job Object, cgroup, service,
environment install or host operation is authorized/run by this docs-only unit.

## 4. Scope and residual risks

Only the new dated research file and new files in this feature folder belong to
the branch. No existing verifier, worker, runtime, schema/DDL, app/API, test,
module manifest, public admission or bundle-policy path changes. No packages,
keys, secrets, private fixtures, backups or production directories touched.

The stronger no-escape and kill-latency properties cannot be inferred from
API availability. Windows external brokers/handle duplication and Linux compute
control-write authority/controller+worker loss are explicit CLOSED conditions.
Profile timing assumptions are provisional, not real-time kernel guarantees.
No particular OS, device or host is currently admitted by these documents.

MAIN reported the earlier 29.42% disk observation against the unchanged 30%
gate. This design did not remeasure it. Owner authorization/headroom decision
remains absent; actual host/recovery drill, service activation and production
changes remain CLOSED and NOT_RUN. No claim of unattended crash recovery, future
child restore support or completed field/physical capability is made.
