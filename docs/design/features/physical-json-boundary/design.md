# Local physical JSON ingestion design

Date: 2026-10-03. Status: local implementation candidate after MAIN's full b124 read and explicit approval recorded before code. [Research](research.md) precedes the design; approved limits and architecture remain unchanged. Baseline `7e26d253ac7d3a3688cb6263f669a747681aa077`; branch `task/geophysics-physical-json-sdd`. Actual execution is separated from design assumptions in the [review packet](review-packet.md).

## 1. Problem, scope and non-goals

Propose an independently useful local entry boundary for user-supplied physical gravity JSON: `data-pipeline/gravity_station_json.py::load_gravity_stations_json(raw: bytes) -> dict`. Its later tests belong only in `tests/data/test_gravity_station_json.py`. The ordinary correction adapter currently starts from native objects, too late to recover duplicate names or constrain allocations already performed by an untrusted decoder.

This root lane is deliberately narrower than the offline core. It accepts at most 400 stations and the fixed [contracts](contracts.md), not every core-capable survey or arbitrary JSON. Rejected overbounds can be handled by a separately reviewed offline workflow; there is no silent subset or bypass option here.

No API, routes, wire envelopes, registration, parser dispatch, storage, SourceRecord, jobs, worker, migration, bundle/export/import, browser/frontend, host/runtime activation, method acceptance, acquisition or canonical-data changes. No integration into the existing CLI/adapter occurs in this unit. No config/transform/result/app envelope acceptance. No file/path/network/dynamic hook parameter. No science imports, processing, reprojection, datum guesses, conversion, coordinate equivalence, uncertainty propagation, correction replay or field/provider authentication.

The held larger M01 physical-vertical SDD remains held. Approval of this independent ordinary helper cannot waive any vertical contract, storage, numerical, browser, host or release requirement. A docs merge, if later authorized, is not implementation approval.

## 2. Interface and ownership

The only callable operation is `load_gravity_stations_json(raw: bytes) -> dict`. Require `type(raw) is bytes` before invoking len/decoding; reject str, bytearray, memoryview, bytes subclasses, dicts, paths and file-like objects without consulting their methods. No optional limits, callbacks or caller-supplied decoders. Expose the one error class and fixed immutable numeric limits, no mutable process-wide configuration.

The caller already owns the bytes. This helper bounds additional parsing, not the caller's earlier acquisition allocation. It never reads a file or stream and cannot certify that a caller used bounded acquisition. The caller separately retains original bytes and records raw hashes when required. Returning a dict does not make it immutable: it is caller-owned, fresh per call, with no cache or shared mutable defaults. The function does not return a receipt or injected eligibility field.

## 3. Ordered decoding pipeline

| Stage | Action and bounded live state | Forbidden shortcut |
| --- | --- | --- |
| A | Exact bytes type, actual len <=16 MiB, BOM/empty checks | stat, Content-Length, path read, permissive coercion |
| B | Iterative grammar scanner over byte indices; <=16 active container frames; count nodes and canonical bytes; per-token bounded decode and key sets | json.loads first, regex over a giant copied token, recursive descent with global recursion changes |
| C | Only after full scan succeeds, strict UTF-8 text decode and one ordinary json.loads without hooks/custom classes; native dict/list/int/float/str values | object/parse hooks, Decimal, repeated full-object decoding, deep copy |
| D | Exact static root schema, scalar ranges, ordered history shapes and station-ID uniqueness; direct examination without normalization | core imports, numerical checks or repairing fields |
| E | Stream JSONEncoder(sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) fragments; count and compare <=8 MiB with scanner total | joining encoded fragments, changing digest dialect, hashing reconstructed bytes as original |
| F | Return the same decoded dict object from C | wrapper, receipt, synthetic provenance or eligibility claim |

Scanning validates complete RFC-style grammar, not merely brace depth. Track object key/colon/value/comma/end and array value/comma/end states. Only ASCII JSON whitespace (space, tab, LF, CR) is allowed outside strings; exactly one top-level value followed only by permitted whitespace. A non-object top-level value can pass grammar but fails root contract. Reject comments, trailing commas, missing separators, leading-plus/leading-zero numbers, unescaped controls and nonfinite constant extensions. Root syntax and wrong schema remain distinct error categories.

String handling decodes strict UTF-8 scalars and JSON escapes incrementally, including valid high/low surrogate escape pairs as one Unicode scalar; reject lone/reversed/truncated pairs, overlong/invalid UTF-8 and escaped/unescaped invalid scalars. Count decoded UTF-8 bytes, not source escape characters. Stop at key/value cap before accumulating a larger token. Active object frames retain only bounded decoded key sets and counts; no list of all tokens, unbounded pair list, or second survey tree. Duplicate equality uses decoded code points, not raw spellings, case folding or Unicode normalization. Discard frame key sets on closure. Key-state errors cannot echo the unknown key.

