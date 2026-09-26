# Scientific recovery design

Read alongside `docs/research/recovery-2026-09-24.md` and the retained audit. This unit corrects the existing scientific pipeline rather than changing shell architecture or deployment targets. User authorization covers the audit findings plus open EDI, PGI and ensemble work.

## Contracts

Keep the existing replay arrays and add typed evaluation, solver settings, state identity, sample provenance and uncertainty fields. Every added method exports its actual parameter target and unit. Shared data units never depend on method selection. Explicit per-method applicability prevents a regularization control from claiming to retrain a frozen neural checkpoint.

## Architecture

Common evaluation functions independently derive data/model/baseline metrics. Potential inversion, joint/PGI, MT, seismic and learning consume those evaluators. A release validation script reads every result and records method-level recovery verdicts; it is executed locally, never as GPU training in CI. Static CI validates the committed evidence contract. Heavy solves and ensembles remain local; the browser offers bounded live MT and reads the canonical evidence.

Potential-field regularization uses physical mesh derivatives and noise weighting. Select tradeoffs without target truth. Compare conventional coefficient L2/sparse priors, three-component magnetization and joint objectives using matched data and explicit mismatch controls. Preserve genuine nonuniqueness rather than forcing estimates to known masks.

FWI separates initial/background parameterization, Hz-defined frequency stages, accepted optimizer states, and acquisition geometry. Final predictions, residuals and model must belong to one identical selected state. Nominal layered/fault/channel reference cases must improve whole-model initial RMSE; salt remains a declared cycle-skipping challenge. Variant failures are retained and marked unsuccessful, never silently dropped. A release with every nominal FWI failure is rejected.

MT shares bounds and mean-of-real-component-squares normalization across optimizers. EDI processing is explicit about native E/B versus SI E/H units, sign/time convention, tensor orientation and absent covariance. The 1D solver does not pretend that arbitrary 3D transfer functions satisfy its assumptions.

PGI consumes independent petrophysical sample fixtures, not recovered-case truth labels. Mixture prior fit, objectives, responsibilities and recovered lithology are exported. Structural coupling and PGI are separate algorithms, with identical initialization and uncoupled data/spatial prior baseline.

Uncertainty includes repeatable conditional noise ensembles and an independently seeded calibration set. Interval calibration is measured, not assumed. Expose coverage separately for active cells/parameters and background. No aggregate score merges incompatible scientific quantities.

Learning keeps explicit train/validation/calibration/test roles. Classical and learned baselines get the same noisy inputs. Checkpoint selection and rejection thresholds must not use display-case truth. Out-of-distribution failures remain part of the result matrix.

## Acceptance and adversarial review

Pre-implementation review rejects: selecting beta by held-out true-model error; initializing from smoothed truth; replacing physical inverses with known geometry fits without naming a distinct constrained method; labeling bootstrap spread as posterior probability; silently filtering failure cases; and merely relaxing gates to accept prior outputs. The selected design adds metrics and actual method improvements. Requirement-to-gate convergence will be recorded after execution, not inferred from this document.

Computational probes write only to ignored experiment directories. Production arrays stay intact until replacement candidates pass tests. Canonical bake, builds, Git promotion and deployments are separate recorded stages. The interface keeps shared fonts, palette, primitives, six routes and bilingual scientific content.
