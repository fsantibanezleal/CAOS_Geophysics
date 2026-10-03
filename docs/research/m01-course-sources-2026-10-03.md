# M01 course source inspection and research receipts

Date: 2026-10-03. This is a source-inspection record, not a numerical run or field-source receipt. Base: `4db6a1613373d139e4496b6392e605c36adfa978`. Worktree: geophysics-m01-corrections; branch: task/geophysics-m01-scientific-course-sdd. Original station-adapter branch/reference `9ce5cc97a9d3e3c77a9a893868d1e1b1b3c3d048` is preserved.

## Primary sources and inspection depth

| Source | Read/use boundary |
| --- | --- |
| [Boule 0.5 normal gravity](https://www.fatiando.org/boule/v0.5.0/user_guide/normal_gravity.html), [Ellipsoid API](https://www.fatiando.org/boule/v0.5.0/api/generated/boule.Ellipsoid.html) | Normal rotating potential, geodetic latitude, height domain, mGal and co-located reference discussion inspected; closed-form height engine remains authoritative |
| [Harmonica 0.7 plate](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.bouguer_correction.html), [topographic guide](https://www.fatiando.org/harmonica/v0.7.0/user_guide/topographic_correction.html) | Plate formula/API and prism-topography section inspected; external DEM modelling is distinct from supplied signed residual |
| [Harmonica EquivalentSources](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.EquivalentSources.html) | Scalar 1/r, custom source positions, damping and coordinate/API sections inspected; no gradient-boosting implementation proposed |
| [Verde 1.9 least-squares source](https://www.fatiando.org/verde/v1.9.0/_modules/verde/base/least_squares.html) | Full least_squares function inspected: StandardScaler without centering, Ridge alpha, sample weights and unscaling |
| [BlockKFold](https://www.fatiando.org/verde/v1.9.0/api/generated/verde.BlockKFold.html), [BlockShuffleSplit](https://www.fatiando.org/verde/v1.9.0/api/generated/verde.BlockShuffleSplit.html) | Shape order, shuffle/random-state, balancing and block fractions inspected |
| [Harmonica upward kernel](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.filters.upward_continuation_kernel.html) | Fourier attenuation equation and wavenumber convention inspected; explanatory flat-plane model only |
| [NOAA GEOID18 technical details](https://www.ngs.noaa.gov/GEOID/GEOID18/geoid18_tech_details.shtml) | NAD83(2011)/NAVD88 reference and geoid error definitions inspected; not a Bartlett conversion receipt |
| [JCGM 100:2008](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf), [Amendment 1:2026](https://www.bipm.org/documents/20126/2071204/JCGM_100_Amd1_2026.pdf) | First-order covariance section inspected; five-page 2026 amendment read completely, including nonlinearity caution. Original course derivations, not a translated reproduction of the publication |
| [Li and Gotze 2001](https://geored2.sgc.gov.co/Articulos%20y%20documentacion/Li_G_Tut.pdf), [DOI](https://doi.org/10.1190/1.1487109) | Introductory reference-surface discussion inspected; DOI/year checked. Not a claim to have reproduced the complete appendix |
| [USGS OFR 2006-1204 computations](https://pubs.usgs.gov/of/2006/1204/Gravity/computations.pdf) | Actual HTTP bytes checked below; web extraction unavailable. Indexed Somigliana constants are supporting reference, not a fully read PDF or new oracle execution |
| [USGS OFR 2014-1043](https://pubs.usgs.gov/of/2014/1043/pdf/ofr2014-1043.pdf) | Official indexed reduction excerpt only; subsequent direct access 403. Provider free-air/Bouguer conventions cannot be silently equated to current core outputs |
| [Dampney 1969 DOI](https://doi.org/10.1190/1.1439996) | Bibliographic identity verified: equivalent-source technique, Geophysics 34(1). Full paper not accessed; no unread formula claimed |
| [Roberts et al. 2017](https://nsojournals.onlinelibrary.wiley.com/doi/full/10.1111/ecog.02881) | Primary publisher indexed structured-CV discussion consulted; not a newly reproduced full-paper study or guarantee of independence |

Versioned engine documents are selected deliberately to match existing pins, not to authorize dependency updates. Access date is not a source publication date. Bibliographic sources do not substitute for independent numerical controls.

## Direct HTTP byte receipts

PowerShell Invoke-WebRequest, response RawContentStream bytes, SHA-256 in memory; no source files saved or redistributed. All responses below were HTTP 200 on 2026-10-03 between 11:40:31 and 11:40:36 UTC. These are transport-byte checks, not full-text-read assertions or provider/physics approval. HTML responses can change without a version identifier changing.

| URL (source label above) | Bytes | SHA-256 |
| --- | ---: | --- |
| Boule normal guide | 72969 | `1f3efd89115714649e18d562d45f3a607aa1a367467221c48948db817b1a0af1` |
| Boule Ellipsoid API | 113375 | `a3d028ae353f083ac39a1ab89bd9619636a07293327ff15e0069d85bbbe8100f` |
| Harmonica plate API | 36170 | `602224789f53b724416d04c41c86d0b50693409992d03d50f21f838f1f11e5a3` |
| Harmonica topographic guide | 127984 | `eccd397f895243ad0b991cea70c4a187065f4f5a223ef0efe3da73cfe338a311` |
| Harmonica EquivalentSources | 128251 | `e0fbc5a8d1af70789aba77042c879495577377d984730d4dadc106c3dc5beea4` |
| Verde least-squares source | 33064 | `673acf5af11fed6dabb81dd918e3c3d5b2cc2daeaa2f34eeeb82b48030454d7b` |
| Verde BlockKFold | 58813 | `2164ba0aab38cd3bbaf375b619b92e2ea52e5c622e85f9f1b95998c11775c304` |
| Verde BlockShuffleSplit | 57664 | `aabac5e77db3189cabe842641d977a31c24d88337dc98ec12556a22d5a39d972` |
| Harmonica upward kernel | 34608 | `902214b958cb4a3d2c2691c693f09c4d8358ebd481fa9ceeeae606bcccf08eba` |
| NOAA GEOID18 | 34388 | `71443e12542cafe478a2d8597e622193bc9733b30ab3c5cea3e99469dc332a51` |
| USGS computations PDF | 1070185 | `a96abcdf0adddd2b3fcd891adf064a18fdae37e0e73614804415f98af16efe59` |

## Actual local sources fully read

Scientific functions and CLI/scripts were read, not imported/executed for this course proposal:

| File | SHA-256 |
| --- | --- |
| data-pipeline/gravity_processing.py | `7863699269b491c2895bcf030d3fb65cf27ac32a652fce91112bc2c7c9c73321` |
| data-pipeline/gravity_station_adapter.py | `b770b16ef87e83dd92f65a90472145ef93a525a9cedf7f55ee3e6f20f8a10cf8` |
| data-pipeline/gravity_transforms.py | `d11d0f207c89c308c9f8711da2a31b84b8adaeb0c12597a5ecc89ce527fdecf0` |
| data-pipeline/gravity_transform_controls.py | `5ed27d94f55adbfbfabb7db7371affacd42b1d0bb1887ed2322fc36df077afc9` |
| data-pipeline/gravity_transform_figures.py | `4a529f2f19bce53ea80d14c007a43d65f99cbd707ad49e2e9bb3cfbf3c96a273` |
| frontend/src/components/OnlineMTCourse.tsx | `1cdfa1a371b901de43f0b6aa4ae7ff9d65d7604f49aed7a623bb093777356f6c` |
| frontend/src/data/online-mt-course.ts | `c0d7041a799eb6fcda968f1f544ffe3ae11b4b9ee63ea7aa4e6d43f6fc1faede` |
| frontend/src/components/OnlineMTExercise.tsx | `9a1ec3758ce8360ab3702643194609f308bbbf28c79dc498ecd9a5d740d51d16` |
| frontend/src/components/OnlineMTDiagram.tsx | `d85d71b72072f64a91935665b12cc7c42bffda85e9034a07bd99364c65e45e7d` |
| frontend/src/data/online-mt-worked.json | `5092c98b177bf58f6df43cab01ebe4ff8c4e5e832caf3c1249b2e03ee7c650a9` |
| tests/test_online_mt_course.py | `cc9a1d18dd20668b5b49f6f4e75da6c446cbfdebe669d88b1be6410c61496f74` |

Also read: complete product docs/design/SDD.md; M05/M06 online-mt-course research/requirements/design/tasks; current course guides and scoped CSS; M01 existing guides, transform research/requirements, requirements-m01*.txt and paired gravity/transform scripts. Inspected Research.tsx course integration locations, not authorization to edit that large route. Existing independent Somigliana/formula tests were consulted, not rerun.

Shared-shell package 0.6.8 was inspected read-only in the installed product checkout: README, package.json, full dist/index.d.ts and styles.css. No dependency installation or own frontend environment was created. Governance read first: management Entry_point.md, ADR-0069/0075, ADR-0016/0017/0071 and spec/workflow conventions. The shell owns fonts, themes, page width, tabs, equations, references and figure palette. ADR-0017 excludes ReferenceList use despite its library export; cite per section instead.

## Preserved non-claims

No new research download of private Bartlett/author data; MAIN owns acquisition/profile/rights receipts. Existing source review records eligibility gaps, not eligible field truth. No numerical course run, metrics, screenshots, GPU/neural experiment, fixture or emitted scientific receipt has been created here. Read-only JSON peer reviews are separate tasks and not evidence for this course. Documentation checks later certify only tracked content/structure. Full MAIN read/approval must precede authored lessons, frontend, solver or test implementation.