Numbers use JSON grammar and at most 128 ASCII source characters before bounded int/float conversion. Integer tokens have neither fraction nor exponent and are restricted to +/-9007199254740991. Float tokens retain ordinary CPython float semantics; overflow rejects, finite underflow and floating negative zero remain unchanged. A mathematically integral float is not coerced to int. Scalar conversion during scanning is bounded token-local work, not construction of the final survey.

Resource accounting is exact as [contracts](contracts.md) defines. The scanner must reject violations before C is invoked. Stage C is bounded but creates both decoded text and a tree: local peak-memory measurements must include those overlaps, scanner metadata, encoder fragments and validator sets, not merely raw size. No universal RSS safety claim follows from these numeric caps.

## 4. Canonical pre-allocation bound

Pre-count the scientific canonical byte length during B. Every accepted string/key contributes its bounded scalar JSON encoding with ensure_ascii=True; every numeric token contributes the JSON encoding of its native int/float value, not its original spelling. Literals and structural punctuation contribute their canonical lengths; whitespace contributes zero. Key sorting changes byte order but not total length once duplicates are excluded.

For an object with m members the count is 2 braces + encoded keys + encoded values + m colons + max(m-1,0) commas. An array has 2 brackets + encoded values + max(n-1,0) commas. These formulas are additive while scanning. Capped scalar fragments may be transiently encoded; no final root/dict/canonical buffer is allocated to compute the pre-count. Reject immediately when the cumulative count exceeds 8388608. E independently cross-checks the count against the unchanged stdlib encoder on the decoded object; disagreement is a safe invalid-input/invariant failure, never a relaxed bound.

Sorting remains only in this cross-check; insertion/station/history order of the returned dict is not rewritten. Raw formatting/exponent spellings cannot be reconstructed from a dict. Python native scalar type and Unicode semantics must match ordinary strict UTF-8 json.loads on every scanner-accepted positive control. The separate scientific SHA-256 dialect remains sorted compact ensure_ascii=True UTF-8; this function need not calculate or return a digest.

## 5. Structural versus scientific validation

The helper checks known schemas, literals, ranges and array/key shapes only. It knows history prefix lengths and exact recorded parameter declarations, not whether additions, current values or historical hashes reconstruct. Hash-shaped values are not authenticated. Unit signs, datum, calibration, geoid and terrain statements must be explicit, never defaulted. Zero primitive sigma is permitted; missing/null/bool sigma is not substituted with zero.

It may accept otherwise well-formed roots with wrong numerical history, duplicate physical coordinates including -180/+180 or polar equivalence, receiver below surface, negative land surface, or inconsistent converted original/current values. Those controls are intentionally rejected later by unchanged core scientific gates, not by hidden physics here. Negative primitive sigma or out-of-range latitude is a declared scalar-contract rejection, distinct from geometry/error propagation. A terrain history's exact station-ID order is structural alignment, not verification of its supplied method/source or numerical additions.

## 6. Errors, performance and kill criteria

Use the safe typed exception contract in [contracts](contracts.md). Expected input failures expose no json.JSONDecodeError.doc, supplied key/value, source citation or context chain. Do not promise Python traceback-frame secret erasure: callers must not serialize traceback/locals. Catastrophic interpreter/resource failure is not silently turned into a valid dict or a misleading scientific failure. No global json monkeypatch, setrecursionlimit or set_int_max_str_digits.

Measure valid nominal, largest schema-valid root near the canonical cap, whitespace-padded raw upper boundary, and malformed/duplicate/overflow/deep/node/key/string/canonical overbounds. Include active decoded-key sets near the node/canonical limits and a literal astral scalar plus16-MiB whitespace: CPython's decoded text may use four bytes per code point even though most raw bytes are ASCII. Record source/runtime/commands, exact input and scientific byte sizes, wall and CPU, peak allocations/working-set and whether materialization ran. Separate fixture-build from helper allocation peaks; scanner-only generic JSON is not root acceptance. There is no helper scratch I/O. Actual measurements are in the review packet, not worker/browser/host admission or universal resource guarantees.

Stop if preflight allocates a full tree, duplicate detection happens after overwrite, Unicode/int/float semantics drift, an overbound reaches materialization, scientific code is imported, private errors escape, existing sources change or a local PASS is promoted into vertical/field/host acceptance. No tolerance/hash rewriting or scope expansion is a remedy. See [validation](validation-plan.md) and [review packet](review-packet.md).
