# Inverse Earth Studio: replacement design

Date: 2026-09-23. Authority: the user rejected the original release and explicitly instructed a complete rebuild, including all cases, UI, UX, diagrams and visualizations. This document records that authorized correction. Version 0.01.000 is rejected and is not a scientific baseline.

## Problem

Enable inspection of the relationship between a geological model, the survey that measures it, and the model recovered from those observations. Distinct physics require distinct data and representations. Synthetic experiments establish reproducibility and algorithm behavior, not field validation or a novel inversion algorithm.

## Contracts and lanes

Input: typed case registry with family, geological construction, seed, SI geometry, property units, source/receiver geometry, declared observation noise and six acquisition/regularization variants. External observation CSV is validated before fitting; non-finite values, missing columns, duplicate locations and nonpositive errors fail. Preprocessing preserves physical quantities and records centering/scaling only for learning.

Output: `inverse-earth/v2` catalogue and individual case/variant runs. Each run contains volume or section coordinates, truth, observed measurements, noise, per-method reconstructions, predictions, residuals, objective history, metrics, provenance and runtime. Index entries carry SHA-256 and byte size. Numerical work uses published SimPEG, SciPy and Deepwave/PyTorch; product orchestration is plain Python scripts, not an internal package. Canonical solves and training run locally; public deployments serve committed artifacts. Browser interactions rotate, slice, compare, replay iterations and wavefields, and select six genuinely recomputed variants. Lightweight MT forward modelling on user input is a separate deterministic browser tool, parity tested against the offline recursion; it does not invert uploaded observations.

## Cases

Potential fields: offset intrusive stock, negative-density asymmetric basin, paired opposing bodies, faulted/dipping contact, narrow dipping magnetic dyke, remanent tabular body, deep compact lens, crossing dykes. EM: resistive cap, conductive middle layer, alternating multilayer, noisy deep conductor. Seismic: horizontally layered reflections, fault displacement, salt dome with missing low frequencies, low-velocity gas lens. Joint: shared contact and disjoint bodies. Learning: held-out oblique intrusion and anomalous ring geometry. Each uses a separate construction, not a shift of one Gaussian. Six variants change physical contrast, data noise, height/frequency, survey coverage and regularization, with family-specific meanings.

## Method acceptance

Gravity forward uses the SimPEG 3D prism operator. Weighted L2 and sparse IRLS solve separate objectives with exported histories and data residuals. Magnetics includes a scalar induced model and a three-component magnetization solve. Layered MT preserves complex impedance; bounded least squares and a differentiable neural parameterization both optimize against complex observations. Seismic propagation and gradients call Deepwave; direct FWI and multiscale FWI optimize measured shots and expose the returned receiver gathers. Joint inversion optimizes two data fits with explicit cross-gradient coupling. A trained convolutional inverse maps gravity observations to depth-integrated density, and a trained autoencoder returns actual reconstruction error. Learned checkpoints, training split, held-out classical comparison and losses are persisted.

## UI and visual language

Keep the shared shell and six routes. Replace all app-specific styling. Use neutral ivory/white light surfaces, charcoal dark surfaces, ink text, a restrained blue interaction accent, and physical colormaps with legends. No purple/cyan/amber dashboard gradients. One 300px control rail plus a dominant instrument, organized into at most five measurement families. Show only relevant controls. Potential fields use rotatable 3D voxels, a survey surface and linked orthogonal sections; MT uses a log-resistivity depth column plus log-frequency impedance plots; seismic uses receiver-time gathers, velocity sections and actual wavefield frames. Residuals use a zero-centered diverging scale. Truth/recovered comparison has shared limits. All views include units, coordinate readouts and labeled acquisition geometry. No claim of certainty inferred from a noise slider.

## Requirements and gates

R-001 THE pipeline SHALL produce distinct geological arrays for all 20 cases. Gate: `scripts/check_artifacts.py`, checking truth hashes, identities, shapes and all variant artifacts; rendered case walkthrough.

R-002 THE potential-field inverse SHALL fit actual SimPEG-generated observations with separately exported L2 and IRLS results. Gate: `tests/test_rebuild.py::test_inverse_improves_data_fit`, `test_gravity_independent_prism_and_linear_scaling` and release objective audit.

R-003 THE MT solver SHALL reproduce a homogeneous halfspace and fit layered complex impedance. Gate: `tests/test_rebuild.py::test_mt_halfspace_and_split_homogeneous_layer`, `test_mt_autodiff_parity_and_directional_derivative` and `test_all_artifact_cells[mt]`.

R-004 THE FWI solver SHALL differentiate Deepwave receiver residuals and record before/after data misfit. Gate: `tests/test_rebuild.py::test_deepwave_cuda_adjoint_directional_derivative` and `test_all_artifact_cells[seismic]`.

R-005 THE learned tools SHALL load persisted checkpoints and evaluate held-out geometry groups. Gate: `tests/test_rebuild.py::test_learning_split_hashes_and_checkpoint_inference` and `scripts/check_artifacts.py`.

R-006 WHEN a case or variant changes, THE web SHALL show that artifact's model and measured response. Gate: rendered case/variant walkthrough and `frontend/src/test/contract.test.ts`.

R-007 THE public release SHALL contain every case, all six variants and every family-applicable method. Gate: `scripts/check_artifacts.py`, including file hashes, finite values and matrix completeness.

R-008 THE workbench SHALL expose rotation, slice, property/model selection, comparison, meaningful playback, reset and export without page overflow. Gate: rendered pointer walkthrough at 1280x800, 1600x900, 2560x1440 and 390x844, both themes.

R-009 THE docs SHALL describe implemented equations, assumptions, limitations, acquisition and reproducibility using verified primary references. Gate: source-to-document review recorded in `docs/design/acceptance.md`.

R-010 THE build SHALL preserve the public shared shell, six routes and EN/ES UI. Gate: frontend build and rendered navigation/language acceptance.

## Deployment and failure criteria

The existing Pages and ML static destinations remain authorized. The workload runs on the local RTX 4070 and the web ships compact results. Measure total artifact bytes, initial route latency and GPU memory before promotion. Stop release on duplicate geology, claimed method without solver output, invalid units, missing checkpoint, empty evidence, non-finite arrays, false metric labels, UI clipping or unresolved route errors. Deployment success alone is not acceptance.

## Sources

- SimPEG framework: https://doi.org/10.1016/j.cageo.2015.09.015
- SimPEG EM: https://doi.org/10.1016/j.cageo.2017.06.018
- Choclo coordinate and unit conventions: https://www.fatiando.org/choclo/latest/overview.html
- Deepwave differentiable FWI: https://ausargeo.com/deepwave/example_fwi
- FWI review: https://doi.org/10.1190/1.3238367
- Cross-gradient inversion: https://doi.org/10.1029/2003GL017370
- Course inspiration: https://github.com/Anagabrielamantilla/inversion-geofisica-python

## Design review

Rejected alternatives: recolouring the old plots, switching method labels over one result, increasing synthetic counts by only shifting a shared Gaussian, fitting against test truth, and calling solver import checks numerical validation. Review outcome: implement the case-first result contract above; retain unmet gates explicitly until their evidence exists.
