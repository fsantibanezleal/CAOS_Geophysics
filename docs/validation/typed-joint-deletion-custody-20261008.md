# Typed joint deletion custody validation

The current deletion reader accepts `geophysics.physical-custody/v3` only
when its inventory contains at least one valid, explicitly typed native joint
member. Merely changing a waveform-only record's schema does not confer
dispatch. The existing v1 and v2 validators retain their original rules.

Joint members bind the canonical job UUID, closed member-name grammar,
`result_copy` role, `deleting_derived` location, bounded positive byte count
and SHA-256. Unknown fields, path traversal, invalid identity, missing member,
wrong role/location and oversized members reject. This reader confers no
scientific, filesystem, cleanup or publication authority.

## Actual local execution

The four complete current custody and native joint reader suites passed
71 tests with zero failures, errors or skips in 0.510 seconds. Execution
used the source-frozen validation driver with fresh before/after source,
input and runtime inventories. The original schema-rejection negative
control was retained. Ruff and `git diff --check` passed.

JUnit SHA-256:
`e0c08fc3f6b0936f771f7ede456d4eaf3103e250c55fd944268d1eab58b4a6e9`.

This is a parser/helper regression result, not acceptance of the complete
populated mixed-method store, native worker, scientific methods, actual-host
runtime or product deployment.
