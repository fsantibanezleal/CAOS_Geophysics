# Exact pure implementation approval record

Date: 2026-10-03. Persisted BEFORE source/test creation.
Approved immutable sub-SDD: 2c94da44b6205652cd2d89d73ebbf78cc4626903.

MAIN explicitly reports FULL read of all seven pure sub-SDD documents plus the
parent packet delta at that pin. MAIN accepts supplied-stream-only contracts,
bounds, checked conversions, phases, receipt/release validation and
runtime_authorized ALWAYS false. MAIN expressly authorizes test-first implementation
of all twelve gates and then the pure module, ONLY in these NEW paths:

```text
scripts/physical_accounting_protocol.py
tests/worker_accounting/test_protocol.py
```

Own subdocs/evidence may be updated. No additional imports beyond the approved
stdlib design, package, caller hooks or CLI. Decoder preflight BEFORE copying,
tree allocation or integer conversion; exact null/unavailable and absorbing
FAILED_HELD preserved. Frozen B60/240, S57/237, M3 seconds, no weakened negative
or numerical tolerance. Synthetic fixtures are in memory only.

No actual OS/native launch/probe/controller, clock, file/network/runtime/profile/
auth/storage/environment/source-policy change or measurement is authorized.
Ordinary module loading and local pure test invocation do not certify those
mechanisms. All15 parent platform gates stay CLOSED/NOT_RUN. No profile activation
or production probe; no actual host access is needed or authorized.

Delivery requires scoped commits/push, local pure gate evidence and pinned
self-review. MAIN independent review/rerun is REQUIRED before develop promotion;
this approval is not merge/deploy/runtime authority. Parent native worker remains
unimplemented. Parent research/SDD/ops evidence and preserved builder refs unchanged.

Implementation order: persist this approval; write all12 named gates and observe
expected pre-implementation failure; commit test-first evidence; implement the
exact pure unit; pass all gates/cheap guards and record convergence; hand off
exact pushed pin for independent review without merging.
