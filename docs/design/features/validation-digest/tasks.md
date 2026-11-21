# Validation digest tasks

- VDG-001: implement read-only consistency verification using the existing runner's evidence functions; do not execute commands or capture current inventories.
- VDG-002: create requested output exclusively and refuse to overwrite existing evidence.
- VDG-003, VDG-004: refuse tampered evidence and report bounded counts plus the first failed or refused node.
- VDG-005: expose at most 4096 bytes per stream from only the first failed command when explicit tail inspection is requested.
- VDG-006: document acceptance boundaries and test that retained receipts do not imply current-source, scientific, generated-output or deployment acceptance.
- Run focused controls, then inspect an actual retained completed report without rerunning its command.
- Record gate results after execution; this feature does not close scientific or deployment requirements.

## Feature verification

VDG-001 through VDG-006 pass in the focused reader suite: 19 tests, zero failures,
errors or skips, 7.570 seconds. The local DAG's fresh complete declared
source/runtime inventories agree before and after the command. Retained JUnit
SHA-256: `74a6de9b8aba24cc15596f683014a79c03c02d3bf3da592e8172c2f2838a0d98`.
Ruff and whitespace checks pass. The first direct regression run retained one
test expectation failure: a missing path raises the existing typed refusal,
not an OS exception. That expectation was corrected; evidence was not replaced.
An initial DAG declaration refused before execution because its temporary
directory equalled the selected data root; the corrected declaration selects
an existing child directory without relaxing the external-path rule.

Actual retained reports were independently read: a completed parser/custody
command passed; a gravity prerequisite report retained two passed commands and
its original native-direction failure; a catalog/export report retained its
original HTTP integrity failure. No original command reran. This verifies
report ingestion and retained seals, not corrected solver, catalog, scientific
or deployment acceptance. These retained failures remain visible.
