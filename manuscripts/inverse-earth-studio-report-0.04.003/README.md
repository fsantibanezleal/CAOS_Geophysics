# Inverse Earth Studio technical report

This directory contains a working report draft. The page-one header deliberately marks the DOI fields as unassigned; it is not a deposited or peer-reviewed report. Do not treat the PDF as a release publication until an actual Zenodo concept/version record has been created and verified and `product.json` is updated from that record.

## Build

From this directory, run `./build.ps1`. The script assembles `main.tex` from `main.tex.in` and compiles `main.pdf` directly from the LaTeX sources with `latexmk` and XeLaTeX. Figure assets are in `figures/` and are embedded by relative path.

The report source is `body.tex` and the abstract source is `abstract.tex`. `main.tex.in` assembles both with the bibliography and page-one header. Confirm the PDF visually after changes. Numerical claims cite their underlying repository artifacts; the report does not claim field validation or release acceptance.
