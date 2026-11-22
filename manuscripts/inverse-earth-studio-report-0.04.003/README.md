# Inverse Earth Studio technical report

This directory contains a working report draft. The page-one header deliberately marks the DOI fields as unassigned; it is not a deposited or peer-reviewed report. Do not treat the PDF as a release publication until an actual Zenodo concept/version record has been created and verified and `product.json` is updated from that record.

## Build

From this directory, set `GEOPHYSICS_LOCAL_DATA_ROOT` to the configured external data root, then run `python build_sparc_case.py --data-root $env:GEOPHYSICS_LOCAL_DATA_ROOT`. The script verifies the exact source, parser, processor, derived CSV and three M03 result hashes from the external case receipt, then regenerates `generated/sparc-m03-table.tex`. Run `python build_sparc_case.py --data-root $env:GEOPHYSICS_LOCAL_DATA_ROOT --check` to verify the committed table. Finally run `./build.ps1`; it assembles `main.tex` from `main.tex.in` and compiles `main.pdf` directly from the LaTeX sources with `latexmk` and XeLaTeX. Figure assets are in `figures/` and are embedded by relative path.

The report source is `body.tex` and the abstract source is `abstract.tex`. `main.tex.in` assembles both with the bibliography and page-one header. Confirm the PDF visually after changes. The SPARC case receipt and full provider archive remain outside Git; its generated summary table is hash-bound to those source artifacts. Numerical claims cite their underlying repository artifacts; the report does not claim field validation or release acceptance.
