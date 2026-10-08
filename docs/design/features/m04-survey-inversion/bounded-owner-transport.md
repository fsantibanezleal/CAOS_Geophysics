# Bounded magnetic owner transport

## Requirements

R-457 WHEN downloading a magnetic numeric ZIP, THE consumer SHALL call the
existing `ApiClient.requestBoundedBytes` with the unchanged128MiB maximum before
building a Blob or hashing a complete buffer. Invalid Content-Length, streamed
overflow, declared-size drift and cancellation SHALL refuse the download.
Gate: `magnetic-processing.test.ts` bounded ZIP consumer controls, retaining
the independent native transport controls.

R-458 WHEN reading a magnetic dataset, THE consumer SHALL bound the complete
JSON wire response to8MiB before UTF8 decoding or JSON parsing. The contained
request retains its separate8MiB exact UTF8/hash check. An otherwise valid
request whose escaped envelope exceeds the wire bound is refused, not given a
larger transport cap. Gate: bounded dataset consumer controls, including invalid
UTF8, oversized stream and cancellation.

## Design

Use the parent's existing public bounded transport unchanged. This older leaf
carries that exact method only for independent consumer validation; integration
must retain the parent's current client and native transport tests. Do not use
`requestBlob`, `response.blob`, `response.json` or a second transport framework
for these two reads. After the bounded ZIP read, the existing exact retained-ZIP
signature/SHA verification remains mandatory. After the bounded dataset read,
fatal UTF8 decode and JSON parsing feed the existing closed dataset validator.
Scientific numeric byte hashes and selected job bindings remain unchanged.

## Tasks and validation

1. Bind both consumers to the public bounded method.
2. Retain actual CSV-derived dataset and complete ZIP parity controls.
3. Independently exercise declared-length errors, streamed overflow without
   allocating an oversized aggregate, size drift, mid-stream cancellation and
   malformed UTF8 at the consumer boundary.
4. Run focused consumer plus unchanged native transport tests and strict type
   checks. These gates establish allocation/transfer behavior only, not hosted
   integration or nonzero scientific acceptance.
