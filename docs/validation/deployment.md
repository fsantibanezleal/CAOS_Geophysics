# v2 deployment receipt

Verified 2026-09-24 UTC. This is a release of the replacement instrument, not an assertion that every ambition in the original v1 plan was implemented.

## Released code and gates

- Rebuild PR #4 into develop, promotion PR #5 into main.
- Production QA corrections: PR #6 into develop, promotion PR #7 into main.
- Deployed source: `12fbc7f3155164e11b75fda53cc2ef4aa166ed90`.
- Develop correction CI: [35950964305](https://github.com/fsantibanezleal/CAOS_Geophysics/actions/runs/35950964305), successful.
- Main CI: [35951086965](https://github.com/fsantibanezleal/CAOS_Geophysics/actions/runs/35951086965), successful.
- Pages: [35951087029](https://github.com/fsantibanezleal/CAOS_Geophysics/actions/runs/35951087029), successful.
- ML immutable release: `/var/www/geophysics.ml.fasl-work.com/releases/20260924032105`. Nginx validation/reload succeeded. Previous releases remain available for rollback.

## External verification

`scripts/verify_deployment.py` fetched the following from both [ML VPS](https://geophysics.ml.fasl-work.com/) and [GitHub Pages](https://fsantibanezleal.github.io/CAOS_Geophysics/), with normal TLS hostname/certificate validation enabled:

- Exact catalogue bytes, 20 cases and 120 experiment files, each checked against its SHA-256 and byte length.
- Six directly loaded route documents, each matching the local production `index.html` bytes.
- The CNN, autoencoder and training-ledger files, each matching the local release bytes.

Machine-readable receipts: [deployment.json](deployment.json). Catalogue hash: `3c544d0f15a48845ec5561e0970fc7fc03f71cb38c8dd6bde6b105024d4379c2`. Final HTML hash: `f11f94a34fc287722fc16f72d9e51e17d71703b8252387a2d06f35ec76b97108`.

## Rendered production checks

The browser loaded live 3D magnetic dykes, exercised angle-step and northing cut, played/paused/scrubbed actual acoustic pressure states, changed a live MT resistivity, and loaded the benchmark's 20/120/324/1120 counts with numerical tables. On Pages, direct benchmark loading, corrected brand navigation under the project base, seismic velocity-RMSE default, layered MT, Spanish/light mode and the 390x844 phone layout were checked. The mobile document measured exactly 390x844 without horizontal overflow. Architecture diagrams rendered on a deep route. No production console errors were observed.

An already-open Pages document briefly retained the previous cached HTML. A fresh release URL loaded the corrected build; independent no-cache HTTP verification passed the canonical URLs as well. Use a hard refresh after a release if an existing tab still shows an older interface.

## Scientific boundary

Original synthetic cases; actual local solver computation and CUDA evidence; static public replay plus live layered MT forward modelling. No hosted GPU service, field-scale interpretation, posterior confidence or algorithmic-novelty claim. EDI ingestion, PGI and ensemble uncertainty from the original broad plan are not implemented and are not certified by this release. The technical manuscript reports implemented methods and negative results explicitly. The user's aesthetic acceptance is not inferred from engineering checks.
