$ErrorActionPreference = 'Stop'

Push-Location $PSScriptRoot
try {
    $repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
    py -3.12 (Join-Path $PSScriptRoot 'build_threshold_table.py') --root $repositoryRoot
    if ($LASTEXITCODE -ne 0) { throw "Threshold-table generation failed with exit code $LASTEXITCODE" }

    latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
    if ($LASTEXITCODE -ne 0) { throw "LaTeX compilation failed with exit code $LASTEXITCODE" }
}
finally {
    Pop-Location
}
