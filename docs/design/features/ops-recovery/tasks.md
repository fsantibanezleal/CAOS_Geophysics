# Ops recovery tasks

- [x] R-OPS-01 through R-OPS-08: read governance, full approved product SDD, API storage/deletion and processing contracts; persist official primary-source dossier and feature design before code.
- [x] R-OPS-01/R-OPS-03/R-OPS-08: implement explicit path, maintenance, age and bounded scratch primitives.
- [x] R-OPS-02/R-OPS-04/R-OPS-06: implement strict schema/file inventory, cumulative authority, snapshot registration and tombstone reconciliation.
- [x] R-OPS-05: implement manual bounded archive validation and extraction.
- [x] R-OPS-07: author full operations/retention/drill guide, including the parallel host unit's exact-stage quarantine and operator-assisted crash recovery policy.
- [x] R-OPS-01 through R-OPS-08: run local temporary-only real encryption/integrity/deletion and hostile-input gates; record [convergence and limitations](convergence.md).
- [ ] Review diff/history/ownership, commit and push scoped new paths, open PR to develop and add self-review. Do not merge/deploy or write to a host.

The actual-host maintenance/restore drill and deletion-path synchronous external checkpoint integration belong to the main agent's release review, not a local fixture PASS.
