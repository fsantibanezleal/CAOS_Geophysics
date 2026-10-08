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

## Mounting and gates

`JointResultWorkbench` is independently importable. The existing joint instrument
owns the mounting location and single citation provider; a separate mount proposal
adds an explicit supplied-output inspection choice beside existing synthetic replay
and course content. No new top-level shell route or changes to FWI/scientific arrays.
Vitest uses real offline output directories supplied through an external environment
argument, with missing fixtures explicitly skipped and reported. Malformed transport
tests use in-memory mutation, never a modified scientific result on disk. Browser
gates import the same actual outputs and exercise both languages/themes/mobile and
desktop, selectors and downloaded exports. Parent owns integrated mount/render.
