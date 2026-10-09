# Local physical JSON producer execution and review provenance

Date: 2026-10-03. Local-only candidate, not API/worker/browser/host/provider/field/method acceptance. Fixed caps, public contract, scientific sources and native semantics remain unchanged. Draft PR127; no merge/release. This record separates producer execution from MAIN-reported independent execution.

## Producer pins and runtime

- Code/test execution head: `9e4d35b5eaf7eafab21c96142bd0d7ab3e89502c`.
- Module `data-pipeline/gravity_station_json.py`: SHA-256 `83d62675e47e9db97d3b93be2e1ccf2b268717c42aca32f167b8526b1f95bb6e`, unchanged since a7307ba.
- Test `tests/data/test_gravity_station_json.py`: SHA-256 `65392731acae33e7e4c4176b7b9edc19fffc8d249a4d7020e44e387e38c80738`.
- Existing owned `.venv-ingestion/Scripts/python.exe`: CPython3.12.10 MSC1943 AMD64 Windows; pytest9.1.1, NumPy2.2.6, SciPy1.15.2, Ruff0.15.18. Boule/Harmonica absent; no installs/environment changes. Helper imports only stdlib; science runtime is tests-only.
- Final unit: **13PASS,1SKIP,0FAIL**,148.43s. The skip is the real-core R-PJB11 gate, not a mock PASS.
- Actual private XML `unit-full-3.xml`: SHA-256 `9acddf9539e604f771c8c4cf0d89b8a78f40c2f65f6be866efbbaa8c31a80e65`; stdout `36c96a535991d96a7097dfaf251a6d32c319eb513cd73a566faee49c70816bf3`; stderr empty.
- [Sanitized actual resource receipts](2026-10-03-producer-resources.json) retain fifteen original receipt hashes, actual input hashes, exact measurements and empty-stderr hashes. No private data or original field source was used.

Approval was persisted aaada30 before any code. Test-first d2ced41 collected14 gates with the module absent; actual expected ModuleNotFoundError red execution retained. Implementation a7307ba and resource-test expansion9e4d35b were committed/pushed as separate scoped milestones. No protocol/cap/error/scientific guard revision occurred.

## Reproducible commands and retained private outputs

Run from the owned ingestion worktree. `SCRATCH` below means a fresh directory under this unit's ignored `evidence/.pytest_cache/`, not a public fixture or a replacement for an earlier execution.

```text
.venv-ingestion/Scripts/python.exe -B -m pytest tests/data/test_gravity_station_json.py -ra --basetemp SCRATCH/unit-full-3 --junitxml=SCRATCH/unit-full-3.xml
.venv-ingestion/Scripts/python.exe -B -S tests/data/test_gravity_station_json.py PROFILE
.venv-ingestion/Scripts/python.exe -B -m pytest tests/data --ignore=tests/data/test_gravity_station_json.py -ra --basetemp SHORT_SCRATCH/t --junitxml=SCRATCH/legacy-data-2.xml
.venv-ingestion/Scripts/python.exe -B -m ruff check data-pipeline/gravity_station_json.py tests/data/test_gravity_station_json.py
```

Final producer private scratch is `evidence/.pytest_cache/run-9ba51a54f53a41e78d1619b70260a6d4/`; receipts are under `unit-full-3/test_local_resource_and_legacy0/`. Each child uses CPython `-B -S`, fresh process and fresh pytest working directory; no cached source/measurement replay.

Earlier artifacts remain distinct and untouched:

- a7307ba test SHA `48527def43380ce48b5bebe25a3d800889d507f95255d0182c17386da70fe290`: producer13PASS/1SKIP52.23s, ten profiles; XML `cc3a577f457815e3a150e8ef0fa0f9b31feca0c61bd9e98799aa2a84f5f17b56`.
- Intermediate uncommitted test SHA `810f492af20949b6f38d0ad2f8c2000df6c0c0c4bcd90ba96c672016d3911620`: producer13PASS/1SKIP124.74s, fourteen profiles; XML `38cd4608d118704d28303f1c7e89f91172f864b0bf1660b2d2f9fd2742705002`. Its three unique-key profiles used private scanner calls only; not relabelled as final public-loader evidence.
- First unchanged legacy run:1FAIL/99PASS/2SKIP due to Windows long-path hardlink fixture creation. Preserved failure, no source/settings change. Fresh shorter `evidence/.pytest_cache/l-0ae3c8e8/t` rerun: **100PASS/2SKIP0.91s**, XML `2a4cc5c5083af473828e866c1308b057c7fc55964c3fb121788e2c13e0885189`. Skips: explicit external potential archive not supplied to producer; Windows symlink privilege unavailable (junction control passes). Existing tests and EDI source untouched.

