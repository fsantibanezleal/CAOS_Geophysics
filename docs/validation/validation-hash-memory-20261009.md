# Validation inventory allocation controls

The changed inventory hashes original bytes with one reusable 64KiB buffer.
Held file identity, complete input inventories, source fingerprints, process
custody, deadlines and scientific assertions remain unchanged. Allocation
failure refuses without retry or a partial inventory.

The first new control failed against the original allocating-read path. The
new nine controls subsequently passed. A first combined run stopped at a
missing `VALIDATION_COPYABLE_PYTHON` operator declaration, not a changed test
assertion. With that declaration pointing at the actual base Python executable,
the executable-mutation selector passed and the combined gate passed all 54
controls: zero failures, errors or skips; pytest duration 48.390 seconds.

The command used the repository `.venv-validation` Python, explicit
`-c pyproject.toml --rootdir=. --confcutdir=.`, external temporary storage,
`-x`, and the hash-memory plus original local-driver test files. The raw XML
is retained privately at `E:\_Temp\ghm5.xml`, SHA-256
`87f11f15d628d767d48a5e3af2d6cb165d4ff595b250524ef3a6b0f13d49091f`.
Changed driver SHA-256:
`33bb83d8475c0b0ea2fae87e29d1425878fb089b5d11968c26518dc28470d40a`.

Injected allocation failures establish refusal/closure behavior, not an OS OOM
reproduction or the sole cause of the earlier inventory MemoryError. These
controls do not qualify the previously refused source-frozen M12 run, scientific
methods, whole-service resources or deployment. New runs must bind the changed
driver; earlier receipts retain their original fingerprints.
