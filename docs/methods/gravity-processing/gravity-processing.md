# Gravity station processing

This is the local station corrections/QC unit. It invokes pinned Boule and Harmonica, preserves original values and rejects ambiguous or duplicate corrections. Its numerical controls are labelled synthetic. Full M01 field, map/holdout, transform and integrated web acceptance remains open.

- [Theory, correction state, uncertainty and other-data worked guide](01_station-corrections.md).
- [Theme-aware correction and lineage diagram](station-corrections.svg).
- [Executable authored station control](examples/station-control.json).
- [Requirements and numerical gates](../../design/features/m01-gravity-corrections/requirements.md).
- [Primary-source dossier](../../design/features/m01-gravity-corrections/research.md).
- [Convergence and handoff](../../design/features/m01-gravity-corrections/convergence.md).
