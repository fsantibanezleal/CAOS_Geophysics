# M08 waveform implementation and remaining gates

Scientific requirements and tolerances are unchanged. Operational direction, dependency inventories and execution receipts are private; this table reports component scope, not production authority.

| Component | Implemented boundary | Remaining gate |
| --- | --- | --- |
| Ordinary input/QC | Exact MiniSEED2 preflight, typed StationXML epochs/stages, request/rights declaration | Hostile native containment, source authenticity/rights |
| Response/filter/PSD/onsets | Real engine, independent complex/direct numerical controls, unlabelled intervals | Whole-method acceptance and resource eligibility |
| A1 formats | UTF8/explicit Latin1; transparent unity ledger; FIR DC; named cloud10, legacy9 unchanged | Unchanged-original native physical run in containment |
| A2 export | Bounded streaming, exclusive files, strict manifest/evaluation, read-only reopen | Contained-child integration; power-loss durability not claimed |
| A3 files/CLI | Exact held paths, new-only output, safe CLI/wrappers, ordinary callable seam | Positive child CLI requires A4; current CLI refuses before reads/output |
| A4 Windows | Concrete signature/ABI/containment contract only | Actual code/probe/closure/private context and OS controls NOT_RUN |
| A5 Linux | Separate required containment/accounting contract | Concrete source/context and actual controls NOT_RUN |

## Immutable scientific cases

The selected Ridgecrest original retains the [historical XML rejection](evidence/ridgecrest-terminal-20261003.json), committed before catalogue access, and [historical legacy-STP rejection](evidence/ridgecrest-phase-20261003.json). Current format admission is tested on unchanged originals, not a replacement terminal for either receipt. The cloud catalogue's GSC row is HHZ; selected HNZ references remain empty / not_evaluable. Original native physical correction is NOT_RUN, not inferred from schema validity.

The [authored worked artifact](../../../../data/derived/waveform/m08-authored-worked.json) and [held-out replay](../../../../data/derived/waveform/m08-heldout-display-replay.json) remain byte-unchanged. The inspected display subset has23 valid inputs and one QC rejection, exact comparator onset agreement but weak catalogue agreement. It is not a new blind cohort or instrument-response field validation.

## Test-first and integration

Owned tests cover exact byte/hash domains, parser caps, response ledgers and chain parity, DC/phase, direct DSP comparisons, masks/candidates, seals, corrupt exports/read-only reopening, paths and unavailable CLI. Original tests require explicit private opt-in; absence is an explicit skip, not clearance. Tests write fresh temp fixtures and never fetch providers.

The [intrinsic matrix](intrinsic-validation.md) retains every positive/adversarial/native gate. A test file's existence is not evidence that the full matrix passed. Cold upper resource/crash/cancel/exited-descendant/parent-final controls remain NOT_RUN. No imaginary provider, uncontained fallback, weakened threshold or substitute station closes those gates.

See the [science chapter](../../../methods/waveform-processing.md), [user-data/export guide](../../../methods/waveform-local-data.md), [contracts](contracts.md), [algorithms](algorithms.md) and [amendment](intrinsic-amendment.md). Full method/API/UI/platform acceptance stays open. Auth/admin/production backup are deferred, not removed from the platform.