## Fifteen cold profile observations

All15 emitted empty stderr, matched actual source/test pins and passed their fixed result/materialization assertions. Times include tracemalloc overhead and cold helper import. CPU is whole-process CPU including fixture generation; zero on tiny cases reflects clock quantization. Peaks are Windows GetProcessMemoryInfo **PeakWorkingSetSize bytes**, including runtime/fixture/tracemalloc, not Linux RSS. Allocation pairs below are fixture-build peak / helper peak after reset; helper peak includes retained raw bytes, not an incremental/subtracted baseline.

| Profile | Result | Raw bytes | Accepted canonical bytes | Materializations | Helper wall ms | Process CPU ms | Process peak bytes | Build/helper allocation peak bytes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| canonical-over | rejected | 8388609 | not applicable | 0 | 10777.09 | 10312.50 | 47046656 | 18379906 / 9976065 |
| canonical-upper | accepted | 8388608 | 8388608 | 1 | 10698.96 | 10546.88 | 47001600 | 18379903 / 18516440 |
| depth-over | rejected | 35 | not applicable | 0 | 10.02 | 15.63 | 30109696 | 137 / 1583679 |
| malformed | rejected | 16777215 | not applicable | 0 | 11159.28 | 10546.88 | 60620800 | 33554478 / 18360983 |
| nodes-over | rejected | 400001 | not applicable | 0 | 2628.78 | 2609.38 | 29872128 | 800066 / 1983769 |
| nominal | accepted | 1168 | 1168 | 1 | 13.13 | 15.63 | 30162944 | 4891 / 1584936 |
| overflow | rejected | 1172 | not applicable | 0 | 12.09 | 0.00 | 30048256 | 4891 / 1584940 |
| raw-over | rejected | 16777217 | not applicable | 0 | 11.02 | 31.25 | 60878848 | 33556021 / 18360985 |
| raw-upper-astral | accepted | 16777216 | 1180 | 1 | 10900.40 | 10546.88 | 110764032 | 33557193 / 100767310 |
| raw-upper | accepted | 16777216 | 1168 | 1 | 11003.29 | 10593.75 | 60813312 | 33556019 / 33663791 |
| unique-keys-canonical-over | rejected | 8888604 | not applicable | 0 | 20984.34 | 20906.25 | 66928640 | 29778358 / 25177473 |
| unique-keys-nodes-over | rejected | 8800001 | not applicable | 0 | 20509.61 | 20250.00 | 67055616 | 29601232 / 25000330 |
| unique-keys-root-invalid | rejected | 8888603 | not applicable | 1 | 21476.05 | 21171.88 | 77447168 | 29778356 / 37979016 |
| unique-keys-upper | scanner_accepted | 8888603 | not applicable | 0 | 20721.23 | 20484.38 | 67166208 | 29778356 / 25176863 |
| upper400 | accepted | 108649 | 108649 | 1 | 358.62 | 390.63 | 30621696 | 462238 / 1696105 |

No universal memory/time ceiling or host budget PASS is inferred. In particular, actual astral-plus-whitespace overlap raises measured process peak from60813312 (ASCII raw upper) to110764032 bytes. Its helper allocation peak is100767310 bytes. The scanner's active key set is not equivalent to400 legitimate station IDs.

### Independent fixed counts and whole-helper negative

