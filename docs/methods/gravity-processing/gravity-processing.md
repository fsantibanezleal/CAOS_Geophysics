# Gravity station processing

This is the local station corrections/QC and harmonic-transform chain. It invokes pinned Boule, Harmonica and Verde, preserves original values and rejects ambiguous or duplicate corrections. Its independent numerical controls are labelled synthetic. Local metric gridding/upward-continuation and blocked-holdout gates are separate from full M01 field and integrated web acceptance, which remains open.

- [Theory, correction state, uncertainty and other-data worked guide](01_station-corrections.md).
- [Theme-aware correction and lineage diagram](station-corrections.svg).
- [Executable authored station control](examples/station-control.json).
- [Requirements and numerical gates](../../design/features/m01-gravity-corrections/requirements.md).
- [Primary-source dossier](../../design/features/m01-gravity-corrections/research.md).
- [Convergence and handoff](../../design/features/m01-gravity-corrections/convergence.md).
- [Equivalent-source theory, blocked validation and other-data exercise](02_equivalent-source-transforms.md).
- [Local transform requirements](../../design/features/m01-gravity-transforms/requirements.md).
