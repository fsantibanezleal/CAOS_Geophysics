# Closed current tombstone lexical contract, 2026-10-08

The exact two-file registered lexical decoder and its controls were reviewed
and imported without modifying the generic scanner, historical admission or
the current default migration. It recognizes only the current physical deletion
envelope and saved native receipt schemas. Exact saved SQL TEXT fields retain
their original4MiB ceiling; registered joint compact metadata fields retain
256KiB. Unregistered strings remain8192 bytes and keys128 bytes.

The non-building pass checks closed schema/record envelopes, lexical limits,
duplicate keys and complete EOF before constructing the nested tree. Complete
native receipt, SQL joins, owner, source, byte/hash and deletion identity
validation remains a separate mandatory step. Lexical acceptance alone never
accepts an invalid tombstone or repairs a database.

Fresh source-frozen execution passed97 parser/current-custody/native-reader
tests, zero failures/errors/skips,1.130s. Actual JUnit SHA-256:

```text
bfab8a783094c47a79cd9e6679ae42f76813a3910697cb7cbb8637ef0be7c009
```

The driver recorded exit0 and stable pre/post source/runtime inventories.
Ruff and diff checks pass. Exact Git blobs are:

```text
5ca57f60e41f3f7f14c246b3c6d208e3c1774186  app/physical_tombstone_lexer.py
7e69f507cd752f54dace7a3e7693b40b3a490d0b  tests/api/test_physical_tombstone_lexer.py
```

The producer's separate focused populated retirement run passed38 tests,
zero failures/errors/skips,63.110s, including the original failed authentic
retirement case. Its JUnit SHA-256:

```text
d335935fd315802ceb9b93ca4af756fa0d0e6ef80fa68e1d5c1d5492c065912d
```

That producer result is not the complete merged mixed-method lifecycle gate.
The integrated97-test run covers the pure decoder and existing readers, not
activation of the remaining populated union, native worker, complete deletion
or deployed application. Original failed evidence is retained. No public
replacement release or scientific calculation is granted by these tests.
