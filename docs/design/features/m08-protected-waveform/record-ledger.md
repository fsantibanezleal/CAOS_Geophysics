# Lossless bounded record ledger

This corrects the representation of the existing admitted MiniSEED record
ledger; it does not change sample decoding, numerical algorithms, scientific
tolerances, admission or resource ceilings. Read the user-data contracts,
intrinsic-amendment and intrinsic-resources with the protected design and Linux
fixed-lane contract. Historical result bytes and failures remain immutable.

## Requirement and defect

R-M08L-01: every admitted record retains byte offset/length, channel/NSLC,
sequence/quality, both byte orders, encoding/data offset, sample count/rate,
corrected start/end, all flags, header correction/applied bit, microsecond
offset, timing quality/frame count, STEIM endpoints/capacity when present, and
the cumulative decoded sample interval. No provenance field may be discarded,
inferred from its neighbour, averaged or recoded into an approximate number.

The existing2MiB metadata cap also applies to4096 records. An actual authored
16MiB/4096record/180000sample three-channel input's record ledger alone needs
2187180 canonical ASCII bytes. It therefore cannot fit the current repeated-key
representation. This is a proven structural contradiction, not proof of the
sole cause of any native failure. The2MiB/32MiB/aggregate scratch caps remain
unchanged. Input raw bytes, hashes and native one-record decoding are unchanged.

## Closed transport

R-M08L-02: new channel `records` uses a versioned closed object with exactly
`schema,fields,rows`. Schema is `caos.waveform-record-ledger/v1`. Fields are the
fixed ordered registered names below, repeated once per channel; each row is
exactly one value per field. This is ordinary positional JSON, not compressed
binary, pickle, expression evaluation, arbitrary column selection or a package.

```text
byte_offset byte_length header_order sample_word_order encoding data_offset
npts sample_rate_hz start_us end_exclusive_us activity_flags io_clock_flags
data_quality_flags header_correction_100us correction_already_applied
microsecond_offset timing_quality steim_frame_count channel_index nslc sequence
quality sample_interval steim_x0 steim_xn packed_difference_capacity
```

The first23 fields are required in every returned record. The final three
fields are required exact integers for STEIM encodings10/11, and JSON null
sentinels for the *absent* keys in integer encodings1/3. Those scanner keys are
never present-null, so this preserves missing-vs-null exactly. Nullable timing
quality/frame count remain present-null as before. `sample_interval` remains
the exact `{start,stop}` object and NSLC remains its explicit four-item list.
No record or optional-field deduplication/reordering/renumbering occurs.

R-M08L-03: strict readers reject unknown schema/fields, reordered/duplicate
fields, short/long rows, extra keys, incorrect exact primitive types (including
bool-as-int), invalid known scanner field domains, malformed nested objects,
illegal absent STEIM fields, cycles and nonfinite/unsafe numbers. Per-row
pre-count before retained copy, maximum4096 rows and60000 samples per channel;
sealed result also checks4096 rows/180000 samples across all channels. Expansion
is bounded/lazy one row at a time; it reconstructs every original dictionary
exactly and never constructs a full repeated-key metadata graph on reopening.
Outer result/request/export/API/resource schemas remain unchanged. Historical
`records` list results keep their original bytes/hash/read contract; they are
never rewritten merely by reading. Only the explicit versioned new envelope
enters the new strict grammar.

R-M08L-04: pack after all existing per-record decoding/checks/interval assignment
but before final metadata pre-count. Neither decode order nor engine operations
change. The packer lives in the existing stdlib input module; seal validation
uses it from the existing evaluation module. The installation keeps its exact23
source names and changes content hashes normally. Already admitted jobs reject
changed source; old native grants cannot qualify these new bytes. Client/API
consumers continue to receive source-bound metadata and all arrays unchanged.
The current UI displays retained metadata rather than assuming records is a
list; no UI/CSS/SQL/shared worker or installation policy change is required.

## Verification order and review boundaries

Before implementation: preserve the actual failure and structural finding;
persist this concrete representation contract. The reviewed existing physical
and scientific contract remains controlling. Engineering review checks the
registered scanner field set, missing/null semantics, pre-count allocation,
historical reads, exact reconstruction, source pins and unchanged caps. There
is no new method/provider/field-acceptance or deployment prerequisite.

G-M08L-01: failing pure exact roundtrip tests over scanner-produced integer and
STEIM rows, including all flags/corrections/nullable values, empty/mixed rows;
malformed grammar/domain/type controls and4096/4097 row/sample caps.
G-M08L-02: a literal scanner-produced full4096record/16MiB/180000sample ledger
with unchanged counts fits2MiB after pack; prove exact every-row reconstruction
and demonstrate the repeated-key lower bound fails without raising its cap.
G-M08L-03: actual scientific calculation, sealing, export and independent reopen
exercise the packed ledger; historical list calculation still seals/reopens
without mutation. No authored metadata is labelled native/resource proof.
G-M08L-04: fresh full fixed-installed native queue at current source/runtime,
original nominal/upper/field QC and exact array/ZIP comparison; retain failures,
fail first, no unchanged retry. All original resource and lifecycle predicates
must pass independently. Exact terminal recovery/common-writer/release and
remaining adverse/overhead gates are not closed by these transport controls.
