# M13 real-waveform adversarial validation

Each Python entry point executes the owning focused test with its normal pytest
fixtures. The browser contract gate tests tampered real held-out asset identity.
These gates protect the defined pipeline; they do not turn STEAD analyst picks
into geological truth or establish transfer to a new network or field catalogue.

| requirement | adversarial check | gate |
| --- | --- | --- |
| PH-001 | Plant altered archive bytes, unsafe members and malformed source metadata; verify the reader refuses before decoding. | `tests/adversarial/test_phase_picking_adversarial.py::test_adversarial_ph_001_archive` |
| PH-002 | Plant invalid channel geometry, rate, pick order, units and nonfinite values; verify typed rejection with no fabricated samples. | `tests/adversarial/test_phase_picking_adversarial.py::test_adversarial_ph_002_trace_contract` |
| PH-003 | Plant overlapping events/stations and nondeterministic metadata; verify the split remains joint, disjoint and reproducible. | `tests/adversarial/test_phase_picking_adversarial.py::test_adversarial_ph_003_split` |
| PH-004 | Plant failed picks and noise rows on matched held-out identities; verify M08 and M13 are scored on the same records with failures retained. | `tests/adversarial/test_phase_picking_adversarial.py::test_adversarial_ph_004_matched_evaluation` |
| PH-005 | Plant waveform bytes on the QC-rejected held-out row; verify the browser contract refuses the trace before inference or export. | `frontend/src/test/phase-browser-contract.test.ts::adversarial: rejects waveform bytes added to the QC-rejected held-out row` |
| PH-006 | Plant a finalized receipt whose release flag claims acceptance; verify export identity and the explicit unaccepted state remain bound. | `tests/adversarial/test_phase_picking_adversarial.py::test_adversarial_ph_006_rights_boundary` |
| PH-007 | Plant malformed bucket slices, duplicate/flat components and source format mismatches; verify the STEAD reader rejects them. | `tests/adversarial/test_phase_picking_adversarial.py::test_adversarial_ph_007_bucket_reader` |
| PH-008 | Plant event/station cross-partition reuse and invalid noise assignment; verify metadata selection quarantines conflicts. | `tests/adversarial/test_phase_picking_adversarial.py::test_adversarial_ph_008_joint_selection` |
| PH-009 | Plant wrong tensor shape/order and invalid target construction; verify the model contract and gradient path reject the mismatch. | `tests/adversarial/test_phase_picking_adversarial.py::test_adversarial_ph_009_model_contract` |
| PH-010 | Plant a QC failure eligible for silent replacement and attempt test extraction without a frozen receipt; verify the test remains sealed and QC identity is retained. | `tests/adversarial/test_phase_picking_adversarial.py::test_adversarial_ph_010_extraction_freeze` |
| PH-011 | Plant the same normalized waveform under different event/station IDs across partitions; verify exact-array overlap blocks training. | `tests/adversarial/test_phase_picking_adversarial.py::test_adversarial_ph_011_exact_overlap` |
| PH-012 | Plant fp16 gradient overflow; verify no corrupt optimizer update is applied, scale backs off, and persistence fails closed. | `tests/adversarial/test_phase_picking_adversarial.py::test_adversarial_ph_012_amp_overflow` |
| PH-013 | Plant a narrow-clock shortcut and noisy false-pick condition; verify the dev-only screen detects the shortcut before the sealed test opens. | `tests/adversarial/test_phase_picking_adversarial.py::test_adversarial_ph_013_clock_and_noise_screen` |
| PH-014 | Plant a QC-rejected browser record or change its display selection after scoring; verify the predeclared 24/23/1 population and full 6,000-trace denominator. | `tests/adversarial/test_phase_picking_adversarial.py::test_adversarial_ph_014_display_population` |
