# Physical root JSON boundary research

Date: 2026-10-03. Initial research was design-only at baseline `7e26d253ac7d3a3688cb6263f669a747681aa077`. MAIN subsequently read all seven b124 documents and approved only the independent LOCAL-ONLY helper/tests/docs/evidence. The inspected scientific sources below remain unchanged. Actual implementation, local measurements and separately attributed independent review are recorded in the [review packet](review-packet.md); none constitutes numerical/method/host admission.

## Existing ordinary sources inspected

- `data-pipeline/gravity_processing.py`, SHA-256 `7863699269b491c2895bcf030d3fb65cf27ac32a652fce91112bc2c7c9c73321`: exact gravity-stations-1 metadata/stations, history generation/replay, units/signs, primitive errors and scientific digest. Its scientific functions import Boule, Harmonica and NumPy. Its existing CLI accepts a different dataset/config request and remains unchanged.
- `data-pipeline/gravity_station_adapter.py`, SHA-256 `b770b16ef87e83dd92f65a90472145ef93a525a9cedf7f55ee3e6f20f8a10cf8`: already-decoded native-object admission, container depth 16, 200000 containers/keys/scalars, 128-byte keys, 8192-byte values, 400 stations and bounded scientific encoding. It is not a raw decoder. Its full six-key request has a 16-MiB canonical bound, not this root's 8-MiB bound.
- `tests/numerics/test_gravity_processing.py` and existing ordinary adapter tests: independent physical oracles belong to the scientific units. Their earlier PASS receipts are not new parser evidence.
- Product [SDD](../../SDD.md), [local correction requirements](../m01-gravity-corrections/requirements.md) and [local transform design](../m01-gravity-transforms/design.md): structural parsing cannot close method, field, source, browser or host gates.

The existing CLI's stat/read/JSON hook is not adopted or modified. The new ordinary helper accepts actual exact bytes, not a path or an already-decoded arbitrary object. It does not supersede any existing parser or activate callers.

## Primary language sources

Reviewed on 2026-10-03:

1. [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259), sections 2, 4, 6, 7, 8 and 9: JSON grammar, decoded member-name equality, number grammar, interoperable integer range, UTF-8 and implementation limits. This lane deliberately rejects duplicates and unpaired surrogates rather than relying on unspecified consumer behavior.
2. [CPython 3.12 JSON documentation](https://docs.python.org/3.12/library/json.html): default native int/float decoding, permissive duplicate/nonfinite behavior, ASCII escaping, compact sorted encoding and warnings about untrusted CPU/memory consumption. A default decode alone is insufficient; a bounded grammar scan must precede it.
3. [CPython 3.12 codecs documentation](https://docs.python.org/3.12/library/codecs.html): strict UTF-8 decoding is the encoding boundary. No replacement or ignored invalid input is allowed.

These are source references, not provider acquisition, engine/runtime approval or downloaded field-data receipts. The implementation runtime will be recorded explicitly; documentation does not authorize a dependency upgrade.

## Serialization observations, not a parser PASS

A read-only CPython 3.12.10 stdlib serialization probe (`python -B -S -`, Windows) on this checkout produced the following scalar-domain golden vectors. They are not complete survey fixtures or live execution evidence. Python script used `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")` and SHA-256. The Unicode probe used an ASCII source escape, avoiding shell transport substitution. Primary online documentation currently displays a later3.12 patch; it does not change the executed runtime or authorize an upgrade.

| Exact scientific bytes | SHA-256 |
| --- | --- |
| `{"n":1}` | `2bfd14f43d17fc7cea24e0917a8879b4b2f880b8baeec1b9d90fbaad655e71bd` |
| `{"n":1.0}` | `3b6b06ecd1c968c8e738e0f11c4bb361fca80a9a694de22fe66a05286afbd081` |
| `{"n":-0.0}` | `a8a313cade05001e69f7ddb5db01e1e2d06fb8f6913ab492cc4506d4e65d465a` |
| `{"n":1e-07}` | `ff7a1315299260617fe404199e54e6d976a0b03e47da54fccec073c2fa48ff5c` |
| `{"s":"\u00e1"}` | `e74e492be1c93dbcb256ec215ca9b13edd33816ed36b4132c2984b04f839afde` |

The application-domain UTF-8 bytes for the same accented string have SHA-256 `dbc8194c22b6728e823195d25b4335c5075dbe8504d75e584871f0e743e73196`, and differ from the scientific ASCII-escaped bytes. Neither digest is the original raw-file digest unless those exact bytes were the original file. JSON exponent spelling and whitespace are not retained in the native dictionary; native integer/float distinctions, signed floating zero and decoded Unicode are retained. No JCS substitution, float rewriting or Unicode normalization is proposed.

## Design conclusions

Use a stdlib-only, iterative byte grammar scanner with bounded per-token decoding and active-object key sets before materializing the final native object. Reject lexical/structural/resource violations before a full `json.loads` or copying. Pre-count canonical size from scalar encodings and punctuation; key sorting changes order, not encoded length. Then perform ordinary native decode without hooks, exact root checks, and an independent streamed canonical-length cross-check. No scientific import is needed for any stage.

Full root-schema validation and numerical replay are different gates. Declared metadata and supplied hashes survive unchanged; the core later decides numerical history, physical coordinate equivalence, land geometry, converted gravity and error propagation. A structurally accepted root may still be scientifically rejected.

Scope stays entirely ordinary/local. The larger physical-vertical SDD and its hard holds are neither replaced nor waived. API/storage/jobs/bundle/UI/admission/method acceptance remain outside this unit.
