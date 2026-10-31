# Development serialization and external storage

`write_joint_development(directory, request)` is a local exclusive writer for
the existing exact development intake. Request keys are schema
`joint-survey-write-request-1`, survey_request, development, sealed_manifest,
originals. Originals is null (provider reference) or a two-modality dictionary,
each with exact raw and correction bytes. No observation, split or scientific
parameter is changed. No fit or fabricated result is exported by this writer.

All native shape/byte/source/hash/noise/split/commitment checks precede mkdir.
Serialize exact existing28 arrays as NPY1.0 without pickle and request.json;
retain original bytes only when explicitly supplied, with original exact SHA.
Public publication is outside this local operation: provided private_use and
provider_link_only input remains private and the resulting envelope states the
original rights. A new absolute destination is mandatory and its parent must
already exist outside every repository; no overwrite, deletion or fallback to
product/raw/model/temp locations. Reparse/symlink ancestors reject.

The writer validates its output using the genuine strict loader. On a write or
verification failure, leave the incomplete newly created directory as evidence
and report the exception; never delete arbitrary existing input. Exclusive files
and request.json written last make incomplete output un-loadable. Existing native
96MiB and adapter256MiB/256KiB/header limits are unchanged. Before copying arrays,
header bytes and serialized metadata are included in actual output admission.

`local_joint_data_root(root=None)` resolves an explicit absolute argument or
GEOPHYSICS_LOCAL_DATA_ROOT only. It has no repository-relative or machine-specific
default. It creates nothing. This owned helper does not alter the product's source
ledger/root or acquisition, ingestion, ERT and traveltime workflows.

Gate: tests/numerics/test_joint_survey_serialization.py::test_original_roundtrip
checks both uncertainty modes with provided/reference originals, strict loader
identity and unchanged source bytes. Gate:
tests/numerics/test_joint_survey_serialization.py::test_prewrite_rejection checks
source/commitment/extra-key/nonexternal/overwrite rejection before output exists.
Gate: tests/numerics/test_joint_survey_serialization.py::test_explicit_root checks
external roots without repository or system-temp fallback. Complete solver-result
export and solve CLI remain separate JS14/15 obligations, not asserted here.
