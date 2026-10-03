# M01 physical persistence: milestone A requirements

Status: DOCS_ONLY, REVIEW_REQUIRED, IMPLEMENTATION_NOT_STARTED. This is an exact DDL/custody proposal, not permission to create a migration. It extends the protected [physical vertical](../m01-physical-vertical/design.md) at `87eb9e9bd65e8a5cd1385d9c58e5ed32460461bb`. Main must read and approve each milestone before code. No product, worker, source-schema, host or canonical-artifact change is included.

## Scope and approval boundary

Milestone A specifies column domains, keys, references, reservation identities, publication versus custody inventories and terminal accounting. Milestone B must subsequently specify the complete locked recovery algorithm, v2 tombstone/authority and legacy bridge, exact migration revision and selected-source registry. A plus B approval is necessary before schema/worker implementation. CPU lifetime accounting, actual host admission and measured browser admission remain separate prerequisites. There is no default public activation.

All requirements are prospective EARS requirements. Gate names are definitions in [validation](validation-plan.md), not executed tests.

| ID | Requirement | Gate |
| --- | --- | --- |
| MP-A01 | When migrating a valid 0003 database, the system SHALL preserve every legacy column value and original raw/dataset/result byte, including NULL, native JSON text and timestamps. | PA01_legacy_exact |
| MP-A02 | When reserving a root, the system SHALL serialize raw/parser uniqueness against pending and published roots without referencing a nonexistent dataset. | PA02_reserved_root |
| MP-A03 | When publishing a child, the system SHALL enforce the named composite owner/project/raw/root constraints, one immutable parent and a lower parent ordinal. | PA03_forest |
| MP-A04 | When accepting an identical physical request, the system SHALL reuse its active/successful fingerprint identity and permit a new identity only after failed/cancelled termination. | PA04_fingerprint |
| MP-A05 | Before creating any physical stage byte, the system SHALL commit its bounded custody and charge reservation. | PA05_stage_first |
| MP-A06 | When committing success, failure, cancellation or abandonment, the system SHALL co-commit retained-byte custody and charge before retiring the intent/reservation. | PA06_terminal_transfer |
| MP-A07 | While any retained stage or deletion file remains, the system SHALL retain its charge and evidence independently of intent/project existence. | PA07_debt_survival |
| MP-A08 | When removing a custody file, the system SHALL release its charge only after exact file verification, removal and the reviewed durability barrier, never on an attempted unlink. | PA08_removal |
| MP-A09 | If a file, cache name, schema, link, budget or binding is unknown, the system SHALL close admission and preserve custody; it SHALL NOT adopt, sweep or zero it. | PA09_unknown_closed |
| MP-A10 | When auditing a physical producer, the system SHALL compare the complete saved request/result/envelope and unchanged scientific receipt bindings, not infer them from a compact DB relation. | PA10_producer |
| MP-A11 | If commit outcome is uncertain, the system SHALL prohibit legacy recovery/accounting mutations until milestone B's all-writers/fresh-WAL classification has completed. | PB01_wal_cut |
| MP-A12 | After writers reopen, the system SHALL prohibit destructive pre-migration snapshot rollback that loses later committed writes. | PB02_no_lost_writes |
| MP-A13 | If the new migration/authority/source policy is not fully registered and independently reviewed, backup/restore and physical admission SHALL remain closed for that schema. | PB03_authority_bridge |

No source verification, full M01 acceptance, method/runtime PASS or complete vertical implementation approval follows from this document. Existing flag-only QC and MT discriminators remain literal and unchanged.
