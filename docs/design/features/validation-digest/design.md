# Read-only validation digest design

Extend the existing local validation tooling with a standalone path-invoked
stdlib reader. Do not change the running dispatcher or create another runner.
Reuse its closed JSON, external path and sealed-cache verification helpers.
Read one explicitly selected completed report, with at most 64 distinct nodes.
For executed nodes, verify the canonical plan fingerprint, predecessor bindings,
receipt and complete evidence seal. A report is not a signed authority: this is
internal consistency against retained evidence, not independent authenticity.

The compact JSON exposes counts, node status/action/reason, elapsed seconds,
the first failure and evidence hashes. Never emit command environment or raw
logs by default. An explicit local diagnostic option permits a bounded first
failure tail; that output may contain private data and must not be published.
All source inventories remain retained in the existing plans. This reader does
not rehash current scientific inputs or infer full-product acceptance.

Limits: 4 MiB closed JSON per existing parser, 64 nodes, 512 displayed reason
characters and 4096 diagnostic bytes per stream. Hash logs by streaming, not by
loading their complete contents into memory. Reject incomplete and changed
evidence. Do not remove locks, retry commands or produce synthetic receipts.

Optional output creation uses the runner's exclusive, fsynced writer after
external-path validation. Existing outputs are refused, not replaced. Without
that option, inspection writes nothing. No public endpoint or credential is
introduced. This is orchestration tooling, not a new computation lane.
