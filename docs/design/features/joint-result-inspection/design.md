# Native output to local browser instrument

This unit extends the supplied joint processing contract. It is not a new solver,
HTTP execution endpoint or cached synthetic replay. The offline `solve`,
`evaluate` and `validate` commands retain all scientific responsibility. Native
schemas are defined by joint-survey-inversion/evaluation-unit.md and
calibration-unit.md and the actual corresponding writers. The instrument's
controls affect only inspection: modality, partition, receiver, active cell,
candidate and accepted state. Neither model values nor frozen strengths change.

## Admission and identity

Users select the **output** directory, not a data root containing development or
sealed inputs. Browser directory entries may have a single common directory
prefix; it is stripped once, never accepted as an arbitrary path. Only fixed
ordinary relative identifiers with `.json` or `.npy` extensions are admitted.
Paths, duplicate/case variants, missing/extra entries, nonfinite metadata,
prototype keys, duplicate JSON keys, over-depth records and unsupported epochs
reject. Maximum256MiB transport,256KiB per JSON, depth8,4096 mesh cells,
2048 receivers per modality,26 candidates,251 accepted states. All descriptors
and all literal NPY1 headers are admitted before any value decoding or hashing.
No ZIP import or automatic filesystem extraction. Original bytes and their
SHA-256 receipts are preserved. Export is a stored private ZIP, with the original
relative directory structure, using the product's existing fflate dependency.

Native result manifests bind file and data hashes. The browser also checks shared
plan/development/freeze/selection identities, q arrays, physical scaling, exact
mesh geometry, row partitions, signed residual arithmetic, metric arithmetic,
and ledger terminal/state/selection consistency. These checks are **inspection
consistency**, not independent forward-kernel/objective/KKT replay. Source hashes
are displayed as declarations pinned to the reviewed optimizer ABI. No untrusted
file imports modules or defines executable callbacks. A rehashed malicious archive
is not authenticated. Offline validation still requires original development and
sealed inputs and the pinned physical runtime.

## Views

The component composes the existing instrument/table/plot-pair classes and
ScientificPlots.Plot in the existing shell; no shell, font or page CSS is copied.
Receiver curves use exported row indices, not invented coordinates. Exact selected
values stay readable; whitened residuals are Cholesky/principal-marginal outputs,
not silently labelled per-receiver SD residuals. Physical cells use native active
indices and centres/bounds/volumes with density kg/m3 and SI susceptibility. Inactive
cells are not filled or interpolated. Candidate and accepted-state inspection shows
the recorded physical property blocks and exported five scalar terms. There are no
synthetic historical response curves, CrossGradient vector-factor maps, animations
that imply refits, inferred geological truth or public rights claims.

Completed evaluate mode always remains a supplied-model evaluation. Solve receipt
reports execution but individual attempts may still fail or be nonconverged.
The browser's own flags `offline_scientific_replay_performed`,
`inverse_executed_in_browser`, `scientific_acceptance_verified`,
`field_eligible`, `public_redistribution` remain false in all inspection exports.
Failed workflow display has no completed sealed result; an unreplayed last attempt
is explicitly distinct from the replay-verified prefix. Interrupted output may
contain earlier calibration/frozen/model/result files; these are preserved but not
promoted to completed science merely because they exist.

Pre-code technical review clarifications: an offline writer's replay-verified
prefix label remains a declaration, never browser-established physics or
authenticity. Signed residual arithmetic is predicted-minus-observed and is
checked on imported arrays. All original occurrences are charged before reads;
histories exceeding caps reject, never truncate. Typed float arrays share owned
original byte buffers, but crypto/export copies still consume memory. Maximum
input/mobile support requires actual browser measurements, not byte admission.
Any failed workflow marker overrides earlier completed files. Historical terms
and physical blocks bind the exact attempt/state and that attempt's fixed weights,
not the terminal model's metrics. Missing actual fixtures remain explicit skips.

Native failed-inventory clarification before admission correction: the completed
calibration may be retained beside a separately serialized26-candidate aborted
prefix. These are actual repeated file occurrences and both charge the unchanged
256MiB whole-byte cap. A complete solve has at most568members; retained failure
with duplicate calibration/abort histories and all durable directories has at
most1090members. Use a1100file transport cap plus exact per-directory inventories,
not a700file assumption derived from the completed-only layout. This changes no
physical array, solver tolerance, scientific budget or accepted native schema;
it prevents genuine late failures being excluded from inspection.

## Mounting and gates

`JointResultWorkbench` is independently importable. The existing joint instrument
owns the mounting location and single citation provider; a separate mount proposal
adds an explicit supplied-output inspection choice beside existing synthetic replay
and course content. No new top-level shell route or changes to FWI/scientific arrays.
Vitest uses real offline output directories supplied through an external environment
argument, with missing fixtures explicitly skipped and reported. Malformed transport
tests use in-memory mutation, never a modified scientific result on disk. Browser
gates import the same actual outputs and exercise both languages/themes/mobile and
desktop, selectors and downloaded exports. Integrated mount/render is separately
qualified in the actual application.

## Bounded asynchronous native reads and immutable digests

After whole metadata admission, the importer reads at most four small original
NPY members (each at most256KiB) concurrently, with a complete drain on error
or cancellation. Large members are read alone. Every original header must pass
before any array hash or value decoding. This retains the original256MiB whole
transport/logical limits; it does not preload or reuse a previously passed input.

The next phase uses the same small-file/large-alone schedule. Each task verifies
the actual whole-file SHA256, then the exact data-view SHA256, then decodes.
At most four <=256KiB digest input snapshots exist concurrently. Any batch's
rejection or cancellation drains all its submitted work before propagating;
no partially checked inspection escapes. Returned hashes are computed actual
digests, not descriptor declarations. Export still independently rehashes every
original and refuses altered bytes.

[WebCrypto digest's normative input snapshot](https://www.w3.org/TR/webcrypto/#SubtleCrypto-method-digest)
copies the exact BufferSource bytes before returning its Promise. Nonshared
views therefore need no additional full JS slice; shared/other buffers take an
owned copy. Immediate caller mutation and exact subarray offset/length are
tested. This does not establish whole-browser memory, cold-device timing,
hard-realtime interruption, authenticity, physical replay or scientific accuracy.
The actual native-output tests use asynchronous original-file readers matching
the browser contract, with unchanged corruption/array/export assertions,
all24 outputs and their original5s/30s test deadlines.
