# Deployment verification: 0.03.000

Verified on 2026-09-24 after the ADR UI correction and full numerical refinement.

- Application commit: `b3863eacfd9e6be7e5435861c8877e235f38b1f7`.
- Task-to-develop PR [#12](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/12), merge `3b749ab`.
- Develop CI [35957240225](https://github.com/fsantibanezleal/CAOS_Geophysics/actions/runs/35957240225): success.
- Develop-to-main PR [#13](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/13), merge `4aec26d`.
- Main CI [35957423285](https://github.com/fsantibanezleal/CAOS_Geophysics/actions/runs/35957423285): success.
- Pages [35957423269](https://github.com/fsantibanezleal/CAOS_Geophysics/actions/runs/35957423269): success.
- VPS immutable release: `/var/www/geophysics.ml.fasl-work.com/releases/20260924044648`.
  Nginx configuration test and reload succeeded. The previous release remains recoverable.

## External verification

`scripts/verify_deployment.py` verified normal certificate validation on both HTTPS origins,
downloaded all 120 experiment artifacts and checked every SHA-256 and byte size. It also compared
six route HTML documents and all three model files with local bytes. The machine-readable receipt
is [deployment.json](deployment.json).

| Item | Value |
|---|---|
| Catalogue SHA-256 | `580ec02af9a8e80d55e3444c0d0bcd9bef1b25753236089cd96af8ffc658332c` |
| HTML SHA-256 | `761cf7540b83c4e047134806280290193781f71fb38ca516d3dac0af078bd887` |
| VPS | https://geophysics.ml.fasl-work.com/ |
| Pages | https://fsantibanezleal.github.io/CAOS_Geophysics/ |

These checks cover numerical files and route documents, not a claim of exhaustive browser behavior.
Rendered checks complement them: the VPS direct Implementation route displayed the new equations
and algorithm panels; its opposing-density 3D case loaded the refined mesh. The Pages direct
Benchmark route populated real numerical values. Pages navigation, refined fault-wave playback,
pause/scrub, Spanish and theme switching were exercised with zero browser console errors observed.
All twenty cases, eleven algorithm panels and responsive controls were inspected locally as detailed
in [scientific-ui-0.03.md](scientific-ui-0.03.md).

The remaining EDI, PGI and ensemble workflows are tracked in issue #10. Publishing this correction
does not mark those research extensions complete or establish user aesthetic acceptance.
