# Template content-guard adoption: 2026-11-11

## Source and changes

The product checkout was based on `45f6427` and pins Shell `0.26.0`. Its reviewed template base is `0.15.008`, while `.template-version` remains the original `0.13.001` instantiation marker. The released template source is `CAOS_PRODUCT_TEMPLATE` tag `v0.15.008` (`ea61a66951a139b076c75af751e24a2d0b083f6b`).

This change brings the template's static notebook-depth and LaTeX-manuscript-depth guards into the product, with their adversarial fixtures. The product notebook reader now includes the released visibility parser and strips hidden HTML before it measures prose. `scripts/notebook_bar.json` adopts the released 1,000/1,500-word and 2/3-figure floors. CI runs both depth guards on pushes to `main` or `develop` and by manual `workflow_dispatch`; it does not trigger on pull requests under ADR-0074.

The checks read files only; they do not execute notebooks, build manuscripts, contact data providers, or change the VPS. Product-specific test adaptations remove only the template's expectation that an instantiated product already passes every curriculum gate; they retain synthetic pass controls, adversarial failures, and the read-only default-CLI check.

## Current results

Focused checker tests pass:

```powershell
.venv-pipeline\Scripts\python.exe -m pytest tests/adversarial/test_check_notebook_depth.py tests/adversarial/test_manuscript_depth.py tests/adversarial/test_manuscript_depth_admission.py -q
```

`py_compile` passes for both new guards, the notebook reader and their tests. `git diff --check` passes.

The current product content does not pass these newly integrated gates:

- Notebook depth at guard adoption: **179 findings** across the bilingual course, including missing equations, sources, figures, own-data/sensitivity sections, three contract mappings, and a declared pipeline-stage inventory.
- Manuscript depth: **5 findings**. The technical report and M12 paper are below the required depth; both lack coverage maps. The identifiability folder lacks a LaTeX main file. The beyond-methods paper is not in the DOI-backed product manifest, and there is no declared technical report coverage map.
- The existing notebook structural gate also fails under the adopted current notebook floors.

These results mean CI is now able to expose current content debt on pull requests. This tooling adoption does not resolve that debt or establish scientific, manuscript, UI, host, or release acceptance. No manuscript was registered or published and no VPS release was activated.


## Content follow-up

The English and Spanish foundations lessons on inverse evidence and residual identifiability now run the product gravity forward method, explain its two-cell sensitivity matrix and weighted objective, and store fresh outputs from execution in separate kernels. The identifiability chapter includes a grid-evaluated objective surface and explicitly distinguishes its deterministic perturbation from statistical confidence. Its own-data section follows the current gravity upload and eligibility contract. The product manifest now declares `gravity_forward.forward_gravity`, which those lessons execute.

Both foundations lessons pass their notebook depth and structural checks; their four fresh executions (write and read-only verification) completed successfully. The full-course notebook-depth checker now reports **161 findings**, down from the measured adoption baseline of 179. The rest of the bilingual curriculum and the manuscript findings remain open. This follow-up does not claim full content, scientific, release, or deployment acceptance.
