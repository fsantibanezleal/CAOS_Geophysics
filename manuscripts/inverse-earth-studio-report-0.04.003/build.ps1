$ErrorActionPreference = 'Stop'

pandoc abstract.md --from markdown --to latex --output abstract-generated.tex
pandoc body.md --from markdown --to latex --output body-generated.tex
$bodyPath = Join-Path $PSScriptRoot 'body-generated.tex'
$body = [System.IO.File]::ReadAllText($bodyPath)
$body = $body.Replace('\begin{figure}', '\begin{figure}[!t]')
[System.IO.File]::WriteAllText($bodyPath, $body, [System.Text.UTF8Encoding]::new($false))
$templatePath = Join-Path $PSScriptRoot 'main.tex.in'
[System.IO.File]::WriteAllText((Join-Path $PSScriptRoot 'main.tex'), [System.IO.File]::ReadAllText($templatePath), [System.Text.UTF8Encoding]::new($false))
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
if ($LASTEXITCODE -ne 0) { throw "LaTeX compilation failed with exit code $LASTEXITCODE" }