- `unique-keys-upper`:99999 decoded distinct keys,78/79 UTF-8 bytes per key, depth1,199999 nodes,8388608 canonical bytes,8888603 raw bytes. The escaped initial k contributes five extra raw bytes/key; no native dict is used to construct the input. Observed private scan tuple is exactly `[8388608,199999,1]`; materializer0. It is **not** a gravity-stations-1 root.
- `unique-keys-root-invalid`: identical actual raw SHA `bf080e66423754f7bdabdc1e6607123f14522ff4d32096d6638b337c686cca2d`, public loader, exactly one native materialization, fixed gravity_json_contract, root_accepted=false. Peak77447168 bytes and helper allocation37979016 include native decoded text/dict overhead missing from scanner-only evidence.
- `unique-keys-canonical-over`:99999 keys,199999 nodes,8388609 canonical bytes,8888604 raw bytes; public loader rejects gravity_json_limit before materialization.
- `unique-keys-nodes-over`:100000 keys,200001 nodes,8300001 canonical bytes,8800001 raw bytes; public loader rejects gravity_json_limit before materialization. This is a separate node violation below the canonical cap.
- The negative counts are fixed input arithmetic, not fabricated completed-scan values; `observed_scan=null` for rejects.
- `raw-upper-astral`: the source citation appends literal U+1D11E, UTF-8 ensure_ascii=False emission plus ASCII whitespace to16777216 bytes; unchanged accepted scientific canonical1180 bytes, materializer1. No Unicode normalization/type/hash rewriting.

Helper scratch is0 bytes based on independently executed no-I/O traps, not filesystem telemetry guessed from a directory. Final harness receipts/logs/XML separately occupy **33files/23347bytes**; this count excludes retained earlier runs and all other diagnostic/pytest outputs.

## Independent MAIN/static review : not producer execution

The following was reported directly by MAIN, retained in its own private review tree, not rerun or adopted as producer receipts:

- Exact a730 module SHA83d62675…95bb6e and original test SHA48527def…fe290: real reviewed M01 runtime CPython3.12.10, **179PASS/0SKIP72.90s** including actual retained author-archive negative. Private `gj-main-caa4461d/json-regression.xml`, SHA `3b4220b9ac6c478545d60b5bd18cf3c1b7da915746ac217654f0022cbb9442d2`.
- Ten independent cold resources with tracemalloc, reported max process peak60743680 bytes. These remain original a730/ten-profile execution, not final15-profile evidence or a host budget claim.
- MAIN authored seed202610031118:5000 scalar/nested native/canonical parity controls and17 strict negatives before materializer with safe error context, actual independent helper `gj-main-caa4461d/independent_json_controls.py` SHA `a8ed2d5fee046a41abd8b679362535a97497a82a61da1dd0a1480191edc0d381`. No field/API proof.
- Curie static independent exact a730: no blockers, source/test/core Git bytes verified; later resource delta is not silently within that old static pin.
- MAIN full-read the79-line final test-only9e4d35b delta and reported its separate final **179PASS/0SKIP168.75s**, including165 unchanged M01 tests and the actual protected-author negative, in `gj-final-8b3fe5d9`. Final XML SHA `abdc3fe50bd3b8c4cbf8788d487cf828da20f1a18de1fde65c775f621c1769b2`; exact module/test pins match9e4d35b above. All15 independent cold profiles passed. Reported astral: helper10908.8ms/process CPU10656.2ms/process peak110809088/helper allocation100767215 bytes, accepted/materializer1. Unique upper private scan peak66949120/materializer0; same-byte public wrong-root contract rejection peak77025280/materializer1; canonical+1/node200001 public negatives peak66924544/66617344/materializer0. These are reviewer measurements, not producer execution or a universal resource budget.

This is the sole detailed placement of reviewer runtime/receipt provenance. R-PJB11 remains producer SKIP/UNRESOLVED; independently reported actual-core PASS is attributed, not a fabricated local execution. Final packet review/resource suitability/promotion remain owner decisions.

## Unchanged scope and outstanding holds

Only new helper, new test and this unit's seven docs/evidence belong to the candidate. Ordinary core/adapter/transform/EDI hashes remain the approved values checked by tests; no existing source, API, frontend, dependencies, runtime, canonical data, fixture hash or tolerance changed. Eleven protected diagnostic directories, private outputs and coursebe4 reference are preserved/excluded.

No API/storage/worker/job/bundle/UI integration, admission activation or held physical-vertical waiver. No public method/source eligibility. No merge/deploy/release. Final scoped guard results and remote head are recorded in the review packet/handoff; MAIN final independent replay is reported PASS, but final packet review/promotion remain owner decisions, not replaced by this producer evidence.
