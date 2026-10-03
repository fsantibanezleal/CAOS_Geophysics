# Independent local physical JSON review

This record concerns the separately approved local raw-bytes helper in PR127,
not authenticated upload activation, worker execution, immutable child
publication, provider verification or full M01 acceptance. Its caller supplies
already owned bytes; the helper never acquires files or certifies a transport.

MAIN fully read all seven design documents at
`b1242ac6d62ea7403c9c9fad0e0442da11f560eb` before explicitly authorizing only
the new local helper, paired tests and their owned feature evidence. The initial
test-first commit is `d2ced4158cfcd9dc3f478c5373a7d6316bda3551`;
implementation review/replay is pinned to
`a7307bad928398dd2230209e5838d4bead12d14d`.
MAIN read the complete475-line implementation and complete test-first file,
including its14-line implementation-stage test correction. Those corrections
fix fixture encoding while JSON functions are fault-injected and preload the
future-annotations dependency in the import-denial harness; they do not weaken
limits, skip tests or authorize a production hook.

Helper SHA-256:
`83d62675e47e9db97d3b93be2e1ccf2b268717c42aca32f167b8526b1f95bb6e`.
Test SHA-256 at this first independently executed pin:
`48527def43380ce48b5bebe25a3d800889d507f95255d0182c17386da70fe290`.
Later source/test/evidence changes need their own exact-diff review and replay;
these receipt hashes do not silently transfer to a changed candidate.

## Actual pinned numerical and parser execution

MAIN created a detached review checkout and fresh external private scratch/cache.
The already installed M01 CPython3.12.10 interpreter was used read-only, with
bytecode disabled, one numerical thread and the actual protected author archive
explicitly supplied to the existing source-negative gate. No dependencies,
scientific sources, provider metadata, historical receipts or canonical arrays
were changed.

```text
<READ_ONLY_M01_PYTHON> -B -m pytest
  tests/data/test_gravity_station_json.py
  tests/numerics/test_gravity_processing.py
  tests/numerics/test_gravity_transforms.py
  tests/numerics/test_gravity_station_adapter.py
  -o addopts= -q -rs -p no:cacheprovider
  --basetemp <FRESH_PRIVATE_TEST_ROOT>
  --junitxml <FRESH_PRIVATE_RECEIPT>
```

Actual result:179 passed, zero skips,72.90 s. This executes all14 new named gates
and165 unchanged M01 regressions, including real ordinary core/adapter positives
and structurally valid inputs that the physical core correctly rejects.
Private JUnit SHA-256:
`3b4220b9ac6c478545d60b5bd18cf3c1b7da915746ac217654f0022cbb9442d2`.
The review checkout remained tracked-clean after the run. Scientific history,
unit conversion and physical-position/error checks stay in the real core; this
stdlib helper only validates the raw grammar and declared structural contract.

## Fresh-process allocation and source limits

Every following profile ran in a separate actual CPython `-B -S` process,
without pytest/scientific imports. Tracemalloc was active before authored raw
construction, so both its overhead and fixture construction are included.
Reported CPU is whole-process user+system, not a process-tree/host receipt.
Windows GetProcessMemoryInfo PeakWorkingSetSize reports process peak bytes,
including already owned raw bytes, scanner, text/tree and encoding overlap.
No universal device/server ceiling is inferred from these local observations.

| Authored profile | Outcome | Helper wall, ms | Whole-process CPU, ms | Peak process bytes | Native materializations |
| --- | --- | ---: | ---: | ---: | ---: |
| One station | accepted | 12.6 | 15.6 | 29892608 | 1 |
| 400 stations with four-record structural history | accepted | 354.6 | 359.4 | 30212096 | 1 |
| Exact8-MiB scientific canonical root | accepted | 10667.0 | 10250.0 | 46530560 | 1 |
| Exact16-MiB source including whitespace | accepted | 11336.3 | 10906.2 | 60743680 | 1 |
| Canonical8 MiB plus one byte | rejected | 10612.5 | 10328.1 | 46673920 | 0 |
| Raw16 MiB plus one byte | rejected | 9.9 | 31.2 | 60698624 | 0 |
| Near16-MiB whitespace followed by decoded duplicate keys | rejected | 11403.2 | 10765.6 | 60669952 | 0 |
| Float overflow1e400 | rejected | 11.8 | 15.6 | 29683712 | 0 |
| Depth17 | rejected | 9.8 | 15.6 | 29827072 | 0 |
| Node200001 | rejected | 2610.1 | 2468.8 | 29794304 | 0 |

Values are rounded table readouts; private JSON records retain full measurements,
source/test/runtime/raw identities and actual allocation peaks. The16-MiB
whitespace case peaked at33663640 traced bytes. The canonical boundary is reached
using explicitly authored escaped control characters in long unique station IDs;
it is an adversarial structural control, not a plausible field observation.
The initial node-overrun array measures node/CPU bounds, not the worst live
decoded-key set. A separately requested key-heavy object control remains required
before final candidate acceptance; no memory claim substitutes for that test.

## Additional independent representation controls

MAIN authored a new private helper, independently of producer tests, with seed
202610031118. It compares5000 generated scalar/nested JSON source variants with
the native sorted compact ASCII encoder: integers versus floats, negative zero,
subnormals, maximum finite float, control characters, escaped slash, Unicode
combining characters/supplementary scalars, compact/pretty source and whitespace.
All5000 canonical-precount comparisons passed. Seventeen separately authored
duplicate/encoding/surrogate/nonfinite/overflow/numeric-grammar negatives also
rejected before final materialization; typed error contexts/causes remained null.
Private authored helper SHA-256:
`a8ed2d5fee046a41abd8b679362535a97497a82a61da1dd0a1480191edc0d381`.

The frozen caps remain raw16 MiB/canonical8 MiB/depth16/nodes200000/key128
UTF-8 bytes/string8192/numeric lexeme128/integer-token magnitude2^53-1.
Full iterative grammar/canonical scanning precedes one native materialization.
Exactly supplied native numeric/string/history semantics are preserved; no
defaulting, numerical repair, Unicode normalization, provider authentication,
source-digest manufacture, I/O or hidden scientific replay occurs.
Fixed safe error records are not a guarantee that traceback locals erase input.

This is initial independent candidate evidence. Final peer review, added
key-heavy resource control, producer convergence and exact final-head promotion
remain separate steps. All whole-product unresolved/failed verdicts remain.
