# Independent M01 transform review

Main reviewed the local equivalent-source implementation, independent prism-volume controls, blocked selection, propagation, figures and strict contracts. The final hardening was reviewed and independently tested in a separate detached checkout at `f42d3816d2fb094ee81102dd0f39e65367fd29d4` before PR #109 was merged to develop.

The first review identified incomplete correction-receipt verification and a pre-read size check that did not bound actual bytes read. The final code checks all deterministic processing fields, reconstructable earlier input states, compatible declared Python provenance and strict bounded JSON before numerics. Compatible runtime declarations are not authenticated source-runtime evidence. No station-correction source was changed, and previously published receipts and images remain explicitly historical.

## Independent execution

Using the existing isolated M01 interpreter read-only, with bytecode disabled and numerical threads limited to one:

```text
python -B -m pytest --override-ini=addopts= tests/numerics/test_gravity_transforms.py tests/numerics/test_gravity_processing.py tests/data/test_sources.py tests/data/test_ingest_dispatch.py -q --tb=short --basetemp <new-external-root>/p -o cache_dir=<new-external-root>/cache --junitxml <new-external-root>/m01-review.xml
```

Result: **89 passed, zero skips, 22.57 s**. Private XML SHA-256: `44b5e2cf377ac38d29f5eb26909122d3bcb788cdec7a9650ee889b836c5b766a`.

`M01_PRINCIPAL_FACT_ARCHIVE` pointed read-only to the previously acquired and pinned actual author archive, so the negative physical-metadata admission test ran rather than being skipped. Neither the archive nor its observations were copied to this checkout, public fixtures or evidence. Missing datum, uncertainty and original-processing lineage remain unresolved; rejection is not an eligible field modelling case.

The independent tests include actual Harmonica/Verde fits, three distinct irregular off-centre volume-generated controls, withheld-block perturbation, independent kernel/transfer comparisons, supported elevated predictions, nonunique layers, conditional covariance, immutable exports, known-stage resume, stale/rehashed receipt rejection, actual-byte/depth/encoding/nonfinite controls and committed figure/receipt integrity. Earlier direct map inspection was retained; these are labelled scientific diagnostic figures, not acceptance of the complete browser interface.

PR #109 merged at `66b3d5299b4133720bc6d0ad68ba7437afd41c82`. This is a local transform unit, not the full M01 workflow, uploaded-data correction worker, host admission, field eligibility, geological density inference, main release or deployment. Its prospective station API documentation is a separate design, not executed backend code.
