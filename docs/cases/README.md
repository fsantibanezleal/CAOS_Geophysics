# Case taxonomy and coverage

The selected case is the workbench unit. Experiments and Benchmark summarize the canonical comparison matrix. All 20 canonical inversion cases are original seeded synthetic records; their known truth is explicitly labelled synthetic.

| Category | Cases | Physical question |
| --- | ---: | --- |
| potential fields | 8 | density, susceptibility, depth, field direction, noise |
| electromagnetics | 4 | layered conductivity, phase, frequency, uncertainty |
| seismic | 4 | acoustic response, update, frequency, cycle skipping |
| joint inversion | 2 | cross-gradient agreement and conflict |
| learned methods | 2 | held-out spatial prior and novelty guard |

Every manifest records case, method, seed, parameters, engine inventory, metrics, and replay artifact. No external raw dataset is silently presented as a canonical case.

## Field-data study outside the synthetic inversion matrix

The [Long Valley repeated-station gravity study](../research/long-valley-field-time-lapse.md) is a separate, source-bound field-processing lesson in the Experiments page. It includes 37 stations, eight occupation epochs, 212 source observations, client-side epoch pairing, and propagated measurement uncertainty. It is not added to the 20-case synthetic inversion benchmark and does not claim corrected residuals, a density model, or a magma-source estimate. The original source table is fetched from USGS by a checksum-pinned local script; the web release receives only the compact reviewed observation artifact.
