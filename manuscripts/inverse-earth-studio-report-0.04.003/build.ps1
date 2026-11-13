$ErrorActionPreference = 'Stop'

Push-Location $PSScriptRoot
try {
    $templatePath = Join-Path $PSScriptRoot 'main.tex.in'
    [System.IO.File]::WriteAllText((Join-Path $PSScriptRoot 'main.tex'), [System.IO.File]::ReadAllText($templatePath), [System.Text.UTF8Encoding]::new($false))
    latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
    if ($LASTEXITCODE -ne 0) { throw "LaTeX compilation failed with exit code $LASTEXITCODE" }
}
finally {
    Pop-Location
}
