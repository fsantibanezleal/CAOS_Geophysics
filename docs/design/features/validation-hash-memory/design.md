# Reusable inventory buffer

Replace per-chunk one-MiB bytes allocations with one 65536-byte bytearray and
readinto/memoryview. A checked integer read count controls SHA update and total
byte accounting; EOF total must equal held file size. All directory membership,
source/runtime inventories, pre/post identity, cache seals, process custody,
deadlines and scientific checks remain unchanged. No cache entry is reused
under an old driver fingerprint after this source changes.

Translate only MemoryError at the hashing boundary to Refusal. Existing context
exit closes the held stream. Top-level MemoryError outside hashing emits one
fixed REFUSED diagnostic and returns2; it does not rerun or manufacture a node
report. Focused controls use real files and instrument the read operation;
allocation failures are explicitly authored injection, not an OS OOM proof.
